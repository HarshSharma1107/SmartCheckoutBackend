from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategoryResponse(BaseModel):
    category_id: UUID
    name: str
    parent_id: Optional[UUID] = None
    is_active: bool


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Product barcodes
# ---------------------------------------------------------------------------


class ProductBarcodeResponse(BaseModel):
    barcode_id: UUID
    product_id: UUID
    barcode_value: str
    barcode_type: str
    is_primary: bool
    is_active: bool
    created_at: datetime


class ProductBarcodeCreateRequest(BaseModel):
    barcode_value: str = Field(min_length=1, max_length=50)
    barcode_type: str = Field(default="EAN13", max_length=20)
    is_primary: bool = False


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class ProductAdminResponse(BaseModel):
    product_id: UUID
    sku: str
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category_id: UUID
    category_name: Optional[str] = None
    mrp: Decimal
    cost_price: Optional[Decimal] = None
    cgst_rate: Decimal
    sgst_rate: Decimal
    is_active: bool
    is_discontinued: bool
    created_at: datetime
    updated_at: datetime
    barcodes: list[ProductBarcodeResponse] = []


class ProductCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    brand: Optional[str] = Field(default=None, max_length=200)
    category_id: UUID
    mrp: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    cost_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    cgst_rate: Decimal = Field(ge=0, max_digits=5, decimal_places=2)
    sgst_rate: Decimal = Field(ge=0, max_digits=5, decimal_places=2)


class ProductUpdateRequest(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=100)
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    brand: Optional[str] = Field(default=None, max_length=200)
    category_id: Optional[UUID] = None
    mrp: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    cost_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    cgst_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=5, decimal_places=2)
    sgst_rate: Optional[Decimal] = Field(default=None, ge=0, max_digits=5, decimal_places=2)
    is_active: Optional[bool] = None
    is_discontinued: Optional[bool] = None


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


class InventoryRowResponse(BaseModel):
    inventory_id: UUID
    product_id: UUID
    store_id: UUID
    sku: str
    product_name: str
    qty_on_hand: int
    qty_reserved: int
    qty_available: int
    last_updated: datetime


class InventoryAdjustRequest(BaseModel):
    delta: int = Field(description="Positive to add stock, negative to remove")


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
