"""Regression test for the "관련 기록" tab order (stakeholder bug report:
"생성된 레이어에 related records를 Details 뒤에 위치해야 함.
Details를 먼저 입력하고 daughter 레이어를
추가하는 방식으로 작업하기 때문임" -- "관련 기록" must be positioned after "상세 정보", because
the workflow is "fill in Details first, then add daughter/child records").

Confirmed root cause: `qfield_builder.qgis_worker._build_drag_and_drop_form` added the "Related
records" container (`related_container`) to `invisible_root` *inside* the `if child_relations:`
block, which ran *before* `invisible_root.addChildElement(root)` (the "상세 정보" container) at the
end of the function -- so "관련 기록" ended up as the first top-level tab and "상세 정보" as
the second. The fix reorders these two `addChildElement` calls so "상세 정보" is always added first.

This exercises the real PyQGIS-calling pipeline end-to-end (mirroring
`test_qgis_worker_drag_and_drop_form.py`'s own convention) and inspects the actual generated `.qgs`
XML's `<attributeEditorForm>` top-level child order for a layer that genuinely has both containers
(the "temporary_plots" survey type's "site" layer, which has its own Details columns *and* is
referenced by "survey" via a foreign key, giving it a non-empty "관련 기록" tab) --
confirming `QgsAttributeEditorContainer`'s own `TabLayout` tab order really is determined by
`addChildElement` call order, which a fake/mocked `pyqgis` dict cannot verify. Skipped when no
real, bridgeable QGIS/PyQGIS runtime is available, matching that same file's convention.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from qfield_builder import gpkg, layer_lookup, naming, qgis_worker
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

_SURVEY_TYPE = "temporary_plots"
_LAYER_WITH_BOTH_TABS = "site"  # has its own Details columns, and is referenced by "survey".


def _build_and_parse_qgs(tmp_path: Path) -> ET.Element:
    gpkg_path = tmp_path / f"{_SURVEY_TYPE}.gpkg"
    qgs_path = tmp_path / f"{_SURVEY_TYPE}.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        _SURVEY_TYPE,
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=_SURVEY_TYPE,
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


def _attribute_editor_form_for_layer(root: ET.Element, table_name: str) -> ET.Element:
    """Locates `<maplayer>` by its own underlying GeoPackage *table* name (parsed from
    `<datasource>`), not by `<layername>` -- DR-QPB-078/FR-QPB-130 (Decision Log D-80/D-84) sets a
    domain layer's own `<layername>` to a Korean display name, distinct from its table name."""
    for maplayer in root.iter("maplayer"):
        datasource_el = maplayer.find("datasource")
        source_text = datasource_el.text if datasource_el is not None else None
        if layer_lookup.table_name_from_layer(_SourceOnly(source_text)) == table_name:
            form = maplayer.find(".//attributeEditorForm")
            assert form is not None, f"{table_name}: missing <attributeEditorForm> element"
            return form
    raise AssertionError(f"expected a maplayer for table {table_name!r} in the .qgs XML")


def _top_level_container_names(form: ET.Element) -> list[str]:
    return [
        el.get("name")
        for el in form
        if el.tag == "attributeEditorContainer" and el.get("name") in ("상세 정보", "관련 기록")
    ]


def test_site_layer_has_both_details_and_related_records_containers(tmp_path: Path):
    """Sanity precondition: confirm the "site" layer in "temporary_plots" genuinely has both
    top-level containers -- otherwise the ordering assertion below would be vacuous."""
    root = _build_and_parse_qgs(tmp_path)
    form = _attribute_editor_form_for_layer(root, _LAYER_WITH_BOTH_TABS)
    names = _top_level_container_names(form)
    assert set(names) == {"상세 정보", "관련 기록"}, (
        f"expected both '상세 정보' and '관련 기록' top-level containers; found: {names}"
    )


def test_details_tab_appears_before_related_records_tab(tmp_path: Path):
    """The actual regression assertion: "상세 정보" must be the first top-level tab, "Related
    records" the second -- matching the stakeholder's required "fill Details in first, then add
    daughter records" workflow."""
    root = _build_and_parse_qgs(tmp_path)
    form = _attribute_editor_form_for_layer(root, _LAYER_WITH_BOTH_TABS)
    names = _top_level_container_names(form)
    assert names == ["상세 정보", "관련 기록"], (
        f"expected '상세 정보' before '관련 기록'; actual top-level tab order: {names}"
    )


def test_details_and_related_records_keep_the_normal_entry_workflow(tmp_path: Path):
    """Every schema field remains in Details while Related records stays second."""
    from qfield_builder import schemas

    root = _build_and_parse_qgs(tmp_path)
    form = _attribute_editor_form_for_layer(root, _LAYER_WITH_BOTH_TABS)

    details_el = next(
        el for el in form if el.tag == "attributeEditorContainer" and el.get("name") == "상세 정보"
    )
    related_el = next(
        el
        for el in form
        if el.tag == "attributeEditorContainer" and el.get("name") == "관련 기록"
    )

    table_def = schemas.get_schema(_SURVEY_TYPE)[_LAYER_WITH_BOTH_TABS]
    expected_column_names = {col.name for col in table_def.columns} - {table_def.uuid_pk}
    details_field_names = {el.get("name") for el in details_el.iter("attributeEditorField")}
    assert expected_column_names <= details_field_names

    assert related_el.find(".//attributeEditorRelation") is not None


def test_directly_drawn_site_remains_a_checked_project_layer_after_reordering(tmp_path: Path):
    """Reordering must not unregister a directly drawn `site` layer (regression)."""
    gpkg_path = tmp_path / "drawn-site.gpkg"
    qgs_path = tmp_path / "drawn-site.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        _SURVEY_TYPE,
        naming.new_project_id(),
        seed_sites=[
            {
                "site_name": "직접 그린 사이트",
                "geom_wkt": (
                    "MULTIPOLYGON(((127.10 37.50, 127.11 37.50, "
                    "127.11 37.51, 127.10 37.50)))"
                ),
            }
        ],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=_SURVEY_TYPE,
        project_crs="EPSG:5186",
        basemap_config=None,
    )

    root = ET.parse(str(qgs_path)).getroot()
    matches = [
        node
        for node in root.iter("layer-tree-layer")
        if "|layername=site" in (node.get("source") or "")
    ]
    assert len(matches) == 1
    assert matches[0].get("checked") == "Qt::Checked"
    assert any(
        "|layername=site" in (node.findtext("datasource") or "")
        for node in root.iter("maplayer")
    )
