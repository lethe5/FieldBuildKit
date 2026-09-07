# Traceability Matrix — QField Project Builder, Basemap Group Stacking Order (Decision Log D-71)

> Specification: `specs/qfield-project-builder.md`, `FR-QPB-055` (revised; Decision Log D-71,
> Section 19), `AC-QPB-110` (Section 18.2).
>
> This round adds acceptance-test coverage for a single, newly approved requirement:
> `FR-QPB-055` (revised) requires that, within the root layer tree's own root
> `QgsLayerTreeGroup.children()` list, `"Basemap"`'s own child index be greater than both
> `"Survey data"`'s and `"Reference"`'s own child index — i.e. `"Basemap"` must be the last
> (highest-index) of the three required root groups, so it renders beneath (behind) both other
> groups rather than on top of them. New `AC-QPB-110` (Section 18.2) makes this independently
> testable against a generated project's `.qgs` file.
>
> Root-cause context (given by the task, independently confirmed against the current, uncommitted
> source during this round's own test design — see "Confirmed current (buggy) behavior" below):
> `qfield_builder/qgis_worker.py`'s `_add_reference_and_basemap_groups(project)` calls
> `root.addGroup("Basemap")` then `root.addGroup("Reference")`, both **before**
> `_add_domain_layers()` (called immediately after, in `_build_qgis_project_pyqgis`) adds
> `"Survey data"`. Because `QgsLayerTreeGroup.addGroup()` appends to the end of the parent's
> existing children, `"Basemap"` ends up as the very **first** (index 0) group — the opposite of
> what `FR-QPB-055` (revised)/`AC-QPB-110` now require. This has not been fixed yet; the new test
> is expected to fail (red) against the current source and is expected to pass once a future
> `implementer` round reorders group creation.
>
> Tests: `tests/acceptance/qfield_project_builder/test_qgis_project_config.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (test-designer round, 2026-08-27): root layer-tree group stacking order (Decision Log D-71,
> AC-QPB-110)" section — no new `acceptance_api` function; reads the generated `.qgs` XML directly
> via `xml.etree.ElementTree`, mirroring the existing `test_post_mvp_plantnet_key_embedding.py`
> `_read_project_variables()` convention for a documented, confirmed `.qgs`-format fact.

## What this round covers

A single criterion, `AC-QPB-110`, tested once per survey type (all four: `simple_inventory`,
`temporary_plots`, `permanent_plots`, `vegetation_mapping`) via
`test_ac110_basemap_group_is_last_of_the_three_required_root_groups_by_children_index`, mirroring
this suite's own existing convention (used throughout `test_qgis_project_config.py`, e.g.
`test_ac010_ac014_...`, `test_ac103_...`) of parametrizing structural `.qgs`-configuration checks
across every survey type via `SURVEY_TYPE_SCHEMAS`, since `FR-QPB-055`'s three-group requirement
applies identically regardless of survey type.

The test asserts, in one pass:

1. All three required root groups (`Survey data`, `Basemap`, `Reference`) are actually present as
   direct children of the root layer tree (a precondition `AC-QPB-110`'s own "given...the root
   layer tree's group children are inspected" clause presupposes, and a genuine regression this
   test would also catch if a future change silently dropped a group).
2. Among those three groups' own relative order (ignoring any other root-level content — see
   "Design choices" below), `"Basemap"`'s own index is strictly greater than both `"Survey data"`'s
   and `"Reference"`'s index.

No assertion is made about the relative order of `"Survey data"` and `"Reference"` themselves,
exactly matching `AC-QPB-110`'s own explicit "does not assert...any particular relative order
between Survey data and Reference" clause.

## Confirmed current (buggy) behavior, verified directly against a real generated project

This round built a real `simple_inventory` project via `build_project()` (through the isolated
QGIS bridge already used by this suite's own fixtures/`conftest.py` — never by constructing a
`QgsApplication` directly) and inspected the raw `.qgs` XML output to confirm both (a) the exact
serialization shape the new test relies on, and (b) that the bug described by the task is real,
today, in the current source:

```xml
<layer-tree-group>
  <customproperties><Option/></customproperties>
  <layer-tree-group checked="Qt::Checked" groupLayer="" expanded="1" name="Basemap">
    <customproperties><Option/></customproperties>
  </layer-tree-group>
  <layer-tree-group checked="Qt::Checked" groupLayer="" expanded="1" name="Reference">
    ...
  </layer-tree-group>
  <layer-tree-group checked="Qt::Checked" groupLayer="" expanded="1" name="Survey data">
    ...
  </layer-tree-group>
  <custom-order enabled="0">...</custom-order>
</layer-tree-group>
```

Root group children order today: `["Basemap", "Reference", "Survey data"]` — `"Basemap"`'s index
(0) is the *smallest* of the three, not the largest, so the new test fails (red) against the
current source, exactly as expected.

## Design choices this round made, and why

- **No new `acceptance_api`/PyQGIS-backed harness function.** The `.qgs` container format's own
  `<layer-tree-group>`/`<layer-tree-layer>` nested-XML shape, and the fact that document order
  mirrors the real `QgsLayerTreeGroup.children()` index order, is a documented, confirmed fact
  about the file format itself (confirmed by this round's own direct inspection above), not an
  invented application behavior — matching this suite's own established preference (see
  `HARNESS_CONTRACT.md`'s top-of-document rationale, and the existing
  `test_qgs_and_gpkg_paths_are_relative_to_each_other`/`_read_project_variables()` precedents) for
  reading a generated artifact's own inspectable standard format directly rather than inventing a
  new inspection API for every new structural fact.
- **Scoped `findall("layer-tree-group")` to the root group element only, not `.//layer-tree-group`.**
  A layer loaded inside a group (e.g. the KTSN accepted-name lookup layer inside `"Reference"`,
  DR-QPB-072) is itself wrapped in nested `<layer-tree-layer>`/possible-nested-`<layer-tree-group>`
  elements that are descendants of that group's own element, not direct children of the *root*
  `<layer-tree-group>`. Using an unscoped, recursive `.//layer-tree-group` search would risk
  matching a nested group (none exist today, but nothing in `FR-QPB-055` forbids one appearing
  inside `"Reference"`/`"Survey data"` in the future) and silently corrupting the "three top-level
  groups" comparison. Scoping to direct children of the confirmed root group element avoids this.
- **The test tolerates other, non-required root-level content (there is none observed today, but
  the assertion does not assume there never will be) by filtering to only the three named,
  required groups before comparing indices**, rather than asserting the root group has *exactly*
  three children in a fixed order. This is deliberately narrower than the observed reality (which,
  as shown above, currently has exactly the three required groups and nothing else at the root)
  — `FR-QPB-055`/`AC-QPB-110` state nothing about forbidding additional root-level groups, so the
  test does not invent that constraint.
- **Reused the existing `built_project_by_type` session-scoped fixture**, matching every other
  structural `.qgs`-configuration test already in `test_qgis_project_config.py` (`AC-QPB-010`
  through `AC-QPB-103`), rather than introducing a new build helper for this one criterion.

## Traceability table

| AC ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-110 | `"Basemap"` is the last (highest-index) of the three required root layer-tree groups (`Survey data`, `Basemap`, `Reference`), for every survey type | `test_qgis_project_config.py::test_ac110_basemap_group_is_last_of_the_three_required_root_groups_by_children_index` (parametrized over `simple_inventory`, `temporary_plots`, `permanent_plots`, `vegetation_mapping`) | auto (`qgis`-marked; skipped when no real, working QGIS/PyQGIS runtime is available on the machine running the suite) |

## Ambiguities / gaps found

None found in `FR-QPB-055` (revised)/`AC-QPB-110`'s own text. Decision Log D-71 is explicit and
precise about what "last" means (children-index order, stated deliberately to avoid the three
different readings — "last added," "last in the visual list," "bottom of the rendering stack" —
the criterion's own text calls out), and explicit that no relative order between `"Survey data"`
and `"Reference"` is asserted. Both halves are directly, unambiguously testable as written; no
invented behavior was needed.
