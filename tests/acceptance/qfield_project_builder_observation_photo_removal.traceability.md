# Traceability Matrix — QField Project Builder, Type 2/3 `observation_photo` Removal (Decision Log D-74/D-78)

> Specification: `specs/qfield-project-builder.md` — new `DR-QPB-074`-`DR-QPB-077` (Section 8.2,
> shared by cross-reference with Section 8.3), the struck-through/annotated `DR-QPB-031`/`DR-QPB-032`/
> `DR-QPB-033`/`DR-QPB-042` (each superseded, not deleted), the narrowed `AC-QPB-009` (Section 18.1),
> new `AC-QPB-112`/`AC-QPB-114` (Section 18.1) and `AC-QPB-113` (Section 18.6, post-MVP), Section
> 8.5's three new `observation` photo-path alias rows (Type 2 table, cross-referenced by Type 3),
> and Section 8.5's `observation_photo` rows annotated historical/moot — all from **Decision Log
> D-74** (2026-08-28; the stakeholder's verbatim instruction to stop storing Type 2/3 observation
> photos in a separate `observation_photo` child table and instead add `leaf_photo_path`/
> `flower_photo_path`/`fruit_photo_path` columns directly to `observation`, mirroring Type 1's
> `inventory_observation`, and wire this into the "identify attached photos" mechanism) and
> **Decision Log D-78** (2026-08-28; the stakeholder's explicit follow-up answer that this applies
> only to newly generated projects going forward — no migration/backward-compatibility mechanism
> for an already-generated project is required or in scope, closing Open Question O-37).
>
> This is a later `test-designer` round against the same overall specification as
> [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md) (the approved
> MVP baseline) and
> [`qfield_project_builder_post_mvp_identification.traceability.md`](qfield_project_builder_post_mvp_identification.traceability.md)
> (the approved post-MVP identification-subsystem baseline, which this round extends for its one
> touched criterion, `AC-QPB-113`, without reopening anything else in that file). It is recorded as
> its own file, not merged into either, so neither already-approved traceability record is touched
> by this round's additions — see `tests/acceptance/README.md` for the pointer between all of this
> repository's traceability files.
>
> Tests: `tests/acceptance/qfield_project_builder/test_observation_photo_removal.py` (new file,
> AC-QPB-112/AC-QPB-113/AC-QPB-114, plus the negative controls this round's task explicitly
> required — Type 2's `survey_photo`/Type 3's `plot_photo` unaffected, Type 4's `community`
> unaffected). One pre-existing test was **retired** (not merely edited) from
> `test_geopackage_schema_by_type.py` because it asserted a now-superseded premise — see "What was
> revised in already-existing test files" below. The Korean-alias half of AC-QPB-112 is covered by
> `test_korean_field_aliases.py`'s own pre-existing, data-driven tests, automatically extended by
> this round's `conftest.py` change — see
> `qfield_project_builder_korean_field_aliases.traceability.md`'s own "Correction record (Decision
> Log D-74/D-78)" section for that file's side of this round.
>
> Test harness contract: no new `acceptance_api` function was needed. This round uses three
> pre-existing harness functions unchanged — `validate_project`/`attempt_feature_save` (functions
> 5/6), `inspect_editor_widget` (function 16), and `inspect_identification_widget` (function 10) —
> plus direct inspection of the generated GeoPackage (`sqlite3`) and `.qgs` project text, mirroring
> this suite's own established "read the generated artifact's own inspectable standard format
> directly" convention (see `HARNESS_CONTRACT.md`'s top-of-document rationale, and the identical
> precedent set by `qfield_project_builder_basemap_group_stacking_order.traceability.md`, which
> likewise added no new harness function for a comparable `.qgs`-structure assertion).

## What this round covers

Three new/revised acceptance criteria, all scoped to Type 2 (`temporary_plots`) and Type 3
(`permanent_plots`) only — Type 1 (`simple_inventory`) is the existing, unaffected design being
mirrored, and Type 4 (`vegetation_mapping`) is confirmed, not merely assumed, unaffected:

