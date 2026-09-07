"""Acceptance tests for the generated QField canonical-runtime lookup route.

The two test seams used here are deliberately semantic, not serialization-specific:
``inspect_canonical_runtime_lookup(project_dir)`` must inspect the delivered resource/provenance,
and ``exercise_canonical_runtime_lookup(...)`` must execute the generated QML/JavaScript route
against that resource (not a separate Python matcher).  Their required result fields are asserted
below, so an implementation remains free to choose CSV, JSON, or another compact local format.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from .conftest import REFERENCE_DATA_VALID_SAMPLE_DIR, make_base_config


CANONICAL_TABLE = "ktsn_taxonomy_reference"
CANONICAL_LAYER = "식물 분류 참조표"
ACCEPTED_KEY = "Runtimeus acceptus"
SYNONYM_KEY = "Runtimeus synonymus"
EXPECTED = {
    "selected_korean_name": "런타임정명",
    "selected_scientific_name": "Runtimeus acceptus (A.) B.",
    "selected_ktsn": "000000000101",
}
TYPE_LAYERS = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}


def _require(api, name: str):
    function = getattr(api, name, None)
    assert callable(function), f"QCR acceptance seam is required: acceptance_api.{name}"
    return function


def _write_fixture_workbook(path: Path) -> Path:
    """A minimal accepted-before-synonym D-95 workbook, created only under pytest tmp_path."""
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Data Sheet"
    sheet.append([
        "No", "관리분류군", "정이명여부", "학명", "대표국명", "명명자", "명명년도",
        "Phylum", None, "Class", None, "Order", None, "Family", None, "Genus", None,
        "SubGenus", None, "Species", None, "콘텐츠 여부", "URL",
    ])
    sheet.append([
        None, None, None, None, None, None, None, "Name", "국명", "Name", "국명", "Name",
        "국명", "Name", "국명", "Name", "국명", "Name", "국명", "Name", "국명", None,
        None,
    ])
    ranks = [
        "Magnoliophyta", "속씨식물문", "Runtimeopsida", "런타임강", "Runtimeales", "런타임목",
        "Runtimeaceae", "런타임과", "Runtimeus", "런타임속", None, None, "acceptus", "런타임정명",
    ]
    sheet.append([
        1, "관속식물류", "정명", "Runtimeus acceptus (A.) B.", "런타임정명", "B.", "2026",
        *ranks, "Y", "https://species.nibr.go.kr/species-detail/000000000101",
    ])
    sheet.append([
        "-", "관속식물류", "이명", "Runtimeus synonymus A.", "런타임정명", "A.", "2025",
        *ranks, "Y", "https://species.nibr.go.kr/species-detail/000000000102",
    ])
    workbook.save(path)
    return path


def _config(survey_type: str, workbook: Path, *, identification: bool = True) -> dict:
    config = make_base_config(survey_type, display_name=f"QCR {survey_type}")
    config["identification_enabled"] = identification
    config["canonical_reference_path"] = str(workbook)
    config["canonical_source_kind"] = "user_upload"
    return config


@pytest.fixture()
def canonical_workbook(tmp_path: Path) -> Path:
    return _write_fixture_workbook(tmp_path / "runtime-canonical.xlsx")


def _inspect(api, project_dir: str) -> dict:
    inspection = _require(api, "inspect_canonical_runtime_lookup")(project_dir)
    assert isinstance(inspection, dict)
    return inspection


def _run(api, project_dir: str, comparison_key: str, **kwargs) -> dict:
    result = _require(api, "exercise_canonical_runtime_lookup")(
        project_dir, comparison_key, **kwargs
    )
    assert isinstance(result, dict)
    return result


def _assert_no_fallback(result: dict) -> None:
    trace = result["trace"]
    assert trace["canonical_expression_operations"] == []
    assert trace["canonical_gpkg_expression_fallback_called"] is False
    assert trace["legacy_csv_branch_called"] is False


@pytest.mark.qgis
@pytest.mark.parametrize("survey_type", tuple(TYPE_LAYERS))
def test_ac_qcr_001_type1_to3_project_contains_minimal_relative_verified_runtime_resource(
    acceptance_api, canonical_workbook, tmp_path, survey_type
):
    result = _require(acceptance_api, "build_project")(
        _config(survey_type, canonical_workbook), str(tmp_path / survey_type)
    )
    assert result["success"] is True, result.get("error_message")
    project_dir = Path(result["project_dir"])
    inspection = _inspect(acceptance_api, str(project_dir))
    resource = inspection["resource"]
    provenance = inspection["provenance"]

    assert inspection["mode"] == "canonical_runtime_resource"
    assert resource["relative_path"] and not Path(resource["relative_path"]).is_absolute()
    resource_path = project_dir / resource["relative_path"]
    assert resource_path.is_file()
    assert resource_path.resolve().is_relative_to(project_dir.resolve())
    assert resource["byte_size"] == resource_path.stat().st_size
    assert resource["sha256"] == hashlib.sha256(resource_path.read_bytes()).hexdigest()
    for name in ("relative_path", "schema_revision", "pipeline_revision", "record_count", "byte_size", "sha256"):
        assert provenance[name] == resource[name]
    assert resource["schema_revision"] and resource["pipeline_revision"]
    assert resource["record_count"] == len(resource["records"]) == 2

    payload = resource_path.read_bytes()
    assert canonical_workbook.name.encode() not in payload
    assert str(canonical_workbook).encode() not in payload
    assert b"https://species.nibr.go.kr/species-detail/" not in payload
    assert not any(path.name == canonical_workbook.name for path in project_dir.rglob("*"))
    forbidden = {"source_url", "phylum_scientific_name", "class_scientific_name", "photo", "api_key"}
    for record in resource["records"]:
        assert {
            "scientific_name_without_authority", "accepted_ktsn", "korean_name", "scientific_name",
        }.issubset(record)
        assert forbidden.isdisjoint(record)

    with sqlite3.connect(result["gpkg_path"]) as connection:
        canonical_rows = connection.execute(
            f"SELECT scientific_name_without_authority, accepted_ktsn, korean_name, scientific_name "
            f"FROM {CANONICAL_TABLE} ORDER BY source_row"
        ).fetchall()
    assert canonical_rows == [
        (ACCEPTED_KEY, "000000000101", "런타임정명", "Runtimeus acceptus (A.) B."),
        (SYNONYM_KEY, "000000000101", "런타임정명", "Runtimeus synonymus A."),
    ]
    assert {
        (r["scientific_name_without_authority"], r["accepted_ktsn"], r["korean_name"], r["scientific_name"])
        for r in resource["records"]
    } == {
        (ACCEPTED_KEY, "000000000101", "런타임정명", "Runtimeus acceptus (A.) B."),
        (SYNONYM_KEY, "000000000101", "런타임정명", "Runtimeus acceptus (A.) B."),
    }


@pytest.mark.qgis
def test_ac_qcr_002_ac_qcr_003_accepted_and_synonym_use_resource_without_expression_lookup(
    acceptance_api, canonical_workbook, tmp_path
):
    result = _require(acceptance_api, "build_project")(
        _config("simple_inventory", canonical_workbook), str(tmp_path / "canonical")
    )
    assert result["success"] is True, result.get("error_message")
    inspection = _inspect(acceptance_api, result["project_dir"])
    source = inspection["canonical_lookup_source"]
    assert source.strip()
    for runtime_resource_operation in (
        "qpbLoadCanonicalRuntimeResource",
        "qpbCanonicalRuntimeResourcePath",
        "qpbCanonicalRuntimeResourceProvenance",
        "FileUtils.readFileContent",
    ):
        assert runtime_resource_operation in source
    for operation in ("layer_property(", "aggregate(", "get_feature("):
        assert operation not in source

    for key in (ACCEPTED_KEY, SYNONYM_KEY):
        lookup = _run(
            acceptance_api,
            result["project_dir"],
            key,
            forbid_expression_operations=True,
        )
        assert lookup["available"] is True
        assert lookup["matched"] is True
        assert lookup["ambiguous"] is False
        assert {name: lookup["candidate"][name] for name in EXPECTED} == EXPECTED
        assert lookup["write_back_input"] == EXPECTED
        assert inspection["resource"]["relative_path"] in lookup["trace"]["local_resource_reads"]
        _assert_no_fallback(lookup)


@pytest.mark.qgis
@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing_resource", "canonical_taxonomy_lookup_resource_unavailable"),
        ("unreadable_resource", "canonical_taxonomy_lookup_resource_unavailable"),
        ("unknown_schema", "canonical_taxonomy_lookup_resource_invalid"),
        ("truncated_record", "canonical_taxonomy_lookup_resource_invalid"),
        ("provenance_mismatch", "canonical_taxonomy_lookup_resource_invalid"),
        ("internal_consistency_failure", "canonical_taxonomy_lookup_resource_invalid"),
        ("blank_accepted_output", "canonical_taxonomy_lookup_resource_invalid"),
    ],
)
def test_ac_qcr_004_failure_matrix_is_fail_closed_without_expression_or_legacy_fallback(
    acceptance_api, canonical_workbook, tmp_path, mutation, reason
):
    result = _require(acceptance_api, "build_project")(
        _config("simple_inventory", canonical_workbook), str(tmp_path / "canonical")
    )
    assert result["success"] is True, result.get("error_message")
    lookup = _run(
        acceptance_api, result["project_dir"], ACCEPTED_KEY,
        mutation=mutation, forbid_expression_operations=True,
    )
    assert lookup["available"] is False
    assert lookup["reason"] == reason
    assert lookup["matched"] is False and lookup["ambiguous"] is False
    assert lookup["candidate"] is None and lookup["write_back_input"] is None
    _assert_no_fallback(lookup)


@pytest.mark.qgis
def test_ac_qcr_004_normal_no_match_and_ambiguity_do_not_guess_or_write_back(
    acceptance_api, canonical_workbook, tmp_path
):
    result = _require(acceptance_api, "build_project")(
        _config("simple_inventory", canonical_workbook), str(tmp_path / "canonical")
    )
    assert result["success"] is True, result.get("error_message")
    no_match = _run(acceptance_api, result["project_dir"], "Runtimeus absentus")
    assert no_match["available"] is True
    assert no_match["matched"] is False and no_match["ambiguous"] is False
    assert no_match["candidate"] is None and no_match["write_back_input"] is None
    _assert_no_fallback(no_match)

    ambiguous = _run(
        acceptance_api, result["project_dir"], ACCEPTED_KEY, mutation="ambiguous_accepted_group"
    )
    assert ambiguous["available"] is True
    assert ambiguous["matched"] is False and ambiguous["ambiguous"] is True
    assert ambiguous["candidate"] is None and ambiguous["write_back_input"] is None
    _assert_no_fallback(ambiguous)


@pytest.mark.qgis
def test_ac_qcr_005_ac_qcr_006_preserve_gpkg_and_legacy_but_do_not_create_resource_for_boundaries(
    acceptance_api, canonical_workbook, tmp_path
):
    build = _require(acceptance_api, "build_project")
    canonical = build(_config("simple_inventory", canonical_workbook), str(tmp_path / "canonical"))
    assert canonical["success"] is True, canonical.get("error_message")
    layers = _require(acceptance_api, "inspect_canonical_reference_layers")(canonical["project_dir"])
    assert layers[CANONICAL_TABLE]["display_name"] == CANONICAL_LAYER
    inspection = _inspect(acceptance_api, canonical["project_dir"])
    assert inspection["report_taxonomy_source"] == {
        "table": CANONICAL_TABLE, "uses_runtime_resource": False,
    }

    for survey_type in TYPE_LAYERS:
        disabled = build(
            _config(survey_type, canonical_workbook, identification=False),
            str(tmp_path / f"disabled-{survey_type}"),
        )
        assert disabled["success"] is True, disabled.get("error_message")
        assert _inspect(acceptance_api, disabled["project_dir"])["mode"] == "identification_disabled"
        assert _inspect(acceptance_api, disabled["project_dir"]).get("resource") is None

    type4 = build(_config("vegetation_mapping", canonical_workbook), str(tmp_path / "type4"))
    assert type4["success"] is True, type4.get("error_message")
    assert _inspect(acceptance_api, type4["project_dir"])["mode"] == "type4_not_applicable"
    assert _inspect(acceptance_api, type4["project_dir"]).get("resource") is None

    legacy_config = make_base_config("simple_inventory", display_name="QCR legacy")
    legacy_config.pop("canonical_reference_path", None)
    legacy_config["identification_enabled"] = True
    legacy_config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    legacy_config["_test_reference_data_dir"] = str(REFERENCE_DATA_VALID_SAMPLE_DIR)
    legacy = build(legacy_config, str(tmp_path / "legacy"))
    assert legacy["success"] is True, legacy.get("error_message")
    legacy_inspection = _inspect(acceptance_api, legacy["project_dir"])
    assert legacy_inspection["mode"] == "legacy_csv"
    assert legacy_inspection.get("resource") is None
    assert legacy_inspection["legacy_csv_branch_configured"] is True


@pytest.mark.qgis
@pytest.mark.parametrize("stage", ("materialization", "schema_validation", "provenance_write"))
def test_ac_qcr_006_resource_stage_failures_do_not_promote_partial_projects(
    acceptance_api, canonical_workbook, tmp_path, stage
):
    config = _config("simple_inventory", canonical_workbook)
    config["_test_force_canonical_runtime_resource_failure"] = stage
    output = tmp_path / stage
    result = _require(acceptance_api, "build_project")(config, str(output))
    assert result["success"] is False
    assert result.get("failed_stage") == "canonical_runtime_lookup_resource"
    assert not output.exists() or not any(output.iterdir())


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-QCR-007 is a release gate on a physical iPhone running QField. Transfer an unchanged "
        "new canonical Type 1–3 project, use a real response whose scientificNameWithoutAuthor "
        "matches the runtime resource, press 사진으로 동정하기, and select the displayed candidate. "
        "Record only app build, project build/ID, QField version, iPhone/OS, comparison key, "
        "whether canonical_taxonomy_lookup_failed was absent, and the resulting Korean name/raw "
        "scientific name/KTSN availability. Do not record API keys, photo/image bytes, or precise "
        "coordinates. Desktop QGIS or a simulated QField-shaped run is not this gate."
    )
)
def test_ac_qcr_007_iphone_qfield_release_device_gate():
    raise AssertionError("manual device gate must remain skipped in automated runs")
