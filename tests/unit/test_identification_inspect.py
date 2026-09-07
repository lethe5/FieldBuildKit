"""Unit tests for qfield_builder.identification_inspect's defensive fallback behavior.

The real, PyQGIS-backed inspection logic (finding a `QgsAttributeEditorQmlElement`, and the
empirically-confirmed `sip.cast` downcast needed after a `.qgs` round trip -- see this module's
own docstring) is exercised end-to-end by the acceptance suite's
`test_post_mvp_identification_plugin.py` (`qgis`-marked, requires a real bridgeable QGIS
installation). This file covers the parts that do not require PyQGIS: the direct-call ImportError
short-circuit, and the public function's graceful fallback when no QGIS bridge is available at
all (mirrors `qfield_builder.validate`'s own tested fallback pattern).
"""
from __future__ import annotations

from qfield_builder import identification_inspect


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = identification_inspect._inspect_identification_widget_pyqgis(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        identification_inspect, "_inspect_identification_widget_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = identification_inspect.inspect_identification_widget(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result == {
        "qml_widget_field_found": False,
        "qml_widget_field_name": None,
        "embedded_in_attribute_form": False,
        "qml_code_present": False,
        "qml_code": "",
    }


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        identification_inspect, "_inspect_identification_widget_pyqgis", lambda *_a, **_k: None
    )
    fake_result = {
        "qml_widget_field_found": True,
        "qml_widget_field_name": "Identify attached photos",
        "embedded_in_attribute_form": True,
        "qml_code_present": True,
        "qml_code": "Column { }",
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = identification_inspect.inspect_identification_widget("/some/dir", "observation")
    assert result == fake_result
