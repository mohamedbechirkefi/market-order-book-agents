# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Real limit-order-book data (FI-2010, CC BY 4.0) for the EXP-005 comparison.

Protocol amendment R1 (owner-approved 2026-11-24, round 2). The real data is never
fitted to: no simulation parameter is calibrated on it. It supplies reference values
of three stylized statistics (volatility clustering, realised volatility, relative
spread), estimated on the reference split (days 1..9), that the simulated EXP-001 arms
are compared with in EXP-005, and a held-out day (day 10) that tests the reference.

Everything here is a pure function of arrays, so it is tested on small synthetic
fixtures (``tests/fixtures/fi2010_synthetic.txt``), never on real rows.

File layout (Fairdata record, opened 2026-11-24): each text file is a 149-row matrix,
one column per representation (one representation per block of 10 consecutive order-book
events, Ntakaris et al., arXiv:1705.03233). Rows 1..40 hold the 10-level book in the order
ask price, ask volume, bid price, bid volume for level 1, then level 2, and so on;
rows 145..149 are labels (unused). Decimal-precision normalisation divides prices by a
power of ten, so log returns and spreads relative to the mid are unchanged by it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .metrics import acf, excess_kurtosis, vci

N_ROWS = 149
ROW_ASK1, ROW_ASKV1, ROW_BID1, ROW_BIDV1 = 0, 1, 2, 3
EVENTS_PER_ROW = 10
STATISTICS = ("vci", "realised_volatility", "mean_relative_spread", "excess_kurtosis", "return_acf1")


class RealDataError(ValueError):
    """Schema or validation failure of a real-data file (fail closed)."""


def parse_matrix(text: str) -> np.ndarray:
    """Parse a whitespace-separated FI-2010 text file into a (149, N) float array."""
    rows = [ln.split() for ln in text.splitlines() if ln.strip()]
    if len(rows) != N_ROWS:
        raise RealDataError(f"expected {N_ROWS} rows, found {len(rows)}")
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        raise RealDataError(f"ragged rows: widths {sorted(widths)}")
    try:
        return np.array(rows, dtype=np.float64)
    except ValueError as e:
        raise RealDataError(f"non-numeric value: {e}") from None


def load_matrix(path: Path) -> np.ndarray:
    """Read only the first four rows needed (level 1) plus a row count check, memory-light."""
    path = Path(path)
    keep: list[np.ndarray] = []
    n_rows = 0
    width = None
    with path.open("r", encoding="ascii") as fh:
        for line in fh:
            if not line.strip():
                continue
            if n_rows < 4:
                arr = np.array(line.split(), dtype=np.float64)
                if width is None:
                    width = arr.size
                elif arr.size != width:
                    raise RealDataError("ragged rows")
                keep.append(arr)
            n_rows += 1
    if n_rows != N_ROWS:
        raise RealDataError(f"expected {N_ROWS} rows, found {n_rows}")
    return np.vstack(keep)


@dataclass(frozen=True)
class Ingested:
    ask: np.ndarray
    bid: np.ndarray
    mid: np.ndarray
    segment: np.ndarray  # integer segment id per kept column
    counts: dict


def ingest(matrix: np.ndarray, jump_threshold: float, expected_segments: int | None = None) -> Ingested:
    """Level-1 quotes, validation, exclusions and stock-day segmentation (pure).

    Missing: a non-finite level-1 price or volume. Excluded: missing, non-positive prices,
    or a crossed or locked quote (ask <= bid). Segments: a new segment starts where the
    absolute log change of the mid between consecutive kept columns exceeds
    ``jump_threshold`` (the files concatenate stock-days whose price levels differ).
    """
    m = np.asarray(matrix, dtype=np.float64)
    if m.ndim != 2 or m.shape[0] < 4 or m.shape[1] < 2:
        raise RealDataError("matrix must have at least 4 rows and 2 columns")
    ask, askv, bid, bidv = (m[i] for i in (ROW_ASK1, ROW_ASKV1, ROW_BID1, ROW_BIDV1))
    finite = np.isfinite(ask) & np.isfinite(bid) & np.isfinite(askv) & np.isfinite(bidv)
    positive = finite & (ask > 0) & (bid > 0)
    ordered = positive & (ask > bid)
    keep = ordered
    counts = {
        "columns": int(m.shape[1]),
        "missing": int((~finite).sum()),
        "non_positive_price": int((finite & ~positive).sum()),
        "crossed_or_locked": int((positive & ~ordered).sum()),
        "kept": int(keep.sum()),
    }
    if counts["kept"] < 2:
        raise RealDataError("fewer than two valid columns")
    a, b = ask[keep], bid[keep]
    mid = (a + b) / 2.0
    jumps = np.abs(np.diff(np.log(mid))) > jump_threshold
    seg = np.concatenate([[0], np.cumsum(jumps)]).astype(np.int64)
    counts["segments"] = int(seg[-1] + 1)
    if expected_segments is not None and counts["segments"] != expected_segments:
        raise RealDataError(f"found {counts['segments']} segments, expected {expected_segments}")
    return Ingested(a, b, mid, seg, counts)


