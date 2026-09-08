"""Shared fixtures for the QField Project Builder acceptance suite.

See HARNESS_CONTRACT.md in this directory for the (implementer-provided) `acceptance_api`
surface these tests call into, and specs/qfield-project-builder.md for the approved
specification these tests verify.

If `qfield_builder.acceptance_api` does not exist yet, every test that needs it is *skipped*
(via `pytest.importorskip`), not failed/errored — that is the expected state before an
implementation exists.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

import pytest

MIB = 1024 * 1024
GIB = 1024 * MIB
OFFLINE_PREGENERATION_THRESHOLD_BYTES = 900 * MIB  # DR-QPB-060
OFFLINE_HARD_LIMIT_BYTES = 1 * GIB  # DR-QPB-060


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "qgis: requires a real, working QGIS/PyQGIS runtime on this machine"
    )
    config.addinivalue_line(
        "markers", "network: requires live network access to the real VWorld API (skipped by default)"
    )
    config.addinivalue_line(
        "markers", "device: requires a physical iOS/Android device running QField (not automated here)"
    )
    config.addinivalue_line(
        "markers", "manual: requires human/GUI/installer interaction not automatable via this harness"
    )
    config.addinivalue_line(
        "markers", "legacy_compatibility: explicitly exercises the pre-D-95 source contract"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    if config.getoption("--run-network", default=False):
        return
    skip_network = pytest.mark.skip(reason="requires --run-network and a live VWorld API key")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run acceptance tests that require live network access to the real VWorld API.",
    )


@pytest.fixture(scope="session")
def acceptance_api():
    """The implementer-provided test harness surface. See HARNESS_CONTRACT.md."""
    return pytest.importorskip(
        "qfield_builder.acceptance_api",
        reason=(
            "qfield_builder.acceptance_api is not implemented yet — see "
            "tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md"
        ),
    )


def _require_harness_function(acceptance_api, name: str):
    """Returns the named function from `acceptance_api`, or *skips* (not fails) the current test
    if the implementer has not added it yet.

    This extends, function-by-function, the same "skip gracefully before an implementation
    exists" convention `acceptance_api` itself already uses via `pytest.importorskip` above. That
    whole-module skip was written when no application code existed at all; later test-design
    rounds (e.g. the post-MVP Section 13 round, and the Decision Log D-56/D-57/D-58 Korean
    field-alias round) each add tests that call brand-new functions on a module
    (`qfield_builder.acceptance_api`) that, by the time each round was authored, an earlier
    implementation had already made real (see HARNESS_CONTRACT.md for the specific section
    documenting each individual function) — so a bare `pytest.importorskip` on the whole module no
    longer detects "this specific new function isn't built yet." This restores the same,
    deliberate "not implemented yet -> skip" signal at the level of an individual new harness
    function, rather than letting a plain `AttributeError` report as a hard failure.
    """
    fn = getattr(acceptance_api, name, None)
    if fn is None:
        pytest.skip(
            f"qfield_builder.acceptance_api.{name}() is not implemented yet — see "
            "tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md for the section "
            "documenting this function"
        )
    return fn


@pytest.fixture()
def match_ktsn(acceptance_api):
    return _require_harness_function(acceptance_api, "match_ktsn")


@pytest.fixture()
def match_ktsn_with_national_list(acceptance_api):
    """D-88-aware matching seam, including NIBR disambiguation at every hop."""
    return _require_harness_function(acceptance_api, "match_ktsn_with_national_list")


@pytest.fixture()
def build_plantnet_identify_request(acceptance_api):
    return _require_harness_function(acceptance_api, "build_plantnet_identify_request")


@pytest.fixture()
def call_plantnet_identify(acceptance_api):
    return _require_harness_function(acceptance_api, "call_plantnet_identify")


@pytest.fixture()
def inspect_identification_widget(acceptance_api):
    return _require_harness_function(acceptance_api, "inspect_identification_widget")


@pytest.fixture()
def run_ktsn_reference_pipeline(acceptance_api):
    return _require_harness_function(acceptance_api, "run_ktsn_reference_pipeline")


@pytest.fixture()
def inspect_field_aliases(acceptance_api):
    """DR-QPB-071/FR-QPB-119/Section 8.5/AC-QPB-098 (Decision Log D-56/D-57/D-58) — see
    HARNESS_CONTRACT.md function 12."""
    return _require_harness_function(acceptance_api, "inspect_field_aliases")


# ---------------------------------------------------------------------------
# Decision Log D-64–D-69 (2026-08-26 stakeholder-decisions round) harness fixtures — see
# HARNESS_CONTRACT.md's "New (Decision Log D-64–D-69...)" section, functions 13-17.
# ---------------------------------------------------------------------------


@pytest.fixture()
def fetch_tabler_icon_svg(acceptance_api):
    """Decision Log D-65 — see HARNESS_CONTRACT.md function 13. Real-network-calling; used only
    by the one `network`-marked live test."""
    return _require_harness_function(acceptance_api, "fetch_tabler_icon_svg")


@pytest.fixture()
def search_bundled_tabler_icon_names(acceptance_api):
    """FR-QPB-121 (Decision Log D-65) — see HARNESS_CONTRACT.md function 14."""
    return _require_harness_function(acceptance_api, "search_bundled_tabler_icon_names")


@pytest.fixture()
def inspect_layer_renderer(acceptance_api):
    """FR-QPB-120/FR-QPB-121 (Decision Log D-65) — see HARNESS_CONTRACT.md function 15."""
    return _require_harness_function(acceptance_api, "inspect_layer_renderer")


@pytest.fixture()
def inspect_editor_widget(acceptance_api):
    """FR-QPB-122/FR-QPB-124/FR-QPB-125 (Decision Log D-66/D-67/D-69) — see HARNESS_CONTRACT.md
    function 16."""
    return _require_harness_function(acceptance_api, "inspect_editor_widget")


@pytest.fixture()
def derive_accepted_name_lookup_table(acceptance_api):
    """FR-QPB-126 (Decision Log D-67) — see HARNESS_CONTRACT.md function 17."""
    return _require_harness_function(acceptance_api, "derive_accepted_name_lookup_table")


# ---------------------------------------------------------------------------
# Decision Log D-73/D-77 (Korean relation-widget display names; FR-QPB-128, Section 8.6,
# AC-QPB-111) harness fixture — see HARNESS_CONTRACT.md's "New (Decision Log D-73/D-77)" section,
# function 18 (`inspect_relations`).
# ---------------------------------------------------------------------------


@pytest.fixture()
def inspect_relations(acceptance_api):
    """FR-QPB-128/Section 8.6/AC-QPB-111 (Decision Log D-73/D-77) — see HARNESS_CONTRACT.md
    function 18."""
    return _require_harness_function(acceptance_api, "inspect_relations")


# ---------------------------------------------------------------------------
# Decision Log D-80/D-84 (Korean layer display names; DR-QPB-078, FR-QPB-130, Section 8.7,
# AC-QPB-118) harness fixture — see HARNESS_CONTRACT.md's "New (Decision Log D-80/D-84)" section,
# function 19 (`inspect_layer_names`).
# ---------------------------------------------------------------------------


@pytest.fixture()
def inspect_layer_names(acceptance_api):
    """DR-QPB-078/FR-QPB-130/Section 8.7/AC-QPB-118 (Decision Log D-80/D-84) — see
    HARNESS_CONTRACT.md function 19."""
    return _require_harness_function(acceptance_api, "inspect_layer_names")


# ---------------------------------------------------------------------------
# test-designer conformance-gap round (2026-08-27): FR-QPB-008 manual QGIS-install-path override
# — see HARNESS_CONTRACT.md's "New (test-designer conformance-gap round...)" section and
# ../qfield_project_builder_qgis_manual_path_override.traceability.md.
# ---------------------------------------------------------------------------


@pytest.fixture()
def check_runtime_with_manual_path(acceptance_api):
    """`check_runtime` (function 1) already exists, but its pre-existing signature —
    `check_runtime(force_missing: bool = False) -> dict` — has no `manual_path` parameter at all;
    FR-QPB-008's manual QGIS-install-path-override half has zero implementation as of this round
    (see the traceability file for the full conformance-gap report). This skips cleanly, mirroring
    `_require_harness_function`'s established "not implemented yet -> skip" convention above,
    rather than erroring on an unexpected keyword argument, until `check_runtime` gains the
    `manual_path` parameter this round's tests require.
    """
    import inspect

    params = inspect.signature(acceptance_api.check_runtime).parameters
    if "manual_path" not in params:
        pytest.skip(
            "qfield_builder.acceptance_api.check_runtime() does not yet accept a `manual_path` "
            "parameter (FR-QPB-008) — see HARNESS_CONTRACT.md's 'New (test-designer "
            "conformance-gap round...)' section"
        )
    return acceptance_api.check_runtime


# ---------------------------------------------------------------------------
# Decision Log D-76 (live Tabler icon preview-fetch during search; FR-QPB-011(d)(ii), NFR-QPB-080
# clauses (5)-(8), AC-QPB-117) harness fixture — see HARNESS_CONTRACT.md's "New (Decision Log
# D-76)" section, function 20 (`fetch_tabler_icon_preview_svgs`), and
# ../qfield_project_builder_tabler_icon_preview_fetch.traceability.md.
# ---------------------------------------------------------------------------


@pytest.fixture()
def fetch_tabler_icon_preview_svgs(acceptance_api):
    """FR-QPB-011(d)(ii)/NFR-QPB-080 clauses (5)-(8)/AC-QPB-117 (Decision Log D-76) — see
    HARNESS_CONTRACT.md function 20. A fake-double-only (never "real network") pure reference
    implementation, mirroring `search_bundled_tabler_icon_names`'s (function 14) own "expose the
    pure, GUI-independent logic headlessly, never the PySide6 keystroke/debounce event itself"
    convention -- the actual debounced, bounded-concurrency, User-Agent-carrying wizard-widget
    mechanism that decides *when* and via *which* real HTTP client this gets called is routed to
    `tests/unit/` (see this round's traceability file's routed contract table), not tested here.
    """
    return _require_harness_function(acceptance_api, "fetch_tabler_icon_preview_svgs")


@pytest.fixture(scope="session")
def runtime_available(acceptance_api) -> bool:
    info = acceptance_api.check_runtime()
    assert "available" in info and "message" in info, (
        "check_runtime() must return {'available': bool, 'message': str} per HARNESS_CONTRACT.md"
    )
    return bool(info["available"])


@pytest.fixture(autouse=True)
def _skip_qgis_tests_when_runtime_missing(request, acceptance_api):
    if request.node.get_closest_marker("qgis") is None:
        yield
        return
    info = acceptance_api.check_runtime()
    if not info.get("available"):
        pytest.skip(
            "No working QGIS/PyQGIS runtime detected on this machine "
            f"({info.get('message')!r}); skipping test that requires FR-QPB-007/007a runtime."
        )
    yield


@pytest.fixture()
def output_root(tmp_path: Path) -> Path:
    """A fresh, non-pre-existing directory root for a single build's output."""
    root = tmp_path / "qpb_output"
    return root


