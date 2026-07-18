from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import Brand, Store
from ..schemas_terminal import BrandCreateRequest, BrandResponse, StoreCreateRequest, StoreResponse

router = APIRouter(tags=["brands"])


@router.get("/api/v1/brands")
async def list_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.is_active == True))  # noqa: E712
    brands = result.scalars().all()
    return ok([BrandResponse.model_validate(b, from_attributes=True).model_dump(mode="json") for b in brands])


@router.post("/api/v1/admin/brands")
async def create_brand(
    payload: BrandCreateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """SUPER_ADMIN only - a STORE_ADMIN is scoped to an existing brand and
    has no reason to create new ones."""
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Only SUPER_ADMIN can create brands"})

    existing = await db.execute(select(Brand).where(Brand.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Brand code already exists"})

    brand = Brand(code=payload.code, name=payload.name, logo_url=payload.logo_url)
    db.add(brand)
    await db.flush()
    return ok(BrandResponse.model_validate(brand, from_attributes=True).model_dump(mode="json"))


@router.get("/api/v1/admin/stores")
async def list_stores_admin(
    brand_id: UUID | None = None,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Store, Brand.name).join(Brand, Brand.brand_id == Store.brand_id)
    if admin.role != "SUPER_ADMIN":
        if not admin.brand_id:
            return ok([])
        stmt = stmt.where(Store.brand_id == UUID(admin.brand_id))
    elif brand_id:
        stmt = stmt.where(Store.brand_id == brand_id)

    result = await db.execute(stmt)
    rows = result.all()
    return ok(
        [
            StoreResponse(
                store_id=store.store_id,
                brand_id=store.brand_id,
                brand_name=brand_name,
                code=store.code,
                name=store.name,
                city=store.city,
                is_active=store.is_active,
            ).model_dump(mode="json")
            for store, brand_name in rows
        ]
    )


@router.post("/api/v1/admin/stores")
async def create_store(
    payload: StoreCreateRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin.role != "SUPER_ADMIN":
        if not admin.brand_id or UUID(admin.brand_id) != payload.brand_id:
            raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Not authorized for this brand"})

    brand_result = await db.execute(select(Brand).where(Brand.brand_id == payload.brand_id))
    brand = brand_result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Brand not found"})

    existing = await db.execute(
        select(Store).where(Store.brand_id == payload.brand_id, Store.code == payload.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Store code already exists for this brand"})

    store = Store(brand_id=payload.brand_id, code=payload.code, name=payload.name, city=payload.city)
    db.add(store)
    await db.flush()
    return ok(
        StoreResponse(
            store_id=store.store_id,
            brand_id=store.brand_id,
            brand_name=brand.name,
            code=store.code,
            name=store.name,
            city=store.city,
            is_active=store.is_active,
        ).model_dump(mode="json")
    )
