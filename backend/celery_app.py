from celery import Celery

from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "smartcheckout",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["backend.tasks.invoice", "backend.tasks.whatsapp"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_default_retry_delay=30,
    task_routes={
        "backend.tasks.invoice.*": {"queue": "invoices"},
        "backend.tasks.whatsapp.*": {"queue": "whatsapp"},
    },
)
