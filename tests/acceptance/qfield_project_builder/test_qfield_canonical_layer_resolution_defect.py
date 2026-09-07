"""QGIS 3.44 acceptance tests for generated canonical layer-ID lookup.

The project is created in a temporary directory with a minimal real GeoPackage.  The test then
reopens the generated project in an isolated QGIS process, captures the embedded QML widget, and
evaluates the exact expressions emitted by its production lookup function against the generated
canonical layer.  No live QGIS profile is used.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from qfield_builder import canonical_reference, gpkg, naming, qgis_bridge, qgis_worker


pytestmark = pytest.mark.qgis

CANONICAL_TABLE = "ktsn_taxonomy_reference"
CANONICAL_DISPLAY_NAME = "식물 분류 참조표"
CANONICAL_LAYER_ID = "canonical-layer-id-7f2a"


def _canonical_row(**overrides) -> dict:
    row = {column: "" for column in canonical_reference.LOGICAL_COLUMNS}
    row.update(
        {
            "ktsn": "K1",
            "source_no": "1",
            "taxon_status": "정명",
            "korean_name": "테스트종",
            "scientific_name": "Testus demo",
            "scientific_name_normalized": "Testus demo",
            "scientific_name_without_authority": "Testus demo",
            "authority": "",
            "naming_year": "2020",
            "phylum_scientific_name": "Testophyta",
            "phylum_korean_name": "테스트문",
            "class_scientific_name": "Testopsida",
            "class_korean_name": "테스트강",
            "order_scientific_name": "Testales",
            "order_korean_name": "테스트목",
            "family_scientific_name": "Testaceae",
            "family_korean_name": "테스트과",
            "genus_scientific_name": "Testus",
            "genus_korean_name": "테스트속",
            "accepted_ktsn": "K1",
            "source_url": "https://species.nibr.go.kr/species-detail/K1",
            "content_available": "Y",
            "source_row": 3,
        }
    )
    row.update(overrides)
    return row


def _build_minimal_canonical_project(tmp_path: Path, *, identification: bool = True) -> Path:
    gpkg_path = tmp_path / "canonical.gpkg"
    qgs_path = tmp_path / "canonical.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        "simple_inventory",
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    gpkg.add_ktsn_taxonomy_reference_table(
        str(gpkg_path), CANONICAL_TABLE, [_canonical_row()]
    )
    result = qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type="simple_inventory",
        project_crs="EPSG:4326",
        basemap_config=None,
        identification_enabled=identification,
        ktsn_taxonomy_table_name=CANONICAL_TABLE,
    )
    assert isinstance(result, dict)
    assert qgs_path.exists()
    return qgs_path


def _run_qgis_inspection(qgs_path: Path, tmp_path: Path, *, roundtrip: bool = False) -> dict:
    output_path = tmp_path / "roundtrip.qgs"
    script_path = tmp_path / "inspect-canonical-layer.py"
    script_path.write_text(
        f"""
import json
from qgis.core import Qgis, QgsProject

qgs_path = {str(qgs_path)!r}
roundtrip_path = {str(output_path)!r}
project = QgsProject.instance()
project.clear()
assert project.read(qgs_path)
if {roundtrip!r}:
    assert project.write(roundtrip_path)
    project.clear()
    assert project.read(roundtrip_path)

taxonomy = None
widget_code = ""
for layer in project.mapLayers().values():
    if "|layername={CANONICAL_TABLE}" in layer.source():
        taxonomy = layer
    root = layer.editFormConfig().invisibleRootContainer()
    for element in root.findElements(Qgis.AttributeEditorType.QmlElement):
        try:
            widget_code = element.qmlCode()
        except AttributeError:
            import sip
            from qgis.core import QgsAttributeEditorQmlElement
            widget_code = sip.cast(element, QgsAttributeEditorQmlElement).qmlCode()
        if widget_code:
            break
    if taxonomy is not None and widget_code:
        break

