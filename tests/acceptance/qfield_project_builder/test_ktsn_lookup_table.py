"""The D-95 canonical bundled KTSN accepted-name lookup table, its `ValueRelation` widget, and the derived
read-only `selected_scientific_name`/`selected_ktsn` fields (Section 7/9, Section 13.3, Section
13.9, Section 18.1/18.2; Decision Log D-62/D-66/D-67/D-68/D-70, closing Open Questions O-28, O-29,
O-30, O-31, O-32, O-34).

Covers:
- AC-QPB-105 (new DR-QPB-072/FR-QPB-124): `selected_korean_name` (Types 1-3 only) is configured
  with a `ValueRelation` editor widget referencing the bundled accepted-name lookup table, with a
  filter/completer configuration rather than a plain text-edit widget; Type 4 `community` uses
  the same picker for both `dominant_species` and `subdominant_species`.
- AC-QPB-106 (new DR-QPB-072): the bundled lookup table has a real, build-time-created index on its
  Korean-name column and on its scientific-name column.
- AC-QPB-107 (new FR-QPB-125/FR-QPB-126): `selected_scientific_name`/`selected_ktsn` are each
  configured with a `QgsDefaultValue` (`applyOnUpdate=True`) expression referencing
  `selected_korean_name`, and are configured non-editable; the bundled lookup table itself contains
  no row that is a synonym or original-combination name (`taxon_jm_nm != '정명'`).
- AC-QPB-108 (new FR-QPB-127): the lookup table, its index, and the `ValueRelation`/derived-field
  configuration above are all present and functional in a Types 1-3 project even when the post-MVP
  identification subsystem is disabled (`identification_enabled=False`) -- decoupled from
  FR-QPB-112's own conditional-bundling trigger.
- AC-QPB-109 (new; Decision Log D-70; closes O-34): canonical source fail-early reference-data
  validation (CSV missing, or present but lacking a required column) must still fire for a Types
  1-3 build even when `identification_enabled=False` -- a second, independent trigger condition,
  distinct from AC-QPB-108 above, because FR-QPB-127's unconditional accepted-name-lookup-table
  derivation (FR-QPB-126) reuses this same raw-CSV-reading pipeline regardless of that toggle.

**Design choice, applied throughout this file: every normal `build_project()` call below uses
`identification_enabled=False` and the canonical D-95 workbook from the shared fixture config.**
This keeps AC-QPB-108's unconditional accepted-name lookup behavior covered without routing the
new build through the legacy CSV path. The two synthetic
`derive_accepted_name_lookup_table()` checks are explicitly marked `legacy_compatibility` because
that helper belongs to the retained pre-D-95 compatibility seam.

The AC-QPB-109 cases below deliberately remove the canonical path and supply invalid/missing
reference roots, so they continue to test the explicit compatibility fail-closed behavior. No
normal build in this file relies on a legacy fixture or on automatic fallback.
"""
from __future__ import annotations

import pytest

from .conftest import (
    CANONICAL_REFERENCE_WORKBOOK_PATH,
    KTSN_STEP5_ACCEPTED_ONLY_SYNTHETIC_CSV_PATH,
    REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR,
    REFERENCE_DATA_VALID_SAMPLE_DIR,
    make_base_config,
    open_gpkg,
)

pytestmark = pytest.mark.qgis

TYPES_1_TO_3 = ("simple_inventory", "temporary_plots", "permanent_plots")

# The layer/field pair on which selected_korean_name (and the derived scientific-name/KTSN pair)
# actually lives, per survey type (Section 8.1/8.2/8.3).
NAME_FIELD_LAYER_BY_TYPE = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}

# The old NIBR xlsx sidecar is used only by the explicitly marked legacy synthetic checks below.
_REAL_EMPTY_SHEET_NIBR_XLSX = (
    REFERENCE_DATA_VALID_SAMPLE_DIR / "tables" / "2025년 국가생물종목록_v1.0.xlsx"
)


@pytest.fixture()
def ingest_canonical_workbook(acceptance_api):
    function = getattr(acceptance_api, "ingest_canonical_workbook", None)
    if function is None:
        pytest.skip("D-95 canonical ingestion seam is not implemented")
    return function


def _build_with_lookup_table(acceptance_api, tmp_path, survey_type: str, name: str = "proj"):
    config = make_base_config(survey_type)
    config["identification_enabled"] = False
    out_dir = tmp_path / name
    return acceptance_api.build_project(config, str(out_dir))


