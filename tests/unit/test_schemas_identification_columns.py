"""Unit tests for DR-QPB-052/053/054 (Decision Log D-38): the two new nullable, reserved
`identification_timestamp`/`identification_model_version` columns added to Types 1-3, and
deliberately excluded from Type 4 `community`.
"""
from __future__ import annotations

import pytest

from qfield_builder import schemas

_NEW_COLUMN_NAMES = ("identification_timestamp", "identification_model_version")


@pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)
def test_identification_timestamp_and_model_version_columns_present(survey_type, layer_name):
    schema = schemas.get_schema(survey_type)
    columns_by_name = {c.name: c for c in schema[layer_name].columns}
    for name in _NEW_COLUMN_NAMES:
        assert name in columns_by_name, f"{survey_type}/{layer_name}: missing column {name!r}"


def test_identification_timestamp_column_is_nullable_datetime():
    schema = schemas.get_schema("simple_inventory")
    col = {c.name: c for c in schema["inventory_observation"].columns}["identification_timestamp"]
    assert col.not_null is False
    assert col.sql_type == "DATETIME"


def test_identification_model_version_column_is_nullable_text():
    schema = schemas.get_schema("simple_inventory")
    col = {c.name: c for c in schema["inventory_observation"].columns}[
        "identification_model_version"
    ]
    assert col.not_null is False
    assert col.sql_type == "TEXT"


def test_vegetation_mapping_community_does_not_receive_the_new_columns():
    """DR-QPB-054: a non-destructive extension of DR-QPB-050's existing Type 4 exclusion."""
    schema = schemas.get_schema("vegetation_mapping")
    columns_by_name = {c.name for c in schema["community"].columns}
    for name in _NEW_COLUMN_NAMES:
        assert name not in columns_by_name


def test_no_other_vegetation_mapping_table_receives_the_new_columns():
    schema = schemas.get_schema("vegetation_mapping")
    for table_name, table_def in schema.items():
        columns_by_name = {c.name for c in table_def.columns}
        for name in _NEW_COLUMN_NAMES:
            assert name not in columns_by_name, f"{table_name} unexpectedly has {name!r}"


def test_gpkg_creates_the_new_columns_and_they_default_to_null(tmp_path):
    from qfield_builder import gpkg, naming

    gpkg_path = tmp_path / "test.gpkg"
    gpkg.build_geopackage(
        str(gpkg_path),
        "simple_inventory",
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    import sqlite3

    conn = sqlite3.connect(str(gpkg_path))
    try:
        cols = [row[1] for row in conn.execute('PRAGMA table_info("inventory_observation");')]
        for name in _NEW_COLUMN_NAMES:
            assert name in cols
    finally:
        conn.close()
