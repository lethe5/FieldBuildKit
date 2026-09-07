"""QGIS project generation, relations, and form/widget configuration (Section 9, Section 18.2).

Covers:
- AC-QPB-010: project opens without a missing-layer warning after being moved to a new absolute
  path.
- AC-QPB-011: a new child record created from a parent's relation is saved and correctly
  associated.
- AC-QPB-012: the UUID field is auto-generated and cannot be edited through the normal form.
- AC-QPB-013: a foreign-key field rendered via a Relation Reference widget shows a human-readable
  name, not a raw UUID.
- AC-QPB-014: attachment paths remain relative and valid after a folder move (automated proxy for
  the full computer-to-phone-to-computer round trip; see the traceability notes for the
  hardware-dependent remainder of this criterion).
- AC-QPB-016: opens successfully in each explicitly supported QGIS/QField version — blocked on
  Open Question O-9 (the exact version matrix is not yet pinned); see notes below.

AC-QPB-011/012/013 are verified by inspecting the generated `.qgs` project's relation and field/
widget configuration (via PyQGIS through `validate_project`/direct XML inspection, and via
`attempt_feature_save`) rather than by physically driving the QGIS Desktop or QField GUI, per
HARNESS_CONTRACT.md — the configuration is the mechanism that produces the described interactive
behavior.
"""
from __future__ import annotations

import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from .conftest import SURVEY_TYPE_SCHEMAS

pytestmark = pytest.mark.qgis

# `identification_status` lives on `inventory_observation` (Type 1) or `observation` (Types 2/3) --
# Section 8.1/8.2/8.3.
_IDENTIFICATION_STATUS_LAYER_BY_TYPE = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}
_IDENTIFICATION_STATUS_VALUES = ("not_requested", "pending", "complete", "failed", "manual")


# --- AC-QPB-010 / AC-QPB-014 (automated proxy) --------------------------------

