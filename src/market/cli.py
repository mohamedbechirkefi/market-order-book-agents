# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Command-line interface.

    python -m market.cli smoke   [--out DIR] [--workers N]     exploratory smoke matrix (protocol section 8)
    python -m market.cli run     --exp EXP-001 | --config FILE [--out DIR] [--workers N]
    python -m market.cli report  --results DIR | --exp EXP-002 [--control A0] [--pdf]
    python -m market.cli realdata reference [--write-config]      FI-2010 reference values, days 1..9 (exploratory)
    python -m market.cli realdata compare --exp EXP-005 [--results DIR]   EXP-005 second test (gated)
    python -m market.cli test    [pytest args...]

``run`` refuses a confirmatory config while its protocol is not frozen (G-FREEZE), and
refuses confirmatory seeds (>= 1000) in an exploratory config.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import ConfigError
from .report import build_report
from .runner import (GateError, check_gate, freeze_check, load_experiment, parse_experiment, protocol_status, repo_root,
                     run_experiment, sha256_file)

SMOKE_CONFIG = {
    "exp_id": "SMOKE",
    "label": "exploratory",
    "note": "Protocol section 8 smoke matrix: arms A0 and A1, development seeds 1..5, T = 10,000, B = 1,000.",
    "seeds": {"from": 1, "to": 5},
    "base": {"steps": 10_000, "burn_in": 1_000},
    "arms": {"A0": {"composition": {"ZI": 100}}, "A1": {"composition": {"ZI": 70, "TF": 30}}},
    "series_every": 50,
}


def _print_run(doc: dict) -> None:
    m = doc["metrics"]
    vci = "n/a" if m.get("vci") is None else f"{m['vci']:.4f}"
    print(f"  {doc['run_id']}: {doc['status']} {doc['runtime_s']:.2f}s vci={vci} degenerate={doc['flags']['degenerate']}", flush=True)


def cmd_smoke(args) -> int:
    out = Path(args.out or repo_root() / "results" / "exploratory" / "smoke")
    spec = parse_experiment(SMOKE_CONFIG)
    print(f"EXPLORATORY smoke matrix -> {out}")
    man = run_experiment(spec, out, workers=args.workers, progress=_print_run)
    failed = sum(r["status"] != "ok" for r in man["runs"])
    print(f"runs: {len(man['runs'])}, failed: {failed}, wall time: {man['wall_time_s']:.2f}s")
    rep = build_report(out)
    print(f"summary: {rep['summary']}")
    return 1 if failed else 0


