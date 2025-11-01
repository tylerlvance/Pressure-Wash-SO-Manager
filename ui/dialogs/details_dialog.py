# C:\Users\tyler\Desktop\FoundersSOManager\ui\dialogs\details_dialog.py
from __future__ import annotations

from typing import Optional, Iterable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
    QAbstractItemView, QHeaderView
)

# ---------- helpers
def _spacer(px: int = 8) -> QWidget:
    w = QWidget(); w.setFixedHeight(px); return w

def _to_dollars(cents: int) -> float:
    return float(cents or 0) / 100.0

def _ro_line(text: str = "") -> QLineEdit:
    le = QLineEdit(text or "")
    le.setReadOnly(True)
    le.setCursorPosition(0)
    return le

def _ro_text(text: str = "") -> QTextEdit:
    te = QTextEdit()
    te.setPlainText(text or "")
    te.setReadOnly(True)
    te.setMinimumHeight(64)
    te.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    return te


class CustomerSiteDetailsDialog(QDialog):
    """
    Read only viewer for a Customer, optional Site, and Contracted Services.
    - Mirrors the CustomerDialog visual style
    - Fields are selectable for easy copy
    - Services table highlights the selected row and shows a total
    """
    def __init__(self, parent=None, *, customer=None, site=None, services: Optional[Iterable]=None):
        super().__init__(parent)
        self.setWindowTitle("Details")

        # ---------- groups
        gb_c = None
        if customer is not None:
            gb_c = QGroupBox("Customer")
            form_c = QFormLayout(gb_c)
            form_c.setLabelAlignment(Qt.AlignRight)
            form_c.addRow("Name",  _ro_line(getattr(customer, "name", "") or ""))
            form_c.addRow("Phone", _ro_line(getattr(customer, "phone", "") or ""))
            form_c.addRow("Email", _ro_line(getattr(customer, "email", "") or ""))
            form_c.addRow("Notes", _ro_text(getattr(customer, "notes", "") or ""))

        gb_s = None
        if site is not None:
            gb_s = QGroupBox("Site")
            form_s = QFormLayout(gb_s)
            form_s.setLabelAlignment(Qt.AlignRight)
            form_s.addRow("Name",       _ro_line(getattr(site, "name", "") or ""))
            form_s.addRow("Address",    _ro_text(getattr(site, "address", "") or ""))
            form_s.addRow("POC Name",   _ro_line(getattr(site, "poc_name", "") or ""))
            form_s.addRow("POC Phone",  _ro_line(getattr(site, "poc_phone", "") or ""))
            form_s.addRow("POC Email",  _ro_line(getattr(site, "poc_email", "") or ""))
            form_s.addRow("Cadence",    _ro_line(getattr(site, "cadence_text", "") or ""))
            form_s.addRow("Notes",      _ro_text(getattr(site, "notes", "") or ""))

        gb_sv = None
        total = 0.0
        if services is not None:
            # filter active rows if an 'active' attr exists
            rows = list(services)
            try:
                rows = [s for s in rows if bool(getattr(s, "active", True))]
            except Exception:
                pass

            gb_sv = QGroupBox("Contracted Services")
            tbl = QTableWidget(0, 2, gb_sv)
            tbl.setHorizontalHeaderLabels(["Service", "Price ($)"])
            tbl.verticalHeader().setVisible(False)
            tbl.setAlternatingRowColors(True)
            tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
            tbl.setSelectionMode(QAbstractItemView.SingleSelection)
            tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
            hh = tbl.horizontalHeader()
            hh.setSectionResizeMode(0, QHeaderView.Stretch)
            hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)

            for s in rows:
                r = tbl.rowCount()
                tbl.insertRow(r)
                name = getattr(s, "name", "") or ""
                price = _to_dollars(getattr(s, "unit_price_cents", 0))
                total += price
                tbl.setItem(r, 0, QTableWidgetItem(name))
                itp = QTableWidgetItem(f"{price:.2f}")
                itp.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(r, 1, itp)

            layout_sv = QVBoxLayout(gb_sv)
            layout_sv.addWidget(tbl)
            # total row
            total_row = QHBoxLayout()
            total_row.addStretch(1)
            lbl_total = QLabel(f"Total: ${total:,.2f}")
            lbl_total.setObjectName("totalLabel")
            total_row.addWidget(lbl_total)
            layout_sv.addLayout(total_row)

        # ---------- layout
        root = QVBoxLayout(self)
        hdr = QLabel("Details"); hdr.setObjectName("dlgTitle")
        root.addWidget(hdr)
        root.addWidget(_spacer(6))

        # two column body like CustomerDialog
        body = QHBoxLayout()
        left = QWidget(); lc = QVBoxLayout(left); lc.setContentsMargins(8, 8, 8, 8)
        right = QWidget(); rc = QVBoxLayout(right); rc.setContentsMargins(8, 8, 8, 8)
        if gb_c: lc.addWidget(gb_c)
        if gb_s: lc.addWidget(gb_s)
        if gb_sv: rc.addWidget(gb_sv)

        body.addWidget(left, 1)
        body.addWidget(right, 1)
        root.addLayout(body, 1)

        # buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        root.addLayout(btns)

        # polish
        self.setMinimumWidth(720)
        self._apply_style()

    # ---------- style to match your modern dialogs and improve selection contrast
    def _apply_style(self):
        self.setStyleSheet("""
        QLabel#dlgTitle { font-size: 18px; font-weight: 600; padding-left: 8px; }
        QGroupBox { font-weight: 600; }

        QLineEdit, QTextEdit { padding: 6px; }
        /* Better readability for selected table rows */
        QTableView::item:selected { background: #e5f3ff; color: #111111; }

        QHeaderView::section {
            font-weight: 600;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 4px 6px;
        }
        QLabel#totalLabel { font-weight: 600; padding: 4px 2px; }
        """)
