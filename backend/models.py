from datetime import datetime
import uuid
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey,func
from .database import Base



class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]              = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    is_active: Mapped[bool]        = mapped_column(Boolean, default=True)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")



class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[uuid.UUID]   = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str]                = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str]               = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]]    = mapped_column(String(200), nullable=True)
    category_id: Mapped[uuid.UUID]  = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.category_id"))
    mrp: Mapped[Decimal]            = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    cgst_rate: Mapped[Decimal]      = mapped_column(Numeric(5, 2), default=Decimal("0"))
    sgst_rate: Mapped[Decimal]      = mapped_column(Numeric(5, 2), default=Decimal("0"))
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True)
    is_discontinued: Mapped[bool]   = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]    = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime]    = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category"]    = relationship("Category", back_populates="products")
    barcodes: Mapped[List["ProductBarcode"]] = relationship("ProductBarcode", back_populates="product")
    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="product")



class ProductBarcode(Base):
    __tablename__ = "product_barcodes"

    barcode_id: Mapped[uuid.UUID]   = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]   = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    barcode_value: Mapped[str]      = mapped_column(String(50), nullable=False)
    barcode_type: Mapped[str]       = mapped_column(String(20), default="EAN13")
    is_primary: Mapped[bool]        = mapped_column(Boolean, default=False)
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]    = mapped_column(default=datetime.utcnow)

    product: Mapped["Product"]      = relationship("Product", back_populates="barcodes")



class Store(Base):
    __tablename__ = "stores"

    store_id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str]               = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str]               = mapped_column(String(200), nullable=False)
    city: Mapped[Optional[str]]     = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True)

    inventory_records: Mapped[List["Inventory"]] = relationship("Inventory", back_populates="store")


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]   = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    store_id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False)
    qty_on_hand: Mapped[int]        = mapped_column(Integer, default=0)
    qty_reserved: Mapped[int]       = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime]  = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"]      = relationship("Product", back_populates="inventory_records")
    store: Mapped["Store"]          = relationship("Store", back_populates="inventory_records")

    @property
    def qty_available(self) -> int:
        return max(0, self.qty_on_hand - self.qty_reserved)




class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str]       = mapped_column(String(50), unique=True, nullable=False)
    customer_name: Mapped[str]      = mapped_column(String(200), nullable=False)
    customer_phone: Mapped[str]     = mapped_column(String(20), nullable=False)
    store_id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False)
    status: Mapped[str]             = mapped_column(String(30), default="PENDING")
    subtotal: Mapped[Decimal]       = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cgst_total: Mapped[Decimal]     = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_total: Mapped[Decimal]     = mapped_column(Numeric(12, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal]    = mapped_column(Numeric(12, 2), default=Decimal("0"))
    payment_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    payment_status: Mapped[str]     = mapped_column(String(30), default="PENDING")
    ordered_at: Mapped[datetime]    = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

  


class OrderItem(Base):
    __tablename__ = "order_items"

    item_id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.order_id"), nullable=False)
    product_id: Mapped[uuid.UUID]   = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int]           = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal]     = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Decimal]            = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cgst_rate: Mapped[Decimal]      = mapped_column(Numeric(5, 2), default=Decimal("0"))
    cgst_amount: Mapped[Decimal]    = mapped_column(Numeric(10, 2), default=Decimal("0"))
    sgst_rate: Mapped[Decimal]      = mapped_column(Numeric(5, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal]    = mapped_column(Numeric(10, 2), default=Decimal("0"))
    line_total: Mapped[Decimal]     = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime]    = mapped_column(default=datetime.utcnow)

    order: Mapped["Order"]          = relationship("Order", back_populates="items")
    product: Mapped["Product"]      = relationship("Product")

