# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""FI-2010 ingestion and EXP-005 helpers, tested on a SYNTHETIC fixture in the FI-2010 schema (no real rows)."""

import json
from pathlib import Path

import numpy as np
import pytest

from market import realdata as rd
from market.metrics import vci

FIX = Path(__file__).parent / "fixtures" / "fi2010_synthetic.txt"
CFG = {"jump_threshold": 0.2, "expected_segments": {"reference": 3, "heldout": 3},
       "block_columns": {"reference": None, "heldout": None},
       "rows_per_return": {"primary": 5, "dt10": 1, "dt200": 20}, "min_returns": 50}


@pytest.fixture(scope="module")
def matrix():
    return rd.load_matrix(FIX)


def test_fixture_schema_and_full_parse_agree(matrix):
    full = rd.parse_matrix(FIX.read_text())
    assert full.shape == (149, 900) and matrix.shape == (4, 900)
    np.testing.assert_array_equal(full[:4], matrix)


def test_ingest_counts_missing_and_exclusions(matrix):
    ing = rd.ingest(matrix, 0.2, expected_segments=3)
    c = ing.counts
    assert c == {"columns": 900, "missing": 1, "non_positive_price": 1, "crossed_or_locked": 1, "kept": 897, "segments": 3}
    assert np.all(ing.ask > ing.bid) and np.all(ing.bid > 0)
    assert [int((ing.segment == s).sum()) for s in range(3)] == [297, 300, 300]  # the three bad columns are in the first segment


def test_ingest_fails_closed_on_wrong_segment_count(matrix):
    with pytest.raises(rd.RealDataError):
        rd.ingest(matrix, 0.2, expected_segments=45)


def test_parse_rejects_bad_files():
    with pytest.raises(rd.RealDataError):
        rd.parse_matrix("1 2 3\n4 5 6\n")
    rows = ["1 2"] * 148 + ["1"]
    with pytest.raises(rd.RealDataError):
        rd.parse_matrix("\n".join(rows))
    rows = ["1 2"] * 148 + ["1 x"]
    with pytest.raises(rd.RealDataError):
        rd.parse_matrix("\n".join(rows))


def test_ingest_rejects_degenerate_input():
    with pytest.raises(rd.RealDataError):
        rd.ingest(np.full((4, 5), np.nan), 0.2)
    with pytest.raises(rd.RealDataError):
        rd.ingest(np.ones((3, 5)), 0.2)


def test_segment_statistics_hand_example():
    mid = np.array([100.0, 101.0, 100.0, 102.0, 101.0])
    ask, bid = mid + 0.5, mid - 0.5
    st = rd.segment_statistics(mid, ask, bid, rows_per_return=2)
    r = np.diff(np.log(mid[::2]))  # 100 -> 100 -> 101
    assert st["n_returns"] == 2 and st["n_nonzero_returns"] == 1
    assert st["realised_volatility"] == pytest.approx(float(np.std(r, ddof=1)))
    assert st["mean_relative_spread"] == pytest.approx(float(np.mean(1.0 / mid)))
    assert st["vci"] is None  # too few returns for lag 10


def test_vci_matches_simulation_definition(matrix):
    ing = rd.ingest(matrix, 0.2, expected_segments=3)
    sel = ing.segment == 0
    st = rd.segment_statistics(ing.mid[sel], ing.ask[sel], ing.bid[sel], 5)
    assert st["vci"] == pytest.approx(vci(np.diff(np.log(ing.mid[sel][::5]))))


def test_scale_invariance_of_decimal_precision(matrix):
    """Dividing all prices by a power of ten (decimal precision) leaves every statistic unchanged."""
    scaled = matrix.copy()
    scaled[[0, 2]] *= 1000.0
    a = rd.statistics_for_split(matrix, CFG, "reference")
    b = rd.statistics_for_split(scaled, CFG, "reference")
    for key in CFG["rows_per_return"]:
        for sa, sb in zip(a["per_segment"][key], b["per_segment"][key]):
            for k in ("vci", "realised_volatility", "mean_relative_spread"):
                if sa[k] is None:
                    assert sb[k] is None
                else:
                    assert sb[k] == pytest.approx(sa[k], rel=1e-9, abs=1e-15)


