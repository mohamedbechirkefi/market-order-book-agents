# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""M0 exploratory smoke test: the package imports and numpy resolves from the lockfile."""

import numpy as np

import market


def test_package_imports():
    assert market.__version__ == "0.0.0"


def test_numpy_seeded_rng_is_deterministic():
    a = np.random.default_rng(np.random.SeedSequence(1)).integers(0, 1000, 5)
    b = np.random.default_rng(np.random.SeedSequence(1)).integers(0, 1000, 5)
    assert (a == b).all()
