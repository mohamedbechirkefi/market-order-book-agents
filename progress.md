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

## 2026-11-24: Session 2, M2 core implementation (protocol not frozen)

**Milestone:** M2. **Next bounded task:** the owner reviews D-006 and the D-007 amendment proposals and decides on the freeze (G-FREEZE); M3 confirmatory runs only after that.

### State found
`git status`: clean on `main` at `10b0e8b`. Control files read in the order of the session brief. The `.venv` had been created under the repository's former name (`market-research`): `uv sync --frozen` swapped the editable install, and `uv run pytest` failed with `ModuleNotFoundError: No module named 'market'` because the console scripts carried the old interpreter path. Fixed with `uv sync --frozen --reinstall` (no file deleted; `uv.lock` unchanged).

### Implemented (src/market/)
- `config.py`: immutable, validated `SimConfig` and `Composition`; canonical-JSON SHA-256 config hash.
- `book.py`: limit-order book, price-time priority, partial fills, marketable limits, market-order remainder cancelled, cash-capped market buys, lazy cancellation, structural invariant check.
- `ledger.py`: integer cash and inventory with reservations; settlement; conservation and reservation invariants.
- `rng.py`: six named streams from one `SeedSequence` (common random numbers).
- `agents.py`: ZI, TF, MR and placebo-aggressive rules as pure functions with a fixed number of draws per activation.
- `simulate.py`: event-time loop (expiry, optional shock, one activation, record), invariants checked at the end of every run and optionally every k steps.
- `metrics.py`: protocol section 5 metrics plus `vci_dt10`, `vci_dt200` and the EXP-003 shock metrics; undefined values are `null`, never 0.
- `analysis.py`: paired differences, d_z, percentile bootstrap, Holm, planning seed count.
- `schema.py` and `schemas/`: JSON schemas `market.run_result` 1.0.0 and `market.run_manifest` 1.0.0 with a validator; validated at export and at import (fail closed).
- `runner.py`: experiment configs, freeze gate (registry hash must equal the protocol file hash), development-seed rule for exploratory configs, parallel execution, per-run result files, run manifest (git revision and dirty flag, Python, numpy, OS, CPU, runtime, peak RSS, result SHA-256), `metrics.csv`.
- `report.py`: CSV tables, SVG figures, `summary.md`, PDF through pandoc to Typst with `-V mainfont="Libertinus Serif"`.
- `cli.py`: `smoke`, `run`, `report`, `test`.
- `reference.py`: naive matcher for differential tests.
- `experiments/configs/`: EXP-001..004 (confirmatory, refused while unfrozen) and three exploratory pilot configs.

Decisions: D-006 (implementation choices), D-007 (proposed amendments, not applied), D-008 (SVG figures, no plotting dependency).

### Commands and actual outputs
- `uv run --frozen pytest -q` -> `110 passed in 6.59s` (after the reinstall); `uv run --frozen python -m market.cli test -q` -> `110 passed in 9.43s`. 0 failed.
- `python -m market.cli run --exp EXP-001` -> `REFUSED: EXP-001 is confirmatory but its protocol is not frozen ...`, exit 3; same for EXP-002. No `results/confirmatory/` folder was created.
- `python -m market.cli smoke` -> `runs: 10, failed: 0, wall time: 1.62s` (J-0002).
- `python -m market.cli run --config experiments/configs/pilot-mixtures.json --workers 8` -> `runs: 140, failed: 0, wall time: 39.37s`; `pilot-liquidity.json` -> `runs: 60, failed: 0, wall time: 17.93s`; `pilot-shock.json` -> `runs: 30, failed: 0, wall time: 7.23s` (J-0003). `uptime` at the start of the batch: load averages 75.78 35.46 16.45 (shared machine).
- `python -m market.cli report --results results/exploratory/<dir> --pdf` -> four `summary.pdf` files; pypdf reads 4 pages for PILOT-MIX with text and figure labels extracted. Not visually inspected: no PDF rasteriser is installed.
- Uncontended serial timing before the first commit: 0.64 to 0.68 s per full-length run (4 arms, seed 1).

### Exploratory measurements (J-0003; development seeds; not findings)
- Runtime per full-length run: 0.64 to 0.68 s uncontended serial; mean 2.19 s (1.67 to 3.30) per run inside 8 workers on the loaded machine.
- Projected full matrix (480 runs): about 2.3 min wall on 8 workers at the loaded rate; the 10 s per run planning target is met with a wide margin.
- Seed spread: SD of VCI over 20 seeds 0.012 (A0) to 0.048 (A1); SD of the paired A1 minus A0 VCI difference 0.051. Thirty seeds detect about d_z 0.53, about 0.027 VCI units.
- Degenerate cells: EXP-002 low-liquidity ZI+TF flagged in 10 of 10 seeds (one-sided fraction about 0.19, mid at the price floor); no other arm flagged. EXP-003: recovery censored in 2 of 30 runs.
- TF skip fraction: 0.45% in A1 (placebo activity matching not triggered), 21% at tick 2.
- Determinism: the pilot was run more than once with unchanged engine code; per-arm metric spreads were identical.

### Failures and fixes
- First pilot batch recorded `git.dirty = true` because untracked result files counted; fixed in `6e3ea17` (`--untracked-files=no`); the batch was deleted and rerun on the clean revision.
- `market.cli test -q` failed with `unrecognized arguments: -q`; fixed by passing everything after `test` to pytest unchanged. The `run` command now checks the gate before printing the output folder.

