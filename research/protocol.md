<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# MARKET research protocol

**Status: v1.0, FROZEN (owner-approved 2026-11-24).** Draft v0.1 (2026-11-24) plus the amendments in section 12, applied before the freeze. The freeze record with the SHA-256 of this file and of every confirmatory protocol and config is `research/freeze.json`. No run made before the freeze is confirmatory. Every number in this document is a planning proposal, not a measurement, unless it cites a journal entry. Any later change is dated, justified and exploratory.

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

Parameter values are fixed in each EXP protocol and in the frozen configs `experiments/configs/EXP-00N.json`.

### 3.5 Randomness

`numpy.random.SeedSequence(seed)` spawns independent named streams (activation, ZI decisions, TF/MR sizes, PA coins, shock). Arms that share a seed share the activation stream and the ZI streams: these are **common random numbers**, so arms are compared pairwise per seed.

### 3.6 Implementation rules (decision D-006, folded in by amendment A5)

These rules were chosen during implementation where the draft was silent. They are part of the frozen model.

1. **Self-trades are allowed.** An agent's market or marketable order may fill against its own resting order. Such fills are accounting-neutral and are counted in `counts.self_fills`.
2. **Market orders and resources.** A market sell is rejected when the agent's free inventory is below its size. A market buy is rejected when the agent's free cash is below the best ask; otherwise it walks the book, capped by the agent's free cash. Rejections count towards the rejected-order share.
3. **ZI limit offset.** The offset is drawn uniformly on `0..delta`. Offset 0 gives a marketable limit order: it executes against the book and rests any remainder.
4. **Empty reference side.** When the reference side is empty, ZI orders price from the last mid. TF, MR and PA limit orders go one tick inside the opposite best, or to the mid when both sides are empty. Prices snap to the grid away from crossing and never go below one tick (price floor).
5. **Initial book.** 20 limit orders per side, owned by ZI agents drawn from the `init` stream, at 1..delta ticks from the initial price.
6. **Random streams.** One `SeedSequence(seed)` is spawned into six named streams: activation, zi, strategic (TF and MR), pa, shock and init. Each rule draws a fixed number of uniforms per activation, so arms sharing a seed share the activation sequence (common random numbers).
7. **Signals.** The TF signal compares the current mid with the recorded mid `L` steps earlier. The MR moving average is the mean of the last `L` recorded mids (fewer at the start of a run).
8. **Sampling-interval reanalysis.** The EXP-004 `dt` reanalysis is computed at run time (`vci_dt10`, `vci_dt200`, and for EXP-005 `realised_volatility_dt10`, `realised_volatility_dt200`), so that no full-resolution series must be stored.

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
| Mean relative spread (amendment R2, for EXP-005) | mean over two-sided steps of `(ask - bid) / ((ask + bid) / 2)` | fraction of the mid |
| Realised volatility at `dt` 10 and 200 (amendment R2, for EXP-005) | sample SD of log returns sampled every 10 or 200 steps | log-return per `dt` steps |
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
- **Pre-declared degenerate cell (amendment A1).** The EXP-002 low-liquidity ZI+TF arm (`low-ZI+TF`, ZI market-order probability 0.35) was flagged in 10 of 10 development seeds (journal J-0003). It is run and reported in full (metrics, flags, per-seed values) but excluded from every EXP-002 contrast. This exclusion is fixed before any confirmatory run and does not depend on its confirmatory flag rate.
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
| EXP-005 Real-market comparison (FI-2010) | EXP-001 arms against real reference values | uses the EXP-001 runs | 0 new runs |
| **Total** | | | **480 runs** |

