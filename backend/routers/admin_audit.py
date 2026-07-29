from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import AdminUser, AuditLog
from ..schemas_catalog import AuditLogListItem

router = APIRouter(prefix="/api/v1/admin/audit-logs", tags=["admin-audit"])


@router.get("")
async def list_audit_logs(
    event_type: str | None = None,
    entity_type: str | None = None,
    actor_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Audit logs span every brand/store - SUPER_ADMIN only, same restriction
    # already applied to the admin-accounts list endpoint.
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": "Only SUPER_ADMIN can view audit logs"},
        )

    stmt = (
        select(AuditLog, AdminUser.email)
        .outerjoin(AdminUser, (AuditLog.actor_type == "admin") & (AdminUser.admin_id == AuditLog.actor_id))
        # The audit_logs table still carries rows from an older logging
        # scheme (populated `action`/`admin_id`/`created_at` instead of the
        # current columns) with event_type and/or entity_id left null. Skip
        # anything missing a field this response requires, rather than fail
        # the whole request - they predate this endpoint's contract.
        .where(
            AuditLog.event_type.is_not(None),
            AuditLog.entity_id.is_not(None),
            AuditLog.actor_type.is_not(None),
            AuditLog.occurred_at.is_not(None),
        )
    )
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.occurred_at <= date_to)
    stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.all()
    return ok(
        [
            AuditLogListItem(
                log_id=log.log_id,
                event_type=log.event_type,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                actor_type=log.actor_type,
                actor_id=log.actor_id,
                actor_email=actor_email,
                notes=log.notes,
                occurred_at=log.occurred_at,
            ).model_dump(mode="json")
            for log, actor_email in rows
        ]
    )
