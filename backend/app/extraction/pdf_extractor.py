from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> dict:
    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Unsupported file type: {pdf_path.suffix}. Only PDF files are supported."
        )

    document = fitz.open(pdf_path)

    extracted_pages = []

    for page_num, page in enumerate(document, start=1):
        page_text = page.get_text("text").strip()

        extracted_pages.append(
            {
                "page_number": page_num,
                "text": page_text,
                "character_count": len(page_text),
                "word_count": len(page_text.split()),
            }
        )

    full_text = "\n\n".join(
        page_data["text"]
        for page_data in extracted_pages
        if page_data["text"]
    )

    document.close()

    return {
        "text": full_text,
        "page_count": len(extracted_pages),
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "extraction_method": "pymupdf",
        "status": "success" if full_text else "empty",
        "pages": extracted_pages,
    }