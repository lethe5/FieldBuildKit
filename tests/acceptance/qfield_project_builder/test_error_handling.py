"""Error handling and atomicity (Section 15, Section 18.5).

Covers:
- AC-QPB-030: an existing output directory is never silently overwritten; a rename or
  explicit replace-with-backup path is offered instead. Covers both a non-empty pre-existing
  directory (sentinel-file case) and an empty pre-existing directory (E-QPB-008/AC-QPB-030 carry
  no emptiness qualifier, so both must be rejected the same way). No explicit "replace with
  backup" operation currently exists anywhere in the implementation to test separately (see
  traceability notes).
- AC-QPB-031: a build that fails partway through leaves no partially generated project at the
  final output path.
- AC-QPB-032: packaged Windows/macOS installers start the application and complete the wizard —
  requires real platform installers on real target OS installs; marked `manual` (not automated
  here), and additionally blocked on the exact supported-OS-version matrix (Open Question O-9).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import SAMPLE_INVALID_POLYGON_WKT, make_base_config

pytestmark = pytest.mark.qgis


# --- AC-QPB-030 -----------------------------------------------------------------

def test_ac030_existing_output_directory_is_never_silently_overwritten(acceptance_api, tmp_path):
    out_dir = tmp_path / "existing_project"
    out_dir.mkdir()
    sentinel = out_dir / "sentinel.txt"
    sentinel.write_text("do not touch")

    config = make_base_config("simple_inventory")
    result = acceptance_api.build_project(config, str(out_dir))

    assert result["success"] is False, (
        "E-QPB-008/AC-QPB-030: building into an existing directory must not silently succeed "
        "by overwriting it"
    )
    assert result.get("error_code") in (
        "output_dir_exists",
        "output_directory_exists",
    ) or "exists" in (result.get("error_code") or "").lower()
    assert sentinel.exists() and sentinel.read_text() == "do not touch", (
        "the pre-existing directory's contents must be left untouched"
    )


def test_ac030_existing_empty_output_directory_is_never_silently_overwritten(acceptance_api, tmp_path):
    """E-QPB-008/AC-QPB-030 edge case: an *already-existing but empty* output directory must be
    rejected exactly like a non-empty one. Neither E-QPB-008 ("If the chosen output directory
    already exists, the application must not overwrite it silently...") nor AC-QPB-030's own
    wording ("Given an existing directory at the chosen output path...") carries an emptiness
    qualifier -- an empty directory is still pre-existing, user-owned filesystem state, and a
    normal build attempt must not silently delete, replace, or populate it."""
    out_dir = tmp_path / "existing_empty_project"
    out_dir.mkdir()

    config = make_base_config("simple_inventory")
    result = acceptance_api.build_project(config, str(out_dir))

    assert result["success"] is False, (
        "E-QPB-008/AC-QPB-030: building into an already-existing directory must not silently "
        "succeed by overwriting it, even when that directory happens to be empty"
    )
    assert result.get("error_code") in (
        "output_dir_exists",
        "output_directory_exists",
    ) or "exists" in (result.get("error_code") or "").lower()
    assert out_dir.exists(), (
        "the pre-existing (empty) output directory must not be deleted by a rejected build"
    )
    assert not any(out_dir.iterdir()), (
        "the pre-existing (empty) output directory must not be populated with the new "
        "project's files (.qgs, .gpkg, attachments/, etc.) by a rejected build"
    )


# --- AC-QPB-031 -----------------------------------------------------------------

def test_ac031_a_failed_build_leaves_no_partial_project_at_the_final_path(acceptance_api, tmp_path):
    """Uses invalid input geometry (FR-QPB-026/028) to force a mid-build failure deterministically."""
    config = make_base_config("temporary_plots")
    config["sites"] = [{"site_name": "Invalid Site", "geom_wkt": SAMPLE_INVALID_POLYGON_WKT}]

    out_dir = tmp_path / "out"
    result = acceptance_api.build_project(config, str(out_dir))

    assert result["success"] is False
    assert not out_dir.exists() or not any(out_dir.iterdir()), (
        "AC-QPB-031/E-QPB-009: no partially generated project may exist at the final path "
        "after a failed build"
    )


def test_invalid_geometry_is_reported_not_silently_repaired(acceptance_api, tmp_path):
    """FR-QPB-028/E-QPB-011: invalid geometry must be reported, repaired only with explicit
    user approval — never silently auto-repaired."""
    config = make_base_config("temporary_plots")
    config["sites"] = [{"site_name": "Invalid Site", "geom_wkt": SAMPLE_INVALID_POLYGON_WKT}]

    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"] is False
    assert result.get("error_code"), "expected a structured error_code for invalid geometry"
    message = (result.get("error_message") or "").lower()
    assert "geometry" in message or "invalid" in message, (
        f"expected the error to be reported as an invalid-geometry issue, got: {result}"
    )


def test_required_text_field_rejects_empty_or_whitespace_only(acceptance_api, built_project_by_type):
    """E-QPB-012/DR-QPB-013: a required text field submitted empty/whitespace-only is rejected."""
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")
    for bad_value in ["", "   "]:
        outcome = acceptance_api.attempt_feature_save(
            result["project_dir"],
            "inventory_observation",
            {"surveyor": bad_value, "selected_scientific_name": "Test taxon"},
            geometry_wkt="POINT(127.0 37.0)",
        )
        assert outcome["accepted"] is False, (
            f"empty/whitespace-only surveyor {bad_value!r} must be rejected, got {outcome}"
        )


# --- AC-QPB-032 (manual/hardware-dependent; not automated here) ---------------

@pytest.mark.manual
@pytest.mark.parametrize("target_os", ["Windows", "macOS"])
@pytest.mark.skip(
    reason=(
        "AC-QPB-032 requires installing and launching the actual packaged Windows/macOS "
        "application on its target OS and completing the wizard — not automatable by this "
        "harness, and additionally the exact supported OS versions are not yet pinned "
        "(Open Question O-9). Documented as a required manual release-QA test case."
    )
)
def test_ac032_packaged_application_starts_and_completes_wizard_on_target_os(target_os):
    raise AssertionError("should never run while skipped — see skip reason")
