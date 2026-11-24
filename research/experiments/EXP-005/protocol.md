<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-005: Simulated and real-market volatility, spread and clustering (FI-2010) (protocol)

**Status: v1.0, FROZEN (owner-approved 2026-11-24).** Registered by amendment R1 (`research/protocol.md` section 12), from the owner's approval of real data ("Approve all", `labs/_shared/owner-approvals-2026-11-24b.md` section 1: MARKET, FI-2010, "Compare simulated volatility, spread and clustering with a real market"). Freeze record: `research/freeze.json`. Secondary and descriptive: it never changes the EXP-001 verdict.

## 1. Question
Where do the simulated markets of EXP-001 sit relative to a real limit-order market on three stylized statistics: volatility clustering (VCI), realised volatility and relative spread? Does the real market itself show positive volatility clustering on a held-out day?

## 2. Mechanism and rationale
A random-order market reproduces much of the spread and diffusion behaviour of real books (Farmer, Patelli and Zovko 2005), and volatility clustering is a stylized fact of real returns (Cont 2001). A comparison with one real order book shows whether the simulated levels are of a plausible order and whether any arm comes closer to the real clustering. It cannot validate the model: one market, ten days, five stocks, and a crude match of event clocks.

## 3. Competing explanations and threats
1. **Clock mismatch.** A simulation step is one agent action; an FI-2010 column is 10 order-book events (submissions, cancellations, executions). The match `dt = 50` steps to `h = 5` columns is approximate. The `dt = 10`/`h = 1` and `dt = 200`/`h = 20` pairs are the sensitivity check.
2. **Price grid.** The simulation tick is 1 price unit at a price near 1,000 (about 10 basis points). The real tick is one cent on prices of a few euros to tens of euros. Relative spreads are partly mechanical consequences of the tick.
3. **Selection of the real data.** Five liquid Helsinki stocks in June 2010, 10:30 to 18:00, auction periods removed. Other markets or periods may differ.
4. **Normalisation.** Decimal-precision normalisation divides prices by a power of ten. Log returns and relative spreads are unchanged by it if ask and bid prices share the scale; the ingestion requires `ask > bid` and the per-column scale is checked in J-0004.

## 4. Hypotheses and outcomes
- **(a) Held-out real-data check (directional).** On day 10 (held-out file), VCI at `h = 5` is positive in each of the five stocks. Not supported if any stock has VCI <= 0 or undefined. Also reported: the share of day-10 stock values inside the reference range, per statistic.
- **(b) Model-to-market placement (descriptive, no H0).** For each EXP-001 arm (A0, A1, A2, A3) and each statistic (VCI, realised volatility, mean relative spread) at the primary sampling, the 95% percentile bootstrap CI of the arm mean over the 30 confirmatory seeds is placed against the reference range [min, max] of the reference split as `inside`, `overlapping`, `below` or `above`. The same placement at `dt = 10`/`h = 1` and `dt = 200`/`h = 20` for VCI and realised volatility is a sensitivity analysis.
- No statement of the form "the model matches the real market" is allowed. Placement statements hold only for this dataset, these statistics and this clock match.

## 5. Data, splits and the reference "fit"
- **Dataset.** FI-2010 (Ntakaris, Magris, Kanniainen, Gabbouj and Iosifidis, Journal of Forecasting, doi:10.1002/for.2543, arXiv:1705.03233, opened 2026-11-24; data record `https://etsin.fairdata.fi/dataset/73eb48d7-4dbc-4a10-a52a-da745b47a649`), licence CC BY 4.0. Downloaded by `scripts/download_fi2010.py`, which checks the SHA-256 of the archive against the Fairdata record. Raw files are git-ignored (archive 1.86 GB, above the 20 MB commit limit). Hashes in `data/manifest.json`.
- **Variant.** No auction period, decimal-precision normalisation, anchored fold 9. Reference split: `Train_Dst_NoAuction_DecPre_CF_9.txt` (days 1 to 9; 362,400 columns, five stock segments). Held-out split: `Test_Dst_NoAuction_DecPre_CF_9.txt` (day 10; 31,937 columns, five stock segments).
- **Method** (fixed in `research/protocol.md` section 12, R1, before any statistic was computed): ingestion and exclusions; segmentation into the five stocks by the jump threshold `J = 0.1` with a fail-closed segment count of 5 per file; reference units are non-overlapping blocks of 9,000 columns (90,000 events, the post-burn-in length of a simulated run) within each stock, remainder dropped and counted; held-out units are the five stock-days of day 10; returns every `h` columns within a unit; units with fewer than 50 returns excluded; reference values = median, quartiles, minimum and maximum over the kept reference blocks.
- **Jump threshold `J` and the revision before fitting.** The structural inspection (J-0004; validity counts and the distribution of absolute log mid changes only) found four jumps above 0.2 and none between 0.035 and 0.26, so `J = 0.1` lies in the gap. It also showed that the files are ordered by stock and that day boundaries are not identifiable, which replaced the first plan (45 stock-days) by blocks before any reference value was computed.
- **What is fitted.** Only the reference values above. No simulation parameter is calibrated on FI-2010, and the held-out day is not used for any statistic before the freeze. The primary contrast of EXP-001 plays no part in the reference values.

## 6. Unit, seeds, budget
Real side: one block of 9,000 columns in the reference split (37 blocks: 3, 6, 6, 8 and 14 per stock in file order) and one stock-day on the held-out day (5). Simulated side: one EXP-001 run; 4 arms by 30 confirmatory seeds (1001 to 1030), no new runs. Compute: seconds (one pass over a 0.9 GB text file).

## 7. Analysis plan
Implemented in `market.realdata` and `python -m market.cli realdata compare --exp EXP-005`, which refuses to run unless the EXP-005 protocol and config match the freeze record and the input results are confirmatory EXP-001 results. Bootstrap: 10,000 resamples, seed 20261124, over seeds within an arm. Outputs: `results/confirmatory/EXP-005/comparison.json`, then the report.

## 8. Exclusion, stopping, failure modes
Ingestion exclusions, dropped remainders and short units are counted and reported. If a file does not give exactly 5 segments, ingestion fails and EXP-005 is reported as failed; `J` is not retuned after the freeze. Failed or degenerate EXP-001 runs follow the shared protocol section 7; the placement uses the runs whose metric is defined, with counts reported.

## 9. Reproduction
```
python scripts/download_fi2010.py
uv run python -m market.cli realdata reference          # exploratory, reproduces the frozen reference values
uv run python -m market.cli realdata compare --exp EXP-005 --results results/confirmatory/EXP-001
```
