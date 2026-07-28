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
    ocr_render_dpi: int = 200
    ocr_text_score_threshold: float = 0.5
    ocr_use_doc_orientation: bool = True
    ocr_use_textline_orientation: bool = True
    ocr_enable_mkldnn: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
