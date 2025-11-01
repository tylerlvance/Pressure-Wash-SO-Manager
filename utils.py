# -----------------------------
# File: utils.py
# -----------------------------
from __future__ import annotations
from PySide6.QtWidgets import QFileDialog, QWidget


def pick_file(parent: QWidget) -> str | None:
    path, _ = QFileDialog.getOpenFileName(parent, "Select File", "", "All Files (*.*)")
    return path or None