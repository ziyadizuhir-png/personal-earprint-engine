from app.main import app
from app.v44 import _base_target, _default_target_folder, v44_generate, v44_iems, v44_status, v44_targets
from fastapi import HTTPException
import json


def test_routes_are_attached_and_legacy_status_has_no_pure_mode():
    paths = set(app.openapi()["paths"])
    assert {"/api/v44/status", "/api/v44/iems", "/api/v44/targets", "/api/v44/generate", "/api/v44/validate"} <= paths
    body = v44_status()
    assert body["target_modes"] == ["robust_target"]
    assert "Hybrid Graph" not in body["target_modes"]


def test_v44_discovers_real_library_and_base_target():
    iems = v44_iems()["items"]
    targets = v44_targets()["items"]
    assert iems
    assert all(item["has_prepared"] and item["has_preferred"] for item in iems)
    defaults = [item for item in targets if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)"
    assert v44_status()["resolved_base_target"] == "JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)"


def test_v44_generate_uses_selected_real_iem():
    iem = v44_iems()["items"][0]["id"]
    body = v44_generate({"mode": "robust_target", "iem_ids": [iem]})
    assert body["mode"] == "robust_target"
    assert body["final_target"] is not None
    assert body["delta_safe"] is not None
    assert body["base_target_info"]["name"] == "JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)"
    assert body["selected_base_target"]["slug"] == "headphones-com-iem-df-b105-8-db"
    assert body["iem_count"] == 1
    assert body["exact_1000_hz"] is True
    assert "Broad" in body["unresolved_stages"]


def test_v44_rejects_third_mode():
    iem = v44_iems()["items"][0]["id"]
    try:
        v44_generate({"mode": "hybrid_graph", "iem_ids": [iem]})
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("third target mode was accepted")


def test_v44_rejects_duplicate_iem_votes():
    iem = v44_iems()["items"][0]["id"]
    with __import__("pytest").raises(HTTPException) as duplicate:
        v44_generate({"mode": "robust_target", "iem_ids": [iem, iem]})
    assert duplicate.value.status_code == 400


def test_v44_real_dataset_runs_all_nine_votes_to_spec_blocker():
    ids = [item["id"] for item in v44_iems()["items"]]
    assert len(ids) == 9
    result = v44_generate({"mode": "robust_target", "iem_ids": ids})
    assert result["iem_count"] == 9
    assert result["selected_base_target"]["name"] == "JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)"
    assert result["final_target"] is not None
    assert result["delta_safe"] is not None


def test_default_target_resolution_is_exact_and_fail_closed(tmp_path, monkeypatch):
    import app.v44 as v44
    monkeypatch.setattr(v44, "BASE_TARGET_ROOT", tmp_path)
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    (wrong / "metadata.json").write_text(json.dumps({"name": "Headphones.com IEM DF (Tilt -0.8 dB/oct, B105 5 dB)"}), encoding="utf-8")
    assert _default_target_folder() is None
    with __import__("pytest").raises(HTTPException) as missing:
        _base_target()
    assert missing.value.status_code == 404
    exact = tmp_path / "exact"
    exact.mkdir()
    (exact / "metadata.json").write_text(json.dumps({"name": "JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)", "files": {"target": "target.csv"}}), encoding="utf-8")
    (exact / "target.csv").write_text("freq,db\n20,0\n1000,0\n14000,0\n20000,0\n", encoding="utf-8")
    assert _default_target_folder() == exact
    assert _base_target()[0] == exact


def test_base_target_errors_are_fastapi_errors(tmp_path, monkeypatch):
    import app.v44 as v44
    monkeypatch.setattr(v44, "BASE_TARGET_ROOT", tmp_path)
    with __import__("pytest").raises(HTTPException) as missing:
        _base_target("does-not-exist")
    assert missing.value.status_code == 404
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "metadata.json").write_text(json.dumps({}), encoding="utf-8")
    with __import__("pytest").raises(HTTPException) as no_file:
        _base_target("broken")
    assert no_file.value.status_code == 422
    with __import__("pytest").raises(HTTPException) as invalid:
        _base_target("../broken")
    assert invalid.value.status_code == 400
