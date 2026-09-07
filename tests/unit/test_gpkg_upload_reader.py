"""Unit tests for qfield_builder.gpkg_upload_reader (FR-QPB-025 GeoPackage site/plot uploads).

These fixtures are built directly via plain :mod:`sqlite3` (plus this codebase's own
:mod:`qfield_builder.wkt` geometry-encoding helpers) rather than through
:func:`qfield_builder.gpkg.build_geopackage`, to genuinely stand in for an arbitrary *externally*
produced GeoPackage (e.g. one authored by QGIS) -- exactly the kind of input
:mod:`qfield_builder.gpkg_upload_reader` documents itself as needing to read, not one this
application necessarily created itself.
"""
from __future__ import annotations

import sqlite3
import struct

import pytest

from qfield_builder.errors import BuildError
from qfield_builder.gpkg_upload_reader import (
    first_feature_layer_info,
    list_feature_layer_fields,
    read_first_feature_layer,
)
from qfield_builder.wkt import wkb_to_gpkg_blob, wkt_to_gpkg_geometry

VALID_SITE_WKT = (
    "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
)


def _build_minimal_external_gpkg(
    path: str,
    features: list[tuple[str, str]],
    *,
    table: str = "sites",
    geom_col: str = "geom",
    name_col: str = "name",
    geom_type_name: str = "MULTIPOLYGON",
    srs_id: int = 4326,
) -> None:
    """Build a minimal, externally-authored-style GeoPackage: just enough of the
    `gpkg_contents`/`gpkg_geometry_columns` bookkeeping tables plus one real feature table for
    `gpkg_upload_reader` to discover and read -- deliberately not using this application's own
    schema/builder, since an uploaded GeoPackage is not guaranteed to have been produced by it.
    """
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            f"""
            CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT);
            CREATE TABLE gpkg_geometry_columns (
                table_name TEXT, column_name TEXT, geometry_type_name TEXT,
                srs_id INTEGER, z TINYINT, m TINYINT
            );
            CREATE TABLE "{table}" (
                "fid" INTEGER PRIMARY KEY AUTOINCREMENT,
                "{name_col}" TEXT,
                "{geom_col}" BLOB
            );
            """
        )
        conn.execute(
            "INSERT INTO gpkg_contents (table_name, data_type) VALUES (?, 'features');", (table,)
        )
        conn.execute(
            "INSERT INTO gpkg_geometry_columns "
            "(table_name, column_name, geometry_type_name, srs_id, z, m) "
            "VALUES (?, ?, ?, ?, 0, 0);",
            (table, geom_col, geom_type_name, srs_id),
        )
        for name, wkt in features:
            blob, _ = wkt_to_gpkg_geometry(wkt, geom_type_name, srs_id=srs_id)
            conn.execute(
                f'INSERT INTO "{table}" ("{name_col}", "{geom_col}") VALUES (?, ?);', (name, blob)
            )
        conn.commit()
    finally:
        conn.close()


def test_list_feature_layer_fields_returns_non_geometry_columns(tmp_path):
    gpkg_path = str(tmp_path / "sites.gpkg")
    _build_minimal_external_gpkg(gpkg_path, [("Site A", VALID_SITE_WKT)], name_col="site_name")

    fields = list_feature_layer_fields(gpkg_path)

    assert fields == ["site_name"]


def test_first_feature_layer_info_reports_declared_srs_id(tmp_path):
    gpkg_path = str(tmp_path / "sites.gpkg")
    _build_minimal_external_gpkg(
        gpkg_path,
        [("Site A", VALID_SITE_WKT)],
        table="boundaries",
        srs_id=5186,
    )

    assert first_feature_layer_info(gpkg_path) == {"table_name": "boundaries", "srs_id": 5186}


def test_read_first_feature_layer_returns_attributes_and_wkt(tmp_path):
    gpkg_path = str(tmp_path / "sites.gpkg")
    _build_minimal_external_gpkg(
        gpkg_path,
        [("Site A", VALID_SITE_WKT)],
        name_col="site_name",
    )

    rows = read_first_feature_layer(gpkg_path)

    assert len(rows) == 1
    assert rows[0]["attributes"] == {"site_name": "Site A"}
    assert rows[0]["geom_wkt"] == (
        "MULTIPOLYGON(((127.0 37.0, 127.01 37.0, 127.01 37.01, 127.0 37.01, 127.0 37.0)))"
    )


