import os

from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(database_url: str | None) -> str | None:
    if database_url and database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url and database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtts://localhost:8883")
S3_BUCKET_INVOICES = os.getenv("S3_BUCKET_INVOICES")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v19.0")
