"""D-89 acceptance coverage for the distributed filtered-reference bundle.

The release artifact checks are intentionally filesystem-level: a PyInstaller ``.app``/onedir
bundle is a normal directory, so inspecting its extracted contents avoids inventing a product API
and catches accidental ``datas=[("storage/reference", ...)]`` regressions directly.

The release-artifact checks are the current packaging boundary; only the two filtered-only project
build checks retain the pre-D-95 compatibility seam and are explicitly marked
``legacy_compatibility`` below.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from .conftest import REFERENCE_DATA_VALID_SAMPLE_DIR, REPO_ROOT, make_base_config

pytestmark = pytest.mark.qgis

FILTERED_RELATIVE = Path("storage") / "reference" / "filtered"
KTSN_LOOKUP_NAME = "ktsn_lookup.csv"
RAW_TABLE_RELATIVE = Path("storage") / "reference" / "tables"
RASTER_RELATIVE = (
    Path("storage") / "reference" / "rasters" / "bce_inverse_corrected_probability_maps"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_root(app_path: Path) -> Path:
    """Return the PyInstaller data root for either macOS ``.app`` or onedir output."""
    candidates = [
        app_path / "Contents" / "Resources",
        app_path,
    ]
    for candidate in candidates:
        if (candidate / FILTERED_RELATIVE / KTSN_LOOKUP_NAME).is_file():
            return candidate
    matches = list(app_path.rglob(KTSN_LOOKUP_NAME))
    for match in matches:
        if match.parent.name == "filtered":
            return match.parents[3]
    raise AssertionError(
        f"D-89: package has no {FILTERED_RELATIVE / KTSN_LOOKUP_NAME}: inspected {app_path}"
    )


def _packaged_app_path() -> Path | None:
    configured = os.environ.get("QPB_PACKAGED_APP_PATH")
    if configured:
        path = Path(configured)
    else:
        path = REPO_ROOT / "dist" / "FieldBuild Kit.app"
    return path if path.exists() else None


def _manifest_candidates(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.json")
        if "manifest" in path.name.lower() or "bundle" in path.name.lower()
    )


def _manifest_text(root: Path) -> tuple[Path, str]:
    candidates = _manifest_candidates(root)
    assert candidates, "D-89: filtered bundle must ship a machine-readable manifest"
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if "ktsn_lookup.csv" in text:
            return path, text
    raise AssertionError("D-89: no shipped manifest records ktsn_lookup.csv")


def test_ac130_packaging_spec_stages_filtered_data_instead_of_raw_reference_tree():
    spec_text = (REPO_ROOT / "packaging" / "qfield_builder.spec").read_text(encoding="utf-8")
    assert "storage/reference/filtered" in spec_text.replace("\\", "/"), (
        "FR-QPB-135/DR-QPB-073: PyInstaller must receive the validated filtered bundle"
    )
    assert '(str(REPO_ROOT / "storage" / "reference"), "storage/reference")' not in spec_text, (
        "D-89: the complete raw storage/reference tree must not be copied into the app"
    )


def test_ac130_release_package_contains_only_filtered_tables_and_consistent_manifest():
    app_path = _packaged_app_path()
    if app_path is None:
        pytest.skip(
            "release artifact not present; set QPB_PACKAGED_APP_PATH to a built .app/onedir bundle"
        )
    root = _package_root(app_path)
    filtered = root / FILTERED_RELATIVE
    lookup = filtered / KTSN_LOOKUP_NAME
    header = lookup.read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    assert header == ["ktsn", "taxon_full_nm", "taxon_kor_nm", "taxon_jm_nm", "correct_list"]
    assert sum(1 for _ in lookup.open(encoding="utf-8-sig")) - 1 == 20_914

    filtered_files = [path for path in filtered.rglob("*") if path.is_file()]
    assert any("accepted" in path.name.lower() for path in filtered_files)
    assert any("nibr" in path.name.lower() for path in filtered_files)

    raw_tables = root / RAW_TABLE_RELATIVE
    assert not raw_tables.exists(), "D-89: raw storage/reference/tables must be absent"
    assert not list(root.rglob("tb_leco_nib_ktsn_dtl_gat.csv"))
    assert not list(root.rglob("2025년 국가생물종목록_v1.0.xlsx"))
    assert not any(
        path.suffix.lower() in {".csv", ".xlsx", ".xls"}
        for path in raw_tables.rglob("*")
        if path.is_file()
    )

    _, manifest_text = _manifest_text(root)
    manifest = json.loads(manifest_text)
    flattened = json.dumps(manifest, ensure_ascii=False)
    for required in ("ktsn_lookup.csv", "accepted", "nibr", "20914"):
        assert required.lower() in flattened.lower()
    for artifact in filtered_files:
        digest = _sha256(artifact)
        assert digest in flattened, f"D-89: manifest does not record hash for {artifact.name}"


def test_ac131_release_package_retains_every_probability_raster_byte_for_byte(
    real_probability_raster_dir,
):
    app_path = _packaged_app_path()
    if app_path is None:
        pytest.skip("release artifact not present; set QPB_PACKAGED_APP_PATH to a built bundle")
    root = _package_root(app_path)
    source_files = sorted(real_probability_raster_dir.glob("*.tif"))
    packaged_dir = root / RASTER_RELATIVE
    packaged_files = sorted(packaged_dir.glob("*.tif"))
    assert {path.name for path in packaged_files} == {path.name for path in source_files}
    for source in source_files:
        packaged = packaged_dir / source.name
        assert _sha256(packaged) == _sha256(source), f"D-89: raster changed: {source.name}"


def _filtered_only_fixture(tmp_path: Path) -> Path:
    """Create a minimal filtered-only input, proving project generation need not see raw tables."""
    root = tmp_path / "filtered_reference"
    filtered = root / "filtered"
    filtered.mkdir(parents=True)
    # D-89's release validator treats the verified final row count as part of the artifact
    # contract. Generate a deterministic all-accepted synthetic bundle at that exact size, while
    # keeping each file small enough for this acceptance fixture and avoiding any raw source.
    count = 20_914
    lookup_lines = ["ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list"]
    accepted_lines = ["ktsn,taxon_kor_nm,taxon_full_nm"]
    nibr_lines = []
    for index in range(count):
        ktsn = f"9000{index:09d}"
        scientific = f"Testus terminalis{index}"
        korean = f"최종정명종{index}"
        lookup_lines.append(f"{ktsn},{scientific},{korean},정명,[]")
        accepted_lines.append(f"{ktsn},{korean},{scientific}")
        nibr_lines.append(ktsn)
    (filtered / KTSN_LOOKUP_NAME).write_text("\n".join(lookup_lines) + "\n", encoding="utf-8")
    (filtered / "accepted_name_lookup.csv").write_text(
        "\n".join(accepted_lines) + "\n", encoding="utf-8"
    )
    (filtered / "nibr_accepted_ktsn_list.txt").write_text(
        "\n".join(nibr_lines) + "\n", encoding="utf-8"
    )
    (filtered / "bundle_manifest.json").write_text(
        json.dumps(
            {
                "pipeline_revision": "FR-QPB-118-D48",
                "artifacts": {
                    "ktsn_lookup.csv": {
                        "row_count": count,
                        "sha256": _sha256(filtered / KTSN_LOOKUP_NAME),
                    },
                    "accepted_name_lookup.csv": {
                        "row_count": count,
                        "sha256": _sha256(filtered / "accepted_name_lookup.csv"),
                    },
                    "nibr_accepted_ktsn_list.txt": {
                        "row_count": count,
                        "sha256": _sha256(filtered / "nibr_accepted_ktsn_list.txt"),
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raster_target = root / "rasters" / "bce_inverse_corrected_probability_maps"
    raster_target.mkdir(parents=True)
    source_raster = next(
        (
            REFERENCE_DATA_VALID_SAMPLE_DIR
            / "rasters"
            / "bce_inverse_corrected_probability_maps"
        ).glob("*.tif")
    )
    shutil.copyfile(source_raster, raster_target / source_raster.name)
    return root


@pytest.mark.legacy_compatibility
def test_ac131_filtered_only_project_build_emits_no_raw_table_sources(
    acceptance_api, tmp_path
):
    reference_root = _filtered_only_fixture(tmp_path)
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = True
    config["_test_reference_data_dir"] = str(reference_root)
    # The filtered-only input is the retained explicit compatibility seam; do not let the
    # shared canonical candidate mask that boundary.
    config.pop("canonical_reference_path", None)
    config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    output = tmp_path / "filtered_project"
    result = acceptance_api.build_project(config, str(output))
    assert result["success"] is True, result
    project = Path(result["project_dir"])
    assert (project / "reference" / "ktsn_lookup.csv").is_file()
    assert (project / "reference" / "nibr_accepted_ktsn_list.txt").is_file()
    assert not (project / "reference" / "tables").exists()
    assert not list(project.rglob("*.xlsx"))
    assert not list(project.rglob("tb_leco_nib_ktsn_dtl_gat.csv"))


@pytest.mark.parametrize("failure", ["missing_lookup", "invalid_manifest"])
@pytest.mark.legacy_compatibility
def test_ac132_missing_or_invalid_filtered_artifact_fails_without_partial_project(
    acceptance_api, tmp_path, failure
):
    reference_root = _filtered_only_fixture(tmp_path)
    filtered = reference_root / "filtered"
    if failure == "missing_lookup":
        (filtered / KTSN_LOOKUP_NAME).unlink()
    else:
        (filtered / "bundle_manifest.json").write_text("{not-json", encoding="utf-8")
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = True
    config["_test_reference_data_dir"] = str(reference_root)
    config.pop("canonical_reference_path", None)
    config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    output = tmp_path / f"failed_{failure}"
    result = acceptance_api.build_project(config, str(output))
    assert result["success"] is False, result
    assert not output.exists(), "D-89/AC-QPB-132: failed validation must not promote partial output"
