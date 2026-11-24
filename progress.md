<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Progress journal (append-only)

## 2026-11-24: Session 1, M0 bootstrap and feasibility (plus M1 drafts)

**Milestone:** M0. **Next bounded task:** owner review of the draft protocol; then M2 engine (order book and accounting with tests), which may start before the freeze.

### State found
`git status`: `On branch main, nothing to commit, working tree clean`. One commit `de496af` (master prompt and the owner's licence package). `master_prompt.md` read in full; not modified.

### Decisions
D-001 (owner's licence), D-002 (primary metric and baseline, draft), D-003 (zero-cost toolchain), D-004 (dependency cutoff), D-005 (synthetic data only, draft). See `research/decision_log.md`.

### Commands and actual outputs
- `sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize` -> `Apple M1 Pro`, `10`, `17179869184`
- `sw_vers` -> `macOS 15.3.1 (24D70)`
- `df -h /Users/bechir/research/labs` -> `460Gi 311Gi 128Gi 71%`
- `/usr/local/bin/python3 --version` -> `Python 3.12.1`
- `.tools/py/bin/uv --version` -> `uv 0.9.5 (d5f39331a 2025-10-21)`
- `.tools/py/bin/typst --version` -> `no such file or directory` (typst exists only as the Python package; `importlib.metadata.version('typst')` -> `0.15.0`)
- pypdf / pillow -> `pypdf 6.20.0 pillow 11.3.0`
- `.tools/pandoc --version` -> `pandoc 3.6.3`
- `helix/.tools/node/bin/node --version` -> `v22.23.3` (read-only use)
- `git --version` -> `git version 2.42.1`
- `which pdflatex xelatex lualatex tectonic` -> `not found` (all four)
- `uv lock` (first run, before README existed) -> `Resolved 10 packages in 7ms`; numpy 2.5.4, pytest 9.2.0, hypothesis 6.170.15; latest upload time in lock `2026-11-06T09:54:57.339Z` (before the 2026-11-10 cutoff)
- `uv sync --frozen` (first try) -> failed: `OSError: Readme file does not exist: README.md`; rerun after writing README.md succeeded
- `uv run --frozen pytest -q` -> `2 passed in 2.22s` (import smoke test only; exploratory)
- `pandoc -s manuscript.md -t latex -o manuscript.tex` -> exit 0
- `pandoc -t typst` then `typst.compile` -> failed `font fallback list must not be empty`; with `-V mainfont="Libertinus Serif"` -> 3-page PDF in the session scratchpad, headings extracted by pypdf. PDF not committed (skeleton only). Journal entry J-0001.

### Sources
WebSearch and WebFetch; nine sources opened (abstract or record pages), listed with URLs in `research/literature_review.md`. lobsterdata.com and the Etsin page for FI-2010 did not render. No dataset bytes downloaded.

### Files created or changed
`CLAUDE.md`, `roadmap.md`, `progress.md`, `README.md`, `CITATION.cff`, `pyproject.toml`, `uv.lock`, `CONTRIBUTING.md` (development commands appended), `src/market/__init__.py`, `tests/test_smoke_import.py`, folder READMEs (`results/`, `tests/`, `experiments/`, `demo/`, `articles/`, `research/paper/figures/`), `data/manifest.json`, `research/{protocol,feasibility,literature_review,decision_log,limitations}.md`, `research/claims_register.csv` (header only), `research/experiment_journal.jsonl`, `research/experiment_registry.csv`, `research/experiments/EXP-001..004/protocol.md`, `research/paper/{manuscript.md,manuscript.tex,supplementary.md,references.bib}`, `research/publication/{artifact_manifest.json,claims_audit.md,reproducibility_report.md,author_review.md,release_checklist.md}`.

Not created on purpose (11.1 tree items that would be placeholders): EXP `report.md`, `report.pdf`, `config.json`, `run_manifest.json`, `metrics.csv`, `figures/`, `reproduction.md`; `manuscript.pdf`. They are produced when the experiments run.

### Outstanding risks
Engine throughput unknown (planning target 10 s per 100,000-step run); random-order book may empty on one side; confounding of trend feedback with aggressiveness (placebo arm planned); no TeX (Typst route works on the skeleton).

### Owner decisions needed
1. Approve or amend the primary metric (VCI), baseline (all random-order) and directional H1 (D-002).
2. Approve synthetic-only data (D-005); real-data calibration would need a source with clear rights.
3. Freeze the protocol after M2 throughput measurement (G-FREEZE).
4. Confirm EXP-003 as optional under the five-day budget.

### Next action
M2: implement the order book with price-time priority, partial fills, expiry and accounting, with tests for matching, partial fills, conservation, no negative balances and deterministic ordering; measure throughput on development seeds.
