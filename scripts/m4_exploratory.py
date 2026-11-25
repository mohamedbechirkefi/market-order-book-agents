# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M4 exploratory confounder and sensitivity checks (EXPLORATORY, never confirmatory).

Nothing here changes or replaces a frozen verdict. Outputs go to results/exploratory/M4-SENS/.
Journal entry J-0011; decision D-016.

Part 1 (new simulations, development seeds 101..130 only, never the confirmatory seeds 1001..1030):
  arms A0 (100 ZI), A1 (70 ZI + 30 TF), A2 (70 ZI + 30 MR), A4 (70 ZI + 30 PA), and the
  EXP-003 shock arms S-ZI and S-ZI+TF (shock at step 50,000), all other parameters at the frozen
  EXP-001 / EXP-003 values.
  E1. VCI over a grid of sampling intervals dt in {5, 10, 20, 50, 100, 200, 500}: is the TF effect
      on clustering horizon-dependent, and does the placebo (A4) track it? The lag-1 autocorrelation
      of signed returns is recorded at each dt (bid-ask bounce if negative, trend runs if positive),
      added after the second review pass to test a competing reading of VCI.
  E2. Unshocked control window for EXP-003: the post-shock drawdown formula applied at step 50,000
      in unshocked runs on the same seeds, and the paired difference-in-differences
      [DD(S-ZI+TF) - DD(A1)] - [DD(S-ZI) - DD(A0)].
Part 2 (committed confirmatory outputs only, no simulation):
  E3. Holm intervals with ties at p = 0 given the most conservative level (D-014 alternative).
  E4. EXP-004 robustness rule read with the sign of H1 (positive) as the reference instead of the
      sign of the EXP-001 point estimate (D-013 item 6 alternative).
  E5. Seed-level association between A1 VCI and A1 trend excursions (max drawdown, realised
      volatility) in the committed EXP-001 runs.
  E6. EXP-003 competing explanations named in its protocol: did the shock consume the bid side
      completely (filled versus ordered quantity, one-sided flags), and how does the post-shock
      drawdown vary with bid depth at the shock within each arm (committed EXP-003 runs).

    .venv/bin/python scripts/m4_exploratory.py --workers 2
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market.config import Composition, SimConfig  # noqa: E402
from market.frozen_analysis import ALPHA, boot_means, boot_p, interval  # noqa: E402
from market.metrics import acf, sampled_log_returns, vci  # noqa: E402
from market.runner import load_results  # noqa: E402
from market.simulate import simulate  # noqa: E402

SEEDS = tuple(range(101, 131))
DT_GRID = (5, 10, 20, 50, 100, 200, 500)
SHOCK_STEP = 50_000
WINDOW = 5_000
ARMS = {
    "A0": dict(composition=Composition(ZI=100)),
    "A1": dict(composition=Composition(ZI=70, TF=30)),
    "A2": dict(composition=Composition(ZI=70, MR=30)),
    "A4": dict(composition=Composition(ZI=70, PA=30)),
    "S-ZI": dict(composition=Composition(ZI=100), shock_step=SHOCK_STEP, shock_fraction=0.5),
    "S-ZI+TF": dict(composition=Composition(ZI=70, TF=30), shock_step=SHOCK_STEP, shock_fraction=0.5),
}
OUT = ROOT / "results" / "exploratory" / "M4-SENS"


def window_drawdown(mid: np.ndarray, t0: int = SHOCK_STEP, window: int = WINDOW) -> float:
    """The EXP-003 drawdown formula (market.metrics.shock_metrics) applied at step t0.

    Reference = mid recorded at step t0 - 1 (the pre-shock mid in a shocked run).
    """
    pre = float(mid[t0 - 1])
    return max(0.0, 1.0 - float(mid[t0 : t0 + window].min()) / pre)


def one_run(args: tuple[str, int]) -> dict:
    arm, seed = args
    cfg = SimConfig(**ARMS[arm]).validate()
    t = time.perf_counter()
    out = simulate(cfg, seed)
    row = {"arm": arm, "seed": seed, "config_hash": cfg.config_hash()}
    for dt in DT_GRID:
        r = sampled_log_returns(out.mid, cfg.burn_in, dt)
        row[f"vci_dt{dt}"] = vci(r)
        row[f"acf1_dt{dt}"] = acf(r, 1)  # signed-return autocorrelation: bounce (< 0) or trend runs (> 0)
    row["window_drawdown_50000"] = window_drawdown(out.mid)
    row["runtime_s"] = time.perf_counter() - t
    return row


