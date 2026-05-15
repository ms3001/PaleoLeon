from datetime import datetime, timezone

from app.models import AccountSummary, Position, Snapshot
from app.routes.watchlist import autocomplete, move, positions_in_scope, row_view


def _pos(account, symbol, qty, price, sec_type="STK", currency="USD"):
    return Position(
        account=account,
        symbol=symbol,
        sec_type=sec_type,
        currency=currency,
        quantity=qty,
        avg_cost=price,
        market_price=price,
        market_value=qty * price,
    )


def _snapshot():
    a = AccountSummary(
        account="U111",
        net_liquidation=100_000,
        positions=[
            _pos("U111", "AAPL", 100, 180.0),
            _pos("U111", "MSFT", 50, 400.0),
            _pos("U111", "BTC", 1, 60_000.0, sec_type="CRYPTO"),
        ],
    )
    b = AccountSummary(
        account="U222",
        net_liquidation=50_000,
        positions=[
            _pos("U222", "AAPL", 50, 180.0),
            _pos("U222", "TLT", 100, 90.0),
        ],
    )
    return Snapshot(taken_at=datetime.now(timezone.utc), accounts=[a, b])


def test_positions_in_scope_all_concatenates():
    snap = _snapshot()
    syms = [p.symbol for p in positions_in_scope(snap, "all")]
    assert syms == ["AAPL", "MSFT", "BTC", "AAPL", "TLT"]


def test_positions_in_scope_single_account():
    snap = _snapshot()
    syms = [p.symbol for p in positions_in_scope(snap, "U222")]
    assert syms == ["AAPL", "TLT"]


def test_positions_in_scope_unknown_account_returns_empty():
    assert positions_in_scope(_snapshot(), "UZZZ") == []


def test_autocomplete_dedupes_across_accounts():
    snap = _snapshot()
    matches = autocomplete(snap, "all", "AA")
    assert [m.symbol for m in matches] == ["AAPL"]


def test_autocomplete_filters_by_scope():
    snap = _snapshot()
    matches = autocomplete(snap, "U111", "")
    assert [m.symbol for m in matches] == ["AAPL", "MSFT", "BTC"]


def test_autocomplete_case_insensitive_substring():
    snap = _snapshot()
    matches = autocomplete(snap, "all", "ms")
    assert [m.symbol for m in matches] == ["MSFT"]


def test_row_view_sums_quantity_in_scope_all():
    snap = _snapshot()
    row = row_view(snap, "all", {"symbol": "AAPL", "sec_type": "STK", "currency": "USD"})
    assert row["qty"] == 150
    assert row["price"] == 180.0
    assert row["in_scope"] is True


def test_row_view_quantity_zero_when_not_in_scope_but_price_borrowed():
    snap = _snapshot()
    row = row_view(snap, "U222", {"symbol": "MSFT", "sec_type": "STK", "currency": "USD"})
    assert row["qty"] == 0
    assert row["price"] == 400.0
    assert row["in_scope"] is False


def test_row_view_unknown_symbol_returns_none_price():
    snap = _snapshot()
    row = row_view(snap, "all", {"symbol": "XXXX", "sec_type": "STK", "currency": "USD"})
    assert row["qty"] == 0
    assert row["price"] is None
    assert row["in_scope"] is False


def test_move_up_swaps():
    items = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
    assert [i["symbol"] for i in move(items, 2, "up")] == ["A", "C", "B"]


def test_move_down_swaps():
    items = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
    assert [i["symbol"] for i in move(items, 0, "down")] == ["B", "A", "C"]


def test_move_at_top_is_noop():
    items = [{"symbol": "A"}, {"symbol": "B"}]
    assert [i["symbol"] for i in move(items, 0, "up")] == ["A", "B"]


def test_move_at_bottom_is_noop():
    items = [{"symbol": "A"}, {"symbol": "B"}]
    assert [i["symbol"] for i in move(items, 1, "down")] == ["A", "B"]


def test_move_out_of_range_is_noop():
    items = [{"symbol": "A"}, {"symbol": "B"}]
    assert [i["symbol"] for i in move(items, 9, "up")] == ["A", "B"]
