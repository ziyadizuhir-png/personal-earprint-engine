from pathlib import Path

import numpy as np
import pytest

from app.ingest import ingest_iem
from app.v44 import _iem, v44_generate, v44_iems
from engine.v44_engine import Curve, reconstruct_peq, parse_peq


def _write_metadata(folder: Path, name: str = "Temporary IEM") -> None:
    (folder / "metadata.json").write_text(
        '{"name": "' + name + '", "slug": "temporary-iem"}',
        encoding="utf-8",
    )


def test_uploaded_preferred_peq_reaches_v44_generation_and_changes_output(monkeypatch, tmp_path: Path):
    import app.ingest as ingest_module
    import app.v44 as v44_module

    iem_root = tmp_path / "iems"
    monkeypatch.setattr(ingest_module, "unique_iem_dir", lambda slug: iem_root / slug)
    metadata = ingest_iem(
        "Temporary IEM",
        b"20 0\n1000 0\n2000 0\n12000 0\n14000 0\n20000 0\n",
        b"Filter 1: ON PK Fc 1000 Hz Gain 2 dB Q 1\n",
    )
    folder = iem_root / "temporary-iem"
    monkeypatch.setattr(v44_module, "IEM_ROOT", iem_root)
    monkeypatch.setattr(v44_module, "discover_collection", lambda collection: [folder] if collection == "iems" else [])
    base = Curve([20.0, 1000.0, 2000.0, 12000.0, 14000.0, 20000.0], [0.0] * 6)
    target_folder = tmp_path / "base-target"
    target_folder.mkdir()
    _write_metadata(target_folder, "Test Base")
    monkeypatch.setattr(v44_module, "_base_target", lambda slug=None: (target_folder, {"name": "Test Base", "slug": "test-base"}, base))

    listing = v44_iems()["items"][0]
    assert metadata["source_hashes"]["preferred_sha256"]
    assert listing["has_preferred"] is True
    assert listing["peq_valid"] is True
    assert listing["peq_filter_count"] == 1

    first = v44_generate({"mode": "robust_target", "iem_ids": ["temporary-iem"], "target_id": "test-base"})
    expected = reconstruct_peq(parse_peq("Filter 1: ON PK Fc 1000 Hz Gain 2 dB Q 1\n"), np.asarray(base.frequency_hz))
    actual = np.asarray(first["per_iem"]["temporary-iem"]["reconstructed_peq"]["level_db"])
    assert np.allclose(actual, expected)
    assert not np.allclose(actual, 0.0)

    (folder / "preferred.txt").write_text("Filter 1: ON PK Fc 1000 Hz Gain 6 dB Q 1\n", encoding="utf-8")
    second = v44_generate({"mode": "robust_target", "iem_ids": ["temporary-iem"], "target_id": "test-base"})
    assert second["per_iem"]["temporary-iem"]["reconstructed_peq"] != first["per_iem"]["temporary-iem"]["reconstructed_peq"]


@pytest.mark.parametrize(
    "preferred, expected",
    [(None, "missing"), ("Filter 1: ON PK Fc nope Hz Gain 1 dB Q 1\n", "Malformed")],
)
def test_missing_or_malformed_preferred_blocks_generation(monkeypatch, tmp_path: Path, preferred: str | None, expected: str):
    import app.v44 as v44_module

    iem_root = tmp_path / "iems"
    folder = iem_root / "broken-iem"
    folder.mkdir(parents=True)
    (folder / "measurement.csv").write_text("freq,db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    _write_metadata(folder, "Broken IEM")
    if preferred is not None:
        (folder / "preferred.txt").write_text(preferred, encoding="utf-8")
    monkeypatch.setattr(v44_module, "IEM_ROOT", iem_root)
    monkeypatch.setattr(v44_module, "discover_collection", lambda collection: [folder] if collection == "iems" else [])
    item = v44_iems()["items"][0]
    assert item["peq_valid"] is False
    assert expected in item["peq_error"]
    with pytest.raises(ValueError, match="invalid SoundEQ Dore PEQ"):
        _iem(folder)
