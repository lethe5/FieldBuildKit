"""Regression test for the Decision Log D-80/D-84 layer-lookup fix in
`qfield_builder.field_alias_inspect.inspect_field_aliases`,
`qfield_builder.editor_widget_inspect.inspect_editor_widget`,
`qfield_builder.layer_renderer_inspect.inspect_layer_renderer` (traceability file
`tests/acceptance/qfield_project_builder_korean_layer_display_names.traceability.md`'s "Flagged
interaction with this suite's own pre-existing name-based layer lookups" section;
`qfield_builder.layer_lookup`), and two more functions with the identical pre-existing defect --
`qfield_builder.feature_save.attempt_feature_save` and `qfield_builder.identification_inspect.
inspect_identification_widget` -- discovered as genuine, reproducing regressions (not merely a
theoretical risk) by this same round's own mandatory full-acceptance-suite verification pass, and
fixed via the identical `qfield_builder.layer_lookup.find_layer_by_table_name` mechanism.

**What this proves, and why it is the single most important regression this task must prevent.**
Before DR-QPB-078/FR-QPB-130 (Section 8.7) shipped, a domain layer's own `QgsMapLayer.name()` and
its underlying GeoPackage table name were always the identical string, so it would be easy for a
regression test to pass merely by coincidence -- e.g. if it only ever exercised the functions
above against a layer whose `.name()` happens to already be its Section 8.7-confirmed Korean text,
that would not distinguish "the lookup mechanism now genuinely matches by table name" from "the
lookup mechanism still matches by `.name()`, and this test's Korean name and table name both
happen to resolve correctly by luck of what production code currently sets." This test closes that
gap directly: it renames every domain layer in a freshly generated project's own `.qgs` XML to an
arbitrary string that is deliberately **not** any table name, **not** any Section 8.7 Korean
display name, and **not** related to either -- then confirms every function above still correctly
locates the target layer and returns correct, non-empty results when called with the raw table
name, exactly as every existing caller across this suite already does.

The rename is performed by directly editing the generated `.qgs` XML (both places a layer's own
name is stored in a real, generated `.qgs` file -- confirmed by direct inspection, this round, of
an actual generated project: the `<maplayer><layername>` element, and the `<layer-tree-layer
name="...">` attribute), deliberately bypassing PyQGIS and this codebase's own Korean-naming code
entirely -- this test's own manipulation must not depend on, or be constrained by, the very
production code path (`qfield_builder.korean_layer_display_names`/`_add_domain_layers`) whose
*separate* concern (a layer's own name) this test needs to vary independently of the table-name
lookup mechanism under test.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from qfield_builder import (
    editor_widget_inspect,
    feature_save,
    field_alias_inspect,
    gpkg,
    identification_inspect,
    layer_lookup,
    layer_renderer_inspect,
    naming,
    qgis_worker,
    schemas,
)
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

# Deliberately not a table name, not a Section 8.7 Korean display name, and not related to either.
_ARBITRARY_NAME = "Completely Unrelated Display Name 12345"


def _build_project(tmp_path: Path, survey_type: str) -> tuple[str, Path]:
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
    return str(tmp_path), qgs_path


class _SourceOnly:
    """Minimal stand-in for a `QgsMapLayer`, exposing only `.source()` -- just enough for
    `qfield_builder.layer_lookup.table_name_from_layer` to parse the table name out of a raw
    `<datasource>`/`source=` string read from `.qgs` XML, without needing a real PyQGIS object."""

    def __init__(self, source_text: str | None):
        self._source_text = source_text or ""

    def source(self) -> str:
        return self._source_text


def _rename_every_domain_layer_to_an_arbitrary_name(qgs_path: Path) -> None:
    """Rewrites every domain layer's own stored name (in both places a real `.qgs` file stores it)
    to `_ARBITRARY_NAME`, regardless of its underlying table name -- see this module's own
    docstring for why this must not depend on `qfield_builder.korean_layer_display_names`/PyQGIS.
    """
    tree = ET.parse(qgs_path)
    root = tree.getroot()

    for maplayer in root.iter("maplayer"):
        datasource_el = maplayer.find("datasource")
        table_name = layer_lookup.table_name_from_layer(
            _SourceOnly(datasource_el.text if datasource_el is not None else None)
        )
        if table_name is None:
            continue  # Not a GeoPackage-table-backed layer (e.g. a basemap layer) -- skip.
        layername_el = maplayer.find("layername")
        if layername_el is not None:
            layername_el.text = _ARBITRARY_NAME

    for layer_tree_layer in root.iter("layer-tree-layer"):
        table_name = layer_lookup.table_name_from_layer(
            _SourceOnly(layer_tree_layer.get("source"))
        )
        if table_name is None:
            continue
        layer_tree_layer.set("name", _ARBITRARY_NAME)

    tree.write(qgs_path, encoding="UTF-8", xml_declaration=True)


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_inspect_field_aliases_locates_layer_by_table_name_after_arbitrary_rename(
    tmp_path: Path, survey_type: str
):
    project_dir, qgs_path = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)
    _rename_every_domain_layer_to_an_arbitrary_name(qgs_path)

    for table_name, table_def in schema.items():
        info = field_alias_inspect.inspect_field_aliases(project_dir, table_name)
        expected_field_names = {col.name for col in table_def.columns}
        assert expected_field_names <= set(info["field_names"]), (
            f"{survey_type}.{table_name}: expected inspect_field_aliases to still locate this "
            f"layer by its raw table name after its .name() was changed to {_ARBITRARY_NAME!r} "
            f"-- got field_names={info['field_names']!r}"
        )


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_inspect_editor_widget_locates_layer_by_table_name_after_arbitrary_rename(
    tmp_path: Path, survey_type: str
):
    project_dir, qgs_path = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)
    _rename_every_domain_layer_to_an_arbitrary_name(qgs_path)

    found_a_foreign_key = False
    for table_name, table_def in schema.items():
        if table_def.foreign_key is None:
            continue
        found_a_foreign_key = True
        fk = table_def.foreign_key
        info = editor_widget_inspect.inspect_editor_widget(project_dir, table_name, fk.column)
        assert info["widget_type"] == "RelationReference", (
            f"{survey_type}.{table_name}.{fk.column}: expected inspect_editor_widget to still "
            f"locate this layer by its raw table name after its .name() was changed to "
            f"{_ARBITRARY_NAME!r} -- got {info}"
        )
        # The *referenced* layer was also renamed to the same arbitrary name; confirming this
        # still resolves to the referenced layer's own table name (not the arbitrary display
        # name, and not None) additionally regression-tests the `_referenced_layer_name_for_
        # relation_reference` fix (Decision Log D-80/D-84), not merely the target-layer lookup.
        assert info["referenced_layer_name"] == fk.ref_table, (
            f"{survey_type}.{table_name}.{fk.column}: expected referenced_layer_name "
            f"{fk.ref_table!r}, got {info['referenced_layer_name']!r}"
        )

    assert found_a_foreign_key or survey_type == "simple_inventory", (
        f"{survey_type}: expected at least one table with a foreign key (simple_inventory is the "
        f"sole exception, per its own schema)"
    )


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_inspect_layer_renderer_locates_layer_by_table_name_after_arbitrary_rename(
    tmp_path: Path, survey_type: str
):
    project_dir, qgs_path = _build_project(tmp_path, survey_type)
    schema = schemas.get_schema(survey_type)
    _rename_every_domain_layer_to_an_arbitrary_name(qgs_path)

    found_a_spatial_table = False
    for table_name, table_def in schema.items():
        if table_def.geometry is None:
            continue
        found_a_spatial_table = True
        info = layer_renderer_inspect.inspect_layer_renderer(project_dir, table_name)
        assert info["renderer_class"], (
            f"{survey_type}.{table_name}: expected inspect_layer_renderer to still locate this "
            f"layer by its raw table name after its .name() was changed to {_ARBITRARY_NAME!r} "
            f"-- got {info}"
        )

    assert found_a_spatial_table, f"{survey_type}: expected at least one spatial (geometry) table"


def _root_table_and_valid_attrs(survey_type: str) -> tuple[str, dict, str]:
    """Returns (table_name, attributes, geometry_wkt) for a valid, self-contained (no
    foreign-key-dependency) record on `survey_type`'s own root table -- `inventory_observation`
    for `simple_inventory`, `site` for every other survey type."""
    if survey_type == "simple_inventory":
        return "inventory_observation", {"surveyor": "Field Researcher"}, "POINT(127.0 37.0)"
    return (
        "site",
        {"site_name": "Test Site"},
        "MULTIPOLYGON(((127.0 37.0, 127.01 37.0, 127.01 37.01, 127.0 37.01, 127.0 37.0)))",
    )


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_attempt_feature_save_locates_layer_by_table_name_after_arbitrary_rename(
    tmp_path: Path, survey_type: str
):
    """`qfield_builder.feature_save.attempt_feature_save` has the identical pre-existing
    `lyr.name() == layer_name` defect as the three functions above -- discovered as a real
    regression (not merely a theoretical one) by this same round's own mandatory
    full-acceptance-suite verification pass, since dozens of existing acceptance tests build a
    feature via this exact function using a raw table name."""
    project_dir, qgs_path = _build_project(tmp_path, survey_type)
    _rename_every_domain_layer_to_an_arbitrary_name(qgs_path)

    table_name, attrs, geometry_wkt = _root_table_and_valid_attrs(survey_type)
    outcome = feature_save.attempt_feature_save(project_dir, table_name, attrs, geometry_wkt)
    assert outcome["accepted"], (
        f"{survey_type}.{table_name}: expected attempt_feature_save to still locate this layer "
        f"by its raw table name after its .name() was changed to {_ARBITRARY_NAME!r} -- got "
        f"{outcome}"
    )
    assert outcome["rejected_reason"] != f"Unknown layer: {table_name!r}"


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots"])
def test_inspect_identification_widget_locates_layer_by_table_name_after_arbitrary_rename(
    tmp_path: Path, survey_type: str
):
    """`qfield_builder.identification_inspect.inspect_identification_widget` has the identical
    pre-existing `lyr.name() == layer_name` defect as the three functions above -- discovered as a
    real regression (not merely a theoretical one) by this same round's own mandatory
    full-acceptance-suite verification pass."""
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
        identification_enabled=True,
    )
    _rename_every_domain_layer_to_an_arbitrary_name(qgs_path)

    target_table = {
        "simple_inventory": "inventory_observation",
        "temporary_plots": "observation",
        "permanent_plots": "observation",
    }[survey_type]

    info = identification_inspect.inspect_identification_widget(str(tmp_path), target_table)
    assert info["qml_widget_field_found"] is True, (
        f"{survey_type}.{target_table}: expected inspect_identification_widget to still locate "
        f"this layer by its raw table name after its .name() was changed to "
        f"{_ARBITRARY_NAME!r} -- got {info}"
    )
