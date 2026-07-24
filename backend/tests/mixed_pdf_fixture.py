from pathlib import Path

import fitz


def create_mixed_pdf(path: Path) -> None:
    """Create a real two-page PDF: native text followed by a rasterized scan."""
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
