"""D-95 generated-project, lookup/write-back, and compatibility acceptance checks.

The module is QGIS-marked because it inspects the generated GeoPackage/QGIS project and exercises
the existing feature-save seam. Pure ingestion, matching, report, and wizard checks live in
``test_d95_canonical_ktsn_reference.py`` so they remain useful without PyQGIS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from .conftest import REFERENCE_DATA_VALID_SAMPLE_DIR, REPO_ROOT, make_base_config, open_gpkg, user_tables

PRIVATE_WORKBOOK = os.environ.get("QPB_PRIVATE_REFERENCE_WORKBOOK")
pytestmark = [pytest.mark.qgis, pytest.mark.skipif(
    not PRIVATE_WORKBOOK, reason="optional historical dataset: set QPB_PRIVATE_REFERENCE_WORKBOOK"
)]
CANONICAL = Path(PRIVATE_WORKBOOK or "__private_workbook_not_supplied__.xlsx")
OLD_SOURCE_NAMES = {
    "tb_leco_nib_ktsn_dtl_gat.csv",
    "2025년 국가생물종목록_v1.0.xlsx",
}


def _require(acceptance_api, name: str):
    function = getattr(acceptance_api, name, None)
    if function is None:
        pytest.skip(f"qfield_builder.acceptance_api.{name}() is not implemented yet")
    return function


@pytest.fixture()
def inspect_reference_layers(acceptance_api):
    return _require(acceptance_api, "inspect_canonical_reference_layers")


def _build_canonical(acceptance_api, tmp_path: Path, survey_type: str = "simple_inventory"):
    config = make_base_config(survey_type)
    config["identification_enabled"] = False
    # The test override points at the real scaffold root; D-95 requires the workbook under its
    # exact canonical path and does not authorize selecting either legacy source instead.
    config["canonical_reference_path"] = str(CANONICAL)
    return acceptance_api.build_project(config, str(tmp_path / survey_type))


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots"])
def test_ac140_new_type1_to3_projects_create_both_reference_layers_and_preserve_schema(
    acceptance_api, inspect_reference_layers, tmp_path, survey_type
):
    result = _build_canonical(acceptance_api, tmp_path, survey_type)
    assert result["success"] is True, result.get("error_message")
    report = inspect_reference_layers(result["project_dir"])

    taxonomy = report["ktsn_taxonomy_reference"]
    assert taxonomy["display_name"] == "식물 분류 참조표"
    assert taxonomy["read_only"] is True
    assert taxonomy["identifiable"] is False
    assert taxonomy["row_count"] == 8_042
    assert taxonomy["fields"] == [
        "ktsn", "source_no", "taxon_status", "korean_name", "scientific_name",
        "scientific_name_normalized", "scientific_name_without_authority", "authority",
        "naming_year", "phylum_scientific_name", "phylum_korean_name",
        "class_scientific_name", "class_korean_name", "order_scientific_name",
        "order_korean_name", "family_scientific_name", "family_korean_name",
        "genus_scientific_name", "genus_korean_name", "accepted_ktsn", "source_url",
        "content_available", "source_row",
    ]
    assert taxonomy["indexes"] >= {
        "ktsn", "accepted_ktsn", "scientific_name_without_authority"
    }

    accepted = report["ktsn_accepted_name_lookup"]
    assert accepted["display_name"] == "인정 국명 조회표"
    assert accepted["row_count"] == 4_673
    assert accepted["taxon_status_values"] == ["정명"]
    assert report["reference_group"][:2] == [
        "ktsn_taxonomy_reference",
        "ktsn_accepted_name_lookup",
    ]


def test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources(
    acceptance_api, tmp_path
):
    result = _build_canonical(acceptance_api, tmp_path)
    assert result["success"] is True, result.get("error_message")
    project_dir = Path(result["project_dir"])
    assert not any(path.name in OLD_SOURCE_NAMES for path in project_dir.rglob("*"))
    assert not (project_dir / "reference" / "tables").exists()
    assert not any(path.name == CANONICAL.name for path in project_dir.rglob("*"))

    qml_sources = [path.read_text(encoding="utf-8") for path in project_dir.glob("*.qml")]
    assert qml_sources, "the unconditional project-plugin/report sidecar must be present"
    report_source = "\n".join(qml_sources)
    for token in ("ktsn_taxonomy_reference", "Phylum", "Class", "Order", "Family", "Genus"):
        assert token in report_source, (
            f"FR-QPB-141: generated report/plugin source must expose taxonomy aggregation for "
            f"{token}"
        )
    assert "taxonomy_reference_unavailable" in report_source

    manifest = json.loads((project_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    provenance = manifest["source_provenance"]
    assert provenance["source_filename"] == CANONICAL.name
    assert provenance["source_kind"] == "bundled_candidate"
    assert provenance["sheet_name"] == "Data Sheet"
    assert provenance["header_rows"] == [1, 2]
    assert provenance["source_row_count"] == 8_042
    assert provenance["sha256"]
    assert provenance["byte_size"] == CANONICAL.stat().st_size
    assert "dataset_version" not in provenance


def test_ac141_missing_canonical_source_fails_before_project_promotion_without_legacy_fallback(
    acceptance_api, tmp_path
):
    reference_root = tmp_path / "reference-without-canonical"
    (reference_root / "tables").mkdir(parents=True)
    (reference_root / "rasters" / "bce_inverse_corrected_probability_maps").mkdir(
        parents=True
    )
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = False
    config["_test_reference_data_dir"] = str(reference_root)
    output = tmp_path / "not-promoted"

    result = acceptance_api.build_project(config, str(output))
    assert result["success"] is False
    assert result.get("error_code")
    assert result.get("error_message")
    assert not output.exists() or not any(output.iterdir())


def test_ac142_canonical_match_values_write_back_to_existing_observation_fields_without_relation_change(
    acceptance_api, tmp_path
):
    result = _build_canonical(acceptance_api, tmp_path)
    assert result["success"] is True, result.get("error_message")
    project_dir = Path(result["project_dir"])
    inspect_relations = getattr(acceptance_api, "inspect_relations", None)
    assert callable(inspect_relations), "the existing relation inspection seam must remain available"
    relations_before = inspect_relations(str(project_dir))
    outcome = acceptance_api.attempt_feature_save(
        str(project_dir),
        "inventory_observation",
        {
            "surveyor": "tester",
            "selected_korean_name": "긴다람쥐꼬리",
            "selected_scientific_name": "Huperzia jejuensis B.-Y Sun & J. Lim",
            "selected_ktsn": "120000059515",
        },
        geometry_wkt="POINT(127.0 37.0)",
    )
    assert outcome["accepted"] is True, outcome
    assert inspect_relations(str(project_dir)) == relations_before
    with open_gpkg(result["gpkg_path"]) as connection:
        table = "inventory_observation"
        assert table in user_tables(connection)
        row = connection.execute(
            f"SELECT selected_korean_name, selected_scientific_name, selected_ktsn "
            f"FROM {table} ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
    assert row == ("긴다람쥐꼬리", "Huperzia jejuensis B.-Y Sun & J. Lim", "120000059515")


@pytest.mark.legacy_compatibility
def test_ac141_legacy_project_without_taxonomy_reference_remains_readable(
    acceptance_api, tmp_path
):
    # This is an explicit compatibility build, not the shared canonical fixture.  It verifies
    # that a pre-D-95 project remains readable without making a new build silently fall back to
    # either legacy source when canonical input is absent.
    config = make_base_config("simple_inventory")
    config.pop("canonical_reference_path", None)
    config["_test_reference_data_dir"] = str(REFERENCE_DATA_VALID_SAMPLE_DIR)
    config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    legacy = acceptance_api.build_project(config, str(tmp_path / "legacy-project"))
    assert legacy["success"] is True, legacy.get("error_message")
    validation = acceptance_api.validate_project(legacy["project_dir"])
    assert validation["success"] is True, validation
    assert "taxonomy_reference_unavailable" not in validation.get("issues", [])
