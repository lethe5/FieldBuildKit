"""Unit tests for qfield_builder.relation_inspect's defensive fallback behavior
(HARNESS_CONTRACT.md function 18; FR-QPB-128/Section 8.6/AC-QPB-111; Decision Log D-73/D-77).

Mirrors `tests/unit/test_field_alias_inspect.py`'s own structure: the real, PyQGIS-backed
inspection logic (opening a real `.qgs` project and reading back each relation's `id()`/`name()`
via `QgsProject.relationManager()`) is exercised end-to-end by the acceptance suite's
`test_korean_relation_display_names.py` and by `test_qgis_worker_relations.py` (both `qgis`-marked/
skipped without a real, bridgeable QGIS installation). This file covers the parts that do not
require PyQGIS: the direct-call ImportError short-circuit, and the public function's graceful
fallback when no QGIS bridge is available at all.
"""
from __future__ import annotations

from qfield_builder import relation_inspect


def test_direct_pyqgis_call_returns_none_when_pyqgis_is_not_importable():
    """In this plain test environment (no PyQGIS on `sys.path`), the direct, in-process call must
    return None rather than raising, so the public function knows to fall back to the bridge."""
    result = relation_inspect._inspect_relations_pyqgis("/nonexistent/project/dir")
    assert result is None


def test_public_function_returns_the_empty_result_shape_when_no_bridge_is_available(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(relation_inspect, "_inspect_relations_pyqgis", lambda *_a, **_k: None)
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: None)

    result = relation_inspect.inspect_relations("/nonexistent/project/dir")
    assert result == {"relation_ids": [], "names": {}}


def test_public_function_uses_the_bridge_result_when_the_direct_call_is_unavailable(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(relation_inspect, "_inspect_relations_pyqgis", lambda *_a, **_k: None)
    fake_result = {
        "relation_ids": ["rel_survey_site", "rel_observation_survey"],
        "names": {"rel_survey_site": "조사", "rel_observation_survey": "식물관찰"},
    }
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": True, "result": fake_result}
    )

    result = relation_inspect.inspect_relations("/some/dir")
    assert result == fake_result


def test_public_function_falls_back_to_empty_result_when_bridge_job_fails(monkeypatch):
    from qfield_builder import qgis_bridge

    monkeypatch.setattr(relation_inspect, "_inspect_relations_pyqgis", lambda *_a, **_k: None)
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": "boom"})

    result = relation_inspect.inspect_relations("/some/dir")
    assert result == {"relation_ids": [], "names": {}}
