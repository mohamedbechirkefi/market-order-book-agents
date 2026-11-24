# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Frozen M3 analysis of EXP-001 to EXP-004 (protocol v1.0 sections 4, 6, 7, 9 and the EXP protocols).

Written and tested before any confirmatory output existed (decision D-013). It never changes a
frozen artifact and is not to be edited once confirmatory output exists.

Procedures, as frozen:
- every contrast is a mean over seeds of per-seed paired differences (treatment minus control);
- 95% percentile bootstrap interval of that mean, 10,000 resamples, bootstrap seed 20261124
  (identical to ``market.analysis.bootstrap_mean_ci``); ``d_z`` = mean / SD of the differences;
- verdict of a directional hypothesis ``E[D] > 0``: supported if the interval lies above 0,
  contradicted if it lies below 0, otherwise inconclusive (never equivalence);
- degenerate-run sensitivity (protocol section 7): the same contrast without flagged runs and
  their paired partners;
- Holm-adjusted intervals for the declared secondary families of EXP-001 to EXP-003. The protocol
  does not spell out the interval construction; D-013 fixes it before any confirmatory data: a
  two-sided bootstrap p-value from the same resamples, ``p = min(1, 2 min(P*(mean <= 0), P*(mean >= 0)))``,
  Holm step-down adjusted p-values, and for the contrast with Holm rank ``j`` (1 = smallest p) out of
  ``m`` an interval at level ``1 - 0.05 / (m - j + 1)``.

    python -m market.frozen_analysis --exp EXP-001|EXP-002|EXP-003|EXP-004
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from html import escape
from pathlib import Path

import numpy as np

from .analysis import d_z, holm
from .runner import load_results, repo_root

N_RESAMPLES = 10_000
BOOT_SEED = 20261124
ALPHA = 0.05

EXP001_SECONDARY_METRICS = ("vci", "realised_volatility", "excess_kurtosis", "return_acf1", "mean_spread", "mean_depth_at_best",
                            "volume_per_step", "max_drawdown", "one_sided_fraction", "rejected_fraction")
EXP002_LEVEL_METRICS = ("mean_spread", "mean_depth_at_best", "volume_per_step", "realised_volatility")


# ----- core statistics -----

def boot_means(x: np.ndarray, n_resamples: int = N_RESAMPLES, seed: int = BOOT_SEED) -> np.ndarray:
    """Bootstrap means drawn exactly as ``market.analysis.bootstrap_mean_ci`` draws them."""
    x = np.asarray(x, dtype=np.float64)
    rng = np.random.Generator(np.random.PCG64(seed))
    idx = rng.integers(0, len(x), size=(n_resamples, len(x)))
    return x[idx].mean(axis=1)


def interval(means: np.ndarray, level: float) -> tuple[float, float]:
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [a, 1.0 - a])
    return float(lo), float(hi)


def boot_p(means: np.ndarray) -> float:
    return float(min(1.0, 2.0 * min(np.mean(means <= 0.0), np.mean(means >= 0.0))))


def verdict(lo: float | None, hi: float | None) -> str:
    """Directional H1 (E[D] > 0) under the frozen rule."""
    if lo is None or hi is None:
        return "undefined"
    if lo > 0:
        return "supported"
    if hi < 0:
        return "contradicted"
    return "inconclusive"


def _by_seed(docs: list[dict], arm: str, metric: str, drop: set[int] = frozenset()) -> dict[int, float]:
    out = {}
    for d in docs:
        if d["arm"] == arm and d["status"] == "ok" and d["seed"] not in drop:
            v = d["metrics"].get(metric)
            if v is not None:
                out[d["seed"]] = float(v)
    return out


def flagged_seeds(docs: list[dict], arms: tuple[str, ...]) -> set[int]:
    """Seeds where any of ``arms`` is flagged degenerate or failed (the run and its paired partners are dropped)."""
    return {d["seed"] for d in docs if d["arm"] in arms and (d["status"] != "ok" or d["flags"]["degenerate"])}


