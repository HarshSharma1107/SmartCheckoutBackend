from decimal import Decimal

from backend.services.whatsapp import build_invoice_template_payload, to_e164_india


def test_to_e164_india_normalizes_local_number():
    assert to_e164_india("9876543210") == "+919876543210"


def test_build_invoice_template_payload():
    payload = build_invoice_template_payload(
        phone_to="9876543210",
        media_id="media123",
        customer_name="Rahul",
        order_number="ORD-1",
        store_name="Main Store",
        grand_total=Decimal("123.45"),
        points_earned=1,
    )

    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "+919876543210"
    assert payload["template"]["name"] == "order_invoice_v1"
    assert payload["template"]["components"][0]["parameters"][0]["document"]["id"] == "media123"
