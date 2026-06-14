from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..schemas_enterprise import AdminAssignDeviceRequest, AdminAssignDeviceResponse, AdminRevokeDeviceRequest
from ..services.audit import write_audit_log

router = APIRouter(prefix="/api/v1/admin/devices", tags=["enterprise-admin-devices"])


@router.post("/{device_id}/assign")
async def assign_device(
    device_id: UUID,
    payload: AdminAssignDeviceRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign a physical Pi to a logical terminal, closing previous assignment history."""
    terminal = await db.execute(
        text(
            """
            SELECT t.terminal_id, t.store_id, s.brand_id
            FROM ekart_prod.terminals t
            JOIN ekart_prod.stores s ON s.store_id = t.store_id
            WHERE t.terminal_id = :terminal_id
            """
        ),
        {"terminal_id": payload.terminal_id},
    )
    terminal_row = terminal.mappings().one_or_none()
    if not terminal_row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Terminal not found"})

    active_terminal = await db.execute(
        text(
            """
            SELECT assignment_id
            FROM ekart_prod.device_terminal_assignments
            WHERE terminal_id = :terminal_id AND revoked_at IS NULL
            """
        ),
        {"terminal_id": payload.terminal_id},
    )
    if active_terminal.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Terminal already has an active device"})

    await db.execute(
        text(
            """
            UPDATE ekart_prod.device_terminal_assignments
            SET revoked_at = now(), revoke_reason = 'REASSIGNED'
            WHERE device_id = :device_id AND revoked_at IS NULL
            """
        ),
        {"device_id": device_id},
    )
    result = await db.execute(
        text(
            """
            INSERT INTO ekart_prod.device_terminal_assignments (
                device_id, terminal_id, assigned_by
            )
            VALUES (:device_id, :terminal_id, :assigned_by)
            RETURNING assignment_id, assigned_at
            """
        ),
        {"device_id": device_id, "terminal_id": payload.terminal_id, "assigned_by": admin.admin_id},
    )
    row = result.mappings().one()
    await write_audit_log(
        db,
        event_type="DEVICE_ASSIGNED",
        entity_type="device",
        entity_id=device_id,
        brand_id=terminal_row["brand_id"],
        store_id=terminal_row["store_id"],
        actor_id=UUID(admin.admin_id),
        actor_type="admin",
        payload={"terminal_id": str(payload.terminal_id), "notes": payload.notes},
    )
    response = AdminAssignDeviceResponse(assignment_id=row["assignment_id"], assigned_at=row["assigned_at"])
    return ok(response.model_dump(mode="json"))


@router.post("/{device_id}/revoke")
async def revoke_device(
    device_id: UUID,
    payload: AdminRevokeDeviceRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke current assignment and place the device back into provisioned state."""
    await db.execute(
        text(
            """
            UPDATE ekart_prod.device_terminal_assignments
            SET revoked_at = now(), revoke_reason = :reason
            WHERE device_id = :device_id AND revoked_at IS NULL
            """
        ),
        {"device_id": device_id, "reason": payload.reason},
    )
    await db.execute(
        text("UPDATE ekart_prod.devices SET status='PROVISIONED', updated_at=now() WHERE device_id=:device_id"),
        {"device_id": device_id},
    )
    await write_audit_log(
        db,
        event_type="DEVICE_REVOKED",
        entity_type="device",
        entity_id=device_id,
        actor_id=UUID(admin.admin_id),
        actor_type="admin",
        payload={"reason": payload.reason, "mqtt_action": "INVALIDATE_CONFIG"},
    )
    return ok({"revoked": True, "mqtt_topic": f"ekart/device/{device_id}/commands"})
