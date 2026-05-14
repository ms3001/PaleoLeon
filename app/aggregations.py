from __future__ import annotations

from dataclasses import dataclass

from .models import AccountSummary, Position, Snapshot


@dataclass
class FirmTotals:
    net_liquidation: float = 0.0
    total_cash: float = 0.0
    gross_position_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    account_count: int = 0


def firm_totals(accounts: list[AccountSummary]) -> FirmTotals:
    t = FirmTotals(account_count=len(accounts))
    for a in accounts:
        t.net_liquidation += a.net_liquidation
        t.total_cash += a.total_cash
        t.gross_position_value += a.gross_position_value
        t.unrealized_pnl += a.unrealized_pnl
        t.realized_pnl += a.realized_pnl
    return t


def top_positions(accounts: list[AccountSummary], n: int = 10) -> list[Position]:
    merged: dict[tuple[str, str], Position] = {}
    for a in accounts:
        for p in a.positions:
            key = (p.symbol, p.sec_type)
            existing = merged.get(key)
            if existing is None:
                merged[key] = Position(
                    account="*",
                    symbol=p.symbol,
                    sec_type=p.sec_type,
                    currency=p.currency,
                    quantity=p.quantity,
                    avg_cost=p.avg_cost,
                    market_price=p.market_price,
                    market_value=p.market_value,
                    unrealized_pnl=p.unrealized_pnl,
                    realized_pnl=p.realized_pnl,
                )
            else:
                existing.quantity += p.quantity
                existing.market_value += p.market_value
                existing.unrealized_pnl += p.unrealized_pnl
                existing.realized_pnl += p.realized_pnl
                existing.market_price = p.market_price
    positions = list(merged.values())
    positions.sort(key=lambda p: abs(p.market_value), reverse=True)
    return positions[:n]


def exposure_by_sec_type(accounts: list[AccountSummary]) -> list[tuple[str, float]]:
    totals: dict[str, float] = {}
    for a in accounts:
        for p in a.positions:
            totals[p.sec_type] = totals.get(p.sec_type, 0.0) + p.market_value
    rows = sorted(totals.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return rows


def visible_accounts(snapshot: Snapshot, visible: list[str], labels: dict[str, str]) -> list[AccountSummary]:
    if not visible:
        accounts = list(snapshot.accounts)
    else:
        wanted = set(visible)
        accounts = [a for a in snapshot.accounts if a.account in wanted]
    for a in accounts:
        a.label = labels.get(a.account)
    return accounts
