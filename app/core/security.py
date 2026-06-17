"""
app/core/security.py
JWT token creation/verification + bcrypt password hashing.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Union[str, int]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises JWTError on failure.
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )


def verify_token_type(token: str, expected_type: str) -> Optional[str]:
    """
    Decode token, verify its type, return subject (user_id).
    Returns None if invalid.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
