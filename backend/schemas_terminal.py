from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Brands (public read)
# ---------------------------------------------------------------------------


class BrandResponse(BaseModel):
    brand_id: UUID
    code: str
    name: str
    logo_url: Optional[str] = None
    is_active: bool


# ---------------------------------------------------------------------------
# Device provisioning (Android app)
# ---------------------------------------------------------------------------


class DeviceRegisterRequest(BaseModel):
    local_install_id: UUID
    device_name: Optional[str] = Field(default=None, max_length=150)
    manufacturer: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    os_version: Optional[str] = Field(default=None, max_length=50)
    app_version: Optional[str] = Field(default=None, max_length=20)
    platform: str = Field(default="android", max_length=20)


class DeviceRegisterResponse(BaseModel):
    device_id: UUID
    status: str
    pairing_code: Optional[str] = None
    pairing_code_expires_at: Optional[datetime] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    terminal_code: Optional[str] = None
    message: str


class DeviceMeResponse(BaseModel):
    device_id: UUID
    status: str
    terminal_id: Optional[UUID] = None
    terminal_code: Optional[str] = None
    store_id: Optional[UUID] = None
    store_name: Optional[str] = None
    brand_id: Optional[UUID] = None
    brand_name: Optional[str] = None


class DeviceHeartbeatRequest(BaseModel):
    app_version: Optional[str] = Field(default=None, max_length=20)


class DeviceHeartbeatResponse(BaseModel):
    acknowledged: bool = True
    server_time: datetime
    status: str


class DeviceRefreshRequest(BaseModel):
    refresh_token: str


class DeviceRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
