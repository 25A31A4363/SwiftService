from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, Any
from datetime import datetime, timezone

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int = 1
    limit: int = 50
    total: int = 0
    totalPages: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ApiErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: Optional[str] = None

class ApiErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: Optional[str] = None
    requestId: Optional[str] = None

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[ApiErrorResponse] = None
    meta: Optional[PaginationMeta] = None
