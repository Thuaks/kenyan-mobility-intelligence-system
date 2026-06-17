"""
app/core/config.py
Centralised application configuration via pydantic-settings.
All values read from environment variables / .env file.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    app_name: str = "Kenya Urban Mobility Intelligence Platform"
    app_env: str = "development"
    app_version: str = "1.0.0"
    debug: bool = True

    # ── API Server ─────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Auth / JWT ─────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./kumip.db"
    duckdb_path: str = "./data/kumip_analytics.duckdb"

    # ── CORS ───────────────────────────────────────────────────────────────────
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8501",
    ]

    # ── External APIs ──────────────────────────────────────────────────────────
    twitter_bearer_token: str = ""
    nasa_power_api_base: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    africas_talking_api_key: str = ""
    africas_talking_username: str = "sandbox"

    # ── ML ────────────────────────────────────────────────────────────────────
    models_dir: str = "./models/saved"
    retrain_schedule_hour: int = 2

    # ── Logging ────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = "./logs/kumip.log"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — call this everywhere."""
    return Settings()