def contrast(diffs: dict[int, float], label: dict) -> dict:
    x = np.array([diffs[s] for s in sorted(diffs)])
    row = dict(label, n_pairs=int(len(x)), mean_diff=None, sd_diff=None, d_z=None, ci95_low=None, ci95_high=None, p_boot=None,
               seeds_used=sorted(diffs))
    if len(x) >= 1:
        row["mean_diff"] = float(x.mean())
    if len(x) >= 2:
        row["sd_diff"] = float(np.std(x, ddof=1))
        row["d_z"] = d_z(x)
        means = boot_means(x)
        row["ci95_low"], row["ci95_high"] = interval(means, 0.95)
        row["p_boot"] = boot_p(means)
        row["_means"] = means
    return row


def paired(docs_t: list[dict], arm_t: str, docs_c: list[dict], arm_c: str, metric: str, drop: set[int] = frozenset(),
           **label) -> dict:
    t, c = _by_seed(docs_t, arm_t, metric, drop), _by_seed(docs_c, arm_c, metric, drop)
    diffs = {s: t[s] - c[s] for s in sorted(set(t) & set(c))}
    return contrast(diffs, dict(label, treatment=arm_t, control=arm_c, metric=metric))


def holm_family(rows: list[dict]) -> list[dict]:
    """Add Holm-adjusted p-values and step-down intervals (D-013) to a family of secondary contrasts."""
    usable = [r for r in rows if r.get("p_boot") is not None]
    m = len(usable)
    if m == 0:
        return rows
    adj = holm([r["p_boot"] for r in usable])
    order = sorted(range(m), key=lambda i: usable[i]["p_boot"])
    for rank, i in enumerate(order, start=1):
        r = usable[i]
        level = 1.0 - ALPHA / (m - rank + 1)
        r["holm_rank"], r["holm_m"], r["p_holm"] = rank, m, adj[i]
        r["holm_level"] = level
        r["holm_ci_low"], r["holm_ci_high"] = interval(r["_means"], level)
    return rows


