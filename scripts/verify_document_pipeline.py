from __future__ import annotations

import argparse
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import fitz
import psycopg2
import requests


class VerificationError(RuntimeError):
    """Raised when a verification stage does not meet its contract."""


def require(condition: bool, stage: str, message: str, details: Any = None) -> None:
    if condition:
        return
    suffix = f" Details: {details!r}" if details is not None else ""
    raise VerificationError(f"{stage}: {message}.{suffix}")


def request(
    method: str,
    url: str,
    *,
    stage: str,
    timeout: int,
    **kwargs: Any,
) -> requests.Response:
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        response = getattr(exc, "response", None)
        body = response.text[:2000] if response is not None else None
        raise VerificationError(
            f"{stage}: request failed for {method} {url}. Response: {body!r}"
        ) from exc


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
    raise VerificationError(
        f"readiness: backend did not become ready within {timeout_seconds}s"
    )


def wait_for_processing(
    api_url: str,
    document_id: str,
    timeout_seconds: int = 900,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    latest: dict = {}
    while time.monotonic() < deadline:
        latest = request(
            "GET",
            f"{api_url}/documents/{document_id}/status",
            stage="background processing",
            timeout=30,
        ).json()
        if latest.get("job_status") == "completed":
            return latest
        if latest.get("job_status") == "failed":
            raise VerificationError(
                f"background processing: worker failed. Details: {latest!r}"
            )
        time.sleep(2)
    raise VerificationError(
        "background processing: document did not complete within "
        f"{timeout_seconds}s. Details: {latest!r}"
    )


def processing_is_terminal(api_url: str, document_id: str) -> bool:
    try:
        response = requests.get(
            f"{api_url}/documents/{document_id}/status",
            timeout=30,
        )
        if response.status_code == 404:
            return True
        response.raise_for_status()
        return response.json().get("job_status") in {"completed", "failed"}
    except requests.RequestException:
        return False


def create_mixed_pdf(path: Path, scanned_pages: int = 1) -> None:
    with fitz.open() as scanned_source:
        scanned_page = scanned_source.new_page(width=612, height=792)
        scanned_page.insert_text(
            (72, 120),
            "SCANNED PAGE: quarterly revenue was 42 million dollars.",
            fontsize=18,
        )
        scanned_image = scanned_page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        ).tobytes("png")

    with fitz.open() as document:
        native_page = document.new_page(width=612, height=792)
        native_page.insert_text(
            (72, 120),
            "NATIVE PAGE: DocuMindAI keeps searchable digital text.",
            fontsize=18,
        )
        for _ in range(scanned_pages):
            image_page = document.new_page(width=612, height=792)
            image_page.insert_image(image_page.rect, stream=scanned_image)
        document.save(path)


