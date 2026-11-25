<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Limitations (living document: M0 draft, M2, M3 and M4 additions)

The first sections list limitations known from the design (M0 to M2). The M3 and M4 sections add what the confirmatory results and the M4 interpretation showed.

## Construct validity
- "Volatility clustering" is measured by one statistic (mean ACF of absolute returns, lags 1 to 10) at one sampling interval; other measures (GARCH fits, long-memory exponents) are not used.
- Event time, not clock time: returns are sampled every `dt` agent actions, which is not equivalent to calendar intervals in real markets.
- Agents are fixed rules, not learning or optimising traders. "Trend follower" and "mean reverter" are stylised caricatures.

## Internal validity
- Replacing zero-intelligence agents by trend followers removes liquidity providers at the same time as it adds feedback. The placebo arm (EXP-004) controls aggressiveness but not every difference.
- Parameters are tuned on development seeds 1 to 999; tuning choices may still favour or disfavour the hypothesis. All tuning runs are journaled as exploratory.
- Burn-in, order lifetime, initial book seeding and the price floor are modelling choices that can affect results.

## External validity
- Simulated agents are not human participants and the model is not calibrated to any real market. Results hold only within the model's assumptions.
- No claim about real markets, prediction, trading recommendations or profitability is made or implied. Wealth by agent type is descriptive model output, not evidence of a profitable strategy.

## Statistical validity
- About 2,000 returns per run make each VCI estimate noisy; power is planned for a paired effect of about 0.53 standard deviations (draft).
- A null result is not evidence of no effect.

## Tooling
- No TeX distribution: `manuscript.tex` is generated but not compiled locally; PDFs use pandoc and Typst.

## Implementation (added in M2)
- Self-trades are allowed and accounting-neutral; a real venue would usually prevent them (D-006).
- Prices have a floor of one tick. In the exploratory pilot (J-0003) the low-liquidity arm with trend followers reached that floor in every development seed, so results for that cell would describe the floor mechanics as much as the agents (D-007, item 3).
- Pilot runtimes were measured on a shared, heavily loaded machine; uncontended timings are lower.
- Figures are plain generated SVG; the PDF summaries were checked by text extraction only (no rasteriser installed), not by visual inspection.

## Real-data comparison (added at the freeze, EXP-005)
- One real market only: five liquid Helsinki stocks over ten days in June 2010 (FI-2010). Placement of a simulated arm inside or outside the real range says nothing about other markets or periods.
- The clocks are matched crudely: one simulation step (one agent action) against one tenth of an FI-2010 column (10 order-book events of any kind). The `dt` 10 and 200 sensitivity checks bound, but do not remove, this mismatch.
- Relative spreads depend on the tick relative to the price level; the simulation tick (1 unit at about 1,000) and the real tick (one cent on prices of a few to tens of euros) differ by stock.
- FI-2010 is distributed normalised. Only the decimal-precision variant is used, whose scaling leaves log returns and relative spreads unchanged; this depends on ask and bid prices sharing one scale within a file (checked in J-0004).
- No simulation parameter is calibrated on the real data, so the comparison tests the frozen model as specified, not a fitted one.
- The low-liquidity ZI+TF cell of EXP-002 is excluded from contrasts by a pre-declared rule (amendment A1); its behaviour is reported but not compared.
- FI-2010 files carry no timestamps and are ordered by stock, then by day; day boundaries inside a stock cannot be located. Reference blocks of 9,000 columns can therefore contain an overnight return at an unknown position, which can raise kurtosis and realised volatility in that block. Held-out units (one day per stock) are shorter than a block (1,888 to 13,378 columns), so their VCI estimates are noisier than the reference blocks'.

## Confirmatory results (added at M3, 2026-11-25)
- The EXP-001 primary contrast is inconclusive at `dt` = 50, but the same contrast is positive at `dt` = 10 and 200 (EXP-004). Any statement about trend followers and clustering is conditional on the sampling interval.
- A1's VCI varies much more across seeds than A0's (SD about 0.065 against 0.008), which limits power; the observed |d_z| (about 0.12) is far below the planned 0.53.
- The aggressiveness-matched placebo raised VCI at least as much as trend followers at `dt` = 50; the placebo does not reproduce the serial correlation of TF order direction, which is the feedback itself.
- EXP-003 post-shock drawdowns overlap ordinary TF excursions (no unshocked control window); spread widening was not measured, because the protocol gives no formula, and no metric is defined after the data (owner decision, D-015).
- Holm intervals among contrasts with a bootstrap p-value of 0 depend on input order (D-014); decisions do not. Disclosed and not changed (owner decision, D-015).
- The EXP-002 liquidity manipulation changes aggressive flow and limit supply together; the spread result is largely mechanical.
- The D-013 analysis choices (Holm interval construction, EXP-002 family, sign reference of the EXP-004 robustness rule) were made by the AI assistant before the data and are reviewed by the owner in M4 (D-015).

## Interpretation (added at M4, 2026-11-25)
- **VCI is not a clean clustering measure in this model.** At short sampling intervals it is shaped by the strongly negative autocorrelation of signed returns (bid-ask bounce; confirmatory A0 acf(r, 1) at `dt` = 50 is -0.3786, A1 -0.00584). At long intervals in trend-follower markets it is shaped by trend runs (exploratory: A1 signed-return autocorrelation 0.653 at `dt` = 200 and 0.8921 at 500). A VCI difference between arms therefore mixes changes in microstructure noise, in trending and in clustering (review pass R2-1, R2-2).
- **The EXP-004 verdict depends on an analysis choice.** With the sign of H1 as the reference instead of the sign of the near-zero EXP-001 estimate (D-013 item 6), the robustness rule returns "qualified" instead of "invalidated". The frozen verdict stands (D-015).
- **The placebo contrast is fragile.** A1 minus A4 at `dt` = 50 has an upper interval end of -0.0002837 and EXP-004 carries no multiplicity adjustment across its six components.
- **The EXP-002 interaction may be a discreteness effect** (high-ZI+TF has a negative mean VCI at a spread of 1.132 ticks).
- **EXP-003 decomposition is exploratory and approximate.** The unshocked control window (development seeds) attributes part of the shock contrast to ordinary trend excursions; drawdowns are window minima, so effects need not add, and the seeds differ from EXP-003.
- **The M4 checks are post hoc.** They were designed after the confirmatory results were seen; they are hypothesis-generating only and never change a frozen verdict. The interval dependence itself was visible in the pre-freeze pilot (J-0003, D-007 item 6).
- **Literature.** Except FI-2010 and Ratliff-Crain et al. (2023), only abstracts or bibliographic records were read; Cont (2001) is cited only for what its abstract supports.
- **Not run.** The protocol sensitivities "order lifetime halved" (EXP-002) and "25% shock" (EXP-003) were never run; the alternative EXP-002 Holm family (all ten pairs) was not computed.
