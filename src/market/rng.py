# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Seeded, named random streams.

``numpy.random.SeedSequence(seed)`` is spawned into one child per named stream, in a fixed
order. Arms that share a seed therefore share every stream (common random numbers).
Uniforms are drawn in blocks for speed; the value sequence of a stream depends only on
the seed and the stream name, not on the block size.
"""

from __future__ import annotations

import numpy as np

STREAM_NAMES = ("activation", "zi", "strategic", "pa", "shock", "init")


class Stream:
    """Buffered U[0, 1) stream from one numpy Generator (PCG64)."""

    __slots__ = ("_gen", "_buf", "_i", "_block", "drawn")

    def __init__(self, seed_seq: np.random.SeedSequence, block: int = 4096):
        self._gen = np.random.Generator(np.random.PCG64(seed_seq))
        self._block = block
        self._buf: list[float] = []
        self._i = 0
        self.drawn = 0

    def uniform(self) -> float:
        if self._i >= len(self._buf):
            self._buf = self._gen.random(self._block).tolist()
            self._i = 0
        u = self._buf[self._i]
        self._i += 1
        self.drawn += 1
        return u

    def integer(self, n: int) -> int:
        """Uniform integer on 0..n-1 from one uniform draw."""
        if n < 1:
            raise ValueError("n must be >= 1")
        k = int(self.uniform() * n)
        return k if k < n else n - 1


def make_streams(seed: int) -> dict[str, Stream]:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError(f"seed must be a non-negative int, got {seed!r}")
    children = np.random.SeedSequence(seed).spawn(len(STREAM_NAMES))
    return {name: Stream(child) for name, child in zip(STREAM_NAMES, children)}
