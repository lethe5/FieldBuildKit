"""Acceptance coverage for the probability-raster generation timeout fix.

The tests are deliberately deterministic on macOS.  They use the existing ``acceptance_api``
build seam with a fake runtime/QGIS project writer, the checked-in reference bundle, and generated
QML source contracts.  No QGIS application, QField runtime, browser, network, or real PyQGIS
process is started here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from qfield_builder import build as build_module
from qfield_builder import (
    korean_layer_display_names,
    qgis_worker,
    qml_plugin,
    reference_bundle,
    schemas,
)
from qfield_builder.qgis_worker import _authoritative_location_expression

from .conftest import REFERENCE_DATA_VALID_SAMPLE_DIR, make_base_config

pytestmark = pytest.mark.qgis

RASTER_REL_DIR = Path("reference/rasters/bce_inverse_corrected_probability_maps")
SOURCE_RASTER_REL_DIR = Path("rasters/bce_inverse_corrected_probability_maps")
REAL_REFERENCE_RASTER_DIR = (
    Path(__file__).resolve().parents[3]
    / "storage"
    / "reference"
    / "rasters"
    / "bce_inverse_corrected_probability_maps"
)
PROBABILITY_GROUP_NAME = "Probability rasters (lookup)"
SURVEY_LAYER_NAME = korean_layer_display_names.display_name_for("survey")
PLOT_LAYER_NAME = korean_layer_display_names.display_name_for("plot")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strip_js_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def _fake_qgis_build(monkeypatch):
    """Patch only the QGIS/runtime boundary while keeping build_project's real file flow."""
    calls: list[dict] = []

    monkeypatch.setattr(
        build_module.runtime,
        "check_runtime",
        lambda **_kwargs: {"available": True, "message": ""},
    )

    def fake_build_qgis_project(**kwargs):
        calls.append(kwargs)
        Path(kwargs["qgs_path"]).write_text("<qgis-project />\n", encoding="utf-8")
        return {"online_key_embedded": False, "plantnet_key_embedded": False}

    monkeypatch.setattr(build_module.qgis_worker, "build_qgis_project", fake_build_qgis_project)
    monkeypatch.setattr(
        build_module.validate,
        "validate_project",
        lambda _project_dir: {"valid": True, "issues": []},
    )

    def fake_write_validation_report(project_dir: str, report: dict) -> str:
        path = Path(project_dir) / "VALIDATION_REPORT.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return str(path)

    monkeypatch.setattr(
        build_module.validate, "write_validation_report", fake_write_validation_report
    )
    return calls


def _build_without_qgis(acceptance_api, monkeypatch, tmp_path: Path) -> tuple[dict, list[dict]]:
    calls = _fake_qgis_build(monkeypatch)
    config = make_base_config("simple_inventory", display_name="확률 래스터 생성 테스트")
    config["identification_enabled"] = True
    result = acceptance_api.build_project(config, str(tmp_path / "generated"))
    return result, calls


def _widget_source(survey_type: str, table_name: str) -> str:
    return qml_plugin.render_identification_widget_qml(
        "array_to_string(array(leaf_photo_path), ',')",
        immediate_identification=True,
        layer_context=table_name,
        location_expression=_authoritative_location_expression(survey_type, table_name),
    )


def _called_function_names(source: str, function_name: str) -> set[str]:
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_ac_prg_001_small_reference_rasters_are_copied_byte_for_byte_and_sorted(tmp_path):
    source_dir = REFERENCE_DATA_VALID_SAMPLE_DIR / SOURCE_RASTER_REL_DIR
    project_dir = tmp_path / "project"
    reference_bundle.bundle_reference_data(str(REFERENCE_DATA_VALID_SAMPLE_DIR), str(project_dir))

    source_files = sorted(source_dir.glob("*.tif"))
    destination_files = sorted((project_dir / RASTER_REL_DIR).glob("*.tif"))
    assert [path.name for path in destination_files] == [path.name for path in source_files]
    assert all(
        _sha256(dst) == _sha256(src)
        for src, dst in zip(source_files, destination_files, strict=True)
    )


