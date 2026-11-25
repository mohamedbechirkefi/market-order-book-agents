# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M5 consistency (master prompt 11.6): the demo's published numbers are the manuscript's.

1. Re-running the export in memory reproduces the committed demo/public/data/results.json byte for byte.
2. Every ``display`` and ``interval_display`` string in it appears verbatim in research/paper/manuscript.md.
   There is no documented exception: the export prints only values the manuscript prints.
3. The same holds for the public texts: every result number quoted in README.md, the articles and
   demo/README.md is one of the exported display strings.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "public" / "data" / "results.json"
MANUSCRIPT = (ROOT / "research" / "paper" / "manuscript.md").read_text(encoding="utf-8")
EXCEPTIONS: dict[str, str] = {}  # display text -> documented reason; empty by design


def _export():
    spec = importlib.util.spec_from_file_location("export_demo_data", ROOT / "scripts" / "export_demo_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _displays(o, acc):
    if isinstance(o, dict):
        for k in ("display", "interval_display"):
            if o.get(k) is not None:
                acc.append(o[k])
        for v in o.values():
            _displays(v, acc)
    elif isinstance(o, list):
        for v in o:
            _displays(v, acc)
    return acc


def test_committed_results_json_matches_a_fresh_export():
    mod = _export()
    assert OUT.read_text(encoding="utf-8") == mod.render(mod.build())


def test_every_display_string_is_printed_in_the_manuscript():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    shown = _displays(doc, [])
    assert len(shown) > 40
    missing = [s for s in shown if s not in MANUSCRIPT and s not in EXCEPTIONS]
    assert missing == []


def test_export_has_every_registered_experiment_and_the_frozen_verdict():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    ids = [e["id"] for e in doc["experiments"]]
    reg = [line.split(",")[0] for line in (ROOT / "research" / "experiment_registry.csv").read_text().splitlines()[1:] if line]
    assert ids == reg
    assert doc["headline"]["frozen_verdict"] == "invalidated"
    assert doc["experiments"][0]["verdict"].startswith("invalidated")
    assert any(n["status"] == "not measured" and "spread widening" in n["outcome"] for n in doc["not_measured"])
    assert not re.search(r"20\d\d-\d\d-\d\dT\d\d:", OUT.read_text())  # no timestamps


NUM = re.compile(r"(?<![\w.\-])-?\d+\.\d+(?![\w.])")


def test_public_texts_quote_only_exported_numbers():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    allowed = set()
    for s in _displays(doc, []):
        allowed.update(NUM.findall(s))
    for rel in ("README.md", "articles/medium.md", "articles/linkedin.md", "demo/README.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for n in NUM.findall(text):
            assert n in allowed or n in MANUSCRIPT, f"{rel}: {n} is not a published number"
