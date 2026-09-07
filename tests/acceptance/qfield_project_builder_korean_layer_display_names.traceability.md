# Traceability Matrix — QField Project Builder, Korean Layer Display Names (Decision Log D-80/D-84)

> Specification: `specs/qfield-project-builder.md` — new `DR-QPB-078` (Section 7) and new
> `FR-QPB-130` (Section 9), from Decision Log **D-80** (investigated the gap and proposed Section
> 8.7's per-survey-type Korean layer-display-name table plus a separate KTSN-lookup-layer "bonus
> row," in response to the stakeholder's verbatim report **"레이어가 표시되는 이름을 한국어로
> 변경할 수 있나? 예를 들어, 테이블 이름은 inventory_observation이더라도 QField에서 표시되는
> 이름은 식물관찰 이라던지"** — "Can the displayed layer name be changed to Korean? For example,
> even if the table name is inventory_observation, the name displayed in QField could be
> 식물관찰") and **D-84** (confirmed both of Section 8.7's tables in full — every row exactly as
> proposed, except `site`, corrected from "사이트" to "조사지" in all three of its occurrences —
> and, as a directly traceable consequence of that same confirmation, extended DR-QPB-078/
> FR-QPB-130/AC-QPB-118's own governed scope to also include the bundled KTSN accepted-name lookup
> table, DR-QPB-072, closing the domain-layer-name and KTSN-lookup-layer-name portions of Open
> Question O-39). New Section 8.7 (Section 8) records the confirmed, per-layer Korean
> display-name tables this round tests against.
>
> This is a later `test-designer` round against the same overall specification as
> [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md) (the approved
> MVP baseline). It is recorded as its own file, not merged into the MVP file or into
> [`qfield_project_builder_korean_field_aliases.traceability.md`](qfield_project_builder_korean_field_aliases.traceability.md)/
> [`qfield_project_builder_korean_relation_display_names.traceability.md`](qfield_project_builder_korean_relation_display_names.traceability.md)
> (two related but textually distinct requirements — a field's own display alias, and a relation
> widget's own display name, neither of which is a *layer's* own name), so none of those
> already-approved traceability records is touched by this round's additions — see
> `tests/acceptance/README.md` for the pointer between all of this repository's traceability
> files.
>
> Tests: `tests/acceptance/qfield_project_builder/test_korean_layer_display_names.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s new
> "Decision Log D-80/D-84" section (function 19, `inspect_layer_names`).
> Shared per-layer Korean-display-name data: `KOREAN_LAYER_DISPLAY_NAMES`/
> `KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME` in `tests/acceptance/qfield_project_builder/conftest.py`
> (mirrors the existing `KOREAN_FIELD_ALIASES`/`KOREAN_RELATION_DISPLAY_NAMES`/`SURVEY_TYPE_SCHEMAS`
> convention already used by earlier rounds).

## Why this round could proceed without a blocking-ambiguity note

Mirroring Decision Log D-77's identical treatment of `FR-QPB-128`/`AC-QPB-111` once Section 8.6
was confirmed (and unlike the earlier Decision Log D-56/D-57/D-58 Korean field-alias round, whose
`DR-QPB-071`/`FR-QPB-119`/`AC-QPB-098` own inline requirement text was left textually unedited,
requiring that earlier round's traceability file to carry an explicit "why this round could
proceed at all" note): **`DR-QPB-078`, `FR-QPB-130`, and `AC-QPB-118`'s own body text was itself
directly updated in place by Decision Log D-84**, and Section 8.7's own header status note was
likewise updated in place. Each now reads, verbatim, "~~draft, not yet stakeholder-approved...~~
confirmed by Decision Log D-84 — Section 8.7's proposed layer names are now stakeholder-confirmed
(with one correction, `site` → 조사지); `test-designer`/`implementer` work may proceed against
this requirement." No separate reconciliation of stale wording is required here; the confirmation
is already live in every requirement ID's own current text.

## Traceability table

| AC ID / FR ID / DR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-118 (domain-layer half) | Given a generated project for any survey type, when every domain survey-data layer's own name (`QgsMapLayer.setName()`) is inspected, then it is a non-empty Korean-language name matching Section 8.7's confirmed mapping for that layer's underlying table — never the raw, unmodified GeoPackage table name | `test_korean_layer_display_names.py::test_ac118_domain_layer_name_is_the_confirmed_korean_display_name` (parametrized: 13 cases — every one of the eight Section 8.7 domain table names, once per survey type it actually applies to; see "Coverage detail" below) | auto |
| AC-QPB-118 (KTSN-lookup-layer extended scope, Decision Log D-84) | Given a Type 1-3 project specifically, when the bundled KTSN accepted-name lookup layer's (DR-QPB-072) own name is inspected, then it likewise matches Section 8.7's confirmed "인정 국명 조회표" — not the raw table name — per DR-QPB-078 (revised)/FR-QPB-130 (revised)'s own scope extension | `test_korean_layer_display_names.py::test_ac118_ktsn_lookup_layer_name_is_the_confirmed_korean_display_name` (parametrized: 3 cases — `simple_inventory`/`temporary_plots`/`permanent_plots`) | auto |
| AC-QPB-118 (negative control; explicitly out of scope, Section 8.7's own closing paragraph / Open Question O-39, narrowed not closed) | Given a generated project for any survey type, when the three root layer-tree *group* names are inspected, then they remain unaffected by this requirement — a structurally distinct UI surface (`QgsLayerTreeGroup` naming) this criterion does not govern | `test_korean_layer_display_names.py::test_ac118_negative_control_root_layer_tree_group_names_are_unaffected` (parametrized: 4 cases, one per survey type) | auto |
| DR-QPB-078 (revised)/FR-QPB-130 (revised) | Every generated domain survey-data layer, and (Decision Log D-84 scope extension) the bundled KTSN accepted-name lookup table for Types 1-3, must have its own display name set via `QgsMapLayer.setName()` to the Section 8.7-confirmed Korean text, replacing the raw GeoPackage table name | Same two positive tests above — both the `table_name in info["table_names"]` presence check and the `actual_display_name == expected_display_name` / `actual_display_name != table_name` assertions are asserted together, mirroring how DR-QPB-078/FR-QPB-130's own text and AC-QPB-118's own "Given/when/then" sentence bind "every domain layer gets some Korean name" and "it is *this specific* Korean name" into one criterion | auto |

## Coverage detail (per table / survey type)

Every one of the eight domain table names Section 8.7 lists is covered, once per survey type its
own schema actually declares it (confirmed directly against `qfield_builder/schemas.py`'s own
`get_schema()` output by this round — see `KOREAN_LAYER_DISPLAY_NAMES`'s own comment block in
`conftest.py`, and the "Scope confirmation against the current schema" section below):

- `inventory_observation` → **식물관찰** — Type 1 (`simple_inventory`) only: 1 case.
- `site` → **조사지** (Decision Log D-84 correction; originally proposed "사이트") — Type 2
  (`temporary_plots`), Type 3 (`permanent_plots`), Type 4 (`vegetation_mapping`): 3 cases.
- `survey` → **조사** — Type 2, Type 3, Type 4: 3 cases.
- `observation` → **식물관찰** — Type 2 (`temporary_plots`), Type 3 (`permanent_plots`): 2 cases.
- `survey_photo` → **조사 사진** — Type 2 (`temporary_plots`) only: 1 case.
- `plot` → **고정조사구** — Type 3 (`permanent_plots`) only: 1 case.
- `plot_photo` → **고정조사구 사진** — Type 3 (`permanent_plots`) only: 1 case.
- `community` → **군락** — Type 4 (`vegetation_mapping`) only: 1 case.

Total: **13** parametrized invocations of
`test_ac118_domain_layer_name_is_the_confirmed_korean_display_name`, matching Section 8.7's own
domain-layer table row count exactly (Type 1: 1 row; Type 2: 4 rows; Type 3: 5 rows; Type 4: 3
rows = 13; the two `observation_photo` "moot" rows are correctly not counted, since that table no
longer exists per Decision Log D-74), confirmed collected by an actual `pytest --collect-only` run
performed during this round (see "Verification performed by this round" below).

Plus **3** parametrized invocations of
`test_ac118_ktsn_lookup_layer_name_is_the_confirmed_korean_display_name` (Types 1-3, `→` 인정
국명 조회표), and **4** parametrized invocations of
`test_ac118_negative_control_root_layer_tree_group_names_are_unaffected` (all four survey types) —
**20** total parametrized test invocations in this file, zero non-parametrized tests.

## Scope confirmation against the current schema (task-mandated check)

Per this round's own explicit instruction to confirm scope against `qfield_builder/schemas.py`
directly rather than assume Section 8.7's own text is already current: `schemas.py` was read in
full during this round. It already reflects Decision Log D-74's `observation_photo` removal for
Type 2/3 (`_build_temporary_plots()`/`_build_permanent_plots()` each return exactly `site`,
`survey`, `observation` (or `plot`), and one photo table — `survey_photo`/`plot_photo`
respectively — with an explicit comment confirming `observation_photo`'s deliberate absence), so
Section 8.7's own domain-layer table (already written against the current, approved schema per its
own text) and `qfield_builder/schemas.py`'s actual current contents agree exactly. No test in this
round mentions `observation_photo`, positively or negatively, for the same reason the sibling
Korean-relation-display-name round's own test file does not — see that file's own "Coverage
detail"/"Notes on automation approach" precedent, mirrored here.

## Notes on automation approach

1. **Why a dedicated PyQGIS-backed harness function (`inspect_layer_names`) rather than a raw
   `.qgs` XML regex on a `<layername>` element.** QGIS project XML does have a well-known
   `<maplayer>...<layername>...</layername>...</maplayer>` shape, and asserting on it directly —
   the same way `test_ac013_foreign_key_field_uses_relation_reference_widget` already asserts on
   the unrelated `"RelationReference"` widget-type string — was considered. It was not done, for
   the same reason `inspect_field_aliases`/`inspect_relations` were not built as raw XML regexes
   either: the exact `<layername>`/`<datasource>` XML serialization shape was not independently
   confirmed against a live QGIS instance during this round, and this project's hard QGIS-isolation
   rule bars the test-designer from constructing a `QgsApplication` for any verification purpose,
   including this one. The judgment is delegated instead to a real-PyQGIS-backed harness function
   that reads `QgsMapLayer.name()` directly off the live, opened project — the exact mechanism
   AC-QPB-118's own text names ("as configured via `QgsMapLayer.setName()`") — mirroring the
   established `inspect_field_aliases`/`inspect_relations` precedent. See `HARNESS_CONTRACT.md`'s
   new "Decision Log D-80/D-84" section for the full rationale.
2. **Layers are looked up by underlying table name, never by current display name — a
   deliberate, load-bearing design choice, not an arbitrary one.** Every pre-existing
   by-`layer_name` harness function in this suite (`inspect_field_aliases`/`inspect_editor_widget`/
   `inspect_layer_renderer`) locates a layer via `lyr.name() == layer_name`, which only works
   because, today, a layer's own name and its underlying table name are identical strings. This
   round's own requirement breaks that equivalence by design (that is the entire point of
   DR-QPB-078/FR-QPB-130) — so `inspect_layer_names` cannot itself be built the same way without
   becoming untestable the moment its own target requirement is implemented. It is instead
   designed around each layer's own OGR data source (`<gpkg_path>|layername=<table_name>`), the
   same connection-string convention `qgis_worker.py`'s own `_add_domain_layers()`/
   `_add_ktsn_lookup_layer()` already, confirmedly, construct — see `HARNESS_CONTRACT.md` function
   19's own "Why table names are identified via each layer's own data source" note for the full
   rationale.
3. **A direct regression-guard assertion (`actual_display_name != table_name`) is included
   alongside the positive expected-value assertion, in both positive tests.** This directly
   encodes AC-QPB-118's own explicit "never the raw, unmodified GeoPackage table name" wording, and
   is the literal condition the current, pre-fix `_add_domain_layers()`/`_add_ktsn_lookup_layer()`
   violate today (`QgsVectorLayer(uri, table_name, "ogr")` with no subsequent `.setName()` call) —
   so this assertion is what actually fails (once `inspect_layer_names` exists), with a clear
   message naming the observed raw-table-name string.
4. **The negative-control test is not merely a placeholder — it asserts a currently-true fact and
   is expected to pass today, unlike the two positive tests.** It exists to catch a future
   implementer round accidentally renaming a layer-tree *group* while implementing this
   requirement's own layer-*name* change (an easy category confusion, since both are QGIS
   "naming" concepts), and to make explicit, in an executable form, that Section 8.7's own
   "not addressed by this proposal" carve-out for the three group names is honored. It reuses the
   already-established, already real-QGIS-confirmed `.qgs` root-`<layer-tree-group>`-children XML
   convention `test_qgis_project_config.py::test_ac110_...` already relies on, rather than
   inventing a new one.
5. **Every project used below is built via the ordinary, default `built_project_by_type`
   fixture** (this suite's existing default, `identification_enabled=False`) — this requirement
   concerns layer-naming configuration, which does not vary with the post-MVP identification-
   subsystem toggle, so no special build configuration was needed. The KTSN-lookup-layer test
   relies on `build_project()`'s own pre-existing `ktsn_lookup_table_name` return key (Decision Log
   D-66/D-67/D-68) to discover the real table name actually used, rather than hardcoding
   `"ktsn_accepted_name_lookup"` — the same discipline HARNESS_CONTRACT.md's function 17 addendum
   already established for that key.

## Flagged interaction with this suite's own pre-existing name-based layer lookups

**Not an ambiguity in DR-QPB-078/FR-QPB-130/AC-QPB-118's own text — a real, identified
implementation-risk interaction with this suite's own existing harness modules, reported
explicitly rather than silently left for a future round to discover the hard way.**

Three pre-existing, already-shipped `qfield_builder` harness modules —
`field_alias_inspect.inspect_field_aliases`, `editor_widget_inspect.inspect_editor_widget`
(and its neighboring `_evaluate_default_values_after_setting_attribute_pyqgis` test-support
helper), and `layer_renderer_inspect.inspect_layer_renderer` — each take a `layer_name: str`
parameter and locate the target layer with the identical pattern:

```python
for lyr in project.mapLayers().values():
    if lyr.name() == layer_name:
        layer = lyr
        break
