import re


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[dict]:
    
    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    words = text.split()
    chunks = []

    start = 0
    chunk_index = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_value = " ".join(chunk_words)

        chunks.append(
            {
                "chunk_index": chunk_index,
                "text": chunk_text_value,
                "word_count": len(chunk_words),
                "char_count": len(chunk_text_value),
                "start_word_index": start,
                "end_word_index": min(end, len(words)),
            }
        )

        chunk_index += 1
        start += chunk_size - overlap

    return chunks


STRUCTURE_CHUNKER_VERSION = "structure-aware-v2.3"


def _sentence_units(text: str, max_words: int) -> list[str]:
    sentences = [value.strip() for value in re.split(r"(?<=[.!?])\s+|\n+", text) if value.strip()]
    units: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words:
            units.append(sentence)
        else:
            units.extend(" ".join(words[start : start + max_words]) for start in range(0, len(words), max_words))
    return units


def chunk_blocks(blocks: list[dict], target_words: int = 400, max_words: int = 650) -> list[dict]:
    """Create deterministic chunks without crossing incompatible structural boundaries."""
    chunks: list[dict] = []
    cursor = 0
    for block in blocks:
        text = (block.get("text") or "").strip()
        if not text or block.get("block_type") == "heading":
            continue
        heading_path = list(block.get("heading_path") or [])
        prefix = " > ".join(heading_path)
        units = _sentence_units(text, max_words)
        current: list[str] = []
        for unit in units:
            projected = len(" ".join(current + [unit]).split())
            if current and projected > target_words:
                value = " ".join(current)
                rendered = f"{prefix}\n\n{value}" if prefix else value
                count = len(rendered.split())
                chunks.append({
                    "chunk_index": len(chunks), "text": rendered,
                    "word_count": count, "char_count": len(rendered),
                    "start_word_index": cursor, "end_word_index": cursor + count,
                    "source_location": block.get("location") or {},
                    "heading_path": heading_path,
                    "block_types": [block.get("block_type", "paragraph")],
                })
                cursor += count
                current = []
            current.append(unit)
        if current:
            value = " ".join(current)
            rendered = f"{prefix}\n\n{value}" if prefix else value
            count = len(rendered.split())
            chunks.append({
                "chunk_index": len(chunks), "text": rendered,
                "word_count": count, "char_count": len(rendered),
                "start_word_index": cursor, "end_word_index": cursor + count,
                "source_location": block.get("location") or {},
                "heading_path": heading_path,
                "block_types": [block.get("block_type", "paragraph")],
            })
            cursor += count
    return chunks
