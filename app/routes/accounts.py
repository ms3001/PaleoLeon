from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import store
from ..config import IB_HOST, IB_PORT
from ..ib_client import client
from ..templating import templates

router = APIRouter()


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_page(request: Request, account_id: str):
    snap = client.snapshot(only=[account_id])
    account = snap.by_id(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    settings = store.load()
    account.label = settings.labels.get(account.account)
    return templates.TemplateResponse(
        request,
        "account.html",
        {
            "connected": snap.connected,
            "ib_error": snap.error,
            "ib_port": IB_PORT,
            "taken_at": snap.taken_at,
            "account": account,
        },
    )


@router.get("/settings/accounts", response_class=HTMLResponse)
def settings_page(request: Request, saved: bool = False):
    settings = store.load()
    managed = client.list_managed_accounts()
    return templates.TemplateResponse(
        request,
        "accounts_settings.html",
        {
            "connected": client.connected,
            "ib_error": client.last_error,
            "ib_host": IB_HOST,
            "ib_port": IB_PORT,
            "taken_at": None,
            "managed_accounts": managed,
            "settings": settings,
            "saved": saved,
        },
    )


@router.post("/settings/accounts")
async def save_settings(request: Request):
    form = await request.form()
    visible = form.getlist("visible")
    settings = store.load()
    settings.visible_accounts = list(visible)
    labels: dict[str, str] = {}
    for key, value in form.multi_items():
        if key.startswith("label_"):
            acct = key[len("label_"):]
            text = (value or "").strip()
            if text:
                labels[acct] = text
    settings.labels = labels
    store.save(settings)
    return RedirectResponse(url="/settings/accounts?saved=1", status_code=303)
