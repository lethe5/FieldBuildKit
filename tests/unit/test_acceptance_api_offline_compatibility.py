"""The acceptance API preserves D-94's explicit offline-layer selection contract."""
from __future__ import annotations

from qfield_builder import acceptance_api


def test_missing_offline_selection_reaches_the_build_without_an_implicit_default(monkeypatch):
    config = {
        "basemap": {
            "mode": "offline",
            "vworld_api_key": "ACCEPTANCE-TEST-FAKE-KEY-OFFLINE",
        }
    }
    captured = {}

    def fake_build(received_config, output_dir):
        captured["config"] = received_config
        captured["output_dir"] = output_dir
        return {"success": False, "error_code": "offline_layer_unavailable"}

    monkeypatch.setattr(acceptance_api, "_build_project", fake_build)

    result = acceptance_api.build_project(config, "ignored-output")

    assert result["error_code"] == "offline_layer_unavailable"
    assert captured["config"] is config
    assert "layer" not in captured["config"]["basemap"]
    assert "layer" not in config["basemap"]


def test_explicit_offline_selection_reaches_the_build_unchanged(monkeypatch):
    config = {
        "basemap": {
            "mode": "offline",
            "vworld_api_key": "ACCEPTANCE-TEST-FAKE-KEY-FOLLOWUP",
            "layer": "Satellite",
        }
    }
    captured = {}

    def fake_build(received_config, output_dir):
        captured["config"] = received_config
        return {"success": True}

    monkeypatch.setattr(acceptance_api, "_build_project", fake_build)

    assert acceptance_api.build_project(config, "ignored-output")["success"] is True
    assert captured["config"] is config
    assert captured["config"]["basemap"]["layer"] == "Satellite"
