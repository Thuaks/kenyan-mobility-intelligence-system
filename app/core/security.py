"""
app/core/security.py
JWT token creation/verification + bcrypt password hashing.

NOTE: We use bcrypt directly instead of passlib's CryptContext wrapper.
passlib 1.7.4's bcrypt backend probes `bcrypt.__about__.__version__`,
which was removed in bcrypt>=4.1.0, causing a hard crash on every
hash/verify call regardless of which bcrypt version is pinned in
requirements.txt (transitive deps can still resolve a newer one).
Calling bcrypt directly removes this fragile coupling entirely.
"""
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from app.core.config import get_settings

settings = get_settings()

# bcrypt has a hard 72-byte limit on the input password
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    pw_bytes = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


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
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )


def verify_token_type(token: str, expected_type: str) -> Optional[str]:
    try:
        payload = decode_token(token)
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
