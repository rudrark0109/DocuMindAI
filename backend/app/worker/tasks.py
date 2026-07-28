from backend.app.services.document_processing import process_document_job
from backend.app.worker.celery_app import celery_app


@celery_app.task(name="documents.process", acks_late=True)
def process_document_task(document_id: str) -> dict:
    return process_document_job(document_id)
