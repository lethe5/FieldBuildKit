"""Acceptance coverage for AC-IHRM-001..013.

This module drives the production integrated-report path through the narrow
``render_html_report_integrated_fixture`` seam documented in
``HARNESS_CONTRACT.md``.  All fixtures are in-memory and repository-local; the
tests never construct QGIS, open a browser, access the attached Downloads
fixtures, or use a network service.
"""

from __future__ import annotations

import copy
import csv
import io
from typing import Any

import pytest


@pytest.fixture()
def render_integrated_report_fixture(acceptance_api):
    renderer = getattr(acceptance_api, "render_html_report_integrated_fixture", None)
    if renderer is None:
        pytest.skip(
            "qfield_builder.acceptance_api.render_html_report_integrated_fixture() is not "
            "implemented yet — see tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md"
        )
    return renderer


def _run(renderer, fixture: dict[str, Any]) -> dict[str, Any]:
    original = copy.deepcopy(fixture)
    result = renderer(fixture)
    assert fixture == original, "report rendering must not mutate source schema, rows, or values"
    assert result["success"] is True, result.get("error_message")
    return result


def _keys(result: dict[str, Any]) -> dict[str, str]:
    mapping = result["source_to_final_key"]
    assert mapping
    return mapping


def _rows(result: dict[str, Any], projection: str) -> dict[str, dict[str, Any]]:
    rows = result[projection]
    assert len({row["source_row_id"] for row in rows}) == len(rows)
    return {row["source_row_id"]: row["values"] for row in rows}


def _csv_rows(result: dict[str, Any], row_id_key: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(result["csv_text"]))
    assert reader.fieldnames is not None
    return reader.fieldnames, {row[row_id_key]: row for row in reader}


def _semantic_columns() -> list[dict[str, Any]]:
    return [
        {
            "id": "inventory_uuid",
            "source_table": "inventory_observation",
            "source_field": "inventory_observation_id",
            "schema_order": 0,
        },
        {
            "id": "korean_name",
            "source_table": "joined",
            "source_field": "selected_korean_name",
            "semantic_identity": "selected_korean_name",
            "schema_order": 1,
        },
        {
            "id": "inventory_korean_name",
            "source_table": "inventory_observation",
            "source_field": "selected_korean_name",
            "semantic_identity": "selected_korean_name",
            "schema_order": 2,
        },
        {
            "id": "scientific_name",
            "source_table": "joined",
            "source_field": "selected_scientific_name",
            "semantic_identity": "selected_scientific_name",
            "schema_order": 3,
        },
        {
            "id": "inventory_scientific_name",
            "source_table": "inventory_observation",
            "source_field": "selected_scientific_name",
            "semantic_identity": "selected_scientific_name",
            "schema_order": 4,
        },
        {
            "id": "ktsn",
            "source_table": "joined",
            "source_field": "selected_ktsn",
            "semantic_identity": "selected_ktsn",
            "schema_order": 5,
        },
        {
            "id": "inventory_ktsn",
            "source_table": "inventory_observation",
            "source_field": "selected_ktsn",
            "semantic_identity": "selected_ktsn",
            "schema_order": 6,
        },
    ]


def _five_equal_semantic_rows() -> list[dict[str, Any]]:
    rows = []
    for number in range(1, 6):
        uuid = f"inventory-{number:03d}"
        values = {
            "inventory_uuid": uuid,
            "korean_name": f"국명 {number}",
            "inventory_korean_name": f"국명 {number}",
            "scientific_name": f"Species {number}",
            "inventory_scientific_name": f"Species {number}",
            "ktsn": f"KTSN-{number:03d}",
            "inventory_ktsn": f"KTSN-{number:03d}",
        }
        rows.append({"source_row_id": uuid, "values": values})
    return rows


