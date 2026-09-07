"""Executable acceptance coverage for AC-IRF-018..020.

The tests drive the same report transformation/rendering pipeline through the narrow
``render_html_report_fixture`` acceptance seam documented in ``HARNESS_CONTRACT.md``.  Fixtures
are synthetic and repository-local: no QGIS application, user profile, GeoPackage, browser, or
network service is opened by this module.
"""

from __future__ import annotations

import copy
import csv
import io
from typing import Any

import pytest


@pytest.fixture()
def render_html_report_fixture(acceptance_api):
    renderer = getattr(acceptance_api, "render_html_report_fixture", None)
    if renderer is None:
        pytest.skip(
            "qfield_builder.acceptance_api.render_html_report_fixture() is not implemented yet "
            "— see tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md"
        )
    return renderer


def _run(renderer, fixture: dict[str, Any]) -> dict[str, Any]:
    original = copy.deepcopy(fixture)
    result = renderer(fixture)
    assert fixture == original, "report rendering must not mutate source schema, rows, or values"
    assert result["success"] is True, result.get("error_message")
    return result


def _column_keys(result: dict[str, Any]) -> dict[str, str]:
    definitions = result["column_definitions"]
    assert len({definition["key"] for definition in definitions}) == len(definitions)
    return {definition["source_column_id"]: definition["key"] for definition in definitions}


