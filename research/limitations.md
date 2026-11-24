<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Limitations (living document, M0 draft)

No results exist yet. These limitations are known from the design and will be revisited at M4.

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
