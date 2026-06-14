from decimal import Decimal
from typing import Any

try:
    import phonenumbers
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    phonenumbers = None


def to_e164_india(phone: str) -> str:
    if phonenumbers is None:
        digits = "".join(ch for ch in phone if ch.isdigit())
        if digits.startswith("91") and len(digits) == 12:
            return f"+{digits}"
        if len(digits) == 10:
            return f"+91{digits}"
        raise ValueError("Invalid phone number")
    parsed = phonenumbers.parse(phone, "IN")
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def build_invoice_template_payload(
    *,
    phone_to: str,
    media_id: str,
    customer_name: str,
    order_number: str,
    store_name: str,
    grand_total: Decimal,
    points_earned: int,
    template_name: str = "order_invoice_v1",
) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "to": to_e164_india(phone_to),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_IN"},
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "document",
                            "document": {
                                "id": media_id,
                                "filename": f"invoice_{order_number}.pdf",
                            },
                        }
                    ],
                },
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": customer_name or "Customer"},
                        {"type": "text", "text": order_number},
                        {"type": "text", "text": store_name},
                        {"type": "text", "text": f"{grand_total:.2f}"},
                        {"type": "text", "text": str(points_earned)},
                    ],
                },
            ],
        },
    }
