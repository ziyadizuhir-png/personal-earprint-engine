"""Canonical Personal EarPrint v0.3.1 implementation.

This is a direct library implementation of the uploaded v0.3.1 bundle.
There is deliberately no compatibility path to the retired v0.3.0/V4.4
implementations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Literal, Sequence

import numpy as np

AnchorHz = 1000.0
ConsensusEpsilonDb = 0.25
TargetMode = Literal["robust_target"]
ENGINE_VERSION = "Personal EarPrint Engine 0.3.1"
ALGORITHM_VERSION = "PersonalDelta-FullBand-0.3.1"
SAMPLE_RATE_HZ = 48000.0
HUBER_C = 1.345
HUBER_TOL_DB = 1.0e-8
HUBER_MAX_ITER = 100
SCALE_FLOOR_DB = 0.10
EDGE_TAPER_START_HZ = 11200.0
PERSONALIZATION_END_HZ = 12000.0


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
class V031Result:
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
    # Diagnostics required by the v0.3.1 bundle.
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
    engine_version: str = ENGINE_VERSION
    algorithm_version: str = ALGORITHM_VERSION
    huber_iterations: list[int] = field(default_factory=list)
    narrow_peak_diagnostics: list[dict[str, float | str]] = field(default_factory=list)

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
    """Reject inputs that do not contain the exact v0.3.1 anchor."""
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
        if re.search(r"\boff\b", lowered):
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
        if item.kind != "PK":
            raise ValueError("v0.3.1 accepts only active PK filters")
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


def smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def construct_target(base: Curve, robust_delta: Curve) -> Curve:
    """Apply v0.3.1 ownership: full delta, then only the boundary taper."""
    f, b = base.array()
    fd, d = robust_delta.array()
    d = interpolate_log(fd, d, f)
    w = np.zeros_like(f)
    w[(f >= AnchorHz) & (f < EDGE_TAPER_START_HZ)] = 1.0
    taper = (f >= EDGE_TAPER_START_HZ) & (f < PERSONALIZATION_END_HZ)
    w[taper] = 1.0 - smoothstep((f[taper] - EDGE_TAPER_START_HZ) / 800.0)
    return _curve(f, b + d * w)


def analyze_broad_local(frequency_hz: np.ndarray, robust_delta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Gaussian log-frequency diagnostic only; never alters robust Delta."""
    log_frequency = np.log2(frequency_hz)
    broad = np.empty_like(robust_delta, dtype=float)
    sigma = 1.0 / 12.0
    for index, center in enumerate(log_frequency):
        weights = np.exp(-0.5 * ((log_frequency - center) / sigma) ** 2)
        broad[index] = float(np.sum(weights * robust_delta) / np.sum(weights))
    return broad, robust_delta - broad


def huber_center(matrix: np.ndarray, c: float = HUBER_C, floor_db: float = SCALE_FLOOR_DB, max_iter: int = HUBER_MAX_ITER) -> tuple[np.ndarray, np.ndarray]:
    """Return the Huber IRLS center and per-frequency iteration counts."""
    mu = np.median(matrix, axis=0)
    mad = np.median(np.abs(matrix - mu), axis=0)
    scale = np.maximum(1.4826 * mad, floor_db)
    iterations = np.zeros(matrix.shape[1], dtype=int)
    for iteration in range(1, max_iter + 1):
        residual = matrix - mu
        k = c * scale
        abs_residual = np.abs(residual)
        ratio = np.divide(k, abs_residual, out=np.zeros_like(abs_residual), where=abs_residual != 0.0)
        weights = np.where(abs_residual <= k, 1.0, ratio)
        next_mu = np.sum(weights * matrix, axis=0) / np.sum(weights, axis=0)
        iterations[np.abs(next_mu - mu) > HUBER_TOL_DB] = iteration
        if np.max(np.abs(next_mu - mu)) <= HUBER_TOL_DB:
            return next_mu, iterations
        mu = next_mu
    return mu, iterations


