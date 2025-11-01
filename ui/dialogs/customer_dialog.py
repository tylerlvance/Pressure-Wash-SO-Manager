# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QLabel, QPushButton, QComboBox, QCheckBox, QSpinBox, QGroupBox, QMessageBox
)

def _spacer(px: int = 8) -> QWidget:
    w = QWidget()
    w.setFixedHeight(px)
    return w


class CustomerDialog(QDialog):
    """
    Modern Customer dialog
    - Left column: core customer info
    - Right column: payment profile (optional), tidy groups
    - values() returns the same shape you already use, including optional 'payment_profile'
    """
    def __init__(self, parent=None, obj=None, repo=None):
        super().__init__(parent)
        self.setWindowTitle("Customer")
        self._obj = obj
        self._repo = repo

        # ---------- Core fields
        self.name = QLineEdit();  self.name.setPlaceholderText("Company or contact")
        self.phone = QLineEdit(); self.phone.setPlaceholderText("###-###-####")
        self.email = QLineEdit(); self.email.setPlaceholderText("name@example.com")
        self.notes = QTextEdit(); self.notes.setPlaceholderText("Notes for dispatch, billing, or scope")
        self.notes.setMinimumHeight(80)

        # ---------- Payment profile (optional)
        self.grp_pay = QGroupBox("Payment Profile (optional)")
        self.cmb_method = QComboBox(); self.cmb_method.addItems(["Other", "ACH", "Card", "Check"])
        self.bill_street = QLineEdit();       self.bill_street.setPlaceholderText("123 Main St, Suite 200")
        self.bill_city_state_zip = QLineEdit(); self.bill_city_state_zip.setPlaceholderText("City, ST 99999")

        # ACH
        self.ach_routing = QLineEdit(); self.ach_routing.setPlaceholderText("Routing")
        self.ach_account = QLineEdit(); self.ach_account.setPlaceholderText("Account")

        # Card
        self.card_brand = QLineEdit(); self.card_brand.setPlaceholderText("Visa, MC, Amex")
        self.card_last4 = QLineEdit(); self.card_last4.setPlaceholderText("1234")
        self.card_name = QLineEdit();  self.card_name.setPlaceholderText("Name on card")
        self.card_exp_month = QSpinBox(); self.card_exp_month.setRange(0, 12)
        self.card_exp_year = QSpinBox();  self.card_exp_year.setRange(0, 2100)
        self.chk_default = QCheckBox("Default for this customer")

        # ---------- Layouts
        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignRight)
        left_form.addRow("Customer Name", self.name)
        left_form.addRow("Phone", self.phone)
        left_form.addRow("Email", self.email)
        left_form.addRow("Notes", self.notes)

        pay_form = QFormLayout()
        pay_form.setLabelAlignment(Qt.AlignRight)
        pay_form.addRow("Method", self.cmb_method)
        pay_form.addRow("Billing Street", self.bill_street)
        pay_form.addRow("City/State/ZIP", self.bill_city_state_zip)

        # Sub-groups inline labels for clarity
        pay_form.addRow(QLabel("ACH"))
        pay_form.addRow("Routing", self.ach_routing)
        pay_form.addRow("Account", self.ach_account)

        pay_form.addRow(QLabel("Card"))
        pay_form.addRow("Brand", self.card_brand)
        pay_form.addRow("Last4", self.card_last4)
        pay_form.addRow("Name on Card", self.card_name)
        pay_form.addRow("Exp. Month", self.card_exp_month)
        pay_form.addRow("Exp. Year", self.card_exp_year)
        pay_form.addRow("", self.chk_default)

        pay_wrap = QVBoxLayout(self.grp_pay)
        pay_wrap.addLayout(pay_form)

        # Buttons
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)

        # Two-column root
        body = QHBoxLayout()
        left_col = QWidget(); lc = QVBoxLayout(left_col); lc.setContentsMargins(8, 8, 8, 8)
        right_col = QWidget(); rc = QVBoxLayout(right_col); rc.setContentsMargins(8, 8, 8, 8)

        lc.addLayout(left_form)
        rc.addWidget(self.grp_pay)

        body.addWidget(left_col, 1)
        body.addWidget(right_col, 1)

        root = QVBoxLayout(self)
        hdr = QLabel("Customer")
        hdr.setObjectName("dlgTitle")
        root.addWidget(hdr)
        root.addWidget(_spacer(6))
        root.addLayout(body, 1)
        root.addLayout(btns)

        # Signals
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)
        self.cmb_method.currentTextChanged.connect(self._toggle_payment_fields)

        # Polishing
        self.setMinimumWidth(720)
        self._apply_style()
        self._load_obj()
        self._toggle_payment_fields(self.cmb_method.currentText())

    # ---------- Style
    def _apply_style(self):
        self.setStyleSheet("""
        QLabel#dlgTitle { font-size: 18px; font-weight: 600; padding-left: 8px; }
        QGroupBox { font-weight: 600; }
        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            padding: 6px;
        }
        QPushButton {
            padding: 6px 12px;
        }
        """)

    # ---------- Data
    def _load_obj(self):
        if not self._obj:
            return
        self.name.setText(self._obj.name or "")
        self.phone.setText(self._obj.phone or "")
        self.email.setText(self._obj.email or "")
        self.notes.setText(self._obj.notes or "")

    def _toggle_payment_fields(self, method_text: str):
        method = (method_text or "Other").lower()
        use_ach = method == "ach"
        use_card = method == "card"

        for w in (self.ach_routing, self.ach_account):
            w.setEnabled(use_ach)
        for w in (self.card_brand, self.card_last4, self.card_name, self.card_exp_month, self.card_exp_year):
            w.setEnabled(use_card)

    # ---------- Output
    def values(self) -> dict:
        """
        Returns:
          {
            name, phone, email, notes,
            payment_profile: {
              method, billing_street, billing_city_state_zip, default,
              ach_routing, ach_account,    (if ACH)
              card_brand, card_last4, card_name, card_exp_month, card_exp_year  (if Card)
            }   # only present if any payment data entered or method != Other
          }
        """
        vals = dict(
            name=self.name.text().strip(),
            phone=self.phone.text().strip(),
            email=self.email.text().strip(),
            notes=self.notes.toPlainText().strip(),
        )

        method_text = (self.cmb_method.currentText() or "Other").strip()
        touched = any([
            self.bill_street.text().strip(),
            self.bill_city_state_zip.text().strip(),
            self.ach_routing.text().strip(),
            self.ach_account.text().strip(),
            self.card_brand.text().strip(),
            self.card_last4.text().strip(),
            self.card_name.text().strip(),
            self.card_exp_month.value() > 0,
            self.card_exp_year.value() > 0,
            self.chk_default.isChecked(),
        ])

        if touched or method_text != "Other":
            pp = dict(
                method=method_text.lower(),
                billing_street=self.bill_street.text().strip(),
                billing_city_state_zip=self.bill_city_state_zip.text().strip(),
                default=self.chk_default.isChecked(),
            )
            if pp["method"] == "ach":
                pp.update(
                    ach_routing=self.ach_routing.text().strip(),
                    ach_account=self.ach_account.text().strip(),
                )
            elif pp["method"] == "card":
                pp.update(
                    card_brand=self.card_brand.text().strip(),
                    card_last4=self.card_last4.text().strip(),
                    card_name=self.card_name.text().strip(),
                    card_exp_month=int(self.card_exp_month.value()),
                    card_exp_year=int(self.card_exp_year.value()),
                )
            vals["payment_profile"] = pp

        return vals

    # ---------- Save handler
    def _on_save(self):
        """
        Validate required fields and close the dialog if valid.
        
        Checks that the name field contains non-whitespace text; if empty, shows a warning message, focuses the name field, and does not close the dialog. If the name is present, accepts the dialog.
        """
        if not self.name.text().strip():
            QMessageBox.warning(self, "Missing", "Customer name is required.")
            self.name.setFocus()
            return
        self.accept()
# coderabbit-review-marker