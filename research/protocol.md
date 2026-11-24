<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# MARKET research protocol

**Status: DRAFT v0.1 (2026-11-24). NOT FROZEN.** Freezing is the owner's decision (gate G-FREEZE). No run made before the freeze is confirmatory. Every number in this document is a planning proposal, not a measurement, unless it cites a journal entry.

The feasibility audit is in [`feasibility.md`](feasibility.md). Per-experiment protocols are in [`experiments/`](experiments/). The registry is [`experiment_registry.csv`](experiment_registry.csv).

## 1. Research question

Master prompt, section 10: *Can simple trading rules generate volatility and liquidity patterns under explicit assumptions?*

Operational version used here: in a simulated continuous double auction with price-time priority, cash and inventory constraints and a fixed order-arrival process, does replacing a share of random-order ("zero-intelligence") traders by trend-following traders change the volatility clustering of mid-price returns, and how do agent mixtures, liquidity supply and an exogenous shock change spread, volume, volatility and drawdowns?

The scope is a synthetic model. Results hold only within its assumptions. No statement about real markets, prediction, trading advice or profitability is in scope (section 10, claims boundary).

## 2. Background that motivates the hypothesis

Sources actually opened are listed in [`literature_review.md`](literature_review.md).

- Random order flow in a continuous double auction already reproduces much of the spread and price-diffusion behaviour of real order books (Farmer, Patelli and Zovko 2005; Smith et al. 2003). A random-order market is therefore the natural null model and the simplest baseline.
- In an order-driven model with fundamentalist, chartist and noise components, the chartist component was reported as the main source of fat tails and clustering (Chiarella, Iori and Perello 2009).
- Volatility clustering is one of the stylized facts catalogued by Cont (2001).

The narrow contribution proposed: a small, fully tested, reproducible order-book simulation that measures the volatility-clustering effect of trend followers against a random-order baseline with matched random numbers, and that includes a placebo arm separating the trend feedback from the mere increase in aggressive order flow. This is a replication-style study at small scale, not a novelty claim.

## 3. Formal model (draft)

### 3.1 Market mechanism

- One asset, integer price grid in ticks (tick size 1 in the primary configuration).
- Continuous double auction, one order book, **price-time priority**: better price first, then earlier arrival (a strictly increasing sequence number).
- Order types: limit (with price and size) and market (size only). Market orders walk the book and may be **partially filled**; any unfilled remainder of a market order is cancelled, not rested. A marketable limit order executes against the book up to its limit, and its remainder rests.
- Each resting limit order expires after a fixed lifetime of `tau` steps (cancellation mechanism).
- Trade price is the resting order's price.
- No fees, no latency, no hidden orders.

### 3.2 Time and activation

Event time. At each step `t = 1..T` one agent is drawn uniformly at random and acts once. The first `B` steps are burn-in and are discarded from every metric.

### 3.3 Accounting

Each agent has cash `c_i >= 0` and inventory `q_i >= 0` (no short selling, no borrowing). An order is accepted only if its worst-case cost is covered: a buy limit reserves `price * size` cash, a sell limit reserves `size` units; a market buy may consume only the agent's free cash and stops when it is exhausted. Totals `sum_i c_i` and `sum_i q_i` are conserved exactly by every trade (integer arithmetic, ticks and units).

### 3.4 Agents

All agents share the same order-size distribution (uniform integer on `1..s_max`) and the same activation probability. Only the decision rule differs.

| Agent | Rule (draft) |
| --- | --- |
| Noise / random-order (ZI) | With probability `p_mkt` sends a market order, side buy or sell with probability 1/2; otherwise a limit order on a random side at an offset drawn uniformly in `0..delta` ticks behind the best opposite quote (the book is seeded at start so both sides exist). |
| Trend follower (TF) | Signal `s = sign(m_t - m_{t-L})` on the mid-price `m`. If `s = 0` it sends nothing. Otherwise it sends, in the direction `s`, a market order with probability `p_mkt_tf`, else a limit order at the best quote on its side. |
| Mean reverter (MR) | Signal `s = -sign(m_t - MA_L(m)_t)`, same order rule as TF. |
| Placebo aggressive (PA) | Same order-type and size distribution as TF, but the direction is a fair coin, independent of prices. Used to separate feedback from aggressiveness (EXP-004). |

