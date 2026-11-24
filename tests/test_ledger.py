# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Cash and inventory accounting: hand-computed settlements, reservations, invalid inputs."""

import pytest

from market.book import BUY, SELL, Fill, OrderBook
from market.ledger import Ledger, LedgerError


def test_settle_taker_buy_hand_example():
    led = Ledger([1000, 1000], [10, 10])
    b = OrderBook()
    _, o = b.submit_limit(0, SELL, 100, 3)
    led.reserve(o)
    assert led.free_inv(0) == 7
    fills, _ = b.submit_market(1, BUY, 2)
    for f in fills:
        led.settle(f)
    assert led.cash == [1200, 800] and led.inv == [8, 12]
    assert led.rinv == [1, 0]
    led.check_invariants(b.resting_orders())


def test_settle_taker_sell_consumes_maker_cash_reservation():
    led = Ledger([1000, 0], [0, 5])
    b = OrderBook()
    _, o = b.submit_limit(0, BUY, 90, 4)
    led.reserve(o)
    assert led.rcash[0] == 360 and led.free_cash(0) == 640
    fills, _ = b.submit_limit(1, SELL, 80, 5)  # trades 4 @ 90, 1 rests at 80
    for f in fills:
        led.settle(f)
    assert led.cash == [640, 360] and led.inv == [4, 1]
    assert led.rcash == [0, 0]


def test_self_trade_is_neutral():
    led = Ledger([500], [5])
    b = OrderBook()
    _, o = b.submit_limit(0, SELL, 100, 2)
    led.reserve(o)
    fills, _ = b.submit_market(0, BUY, 2, cash_cap=led.free_cash(0))
    for f in fills:
        led.settle(f)
    assert led.cash == [500] and led.inv == [5] and led.rinv == [0]


def test_reserve_refuses_unfunded_orders():
    led = Ledger([99], [0])
    b = OrderBook()
    _, o = b.submit_limit(0, BUY, 100, 1)
    with pytest.raises(LedgerError):
        led.reserve(o)
    assert not led.can_place_limit(0, BUY, 100, 1)
    assert not led.can_place_limit(0, SELL, 100, 1)


def test_release_restores_free_funds():
    led = Ledger([1000], [10])
    b = OrderBook()
    _, o = b.submit_limit(0, BUY, 100, 3)
    led.reserve(o)
    led.release(0, BUY, 100, 3)
    assert led.free_cash(0) == 1000
    with pytest.raises(LedgerError):
        led.release(0, SELL, 100, 1)


def test_settle_rejects_negative_balance():
    led = Ledger([0, 0], [1, 0])
    with pytest.raises(LedgerError):
        led.settle(Fill(maker_oid=1, maker_owner=0, taker_owner=1, taker_side=BUY, price=10, qty=1))


@pytest.mark.parametrize("cash,inv", [([-1], [0]), ([0], [-1]), ([1.5], [0]), ([0, 0], [0])])
def test_invalid_endowments(cash, inv):
    with pytest.raises(LedgerError):
        Ledger(cash, inv)
