"""Stable Robust Target API contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from engine.robust_target import generate_robust_target
from engine.v44.v44 import Curve, IEMInput
from .storage import BASE_TARGET_ROOT, IEM_ROOT, storage_info
from .v44 import _base_target, _default_target_folder, _iem

router = APIRouter(prefix="/api", tags=["robust-target"])


@router.get("/engine/status")
def engine_status() -> dict:
    return {"status": "ready", "engine": "dynamic-robust-target", "version": "1.0.0", "engine_math": "V4.4", "storage": storage_info(), "produces": ["robust_target_curve"], "peq_output": False}


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
    return {"items": []}


@router.post("/robust-targets/generate")
def generate(payload: dict) -> dict:
    slug = payload.get("base_target_id")
    try:
        base = _base_target(slug)
        ids = payload.get("iem_ids")
        if ids is not None and (not isinstance(ids, list) or not ids):
            raise HTTPException(422, "iem_ids must be a non-empty list when provided")
        folders = []
        for item in ids if ids is not None else [p.name for p in sorted(IEM_ROOT.iterdir()) if p.is_dir()]:
            if not isinstance(item, str) or not item or Path(item).name != item:
                raise HTTPException(400, "Invalid IEM selection")
            folder = IEM_ROOT / item
            if not folder.is_dir():
                raise HTTPException(404, f"IEM not found: {item}")
            folders.append(folder)
        iems = [_iem(folder) for folder in folders]
        result = generate_robust_target(base, iems)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, str(exc)) from exc
    canonical = json.dumps({"frequency_hz": result.final_target.frequency_hz, "level_db": result.final_target.level_db}, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return {"status": "ready", "robust_target_id": digest[:16], "target_hash": digest, "base_target_id": slug or base[0].name, "base_target_name": base[1].get("name", base[0].name), "iem_count": len(iems), "canonical_curve_artifact": {"content_type": "application/json", "sha256": digest, "grid_type": "base_target_master"}, "interoperability_curve_artifact": None, "validation": {"exact_1000_hz": True, "peq_filters": False}, "curve": result.final_target.__dict__, "base_target": result.base_target.__dict__, "final_target": result.final_target.__dict__, "warnings": result.warnings, "stage_status": result.stage_status}
