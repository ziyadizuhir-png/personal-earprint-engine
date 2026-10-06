"""Stable production facade over the locked robust-target mathematics."""
from __future__ import annotations

from engine.v44.v44 import *  # noqa: F401,F403 - compatibility facade for the frozen math


def generate_robust_target(base_target: Curve, iems: Sequence[IEMInput], sample_rate_hz: float = 48000.0) -> V44Result:
    """Build one Robust Target; no target mode or device PEQ output is produced."""
    return generate(base_target, iems, "robust_target", sample_rate_hz=sample_rate_hz)
