"""
app/schemas/accident.py
Pydantic v2 schemas for accident and blackspot endpoints.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AccidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accident_id: str
    date: date
    hour: int
    latitude: float
    longitude: float
    sub_county: Optional[str]
    route_id: Optional[str]
    accident_type: Optional[str]
    cause: Optional[str]
    severity: str
    casualties: int
    weather_condition: Optional[str]


class BlackspotCluster(BaseModel):
    cluster_id: int
    centroid_lat: float
    centroid_lon: float
    radius_m: int
    n_incidents: int
    n_fatal: int
    dominant_hour: int
    dominant_type: str
    dominant_cause: str
    severity_score: float
    risk_tier: int


class BlackspotResponse(BaseModel):
    total_clusters: int
    total_incidents_clustered: int
    blackspots: List[BlackspotCluster]


class AccidentStatsResponse(BaseModel):
    total_records: int
    date_range: dict           # {"from": ..., "to": ...}
    by_severity: dict          # {"Fatal": 384, ...}
    by_sub_county: dict
    by_cause: dict
    by_hour: dict
    peak_accident_hour: int
    worst_sub_county: str
    pct_peak_hour: float
