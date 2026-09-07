"""Regression tests for canonical taxonomy layer-ID resolution in generated QField QML.

These tests intentionally exercise the generated JavaScript rather than reimplementing the
canonical lookup in Python.  The renderer receives the project layer ID as an explicit input;
Node is used only as a small harness around the generated functions so the exact production
expressions sent to ``expression.evaluate()`` can be captured.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from qfield_builder import qml_plugin


CANONICAL_LAYER_ID = "canonical-layer-id-7f2a"
DISPLAY_NAME = "식물 분류 참조표"


def _widget_source(*, canonical_layer_id: str | None = CANONICAL_LAYER_ID, canonical: bool = True):
    """Render a production widget with the new explicit layer-ID input."""
    return qml_plugin.render_identification_widget_qml(
        "array('leaf_photo_path')",
        layer_context="inventory_observation",
        canonical_reference_enabled=canonical,
        canonical_layer_id=canonical_layer_id,
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


def _lookup_functions(source: str) -> str:
    return "\n".join(
        _function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
        )
    )


def _invoke_lookup(
    evaluated_value,
    *,
    source: str | None = None,
    first_value=DISPLAY_NAME,
    expression_present: bool = True,
    canonical_layer_id: str = CANONICAL_LAYER_ID,
) -> dict:
    source = source or _widget_source()
    value = json.dumps(evaluated_value, ensure_ascii=False)
    first = json.dumps(first_value, ensure_ascii=False)
    expression_decl = (
        "var expression = {evaluate: function(text) {\n"
        "    captured.push(String(text));\n"
        f"    return captured.length === 1 ? {first} : {value};\n"
        "}};"
        if expression_present
        else ""
    )
    return _run_node(
        f"""
var captured = [];
var qpbCanonicalLayerId = {json.dumps(canonical_layer_id)};
{expression_decl}
{_lookup_functions(source)}
var result = qpbLookupCanonicalTaxonomy("Testus demo");
process.stdout.write(JSON.stringify({{result: result, expressions: captured}}));
"""
    )


def _invoke_response(value, *, canonical: bool = True, source: str | None = None) -> dict:
    source = source or _widget_source(canonical=canonical)
    evaluated = json.dumps(value, ensure_ascii=False)
    functions = "\n".join(
        _function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbNormalizeName",
            "qpbLookupCanonicalTaxonomy",
            "qpbHandlePlantNetResponse",
        )
    )
    return _run_node(
        f"""
var captured = [];
var qpbCanonicalLayerId = {json.dumps(CANONICAL_LAYER_ID)};
var expression = {{evaluate: function(text) {{
    captured.push(String(text));
    return captured.length === 1 ? {json.dumps(DISPLAY_NAME, ensure_ascii=False)} : {evaluated};
}}}};
var qpbCanonicalReferenceRequired = {str(canonical).lower()};
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
    status: qpbStatusLabel.text, manual: qpbManualEntryPanel.visible,
    expressions: captured}}));
