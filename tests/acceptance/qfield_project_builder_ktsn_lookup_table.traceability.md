# Traceability Matrix — QField Project Builder, KTSN Accepted-Name Lookup Table / Autofill

> Specification: `specs/qfield-project-builder.md`, Section 7 (new `DR-QPB-072`), Section 9 (new
> `FR-QPB-124`/`FR-QPB-125`/`FR-QPB-126`/`FR-QPB-127`), Section 13.3 (`FR-QPB-105`, further revised),
> Section 13.9, Section 8.1/8.2/8.3's revised `selected_korean_name`/`selected_scientific_name`/
> `selected_ktsn` field-table entries, Section 18.1/18.2 (`AC-QPB-105`–`109`) — Decision Log D-62
> (investigation/proposal record) resolved by Decision Log D-66 (architecture/scope), D-67 (synonym
> handling/derived fields), D-68 (bundling scope), closing Open Questions O-28, O-29, O-30, O-31,
> O-32; and, in a follow-up round below, Decision Log D-70 (FR-QPB-105's second, independent
> trigger condition; new `AC-QPB-109`), closing Open Question O-34.
>
> This is a **later, separate `test-designer` round against the same overall specification** as
> `qfield_project_builder.traceability.md` (the approved MVP baseline), recorded as its own file
> per this project's established convention (see `tests/acceptance/README.md`), so the
> already-approved MVP/post-MVP traceability records are not touched by this round's additions.
>
> **Follow-up round (this file's own "AC-QPB-109 addendum" section below):** Decision Log D-70
> closes a genuine specification gap this same file's own D-64–D-69 round found and explicitly
> reported (see the now-resolved historical shared-fixture section below) — this
> is a distinct, later `test-designer` invocation against the resulting spec revision, adding only
> `AC-QPB-109`'s tests/traceability row on top of the D-64–D-69 content below, which it leaves
> otherwise unchanged (see the addendum section for what was, and was not, found to need updating).
>
> Tests: `tests/acceptance/qfield_project_builder/test_ktsn_lookup_table.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (Decision Log D-64–D-69...)" section (functions 16–17: `inspect_editor_widget`,
> `derive_accepted_name_lookup_table`; the `ktsn_lookup_table_name` `build_project` return
> addition). `AC-QPB-109`'s own two new tests reuse this same harness surface (`build_project`'s
> existing `success`/`error_code`/`error_message` result keys and the existing
> `REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR` fixture) — no harness-contract change was needed.

> **Maintenance reconciliation (2026-09-04):** The shared acceptance config now selects the
> canonical D-95 workbook explicitly. Tests that intentionally exercise the pre-D-95 CSV/filtered
> contract are isolated with the `legacy_compatibility` marker and explicitly opt into
> `legacy_reference_compatibility`; no normal new-build test relies on automatic legacy fallback.

## What this round covers, and its own scope note

This is the largest of the D-60–D-69 stakeholder-decision items: a real, bundled, indexed
accepted-name lookup table (DR-QPB-072); a `ValueRelation` widget on `selected_korean_name`
(FR-QPB-124); derived, read-only `selected_scientific_name`/`selected_ktsn` fields via
`QgsDefaultValue`/`applyOnUpdate` (FR-QPB-125); the table's own accepted-only row-derivation rule
(FR-QPB-126); and unconditional bundling for every Types 1–3 project, independent of
`identification_enabled` (FR-QPB-127). New AC-QPB-105–108 make this independently testable.

**Explicitly out of scope, confirmed by the specification itself, not touched by this round:**
`dominant_species` (Type 4 `community`) — Decision Log D-66/O-29 explicitly excludes it; DR-QPB-050's
existing Type-4 exclusion is confirmed unaffected. `test_ac105_type4_dominant_species_is_unaffected_
not_a_value_relation_widget`/`test_ac108_type4_vegetation_mapping_has_no_lookup_table_even_when_
disabled` confirm this negatively, they do not test any Type-4 lookup behavior positively (there is
none to test).

## Genuinely out of this harness's reach, not silently claimed as covered

**AC-QPB-107's "works identically for a brand-new feature and for an existing, already-saved
feature reopened later" claim — the *live, cross-session* half only.** FR-QPB-125's own confirmed
technical finding (Decision Log D-67) is that `QgsDefaultValue.applyOnUpdate` is genuinely
*layer-level* field configuration, re-evaluated by QGIS's/QField's own standard live-default-value
machinery on every feature update — unlike Decision Log D-50's custom QML write-back hack, there is
no separate "brand-new feature" vs. "reopened feature" *code path* in this mechanism at all; it is
one configuration, applied uniformly. This round's structural test
(`test_ac107_field_is_derived_and_read_only_via_apply_on_update_default_value`) verifies that
single, layer-level configuration exists (the `QgsDefaultValue` expression referencing
`selected_korean_name`, `applyOnUpdate=True`, and the field's own read-only flag) — which, by
construction, is what makes the "works identically for both cases" claim true *if* QGIS's/QField's
own engine correctly implements `applyOnUpdate` as documented. Genuinely *exercising* that engine
end-to-end — actually reopening an already-saved feature in a live QGIS Desktop/QField session and
confirming the re-derivation happens on screen — requires a real, running editing session this
harness cannot drive (no QField/QML runtime; this project's hard QGIS-isolation rule also bars
constructing a `QgsApplication` for any diagnostic purpose). A documented, `manual`-marked, skipped
placeholder is added —
`test_ac107_live_re_derivation_works_identically_for_a_reopened_already_saved_feature` — mirroring
this suite's own established convention for exactly this category of criterion (e.g.
`test_post_mvp_manual_qfield_runtime.py`'s `AC-QPB-046a`/`046b` placeholders for Decision Log D-50's
own, structurally different, per-session write-back mechanism).

## Historical shared-fixture finding (resolved by maintenance)

**Historical finding: FR-QPB-127's unconditional-bundling scope vs.
`make_base_config()`/`built_project_by_type()`'s existing defaults.** See
`HARNESS_CONTRACT.md`'s own "Flagged interaction..." note (reproduced in full there) for the
complete reasoning; summarized here: FR-QPB-127 (Decision Log D-68) makes the accepted-name
lookup table's build-time derivation/bundling — and therefore FR-QPB-105's reused source-CSV
presence/required-column fail-early validation — run **unconditionally** for every Types 1–3 build,
independent of `identification_enabled`. This suite's own pre-existing `make_base_config()`/
`built_project_by_type()`/`isolated_project_by_type()` fixtures, used by dozens of already-approved
MVP tests across this entire suite, default to `identification_enabled=False` **and supply no
`_test_reference_data_dir` override at all** — meaning that, once FR-QPB-127 is implemented, a
Types 1–3 build made through *those* fixtures would resolve reference data from the real,
production-default `REFERENCE_DATA_DIR` location, which is gitignored, machine-local data this
repository's own existing fixtures already document as "not guaranteed present on a fresh
checkout." **Concretely: every one of the dozens of pre-existing MVP acceptance tests that build a
Types 1–3 project via `built_project_by_type`/`make_base_config()` (e.g. every test in
`test_geopackage_common.py`, `test_qgis_project_config.py`, `test_korean_field_aliases.py`, and
many others) would begin failing FR-QPB-105's early-failure validation on any machine lacking the
real `storage/reference/` scaffold, purely as a side effect of implementing FR-QPB-127 — unless the
implementer arranges for the production-default `REFERENCE_DATA_DIR` to always resolve to
something present in every environment a Types 1–3 project can be built in (a packaging/
distribution concern Decision Log D-44 addresses only for the *distributed, packaged* macOS
application, not for a developer/CI working tree building from source).**

The alternatives below record the original routing discussion; the current harness follows the
canonical-fixture path and does not use a legacy fixture as an implicit fallback:

- (a) the production-default `REFERENCE_DATA_DIR` should always point at something bundled inside
  the repository/package itself (not gitignored), so a Types 1–3 build always succeeds regardless
  of environment — in which case every existing gitignored-reference-data-skip convention in this
  suite (`real_ktsn_csv_path`/`real_nibr_xlsx_path`/`real_probability_raster_dir`) would need
  re-examination for *this* new, smaller, always-required table specifically, even though the much
  larger `reference/ktsn_lookup.csv`/probability-raster bundle remains genuinely optional/gitignored;
- (b) a Types 1–3 build should be allowed to *degrade* (proceed without the lookup table, or with
  an empty one) when the source reference data is genuinely absent, rather than fail-early — which
  would itself be a substantive, unstated relaxation of FR-QPB-127's own "must always run and always
  be bundled" / reused-FR-QPB-105-fail-early-discipline text; or
- (c) this is simply an accepted, known operational precondition (every environment building a
  Types 1–3 project, in development/CI or production, is expected to always have the reference data
  scaffold present) that this specification's own text already implies but this suite's existing
  test-fixture defaults have not yet been updated to reflect, and updating those *shared* fixture
  defaults (`make_base_config`/`built_project_by_type`) is simply future `test-designer`/
  `implementer` housekeeping once this ambiguity is resolved.

**Historical resolution recommendation:** route this through `spec-writer` for an explicit
stakeholder decision. That decision is now recorded as Option (c), and the shared fixture
housekeeping has been applied: normal builds select the canonical D-95 workbook explicitly.

**RESOLVED at the specification and fixture level by Decision Log D-70 and this maintenance round.**
The stakeholder chose Option (c), confirming — rather than relaxing — the fail-early contract.
`make_base_config()` now supplies the canonical workbook path, while tests for the retained
pre-D-95 CSV/filtered path explicitly set `reference_compatibility_mode="legacy_reference_compatibility"`
and are marked `legacy_compatibility`. No normal new-build test silently falls back to legacy data.

## Design choices this round made, and why

- **Normal `build_project()` calls use the canonical D-95 workbook explicitly.** The existing
  `REFERENCE_DATA_VALID_SAMPLE_DIR` remains only as the small raster sidecar for those builds;
  its neighboring pre-D-95 CSV/XLSX files cannot be selected accidentally. The canonical workbook
  is also the oracle for the generated lookup-table row-set comparison, so this regression checks
  the current product source contract rather than treating a legacy fixture as an equivalent input.
- **Legacy-only helper checks retain small, clearly-labeled synthetic fixtures.** The two
  `derive_accepted_name_lookup_table()` tests are marked `legacy_compatibility` and preserve
  coverage for blank `taxon_jm_nm` exclusion and leading-zero `ktsn` string preservation without
  presenting those pre-D-95 inputs as valid new-build fixtures.
- **One new, small, clearly-labeled synthetic CSV fixture was added**
  (`fixtures/ktsn_step5_accepted_only_synthetic.csv`) specifically to isolate two properties the
  existing real-data fixture cannot exercise on its own: a row with a *blank* `taxon_jm_nm` value
  (as distinct from an explicit synonym/`이명` value — FR-QPB-126's own text requires both to be
  excluded, but they are different underlying data shapes) and `ktsn` string-preservation with a
  leading zero (the real, full source CSV was already confirmed, by a prior round's full-file scan,
  to contain zero rows with a leading-zero `ktsn` value — mirroring this suite's own established
  precedent for exactly this situation, e.g. `fixtures/reference_data_ktsn_lookup_sample/`'s own
  synthetic leading-zero row).
- **`inspect_editor_widget()` is used for both `ValueRelation` (FR-QPB-124) and the derived-field
  `QgsDefaultValue`/`applyOnUpdate` inspection (FR-QPB-125), rather than a raw `.qgs` XML regex.**
  Neither the exact registered `ValueRelation` widget-type-ID string nor the exact
  `QgsDefaultValue`/`applyOnUpdate` XML serialization shape has been independently confirmed
  against a live QGIS instance by this test-designer round (this project's hard QGIS-isolation rule
  bars constructing a `QgsApplication` for that purpose) — mirroring the exact same posture
  `inspect_identification_widget`/`inspect_field_aliases` already established for "QML Widget"/
  field-alias inspection. See HARNESS_CONTRACT.md function 16's own note.
- **FR-QPB-124's own disclosed "cap at five results" caveat is not asserted as confirmed
  runtime behavior.** `test_ac105_...` checks only that `has_filter_or_completer_config` is `True`
  (a completer and/or filter expression is configured) — it does not, and cannot, assert that
  exactly five results are displayed at runtime, matching FR-QPB-124's own explicit disclosure that
  this is "not independently verified by this specification" and is "implementer work to report
  back."

## Traceability table

| AC ID / FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-105 | `selected_korean_name` (Types 1-3) uses a `ValueRelation` widget referencing the bundled lookup table, with a filter/completer configuration; `dominant_species` (Type 4) is unaffected | `test_ktsn_lookup_table.py::test_ac105_selected_korean_name_uses_a_value_relation_widget_referencing_the_lookup_table` (parametrized, 3 survey types), `::test_ac105_type4_dominant_species_is_unaffected_not_a_value_relation_widget` | auto (proxy — PyQGIS-backed `inspect_editor_widget`; the exact "capped at five" runtime behavior is explicitly not asserted — see design-choices note) |
| AC-QPB-106 | The bundled lookup table has a real, build-time-created index on its Korean-name and scientific-name columns | `test_ktsn_lookup_table.py::test_ac106_bundled_lookup_table_has_a_real_index_on_korean_and_scientific_name_columns` (parametrized, 3 survey types) | auto (direct `PRAGMA index_list`/`index_info` inspection of the generated GeoPackage — robust to exact `CREATE INDEX` SQL-text formatting) |
| AC-QPB-107, half 1 (derived, read-only fields) | `selected_scientific_name`/`selected_ktsn` are each configured with a `QgsDefaultValue` (`applyOnUpdate=True`) expression referencing `selected_korean_name`, and are non-editable | `test_ktsn_lookup_table.py::test_ac107_field_is_derived_and_read_only_via_apply_on_update_default_value` (parametrized, 2 fields × 3 survey types) | auto (proxy — `inspect_editor_widget`; structural, field-level configuration only — see the "genuinely out of this harness's reach" note above for the live-behavior half) |
| AC-QPB-107, half 2 (no synonym rows in the lookup table) | The bundled lookup table contains no row with `taxon_jm_nm != '정명'` | `test_ktsn_lookup_table.py::test_ac107_bundled_lookup_table_matches_canonical_accepted_rows` (parametrized, 3 survey types; compares the generated table with D-95 canonical ingestion), `::test_legacy_derive_accepted_name_lookup_table_excludes_a_blank_taxon_jm_nm_row`, `::test_legacy_derive_accepted_name_lookup_table_preserves_ktsn_as_a_string_with_leading_zero` (explicit `legacy_compatibility`) | auto |
| AC-QPB-107, half 3 (live, cross-session re-derivation on a reopened feature) | Genuinely exercising QGIS's/QField's own live-default-value engine on an already-saved, reopened feature | `test_ktsn_lookup_table.py::test_ac107_live_re_derivation_works_identically_for_a_reopened_already_saved_feature` | **manual** (documented, skipped — see the "genuinely out of this harness's reach" note above) |
| AC-QPB-108 | The lookup table, its index, and the `ValueRelation`/derived-field configuration are present and functional in a Types 1-3 project even when `identification_enabled=False` | `test_ktsn_lookup_table.py::test_ac108_lookup_table_present_indexed_and_referenced_when_identification_disabled` (parametrized, 3 survey types), `::test_ac108_type4_vegetation_mapping_has_no_lookup_table_even_when_disabled` (negative control) | auto — and, as a design choice (see module docstring), *every other test in this file* also builds with `identification_enabled=False`, so AC-QPB-108's own claim is additionally, incidentally reconfirmed by every other passing test in this file |
| DR-QPB-072 (no numbered AC beyond AC-QPB-106/107/108 above; the table's own bundling/placement rule) | Bundled as a non-spatial table inside the existing survey `.gpkg` (not a second file); populates the "Reference" layer-tree group as its first layer; Types 1-3 only | Table-inside-existing-`.gpkg`/Types-1-3-only: implicitly confirmed by every test above (all read `result["gpkg_path"]`, the same file every other domain table lives in, and `ktsn_lookup_table_name` is `None` for Type 4). "Reference" layer-tree-group population specifically: **not separately asserted by a dedicated test in this round** — see "Ambiguities / gaps found" below | auto (partial — see ambiguities note) |
| AC-QPB-109 *(new; follow-up round; Decision Log D-70; closes O-34)* | FR-QPB-105 (further revised)'s new, independent second trigger condition — a Types 1-3 build must still fail early on a missing/invalid raw KTSN reference CSV even when `identification_enabled=False` — is independently testable, distinct from AC-QPB-108 (which always supplies valid reference data) | `test_ktsn_lookup_table.py::test_ac109_missing_raw_reference_csv_still_fails_build_early_when_identification_disabled` (parametrized, 3 survey types), `::test_ac109_reference_csv_missing_required_columns_still_fails_build_early_when_disabled` (parametrized, 3 survey types); both explicitly use `legacy_compatibility` to test the retained fail-closed seam | auto — acceptance contract retained; implementation status is recorded in the historical addendum below |

## Ambiguities / gaps found (routing recommendation, not silently resolved)

1. **The main flagged interaction is the shared-fixture-default gap already reported in full above
   ("Flagged interaction with this suite's own shared fixture defaults") — repeated here only as a
   pointer, not duplicated, per this project's own established cross-referencing convention.**
2. **DR-QPB-072's "Reference" layer-tree-group population is not separately, directly asserted by
   this round's own tests.** DR-QPB-072 requires the lookup table be "loaded into the generated
   project's `.qgs` file as the first layer to actually populate the pre-existing, previously-
   always-empty 'Reference' layer-tree group (FR-QPB-055)." This round's own assigned AC list
   (AC-QPB-105–108) does not itself name a criterion specifically testing layer-tree-group
   placement — AC-QPB-106 tests the index, AC-QPB-107/108 test widget/field configuration and
   unconditional presence, none tests *where in the layer tree* the table's layer sits. This is a
   genuine, disclosed gap in this round's own coverage against DR-QPB-072's full text, not
   something silently claimed as covered by the tests above (which only confirm the table exists in
   the same `.gpkg` and is queryable/indexed — not its `.qgs` layer-tree placement). Flagged here
   for a future round to close, rather than adding an unreviewed, ad hoc assertion outside this
   round's assigned AC scope.

## AC-QPB-109 addendum (follow-up round; Decision Log D-70; closes O-34)

This section records a **later, separate `test-designer` invocation** against this same
specification file, tasked only with: (1) writing acceptance test(s) for the new `AC-QPB-109`
(Section 18.2), (2) adding its traceability row (done above), and (3) confirming whether Decision
Log D-70's `FR-QPB-105`/`FR-QPB-112` revisions require any change to the *existing* D-64–D-69 tests
already in this file (or elsewhere in this suite). This addendum does not revise or reopen any
D-64–D-69 content above; it only adds `AC-QPB-109` coverage and reports the confirmation findings
below.

### What was added

Two explicit compatibility tests in `test_ktsn_lookup_table.py`, added under a new
`# --- AC-QPB-109 ...` section following the existing `AC-QPB-108` tests, each parametrized over
the three Types 1–3 survey types (mirroring this file's own existing `TYPES_1_TO_3` convention).
They remove the canonical path, set `reference_compatibility_mode="legacy_reference_compatibility"`,
and are marked `legacy_compatibility`; this preserves the old fail-closed contract without making
legacy input an implicit new-build fallback:

- `test_ac109_missing_raw_reference_csv_still_fails_build_early_when_identification_disabled` —
  builds a Types 1–3 project with `identification_enabled=False` and a `_test_reference_data_dir`
  override pointing at an empty scaffold directory (a `tables/` folder and the raster subfolder,
  both empty — no CSV at all), mirroring `test_post_mvp_reference_bundling.py`'s own
  `test_fr105_missing_reference_csv_fails_build_early_with_a_clear_message` (the existing
  `identification_enabled=True`-trigger structural template this round was pointed at), adapted to
  the new `identification_enabled=False` trigger. Asserts `result["success"] is False`, a non-null
  `error_code`, and a non-empty `error_message`.
- `test_ac109_reference_csv_missing_required_columns_still_fails_build_early_when_disabled` — same
  structure, using the existing `REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR` fixture (a real CSV
  header lacking `taxon_jm_nm`/`correct_list`) in place of a wholly missing CSV, mirroring
  `test_post_mvp_reference_bundling.py::test_fr105_reference_csv_missing_required_columns_fails_
  build_early`. Same three assertions.

No new fixture files were authored: both tests reuse fixtures this suite already has (the inline
empty-directory-creation pattern already established in `test_post_mvp_reference_bundling.py`, and
the existing `REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR`). No harness-contract (`HARNESS_CONTRACT.
md`) change was needed — `build_project()`'s existing `success`/`error_code`/`error_message` result
keys, already used by every other `FR-QPB-105` test in this suite, are sufficient.

### Confirmation task: do the existing D-64–D-69 tests need any change?

**No change was needed to any existing D-64–D-69 test, in this file or elsewhere in this suite.**
Specifically checked:

- **`AC-QPB-108`'s own test
  (`test_ac108_lookup_table_present_indexed_and_referenced_when_identification_disabled`), whose
  traceability note above says it "assumes valid reference data is present."** This assumption
  still holds correctly. That test always passes
  `_test_reference_data_dir=REFERENCE_DATA_VALID_SAMPLE_DIR` (a real, valid reference-data
  scaffold), so it never exercises FR-QPB-105's fail-early path either before or after D-70 — D-70
  only changes *when* the validation runs (the trigger condition), never *what* it validates or how
  a *valid* input behaves. Nothing in `AC-QPB-108`'s Given/When/Then text, or D-70's own text,
  contradicts the other — `AC-QPB-108` ("present and functional... even when identification is
  disabled," always with valid data) and `AC-QPB-109` ("still fails early... even when
  identification is disabled," always with invalid/missing data) are the positive and negative
  halves of the same underlying trigger-condition claim, not in tension.
- **Every other test in `test_ktsn_lookup_table.py`** (`AC-QPB-105`, `106`, `107`) also always
  passes `_test_reference_data_dir=REFERENCE_DATA_VALID_SAMPLE_DIR` (per this file's own documented
  "Design choice" in the module docstring), so none of them exercise the fail-early path either;
  none needed a change.
- **`test_post_mvp_reference_bundling.py`'s own `FR-QPB-105`/`AC-QPB-083` tests** (the
  `identification_enabled=True`-trigger tests this round used as its structural template) are
  unaffected: D-70's second trigger is additive (an *or*-condition), and every one of those tests
  already sets `identification_enabled=True`, which was, and remains, sufficient on its own to
  trigger the validation. Confirmed by inspection — no assertion in that file depends on
  `identification_enabled=False` *not* triggering validation.
- **Every other pre-existing MVP acceptance test in this suite that builds a Types 1–3 project via
  `built_project_by_type`/`make_base_config()` with `identification_enabled=False` and no
  `_test_reference_data_dir` override** (e.g. `test_geopackage_common.py`,
  `test_qgis_project_config.py`, `test_korean_field_aliases.py`, and many others) is **not**
  contradicted by D-70's text, and D-70 does not ask this round to change any of them — but they
  remain the same already-flagged, already-disclosed exposure the D-64–D-69 round's own "Flagged
  interaction" section already reported (repeated, not duplicated, in this addendum's own
  "Red/green result" note below): once an implementer actually wires up FR-QPB-105's new second
  trigger, any of those tests run on a machine lacking the real `storage/reference/` scaffold would
  begin failing, purely as a side effect. D-70 confirms this is the *intended*, accepted
  precondition (Option (c)) rather than a defect to work around — but the *mechanical* fixture-
  default housekeeping this implies (giving `make_base_config`/`built_project_by_type` a small,
  synthetic reference-data override by default, matching this file's own existing per-file
  convention) is explicitly deferred by D-70 itself to "a future `test-designer`/`implementer`
  round," not performed by this addendum, which was scoped only to `AC-QPB-109` plus this
  confirmation check. Reported here, not silently carried forward or silently fixed.

**`FR-QPB-112`'s own purely additive D-70 cross-reference** (confirming its ~247 MB bundle remains
conditional on `identification_enabled`, unaffected by FR-QPB-105's new second trigger) required no
test change either: every `FR-QPB-112`/`AC-QPB-071` test in `test_post_mvp_reference_bundling.py`
already builds with `identification_enabled=True` (via that file's own `_build_with_identification`
helper), so none of them ever depended on, or could be affected by, the *disabled* case D-70's
cross-reference clarifies.

### Red/green result (this round's own two new tests)

Ran `./.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_ktsn_lookup_table.py
-q` after adding the two new tests above. Both `AC-QPB-109` tests are **currently red (failing)**,
for the expected, correct reason at this stage: `qfield_builder/build.py::build_project()` (line
~248) still gates its call to `reference_bundle.validate_reference_data()` — FR-QPB-105's own
validation function — strictly behind `if identification_enabled:`, exactly the pre-D-70 behavior
D-70 revises. Concretely, every new `AC-QPB-109` test observed `result["success"] is True` (the
build silently succeeded despite the missing/invalid reference data) instead of the expected
`False`, because nothing in the current, uncommitted application code yet reads reference data at
all when `identification_enabled=False` (confirmed by inspection: no `ktsn_lookup_table_name`
appears anywhere in `qfield_builder/*.py` — `DR-QPB-072`'s entire accepted-name-lookup-table
feature, including its own D-64–D-69 predecessor `AC-QPB-105`–`108`, is not implemented yet
either). This is the same "red before implementation" state the rest of this file's own tests are
already in (9 of the file's 30 tests fail or are unexpectedly not-skipped for the same
not-yet-implemented reason; 19 are cleanly skipped via documented "not implemented yet" guards on
`inspect_editor_widget`/`derive_accepted_name_lookup_table`) — **this is the expected, correct state
for acceptance tests written ahead of their implementation, not a defect in the tests themselves.**

## Shared-fixture-default housekeeping addendum (later, separate `test-designer` round; Decision
## Log D-70 Option (c), the mechanical follow-up the AC-QPB-109 addendum above explicitly deferred)

This section records a **third, later `test-designer` invocation**, narrowly scoped (per the
orchestrator's own task framing) to the mechanical shared-fixture-default housekeeping Decision
Log D-70 itself confirmed as the only remaining open item ("this is `test-designer`/`implementer`
housekeeping work for a future round"). It does not reopen or revise anything above, including the
`AC-QPB-109` addendum's own content.

**What was changed:** `tests/acceptance/qfield_project_builder/conftest.py`'s `make_base_config()`
now includes a default `_test_reference_data_dir` override, `str(REFERENCE_DATA_VALID_SAMPLE_DIR)`,
in the config dict it returns for every survey type. `built_project_by_type()`/
`isolated_project_by_type()` needed no direct edit — both call `make_base_config()` internally, so
they inherit the new default automatically. See `conftest.py`'s own `make_base_config()` docstring
and its comment above the `REFERENCE_DATA_VALID_SAMPLE_DIR` constant for the full, in-file record
of this change, and `HARNESS_CONTRACT.md`'s matching "Addendum (Decision Log D-70...)" note
(appended immediately after its own pre-existing "Flagged interaction..." section) for the
identical report.

**Verification performed:** the full acceptance suite (`pytest tests/acceptance/qfield_project_builder
-q`, 448 tests) was run once immediately before this change and once immediately after, on the same
machine (which happens to have the real, gitignored `storage/reference/` scaffold present).
Before: 392 passed, 21 failed, 35 skipped — all 21 failures in this file (`test_ktsn_lookup_table.py`),
the expected pre-implementation red state the `AC-QPB-109` addendum above already documents. After:
391 passed, 22 failed, 35 skipped — the same 21 pre-existing failures, unchanged, plus exactly one
newly failing test, `test_post_mvp_reference_bundling.py::
test_ac071_full_real_reference_dataset_extraction_and_raster_bundling`. No other test's outcome
changed in either direction.

**The one newly failing test, explained (a known, understood interaction — not silently patched):**
that test's own local `_build_with_identification` helper (in `test_post_mvp_reference_bundling.py`,
distinct from and predating this round) deliberately calls `make_base_config("simple_inventory")`
with no `reference_data_dir` argument, specifically so `_test_reference_data_dir` is left completely
unset and `build_project()` falls through to the real, full production `REFERENCE_DATA_DIR` — this
is the one test in the whole suite that proves the true, complete, real-world 212,397 -> 20,914
row-count transformation against the real ~183 MB source CSV, guarded by `real_ktsn_csv_path`/
`real_probability_raster_dir`/`real_nibr_xlsx_path` (which skip this test entirely when the real,
gitignored data is absent). Because `make_base_config()` now always sets
`_test_reference_data_dir`, this helper's "no argument passed -> no override configured" assumption
no longer holds; the key is always present now (pointing at the small `REFERENCE_DATA_VALID_SAMPLE_DIR`
sample), so this test's `assert len(lookup_rows) == 20_914` now fails against the sample's few rows.
This is a fully diagnosed, single-point, expected consequence of this round's own change, not an
unrelated or silent regression. Per this round's own explicit scope (shared fixture defaults only,
not per-test files/assertions), this is **reported here as an open item for a future round**, not
resolved by editing `test_post_mvp_reference_bundling.py` itself — a future round should decide
whether to have that one local helper explicitly reset `config["_test_reference_data_dir"] = None`
when no override argument is given (restoring its original behavior, since `build_project()`'s own
`_resolve_reference_data_dir()` already treats a falsy override the same as an absent one), or
whether some other resolution is preferred.

**No other ambiguity found.** Every other `make_base_config()`/`built_project_by_type`/
`isolated_project_by_type` consumer checked across the suite either (a) already passes its own
explicit `_test_reference_data_dir` override (this file's own tests; every `FR-QPB-105`/`AC-QPB-071`/
`AC-QPB-083` test in `test_post_mvp_reference_bundling.py` other than `test_ac071_...` itself; every
`identification_enabled=True` test in `test_post_mvp_identification_plugin.py`/
`test_post_mvp_plantnet_key_embedding.py`, which build successfully either way and assert nothing
about reference-data row counts/content, so redirecting them to the small sample changes nothing
observable), or (b) does not depend on reference-data content at all (the large majority of the
suite — basemap, naming, transfer/validation, runtime-detection, symbol-styling, Korean-field-alias,
GeoPackage/QGIS-project-config tests, etc.), matching the full-suite comparison's own result of
exactly one changed outcome.
