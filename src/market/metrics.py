# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Per-run metrics (protocol section 5). Pure functions of recorded series.

All metrics use steps strictly after burn-in (t = B+1..T) unless stated. Undefined values
(for example an autocorrelation of a constant series) are returned as None, never as 0.
"""

from __future__ import annotations

import math

import numpy as np

from .simulate import SimOutput

VCI_MAX_LAG = 10


class MetricError(ValueError):
    """Raised on invalid metric inputs (wrong shape, non-finite or non-positive prices)."""


def sampled_log_returns(mid: np.ndarray, burn_in: int, dt: int) -> np.ndarray:
    """r_k = ln m_{B + k dt} - ln m_{B + (k-1) dt}, k = 1..floor((T - B) / dt)."""
    mid = np.asarray(mid, dtype=np.float64)
    if mid.ndim != 1:
        raise MetricError("mid must be one-dimensional")
    if dt < 1 or burn_in < 0 or burn_in >= len(mid):
        raise MetricError("need dt >= 1 and 0 <= burn_in < len(mid)")
    m = mid[burn_in::dt]
    if not np.all(np.isfinite(m)) or np.any(m <= 0):
        raise MetricError("mid prices must be finite and positive")
    return np.diff(np.log(m))


def acf(x: np.ndarray, lag: int) -> float | None:
    """Sample autocorrelation at ``lag``: sum (x_t - xbar)(x_{t+lag} - xbar) / sum (x_t - xbar)^2.

    None if the series is constant or shorter than lag + 2.
    """
    x = np.asarray(x, dtype=np.float64)
    if lag < 1:
        raise MetricError("lag must be >= 1")
    if len(x) < lag + 2:
        return None
    d = x - x.mean()
    den = float(np.dot(d, d))
    if den <= 0.0:
        return None
    return float(np.dot(d[:-lag], d[lag:]) / den)


def vci(r: np.ndarray, max_lag: int = VCI_MAX_LAG) -> float | None:
    """Volatility clustering index: mean of acf(|r|, l) for l = 1..max_lag; None if undefined."""
    vals = [acf(np.abs(r), lag) for lag in range(1, max_lag + 1)]
    if any(v is None for v in vals):
        return None
    return float(sum(vals) / max_lag)


def excess_kurtosis(r: np.ndarray) -> float | None:
    """Population (biased) excess kurtosis m4 / m2^2 - 3; None if variance is zero."""
    r = np.asarray(r, dtype=np.float64)
    if len(r) < 2:
        return None
    d = r - r.mean()
    m2 = float(np.mean(d**2))
    if m2 <= 0.0:
        return None
    return float(np.mean(d**4) / m2**2 - 3.0)


def max_drawdown(m: np.ndarray) -> float:
    """max_t (1 - m_t / max_{u <= t} m_u), a fraction in [0, 1)."""
    m = np.asarray(m, dtype=np.float64)
    if len(m) == 0:
        raise MetricError("empty series")
    if np.any(m <= 0) or not np.all(np.isfinite(m)):
        raise MetricError("prices must be finite and positive")
    peak = np.maximum.accumulate(m)
    return float(np.max(1.0 - m / peak))


def _none_if_nan(x: float) -> float | None:
    return None if (x is None or not math.isfinite(x)) else float(x)


def compute_metrics(out: SimOutput) -> tuple[dict, dict]:
    """Return (metrics, flags) for one run. Units are in the protocol section 5 table."""
    cfg = out.config
    B, dt = cfg.burn_in, cfg.sample_interval
    post = slice(B + 1, None)
    bid, ask = out.best_bid[post], out.best_ask[post]
    two_sided = (bid > 0) & (ask > 0)
    n_post = len(bid)
    r = sampled_log_returns(out.mid, B, dt)
    nonzero_returns = int(np.count_nonzero(r))
    m: dict[str, float | int | None] = {}
    m["vci"] = vci(r)
    for extra in cfg.extra_vci_intervals:
        m[f"vci_dt{extra}"] = vci(sampled_log_returns(out.mid, B, extra))
    m["realised_volatility"] = _none_if_nan(float(np.std(r, ddof=1))) if len(r) >= 2 else None
    m["excess_kurtosis"] = excess_kurtosis(r)
    m["return_acf1"] = acf(r, 1)
    spread = (ask - bid)[two_sided]
    m["mean_spread"] = float(spread.mean()) if spread.size else None
    m["mean_depth_at_best"] = float(out.depth_best[post][two_sided].mean()) if two_sided.any() else None
    m["volume_per_step"] = float(out.volume[post].sum() / n_post)
    m["max_drawdown"] = max_drawdown(out.mid[B:])
    m["one_sided_fraction"] = float(1.0 - two_sided.mean())
    sub = out.counts["submitted_post_burn_in"]
    m["rejected_fraction"] = float(out.counts["rejected_post_burn_in"] / sub) if sub else None
    m["n_returns"] = int(len(r))
    m["n_nonzero_returns"] = nonzero_returns
    m["final_mid"] = float(out.mid[-1])
    tf_act = out.counts["activations"]["TF"]
    m["tf_skip_fraction"] = float(out.counts["no_order"]["TF"] / tf_act) if tf_act else None
    # descriptive wealth by type (mark to the final mid), never framed as profitability
    last = float(out.mid[-1])
    p0 = cfg.initial_price
    init_w = cfg.initial_cash + cfg.initial_inventory * p0
    by_type: dict[str, list[float]] = {}
    for i, ty in enumerate(out.agent_types):
        if ty == "SHOCK":
            continue
        by_type.setdefault(ty, []).append(out.final_cash[i] + out.final_inventory[i] * last - init_w)
    for ty in ("ZI", "TF", "MR", "PA"):
        vals = by_type.get(ty)
        m[f"mean_wealth_change_{ty}"] = float(np.mean(vals)) if vals else None
    if out.shock is not None:
        m.update(shock_metrics(out))
    flags = {
        "one_sided_over_5pct": bool(m["one_sided_fraction"] > 0.05),
        "fewer_than_50_nonzero_returns": nonzero_returns < 50,
        "vci_undefined": m["vci"] is None,
    }
    flags["degenerate"] = bool(flags["one_sided_over_5pct"] or flags["fewer_than_50_nonzero_returns"])
    return m, flags


def shock_metrics(out: SimOutput, window: int = 5_000, recovery_cap: int = 20_000, band: float = 0.01) -> dict:
    """EXP-003 outcomes: post-shock drawdown relative to the pre-shock mid, and recovery time.

    Drawdown = max(0, 1 - min(m over the window after the shock) / pre-shock mid).
    Recovery = steps after the shock until |m / pre - 1| <= band, censored at recovery_cap.
    """
    s = out.shock
    pre = float(s["pre_shock_mid"])
    t0 = int(s["step"])
    after = out.mid[t0 : t0 + window]
    dd = max(0.0, 1.0 - float(after.min()) / pre)
    seg = out.mid[t0 : t0 + recovery_cap + 1]
    ok = np.nonzero(np.abs(seg / pre - 1.0) <= band)[0]
    # index 0 is the shock step itself (after the shock); recovery means after leaving the band
    left = np.nonzero(np.abs(seg / pre - 1.0) > band)[0]
    if left.size == 0:
        rec, censored = 0, False
    else:
        back = ok[ok > left[0]]
        if back.size:
            rec, censored = int(back[0]), False
        else:
            rec, censored = int(len(seg) - 1), True
    return {
        "shock_drawdown": dd,
        "shock_recovery_steps": rec,
        "shock_recovery_censored": censored,
        "shock_window_truncated": bool(len(after) < window),
    }