def test_ac001_same_semantic_identity_columns_collapse_without_changing_five_source_records(
    render_integrated_report_fixture,
):
    fixture = {
        "survey_type": "simple_inventory",
        "source_columns": _semantic_columns(),
        "source_rows": _five_equal_semantic_rows(),
    }
    result = _run(render_integrated_report_fixture, fixture)
    keys = _keys(result)

    for left, right in (
        ("korean_name", "inventory_korean_name"),
        ("scientific_name", "inventory_scientific_name"),
        ("ktsn", "inventory_ktsn"),
    ):
        assert keys[left] == keys[right]
        definitions = [
            definition
            for definition in result["column_definitions"]
            if set(definition["source_column_ids"]) == {left, right}
        ]
        assert len(definitions) == 1

    for projection in ("integrated_rows", "detail_rows", "payload_rows"):
        rows = _rows(result, projection)
        assert set(rows) == {f"inventory-{number:03d}" for number in range(1, 6)}
        for number in range(1, 6):
            values = rows[f"inventory-{number:03d}"]
            assert values[keys["korean_name"]] == f"국명 {number}"
            assert values[keys["scientific_name"]] == f"Species {number}"
            assert values[keys["ktsn"]] == f"KTSN-{number:03d}"

    header, exported = _csv_rows(result, keys["inventory_uuid"])
    assert header.count(keys["korean_name"]) == 1
    assert header.count(keys["scientific_name"]) == 1
    assert header.count(keys["ktsn"]) == 1
    assert exported["inventory-005"][keys["korean_name"]] == "국명 5"
    assert exported["inventory-005"][keys["scientific_name"]] == "Species 5"
    assert exported["inventory-005"][keys["ktsn"]] == "KTSN-005"


def test_ac002_falsey_missing_and_present_null_values_keep_stable_canonical_provenance(
    render_integrated_report_fixture,
):
    columns = [
        {"id": "row_id", "source_table": "source", "source_field": "row_id", "schema_order": 0},
        {
            "id": "left",
            "source_table": "source_a",
            "source_field": "value",
            "semantic_identity": "value",
            "schema_order": 1,
        },
        {
            "id": "right",
            "source_table": "source_b",
            "source_field": "value",
            "semantic_identity": "value",
            "schema_order": 2,
        },
    ]
    fixture = {
        "source_columns": columns,
        "source_rows": [
            {"source_row_id": "zero", "values": {"row_id": "zero", "left": 0, "right": 0}},
            {"source_row_id": "false", "values": {"row_id": "false", "left": False, "right": False}},
            {"source_row_id": "empty", "values": {"row_id": "empty", "left": "", "right": ""}},
            {"source_row_id": "null", "values": {"row_id": "null", "left": None, "right": None}},
            {"source_row_id": "missing", "values": {"row_id": "missing", "left": 0}},
        ],
    }
    first = _run(render_integrated_report_fixture, fixture)
    second = _run(render_integrated_report_fixture, copy.deepcopy(fixture))
    keys = _keys(first)
    assert keys["left"] == keys["right"]
    canonical_key = keys["left"]

    rows = _rows(first, "payload_rows")
    assert rows["zero"][canonical_key] == 0
    assert rows["false"][canonical_key] is False
    assert rows["empty"][canonical_key] == ""
    assert rows["null"][canonical_key] is None
    assert rows["missing"][canonical_key] == 0
    assert first["source_value_presence"]["missing"]["left"] is True
    assert first["source_value_presence"]["missing"]["right"] is False
    assert "left" in first["source_to_canonical_provenance"]
    assert "right" in first["source_to_canonical_provenance"]
    assert first["source_to_final_key"] == second["source_to_final_key"]
    assert first["source_to_canonical_provenance"] == second["source_to_canonical_provenance"]


def test_ac003_differing_semantic_values_are_source_specific_disclosed_and_repeatable(
    render_integrated_report_fixture,
):
    fixture = {
        "source_columns": [
            {"id": "row_id", "source_table": "source", "source_field": "id", "schema_order": 0},
            {
                "id": "left",
                "source_table": "observation",
                "source_field": "selected_korean_name",
                "semantic_identity": "selected_korean_name",
                "schema_order": 1,
            },
            {
                "id": "right",
                "source_table": "inventory_observation",
                "source_field": "selected_korean_name",
                "semantic_identity": "selected_korean_name",
                "schema_order": 2,
            },
        ],
        "source_rows": [
            {"source_row_id": "different", "values": {"row_id": "different", "left": "가", "right": "나"}},
            {"source_row_id": "null-versus-value", "values": {"row_id": "null-versus-value", "left": None, "right": "다"}},
        ],
    }
    first = _run(render_integrated_report_fixture, fixture)
    second = _run(render_integrated_report_fixture, copy.deepcopy(fixture))
    keys = _keys(first)
    assert keys["left"] != keys["right"]
    assert len(set(keys.values())) == len(keys)
    assert first["semantic_collision_notices"]
    assert all("selected_korean_name" in notice["semantic_identity"] for notice in first["semantic_collision_notices"])
    values = _rows(first, "integrated_rows")
    assert values["different"][keys["left"]] == "가"
    assert values["different"][keys["right"]] == "나"
    assert values["null-versus-value"][keys["left"]] is None
    assert values["null-versus-value"][keys["right"]] == "다"
    assert first["source_to_final_key"] == second["source_to_final_key"]
    assert first["column_definitions"] == second["column_definitions"]
    assert first["csv_text"] == second["csv_text"]


