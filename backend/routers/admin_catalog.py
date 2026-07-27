from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import (
    AdminUser,
    Brand,
    Category,
    Device,
    DeviceTerminalAssignment,
    Inventory,
    Product,
    ProductBarcode,
    Store,
    Terminal,
)
from ..schemas_catalog import (
    AdminTerminalListItem,
    AdminUserListItem,
    CategoryCreateRequest,
    CategoryResponse,
    InventoryAdjustRequest,
    InventoryRowResponse,
    ProductAdminResponse,
    ProductBarcodeCreateRequest,
    ProductBarcodeResponse,
    ProductCreateRequest,
    ProductUpdateRequest,
)
from ..services.audit import write_audit_log
from ._admin_common import require_brand_access

router = APIRouter(tags=["admin-catalog"])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/categories")
async def list_categories(
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return ok([CategoryResponse.model_validate(c, from_attributes=True).model_dump(mode="json") for c in categories])


@router.post("/api/v1/admin/categories")
async def create_category(
    payload: CategoryCreateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.parent_id is not None:
        parent_result = await db.execute(select(Category).where(Category.category_id == payload.parent_id))
        if parent_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Parent category not found"})

    category = Category(name=payload.name, parent_id=payload.parent_id)
    db.add(category)
    await db.flush()
    return ok(CategoryResponse.model_validate(category, from_attributes=True).model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def _product_to_response(product: Product, category_name: str | None, barcodes: list[ProductBarcode] | None = None) -> dict:
    return ProductAdminResponse(
        product_id=product.product_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        brand=product.brand,
        category_id=product.category_id,
        category_name=category_name,
        mrp=product.mrp,
        cost_price=product.cost_price,
        cgst_rate=product.cgst_rate,
        sgst_rate=product.sgst_rate,
        is_active=product.is_active,
        is_discontinued=product.is_discontinued,
        created_at=product.created_at,
        updated_at=product.updated_at,
        barcodes=[ProductBarcodeResponse.model_validate(b, from_attributes=True) for b in (barcodes or [])],
    ).model_dump(mode="json")


async def _active_barcodes_by_product(db: AsyncSession, product_ids: list[UUID]) -> dict[UUID, list[ProductBarcode]]:
    if not product_ids:
        return {}
    result = await db.execute(
        select(ProductBarcode)
        .where(ProductBarcode.product_id.in_(product_ids), ProductBarcode.is_active == True)  # noqa: E712
        .order_by(ProductBarcode.created_at)
    )
    grouped: dict[UUID, list[ProductBarcode]] = {}
    for barcode in result.scalars().all():
        grouped.setdefault(barcode.product_id, []).append(barcode)
    return grouped


@router.get("/api/v1/admin/products")
async def list_products_admin(
    category_id: UUID | None = None,
    search: str | None = None,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Products are not brand-scoped today (no brand_id column on Product) -
    # open to any admin role, per mainadmin.md §6.
    stmt = select(Product, Category.name).outerjoin(Category, Category.category_id == Product.category_id)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    stmt = stmt.order_by(Product.name)

    result = await db.execute(stmt)
    rows = result.all()
    barcodes_by_product = await _active_barcodes_by_product(db, [product.product_id for product, _ in rows])
    return ok(
        [
            _product_to_response(product, category_name, barcodes_by_product.get(product.product_id, []))
            for product, category_name in rows
        ]
    )


@router.post("/api/v1/admin/products")
async def create_product(
    payload: ProductCreateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    category_result = await db.execute(select(Category).where(Category.category_id == payload.category_id))
    if category_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Category not found"})

    existing = await db.execute(select(Product).where(Product.sku == payload.sku))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "SKU already exists"})

    product = Product(
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        brand=payload.brand,
        category_id=payload.category_id,
        mrp=payload.mrp,
        cost_price=payload.cost_price,
        cgst_rate=payload.cgst_rate,
        sgst_rate=payload.sgst_rate,
    )
    db.add(product)
    await db.flush()

    await write_audit_log(
        db,
        event_type="PRODUCT_CREATED",
        entity_type="product",
        entity_id=product.product_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=f"sku={product.sku}",
    )

    category = await db.get(Category, product.category_id)
    return ok(_product_to_response(product, category.name if category else None))


@router.patch("/api/v1/admin/products/{product_id}")
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(select(Product).where(Product.product_id == product_id))
    product = product_result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Product not found"})

    updates = payload.model_dump(exclude_unset=True)

    if "sku" in updates and updates["sku"] != product.sku:
        existing = await db.execute(select(Product).where(Product.sku == updates["sku"], Product.product_id != product_id))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "SKU already exists"})

    if "category_id" in updates:
        category_result = await db.execute(select(Category).where(Category.category_id == updates["category_id"]))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Category not found"})

    for field, value in updates.items():
        setattr(product, field, value)
    await db.flush()

    await write_audit_log(
        db,
        event_type="PRODUCT_UPDATED",
        entity_type="product",
        entity_id=product.product_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=",".join(updates.keys()),
    )

    category = await db.get(Category, product.category_id)
    barcodes_by_product = await _active_barcodes_by_product(db, [product.product_id])
    return ok(_product_to_response(product, category.name if category else None, barcodes_by_product.get(product.product_id, [])))


# ---------------------------------------------------------------------------
# Product barcodes
# ---------------------------------------------------------------------------


@router.post("/api/v1/admin/products/{product_id}/barcodes")
async def add_product_barcode(
    product_id: UUID,
    payload: ProductBarcodeCreateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(select(Product).where(Product.product_id == product_id))
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Product not found"})

    existing = await db.execute(select(ProductBarcode).where(ProductBarcode.barcode_value == payload.barcode_value))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Barcode already registered"})

    if payload.is_primary:
        await db.execute(
            update(ProductBarcode)
            .where(ProductBarcode.product_id == product_id)
            .values(is_primary=False)
        )

    barcode = ProductBarcode(
        product_id=product_id,
        barcode_value=payload.barcode_value,
        barcode_type=payload.barcode_type,
        is_primary=payload.is_primary,
    )
    db.add(barcode)
    await db.flush()
    return ok(ProductBarcodeResponse.model_validate(barcode, from_attributes=True).model_dump(mode="json"))


@router.delete("/api/v1/admin/products/{product_id}/barcodes/{barcode_id}")
async def delete_product_barcode(
    product_id: UUID,
    barcode_id: UUID,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductBarcode).where(ProductBarcode.barcode_id == barcode_id, ProductBarcode.product_id == product_id)
    )
    barcode = result.scalar_one_or_none()
    if barcode is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Barcode not found"})

    # Soft-delete, per mainadmin.md §6 - keeps barcode history intact.
    barcode.is_active = False
    await db.flush()
    return ok({"deleted": True})


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/inventory")
async def list_inventory(
    store_id: UUID = Query(...),
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    store_result = await db.execute(select(Store).where(Store.store_id == store_id))
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Store not found"})
    require_brand_access(admin, store.brand_id)

    result = await db.execute(
        select(Inventory, Product.sku, Product.name)
        .join(Product, Product.product_id == Inventory.product_id)
        .where(Inventory.store_id == store_id)
        .order_by(Product.name)
    )
    rows = result.all()
    return ok(
        [
            InventoryRowResponse(
                inventory_id=inv.inventory_id,
                product_id=inv.product_id,
                store_id=inv.store_id,
                sku=sku,
                product_name=name,
                qty_on_hand=inv.qty_on_hand,
                qty_reserved=inv.qty_reserved,
                qty_available=inv.qty_available,
                last_updated=inv.last_updated,
            ).model_dump(mode="json")
            for inv, sku, name in rows
        ]
    )


@router.patch("/api/v1/admin/inventory/{inventory_id}")
async def adjust_inventory(
    inventory_id: UUID,
    payload: InventoryAdjustRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Inventory).where(Inventory.inventory_id == inventory_id).with_for_update())
    inventory = result.scalar_one_or_none()
    if inventory is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Inventory row not found"})

    store_result = await db.execute(select(Store).where(Store.store_id == inventory.store_id))
    store = store_result.scalar_one_or_none()
    require_brand_access(admin, store.brand_id)

    new_qty = inventory.qty_on_hand + payload.delta
    if new_qty < 0:
        raise HTTPException(
            status_code=409,
            detail={"code": ErrorCode.CONFLICT, "message": "Adjustment would take stock on hand below zero"},
        )
    inventory.qty_on_hand = new_qty
    await db.flush()

    await write_audit_log(
        db,
        event_type="INVENTORY_ADJUSTED",
        entity_type="inventory",
        entity_id=inventory.inventory_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=f"delta={payload.delta} new_qty_on_hand={new_qty}",
    )

    product_result = await db.execute(select(Product.sku, Product.name).where(Product.product_id == inventory.product_id))
    sku, name = product_result.one()
    return ok(
        InventoryRowResponse(
            inventory_id=inventory.inventory_id,
            product_id=inventory.product_id,
            store_id=inventory.store_id,
            sku=sku,
            product_name=name,
            qty_on_hand=inventory.qty_on_hand,
            qty_reserved=inventory.qty_reserved,
            qty_available=inventory.qty_available,
            last_updated=inventory.last_updated,
        ).model_dump(mode="json")
    )


# ---------------------------------------------------------------------------
# Terminals (list)
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/terminals")
async def list_terminals(
    store_id: UUID = Query(...),
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    store_result = await db.execute(select(Store).where(Store.store_id == store_id))
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Store not found"})
    require_brand_access(admin, store.brand_id)

    result = await db.execute(
        select(Terminal, Device.device_id, Device.device_name, Device.last_seen_at)
        .outerjoin(
            DeviceTerminalAssignment,
            (DeviceTerminalAssignment.terminal_id == Terminal.terminal_id) & (DeviceTerminalAssignment.revoked_at.is_(None)),
        )
        .outerjoin(Device, Device.device_id == DeviceTerminalAssignment.device_id)
        .where(Terminal.store_id == store_id)
        .order_by(Terminal.terminal_code)
    )
    rows = result.all()

    online_cutoff = datetime.utcnow() - timedelta(seconds=90)
    items = []
    for terminal, device_id, device_name, last_seen_at in rows:
        items.append(
            AdminTerminalListItem(
                terminal_id=terminal.terminal_id,
                store_id=terminal.store_id,
                terminal_code=terminal.terminal_code,
                label=terminal.label,
                is_active=terminal.is_active,
                deactivated_at=terminal.deactivated_at,
                created_at=terminal.created_at,
                device_id=device_id,
                device_name=device_name,
                is_online=bool(device_id and last_seen_at and last_seen_at >= online_cutoff),
            ).model_dump(mode="json")
        )
    return ok(items)


# ---------------------------------------------------------------------------
# Admin users (list)
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/admins")
async def list_admins(
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Only SUPER_ADMIN can list admin accounts"})

    result = await db.execute(
        select(AdminUser, Brand.name).outerjoin(Brand, Brand.brand_id == AdminUser.brand_id).order_by(AdminUser.created_at)
    )
    rows = result.all()
    return ok(
        [
            AdminUserListItem(
                admin_id=a.admin_id,
                email=a.email,
                full_name=a.full_name,
                role=a.role,
                brand_id=a.brand_id,
                brand_name=brand_name,
                is_active=a.is_active,
                last_login_at=a.last_login_at,
                created_at=a.created_at,
            ).model_dump(mode="json")
            for a, brand_name in rows
        ]
    )
