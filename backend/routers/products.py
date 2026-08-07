import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import DevicePrincipal, require_device
from ..database import get_db
from ..errors import ErrorCode
from ..models import Product, ProductBarcode, Category, Inventory
from ..schemas import BarcodeScannedResponse, ProductResponse
from ..services.terminal import get_active_assignment

router = APIRouter(prefix="/api/v1", tags=["products"])


async def _resolve_device_store_id(db: AsyncSession, principal: DevicePrincipal):
    """The scanning/shopping flow only ever runs on an already-assigned
    device, so its own active terminal assignment is the sole source of
    truth for which store's inventory it can see - a client-supplied
    store_id is never trusted (that was the gap that let any caller who
    knew a store_id query/act on a store its device wasn't assigned to)."""
    assignment_row = await get_active_assignment(db, uuid.UUID(principal.device_id))
    if assignment_row is None:
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": "Device is not assigned to a store"},
        )
    _assignment, _terminal, store, _brand = assignment_row
    return store.store_id


@router.get("/scan/{barcode}", response_model=BarcodeScannedResponse)
async def scan_barcode(
    barcode: str,
    principal: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    barcode = barcode.strip()
    if not barcode:
        raise HTTPException(status_code=400, detail={"code": ErrorCode.VALIDATION_ERROR, "message": "Barcode cannot be empty"})

    store_uuid = await _resolve_device_store_id(db, principal)

    stmt = select(ProductBarcode).where(ProductBarcode.barcode_value == barcode, ProductBarcode.is_active == True)
    result = await db.execute(stmt)
    bc = result.scalar_one_or_none()

    if not bc:
        return BarcodeScannedResponse(found=False, barcode=barcode, error="Product not found. Barcode not in catalogue.")

    stmt = select(Product).where(Product.product_id == bc.product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product or not product.is_active or product.is_discontinued:
        return BarcodeScannedResponse(found=False, barcode=barcode, error="Product is discontinued or inactive.")

    if product.expiry_date and product.expiry_date < date.today():
        return BarcodeScannedResponse(found=False, barcode=barcode, error="Product is expired.")

    inv_stmt = select(Inventory).where(Inventory.product_id == product.product_id, Inventory.store_id == store_uuid)
    inv_result = await db.execute(inv_stmt)
    inventory = inv_result.scalars().first()

    qty_available = inventory.qty_available if inventory else 0

    cat_result = await db.execute(select(Category).where(Category.category_id == product.category_id))
    cat = cat_result.scalar_one_or_none()
    tax_rate = float(product.cgst_rate) + float(product.sgst_rate)

    return BarcodeScannedResponse(
        found=True,
        barcode=barcode,
        product=ProductResponse(
            product_id=str(product.product_id),
            sku=product.sku,
            name=product.name,
            brand=product.brand,
            mrp=float(product.mrp),
            selling_price=float(product.mrp),
            cgst_rate=float(product.cgst_rate),
            sgst_rate=float(product.sgst_rate),
            tax_rate=tax_rate,
            qty_available=qty_available,
            category_name=cat.name if cat else None,
            in_stock=qty_available > 0,
            expiry_date=product.expiry_date.isoformat() if product.expiry_date else None,
        )
    )
@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    principal: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": ErrorCode.VALIDATION_ERROR, "message": "Invalid product_id format"})

    store_uuid = await _resolve_device_store_id(db, principal)

    result = await db.execute(select(Product).where(Product.product_id == pid, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Product not found"})
    if product.expiry_date and product.expiry_date < date.today():
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Product is expired"})

    inv_stmt = select(Inventory).where(Inventory.product_id == pid, Inventory.store_id == store_uuid)
    inv_result = await db.execute(inv_stmt)
    inventory = inv_result.scalars().first()
    qty_available = inventory.qty_available if inventory else 0

    cat_result = await db.execute(select(Category).where(Category.category_id == product.category_id))
    cat = cat_result.scalar_one_or_none()
    tax_rate = float(product.cgst_rate) + float(product.sgst_rate)

    return ProductResponse(
        product_id=str(product.product_id),
        sku=product.sku,
        name=product.name,
        brand=product.brand,
        mrp=float(product.mrp),
        selling_price=float(product.mrp),
        cgst_rate=float(product.cgst_rate),
        sgst_rate=float(product.sgst_rate),
        tax_rate=tax_rate,
        qty_available=qty_available,
        category_name=cat.name if cat else None,
        in_stock=qty_available > 0,
        expiry_date=product.expiry_date.isoformat() if product.expiry_date else None,
    )

@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.is_active == True))
    products = result.scalars().all()
    return {"count": len(products), "products": [{"product_id": str(p.product_id), "sku": p.sku, "name": p.name, "mrp": float(p.mrp)} for p in products]}