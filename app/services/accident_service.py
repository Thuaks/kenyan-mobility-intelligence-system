"""
app/services/accident_service.py
Serves accident records and blackspot clusters via DuckDB.
"""
from app.db.duckdb_client import DuckDBClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class AccidentService:

    @staticmethod
    def get_stats(duck: DuckDBClient) -> dict:
        totals = duck.query(
            """
            SELECT
                COUNT(*)                         AS total_records,
                MIN(date)                        AS date_from,
                MAX(date)                        AS date_to
            FROM accidents
            """
        ).iloc[0].to_dict()

        by_severity = duck.query(
            "SELECT severity, COUNT(*) AS n FROM accidents GROUP BY severity ORDER BY n DESC"
        ).set_index("severity")["n"].to_dict()

        by_sub_county = duck.query(
            "SELECT sub_county, COUNT(*) AS n FROM accidents GROUP BY sub_county ORDER BY n DESC LIMIT 10"
        ).set_index("sub_county")["n"].to_dict()

        by_cause = duck.query(
            "SELECT cause, COUNT(*) AS n FROM accidents GROUP BY cause ORDER BY n DESC LIMIT 8"
        ).set_index("cause")["n"].to_dict()

        by_hour = duck.query(
            "SELECT hour, COUNT(*) AS n FROM accidents GROUP BY hour ORDER BY hour"
        ).set_index("hour")["n"].to_dict()

        peak_hour  = int(max(by_hour, key=by_hour.get))
        worst_sub  = next(iter(by_sub_county))
        total      = int(totals["total_records"])
        peak_count = sum(
            v for k, v in by_hour.items()
            if (6 <= int(k) < 9) or (16 <= int(k) < 20)
        )
        pct_peak = round(peak_count / total * 100, 1) if total else 0

        return {
            "total_records":   total,
            "date_range":      {"from": totals["date_from"], "to": totals["date_to"]},
            "by_severity":     {str(k): int(v) for k, v in by_severity.items()},
            "by_sub_county":   {str(k): int(v) for k, v in by_sub_county.items()},
            "by_cause":        {str(k): int(v) for k, v in by_cause.items()},
            "by_hour":         {str(k): int(v) for k, v in by_hour.items()},
            "peak_accident_hour": peak_hour,
            "worst_sub_county":   worst_sub,
            "pct_peak_hour":      pct_peak,
        }

    @staticmethod
    def get_blackspots(duck: DuckDBClient, min_incidents: int = 3) -> dict:
        df = duck.query(
            "SELECT * FROM blackspots WHERE n_incidents >= ? ORDER BY severity_score DESC",
            [min_incidents],
        )
        clusters = df.to_dict("records")
        return {
            "total_clusters":           len(clusters),
            "total_incidents_clustered": int(df["n_incidents"].sum()) if not df.empty else 0,
            "blackspots":               clusters,
        }

    @staticmethod
    def get_recent(duck: DuckDBClient, limit: int = 50, severity: str = None) -> list:
        sql = "SELECT * FROM accidents"
        params = []
        if severity:
            sql += " WHERE severity = ?"
            params.append(severity)
        sql += f" ORDER BY date DESC, hour DESC LIMIT {int(limit)}"
        return duck.query(sql, params or None).to_dict("records")
