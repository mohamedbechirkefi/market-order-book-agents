<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Roadmap

Five focused development days (planning estimate, master prompt section 1). Effort is in focused hours. Status values: `done`, `in progress`, `not started`, `blocked`. Section 11.6 additions are mandatory at every milestone.

| ID | Milestone | Depends on | Priority | Effort | Status | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| M0 | Bootstrap and feasibility | none | P0 | 4 h | done (2026-11-24), pending owner review of the gate | none |
| M1 | Research and preregistration | M0 | P0 | 4 h | done (2026-11-24): gate passed, protocol v1.0 frozen on the owner's approval (`research/freeze.json`, D-011) with the round-2 amendments and FI-2010 (D-009, D-010) | none (a fuller literature search on aggressiveness-matched controls remains desirable for M4) |
| M2 | Core implementation | M1 draft (not the freeze) | P0 | 10 h | done (2026-11-24), pending owner review | none |
| M3 | Experiments | M1 freeze, M2 | P0 | 5 h | done (2026-11-25): full frozen matrix, 480/480 runs, 0 failed; EXP-005 comparison; five reports (J-0005 to J-0010, D-013, D-014) | owner review of D-013 analysis choices and D-014 observations |
| M4 | Interpretation | M3 | P0 | 6 h | done (2026-11-25): confounders and exploratory sensitivity (J-0011), expected versus observed, claims register, evidence audit (J-0012), manuscript and supplement, second review pass (D-016) | none (owner ruled on D-016: release text leads with "invalidated", D-018; statements approved, D-017) |
| M5 | Interactive experience | M2 (schema), M4 (published results) | P1 | 8 h | done (2026-11-25): static page and faithful engine-port sandbox (D-019, J-0013); checker PASS; demo, paper, reports and articles print identical numbers (test) | none (owner placeholders: repository and demo URL; confirmation of funding and competing-interest statements) |
| M6 | Release candidate | M4, M5 | P0 | 3 h | release candidate prepared, awaiting owner review and G-PUBLIC (2026-11-25; D-020, J-0014) | owner approval for any publication (G-PUBLIC) |

## M0: Bootstrap and feasibility
- Control files (section 2 and 11.1 tree), feasibility audit (`research/feasibility.md`), source and licence audit (`research/literature_review.md`, `data/manifest.json`), budget (zero cost), scope and fallback, lockfile.
- 11.6 addition: registry initialised, manuscript skeleton, draft experiment protocols, zero-cost publication toolchain confirmed (D-003).
- **Acceptance:** the owner can understand the question, the cost (zero) and the exclusions from `README.md` and `research/protocol.md`.

## M1: Research and preregistration
- Evidence review extended (aggressiveness-matched or placebo controls in agent-based LOB studies; random-order LOB volatility clustering results).
- Formal model fixed with parameter values chosen on development seeds 1..999; throughput measured (needs M2 engine).
- Protocol v1.0 for EXP-001..EXP-004; fixture manifest.
- 11.6 addition: freeze confirmatory protocols before execution; record hash and owner approval in `research/decision_log.md` and the registry.
- **Acceptance:** owner-approved frozen protocol with hash; exploratory results visibly separated.
- **Status (2026-11-24):** done. Amendments A1 to A5 and R1, R2 applied (protocol section 12); FI-2010 downloaded and its reference values fitted on days 1 to 9 (J-0004); EXP-005 registered; all five protocols and configs hashed in `research/freeze.json`; the runner accepts the frozen configs and refuses changed ones (tests).

