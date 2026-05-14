from datetime import datetime, timezone

from app.aggregations import (
    exposure_by_sec_type,
    firm_totals,
    top_positions,
    visible_accounts,
)
from app.models import AccountSummary, Position, Snapshot


def _pos(account: str, symbol: str, qty: float, mv: float, upnl: float, sec_type: str = "STK") -> Position:
    return Position(
        account=account,
        symbol=symbol,
        sec_type=sec_type,
        quantity=qty,
        avg_cost=mv / qty if qty else 0.0,
        market_price=mv / qty if qty else 0.0,
        market_value=mv,
        unrealized_pnl=upnl,
    )


def _acct(account: str, nav: float, cash: float, upnl: float, rpnl: float, positions: list[Position]) -> AccountSummary:
    return AccountSummary(
        account=account,
        net_liquidation=nav,
        total_cash=cash,
        gross_position_value=nav - cash,
        unrealized_pnl=upnl,
        realized_pnl=rpnl,
        positions=positions,
    )


def _snapshot() -> Snapshot:
    a = _acct(
        "U111",
        nav=100_000,
        cash=20_000,
        upnl=5_000,
        rpnl=1_000,
        positions=[
            _pos("U111", "AAPL", 100, 30_000, 2_000),
            _pos("U111", "MSFT", 50, 25_000, 3_000),
            _pos("U111", "ESZ5", 1, 37_000, 0, sec_type="FUT"),
        ],
    )
    b = _acct(
        "U222",
        nav=50_000,
        cash=5_000,
        upnl=-1_000,
        rpnl=500,
        positions=[
            _pos("U222", "AAPL", 50, 9_000, -500),
            _pos("U222", "TLT", 100, 36_000, -500),
        ],
    )
    c = _acct("U333", nav=10_000, cash=10_000, upnl=0, rpnl=0, positions=[])
    return Snapshot(taken_at=datetime.now(timezone.utc), accounts=[a, b, c])


def test_firm_totals_sums_every_account():
    t = firm_totals(_snapshot().accounts)
    assert t.account_count == 3
    assert t.net_liquidation == 160_000
    assert t.total_cash == 35_000
    assert t.unrealized_pnl == 4_000
    assert t.realized_pnl == 1_500


def test_top_positions_merges_by_symbol_and_sorts_by_abs_value():
    top = top_positions(_snapshot().accounts, n=3)
    assert top[0].symbol == "AAPL"
    assert top[0].market_value == 39_000
    assert top[0].unrealized_pnl == 1_500
    assert top[0].quantity == 150
    symbols = [p.symbol for p in top]
    assert "ESZ5" in symbols or "TLT" in symbols
    assert len(top) == 3


def test_exposure_by_sec_type_groups_correctly():
    rows = dict(exposure_by_sec_type(_snapshot().accounts))
    assert rows["STK"] == 30_000 + 25_000 + 9_000 + 36_000
    assert rows["FUT"] == 37_000


def test_visible_accounts_filters_and_labels():
    snap = _snapshot()
    accounts = visible_accounts(snap, ["U111", "U333"], {"U111": "Growth A"})
    ids = [a.account for a in accounts]
    assert ids == ["U111", "U333"]
    assert accounts[0].display_name == "Growth A"
    assert accounts[1].display_name == "U333"


def test_visible_accounts_empty_list_means_all():
    snap = _snapshot()
    accounts = visible_accounts(snap, [], {})
    assert [a.account for a in accounts] == ["U111", "U222", "U333"]
