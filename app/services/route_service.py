"""
app/services/route_service.py
Business logic for route catalogue and risk scores.
Reads from SQLite (transactional) and DuckDB (analytics).
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.route import Route, RouteRiskScore
from app.db.duckdb_client import DuckDBClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class RouteService:

    @staticmethod
    def get_all_routes(db: Session, active_only: bool = True) -> list[Route]:
        q = db.query(Route)
        if active_only:
            q = q.filter(Route.is_active == True)
        return q.order_by(Route.route_id).all()

    @staticmethod
    def get_route(db: Session, route_id: str) -> Route:
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found.")
        return route

    @staticmethod
    def get_risk_score(db: Session, route_id: str) -> RouteRiskScore:
        score = (
            db.query(RouteRiskScore)
            .filter(RouteRiskScore.route_id == route_id)
            .order_by(RouteRiskScore.scored_at.desc())
            .first()
        )
        if not score:
            raise HTTPException(
                status_code=404,
                detail=f"No risk score found for route '{route_id}'. Run the ML pipeline first.",
            )
        return score

    @staticmethod
    def get_all_risk_scores(db: Session) -> list[RouteRiskScore]:
        """Latest risk score per route."""
        from sqlalchemy import func
        subq = (
            db.query(
                RouteRiskScore.route_id,
                func.max(RouteRiskScore.scored_at).label("latest"),
            )
            .group_by(RouteRiskScore.route_id)
            .subquery()
        )
        return (
            db.query(RouteRiskScore)
            .join(subq, (RouteRiskScore.route_id == subq.c.route_id) &
                        (RouteRiskScore.scored_at == subq.c.latest))
            .order_by(RouteRiskScore.risk_score.desc())
            .all()
        )

    @staticmethod
    def get_risk_summary(db: Session) -> dict:
        scores = RouteService.get_all_risk_scores(db)
        by_tier: dict[str, int] = {}
        for s in scores:
            tier = str(s.risk_score)
            by_tier[tier] = by_tier.get(tier, 0) + 1

        critical = [s.route_id for s in scores if s.risk_score == 5]
        high     = [s.route_id for s in scores if s.risk_score == 4]
        last_scored = max((s.scored_at for s in scores), default=None)

        return {
            "total_routes":    len(scores),
            "by_tier":         by_tier,
            "critical_routes": critical,
            "high_risk_routes": high,
            "last_scored":     last_scored,
        }

    @staticmethod
    def upsert_risk_score(db: Session, route_id: str, score_data: dict) -> RouteRiskScore:
        score = RouteRiskScore(
            route_id=route_id,
            scored_at=datetime.now(timezone.utc),
            **score_data,
        )
        db.add(score)
        db.commit()
        db.refresh(score)
        return score

    @staticmethod
    def get_route_analytics(duck: DuckDBClient, route_id: str) -> dict:
        """Pull rich analytics for a route from DuckDB."""
        acc_stats = duck.query(
            """
            SELECT
                COUNT(*) as total_accidents,
                SUM(CASE WHEN severity='Fatal'   THEN 1 ELSE 0 END) as fatal,
                SUM(CASE WHEN severity='Serious' THEN 1 ELSE 0 END) as serious,
                AVG(CAST(is_peak_hour AS INTEGER)) * 100 as pct_peak_hour,
                MODE(cause)         as top_cause,
                MODE(accident_type) as top_type
            FROM accidents
            WHERE route_id = ?
            """,
            [route_id],
        )
        demand_stats = duck.query(
            """
            SELECT
                AVG(passengers)         as avg_hourly,
                MAX(passengers)         as peak_passengers,
                MIN(passengers)         as min_passengers
            FROM demand
            WHERE route_id = ?
            """,
            [route_id],
        )
        result = {}
        if not acc_stats.empty:
            result["accidents"] = acc_stats.iloc[0].to_dict()
        if not demand_stats.empty:
            result["demand"] = demand_stats.iloc[0].to_dict()
        return result
