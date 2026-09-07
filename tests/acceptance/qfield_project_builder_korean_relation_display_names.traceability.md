# Traceability Matrix — QField Project Builder, Korean Relation-Widget Display Names (Decision Log D-73/D-77)

> Specification: `specs/qfield-project-builder.md` — new `FR-QPB-128` (Section 9) and new
> `AC-QPB-111` (Section 18.2), from Decision Log **D-73** (investigated the gap and proposed the
> mapping, in response to the stakeholder's verbatim report **"Widget에 relation을 추가할 때
> rel_observation_survey와 같은 이름으로 추가하지 말고 적절한 한국어 alias를 적용할 것"** — "When
> adding a relation to a widget, don't add it with a name like 'rel_observation_survey' — apply an
> appropriate Korean alias instead") and **D-77** (confirmed six of the seven proposed names
> exactly as proposed and corrected the seventh, `rel_observation_survey`: "관찰" → "식물관찰",
> closing Open Question O-36). New Section 8.6 (Section 8) records the confirmed, per-relation
> Korean display-name table this round tests against.
>
> This is a later `test-designer` round against the same overall specification as
> [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md) (the approved
> MVP baseline). It is recorded as its own file, not merged into the MVP file or into
> [`qfield_project_builder_korean_field_aliases.traceability.md`](qfield_project_builder_korean_field_aliases.traceability.md)
> (a related but textually distinct requirement — an ordinary attribute-*field* alias, not a
> relation's own display name), so neither already-approved traceability record is touched by this
> round's additions — see `tests/acceptance/README.md` for the pointer between all of this
> repository's traceability files.
>
> Tests: `tests/acceptance/qfield_project_builder/test_korean_relation_display_names.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s new
> "Decision Log D-73/D-77" section (function 18, `inspect_relations`).
> Shared per-relation Korean-display-name data: `KOREAN_RELATION_DISPLAY_NAMES` in
> `tests/acceptance/qfield_project_builder/conftest.py` (mirrors the existing
> `KOREAN_FIELD_ALIASES`/`SURVEY_TYPE_SCHEMAS` convention already used by earlier rounds).

## Why this round could proceed without a blocking-ambiguity note

Unlike the earlier Decision Log D-56/D-57/D-58 Korean field-alias round — whose `DR-QPB-071`/
`FR-QPB-119`/`AC-QPB-098` own inline requirement text was left textually unedited, still literally
reading "draft proposal, not yet stakeholder-approved," requiring that earlier round's traceability
file to carry an explicit "why this round could proceed at all" note — **`FR-QPB-128` and
`AC-QPB-111`'s own body text was itself directly updated in place by Decision Log D-77**: each now
reads, verbatim, "~~draft proposal, not yet stakeholder-approved...~~ **confirmed by Decision Log
D-77 — Section 8.6's proposed relation display names are now stakeholder-confirmed (six as
proposed, one corrected); `test-designer`/`implementer` work may now proceed against this
requirement**." No separate reconciliation of stale wording is required here; the confirmation is
already live in both requirement IDs' own current text.

## Traceability table

| AC ID / FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-111 | Given a generated project for any survey type, when each embedded child-relation widget's underlying `QgsRelation` is inspected, then its `id()` is unchanged from the existing stable relation-ID convention (FR-QPB-056) and its `name()` is the corresponding Section 8.6-confirmed Korean display name — never the raw relation-ID string | `test_korean_relation_display_names.py::test_ac111_relation_id_is_unchanged_and_name_is_the_confirmed_korean_display_name` (parametrized: 9 cases — every one of the seven Section 8.6 relations, once per survey type it actually applies to; see "Coverage detail" below) | auto |
| AC-QPB-111 (disclosed rendering-mechanism caveat, explicitly out of this criterion's own scope, Decision Log D-73/D-77) | Whether `QgsRelation.name()` is actually the mechanism QGIS Desktop/QField use to paint the embedded widget's on-screen label, as opposed to some other, not-yet-identified override | `test_korean_relation_display_names.py::test_ac111_embedded_widget_actually_renders_the_configured_korean_name_on_screen` | `manual`/`device` (skip placeholder — not automatable by this harness; see the test's own skip reason for the manual QA steps) |
| FR-QPB-128 | The relation's own stable ID (`QgsRelation.setId()`) must remain completely unchanged; only the relation's separate, human-facing display name (`QgsRelation.setName()`) is affected, and it must be the Section 8.6-confirmed Korean text for that relation | Same parametrized test above — both the `relation_id in info["relation_ids"]` regression guard (id-unchanged half) and the `actual_display_name == expected_display_name` / `actual_display_name != relation_id` assertions (name-changed half) are asserted together in the same test, mirroring how AC-QPB-111's own "Given/when/then" text binds both facts into a single criterion | auto |

## Coverage detail (per relation / survey type)

Every one of the seven relations Section 8.6 lists is covered, once per survey type its own
schema actually declares it (confirmed directly against `qfield_builder/schemas.py`'s own
`ForeignKeyDef(relation_id=...)` values by this round — see `KOREAN_RELATION_DISPLAY_NAMES`'s own
comment block in `conftest.py`):

- `rel_survey_site` → **조사** — Type 2 (`temporary_plots`), Type 4 (`vegetation_mapping`): 2 cases.
- `rel_observation_survey` → **식물관찰** (Decision Log D-77 correction; originally proposed
  "관찰") — Type 2 (`temporary_plots`), Type 3 (`permanent_plots`): 2 cases.
- `rel_survey_photo_survey` → **조사 사진** — Type 2 (`temporary_plots`) only: 1 case.
- `rel_plot_site` → **고정조사구** — Type 3 (`permanent_plots`) only: 1 case.
- `rel_survey_plot` → **조사** — Type 3 (`permanent_plots`) only: 1 case.
- `rel_plot_photo_plot` → **고정조사구 사진** — Type 3 (`permanent_plots`) only: 1 case.
- `rel_community_survey` → **군락** — Type 4 (`vegetation_mapping`) only: 1 case.

Total: **9** parametrized invocations of
`test_ac111_relation_id_is_unchanged_and_name_is_the_confirmed_korean_display_name`, confirmed
collected by an actual `pytest --collect-only` run performed during this round (see "Verification
performed by this round" below), plus the one non-parametrized `manual`/`device`-marked skip
placeholder test.

Type 1 (`simple_inventory`) has zero foreign keys/relations at all (Section 8.1; confirmed by
`SURVEY_TYPE_SCHEMAS["simple_inventory"]["relations"] == []` in `conftest.py`, pre-dating this
round) and is therefore correctly absent from every case above — there is nothing for this
requirement to apply to on that survey type.

## Notes on automation approach

1. **Why a dedicated PyQGIS-backed harness function (`inspect_relations`) rather than a raw `.qgs`
   XML regex, unlike AC-QPB-013's `RelationReference` check.** QGIS project XML does have a
   well-known `<relations><relation id="..." name="..." .../></relations>` block, and hardcoding a
   regex against it directly was considered. It was not done, for the same reason
   `inspect_field_aliases` (the Korean field-alias round's own harness function) was not built as a
   raw XML regex either: the exact `<relations>` XML attribute-serialization shape was not
   independently confirmed against a live QGIS instance during this round, and this project's hard
   QGIS-isolation rule bars the test-designer from constructing a `QgsApplication` for any
   verification purpose, including this one. The judgment is delegated instead to a real-PyQGIS-
   backed harness function that reads `QgsRelation.id()`/`QgsRelation.name()` directly off the live
   `QgsRelationManager` — the exact mechanism AC-QPB-111's own text names — mirroring the
   established `inspect_field_aliases`/`inspect_editor_widget` precedent. See
   `HARNESS_CONTRACT.md`'s new "Decision Log D-73/D-77" section for the full rationale.
2. **Both halves of AC-QPB-111 (id-unchanged, name-confirmed) are asserted inside one test
   function, not two, deliberately mirroring the criterion's own single "Given/when/then"
   sentence.** Unlike the Korean field-alias round's positive/negative-test split (which reflects
   two textually separate clauses of AC-QPB-098), AC-QPB-111's own text binds "its `id()` is
   unchanged ... and its `name()` is the corresponding Korean display name" into one criterion
   about one relation at a time — splitting it into two separate test functions here would not add
   coverage, only indirection.
3. **A direct regression-guard assertion (`actual_display_name != relation_id`) is included
   alongside the positive expected-value assertion.** This is not redundant: it directly encodes
   AC-QPB-111's own explicit "never the raw relation ID string" wording, and it is the literal
   condition the current, pre-fix `_add_relations()` violates today (`relation.setName(fk.
   relation_id)`) — so this assertion is what actually fails, with a clear message naming the
   observed raw-ID string, against the current, unmodified codebase (see "Verification performed by
   this round" below).
4. **`rel_observation_photo_observation` is deliberately never mentioned anywhere in this round's
   test file, fixture data, or this traceability file.** Section 8.6/Decision Log D-73 excludes it
   from the Korean-display-name proposal because a separate, related round (Decision Log D-74)
   removes the `observation_photo` table — and therefore this relation — entirely for Type 2/3.
   This round's own direct investigation of `qfield_builder/schemas.py` (performed at two different
   points during this round, given a live, uncommitted, in-progress "macOS release checkpoint"
   phase touching the same files) found the table, and this relation, **already removed** as of
   this round's final check — but this file, `conftest.py`'s `KOREAN_RELATION_DISPLAY_NAMES`, and
   the test file itself make no claim either way about that relation's existence, `id()`, or
   `name()`, precisely so this round's own coverage is correct regardless of exactly when, in this
   repository's ongoing history, that separate round's schema change lands. This is the explicit
   "scope your test suite to only the seven relations Section 8.6 actually lists" option the task
   itself authorized, chosen over the alternative "write one test file robust to either state,"
   since it fully avoids the ambiguity rather than merely tolerating it.
5. **Every project used below is built via the ordinary, default `built_project_by_type` fixture**
   (this suite's existing default, `identification_enabled=False`) — this requirement concerns
   relation configuration, which does not vary with the post-MVP identification-subsystem toggle,
   so no special build configuration was needed.

## Verification performed by this round

Per this project's hard QGIS-isolation rule, the test-designer cannot construct a `QgsApplication`
or invoke a QGIS binary directly for any diagnostic purpose — but running the acceptance suite
itself through its own existing, isolated `qfield_builder.qgis_bridge`-backed harness (exactly what
every other round of this suite already does via `pytest`) is the sanctioned way to execute a
`qgis`-marked test, and was used here.

`ruff check tests` — reported below (see the task's own completion report for the exact command
and output).

`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_korean_relation_display_names.py --collect-only -q`
— confirmed collecting 9 parametrized cases for
`test_ac111_relation_id_is_unchanged_and_name_is_the_confirmed_korean_display_name` plus the one
non-parametrized skip-placeholder test (10 total), with no collection errors.

`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_korean_relation_display_names.py -q`
— run against the current, real `qfield_builder/` implementation, in which
`qfield_builder.acceptance_api` exists and is a real, working implementation for many other
functions, but does **not** yet define `inspect_relations` (function 18, new in this round). Result:
all 9 parametrized cases **SKIP** (not fail/error), each with the reason
`qfield_builder.acceptance_api.inspect_relations() is not implemented yet`, exactly as expected for
a harness function this round introduces but does not itself implement — mirroring this project's
own established "not implemented yet -> skip, never a hard failure" convention (see
`HARNESS_CONTRACT.md`'s own framing, and the pre-existing `_require_harness_function` helper in
`conftest.py`, which this round's `inspect_relations` fixture reuses unchanged in mechanism). The
one `manual`/`device`-marked placeholder test **SKIP**s independently, for its own, unrelated,
always-skipped reason (not automatable by this harness at all), exactly like the existing
`test_ac072_on_device_probability_sampling_while_disconnected_from_desktop`/`test_ac016_opens_in_
every_explicitly_supported_qgis_and_qfield_version` precedents already in this suite.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **No genuine terminology-mapping ambiguity found.** All seven of Section 8.6's proposed relation
  display names were explicitly confirmed by the stakeholder (six exactly as proposed, one
  corrected — Decision Log D-77); this round did not independently second-guess any of the
  confirmed Korean text itself (a domain-expert/stakeholder judgment call, not a test-design
  judgment call), only transcribed it exactly as written in Section 8.6 into
  `KOREAN_RELATION_DISPLAY_NAMES`.
- **The disclosed, not-yet-independently-verified rendering-mechanism caveat (Decision Log
  D-73/D-77) is not an ambiguity this round could resolve, and is not silently treated as settled.**
  AC-QPB-111's own text is explicit that confirming whether `QgsRelation.name()` actually drives the
  widget's on-screen rendered label is "implementer verification work," not a test-design
  determination — this round records it as a `manual`/`device`-marked placeholder test (mirroring
  Decision Log D-36/FR-QPB-111's identical convention) rather than guessing an answer or silently
  omitting coverage of it.
- **Whether `rel_observation_photo_observation` currently exists in `qfield_builder/schemas.py` is
  not settled by this round, and this round takes no position on it either way** — see "Notes on
  automation approach," item 4, above. This is disclosed here explicitly, rather than silently
  assumed, because a less careful reading of Decision Log D-73's exclusion note might have led to
  either (a) asserting the relation is absent (risking a false failure if a separate D-74
  implementer round has not yet landed) or (b) asserting it is present with the pre-existing raw-ID
  name unchanged (risking a false failure once that separate round *does* land and, per its own
  scope, removes the relation entirely) — this round deliberately avoids both traps by never
  mentioning the relation at all.
