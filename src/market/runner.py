# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Experiment runner: expands an experiment config into (arm, seed) runs, executes them,
validates every result against the versioned schema and writes a run manifest.

Gate (G-FREEZE): a confirmatory config runs only if its protocol is frozen, meaning the
registry row carries a 64-hex protocol hash equal to the SHA-256 of the protocol file.
Exploratory configs may only use development seeds (< 1000).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import __version__
from .config import ConfigError, SimConfig, canonical_json
from .metrics import compute_metrics
from .schema import RUN_MANIFEST_VERSION, RUN_RESULT_VERSION, dump_json, validate_run_manifest, validate_run_result
from .simulate import simulate

CONFIRMATORY_SEED_MIN = 1000
REQUIRED_METRICS = (
    "vci", "realised_volatility", "excess_kurtosis", "return_acf1", "mean_spread", "mean_depth_at_best",
    "volume_per_step", "max_drawdown", "one_sided_fraction", "rejected_fraction", "n_returns", "n_nonzero_returns",
)


class GateError(RuntimeError):
    """Refusal to run: protocol not frozen, or confirmatory seeds in an exploratory config."""


@dataclass(frozen=True)
class ExperimentSpec:
    exp_id: str
    label: str
    protocol_path: str | None
    seeds: tuple[int, ...]
    arms: dict[str, SimConfig]
    series_every: int  # 0 = no price series saved; else save mid every k steps for the first seed
    source_path: str | None = None
    source_sha256: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _seeds(spec: object) -> tuple[int, ...]:
    if isinstance(spec, dict):
        lo, hi = spec.get("from"), spec.get("to")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (lo, hi)) or lo > hi:
            raise ConfigError("seeds must be {'from': int, 'to': int} with from <= to")
        return tuple(range(lo, hi + 1))
    if isinstance(spec, list) and spec and all(isinstance(v, int) and not isinstance(v, bool) for v in spec):
        if len(set(spec)) != len(spec):
            raise ConfigError("duplicate seeds")
        return tuple(spec)
    raise ConfigError("seeds must be a non-empty list of ints or a {from, to} range")


def parse_experiment(doc: dict, source_path: str | None = None, source_sha256: str | None = None) -> ExperimentSpec:
    if not isinstance(doc, dict):
        raise ConfigError("experiment config must be a JSON object")
    allowed = {"exp_id", "label", "protocol_path", "seeds", "base", "arms", "series_every", "note"}
    unknown = set(doc) - allowed
    if unknown:
        raise ConfigError(f"unknown experiment keys: {sorted(unknown)}")
    for k in ("exp_id", "label", "seeds", "arms"):
        if k not in doc:
            raise ConfigError(f"missing experiment key {k!r}")
    label = doc["label"]
    if label not in ("exploratory", "confirmatory"):
        raise ConfigError("label must be 'exploratory' or 'confirmatory'")
    base = doc.get("base", {})
    if not isinstance(base, dict) or not isinstance(doc["arms"], dict) or not doc["arms"]:
        raise ConfigError("base must be an object and arms a non-empty object")
    arms = {}
    for name, over in doc["arms"].items():
        if not isinstance(over, dict):
            raise ConfigError(f"arm {name} must be an object")
        merged = dict(base)
        merged.update(over)
        arms[name] = SimConfig.from_dict(merged)
    seeds = _seeds(doc["seeds"])
    if label == "exploratory" and any(s >= CONFIRMATORY_SEED_MIN for s in seeds):
        raise GateError("exploratory configs may only use development seeds (< 1000); 1001-1030 are confirmatory")
    if label == "confirmatory" and not doc.get("protocol_path"):
        raise ConfigError("confirmatory configs must name protocol_path")
    series_every = doc.get("series_every", 0)
    if isinstance(series_every, bool) or not isinstance(series_every, int) or series_every < 0:
        raise ConfigError("series_every must be a non-negative int")
    return ExperimentSpec(doc["exp_id"], label, doc.get("protocol_path"), seeds, arms, series_every, source_path, source_sha256)