@pytest.mark.skipif(
    not REAL_REFERENCE_RASTER_DIR.is_dir(),
    reason="the full storage/reference raster fixture is not present on this checkout",
)
def test_ac_prg_001_full_reference_fixture_has_2532_files_and_is_fully_bundled(tmp_path):
    """Exercise the complete 64 MB TIFF set without constructing a QGIS application."""
    assert len(list(REAL_REFERENCE_RASTER_DIR.glob("*.tif"))) == 2532

    reference_dir = tmp_path / "reference"
    (reference_dir / "tables").mkdir(parents=True)
    shutil.copytree(
        REFERENCE_DATA_VALID_SAMPLE_DIR / "tables",
        reference_dir / "tables",
        dirs_exist_ok=True,
    )
    (reference_dir / "rasters").mkdir()
    (reference_dir / "rasters" / REAL_REFERENCE_RASTER_DIR.name).symlink_to(
        REAL_REFERENCE_RASTER_DIR, target_is_directory=True
    )

    project_dir = tmp_path / "full-project"
    reference_bundle.bundle_reference_data(str(reference_dir), str(project_dir))
    source_files = sorted(REAL_REFERENCE_RASTER_DIR.glob("*.tif"))
    destination_files = sorted((project_dir / RASTER_REL_DIR).glob("*.tif"))
    assert len(destination_files) == 2532
    assert [path.name for path in destination_files] == [path.name for path in source_files]
    assert all(
        _sha256(dst) == _sha256(src)
        for src, dst in zip(source_files, destination_files, strict=True)
    )


def test_ac_prg_003_fake_bridge_generation_succeeds_without_worker_timeout(
    acceptance_api, monkeypatch, tmp_path
):
    result, calls = _build_without_qgis(acceptance_api, monkeypatch, tmp_path)
    assert result["success"], result.get("error_message")
    assert result.get("error_code") != "worker_timeout"
    assert len(calls) == 1
    assert Path(result["project_dir"]).is_dir()


def test_ac_prg_002_qgis_project_builder_has_no_probability_raster_registration_or_group():
    source = Path(qgis_worker.__file__).read_text(encoding="utf-8")
    calls = _called_function_names(source, "_build_qgis_project_pyqgis")
    assert "_add_probability_raster_layers" not in calls
    assert "_hide_probability_raster_group" not in calls
    assert "_add_probability_raster_layers" not in source
    assert PROBABILITY_GROUP_NAME not in source