@pytest.fixture(scope="module")
def lookup_table_project_by_type(acceptance_api, tmp_path_factory):
    """Session/module-cached `build_project()` results, one per Types 1-3 survey type, each built
    with identification_enabled=False and the canonical D-95 source from `make_base_config()` --
    mirrors conftest.py's own `built_project_by_type` fixture."""
    cache: dict = {}

    def _get(survey_type: str) -> dict:
        if survey_type not in cache:
            config = make_base_config(survey_type)
            config["identification_enabled"] = False
            out_dir = tmp_path_factory.mktemp(f"lookup_{survey_type}_") / "project"
            cache[survey_type] = acceptance_api.build_project(config, str(out_dir))
        return cache[survey_type]

    return _get


# --- AC-QPB-105 --------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
def test_ac105_selected_korean_name_uses_a_value_relation_widget_referencing_the_lookup_table(
    inspect_editor_widget, lookup_table_project_by_type, survey_type
):
    result = lookup_table_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    layer = NAME_FIELD_LAYER_BY_TYPE[survey_type]
    info = inspect_editor_widget(result["project_dir"], layer, "selected_korean_name")
    assert info["widget_type"] == "ValueRelation", (
        f"AC-QPB-105/FR-QPB-124: {survey_type}.{layer}.selected_korean_name must be configured "
        f"with a ValueRelation editor widget, not a plain text-edit widget — got {info}"
    )
    assert info["referenced_layer_name"] == result.get("ktsn_lookup_table_name"), (
        f"AC-QPB-105/DR-QPB-072: the ValueRelation widget must reference the bundled accepted-name "
        f"lookup table — got referenced_layer_name={info['referenced_layer_name']!r}, expected "
        f"{result.get('ktsn_lookup_table_name')!r}"
    )
    assert info["has_filter_or_completer_config"] is True, (
        f"AC-QPB-105/FR-QPB-124: the widget must be configured for a filterable, typeahead "
        f"selection experience (a completer and/or filter expression), not a plain unfiltered "
        f"picklist — got {info}"
    )


@pytest.mark.parametrize("field_name", ("dominant_species", "subdominant_species"))
def test_ac105_type4_community_species_fields_use_the_same_value_relation_widget(
    inspect_editor_widget, acceptance_api, tmp_path, field_name
):
    """Type 4 writes Korean dominant/subdominant names from the accepted-name lookup table."""
    result = _build_with_lookup_table(acceptance_api, tmp_path, "vegetation_mapping")
    assert result["success"], result.get("error_message")
    assert result.get("ktsn_lookup_table_name")

    info = inspect_editor_widget(result["project_dir"], "community", field_name)
    assert info["widget_type"] == "ValueRelation", (
        f"community.{field_name} must use the accepted-name ValueRelation widget — "
        f"got {info}"
    )
    assert info["referenced_layer_name"] == result["ktsn_lookup_table_name"]
    assert info["has_filter_or_completer_config"] is True


# --- AC-QPB-106 --------------------------------------------------------------------------------


def _indexed_columns(conn, table: str) -> set[str]:
    """Every column covered by a real index on `table`, discovered via PRAGMA index_list/
    index_info rather than parsing raw CREATE INDEX SQL text — robust to exact SQL formatting."""
    columns: set[str] = set()
    for _seq, index_name, *_rest in conn.execute(f"PRAGMA index_list({table});").fetchall():
        for _seqno, _cid, col_name in conn.execute(f"PRAGMA index_info({index_name});").fetchall():
            if col_name is not None:
                columns.add(col_name)
    return columns


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
def test_ac106_bundled_lookup_table_has_a_real_index_on_korean_and_scientific_name_columns(
    lookup_table_project_by_type, survey_type
):
    result = lookup_table_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    table_name = result.get("ktsn_lookup_table_name")
    assert table_name, (
        f"AC-QPB-106/DR-QPB-072: expected build_project() to report ktsn_lookup_table_name for a "
        f"Types 1-3 build — got {result}"
    )

    conn = open_gpkg(result["gpkg_path"])
    try:
        indexed = _indexed_columns(conn, table_name)
    finally:
        conn.close()

    assert "taxon_kor_nm" in indexed, (
        f"AC-QPB-106/DR-QPB-072: expected a real, build-time-created index on the lookup table's "
        f"Korean-name column (taxon_kor_nm) — indexed columns found: {indexed}"
    )
    assert "taxon_full_nm" in indexed, (
        f"AC-QPB-106/DR-QPB-072: expected a real, build-time-created index on the lookup table's "
        f"scientific-name column (taxon_full_nm) — indexed columns found: {indexed}"
    )