def load_experiment(path: Path) -> ExperimentSpec:
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    try:
        rel = str(path.resolve().relative_to(repo_root()))
    except ValueError:
        rel = str(path)
    return parse_experiment(doc, rel, sha256_file(path))


def protocol_status(exp_id: str, protocol_path: str | None, root: Path | None = None) -> dict:
    """Frozen iff the registry hash for exp_id is 64 hex chars and equals the protocol file hash."""
    root = root or repo_root()
    if not protocol_path:
        return {"path": None, "sha256": None, "frozen": False}
    p = root / protocol_path
    actual = sha256_file(p) if p.exists() else None
    registered = None
    reg = root / "research" / "experiment_registry.csv"
    if reg.exists():
        with reg.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("exp_id") == exp_id:
                    registered = (row.get("protocol_hash") or "").strip()
    frozen = bool(registered and len(registered) == 64 and all(c in "0123456789abcdef" for c in registered) and registered == actual)
    return {"path": protocol_path, "sha256": actual, "frozen": frozen}


def check_gate(spec: ExperimentSpec, root: Path | None = None) -> dict:
    status = protocol_status(spec.exp_id, spec.protocol_path, root)
    if spec.label == "confirmatory" and not status["frozen"]:
        raise GateError(
            f"{spec.exp_id} is confirmatory but its protocol is not frozen (no matching hash in "
            "research/experiment_registry.csv). Freezing is the owner's decision (G-FREEZE); refusing to run."
        )
    return status


def git_info(root: Path | None = None) -> dict:
    root = root or repo_root()
    try:
        rev = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return {"revision": rev, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}


def environment_info() -> dict:
    cpu = platform.processor() or None
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "market": __version__,
        "os": f"{platform.system()} {platform.release()} ({platform.platform()})",
        "machine": platform.machine(),
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
    }


def _peak_rss_bytes() -> int | None:
    try:
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (OSError, ValueError):
        return None
    return int(r if sys.platform == "darwin" else r * 1024)


def execute_run(exp_id: str, label: str, arm: str, cfg: SimConfig, seed: int, series_every: int = 0) -> tuple[dict, list | None]:
    """Run one (arm, seed) and return (validated result document, optional mid series)."""
    run_id = f"{exp_id}-{arm}-s{seed}"
    t0 = time.perf_counter()
    series = None
    base = {
        "schema": "market.run_result",
        "schema_version": RUN_RESULT_VERSION,
        "label": label,
        "exp_id": exp_id,
        "arm": arm,
        "run_id": run_id,
        "seed": seed,
        "config": cfg.to_dict(),
        "config_hash": cfg.config_hash(),
    }
    try:
        out = simulate(cfg, seed)
        metrics, flags = compute_metrics(out)
        doc = dict(base, status="ok", error=None, metrics=metrics, flags=flags, counts=out.counts,
                   invariants={"checked": out.invariant_checks, "passed": True}, shock=out.shock)
        if series_every:
            series = out.mid[::series_every].tolist()
    except Exception as e:  # recorded, never silently dropped
        doc = dict(base, status="failed", error=f"{type(e).__name__}: {e}",
                   metrics={k: None for k in REQUIRED_METRICS},
                   flags={"one_sided_over_5pct": False, "fewer_than_50_nonzero_returns": False, "vci_undefined": True, "degenerate": False},
                   counts={}, invariants={"checked": 0, "passed": False}, shock=None)
    doc["runtime_s"] = time.perf_counter() - t0
    validate_run_result(json.loads(json.dumps(doc, allow_nan=False)))
    return doc, series


def _worker(args):
    exp_id, label, arm, cfg_dict, seed, series_every = args
    cfg = SimConfig.from_dict(cfg_dict)
    doc, series = execute_run(exp_id, label, arm, cfg, seed, series_every)
    return doc, series, _peak_rss_bytes()


