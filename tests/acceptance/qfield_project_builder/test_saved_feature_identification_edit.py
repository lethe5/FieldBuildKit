"""D-92 — saved plant-observation identification edit write-back.

The Python acceptance harness can inspect generated QML/QGS artifacts, but it has no QField/QML
runtime and cannot open a saved feature, drive the Identify action, or perform a real QField save.
Accordingly, this module keeps the mechanically testable part honest (the generated plugin's
lookup, UUID/layer guards, active attribute-form model, and fail-closed shape) and records every
runtime/device assertion as an explicit skipped placeholder with concrete QA steps.

The existing-feature path is deliberately checked separately from the historical Add-feature
``overlayFeatureFormDrawer`` path.  A list model is never an acceptable write target.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config


def _build_identification_project(acceptance_api, tmp_path, survey_type: str):
    config = make_base_config(survey_type, display_name="저장 식물관찰 동정 편집 테스트")
    config["identification_enabled"] = True
    return acceptance_api.build_project(config, str(tmp_path / f"saved_edit_{survey_type}"))


def _plugin_source(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    plugin_path = project_dir / f"{result['project_slug']}.qml"
    assert plugin_path.is_file(), f"expected generated project plugin at {plugin_path}"
    return plugin_path.read_text(encoding="utf-8")


def _widget_source(inspect_identification_widget, result: dict, layer_name: str) -> str:
    report = inspect_identification_widget(result["project_dir"], layer_name)
    assert report["qml_widget_field_found"] is True, report
    source = report.get("qml_code", "")
    assert source, "inspect_identification_widget() must expose the embedded widget QML source"
    return source


def _request_layer_context_is_referenced(source: str) -> bool:
    """Accept sensible public names without prescribing an internal request schema."""
    return bool(
        re.search(
            r"request\s*(?:\.\s*(?:layer|layer_name|layerId|layerContext)|\[\s*['\"]layer)",
            source,
            re.IGNORECASE,
        )
    )


@pytest.mark.qgis
@pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)
def test_ac007_existing_feature_lookup_is_distinct_and_targets_active_attribute_form_model(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-SFE-007 / FR-SFE-008: generated code has a distinct existing-form lookup.

    This is intentionally a structural, necessary-not-sufficient check.  It requires the
    documented ``featureForm.model``/attribute-form model family, request UUID and layer context,
    all three selected fields, and the relation-form traversal vocabulary.  It rejects the
    documented-invalid feature-list model as a target and does not claim QField execution.
    """
    result = _build_identification_project(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")

    plugin = _plugin_source(result)
    widget = _widget_source(inspect_identification_widget, result, layer_name)
    combined = f"{plugin}\n{widget}"

    assert re.search(
        r"iface\.findItemByObjectName\(\s*['\"]featureForm['\"]\s*\)", plugin
    ), (
        "AC-SFE-007: existing saved-feature edits need an explicit featureForm host lookup; "
        "the Add-feature overlay path is not sufficient"
    )
    assert "overlayFeatureFormDrawer" in plugin, (
        "AC-SFE-007: keep the historical Add-feature path present as a distinct branch"
    )
    assert "featureForm" in plugin and ".model" in plugin, (
        "AC-SFE-007/FR-SFE-008: use the active FeatureForm.model (or equivalent active model)"
    )
    assert "embeddedFeatureForm" in plugin and "attributeFormModel" in plugin, (
        "AC-SFE-002/007: Type 3 relation edits must traverse the EmbeddedFeatureForm attribute "
        "model family"
    )
    assert re.search(r"uuid", plugin, re.IGNORECASE), (
        "AC-SFE-007: pending requests must be associated with a domain UUID"
    )
    assert _request_layer_context_is_referenced(plugin), (
        "FR-SFE-003/AC-SFE-007: the write target must be checked against request layer context, "
        "not UUID alone"
    )
    assert "changeAttribute(" in plugin, "AC-SFE-007: apply changes through the active model"
    for field in (
        "selected_korean_name",
        "selected_scientific_name",
        "selected_ktsn",
    ):
        assert field in combined, f"AC-SFE-001/007: generated QML must carry {field!r}"

    invalid_list_model_tokens = (
        "QfFeatureListForm.model",
        "QfMultiFeatureListModel",
        "featureListForm.model",
    )
    assert not any(token in plugin for token in invalid_list_model_tokens), (
        "AC-SFE-007/FR-SFE-008: a feature-list model is not an editable attribute-form target"
    )


@pytest.mark.qgis
def test_ac005_plugin_is_structurally_fail_closed_until_uuid_and_model_context_match(
    acceptance_api, tmp_path
):
    """AC-SFE-005: static guard checks for pending-request polling.

    The assertion that an actual QField poll retains a request across asynchronous mounting and
    eventually surfaces a diagnostic is covered by the manual placeholder below.  This automated
    portion verifies the source contains the non-negotiable fail-closed gates: missing model,
    missing/mismatched UUID, bounded/repeated polling, and no delete-based consumption.
    """
    result = _build_identification_project(acceptance_api, tmp_path, "permanent_plots")
    assert result["success"], result.get("error_message")
    source = _plugin_source(result)

    assert re.search(r"Timer\s*\{", source), "AC-SFE-005: pending requests must be polled"
    assert re.search(r"repeat\s*:\s*true", source), (
        "AC-SFE-005: polling must retry while a relation child form is still mounting"
    )
    assert re.search(r"if\s*\(!model\)\s*\{\s*return\s+false", source), (
        "AC-SFE-005: an unavailable active model must fail closed and remain retryable"
    )
    assert re.search(r"currentUuid", source) and re.search(
        r"request\.uuid", source
    ), "AC-SFE-005: compare the active model UUID with the pending request UUID"
    assert re.search(r"String\(currentUuid\).*String\(request\.uuid\)", source, re.DOTALL), (
        "AC-SFE-005: a UUID mismatch must reject the write"
    )
    assert "FileUtils.deleteFiles(" not in source, (
        "AC-SFE-005: a failed lookup must not consume a request through deleteFiles"
    )
    assert re.search(r"qpbApplyPendingWriteBack\(request\)\s*\)\s*\{?", source), (
        "AC-SFE-005: polling must gate request consumption on the apply result"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-001 requires a real QField session and cannot be driven by this Python harness. "
        "Manual QA: generate identification-enabled Type 1 (simple_inventory), Type 2 "
        "(temporary_plots), and Type 3 (permanent_plots) projects; create and save one valid "
        "observation of each type; reopen each saved feature directly from its observation layer; "
        "run Identify, select a displayed candidate, verify the open form shows selected Korean "
        "name/scientific name/KTSN, use normal QField Save, reopen, and record all three values "
        "from the GeoPackage-backed form. Record QField version/platform."
    )
)
def test_ac001_saved_type_1_2_and_3_direct_edit_round_trip_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-002 requires a real QField relation form. Manual QA: in a generated Type 3 "
        "project, save a site/survey/observation chain, record the observation UUID, survey_id, "
        "parent survey/site and sibling rows, then open the observation through 조사지 → 조사 → "
        "식물관찰. Select a candidate, save, reopen, and verify the three selected fields changed "
        "on the observation, UUID and survey_id are unchanged, and parent/sibling records are "
        "byte-for-byte equivalent except for intended observation candidate fields/metadata."
    )
)
def test_ac002_type_3_relation_path_preserves_uuid_fk_parent_and_siblings_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-003 requires a real saved-feature edit. Manual QA: create two saved observations "
        "in the same direct observation-layer view, record both UUIDs and all candidate metadata, "
        "edit only the first with Identify and save, then reopen both and inspect the GeoPackage. "
        "Verify no duplicate row exists, only the intended row's three selected fields and existing "
        "candidate metadata changed, and the second observation is unchanged."
    )
)
def test_ac003_direct_saved_edit_updates_only_intended_observation_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-004 requires selecting a real candidate in QField. Manual QA: use a candidate "
        "whose KTSN match is a synonym with a correct_list chain ending at a terminal 정명 row; "
        "select it once in a direct saved observation and once through the Type 3 relation path. "
        "After normal save/reopen, verify Korean name, standardized scientific name, and KTSN are "
        "from the terminal 정명 row, never the intermediate alias."
    )
)
def test_ac004_terminal_accepted_name_is_persisted_for_direct_and_relation_edits_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-005's asynchronous/runtime half cannot be exercised here. Manual QA: place a "
        "pending request while the relation child form is mounting and confirm polling retains it "
        "until the matching active attribute model appears; inject or arrange a UUID mismatch and "
        "an unavailable model, confirm no other feature/model changes and the request is not "
        "cleared, then confirm bounded expiry produces a clear non-success diagnostic. Capture "
        "QField version/platform and the diagnostic text/log."
    )
)
def test_ac005_unmounted_or_uuid_mismatched_model_is_fail_closed_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-006 is explicitly real-device QA. On the release-verification iOS/Android QField "
        "build, exercise AC-SFE-001 direct edits and AC-SFE-002 Type 3 relation edits with real "
        "candidate selections and normal save/reopen. Record exact QField version, platform, "
        "device/OS, project build identifier, and pass/fail evidence for both paths."
    )
)
def test_ac006_release_device_verification_record_for_direct_and_type3_paths():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-SFE-008 is a runtime/API-boundary verification gate. On the target QField build, "
        "inspect the public object graph reachable from iface.findItemByObjectName('featureForm') "
        "and iface.mainWindow() while an existing saved feature is open. If no active "
        "FeatureForm.model/QfAttributeFormModel can be reached and UUID-verified, record the "
        "concrete QField version/platform, object-graph evidence, and the required QField-side "
        "public accessor/write-back change. Confirm the plugin makes no false persistence claim, "
        "does not write a list/other feature, and does not silently clear the request."
    )
)
def test_ac008_unreachable_existing_attribute_model_is_reported_as_concrete_qfield_limitation():
    raise AssertionError("should never run while skipped -- see skip reason")
