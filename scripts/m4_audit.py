# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M4 evidence audit (master prompt 11.5): artifact manifest, raw-output checks and number trace.

1. Integrity: every file listed in results/confirmatory/EXP-00N/SHA256SUMS matches its checksum.
2. Raw checks: per-run JSON against metrics.csv (every metric, exact), run and arm counts, statuses,
   n_returns, the arm summary table against a recomputation from the runs, and the primary
   contrasts of EXP-001 to EXP-004 recomputed independently from the per-run JSON (mean of
   paired differences, n pairs, percentile bootstrap with the frozen seed).
3. Artifact manifest: research/publication/artifact_manifest.json maps every numeric value in the
   committed analysis outputs (analysis.json, comparison.json, arm_summary.csv, run manifests,
   the FI-2010 reference and the labelled exploratory M4 output) to experiment id, run ids, metric,
   result path and JSON path, generator script, config and protocol SHA-256 and code revision.
4. Number trace: every decimal number in the manuscript, the supplement and the five experiment
   reports must equal (at the precision printed) a value in the manifest, or a frozen parameter
   or structural constant. Unmatched tokens are listed for manual review.

    .venv/bin/python scripts/m4_audit.py            # writes the manifest and research/publication/audit_result.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "confirmatory"
EXPL = ROOT / "results" / "exploratory"
FREEZE = json.loads((ROOT / "research" / "freeze.json").read_text())
EXPS = ("EXP-001", "EXP-002", "EXP-003", "EXP-004")
DOCS = ["research/paper/manuscript.md", "research/paper/supplementary.md", "research/publication/review_pass_2.md",
        "research/publication/evidence_audit.md",
        *[f"research/experiments/EXP-00{i}/report.md" for i in range(1, 6)]]
GENERATORS = {
    "analysis": "src/market/frozen_analysis.py (python -m market.frozen_analysis --exp <EXP>)",
    "comparison": "src/market/realdata.py (python -m market.cli realdata compare --exp EXP-005)",
    "arm_summary": "src/market/report.py (python -m market.cli report --exp <EXP>)",
    "run_manifest": "src/market/runner.py (python -m market.cli run --exp <EXP>)",
    "reference": "src/market/realdata.py (python -m market.cli realdata reference)",
    "exploratory": "scripts/m4_exploratory.py",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def g(x, nd=4) -> str:
    if x == 0:
        return "0"
    return f"{x:.{nd}g}"


def frozen_hashes(exp: str) -> tuple[str | None, str | None]:
    e = FREEZE["experiments"].get(exp, {})
    files = FREEZE["files"]
    return files.get(e.get("config")), files.get(e.get("protocol"))


# ----- 1 and 2: integrity and raw checks -----

def check_integrity() -> dict:
    out = {}
    for exp in (*EXPS, "EXP-005"):
        bad, n = [], 0
        for line in (RES / exp / "SHA256SUMS").read_text().splitlines():
            h, rel = line.split("  ", 1)
            n += 1
            if sha(RES / exp / rel) != h:
                bad.append(rel)
        out[exp] = {"files": n, "mismatch": bad}
    return out


def load_runs(exp: str) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((RES / exp / "runs").glob("*.json"))]


def boot_ci(x: np.ndarray) -> tuple[float, float]:
    rng = np.random.Generator(np.random.PCG64(20261124))
    idx = rng.integers(0, len(x), size=(10_000, len(x)))
    m = x[idx].mean(axis=1)
    lo, hi = np.quantile(m, [0.025, 0.975])
    return float(lo), float(hi)


