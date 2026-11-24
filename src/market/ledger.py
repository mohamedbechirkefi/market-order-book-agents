# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Cash and inventory accounting with reservations.

Every agent holds integer cash (price units) and inventory (units), both never negative
(no borrowing, no short selling). A resting buy limit reserves ``price * qty`` cash; a
resting sell limit reserves ``qty`` units. Trades move cash and units between two agents,
so the totals over all agents are conserved exactly.
"""

from __future__ import annotations

from .book import BUY, SELL, Fill, Order


class LedgerError(ValueError):
    """Raised when an operation would break an accounting constraint."""


class Ledger:
    def __init__(self, cash: list[int], inventory: list[int]):
        if len(cash) != len(inventory):
            raise LedgerError("cash and inventory must have the same length")
        for v in list(cash) + list(inventory):
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise LedgerError(f"endowments must be non-negative ints, got {v!r}")
        self.cash = list(cash)
        self.inv = list(inventory)
        self.rcash = [0] * len(cash)
        self.rinv = [0] * len(cash)
        self.total_cash = sum(cash)
        self.total_inv = sum(inventory)

    def __len__(self) -> int:
        return len(self.cash)

    def free_cash(self, a: int) -> int:
        return self.cash[a] - self.rcash[a]

    def free_inv(self, a: int) -> int:
        return self.inv[a] - self.rinv[a]

    def can_place_limit(self, a: int, side: int, price: int, qty: int) -> bool:
        if side == BUY:
            return self.free_cash(a) >= price * qty
        return self.free_inv(a) >= qty

    def reserve(self, order: Order) -> None:
        """Reserve resources for a resting order (after matching)."""
        a = order.owner
        if order.side == BUY:
            amt = order.price * order.qty
            if self.free_cash(a) < amt:
                raise LedgerError("insufficient free cash to reserve")
            self.rcash[a] += amt
        else:
            if self.free_inv(a) < order.qty:
                raise LedgerError("insufficient free inventory to reserve")
            self.rinv[a] += order.qty

    def release(self, owner: int, side: int, price: int, qty: int) -> None:
        """Release the reservation of ``qty`` units of a resting order (cancel or expiry)."""
        if side == BUY:
            self.rcash[owner] -= price * qty
        else:
            self.rinv[owner] -= qty
        if self.rcash[owner] < 0 or self.rinv[owner] < 0:
            raise LedgerError("reservation released below zero")

    def settle(self, fill: Fill) -> None:
        """Apply one fill. The maker's reservation is consumed; the taker pays from free funds."""
        q, p = fill.qty, fill.price
        amt = p * q
        maker, taker = fill.maker_owner, fill.taker_owner
        if fill.taker_side == BUY:
            # maker sold: consume its reserved units
            self.rinv[maker] -= q
            self.inv[maker] -= q
            self.cash[maker] += amt
            self.cash[taker] -= amt
            self.inv[taker] += q
        else:
            # maker bought: consume its reserved cash at its own (the trade) price
            self.rcash[maker] -= amt
            self.cash[maker] -= amt
            self.inv[maker] += q
            self.inv[taker] -= q
            self.cash[taker] += amt
        if self.cash[taker] < 0 or self.inv[taker] < 0 or self.cash[maker] < 0 or self.inv[maker] < 0:
            raise LedgerError("negative balance after settlement")

    def check_invariants(self, resting: list[Order] | None = None) -> None:
        """Raise AssertionError on any broken accounting invariant."""
        assert sum(self.cash) == self.total_cash, "cash not conserved"
        assert sum(self.inv) == self.total_inv, "inventory not conserved"
        for a in range(len(self.cash)):
            assert self.cash[a] >= 0, f"negative cash for agent {a}"
            assert self.inv[a] >= 0, f"negative inventory for agent {a}"
            assert 0 <= self.rcash[a] <= self.cash[a], f"bad cash reservation for agent {a}"
            assert 0 <= self.rinv[a] <= self.inv[a], f"bad inventory reservation for agent {a}"
        if resting is not None:
            rc = [0] * len(self.cash)
            ri = [0] * len(self.cash)
            for o in resting:
                if o.side == BUY:
                    rc[o.owner] += o.price * o.qty
                else:
                    ri[o.owner] += o.qty
            assert rc == self.rcash, "cash reservations do not match resting buys"
            assert ri == self.rinv, "inventory reservations do not match resting sells"


__all__ = ["Ledger", "LedgerError", "BUY", "SELL"]
