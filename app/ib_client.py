from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from .config import IB_CLIENT_ID, IB_HOST, IB_PORT
from .models import AccountSummary, Position, Snapshot

log = logging.getLogger(__name__)

try:
    from ib_async import IB, util  # type: ignore
except Exception:  # pragma: no cover - import-time only; offline dev fallback
    IB = None  # type: ignore
    util = None  # type: ignore


_SUMMARY_FIELDS = {
    "NetLiquidation": "net_liquidation",
    "TotalCashValue": "total_cash",
    "GrossPositionValue": "gross_position_value",
    "BuyingPower": "buying_power",
    "UnrealizedPnL": "unrealized_pnl",
    "RealizedPnL": "realized_pnl",
}


class IBClient:
    """Runs an ib_async IB instance on a dedicated background event loop.

    Route handlers call snapshot()/snapshot_account() synchronously; the work
    is dispatched to the IB loop with run_coroutine_threadsafe.
    """

    def __init__(self) -> None:
        self._ib: Optional["IB"] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._last_error: Optional[str] = None
        self._started = threading.Event()

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

    def _submit(self, coro):
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=15)

    async def _ensure_connected(self) -> bool:
        assert self._ib is not None
        if self._ib.isConnected():
            return True
        try:
            await self._ib.connectAsync(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=8)
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return False

    async def _managed_accounts(self) -> list[str]:
        assert self._ib is not None
        accts = list(self._ib.managedAccounts() or [])
        return [a for a in accts if a]

    async def _account_summary(self, account: str) -> AccountSummary:
        assert self._ib is not None
        rows = await self._ib.accountSummaryAsync(account)
        summary = AccountSummary(account=account)
        for row in rows:
            attr = _SUMMARY_FIELDS.get(row.tag)
            if attr is None:
                continue
            try:
                setattr(summary, attr, float(row.value))
            except (TypeError, ValueError):
                continue
            if row.currency:
                summary.currency = row.currency
        positions = []
        for item in self._ib.portfolio(account):
            contract = item.contract
            positions.append(
                Position(
                    account=account,
                    symbol=contract.localSymbol or contract.symbol,
                    sec_type=contract.secType or "STK",
                    currency=contract.currency or summary.currency,
                    quantity=float(item.position),
                    avg_cost=float(item.averageCost),
                    market_price=float(item.marketPrice),
                    market_value=float(item.marketValue),
                    unrealized_pnl=float(item.unrealizedPNL),
                    realized_pnl=float(item.realizedPNL),
                )
            )
        positions.sort(key=lambda p: abs(p.market_value), reverse=True)
        summary.positions = positions
        return summary

    async def _snapshot(self, only: Optional[list[str]] = None) -> Snapshot:
        ok = await self._ensure_connected()
        if not ok:
            return Snapshot(
                taken_at=datetime.now(timezone.utc),
                connected=False,
                error=self._last_error,
            )
        accounts = await self._managed_accounts()
        if only:
            accounts = [a for a in accounts if a in only]
        summaries: list[AccountSummary] = []
        for acct in accounts:
            try:
                summaries.append(await self._account_summary(acct))
            except Exception as e:
                log.warning("snapshot %s failed: %s", acct, e)
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
