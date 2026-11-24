# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Simulation: conservation, no negative balances, determinism, extreme parameters."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from market.config import Composition, ConfigError, SimConfig
from market.simulate import simulate

SMALL = dict(steps=3_000, burn_in=300, lookback=50, order_lifetime=200)


def _cfg(**kw):
    base = dict(SMALL)
    base.update(kw)
    return SimConfig(**base)


@pytest.mark.parametrize("comp", [Composition(), Composition(ZI=70, TF=30), Composition(ZI=70, MR=30),
                                  Composition(ZI=70, TF=15, MR=15), Composition(ZI=70, PA=30)])
def test_invariants_hold_every_step(comp):
    out = simulate(_cfg(composition=comp), seed=7, check_every=1)
    assert out.invariant_checks == SMALL["steps"] + 1
    assert sum(out.final_cash) == comp.total * 1_000_000
    assert sum(out.final_inventory) == comp.total * 1_000
    assert min(out.final_cash) >= 0 and min(out.final_inventory) >= 0


def test_same_seed_is_bit_identical():
    c = _cfg(composition=Composition(ZI=70, TF=15, MR=15))
    a, b = simulate(c, 3), simulate(c, 3)
    for k in ("best_bid", "best_ask", "mid", "depth_best", "volume"):
        assert np.array_equal(getattr(a, k), getattr(b, k))
    assert a.counts == b.counts and a.final_cash == b.final_cash


def test_different_seeds_differ():
    c = _cfg()
    assert not np.array_equal(simulate(c, 1).mid, simulate(c, 2).mid)


def test_common_random_numbers_share_activation_sequence():
    # same seed, different arms: the same agent ids are activated at every step
    a = simulate(_cfg(composition=Composition(ZI=100)), 5)
    b = simulate(_cfg(composition=Composition(ZI=70, TF=30)), 5)
    assert sum(a.counts["activations"].values()) == sum(b.counts["activations"].values())
    assert a.counts["activations"]["ZI"] == b.counts["activations"]["ZI"] + b.counts["activations"]["TF"]


def test_mid_is_carried_forward_and_positive():
    out = simulate(_cfg(composition=Composition(ZI=70, TF=30)), 11)
    assert np.all(out.mid > 0)
    both = (out.best_bid > 0) & (out.best_ask > 0)
    assert np.allclose(out.mid[both], (out.best_bid[both] + out.best_ask[both]) / 2)
    assert np.all(out.best_bid[both] < out.best_ask[both])


@pytest.mark.parametrize("kw", [
    dict(zi_market_prob=1.0),  # only market orders after seeding: book drains
    dict(zi_market_prob=0.0),  # only limit orders
    dict(initial_cash=0),  # nobody can buy
    dict(initial_inventory=0, initial_orders_per_side=0),  # nobody can sell
    dict(initial_cash=50, initial_inventory=1),  # very poor agents: many rejections
    dict(max_order_size=1, zi_limit_offset=0),
    dict(order_lifetime=1),
    dict(tick=5, initial_price=1000),
    dict(initial_price=1, tick=1),  # price floor
    dict(composition=Composition(ZI=1, TF=50)),
])
def test_extreme_parameters_keep_invariants(kw):
    out = simulate(_cfg(**kw), seed=2, check_every=1)
    assert min(out.final_cash) >= 0 and min(out.final_inventory) >= 0


def test_tick_grid_respected():
    out = simulate(_cfg(tick=2), seed=4)
    for arr in (out.best_bid, out.best_ask):
        assert np.all(arr % 2 == 0)


def test_shock_executes_and_is_conserved():
    c = _cfg(composition=Composition(ZI=70, TF=30), shock_step=1_500, shock_fraction=0.5, shock_inventory=10_000)
    out = simulate(c, 9, check_every=10)
    assert out.shock["step"] == 1_500 and out.shock["qty"] >= 1
    assert 0 < out.shock["filled"] <= out.shock["qty"]
    assert sum(out.final_inventory) == 100 * 1_000 + 10_000
    assert out.agent_types[-1] == "SHOCK"


@pytest.mark.parametrize("kw", [dict(steps=0), dict(burn_in=3_000), dict(zi_market_prob=1.5), dict(tick=0),
                                dict(initial_price=1001, tick=2), dict(composition=Composition(ZI=0, TF=0)),
                                dict(composition=Composition(ZI=0, TF=10)), dict(shock_step=0), dict(steps=10.0)])
def test_invalid_configs_raise(kw):
    with pytest.raises(ConfigError):
        _cfg(**kw).validate()


@settings(max_examples=25, deadline=None)
@given(
    zi=st.integers(1, 30), tf=st.integers(0, 15), mr=st.integers(0, 15), pa=st.integers(0, 15),
    p_mkt=st.floats(0, 1), size=st.integers(1, 20), offset=st.integers(0, 30), life=st.integers(1, 400),
    cash=st.integers(0, 50_000), inv=st.integers(0, 50), seed=st.integers(0, 999),
)
def test_property_conservation_random_configs(zi, tf, mr, pa, p_mkt, size, offset, life, cash, inv, seed):
    c = SimConfig(composition=Composition(ZI=zi, TF=tf, MR=mr, PA=pa), steps=400, burn_in=50, lookback=20,
                  zi_market_prob=p_mkt, max_order_size=size, zi_limit_offset=offset, order_lifetime=life,
                  initial_cash=cash, initial_inventory=inv, initial_price=100)
    out = simulate(c, seed, check_every=1)
    n = c.composition.total
    assert sum(out.final_cash) == n * cash and sum(out.final_inventory) == n * inv
