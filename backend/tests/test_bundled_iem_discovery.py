from pathlib import Path


def test_list_iems_validates_the_discovered_folder_not_only_data_root(monkeypatch, tmp_path: Path):
    import app.main as main

    bundled = tmp_path / "bundled" / "example"
    bundled.mkdir(parents=True)
    (bundled / "metadata.json").write_text('{"name":"Example"}', encoding="utf-8")
    (bundled / "measurement.csv").write_text("freq,db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    (bundled / "preferred.txt").write_text("Filter 1: ON PK Fc 1000 Hz Gain 1 dB Q 1\n", encoding="utf-8")
    monkeypatch.setattr(main, "discover_collection", lambda collection: [bundled] if collection == "iems" else [])
    assert main.list_iems()["items"][0]["ready"] is True