### Files created or changed
`src/market/*` (13 modules, 2 schemas), `tests/test_*.py` (7 new files), `experiments/configs/*.json` (7), `results/exploratory/{smoke,PILOT-MIX,PILOT-LIQ,PILOT-SHOCK}/`, `README.md`, `CLAUDE.md` (CLI line), `CONTRIBUTING.md` (CLI commands), `roadmap.md`, `research/{decision_log.md,experiment_journal.jsonl,experiment_registry.csv,limitations.md,protocol.md}` (protocol: section 11 heading and a section 12 pointer to D-006 and D-007 only), `data/manifest.json`, folder READMEs.

### Not done, and why
- No confirmatory run, no protocol hash: the freeze is the owner's (G-FREEZE).
- No per-experiment `report.md`, `config.json` or `run_manifest.json` under `research/experiments/EXP-NNN/`: they are written when confirmatory runs exist (M3). Exploratory summaries live in `results/exploratory/`.
- No demo UI (M5).

### Owner decisions needed
1. D-006 implementation choices and D-007 amendments (budget, seed count, the degenerate low-liquidity cell, placebo matching, folding D-006 into protocol section 3).
2. Then freeze the protocol and record its hash in the registry; the runner will then accept `run --exp`.

## 2026-11-24: Session 3, real data (FI-2010), round-2 amendments and freeze (M1 gate)

**Milestone:** M1 (freeze). **Next bounded task:** M3 confirmatory runs when the coordinator schedules them (quiet machine); EXP-005 needs `scripts/download_fi2010.py` run locally first.

### State found
`git status`: clean on `main` at `c1369b2`. Authority: `labs/_shared/owner-approvals-2026-11-24b.md` sections 1 and 7 ("Approve all", "yes for all others") and the DATA-FREEZE and FREEZE briefs.

### Licence check and download
- Fairdata Metax record (opened 2026-11-24): CC BY 4.0, access "Open", one file `BenchmarkDatasets.zip`, 1,864,361,899 bytes, SHA-256 `cea93692...f664`. Licence matches the approvals file. The Etsin `/api/v3/download/authorize` endpoint gave an open download URL (no account).
- `python3 -I scripts/download_fi2010.py` -> exit 0 after about 52 min; archive SHA-256 and size equal to the record; extracted `Train_Dst_NoAuction_DecPre_CF_9.txt` (863,961,898 bytes, `f46b3dd6...a02a`) and `Test_Dst_NoAuction_DecPre_CF_9.txt` (76,138,106 bytes, `c09785b0...aca0`); archive deleted; `data/raw/` git-ignored.

### Structural inspection and reference fit (J-0004, exploratory)
- Reference file: 362,400 columns, 0 missing, 0 non-positive, 0 crossed; four jumps above 0.2 and none between 0.035 and 0.26, so the files are ordered by stock and stock-days cannot be located. The R1 method was revised before fitting: 5 stock segments (J = 0.1), 9,000-column blocks (37 blocks; remainders 856, 8,807, 3,176, 8,784, 7,777 columns dropped). Held-out file: 31,937 columns, 5 segments (counts only).
- `python -m market.cli realdata reference --write-config` -> exit 0. Reference medians (min..max over 37 blocks), h = 5: VCI 0.0481 (0.0004..0.1680); realised volatility 0.000500 (0.000235..0.001041); mean relative spread 0.001675 (0.001098..0.002340). Written to `experiments/realdata/EXP-005.json`.

### Amendments and code
A1 to A5, R1, R2 applied (protocol section 12; D-009, D-010). Code: `market.realdata`, `realdata` CLI, `report --exp`, `excluded_from_contrasts`, comparison metrics, freeze guard against `research/freeze.json`. The two M2 tests that called `run --exp EXP-001` expecting a refusal were rewritten: after the freeze they would have launched a confirmatory run.

### Tests
- `../.tools/py/bin/uv sync --frozen --all-groups --all-extras` -> `Audited 9 packages`.
- `.venv/bin/python -m pytest` before the freeze record: 142 passed, 10 failed (the 10 tests that require `research/freeze.json`, as expected); after: **154 passed, 0 failed**.
- Guard check by hand: `check_gate` accepts EXP-001..004 as committed; an EXP-001 copy with seeds to 1031 -> refused ("the loaded config differs from the frozen config"); `realdata reference --write-config` -> refused, exit 3. No `results/confirmatory/` folder exists.

### Freeze
`research/freeze.json`: owner quotes, C1 to C4 with C4 disclosure, amendments, SHA-256 of the main protocol (`a5e3663b...3754`), the five EXP protocols and five configs at revision `d467595`, data manifest hash. Registry statuses "frozen (owner-approved 2026-11-24), not yet run". D-011.

### Not done
No confirmatory run, no push, no paid service. The held-out day 10 statistics and every simulated-versus-real placement are left to M3.

## 2026-11-24: Session 4, round-3 ratification (FI-2010 block method)

**Milestone:** M1 (records only). **Next bounded task:** M3 confirmatory runs when the coordinator schedules them.

### State found
`git status`: clean on `main` at `09ddbd3`. Authority: `labs/_shared/owner-approvals-2026-11-24c.md` section 4 (MARKET row, "Approve all", round 3) and the ROUND3 and FREEZE briefs.

### Done
- D-012 in `research/decision_log.md`: the FI-2010 block method (5 stocks, 37 blocks of 9,000 columns, R1, J-0004) ratified, quoting the owner.
- `research/freeze.json`: new `ratifications` list with the item, quote, source and date. The frozen files are unchanged (the frozen R1 text already holds this method), so every recorded hash still matches.

### Tests
- `../.tools/py/bin/uv sync --frozen --all-groups --all-extras` -> `Audited 9 packages`.
- `.venv/bin/python -m pytest -q` -> **154 passed, 0 failed** (includes the guard tests: frozen configs accepted, edited config refused, freeze-record hashes match the files).

### Not done
No confirmatory run, no computation on FI-2010, no push.
