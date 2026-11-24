<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# tests/

pytest and hypothesis. Run with `uv run pytest` or `uv run python -m market.cli test`.

| File | Covers |
| --- | --- |
| `test_book.py` | price-time priority, partial fills, marketable limits, market-order remainder, cash cap, cancel, invalid orders (hand-computed examples) |
| `test_reference_diff.py` | differential test of the order book against the naive `market.reference.ReferenceBook` on random operation streams (hypothesis) |
| `test_ledger.py` | settlement, reservations, self-trades, negative balances, invalid endowments |
| `test_simulate.py` | conservation and no negative balances checked at every step, bit-identical reruns, common random numbers, extreme parameters, tick grid, shock, invalid configs, property test over random configurations |
| `test_metrics.py` | autocorrelation, VCI, log returns, drawdown, kurtosis (golden values), undefined cases |
| `test_analysis_rng_agents.py` | bootstrap, d_z, Holm, seeded streams, agent rules (golden intents) |
| `test_runner_schema_cli.py` | config to results to manifest to report, serial equals parallel, freeze gate, schema failures fail closed, failed runs recorded |
| `test_smoke_import.py` | package import (M0) |
| `test_realdata.py` | FI-2010 ingestion on a SYNTHETIC fixture in the FI-2010 schema (`fixtures/fi2010_synthetic.txt`, made by `scripts/make_fi2010_fixture.py`; no real rows): parsing, missingness and exclusion counts, segmentation (fail closed), statistics, scale invariance, reference values, placement |
| `test_freeze.py` | freeze guard: frozen configs accepted, changed configs and protocols refused; the CLI path is checked with a sentinel so no test launches a confirmatory run |
