"""Korean layer display names on the generated project's real QGIS layers (Section 8.7,
DR-QPB-078, FR-QPB-130, AC-QPB-118; Decision Log D-80/D-84).

Covers:
- AC-QPB-118 (domain-layer half): Given a generated project for any survey type, when every
  domain survey-data layer's own name (as configured via `QgsMapLayer.setName()`) is inspected in
  the Layers panel, then it is a non-empty Korean-language name matching Section 8.7's
  stakeholder-confirmed mapping for that layer's underlying table — never the raw, unmodified
  GeoPackage table name (e.g. `inventory_observation`).
- AC-QPB-118 (KTSN-lookup-layer extended scope, Decision Log D-84): given a Type 1-3 project
  specifically, when the bundled KTSN accepted-name lookup layer's (DR-QPB-072) own name is
  inspected, then it likewise matches Section 8.7's confirmed "인정 국명 조회표" — not the raw
  table name `ktsn_accepted_name_lookup` — per DR-QPB-078 (revised)/FR-QPB-130 (revised)'s own
  scope extension to this one additional layer.
- Negative control (explicitly out of scope, per Section 8.7's own closing paragraph and Open
  Question O-39, narrowed but not closed by Decision Log D-84): the three root layer-tree *group*
  names (`Survey data`/`Basemap`/`Reference`, FR-QPB-055) remain completely unaffected by this
  requirement — a structurally distinct UI surface this criterion does not govern, and this
  requirement must never be implemented by touching it.

Per Decision Log D-84's own "Approval status" line, Section 8.7's two proposed Korean layer-name
tables (the domain-layer table across Types 1-4, plus the separate KTSN-lookup-layer bonus row)
are now fully stakeholder-confirmed — every row exactly as proposed, except `site`, corrected from
"사이트" to "조사지" in all three of its occurrences (Types 2/3/4) — and `test-designer`/
`implementer` work may proceed against DR-QPB-078 (revised)/FR-QPB-130 (revised)/Section 8.7/
AC-QPB-118 (revised). Like Decision Log D-77's identical treatment of FR-QPB-128/AC-QPB-111 once
Section 8.6 was confirmed (and unlike the earlier Decision Log D-56/D-57/D-58 Korean field-alias
round, whose requirement text was left textually unedited), DR-QPB-078/FR-QPB-130/AC-QPB-118's own
body text was itself updated in place by Decision Log D-84 — so no separate "why this round could
proceed despite stale wording" note is needed here.

**Current, pre-fix state confirmed by direct code reading (`qfield_builder/qgis_worker.py`'s
`_add_domain_layers()`/`_add_ktsn_lookup_layer()`):** every domain layer is constructed as
`QgsVectorLayer(uri, table_name, "ogr")`, and the KTSN lookup layer identically as
`QgsVectorLayer(uri, table_name, "ogr")` — in both cases the third constructor argument, which
QGIS uses as the layer's own initial display name (`QgsMapLayer.name()`), is passed the *raw table
name string* itself, and no code anywhere in this codebase ever calls `.setName()` on either kind
of layer afterward to override it. The two domain-layer/KTSN-lookup-layer tests below are
therefore expected to **fail** once `inspect_layer_names` (a brand-new harness function this round
introduces — see below) is implemented against the current, not-yet-fixed source, or, until then,
to **skip cleanly** (the correct, expected pre-implementation state for a not-yet-built harness
function, mirroring this suite's own established `_require_harness_function` convention) — never
to silently pass. The negative-control group-name test is different: it requires no new harness
function and is expected to **pass already**, today, against the current, unmodified codebase —
see that test's own module comment below for why.

**Scope: exactly the eight domain table names Section 8.7 lists, plus the one KTSN-lookup-layer
bonus row — nothing else.** No test in this file asserts anything about the online/offline
basemap layer's own name, or about the three root layer-tree *group* names' own English text
changing — both are explicitly out of Section 8.7/DR-QPB-078/FR-QPB-130/AC-QPB-118's own governed
scope (Open Question O-39, narrowed but not closed, by Decision Log D-84). The group-name
negative-control test below exists precisely to guard against a future implementer accidentally
conflating "a layer's own name" with "a layer-tree group's own name" and touching the wrong API —
not to claim this round decides anything about group names, which remain undecided.

See `HARNESS_CONTRACT.md`'s new "Decision Log D-80/D-84" section, function 19
(`inspect_layer_names`), for the full rationale behind: (a) using a dedicated, real-PyQGIS-backed
harness function here rather than a raw `.qgs` XML regex on a `<layername>` element — this
project's hard QGIS-isolation rule bars the test-designer from constructing a `QgsApplication` to
independently confirm that exact XML shape, mirroring the established `inspect_field_aliases`/
`inspect_relations` precedent; and (b) why that same function identifies each layer by its
underlying GeoPackage table name (parsed from the layer's own OGR data source), never by the
layer's own current `.name()` — which is exactly the property this requirement changes, and is
therefore unusable as a stable lookup key once this fix lands.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from .conftest import (
    ALL_SURVEY_TYPES,
    KOREAN_LAYER_DISPLAY_NAMES,
    KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME,
)

pytestmark = pytest.mark.qgis


def _layer_name_cases():
    cases = []
    ids = []
    for table_name, info in KOREAN_LAYER_DISPLAY_NAMES.items():
        for survey_type in info["survey_types"]:
            cases.append((survey_type, table_name, info["display_name"]))
            ids.append(f"{survey_type}-{table_name}")
    return cases, ids


_LAYER_CASES, _LAYER_IDS = _layer_name_cases()

# DR-QPB-072's own explicit Type 4 exclusion: the KTSN accepted-name lookup layer only ever exists
# for Types 1-3 (`simple_inventory`/`temporary_plots`/`permanent_plots`), never for
# `vegetation_mapping`.
_KTSN_LOOKUP_SURVEY_TYPES = tuple(t for t in ALL_SURVEY_TYPES if t != "vegetation_mapping")


# --- AC-QPB-118 (domain-layer half) ------------------------------------------------------------

@pytest.mark.parametrize(
    "survey_type,table_name,expected_display_name", _LAYER_CASES, ids=_LAYER_IDS
)
def test_ac118_domain_layer_name_is_the_confirmed_korean_display_name(
    inspect_layer_names, built_project_by_type, survey_type, table_name, expected_display_name
):
    """DR-QPB-078/FR-QPB-130: every domain survey-data layer's own name (`QgsMapLayer.name()`)
    must be the Section 8.7-confirmed Korean text for its underlying table — never the raw,
    unmodified GeoPackage table name this codebase currently uses as the layer's name today
    (`_add_domain_layers()`, `qfield_builder/qgis_worker.py`)."""
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    info = inspect_layer_names(result["project_dir"])

    assert table_name in info["table_names"], (
        f"AC-QPB-118: expected the generated {survey_type} project to have a domain layer loaded "
        f"for table {table_name!r} — got table_names={sorted(info['table_names'])!r}"
    )
    assert table_name in info["names"], (
        f"AC-QPB-118: expected a configured name() to be reported for table {table_name!r} on "
        f"the generated {survey_type} project — got names={info['names']!r}"
    )

    actual_display_name = info["names"][table_name]
    assert actual_display_name == expected_display_name, (
        f"AC-QPB-118/FR-QPB-130: {survey_type}.{table_name}'s own configured layer name "
        f"(QgsMapLayer.name()) must be the Section 8.7-confirmed Korean text "
        f"{expected_display_name!r} (Decision Log D-80/D-84) — got {actual_display_name!r}"
    )
    assert actual_display_name != table_name, (
        f"AC-QPB-118/FR-QPB-130: {survey_type}.{table_name}'s own configured layer name must "
        f"never be the raw, unmodified GeoPackage table name itself — got "
        f"{actual_display_name!r}, exactly the pre-fix state this requirement closes "
        f'(`QgsVectorLayer(uri, table_name, "ogr")` with no subsequent `.setName()` call, '
        f"`qfield_builder/qgis_worker.py`'s `_add_domain_layers()`)"
    )


# --- AC-QPB-118 (KTSN-lookup-layer extended scope, Decision Log D-84) --------------------------

@pytest.mark.parametrize("survey_type", _KTSN_LOOKUP_SURVEY_TYPES)
def test_ac118_ktsn_lookup_layer_name_is_the_confirmed_korean_display_name(
    inspect_layer_names, built_project_by_type, survey_type
):
    """Decision Log D-84's scope extension of DR-QPB-078/FR-QPB-130/AC-QPB-118 to the bundled
    KTSN accepted-name lookup layer (DR-QPB-072), for every Types 1-3 generated project (Type 4
    has no such layer at all, per DR-QPB-072's own pre-existing exclusion)."""
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    table_name = result.get("ktsn_lookup_table_name")
    assert table_name, (
        f"expected build_project() to report a non-empty ktsn_lookup_table_name for the "
        f"Types 1-3 {survey_type} project (FR-QPB-127/Decision Log D-68's unconditional "
        f"bundling, already confirmed and in scope independently of this round) — got "
        f"{table_name!r}"
    )

    info = inspect_layer_names(result["project_dir"])

    assert table_name in info["table_names"], (
        f"AC-QPB-118 (Decision Log D-84 scope extension): expected the generated {survey_type} "
        f"project to have the KTSN accepted-name lookup layer loaded for table {table_name!r} — "
        f"got table_names={sorted(info['table_names'])!r}"
    )

    actual_display_name = info["names"].get(table_name)
    assert actual_display_name == KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME, (
        f"AC-QPB-118/DR-QPB-078 (revised)/FR-QPB-130 (revised) (Decision Log D-84): the KTSN "
        f"accepted-name lookup layer's own configured name (QgsMapLayer.name()) must be the "
        f"Section 8.7-confirmed {KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME!r} — got "
        f"{actual_display_name!r}"
    )
    assert actual_display_name != table_name, (
        f"AC-QPB-118: the KTSN accepted-name lookup layer's own configured name must never be "
        f"the raw table name itself — got {actual_display_name!r}"
    )


# --- Negative control: root layer-tree GROUP names are a distinct, unaffected UI surface --------
#
# Explicitly out of scope for DR-QPB-078/FR-QPB-130/AC-QPB-118 (Section 8.7's own closing
# paragraph; Open Question O-39, narrowed but not closed by Decision Log D-84): the three
# English-named root layer-tree groups (`Survey data`/`Basemap`/`Reference`, FR-QPB-055) are a
# structurally different QGIS concept (`QgsLayerTreeGroup`'s own `name`/the group's own `name`
# attribute in `.qgs` XML) from an individual layer's own name (`QgsMapLayer.setName()`,
# AC-QPB-118). This test is a regression guard confirming this requirement's own implementation
# does not (accidentally or otherwise) touch group names at all — it is expected to **PASS already,
# today**, against the current, unmodified codebase (unlike the two tests above, which are expected
# to fail/skip until this round's own fix lands), since the pre-existing group-name behavior it
# checks is already correct and is simply required to remain untouched by this round.
#
# Read directly from the generated `.qgs` XML rather than via a new PyQGIS-backed harness
# function, mirroring `test_qgis_project_config.py::test_ac110_basemap_group_is_last_of_the_
# three_required_root_groups_by_children_index`'s own identical, already real-QGIS-confirmed
# convention for this exact XML shape: a real QGIS 3.44.12 project's `<qgis>` root element has
# exactly one direct-child `<layer-tree-group>` element (the layer tree's own root group), whose
# own direct children include one `<layer-tree-group name="...">` element per top-level group.

def _root_group_names(qgs_path: str) -> list[str | None]:
    """The root layer tree's own direct-child group names — see the module comment above for why
    this is read directly from the `.qgs` XML rather than via a new harness function."""
    tree = ET.parse(qgs_path)
    qgis_root = tree.getroot()
    root_layer_tree_group = qgis_root.find("layer-tree-group")
    assert root_layer_tree_group is not None, (
        f"expected a root <layer-tree-group> element directly under <qgis> in {qgs_path}"
    )
    return [child.get("name") for child in root_layer_tree_group.findall("layer-tree-group")]


@pytest.mark.parametrize("survey_type", ALL_SURVEY_TYPES)
def test_ac118_negative_control_root_layer_tree_group_names_are_unaffected(
    built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    group_names = _root_group_names(result["qgs_path"])
    assert set(group_names) == {"Survey data", "Basemap", "Reference"}, (
        f"Negative control (Section 8.7's own out-of-scope carve-out; Open Question O-39, "
        f"narrowed but not closed by Decision Log D-84): expected the root layer tree's three "
        f"required groups to remain present, in English, completely unaffected by "
        f"DR-QPB-078/FR-QPB-130/AC-QPB-118 — got root group children {group_names!r}"
    )
