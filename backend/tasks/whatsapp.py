from decimal import Decimal
from uuid import UUID

from ..celery_app import celery_app
from ..services.whatsapp import build_invoice_template_payload


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.whatsapp.send_whatsapp_invoice")
def send_whatsapp_invoice(self, order_id: str) -> dict[str, object]:
    """Build and send the WhatsApp invoice template message.

    Network calls to Meta are intentionally deferred until brand credentials,
    media upload, and webhook signature verification are configured.
    """
    UUID(order_id)
    payload = build_invoice_template_payload(
        phone_to="+919999999999",
        media_id="media-placeholder",
        customer_name="Customer",
        order_number=order_id,
        store_name="Store",
        grand_total=Decimal("0.00"),
        points_earned=0,
    )
    return {"order_id": order_id, "payload": payload, "sent": False, "reason": "WHATSAPP_NOT_CONFIGURED"}

