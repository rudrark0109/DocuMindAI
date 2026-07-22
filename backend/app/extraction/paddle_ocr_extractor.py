from functools import lru_cache

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def get_ocr_engine():
    # PaddleOCR is deliberately imported lazily: normal PyMuPDF extraction does
    # not need to initialize the OCR runtime or download OCR model weights.
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang=settings.paddle_ocr_language,
        ocr_version=settings.paddle_ocr_version,
        device=settings.paddle_ocr_device,
        text_rec_score_thresh=settings.ocr_text_score_threshold,
        use_doc_orientation_classify=settings.ocr_use_doc_orientation,
        use_doc_unwarping=False,
        use_textline_orientation=settings.ocr_use_textline_orientation,
    )