def segment_statistics(mid: np.ndarray, ask: np.ndarray, bid: np.ndarray, rows_per_return: int) -> dict:
    """Statistics of one stock-day segment, returns sampled every ``rows_per_return`` columns."""
    if rows_per_return < 1:
        raise RealDataError("rows_per_return must be >= 1")
    mid = np.asarray(mid, dtype=np.float64)
    r = np.diff(np.log(mid[::rows_per_return]))
    rel = (np.asarray(ask) - np.asarray(bid)) / mid
    return {
        "n_columns": int(len(mid)),
        "n_returns": int(len(r)),
        "n_nonzero_returns": int(np.count_nonzero(r)),
        "vci": vci(r),
        "realised_volatility": float(np.std(r, ddof=1)) if len(r) >= 2 else None,
        "excess_kurtosis": excess_kurtosis(r),
        "return_acf1": acf(r, 1),
        "mean_relative_spread": float(rel.mean()),
    }


def per_segment(ing: Ingested, rows_per_return: int, min_returns: int = 50, block_columns: int | None = None) -> list[dict]:
    """Statistics per unit; units with fewer than ``min_returns`` returns are flagged ``excluded_short``.

    With ``block_columns`` = None a unit is a whole segment (one stock). Otherwise each segment is cut,
    from its first column, into non-overlapping blocks of ``block_columns`` columns; the remainder
    shorter than a block is dropped and counted in ``dropped_columns`` of the segment's last block.
    """
    if block_columns is not None and block_columns < 2:
        raise RealDataError("block_columns must be >= 2")
    out = []
    for s in range(int(ing.segment[-1]) + 1):
        idx = np.nonzero(ing.segment == s)[0]
        if block_columns is None:
            spans, dropped = [(0, len(idx))], 0
        else:
            nb = len(idx) // block_columns
            spans = [(b * block_columns, (b + 1) * block_columns) for b in range(nb)]
            dropped = len(idx) - nb * block_columns
        for b, (lo, hi) in enumerate(spans):
            sel = idx[lo:hi]
            st = segment_statistics(ing.mid[sel], ing.ask[sel], ing.bid[sel], rows_per_return)
            st["segment"] = s
            st["block"] = b
            st["excluded_short"] = st["n_returns"] < min_returns
            if b == len(spans) - 1:
                st["dropped_columns"] = dropped
            out.append(st)
        if not spans:
            out.append({"segment": s, "block": None, "n_columns": int(len(idx)), "n_returns": 0, "excluded_short": True,
                        "dropped_columns": int(len(idx)), **{k: None for k in STATISTICS}, "n_nonzero_returns": 0})
    return out


def summarise(stats: list[dict], keys=STATISTICS) -> dict:
    """Reference values per statistic over kept segments: n, median, quartiles, min, max."""
    kept = [s for s in stats if not s.get("excluded_short")]
    out = {}
    for k in keys:
        v = np.array([s[k] for s in kept if s.get(k) is not None], dtype=np.float64)
        if v.size == 0:
            out[k] = {"n": 0, "median": None, "q25": None, "q75": None, "min": None, "max": None}
            continue
        q25, med, q75 = np.quantile(v, [0.25, 0.5, 0.75])
        out[k] = {"n": int(v.size), "median": float(med), "q25": float(q25), "q75": float(q75),
                  "min": float(v.min()), "max": float(v.max())}
    return out


def classify(ci: tuple[float, float], ref_min: float, ref_max: float) -> str:
    """Place a simulated arm's 95% CI against the real reference range [min, max].

    'inside' if the CI lies within the range, 'below' or 'above' if it lies entirely outside,
    otherwise 'overlapping'.
    """
    lo, hi = ci
    if lo > hi or ref_min > ref_max:
        raise RealDataError("intervals must be ordered")
    if lo >= ref_min and hi <= ref_max:
        return "inside"
    if hi < ref_min:
        return "below"
    if lo > ref_max:
        return "above"
    return "overlapping"


# ----- EXP-005 driver functions (config-driven; file access kept at the edges) -----

