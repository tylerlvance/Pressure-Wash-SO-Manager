# Founders Pressure Wash SO Manager

Desktop app for managing service orders, customers, invoices, and staff.

## Features
- SO management with bulk actions
- Catalog Manager for line items and pricing
- Invoice generator with PDF export
- Staff manager and assignment dialog
- Preferences saved in `data/ui_prefs.json`

## Setup
```bash
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
py -3.11 main.py
