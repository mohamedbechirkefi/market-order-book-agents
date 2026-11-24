<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Feasibility audit (M0, 2026-11-24)

All outputs below were produced by commands run in this session; they are copied, not paraphrased.

## 1. Hardware

| Item | Command | Output |
| --- | --- | --- |
| CPU | `sysctl -n machdep.cpu.brand_string` | `Apple M1 Pro` |
| Cores | `sysctl -n hw.ncpu` | `10` |
| Memory | `sysctl -n hw.memsize` | `17179869184` (16 GiB) |
| OS | `sw_vers` | `ProductName: macOS`, `ProductVersion: 15.3.1`, `BuildVersion: 24D70` |
| Free disk | `df -h /Users/bechir/research/labs` | `460Gi` size, `311Gi` used, `128Gi` available |

The brief stated "about 127 GB free"; the measured value is 128 GiB. Consistent.

## 2. Tools

| Tool | Location | Version check output |
| --- | --- | --- |
| Python | `/usr/local/bin/python3` | `Python 3.12.1` |
| uv | `labs/.tools/py/bin/uv` | `uv 0.9.5 (d5f39331a 2025-10-21)` |
| typst (Python package) | `labs/.tools/py` | `typst 0.15.0` (via `importlib.metadata.version`) |
| pypdf, pillow | `labs/.tools/py` | `pypdf 6.20.0 pillow 11.3.0` |
| pandoc | `labs/.tools/pandoc` | `pandoc 3.6.3` |
| Node | `helix/.tools/node/bin/node` (read-only use) | `v22.23.3` |
| git | system | `git version 2.42.1` |
| TeX | `which pdflatex xelatex lualatex tectonic` | `not found` for all four |

There is no `typst` executable in `labs/.tools/py/bin`; typst is available only as the Python package. This matches the planned toolchain.

## 3. Zero-cost publication toolchain (decision D-003)

No TeX distribution is installed and none will be bought or installed system-wide. Plan:

- Markdown is the canonical source.
- `manuscript.tex` is generated from Markdown with `pandoc -t latex -s` (source only; it is not compiled locally).
- PDFs are produced by `pandoc -t typst` followed by compilation with the `typst` Python package (`typst.compile`), and inspected with `pypdf` (page count, text extraction) and rendered pages where possible.

A toolchain smoke check was run in this session (exploratory, see `progress.md`). No PDF is committed.

## 4. Time budget

Five focused development days (planning estimate). Allocation in `roadmap.md`. If threatened, cut optional UI and EXP-003 before any control or reporting duty (master prompt sections 9 and 11.6).

## 5. Compute budget

Local only, zero cost. Pure-Python order book; expected run cost is a planning estimate (at most 10 s for 100,000 steps) to be measured in M2 before the owner freezes the protocol. Full matrix: 480 runs, parallel over up to 10 processes.

## 6. Money

Zero. No paid API, dataset, compute, hosting or service. Dependency downloads from PyPI (free) only.

## 7. Sources and data

See `literature_review.md` and `data/manifest.json`. The primary study uses synthetic data only. Real order-book data are not needed for any registered hypothesis.

## 8. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Pure-Python engine too slow | Matrix does not fit budget | Measure in M2; reduce `T` or seeds by owner decision before freeze (seeds never below 10) |
| Random-order book empties on one side | Undefined mid, degenerate runs | Initial book seeding, lifetime tuning in exploratory runs, flag rule in protocol section 7 |
| Trend agents destabilise the price to the grid boundary | Runs dominated by boundary effects | Price floor at 1 tick with rejection; boundary hits recorded; parameters tuned on seeds 1..999 only |
| VCI noisy at about 2,000 returns per run | Low power | 30 paired seeds; report `d_z` and CIs; no claim of equivalence from null |
| Confounding of trend effect with order aggressiveness | Wrong mechanism | Placebo arm, EXP-004 |
| No TeX | No LaTeX-compiled PDF | Typst route; `manuscript.tex` delivered as source |