def generate(base_target: Curve, iems: Sequence[IEMInput], mode: TargetMode = "robust_target", sample_rate_hz: float = SAMPLE_RATE_HZ) -> V031Result:
    if mode != "robust_target":
        raise ValueError("production engine accepts only the Robust Target contract")
    bf, by = base_target.array()
    if bf[0] > 20 or bf[-1] < 12000:
        raise ValueError("base target must cover the complete v0.3.1 ownership range")
    bf = np.unique(np.r_[bf, AnchorHz, EDGE_TAPER_START_HZ, PERSONALIZATION_END_HZ])
    by = interpolate_log(base_target.array()[0], base_target.array()[1], bf)
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
    n_active = np.asarray(n_plus, dtype=int) + np.asarray(n_minus, dtype=int)
    g_values = np.divide(np.abs(np.asarray(n_plus) - np.asarray(n_minus)), n_active, out=np.zeros_like(median), where=n_active != 0)
    c_values = np.divide(np.maximum(np.asarray(n_plus), np.asarray(n_minus)), n_active, out=np.zeros_like(median), where=n_active != 0)
    c_curve = _curve(bf, c_values) if np.all(n_active != 0) else None
    result = V031Result(mode, bf.tolist(), _curve(bf, by), _curve(bf, bn), per_iem, {k: _curve(bf, v) for k, v in zip([x.id for x in iems], deltas)}, _curve(bf, median), _curve(bf, mad), n_plus, n_minus, n_zero, G=_curve(bf, g_values), C=c_curve)
    for curves in result.per_iem.values():
        measured = np.asarray(curves["normalized_measured_fr"].level_db)
        desired = np.asarray(curves["desired_response"].level_db)
        curves["original_preferred_correction"] = _curve(bf, desired - measured)
    robust, huber_iterations = huber_center(matrix)
    result.robust_delta = _curve(bf, robust)
    broad, local = analyze_broad_local(bf, robust)
    result.broad = _curve(bf, broad)
    result.local = _curve(bf, local)
    result.delta_safe = _curve(bf, robust)
    result.final_target = construct_target(_curve(bf, by), result.delta_safe)
    result.stage_status = {
        "source_identity": "IMPLEMENTED: bundle hashes verified by API provenance",
        "peq_reconstruction": "IMPLEMENTED: 48 kHz digital PK biquads",
        "robust_estimator": "IMPLEMENTED: median + raw MAD + Huber IRLS",
        "broad_local_diagnostics": "DIAGNOSTIC_ONLY: Gaussian log-frequency smoother",
        "narrow_peak_diagnostics": "DIAGNOSTIC_ONLY: residual local extrema",
        "final_curve": "IMPLEMENTED: v0.3.1 ownership contract",
        "export": "IMPLEMENTED: final target curve",
    }
    result.warnings.append("Broad and Local are diagnostics only; no global smoothing or fixed 8.1275 kHz guardrail is applied.")
    result.engine_version = ENGINE_VERSION
    result.algorithm_version = ALGORITHM_VERSION
    result.huber_iterations = huber_iterations.tolist()
    peaks: list[dict[str, float | str]] = []
    for index in range(1, len(bf) - 1):
        if not (1000.0 <= bf[index] < 12000.0):
            continue
        if abs(local[index]) >= abs(local[index - 1]) and abs(local[index]) >= abs(local[index + 1]) and abs(local[index]) >= 1.0:
            peaks.append({"frequency_hz": float(bf[index]), "residual_db": float(local[index]), "kind": "narrow_peak" if local[index] > 0 else "narrow_dip"})
    result.narrow_peak_diagnostics = sorted(peaks, key=lambda item: abs(float(item["residual_db"])), reverse=True)[:24]
    final = np.asarray(result.final_target.level_db)
    for curves in result.per_iem.values():
        measured = np.asarray(curves["normalized_measured_fr"].level_db)
        curves["required_correction"] = _curve(bf, final - measured)
    return result
