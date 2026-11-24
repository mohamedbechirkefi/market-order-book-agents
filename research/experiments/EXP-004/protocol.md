<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-004: Sensitivity analyses that could invalidate EXP-001 (protocol)

**Status: DRAFT v0.1, 2026-11-24. Planned (protocol draft, awaiting owner freeze). Not frozen; no protocol hash yet.** Depends on EXP-001. Not optional: it is the control that decides how EXP-001 may be interpreted.

## 1. Question
Is any VCI increase found in EXP-001 attributable to the trend rule's price feedback, rather than to changed order aggressiveness, the sampling interval or the tick size?

## 2. Rationale
Trend followers differ from ZI agents both in conditioning on prices and in the mix of order types they send. Without a placebo matched on aggressiveness, a VCI increase cannot be attributed to feedback.

## 3. Components and arms
1. **Placebo (A4):** 70 ZI + 30 placebo-aggressive (PA) agents. PA agents use the TF order-type probability, order sizes and limit placement, but their direction is a fair coin independent of prices, and they act on every activation (TF agents skip when the signal is 0; the TF skip rate is measured in EXP-001 and, if above 5%, PA agents skip with the same probability to match activity). Seeds 1001..1030. 30 runs.
2. **Tick size:** A0 and A1 with tick 2 (prices on even ticks only, all other parameters equal). 60 runs.
3. **Sampling interval:** EXP-001 runs reanalysed at `dt = 10` and `dt = 200` (no new runs).
4. **Exclusion:** EXP-001 primary contrast without flagged runs and their paired partners.

## 4. Hypotheses and invalidation criteria
- Placebo: H0 `E[VCI(A1) - VCI(A4)] = 0`; H1 `> 0`. If the 95% CI includes 0 while EXP-001 supports H1, the report must state that the EXP-001 effect is not attributable to trend feedback.
- `dt` and tick: the EXP-001 contrast is called robust only if its sign is the same and its CI excludes 0 at both `dt` values and at tick 2. A sign reversal invalidates the main interpretation; a CI including 0 qualifies it.

## 5. Unit, seeds, budget
Unit one run; seeds 1001..1030 with common random numbers shared with EXP-001; 90 new runs.

## 6. Analysis plan
Same bootstrap procedure as EXP-001. All four components reported, whichever way they come out.

## 7. Exclusion, stopping, failure modes
As in the shared protocol.

## 8. Reproduction (planned)
`uv run python -m market.cli run --exp EXP-004 && uv run python -m market.cli report --exp EXP-004`
