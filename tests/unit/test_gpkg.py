"""Unit tests for qfield_builder.gpkg — mirrors the acceptance suite's AC-QPB-002/003/004/005/006
checks (test_geopackage_common.py / test_geopackage_schema_by_type.py) but runs entirely via
plain sqlite3, so it exercises the same GeoPackage-correctness guarantees without requiring a
real QGIS/PyQGIS/GDAL runtime.
"""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from qfield_builder.gpkg import add_ktsn_lookup_table, build_geopackage
from qfield_builder.gpkg_functions import register_gpkg_functions
from qfield_builder.naming import new_project_id
from qfield_builder.schemas import SURVEY_TYPES, get_schema

SITE_WKT = "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
PLOT_WKT = "POINT(127.005 37.005)"


def _open(path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON;")
    register_gpkg_functions(conn)
    return conn


def _build(tmp_path, survey_type, **seed_kwargs):
    path = tmp_path / f"{survey_type}.gpkg"
    build_geopackage(str(path), survey_type, new_project_id(), **seed_kwargs)
    return path


@pytest.mark.parametrize("survey_type", SURVEY_TYPES)
def test_every_table_from_schema_exists_with_uuid_pk(tmp_path, survey_type):
    path = _build(tmp_path, survey_type)
    conn = _open(path)
    try:
        schema = get_schema(survey_type)
        for table_name, table_def in schema.items():
            columns = {
                row[1]: row for row in conn.execute(f'PRAGMA table_info("{table_name}");')
            }
            assert table_def.uuid_pk in columns, f"{table_name} missing {table_def.uuid_pk}"
            _, _, _, notnull, _, _ = columns[table_def.uuid_pk]
            assert notnull == 1
    finally:
        conn.close()


@pytest.mark.parametrize("survey_type", SURVEY_TYPES)
def test_no_domain_relation_references_fid(tmp_path, survey_type):
    path = _build(tmp_path, survey_type)
    conn = _open(path)
    try:
        schema = get_schema(survey_type)
        for table_name, table_def in schema.items():
            for row in conn.execute(f'PRAGMA foreign_key_list("{table_name}");'):
                assert row[4] != "fid"
            if table_def.foreign_key is not None:
                fk = table_def.foreign_key
                fk_rows = conn.execute(f'PRAGMA foreign_key_list("{table_name}");').fetchall()
                matching = [r for r in fk_rows if r[3] == fk.column and r[2] == fk.ref_table]
                assert matching, f"expected FK {table_name}.{fk.column} -> {fk.ref_table}"
    finally:
        conn.close()


@pytest.mark.parametrize("survey_type", SURVEY_TYPES)
def test_foreign_key_check_clean_on_fresh_geopackage(tmp_path, survey_type):
    path = _build(
        tmp_path,
        survey_type,
        seed_sites=(
            [{"site_name": "Site A", "geom_wkt": SITE_WKT}]
            if survey_type != "simple_inventory"
            else None
        ),
    )
    conn = _open(path)
    try:
        assert conn.execute("PRAGMA foreign_key_check;").fetchall() == []
    finally:
        conn.close()


@pytest.mark.parametrize("survey_type", SURVEY_TYPES)
def test_spatial_index_exists_for_every_geometry_column(tmp_path, survey_type):
    path = _build(tmp_path, survey_type)
    conn = _open(path)
    try:
        schema = get_schema(survey_type)
        for table_name, table_def in schema.items():
            if table_def.geometry is None:
                continue
            rtree_table = f"rtree_{table_name}_{table_def.geometry.column}"
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (rtree_table,)
            ).fetchone()
            assert exists, f"missing {rtree_table}"
    finally:
        conn.close()


@pytest.mark.parametrize("survey_type", SURVEY_TYPES)
def test_geometry_columns_registered_with_correct_type_and_srs(tmp_path, survey_type):
    path = _build(tmp_path, survey_type)
    conn = _open(path)
    try:
        schema = get_schema(survey_type)
        registered = {
            (t, c): (geom_type, srs_id)
            for t, c, geom_type, srs_id in conn.execute(
                "SELECT table_name, column_name, geometry_type_name, srs_id "
                "FROM gpkg_geometry_columns;"
            )
        }
        for table_name, table_def in schema.items():
            if table_def.geometry is None:
                continue
            geom_type, srs_id = registered[(table_name, table_def.geometry.column)]
            assert geom_type == table_def.geometry.geom_type
            org, code = conn.execute(
                "SELECT organization, organization_coordsys_id FROM gpkg_spatial_ref_sys "
                "WHERE srs_id = ?;",
                (srs_id,),
            ).fetchone()
            assert org.upper() == "EPSG" and int(code) == 4326
    finally:
        conn.close()