def check_raw() -> dict:
    out = {}
    runs = {exp: load_runs(exp) for exp in EXPS}
    for exp, docs in runs.items():
        rows = list(csv.DictReader((RES / exp / "metrics.csv").open()))
        csv_by = {r["run_id"]: r for r in rows}
        mism = []
        for d in docs:
            r = csv_by.get(d["run_id"])
            if r is None:
                mism.append((d["run_id"], "missing in metrics.csv"))
                continue
            for k, v in d["metrics"].items():
                c = r.get(k)
                if v is None:
                    if c not in ("", None):
                        mism.append((d["run_id"], k))
                elif isinstance(v, bool):
                    if c != str(v):
                        mism.append((d["run_id"], k))
                elif abs(float(c) - float(v)) > 1e-12 * max(1.0, abs(float(v))):
                    mism.append((d["run_id"], k))
        arms = {}
        for d in docs:
            a = arms.setdefault(d["arm"], {"runs": 0, "ok": 0, "seeds": set(), "n_returns": set()})
            a["runs"] += 1
            a["ok"] += d["status"] == "ok"
            a["seeds"].add(d["seed"])
            a["n_returns"].add(d["metrics"].get("n_returns"))
        # arm summary table recomputed from runs
        summ = list(csv.DictReader((RES / exp / "tables" / "arm_summary.csv").open()))
        summ_bad = []
        for s in summ:
            for met in ("vci", "realised_volatility", "mean_spread", "mean_depth_at_best", "volume_per_step", "max_drawdown"):
                vals = np.array([d["metrics"][met] for d in docs if d["arm"] == s["arm"] and d["metrics"][met] is not None])
                if abs(vals.mean() - float(s[f"{met}_mean"])) > 1e-12 * max(1, abs(vals.mean())) or \
                   abs(vals.std(ddof=1) - float(s[f"{met}_sd"])) > 1e-12 * max(1, abs(vals.std(ddof=1))):
                    summ_bad.append((s["arm"], met))
        out[exp] = {"runs": len(docs), "metrics_csv_rows": len(rows), "metric_mismatches": mism[:20], "n_metric_mismatches": len(mism),
                    "arms": {a: {"runs": v["runs"], "ok": v["ok"], "seeds": f"{min(v['seeds'])}..{max(v['seeds'])} ({len(v['seeds'])})",
                                 "n_returns": sorted(x for x in v["n_returns"] if x is not None)} for a, v in sorted(arms.items())},
                    "arm_summary_mismatches": summ_bad}
    # independent recomputation of the primary contrasts
    def by(docs, arm, met):
        return {d["seed"]: d["metrics"][met] for d in docs if d["arm"] == arm and d["status"] == "ok" and d["metrics"][met] is not None}

    prims = {
        "EXP-001 primary A1-A0 vci": (runs["EXP-001"], "A1", runs["EXP-001"], "A0", "vci", ("EXP-001", "primary")),
        "EXP-002 primary low-ZI - high-ZI mean_spread": (runs["EXP-002"], "low-ZI", runs["EXP-002"], "high-ZI", "mean_spread", ("EXP-002", "primary")),
        "EXP-003 primary S-ZI+TF - S-ZI shock_drawdown": (runs["EXP-003"], "S-ZI+TF", runs["EXP-003"], "S-ZI", "shock_drawdown", ("EXP-003", "primary")),
        "EXP-004 placebo A1 - A4 vci": (runs["EXP-001"], "A1", runs["EXP-004"], "A4", "vci", ("EXP-004", "placebo")),
        "EXP-004 tick2": (runs["EXP-004"], "A1-tick2", runs["EXP-004"], "A0-tick2", "vci", ("EXP-004", "tick2")),
    }
    rec = {}
    for name, (dt_, at, dc, ac, met, (exp, key)) in prims.items():
        t, c = by(dt_, at, met), by(dc, ac, met)
        seeds = sorted(set(t) & set(c))
        x = np.array([t[s] - c[s] for s in seeds])
        lo, hi = boot_ci(x)
        ref = json.loads((RES / exp / "analysis.json").read_text())["result"][key]
        rec[name] = {"n_pairs": len(x), "mean": float(x.mean()), "ci": [lo, hi],
                     "matches_analysis_json": bool(len(x) == ref["n_pairs"] and abs(x.mean() - ref["mean_diff"]) < 1e-15 + 1e-12 * abs(ref["mean_diff"])
                                                   and abs(lo - ref["ci95_low"]) < 1e-12 and abs(hi - ref["ci95_high"]) < 1e-12)}
    out["primary_recomputation"] = rec
    # common random numbers check: med-ZI(+TF) of EXP-002 equal EXP-001 A0 (A1)
    e1 = {(d["arm"], d["seed"]): d["metrics"]["vci"] for d in runs["EXP-001"]}
    e2 = {(d["arm"], d["seed"]): d["metrics"]["vci"] for d in runs["EXP-002"]}
    out["crn_check_med_equals_EXP001"] = all(e2[("med-ZI", s)] == e1[("A0", s)] and e2[("med-ZI+TF", s)] == e1[("A1", s)] for s in range(1001, 1031))
    return out