def summarise(x: list[float]) -> dict:
    a = np.asarray(x, dtype=np.float64)
    means = boot_means(a)
    lo, hi = interval(means, 0.95)
    sd = float(np.std(a, ddof=1))
    return {"n": int(len(a)), "mean": float(a.mean()), "sd": sd, "d_z": float(a.mean() / sd) if sd > 0 else None,
            "ci95_low": lo, "ci95_high": hi}


def part1(workers: int) -> dict:
    jobs = [(arm, s) for arm in ARMS for s in SEEDS]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one_run, jobs))
    wall = time.time() - t0
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "runs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    by = {(r["arm"], r["seed"]): r for r in rows}

    def diff(t: str, c: str, key: str) -> list[float]:
        return [by[(t, s)][key] - by[(c, s)][key] for s in SEEDS if by[(t, s)][key] is not None and by[(c, s)][key] is not None]

    e1 = []
    for dt in DT_GRID:
        k = f"vci_dt{dt}"
        for t, c in (("A1", "A0"), ("A4", "A0"), ("A1", "A4"), ("A2", "A0")):
            e1.append(dict(contrast=f"{t} - {c}", metric=k, dt=dt, **summarise(diff(t, c, k))))
    arm_means = {arm: {f"{k}_dt{dt}": float(np.mean([by[(arm, s)][f"{k}_dt{dt}"] for s in SEEDS])) for k in ("vci", "acf1") for dt in DT_GRID}
                 for arm in ARMS}
    k = "window_drawdown_50000"
    did = [(by[("S-ZI+TF", s)][k] - by[("A1", s)][k]) - (by[("S-ZI", s)][k] - by[("A0", s)][k]) for s in SEEDS]
    e2 = {
        "shocked: S-ZI+TF - S-ZI (replicates the EXP-003 primary on development seeds)": summarise(diff("S-ZI+TF", "S-ZI", k)),
        "unshocked window: A1 - A0 (ordinary TF excursion, no shock)": summarise(diff("A1", "A0", k)),
        "shock response, TF market: S-ZI+TF - A1": summarise(diff("S-ZI+TF", "A1", k)),
        "shock response, ZI market: S-ZI - A0": summarise(diff("S-ZI", "A0", k)),
        "difference-in-differences: [S-ZI+TF - A1] - [S-ZI - A0]": summarise(did),
        "arm means of window drawdown": {arm: float(np.mean([by[(arm, s)][k] for s in SEEDS])) for arm in ARMS},
    }
    return {"n_runs": len(rows), "wall_time_s": wall, "seeds": [SEEDS[0], SEEDS[-1]], "dt_grid": list(DT_GRID),
            "E1_vci_dt_grid": e1, "E1_arm_means": arm_means, "E2_unshocked_control_window": e2}


