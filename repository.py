# C:\Users\tyler\Desktop\FoundersSOManager\repository.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import date, timedelta
import calendar
from typing import Optional, Iterable, Tuple, List

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from models import (
    Customer, Site, ServiceOrder, Attachment,
    PaymentProfile, Employee, ServiceOrderAssignment as SOAssignment, Invoice,
    SiteService, SOService, ServiceCatalog,
)

# ---------- cadence helpers ----------
def _eom(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]

def _add_month_clamped(d: date) -> date:
    y, m = d.year, d.month
    if m == 12:
        y, m = y + 1, 1
    else:
        m += 1
    return date(y, m, min(d.day, _eom(y, m)))

def _nth_weekday_of_month(y: int, m: int, weekday_idx: int, n: int) -> date:
    first_weekday, dim = calendar.monthrange(y, m)
    offset = (weekday_idx - first_weekday) % 7
    day = 1 + offset + (n - 1) * 7
    if day > dim:
        day = dim
    return date(y, m, day)

def _title_from_cadence(code: str) -> str:
    if not code:
        return "Cleaning"
    if code == "weekly":
        return "Weekly Cleaning"
    if code == "biweekly":
        return "Biweekly Cleaning"
    if code == "monthly_same_day":
        return "Monthly Cleaning"
    if code.startswith("monthly_nth_wd:"):
        try:
            _, n, w = code.split(":")
            n = int(n); w = int(w)
            nth = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(n, f"{n}th")
            weekday = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][w]
            return f"Monthly {nth} {weekday} Cleaning"
        except Exception:
            return "Monthly Cleaning"
    return "Cleaning"

def _next_due_from_cadence(code: str, base: date) -> date:
    if not code:
        return base
    if code == "weekly":
        return base + timedelta(days=7)
    if code == "biweekly":
        return base + timedelta(days=14)
    if code == "monthly_same_day":
        return _add_month_clamped(base)
    if code.startswith("monthly_nth_wd:"):
        try:
            _, n, w = code.split(":")
            n = int(n); w = int(w)
            y, m = base.year, base.month
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1
            return _nth_weekday_of_month(y, m, w, n)
        except Exception:
            return _add_month_clamped(base)
    return base
# -------------------------------------


