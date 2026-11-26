<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
<!-- DRAFT for the owner. Not published. Every number is copied from research/paper/manuscript.md; tests/test_demo_export.py checks it. Publication is the owner's decision. -->

# Do trend followers make a simulated market's volatility cluster? A preregistered test that came back "invalidated"

*By Mohamed Bechir Kefi, independent researcher. Draft. Simulated markets only: nothing here is a statement about real markets, a prediction, trading advice or a claim of profitability.*

Markets have calm stretches and turbulent stretches: big price moves tend to follow big price moves. Economists call this volatility clustering. A long line of agent-based models attributes it to traders who chase trends. But a trader who chases trends also trades more aggressively than a random one, so if a market full of trend followers clusters more, is that the trend rule, or just the aggressive orders?

I built a small simulated limit-order book to test this, and I wrote down the test, the metric and the rules for reading the result before running anything.

## The setup

One asset, 100 agents, a continuous double auction with price-time priority and strict cash and inventory accounting (no short selling, no borrowing). The baseline market has only random-order traders. The treatment replaces 30% of them by trend followers. Volatility clustering is measured by VCI, the mean autocorrelation of absolute mid-price returns over lags 1 to 10, with returns sampled every 50 agent actions.

Three controls were frozen with the protocol: a placebo arm of agents that trade exactly as aggressively as trend followers but pick their direction with a coin flip; the same contrast at sampling intervals of 10 and 200 steps; and a coarser tick. Every arm used the same 30 seeds, so arms are compared seed by seed.

*Figure (placeholder for the demo screenshot, `docs/demo.png`). Alt text: the frozen verdict "invalidated" above a chart of the trend-follower VCI contrast at dt 50, 10 and 200 steps and at tick 2, each with its 95% interval.*

## What happened

At the preregistered interval of 50 steps, trend followers changed VCI by -0.007825, with a 95% bootstrap interval of [-0.0268, 0.01785]. That is inconclusive, and inconclusive is not the same as "no effect".

The robustness rule then did what it was written to do. At 10 steps the same contrast was 0.02481 [0.0153, 0.03842]; at 200 steps it was 0.0915 [0.04287, 0.1489]. The rule reads this as a sign reversal, so the frozen verdict is that the primary interpretation is **invalidated**.

One honest caveat, reported as a secondary reading only: the rule takes its sign from the near-zero primary estimate. Had it used the sign of the hypothesis instead, it would have returned "qualified". Both readings agree on the substance: the answer depends on the sampling interval.

The placebo was the most informative arm. Coin-flip agents with the same aggressiveness raised VCI relative to the baseline (0.01751, [0.0135, 0.02148]), and trend followers added nothing beyond them (-0.02534, [-0.04414, -0.0002837]).

Two secondary results were clear. Less limit-order supply widened the spread by 1.632 price units [1.624, 1.641], which is close to mechanical in this model. Trend followers deepened the drawdown after a large sell shock by 0.02545 of the pre-shock price [0.01976, 0.03148]. A declared secondary outcome, spread widening after the shock, was not measured, because the protocol gave no formula for it.

## Why one interval can mislead here

Exploratory checks, run afterwards on separate seeds and never used to change a verdict, suggest why. At short intervals the statistic is dominated by the mid-price bouncing inside the spread. At long intervals, trend followers create runs of same-signed returns, and a run makes absolute returns autocorrelated whether or not volatility clusters. A single-interval comparison of chartists against noise traders can therefore mix three mechanisms.

## Limitations

One parameter set, 100 fixed-rule agents, one asset, no calibration to any market. VCI is one statistic. The comparison with real order-book data (FI-2010) is descriptive only. The primary test had low power for the effect that occurred.

## Reproduce it

Everything runs on a laptop at zero cost. Code, frozen protocols, raw results, experiment reports and the manuscript: https://github.com/mohamedbechirkefi/market-order-book-agents. Interactive page with an in-browser order-book sandbox: https://market-order-book-agents.kefimohamedbechir.workers.dev.

*AI assistance: an AI system (Claude, Anthropic) helped with code, analysis scripts and drafting, under the author's direction; it is not an author. This is an independent preprint draft, not peer-reviewed.*
