"""Stable Robust Target API contract."""
from __future__ import annotations

import hashlib
import json
from fastapi import APIRouter, HTTPException
from engine.robust_target import generate_robust_target
from engine.v44.v44 import Curve, IEMInput
from .storage import BASE_TARGET_ROOT, IEM_ROOT
from .v44 import _base_target, _iem

router = APIRouter(prefix="/api", tags=["robust-target"])


@router.get("/engine/status")
def engine_status() -> dict:
    return {"status": "ready", "engine": "dynamic-robust-target", "version": "1.0.0", "produces": ["robust_target_curve"], "peq_output": False}


@router.get("/base-targets")
def base_targets() -> dict:
    from .main import list_collection
    return {"items": list_collection(BASE_TARGET_ROOT, "base-targets")}


@router.get("/robust-targets")
def robust_targets() -> dict:
    return {"items": []}


@router.post("/robust-targets/generate")
def generate(payload: dict) -> dict:
    slug = payload.get("base_target_id")
    try:
        base = _base_target(slug)
        ids = payload.get("iem_ids")
        folders = [IEM_ROOT / x for x in ids] if ids else [p for p in sorted(IEM_ROOT.iterdir()) if p.is_dir()]
        iems = [_iem(folder) for folder in folders]
        result = generate_robust_target(base, iems)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, str(exc)) from exc
    canonical = json.dumps({"frequency_hz": result.final_target.frequency_hz, "level_db": result.final_target.level_db}, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return {"status": "ready", "robust_target_id": digest[:16], "target_hash": digest, "base_target_id": slug, "iem_count": len(iems), "canonical_curve_artifact": {"content_type": "application/json", "sha256": digest, "grid_type": "base_target_master"}, "interoperability_curve_artifact": None, "validation": {"exact_1000_hz": True, "peq_filters": False}, "curve": result.final_target.__dict__}
