<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Reproducibility report (M6, release candidate)

**Date:** 2026-11-25. **Prepared by:** the AI research assistant under the owner's instruction of 2026-11-25, "Next" (second) (`labs/_shared/owner-approvals-2026-11-25e.md`). Journal J-0014; decision D-020. Every output below is copied from the terminal; nothing is paraphrased into a number.

## 1. Environment

- Apple M1 Pro laptop, macOS (Darwin 24.3.0), shared with other work; two workers at most.
- Python 3.12 from `uv` (`labs/.tools/py/bin/uv`), locked by `uv.lock` (`exclude-newer` 2026-11-10).
- Node 22.23.3 (`node --version` -> `v22.23.3`), npm cache in a scratch folder; Google Chrome (system) for the accessibility checker.
- PDF toolchain: pandoc 3.6.3 (`labs/.tools/pandoc`), Typst through the `typst` Python package 0.15.0, metadata check with pypdf 6.20.0.

## 2. Clean clone (revision 704a568, before the M6 changes)

Commands run in a scratch folder outside the repository (the clone was deleted at the end):

| Step | Command | Actual output |
| --- | --- | --- |
| Clone | `git clone -q <repo> <scratch>/clone`; `git log --oneline -1` | `704a568 M5: interactive page and faithful engine-port sandbox; ...` |
| Install | `uv sync --frozen --all-groups --all-extras` | installed the locked set (`+ numpy`, `+ pytest`, `+ hypothesis`, ...); a second run: `Audited 9 packages in 1ms` |
| Tests | `.venv/bin/python -m pytest -q` | `170 passed in 27.45s` |
| Smoke reproduction | `.venv/bin/python -m market.cli smoke --out <scratch>/smoke --workers 2` | `runs: 10, failed: 0, wall time: 0.62s` |
| Demo install | `cd demo && npm ci --prefer-offline` | `added 53 packages in 631ms` |
| Demo tests | `npm test` | `Test Files  2 passed (2)`, `Tests  27 passed (27)` |
| Demo build | `npm run build` | `dist/assets/index-DLdWyS6v.js 251.33 kB`, `sandbox.worker-zOukWTlf.js 16.58 kB`, `built in 315ms` |
| Accessibility | `node tools/a11y_check.mjs dist` | nine PASS lines (8 experiment panels; contrast light and dark; keyboard 28 of 28; focus; 360 px overflow 0px; reduced motion 0 running; no request leaves the local origin; offline after first load), then `A11Y-CHECK PASS` |
| Export determinism | `.venv/bin/python scripts/export_demo_data.py`; `git status --short` | `wrote demo/public/data/results.json`; no status line (clean) |

## 3. Smoke reproduction comparison

The documented smoke reproduction is `market.cli smoke` (README "Quick start"; deterministic given seed and revision). Its output was compared with the two committed smoke outputs.

| Compared with | Result |
| --- | --- |
| `results/exploratory/smoke-M3/` (written by the same code path in M3, J-0005) | `metrics.csv` (10 rows) and `tables/arm_summary.csv` (2 rows) identical except the runtime columns (`runtime_s`, `runtime_mean_s`); `tables/paired_contrasts.csv` byte-identical; the metric block of each of the 10 run JSON files identical |
| `results/exploratory/smoke/` (M2, before three metrics were added) | every metric present in the older files identical in all 10 runs; `mean_relative_spread`, `realised_volatility_dt10` and `realised_volatility_dt200` are absent from the older files; both `series/*.json` files byte-identical |

Tolerance: exact equality for every metric (documented determinism; README "Full reproduction"). Runtimes are wall-clock measurements and are not expected to match. Outcome: **reproduced**.

## 4. Checks run in the working repository (M6)

| Check | Command | Actual output |
| --- | --- | --- |
| Evidence audit | `.venv/bin/python scripts/m4_audit.py` | `"integrity_ok": true, "raw_ok": true, "manifest_entries": 6495, "unmatched": {}` |
| Result checksums | `shasum -a 256 -c SHA256SUMS` in each `results/confirmatory/EXP-00N/` | 137, 199, 106, 106, 2 OK (550), 0 failed |
| Data manifest | SHA-256 and size of the two FI-2010 files used | both equal to `data/manifest.json` |
| Links | `.venv/bin/python scripts/check_links.py` | `LINK-CHECK PASS: 118 relative links in 54 Markdown files resolve` (before the M6 files were added) |
| PDFs | `.venv/bin/python scripts/build_pdfs.py` | 7 PDFs; a second build gives identical bytes (7 of 7 SHA-256 equal) |
| Report regeneration | `scripts/write_m3_reports.py` on a scratch copy of the M6 tree | every `report.md`, `reproduction.md`, JSON and `metrics.csv` byte-identical to the repository |

## 5. Failures and deviations

- **Clean clone:** no failure. Every step passed at revision 704a568.
- **Findings fixed in the working repository (M6):**
  1. PDF layout (first build): wide tables overlapped and were justified; a table caption was separated from its table; figure captions were numbered twice ("Figure 1: Figure 1."); the Typst writer emitted native citation references, so the manuscript did not compile until citations were resolved by pandoc. Fixed in the builder (`src/market/report.py`, `render_pdf`: table and figure rules, pandoc `--citeproc` with the bibliography, title from the first heading, page numbers, no creation date), never by editing a PDF.
  2. Absolute home-directory paths in `README.md`, the manuscript, four experiment reports and reproduction files, `demo/README.md` and the report generator: replaced by the plain `uv` command (the reports regenerate byte-identically from the edited generator).
  3. `research/publication/artifact_manifest.json` was stale since M5 (it lacked the two J-0013 journal values): regenerated by the audit script.
- **Not changed, recorded:** paths in `CLAUDE.md` (session instructions that name the shared toolchain), `research/feasibility.md` (M0 measurement record), the five `results/confirmatory/*.log` files (committed raw logs), `progress.md` (append-only) and the default tool paths in `src/market/report.py` (overridable by `MARKET_PANDOC` and `MARKET_TYPST_PYTHON`).
