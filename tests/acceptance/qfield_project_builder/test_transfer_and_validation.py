"""Portability, transfer instructions, and manifest-based validation (Section 12, Section 18.4).

Covers:
- AC-QPB-024: a project folder copied to a new local path opens successfully.
- AC-QPB-025: computer -> phone -> computer round trip with real field edits reopens correctly.
  Requires a physical iOS/Android device running QField; marked `device` (not automated here).
- AC-QPB-026: the supported transfer workflow never invokes/requires QFieldSync packaging.
- AC-QPB-027: MANIFEST.json detects a missing attachment/plugin/database/basemap file.
- AC-QPB-028: macOS->iOS, Windows->iOS, Windows->Android, macOS->Android transfer paths function
  correctly on the target platform. Requires physical devices across OS/QField combinations;
  marked `device` (not automated here).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis


# --- AC-QPB-024 -----------------------------------------------------------------

def test_ac024_project_folder_copied_to_new_local_path_opens_successfully(
    acceptance_api, built_project_by_type, tmp_path
):
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")

    new_path = tmp_path / "some" / "very" / "different" / "location"
    shutil.copytree(result["project_dir"], new_path)

    report = acceptance_api.validate_project(str(new_path))
    assert report["opens_without_repair_warning"] is True, report["issues"]
    assert report["missing_layer_warning"] is False, report["issues"]


# --- AC-QPB-025 (device-dependent; not automated here) -------------------------

@pytest.mark.device
@pytest.mark.skip(
    reason=(
        "AC-QPB-025 requires copying the generated project to a physical smartphone running "
        "QField, editing data/photos in QField, closing, and copying back — this cannot be "
        "automated by this harness. Documented here as a required manual QA test case; run "
        "manually per README_TRANSFER_KO.md before each release."
    )
)
def test_ac025_computer_to_phone_to_computer_round_trip_preserves_edits():
    raise AssertionError("should never run while skipped — see skip reason")


# --- AC-QPB-026 -----------------------------------------------------------------

def test_ac026_transfer_workflow_never_requires_qfieldsync(acceptance_api, built_project_by_type):
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")

    for path in Path(result["project_dir"]).rglob("*"):
        assert "qfieldsync" not in path.name.lower(), (
            f"no QFieldSync-specific artifact may be required in the delivered project: {path}"
        )

    readme_path = Path(result["project_dir"]) / "README_TRANSFER_KO.md"
    assert readme_path.exists(), "FR-QPB-093: README_TRANSFER_KO.md must exist"
    readme_text = readme_path.read_text(encoding="utf-8")
    lowered = readme_text.lower()
    assert "qfieldsync" in lowered, (
        "FR-QPB-093: the transfer notice must explicitly warn against packaging with QFieldSync"
    )


def test_readme_transfer_ko_covers_required_instructions(built_project_by_type):
    """Supports AC-QPB-026/AC-QPB-028: content checks for the required transfer notice.

    FR-QPB-093 requires the notice to: warn against QFieldSync packaging; instruct copying the
    entire folder (not just the .gpkg); instruct opening in QField; instruct copying the whole
    folder back after fieldwork; warn against renaming/moving files inside the folder; and cover
    both Android and iOS in non-technical language.
    """
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")
    readme_text = (Path(result["project_dir"]) / "README_TRANSFER_KO.md").read_text(
        encoding="utf-8"
    )
    lowered = readme_text.lower()
    assert "qfieldsync" in lowered
    assert "qfield" in lowered
    assert "android" in lowered
    assert "ios" in lowered
    assert (
        ".gpkg" in lowered or "지오패키지" in readme_text or "geopackage" in lowered
    ), "expected an instruction not to copy only the GeoPackage"


# --- AC-QPB-027 -----------------------------------------------------------------

@pytest.mark.parametrize(
    "corrupt_kind",
    ["attachment", "database", "basemap"],
)
def test_ac027_manifest_detects_a_missing_required_file(
    acceptance_api, tmp_path, corrupt_kind
):
    if corrupt_kind == "basemap":
        config = make_base_config("simple_inventory")
        config["basemap"] = {
            "mode": "offline",
            "vworld_api_key": "FAKE",
            "layer": "Base",
            "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
            "min_zoom": 10,
            "max_zoom": 11,
            "tile_source": {"fake": {"mode": "success", "tile_bytes": 4000}},
        }
    else:
        config = make_base_config("simple_inventory")

    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    if corrupt_kind == "database":
        Path(result["gpkg_path"]).unlink()
    elif corrupt_kind == "basemap":
        mbtiles_files = list(Path(result["basemap_dir"]).glob("*.mbtiles"))
        assert mbtiles_files, "expected a generated .mbtiles file to remove"
        mbtiles_files[0].unlink()
    elif corrupt_kind == "attachment":
        # Record a real attachment (so MANIFEST.json/validation has something concrete to
        # expect), confirm it validates clean, then remove the file out from under the project
        # to simulate the "before transfer" missing-attachment scenario (FR-QPB-092).
        attachments_dir = Path(result["attachments_dir"])
        attachments_dir.mkdir(parents=True, exist_ok=True)
        relative_photo_path = "attachments/leaf_ac027.jpg"
        (Path(result["project_dir"]) / relative_photo_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        (Path(result["project_dir"]) / relative_photo_path).write_bytes(b"fake-jpeg-bytes")
        outcome = acceptance_api.attempt_feature_save(
            result["project_dir"],
            "inventory_observation",
            {
                "surveyor": "Field Researcher",
                "selected_scientific_name": "Test taxon",
                "leaf_photo_path": relative_photo_path,
            },
            geometry_wkt="POINT(127.0 37.0)",
        )
        assert outcome["accepted"], outcome

        clean_report = acceptance_api.validate_project(result["project_dir"])
        assert not any(
            issue["code"] == "missing_manifest_file" for issue in clean_report["issues"]
        ), f"attachment file is present; must not be flagged missing yet: {clean_report['issues']}"

        (Path(result["project_dir"]) / relative_photo_path).unlink()

    report = acceptance_api.validate_project(result["project_dir"])
    codes = {issue["code"] for issue in report["issues"]}
    assert "missing_manifest_file" in codes or any(
        "missing" in issue["code"] for issue in report["issues"]
    ), (
        f"AC-QPB-027: a missing {corrupt_kind} file referenced by MANIFEST.json must be "
        f"detected; got issues: {report['issues']}"
    )


# --- AC-QPB-028 (device-dependent; not automated here) -------------------------

@pytest.mark.device
@pytest.mark.parametrize(
    "transfer_path",
    ["macOS_to_iOS", "Windows_to_iOS", "Windows_to_Android", "macOS_to_Android"],
)
@pytest.mark.skip(
    reason=(
        "AC-QPB-028 requires exercising each of macOS->iOS, Windows->iOS, Windows->Android, and "
        "macOS->Android end-to-end on real hardware running QField — not automatable by this "
        "harness. Documented as a required manual QA matrix (NFR-QPB-031); run manually before "
        "each release, alongside the O-9 version-matrix audit."
    )
)
def test_ac028_transfer_path_functions_correctly_on_target_platform(transfer_path):
    raise AssertionError("should never run while skipped — see skip reason")
