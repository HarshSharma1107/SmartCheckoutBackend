import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit_log(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    brand_id: UUID | None = None,
    store_id: UUID | None = None,
    actor_id: UUID | None = None,
    actor_type: str = "system",
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO ekart_prod.audit_logs (
                event_type, entity_type, entity_id, brand_id, store_id,
                actor_id, actor_type, payload, ip_address
            )
            VALUES (
                :event_type, :entity_type, :entity_id, :brand_id, :store_id,
                :actor_id, :actor_type, CAST(:payload AS jsonb), :ip_address
            )
            """
        ),
        {
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "brand_id": brand_id,
            "store_id": store_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "payload": json.dumps(payload or {}),
            "ip_address": ip_address,
        },
    )
