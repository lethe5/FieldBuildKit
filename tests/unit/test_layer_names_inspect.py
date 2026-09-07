"""Unit tests for qfield_builder.layer_names_inspect's defensive fallback behavior
(HARNESS_CONTRACT.md function 19; DR-QPB-078/FR-QPB-130/Section 8.7/AC-QPB-118; Decision Log
D-80/D-84).

Mirrors `tests/unit/test_relation_inspect.py`'s own structure: the real, PyQGIS-backed inspection
logic (opening a real `.qgs` project and reading back every GeoPackage-table-backed layer's own
`.name()`) is exercised end-to-end by `test_qgis_worker_layer_display_names.py` and by the
acceptance suite's `test_korean_layer_display_names.py` (both `qgis`-marked/skipped without a
real, bridgeable QGIS installation). This file covers the parts that do not require PyQGIS: the
direct-call ImportError short-circuit, and the public function's graceful fallback when no QGIS
bridge is available at all.
"""
from __future__ import annotations

from qfield_builder import layer_names_inspect


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = layer_names_inspect._inspect_layer_names_pyqgis("/nonexistent/project/dir")
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_names_inspect, "_inspect_layer_names_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = layer_names_inspect.inspect_layer_names("/nonexistent/project/dir")
    assert result == {"table_names": [], "names": {}}


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_names_inspect, "_inspect_layer_names_pyqgis", lambda *_a, **_k: None
    )
    fake_result = {
        "table_names": ["site", "survey"],
        "names": {"site": "조사지", "survey": "조사"},
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = layer_names_inspect.inspect_layer_names("/some/dir")
    assert result == fake_result


def test_public_function_falls_back_to_empty_result_when_bridge_job_fails(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        layer_names_inspect, "_inspect_layer_names_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": "boom"})

    result = layer_names_inspect.inspect_layer_names("/some/dir")
    assert result == {"table_names": [], "names": {}}