# ---------------------------------------------------------------------------
# Minimal, valid sample WKT geometry for each survey type, in EPSG:4326
# (DR-QPB-008: sites/communities are MULTIPOLYGON; plots/inventory points are POINT).
# ---------------------------------------------------------------------------

SAMPLE_SITE_POLYGON_WKT = (
    "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
)

SAMPLE_INVALID_POLYGON_WKT = (
    # Self-intersecting "bowtie" polygon — invalid geometry per FR-QPB-028/E-QPB-011.
    "POLYGON((127.00 37.00, 127.01 37.01, 127.00 37.01, 127.01 37.00, 127.00 37.00))"
)

SAMPLE_POINT_WKT = "POINT(127.005 37.005)"


def make_base_config(survey_type: str, display_name: str = "테스트 프로젝트 1") -> dict:
    """A minimal, otherwise-valid build_project() config for the given survey type.

    The shared successful-build fixture uses the D-95 canonical workbook explicitly.  The small
    fixture directory supplies only the test raster scaffold; the canonical workbook path is
    separate so the legacy CSV/XLSX files beside that raster fixture cannot be selected by
    accident.  Tests that intentionally exercise the pre-D-95 contract opt in with
    `reference_compatibility_mode` themselves.
    """
    config: dict = {
        "project_display_name": display_name,
        "description": "Acceptance-test fixture project",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": survey_type,
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "_test_reference_data_dir": str(REFERENCE_DATA_VALID_SAMPLE_DIR),
        "canonical_reference_path": str(CANONICAL_REFERENCE_WORKBOOK_PATH),
    }
    if survey_type in ("temporary_plots", "permanent_plots", "vegetation_mapping"):
        config["sites"] = [
            {"site_name": "Site A", "geom_wkt": SAMPLE_SITE_POLYGON_WKT},
        ]
    if survey_type == "permanent_plots":
        config["plots"] = [
            {"plot_name": "Plot A-1", "geom_wkt": SAMPLE_POINT_WKT, "plot_size": "10m x 10m"},
        ]
    return config


