import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import (
    DevicePrincipal,
    create_device_access_token,
    create_device_refresh_token,
    decode_device_refresh_token,
    require_device,
)
from ..config import DEVICE_ACCESS_TOKEN_TTL_SECONDS, DEVICE_REFRESH_TOKEN_TTL_SECONDS, PAIRING_CODE_TTL_SECONDS
from ..database import get_db
from ..errors import ErrorCode
from ..models import Brand, Device, DeviceTerminalAssignment, Store, Terminal
from ..schemas_terminal import (
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceMeResponse,
    DeviceRefreshRequest,
    DeviceRefreshResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
)
from ..services.audit import write_audit_log

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _generate_pairing_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _active_assignment(db: AsyncSession, device_id: UUID):
    result = await db.execute(
        select(DeviceTerminalAssignment, Terminal, Store, Brand)
        .join(Terminal, Terminal.terminal_id == DeviceTerminalAssignment.terminal_id)
        .join(Store, Store.store_id == Terminal.store_id)
        .join(Brand, Brand.brand_id == Store.brand_id)
        .where(DeviceTerminalAssignment.device_id == device_id, DeviceTerminalAssignment.revoked_at.is_(None))
    )
    return result.first()


def _issue_device_tokens(device: Device) -> tuple[str, str]:
    access_token = create_device_access_token(device.device_id)
    refresh_token = create_device_refresh_token(device.device_id)
    device.refresh_token_hash = _hash_token(refresh_token)
    device.refresh_token_expires_at = datetime.utcnow() + timedelta(seconds=DEVICE_REFRESH_TOKEN_TTL_SECONDS)
    return access_token, refresh_token


def _apply_registration_fields(device: Device, payload: DeviceRegisterRequest) -> None:
    device.device_name = payload.device_name or device.device_name
    device.manufacturer = payload.manufacturer or device.manufacturer
    device.model = payload.model or device.model
    device.os_version = payload.os_version or device.os_version
    device.app_version = payload.app_version or device.app_version


