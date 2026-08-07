from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api_response import ok
from ..models import Brand
from ..schemas_terminal import BrandResponse

router = APIRouter(tags=["brands"])


@router.get("/api/v1/brands")
async def list_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.is_active == True))  # noqa: E712
    brands = result.scalars().all()
    return ok([BrandResponse.model_validate(b, from_attributes=True).model_dump(mode="json") for b in brands])