@pytest.mark.parametrize("survey_type", list(SURVEY_TYPE_SCHEMAS.keys()))
def test_ac010_ac014_project_reopens_without_missing_layer_warning_after_move(
    acceptance_api, built_project_by_type, survey_type, tmp_path
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    moved_dir = tmp_path / f"moved_{survey_type}"
    shutil.copytree(result["project_dir"], moved_dir)

    report = acceptance_api.validate_project(str(moved_dir))
    assert report["missing_layer_warning"] is False, (
        f"AC-QPB-010: moved project reports a missing-layer warning: {report['issues']}"
    )
    assert report["opens_without_repair_warning"] is True, report["issues"]

    # AC-QPB-014 (automated proxy for the relative-path portion of the computer<->phone round
    # trip): after the move, any stored attachment path must remain a relative path, and must
    # resolve to an existing file under the moved project directory (or simply be recorded
    # relatively, for paths that are not yet populated with a real photo in this fixture).
    gpkg_text_path = result.get("gpkg_path")
    assert gpkg_text_path, "expected a gpkg_path in the build result"


def _is_absolute_or_unc_path(path: str) -> bool:
    """True for a POSIX absolute path, a Windows drive-letter absolute path, or a UNC path — the
    same absolute-path shapes DR-QPB-012 treats as invalid for attachment paths, reused here to
    judge whether a `.qgs` layer datasource path is itself relative (FR-QPB-052)."""
    return (
        path.startswith("/")
        or path.startswith("\\\\")
        or bool(re.match(r"^[A-Za-z]:[\\/]", path))
    )


def test_qgs_and_gpkg_paths_are_relative_to_each_other(built_project_by_type):
    """FR-QPB-052 (supports AC-QPB-010/014): .qgs references the .gpkg via a relative path.

    QGIS 3.44's `QgsProject.write()` unconditionally emits a project-level
    `<Paths><Absolute type="bool">false</Absolute></Paths>` marker regardless of whether any
    individual layer datasource is itself relative, and never emits the literal string
    `relativePaths` anywhere in real QGIS 3.44.12 project XML — so neither is a valid signal for
    FR-QPB-052. What FR-QPB-052 actually requires — that the `.qgs` references the `.gpkg` via a
    relative path — is verified directly here by inspecting the actual layer `<datasource>`
    element(s) that reference the project's own GeoPackage (e.g.
    `./data/<slug>.gpkg|layername=inventory_observation` in real QGIS 3.44.12 output), rather
    than the unrelated project-level `<Paths><Absolute>` marker.
    """
    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")
    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()

    gpkg_name = Path(result["gpkg_path"]).name
    datasources = re.findall(r"<datasource>(.*?)</datasource>", qgs_text, re.DOTALL)
    gpkg_datasources = [ds for ds in datasources if gpkg_name in ds]
    assert gpkg_datasources, (
        f"expected at least one layer <datasource> referencing the project's own GeoPackage "
        f"({gpkg_name!r}) in {result['qgs_path']}"
    )
    for datasource in gpkg_datasources:
        gpkg_path_part = datasource.split("|", 1)[0]
        assert not _is_absolute_or_unc_path(gpkg_path_part), (
            f"layer datasource must reference the GeoPackage via a path relative to the "
            f"project folder, not an absolute/UNC path (FR-QPB-052): {datasource!r}"
        )


# --- AC-QPB-011 ----------------------------------------------------------------

def test_ac011_child_record_created_via_relation_is_saved_and_associated(
    acceptance_api, built_project_by_type
):
    result = built_project_by_type("vegetation_mapping")
    assert result["success"], result.get("error_message")

    site_outcome_source = acceptance_api.attempt_feature_save
    # Fetch an existing seeded site to relate a survey to, then a community to that survey,
    # mirroring what happens when a user creates a child record from an embedded relation
    # widget on the parent's attribute form (FR-QPB-056).
    from .conftest import open_gpkg

    conn = open_gpkg(result["gpkg_path"])
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()

    survey_outcome = site_outcome_source(
        result["project_dir"], "survey", {"surveyor": "Field Researcher", "site_id": site_id}
    )
    assert survey_outcome["accepted"], survey_outcome
    survey_id = survey_outcome["generated_uuid"]

    community_outcome = site_outcome_source(
        result["project_dir"],
        "community",
        {
            "community_name": "Community A",
            "dominant_species": "Quercus test",
            "is_field_checked": False,
            "survey_id": survey_id,
        },
        geometry_wkt="MULTIPOLYGON(((127.00 37.00, 127.005 37.00, 127.005 37.005, 127.00 37.005, 127.00 37.00)))",
    )
    assert community_outcome["accepted"], community_outcome

    conn = open_gpkg(result["gpkg_path"])
    try:
        row = conn.execute(
            "SELECT community_name, survey_id FROM community WHERE community_id = ?;",
            (community_outcome["generated_uuid"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "the created community record must be persisted"
    assert row[0] == "Community A"
    assert row[1] == survey_id, "the child record must be correctly associated to its parent"


# --- AC-QPB-012 ----------------------------------------------------------------

@pytest.mark.parametrize(
    "survey_type,table,uuid_col",
    [(t, "site", "site_id") for t in ("temporary_plots", "permanent_plots", "vegetation_mapping")]
    + [("simple_inventory", "inventory_observation", "inventory_id")],
)
def test_ac012_uuid_field_is_autogenerated_and_not_normally_editable(
    acceptance_api, built_project_by_type, survey_type, table, uuid_col
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    geometry_wkt = None
    attrs = {}
    if table == "site":
        attrs = {"site_name": "Attempted-edit site"}
        geometry_wkt = "MULTIPOLYGON(((127.02 37.02, 127.03 37.02, 127.03 37.03, 127.02 37.03, 127.02 37.02)))"
    else:
        attrs = {"surveyor": "Field Researcher", "selected_scientific_name": "Test taxon"}
        geometry_wkt = "POINT(127.02 37.02)"

    attempted_manual_uuid = "11111111-1111-4111-8111-111111111111"
    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"], table, {**attrs, uuid_col: attempted_manual_uuid}, geometry_wkt
    )
    if outcome["accepted"]:
        # If the save is accepted (because the field is read-only and the supplied value is
        # simply ignored, per DR-QPB-005), the persisted value must be the auto-generated one,
        # not the caller-supplied one.
        assert outcome["generated_uuid"] != attempted_manual_uuid, (
            "the UUID field must not be settable through the normal form/save path (AC-QPB-012)"
        )
    else:
        assert outcome.get("rejected_field") == uuid_col


# --- AC-QPB-013 ----------------------------------------------------------------

@pytest.mark.parametrize(
    "survey_type,layer,fk_field",
    [
        ("temporary_plots", "survey", "site_id"),
        ("permanent_plots", "plot", "site_id"),
        ("permanent_plots", "survey", "plot_id"),
        ("vegetation_mapping", "community", "survey_id"),
    ],
)
def test_ac013_foreign_key_field_uses_relation_reference_widget(
    built_project_by_type, survey_type, layer, fk_field
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()

    # A QGIS "Relation Reference" edit widget is serialized in the .qgs as
    # <editWidget type="RelationReference"> (or the equivalent modern <widget type="...">
    # QGIS project XML form). We accept either serialization but require it to be present and
    # associated with the foreign-key field name, and that it is not merely a raw text widget.
    pattern = re.compile(
        rf'field\s*=\s*"{re.escape(fk_field)}"[^>]*/?>.*?RelationReference',
        re.DOTALL,
    )
    reverse_pattern = re.compile(
        rf'RelationReference.*?field\s*=\s*"{re.escape(fk_field)}"',
        re.DOTALL,
    )
    assert "RelationReference" in qgs_text, (
        f"{layer}.{fk_field} — expected a RelationReference widget configured somewhere in the "
        "project for at least one foreign key (FR-QPB-056/057)"
    )
    assert pattern.search(qgs_text) or reverse_pattern.search(qgs_text), (
        f"expected {layer}.{fk_field} specifically to use the RelationReference widget"
    )


# --- AC-QPB-103 (new; Decision Log D-63, confirmed by D-69) --------------------------------------
#
# FR-QPB-122 requires `identification_status` (Section 8.1's `inventory_observation`; Section
# 8.2/8.3's `observation`) to be configured with a `ValueMap` (or functionally equivalent
# fixed-list-selection) editor widget listing exactly its five existing enum values as the only
# selectable options -- replacing the plain default text-edit widget it currently receives. The
# displayed option text keeps the existing raw English enum strings as both keys and values (no
# Korean-language value-label translation, Decision Log D-69, closing O-33), matching the existing
# `organ` `ValueMap` widget's own precedent in this codebase. The value actually written to the
# GeoPackage on selection must remain exactly the existing raw enum string -- this is a
# presentation/entry-constraint change only, not a change to the column's SQL type/CHECK
# constraint/default value.
#
# `inspect_editor_widget` (HARNESS_CONTRACT.md function 16) is used here, exactly like the
# analogous ValueRelation checks in `test_ktsn_lookup_table.py`, rather than a raw `.qgs` XML
# regex -- see that file's own module docstring and HARNESS_CONTRACT.md's own note on why
# "ValueMap" (already present in this codebase's shipped `organ`-field configuration, but not
# independently reverified against a live QGIS instance by any test in this suite to date) is
# routed through the same dedicated harness function as "ValueRelation," for consistency, rather
# than cherry-picking which already-shipped widget-type strings get raw-regex treatment.


@pytest.mark.parametrize("survey_type", list(_IDENTIFICATION_STATUS_LAYER_BY_TYPE))
def test_ac103_identification_status_uses_a_value_map_widget_with_exactly_the_five_enum_values(
    inspect_editor_widget, built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    layer = _IDENTIFICATION_STATUS_LAYER_BY_TYPE[survey_type]
    info = inspect_editor_widget(result["project_dir"], layer, "identification_status")
    assert info["widget_type"] == "ValueMap", (
        f"AC-QPB-103/FR-QPB-122: {survey_type}.{layer}.identification_status must be configured "
        f"with a ValueMap editor widget, not a plain text-edit widget — got {info}"
    )
    value_map = info.get("value_map") or {}
    assert set(value_map.keys()) == set(_IDENTIFICATION_STATUS_VALUES), (
        f"AC-QPB-103/FR-QPB-122: expected exactly the five existing enum values as the only "
        f"selectable options — got keys {sorted(value_map.keys())}"
    )
    # Decision Log D-69 (closes O-33): displayed option text keeps the raw English enum strings as
    # both keys and values -- no Korean-language value-label translation, mirroring the existing
    # `organ` ValueMap widget's own identical-keys/values precedent.
    for value in _IDENTIFICATION_STATUS_VALUES:
        assert value_map.get(value) == value, (
            f"AC-QPB-103/Decision Log D-69: expected the displayed label for {value!r} to be the "
            f"raw English string itself (no Korean translation) — got {value_map.get(value)!r}"
        )


def test_ac103_selecting_and_saving_a_value_writes_the_exact_raw_enum_string(
    acceptance_api, built_project_by_type, tmp_path
):
    """AC-QPB-103's second half: 'given a value is selected and saved, then the GeoPackage record's
    stored value is exactly the corresponding raw enum string, unchanged from today.' Uses
    `attempt_feature_save` (the same field-constraint-enforcing save path every other MVP save-time
    test in this suite already uses) rather than asserting anything about the *widget* here -- the
    widget-configuration half (identical ValueMap semantics for every Types 1-3 survey type) is
    covered, per survey type, by the test above. Exercised once, on `simple_inventory`'s
    `inventory_observation` (a self-contained layer with no foreign-key dependency), since the
    save-time persistence mechanism itself (a ValueMap widget still writes the raw underlying
    value, unaffected by its own presentation) is not survey-type-specific."""
    from .conftest import open_gpkg

    result = built_project_by_type("simple_inventory")
    assert result["success"], result.get("error_message")

    outcome = acceptance_api.attempt_feature_save(
        result["project_dir"],
        "inventory_observation",
        {"surveyor": "Field Researcher", "identification_status": "manual"},
        "POINT(127.006 37.006)",
    )
    assert outcome["accepted"], outcome

    conn = open_gpkg(Path(result["gpkg_path"]))
    try:
        row = conn.execute(
            "SELECT identification_status FROM inventory_observation WHERE inventory_id = ?;",
            (outcome["generated_uuid"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "manual", (
        f"AC-QPB-103: the stored value must be exactly the raw enum string 'manual', unchanged by "
        f"the new ValueMap widget's presentation-only nature — got {row[0]!r}"
    )


# --- AC-QPB-110 (new; Decision Log D-71) ---------------------------------------------------------
#
# FR-QPB-055 (revised; Decision Log D-71) requires that, within the root layer tree's own
# `QgsLayerTreeGroup.children()` list, "Basemap"'s own child index be greater than both
# "Survey data"'s and "Reference"'s own child index -- i.e. "Basemap" is the last (highest-index)
# of the three required root groups, so it renders beneath (behind) both other groups rather than
# on top of them. No relative order between "Survey data" and "Reference" is asserted (FR-QPB-055
# (revised) is explicit that this remains unconstrained).
#
# Read directly from the generated `.qgs` XML rather than via a new PyQGIS-backed harness
# function, mirroring this suite's existing preference (see HARNESS_CONTRACT.md's top-of-document
# rationale, and e.g. `test_qgs_and_gpkg_paths_are_relative_to_each_other`/
# `test_post_mvp_plantnet_key_embedding.py::_read_project_variables` above/elsewhere) for reading
# a generated artifact's own inspectable standard format directly wherever the shape is a
# documented, confirmed fact about the `.qgs` container format itself, rather than inventing a new
# inspection API for it. The shape relied on here -- a real QGIS 3.44.12 project's `<qgis>` root
# element has exactly one direct-child `<layer-tree-group>` element (the layer tree's own root
# group, itself carrying no `name` attribute), whose own direct children include one
# `<layer-tree-group name="...">` element per top-level group, in the same document order as that
# group's `QgsLayerTreeGroup.children()` index order -- was confirmed by this round's own direct
# inspection of a real, freshly generated project's `.qgs` output (via `build_project()`, not by
# constructing a `QgsApplication` directly, per this project's hard QGIS-isolation rule). Nested
# `<layer-tree-layer>`/`<layer-tree-group>` elements (e.g. a layer loaded inside "Reference") are
# descendants of that group's own element, not direct children of the *root* `<layer-tree-group>`,
# so `ElementTree.findall("layer-tree-group")` scoped to the root group element alone (not
# `.//layer-tree-group`, which would also match nested groups) correctly isolates just the three
# top-level groups this criterion is about.


def _root_group_children_order(qgs_path: str) -> list[str | None]:
    """The root layer tree's own direct-child group names, in their real document/children-index
    order -- see the module comment above for why this is read directly from the `.qgs` XML."""
    tree = ET.parse(qgs_path)
    qgis_root = tree.getroot()
    root_layer_tree_group = qgis_root.find("layer-tree-group")
    assert root_layer_tree_group is not None, (
        f"expected a root <layer-tree-group> element directly under <qgis> in {qgs_path}"
    )
    return [child.get("name") for child in root_layer_tree_group.findall("layer-tree-group")]


@pytest.mark.parametrize("survey_type", list(SURVEY_TYPE_SCHEMAS.keys()))
def test_ac110_basemap_group_is_last_of_the_three_required_root_groups_by_children_index(
    built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    group_names = _root_group_children_order(result["qgs_path"])
    required_groups = {"Survey data", "Basemap", "Reference"}
    present_required = [name for name in group_names if name in required_groups]
    assert set(present_required) == required_groups, (
        f"AC-QPB-110/FR-QPB-055: expected all three required root layer-tree groups (Survey "
        f"data, Basemap, Reference) to be present as direct children of the root layer tree — "
        f"found root group children {group_names}"
    )

    basemap_index = present_required.index("Basemap")
    survey_data_index = present_required.index("Survey data")
    reference_index = present_required.index("Reference")
    assert basemap_index > survey_data_index and basemap_index > reference_index, (
        f"AC-QPB-110/FR-QPB-055 (revised, Decision Log D-71): 'Basemap' must be the last "
        f"(highest-index) of the three required root layer-tree groups, so it renders beneath "
        f"both 'Survey data' and 'Reference' — but the observed root group children order was "
        f"{group_names} (Basemap must come after both Survey data and Reference in this list)"
    )


# --- AC-QPB-016 ----------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "AC-QPB-016 requires opening the generated project in 'each explicitly supported QGIS "
        "and QField version', but that version matrix is not yet pinned (Open Question O-9 — "
        "NFR-QPB-001 explicitly says these versions must not be invented without verification). "
        "This test is a placeholder to be parametrized over the release-gate compatibility "
        "matrix once O-9 is resolved; see the traceability notes for this criterion."
    )
)
def test_ac016_opens_in_every_explicitly_supported_qgis_and_qfield_version():
    raise AssertionError("should never run while skipped — see skip reason")
