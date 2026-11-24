<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-003: Response to an exogenous sell shock (protocol)

**Status: DRAFT v0.1, 2026-11-24. Planned (protocol draft, awaiting owner freeze). Not frozen; no protocol hash yet.** Optional under the five-day target: cut first among experiments if the schedule is threatened (roadmap fallbacks). Shared definitions are in `research/protocol.md`.

## 1. Question
After a single large exogenous market sell order, how do agent mixtures differ in drawdown and recovery of the mid-price?

## 2. Mechanism and rationale
Trend followers may extend a shock-induced fall (positive feedback); mean reverters may buy into it (negative feedback). The ZI-only market gives the mechanical response of the book alone.

## 3. Competing explanations
Differences in book depth at shock time across mixtures (measured and reported as a covariate); the shock consuming one side completely.

## 4. Hypotheses
- Primary outcome: post-shock maximum drawdown of the mid-price over the 5,000 steps after the shock, relative to the pre-shock mid.
- H0: no difference between ZI+TF and ZI-only. H1 (directional): larger drawdown with ZI+TF.
- Secondary: recovery time (steps until the mid returns within 1% of the pre-shock mid, censored at 20,000 steps; censoring reported), spread widening, ZI+MR vs ZI-only (nondirectional).
- Contradiction: CI of mean paired drawdown difference entirely below 0.

## 5. Shock definition
At step 50,000 a dedicated shock agent outside the 100 agents submits one market sell of size equal to 50% of the total resting bid depth at that step (rounded down, minimum 1), with inventory endowed for that purpose; its cash and inventory are included in the conservation checks.

## 6. Arms
ZI-only, ZI+TF (70/30), ZI+MR (70/30), each with the shock. Other parameters as EXP-001.

## 7. Seeds, unit, budget
Seeds 1001..1030, common random numbers; unit one run; 90 runs.

## 8. Analysis plan
Bootstrap 95% CI of mean paired differences; Kaplan-Meier style reporting of censored recovery times is descriptive only. Holm adjustment across the declared secondary contrasts.

## 9. Exclusion, stopping, failure modes
As in the shared protocol. A shock that empties the bid side is recorded and the run kept.

## 10. Sensitivity
Shock size 25% of bid depth (exploratory, labelled).

## 11. Reproduction (planned)
`uv run python -m market.cli run --exp EXP-003 && uv run python -m market.cli report --exp EXP-003`
