"""Multiple, separately-named polygons in one site-input drawing session (Section 6.3, FR-QPB-129;
Decision Log **D-75** — originally Type 2/Type 3 only; **D-79** — explicitly extended to Type 4
as well, since Type 4's `site` layer reaches the identical `SiteInputPage`/`MapCanvas` drawing
mechanism); AC-QPB-115 (Section 18.1), AC-QPB-116 (Section 18.5).

**What this requirement is (confirmed, already-decided; this file tests it, does not re-decide
it).** For Type 2 (`temporary_plots`), Type 3 (`permanent_plots`), and Type 4
(`vegetation_mapping`) — every survey type whose schema (`qfield_builder/schemas.py`) declares a
`site` table at all — the wizard's drawing-canvas alternative to file upload (FR-QPB-025) must let
the user draw **multiple, separate polygons in one drawing session**, with each finished polygon
individually, manually named by the user and written to its own separate `site` GeoPackage record
— never merged into one `site` record with a multi-part `MultiPolygon` geometry, and never sharing
one single name applied to every polygon. `site_geom` itself remains a single Polygon/MultiPolygon
column (DR-QPB-008), completely unchanged — this is a pure workflow/UX change to the wizard/canvas,
not a schema change.

**Confirmed by direct code reading, before writing any test here (per this round's own
instructions), exactly as Decision Log D-75 itself already states:**

- `qfield_builder/build.py`'s `_resolve_seed_sites()`/`build_project()` **already** accept
  `config["sites"]` as a **list** of `{"site_name": ..., "geom_wkt": ...}` dicts, validating each
  entry's geometry individually in a loop and raising a per-site-named error on failure — this is
  exactly the target end-state data model, confirmed by reading `build.py` directly: it requires
  **no** backend/build-pipeline change whatsoever. `qfield_builder/gpkg.py::build_geopackage()`
  then writes exactly one `INSERT INTO "site"` per list entry (confirmed by direct reading), one
  GeoPackage record per entry, each with its own `site_name`/`site_geom` — this is precisely how
  the existing GeoPackage/Shapefile upload path (`_resolve_sites_from_upload()`) already produces
  one `site` record per uploaded feature today.
- `qfield_builder/schemas.py` confirms `simple_inventory` (Type 1) has **no** `site` table in its
  schema at all (`_build_simple_inventory()` returns only `inventory_observation`) — this feature
  is naturally inapplicable to Type 1, which is why this file contains no Type-1 test of any kind
  (there is no "Type 1's site mechanism" to assert anything about).
- `qfield_builder/ui/map_canvas.py`'s `MapCanvas` and `qfield_builder/ui/wizard.py`'s
  `SiteInputPage` are today still single-polygon-only (one `draw_site_name_edit`, one
  `_drawn_site_wkt`, `config["sites"]` built as a single-element list) — this is the genuinely
  PySide6-widget-internal half of this requirement that this file, and this harness's
  `qfield_builder.acceptance_api` black-box, `build_project()`-config-in/GeoPackage-out
  convention, cannot reach or drive directly. See this round's traceability file
  (`../qfield_project_builder_multi_polygon_site_drawing.traceability.md`) for the fully specified
  `tests/unit/test_map_canvas.py`/`tests/unit/test_wizard.py` contract that covers that half, and
  the `manual`-marked placeholder at the bottom of this file for the genuinely
  GUI-interaction-only fact (a real user drawing and naming multiple polygons on screen).

**What this file covers.** The core, fully-automatable, most valuable half of this requirement:
given `config["sites"]` already shaped as a list of two or more `{"site_name", "geom_wkt"}`
entries (exactly the shape a fixed `SiteInputPage`/`MapCanvas` must eventually produce, and
exactly the shape the pre-existing upload path already produces today), `build_project()` must
produce exactly that many separate `site` records, each individually named and geometrically
correct, never merged, never sharing one name — for Types 2, 3, and 4 alike.
"""
from __future__ import annotations

import struct

import pytest

from .conftest import open_gpkg

pytestmark = pytest.mark.qgis

ALL_SITE_OWNING_SURVEY_TYPES = ("temporary_plots", "permanent_plots", "vegetation_mapping")

