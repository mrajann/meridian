"""Deterministic pseudo-randomness for the synthetic telemetry world.

Everything is a pure function of its string keys (hashed with blake2b), not of
a shared RNG's call order: the same (incident, service, metric, minute) always
yields the same value, so two queries over overlapping windows agree, tests
are reproducible, and generating one series never perturbs another.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")

_TWO_64 = float(1 << 64)


def _digest(parts: tuple) -> bytes:
    return hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=16).digest()


def unit(*parts) -> float:
    """Uniform in [0, 1)."""
    return int.from_bytes(_digest(parts)[:8], "big") / _TWO_64


def uniform(low: float, high: float, *parts) -> float:
    return low + (high - low) * unit(*parts)


def gauss(*parts) -> float:
    """Standard normal via Box-Muller from the digest's two halves."""
    digest = _digest(parts)
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (_TWO_64 + 1)  # (0, 1], keeps log() finite
    u2 = int.from_bytes(digest[8:], "big") / _TWO_64
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def choice(options: Sequence[T], *parts) -> T:
    return options[int(unit(*parts) * len(options)) % len(options)]
