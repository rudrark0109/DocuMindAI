from celery import Celery

from backend.app.core.config import settings


celery_app = Celery(
    "documindai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.app.worker.tasks"],
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
