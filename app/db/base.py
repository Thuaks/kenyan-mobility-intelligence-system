"""
app/db/base.py
SQLAlchemy session factory.
Uses SQLite for dev, swap DATABASE_URL for PostgreSQL in prod.
"""
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger   = get_logger(__name__)


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
    """
    Create all tables on startup if they don't already exist.
    Safe to call on every container start/restart — Railway's persistent
    volume keeps the SQLite file across deploys, so tables usually already
    exist. We explicitly inspect first rather than relying solely on
    create_all()'s internal checkfirst, and we swallow the
    'table already exists' race so a fast double-start (e.g. Railway health
    check hitting the app while it's still booting) never crashes startup.
    """
    from app.models import user, route, accident, forecast, alert  # noqa: F401
    from sqlalchemy.exc import OperationalError

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    all_tables = set(Base.metadata.tables.keys())
    missing = all_tables - existing_tables

    if not missing:
        logger.info(f"All {len(all_tables)} tables already exist — skipping create_all()")
        return

    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info(f"Created {len(missing)} missing table(s): {missing}")
    except OperationalError as e:
        if "already exists" in str(e):
            logger.warning(f"Table creation race detected (harmless): {e}")
        else:
            raise
