"""Implementation-level coverage for the integrated report data contract."""

from __future__ import annotations

import json
import re

from qfield_builder.html_report_core import (
    render_html_report_fixture,
    render_html_report_integrated_fixture,
)
from qfield_builder.qml_plugin import render_project_plugin_qml


def _standalone_runtime(source: str) -> str:
    scripts = []
    for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source):
        script = json.loads(match.group(1))
        if script.startswith("<script>"):
            scripts.append(script)
    return "\n".join(scripts)


def test_semantic_columns_share_one_key_without_losing_falsey_values():
    result = render_html_report_integrated_fixture(
        {
            "source_columns": [
                {
                    "id": "left",
                    "source_table": "joined",
                    "source_field": "selected_ktsn",
                    "semantic_identity": "selected_ktsn",
                    "schema_order": 0,
                },
                {
                    "id": "right",
                    "source_table": "inventory_observation",
                    "source_field": "selected_ktsn",
                    "semantic_identity": "selected_ktsn",
                    "schema_order": 1,
                },
            ],
            "source_rows": [
                {"source_row_id": "zero", "values": {"left": 0, "right": 0}},
                {"source_row_id": "missing", "values": {"left": False}},
            ],
        }
    )

    key = result["source_to_final_key"]["left"]
    assert result["success"] is True
    assert key == result["source_to_final_key"]["right"]
    rows = {row["source_row_id"]: row["values"] for row in result["payload_rows"]}
    assert rows["zero"][key] == 0 and type(rows["zero"][key]) is int
    assert rows["missing"][key] is False
    assert result["source_value_presence"]["missing"]["right"] is False


def test_direct_cards_and_theme_do_not_depend_on_join_fanout():
    result = render_html_report_integrated_fixture(
        {
            "survey_type": "simple_inventory",
            "source_columns": [
                {"id": "id", "source_table": "joined", "source_field": "id", "schema_order": 0}
            ],
            "source_rows": [{"source_row_id": "joined-1", "values": {"id": "joined-1"}}] * 4,
            "direct_sources": {
                "inventory_observation": {
                    "schema_present": True,
                    "records": [
                        {"observed_at": "2026-01-01", "selected_ktsn": "K-1"},
                        {"observed_at": "2026-01-01T10:00:00", "selected_ktsn": "K-1"},
                        {"observed_at": "bad", "selected_ktsn": None},
                    ],
                }
            },
            "theme_interaction": {
                "initial_theme": "light",
                "storage_available": True,
                "actions": [{"kind": "click"}, {"kind": "reopen"}],
                "state": {"selected_detail_id": "joined-1"},
            },
        }
    )

    cards = {card["label"]: card["value"] for card in result["overview_cards"]}
    assert cards == {"총 조사일 수": 1, "관찰 수": 3, "총 종수": 1}
    assert any(
        item["kind"] == "invalid_or_missing_date" and item["count"] == 1
        for item in result["limitations"]
    )
    assert any(
        item["kind"] == "invalid_ktsn" and item["count"] == 1 for item in result["limitations"]
    )
    assert [state["theme"] for state in result["theme_states"]] == ["light", "dark", "dark"]
    assert all(
        state["report_state"] == {"selected_detail_id": "joined-1"}
        for state in result["theme_states"]
    )


def test_wgs84_geometry_is_kept_when_coordinate_transform_is_unavailable():
    result = render_html_report_integrated_fixture(
        {
            "source_columns": [
                {
                    "id": "id",
                    "source_table": "inventory_observation",
                    "source_field": "id",
                    "schema_order": 0,
                }
            ],
            "source_rows": [
                {
                    "source_row_id": "valid",
                    "values": {"id": "valid"},
                    "geometry": {"format": "wkt", "value": "POINT (127 37)"},
                },
                {
                    "source_row_id": "invalid",
                    "values": {"id": "invalid"},
                    "geometry": {"format": "wkt", "value": "POINT (wrong 37)"},
                },
            ],
            "spatial_metadata": [
                {
                    "table": "inventory_observation",
                    "geometry_column": "geom",
                    "geometry_type": "POINT",
                    "source_crs": "EPSG:4326",
                    "record_ids": ["valid", "invalid"],
                }
            ],
            "coordinate_transform_available": False,
        }
    )

    assert result["map_features"] == [
        {
            "source_row_id": "valid",
            "stable_source_id": "valid",
            "geometry": {"type": "Point", "coordinates": [127.0, 37.0]},
            "joined_attributes": {
                "report__latitude": "37.00000000",
                "report__longitude": "127.00000000",
            },
        }
    ]
    assert result["invalid_geometries"][0]["source_row_id"] == "invalid"
    assert result["map_empty_notice_present"] is False


def test_type1_overview_and_standalone_runtime_are_canonical():
    result = render_html_report_integrated_fixture(
        {
            "survey_type": "simple_inventory",
            "source_columns": [],
            "source_rows": [],
        }
    )
    source = render_project_plugin_qml(
        "type1-runtime", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _standalone_runtime(source)

    assert [card["label"] for card in result["overview_cards"]] == [
        "총 조사일 수",
        "관찰 수",
        "총 종수",
    ]
    assert 'type1Labels=["총 조사일 수","관찰 수","총 종수"]' in runtime
    for name in (
        "qpbApplyTheme",
        "qpbToggleTheme",
        "renderCards",
        "renderMap",
        "renderSummaries",
        "renderJoined",
        "saveCsv",
        "renderCharts",
        "detailForFeature",
        "qpbMapFeatureDetail",
        "qpbInitializeReport",
    ):
        assert len(re.findall(rf"function\s+{name}\s*\(", runtime)) == 1, name


def test_theme_binds_before_renderer_errors_and_wgs84_fallback_uses_xy_geometry():
    source = render_project_plugin_qml(
        "theme-runtime", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _standalone_runtime(source)
    initialization = runtime[runtime.index("function qpbInitializeReport(){") :]
    assert initialization.index("qpbBindThemeControl()") < initialization.index(
        'qpbRunRenderer(renderCards,"개요")'
    )
    assert 'document.documentElement.setAttribute("data-theme",selected)' in runtime
    assert 'document.body.classList.add(isDark?"dark-theme":"light-theme")' in runtime
    assert 'input.addEventListener("change",qpbToggleTheme)' in runtime
    assert 'qpbLayerCrs(layer, table.geometry_crs)' in source

    result = render_html_report_fixture(
        {
            "direct_access": {"status": "failed", "path": "saved.gpkg"},
            "layer_crs_unavailable": True,
            "source_columns": [{"id": "id", "source_table": "inventory_observation", "source_field": "id"}],
            "source_rows": [
                {
                    "source_row_id": "wgs84-zm",
                    "values": {"id": "wgs84-zm"},
                    "geometry": {
                        "format": "geojson",
                        "value": {"type": "Point", "coordinates": [127, 37, 10, 20]},
                    },
                }
            ],
        }
    )
    assert result["success"] is True
    assert result["map_feature_ids"] == ["wgs84-zm"]
    assert result["normalized_geometry_by_row"]["wgs84-zm"] == {
        "type": "Point",
        "coordinates": [127, 37],
    }
