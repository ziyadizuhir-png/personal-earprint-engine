from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from engine.v44_engine import Curve, IEMInput, generate
from engine.v44.constants import (
    CONSENSUS_EPSILON_DB,
    DEFAULT_BASE_TARGET,
    DEFAULT_SAMPLE_RATE,
    NORMALIZATION_HZ,
)

from .storage import BASE_TARGET_ROOT, IEM_ROOT

router = APIRouter(prefix="/api/v44", tags=["v44"])
HEADPHONES_TARGET_SLUG = "headphones-com-iem-df-tilt-0-8-db-oct-b105-5-db"


def _metadata(folder: Path) -> dict[str, Any]:
    try:
        return json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_curve(path: Path) -> Curve:
    rows: list[tuple[float, float]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 2:
                continue
            try:
                rows.append((float(row[0]), float(row[1])))
            except ValueError:
                continue
    if len(rows) < 2:
        raise ValueError(f"Curve file has fewer than two numeric rows: {path}")
    rows.sort()
    dedup = dict(rows)
    return Curve([x for x, _ in sorted(dedup.items())], [y for _, y in sorted(dedup.items())])


def _iem(folder: Path) -> IEMInput:
    metadata = _metadata(folder)
    prepared = folder / "measurement.csv"
    source = folder / "measurement_source.txt"
    if not prepared.exists() or not (folder / "preferred.txt").exists():
        raise ValueError(f"IEM {folder.name} is missing prepared/PEQ data")
    prepared_curve = _read_curve(prepared)
    try:
        original_curve = _read_curve(source) if source.exists() else prepared_curve
    except ValueError:
        # Some seeded profiles intentionally have an empty source placeholder;
        # keep the prepared measurement as the usable curve and preserve the
        # metadata fact that an original source is unavailable.
        original_curve = prepared_curve
    return IEMInput(
        id=folder.name,
        original_measurement=original_curve,
        prepared_measurement=prepared_curve,
        peq_text=(folder / "preferred.txt").read_text(encoding="utf-8", errors="replace"),
        metadata=metadata,
    )


def _base_target(slug: str | None = None) -> tuple[Path, dict[str, Any], Curve]:
    target_slug = slug or HEADPHONES_TARGET_SLUG
    folder = BASE_TARGET_ROOT / target_slug
    if not folder.is_dir():
        raise HTTPException(404, f"Base Target not found: {target_slug}")
    metadata = _metadata(folder)
    target_file = folder / metadata.get("files", {}).get("target", "target.csv")
    if not target_file.exists():
        raise HTTPException(422, f"Base Target has no prepared curve: {target_slug}")
    return folder, metadata, _read_curve(target_file)


def _curve_payload(curve: Curve | None) -> dict[str, Any] | None:
    return None if curve is None else {"frequency_hz": curve.frequency_hz, "level_db": curve.level_db}


def _result_payload(result, target_meta: dict[str, Any]) -> dict[str, Any]:
    data = result.to_dict()
    data["base_target_info"] = target_meta
    data["warnings"] = list(data["warnings"])
    actual_name = target_meta.get("name")
    if actual_name != DEFAULT_BASE_TARGET:
        data["warnings"].append(f"Default requested as {DEFAULT_BASE_TARGET}, but repository resolves to {actual_name}.")
    return data


@router.get("/status")
def v44_status() -> dict[str, Any]:
    folder = BASE_TARGET_ROOT / HEADPHONES_TARGET_SLUG
    metadata = _metadata(folder)
    return {
        "version": "4.4",
        "target_modes": ["robust_target", "pure_earprint"],
        "default_target": DEFAULT_BASE_TARGET,
        "resolved_base_target": metadata.get("name"),
        "normalization_anchor_hz": NORMALIZATION_HZ,
        "sample_rate_hz_default": DEFAULT_SAMPLE_RATE,
        "consensus_epsilon_db": CONSENSUS_EPSILON_DB,
        "unlocked_stages": ["G", "C", "Broad", "Local", "Feature Classification", "Delta Safe"],
        "warnings": [] if metadata.get("name") == DEFAULT_BASE_TARGET else ["Requested default target label does not match the stored repository target metadata."],
    }


@router.get("/iems")
def v44_iems() -> dict[str, Any]:
    items = []
    for folder in sorted(IEM_ROOT.iterdir()) if IEM_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        metadata = _metadata(folder)
        items.append({"id": folder.name, "name": metadata.get("name", folder.name), "metadata": metadata, "has_original": (folder / "measurement_source.txt").exists(), "has_prepared": (folder / "measurement.csv").exists(), "has_preferred": (folder / "preferred.txt").exists()})
    return {"items": items}


@router.get("/targets")
def v44_targets() -> dict[str, Any]:
    items = []
    for folder in sorted(BASE_TARGET_ROOT.iterdir()) if BASE_TARGET_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        metadata = _metadata(folder)
        items.append({"id": folder.name, "name": metadata.get("name", folder.name), "kind": "base", "metadata": metadata, "is_default": folder.name == HEADPHONES_TARGET_SLUG})
    return {"items": items, "default_target": DEFAULT_BASE_TARGET}


@router.post("/generate")
def v44_generate(payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload.get("mode", "robust_target")
    if mode not in {"robust_target", "pure_earprint"}:
        raise HTTPException(400, "V4.4 target mode must be robust_target or pure_earprint")
    ids = payload.get("iem_ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(400, "Select at least one IEM")
    try:
        iems = [_iem(IEM_ROOT / item_id) for item_id in ids]
    except (OSError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    _folder, target_meta, base = _base_target(payload.get("target_id"))
    try:
        result = generate(base, iems, mode=mode, sample_rate_hz=float(payload.get("sample_rate_hz", DEFAULT_SAMPLE_RATE)))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _result_payload(result, target_meta)


@router.post("/validate")
def v44_validate(payload: dict[str, Any]) -> dict[str, Any]:
    generated = v44_generate(payload)
    return {"mode": generated["mode"], "status": "pending" if generated["final_target"] is None else "complete", "final_target_available": generated["final_target"] is not None, "warnings": generated["warnings"], "intermediate": generated}
