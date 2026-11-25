<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Second review pass (M4): arguing against the preferred reading

**Date:** 2026-11-25. **Reviewer:** the AI research assistant, internal quality control (master prompt 11.5). This is not external peer review. **Object:** `research/paper/manuscript.md` as first drafted in M4, the five experiment reports, and the exploratory M4 checks.

**Preferred reading under challenge.** The first M4 draft carried three claims beyond the frozen verdicts: (P1) the trend-follower effect on VCI is horizon-dependent, with aggressiveness explaining a short-horizon effect and trend feedback a long-horizon "persistent volatility" effect (exploratory E1); (P2) at the primary interval, trend following produces less clustering than an aggressiveness-matched placebo (EXP-004); (P3) trend followers deepen post-shock drawdowns, mostly as a genuine shock response (EXP-003 plus exploratory E2). Each was attacked below. "Holds" means the challenge succeeded and the manuscript was revised.

## 1. Strongest alternative readings

| ID | Challenge | Test made | Outcome | Change |
| --- | --- | --- | --- | --- |
| R2-1 | **VCI at long intervals measures trend runs, not volatility clustering.** With a 500-step lookback, TF markets may drift in runs. Serially correlated signed returns make the autocorrelation of absolute returns positive even if volatility is constant, so a high VCI at `dt` 200 or 500 need not be clustering in the stylized-fact sense. | Added the lag-1 autocorrelation of signed returns per `dt` to the exploratory script (development seeds 101 to 130, rerun, J-0011). | **Holds.** In A1 the mean lag-1 autocorrelation of signed returns is 0.653 at `dt` 200 and 0.8921 at `dt` 500 (A0: -0.4315 and -0.4306). Long-horizon A1 returns are trend runs. | P1 withdrawn in its "persistent volatility" form. Abstract, sections 5.6, 6.1 to 6.3, 7 and 9 now say that the long-horizon VCI increase reflects trend runs at least as much as clustering. The confirmatory `dt` = 200 contrast (EXP-004) carries the same caveat. |
| R2-2 | **VCI at short intervals is shaped by bid-ask bounce.** The all-ZI market has a strongly negative lag-1 autocorrelation of signed returns (committed A0 mean -0.3786 at `dt` 50), the sign of a mid bouncing within the spread. Trend followers remove most of it (A1 -0.00584). A change in VCI between A0 and A1 therefore mixes a change in microstructure noise with any change in clustering. | Committed EXP-001 arm summaries; exploratory per-`dt` values. | **Holds** as a construct-validity threat. A0 is negative at every `dt` from 5 to 500 on the development seeds (-0.1691 to -0.4315), so even the baseline is not a clean "no clustering" reference. | Added to section 7 (construct) and section 6.2 (Table 10) as a competing explanation the protocol did not name. The confirmatory verdict is unaffected; its interpretation is weaker. |
| R2-3 | **The placebo result (P2) is fragile.** A1 minus A4 at `dt` 50 has an interval whose upper end is -0.0002837, and EXP-004 has six components with no multiplicity adjustment. A single extra test would move it across 0. | Inspection of the committed interval; no new computation. | **Holds.** | Sections 5.4 and 6.2 now state that the interval only just excludes 0 and that EXP-004 has no multiplicity adjustment; the claim is worded as "no evidence that the trend rule adds clustering beyond aggressive flow at `dt` = 50", not as "less clustering". Claim C-005 qualified. |
| R2-4 | **The EXP-004 verdict is an artefact of an analysis choice.** The frozen rule says "same sign"; the AI chose the sign of the near-zero point estimate as the reference (D-013). The rule was written to protect a positive H1. | E4: reading with the sign of H1. | **Holds in part.** The alternative reading returns "qualified", not "invalidated". Both readings agree that the conclusion depends on the horizon. | The manuscript already reported this (section 6.4); the abstract now says the verdict depends on that choice. The frozen verdict stands (D-015). |
| R2-5 | **The EXP-003 effect (P3) is ordinary trend excursions plus thinner books.** | E2 (development seeds) and E6 (committed runs). | **Does not hold in full.** Ordinary excursions match about one third of the shocked contrast on the development seeds (0.007912 of 0.02408); the difference-in-differences is 0.01616 [0.009609, 0.02483]. Within the TF arm drawdown is nearly unrelated to bid depth at the shock (Spearman 0.07141), and every shock was fully filled. | Wording kept but bounded: "part, not all, of the shocked contrast". The difference-in-differences is not additive in a strict sense (drawdown is a minimum over a window), and E2 used different seeds from EXP-003; both stated. |
| R2-6 | **The EXP-002 interaction is a discreteness effect.** high-ZI+TF has a negative mean VCI (-0.03352) with a mean spread of 1.132 ticks, so its mid moves in half-tick steps and alternation dominates the absolute returns. | Committed arm summaries. | **Holds** as an alternative reading that cannot be excluded. | Section 5.2 and Table 10 now say that the interaction may reflect microstructure at a spread close to one tick rather than an interplay of liquidity and feedback. |
| R2-8 | **The horizon dependence was known before the freeze, so presenting it as a discovery overstates it.** | Journal J-0003 and decision D-007 item 6. | **Holds.** The pre-freeze pilot (development seeds 1 to 20) already gave A1 - A0 = -0.003781 [-0.02328, 0.02025] at `dt` = 50 and positive values at 10 and 200 (0.01781 and 0.1319). The observation was reported to the owner before the freeze, and the primary interval was kept. | Section 6.1 now states that the confirmatory runs reproduced a pattern seen in the pilot. The contribution is the preregistered confirmation and the controls, not the discovery of interval dependence. |
| R2-7 | **The exploratory "replication" on development seeds is not independent.** The checks were designed after the confirmatory results were seen, by the same analyst, and the dt grid was chosen to include the confirmatory intervals. | Process review. | **Holds.** | Section 5.6 and section 7 state that the M4 checks are post hoc and hypothesis-generating; nothing in them is called a replication of a confirmatory result except the direct recomputation of the same formulas. |