def inspect_vectors(database_url: str, document_id: str) -> tuple[int, int, int]:
    try:
        with (
            psycopg2.connect(database_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """
                SELECT
                    count(*),
                    min(vector_dims(embedding)),
                    max(vector_dims(embedding))
                FROM document_chunks
                WHERE document_id = %s
                  AND embedding_status = 'embedded'
                """,
                (document_id,),
            )
            result = cursor.fetchone()
    except psycopg2.Error as exc:
        raise VerificationError(
            f"database inspection: unable to inspect vectors for {document_id}"
        ) from exc

    require(
        result is not None,
        "database inspection",
        "vector query returned no aggregate row",
    )
    chunk_count, min_dimensions, max_dimensions = result
    return int(chunk_count), int(min_dimensions or 0), int(max_dimensions or 0)


def cleanup_document(database_url: str, document_id: str) -> None:
    file_path: str | None = None
    try:
        with (
            psycopg2.connect(database_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "SELECT file_path FROM documents WHERE id = %s",
                (document_id,),
            )
            row = cursor.fetchone()
            file_path = row[0] if row else None
            cursor.execute(
                "DELETE FROM document_chunks WHERE document_id = %s",
                (document_id,),
            )
            cursor.execute(
                "DELETE FROM documents WHERE id = %s",
                (document_id,),
            )
    except psycopg2.Error as exc:
        raise VerificationError(
            f"cleanup: unable to remove test document {document_id}"
        ) from exc

    if file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError as exc:
            raise VerificationError(
                f"cleanup: unable to remove stored test file {file_path}"
            ) from exc


def verify(
    api_url: str,
    database_url: str,
    keep_test_data: bool = False,
    scanned_pages: int = 1,
) -> None:
    wait_for_api(api_url)
    document_id: str | None = None
    verification_failed = False

    try:
        with ExitStack() as stack:
            temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            pdf_path = Path(temp_dir) / "mixed-pipeline-smoke.pdf"
            create_mixed_pdf(pdf_path, scanned_pages=scanned_pages)

            pdf_file = stack.enter_context(pdf_path.open("rb"))
            upload_started = time.monotonic()
            response = request(
                "POST",
                f"{api_url}/documents/upload",
                stage="upload and queue",
                files={"file": (pdf_path.name, pdf_file, "application/pdf")},
                timeout=30,
            )
            upload_seconds = time.monotonic() - upload_started

        result = response.json()
        document_id = result.get("document_id")
        require(
            bool(document_id),
            "upload and queue",
            "response did not contain document_id",
            result,
        )
        require(
            result.get("processing_status") == "queued",
            "upload and queue",
            "document was not queued",
            result,
        )
        require(
            upload_seconds < 10,
            "upload and queue",
            "upload response was not bounded",
            {"seconds": upload_seconds},
        )

        processing_started = time.monotonic()
        processing_status = wait_for_processing(
            api_url,
            document_id,
            timeout_seconds=max(900, scanned_pages * 30),
        )
        processing_seconds = time.monotonic() - processing_started
        document_result = request(
            "GET",
            f"{api_url}/documents/{document_id}",
            stage="document metadata",
            timeout=30,
        ).json()
        require(
            document_result.get("processing_status") == "embedded",
            "background processing",
            "document did not reach embedded status",
            document_result,
        )
        require(
            document_result.get("extraction_method") == "hybrid",
            "background processing",
            "mixed PDF did not use hybrid extraction",
            document_result,
        )

        text_response = request(
            "GET",
            f"{api_url}/documents/{document_id}/text",
            stage="text retrieval",
            timeout=30,
        )
        extracted_text = text_response.json().get("text", "")
        require(
            "NATIVE PAGE" in extracted_text,
            "text retrieval",
            "native page text is missing",
            extracted_text,
        )
        require(
            "quarterly revenue" in extracted_text.lower(),
            "text retrieval",
            "OCR-produced page text is missing",
            extracted_text,
        )

        chunk_count, min_dimensions, max_dimensions = inspect_vectors(
            database_url,
            document_id,
        )
        require(
            chunk_count >= 1,
            "database inspection",
            "no embedded chunks were persisted",
            {"database": chunk_count},
        )
        require(
            min_dimensions == max_dimensions == 384,
            "database inspection",
            "stored embeddings do not have 384 dimensions",
            {
                "minimum": min_dimensions,
                "maximum": max_dimensions,
            },
        )

        repeat = request(
            "POST",
            f"{api_url}/documents/{document_id}/embed",
            stage="repeat embedding",
            timeout=30,
        ).json()
        require(
            repeat.get("embedding_result", {}).get("status")
            == "no_pending_chunks",
            "repeat embedding",
            "repeat call was not idempotent",
            repeat,
        )

        search_result = request(
            "POST",
            f"{api_url}/search",
            stage="semantic search",
            json={
                "query": "quarterly revenue",
                "top_k": 3,
                "similarity_threshold": 0.0,
                "document_id": document_id,
            },
            timeout=120,
        ).json()
        require(
            search_result.get("result_count", 0) >= 1,
            "semantic search",
            "no matching result was returned",
            search_result,
        )
        first_result = search_result["results"][0]
        require(
            first_result.get("document_id") == document_id,
            "semantic search",
            "top result references a different document",
            first_result,
        )
        require(
            "quarterly revenue" in first_result.get("text", "").lower(),
            "semantic search",
            "top result does not contain the expected passage",
            first_result,
        )

        print(
            "PASS:",
            f"document={document_id}",
            f"method={document_result['extraction_method']}",
            f"chunks={chunk_count}",
            f"pages={scanned_pages + 1}",
            f"upload_seconds={upload_seconds:.3f}",
            f"processing_seconds={processing_seconds:.3f}",
            f"job_status={processing_status['job_status']}",
            "dimensions=384",
            "repeat_embed=no_pending_chunks",
            f"search_similarity={first_result['similarity']}",
            f"cleanup={'skipped' if keep_test_data else 'pending'}",
        )
    except Exception:
        verification_failed = True
        raise
    finally:
        if (
            document_id
            and not keep_test_data
            and processing_is_terminal(api_url, document_id)
        ):
            try:
                cleanup_document(database_url, document_id)
                print(f"CLEANUP: removed test document {document_id}")
            except VerificationError as cleanup_error:
                if verification_failed:
                    print(str(cleanup_error), file=sys.stderr)
                else:
                    raise
        elif document_id and not keep_test_data:
            print(
                "CLEANUP: retained active test document "
                f"{document_id}; remove it after processing reaches a terminal state."
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the complete DocuMindAI pipeline inside Docker Compose. "
            "The default service names are not resolvable from the host."
        )
    )
    parser.add_argument("--api-url", default="http://backend:8000")
    parser.add_argument(
        "--database-url",
        default="postgresql://postgres:postgres@postgres:5432/documind_ai",
        help="Direct psycopg PostgreSQL URL used for integrity checks and cleanup.",
    )
    parser.add_argument(
        "--keep-test-data",
        action="store_true",
        help="Retain the generated document, chunks, embeddings, and stored PDF.",
    )
    parser.add_argument(
        "--scanned-pages",
        type=int,
        default=1,
        choices=range(1, 101),
        metavar="1-100",
        help="Number of image-only pages to generate after one native-text page.",
    )
    args = parser.parse_args()
    verify(
        args.api_url.rstrip("/"),
        args.database_url,
        keep_test_data=args.keep_test_data,
        scanned_pages=args.scanned_pages,
    )


if __name__ == "__main__":
    main()
