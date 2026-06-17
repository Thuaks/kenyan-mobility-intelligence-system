"""
app/api/routers/social.py
Social media incident intelligence endpoints.
"""
from fastapi import APIRouter, Query
from app.schemas.common import APIResponse
from app.services.social_service import SocialService
from app.api.dependencies.db import DuckDB

router = APIRouter(prefix="/social", tags=["Social Intelligence"])

VALID_TOPICS = ["breakdown","accident","police_block","flooding","positive","overloading"]


@router.get(
    "/incidents",
    summary="Recent matatu incident tweets (negative sentiment only)",
)
def recent_incidents(
    duck: DuckDB,
    limit: int  = Query(30, ge=1, le=100),
    topic: str  = Query(None, description=f"Filter by topic: {VALID_TOPICS}"),
):
    if topic and topic not in VALID_TOPICS:
        from fastapi import HTTPException
        raise HTTPException(400, f"Invalid topic. Choose from: {VALID_TOPICS}")
    records = SocialService.get_recent_incidents(duck, limit=limit, topic=topic)
    return APIResponse(
        success=True,
        message=f"{len(records)} incident records returned",
        data=records,
    )


@router.get(
    "/sentiment",
    summary="Overall social sentiment summary and topic breakdown",
)
def sentiment_summary(duck: DuckDB):
    summary = SocialService.get_sentiment_summary(duck)
    return APIResponse(success=True, data=summary)


@router.get(
    "/sentiment/{route_ref}",
    summary="Sentiment breakdown for a specific route reference (e.g. Westlands)",
)
def route_sentiment(route_ref: str, duck: DuckDB):
    data = SocialService.get_route_sentiment(duck, route_ref)
    return APIResponse(success=True, data=data)
