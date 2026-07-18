from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Brands / Stores
# ---------------------------------------------------------------------------


class BrandResponse(BaseModel):
    brand_id: UUID
    code: str
    name: str
    logo_url: Optional[str] = None
    is_active: bool


class BrandCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    logo_url: Optional[str] = None


class StoreResponse(BaseModel):
    store_id: UUID
    brand_id: UUID
    brand_name: str
    code: str
    name: str
    city: Optional[str] = None
    is_active: bool


class StoreCreateRequest(BaseModel):
    brand_id: UUID
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    city: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------


def _validate_email(v: str) -> str:
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("Enter a valid email address")
    return v.strip().lower()


class AdminBootstrapRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=72)
    full_name: Optional[str] = Field(default=None, max_length=200)
    brand_id: Optional[UUID] = None

    _validate = field_validator("email")(_validate_email)


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=72)

    _validate = field_validator("email")(_validate_email)


class AdminLoginResponse(BaseModel):
    access_token: str
    expires_in: int
    admin_id: UUID
    role: str
    brand_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Admin device management
# ---------------------------------------------------------------------------


class AdminAssignStoreRequest(BaseModel):
    store_id: UUID
    pairing_code: str = Field(min_length=4, max_length=8)
    notes: Optional[str] = Field(default=None, max_length=500)


class AdminAssignStoreResponse(BaseModel):
    assignment_id: UUID
    terminal_id: UUID
    terminal_code: str
    assigned_at: datetime
    access_token: str
    refresh_token: str
    expires_in: int


class AdminDeactivateDeviceRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AdminDeactivateTerminalRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AdminDeviceListItem(BaseModel):
    device_id: UUID
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    status: str
    terminal_code: Optional[str] = None
    store_name: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    is_online: bool
    registered_at: datetime
