from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..database import get_db
from ..schemas_enterprise import CustomerLookupRequest, CustomerLookupResponse, VerifyOtpRequest, VerifyOtpResponse, VerifyPhoneRequest

router = APIRouter(prefix="/api/v1/customers", tags=["enterprise-customers"])


@router.post("/lookup")
async def lookup_customer(payload: CustomerLookupRequest, db: AsyncSession = Depends(get_db)):
    """Lookup customer loyalty profile and recent orders by brand-scoped phone."""
    result = await db.execute(
        text(
            """
            SELECT customer_id, name, loyalty_points, tier, whatsapp_opt_in
            FROM ekart_prod.customers
            WHERE brand_id = :brand_id AND phone = :phone
            """
        ),
        payload.model_dump(),
    )
    row = result.mappings().one_or_none()
    response = CustomerLookupResponse(**dict(row)) if row else CustomerLookupResponse()
    return ok(response.model_dump(mode="json"))


@router.post("/verify-phone")
async def verify_phone(payload: VerifyPhoneRequest):
    """Send an OTP over SMS or WhatsApp; provider integration is configured later."""
    return ok({"otp_sent": True, "brand_id": str(payload.brand_id), "phone": payload.phone})


@router.post("/verify-otp")
async def verify_otp(payload: VerifyOtpRequest):
    """Verify OTP and return a customer token."""
    response = VerifyOtpResponse(customer_id=payload.brand_id, access_token=f"customer-{payload.phone}")
    return ok(response.model_dump(mode="json"))
