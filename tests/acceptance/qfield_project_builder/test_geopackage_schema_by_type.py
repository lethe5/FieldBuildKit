"""Per-survey-type schema, constraint, and symbology rules (Section 8, Section 18.1/18.2).

Covers:
- AC-QPB-005: geometry layers and CRS match Section 8's schema for the selected survey type.
- AC-QPB-007: a `cover` value outside 0-100 is rejected when saved.
- AC-QPB-008: a Type-1 inventory record with 0, 1, 2, or 3 photo fields populated is always
  accepted (no photo required).
- AC-QPB-009 (revised; Decision Log D-23; corrects a prior mandatory-photo misinterpretation;
  **further narrowed by Decision Log D-74, 2026-08-28**): a Type-2 `survey`, or a Type-3 `plot`,
  with zero related photo records (`survey_photo`/`plot_photo`) is accepted on save and is never
  flagged by project validation — zero related photos is valid, per DR-QPB-030/040 and
  NFR-QPB-041. When one or more related photo records exist, each must have a valid, non-empty
  relative attachment path (DR-QPB-012): a well-formed relative path is accepted; an empty,
  whitespace-only, absolute (POSIX/Windows drive-letter/UNC), `file://`, or project-root-escaping
  `..`-traversal path is invalid (`invalid_attachment_path`); and a well-formed relative path
  whose target file is later found missing from the project folder is a distinct, separate
  failure (`broken_attachment_reference`) — the two codes must never collide. **Decision Log
  D-74 removes `observation_photo` entirely for Type 2/3's `observation` table (replaced by three
  inline photo-path columns, mirroring Type 1) — this file's own former
  `test_ac009_observation_with_zero_related_photos_is_accepted` accordingly no longer applies and
  has been retired, not merely left in place: see
  `test_observation_photo_removal.py` (AC-QPB-112/AC-QPB-114) and
  `../qfield_project_builder_observation_photo_removal.traceability.md` for its replacement
  coverage.** The `survey`/`plot` cases below are entirely unaffected by D-74 and remain
  unchanged.
- AC-QPB-015: a Type-4 `community` feature's symbology switches between red/green hatch based on
  `is_field_checked`.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from .conftest import SURVEY_TYPE_SCHEMAS, open_gpkg

pytestmark = pytest.mark.qgis


# --- AC-QPB-005 ---------------------------------------------------------------

@pytest.mark.parametrize("survey_type", list(SURVEY_TYPE_SCHEMAS.keys()))
def test_ac005_geometry_layers_and_crs_match_schema_for_type(
    built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    conn = open_gpkg(result["gpkg_path"])
    try:
        geometry_columns = {
            (t, c): (geom_type, srs_id)
            for t, c, geom_type, srs_id in conn.execute(
                "SELECT table_name, column_name, geometry_type_name, srs_id "
                "FROM gpkg_geometry_columns;"
            ).fetchall()
        }
        schema = SURVEY_TYPE_SCHEMAS[survey_type]
        for table, meta in schema["tables"].items():
            if meta["geometry"] is None:
                # storage_crs default EPSG:4326 applies only to spatial layers; non-spatial
                # tables (e.g. observation, survey in some types) correctly have no geometry.
                continue
            geom_col, expected_type = meta["geometry"]
            key = (table, geom_col)
            assert key in geometry_columns, f"expected geometry column {key} in {survey_type}"
            actual_type, srs_id = geometry_columns[key]
            assert actual_type.upper() == expected_type, (
                f"{table}.{geom_col} geometry type is {actual_type}, expected {expected_type} "
                f"(DR-QPB-008)"
            )
            srs_row = conn.execute(
                "SELECT organization, organization_coordsys_id FROM gpkg_spatial_ref_sys "
                "WHERE srs_id = ?;",
                (srs_id,),
            ).fetchone()
            assert srs_row is not None, f"srs_id {srs_id} for {table}.{geom_col} not registered"
            org, code = srs_row
            assert (org or "").upper() == "EPSG" and int(code) == 4326, (
                f"{table}.{geom_col} storage CRS must be EPSG:4326 by default (DR-QPB-008), "
                f"found {org}:{code}"
            )
    finally:
        conn.close()


# --- AC-QPB-007 ----------------------------------------------------------------

@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
@pytest.mark.parametrize("bad_cover", [-1, 101, 1000, -100])
def test_ac007_cover_outside_0_100_is_rejected(
    acceptance_api, built_project_by_type, survey_type, bad_cover
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "observation",
        {"cover": bad_cover, "selected_scientific_name": "Test taxon"},
    )
    assert outcome["accepted"] is False, f"cover={bad_cover} must be rejected, got {outcome}"


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
@pytest.mark.parametrize("good_cover", [0, 1, 50, 100])
def test_cover_within_0_100_is_accepted(
    acceptance_api, built_project_by_type, survey_type, good_cover
):
    """Complements AC-QPB-007: valid boundary/interior cover values must not be rejected.

    `observation.survey_id` is a hard NOT NULL foreign key (Section 8.2/8.3), so a valid parent
    chain (site -> survey for Type 2, site -> plot -> survey for Type 3) must be built first and
    a real `survey_id` supplied — otherwise any save would be rejected for the missing FK
    regardless of `cover`, which would not actually isolate cover-value acceptance. Mirrors the
    parent-chain pattern in `test_ac009_observation_with_zero_related_photos_is_accepted`.
    """
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    conn = open_gpkg(result["gpkg_path"])
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()

    # Unique-per-case coordinates so repeated parametrized saves against the shared, session-
    # cached project don't collide with points created by other cases of this same test.
    offset = good_cover * 0.0001
    point_wkt = f"POINT({127.03 + offset} {37.03 + offset})"

    if survey_type == "temporary_plots":
        survey_outcome = acceptance_api.attempt_feature_save(
            result["project_dir"],
            "survey",
            {"surveyor": "Field Researcher", "plot_size": "5m x 5m", "site_id": site_id},
            geometry_wkt=point_wkt,
        )
    else:
        plot_outcome = acceptance_api.attempt_feature_save(
            result["project_dir"],
            "plot",
            {
                "plot_name": f"Plot cover-{good_cover}",
                "plot_size": "10m x 10m",
                "site_id": site_id,
            },
            geometry_wkt=point_wkt,
        )
        assert plot_outcome["accepted"], plot_outcome
        survey_outcome = acceptance_api.attempt_feature_save(
            result["project_dir"],
            "survey",
            {"surveyor": "Field Researcher", "plot_id": plot_outcome["generated_uuid"]},
        )
    assert survey_outcome["accepted"], survey_outcome
    survey_id = survey_outcome["generated_uuid"]

    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "observation",
        {
            "cover": good_cover,
            "selected_scientific_name": "Test taxon",
            "survey_id": survey_id,
        },
    )
    assert outcome["accepted"] is True, f"cover={good_cover} must be accepted, got {outcome}"


# --- AC-QPB-008 ----------------------------------------------------------------

@pytest.mark.parametrize(
    "photo_fields",
    [
        {},
        {"leaf_photo_path": "attachments/leaf1.jpg"},
        {"leaf_photo_path": "attachments/leaf1.jpg", "flower_photo_path": "attachments/fl1.jpg"},
        {
            "leaf_photo_path": "attachments/leaf1.jpg",
            "flower_photo_path": "attachments/fl1.jpg",
            "fruit_photo_path": "attachments/fr1.jpg",
        },
    ],
    ids=["zero_photos", "one_photo", "two_photos", "three_photos"],
)
def test_ac008_type1_photo_field_combinations_are_all_accepted(
    acceptance_api, isolated_project_by_type, photo_fields
):
    """Uses `isolated_project_by_type` (not the shared `built_project_by_type` cache): this test
    deliberately saves photo paths that are never written to disk, which would otherwise leave a
    permanently broken attachment reference behind in the session-shared `simple_inventory`
    project for other tests to trip over."""
    result = isolated_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")
    attributes = {
        "surveyor": "Field Researcher",
        "selected_scientific_name": "Test taxon",
        **photo_fields,
    }
    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"], "inventory_observation", attributes, geometry_wkt="POINT(127.0 37.0)"
    )
    assert outcome["accepted"] is True, (
        f"Type-1 observation with photo fields {sorted(photo_fields)} must be accepted "
        f"(DR-QPB-021), got {outcome}"
    )


def test_type1_layer_has_exactly_three_relation_free_photo_fields(built_project_by_type):
    """DR-QPB-020/DR-QPB-022 (supports AC-QPB-008): exactly 3 nullable, relation-free photo cols."""
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")
    conn = open_gpkg(result["gpkg_path"])
    try:
        columns = {
            row[1]: row for row in conn.execute("PRAGMA table_info(inventory_observation);")
        }
        for expected_col in ("leaf_photo_path", "flower_photo_path", "fruit_photo_path"):
            assert expected_col in columns, f"missing {expected_col}"
            _, name, _coltype, notnull, _default, _pk = columns[expected_col]
            assert notnull == 0, f"{expected_col} must be nullable/optional"
        fk_list = conn.execute("PRAGMA foreign_key_list(inventory_observation);").fetchall()
        assert fk_list == [], "inventory_observation must remain relation-free (DR-QPB-022)"
    finally:
        conn.close()


# --- AC-QPB-009 ----------------------------------------------------------------
#
# A freshly built project (from the minimal base config) seeds only a `site`, with no `survey`/
# `plot` rows yet (those are ordinarily created in the field) — so these tests first create a
# parent row themselves via `attempt_feature_save` (which handles GeoPackage geometry-blob
# construction), then assert the corrected DR-QPB-030/031/040/042 zero-or-more cardinality rule.

@pytest.mark.parametrize(
    "survey_type,parent_table,parent_attrs,parent_geom_wkt,photo_table",
    [
        (
            "temporary_plots",
            "survey",
            {"surveyor": "Field Researcher", "plot_size": "5m x 5m"},
            "POINT(127.005 37.005)",
            "survey_photo",
        ),
        (
            "permanent_plots",
            "plot",
            {"plot_name": "Plot A-1", "plot_size": "10m x 10m"},
            "POINT(127.005 37.005)",
            "plot_photo",
        ),
    ],
)
def test_ac009_parent_with_zero_related_photos_is_accepted(
    acceptance_api,
    built_project_by_type,
    survey_type,
    parent_table,
    parent_attrs,
    parent_geom_wkt,
    photo_table,
):
    """DR-QPB-030/DR-QPB-040 (revised, Decision Log D-23): zero related photo records is valid
    and must never block an ordinary save or project validation."""
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    conn = open_gpkg(result["gpkg_path"])
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()
        assert site_id, "expected the seeded site from the base config"
        site_id = site_id[0]
    finally:
        conn.close()

    create_outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        parent_table,
        {**parent_attrs, "site_id": site_id},
        geometry_wkt=parent_geom_wkt,
    )
    assert create_outcome["accepted"], (
        f"a {parent_table} with zero related {photo_table} records must be accepted on save "
        f"(AC-QPB-009): {create_outcome}"
    )
    parent_id = create_outcome["generated_uuid"]
    assert parent_id, "attempt_feature_save must report the generated UUID (HARNESS_CONTRACT.md)"

    report = acceptance_api.validate_project(result["project_dir"])
    assert not any(
        issue["code"] == "missing_required_child_photo" for issue in report["issues"]
    ), (
        "validate_project() must never report a 'missing required child photo' style issue: "
        "DR-QPB-030/031/040/042 were corrected to zero-or-more (Decision Log D-23); "
        f"got: {report['issues']}"
    )
    related_issues = [
        issue for issue in report["issues"] if parent_id in issue.get("message", "")
    ]
    assert not related_issues, (
        f"a {parent_table} with zero related {photo_table} records must be accepted by project "
        f"validation and must never be treated as an error (AC-QPB-009, NFR-QPB-041); "
        f"got: {related_issues}"
    )
    # Completeness (stakeholder-required, see HARNESS_CONTRACT.md): a record with zero related
    # photo rows must never produce either photo-integrity code, since there is no photo record
    # whose path could be malformed or broken in the first place.
    codes_for_this_parent = {
        issue["code"] for issue in report["issues"] if parent_id in issue.get("message", "")
    }
    assert "invalid_attachment_path" not in codes_for_this_parent
    assert "broken_attachment_reference" not in codes_for_this_parent


def test_ac009_photo_record_needs_valid_path_and_missing_file_is_a_broken_attachment(
    acceptance_api, isolated_project_by_type
):
    """AC-QPB-009 positive path (unchanged by Decision Log D-23): when a related photo record
    does exist, its `path` must be a valid, non-empty relative attachment path, and a referenced
    file that is missing from the project folder must be reported as a broken attachment. This
    does not make the absence of a photo record itself an error (see the zero-photo tests above);
    it only governs photo records that do exist.

    Uses `isolated_project_by_type` (not the shared `built_project_by_type` cache): this test
    deliberately writes then deletes a photo file, which would otherwise leave a permanently
    broken attachment reference behind in the session-shared `temporary_plots` project for other
    tests to trip over."""
    result = isolated_project_by_type("temporary_plots")
    assert result["success"], result.get("error_message")

    conn = open_gpkg(result["gpkg_path"])
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()

    survey_outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5m x 5m", "site_id": site_id},
        geometry_wkt="POINT(127.007 37.007)",
    )
    assert survey_outcome["accepted"], survey_outcome
    survey_id = survey_outcome["generated_uuid"]

    relative_photo_path = "attachments/survey_photo_ac009.jpg"
    photo_file = Path(result["project_dir"]) / relative_photo_path
    photo_file.parent.mkdir(parents=True, exist_ok=True)
    photo_file.write_bytes(b"fake-jpeg-bytes")

    conn = open_gpkg(result["gpkg_path"])
    try:
        conn.execute(
            "INSERT INTO survey_photo (photo_id, survey_id, path, captured_at, notes) "
            "VALUES (?, ?, ?, ?, ?);",
            (str(uuid.uuid4()), survey_id, relative_photo_path, "2026-08-10T09:00:00+09:00", None),
        )
        conn.commit()
    finally:
        conn.close()

    clean_report = acceptance_api.validate_project(result["project_dir"])
    assert not any(
        issue["code"] == "broken_attachment_reference"
        and relative_photo_path in issue.get("message", "")
        for issue in clean_report["issues"]
    ), (
        f"survey_photo path {relative_photo_path} exists on disk; must not yet be flagged as a "
        f"broken/missing attachment: {clean_report['issues']}"
    )

    photo_file.unlink()

    broken_report = acceptance_api.validate_project(result["project_dir"])
    assert any(
        issue["code"] == "broken_attachment_reference"
        and relative_photo_path in issue.get("message", "")
        for issue in broken_report["issues"]
    ), (
        f"a survey_photo record whose path references a file now missing from the project "
        f"folder must be reported as a broken attachment (AC-QPB-009); "
        f"got: {broken_report['issues']}"
    )


# --- AC-QPB-009 (invalid_attachment_path) --------------------------------------
#
# DR-QPB-012 requires that only project-relative paths may ever be stored for a photo record, and
# that absolute paths must never be written into the GeoPackage/QGIS project. See
# HARNESS_CONTRACT.md's "Save-time vs. validate_project-only enforcement for
# invalid_attachment_path" section for exactly which of the malformed shapes below
# `attempt_feature_save` is expected to reject at save time (a purely syntactic, per-field
# constraint check) versus which is validate_project-only (`..`-traversal, which requires
# resolving the stored path against the actual project folder location — filesystem/project-path
# context a single field-constraint expression does not have). Both layers are exercised below;
# neither is assumed to catch a case the harness contract does not commit it to.

SAVE_TIME_ENFORCED_MALFORMED_ATTACHMENT_PATHS = [
    ("empty", ""),
    ("whitespace_only", "   "),
    ("posix_absolute", "/etc/photos/leaf.jpg"),
    ("windows_drive_absolute", "C:\\Users\\x\\leaf.jpg"),
    ("unc_path", "\\\\server\\share\\leaf.jpg"),
    ("file_uri", "file:///Users/x/leaf.jpg"),
]

VALIDATE_PROJECT_ONLY_MALFORMED_ATTACHMENT_PATHS = [
    ("traversal_escapes_project_root", "../../outside/leaf.jpg"),
]

ALL_INVALID_ATTACHMENT_PATH_CASES = (
    SAVE_TIME_ENFORCED_MALFORMED_ATTACHMENT_PATHS + VALIDATE_PROJECT_ONLY_MALFORMED_ATTACHMENT_PATHS
)


def _create_temporary_plots_survey(acceptance_api, project_dir, gpkg_path, geom_wkt):
    """Shared helper: create a valid `survey` parent row to attach a `survey_photo` to."""
    conn = open_gpkg(gpkg_path)
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()
    outcome = acceptance_api.attempt_feature_save(
        project_dir,
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5m x 5m", "site_id": site_id},
        geometry_wkt=geom_wkt,
    )
    assert outcome["accepted"], outcome
    return outcome["generated_uuid"]


def test_ac009_valid_relative_attachment_path_is_accepted(
    acceptance_api, built_project_by_type
):
    """AC-QPB-009 / DR-QPB-012: a well-formed, project-relative attachment path must be accepted
    when saving a new photo record."""
    result = built_project_by_type("temporary_plots")
    assert result["success"], result.get("error_message")
    survey_id = _create_temporary_plots_survey(
        acceptance_api, result["project_dir"], result["gpkg_path"], "POINT(127.008 37.008)"
    )

    relative_photo_path = "attachments/survey_photo_valid_path.jpg"
    photo_file = Path(result["project_dir"]) / relative_photo_path
    photo_file.parent.mkdir(parents=True, exist_ok=True)
    photo_file.write_bytes(b"fake-jpeg-bytes")

    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "survey_photo",
        {
            "survey_id": survey_id,
            "path": relative_photo_path,
            "captured_at": "2026-08-10T09:00:00+09:00",
        },
    )
    assert outcome["accepted"] is True, (
        f"a well-formed, project-relative attachment path must be accepted at save time "
        f"(AC-QPB-009, DR-QPB-012): {outcome}"
    )


@pytest.mark.parametrize(
    "path_kind,bad_path",
    SAVE_TIME_ENFORCED_MALFORMED_ATTACHMENT_PATHS,
    ids=[k for k, _ in SAVE_TIME_ENFORCED_MALFORMED_ATTACHMENT_PATHS],
)
def test_ac009_malformed_attachment_path_is_rejected_at_save_time(
    acceptance_api, built_project_by_type, path_kind, bad_path
):
    """AC-QPB-009 / DR-QPB-012: saving a new photo record whose path is empty, whitespace-only,
    a POSIX absolute path, a Windows drive-letter absolute path, a UNC path, or a `file://` URI
    must be rejected at save time — these are the shapes HARNESS_CONTRACT.md commits
    `attempt_feature_save` to catching via a static field constraint. `..`-traversal is
    deliberately excluded from this parametrization; see
    `test_ac009_malformed_attachment_path_is_detected_by_validate_project` and the harness
    contract for why it is validate_project-only."""
    result = built_project_by_type("temporary_plots")
    assert result["success"], result.get("error_message")
    survey_id = _create_temporary_plots_survey(
        acceptance_api, result["project_dir"], result["gpkg_path"], "POINT(127.009 37.009)"
    )

    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "survey_photo",
        {
            "survey_id": survey_id,
            "path": bad_path,
            "captured_at": "2026-08-10T09:00:00+09:00",
        },
    )
    assert outcome["accepted"] is False, (
        f"a photo record with a {path_kind!r} path ({bad_path!r}) must be rejected at save time "
        f"(AC-QPB-009, DR-QPB-012): {outcome}"
    )


@pytest.mark.parametrize(
    "path_kind,bad_path",
    ALL_INVALID_ATTACHMENT_PATH_CASES,
    ids=[k for k, _ in ALL_INVALID_ATTACHMENT_PATH_CASES],
)
def test_ac009_malformed_attachment_path_is_detected_by_validate_project(
    acceptance_api, base_config_factory, tmp_path, path_kind, bad_path
):
    """AC-QPB-009 / DR-QPB-012: `validate_project()` must report `invalid_attachment_path` for a
    photo record whose stored path is malformed, even when no field constraint prevented it from
    reaching the GeoPackage in the first place — simulating imported, externally edited, or
    corrupted data (per the stakeholder's explicit requirement; see HARNESS_CONTRACT.md). This
    covers every malformed shape, including `..`-traversal, which is validate_project-only (not
    asserted at save time — see `test_ac009_malformed_attachment_path_is_rejected_at_save_time`).

    Built fresh (not the session-shared `built_project_by_type` fixture) because this test writes
    directly to the GeoPackage via raw SQL, deliberately bypassing the form/field-constraint layer,
    and should not leave a malformed row behind in a project other tests reuse.
    """
    config = base_config_factory("temporary_plots")
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    survey_id = _create_temporary_plots_survey(
        acceptance_api, result["project_dir"], result["gpkg_path"], "POINT(127.01 37.01)"
    )

    conn = open_gpkg(result["gpkg_path"])
    try:
        conn.execute(
            "INSERT INTO survey_photo (photo_id, survey_id, path, captured_at, notes) "
            "VALUES (?, ?, ?, ?, ?);",
            (str(uuid.uuid4()), survey_id, bad_path, "2026-08-10T09:00:00+09:00", None),
        )
        conn.commit()
    finally:
        conn.close()

    report = acceptance_api.validate_project(result["project_dir"])
    assert any(
        issue["code"] == "invalid_attachment_path" for issue in report["issues"]
    ), (
        f"a survey_photo record with a {path_kind!r} path ({bad_path!r}) must be reported as "
        f"invalid_attachment_path by validate_project() (AC-QPB-009, DR-QPB-012); "
        f"got: {report['issues']}"
    )


def test_ac009_valid_relative_path_with_absent_file_is_broken_not_invalid_attachment_path(
    acceptance_api, base_config_factory, tmp_path
):
    """AC-QPB-009 differential guard: a syntactically valid, well-formed relative path whose
    target file is genuinely absent from the project folder must be reported as
    `broken_attachment_reference`, and must never also be reported as `invalid_attachment_path` —
    the two codes govern different failure layers (a malformed stored value vs. a well-formed
    stored value whose target file happens to be missing) and must never collide.
    """
    config = base_config_factory("temporary_plots")
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    survey_id = _create_temporary_plots_survey(
        acceptance_api, result["project_dir"], result["gpkg_path"], "POINT(127.011 37.011)"
    )

    relative_photo_path = "attachments/survey_photo_absent_target.jpg"
    # Deliberately never created on disk — this is the well-formed-path-but-absent-file case.

    conn = open_gpkg(result["gpkg_path"])
    try:
        conn.execute(
            "INSERT INTO survey_photo (photo_id, survey_id, path, captured_at, notes) "
            "VALUES (?, ?, ?, ?, ?);",
            (str(uuid.uuid4()), survey_id, relative_photo_path, "2026-08-10T09:00:00+09:00", None),
        )
        conn.commit()
    finally:
        conn.close()

    report = acceptance_api.validate_project(result["project_dir"])
    codes_for_this_path = {
        issue["code"]
        for issue in report["issues"]
        if relative_photo_path in issue.get("message", "")
    }
    assert "broken_attachment_reference" in codes_for_this_path, (
        f"a well-formed relative path whose target file is absent must be reported as "
        f"broken_attachment_reference (AC-QPB-009); got issues: {report['issues']}"
    )
    assert "invalid_attachment_path" not in codes_for_this_path, (
        f"a well-formed relative path must never also be reported as invalid_attachment_path "
        f"merely because its target file is absent — that is a distinct failure mode "
        f"(AC-QPB-009); got issues: {report['issues']}"
    )


# --- AC-QPB-015 ----------------------------------------------------------------

def test_ac015_community_symbology_rule_exists_in_qgs_project(built_project_by_type):
    """AC-QPB-015 / DR-QPB-051: is_field_checked true -> green hatch, else red hatch.

    Verified by inspecting the generated `.qgs` project's rule-based renderer for the
    `community` layer, since driving an actual rendered map image is outside what this harness
    can assert on deterministically; the renderer rule expressions are the mechanism that
    produces the described visual behavior.
    """
    result = built_project_by_type("vegetation_mapping")
    assert result["success"], result.get("error_message")
    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    assert "is_field_checked" in qgs_text, (
        "expected the community layer's renderer to reference is_field_checked"
    )
    # A rule-based renderer with two rules keyed on is_field_checked is the documented mechanism
    # (DR-QPB-051); we look for both a true-branch and a false/else-branch rule expression.
    assert "true" in qgs_text.lower() and (
        "false" in qgs_text.lower() or "ELSE" in qgs_text
    ), "expected both a true-branch and a default/false-branch renderer rule"
