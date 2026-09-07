"""Acceptance coverage for the single multiband occurrence-probability raster.

The build/artifact assertions use the acceptance API's repository-isolated seams.  Runtime
assertions inspect the generated identification-widget QML because this repository has no QField
QML runtime.  No test in this module constructs QGIS or launches QGIS/QField itself.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import unicodedata
from pathlib import Path

import pytest

from qfield_builder import korean_layer_display_names, qml_plugin
from qfield_builder.qgis_worker import (
    IDENTIFICATION_TARGET_LAYERS,
    _authoritative_location_expression,
)

from .conftest import (
    REFERENCE_DATA_VALID_SAMPLE_DIR,
    _require_harness_function,
    make_base_config,
)

SPECIES_NAME_RE = re.compile(r"^bce_inverse_corrected_probability_(.+)\.tif$")
STACK_RELPATH = "reference/rasters/occurrence_probability_multiband.tif"
INDEX_RELPATH = "reference/rasters/occurrence_probability_bands.json"

TYPE_1 = ("simple_inventory", "inventory_observation")
TYPE_2 = ("temporary_plots", "observation")
TYPE_3 = ("permanent_plots", "observation")
TYPE_1_2_3 = (TYPE_1, TYPE_2, TYPE_3)


def _harness_fn(acceptance_api, name: str):
    return _require_harness_function(acceptance_api, name)


def _function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", source)
    assert match, f"generated QML must contain function {name}()"
    opening = source.find("{", match.end())
    assert opening >= 0
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    for index in range(opening, len(source)):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "/" and next_char == "/":
            line_comment = True
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"unterminated generated function {name}()")


def _widget_source(survey_type: str, table_name: str, project_crs: str = "EPSG:5186") -> str:
    return qml_plugin.render_identification_widget_qml(
        "array_to_string(array(leaf_photo_path, flower_photo_path, fruit_photo_path), ',')",
        immediate_identification=True,
        layer_context=table_name,
        location_expression=_authoritative_location_expression(
            survey_type, table_name, project_crs
        ),
    )


def _species_files(raster_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in raster_dir.iterdir()
        if path.is_file() and SPECIES_NAME_RE.fullmatch(path.name)
    )


def _link_inventory(source_files: list[Path], target: Path) -> Path:
    """Create an enumeration-controlled inventory without copying raster payloads."""
    target.mkdir(parents=True, exist_ok=True)
    try:
        for source in source_files:
            os.link(source, target / source.name)
    except OSError as exc:
        pytest.skip(f"cannot create hard-linked probability-raster inventory: {exc}")
    return target


@pytest.fixture(scope="module")
def authoritative_species_inventory(real_probability_raster_dir) -> Path:
    species = _species_files(real_probability_raster_dir)
    if not species:
        pytest.skip("authoritative raster fixture has no species-pattern TIFFs")
    return real_probability_raster_dir


@pytest.fixture(scope="module")
def discovered_species_count(authoritative_species_inventory) -> int:
    return len(_species_files(authoritative_species_inventory))


@pytest.fixture(scope="module")
def generated_multiband_project_by_type(
    acceptance_api, authoritative_species_inventory, tmp_path_factory
):
    cache: dict[str, dict] = {}

    def build_for(survey_type: str) -> dict:
        if survey_type not in cache:
            config = make_base_config(survey_type, f"MPR {survey_type}")
            config["identification_enabled"] = True
            config["_test_probability_raster_source_dir"] = str(authoritative_species_inventory)
            config["_test_reference_data_dir"] = str(REFERENCE_DATA_VALID_SAMPLE_DIR)
            output_dir = tmp_path_factory.mktemp(f"mpr_{survey_type}") / "project"
            cache[survey_type] = acceptance_api.build_project(config, str(output_dir))
            assert cache[survey_type].get("success"), cache[survey_type].get("error_message")
        return cache[survey_type]

    return build_for


def test_ac_mpr_001_species_inventory_uses_discovered_count_and_excludes_richness(
    acceptance_api,
    authoritative_species_inventory,
    discovered_species_count,
    tmp_path,
):
    """AC-MPR-001: every matching TIFF is accepted; nonmatching richness is excluded."""
    validate = _harness_fn(acceptance_api, "validate_probability_raster_sources")
    build_stack = _harness_fn(acceptance_api, "build_probability_stack")

    validation = validate(str(authoritative_species_inventory))
    assert validation["ok"] is True, validation["message"]
    assert validation["discovered_species_count"] == discovered_species_count
    assert any("richness" in path.lower() for path in validation["excluded_files"])

    species = _species_files(authoritative_species_inventory)
    changed_count_sources = species[:1]
    if discovered_species_count == 1:
        alias = tmp_path / "alias" / "bce_inverse_corrected_probability_동적테스트종.tif"
        alias.parent.mkdir(parents=True)
        try:
            os.link(species[0], alias)
        except OSError as exc:
            pytest.skip(f"cannot create dynamic-count test alias: {exc}")
        changed_count_sources.append(alias)

    changed_inventory = _link_inventory(changed_count_sources, tmp_path / "changed_inventory")
    richness = next(
        (
            path
            for path in authoritative_species_inventory.iterdir()
            if "richness" in path.name.lower()
        ),
        None,
    )
    if richness is not None:
        try:
            os.link(richness, changed_inventory / richness.name)
        except OSError as exc:
            pytest.skip(f"cannot link excluded richness fixture: {exc}")

    changed_count = len(changed_count_sources)
    assert changed_count != discovered_species_count
    changed_validation = validate(str(changed_inventory))
    assert changed_validation["ok"] is True, changed_validation["message"]
    assert changed_validation["discovered_species_count"] == changed_count
    changed_result = build_stack(str(changed_inventory), str(tmp_path / "changed_project"))
    assert changed_result["success"], changed_result.get("error_message")
    changed_index = json.loads(Path(changed_result["index_path"]).read_text(encoding="utf-8"))
    assert changed_index["band_count"] == changed_count
    assert not any(
        SPECIES_NAME_RE.fullmatch(path.name)
        for path in (tmp_path / "changed_project").rglob("*.tif")
    )


@pytest.mark.parametrize("failure_case", ("missing", "empty", "invalid"))
def test_ac_mpr_001_missing_empty_or_invalid_inventory_fails_closed(
    acceptance_api, tmp_path, failure_case
):
    """AC-MPR-001: unusable inventories publish no stack or index."""
    validate = _harness_fn(acceptance_api, "validate_probability_raster_sources")
    build_stack = _harness_fn(acceptance_api, "build_probability_stack")
    source_dir = tmp_path / f"source_{failure_case}"
    if failure_case != "missing":
        source_dir.mkdir()
    if failure_case == "invalid":
        invalid = source_dir / "bce_inverse_corrected_probability_손상래스터.tif"
        invalid.write_bytes(b"not a GeoTIFF")

    validation = validate(str(source_dir))
    assert validation["ok"] is False
    assert validation["error_code"]
    assert validation["message"]

    output_dir = tmp_path / f"failed_{failure_case}"
    result = build_stack(str(source_dir), str(output_dir))
    assert result["success"] is False
    assert result["error_code"]
    assert not (output_dir / STACK_RELPATH).exists()
    assert not (output_dir / INDEX_RELPATH).exists()


def test_ac_mpr_002_stack_band_count_matches_discovered_species_and_preserves_pixels(
    acceptance_api, authoritative_species_inventory, discovered_species_count, tmp_path
):
    """AC-MPR-002: every source raster is represented once with values/NoData preserved."""
    validate = _harness_fn(acceptance_api, "validate_probability_raster_sources")
    build_stack = _harness_fn(acceptance_api, "build_probability_stack")
    inspect_stack = _harness_fn(acceptance_api, "inspect_probability_stack")
    validation = validate(str(authoritative_species_inventory))
    assert validation["ok"] is True, validation["message"]
    result = build_stack(str(authoritative_species_inventory), str(tmp_path / "project"))

    assert result["success"], result.get("error_message")
    assert result["stack_path"].endswith(STACK_RELPATH)
    assert result["index_path"].endswith(INDEX_RELPATH)

    report = inspect_stack(result["stack_path"], str(authoritative_species_inventory))
    assert report["valid"] is True
    assert report["band_count"] == discovered_species_count
    assert report["source_files_represented_once"] is True
    assert report["pixel_crosscheck"]["values_match"] is True
    assert report["pixel_crosscheck"]["nodata_match"] is True
    assert report["metadata"]["nodata"] == -9999


def test_ac_mpr_003_index_is_nfc_normalized_unique_1_based_and_order_independent(
    acceptance_api, authoritative_species_inventory, discovered_species_count, tmp_path
):
    """AC-MPR-003: the JSON band index is exact and independent of filesystem enumeration."""
    build_stack = _harness_fn(acceptance_api, "build_probability_stack")
    first_dir = tmp_path / "first"
    second_inventory = tmp_path / "second" / "rasters" / "bce_inverse_corrected_probability_maps"
    second_inventory.mkdir(parents=True)
    source_files = _species_files(authoritative_species_inventory)
    _link_inventory(list(reversed(source_files)), second_inventory)

    first = build_stack(str(authoritative_species_inventory), str(first_dir))
    second = build_stack(str(second_inventory), str(tmp_path / "second_project"))
    assert first["success"], first.get("error_message")
    assert second["success"], second.get("error_message")

    first_index = json.loads(Path(first["index_path"]).read_text(encoding="utf-8"))
    second_index = json.loads(Path(second["index_path"]).read_text(encoding="utf-8"))
    assert first_index["stack_path"] == STACK_RELPATH
    assert first_index["band_count"] == discovered_species_count
    assert first_index["mapping"] == second_index["mapping"]

    mapping = first_index["mapping"]
    assert len(mapping) == discovered_species_count
    assert list(mapping) == sorted(unicodedata.normalize("NFC", name) for name in mapping)
    assert all(
        isinstance(band, int) and 1 <= band <= discovered_species_count
        for band in mapping.values()
    )
    assert len(set(mapping.values())) == discovered_species_count
    assert all(unicodedata.normalize("NFC", name) == name for name in mapping)
    serialized = Path(first["index_path"]).read_text(encoding="utf-8")
    assert "credentials" not in serialized.lower()
    assert "photo" not in serialized.lower()
    assert not re.search(r"(?:[A-Za-z]:[\\/]|/Users/|/private/|/tmp/)", serialized)


@pytest.mark.parametrize("survey_type,table_name", TYPE_1_2_3)
@pytest.mark.qgis
def test_ac_mpr_004_ac_mpr_005_project_has_one_relative_multiband_layer_and_no_species_tiffs(
    acceptance_api,
    survey_type,
    table_name,
    generated_multiband_project_by_type,
    discovered_species_count,
):
    """AC-MPR-004/005: enabled Types 1–3 package and register one shared raster only."""
    del table_name
    inspect_project = _harness_fn(acceptance_api, "inspect_probability_project")
    generated = generated_multiband_project_by_type(survey_type)
    project_dir = generated["project_dir"]
    report = inspect_project(project_dir)
    layers = report["probability_layers"]
    nodes = report["probability_layer_tree_nodes"]
    assert len(layers) == 1
    assert len(nodes) == 1
    assert layers[0]["valid"] is True
    assert layers[0]["datasource"].endswith(STACK_RELPATH)
    assert report["reference_files"].count(STACK_RELPATH) == 1
    assert report["reference_files"].count(INDEX_RELPATH) == 1
    assert report["manifest"]["band_count"] == discovered_species_count
    assert not any(SPECIES_NAME_RE.match(Path(path).name) for path in report["reference_files"])
    assert report["absolute_path_leaks"] == []


@pytest.mark.qgis
def test_ac_mpr_006_generation_returns_before_180_seconds_and_registers_once(
    acceptance_api, authoritative_species_inventory, tmp_path
):
    """AC-MPR-006: the authoritative bridge job is bounded and never reports worker_timeout."""
    config = make_base_config("simple_inventory", "MPR performance project")
    config["identification_enabled"] = True
    config["_test_probability_raster_source_dir"] = str(authoritative_species_inventory)
    started = time.monotonic()
    result = acceptance_api.build_project(config, str(tmp_path / "project"))
    elapsed = time.monotonic() - started
    assert result.get("success"), result.get("error_message")
    assert elapsed <= 180
    assert result.get("error_code") != "worker_timeout"
    assert result.get("probability_raster_registration_count") == 1


def test_ac_mpr_007_runtime_looks_up_nfc_korean_name_and_samples_shared_stack_via_raster_value():
    """AC-MPR-007: runtime key/band selection is Korean-name/index/raster_value based."""
    source = _widget_source(*TYPE_1)
    formatter = _function_body(source, "qpbFormatProbability")
    assert "occurrence_probability_bands.json" in source
    assert re.search(r"normalize\s*\(\s*[\"']NFC[\"']\s*\)", source)
    assert "occurrence_probability_multiband.tif" in formatter
    assert "raster_value(" in formatter
    assert re.search(r"band|band_number|bandIndex", formatter, re.IGNORECASE)
    assert "scientificName" not in formatter
    assert "KTSN" not in formatter
    assert "bce_inverse_corrected_probability_" not in formatter
    assert "readdir" not in formatter and "enumerat" not in formatter.lower()


def test_ac_mpr_008_ac_mpr_011_missing_mapping_and_sampler_failure_are_candidate_local():
    """AC-MPR-008/011: unavailable probability cannot cancel identification or save flow."""
    source = _widget_source(*TYPE_1)
    formatter = _function_body(source, "qpbFormatProbability")
    response = _function_body(source, "qpbHandlePlantNetResponse")
    sampler = _function_body(source, "qpbSampleProbabilityRaster")
    selection = _function_body(source, "qpbSelectCandidate")

    assert "available: false" in formatter
    assert "occurrence_probability_bands.json" in source
    assert "qpbCandidatesModel" in response
    assert "candidates.push" in response
    assert "try" in sampler and "catch" in sampler
    assert re.search(r"timeout|timed[_ -]?out", source, re.IGNORECASE)
    assert "if (!location)" in formatter or "if (location == null)" in formatter
    assert "qpbWriteAttributeWriteBackRequest" in selection
    assert "qpbCandidatesModel = []" in selection


def test_ac_mpr_009_zero_nodata_nonfinite_and_out_of_range_values_are_not_clamped():
    """AC-MPR-009: valid zero survives; NoData/invalid/out-of-extent remain unavailable."""
    source = _widget_source(*TYPE_1)
    formatter = _function_body(source, "qpbFormatProbability")
    assert re.search(r"sample\s*(?:>=|>)\s*0(?:\.0)?", formatter)
    assert re.search(r"sample\s*(?:<=|<)\s*1(?:\.0)?", formatter)
    assert "sample === -9999" in formatter
    assert "sample === null" in formatter or "sample === undefined" in formatter
    assert "isFinite" in source
    assert "value: null" in source
    assert "raster_missing_nodata_or_outside_extent" in source
    assert "raster_invalid_value" in source
    assert "Math.max" not in source
    assert "Math.min" not in source


def test_ac_mpr_010_authoritative_locations_are_type_specific_and_transform_to_epsg4326():
    """AC-MPR-010: Type 3 uses its live/persisted plot, never survey geometry."""
    type1 = _authoritative_location_expression(*TYPE_1, project_crs="EPSG:5186")
    type2 = _authoritative_location_expression(*TYPE_2, project_crs="EPSG:5186")
    type3 = _authoritative_location_expression(*TYPE_3, project_crs="EPSG:5186")
    survey_layer = korean_layer_display_names.display_name_for("survey")
    plot_layer = korean_layer_display_names.display_name_for("plot")
    assert "$geometry" in type1
    assert f"get_feature('{survey_layer}'" in type2
    assert f"get_feature('{plot_layer}'" in type3
    assert "current_parent_value('plot_id')" in type3
    assert "survey_geom" not in type3
    assert "parent_survey_geom" not in type3
    for expression in (type1, type2, type3):
        assert "transform(" in expression
        assert "EPSG:5186" in expression
        assert "EPSG:4326" in expression
        assert "centroid" not in expression.lower()
        assert "EXIF" not in expression

    for survey_type, table_name in TYPE_1_2_3:
        source = _widget_source(survey_type, table_name, "EPSG:5186")
        location = _function_body(source, "qpbResolveAuthoritativeLocation")
        assert "qpbLastLocation" not in location
        assert "EPSG:4326" in source
        for forbidden in ("EXIF", "exif", "deviceGps", "device_gps", "photoMetadata"):
            assert forbidden not in location


def test_ac_mpr_012_mixed_candidates_keep_individual_probability_and_persist_only_selected_value():
    """AC-MPR-012: mixed candidate outcomes do not overwrite each other or relation fields."""
    source = _widget_source(*TYPE_1)
    response = _function_body(source, "qpbHandlePlantNetResponse")
    selection = _function_body(source, "qpbSelectCandidate")
    assert "probability_value: probability.value" in response
    assert "probability_text: probability.text" in response
    assert "probability_request_id" in response
    assert "c.probability_value" in selection
    assert "occurrence_probability" in selection
    assert "qpbWriteAttributeWriteBackRequest" in selection
    assert "uuid" not in selection.lower() or "uuid" in source.lower()


@pytest.mark.parametrize("survey_type,table_name", TYPE_1_2_3)
@pytest.mark.qgis
def test_ac_mpr_013_identification_disabled_does_not_add_probability_scope(
    acceptance_api, survey_type, table_name, tmp_path
):
    """AC-MPR-013: Type 4 and disabled identification have no probability deliverables."""
    del table_name
    if survey_type != "simple_inventory":
        pytest.skip("Type 4 is covered by the dedicated case below")
    config = make_base_config(survey_type, "MPR identification disabled")
    config["identification_enabled"] = False
    result = acceptance_api.build_project(config, str(tmp_path / "disabled"))
    assert result.get("success"), result.get("error_message")
    project_dir = Path(result["project_dir"])
    assert not (project_dir / STACK_RELPATH).exists()
    assert not (project_dir / INDEX_RELPATH).exists()
    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8", errors="replace")
    assert "occurrence_probability_multiband" not in qgs_text


@pytest.mark.qgis
def test_ac_mpr_013_type4_has_no_probability_stack_layer_when_identification_is_disabled(
    acceptance_api, tmp_path
):
    config = make_base_config("vegetation_mapping", "MPR Type 4")
    config["identification_enabled"] = False
    result = acceptance_api.build_project(config, str(tmp_path / "type4"))
    assert result.get("success"), result.get("error_message")
    project_dir = Path(result["project_dir"])
    assert not (project_dir / STACK_RELPATH).exists()
    assert not (project_dir / INDEX_RELPATH).exists()
    assert "community" in IDENTIFICATION_TARGET_LAYERS
    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8", errors="replace")
    assert "occurrence_probability_multiband" not in qgs_text
    assert "Identify attached photos" not in qgs_text


@pytest.mark.qgis
def test_ac_mpr_014_copied_project_resolves_relative_stack_and_index_without_species_layers(
    acceptance_api, generated_multiband_project_by_type, tmp_path
):
    """AC-MPR-014: transfer preserves relative artifacts and avoids species layers."""
    generated = generated_multiband_project_by_type("simple_inventory")
    source_dir = Path(generated["project_dir"])
    copied_dir = tmp_path / "copied_project"
    shutil.copytree(source_dir, copied_dir)
    inspect_project = _harness_fn(acceptance_api, "inspect_probability_project")
    sample = _harness_fn(acceptance_api, "sample_probability_candidate")
    report = inspect_project(str(copied_dir))
    assert report["absolute_path_leaks"] == []
    assert report["probability_layers"][0]["datasource"].endswith(STACK_RELPATH)
    assert report["reference_files"].count(STACK_RELPATH) == 1
    assert report["reference_files"].count(INDEX_RELPATH) == 1
    assert len(report["probability_layers"]) == 1
    known_name = sorted(report["band_index_mapping"])[0]
    sampled = sample(str(copied_dir), known_name, {"lon": 127.0, "lat": 37.0})
    assert sampled["available"] is True
    assert 0.0 <= sampled["value"] <= 1.0


@pytest.mark.device
@pytest.mark.skip(
    reason=(
        "AC-MPR-007–012 require exercising the generated QML inside QField: open a transferred "
        "Types 1–3 project, sample candidates whose Korean names map to distinct bands, and "
        "confirm known values, exact 0.0, -9999/NoData, non-finite/out-of-range, invalid or "
        "out-of-extent locations, missing mappings, mixed candidate-local fallback, selection, "
        "write-back, save/reopen, and UUID/FK/relation preservation. This repository has no "
        "QField/QML runtime and the test-designer must not launch QGIS/QField."
    )
)
def test_ac_mpr_007_to_012_end_to_end_qfield_runtime_sampling_and_persistence():
    raise AssertionError("should never run while skipped -- see skip reason")
