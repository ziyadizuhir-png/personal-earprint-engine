from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable

from .storage import unique_iem_dir

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_measurement(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = re.split(r"[\s,;]+", line)
        if len(parts) < 2:
            continue
        try:
            f = float(parts[0])
            db = float(parts[1])
        except ValueError:
            continue
        if not (math.isfinite(f) and math.isfinite(db) and f > 0):
            continue
        rows.append((f, db))

    rows.sort(key=lambda x: x[0])
    if not rows:
        raise ValueError("No valid frequency-response points found.")

    dedup: list[tuple[float, float]] = []
    seen = set()
    for f, db in rows:
        if f in seen:
            continue
        seen.add(f)
        dedup.append((f, db))

    if any(dedup[i][0] >= dedup[i+1][0] for i in range(len(dedup)-1)):
        raise ValueError("Measurement frequencies must be strictly ascending after parsing.")

    if not (dedup[0][0] <= 1000.0 <= dedup[-1][0]):
        raise ValueError("Measurement must cover 1000 Hz.")

    return dedup

def log_interp(rows: list[tuple[float, float]], x: float) -> float:
    for f, db in rows:
        if abs(f - x) < 1e-12:
            return db
    for i in range(1, len(rows)):
        f0, y0 = rows[i - 1]
        f1, y1 = rows[i]
        if f0 < x < f1:
            t = (math.log(x) - math.log(f0)) / (math.log(f1) - math.log(f0))
            return y0 + (y1 - y0) * t
    raise ValueError(f"Cannot interpolate {x} Hz.")

def prepare_measurement(source: Path, output: Path) -> dict:
    rows = parse_measurement(source)
    exact = any(abs(f - 1000.0) < 1e-12 for f, _ in rows)

    prepared = list(rows)
    added = False
    if not exact:
        prepared.append((1000.0, log_interp(rows, 1000.0)))
        prepared.sort(key=lambda x: x[0])
        added = True

    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["freq", "db"])
        for f, db in prepared:
            writer.writerow([f"{f:.12g}", f"{db:.12g}"])

    return {
        "source_points": len(rows),
        "prepared_points": len(prepared),
        "source_grid_contains_exact_1000_hz": exact,
        "prepared_grid_contains_exact_1000_hz": True,
        "added_1000_hz_point": added,
        "added_point_method": (
            "log-frequency linear interpolation between adjacent source points"
            if added else None
        ),
        "frequency_range_hz": [rows[0][0], rows[-1][0]],
    }

def basic_peq_validation(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("PEQ file is empty.")

    supported = bool(re.search(r"\b(PK|HS|LS)\b", text, flags=re.I))
    return {
        "non_empty": True,
        "contains_supported_filter_type": supported,
        "source_format": "SoundEQ Dore / simplified filter text",
    }

def ingest_iem(name: str, measurement, preferred, notes: str | None = None) -> dict:
    base_dir = unique_iem_dir(slugify(name))
    base_dir.mkdir(parents=True, exist_ok=False)

    source_measurement = base_dir / "measurement_source.txt"
    preferred_path = base_dir / "preferred.txt"
    prepared_measurement = base_dir / "measurement.csv"

    source_measurement.write_bytes(measurement)
    preferred_path.write_bytes(preferred)

    measurement_info = prepare_measurement(source_measurement, prepared_measurement)
    peq_info = basic_peq_validation(preferred_path)

    metadata = {
        "name": name.strip(),
        "slug": base_dir.name,
        "status": "validated",
        "files": {
            "measurement": "measurement.csv",
            "measurement_source": "measurement_source.txt",
            "preferred": "preferred.txt",
            "metadata": "metadata.json",
        },
        "measurement": measurement_info,
        "preferred": {
            **peq_info,
            "source": "SoundEQ Dore",
            "sample_rate_hz_default": 48000,
        },
        "engine": {
            "target_version": "V4.4",
            "normalization_anchor_hz": 1000.0,
            "grid_policy": "Base Target grid will be the Master Grid during target generation.",
        },
        "notes": notes or "",
        "source_hashes": {
            "measurement_source_sha256": sha256_file(source_measurement),
            "preferred_sha256": sha256_file(preferred_path),
        },
    }

    (base_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return metadata
