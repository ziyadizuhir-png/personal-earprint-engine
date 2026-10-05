from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT.parent / "data"
IEM_ROOT = DATA_ROOT / "iems"

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unnamed-iem"

def ensure_data_dirs() -> None:
    for path in [
        DATA_ROOT / "iems",
        DATA_ROOT / "base-targets",
        DATA_ROOT / "targets",
    ]:
        path.mkdir(parents=True, exist_ok=True)

def unique_iem_dir(slug: str) -> Path:
    candidate = IEM_ROOT / slug
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = IEM_ROOT / f"{slug}-{index}"
        if not candidate.exists():
            return candidate
        index += 1