def test_cover_check_constraint_rejects_out_of_range_via_raw_sql(tmp_path):
    path = _build(
        tmp_path,
        "temporary_plots",
        seed_sites=[{"site_name": "Site A", "geom_wkt": SITE_WKT}],
    )
    conn = _open(path)
    try:
        site_id = conn.execute("SELECT site_id FROM site;").fetchone()[0]
        survey_id = str(uuid.uuid4())
        conn.execute(
            'INSERT INTO survey (survey_id, site_id, surveyor, plot_size) VALUES (?, ?, ?, ?);',
            (survey_id, site_id, "Field Researcher", "5x5"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                'INSERT INTO observation (observation_id, survey_id, cover) VALUES (?, ?, ?);',
                (str(uuid.uuid4()), survey_id, 101),
            )
    finally:
        conn.close()


def test_type1_photo_columns_are_nullable_and_relation_free(tmp_path):
    path = _build(tmp_path, "simple_inventory")
    conn = _open(path)
    try:
        columns = {
            row[1]: row for row in conn.execute('PRAGMA table_info("inventory_observation");')
        }
        for col in ("leaf_photo_path", "flower_photo_path", "fruit_photo_path"):
            assert col in columns
            assert columns[col][3] == 0  # notnull == 0
        assert conn.execute('PRAGMA foreign_key_list("inventory_observation");').fetchall() == []
    finally:
        conn.close()


def test_community_keeps_identity_write_back_columns_absent_but_has_photo_paths(tmp_path):
    path = _build(
        tmp_path,
        "vegetation_mapping",
        seed_sites=[{"site_name": "Site A", "geom_wkt": SITE_WKT}],
    )
    conn = _open(path)
    try:
        columns = {row[1] for row in conn.execute('PRAGMA table_info("community");')}
        for forbidden in (
            "selected_korean_name",
            "selected_scientific_name",
            "selected_ktsn",
            "identification_score",
            "occurrence_probability",
            "identification_status",
        ):
            assert forbidden not in columns
        for photo_path in ("leaf_photo_path", "flower_photo_path", "fruit_photo_path"):
            assert photo_path in columns
    finally:
        conn.close()


def test_seed_site_and_permanent_plot_are_written_with_valid_geometry(tmp_path):
    path = _build(
        tmp_path,
        "permanent_plots",
        seed_sites=[{"site_name": "Site A", "geom_wkt": SITE_WKT}],
        seed_plots=[{"plot_name": "Plot A-1", "geom_wkt": PLOT_WKT, "plot_size": "10x10"}],
    )
    conn = _open(path)
    try:
        site_row = conn.execute("SELECT site_id, site_name FROM site;").fetchone()
        assert site_row[1] == "Site A"
        plot_row = conn.execute("SELECT plot_name, site_id FROM plot;").fetchone()
        assert plot_row[0] == "Plot A-1"
        assert plot_row[1] == site_row[0]
    finally:
        conn.close()


def test_temporary_plot_seed_points_have_null_date_and_surveyor(tmp_path):
    path = _build(
        tmp_path,
        "temporary_plots",
        seed_sites=[{"site_name": "Site A", "geom_wkt": SITE_WKT}],
        seed_temporary_plot_points=[
            {"site_name": "Site A", "geom_wkt": PLOT_WKT, "plot_size": "5x5"}
        ],
    )
    conn = _open(path)
    try:
        row = conn.execute("SELECT survey_date, surveyor FROM survey;").fetchone()
        assert row == (None, None)
    finally:
        conn.close()


def test_schema_version_metadata_present(tmp_path):
    path = _build(tmp_path, "simple_inventory")
    conn = _open(path)
    try:
        row = conn.execute(
            "SELECT survey_type, schema_version FROM qpb_schema_metadata;"
        ).fetchone()
        assert row[0] == "simple_inventory"
        assert row[1]
    finally:
        conn.close()


def test_invalid_seed_geometry_raises_before_commit(tmp_path):
    from qfield_builder.wkt import InvalidGeometryError

    with pytest.raises(InvalidGeometryError):
        _build(
            tmp_path,
            "temporary_plots",
            seed_sites=[
                {
                    "site_name": "Bad",
                    "geom_wkt": (
                        "POLYGON((127.00 37.00, 127.01 37.01, 127.00 37.01, 127.01 37.00, "
                        "127.00 37.00))"
                    ),
                }
            ],
        )


# ================================================================================================
# DR-QPB-072/FR-QPB-126/FR-QPB-127 (Decision Log D-66/D-67/D-68) -- add_ktsn_lookup_table()
# ================================================================================================

_LOOKUP_ROWS = [
    {"ktsn": "120000000001", "taxon_kor_nm": "테스트종", "taxon_full_nm": "Testus demo"},
    {"ktsn": "012000000002", "taxon_kor_nm": "", "taxon_full_nm": "Alius demo"},
]


def test_add_ktsn_lookup_table_creates_table_with_expected_rows(tmp_path):
    path = _build(tmp_path, "simple_inventory")
    add_ktsn_lookup_table(str(path), "ktsn_accepted_name_lookup", _LOOKUP_ROWS)

    conn = _open(path)
    try:
        rows = conn.execute(
            "SELECT ktsn, taxon_kor_nm, taxon_full_nm FROM ktsn_accepted_name_lookup "
            "ORDER BY ktsn;"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [
        ("012000000002", "", "Alius demo"),
        ("120000000001", "테스트종", "Testus demo"),
    ]


def test_add_ktsn_lookup_table_preserves_leading_zero_ktsn_as_text(tmp_path):
    path = _build(tmp_path, "simple_inventory")
    add_ktsn_lookup_table(str(path), "ktsn_accepted_name_lookup", _LOOKUP_ROWS)

    conn = _open(path)
    try:
        value = conn.execute(
            "SELECT ktsn FROM ktsn_accepted_name_lookup WHERE taxon_full_nm = 'Alius demo';"
        ).fetchone()[0]
    finally:
        conn.close()
    assert value == "012000000002"


def test_add_ktsn_lookup_table_creates_indexes_on_korean_and_scientific_name_columns(tmp_path):
    """AC-QPB-106/O-32: a real, build-time `CREATE INDEX` on the Korean-name and scientific-name
    columns -- not the in-memory JavaScript index technique used elsewhere for this same CSV."""
    path = _build(tmp_path, "simple_inventory")
    add_ktsn_lookup_table(str(path), "ktsn_accepted_name_lookup", _LOOKUP_ROWS)

    conn = _open(path)
    try:
        indexed_columns: set[str] = set()
        for _seq, index_name, *_rest in conn.execute(
            'PRAGMA index_list("ktsn_accepted_name_lookup");'
        ).fetchall():
            for _seqno, _cid, col_name in conn.execute(
                f'PRAGMA index_info("{index_name}");'
            ).fetchall():
                if col_name is not None:
                    indexed_columns.add(col_name)
    finally:
        conn.close()
    assert {"taxon_kor_nm", "taxon_full_nm"} <= indexed_columns


def test_add_ktsn_lookup_table_registered_as_attributes_table_in_gpkg_contents(tmp_path):
    path = _build(tmp_path, "simple_inventory")
    add_ktsn_lookup_table(str(path), "ktsn_accepted_name_lookup", _LOOKUP_ROWS)

    conn = _open(path)
    try:
        row = conn.execute(
            "SELECT data_type FROM gpkg_contents WHERE table_name = 'ktsn_accepted_name_lookup';"
        ).fetchone()
    finally:
        conn.close()
    assert row == ("attributes",)


def test_add_ktsn_lookup_table_no_uuid_primary_key(tmp_path):
    """DR-QPB-072's own explicit carve-out from DR-QPB-001: this table's key column is the source
    data's own natural `ktsn` identifier, not a newly generated UUID."""
    path = _build(tmp_path, "simple_inventory")
    add_ktsn_lookup_table(str(path), "ktsn_accepted_name_lookup", _LOOKUP_ROWS)

    conn = _open(path)
    try:
        columns = {
            row[1] for row in conn.execute('PRAGMA table_info("ktsn_accepted_name_lookup");')
        }
    finally:
        conn.close()
    assert columns == {"fid", "ktsn", "taxon_kor_nm", "taxon_full_nm"}
