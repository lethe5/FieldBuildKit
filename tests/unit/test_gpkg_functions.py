"""Unit tests for qfield_builder.gpkg_functions (ST_MinX/MaxX/MinY/MaxY/IsEmpty)."""
from __future__ import annotations

import sqlite3

from qfield_builder.gpkg_functions import register_gpkg_functions, st_is_empty
from qfield_builder.wkt import wkt_to_gpkg_geometry


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    register_gpkg_functions(conn)
    return conn


def test_st_min_max_match_python_computed_envelope():
    blob, envelope = wkt_to_gpkg_geometry(
        "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))",
        "MULTIPOLYGON",
    )
    conn = _connection()
    row = conn.execute(
        "SELECT ST_MinX(?), ST_MaxX(?), ST_MinY(?), ST_MaxY(?);", (blob, blob, blob, blob)
    ).fetchone()
    assert row[0] == envelope.min_x
    assert row[1] == envelope.max_x
    assert row[2] == envelope.min_y
    assert row[3] == envelope.max_y


def test_st_min_max_for_point():
    blob, envelope = wkt_to_gpkg_geometry("POINT(127.005 37.005)", "POINT")
    conn = _connection()
    row = conn.execute("SELECT ST_MinX(?), ST_MinY(?);", (blob, blob)).fetchone()
    assert row == (envelope.min_x, envelope.min_y)


def test_st_is_empty_false_for_valid_geometry():
    blob, _ = wkt_to_gpkg_geometry("POINT(127.005 37.005)", "POINT")
    conn = _connection()
    assert conn.execute("SELECT ST_IsEmpty(?);", (blob,)).fetchone()[0] == 0
    assert st_is_empty(blob) == 0


def test_st_is_empty_true_for_none_or_garbage():
    assert st_is_empty(None) == 1
    assert st_is_empty(b"not-a-geometry") == 1


def test_functions_work_with_no_envelope_in_header():
    from qfield_builder.wkt import wkb_to_gpkg_blob, wkt_to_wkb

    wkb = wkt_to_wkb("POINT(1.0 2.0)", "POINT")
    blob = wkb_to_gpkg_blob(wkb, srs_id=4326, envelope=None)
    conn = _connection()
    row = conn.execute("SELECT ST_MinX(?), ST_MinY(?);", (blob, blob)).fetchone()
    assert row == (1.0, 2.0)
