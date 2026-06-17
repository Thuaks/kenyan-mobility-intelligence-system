"""
app/core/logging.py
Structured logging configuration using loguru.
Outputs JSON in production, human-readable in development.
"""
import sys
import os
from loguru import logger
from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()

    # Remove default handler
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=not settings.is_production,
        serialize=settings.is_production,  # JSON in prod
    )

    # File handler — rotated daily, kept 14 days
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
    logger.add(
        settings.log_file,
        format=log_format,
        level=settings.log_level,
        rotation="00:00",
        retention="14 days",
        compression="gz",
        serialize=settings.is_production,
    )

    logger.info(
        f"Logging initialised | env={settings.app_env} | level={settings.log_level}"
    )


def get_logger(name: str):
    return logger.bind(module=name)
