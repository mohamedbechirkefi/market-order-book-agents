# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Limit-order book with price-time priority.

The book only matches orders; it knows nothing about cash or inventory (see ``ledger``).
Prices and quantities are positive integers. Priority: better price first, then lower
sequence number (earlier arrival). Trades execute at the resting (maker) order's price.
Market orders walk the book; their unfilled remainder is cancelled, never rested.
A marketable limit order executes up to its limit and its remainder rests.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass

BUY = 1
SELL = -1


class BookError(ValueError):
    """Raised on an invalid order (non-positive price or size, bad side, unknown id)."""


class Order:
    __slots__ = ("oid", "owner", "side", "price", "qty", "seq", "expiry")

    def __init__(self, oid: int, owner: int, side: int, price: int, qty: int, seq: int, expiry: int | None):
        self.oid = oid
        self.owner = owner
        self.side = side
        self.price = price
        self.qty = qty
        self.seq = seq
        self.expiry = expiry

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Order(oid={self.oid}, owner={self.owner}, side={self.side}, price={self.price}, qty={self.qty})"


@dataclass(frozen=True)
class Fill:
    """One execution. ``taker_side`` is BUY or SELL; price is the maker's price."""

    maker_oid: int
    maker_owner: int
    taker_owner: int
    taker_side: int
    price: int
    qty: int


def _check_side(side: int) -> None:
    if side not in (BUY, SELL):
        raise BookError(f"side must be BUY (1) or SELL (-1), got {side!r}")


def _check_pos_int(name: str, v: object) -> None:
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise BookError(f"{name} must be a positive int, got {v!r}")