1. **AC-QPB-112** — given a generated Type 2 or Type 3 project, `observation_photo` no longer
   exists anywhere in the GeoPackage, and `observation` instead has exactly three optional,
   nullable `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` columns, each configured with
   the Attachment (`ExternalResource`) editor widget and the same Korean alias already confirmed
   for Type 1's identical column names; Type 2's `survey_photo`/Type 3's `plot_photo` remain fully
   present and unaffected.
2. **AC-QPB-113** (post-MVP) — the embedded "Identify attached photos" widget's photo-paths
   expression for `observation` now reads the three inline columns directly, identically to Type
   1's `inventory_observation`, with no `relation_aggregate()` expression referencing the
   now-removed `rel_observation_photo_observation` relation.
3. **AC-QPB-114** — a Type 2/3 `observation` record with zero, one, two, or three of the three
   photo fields populated is always accepted (mirrors AC-QPB-008 for Type 1).

Plus the negative controls the task explicitly required be tested, not merely assumed:

- Type 2's `survey_photo` table and its `rel_survey_photo_survey` relation, and Type 3's
  `plot_photo` table and its `rel_plot_photo_plot` relation, are structurally distinct from the
  removed `observation_photo` and are completely unaffected.
- Type 4's `community` table has no photo mechanism of any kind (no photo-path columns, no photo
  child table, no identification widget) and is confirmed unaffected, not merely assumed to be.
- Decision Log D-78's migration/backward-compatibility scope closure: **no test in this round (or
  anywhere in this suite) exercises, or asserts the presence or absence of, any migration/
  dual-schema-read/upgrade mechanism for an already-generated project using the old
  `observation_photo` schema** — every test builds only newly generated projects. This is recorded
  explicitly in `test_observation_photo_removal.py`'s own closing module section, per this
  project's ambiguity-handling procedure (do not invent behavior the specification does not
  define, and do not silently leave a stakeholder-closed non-requirement untested without saying
  so).

## What was revised in already-existing test files (not just new tests added)

- **`tests/acceptance/qfield_project_builder/conftest.py`**:
  - `SURVEY_TYPE_SCHEMAS["temporary_plots"]`/`["permanent_plots"]`: the `observation_photo` table
    entry (and its relation tuple) was removed from each `"tables"`/`"relations"` list. This is
    consumed generically (data-driven, no hardcoded table names) by `test_geopackage_common.py`'s
    AC-QPB-002/003/004/006 tests and by `test_geopackage_schema_by_type.py`'s AC-QPB-005 test, so
    removing the entry automatically and correctly stops asserting anything about a table that no
    longer exists, with no further edit needed in either of those files.
  - `KOREAN_FIELD_ALIASES`: `_TYPE2_3_OBSERVATION_ALIASES` gained
    `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` (잎 사진/꽃 사진/열매 사진, identical
    to Type 1's own confirmed aliases); the `temporary_plots`/`permanent_plots` entries'
    `observation_photo` table dict was removed entirely, along with the now-unused
    `_OBSERVATION_PHOTO_ALIASES` constant. See
    `qfield_project_builder_korean_field_aliases.traceability.md`'s own "Correction record
    (Decision Log D-74/D-78)" section for the full before/after count reconciliation (103 → 97
    total parametrized cases in `test_korean_field_aliases.py`).
- **`tests/acceptance/qfield_project_builder/test_geopackage_schema_by_type.py`**: the pre-existing
  `test_ac009_observation_with_zero_related_photos_is_accepted` test was **retired (deleted), not
  merely edited in place** — it asserted that a Type 2/3 `observation` record with zero related
  `observation_photo` rows is accepted by save/`validate_project()`, a premise that is now moot
  once `observation_photo` no longer exists for these survey types at all (there is no longer any
  "related photo record" relationship to have zero of). Its replacement coverage — that an
  `observation` record with 0/1/2/3 of the three *inline* photo fields populated is always accepted
  — is `AC-QPB-114`, tested in this round's new `test_observation_photo_removal.py`, not by editing
  the retired test into a new shape in its original file (a clean removal-plus-fresh-test was
  judged clearer than repurposing a test whose entire premise, name, and docstring described a
  mechanism that no longer exists). The remaining `test_ac009_*` tests in that file (parent-`survey`/
  `plot`-level "zero related `survey_photo`/`plot_photo`" cases, and every malformed-attachment-path
  case, all of which use `survey_photo`, never `observation_photo`) are entirely unaffected by
  Decision Log D-74 and were left unchanged. The file's own module docstring and the (now-adjacent)
  AC-QPB-009 bullet were updated to record the narrowing and cross-reference this round's own new
  file, per this project's non-destructive-revision convention.

