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

# JWT auth for device/admin identity. Set a real JWT_SECRET in production —
# the fallback is only safe for local development.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
DEVICE_ACCESS_TOKEN_TTL_SECONDS = 15 * 60
DEVICE_REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60
ADMIN_ACCESS_TOKEN_TTL_SECONDS = 60 * 60
PAIRING_CODE_TTL_SECONDS = 15 * 60
DEFAULT_BRAND_CODE = os.getenv("DEFAULT_BRAND_CODE", "DEFAULT")
DEFAULT_BRAND_NAME = os.getenv("DEFAULT_BRAND_NAME", "Default Brand")

# Outgoing mail for order receipts. SMTP_EMAIL/SMTP_PASSWORD are the sending
# mailbox's address and app password (e.g. a Gmail App Password, not the
# account login password). Receipt sending is best-effort - if these are
# unset, checkout still succeeds and the email is just skipped.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "SmartCheckout")
