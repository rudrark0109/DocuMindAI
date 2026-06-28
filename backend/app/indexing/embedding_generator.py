from functools import lru_cache
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)

def generate_embedding(text: str) -> list[float]:
    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError("Input text is empty or contains only whitespace.")
    
    model = get_embedding_model()
    embedding = model.encode(cleaned_text, normalize_embeddings=True, convert_to_numpy=True)
    
    vector = embedding.tolist()

    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(f"Generated embedding has an unexpected dimension: {len(vector)}. Expected: {EMBEDDING_DIMENSION}.")
    
    return vector

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    cleaned_texts = [text.strip() for text in texts]

    if not cleaned_texts:
        return []
    
    if any(not text for text in cleaned_texts):
        raise ValueError("One or more input texts are empty or contain only whitespace.")
    
    model = get_embedding_model()
    embeddings = model.encode(cleaned_texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)

    vectors = embeddings.tolist()

    if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
        raise ValueError("One or more generated embeddings have unexpected dimensions.")
    
    return vectors  