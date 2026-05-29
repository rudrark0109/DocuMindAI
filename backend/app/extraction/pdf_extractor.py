from pathlib import Path
import fitz  # PyMuPDF

def text_extractor(file_path: str) -> dict:
    pdf_path = Path(file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"Unsupported file type: {pdf_path.suffix}. Only PDF files are supported.")
    
    document = fitz.open(pdf_path)

    extracted_pages = []

    for page_num, page in enumerate(document, start=1):
        page_text = page.get_text("text").strip()

        extracted_pages.append({
            "page_number": page_num,
            "text": page_text,
            "character_count": len(page_text),
        })

    full_text = "\n\n".join(
        page_data["text"] 
        for page_data in extracted_pages 
        if page_data["text"]
    )

    document.close()

    character_count = len(full_text)
    page_count = len(extracted_pages)

    if character_count == 0:
        raise ValueError("No text could be extracted from the PDF. The document may be scanned or contain only images.")
        requires_ocr = True
    elif character_count < 100:
        extraction_quality = "low"
        requires_ocr = True
    else:
        extraction_quality = "high"
        requires_ocr = False

    return {
        "text": full_text,
        "page_count": page_count,
        "character_extracted": character_count,
        "extraction_quality": extraction_quality,
        "requires_ocr": requires_ocr,
        "method": "pymupdf",
        "pages": extracted_pages
    }

