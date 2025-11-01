# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, List, Optional
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QCheckBox, QDoubleSpinBox,
    QMessageBox, QFrame
)

# -------------------------------
# Data model for table rows
# -------------------------------
@dataclass
class _CatRow:
    id: Optional[int]
    name: str
    description: str
    default_price_cents: int
    active: bool

def _to_dollars(cents: int) -> float:
    return float(cents or 0) / 100.0

def _to_cents(dollars: float) -> int:
    return int(round(float(dollars or 0.0) * 100))


# -------------------------------
# Repo helpers with safe fallbacks
# -------------------------------
def _repo_has(obj: Any, *names: str) -> Optional[str]:
    for n in names:
        if hasattr(obj, n):
            return n
    return None

def _repo_list(repo: Any, *, include_inactive: bool = True) -> List[Any]:
    # Preferred: repo method
    fn = _repo_has(repo, "list_catalog")
    if fn:
        try:
            return getattr(repo, fn)(active_only=not include_inactive)
        except TypeError:
            return getattr(repo, fn)()
    # Fallback: query DB directly
    try:
        from models import ServiceCatalog
        s = getattr(repo, "s")  # SQLAlchemy Session
        q = s.query(ServiceCatalog)
        if not include_inactive:
            q = q.filter(ServiceCatalog.active.is_(True))
        return q.order_by(ServiceCatalog.name.asc()).all()
    except Exception as e:
        raise RuntimeError(f"Cannot load catalog: {e}")

def _repo_create(repo: Any, **kw) -> Any:
    fn = _repo_has(repo, "create_catalog_item", "create_catalog", "add_catalog_item")
    if fn:
        return getattr(repo, fn)(**kw)
    # Fallback: direct insert
    from models import ServiceCatalog
    s = getattr(repo, "s")
    obj = ServiceCatalog(
        name=kw.get("name", ""),
        description=kw.get("description", ""),
        default_price_cents=int(kw.get("default_price_cents", 0) or 0),
        active=bool(kw.get("active", True)),
    )
    s.add(obj)
    s.commit()
    s.refresh(obj)
    return obj

def _repo_update(repo: Any, item_id: int, **kw) -> Any:
    fn = _repo_has(repo, "update_catalog_item", "update_catalog")
    if fn:
        return getattr(repo, fn)(item_id, **kw)
    # Fallback: direct update
    from models import ServiceCatalog
    s = getattr(repo, "s")
    obj = s.get(ServiceCatalog, int(item_id))
    if obj is None:
        raise RuntimeError(f"Catalog id {item_id} not found")
    if "name" in kw: obj.name = kw["name"] or ""
    if "description" in kw: obj.description = kw["description"] or ""
    if "default_price_cents" in kw: obj.default_price_cents = int(kw["default_price_cents"] or 0)
    if "active" in kw: obj.active = bool(kw["active"])
    s.commit()
    return obj

def _repo_delete(repo: Any, item_id: int) -> Any:
    fn = _repo_has(repo, "delete_catalog_item", "delete_catalog")
    if fn:
        return getattr(repo, fn)(item_id)
    # Fallback: direct delete
    from models import ServiceCatalog
    s = getattr(repo, "s")
    obj = s.get(ServiceCatalog, int(item_id))
    if obj:
        s.delete(obj)
        s.commit()
    return None


