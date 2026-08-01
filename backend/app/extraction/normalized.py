from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ContentBlock:
    block_index: int
    block_type: str
    text: str
    location: dict[str, Any] = field(default_factory=dict)
    heading_path: list[str] = field(default_factory=list)
    extraction_method: str = "native"
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalized_result(
    *,
    source_format: str,
    content_type: str,
    extraction_method: str,
    blocks: list[ContentBlock],
    warnings: list[str] | None = None,
    pages: list[dict] | None = None,
    ocr_required: str = "NO",
    ocr_confidence: float | None = None,
    ocr_model_version: str | None = None,
) -> dict:
    text = "\n\n".join(block.text.strip() for block in blocks if block.text.strip())
    return {
        "status": "success" if text else "empty",
        "source_format": source_format,
        "detected_content_type": content_type,
        "blocks": [block.to_dict() for block in blocks],
        "warnings": warnings or [],
        "text": text,
        "page_count": len(pages or []),
        "character_count": len(text),
        "word_count": len(text.split()),
        "extraction_method": extraction_method,
        "ocr_required": ocr_required,
        "ocr_confidence": ocr_confidence,
        "ocr_model_version": ocr_model_version,
        "pages": pages or [],
    }
