"""
app/services/alert_service.py
Business logic for SMS alert generation and the mock SMS gateway.

PRODUCTION NOTE: send_sms_mock() simulates Africa's Talking's API
response shape without making any real network call or requiring API
credentials. This lets the full alert pipeline — rule evaluation,
message composition, database logging, delivery status tracking — be
fully demonstrated and tested. Swapping to real Africa's Talking is a
single-function change: replace send_sms_mock() with a real call to
africastalking.SMS.send(), keeping the same return shape.
"""
import random
import string
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.route import Route, RouteRiskScore
from app.core.logging import get_logger

logger = get_logger(__name__)

DEMAND_SPIKE_THRESHOLD = 1.5
CRITICAL_RISK_SCORE = 5


def send_sms_mock(phone: str, message: str) -> dict:
    """
    Simulates Africa's Talking's SMS send response.
    Returns the same shape a real integration would: a message ID,
    delivery status, and cost — but performs no real network I/O.
    """
    if not phone or len(phone.strip()) < 9:
        return {
            "success": False,
            "message_id": None,
            "error": "Invalid phone number format.",
        }

    mock_id = "ATX" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    logger.info(f"[MOCK SMS] To: {phone} | Message: {message[:60]}... | ID: {mock_id}")

    return {
        "success": True,
        "message_id": mock_id,
        "error": None,
    }


class AlertService:

    @staticmethod
    def evaluate_route_for_alert(route: Route, risk_score: RouteRiskScore) -> Optional[dict]:
        if risk_score.risk_score >= CRITICAL_RISK_SCORE:
            message = (
                f"NUMIP ALERT: Route {route.route_id} ({route.route_name}) "
                f"is now CRITICAL risk (score {risk_score.risk_score}/5). "
                f"Accidents (24mo): {risk_score.accidents_24mo}. "
                f"SACCO operators should review vehicle safety checks."
            )
            return {
                "alert_type": "risk_change",
                "route_id": route.route_id,
                "message": message,
            }
        return None

    @staticmethod
    def trigger_alert(
        db: Session,
        route_id: str,
        recipient_phone: str,
        custom_message: Optional[str] = None,
        triggered_by: str = "manual",
    ) -> Alert:
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            raise ValueError(f"Route '{route_id}' not found.")

        if custom_message:
            message = custom_message
            alert_type = "manual"
        else:
            latest_score = (
                db.query(RouteRiskScore)
                .filter(RouteRiskScore.route_id == route_id)
                .order_by(RouteRiskScore.scored_at.desc())
                .first()
            )
            if not latest_score:
                message = f"NUMIP ALERT: Route {route_id} status update requested."
                alert_type = "manual"
            else:
                evaluation = AlertService.evaluate_route_for_alert(route, latest_score)
                if evaluation:
                    message = evaluation["message"]
                    alert_type = evaluation["alert_type"]
                else:
                    message = (
                        f"NUMIP ALERT: Route {route_id} ({route.route_name}) "
                        f"risk score: {latest_score.risk_score}/5 ({latest_score.risk_label})."
                    )
                    alert_type = "manual"

        result = send_sms_mock(recipient_phone, message)

        alert = Alert(
            alert_type=alert_type,
            route_id=route_id,
            recipient_phone=recipient_phone,
            message=message,
            sent=result["success"],
            delivered=result["success"],
            at_message_id=result.get("message_id"),
            error_message=result.get("error"),
            triggered_by=triggered_by,
            sent_at=datetime.now(timezone.utc) if result["success"] else None,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            f"Alert {'sent' if alert.sent else 'failed'}: "
            f"route={route_id} phone={recipient_phone} type={alert_type}"
        )
        return alert

    @staticmethod
    def scan_for_critical_routes(db: Session) -> list[dict]:
        from sqlalchemy import func

        subq = (
            db.query(
                RouteRiskScore.route_id,
                func.max(RouteRiskScore.scored_at).label("latest"),
            )
            .group_by(RouteRiskScore.route_id)
            .subquery()
        )
        latest_scores = (
            db.query(RouteRiskScore)
            .join(subq, (RouteRiskScore.route_id == subq.c.route_id) &
                        (RouteRiskScore.scored_at == subq.c.latest))
            .filter(RouteRiskScore.risk_score >= CRITICAL_RISK_SCORE)
            .all()
        )

        results = []
        for score in latest_scores:
            route = db.query(Route).filter(Route.route_id == score.route_id).first()
            if route:
                results.append({
                    "route_id": route.route_id,
                    "route_name": route.route_name,
                    "risk_score": score.risk_score,
                    "risk_label": score.risk_label,
                    "accidents_24mo": score.accidents_24mo,
                })
        return results

    @staticmethod
    def get_alert_history(db: Session, limit: int = 20) -> list[Alert]:
        return (
            db.query(Alert)
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .all()
        )
