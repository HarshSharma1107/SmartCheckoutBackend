from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BarcodeProductResponse(BaseModel):
    product_id: UUID
    sku: str
    name: str
    mrp: float
    unit_price: float
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    tax_rates: dict[str, float]
    batch_info: Optional[dict[str, Any]] = None
    inventory: dict[str, int]


class EnterpriseOrderCreateRequest(BaseModel):
    terminal_id: UUID
    store_id: UUID
    brand_id: UUID
    device_id: UUID
    customer_phone: Optional[str] = None


class EnterpriseOrderCreateResponse(BaseModel):
    order_id: UUID
    order_number: str
    status: Literal["ACTIVE"]


class OrderItemCreateRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=1, le=999)


class OrderItemUpdateRequest(BaseModel):
    quantity: int = Field(ge=1, le=999)


class OrderItemMutationResponse(BaseModel):
    item_id: UUID
    product_id: UUID
    name: str
    quantity: int
    unit_price: float
    line_total: float
    order_subtotal: float
    order_grand_total: float


class CheckoutRequest(BaseModel):
    payment_method: Literal["CASH", "UPI", "CARD", "WALLET"]
    coupon_code: Optional[str] = None
    loyalty_points_to_redeem: int = Field(default=0, ge=0)


class CheckoutResponse(BaseModel):
    payment_gateway_url: Optional[str] = None
    qr_code_data: Optional[str] = None
    grand_total: float
    razorpay_order_id: Optional[str] = None


class PaymentConfirmationRequest(BaseModel):
    gateway_order_id: str
    payment_ref: str
    status: Literal["SUCCESS", "FAILED"]
    amount: float


class CustomerLookupRequest(BaseModel):
    brand_id: UUID
    phone: str = Field(min_length=8, max_length=20)


class CustomerLookupResponse(BaseModel):
    customer_id: Optional[UUID] = None
    name: Optional[str] = None
    loyalty_points: int = 0
    tier: str = "STANDARD"
    whatsapp_opt_in: bool = False
    recent_orders: list[dict[str, Any]] = Field(default_factory=list)


class VerifyPhoneRequest(BaseModel):
    brand_id: UUID
    phone: str


class VerifyOtpRequest(BaseModel):
    brand_id: UUID
    phone: str
    otp: str = Field(min_length=4, max_length=8)

class VerifyOtpResponse(BaseModel):
    customer_id: UUID
    access_token: str
