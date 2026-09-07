"""Real, PyQGIS-backed regression test for the Korean relation-display-name mechanism
(FR-QPB-128/Section 8.6/AC-QPB-111; Decision Log D-73/D-77).

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.qgis_worker.build_qgis_project`) and reads the relations back via
`qfield_builder.relation_inspect.inspect_relations`, mirroring the existing convention in
`test_qgis_worker_field_aliases.py` (skipped when no real, bridgeable QGIS/PyQGIS runtime is
available on this machine). The acceptance suite's `test_korean_relation_display_names.py` is the
authoritative, exhaustive coverage of this same behavior; this file is a smaller,
implementation-level regression check colocated with this codebase's other `qgis_worker` unit
tests.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from qfield_builder import (
    editor_widget_inspect,
    gpkg,
    korean_relation_display_names,
    naming,
    qgis_worker,
    relation_inspect,
    schemas,
)
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)


def _build_project(tmp_path: Path, survey_type: str) -> str:
    gpkg_path = tmp_path / f"{survey_type}.gpkg"
    qgs_path = tmp_path / f"{survey_type}.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        survey_type,
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=survey_type,
        project_crs="EPSG:4326",
        basemap_config=None,
    )
    return str(tmp_path)


def _every_relation_id(survey_type: str) -> set[str]:
    schema = schemas.get_schema(survey_type)
    return {
        table_def.foreign_key.relation_id
        for table_def in schema.values()
        if table_def.foreign_key is not None
    }


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_every_relation_id_is_unchanged_and_stable(tmp_path: Path, survey_type: str):
    """FR-QPB-056/FR-QPB-128: the relation's own stable ID (`QgsRelation.setId()`) must remain
    completely unaffected by the Korean display-name requirement."""
    project_dir = _build_project(tmp_path, survey_type)
    expected_ids = _every_relation_id(survey_type)
    if not expected_ids:
        pytest.skip(f"{survey_type} defines no foreign keys/relations")

    info = relation_inspect.inspect_relations(project_dir)
    assert expected_ids <= set(info["relation_ids"]), (
        f"{survey_type}: expected relation IDs {expected_ids} to be present, "
        f"got {sorted(info['relation_ids'])!r}"
    )


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_every_relation_name_is_the_confirmed_korean_display_name(tmp_path: Path, survey_type: str):
    """FR-QPB-128/Section 8.6: each relation's separate, human-facing `name()` must be the
    Section 8.6-confirmed Korean display name -- never the raw relation-ID string."""
    project_dir = _build_project(tmp_path, survey_type)
    expected_ids = _every_relation_id(survey_type)
    if not expected_ids:
        pytest.skip(f"{survey_type} defines no foreign keys/relations")

    info = relation_inspect.inspect_relations(project_dir)
    for relation_id in expected_ids:
        expected_name = korean_relation_display_names.display_name_for(relation_id)
        actual_name = info["names"].get(relation_id)
        assert actual_name == expected_name, (
            f"{survey_type}.{relation_id}: expected name() {expected_name!r}, got {actual_name!r}"
        )
        assert actual_name != relation_id, (
            f"{survey_type}.{relation_id}: name() must never be the raw relation-ID string itself"
        )


def test_related_record_project_keeps_deferred_fk_transaction_groups(tmp_path: Path):
    """Nested daughters need deferred FKs and UUID defaults available before child creation."""
    project_dir = Path(_build_project(tmp_path, "permanent_plots"))
    project_xml = ET.parse(project_dir / "permanent_plots.qgs").getroot()

    assert project_xml.find("transaction").get("mode") == "AutomaticGroups"
    assert "EvaluateDefaultValuesOnProviderSide" in (
        project_xml.find("projectFlags").get("set") or ""
    )


@pytest.mark.parametrize(
    ("survey_type", "table_name"),
    (("temporary_plots", "survey"), ("permanent_plots", "plot")),
)
def test_directly_drawn_geometry_defaults_to_its_intersecting_site(
    tmp_path: Path, survey_type: str, table_name: str
):
    project_dir = _build_project(tmp_path, survey_type)
    info = editor_widget_inspect.inspect_editor_widget(project_dir, table_name, "site_id")

    assert info["default_value_expression"] == qgis_worker._overlapping_site_id_default_expression()
    assert info["apply_on_update"] is False


@pytest.mark.parametrize(
    ("survey_type", "table_name"),
    (("temporary_plots", "survey"), ("permanent_plots", "plot")),
)
def test_intersecting_site_default_resolves_the_korean_named_site_layer(
    tmp_path: Path, survey_type: str, table_name: str
):
    """The expression must resolve ``조사지``, not the hidden GeoPackage table name."""
    gpkg_path = tmp_path / f"{survey_type}-site-default.gpkg"
    qgs_path = tmp_path / f"{survey_type}-site-default.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        survey_type,
        naming.new_project_id(),
        seed_sites=[
            {
                "site_name": "겹치는 조사지",
                "geom_wkt": (
                    "MULTIPOLYGON(((127.10 37.50, 127.11 37.50, "
                    "127.11 37.51, 127.10 37.51, 127.10 37.50)))"
                ),
            }
        ],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path), qgs_path=str(qgs_path), survey_type=survey_type,
        project_crs="EPSG:4326", basemap_config=None,
    )
    script_path = tmp_path / f"evaluate-{survey_type}-site-default.py"
    expression = qgis_worker._overlapping_site_id_default_expression()
    script_path.write_text(
        f"""