def test_ac004_one_column_definition_drives_collision_filter_sort_detail_and_csv(
    render_integrated_report_fixture,
):
    fixture = {
        "source_columns": [
            {"id": "row_id", "source_table": "fixture", "source_field": "row_id", "schema_order": 0},
            {"id": "first", "source_table": "Specimen Table", "source_field": "Quality-Flag", "schema_order": 1},
            {"id": "second", "source_table": "Specimen_Table", "source_field": "Quality Flag", "schema_order": 2},
        ],
        "source_rows": [
            {"source_row_id": "one", "values": {"row_id": "one", "first": 2, "second": 20}},
            {"source_row_id": "two", "values": {"row_id": "two", "first": 1, "second": 10}},
        ],
        "actions": {
            "filter": {"source_column_id": "second", "equals": 10},
            "sort": {"source_column_id": "first", "direction": "ascending"},
        },
    }
    first = _run(render_integrated_report_fixture, fixture)
    second = _run(render_integrated_report_fixture, copy.deepcopy(fixture))
    keys = _keys(first)
    assert keys["first"] != keys["second"]
    assert keys["first"].startswith("specimen_table__quality_flag")
    assert keys["second"].startswith("specimen_table__quality_flag")
    assert first["filter_result_ids"] == ["two"]
    assert first["sort_result_ids"] == ["two", "one"]
    for projection in ("integrated_rows", "detail_rows", "payload_rows"):
        rows = _rows(first, projection)
        assert rows["one"][keys["first"]] == 2
        assert rows["one"][keys["second"]] == 20
        assert rows["two"][keys["first"]] == 1
        assert rows["two"][keys["second"]] == 10
    header, exported = _csv_rows(first, keys["row_id"])
    assert len(header) == len(set(header))
    assert exported["two"][keys["first"]] == "1"
    assert exported["two"][keys["second"]] == "10"
    assert first["column_definitions"] == second["column_definitions"]
    assert first["csv_text"] == second["csv_text"]


def _point_fixture(*, malformed_middle: bool = False) -> dict[str, Any]:
    rows = []
    for number in range(1, 6):
        row_id = f"inventory-{number:03d}"
        geometry = f"POINT ({126 + number / 10} {37 + number / 10})"
        if malformed_middle and number == 3:
            geometry = "POINT (not-a-number 37.3)"
        rows.append(
            {
                "source_row_id": row_id,
                "stable_source_id": row_id,
                "values": {"inventory_uuid": row_id, "joined_attribute": f"joined-{number}"},
                "geometry": {"format": "wkt", "value": geometry},
            }
        )
    return {
        "survey_type": "simple_inventory",
        "source_columns": [
            {"id": "inventory_uuid", "source_table": "inventory_observation", "source_field": "inventory_observation_id", "schema_order": 0},
            {"id": "joined_attribute", "source_table": "survey_join", "source_field": "joined_attribute", "schema_order": 1},
        ],
        "source_rows": rows,
        "spatial_metadata": [
            {
                "table": "inventory_observation",
                "geometry_column": "geom",
                "geometry_type": "POINT",
                "source_crs": "EPSG:4326",
                "record_ids": [row["source_row_id"] for row in rows],
            }
        ],
        "qgis_spatial_layers": [
            {"table": "inventory_observation", "geometry_column": "geom", "crs": "EPSG:4326"}
        ],
        "coordinate_transform_available": False,
    }


