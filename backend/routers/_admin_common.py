from uuid import UUID

from fastapi import HTTPException

from ..auth import AdminPrincipal
from ..errors import ErrorCode


def require_brand_access(admin: AdminPrincipal, brand_id: UUID) -> None:
    if admin.role == "SUPER_ADMIN":
        return
    if not admin.brand_id or UUID(admin.brand_id) != brand_id:
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Not authorized for this brand"})