# ----- 3: manifest -----

def leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}/{i}")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield path, obj


def row_metric(obj, path: str) -> str:
    """Best-effort metric description for a JSON path: the enclosing row's labels."""
    parts = path.strip("/").split("/")
    cur, labels = obj, []
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
        if isinstance(cur, dict):
            for k in ("role", "treatment", "control", "metric", "arm", "statistic", "sampling", "contrast"):
                if k in cur and isinstance(cur[k], (str, int)):
                    labels.append(f"{k}={cur[k]}")
    return "; ".join(dict.fromkeys(labels)) + (f"; field={parts[-1]}" if parts else "")


def run_ids_for(exp: str) -> str:
    if exp == "EXP-005":
        return "EXP-001-<arm>-s<seed>, arms A0..A3, seeds 1001..1030 (EXP-005 has no runs of its own)"
    arms = sorted({d["arm"] for d in load_runs(exp)})
    return f"{exp}-<arm>-s<seed>, arms {', '.join(arms)}, seeds 1001..1030"


def build_manifest(rev: str) -> list[dict]:
    ents = []

    def add(exp, kind, path_rel, obj, label="confirmatory", run_ids=None, cfg=None, proto=None, code_rev=None):
        c, p = frozen_hashes(exp) if exp.startswith("EXP") else (None, None)
        for jp, v in leaves(obj):
            ents.append({"exp_id": exp, "label": label, "value": v, "result_path": path_rel, "json_path": jp,
                         "metric": row_metric(obj, jp), "run_ids": run_ids, "generator": GENERATORS[kind],
                         "config_sha256": cfg or c, "protocol_sha256": proto or p, "code_revision": code_rev})

    for exp in EXPS:
        a = json.loads((RES / exp / "analysis.json").read_text())
        man = json.loads((RES / exp / "run_manifest.json").read_text())
        r = man["git"]["revision"]
        rid = run_ids_for(exp)
        add(exp, "analysis", f"results/confirmatory/{exp}/analysis.json", a["result"], run_ids=rid, code_rev=r)
        add(exp, "run_manifest", f"results/confirmatory/{exp}/run_manifest.json", {"wall_time_s": man["wall_time_s"], "workers": man["workers"]},
            run_ids=rid, code_rev=r)
        summ = list(csv.DictReader((RES / exp / "tables" / "arm_summary.csv").open()))
        add(exp, "arm_summary", f"results/confirmatory/{exp}/tables/arm_summary.csv",
            [{"arm": s["arm"], **{k: float(v) for k, v in s.items() if k != "arm" and v not in ("", None)}} for s in summ], run_ids=rid, code_rev=r)
    c5 = json.loads((RES / "EXP-005" / "comparison.json").read_text())
    add("EXP-005", "comparison", "results/confirmatory/EXP-005/comparison.json", c5, run_ids=run_ids_for("EXP-005"),
        code_rev=json.loads((RES / "EXP-001" / "run_manifest.json").read_text())["git"]["revision"])
    ref = json.loads((EXPL / "REAL-REF" / "reference.json").read_text())
    add("EXP-005", "reference", "results/exploratory/REAL-REF/reference.json", ref, label="exploratory (pre-freeze reference fit, J-0004)",
        run_ids="FI-2010 reference blocks (days 1 to 9)")
    for pilot in ("PILOT-MIX", "PILOT-LIQ", "PILOT-SHOCK"):
        for t in ("paired_contrasts", "arm_summary"):
            f = EXPL / pilot / "tables" / f"{t}.csv"
            rows = [{k: (float(v) if k not in ("treatment", "control", "metric", "arm") and v not in ("", None) else v) for k, v in r.items()}
                    for r in csv.DictReader(f.open())]
            add(pilot, "arm_summary", f"results/exploratory/{pilot}/tables/{t}.csv", rows, label="exploratory (pre-freeze pilot, J-0003)",
                run_ids=f"{pilot}-<arm>-s<seed>, development seeds (J-0003)", cfg="pilot configs experiments/configs/pilot-*.json", proto="exploratory, no protocol")
    ex = json.loads((EXPL / "M4-SENS" / "m4_exploratory.json").read_text())
    add("M4-SENS", "exploratory", "results/exploratory/M4-SENS/m4_exploratory.json", {"part1": ex["part1"], "part2": ex["part2"]},
        label="exploratory (M4, J-0011)", run_ids="M4-<arm>-s<seed>, arms A0, A1, A2, A4, S-ZI, S-ZI+TF, development seeds 101..130 (part 1); confirmatory outputs read only (part 2)",
        code_rev=ex["code_revision"], cfg="frozen EXP-001 / EXP-003 parameter values (scripts/m4_exploratory.py ARMS)", proto="exploratory, no protocol")
    for line in (ROOT / "research" / "experiment_journal.jsonl").read_text().splitlines():
        j = json.loads(line)
        for jp, v in leaves(j):
            ents.append({"exp_id": str(j.get("exp_id")), "label": f"journal {j['entry_id']} ({j.get('label')})", "value": v,
                         "result_path": "research/experiment_journal.jsonl", "json_path": f"{j['entry_id']}{jp}", "metric": jp,
                         "run_ids": j.get("seeds"), "generator": "journal record (commands and outputs as logged)",
                         "config_sha256": j.get("config_sha256"), "protocol_sha256": None, "code_revision": j.get("code_revision")})
    for i, e in enumerate(ents):
        e["id"] = f"N-{i + 1:05d}"
    return ents