def test_ac005_ac006_five_epsg4326_points_stay_map_eligible_with_stable_joined_details(
    render_integrated_report_fixture,
):
    result = _run(render_integrated_report_fixture, _point_fixture())
    assert result["spatial_metadata"] == [
        {
            "table": "inventory_observation",
            "geometry_column": "geom",
            "geometry_type": "POINT",
            "source_crs": "EPSG:4326",
            "non_null_geometry_count": 5,
        }
    ]
    assert result["map_empty_notice_present"] is False
    assert [feature["source_row_id"] for feature in result["map_features"]] == [
        f"inventory-{number:03d}" for number in range(1, 6)
    ]
    for number, feature in enumerate(result["map_features"], start=1):
        assert feature["stable_source_id"] == f"inventory-{number:03d}"
        assert feature["geometry"] == {
            "type": "Point",
            "coordinates": [126 + number / 10, 37 + number / 10],
        }
        assert feature["joined_attributes"]["joined_attribute"] == f"joined-{number}"
    assert not result["invalid_geometries"]


def test_ac007_one_malformed_geometry_keeps_row_off_map_with_a_stable_visible_limitation(
    render_integrated_report_fixture,
):
    result = _run(render_integrated_report_fixture, _point_fixture(malformed_middle=True))
    keys = _keys(result)
    assert [feature["source_row_id"] for feature in result["map_features"]] == [
        "inventory-001", "inventory-002", "inventory-004", "inventory-005"
    ]
    invalid = result["invalid_geometries"]
    assert len(invalid) == 1
    assert invalid[0]["source_row_id"] == "inventory-003"
    assert invalid[0]["reason"].strip()
    assert invalid[0]["reason"] in result["limitation_notice_text"]
    for projection in ("integrated_rows", "detail_rows", "payload_rows"):
        row = _rows(result, projection)["inventory-003"]
        assert row[keys["inventory_uuid"]] == "inventory-003"
        assert row[keys["joined_attribute"]] == "joined-3"
    _, exported = _csv_rows(result, keys["inventory_uuid"])
    assert exported["inventory-003"][keys["joined_attribute"]] == "joined-3"
    assert result["summary"]["source_row_count"] == 5


def _card_fixture(survey_type: str) -> dict[str, Any]:
    direct_sources: dict[str, dict[str, Any]] = {
        "site": {"schema_present": True, "records": [{"id": "site-1"}, {"id": "site-2"}]},
        "plot": {"schema_present": True, "records": [{"id": "plot-1"}, {"id": "plot-2"}, {"id": "plot-3"}]},
        "survey": {
            "schema_present": True,
            "records": [
                {"id": "survey-1", "survey_date": "2026-01-01T12:00:00"},
                {"id": "survey-2", "survey_date": "2026-01-01"},
                {"id": "survey-3", "survey_date": "not-a-date"},
                {"id": "survey-4", "survey_date": None},
            ],
        },
        "observation": {
            "schema_present": True,
            "records": [
                {"id": "obs-1", "selected_ktsn": "K-1"},
                {"id": "obs-2", "selected_ktsn": "K-1"},
                {"id": "obs-3", "selected_ktsn": "K-2"},
                {"id": "obs-4", "selected_ktsn": None},
                {"id": "obs-5", "selected_ktsn": ""},
                {"id": "obs-6", "selected_ktsn": "  "},
            ],
        },
        "inventory_observation": {
            "schema_present": True,
            "records": [
                {"id": "inventory-1", "observed_at": "2026-02-01T08:00:00", "selected_ktsn": "I-1"},
                {"id": "inventory-2", "observed_at": "2026-02-01", "selected_ktsn": "I-1"},
                {"id": "inventory-3", "observed_at": "invalid", "selected_ktsn": "I-2"},
                {"id": "inventory-4", "observed_at": None, "selected_ktsn": None},
                {"id": "inventory-5", "observed_at": "", "selected_ktsn": " "},
            ],
        },
        "community": {
            "schema_present": True,
            "records": [
                {"id": "community-1", "community_name": "군락 A"},
                {"id": "community-2", "community_name": "군락 A"},
                {"id": "community-3", "community_name": "군락 B"},
                {"id": "community-4", "community_name": None},
            ],
        },
    }
    return {
        "survey_type": survey_type,
        "source_columns": [{"id": "row_id", "source_table": "joined", "source_field": "row_id", "schema_order": 0}],
        # Fan-out deliberately repeats direct source records.  Cards must ignore it.
        "source_rows": [
            {"source_row_id": f"joined-{number}", "values": {"row_id": f"joined-{number}"}, "direct_source_ids": ["obs-1", "inventory-1"]}
            for number in range(1, 5)
        ],
        "direct_sources": direct_sources,
    }


