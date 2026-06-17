"""
app/schemas/route.py
Pydantic v2 schemas for route and risk score API responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ShapDriver(BaseModel):
    feature: str
    shap_value: float
    direction: str   # "increases_risk" | "decreases_risk"


class RouteBase(BaseModel):
    route_id: str
    route_name: str
    sub_county: Optional[str] = None
    distance_km: Optional[float] = None
    avg_fare_ksh: Optional[int] = None


class RouteResponse(RouteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    n_stops: Optional[int] = None
    is_active: bool


class RiskScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route_id: str
    route_name: str
    risk_score: int               # 1–5
    risk_label: str               # Very Low → Critical
    risk_color: str               # hex colour for UI
    confidence: Optional[float]
    top_drivers: Optional[List[ShapDriver]]
    accidents_24mo: Optional[int]
    accidents_per_km: Optional[float]
    model_version: Optional[str]
    scored_at: datetime


class RouteListResponse(BaseModel):
    total: int
    routes: List[RouteResponse]


class RiskSummaryResponse(BaseModel):
    """Aggregate risk distribution across all routes."""
    total_routes: int
    by_tier: dict              # {"1": 4, "2": 6, ...}
    critical_routes: List[str]
    high_risk_routes: List[str]
    last_scored: Optional[datetime]
