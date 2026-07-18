from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..config import DEVICE_ACCESS_TOKEN_TTL_SECONDS
from ..database import get_db
from ..errors import ErrorCode
from ..models import Device, DeviceTerminalAssignment, Store, Terminal
from ..routers.devices import _issue_device_tokens
from ..schemas_terminal import AdminAssignStoreRequest, AdminAssignStoreResponse, AdminDeactivateDeviceRequest, AdminDeviceListItem
from ..services.audit import write_audit_log
from ._admin_common import require_brand_access

router = APIRouter(prefix="/api/v1/admin/devices", tags=["admin-devices"])


async def _next_terminal_code(db: AsyncSession) -> str:
    seq = await db.execute(text("SELECT nextval('ekart_prod.terminal_code_seq')"))
    return f"SC-{seq.scalar_one():06d}"


@router.post("/{device_id}/assign-store")
async def assign_store(
    device_id: UUID,
    payload: AdminAssignStoreRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign an unassigned (or reassign an already-assigned) device to a
    store. Requires the pairing code shown on the physical device's pending
    screen — see docs/terminal-provisioning-plan.md section 2.1. This is
    also how a dead device gets replaced: assign the new device to the same
    store and it lands on the same terminal, preserving order history."""
    # Lock the device row up front - this is a multi-statement transaction
    # (revoke old assignments, insert new one, flip status, issue tokens),
    # so a concurrent assign-store call for the same device must fully wait
    # rather than race past these checks.
    device_result = await db.execute(select(Device).where(Device.device_id == device_id).with_for_update())
    device = device_result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Device not found"})
    if device.status == "DISABLED":
        raise HTTPException(status_code=409, detail={"code": ErrorCode.CONFLICT, "message": "Device is disabled"})
    if not device.pairing_code or device.pairing_code != payload.pairing_code:
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Pairing code does not match"})
    if not device.pairing_code_expires_at or device.pairing_code_expires_at <= datetime.utcnow():
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": "Pairing code expired - ask the device to refresh and try again"},
        )

    # Lock the store row too - closes the terminal-auto-creation race (two
    # concurrent assign-store calls for a brand-new store both deciding to
    # create a terminal) and the same-terminal assignment race. Lock order
    # is Device -> Store, matching the read order above.
    store_result = await db.execute(select(Store).where(Store.store_id == payload.store_id).with_for_update())
    store = store_result.scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Store not found"})
    require_brand_access(admin, store.brand_id)

    terminal_result = await db.execute(
        select(Terminal)
        .where(Terminal.store_id == store.store_id, Terminal.deactivated_at.is_(None))
        .order_by(Terminal.created_at)
        .limit(1)
    )
    terminal = terminal_result.scalars().first()
    if terminal is None:
        terminal_code = await _next_terminal_code(db)
        terminal = Terminal(store_id=store.store_id, terminal_code=terminal_code)
        db.add(terminal)
        await db.flush()

    now = datetime.utcnow()
    await db.execute(
        update(DeviceTerminalAssignment)
        .where(DeviceTerminalAssignment.device_id == device.device_id, DeviceTerminalAssignment.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="REASSIGNED")
    )
    await db.execute(
        update(DeviceTerminalAssignment)
        .where(DeviceTerminalAssignment.terminal_id == terminal.terminal_id, DeviceTerminalAssignment.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="REASSIGNED")
    )

    assignment = DeviceTerminalAssignment(
        device_id=device.device_id,
        terminal_id=terminal.terminal_id,
        assigned_by=UUID(admin.admin_id),
    )
    db.add(assignment)

    access_token, refresh_token = _issue_device_tokens(device)
    device.status = "ASSIGNED"
    # Pairing code is single-use - clearing it stops a second admin from
    # assigning the same physical device to a different store using a code
    # they happened to see earlier.
    device.pairing_code = None
    device.pairing_code_expires_at = None
    try:
        await db.flush()
    except IntegrityError:
        # Defense-in-depth: the Device/Store locks above should make this
        # unreachable, but don't let any future code path that mutates these
        # tables without the same locks surface a raw 500 here.
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.CONFLICT,
                "message": "This device or terminal was modified concurrently - please retry",
            },
        )

    await write_audit_log(
        db,
        event_type="DEVICE_ASSIGNED",
        entity_type="device",
        entity_id=device.device_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=f"store={store.store_id} terminal={terminal.terminal_code} notes={payload.notes or ''}",
    )

    return ok(
        AdminAssignStoreResponse(
            assignment_id=assignment.assignment_id,
            terminal_id=terminal.terminal_id,
            terminal_code=terminal.terminal_code,
            assigned_at=assignment.assigned_at,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=DEVICE_ACCESS_TOKEN_TTL_SECONDS,
        ).model_dump(mode="json")
    )


@router.post("/{device_id}/deactivate")
async def deactivate_device(
    device_id: UUID,
    payload: AdminDeactivateDeviceRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    device_result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = device_result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Device not found"})

    active = await db.execute(
        select(Store.brand_id)
        .select_from(DeviceTerminalAssignment)
        .join(Terminal, Terminal.terminal_id == DeviceTerminalAssignment.terminal_id)
        .join(Store, Store.store_id == Terminal.store_id)
        .where(DeviceTerminalAssignment.device_id == device_id, DeviceTerminalAssignment.revoked_at.is_(None))
    )
    brand_id = active.scalar_one_or_none()
    if brand_id is not None:
        require_brand_access(admin, brand_id)
    elif admin.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Not authorized"})

    await db.execute(
        update(DeviceTerminalAssignment)
        .where(DeviceTerminalAssignment.device_id == device_id, DeviceTerminalAssignment.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow(), revoke_reason=payload.reason)
    )
    device.status = "DISABLED"
    # Immediately kill any live session so a deactivated device can't keep
    # refreshing its way back into service.
    device.refresh_token_hash = None
    device.refresh_token_expires_at = None
    device.pairing_code = None
    device.pairing_code_expires_at = None

    await write_audit_log(
        db,
        event_type="DEVICE_DEACTIVATED",
        entity_type="device",
        entity_id=device_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=payload.reason,
    )
    return ok({"deactivated": True})


@router.get("")
async def list_devices(
    status: str | None = Query(default=None, pattern="^(unassigned|assigned|offline|disabled)$"),
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Device, Terminal.terminal_code, Store.name, Store.brand_id)
        .outerjoin(
            DeviceTerminalAssignment,
            (DeviceTerminalAssignment.device_id == Device.device_id) & (DeviceTerminalAssignment.revoked_at.is_(None)),
        )
        .outerjoin(Terminal, Terminal.terminal_id == DeviceTerminalAssignment.terminal_id)
        .outerjoin(Store, Store.store_id == Terminal.store_id)
    )
    if admin.role != "SUPER_ADMIN":
        if not admin.brand_id:
            return ok([])
        stmt = stmt.where(Store.brand_id == UUID(admin.brand_id))

    result = await db.execute(stmt)
    rows = result.all()

    online_cutoff = datetime.utcnow() - timedelta(seconds=90)
    offline_cutoff = datetime.utcnow() - timedelta(minutes=5)
    items = []
    for device, terminal_code, store_name, _brand_id in rows:
        is_online = bool(device.last_seen_at and device.last_seen_at >= online_cutoff)
        if device.status == "UNASSIGNED":
            bucket = "unassigned"
        elif device.status == "DISABLED":
            bucket = "disabled"
        elif not device.last_seen_at or device.last_seen_at < offline_cutoff:
            bucket = "offline"
        else:
            bucket = "assigned"

        if status and bucket != status:
            continue

        items.append(
            AdminDeviceListItem(
                device_id=device.device_id,
                device_name=device.device_name,
                manufacturer=device.manufacturer,
                model=device.model,
                os_version=device.os_version,
                app_version=device.app_version,
                status=device.status,
                terminal_code=terminal_code,
                store_name=store_name,
                last_seen_at=device.last_seen_at,
                is_online=is_online,
                registered_at=device.created_at,
            )
        )
    return ok([item.model_dump(mode="json") for item in items])
