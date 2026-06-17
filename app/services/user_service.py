"""
app/services/user_service.py
Business logic for user registration, authentication, and management.
All DB interaction is isolated here — routers stay thin.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import get_settings
from app.core.logging import get_logger

logger   = get_logger(__name__)
settings = get_settings()


class UserService:

    @staticmethod
    def register(db: Session, payload: UserRegisterRequest) -> User:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            organisation=payload.organisation,
            phone=payload.phone,
            is_active=True,
            is_verified=False,   # production: send verification email
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user registered: {user.email} | role={user.role}")
        return user

    @staticmethod
    def authenticate(db: Session, payload: UserLoginRequest) -> dict:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support.",
            )

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        access_token  = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        logger.info(f"User logged in: {user.email}")
        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "token_type":    "bearer",
            "expires_in":    settings.access_token_expire_minutes * 60,
        }

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def deactivate(db: Session, user_id: int, requesting_user: User) -> User:
        if requesting_user.role != UserRole.admin and requesting_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not authorised.")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
