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