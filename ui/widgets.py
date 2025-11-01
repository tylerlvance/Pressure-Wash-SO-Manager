from __future__ import annotations
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableView
from models import ServiceOrder


class SoTableModel(QAbstractTableModel):
    HEADERS = ["Scheduled", "Customer", "Site", "Title", "Completed", "Invoiced"]

    def __init__(self, rows: list[ServiceOrder], repo=None):
        """
        repo is kept for backward compatibility but unused here (no inline edits).
        """
        super().__init__()
        self.rows = rows
        self.repo = repo  # not used (no checkboxes / inline update)

    # ---- required model API ----
    def rowCount(self, parent=None):
        return len(self.rows)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        so = self.rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return so.scheduled_date.isoformat() if so.scheduled_date else ""
            if col == 1:
                return so.site.customer.name if so.site and so.site.customer else ""
            if col == 2:
                return so.site.name if so.site else ""
            if col == 3:
                return so.title or ""
            if col == 4:
                # simple text status (no checkbox)
                return "Yes" if so.completed else ""
            if col == 5:
                return "Yes" if so.invoiced else ""

        if role == Qt.BackgroundRole:
            # Visual status (green tints)
            if so.completed:
                # Deeper green for completed
                return QColor(200, 245, 200)
            elif so.invoiced:
                # Lighter green for invoiced (but not completed)
                return QColor(225, 250, 225)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex):
        # Read-only, selectable rows (no checkboxes, no edits)
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    # Convenience when resetting rows from the outside
    def setRows(self, rows: list[ServiceOrder]):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class SoTable(QTableView):
    def __init__(self, repo=None):
        super().__init__()
        self.repo = repo  # kept for parity; not required here
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)

    def setModel(self, model: SoTableModel):
        super().setModel(model)
        # Auto-size some columns for clarity
        self.resizeColumnsToContents()
# coderabbit-review-marker
