# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M6: every relative Markdown link resolves (scripts/check_links.py), and the checker catches breaks."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _checker():
    spec = importlib.util.spec_from_file_location("check_links", ROOT / "scripts" / "check_links.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_repository_links_resolve():
    n, errors = _checker().check(ROOT)
    assert n > 50
    assert errors == []


def test_checker_reports_missing_file_and_anchor(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "b.md").write_text("# Section One\n\ntext\n", encoding="utf-8")
    (tmp_path / "a.md").write_text(
        "[ok](b.md) [ok anchor](b.md#section-one) [url](https://example.org/x)\n"
        "[gone](missing.md) [bad anchor](b.md#nope)\n"
        "```\n[ignored](in-code.md)\n```\n`[ignored](inline.md)`\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.md", "b.md"], cwd=tmp_path, check=True)
    n, errors = _checker().check(tmp_path)
    assert n == 4
    assert len(errors) == 2
    assert any("missing target missing.md" in e for e in errors)
    assert any("missing anchor b.md#nope" in e for e in errors)


def test_slug_matches_github_rule():
    assert _checker().slug("5.1 EXP-001: agent mixtures") == "51-exp-001-agent-mixtures"
