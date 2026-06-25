"""
app/main.py
FastAPI application factory.
Registers routers, middleware, startup/shutdown events, and health check.
"""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.base import create_tables
from app.db.duckdb_client import DuckDBClient
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.routers import auth
from app.api.routers import routes as routes_router
from app.api.routers import demand, accidents, social, admin
from app.api.routers import alerts

settings = get_settings()
logger   = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("🟢🟢🟢 BUILD MARKER vFIX2026 — bcrypt-direct security.py is ACTIVE 🟢🟢🟢")

    # Create SQLite tables (dev). In prod, Alembic handles this.
    create_tables()
    logger.info("Database tables verified/created")

    # Warm up DuckDB — registers CSV views
    try:
        duck = DuckDBClient.get()
        logger.info("DuckDB analytical store ready")
    except Exception as e:
        logger.warning(f"DuckDB init failed (data may not be seeded yet): {e}")

    # Seed initial admin user if not exists
    _seed_admin_user()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down NUMP API")
    DuckDBClient.get().close()


def _seed_admin_user():
    """Create a default admin account if no users exist."""
    try:
        from app.db.base import SessionLocal
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        db = SessionLocal()
        if db.query(User).count() == 0:
            admin = User(
                email="admin@nump.co.ke",
                full_name="NUMP Admin",
                hashed_password=hash_password("admin1234!"),
                role=UserRole.admin,
                organisation="NUMP",
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user created: admin@nump.co.ke / admin1234!")
        db.close()
    except Exception as e:
        logger.warning(f"Could not seed admin user: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Nairobi Urban Mobility Platform — "
            "Real-time transit demand forecasting, matatu route risk scoring, "
            "and road safety intelligence for Nairobi."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = settings.api_prefix
    app.include_router(auth.router,                prefix=prefix)
    app.include_router(routes_router.router,       prefix=prefix)
    app.include_router(demand.router,              prefix=prefix)
    app.include_router(accidents.router,           prefix=prefix)
    app.include_router(social.router,              prefix=prefix)
    app.include_router(admin.router,               prefix=prefix)
    app.include_router(alerts.router,              prefix=prefix)
    logger.info(f"[DIAG] alerts.router has {len(alerts.router.routes)} routes: {[r.path for r in alerts.router.routes]}")
    logger.info(f"[DIAG] Total app routes after all registrations: {len(app.routes)}")

    # ── Health check (unauthenticated) ────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=True)
    def health():
        from app.db.base import engine
        from sqlalchemy import text
        db_ok = False
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

        models_dir = settings.models_dir
        models_ok  = os.path.isdir(models_dir) and bool(os.listdir(models_dir))

        return JSONResponse({
            "status":        "healthy" if db_ok else "degraded",
            "version":       settings.app_version,
            "environment":   settings.app_env,
            "db_connected":  db_ok,
            "models_loaded": models_ok,
        })

    @app.get("/", include_in_schema=False)
    def root():
        return {"message": f"NUMP API v{settings.app_version} — visit /docs"}

    return app


app = create_app()
