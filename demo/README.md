<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# demo/: MARKET interactive page (M5)

A static page (TypeScript, React, Vite, Web Worker; versions pinned in `package-lock.json`, copied from the shared lab template) with:

- **Published results**, led by the frozen verdict "invalidated" (EXP-001, sign reversal under the EXP-004 robustness rule), with the reading against the sign of H1 ("qualified") marked as a secondary, exploratory reading. Every estimate and interval is printed exactly as in `research/paper/manuscript.md`; the primary contrast is -0.007825 [-0.0268, 0.01785]. Every registered experiment has a card of equal weight, and EXP-003 spread widening is shown as "not measured".
- **Charts** drawn from the exported data: the EXP-001 primary and EXP-004 components with 95% intervals, the placebo contrasts, the EXP-001 price paths of seed 1001, and the exploratory sampling-interval grid (labelled exploratory).
- **Order-book sandbox**: an interactive order book (ten best levels per side at any step), a price chart, agent composition control, liquidity, optional sell shock, seed (development seeds 1 to 999 only) and reset. It runs a TypeScript port of `src/market/` (`src/engine/`). The port is faithful: on six short development-seed runs from the Python engine (`scripts/make_demo_fixture.py`, fixture `src/engine/fixture.json`), the random streams, every mid price, the event counts and the final balances are identical, and the metrics agree within 1e-9 (`src/engine/engine.test.ts`). Sandbox output is labelled as such and never mixed with the published results.

Data: `public/data/results.json` is written by `scripts/export_demo_data.py` from committed results only; the page validates it and shows no numbers if it is missing or malformed. Nothing is collected or sent; no font, script or image is loaded from another host; the page works offline after the first load. Nothing on the page is investment advice or a claim about real markets.

## Commands

Node 22 (a local Node 22 installation on the PATH):

    cd demo && npm ci && npm run build && npm run preview
    npm test                                         # vitest: results validator and engine port
    node tools/a11y_check.mjs dist --screenshots <dir>   # offline and accessibility check (Chrome)

Regenerate the data from the repository root:

    .venv/bin/python scripts/export_demo_data.py
    .venv/bin/python scripts/make_demo_fixture.py

Public URL: https://market-order-book-agents.kefimohamedbechir.workers.dev. The page is hosted as Cloudflare Workers static assets on the free plan (`demo/wrangler.jsonc`: assets only, no Worker script, directory `./dist`). It is deployed by the coordinator, not by any script of this repository. Repository: https://github.com/mohamedbechirkefi/market-order-book-agents.

## Design and brand (owner request, 2026-11-26)

The page has its own identity, described in `DESIGN.md`: a 1980s quote board (deep green, amber figures) above a ticker-tape page, bids in blue and asks in red. The hero tape and ladder are a fixed toy drawing labelled "Illustration, not study data" and print no number. Brand files are in `public/brand/`: the mark (`market-mark-*.svg`, an M cut into five volume bars), the wordmark and lockup in ink, amber and paper, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` and the Open Graph image `og.png` (rendered from an HTML page with headless Chrome). Every animation has a reduced-motion variant.

## Third-party notes: fonts

Both fonts are self-hosted from the Fontsource npm packages (pinned in `package-lock.json`), Latin subset only, bundled into the build; nothing is loaded from another host.

| Family | Package and version | Licence | Use |
|---|---|---|---|
| Big Shoulders Display | `@fontsource-variable/big-shoulders-display` 5.3.0 | SIL Open Font License (OFL-1.1) | display type |
| Libre Franklin | `@fontsource-variable/libre-franklin` 5.3.0 | SIL Open Font License (OFL-1.1) | text and figures |
