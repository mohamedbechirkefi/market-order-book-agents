# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Tests of the M4 helper scripts (exploratory checks, table filler, evidence audit)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_window_drawdown_matches_shock_metric_formula():
    from market.metrics import shock_metrics
    from market.simulate import SimOutput
    from market.config import SimConfig

    ex = _load("m4_exploratory")
    mid = np.full(60, 100.0)
    mid[30:40] = 95.0  # a 5% dip right after the reference step 29
    out = SimOutput(config=SimConfig(), seed=0, best_bid=np.zeros(60, dtype=np.int64), best_ask=np.zeros(60, dtype=np.int64),
                    mid=mid, depth_best=np.zeros(60, dtype=np.int64), volume=np.zeros(60, dtype=np.int64), agent_types=[],
                    shock={"step": 30, "pre_shock_mid": float(mid[29]), "bid_depth": 1, "qty": 1, "filled": 1})
    expected = shock_metrics(out, window=20)["shock_drawdown"]
    assert abs(ex.window_drawdown(mid, t0=30, window=20) - expected) < 1e-15
    assert abs(expected - 0.05) < 1e-12
    assert ex.window_drawdown(np.full(60, 100.0), t0=30, window=20) == 0.0


def test_table_filler_replaces_only_marked_blocks(tmp_path):
    tb = _load("m4_tables")
    f = tmp_path / "doc.md"
    f.write_text("before\n<!-- BEGIN TABLE holm_conservative (x) -->\nstale\n<!-- END TABLE holm_conservative -->\nafter\n")
    assert tb.fill(f) == ["holm_conservative"]
    first = f.read_text()
    assert first.startswith("before\n") and first.endswith("after\n") and "stale" not in first
    tb.fill(f)
    assert f.read_text() == first  # idempotent


def test_audit_number_trace_helpers():
    au = _load("m4_audit")
    text = au.strip_code("value 0.02545 in `code 9.99` with hash 3edbb40f and date 2026-11-25, J-0011, Python 3.12.1")
    toks = au.NUM.findall(text)
    assert "0.02545" in toks and "9.99" not in toks and "3.12" not in toks
    assert au.token_value("1,632%") == (1632.0, True)
    assert au.g(0.0254504547, 4) == "0.02545"
