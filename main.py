# -----------------------------
# File: main.py
# -----------------------------
from __future__ import annotations

import os
import sys
import sqlite3
from typing import Optional

from PySide6.QtCore import Qt, QCoreApplication, QTimer, QObject
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QMessageBox

from sqlalchemy import event

from db import init_engine_and_session, ensure_schema
from ui.main_window import MainWindow

APP_NAME = "Founders PW - SO Manager"
FORCE_LIGHT_PALETTE = True  # set False if you want to follow OS theme


def _enable_qt_scaling():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
    os.environ.setdefault("QT_SCALE_FACTOR", "1")


def _sqlite_path_from_db_url(db_url: str) -> Optional[str]:
    """
    Extract a filesystem path from a URL like sqlite:///data/fpc.db
    Returns None for non-sqlite URLs.
    """
    if not db_url:
        return None
    lower = db_url.lower()
    if lower.startswith("sqlite:///"):
        return db_url.split("sqlite:///", 1)[1]
    if lower.startswith("sqlite://"):
        return None
    return None


def _enable_sqlite_foreign_keys(engine):
    """
    Ensure SQLite cascade deletes run by turning on foreign_keys at connect time.
    Uses the engine you already create via init_engine_and_session.
    """
    def _fk_on(dbapi_conn, conn_record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    event.listen(engine, "connect", _fk_on, once=False)


def ensure_sqlite_columns(db_path: Optional[str]):
    """
    Lightweight self-heal for dev DBs.
    - Creates 'service_catalog' table if missing.
    - Adds price/cross-ref columns to site_services and so_services.
    - Adds any missing Invoice fields.
    Safe to call repeatedly.
    """
    if not db_path or not os.path.exists(db_path):
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    def table_exists(name: str) -> bool:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
        return cur.fetchone() is not None

    def has_col(table: str, name: str) -> bool:
        cur.execute(f"PRAGMA table_info({table})")
        return any(r[1] == name for r in cur.fetchall())

    # 1) service_catalog table
    if not table_exists("service_catalog"):
        cur.execute("""
        CREATE TABLE service_catalog (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            default_price_cents INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME
        )
        """)

    # 2) site_services: catalog_id + unit_price_cents
    if table_exists("site_services"):
        if not has_col("site_services", "catalog_id"):
            cur.execute("ALTER TABLE site_services ADD COLUMN catalog_id INTEGER")
        if not has_col("site_services", "unit_price_cents"):
            cur.execute("ALTER TABLE site_services ADD COLUMN unit_price_cents INTEGER NOT NULL DEFAULT 0")
        if not has_col("site_services", "active"):
            cur.execute("ALTER TABLE site_services ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

    # 3) so_services: unit_price_cents snapshot
    if table_exists("so_services"):
        if not has_col("so_services", "unit_price_cents"):
            cur.execute("ALTER TABLE so_services ADD COLUMN unit_price_cents INTEGER NOT NULL DEFAULT 0")

    # 4) invoices: ensure all model columns exist
    invoice_cols = [
        ("invoice_no", "TEXT"),
        ("invoice_date", "DATE"),
        ("due_date", "DATE"),
        ("subtotal_cents", "INTEGER"),
        ("tax_cents", "INTEGER"),
        ("total_cents", "INTEGER"),
        ("paid", "INTEGER"),
        ("notes", "TEXT"),
        ("pdf_path", "TEXT"),
        ("created_at", "DATETIME"),
    ]
    if table_exists("invoices"):
        for col, sqltype in invoice_cols:
            if not has_col("invoices", col):
                cur.execute(f"ALTER TABLE invoices ADD COLUMN {col} {sqltype}")

    con.commit()
    con.close()


# ---------- Global UI helpers ----------

def _apply_light_palette(app: QApplication):
    """Force a neutral light palette independent of OS dark mode."""
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(245, 245, 245))
    pal.setColor(QPalette.WindowText, QColor(0, 0, 0))
    pal.setColor(QPalette.Base, QColor(255, 255, 255))
    pal.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    pal.setColor(QPalette.ToolTipBase, QColor(255, 255, 225))
    pal.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    pal.setColor(QPalette.Text, QColor(0, 0, 0))
    pal.setColor(QPalette.Button, QColor(245, 245, 245))
    pal.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    pal.setColor(QPalette.Highlight, QColor(30, 144, 255))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)


def _install_global_msgbox_silencer():
    """
    Monkey-patch QMessageBox.* so any 'Preview…' or 'NoError' dialog
    is suppressed globally. Returns nothing.
    """
    _orig_critical = QMessageBox.critical
    _orig_warning = QMessageBox.warning
    _orig_information = QMessageBox.information
    _orig_question = QMessageBox.question

    def _silence_if_preview(parent, title, text, *args, **kwargs):
        t = (str(title) or "").strip()
        s = (str(text) or "").strip()
        if t.startswith("Preview") or s == "NoError":
            return QMessageBox.Ok  # pretend acknowledged
        return None

    def _wrap(orig_func):
        def _wrapped(parent, title, text, *args, **kwargs):
            r = _silence_if_preview(parent, title, text, *args, **kwargs)
            return r if r is not None else orig_func(parent, title, text, *args, **kwargs)
        return staticmethod(_wrapped)

    QMessageBox.critical = _wrap(_orig_critical)
    QMessageBox.warning = _wrap(_orig_warning)
    QMessageBox.information = _wrap(_orig_information)
    QMessageBox.question = _wrap(_orig_question)


class _PreviewSweeper(QObject):
    """Extra safety: close any stray Preview/NoError boxes shortly after startup."""
    def __init__(self, parent=None):
        super().__init__(parent)
        for ms in (0, 25, 50, 100, 200):
            QTimer.singleShot(ms, self._sweep)

    def _sweep(self):
        app = QApplication.instance()
        if not app:
            return
        for w in app.topLevelWidgets():
            # we cannot import QMessageBox type-safely here without recursion
            try:
                title = getattr(w, "windowTitle", lambda: "")() or ""
                text = getattr(w, "text", lambda: "")() or ""
            except Exception:
                continue
            title = str(title).strip()
            text = str(text).strip()
            if title.startswith("Preview") or text == "NoError":
                try:
                    w.done(0)
                except Exception:
                    pass
                try:
                    w.close()
                except Exception:
                    pass


def main():
    _enable_qt_scaling()

    QCoreApplication.setApplicationName(APP_NAME)
    app = QApplication(sys.argv)

    if FORCE_LIGHT_PALETTE:
        _apply_light_palette(app)

    # Global guard against the rogue Preview/NoError dialog
    _install_global_msgbox_silencer()
    _ = _PreviewSweeper(app)

    db_url = os.getenv("FPC_DB_URL", "sqlite:///data/fpc.db")

    # Build engine + SessionLocal using your existing db.py helpers
    engine, SessionLocal = init_engine_and_session(db_url)

    # Make sure SQLite honors ON DELETE CASCADE on this engine
    _enable_sqlite_foreign_keys(engine)

    # Create any missing tables
    ensure_schema(engine)

    # Self-heal columns that the ORM expects (e.g., invoices.invoice_no)
    ensure_sqlite_columns(_sqlite_path_from_db_url(db_url))

    # Launch UI
    win = MainWindow(SessionLocal)
    win.setWindowTitle(APP_NAME)
    win.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
    win.resize(1600, 900)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
# coderabbit-review-marker
