from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    account: str
    symbol: str
    sec_type: str = "STK"
    currency: str = "USD"
    quantity: float = 0.0
    avg_cost: float = 0.0
    market_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class AccountSummary(BaseModel):
    account: str
    label: Optional[str] = None
    currency: str = "USD"
    net_liquidation: float = 0.0
    total_cash: float = 0.0
    gross_position_value: float = 0.0
    buying_power: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    positions: list[Position] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.label or self.account


class Snapshot(BaseModel):
    taken_at: datetime
    connected: bool = True
    error: Optional[str] = None
    accounts: list[AccountSummary] = Field(default_factory=list)

    def by_id(self, account: str) -> Optional[AccountSummary]:
        for a in self.accounts:
            if a.account == account:
                return a
        return None
