<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Evidence audit (M4, master prompt 11.5)

**Date:** 2026-11-25. **Auditor:** the AI research assistant (internal quality control, not external review). **Command:** `.venv/bin/python scripts/m4_audit.py`. **Outputs:** `research/publication/artifact_manifest.json` (the manifest) and `research/publication/audit_result.json` (every check below, machine-readable). Journal J-0012.

## 1. Scope

- Documents audited: `research/paper/manuscript.md`, `research/paper/supplementary.md`, the five experiment reports `research/experiments/EXP-00N/report.md`, `research/publication/review_pass_2.md` and this file.
- Evidence: `results/confirmatory/EXP-001` to `EXP-005` (per-run JSON, `metrics.csv`, `tables/arm_summary.csv`, `analysis.json`, `comparison.json`, `run_manifest.json`, `SHA256SUMS`), `results/exploratory/REAL-REF/reference.json`, the pre-freeze pilot tables `results/exploratory/PILOT-*/tables/`, the M4 exploratory output `results/exploratory/M4-SENS/m4_exploratory.json` and `research/experiment_journal.jsonl`.

## 2. The artifact manifest

The manifest has one entry per numeric value in the evidence files listed above. Each entry records the experiment id, the label (confirmatory, exploratory or journal), the value, the result path and JSON path, a description of the metric (the labels of the enclosing row: role, treatment, control, metric, arm, statistic, sampling), the run ids (pattern `EXP-00N-<arm>-s<seed>`, arms and seeds), the generator script, the config SHA-256 and protocol SHA-256 from `research/freeze.json`, and the code revision from the run manifest. It also lists every figure in the experiment folders with its source and generator. The exploratory entries carry their own revision and the note "exploratory, no protocol".

The manuscript's tables are written by `scripts/m4_tables.py` from the same files, between generated-table markers; the figures in `research/paper/figures/` are copies of the experiment figures plus one exploratory figure drawn from `m4_exploratory.json`. The claims register (`research/claims_register.csv`) gives each claim its result id, config hash, table or figure, manuscript section and limit.

## 3. Checks against the raw outputs

| Check | Result |
| --- | --- |
| Every file listed in the five `SHA256SUMS` matches its checksum | 550 files, 0 mismatches |
| Per-run JSON against `metrics.csv`, every metric, exact (tolerance 1e-12 relative) | EXP-001 120, EXP-002 180, EXP-003 90, EXP-004 90 rows; 0 mismatches |
| Runs per arm, status and seeds | every arm 30 runs, all `ok`, seeds 1001..1030 |
| Returns per run (denominator of every return statistic) | 1,800 in every one of the 480 runs |
| Arm summary means and SDs recomputed from the per-run JSON (six metrics) | 0 mismatches in all four experiments |
| Primary contrasts recomputed independently from per-run JSON (paired differences, own bootstrap with the frozen seed) | EXP-001, EXP-002, EXP-003 primaries, the EXP-004 placebo and tick-2 contrast: mean, interval and pair count identical to `analysis.json` |
| Common random numbers: EXP-002 med-ZI and med-ZI+TF equal EXP-001 A0 and A1 seed by seed | true |
| Number trace: every decimal number and every integer above 100 in the audited documents equals, at its printed precision, a manifest value, a frozen parameter or a structural constant | 0 unmatched tokens in the final state |

**Units and precision.** VCI, excess kurtosis and autocorrelations are dimensionless; realised volatility is a log return per `dt` steps; spreads are in ticks (equal to price units at tick 1; the EXP-004 tick-2 arms are labelled in price units, correctly); depth and volume in units; drawdowns as fractions. Values are printed to four significant digits and `d_z` to three; Holm levels to five decimals. "Holm p < 0.0001" means that none of the 10,000 bootstrap means crossed 0, which is the resolution of the bootstrap; the reports say so. Uncertainty is the 95% percentile bootstrap interval of the mean paired difference over 30 seeds, as frozen; every interval in the documents names its pair count or is in a table that does.

## 4. External claims

Each external claim is a row X-001 to X-008 in the claims register, with the source that was opened. Abstracts were re-read on 2026-11-25 for Chiarella et al. (arXiv 0711.3581), Smith et al. (arXiv cond-mat/0210475), Farmer et al. (arXiv cond-mat/0309233) and Cont (RePEc record); the full text of Ratliff-Crain et al. (arXiv 2311.07738 v2, HTML) was read; the FI-2010 journal metadata was checked against the Crossref record of doi:10.1002/for.2543. Abstract-only sources are marked as such in the manuscript's reference list and in `research/literature_review.md`.

## 5. Findings and fixes

| ID | Finding | Severity | Action |
| --- | --- | --- | --- |
| F-1 | In the EXP-001, EXP-002 and EXP-003 reports the primary row and the degenerate-run sensitivity row of the primary table were printed identically with no label (no run was flagged, so the numbers are equal); the EXP-004 exclusion row could not be told apart from the EXP-001 primary. | presentation; numbers correct | Fixed: the generator `scripts/write_m3_reports.py` now prints a role column in every non-Holm contrast table; the four reports were regenerated, and only those table lines and the M4 notes changed. No number changed. |
| F-2 | "Volatility clustering is one of the stylized facts catalogued by Cont (2001)" (protocol section 2, reports) is not supported by the Cont abstract, which was the only part read; the abstract speaks of "nonlinear dependence of returns in time". | citation scope | The manuscript now cites Cont for the catalogue and Ratliff-Crain et al. (full text read) for the content of the volatility-clustering fact. The frozen protocol is not edited; this note records the narrower support. |
| F-3 | Chiarella et al.'s abstract says "clustering", not "volatility clustering". | wording | The manuscript quotes "fat tails and clustering". |
| F-4 | The FI-2010 paper had no entry in `references.bib`. | bibliography | Added `Ntakaris2018`, metadata from the Crossref record. |
| F-5 | The manuscript draft cited a wall time of 57.2 s for the exploratory script after the script had been rerun (final execution 58.4 s). The trace did not flag it at first because the manifest then still held the earlier value; rerunning the audit after the final execution did. | stale number | Fixed in the manuscript; the audit was rerun last, on the final outputs. |
| F-6 | Smith et al.'s claim "order size matters more than tick size" in `research/literature_review.md` was not seen in the abstract excerpt read on 2026-11-25. | unverified detail | Not used in the manuscript; left in the literature review with this note. |
| F-7 | The report generator's statement about the pre-freeze pilot ("had also given an interval including 0") was checked against `results/exploratory/PILOT-MIX/tables/paired_contrasts.csv`: correct (A1 - A0 -0.003781 [-0.02328, 0.02025], 20 pairs). | none | The pilot tables were added to the manifest; the pilot's interval pattern is now disclosed in the manuscript (review pass R2-8). |

## 6. Limits of this audit

- The number trace is permissive: a printed number passes if any of the several thousand manifest values formats to it at two to four significant digits (or as a percentage). A coincidental match is possible. The key results (primary contrasts, verdicts and the tables, which are generated) were additionally checked by recomputation or by generation, not only by the trace.
- Integers of 100 or less (section numbers, counts such as "16 of 30", lags) are not traced automatically; the counts used in the manuscript were checked by hand against `m4_exploratory.json` (E5, E6) and `analysis.json`.
- Statements about code behaviour (for example the book's data structures) were checked by reading the source, not by test.
- The audit does not re-run the simulations. Determinism was established in M3 (J-0005: the smoke check reproduced J-0002 bit for bit) and is exercised by the test suite.