def part2() -> dict:
    res = {}
    # E3: Holm intervals, ties at p = 0 given the most conservative level 1 - alpha / m
    e3 = {}
    for exp in ("EXP-001", "EXP-002", "EXP-003"):
        a = json.loads((ROOT / "results" / "confirmatory" / exp / "analysis.json").read_text())["result"]
        docs = load_results(ROOT / "results" / "confirmatory" / exp)
        by = {}
        for d in docs:
            if d["status"] == "ok":
                by.setdefault(d["arm"], {})[d["seed"]] = d["metrics"]
        rows = a["secondary_holm"]
        m = len([r for r in rows if r.get("p_boot") is not None])
        changed = []
        for r in rows:
            if r.get("p_boot") != 0.0:
                continue
            if r["metric"] == "vci (interaction)":
                seeds = sorted(by["med-ZI"])
                x = [(by["med-ZI+TF"][s]["vci"] - by["med-ZI"][s]["vci"]) - (by["high-ZI+TF"][s]["vci"] - by["high-ZI"][s]["vci"]) for s in seeds]
            else:
                t, c = by[r["treatment"]], by[r["control"]]
                x = [t[s][r["metric"]] - c[s][r["metric"]] for s in sorted(set(t) & set(c))]
            means = boot_means(np.asarray(x, dtype=np.float64))
            lo, hi = interval(means, 1.0 - ALPHA / m)
            changed.append({"contrast": f"{r['treatment']} - {r['control']}", "metric": r["metric"], "frozen_level": r["holm_level"],
                            "frozen_holm_ci": [r["holm_ci_low"], r["holm_ci_high"]], "conservative_level": 1.0 - ALPHA / m,
                            "conservative_ci": [lo, hi], "excludes_0": bool(lo > 0 or hi < 0),
                            "check_p_boot": boot_p(means)})
        e3[exp] = {"m": m, "tied_at_p0": len(changed), "all_still_exclude_0": all(c["excludes_0"] for c in changed), "rows": changed}
    res["E3_holm_conservative_ties"] = e3
    # E4: robustness rule with the H1 direction (+) as the sign reference
    a4 = json.loads((ROOT / "results" / "confirmatory" / "EXP-004" / "analysis.json").read_text())["result"]
    comps = [*a4["dt"], a4["tick2"]]
    rows = []
    for r in comps:
        same = r["mean_diff"] > 0
        ex0 = r["ci95_low"] > 0 or r["ci95_high"] < 0
        rows.append({"component": r["role"], "mean_diff": r["mean_diff"], "ci95": [r["ci95_low"], r["ci95_high"]],
                     "same_sign_as_H1": bool(same), "ci_excludes_0": bool(ex0)})
    robust = all(x["same_sign_as_H1"] and x["ci_excludes_0"] for x in rows)
    reversal = any((not x["same_sign_as_H1"]) and x["ci_excludes_0"] for x in rows)
    res["E4_robustness_rule_H1_reference"] = {
        "rows": rows,
        "reading": "robust" if robust else ("invalidated (a sign reversal with an interval excluding 0)" if reversal else
                                            "qualified (at least one dt or tick-2 contrast has a different sign or an interval including 0)"),
        "frozen_reading": a4["robustness_rule"],
    }
    # E5: seed-level association in committed EXP-001 runs
    docs = load_results(ROOT / "results" / "confirmatory" / "EXP-001")
    m1 = {d["seed"]: d["metrics"] for d in docs if d["arm"] == "A1"}
    m0 = {d["seed"]: d["metrics"] for d in docs if d["arm"] == "A0"}
    seeds = sorted(m1)

    def spearman(x, y):
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        return float(np.corrcoef(rx, ry)[0, 1])

    v1 = np.array([m1[s]["vci"] for s in seeds])
    dd = np.array([m1[s]["max_drawdown"] for s in seeds])
    rv = np.array([m1[s]["realised_volatility"] for s in seeds])
    d = np.array([m1[s]["vci"] - m0[s]["vci"] for s in seeds])
    res["E5_A1_seed_level"] = {
        "n": len(seeds),
        "spearman_vci_vs_max_drawdown": spearman(v1, dd),
        "spearman_vci_vs_realised_volatility": spearman(v1, rv),
        "spearman_paired_diff_vs_max_drawdown": spearman(d, dd),
        "A1_vci_min": float(v1.min()), "A1_vci_max": float(v1.max()),
        "A1_seeds_vci_below_0": int(np.sum(v1 < 0)),
        "A0_vci_min": float(min(m0[s]["vci"] for s in seeds)), "A0_vci_max": float(max(m0[s]["vci"] for s in seeds)),
    }
    # E6: EXP-003 shock covariates
    docs = load_results(ROOT / "results" / "confirmatory" / "EXP-003")
    e6 = {}
    for arm in ("S-ZI", "S-ZI+TF", "S-ZI+MR"):
        ok = [d for d in docs if d["arm"] == arm and d["status"] == "ok"]
        depth = np.array([d["shock"]["bid_depth"] for d in ok], dtype=float)
        dd = np.array([d["metrics"]["shock_drawdown"] for d in ok])
        e6[arm] = {"n": len(ok), "fully_filled": int(sum(d["shock"]["filled"] == d["shock"]["qty"] for d in ok)),
                   "one_sided_flagged": int(sum(d["flags"]["one_sided_over_5pct"] for d in ok)),
                   "spearman_drawdown_vs_bid_depth": spearman(dd, depth),
                   "bid_depth_min": float(depth.min()), "bid_depth_max": float(depth.max())}
    res["E6_EXP003_shock_covariates"] = e6
    return res


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--workers", type=int, default=2)
    args = p.parse_args(argv)
    if args.workers > 2:
        raise SystemExit("at most 2 workers (M4 brief)")
    rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    p1 = part1(args.workers)
    p2 = part2()
    doc = {"label": "exploratory", "journal": "J-0011", "decision": "D-016", "script": "scripts/m4_exploratory.py",
           "code_revision": rev, "started_utc": started, "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "platform": platform.platform(), "python": platform.python_version(), "numpy": np.__version__,
           "bootstrap": {"n_resamples": 10_000, "seed": 20261124, "method": "percentile, mean of per-seed paired differences"},
           "note": "EXPLORATORY. Development seeds 101..130 for new simulations; confirmatory outputs read only. "
                   "Never changes or replaces a frozen verdict.",
           "part1": p1, "part2": p2}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "m4_exploratory.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"n_runs": p1["n_runs"], "wall_time_s": round(p1["wall_time_s"], 1), "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
