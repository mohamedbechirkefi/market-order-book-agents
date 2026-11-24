# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Deliberately naive reference matcher for differential testing of ``book.OrderBook``.

Keeps a flat list of resting orders and re-sorts it on every match. Slow, short and
obviously correct; it must produce exactly the same fills and resting book.
"""

from __future__ import annotations

from .book import BUY, SELL


class ReferenceBook:
    def __init__(self) -> None:
        self.orders: list[dict] = []  # live orders: oid, owner, side, price, qty, seq
        self.next_oid = 1
        self.next_seq = 1

    def _queue(self, side: int) -> list[dict]:
        if side == BUY:
            return sorted((o for o in self.orders if o["side"] == BUY), key=lambda o: (-o["price"], o["seq"]))
        return sorted((o for o in self.orders if o["side"] == SELL), key=lambda o: (o["price"], o["seq"]))

    def _match(self, owner, side, qty, limit, cash_cap):
        fills = []
        remaining = qty
        budget = cash_cap
        for o in self._queue(-side):
            if remaining == 0:
                break
            p = o["price"]
            if limit is not None and ((side == BUY and p > limit) or (side == SELL and p < limit)):
                break
            take = min(remaining, o["qty"])
            if budget is not None:
                take = min(take, budget // p)
                if take == 0:
                    break
                budget -= take * p
            o["qty"] -= take
            remaining -= take
            fills.append((o["oid"], o["owner"], owner, side, p, take))
        self.orders = [o for o in self.orders if o["qty"] > 0]
        return fills, remaining

    def submit_limit(self, owner, side, price, qty):
        fills, rem = self._match(owner, side, qty, price, None)
        oid = None
        if rem > 0:
            oid = self.next_oid
            self.next_oid += 1
            self.orders.append({"oid": oid, "owner": owner, "side": side, "price": price, "qty": rem, "seq": self.next_seq})
        self.next_seq += 1
        return fills, oid

    def submit_market(self, owner, side, qty, cash_cap=None):
        self.next_seq += 1
        return self._match(owner, side, qty, None, cash_cap)

    def cancel(self, oid):
        before = len(self.orders)
        self.orders = [o for o in self.orders if o["oid"] != oid]
        if len(self.orders) == before:
            raise KeyError(oid)

    def levels(self, side):
        agg: dict[int, int] = {}
        for o in self.orders:
            if o["side"] == side:
                agg[o["price"]] = agg.get(o["price"], 0) + o["qty"]
        return sorted(agg.items(), reverse=(side == BUY))

    def resting(self):
        return [(o["oid"], o["owner"], o["side"], o["price"], o["qty"]) for o in self._queue(BUY) + self._queue(SELL)]