## 2. Overgeneralisation

- The first draft's abstract said that the exploratory check "suggests that aggressiveness explains the short-horizon effect and trend feedback a long-horizon one". After R2-1 and R2-2 this is too strong: the short-horizon VCI difference also tracks bounce, and the long-horizon one tracks trend runs. **Revised** to a bounded statement.
- "Trend followers deepen the drawdown after a sell shock" is stated only for this model, one shock size (50% of bid depth), one time (step 50,000) and one window (5,000 steps). **Kept**, with that scope.
- The FI-2010 placement is described as order-of-magnitude agreement under a crude clock match, never as validation. **Kept.**
- "Contributions" item 4 was reworded from a finding to a question for a new study.

## 3. Stale figures and numbers

- The manuscript tables are generated by `scripts/m4_tables.py` from committed outputs and the figures are copied from the experiment folders at the same revision; the evidence audit (`research/publication/evidence_audit.md`) found no stale number. The exploratory output was regenerated after R2-1 (third run of the script); part 1 numbers other than the new autocorrelation columns are identical across runs (deterministic simulation), and the manuscript and reports were regenerated from the final file.
- The EXP-001 and EXP-002 to EXP-004 reports had primary and sensitivity rows that were indistinguishable (identical numbers, no label). **Fixed** by a role column (audit finding F-1).

## 4. Leakage

- FI-2010: the reference values were fitted on days 1 to 9 before the freeze; day 10 was not read for statistics before the comparison; no simulation parameter was fitted to the data (J-0004, R1). No leakage found.
- Seeds: confirmatory seeds 1001 to 1030 were not run before the freeze (guard tests); exploratory M4 seeds 101 to 130 are disjoint from the pilot seeds 1 to 40 and from the confirmatory seeds. No leakage found.
- Analysis: `market.frozen_analysis` was committed before any confirmatory output (D-013) and has not been edited since. M4 code is new and labelled exploratory.

## 5. Missing failed runs and unreported analyses

- Confirmatory: 480 of 480 runs `ok`; none dropped or retried (audit: run counts, statuses and `n_returns` = 1,800 in every run).
- Exploratory M4: `scripts/m4_exploratory.py` was executed three times (the second run added E6, the third added the per-`dt` signed-return autocorrelation after R2-1). Each run overwrote the previous output; all three are recorded in J-0011. No run failed.
- Sensitivities named in the protocols but never run: order lifetime halved (EXP-002) and the 25% shock (EXP-003). Disclosed in section 7 and the supplement.
- The alternative EXP-002 Holm family (all ten pairs) was not computed. Disclosed.

## 6. What survives

The frozen verdicts are unchanged: EXP-001 inconclusive and, under the frozen rule, invalidated by a sign reversal; EXP-002 supported; EXP-003 supported; EXP-004 placebo interval below 0 (just); EXP-005 (a) not supported. After this pass, the manuscript's interpretive claims are narrower: the study shows that a trend-follower effect on VCI cannot be read off one sampling interval, that aggressive flow alone changes VCI at the primary interval, and that VCI in this model is entangled with bounce at short horizons and with trend runs at long ones. Whether trend feedback produces volatility clustering in the stylized-fact sense is left open, with a concrete design for a new preregistered study (a `dt` and lookback sweep with a placebo at each point, and a clustering measure robust to signed autocorrelation, for example the autocorrelation of absolute residuals after removing the signed-return dependence).

## 7. Record of manuscript changes made after this pass

1. Abstract: last sentences rewritten (R2-1, R2-2, R2-4).
2. Contribution 4 reworded as an open question (section 2 above).
3. Section 5.2: discreteness reading of the interaction (R2-6).
4. Section 5.4: placebo wording and multiplicity caveat (R2-3).
5. Section 5.6 E1: trend-run evidence added, "persistent volatility" removed (R2-1); post hoc status stated (R2-7).
6. Section 6.1 to 6.3: interpretation narrowed; the pre-freeze pilot pattern disclosed (R2-8); Table 10 gains the bounce, trend-run and discreteness rows (R2-1, R2-2, R2-6).
7. Section 7: construct-validity items for bounce and trend runs; post hoc status of M4 checks.
8. Section 9: conclusion and the proposed next study updated.
9. Claims register: C-005 qualified; C-013 to C-016 added for the exploratory results, each labelled exploratory.
