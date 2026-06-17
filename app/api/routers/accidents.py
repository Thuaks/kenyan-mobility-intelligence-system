"""
app/api/routers/accidents.py
Accident data and blackspot detection endpoints.
"""
from fastapi import APIRouter, Query
from app.schemas.accident import AccidentStatsResponse, BlackspotResponse
from app.schemas.common import APIResponse
from app.services.accident_service import AccidentService
from app.api.dependencies.db import DuckDB

router = APIRouter(prefix="/accidents", tags=["Accidents & Blackspots"])


@router.get(
    "/stats",
    response_model=APIResponse[AccidentStatsResponse],
    summary="Aggregate accident statistics across all Nairobi records",
)
def accident_stats(duck: DuckDB):
    stats = AccidentService.get_stats(duck)
    return APIResponse(success=True, data=AccidentStatsResponse(**stats))


@router.get(
    "/blackspots",
    response_model=APIResponse[BlackspotResponse],
    summary="DBSCAN-detected accident blackspot clusters in Nairobi",
)
def get_blackspots(
    duck: DuckDB,
    min_incidents: int = Query(3, ge=1, le=50,
                               description="Minimum incidents to qualify as a blackspot"),
):
    data = AccidentService.get_blackspots(duck, min_incidents=min_incidents)
    return APIResponse(success=True, data=BlackspotResponse(**data))


@router.get(
    "/recent",
    summary="Recent accident records (newest first)",
)
def recent_accidents(
    duck: DuckDB,
    limit: int = Query(50, ge=1, le=200),
    severity: str = Query(None, description="Filter by severity: Fatal | Serious | Minor"),
):
    records = AccidentService.get_recent(duck, limit=limit, severity=severity)
    return APIResponse(
        success=True,
        message=f"{len(records)} records returned",
        data=records,
    )


@router.get(
    "/heatmap-data",
    summary="Lat/lon + severity data for front-end map heatmap",
)
def heatmap_data(duck: DuckDB):
    df = duck.query(
        """
        SELECT latitude, longitude, severity,
               CASE severity WHEN 'Fatal'   THEN 3
                             WHEN 'Serious' THEN 2
                             ELSE 1 END AS weight
        FROM accidents
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
    )
    return APIResponse(
        success=True,
        data=df.to_dict("records"),
    )
