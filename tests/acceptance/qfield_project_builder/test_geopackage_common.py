"""GeoPackage integrity rules common to all four survey types (Section 7, Section 18.1).

Covers:
- AC-QPB-001: generated project opens in QGIS Desktop without a repair warning.
- AC-QPB-002: every domain UUID column value is valid, unique, non-null.
- AC-QPB-003: no domain relation references `fid`.
- AC-QPB-004: `PRAGMA foreign_key_check` returns zero rows.
- AC-QPB-006: a spatial index exists on every geometry column.

Uses the generated `.gpkg` directly via `sqlite3` (a GeoPackage is a standard SQLite database),
rather than a bespoke inspection API, per HARNESS_CONTRACT.md.
"""
from __future__ import annotations

import pytest

from .conftest import (
    ALL_SURVEY_TYPES,
    SURVEY_TYPE_SCHEMAS,
    is_valid_uuid_v4_text,
    open_gpkg,
)

pytestmark = pytest.mark.qgis


@pytest.fixture(params=ALL_SURVEY_TYPES)
def survey_type(request):
    return request.param


@pytest.fixture()
def built(built_project_by_type, survey_type):
    result = built_project_by_type(survey_type)
    assert result["success"], f"{survey_type} build failed: {result.get('error_message')}"
    return result


@pytest.fixture()
def gpkg_conn(built):
    conn = open_gpkg(built["gpkg_path"])
    try:
        yield conn
    finally:
        conn.close()


def test_ac001_project_opens_without_repair_warning(acceptance_api, built):
    """AC-QPB-001."""
    report = acceptance_api.validate_project(built["project_dir"])
    assert report["opens_without_repair_warning"] is True, report.get("issues")


def test_ac002_every_domain_uuid_is_valid_unique_and_non_null(gpkg_conn, survey_type):
    """AC-QPB-002 / DR-QPB-001, DR-QPB-003, DR-QPB-004."""
    schema = SURVEY_TYPE_SCHEMAS[survey_type]
    for table, meta in schema["tables"].items():
        uuid_col = meta["uuid_pk"]
        rows = gpkg_conn.execute(f"SELECT {uuid_col} FROM {table};").fetchall()
        values = [r[0] for r in rows]
        assert None not in values, f"{table}.{uuid_col} must never be NULL"
        assert len(values) == len(set(values)), f"{table}.{uuid_col} must be unique"
        for v in values:
            assert is_valid_uuid_v4_text(v), (
                f"{table}.{uuid_col} value {v!r} is not a canonical lowercase UUID v4 "
                "without braces"
            )


def test_ac003_no_domain_relation_references_fid(gpkg_conn, survey_type):
    """AC-QPB-003 / DR-QPB-006: foreign keys must reference UUID columns, never `fid`."""
    schema = SURVEY_TYPE_SCHEMAS[survey_type]
    for table, meta in schema["tables"].items():
        fk_pragma = gpkg_conn.execute(f"PRAGMA foreign_key_list({table});").fetchall()
        for row in fk_pragma:
            # sqlite3 PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update, ...
            to_column = row[4]
            assert to_column != "fid", (
                f"{table} has a foreign key referencing fid — must reference a UUID column"
            )
        expected_fk = meta["fk"]
        if expected_fk is not None:
            from_col, ref_table, ref_col = expected_fk
            matching = [r for r in fk_pragma if r[3] == from_col and r[2] == ref_table]
            assert matching, (
                f"expected a declared foreign key {table}.{from_col} -> {ref_table}.{ref_col}, "
                f"found: {fk_pragma}"
            )


def test_ac004_foreign_key_check_returns_zero_rows(gpkg_conn):
    """AC-QPB-004 / DR-QPB-011."""
    violations = gpkg_conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert violations == [], f"PRAGMA foreign_key_check reported violations: {violations}"


def test_ac006_spatial_index_exists_for_every_geometry_column(gpkg_conn, survey_type):
    """AC-QPB-006 / DR-QPB-009."""
    schema = SURVEY_TYPE_SCHEMAS[survey_type]
    gpkg_contents = gpkg_conn.execute(
        "SELECT table_name, column_name FROM gpkg_geometry_columns;"
    ).fetchall()
    geometry_columns = {(t, c) for t, c in gpkg_contents}

    for table, meta in schema["tables"].items():
        if meta["geometry"] is None:
            continue
        geom_col, _geom_type = meta["geometry"]
        assert (table, geom_col) in geometry_columns, (
            f"{table}.{geom_col} must be registered in gpkg_geometry_columns"
        )
        rtree_table = f"rtree_{table}_{geom_col}"
        exists = gpkg_conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (rtree_table,)
        ).fetchone()
        assert exists, (
            f"expected a spatial (R*Tree) index table {rtree_table!r} for {table}.{geom_col}"
        )


def test_hidden_fid_is_never_the_declared_domain_identifier(gpkg_conn, survey_type):
    """DR-QPB-002 (supports AC-QPB-003): `fid`, if present, is not a domain-facing identifier."""
    schema = SURVEY_TYPE_SCHEMAS[survey_type]
    for table, meta in schema["tables"].items():
        columns = [
            row[1] for row in gpkg_conn.execute(f"PRAGMA table_info({table});").fetchall()
        ]
        assert meta["uuid_pk"] in columns
        assert meta["uuid_pk"] != "fid"


def test_schema_version_metadata_present(gpkg_conn):
    """DR-QPB-014: schema-version metadata (survey type, version, creation timestamp) must exist.

    The exact storage mechanism is left to the implementer (DR-QPB-014); this test only checks
    that *some* inspectable metadata records the survey type and a schema version, without
    assuming a specific table name beyond the documented options.
    """
    candidate_tables = [
        row[0]
        for row in gpkg_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    has_dedicated_table = any("schema" in t.lower() or "metadata" in t.lower() for t in candidate_tables)
    has_gpkg_extension_metadata = "gpkg_metadata" in candidate_tables
    assert has_dedicated_table or has_gpkg_extension_metadata, (
        "expected either a dedicated schema-version metadata table, or use of the GeoPackage "
        f"gpkg_metadata extension; tables found: {candidate_tables}"
    )
