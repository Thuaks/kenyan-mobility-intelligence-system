"""
app/schemas/common.py
Shared API response envelopes and pagination schemas.
"""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[Any] = None
    code: Optional[str] = None


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    db_connected: bool
    models_loaded: bool
