"""Regression tests for the final canonical/report/write-back review findings."""

from __future__ import annotations

from unittest.mock import patch

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


def test_candidate_write_back_preserves_three_identity_values_but_manual_path_is_compatible():
    source = qml_plugin.render_identification_widget_qml("''")
    candidate = source[
        source.index("function qpbSelectCandidate(index) {") : source.index(
            "function qpbConfirmManualEntry", source.index("function qpbSelectCandidate(index) {")
        )
    ]
    assert "selected_korean_name: korean" in candidate
    assert "selected_scientific_name: selectedScientific" in candidate
    assert "selected_ktsn: selectedKtsn" in candidate
    project_source = qml_plugin.render_project_plugin_qml(
        "candidate-writeback", identification_enabled=True
    )
    apply_source = project_source[
        project_source.index("function qpbApplyPendingWriteBack(request)") : project_source.index(
            "function qpbFindMatchingFeatureModel", project_source.index("function qpbApplyPendingWriteBack(request)")
        )
    ]
    assert "if (!isCandidateSelection &&" in apply_source


def test_release_packaging_entry_points_name_only_the_canonical_workbook():
    script = open("packaging/build_macos_app.sh", encoding="utf-8").read()
    bundle_source = open("qfield_builder/reference_bundle.py", encoding="utf-8").read()
    assert "Rpt_2026-08-29_List.xlsx" in script
    release_body = bundle_source.split("def prepare_filtered_reference_bundle", 1)[1].split(
        "def _extract_ktsn_lookup_csv", 1
    )[0]
    assert "CANONICAL_WORKBOOK_RELATIVE_SUBPATH" in release_body
    assert "tb_leco_nib_ktsn_dtl_gat.csv" not in release_body
    assert "2025년 국가생물종목록_v1.0.xlsx" not in release_body
