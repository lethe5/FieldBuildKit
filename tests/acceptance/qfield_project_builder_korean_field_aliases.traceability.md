# Traceability Matrix — QField Project Builder, Korean Field Aliases (Decision Log D-56/D-57/D-58)

> Specification: `specs/qfield-project-builder.md` — new `DR-QPB-071` (Section 7), new
> `FR-QPB-119` (Section 9, plus its additive cross-reference from `FR-QPB-057`), new Section 8.5
> (the full, per-survey-type Korean field-alias table), and new `AC-QPB-098` (Section 18.2) — all
> from Decision Log **D-56** (proposed the mapping, in response to the stakeholder's verbatim
> instruction "Add Korean aliases to the fields in the form"), **D-57** (confirmed all ten
> originally-flagged Medium-confidence terms verbatim, closing Open Question O-22), and **D-58**
> (confirmed the one remaining open sub-question — whether the Type-3 `plot_id` foreign-key label
> should also carry the "고정" prefix used by `plot.plot_name`'s own alias — verbatim: **"'고정'
> added there too"**).
>
> This is a later `test-designer` round against the same overall specification as
> [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md) (the approved
> MVP baseline). It is recorded as its own file, not merged into the MVP file, so the
> already-approved MVP traceability record is not touched by this round's additions — see
> `tests/acceptance/README.md` for the pointer between all of this repository's traceability
> files.
>
> Tests: `tests/acceptance/qfield_project_builder/test_korean_field_aliases.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s new
> "Decision Log D-56/D-57/D-58" section (function 12, `inspect_field_aliases`).
> Shared per-survey-type/per-table Korean-alias data: `KOREAN_FIELD_ALIASES` in
> `tests/acceptance/qfield_project_builder/conftest.py` (mirrors the existing
> `SURVEY_TYPE_SCHEMAS` convention already used by the MVP round).
>
> **Corrected by a later `test-designer` round (2026-08-26; Decision Log D-59)** — see the
> "Correction record (Decision Log D-59)" section near the end of this file for exactly what
> changed in this file, in `HARNESS_CONTRACT.md`, in `conftest.py`, and in
> `test_korean_field_aliases.py`, and why.
>
> **Extended by a later `test-designer` round (2026-08-28; Decision Log D-74/D-78)** — Type 2/3's
> `observation_photo` table is removed entirely, replaced by three new photo-path columns on
> `observation` itself, reusing Type 1's own already-confirmed aliases verbatim. See the
> "Correction record (Decision Log D-74)" section near the end of this file for the coverage-count
> changes this made to `KOREAN_FIELD_ALIASES` (`conftest.py`) and this file's own "Coverage detail"
> section below; the primary new/revised test coverage for this round lives in the dedicated
> `qfield_project_builder_observation_photo_removal.traceability.md` file (AC-QPB-112/113/114),
> not in this file — this file only records the Korean-alias-table side effect of that change.

## A note on why this round could proceed at all (read before the "Ambiguities" section)

`DR-QPB-071`, `FR-QPB-119`, and `AC-QPB-098`'s own inline requirement text each still read,
verbatim, "**draft proposal, not yet stakeholder-approved**" — and `AC-QPB-098`'s text goes
further, saying it is "**not to be exercised by any `test-designer`/`implementer` work until
Section 8.5's proposed aliases are stakeholder-confirmed**." Taken in isolation, that wording
would normally be a hard stop under this project's own ambiguity-handling procedure.

It is not a stop here, because Decision Log **D-57**'s own "Approval status" line (Section 19,
immediately under Decision Log D-56) is explicit that this exact situation is expected and
already resolved: *"Per this project's change-control discipline, `test-designer`/`implementer`
work may now proceed against DR-QPB-071/FR-QPB-119/Section 8.5/AC-QPB-098, per Decision Log
D-57/D-58's confirmation; Open Question O-22 is closed."* Decision Log D-57's own "What this does
not change" paragraph additionally confirms, explicitly, that this textual staleness is
intentional and known: *"DR-QPB-071/FR-QPB-119's own requirement text is unaffected in substance
... only Section 8.5's per-field confidence/status markers and D-56's approval-status line
change."* Decision Log D-58 repeats the identical framing for its own, narrower confirmation.
Section 8.5's own header banner independently confirms the same conclusion: *"FULLY CONFIRMED by
the stakeholder (Decision Log D-57/D-58) ... No exception remains."*

In other words: the specification's authors deliberately left the requirement-ID-level "draft,
not yet approved" sentences untouched (as a historical record of what the text said when
originally proposed, per this specification's own consistent non-destructive-revision
convention — see, e.g., how Decision Log D-8/D-13 entries are handled), while using the Decision
Log's own explicit "Approval status" line as the actual, current, load-bearing gate. This
test-designer round reads both together, per the specification's own documented convention, and
treats the gate as open — not as an invented resolution of a genuine ambiguity. This is recorded
here, explicitly, rather than silently assumed, exactly because it could otherwise look like this
round overstepped a "do not proceed" instruction still literally present in three requirement
IDs' own body text.

## Traceability table

| AC ID / FR ID / DR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-098 (positive half) — every in-scope field carries its exact, confirmed Korean alias | Given a generated project for any of the four survey types, every attribute field on every layer except a table's own UUID primary key has a non-empty Korean-language alias matching Section 8.5's confirmed mapping, not the raw column name | `test_korean_field_aliases.py::test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias` (parametrized: 73 cases — every in-scope field, every table, all 4 survey types; see "Coverage detail" below) | auto |
| AC-QPB-098 (negative half) — a table's own UUID primary key carries no alias | Given the same layers, a table's own UUID primary-key field specifically has no alias set | `test_korean_field_aliases.py::test_ac098_uuid_primary_key_field_has_no_alias_set` (parametrized: 15 cases — one per table, all 4 survey types) | auto |
| AC-QPB-098 (completeness cross-check) — no field silently escapes any of the three expectations above | Every field QGIS actually reports for a layer is accounted for by exactly one of three expectations: the table's own UUID primary key (no alias), an in-scope Section 8.5 field (its confirmed alias), or the GeoPackage physical primary key `fid` (present, no alias, out of scope entirely — Decision Log D-59); no unexpected fourth field is present, and none of the expected fields is silently absent | `test_korean_field_aliases.py::test_every_layer_field_is_accounted_for_by_exactly_one_alias_expectation` (parametrized: 15 cases — one per table, all 4 survey types) | auto |
| DR-QPB-071 | The scoping rule itself (UUID-PK role excluded; UUID-FK role in scope; geometry columns never `ColumnDef`s/never members of `layer.fields()`, never aliased; `fid` a genuine member of `layer.fields()` but likewise never aliased, for a separate reason — Decision Log D-59) | Demonstrated jointly by all three tests above: the positive test explicitly includes every UUID *foreign-key* field (e.g. `temporary_plots.survey.site_id` → 사이트, `permanent_plots.observation.survey_id` → 조사) as an in-scope, aliased field, not merely non-PK data fields; the negative test targets exactly the UUID *primary-key* field per table; no test anywhere in this round attempts to assert an alias for a geometry column (`geom`/`site_geom`/`plot_geom`/`community_geom`), consistent with Section 8.5's own statement that geometry columns are never members of `layer.fields()` at all; and the completeness test explicitly asserts `fid` **is** present in `layer.fields()` for every table, with no alias, as its own third, distinct category (corrected by Decision Log D-59; see this file's correction-record section below) | auto (no dedicated test needed beyond the above — this is a structural/scoping rule, not an independently observable behavior beyond what the three tests above already show) |
| FR-QPB-119 | The build pipeline must set every in-scope alias via `QgsVectorLayer.setFieldAlias` (mechanism), for every layer of the generated project | Same three tests above — `inspect_field_aliases` reads back exactly the value `QgsField.alias()` reports, which is only ever populated by a prior `setFieldAlias` call (see HARNESS_CONTRACT.md function 12's own rationale for why `attributeDisplayName()` is deliberately not used) | auto |

## Coverage detail (per survey type / table)

~~Every table listed in Section 8's per-survey-type schema is covered — 15 tables total across the
four survey types:~~ **(superseded by Decision Log D-74, 2026-08-28 — see the "Correction record
(Decision Log D-74)" section near the end of this file; 13 tables total, not 15, now that
`observation_photo` no longer exists for Type 2/3)**:

- **Type 1 (`simple_inventory`)**: `inventory_observation` (14 in-scope fields aliased;
  `inventory_id` excluded). Unaffected by Decision Log D-74.
- **Type 2 (`temporary_plots`)**: `site` (1), `survey` (4), `observation` (~~11~~ **14, Decision
  Log D-74 — gains `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path`**), `survey_photo`
  (4)~~, `observation_photo` (4)~~ **(removed entirely, Decision Log D-74)** — ~~24~~ **23**
  in-scope fields aliased across ~~5~~ **4** tables; ~~5~~ **4** UUID primary keys excluded.
- **Type 3 (`permanent_plots`)**: `site` (1), `plot` (3), `survey` (3), `observation` (~~11~~
  **14**, same fields as Type 2's `observation`), `plot_photo` (4)~~, `observation_photo` (4, same
  fields as Type 2's `observation_photo`)~~ **(removed entirely, Decision Log D-74)** — ~~26~~
  **25** in-scope fields aliased across ~~6~~ **5** tables; ~~6~~ **5** UUID primary keys excluded.
  This is the table containing the two Decision-Log-D-58-confirmed `plot_id` foreign-key labels
  (`survey.plot_id`, `plot_photo.plot_id`, both → 고정조사구).
- **Type 4 (`vegetation_mapping`)**: `site` (1), `survey` (3), `community` (5) — 9 in-scope fields
  aliased across 3 tables; 3 UUID primary keys excluded. Unaffected by Decision Log D-74.

~~Total: 73 in-scope-field alias assertions (`test_ac098_in_scope_field_has_the_exact_confirmed_
korean_alias`'s 73 parametrized cases) + 15 UUID-primary-key no-alias assertions
(`test_ac098_uuid_primary_key_field_has_no_alias_set`'s 15 parametrized cases) + 15 completeness
cross-checks (`test_every_layer_field_is_accounted_for_by_exactly_one_alias_expectation`'s 15
parametrized cases) = 103 total parametrized test invocations, confirmed collected by an actual
`pytest --collect-only` run performed during this round.~~

**Superseded by Decision Log D-74 (2026-08-28):** Total: **71** in-scope-field alias assertions
(`test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias`'s 71 parametrized cases, down
from 73 — net -2: -4 for each removed `observation_photo` table's own aliased-field count [-8
total], +3 for each of Type 2/3's newly-aliased `observation` photo-path fields [+6 total]) + **13**
UUID-primary-key no-alias assertions (down from 15, one fewer per survey type for Type 2/3 now
that `observation_photo`'s own UUID primary key no longer exists) + **13** completeness
cross-checks (down from 15, the same one-fewer-table-per-Type-2/3 reason) = **97** total
parametrized test invocations (down from 103), confirmed collected by an actual
`pytest --collect-only` run performed during this round
(`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_korean_field_aliases.py
--collect-only -q` reports "97 tests collected").

**Confirmed by an actual test run performed during the original (D-56/D-57/D-58) round:** all 103
parametrized invocations then in existence **SKIP**ped (not fail/error), each with the reason
`qfield_builder.acceptance_api.inspect_field_aliases() is not implemented yet`, exactly as
expected for a harness function that round introduces but does not itself implement — mirroring
this project's own established "not implemented yet -> skip, never a hard failure" convention
(see `HARNESS_CONTRACT.md`'s own framing, and the existing `_require_harness_function` helper in
`conftest.py`, which that round's `inspect_field_aliases` fixture reuses unchanged in mechanism).

**Confirmed by an actual test run performed during this later (Decision Log D-74) round**
(`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_korean_field_aliases.py
-q`, run against the current, not-yet-updated `qfield_builder/korean_field_aliases.py`/
`qfield_builder/schemas.py`, since `qfield_builder.acceptance_api.inspect_field_aliases` is now a
real, working implementation as of this later round, unlike the original round above): **89
passed, 8 failed** — the 8 failures are exactly `test_ac098_in_scope_field_has_the_exact_confirmed_
korean_alias[temporary_plots-observation-leaf_photo_path]` (and its `flower_photo_path`/
`fruit_photo_path`/`permanent_plots` siblings, 6 cases total) plus
`test_every_layer_field_is_accounted_for_by_exactly_one_alias_expectation[temporary_plots-
observation]`/`[permanent_plots-observation]` (2 cases), all failing because `observation` does
not yet have the three new photo-path columns at all in the current, not-yet-updated schema — the
correct, expected red state for a not-yet-implemented change. No other, previously-passing case in
this file regressed.

## Notes on automation approach

1. **Why a dedicated PyQGIS-backed harness function (`inspect_field_aliases`) rather than a raw
   `.qgs` XML regex, unlike AC-QPB-013's `RelationReference` check.** QGIS project XML does have a
   well-known, long-standing per-layer `<aliases>`/`<alias field="..." name="..." index="N"/>`
   block, and hardcoding a regex against it directly (mirroring
   `test_qgis_project_config.py::test_ac013_foreign_key_field_uses_relation_reference_widget`) was
   considered. It was not done, because — unlike `"RelationReference"`, a string this codebase's
   own already-working `qgis_worker.py` independently confirms is correct — the exact `<aliases>`
   XML shape was not independently confirmed against a live QGIS instance during this round, and
   this project's hard QGIS-isolation rule bars the test-designer from constructing a
   `QgsApplication` for any verification purpose, including this one. The judgment is delegated
   instead to a real-PyQGIS-backed harness function, mirroring the established precedent
   `inspect_identification_widget` already set for exactly this situation (see
   `qfield_project_builder_post_mvp_identification.traceability.md`'s note 1, and
   `HARNESS_CONTRACT.md` function 10's own "Exact editor-widget-type-string note"). See
   `HARNESS_CONTRACT.md`'s new "Decision Log D-56/D-57/D-58" section for the full rationale,
   including why `QgsField.alias()` must be used rather than
   `QgsVectorLayer.attributeDisplayName()` (the latter's fallback-to-field-name behavior would make
   an intentionally-unset alias indistinguishable from a coincidentally-identical one, defeating
   AC-QPB-098's own negative assertion).
2. **AC-QPB-098's own "remains configured `Hidden`/read-only exactly as before ... unchanged by
   this criterion" clause is not re-tested here.** That half of the criterion restates an
   already-approved, already-tested MVP behavior (DR-QPB-005/FR-QPB-057), already covered by
   `test_qgis_project_config.py::test_ac012_uuid_field_is_autogenerated_and_not_normally_editable`.
   Duplicating that assertion in this file would test the same underlying mechanism twice under
   two different test names for no added coverage; this round's own three tests cover only the
   genuinely new half of AC-QPB-098 (the alias presence/absence itself).
3. **The completeness cross-check (`test_every_layer_field_is_accounted_for_by_exactly_one_alias_
   expectation`) exists specifically to make AC-QPB-098's own "every field ... except" wording
   fully covered, not merely covered for the specific fields this round happened to enumerate.**
   Without it, a future schema change that silently added a new column to, say, `community`
   without updating `KOREAN_FIELD_ALIASES` in `conftest.py` would leave that new column completely
   unchecked by either of the other two tests — neither asserting it has an alias, nor asserting it
   doesn't — which would under-cover the criterion's own "every field" wording without any test
   actually failing to say so. This test closes that gap by asserting the *complete* field set
   returned by `inspect_field_aliases` for each table equals exactly the union of "the UUID
   primary key," "Section 8.5's listed in-scope fields," **and the GeoPackage physical primary key
   `fid` (Decision Log D-59 — see this file's correction-record section below for why `fid` is a
   third, distinct category here, not folded into either of the other two)**, so any drift between
   the schema and this round's own `KOREAN_FIELD_ALIASES` data is caught as a test failure rather
   than silently passing by omission.
4. **`built_project_by_type`'s default `identification_enabled=False` build is sufficient for
   every field this round tests, including the reserved, inactive-until-post-MVP columns.**
   `selected_ktsn`, `identification_score`, `occurrence_probability`, `identification_timestamp`,
   and `identification_model_version` are part of every relevant table's schema regardless of
   whether the post-MVP identification subsystem is enabled (DR-QPB-034/052/053's own "must remain
   nullable and inactive in the MVP build" wording describes the *columns'* runtime behavior, not
   a condition on whether the columns exist at all) — the pre-existing
   `test_type1_layer_has_exactly_three_relation_free_photo_fields` in
   `test_geopackage_schema_by_type.py` already relies on this same fact for a sibling set of
   columns using the same default fixture. No test in this round needed to pass
   `identification_enabled=True` or any other non-default `build_project()` config.
5. **A shared helper's skip-message was corrected, not just reused, as a minor, in-scope accuracy
   fix.** The pre-existing `_require_harness_function` helper in `conftest.py` (used by every
   `_require_harness_function`-based fixture, including this round's new `inspect_field_aliases`
   fixture) had its skip message hardcoded to always cite HARNESS_CONTRACT.md's "Post-MVP: Section
   13" section, regardless of which function was actually missing. That was accurate for every
   fixture that existed before this round, but not for `inspect_field_aliases`, whose documenting
   section is new and unrelated to Section 13. The message was generalized to no longer name a
   specific (now sometimes wrong) section, and was confirmed, by an actual test run performed
   during this round, to still produce the same skip (not fail/error) behavior for every
   pre-existing `_require_harness_function`-based fixture used elsewhere in this suite (`match_ktsn`,
   `build_plantnet_identify_request`, `call_plantnet_identify`, `inspect_identification_widget`,
   `run_ktsn_reference_pipeline`) — this is a wording-only change with no behavioral effect on any
   pre-existing test.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **No genuine field-mapping ambiguity found.** Every one of Section 8.5's originally-Medium-
  confidence terms (ten items, per Open Question O-22) was explicitly confirmed verbatim by the
  stakeholder (Decision Log D-57), and the one remaining open sub-question (the Type-3 `plot_id`
  foreign-key label's "고정" prefix) was likewise explicitly confirmed verbatim (Decision Log
  D-58). Section 8.5's own closing line — "No field below remains at Medium confidence or
  otherwise unconfirmed" — is taken at face value; this round did not independently second-guess
  any of the confirmed Korean text itself (that is a domain-expert/stakeholder judgment call, not
  a test-design judgment call), only transcribed it exactly as written in Section 8.5 into
  `KOREAN_FIELD_ALIASES`.
- **The requirement-ID-level "draft, not yet stakeholder-approved" wording still present in
  DR-QPB-071/FR-QPB-119/AC-QPB-098's own body text is not treated as a blocking ambiguity** — see
  "A note on why this round could proceed at all" above for the full reasoning (Decision Log
  D-57's own explicit "Approval status" line authorizes proceeding). This is disclosed here,
  rather than silently proceeding without comment, precisely because it could otherwise look like
  an overstepped "do not proceed" instruction.
- **Value-level translation of enumerated fields (e.g. `identification_status`'s
  `not_requested`/`pending`/`complete`/`failed`/`manual`, `organ`'s
  `leaf`/`flower`/`fruit`/`bark`/`auto`) is explicitly out of scope, per Section 8.5's own text**
  ("This proposal does **not** address translating the *values* of enumerated/status fields ...
  only the field *label* (alias) itself"). No test in this round asserts anything about a
  `ValueMap`'s displayed *value* text — only the field's own alias (label). This is a
  specification-stated scope boundary, not a gap this round left uncovered by oversight.

## Correction record (Decision Log D-59)

A round of this same acceptance-test suite, prior to this entry, was built on an incorrect
technical claim — traced back to the approved specification text itself at the time — that the
GeoPackage physical primary-key field `fid` is never a member of a real generated layer's
`layer.fields()`, the same way geometry columns genuinely are never members of it. Specification
Decision Log **D-59** (`specs/qfield-project-builder.md`, Section 19) corrects this: `fid` *is* a
genuine member of `layer.fields()` for every generated GeoPackage layer (it is a real physical
column, per the OGC GeoPackage specification's own required named integer primary key); it simply
receives no Korean alias, for a different reason than geometry columns' omission — it is a
non-domain physical key, already excluded from the *visible* attribute-editor form tree by the
pre-existing, unrelated `_build_drag_and_drop_form` mechanism in `qfield_builder/qgis_worker.py`
(unaffected by any of this).

This is a Category B correction of the specification's/this test suite's own prior reasoning, not
a stakeholder product decision and not a conformance defect in `qfield_builder/` — D-59 itself
confirms the already-implemented `fid`-exclusion-from-the-visible-form behavior is correct and
unaffected. Reconciling it against this round's own test artifacts was a corresponding
`test-designer` round's own responsibility (D-59's own "what remains out of scope for this entry"
paragraph), performed here, 2026-08-26:

- **`HARNESS_CONTRACT.md`** (function 12, `inspect_field_aliases`): corrected the return-value
  description for `field_names` — geometry columns remain correctly described as absent from
  `layer.fields()`; `fid` is now correctly described as present in `layer.fields()`, with no
  alias, for the separate reason above. A corrective note was also added to this section's own
  intro banner for discoverability.
- **`conftest.py`**: corrected the comment block immediately above `KOREAN_FIELD_ALIASES` the same
  way, and added a new module-level `FID_PHYSICAL_KEY_FIELD = "fid"` constant. `fid` was not added
  as a new key inside any table's own `aliases`/`uuid_pk` entries in `KOREAN_FIELD_ALIASES` itself,
  because it is the same single fixed name for every table (unlike `uuid_pk`, which differs per
  table) and Section 8.5 never proposed an alias for it in the first place (unlike the entries in
  `aliases`) — representing it once, as a shared constant that tests union in explicitly wherever
  they need the layer's *complete* field set, was judged the cleanest fix that does not conflate
  "a field with a confirmed Korean alias" with "a field this proposal simply never covers."
- **`test_korean_field_aliases.py`**: corrected
  `test_every_layer_field_is_accounted_for_by_exactly_one_alias_expectation` to union
  `FID_PHYSICAL_KEY_FIELD` into its `expected_fields` set (previously only `table_info["aliases"]`
  and `table_info["uuid_pk"]`), and added a direct assertion that `fid`'s own reported alias is
  empty — so the test continues to actually verify "no alias," not merely "this name is allowed to
  be present," preserving the substance of what this completeness check exists to catch. The
  module docstring and the test's own docstring were both updated to explain `fid` as a third,
  distinct field category, and to record the concrete `extra=['fid']` failure this correction
  resolves. No other test in this file was touched: the 73
  `test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias` cases and the 15
  `test_ac098_uuid_primary_key_field_has_no_alias_set` cases never made any claim about `fid` and
  needed no change.
- **This traceability file**: corrected the completeness-cross-check and DR-QPB-071 table rows,
  and the matching "Notes on automation approach" item, to describe three field categories instead
  of two and to no longer claim `fid` is absent from `layer.fields()`.

**Verification performed by this round.** Per this project's hard QGIS-isolation rule, the
test-designer cannot construct a `QgsApplication` or invoke a QGIS binary for any purpose,
including authoring-support verification of a `qgis`-marked test — so the corrected test was not,
and could not be, executed end-to-end against a real generated project by this round. What *was*
verified: `python -m pytest tests/acceptance/qfield_project_builder/test_korean_field_aliases.py
--collect-only -q` (collection only, no QGIS invocation) still collects the same 103 parametrized
cases with no errors, confirming the edit is syntactically and structurally sound. Per the task
that authorized this correction, the corrected test is expected to pass once actually run against
the current, unmodified `qfield_builder/` implementation, since that implementation's `fid`-no-alias
behavior was already independently confirmed correct — this round changed only the test's
accounting of `fid`'s *presence*, not any expectation about its alias content, and not any
application code.

**No other incorrect assumption was found** in this file, `HARNESS_CONTRACT.md`,
`conftest.py`, or `test_korean_field_aliases.py` while performing this correction — the search was
scoped to every place each file mentions `fid` or geometry-column exclusion from `layer.fields()`,
per the task's explicit instruction to flag rather than silently fix anything else found stale.

## Correction record (Decision Log D-74/D-78, 2026-08-28)

Unlike Decision Log D-59's correction above (which fixed this file's/this suite's own incorrect
prior *reasoning* about `fid`), this round reflects a genuine, stakeholder-approved **schema
change**, not a correction of a prior mistake: Decision Log D-74 removes Type 2/3's
`observation_photo` table entirely (and its relation, `rel_observation_photo_observation`),
replacing it with three new, optional, nullable, relation-free photo-path columns directly on
`observation` — `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` — reusing Type 1's own
already-confirmed aliases verbatim (Section 8.5's Type 2 table, DR-QPB-077). Decision Log D-78
separately confirms this applies only to newly generated projects going forward — no migration/
backward-compatibility handling is required or tested anywhere in this suite.

**This round's primary new/revised acceptance-test coverage (AC-QPB-112/113/114, and AC-QPB-009's
narrowing) lives in a new, dedicated file, not in this one** — see
`qfield_project_builder_observation_photo_removal.traceability.md`. This file only needed updating
because its own tests are entirely data-driven off `KOREAN_FIELD_ALIASES` in `conftest.py`, which
that new round's own schema change required updating (the three new fields' aliases did not
previously exist anywhere in that dict, and `observation_photo`'s own table entries needed
removing since that table itself no longer exists) — updating that shared fixture automatically
extends/retracts this file's own already-existing, data-driven test coverage with no new test
function needed in `test_korean_field_aliases.py` itself.

- **`conftest.py`**: `_TYPE2_3_OBSERVATION_ALIASES` gained `leaf_photo_path`/`flower_photo_path`/
  `fruit_photo_path` (잎 사진/꽃 사진/열매 사진, identical to Type 1's `inventory_observation`
  entry). The `temporary_plots`/`permanent_plots` entries of `KOREAN_FIELD_ALIASES` had their own
  `observation_photo` table entry removed entirely (not struck through — this is executable test
  data, not specification prose), along with the now-unused `_OBSERVATION_PHOTO_ALIASES` module
  constant it referenced. `SURVEY_TYPE_SCHEMAS`'s own `temporary_plots`/`permanent_plots` entries
  were likewise updated in the same round (removing `observation_photo`'s table/relation entries),
  since that dict is consumed by other test files (`test_geopackage_common.py`,
  `test_geopackage_schema_by_type.py`) that this correction record does not otherwise touch.
- **`test_korean_field_aliases.py`**: no test function was added, removed, or edited. Every test
  in this file is already fully data-driven off `KOREAN_FIELD_ALIASES`
  (`_in_scope_field_cases()`/`_uuid_pk_cases()`/`_table_cases()`, all called once at module import
  time) — the `conftest.py` change above automatically added 6 new
  `test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias` parametrized cases (3 fields ×
  2 survey types) and automatically removed the 8 `observation_photo`-table-scoped cases that
  previously existed across all three parametrized test functions (4 in-scope-field cases ×
  2 survey types = 8 for the positive test alone; 1 UUID-pk case × 2 survey types = 2 for the
  negative test; 1 table case × 2 survey types = 2 for the completeness test), with no code change
  needed in this file itself.
- **This traceability file**: the "Coverage detail" section's per-table counts and grand totals
  were updated in place (struck through, not deleted, per this project's own non-destructive
  convention) to reflect 13 tables (not 15), 71 in-scope-field cases (not 73), 13 UUID-pk cases
  (not 15), 13 completeness cases (not 15), 97 total parametrized invocations (not 103).

**Verification performed by this round.** Per this project's hard QGIS-isolation rule, the
test-designer cannot construct a `QgsApplication` or invoke a QGIS binary directly for any
diagnostic purpose — but running the acceptance suite itself through its own existing, isolated
`qfield_builder.qgis_bridge`-backed harness (exactly what every other round of this suite already
does via `pytest`) is the sanctioned way to execute a `qgis`-marked test, and was used here:
`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_korean_field_aliases.py
-q` was actually run against the current, real, not-yet-updated `qfield_builder/` implementation
(unlike Decision Log D-59's correction above, which predates a working `inspect_field_aliases`
implementation and could only confirm collection). Result: **89 passed, 8 failed** — exactly the
8 cases named in this file's "Coverage detail" section above (6 new-field alias assertions plus 2
completeness cross-checks for `observation`, both survey types), all failing because the three new
photo-path columns do not yet exist on `observation` in the current, not-yet-updated
`qfield_builder/schemas.py`. No other, previously-passing case in this file regressed — confirming
this round's `conftest.py` edit is behavior-neutral for every field/table this round did not touch.

**No other incorrect assumption was found** in this file, `HARNESS_CONTRACT.md`, `conftest.py`, or
`test_korean_field_aliases.py` while performing this update — the search was scoped to every place
each file mentions `observation_photo` or `observation`'s own photo-path fields, per the task's
explicit instruction to flag rather than silently fix anything else found stale.
