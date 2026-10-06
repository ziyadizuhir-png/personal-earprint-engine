"""Auditable Personal Earprint Robust Target calculations.

This module deliberately does not import the legacy engine.  V4.4 owns its
master grid, 1 kHz anchor, PEQ reconstruction, and Robust Target contract.
Feature Classification remains an explicit extension point because its
qualitative categories and thresholds are not defined by the production
formula. All numeric Robust Target stages implemented here are canonical.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Callable, Literal, Sequence

import numpy as np

AnchorHz = 1000.0
ConsensusEpsilonDb = 0.25
TargetMode = Literal["robust_target"]


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
    stage_status: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    robust_delta: Curve | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interpolate_log(f_src: np.ndarray, y_src: np.ndarray, f_dst: np.ndarray) -> np.ndarray:
    """Linear interpolation over log(f), with no extrapolation."""
    # Prepared CSVs serialize the shared endpoint independently. Allow only
    # that bounded decimal-rounding difference; np.interp still clamps at the
    # endpoint and no mathematical extrapolation is performed.
    tolerance = 1.0e-10 * max(1.0, abs(float(f_src[0])), abs(float(f_src[-1])), abs(float(f_dst[0])), abs(float(f_dst[-1])))
    if f_dst[0] < f_src[0] - tolerance or f_dst[-1] > f_src[-1] + tolerance:
        raise ValueError("source curve does not cover destination grid")
    return np.interp(np.log(f_dst), np.log(f_src), y_src)


def normalize_at_1000(f: np.ndarray, y: np.ndarray) -> np.ndarray:
    return y - float(np.interp(math.log(AnchorHz), np.log(f), y))


def require_exact_1000_hz(f: np.ndarray, label: str) -> None:
    """Reject unprepared V4.4 inputs instead of silently interpolating the anchor."""
    if not np.any(np.isclose(f, AnchorHz, rtol=0.0, atol=1.0e-12)):
        raise ValueError(f"{label} must contain an exact 1000 Hz calculation anchor")


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_FILTER_RE = re.compile(
    rf"(?:Filter\s*\d+\s*:\s*)?(?:ON\s+)?(PK|HS|LS)\s*(?:Fc\s*)?({_NUMBER})\s*(?:Hz)?\s*(?:Gain\s*)?({_NUMBER})\s*(?:dB)?\s*(?:Q\s*)?({_NUMBER})",
    re.I,
)
_COMMENT_PREFIXES = ("#", "//", ";")
_METADATA_PREFIXES = (
    "soundeq dore",
    "device:",
    "generated:",
    "preamp:",
    "channel:",
    "sample rate:",
    "format:",
    "author:",
    "notes:",
)


def parse_peq(text: str | Sequence[PEQFilter]) -> list[PEQFilter]:
    if not isinstance(text, str):
        return list(text)
    filters: list[PEQFilter] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if line.startswith(_COMMENT_PREFIXES) or lowered.startswith(_METADATA_PREFIXES):
            continue
        m = _FILTER_RE.fullmatch(line)
        if not m:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 4 and parts[0].upper() in {"PK", "HS", "LS"}:
                try:
                    item = PEQFilter(parts[0].upper(), float(parts[1]), float(parts[2]), float(parts[3]))
                except ValueError as exc:
                    raise ValueError(f"Malformed PEQ filter on line {line_number}") from exc
                filters.append(item)
            else:
                raise ValueError(f"Malformed or unsupported PEQ filter on line {line_number}: {line}")
            continue
        try:
            item = PEQFilter(m.group(1).upper(), float(m.group(2)), float(m.group(3)), float(m.group(4)))
        except ValueError as exc:
            raise ValueError(f"Malformed PEQ filter on line {line_number}") from exc
        filters.append(item)
    for item in filters:
        if not all(math.isfinite(value) for value in (item.frequency_hz, item.gain_db, item.q)) or item.frequency_hz <= 0 or item.q <= 0:
            raise ValueError("PEQ filters require finite positive frequency/Q and finite gain")
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
    """Apply the production ownership and C1 cubic-Hermite handoff."""
    f, b = base.array()
    fd, d = delta_safe.array()
    d = interpolate_log(fd, d, f)
    # 1-10 kHz: full personal ownership; 10-12 kHz: half ownership.
    w = np.where(f < 1000.0, 0.0, np.where(f < 10000.0, 1.0, np.where(f < 12000.0, 0.5, 0.0)))
    handoff = (f >= 12000.0) & (f < 14000.0)
    t = np.clip((f - 12000.0) / 2000.0, 0.0, 1.0)
    # Cubic Hermite: value and left slope are preserved at 12 kHz; zero at 14 kHz.
    left_slope = np.gradient(d, f)
    d12 = np.interp(np.log(12000.0), np.log(f), d)
    s12 = np.interp(np.log(12000.0), np.log(f), left_slope)
    span = 2000.0
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    handoff_delta = h00*d12 + h10*span*s12
    return _curve(f, b + np.where(handoff, handoff_delta, d * w))


def analyze_broad_local(frequency_hz: np.ndarray, robust_delta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic approximately 1/12-octave broad/local diagnostic split."""
    log_frequency = np.log2(frequency_hz)
    broad = np.empty_like(robust_delta, dtype=float)
    half_window = 1.0 / 24.0
    for index, center in enumerate(log_frequency):
        mask = np.abs(log_frequency - center) <= half_window
        broad[index] = float(np.mean(robust_delta[mask]))
    return broad, robust_delta - broad


