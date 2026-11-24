<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# results/

Machine-readable experiment outputs, written by `market.runner` and validated against `src/market/schemas/`.

- `exploratory/`: exploratory runs on development seeds (smoke and pilots). **Never evidence for a hypothesis**; every summary is labelled exploratory.
- `confirmatory/`: created only after the owner freezes the protocol. Empty until then.
- `raw/`: git-ignored scratch space for large regenerated outputs.

Each run folder holds `runs/<run_id>.json` (schema `market.run_result` 1.0.0), `run_manifest.json` (schema `market.run_manifest` 1.0.0: git revision, environment, protocol hash and freeze state, per-run runtime, peak RSS and result SHA-256), `metrics.csv`, `tables/`, `figures/`, `series/` (sampled mid for the first seed of each arm), `summary.md` and, when built, `summary.pdf`.
