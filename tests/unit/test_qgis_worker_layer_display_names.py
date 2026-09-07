"""Real, PyQGIS-backed regression test for the Korean layer-display-name mechanism
(DR-QPB-078/FR-QPB-130/Section 8.7/AC-QPB-118; Decision Log D-80/D-84).

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.qgis_worker.build_qgis_project`) and reads the layer names back via
`qfield_builder.layer_names_inspect.inspect_layer_names`, mirroring the existing convention in
`test_qgis_worker_relations.py` (skipped when no real, bridgeable QGIS/PyQGIS runtime is available
on this machine). The acceptance suite's `test_korean_layer_display_names.py` is the authoritative,
exhaustive coverage of this same behavior; this file is a smaller, implementation-level regression
check colocated with this codebase's other `qgis_worker` unit tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qfield_builder import (
    gpkg,
    korean_layer_display_names,
    layer_names_inspect,
    naming,
    qgis_worker,
    reference_bundle,
    schemas,
)
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

_LOOKUP_ROWS = [
    {"ktsn": "120000000001", "taxon_kor_nm": "테스트종", "taxon_full_nm": "Testus demo"},
]


def _build_project(
    tmp_path: Path, survey_type: str, with_ktsn_lookup_table: bool = False
) -> tuple[str, str | None]:
    """Returns (project_dir, ktsn_lookup_table_name_or_none)."""
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

    table_name = None
    if with_ktsn_lookup_table:
        table_name = reference_bundle.KTSN_LOOKUP_TABLE_NAME
        gpkg.add_ktsn_lookup_table(str(gpkg_path), table_name, _LOOKUP_ROWS)

    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=survey_type,
        project_crs="EPSG:4326",
        basemap_config=None,
        ktsn_lookup_table_name=table_name,
    )
    return str(tmp_path), table_name


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_every_domain_layer_name_is_the_confirmed_korean_display_name(
    tmp_path: Path, survey_type: str
):
    """DR-QPB-078/FR-QPB-130: every domain survey-data layer's own name (`QgsMapLayer.name()`)
    must be the Section 8.7-confirmed Korean text for its underlying table -- never the raw,
    unmodified GeoPackage table name."""
    project_dir, _ = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)

    info = layer_names_inspect.inspect_layer_names(project_dir)
    for table_name in schema:
        assert table_name in info["table_names"], (
            f"{survey_type}: expected a layer loaded for table {table_name!r}, got "
            f"table_names={sorted(info['table_names'])!r}"
        )
        expected_name = korean_layer_display_names.display_name_for(table_name)
        actual_name = info["names"].get(table_name)
        assert actual_name == expected_name, (
            f"{survey_type}.{table_name}: expected name() {expected_name!r}, got {actual_name!r}"
        )
        assert actual_name != table_name, (
            f"{survey_type}.{table_name}: name() must never be the raw table name itself"
        )


@pytest.mark.parametrize(
    "survey_type", [t for t in schemas.SURVEY_TYPES if t != "vegetation_mapping"]
)
def test_ktsn_lookup_layer_name_is_the_confirmed_korean_display_name(
    tmp_path: Path, survey_type: str
):
    """Decision Log D-84's scope extension of DR-QPB-078/FR-QPB-130 to the bundled KTSN
    accepted-name lookup layer (DR-QPB-072), for every Types 1-3 generated project."""
    project_dir, table_name = _build_project(tmp_path, survey_type, with_ktsn_lookup_table=True)

    info = layer_names_inspect.inspect_layer_names(project_dir)
    assert table_name in info["table_names"], (
        f"{survey_type}: expected the KTSN lookup layer loaded for table {table_name!r}, got "
        f"table_names={sorted(info['table_names'])!r}"
    )
    actual_name = info["names"].get(table_name)
    assert actual_name == korean_layer_display_names.KTSN_LOOKUP_LAYER_DISPLAY_NAME
    assert actual_name != table_name
