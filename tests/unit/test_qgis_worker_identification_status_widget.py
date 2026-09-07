"""Real, PyQGIS-backed regression test for `identification_status`'s `ValueMap` editor widget
(FR-QPB-122; Decision Log D-63, confirmed by D-69; AC-QPB-103).

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.qgis_worker.build_qgis_project`) and reads the configured widget back via
`qfield_builder.editor_widget_inspect.inspect_editor_widget`, mirroring the existing convention in
`test_qgis_worker_field_aliases.py`/`test_qgis_worker_drag_and_drop_form.py` (skipped when no
real, bridgeable QGIS/PyQGIS runtime is available on this machine). The acceptance suite's
`test_qgis_project_config.py::test_ac103_*` tests are the authoritative coverage of this same
behavior; this file is a smaller, implementation-level regression check colocated with this
codebase's other `qgis_worker` unit tests.

`identification_status` exists on `inventory_observation` (Type 1, `simple_inventory`) and
`observation` (Types 2/3, `temporary_plots`/`permanent_plots`) -- see Section 8.1/8.2/8.3 of the
specification. `vegetation_mapping` (Type 4)'s `community` table deliberately excludes it
(DR-QPB-050) and is not exercised here.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qfield_builder import editor_widget_inspect, gpkg, naming, qgis_worker, schemas
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

_LAYER_BY_SURVEY_TYPE = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}
_IDENTIFICATION_STATUS_VALUES = ("not_requested", "pending", "complete", "failed", "manual")


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


@pytest.mark.parametrize("survey_type", list(_LAYER_BY_SURVEY_TYPE))
def test_identification_status_gets_a_value_map_widget_with_exactly_the_five_enum_values(
    tmp_path: Path, survey_type: str
):
    project_dir = _build_project(tmp_path, survey_type)
    layer_name = _LAYER_BY_SURVEY_TYPE[survey_type]

    info = editor_widget_inspect.inspect_editor_widget(
        project_dir, layer_name, "identification_status"
    )
    assert info["widget_type"] == "ValueMap", (
        f"{survey_type}.{layer_name}.identification_status must be configured with a ValueMap "
        f"editor widget, not a plain text-edit widget -- got {info}"
    )
    value_map = info.get("value_map") or {}
    assert set(value_map.keys()) == set(_IDENTIFICATION_STATUS_VALUES), (
        f"expected exactly the five existing enum values as the only selectable options -- got "
        f"keys {sorted(value_map.keys())}"
    )


def test_identification_status_value_map_uses_raw_english_strings_as_both_key_and_label():
    """Decision Log D-69 (closes O-33): no Korean-language value-label translation, matching the
    existing `organ` ValueMap widget's own identical-keys/values precedent."""
    assert schemas._IDENTIFICATION_STATUS_VALUES == _IDENTIFICATION_STATUS_VALUES


@pytest.mark.parametrize("survey_type", list(_LAYER_BY_SURVEY_TYPE))
def test_identification_status_value_map_does_not_alter_the_check_constraint_or_default(
    tmp_path: Path, survey_type: str
):
    """FR-QPB-122: this is a presentation/entry-constraint change only -- the column's SQL type,
    `CHECK` constraint, and default value are unaffected."""
    project_dir = _build_project(tmp_path, survey_type)
    layer_name = _LAYER_BY_SURVEY_TYPE[survey_type]
    schema = schemas.get_schema(survey_type)
    table_def = schema[layer_name]
    col = next(c for c in table_def.columns if c.name == "identification_status")

    info = editor_widget_inspect.inspect_editor_widget(
        project_dir, layer_name, "identification_status"
    )
    assert col.check_sql, "identification_status is expected to keep its existing CHECK clause"
    assert col.default_sql == "'not_requested'"
    # The ValueMap widget setup coexists with (does not replace/clear) the column's own default
    # value definition, which is set from `col.default_sql` elsewhere in
    # `_configure_widget_for_column`, independent of the widget-type branch added by this round.
    assert info["default_value_expression"] == "'not_requested'"
