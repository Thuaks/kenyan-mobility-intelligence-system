"""
app/api/dependencies/db.py
Re-exports DB session and DuckDB client as FastAPI-injectable dependencies.
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.duckdb_client import DuckDBClient, get_duckdb

# Type aliases for cleaner endpoint signatures
DBSession   = Annotated[Session,      Depends(get_db)]
DuckDB      = Annotated[DuckDBClient, Depends(get_duckdb)]
