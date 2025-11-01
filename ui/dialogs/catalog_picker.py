# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QCheckBox, QLabel, QMessageBox
)


def _to_dollars(cents: int) -> float:
    return float(cents or 0) / 100.0


class CatalogPickerDialog(QDialog):
    """
    Clean catalog picker for adding services to a Site.

    - Search box filters by name or description
    - Select All / None helpers
    - Checkboxes per row control selection
    - Columns: Selected | Name | Description | Default Rate | Active
    - selected_ids() returns list of catalog row ids
    """
    def __init__(self, parent=None, repo: Any = None, title: str = "Select Services from Catalog"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(700)
        self._repo = getattr(parent, "repo", repo) or repo

        self._rows: List[Any] = []   # raw repo rows
        self._id_col = 1             # we will store id on the Name item (col 1)

        root = QVBoxLayout(self)

        # Top - search and bulk selects
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or description")
        self.btn_all = QPushButton("Select All")
        self.btn_none = QPushButton("Select None")
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_all)
        top.addWidget(self.btn_none)
        root.addLayout(top)

        # Table
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["", "Name", "Description", "Default Rate", "Active"])
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        root.addWidget(self.tbl, 1)

        # Bottom buttons
        bot = QHBoxLayout()
        bot.addStretch(1)
        self.btn_ok = QPushButton("Add Selected")
        self.btn_cancel = QPushButton("Cancel")
        bot.addWidget(self.btn_ok)
        bot.addWidget(self.btn_cancel)
        root.addLayout(bot)

        # Style
        self.setStyleSheet("""
            QDialog { background: #fafafa; }
            QLineEdit { padding: 6px; }
            QPushButton { padding: 6px 10px; }
            QTableWidget { gridline-color: #dddddd; }
        """)

        # Signals
        self.search.textChanged.connect(self._apply_filter)
        self.btn_all.clicked.connect(lambda: self._bulk_select(True))
        self.btn_none.clicked.connect(lambda: self._bulk_select(False))
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.tbl.cellDoubleClicked.connect(self._toggle_row_checkbox)

        # Load rows
        self._load()

    # ---------- data ----------
    def _load(self):
        self.tbl.setRowCount(0)
        self._rows.clear()
        rows = []
        try:
            rows = self._repo.list_catalog(active_only=True) if self._repo else []
        except Exception as e:
            QMessageBox.warning(self, "Catalog", f"Could not load catalog:\n{e}")
        self._rows = rows or []
        for r in self._rows:
            self._insert_row(r)

        self._apply_filter()

    def _insert_row(self, r: Any):
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)

        # Selected checkbox
        chk = QCheckBox()
        chk.setChecked(False)
        self.tbl.setCellWidget(row, 0, chk)

        # Name with id on UserRole
        name = str(getattr(r, "name", "") or "")
        it_name = QTableWidgetItem(name)
        it_name.setData(Qt.UserRole, getattr(r, "id", None))
        self.tbl.setItem(row, 1, it_name)

        # Description
        it_desc = QTableWidgetItem(str(getattr(r, "description", "") or ""))
        self.tbl.setItem(row, 2, it_desc)

        # Default Rate
        price = _to_dollars(int(getattr(r, "default_price_cents", 0) or 0))
        it_price = QTableWidgetItem(f"{price:.2f}")
        it_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl.setItem(row, 3, it_price)

        # Active flag
        it_active = QTableWidgetItem("Yes" if bool(getattr(r, "active", True)) else "No")
        self.tbl.setItem(row, 4, it_active)

    # ---------- UX helpers ----------
    def _apply_filter(self):
        needle = (self.search.text() or "").strip().lower()
        for r in range(self.tbl.rowCount()):
            name = self.tbl.item(r, 1).text().lower() if self.tbl.item(r, 1) else ""
            desc = self.tbl.item(r, 2).text().lower() if self.tbl.item(r, 2) else ""
            visible = (needle in name) or (needle in desc)
            self.tbl.setRowHidden(r, not visible)

    def _bulk_select(self, state: bool):
        for r in range(self.tbl.rowCount()):
            if not self.tbl.isRowHidden(r):
                w = self.tbl.cellWidget(r, 0)
                if isinstance(w, QCheckBox):
                    w.setChecked(state)

    def _toggle_row_checkbox(self, row: int, col: int):
        # double-click anywhere on the row toggles the checkbox
        w = self.tbl.cellWidget(row, 0)
        if isinstance(w, QCheckBox):
            w.setChecked(not w.isChecked())

    # ---------- API ----------
    def selected_ids(self) -> List[int]:
        out: List[int] = []
        for r in range(self.tbl.rowCount()):
            w = self.tbl.cellWidget(r, 0)
            if isinstance(w, QCheckBox) and w.isChecked():
                it = self.tbl.item(r, self._id_col)
                cid = it.data(Qt.UserRole) if it else None
                if cid is not None:
                    out.append(int(cid))
        return out
# coderabbit-review-marker