# ----- 4: number trace -----

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?%?(?![\w])")


def strip_code(text: str) -> str:
    # bibliographic entries (volumes, pages) are checked against literature_review.md, not results
    text = re.split(r"^# References\s*$", text, flags=re.M)[0] if "\n# References" in text else text
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\([^()]*\.(?:svg|md|json|csv)[^()]*\)", " ", text)  # link targets
    text = re.sub(r"\b[0-9a-f]{7,64}\b", " ", text)  # hashes
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}(T[\d:]+Z)?\b", " ", text)  # dates
    text = re.sub(r"\b(?:J|D|C|N|DEV|EXP|PILOT|R|A|S|H|E|F|T)-?\d+\b", " ", text)  # identifiers
    text = re.sub(r"\b(?:doi|arXiv|DOI)[: ]\S+", " ", text)
    # software versions, licence and hash names, years in citations (not results)
    text = re.sub(r"(?:Python|Darwin|numpy|macOS-|CC BY|SHA-|Typst|pandoc|version|v)\s?\d+(?:\.\d+)*", " ", text)
    text = re.sub(r"\b(?:19[5-9]\d|20[0-2]\d)\b", " ", text)
    text = re.sub(r"(?:master prompt|[Ss]ection|sections|plan ch\.)\s+\d+(?:\.\d+)*", " ", text)
    return text


def structural_values() -> set[float]:
    vals = set()
    for p in list((ROOT / "experiments" / "configs").glob("EXP-00*.json")) + [ROOT / "experiments" / "realdata" / "EXP-005.json"]:
        for _, v in leaves(json.loads(p.read_text())):
            vals.add(float(v))
    from_src = [100_000, 10_000, 50, 1, 1_000, 5, 0.2, 10, 2_000, 500, 0.5, 100, 1_000_000, 20, 0.35, 0.1, 200, 0.05, 0.95,
                1001, 1030, 1999, 30, 120, 180, 90, 480, 150, 5_000, 20_000, 50_000, 0.01, 20261124, 9_000, 90_000, 1_800, 37,
                0.53, 0.84, 1.96, 0.025, 0.975, 101, 130, 999, 3_000, 6_000, 250, 49_999]
    vals.update(float(v) for v in from_src)
    return vals


