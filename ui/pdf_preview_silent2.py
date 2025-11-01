from __future__ import annotations
# -*- coding: utf-8 -*-
import os, tempfile
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QMessageBox
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView


class SilentPdfPreview(QWidget):
    """Silent PDF preview. No message boxes; returns True/False."""
    VERSION = "silent-2"

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

    # ---- popup janitor -------------------------------------------------
    @staticmethod
    def _sweep_noerror_boxes():
        """Close any stray QMessageBox that looks like the 'Preview… / NoError' box."""
        app = QApplication.instance()
        if not app:
            return
        for w in app.topLevelWidgets():
            if isinstance(w, QMessageBox):
                title = (w.windowTitle() or "").strip()
                text = (w.text() or "").strip()
                if title.startswith("Preview") or text == "NoError":
                    # close immediately without user interaction
                    try:
                        w.done(0)
                    except Exception:
                        pass
                    try:
                        w.close()
                    except Exception:
                        pass

    def load_pdf(self, path: str) -> bool:
        """Load a PDF quietly, avoiding Qt's stray 'NoError' popup."""
        if not path or not os.path.isfile(path):
            return False

        # First sweep, in case something fires synchronously
        SilentPdfPreview._sweep_noerror_boxes()

        try:
            status = self.doc.load(path)
        except Exception:
            # Rare QtPdf quirk: schedule async load to avoid native popup
            QTimer.singleShot(0, lambda p=path: self.doc.load(p))
            self.view.setPageMode(QPdfView.PageMode.MultiPage)
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self._temp_pdf = path
            # Sweep again shortly after
            QTimer.singleShot(0, SilentPdfPreview._sweep_noerror_boxes)
            QTimer.singleShot(50, SilentPdfPreview._sweep_noerror_boxes)
            return True

        ok = (
            self.doc.error() == QPdfDocument.Error.NoError
            and status == QPdfDocument.Error.NoError
        )
        if ok:
            self._temp_pdf = path
            self.view.setPageMode(QPdfView.PageMode.MultiPage)
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

        # Sweep after successful load, too (some builds show late)
        QTimer.singleShot(0, SilentPdfPreview._sweep_noerror_boxes)
        QTimer.singleShot(50, SilentPdfPreview._sweep_noerror_boxes)

        return ok
# coderabbit-review-marker
