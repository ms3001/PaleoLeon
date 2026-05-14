from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _money(value) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"


def _num(value) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def _fmt_dt(value) -> str:
    if isinstance(value, datetime):
        return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    return str(value) if value is not None else "—"


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["money"] = _money
templates.env.filters["num"] = _num
templates.env.filters["dt"] = _fmt_dt
