from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .ingest import ingest_iem
from .storage import IEM_ROOT, ensure_data_dirs

ensure_data_dirs()

app = FastAPI(title="Personal Earprint Engine API", version="0.1.0-backbone")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0-backbone"}

@app.get("/api/iems")
def list_iems():
    items = []
    for folder in sorted(IEM_ROOT.iterdir()) if IEM_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        metadata_path = folder / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        items.append({
            "name": metadata.get("name", folder.name),
            "slug": folder.name,
            "status": metadata.get("status", "unknown"),
            "path": str(folder.relative_to(IEM_ROOT.parent.parent)),
            "has_measurement": (folder / "measurement.csv").exists(),
            "has_preferred": (folder / "preferred.txt").exists(),
            "has_metadata": metadata_path.exists(),
        })
    return {"items": items}

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
        metadata = ingest_iem(
            name=name,
            measurement=measurement_bytes,
            preferred=preferred_bytes,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="IEM directory collision.") from exc

    return {"ok": True, "item": metadata}
