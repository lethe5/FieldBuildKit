"""Unit tests for qfield_builder.field_alias_inspect's defensive fallback behavior
(HARNESS_CONTRACT.md function 12; DR-QPB-071/FR-QPB-119/Section 8.5/AC-QPB-098).

Mirrors `tests/unit/test_identification_inspect.py`'s own structure: the real, PyQGIS-backed
inspection logic (opening a real `.qgs` project and reading back each field's alias via
`QgsField.alias()`) is exercised end-to-end by the acceptance suite's
`test_korean_field_aliases.py` and by `test_qgis_worker_field_aliases.py` (both `qgis`-marked/
skipped without a real, bridgeable QGIS installation). This file covers the parts that do not
require PyQGIS: the direct-call ImportError short-circuit, and the public function's graceful
fallback when no QGIS bridge is available at all.
"""
from __future__ import annotations

from qfield_builder import field_alias_inspect


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = field_alias_inspect._inspect_field_aliases_pyqgis(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        field_alias_inspect, "_inspect_field_aliases_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = field_alias_inspect.inspect_field_aliases(
        "/nonexistent/project/dir", "inventory_observation"
    )
    assert result == {"field_names": [], "aliases": {}}


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        field_alias_inspect, "_inspect_field_aliases_pyqgis", lambda *_a, **_k: None
    )
    fake_result = {
        "field_names": ["site_id", "site_name"],
        "aliases": {"site_id": "", "site_name": "사이트명"},
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = field_alias_inspect.inspect_field_aliases("/some/dir", "site")
    assert result == fake_result


def test_public_function_falls_back_to_empty_result_when_bridge_job_fails(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(
        field_alias_inspect, "_inspect_field_aliases_pyqgis", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": "boom"}
    )

    result = field_alias_inspect.inspect_field_aliases("/some/dir", "site")
    assert result == {"field_names": [], "aliases": {}}
