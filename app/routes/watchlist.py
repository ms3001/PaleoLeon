from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .. import store
from ..config import IB_PORT, REFRESH_SECONDS
from ..ib_client import client
from ..models import Position, Snapshot
from ..templating import templates

router = APIRouter()


def positions_in_scope(snapshot: Snapshot, scope: str) -> list[Position]:
    if scope == "all":
        return [p for a in snapshot.accounts for p in a.positions]
    a = snapshot.by_id(scope)
    return list(a.positions) if a else []


def autocomplete(snapshot: Snapshot, scope: str, q: str, limit: int = 10) -> list[Position]:
    q = q.strip().upper()
    seen: dict[tuple[str, str, str], Position] = {}
    for p in positions_in_scope(snapshot, scope):
        if q and q not in p.symbol.upper():
            continue
        seen.setdefault((p.symbol, p.sec_type, p.currency), p)
    return list(seen.values())[:limit]


def row_view(snapshot: Snapshot, scope: str, item: dict) -> dict:
    key = (item["symbol"], item["sec_type"], item["currency"])
    qty = 0.0
    price: float | None = None
    in_scope = False
    for p in positions_in_scope(snapshot, scope):
        if (p.symbol, p.sec_type, p.currency) == key:
            qty += p.quantity
            price = p.market_price
            in_scope = True
    if price is None:
        for a in snapshot.accounts:
            for p in a.positions:
                if (p.symbol, p.sec_type, p.currency) == key:
                    price = p.market_price
                    break
            if price is not None:
                break
    return {**item, "price": price, "qty": qty, "in_scope": in_scope}


def move(items: list[dict], index: int, direction: str) -> list[dict]:
    if not 0 <= index < len(items):
        return items
    new_index = index - 1 if direction == "up" else index + 1
    if not 0 <= new_index < len(items):
        return items
    items[index], items[new_index] = items[new_index], items[index]
    return items


def _context() -> dict:
    settings = store.load()
    snap = client.snapshot()
    accounts = list(snap.accounts)
    accounts.sort(key=lambda a: a.account)
    rows = [row_view(snap, settings.scope, item) for item in settings.watchlist]
    return {
        "connected": snap.connected,
        "ib_error": snap.error,
        "ib_port": IB_PORT,
        "taken_at": snap.taken_at,
        "refresh_seconds": REFRESH_SECONDS,
        "scope": settings.scope,
        "accounts": accounts,
        "rows": rows,
    }


def _render_table(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "partials/watchlist_table.html", _context())


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "watchlist.html", _context())


@router.get("/partials/watchlist", response_class=HTMLResponse)
def watchlist_partial(request: Request):
    return _render_table(request)


@router.get("/watchlist/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    settings = store.load()
    snap = client.snapshot()
    matches = autocomplete(snap, settings.scope, q)
    already = {(i["symbol"], i["sec_type"], i["currency"]) for i in settings.watchlist}
    matches = [m for m in matches if (m.symbol, m.sec_type, m.currency) not in already]
    return templates.TemplateResponse(
        request,
        "partials/search_results.html",
        {"matches": matches, "query": q},
    )


@router.post("/watchlist/add", response_class=HTMLResponse)
def add(
    request: Request,
    symbol: str = Form(...),
    sec_type: str = Form("STK"),
    currency: str = Form("USD"),
):
    symbol = symbol.strip().upper()
    sec_type = sec_type.strip().upper() or "STK"
    currency = currency.strip().upper() or "USD"
    if symbol:
        settings = store.load()
        key = (symbol, sec_type, currency)
        if not any((i["symbol"], i["sec_type"], i["currency"]) == key for i in settings.watchlist):
            settings.watchlist.append(
                {"symbol": symbol, "sec_type": sec_type, "currency": currency}
            )
            store.save(settings)
    return _render_table(request)


@router.post("/watchlist/delete", response_class=HTMLResponse)
def delete(request: Request, index: int = Form(...)):
    settings = store.load()
    if 0 <= index < len(settings.watchlist):
        settings.watchlist.pop(index)
        store.save(settings)
    return _render_table(request)


@router.post("/watchlist/move", response_class=HTMLResponse)
def move_row(request: Request, index: int = Form(...), dir: str = Form(...)):
    settings = store.load()
    settings.watchlist = move(settings.watchlist, index, dir)
    store.save(settings)
    return _render_table(request)


@router.post("/watchlist/scope", response_class=HTMLResponse)
def set_scope(request: Request, scope: str = Form(...)):
    settings = store.load()
    settings.scope = (scope or "all").strip() or "all"
    store.save(settings)
    return _render_table(request)
