# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Validated, immutable simulation configuration.

Units: prices and cash are integers in base price units ("ticks" of the tick-1 grid);
quantities are integer units of the single asset; time is event time in steps.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields

AGENT_TYPES = ("ZI", "TF", "MR", "PA")


class ConfigError(ValueError):
    """Raised when a configuration value is missing, of the wrong type or out of range."""


def _require_int(name: str, value: object, lo: int | None = None, hi: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an int, got {type(value).__name__}")
    if lo is not None and value < lo:
        raise ConfigError(f"{name} must be >= {lo}, got {value}")
    if hi is not None and value > hi:
        raise ConfigError(f"{name} must be <= {hi}, got {value}")


def _require_prob(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number, got {type(value).__name__}")
    if not (0.0 <= float(value) <= 1.0):
        raise ConfigError(f"{name} must be in [0, 1], got {value}")


@dataclass(frozen=True)
class Composition:
    """Number of agents of each type. Agent ids are assigned in the order ZI, TF, MR, PA."""

    ZI: int = 100
    TF: int = 0
    MR: int = 0
    PA: int = 0

    def validate(self) -> None:
        for name in AGENT_TYPES:
            _require_int(f"composition.{name}", getattr(self, name), lo=0)
        if self.total < 1:
            raise ConfigError("composition must contain at least one agent")

    @property
    def total(self) -> int:
        return self.ZI + self.TF + self.MR + self.PA

    def types(self) -> list[str]:
        """Agent type per agent id (length = total)."""
        out: list[str] = []
        for name in AGENT_TYPES:
            out.extend([name] * getattr(self, name))
        return out


@dataclass(frozen=True)
class SimConfig:
    """All parameters of one simulation run except the seed.

    Defaults are the draft planning values of EXP-001 (protocol draft v0.1), not measurements.
    """

    composition: Composition = field(default_factory=Composition)
    steps: int = 100_000  # T, event-time steps
    burn_in: int = 10_000  # B, steps discarded from every metric
    sample_interval: int = 50  # dt, steps between sampled mid prices
    tick: int = 1  # price grid step (prices are multiples of tick)
    initial_price: int = 1_000  # price units
    max_order_size: int = 5  # sizes uniform on 1..max_order_size (units)
    zi_market_prob: float = 0.2  # p_mkt
    zi_limit_offset: int = 10  # delta, price units
    order_lifetime: int = 2_000  # tau, steps
    lookback: int = 500  # L, steps
    strategic_market_prob: float = 0.5  # p_mkt_tf, used by TF, MR and PA
    pa_skip_prob: float = 0.0  # PA skip probability (activity matching, EXP-004)
    initial_cash: int = 1_000_000  # price units per agent
    initial_inventory: int = 1_000  # units per agent
    initial_orders_per_side: int = 20
    shock_step: int | None = None  # EXP-003: step of the exogenous market sell, or None
    shock_fraction: float = 0.5  # share of resting bid depth sold by the shock
    shock_inventory: int = 1_000_000  # units endowed to the shock agent
    extra_vci_intervals: tuple[int, ...] = (10, 200)  # dt values for the EXP-004 reanalysis

    def validate(self) -> "SimConfig":
        if not isinstance(self.composition, Composition):
            raise ConfigError("composition must be a Composition")
        self.composition.validate()
        _require_int("steps", self.steps, lo=1)
        _require_int("burn_in", self.burn_in, lo=0)
        if self.burn_in >= self.steps:
            raise ConfigError("burn_in must be < steps")
        _require_int("sample_interval", self.sample_interval, lo=1)
        _require_int("tick", self.tick, lo=1)
        _require_int("initial_price", self.initial_price, lo=1)
        if self.initial_price % self.tick != 0:
            raise ConfigError("initial_price must be a multiple of tick")
        _require_int("max_order_size", self.max_order_size, lo=1)
        _require_prob("zi_market_prob", self.zi_market_prob)
        _require_int("zi_limit_offset", self.zi_limit_offset, lo=0)
        _require_int("order_lifetime", self.order_lifetime, lo=1)
        _require_int("lookback", self.lookback, lo=1)
        _require_prob("strategic_market_prob", self.strategic_market_prob)
        _require_prob("pa_skip_prob", self.pa_skip_prob)
        _require_int("initial_cash", self.initial_cash, lo=0)
        _require_int("initial_inventory", self.initial_inventory, lo=0)
        _require_int("initial_orders_per_side", self.initial_orders_per_side, lo=0)
        if self.initial_orders_per_side > 0 and self.composition.ZI < 1:
            raise ConfigError("initial book seeding needs at least one ZI agent")
        if self.shock_step is not None:
            _require_int("shock_step", self.shock_step, lo=1, hi=self.steps)
            _require_prob("shock_fraction", self.shock_fraction)
            _require_int("shock_inventory", self.shock_inventory, lo=0)
        if not isinstance(self.extra_vci_intervals, tuple):
            raise ConfigError("extra_vci_intervals must be a tuple")
        for v in self.extra_vci_intervals:
            _require_int("extra_vci_intervals[]", v, lo=1)
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        d["extra_vci_intervals"] = list(self.extra_vci_intervals)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        if not isinstance(d, dict):
            raise ConfigError("config must be a JSON object")
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ConfigError(f"unknown config keys: {sorted(unknown)}")
        kw = dict(d)
        if "composition" in kw:
            comp = kw["composition"]
            if not isinstance(comp, dict):
                raise ConfigError("composition must be an object")
            bad = set(comp) - set(AGENT_TYPES)
            if bad:
                raise ConfigError(f"unknown agent types: {sorted(bad)}")
            kw["composition"] = Composition(**comp)
        if "extra_vci_intervals" in kw:
            if not isinstance(kw["extra_vci_intervals"], (list, tuple)):
                raise ConfigError("extra_vci_intervals must be a list")
            kw["extra_vci_intervals"] = tuple(kw["extra_vci_intervals"])
        return cls(**kw).validate()

    def config_hash(self) -> str:
        """SHA-256 of the canonical JSON form (sorted keys, no whitespace)."""
        return sha256_json(self.to_dict())


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(obj: object) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
