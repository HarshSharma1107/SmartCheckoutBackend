import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, ProductBarcode, Category, Inventory
from ..schemas import BarcodeScannedResponse, ProductResponse

router = APIRouter(prefix="/api/v1", tags=["products"])

@router.get("/scan/{barcode}", response_model=BarcodeScannedResponse)
async def scan_barcode(barcode: str, store_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    barcode = barcode.strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode cannot be empty")

    # Look up barcode
    stmt = select(ProductBarcode).where(ProductBarcode.barcode_value == barcode, ProductBarcode.is_active == True)
    result = await db.execute(stmt)
    bc = result.scalar_one_or_none()

    if not bc:
        return BarcodeScannedResponse(found=False, barcode=barcode, error="Product not found. Barcode not in catalogue.")

    # Get product
    stmt = select(Product).where(Product.product_id == bc.product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product or not product.is_active or product.is_discontinued:
        return BarcodeScannedResponse(found=False, barcode=barcode, error="Product is discontinued or inactive.")

    # Get inventory – use .first() to avoid MultipleResultsFound
    inv_stmt = select(Inventory).where(Inventory.product_id == product.product_id)
    if store_id:
        try:
            store_uuid = uuid.UUID(store_id)
            inv_stmt = inv_stmt.where(Inventory.store_id == store_uuid)
        except ValueError:
            pass
    inv_result = await db.execute(inv_stmt)
    inventory = inv_result.scalars().first()   # ✅ FIX: take first if multiple

    qty_available = inventory.qty_available if inventory else 0

    # Get category name
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
        )
    )
@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, store_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    result = await db.execute(select(Product).where(Product.product_id == pid, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    inv_stmt = select(Inventory).where(Inventory.product_id == pid)
    if store_id:
        try:
            inv_stmt = inv_stmt.where(Inventory.store_id == uuid.UUID(store_id))
        except ValueError:
            pass
    inv_result = await db.execute(inv_stmt)
    inventory = inv_result.scalar_one_or_none()
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
    )

@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.is_active == True))
    products = result.scalars().all()
    return {"count": len(products), "products": [{"product_id": str(p.product_id), "sku": p.sku, "name": p.name, "mrp": float(p.mrp)} for p in products]}