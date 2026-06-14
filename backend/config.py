import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtts://localhost:8883")
S3_BUCKET_INVOICES = os.getenv("S3_BUCKET_INVOICES")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v19.0")