def cmd_run(args) -> int:
    if bool(args.exp) == bool(args.config):
        print("error: give exactly one of --exp or --config", file=sys.stderr)
        return 2
    path = Path(args.config) if args.config else repo_root() / "experiments" / "configs" / f"{args.exp}.json"
    try:
        spec = load_experiment(path)
        check_gate(spec)
        default_out = repo_root() / "results" / ("confirmatory" if spec.label == "confirmatory" else "exploratory") / spec.exp_id
        out = Path(args.out or default_out)
        print(f"{spec.label.upper()} {spec.exp_id}: {len(spec.arms)} arms x {len(spec.seeds)} seeds -> {out}")
        man = run_experiment(spec, out, workers=args.workers, progress=_print_run)
    except GateError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    except (ConfigError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    failed = sum(r["status"] != "ok" for r in man["runs"])
    print(f"runs: {len(man['runs'])}, failed: {failed}, wall time: {man['wall_time_s']:.2f}s")
    return 1 if failed else 0


def cmd_report(args) -> int:
    if bool(args.exp) == bool(args.results):
        print("error: give exactly one of --exp or --results", file=sys.stderr)
        return 2
    exclude: tuple[str, ...] = ()
    results = Path(args.results) if args.results else None
    if args.exp:
        try:
            spec = load_experiment(repo_root() / "experiments" / "configs" / f"{args.exp}.json")
        except (ConfigError, FileNotFoundError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        exclude = spec.excluded_from_contrasts
        results = repo_root() / "results" / ("confirmatory" if spec.label == "confirmatory" else "exploratory") / spec.exp_id
    try:
        rep = build_report(results, control=args.control, pdf=args.pdf, exclude=exclude)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{rep['label']}: {rep['runs']} runs, arms {rep['arms']}, control {rep['control']}")
    print(f"summary: {rep['summary']}")
    if rep["pdf"]:
        print(f"pdf: {rep['pdf']}")
    return 0


REALDATA_CONFIG = Path("experiments") / "realdata" / "EXP-005.json"


def cmd_realdata(args) -> int:
    import json

    from . import realdata as rd

    root = repo_root()
    cfg_path = root / REALDATA_CONFIG
    try:
        cfg = rd.load_config(cfg_path)
    except (rd.RealDataError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    frozen = protocol_status(cfg["exp_id"], cfg["protocol_path"], root)["frozen"]

    def load_split(split: str):
        path = root / cfg[f"{split}_file"]
        want = cfg.get(f"{split}_sha256")
        if not path.exists():
            raise FileNotFoundError(f"{path} missing: run scripts/download_fi2010.py first")
        if want and sha256_file(path) != want:
            raise rd.RealDataError(f"{path.name} does not match its recorded SHA-256")
        return rd.statistics_for_split(rd.load_matrix(path), cfg, split)

    if args.action == "reference":
        if args.write_config and frozen:
            print("REFUSED: EXP-005 is frozen; its reference values cannot be rewritten (G-FREEZE).", file=sys.stderr)
            return 3
        try:
            st = load_split("reference")
        except (rd.RealDataError, FileNotFoundError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        ref = rd.reference_values(st)
        out = Path(args.out or root / "results" / "exploratory" / "REAL-REF")
        out.mkdir(parents=True, exist_ok=True)
        doc = {"label": "exploratory", "split": "reference (days 1..9)", "counts": st["counts"], "reference": ref,
               "per_segment": st["per_segment"]}
        (out / "reference.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"counts": st["counts"], "reference": ref}, indent=2))
        if args.write_config:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            raw["reference"] = ref
            raw["reference_counts"] = st["counts"]
            cfg_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            print(f"reference values written to {REALDATA_CONFIG}")
        return 0

    # compare: the second test, confirmatory, only on the frozen config and confirmatory EXP-001 results
    if not frozen:
        print("REFUSED: EXP-005 protocol is not frozen (G-FREEZE).", file=sys.stderr)
        return 3
    problems = freeze_check(cfg["exp_id"], sha256_file(cfg_path), root)
    if problems:
        print("REFUSED: EXP-005 does not match the freeze record: " + "; ".join(problems), file=sys.stderr)
        return 3
    from .runner import load_results

    sim_dir = Path(args.results or root / "results" / "confirmatory" / cfg["simulated_from"])
    try:
        docs = load_results(sim_dir)
        if {d["label"] for d in docs} != {"confirmatory"} or {d["exp_id"] for d in docs} != {cfg["simulated_from"]}:
            raise rd.RealDataError(f"{sim_dir} must hold confirmatory {cfg['simulated_from']} results only")
        held = load_split("heldout")
    except (rd.RealDataError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    rows = rd.compare_arms(docs, cfg["reference"], cfg["arms"], cfg["bootstrap"]["n_resamples"], cfg["bootstrap"]["seed"])
    check = rd.heldout_check(held, cfg["reference"])
    out = Path(args.out or root / "results" / "confirmatory" / cfg["exp_id"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparison.json").write_text(json.dumps({"label": "confirmatory", "exp_id": cfg["exp_id"],
                                                    "heldout_counts": held["counts"], "heldout_check": check,
                                                    "arms": rows}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"heldout_check": check, "arms": rows}, indent=2))
    return 0


def cmd_test(args) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", *args.pytest_args], cwd=repo_root())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="market", description="MARKET order-book simulation (research project).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("smoke", help="run the exploratory smoke matrix")
    s.add_argument("--out")
    s.add_argument("--workers", type=int, default=1)
    s.set_defaults(func=cmd_smoke)
    r = sub.add_parser("run", help="run an experiment config")
    r.add_argument("--exp")
    r.add_argument("--config")
    r.add_argument("--out")
    r.add_argument("--workers", type=int, default=1)
    r.set_defaults(func=cmd_run)
    rp = sub.add_parser("report", help="build tables, figures and summary from result files")
    rp.add_argument("--results")
    rp.add_argument("--exp")
    rp.add_argument("--control")
    rp.add_argument("--pdf", action="store_true")
    rp.set_defaults(func=cmd_report)
    rd = sub.add_parser("realdata", help="FI-2010 reference values (exploratory) or the EXP-005 comparison (gated)")
    rd.add_argument("action", choices=["reference", "compare"])
    rd.add_argument("--exp", default="EXP-005")
    rd.add_argument("--results")
    rd.add_argument("--out")
    rd.add_argument("--write-config", action="store_true")
    rd.set_defaults(func=cmd_realdata)
    t = sub.add_parser("test", help="run the test suite")
    t.add_argument("pytest_args", nargs=argparse.REMAINDER)
    t.set_defaults(func=cmd_test)
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "test":  # pass every remaining argument to pytest unchanged
        return cmd_test(argparse.Namespace(pytest_args=argv[1:]))
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