# --- AC-QPB-107, half 1: derived, read-only selected_scientific_name/selected_ktsn -------------


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
@pytest.mark.parametrize("field_name", ["selected_scientific_name", "selected_ktsn"])
def test_ac107_field_is_derived_and_read_only_via_apply_on_update_default_value(
    inspect_editor_widget, lookup_table_project_by_type, survey_type, field_name
):
    result = lookup_table_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    layer = NAME_FIELD_LAYER_BY_TYPE[survey_type]
    info = inspect_editor_widget(result["project_dir"], layer, field_name)
    assert info["default_value_expression"], (
        f"AC-QPB-107/FR-QPB-125: {survey_type}.{layer}.{field_name} must carry a QgsDefaultValue "
        f"expression deriving it from selected_korean_name — got {info}"
    )
    assert "selected_korean_name" in info["default_value_expression"], (
        f"AC-QPB-107/FR-QPB-125: {field_name}'s default-value expression must reference "
        f"selected_korean_name's current value — got "
        f"{info['default_value_expression']!r}"
    )
    assert info["apply_on_update"] is True, (
        f"AC-QPB-107/FR-QPB-125: {field_name}'s default value must have applyOnUpdate=True "
        f"(QField's 'apply default upon update'), so it re-derives for an existing, reopened "
        f"feature too, not only a brand-new feature — got {info}"
    )
    assert info["is_read_only"] is True, (
        f"AC-QPB-107/FR-QPB-125: {field_name} must be configured non-editable (read-only) — got "
        f"{info}"
    )


# --- AC-QPB-107, half 2: no synonym/original-combination row in the bundled lookup table -------


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
def test_ac107_bundled_lookup_table_matches_canonical_accepted_rows(
    lookup_table_project_by_type, ingest_canonical_workbook, survey_type
):
    """AC-QPB-107/108: compare the generated lookup table with D-95's canonical ingestion result.

    The former test compared a canonical build against the pre-D-95 CSV/NIBR derivation helper;
    that was a stale source-contract assertion, not an independent check of the current product
    behavior.  Canonical ingestion remains the independent oracle here, and accepted-only and
    exact row-set properties remain asserted.
    """
    result = lookup_table_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    table_name = result["ktsn_lookup_table_name"]

    conn = open_gpkg(result["gpkg_path"])
    try:
        rows = conn.execute(
            f"SELECT ktsn, taxon_kor_nm, taxon_full_nm FROM {table_name};"
        ).fetchall()
    finally:
        conn.close()
    actual = {(str(r[0]), r[2]) for r in rows}

    expected_reference = ingest_canonical_workbook(
        str(CANONICAL_REFERENCE_WORKBOOK_PATH), source_kind="bundled_candidate"
    )
    assert expected_reference["success"] is True, expected_reference
    expected = {
        (row["ktsn"], row["scientific_name"])
        for row in expected_reference["rows"]
        if row["taxon_status"] == "정명"
    }

    assert actual == expected, (
        f"AC-QPB-107/FR-QPB-126: the bundled lookup table's own (ktsn, taxon_full_nm) row set must "
        f"match the accepted-only pure-Python reference computation exactly — actual={actual}, "
        f"expected={expected}"
    )
    assert len(actual) == 4_673, "D-95 canonical release contains only accepted rows"


@pytest.mark.legacy_compatibility
def test_legacy_derive_accepted_name_lookup_table_excludes_a_blank_taxon_jm_nm_row(
    derive_accepted_name_lookup_table,
):
    """FR-QPB-126's own explicit rule: a row with a missing/blank taxon_jm_nm value fails the exact
    '정명' test and is excluded, exactly like a genuine synonym row — not silently kept."""
    result = derive_accepted_name_lookup_table(
        str(KTSN_STEP5_ACCEPTED_ONLY_SYNTHETIC_CSV_PATH), str(_REAL_EMPTY_SHEET_NIBR_XLSX)
    )
    names = {row["taxon_full_nm"] for row in result["rows"]}
    assert "Testus acceptus" in names, "the accepted (정명) row must survive"
    assert "Testus blankstatus" not in names, (
        "a row with a blank taxon_jm_nm value must be excluded, matching the exact-'정명'-only rule"
    )


@pytest.mark.legacy_compatibility
def test_legacy_derive_accepted_name_lookup_table_preserves_ktsn_as_a_string_with_leading_zero(
    derive_accepted_name_lookup_table,
):
    result = derive_accepted_name_lookup_table(
        str(KTSN_STEP5_ACCEPTED_ONLY_SYNTHETIC_CSV_PATH), str(_REAL_EMPTY_SHEET_NIBR_XLSX)
    )
    by_name = {row["taxon_full_nm"]: row for row in result["rows"]}
    assert "Testus leadingzero" in by_name, "the leading-zero-ktsn accepted row must survive"
    ktsn_value = by_name["Testus leadingzero"]["ktsn"]
    assert ktsn_value == "090000000103", (
        f"ktsn must be preserved as a string, leading zero intact (mirrors FR-QPB-118's existing "
        f"string-preservation rule) — got {ktsn_value!r}"
    )


