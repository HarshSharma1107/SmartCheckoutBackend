from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

from .errors import ErrorCode

T = TypeVar("T")


class ErrorPayload(BaseModel):
    code: ErrorCode | str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorPayload] = None


def ok(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def fail(code: ErrorCode | str, message: str) -> dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": str(code), "message": message}}

