# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Write tests/fixtures/fi2010_synthetic.txt: SYNTHETIC rows in the FI-2010 file schema.

No real data. Three "stock-days" (segments) of 300 columns at price levels 0.30, 0.12 and
0.45 (decimal-precision scale), random-walk mids on a 0.0001 grid, spreads of 1 to 3 ticks,
and three planted bad columns: one missing (NaN), one crossed quote, one non-positive price.
Rows 5..144 are zero filler features and rows 145..149 labels in {1, 2, 3}. Deterministic (seed 7).
"""

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "fi2010_synthetic.txt"


def build() -> np.ndarray:
    rng = np.random.default_rng(7)
    cols = []
    for level in (0.30, 0.12, 0.45):
        n = 300
        ticks = np.round(level / 1e-4) + np.cumsum(rng.integers(-1, 2, size=n))
        spread = rng.integers(1, 4, size=n)
        bid = ticks * 1e-4
        ask = (ticks + spread) * 1e-4
        block = np.zeros((149, n))
        block[0], block[2] = ask, bid
        block[1], block[3] = rng.integers(1, 50, size=n) * 1e-3, rng.integers(1, 50, size=n) * 1e-3
        block[4:144] = 0.0  # filler features (unused by the study)
        block[144:149] = rng.integers(1, 4, size=(5, n))
        cols.append(block)
    m = np.hstack(cols)
    m[0, 10] = np.nan  # missing
    m[0, 20], m[2, 20] = 0.2999, 0.3001  # crossed
    m[2, 30] = -0.1  # non-positive bid
    return m


def main() -> None:
    m = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [" ".join(f"{v:.7g}" for v in row) for row in m]
    OUT.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"wrote {OUT} ({m.shape[0]} x {m.shape[1]})")


if __name__ == "__main__":
    main()
