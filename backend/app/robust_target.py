"""FastAPI surface for the Personal EarPrint v0.3.1 contract."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from engine.personal_earprint_v031 import Curve, IEMInput, generate
from .ingest import sha256_file
from .storage import BASE_TARGET_ROOT, BUNDLED_DATA_ROOT, discover_collection, generated_target_root, storage_info

router = APIRouter(prefix="/api", tags=["personal-earprint-v031"])
DEFAULT_BASE_ID = "headphones-com-iem-df-tilt-1-db-oct-b105-5-db"
ENGINE_VERSION = "Personal EarPrint Engine 0.3.1"


def _metadata(folder: Path) -> dict[str, Any]:
    try:
        return json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_curve(path: Path) -> Curve:
    rows: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        parts = line.strip().replace(",", "\t").split()
        if len(parts) >= 2:
            try:
                rows.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if len(rows) < 2:
        raise ValueError(f"Curve file is invalid: {path.name}")
    rows = sorted(dict(rows).items())
    curve = Curve([f for f, _ in rows], [y for _, y in rows])
    curve.array()
    if curve.frequency_hz[0] > 20 or curve.frequency_hz[-1] < 12000:
        raise ValueError("Base Target must cover at least 20 Hz through 12 kHz")
    return curve


def _curve(curve: Curve | None) -> dict[str, list[float]] | None:
    return None if curve is None else {"frequency_hz": curve.frequency_hz, "level_db": curve.level_db}


def _iem(folder: Path) -> IEMInput:
    measurement, preferred = folder / "measurement_source.txt", folder / "preferred.txt"
    if not measurement.exists() or not preferred.exists():
        raise ValueError(f"IEM {folder.name} is missing its measurement/PEQ pair")
    curve = _read_curve(measurement)
    return IEMInput(folder.name, curve, curve, preferred.read_text(encoding="utf-8", errors="replace"), _metadata(folder))


def _base_folder(slug: str) -> Path | None:
    if Path(slug).name != slug:
        raise HTTPException(400, "Invalid Base Target selection")
    candidates = [BASE_TARGET_ROOT / slug, BUNDLED_DATA_ROOT / "base-targets" / slug]
    candidates += [folder for folder in discover_collection("base-targets") if folder.name == slug]
    for folder in candidates:
        if folder.name == slug and (folder / "target_source.txt").is_file():
            return folder
    return None


def _canonical_base_folder() -> Path | None:
    return _base_folder(DEFAULT_BASE_ID)


def _base_target(slug: str | None = None) -> tuple[Path, dict[str, Any], Curve]:
    target_id = slug or DEFAULT_BASE_ID
    folder = _base_folder(target_id)
    if folder is None:
        raise HTTPException(404, f"Base Target not found: {target_id}")
    try:
        return folder, _metadata(folder), _read_curve(folder / "target_source.txt")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _legacy(meta: dict[str, Any]) -> bool:
    version = str(meta.get("engine", {}).get("target_version", ""))
    return bool(version and version not in {"0.3.1", "Personal EarPrint v0.3.1"})


def build_robust_target_name(base_name: str) -> str:
    """Apply the locked name rule without mutating the source name."""
    clean = base_name.strip()
    return clean if clean.endswith(" Robust") else f"{clean} Robust"


def _target_item(folder: Path) -> dict[str, Any]:
    meta = _metadata(folder)
    source = folder / "target_source.txt"
    try:
        curve = _read_curve(source) if source.exists() else None
        coverage = [curve.frequency_hz[0], curve.frequency_hz[-1]] if curve else None
        validation = {"valid_curve": curve is not None, "exact_1000_hz": bool(curve and 1000.0 in curve.frequency_hz), "coverage_hz": coverage}
        status = meta.get("status", "validated") if curve else "invalid"
    except ValueError as exc:
        validation = {"valid_curve": False, "error": str(exc)}
        status = "invalid"
    return {
        "name": meta.get("name", folder.name), "slug": folder.name, "kind": meta.get("kind", "base"),
        "status": status, "collection": "base-targets", "is_default": folder.name == DEFAULT_BASE_ID,
        "legacy": _legacy(meta), "has_source": source.exists(), "has_prepared": (folder / "target.csv").exists(),
        "metadata": meta, "validation": validation, "source": meta.get("source", "uploaded or bundled reference curve"),
    }


def _result(result: Any, target_id: str, meta: dict[str, Any], provenance: dict[str, Any], digest: str) -> dict[str, Any]:
    data = result.to_dict()
    source_name = str(meta.get("name", target_id)).strip()
    robust_name = build_robust_target_name(source_name)
    data.update({"base_target_id": target_id, "base_target_name": source_name, "robust_target_name": robust_name,
                 "active_iem_ids": list(result.personal_delta), "iem_count": len(result.personal_delta),
                 "target_hash": digest, "provenance": provenance, "status": "ready", "legacy_source": _legacy(meta)})
    data["validation"] = {
        "exact_1000_hz": 1000.0 in result.master_grid_hz, "master_grid_points": len(result.master_grid_hz),
        "base_exact_below_1k": all(a == b for a, b, f in zip(result.base_target.level_db, result.final_target.level_db, result.master_grid_hz) if f < 1000),
        "base_exact_at_or_above_12k": all(a == b for a, b, f in zip(result.base_target.level_db, result.final_target.level_db, result.master_grid_hz) if f >= 12000),
        "all_iems_retained": len(result.personal_delta) == 9, "coverage_hz": [result.base_target.frequency_hz[0], result.base_target.frequency_hz[-1]],
    }
    return data


def _registry_path(target_id: str) -> Path:
    if Path(target_id).name != target_id:
        raise HTTPException(400, "Invalid Robust Target id")
    return generated_target_root() / f"{target_id}.json"


@router.get("/engine/status")
def engine_status() -> dict[str, Any]:
    folders = discover_collection("iems")
    valid, skipped = 0, []
    for folder in folders:
        try:
            _iem(folder); valid += 1
        except (OSError, ValueError) as exc:
            skipped.append({"id": folder.name, "reason": str(exc)})
    return {"status": "ready" if valid >= 1 and _base_folder(DEFAULT_BASE_ID) else "not_ready", "engine": ENGINE_VERSION,
            "version": "0.3.1", "engine_math": "PersonalDelta-FullBand-0.3.1", "storage": storage_info(),
            "dataset": {"discovered_iems": len(folders), "valid_active_iems": valid, "skipped_iems": skipped},
            "base_target": DEFAULT_BASE_ID, "produces": ["robust_target_curve", "narrow_peak_diagnostics"]}


@router.get("/base-targets")
def base_targets() -> dict[str, Any]:
    return {"items": [_target_item(folder) for folder in discover_collection("base-targets") if folder.is_dir()]}


@router.get("/base-targets/{target_id}")
def base_target_detail(target_id: str) -> dict[str, Any]:
    folder, meta, curve = _base_target(target_id)
    item = _target_item(folder)
    item["curve"] = _curve(curve)
    item["source_text"] = (folder / "target_source.txt").read_text(encoding="utf-8", errors="replace")
    item["metadata"] = meta
    return item


@router.get("/base-targets/{target_id}/export", response_class=PlainTextResponse)
def export_base_target(target_id: str) -> str:
    folder, meta, curve = _base_target(target_id)
    header = f"# {meta.get('name', target_id)}\n# reference: Base Target\n"
    return header + "\n".join(f"{f:.6f}\t{y:.6f}" for f, y in zip(curve.frequency_hz, curve.level_db)) + "\n"


@router.delete("/base-targets/{target_id}")
def delete_base_target(target_id: str, confirm: bool = Query(False)) -> dict[str, Any]:
    folder, meta, _ = _base_target(target_id)
    if not confirm:
        raise HTTPException(400, "Deletion requires confirm=true")
    if target_id == DEFAULT_BASE_ID or folder.resolve().is_relative_to(BUNDLED_DATA_ROOT.resolve()):
        raise HTTPException(409, "The bundled Base Target is protected")
    active = []
    for p in generated_target_root().glob("*.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("base_target_id") == target_id:
                active.append(p)
        except (OSError, json.JSONDecodeError):
            continue
    if active:
        raise HTTPException(409, "Base Target is referenced by generated Robust Target history")
    shutil.rmtree(folder)
    return {"ok": True, "deleted": target_id, "name": meta.get("name", target_id)}


@router.get("/robust-targets")
def robust_targets() -> dict[str, Any]:
    items = []
    for path in sorted(generated_target_root().glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            items.append({"id": path.stem, "name": item.get("robust_target_name", path.stem), "base_target_name": item.get("base_target_name"), "base_target_id": item.get("base_target_id"), "created_at": item.get("created_at"), "status": item.get("status", "ready"), "legacy_source": item.get("legacy_source", False)})
        except (OSError, json.JSONDecodeError):
            continue
    return {"items": items}


@router.get("/robust-targets/{target_id}")
def robust_target_detail(target_id: str) -> dict[str, Any]:
    path = _registry_path(target_id)
    if not path.exists():
        raise HTTPException(404, "Robust Target not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Robust Target record is unreadable") from exc


@router.post("/robust-targets/generate")
def generate_target(payload: dict[str, Any]) -> dict[str, Any]:
    folder, meta, base = _base_target(payload.get("base_target_id"))
    folders = {f.name: f for f in discover_collection("iems")}
    ids = payload.get("iem_ids") or sorted(folders)
    if not isinstance(ids, list) or len(ids) != 9 or len(set(ids)) != 9:
        raise HTTPException(422, "v0.3.1 requires exactly nine distinct IEM votes")
    try:
        result = generate(base, [_iem(folders[item]) for item in ids])
    except (KeyError, OSError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    provenance = {"engine_version": ENGINE_VERSION, "algorithm_version": result.algorithm_version, "base_target_sha256": sha256_file(folder / "target_source.txt"), "iems": [{"id": f.name, "measurement_sha256": sha256_file(f / "measurement_source.txt"), "peq_sha256": sha256_file(f / "preferred.txt")} for f in sorted((folders[item] for item in ids), key=lambda p: p.name)]}
    digest = hashlib.sha256(json.dumps({"provenance": provenance, "curve": _curve(result.final_target)}, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    data = _result(result, folder.name, meta, provenance, digest)
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    _registry_path(digest).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


@router.get("/robust-targets/{target_id}/export", response_class=PlainTextResponse)
def export_target(target_id: str) -> str:
    data = robust_target_detail(target_id)
    curve = data.get("final_target")
    if not curve:
        raise HTTPException(422, "Robust Target has no exportable curve")
    header = f"# {data.get('robust_target_name', 'Robust Target')}\n# engine: {ENGINE_VERSION}\n# base_target: {data.get('base_target_name', '')}\n"
    return header + "\n".join(f"{f:.6f}\t{y:.6f}" for f, y in zip(curve["frequency_hz"], curve["level_db"])) + "\n"
