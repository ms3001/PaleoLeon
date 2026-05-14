from __future__ import annotations

from fastapi import APIRouter, Form, Request  # noqa: F401
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import schwab_client, store
from ..config import IB_PORT
from ..ib_client import client
from ..templating import templates

router = APIRouter()


@router.get("/quote", response_class=HTMLResponse)
def quote_page(request: Request):
    settings = store.load()
    return templates.TemplateResponse(
        request,
        "quote.html",
        {
            "connected": client.connected,
            "ib_error": client.last_error,
            "ib_port": IB_PORT,
            "taken_at": None,
            "settings": settings,
        },
    )


@router.get("/quote/lookup", response_class=HTMLResponse)
def quote_lookup(request: Request, symbol: str = ""):
    if not symbol:
        return templates.TemplateResponse(
            request,
            "partials/quote_result.html",
            {"error": "Enter a symbol.", "quote": None},
        )
    try:
        q = schwab_client.quote(symbol)
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "partials/quote_result.html",
            {"error": f"{type(e).__name__}: {e}", "quote": None},
        )
    return templates.TemplateResponse(
        request,
        "partials/quote_result.html",
        {"quote": q, "error": None},
    )


@router.post("/quote/credentials")
def save_credentials(
    api_key: str = Form(""),
    app_secret: str = Form(""),
    callback_url: str = Form("https://127.0.0.1:8182"),
):
    settings = store.load()
    settings.schwab_api_key = api_key.strip() or None
    settings.schwab_app_secret = app_secret.strip() or None
    settings.schwab_callback_url = callback_url.strip() or "https://127.0.0.1:8182"
    store.save(settings)
    return RedirectResponse(url="/quote", status_code=303)
