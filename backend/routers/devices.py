from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import DevicePrincipal, require_device
from ..database import get_db
from ..errors import ErrorCode
from ..schemas_enterprise import (
    DeviceActivateRequest,
    DeviceActivateResponse,
    DeviceConfig,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceRuntimeConfigResponse,
)
from ..services.audit import write_audit_log

router = APIRouter(prefix="/api/v1/devices", tags=["enterprise-devices"])


@router.post("/register")
async def register_device(payload: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a freshly imaged Raspberry Pi and persist its CSR metadata.

    Production certificate issuance should sign `csr_pem` with the device CA
    and store the certificate fingerprint. This first implementation records
    the physical device and audit event.
    """
    result = await db.execute(
        text(
            """
            INSERT INTO ekart_prod.devices (
                device_serial, hostname, model, os_version, status
            )
            VALUES (:device_serial, :hostname, :model, :os_version, 'UNPROVISIONED')
            ON CONFLICT (device_serial) DO UPDATE
            SET hostname = EXCLUDED.hostname,
                model = EXCLUDED.model,
                os_version = EXCLUDED.os_version,
                updated_at = now()
            RETURNING device_id, status
            """
        ),
        payload.model_dump(),
    )
    row = result.mappings().one()
    response = DeviceRegisterResponse(device_id=row["device_id"], status="UNPROVISIONED")
    await write_audit_log(
        db,
        event_type="DEVICE_REGISTERED",
        entity_type="device",
        entity_id=row["device_id"],
        actor_type="device",
        payload={"device_serial": payload.device_serial, "hostname": payload.hostname},
    )
    return ok(response.model_dump(mode="json"))


@router.post("/activate")
async def activate_device(payload: DeviceActivateRequest, db: AsyncSession = Depends(get_db)):
    """Activate a device with a short-lived admin-generated activation code."""
    result = await db.execute(
        text(
            """
            SELECT d.device_id, d.activation_code, d.activation_code_expires_at,
                   a.terminal_id, t.store_id, s.brand_id
            FROM ekart_prod.devices d
            JOIN ekart_prod.device_terminal_assignments a
              ON a.device_id = d.device_id AND a.revoked_at IS NULL
            JOIN ekart_prod.terminals t ON t.terminal_id = a.terminal_id
            JOIN ekart_prod.stores s ON s.store_id = t.store_id
            WHERE d.device_id = :device_id
            """
        ),
        {"device_id": payload.device_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Device assignment not found"})
    if row["activation_code"] and row["activation_code"] != payload.activation_code:
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Invalid activation code"})

    await db.execute(
        text("UPDATE ekart_prod.devices SET status='ACTIVE', updated_at=now() WHERE device_id=:device_id"),
        {"device_id": payload.device_id},
    )
    await write_audit_log(
        db,
        event_type="DEVICE_ACTIVATED",
        entity_type="device",
        entity_id=payload.device_id,
        brand_id=row["brand_id"],
        store_id=row["store_id"],
        actor_type="device",
    )
    response = DeviceActivateResponse(
        access_token=f"dev-{payload.device_id}",
        refresh_token=f"refresh-{payload.device_id}",
        terminal_id=row["terminal_id"],
        store_id=row["store_id"],
        brand_id=row["brand_id"],
        config=DeviceConfig(mqtt_broker_url=None),
    )
    return ok(response.model_dump(mode="json"))


@router.post("/{device_id}/heartbeat")
async def heartbeat(
    device_id: UUID,
    payload: DeviceHeartbeatRequest,
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Record Pi health telemetry and return pending commands."""
    assignment = await db.execute(
        text(
            """
            SELECT a.terminal_id, t.store_id
            FROM ekart_prod.device_terminal_assignments a
            JOIN ekart_prod.terminals t ON t.terminal_id = a.terminal_id
            WHERE a.device_id = :device_id AND a.revoked_at IS NULL
            """
        ),
        {"device_id": device_id},
    )
    current = assignment.mappings().one_or_none()
    await db.execute(
        text(
            """
            UPDATE ekart_prod.devices
            SET last_seen_at = now(), last_ip = :ip_address,
                app_version = COALESCE(:app_version, app_version),
                updated_at = now()
            WHERE device_id = :device_id
            """
        ),
        {"device_id": device_id, **payload.model_dump()},
    )
    await db.execute(
        text(
            """
            INSERT INTO ekart_prod.device_heartbeats (
                device_id, terminal_id, store_id, ip_address, signal_strength,
                cpu_temp, ram_used_mb, disk_used_pct, app_version, uptime_seconds
            )
            VALUES (
                :device_id, :terminal_id, :store_id, :ip_address, :signal_strength,
                :cpu_temp, :ram_used_mb, :disk_used_pct, :app_version, :uptime_seconds
            )
            """
        ),
        {
            "device_id": device_id,
            "terminal_id": current["terminal_id"] if current else None,
            "store_id": current["store_id"] if current else None,
            **payload.model_dump(),
        },
    )
    response = DeviceHeartbeatResponse(server_time=datetime.now(timezone.utc))
    return ok(response.model_dump(mode="json"))


@router.get("/{device_id}/config")
async def get_device_config(
    device_id: UUID,
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Return the current store/terminal runtime config for a device."""
    result = await db.execute(
        text(
            """
            SELECT a.terminal_id, t.store_id, s.brand_id, s.name AS store_name,
                   s.gstin, b.logo_url, b.invoice_template_id,
                   b.whatsapp_phone_number_id IS NOT NULL AS whatsapp_enabled
            FROM ekart_prod.device_terminal_assignments a
            JOIN ekart_prod.terminals t ON t.terminal_id = a.terminal_id
            JOIN ekart_prod.stores s ON s.store_id = t.store_id
            JOIN ekart_prod.brands b ON b.brand_id = s.brand_id
            WHERE a.device_id = :device_id AND a.revoked_at IS NULL
            """
        ),
        {"device_id": device_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Active device config not found"})
    response = DeviceRuntimeConfigResponse(
        terminal_id=row["terminal_id"],
        store_id=row["store_id"],
        brand_id=row["brand_id"],
        store_name=row["store_name"],
        gstin=row["gstin"],
        logo_url=row["logo_url"],
        invoice_template_id=row["invoice_template_id"],
        whatsapp_enabled=bool(row["whatsapp_enabled"]),
        offline_mode_allowed=True,
        max_offline_orders=0,
    )
    return ok(response.model_dump(mode="json"))
