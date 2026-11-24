# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Metric formulas: hand-computed golden values, undefined cases and invalid inputs."""

import math

import numpy as np
import pytest

from market.config import Composition, SimConfig
from market.metrics import MetricError, acf, compute_metrics, excess_kurtosis, max_drawdown, sampled_log_returns, vci
from market.simulate import simulate


def test_acf_hand_example():
    # x = 1,2,3,4: mean 2.5, d = -1.5,-0.5,0.5,1.5, sum d^2 = 5; lag 1: 0.75 - 0.25 + 0.75 = 1.25 -> 0.25
    assert acf(np.array([1.0, 2.0, 3.0, 4.0]), 1) == pytest.approx(0.25)
    # lag 2: d0 d2 + d1 d3 = -0.75 - 0.75 = -1.5 -> -0.3 (needs len >= lag + 2)
    assert acf(np.array([1.0, 2.0, 3.0, 4.0]), 2) == pytest.approx(-0.3)


def test_acf_alternating_series():
    x = np.array([1.0, -1.0] * 50)
    assert acf(x, 1) == pytest.approx(-0.99)


def test_acf_undefined_cases():
    assert acf(np.ones(20), 1) is None
    assert acf(np.array([1.0, 2.0]), 1) is None
    with pytest.raises(MetricError):
        acf(np.arange(10.0), 0)


def test_vci_matches_definition_and_constant_is_none():
    rng = np.random.default_rng(0)
    r = rng.normal(size=500)
    expected = sum(acf(np.abs(r), lag) for lag in range(1, 11)) / 10
    assert vci(r) == pytest.approx(expected)
    assert vci(np.zeros(100)) is None


def test_vci_detects_clustered_series():
    rng = np.random.default_rng(1)
    calm = rng.normal(scale=0.1, size=(20, 50))
    wild = rng.normal(scale=1.0, size=(20, 50))
    clustered = np.concatenate([np.concatenate([c, w]) for c, w in zip(calm, wild)])
    iid = rng.normal(size=clustered.size)
    assert vci(clustered) > 0.2 > abs(vci(iid))


def test_sampled_log_returns_hand_example():
    mid = np.array([100.0, 101, 102, 104, 103, 103])
    r = sampled_log_returns(mid, burn_in=1, dt=2)  # samples at 1, 3, 5: 101, 104, 103
    assert r == pytest.approx([math.log(104 / 101), math.log(103 / 104)])
    with pytest.raises(MetricError):
        sampled_log_returns(np.array([1.0, 0.0, 1.0]), 0, 1)
    with pytest.raises(MetricError):
        sampled_log_returns(mid, 0, 0)


def test_max_drawdown_hand_example():
    assert max_drawdown(np.array([100, 120, 90, 110, 60, 130.0])) == pytest.approx(0.5)
    assert max_drawdown(np.array([1, 2, 3.0])) == 0.0
    with pytest.raises(MetricError):
        max_drawdown(np.array([]))


def test_excess_kurtosis_examples():
    assert excess_kurtosis(np.array([1.0, -1.0] * 10)) == pytest.approx(-2.0)
    assert excess_kurtosis(np.ones(5)) is None
    big = np.random.default_rng(2).normal(size=200_000)
    assert abs(excess_kurtosis(big)) < 0.05


def test_compute_metrics_on_a_run():
    c = SimConfig(composition=Composition(ZI=70, TF=30), steps=5_000, burn_in=500, lookback=50, order_lifetime=300)
    m, flags = compute_metrics(simulate(c, 1))
    assert m["n_returns"] == (5_000 - 500) // 50
    assert 0.0 <= m["one_sided_fraction"] <= 1.0
    assert 0.0 <= m["max_drawdown"] < 1.0
    assert m["mean_spread"] is None or m["mean_spread"] > 0
    assert set(flags) == {"one_sided_over_5pct", "fewer_than_50_nonzero_returns", "vci_undefined", "degenerate"}
    assert "vci_dt10" in m and "vci_dt200" in m


def test_shock_metrics_present():
    c = SimConfig(steps=4_000, burn_in=500, lookback=50, order_lifetime=300, shock_step=2_000)
    m, _ = compute_metrics(simulate(c, 3))
    assert 0.0 <= m["shock_drawdown"] < 1.0
    assert isinstance(m["shock_recovery_censored"], bool)
