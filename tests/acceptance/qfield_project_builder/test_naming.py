"""Project naming: project_display_name / project_slug / project_id (Section 6.1).

Covers:
- AC-QPB-059: Unicode/space/punctuation display name -> valid ASCII slug, used for generated
  folder/file names.
- AC-QPB-060: blank / path-traversal / Windows-reserved names are rejected, not silently
  sanitized into something unsafe.
- AC-QPB-061: two different generated projects get distinct, valid project_id UUID v4 values,
  independent of project_display_name/project_slug.

These are tested as pure, standalone functions (derive_project_slug) wherever possible, so that
naming-rule coverage does not require a working QGIS installation (naming validation is
orthogonal to the QGIS/PyQGIS runtime dependency). AC-QPB-061 additionally requires a full build
(to observe two independently generated project_id values), so it is marked `qgis`.
"""
from __future__ import annotations

import re
import uuid

import pytest

from .conftest import make_base_config

ASCII_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


# --- AC-QPB-059 -------------------------------------------------------------

@pytest.mark.parametrize(
    "display_name",
    [
        "테스트 프로젝트 1",  # Korean + space + digit
        "Café Survey — 2026",  # accented Latin + punctuation + em dash
        "My  Project!! (v2)",  # ASCII punctuation/whitespace
        "  leading and trailing spaces  ",
        "植生調査プロジェクト",  # Japanese
    ],
)
def test_slug_is_derived_and_ascii_safe_for_unicode_display_names(acceptance_api, display_name):
    """AC-QPB-059: Unicode/space/punctuation names must yield a valid ASCII slug."""
    result = acceptance_api.derive_project_slug(display_name)
    assert result.get("ok") is True, f"expected a derivable slug for {display_name!r}: {result}"
    slug = result["slug"]
    assert ASCII_SLUG_RE.match(slug), f"slug {slug!r} is not ASCII-safe/within length limits"


def test_slug_never_exceeds_64_characters(acceptance_api):
    """FR-QPB-021: project_slug must not exceed 64 characters, even for a very long name."""
    long_name = "a very long project display name " * 5
    result = acceptance_api.derive_project_slug(long_name)
    assert result.get("ok") is True
    assert len(result["slug"]) <= 64


# --- AC-QPB-060 -------------------------------------------------------------

@pytest.mark.parametrize(
    "display_name",
    [
        "",
        "   ",
        "..",
        "../../etc/passwd",
        "a/../b",
        "a\\..\\b",
        "/",
        "\\",
    ],
)
def test_blank_and_path_traversal_names_are_rejected(acceptance_api, display_name):
    """AC-QPB-060: blank input and path-traversal components must be rejected outright."""
    result = acceptance_api.derive_project_slug(display_name)
    assert result.get("ok") is False, (
        f"expected rejection of unsafe/blank display_name {display_name!r}, got: {result}"
    )
    assert result.get("error_code"), "rejection must include an error_code (HARNESS_CONTRACT.md)"
    slug = result.get("slug")
    assert not slug, "a rejected name must never also produce a usable slug"


@pytest.mark.parametrize(
    "reserved_name",
    ["CON", "con", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"],
)
def test_windows_reserved_filenames_are_rejected(acceptance_api, reserved_name):
    """AC-QPB-060: Windows-reserved device names must never be produced/accepted as the slug."""
    result = acceptance_api.derive_project_slug(reserved_name)
    assert result.get("ok") is False, (
        f"Windows-reserved name {reserved_name!r} must be rejected, got: {result}"
    )


def test_rejected_name_never_silently_becomes_a_reserved_or_traversal_slug(acceptance_api):
    """AC-QPB-060: rejection must be explicit, not a silent fallback to an unsafe slug."""
    for bad in ["..", "CON", ""]:
        result = acceptance_api.derive_project_slug(bad)
        if result.get("ok"):
            slug = result["slug"]
            assert slug not in {"..", "con", "CON", ""}
            assert "/" not in slug and "\\" not in slug
        else:
            assert result.get("slug") in (None, "")


# --- AC-QPB-061 --------------------------------------------------------------

@pytest.mark.qgis
def test_each_generated_project_gets_a_distinct_valid_project_id(
    acceptance_api, base_config_factory, tmp_path
):
    """AC-QPB-061: project_id is a valid, distinct UUID v4 per project, independent of naming."""
    outcomes = []
    for i, name in enumerate(["Same-ish Name", "Same-ish Name"]):
        config = base_config_factory("simple_inventory", display_name=name)
        out_dir = tmp_path / f"proj_{i}"
        result = acceptance_api.build_project(config, str(out_dir))
        assert result["success"], result.get("error_message")
        outcomes.append(result)

    ids = [o["project_id"] for o in outcomes]
    assert all(ids), "every build must report a project_id"
    for pid in ids:
        parsed = uuid.UUID(pid)
        assert parsed.version == 4, f"project_id {pid!r} is not a UUID v4"
    assert ids[0] != ids[1], "two distinct projects must not share a project_id"
    # Whether two projects built from the same display_name end up with the same or a
    # disambiguated project_slug is not specified (only that project_id is independent of both
    # names, per FR-QPB-021a) — deliberately not asserted here.