def run_experiment(spec: ExperimentSpec, out_dir: Path, workers: int = 1, root: Path | None = None, progress=None) -> dict:
    """Execute all runs of ``spec`` into ``out_dir``; return the validated manifest."""
    status = check_gate(spec, root)
    out_dir = Path(out_dir)
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)
    jobs = []
    for arm, cfg in spec.arms.items():
        for i, seed in enumerate(spec.seeds):
            jobs.append((spec.exp_id, spec.label, arm, cfg.to_dict(), seed, spec.series_every if i == 0 else 0))
    t0 = time.perf_counter()
    results = []
    if workers <= 1:
        for j in jobs:
            results.append(_worker(j))
            if progress:
                progress(results[-1][0])
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for r in ex.map(_worker, jobs):
                results.append(r)
                if progress:
                    progress(r[0])
    wall = time.perf_counter() - t0
    entries = []
    for doc, series, rss in results:
        rel = Path("runs") / f"{doc['run_id']}.json"
        text = dump_json(doc)
        (out_dir / rel).write_text(text, encoding="utf-8")
        if series is not None:
            (out_dir / "series").mkdir(exist_ok=True)
            (out_dir / "series" / f"{doc['run_id']}.json").write_text(
                json.dumps({"run_id": doc["run_id"], "every": spec.series_every, "mid": series}) + "\n", encoding="utf-8")
        entries.append({
            "run_id": doc["run_id"], "arm": doc["arm"], "seed": doc["seed"], "config_hash": doc["config_hash"],
            "status": doc["status"], "runtime_s": doc["runtime_s"], "peak_rss_bytes": rss,
            "result_path": str(rel), "result_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    manifest = {
        "schema": "market.run_manifest",
        "schema_version": RUN_MANIFEST_VERSION,
        "label": spec.label,
        "exp_id": spec.exp_id,
        "batch_id": f"{spec.exp_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_config_path": spec.source_path,
        "experiment_config_sha256": spec.source_sha256,
        "git": git_info(root),
        "environment": environment_info(),
        "protocol": status,
        "workers": max(1, workers),
        "wall_time_s": wall,
        "runs": entries,
    }
    validate_run_manifest(manifest)
    (out_dir / "run_manifest.json").write_text(dump_json(manifest), encoding="utf-8")
    write_metrics_csv(out_dir, [r[0] for r in results])
    return manifest


def write_metrics_csv(out_dir: Path, docs: list[dict]) -> Path:
    keys: list[str] = []
    for d in docs:
        for k in d["metrics"]:
            if k not in keys:
                keys.append(k)
    flag_keys = ["degenerate", "one_sided_over_5pct", "fewer_than_50_nonzero_returns", "vci_undefined"]
    path = Path(out_dir) / "metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "label", "exp_id", "arm", "seed", "status", "config_hash", "runtime_s"] + keys + flag_keys)
        for d in sorted(docs, key=lambda d: (d["arm"], d["seed"])):
            row = [d["run_id"], d["label"], d["exp_id"], d["arm"], d["seed"], d["status"], d["config_hash"], f"{d['runtime_s']:.4f}"]
            row += ["" if d["metrics"].get(k) is None else d["metrics"][k] for k in keys]
            row += [d["flags"].get(k) for k in flag_keys]
            w.writerow(row)
    return path


def load_results(out_dir: Path) -> list[dict]:
    """Load and validate every run result in ``out_dir/runs``; fail closed on any invalid file."""
    docs = []
    for p in sorted((Path(out_dir) / "runs").glob("*.json")):
        docs.append(validate_run_result(json.loads(p.read_text(encoding="utf-8"))))
    if not docs:
        raise FileNotFoundError(f"no run results under {out_dir}/runs")
    return docs


__all__ = ["ExperimentSpec", "GateError", "check_gate", "execute_run", "load_experiment", "load_results",
           "parse_experiment", "protocol_status", "run_experiment", "canonical_json"]
