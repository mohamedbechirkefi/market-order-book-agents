# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Analysis helpers, seeded streams and agent rules."""

import numpy as np
import pytest

from market.agents import View, mr_rule, pa_rule, passive_price, snap, tf_rule, zi_rule
from market.analysis import AnalysisError, bootstrap_mean_ci, d_z, holm, paired_differences, seeds_needed
from market.book import BUY, SELL
from market.rng import Stream, make_streams


def test_paired_differences_drops_unpaired_and_undefined():
    assert paired_differences({1: 2.0, 2: None, 3: 5.0}, {1: 1.0, 2: 1.0, 4: 0.0}) == {1: 1.0}


def test_d_z_hand_example():
    assert d_z(np.array([1.0, 2.0, 3.0])) == pytest.approx(2.0)
    assert d_z(np.array([1.0, 1.0])) is None


def test_bootstrap_ci_deterministic_and_brackets_mean():
    x = np.random.default_rng(0).normal(1.0, 1.0, size=30)
    a = bootstrap_mean_ci(x, n_resamples=2_000)
    assert a == bootstrap_mean_ci(x, n_resamples=2_000)
    assert a[0] < x.mean() < a[1]
    with pytest.raises(AnalysisError):
        bootstrap_mean_ci(np.array([1.0]))


def test_holm_hand_example():
    # sorted 0.01, 0.02, 0.04 -> 0.03, 0.04, 0.04 (monotone)
    assert holm([0.04, 0.01, 0.02]) == pytest.approx([0.04, 0.03, 0.04])
    with pytest.raises(AnalysisError):
        holm([1.2])


def test_seeds_needed_matches_protocol_planning_value():
    assert seeds_needed(0.53) == pytest.approx(29.9, abs=0.1)


def test_stream_independent_of_block_size():
    import numpy as np
    s1 = Stream(np.random.SeedSequence(5), block=3)
    s2 = Stream(np.random.SeedSequence(5), block=1000)
    assert [s1.uniform() for _ in range(50)] == [s2.uniform() for _ in range(50)]


def test_named_streams_are_distinct_and_reproducible():
    a, b = make_streams(1), make_streams(1)
    assert a["zi"].uniform() == b["zi"].uniform()
    assert make_streams(1)["zi"].uniform() != make_streams(1)["activation"].uniform()
    with pytest.raises(ValueError):
        make_streams(-1)


class Fixed:
    """Stream stub returning given uniforms in order."""

    def __init__(self, vals):
        self.vals = list(vals)

    def uniform(self):
        return self.vals.pop(0)


V = View(best_bid=99, best_ask=101, mid=100.0, mid_lag=98.0, mid_ma=102.0, tick=1)


def test_snap_rounds_away_from_crossing():
    assert snap(100.5, 1, BUY) == 100 and snap(100.5, 1, SELL) == 101
    assert snap(101, 2, BUY) == 100 and snap(101, 2, SELL) == 102
    assert snap(-5, 1, BUY) == 1


def test_zi_rule_golden():
    # market? 0.1 < 0.2 -> market; side 0.7 -> SELL; size 0.0 -> 1
    assert zi_rule(V, Fixed([0.1, 0.7, 0.0, 0.0]), 0.2, 10, 5) == ("M", SELL, 1)
    # limit buy, size int(0.5*5)+1 = 3, offset int(0.35*11) = 3 behind best ask 101 -> 98
    assert zi_rule(V, Fixed([0.9, 0.2, 0.5, 0.35]), 0.2, 10, 5) == ("L", BUY, 98, 3)
    # limit sell at best bid + offset 10 (u -> 0.999)
    assert zi_rule(V, Fixed([0.9, 0.8, 0.999, 0.999]), 0.2, 10, 5) == ("L", SELL, 109, 5)


def test_trend_and_mean_reversion_directions():
    # mid 100 > lag 98: TF buys; mid 100 < MA 102: MR buys
    assert tf_rule(V, Fixed([0.9, 0.0]), 0.5, 5) == ("L", BUY, 99, 1)
    assert mr_rule(V, Fixed([0.1, 0.0]), 0.5, 5) == ("M", BUY, 1)
    flat = View(99, 101, 100.0, 100.0, 100.0, 1)
    assert tf_rule(flat, Fixed([0.1, 0.1]), 0.5, 5) is None
    assert mr_rule(flat, Fixed([0.1, 0.1]), 0.5, 5) is None


def test_placebo_rule_skip_and_coin():
    assert pa_rule(V, Fixed([0.05, 0.1, 0.9, 0.0]), 0.5, 5, skip_prob=0.1) is None
    assert pa_rule(V, Fixed([0.5, 0.9, 0.9, 0.0]), 0.5, 5, skip_prob=0.1) == ("L", SELL, 101, 1)


def test_passive_price_fallbacks():
    assert passive_price(View(None, 101, 100.0, 0, 0, 1), BUY) == 100
    assert passive_price(View(99, None, 100.0, 0, 0, 1), SELL) == 100
    assert passive_price(View(None, None, 100.5, 0, 0, 1), BUY) == 100
    assert passive_price(View(None, None, 100.5, 0, 0, 1), SELL) == 101
