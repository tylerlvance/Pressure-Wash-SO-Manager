# -----------------------------
# File: utils.py
# -----------------------------
from __future__ import annotations
from PySide6.QtWidgets import QFileDialog, QWidget


def pick_file(parent: QWidget) -> str | None:
    """
    Open a file-selection dialog and return the chosen file path.
    
    Displays a file-open dialog titled "Select File" with the filter "All Files (*.*)". If a file is selected its filesystem path is returned; if the dialog is canceled or no file is chosen, returns None.
    
    Parameters:
        parent (QWidget): Owner widget for the file dialog.
    
    Returns:
        str | None: The selected file path, or `None` if no file was selected.
    """
    path, _ = QFileDialog.getOpenFileName(parent, "Select File", "", "All Files (*.*)")
    return path or None# coderabbit-review-marker