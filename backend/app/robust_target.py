"""Production API for the uploaded Personal EarPrint v0.3.1 bundle."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from engine.personal_earprint_v031 import Curve, IEMInput, generate
from .ingest import sha256_file
from .storage import BASE_TARGET_ROOT, BUNDLED_DATA_ROOT, discover_collection, storage_info

router = APIRouter(prefix="/api", tags=["personal-earprint-v031"])
DEFAULT_BASE_ID = "headphones-com-iem-df-tilt-1-db-oct-b105-5-db"
ENGINE_VERSION = "Personal EarPrint Engine 0.3.1"

def _metadata(folder: Path) -> dict[str, Any]:
    try: return json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {}

def _read_curve(path: Path) -> Curve:
    rows = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        parts = line.strip().replace(",", "\t").split()
        if len(parts) >= 2:
            try: rows.append((float(parts[0]), float(parts[1])))
            except ValueError: pass
    rows = sorted(dict(rows).items())
    if len(rows) < 2: raise ValueError(f"Curve file is invalid: {path.name}")
    return Curve([f for f, _ in rows], [y for _, y in rows])

def _iem(folder: Path) -> IEMInput:
    measurement, preferred = folder / "measurement_source.txt", folder / "preferred.txt"
    if not measurement.exists() or not preferred.exists(): raise ValueError(f"IEM {folder.name} is missing the bundle source pair")
    curve = _read_curve(measurement)
    return IEMInput(folder.name, curve, curve, preferred.read_text(encoding="utf-8", errors="replace"), _metadata(folder))

def _canonical_base_folder() -> Path | None:
    """Resolve the canonical bundle target across mounted and image data roots."""
    candidates = [
        BASE_TARGET_ROOT / DEFAULT_BASE_ID,
        BUNDLED_DATA_ROOT / "base-targets" / DEFAULT_BASE_ID,
    ]
    seen: set[Path] = set()
    for folder in candidates:
        folder = folder.resolve()
        if folder in seen:
            continue
        seen.add(folder)
        if folder.is_dir() and (folder / "target_source.txt").is_file():
            return folder
    return None

def _base_target(slug: str | None = None) -> tuple[Path, dict[str, Any], Curve]:
    target_id = slug or DEFAULT_BASE_ID
    if Path(target_id).name != target_id: raise HTTPException(400, "Invalid Base Target selection")
    if target_id != DEFAULT_BASE_ID:
        raise HTTPException(422, f"v0.3.1 only supports the bundle Base Target: {DEFAULT_BASE_ID}")
    folder = _canonical_base_folder() if target_id == DEFAULT_BASE_ID else None
    if folder is None: raise HTTPException(404, f"Bundle Base Target not found: {target_id}")
    source = folder / "target_source.txt"
    if not source.exists(): raise HTTPException(404, f"Bundle Base Target not found: {target_id}")
    return folder, _metadata(folder), _read_curve(source)

def _curve(curve: Curve | None) -> dict[str, list[float]] | None:
    return None if curve is None else {"frequency_hz": curve.frequency_hz, "level_db": curve.level_db}

def _result(result: Any, meta: dict[str, Any], provenance: dict[str, Any], digest: str) -> dict[str, Any]:
    data = result.to_dict()
    data.update({"base_target_id": DEFAULT_BASE_ID, "base_target_name": meta.get("name", DEFAULT_BASE_ID), "active_iem_ids": list(result.personal_delta), "iem_count": len(result.personal_delta), "target_hash": digest, "provenance": provenance, "status": "ready"})
    data["validation"] = {"exact_1000_hz": 1000.0 in result.master_grid_hz, "master_grid_points": len(result.master_grid_hz), "base_exact_below_1k": all(a == b for a, b, f in zip(result.base_target.level_db, result.final_target.level_db, result.master_grid_hz) if f < 1000), "base_exact_at_or_above_12k": all(a == b for a, b, f in zip(result.base_target.level_db, result.final_target.level_db, result.master_grid_hz) if f >= 12000), "all_iems_retained": len(result.personal_delta) == 9}
    return data

@router.get("/engine/status")
def engine_status() -> dict[str, Any]:
    folders = discover_collection("iems"); valid, skipped = 0, []
    for folder in folders:
        try: _iem(folder); valid += 1
        except (OSError, ValueError) as exc: skipped.append({"id": folder.name, "reason": str(exc)})
    return {"status": "ready" if valid == 9 and _canonical_base_folder() is not None else "not_ready", "engine": ENGINE_VERSION, "version": "0.3.1", "engine_math": "PersonalDelta-FullBand-0.3.1", "storage": storage_info(), "dataset": {"discovered_iems": len(folders), "valid_active_iems": valid, "skipped_iems": skipped}, "base_target": DEFAULT_BASE_ID, "produces": ["robust_target_curve", "narrow_peak_diagnostics"]}

@router.get("/base-targets")
def base_targets() -> dict[str, Any]:
    folder = _canonical_base_folder()
    if folder is None:
        return {"items": []}
    return {"items": [{"name": _metadata(folder).get("name", DEFAULT_BASE_ID), "slug": DEFAULT_BASE_ID, "kind": "base", "status": "validated", "is_default": True, "collection": "base-targets"}]}

@router.get("/robust-targets")
def robust_targets() -> dict[str, Any]: return {"items": []}

@router.post("/robust-targets/generate")
def generate_target(payload: dict[str, Any]) -> dict[str, Any]:
    folder, meta, base = _base_target(payload.get("base_target_id"))
    folders = {f.name: f for f in discover_collection("iems")}
    ids = payload.get("iem_ids") or sorted(folders)
    if not isinstance(ids, list) or len(ids) != 9 or len(set(ids)) != 9: raise HTTPException(422, "v0.3.1 requires exactly nine distinct IEM votes")
    try: result = generate(base, [_iem(folders[item]) for item in ids])
    except (KeyError, OSError, ValueError) as exc: raise HTTPException(422, str(exc)) from exc
    provenance = {"engine_version": ENGINE_VERSION, "algorithm_version": result.algorithm_version, "base_target_sha256": sha256_file(folder / "target_source.txt"), "iems": [{"id": f.name, "measurement_sha256": sha256_file(f / "measurement_source.txt"), "peq_sha256": sha256_file(f / "preferred.txt")} for f in sorted((folders[item] for item in ids), key=lambda p: p.name)]}
    digest = hashlib.sha256(json.dumps({"provenance": provenance, "curve": _curve(result.final_target)}, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    return _result(result, meta, provenance, digest)

@router.get("/robust-targets/{target_id}/export", response_class=PlainTextResponse)
def export_target(target_id: str) -> str: raise HTTPException(404, "Targets are generated on demand in v0.3.1")