def _cards_by_label(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["label"]: card for card in result["overview_cards"]}


def _ktsn_count_separation_fixture(survey_type: str) -> dict[str, Any]:
    """Make the overview-card KTSN measure observably different from species groups.

    The two KTSN-only source records contribute two valid direct-layer KTSNs, but their
    deliberately repeated joined projections must neither become species/chart groups nor
    inflate the overview card.  The all-fields-empty source record is the only record allowed
    into the ``미동정`` bucket.
    """
    fixture = _card_fixture(survey_type)
    source_layer = "inventory_observation" if survey_type == "simple_inventory" else "observation"
    fixture["direct_sources"][source_layer]["records"] = [
        {
            "id": "source-keyed",
            "selected_korean_name": "기준 식물",
            "selected_scientific_name": "Reference plant",
            "selected_ktsn": "K-KEYED",
        },
        {
            "id": "source-ktsn-only-a",
            "selected_korean_name": "",
            "selected_scientific_name": "",
            "selected_ktsn": "K-ONLY-A",
        },
        {
            "id": "source-ktsn-only-b",
            "selected_korean_name": None,
            "selected_scientific_name": None,
            "selected_ktsn": "K-ONLY-B",
        },
        {
            "id": "source-ktsn-only-a-duplicate",
            "selected_korean_name": " ",
            "selected_scientific_name": " ",
            "selected_ktsn": "K-ONLY-A",
        },
        {
            "id": "source-unidentified",
            "selected_korean_name": "",
            "selected_scientific_name": "",
            "selected_ktsn": None,
        },
    ]
    fixture["source_columns"] = [
        {"id": "row_id", "source_table": "joined", "source_field": "row_id", "schema_order": 0},
        {
            "id": "selected_korean_name",
            "source_table": source_layer,
            "source_field": "selected_korean_name",
            "schema_order": 1,
        },
        {
            "id": "selected_scientific_name",
            "source_table": source_layer,
            "source_field": "selected_scientific_name",
            "schema_order": 2,
        },
        {
            "id": "selected_ktsn",
            "source_table": source_layer,
            "source_field": "selected_ktsn",
            "schema_order": 3,
        },
    ]

    def joined_row(row_id: str, source_id: str, korean: Any, scientific: Any, ktsn: Any) -> dict[str, Any]:
        return {
            "source_row_id": row_id,
            "direct_source_ids": [source_id],
            "values": {
                "row_id": row_id,
                "selected_korean_name": korean,
                "selected_scientific_name": scientific,
                "selected_ktsn": ktsn,
            },
        }

    fixture["source_rows"] = [
        joined_row("joined-keyed", "source-keyed", "기준 식물", "Reference plant", "K-KEYED"),
        joined_row("joined-ktsn-only-a-1", "source-ktsn-only-a", "", "", "K-ONLY-A"),
        joined_row("joined-ktsn-only-a-2", "source-ktsn-only-a", "", "", "K-ONLY-A"),
        joined_row("joined-ktsn-only-b", "source-ktsn-only-b", None, None, "K-ONLY-B"),
        joined_row("joined-unidentified", "source-unidentified", "", "", None),
    ]
    return fixture


