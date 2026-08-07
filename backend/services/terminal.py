from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Brand, DeviceTerminalAssignment, Store, Terminal


async def get_active_assignment(db: AsyncSession, device_id: UUID):
    """Return `(assignment, terminal, store, brand)` for a device's current
    active (non-revoked) terminal assignment, or `None` if it isn't
    assigned. Shared by every endpoint that needs to know which store an
    authenticated device is actually allowed to act on — the store/terminal
    must always be derived from this, never trusted from client input.
    """
    result = await db.execute(
        select(DeviceTerminalAssignment, Terminal, Store, Brand)
        .join(Terminal, Terminal.terminal_id == DeviceTerminalAssignment.terminal_id)
        .join(Store, Store.store_id == Terminal.store_id)
        .join(Brand, Brand.brand_id == Store.brand_id)
        .where(DeviceTerminalAssignment.device_id == device_id, DeviceTerminalAssignment.revoked_at.is_(None))
    )
    return result.first()
