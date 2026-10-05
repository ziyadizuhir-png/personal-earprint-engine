from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .ingest import ingest_iem, ingest_target
from .storage import BASE_TARGET_ROOT, IEM_ROOT, TARGET_ROOT, ensure_data_dirs, storage_info
from .v44 import router as v44_router

ensure_data_dirs()
app = FastAPI(title="Personal Earprint Engine API", version="0.2.0-backbone")
app.include_router(v44_router)


def configured_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def read_metadata(folder: Path) -> dict:
    metadata_path = folder / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def list_collection(root: Path, collection_name: str) -> list[dict]:
    items = []
    for folder in sorted(root.iterdir()) if root.exists() else []:
        if not folder.is_dir():
            continue
        metadata = read_metadata(folder)
        items.append(
            {
                "name": metadata.get("name", folder.name),
                "slug": folder.name,
                "status": metadata.get("status", "unknown"),
                "kind": metadata.get("kind"),
                "collection": collection_name,
                "path": f"{collection_name}/{folder.name}",
                "has_metadata": (folder / "metadata.json").exists(),
                "has_source": any(path.name.endswith("_source.txt") for path in folder.iterdir()),
                "has_prepared": any(path.suffix == ".csv" for path in folder.iterdir()),
            }
        )
    return items


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": app.version,
        "cors_origins": configured_origins(),
        "storage": storage_info(),
    }


@app.get("/api/iems")
def list_iems():
    items = list_collection(IEM_ROOT, "iems")
    for item in items:
        folder = IEM_ROOT / item["slug"]
        item.update(
            {
                "has_measurement": (folder / "measurement.csv").exists(),
                "has_preferred": (folder / "preferred.txt").exists(),
            }
        )
    return {"items": items}


@app.get("/api/targets")
def list_targets():
    return {"items": list_collection(BASE_TARGET_ROOT, "base-targets") + list_collection(TARGET_ROOT, "targets")}


@app.post("/api/iems/import")
async def import_iem(
    name: str = Form(...),
    measurement_file: UploadFile = File(...),
    preferred_file: UploadFile = File(...),
    notes: str = Form(""),
):
    if not name.strip():
        raise HTTPException(status_code=400, detail="IEM name is required.")
    measurement_bytes = await measurement_file.read()
    preferred_bytes = await preferred_file.read()
    if not measurement_bytes:
        raise HTTPException(status_code=400, detail="Measurement file is empty.")
    if not preferred_bytes:
        raise HTTPException(status_code=400, detail="PEQ / preferred file is empty.")

    try:
        metadata = ingest_iem(name=name, measurement=measurement_bytes, preferred=preferred_bytes, notes=notes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="IEM directory collision.") from exc
    return {"ok": True, "item": metadata}


@app.post("/api/targets/import")
async def import_target(
    name: str = Form(...),
    target_file: UploadFile = File(...),
    kind: str = Form("base"),
    notes: str = Form(""),
):
    if not name.strip():
        raise HTTPException(status_code=400, detail="Target name is required.")
    target_bytes = await target_file.read()
    if not target_bytes:
        raise HTTPException(status_code=400, detail="Target file is empty.")

    try:
        metadata = ingest_target(name=name, target=target_bytes, kind=kind, notes=notes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="Target directory collision.") from exc
    return {"ok": True, "item": metadata}
