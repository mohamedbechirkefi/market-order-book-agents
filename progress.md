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

## 2026-11-25: Session 5, M3 confirmatory experiments

**Milestone:** M3 (done). **Next bounded task:** M4 interpretation, after the owner reviews D-013 (analysis choices) and D-014 (observations).

### State found
`git status`: clean on `main` at `a204657`. Authority: the owner's "Start next" (2026-11-25) and the coordinator's M3 brief.

### Pre-run checks (J-0005, exploratory)
- All 11 frozen files and `data/manifest.json` match `research/freeze.json`; both FI-2010 files match their SHA-256.
- `../.tools/py/bin/uv sync --frozen --all-groups --all-extras` -> `Audited 9 packages`; `market` imported from this repository's `src/`.
- `.venv/bin/python -m pytest` -> **154 passed, 0 failed**.
- `market.cli smoke --out results/exploratory/smoke-M3 --workers 2` (seeds 1..5) -> 10 runs, 0 failed, 0.41 s; contrasts identical to J-0002.
- `scripts/validate_metrics.py` -> 13 of 13 known-case checks PASS.
- `market.frozen_analysis` and its tests written before any confirmatory output (D-013); suite -> **163 passed**. Committed as `26266f2` (the provenance revision).

### Confirmatory runs (revision 26266f2, `--workers 2`, `nice -n 10`)
| EXP | Runs | Failed | Wall time | Headline (95% bootstrap CI) | Verdict |
| --- | --- | --- | --- | --- | --- |
| EXP-001 | 120 | 0 | 111.3 s | VCI A1 - A0 = -0.00783 [-0.0268, 0.0179] | inconclusive |
| EXP-002 | 180 | 0 | 148.9 s | spread low-ZI - high-ZI = 1.632 [1.624, 1.641] | supported; low-ZI+TF degenerate 30/30 (excluded) |
| EXP-003 | 90 | 0 | 73.3 s | shock drawdown S-ZI+TF - S-ZI = 0.0255 [0.0198, 0.0315] | supported |
| EXP-004 | 90 | 0 | 68.8 s | placebo A1 - A4 = -0.0253 [-0.0441, -0.0003]; dt 10 +0.0248 [0.0153, 0.0384], dt 200 +0.0915 [0.0429, 0.149] | robustness rule: invalidated (sign reversal) |
| EXP-005 | 0 | 0 | about 1 s | held-out VCI > 0 in 4 of 5 stocks | (a) not supported; (b) descriptive |

Values from `results/confirmatory/EXP-00N/analysis.json` and `EXP-005/comparison.json`. Machine shared (load average up to about 84).

### Records
Reports `research/experiments/EXP-00N/report.md` (with `config.json`, `run_manifest.json`, `metrics.csv`, `figures/`, `reproduction.md`) generated by `scripts/write_m3_reports.py` from the raw outputs; `provenance.csv` and `SHA256SUMS` per experiment; registry statuses; journal J-0006 to J-0010; claims C-001 to C-012; limitations; D-014.

### Tests at the end
`.venv/bin/python -m pytest -q` -> **163 passed, 0 failed**.

### Not done
No push. No manuscript synthesis (M4). EXP-003 spread widening not measured (no defined metric). Exploratory sensitivities named in the protocols (tau halved, 25% shock) not run.

## 2026-11-25: Session 6, M3 close (owner decisions)

**Milestone:** M3 (closed). **Next bounded task:** M4 interpretation, starting with the owner's review of the D-013 analysis choices.

- Authority: owner, 2026-11-25, "approve all recommendations, RIGGED A" (`labs/_shared/owner-approvals-2026-11-25.md`, sections 4 and 8) and the M3-close brief.
- Recorded: D-015 (Holm ties disclosed and not changed; EXP-004 reported exactly as the frozen rule gives it, with the near-zero primary noted; EXP-003 spread widening reported as not measured; D-013 reviewed in M4). `research/freeze.json` gains a `deviations` list (DEV-1 to DEV-4; no frozen file or hash changed). Limitations and claims C-003, C-004, C-007 and C-009 updated.
- Reports: all five `report.md` and `reproduction.md` already existed; the EXP-001 to EXP-004 reports were amended to cite the owner's decisions. No number changed and nothing was recomputed. `scripts/write_m3_reports.py` carries the same text: regenerating it in a scratch copy of the repository gives byte-identical reports and results.
- **M3 status: done.** The gate holds: complete planned matrix (480/480 runs, 0 failed, none dropped), EXP-005 comparison, and a report for every registered experiment.
- Tests: `.venv/bin/python -m pytest -q` -> **163 passed, 0 failed**.

## 2026-11-25: Session 7, M4 interpretation

**Milestone:** M4 (done). **Next bounded task:** owner review of D-016 (in particular the EXP-004 sign-reference reading), then M5.

