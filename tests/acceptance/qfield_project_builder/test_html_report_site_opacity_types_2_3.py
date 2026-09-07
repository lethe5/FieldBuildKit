"""Acceptance coverage for Type 2/3 site styling and editable-layer order.

The acceptance harness reopens the generated QGIS project through the existing real-PyQGIS
build seam.  Project XML is used only to inspect persisted, semantic QGIS facts that the current
harness does not expose as a dedicated function: layer opacity, layer-tree order, geometry type,
and read-only state.  The generated QML sidecar is inspected for the report-local style and for
the existing map/table/CSV execution paths; this keeps the tests deterministic on the macOS host
without a browser or a live tile service.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = pytest.mark.qgis

TYPE_2_3 = ("temporary_plots", "permanent_plots")


def _build(acceptance_api, built_project_by_type, survey_type: str) -> dict:
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    return result


def _project_root(result: dict) -> ET.Element:
    return ET.parse(result["qgs_path"]).getroot()


def _table_from_source(source: str) -> str | None:
    match = re.search(r"(?:^|\|)layername=([^|]+)", source or "")
    return match.group(1) if match else None


def _project_layers(root: ET.Element) -> dict[str, ET.Element]:
    return {
        element.findtext("id", ""): element
        for element in root.findall(".//maplayer")
        if element.findtext("id")
    }


def _layer_by_table(root: ET.Element, table_name: str) -> ET.Element:
    for layer in _project_layers(root).values():
        if _table_from_source(layer.findtext("datasource", "")) == table_name:
            return layer
    raise AssertionError(f"generated project has no layer backed by table {table_name!r}")


def _layer_tree_tables(root: ET.Element) -> list[str]:
    tables = []
    for node in root.iter("layer-tree-layer"):
        table_name = _table_from_source(node.get("source", ""))
        if table_name is not None:
            tables.append(table_name)
    return tables


def _editable_geometry_tables(root: ET.Element) -> list[str]:
    layers = _project_layers(root)
    ordered = []
    for node in root.iter("layer-tree-layer"):
        table_name = _table_from_source(node.get("source", ""))
        layer = layers.get(node.get("id", ""))
        if table_name is None or layer is None:
            continue
        geometry = layer.get("geometry", "").lower()
        read_only = layer.get("readOnly", "0")
        if geometry not in {"", "no geometry", "nogeometry", "unknown"} and read_only != "1":
            ordered.append(table_name)
    return ordered


def _qml_source(result: dict) -> str:
    path = Path(result["project_dir"]) / f"{result['project_slug']}.qml"
    assert path.is_file(), f"expected generated report sidecar: {path}"
    source = path.read_text(encoding="utf-8")
    # The report JavaScript is stored inside QML string literals.  Decode the literal payloads
    # before inspecting browser-visible code; otherwise escaped quotes/newlines would make a
    # valid report style look absent to the acceptance test.
    decoded_pushes = []
    for match in re.finditer(r"html\.push\((\"(?:\\.|[^\"\\])*\")\);", source):
        try:
            decoded_pushes.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    escaped_source = source.replace("\\n", "\n").replace('\\"', '"')
    return "\n".join(decoded_pushes) + "\n" + escaped_source


def _function_body(source: str, name: str) -> str:
    matches = list(re.finditer(rf"\bfunction\s+{re.escape(name)}\s*\(", source))
    assert matches, f"generated report must contain function {name}()"
    # The report template retains a legacy renderer and then installs the final adapter.  The
    # last definition is the live implementation, so inspect it rather than the compatibility
    # definition that appears earlier in the generated sidecar.
    for match in reversed(matches):
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
    raise AssertionError(f"unterminated generated function {name}()")


def _layer_opacity(layer: ET.Element) -> float:
    value = layer.findtext("layerOpacity")
    assert value is not None, "generated QGIS layer must persist layerOpacity"
    return float(value)


# AC-SOP-001 / FR-SOP-001 / FR-SOP-003 / FR-SOP-004 -------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_2_3)
def test_ac001_ac002_site_persists_070_opacity_in_type2_and_type3_project_and_report(
    acceptance_api, built_project_by_type, survey_type
):
    result = _build(acceptance_api, built_project_by_type, survey_type)
    root = _project_root(result)

    site = _layer_by_table(root, "site")
    assert site.get("geometry", "").lower() in {"polygon", "multipolygon"}
    assert _layer_opacity(site) == pytest.approx(0.70, abs=1e-9)

    source = _qml_source(result)
    render_map = _function_body(source, "renderMap")
    assert re.search(r"anchor_table\s*===\s*[\"']site[\"']", render_map)
    assert re.search(r"(?:fillOpacity|opacity)\s*:\s*(?:0\.70|0\.7|\.70|\.7)", render_map)
    assert "map_features" in render_map


# AC-SOP-003 / FR-SOP-005 / C-SOP-001 / C-SOP-004 ---------------------------------------------


def test_ac003_type1_and_type4_site_keep_their_opacity_while_type4_community_is_20_percent(
    built_project_by_type,
):
    type1_root = _project_root(_build(None, built_project_by_type, "simple_inventory"))
    inventory = _layer_by_table(type1_root, "inventory_observation")
    assert _layer_opacity(inventory) == pytest.approx(1.0, abs=1e-9)

    type4_root = _project_root(_build(None, built_project_by_type, "vegetation_mapping"))
    site = _layer_by_table(type4_root, "site")
    community = _layer_by_table(type4_root, "community")
    assert _layer_opacity(site) == pytest.approx(1.0, abs=1e-9)
    assert _layer_opacity(community) == pytest.approx(0.20, abs=1e-9)


@pytest.mark.parametrize(
    "survey_type,anchor_table",
    [("temporary_plots", "survey"), ("permanent_plots", "plot")],
)
def test_ac003_site_opacity_does_not_change_type2_type3_anchor_layer_style(
    built_project_by_type, survey_type, anchor_table
):
    root = _project_root(_build(None, built_project_by_type, survey_type))
    anchor = _layer_by_table(root, anchor_table)
    assert _layer_opacity(anchor) == pytest.approx(1.0, abs=1e-9)


# AC-SOP-004 / C-SOP-002 -----------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_2_3)
def test_ac004_existing_join_table_and_csv_paths_remain_in_report(
    built_project_by_type, survey_type
):
    result = _build(None, built_project_by_type, survey_type)
    source = _qml_source(result)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert "selected_korean_name" in joined
    assert "selected_scientific_name" in joined
    assert "selected_ktsn" in joined
    assert "rows.push" in joined
    assert "function saveCsv" in source
    assert "qpbBuildHtmlReport" in source


# AC-SOP-005 / FR-SOP-004 / A-SOP-003 / E-SOP-003 ----------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_2_3)
def test_ac005_local_report_style_is_feature_local_and_keeps_offline_map_path(
    built_project_by_type, survey_type
):
    source = _qml_source(_build(None, built_project_by_type, survey_type))
    render_map = _function_body(source, "renderMap")
    assert "geometry.valid" in render_map
    assert "map_features" in render_map
    assert re.search(r"anchor_table\s*===\s*[\"']site[\"']", render_map)
    assert "qpbSelectBackground(map)" in render_map
    assert "fillOpacity" in render_map


# AC-SOP-006 / A-SOP-002 / E-SOP-004 ----------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_2_3)
def test_ac006_missing_site_geometry_keeps_report_empty_geometry_contract(
    built_project_by_type, survey_type
):
    source = _qml_source(_build(None, built_project_by_type, survey_type))
    assert "유효한 도형 없음" in source
    assert "geometry_limitations" in source
    assert "유효하지 않거나 누락된 도형" in source
    assert "map_features" in _function_body(source, "renderMap")


# AC-SOP-007 / FR-SOP-006 / C-SOP-005 / D-SOP-001 --------------------------------------------


@pytest.mark.parametrize("survey_type,expected_editable_order", [
    ("temporary_plots", ["survey", "site"]),
    ("permanent_plots", ["plot", "site"]),
    ("vegetation_mapping", ["community", "site"]),
])
def test_ac007_site_is_last_among_editable_geometry_layers_only(
    built_project_by_type, survey_type, expected_editable_order
):
    root = _project_root(_build(None, built_project_by_type, survey_type))
    all_tables = _layer_tree_tables(root)
    editable_geometry = _editable_geometry_tables(root)

    assert "site" in all_tables
    assert editable_geometry == expected_editable_order
    assert editable_geometry[-1] == "site"

    # The lookup/reference layer and the relation-only tables are deliberately not part of the
    # ordered subset, even though they are present in the generated project tree.
    assert "ktsn_accepted_name_lookup" in all_tables
    assert "ktsn_accepted_name_lookup" not in editable_geometry
    assert all(
        table_name not in editable_geometry
        for table_name in ("observation", "survey_photo", "plot_photo")
    )
