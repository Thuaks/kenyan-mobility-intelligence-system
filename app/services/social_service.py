"""
app/services/social_service.py
Serves social media incident intelligence from DuckDB.
"""
from app.db.duckdb_client import DuckDBClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class SocialService:

    @staticmethod
    def get_recent_incidents(
        duck: DuckDBClient,
        limit: int = 30,
        topic: str = None,
    ) -> list:
        sql    = "SELECT * FROM social WHERE is_incident = 1"
        params = []
        if topic:
            sql += " AND topic = ?"
            params.append(topic)
        sql += f" ORDER BY timestamp DESC LIMIT {int(limit)}"
        df = duck.query(sql, params or None)
        return df.to_dict("records") if not df.empty else []

    @staticmethod
    def get_sentiment_summary(duck: DuckDBClient) -> dict:
        totals = duck.query(
            """
            SELECT
                COUNT(*)                                              AS total_tweets,
                AVG(compound)                                         AS avg_sentiment,
                SUM(CASE WHEN sentiment='Positive' THEN 1 ELSE 0 END) AS positive,
                SUM(CASE WHEN sentiment='Negative' THEN 1 ELSE 0 END) AS negative,
                SUM(CASE WHEN sentiment='Neutral'  THEN 1 ELSE 0 END) AS neutral,
                SUM(is_incident)                                      AS incident_tweets
            FROM social
            """
        ).iloc[0].to_dict()

        by_topic = duck.query(
            """
            SELECT topic,
                   COUNT(*)    AS n_tweets,
                   AVG(compound) AS avg_sentiment
            FROM social
            GROUP BY topic
            ORDER BY n_tweets DESC
            """
        ).to_dict("records")

        volume_trend = duck.query(
            """
            SELECT DATE_TRUNC('week', CAST(date AS DATE)) AS week,
                   COUNT(*)    AS total,
                   SUM(is_incident) AS incidents
            FROM social
            GROUP BY week
            ORDER BY week
            """
        ).to_dict("records")

        return {
            "totals":       {k: (round(float(v), 3) if isinstance(v, float) else int(v or 0))
                             for k, v in totals.items()},
            "by_topic":     by_topic,
            "volume_trend": volume_trend,
        }

    @staticmethod
    def get_route_sentiment(duck: DuckDBClient, route_ref: str) -> dict:
        df = duck.query(
            """
            SELECT topic, sentiment, COUNT(*) AS n,
                   AVG(compound) AS avg_compound
            FROM social
            WHERE route_ref ILIKE ?
            GROUP BY topic, sentiment
            ORDER BY n DESC
            """,
            [f"%{route_ref}%"],
        )
        return {"route_ref": route_ref, "breakdown": df.to_dict("records")}
