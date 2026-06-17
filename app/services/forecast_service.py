"""
app/services/forecast_service.py
Serves demand forecasts: reads from DB if available, falls back to DuckDB aggregates.
"""
from datetime import datetime, date, timedelta
from typing import Optional
import numpy as np
from sqlalchemy.orm import Session
from app.models.forecast import DemandForecast
from app.db.duckdb_client import DuckDBClient
from app.models.route import Route
from app.core.logging import get_logger

logger = get_logger(__name__)

DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


class ForecastService:

    @staticmethod
    def get_forecast(
        db: Session,
        duck: DuckDBClient,
        route_id: str,
        days: int = 7,
    ) -> dict:
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            raise ValueError(f"Route {route_id} not found")

        # Try DB first (populated by ML pipeline)
        stored = (
            db.query(DemandForecast)
            .filter(DemandForecast.route_id == route_id)
            .filter(DemandForecast.forecast_date >= date.today())
            .order_by(DemandForecast.forecast_date, DemandForecast.hour)
            .limit(days * 18)
            .all()
        )

        if stored:
            return ForecastService._format_stored(route, stored, days)
        else:
            # Fallback: compute on-the-fly from historical DuckDB aggregates
            logger.warning(f"No stored forecast for {route_id}, computing from history")
            return ForecastService._compute_from_history(duck, route, days)

    @staticmethod
    def _format_stored(route: Route, records: list[DemandForecast], days: int) -> dict:
        from collections import defaultdict
        by_day: dict[date, list] = defaultdict(list)
        for r in records:
            by_day[r.forecast_date].append(r)

        daily_forecasts = []
        for d, entries in sorted(by_day.items())[:days]:
            hourly = [
                {
                    "hour":           e.hour,
                    "passengers":     max(0, round(e.yhat)),
                    "lower_bound":    max(0, round(e.yhat_lower)) if e.yhat_lower else None,
                    "upper_bound":    max(0, round(e.yhat_upper)) if e.yhat_upper else None,
                    "xgb_passengers": max(0, round(e.xgb_yhat))  if e.xgb_yhat  else None,
                }
                for e in sorted(entries, key=lambda x: x.hour)
            ]
            passengers = [h["passengers"] for h in hourly]
            peak_idx   = int(np.argmax(passengers)) if passengers else 0
            daily_forecasts.append({
                "date":             d.isoformat(),
                "day_name":         DAY_NAMES[d.weekday()],
                "hourly":           hourly,
                "daily_total":      sum(passengers),
                "peak_hour":        hourly[peak_idx]["hour"] if hourly else 0,
                "peak_passengers":  hourly[peak_idx]["passengers"] if hourly else 0,
            })

        return {
            "route_id":         route.route_id,
            "route_name":       route.route_name,
            "forecast_days":    days,
            "model_used":       "prophet+xgboost",
            "generated_at":     datetime.utcnow().isoformat(),
            "daily_forecasts":  daily_forecasts,
        }

    @staticmethod
    def _compute_from_history(
        duck: DuckDBClient, route: Route, days: int
    ) -> dict:
        """Aggregate historical hourly averages as a proxy forecast."""
        df = duck.query(
            """
            SELECT hour, day_of_week,
                   AVG(passengers) AS avg_pass,
                   STDDEV(passengers) AS std_pass
            FROM demand
            WHERE route_id = ?
            GROUP BY hour, day_of_week
            ORDER BY day_of_week, hour
            """,
            [route.route_id],
        )

        lookup: dict[tuple, float] = {}
        if not df.empty:
            for _, row in df.iterrows():
                lookup[(int(row["day_of_week"]), int(row["hour"]))] = float(row["avg_pass"])

        daily_forecasts = []
        for offset in range(days):
            d    = date.today() + timedelta(days=offset)
            dow  = d.weekday()
            hourly = []
            for h in range(5, 23):
                base = lookup.get((dow, h), 120.0)
                noise = float(np.random.normal(0, base * 0.08))
                val  = max(0, round(base + noise))
                hourly.append({
                    "hour": h, "passengers": val,
                    "lower_bound": max(0, round(val * 0.85)),
                    "upper_bound": round(val * 1.15),
                    "xgb_passengers": None,
                })
            passengers = [h["passengers"] for h in hourly]
            peak_idx   = int(np.argmax(passengers))
            daily_forecasts.append({
                "date":            d.isoformat(),
                "day_name":        DAY_NAMES[dow],
                "hourly":          hourly,
                "daily_total":     sum(passengers),
                "peak_hour":       hourly[peak_idx]["hour"],
                "peak_passengers": hourly[peak_idx]["passengers"],
            })

        return {
            "route_id":        route.route_id,
            "route_name":      route.route_name,
            "forecast_days":   days,
            "model_used":      "historical_average",
            "generated_at":    datetime.utcnow().isoformat(),
            "daily_forecasts": daily_forecasts,
        }

    @staticmethod
    def get_demand_spikes(duck: DuckDBClient, threshold: float = 1.5) -> list:
        """Identify route-hours where demand exceeds threshold × baseline."""
        df = duck.query(
            """
            WITH base AS (
                SELECT route_id, hour,
                       AVG(passengers) AS baseline
                FROM demand
                GROUP BY route_id, hour
            ),
            recent AS (
                SELECT route_id, date, hour, passengers
                FROM demand
                WHERE date >= (SELECT MAX(date) - INTERVAL '7 days' FROM demand)
            )
            SELECT r.route_id, r.date, r.hour,
                   r.passengers, b.baseline,
                   r.passengers / NULLIF(b.baseline, 0) AS spike_ratio
            FROM recent r
            JOIN base b USING (route_id, hour)
            WHERE spike_ratio >= ?
            ORDER BY spike_ratio DESC
            LIMIT 20
            """,
            [threshold],
        )
        return df.to_dict("records") if not df.empty else []
