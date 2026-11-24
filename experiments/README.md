<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# experiments/

Runnable experiment configurations (code side). The research-side records (protocols, reports, run manifests) live in `research/experiments/EXP-NNN/`.

`configs/` holds one JSON file per experiment:

| File | Label | Seeds | Runs |
| --- | --- | --- | --- |
| `EXP-001.json` .. `EXP-004.json` | confirmatory (draft v0.1 parameters) | 1001..1030 | refused by `market.cli run` until the owner freezes the protocol (G-FREEZE) |
| `pilot-mixtures.json` | exploratory | 1..20 | EXP-001 arms, the EXP-004 placebo arm and the tick-2 arms at full draft length |
| `pilot-liquidity.json` | exploratory | 21..30 | EXP-002 arms |
| `pilot-shock.json` | exploratory | 31..40 | EXP-003 arms |

Format: `exp_id`, `label` (`exploratory` or `confirmatory`), `protocol_path` (required when confirmatory), `seeds` (list or `{"from", "to"}`), `base` (shared `SimConfig` overrides), `arms` (per-arm overrides), `series_every` (save the mid every k steps for the first seed of each arm; 0 disables), `note`. Unknown keys are rejected.

The freeze check (`market.runner.protocol_status`): a protocol is frozen only when its row in `research/experiment_registry.csv` holds a 64-character SHA-256 equal to the hash of the protocol file. Exploratory configs may not use seeds of 1000 or more.