class OrderBook:
    def __init__(self) -> None:
        self._levels: dict[int, dict[int, deque[Order]]] = {BUY: {}, SELL: {}}
        self._level_qty: dict[int, dict[int, int]] = {BUY: {}, SELL: {}}
        # Heaps of prices with lazy deletion. Bids stored negated so heap[0] is the best.
        self._heaps: dict[int, list[int]] = {BUY: [], SELL: []}
        self._orders: dict[int, Order] = {}
        self._next_oid = 1
        self._next_seq = 1

    # ----- queries -----
    def best(self, side: int) -> int | None:
        heap = self._heaps[side]
        lq = self._level_qty[side]
        while heap:
            p = -heap[0] if side == BUY else heap[0]
            if lq.get(p, 0) > 0:
                return p
            heapq.heappop(heap)
            lq.pop(p, None)
            self._levels[side].pop(p, None)
        return None

    def best_bid(self) -> int | None:
        return self.best(BUY)

    def best_ask(self) -> int | None:
        return self.best(SELL)

    def qty_at(self, side: int, price: int) -> int:
        return self._level_qty[side].get(price, 0)

    def depth(self, side: int) -> int:
        """Total resting quantity on one side."""
        return sum(self._level_qty[side].values())

    def get(self, oid: int) -> Order | None:
        return self._orders.get(oid)

    def __len__(self) -> int:
        return len(self._orders)

    def resting_orders(self) -> list[Order]:
        """All live orders sorted by priority within each side (bids then asks)."""
        out: list[Order] = []
        for side in (BUY, SELL):
            prices = sorted(self._levels[side], reverse=(side == BUY))
            for p in prices:
                out.extend(o for o in self._levels[side][p] if o.qty > 0)
        return out

    def snapshot(self, side: int, levels: int | None = None) -> list[tuple[int, int]]:
        """Aggregated (price, quantity) levels, best first."""
        lq = self._level_qty[side]
        prices = sorted((p for p, q in lq.items() if q > 0), reverse=(side == BUY))
        if levels is not None:
            prices = prices[:levels]
        return [(p, lq[p]) for p in prices]

    # ----- mutations -----
    def _rest(self, owner: int, side: int, price: int, qty: int, expiry: int | None) -> Order:
        o = Order(self._next_oid, owner, side, price, qty, self._next_seq, expiry)
        self._next_oid += 1
        self._next_seq += 1
        lv = self._levels[side]
        if price not in lv:
            lv[price] = deque()
        lv[price].append(o)
        lq = self._level_qty[side]
        if lq.get(price, 0) == 0:
            heapq.heappush(self._heaps[side], -price if side == BUY else price)
        lq[price] = lq.get(price, 0) + qty
        self._orders[o.oid] = o
        return o

    def _match(self, taker_owner: int, side: int, qty: int, limit: int | None, cash_cap: int | None) -> tuple[list[Fill], int]:
        """Match an incoming order. Returns fills and the unfilled quantity.

        ``limit`` None means market order. ``cash_cap`` (buys only) bounds total spend.
        """
        opp = -side
        fills: list[Fill] = []
        remaining = qty
        budget = cash_cap
        lv = self._levels[opp]
        lq = self._level_qty[opp]
        while remaining > 0:
            p = self.best(opp)
            if p is None:
                break
            if limit is not None and ((side == BUY and p > limit) or (side == SELL and p < limit)):
                break
            if budget is not None:
                affordable = budget // p
                if affordable <= 0:
                    break
            queue = lv[p]
            while remaining > 0 and queue:
                o = queue[0]
                if o.qty == 0:  # cancelled lazily
                    queue.popleft()
                    continue
                take = min(remaining, o.qty)
                if budget is not None:
                    take = min(take, budget // p)
                    if take <= 0:
                        break
                    budget -= take * p
                o.qty -= take
                lq[p] -= take
                remaining -= take
                fills.append(Fill(o.oid, o.owner, taker_owner, side, p, take))
                if o.qty == 0:
                    queue.popleft()
                    del self._orders[o.oid]
            if budget is not None and budget // p <= 0 and remaining > 0 and lq.get(p, 0) > 0:
                break
        return fills, remaining

    def submit_limit(self, owner: int, side: int, price: int, qty: int, expiry: int | None = None) -> tuple[list[Fill], Order | None]:
        """Submit a limit order. Returns the fills and the resting remainder (or None)."""
        _check_side(side)
        _check_pos_int("price", price)
        _check_pos_int("qty", qty)
        fills, remaining = self._match(owner, side, qty, price, None)
        rested = self._rest(owner, side, price, remaining, expiry) if remaining > 0 else None
        if rested is None:
            # still consume a sequence number so ordering is a pure function of submissions
            self._next_seq += 1
        return fills, rested

    def submit_market(self, owner: int, side: int, qty: int, cash_cap: int | None = None) -> tuple[list[Fill], int]:
        """Submit a market order. Returns the fills and the cancelled (unfilled) quantity."""
        _check_side(side)
        _check_pos_int("qty", qty)
        if cash_cap is not None:
            if side != BUY:
                raise BookError("cash_cap applies to market buys only")
            if isinstance(cash_cap, bool) or not isinstance(cash_cap, int) or cash_cap < 0:
                raise BookError(f"cash_cap must be a non-negative int, got {cash_cap!r}")
        self._next_seq += 1
        return self._match(owner, side, qty, None, cash_cap)

    def cancel(self, oid: int) -> Order:
        """Cancel a live order. Returns the order with its remaining quantity before cancel."""
        o = self._orders.pop(oid, None)
        if o is None:
            raise BookError(f"unknown or inactive order id {oid}")
        removed = Order(o.oid, o.owner, o.side, o.price, o.qty, o.seq, o.expiry)
        self._level_qty[o.side][o.price] -= o.qty
        o.qty = 0  # lazily dropped from its queue
        return removed

    # ----- verification -----
    def check_invariants(self) -> None:
        """Raise AssertionError if the internal structure is inconsistent."""
        live = 0
        for side in (BUY, SELL):
            for p, queue in self._levels[side].items():
                q = [o for o in queue if o.qty > 0]
                assert sum(o.qty for o in q) == self._level_qty[side].get(p, 0), "level quantity mismatch"
                seqs = [o.seq for o in q]
                assert seqs == sorted(seqs), "time priority broken within a level"
                for o in q:
                    assert o.price == p and o.side == side, "order filed at wrong level"
                    assert self._orders.get(o.oid) is o, "order index mismatch"
                live += len(q)
            for p, qty in self._level_qty[side].items():
                assert qty >= 0, "negative level quantity"
        assert live == len(self._orders), "orphan orders in index"
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            assert bb < ba, "crossed book"
