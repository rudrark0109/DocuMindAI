from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5433/documind_ai"
    )
    frontend_origin: str = "http://localhost:5173"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    max_upload_size_mb: int = 25
    paddle_ocr_language: str = "en"
    paddle_ocr_version: str = "PP-OCRv6"
    paddle_ocr_device: str = "cpu"
    ocr_render_dpi: int = 150
    ocr_large_document_page_threshold: int = 20
    ocr_large_document_dpi: int = 96
    ocr_max_render_side: int = 2400
    ocr_max_render_pixels: int = 4_000_000
    ocr_text_score_threshold: float = 0.5
    ocr_use_doc_orientation: bool = False
    ocr_use_textline_orientation: bool = False
    ocr_enable_mkldnn: bool = False
    rag_provider: str = "auto"
    rag_gemini_api_key: str | None = None
    rag_gemini_model: str = "gemini-2.5-flash"
    rag_similarity_threshold: float = 0.25
    rag_max_context_chars: int = 12000
    rag_max_citations: int = 8
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