def test_reference_values_and_short_segment_exclusion(matrix):
    st = rd.statistics_for_split(matrix, CFG, "reference")
    ref = rd.reference_values(st)
    assert ref["primary"]["excluded_short_units"] == 0  # >= 297 columns / 5 = 59 returns >= 50
    assert ref["dt200"]["excluded_short_units"] == 3  # <= 300 / 20 = 14 returns < 50
    assert ref["dt200"]["vci"]["n"] == 0 and ref["dt200"]["vci"]["median"] is None
    p = ref["primary"]["mean_relative_spread"]
    assert p["n"] == 3 and p["min"] <= p["q25"] <= p["median"] <= p["q75"] <= p["max"]
    json.dumps(ref, allow_nan=False)


@pytest.mark.parametrize("ci,expected", [((0.2, 0.3), "inside"), ((0.0, 0.05), "below"), ((0.9, 1.0), "above"),
                                         ((0.05, 0.2), "overlapping"), ((0.05, 0.95), "overlapping")])
def test_classify(ci, expected):
    assert rd.classify(ci, 0.1, 0.8) == expected


def test_classify_rejects_unordered():
    with pytest.raises(rd.RealDataError):
        rd.classify((0.3, 0.2), 0.1, 0.8)


def _sim_doc(arm, seed, **m):
    return {"arm": arm, "seed": seed, "status": "ok", "metrics": m}


def test_compare_arms_and_heldout_check(matrix):
    st = rd.statistics_for_split(matrix, CFG, "reference")
    ref = rd.reference_values(st)
    rng = np.random.default_rng(0)
    docs = []
    for s in range(10):
        docs.append(_sim_doc("A0", s, vci=0.5 + 0.01 * rng.standard_normal(), vci_dt10=None, vci_dt200=None,
                             realised_volatility=1e-3, realised_volatility_dt10=None, realised_volatility_dt200=None,
                             mean_relative_spread=ref["primary"]["mean_relative_spread"]["median"]))
    rows = rd.compare_arms(docs, ref, ["A0"], n_resamples=500, seed=1)
    by = {(r["statistic"], r["sampling"]): r for r in rows}
    assert len(rows) == len(rd.SIM_METRIC)
    assert by[("mean_relative_spread", "primary")]["n_runs"] == 10
    assert by[("vci", "dt10")]["n_runs"] == 0 and by[("vci", "dt10")]["placement"] is None
    assert by[("vci", "dt200")]["placement"] is None  # no reference value at dt200 in the fixture
    chk = rd.heldout_check(st, ref)
    assert chk["n_segments"] == 3 and set(chk["inside_share"]) == {"vci", "realised_volatility", "mean_relative_spread"}
    assert chk["inside_share"]["mean_relative_spread"] == 1.0  # same data as the reference: all inside


def test_load_config_validation(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"exp_id": "EXP-005"}))
    with pytest.raises(rd.RealDataError):
        rd.load_config(p)


def test_blocks_cut_segments_and_count_remainder(matrix):
    ing = rd.ingest(matrix, 0.2, expected_segments=3)
    units = rd.per_segment(ing, 5, min_returns=10, block_columns=120)
    # segment sizes 297, 300, 300 -> 2 blocks each, remainders 57, 60, 60
    assert [(u["segment"], u["block"]) for u in units] == [(s, b) for s in range(3) for b in range(2)]
    assert all(u["n_columns"] == 120 for u in units)
    assert [u.get("dropped_columns") for u in units] == [None, 57, None, 60, None, 60]
    # a block is the same computation as on the slice
    sel = np.nonzero(ing.segment == 1)[0][120:240]
    st = rd.segment_statistics(ing.mid[sel], ing.ask[sel], ing.bid[sel], 5)
    assert units[3]["vci"] == st["vci"]


def test_blocks_longer_than_segment_yield_excluded_unit(matrix):
    ing = rd.ingest(matrix, 0.2, expected_segments=3)
    units = rd.per_segment(ing, 5, block_columns=1000)
    assert len(units) == 3 and all(u["excluded_short"] and u["block"] is None for u in units)
    assert rd.summarise(units)["vci"]["n"] == 0
    with pytest.raises(rd.RealDataError):
        rd.per_segment(ing, 5, block_columns=1)


def test_reference_split_uses_blocks(matrix):
    cfg = dict(CFG, block_columns={"reference": 100, "heldout": None})
    ref = rd.reference_values(rd.statistics_for_split(matrix, cfg, "reference"))
    assert ref["primary"]["units"] == 8  # 297 -> 2 blocks, 300 -> 3 blocks, 300 -> 3 blocks