# Three widely separated MULTIPOLYGON WKT fixtures (EPSG:4326), each a simple, valid, closed
# square ring, chosen so their bounding-box envelopes never overlap -- a single record whose own
# envelope spans more than one of these squares would immediately indicate a merged geometry.
_POLY_A = "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
_POLY_B = "MULTIPOLYGON(((128.00 38.00, 128.01 38.00, 128.01 38.01, 128.00 38.01, 128.00 38.00)))"
_POLY_C = "MULTIPOLYGON(((129.00 36.00, 129.01 36.00, 129.01 36.01, 129.00 36.01, 129.00 36.00)))"

_ENVELOPE_BY_WKT = {
    _POLY_A: (127.00, 127.01, 37.00, 37.01),
    _POLY_B: (128.00, 128.01, 38.00, 38.01),
    _POLY_C: (129.00, 129.01, 36.00, 36.01),
}


def _envelope_from_gpkg_geometry_blob(blob: bytes) -> tuple[float, float, float, float]:
    """Reads the ``(min_x, max_x, min_y, max_y)`` envelope directly out of a standard GeoPackage
    binary-geometry-header blob (OGC GeoPackage spec, Annex on Binary Geometry format) -- a
    well-documented, standard container format, read here with plain `struct` unpacking, mirroring
    this suite's own established "read the artifact directly with well-known tooling" convention
    (`HARNESS_CONTRACT.md`'s opening rationale) rather than importing `qfield_builder.wkt`/`gpkg`
    directly.

    `qfield_builder/gpkg.py::build_geopackage()` always calls `wkt_to_gpkg_geometry()` for a seeded
    `site` record, which always includes an envelope (envelope-contents-indicator code 1:
    minx/maxx/miny/maxy, four little-endian doubles) -- there is no seed-site code path that omits
    one, so this helper does not need to handle the "no envelope" case.
    """
    assert blob[0:2] == b"GP", f"not a GeoPackage geometry blob (bad magic bytes): {blob[0:2]!r}"
    flags = blob[3]
    byte_order = "<" if flags & 0b00000001 else ">"
    envelope_code = (flags >> 1) & 0b00000111
    assert envelope_code == 1, (
        "expected envelope-contents-indicator code 1 (minx/maxx/miny/maxy) -- "
        "qfield_builder.gpkg always writes this shape for seeded site geometry, got "
        f"code {envelope_code}"
    )
    min_x, max_x, min_y, max_y = struct.unpack_from(f"{byte_order}dddd", blob, 8)
    return (min_x, max_x, min_y, max_y)