SIM_METRIC = {  # real statistic at a sampling key -> simulated per-run metric
    ("vci", "primary"): "vci", ("vci", "dt10"): "vci_dt10", ("vci", "dt200"): "vci_dt200",
    ("realised_volatility", "primary"): "realised_volatility",
    ("realised_volatility", "dt10"): "realised_volatility_dt10",
    ("realised_volatility", "dt200"): "realised_volatility_dt200",
    ("mean_relative_spread", "primary"): "mean_relative_spread",
}


def load_config(path: Path) -> dict:
    import json

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    for k in ("exp_id", "label", "protocol_path", "reference_file", "heldout_file", "jump_threshold",
              "expected_segments", "rows_per_return", "min_returns", "simulated_from", "arms", "bootstrap",
              "block_columns"):
        if k not in doc:
            raise RealDataError(f"EXP-005 config misses {k!r}")
    if not isinstance(doc["jump_threshold"], (int, float)) or doc["jump_threshold"] <= 0:
        raise RealDataError("jump_threshold must be a positive number")
    if set(doc["rows_per_return"]) != {"primary", "dt10", "dt200"}:
        raise RealDataError("rows_per_return needs primary, dt10 and dt200")
    return doc


def statistics_for_split(matrix: np.ndarray, cfg: dict, split: str) -> dict:
    """Ingest one split and compute per-segment statistics at every sampling key (pure)."""
    ing = ingest(matrix, cfg["jump_threshold"], cfg["expected_segments"][split])
    block = cfg["block_columns"].get(split)  # None = whole segment
    by_key = {key: per_segment(ing, h, cfg["min_returns"], block) for key, h in cfg["rows_per_return"].items()}
    return {"counts": ing.counts, "per_segment": by_key}


def reference_values(split_stats: dict) -> dict:
    """Reference summary per sampling key (the values written into the EXP-005 config)."""
    out = {}
    for key, segs in split_stats["per_segment"].items():
        keys = STATISTICS if key == "primary" else ("vci", "realised_volatility")
        out[key] = {"units": len(segs), "excluded_short_units": int(sum(s["excluded_short"] for s in segs)),
                    **summarise(segs, keys)}
    return out


def compare_arms(sim_docs: list[dict], reference: dict, arms: list[str], n_resamples: int, seed: int) -> list[dict]:
    """EXP-005 (b): per arm and statistic, bootstrap CI of the arm mean against the reference range."""
    from .analysis import bootstrap_mean_ci

    rows = []
    for arm in arms:
        ds = [d for d in sim_docs if d["arm"] == arm and d["status"] == "ok"]
        for (stat, key), metric in SIM_METRIC.items():
            vals = np.array([d["metrics"][metric] for d in ds if d["metrics"].get(metric) is not None], dtype=np.float64)
            ref = reference[key][stat]
            row = {"arm": arm, "statistic": stat, "sampling": key, "sim_metric": metric, "n_runs": int(vals.size),
                   "sim_mean": float(vals.mean()) if vals.size else None, "ci95_low": None, "ci95_high": None,
                   "ref_median": ref["median"], "ref_min": ref["min"], "ref_max": ref["max"], "placement": None}
            if vals.size >= 2 and ref["min"] is not None:
                lo, hi = bootstrap_mean_ci(vals, n_resamples=n_resamples, seed=seed)
                row.update(ci95_low=lo, ci95_high=hi, placement=classify((lo, hi), ref["min"], ref["max"]))
            rows.append(row)
    return rows


def heldout_check(heldout_stats: dict, reference: dict) -> dict:
    """EXP-005 (a): VCI > 0 in each held-out stock, and share of held-out values inside the reference range."""
    segs = [s for s in heldout_stats["per_segment"]["primary"] if not s["excluded_short"]]
    vci_vals = [s["vci"] for s in segs]
    out = {"n_segments": len(segs), "vci_values": vci_vals,
           "vci_positive_all": bool(segs) and all(v is not None and v > 0 for v in vci_vals), "inside_share": {}}
    for stat in ("vci", "realised_volatility", "mean_relative_spread"):
        ref = reference["primary"][stat]
        vals = [s[stat] for s in segs if s[stat] is not None]
        if ref["min"] is None:
            out["inside_share"][stat] = None
            continue
        inside = [ref["min"] <= v <= ref["max"] for v in vals]
        out["inside_share"][stat] = float(np.mean(inside)) if inside else None
    return out


__all__ = ["SIM_METRIC", "compare_arms", "heldout_check", "load_config", "reference_values", "statistics_for_split", "Ingested", "RealDataError", "classify", "ingest", "load_matrix", "parse_matrix", "per_segment",
           "segment_statistics", "summarise"]
