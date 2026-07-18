from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import Device, DeviceTerminalAssignment, Store, Terminal
from ..schemas_terminal import AdminDeactivateTerminalRequest
from ..services.audit import write_audit_log
from ._admin_common import require_brand_access

router = APIRouter(prefix="/api/v1/admin/terminals", tags=["admin-terminals"])


@router.post("/{terminal_id}/deactivate")
async def deactivate_terminal(
    terminal_id: UUID,
    payload: AdminDeactivateTerminalRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retire a checkout lane. Any device actively holding this terminal is
    freed back to UNASSIGNED (not DISABLED - the phone isn't broken, it
    just needs reassignment) so it naturally re-enters the pairing-code
    flow next time it registers/polls."""
    result = await db.execute(
        select(Terminal, Store.brand_id)
        .join(Store, Store.store_id == Terminal.store_id)
        .where(Terminal.terminal_id == terminal_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Terminal not found"})
    terminal, brand_id = row
    require_brand_access(admin, brand_id)
    if terminal.deactivated_at is not None:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Terminal is already deactivated"})

    # Lock the store row - same lock target assign_store takes - so a
    # concurrent assign-store call for this store can't land a fresh
    # assignment on this terminal in the instant it's being retired.
    await db.execute(select(Store).where(Store.store_id == terminal.store_id).with_for_update())

    now = datetime.utcnow()
    terminal.deactivated_at = now
    terminal.is_active = False

    revoke_result = await db.execute(
        update(DeviceTerminalAssignment)
        .where(DeviceTerminalAssignment.terminal_id == terminal_id, DeviceTerminalAssignment.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="TERMINAL_DEACTIVATED")
        .returning(DeviceTerminalAssignment.device_id)
    )
    freed_device_ids = [row[0] for row in revoke_result.all()]
    if freed_device_ids:
        await db.execute(
            update(Device).where(Device.device_id.in_(freed_device_ids)).values(status="UNASSIGNED")
        )

    await write_audit_log(
        db,
        event_type="TERMINAL_DEACTIVATED",
        entity_type="terminal",
        entity_id=terminal_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=payload.reason,
    )
    return ok({"deactivated": True})