# --- AC-QPB-107, half 3: genuine live re-derivation on an existing/reopened feature -------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "FR-QPB-125's own claim -- that changing selected_korean_name re-derives "
        "selected_scientific_name/selected_ktsn identically for a brand-new feature AND for an "
        "existing, already-saved feature reopened later, via QGIS's/QField's own standard "
        "live-default-value re-evaluation ('apply default upon update') -- is a genuine, live, "
        "running-editing-session behavior. This project's field-level structural configuration "
        "check above (test_ac107_field_is_derived_and_read_only_via_apply_on_update_default_value) "
        "confirms the QgsDefaultValue/applyOnUpdate/read-only configuration exists once, at the "
        "layer level -- which, by construction, applies identically to every feature of that "
        "layer, new or reopened, since it is not a per-feature/per-session mechanism the way "
        "Decision Log D-50's QML write-back hack was. Genuinely *exercising* QGIS's/QField's own "
        "live-default-value engine end-to-end on an already-saved, reopened feature requires a "
        "real, running editing session this harness cannot drive (no QField/QML runtime; this "
        "project's hard QGIS-isolation rule also bars constructing a QgsApplication for any "
        "diagnostic purpose)."
        "\n\nManual QA steps: (1) In QGIS Desktop or QField, open a generated Types 1-3 project "
        "and create a brand-new feature; select a selected_korean_name value and confirm "
        "selected_scientific_name/selected_ktsn populate immediately and are not manually "
        "editable. (2) Save the feature and close the form. (3) Reopen the same, now already-saved "
        "feature and change selected_korean_name to a different accepted name. (4) Confirm "
        "selected_scientific_name/selected_ktsn re-derive to match the new selection -- not stale, "
        "not requiring a project reload -- for this reopened-feature case too."
    )
)
def test_ac107_live_re_derivation_works_identically_for_a_reopened_already_saved_feature():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- AC-QPB-108 ----------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
def test_ac108_lookup_table_present_indexed_and_referenced_when_identification_disabled(
    acceptance_api, inspect_editor_widget, tmp_path, survey_type
):
    """FR-QPB-127/AC-QPB-108: with identification_enabled explicitly False, the accepted-name
    lookup table, its index, and the ValueRelation/derived-field configuration must all still be
    present and functional -- decoupled from FR-QPB-112's own, separate, much larger conditional
    bundling trigger."""
    result = _build_with_lookup_table(
        acceptance_api, tmp_path, survey_type, name=f"proj_ac108_{survey_type}"
    )
    assert result["success"], result.get("error_message")

    table_name = result.get("ktsn_lookup_table_name")
    assert table_name, (
        f"AC-QPB-108/FR-QPB-127: expected the accepted-name lookup table to be bundled even with "
        f"identification_enabled=False — got {result}"
    )

    conn = open_gpkg(result["gpkg_path"])
    try:
        indexed = _indexed_columns(conn, table_name)
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]
    finally:
        conn.close()
    assert {"taxon_kor_nm", "taxon_full_nm"} <= indexed, (
        f"AC-QPB-108: the lookup table must remain indexed even with identification disabled — "
        f"indexed columns: {indexed}"
    )
    assert row_count > 0, (
        "expected at least one accepted row bundled from the fixture reference data"
    )

    layer = NAME_FIELD_LAYER_BY_TYPE[survey_type]
    widget_info = inspect_editor_widget(result["project_dir"], layer, "selected_korean_name")
    assert widget_info["widget_type"] == "ValueRelation", (
        f"AC-QPB-108: the ValueRelation widget must be configured even with identification "
        f"disabled — got {widget_info}"
    )


def test_ac108_type4_vegetation_mapping_bundles_lookup_table_even_when_identification_is_disabled(
    acceptance_api, inspect_editor_widget, tmp_path
):
    """Type 4's dominant/subdominant pickers need the accepted-name lookup independently of photo ID."""
    result = _build_with_lookup_table(acceptance_api, tmp_path, "vegetation_mapping")
    assert result["success"], result.get("error_message")
    table_name = result.get("ktsn_lookup_table_name")
    assert table_name
    info = inspect_editor_widget(result["project_dir"], "community", "dominant_species")
    assert info["widget_type"] == "ValueRelation"
    assert info["referenced_layer_name"] == table_name


