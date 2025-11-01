# -*- coding: utf-8 -*-
from __future__ import annotations
# -*- coding: utf-8 -*-

from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLineEdit,
    QLabel, QPushButton, QFormLayout, QComboBox, QCheckBox, QMessageBox
)

# Expects repo helpers:
#   - Repo.list_employees(active_only=True/False)
#   - Repo.create_employee(...)
#   - Repo.update_employee(emp_id, **kwargs)
#   - Repo.delete_employee(emp_id)
#   - Repo.list_assignments_for_so(so_id)
#   - Repo.assign_employee(so_id, emp_id, role="Primary")
#   - Repo.unassign_employee(so_id, emp_id)


# ----------------------------
# Employee Manager Dialog
# ----------------------------
class EmployeeManagerDialog(QDialog):
    """
    Simple CRUD for employees.
    Left: searchable list of employees (all or active-only).
    Right: details editor (name, role, phone, email, active).
    """
    def __init__(self, parent=None, repo=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Staff")
        self.repo = repo

        # ---- Left: list + search ----
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name/role/phone/email...")
        self.chk_active_only = QCheckBox("Active only")
        sheck = True
        self.chk_active_only.setChecked(True)

        self.list = QListWidget()
        self.list.setMinimumWidth(260)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(8, 8, 8, 8)
        left_lay.addWidget(self.search)
        left_lay.addWidget(self.chk_active_only)
        left_lay.addWidget(self.list, 1)

        # ---- Right: details form ----
        self.name = QLineEdit()
        self.role = QComboBox(); self.role.addItems(["Technician", "Manager", "Supervisor", "Owner"])
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.active = QCheckBox("Active")

        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Role", self.role)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("", self.active)

        self.btn_new = QPushButton("+ New")
        self.btn_save = QPushButton("Save")
        self.btn_delete = QPushButton("Delete")
        self.btn_close = QPushButton("Close")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_new)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_close)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 8, 8, 8)
        right_lay.addLayout(form)
        right_lay.addStretch(1)
        right_lay.addLayout(btn_row)

        # ---- Root ----
        root = QHBoxLayout(self)
        root.addWidget(left, 1)
        root.addWidget(right, 2)

        # ---- Signals ----
        self.search.textChanged.connect(self._populate)
        self.chk_active_only.toggled.connect(self._populate)
        self.list.currentItemChanged.connect(self._on_select)
        self.btn_new.clicked.connect(self._new)
        self.btn_save.clicked.connect(self._save)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_close.clicked.connect(self.accept)

        # ---- State ----
        self._current_id: Optional[int] = None
        self._populate()

    # --- helpers ---
    def _populate(self):
        self.list.clear()
        if not self.repo:
            return
        query = (self.search.text() or "").strip().lower()
        active_only = self.chk_active_only.isChecked()
        try:
            rows = self.repo.list_employees(active_only=active_only)
        except Exception:
            rows = []

        for e in rows:
            txt = f"{e.name}  |  {e.role}"
            if e.phone:
                txt += f"  |  {e.phone}"
            item = QListWidgetItem(txt)
            item.setData(Qt.UserRole, e.id)
            # visually show inactive if not filtered
            if not e.active:
                item.setForeground(Qt.gray)
            self.list.addItem(item)

        # clear the form if list no longer contains current item
        self._maybe_clear_if_missing()

        # basic search filter (client-side)
        if query:
            # hide by removing non-matching items
            for i in reversed(range(self.list.count())):
                it = self.list.item(i)
                if query not in it.text().lower():
                    self.list.takeItem(i)

    def _maybe_clear_if_missing(self):
        if self._current_id is None:
            return
        ids = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if self._current_id not in ids:
            self._clear_form()

    def _on_select(self, cur: QListWidgetItem, prev: QListWidgetItem):
        if not cur:
            self._current_id = None
            self._clear_form()
            return
        emp_id = int(cur.data(Qt.UserRole))
        self._current_id = emp_id
        # fetch fresh via repo session
        e = None
        try:
            # try direct get using the mapped class from list
            rows = self.repo.list_employees(active_only=False)
            if rows:
                e = self.repo.s.get(type(rows[0]), emp_id)
        except Exception:
            e = None
        if e is None:
            # fallback: search rows
            for row in self.repo.list_employees(active_only=False):
                if row.id == emp_id:
                    e = row
                    break
        if not e:
            self._clear_form()
            return
        self.name.setText(e.name or "")
        self.role.setCurrentText(e.role or "Technician")
        self.phone.setText(e.phone or "")
        self.email.setText(e.email or "")
        self.active.setChecked(bool(e.active))

    def _clear_form(self):
        self.name.clear()
        self.role.setCurrentText("Technician")
        self.phone.clear()
        self.email.clear()
        self.active.setChecked(True)

    def _new(self):
        self._current_id = None
        self._clear_form()
        self.name.setFocus()

    def _save(self):
        vals = dict(
            name=self.name.text().strip(),
            role=self.role.currentText().strip(),
            phone=self.phone.text().strip(),
            email=self.email.text().strip(),
            active=self.active.isChecked(),
        )
        if not vals["name"]:
            QMessageBox.warning(self, "Missing", "Employee name is required.")
            return
        try:
            if self._current_id is None:
                e = self.repo.create_employee(**vals)
                self._current_id = e.id
            else:
                self.repo.update_employee(self._current_id, **vals)
            self._populate()
            self._select_by_id(self._current_id)
        except Exception as ex:
            QMessageBox.critical(self, "Save Failed", str(ex))

    def _select_by_id(self, emp_id: Optional[int]):
        if emp_id is None:
            return
        for i in range(self.list.count()):
            it = self.list.item(i)
            if int(it.data(Qt.UserRole)) == emp_id:
                self.list.setCurrentRow(i)
                break

    def _delete(self):
        if self._current_id is None:
            QMessageBox.information(self, "Select", "Pick a staff member first.")
            return
        ok = QMessageBox.question(self, "Confirm", "Delete this staff member?", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        try:
            self.repo.delete_employee(self._current_id)
            self._current_id = None
            self._populate()
        except Exception as ex:
            QMessageBox.critical(self, "Delete Failed", str(ex))


# ----------------------------
# Assign Staff to SO Dialog
# ----------------------------
class AssignStaffDialog(QDialog):
    """
    Assign/unassign employees to a Service Order using checkboxes.
    - Left: active employees list with checkboxes
    - Right: quick info and Apply/Close buttons

    Usage:
        dlg = AssignStaffDialog(self, repo=repo, so_id=123)
        dlg.exec()
    """
    def __init__(self, parent=None, repo=None, so_id: int | None = None):
        super().__init__(parent)
        self.setWindowTitle("Assign Staff")
        self.repo = repo
        self.so_id = int(so_id) if so_id is not None else None

        # Left column: checkable list of employees
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setAlternatingRowColors(True)
        self.list.setMinimumWidth(360)

        # Right column: info + buttons
        self.lbl_info = QLabel("Check employees to assign to this Service Order.")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_apply = QPushButton("Apply")
        self.btn_close = QPushButton("Close")

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(8, 8, 8, 8)
        rlay.addWidget(self.lbl_info)
        rlay.addStretch(1)
        btns = QHBoxLayout()
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_close)
        rlay.addLayout(btns)

        root = QHBoxLayout(self)
        root.addWidget(self.list, 1)
        root.addWidget(right, 0)

        # Signals
        self.btn_refresh.clicked.connect(self._populate)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.accept)

        # Initial load
        self._populate()

    def _populate(self):
        self.list.clear()
        if not (self.repo and self.so_id):
            return
        # active employees
        try:
            emps = self.repo.list_employees(active_only=True)
        except Exception:
            emps = []

        # current assignments
        assigned_ids = set()
        try:
            assigns = self.repo.list_assignments_for_so(self.so_id)
            for a in assigns:
                assigned_ids.add(int(a.employee_id))
        except Exception:
            pass

        for e in emps:
            item = QListWidgetItem(f"{e.name}  |  {e.role}")
            item.setData(Qt.UserRole, int(e.id))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if int(e.id) in assigned_ids else Qt.Unchecked)
            self.list.addItem(item)

        self.lbl_info.setText(f"Active employees: {self.list.count()}  |  Assigned: {len(assigned_ids)}")

    def _apply(self):
        """Unassign anyone unchecked, then assign all checked."""
        if not (self.repo and self.so_id):
            return

        # Gather checked employee ids
        checked_ids = set()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.checkState() == Qt.Checked:
                checked_ids.add(int(it.data(Qt.UserRole)))

        errs = []

        # Unassign all that are currently assigned but unchecked
        try:
            current = self.repo.list_assignments_for_so(self.so_id)
        except Exception as ex:
            current = []
            errs.append(str(ex))

        for a in current:
            if int(a.employee_id) not in checked_ids:
                try:
                    self.repo.unassign_employee(self.so_id, int(a.employee_id))
                except Exception as ex:
                    errs.append(str(ex))

        # Assign all checked ids
        for emp_id in sorted(checked_ids):
            try:
                # accept extra kwargs but they are optional in Repo
                self.repo.assign_employee(self.so_id, emp_id, role="Primary")
            except Exception as ex:
                errs.append(str(ex))

        if errs:
            QMessageBox.warning(self, "Partial Success", "Some changes failed:\n" + "\n".join(errs))
            self._populate()
            return

        QMessageBox.information(self, "Saved", "Staff assignments updated.")
        self._populate()