No other pre-existing test file needed a substantive edit: `test_post_mvp_identification_plugin.py`
already has a passing negative control for Type 4
(`test_ac070_vegetation_mapping_community_layer_has_no_qml_widget`) that this round's own new
`test_type4_community_has_no_photo_mechanism` complements at the schema level, rather than
duplicating at the widget level.

## Confirmed current (pre-implementation) behavior, verified directly

This round built real `temporary_plots`/`permanent_plots`/`simple_inventory` projects via
`build_project()` (through this suite's own isolated QGIS bridge — never by constructing a
`QgsApplication` directly) and confirmed, by direct inspection:

- `qfield_builder/schemas.py`'s `_build_temporary_plots()`/`_build_permanent_plots()` still define
  an `observation_photo` `TableDef` (with its `organ` `CHECK` constraint and
  `rel_observation_photo_observation` foreign key), exactly as Decision Log D-74/D-80's own text
  anticipated; `observation`'s own `TableDef` does not yet include `leaf_photo_path`/
  `flower_photo_path`/`fruit_photo_path`.
- `qfield_builder/qgis_worker.py`'s `_identification_photo_paths_expression()` still branches
  `table.name == "inventory_observation"` vs. a `relation_aggregate()` expression against
  `rel_observation_photo_observation` for every other table.
- `qfield_builder/korean_field_aliases.py`'s `FIELD_ALIASES_BY_TABLE["observation"]` does not yet
  include the three new photo-path fields; `FIELD_ALIASES_BY_TABLE["observation_photo"]` still
  exists.

**Confirmed by an actual test run performed during this round**
(`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_observation_photo_removal.py -q`):
**24 failed, 3 passed** — the 3 passes are exactly the negative controls (`survey_photo`/
`plot_photo` unaffected, ×2 survey types; `community` unaffected, ×1) that require no
implementation change; the 24 failures are exactly the AC-QPB-112 (schema shape ×2, sibling-
relation-absence ×2, attachment-widget-match ×6), AC-QPB-113 (×2 + ×2), and AC-QPB-114 (×8) cases
this round's task expects to be red pre-implementation. Every failure is a clean, informative
`assert` failure (see "Design choices" below for why AC-QPB-114 in particular needed strengthening
to fail red at all, rather than passing vacuously), not an uncaught exception or a collection
error. A full acceptance-suite collection run
(`.venv/bin/python -m pytest tests/acceptance --collect-only -q`) confirms **no other test file's
collection was broken by this round's `conftest.py`/`test_geopackage_schema_by_type.py` edits**
(481 tests collected). `test_geopackage_schema_by_type.py` itself, run standalone after the stale
test's removal, is **44 passed** (no regression among the tests that remain). The parallel
`test_korean_field_aliases.py` re-run this round performed is documented in
`qfield_project_builder_korean_field_aliases.traceability.md` instead (89 passed, 8 failed there).

## Design choices this round made, and why

- **A dedicated new file, not additions to `test_geopackage_schema_by_type.py` or
  `test_post_mvp_identification_plugin.py`.** AC-QPB-112/113/114 together describe one coherent
  schema/behavior change spanning GeoPackage shape, `.qgs` relation/widget configuration, and the
  post-MVP identification mechanism. Keeping all of it in one new file (mirroring this suite's own
  established precedent of a dedicated file per substantial round — e.g. `test_symbol_styling.py`,
  `test_ktsn_lookup_table.py`, `test_map_canvas_pan_navigability.py`) keeps this round's own
  traceability legible as a single unit, rather than splitting it across two pre-existing files
  whose own module docstrings would otherwise need substantial rewriting to explain a change that
  is not really "about" either file's own original scope.