assert taxonomy is not None
print(json.dumps({{
    "qgis_version": Qgis.QGIS_VERSION,
    "canonical_id": taxonomy.id(),
    "canonical_name": taxonomy.name(),
    "canonical_source": taxonomy.source(),
    "widget_code": widget_code,
}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )
    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    if outcome is None:
        pytest.skip("requires a working QGIS/PyQGIS bridge")
    assert outcome["ok"], outcome
    payload = json.loads(outcome["stdout"])
    if not payload["qgis_version"].startswith("3.44"):
        pytest.skip(f"QGIS 3.44 required, got {payload['qgis_version']}")
    return payload


def _qml_function(source: str, name: str) -> str:
    start = source.index("function " + name)
    if name == "qpbLookupCanonicalTaxonomy":
        end = source.index("\n    // Probability rasters", start)
        return source[start:end]
    return source[start : source.index("\n    }", start) + len("\n    }")]


def _capture_production_expressions(widget_code: str, canonical_layer_id: str) -> list[str]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to capture generated QML expressions")
    functions = "\n".join(
        _qml_function(widget_code, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
        )
    )
    script = f"""
var captured = [];
var qpbCanonicalLayerId = {json.dumps(canonical_layer_id)};
var expression = {{evaluate: function(text) {{
    captured.push(String(text));
    return captured.length === 1 ? {json.dumps(CANONICAL_DISPLAY_NAME, ensure_ascii=False)} : {{matched: false}};
}}}};
{functions}
qpbLookupCanonicalTaxonomy("Testus demo");
process.stdout.write(JSON.stringify(captured));
"""
    completed = subprocess.run(
        [node, "-e", script], check=True, capture_output=True, text=True, timeout=10
    )
    expressions = json.loads(completed.stdout)
    assert len(expressions) == 2
    return expressions


def _evaluate_expressions_in_qgis(
    qgs_path: Path, tmp_path: Path, expressions: list[str], rows: list[dict]
) -> dict:
    script_path = tmp_path / "evaluate-canonical-expressions.py"
    script_path.write_text(
        f"""
import json
from qgis.core import (
    Qgis, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsProject
)

expressions = json.loads({json.dumps(expressions, ensure_ascii=False)!r})
project = QgsProject.instance()
project.clear()
assert project.read({str(qgs_path)!r})
context = QgsExpressionContext()
context.appendScope(QgsExpressionContextUtils.globalScope())
context.appendScope(QgsExpressionContextUtils.projectScope(project))

def plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "toVariant"):
        try:
            return plain(value.toVariant())
        except Exception:
            pass
    if hasattr(value, "keys"):
        try:
            return {{str(key): plain(value[key]) for key in value.keys()}}
        except Exception:
            pass
    return str(value)

evaluated = []
for text in expressions:
    expression = QgsExpression(text)
    value = expression.evaluate(context) if not expression.hasParserError() else None
    evaluated.append({{
        "text": text,
        "parser_error": expression.parserErrorString(),
        "eval_error": expression.evalErrorString(),
        "has_parser_error": expression.hasParserError(),
        "has_eval_error": expression.hasEvalError(),
        "value": plain(value),
    }})
print(json.dumps({{"qgis_version": Qgis.QGIS_VERSION, "evaluated": evaluated}}, ensure_ascii=False))
""",
        encoding="utf-8",
    )
    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    if outcome is None:
        pytest.skip("requires a working QGIS/PyQGIS bridge")
    assert outcome["ok"], outcome
    payload = json.loads(outcome["stdout"])
    if not payload["qgis_version"].startswith("3.44"):
        pytest.skip(f"QGIS 3.44 required, got {payload['qgis_version']}")
    return payload


def test_generated_project_propagates_actual_canonical_layer_id_to_embedded_widget(tmp_path):
    qgs_path = _build_minimal_canonical_project(tmp_path)
    inspected = _run_qgis_inspection(qgs_path, tmp_path)

    assert inspected["canonical_name"] == CANONICAL_DISPLAY_NAME
    assert inspected["canonical_id"] != CANONICAL_TABLE
    assert inspected["canonical_id"] in inspected["widget_code"]


def test_qgis_344_parses_and_evaluates_all_captured_production_targets_by_layer_id(tmp_path):
    qgs_path = _build_minimal_canonical_project(tmp_path)
    inspected = _run_qgis_inspection(qgs_path, tmp_path)
    expressions = _capture_production_expressions(
        inspected["widget_code"], inspected["canonical_id"]
    )

    assert expressions[0] == f"layer_property('{inspected['canonical_id']}', 'name')"
    lookup_expression = expressions[1]
    assert f"aggregate('{inspected['canonical_id']} '" not in lookup_expression
    assert f"aggregate('{inspected['canonical_id']}'" in lookup_expression
    assert f"get_feature('{inspected['canonical_id']}'" in lookup_expression
    assert CANONICAL_DISPLAY_NAME not in lookup_expression
    assert CANONICAL_TABLE not in lookup_expression
    assert lookup_expression.count("(") == lookup_expression.count(")")

    payload = _evaluate_expressions_in_qgis(qgs_path, tmp_path, expressions, [_canonical_row()])
    for item in payload["evaluated"]:
        assert item["has_parser_error"] is False, item
        assert item["has_eval_error"] is False, item


def test_qgis_344_valid_row_returns_all_selected_identity_values(tmp_path):
    qgs_path = _build_minimal_canonical_project(tmp_path)
    inspected = _run_qgis_inspection(qgs_path, tmp_path)
    expressions = _capture_production_expressions(
        inspected["widget_code"], inspected["canonical_id"]
    )
    payload = _evaluate_expressions_in_qgis(qgs_path, tmp_path, expressions, [_canonical_row()])
    value = payload["evaluated"][1]["value"]

    assert value["matched"] is True
    assert value["selected_ktsn"] == "K1"
    assert value["selected_korean_name"] == "테스트종"
    assert value["selected_scientific_name"] == "Testus demo"


def test_saved_and_reloaded_project_keeps_the_same_id_in_widget_and_project(tmp_path):
    qgs_path = _build_minimal_canonical_project(tmp_path)
    initial = _run_qgis_inspection(qgs_path, tmp_path)
    reloaded = _run_qgis_inspection(qgs_path, tmp_path, roundtrip=True)

    assert reloaded["canonical_id"] == initial["canonical_id"]
    assert reloaded["canonical_id"] in reloaded["widget_code"]
