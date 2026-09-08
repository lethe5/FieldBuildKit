"""Unit regressions for generated canonical-taxonomy lookup and candidate handling."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from qfield_builder import qml_plugin


def _widget_source(*, canonical: bool = True) -> str:
    return qml_plugin.render_identification_widget_qml(
        "array('leaf_photo_path')",
        layer_context="inventory_observation",
        canonical_reference_enabled=canonical,
    )


def _function(source: str, name: str) -> str:
    start = source.index("function " + name)
    if name == "qpbLookupCanonicalTaxonomy":
        end = source.index("\n    // Probability rasters", start)
        return source[start:end]
    if name == "qpbHandlePlantNetResponse":
        end = source.index("\n    // Compatibility hook", start)
        return source[start:end]
    end = source.index("\n    }", start) + len("\n    }")
    return source[start:end]


def _run_node(script: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute generated QML JavaScript")
    completed = subprocess.run(
        [node, "-e", script], check=True, capture_output=True, text=True, timeout=10
    )
    return json.loads(completed.stdout)


def _invoke_lookup(evaluated_value) -> dict:
    source = _widget_source()
    functions = "\n".join(
        _function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
        )
    )
    value = json.dumps(evaluated_value, ensure_ascii=False)
    return _run_node(
        f"""
var captured = [];
var expression = {{evaluate: function(text) {{
    captured.push(String(text));
    return captured.length === 1 ? "식물 분류 참조표" : {value};
}}}};
{functions}
var result = qpbLookupCanonicalTaxonomy("Testus demo");
process.stdout.write(JSON.stringify({{result: result, expressions: captured}}));
"""
    )


def test_qpb_lookup_captures_the_nested_expression_from_generated_qml():
    captured = _invoke_lookup({"matched": False})

    assert len(captured["expressions"]) == 2
    assert captured["expressions"][0] == "layer_property('식물 분류 참조표', 'name')"
    lookup_expression = captured["expressions"][1]
    assert lookup_expression.startswith("with_variable('groups'")
    assert "aggregate('식물 분류 참조표'" in lookup_expression
    assert "get_feature('식물 분류 참조표'" in lookup_expression
    assert lookup_expression.count("(") == lookup_expression.count(")")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            {
                "matched": True,
                "ambiguous": False,
                "matched_ktsn": "K1",
                "accepted_ktsn": "K1",
                "taxon_status": "정명",
                "selected_ktsn": "K1",
                "selected_korean_name": "테스트종",
                "selected_scientific_name": "Testus demo",
                "selected_scientific_name_without_authority": "Testus demo",
            },
            {"available": True, "matched": True, "selected_ktsn": "K1"},
        ),
        ({"matched": False}, {"available": True, "matched": False}),
        (
            {
                "matched": True,
                "ambiguous": True,
                "ambiguous_reason": "two accepted groups",
            },
            {"available": True, "matched": True, "ambiguous": True},
        ),
        (
            {
                "matched": True,
                "ambiguous": False,
                "selected_ktsn": None,
                "selected_korean_name": None,
                "selected_scientific_name": None,
            },
            {"available": False, "reason": "canonical_taxonomy_row_invalid"},
        ),
    ],
)
def test_qpb_lookup_keeps_fail_closed_result_contract(value, expected):
    result = _invoke_lookup(value)["result"]
    for key, expected_value in expected.items():
        assert result.get(key) == expected_value


def _invoke_response(value, *, canonical: bool = True) -> dict:
    source = _widget_source(canonical=canonical)
    assert "readonly property bool qpbCandidateSelectionEnabled: true" in source
    functions = "\n".join(
        _function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
            "qpbHandlePlantNetResponse",
        )
    )
    evaluated = json.dumps(value, ensure_ascii=False)
    return _run_node(
        f"""
var captured = [];
var expression = {{evaluate: function(text) {{
    captured.push(String(text));
    return captured.length === 1 ? "식물 분류 참조표" : {evaluated};
}}}};
var qpbCanonicalReferenceRequired = {str(canonical).lower()};
var qpbCandidateSelectionEnabled = true;
var qpbCandidatesModel = [];
var qpbLastLocation = null;
var qpbLastModelVersion = "";
var qpbManualEntryPanel = {{visible: false}};
var qpbStatusLabel = {{text: ""}};
function qpbFormatProbability() {{
    return {{text: "확률 데이터 없음", value: null, pending: false, warning: false, request_id: ""}};
}}
{functions}
qpbHandlePlantNetResponse({{version: "fixture", results: [{{score: 0.63, species: {{
    scientificNameWithoutAuthor: "Testus demo", scientificName: "Testus demo"
}}}}]}});
process.stdout.write(JSON.stringify({{candidates: qpbCandidatesModel,
    status: qpbStatusLabel.text, manual: qpbManualEntryPanel.visible}}));
"""
    )


def test_generated_widget_displays_a_valid_canonical_candidate():
    result = _invoke_response(
        {
            "matched": True,
            "ambiguous": False,
            "matched_ktsn": "K1",
            "accepted_ktsn": "K1",
            "taxon_status": "정명",
            "selected_ktsn": "K1",
            "selected_korean_name": "테스트종",
            "selected_scientific_name": "Testus demo",
            "selected_scientific_name_without_authority": "Testus demo",
        }
    )

    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["korean_name_display"] == "테스트종"
    assert candidate["scientific_name"] == "Testus demo"
    assert candidate["ktsn_match"]["selected_ktsn"] == "K1"
    assert "canonical_taxonomy_lookup_failed" not in result["status"]
    assert result["manual"] is False


def test_generated_widget_preserves_canonical_failure_message_and_does_not_display_candidates():
    result = _invoke_response(None)

    assert result["candidates"] == []
    assert result["manual"] is True
    assert "식물 분류 참조표를 사용할 수 없어 자동 동정 후보를 표시할 수 없습니다" in result[
        "status"
    ]
    assert "canonical_taxonomy_lookup_failed" in result["status"]


def test_canonical_branch_does_not_silently_use_legacy_csv_fallback():
    source = _widget_source(canonical=True)
    response = _function(source, "qpbHandlePlantNetResponse")
    branch_start = response.index("if (canonicalReferenceRequired)")
    canonical_branch = response[branch_start : response.index("} else {", branch_start)]
    assert "qpbLookupCanonicalTaxonomy" in canonical_branch
    assert "qpbLoadCsv" not in canonical_branch
    assert "qpbMatchKtsn" not in canonical_branch
    assert "canonical_taxonomy_lookup_failed" in response

    legacy_source = _widget_source(canonical=False)
    legacy_response = _function(legacy_source, "qpbHandlePlantNetResponse")
    legacy_branch = legacy_response[legacy_response.index("} else {") :]
    assert "qpbLoadCsv" in legacy_branch
    assert "qpbMatchKtsn" in legacy_branch