def test_read_first_feature_layer_multiple_rows(tmp_path):
    gpkg_path = str(tmp_path / "sites.gpkg")
    other_wkt = (
        "MULTIPOLYGON(((128.00 38.00, 128.01 38.00, 128.01 38.01, 128.00 38.01, 128.00 38.00)))"
    )
    _build_minimal_external_gpkg(
        gpkg_path,
        [("Site A", VALID_SITE_WKT), ("Site B", other_wkt)],
        name_col="site_name",
    )

    rows = read_first_feature_layer(gpkg_path)

    assert [r["attributes"]["site_name"] for r in rows] == ["Site A", "Site B"]


def test_read_first_feature_layer_skips_null_geometry_rows(tmp_path):
    gpkg_path = str(tmp_path / "sites.gpkg")
    _build_minimal_external_gpkg(gpkg_path, [("Site A", VALID_SITE_WKT)], name_col="site_name")
    conn = sqlite3.connect(gpkg_path)
    conn.execute('INSERT INTO "sites" ("site_name", "geom") VALUES (?, NULL);', ("Site NoGeom",))
    conn.commit()
    conn.close()

    rows = read_first_feature_layer(gpkg_path)

    assert len(rows) == 1
    assert rows[0]["attributes"]["site_name"] == "Site A"


def test_read_first_feature_layer_rejects_non_sqlite_file(tmp_path):
    bogus_path = tmp_path / "not_a_gpkg.gpkg"
    bogus_path.write_text("this is not a sqlite database")

    with pytest.raises(BuildError) as excinfo:
        read_first_feature_layer(str(bogus_path))
    assert excinfo.value.error_code == "malformed_upload"


def test_read_first_feature_layer_rejects_gpkg_with_no_feature_layer(tmp_path):
    gpkg_path = str(tmp_path / "empty.gpkg")
    conn = sqlite3.connect(gpkg_path)
    conn.execute("CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT);")
    conn.commit()
    conn.close()

    with pytest.raises(BuildError) as excinfo:
        read_first_feature_layer(gpkg_path)
    assert excinfo.value.error_code == "malformed_upload"


def test_read_first_feature_layer_decodes_z_dimensioned_polygon(
    tmp_path,
):
    """A GeoPackage whose geometry has a Z ordinate (e.g. QGIS's "Include Z dimension" option)
    must consume the extra ordinate without corrupting or dropping the eligible polygon row."""
    gpkg_path = str(tmp_path / "z_sites.gpkg")
    conn = sqlite3.connect(gpkg_path)
    conn.executescript(
        """
        CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT);
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT, column_name TEXT, geometry_type_name TEXT,
            srs_id INTEGER, z TINYINT, m TINYINT
        );
        CREATE TABLE "sites" (
            "fid" INTEGER PRIMARY KEY AUTOINCREMENT,
            "site_name" TEXT,
            "geom" BLOB
        );
        """
    )
    conn.execute("INSERT INTO gpkg_contents (table_name, data_type) VALUES ('sites', 'features');")
    conn.execute(
        "INSERT INTO gpkg_geometry_columns "
        "(table_name, column_name, geometry_type_name, srs_id, z, m) "
            "VALUES ('sites', 'geom', 'POLYGON', 4326, 1, 0);"
    )
    ring = [(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01), (127.0, 37.0)]
    polygon_z_wkb = struct.pack("<BI", 1, 1003) + struct.pack("<II", 1, len(ring))
    polygon_z_wkb += b"".join(struct.pack("<ddd", x, y, 55.0) for x, y in ring)
    blob = wkb_to_gpkg_blob(polygon_z_wkb, srs_id=4326)
    conn.execute('INSERT INTO "sites" ("site_name", "geom") VALUES (?, ?);', ("Site Z", blob))
    conn.commit()
    conn.close()

    rows = read_first_feature_layer(gpkg_path)
    assert len(rows) == 1
    assert rows[0]["geom_wkt"].startswith("POLYGON((127.0 37.0")
