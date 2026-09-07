"""Unit tests for qfield_builder.feature_save's SQLite fallback path.

Deliberately calls `_attempt_feature_save_sqlite_fallback` directly (rather than the public
`attempt_feature_save` dispatcher) so this module exercises the same constraint rules
(schemas.py) that the primary PyQGIS path also enforces via QgsFieldConstraints, without
requiring — or depending on the absence of — a real QGIS runtime. `attempt_feature_save`'s
PyQGIS-vs-fallback dispatch, and the PyQGIS-path behavior itself, are covered by the acceptance
suite (`tests/acceptance/qfield_project_builder/`) and, for the fixtures below (which build a
GeoPackage only, no `.qgs` project), would otherwise be rejected purely for having no `.qgs` file
to open on a machine that does have a working QGIS bridge — a fixture-setup gap unrelated to
what these tests are actually about.
"""
from __future__ import annotations

import sqlite3

import pytest

from qfield_builder.feature_save import _attempt_feature_save_sqlite_fallback
from qfield_builder.gpkg import build_geopackage
from qfield_builder.naming import new_project_id


def attempt_feature_save(project_dir, layer_name, attributes, geometry_wkt=None):
    return _attempt_feature_save_sqlite_fallback(project_dir, layer_name, attributes, geometry_wkt)

SITE_WKT = "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"


@pytest.fixture()
def temp_plots_project(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "data").mkdir(parents=True)
    build_geopackage(
        str(project_dir / "data" / "project.gpkg"),
        "temporary_plots",
        new_project_id(),
        seed_sites=[{"site_name": "Site A", "geom_wkt": SITE_WKT}],
    )
    return project_dir


@pytest.fixture()
def simple_inventory_project(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "data").mkdir(parents=True)
    build_geopackage(
        str(project_dir / "data" / "project.gpkg"), "simple_inventory", new_project_id()
    )
    return project_dir


def _site_id(project_dir) -> str:
    conn = sqlite3.connect(str(project_dir / "data" / "project.gpkg"))
    try:
        return conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()


@pytest.mark.parametrize("bad_cover", [-1, 101, 1000, -100])
def test_cover_out_of_range_rejected(temp_plots_project, bad_cover):
    site_id = _site_id(temp_plots_project)
    survey = attempt_feature_save(
        str(temp_plots_project),
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5x5", "site_id": site_id},
        geometry_wkt="POINT(127.005 37.005)",
    )
    assert survey["accepted"]
    outcome = attempt_feature_save(
        str(temp_plots_project),
        "observation",
        {
            "cover": bad_cover,
            "selected_scientific_name": "Test taxon",
            "survey_id": survey["generated_uuid"],
        },
    )
    assert outcome["accepted"] is False
    assert outcome["rejected_field"] == "cover"


@pytest.mark.parametrize("good_cover", [0, 1, 50, 100])
def test_cover_within_range_accepted(temp_plots_project, good_cover):
    site_id = _site_id(temp_plots_project)
    survey = attempt_feature_save(
        str(temp_plots_project),
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5x5", "site_id": site_id},
        geometry_wkt="POINT(127.005 37.005)",
    )
    outcome = attempt_feature_save(
        str(temp_plots_project),
        "observation",
        {
            "cover": good_cover,
            "selected_scientific_name": "Test taxon",
            "survey_id": survey["generated_uuid"],
        },
    )
    assert outcome["accepted"] is True
    assert outcome["generated_uuid"]


def test_type1_photo_field_combinations_all_accepted(simple_inventory_project):
    combos = [
        {},
        {"leaf_photo_path": "attachments/leaf1.jpg"},
        {"leaf_photo_path": "attachments/leaf1.jpg", "flower_photo_path": "attachments/fl1.jpg"},
        {
            "leaf_photo_path": "attachments/leaf1.jpg",
            "flower_photo_path": "attachments/fl1.jpg",
            "fruit_photo_path": "attachments/fr1.jpg",
        },
    ]
    for combo in combos:
        outcome = attempt_feature_save(
            str(simple_inventory_project),
            "inventory_observation",
            {"surveyor": "Field Researcher", "selected_scientific_name": "Test taxon", **combo},
            geometry_wkt="POINT(127.0 37.0)",
        )
        assert outcome["accepted"] is True, (combo, outcome)


@pytest.mark.parametrize(
    "bad_path",
    ["", "   ", "/etc/photos/leaf.jpg", "C:\\Users\\x\\leaf.jpg", "\\\\server\\share\\leaf.jpg", "file:///x/leaf.jpg"],
)
def test_malformed_attachment_path_rejected_at_save_time(temp_plots_project, bad_path):
    site_id = _site_id(temp_plots_project)
    survey = attempt_feature_save(
        str(temp_plots_project),
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5x5", "site_id": site_id},
        geometry_wkt="POINT(127.006 37.006)",
    )
    outcome = attempt_feature_save(
        str(temp_plots_project),
        "survey_photo",
        {
            "survey_id": survey["generated_uuid"],
            "path": bad_path,
            "captured_at": "2026-08-10T09:00:00+09:00",
        },
    )
    assert outcome["accepted"] is False


def test_valid_relative_attachment_path_accepted(temp_plots_project):
    site_id = _site_id(temp_plots_project)
    survey = attempt_feature_save(
        str(temp_plots_project),
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5x5", "site_id": site_id},
        geometry_wkt="POINT(127.007 37.007)",
    )
    outcome = attempt_feature_save(
        str(temp_plots_project),
        "survey_photo",
        {
            "survey_id": survey["generated_uuid"],
            "path": "attachments/survey1.jpg",
            "captured_at": "2026-08-10T09:00:00+09:00",
        },
    )
    assert outcome["accepted"] is True


def test_required_text_field_rejects_empty_or_whitespace(simple_inventory_project):
    for bad_value in ["", "   "]:
        outcome = attempt_feature_save(
            str(simple_inventory_project),
            "inventory_observation",
            {"surveyor": bad_value, "selected_scientific_name": "Test taxon"},
            geometry_wkt="POINT(127.0 37.0)",
        )
        assert outcome["accepted"] is False
        assert outcome["rejected_field"] == "surveyor"


def test_zero_related_photos_never_blocks_parent_save(temp_plots_project):
    site_id = _site_id(temp_plots_project)
    outcome = attempt_feature_save(
        str(temp_plots_project),
        "survey",
        {"surveyor": "Field Researcher", "plot_size": "5x5", "site_id": site_id},
        geometry_wkt="POINT(127.009 37.009)",
    )
    assert outcome["accepted"] is True

    conn = sqlite3.connect(str(temp_plots_project / "data" / "project.gpkg"))
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM survey_photo WHERE survey_id = ?;", (outcome["generated_uuid"],)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_generated_uuid_is_a_valid_uuid_v4(simple_inventory_project):
    import uuid

    outcome = attempt_feature_save(
        str(simple_inventory_project),
        "inventory_observation",
        {"surveyor": "Field Researcher", "selected_scientific_name": "Test taxon"},
        geometry_wkt="POINT(127.0 37.0)",
    )
    assert outcome["accepted"]
    parsed = uuid.UUID(outcome["generated_uuid"])
    assert parsed.version == 4
