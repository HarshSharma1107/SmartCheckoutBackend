from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Brand, Store

router = APIRouter(prefix="/api/v1", tags=["stores"])

@router.get("/stores")
async def list_stores(brand_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    # brand_id is optional for backward compatibility with existing app
    # builds that call this with no query params at all.
    stmt = select(Store, Brand.name).join(Brand, Brand.brand_id == Store.brand_id).where(Store.is_active == True)  # noqa: E712
    if brand_id:
        stmt = stmt.where(Store.brand_id == brand_id)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "store_id": str(s.store_id),
            "code": s.code,
            "name": s.name,
            "city": s.city,
            "brand_id": str(s.brand_id),
            "brand_name": brand_name,
        }
        for s, brand_name in rows
    ]
