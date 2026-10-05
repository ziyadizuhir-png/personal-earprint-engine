"""Locked, auditable V4.4 Earprint calculations.

This module deliberately does not import the legacy engine.  V4.4 owns its
master grid, 1 kHz anchor, PEQ reconstruction, and two-mode target contract.
The robustness/classification formulas not present in the V4.4 specification
are typed extension points and remain unresolved instead of being guessed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Callable, Literal, Sequence

import numpy as np

AnchorHz = 1000.0
ConsensusEpsilonDb = 0.25
TargetMode = Literal["robust_target", "pure_earprint"]


@dataclass(frozen=True)
class Curve:
    frequency_hz: list[float]
    level_db: list[float]

    def array(self) -> tuple[np.ndarray, np.ndarray]:
        f = np.asarray(self.frequency_hz, dtype=float)
        y = np.asarray(self.level_db, dtype=float)
        if f.ndim != 1 or y.ndim != 1 or f.size != y.size or f.size < 2:
            raise ValueError("curve must contain matching one-dimensional arrays")
        if not np.all(np.isfinite(f)) or not np.all(np.isfinite(y)) or np.any(f <= 0):
            raise ValueError("curve contains invalid values")
        if np.any(np.diff(f) <= 0):
            raise ValueError("frequency values must be strictly ascending")
        return f, y

    @classmethod
    def from_arrays(cls, f: np.ndarray, y: np.ndarray) -> "Curve":
        return cls(f.astype(float).tolist(), y.astype(float).tolist())


@dataclass(frozen=True)
class IEMInput:
    id: str
    original_measurement: Curve
    prepared_measurement: Curve
    peq_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PEQFilter:
    kind: Literal["PK", "HS", "LS"]
    frequency_hz: float
    gain_db: float
    q: float


@dataclass
class V44Result:
    mode: TargetMode
    master_grid_hz: list[float]
    base_target: Curve
    normalized_base_target: Curve
    per_iem: dict[str, dict[str, Curve]]
    personal_delta: dict[str, Curve]
    median_delta: Curve
    mad: Curve
    n_plus: list[int]
    n_minus: list[int]
    n_zero: list[int]
    # These are intentionally optional: V4.4 does not currently lock them.
    G: Curve | None = None
    C: Curve | None = None
    broad: Curve | None = None
    local: Curve | None = None
    feature_classification: list[str] | None = None
    delta_safe: Curve | None = None
    final_target: Curve | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interpolate_log(f_src: np.ndarray, y_src: np.ndarray, f_dst: np.ndarray) -> np.ndarray:
    """Linear interpolation over log(f), with no extrapolation."""
    if f_dst[0] < f_src[0] or f_dst[-1] > f_src[-1]:
        raise ValueError("source curve does not cover destination grid")
    return np.interp(np.log(f_dst), np.log(f_src), y_src)


def normalize_at_1000(f: np.ndarray, y: np.ndarray) -> np.ndarray:
    return y - float(np.interp(math.log(AnchorHz), np.log(f), y))


_FILTER_RE = re.compile(
    r"(?:Filter\s*\d+\s*:\s*)?(PK|HS|LS)\s*(?:Fc\s*)?([0-9.]+)\s*(?:Hz)?\s*(?:Gain\s*)?([-+]?[0-9.]+)\s*(?:dB)?\s*(?:Q\s*)?([0-9.]+)", re.I
)


def parse_peq(text: str | Sequence[PEQFilter]) -> list[PEQFilter]:
    if not isinstance(text, str):
        return list(text)
    filters: list[PEQFilter] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "//", ";")):
            continue
        m = _FILTER_RE.search(line)
        if not m:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 4 and parts[0].upper() in {"PK", "HS", "LS"}:
                filters.append(PEQFilter(parts[0].upper(), float(parts[1]), float(parts[2]), float(parts[3])))
            continue
        filters.append(PEQFilter(m.group(1).upper(), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return filters


def _biquad_response(filter_: PEQFilter, f: np.ndarray, sample_rate_hz: float) -> np.ndarray:
    A = 10.0 ** (filter_.gain_db / 40.0)
    w0 = 2.0 * np.pi * filter_.frequency_hz / sample_rate_hz
    alpha = np.sin(w0) / (2.0 * filter_.q)
    c, s = np.cos(w0), np.sin(w0)
    if filter_.kind == "PK":
        b0, b1, b2 = 1 + alpha*A, -2*c, 1 - alpha*A
        a0, a1, a2 = 1 + alpha/A, -2*c, 1 - alpha/A
    elif filter_.kind == "HS":
        b0, b1, b2 = A*((A+1)+(A-1)*c+2*np.sqrt(A)*alpha), -2*A*((A-1)+(A+1)*c), A*((A+1)+(A-1)*c-2*np.sqrt(A)*alpha)
        a0, a1, a2 = (A+1)-(A-1)*c+2*np.sqrt(A)*alpha, 2*((A-1)-(A+1)*c), (A+1)-(A-1)*c-2*np.sqrt(A)*alpha
    else:
        b0, b1, b2 = A*((A+1)-(A-1)*c+2*np.sqrt(A)*alpha), 2*A*((A-1)-(A+1)*c), A*((A+1)-(A-1)*c-2*np.sqrt(A)*alpha)
        a0, a1, a2 = (A+1)+(A-1)*c+2*np.sqrt(A)*alpha, -2*((A-1)+(A+1)*c), (A+1)+(A-1)*c-2*np.sqrt(A)*alpha
    z = np.exp(-1j * 2.0 * np.pi * f / sample_rate_hz)
    h = (b0 + b1*z + b2*z*z) / (a0 + a1*z + a2*z*z)
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-300))


def reconstruct_peq(filters: Sequence[PEQFilter], f: np.ndarray, sample_rate_hz: float = 48000.0) -> np.ndarray:
    out = np.zeros_like(f, dtype=float)
    for item in filters:
        if item.kind not in {"PK", "HS", "LS"} or item.frequency_hz <= 0 or item.q <= 0:
            raise ValueError("unsupported or invalid PEQ filter")
        out += _biquad_response(item, f, sample_rate_hz)
    return out


def _curve(f: np.ndarray, y: np.ndarray) -> Curve:
    return Curve.from_arrays(f, y)


def construct_target(base: Curve, delta_safe: Curve) -> Curve:
    """Apply only the locked V4.4 frequency ownership rules."""
    f, b = base.array()
    fd, d = delta_safe.array()
    d = interpolate_log(fd, d, f)
    w = np.where(f < 1000.0, 0.0, np.where(f <= 12000.0, 1.0, np.where(f < 14000.0, (14000.0 - f) / 2000.0, 0.0)))
    return _curve(f, b + d * w)


def generate(base_target: Curve, iems: Sequence[IEMInput], mode: TargetMode = "robust_target", sample_rate_hz: float = 48000.0, delta_safe: Curve | None = None) -> V44Result:
    if mode not in {"robust_target", "pure_earprint"}:
        raise ValueError("V4.4 has exactly two target modes")
    bf, by = base_target.array()
    if bf[0] > 20 or bf[-1] < 14000:
        raise ValueError("base target must cover the complete V4.4 ownership range")
    bn = normalize_at_1000(bf, by)
    per_iem: dict[str, dict[str, Curve]] = {}
    deltas: list[np.ndarray] = []
    for iem in iems:
        mf, my = iem.prepared_measurement.array()
        mi = interpolate_log(mf, my, bf)
        mi_n = normalize_at_1000(bf, mi)
        peq = reconstruct_peq(parse_peq(iem.peq_text), bf, sample_rate_hz)
        peq_n = normalize_at_1000(bf, peq)
        desired = mi_n + peq_n
        delta = desired - bn
        deltas.append(delta)
        per_iem[iem.id] = {"normalized_measured_fr": _curve(bf, mi_n), "reconstructed_peq": _curve(bf, peq), "normalized_peq": _curve(bf, peq_n), "desired_response": _curve(bf, desired)}
    if not deltas:
        raise ValueError("at least one IEM is required")
    matrix = np.vstack(deltas)
    median = np.median(matrix, axis=0)
    mad = np.median(np.abs(matrix - median), axis=0)
    n_plus = np.sum(matrix > ConsensusEpsilonDb, axis=0).astype(int).tolist()
    n_minus = np.sum(matrix < -ConsensusEpsilonDb, axis=0).astype(int).tolist()
    n_zero = np.sum(np.abs(matrix) <= ConsensusEpsilonDb, axis=0).astype(int).tolist()
    result = V44Result(mode, bf.tolist(), _curve(bf, by), _curve(bf, bn), per_iem, {k: _curve(bf, v) for k, v in zip([x.id for x in iems], deltas)}, _curve(bf, median), _curve(bf, mad), n_plus, n_minus, n_zero)
    if delta_safe is None:
        result.warnings.append("G, C, Broad, Local, Feature Classification, and Delta Safe formulas are not locked in V4.4; final target is intentionally pending.")
    else:
        result.delta_safe = delta_safe
        result.final_target = construct_target(base_target, delta_safe)
        final = np.asarray(result.final_target.level_db)
        for curves in result.per_iem.values():
            measured = np.asarray(curves["normalized_measured_fr"].level_db)
            desired = np.asarray(curves["desired_response"].level_db)
            curves["required_correction"] = _curve(bf, final - measured)
            curves["original_preferred_correction"] = _curve(bf, desired - measured)
    return result
