"""Unit tests for qfield_builder.editor_widget_inspect's defensive fallback behavior
(HARNESS_CONTRACT.md function 16; FR-QPB-122/AC-QPB-103).

Mirrors `tests/unit/test_field_alias_inspect.py`/`tests/unit/test_identification_inspect.py`'s own
structure: the real, PyQGIS-backed inspection logic (opening a real `.qgs` project and reading
back a field's configured editor widget type/config via `QgsEditorWidgetSetup`) is exercised
end-to-end by the acceptance suite's `test_qgis_project_config.py::test_ac103_*` tests and by
`test_qgis_worker_identification_status_widget.py` (both `qgis`-marked/skipped without a real,
bridgeable QGIS installation). This file covers the parts that do not require PyQGIS: the
direct-call ImportError short-circuit, and the public function's graceful fallback when no QGIS
bridge is available at all.
"""
from __future__ import annotations

from qfield_builder import editor_widget_inspect

# Sourced directly from the module's own `_EMPTY_RESULT` (rather than duplicated verbatim here) so
# this test never silently drifts out of sync when the module's result shape gains a new key (as
# it did in the Key/Value-swap fix round: `value_relation_key_column`/
# `value_relation_value_column`).
_EMPTY_RESULT = dict(editor_widget_inspect._EMPTY_RESULT)


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = editor_widget_inspect._inspect_editor_widget_pyqgis(
        "/nonexistent/project/dir", "inventory_observation", "identification_status"
    )
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        editor_widget_inspect, "_inspect_editor_widget_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = editor_widget_inspect.inspect_editor_widget(
        "/nonexistent/project/dir", "inventory_observation", "identification_status"
    )
    assert result == _EMPTY_RESULT


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        editor_widget_inspect, "_inspect_editor_widget_pyqgis", lambda *_a, **_k: None
    )
    fake_result = {
        "widget_type": "ValueMap",
        "value_map": {
            "not_requested": "not_requested",
            "pending": "pending",
            "complete": "complete",
            "failed": "failed",
            "manual": "manual",
        },
        "referenced_layer_name": None,
        "has_filter_or_completer_config": None,
        "default_value_expression": "'not_requested'",
        "apply_on_update": False,
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = editor_widget_inspect.inspect_editor_widget(
        "/some/dir", "inventory_observation", "identification_status"
    )
    assert result == fake_result


def test_public_function_falls_back_to_empty_result_when_bridge_job_fails(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        editor_widget_inspect, "_inspect_editor_widget_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": "boom"})

    result = editor_widget_inspect.inspect_editor_widget(
        "/some/dir", "inventory_observation", "identification_status"
    )
    assert result == _EMPTY_RESULT