## M2: Core implementation
- Order book with price-time priority, partial fills, expiry; cash and inventory accounting; ZI, TF, MR, PA agents; seeded streams; metrics; runner; CLI (`smoke`, `run`, `report`, `test`).
- Tests: matching, partial fills, conservation, no negative balances, deterministic ordering, hand-computed examples, property tests (hypothesis), invalid inputs, extreme parameters.
- 11.6 addition: versioned JSON result schema, run manifests (runtime, peak memory, OS, CPU, package versions, git revision, config), report generators built with the core.
- **Acceptance:** all tests pass (counts recorded from actual runs); correctness before UI.
- **Status (2026-11-24):** done, pending owner review. Engine, ledger, agents, metrics, analysis helpers, schemas (`run_result` and `run_manifest` 1.0.0), runner with freeze gate, report generator (CSV tables, SVG figures, Markdown and Typst PDF summaries) and CLI implemented. Tests: 110 passed, 0 failed. Exploratory smoke run (J-0002) and pre-freeze pilot (J-0003) on development seeds; amendment proposals in `research/decision_log.md` D-007. Not done in M2: per-experiment `report.md` files (they belong to M3, after confirmatory runs).

## M3: Experiments
- Smoke matrix (exploratory), then the frozen full matrix (480 runs planned; EXP-003 optional), then EXP-005 on the EXP-001 runs (no new runs).
- 11.6 addition: each experiment's report generated as it finishes; failures and deviations recorded at once.
- **Acceptance:** complete planned matrix or documented failure; no silently dropped runs.
- **Status (2026-11-25):** done. Gate holds: complete planned matrix (EXP-001 120, EXP-002 180, EXP-003 90, EXP-004 90 runs, all `ok`, none dropped) plus EXP-005 on the EXP-001 runs. Reports in `research/experiments/EXP-00N/report.md`; raw results committed under `results/confirmatory/` with SHA256SUMS.

## M4: Interpretation
- Confounders, sensitivity (EXP-004), expected versus observed, claims register, limitations; manuscript synthesis; adversarial second review pass.
- **Acceptance:** every numerical claim maps to result id, config and figure; every external claim to a verified source.
- **Status (2026-11-25):** done. Gate holds: `scripts/m4_audit.py` traces every decimal number of the manuscript, supplement and reports to the artifact manifest (0 unmatched), raw checks pass, and every claim has a register row with result id, config hash and table or figure; external claims map to opened sources (abstract-only marked). Frozen verdicts unchanged.

## M5: Interactive experience
- Static page (TypeScript, Vite, Web Worker): interactive order book, price chart, agent composition control, seed and reset controls, published results with uncertainty clearly separated from visitor sandbox runs.
- 11.6 addition: demo, paper, reports and articles show identical verified numbers.
- **Acceptance:** offline after load, responsive, keyboard usable, reduced motion, no runtime service, no fabricated data.
- Cut first if the schedule is threatened (section 9).
- **Status (2026-11-25):** done. Gate holds: offline after the first load, responsive at 360 px, every control reachable by keyboard with a visible focus, reduced motion respected, no request leaves the local origin (`demo/tools/a11y_check.mjs`: A11Y-CHECK PASS); no fabricated data (export from committed results only, every display string printed in the manuscript, `tests/test_demo_export.py`); no runtime service (static build). The sandbox is a port of the engine, identical to the Python engine on a fixture (D-019).

## M6: Release candidate
- Clean clone, locked install, tests, smoke reproduction, demo build, manifest and link checks, secret and licence scan; PDFs compiled and inspected via Typst; owner review checklist.
- **Acceptance:** verified facts only; nothing pushed or published without the owner.
- **Status (2026-11-25):** release candidate prepared, awaiting owner review and G-PUBLIC. Clean clone of 704a568: 170 tests passed, smoke reproduced (metrics identical), demo 27 tests and A11Y-CHECK PASS, export deterministic. Seven PDFs built and inspected (`scripts/build_pdfs.py`); links, manifests, checksums, secret and licence scans done (`research/publication/reproducibility_report.md`, `release_checklist.md`, `dependency_licences.md`). Not done until the owner signs `research/publication/author_review.md` off.

## Fallbacks
- Engine too slow: reduce `T`, then seeds (never below 10), by owner decision before freeze.
- Schedule threatened: drop M5 extras, then EXP-003; never drop controls, EXP-004 or reports.
