# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# -----------------------------
# Core tables
# -----------------------------

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    phone = Column(String(100), default="")
    email = Column(String(200), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    sites = relationship("Site", back_populates="customer", cascade="all, delete-orphan")
    payment_profiles = relationship("PaymentProfile", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Customer(id={self.id}, name={self.name})"


class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(Text, default="")
    poc_name = Column(String(200), default="")
    poc_phone = Column(String(100), default="")
    poc_email = Column(String(200), default="")
    scope_of_work = Column(Text, default="")
    area_zone = Column(String(200), default="")
    cadence_text = Column(String(200), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="sites")
    service_orders = relationship("ServiceOrder", back_populates="site", cascade="all, delete-orphan")
    services = relationship("SiteService", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Site(id={self.id}, name={self.name})"


class ServiceOrder(Base):
    __tablename__ = "service_orders"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), default="")
    description = Column(Text, default="")
    scheduled_date = Column(Date, nullable=True)
    completed = Column(Boolean, default=False)
    invoiced = Column(Boolean, default=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="service_orders")
    invoice = relationship("Invoice", back_populates="service_order", uselist=False, cascade="all, delete-orphan")
    staff_assignments = relationship("ServiceOrderAssignment", back_populates="service_order", cascade="all, delete-orphan")
    so_services = relationship("SOService", back_populates="service_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"SO(id={self.id}, site_id={self.site_id}, scheduled={self.scheduled_date})"


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(32), nullable=False)  # "service_order", "invoice", etc.
    entity_id = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

# -----------------------------
# Additive / auxiliary tables
# -----------------------------

class PaymentProfile(Base):
    __tablename__ = "payment_profiles"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)

    method = Column(String(16), default="other")   # "ach", "card", "check", "other"

    # ACH (display only)
    ach_routing = Column(String(32), default="")
    ach_account = Column(String(32), default="")

    # Card (display only)
    card_brand = Column(String(32), default="")
    card_last4 = Column(String(8), default="")
    card_name = Column(String(200), default="")
    card_exp_month = Column(Integer, default=0)
    card_exp_year = Column(Integer, default=0)

    bill_street = Column(Text, default="")
    bill_city_state_zip = Column(String(200), default="")

    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="payment_profiles")

    def __repr__(self):
        return f"PaymentProfile(id={self.id}, customer_id={self.customer_id}, method={self.method})"


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    role = Column(String(64), default="Technician")
    phone = Column(String(100), default="")
    email = Column(String(200), default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assignments = relationship("ServiceOrderAssignment", back_populates="employee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Employee(id={self.id}, name={self.name})"


class ServiceOrderAssignment(Base):
    __tablename__ = "so_assignments"
    id = Column(Integer, primary_key=True)
    service_order_id = Column(Integer, ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    service_order = relationship("ServiceOrder", back_populates="staff_assignments")
    employee = relationship("Employee", back_populates="assignments")

    __table_args__ = (UniqueConstraint("service_order_id", "employee_id", name="uq_so_employee"),)

# -----------------------------
# Invoicing
# -----------------------------

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    service_order_id = Column(Integer, ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False, unique=True)

    invoice_no = Column(String(64), nullable=False)
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    subtotal_cents = Column(Integer, default=0)
    tax_cents = Column(Integer, default=0)
    total_cents = Column(Integer, default=0)

    paid = Column(Boolean, default=False)
    notes = Column(Text, default="")
    pdf_path = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    service_order = relationship("ServiceOrder", back_populates="invoice")

    def __repr__(self):
        return f"Invoice(id={self.id}, so_id={self.service_order_id}, no={self.invoice_no})"

# -----------------------------
# Services and pricing
# -----------------------------

class ServiceCatalog(Base):
    """
    Global catalog of named services with a default price.
    Store price in cents for integer math and expose a pythonic `default_rate` in dollars.
    """
    __tablename__ = "service_catalog"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    default_price_cents = Column(Integer, nullable=False, default=0)
    description = Column(Text, default="")  # new
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Dollars-facing property used by Catalog Manager UI
    @property
    def default_rate(self) -> float:
        return float(self.default_price_cents or 0) / 100.0

    @default_rate.setter
    def default_rate(self, value: float) -> None:
        try:
            cents = int(round(float(value or 0.0) * 100))
        except Exception:
            cents = 0
        self.default_price_cents = max(cents, 0)

    def __repr__(self):
        return f"ServiceCatalog(id={self.id}, name={self.name}, default={self.default_price_cents})"


class SiteService(Base):
    """
    Contracted service at a Site, with optional price override from the catalog.
    """
    __tablename__ = "site_services"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)  # legacy free-text name (kept for compatibility)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # link to catalog + pricing override
    catalog_id = Column(Integer, ForeignKey("service_catalog.id", ondelete="SET NULL"), nullable=True)
    unit_price_cents = Column(Integer, nullable=False, default=0)

    site = relationship("Site", back_populates="services")
    catalog = relationship("ServiceCatalog")
    so_links = relationship("SOService", back_populates="site_service", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_site_service_name"),)

    def __repr__(self):
        return f"SiteService(id={self.id}, site_id={self.site_id}, name={self.name}, price={self.unit_price_cents})"


class SOService(Base):
    """
    Snapshot of services included on a specific SO, with frozen price at scheduling time.
    """
    __tablename__ = "so_services"
    id = Column(Integer, primary_key=True)
    service_order_id = Column(Integer, ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False)
    site_service_id = Column(Integer, ForeignKey("site_services.id", ondelete="CASCADE"), nullable=False)

    # price snapshot for this SO line
    unit_price_cents = Column(Integer, nullable=False, default=0)

    service_order = relationship("ServiceOrder", back_populates="so_services")
    site_service = relationship("SiteService", back_populates="so_links")

    __table_args__ = (UniqueConstraint("service_order_id", "site_service_id", name="uq_so_service_link"),)

# Backwards-compat alias used by repository and UI code
SOAssignment = ServiceOrderAssignment

# Alias so catalog_manager.py can `from models import CatalogService`
CatalogService = ServiceCatalog


# ---- Optional one-time helper to add new column if DB already exists ----
# Run this once at startup or from a tiny admin script if you created the DB earlier.
def ensure_service_catalog_columns(engine) -> None:
    """
    Adds `description` column to service_catalog if missing.
    Safe to call; no-op if column already exists.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(service_catalog)").fetchall()]
        if "description" not in cols:
            conn.exec_driver_sql("ALTER TABLE service_catalog ADD COLUMN description TEXT DEFAULT ''")
            
# --- Right panel collapse/expand ---
def _toggle_right_panel(self):
    if self._right_collapsed:
        self._expand_right_panel()
    else:
        self._collapse_right_panel()

def _collapse_right_panel(self):
    try:
        self._saved_sizes = self.splitter.sizes()
    except Exception:
        self._saved_sizes = None
    self.right_panel.setVisible(False)
    self._right_collapsed = True
    self.btn_toggle_right.setText("Show Month")
    sizes = self.splitter.sizes()
    if len(sizes) == 3:
        self.splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])

def _expand_right_panel(self):
    self.right_panel.setVisible(True)
    self._right_collapsed = False
    self.btn_toggle_right.setText("Hide Month")
    if self._saved_sizes and len(self._saved_sizes) == 3 and self._saved_sizes[2] > 0:
        self.splitter.setSizes(self._saved_sizes)
    else:
        self.splitter.setSizes([320, 820, 500])

# coderabbit-review-marker