@pytest.fixture()
def base_config_factory():
    return make_base_config


@pytest.fixture(scope="session")
def built_project_by_type(acceptance_api, tmp_path_factory):
    """Session-cached `build_project()` results, one per survey type, built on first use.

    Several acceptance tests only need *a* successfully generated, minimal project of a given
    survey type to inspect (schema, relations, UUIDs, ...) and do not need to vary the build
    config. Building once per type per test session avoids repeatedly re-running full
    QGIS/PyQGIS-backed generation for every individual assertion.
    """
    cache: dict = {}

    def _get(survey_type: str) -> dict:
        if survey_type not in cache:
            config = make_base_config(survey_type)
            out_dir = tmp_path_factory.mktemp(f"proj_{survey_type}_") / "project"
            result = acceptance_api.build_project(config, str(out_dir))
            cache[survey_type] = result
        return cache[survey_type]

    return _get


@pytest.fixture
def project_layer_xml():
    """Inspect standalone-generated layer structure; does not claim PyQGIS execution."""
    import xml.etree.ElementTree as ET

    def read(result, table):
        root = ET.parse(result["qgs_path"]).getroot()
        matches = [layer for layer in root.findall("./projectlayers/maplayer")
                   if f"layername={table}" in (layer.findtext("datasource", "").split("|"))]
        assert len(matches) == 1, f"Expected exactly one generated layer for {table}"
        return matches[0]

    return read


def _remap_project_paths(result: dict, old_root: str, new_root: str) -> dict:
    """Returns a copy of a `build_project()`-shaped result dict with its path-valued keys
    rewritten from `old_root` to `new_root` (used when a test operates on a copy of a cached
    build rather than the original build location)."""
    remapped = dict(result)
    for key in ("project_dir", "qgs_path", "gpkg_path", "attachments_dir", "basemap_dir"):
        value = remapped.get(key)
        if isinstance(value, str) and value.startswith(old_root):
            remapped[key] = new_root + value[len(old_root) :]
    return remapped


@pytest.fixture()
def isolated_project_by_type(built_project_by_type, tmp_path):
    """Like `built_project_by_type`, but returns a private, per-test copy of the cached build.

    `built_project_by_type` is session-scoped and shared by every test that only needs to
    *inspect* a project of a given survey type. Any test that intentionally *mutates* a built
    project's on-disk state in a way that would leave it altered for the rest of the session
    (e.g. writing then deleting an attachment file so a broken reference is permanently left
    behind, or recording photo paths that were never written to disk) must use this fixture
    instead, so it operates on its own `shutil.copytree`'d copy and never contaminates the
    shared cache reused by other tests that expect a clean project.
    """

    def _get(survey_type: str) -> dict:
        cached = built_project_by_type(survey_type)
        assert cached["success"], cached.get("error_message")
        isolated_dir = tmp_path / f"isolated_{survey_type}"
        shutil.copytree(cached["project_dir"], isolated_dir)
        return _remap_project_paths(cached, cached["project_dir"], str(isolated_dir))

    return _get