### State found
`git status`: clean on `main` at `49010ed`. Authority: owner, 2026-11-25, "Approve all recommendations, push then next" (`labs/_shared/owner-approvals-2026-11-25b.md`, section 5) and the coordinator's M4 brief. No MARKET-specific follow-up in that file.

### Done
- **Confounders and sensitivity.** Competing explanations of every protocol mapped to the results that address them (manuscript Table 10). Exploratory checks `scripts/m4_exploratory.py` (J-0011): 180 runs on development seeds 101..130, two workers, `nice -n 10`; final execution 01:30:58Z to 01:31:57Z, wall 58.4 s, 0 failed (executed three times; the second added E6, the third the signed-return autocorrelation per `dt` after review pass R2-1). Output `results/exploratory/M4-SENS/`. Main results: VCI A1 - A0 over `dt` 5..500 reproduces the confirmatory sign pattern; A1 signed-return lag-1 autocorrelation 0.653 at `dt` 200 and 0.8921 at 500 (trend runs); EXP-003 difference-in-differences 0.01616 [0.009609, 0.02483]; conservative Holm ties change no interval's relation to 0; EXP-004 rule with the H1 sign reads "qualified". No frozen verdict changed.
- **Expected versus observed:** manuscript Table 1 (generated).
- **Claims register:** columns result id, config SHA-256, figure or table, manuscript section added; C-013 to C-021 and X-001 to X-008 added; C-005 qualified (29 rows).
- **Evidence audit** (`scripts/m4_audit.py`, J-0012): `research/publication/artifact_manifest.json` (6,489 entries), `audit_result.json`, `evidence_audit.md` (findings F-1 to F-7), `claims_audit.md`. 550 checksummed files, 0 mismatches; per-run JSON against `metrics.csv` 0 mismatches; primaries recomputed independently and identical; number trace 0 unmatched.
- **Reports:** role column in non-Holm contrast tables (F-1) and labelled exploratory M4 notes in EXP-001, EXP-003, EXP-004, via `scripts/write_m3_reports.py`; no number changed.
- **Manuscript and supplement:** `research/paper/manuscript.md` (section 11.4 structure; tables by `scripts/m4_tables.py`; figures in `research/paper/figures/`), `supplementary.md`, `references.bib` (Ntakaris2018 added), `manuscript.tex` regenerated with pandoc 3.6.3 (not compiled; no PDF made in M4).
- **Second review pass:** `research/publication/review_pass_2.md` (R2-1 to R2-8; seven of eight challenges held in full or in part) and the resulting manuscript revisions listed there.
- **Records:** limitations (M4 section), D-016, J-0011, J-0012, literature review section 5 (sources re-opened 2026-11-25), roadmap.

### Tests
- `/Users/bechir/research/labs/.tools/py/bin/uv sync --frozen --all-groups --all-extras` -> `Audited 9 packages`.
- `.venv/bin/python -m pytest -q` -> **166 passed** (163 plus 3 in `tests/test_m4_scripts.py`).

### M4 gate
Holds: every numerical claim maps to a result id, config and table or figure (claims register, artifact manifest, number trace 0 unmatched); every external claim maps to an opened source, abstract-only sources marked.

### Not done
No push. No PDF (M6). Protocol sensitivities never run: order lifetime halved (EXP-002), 25% shock (EXP-003). No systematic literature search on placebo controls.

## 2026-11-25: Session 8, post-M4 owner decisions (items 2 and 4)

**Milestone:** M4 (done); M5 not started. **Next bounded task:** M5, after the owner fills the placeholders below.

- Authority: owner, 2026-11-25, "Approve all" (post-M4) (`labs/_shared/owner-approvals-2026-11-25c.md`, items 2 and 4) and the coordinator's post-M4 brief.
- **Item 2 (statements):** manuscript section 11 wording recorded as owner-approved (D-017). No wording changed.
- **Item 4 (D-016):** abstract and conclusion now lead with the frozen verdict "invalidated"; the reading against the H1 sign ("qualified") is given as secondary (D-018). No number changed. `scripts/m4_audit.py` on a scratch copy of the edited tree -> `"integrity_ok": true, "raw_ok": true, "manifest_entries": 6489, "unmatched": {}`.
- `manuscript.tex` regenerated with pandoc 3.6.3 (`pandoc -s research/paper/manuscript.md -t latex`, header lines kept); the diff touches only the abstract and conclusion. Not compiled; no PDF (M6).

### Owner placeholders for M5
1. Manuscript section 10: "public URL: [placeholder, not yet published]" (the repository's public URL, known only once the owner publishes it).
2. Manuscript section 11: funding and competing interests ("none are recorded in the project files. The owner confirms both statements before any release"): the owner confirms that there is no funding and no competing interest, or supplies them.
3. Noted, not a placeholder: `README.md` and `CITATION.cff` still describe the pre-M3 state ("no confirmatory results yet", version 0.0.0); they need an update in M5 or M6.
