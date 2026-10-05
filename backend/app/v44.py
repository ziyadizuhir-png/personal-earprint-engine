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


def _default_target_folder() -> Path | None:
    candidates: list[tuple[str, Path]] = []
    wanted = "".join(ch for ch in DEFAULT_BASE_TARGET.lower() if ch.isalnum())
    for folder in sorted(BASE_TARGET_ROOT.iterdir()) if BASE_TARGET_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        metadata = _metadata(folder)
        name = str(metadata.get("name", ""))
        identifier = str(metadata.get("identifier", metadata.get("id", "")))
        identifiers = [name, identifier, str(metadata.get("target_id", "")), str(metadata.get("default_target_id", ""))]
        if any("".join(ch for ch in value.lower() if ch.isalnum()) == wanted for value in identifiers):
            candidates.append((folder.name, folder))
    return sorted(candidates, key=lambda item: item[0])[0][1] if candidates else None


def _base_target(slug: str | None = None) -> tuple[Path, dict[str, Any], Curve]:
    target_slug = slug
    if target_slug:
        if Path(target_slug).name != target_slug:
            raise HTTPException(400, "Invalid Base Target selection")
        folder = BASE_TARGET_ROOT / target_slug
    else:
        folder = _default_target_folder()
        if folder is None:
            raise HTTPException(404, f"No repository target matches default identifier: {DEFAULT_BASE_TARGET}")
    if not folder.is_dir():
        raise HTTPException(404, f"Base Target not found: {target_slug or folder.name}")
    metadata = _metadata(folder)
    target_file = folder / metadata.get("files", {}).get("target", "target.csv")
    if not target_file.exists():
        raise HTTPException(422, f"Base Target has no prepared curve: {folder.name}")
    try:
        curve = _read_curve(target_file)
    except (OSError, ValueError) as exc:
        raise HTTPException(422, f"Base Target curve is invalid: {folder.name}") from exc
    return folder, metadata, curve


def _curve_payload(curve: Curve | None) -> dict[str, Any] | None:
    return None if curve is None else {"frequency_hz": curve.frequency_hz, "level_db": curve.level_db}


def _result_payload(result, target_meta: dict[str, Any]) -> dict[str, Any]:
    data = result.to_dict()
    data["base_target_info"] = target_meta
    data["selected_base_target"] = {
        "name": target_meta.get("name"),
        "slug": target_meta.get("slug"),
    }
    data["iem_count"] = len(data["per_iem"])
    data["exact_1000_hz"] = True
    data["unresolved_stages"] = ["G", "C", "Broad", "Local", "Feature Classification", "Delta Safe"]
    data["warnings"] = list(data["warnings"])
    actual_name = target_meta.get("name")
    if actual_name != DEFAULT_BASE_TARGET:
        data["warnings"].append(f"Default requested as {DEFAULT_BASE_TARGET}, but repository resolves to {actual_name}.")
    return data


@router.get("/status")
def v44_status() -> dict[str, Any]:
    folder = _default_target_folder()
    metadata = _metadata(folder) if folder else {}
    return {
        "version": "4.4",
        "target_modes": ["robust_target", "pure_earprint"],
        "default_target": DEFAULT_BASE_TARGET,
        "resolved_base_target": metadata.get("name"),
        "normalization_anchor_hz": NORMALIZATION_HZ,
        "sample_rate_hz_default": DEFAULT_SAMPLE_RATE,
        "consensus_epsilon_db": CONSENSUS_EPSILON_DB,
        "unlocked_stages": ["G", "C", "Broad", "Local", "Feature Classification", "Delta Safe"],
        "warnings": [] if metadata.get("name") == DEFAULT_BASE_TARGET else ["Requested default target identifier is not currently represented by the stored target metadata."],
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
    default_folder = _default_target_folder()
    items = []
    for folder in sorted(BASE_TARGET_ROOT.iterdir()) if BASE_TARGET_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        metadata = _metadata(folder)
        items.append({"id": folder.name, "name": metadata.get("name", folder.name), "kind": "base", "metadata": metadata, "is_default": default_folder == folder})
    return {"items": items, "default_target": DEFAULT_BASE_TARGET}


@router.post("/generate")
def v44_generate(payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload.get("mode", "robust_target")
    if mode not in {"robust_target", "pure_earprint"}:
        raise HTTPException(400, "V4.4 target mode must be robust_target or pure_earprint")
    ids = payload.get("iem_ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(400, "Select at least one IEM")
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "Duplicate IEM identities cannot be separate votes")
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