- **The Korean-alias half of AC-QPB-112 is deliberately not re-tested in the new file** — it is
  already fully covered by `test_korean_field_aliases.py`'s own pre-existing, data-driven tests,
  automatically extended by this round's `conftest.py`/`KOREAN_FIELD_ALIASES` update. Duplicating
  an alias assertion in the new file as well would test the identical underlying fact
  (`QgsField.alias()`) twice under two different test names for no added coverage — mirroring this
  suite's own explicit precedent for exactly this kind of non-duplication decision (see
  `qfield_project_builder_korean_field_aliases.traceability.md`'s own note 2, "AC-QPB-098's own
  ... clause is not re-tested here ... for no added coverage").
- **AC-QPB-114's test needed strengthening beyond a bare `outcome["accepted"] is True` assertion,
  to actually fail red pre-implementation.** `qfield_builder/feature_save.py`'s
  `_attempt_feature_save_pyqgis` silently drops any attribute key that does not match a real field
  on the layer (`idx = layer.fields().indexOf(name); if idx >= 0: attribute_map[idx] = value`) —
  confirmed by direct inspection during this round. Against the current, not-yet-updated schema
  (`observation` without the three new columns), a bare acceptance assertion would have **passed
  vacuously**: the unknown `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` keys are simply
  ignored, and the remaining valid attributes (`cover`, `selected_scientific_name`, `survey_id`)
  are already sufficient for the save to succeed on their own — confirmed by an actual test run
  during this round's own authoring process, before this strengthening was added, which showed
  exactly this false-green result. The test was revised to read the saved row back from the
  GeoPackage by its `generated_uuid` and assert the three columns actually exist and actually
  persisted the supplied value (or remained `NULL` when omitted) — this is the same
  "read the generated artifact back to confirm a real, not merely-accepted, effect" pattern this
  suite already uses elsewhere (e.g. `test_geopackage_schema_by_type.py`'s own
  `test_ac009_photo_record_needs_valid_path_and_missing_file_is_a_broken_attachment`), not an
  invented new testing mechanism.
