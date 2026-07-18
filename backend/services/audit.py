from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    actor_type: str = "system",
    actor_id: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            notes=notes,
        )
    )
