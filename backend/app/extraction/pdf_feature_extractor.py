import string
from pathlib import Path

import fitz


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def extract_pdf_features(file_path: str) -> dict:
    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Feature extractor currently supports PDF files only.")

    document = fitz.open(pdf_path)

    full_text = ""
    text_block_count = 0
    image_count = 0

    page_width = 0.0
    page_height = 0.0
    page_area = 0.0

    total_text_area = 0.0
    largest_text_block_area = 0.0

    total_image_area = 0.0
    largest_image_area = 0.0

    for page in document:
        page_rect = page.rect
        page_width = float(page_rect.width)
        page_height = float(page_rect.height)
        page_area += page_width * page_height

        page_text = page.get_text("text")
        full_text += page_text + "\n"

        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])

        for block in blocks:
            block_type = block.get("type")

            x0, y0, x1, y1 = block.get("bbox", [0, 0, 0, 0])
            block_area = max(0.0, (x1 - x0) * (y1 - y0))

            if block_type == 0:
                text_block_count += 1
                total_text_area += block_area
                largest_text_block_area = max(largest_text_block_area, block_area)

            elif block_type == 1:
                image_count += 1
                total_image_area += block_area
                largest_image_area = max(largest_image_area, block_area)

    document.close()

    text = full_text.strip()

    char_count = len(text)
    words = text.split()
    word_count = len(words)

    alphabetic_count = sum(char.isalpha() for char in text)
    digit_count = sum(char.isdigit() for char in text)
    whitespace_count = sum(char.isspace() for char in text)
    printable_count = sum(char in string.printable for char in text)
    symbol_count = sum(
        not char.isalnum() and not char.isspace()
        for char in text
    )

    avg_word_length = (
        sum(len(word) for word in words) / word_count
        if word_count > 0
        else 0.0
    )

    avg_text_block_area = _safe_divide(total_text_area, text_block_count)
    avg_image_area = _safe_divide(total_image_area, image_count)

    return {
        "char_count": char_count,
        "word_count": word_count,
        "avg_word_length": avg_word_length,
        "printable_char_ratio": _safe_divide(printable_count, char_count),
        "whitespace_ratio": _safe_divide(whitespace_count, char_count),
        "alphabetic_ratio": _safe_divide(alphabetic_count, char_count),
        "digit_ratio": _safe_divide(digit_count, char_count),
        "symbol_ratio": _safe_divide(symbol_count, char_count),

        "text_block_count": text_block_count,
        "image_count": image_count,

        "page_width": page_width,
        "page_height": page_height,
        "page_area": page_area,

        "chars_per_page_area": _safe_divide(char_count, page_area),
        "words_per_page_area": _safe_divide(word_count, page_area),

        "layout_text_block_count": text_block_count,
        "layout_image_count": image_count,

        "total_text_area": total_text_area,
        "avg_text_block_area": avg_text_block_area,
        "largest_text_block_area": largest_text_block_area,

        "total_image_area": total_image_area,
        "avg_image_area": avg_image_area,
        "largest_image_area": largest_image_area,

        "text_area_ratio": _safe_divide(total_text_area, page_area),
        "image_area_ratio": _safe_divide(total_image_area, page_area),
        "largest_image_area_ratio": _safe_divide(largest_image_area, page_area),
        "largest_text_block_ratio": _safe_divide(largest_text_block_area, page_area),
        "text_to_image_area_ratio": _safe_divide(total_text_area, total_image_area),
    }