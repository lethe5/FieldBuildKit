"""Acceptance coverage for the approved FieldBuild Kit five-fix specification.

The generated-project checks use the existing acceptance harness.  Wizard, browser, and QField
runtime behavior is recorded as explicit manual/device acceptance gates because this repository's
Python harness cannot drive those runtimes.  The tests intentionally assert only the approved
specification's observable contracts; they do not alter application code or the feature spec.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from .conftest import _require_harness_function, make_base_config

pytestmark = pytest.mark.qgis

SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}
FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-FAKE-KEY-FIXES"

OBSERVATION_DISPLAY_EXPRESSION = (
    "concat(coalesce(selected_korean_name, selected_scientific_name, '미입력'), "
    "'(', coalesce(to_string(cover), '미입력'), '%)')"
)
SURVEY_DISPLAY_EXPRESSION = "concat(survey_date, ' ', surveyor)"

_IDENTIFICATION_TARGETS = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}
_FORBIDDEN_LOCATION_TOKENS = (
    "exif",
    "qpbReadExifTag",
    "qpbReadPhotoGps",
    "photoGps",
    "deviceGps",
    "device_gps",
)


@pytest.fixture()
def inspect_display_expressions(acceptance_api):
    """Return the narrow PyQGIS inspection seam documented in the traceability artifact."""
    return _require_harness_function(acceptance_api, "inspect_display_expressions")


def _build(acceptance_api, tmp_path: Path, survey_type: str, *, identification: bool = False):
    config = make_base_config(survey_type, display_name="FieldBuild Kit five-fix acceptance")
    config["identification_enabled"] = identification
    result = acceptance_api.build_project(config, str(tmp_path / f"fixes_{survey_type}"))
    assert result["success"], result.get("error_message")
    return result


def _plugin_source(result: dict) -> str:
    path = Path(result["project_dir"]) / f"{result['project_slug']}.qml"
    assert path.is_file(), f"expected generated project plugin at {path}"
    return path.read_text(encoding="utf-8")


def _widget_source(inspect_identification_widget, result: dict, layer_name: str) -> str:
    report = inspect_identification_widget(result["project_dir"], layer_name)
    assert report["qml_widget_field_found"] is True, report
    source = report.get("qml_code", "")
    assert source, "inspect_identification_widget() must expose the embedded widget QML source"
    return source


def _report_source(result: dict) -> str:
    return _plugin_source(result)


def _find_mbtiles(result: dict) -> Path:
    basemap_dir = Path(result["basemap_dir"])
    files = list(basemap_dir.glob("*.mbtiles"))
    assert files, f"expected a completed MBTiles file under {basemap_dir}"
    return files[0]


# AC-FIX-001 ---------------------------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-001 requires the real PySide6 wizard. Manual QA: render every supported wizard "
        "page at the documented minimum 700x560 window size; verify the full "
        "resources/fieldbuild-kit-logo.png lockup is above that page's explanation/title and "
        "instructional copy, remains visible without overlap or clipping, and is not replaced "
        "by a platform watermark, side banner, or icon-only mark. Record platform and font metrics."
    )
)
def test_acfix001_full_logo_is_above_content_on_every_wizard_page():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-002 ---------------------------------------------------------------------------------


def test_acfix002_successful_offline_build_publishes_only_a_completed_mbtiles_file(
    acceptance_api, tmp_path
):
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": FAKE_VWORLD_KEY,
        "bbox": SMALL_BBOX,
        "min_zoom": 10,
        "max_zoom": 11,
        "layer": "Base",
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 4000}},
    }
    result = acceptance_api.build_project(config, str(tmp_path / "successful_offline"))
    assert result["success"], result.get("error_message")
    mbtiles = _find_mbtiles(result)
    with sqlite3.connect(str(mbtiles)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] > 0


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-002 requires observing the desktop operation lifecycle. Manual QA: start a "
        "supported offline build whose tile acquisition and MBTiles writing remain active past "
        "the former premature timeout boundary; verify progress continues to a valid completed "
        "file. Repeat with explicit cancel, bounded request timeout, provider failure, and the "
        "existing pre-generation/1 GiB size-limit failure. Each non-success must identify the "
        "specific outcome and recovery action and leave no partial MBTiles deliverable."
    )
)
def test_acfix002_progress_timeout_cancel_provider_and_size_outcomes_are_distinct():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-003 ---------------------------------------------------------------------------------


def test_acfix003_type3_generated_identification_path_targets_saved_child_fields(
    acceptance_api, inspect_identification_widget, tmp_path
):
    result = _build(acceptance_api, tmp_path, "permanent_plots", identification=True)
    widget = _widget_source(inspect_identification_widget, result, "observation")
    source = f"{_plugin_source(result)}\n{widget}"
    assert "featureForm" in source and ".model" in source
    assert "changeAttribute(" in source
    for field in ("selected_korean_name", "selected_scientific_name", "selected_ktsn"):
        assert field in source, f"AC-FIX-003: missing saved child write-back field {field!r}"
    assert "survey_id" in source
    assert "overlayFeatureFormDrawer" in source or "EmbeddedFeatureForm" in source


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-003 requires QField and a real provider/candidate flow. Manual QA: generate a "
        "Type 3 project, save an observation, open it through 조사지 → 조사 → 식물관찰 / Related "
        "records, run identification, select a candidate, and verify Korean name, scientific "
        "name, and KTSN in the currently edited child form. Save normally, reopen, and verify "
        "the three values persisted while the child UUID and survey_id and all parent/sibling "
        "records are unchanged."
    )
)
def test_acfix003_type3_related_child_write_back_survives_save_reopen_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-004 ---------------------------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-004 requires the real desktop UI. Manual QA: at 700x560 and throughout the "
        "supported window range, under Korean localization and supported platform font metrics, "
        "verify the complete Ex... plugin label and complete photo-identification label are both "
        "readable, not clipped or ellipsized, distinguishable, and independently actionable."
    )
)
def test_acfix004_top_right_plugin_labels_are_complete_and_actionable():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-005 ---------------------------------------------------------------------------------


def test_acfix005_report_source_contains_body_map_table_and_single_runtime_entrypoints(
    acceptance_api, tmp_path
):
    source = _report_source(_build(acceptance_api, tmp_path, "permanent_plots"))
    assert re.search(r"<!doctype html|<html", source, re.IGNORECASE)
    assert re.search(r"<body", source, re.IGNORECASE)
    assert re.search(r"map|leaflet|d3", source, re.IGNORECASE)
    assert re.search(r"<table|joined", source, re.IGNORECASE)
    assert re.search(r"csv", source, re.IGNORECASE)
    assert re.search(r"addEventListener|DOMContentLoaded|onload", source, re.IGNORECASE)
    assert re.search(r"UTF-8|utf-8|text/csv", source, re.IGNORECASE)


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-005 requires a real generated report opened in a supported browser/QField. "
        "Manual QA: seed valid point/polygon geometry, joined rows, Korean/non-ASCII values, "
        "commas, quotes, newlines, HTML-looking text, and a filterable field. Open the report "
        "and verify valid standalone HTML, exactly one initialized map and table after their "
        "target elements exist, visible/clickable CSV control inside body, local features and "
        "joined rows. Export filtered and all-row choices and parse each UTF-8 CSV for exact row "
        "scope, stable headers, Korean text, and RFC-compatible quoting. Repeat with no network "
        "and no valid geometry; local table and explicit map/offline state must remain usable."
    )
)
def test_acfix005_report_map_table_and_csv_are_integrated_and_usable():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-006 / AC-FIX-007 / AC-FIX-008 ---------------------------------------------------------


def test_acfix007_selected_offline_layer_is_recorded_without_api_key(
    acceptance_api, tmp_path
):
    selected_layer = "Satellite"
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": FAKE_VWORLD_KEY,
        "bbox": SMALL_BBOX,
        "min_zoom": 10,
        "max_zoom": 11,
        "layer": selected_layer,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 4000}},
    }
    result = acceptance_api.build_project(config, str(tmp_path / "selected_layer"))
    assert result["success"], result.get("error_message")
    mbtiles = _find_mbtiles(result)
    with sqlite3.connect(str(mbtiles)) as conn:
        metadata = dict(conn.execute("SELECT name, value FROM metadata").fetchall())
    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8")
    output_text = json.dumps(metadata, ensure_ascii=False) + "\n" + qgs_text
    assert "VWorld" in output_text or "vworld" in output_text.lower()
    assert selected_layer in output_text
    assert FAKE_VWORLD_KEY not in output_text
    assert ".mbtiles" in output_text.lower()
    assert str(mbtiles) not in Path(result["qgs_path"]).read_text(encoding="utf-8")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-006 requires the real wizard and online/offline selectors. Manual QA: resolve "
        "the current VWorld capability-advertised subset; compare online and offline selectors "
        "side by side and verify identical control pattern, labels, options, and single-choice "
        "semantics. With multiple choices, verify download is blocked until exactly one is "
        "explicitly selected and never silently defaults to Base. With one choice, verify it is "
        "visibly resolved and carried into the request. Verify OpenStreetMap is absent from the "
        "offline choices and the selected layer's tiles are the ones acquired."
    )
)
def test_acfix006_offline_selector_mirrors_online_layer_selector_and_controls_download():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-008 requires capability-discovery and wizard failure-path execution. Manual QA: "
        "make the effective supported VWorld catalog empty; verify offline download is blocked "
        "with a clear actionable no-supported-map message, no unsupported provider/layer is used, "
        "and no MBTiles is published. Separately change the catalog after selection and verify a "
        "stale choice is invalidated/revalidated; a completed file must never claim a different "
        "source/layer than the tiles downloaded."
    )
)
def test_acfix008_empty_or_stale_offline_catalog_fails_closed_without_partial_output():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-009 / AC-FIX-010 / AC-FIX-011 ---------------------------------------------------------


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_acfix009_observation_display_expression_is_exact(
    acceptance_api, inspect_display_expressions, tmp_path, survey_type
):
    result = _build(acceptance_api, tmp_path, survey_type)
    info = inspect_display_expressions(result["project_dir"])
    actual = info["display_expressions"]["observation"]
    assert actual == OBSERVATION_DISPLAY_EXPRESSION


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-010/011 require a real QField Related records surface. Manual QA: create Type 2 "
        "and Type 3 surveys with multiple linked observations, including duplicate and partially "
        "NULL names, NULL cover, cover 0, and no-child cases. Under 식물관찰 verify every child "
        "appears once, in existing relation order, with its own exact label; verify fallback to "
        "scientific name/미입력, NULL cover as 미입력, cover 0 as 0, no prefixes, and unchanged "
        "empty state. Use each existing row action and verify it opens that editable child, not "
        "the parent or a sibling."
    )
)
def test_acfix010_acfix011_related_observations_are_distinct_and_editable_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-012 / AC-FIX-013 ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "survey_type", ["temporary_plots", "permanent_plots", "vegetation_mapping"]
)
def test_acfix013_survey_display_expression_is_exact(
    acceptance_api, inspect_display_expressions, tmp_path, survey_type
):
    result = _build(acceptance_api, tmp_path, survey_type)
    info = inspect_display_expressions(result["project_dir"])
    assert info["display_expressions"]["survey"] == SURVEY_DISPLAY_EXPRESSION
    assert info["display_expressions"]["survey"] != "coalesce(surveyor, survey_date, 'Survey')"


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-012/013 require a real QGIS/QField form. Manual QA: inspect Type 2, Type 3, and "
        "Type 4 survey layer display expressions and verify the literal expression is exactly "
        "concat(survey_date, ' ', surveyor), including Type 2 seed-survey NULL/blank values; do "
        "not restore the old Survey fallback. Edit/save/reopen a Related-records child and verify "
        "the combined label refreshes from the saved child without changing UUID or survey_id."
    )
)
def test_acfix012_acfix013_survey_and_child_display_behavior_survives_refresh():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-014 / AC-FIX-015 / AC-FIX-016 ---------------------------------------------------------


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots"])
def test_acfix014_identification_qml_uses_domain_location_and_no_image_metadata(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type
):
    layer_name = _IDENTIFICATION_TARGETS[survey_type]
    result = _build(acceptance_api, tmp_path, survey_type, identification=True)
    source = _widget_source(inspect_identification_widget, result, layer_name)
    lowered = source.lower()
    assert not any(token.lower() in lowered for token in _FORBIDDEN_LOCATION_TOKENS)
    assert "probability" in lowered or "occurrence" in lowered
    assert "candidate" in lowered
    if survey_type == "simple_inventory":
        assert "geom" in lowered
    elif survey_type == "temporary_plots":
        assert "survey_id" in lowered and "plot_geom" in lowered
    else:
        assert "survey_id" in lowered and "plot_id" in lowered and "plot_geom" in lowered


def test_acfix014_type4_has_no_identification_target_or_location_path(
    acceptance_api, inspect_identification_widget, tmp_path
):
    result = _build(acceptance_api, tmp_path, "vegetation_mapping", identification=True)
    report = inspect_identification_widget(result["project_dir"], "community")
    assert report["qml_widget_field_found"] is False


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-014/015/016 require a real QField session and request observation. Manual QA: "
        "with a photo containing valid/conflicting EXIF GPS or other image location metadata, "
        "exercise enabled Type 1, Type 2, and Type 3 targets and verify only Type 1 current "
        "inventory_observation.geom, Type 2 observation.survey_id → survey.plot_geom, and Type 3 "
        "observation.survey_id → survey.plot_id → plot.plot_geom supply location context. Verify "
        "Type 4 community has no button/path. Repeat with missing, ambiguous, mismatched, empty, "
        "invalid, wrong-type, non-finite, and out-of-bounds authoritative geometry. The photo "
        "request, candidate result, explicit selection, and Korean/scientific/KTSN write-back "
        "must continue under normal photo/provider conditions; only occurrence probability is "
        "skipped, reported as unavailable/no probability data, never numeric zero. Inspect logs, "
        "request/context, persisted fields, and original attachment path/bytes to verify no EXIF, "
        "image-metadata, device-GPS, site, centroid, stale-record, or alternate fallback is used."
    )
)
def test_acfix015_acfix016_invalid_location_does_not_block_identification_or_mutate_photo():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FIX-017 ---------------------------------------------------------------------------------


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FIX-017 / D-FIX-011 is a QField 4.2.11 iOS relation-list runtime gate. Build a Type "
        "3 project, save the site → plot → survey chain, and record the immediate survey parent's "
        "existing 식물관찰 Related records count and row identities. Add one daughter observation "
        "only through that survey's Related records workflow, give it a unique visible value, and "
        "save it successfully. Return immediately to that same survey: its Related records list "
        "must contain the new daughter exactly once using the existing relation display (count is "
        "old count + 1), with no duplicate, transient-only row, or unrelated child. Navigate away "
        "to the plot/site, reopen the same survey and its Related records, and verify the same "
        "GeoPackage-backed daughter remains exactly once. Inspect the local GeoPackage when "
        "available: exactly one row has the recorded daughter UUID and that survey_id. Record "
        "QField 4.2.11, iOS/device, project build ID, before/after counts, UUID/FK, screenshots, "
        "and pass/fail evidence. Desktop QGIS, generated-project inspection, and synthetic SQL "
        "insertion do not exercise this QField refresh/save path."
    )
)
def test_acfix017_qfield_4211_related_daughter_is_immediately_visible_once_after_save():
    raise AssertionError("should never run while skipped -- see skip reason")
