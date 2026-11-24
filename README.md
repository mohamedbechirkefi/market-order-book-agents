<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# MARKET: can simple trading rules generate volatility and liquidity patterns?

**Status: protocol v1.0 frozen (owner-approved 2026-11-24, `research/freeze.json`). No confirmatory experiment has run yet and there are no findings.** Exploratory runs on development seeds exist only to plan the freeze.

## Question

Can simple trading rules generate volatility and liquidity patterns under explicit assumptions? The project will build a small simulated limit-order book (price-time priority, cash and inventory accounting) populated by random-order, trend-following and mean-reverting agents, and compare agent mixtures, liquidity levels and shocks against a random-order baseline.

## Why it matters

Random order flow alone already reproduces much of the behaviour of real order books in published models. Asking what simple rules add on top of that baseline, with matched random numbers and a placebo control, is a small and testable question.

## What exists now

- Control files, feasibility audit, literature and dataset audit: `research/feasibility.md`, `research/literature_review.md`, `data/manifest.json`.
- The frozen protocol v1.0: `research/protocol.md`, with five registered experiments in `research/experiment_registry.csv` and their protocols in `research/experiments/EXP-001` to `EXP-005`; freeze record `research/freeze.json`.
- A manuscript skeleton (headings only): `research/paper/manuscript.md`.
- The simulation engine (`src/market/`): price-time-priority order book with partial fills, cash and inventory accounting, random-order, trend-following, mean-reverting and placebo agents, metrics, versioned result schemas, run manifests, a runner that refuses any confirmatory config whose protocol or config bytes differ from the freeze record, FI-2010 ingestion (`market.realdata`), and a report generator. Tests in `tests/`.
- Exploratory smoke and pilot outputs: `results/exploratory/` (labelled exploratory; not evidence).
- Locked dependencies: `pyproject.toml`, `uv.lock`.

## Experiments

| ID | Title | Status |
| --- | --- | --- |
| EXP-001 | Agent mixtures and volatility clustering | frozen (owner-approved 2026-11-24), not yet run |
| EXP-002 | Liquidity supply and spread | frozen (owner-approved 2026-11-24), not yet run |
| EXP-003 | Response to an exogenous sell shock | frozen (owner-approved 2026-11-24), not yet run; optional |
| EXP-004 | Sensitivity analyses that could invalidate EXP-001 | frozen (owner-approved 2026-11-24), not yet run |
| EXP-005 | Simulated and real-market statistics (FI-2010) | frozen (owner-approved 2026-11-24), not yet run; descriptive, no new runs |

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
- Simulated markets are the controlled part of every experiment. One real dataset, FI-2010 (CC BY 4.0, Ntakaris et al.), is used only for the descriptive comparison EXP-005; it is downloaded by `scripts/download_fi2010.py` and never committed (see `data/manifest.json`).
- Claims boundary: no real-market predictions, trading recommendations or profitability claims. Results will hold only within the model's assumptions.

## Licence

MARKET Source-Available Non-Commercial Research License v1.0 (`LicenseRef-MARKET-NC-Research-1.0`). This is a custom, source-available licence, not an OSI-approved open-source licence. See `LICENSE`, `NOTICE.md` and `research/decision_log.md` (D-001). Third-party data and dependencies keep their own licences.

## Citation

See `CITATION.cff`.
