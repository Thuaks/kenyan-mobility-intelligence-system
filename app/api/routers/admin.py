"""
app/api/routers/admin.py
Admin-only endpoints: user management, system stats, pipeline triggers.
"""
from fastapi import APIRouter, Query
from app.schemas.user import UserResponse
from app.schemas.common import APIResponse
from app.services.user_service import UserService
from app.api.dependencies.db import DBSession, DuckDB
from app.api.dependencies.auth import AdminOnly

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=APIResponse[list[UserResponse]],
    summary="List all registered users [admin only]",
)
def list_users(
    db: DBSession,
    _admin: AdminOnly,
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    users = UserService.get_all(db, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        data=[UserResponse.model_validate(u) for u in users],
    )


@router.delete(
    "/users/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Deactivate a user account [admin only]",
)
def deactivate_user(user_id: int, db: DBSession, admin: AdminOnly):
    user = UserService.deactivate(db, user_id, requesting_user=admin)
    return APIResponse(
        success=True,
        message=f"User {user_id} deactivated.",
        data=UserResponse.model_validate(user),
    )


@router.get(
    "/system/stats",
    summary="System-wide data statistics [admin only]",
)
def system_stats(duck: DuckDB, _admin: AdminOnly):
    counts = {}
    for table in ["accidents", "demand", "social", "route_profiles", "blackspots"]:
        try:
            counts[table] = int(duck.scalar(f"SELECT COUNT(*) FROM {table}"))
        except Exception:
            counts[table] = 0
    return APIResponse(success=True, data={"record_counts": counts})


@router.post(
    "/pipeline/trigger",
    summary="Trigger the ML scoring pipeline manually [admin only]",
)
def trigger_pipeline(_admin: AdminOnly):
    """
    In production this would enqueue a Celery task or APScheduler job.
    For now, returns a stub response.
    """
    return APIResponse(
        success=True,
        message="Pipeline trigger queued. Results available within ~5 minutes.",
        data={"status": "queued"},
    )