def _projection(result: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    rows = result[name]
    assert len({row["source_row_id"] for row in rows}) == len(rows)
    return {row["source_row_id"]: row["values"] for row in rows}


def _csv_rows(result: dict[str, Any], row_id_key: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(result["csv_text"]))
    assert reader.fieldnames is not None
    rows = list(reader)
    return reader.fieldnames, {row[row_id_key]: row for row in rows}


def _collision_fixture() -> dict[str, Any]:
    return {
        "source_columns": [
            {
                "id": "row_id",
                "source_table": "Fixture",
                "source_field": "Row ID",
                "schema_order": 0,
            },
            {
                "id": "collision_zero",
                "source_table": "Specimen Table",
                "source_field": "Quality-Flag",
                "schema_order": 1,
            },
            {
                "id": "collision_false",
                "source_table": "Specimen_Table",
                "source_field": "Quality Flag",
                "schema_order": 2,
            },
            {
                "id": "collision_empty",
                "source_table": "Specimen--Table",
                "source_field": "Quality__Flag",
                "schema_order": 3,
            },
        ],
        "source_rows": [
            {
                "source_row_id": "collision-row-1",
                "values": {
                    "row_id": "collision-row-1",
                    "collision_zero": 0,
                    "collision_false": False,
                    "collision_empty": "",
                },
            },
            {
                "source_row_id": "collision-row-2",
                "values": {
                    "row_id": "collision-row-2",
                    "collision_zero": None,
                    "collision_false": "false-column-sentinel",
                    "collision_empty": "empty-column-sentinel",
                },
            },
            {
                "source_row_id": "collision-row-3",
                "values": {
                    "row_id": "collision-row-3",
                    # collision_zero is genuinely absent, unlike row 2's present null.
                    "collision_false": 0,
                    "collision_empty": False,
                },
            },
        ],
    }


def test_ac018_collision_suffixes_move_every_value_without_overwrite_and_repeat_stably(
    render_html_report_fixture,
):
    fixture = _collision_fixture()
    first = _run(render_html_report_fixture, fixture)
    second = _run(render_html_report_fixture, copy.deepcopy(fixture))

    expected_keys = {
        "row_id": "fixture__row_id",
        "collision_zero": "specimen_table__quality_flag",
        "collision_false": "specimen_table__quality_flag_2",
        "collision_empty": "specimen_table__quality_flag_3",
    }
    assert _column_keys(first) == expected_keys
    assert _column_keys(second) == expected_keys

    expected_collision_values = {
        "collision-row-1": {
            expected_keys["collision_zero"]: 0,
            expected_keys["collision_false"]: False,
            expected_keys["collision_empty"]: "",
        },
        "collision-row-2": {
            expected_keys["collision_zero"]: None,
            expected_keys["collision_false"]: "false-column-sentinel",
            expected_keys["collision_empty"]: "empty-column-sentinel",
        },
        "collision-row-3": {
            expected_keys["collision_false"]: 0,
            expected_keys["collision_empty"]: False,
        },
    }
    collision_key_set = set(expected_keys.values()) - {expected_keys["row_id"]}
    for projection_name in ("integrated_rows", "detail_rows", "payload_rows"):
        rows = _projection(first, projection_name)
        assert set(rows) == set(expected_collision_values)
        for row_id, expected in expected_collision_values.items():
            actual = rows[row_id]
            assert {key: actual[key] for key in expected} == expected
            assert {key for key in actual if key in collision_key_set} == set(expected)

    header, csv_rows = _csv_rows(first, expected_keys["row_id"])
    assert len(header) == len(set(header))
    assert [key for key in header if key.startswith("specimen_table__quality_flag")] == [
        expected_keys["collision_zero"],
        expected_keys["collision_false"],
        expected_keys["collision_empty"],
    ]
    assert csv_rows["collision-row-1"][expected_keys["collision_zero"]] == "0"
    assert csv_rows["collision-row-1"][expected_keys["collision_false"]].lower() == "false"
    assert csv_rows["collision-row-1"][expected_keys["collision_empty"]] == ""
    assert csv_rows["collision-row-2"][expected_keys["collision_false"]] == "false-column-sentinel"
    assert csv_rows["collision-row-2"][expected_keys["collision_empty"]] == "empty-column-sentinel"
    assert csv_rows["collision-row-3"][expected_keys["collision_false"]] == "0"
    assert csv_rows["collision-row-3"][expected_keys["collision_empty"]].lower() == "false"

    assert first["column_definitions"] == second["column_definitions"]
    assert first["integrated_rows"] == second["integrated_rows"]
    assert first["detail_rows"] == second["detail_rows"]
    assert first["payload_rows"] == second["payload_rows"]
    assert first["csv_text"] == second["csv_text"]


def test_ac019_direct_gpkg_failure_discloses_partial_fallback_without_hiding_success(
    render_html_report_fixture,
):
    fixture = {
        "source_columns": [
            {"id": "row_id", "source_table": "Loaded Observation", "source_field": "Row ID", "schema_order": 0},
            {"id": "species", "source_table": "Loaded Observation", "source_field": "Species", "schema_order": 1},
            {"id": "cover", "source_table": "Loaded Observation", "source_field": "Cover", "schema_order": 2},
        ],
        "direct_access": {
            "status": "failed",
            "path": "project.gpkg direct SQLite",
            "reason": "forced direct-access failure",
        },
        "fallback": {
            "source": "loaded_layers",
            "known_omissions": [
                {"kind": "table", "identifier": "registered_but_unloaded_table"},
                {"kind": "row", "identifier": "known-missing-row-77"},
            ],
            "unverifiable_scopes": [
                {"identifier": "unloaded table and row inventory", "count": None},
            ],
            "rows": [
                {
                    "source_row_id": "fallback-success-001",
                    "values": {
                        "row_id": "fallback-success-001",
                        "species": "fallback-success-species",
                        "cover": 17,
                    },
                    "geometry": {"format": "wkt", "value": "POINT (127.1 37.5)"},
                }
            ],
        },
        "actions": {
            "filter": {"source_column_id": "species", "equals": "fallback-success-species"},
            "sort": {"source_column_id": "cover", "direction": "descending"},
        },
    }
    result = _run(render_html_report_fixture, fixture)
    keys = _column_keys(result)

    assert result["fallback"]["used"] is True
    assert result["fallback"]["source"] == "loaded_layers"
    assert result["fallback"]["failed_direct_path"] == "project.gpkg direct SQLite"
    assert result["claims_complete_direct_inventory"] is False
    assert result["inventory_status"] in {"partial", "partial_unverified", "unverified"}

    known = {(item["kind"], item["identifier"]) for item in result["limitations"]["known_omissions"]}
    assert known == {
        ("table", "registered_but_unloaded_table"),
        ("row", "known-missing-row-77"),
    }
    unknown = result["limitations"]["unverifiable_scopes"]
    assert len(unknown) == 1
    assert unknown[0]["identifier"] == "unloaded table and row inventory"
    assert unknown[0]["count"] is None
    assert unknown[0]["completeness"] == "unknown"

    notice = result["limitation_notice_text"]
    for required in (
        "project.gpkg direct SQLite",
        "registered_but_unloaded_table",
        "known-missing-row-77",
        "unloaded table and row inventory",
    ):
        assert required in notice
    assert any(token in notice.lower() for token in ("fallback", "대체", "폴백"))
    assert any(token in notice.lower() for token in ("unknown", "unverified", "미확인", "확인 불가"))

    success_id = "fallback-success-001"
    for projection_name in ("integrated_rows", "detail_rows", "payload_rows"):
        assert success_id in _projection(result, projection_name)
    assert result["map_feature_ids"] == [success_id]
    assert result["filter_result_ids"] == [success_id]
    assert result["sort_result_ids"] == [success_id]
    assert result["summary"]["source_row_count"] == 1
    assert result["charts"]["species_occurrence"] == {"fallback-success-species": 1}
    _, csv_rows = _csv_rows(result, keys["row_id"])
    assert csv_rows[success_id][keys["species"]] == "fallback-success-species"
    assert csv_rows[success_id][keys["cover"]] == "17"


def _malformed_geometry_fixture() -> dict[str, Any]:
    columns = [
        {"id": "row_id", "source_table": "Fixture Anchor", "source_field": "Row ID", "schema_order": 0},
        {"id": "attribute", "source_table": "Fixture Anchor", "source_field": "Attribute", "schema_order": 1},
        {"id": "joined", "source_table": "Fixture Child", "source_field": "Joined Value", "schema_order": 2},
        {"id": "species", "source_table": "Fixture Child", "source_field": "Species", "schema_order": 3},
    ]
    rows = []
    for row_id, attribute, joined, geometry in (
        ("valid-before", "attribute-before", "join-before", "POINT (127.0 37.0)"),
        ("malformed-middle", "attribute-malformed", "join-malformed", "POINT (not-a-number 37.5)"),
        ("valid-after", "attribute-after", "join-after", "POINT (128.0 38.0)"),
    ):
        rows.append(
            {
                "source_row_id": row_id,
                "values": {
                    "row_id": row_id,
                    "attribute": attribute,
                    "joined": joined,
                    "species": "same-species",
                },
                "established_fk_join_column_ids": ["joined", "species"],
                "geometry": {"format": "wkt", "value": geometry},
            }
        )
    return {"source_columns": columns, "source_rows": rows}


def test_ac020_one_malformed_geometry_preserves_its_row_join_and_aggregates_only_off_map(
    render_html_report_fixture,
):
    fixture = _malformed_geometry_fixture()
    first = _run(render_html_report_fixture, fixture)
    second = _run(render_html_report_fixture, copy.deepcopy(fixture))
    keys = _column_keys(first)
    all_ids = {"valid-before", "malformed-middle", "valid-after"}

    assert first["source_table_processing_succeeded"] is True
    for projection_name in ("integrated_rows", "detail_rows", "payload_rows"):
        rows = _projection(first, projection_name)
        assert set(rows) == all_ids
        assert rows["malformed-middle"][keys["attribute"]] == "attribute-malformed"
        assert rows["malformed-middle"][keys["joined"]] == "join-malformed"
        assert rows["malformed-middle"][keys["species"]] == "same-species"

    assert set(first["map_feature_ids"]) == {"valid-before", "valid-after"}
    assert first["normalized_geometry_by_row"]["malformed-middle"] is None
    invalid = first["invalid_geometries"]
    assert len(invalid) == 1
    assert invalid[0]["source_row_id"] == "malformed-middle"
    assert isinstance(invalid[0]["reason"], str) and invalid[0]["reason"].strip()
    assert first["geometry_limitations"]["invalid_count"] == 1
    assert first["summary"]["source_row_count"] == 3
    assert first["charts"]["species_occurrence"] == {"same-species": 3}

    _, csv_rows = _csv_rows(first, keys["row_id"])
    assert set(csv_rows) == all_ids
    assert csv_rows["malformed-middle"][keys["attribute"]] == "attribute-malformed"
    assert csv_rows["malformed-middle"][keys["joined"]] == "join-malformed"
    assert csv_rows["malformed-middle"][keys["species"]] == "same-species"
    assert first["invalid_geometries"] == second["invalid_geometries"]


def test_ac017_ac020_regression_zm_is_removed_before_xy_validity_and_never_substitutes_for_xy(
    render_html_report_fixture,
):
    z_sentinel = 987654321.125
    m_sentinel = 876543210.25
    fixture = {
        "source_columns": [
            {"id": "row_id", "source_table": "Dimensional", "source_field": "Row ID", "schema_order": 0},
            {"id": "attribute", "source_table": "Dimensional", "source_field": "Attribute", "schema_order": 1},
        ],
        "source_rows": [
            {
                "source_row_id": "valid-zm",
                "values": {"row_id": "valid-zm", "attribute": "valid-zm-attribute"},
                "geometry": {
                    "format": "wkt",
                    "value": f"POINT ZM (127.0 37.0 {z_sentinel} {m_sentinel})",
                },
            },
            {
                "source_row_id": "invalid-xy-valid-zm",
                "values": {"row_id": "invalid-xy-valid-zm", "attribute": "invalid-xy-attribute"},
                "geometry": {
                    "format": "wkt",
                    "value": f"POINT ZM (NaN 37.5 {z_sentinel} {m_sentinel})",
                },
            },
        ],
    }
    result = _run(render_html_report_fixture, fixture)
    keys = _column_keys(result)

    assert result["map_feature_ids"] == ["valid-zm"]
    assert result["normalized_geometry_by_row"]["valid-zm"] == {
        "type": "Point",
        "coordinates": [127.0, 37.0],
    }
    assert result["normalized_geometry_by_row"]["invalid-xy-valid-zm"] is None
    assert [item["source_row_id"] for item in result["invalid_geometries"]] == [
        "invalid-xy-valid-zm"
    ]

    for projection_name in ("integrated_rows", "detail_rows", "payload_rows"):
        rows = _projection(result, projection_name)
        assert set(rows) == {"valid-zm", "invalid-xy-valid-zm"}
        assert rows["invalid-xy-valid-zm"][keys["attribute"]] == "invalid-xy-attribute"
        assert str(z_sentinel) not in repr(rows)
        assert str(m_sentinel) not in repr(rows)
    assert str(z_sentinel) not in result["csv_text"]
    assert str(m_sentinel) not in result["csv_text"]