def open_gpkg(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def user_tables(conn: sqlite3.Connection) -> list[str]:
    """GeoPackage user data tables, excluding GeoPackage-internal `gpkg_*`/`rtree_*` tables."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'gpkg_%' AND name NOT LIKE 'rtree_%' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Schema map per survey type (Section 8). Used by schema/relation/UUID acceptance tests so the
# per-type table/column/relation facts live in exactly one place.
# ---------------------------------------------------------------------------

SURVEY_TYPE_SCHEMAS: dict = {
    "simple_inventory": {
        "tables": {
            "inventory_observation": {
                "uuid_pk": "inventory_id",
                "geometry": ("geom", "POINT"),
                "fk": None,
            },
        },
        "relations": [],
    },
    "temporary_plots": {
        "tables": {
            "site": {"uuid_pk": "site_id", "geometry": ("site_geom", "MULTIPOLYGON"), "fk": None},
            "survey": {
                "uuid_pk": "survey_id",
                "geometry": ("plot_geom", "POINT"),
                "fk": ("site_id", "site", "site_id"),
            },
            "observation": {
                "uuid_pk": "observation_id",
                "geometry": None,
                "fk": ("survey_id", "survey", "survey_id"),
            },
            "survey_photo": {
                "uuid_pk": "photo_id",
                "geometry": None,
                "fk": ("survey_id", "survey", "survey_id"),
            },
            # `observation_photo` (and its relation, `rel_observation_photo_observation`) is
            # deliberately absent here, not merely unreferenced: Decision Log D-74 (2026-08-28)
            # removes this table entirely for Type 2/3, replacing it with three inline photo-path
            # columns on `observation` itself (see `_TYPE2_3_OBSERVATION_ALIASES` below and
            # `../qfield_project_builder_observation_photo_removal.traceability.md`). This mirrors
            # the pre-existing `simple_inventory` entry above, which likewise never lists
            # `observation_photo`-equivalent tables at all -- both survey types are relation-free
            # for their own photo-path columns now.
        },
        "relations": [
            ("survey", "site_id", "site", "site_id"),
            ("observation", "survey_id", "survey", "survey_id"),
            ("survey_photo", "survey_id", "survey", "survey_id"),
        ],
    },
    "permanent_plots": {
        "tables": {
            "site": {"uuid_pk": "site_id", "geometry": ("site_geom", "MULTIPOLYGON"), "fk": None},
            "plot": {
                "uuid_pk": "plot_id",
                "geometry": ("plot_geom", "POINT"),
                "fk": ("site_id", "site", "site_id"),
            },
            "survey": {
                "uuid_pk": "survey_id",
                "geometry": None,
                "fk": ("plot_id", "plot", "plot_id"),
            },
            "observation": {
                "uuid_pk": "observation_id",
                "geometry": None,
                "fk": ("survey_id", "survey", "survey_id"),
            },
            "plot_photo": {
                "uuid_pk": "photo_id",
                "geometry": None,
                "fk": ("plot_id", "plot", "plot_id"),
            },
            # `observation_photo` is deliberately absent here too -- see the identical note on
            # `temporary_plots["tables"]` above (Decision Log D-74). `plot_photo` immediately
            # above is a structurally distinct table (photos of the permanent `plot` itself, not
            # of an individual `observation`) and is completely unaffected by this change.
        },
        "relations": [
            ("plot", "site_id", "site", "site_id"),
            ("survey", "plot_id", "plot", "plot_id"),
            ("observation", "survey_id", "survey", "survey_id"),
            ("plot_photo", "plot_id", "plot", "plot_id"),
        ],
    },
    "vegetation_mapping": {
        "tables": {
            "site": {"uuid_pk": "site_id", "geometry": ("site_geom", "MULTIPOLYGON"), "fk": None},
            "survey": {
                "uuid_pk": "survey_id",
                "geometry": None,
                "fk": ("site_id", "site", "site_id"),
            },
            "community": {
                "uuid_pk": "community_id",
                "geometry": ("community_geom", "MULTIPOLYGON"),
                "fk": ("survey_id", "survey", "survey_id"),
            },
        },
        "relations": [
            ("survey", "site_id", "site", "site_id"),
            ("community", "survey_id", "survey", "survey_id"),
        ],
    },
}

ALL_SURVEY_TYPES = tuple(SURVEY_TYPE_SCHEMAS.keys())


# ---------------------------------------------------------------------------
# Korean field-alias map (Section 8.5, DR-QPB-071, FR-QPB-119, AC-QPB-098; Decision Log D-56
# proposed it, D-57 confirmed all ten originally-flagged Medium-confidence terms verbatim, and
# D-58 confirmed the one remaining open sub-question — the Type-3 `plot_id` foreign-key label's
# "고정" prefix — verbatim as well ("'고정' added there too"). Per Decision Log D-57's own
# "Approval status" line, this table is fully stakeholder-confirmed and test-designer/implementer
# work may proceed against it; Open Question O-22 is closed. See this round's traceability file
# for the note on why DR-QPB-071/FR-QPB-119/AC-QPB-098's own inline requirement text still reads
# "draft proposal, not yet stakeholder-approved" despite this.
#
# Keyed exactly like SURVEY_TYPE_SCHEMAS above (survey_type -> table -> ...), but per-table value
# is `{"uuid_pk": <field name>, "aliases": {<field name>: <confirmed Korean alias text>}}` for
# every field this table has *other than* its own UUID primary key (excluded per DR-QPB-071 — a
# `Hidden`, read-only field must carry no alias) and other than geometry columns (never modeled as
# a `ColumnDef`/`QgsField` at all, per Section 8.5's own scoping note, so they never appear in a
# table's own field list in the first place and require no exclusion entry here).
#
# `observation_photo` (Type 2/3) — removed by a later `test-designer` round (2026-08-28; Decision
# Log D-74/D-78): this table (and its relation, `rel_observation_photo_observation`) no longer
# exists for Type 2/3 -- `observation` itself gains three new photo-path fields instead
# (`leaf_photo_path`/`flower_photo_path`/`fruit_photo_path`), reusing Type 1's own already-
# confirmed aliases verbatim (Section 8.5/DR-QPB-077). This table's own former dict entry (and the
# `_OBSERVATION_PHOTO_ALIASES` constant it used) has been removed from `KOREAN_FIELD_ALIASES`
# below, not merely struck through, since this is executable test data, not specification prose —
# see `../qfield_project_builder_observation_photo_removal.traceability.md` for the full record of
# this round's changes (and `qfield_project_builder_korean_field_aliases.traceability.md`'s own
# "Correction record (Decision Log D-74)" section for how this affects that round's coverage
# counts).
#
# `fid` (corrected by Decision Log D-59, 2026-08-26 — an earlier version of this comment block
# incorrectly grouped `fid` together with geometry columns above; it does not belong in that
# group): unlike geometry columns, `fid` *is* a genuine member of every generated GeoPackage
# layer's own `layer.fields()` — the OGC-required physical `"fid" INTEGER PRIMARY KEY
# AUTOINCREMENT` column (DR-QPB-002). It is deliberately represented as neither a key of any
# table's own `aliases` dict below, nor as that table's `uuid_pk` value (it is not a UUID field
# and is not the table's own domain primary key) — it is a third, distinct category. Because it is
# the same single fixed physical-key name (`"fid"`) for every table, rather than a per-table value
# the way `uuid_pk`/`aliases` are, it is represented once, below, as the module-level
# `FID_PHYSICAL_KEY_FIELD` constant rather than duplicated into every table's own dict entry here.
# It carries no Korean alias, but for a different reason than the UUID primary key's own
# "meaningless label for a hidden field" reasoning (DR-QPB-071): it is a non-domain physical key
# that Section 8.5's alias proposal simply does not assign one to, and it is separately already
# excluded from the *visible* attribute-editor form tree by the pre-existing, unrelated
# `_build_drag_and_drop_form` mechanism (`qfield_builder/qgis_worker.py`). See Decision Log D-59
# for the full correction record and `test_korean_field_aliases.py`'s completeness test for how
# this constant is consumed.
# ---------------------------------------------------------------------------

# The physical GeoPackage primary-key column present on every generated layer (Decision Log D-59)
# — the same fixed name for every table, unlike `uuid_pk` (which differs per table) and `aliases`
# (which lists only fields that carry a confirmed Korean alias). It is never a key inside any
# table's `aliases` dict and is never used as a table's `uuid_pk` value; tests that need to assert
# on the *complete* field set a layer reports (e.g. the completeness cross-check) must union this
# in explicitly alongside `aliases`/`uuid_pk`.
FID_PHYSICAL_KEY_FIELD = "fid"

# Decision Log D-74 (2026-08-28): three new photo-path fields on Type 2/3's `observation`,
# reusing Type 1's own already-confirmed aliases verbatim (Section 8.5/DR-QPB-077) -- see
# `../qfield_project_builder_observation_photo_removal.traceability.md` for this round's full
# record. These replace the removed `observation_photo` child table's own aliases (historical
# `_OBSERVATION_PHOTO_ALIASES` dict removed by this same round -- it is no longer referenced by
# any table entry below, since `observation_photo` itself no longer exists for Type 2/3).
_TYPE2_3_OBSERVATION_ALIASES = {
    "selected_korean_name": "국명",
    "selected_scientific_name": "학명",
    "selected_ktsn": "KTSN",
    "cover": "피도",
    "identification_score": "식별 신뢰도",
    "occurrence_probability": "출현 확률",
    "identification_status": "식별 상태",
    "identification_timestamp": "식별 일시",
    "identification_model_version": "식별 모델 버전",
    "leaf_photo_path": "잎 사진",
    "flower_photo_path": "꽃 사진",
    "fruit_photo_path": "열매 사진",
    "notes": "비고",
}

KOREAN_FIELD_ALIASES: dict = {
    "simple_inventory": {
        "inventory_observation": {
            "uuid_pk": "inventory_id",
            "aliases": {
                "observed_at": "관찰일시",
                "surveyor": "조사자",
                "selected_korean_name": "국명",
                "selected_scientific_name": "학명",
                "selected_ktsn": "KTSN",
                "identification_score": "식별 신뢰도",
                "occurrence_probability": "출현 확률",
                "identification_timestamp": "식별 일시",
                "identification_model_version": "식별 모델 버전",
                "leaf_photo_path": "잎 사진",
                "flower_photo_path": "꽃 사진",
                "fruit_photo_path": "열매 사진",
                "identification_status": "식별 상태",
                "notes": "비고",
            },
        },
    },
    "temporary_plots": {
        "site": {
            "uuid_pk": "site_id",
            "aliases": {"site_name": "사이트명"},
        },
        "survey": {
            "uuid_pk": "survey_id",
            "aliases": {
                "site_id": "사이트",
                "survey_date": "조사일자",
                "surveyor": "조사자",
                "plot_size": "조사구 크기",
            },
        },
        "observation": {
            "uuid_pk": "observation_id",
            "aliases": {"survey_id": "조사", **_TYPE2_3_OBSERVATION_ALIASES},
        },
        "survey_photo": {
            "uuid_pk": "photo_id",
            "aliases": {
                "survey_id": "조사",
                "path": "사진",
                "captured_at": "촬영일시",
                "notes": "비고",
            },
        },
        # `observation_photo` is deliberately absent here (Decision Log D-74): it no longer
        # exists for Type 2, so it has no field-alias table of its own any more either.
    },
    "permanent_plots": {
        "site": {
            "uuid_pk": "site_id",
            "aliases": {"site_name": "사이트명"},
        },
        "plot": {
            "uuid_pk": "plot_id",
            "aliases": {
                "site_id": "사이트",
                "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
                "plot_name": "고정조사구명",
                "plot_size": "조사구 크기",
            },
        },
        "survey": {
            "uuid_pk": "survey_id",
            "aliases": {
                # Decision Log D-58: the Type-3 plot_id foreign-key label carries the same "고정"
                # prefix as plot.plot_name's own confirmed alias — NOT the plain "조사구" originally
                # proposed at Medium confidence and left open by Decision Log D-57.
                "plot_id": "고정조사구",
                "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
                "survey_date": "조사일자",
                "surveyor": "조사자",
            },
        },
        "observation": {
            "uuid_pk": "observation_id",
            "aliases": {
                "survey_id": "조사",
                "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
                **_TYPE2_3_OBSERVATION_ALIASES,
            },
        },
        "plot_photo": {
            "uuid_pk": "photo_id",
            "aliases": {
                "plot_id": "고정조사구",  # Decision Log D-58, same as survey.plot_id above
                "path": "사진",
                "captured_at": "촬영일시",
                "notes": "비고",
            },
        },
        # `observation_photo` is deliberately absent here too (Decision Log D-74) -- see the
        # identical note on `temporary_plots["observation_photo"]`'s removal above.
    },
    "vegetation_mapping": {
        "site": {
            "uuid_pk": "site_id",
            "aliases": {"site_name": "사이트명"},
        },
        "survey": {
            "uuid_pk": "survey_id",
            "aliases": {
                "site_id": "사이트",
                "survey_date": "조사일자",
                "surveyor": "조사자",
            },
        },
        "community": {
            "uuid_pk": "community_id",
            "aliases": {
                "survey_id": "조사",
                "community_name": "군락명",
                "dominant_species": "우점종",
                "subdominant_species": "차우점종",
                "is_field_checked": "현장 확인 여부",
                "leaf_photo_path": "잎 사진",
                "flower_photo_path": "꽃 사진",
                "fruit_photo_path": "열매 사진",
                "notes": "비고",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Korean relation-widget display names (Section 8.6, FR-QPB-128, AC-QPB-111; Decision Log D-73
# proposed the mapping, in response to the stakeholder's verbatim report "Widget에 relation을
# 추가할 때 rel_observation_survey와 같은 이름으로 추가하지 말고 적절한 한국어 alias를 적용할
# 것"; Decision Log D-77 confirmed six of the seven proposed names exactly as proposed and
# corrected the seventh, `rel_observation_survey`, from the originally proposed "관찰" to the
# stakeholder's actual confirmed term, "식물관찰"). Distinct from, and independent of,
# `KOREAN_FIELD_ALIASES` above (an ordinary attribute-*field* alias, DR-QPB-071/FR-QPB-119): this
# instead governs a relation's own separate, human-facing "name" property
# (`QgsRelation.setName()`), used as the label QGIS/QField renders for the embedded
# `QgsAttributeEditorRelation` widget that lists a parent record's related child records
# (FR-QPB-056/FR-QPB-057) — never the relation's own stable `id()` (`QgsRelation.setId()`), which
# this requirement leaves completely unchanged (FR-QPB-056; depended on by
# `relation_aggregate()` expressions elsewhere).
#
# Keyed by the relation's own stable ID (unaffected by this requirement). Each value is
# `{"display_name": <confirmed Korean text>, "survey_types": (<survey_type>, ...)}` —
# `survey_types` lists every survey type (named exactly like `SURVEY_TYPE_SCHEMAS`/
# `qfield_builder.schemas.get_schema` above) whose own schema actually declares this relation,
# per Section 8.6's own "Survey type(s)" column, confirmed directly against
# `qfield_builder/schemas.py`'s own `ForeignKeyDef(relation_id=...)` values by this round.
#
# `rel_observation_photo_observation` is deliberately absent from this dict, not merely
# unreferenced: Section 8.6 explicitly excludes it (Decision Log D-73's own text: proposing a
# Korean name for it "would immediately be moot"), since Decision Log D-74 — a separate, related
# round — removes the `observation_photo` table, and therefore this relation, entirely for Type
# 2/3. Whether D-74's schema change has itself landed in `qfield_builder/schemas.py` as of any
# given point in this repository's history is immaterial to this dict and to every test built from
# it: neither asserts anything, positive or negative, about `rel_observation_photo_observation`'s
# own display name, existence, or absence — this dict is scoped, deliberately, to exactly the
# seven relations Section 8.6 lists, nothing more.
# ---------------------------------------------------------------------------

KOREAN_RELATION_DISPLAY_NAMES: dict = {
    "rel_survey_site": {
        "display_name": "조사",
        "survey_types": ("temporary_plots", "vegetation_mapping"),
    },
    "rel_observation_survey": {
        "display_name": "식물관찰",  # Decision Log D-77 correction (originally proposed "관찰")
        "survey_types": ("temporary_plots", "permanent_plots"),
    },
    "rel_survey_photo_survey": {
        "display_name": "조사 사진",
        "survey_types": ("temporary_plots",),
    },
    "rel_plot_site": {
        "display_name": "고정조사구",
        "survey_types": ("permanent_plots",),
    },
    "rel_survey_plot": {
        "display_name": "조사",
        "survey_types": ("permanent_plots",),
    },
    "rel_plot_photo_plot": {
        "display_name": "고정조사구 사진",
        "survey_types": ("permanent_plots",),
    },
    "rel_community_survey": {
        "display_name": "군락",
        "survey_types": ("vegetation_mapping",),
    },
}


# ---------------------------------------------------------------------------
# Korean layer display-name map (Section 8.7, DR-QPB-078, FR-QPB-130, AC-QPB-118; Decision Log
# D-80 proposed the mapping, D-84 confirmed it — with one correction, `site`'s own proposed
# "사이트" corrected to "조사지", applied uniformly across all three of its occurrences (Types
# 2/3/4)).
#
# This is a *layer's own name* (`QgsMapLayer.setName()`) — a third, separately configured UI
# surface from, and unaffected by, both `KOREAN_FIELD_ALIASES` (a field's own display alias,
# DR-QPB-071/Section 8.5) and `KOREAN_RELATION_DISPLAY_NAMES` (an embedded relation widget's own
# display name, FR-QPB-128/Section 8.6) above. The same underlying table name legitimately appears
# in all three dicts with an unrelated value in each — e.g. `site`'s own field alias for
# `site_name` is "사이트명" (Section 8.5, unaffected by this dict); its entries in
# `KOREAN_RELATION_DISPLAY_NAMES` above are the names of *child* relations that reference `site`
# (`rel_survey_site` → "조사", `rel_plot_site` → "고정조사구", never "site" itself, since a
# relation's own name is not the same thing as either of the two tables it connects); this dict's
# own value for `site` is the `site` layer's own name, "조사지".
#
# Keyed by the underlying GeoPackage table name (unaffected by this requirement, mirrors
# `SURVEY_TYPE_SCHEMAS`'s own per-table keys above). Each value is
# `{"display_name": <confirmed Korean text>, "survey_types": (<survey_type>, ...)}` — `survey_types`
# lists every survey type whose own schema actually declares this table, confirmed directly against
# `qfield_builder/schemas.py`'s own `TableDef`/`get_schema()` output by this round (which already
# reflects Decision Log D-74's `observation_photo` removal for Types 2/3 — Section 8.7's own table
# is written against this same current, approved schema, not a stale one; `observation_photo` is
# correctly absent from this dict for the identical reason it is already absent from
# `SURVEY_TYPE_SCHEMAS`/`KOREAN_RELATION_DISPLAY_NAMES` above).
# ---------------------------------------------------------------------------

KOREAN_LAYER_DISPLAY_NAMES: dict = {
    "inventory_observation": {
        "display_name": "식물관찰",
        "survey_types": ("simple_inventory",),
    },
    "site": {
        "display_name": "조사지",  # Decision Log D-84 correction (originally proposed "사이트")
        "survey_types": ("temporary_plots", "permanent_plots", "vegetation_mapping"),
    },
    "survey": {
        "display_name": "조사",
        "survey_types": ("temporary_plots", "permanent_plots", "vegetation_mapping"),
    },
    "observation": {
        "display_name": "식물관찰",
        "survey_types": ("temporary_plots", "permanent_plots"),
    },
    "survey_photo": {
        "display_name": "조사 사진",
        "survey_types": ("temporary_plots",),
    },
    "plot": {
        "display_name": "고정조사구",
        "survey_types": ("permanent_plots",),
    },
    "plot_photo": {
        "display_name": "고정조사구 사진",
        "survey_types": ("permanent_plots",),
    },
    "community": {
        "display_name": "군락",
        "survey_types": ("vegetation_mapping",),
    },
}

# The bundled KTSN accepted-name lookup table's own confirmed layer name (Section 8.7's separate
# "bonus row"; DR-QPB-072; Decision Log D-84's scope extension of DR-QPB-078/FR-QPB-130/
# AC-QPB-118 to this one additional, non-domain layer) — Types 1-3 only (DR-QPB-072's own explicit
# Type 4 exclusion). Kept as its own constant rather than folded into `KOREAN_LAYER_DISPLAY_NAMES`
# above: it is not a `TableDef`-backed domain survey-data layer at all (that dict's own scope), and
# its own real GeoPackage table name is not a hardcoded literal this suite should rely on directly
# — `build_project()`'s own `ktsn_lookup_table_name` return key (Decision Log D-66/D-67/D-68,
# HARNESS_CONTRACT.md function 17's neighboring addendum) is the existing, established source of
# truth for that name.
KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME = "인정 국명 조회표"


def is_valid_uuid_v4_text(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    # canonical lowercase, hyphenated, no braces (DR-QPB-003)
    if str(parsed) != value.lower():
        return False
    if value != value.lower():
        return False
    if "{" in value or "}" in value:
        return False
    return True


# ---------------------------------------------------------------------------
# Post-MVP (Section 13) additions: real reference-data fixture locations and small
# override/sample fixtures for FR-QPB-105/106/107/112. See HARNESS_CONTRACT.md's
# "Post-MVP: Section 13" section for the full rationale.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
POST_MVP_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

REAL_KTSN_CSV_PATH = REPO_ROOT / "storage" / "reference" / "tables" / "tb_leco_nib_ktsn_dtl_gat.csv"
REAL_PROBABILITY_RASTER_DIR = (
    REPO_ROOT / "storage" / "reference" / "rasters" / "bce_inverse_corrected_probability_maps"
)

# A real slice (11 rows: header + 10 real data rows, copied verbatim from the file above) used
# for fast, non-network, non-full-file-scan KTSN matching tests. NOT synthetic data — see
# `fixtures/ktsn_real_slice.csv`'s own selection documented in HARNESS_CONTRACT.md /
# the traceability file.
KTSN_REAL_SLICE_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_real_slice.csv"

# Deliberately constructed (NOT real-data) rows exercising `correct_list` edge cases confirmed
# absent from the real file by a full-file scan performed during test design (zero malformed
# JSON, zero "KTNS" misspellings across all ~212,397 real rows) — see
# `fixtures/ktsn_synthetic_edge_cases.csv` and HARNESS_CONTRACT.md.
KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_synthetic_edge_cases.csv"

# A tiny, valid-shaped reference-data directory (real CSV header + 2 real rows; placeholder,
# non-GeoTIFF ".tif" stand-ins) used with `build_project`'s `_test_reference_data_dir` hook for
# fast FR-QPB-112 bundling-*mechanism* tests, without touching the real ~247 MB dataset.
#
# Decision Log D-70 housekeeping (this round): also used as `make_base_config()`'s own default
# `_test_reference_data_dir` value (see that function's own docstring, near the top of this
# module, for the full rationale) — referenced only at call time, so this constant's own
# definition need not precede `make_base_config()`'s in the file — so every shared-fixture-built
# Types 1-3 project (via `make_base_config`/`built_project_by_type`/`isolated_project_by_type`)
# resolves reference data from here by default, instead of the real, gitignored,
# production-default `REFERENCE_DATA_DIR`.
REFERENCE_DATA_VALID_SAMPLE_DIR = POST_MVP_FIXTURES_DIR / "reference_data_valid_sample"

# D-95 canonical source used by all normal shared build fixtures.  The raster sidecar remains in
# `REFERENCE_DATA_VALID_SAMPLE_DIR` because the canonical release source deliberately stores the
# workbook separately from the large probability-raster set.
CANONICAL_REFERENCE_WORKBOOK_PATH = (
    REPO_ROOT / "resources" / "samples" / "taxonomy_sample.xlsx"
)

# A reference-data directory whose CSV is missing required columns (`taxon_jm_nm`, `correct_list`)
# — used to test FR-QPB-105's early-failure behavior.
REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR = (
    POST_MVP_FIXTURES_DIR / "reference_data_missing_columns_sample"
)

# ---------------------------------------------------------------------------
# Decision Log D-48 (FR-QPB-118, further revised, complete five-step form) additions: the real
# NIBR xlsx workbook's `관속식물류` sheet (Step 4's duplicate-name cross-reference source), and
# small, synthetic, per-step fixtures for `run_ktsn_reference_pipeline()`
# (HARNESS_CONTRACT.md function 11). See test_post_mvp_ktsn_reference_pipeline.py.
# ---------------------------------------------------------------------------

REAL_NIBR_XLSX_PATH = REPO_ROOT / "storage" / "reference" / "tables" / "2025년 국가생물종목록_v1.0.xlsx"

# Step-isolation synthetic fixtures (AC-QPB-084/085/086/087) — see each fixture's own row
# construction note in test_post_mvp_ktsn_reference_pipeline.py's module docstring. Every row in
# every one of these fixtures deliberately sets `p_ktsn` directly to the literal Plantae-root
# `ktsn` (`120000098391`) unless the row is specifically testing Step 1's own chain-traversal
# behavior — this keeps each small, standalone fixture self-contained (Step 1's transitive
# closure is computed only over the rows present in the same file; a small fixture cannot embed
# a real, multi-level ancestor chain) without weakening the step *under test* in each fixture,
# since a direct, one-hop child of the Plantae root is unambiguously still "a transitive
# descendant of `120000098391`" per FR-QPB-118's own Step 1 wording.
KTSN_PIPELINE_STEP1_SYNTHETIC_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_pipeline_step1_synthetic.csv"
KTSN_PIPELINE_STEP2_SYNTHETIC_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_pipeline_step2_synthetic.csv"
KTSN_PIPELINE_STEP3_SYNTHETIC_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_pipeline_step3_synthetic.csv"
KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH = POST_MVP_FIXTURES_DIR / "ktsn_pipeline_step4_synthetic.csv"
KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH = (
    POST_MVP_FIXTURES_DIR / "ktsn_pipeline_step4_synthetic_nibr_sheet.xlsx"
)

# Decision Log D-66/D-67 (DR-QPB-072/FR-QPB-126, new Step 5 of the shared reference-derivation
# pipeline: keep only taxon_jm_nm == '정명'). Three clearly-labeled synthetic rows (fake
# 9000000001xx-style/leading-zero KTSN identifiers, fictional "Testus ..." names), each already a
# direct child of the real Plantae root (p_ktsn == "120000098391") with rank_id 700 and an
# allowlisted phylum, so all three survive Steps 1-3 unfiltered and Step 4 is a no-op (no
# duplicated taxon_full_nm) -- isolating Step 5's own new accepted-only filter: row 1 (taxon_jm_nm
# == "정명") survives; row 2 (taxon_jm_nm blank) is excluded (fails the exact "정명" test, matching
# this pipeline's existing exclude-on-ambiguity posture, Decision Log D-48); row 3 (taxon_jm_nm ==
# "정명", leading-zero ktsn "090000000103") survives and exercises string-preservation. Pair with
# REFERENCE_DATA_VALID_SAMPLE_DIR's own real, empty-sheet NIBR xlsx sidecar below (reusable as-is:
# no row here has a duplicated taxon_full_nm, so Step 4 never needs a real lookup entry).
KTSN_STEP5_ACCEPTED_ONLY_SYNTHETIC_CSV_PATH = (
    POST_MVP_FIXTURES_DIR / "ktsn_step5_accepted_only_synthetic.csv"
)


@pytest.fixture(scope="session")
def real_nibr_xlsx_path() -> Path:
    """The real NIBR accepted-taxa workbook (Decision Log D-40/D-41/D-48) — `storage/reference/**`
    is gitignored and not guaranteed present on a fresh checkout, so any test using this fixture
    must be prepared to skip gracefully."""
    if not REAL_NIBR_XLSX_PATH.is_file():
        pytest.skip(
            f"Real NIBR accepted-taxa xlsx not present at {REAL_NIBR_XLSX_PATH} on this machine "
            "(storage/reference/** is gitignored data, not shipped in the repository); skipping "
            "test that validates against the real, full NIBR workbook."
        )
    return REAL_NIBR_XLSX_PATH


@pytest.fixture(scope="session")
def real_ktsn_csv_path() -> Path:
    """The real, full, stakeholder-confirmed-authoritative (Decision Log D-34) KTSN CSV.

    `storage/reference/**` is gitignored (see `.gitignore`) and is not guaranteed present on a
    fresh checkout, so any test using this fixture must be prepared to skip gracefully."""
    if not REAL_KTSN_CSV_PATH.is_file():
        pytest.skip(
            f"Real KTSN reference CSV not present at {REAL_KTSN_CSV_PATH} on this machine "
            "(storage/reference/** is gitignored data, not shipped in the repository); "
            "skipping test that validates against the real, full reference dataset."
        )
    return REAL_KTSN_CSV_PATH


@pytest.fixture(scope="session")
def real_probability_raster_dir() -> Path:
    if not REAL_PROBABILITY_RASTER_DIR.is_dir():
        pytest.skip(
            f"Real probability-raster directory not present at {REAL_PROBABILITY_RASTER_DIR} on "
            "this machine (storage/reference/** is gitignored data); skipping test that "
            "validates against the real, full raster dataset."
        )
    return REAL_PROBABILITY_RASTER_DIR
