# C:\Users\tyler\Desktop\FoundersSOManager\ui\dialogs\site_dialog.py
from __future__ import annotations

from typing import Optional, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QLabel, QPushButton, QComboBox, QCheckBox, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QDoubleSpinBox,
    QSizePolicy
)

from .common import _get_repo, _to_cents, _to_dollars
from .catalog_picker import CatalogPickerDialog


def _spacer(px: int = 8) -> QWidget:
    w = QWidget(); w.setFixedHeight(px); return w


class SiteDialog(QDialog):
    """
    Site dialog matching CustomerDialog style.
    - Left: site core info
    - Right: contracted services with toolbar
    - Safe persistence: never NULL name; flush+commit; rollback on error
    """
    def __init__(self, parent=None, customer_name: str = "", obj=None, repo=None):
        super().__init__(parent)
        self.setWindowTitle(f"Site - {customer_name}" if customer_name else "Site")
        self._obj = obj
        self._repo = _get_repo(parent, repo)

        self._deleted_ids: list[int] = []

        # ---------- Core fields (left)
        self.site_name = QLineEdit();  self.site_name.setPlaceholderText("Location name")
        self.address = QTextEdit();    self.address.setPlaceholderText("Street, City, ST ZIP"); self.address.setMinimumHeight(64)
        self.poc_name = QLineEdit();   self.poc_name.setPlaceholderText("On-site contact")
        self.poc_phone = QLineEdit();  self.poc_phone.setPlaceholderText("###-###-####")
        self.poc_email = QLineEdit();  self.poc_email.setPlaceholderText("name@example.com")
        self.cadence = QComboBox()
        self.cadence.addItems([
            "", "weekly", "biweekly", "monthly_same_day",
            "monthly_nth_wd:1:0", "monthly_nth_wd:2:0", "monthly_nth_wd:3:0", "monthly_nth_wd:4:0"
        ])
        self.notes = QTextEdit(); self.notes.setPlaceholderText("Special access notes, scope, etc."); self.notes.setMinimumHeight(64)

        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignRight)
        left_form.addRow("Site Name", self.site_name)
        left_form.addRow("Address", self.address)
        left_form.addRow("POC Name", self.poc_name)
        left_form.addRow("POC Phone", self.poc_phone)
        left_form.addRow("POC Email", self.poc_email)
        left_form.addRow("Service Cadence", self.cadence)
        left_form.addRow("Notes", self.notes)

        # ---------- Contracted Services (right)
        self.grp_services = QGroupBox("Contracted Services")
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Active", "Service", "Price ($)"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)

        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Toolbar
        self.btn_pick = QPushButton("Pick")
        self.btn_add_custom = QPushButton("Add Custom")
        self.btn_dup = QPushButton("Duplicate")
        self.btn_del = QPushButton("Delete")
        for b in (self.btn_pick, self.btn_add_custom, self.btn_dup, self.btn_del):
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        tools = QHBoxLayout()
        tools.addWidget(self.btn_pick)
        tools.addWidget(self.btn_add_custom)
        tools.addWidget(self.btn_dup)
        tools.addWidget(self.btn_del)
        tools.addStretch(1)

        sv = QVBoxLayout(self.grp_services)
        sv.addLayout(tools)
        sv.addWidget(self.tbl, 1)

        # Buttons
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)

        # Two-column body
        body = QHBoxLayout()
        left_col = QWidget(); lc = QVBoxLayout(left_col); lc.setContentsMargins(8, 8, 8, 8)
        right_col = QWidget(); rc = QVBoxLayout(right_col); rc.setContentsMargins(8, 8, 8, 8)
        lc.addLayout(left_form)
        rc.addWidget(self.grp_services)
        body.addWidget(left_col, 1)
        body.addWidget(right_col, 1)

        # Root
        root = QVBoxLayout(self)
        hdr = QLabel("Site Details"); hdr.setObjectName("dlgTitle")
        root.addWidget(hdr)
        root.addWidget(_spacer(6))
        root.addLayout(body, 1)
        root.addLayout(btns)

        # Signals
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_pick.clicked.connect(self._on_pick_from_catalog)
        self.btn_add_custom.clicked.connect(self._on_add_custom)
        self.btn_dup.clicked.connect(self._on_duplicate_selected)
        self.btn_del.clicked.connect(self._on_delete_selected)

        # Keyboard Delete and custom row highlight
        self._orig_keypress = self.tbl.keyPressEvent
        self.tbl.keyPressEvent = self._table_keypress
        self.tbl.currentCellChanged.connect(self._on_current_cell_changed)
        self._last_sel_row: int = -1

        # Data
        self._catalog = []
        self._catalog_by_id = {}
        self._load_obj()
        self._load_catalog()
        self._load_services()

        # Style
        self.setMinimumWidth(720)
        self._apply_style()

    # ---------- Style (match CustomerDialog and improve selection contrast)
    def _apply_style(self):
        self.setStyleSheet("""
        QLabel#dlgTitle { font-size: 18px; font-weight: 600; padding-left: 8px; }
        QGroupBox { font-weight: 600; }
        QLineEdit, QTextEdit, QComboBox { padding: 6px; }

        /* Default item selection colors for tables */
        QTableView::item:selected { background: #e5f3ff; color: #111111; }
        QHeaderView::section {
            font-weight: 600;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 4px 6px;
        }
        QPushButton { padding: 6px 12px; }

        /* Highlight cells that are widgets on the selected row */
        QComboBox[rowSelected="1"],
        QDoubleSpinBox[rowSelected="1"],
        QCheckBox[rowSelected="1"] {
            background: #e5f3ff;
        }
        """)

    # ---------- Row highlight for widget cells
    def _on_current_cell_changed(self, cur_row, cur_col, prev_row, prev_col):
        if prev_row is not None and prev_row >= 0:
            self._set_row_selected(prev_row, False)
        if cur_row is not None and cur_row >= 0:
            self._set_row_selected(cur_row, True)
        self._last_sel_row = cur_row

    def _set_row_selected(self, row: int, sel: bool):
        # Set a dynamic property so QSS above can color the widgets
        for c in range(3):
            w = self.tbl.cellWidget(row, c)
            if w:
                w.setProperty("rowSelected", "1" if sel else "0")
                w.style().unpolish(w); w.style().polish(w)

    # ---------- Actions
    def _on_add_custom(self):
        self._append_row(active=True, name="Custom Service", price_dollars=0.00, service_id=None, catalog_id=None)

    def _on_duplicate_selected(self):
        r = self.tbl.currentRow()
        if r < 0: return
        chk: QCheckBox = self.tbl.cellWidget(r, 0)
        cmb: QComboBox = self.tbl.cellWidget(r, 1)
        spn: QDoubleSpinBox = self.tbl.cellWidget(r, 2)
        active = bool(chk.isChecked()) if chk else True
        name = cmb.currentText().strip() if cmb else "Service"
        price = float(spn.value()) if spn else 0.0
        cat_id = cmb.currentData() if cmb else None
        self._append_row(active=active, name=name, price_dollars=price, service_id=None, catalog_id=cat_id)

    def _on_delete_selected(self):
        r = self.tbl.currentRow()
        if r < 0: return
        it_hidden = self.tbl.item(r, 0)
        svc_id = it_hidden.data(Qt.UserRole) if it_hidden else None
        if svc_id:
            self._deleted_ids.append(int(svc_id))
        self.tbl.removeRow(r)

    def _table_keypress(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._on_delete_selected(); return
        return self._orig_keypress(event)

    def _on_pick_from_catalog(self):
        if not self._catalog:
            QMessageBox.information(self, "Catalog", "No catalog services available. Add some in Catalog Manager.")
            return
        self._safe_rollback_if_needed()
        try:
            dlg = CatalogPickerDialog(self, repo=self._repo)
        except TypeError:
            dlg = CatalogPickerDialog(self)

        # Force readable selected text in the picker
        dlg.setStyleSheet("""
            QTableView::item:selected { background: #e5f3ff; color: #111111; }
        """)

        if dlg.exec():
            ids = []
            if hasattr(dlg, "selected_ids"):
                try: ids = dlg.selected_ids()
                except Exception: ids = []
            elif hasattr(dlg, "selected"):
                ids = dlg.selected()
            for cid in ids:
                cat = self._catalog_by_id.get(cid)
                if not cat: continue
                self._append_row(
                    active=True,
                    name=getattr(cat, "name", "Service") or "Service",
                    price_dollars=_to_dollars(getattr(cat, "default_price_cents", 0)),
                    service_id=None,
                    catalog_id=cid,
                )

    # ---------- Data loading
    def _load_obj(self):
        if not self._obj: return
        self.site_name.setText(self._obj.name or "")
        self.address.setPlainText(self._obj.address or "")
        self.poc_name.setText(self._obj.poc_name or "")
        self.poc_phone.setText(self._obj.poc_phone or "")
        self.poc_email.setText(self._obj.poc_email or "")
        self.cadence.setCurrentText(self._obj.cadence_text or "")
        self.notes.setPlainText(self._obj.notes or "")

    def _load_catalog(self):
        if not self._repo: return
        self._safe_rollback_if_needed()
        try:
            self._catalog = self._repo.list_catalog(active_only=True)
        except Exception:
            self._catalog = []
        self._catalog_by_id = {c.id: c for c in self._catalog}

    def _load_services(self):
        self.tbl.setRowCount(0)
        if not (self._repo and self._obj and getattr(self._obj, "id", None)):
            return
        self._safe_rollback_if_needed()
        try:
            try:
                rows = self._repo.list_services_for_site(self._obj.id, active_only=True)
            except TypeError:
                rows = self._repo.list_services_for_site(self._obj.id)
                rows = [s for s in rows if bool(getattr(s, "active", True))]
            for s in rows:
                self._append_row(
                    active=bool(getattr(s, "active", True)),
                    name=(s.name or ""),
                    price_dollars=_to_dollars(getattr(s, "unit_price_cents", 0)),
                    service_id=s.id,
                    catalog_id=getattr(s, "catalog_id", None),
                )
        except Exception:
            pass

    # ---------- Row helpers
    def _append_row(self, *, active: bool, name: str, price_dollars: float,
                    service_id: Optional[int], catalog_id: Optional[int]):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)

        chk = QCheckBox(); chk.setChecked(active)
        self.tbl.setCellWidget(r, 0, chk)

        cmb = QComboBox(); cmb.setEditable(True)
        for c in self._catalog:
            cmb.addItem(c.name, c.id)
        idx = cmb.findText(name, Qt.MatchExactly)
        if idx < 0:
            cmb.addItem(name or "Custom Service", None)
            idx = cmb.count() - 1
        cmb.setCurrentIndex(idx)
        self.tbl.setCellWidget(r, 1, cmb)

        spn = QDoubleSpinBox()
        spn.setRange(0.00, 999999.00)
        spn.setDecimals(2)
        spn.setSingleStep(1.00)
        spn.setValue(price_dollars)
        spn.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl.setCellWidget(r, 2, spn)

        # hidden ids stored in col 0 and 1 items
        self.tbl.setItem(r, 0, self._mk_hidden(service_id))
        self.tbl.setItem(r, 1, self._mk_hidden(catalog_id))

        def on_changed(_idx, row=r):
            self._row_service_changed(row)
        cmb.currentIndexChanged.connect(on_changed)

        # If this is the first row added, move selection to it to show highlight
        if self.tbl.currentRow() == -1 and r == 0:
            self.tbl.setCurrentCell(0, 1)

    def _row_service_changed(self, row: int):
        cmb: QComboBox = self.tbl.cellWidget(row, 1)
        spn: QDoubleSpinBox = self.tbl.cellWidget(row, 2)
        if not cmb or not spn: return
        selected_cat_id = cmb.currentData()
        it_hidden = self.tbl.item(row, 1)
        if it_hidden:
            it_hidden.setData(Qt.UserRole, selected_cat_id)
        if selected_cat_id is None: return
        cat = self._catalog_by_id.get(selected_cat_id)
        if not cat: return
        spn.setValue(_to_dollars(getattr(cat, "default_price_cents", 0)))

    def _mk_hidden(self, val):
        it = QTableWidgetItem(str(val) if val is not None else "")
        it.setFlags(Qt.ItemIsEnabled)
        it.setData(Qt.UserRole, val)
        it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return it

    # ---------- Extraction and persist
    def _safe_display_name(self, catalog_id: Optional[int], raw_name: str) -> str:
        raw = (raw_name or "").strip()
        if catalog_id is not None:
            cat = self._catalog_by_id.get(catalog_id)
            if cat and getattr(cat, "name", None):
                return cat.name
        return raw if raw else "Service"

    def _extract_row_values(self, row: int) -> dict:
        chk: QCheckBox = self.tbl.cellWidget(row, 0)
        cmb: QComboBox = self.tbl.cellWidget(row, 1)
        spn: QDoubleSpinBox = self.tbl.cellWidget(row, 2)

        item_svc = self.tbl.item(row, 0)
        item_cat = self.tbl.item(row, 1)
        service_id = item_svc.data(Qt.UserRole) if item_svc else None
        catalog_id = item_cat.data(Qt.UserRole) if item_cat else None

        chosen_cat_id = cmb.currentData() if cmb else None
        if chosen_cat_id is not None:
            catalog_id = chosen_cat_id

        raw_name = (cmb.currentText().strip() if cmb else "")
        safe_name = self._safe_display_name(catalog_id, raw_name)

        active = bool(chk.isChecked()) if chk else True
        price_cents = _to_cents(spn.value() if spn else 0.0)

        return dict(
            service_id=int(service_id) if service_id is not None else None,
            catalog_id=int(catalog_id) if catalog_id is not None else None,
            name=safe_name,
            price_cents=price_cents,
            active=active,
        )

    def _safe_rollback_if_needed(self):
        try:
            s = getattr(self._repo, "s", None)
            if s is not None:
                s.rollback()
        except Exception:
            pass

    def _persist_services(self):
        if not (self._repo and self._obj and getattr(self._obj, "id", None)):
            return

        site_id = int(self._obj.id)
        self._safe_rollback_if_needed()

        try:
            # Upsert visible rows
            for r in range(self.tbl.rowCount()):
                vals = self._extract_row_values(r)
                if vals["service_id"]:
                    self._repo.update_site_service(
                        vals["service_id"],
                        name=vals["name"],
                        catalog_id=vals["catalog_id"],
                        unit_price_cents=vals["price_cents"],
                        active=vals["active"],
                    )
                else:
                    self._repo.add_service_to_site(
                        site_id,
                        name=vals["name"],
                        catalog_id=vals["catalog_id"],
                        unit_price_cents=vals["price_cents"],
                    )

            # Apply removals last
            for svc_id in self._deleted_ids:
                if hasattr(self._repo, "delete_site_service"):
                    try:
                        self._repo.delete_site_service(int(svc_id))
                        continue
                    except Exception:
                        pass
                self._repo.update_site_service(int(svc_id), active=False)
            self._deleted_ids.clear()

            s = getattr(self._repo, "s", None)
            if s is not None:
                s.flush()
                s.commit()

        except Exception as e:
            self._safe_rollback_if_needed()
            QMessageBox.critical(
                self, "Save Failed",
                "Could not save Site services. The form will remain open.\n\n"
                f"Details:\n{e}"
            )
            raise

    # ---------- Save + values
    def _on_save(self):
        if not self.site_name.text().strip():
            QMessageBox.warning(self, "Missing", "Site name is required.")
            self.site_name.setFocus(); return
        try:
            if self._obj is not None:
                self._obj.name = self.site_name.text().strip()
                self._obj.address = self.address.toPlainText().strip()
                self._obj.poc_name = self.poc_name.text().strip()
                self._obj.poc_phone = self.poc_phone.text().strip()
                self._obj.poc_email = self.poc_email.text().strip()
                self._obj.cadence_text = self.cadence.currentText().strip()
                self._obj.notes = self.notes.toPlainText().strip()
            self._persist_services()
        except Exception:
            return
        self.accept()

    def values(self) -> dict:
        """
        Collect the current site fields from the dialog into a dictionary.
        
        When this dialog was used to create a new site (no backing _obj), also includes
        "services_selected_names": a list of display names for services with the Active
        checkbox checked in the services table.
        
        Returns:
            dict: Dictionary with keys:
                - name: site name string
                - address: address string
                - poc_name: point-of-contact name string
                - poc_phone: point-of-contact phone string
                - poc_email: point-of-contact email string
                - cadence_text: cadence selection string
                - notes: notes string
                - services_selected_names (optional): list of service display names selected in the table
        """
        vals = dict(
            name=self.site_name.text().strip(),
            address=self.address.toPlainText().strip(),
            poc_name=self.poc_name.text().strip(),
            poc_phone=self.poc_phone.text().strip(),
            poc_email=self.poc_email.text().strip(),
            cadence_text=self.cadence.currentText().strip(),
            notes=self.notes.toPlainText().strip(),
        )
        if not getattr(self, "_obj", None):
            selected: List[str] = []
            for r in range(self.tbl.rowCount()):
                chk = self.tbl.cellWidget(r, 0)
                if chk and chk.isChecked():
                    cmb = self.tbl.cellWidget(r, 1)
                    raw = (cmb.currentText().strip() if cmb else "")
                    cat_id = cmb.currentData() if cmb else None
                    name = self._safe_display_name(cat_id, raw)
                    if name:
                        selected.append(name)
            vals["services_selected_names"] = selected
        return vals
# coderabbit-review-marker