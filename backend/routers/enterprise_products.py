from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import DevicePrincipal, require_device
from ..database import get_db
from ..errors import ErrorCode
from ..schemas_enterprise import BarcodeProductResponse

router = APIRouter(prefix="/api/v1/products", tags=["enterprise-products"])


@router.get("/barcode/{barcode_value}")
async def get_product_by_barcode(
    barcode_value: str,
    store_id: UUID = Query(...),
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a scanned barcode to a sellable product and store inventory."""
    result = await db.execute(
        text(
            """
            SELECT p.product_id, p.sku, p.name, p.brand, p.mrp,
                   p.cgst_rate, p.sgst_rate, c.name AS category_name,
                   COALESCE(i.qty_on_hand - i.qty_reserved, 0) AS qty_available
            FROM ekart_prod.product_barcodes pb
            JOIN ekart_prod.products p ON p.product_id = pb.product_id
            LEFT JOIN ekart_prod.categories c ON c.category_id = p.category_id
            LEFT JOIN ekart_prod.inventory i
              ON i.product_id = p.product_id AND i.store_id = :store_id
            WHERE pb.barcode_value = :barcode_value
              AND pb.is_active = true
              AND p.is_active = true
              AND p.is_discontinued = false
            LIMIT 1
            """
        ),
        {"barcode_value": barcode_value, "store_id": store_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Barcode not found"})
    response = BarcodeProductResponse(
        product_id=row["product_id"],
        sku=row["sku"],
        name=row["name"],
        mrp=float(row["mrp"]),
        unit_price=float(row["mrp"]),
        brand=row["brand"],
        category=row["category_name"],
        tax_rates={"cgst": float(row["cgst_rate"]), "sgst": float(row["sgst_rate"])},
        batch_info=None,
        inventory={"qty_available": int(row["qty_available"] or 0)},
    )
    return ok(response.model_dump(mode="json"))

