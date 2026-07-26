"""Run a reproducible mixed-PDF upload-to-search smoke test."""
import argparse
import tempfile
import time
from pathlib import Path

import fitz
import psycopg2
import requests


def wait_for_api(api_url: str, timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise TimeoutError(f"Backend did not become ready within {timeout_seconds}s.")


def create_mixed_pdf(path: Path) -> None:
    scanned_source = fitz.open()
    scanned_page = scanned_source.new_page(width=612, height=792)
    scanned_page.insert_text(
        (72, 120),
        "SCANNED PAGE: quarterly revenue was 42 million dollars.",
        fontsize=18,
    )
    scanned_image = scanned_page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
    scanned_source.close()

    document = fitz.open()
    native_page = document.new_page(width=612, height=792)
    native_page.insert_text(
        (72, 120),
        "NATIVE PAGE: DocuMindAI keeps searchable digital text.",
        fontsize=18,
    )
    image_page = document.new_page(width=612, height=792)
    image_page.insert_image(image_page.rect, stream=scanned_image)
    document.save(path)
    document.close()


def verify(api_url: str, database_url: str) -> None:
    wait_for_api(api_url)
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / "mixed-pre-search-smoke.pdf"
        create_mixed_pdf(pdf_path)

        with pdf_path.open("rb") as pdf_file:
            response = requests.post(
                f"{api_url}/documents/upload",
                files={"file": (pdf_path.name, pdf_file, "application/pdf")},
                timeout=900,
            )

    response.raise_for_status()
    result = response.json()
    assert result["processing_status"] == "embedded", result
    assert result["extraction_method"] == "hybrid", result
    assert result["chunk_count"] >= 1, result
    assert result["embedded_chunk_count"] == result["chunk_count"], result

    document_id = result["document_id"]
    text_response = requests.get(
        f"{api_url}/documents/{document_id}/text",
        timeout=30,
    )
    text_response.raise_for_status()
    extracted_text = text_response.json()["text"]
    assert "NATIVE PAGE" in extracted_text, extracted_text
    assert "quarterly revenue" in extracted_text.lower(), extracted_text

    psycopg_url = database_url.replace("postgresql+psycopg2://", "postgresql://")
    with psycopg2.connect(psycopg_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*), min(vector_dims(embedding)), max(vector_dims(embedding))
                FROM document_chunks
                WHERE document_id = %s AND embedding_status = 'embedded'
                """,
                (document_id,),
            )
            chunk_count, min_dimensions, max_dimensions = cursor.fetchone()

    assert chunk_count == result["chunk_count"]
    assert min_dimensions == max_dimensions == 384

    repeat = requests.post(
        f"{api_url}/documents/{document_id}/embed",
        timeout=30,
    )
    repeat.raise_for_status()
    assert repeat.json()["embedding_result"]["status"] == "no_pending_chunks"

    search_response = requests.post(
        f"{api_url}/search",
        json={
            "query": "quarterly revenue",
            "top_k": 3,
            "similarity_threshold": 0.0,
            "document_id": document_id,
        },
        timeout=120,
    )
    search_response.raise_for_status()
    search_result = search_response.json()
    assert search_result["result_count"] >= 1, search_result
    assert search_result["results"][0]["document_id"] == document_id, search_result
    assert "quarterly revenue" in search_result["results"][0]["text"].lower()

    print(
        "PASS:",
        f"document={document_id}",
        f"method={result['extraction_method']}",
        f"chunks={chunk_count}",
        "dimensions=384",
        "repeat_embed=no_pending_chunks",
        f"search_similarity={search_result['results'][0]['similarity']}",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://backend:8000")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg2://postgres:postgres@postgres:5432/documind_ai",
    )
    args = parser.parse_args()
    verify(args.api_url.rstrip("/"), args.database_url)


if __name__ == "__main__":
    main()
