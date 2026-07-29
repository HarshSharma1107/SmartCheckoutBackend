from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import AdminUser, Brand, Device, DeviceTerminalAssignment, Store, Terminal
from ..schemas_catalog import AdminTerminalListItem, AdminUserListItem
from ._admin_common import require_brand_access

router = APIRouter(tags=["admin-catalog"])


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
