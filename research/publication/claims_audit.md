<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Claims audit (M4, 2026-11-25)

Register: `research/claims_register.csv` (29 rows: C-001 to C-021 for results, X-001 to X-008 for external sources). Columns: claim, type, result id, config SHA-256, figure or table, manuscript section, evidence path, scope, status, limitations. The evidence audit behind this file is `evidence_audit.md`; the adversarial review is `review_pass_2.md`.

## Procedure

For every row: the evidence path exists; the number equals the raw output at the printed precision (denominator, unit, uncertainty and sample count checked; `scripts/m4_audit.py`); the scope and limitation are stated; the manuscript section and table or figure named in the row contain the claim. For external rows: the source is in `research/literature_review.md` as opened, and the depth of reading (abstract only or full text) is stated in the row.

Every quantitative statement in the manuscript was then checked for a row. Statements without a row were either given one (C-013 to C-021) or reworded.

## Strength and scope of evidence per conclusion

| Conclusion | Rows | Strength | Scope |
| --- | --- | --- | --- |
| Trend followers did not detectably change VCI at `dt` = 50 (inconclusive) | C-001, C-017 | confirmatory, preregistered; low power for the effect observed | this model and parameter set; one statistic and interval |
| The EXP-001 interpretation is not robust to the sampling interval (frozen rule: invalidated) | C-004, C-016 | confirmatory sensitivity; verdict depends on an analysis choice (D-013 item 6) | three intervals; tick 1 and 2 |
| No evidence that the trend rule adds VCI beyond aggressive flow at `dt` = 50 | C-005 | confirmatory sensitivity; interval close to 0, no multiplicity adjustment | `dt` = 50 |
| More ZI limit supply narrows the spread | C-002, C-021 | confirmatory, very large effect, largely mechanical | liquidity varied through market-order probability |
| Trend followers deepen post-shock drawdowns | C-003, C-015, C-018 | confirmatory; exploratory decomposition attributes part to ordinary excursions | one shock size, time and window |
| Simulated statistics are of the same order of magnitude as FI-2010 | C-010, C-011 | descriptive | one market, crude clock match; never validation |
| VCI in this model is entangled with bounce (short `dt`) and trend runs (long `dt`) | C-013, C-014 | exploratory, post hoc, development seeds | hypothesis-generating |

## Claims qualified or reworded in M4

- C-005: "less clustering than the placebo" is no longer claimed; the row now reads "no evidence that the trend rule adds clustering beyond aggressive flow at `dt` = 50" (review pass R2-3).
- C-004, C-007, C-001, C-003: limitations extended with the M4 findings (sign-reference dependence, discreteness, bounce, ordinary excursions).
- The manuscript's first-draft claim that trend feedback produces "persistent volatility" at long horizons was withdrawn (R2-1).
- The Cont (2001) citation is now limited to what its abstract supports (evidence audit F-2).

## Result

Every numerical claim in the manuscript maps to a result id, a config hash and a table or figure; every external claim maps to a source that was opened, with abstract-only sources marked.
