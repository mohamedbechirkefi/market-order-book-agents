# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Command-line interface.

    python -m market.cli smoke   [--out DIR] [--workers N]     exploratory smoke matrix (protocol section 8)
    python -m market.cli run     --exp EXP-001 | --config FILE [--out DIR] [--workers N]
    python -m market.cli report  --results DIR [--control A0] [--pdf]
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
from .runner import GateError, check_gate, load_experiment, parse_experiment, repo_root, run_experiment

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
    try:
        rep = build_report(Path(args.results), control=args.control, pdf=args.pdf)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{rep['label']}: {rep['runs']} runs, arms {rep['arms']}, control {rep['control']}")
    print(f"summary: {rep['summary']}")
    if rep["pdf"]:
        print(f"pdf: {rep['pdf']}")
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
    rp.add_argument("--results", required=True)
    rp.add_argument("--control")
    rp.add_argument("--pdf", action="store_true")
    rp.set_defaults(func=cmd_report)
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
