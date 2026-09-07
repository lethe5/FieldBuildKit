"""Acceptance coverage for the approved FieldBuild Standalone follow-up defect corrections.

The tests in this file use only the existing acceptance API and shared fixtures.  The Python
harness can exercise deterministic offline builds and generated-artifact structure, but it does
not run QField or a QML engine.  Runtime/device boundaries are therefore explicit skipped gates;
they are not converted into weaker black-box assertions.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from .conftest import (
    OFFLINE_PREGENERATION_THRESHOLD_BYTES,
    make_base_config,
)

pytestmark = pytest.mark.qgis

FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-FAKE-KEY-FOLLOWUP"
FAKE_PLANTNET_KEY = "ACCEPTANCE-TEST-FAKE-PLANTNET-KEY-FOLLOWUP"
SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}
HUGE_BBOX = {"min_lon": 126.0, "min_lat": 33.0, "max_lon": 130.0, "max_lat": 39.0}

_PHOTO_PATH_FIELDS = ("leaf_photo_path", "flower_photo_path", "fruit_photo_path")
_PHOTO_PATHS_EXPRESSION_RE = re.compile(r'expression\.evaluate\("(.*?)"\)')


def _offline_config(
    *,
    bbox: dict,
    min_zoom: int = 10,
    max_zoom: int = 11,
    layer: str | None = "Base",
    tile_source: dict | str = None,
    key: str | None = FAKE_VWORLD_KEY,
) -> dict:
    config = make_base_config("simple_inventory")
    basemap = {
        "mode": "offline",
        "bbox": bbox,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "tile_source": tile_source or {"fake": {"mode": "success", "tile_bytes": 4000}},
    }
    if key is not None:
        basemap["vworld_api_key"] = key
    if layer is not None:
        basemap["layer"] = layer
    config["basemap"] = basemap
    return config


def _mbtiles_path(result: dict) -> Path:
    basemap_dir = Path(result["basemap_dir"])
    files = list(basemap_dir.glob("*.mbtiles"))
    assert len(files) == 1, f"expected one completed MBTiles file under {basemap_dir}, got {files}"
    return files[0]


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


def _photo_paths_expression(qml_code: str) -> str:
    match = _PHOTO_PATHS_EXPRESSION_RE.search(qml_code)
    assert match, "expected a literal expression.evaluate(\"...\") photo-path expression"
    return match.group(1)


# AC-FOLLOWUP-001 -----------------------------------------------------------------------------


def test_ac_followup_001_progressing_offline_build_completes_with_bounded_cleanup_contract(
    acceptance_api, tmp_path
):
    """The existing fake source provides a bounded forward-progress seam.

    This deliberately does not wait for, or sleep through, the former 12-hour ceiling.  It
    verifies that a progressing request can complete through the existing build seam and publish
    one finished deliverable without temporary/partial MBTiles artifacts.  The elapsed-time
    boundary itself remains the explicit manual/device gate below.
    """
    config = _offline_config(bbox=SMALL_BBOX, tile_source={"fake": {"mode": "success", "tile_bytes": 4000}})
    result = acceptance_api.build_project(config, str(tmp_path / "progressing"))

    assert result["success"], result.get("error_message")
    assert result["cancelled"] is False
    mbtiles = _mbtiles_path(result)
    assert mbtiles.stat().st_size > 0
    assert not list(Path(result["basemap_dir"]).glob("*.part"))
    assert not list(Path(result["basemap_dir"]).glob("*.tmp"))


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FOLLOWUP-001's elapsed-time liveness boundary is not executable in this Python/QGIS "
        "harness without waiting 12 hours. Use the implementation's bounded time-scaled/fake-"
        "clock lifecycle seam (never real wall-clock waiting) to keep a tile/MBTiles operation "
        "reporting forward progress beyond the former fixed ceiling; verify it completes and "
        "publishes valid MBTiles. Repeat with bounded per-request timeout, explicit cancellation, "
        "provider failure, and >900 MiB size failure; every non-success must report its distinct "
        "outcome and leave no partial deliverable. Record that this is separate from the automated "
        "fake-progress smoke above."
    )
)
def test_ac_followup_001_progress_beyond_former_12h_ceiling_and_failure_outcomes_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FOLLOWUP-002 -----------------------------------------------------------------------------


def test_ac_followup_002_qml_direct_write_targets_only_active_child_korean_name(
    acceptance_api, inspect_identification_widget, inspect_editor_widget, tmp_path
):
    """Structural proxy: QML directly changes only Korean name; QGIS derives the other fields."""
    config = make_base_config("permanent_plots", display_name="후속 저장 관찰 테스트")
    config["identification_enabled"] = True
    result = acceptance_api.build_project(config, str(tmp_path / "writeback"))
    assert result["success"], result.get("error_message")

    plugin = _plugin_source(result)
    widget = _widget_source(inspect_identification_widget, result, "observation")
    combined = f"{plugin}\n{widget}"

    assert "featureForm" in plugin and ".model" in plugin
    assert "EmbeddedFeatureForm" in plugin or "embeddedFeatureForm" in plugin
    assert re.search(r"uuid", plugin, re.IGNORECASE)
    assert "survey_id" in combined

    selected_field_calls = re.findall(
        r"changeAttribute\s*\(\s*['\"](selected_[a-z_]+)['\"]", combined
    )
    assert "selected_korean_name" in selected_field_calls, (
        "AC-FOLLOWUP-002: the active child write-back must directly change selected_korean_name"
    )
    assert set(selected_field_calls) == {"selected_korean_name"}, (
        "AC-FOLLOWUP-002/C-FOLLOWUP-003: QML must not directly change derived scientific/KTSN "
        f"fields; selected-field changeAttribute calls were {selected_field_calls!r}"
    )
    assert re.search(
        r"(?:attributeValue|getAttribute|readAttribute|currentFeature|model\s*\.)[^\n]{0,160}"
        r"selected_korean_name|selected_korean_name[^\n]{0,160}"
        r"(?:attributeValue|getAttribute|readAttribute|currentFeature|model\s*\.)",
        combined,
        re.IGNORECASE,
    ), "AC-FOLLOWUP-002: QML must read back the resulting selected_korean_name value"

    for field_name in ("selected_scientific_name", "selected_ktsn"):
        info = inspect_editor_widget(result["project_dir"], "observation", field_name)
        assert info["default_value_expression"], (field_name, info)
        assert "selected_korean_name" in info["default_value_expression"]
        assert info["apply_on_update"] is True
        assert info["is_read_only"] is True


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FOLLOWUP-002's normal QField flow is runtime/device-only here. Generate a Type 3 "
        "project, save a child observation, open it through 조사지 → 조사 → 식물관찰, select a "
        "candidate, and confirm the active child model accepts and reads back only the selected "
        "Korean name through changeAttribute. Save normally and reopen; verify QGIS derives the "
        "scientific name/KTSN, while child UUID/survey_id, parent, and siblings remain unchanged. "
        "Do not assert separate direct changeAttribute calls for the derived fields. Record QField "
        "version/platform."
    )
)
def test_ac_followup_002_type3_child_writeback_and_save_reopen_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FOLLOWUP-003 -----------------------------------------------------------------------------


def test_ac_followup_003_explicit_supported_layer_reaches_existing_offline_scenarios(
    acceptance_api, tmp_path
):
    """The existing deterministic success/metadata seam now carries an explicit layer."""
    config = _offline_config(
        bbox=SMALL_BBOX,
        layer="Satellite",
        tile_source={"fake": {"mode": "success", "tile_bytes": 4000}},
    )
    result = acceptance_api.build_project(config, str(tmp_path / "selected-layer"))
    assert result["success"], result.get("error_message")

    mbtiles = _mbtiles_path(result)
    with sqlite3.connect(str(mbtiles)) as conn:
        metadata = dict(conn.execute("SELECT name, value FROM metadata").fetchall())
    output = "\n".join(str(value) for value in metadata.values())
    assert "Satellite" in output
    assert "VWorld" in output or "vworld" in output.lower()


def test_ac_followup_003_missing_selected_layer_fails_with_existing_selection_error(
    acceptance_api, tmp_path
):
    config = _offline_config(
        bbox=SMALL_BBOX,
        layer=None,
        tile_source={"fake": {"mode": "success", "tile_bytes": 4000}},
    )
    result = acceptance_api.build_project(config, str(tmp_path / "missing-layer"))
    assert result["success"] is False
    assert result.get("error_code") == "offline_layer_unavailable"
    assert not Path(tmp_path / "missing-layer").exists()


# AC-FOLLOWUP-004 -----------------------------------------------------------------------------


def test_ac_followup_004_size_guard_precedes_fake_tile_fetch_for_valid_selected_layer(
    acceptance_api, tmp_path
):
    """A fake provider failure is a negative control for size-before-fetch ordering."""
    config = _offline_config(
        bbox=HUGE_BBOX,
        min_zoom=1,
        max_zoom=18,
        layer="Base",
        tile_source={"fake": {"mode": "quota_error", "tile_bytes": 20_000}},
    )
    result = acceptance_api.build_project(config, str(tmp_path / "oversized"))
    assert result["success"] is False
    assert result.get("error_code") == "offline_size_exceeded" or "size" in (
        result.get("error_code") or ""
    ).lower()
    assert result.get("error_code") not in {"offline_layer_unavailable", "provider_quota"}
    assert not Path(tmp_path / "oversized").exists()


def test_ac_followup_004_within_threshold_selected_layer_reaches_tile_source(
    acceptance_api, tmp_path
):
    estimate_config = _offline_config(
        bbox=SMALL_BBOX,
        min_zoom=10,
        max_zoom=11,
        layer="Base",
        tile_source={"fake": {"mode": "success", "tile_bytes": 4000}},
    )
    result = acceptance_api.build_project(estimate_config, str(tmp_path / "within-threshold"))
    assert result["success"], result.get("error_message")
    assert _mbtiles_path(result).stat().st_size > 0


# AC-FOLLOWUP-005 / AC-FOLLOWUP-006 ------------------------------------------------------------


@pytest.mark.parametrize("consent", [False, True], ids=["embedding-declined", "embedding-accepted"])
def test_ac_followup_005_type1_identify_is_direct_manual_only_and_separate_from_key_embedding_consent(
    acceptance_api, inspect_identification_widget, tmp_path, consent
):
    """D-93: Type 1 joins Type 2/3 on the direct, explicit-Identify path."""
    config = make_base_config("simple_inventory", display_name="D-93 Type 1 직접 동정 테스트")
    config["identification_enabled"] = True
    config["plantnet"] = {
        "api_key": FAKE_PLANTNET_KEY,
        "consent_accepted": consent,
        "remember_key": False,
    }
    result = acceptance_api.build_project(config, str(tmp_path / f"d93-type1-{consent}"))
    assert result["success"], result.get("error_message")
    source = _widget_source(inspect_identification_widget, result, "inventory_observation")

    button = re.search(r"\bid\s*:\s*qpbIdentifyButton\b[\s\S]{0,500}", source)
    assert button, "AC-FOLLOWUP-005/D-93: expected the generated Type 1 Identify button"
    assert 'text: "사진으로 동정하기"' in button.group(0)
    clicked = source.find("onClicked:", button.start())
    assert clicked >= 0, "AC-FOLLOWUP-005/D-93: expected an Identify-button click handler"
    handler_end = source.find("\n        }", clicked)
    assert handler_end >= 0, "could not delimit the generated Type 1 click handler"
    handler = source[clicked:handler_end]

    assert re.search(r"\bqpbRunIdentification\s*\(\s*\)", handler), (
        "AC-FOLLOWUP-005/FR-QPB-101 (D-93): Type 1 Identify must start identification directly"
    )
    assert "qpbConsentDialog" not in source
    assert not re.search(r"\bDialog\s*\{", source), (
        "AC-FOLLOWUP-005/D-93: Type 1 must not author a consent/OK dialog"
    )
    assert not re.search(r"\b(open|show)\s*\(", handler), (
        "AC-FOLLOWUP-005/D-93: Type 1 Identify must not open an intermediate dialog"
    )

    declaration = re.search(r"\bfunction\s+qpbRunIdentification\s*\(", source)
    calls = []
    for call in re.finditer(r"\bqpbRunIdentification\s*\(", source):
        if declaration and call.start() == declaration.end() - len(call.group(0)):
            continue
        calls.append(call)
    assert len(calls) == 1, (
        "AC-FOLLOWUP-005/FR-QPB-102: attachment alone must not trigger identification; the "
        f"explicit Type 1 Identify button must be the only runtime call, found {len(calls)}"
    )

    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8")
    if consent:
        assert FAKE_PLANTNET_KEY in qgs_text
    else:
        assert FAKE_PLANTNET_KEY not in qgs_text


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FOLLOWUP-005/D-93 requires real QField verification. Attach a photo and confirm that "
        "attachment alone does not start identification; click 사진으로 동정하기 and confirm the "
        "request starts without an application-owned consent/confirmation/OK gate. Repeat with "
        "desktop Pl@ntNet-key embedding consent accepted and declined: the field-button behavior "
        "must remain direct, while only the accepted project embeds the key and the declined path "
        "retains manual key entry. Platform-owned permission prompts are outside this check."
    )
)
def test_ac_followup_005_type1_direct_identification_and_key_consent_boundary_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-FOLLOWUP-006/O-FOLLOWUP-001 is intentionally unresolved. Re-run the existing D-91 "
        "offline visibility evidence test for the generated layer tree, but classify any failure "
        "only after stakeholder approval resolves whether D-91 is authoritative for this scope. "
        "Do not claim this follow-up fixes, excludes, or changes offline visibility semantics."
    )
)
def test_ac_followup_006_d91_offline_visibility_remains_open_classification():
    raise AssertionError("should never run while skipped -- see skip reason")


# AC-FOLLOWUP-007 -----------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac_followup_007_type23_photo_expression_matches_strict_type1_inline_shape(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type
):
    def build(survey: str, label: str) -> dict:
        config = make_base_config(survey, display_name="후속 inline photo expression")
        config["identification_enabled"] = True
        result = acceptance_api.build_project(config, str(tmp_path / label))
        assert result["success"], result.get("error_message")
        return result

    type1 = build("simple_inventory", f"type1-{survey_type}")
    type23 = build(survey_type, f"type23-{survey_type}")
    type1_expr = _photo_paths_expression(
        _widget_source(inspect_identification_widget, type1, "inventory_observation")
    )
    type23_expr = _photo_paths_expression(
        _widget_source(inspect_identification_widget, type23, "observation")
    )

    assert "relation_aggregate" not in type23_expr
    assert "rel_observation_photo_observation" not in type23_expr
    for field in _PHOTO_PATH_FIELDS:
        assert field in type23_expr

    def normalize(expr: str) -> str:
        for index, field in enumerate(_PHOTO_PATH_FIELDS):
            expr = expr.replace(field, f"__PHOTO_FIELD_{index}__")
        return expr

    assert normalize(type23_expr) == normalize(type1_expr), (
        "AC-FOLLOWUP-007/AC-QPB-113: Type 2/3 must retain the strict Type 1 inline expression "
        f"shape; type1={type1_expr!r}, type23={type23_expr!r}"
    )


# AC-FOLLOWUP-008 / AC-FOLLOWUP-009 ------------------------------------------------------------


@pytest.mark.parametrize("key", [None, "", "   "])
def test_ac_followup_008_missing_or_blank_key_fails_before_size_or_fake_download(
    acceptance_api, tmp_path, key
):
    config = _offline_config(
        bbox=HUGE_BBOX,
        min_zoom=1,
        max_zoom=18,
        layer="Base",
        key=key,
        tile_source={"fake": {"mode": "success", "tile_bytes": 20_000}},
    )
    config["_test_cancel_after_phase"] = "basemap_download"
    result = acceptance_api.build_project(config, str(tmp_path / f"missing-key-{key!r}"))

    assert result["success"] is False
    assert result["cancelled"] is False
    assert result.get("error_code") != "offline_size_exceeded"
    message = (result.get("error_message") or "").strip()
    assert message
    assert "'vworld_api_key'" not in message
    assert not any(term in message.lower() for term in ("keyerror", "traceback", "exception"))


def test_ac_followup_009_successful_offline_outputs_contain_no_vworld_key_anywhere(
    acceptance_api, tmp_path
):
    config = _offline_config(
        bbox=SMALL_BBOX,
        layer="Hybrid",
        tile_source={"fake": {"mode": "success", "tile_bytes": 4000}},
    )
    result = acceptance_api.build_project(config, str(tmp_path / "secret-free"))
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    assert (project_dir / "MANIFEST.json").is_file()
    assert (project_dir / "VALIDATION_REPORT.json").is_file()
    mbtiles = _mbtiles_path(result)
    with sqlite3.connect(str(mbtiles)) as conn:
        metadata_text = repr(dict(conn.execute("SELECT name, value FROM metadata").fetchall()))
    assert FAKE_VWORLD_KEY not in metadata_text

    # The generated project directory is the self-contained mobile transfer folder in the
    # existing contract. Scan every emitted file, including the named manifest/report/qgs/MBTiles.
    for path in project_dir.rglob("*"):
        if path.is_file():
            assert FAKE_VWORLD_KEY.encode() not in path.read_bytes(), f"key found in {path}"
