"""
app/db/base.py
SQLAlchemy async-compatible session factory.
Uses SQLite for dev, swap DATABASE_URL for PostgreSQL in prod.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings

settings = get_settings()

# SQLite: enforce FK constraints (disabled by default in SQLite)
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
    echo=settings.debug,
)

if "sqlite" in settings.database_url:
    event.listen(engine, "connect", _set_sqlite_pragma)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


def get_db():
    """FastAPI dependency — yields a DB session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables on startup (dev). Use Alembic for prod migrations."""
    from app.models import user, route, accident, forecast, alert  # noqa: F401
    Base.metadata.create_all(bind=engine)