@pytest.mark.parametrize(
    ("survey_type", "expected_labels"),
    [
        ("simple_inventory", ["총 조사일 수", "관찰 수", "총 종수"]),
        ("temporary_plots", ["조사지 수", "조사구 수", "총 조사일 수", "관찰 수", "총 종수"]),
        ("permanent_plots", ["조사지 수", "조사구 수", "총 조사일 수", "관찰 수", "총 종수"]),
        ("vegetation_mapping", ["조사지 수", "고유군락 수", "총군락 수", "총 조사일 수"]),
    ],
)
def test_ac008_cards_have_exact_type_specific_labels_number_and_order(
    render_integrated_report_fixture, survey_type, expected_labels
):
    result = _run(render_integrated_report_fixture, _card_fixture(survey_type))
    cards = result["overview_cards"]
    assert [card["label"] for card in cards] == expected_labels
    assert len(cards) == len(expected_labels)
    if survey_type == "vegetation_mapping":
        assert "총 종수" not in [card["label"] for card in cards]
        assert "관찰 수" not in [card["label"] for card in cards]
        unique_community = _cards_by_label(result)["고유군락 수"]
        assert unique_community["direct_source_layer"] == "community"
        assert unique_community["source_field"] == "community_name"
        assert unique_community["value"] == 2


@pytest.mark.parametrize(
    ("survey_type", "expected_values", "expected_sources"),
    [
        (
            "simple_inventory",
            {"총 조사일 수": 1, "관찰 수": 5, "총 종수": 2},
            {"총 조사일 수": "inventory_observation", "관찰 수": "inventory_observation", "총 종수": "inventory_observation"},
        ),
        (
            "temporary_plots",
            {"조사지 수": 2, "조사구 수": 4, "총 조사일 수": 1, "관찰 수": 6, "총 종수": 2},
            {"조사지 수": "site", "조사구 수": "survey", "총 조사일 수": "survey", "관찰 수": "observation", "총 종수": "observation"},
        ),
        (
            "permanent_plots",
            {"조사지 수": 2, "조사구 수": 3, "총 조사일 수": 1, "관찰 수": 6, "총 종수": 2},
            {"조사지 수": "site", "조사구 수": "plot", "총 조사일 수": "survey", "관찰 수": "observation", "총 종수": "observation"},
        ),
        (
            "vegetation_mapping",
            {"조사지 수": 2, "고유군락 수": 2, "총군락 수": 4, "총 조사일 수": 1},
            {"조사지 수": "site", "고유군락 수": "community", "총군락 수": "community", "총 조사일 수": "survey"},
        ),
    ],
)
def test_ac009_direct_layer_cards_ignore_join_fanout_and_disclose_invalid_inputs(
    render_integrated_report_fixture, survey_type, expected_values, expected_sources
):
    result = _run(render_integrated_report_fixture, _card_fixture(survey_type))
    cards = _cards_by_label(result)
    assert {label: cards[label]["value"] for label in expected_values} == expected_values
    assert {label: cards[label]["direct_source_layer"] for label in expected_sources} == expected_sources
    for card in cards.values():
        assert card["basis"]
    limitations = result["limitations"]
    expected_invalid_dates = 3 if survey_type == "simple_inventory" else 2
    assert any(item["kind"] == "invalid_or_missing_date" and item["count"] == expected_invalid_dates for item in limitations)
    if survey_type != "vegetation_mapping":
        expected_invalid_ktsn = 2 if survey_type == "simple_inventory" else 3
        assert any(item["kind"] == "invalid_ktsn" and item["count"] == expected_invalid_ktsn for item in limitations)

    empty_layers = _card_fixture(survey_type)
    for source in empty_layers["direct_sources"].values():
        source["records"] = []
    empty_result = _run(render_integrated_report_fixture, empty_layers)
    assert all(isinstance(card["value"], int) and card["value"] == 0 for card in empty_result["overview_cards"])

    absent_layers = _card_fixture(survey_type)
    required = "inventory_observation" if survey_type == "simple_inventory" else (
        "observation" if survey_type in {"temporary_plots", "permanent_plots"} else "community"
    )
    absent_layers["direct_sources"][required]["schema_present"] = False
    absent_result = _run(render_integrated_report_fixture, absent_layers)
    absent_cards = _cards_by_label(absent_result)
    if survey_type == "vegetation_mapping":
        assert absent_cards["고유군락 수"]["value"] == "해당 레벨 부재"
        assert absent_cards["총군락 수"]["value"] == "해당 레벨 부재"
    else:
        assert absent_cards["관찰 수"]["value"] == "해당 레벨 부재"
        assert absent_cards["총 종수"]["value"] == "해당 레벨 부재"


