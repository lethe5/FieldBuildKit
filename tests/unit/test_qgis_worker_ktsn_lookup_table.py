"""Real, PyQGIS-backed regression test for the bundled accepted-name lookup widget.

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.gpkg.add_ktsn_lookup_table` + `qfield_builder.qgis_worker.build_qgis_project`) and
reads the configured widgets back via
`qfield_builder.editor_widget_inspect.inspect_editor_widget`, mirroring the existing convention in
`test_qgis_worker_identification_status_widget.py`/`test_qgis_worker_symbol_styling.py` (skipped
when no real, bridgeable QGIS/PyQGIS runtime is available on this machine). The acceptance suite's
`test_ktsn_lookup_table.py` (AC-QPB-105-109) is the authoritative, exhaustive coverage of this same
behavior; this file is a smaller, implementation-level regression check colocated with this
codebase's other `qgis_worker` unit tests.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from qfield_builder import editor_widget_inspect, gpkg, naming, qgis_worker, reference_bundle
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

_NAME_FIELD_LAYER_BY_TYPE = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}

_LOOKUP_ROWS = [
    {"ktsn": "120000000001", "taxon_kor_nm": "테스트종", "taxon_full_nm": "Testus demo"},
]


def _build_project(tmp_path: Path, survey_type: str, with_lookup_table: bool) -> tuple[str, str]:
    """Returns (project_dir, ktsn_lookup_table_name_or_empty)."""
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
    if with_lookup_table:
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


@pytest.mark.parametrize("survey_type", list(_NAME_FIELD_LAYER_BY_TYPE))
def test_selected_korean_name_gets_a_value_relation_widget_referencing_the_lookup_table(
    tmp_path: Path, survey_type: str
):
    project_dir, table_name = _build_project(tmp_path, survey_type, with_lookup_table=True)
    layer = _NAME_FIELD_LAYER_BY_TYPE[survey_type]

    info = editor_widget_inspect.inspect_editor_widget(project_dir, layer, "selected_korean_name")
    assert info["widget_type"] == "ValueRelation"
    assert info["referenced_layer_name"] == table_name
    assert info["has_filter_or_completer_config"] is True


@pytest.mark.parametrize("survey_type", list(_NAME_FIELD_LAYER_BY_TYPE))
def test_value_relation_key_column_is_the_korean_name_column_not_the_ktsn_column(
    tmp_path: Path, survey_type: str
):
    """Regression test for the Key/Value swap defect (reviewer Blocking Finding 1).

    QGIS's `ValueRelation` widget writes the **"Key"** column's value into the edited field on
    selection; **"Value"** only drives the dropdown/completer's display label
    (`QgsValueRelationFieldFormatter`'s documented semantics; QGIS issue #30194). FR-QPB-124
    requires the plain Korean-name text to be written into `selected_korean_name`, so "Key" must
    point at the lookup table's Korean-name column (`taxon_kor_nm`), not its KTSN column
    (`ktsn`). A test that only checks `widget_type == "ValueRelation"` or that both "Key" and
    "Value" config entries merely exist would NOT catch a Key/Value swap -- this test checks the
    actual column each one is assigned to.
    """
    project_dir, _table_name = _build_project(tmp_path, survey_type, with_lookup_table=True)
    layer = _NAME_FIELD_LAYER_BY_TYPE[survey_type]
    ktsn_col, kor_col, _sci_col = reference_bundle.ACCEPTED_NAME_LOOKUP_TABLE_COLUMNS

    info = editor_widget_inspect.inspect_editor_widget(project_dir, layer, "selected_korean_name")
    assert info["value_relation_key_column"] == kor_col, (
        f"FR-QPB-124: the ValueRelation widget's 'Key' column (what actually gets WRITTEN into "
        f"selected_korean_name on selection) must be the lookup table's Korean-name column "
        f"({kor_col!r}) -- got {info['value_relation_key_column']!r}. If this is {ktsn_col!r}, "
        f"a real selection would silently write the KTSN code instead of the Korean-name text."
    )
    assert info["value_relation_key_column"] != ktsn_col


def test_a_real_value_relation_selection_writes_the_korean_name_and_derived_fields_resolve(
    tmp_path: Path,
):
    """Empirical, behavioral regression test for the Key/Value swap defect.

    Rather than asserting the "correct" column name directly, this test reads the widget's own
    currently configured "Key" column *dynamically* and uses it to determine which value a real
    `ValueRelation` selection would actually write into `selected_korean_name` for a known
    lookup-table row -- exactly mirroring what a real QGIS/QField form selection does. It then
    genuinely *evaluates* `selected_scientific_name`/`selected_ktsn`'s configured `QgsDefaultValue`
    expression against a synthetic feature carrying that simulated write (via
    `editor_widget_inspect.evaluate_default_values_after_setting_attribute`, which exercises real
    PyQGIS `QgsVectorLayer.defaultValue()` evaluation, not merely the expression's static text),
    confirming both fields resolve to the lookup table's own correct, non-NULL accepted values.

    Because this test derives the "written" value from the widget's own live config rather than a
    hardcoded assumption, it genuinely fails if `_configure_value_relation_widget` ever regresses
    to writing `Key=ktsn` again (this round's exact defect): the simulated write would then be the
    raw KTSN code, `_derived_ktsn_field_expression`'s lookup (which always matches against the
    lookup table's Korean-name column) would find no matching row, and
    `selected_scientific_name`/`selected_ktsn` would resolve to NULL instead of the expected
    values below -- reproducing, not merely re-describing, the reported production bug (confirmed
    empirically this round via `scripts/qgis_isolated_probe.py`: a simulated write of the raw KTSN
    code resolves both derived fields to `NULL`, exactly as the reviewer's finding described).
    """
    survey_type = "simple_inventory"
    layer = _NAME_FIELD_LAYER_BY_TYPE[survey_type]
    lookup_row = _LOOKUP_ROWS[0]

    project_dir, _table_name = _build_project(tmp_path, survey_type, with_lookup_table=True)

    widget_info = editor_widget_inspect.inspect_editor_widget(
        project_dir, layer, "selected_korean_name"
    )
    key_column = widget_info["value_relation_key_column"]
    assert key_column in lookup_row, (
        f"expected the ValueRelation widget's Key column ({key_column!r}) to be one of the "
        f"bundled lookup table's own columns {list(lookup_row)!r}"
    )
    simulated_written_value = lookup_row[key_column]

    evaluation = editor_widget_inspect.evaluate_default_values_after_setting_attribute(
        project_dir,
        layer,
        "selected_korean_name",
        simulated_written_value,
        ["selected_scientific_name", "selected_ktsn"],
    )
    assert evaluation["found"], evaluation

    resolved_scientific_name = evaluation["values"]["selected_scientific_name"]
    resolved_ktsn = evaluation["values"]["selected_ktsn"]
    assert resolved_scientific_name == lookup_row["taxon_full_nm"], (
        f"FR-QPB-125: selected_scientific_name must derive to the lookup table's own accepted "
        f"scientific name ({lookup_row['taxon_full_nm']!r}), not NULL -- got "
        f"{resolved_scientific_name!r} (widget Key column was {key_column!r}, simulated written "
        f"selected_korean_name value was {simulated_written_value!r})"
    )
    assert resolved_ktsn == lookup_row["ktsn"], (
        f"FR-QPB-125: selected_ktsn must derive to the lookup table's own accepted KTSN "
        f"identifier ({lookup_row['ktsn']!r}), not NULL -- got {resolved_ktsn!r} (widget Key "
        f"column was {key_column!r}, simulated written selected_korean_name value was "
        f"{simulated_written_value!r})"
    )


@pytest.mark.parametrize("survey_type", list(_NAME_FIELD_LAYER_BY_TYPE))
@pytest.mark.parametrize("field_name", ["selected_scientific_name", "selected_ktsn"])
def test_derived_field_is_read_only_with_apply_on_update_default_value(
    tmp_path: Path, survey_type: str, field_name: str
):
    project_dir, _table_name = _build_project(tmp_path, survey_type, with_lookup_table=True)
    layer = _NAME_FIELD_LAYER_BY_TYPE[survey_type]

    info = editor_widget_inspect.inspect_editor_widget(project_dir, layer, field_name)
    assert info["default_value_expression"]
    assert "selected_korean_name" in info["default_value_expression"]
    assert info["apply_on_update"] is True
    assert info["is_read_only"] is True


@pytest.mark.parametrize("field_name", ("dominant_species", "subdominant_species"))
def test_type4_community_species_fields_use_the_accepted_name_lookup_table(
    tmp_path: Path, field_name: str
):
    """Type 4 stores Korean dominant/subdominant names from the accepted-name picker."""
    project_dir, table_name = _build_project(
        tmp_path, "vegetation_mapping", with_lookup_table=True
    )
    assert table_name

    info = editor_widget_inspect.inspect_editor_widget(project_dir, "community", field_name)
    assert info["widget_type"] == "ValueRelation"
    assert info["referenced_layer_name"] == table_name
    assert info["has_filter_or_completer_config"] is True


def test_type4_community_name_defaults_from_dominant_and_subdominant_species(tmp_path: Path):
    project_dir, _table_name = _build_project(
        tmp_path, "vegetation_mapping", with_lookup_table=True
    )

    info = editor_widget_inspect.inspect_editor_widget(project_dir, "community", "community_name")
    assert info["default_value_expression"] == (
        "CASE "
        "WHEN coalesce(trim(\"dominant_species\"), '') = '' THEN NULL "
        "WHEN coalesce(trim(\"subdominant_species\"), '') = '' THEN \"dominant_species\" "
        "ELSE \"dominant_species\" || '-' || \"subdominant_species\" END"
    )
    assert info["apply_on_update"] is True
    assert info["is_read_only"] is False


def test_ktsn_lookup_layer_populates_the_reference_group(tmp_path: Path):
    """DR-QPB-072: the lookup table must be loaded as the first (and only) layer of the
    pre-existing, previously-always-empty "Reference" layer-tree group (FR-QPB-055). Checked via
    a plain text search of the generated `.qgs` XML -- mirroring
    `test_qgis_project_config.py`'s own existing `RelationReference` regex-based check -- rather
    than constructing a second `QgsApplication`/PyQGIS session for this one structural fact."""
    project_dir, table_name = _build_project(tmp_path, "simple_inventory", with_lookup_table=True)
    qgs_text = Path(project_dir, "simple_inventory.qgs").read_text(
        encoding="utf-8", errors="replace"
    )

    match = re.search(
        r'<layer-tree-group[^>]*name="Reference"[^>]*>(.*?)</layer-tree-group>',
        qgs_text,
        re.DOTALL,
    )
    assert match is not None, "expected a 'Reference' layer-tree group in the generated .qgs"
    assert table_name in match.group(1), (
        f"expected the bundled lookup table layer ({table_name!r}) inside the 'Reference' group"
    )
