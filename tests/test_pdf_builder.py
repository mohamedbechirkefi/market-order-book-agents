# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M6: the PDF builder's title handling and target list (no toolchain needed)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from market.report import TYPST_PREAMBLE, _first_heading

ROOT = Path(__file__).resolve().parents[1]


def test_first_heading_becomes_title_and_is_removed():
    title, body = _first_heading("<!-- SPDX -->\n# EXP-009: a title (report)\n\ntext\n## Sub\n")
    assert title == "EXP-009: a title (report)"
    assert body == "<!-- SPDX -->\n\ntext\n## Sub\n"
    assert _first_heading("no heading\n## level two\n") == (None, "no heading\n## level two\n")


def test_preamble_keeps_tables_readable():
    assert "#show table: set text(size: 8pt)" in TYPST_PREAMBLE
    assert "breakable: true" in TYPST_PREAMBLE


def test_build_targets_cover_manuscript_supplement_and_every_report():
    spec = importlib.util.spec_from_file_location("build_pdfs", ROOT / "scripts" / "build_pdfs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names = [p.relative_to(ROOT).as_posix() for p in mod.targets()]
    reports = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "research" / "experiments").glob("EXP-*/report.md"))
    assert names == ["research/paper/manuscript.md", "research/paper/supplementary.md", *reports]
    assert len(reports) == 5
