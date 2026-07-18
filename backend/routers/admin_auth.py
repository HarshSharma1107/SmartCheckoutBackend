from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, create_admin_access_token, hash_password, require_admin, verify_password
from ..config import ADMIN_ACCESS_TOKEN_TTL_SECONDS
from ..database import get_db
from ..errors import ErrorCode
from ..models import AdminUser
from ..schemas_terminal import AdminBootstrapRequest, AdminLoginRequest, AdminLoginResponse

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])


@router.post("/bootstrap")
async def bootstrap_admin(payload: AdminBootstrapRequest, db: AsyncSession = Depends(get_db)):
    """Create the first admin account. Only works while `admin_users` is
    empty - this is intentionally a one-time door, not a public signup
    endpoint. Once your first admin exists, use `/login`, and have that
    admin create any further accounts via `POST /admin/auth/users`."""
    count_result = await db.execute(select(func.count()).select_from(AdminUser))
    if count_result.scalar_one() > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.CONFLICT,
                "message": "An admin already exists. Use /login, or have an existing admin create your account.",
            },
        )

    admin = AdminUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="SUPER_ADMIN",
        brand_id=payload.brand_id,
    )
    db.add(admin)
    await db.flush()

    access_token = create_admin_access_token(admin.admin_id, admin.role, admin.brand_id)
    return ok(
        AdminLoginResponse(
            access_token=access_token,
            expires_in=ADMIN_ACCESS_TOKEN_TTL_SECONDS,
            admin_id=admin.admin_id,
            role=admin.role,
            brand_id=admin.brand_id,
        ).model_dump(mode="json")
    )


@router.post("/login")
async def login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminUser).where(AdminUser.email == payload.email))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid email or password"})

    admin.last_login_at = datetime.utcnow()
    access_token = create_admin_access_token(admin.admin_id, admin.role, admin.brand_id)
    return ok(
        AdminLoginResponse(
            access_token=access_token,
            expires_in=ADMIN_ACCESS_TOKEN_TTL_SECONDS,
            admin_id=admin.admin_id,
            role=admin.role,
            brand_id=admin.brand_id,
        ).model_dump(mode="json")
    )


@router.post("/users")
async def create_admin_user(
    payload: AdminBootstrapRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Let an existing SUPER_ADMIN create further admin accounts, once the
    dashboard exists to call this. STORE_ADMIN accounts created this way are
    scoped to `brand_id` from the request."""
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Only SUPER_ADMIN can create admins"})

    existing = await db.execute(select(AdminUser).where(AdminUser.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Email already registered"})

    new_admin = AdminUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="STORE_ADMIN" if payload.brand_id else "SUPER_ADMIN",
        brand_id=payload.brand_id,
    )
    db.add(new_admin)
    await db.flush()
    return ok({"admin_id": str(new_admin.admin_id), "role": new_admin.role})
