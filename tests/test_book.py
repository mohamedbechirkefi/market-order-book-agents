# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Order matching, price-time priority, partial fills and invalid inputs (hand-computed)."""

import pytest

from market.book import BUY, SELL, BookError, OrderBook


def test_empty_book_has_no_quotes():
    b = OrderBook()
    assert b.best_bid() is None and b.best_ask() is None and len(b) == 0


def test_non_crossing_limits_rest():
    b = OrderBook()
    f1, o1 = b.submit_limit(1, BUY, 99, 5)
    f2, o2 = b.submit_limit(2, SELL, 101, 3)
    assert f1 == [] and f2 == []
    assert b.best_bid() == 99 and b.best_ask() == 101
    assert b.snapshot(BUY) == [(99, 5)] and b.snapshot(SELL) == [(101, 3)]
    b.check_invariants()


def test_price_priority_then_time_priority():
    # asks: 102 (a, t1), 101 (b, t2), 101 (c, t3). A market buy of 4 must take b, then c, then a.
    b = OrderBook()
    b.submit_limit(10, SELL, 102, 2)
    b.submit_limit(11, SELL, 101, 1)
    b.submit_limit(12, SELL, 101, 2)
    fills, left = b.submit_market(20, BUY, 4)
    assert [(f.maker_owner, f.price, f.qty) for f in fills] == [(11, 101, 1), (12, 101, 2), (10, 102, 1)]
    assert left == 0
    assert b.snapshot(SELL) == [(102, 1)]
    b.check_invariants()


def test_partial_fill_of_resting_order_keeps_its_priority():
    b = OrderBook()
    b.submit_limit(1, BUY, 100, 5)  # first in queue
    b.submit_limit(2, BUY, 100, 5)
    fills, _ = b.submit_market(9, SELL, 3)
    assert [(f.maker_owner, f.qty) for f in fills] == [(1, 3)]
    fills, _ = b.submit_market(9, SELL, 4)
    assert [(f.maker_owner, f.qty) for f in fills] == [(1, 2), (2, 2)]
    assert b.snapshot(BUY) == [(100, 3)]
    b.check_invariants()


def test_marketable_limit_executes_then_rests_remainder():
    b = OrderBook()
    b.submit_limit(1, SELL, 100, 2)
    b.submit_limit(1, SELL, 103, 2)
    fills, rested = b.submit_limit(2, BUY, 101, 5)
    assert [(f.price, f.qty) for f in fills] == [(100, 2)]  # 103 is beyond the limit
    assert rested is not None and rested.price == 101 and rested.qty == 3
    assert b.best_bid() == 101 and b.best_ask() == 103
    b.check_invariants()


def test_trade_price_is_the_resting_price():
    b = OrderBook()
    b.submit_limit(1, BUY, 100, 1)
    fills, _ = b.submit_limit(2, SELL, 90, 1)
    assert fills[0].price == 100


def test_market_order_remainder_is_cancelled_not_rested():
    b = OrderBook()
    b.submit_limit(1, SELL, 100, 2)
    fills, left = b.submit_market(2, BUY, 5)
    assert sum(f.qty for f in fills) == 2 and left == 3
    assert b.best_bid() is None and b.best_ask() is None


def test_market_buy_cash_cap_hand_example():
    # asks 100 x2, 105 x3; cap 310 buys 2 @ 100 (200) then 1 @ 105 (105) = 305, remaining 5 < 105.
    b = OrderBook()
    b.submit_limit(1, SELL, 100, 2)
    b.submit_limit(1, SELL, 105, 3)
    fills, left = b.submit_market(2, BUY, 10, cash_cap=310)
    assert [(f.price, f.qty) for f in fills] == [(100, 2), (105, 1)]
    assert left == 7
    assert b.snapshot(SELL) == [(105, 2)]
    b.check_invariants()


def test_market_buy_cash_cap_zero_fills_nothing():
    b = OrderBook()
    b.submit_limit(1, SELL, 100, 2)
    fills, left = b.submit_market(2, BUY, 1, cash_cap=99)
    assert fills == [] and left == 1 and b.snapshot(SELL) == [(100, 2)]


def test_cancel_removes_quantity_and_level():
    b = OrderBook()
    _, o = b.submit_limit(1, BUY, 100, 4)
    b.submit_limit(2, BUY, 99, 1)
    removed = b.cancel(o.oid)
    assert removed.qty == 4
    assert b.best_bid() == 99
    with pytest.raises(BookError):
        b.cancel(o.oid)
    b.check_invariants()


def test_cancelled_order_is_skipped_in_matching():
    b = OrderBook()
    _, o1 = b.submit_limit(1, SELL, 100, 1)
    b.submit_limit(2, SELL, 100, 1)
    b.cancel(o1.oid)
    fills, _ = b.submit_market(3, BUY, 1)
    assert fills[0].maker_owner == 2


def test_level_reused_after_emptying():
    b = OrderBook()
    b.submit_limit(1, SELL, 100, 1)
    b.submit_market(2, BUY, 1)
    b.submit_limit(3, SELL, 100, 2)
    assert b.best_ask() == 100 and b.qty_at(SELL, 100) == 2
    b.check_invariants()


@pytest.mark.parametrize("kwargs", [
    dict(owner=1, side=0, price=100, qty=1),
    dict(owner=1, side=BUY, price=0, qty=1),
    dict(owner=1, side=BUY, price=100, qty=0),
    dict(owner=1, side=BUY, price=100.5, qty=1),
    dict(owner=1, side=BUY, price=True, qty=1),
    dict(owner=1, side=BUY, price=100, qty=-3),
])
def test_invalid_limit_orders_raise(kwargs):
    with pytest.raises(BookError):
        OrderBook().submit_limit(**kwargs)


def test_invalid_market_orders_raise():
    b = OrderBook()
    with pytest.raises(BookError):
        b.submit_market(1, BUY, 0)
    with pytest.raises(BookError):
        b.submit_market(1, SELL, 1, cash_cap=10)
    with pytest.raises(BookError):
        b.submit_market(1, BUY, 1, cash_cap=-1)


def test_depth_and_snapshot_levels_limit():
    b = OrderBook()
    for p, q in ((99, 1), (98, 2), (97, 3)):
        b.submit_limit(1, BUY, p, q)
    assert b.depth(BUY) == 6
    assert b.snapshot(BUY, levels=2) == [(99, 1), (98, 2)]