def test_ac_prg_003_build_manifest_lists_every_raster_as_project_relative_reference(
    acceptance_api, monkeypatch, tmp_path
):
    result, _calls = _build_without_qgis(acceptance_api, monkeypatch, tmp_path)
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])
    manifest = json.loads((project_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    references = manifest["required_files"]["reference"]
    raster_references = [
        path for path in references if path.startswith(f"{RASTER_REL_DIR.as_posix()}/")
    ]
    expected = [
        f"{RASTER_REL_DIR.as_posix()}/{path.name}"
        for path in sorted((REFERENCE_DATA_VALID_SAMPLE_DIR / SOURCE_RASTER_REL_DIR).glob("*.tif"))
    ]
    assert raster_references == expected
    assert all(not Path(path).is_absolute() for path in references)


def test_ac_prg_004_generated_manifest_has_no_absolute_secret_or_photo_paths(
    acceptance_api, monkeypatch, tmp_path
):
    result, _calls = _build_without_qgis(acceptance_api, monkeypatch, tmp_path)
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])
    manifest_text = (project_dir / "MANIFEST.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in manifest_text
    assert "API-KEY" not in manifest_text
    assert "photo" not in manifest_text.lower()
    assert "attachments/" not in manifest_text


@pytest.mark.parametrize(
    ("survey_type", "table_name", "required_location_fragments"),
    [
        ("simple_inventory", "inventory_observation", ("$geometry",)),
        (
            "temporary_plots",
            "observation",
            (f"get_feature('{SURVEY_LAYER_NAME}'", "plot_geom"),
        ),
        (
            "permanent_plots",
            "observation",
            (f"get_feature('{PLOT_LAYER_NAME}'", "plot_geom", "current_parent_value('plot_id')"),
        ),
    ],
)
def test_ac_prg_006_types_1_to_3_keep_authoritative_location_and_direct_worker_sampler(
    survey_type, table_name, required_location_fragments
):
    location = _authoritative_location_expression(survey_type, table_name)
    widget = _strip_js_comments(_widget_source(survey_type, table_name))
    assert all(fragment in location for fragment in required_location_fragments)
    if survey_type == "permanent_plots":
        assert "survey_geom" not in location
        assert "parent_survey_geom" not in location
    assert "WorkerScript" in widget
    assert "qpb_probability_worker.js" in widget
    assert "qpbReadProbabilityRasterBytes" in widget
    assert "FileUtils.readFileContent" in widget
    assert "@project_folder" in widget
    assert "raster_value(" not in widget


def test_ac_prg_005_worker_script_retains_tiff_lzw_msb_first_decoder_and_pixel_validation():
    worker = qml_plugin.PROBABILITY_WORKER_SCRIPT
    assert "most-significant bit first" in worker
    assert "(byte >> (7 - (pos & 7)))" in worker
    assert "table = []; for (var k = 0; k < 256; k++)" in worker
    assert "codeSize < 12" in worker
    assert "sampleFormat !== 3" in worker
    assert "value < 0 || value > 1" in worker
    assert "raster_missing_nodata_or_outside_extent" in worker


def test_ac_prg_007_missing_or_invalid_candidate_is_unavailable_without_dropping_candidates():
    widget = _strip_js_comments(_widget_source("simple_inventory", "inventory_observation"))
    assert "raster_missing_nodata_or_outside_extent" in widget
    assert "raster_sampling_failed" in widget
    assert "probability_value = null" in widget
    assert "확률 데이터가 없습니다." in widget
    assert "qpbFinishProbabilitySample" in widget
    assert "qpbProbabilityJobs" in widget


def test_ac_prg_009_sampling_is_async_watchdog_bounded_and_has_no_sync_qgis_expression_path():
    widget = _strip_js_comments(_widget_source("simple_inventory", "inventory_observation"))
    assert "qpbProbabilityWorker.sendMessage" in widget
    assert "qpbProbabilityWatchdog" in widget
    assert "timeoutMs = 3000" in widget
    assert "raster_sampling_timed_out" in widget
    assert "expression.evaluate(raster_value" not in widget
    assert "raster_value(" not in widget


def test_ac_prg_010_location_failure_uses_no_exif_gps_or_photo_metadata_fallback():
    widget = _strip_js_comments(_widget_source("permanent_plots", "observation"))
    assert "qpbResolveAuthoritativeLocation" in widget
    assert "return null" in widget
    assert "exif" not in widget.lower()
    assert "device gps" not in widget.lower()
    assert "metadata" not in widget.lower()
    assert "qpbCurrentPhotoPaths" in widget
    assert "qpbResolveAuthoritativeLocation()" in widget


def test_ac_prg_011_type4_is_display_only_and_has_no_probability_specific_schema_fields():
    assert "community" in qgis_worker.IDENTIFICATION_TARGET_LAYERS
    type4 = schemas.get_schema("vegetation_mapping")
    community_columns = {column.name for column in type4["community"].columns}
    assert not {
        "selected_korean_name",
        "selected_scientific_name",
        "selected_ktsn",
    } & community_columns


def test_ac_prg_012_identification_enabled_build_keeps_worker_and_raster_files_outside_qgis_tree(
    acceptance_api, monkeypatch, tmp_path
):
    result, calls = _build_without_qgis(acceptance_api, monkeypatch, tmp_path)
    assert result["success"], result.get("error_message")
    assert len(calls) == 1
    project_dir = Path(result["project_dir"])
    assert (project_dir / qml_plugin.PROBABILITY_WORKER_SCRIPT_RELPATH).is_file()
    assert (project_dir / "reference" / "ktsn_lookup.csv").is_file()
    assert list((project_dir / RASTER_REL_DIR).glob("*.tif"))
    assert not list(project_dir.glob("*Probability*"))
