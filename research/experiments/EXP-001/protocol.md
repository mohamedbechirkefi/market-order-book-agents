<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-001: Agent mixtures and volatility clustering (protocol)

**Status: DRAFT v0.1, 2026-11-24. Planned (protocol draft, awaiting owner freeze). Not frozen; no protocol hash yet.** Shared definitions (mechanism, accounting, agents, metrics, rules) are in `research/protocol.md` sections 3, 5 and 7 and are part of this protocol by reference.

## 1. Question
Does replacing 30% of random-order (ZI) agents by trend followers (TF) raise the volatility clustering index (VCI) of mid-price returns relative to an all-ZI market, with everything else held equal? Secondary: what do mean reverters (MR) and a TF+MR mix do to VCI, volatility, spread, volume and drawdown?

## 2. Mechanism and rationale
Trend followers act in the direction of recent mid-price changes, so a large move raises the chance of further aggressive orders in the same direction, which can make large absolute returns follow large ones. Chiarella, Iori and Perello (2009, arXiv 0711.3581, opened 2026-11-24) report the chartist component as the main source of clustering in their order-driven model. Random-order models (Farmer, Patelli and Zovko 2005; Smith et al. 2003) give the null comparison.

## 3. Competing explanations
1. Aggressiveness: TF agents send market orders at a different rate than ZI agents; more market orders alone can change return dynamics (tested by EXP-004 placebo).
2. Liquidity removal: each TF replaces a ZI liquidity provider, thinning the book (partly addressed by EXP-002).
3. Sampling artefact of `dt` (EXP-004).

## 4. Hypotheses
- H0: `E[VCI(A1) - VCI(A0)] = 0`. H1: `> 0`.
- Contradiction: 95% CI of the mean paired difference entirely below 0. Inconclusive: CI includes 0 (never read as equivalence).

## 5. Estimand, unit, scope
- Estimand: mean over seeds of the paired difference `VCI(A1, s) - VCI(A0, s)`, within this model and parameter set.
- Experimental unit: one run (arm, seed). Simulation scope: the parameter set below only.

## 6. Variables and arms
Independent variable: agent composition (100 agents in total in all arms).

| Arm | ZI | TF | MR | Role |
| --- | --- | --- | --- | --- |
| A0 | 100 | 0 | 0 | Baseline (random-order), control |
| A1 | 70 | 30 | 0 | Primary treatment |
| A2 | 70 | 0 | 30 | Secondary |
| A3 | 70 | 15 | 15 | Secondary |

Dependent variables: VCI (primary); realised volatility, excess kurtosis, `acf(r,1)`, mean spread, depth at best, volume, maximum drawdown, one-sided fraction, rejected-order share (secondary).

## 7. Fixed parameters (draft planning values; finalised from development seeds before freeze)
`T = 100,000` steps, `B = 10,000`, `dt = 50`, tick 1, initial price 1,000 ticks, order size uniform on 1..5, ZI market-order probability `p_mkt = 0.2`, limit offset `delta = 10` ticks, order lifetime `tau = 2,000` steps, TF/MR lookback `L = 500` steps, TF/MR market-order probability `p_mkt_tf = 0.5`, initial endowment per agent 1,000,000 ticks of cash and 1,000 units. Initial book: 20 limit orders per side seeded from the ZI rule.

## 8. Seeds and sample size
Seeds 1001..1030, common random numbers across arms (shared activation and ZI streams). 30 paired seeds detect `d_z` of about 0.53 at 80% power, two-sided alpha 0.05 (planning approximation, protocol section 6).

## 9. Compute budget
120 runs. Planning target at most 10 s per run on one core (to be measured in M2); about 20 minutes total on 10 cores.

## 10. Metric formulas
As in `research/protocol.md` section 5. VCI = mean over lags 1..10 of the sample autocorrelation of `|r_k|`.

## 11. Analysis plan
Primary: 95% percentile bootstrap CI (10,000 resamples, bootstrap seed 20261124) of mean `D = VCI(A1) - VCI(A0)` over seeds; `d_z`; per-seed values plotted. Secondary contrasts A2 vs A0, A3 vs A0, A1 vs A2 on VCI and on every secondary metric, Holm-adjusted, labelled secondary.

## 12. Exclusion and stopping
As in `research/protocol.md` section 7. No optional stopping; all 120 runs.

## 13. Anticipated failure modes
TF herding drives the price to the floor or empties a book side; VCI undefined when all returns are zero; slow engine. Each is detected by flags in the run manifest.

## 14. Sensitivity
EXP-004 (placebo, `dt`, tick size) and exclusion of flagged runs.

## 15. Reproduction (planned)
`uv sync --frozen && uv run python -m market.cli run --exp EXP-001 && uv run python -m market.cli report --exp EXP-001`
