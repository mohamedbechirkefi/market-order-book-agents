# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Event-time simulation of one market run (one configuration, one seed).

Step order at each t = 1..T: (1) expire resting orders whose expiry is <= t;
(2) at the shock step, the shock agent sends its market sell; (3) one agent drawn
uniformly at random acts once; (4) the step's state is recorded.
The run is a deterministic function of (config, seed).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np

from .agents import View, mr_rule, pa_rule, snap, tf_rule, zi_rule
from .book import BUY, SELL, OrderBook
from .config import SimConfig
from .ledger import Ledger
from .rng import make_streams


class InvariantViolation(AssertionError):
    """An accounting or order-book invariant failed during a run."""


@dataclass
class SimOutput:
    config: SimConfig
    seed: int
    best_bid: np.ndarray  # int64, 0 when the side is empty; index t = 0..T (0 = after seeding)
    best_ask: np.ndarray  # int64, 0 when the side is empty
    mid: np.ndarray  # float64, carried forward when a side is empty
    depth_best: np.ndarray  # int64, size at best bid + size at best ask
    volume: np.ndarray  # int64, units traded during step t
    agent_types: list[str]
    counts: dict = field(default_factory=dict)
    final_cash: list[int] = field(default_factory=list)
    final_inventory: list[int] = field(default_factory=list)
    shock: dict | None = None
    invariant_checks: int = 0


def _mid(bb: int | None, ba: int | None, last: float) -> float:
    if bb is not None and ba is not None:
        return (bb + ba) / 2.0
    return last