"""
    )


def test_new_renderer_requires_and_embeds_the_project_layer_id():
    source = _widget_source()

    assert "qpbCanonicalLayerId" in source
    assert json.dumps(CANONICAL_LAYER_ID) in source
    assert DISPLAY_NAME in source  # retained only for the documented old-project fallback
    assert "ktsn_taxonomy_reference" not in source


def test_canonical_lookup_targets_the_embedded_id_for_every_expression_function():
    captured = _invoke_lookup({"matched": False})

    assert len(captured["expressions"]) == 2
    assert captured["expressions"][0] == (
        f"layer_property('{CANONICAL_LAYER_ID}', 'name')"
    )
    lookup_expression = captured["expressions"][1]
    assert f"aggregate('{CANONICAL_LAYER_ID}'" in lookup_expression
    assert f"get_feature('{CANONICAL_LAYER_ID}'" in lookup_expression
    assert DISPLAY_NAME not in lookup_expression
    assert "ktsn_taxonomy_reference" not in lookup_expression
    assert lookup_expression.count("(") == lookup_expression.count(")")


def test_renderer_forwards_the_actual_layer_id_to_the_widget(monkeypatch):
    """The worker seam must pass the ID returned by ``layer.id()``, not a display/table name."""
    from qfield_builder import qgis_worker, schemas

    captured = {}

    class FakeElement:
        def __init__(self, name, parent):
            self.name = name
            self.parent = parent
            self.qml = ""

        def setQmlCode(self, value):
            self.qml = value

    class FakeContainer:
        def __init__(self):
            self.elements = []

        def children(self):
            return []

        def addChildElement(self, element):
            self.elements.append(element)

    class FakeForm:
        def __init__(self):
            self.root = FakeContainer()

        def invisibleRootContainer(self):
            return self.root

    class FakeLayer:
        def __init__(self):
            self._form = FakeForm()

        def id(self):
            return CANONICAL_LAYER_ID

        def editFormConfig(self):
            return self._form

        def updateFields(self):
            pass

    class FakeQmlElement:
        def __new__(cls, name, parent):
            return FakeElement(name, parent)

    def fake_render(*args, **kwargs):
        captured.update(kwargs)
        return "fixture-qml"

    monkeypatch.setattr(qgis_worker.qml_plugin, "render_identification_widget_qml", fake_render)
    monkeypatch.setattr(qgis_worker, "_identification_photo_paths_expression", lambda _t: "''")
    monkeypatch.setattr(qgis_worker.korean_layer_display_names, "display_name_for", lambda n: n)

    table = schemas.get_schema("simple_inventory")["inventory_observation"]
    qgis_worker._add_identification_widget(
        {"QgsAttributeEditorQmlElement": FakeQmlElement},
        FakeLayer(),
        table,
        "simple_inventory",
        canonical_reference_enabled=True,
        canonical_layer_id=CANONICAL_LAYER_ID,
    )

    assert captured["canonical_layer_id"] == CANONICAL_LAYER_ID
    assert captured["canonical_layer_id"] != DISPLAY_NAME
    assert captured["canonical_layer_id"] != "ktsn_taxonomy_reference"


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
            {"matched": True, "ambiguous": True, "ambiguous_reason": "two groups"},
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
def test_id_based_lookup_preserves_selected_fields_and_fail_closed_semantics(value, expected):
    result = _invoke_lookup(value)["result"]
    for key, expected_value in expected.items():
        assert result.get(key) == expected_value


def test_invalid_id_and_missing_expression_context_are_unavailable():
    invalid_id = _invoke_lookup({"matched": True}, first_value="다른 레이어")
    assert invalid_id["result"]["available"] is False
    assert invalid_id["result"]["reason"] == "canonical_taxonomy_layer_missing"

    missing_context = _invoke_lookup(None, expression_present=False)
    assert missing_context["result"]["available"] is False
    assert missing_context["result"]["reason"] == "canonical_expression_unavailable"


def test_valid_id_based_candidate_display_keeps_all_selected_identity_fields():
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


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"matched": False},
        {"matched": True, "ambiguous": True, "ambiguous_reason": "two groups"},
    ],
)
def test_no_match_ambiguous_and_lookup_failure_never_display_a_candidate(value):
    result = _invoke_response(value)
    assert result["candidates"] == []
    if value is None:
        assert result["manual"] is True
        assert "canonical_taxonomy_lookup_failed" in result["status"]


def test_canonical_branch_does_not_activate_legacy_csv_fallback():
    canonical = _function(_widget_source(canonical=True), "qpbHandlePlantNetResponse")
    branch_start = canonical.index("if (canonicalReferenceRequired)")
    canonical_branch = canonical[branch_start : canonical.index("} else {", branch_start)]
    assert "qpbLookupCanonicalTaxonomy" in canonical_branch
    assert "qpbLoadCsv" not in canonical_branch
    assert "qpbMatchKtsn" not in canonical_branch

    legacy = _function(_widget_source(canonical=False), "qpbHandlePlantNetResponse")
    legacy_branch = legacy[legacy.index("} else {") :]
    assert "qpbLoadCsv" in legacy_branch
    assert "qpbMatchKtsn" in legacy_branch


def test_old_generated_project_without_embedded_id_uses_only_documented_display_name_fallback():
    source = _widget_source(canonical_layer_id=None, canonical=True)
    assert "qpbCanonicalLayerId" in source
    assert DISPLAY_NAME in source
    assert "ktsn_taxonomy_reference" not in source

    result = _invoke_lookup(
        {
            "matched": True,
            "ambiguous": False,
            "matched_ktsn": "K1",
            "accepted_ktsn": "K1",
            "selected_ktsn": "K1",
            "selected_korean_name": "구프로젝트종",
            "selected_scientific_name": "Testus demo",
        },
        source=source,
        first_value=DISPLAY_NAME,
        canonical_layer_id="",
    )
    assert result["result"]["available"] is True
    assert result["result"]["selected_ktsn"] == "K1"
    assert all(DISPLAY_NAME in expression for expression in result["expressions"])
