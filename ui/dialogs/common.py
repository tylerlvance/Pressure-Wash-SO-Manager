# C:\Users\tyler\Desktop\FoundersSOManager\ui\dialogs\common.py
# -*- coding: utf-8 -*-
from __future__ import annotations

def _get_repo(parent, fallback=None):
    if fallback is not None:
        return fallback
    return getattr(parent, "repo", None)

def _to_cents(dollars: float) -> int:
    return int(round(float(dollars or 0.0) * 100))

def _to_dollars(cents: int) -> float:
    return float(cents or 0) / 100.0
# coderabbit-review-marker
