<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# MARKET: can simple trading rules generate volatility and liquidity patterns?

**Status: M2 (core implementation) done, 2026-11-24, pending owner review. The protocol is not frozen: no confirmatory experiment has run and there are no findings.** Exploratory runs on development seeds exist only to plan the freeze.

## Question

Can simple trading rules generate volatility and liquidity patterns under explicit assumptions? The project will build a small simulated limit-order book (price-time priority, cash and inventory accounting) populated by random-order, trend-following and mean-reverting agents, and compare agent mixtures, liquidity levels and shocks against a random-order baseline.

## Why it matters

Random order flow alone already reproduces much of the behaviour of real order books in published models. Asking what simple rules add on top of that baseline, with matched random numbers and a placebo control, is a small and testable question.

## What exists now

- Control files, feasibility audit, literature and dataset audit: `research/feasibility.md`, `research/literature_review.md`, `data/manifest.json`.
- A **draft** protocol (not frozen): `research/protocol.md`, with four registered experiments in `research/experiment_registry.csv` and draft protocols in `research/experiments/EXP-001` to `EXP-004`.
- A manuscript skeleton (headings only): `research/paper/manuscript.md`.
- The simulation engine (`src/market/`): price-time-priority order book with partial fills, cash and inventory accounting, random-order, trend-following, mean-reverting and placebo agents, metrics, versioned result schemas, run manifests, a runner that refuses confirmatory configs while the protocol is unfrozen, and a report generator. Tests in `tests/`.
- Exploratory smoke and pilot outputs: `results/exploratory/` (labelled exploratory; not evidence).
- Locked dependencies: `pyproject.toml`, `uv.lock`.

## Experiments

| ID | Title | Status |
| --- | --- | --- |
| EXP-001 | Agent mixtures and volatility clustering | planned (protocol draft, awaiting owner freeze) |
| EXP-002 | Liquidity supply and spread | planned (protocol draft, awaiting owner freeze) |
| EXP-003 | Response to an exogenous sell shock | planned (protocol draft, awaiting owner freeze) |
| EXP-004 | Sensitivity analyses that could invalidate EXP-001 | planned (protocol draft, awaiting owner freeze) |

## Quick start

```
uv sync --frozen
uv run pytest
uv run python -m market.cli smoke
uv run python -m market.cli report --results results/exploratory/smoke
```

`uv run python -m market.cli run --exp EXP-001` is refused until the owner freezes the protocol.

## Scope, cost and exclusions

- Zero cost: local laptop only; no paid API, data, compute or hosting.
- Synthetic data only; no external dataset is used (see `data/manifest.json`).
- Claims boundary: no real-market predictions, trading recommendations or profitability claims. Results will hold only within the model's assumptions.

## Licence

MARKET Source-Available Non-Commercial Research License v1.0 (`LicenseRef-MARKET-NC-Research-1.0`). This is a custom, source-available licence, not an OSI-approved open-source licence. See `LICENSE`, `NOTICE.md` and `research/decision_log.md` (D-001). Third-party data and dependencies keep their own licences.

## Citation

See `CITATION.cff`.
