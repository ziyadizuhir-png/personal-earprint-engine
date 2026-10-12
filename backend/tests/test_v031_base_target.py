from pathlib import Path

import pytest

from app import robust_target


def test_canonical_base_target_falls_back_to_bundled_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    mounted = tmp_path / "mounted" / "base-targets" / robust_target.DEFAULT_BASE_ID
    bundled = tmp_path / "bundled" / "base-targets" / robust_target.DEFAULT_BASE_ID
    bundled.mkdir(parents=True)
    (bundled / "metadata.json").write_text('{"name":"Bundle Base"}', encoding="utf-8")
    (bundled / "target_source.txt").write_text("20 0\n1000 0\n20000 0\n", encoding="utf-8")
    monkeypatch.setattr(robust_target, "BASE_TARGET_ROOT", mounted.parent)
    monkeypatch.setattr(robust_target, "BUNDLED_DATA_ROOT", tmp_path / "bundled")

    listing = robust_target.base_targets()

    assert robust_target.DEFAULT_BASE_ID in {item["slug"] for item in listing["items"]}
    assert robust_target._canonical_base_folder() == bundled
    assert robust_target._base_target()[0] == bundled


def test_noncanonical_base_target_can_be_selected_as_a_reference_input():
    folder, metadata, curve = robust_target._base_target("5128-df-tilt-0-8-db-oct-b105-5-db")
    assert folder.name == "5128-df-tilt-0-8-db-oct-b105-5-db"
    assert metadata["name"].startswith("5128 DF")
    assert curve.frequency_hz[0] <= 20


def test_robust_target_name_uses_selected_base_name_once():
    assert robust_target.build_robust_target_name("My Custom Target") == "My Custom Target Robust"
    assert robust_target.build_robust_target_name("My Custom Target Robust") == "My Custom Target Robust"
