# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Freeze guard (G-FREEZE): accepts frozen configs, refuses changed ones. No test here launches a run:
``run_experiment`` is replaced by a sentinel wherever the CLI could reach it."""

import hashlib
import json
from pathlib import Path

import pytest

from market import cli
from market.runner import GateError, check_gate, freeze_check, load_experiment, parse_experiment, repo_root

ROOT = repo_root()
CONFIRMATORY = ("EXP-001", "EXP-002", "EXP-003", "EXP-004")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def sentinel(monkeypatch):
    calls = []

    def fake_run(spec, out, workers=1, progress=None):
        calls.append(spec.exp_id)
        return {"runs": [], "wall_time_s": 0.0}
    monkeypatch.setattr(cli, "run_experiment", fake_run)
    return calls


def _mini_repo(tmp_path: Path) -> Path:
    (tmp_path / "research" / "experiments" / "X").mkdir(parents=True)
    (tmp_path / "experiments" / "configs").mkdir(parents=True)
    main = tmp_path / "research" / "protocol.md"
    main.write_text("main protocol\n")
    proto = tmp_path / "research" / "experiments" / "X" / "protocol.md"
    proto.write_text("X protocol\n")
    cfg = tmp_path / "experiments" / "configs" / "X.json"
    cfg.write_text(json.dumps({"exp_id": "X", "label": "confirmatory", "protocol_path": "research/experiments/X/protocol.md",
                               "seeds": [1001], "arms": {"A0": {"steps": 50, "burn_in": 10}}}))
    (tmp_path / "research" / "experiment_registry.csv").write_text(f"exp_id,protocol_hash\nX,{_sha(proto)}\n")
    files = {rel: _sha(tmp_path / rel) for rel in ("research/protocol.md", "research/experiments/X/protocol.md",
                                                   "experiments/configs/X.json")}
    (tmp_path / "research" / "freeze.json").write_text(json.dumps({
        "files": files, "experiments": {"X": {"protocol": "research/experiments/X/protocol.md",
                                              "config": "experiments/configs/X.json"}}}))
    return tmp_path


def _spec(root: Path):
    p = root / "experiments" / "configs" / "X.json"
    return parse_experiment(json.loads(p.read_text()), str(p), _sha(p))


def test_guard_accepts_frozen_and_refuses_changed(tmp_path):
    root = _mini_repo(tmp_path)
    assert check_gate(_spec(root), root)["frozen"] is True
    cfg = root / "experiments" / "configs" / "X.json"
    cfg.write_text(cfg.read_text().replace("1001", "1002"))
    with pytest.raises(GateError, match="differs"):
        check_gate(_spec(root), root)


def test_guard_refuses_changed_main_protocol(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "research" / "protocol.md").write_text("main protocol, edited\n")
    with pytest.raises(GateError, match="protocol.md differs"):
        check_gate(_spec(root), root)


def test_guard_refuses_without_record_or_source(tmp_path):
    root = _mini_repo(tmp_path)
    p = root / "experiments" / "configs" / "X.json"
    unsourced = parse_experiment(json.loads(p.read_text()))  # no file bytes: cannot be matched
    with pytest.raises(GateError):
        check_gate(unsourced, root)
    (root / "research" / "freeze.json").unlink()
    with pytest.raises(GateError, match="no freeze record"):
        check_gate(_spec(root), root)


def test_exploratory_configs_need_no_freeze(tmp_path):
    spec = parse_experiment({"exp_id": "E", "label": "exploratory", "seeds": [1], "arms": {"A0": {}}})
    assert check_gate(spec, tmp_path)["frozen"] is False


@pytest.mark.parametrize("exp_id", CONFIRMATORY)
def test_repository_frozen_configs_pass_the_guard(exp_id):
    spec = load_experiment(ROOT / "experiments" / "configs" / f"{exp_id}.json")
    assert spec.label == "confirmatory"
    status = check_gate(spec)
    assert status["frozen"] is True and freeze_check(exp_id, spec.source_sha256) == []


def test_repository_freeze_record_hashes_match_files():
    rec = json.loads((ROOT / "research" / "freeze.json").read_text())
    for rel, h in rec["files"].items():
        assert _sha(ROOT / rel) == h, rel


@pytest.mark.parametrize("exp_id", CONFIRMATORY)
def test_cli_accepts_frozen_config_without_running(exp_id, sentinel):
    assert cli.main(["run", "--exp", exp_id]) == 0
    assert sentinel == [exp_id]


def test_cli_refuses_edited_frozen_config(tmp_path, sentinel, capsys):
    src = ROOT / "experiments" / "configs" / "EXP-004.json"
    p = tmp_path / "EXP-004.json"
    p.write_text(src.read_text().replace('"pa_skip_prob": 0.0', '"pa_skip_prob": 0.05'))
    assert p.read_text() != src.read_text()
    assert cli.main(["run", "--config", str(p)]) == 3
    assert sentinel == [] and "REFUSED" in capsys.readouterr().err


def test_realdata_compare_refuses_edited_config(tmp_path, monkeypatch, capsys):
    """The EXP-005 comparison is gated on the frozen config bytes."""
    cfg_src = ROOT / cli.REALDATA_CONFIG
    fake_root = tmp_path
    for rel in ("research/protocol.md", "research/experiment_registry.csv", "research/freeze.json",
                "research/experiments/EXP-005/protocol.md", str(cli.REALDATA_CONFIG)):
        (fake_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (fake_root / rel).write_bytes((ROOT / rel).read_bytes())
    edited = json.loads(cfg_src.read_text())
    edited["jump_threshold"] = edited["jump_threshold"] * 2
    (fake_root / cli.REALDATA_CONFIG).write_text(json.dumps(edited, indent=2) + "\n")
    monkeypatch.setattr(cli, "repo_root", lambda: fake_root)
    assert cli.main(["realdata", "compare"]) == 3
    assert "REFUSED" in capsys.readouterr().err


def test_realdata_reference_cannot_rewrite_frozen_config(capsys):
    before = (ROOT / cli.REALDATA_CONFIG).read_bytes()
    assert cli.main(["realdata", "reference", "--write-config"]) == 3
    assert "REFUSED" in capsys.readouterr().err
    assert (ROOT / cli.REALDATA_CONFIG).read_bytes() == before


def test_realdata_config_is_in_the_freeze_record():
    rec = json.loads((ROOT / "research" / "freeze.json").read_text())
    assert rec["experiments"]["EXP-005"]["config"] == str(cli.REALDATA_CONFIG)
    assert freeze_check("EXP-005", _sha(ROOT / cli.REALDATA_CONFIG)) == []
