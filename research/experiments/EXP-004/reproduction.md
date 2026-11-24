<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# EXP-004 reproduction

```
/Users/bechir/research/labs/.tools/py/bin/uv sync --frozen --all-groups --all-extras
.venv/bin/python -m pytest
.venv/bin/python -m market.cli run --exp EXP-004 --workers 2
.venv/bin/python -m market.cli report --exp EXP-004 --control A0-tick2
.venv/bin/python -m market.frozen_analysis --exp EXP-004
.venv/bin/python scripts/write_m3_reports.py
```

Raw results: [`results/confirmatory/EXP-004/`](../../../results/confirmatory/EXP-004/) (schema `market.run_result` 1.0.0 per run, `run_manifest.json`, `metrics.csv`, `analysis.json`, tables, figures); checksums in `SHA256SUMS` there. The simulation is deterministic given the seed and the code revision: a rerun at the recorded revision reproduces each run's metrics exactly (the smoke check in J-0005 reproduced J-0002 bit for bit).

Verified references used in this report are listed in `research/literature_review.md` (sources opened 2026-11-24).