Parameter values are fixed in each EXP protocol and will be finalised, with measured throughput, before the owner freezes the protocol.

### 3.5 Randomness

`numpy.random.SeedSequence(seed)` spawns independent named streams (activation, ZI decisions, TF/MR sizes, PA coins, shock). Arms that share a seed share the activation stream and the ZI streams: these are **common random numbers**, so arms are compared pairwise per seed.

## 4. Hypotheses (EXP-001, the confirmatory test)

Let `VCI` be the volatility clustering index of one run (definition in section 5). Let `D_s = VCI(A1, seed s) - VCI(A0, seed s)`, where A0 is the random-order baseline and A1 replaces 30% of ZI agents by trend followers, all else equal.

- **H0:** the mean paired difference `E[D] = 0`.
- **H1 (directional):** `E[D] > 0`; trend followers increase volatility clustering relative to the random-order baseline.
- **Disconfirmation:** H1 is not supported if the 95% bootstrap confidence interval of mean `D` includes 0 or lies below 0. A CI entirely below 0 contradicts H1. A CI including 0 is reported as inconclusive, never as equivalence.
- **Interpretation guard:** even if H1 is supported, the feedback interpretation is invalidated if the placebo arm of EXP-004 produces a paired increase of similar size (section 9).

## 5. Metrics

Mid-price `m_t = (best bid + best ask) / 2` in ticks; when one side is empty, `m_t` carries the last defined value and the step is counted as one-sided. Returns are sampled every `dt` steps after burn-in: `r_k = ln m_{B + k dt} - ln m_{B + (k-1) dt}`.

**Primary metric (one).** Volatility clustering index:

`VCI = (1/10) * sum_{l=1..10} acf(|r|, l)`

the mean sample autocorrelation of absolute returns over lags 1 to 10 (dimensionless), per run. Direction: higher means more clustering. Justification: it is the one outcome in the list (returns, volatility, spread, volume, drawdowns) that is a *pattern* rather than a level, it is a recognised stylized fact (Cont 2001), and it is the outcome the trend mechanism is claimed to affect (Chiarella, Iori and Perello 2009). Levels of volatility and spread respond mechanically to the share of market orders, which the placebo arm controls.

**Secondary metrics** (per run, post burn-in):

| Metric | Formula | Unit |
| --- | --- | --- |
| Realised volatility | sample standard deviation of `r_k` | log-return per `dt` steps |
| Excess kurtosis | sample excess kurtosis of `r_k` | dimensionless |
| Return autocorrelation | `acf(r, 1)` | dimensionless |
| Mean quoted spread | mean over steps of `ask - bid` when both sides exist | ticks |
| Depth at best | mean of (size at best bid + size at best ask) | units |
| Volume | total traded units / post-burn-in steps | units per step |
| Maximum drawdown | `max_t (1 - m_t / max_{u<=t} m_u)` | fraction |
| One-sided fraction | share of steps with an empty side | fraction |
| Rejected orders | share of submitted orders rejected for lack of cash or inventory | fraction |
| Wealth dispersion by agent type | final mark-to-mid wealth per type, descriptive only, never framed as profitability | ticks |

## 6. Design

- **Experimental unit:** one simulation run (one arm, one seed). Steps and returns within a run are correlated and are never treated as independent observations.
- **Seeds:** 30 per arm (above the minimum of 5), seeds 1001..1030 for confirmatory runs. Smoke runs and development use seeds 1..999 only; seeds 1001..1030 are not run before the freeze.
- **Pairing:** common random numbers across arms; analysis on per-seed paired differences.
- **Sample-size rationale:** for a paired design the number of seeds needed for 80% power at two-sided alpha 0.05 is approximately `((1.96 + 0.84) / d_z)^2 + 2`. Thirty seeds detect a standardised paired effect `d_z` of about 0.53. Runs are cheap, so 30 is affordable; the value is fixed in advance and not adapted to results. If the M2 throughput measurement shows 30 seeds per arm does not fit the budget, the owner decides any reduction before the freeze (never below 10).
- **Uncertainty:** 95% percentile bootstrap CI of the mean paired difference over seeds, 10,000 resamples, fixed bootstrap seed; effect size `d_z`; per-seed values and distributions always shown.
- **Multiplicity:** only the EXP-001 primary contrast is confirmatory. Declared secondary contrasts in EXP-001 to EXP-003 are reported with Holm-adjusted intervals within each experiment and labelled secondary.
- **Compute budget:** local laptop only, zero cost. Planning target (to be measured in M2): at most 10 seconds per run of `T = 100,000` steps, so the full matrix (section 8) stays under about two hours on 10 cores.

