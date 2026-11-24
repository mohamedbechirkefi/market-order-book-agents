# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Tests of the frozen M3 analysis (D-013) on synthetic result documents (no simulation)."""

import numpy as np
import pytest

from market.analysis import bootstrap_mean_ci
from market.frozen_analysis import (analyse_exp001, analyse_exp002, analyse_exp003, analyse_exp004, boot_means, boot_p,
                                    contrast, flagged_seeds, holm_family, interval, kaplan_meier, verdict)


def doc(arm, seed, degenerate=False, status="ok", **metrics):
    return {"arm": arm, "seed": seed, "status": status, "metrics": metrics,
            "flags": {"degenerate": degenerate, "one_sided_over_5pct": degenerate, "fewer_than_50_nonzero_returns": False,
                      "vci_undefined": metrics.get("vci") is None}}


def test_boot_interval_equals_frozen_bootstrap():
    x = np.random.default_rng(1).normal(0.1, 1, 30)
    assert interval(boot_means(x), 0.95) == pytest.approx(bootstrap_mean_ci(x))


def test_verdict_rule():
    assert verdict(0.01, 0.2) == "supported"
    assert verdict(-0.2, -0.01) == "contradicted"
    assert verdict(-0.1, 0.1) == "inconclusive"
    assert verdict(None, None) == "undefined"


def test_boot_p_bounds():
    assert boot_p(np.array([1.0, 2.0, 3.0])) == 0.0
    assert boot_p(np.array([-1.0, 1.0])) == 1.0


def test_contrast_hand_example():
    r = contrast({1: 1.0, 2: 2.0, 3: 3.0}, {"treatment": "T", "control": "C", "metric": "m"})
    assert r["mean_diff"] == 2.0 and r["sd_diff"] == 1.0 and r["d_z"] == 2.0 and r["n_pairs"] == 3


def test_holm_family_levels():
    rows = [contrast({s: v for s, v in enumerate(np.random.default_rng(k).normal(mu, 1, 30))}, {"treatment": "T", "control": "C", "metric": str(k)})
            for k, mu in enumerate((2.0, 0.0, 0.5))]
    holm_family(rows)
    by_rank = sorted(rows, key=lambda r: r["holm_rank"])
    assert [r["holm_level"] for r in by_rank] == pytest.approx([1 - 0.05 / 3, 1 - 0.05 / 2, 0.95])
    for r in rows:  # Holm intervals are at least as wide as the 95% ones
        assert r["holm_ci_low"] <= r["ci95_low"] and r["holm_ci_high"] >= r["ci95_high"]


def test_exp001_pairs_and_exclusion():
    docs = []
    for s in range(1001, 1011):
        docs += [doc("A0", s, vci=0.0), doc("A1", s, vci=0.1 + 0.01 * s % 3, degenerate=(s == 1003)),
                 doc("A2", s, vci=0.0), doc("A3", s, vci=0.05)]
        for d in docs[-4:]:
            for m in ("realised_volatility", "excess_kurtosis", "return_acf1", "mean_spread", "mean_depth_at_best",
                      "volume_per_step", "max_drawdown", "one_sided_fraction", "rejected_fraction"):
                d["metrics"][m] = float(s % 4)
            d["metrics"]["tf_skip_fraction"] = 0.01 if d["arm"] == "A1" else None
    r = analyse_exp001(docs)
    assert r["primary"]["n_pairs"] == 10 and r["primary"]["verdict"] == "supported"
    assert r["flagged_seeds_A0_A1"] == [1003] and r["sensitivity_exclusion"]["n_pairs"] == 9
    assert len(r["secondary_holm"]) == 30
    assert r["a1_tf_skip_fraction"]["mean"] == pytest.approx(0.01)


def test_exp002_excludes_low_tf_and_interaction():
    docs = []
    for s in range(1, 9):
        for arm, spread, v in (("low-ZI", 3.0, 0.0), ("low-ZI+TF", 9.0, 9.0), ("med-ZI", 2.0, 0.0), ("med-ZI+TF", 2.0, 0.3),
                               ("high-ZI", 1.0, 0.0), ("high-ZI+TF", 1.0, 0.1)):
            docs.append(doc(arm, s, degenerate=arm == "low-ZI+TF", vci=v + 0.001 * s, mean_spread=spread + 0.01 * s,
                            mean_depth_at_best=1.0, volume_per_step=1.0, realised_volatility=1.0))
    r = analyse_exp002(docs)
    assert r["primary"]["mean_diff"] == pytest.approx(2.0) and r["primary"]["verdict"] == "supported"
    inter = [x for x in r["secondary_holm"] if x["metric"] == "vci (interaction)"][0]
    assert inter["mean_diff"] == pytest.approx(0.2)
    assert len(r["secondary_holm"]) == 16
    assert all("low-ZI+TF" not in (x["treatment"], x["control"]) for x in r["secondary_holm"])
    assert "low-ZI+TF" in r["arms_flag_rate_above_20pct (model failure for that arm)"]


def test_kaplan_meier_hand_example():
    km = kaplan_meier([2, 4, 4, 6], [False, False, True, False])
    # S(2) = 3/4, S(4) = 3/4 * 2/3 = 1/2 -> median 4; S(6) = 0
    assert km["curve"] == [[2, 0.75], [4, pytest.approx(0.5)], [6, 0.0]] and km["median_steps"] == 4 and km["censored"] == 1


def test_exp003_and_exp004_shapes():
    d3 = []
    for s in range(1, 6):
        for arm, dd in (("S-ZI", 0.01), ("S-ZI+TF", 0.03), ("S-ZI+MR", 0.0)):
            x = doc(arm, s, shock_drawdown=dd + 0.001 * s, shock_recovery_steps=100 * s, shock_recovery_censored=s == 5,
                    shock_window_truncated=False)
            x["shock"] = {"bid_depth": 50 + s}
            d3.append(x)
    r3 = analyse_exp003(d3)
    assert r3["primary"]["mean_diff"] == pytest.approx(0.02) and r3["recovery_kaplan_meier"]["S-ZI"]["censored"] == 1
    d1 = [doc(a, s, vci=v, vci_dt10=v, vci_dt200=v) for s in range(1, 9) for a, v in (("A0", 0.0 + 0.001 * s), ("A1", 0.1))]
    d4 = [doc(a, s, vci=v) for s in range(1, 9) for a, v in (("A4", 0.1 + 0.001 * (-1) ** s), ("A0-tick2", 0.0), ("A1-tick2", 0.05 + 0.001 * s))]
    prim = analyse_exp001_primary_stub(d1)
    r4 = analyse_exp004(d4, d1, prim)
    assert r4["robustness_rule"] == "robust"
    assert r4["placebo_rule"].startswith("EXP-001 effect not attributable")
    assert flagged_seeds(d1, ("A0", "A1")) == set()


def analyse_exp001_primary_stub(d1):
    from market.frozen_analysis import paired
    p = paired(d1, "A1", d1, "A0", "vci")
    p["verdict"] = verdict(p["ci95_low"], p["ci95_high"])
    return p
