# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Export the published results for the static demo (M5): demo/public/data/results.json.

Reads committed outputs only (results/confirmatory/, results/exploratory/M4-SENS/), the claims
register, the experiment registry and the artifact manifest. Every printed number is formatted
with the same functions that fill the manuscript tables (scripts/m4_tables.py: g and ci), so
the page prints exactly the text of the manuscript. No timestamps; the output is deterministic.

    .venv/bin/python scripts/export_demo_data.py          # write the file
    .venv/bin/python scripts/export_demo_data.py --check  # exit 1 if the committed file differs
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m4_tables import ci, g  # noqa: E402  (the manuscript's own number formatting)

OUT = ROOT / "demo" / "public" / "data" / "results.json"
RES = "results/confirmatory"
SCHEMA = "lab-demo-results"
SCHEMA_VERSION = "1.0.0"


class Reader:
    """Reads repository files and remembers each one's SHA-256 for the sources list."""

    def __init__(self) -> None:
        self.sources: dict[str, str] = {}

    def raw(self, rel: str) -> bytes:
        b = (ROOT / rel).read_bytes()
        self.sources[rel] = hashlib.sha256(b).hexdigest()
        return b

    def json(self, rel: str):
        return json.loads(self.raw(rel))

    def csv(self, rel: str) -> list[dict]:
        return list(csv.DictReader(self.raw(rel).decode("utf-8").splitlines()))


def est(label: str, x: float, lo: float | None, hi: float | None, level: float | None, unit: str = "") -> dict:
    return {
        "label": label,
        "estimate": x,
        "ci_low": lo,
        "ci_high": hi,
        "ci_level": level if lo is not None else None,
        "unit": unit,
        "display": g(x),
        "interval_display": ci(lo, hi) if lo is not None else None,
    }


def contrast(label: str, r: dict, unit: str = "") -> dict:
    return est(label, r["mean_diff"], r["ci95_low"], r["ci95_high"], 0.95, unit)


def holm(label: str, r: dict, unit: str = "") -> dict:
    return est(label, r["mean_diff"], r["holm_ci_low"], r["holm_ci_high"], r["holm_level"], unit)