@router.post("/register")
async def register_device(payload: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Idempotent by `local_install_id`. Safe to call repeatedly while the
    pending screen polls for assignment, and safe to call again after a
    reinstall — it returns the device's existing state instead of creating a
    duplicate row, per docs/terminal-provisioning-plan.md section 4.1.
    """
    result = await db.execute(select(Device).where(Device.local_install_id == payload.local_install_id))
    device = result.scalar_one_or_none()

    if device is None:
        device = Device(
            local_install_id=payload.local_install_id,
            device_type="ANDROID_APP",
            device_name=payload.device_name,
            manufacturer=payload.manufacturer,
            model=payload.model,
            os_version=payload.os_version,
            app_version=payload.app_version,
            platform=payload.platform,
            status="UNASSIGNED",
        )
        db.add(device)
        try:
            await db.flush()
        except IntegrityError:
            # Lost a race to another concurrent /register call for the same
            # brand-new local_install_id (uq_devices_local_install_id) -
            # treat it as "found existing" instead of surfacing a raw 500.
            await db.rollback()
            result = await db.execute(select(Device).where(Device.local_install_id == payload.local_install_id))
            device = result.scalar_one_or_none()
            if device is None:
                raise HTTPException(
                    status_code=409,
                    detail={"code": ErrorCode.CONFLICT, "message": "Registration conflict - please retry"},
                )
            _apply_registration_fields(device, payload)
        else:
            await write_audit_log(db, event_type="DEVICE_REGISTERED", entity_type="device", entity_id=device.device_id)
    else:
        _apply_registration_fields(device, payload)
    device.last_seen_at = datetime.utcnow()

    if device.status == "DISABLED":
        await db.flush()
        return ok(
            DeviceRegisterResponse(
                device_id=device.device_id,
                status="DISABLED",
                message="This device has been disabled by an admin.",
            ).model_dump(mode="json")
        )

    if device.status == "ASSIGNED":
        row = await _active_assignment(db, device.device_id)
        if row is None:
            # Assignment was revoked without resetting device status back to
            # UNASSIGNED elsewhere - fall through and treat it as unassigned
            # rather than issuing tokens for a terminal it no longer holds.
            device.status = "UNASSIGNED"
        else:
            _assignment, terminal, _store, _brand = row
            access_token, refresh_token = _issue_device_tokens(device)
            await db.flush()
            return ok(
                DeviceRegisterResponse(
                    device_id=device.device_id,
                    status="ASSIGNED",
                    access_token=access_token,
                    refresh_token=refresh_token,
                    terminal_code=terminal.terminal_code,
                    message="Device already assigned.",
                ).model_dump(mode="json")
            )

    if (
        not device.pairing_code
        or not device.pairing_code_expires_at
        or device.pairing_code_expires_at <= datetime.utcnow()
    ):
        device.pairing_code = _generate_pairing_code()
        device.pairing_code_expires_at = datetime.utcnow() + timedelta(seconds=PAIRING_CODE_TTL_SECONDS)

    await db.flush()
    return ok(
        DeviceRegisterResponse(
            device_id=device.device_id,
            status="UNASSIGNED",
            pairing_code=device.pairing_code,
            pairing_code_expires_at=device.pairing_code_expires_at,
            message="Registered. Show this code to your admin to assign a store.",
        ).model_dump(mode="json")
    )


@router.post("/refresh")
async def refresh_device_token(payload: DeviceRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Rotate a device's access/refresh token pair. The refresh token itself
    proves nothing on its own — it must also match the hash stored on the
    device row, so a revoked/reassigned device can't refresh its way back
    into a valid session (prevents spoofing after deactivation)."""
    claimed_device_id = decode_device_refresh_token(payload.refresh_token)
    result = await db.execute(select(Device).where(Device.device_id == UUID(claimed_device_id)))
    device = result.scalar_one_or_none()
    if device is None or device.status != "ASSIGNED":
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "message": "Device is not active"})
    if not device.refresh_token_hash or _hash_token(payload.refresh_token) != device.refresh_token_hash:
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "message": "Refresh token revoked"})
    if not device.refresh_token_expires_at or device.refresh_token_expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail={"code": ErrorCode.UNAUTHORIZED, "message": "Refresh token expired"})

    access_token, refresh_token = _issue_device_tokens(device)
    await db.flush()
    return ok(
        DeviceRefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=DEVICE_ACCESS_TOKEN_TTL_SECONDS,
        ).model_dump(mode="json")
    )


@router.post("/heartbeat")
async def heartbeat(
    payload: DeviceHeartbeatRequest,
    principal: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.device_id == UUID(principal.device_id)))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Device not found"})
    device.last_seen_at = datetime.utcnow()
    if payload.app_version:
        device.app_version = payload.app_version
    return ok(
        DeviceHeartbeatResponse(server_time=datetime.now(timezone.utc), status=device.status).model_dump(mode="json")
    )


@router.get("/me")
async def get_me(principal: DevicePrincipal = Depends(require_device), db: AsyncSession = Depends(get_db)):
    """Identity comes from the verified JWT claim, never a client-supplied
    device_id — this is what lets a device only ever read its own config."""
    device_id = UUID(principal.device_id)
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Device not found"})

    row = await _active_assignment(db, device_id)
    if row is None:
        return ok(DeviceMeResponse(device_id=device.device_id, status="UNASSIGNED").model_dump(mode="json"))

    _assignment, terminal, store, brand = row
    return ok(
        DeviceMeResponse(
            device_id=device.device_id,
            status="ASSIGNED",
            terminal_id=terminal.terminal_id,
            terminal_code=terminal.terminal_code,
            store_id=store.store_id,
            store_name=store.name,
            brand_id=brand.brand_id,
            brand_name=brand.name,
        ).model_dump(mode="json")
    )
