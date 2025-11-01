from __future__ import annotations
# -*- coding: utf-8 -*-

import os, shutil, tempfile
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView

class PdfPreview(QWidget):
    """Silent PDF preview. load_pdf() returns True/False. No message boxes."""
    VERSION = "silent-1"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._temp_pdf: Optional[str] = None
        self.doc = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.doc)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)

    def new_temp_path(self) -> str:
        fd, path = tempfile.mkstemp(prefix="preview_", suffix=".pdf")
        os.close(fd)
        return path

    def load_pdf(self, path: str) -> bool:
        if not path or not os.path.isfile(path):
            return False
        status = self.doc.load(path)
        ok = (self.doc.error() == QPdfDocument.Error.NoError) and (status == QPdfDocument.Error.NoError)
        if ok:
            self._temp_pdf = path
            self.view.setPageMode(QPdfView.PageMode.MultiPage)
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        return ok

    def save_preview_as(self, target_path: str) -> bool:
        if not self._temp_pdf or not os.path.isfile(self._temp_pdf):
            return False
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copyfile(self._temp_pdf, target_path)
        return True

    def has_preview(self) -> bool:
        return bool(self._temp_pdf)
# coderabbit-review-marker
