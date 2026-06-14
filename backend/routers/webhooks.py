from fastapi import APIRouter, Depends, Request

from ..api_response import ok
from ..auth import require_webhook_key

router = APIRouter(prefix="/api/v1/webhooks", tags=["enterprise-webhooks"])


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, _: str = Depends(require_webhook_key)):
    """Handle Meta WhatsApp delivery callbacks after HMAC verification."""
    payload = await request.json()
    return ok({"received": True, "provider": "whatsapp", "payload_keys": list(payload.keys())})


@router.post("/payment")
async def payment_webhook(request: Request, _: str = Depends(require_webhook_key)):
    """Handle payment provider callbacks after HMAC verification."""
    payload = await request.json()
    return ok({"received": True, "provider": "payment", "payload_keys": list(payload.keys())})