def simulate(cfg: SimConfig, seed: int, check_every: int = 0) -> SimOutput:
    """Run one simulation. ``check_every`` > 0 checks all invariants every that many steps.

    Invariants are always checked once at the end. A violation raises InvariantViolation.
    """
    cfg.validate()
    streams = make_streams(seed)
    s_act, s_zi, s_str, s_pa, s_shock, s_init = (streams[k] for k in ("activation", "zi", "strategic", "pa", "shock", "init"))
    types = cfg.composition.types()
    n = len(types)
    has_shock = cfg.shock_step is not None
    cash = [cfg.initial_cash] * n + ([0] if has_shock else [])
    inv = [cfg.initial_inventory] * n + ([cfg.shock_inventory] if has_shock else [])
    ledger = Ledger(cash, inv)
    book = OrderBook()
    expiries: list[tuple[int, int]] = []
    tick = cfg.tick
    T = cfg.steps
    L = cfg.lookback

    counts = {
        "activations": {k: 0 for k in ("ZI", "TF", "MR", "PA")},
        "no_order": {k: 0 for k in ("ZI", "TF", "MR", "PA")},
        "submitted": 0,
        "submitted_post_burn_in": 0,
        "rejected": 0,
        "rejected_post_burn_in": 0,
        "market_orders": 0,
        "limit_orders": 0,
        "fills": 0,
        "self_fills": 0,
        "expired": 0,
        "market_unfilled_units": 0,
        "seed_orders_placed": 0,
        "seed_orders_rejected": 0,
    }

    def place(owner: int, intent, t: int) -> int:
        """Submit an intent with accounting. Returns traded units; counts rejections."""
        post = t > cfg.burn_in
        counts["submitted"] += 1
        if post:
            counts["submitted_post_burn_in"] += 1
        if intent[0] == "M":
            _, side, qty = intent
            counts["market_orders"] += 1
            if side == BUY:
                cap = ledger.free_cash(owner)
                ba = book.best_ask()
                if ba is not None and cap < ba:
                    counts["rejected"] += 1
                    counts["rejected_post_burn_in"] += post
                    return 0
                fills, left = book.submit_market(owner, BUY, qty, cash_cap=cap)
            else:
                if ledger.free_inv(owner) < qty:
                    counts["rejected"] += 1
                    counts["rejected_post_burn_in"] += post
                    return 0
                fills, left = book.submit_market(owner, SELL, qty)
            counts["market_unfilled_units"] += left
        else:
            _, side, price, qty = intent
            counts["limit_orders"] += 1
            if not ledger.can_place_limit(owner, side, price, qty):
                counts["rejected"] += 1
                counts["rejected_post_burn_in"] += post
                return 0
            fills, rested = book.submit_limit(owner, side, price, qty, expiry=t + cfg.order_lifetime)
            if rested is not None:
                ledger.reserve(rested)
                heapq.heappush(expiries, (rested.expiry, rested.oid))
        traded = 0
        for f in fills:
            ledger.settle(f)
            traded += f.qty
            if f.maker_owner == f.taker_owner:
                counts["self_fills"] += 1
        counts["fills"] += len(fills)
        return traded

    # ----- initial book (t = 0), drawn from the init stream -----
    zi_ids = [i for i, ty in enumerate(types) if ty == "ZI"]
    p0 = cfg.initial_price
    for side in (BUY, SELL):
        for _ in range(cfg.initial_orders_per_side):
            owner = zi_ids[s_init.integer(len(zi_ids))]
            k = 1 + s_init.integer(max(1, cfg.zi_limit_offset))
            qty = 1 + s_init.integer(cfg.max_order_size)
            price = snap(p0 - k, tick, BUY) if side == BUY else snap(p0 + k, tick, SELL)
            if side == BUY and price >= p0:
                price = max(tick, p0 - tick)
            if not ledger.can_place_limit(owner, side, price, qty):
                counts["seed_orders_rejected"] += 1
                continue
            fills, rested = book.submit_limit(owner, side, price, qty, expiry=cfg.order_lifetime)
            for f in fills:  # cannot happen with bids below p0 and asks above, kept for safety
                ledger.settle(f)
            if rested is not None:
                ledger.reserve(rested)
                heapq.heappush(expiries, (rested.expiry, rested.oid))
            counts["seed_orders_placed"] += 1

    best_bid = np.zeros(T + 1, dtype=np.int64)
    best_ask = np.zeros(T + 1, dtype=np.int64)
    mid = np.zeros(T + 1, dtype=np.float64)
    depth_best = np.zeros(T + 1, dtype=np.int64)
    volume = np.zeros(T + 1, dtype=np.int64)

    bb, ba = book.best_bid(), book.best_ask()
    last_mid = _mid(bb, ba, float(p0))
    best_bid[0] = bb or 0
    best_ask[0] = ba or 0
    mid[0] = last_mid
    depth_best[0] = (book.qty_at(BUY, bb) if bb else 0) + (book.qty_at(SELL, ba) if ba else 0)
    mids: list[float] = [last_mid]
    prefix: list[float] = [0.0, last_mid]  # prefix[k] = sum of mids[0..k-1]
    shock_info = None
    checks = 0

    for t in range(1, T + 1):
        # (1) expiry
        while expiries and expiries[0][0] <= t:
            _, oid = heapq.heappop(expiries)
            o = book.get(oid)
            if o is not None:
                removed = book.cancel(oid)
                ledger.release(removed.owner, removed.side, removed.price, removed.qty)
                counts["expired"] += 1
        traded = 0
        # (2) shock
        if has_shock and t == cfg.shock_step:
            bid_depth = book.depth(BUY)
            qty = max(1, int(math.floor(cfg.shock_fraction * bid_depth)))
            _ = s_shock.uniform()  # reserved draw, keeps the stream defined for future variants
            pre_mid = mids[-1]
            shock_info = {"step": t, "bid_depth": bid_depth, "qty": qty, "pre_shock_mid": pre_mid}
            traded += place(n, ("M", SELL, qty), t)
            shock_info["filled"] = traded
        # (3) one agent acts
        a = s_act.integer(n)
        ty = types[a]
        counts["activations"][ty] += 1
        bb, ba = book.best_bid(), book.best_ask()
        cur_mid = _mid(bb, ba, last_mid)
        lag_idx = t - L if t - L > 0 else 0
        lo = t - L if t - L > 0 else 0
        ma = (prefix[t] - prefix[lo]) / (t - lo)
        view = View(bb, ba, cur_mid, mids[lag_idx], ma, tick)
        if ty == "ZI":
            intent = zi_rule(view, s_zi, cfg.zi_market_prob, cfg.zi_limit_offset, cfg.max_order_size)
        elif ty == "TF":
            intent = tf_rule(view, s_str, cfg.strategic_market_prob, cfg.max_order_size)
        elif ty == "MR":
            intent = mr_rule(view, s_str, cfg.strategic_market_prob, cfg.max_order_size)
        else:
            intent = pa_rule(view, s_pa, cfg.strategic_market_prob, cfg.max_order_size, cfg.pa_skip_prob)
        if intent is None:
            counts["no_order"][ty] += 1
        else:
            traded += place(a, intent, t)
        # (4) record
        bb, ba = book.best_bid(), book.best_ask()
        last_mid = _mid(bb, ba, last_mid)
        best_bid[t] = bb or 0
        best_ask[t] = ba or 0
        mid[t] = last_mid
        depth_best[t] = (book.qty_at(BUY, bb) if bb else 0) + (book.qty_at(SELL, ba) if ba else 0)
        volume[t] = traded
        mids.append(last_mid)
        prefix.append(prefix[-1] + last_mid)
        if check_every and t % check_every == 0:
            _check(book, ledger)
            checks += 1

    _check(book, ledger)
    checks += 1
    return SimOutput(
        config=cfg,
        seed=seed,
        best_bid=best_bid,
        best_ask=best_ask,
        mid=mid,
        depth_best=depth_best,
        volume=volume,
        agent_types=types + (["SHOCK"] if has_shock else []),
        counts=counts,
        final_cash=list(ledger.cash),
        final_inventory=list(ledger.inv),
        shock=shock_info,
        invariant_checks=checks,
    )


def _check(book: OrderBook, ledger: Ledger) -> None:
    try:
        book.check_invariants()
        ledger.check_invariants(book.resting_orders())
    except AssertionError as e:
        raise InvariantViolation(str(e)) from e
