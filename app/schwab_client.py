from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import SCHWAB_TOKEN_FILE
from . import store


@dataclass
class Quote:
    symbol: str
    description: Optional[str] = None
    last: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    net_change: Optional[float] = None
    net_pct: Optional[float] = None
    quote_time: Optional[str] = None


def _client():
    settings = store.load()
    if not settings.schwab_api_key or not settings.schwab_app_secret:
        raise RuntimeError("Schwab credentials not configured. Open /quote and save them first.")
    try:
        from schwab.auth import client_from_token_file, easy_client  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "schwab-py not installed. Run: pip install 'paleoleon[schwab]'"
        ) from e
    if SCHWAB_TOKEN_FILE.exists():
        return client_from_token_file(
            token_path=str(SCHWAB_TOKEN_FILE),
            api_key=settings.schwab_api_key,
            app_secret=settings.schwab_app_secret,
        )
    return easy_client(
        api_key=settings.schwab_api_key,
        app_secret=settings.schwab_app_secret,
        callback_url=settings.schwab_callback_url,
        token_path=str(SCHWAB_TOKEN_FILE),
    )


def quote(symbol: str) -> Quote:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol required")
    c = _client()
    resp = c.get_quote(symbol)
    resp.raise_for_status()
    body = resp.json() or {}
    row = body.get(symbol) or next(iter(body.values()), {})
    qd = row.get("quote") or row
    ref = row.get("reference") or {}
    return Quote(
        symbol=symbol,
        description=ref.get("description"),
        last=qd.get("lastPrice") or qd.get("mark"),
        bid=qd.get("bidPrice"),
        ask=qd.get("askPrice"),
        volume=qd.get("totalVolume"),
        net_change=qd.get("netChange"),
        net_pct=qd.get("netPercentChange"),
        quote_time=str(qd.get("quoteTime") or ""),
    )
