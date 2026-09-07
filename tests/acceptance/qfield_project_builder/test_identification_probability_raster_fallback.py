"""Acceptance contracts for species-specific occurrence-probability raster sampling.

The QField/QML runtime is not available to this deterministic macOS harness.  These tests use
the generated QML as the injectable seam: the sampling result is represented by the QML sampler
contract, while the tests verify the type-specific location expression, candidate-level fallback,
and persistence boundaries without opening QGIS, reading a photo, or making a network request.
"""
from __future__ import annotations

import re

import pytest

from qfield_builder import korean_layer_display_names, qml_plugin
from qfield_builder.qgis_worker import (
    IDENTIFICATION_TARGET_LAYERS,
    _authoritative_location_expression,
)

TYPE_1 = ("simple_inventory", "inventory_observation")
TYPE_2 = ("temporary_plots", "observation")
TYPE_3 = ("permanent_plots", "observation")
TYPE_1_2_3 = (TYPE_1, TYPE_2, TYPE_3)


def _widget_source(survey_type: str, table_name: str) -> str:
    return qml_plugin.render_identification_widget_qml(
        "array_to_string(array(photo_path), ',')",
        immediate_identification=True,
        layer_context=table_name,
        location_expression=_authoritative_location_expression(survey_type, table_name),
    )


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
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "/" and next_char == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
        index += 1
    raise AssertionError(f"unterminated generated function {name}()")


def _location_body(survey_type: str, table_name: str) -> str:
    source = _widget_source(survey_type, table_name)
    return _function_body(source, "qpbResolveAuthoritativeLocation")


@pytest.mark.parametrize("survey_type,table_name", TYPE_1_2_3)
def test_ac_prf_001_008_012_sampling_uses_the_candidate_raster_and_real_location_seam(
    survey_type: str, table_name: str
):
    """AC-PRF-001/008/012: each returned candidate reaches the raster sampler.

    ``qpbSampleProbabilityRaster`` is the injectable runtime seam.  This contract deliberately
    does not require one private QField utility name, but it does require the generated widget to
    pass a relative species-specific TIFF path and the authoritative lon/lat to that seam.
    """
    source = _widget_source(survey_type, table_name)
    sampler = _function_body(source, "qpbSampleProbabilityRaster")
    formatter = _function_body(source, "qpbFormatProbability")
    response = _function_body(source, "qpbHandlePlantNetResponse")

    assert qml_plugin.REFERENCE_RASTER_DIR_RELPATH in formatter
    assert "bce_inverse_corrected_probability_" in formatter
    assert ".tif" in formatter
    assert re.search(r"qpbSampleProbabilityRaster\([^;]+location\.lon[^;]+location\.lat", formatter)
    assert "qpbFormatProbability(koreanName, location)" in response
    assert "probability_value: probability.value" in response
    assert "qpbReadProbabilityRasterBytes(rasterRelPath)" in sampler
    assert "qpbProbabilityWorker.sendMessage" in sampler
    assert re.search(r"requestId\s*:\s*requestId", sampler)
    assert re.search(r"bytes\s*:\s*bytes", sampler)
    assert re.search(r"lon\s*:\s*Number\(lon\)", sampler)
    assert re.search(r"lat\s*:\s*Number\(lat\)", sampler)
    assert "return requestId" in sampler
    assert "available: false" in sampler
    assert "qpbProbabilityWorker" in source
    assert "onMessage: qpbFinishProbabilitySample(message)" in source


def test_ac_prf_001_type1_uses_inventory_observation_geometry_only():
    """AC-PRF-001/002/004: Type 1 authoritative location is the current inventory feature."""
    expression = _authoritative_location_expression(*TYPE_1)
    assert "$geometry" in expression
    assert "geometry_type(@g) <> 'Point'" in expression
    assert "get_feature('survey'" not in expression
    assert "get_feature('plot'" not in expression
    assert "@project_folder" not in expression


def test_ac_prf_008_013_type2_uses_survey_and_type3_uses_snapshot_or_persisted_plot_only():
    """AC-PRF-008/013: Type 3 never promotes survey geometry to an authoritative location.

    The embedded observation widget cannot rely on QField's nested parent-form context. It must
    use the plot-WKT snapshot copied into the observation at form creation, then use a persisted
    plot only when reopening an already saved observation.
    """
    type2 = _authoritative_location_expression(*TYPE_2)
    type3 = _authoritative_location_expression(*TYPE_3)

    survey_layer = korean_layer_display_names.display_name_for("survey")
    plot_layer = korean_layer_display_names.display_name_for("plot")
    assert f"get_feature('{survey_layer}'" in type2
    assert f"get_feature('{plot_layer}'" not in type2
    assert f"get_feature('{plot_layer}'" in type3
    assert '"qpb_plot_geometry_wkt"' in type3
    assert "current_parent_value(" not in type3
    assert re.search(r"plot_geom.*IS NULL|plot_geom.*is_empty|plot_geom.*geometry_type", type3)
    assert "survey_geom" not in type3
    assert "parent_survey_geom" not in type3

    for survey_type, table_name in (TYPE_2, TYPE_3):
        source = _widget_source(survey_type, table_name)
        assert "qpbLastLocation = qpbResolveAuthoritativeLocation()" in source
        assert "EXIF" not in _function_body(source, "qpbResolveAuthoritativeLocation")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-PRF-013 / D-PRF-003 requires QField's real nested-form runtime. On a target iOS "
        "QField build, build an identification-enabled Type 3 project with a known candidate "
        "raster "
        "whose values differ at two documented points. Create site → plot → survey → observation "
        "through Related records without saving the plot or survey; digitize a valid current plot "
        "point at the first point, and retain a distinct valid survey point only as a negative "
        "control. Attach a non-geotagged test photo, run Identify from the nested observation, and "
        "verify the returned candidate's probability is the plot-point value, never the survey "
        "value. Then clear or make the current plot geometry invalid while retaining the survey "
        "point: probability must be unavailable, while the candidate remains selectable and the "
        "normal save flow remains usable. Record QField/iOS versions, project build ID, raster "
        "points/expected values, screenshots, and the saved-record result; do not treat a desktop "
        "or source-inspection result as a substitute."
    )
)
def test_ac_prf_013_type3_unsaved_plot_geometry_and_invalid_plot_on_qfield_device():
    raise AssertionError("should never run while skipped -- see skip reason")