def token_value(tok: str) -> tuple[float, bool]:
    pct = tok.endswith("%")
    t = tok.rstrip("%").rstrip(",").replace(",", "")
    return float(t), pct


# Numbers that are quoted on purpose although they are not evidence values: the audit tolerance and
# a stale value quoted as finding F-5 of research/publication/evidence_audit.md.
QUOTED_NOT_EVIDENCE = {1e-12, 57.2}


def trace(entries: list[dict], extra: set[float] = frozenset()) -> dict:
    printed = set()
    for e in entries:
        v = e["value"]
        if isinstance(v, (int, float)):
            printed.add(f"{float(v):.5f}")
            for nd in (2, 3, 4):
                printed.add(g(float(v), nd))
                printed.add(g(-float(v), nd))
                printed.add(g(100 * float(v), nd))
            if float(v).is_integer():
                printed.add(str(int(v)))
    struct = structural_values() | QUOTED_NOT_EVIDENCE | set(extra)
    res = {}
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            res[rel] = {"missing": True}
            continue
        text = strip_code(p.read_text())
        toks = NUM.findall(text)
        unmatched, n_dec = [], 0
        for tok in toks:
            val, pct = token_value(tok)
            is_dec = "." in tok or "e" in tok
            if not is_dec and abs(val) <= 100:
                continue  # small integers: section numbers, counts, lags (see audit limits)
            if is_dec:
                n_dec += 1
            body = tok.rstrip("%").rstrip(",").replace(",", "")
            if body in printed or body.lstrip("-") in printed or val in struct or (pct and val / 100 in struct):
                continue
            unmatched.append(tok)
        res[rel] = {"tokens": len(toks), "decimal_tokens": n_dec, "unmatched": sorted(set(unmatched))}
    return res


def main() -> int:
    rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    integ = check_integrity()
    raw = check_raw()
    ents = build_manifest(rev)
    manifest = {"schema_version": "1.0.0", "created": "2026-11-25", "generator": "scripts/m4_audit.py", "audited_at_revision": rev,
                "note": "Maps every numeric value in the committed analysis outputs to experiment id, run ids, metric, result path "
                        "(with JSON path), generator, config and protocol SHA-256 and code revision. Documents cite these values at "
                        "the printed precision; the number trace in audit_result.json checks every decimal number of the manuscript, "
                        "the supplement and the experiment reports against this manifest.",
                "figures": [{"id": f"FIG-{exp}-{f.stem}", "path": f"research/experiments/{exp}/figures/{f.name}",
                             "source": f"results/confirmatory/{exp}/figures/{f.name}",
                             "generator": GENERATORS["comparison" if exp == "EXP-005" else "analysis"] if f.stem in ("frozen_contrasts", "placement") else GENERATORS["arm_summary"],
                             "exp_id": exp}
                            for exp in (*EXPS, "EXP-005") for f in sorted((ROOT / "research" / "experiments" / exp / "figures").glob("*.svg"))],
                "artifacts": ents}
    (ROOT / "research" / "publication" / "artifact_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    tr = trace(ents, extra={float(sum(v["files"] for v in integ.values()))})
    out = {"label": "M4 evidence audit", "revision": rev, "integrity": integ, "raw_checks": raw, "manifest_entries": len(ents),
           "number_trace": tr}
    (ROOT / "research" / "publication" / "audit_result.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    ok_int = all(not v["mismatch"] for v in integ.values())
    ok_raw = all(raw[e]["n_metric_mismatches"] == 0 and not raw[e]["arm_summary_mismatches"] for e in EXPS) and \
        all(v["matches_analysis_json"] for v in raw["primary_recomputation"].values()) and raw["crn_check_med_equals_EXP001"]
    unmatched = {k: v.get("unmatched") for k, v in tr.items() if v.get("unmatched") or v.get("missing")}
    print(json.dumps({"integrity_ok": ok_int, "raw_ok": ok_raw, "manifest_entries": len(ents), "unmatched": unmatched}, indent=1))
    return 0 if ok_int and ok_raw else 1


if __name__ == "__main__":
    raise SystemExit(main())
