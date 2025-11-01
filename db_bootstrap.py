# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

# Use your actual DB file
DB_PATH = os.path.join("data", "fpc.db")

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

# Ensure SQLite honors ON DELETE CASCADE on every connection
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, conn_record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def ensure_sqlite_columns():
    """
    Lightweight self-healing for dev. Adds missing nullable columns that the ORM expects.
    Safe to run multiple times.
    """
    if not os.path.exists(DB_PATH):
        return
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    def has_col(table: str, name: str) -> bool:
        cur.execute(f"PRAGMA table_info({table})")
        return any(r[1] == name for r in cur.fetchall())

    # Add invoices.invoice_no if missing
    try:
        if not has_col("invoices", "invoice_no"):
            cur.execute("ALTER TABLE invoices ADD COLUMN invoice_no TEXT")
    except sqlite3.OperationalError:
        # table may not exist yet on a fresh DB
        pass

    con.commit()
    con.close()
# coderabbit-review-marker
