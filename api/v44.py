"""Small FastAPI adapter for the V4.4 typed engine.

The adapter is optional so the legacy command-line build remains dependency
compatible. Applications can provide repositories for their own storage.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.v44_engine import Curve, IEMInput, generate

try:
    from fastapi import FastAPI, HTTPException
except ImportError:  # pragma: no cover - runtime-only optional dependency
    FastAPI = None


def create_app(base_target: Curve | None = None, iems: list[IEMInput] | None = None):
    if FastAPI is None:
        raise RuntimeError("Install fastapi to use the V4.4 HTTP adapter")
    app = FastAPI(title="ZUHIR Personal Earprint V4.4")
    base = base_target
    library = iems or []

    @app.get("/api/v44/status")
    def status() -> dict[str, Any]:
        return {"version": "4.4", "target_modes": ["robust_target", "pure_earprint"], "default_target": "Headphones.com IEM DF (B105 + 8 dB)", "locked_pending": ["G", "C", "Broad", "Local", "Feature Classification", "Delta Safe"]}

    @app.get("/api/v44/iems")
    def iems_endpoint() -> list[dict[str, Any]]:
        return [{"id": x.id, "metadata": x.metadata} for x in library]

    @app.get("/api/v44/targets")
    def targets() -> list[dict[str, str]]:
        return [{"id": "headphones-com-iem-df-b105-plus-8db", "name": "Headphones.com IEM DF (B105 + 8 dB)", "default": "true"}]

    @app.post("/api/v44/generate")
    def generate_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
        if base is None:
            raise HTTPException(503, "base target repository is not configured")
        selected = [x for x in library if x.id in payload.get("iem_ids", [])]
        try:
            return generate(base, selected, payload.get("mode", "robust_target")).to_dict()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/v44/validate")
    def validate(payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "pending", "message": "Validation requires a generated result; undefined V4.4 stages are not fabricated."}

    return app