## 7. Exclusion and stopping rules

- **No optional stopping.** All planned seeds run; the analysis happens once the matrix is complete.
- **Invariant failure:** any run that violates conservation of cash or inventory, produces a negative balance, or breaks price-time priority invalidates the code revision. All runs of that revision are discarded (and journaled), the bug is fixed and tested, and the whole matrix reruns. Such a failure is a finding to record.
- **Degenerate runs:** a run whose one-sided fraction exceeds 5% after burn-in, or with fewer than 50 non-zero returns, is flagged. The primary analysis includes all runs; a sensitivity analysis excludes flagged runs and their paired partners. Flag counts are reported.
- **Crashes:** a run that crashes is recorded with its error; it is rerun once on the same seed after a fix only if the cause is a bug, and the incident is reported.

## 8. Matrices

**Smoke matrix (exploratory, M3 start):** arms A0 and A1, 5 seeds (1..5), `T = 10,000`, `B = 1,000`. Purpose: validate the pipeline, schemas and metric code. Never used for inference.

**Full matrix (confirmatory after freeze):**

| EXP | Arms | Seeds | Runs |
| --- | --- | --- | --- |
| EXP-001 Agent mixtures | A0 ZI, A1 ZI+TF, A2 ZI+MR, A3 ZI+TF+MR | 30 | 120 |
| EXP-002 Liquidity | 3 liquidity levels x {ZI, ZI+TF} | 30 | 180 |
| EXP-003 Shock | {ZI, ZI+TF, ZI+MR} with one shock | 30 | 90 |
| EXP-004 Sensitivity | placebo arm; tick size x2; reanalysis at `dt` in {10, 200} | 30 | 90 new runs plus reanalysis |
| **Total** | | | **480 runs** |

## 9. Sensitivity analyses that could invalidate the main interpretation (EXP-004)

1. **Placebo aggressiveness.** Trend followers change two things at once: they add price feedback and they change the mix of aggressive orders. Arm A4 replaces TF by PA agents with the same order-type and size distribution but price-independent direction. If `VCI(A4) - VCI(A0)` is of similar size to `VCI(A1) - VCI(A0)` (the A1 minus A4 CI includes 0), the clustering cannot be attributed to the trend rule.
2. **Sampling interval.** The VCI contrast is recomputed at `dt = 10` and `dt = 200`. A sign change across intervals means the result is an artefact of the sampling choice.
3. **Tick size.** Coarser grid (tick 2) for A0 and A1. A disappearing effect would indicate dependence on discreteness.
4. **Degenerate-run exclusion** (section 7).

## 10. Confounders and threats noted at draft time

Market-order share; the number of active liquidity providers (replacing ZI agents also removes limit orders); order lifetime; burn-in length; initial book seeding; event-time versus clock-time sampling; integer price effects at low prices. The full list is in [`limitations.md`](limitations.md).

## 11. Reproducibility commands (implemented in M2; `run --exp` refuses until the freeze)

```
uv sync --frozen
uv run pytest
uv run python -m market.cli smoke
uv run python -m market.cli run --exp EXP-001
uv run python -m market.cli report --exp EXP-001
```

## 12. Amendments

None applied. Any change after the freeze will be dated, justified and labelled exploratory.

Pre-freeze proposals from the M2 exploratory pilot (journal J-0003) are listed in `decision_log.md` D-007 and await the owner's decision; implementation choices where this draft was silent are in D-006. Neither is applied to this text.