def test_ac010_integrated_table_is_present_for_populated_and_empty_sources_with_one_row_authority(
    render_integrated_report_fixture,
):
    populated_fixture = _point_fixture()
    populated_fixture["actions"] = {
        "filter": {"source_column_id": "joined_attribute", "equals": "joined-2"},
        "sort": {"source_column_id": "inventory_uuid", "direction": "descending"},
    }
    populated = _run(render_integrated_report_fixture, populated_fixture)
    assert populated["integrated_table"]["present"] is True
    assert populated["integrated_table"]["state"] == "populated"
    assert populated["integrated_table"]["header_keys"] == [definition["key"] for definition in populated["column_definitions"]]
    assert populated["filter_result_ids"] == ["inventory-002"]
    assert populated["sort_result_ids"] == [
        "inventory-005", "inventory-004", "inventory-003", "inventory-002", "inventory-001"
    ]

    empty_fixture = _point_fixture()
    empty_fixture["source_rows"] = []
    empty_fixture["spatial_metadata"][0]["record_ids"] = []
    empty = _run(render_integrated_report_fixture, empty_fixture)
    assert empty["integrated_table"]["present"] is True
    assert empty["integrated_table"]["state"] == "empty_data"
    assert empty["integrated_table"]["header_keys"] == [definition["key"] for definition in empty["column_definitions"]]
    assert empty["integrated_rows"] == empty["detail_rows"] == empty["payload_rows"] == []
    header, exported = _csv_rows(empty, _keys(empty)["inventory_uuid"])
    assert header == empty["integrated_table"]["header_keys"]
    assert exported == {}


def test_ac011_partial_fallback_discloses_scope_and_keeps_successful_rows_usable_in_cards(
    render_integrated_report_fixture,
):
    fixture = _point_fixture()
    successful_row = fixture["source_rows"][0]
    fixture["source_rows"] = []
    fixture["spatial_metadata"][0]["record_ids"] = ["inventory-001"]
    fixture["direct_sources"] = {
        "inventory_observation": {
            "schema_present": True,
            "records": [
                {
                    "id": "inventory-001",
                    "observed_at": "2026-03-01",
                    "selected_ktsn": "FALLBACK-KTSN",
                }
            ],
        }
    }
    fixture["direct_access"] = {
        "status": "failed",
        "path": "project.gpkg direct SQLite",
        "reason": "forced direct-access failure",
    }
    fixture["fallback"] = {
        "source": "loaded_layers",
        "rows": [successful_row],
        "known_omissions": [{"kind": "table", "identifier": "unloaded_site"}],
        "unverifiable_scopes": [{"identifier": "full GPKG row inventory", "count": None}],
    }
    fixture["actions"] = {
        "filter": {"source_column_id": "joined_attribute", "equals": "joined-1"},
        "sort": {"source_column_id": "inventory_uuid", "direction": "ascending"},
    }
    result = _run(render_integrated_report_fixture, fixture)
    keys = _keys(result)
    assert result["fallback"]["used"] is True
    assert result["fallback"]["source"] == "loaded_layers"
    assert result["fallback"]["failed_direct_path"] == "project.gpkg direct SQLite"
    assert result["fallback"]["successful_reads"] == [
        {"table": "inventory_observation", "row_count": 1}
    ]
    assert result["claims_complete_direct_inventory"] is False
    assert result["inventory_status"] in {"partial", "partial_unverified", "unverified"}
    notice = result["limitation_notice_text"]
    for required in ("project.gpkg direct SQLite", "loaded_layers", "unloaded_site", "full GPKG row inventory"):
        assert required in notice
    for projection in ("integrated_rows", "detail_rows", "payload_rows"):
        assert _rows(result, projection)["inventory-001"][keys["joined_attribute"]] == "joined-1"
    assert [feature["source_row_id"] for feature in result["map_features"]] == ["inventory-001"]
    assert result["filter_result_ids"] == ["inventory-001"]
    assert result["sort_result_ids"] == ["inventory-001"]
    _, exported = _csv_rows(result, keys["inventory_uuid"])
    assert exported["inventory-001"][keys["joined_attribute"]] == "joined-1"
    cards = _cards_by_label(result)
    assert cards["관찰 수"]["value"] == 1
    assert cards["총 종수"]["value"] == 1


