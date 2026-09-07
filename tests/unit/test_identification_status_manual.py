"""Unit tests for Decision Log D-43: the new `manual` `identification_status` enum value.

FR-QPB-109 (further revised; Decision Log D-43) adds an explicit `manual` enum value to the
`identification_status` column (Section 8.1/8.2), reserved for a manually-entered identification
and distinct from `complete` (a real, persisted Pl@ntNet candidate selection). AC-QPB-046
(revised)/AC-QPB-078 make this independently testable at both the GeoPackage-schema level and the
generated-QML-plugin level.
"""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from qfield_builder.gpkg import build_geopackage
from qfield_builder.gpkg_functions import register_gpkg_functions
from qfield_builder.naming import new_project_id
from qfield_builder.schemas import _IDENTIFICATION_STATUS_VALUES
from qfield_builder.wkt import wkt_to_gpkg_geometry

SITE_WKT = "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"


def _open(path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON;")
    register_gpkg_functions(conn)
    return conn


def _build(tmp_path, survey_type, **seed_kwargs):
    path = tmp_path / f"{survey_type}.gpkg"
    build_geopackage(str(path), survey_type, new_project_id(), **seed_kwargs)
    return path


def test_manual_is_one_of_the_documented_identification_status_values():
    assert "manual" in _IDENTIFICATION_STATUS_VALUES
    # `complete` remains distinct from `manual` -- both values continue to exist.
    assert "complete" in _IDENTIFICATION_STATUS_VALUES


def test_identification_status_check_constraint_accepts_manual_via_raw_sql(tmp_path):
    """Section 8.1/8.2 CHECK constraint: `manual` must now be accepted for `observation`."""
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
        # Must not raise -- "manual" is now an accepted identification_status value.
        conn.execute(
            'INSERT INTO observation (observation_id, survey_id, cover, identification_status) '
            "VALUES (?, ?, ?, ?);",
            (str(uuid.uuid4()), survey_id, 50, "manual"),
        )
        row = conn.execute(
            "SELECT identification_status FROM observation WHERE survey_id = ?;", (survey_id,)
        ).fetchone()
        assert row[0] == "manual"
    finally:
        conn.close()


def test_identification_status_check_constraint_still_rejects_invalid_values(tmp_path):
    """The CHECK constraint must still reject values outside the documented enum."""
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
                'INSERT INTO observation (observation_id, survey_id, cover, '
                "identification_status) VALUES (?, ?, ?, ?);",
                (str(uuid.uuid4()), survey_id, 50, "bogus_status"),
            )
    finally:
        conn.close()


def test_identification_status_check_constraint_accepts_manual_on_inventory_observation(
    tmp_path,
):
    """Same CHECK constraint, Type 1 `inventory_observation` table (Section 8.1)."""
    path = _build(tmp_path, "simple_inventory")
    conn = _open(path)
    try:
        blob, _envelope = wkt_to_gpkg_geometry("POINT(127.005 37.005)", "POINT")
        conn.execute(
            "INSERT INTO inventory_observation "
            "(inventory_id, surveyor, identification_status, geom) "
            "VALUES (?, ?, ?, ?);",
            (str(uuid.uuid4()), "Field Researcher", "manual", blob),
        )
        row = conn.execute(
            "SELECT identification_status FROM inventory_observation;"
        ).fetchone()
        assert row[0] == "manual"
    finally:
        conn.close()
