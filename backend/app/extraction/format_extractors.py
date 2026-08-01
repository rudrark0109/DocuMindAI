from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from backend.app.extraction.normalized import ContentBlock, normalized_result
from backend.app.extraction.paddle_ocr_extractor import extract_text_from_image


class UnsupportedDocumentError(ValueError):
    pass


class MalformedDocumentError(ValueError):
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg"}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def validate_document(path: Path) -> tuple[str, str]:
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentError(f"Unsupported file type: {extension or 'none'}.")
    header = path.read_bytes()[:16]
    if extension == ".pdf" and not header.startswith(b"%PDF-"):
        raise MalformedDocumentError("The uploaded file is not a valid PDF.")
    if extension == ".docx":
        try:
            with zipfile.ZipFile(path) as archive:
                if "[Content_Types].xml" not in archive.namelist() or "word/document.xml" not in archive.namelist():
                    raise MalformedDocumentError("The uploaded file is not a valid DOCX document.")
        except zipfile.BadZipFile as exc:
            raise MalformedDocumentError("The uploaded file is not a valid DOCX document.") from exc
    if extension == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise MalformedDocumentError("The uploaded file is not a valid PNG image.")
    if extension in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
        raise MalformedDocumentError("The uploaded file is not a valid JPEG image.")
    if extension in {".txt", ".md", ".csv"} and b"\x00" in path.read_bytes()[:4096]:
        raise MalformedDocumentError("The uploaded text file contains binary data.")
    return extension.lstrip("."), CONTENT_TYPES[extension]


def _decode_text(path: Path) -> tuple[str, list[str]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            return raw.decode(encoding), []
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), ["Invalid byte sequences were replaced during decoding."]


def extract_text_file(path: Path) -> dict:
    text, warnings = _decode_text(path)
    blocks = [
        ContentBlock(index, "paragraph", paragraph.strip(), {"paragraph": index + 1})
        for index, paragraph in enumerate(re.split(r"\n\s*\n", text))
        if paragraph.strip()
    ]
    return normalized_result(source_format="txt", content_type=CONTENT_TYPES[".txt"], extraction_method="text", blocks=blocks, warnings=warnings)


def extract_markdown(path: Path) -> dict:
    text, warnings = _decode_text(path)
    blocks: list[ContentBlock] = []
    headings: list[str] = []
    in_code = False
    buffer: list[str] = []
    block_type = "paragraph"

    def flush() -> None:
        nonlocal buffer
        value = "\n".join(buffer).strip()
        if value:
            blocks.append(ContentBlock(len(blocks), block_type, value, {"block": len(blocks) + 1}, list(headings)))
        buffer = []

    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if line.strip().startswith("```"):
            flush()
            in_code = not in_code
            block_type = "code" if in_code else "paragraph"
            continue
        if heading and not in_code:
            flush()
            level = len(heading.group(1))
            headings = headings[: level - 1] + [heading.group(2).strip()]
            blocks.append(ContentBlock(len(blocks), "heading", headings[-1], {"heading_level": level}, list(headings)))
            block_type = "paragraph"
        elif not line.strip() and not in_code:
            flush()
            block_type = "paragraph"
        else:
            if not in_code and re.match(r"^\s*[-*+]\s+", line):
                block_type = "list"
            elif not in_code and "|" in line:
                block_type = "table"
            buffer.append(line)
    flush()
    return normalized_result(source_format="md", content_type=CONTENT_TYPES[".md"], extraction_method="markdown", blocks=blocks, warnings=warnings)


def extract_csv(path: Path, rows_per_block: int = 50) -> dict:
    text, warnings = _decode_text(path)
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise MalformedDocumentError(f"Malformed CSV: {exc}") from exc
    if not rows:
        return normalized_result(source_format="csv", content_type=CONTENT_TYPES[".csv"], extraction_method="csv", blocks=[], warnings=warnings)
    header, data = rows[0], rows[1:]
    blocks = []
    for start in range(0, max(len(data), 1), rows_per_block):
        group = data[start : start + rows_per_block]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerows(group)
        blocks.append(ContentBlock(len(blocks), "table", output.getvalue().strip(), {"row_start": start + 2, "row_end": start + len(group) + 1}, metadata={"headers": header}))
    return normalized_result(source_format="csv", content_type=CONTENT_TYPES[".csv"], extraction_method="csv", blocks=blocks, warnings=warnings)


def extract_docx(path: Path) -> dict:
    from docx import Document as DocxDocument
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = DocxDocument(path)
    except (ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise MalformedDocumentError("The DOCX document could not be parsed.") from exc
    blocks: list[ContentBlock] = []
    headings: list[str] = []
    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            value = item.text.strip()
            if not value:
                continue
            style = item.style.name if item.style else ""
            match = re.match(r"Heading (\d+)", style)
            kind = "paragraph"
            if match:
                level = int(match.group(1))
                headings = headings[: level - 1] + [value]
                kind = "heading"
            elif style.lower().startswith("list"):
                kind = "list"
            blocks.append(ContentBlock(len(blocks), kind, value, {"paragraph": len(blocks) + 1}, list(headings), metadata={"style": style}))
        elif isinstance(item, Table):
            rows = [[cell.text.strip() for cell in row.cells] for row in item.rows]
            rendered = "\n".join(" | ".join(row) for row in rows)
            if rendered.strip():
                blocks.append(ContentBlock(len(blocks), "table", rendered, {"table": sum(block.block_type == "table" for block in blocks) + 1}, list(headings)))
    return normalized_result(source_format="docx", content_type=CONTENT_TYPES[".docx"], extraction_method="python-docx", blocks=blocks)


def extract_image(path: Path) -> dict:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"))
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise MalformedDocumentError("The image could not be decoded.") from exc
    result = extract_text_from_image(rgb)
    block = ContentBlock(0, "image_ocr", result["text"], {"image": path.name}, extraction_method="paddleocr", confidence=result["average_confidence"], metadata={"width": width, "height": height})
    return normalized_result(source_format=path.suffix.lower().lstrip("."), content_type=CONTENT_TYPES[path.suffix.lower()], extraction_method="paddleocr", blocks=[block] if block.text else [], ocr_required="YES", ocr_confidence=result["average_confidence"])