def build() -> dict:
    rd = Reader()
    a1 = rd.json(f"{RES}/EXP-001/analysis.json")["result"]
    a2 = rd.json(f"{RES}/EXP-002/analysis.json")["result"]
    a3 = rd.json(f"{RES}/EXP-003/analysis.json")["result"]
    a4 = rd.json(f"{RES}/EXP-004/analysis.json")["result"]
    c5 = rd.json(f"{RES}/EXP-005/comparison.json")
    ex = rd.json("results/exploratory/M4-SENS/m4_exploratory.json")
    claims = rd.csv("research/claims_register.csv")
    registry = {r["exp_id"]: r for r in rd.csv("research/experiment_registry.csv")}
    manifest = rd.json("research/publication/artifact_manifest.json")
    config = rd.json("experiments/configs/EXP-001.json")

    revs = sorted({a["code_revision"] for a in manifest["artifacts"] if a["label"] == "confirmatory"})
    if len(revs) != 1:
        raise SystemExit(f"expected one confirmatory code revision in the manifest, found {revs}")

    # C-016 (exploratory reanalysis of the EXP-004 rule with the H1 sign) is keyed to M4-SENS, not to an EXP id.
    extra = {"EXP-001": ["C-016"], "EXP-004": ["C-016"]}

    def claim_ids(exp: str) -> list[str]:
        ids = [c["claim_id"] for c in claims if f"{exp}:" in c["result_id"]]
        known = {c["claim_id"] for c in claims}
        return ids + [i for i in extra.get(exp, []) if i in known and i not in ids]

    def status(exp: str, role: str) -> str:
        return f"{role}; {registry[exp]['status'].split(':')[0]}"

    p1, p2, p3 = a1["primary"], a2["primary"], a3["primary"]
    sec1 = {(r["treatment"], r["control"], r["metric"]): r for r in a1["secondary_holm"]}
    inter = [r for r in a2["secondary_holm"] if r["metric"] == "vci (interaction)"][0]
    mr = a3["secondary_holm"][0]
    rule = a4["robustness_rule"]
    dt10, dt200 = a4["dt"]
    hv = c5["heldout_check"]["vci_values"]
    e4 = ex["part2"]["E4_robustness_rule_H1_reference"]

    experiments = [
        {
            "id": "EXP-001",
            "title": "Agent mixtures and volatility clustering (primary hypothesis H1)",
            "status": status("EXP-001", "confirmatory primary"),
            "verdict": f"{rule}, under the frozen EXP-004 robustness rule; the primary contrast alone is {p1['verdict']} (H1 not supported)",
            "estimates": [
                contrast("VCI(A1) - VCI(A0), dt 50 (primary)", p1),
                holm("VCI(A2) - VCI(A0), mean reverters (secondary, Holm interval)", sec1[("A2", "A0", "vci")]),
                holm("VCI(A3) - VCI(A0), mixture (secondary, Holm interval)", sec1[("A3", "A0", "vci")]),
            ],
            "claim_ids": claim_ids("EXP-001"),
            "report_path": "research/experiments/EXP-001/report.md",
            "notes": [
                f"{p1['n_pairs']} paired seeds, d_z {g(p1['d_z'], 3)}. An inconclusive result is not evidence of no effect.",
                f"Secondary reading only (exploratory, E4): with the sign of H1 as the reference, the same rule would return \"{e4['reading'].split(' (')[0]}\" "
                "rather than \"invalidated\". Both readings agree that the answer depends on the sampling interval.",
            ],
        },
        {
            "id": "EXP-002",
            "title": "Liquidity supply and spread",
            "status": status("EXP-002", "confirmatory"),
            "verdict": f"{p2['verdict']}",
            "estimates": [
                contrast("spread(low-ZI) - spread(high-ZI), ZI-only (primary)", p2, "price units"),
                holm("interaction on VCI, [med-ZI+TF - med-ZI] - [high-ZI+TF - high-ZI] (secondary, Holm interval)", inter),
            ],
            "claim_ids": claim_ids("EXP-002"),
            "report_path": "research/experiments/EXP-002/report.md",
            "notes": [
                "The pre-declared low-ZI+TF arm was degenerate in 30 of 30 runs (model failure for that arm) and is excluded from every contrast.",
                "The interaction may reflect discreteness at a spread close to one tick rather than an interplay between liquidity and trend feedback.",
            ],
        },
        {
            "id": "EXP-003",
            "title": "Response to an exogenous sell shock (optional)",
            "status": status("EXP-003", "confirmatory, optional"),
            "verdict": f"{p3['verdict']} (drawdown); spread widening not measured",
            "estimates": [
                contrast("post-shock drawdown(S-ZI+TF) - drawdown(S-ZI) (primary)", p3, "fraction of the pre-shock mid"),
                holm("post-shock drawdown(S-ZI+MR) - drawdown(S-ZI) (secondary, Holm interval)", mr, "fraction of the pre-shock mid"),
            ],
            "claim_ids": claim_ids("EXP-003"),
            "report_path": "research/experiments/EXP-003/report.md",
            "notes": [
                "In 7 of 30 trend-follower runs the mid did not return within 1% of the pre-shock level within 20,000 steps (censored).",
            ],
        },
        {
            "id": "EXP-004",
            "title": "Sensitivity analyses that could invalidate EXP-001",
            "status": status("EXP-004", "confirmatory sensitivity"),
            "verdict": f"robustness rule: {rule}; placebo contrast {a4['placebo']['verdict']}, attribution rule not triggered (EXP-001 inconclusive)",
            "estimates": [
                contrast("placebo: VCI(A1) - VCI(A4)", a4["placebo"]),
                contrast("descriptive: VCI(A4) - VCI(A0)", a4["a4_minus_a0"]),
                contrast("sampling interval dt 10: VCI(A1) - VCI(A0)", dt10),
                contrast("sampling interval dt 200: VCI(A1) - VCI(A0)", dt200),
                contrast("tick 2: VCI(A1-tick2) - VCI(A0-tick2)", a4["tick2"]),
            ],
            "claim_ids": claim_ids("EXP-004"),
            "report_path": "research/experiments/EXP-004/report.md",
            "notes": [
                "The rule calls EXP-001 robust only if every dt and tick component has the same sign as EXP-001 and an interval excluding 0. "
                "The sign reference is the near-zero EXP-001 point estimate (D-013), so its sign is weakly determined (D-015).",
                "The six EXP-004 components carry no multiplicity adjustment; the placebo interval's upper end is close to 0.",
            ],
        },
        {
            "id": "EXP-005",
            "title": "Simulated and real-market statistics (FI-2010), descriptive",
            "status": status("EXP-005", "descriptive, real data, no new runs"),
            "verdict": "(a) not supported (one stock below 0); (b) descriptive" if not c5["heldout_check"]["vci_positive_all"] else "(a) supported; (b) descriptive",
            "estimates": [
                *[est(f"held-out day 10, VCI (h 5), stock {i + 1} of 5", v, None, None, None) for i, v in enumerate(hv)],
                *[est(f"arm {r['arm']} mean VCI against FI-2010 range: {r['placement']}", r["sim_mean"], r["ci95_low"], r["ci95_high"], 0.95)
                  for r in c5["arms"] if r["sampling"] == "primary" and r["statistic"] == "vci"],
            ],
            "claim_ids": claim_ids("EXP-005"),
            "report_path": "research/experiments/EXP-005/report.md",
            "notes": [
                "Single stock-days give noisy VCI estimates; no interval is reported for them.",
                "The placement is descriptive, depends on a crude clock match, and is never a validation of the model or a statement about real markets.",
            ],
        },
    ]
    grid = {(r["contrast"], r["dt"]): r for r in ex["part1"]["E1_vci_dt_grid"]}
    dt_grid = {
        "label": "EXPLORATORY (post hoc, development seeds 101 to 130; not confirmatory, never changes a verdict)",
        "source": "results/exploratory/M4-SENS/m4_exploratory.json#part1.E1_vci_dt_grid",
        "claim_ids": ["C-013", "C-014"],
        "unit": "VCI difference (dimensionless)",
        "contrasts": ["A1 - A0", "A4 - A0", "A1 - A4"],
        "rows": [
            {
                "dt": dt,
                "cells": [
                    est(c, grid[(c, dt)]["mean"], grid[(c, dt)]["ci95_low"], grid[(c, dt)]["ci95_high"], 0.95) for c in ("A1 - A0", "A4 - A0", "A1 - A4")
                ],
            }
            for dt in ex["part1"]["dt_grid"]
        ],
    }

    arms_label = {"A0": "A0: 100 random-order", "A1": "A1: 70 ZI + 30 trend followers", "A2": "A2: 70 ZI + 30 mean reverters",
                  "A3": "A3: 70 ZI + 15 TF + 15 MR"}
    paths = []
    for arm in ("A0", "A1", "A2", "A3"):
        s = rd.json(f"{RES}/EXP-001/series/EXP-001-{arm}-s1001.json")
        paths.append({"arm": arm, "label": arms_label[arm], "run_id": s["run_id"], "every": s["every"], "mid": s["mid"]})
    mid_paths = {
        "label": "Measured: EXP-001 confirmatory runs, seed 1001, one per arm (manuscript Figure 2)",
        "unit": "mid price (price units) against event time (steps)",
        "source": f"{RES}/EXP-001/series/",
        "burn_in": 10_000,
        "arms": paths,
    }

    cfg_note = config["note"]
    assumptions = [
        {"name": "Market", "value": "one asset, continuous double auction with price-time priority; trades at the resting order's price; no fees, latency or hidden orders", "source": "manuscript section 3; frozen protocol section 3"},
        {"name": "Price grid", "value": "integer prices, tick 1 (tick 2 in the EXP-004 tick arms); initial price 1,000; price floor of one tick", "source": "manuscript section 3"},
        {"name": "Time", "value": "event time: T = 100,000 steps, one of 100 agents drawn uniformly per step; first B = 10,000 steps are burn-in", "source": "manuscript section 3"},
        {"name": "Accounting", "value": "cash and inventory never negative (no short selling, no borrowing); endowment 1,000,000 cash and 1,000 units per agent", "source": "manuscript section 3"},
        {"name": "Random-order (ZI) agent", "value": "market order with probability 0.2, otherwise a limit order 0 to 10 ticks behind the best opposite quote; sizes uniform on 1 to 5 units", "source": "manuscript section 3"},
        {"name": "Trend follower (TF)", "value": "direction sign(m_t - m_{t-500}); no order when the signal is 0; market order with probability 0.5, else a limit order at its own best quote", "source": "manuscript section 3"},
        {"name": "Mean reverter (MR)", "value": "direction -sign(m_t - MA_500(m)_t), same order rule as TF", "source": "manuscript section 3"},
        {"name": "Placebo aggressive (PA)", "value": "TF order types and sizes, direction from a fair coin independent of prices", "source": "manuscript section 3"},
        {"name": "Order lifetime", "value": "every resting order expires after 2,000 steps", "source": "manuscript section 3"},
        {"name": "Primary metric", "value": "VCI = mean autocorrelation of absolute mid-price log returns at lags 1 to 10, returns sampled every dt = 50 steps after burn-in", "source": "manuscript section 3"},
        {"name": "Seeds and analysis", "value": "confirmatory seeds 1001 to 1030 shared across arms (common random numbers); paired differences with 95% percentile bootstrap intervals (10,000 resamples)", "source": "manuscript section 4.4"},
        {"name": "Frozen configuration", "value": cfg_note, "source": "experiments/configs/EXP-001.json"},
    ]

    limitations = [
        "VCI is one statistic. In this model it is shaped by bid-ask bounce at short sampling intervals and by trend runs at long intervals, so it is not a clean measure of volatility clustering.",
        "The EXP-004 verdict depends on an analysis choice: with the sign of H1 as the reference, the robustness rule returns \"qualified\" instead of the frozen \"invalidated\".",
        "A1's VCI varies widely across seeds, so the primary test had low power for the effect that occurred; a null result is not evidence of no effect.",
        "Replacing random-order agents by trend followers also changes depth and spread; the placebo matches order types, sizes and activity but not the serial correlation of direction.",
        "One parameter set, 100 fixed-rule agents, one asset, self-trades allowed, a one-tick price floor; the model is not calibrated to any market.",
        "The FI-2010 comparison covers five Helsinki stocks over ten days in 2010 with a crude clock match; it is descriptive only.",
        "The exploratory checks were designed after the confirmatory results were seen; they are hypothesis-generating only.",
        "Nothing here is a statement about real markets, a prediction, trading advice or a claim of profitability.",
    ]

    not_measured = [
        {"exp_id": "EXP-003", "outcome": "spread widening after the shock (declared secondary outcome)", "status": "not measured",
         "reason": "the protocol gives no formula and no metric is defined after the data (owner decision, D-015)"},
        {"exp_id": "EXP-002", "outcome": "order lifetime halved (protocol sensitivity)", "status": "not run", "reason": "never run (manuscript section 7)"},
        {"exp_id": "EXP-003", "outcome": "25% shock (protocol sensitivity)", "status": "not run", "reason": "never run (manuscript section 7)"},
    ]

    headline = {
        "frozen_verdict": "invalidated",
        "frozen_text": "Under the frozen protocol, the primary interpretation is invalidated: EXP-001 is invalidated by a sign reversal under the frozen EXP-004 robustness rule. "
                       "Trend followers did not detectably change volatility clustering at the preregistered interval of 50 steps, and the contrast was positive, with intervals excluding 0, at 10 and 200 steps.",
        "secondary_reading": "qualified",
        "secondary_text": "As a secondary reading only, taking the sign of H1 as the reference would make the same rule return \"qualified\" rather than \"invalidated\". "
                          "Both readings agree that the answer depends on the sampling interval.",
    }

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "project": "MARKET",
        "question": "Within a simulated continuous double auction with price-time priority and cash and inventory constraints, does replacing 30% of random-order traders by trend followers change the volatility clustering of mid-price returns, and is any change attributable to price feedback rather than to aggressiveness, the sampling interval or the tick size?",
        "status_label": "Frozen verdict: invalidated (EXP-001, sign reversal under the EXP-004 robustness rule). Preregistered simulation study; independent preprint draft, not peer-reviewed.",
        "code_revision": revs[0],
        "sources": [{"path": p, "sha256": h} for p, h in sorted(rd.sources.items())],
        "experiments": experiments,
        "assumptions": assumptions,
        "limitations": limitations,
        "headline": headline,
        "not_measured": not_measured,
        "exploratory_dt_grid": dt_grid,
        "mid_paths": mid_paths,
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=False, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(build())
    if "--check" in argv:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("export check:", "identical" if same else "DIFFERS")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
