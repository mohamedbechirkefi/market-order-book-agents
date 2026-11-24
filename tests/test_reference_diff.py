# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Differential tests: the heap-based book must equal the naive reference on random op streams."""

from hypothesis import given, settings
from hypothesis import strategies as st

from market.book import BUY, SELL, OrderBook
from market.reference import ReferenceBook

op = st.one_of(
    st.tuples(st.just("L"), st.integers(0, 4), st.sampled_from([BUY, SELL]), st.integers(95, 105), st.integers(1, 6)),
    st.tuples(st.just("M"), st.integers(0, 4), st.sampled_from([BUY, SELL]), st.integers(1, 12), st.one_of(st.none(), st.integers(0, 900))),
    st.tuples(st.just("C"), st.integers(0, 40)),
)


def _fills(fs):
    return [(f.maker_oid, f.maker_owner, f.taker_owner, f.taker_side, f.price, f.qty) for f in fs]


@settings(max_examples=300, deadline=None)
@given(st.lists(op, max_size=80))
def test_book_matches_reference(ops):
    a, r = OrderBook(), ReferenceBook()
    for o in ops:
        if o[0] == "L":
            _, owner, side, price, qty = o
            fa, ra = a.submit_limit(owner, side, price, qty)
            fr, rr = r.submit_limit(owner, side, price, qty)
            assert _fills(fa) == fr
            assert (ra.oid if ra else None) == rr
        elif o[0] == "M":
            _, owner, side, qty, cap = o
            cap = cap if side == BUY else None
            fa, la = a.submit_market(owner, side, qty, cash_cap=cap)
            fr, lr = r.submit_market(owner, side, qty, cash_cap=cap)
            assert _fills(fa) == fr and la == lr
        else:
            oid = o[1]
            live = a.get(oid) is not None
            if live:
                a.cancel(oid)
                r.cancel(oid)
            else:
                assert all(x[0] != oid for x in r.resting())
        assert a.snapshot(BUY) == r.levels(BUY)
        assert a.snapshot(SELL) == r.levels(SELL)
        assert [(o.oid, o.owner, o.side, o.price, o.qty) for o in a.resting_orders()] == r.resting()
        a.check_invariants()
