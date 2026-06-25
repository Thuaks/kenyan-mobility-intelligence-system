"""
app/schemas/alert.py
Pydantic v2 schemas for SMS alert endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class AlertTriggerRequest(BaseModel):
    route_id: str
    recipient_phone: str = Field(..., min_length=9, max_length=20)
    custom_message: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    route_id: Optional[str]
    recipient_phone: str
    message: str
    sent: bool
    delivered: bool
    at_message_id: Optional[str]
    error_message: Optional[str]
    triggered_by: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]


class CriticalRouteAlert(BaseModel):
    route_id: str
    route_name: str
    risk_score: int
    risk_label: str
    accidents_24mo: Optional[int]


class CriticalRoutesResponse(BaseModel):
    total: int
    routes: List[CriticalRouteAlert]


class AlertHistoryResponse(BaseModel):
    total: int
    alerts: List[AlertResponse]
