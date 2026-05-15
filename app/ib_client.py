from __future__ import annotations

import asyncio
import logging
import math
import threading
from datetime import datetime, timezone
from typing import Optional

from .config import IB_CLIENT_ID, IB_HOST, IB_PORT
from .models import AccountSummary, Position, Snapshot

log = logging.getLogger(__name__)

try:
    from ib_async import IB  # type: ignore
except Exception:  # pragma: no cover - import-time only; offline dev fallback
    IB = None  # type: ignore


_SUMMARY_FIELDS = {
    "NetLiquidation": "net_liquidation",
    "TotalCashValue": "total_cash",
    "GrossPositionValue": "gross_position_value",
    "BuyingPower": "buying_power",
    "UnrealizedPnL": "unrealized_pnl",
    "RealizedPnL": "realized_pnl",
}


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return f


class IBClient:
    """Runs an ib_async IB instance on a dedicated background event loop.

    Route handlers call snapshot() synchronously; the work is dispatched to
    the IB loop with run_coroutine_threadsafe.
    """

    def __init__(self) -> None:
        self._ib: Optional["IB"] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._last_error: Optional[str] = None
        self._started = threading.Event()
        self._positions_subscribed: bool = False
        self._mkt_data_subscribed: set[int] = set()

    def start(self) -> None:
        if IB is None:
            self._last_error = "ib_async not installed"
            return
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ib-loop", daemon=True)
        self._thread.start()
        self._started.wait(timeout=2)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ib = IB()
        self._started.set()
        try:
            self._loop.run_forever()
        finally:
            try:
                if self._ib and self._ib.isConnected():
                    self._loop.run_until_complete(self._ib.disconnectAsync())
            except Exception:
                pass
            self._loop.close()

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def connected(self) -> bool:
        return bool(self._ib and self._ib.isConnected())

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def _submit(self, coro, timeout: float = 60.0):
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    async def _ensure_connected(self) -> bool:
        assert self._ib is not None
        if self._ib.isConnected():
            return True
        try:
            await self._ib.connectAsync(
                IB_HOST,
                IB_PORT,
                clientId=IB_CLIENT_ID,
                timeout=8,
                readonly=True,
            )
            self._last_error = None
            self._positions_subscribed = False
            self._mkt_data_subscribed.clear()
            # Ask IB for delayed-frozen data so contracts without a live
            # market-data subscription still return a price (15-20 min lag).
            try:
                self._ib.reqMarketDataType(4)
            except Exception as e:
                log.warning("reqMarketDataType(4) failed: %s", e)
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return False

    async def _managed_accounts(self) -> list[str]:
        assert self._ib is not None
        accts = list(self._ib.managedAccounts() or [])
        return [a for a in accts if a]

    async def _ensure_positions_subscribed(self) -> None:
        """`ib.positions()` reads from a cache populated by reqPositions.
        One subscription covers every FA sub-account, so we only need to
        do this once per connection."""
        assert self._ib is not None
        if self._positions_subscribed:
            return
        try:
            await asyncio.wait_for(self._ib.reqPositionsAsync(), timeout=8.0)
            self._positions_subscribed = True
        except Exception as e:
            log.warning("reqPositionsAsync failed: %s", e)

    def _ensure_mkt_data_subscribed(self, contract) -> None:
        """Streaming market data per unique contract.  Idempotent — IB only
        delivers one stream per (clientId, contract)."""
        assert self._ib is not None
        cid = getattr(contract, "conId", 0)
        if not cid or cid in self._mkt_data_subscribed:
            return
        try:
            self._ib.reqMktData(contract, "", False, False)
            self._mkt_data_subscribed.add(cid)
        except Exception as e:
            log.warning("reqMktData(conId=%s) failed: %s", cid, e)

    def _price_for(self, contract) -> Optional[float]:
        assert self._ib is not None
        try:
            ticker = self._ib.ticker(contract)
        except Exception:
            return None
        if ticker is None:
            return None
        for candidate in (
            ticker.marketPrice() if hasattr(ticker, "marketPrice") else None,
            getattr(ticker, "last", None),
            getattr(ticker, "close", None),
        ):
            value = _safe_float(candidate)
            if value is not None:
                return value
        return None

    async def _account_values(self, account: str) -> dict[str, float]:
        assert self._ib is not None
        rows = await self._ib.accountSummaryAsync(account)
        out: dict[str, float] = {}
        for row in rows:
            attr = _SUMMARY_FIELDS.get(row.tag)
            if attr is None:
                continue
            try:
                out[attr] = float(row.value)
            except (TypeError, ValueError):
                continue
        return out

    async def _snapshot(self, only: Optional[list[str]] = None) -> Snapshot:
        ok = await self._ensure_connected()
        if not ok:
            return Snapshot(
                taken_at=datetime.now(timezone.utc),
                connected=False,
                error=self._last_error,
            )
        assert self._ib is not None
        accounts = await self._managed_accounts()
        if only:
            accounts = [a for a in accounts if a in only]

        await self._ensure_positions_subscribed()

        positions_by_account: dict[str, list] = {a: [] for a in accounts}
        for ibpos in self._ib.positions():
            if ibpos.account in positions_by_account:
                positions_by_account[ibpos.account].append(ibpos)
                self._ensure_mkt_data_subscribed(ibpos.contract)

        summaries: list[AccountSummary] = []
        for acct in accounts:
            try:
                values = await self._account_values(acct)
            except Exception as e:
                log.warning("accountSummary(%s) failed: %s", acct, e)
                values = {}
            summary = AccountSummary(account=acct)
            for attr, value in values.items():
                setattr(summary, attr, value)
            positions: list[Position] = []
            for ibpos in positions_by_account.get(acct, []):
                contract = ibpos.contract
                qty = float(ibpos.position)
                avg_cost = float(ibpos.avgCost or 0.0)
                price = self._price_for(contract) or 0.0
                market_value = price * qty
                positions.append(
                    Position(
                        account=acct,
                        symbol=contract.localSymbol or contract.symbol,
                        sec_type=contract.secType or "STK",
                        currency=contract.currency or summary.currency,
                        quantity=qty,
                        avg_cost=avg_cost,
                        market_price=price,
                        market_value=market_value,
                        unrealized_pnl=(price - avg_cost) * qty if price else 0.0,
                        realized_pnl=0.0,
                    )
                )
            positions.sort(key=lambda p: abs(p.market_value), reverse=True)
            summary.positions = positions
            summaries.append(summary)
        return Snapshot(
            taken_at=datetime.now(timezone.utc),
            connected=True,
            accounts=summaries,
        )

    def snapshot(self, only: Optional[list[str]] = None) -> Snapshot:
        if self._loop is None:
            return Snapshot(
                taken_at=datetime.now(timezone.utc),
                connected=False,
                error=self._last_error or "IB client not started",
            )
        try:
            return self._submit(self._snapshot(only))
        except Exception as e:
            return Snapshot(
                taken_at=datetime.now(timezone.utc),
                connected=False,
                error=f"{type(e).__name__}: {e}",
            )

    def list_managed_accounts(self) -> list[str]:
        if self._loop is None:
            return []
        try:
            async def _go():
                if not await self._ensure_connected():
                    return []
                return await self._managed_accounts()

            return self._submit(_go())
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return []


client = IBClient()
