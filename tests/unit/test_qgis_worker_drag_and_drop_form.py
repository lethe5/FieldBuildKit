"""Regression test for `qfield_builder.qgis_worker._build_drag_and_drop_form` (FR-QPB-057).

Verified defect: `QgsEditFormConfig.invisibleRootContainer()` is pre-populated by QGIS itself,
before `_build_drag_and_drop_form` ever runs, with a flat, ungrouped `QgsAttributeEditorField` for
*every* field on the layer (including the physical `fid` primary key). Building the intentionally
organized "Details"/"Related records" containers as *additional* children of that same root --
without clearing its pre-existing default children first -- left every intentionally organized
field appearing twice in the generated `.qgs` attribute-editor-form tree, and left `fid` present as
a plain, ungrouped, fully visible field, in direct violation of FR-QPB-057's "hide `fid`... from
normal entry" clause.

This exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.
build_geopackage` + `qfield_builder.qgis_worker.build_qgis_project`) and inspects the actual
generated `.qgs` XML, since the defect is specifically about what real PyQGIS/`QgsEditFormConfig`
objects do (a fake/mocked `pyqgis` dict, as used by
`test_qgis_worker_online_basemap.py`, cannot reproduce QGIS's own default-content behavior for
`invisibleRootContainer()`). Skipped when no real, bridgeable QGIS/PyQGIS runtime is available on
this machine, matching the existing convention in `tests/unit/test_worker_process.py`.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from qfield_builder import gpkg, layer_lookup, naming, qgis_worker, schemas
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)


def _build_and_parse_qgs(tmp_path: Path, survey_type: str) -> ET.Element:
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
    return ET.parse(str(qgs_path)).getroot()


class _SourceOnly:
    """Minimal stand-in exposing only `.source()`, just enough for
    `qfield_builder.layer_lookup.table_name_from_layer` to parse a table name out of a raw
    `<datasource>` string read from `.qgs` XML."""

    def __init__(self, source_text: str | None):
        self._source_text = source_text or ""

    def source(self) -> str:
        return self._source_text


def _attribute_editor_forms_by_layer(root: ET.Element) -> dict[str, ET.Element | None]:
    """Keyed by each layer's own underlying GeoPackage *table* name (parsed from `<datasource>`),
    not by `<layername>` -- DR-QPB-078/FR-QPB-130 (Decision Log D-80/D-84) sets a domain layer's
    own `<layername>` to a Korean display name, distinct from its table name, and this dict's keys
    are used elsewhere in this file to look layers up in `qfield_builder.schemas.get_schema()`,
    which is keyed by table name."""
    forms: dict[str, ET.Element | None] = {}
    for maplayer in root.iter("maplayer"):
        datasource_el = maplayer.find("datasource")
        source_text = datasource_el.text if datasource_el is not None else None
        table_name = layer_lookup.table_name_from_layer(_SourceOnly(source_text))
        assert table_name, "every maplayer in a generated .qgs must have a resolvable table name"
        forms[table_name] = maplayer.find(".//attributeEditorForm")
    return forms


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots"])
def test_no_field_appears_more_than_once_in_the_attribute_editor_form_tree(
    tmp_path: Path, survey_type: str
):
    root = _build_and_parse_qgs(tmp_path, survey_type)
    forms = _attribute_editor_forms_by_layer(root)
    assert forms, "expected at least one layer with an attributeEditorForm element"

    for layer_name, form in forms.items():
        assert form is not None, f"{layer_name}: missing <attributeEditorForm> element entirely"
        field_names = [el.get("name") for el in form.iter("attributeEditorField")]
        counts = Counter(field_names)
        duplicates = {name: count for name, count in counts.items() if count > 1}
        assert not duplicates, (
            f"{layer_name}: field(s) appear more than once in the attribute editor form tree: "
            f"{duplicates}"
        )


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots"])
def test_fid_never_appears_anywhere_in_the_attribute_editor_form_tree(
    tmp_path: Path, survey_type: str
):
    root = _build_and_parse_qgs(tmp_path, survey_type)
    forms = _attribute_editor_forms_by_layer(root)

    for layer_name, form in forms.items():
        assert form is not None, f"{layer_name}: missing <attributeEditorForm> element entirely"
        field_names = [el.get("name") for el in form.iter("attributeEditorField")]
        assert "fid" not in field_names, (
            f"{layer_name}: 'fid' must not appear anywhere (top-level or nested) in the "
            f"attribute editor form tree (FR-QPB-057: hide `fid`... from normal entry); found "
            f"field names: {field_names}"
        )
        # There must also be no bare top-level (root-container-level) fields left over from
        # QGIS's own pre-populated default content -- every field must live inside one of the
        # intentionally organized containers ("Details"/"Related records"), never flat at the
        # form root.
        top_level_field_names = [el.get("name") for el in form if el.tag == "attributeEditorField"]
        assert top_level_field_names == [], (
            f"{layer_name}: expected no flat/ungrouped fields directly under the form root "
            f"(all fields must be organized inside a container); found: {top_level_field_names}"
        )


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots"])
def test_details_container_still_contains_every_intended_field(
    tmp_path: Path, survey_type: str
):
    root = _build_and_parse_qgs(tmp_path, survey_type)
    forms = _attribute_editor_forms_by_layer(root)
    schema = schemas.get_schema(survey_type)

    for layer_name, form in forms.items():
        table_def = schema[layer_name]
        assert form is not None, f"{layer_name}: missing <attributeEditorForm> element entirely"
        field_names_in_form = {el.get("name") for el in form.iter("attributeEditorField")}
        expected_column_names = {col.name for col in table_def.columns}
        assert expected_column_names <= field_names_in_form, (
            f"{layer_name}: expected every schema column to still appear in the organized form "
            f"tree; missing: {expected_column_names - field_names_in_form}"
        )


def test_generalizes_across_all_survey_types(tmp_path: Path):
    """Confirms the fix is not specific to `simple_inventory` -- exercised here across every
    declared MVP survey type (`qfield_builder.schemas.SURVEY_TYPES`), each of which shares the
    same `_build_drag_and_drop_form` function for every one of its layers."""
    for survey_type in schemas.SURVEY_TYPES:
        root = _build_and_parse_qgs(tmp_path / survey_type, survey_type)
        forms = _attribute_editor_forms_by_layer(root)
        assert forms
        for layer_name, form in forms.items():
            assert form is not None, f"{survey_type}/{layer_name}: missing attributeEditorForm"
            field_names = [el.get("name") for el in form.iter("attributeEditorField")]
            assert "fid" not in field_names, f"{survey_type}/{layer_name}: 'fid' present"
            counts = Counter(field_names)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            assert not duplicates, f"{survey_type}/{layer_name}: duplicates {duplicates}"
