"""Regression tests for the final canonical/report/write-back review findings."""

from __future__ import annotations

import json
import shutil
import subprocess
from unittest.mock import patch

import pytest

from qfield_builder import canonical_reference, html_report_core, qml_plugin


def test_integrated_report_keeps_envelope_when_node_adapter_is_unavailable():
    fixture = {
        "survey_type": "simple_inventory",
        "source_columns": [
            {
                "id": "name",
                "source_table": "inventory_observation",
                "source_field": "selected_korean_name",
                "schema_order": 0,
            }
        ],
        "source_rows": [
            {
                "source_row_id": "obs-1",
                "values": {"name": "테스트종"},
                "geometry": {"format": "wkt", "value": "POINT (127 37)"},
            }
        ],
    }
    with patch.object(html_report_core.subprocess, "run", side_effect=OSError("node missing")):
        result = html_report_core.render_html_report_integrated_fixture(fixture)

    assert result["success"] is True
    assert result["overview_cards"]
    assert result["map_features"][0]["source_row_id"] == "obs-1"
    assert result["integrated_table"]["present"] is True
    assert "inventory_observation__selected_korean_name" in result["csv_text"]
    assert result["source_to_final_key"]["name"]


def test_canonical_ingest_rejects_unknown_source_kind_before_file_access():
    result = canonical_reference.ingest_canonical_workbook(
        "/does/not/exist.xlsx", source_kind="legacy_csv"
    )
    assert result["success"] is False
    assert result["error_code"] == "invalid_source_kind"
    assert "bundled_candidate" in result["error_message"]
    assert "user_upload" in result["error_message"]


def _run_node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute generated QML JavaScript")
    result = subprocess.run(
        [node, "-e", script], check=True, capture_output=True, text=True, timeout=10
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("has_reference", [True, False])
def test_candidate_writes_editable_identity_fields_not_derived_values(has_reference):
    source = qml_plugin.render_identification_widget_qml(
        "''", taxonomy_reference_available=has_reference
    )
    start, end = qml_plugin._js_function_span(source, 0, "qpbSelectCandidate")
    result = _run_node("""
var qpbCandidateSelectionEnabled=true, qpbWriteBackMode='', qpbLastModelVersion='fixture';
var qpbStatusLabel={}, qpbManualEntryPanel={}, written=null, persisted=null;
var qpbCandidatesModel=[{scientific_name:'Fixture species',score:0.8,probability_value:0.2,
    ktsn_match:{selected_korean_name:'가상풀',selected_scientific_name:'Fixture species',
        selected_ktsn:'K1'}}];
function qpbPersistIdentification(){persisted=Array.from(arguments);return true;}
function qpbApplyCurrentFormWriteBack(fields){written=fields;return true;}
function qpbWriteAttributeWriteBackRequest(){throw new Error('Unexpected queued write');}
""" + source[start:end] + """
qpbSelectCandidate(0);
process.stdout.write(JSON.stringify({written:written,persisted:persisted,mode:qpbWriteBackMode}));
""")
    assert result["written"]["selected_korean_name"] == "가상풀"
    assert ("selected_scientific_name" in result["written"]) == (not has_reference)
    if not has_reference:
        assert result["written"]["selected_scientific_name"] == "Fixture species"
    assert "selected_ktsn" not in result["written"]
    assert result["written"]["identification_score"] == 0.8
    assert result["persisted"][:3] == ["Fixture species", "가상풀", "K1"]
    assert result["mode"] == "candidate"


def test_manual_pending_write_back_does_not_search_existing_forms_or_popups():
    project_source = qml_plugin.render_project_plugin_qml(
        "candidate-writeback", identification_enabled=True
    )
    start, end = qml_plugin._js_function_span(project_source, 0, "qpbApplyPendingWriteBack")
    result = _run_node("""
var searched=[], qpbWriteBackSearch={};
var iface={findItemByObjectName:function(name){return name==='featureForm'?{name:'existing'}:null;},
    mainWindow:function(){return {contentItem:{children:[{name:'popup'}]}};}};
function qpbBeginWriteBackSearch(){}
function qpbTraceWriteBack(){}
function qpbFindActiveRelationModel(root){searched.push(root.name);return null;}
""" + project_source[start:end] + """
var request={uuid:'test',uuid_field:'observation_id',fields:{selected_korean_name:'가상풀'},
    write_back_mode:'manual'};
var manual=qpbApplyPendingWriteBack(request), manualSearch=searched.slice();
searched=[];request.write_back_mode='candidate';
var candidate=qpbApplyPendingWriteBack(request);
process.stdout.write(JSON.stringify({manual:manual,manualSearch:manualSearch,candidate:candidate,candidateSearch:searched}));
""")
    assert result == {"manual": False, "manualSearch": [], "candidate": False,
                      "candidateSearch": ["existing", "popup"]}


def test_release_packaging_entry_points_do_not_require_private_workbooks():
    script = open("packaging/build_macos_app.sh", encoding="utf-8").read()
    bundle_source = open("qfield_builder/reference_bundle.py", encoding="utf-8").read()
    assert "Rpt_2026-08-29_List.xlsx" not in script
    assert "packaging/build_app.py" in script
    release_body = bundle_source.split("def prepare_filtered_reference_bundle", 1)[1].split(
        "def _extract_ktsn_lookup_csv", 1
    )[0]
    assert "CANONICAL_WORKBOOK_RELATIVE_SUBPATH" in release_body
    assert "tb_leco_nib_ktsn_dtl_gat.csv" not in release_body
    assert "2025년 국가생물종목록_v1.0.xlsx" not in release_body
