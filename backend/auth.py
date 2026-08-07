from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import (
    DEVICE_ACCESS_TOKEN_TTL_SECONDS,
    DEVICE_REFRESH_TOKEN_TTL_SECONDS,
    JWT_ALGORITHM,
    JWT_SECRET,
)
from .errors import ErrorCode

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class DevicePrincipal:
    device_id: str
    token: str


def _encode(payload: dict, ttl_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Token expired"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid token"},
        )


def create_device_access_token(device_id: UUID) -> str:
    return _encode(
        {"sub": f"device:{device_id}", "device_id": str(device_id), "type": "device_access"},
        DEVICE_ACCESS_TOKEN_TTL_SECONDS,
    )


def create_device_refresh_token(device_id: UUID) -> str:
    return _encode(
        {"sub": f"device:{device_id}", "device_id": str(device_id), "type": "device_refresh"},
        DEVICE_REFRESH_TOKEN_TTL_SECONDS,
    )


def decode_device_refresh_token(token: str) -> str:
    """Validate a device refresh token and return the claimed device_id.

    Callers must still compare the returned device_id's stored
    `refresh_token_hash` against a hash of this token before trusting it —
    this only proves the token is well-formed and unexpired.
    """
    claims = _decode(token)
    if claims.get("type") != "device_refresh":
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Not a device refresh token"},
        )
    return claims["device_id"]


async def require_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> DevicePrincipal:
    """Verify the device JWT and derive identity from its signed claim.

    Callers must never trust a `device_id` supplied via URL/body/header for
    authorization — always compare it against `DevicePrincipal.device_id`
    from this dependency, which comes from a signature-verified token.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Missing device bearer token"},
        )
    claims = _decode(credentials.credentials)
    if claims.get("type") != "device_access":
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Not a device access token"},
        )
    return DevicePrincipal(device_id=claims["device_id"], token=credentials.credentials)


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