def _fetch_sites(gpkg_path: str) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Returns ``[(site_name, envelope), ...]`` for every row currently in the `site` table."""
    conn = open_gpkg(gpkg_path)
    try:
        rows = conn.execute("SELECT site_name, site_geom FROM site;").fetchall()
    finally:
        conn.close()
    return [(name, _envelope_from_gpkg_geometry_blob(blob)) for name, blob in rows]


# ---------------------------------------------------------------------------------------------
# AC-QPB-115 (core): given config["sites"] as a list of two-or-more {"site_name", "geom_wkt"}
# entries (the drawing-session outcome FR-QPB-129 requires SiteInputPage/MapCanvas to eventually
# produce), the generated GeoPackage's `site` table must contain exactly one record per entry,
# each individually named and geometrically correct -- for Types 2, 3, and 4 (Decision Log D-79).
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", ALL_SITE_OWNING_SURVEY_TYPES)
def test_ac115_two_named_polygons_in_one_session_produce_two_separate_site_records(
    acceptance_api, base_config_factory, tmp_path, survey_type
):
    """FR-QPB-129/AC-QPB-115 (also exercises AC-QPB-116's own GeoPackage-level assertion, "both
    named polygons are available for inclusion in the generated project"): given two named,
    finished polygons from one drawing session, the generated project's `site` table must contain
    exactly one record per polygon, each with the geometry and `site_name` value assigned to that
    specific polygon -- never one record with a merged multi-part geometry, and never every record
    sharing one shared name.
    """
    config = base_config_factory(survey_type)
    config["sites"] = [
        {"site_name": "Site A", "geom_wkt": _POLY_A},
        {"site_name": "Site B", "geom_wkt": _POLY_B},
    ]

    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    sites = _fetch_sites(result["gpkg_path"])
    assert len(sites) == 2, (
        f"expected exactly 2 separate `site` records (one per named, finished polygon) for "
        f"{survey_type}, got {len(sites)}: {sites}"
    )

    names = [name for name, _ in sites]
    assert set(names) == {"Site A", "Site B"}, (
        f"expected the two distinct, individually-assigned site names for {survey_type}, got "
        f"{names} -- each polygon must keep its own individually assigned name, never one "
        "shared name applied to every record"
    )
    assert len(set(names)) == len(names), (
        f"each drawn polygon's own name must land on its own separate record, not be collapsed "
        f"with another's: {names}"
    )

    envelope_by_name = dict(sites)
    assert envelope_by_name["Site A"] == pytest.approx(_ENVELOPE_BY_WKT[_POLY_A]), (
        "Site A's own stored geometry envelope does not match the polygon actually assigned to "
        f"it -- got {envelope_by_name['Site A']}, expected {_ENVELOPE_BY_WKT[_POLY_A]}"
    )
    assert envelope_by_name["Site B"] == pytest.approx(_ENVELOPE_BY_WKT[_POLY_B]), (
        "Site B's own stored geometry envelope does not match the polygon actually assigned to "
        f"it -- got {envelope_by_name['Site B']}, expected {_ENVELOPE_BY_WKT[_POLY_B]}"
    )


@pytest.mark.parametrize("survey_type", ALL_SITE_OWNING_SURVEY_TYPES)
def test_ac115_three_named_polygons_in_one_session_produce_three_separate_site_records(
    acceptance_api, base_config_factory, tmp_path, survey_type
):
    """Generalizes the two-polygon case above beyond exactly two, guarding against an
    implementation that happens to special-case "2" specifically rather than genuinely supporting
    an arbitrary number of polygons per session, per FR-QPB-129's own "multiple, separate
    polygons" wording (not "exactly two")."""
    config = base_config_factory(survey_type)
    config["sites"] = [
        {"site_name": "Site A", "geom_wkt": _POLY_A},
        {"site_name": "Site B", "geom_wkt": _POLY_B},
        {"site_name": "Site C", "geom_wkt": _POLY_C},
    ]

    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    sites = _fetch_sites(result["gpkg_path"])
    assert len(sites) == 3, (
        f"expected exactly 3 separate `site` records for {survey_type}, got {len(sites)}: {sites}"
    )
    names = {name for name, _ in sites}
    assert names == {"Site A", "Site B", "Site C"}, (
        f"unexpected site names for {survey_type}: {names}"
    )

    envelope_by_name = dict(sites)
    for name, wkt in (("Site A", _POLY_A), ("Site B", _POLY_B), ("Site C", _POLY_C)):
        assert envelope_by_name[name] == pytest.approx(_ENVELOPE_BY_WKT[wkt]), (
            f"{name}'s own stored geometry envelope does not match its assigned polygon for "
            f"{survey_type}: got {envelope_by_name[name]}, expected {_ENVELOPE_BY_WKT[wkt]}"
        )


def test_ac115_never_merges_multiple_polygons_into_one_multipolygon_record(
    acceptance_api, base_config_factory, tmp_path
):
    """Explicit differential guard for FR-QPB-129/Decision Log D-75's own central "never merged"
    assertion -- confirms the specifically-superseded behavior (a single `site` record whose one
    MultiPolygon geometry spans every input polygon's combined extent) does not occur, on top of
    the plain record-count assertions above. A merged-geometry record's own envelope would span
    both input polygons' combined bounding box (127.00-128.01 / 37.00-38.01); this asserts that
    never happens, for any single stored record."""
    config = base_config_factory("temporary_plots")
    config["sites"] = [
        {"site_name": "Site A", "geom_wkt": _POLY_A},
        {"site_name": "Site B", "geom_wkt": _POLY_B},
    ]
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    sites = _fetch_sites(result["gpkg_path"])
    assert len(sites) != 1, (
        "a single record for both input polygons would indicate they were merged into one "
        f"MultiPolygon geometry, which FR-QPB-129/Decision Log D-75 explicitly forbids: {sites}"
    )
    for name, (min_x, max_x, min_y, max_y) in sites:
        spans_both = min_x <= 127.00 and max_x >= 128.01
        assert not spans_both, (
            f"record {name!r}'s envelope ({min_x}, {max_x}, {min_y}, {max_y}) spans both input "
            "polygons' combined extent, indicating a merged MultiPolygon geometry, which "
            "FR-QPB-129/Decision Log D-75 explicitly forbids"
        )


def test_ac115_duplicate_site_names_across_distinct_polygons_are_not_deduplicated(
    acceptance_api, base_config_factory, tmp_path
):
    """FR-QPB-129 clause (2): "no uniqueness constraint across these names is required, mirroring
    the existing upload-path precedent" -- two distinct, separately drawn/finished polygons that
    happen to share the identical assigned name must still produce two separate `site` records,
    never deduplicated/collapsed into one merely because their names collide."""
    config = base_config_factory("permanent_plots")
    config["sites"] = [
        {"site_name": "Same Name", "geom_wkt": _POLY_A},
        {"site_name": "Same Name", "geom_wkt": _POLY_B},
    ]
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    sites = _fetch_sites(result["gpkg_path"])
    assert len(sites) == 2, (
        f"two distinctly-drawn polygons sharing the same assigned name must still produce two "
        f"separate `site` records (FR-QPB-129: no uniqueness constraint on names), got "
        f"{len(sites)}: {sites}"
    )
    envelopes = sorted(envelope for _, envelope in sites)
    expected = sorted([_ENVELOPE_BY_WKT[_POLY_A], _ENVELOPE_BY_WKT[_POLY_B]])
    assert envelopes == [pytest.approx(e) for e in expected], (
        f"both distinct geometries must be preserved even though their names collide: {sites}"
    )


# ---------------------------------------------------------------------------------------------
# manual-marked placeholder: the genuinely GUI-interaction-only half of this requirement (a real
# user drawing and individually naming multiple separate polygons on screen), mirroring this
# suite's own established AC-QPB-104/FR-QPB-008/FR-QPB-025-D-24 manual-placeholder convention
# (test_symbol_styling.py, test_qgis_manual_path_override.py, test_map_canvas_pan_navigability.py).
# ---------------------------------------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "FR-QPB-129/AC-QPB-116 (Decision Log D-75, extended to Type 4 by Decision Log D-79): a "
        "real user must be able to finish one polygon on the wizard's drawing canvas, assign it "
        "a name, then draw and finish a second (and further) separate polygon in the same "
        "drawing session -- with the first polygon's own finished shape and assigned name "
        "genuinely preserved on screen while the next one is drawn -- before ending the session "
        "entirely. This is a literal, on-screen PySide6 mouse-interaction/session-state fact "
        "(does the live MapCanvas widget actually retain the first finished shape while a "
        "second is being drawn; is the user actually able to assign a distinct name to each "
        "polygon) -- not a generated-project artifact this harness's black-box "
        "build_project()/validate_project() convention can reach (that build_project()-observable "
        "*outcome* of a completed multi-polygon session is what the automated tests above in "
        "this same file already cover), and not a pure, GUI-independent logic function. No "
        "automated GUI-driving mechanism exists in this harness for this, mirroring this suite's "
        "own established convention for exactly this category of criterion (e.g. AC-QPB-104's "
        "wizard-step-sequencing placeholder in test_symbol_styling.py, FR-QPB-008's "
        "wizard-control-reachability placeholder in test_qgis_manual_path_override.py, and "
        "FR-QPB-025/Decision Log D-24's pan-navigability placeholder in "
        "test_map_canvas_pan_navigability.py). See this round's traceability file "
        "(../qfield_project_builder_multi_polygon_site_drawing.traceability.md) for the fully "
        "specified tests/unit/test_map_canvas.py / tests/unit/test_wizard.py contract covering "
        "the headlessly-automatable half of this same mechanism."
        "\n\nManual QA steps: (1) Launch the desktop wizard for a Type 2, Type 3, or Type 4 "
        "project and reach Step 3 (site input); choose 'draw on map.' (2) Draw a polygon, assign "
        "it a distinct name (e.g. 'Site A'), and finish it. (3) Without clearing or restarting "
        "the session, start drawing a second, separate polygon elsewhere on the canvas; confirm "
        "the first polygon's own finished shape and assigned name are still visibly present, not "
        "discarded or merged into the second shape. (4) Finish the second polygon and assign it "
        "a distinct name (e.g. 'Site B'). (5) Optionally repeat for a third polygon. (6) Confirm "
        "leaving a polygon's own name blank still finishes it with a non-blank fallback name "
        "(mirroring the existing single-shape '그려진 사이트' default), per FR-QPB-129 clause (2). "
        "(7) End the drawing session and build the project; open the generated project's `site` "
        "layer in QGIS and confirm it shows one separate feature per drawn polygon, each with "
        "its own assigned name -- matching this file's automated build_project()-level "
        "assertions, now confirmed reachable through the real UI end-to-end. (8) Repeat for each "
        "of Type 2, Type 3, and Type 4 at least once."
    )
)
def test_wizard_can_draw_and_individually_name_multiple_separate_polygons_in_one_session():
    raise AssertionError("should never run while skipped — see skip reason")
