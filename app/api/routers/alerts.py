"""
app/api/routers/alerts.py
SMS alert endpoints — mock Africa's Talking integration.
"""
from fastapi import APIRouter, HTTPException, Query
from app.schemas.alert import (
    AlertTriggerRequest, AlertResponse, CriticalRoutesResponse,
    CriticalRouteAlert, AlertHistoryResponse,
)
from app.schemas.common import APIResponse
from app.services.alert_service import AlertService
from app.api.dependencies.db import DBSession

router = APIRouter(prefix="/alerts", tags=["Alerts (Mock SMS)"])


@router.get(
    "/critical-routes",
    response_model=APIResponse[CriticalRoutesResponse],
    summary="List routes currently qualifying for a Critical risk alert",
)
def critical_routes(db: DBSession):
    routes = AlertService.scan_for_critical_routes(db)
    return APIResponse(
        success=True,
        data=CriticalRoutesResponse(
            total=len(routes),
            routes=[CriticalRouteAlert(**r) for r in routes],
        ),
    )


@router.post(
    "/trigger",
    response_model=APIResponse[AlertResponse],
    summary="Send a (mock) SMS alert for a route — sandbox mode, no real SMS sent",
)
def trigger_alert(payload: AlertTriggerRequest, db: DBSession):
    try:
        alert = AlertService.trigger_alert(
            db=db,
            route_id=payload.route_id.upper(),
            recipient_phone=payload.recipient_phone,
            custom_message=payload.custom_message,
            triggered_by="api",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return APIResponse(
        success=alert.sent,
        message="Alert sent (mock mode)." if alert.sent else "Alert failed.",
        data=AlertResponse.model_validate(alert),
    )


@router.get(
    "/history",
    response_model=APIResponse[AlertHistoryResponse],
    summary="Recent alert history (newest first)",
)
def alert_history(db: DBSession, limit: int = Query(20, ge=1, le=100)):
    alerts = AlertService.get_alert_history(db, limit=limit)
    return APIResponse(
        success=True,
        data=AlertHistoryResponse(
            total=len(alerts),
            alerts=[AlertResponse.model_validate(a) for a in alerts],
        ),
    )