def test_ac012_theme_click_keyboard_storage_and_no_storage_preserve_report_state(
    render_integrated_report_fixture,
):
    fixture = _point_fixture()
    fixture["theme_interaction"] = {
        "initial_theme": "light",
        "storage_available": True,
        "actions": [
            {"kind": "click"},
            {"kind": "reopen"},
            {"kind": "keyboard", "key": "Enter"},
        ],
        "state": {
            "map_view": {"center": [127.1, 37.5], "zoom": 12},
            "filter_result_ids": ["inventory-002"],
            "sort_result_ids": ["inventory-002", "inventory-001"],
            "expanded_sections": ["site-1"],
            "selected_detail_id": "inventory-002",
            "chart_state": {"selected": "joined_attribute"},
            "csv_headers": ["inventory_uuid", "joined_attribute"],
            "source_rows": copy.deepcopy(fixture["source_rows"]),
        },
    }
    result = _run(render_integrated_report_fixture, fixture)
    states = result["theme_states"]
    assert [state["theme"] for state in states] == ["light", "dark", "dark", "light"]
    assert [state["document_element_theme"] for state in states] == ["light", "dark", "dark", "light"]
    assert [state["aria_pressed"] for state in states] == [False, True, True, False]
    assert states[0]["css_variables"] != states[1]["css_variables"]
    assert states[1]["css_variables"] == states[2]["css_variables"]
    assert all(state["report_state"] == states[0]["report_state"] for state in states[1:])
    assert result["saved_theme_preference"] == "light"

    no_storage = _point_fixture()
    no_storage["theme_interaction"] = {
        "initial_theme": "light",
        "storage_available": False,
        "actions": [{"kind": "keyboard", "key": "Space"}],
        "state": {"map_view": {"center": [127.1, 37.5], "zoom": 12}},
    }
    no_storage_result = _run(render_integrated_report_fixture, no_storage)
    assert [state["theme"] for state in no_storage_result["theme_states"]] == ["light", "dark"]
    assert no_storage_result["saved_theme_preference"] is None
    assert no_storage_result["theme_states"][1]["report_state"] == no_storage_result["theme_states"][0]["report_state"]


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots"])
def test_ac013_total_species_uses_only_direct_type_source_and_excludes_invalid_ktsn(
    render_integrated_report_fixture, survey_type
):
    result = _run(render_integrated_report_fixture, _card_fixture(survey_type))
    cards = _cards_by_label(result)
    source = "inventory_observation" if survey_type == "simple_inventory" else "observation"
    assert cards["총 종수"]["direct_source_layer"] == source
    assert cards["총 종수"]["source_field"] == "selected_ktsn"
    assert cards["총 종수"]["value"] == 2
    expected_invalid_ktsn = 2 if survey_type == "simple_inventory" else 3
    assert any(item["kind"] == "invalid_ktsn" and item["count"] == expected_invalid_ktsn for item in result["limitations"])


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots"])
def test_ac013_ktsn_only_values_count_in_direct_layer_card_but_not_species_charts_or_mijeong(
    render_integrated_report_fixture, survey_type
):
    """D-IHRM-008/D-HRA-004 keep direct KTSN cards separate from species keys."""
    result = _run(render_integrated_report_fixture, _ktsn_count_separation_fixture(survey_type))
    cards = _cards_by_label(result)
    source_layer = "inventory_observation" if survey_type == "simple_inventory" else "observation"

    total_species = cards["총 종수"]
    assert total_species["direct_source_layer"] == source_layer
    assert total_species["value"] == 3, (
        "the direct-layer distinct KTSN card must include K-KEYED, K-ONLY-A, and K-ONLY-B "
        "exactly once, despite duplicate direct values and joined-row fan-out"
    )
    assert total_species["source_field"] == "selected_ktsn"

    species_occurrence = result["charts"]["species_occurrence"]
    assert species_occurrence["기준 식물"] == 1
    assert species_occurrence["미동정"] == 1
    assert len(species_occurrence) == 2
    assert sum(species_occurrence.values()) == 2
    assert not any("K-ONLY" in species_key for species_key in species_occurrence), (
        "KTSN-only records must not form occurrence/chart groups"
    )
    assert species_occurrence["미동정"] == 1, (
        "the repeated KTSN-only rows must not be folded into the sole all-fields-empty 미동정 row"
    )
