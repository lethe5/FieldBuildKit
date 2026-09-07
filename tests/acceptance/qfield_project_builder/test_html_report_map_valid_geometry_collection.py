"""Acceptance coverage for spatial-anchor HTML report map collection (AC-MGC-001..011).

The acceptance harness can build a real project and inspect the generated report sidecar, but it
does not provide a browser or QField's QML engine.  The automated checks therefore verify the
observable generated-report contract: schema-defined map contexts, UUID/FK join paths, anchor
selection, geometry validation/CRS conversion, row authority, and local/offline boundaries.
They deliberately do not require a particular JavaScript library or private helper name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from qfield_builder import schemas

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

TYPE_NAMES = (
    "simple_inventory",
    "temporary_plots",
    "permanent_plots",
    "vegetation_mapping",
)


def _build(acceptance_api, tmp_path: Path, survey_type: str):
    config = make_base_config(
        survey_type,
        display_name=f"도형 수집 acceptance {survey_type}",
    )
    result = acceptance_api.build_project(config, str(tmp_path / f"map_collection_{survey_type}"))
    assert result["success"], result.get("error_message")
    return result


def _source(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    path = project_dir / f"{result['project_slug']}.qml"
    assert path.is_file(), f"expected generated report sidecar: {path}"
    return path.read_text(encoding="utf-8")


def _definition(source: str) -> dict:
    marker = "qpbReportDefinition:"
    start = source.find(marker)
    assert start >= 0, "generated report must embed its schema definition"
    object_start = source.find("{", start)
    definition, _end = json.JSONDecoder().raw_decode(source[object_start:])
    assert isinstance(definition, dict)
    return definition


def _function_body(source: str, *names: str) -> str:
    """Return a string-aware JavaScript function body from the accepted helper-name set."""
    for name in names:
        match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", source)
        if not match:
            continue
        opening = source.find("{", match.end())
        assert opening >= 0
        depth = 0
        quote = None
        escaped = False
        for index in range(opening, len(source)):
            char = source[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in "'\"`":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[opening : index + 1]
    return ""


def _map_builder(source: str) -> str:
    """Return the dedicated map-collection body, allowing equivalent private names."""
    body = _function_body(
        source,
        "qpbBuildMapFeatures",
        "qpbCollectMapFeatures",
        "qpbBuildSpatialFeatures",
        "qpbCollectSpatialFeatures",
        "qpbBuildMapContexts",
        "qpbCollectMapContexts",
    )
    assert body, (
        "the report must have a dedicated spatial map-collection step so anchor selection and "
        "joined attributes are testable independently from Leaflet rendering"
    )
    return body


def _assert_map_collection_is_used(source: str) -> None:
    body = _map_builder(source)
    assert re.search(r"mapFeatures|map_features|spatialFeatures|mapContexts|features", body)
    assert re.search(r"geometry|geojson|coordinates", body, re.IGNORECASE)
    assert re.search(r"valid|usable|serial", body, re.IGNORECASE)
    assert re.search(r"qpbBuildMapFeatures|qpbCollectMapFeatures|qpbBuildSpatialFeatures|"
                     r"qpbCollectSpatialFeatures|qpbBuildMapContexts|qpbCollectMapContexts", source)


def _table(definition: dict, name: str) -> dict:
    return next(table for table in definition["tables"] if table["name"] == name)


# AC-MGC-001 / AC-MGC-002 / AC-MGC-003 ---------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_NAMES)
def test_ac001_ac002_type_specific_spatial_contexts_and_deterministic_layer_order(
    acceptance_api, tmp_path, survey_type
):
    result = _build(acceptance_api, tmp_path, survey_type)
    source = _source(result)
    definition = _definition(source)
    schema = schemas.get_schema(survey_type)

    _assert_map_collection_is_used(source)
    map_body = _map_builder(source)
    assert "유효한 도형 없음" in source
    assert re.search(r"valid|usable", map_body, re.IGNORECASE)

    if survey_type == "simple_inventory":
        assert tuple(table["name"] for table in definition["tables"]) == (
            "inventory_observation",
        )
        assert re.search(r"inventory_observation", map_body)
        assert not re.search(r"site|plot|survey|community", map_body)
    elif survey_type == "temporary_plots":
        assert re.search(r"site[\s\S]{0,500}survey|survey[\s\S]{0,500}site", map_body)
        assert re.search(r"survey[\s\S]{0,700}(?:anchor|좌표|geometry|coordinate)", map_body,
                         re.IGNORECASE)
        assert re.search(r"site[\s\S]{0,700}(?:separate|별도|polygon|context|layer)", map_body,
                         re.IGNORECASE)
    elif survey_type == "permanent_plots":
        assert re.search(r"site[\s\S]{0,800}plot|plot[\s\S]{0,800}site", map_body)
        assert re.search(r"plot[\s\S]{0,800}(?:anchor|좌표|geometry|coordinate)", map_body,
                         re.IGNORECASE)
        assert re.search(r"site[\s\S]{0,800}(?:separate|별도|polygon|context|layer)", map_body,
                         re.IGNORECASE)
    else:
        assert re.search(r"community|vegetation", map_body, re.IGNORECASE)
        assert not re.search(r"observation|inventory_observation", map_body, re.IGNORECASE)
        assert not re.search(r"site[\s\S]{0,500}(?:map|feature|polygon)", map_body,
                             re.IGNORECASE)

    # The embedded definition remains schema-driven and must not invent geometry or tables.
    for table in definition["tables"]:
        assert table["name"] in schema
        expected = schema[table["name"]].geometry
        assert table["geometry_field"] == (expected.column if expected else None)


def test_ac003_valid_geometry_only_is_rendered_and_unusable_records_remain_report_data(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "permanent_plots"))
    body = _map_builder(source)
    assert re.search(r"geometry\.valid|valid\s*\)|valid\s*&&|isValid|usable", body)
    assert re.search(r"missing geometry|invalid geometry|malformed|untransform|unsupported", source,
                     re.IGNORECASE)
    assert re.search(r"serialRecords|tableData|records.*push|report data|표에 남", source,
                     re.IGNORECASE)
    assert re.search(r"geometry_limitations|qpbGeometryLimitations|limitation", source,
                     re.IGNORECASE)
    assert re.search(r"EPSG:4326|WGS84", source)


# AC-MGC-004 / AC-MGC-008 / AC-MGC-009 / AC-MGC-010 / AC-MGC-011 -------------------------------


def test_ac004_ac008_ac009_ac010_ac011_type2_site_survey_observation_join_is_survey_anchored(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "temporary_plots"))
    body = _map_builder(source)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert joined, "existing joined-row builder must remain the row-authoritative source"

    assert re.search(r"site", joined)
    assert re.search(r"survey", joined)
    assert re.search(r"observation", joined)
    assert re.search(r"site_id|survey_id|foreign_key|qpbParentRecord", joined)
    assert re.search(r"selected_korean_name|selected_scientific_name|selected_ktsn", joined)
    assert re.search(r"leafRecords|rows\.push", joined)

    assert re.search(r"site[\s\S]{0,900}(?:separate|별도|polygon|siteFeatures|site_feature)", body,
                     re.IGNORECASE)
    assert re.search(r"survey[\s\S]{0,900}(?:anchor|authoritative|좌표|geometry|coordinate)", body,
                     re.IGNORECASE)
    # Observation geometry may be serialized as data, but it cannot be the Type 2 anchor.
    assert re.search(r"observation[\s\S]{0,900}(?:never|not|금지|제외|child|자식)", body,
                     re.IGNORECASE)
    assert re.search(r"one|single|1\s*(?:feature|map)|anchor.*(?:group|aggregate)|집계|하나", body,
                     re.IGNORECASE)


def test_ac004_ac010_ac011_type3_site_plot_survey_observation_join_and_fallback(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "permanent_plots"))
    body = _map_builder(source)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert joined

    for token in ("site", "plot", "survey", "observation"):
        assert token in joined
    assert re.search(r"site_id|plot_id|survey_id|foreign_key|qpbParentRecord", joined)
    assert re.search(r"selected_korean_name|selected_scientific_name|selected_ktsn", joined)

    assert re.search(r"site[\s\S]{0,1000}(?:separate|별도|polygon|siteFeatures|site_feature)", body,
                     re.IGNORECASE)
    assert re.search(r"plot[\s\S]{0,1000}(?:anchor|authoritative|좌표|geometry|coordinate)", body,
                     re.IGNORECASE)
    assert re.search(r"survey[\s\S]{0,1000}(?:fallback|대체|fallbackGeometry|좌표|geometry)", body,
                     re.IGNORECASE)
    assert re.search(r"plot[\s\S]{0,1000}geometry[\s\S]{0,1000}survey[\s\S]{0,1000}fallback|"
                     r"survey[\s\S]{0,1000}fallback[\s\S]{0,1000}plot", body,
                     re.IGNORECASE)
    assert re.search(r"observation[\s\S]{0,1000}(?:never|not|금지|제외|child|자식)", body,
                     re.IGNORECASE)


def test_ac004_one_to_many_is_row_authoritative_and_map_aggregation_is_deterministic(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "temporary_plots"))
    body = _map_builder(source)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert re.search(r"leafRecords|for\s*\([^)]*leaf|source.*order|iteration|결정", joined,
                     re.IGNORECASE)
    assert re.search(r"rows\.push|joinedRows|one row|행", joined, re.IGNORECASE)
    assert re.search(r"Map|index|group|aggregate|collection|related|children|자식|집계", body,
                     re.IGNORECASE)
    assert re.search(r"anchor[\s_-]*(?:id|uuid)|source.*uuid|stable.*uuid|qpbIndex", body,
                     re.IGNORECASE)
    assert re.search(r"child.*(?:order|sort)|source.*(?:order|iteration)|결정적|stable", body,
                     re.IGNORECASE)


# AC-MGC-005 / AC-MGC-006 / AC-MGC-007 / AC-MGC-008 -------------------------------------------


def test_ac005_crs_conversion_preserves_geometry_type_and_rejects_bad_coordinates(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "simple_inventory"))
    geometry = _function_body(source, "qpbGeometryToGeoJson")
    assert geometry
    assert re.search(r"EPSG:4326|WGS84", geometry)
    assert re.search(r"QgsCoordinateTransform|transform", geometry)
    assert re.search(r"clone|asJson|geojson", geometry, re.IGNORECASE)
    assert re.search(r"null|empty|malformed|JSON\.parse|unsupported|non.?finite|invalid", geometry,
                     re.IGNORECASE)


def test_ac006_type4_community_only_does_not_fabricate_observation_rows_or_identity(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "vegetation_mapping"))
    body = _map_builder(source)
    definition = _definition(source)
    assert {table["name"] for table in definition["tables"]} == {"site", "survey", "community"}
    assert re.search(r"community|vegetation", body, re.IGNORECASE)
    assert not re.search(r"observation|inventory_observation|selected_korean_name|"
                         r"selected_scientific_name|selected_ktsn", body, re.IGNORECASE)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert "community" in joined
    assert not re.search(r"observation|inventory_observation", joined, re.IGNORECASE)


def test_ac007_ac008_local_offline_report_keeps_identity_filter_sort_csv_and_privacy_boundaries(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "temporary_plots"))
    for token in (
        "selected_korean_name",
        "selected_scientific_name",
        "selected_ktsn",
        "renderJoined",
        "renderMap",
        "saveCsv",
        "filter",
        "sort",
        "allRows",
        "CSV",
    ):
        assert token in source, f"local report contract lost {token!r}"
    assert re.search(r"qpbEscapeHtml|escapeHtml|textContent|createTextNode", source)
    assert re.search(r"qpbCsvCell|charset=utf-8|UTF-8|text/csv", source, re.IGNORECASE)
    assert re.search(r"qpbSafeJson|JSON\.stringify", source)
    assert not re.search(r"(?:api[_-]?key|credential|password|secret|attachment[_-]?path).*"
                         r"(?:map properties|visible|CSV|diagnostic|log)", source, re.IGNORECASE)
    assert "OpenStreetMap" in source
    assert re.search(r"offline|오프라인", source, re.IGNORECASE)


def test_ac008_map_details_keep_anchor_uuid_and_joined_site_context_without_fabrication(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "permanent_plots"))
    body = _map_builder(source)
    assert re.search(r"uuid|stable.*id|domain_uuid", body, re.IGNORECASE)
    assert re.search(r"detail|popup|context|site|plot|survey", body, re.IGNORECASE)
    assert re.search(r"foreign.?key|UUID|qpbIndex|qpbParentRecord", source, re.IGNORECASE)
    assert not re.search(r"centroid|photo.*location|EXIF|GPS|device.*location", body, re.IGNORECASE)


# Acceptance boundary --------------------------------------------------------------------------


def test_ac009_ac010_no_observation_geometry_promotion_and_no_valid_state_is_explicit(
    acceptance_api, tmp_path
):
    source = _source(_build(acceptance_api, tmp_path, "temporary_plots"))
    body = _map_builder(source)
    assert re.search(r"missing|invalid|unusable|오류|누락", body, re.IGNORECASE)
    assert re.search(r"observation[\s\S]{0,1000}(?:not|never|child|자식|제외|금지)", body,
                     re.IGNORECASE)
    assert re.search(r"유효한 도형 없음", source)
    assert re.search(r"count|length|validFeatures|mapFeatures", source, re.IGNORECASE)

