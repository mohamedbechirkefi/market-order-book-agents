# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Paired analysis across seeds (protocol section 6). The unit is one run; seeds pair arms."""

from __future__ import annotations

import math

import numpy as np


class AnalysisError(ValueError):
    pass


def paired_differences(treat: dict[int, float | None], ctrl: dict[int, float | None]) -> dict[int, float]:
    """Per-seed differences treat - ctrl over seeds present and defined in both arms."""
    out = {}
    for s in sorted(set(treat) & set(ctrl)):
        a, b = treat[s], ctrl[s]
        if a is None or b is None:
            continue
        out[s] = float(a) - float(b)
    return out


def d_z(diffs: np.ndarray) -> float | None:
    """Standardised paired effect: mean / sample SD (ddof 1). None if undefined."""
    d = np.asarray(diffs, dtype=np.float64)
    if len(d) < 2:
        return None
    sd = float(np.std(d, ddof=1))
    if sd == 0.0:
        return None
    return float(d.mean() / sd)


def bootstrap_mean_ci(x: np.ndarray, n_resamples: int = 10_000, level: float = 0.95, seed: int = 20261124) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean, resampling units with replacement, fixed seed."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or len(x) < 2:
        raise AnalysisError("need at least two independent units")
    if not (0.0 < level < 1.0) or n_resamples < 1:
        raise AnalysisError("bad level or n_resamples")
    rng = np.random.Generator(np.random.PCG64(seed))
    idx = rng.integers(0, len(x), size=(n_resamples, len(x)))
    means = x[idx].mean(axis=1)
    alpha = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [alpha, 1.0 - alpha])
    return float(lo), float(hi)


def holm(pvalues: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    m = len(pvalues)
    for p in pvalues:
        if not (0.0 <= p <= 1.0) or math.isnan(p):
            raise AnalysisError("p-values must be in [0, 1]")
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = running
    return adj


def seeds_needed(dz: float, z_alpha: float = 1.96, z_beta: float = 0.84) -> float:
    """Planning approximation ((z_alpha + z_beta) / d_z)^2 + 2 (protocol section 6)."""
    if dz == 0:
        return math.inf
    return ((z_alpha + z_beta) / abs(dz)) ** 2 + 2
