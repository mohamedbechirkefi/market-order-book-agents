# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Agent decision rules as pure functions.

Each rule maps a read-only market view and random draws to an order intent, or None
(no order). Every rule draws a fixed number of uniforms per activation, whatever it
decides, so streams stay aligned across arms (common random numbers).

Intents: ``("M", side, qty)`` for a market order, ``("L", side, price, qty)`` for a limit order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .book import BUY, SELL
from .rng import Stream

ZI_DRAWS = 4  # market?, side, size, offset
STRATEGIC_DRAWS = 2  # market?, size
PA_DRAWS = 4  # skip?, side, market?, size


@dataclass(frozen=True)
class View:
    """What an agent sees when it acts. Prices in price units; mids may be half-integers."""

    best_bid: int | None
    best_ask: int | None
    mid: float  # current mid, or last defined mid if a side is empty
    mid_lag: float  # mid L steps ago (initial price before that)
    mid_ma: float  # mean of the last L mids (fewer at the start)
    tick: int


def snap(price: float, tick: int, side: int) -> int:
    """Snap a price to the grid without crossing further: buys round down, sells round up.

    The result is at least one tick (prices are positive).
    """
    if side == BUY:
        p = math.floor(price / tick) * tick
    else:
        p = math.ceil(price / tick) * tick
    return max(tick, int(p))


def _draw_size(u: float, max_size: int) -> int:
    k = int(u * max_size)
    return (k if k < max_size else max_size - 1) + 1


def zi_rule(view: View, s: Stream, market_prob: float, max_offset: int, max_size: int):
    """Random-order (zero-intelligence) agent.

    With probability ``market_prob`` a market order on a fair-coin side; otherwise a limit
    order on a fair-coin side at an offset uniform on 0..max_offset price units behind the
    best opposite quote (the last mid if that side is empty), snapped to the grid.
    """
    u_mkt, u_side, u_size, u_off = s.uniform(), s.uniform(), s.uniform(), s.uniform()
    side = BUY if u_side < 0.5 else SELL
    qty = _draw_size(u_size, max_size)
    if u_mkt < market_prob:
        return ("M", side, qty)
    off = int(u_off * (max_offset + 1))
    off = off if off <= max_offset else max_offset
    if side == BUY:
        ref = view.best_ask if view.best_ask is not None else view.mid
        price = snap(ref - off, view.tick, BUY)
    else:
        ref = view.best_bid if view.best_bid is not None else view.mid
        price = snap(ref + off, view.tick, SELL)
    return ("L", side, price, qty)


def passive_price(view: View, side: int) -> int:
    """Limit price at the best quote on the agent's own side.

    If that side is empty: one tick inside the opposite best; if both are empty: the mid,
    snapped away from crossing.
    """
    t = view.tick
    if side == BUY:
        if view.best_bid is not None:
            return view.best_bid
        if view.best_ask is not None:
            return max(t, view.best_ask - t)
        return snap(view.mid, t, BUY)
    if view.best_ask is not None:
        return view.best_ask
    if view.best_bid is not None:
        return view.best_bid + t
    return snap(view.mid, t, SELL)


def _directional_order(side: int, view: View, u_mkt: float, u_size: float, market_prob: float, max_size: int):
    qty = _draw_size(u_size, max_size)
    if u_mkt < market_prob:
        return ("M", side, qty)
    return ("L", side, passive_price(view, side), qty)


def sign(x: float) -> int:
    return (x > 0) - (x < 0)


def tf_rule(view: View, s: Stream, market_prob: float, max_size: int):
    """Trend follower: direction sign(mid - mid_lag); no order when the signal is 0."""
    u_mkt, u_size = s.uniform(), s.uniform()
    d = sign(view.mid - view.mid_lag)
    if d == 0:
        return None
    return _directional_order(BUY if d > 0 else SELL, view, u_mkt, u_size, market_prob, max_size)


def mr_rule(view: View, s: Stream, market_prob: float, max_size: int):
    """Mean reverter: direction -sign(mid - moving average); no order when the signal is 0."""
    u_mkt, u_size = s.uniform(), s.uniform()
    d = -sign(view.mid - view.mid_ma)
    if d == 0:
        return None
    return _directional_order(BUY if d > 0 else SELL, view, u_mkt, u_size, market_prob, max_size)


def pa_rule(view: View, s: Stream, market_prob: float, max_size: int, skip_prob: float):
    """Placebo aggressive: TF order rule with a fair-coin, price-independent direction."""
    u_skip, u_side, u_mkt, u_size = s.uniform(), s.uniform(), s.uniform(), s.uniform()
    if u_skip < skip_prob:
        return None
    side = BUY if u_side < 0.5 else SELL
    return _directional_order(side, view, u_mkt, u_size, market_prob, max_size)