import json
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsGeometry, QgsProject
from qfield_builder.layer_lookup import find_layer_by_table_name

project = QgsProject.instance()
project.clear()
assert project.read({str(qgs_path)!r})
site_layer = find_layer_by_table_name(project, "site")
layer = find_layer_by_table_name(project, {table_name!r})
assert site_layer is not None and layer is not None
site = next(site_layer.getFeatures())
feature = QgsFeature(layer.fields())
feature.setGeometry(QgsGeometry.fromWkt("Point (127.105 37.505)"))
context = QgsExpressionContext()
context.appendScope(QgsExpressionContextUtils.globalScope())
context.appendScope(QgsExpressionContextUtils.projectScope(project))
context.appendScope(QgsExpressionContextUtils.layerScope(layer))
context.setFeature(feature)
expression = QgsExpression({expression!r})
value = expression.evaluate(context)
print(json.dumps({{
    "ok": not expression.hasParserError() and not expression.hasEvalError(),
    "value": value,
    "site_id": site["site_id"],
    "error": expression.evalErrorString(),
}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )
    from qfield_builder import qgis_bridge

    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    assert outcome and outcome["ok"], outcome
    result = json.loads(outcome["stdout"])
    assert result["ok"], result
    assert result["value"] == result["site_id"]


@pytest.mark.parametrize(
    ("table_name", "field_name", "expected_expression", "apply_on_update"),
    (
        ("plot", "plot_id", "uuid('WithoutBraces')", False),
        ("survey", "survey_id", "uuid('WithoutBraces')", False),
        ("observation", "observation_id", "uuid('WithoutBraces')", False),
        ("plot", "qpb_plot_geometry_wkt", "geom_to_wkt($geometry)", True),
        ("survey", "qpb_plot_geometry_wkt", "current_parent_value('qpb_plot_geometry_wkt')", False),
        ("observation", "qpb_plot_geometry_wkt", "current_parent_value('qpb_plot_geometry_wkt')", False),
    ),
)
def test_type3_nested_form_keys_are_stable_and_location_snapshot_is_available(
    tmp_path: Path, table_name: str, field_name: str, expected_expression: str, apply_on_update: bool
):
    """Regression: nested related records keep immutable keys and pass plot geometry one level at a time."""
    project_dir = _build_project(tmp_path, "permanent_plots")
    info = editor_widget_inspect.inspect_editor_widget(project_dir, table_name, field_name)

    assert info["default_value_expression"] == expected_expression, info
    assert info["apply_on_update"] is apply_on_update, info
    if field_name.endswith("_id"):
        assert info["widget_type"] == "Hidden", info
        assert info["is_read_only"] is True, info


def test_type3_internal_values_remain_in_the_existing_details_form(tmp_path: Path):
    """Keep the previously working two-tab QField form layout while retaining internal fields."""
    project_dir = Path(_build_project(tmp_path, "permanent_plots"))
    root = ET.parse(project_dir / "permanent_plots.qgs").getroot()

    for table_name, expected_fields in {
        "plot": {"plot_id", "qpb_plot_geometry_wkt"},
        "survey": {"survey_id", "qpb_plot_geometry_wkt"},
        "observation": {"observation_id", "qpb_plot_geometry_wkt"},
    }.items():
        for maplayer in root.iter("maplayer"):
            datasource = maplayer.findtext("datasource") or ""
            if f"layername={table_name}" not in datasource:
                continue
            form = maplayer.find(".//attributeEditorForm")
            assert form is not None
            details = next(
                (
                    element
                    for element in form
                    if element.tag == "attributeEditorContainer" and element.get("name") == "Details"
                ),
                None,
            )
            assert details is not None, table_name
            actual_fields = {
                field.get("name") for field in details.iter("attributeEditorField")
            }
            assert expected_fields <= actual_fields, (table_name, actual_fields)
            break
        else:
            raise AssertionError(f"missing {table_name} map layer")


def test_type3_observation_location_uses_its_own_snapshot_before_parent_lookup(tmp_path: Path):
    """The embedded QML expression has only the observation context, so its snapshot must suffice."""
    project_dir = Path(_build_project(tmp_path, "permanent_plots"))
    script_path = tmp_path / "evaluate-observation-snapshot.py"
    expression = qgis_worker._authoritative_location_expression("permanent_plots", "observation")
    script_path.write_text(
        f"""
import json
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsProject
from qfield_builder.layer_lookup import find_layer_by_table_name

project = QgsProject.instance()
project.clear()
assert project.read({str(project_dir / "permanent_plots.qgs")!r})
layer = find_layer_by_table_name(project, "observation")
assert layer is not None
feature = QgsFeature(layer.fields())
feature.setAttribute("survey_id", "not-needed-for-snapshot")
feature.setAttribute("qpb_plot_geometry_wkt", "Point (127.25 37.75)")
context = QgsExpressionContext()
context.appendScope(QgsExpressionContextUtils.globalScope())
context.appendScope(QgsExpressionContextUtils.projectScope(project))
context.setFeature(feature)
expression = QgsExpression({expression!r})
value = expression.evaluate(context)
print(json.dumps({{
    "ok": not expression.hasParserError() and not expression.hasEvalError(),
    "value": value,
    "parser_error": expression.parserErrorString(),
    "eval_error": expression.evalErrorString(),
}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )

    from qfield_builder import qgis_bridge

    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    if outcome is None:
        pytest.skip("requires a working QGIS/PyQGIS bridge")
    assert outcome["ok"], outcome
    payload = json.loads(outcome["stdout"])
    assert payload["ok"], payload
    assert payload["value"] == "127.25|37.75"


def test_type4_community_location_evaluates_to_its_polygon_centroid(tmp_path: Path):
    """A Type 4 photo-identification request samples at the live community polygon centroid."""
    project_dir = Path(_build_project(tmp_path, "vegetation_mapping"))
    script_path = tmp_path / "evaluate-community-centroid.py"
    expression = qgis_worker._authoritative_location_expression("vegetation_mapping", "community")
    script_path.write_text(
        f"""
import json
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsGeometry, QgsProject
from qfield_builder.layer_lookup import find_layer_by_table_name

project = QgsProject.instance()
project.clear()
assert project.read({str(project_dir / "vegetation_mapping.qgs")!r})
layer = find_layer_by_table_name(project, "community")
assert layer is not None
feature = QgsFeature(layer.fields())
feature.setGeometry(QgsGeometry.fromWkt(
    "MULTIPOLYGON(((127.0 37.5, 127.5 37.5, 127.5 38.0, 127.0 38.0, 127.0 37.5)))"
))
context = QgsExpressionContext()
context.appendScope(QgsExpressionContextUtils.globalScope())
context.appendScope(QgsExpressionContextUtils.projectScope(project))
context.setFeature(feature)
expression = QgsExpression({expression!r})
value = expression.evaluate(context)
print(json.dumps({{
    "ok": not expression.hasParserError() and not expression.hasEvalError(),
    "value": value,
    "parser_error": expression.parserErrorString(),
    "eval_error": expression.evalErrorString(),
}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )

    from qfield_builder import qgis_bridge

    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    if outcome is None:
        pytest.skip("requires a working QGIS/PyQGIS bridge")
    assert outcome["ok"], outcome
    payload = json.loads(outcome["stdout"])
    assert payload["ok"], payload
    assert payload["value"] == "127.25|37.75"


def test_get_feature_sees_an_uncommitted_plot_geometry_in_the_edit_buffer(tmp_path: Path):
    """`get_feature()` must resolve the live edit buffer for the generated permanent_plots project."""
    project_dir = Path(_build_project(tmp_path, "permanent_plots"))
    script_path = tmp_path / "evaluate-uncommitted-plot.py"
    script_path.write_text(
        f"""
import json
from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsProject,
)

from qfield_builder.layer_lookup import find_layer_by_table_name

project = QgsProject.instance()
project.clear()
assert project.read({str(project_dir / "permanent_plots.qgs")!r})

plot_layer = find_layer_by_table_name(project, "plot")
assert plot_layer is not None
assert plot_layer.startEditing()

plot_id = "11111111-1111-1111-1111-111111111111"
plot_geom = QgsGeometry.fromWkt("Point (127.25 37.75)")
feature = QgsFeature(plot_layer.fields())
feature.setGeometry(plot_geom)
feature.setAttribute("plot_id", plot_id)
feature.setAttribute("plot_name", "Uncommitted plot")
feature.setAttribute("site_id", "22222222-2222-2222-2222-222222222222")
assert plot_layer.addFeature(feature)

context = QgsExpressionContext()
context.appendScope(QgsExpressionContextUtils.globalScope())
context.appendScope(QgsExpressionContextUtils.projectScope(project))
context.setFeature(feature)

x_expression = QgsExpression(
    f"x(geometry(get_feature('{{plot_layer.name()}}', 'plot_id', '{{plot_id}}')))"
)
y_expression = QgsExpression(
    f"y(geometry(get_feature('{{plot_layer.name()}}', 'plot_id', '{{plot_id}}')))"
)
x_value = x_expression.evaluate(context)
y_value = y_expression.evaluate(context)

print(json.dumps({{
    "ok": not x_expression.hasEvalError() and not y_expression.hasEvalError(),
    "x": x_value,
    "y": y_value,
    "expected_x": plot_geom.asPoint().x(),
    "expected_y": plot_geom.asPoint().y(),
    "x_error": x_expression.evalErrorString(),
    "y_error": y_expression.evalErrorString(),
}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )

    from qfield_builder import qgis_bridge

    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    if outcome is None:
        pytest.skip("requires a working QGIS/PyQGIS bridge")
    assert outcome["ok"], outcome
    payload = json.loads(outcome["stdout"])
    assert payload["ok"], payload
    assert payload["x"] == pytest.approx(payload["expected_x"])
    assert payload["y"] == pytest.approx(payload["expected_y"])
