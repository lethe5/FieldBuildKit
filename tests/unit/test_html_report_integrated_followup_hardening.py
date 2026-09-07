"""Implementation-level regressions for integrated report hardening."""

from __future__ import annotations

from qfield_builder import qml_plugin
from qfield_builder.html_report_core import render_html_report_fixture


def test_final_column_mapping_preserves_present_null_and_omits_absent_source_value():
    result = render_html_report_fixture(
        {
            "source_columns": [
                {
                    "id": "first",
                    "source_table": "A-B",
                    "source_field": "C D",
                    "schema_order": 0,
                },
                {
                    "id": "second",
                    "source_table": "A_B",
                    "source_field": "C-D",
                    "schema_order": 1,
                },
            ],
            "source_rows": [
                {"source_row_id": "present-null", "values": {"first": None, "second": False}},
                {"source_row_id": "absent", "values": {"second": 0}},
            ],
        }
    )

    assert result["success"] is True
    keys = {item["source_column_id"]: item["key"] for item in result["column_definitions"]}
    rows = {item["source_row_id"]: item["values"] for item in result["integrated_rows"]}
    assert rows["present-null"] == {keys["first"]: None, keys["second"]: False}
    assert rows["absent"] == {keys["second"]: 0}


def test_direct_success_has_no_fallback_notice_or_partial_inventory_claim():
    result = render_html_report_fixture(
        {
            "source_columns": [
                {"id": "id", "source_table": "rows", "source_field": "id", "schema_order": 0}
            ],
            "direct_access": {"status": "success", "path": "project.gpkg direct SQLite"},
            "source_rows": [{"source_row_id": "one", "values": {"id": "one"}}],
        }
    )

    assert result["fallback"] == {
        "used": False,
        "source": None,
        "failed_direct_path": None,
    }
    assert result["limitation_notice_text"] == ""
    assert result["inventory_status"] == "complete"
    assert result["claims_complete_direct_inventory"] is True


def test_malformed_geojson_object_is_row_isolated_and_later_geometry_still_maps():
    result = render_html_report_fixture(
        {
            "source_columns": [
                {"id": "id", "source_table": "rows", "source_field": "id", "schema_order": 0}
            ],
            "source_rows": [
                {
                    "source_row_id": "bad",
                    "values": {"id": "bad"},
                    "geometry": {
                        "format": "object",
                        "value": {"type": "Point", "coordinates": ["broken", 37, 99]},
                    },
                },
                {
                    "source_row_id": "good",
                    "values": {"id": "good"},
                    "geometry": {
                        "format": "geojson",
                        "value": {"type": "Point", "coordinates": [127, 37, 99, 100]},
                    },
                },
            ],
        }
    )

    assert result["success"] is True
    assert result["map_feature_ids"] == ["good"]
    assert result["normalized_geometry_by_row"]["bad"] is None
    assert result["normalized_geometry_by_row"]["good"] == {
        "type": "Point",
        "coordinates": [127, 37],
    }
    assert [item["source_row_id"] for item in result["invalid_geometries"]] == ["bad"]
    assert len(result["integrated_rows"]) == 2


def test_malformed_wkb_is_row_isolated_without_stopping_following_row():
    result = render_html_report_fixture(
        {
            "source_columns": [
                {"id": "id", "source_table": "rows", "source_field": "id", "schema_order": 0}
            ],
            "source_rows": [
                {
                    "source_row_id": "bad-wkb",
                    "values": {"id": "bad-wkb"},
                    "geometry": {"format": "wkb", "value": "010100000000"},
                },
                {
                    "source_row_id": "after-wkb",
                    "values": {"id": "after-wkb"},
                    "geometry": {"format": "wkt", "value": "POINT (127 37)"},
                },
            ],
        }
    )

    assert result["success"] is True
    assert result["map_feature_ids"] == ["after-wkb"]
    assert result["normalized_geometry_by_row"]["bad-wkb"] is None
    assert "WKB" in result["invalid_geometries"][0]["reason"]
    assert {row["source_row_id"] for row in result["integrated_rows"]} == {
        "bad-wkb",
        "after-wkb",
    }


def test_generated_qml_uses_shared_final_key_projection_and_structured_fallback_surface():
    source = qml_plugin.render_project_plugin_qml(
        "hardening", identification_enabled=False, survey_type="simple_inventory"
    )

    assert "function qpbReserveFinalKey(baseKey, usedKeys)" in source
    assert "row.values = qpbProjectSourceValues(logicalValues, columns);" in source
    assert "source_column_id:sourceColumnId" in source
    assert "function qpbPublishFallbackLimitation(metadata)" in source
    assert "successful_fallback_reads" in source
    assert "unverifiable_scopes" in source
    assert "claims_complete_direct_inventory" in source
    assert "Every decoder/normalizer/transform is row-isolated" in source
