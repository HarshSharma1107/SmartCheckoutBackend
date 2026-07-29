from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Terminals (list)
# ---------------------------------------------------------------------------


class AdminTerminalListItem(BaseModel):
    terminal_id: UUID
    store_id: UUID
    terminal_code: str
    label: Optional[str] = None
    is_active: bool
    deactivated_at: Optional[datetime] = None
    created_at: datetime
    device_id: Optional[UUID] = None
    device_name: Optional[str] = None
    is_online: Optional[bool] = None


# ---------------------------------------------------------------------------
# Orders (admin monitoring)
# ---------------------------------------------------------------------------


class AdminOrderListItem(BaseModel):
    order_id: UUID
    order_number: str
    store_id: UUID
    store_name: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    payment_status: str
    payment_method: Optional[str] = None
    grand_total: Decimal
    ordered_at: datetime
    completed_at: Optional[datetime] = None


class AdminOrderItemResponse(BaseModel):
    item_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    mrp: Decimal
    discount_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    line_total: Decimal


class AdminOrderDetailResponse(BaseModel):
    order_id: UUID
    order_number: str
    store_id: UUID
    store_name: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    status: str
    subtotal: Decimal
    discount_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    grand_total: Decimal
    payment_method: Optional[str] = None
    payment_status: str
    payment_ref: Optional[str] = None
    ordered_at: datetime
    completed_at: Optional[datetime] = None
    items: list[AdminOrderItemResponse] = []


class OrderRefundRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Audit logs (list)
# ---------------------------------------------------------------------------


class AuditLogListItem(BaseModel):
    log_id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID
    actor_type: str
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: datetime


# ---------------------------------------------------------------------------
# Admin users (list)
# ---------------------------------------------------------------------------


class AdminUserListItem(BaseModel):
    admin_id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    brand_id: Optional[UUID] = None
    brand_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
