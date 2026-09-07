"""Real, PyQGIS-backed regression test for the Korean field-alias mechanism
(DR-QPB-071/FR-QPB-119/Section 8.5/AC-QPB-098; Decision Log D-56/D-57/D-58).

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.qgis_worker.build_qgis_project`) and reads the aliases back via
`qfield_builder.field_alias_inspect.inspect_field_aliases`, mirroring the existing convention in
`test_qgis_worker_drag_and_drop_form.py` (skipped when no real, bridgeable QGIS/PyQGIS runtime is
available on this machine). The acceptance suite's `test_korean_field_aliases.py` is the
authoritative, exhaustive (103-case) coverage of this same behavior; this file is a smaller,
implementation-level regression check colocated with this codebase's other `qgis_worker` unit
tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qfield_builder import (
    field_alias_inspect,
    gpkg,
    korean_field_aliases,
    naming,
    qgis_worker,
    schemas,
)
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)


def _build_project(tmp_path: Path, survey_type: str) -> str:
    gpkg_path = tmp_path / f"{survey_type}.gpkg"
    qgs_path = tmp_path / f"{survey_type}.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        survey_type,
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=survey_type,
        project_crs="EPSG:4326",
        basemap_config=None,
    )
    return str(tmp_path)


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_every_in_scope_column_gets_its_confirmed_korean_alias(tmp_path: Path, survey_type: str):
    project_dir = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)

    for table_name, table_def in schema.items():
        info = field_alias_inspect.inspect_field_aliases(project_dir, table_name)
        for col in table_def.columns:
            if col.is_uuid_pk:
                continue
            expected_alias = korean_field_aliases.alias_for(table_name, col.name)
            assert expected_alias, f"no expected alias configured for {table_name}.{col.name}"
            actual_alias = info["aliases"].get(col.name)
            assert actual_alias == expected_alias, (
                f"{survey_type}.{table_name}.{col.name}: expected alias {expected_alias!r}, "
                f"got {actual_alias!r}"
            )


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_uuid_primary_key_field_has_no_alias(tmp_path: Path, survey_type: str):
    project_dir = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)

    for table_name, table_def in schema.items():
        info = field_alias_inspect.inspect_field_aliases(project_dir, table_name)
        pk_alias = info["aliases"].get(table_def.uuid_pk)
        assert not pk_alias, (
            f"{survey_type}.{table_name}.{table_def.uuid_pk} (UUID primary key) must have no "
            f"alias set (DR-QPB-071), got {pk_alias!r}"
        )


@pytest.mark.parametrize(
    "survey_type", [t for t in schemas.SURVEY_TYPES if t != "simple_inventory"]
)
def test_uuid_foreign_key_field_is_in_scope_and_gets_an_alias(tmp_path: Path, survey_type: str):
    """DR-QPB-071: unlike the primary-key case, a UUID field in its foreign-key role must still
    get a Korean alias (it remains a visible RelationReference picker widget).

    `simple_inventory` (Type 1) is deliberately excluded from this parametrization: its single
    table, `inventory_observation`, has no foreign key at all (it is not a related child table of
    anything) -- see `qfield_builder.schemas._build_simple_inventory`.
    """
    project_dir = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)

    found_a_foreign_key = False
    for table_name, table_def in schema.items():
        if table_def.foreign_key is None:
            continue
        found_a_foreign_key = True
        info = field_alias_inspect.inspect_field_aliases(project_dir, table_name)
        fk_alias = info["aliases"].get(table_def.foreign_key.column)
        assert fk_alias, (
            f"{survey_type}.{table_name}.{table_def.foreign_key.column} is a UUID foreign key "
            f"and must have a non-empty alias, got {fk_alias!r}"
        )
    assert found_a_foreign_key, f"{survey_type}: expected at least one table with a foreign key"
