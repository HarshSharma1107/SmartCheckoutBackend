from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Store

router = APIRouter(prefix="/api/v1", tags=["stores"])

@router.get("/stores")
async def list_stores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = result.scalars().all()
    return [{"store_id": str(s.store_id), "code": s.code, "name": s.name, "city": s.city} for s in stores]
    