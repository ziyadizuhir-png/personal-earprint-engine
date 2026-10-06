"""Stable Robust Target API contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from engine.robust_target import generate_robust_target
from engine.v44.v44 import Curve, IEMInput
from .storage import BASE_TARGET_ROOT, IEM_ROOT, TARGET_ROOT, discover_collection, storage_info
from .v44 import _base_target, _default_target_folder, _iem

router = APIRouter(prefix="/api", tags=["robust-target"])


@router.get("/engine/status")
def engine_status() -> dict:
    discovered = discover_collection("iems")
    valid = 0
    skipped: list[dict[str, str]] = []
    for folder in discovered:
        try:
            _iem(folder)
            valid += 1
        except (OSError, ValueError) as exc:
            skipped.append({"id": folder.name, "reason": str(exc)})
    targets = discover_collection("base-targets")
    default_folder = _default_target_folder()
    ready = valid > 0 and default_folder is not None
    return {"status": "ready" if ready else "not_ready", "engine": "dynamic-robust-target", "version": "1.0.0", "engine_math": "V4.4", "storage": storage_info(), "produces": ["robust_target_curve"], "peq_output": False, "dataset": {"discovered_iems": len(discovered), "valid_active_iems": valid, "skipped_iems": skipped}, "base_targets": {"available": len(targets), "active": default_folder.name if default_folder else None}}


@router.get("/base-targets")
def base_targets() -> dict:
    from .main import list_collection
    default_folder = _default_target_folder()
    items = list_collection(BASE_TARGET_ROOT, "base-targets")
    for item in items:
        item["is_default"] = default_folder is not None and item["slug"] == default_folder.name
    return {"items": items}


@router.get("/robust-targets")
def robust_targets() -> dict:
    items = []
    for folder in discover_collection("targets"):
        metadata_path = folder / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(metadata)
    return {"items": items}


@router.get("/robust-targets/{target_id}")
def get_robust_target(target_id: str) -> dict:
    if Path(target_id).name != target_id:
        raise HTTPException(400, "Invalid Robust Target id")
    path = TARGET_ROOT / target_id / "artifact.json"
    if not path.exists():
        raise HTTPException(404, "Robust Target not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Robust Target artifact is invalid") from exc


@router.get("/robust-targets/{target_id}/export", response_class=PlainTextResponse)
def export_robust_target(target_id: str) -> str:
    target = get_robust_target(target_id)
    curve = target.get("curve", {})
    return "\n".join(f"{frequency:.6f}\t{level:.6f}" for frequency, level in zip(curve.get("frequency_hz", []), curve.get("level_db", [])))


@router.post("/robust-targets/generate")
def generate(payload: dict) -> dict:
    slug = payload.get("base_target_id")
    try:
        base = _base_target(slug)
        ids = payload.get("iem_ids")
        if ids is not None and (not isinstance(ids, list) or not ids):
            raise HTTPException(422, "iem_ids must be a non-empty list when provided")
        folders = []
        available = {folder.name: folder for folder in discover_collection("iems")}
        for item in ids if ids is not None else sorted(available):
            if not isinstance(item, str) or not item or Path(item).name != item:
                raise HTTPException(400, "Invalid IEM selection")
            folder = available.get(item)
            if folder is None:
                raise HTTPException(404, f"IEM not found: {item}")
            folders.append(folder)
        iems = [_iem(folder) for folder in folders]
        result = generate_robust_target(base, iems)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, str(exc)) from exc
    active_iem_ids = [folder.name for folder in folders]
    dataset_revision = hashlib.sha256(json.dumps({"base_target_id": base[0].name, "iem_ids": active_iem_ids}, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    canonical = json.dumps({"base_target_id": base[0].name, "iem_ids": active_iem_ids, "frequency_hz": result.final_target.frequency_hz, "level_db": result.final_target.level_db}, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    target_id = digest[:16]
    artifact = {"status": "ready", "robust_target_id": target_id, "target_hash": digest, "dataset_revision": dataset_revision, "base_target_id": slug or base[0].name, "base_target_name": base[1].get("name", base[0].name), "active_iem_ids": active_iem_ids, "iem_count": len(iems), "canonical_curve_artifact": {"content_type": "application/json", "sha256": digest, "grid_type": "base_target_master"}, "interoperability_curve_artifact": {"content_type": "text/plain", "format": "tab-separated UTF-8", "path": f"/api/robust-targets/{target_id}/export"}, "validation": {"exact_1000_hz": True, "peq_filters": False}, "curve": result.final_target.__dict__, "base_target": result.base_target.__dict__, "final_target": result.final_target.__dict__, "intermediate": result.to_dict(), "warnings": result.warnings, "stage_status": result.stage_status}
    artifact.update(result.to_dict())
    folder = TARGET_ROOT / target_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "artifact.json").write_text(json.dumps(artifact, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    (folder / "metadata.json").write_text(json.dumps({"robust_target_id": target_id, "target_hash": digest, "status": "ready", "base_target_id": artifact["base_target_id"], "iem_count": len(iems)}, separators=(",", ":")), encoding="utf-8")
    return artifact


@router.post("/robust-targets/validate")
def validate(payload: dict) -> dict:
    target_id = payload.get("robust_target_id")
    if target_id:
        artifact = get_robust_target(target_id)
    else:
        artifact = generate(payload)
    curve = artifact.get("curve", {})
    frequencies = curve.get("frequency_hz", [])
    levels = curve.get("level_db", [])
    valid = bool(frequencies and len(frequencies) == len(levels) and all(frequencies[i] < frequencies[i + 1] for i in range(len(frequencies) - 1)))
    return {"status": "valid" if valid else "invalid", "robust_target_id": artifact.get("robust_target_id"), "target_hash": artifact.get("target_hash"), "exact_1000_hz": 1000.0 in frequencies, "point_count": len(frequencies)}
