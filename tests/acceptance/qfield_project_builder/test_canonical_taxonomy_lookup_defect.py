"""QGIS 3.44 parser/evaluator regressions for the compatibility canonical lookup expression."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from qfield_builder import qgis_bridge, qml_plugin


pytestmark = pytest.mark.qgis


def _function(source: str, name: str) -> str:
    start = source.index("function " + name)
    if name == "qpbLookupCanonicalTaxonomy":
        end = source.index("\n    // Probability rasters", start)
        return source[start:end]
    return source[start : source.index("\n    }", start) + len("\n    }")]


def _capture_generated_expression() -> dict:
    # QCR supersedes this expression route for newly generated canonical projects.  Rendering
    # without a runtime-resource descriptor deliberately exercises the retained pre-QCR
    # compatibility path that CTLD's parser regression covers.
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to capture the generated QML expression")
    source = qml_plugin.render_identification_widget_qml(
        "array('leaf_photo_path')",
        layer_context="inventory_observation",
        canonical_reference_enabled=True,
    )
    functions = "\n".join(
        _function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
        )
    )
    script = f"""
var captured = [];
var expression = {{evaluate: function(text) {{
    captured.push(String(text));
    return captured.length === 1 ? "식물 분류 참조표" : {{matched: false}};
}}}};
{functions}
qpbLookupCanonicalTaxonomy("Testus demo");
process.stdout.write(JSON.stringify(captured));
"""
    completed = subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
    expressions = json.loads(completed.stdout)
    assert len(expressions) == 2
    return {"layer": expressions[0], "lookup": expressions[1]}


def _run_qgis_probe(tmp_path: Path, expressions: dict, rows: list[dict]) -> dict:
    """Evaluate captured production expressions in a fresh, isolated QGIS process."""
    script_path = tmp_path / "canonical-expression-probe.py"
    expressions_json = json.dumps(expressions, ensure_ascii=False)
    rows_json = json.dumps(rows, ensure_ascii=False)
    script_path.write_text(
        f"""
import json
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    Qgis,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsField,
    QgsProject,
    QgsVectorLayer,
)

expressions = json.loads({expressions_json!r})
rows = json.loads({rows_json!r})
project = QgsProject.instance()
project.clear()
layer = QgsVectorLayer("None", "식물 분류 참조표", "memory")
field_names = [
    "ktsn", "accepted_ktsn", "taxon_status", "korean_name", "scientific_name",
    "scientific_name_without_authority",
]
layer.dataProvider().addAttributes([QgsField(name, QVariant.String) for name in field_names])
layer.updateFields()
features = []
for row in rows:
    feature = QgsFeature(layer.fields())
    feature.setAttributes([row.get(name) for name in field_names])
    features.append(feature)
layer.dataProvider().addFeatures(features)
layer.updateExtents()
project.addMapLayer(layer)

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
for text in expressions.values():
    expression = QgsExpression(text)
    parsed = not expression.hasParserError()
    value = expression.evaluate(context) if parsed else None
    evaluated.append({{
        "text": text,
        "parser_error": expression.parserErrorString(),
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
        pytest.skip(f"QGIS 3.44 required for this parser regression, got {payload['qgis_version']}")
    return payload


@pytest.mark.parametrize(
    ("scenario", "rows", "expected"),
    [
        (
            "valid",
            [{
                "ktsn": "K1", "accepted_ktsn": "K1", "taxon_status": "정명",
                "korean_name": "테스트종", "scientific_name": "Testus demo",
                "scientific_name_without_authority": "Testus demo",
            }],
            {
                "matched": True,
                "selected_ktsn": "K1",
                "selected_korean_name": "테스트종",
                "selected_scientific_name": "Testus demo",
            },
        ),
        (
            "no-match",
            [{
                "ktsn": "K2", "accepted_ktsn": "K2", "taxon_status": "정명",
                "korean_name": "다른종", "scientific_name": "Otherus species",
                "scientific_name_without_authority": "Otherus species",
            }],
            {"matched": False},
        ),
        (
            "ambiguous",
            [
                {"ktsn": "K1", "accepted_ktsn": "K1", "taxon_status": "정명", "korean_name": "첫종", "scientific_name": "Testus demo", "scientific_name_without_authority": "Testus demo"},
                {"ktsn": "K2", "accepted_ktsn": "K2", "taxon_status": "정명", "korean_name": "둘째종", "scientific_name": "Testus demo", "scientific_name_without_authority": "Testus demo"},
            ],
            {"matched": True, "ambiguous": True},
        ),
        (
            "malformed",
            [{
                "ktsn": None, "accepted_ktsn": None, "taxon_status": "정명",
                "korean_name": None, "scientific_name": None,
                "scientific_name_without_authority": "Testus demo",
            }],
            {"matched": True, "selected_ktsn": None},
        ),
    ],
)
def test_qgis_344_evaluates_captured_lookup_expression_without_parser_or_eval_error(
    tmp_path: Path, scenario: str, rows: list[dict], expected: dict
):
    expressions = _capture_generated_expression()
    payload = _run_qgis_probe(tmp_path, expressions, rows)
    for item in payload["evaluated"]:
        assert not item["has_parser_error"], f"{scenario}: {item}"
        assert not item["has_eval_error"], f"{scenario}: {item}"
    value = payload["evaluated"][1]["value"]
    assert isinstance(value, dict), (scenario, payload)
    for key, expected_value in expected.items():
        assert value.get(key) == expected_value, (scenario, value)


def test_widget_keeps_compatibility_candidate_and_failure_paths():
    widget = qml_plugin.render_identification_widget_qml(
        "array('leaf_photo_path')",
        layer_context="inventory_observation",
        canonical_reference_enabled=True,
    )
    assert "qpbCanonicalReferenceRequired" in widget
    assert "qpbLookupCanonicalTaxonomy" in widget
    assert "selected_ktsn" in widget
    assert "selected_korean_name" in widget
    assert "selected_scientific_name" in widget
    assert "canonical_taxonomy_lookup_failed" in widget
    assert "식물 분류 참조표를 사용할 수 없어 자동 동정 후보를 표시할 수 없습니다" in widget
