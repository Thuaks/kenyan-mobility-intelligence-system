"""
app/api/routers/routes.py
Route catalogue + risk score endpoints.
"""
from fastapi import APIRouter, Query
from app.schemas.route import (
    RouteResponse, RiskScoreResponse, RouteListResponse, RiskSummaryResponse,
)
from app.schemas.common import APIResponse
from app.services.route_service import RouteService
from app.api.dependencies.db import DBSession, DuckDB
from app.api.dependencies.auth import CurrentUser

router = APIRouter(prefix="/routes", tags=["Routes & Risk"])


@router.get(
    "/",
    response_model=APIResponse[RouteListResponse],
    summary="List all matatu routes",
)
def list_routes(
    db: DBSession,
    active_only: bool = Query(True, description="Return only active routes"),
):
    routes = RouteService.get_all_routes(db, active_only=active_only)
    return APIResponse(
        success=True,
        data=RouteListResponse(
            total=len(routes),
            routes=[RouteResponse.model_validate(r) for r in routes],
        ),
    )


@router.get(
    "/risk/summary",
    response_model=APIResponse[RiskSummaryResponse],
    summary="Aggregate risk distribution across all routes",
)
def risk_summary(db: DBSession):
    summary = RouteService.get_risk_summary(db)
    return APIResponse(success=True, data=RiskSummaryResponse(**summary))


@router.get(
    "/{route_id}",
    response_model=APIResponse[RouteResponse],
    summary="Get a single route by ID",
)
def get_route(route_id: str, db: DBSession):
    route = RouteService.get_route(db, route_id.upper())
    return APIResponse(success=True, data=RouteResponse.model_validate(route))


@router.get(
    "/{route_id}/risk",
    response_model=APIResponse[RiskScoreResponse],
    summary="Get the latest risk score for a route",
)
def get_risk_score(route_id: str, db: DBSession):
    score = RouteService.get_risk_score(db, route_id.upper())
    route = RouteService.get_route(db, route_id.upper())

    drivers = score.top_drivers or []
    from app.schemas.route import ShapDriver
    shaped_drivers = [
        ShapDriver(
            feature=d.get("feature", ""),
            shap_value=d.get("shap_value", 0.0),
            direction="increases_risk" if d.get("shap_value", 0) > 0 else "decreases_risk",
        )
        for d in drivers
    ]
    return APIResponse(
        success=True,
        data=RiskScoreResponse(
            route_id=score.route_id,
            route_name=route.route_name,
            risk_score=score.risk_score,
            risk_label=score.risk_label,
            risk_color=score.risk_color if hasattr(score, "risk_color") else "#999",
            confidence=score.confidence,
            top_drivers=shaped_drivers,
            accidents_24mo=score.accidents_24mo,
            accidents_per_km=score.accidents_per_km,
            model_version=score.model_version,
            scored_at=score.scored_at,
        ),
    )


@router.get(
    "/{route_id}/analytics",
    summary="Get detailed route analytics from DuckDB (accidents + demand)",
)
def route_analytics(route_id: str, db: DBSession, duck: DuckDB):
    RouteService.get_route(db, route_id.upper())   # 404 guard
    analytics = RouteService.get_route_analytics(duck, route_id.upper())
    return APIResponse(success=True, data=analytics)