# ==========================================================
# Catalog Manager Dialog
# ==========================================================
class CatalogManagerDialog(QDialog):
    """
    Modern Catalog Manager with inline editing.
    Columns: Name | Description | Default Rate | Active

    Double-click or press F2 on Name/Description to edit.
    Uses repo helpers when available, falls back to direct DB updates.
    """
    def __init__(self, session_or_repo: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Catalog Manager")
        self.setMinimumWidth(700)

        # Repo instance: prefer parent's repo if present
        self.repo = getattr(parent, "repo", session_or_repo)

        self._deleted_ids: set[int] = set()
        self._rows_cache: List[_CatRow] = []

        root = QVBoxLayout(self)

        # Top: search + actions
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or description")
        self.btn_add = QPushButton("Add")
        self.btn_dup = QPushButton("Duplicate")
        self.btn_del = QPushButton("Delete")
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_dup)
        top.addWidget(self.btn_del)
        root.addLayout(top)

        # Divider
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep)

        # Table
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Name", "Description", "Default Rate", "Active"])
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        root.addWidget(self.tbl, 1)

        # Bottom
        btm = QHBoxLayout()
        btm.addStretch(1)
        self.btn_save = QPushButton("Save")
        self.btn_close = QPushButton("Close")
        btm.addWidget(self.btn_save)
        btm.addWidget(self.btn_close)
        root.addLayout(btm)

        # Style
        self.setStyleSheet("""
            QDialog { background: #fafafa; }
            QLineEdit { padding: 6px; }
            QPushButton { padding: 6px 10px; }
            QTableWidget { gridline-color: #dddddd; }
        """)

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_dup.clicked.connect(self._duplicate_row)
        self.btn_del.clicked.connect(self._delete_row)
        self.btn_save.clicked.connect(self._save_all)
        self.btn_close.clicked.connect(self.accept)
        self.search.textChanged.connect(self._apply_filter)

        self._load()
        self.tbl.setToolTip("Double-click Name or Description to edit. F2 also edits.")

    # ---------- load/build ----------
    def _load(self):
        self.tbl.setRowCount(0)
        self._rows_cache.clear()
        try:
            rows = _repo_list(self.repo, include_inactive=True)
        except Exception as e:
            QMessageBox.warning(self, "Catalog", f"Could not load catalog:\n{e}")
            rows = []

        for c in rows:
            self._rows_cache.append(_CatRow(
                id=getattr(c, "id", None),
                name=getattr(c, "name", "") or "",
                description=getattr(c, "description", "") or "",
                default_price_cents=int(getattr(c, "default_price_cents", 0) or 0),
                active=bool(getattr(c, "active", True)),
            ))

        for r in self._rows_cache:
            self._insert_table_row(r)

        self._apply_filter()

    def _insert_table_row(self, r: _CatRow):
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)

        it_name = QTableWidgetItem(r.name)
        it_name.setData(Qt.UserRole, r.id)
        it_name.setFlags((it_name.flags() | Qt.ItemIsEditable) & ~Qt.ItemIsDropEnabled)
        self.tbl.setItem(row, 0, it_name)

        it_desc = QTableWidgetItem(r.description)
        it_desc.setFlags((it_desc.flags() | Qt.ItemIsEditable) & ~Qt.ItemIsDropEnabled)
        self.tbl.setItem(row, 1, it_desc)

        spn = QDoubleSpinBox()
        spn.setRange(0.0, 999999.0)
        spn.setDecimals(2)
        spn.setSingleStep(1.00)
        spn.setValue(_to_dollars(r.default_price_cents))
        self.tbl.setCellWidget(row, 2, spn)

        chk = QCheckBox()
        chk.setChecked(r.active)
        chk.setTristate(False)
        chk.setStyleSheet("margin-left: 8px;")
        self.tbl.setCellWidget(row, 3, chk)

    # ---------- actions ----------
    def _add_row(self):
        self._insert_table_row(_CatRow(None, "New service", "", 0, True))

    def _duplicate_row(self):
        idxs = self.tbl.selectionModel().selectedRows()
        if not idxs:
            QMessageBox.information(self, "Duplicate", "Select a row to duplicate.")
            return
        row = idxs[0].row()
        it_name = self.tbl.item(row, 0)
        it_desc = self.tbl.item(row, 1)
        spn: QDoubleSpinBox = self.tbl.cellWidget(row, 2)
        chk: QCheckBox = self.tbl.cellWidget(row, 3)
        self._insert_table_row(_CatRow(
            None,
            (it_name.text() if it_name else "") + " (copy)",
            it_desc.text() if it_desc else "",
            _to_cents(spn.value()) if spn else 0,
            bool(chk.isChecked()) if chk else True
        ))

    def _delete_row(self):
        idxs = self.tbl.selectionModel().selectedRows()
        if not idxs:
            QMessageBox.information(self, "Delete", "Select a row to delete.")
            return
        row = idxs[0].row()
        it_name = self.tbl.item(row, 0)
        item_id = it_name.data(Qt.UserRole) if it_name else None
        if item_id:
            self._deleted_ids.add(int(item_id))
        self.tbl.removeRow(row)

    # ---------- save ----------
    def _collect_rows(self) -> List[_CatRow]:
        rows: List[_CatRow] = []
        for r in range(self.tbl.rowCount()):
            it_name = self.tbl.item(r, 0)
            it_desc = self.tbl.item(r, 1)
            spn: QDoubleSpinBox = self.tbl.cellWidget(r, 2)
            chk: QCheckBox = self.tbl.cellWidget(r, 3)

            cid = it_name.data(Qt.UserRole) if it_name else None
            nm = (it_name.text() if it_name else "").strip()
            ds = (it_desc.text() if it_desc else "").strip()
            pr = _to_cents(spn.value() if spn else 0.0)
            ac = bool(chk.isChecked()) if chk else True
            rows.append(_CatRow(id=int(cid) if cid is not None else None,
                                name=nm, description=ds,
                                default_price_cents=pr, active=ac))
        return rows

    def _save_all(self):
        rows = self._collect_rows()

        for r in rows:
            if not r.name:
                QMessageBox.warning(self, "Missing", "Every item needs a Name.")
                return

        # Deletes
        for did in list(self._deleted_ids):
            try:
                _repo_delete(self.repo, did)
            except Exception as e:
                QMessageBox.warning(self, "Delete", f"Could not delete id {did}:\n{e}")
            else:
                self._deleted_ids.discard(did)

        # Upserts
        for r in rows:
            try:
                if r.id is None:
                    obj = _repo_create(self.repo,
                        name=r.name,
                        description=r.description,
                        default_price_cents=r.default_price_cents,
                        active=r.active,
                    )
                    # refresh id in table
                    if obj is not None:
                        new_id = getattr(obj, "id", None)
                        if new_id is not None:
                            # find matching item by name/desc/price on a new row
                            # safer: re-load after save, but try to set it now
                            pass
                else:
                    _repo_update(self.repo, r.id,
                        name=r.name,
                        description=r.description,
                        default_price_cents=r.default_price_cents,
                        active=r.active,
                    )
            except Exception as e:
                QMessageBox.warning(self, "Save", f"Could not save '{r.name}':\n{e}")

        QMessageBox.information(self, "Saved", "Catalog changes saved.")
        self._load()

    # ---------- filter ----------
    def _apply_filter(self):
        needle = (self.search.text() or "").strip().lower()
        for r in range(self.tbl.rowCount()):
            name = self.tbl.item(r, 0).text().lower() if self.tbl.item(r, 0) else ""
            desc = self.tbl.item(r, 1).text().lower() if self.tbl.item(r, 1) else ""
            self.tbl.setRowHidden(r, not (needle in name or needle in desc))
