from app.main import app
from app.v44 import v44_generate, v44_iems, v44_status, v44_targets


def test_v44_routes_are_attached_and_status_is_two_mode_only():
    paths = set(app.openapi()["paths"])
    assert {"/api/v44/status", "/api/v44/iems", "/api/v44/targets", "/api/v44/generate", "/api/v44/validate"} <= paths
    body = v44_status()
    assert body["target_modes"] == ["robust_target", "pure_earprint"]
    assert "Hybrid Graph" not in body["target_modes"]


def test_v44_discovers_real_library_and_base_target():
    iems = v44_iems()["items"]
    targets = v44_targets()["items"]
    assert iems
    assert all(item["has_prepared"] and item["has_preferred"] for item in iems)
    assert any(item["is_default"] for item in targets)


def test_v44_generate_uses_selected_real_iem_and_keeps_final_pending():
    iem = v44_iems()["items"][0]["id"]
    body = v44_generate({"mode": "pure_earprint", "iem_ids": [iem]})
    assert body["mode"] == "pure_earprint"
    assert body["final_target"] is None
    assert body["delta_safe"] is None
    assert body["per_iem"]


def test_v44_rejects_third_mode():
    iem = v44_iems()["items"][0]["id"]
    from fastapi import HTTPException
    try:
        v44_generate({"mode": "hybrid_graph", "iem_ids": [iem]})
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("third target mode was accepted")
