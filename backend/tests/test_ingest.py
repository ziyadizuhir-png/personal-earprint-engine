from pathlib import Path

import pytest

from app.ingest import ingest_target, parse_measurement, prepare_measurement


def test_prepare_measurement_adds_exact_1000_hz(tmp_path: Path):
    source = tmp_path / "source.txt"
    output = tmp_path / "prepared.csv"
    source.write_text("20 -2\n987 1\n1001 1.1\n20000 -1\n", encoding="utf-8")

    info = prepare_measurement(source, output)

    assert info["added_1000_hz_point"] is True
    assert "1000" in output.read_text(encoding="utf-8")


def test_parse_measurement_rejects_data_without_1000_hz_coverage(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("20 -2\n500 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cover 1000 Hz"):
        parse_measurement(source)


def test_ingest_target_keeps_source_and_marks_math_unapplied(monkeypatch, tmp_path: Path):
    import app.ingest as ingest_module

    target_root = tmp_path / "base-targets"
    monkeypatch.setattr(ingest_module, "unique_target_dir", lambda slug, kind="base": target_root / slug)
    metadata = ingest_target("Base Target", b"20 -2\n1000 0\n20000 -1\n")

    item_dir = target_root / "base-target"
    assert (item_dir / "target_source.txt").read_bytes().startswith(b"20 -2")
    assert (item_dir / "target.csv").exists()
    assert metadata["engine"]["mathematics_applied"] is False
