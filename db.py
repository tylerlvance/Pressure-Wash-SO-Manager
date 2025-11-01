# -----------------------------
# File: db.py
# -----------------------------
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ensure_service_catalog_columns
import os


def init_engine_and_session(db_url: str):
    if db_url.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)
    engine = create_engine(db_url, echo=False, future=True)

    # --- auto-fix missing columns (safe for SQLite) ---
    ensure_service_catalog_columns(engine)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, SessionLocal


def ensure_schema(engine):
    """Create any missing tables, then verify key columns exist."""
    Base.metadata.create_all(engine)
    ensure_service_catalog_columns(engine)
# coderabbit-review-marker