def _clean(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def arm_flags(docs: list[dict]) -> dict:
    out = {}
    for d in docs:
        a = out.setdefault(d["arm"], {"runs": 0, "failed": 0, "degenerate": 0, "one_sided_over_5pct": 0,
                                      "fewer_than_50_nonzero_returns": 0, "vci_undefined": 0})
        a["runs"] += 1
        a["failed"] += d["status"] != "ok"
        for k in ("degenerate", "one_sided_over_5pct", "fewer_than_50_nonzero_returns", "vci_undefined"):
            a[k] += bool(d["flags"].get(k))
    for a in out.values():
        a["flag_rate"] = a["degenerate"] / a["runs"] if a["runs"] else None
    return dict(sorted(out.items()))


# ----- per-experiment analyses -----

def analyse_exp001(docs: list[dict]) -> dict:
    prim = paired(docs, "A1", docs, "A0", "vci", role="primary")
    prim["verdict"] = verdict(prim["ci95_low"], prim["ci95_high"])
    drop = flagged_seeds(docs, ("A0", "A1"))
    sens = paired(docs, "A1", docs, "A0", "vci", drop=drop, role="sensitivity: flagged runs and partners excluded")
    sens["verdict"] = verdict(sens["ci95_low"], sens["ci95_high"])
    sec = [paired(docs, t, docs, c, m, role="secondary")
           for (t, c) in (("A2", "A0"), ("A3", "A0"), ("A1", "A2")) for m in EXP001_SECONDARY_METRICS]
    holm_family(sec)
    tf_skip = [d["metrics"].get("tf_skip_fraction") for d in docs if d["arm"] == "A1" and d["status"] == "ok"]
    tf_skip = [v for v in tf_skip if v is not None]
    return {"primary": _clean([prim])[0], "sensitivity_exclusion": _clean([sens])[0], "flagged_seeds_A0_A1": sorted(drop),
            "secondary_holm": _clean(sec), "arm_flags": arm_flags(docs),
            "a1_tf_skip_fraction": {"n": len(tf_skip), "mean": float(np.mean(tf_skip)) if tf_skip else None,
                                    "max": float(np.max(tf_skip)) if tf_skip else None}}


def analyse_exp002(docs: list[dict], excluded: tuple[str, ...] = ("low-ZI+TF",)) -> dict:
    use = [d for d in docs if d["arm"] not in excluded]
    prim = paired(use, "low-ZI", use, "high-ZI", "mean_spread", role="primary")
    prim["verdict"] = verdict(prim["ci95_low"], prim["ci95_high"])
    drop = flagged_seeds(use, ("low-ZI", "high-ZI"))
    sens = paired(use, "low-ZI", use, "high-ZI", "mean_spread", drop=drop, role="sensitivity: flagged runs and partners excluded")
    sens["verdict"] = verdict(sens["ci95_low"], sens["ci95_high"])
    sec = []
    for t, c in (("low-ZI", "med-ZI"), ("low-ZI", "high-ZI"), ("med-ZI", "high-ZI"), ("med-ZI+TF", "high-ZI+TF")):
        for m in EXP002_LEVEL_METRICS:
            if (t, c, m) == ("low-ZI", "high-ZI", "mean_spread"):
                continue  # the primary contrast is not part of the secondary family
            sec.append(paired(use, t, use, c, m, role="secondary"))
    v = {a: _by_seed(use, a, "vci") for a in ("med-ZI+TF", "med-ZI", "high-ZI+TF", "high-ZI")}
    seeds = sorted(set.intersection(*(set(x) for x in v.values())))
    inter = {s: (v["med-ZI+TF"][s] - v["med-ZI"][s]) - (v["high-ZI+TF"][s] - v["high-ZI"][s]) for s in seeds}
    sec.append(contrast(inter, {"role": "secondary", "treatment": "[med-ZI+TF - med-ZI]", "control": "[high-ZI+TF - high-ZI]",
                                "metric": "vci (interaction)"}))
    holm_family(sec)
    flags = arm_flags(docs)
    failures = {a: f["flag_rate"] for a, f in flags.items() if f["flag_rate"] is not None and f["flag_rate"] > 0.20}
    return {"primary": _clean([prim])[0], "sensitivity_exclusion": _clean([sens])[0], "flagged_seeds_low_high_ZI": sorted(drop),
            "secondary_holm": _clean(sec), "arm_flags": flags, "excluded_from_contrasts": list(excluded),
            "arms_flag_rate_above_20pct (model failure for that arm)": failures}


def kaplan_meier(times: list[int], censored: list[bool]) -> dict:
    """Product-limit estimate of the recovery-time survival curve (descriptive only)."""
    t = np.asarray(times)
    e = ~np.asarray(censored, dtype=bool)
    s, curve, median = 1.0, [], None
    for u in sorted(set(t[e].tolist())):
        at_risk = int(np.sum(t >= u))
        events = int(np.sum((t == u) & e))
        s *= 1.0 - events / at_risk
        curve.append([int(u), s])
        if median is None and s <= 0.5:
            median = int(u)
    return {"n": int(len(t)), "events": int(e.sum()), "censored": int((~e).sum()), "median_steps": median, "curve": curve}


def analyse_exp003(docs: list[dict]) -> dict:
    prim = paired(docs, "S-ZI+TF", docs, "S-ZI", "shock_drawdown", role="primary")
    prim["verdict"] = verdict(prim["ci95_low"], prim["ci95_high"])
    drop = flagged_seeds(docs, ("S-ZI+TF", "S-ZI"))
    sens = paired(docs, "S-ZI+TF", docs, "S-ZI", "shock_drawdown", drop=drop, role="sensitivity: flagged runs and partners excluded")
    sens["verdict"] = verdict(sens["ci95_low"], sens["ci95_high"])
    sec = [paired(docs, "S-ZI+MR", docs, "S-ZI", "shock_drawdown", role="secondary")]
    holm_family(sec)
    km, shock = {}, {}
    for arm in ("S-ZI", "S-ZI+TF", "S-ZI+MR"):
        ok = [d for d in docs if d["arm"] == arm and d["status"] == "ok"]
        km[arm] = kaplan_meier([d["metrics"]["shock_recovery_steps"] for d in ok], [d["metrics"]["shock_recovery_censored"] for d in ok])
        depth = [d["shock"]["bid_depth"] for d in ok if d.get("shock")]
        shock[arm] = {"bid_depth_at_shock_mean": float(np.mean(depth)) if depth else None,
                      "bid_depth_at_shock_sd": float(np.std(depth, ddof=1)) if len(depth) > 1 else None,
                      "window_truncated": sum(bool(d["metrics"].get("shock_window_truncated")) for d in ok)}
    return {"primary": _clean([prim])[0], "sensitivity_exclusion": _clean([sens])[0], "flagged_seeds": sorted(drop),
            "secondary_holm": _clean(sec), "recovery_kaplan_meier": km, "shock_covariates": shock, "arm_flags": arm_flags(docs),
            "not_measured": "spread widening after the shock: no per-run metric exists and the protocol gives no formula (D-013)"}


def analyse_exp004(docs4: list[dict], docs1: list[dict], exp001_primary: dict) -> dict:
    placebo = paired(docs1, "A1", docs4, "A4", "vci", role="placebo: EXP-001 A1 minus EXP-004 A4")
    placebo["verdict"] = verdict(placebo["ci95_low"], placebo["ci95_high"])
    a4_a0 = paired(docs4, "A4", docs1, "A0", "vci", role="descriptive: A4 minus EXP-001 A0")
    tick = paired(docs4, "A1-tick2", docs4, "A0-tick2", "vci", role="tick 2: A1-tick2 minus A0-tick2")
    dts = [paired(docs1, "A1", docs1, "A0", m, role=f"sampling interval {m}") for m in ("vci_dt10", "vci_dt200")]
    drop = flagged_seeds(docs1, ("A0", "A1"))
    excl = paired(docs1, "A1", docs1, "A0", "vci", drop=drop, role="exclusion of flagged runs and partners")
    sign = np.sign(exp001_primary["mean_diff"]) if exp001_primary.get("mean_diff") is not None else 0.0
    checks = []
    for r in [*dts, tick]:
        same = r["mean_diff"] is not None and np.sign(r["mean_diff"]) == sign and sign != 0
        excludes0 = r["ci95_low"] is not None and (r["ci95_low"] > 0 or r["ci95_high"] < 0)
        r["same_sign_as_exp001"] = bool(same)
        r["ci_excludes_0"] = bool(excludes0)
        checks.append(same and excludes0)
    reversal = any(r["mean_diff"] is not None and sign != 0 and np.sign(r["mean_diff"]) == -sign and r["ci_excludes_0"] for r in [*dts, tick])
    exp001_supported = exp001_primary.get("verdict") == "supported"
    if placebo["ci95_low"] is None:
        placebo_rule = "undefined"
    elif exp001_supported and placebo["ci95_low"] <= 0 <= placebo["ci95_high"]:
        placebo_rule = "EXP-001 effect not attributable to trend feedback (placebo CI includes 0 while EXP-001 supports H1)"
    elif exp001_supported:
        placebo_rule = f"placebo contrast {placebo['verdict']}; EXP-001 supports H1"
    else:
        placebo_rule = f"placebo contrast {placebo['verdict']}; EXP-001 does not support H1 (verdict {exp001_primary.get('verdict')}), so the attribution rule is not triggered"
    robust = ("robust" if all(checks) else
              "invalidated (a sign reversal with an interval excluding 0)" if reversal else
              "qualified (at least one dt or tick-2 contrast has a different sign or an interval including 0)")
    return {"placebo": _clean([placebo])[0], "placebo_rule": placebo_rule, "a4_minus_a0": _clean([a4_a0])[0],
            "tick2": _clean([tick])[0], "dt": _clean(dts), "exclusion": _clean([excl])[0], "flagged_seeds_A0_A1": sorted(drop),
            "robustness_rule": robust, "exp001_primary_reference": {k: exp001_primary.get(k) for k in ("mean_diff", "ci95_low", "ci95_high", "verdict")},
            "arm_flags": arm_flags(docs4)}


# ----- outputs -----

def forest_svg(path: Path, rows: list[dict], title: str, desc: str, lo_key="ci95_low", hi_key="ci95_high") -> None:
    rows = [r for r in rows if r.get(lo_key) is not None]
    if not rows:
        return
    W, row_h, left, right, top = 760, 26, 330, 30, 46
    H = top + row_h * len(rows) + 40
    lo = min(min(r[lo_key] for r in rows), 0.0)
    hi = max(max(r[hi_key] for r in rows), 0.0)
    pad = (hi - lo) * 0.06 or 0.01
    lo, hi = lo - pad, hi + pad
    X = lambda v: left + (W - left - right) * (v - lo) / (hi - lo)  # noqa: E731
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">',
         f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>', f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{W/2}" y="22" font-family="serif" font-size="15" text-anchor="middle" fill="#111">{escape(title)}</text>',
         f'<line x1="{X(0):.1f}" y1="{top-8}" x2="{X(0):.1f}" y2="{H-34}" stroke="#888" stroke-dasharray="4 3"/>']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        s.append(f'<text x="{X(v):.1f}" y="{H-18}" font-family="sans-serif" font-size="11" text-anchor="middle" fill="#333">{v:.3g}</text>')
    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2
        lab = f"{r['treatment']} - {r['control']}: {r['metric']}"
        s.append(f'<text x="{left-8}" y="{y+4:.1f}" font-family="sans-serif" font-size="11" text-anchor="end" fill="#333">{escape(lab[:52])}</text>')
        s.append(f'<line x1="{X(r[lo_key]):.1f}" y1="{y:.1f}" x2="{X(r[hi_key]):.1f}" y2="{y:.1f}" stroke="#1f4e79" stroke-width="2"/>')
        s.append(f'<circle cx="{X(r["mean_diff"]):.1f}" cy="{y:.1f}" r="4" fill="#b22222"/>')
    s.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(s) + "\n", encoding="utf-8")