- **AC-QPB-113's second test (`test_ac113_observation_expression_matches_type1_inline_mechanism_
  shape`) is a deliberately stronger companion to the first, not redundant with it.** AC-QPB-113's
  own text requires the expression read the three columns "identically to Type 1's
  `inventory_observation`" — not merely "not via `relation_aggregate()`." DR-QPB-076's own text
  confirms the intended design is a single, table-name-agnostic code path ("no `relation_
  aggregate()` branch remaining for any table in `IDENTIFICATION_TARGET_LAYERS`"), not two
  independent inline-reading implementations that both happen to avoid `relation_aggregate()`. The
  second test asserts this directly: it builds both `inventory_observation` (identification-
  enabled) and `observation` (identification-enabled, both survey types) in the same test run,
  extracts each one's baked-in `expression.evaluate("...")` string via `inspect_identification_
  widget`'s existing `qml_code` field, and asserts the two expressions are identical once the
  three field names are normalized away to placeholder tokens. This is a fair, textually-justified
  strengthening of "identically," not an invented implementation-detail assumption — it does not
  assume any particular function name or syntax beyond what Type 1's own already-shipped, unchanged
  expression already uses today (confirmed by direct inspection: `array_to_string(array_remove_
  all(array(leaf_photo_path,flower_photo_path,fruit_photo_path), NULL), ',')`), and it would remain
  satisfied by any future refactor of that shared mechanism, so long as `observation` and
  `inventory_observation` genuinely continue sharing it.
- **No new `acceptance_api` function was added.** Every fact this round's tests need is already
  exposed by three pre-existing harness functions (`inspect_editor_widget`, `inspect_identification_
  widget`, `attempt_feature_save`/`validate_project`) plus direct GeoPackage/`.qgs`-text inspection.
  The relation-absence check (`rel_observation_photo_observation` no longer appears in the
  generated `.qgs` file) and the sibling-relation-presence check (`rel_survey_photo_survey`/
  `rel_plot_photo_plot` still appear) both use a plain substring search against the `.qgs` file's
  own raw text, mirroring the already-established convention `test_qgis_project_config.py::test_
  qgs_and_gpkg_paths_are_relative_to_each_other`/`test_geopackage_schema_by_type.py::test_ac015_
  community_symbology_rule_exists_in_qgs_project` already set for reading a generated project's own
  inspectable XML directly rather than inventing a new PyQGIS-backed relation-listing function for
  a fact a plain text search already answers unambiguously (a relation's own stable `id()` string,
  e.g. `rel_observation_photo_observation`, is exactly the kind of literal, unique, `id="..."`-style
  token this suite's own `HARNESS_CONTRACT.md` top-of-document rationale already prefers reading
  directly over inventing an inspection API for).
- **`inspect_editor_widget`'s existing return contract (function 16) does not expose the
  `ExternalResource` widget's own configuration dict (`RelativeStorage`/`DocumentViewer`/
  `FileWidget`), only its `widget_type` string.** AC-QPB-112's own text asks for widget
  configuration "matching `inventory_observation`'s own existing widget configuration exactly."
  This round's test asserts equality of `widget_type` (`"ExternalResource"` for both) and of
  `is_read_only`, the two facts function 16 actually exposes — a real, if partial, confirmation of
  "matching exactly." A full field-by-field comparison of the underlying `QgsEditorWidgetSetup`
  config dict would require extending function 16's return contract further; this was judged
  unnecessary rather than a gap, because `qfield_builder/qgis_worker.py`'s own
  `_configure_widget_for_column` applies the identical `ExternalResource` configuration to *every*
  column with `is_attachment_path=True`, regardless of table name (confirmed by direct inspection:
  a single, unconditional `if col.is_attachment_path:` branch, not a per-table special case) — so
  once `observation`'s three new columns are declared via the same `_photo_path_col()` helper
  Type 1 already uses (DR-QPB-020/DR-QPB-074's own shared design precedent), the exact same code
  path necessarily configures them identically, with no table-specific branching possible to get
  wrong. This is disclosed here as a documented scope note, not silently assumed.

## Traceability table

| AC ID / DR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-112 (table/column shape) | No `observation_photo` table anywhere in a generated Type 2/3 project | `test_observation_photo_removal.py::test_ac112_observation_photo_table_no_longer_exists` (parametrized: `temporary_plots`, `permanent_plots`) | auto |
| AC-QPB-112 (column shape) | `observation` has exactly the three new optional, nullable photo-path columns; no `organ` column reintroduced anywhere on `observation` | `test_observation_photo_removal.py::test_ac112_observation_has_exactly_three_optional_nullable_photo_path_columns` (parametrized, both survey types) | auto |
| AC-QPB-112 (relation absence) | `rel_observation_photo_observation` no longer exists anywhere in the generated `.qgs` project | `test_observation_photo_removal.py::test_ac112_rel_observation_photo_observation_relation_no_longer_exists` (parametrized, both survey types) | auto |
| AC-QPB-112 (widget configuration) | The three new fields use the Attachment (`ExternalResource`) editor widget, matching `inventory_observation`'s own existing widget configuration exactly (within what `inspect_editor_widget`'s contract exposes — see "Design choices" above) | `test_observation_photo_removal.py::test_ac112_observation_photo_fields_use_the_same_attachment_widget_as_type1` (parametrized: 3 fields × 2 survey types = 6 cases) | auto |
| AC-QPB-112 (Korean alias) | The three new fields carry Type 1's already-confirmed aliases (잎 사진/꽃 사진/열매 사진) | `test_korean_field_aliases.py::test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias` (6 of its 71 total cases now cover this — see `qfield_project_builder_korean_field_aliases.traceability.md`'s own Decision Log D-74/D-78 correction record); not duplicated in this file (see "Design choices" above) | auto |
| AC-QPB-112 (negative control: sibling photo tables unaffected) | Type 2's `survey_photo`/`rel_survey_photo_survey` and Type 3's `plot_photo`/`rel_plot_photo_plot` remain fully present and unaffected | `test_observation_photo_removal.py::test_ac112_sibling_photo_table_and_relation_are_completely_unaffected` (parametrized, both survey types) | auto |
| AC-QPB-113 (post-MVP; necessary condition) | The `observation` photo-paths expression no longer uses `relation_aggregate()`/references `rel_observation_photo_observation`, and reads the three inline columns directly | `test_observation_photo_removal.py::test_ac113_observation_identification_expression_reads_inline_columns_not_relation_aggregate` (parametrized, both survey types) | auto |
| AC-QPB-113 (post-MVP; "identically to Type 1" strengthening) | The `observation` expression shares the identical structural mechanism as `inventory_observation`'s own expression, field names aside | `test_observation_photo_removal.py::test_ac113_observation_expression_matches_type1_inline_mechanism_shape` (parametrized, both survey types) | auto |
| AC-QPB-114 | A Type 2/3 `observation` record with 0/1/2/3 of the three photo fields populated is always accepted, and the supplied value(s) are actually persisted (not merely silently ignored) | `test_observation_photo_removal.py::test_ac114_type2_3_observation_photo_field_combinations_are_all_accepted` (parametrized: 4 combinations × 2 survey types = 8 cases) | auto |
| AC-QPB-009 (narrowed; Decision Log D-74) | The struck-through "or observation" clauses no longer apply; the surviving `survey`/`plot`-level "zero related photos" rules are unaffected | Unaffected `test_ac009_*` tests in `test_geopackage_schema_by_type.py` (unchanged); the retired `observation`-specific test's replacement coverage is AC-QPB-112/AC-QPB-114 above, not a like-for-like AC-QPB-009 test (see "What was revised" above for why) | auto |
| (negative control) Type 4 unaffected | `community` has no photo-path column, no photo child table, no identification widget | `test_observation_photo_removal.py::test_type4_community_has_no_photo_mechanism` (schema level); `test_post_mvp_identification_plugin.py::test_ac070_vegetation_mapping_community_layer_has_no_qml_widget` (widget level, pre-existing, unchanged) | auto |
| (negative control) Decision Log D-78 — no migration/backward-compatibility scope | No test anywhere in this round (or this suite) asserts any migration/dual-schema-read/upgrade behavior | Documented directly in `test_observation_photo_removal.py`'s own closing module comment; no test function exists for this by design | n/a (deliberately not tested — see "Ambiguities / gaps found" below) |

## Ambiguities / gaps found

- **No genuine ambiguity found in DR-QPB-074-077/AC-QPB-112/113/114/AC-QPB-009 (narrowed) as
  written.** Decision Log D-74's own text is unusually explicit about scope (both Type 2 and Type
  3; cardinality exactly matches Type 1's design; the exact mechanism change needed in
  `_identification_photo_paths_expression`; the exact Korean aliases to reuse), and Decision Log
  D-78 explicitly closes the one question D-74 itself left open (migration/backward-compatibility)
  with a direct, unambiguous "not required" answer. Every criterion this round tests traces
  directly to specific, unambiguous specification text; no invented behavior was needed anywhere in
  this file.
- **The exact `ExternalResource` config-dict-level "matching exactly" comparison is disclosed as a
  documented scope note, not a gap silently left uncovered** — see "Design choices" above for the
  full reasoning (the shared, table-name-agnostic `_configure_widget_for_column` code path makes a
  deeper comparison structurally guaranteed, not merely untested).
- **This round did not re-examine Section 8.6/8.7 (Korean relation-widget display names / Korean
  layer display names) for any interaction with this change.** Both are confirmed, by direct
  reading of Section 8.6/8.7's own text, to already correctly exclude
  `rel_observation_photo_observation`/`observation_photo` from their own proposed-name tables
  (Section 8.6's own text: "`rel_observation_photo_observation` is deliberately excluded... since
  proposing a Korean name for it here would be moot"; Section 8.7's Type 2/3 rows: "moot; this
  table no longer exists"), so no additional test was needed for either — those two sections'
  own existing acceptance criteria (AC-QPB-111, AC-QPB-118) are unaffected by, and do not need to
  additionally assert anything about, this round's change.
