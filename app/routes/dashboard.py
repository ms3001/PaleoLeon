from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import aggregations, store
from ..config import IB_PORT, REFRESH_SECONDS
from ..ib_client import client
from ..templating import templates

router = APIRouter()


def _context() -> dict:
    settings = store.load()
    snap = client.snapshot()
    accounts = aggregations.visible_accounts(snap, settings.visible_accounts, settings.labels)
    return {
        "connected": snap.connected,
        "ib_error": snap.error,
        "ib_port": IB_PORT,
        "taken_at": snap.taken_at,
        "refresh_seconds": REFRESH_SECONDS,
        "totals": aggregations.firm_totals(accounts),
        "accounts": accounts,
        "top": aggregations.top_positions(accounts, n=10),
        "exposures": aggregations.exposure_by_sec_type(accounts),
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", _context())


@router.get("/partials/dashboard", response_class=HTMLResponse)
def dashboard_partial(request: Request):
    return templates.TemplateResponse(request, "partials/dashboard_content.html", _context())