```

Every existing test across this entire acceptance suite that calls one of those three functions
passes the *raw table name* as `layer_name` (e.g. `inspect_field_aliases(project_dir, "site")`,
`inspect_editor_widget(project_dir, "observation", "identification_status")`,
`inspect_layer_renderer(project_dir, "community")`) — dozens of already-approved MVP and post-MVP
tests across `test_korean_field_aliases.py`, `test_symbol_styling.py`, `test_ktsn_lookup_table.py`,
`test_qgis_project_config.py`, `test_post_mvp_identification_plugin.py`, and others.

Once a future `implementer` round implements DR-QPB-078/FR-QPB-130 (setting a domain layer's own
`.name()` to its Section 8.7-confirmed Korean text instead of the raw table name), every one of
those existing `lyr.name() == layer_name` lookups will stop matching for every affected layer —
`lyr.name()` will be, e.g., `"조사지"`, never again `"site"` — and each of those three functions'
own documented `_EMPTY_RESULT`-shaped fallback will silently be returned instead of a real
inspection result. That would make dozens of already-approved, already-passing tests either fail
outright (if they assert on non-empty content) or, worse, silently report an empty/`None` result
that a loosely written assertion might not catch at all.

This round's own new `inspect_layer_names` function is deliberately designed to be immune to this
exact problem (see "Notes on automation approach," item 2, above) — but that immunity does not
extend to the three pre-existing functions themselves, and fixing them is out of this round's own
`tests/acceptance/`-only file-scope boundary (those three modules are application source code
under `qfield_builder/`, not test files). This is reported here as an explicit, load-bearing
finding for whichever future round implements DR-QPB-078/FR-QPB-130: that implementation must
either (a) change `inspect_field_aliases`/`inspect_editor_widget`/`inspect_layer_renderer`'s own
internal layer-lookup mechanism to locate a layer by its underlying table name (mirroring this
round's own `inspect_layer_names` data-source-based approach) rather than by its current,
display-only `.name()`, or (b) update every existing caller across this suite to pass each
affected layer's *new* Korean name instead of the table name it passes today — a determination and
a scope of work this round deliberately does not make on a future round's behalf, since choosing
between (a) and (b) is an implementation decision, not a test-design one, and doing it silently
here (by rewriting those application-source modules) would exceed this round's own file-scope
mandate.

## Verification performed by this round

Per this project's hard QGIS-isolation rule, the test-designer cannot construct a `QgsApplication`
or invoke a QGIS binary directly for any diagnostic purpose — but running the acceptance suite
itself through its own existing, isolated `qfield_builder.qgis_bridge`-backed harness (exactly what
every other round of this suite already does via `pytest`) is the sanctioned way to execute a
`qgis`-marked test, and was used here.

`ruff check tests` and the exact `pytest --collect-only`/`pytest` command output for this round's
new test file are reported in the task's own completion report (this round's chat output), not
duplicated verbatim here.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **No genuine terminology-mapping ambiguity found.** Every row of both of Section 8.7's tables
  (the twelve real domain-layer names — thirteen table/survey-type pairs once the three `site`
  occurrences are counted separately — plus the one KTSN-lookup-layer bonus row) was explicitly
  confirmed by the stakeholder, with exactly one correction (`site`: "사이트" → "조사지," applied
  uniformly to all three occurrences) — Decision Log D-84. This round did not independently
  second-guess any of the confirmed Korean text itself (a domain-expert/stakeholder judgment call,
  not a test-design judgment call), only transcribed it exactly as written in Section 8.7 into
  `KOREAN_LAYER_DISPLAY_NAMES`/`KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME`.
- **The genuinely open, not-yet-decided scope question (the three layer-tree group names and the
  basemap layer's own name, Open Question O-39, narrowed but not closed by Decision Log D-84) is
  not silently resolved either way by this round.** This round's own negative-control test asserts
  only that group names are *currently* unaffected by this requirement's implementation — it takes
  no position on whether they *should* be changed in some future round, mirroring how Section 8.7's
  own text explicitly declines to decide this ("Whether either should also receive Korean-language
  treatment is not decided here; see Open Question O-39").
- **The pre-existing by-`.name()`-lookup interaction with `inspect_field_aliases`/
  `inspect_editor_widget`/`inspect_layer_renderer`, described in full in the dedicated section
  above, is not an ambiguity in DR-QPB-078/FR-QPB-130/AC-QPB-118's own text** — the requirement
  itself is unambiguous — but is disclosed here as a genuine, identified implementation-risk
  finding, per the same "report it, do not guess or silently patch it" discipline the
  ambiguity-handling procedure requires for a genuine ambiguity, applied here to a genuine
  cross-cutting risk instead.
