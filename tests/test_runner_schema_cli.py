# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Integration: config -> runs -> validated results -> manifest -> report; gates; schema failures."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from market import cli
from market.config import ConfigError, SimConfig
from market.report import build_report
from market.runner import (GateError, check_gate, execute_run, load_experiment, load_results, parse_experiment,
                           protocol_status, repo_root, run_experiment)
from market.schema import SchemaError, validate_run_manifest, validate_run_result

TINY = {
    "exp_id": "TEST", "label": "exploratory", "seeds": [1, 2, 3],
    "base": {"steps": 1_500, "burn_in": 200, "lookback": 30, "order_lifetime": 150, "sample_interval": 10},
    "arms": {"A0": {"composition": {"ZI": 20}}, "A1": {"composition": {"ZI": 14, "TF": 6}}},
    "series_every": 50,
}


def test_end_to_end_run_and_report(tmp_path):
    man = run_experiment(parse_experiment(TINY), tmp_path, workers=1)
    assert len(man["runs"]) == 6 and all(r["status"] == "ok" for r in man["runs"])
    validate_run_manifest(json.loads((tmp_path / "run_manifest.json").read_text()))
    for r in man["runs"]:
        text = (tmp_path / r["result_path"]).read_text()
        assert hashlib.sha256(text.encode()).hexdigest() == r["result_sha256"]
    docs = load_results(tmp_path)
    assert {d["label"] for d in docs} == {"exploratory"}
    rep = build_report(tmp_path, n_resamples=500)
    assert rep["label"] == "exploratory" and rep["control"] == "A0"
    summary = (tmp_path / "summary.md").read_text()
    assert "EXPLORATORY" in summary
    for f in ("vci_by_arm.svg", "vci_paired_diff.svg", "mid_paths.svg", "runtime_by_arm.svg"):
        assert (tmp_path / "figures" / f).read_text().startswith("<svg")
    assert (tmp_path / "tables" / "paired_contrasts.csv").exists()
    assert (tmp_path / "metrics.csv").read_text().count("\n") == 7


def test_parallel_equals_serial(tmp_path):
    a = run_experiment(parse_experiment(TINY), tmp_path / "a", workers=1)
    b = run_experiment(parse_experiment(TINY), tmp_path / "b", workers=2)
    ma = {d["run_id"]: d["metrics"] for d in load_results(tmp_path / "a")}
    mb = {d["run_id"]: d["metrics"] for d in load_results(tmp_path / "b")}
    assert ma == mb and len(a["runs"]) == len(b["runs"])


def test_confirmatory_config_refused_while_unfrozen():
    spec = load_experiment(repo_root() / "experiments" / "configs" / "EXP-001.json")
    assert spec.label == "confirmatory" and spec.seeds[0] == 1001
    with pytest.raises(GateError):
        check_gate(spec)


def test_cli_run_refuses_confirmatory(capsys):
    assert cli.main(["run", "--exp", "EXP-001"]) == 3
    assert "REFUSED" in capsys.readouterr().err


def test_exploratory_config_cannot_use_confirmatory_seeds():
    bad = dict(TINY, seeds={"from": 1000, "to": 1002})
    with pytest.raises(GateError):
        parse_experiment(bad)


def test_freeze_detection_requires_matching_hash(tmp_path):
    proto = tmp_path / "p.md"
    proto.write_text("protocol text\n")
    h = hashlib.sha256(proto.read_bytes()).hexdigest()
    reg = tmp_path / "research"
    reg.mkdir()
    (reg / "experiment_registry.csv").write_text(f"exp_id,protocol_hash\nX,{h}\nY,none (not frozen)\n")
    assert protocol_status("X", "p.md", tmp_path)["frozen"] is True
    assert protocol_status("Y", "p.md", tmp_path)["frozen"] is False
    proto.write_text("edited after freeze\n")
    assert protocol_status("X", "p.md", tmp_path)["frozen"] is False


def test_all_shipped_configs_parse():
    for p in sorted((repo_root() / "experiments" / "configs").glob("*.json")):
        spec = load_experiment(p)
        assert spec.arms


@pytest.mark.parametrize("mutate", [
    lambda d: d.pop("metrics"),
    lambda d: d.__setitem__("label", "final"),
    lambda d: d.__setitem__("seed", -1),
    lambda d: d.__setitem__("config_hash", "xyz"),
    lambda d: d["metrics"].__setitem__("vci", "0.3"),
    lambda d: d.__setitem__("unexpected", 1),
    lambda d: d["invariants"].__setitem__("passed", False),
    lambda d: d["metrics"].__setitem__("vci", float("nan")),
])
def test_malformed_results_fail_closed(mutate):
    doc, _ = execute_run("T", "exploratory", "A0", SimConfig(**TINY["base"]), 1)
    validate_run_result(doc)
    bad = copy.deepcopy(doc)
    mutate(bad)
    with pytest.raises(SchemaError):
        validate_run_result(bad)


def test_load_results_rejects_tampered_file(tmp_path):
    run_experiment(parse_experiment(dict(TINY, seeds=[1])), tmp_path)
    p = next((tmp_path / "runs").glob("*.json"))
    d = json.loads(p.read_text())
    del d["flags"]
    p.write_text(json.dumps(d))
    with pytest.raises(SchemaError):
        load_results(tmp_path)


def test_failed_run_is_recorded_not_dropped(monkeypatch):
    import market.runner as r

    def boom(cfg, seed):
        raise RuntimeError("injected")
    monkeypatch.setattr(r, "simulate", boom)
    doc, _ = r.execute_run("T", "exploratory", "A0", SimConfig(**TINY["base"]), 1)
    assert doc["status"] == "failed" and "injected" in doc["error"]


@pytest.mark.parametrize("doc", [
    {"exp_id": "X", "label": "maybe", "seeds": [1], "arms": {"A": {}}},
    {"exp_id": "X", "label": "exploratory", "seeds": [], "arms": {"A": {}}},
    {"exp_id": "X", "label": "exploratory", "seeds": [1, 1], "arms": {"A": {}}},
    {"exp_id": "X", "label": "exploratory", "seeds": [1], "arms": {"A": {"bogus": 1}}},
    {"exp_id": "X", "label": "confirmatory", "seeds": [1001], "arms": {"A": {}}},
    {"exp_id": "X", "label": "exploratory", "seeds": [1], "arms": {}},
])
def test_invalid_experiment_configs(doc):
    with pytest.raises(ConfigError):
        parse_experiment(doc)


def test_report_on_missing_results_fails(tmp_path, capsys):
    assert cli.main(["report", "--results", str(tmp_path)]) == 2