# --- AC-QPB-109 (new; Decision Log D-70; closes O-34) ---------------------------------------------
#
# FR-QPB-105 (further revised; Decision Log D-70): the same CSV-presence/required-column fail-early
# validation this suite's `test_post_mvp_reference_bundling.py::test_fr105_*` tests already exercise
# for the original `identification_enabled=True` trigger must now *also* fire for a Types 1-3 build
# with `identification_enabled=False`, because FR-QPB-127's unconditional accepted-name-lookup-table
# derivation (FR-QPB-126) reuses the same raw-CSV-reading pipeline regardless of that toggle. The
# two tests below are the structural mirror of
# `test_post_mvp_reference_bundling.py::test_fr105_missing_reference_csv_fails_build_early_with_a_
# clear_message`/`::test_fr105_reference_csv_missing_required_columns_fails_build_early`, adapted to
# this new, independent second trigger condition -- distinct from AC-QPB-108 above, which always
# supplies REFERENCE_DATA_VALID_SAMPLE_DIR and therefore never exercises this failure path.

RASTER_SUBDIR = ("rasters", "bce_inverse_corrected_probability_maps")


def _build_with_disabled_identification_and_reference_override(
    acceptance_api, tmp_path, survey_type: str, reference_data_dir, name: str = "proj"
):
    config = make_base_config(survey_type)
    config["identification_enabled"] = False
    config["_test_reference_data_dir"] = str(reference_data_dir)
    config.pop("canonical_reference_path", None)
    # AC-QPB-109 is the retained pre-D-95 raw-source compatibility contract.  Opt into it
    # explicitly so a missing legacy CSV cannot be confused with canonical-source fallback.
    config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    out_dir = tmp_path / name
    return acceptance_api.build_project(config, str(out_dir))


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
@pytest.mark.legacy_compatibility
def test_ac109_missing_raw_reference_csv_still_fails_build_early_when_identification_disabled(
    acceptance_api, tmp_path, survey_type
):
    """AC-QPB-109/FR-QPB-105 (further revised, D-70): a Types 1-3 build must still fail early when
    the raw KTSN reference CSV is missing entirely, even with `identification_enabled=False` --
    confirming the fail-early validation is not bypassed merely because identification itself is
    disabled."""
    empty_reference_dir = tmp_path / f"empty_reference_scaffold_ac109_{survey_type}"
    (empty_reference_dir / "tables").mkdir(parents=True)
    empty_reference_dir.joinpath(*RASTER_SUBDIR).mkdir(parents=True)

    result = _build_with_disabled_identification_and_reference_override(
        acceptance_api,
        tmp_path,
        survey_type,
        reference_data_dir=empty_reference_dir,
        name=f"proj_ac109_missing_csv_{survey_type}",
    )
    assert result["success"] is False, (
        "AC-QPB-109/FR-QPB-105 (further revised, D-70): a Types 1-3 build with a missing raw "
        "reference CSV must still fail early even when identification_enabled=False, since "
        "FR-QPB-127's unconditional accepted-name lookup-table derivation depends on this same "
        f"raw source data regardless of that toggle — got {result}"
    )
    assert result.get("error_code"), "expected a non-null error_code, not a bare failure"
    assert result.get("error_message"), (
        "AC-QPB-109/FR-QPB-105: the failure message must be clear, not a bare stack trace/exception"
    )


@pytest.mark.parametrize("survey_type", TYPES_1_TO_3)
@pytest.mark.legacy_compatibility
def test_ac109_reference_csv_missing_required_columns_still_fails_build_early_when_disabled(
    acceptance_api, tmp_path, survey_type
):
    """AC-QPB-109/FR-QPB-105 (further revised, D-70): same second, independent trigger condition as
    above, exercised via the "present but lacking a required column" variant of AC-QPB-109's own
    Given clause."""
    result = _build_with_disabled_identification_and_reference_override(
        acceptance_api,
        tmp_path,
        survey_type,
        reference_data_dir=REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR,
        name=f"proj_ac109_bad_columns_{survey_type}",
    )
    assert result["success"] is False, (
        "AC-QPB-109/FR-QPB-105 (further revised, D-70): a Types 1-3 build whose raw reference CSV "
        "lacks a required column must still fail early even when identification_enabled=False — "
        f"got {result}"
    )
    assert result.get("error_code"), "expected a non-null error_code, not a bare failure"
    assert result.get("error_message"), (
        "AC-QPB-109/FR-QPB-105: the failure message must be clear, not a bare stack trace/exception"
    )