def apply_local_safety(frequency_hz: np.ndarray, delta: np.ndarray) -> np.ndarray:
    """Apply the specified local 8.13 kHz safety factor only."""
    bump = np.exp(-0.5 * (np.log2(frequency_hz / 8127.5) / 0.16) ** 2)
    return delta * (1.0 - 0.45 * bump)


def huber_center(matrix: np.ndarray, c: float = 1.345, floor_db: float = 1.0e-6, max_iter: int = 50) -> np.ndarray:
    """Deterministic pointwise Huber IRLS center, seeded by the median."""
    mu = np.median(matrix, axis=0)
    mad = np.median(np.abs(matrix - mu), axis=0)
    scale = np.maximum(1.4826 * mad, floor_db)
    for _ in range(max_iter):
        residual = matrix - mu
        k = c * scale
        abs_residual = np.abs(residual)
        ratio = np.divide(k, abs_residual, out=np.zeros_like(abs_residual), where=abs_residual != 0.0)
        weights = np.where(abs_residual <= k, 1.0, ratio)
        next_mu = np.sum(weights * matrix, axis=0) / np.sum(weights, axis=0)
        if np.max(np.abs(next_mu - mu)) <= 1.0e-10:
            return next_mu
        mu = next_mu
    return mu


def generate(base_target: Curve, iems: Sequence[IEMInput], mode: TargetMode = "robust_target", sample_rate_hz: float = 48000.0, delta_safe: Curve | None = None) -> V44Result:
    if mode != "robust_target":
        raise ValueError("production engine accepts only the Robust Target contract")
    bf, by = base_target.array()
    require_exact_1000_hz(bf, "Base Target")
    if bf[0] > 20 or bf[-1] < 14000:
        raise ValueError("base target must cover the complete V4.4 ownership range")
    bn = normalize_at_1000(bf, by)
    per_iem: dict[str, dict[str, Curve]] = {}
    deltas: list[np.ndarray] = []
    for iem in iems:
        mf, my = iem.prepared_measurement.array()
        require_exact_1000_hz(mf, f"Prepared measurement for {iem.id}")
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
    n_active = np.asarray(n_plus, dtype=int) + np.asarray(n_minus, dtype=int)
    g_values = np.divide(np.abs(np.asarray(n_plus) - np.asarray(n_minus)), n_active, out=np.zeros_like(median), where=n_active != 0)
    c_values = np.divide(np.maximum(np.asarray(n_plus), np.asarray(n_minus)), n_active, out=np.zeros_like(median), where=n_active != 0)
    c_curve = _curve(bf, c_values) if np.all(n_active != 0) else None
    result = V44Result(mode, bf.tolist(), _curve(bf, by), _curve(bf, bn), per_iem, {k: _curve(bf, v) for k, v in zip([x.id for x in iems], deltas)}, _curve(bf, median), _curve(bf, mad), n_plus, n_minus, n_zero, G=_curve(bf, g_values), C=c_curve)
    for curves in result.per_iem.values():
        measured = np.asarray(curves["normalized_measured_fr"].level_db)
        desired = np.asarray(curves["desired_response"].level_db)
        curves["original_preferred_correction"] = _curve(bf, desired - measured)
    robust = huber_center(matrix)
    result.robust_delta = _curve(bf, robust)
    broad, local = analyze_broad_local(bf, robust)
    result.broad = _curve(bf, broad)
    result.local = _curve(bf, local)
    safe_values = apply_local_safety(bf, robust)
    result.delta_safe = delta_safe or _curve(bf, safe_values)
    result.final_target = construct_target(base_target, result.delta_safe)
    result.stage_status = {
        "G": "IMPLEMENTED",
        "C": "IMPLEMENTED; undefined at frequencies with Nactive=0",
        "Broad": "IMPLEMENTED_DIAGNOSTIC: approximately 1/12-octave local mean",
        "Local": "IMPLEMENTED_DIAGNOSTIC: RobustDelta - Broad",
        "Feature Classification": "SPEC_BLOCKED: qualitative rules lack executable thresholds/categories",
        "Delta Safe": "IMPLEMENTED: local 8.13 kHz safety factor",
    }
    result.warnings.append("Feature Classification remains specification-blocked; Broad and Local are diagnostics and Delta Safe applies only the specified local 8.13 kHz safety factor.")
    final = np.asarray(result.final_target.level_db)
    for curves in result.per_iem.values():
        measured = np.asarray(curves["normalized_measured_fr"].level_db)
        curves["required_correction"] = _curve(bf, final - measured)
    return result
