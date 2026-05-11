from datetime import datetime,timezone
import uuid
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey,Enum
from .database import Base

SCHEMA_NAME = "ekart_prod"


order_status_enum = Enum(
    "PENDING",
    "AWAITING_PAYMENT",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "REFUND_PENDING",
    "REFUNDED",
    name="order_status_enum",
    schema=SCHEMA_NAME,
    create_type=False
)


order_payment_status_enum = Enum(
    "PENDING",
    "PAID",
    "FAILED",
    "PARTIALLY_REFUNDED",
    "REFUNDED",
    name="payment_status_enum",
    schema=SCHEMA_NAME,
    create_type=False
)

payment_method_enum = Enum(
    "CASH",
    "UPI",
    "CARD",
    "WALLET",
    "BNPL",
    name="payment_method_enum",
    schema=SCHEMA_NAME,
    create_type=False
)

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": SCHEMA_NAME}

    category_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.categories.category_id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": SCHEMA_NAME}

    product_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.categories.category_id"))
    mrp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    cgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    sgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_discontinued: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    barcodes: Mapped[List["ProductBarcode"]] = relationship("ProductBarcode", back_populates="product")
    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product")


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"
    __table_args__ = {"schema": SCHEMA_NAME}

    barcode_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.products.product_id"), nullable=False)
    barcode_value: Mapped[str] = mapped_column(String(50), nullable=False)
    barcode_type: Mapped[str] = mapped_column(String(20), default="EAN13")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="barcodes")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = {"schema": SCHEMA_NAME}

    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="store")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = {"schema": SCHEMA_NAME}

    inventory_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.products.product_id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.stores.store_id"), nullable=False)
    qty_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    qty_reserved: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="inventory_records")
    store: Mapped["Store"] = relationship("Store", back_populates="inventory_records")

    @property
    def qty_available(self) -> int:
        return max(0, self.qty_on_hand - self.qty_reserved)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": SCHEMA_NAME}

    order_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.customers.customer_id"), nullable=True)
    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.stores.store_id"), nullable=False)
    status: Mapped[str] = mapped_column(order_status_enum, default="PENDING")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cgst_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    round_off: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    payment_method: Mapped[Optional[str]] = mapped_column(payment_method_enum, nullable=True)
    payment_status: Mapped[str] = mapped_column(order_payment_status_enum, default="PENDING")
    payment_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cashier_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    terminal_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped[Optional["customers"]] = relationship("customers")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": SCHEMA_NAME}

    item_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.orders.order_id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    sgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")

class customers(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": SCHEMA_NAME}

    customer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(20), default="STANDARD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)