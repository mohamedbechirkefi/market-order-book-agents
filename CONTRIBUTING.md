<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Contributing to MARKET

MARKET is an independent, source-available research project maintained by Mohamed Bechir Kefi: agent-based market dynamics.

Technical suggestions, bug reports, reproducibility results, corrections and Pull Requests are welcome. The project is available for non-commercial research under the MARKET Source-Available Non-Commercial Research License v1.0 ([LICENSE](LICENSE)); it is not OSI-approved open-source software.

## 1. Before you start

For major changes, open an Issue first. Read `master_prompt.md`, `research/protocol.md` and `research/claims_register.csv`: frozen protocols are never changed silently, and every reported number must trace to a result file.

## 2. Pull Request requirements

- Your contribution is original or appropriately licensed, and you have the right to submit it.
- No credentials, secrets, confidential information or personal data.
- Relevant tests are included and pass; you report what you actually ran.
- Third-party dependencies and data sources are identified with their licenses.
- New files carry the header `SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0` where the format allows.
- You accept the Contributor License Agreement before your contribution is merged.

## 3. Contributor License Agreement

A recorded acceptance of [CLA.md](CLA.md) is required before merging copyrightable contributions. When you open a Pull Request, the "CLA Assistant" check comments on it; read the CLA, then post this exact comment:

    I have read the MARKET CLA v1.0 and I hereby sign it

The check records your public GitHub username and account ID, the date and the PR. You sign once. If the check does not update, comment `recheck`. Checking a box is not a signature; the comment is.

The CLA lets the maintainer use, modify, distribute, relicense and commercially exploit accepted contributions. You keep the copyright in your original contributions.

## 4. Governance

Mohamed Bechir Kefi is the project owner and lead maintainer, and the only person who can change the protected `main` branch. The maintainer decides the research direction, protocol freezes, claims, releases and licensing.

## 5. Privacy and disclosure

Never commit an e-mail address, a name or any other personal identifier in code, logs, fixtures or results. Report security issues privately through GitHub's private vulnerability reporting.

## 6. Development commands

Run from the repository root with uv (dependencies are locked in `uv.lock`):

    uv sync --frozen      # install the locked environment into .venv
    uv run pytest         # run the test suite
    uv lock               # re-lock; resolution is limited by tool.uv.exclude-newer in pyproject.toml

Research command line (M2):

    uv run python -m market.cli smoke                         # exploratory smoke matrix -> results/exploratory/smoke
    uv run python -m market.cli run --config experiments/configs/pilot-mixtures.json --workers 8
    uv run python -m market.cli run --exp EXP-001             # accepted only while the config matches research/freeze.json
    uv run python -m market.cli report --results results/exploratory/smoke --pdf
    uv run python -m market.cli test

Real data and the freeze (added 2026-11-24):

    python scripts/download_fi2010.py                          # FI-2010 into data/raw/ (git-ignored), SHA-256 checked
    uv run python -m market.cli realdata reference             # exploratory reference values (days 1..9)
    uv run python -m market.cli realdata compare --exp EXP-005 # gated on research/freeze.json
    uv run python -m market.cli report --exp EXP-002           # applies the config's excluded_from_contrasts

Demo (M5; Node 22, no runtime service):

    uv run python scripts/export_demo_data.py                  # demo/public/data/results.json from committed results
    uv run python scripts/make_demo_fixture.py                 # engine fixture for the sandbox port test
    cd demo && npm ci && npm test && npm run build && npm run preview
    node tools/a11y_check.mjs dist                             # offline and accessibility check (headless Chrome)
