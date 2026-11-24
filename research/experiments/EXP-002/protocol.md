<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-002: Liquidity supply and spread (protocol)

**Status: v1.0, FROZEN (owner-approved 2026-11-24).** Draft v0.1 plus the amendments of 2026-11-24 (round 2) listed in section "Amendments before freeze" below and in `research/protocol.md` section 12. Freeze record: `research/freeze.json`. Shared definitions are in `research/protocol.md` sections 3, 5 and 7.

## 1. Question
How does the liquidity supplied by random-order agents (their limit-order probability) change the mean quoted spread, and does the effect of trend followers on VCI (EXP-001) depend on liquidity?

## 2. Mechanism and rationale
More resting limit orders fill the book, narrowing the spread and absorbing market orders with smaller price moves (random-order CDA theory, Smith et al. 2003, arXiv cond-mat/0210475, opened 2026-11-24). A thin book may amplify the price impact of trend-following order flow.

## 3. Competing explanations
Order-lifetime effects (a higher limit rate with fixed lifetime also raises depth); one-sided book episodes at low liquidity.

## 4. Hypotheses
- Primary outcome: mean quoted spread (ticks). H0: no difference between low and high liquidity in ZI-only markets. H1 (directional): spread is lower at high liquidity.
- Secondary: interaction, `[VCI(ZI+TF) - VCI(ZI)]` at medium liquidity minus the same at high liquidity; nondirectional (the low-liquidity version is dropped by amendment A1).
- Contradiction: CI of the low-minus-high spread difference entirely below 0.

## 5. Estimand and unit
Mean paired (by seed) difference in spread between liquidity levels; unit = one run.

## 6. Arms
ZI market-order probability `p_mkt` in {0.35 (low liquidity), 0.2 (medium, equals EXP-001), 0.1 (high)} crossed with composition {ZI-only (100 ZI), ZI+TF (70 ZI, 30 TF)}. Six arms. Other parameters as EXP-001.

## 7. Seeds and sample size
Seeds 1001..1030, common random numbers across all six arms. Rationale as EXP-001.

## 8. Compute budget
180 runs, about 30 minutes on 10 cores at the planning estimate.

## 9. Analysis plan
Primary: bootstrap 95% CI of mean paired spread difference, low minus high, ZI-only. Secondary: all pairwise level contrasts for spread, depth, volume, realised volatility among the five non-excluded arms; the interaction contrast on VCI at medium versus high liquidity, `[VCI(med-ZI+TF) - VCI(med-ZI)] - [VCI(high-ZI+TF) - VCI(high-ZI)]`; Holm-adjusted within this experiment. The `low-ZI+TF` arm is excluded from every contrast (amendment A1) and reported descriptively.

## 10. Exclusion, stopping, failure modes
As in the shared protocol. Low liquidity is the arm most likely to produce one-sided books; flag counts are reported per arm, and a flag rate above 20% in an arm is reported as a model failure for that arm, not hidden.

## 11. Sensitivity
Exclusion of flagged runs; order lifetime `tau` halved (exploratory, labelled).

## 12. Reproduction (planned)
`uv run python -m market.cli run --exp EXP-002 && uv run python -m market.cli report --exp EXP-002`

## Amendments before freeze (owner-approved 2026-11-24, round 2)

- A1: the degenerate low-liquidity cell `low-ZI+TF` (flagged in 10 of 10 development seeds, journal J-0003: one-sided fraction about 0.19, mid at the 1-tick price floor) is run for all 30 seeds and reported in full (per-seed metrics, flag counts, figures) but excluded from every contrast of this experiment. The interaction contrast moves from low-versus-high to medium-versus-high liquidity. The section 10 rule (flag rate above 20% reported as a model failure for that arm) still applies and is reported.
- A2: 30 seeds per arm, confirmed.
