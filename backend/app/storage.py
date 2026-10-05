from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def configured_data_root() -> Path:
    """Return the data root supplied by the deployment, or the local default."""
    configured = os.getenv("DATA_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return PROJECT_ROOT / "data"


class StorageBackend(Protocol):
    """Small storage contract so object storage or a database can be added later."""

    root: Path

    def ensure_data_dirs(self) -> None: ...

    def collection_root(self, collection: str) -> Path: ...

    def unique_dir(self, collection: str, slug: str) -> Path: ...


class FileSystemStorage:
    """Local adapter for development and persistent-volume deployments."""

    backend_name = "filesystem"

    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure_data_dirs(self) -> None:
        for collection in ("iems", "base-targets", "targets"):
            self.collection_root(collection).mkdir(parents=True, exist_ok=True)

    def collection_root(self, collection: str) -> Path:
        if collection not in {"iems", "base-targets", "targets"}:
            raise ValueError(f"Unknown storage collection: {collection}")
        return self.root / collection

    def unique_dir(self, collection: str, slug: str) -> Path:
        collection_root = self.collection_root(collection)
        candidate = collection_root / slug
        if not candidate.exists():
            return candidate
        index = 2
        while True:
            candidate = collection_root / f"{slug}-{index}"
            if not candidate.exists():
                return candidate
            index += 1


def build_storage() -> FileSystemStorage:
    backend = os.getenv("STORAGE_BACKEND", "filesystem").strip().lower()
    if backend != "filesystem":
        raise RuntimeError(
            f"Unsupported STORAGE_BACKEND={backend!r}. "
            "Add an adapter implementing StorageBackend before enabling it."
        )
    storage = FileSystemStorage(configured_data_root())
    storage.ensure_data_dirs()
    return storage


storage = build_storage()
DATA_ROOT = storage.root
IEM_ROOT = storage.collection_root("iems")
BASE_TARGET_ROOT = storage.collection_root("base-targets")
TARGET_ROOT = storage.collection_root("targets")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unnamed-item"


def ensure_data_dirs() -> None:
    storage.ensure_data_dirs()


def unique_iem_dir(slug: str) -> Path:
    return storage.unique_dir("iems", slug)


def unique_target_dir(slug: str, kind: str = "base") -> Path:
    collection = "base-targets" if kind == "base" else "targets"
    return storage.unique_dir(collection, slug)


def storage_info() -> dict[str, str | bool]:
    return {
        "backend": storage.backend_name,
        "data_root": str(DATA_ROOT),
        "data_root_exists": DATA_ROOT.exists(),
    }
