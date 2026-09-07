"""Unit tests for qfield_builder.layer_renderer_inspect's defensive fallback behavior
(HARNESS_CONTRACT.md function 15; FR-QPB-120/FR-QPB-121/AC-QPB-100/AC-QPB-101/AC-QPB-104).

Mirrors `tests/unit/test_field_alias_inspect.py`'s own structure: the real, PyQGIS-backed
inspection logic (opening a real `.qgs` project and reading back its renderer/symbol via real
QGIS symbol-layer classes) is exercised end-to-end by the acceptance suite's
`test_symbol_styling.py` and by `test_qgis_worker_symbol_styling.py` (both `qgis`-marked/skipped
without a real, bridgeable QGIS installation). This file covers the parts that do not require
PyQGIS: the direct-call ImportError short-circuit, and the public function's graceful fallback
when no QGIS bridge is available at all.
"""
from __future__ import annotations

from qfield_builder import layer_renderer_inspect

_EMPTY_RESULT = {
    "renderer_class": "",
    "symbol_layer_types": [],
    "marker_shape": None,
    "svg_relative_path": None,
}


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = layer_renderer_inspect._inspect_layer_renderer_pyqgis(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_renderer_inspect, "_inspect_layer_renderer_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = layer_renderer_inspect.inspect_layer_renderer(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result == _EMPTY_RESULT


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_renderer_inspect, "_inspect_layer_renderer_pyqgis", lambda *_a, **_k: None
    )
    fake_result = {
        "renderer_class": "QgsSingleSymbolRenderer",
        "symbol_layer_types": ["SimpleMarker"],
        "marker_shape": "circle",
        "svg_relative_path": None,
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = layer_renderer_inspect.inspect_layer_renderer("/some/dir", "site")
    assert result == fake_result


def test_public_function_falls_back_to_empty_result_when_bridge_job_fails(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_renderer_inspect, "_inspect_layer_renderer_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": "boom"})

    result = layer_renderer_inspect.inspect_layer_renderer("/some/dir", "site")
    assert result == _EMPTY_RESULT
