"""
app/schemas/user.py
Pydantic v2 schemas for user registration, login, and responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


# ── Request bodies ────────────────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.public
    organisation: Optional[str] = None
    phone: Optional[str] = Field(None, pattern=r"^\+\d{9,15}$")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ── Response bodies ───────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    organisation: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds


class TokenRefreshRequest(BaseModel):
    refresh_token: str
