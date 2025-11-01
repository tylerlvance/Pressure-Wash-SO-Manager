# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit, QDateEdit,
    QCheckBox, QGroupBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QListWidget, QListWidgetItem
)

from ..employee_dialogs import AssignStaffDialog


def _to_dollars(cents: int) -> float:
    return float(cents or 0) / 100.0


class ServiceOrderDialog(QDialog):
    """
    Shows and edits a Service Order.
    Adds a read-only "Assigned Staff" panel that lists names and roles.
    """
    def __init__(self, parent=None, site_name: str = "", obj=None, repo=None):
        super().__init__(parent)
        self.setWindowTitle(f"Service Order - {site_name}" if site_name else "Service Order")
        self._obj = obj            # models.ServiceOrder or None
        self._repo = repo          # Repo

        # --- core fields
        self.title = QLineEdit()
        self.description = QTextEdit(); self.description.setFixedHeight(60)
        self.scheduled = QDateEdit(); self.scheduled.setCalendarPopup(True); self.scheduled.setDate(QDate.currentDate())
        self.completed = QCheckBox("Completed")
        self.invoiced = QCheckBox("Invoiced"); self.invoiced.setEnabled(False)
        self.notes = QTextEdit(); self.notes.setFixedHeight(60)

        # --- included services table (read only)
        self.grp_inc = QGroupBox("Included Services (snapshot)")
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["Service", "Price ($)"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        lv = QVBoxLayout(self.grp_inc)
        lv.addWidget(self.tbl, 1)

        # --- assigned staff (NEW)
        self.grp_staff = QGroupBox("Assigned Staff")
        self.staff_list = QListWidget()
        self.staff_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.staff_list.setAlternatingRowColors(True)
        self.btn_assign = QPushButton("Assign...")
        self.btn_refresh_staff = QPushButton("Refresh")
        sbtns = QHBoxLayout()
        sbtns.addStretch(1)
        sbtns.addWidget(self.btn_refresh_staff)
        sbtns.addWidget(self.btn_assign)
        sv = QVBoxLayout(self.grp_staff)
        sv.addWidget(self.staff_list, 1)
        sv.addLayout(sbtns)

        # --- buttons
        self.btn_ok = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)

        # --- form layout
        form = QFormLayout()
        form.addRow("Title", self.title)
        form.addRow("Description", self.description)
        form.addRow("Scheduled Date", self.scheduled)
        form.addRow("", self.completed)
        form.addRow("", self.invoiced)
        form.addRow("Notes", self.notes)

        # --- root layout
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.grp_inc, 1)
        root.addWidget(self.grp_staff, 1)
        root.addLayout(btns)

        # signals
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_refresh_staff.clicked.connect(self._load_assignments)
        self.btn_assign.clicked.connect(self._open_assign_dialog)

        # populate
        self._load_obj()
        self._load_included_services()
        self._load_assignments()

    # ----- data loads
    def _load_obj(self):
        if not self._obj:
            return
        self.title.setText(self._obj.title or "")
        self.description.setPlainText(self._obj.description or "")
        if self._obj.scheduled_date:
            y, m, d = self._obj.scheduled_date.year, self._obj.scheduled_date.month, self._obj.scheduled_date.day
            self.scheduled.setDate(QDate(y, m, d))
        self.completed.setChecked(bool(self._obj.completed))
        self.invoiced.setChecked(bool(self._obj.invoiced))
        self.notes.setPlainText(self._obj.notes or "")

    def _load_included_services(self):
        self.tbl.setRowCount(0)
        if not (self._repo and self._obj and getattr(self._obj, "id", None)):
            return
        try:
            links = self._repo.list_services_for_so(self._obj.id)
            for lk in links:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)
                nm = lk.site_service.name if lk.site_service else "Service"
                price = _to_dollars(getattr(lk, "unit_price_cents", 0))
                self.tbl.setItem(r, 0, QTableWidgetItem(nm))
                itp = QTableWidgetItem(f"{price:.2f}")
                itp.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(r, 1, itp)
        except Exception:
            pass

    def _load_assignments(self):
        """Fill the read-only staff list with 'Name  |  Role' for this SO."""
        self.staff_list.clear()
        if not (self._repo and self._obj and getattr(self._obj, "id", None)):
            return
        try:
            assigns = self._repo.list_assignments_for_so(self._obj.id)
        except Exception:
            assigns = []

        # Build lines
        if not assigns:
            self.staff_list.addItem(QListWidgetItem("No staff assigned"))
            return

        for a in assigns:
            # a.employee is relationship; repo methods set it
            emp = getattr(a, "employee", None)
            if emp:
                text = f"{emp.name}  |  {emp.role or 'Staff'}"
            else:
                text = f"Employee #{a.employee_id}"
            self.staff_list.addItem(QListWidgetItem(text))

    # ----- assign button
    def _open_assign_dialog(self):
        if not (self._repo and self._obj and getattr(self._obj, "id", None)):
            return
        dlg = AssignStaffDialog(self, repo=self._repo, so_id=int(self._obj.id))
        dlg.exec()
        # refresh after dialog closes
        self._load_assignments()

    # ----- values out
    def values(self) -> dict:
        sd = self.scheduled.date().toPython()
        return dict(
            title=self.title.text().strip(),
            description=self.description.toPlainText().strip(),
            scheduled_date=sd,
            completed=self.completed.isChecked(),
            invoiced=self.invoiced.isChecked(),
            notes=self.notes.toPlainText().strip(),
        )