def test_ac_prf_002_006_missing_raster_is_candidate_local_and_does_not_drop_candidates():
    """AC-PRF-002/006: unavailable probability does not remove or cancel a candidate."""
    source = _widget_source(*TYPE_1)
    response = _function_body(source, "qpbHandlePlantNetResponse")
    formatter = _function_body(source, "qpbFormatProbability")

    assert "sample.available === false" in formatter
    assert "return { text: \"확률 데이터가 없습니다.\", value: null" in formatter
    assert "candidates.push({" in response
    assert "probability_text: probability.text" in response
    assert "probability_value: probability.value" in response
    assert response.index("var probability = qpbFormatProbability") < response.index(
        "candidates.push({"
    )
    assert "qpbCandidatesModel = candidates" in response


def test_ac_prf_003_011_sampling_capability_errors_are_bounded_and_non_blocking():
    """AC-PRF-003/011: sampler capability/error outcomes are honest and non-blocking."""
    source = _widget_source(*TYPE_1)
    sampler = _function_body(source, "qpbSampleProbabilityRaster")
    formatter = _function_body(source, "qpbFormatProbability")
    watchdog = _function_body(source, "qpbExpireProbabilitySamples")

    assert "try" in sampler and "catch" in sampler
    assert "available: false" in sampler
    assert "raster_sampling_api_not_found" in sampler
    assert "sample.available === false" in formatter
    assert "예측 출현 확률을 계산할 수 없습니다" in formatter
    assert "qpbHandlePlantNetResponse(response)" in source
    assert "WorkerScript" in source
    assert "onMessage: qpbFinishProbabilitySample(message)" in source
    assert "qpbProbabilityWatchdog" in source
    assert "qpbExpireProbabilitySamples()" in source
    assert "timeoutMs = 3000" in watchdog
    assert re.search(r"timeout|timed[_ -]?out", watchdog, re.IGNORECASE)
    assert "setInterval" not in sampler
    assert "while (true)" not in sampler


@pytest.mark.parametrize(
    "sample_contract",
    [
        "sample === -9999",
        "sample === null || sample === undefined",
        "sample >= 0.0 && sample <= 1.0",
    ],
)
def test_ac_prf_005_invalid_raster_values_are_not_fabricated_as_zero(sample_contract: str):
    """AC-PRF-005: NoData/malformed values remain unavailable; valid values stay 0..1."""
    source = _widget_source(*TYPE_1)
    formatter = _function_body(source, "qpbFormatProbability")
    assert sample_contract in formatter
    assert "value: null" in formatter
    assert "Math.max" not in formatter
    assert "Math.min" not in formatter
    assert "sample = 0" not in formatter


def test_ac_prf_004_007_010_location_failure_and_unavailable_probability_keep_writeback_flow():
    """AC-PRF-004/007/010: location/probability failure does not block selection or save."""
    source = _widget_source(*TYPE_1)
    resolver = _function_body(source, "qpbResolveAuthoritativeLocation")
    run = _function_body(source, "qpbRunIdentification")
    select = _function_body(source, "qpbSelectCandidate")

    assert "return null" in resolver
    assert "qpbLastLocation = qpbResolveAuthoritativeLocation()" in run
    assert "qpbWriteAttributeWriteBackRequest" in select
    assert "selected_korean_name" in select
    assert "occurrence_probability: c.probability_value" in select
    assert "qpbCandidatesModel = []" in select
    for forbidden in ("EXIF", "exif", "deviceGps", "device_gps", "photoMetadata"):
        assert forbidden not in resolver
        assert forbidden not in run


def test_ac_prf_009_type4_is_a_display_only_photo_identification_target():
    """Type 4 community shows candidates, but it has no automatic write-back destination."""
    assert "community" in IDENTIFICATION_TARGET_LAYERS
    assert set(IDENTIFICATION_TARGET_LAYERS) == {
        "inventory_observation", "observation", "community"
    }
    source = qml_plugin.render_identification_widget_qml(
        "array_to_string(array(leaf_photo_path), ',')", candidate_selection_enabled=False
    )
    assert "qpbCandidateSelectionEnabled: false" in source
    assert "if (!qpbCandidateSelectionEnabled) { return; }" in source


def test_ac_prf_010_015_paths_are_relative_and_do_not_embed_photo_or_secret_data():
    """AC-PRF-010/015: raster lookup is project-relative and metadata is not a location source."""
    source = _widget_source(*TYPE_1)
    formatter = _function_body(source, "qpbFormatProbability")
    sampler = _function_body(source, "qpbSampleProbabilityRaster")
    assert qml_plugin.REFERENCE_RASTER_DIR_RELPATH in formatter
    assert not re.search(r"[A-Za-z]:[\\/]|^/", formatter, re.MULTILINE)
    assert "photo" not in sampler.lower()
    assert "secret" not in sampler.lower()
    assert "apiKey" not in sampler
    assert "EXIF" not in sampler