def _write_rows(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys and k != "seeds_used":
                keys.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


def run(exp: str, root: Path | None = None) -> dict:
    root = root or repo_root()
    base = root / "results" / "confirmatory"
    docs = load_results(base / exp)
    if {d["label"] for d in docs} != {"confirmatory"} or {d["exp_id"] for d in docs} != {exp}:
        raise ValueError(f"{base / exp} must hold confirmatory {exp} results only")
    if exp == "EXP-001":
        res = analyse_exp001(docs)
        contrasts = [res["primary"], res["sensitivity_exclusion"], *res["secondary_holm"]]
        fig_rows = [res["primary"], res["sensitivity_exclusion"]] + [r for r in res["secondary_holm"] if r["metric"] == "vci"]
    elif exp == "EXP-002":
        res = analyse_exp002(docs)
        contrasts = [res["primary"], res["sensitivity_exclusion"], *res["secondary_holm"]]
        fig_rows = [res["primary"], res["sensitivity_exclusion"]] + [r for r in res["secondary_holm"] if r["metric"] == "mean_spread"]
    elif exp == "EXP-003":
        res = analyse_exp003(docs)
        contrasts = [res["primary"], res["sensitivity_exclusion"], *res["secondary_holm"]]
        fig_rows = contrasts
    elif exp == "EXP-004":
        docs1 = load_results(base / "EXP-001")
        if {d["label"] for d in docs1} != {"confirmatory"}:
            raise ValueError("EXP-004 needs the confirmatory EXP-001 results")
        prim1 = analyse_exp001(docs1)["primary"]
        res = analyse_exp004(docs, docs1, prim1)
        contrasts = [res["placebo"], res["a4_minus_a0"], res["tick2"], *res["dt"], res["exclusion"]]
        fig_rows = contrasts
    else:
        raise ValueError(f"unknown experiment {exp}")
    out = base / exp
    doc = {"label": "confirmatory", "exp_id": exp, "analysis": "market.frozen_analysis (D-013)", "n_resamples": N_RESAMPLES,
           "bootstrap_seed": BOOT_SEED, "result": res}
    (out / "analysis.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    _write_rows(out / "tables" / "frozen_contrasts.csv", contrasts)
    forest_svg(out / "figures" / "frozen_contrasts.svg", fig_rows, f"{exp}: paired contrasts, 95% percentile bootstrap intervals",
               "Mean paired difference over seeds (red dot) with its 95% percentile bootstrap interval (blue line, 10,000 resamples); "
               "dashed line at 0. Each row gives treatment minus control and the metric.")
    return doc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="market.frozen_analysis")
    p.add_argument("--exp", required=True, choices=["EXP-001", "EXP-002", "EXP-003", "EXP-004"])
    a = p.parse_args(argv)
    doc = run(a.exp)
    r = doc["result"]
    print(json.dumps({k: r[k] for k in r if k in ("primary", "placebo", "placebo_rule", "robustness_rule")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
