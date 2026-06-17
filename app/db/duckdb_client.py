"""
app/db/duckdb_client.py
DuckDB client for analytical queries against processed CSV datasets.
SQLite handles transactional data; DuckDB handles analytical reads.
"""
import os
import duckdb
import pandas as pd
from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DuckDBClient:
    """
    Thin wrapper around a DuckDB connection.
    Registers all processed CSV files as virtual tables on init.
    """
    _instance: Optional["DuckDBClient"] = None

    def __init__(self):
        os.makedirs(os.path.dirname(settings.duckdb_path), exist_ok=True)
        self.conn = duckdb.connect(settings.duckdb_path)
        self._register_tables()
        logger.info(f"DuckDB connected → {settings.duckdb_path}")

    @classmethod
    def get(cls) -> "DuckDBClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_tables(self):
        """Register processed CSV files as DuckDB views."""
        tables = {
            "accidents":      "data/processed/accidents_clean.csv",
            "route_profiles": "data/processed/route_profiles.csv",
            "demand":         "data/processed/demand_dataset.csv",
            "social":         "data/processed/social_sentiment.csv",
            "weather":        "data/processed/nairobi_weather.csv",
            "blackspots":     "data/processed/blackspot_clusters.csv",
        }
        for name, path in tables.items():
            if os.path.exists(path):
                self.conn.execute(
                    f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{path}')"
                )
                logger.debug(f"  Registered DuckDB view: {name}")
            else:
                logger.warning(f"  CSV not found, skipping view: {path}")

    def query(self, sql: str, params: list = None) -> pd.DataFrame:
        """Execute SQL and return a DataFrame."""
        try:
            if params:
                return self.conn.execute(sql, params).df()
            return self.conn.execute(sql).df()
        except Exception as e:
            logger.error(f"DuckDB query error: {e}\nSQL: {sql}")
            raise

    def scalar(self, sql: str, params: list = None):
        """Return a single scalar value."""
        df = self.query(sql, params)
        if df.empty:
            return None
        return df.iloc[0, 0]

    def close(self):
        self.conn.close()
        DuckDBClient._instance = None


def get_duckdb() -> DuckDBClient:
    """FastAPI dependency — returns the DuckDB singleton."""
    return DuckDBClient.get()