class Repo:
    def __init__(self, session: Session):
        self.s = session

    # ---------------- Catalog ----------------
    def list_catalog(self, active_only: bool = True) -> list[ServiceCatalog]:
        q = select(ServiceCatalog)
        if active_only:
            q = q.where(ServiceCatalog.active == True)
        return list(self.s.scalars(q.order_by(ServiceCatalog.name)))

    def create_catalog_service(self, name: str, default_price_cents: int = 0) -> ServiceCatalog:
        row = ServiceCatalog(name=name.strip(), default_price_cents=int(default_price_cents), active=True)
        self.s.add(row)
        self.s.commit()
        self.s.refresh(row)
        return row

    def update_catalog_service(self, svc_id: int, **fields) -> ServiceCatalog:
        row = self.s.get(ServiceCatalog, svc_id)
        if not row:
            raise ValueError("ServiceCatalog not found")
        for k, v in fields.items():
            setattr(row, k, v)
        self.s.commit()
        self.s.refresh(row)
        return row

    def deactivate_catalog_service(self, svc_id: int):
        row = self.s.get(ServiceCatalog, svc_id)
        if not row:
            return False
        row.active = False
        self.s.commit()
        return True

    # ---------------- Customers ----------------
    def list_customers(self) -> list[Customer]:
        return list(self.s.scalars(select(Customer).order_by(Customer.name)))

    def create_customer(self, **kwargs) -> Customer:
        c = Customer(**kwargs)
        self.s.add(c)
        self.s.commit()
        self.s.refresh(c)
        return c

    def update_customer(self, customer_id: int, **kwargs) -> Customer:
        c = self.s.get(Customer, customer_id)
        if not c:
            raise ValueError("Customer not found")
        for k, v in kwargs.items():
            setattr(c, k, v)
        self.s.commit()
        self.s.refresh(c)
        return c

    def delete_customer(self, customer_id: int):
        c = self.s.get(Customer, customer_id)
        if not c:
            return False
        self.s.delete(c)
        self.s.commit()
        return True

    # ---------------- Sites ----------------
    def list_sites_for_customer(self, customer_id: int) -> list[Site]:
        return list(self.s.scalars(
            select(Site).where(Site.customer_id == customer_id).order_by(Site.name)
        ))

    def list_services_for_site(self, site_id: int) -> list[SiteService]:
        return list(self.s.scalars(
            select(SiteService).where(SiteService.site_id == site_id).order_by(SiteService.name)
        ))

    def add_service_to_site(
        self,
        site_id: int,
        name: str | None = None,
        *,
        catalog_id: int | None = None,
        unit_price_cents: int | None = None,
    ) -> SiteService:
        """
        Backward compatible:
        - If catalog_id is provided, pull name and default price from the catalog unless overridden.
        - If only name is provided, create a free-text service with price 0 or provided unit_price_cents.
        """
        svc_name = (name or "").strip()
        price = int(unit_price_cents or 0)
        cat = None
        if catalog_id:
            cat = self.s.get(ServiceCatalog, int(catalog_id))
            if cat:
                if not svc_name:
                    svc_name = cat.name
                if unit_price_cents is None:
                    price = int(cat.default_price_cents or 0)
        srow = SiteService(site_id=site_id, name=svc_name or "Service", catalog_id=(cat.id if cat else None),
                           unit_price_cents=price, active=True)
        self.s.add(srow)
        self.s.commit()
        self.s.refresh(srow)
        return srow

    def update_site_service(self, service_id: int, **kwargs) -> SiteService:
        srow = self.s.get(SiteService, service_id)
        if not srow:
            raise ValueError("SiteService not found")
        for k, v in kwargs.items():
            setattr(srow, k, v)
        self.s.commit()
        self.s.refresh(srow)
        return srow

    def delete_site_service(self, service_id: int):
        srow = self.s.get(SiteService, service_id)
        if not srow:
            return False
        self.s.delete(srow)
        self.s.commit()
        return True

    def create_site(self, **kwargs) -> Site:
        # UI-only list of names from SiteDialog
        service_names = kwargs.pop("services_selected_names", None)
        site = Site(**kwargs)
        self.s.add(site)
        self.s.commit()
        self.s.refresh(site)

        # Create contracted services if provided (legacy free-text, price 0)
        if service_names:
            names = {n.strip() for n in service_names if (n or "").strip()}
            for nm in names:
                self.s.add(SiteService(site_id=site.id, name=nm, unit_price_cents=0, active=True))
            self.s.commit()
        return site

    def update_site(self, site_id: int, **kwargs) -> Site:
        service_names = kwargs.pop("services_selected_names", None)
        s = self.s.get(Site, site_id)
        if not s:
            raise ValueError("Site not found")
        for k, v in kwargs.items():
            setattr(s, k, v)
        self.s.commit()
        self.s.refresh(s)

        # Reconcile services if list was provided (legacy checklist, price stays as-is)
        if service_names is not None:
            want = {n.strip() for n in service_names if (n or "").strip()}
            existing = {row.name.strip(): row for row in self.list_services_for_site(site_id)}
            for nm in want:
                if nm in existing:
                    existing[nm].active = True
                else:
                    self.s.add(SiteService(site_id=site_id, name=nm, unit_price_cents=0, active=True))
            for nm, row in existing.items():
                if nm not in want:
                    row.active = False
            self.s.commit()
        return s

    def delete_site(self, site_id: int):
        s = self.s.get(Site, site_id)
        if not s:
            return False
        self.s.delete(s)
        self.s.commit()
        return True

    def get_site(self, site_id: int) -> Optional[Site]:
        return self.s.get(Site, site_id)

    # ---------------- Service Orders ----------------
    def list_sos_for_site(self, site_id: int) -> list[ServiceOrder]:
        return list(self.s.scalars(
            select(ServiceOrder).where(ServiceOrder.site_id == site_id).order_by(ServiceOrder.scheduled_date)
        ))

    def list_sos_due_in_month(self, year: int, month: int) -> list[ServiceOrder]:
        start = date(year, month, 1)
        end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        return list(self.s.scalars(
            select(ServiceOrder).where(
                ServiceOrder.scheduled_date >= start,
                ServiceOrder.scheduled_date < end
            ).order_by(ServiceOrder.scheduled_date)
        ))

    def list_services_for_so(self, so_id: int) -> list[SOService]:
        return list(self.s.scalars(
            select(SOService).where(SOService.service_order_id == so_id)
        ))

    def seed_services_for_so_from_site(self, so_id: int):
        """Copy all active SiteService rows to SOService with price snapshots."""
        so = self.s.get(ServiceOrder, so_id)
        if not so:
            raise ValueError("ServiceOrder not found")
        site_services = self.list_services_for_site(so.site_id)
        # clear existing links first
        self.s.query(SOService).filter(SOService.service_order_id == so_id).delete()
        for srow in site_services:
            if not srow.active:
                continue
            link = SOService(
                service_order_id=so_id,
                site_service_id=srow.id,
                unit_price_cents=int(srow.unit_price_cents or 0),
            )
            self.s.add(link)
        self.s.commit()

    def add_service_to_so(self, so_id: int, site_service_id: int) -> SOService:
        srow = self.s.get(SiteService, int(site_service_id))
        link = SOService(
            service_order_id=so_id,
            site_service_id=int(site_service_id),
            unit_price_cents=int(getattr(srow, "unit_price_cents", 0) or 0),
        )
        self.s.add(link)
        self.s.commit()
        self.s.refresh(link)
        return link

    def set_services_for_so(self, so_id: int, service_ids: list[int]):
        self.s.query(SOService).filter(SOService.service_order_id == so_id).delete()
        for sid in service_ids:
            self.add_service_to_so(so_id, int(sid))
        self.s.commit()

    def create_so(self, **kwargs) -> ServiceOrder:
        service_ids = kwargs.pop("services_selected_ids", None)
        so = ServiceOrder(**kwargs)
        self.s.add(so)
        self.s.commit()
        self.s.refresh(so)
        if service_ids:
            self.set_services_for_so(so.id, [int(x) for x in service_ids])
        else:
            # seed from site's contracted services
            self.seed_services_for_so_from_site(so.id)
        return so

    def update_so(self, so_id: int, **kwargs) -> ServiceOrder:
        service_ids = kwargs.pop("services_selected_ids", None)
        so = self.s.get(ServiceOrder, so_id)
        if not so:
            raise ValueError("ServiceOrder not found")
        for k, v in kwargs.items():
            setattr(so, k, v)
        self.s.commit()
        self.s.refresh(so)
        if service_ids is not None:
            self.set_services_for_so(so_id, [int(x) for x in service_ids])
        return so

    def delete_so(self, so_id: int):
        so = self.s.get(ServiceOrder, so_id)
        if not so:
            return False
        self.s.delete(so)
        self.s.commit()
        return True

    # ------------- cadence-aware helpers -------------
    def last_scheduled_for_site(self, site_id: int) -> Optional[date]:
        stmt = select(func.max(ServiceOrder.scheduled_date)).where(
            ServiceOrder.site_id == site_id,
            ServiceOrder.scheduled_date.is_not(None)
        )
        return self.s.execute(stmt).scalar_one_or_none()

    def next_due_for_site(self, site_id: int) -> Optional[date]:
        site = self.get_site(site_id)
        if not site:
            return None
        code = site.cadence_text or ""
        base = self.last_scheduled_for_site(site_id) or date.today()
        return _next_due_from_cadence(code, base)

    def create_next_so_for_site(self, site_id: int) -> ServiceOrder:
        site = self.get_site(site_id)
        if not site:
            raise ValueError("Site not found")
        code = site.cadence_text or ""
        title = _title_from_cadence(code)
        scheduled = self.next_due_for_site(site_id) or date.today()
        so = ServiceOrder(
            site_id=site_id,
            title=title,
            description="",
            scheduled_date=scheduled,
            completed=False,
            invoiced=False,
            notes=""
        )
        self.s.add(so)
        self.s.commit()
        self.s.refresh(so)
        # seed services + prices
        self.seed_services_for_so_from_site(so.id)
        return so

    # ---------------- Attachments ----------------
    def add_attachment(self, entity_type: str, entity_id: int, file_path: str, note: str = "") -> Attachment:
        a = Attachment(entity_type=entity_type, entity_id=entity_id, file_path=file_path, note=note)
        self.s.add(a)
        self.s.commit()
        self.s.refresh(a)
        return a

    # ---------------- Payment Profiles ----------------
    def list_payment_profiles(self, customer_id: int) -> list[PaymentProfile]:
        return list(self.s.scalars(
            select(PaymentProfile).where(PaymentProfile.customer_id == customer_id).order_by(PaymentProfile.id)
        ))

    def create_payment_profile(self, **kwargs) -> PaymentProfile:
        p = PaymentProfile(**kwargs)
        self.s.add(p)
        self.s.commit()
        self.s.refresh(p)
        return p

    def set_default_payment_profile(self, customer_id: int, profile_id: int):
        self.s.query(PaymentProfile).filter(PaymentProfile.customer_id == customer_id).update({"is_default": False})
        p = self.s.get(PaymentProfile, profile_id)
        if p:
            p.is_default = True
        self.s.commit()

    # ---------------- Employees ----------------
    def list_employees(self, active_only: bool = True) -> list[Employee]:
        q = select(Employee)
        if active_only:
            q = q.where(Employee.active == True)
        return list(self.s.scalars(q.order_by(Employee.name)))

    def create_employee(self, **kwargs) -> Employee:
        e = Employee(**kwargs)
        self.s.add(e)
        self.s.commit()
        self.s.refresh(e)
        return e

    def update_employee(self, emp_id: int, **kwargs) -> Employee:
        e = self.s.get(Employee, emp_id)
        if not e:
            raise ValueError("Employee not found")
        for k, v in kwargs.items():
            setattr(e, k, v)
        self.s.commit()
        self.s.refresh(e)
        return e

    def delete_employee(self, emp_id: int):
        e = self.s.get(Employee, emp_id)
        if not e:
            return False
        self.s.delete(e)
        self.s.commit()
        return True

    # ---------------- Staff Assignments ----------------
    def list_assignments_for_so(self, so_id: int) -> list[SOAssignment]:
        """Return all ServiceOrderAssignment rows for a given SO."""
        return list(self.s.scalars(
            select(SOAssignment).where(SOAssignment.service_order_id == int(so_id))
        ))

    def assign_employee(self, so_id: int, employee_id: int, **_) -> SOAssignment:
        """
        Idempotently assign an employee to an SO.
        Extra kwargs (like role=) are accepted and ignored for forward-compat.
        """
        existing = (
            self.s.query(SOAssignment)
            .filter_by(service_order_id=int(so_id), employee_id=int(employee_id))
            .first()
        )
        if existing:
            return existing
        obj = SOAssignment(service_order_id=int(so_id), employee_id=int(employee_id))
        self.s.add(obj)
        self.s.commit()
        self.s.refresh(obj)
        return obj

    def unassign_employee(self, so_id: int, employee_id: int) -> bool:
        """Remove a specific employee assignment from an SO if present."""
        obj = (
            self.s.query(SOAssignment)
            .filter_by(service_order_id=int(so_id), employee_id=int(employee_id))
            .first()
        )
        if not obj:
            return False
        self.s.delete(obj)
        self.s.commit()
        return True

    # ---------------- Invoice seeding ----------------
    def _seed_invoice_no(self, so_id: int, so_date: Optional[date]) -> str:
        d = (so_date or date.today()).strftime("%Y%m%d")
        return f"FPC-{d}-SO{so_id}"

    def invoice_seed_for_so(self, so_id: int, *, terms_days: int = 14) -> dict:
        so = self.s.get(ServiceOrder, so_id)
        if not so:
            raise ValueError("ServiceOrder not found")
        site = so.site
        cust = site.customer if site else None

        # bill to
        bill_name = (cust.name if cust else "") or ""
        bill_addr = (site.address or "") if site else ""
        bill_phone = (cust.phone or "")
        bill_email = (cust.email or "")
        if bill_email:
            bill_contact = f"{bill_phone}\n{bill_email}" if bill_phone else bill_email
        else:
            bill_contact = bill_phone

        # priced lines from SO snapshot
        links = self.list_services_for_so(so_id)
        line_items_cents: list[tuple[str, int]] = []
        for lk in links:
            nm = lk.site_service.name if lk.site_service else "Service"
            amt = int(getattr(lk, "unit_price_cents", 0) or 0)
            line_items_cents.append((nm, amt))

        subtotal_cents = sum(a for _, a in line_items_cents)

        return dict(
            invoice_no=self._seed_invoice_no(so.id, so.scheduled_date),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=int(terms_days)),
            notes=(so.notes or "").strip(),
            line_items_cents=line_items_cents,
            subtotal_cents=subtotal_cents,
            bill_to_name=bill_name,
            bill_to_addr=bill_addr,
            bill_to_contact=bill_contact,
            so_title=so.title or "",
            so_desc=so.description or "",
        )
