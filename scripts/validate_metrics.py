# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M3 metric validation on known cases (exploratory, protocol section 5).

Builds hand-made SimOutput series whose metric values can be computed by hand and checks
``market.metrics.compute_metrics`` against them. Uses no simulation and no seed.

    .venv/bin/python scripts/validate_metrics.py   -> prints one line per check, exit 0 if all pass
"""

from __future__ import annotations

import math
import sys

import numpy as np

from market.config import Composition, SimConfig
from market.metrics import compute_metrics, shock_metrics
from market.simulate import SimOutput


def case() -> tuple[SimOutput, dict]:
    # T = 12, B = 2, dt = 2: post burn-in steps t = 3..12 (10 steps)
    cfg = SimConfig(composition=Composition(ZI=2), steps=12, burn_in=2, sample_interval=2, lookback=2, order_lifetime=5)
    bid = np.array([99, 99, 99, 99, 100, 98, 0, 99, 99, 101, 100, 99, 99])
    ask = np.array([101, 101, 101, 103, 102, 100, 102, 101, 103, 103, 102, 101, 101])
    two = (bid > 0) & (ask > 0)
    mid = np.empty(13)
    last = 100.0
    for t in range(13):
        if two[t]:
            last = (bid[t] + ask[t]) / 2.0
        mid[t] = last
    depth = np.array([5, 5, 5, 6, 7, 3, 4, 8, 2, 6, 5, 4, 4])
    vol = np.array([0, 0, 3, 1, 0, 2, 5, 0, 1, 0, 4, 0, 2])
    counts = {"submitted_post_burn_in": 8, "rejected_post_burn_in": 2, "activations": {"ZI": 12, "TF": 0, "MR": 0, "PA": 0},
              "no_order": {"ZI": 0, "TF": 0, "MR": 0, "PA": 0}}
    out = SimOutput(cfg, 0, bid, ask, mid, depth, vol, ["ZI", "ZI"], counts, [1_000_000, 1_000_000], [1_000, 1_000])
    post = slice(3, None)
    tb, ta, tw = bid[post], ask[post], two[post]
    spreads = (ta - tb)[tw]
    rel = spreads / ((ta + tb)[tw] / 2.0)
    m = mid[2::2]
    r = np.diff(np.log(m))
    mm = mid[2:]
    peak = np.maximum.accumulate(mm)
    expected = {
        "mean_spread": float(spreads.mean()),
        "mean_relative_spread": float(rel.mean()),
        "mean_depth_at_best": float(depth[post][tw].mean()),
        "volume_per_step": float(vol[post].sum() / 10),
        "one_sided_fraction": 1 / 10,
        "rejected_fraction": 2 / 8,
        "n_returns": 5,
        "realised_volatility": float(np.std(r, ddof=1)),
        "max_drawdown": float(np.max(1 - mm / peak)),
    }
    return out, expected


def main() -> int:
    out, exp = case()
    m, flags = compute_metrics(out)
    ok = True
    for k, v in exp.items():
        good = m[k] is not None and math.isclose(m[k], v, rel_tol=1e-12, abs_tol=1e-15)
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {k}: computed {m[k]!r}, by hand {v!r}")
    good = flags["one_sided_over_5pct"] is True and flags["fewer_than_50_nonzero_returns"] is True and flags["degenerate"] is True
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} flags: {flags}")
    # VCI on a known clustered series: |r| alternates in blocks, so acf(|r|, 1) is positive and VCI equals its definition
    from market.metrics import acf, vci
    x = np.array([0.01, 0.01, 0.01, 0.0, 0.0, 0.0] * 20)
    by_hand = sum(acf(np.abs(x), lag) for lag in range(1, 11)) / 10
    d = np.abs(x) - np.abs(x).mean()
    acf1_hand = float(np.dot(d[:-1], d[1:]) / np.dot(d, d))
    good = math.isclose(vci(x), by_hand) and math.isclose(acf(np.abs(x), 1), acf1_hand) and acf1_hand > 0
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} vci: {vci(x)!r} = mean of acf lags 1..10; acf1 by hand {acf1_hand!r}")
    good = vci(np.full(50, 0.01)) is None
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} vci undefined on constant |r| -> None")
    # Shock metrics: pre-shock mid 100, falls to 90, back inside 1% at 4 steps after the shock
    out.shock = {"step": 1, "bid_depth": 10, "qty": 5, "pre_shock_mid": 100.0}
    out.mid = np.array([100.0, 100.0, 95.0, 90.0, 92.0, 99.5, 100.0])
    s = shock_metrics(out, window=5, recovery_cap=5)
    good = math.isclose(s["shock_drawdown"], 0.10) and s["shock_recovery_steps"] == 4 and s["shock_recovery_censored"] is False
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} shock: {s} (by hand: drawdown 0.10, recovery 4 steps, not censored)")
    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