EXP-003 stays optional (amendment A3): it is frozen with the others and is the first experiment cut if the schedule is threatened; if cut, it gets an "abandoned" report and is never silently dropped.

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
python scripts/download_fi2010.py                       # FI-2010 raw files into data/raw/ (git-ignored)
uv run python -m market.cli realdata reference          # reference values from days 1..9 (done before the freeze, J-0004)
uv run python -m market.cli realdata compare --exp EXP-005 --results results/confirmatory/EXP-001
```

## 12. Amendments before freeze (owner-approved 2026-11-24, round 2)

Source: the owner's answers "yes for all others" (amendments) and "Approve all" (real data), recorded in `labs/_shared/owner-approvals-2026-11-24b.md`, sections 1 and 7, MARKET rows. Applied on 2026-11-24 before any confirmatory run. Decision log D-009 (real data) and D-010 (amendments). Draft v0.1 is in git history (commit `c1369b2`).

### R1. How the real data enters the study (FI-2010)

- **Dataset.** FI-2010, "Benchmark Dataset for Mid-Price Forecasting of Limit Order Book Data with Machine Learning Methods" (Ntakaris, Magris, Kanniainen, Gabbouj and Iosifidis), NASDAQ Nordic (Helsinki), five stocks, ten trading days in June 2010, 10:30 to 18:00, one representation per block of 10 order-book events. Licence CC BY 4.0. Source, hashes and access date are in `data/manifest.json`. Variant used: no auction period, decimal-precision normalisation, anchored fold 9 (training file: days 1 to 9; testing file: day 10). Only the level-1 ask and bid prices and volumes (rows 1 to 4) are read. Decimal-precision normalisation divides prices by a power of ten, which leaves log returns and relative spreads unchanged.
- **Role: comparison, not calibration.** No simulation parameter is fitted to FI-2010. The approved role is to "compare simulated volatility, spread and clustering with a real market". Fitting the simulation to the data and then comparing it with the same data would be circular. All simulation parameters keep their frozen values.
- **What is estimated before the freeze ("fit").** Real-market reference values of three statistics, estimated on the **reference split** (training file, days 1 to 9): VCI, realised volatility and mean relative spread (excess kurtosis and `acf(r, 1)` descriptive). Method, fixed here before any statistic was computed:
  1. Ingestion (`market.realdata.ingest`): a column is missing if a level-1 price or volume is not finite, and excluded if missing, if a price is not positive, or if the quote is crossed or locked (ask <= bid). Counts of each are recorded.
  2. Segmentation into stocks: each file concatenates the five stocks, each with its own price level. A new segment starts where the absolute log change of the mid between consecutive kept columns exceeds the jump threshold `J = 0.1` (a 10% jump). The rule fails closed unless it finds exactly 5 segments in each file.
  3. Units. Reference split: each stock segment is cut, from its first column, into non-overlapping blocks of 9,000 columns (90,000 events, the post-burn-in length of one simulated run, 90,000 steps); the remainder shorter than a block is dropped and counted. Held-out day: one unit per stock (the whole day, shorter than a block).
  4. Returns: `r_k = ln m_{(k) h} - ln m_{(k-1) h}` within a unit, sampled every `h` columns. Event matching: one simulation step is one agent action and one FI-2010 column is 10 events, so the primary `dt = 50` steps matches `h = 5` columns (1,800 returns per block, as in a simulated run); `dt = 10` matches `h = 1` and `dt = 200` matches `h = 20` (sensitivity).
  5. Per unit: VCI (lags 1 to 10 of `|r|`, as in section 5), realised volatility (SD of `r`), mean relative spread (mean of `(ask - bid) / mid` over kept columns), excess kurtosis, `acf(r, 1)`. A unit with fewer than 50 returns is excluded and counted.
  6. Reference values per statistic: median, quartiles, minimum and maximum over the kept reference blocks. These are written into `experiments/realdata/EXP-005.json` and journaled as exploratory (J-0004).
  - **Revision before fitting (recorded in J-0004).** The first version of this method assumed the files could be cut into 45 stock-days. A structural inspection of the reference file, which computed only validity counts and the distribution of absolute log mid changes and no statistic of steps 4 and 5, showed exactly four jumps above 0.2 (0.974, 0.731, 0.334, 0.265) and none between 0.035 and 0.26: the files are ordered by stock, then by day, and day boundaries inside a stock are not identifiable from prices (the files carry no timestamps). Steps 2 and 3 were therefore revised to stock segments and fixed-length blocks before any reference value was computed. Blocks can contain an overnight return at an unknown position; this is a stated limitation.
- **Primary contrast untouched.** The estimation uses only FI-2010 data. It reads no simulated output, and the EXP-001 primary contrast (A1 minus A0 VCI) plays no part in it.
- **Second test (EXP-005).** (a) Held-out check of the reference, on day 10 (testing file), not read for statistics before the freeze (only its validity and segment counts were computed): VCI is positive in each of the five stocks, and the share of day-10 stock values inside the reference range is reported per statistic. (b) Model-to-market comparison: for each EXP-001 arm (confirmatory seeds 1001 to 1030), the 95% percentile bootstrap CI of the arm mean of VCI, realised volatility and mean relative spread is placed against the reference range as inside, overlapping, below or above. This is descriptive and secondary. It never changes the EXP-001 verdict and is never read as validation of the model against a real market. Details in `experiments/EXP-005/protocol.md`.

### R2. Metrics added for the comparison

`mean_relative_spread`, `realised_volatility_dt10` and `realised_volatility_dt200` are added to the per-run metrics (section 5 table). They are secondary and descriptive and do not change any existing metric.

### Section 7 amendments (MARKET row)

- **A1. Degenerate low-liquidity cell reported but excluded.** See section 7. EXP-002 contrasts exclude `low-ZI+TF`; the interaction contrast on VCI is computed at medium versus high liquidity only, and the `low-ZI+TF` arm is reported descriptively.
- **A2. Thirty seeds.** Confirmed: 30 seeds per arm, 1001 to 1030, as in section 6 (D-007 item 2 resolved without change).
- **A3. EXP-003 stays optional.** See section 8.
- **A4. Placebo matching confirmed.** PA activity is matched to the tick-1 A1 arm. The development measurement of the TF skip fraction in A1 is 0.45% (J-0003), below the 5% threshold, so `pa_skip_prob = 0` is fixed in the frozen EXP-004 config. The confirmatory A1 skip fraction is reported; if it exceeds 5%, that is reported as a limitation of the placebo match, and the frozen config is not changed. Tick-2 arms contain no PA agents and need no matching.
- **A5. D-006 folded into the protocol.** Section 3.6.

### Not applied

D-007 items 1 (measured compute budget) and 6 (no change) were not in the approved list and are not applied as amendments; the measured budget is in journal J-0003.
