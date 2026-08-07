from datetime import date, datetime, timezone
import uuid
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Boolean, Date, Text, ForeignKey, Enum, Index, UniqueConstraint, text
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

# product_barcodes.barcode_type is a Postgres enum in the live DB (not a
# plain varchar) - this must match the SmartCheckoutAdmin backend's
# admin_backend/routers/admin_products.py ProductBarcodeCreateRequest.barcode_type
# default and accepted values (that service owns barcode CRUD now).
barcode_type_enum = Enum(
    "EAN13",
    "EAN8",
    "UPC_A",
    "QR_CODE",
    "ITF14",
    "INTERNAL",
    "QR",
    "CODE128",
    name="barcode_type_enum",
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
    # Single expiry date per product (not per-batch/lot) - see products.py's
    # scan_barcode, which rejects a scan once this date has passed, same as
    # a Walmart POS blocking an expired SKU at checkout.
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    barcodes: Mapped[List["ProductBarcode"]] = relationship("ProductBarcode", back_populates="product")
    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product")


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"
    __table_args__ = (
        Index("ix_product_barcodes_barcode_value", "barcode_value"),
        {"schema": SCHEMA_NAME},
    )

    barcode_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.products.product_id"), nullable=False)
    barcode_value: Mapped[str] = mapped_column(String(50), nullable=False)
    barcode_type: Mapped[str] = mapped_column(barcode_type_enum, default="EAN13")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="barcodes")


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = {"schema": SCHEMA_NAME}

    brand_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    stores: Mapped[List["Store"]] = relationship("Store", back_populates="brand")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("brand_id", "code", name="uq_stores_brand_code"),
        {"schema": SCHEMA_NAME},
    )

    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.brands.brand_id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="stores")
    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="store")
    terminals: Mapped[List["Terminal"]] = relationship("Terminal", back_populates="store")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        Index("ix_inventory_store_product", "store_id", "product_id"),
        {"schema": SCHEMA_NAME},
    )

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
    __table_args__ = (
        Index("ix_orders_store_id", "store_id"),
        # Lets a retried/double-submitted checkout from the same device
        # replay to the original order instead of creating a duplicate -
        # NULL idempotency_key (legacy/unkeyed orders) is excluded so it
        # never collides with itself.
        Index(
            "uq_orders_device_idempotency_key", "device_id", "idempotency_key",
            unique=True, postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": SCHEMA_NAME},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.customers.customer_id"), nullable=True)
    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.stores.store_id"), nullable=False)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.devices.device_id"), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        {"schema": SCHEMA_NAME},
    )

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


class Terminal(Base):
    """A logical checkout slot at a store. Devices are assigned to terminals,
    not the other way around, so replacing a dead phone/Pi never disturbs the
    terminal's order history — see docs/terminal-provisioning-plan.md."""

    __tablename__ = "terminals"
    __table_args__ = (
        UniqueConstraint("store_id", "terminal_code", name="uq_terminals_store_code"),
        {"schema": SCHEMA_NAME},
    )

    terminal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.stores.store_id"), nullable=False)
    terminal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    store: Mapped["Store"] = relationship("Store", back_populates="terminals")
    assignments: Mapped[List["DeviceTerminalAssignment"]] = relationship("DeviceTerminalAssignment", back_populates="terminal")


class Device(Base):
    """A physical phone/tablet/Pi. Identity is `local_install_id`, a UUID the
    app generates once and persists in secure storage. `device_type` governs
    which auth path applies (only ANDROID_APP/JWT is implemented today)."""

    __tablename__ = "devices"
    __table_args__ = (
        Index("uq_devices_local_install_id", "local_install_id", unique=True,
              postgresql_where=text("local_install_id IS NOT NULL")),
        {"schema": SCHEMA_NAME},
    )

    device_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_install_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    device_type: Mapped[str] = mapped_column(String(20), default="ANDROID_APP")
    device_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="UNASSIGNED")
    pairing_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    pairing_code_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments: Mapped[List["DeviceTerminalAssignment"]] = relationship("DeviceTerminalAssignment", back_populates="device")


class DeviceTerminalAssignment(Base):
    """Temporal history of which device serves which terminal. A partial
    unique index enforces at most one *active* (revoked_at IS NULL) row per
    device and per terminal, without blocking historical rows."""

    __tablename__ = "device_terminal_assignments"
    __table_args__ = (
        Index("uq_dta_active_device", "device_id", unique=True,
              postgresql_where=text("revoked_at IS NULL")),
        Index("uq_dta_active_terminal", "terminal_id", unique=True,
              postgresql_where=text("revoked_at IS NULL")),
        {"schema": SCHEMA_NAME},
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.devices.device_id"), nullable=False)
    terminal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.terminals.terminal_id"), nullable=False)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="assignments")
    terminal: Mapped["Terminal"] = relationship("Terminal", back_populates="assignments")


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = {"schema": SCHEMA_NAME}

    admin_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="STORE_ADMIN")
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.brands.brand_id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": SCHEMA_NAME}

    log_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), default="system")
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)