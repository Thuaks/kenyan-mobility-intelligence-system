"""
app/schemas/forecast.py
Pydantic v2 schemas for demand forecast API responses.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class HourlyForecast(BaseModel):
    hour: int
    passengers: int
    lower_bound: Optional[int] = None
    upper_bound: Optional[int] = None
    xgb_passengers: Optional[int] = None


class DailyForecast(BaseModel):
    date: date
    day_name: str
    hourly: List[HourlyForecast]
    daily_total: int
    peak_hour: int
    peak_passengers: int


class DemandForecastResponse(BaseModel):
    route_id: str
    route_name: str
    forecast_days: int
    model_used: str                # "prophet" | "xgboost" | "ensemble"
    generated_at: datetime
    daily_forecasts: List[DailyForecast]


class DemandSpikeAlert(BaseModel):
    route_id: str
    route_name: str
    forecast_date: date
    forecast_hour: int
    predicted_passengers: int
    baseline_passengers: int
    spike_ratio: float
    alert_level: str               # "moderate" | "high" | "critical"
