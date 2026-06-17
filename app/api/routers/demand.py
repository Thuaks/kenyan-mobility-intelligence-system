"""
app/api/routers/demand.py
Demand forecasting endpoints.
"""
from fastapi import APIRouter, Query
from app.schemas.forecast import DemandForecastResponse
from app.schemas.common import APIResponse
from app.services.forecast_service import ForecastService
from app.api.dependencies.db import DBSession, DuckDB

router = APIRouter(prefix="/demand", tags=["Demand Forecasting"])


@router.get(
    "/forecast/{route_id}",
    response_model=APIResponse[DemandForecastResponse],
    summary="Get 1–14 day hourly demand forecast for a route",
)
def get_demand_forecast(
    route_id: str,
    db: DBSession,
    duck: DuckDB,
    days: int = Query(7, ge=1, le=14, description="Number of forecast days"),
):
    forecast = ForecastService.get_forecast(db, duck, route_id.upper(), days=days)
    return APIResponse(
        success=True,
        data=DemandForecastResponse(**forecast),
    )


@router.get(
    "/spikes",
    summary="Identify routes with abnormal demand spikes (ratio ≥ threshold)",
)
def demand_spikes(
    duck: DuckDB,
    threshold: float = Query(1.5, ge=1.1, le=5.0),
):
    spikes = ForecastService.get_demand_spikes(duck, threshold=threshold)
    return APIResponse(
        success=True,
        message=f"{len(spikes)} demand spike(s) detected above {threshold}×",
        data=spikes,
    )


@router.get(
    "/summary",
    summary="Average hourly demand across all routes (for heatmap)",
)
def demand_summary(duck: DuckDB):
    df = duck.query(
        """
        SELECT hour, day_of_week,
               ROUND(AVG(passengers)) AS avg_passengers,
               ROUND(MAX(passengers)) AS peak_passengers
        FROM demand
        GROUP BY hour, day_of_week
        ORDER BY day_of_week, hour
        """
    )
    return APIResponse(success=True, data=df.to_dict("records"))
