from backend.app.indexing.text_chunker import chunk_text

def create_document_chunks(document)-> dict:
    if not document.extracted_text:
        raise ValueError("Document has no extracted text to chunk.")
    
    chunks = chunk_text(document.extracted_text)

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
