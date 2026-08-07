import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class ProductResponse(BaseModel):
    product_id: str
    sku: str
    name: str
    brand: Optional[str]
    mrp: float
    selling_price: float
    cgst_rate: float
    sgst_rate: float
    tax_rate: float
    qty_available: int
    category_name: Optional[str]
    in_stock: bool
    expiry_date: Optional[str] = None

    class Config:
        from_attributes = True


class BarcodeScannedResponse(BaseModel):
    found: bool
    barcode: str
    product: Optional[ProductResponse] = None
    error: Optional[str] = None

class CartItemIn(BaseModel):
    product_id: str
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def qty_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

class OrderItemResponse(BaseModel):
    item_id: str
    product_id: str
    product_name: str
    sku: str
    quantity: int
    unit_price: float
    mrp: float
    discount_amount: float
    cgst_amount: float
    sgst_amount: float
    line_total: float

class OrderCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str
    store_id: str
    items: List[CartItemIn]
    payment_method: str = "CASH"
    # Optional client-generated key (one per checkout attempt) used to make
    # a retried/double-submitted request return the original order instead
    # of creating a duplicate. store_id itself is informational only now -
    # the authoritative store comes from the authenticated device's active
    # terminal assignment (see routers/orders.py create_order).
    idempotency_key: Optional[str] = Field(default=None, max_length=100)

    @field_validator("customer_phone")
    @classmethod
    def phone_must_be_valid(cls, v):
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return v

    @field_validator("customer_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Customer name cannot be empty")
        return v.strip()

    @field_validator("customer_email")
    @classmethod
    def email_must_be_valid(cls, v):
        v = v.strip()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v



class OrderResponse(BaseModel):
    order_id: str
    order_number: str
    customer_name: str
    customer_phone: str
    customer_email: str
    status: str
    subtotal: float
    discount_total: float
    cgst_total: float
    sgst_total: float
    grand_total: float
    payment_method: Optional[str]
    payment_status: str
    ordered_at: str
    completed_at: Optional[str]
    items: List[OrderItemResponse]


class PaymentRequest(BaseModel):
    order_id: str
    payment_method: str
    amount_paid: float