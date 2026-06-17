"""
app/api/routers/auth.py
Auth endpoints: register, login, token refresh, profile.
"""
from fastapi import APIRouter, status
from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest,
    TokenResponse, TokenRefreshRequest, UserResponse,
)
from app.schemas.common import APIResponse
from app.services.user_service import UserService
from app.api.dependencies.db import DBSession
from app.api.dependencies.auth import CurrentUser
from app.core.security import verify_token_type, create_access_token
from app.core.config import get_settings
from fastapi import HTTPException

router   = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(payload: UserRegisterRequest, db: DBSession):
    user = UserService.register(db, payload)
    return APIResponse(
        success=True,
        message="Account created successfully.",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Login and receive JWT tokens",
)
def login(payload: UserLoginRequest, db: DBSession):
    tokens = UserService.authenticate(db, payload)
    return APIResponse(
        success=True,
        message="Login successful.",
        data=TokenResponse(**tokens),
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh access token using a refresh token",
)
def refresh_token(payload: TokenRefreshRequest, db: DBSession):
    user_id = verify_token_type(payload.refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    user = UserService.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    from app.core.security import create_refresh_token
    return APIResponse(
        success=True,
        message="Token refreshed.",
        data=TokenResponse(
            access_token=create_access_token(subject=user.id),
            refresh_token=create_refresh_token(subject=user.id),
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        ),
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current authenticated user profile",
)
def get_me(current_user: CurrentUser):
    return APIResponse(
        success=True,
        data=UserResponse.model_validate(current_user),
    )
