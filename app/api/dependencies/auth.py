"""
app/api/dependencies/auth.py
FastAPI dependencies for JWT authentication and role-based access control.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.user import User, UserRole
from app.core.security import verify_token_type
from app.core.logging import get_logger

logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=True)


def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    token = credentials.credentials
    user_id = verify_token_type(token, expected_type="access")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ── Public dependency ─────────────────────────────────────────────────────────
CurrentUser = Annotated[User, Depends(_get_current_user)]


# ── Role-gated factory ────────────────────────────────────────────────────────
def require_roles(*roles: UserRole):
    """
    Usage:
        @router.get("/admin-only")
        def endpoint(user: Annotated[User, Depends(require_roles(UserRole.admin))]):
    """
    def _checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _checker


# ── Convenience aliases ───────────────────────────────────────────────────────
AdminOnly       = Annotated[User, Depends(require_roles(UserRole.admin))]
AnalystOrAbove  = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.analyst))]
SaccoOrAbove    = Annotated[User, Depends(
    require_roles(UserRole.admin, UserRole.analyst, UserRole.sacco_operator)
)]
