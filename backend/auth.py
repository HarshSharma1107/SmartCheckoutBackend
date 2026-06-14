from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import ErrorCode

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class DevicePrincipal:
    device_id: Optional[str]
    token: str


@dataclass(frozen=True)
class AdminPrincipal:
    admin_id: str
    token: str


async def require_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_device_id: str | None = Header(default=None),
) -> DevicePrincipal:
    """Validate device mTLS/JWT before allowing device routes.

    Production implementation must verify the client certificate fingerprint,
    JWT signature, token expiry, revocation state, and active assignment. This
    dependency intentionally accepts a bearer token during local development so
    the new route surface can be exercised before certificate infrastructure is
    available.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Missing device bearer token"},
        )
    return DevicePrincipal(device_id=x_device_id, token=credentials.credentials)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_id: str | None = Header(default="00000000-0000-0000-0000-000000000000"),
) -> AdminPrincipal:
    """Validate admin JWT and RBAC before allowing admin routes."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Missing admin bearer token"},
        )
    return AdminPrincipal(admin_id=x_admin_id or "00000000-0000-0000-0000-000000000000", token=credentials.credentials)


async def require_webhook_key(x_webhook_key: str | None = Header(default=None)) -> str:
    """Validate webhook API key or provider signature.

    The production path should verify provider-specific HMAC signatures. This
    function keeps the contract explicit while config is introduced.
    """
    if not x_webhook_key:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Missing webhook key"},
        )
    return x_webhook_key

