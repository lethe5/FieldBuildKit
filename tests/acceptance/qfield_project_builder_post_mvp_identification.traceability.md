# Traceability Matrix — QField Project Builder, Post-MVP Identification Subsystem (Section 13)

## 2026-09-07 D-98 — current candidate-count contract

This section supersedes all fixed-three-result assertions and mappings retained below.
Historical verification results are preserved, not current acceptance requirements.

- FR-QPB-104 / AC-QPB-040: `test_requests_without_a_result_count_limit` checks the Python
  reference request; `test_call_plantnet_identify_requests_include_related_images_true`
  additionally checks the actual helper URL; `test_identification_widget_qml_does_not_request_a_fixed_result_count`
  checks the emitted QML request contains no `nb-results` parameter.
- FR-QPB-101/106/109 / AC-QPB-040: `test_identification_candidates_are_not_truncated_before_or_after_filtering`
  executes the emitted JavaScript handler with mixed candidates, including more than three
  eligible results after an ineligible prefix, and zero/one eligible-result variants.
- `test_plantnet_live_endpoint_authenticates_and_returns_the_confirmed_schema` retains
  schema/score-order checks without a maximum count; it remains network-gated.
- `test_ac040_displayed_candidate_card_order_matches_descending_score` records residual
  physical-QField QA: all eligible cards, including cards beyond the third, are reachable
  and selectable in response order. Offline model checks do not claim device rendering.

> Specification: `specs/qfield-project-builder.md`, Section 13 (Pl@ntNet / KTSN / Occurrence
> Probability), specifically the **guaranteed-manual baseline** slice authorized by Decision Log
> D-31–D-36: FR-QPB-100/101 (project-scoped `.qml` plugin + embedded `QML Widget` action),
> FR-QPB-104 (Pl@ntNet request shape), FR-QPB-105/106/107 (KTSN reference-asset validation, direct
> match, accepted-name resolution), FR-QPB-112 (reference-data bundling), and the acceptance
> criteria this closes: AC-QPB-069, AC-QPB-070, AC-QPB-071, AC-QPB-072 — plus, for completeness,
> the remaining Section 18.6 post-MVP criteria this round's scope touches (AC-QPB-040/041/042/
> 043/044/045/046/049/050).
>
> **2026-08-21 addendum (Decision Log D-47):** FR-QPB-112 is revised, and new FR-QPB-118 and
> AC-QPB-083 are added, to correct a real-device-crash-investigation finding: the KTSN reference
> CSV bundling clause of FR-QPB-112/AC-QPB-071 previously required bundling the complete,
> unmodified 183 MB/212,398-row/~50-column raw CSV into every identification-enabled project; it
> now requires bundling only a build-time-extracted, 5-column `reference/ktsn_lookup.csv` lookup
> file instead. **The probability-raster half of FR-QPB-112/AC-QPB-071 is completely unaffected by
> this addendum** and continues to be tested exactly as before. See the table/notes/ambiguities
> below for the precise, updated mapping; the pre-D-47 text of this addendum's affected rows is not
> deleted, only superseded, per this project's own non-destructive Decision Log convention.
>
> **2026-08-23 addendum (Decision Log D-48):** FR-QPB-118 is further revised to a complete
> five-step form, inserting four ordered row-*filtering* steps (Plantae-kingdom-subtree filter;
> `rank_id >= 700` filter; seven-phylum vascular-plants-only allowlist; duplicate-scientific-name
> canonical-KTSN resolution against the NIBR xlsx's `관속식물류` sheet) ahead of the already-
> existing column-extraction step (now Step 5), in response to a continued real-device crash after
> D-47's fix. AC-QPB-071/AC-QPB-083 are further revised (row-count assertions only; their other
> clauses are unchanged and restated) to the new, final **20,914**-row combined result (superseding
> D-47's "same count as the raw source" expectation); new AC-QPB-084 (Step 1), AC-QPB-085 (Step 2),
> AC-QPB-087 (Step 3), and AC-QPB-086 (Step 4) make each row-filtering step independently testable.
> A new harness function, `run_ktsn_reference_pipeline()` (HARNESS_CONTRACT.md function 11), was
> added specifically to expose each step's own intermediate output — `build_project()`'s own
> bundled artifact only ever exposes the final, Step-5-reduced output, which cannot answer "how
> many rows survive Step 1/2/3 alone." See the table/notes/ambiguities below for the precise,
> updated mapping; the pre-D-48 text of this addendum's affected rows is not deleted, only
> superseded.
>
> **2026-08-24 addendum (Decision Log D-50/D-51):** FR-QPB-109 is further revised, and AC-QPB-046
> is further revised (Decision Log D-50, then extended again by Decision Log D-51), to resolve, for
> the first time, *how* candidate-selection/manual-entry attribute persistence is actually
> achieved, and for which feature-lifecycle state. Real-device testing plus direct QGIS/QField
> source inspection (Decision Log D-50) confirmed the prior speculative
> `currentFeature.setAttribute(...)`-style write-back attempt never works, and confirmed a
> different, narrower mechanism that **does** work — but only for a **brand-new, not-yet-saved
> feature** created via QField's own "Add feature" flow (a pending write-back request written via
> `FileUtils.writeFileContent()`; the `<project_slug>.qml` project plugin polling via a
> short-interval `Timer`; locating the live `AttributeFormModel` via
> `overlayFeatureFormDrawer.featureForm.model`; confirming a UUID match; applying the write via
> `changeAttribute(name, value)`; clearing the request afterward by overwriting it with empty
> content, never `FileUtils.deleteFiles()`). For an **existing, already-saved feature** reopened
> later, write-back is a **confirmed, permanent limitation** (QField's own `FeatureListForm.qml`
> never exposes its internal, per-feature `AttributeFormModel`), not an open question. Decision Log
> D-51 further confirms the stakeholder's explicit answer to former Open Question O-20: the
> identical confirmed mechanism also governs **manual identification entry**, not just real
> candidate selection, for the brand-new/not-yet-saved-feature branch. AC-QPB-078's own
> manual-identification enum-value/nulled-column assertions are confirmed unaffected by both
> entries and are not touched by this addendum.
>
> **What changed in this round's tests, precisely (see the updated table row and new automation
> note below for the full mapping):**
>
> 1. **`test_post_mvp_manual_qfield_runtime.py`'s single `test_ac046_...` placeholder is retired,
>    replaced by two branch-specific placeholders** — `test_ac046a_brand_new_unsaved_feature_
>    write_back_persists_for_candidate_selection_and_manual_entry` (candidate-selection **and**
>    manual-entry sub-cases, both now framed as confirming a *real, already-once-confirmed*
>    mechanism actually persists, not merely hoping an unconfirmed mechanism might) and
>    `test_ac046b_existing_already_saved_feature_write_back_is_a_confirmed_permanent_limitation`
>    (confirming the disclosed "not saved" message appears and the previously-saved value is
>    untouched — a **PASS**, not a defect, for this branch). Both remain manual/`device`-marked,
>    skipped placeholders: this project still has no QField/QML runtime capable of actually driving
>    QField's "Add feature" flow, its project-plugin `Timer` poll, or reopening a previously-saved
>    feature inside a live QField session, and this project's hard QGIS-isolation rule bars
>    constructing a `QgsApplication`/launching an interactive QGIS/QField session to work around
>    that. Both are more precisely worded than the prior single test, but neither is a new kind of
>    check — the underlying limitation (no QField/QML runtime in this harness) is unchanged.
> 2. **New, genuinely automatic `test_fr109_*` tests were added to
>    `test_post_mvp_identification_plugin.py`**, checking only whether the generated QML source for
>    both build-pipeline artifacts (the embedded widget; the `<project_slug>.qml` project plugin)
>    **structurally contains** the confirmed mechanism's named constituent pieces —
>    `FileUtils.writeFileContent(...)` (widget: writing the request; plugin: clearing it by
>    overwrite), a QML `Timer` component (plugin), `overlayFeatureFormDrawer`/`featureForm.model`
>    (plugin), `changeAttribute(...)` (plugin), and the absence of `FileUtils.deleteFiles(...)`
>    (plugin). This required one minimal harness-contract extension — `inspect_identification_
>    widget()` (HARNESS_CONTRACT.md function 10) now also returns a `qml_code` key with the widget's
>    raw QML source text, alongside the pre-existing `qml_code_present` boolean it was already
>    computing internally. **These are necessary, not sufficient, checks**: they cannot execute the
>    QML, so they cannot confirm the mechanism actually works end-to-end on a real device, nor that
>    it is wired specifically to both required trigger points (candidate selection and
>    manual-entry confirmation) rather than only one of them — see automation note 11 below for the
>    full list and each check's own disclosed limitations. **Confirmed by an actual test run
>    against the current (pre-D-50/D-51) implementation**
>    (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/
>    test_post_mvp_identification_plugin.py tests/acceptance/qfield_project_builder/
>    test_post_mvp_manual_qfield_runtime.py -q`): all 9 new `test_fr109_*` tests **FAIL** (red), as
>    expected for a not-yet-implemented mechanism (confirmed, by direct inspection during this
>    round, that `qfield_builder/qml_plugin.py` still implements only the prior,
>    now-confirmed-broken `currentFeature.setAttribute(...)` attempt in `qpbPersistIdentification`,
>    and that `render_project_plugin_qml()` contains only a toolbar button/toast — no pending-request
>    write/poll/apply/clear mechanism of any kind exists yet in either generated artifact); every
>    other, previously-existing test in both files still passes/skips exactly as before. A full
>    `tests/acceptance/` run (`.venv/bin/python -m pytest tests/acceptance -q`) confirms **214
>    passed, 26 skipped, exactly the same 9 new failures** — no other, previously-passing test in
>    the suite was altered or broken by this round's changes.
>
> See the table/notes/ambiguities below for the precise, updated mapping; the pre-D-50/D-51 text of
> this addendum's affected rows is not deleted, only superseded, per this project's own
> non-destructive convention.
>
> **2026-08-25 addendum (Decision Log D-52): new AC-QPB-088, FR-QPB-101 (post-MVP; further
> revised) — the mandatory photo-resize-via-temporary-copy step.** A confirmed real-device HTTP
> `413 Request Entity Too Large` finding (an unresized, full-resolution photo submitted to
> Pl@ntNet) led to FR-QPB-101 being revised to require a mandatory resize step, inserted between
> reading the original attachment file's bytes and submitting those bytes to Pl@ntNet: write the
> original, already-read bytes to a **new temporary file** (`FileUtils.writeFileContent()`); call
> `FileUtils.restrictImageSize(<tempFilePath>, 1280)` against that temporary copy's own path
> only — never the original attachment file's own path; read the resized bytes back from that
> same temporary file (`FileUtils.readFileContent()`), for use as the Pl@ntNet multipart request
> body, in place of the original, unresized bytes; and clean up the temporary file afterward by
> overwriting it with empty content (`FileUtils.writeFileContent(tempPath, "")`), never via
> `FileUtils.deleteFiles()` (Decision Log D-50's already-confirmed unreliability finding for that
> method). The original attachment file itself must remain completely unmodified and at its
> original, full resolution at all times. New AC-QPB-088 (Section 18.6) makes this mechanism
> independently, structurally testable against the generated project's embedded identification
> widget QML, mirroring how AC-QPB-069/AC-QPB-070 and the FR-QPB-109 `test_fr109_*` tests already
> make other Section 13 structural mechanism details independently testable. Five new
> `test_ac088_*` tests were added to `test_post_mvp_identification_plugin.py` (parametrized, all 3
> layer combos each — 15 new test invocations total), checking each of AC-QPB-088's four named
> elements plus a combined ordering assertion; see automation note 12 below for the full mapping,
> the disclosed variable-identification heuristic these tests use (and its limitation), and the
> "Ambiguities" section's own corresponding entry. **Confirmed by an actual test run performed
> during this test-design round** (`.venv/bin/python -m pytest
> tests/acceptance/qfield_project_builder/test_post_mvp_identification_plugin.py -q -k ac088`):
> all 15 new `test_ac088_*` test invocations **FAIL** (red), exactly as expected — a direct
> inspection of `qfield_builder/qml_plugin.py` during this round confirmed no
> `FileUtils.restrictImageSize(` call, and no photo-resize temporary-file handling of any kind,
> exists yet anywhere in the generated QML (`qpbReadFileBytes`/`qpbRunIdentification` still read
> and submit each photo's original, unresized bytes directly) — and a full `tests/acceptance/`
> run (`.venv/bin/python -m pytest tests/acceptance -q`) confirms **223 passed, 26 skipped, 15
> failed — exactly the 15 new `test_ac088_*` invocations, and no other, previously-passing test in
> the suite regressed** (the 223-passed figure is 9 higher than the 214 recorded in the
> immediately preceding 2026-08-24/D-50/D-51 addendum above solely because this repository's
> current, separately-authored working tree already contains an uncommitted implementation of the
> `test_fr109_*` write-back mechanism, unrelated to this round's own AC-QPB-088 work — confirmed
> by inspecting `qfield_builder/qml_plugin.py`, which already implements
> `qpbWriteAttributeWriteBackRequest`/`render_project_plugin_qml`'s `Timer`/
> `overlayFeatureFormDrawer`/`changeAttribute` mechanism; this test-design round did not add,
> modify, or re-verify those 9 tests). FR-QPB-104's new
> cross-reference note (clarifying which bytes are submitted, without duplicating substance) and
> AC-QPB-040 (reviewed, confirmed unaffected in substance) require no test change.
>
> **2026-08-25 addendum (Decision Log D-54): new AC-QPB-094/AC-QPB-095/AC-QPB-096; FR-QPB-104
> (further revised) and FR-QPB-109 (further revised) — Pl@ntNet-supplied representative images per
> candidate, with required CC BY-SA attribution.** Pl@ntNet's own public API documentation
> (researched and confirmed by the orchestrator, not by a fresh test-designer live call this
> round) confirms an `include-related-images=true` request query parameter causes each `results[*]`
> entry to additionally carry a related-images list, each entry with `organ`/`author`/`license`/
> `date`/`citation` fields plus an `o`(original)/`m`(medium)/`s`(small) size-variant `url` object;
> these images are CC BY-SA-licensed with an explicit, verbatim attribution requirement whenever
> displayed (`"Photo(s): [Contributor Username] / Pl@ntNet, CC BY-SA"`). The stakeholder,
> having asked the orchestrator to investigate feasibility, then explicitly directed proceeding.
> FR-QPB-104 (further revised) adds `include-related-images=true` to the existing `api-key`/
> `nb-results=3` query parameters (unchanged in every other respect). FR-QPB-109 (further revised)
> adds a purely additive candidate-card requirement (the existing persistence-mechanism substance,
> Decision Log D-38/D-43/D-50/D-51, is unchanged and not reopened): each candidate card must show
> one representative image (the small, `s`, size variant) when the API response supplies one for
> that candidate, with the required CC BY-SA attribution whenever an image is actually displayed,
> degrading gracefully (no broken-image placeholder, no attribution text) when a candidate has no
> image, and never letting an image-load failure corrupt the rest of that candidate's existing
> textual content.
>
> **What changed in this round's tests, precisely:**
>
> 1. **One new offline request-shape test in `test_post_mvp_plantnet_request_shape.py`** —
>    `test_requests_related_images_are_included` — asserting
>    `build_plantnet_identify_request()`'s returned `query` dict carries
>    `"include-related-images": True` (a Python `bool`, mirroring the existing `"nb-results": 3`
>    int convention — see HARNESS_CONTRACT.md function 7's own 2026-08-25 addendum), alongside the
>    existing `nb-results=3` assertion immediately above it in the same file. `api-key` remains, as
>    before, outside this offline function's own return shape (unchanged; `api-key` is supplied
>    only at real call time, via function 8's `api_key` argument) — this test does not attempt to
>    assert an `api-key` key.
> 2. **Five new, parametrized (3 layer combos each — 15 test invocations total) structural QML
>    checks in `test_post_mvp_identification_plugin.py`**, covering AC-QPB-095's three named
>    elements (an `Image` element bound to the small-variant URL per candidate; the CC BY-SA
>    attribution-text construction; the graceful-degradation guard) plus one additional check for
>    the image-load-failure-isolation clause FR-QPB-109's own text separately requires (an
>    `onStatusChanged`/`Image.Error` guard) — see automation note 13 below for the full mapping,
>    each check's disclosed heuristic, and its limitation. **These required no harness-contract
>    change**: `inspect_identification_widget()`'s existing `qml_code` field (already added by the
>    2026-08-24/D-50/D-51 addendum, function 10) already exposes the raw QML source text these new
>    checks inspect.
> 3. **One new manual/`device`-marked, skipped placeholder in
>    `test_post_mvp_manual_qfield_runtime.py`** —
>    `test_ac096_representative_image_renders_on_screen_with_attribution_and_image_load_failure_does_not_corrupt_the_card`
>    — for AC-QPB-096, which the specification itself already records as "verifiable only via
>    real-device/real-QGIS-Desktop manual QA ... not asserted as already confirmed by this entry."
>    Mirrors this file's established `device`-marked placeholder convention (e.g. AC-QPB-072,
>    AC-QPB-046a/b above).
>
> **Confirmed by an actual test run performed during this test-design round**
> (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/
> test_post_mvp_plantnet_request_shape.py tests/acceptance/qfield_project_builder/
> test_post_mvp_identification_plugin.py -k "ac094 or related_images or ac095" -q`): all 16 new
> test invocations (1 + 15) **FAIL** (red), exactly as expected for a not-yet-implemented
> mechanism — a direct inspection of `qfield_builder/plantnet_client.py` and
> `qfield_builder/qml_plugin.py` during this round confirmed the request's `query` dict carries no
> `include-related-images` key, and the generated identification widget QML contains no `Image`
> element, no occurrence of the literal text "CC BY-SA", and no `author`-field reference of any
> kind. The new `test_ac096_...` manual placeholder **SKIPS**, matching this file's established
> convention for manual/`device`-only criteria. A full `tests/acceptance/` run
> (`.venv/bin/python -m pytest tests/acceptance -q`) confirms **238 passed, 27 skipped, 16
> failed in 903.27s** — the 16 failures are exactly the new tests above, and no other,
> previously-passing test in the suite regressed (the 238-passed/27-skipped figures are higher
> than the 223-passed/26-skipped baseline recorded in the immediately preceding 2026-08-25/D-52
> addendum above solely because this repository's current, separately-authored working tree
> already contains further uncommitted implementation work beyond this traceability file's own
> scope — confirmed by inspecting `qfield_builder/qml_plugin.py`, which already implements
> `FileUtils.restrictImageSize(...)` and the full AC-QPB-088 resize mechanism; this test-design
> round did not add, modify, or re-verify those tests).
>
> See the table/notes/ambiguities below for the precise, updated mapping; the pre-D-54 text of
> this addendum's affected rows is not deleted, only superseded (there is no pre-D-54 text to
> supersede here, since AC-QPB-094/095/096 and this FR-QPB-104/109 revision are net-new additions,
> not corrections of a prior round's rows).
>
> **2026-08-26 addendum (Decision Log D-60, confirmed by D-64): new AC-QPB-099; FR-QPB-106
> (revised)/FR-QPB-109 (further revised) — standardized `taxon_full_nm`-derived scientific-name
> display/persistence.** The stakeholder instructed that, after identification, the displayed and
> persisted scientific name must be the standardized name from `taxon_full_nm` (already bundled,
> already read internally by `qpbMatchKtsn`/`ktsn_match.py`), not Pl@ntNet's own raw
> `species.scientificName`, whenever a KTSN match exists. FR-QPB-106 (revised) adds a new
> `direct_scientific_name` field to the direct-match branch, mirroring the existing
> `direct_korean_name` field exactly (the matched row's own `taxon_full_nm`, `<em>`/`</em>` tags
> removed, populated whenever a direct match is found, independent of whether accepted-name
> resolution itself succeeds). FR-QPB-109 (further revised) requires both the candidate-card
> display and the value persisted to `selected_scientific_name` on selection to prefer, in order:
> (1) `accepted_scientific_name` when accepted-name resolution succeeded; (2) otherwise
> `direct_scientific_name` when a direct match was found but accepted-name resolution did not
> succeed; (3) otherwise (no direct KTSN match at all) Pl@ntNet's own raw `species.scientificName`,
> **completely unchanged** — Decision Log D-64's own explicit, narrower reading: the existing
> no-match fallback and its "KTSN match not found" disclosure are not altered by this entry. New
> AC-QPB-099 makes this independently testable via structural QML inspection.
>
> **What changed in this round's tests, precisely:**
>
> 1. **Three new structural QML checks were added to `test_post_mvp_identification_plugin.py`**
>    (parametrized, 3 layer combos each — 9 test invocations total), in a new section near the end
>    of that file: `test_ac099_direct_match_constructs_direct_scientific_name_from_tag_stripped_
>    taxon_full_nm`, `test_ac099_display_and_persistence_prefer_accepted_then_direct_then_
>    raw_plantnet_name`, `test_ac099_no_direct_match_branch_is_structurally_unchanged_no_direct_
>    scientific_name_constructed`. These required **no harness-contract change** — the existing
>    `inspect_identification_widget()`'s `qml_code` field (already added by the 2026-08-24/D-50/D-51
>    addendum, HARNESS_CONTRACT.md function 10) already exposes the raw QML source text these new
>    checks inspect. Every test in this new section is a *necessary, not sufficient* structural
>    check, exactly like the pre-existing `test_fr109_*`/`test_ac088_*`/`test_ac095_*` sections it
>    is modeled on — it cannot confirm the preference order is actually applied correctly at
>    runtime for a real Pl@ntNet response.
> 2. **A purely additive, supplementary extension to the *pure-Python* `match_ktsn` reference
>    implementation and its own tests in `test_post_mvp_ktsn_matching.py`** — two new tests,
>    `test_direct_scientific_name_is_populated_from_tag_stripped_taxon_full_nm_on_a_direct_match`
>    and `test_direct_scientific_name_is_none_when_no_direct_match_is_found` — extending
>    `match_ktsn()`'s existing return contract (HARNESS_CONTRACT.md function 9) with one new key,
>    `direct_scientific_name`, mirroring the existing `direct_korean_name` key exactly. **This is
>    supplementary evidence, not the primary AC-QPB-099 test**: AC-QPB-099's own text names the QML
>    functions (`qpbHandlePlantNetResponse`/`qpbMatchKtsn`/`qpbSelectCandidate`) to inspect
>    structurally, which the `test_ac099_*` tests above do; extending the pure-Python reference
>    implementation of the same underlying rule keeps that reference implementation faithful to the
>    now-revised FR-QPB-106 text, matching this suite's own established practice of keeping
>    `match_ktsn` a complete, accurate model of FR-QPB-106/107 as revised over time.
>
> **Confirmed by an actual test run performed during this test-design round**
> (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_symbol_styling.py
> tests/acceptance/qfield_project_builder/test_ktsn_lookup_table.py
> tests/acceptance/qfield_project_builder/test_post_mvp_identification_plugin.py
> tests/acceptance/qfield_project_builder/test_post_mvp_ktsn_matching.py
> tests/acceptance/qfield_project_builder/test_qgis_project_config.py -q`): 6 of the 9 new
> `test_ac099_*` invocations and both new `test_direct_scientific_name_*` tests **FAIL** (red), as
> expected for a not-yet-implemented mechanism (confirmed, by direct inspection during this round,
> that `qfield_builder/qml_plugin.py`'s `qpbMatchKtsn`/`qpbHandlePlantNetResponse`/
> `qpbSelectCandidate` construct no `direct_scientific_name` value anywhere, and that
> `qfield_builder/ktsn_match.py`'s Python `match_ktsn` likewise returns no `direct_scientific_name`
> key). **The remaining 3 `test_ac099_*` invocations (`test_ac099_no_match_branch_unchanged_no_
> direct_scientific_name_constructed`, all 3 layer combos) legitimately PASS today, not
> vacuously**: element (3)'s own assertion is that the existing "KTSN match not found" disclosure
> text remains present, unweakened, unremoved by this entry — which is already true of the current,
> pre-this-entry generated QML, exactly as it should be both before and after this feature is
> implemented. Every other, previously-existing test in these five files still passes/skips exactly
> as before (11 failed total across the whole combined run — the 11 above, all new — 86 passed
> (including these 3 `test_ac099_no_match_branch_...` invocations), 43 skipped; the other 6
> failures/skips in that combined run belong to the separate D-65/D-66/D-67/
> D-68 rounds, see `qfield_project_builder_symbol_styling.traceability.md`/
> `qfield_project_builder_ktsn_lookup_table.traceability.md` for those).
>
> See the table/notes/ambiguities below for the precise, updated mapping; the pre-D-64 text of
> this addendum's affected rows is not deleted, only superseded (there is no pre-D-64 text to
> supersede here, since AC-QPB-099 and this FR-QPB-106/109 revision are net-new additions).
>
> This is a **second, later test-design round against the same overall specification** as
> `qfield_project_builder.traceability.md` (the approved MVP baseline). It is recorded as its own
> file, not merged into the MVP file, so the already-approved MVP traceability record is not
> touched by this round's additions — see this repository's `tests/acceptance/README.md` for the
> pointer between the two.
>
> Tests: `tests/acceptance/qfield_project_builder/test_post_mvp_identification_plugin.py`,
> `test_post_mvp_reference_bundling.py`, `test_post_mvp_ktsn_reference_pipeline.py`,
> `test_post_mvp_plantnet_request_shape.py`, `test_post_mvp_ktsn_matching.py`,
> `test_post_mvp_manual_qfield_runtime.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s
> "Post-MVP: Section 13" section (functions 7–11, and the `build_project` config additions; the
> 2026-08-24 addendum to function 10 for the new `qml_code` field; the 2026-08-25 addendum to
> function 7 for the new `include-related-images` query-dict key).

**Explicitly excluded from this round, by the task's own instruction:** FR-QPB-102
(automatic/silent identification). No test in this round implies it exists or is expected; the
specification itself defers it (D-13/D-33), and this round does not reopen that.

**Also out of scope for this round (not part of the requested FR list, and not touched):**
FR-QPB-110 (offline queue) and AC-QPB-047/048 (Section 13.8's queueing behavior, and FR-QPB-102's
own negative-behavior criterion). Not covered, not claimed as covered.

## A genuine architectural split (read this before the table below)

Section 13 splits into two genuinely different kinds of thing:

1. **Desktop build-pipeline output** — files this project's own existing Python build pipeline
   generates into the project folder (a `<project_slug>.qml` sidecar; attribute-form widget
   configuration inside the `.qgs` project; copied reference-data files). Testable the same
   direct way the already-approved MVP suite tests generated artifacts: via
   `qfield_builder.acceptance_api.build_project`, inspecting the real output.
2. **QField/QML runtime behavior** — the actual click handler behind "Identify attached photos";
   the live `XMLHttpRequest` call to Pl@ntNet; KTSN matching *as it runs* against a live response;
   on-device raster sampling. **This project has no QField/QML runtime or test harness of any
   kind.** No test in this round invents one.

For a narrow, explicitly-authorized middle ground — FR-QPB-104's request-shape *rules* and
FR-QPB-106/107's KTSN matching *rules* — these tests validate a **pure-Python reference
implementation of the rules** against real data/a real API, per Decision Log D-32/D-34's explicit
authorizations. **This validates that the rules are correct; it is not, and must never be read
as, a substitute for confirming the eventual QML implementation behaves identically** — that
residual confirmation is manual/`device` QA, documented, not silently skipped.

## Traceability table

| AC ID / FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-069 | `<project_slug>.qml` plugin file alongside `.qgs` | `test_post_mvp_identification_plugin.py::test_ac069_project_slug_qml_plugin_file_exists_alongside_qgs` (parametrized, all 4 survey types), `::test_ac069_plugin_filename_uses_ascii_slug_not_unicode_display_name` | auto |
| AC-QPB-070 | `QML Widget` embedded in the relevant layer's attribute form, not a disconnected surface (further revised, Decision Log D-46 — scoped to QField, QGIS-Desktop-rendering caveat disclosed; see note 5) | `test_post_mvp_identification_plugin.py::test_ac070_qml_widget_is_embedded_in_the_relevant_layers_attribute_form` (parametrized: `inventory_observation`, `observation`×2) | auto (proxy — PyQGIS-backed `inspect_identification_widget`; see note 1) |
| ~~AC-QPB-071 (original, D-35)~~ | ~~Complete, unmodified KTSN CSV + probability rasters bundled under `reference/`, relative paths only~~ | ~~`test_post_mvp_reference_bundling.py::test_ac071_reference_data_is_bundled_with_relative_paths_and_no_cropping`, `::test_ac071_full_real_reference_dataset_is_bundled_completely_unmodified`~~ | **superseded, not deleted — see AC-QPB-071 (further revised, D-47) immediately below; these two named tests no longer exist under these names, see below** |
| ~~AC-QPB-071 (further revised, Decision Log D-47)~~ | ~~(1) Build-time-extracted `reference/ktsn_lookup.csv` (exact 5-column header/order, same row count as source, `ktsn` preserved as string, `correct_list` preserved as valid JSON) bundled **instead of** the complete raw CSV, which must not appear anywhere in the project; (2) the complete, unmodified probability-raster set bundled exactly as before (unaffected, unweakened); (3) relative paths only~~ | ~~`test_post_mvp_reference_bundling.py::test_ac071_ktsn_lookup_csv_and_raster_set_are_bundled_with_relative_paths_and_no_raw_csv`, `::test_ac071_full_real_reference_dataset_extraction_and_raster_bundling`~~ | **superseded, not deleted, for its row-count sub-clause only (the D-47-era assumption that the lookup file has the same row count as the raw source CSV no longer holds under D-48's five-step pipeline) — see AC-QPB-071 (further revised, Decision Log D-48) immediately below; these test names are retained and rewritten in place, not renamed, since D-48 only changes their row-count assertions and adds a cross-check, not their overall structure** |
| AC-QPB-071 (further revised, Decision Log D-48, complete five-step-pipeline form) | (1) Build-time-extracted `reference/ktsn_lookup.csv` (exact 5-column header/order, row count matching the rows surviving **Steps 1-4** of the five-step pipeline — **not** the raw source's row count, `ktsn` preserved as string, `correct_list` preserved as valid JSON) bundled **instead of** the complete raw CSV, which must not appear anywhere in the project; (2) the complete, unmodified probability-raster set bundled exactly as before (unaffected, unweakened); (3) relative paths only | `test_post_mvp_reference_bundling.py::test_ac071_ktsn_lookup_csv_and_raster_set_are_bundled_with_relative_paths_and_no_raw_csv` (fast, fixture-based mechanism check — this fixture now deliberately includes one row that Step 1 must exclude alongside two rows built to survive every step, so the count assertion genuinely proves filtering is wired in, not merely a same-count coincidence), `::test_ac071_full_real_reference_dataset_extraction_and_raster_bundling` (slow, the real ~183 MB CSV + real NIBR xlsx + ~64 MB raster set, no override — asserts the exact real, final **20,914**-row count, and additionally cross-checks the real `build_project()` artifact against `run_ktsn_reference_pipeline()`'s independent computation over the same real data) | auto |
| AC-QPB-083 (further revised, Decision Log D-48, complete five-step-pipeline form; row-count sub-clause only, superseding its D-47 form) | FR-QPB-118's full five-step pipeline: exact 5-column header/order on the rows surviving Steps 1-4 (real-fixture final count exactly **20,914**); success path when source is valid; early, clear failure (not silent skip, not fallback to raw CSV, not partial/truncated output) when source CSV is missing or fails FR-QPB-105 validation | Extraction-property path (Step 5 mechanics, unaffected by D-48 in substance): `test_post_mvp_reference_bundling.py::test_ac083_extraction_preserves_ktsn_as_string_and_correct_list_as_valid_json` (dedicated fixture, all 3 rows deliberately constructed to survive Steps 1-4, exercising string/JSON preservation including a leading-zero-`ktsn` edge case), plus the same assertions folded into `::test_ac071_ktsn_lookup_csv_and_raster_set_are_bundled_with_relative_paths_and_no_raw_csv`/`::test_ac071_full_real_reference_dataset_extraction_and_raster_bundling` (header/final row-count). Failure path (unaffected by D-48): `::test_ac083_missing_source_csv_fails_early_with_no_partial_project_or_lookup_file`, `::test_ac083_source_csv_missing_required_columns_fails_early_with_no_partial_lookup_file`. Per-step row-filtering correctness (Steps 1-4, new for D-48): see AC-QPB-084/085/086/087 below | auto |
| AC-QPB-084 (new, Decision Log D-48; Step 1) | Plantae-kingdom-subtree filter via the `p_ktsn` parent-pointer chain; real count exactly 32,251 of 212,397 | `test_post_mvp_ktsn_reference_pipeline.py::test_ac084_step1_synthetic_transitive_closure_edge_cases` (direct child, two-hop grandchild, chain-terminates, chain-broken, other-kingdom-lineage), `::test_ac084_step1_real_full_csv_produces_exactly_32251_survivors`, `::test_ac084_step1_real_full_csv_excludes_a_known_non_plantae_row` | auto |
| AC-QPB-085 (new, Decision Log D-48; Step 2) | `rank_id >= 700` species-level-and-below filter; real count exactly 26,763 of the 32,251 Step-1 survivors | `test_post_mvp_ktsn_reference_pipeline.py::test_ac085_step2_synthetic_rank_filter_edge_cases` (Species/Subspecies survive; Genus/Family/blank/non-numeric excluded), `::test_ac085_step2_real_full_csv_produces_exactly_26763_survivors` | auto |
| AC-QPB-087 (new, Decision Log D-48; Step 3) | Seven-phylum vascular-plants-only allowlist against `r200_nm`; real count exactly 21,025 of the 26,763 Step-2 survivors | `test_post_mvp_ktsn_reference_pipeline.py::test_ac087_step3_synthetic_phylum_allowlist_edge_cases` (all 7 allowlisted phyla survive; all 3 bryophyte + all 3 algae-under-Plantae phyla + blank excluded), `::test_ac087_step3_real_full_csv_produces_exactly_21025_survivors` | auto |
| AC-QPB-086 (further revised, Decision Log D-48; renumbered Step 3 -> Step 4) | Duplicate-scientific-name canonical-KTSN resolution against the NIBR xlsx's `관속식물류` sheet; real count exactly 20,914 of the 21,025 Step-3 survivors (58 duplicated names/118 rows in, 7 resolved, 51 dropped/104 rows removed) | `test_post_mvp_ktsn_reference_pipeline.py::test_ac086_step4_synthetic_resolvable_duplicate_keeps_exactly_one_row`, `::test_ac086_step4_synthetic_unresolvable_duplicates_drop_all_variants` (all 3 sub-variants: not-found, multi-match, mismatch), `::test_ac086_step4_synthetic_non_duplicated_name_is_unaffected`, `::test_ac086_step4_synthetic_fixture_combined_row_count`, `::test_ac086_step4_real_full_csv_and_xlsx_produces_exactly_20914_survivors` | auto |
| AC-QPB-072 | On-device probability sampling while disconnected from desktop, subject to D-36's feasibility caveat | `test_post_mvp_manual_qfield_runtime.py::test_ac072_on_device_probability_sampling_while_disconnected_from_desktop` | **manual/device** (documented, skipped) |
| AC-QPB-040 | Exactly 3 results, ordered by descending score | Request-count half + response-ordering half: `test_post_mvp_plantnet_request_shape.py::test_requests_exactly_three_results` (offline), `::test_plantnet_live_endpoint_authenticates_and_returns_the_confirmed_schema` (network, confirms real API pre-sorts by descending score). Residual on-screen-rendering half: `test_post_mvp_manual_qfield_runtime.py::test_ac040_displayed_candidate_card_order_matches_descending_score` | auto (offline) + network (opt-in) for the request/response halves; **manual/device** for the on-screen-rendering half |
| AC-QPB-041 | `<em>` tags stripped when normalizing `taxon_full_nm` for matching | `test_post_mvp_ktsn_matching.py::test_ac041_em_tags_are_stripped_and_direct_match_found_for_a_real_accepted_row` (+ whitespace-normalization variants) | auto (pure-Python rule validation against real data — see the KTSN split note above) |
| AC-QPB-042 | Synonym + single-entry `correct_list` resolves to the correct accepted KTSN row | `test_post_mvp_ktsn_matching.py::test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_lestes`, `::test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_tinea`, `::test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_lygris` | auto (pure-Python rule validation against real data) |
| AC-QPB-043 | Missing/malformed/conflicting (`KTSN` vs `KTNS`) accepted-name entries handled deterministically and visibly | Real, naturally-occurring case: `test_ac043_empty_correct_list_is_a_real_naturally_occurring_resolution_failure`. Constructed edge cases (real data confirmed clean of these — see note 2): `::test_ac043_malformed_correct_list_json_is_handled_deterministically_not_a_crash`, `::test_ac043_missing_ktsn_and_ktns_keys_entirely_is_handled_deterministically`, `::test_ac043_conflicting_ktsn_and_ktns_values_are_flagged_ambiguous_not_silently_resolved`, `::test_ktns_is_used_only_as_a_defensive_legacy_fallback_when_ktsn_key_is_absent`, `::test_ktsn_and_ktns_present_with_the_same_value_is_not_treated_as_a_conflict`, `::test_accepted_ktsn_not_found_in_csv_is_handled_gracefully` | auto (pure-Python; one real-data case + clearly-labeled constructed edge cases — note 2) |
| AC-QPB-044 | EXIF GPS (WGS 84) transformed to the raster CRS before sampling | `test_post_mvp_manual_qfield_runtime.py::test_ac044_exif_gps_is_transformed_to_the_raster_crs_before_sampling` | **manual/device** (documented, skipped) |
| AC-QPB-045 | `-9999`/out-of-extent/missing-raster/no-GPS all display "No probability data" (or the no-GPS equivalent), never a numeric zero | `test_post_mvp_manual_qfield_runtime.py::test_ac045_ac049_ac050_probability_display_rules` (parametrized, includes the -9999/out-of-extent/missing-raster/no-GPS scenarios) | **manual/device** (documented, skipped) |
| ~~AC-QPB-046 (post-MVP; revised, Decision Log D-43)~~ | ~~Selecting a candidate updates only the intended observation; UUID relations remain intact~~ | ~~`test_post_mvp_manual_qfield_runtime.py::test_ac046_selecting_a_candidate_updates_only_the_intended_observation`~~ | **superseded, not deleted — see AC-QPB-046 (further revised; Decision Log D-50/D-51) immediately below; this test name no longer exists, see below** |
| AC-QPB-046 (further revised; Decision Log D-50, further revised again by Decision Log D-51) | **(a)** Brand-new, not-yet-saved feature: the confirmed, real write-back mechanism must actually persist the result for both a real candidate selection and a manual identification entry (Decision Log D-51 extends the mechanism to manual entry) — `identification_status` = `"complete"`/`"manual"` respectively, per the unchanged Decision Log D-38/D-43 rule and AC-QPB-078. **(b)** Existing, already-saved feature reopened later: write-back is a confirmed, permanent limitation — the disclosed "not saved" message must appear and the previously-saved GeoPackage value must remain unchanged, for either a candidate selection or a manual entry; this is the correct, intended behavior, not a defect | `test_post_mvp_manual_qfield_runtime.py::test_ac046a_brand_new_unsaved_feature_write_back_persists_for_candidate_selection_and_manual_entry` (branch (a), both sub-cases), `::test_ac046b_existing_already_saved_feature_write_back_is_a_confirmed_permanent_limitation` (branch (b)) | **manual/device** (documented, skipped — see note 3 on why no Python proxy is attempted, and note 11 below for the complementary, automatic, purely structural mechanism-presence check this does not substitute for) |
| FR-QPB-109 (further revised; Decision Log D-50/D-51) — structural presence of the confirmed write-back mechanism only, brand-new/not-yet-saved-feature branch | Does the generated QML source (the embedded widget; the `<project_slug>.qml` project plugin) structurally contain the confirmed mechanism's named constituent pieces: `FileUtils.writeFileContent()` (pending-request write, widget; clearing-by-overwrite, plugin); a `Timer` poll (plugin); `overlayFeatureFormDrawer`/`featureForm.model` (plugin); a UUID-match check before applying (plugin, best-effort); `changeAttribute(name, value)` (plugin); never `FileUtils.deleteFiles()` (plugin) | `test_post_mvp_identification_plugin.py::test_fr109_embedded_widget_writes_a_pending_write_back_request_via_file_utils` (parametrized, 3 layer combos), `::test_fr109_project_plugin_polls_for_the_pending_request_via_a_timer`, `::test_fr109_project_plugin_reaches_the_live_attribute_form_model_via_overlay_drawer`, `::test_fr109_project_plugin_matches_the_pending_requests_uuid_before_applying_it`, `::test_fr109_project_plugin_applies_the_pending_request_via_change_attribute`, `::test_fr109_project_plugin_never_clears_the_pending_request_via_delete_files`, `::test_fr109_project_plugin_clears_the_pending_request_with_a_literal_empty_content_overwrite` | auto — **necessary, not sufficient**; see note 11 below. All 9 currently **FAIL** (red), confirmed by an actual run, since the required mechanism is not yet implemented |
| AC-QPB-049 | Sampled `0.0` is a valid probability, not "No probability data" | `test_post_mvp_manual_qfield_runtime.py::test_ac045_ac049_ac050_probability_display_rules` (parametrized scenario) | **manual/device** (documented, skipped) |
| AC-QPB-050 | Out-of-range, non-`-9999` value is a validation warning, never clamped | `test_post_mvp_manual_qfield_runtime.py::test_ac045_ac049_ac050_probability_display_rules` (parametrized scenario) | **manual/device** (documented, skipped) |
| FR-QPB-104 (request shape, no numbered AC beyond AC-QPB-040 above) | Endpoint family, `nb-results=3`, one `organs` per photo in order, ≤5 photos, JPEG/PNG only, real auth scheme/endpoint/schema confirmed live | `test_post_mvp_plantnet_request_shape.py` (all offline tests) + `::test_plantnet_live_endpoint_authenticates_and_returns_the_confirmed_schema`, `::test_plantnet_live_endpoint_rejects_an_invalid_key_without_losing_the_observation` (both `network`-marked) | auto (offline) + network (opt-in) |
| FR-QPB-105 (no numbered AC; supports FR-QPB-112) | Early, clear failure when the identification subsystem is enabled but the CSV is missing/lacks required columns | `test_post_mvp_reference_bundling.py::test_fr105_missing_reference_csv_fails_build_early_with_a_clear_message`, `::test_fr105_reference_csv_missing_required_columns_fails_build_early` | auto |
| AC-QPB-088 (post-MVP; new, Decision Log D-52) / FR-QPB-101 (post-MVP; further revised; Decision Log D-52) — mandatory photo-resize-via-temporary-copy step | The embedded identification widget's QML must, before submitting a photo to Pl@ntNet: (1) write the original, already-read bytes to a NEW temporary file via `FileUtils.writeFileContent()`, distinct from the original attachment file's own path; (2) call `FileUtils.restrictImageSize(<tempFilePath>, 1280)` against that temporary copy's path only — never the original attachment file's own path; (3) read the resized bytes back from that same temporary file via the plain `FileUtils.readFileContent()`, in place of the original, unresized bytes; and (4) clean up the temporary file by overwriting it with empty content, never via `FileUtils.deleteFiles()` | `test_post_mvp_identification_plugin.py::test_ac088_widget_writes_original_photo_bytes_to_a_new_temporary_file` (element 1, parametrized, 3 layer combos), `::test_ac088_widget_calls_restrict_image_size_only_against_the_temporary_file_with_maximum_1280` (element 2, positive + negative), `::test_ac088_widget_reads_the_resized_bytes_back_from_the_temporary_file` (element 3), `::test_ac088_widget_clears_the_temporary_file_with_empty_content_never_delete_files` (element 4, positive + negative), `::test_ac088_resize_mechanism_runs_in_order_and_resized_bytes_precede_the_plantnet_request` (combined ordering, all 4 elements plus the XMLHttpRequest-submission-boundary check) | auto — **necessary, not sufficient**; see automation note 12 below. All 15 parametrized test invocations currently **FAIL** (red), confirmed by an actual run, since the mechanism is not yet implemented |
| AC-QPB-094 (post-MVP; new, Decision Log D-54) / FR-QPB-104 (post-MVP; further revised; Decision Log D-54) | The outgoing Pl@ntNet identify request's query parameters must include `include-related-images=true`, alongside the existing `api-key`/`nb-results=3` | `test_post_mvp_plantnet_request_shape.py::test_requests_related_images_are_included` | auto. Currently **FAILS** (red), confirmed by an actual run, since the mechanism is not yet implemented |
| AC-QPB-095 (post-MVP; new, Decision Log D-54) / FR-QPB-109 (post-MVP; further revised; Decision Log D-54) — per-candidate representative-image display, CC BY-SA attribution, graceful degradation | For each of the three displayed candidates: (1) an `Image` element bound to that candidate's own small (`s`) size-variant URL; (2) an attribution-text construction combining `author`, "Pl@ntNet", and "CC BY-SA," conditioned on that candidate having image data; (3) a graceful-degradation guard so a candidate with no image data renders neither the image nor attribution text, leaving its other content unaffected; plus (4), from FR-QPB-109's own separate image-load-failure-isolation text, an explicit `Image.Error`-handling guard | `test_post_mvp_identification_plugin.py::test_ac095_widget_contains_an_image_element_bound_to_model_data_per_candidate` (element 1, parametrized, 3 layer combos), `::test_ac095_small_s_size_variant_is_selected_for_the_representative_image` (element 1's size-variant clause), `::test_ac095_attribution_text_combines_author_plantnet_and_cc_by_sa_per_candidate` (element 2), `::test_ac095_image_and_attribution_are_guarded_by_a_conditional_check` (element 3), `::test_ac095_image_element_has_an_error_status_handling_guard` (element 4/image-load-failure-isolation clause) | auto — **necessary, not sufficient**; see automation note 13 below. All 15 parametrized test invocations currently **FAIL** (red), confirmed by an actual run, since the mechanism is not yet implemented |
| AC-QPB-096 (post-MVP; new, Decision Log D-54) | A real representative image actually renders on screen with its required CC BY-SA attribution, and an isolated subsequent image-load failure does not corrupt the rest of that candidate's display | `test_post_mvp_manual_qfield_runtime.py::test_ac096_representative_image_renders_on_screen_with_attribution_and_image_load_failure_does_not_corrupt_the_card` | **manual/device** (documented, skipped — explicitly a manual-QA-only criterion per the specification's own text) |
| AC-QPB-099 (post-MVP; new, Decision Log D-60, confirmed by D-64) / FR-QPB-106 (revised)/FR-QPB-109 (further revised) — standardized `taxon_full_nm`-derived scientific-name display/persistence | (1) The direct-match branch constructs a `direct_scientific_name` value from the matched row's own `taxon_full_nm`, `<em>`/`</em>` tags removed, populated whenever a direct match is found; (2) the candidate-card display and the selection-persistence value each prefer `accepted_scientific_name`, then `direct_scientific_name`, then Pl@ntNet's own raw `species.scientificName`, in that order; (3) the no-direct-match branch is structurally unchanged — still falls through to Pl@ntNet's raw name with the existing "KTSN match not found" disclosure, no `direct_scientific_name` constructed | `test_post_mvp_identification_plugin.py::test_ac099_direct_match_constructs_direct_scientific_name_from_tag_stripped_taxon_full_nm` (element 1, parametrized, 3 layer combos), `::test_ac099_display_and_persistence_prefer_accepted_then_direct_then_raw_plantnet_name` (element 2), `::test_ac099_no_match_branch_unchanged_no_direct_scientific_name_constructed` (element 3). Supplementary pure-Python reference-implementation coverage (not a substitute for the above — see the 2026-08-26/D-60/D-64 addendum note): `test_post_mvp_ktsn_matching.py::test_direct_scientific_name_is_populated_from_tag_stripped_taxon_full_nm_on_a_direct_match`, `::test_direct_scientific_name_is_none_when_no_direct_match_is_found` | auto — **necessary, not sufficient** for the QML-structural tests (see automation note 14 below). 6 of the 9 parametrized `test_ac099_*` invocations (elements 1/2) and both `test_direct_scientific_name_*` tests currently **FAIL** (red), confirmed by an actual run, since the mechanism is not yet implemented; the remaining 3 (`test_ac099_no_match_branch_unchanged_no_direct_scientific_name_constructed`, element 3) legitimately **PASS** already, since the existing no-match fallback text this element checks for is genuinely unaffected by this entry |

## Notes on automation approach

1. **AC-QPB-070's exact editor-widget-type-string uncertainty.** `inspect_identification_widget`
   (a new, PyQGIS-backed harness function, mirroring `validate_project`'s existing role) is used
   instead of a raw-XML-regex assertion (unlike e.g. AC-QPB-013's `RelationReference` regex in the
   MVP suite) specifically because the test-designer could not fully confirm the exact registered
   QGIS editor-widget-type-ID string for "QML Widget" without either constructing a `QgsApplication`
   (barred by this project's hard QGIS-isolation rule) or a canonical document stating it verbatim.
   Evidence gathered instead: the C++ class `QgsQmlWidgetWrapper` is confirmed present in the
   installed QGIS-LTR 3.34 framework (read-only `strings`/`grep` inspection, never executed);
   human-facing labels `"QML Widget"`/`"QML Code"` were found alongside it; and this codebase's own
   already-working code (`qgis_worker.py`) establishes the naming pattern
   `Qgs<X>WidgetWrapper` -> registered ID `"<X>"` (`QgsRelationReferenceWidgetWrapper` ->
   `"RelationReference"`, already used and working), which by the same pattern implies `"Qml"` for
   `QgsQmlWidgetWrapper` — but this specific inference was not independently confirmed live. Rather
   than hardcode a possibly-wrong literal string into an assertion, the exact-string judgment is
   delegated to `inspect_identification_widget`'s own (implementer-authored, real-PyQGIS-backed)
   implementation; the tests assert only on the returned structured booleans. See
   HARNESS_CONTRACT.md function 10 for the full evidence trail.
2. **AC-QPB-043's constructed edge cases.** A full scan of the real, full KTSN CSV
   (~212,397 rows) performed during test design found **zero** malformed `correct_list` JSON
   values and **zero** literal `"KTNS"` occurrences anywhere in the file — the real dataset is
   confirmed clean of exactly the edge cases AC-QPB-043 requires be handled. Rather than leave
   these spec-required rules untested because the real data happens not to exercise them, they
   are tested against a small, explicitly-labeled *constructed* fixture
   (`fixtures/ktsn_synthetic_edge_cases.csv`, clearly-fake `9000000000xx`-style KTSN identifiers
   and fictional `Testus ...` scientific names) exercising exactly the malformed/missing/
   conflicting shapes the rule text describes. This mirrors this project's own established
   practice of using deliberately constructed fixtures for hypothetical-but-required edge-case
   coverage (e.g. the MVP suite's malformed-attachment-path fixtures in
   `test_geopackage_schema_by_type.py`), and is documented here rather than silently blended with
   the real-data tests.
3. **AC-QPB-046 — no Python "as-if-QML-had-updated-it" proxy is attempted, deliberately.** Unlike
   the MVP suite's AC-QPB-011/013/015 proxies (which inspect *real, already-generated* relation/
   widget/renderer configuration — a mechanism this project's own build pipeline genuinely
   produces), the actual mechanism by which embedded QField-plugin QML writes an update back into
   a feature's GeoPackage attributes is not confirmed to exist by any concrete, working example
   found during specification research — the same class of "plausible but unconfirmed" uncertainty
   Decision Log D-36 explicitly records for on-device raster sampling (AC-QPB-072). Simulating "as
   if the QML had made this update" via a bespoke Python harness function would misrepresent an
   unconfirmed runtime mechanism as tested, which the task's own instructions caution against
   ("Do not invent a testing mechanism that doesn't exist"). This criterion is therefore left
   entirely as manual/`device` QA, not partially proxied.

   **2026-08-24 update (Decision Log D-50/D-51) — this note's own reasoning is unchanged, and is
   not contradicted by the new `test_fr109_*` structural tests (see note 11 below).** Decision Log
   D-50 has since confirmed a *real*, working mechanism exists for the brand-new/not-yet-saved-
   feature branch — no longer "plausible but unconfirmed" for that branch specifically. This did
   not change the conclusion above: no Python harness function simulating "as if the QML had
   applied this update" is added here or anywhere else in this round, because doing so would still
   misrepresent this project's own build pipeline as having exercised the *runtime* update path,
   which it genuinely has not and cannot (no QField/QML runtime exists in this project). What *is*
   newly addable, and is added (note 11), is a categorically different kind of check: inspecting
   whether the generated static QML *source text* literally contains the mechanism's named
   constituent API calls — this is exactly the same kind of "generated build-pipeline artifact"
   check AC-QPB-069/070 already perform (note 5 below), not a new "as-if" runtime proxy.
4. **FR-QPB-109's timestamp/API-model-version persistence — flagged as an untestable
   specification gap, not silently resolved (see "Ambiguities" below).**
5. **AC-QPB-070 revised (Decision Log D-46) — no test code change required.** The specification
   was revised to correct FR-QPB-101's photo-file-reading mechanism (QField's native
   `org.qfield.core`/`QfFileUtils.readFileContent()` singleton, not a plain QML `XMLHttpRequest`
   `file://` read) and, as a disclosed consequence, to scope AC-QPB-070's criterion explicitly to
   QField, disclosing that the same embedded `QML Widget` is expected to fail to load/render at
   all when the same generated project is opened in QGIS Desktop specifically (an accepted,
   disclosed tradeoff, not a defect — Decision Log D-46). This traceability round re-examined
   `test_ac070_qml_widget_is_embedded_in_the_relevant_layers_attribute_form` (and
   `inspect_identification_widget`'s contract, HARNESS_CONTRACT.md function 10) against the revised
   criterion and confirmed **no test code change is required**: the test's assertions are, and
   always were, purely structural/static — inspecting the generated `.qgs` project's own XML/PyQGIS
   object model for (a) a QML Widget editor-widget field, (b) that field's embedding inside the
   layer's `QgsAttributeEditorContainer`/`QgsAttributeEditorField` attribute-form tree, and (c) the
   presence of non-empty QML source text. At no point does this test, or
   `inspect_identification_widget`, load, execute, or render the embedded QML through any real QML
   engine, for either QGIS Desktop or QField — the module docstring already explicitly disclaimed
   testing "QML/QField-runtime behavior," only "generated build-pipeline artifacts." Because the
   test never asserted *which* host application successfully renders the widget (nor could it, with
   no QML runtime available to this harness), D-46's scoping/disclosure — which concerns actual
   runtime rendering behavior only — does not touch anything this test actually checks. The test
   file has been updated only with an additive docstring note referencing this determination (no
   assertion changed); see the module docstring in
   `test_post_mvp_identification_plugin.py` for the same note in situ.
6. **New open question surfaced by this D-46 traceability review (not itself resolved here) — a
   documented `manual`-marked placeholder, not a new numbered acceptance criterion.** D-46 discloses
   that the embedded `QML Widget` is expected to fail to *load/render* in QGIS Desktop, but does not
   state whether that same load failure additionally triggers a project-level "repair"/error warning
   of the kind **AC-QPB-001** (an MVP criterion, unrevised by D-46, still worded as applying to "a
   generated project for any of the four survey types," with no identification-enabled carve-out)
   requires be absent. This is a genuine, non-blocking gap worth tracking, not an invented
   requirement: AC-QPB-001's own existing automated test
   (`test_geopackage_common.py::test_ac001_project_opens_without_repair_warning`) only ever builds
   projects with `identification_enabled=False` (`make_base_config`'s default) via a headless,
   non-interactive `validate_project()` call that never opens any feature's attribute form — so it
   has never actually exercised, and cannot detect, this specific new failure mode introduced by
   D-46's mechanism change. Confirming the actual outcome requires a human opening an
   identification-enabled generated project's real attribute form inside a live, running QGIS
   Desktop GUI session — genuinely outside this harness's reach (headless PyQGIS inspection only;
   this repository's hard QGIS-isolation rule also bars the test-designer role from ever
   constructing a `QgsApplication`, GUI or otherwise, for any diagnostic purpose). Judgment call: a
   **documented `manual`-marked, skipped placeholder test** was added — mirroring this same test
   suite's established convention for real-GUI/real-device-only scenarios (e.g.
   `test_error_handling.py::test_ac032_packaged_application_starts_and_completes_wizard_on_target_os`,
   `test_post_mvp_manual_qfield_runtime.py`'s `device`-marked placeholders) — rather than either (a)
   inventing an automated assertion about an outcome the specification does not define, or (b)
   silently treating this as fully out of scope, since it bears directly on an unrevised MVP
   criterion (AC-QPB-001) that this round's own D-46 change newly puts at risk for
   identification-enabled projects specifically. See
   `test_post_mvp_identification_plugin.py::test_qgis_desktop_repair_warning_status_when_qml_widget_fails_to_load_not_yet_confirmed`
   for the full manual-QA steps and reasoning. No new AC-QPB-### number is introduced for this —
   consistent with this file's existing FR-QPB-109 precedent (note 4 above), which also documents an
   untested gap via a placeholder test without minting a new criterion ID.

7. **AC-QPB-071/AC-QPB-083 (Decision Log D-47) — test file updated, not merely re-noted.** Unlike
   D-46's AC-QPB-070 revision (note 5 above, no test-code change required because that revision
   only re-scoped an already-purely-structural assertion), D-47 changes actual bundled-artifact
   *behavior* — the complete raw KTSN CSV must no longer be bundled at all, replaced by a
   build-time-extracted `reference/ktsn_lookup.csv` — so the previously-approved
   `test_ac071_reference_data_is_bundled_with_relative_paths_and_no_cropping`/
   `test_ac071_full_real_reference_dataset_is_bundled_completely_unmodified` tests, which asserted
   the now-superseded "complete raw CSV bundled byte-identical" behavior for the KTSN-CSV half,
   were renamed and rewritten (not merely annotated) to assert the new, revised criterion instead
   — `test_ac071_ktsn_lookup_csv_and_raster_set_are_bundled_with_relative_paths_and_no_raw_csv` and
   `test_ac071_full_real_reference_dataset_extraction_and_raster_bundling`. The probability-raster
   half of both tests' assertions is carried forward **unchanged, line-for-line in substance** (same
   byte-identical `.tif`-by-`.tif` comparison against the source scaffold) — this is the "do not
   remove or weaken existing raster coverage" requirement, confirmed satisfied by inspection. Two
   new dedicated tests were added for AC-QPB-083's own extraction-correctness and early-failure
   requirements: `test_ac083_extraction_preserves_ktsn_as_string_and_correct_list_as_valid_json`
   (using a new fixture, `fixtures/reference_data_ktsn_lookup_sample/`, built from real header +
   real rows plus one deliberately constructed synthetic row — see that fixture's own generation
   note and this test's docstring), `test_ac083_missing_source_csv_fails_early_with_no_partial_project_or_lookup_file`,
   and `test_ac083_source_csv_missing_required_columns_fails_early_with_no_partial_lookup_file`
   (both extending FR-QPB-105's existing early-failure fixtures with the AC-QPB-083-specific
   "no partial/truncated `reference/ktsn_lookup.csv`, no partial project at the final output path"
   assertion, mirroring `test_error_handling.py::test_ac031_a_failed_build_leaves_no_partial_project_at_the_final_path`'s
   established `not out_dir.exists() or not any(out_dir.iterdir())` convention). **Confirmed by an
   actual test run against the current (pre-D-47) implementation** (`pytest -q
   tests/acceptance/qfield_project_builder/test_post_mvp_reference_bundling.py`): the 3 tests
   asserting the new `reference/ktsn_lookup.csv` behavior fail, exactly as expected for a
   not-yet-implemented spec revision (red state); the other 5 tests in the file (FR-QPB-105's two
   early-failure tests, the two new AC-QPB-083 early-failure tests, and the
   identification-disabled `reference/`-absent test) pass unchanged, since none of them depend on
   the specific bundled-KTSN-artifact behavior D-47 changes. A full `tests/acceptance/` run (199
   passed, 25 skipped, exactly the same 3 failures) confirms no other, previously-passing test in
   the suite was altered or broken by this round's changes.
8. **A pre-existing gap noticed, not created, by this round: AC-QPB-077 (Decision Log D-41, the
   NIBR-list extraction — the other precedent this task pointed to) has no acceptance test
   anywhere in `tests/acceptance/`, despite being listed in Section 18.6 and despite a
   corresponding *unit* test already existing (`tests/unit/test_reference_bundle.py`'s
   `test_extract_national_ktsn_list_*` tests, at the `qfield_builder.reference_bundle` module
   level, not the acceptance-suite/`acceptance_api.build_project()` level).** This traceability
   file's own table (both before and after this addendum) has never listed AC-QPB-077 at all. This
   is out of this round's assigned scope (D-47/AC-QPB-071/AC-QPB-083 only) and is not fixed here —
   flagged so it is not mistaken for something this addendum was supposed to close.
9. **AC-QPB-071/083/084/085/086/087 (Decision Log D-48) — new per-step harness function added, not
   merely a test rewrite.** Unlike D-47 (note 7 above), which only changed what a single, final
   bundling artifact must contain, D-48 inserts four ordered row-*filtering* steps that
   `build_project()`'s own final `reference/ktsn_lookup.csv` artifact cannot, by itself, prove
   ran correctly step-by-step (Step 5 has already reduced every surviving row to its 5 lookup
   columns and final row count by the time any generated project can be inspected — there is no
   way to observe "only Steps 1-2 ran" from that artifact alone). A new pure-Python harness
   function, `run_ktsn_reference_pipeline()` (HARNESS_CONTRACT.md function 11, mirroring function
   9's `match_ktsn` precedent for exposing a rule the shipped mechanism will eventually run, but
   unlike `match_ktsn` this rule's *real* production home is expected to be ordinary desktop
   Python, per D-48's own "never at runtime on-device" text), was added and is the sole basis for
   the new `test_post_mvp_ktsn_reference_pipeline.py` file's AC-QPB-084/085/086/087 tests. The
   existing `test_post_mvp_reference_bundling.py` tests for AC-QPB-071/083 were updated in place
   (not renamed) to: (a) assert the new, final 20,914-row count instead of "same as raw source";
   (b) use a `reference_data_valid_sample` fixture deliberately extended with one Step-1-excluded
   row (a real insect taxon) alongside its two pre-existing survivor rows, so the fast mechanism
   test genuinely proves filtering is wired into the bundling pipeline rather than merely
   asserting a same-count coincidence; and (c) in the slow, real-CSV/real-xlsx authoritative test,
   additionally cross-check the real `build_project()` artifact's row set against
   `run_ktsn_reference_pipeline()`'s own independent computation over the identical real source
   data, tying the two code paths together. All of this round's other pre-D-48 tests in
   `test_post_mvp_reference_bundling.py` (FR-QPB-105's two early-failure tests, AC-QPB-083's two
   early-failure tests, the identification-disabled `reference/`-absent test) are unaffected and
   unchanged, since D-48 does not touch the conditions those tests exercise.
10. **A new `_test_reference_data_dir` precondition (Decision Log D-48) — every fixture directory
    used for an identification-enabled `build_project()` call in this round now also needs a
    synthetic NIBR xlsx sidecar.** Because Step 4 depends on the same NIBR xlsx workbook already
    required by FR-QPB-113/D-40/D-41, `reference_data_valid_sample/` and
    `reference_data_ktsn_lookup_sample/` (both pre-existing, D-47-era fixture directories) each
    received a new `tables/2025년 국가생물종목록_v1.0.xlsx` sidecar (a small, synthetic,
    programmatically generated workbook containing only a correctly shaped, empty `관속식물류`
    sheet — no duplicate-name rows are needed in either fixture's own CSV, so no lookup entries
    were needed either). See HARNESS_CONTRACT.md's `_test_reference_data_dir` addendum note.
11. **FR-QPB-109 (further revised; Decision Log D-50/D-51) — the new `test_fr109_*` structural
    tests, what each one actually checks, and each one's own disclosed limitation.** All seven
    `test_fr109_*` tests in `test_post_mvp_identification_plugin.py` inspect only the generated
    QML/JavaScript *source text* this project's own build pipeline produces (never loading,
    executing, or rendering it through any real QML/QField engine) — the same kind of
    "generated build-pipeline artifact" check AC-QPB-069/070 already perform, just against a
    different required piece of content. Each is a *necessary, not sufficient* check on its own
    named piece of the confirmed mechanism, and none of them, individually or collectively, can
    prove: (a) the mechanism actually works end-to-end on a real device; (b) the various pieces are
    actually wired together correctly (e.g. that the `Timer`'s `onTriggered` handler is the thing
    that actually calls `changeAttribute`, rather than these two things merely coexisting
    unconnected somewhere in the same file); or (c) that the mechanism is reachable from **both**
    required trigger points (real candidate selection **and** manual-entry confirmation, per
    Decision Log D-51) rather than only one of them — proving (c) would require tracing the
    generated JavaScript's own call graph, which these regex/substring checks deliberately do not
    attempt, to avoid asserting a claim more precise than a static-text check can actually support.
    The authoritative, end-to-end confirmation for all of this remains the two branch-specific
    manual/`device` placeholders in `test_post_mvp_manual_qfield_runtime.py`
    (`test_ac046a_.../test_ac046b_...`), unchanged in kind from the pre-D-50/D-51 placeholder this
    round retired, just re-worded to the new confirmed-mechanism/confirmed-limitation framing.

    Specifically:
    - `test_fr109_embedded_widget_writes_a_pending_write_back_request_via_file_utils`
      (parametrized, 3 layer combos) — the embedded widget's own QML source must contain
      `FileUtils.writeFileContent(`. Because Decision Log D-51 confirms "the identical confirmed
      mechanism" governs both candidate selection and manual entry, a **single**, shared call site
      is the *expected*, spec-aligned shape (not a limitation to work around) — this test
      therefore requires the call to exist at least once, not that it is duplicated once per
      trigger, and cannot prove the call is reachable from both triggers (see (c) above). This
      required extending `inspect_identification_widget()`'s own return contract with a new
      `qml_code` key (HARNESS_CONTRACT.md function 10, 2026-08-24 addendum) exposing the widget's
      raw QML source text directly — the pre-existing `qml_code_present` boolean alone cannot
      support a content assertion.
    - `test_fr109_project_plugin_polls_for_the_pending_request_via_a_timer` — the project plugin
      must declare a QML `Timer` component (`re.search(r"\bTimer\s*\{", ...)`). Cannot confirm the
      Timer actually drives the polling logic (see (b) above).
    - `test_fr109_project_plugin_reaches_the_live_attribute_form_model_via_overlay_drawer` —
      deliberately loose: requires only that `"overlayFeatureFormDrawer"` and both `"featureForm"`
      and `".model"` appear somewhere in the plugin source, since the exact statement-level
      chaining (a single dotted expression vs. split across an intermediate variable) is an
      implementation detail the specification's own text does not literally dictate beyond naming
      this access path conceptually.
    - `test_fr109_project_plugin_matches_the_pending_requests_uuid_before_applying_it` — this
      section's weakest check, flagged as such in its own docstring: no specific property/variable
      name for the required UUID comparison is named anywhere in the specification's own text
      (unlike `overlayFeatureFormDrawer`/`featureForm.model`/`changeAttribute`, which are literal,
      spec-quoted identifiers), so this test only requires the case-insensitive substring `"uuid"`
      to appear somewhere in a plugin source that also calls `changeAttribute(` — a minimal signal
      that *some* identity check is present, not proof that it is correct or that it actually gates
      the write.
    - `test_fr109_project_plugin_applies_the_pending_request_via_change_attribute` — the plugin
      must call `changeAttribute(`. The most literal, least ambiguous check in this section, since
      `changeAttribute(name, value)` is a literal, spec-quoted API name.
    - `test_fr109_project_plugin_never_clears_the_pending_request_via_delete_files` — the robust
      half of the clearing requirement: `FileUtils.deleteFiles(` must never appear anywhere in the
      plugin (a plain substring absence, not a fragile regex — this is the strongest, most
      confidently-assertable negative in this section), and `FileUtils.writeFileContent(` must
      appear in the plugin at all (for clearing, distinct from the widget's own initial
      request-creating write).
    - `test_fr109_project_plugin_clears_the_pending_request_with_a_literal_empty_content_overwrite`
      — deliberately kept as its own, separate, narrower test (not folded into the previous one) so
      that a styling difference in *how* the empty-content overwrite is expressed cannot mask the
      stronger, more essential `deleteFiles`-absence/`writeFileContent`-presence assertions above.
      Looks for a literal `FileUtils.writeFileContent(<path>, "")` (or `''`) call; a semantically
      equivalent implementation using a named empty-string variable (e.g. `var EMPTY = "";
      FileUtils.writeFileContent(path, EMPTY);`) would not be structurally detected by this
      specific regex — disclosed in the test's own docstring, not silently assumed away. If this
      test alone ever fails while every other `test_fr109_*` test passes, that is this narrow
      regex's own limitation, not necessarily a real conformance defect, and should be checked by
      hand against the actual generated source before being treated as a genuine gap.

    **Confirmed by an actual test run performed during this test-design round** (command and exact
    result recorded in this file's 2026-08-24 addendum note above): all 9 parametrized/individual
    `test_fr109_*` tests **FAIL**, exactly as expected for a not-yet-implemented mechanism, and no
    other test in `tests/acceptance/` regressed.
12. **AC-QPB-088 (Decision Log D-52) — the new `test_ac088_*` structural tests, what each checks,
    and the disclosed variable-identification heuristic they all share.** All five `test_ac088_*`
    tests in `test_post_mvp_identification_plugin.py` (parametrized, 3 layer combos each) inspect
    only the generated widget QML *source text* returned by `inspect_identification_widget()`'s
    `qml_code` field — the same kind of check the `test_fr109_*` tests above already perform —
    never loading, executing, or rendering it through any real QML/QField engine. Each is a
    *necessary, not sufficient* check.

    Identifying "the temporary file's own path" is unambiguous and robust: it is anchored on the
    literal, spec-mandated `1280` argument to `FileUtils.restrictImageSize(<X>, 1280)` — no other
    call in this codebase resizes anything, so `<X>` is taken as ground truth for "the temporary
    file's own path" throughout this section.

    Identifying **"the original attachment file's own path"**, by contrast, is a genuine,
    disclosed heuristic, not a proof, because neither FR-QPB-101 nor AC-QPB-088 names a specific
    variable/identifier for it (unlike FR-QPB-109's spec-quoted `overlayFeatureFormDrawer`/
    `changeAttribute`, which are real QField API names the generated source must contain
    literally). These tests instead: (a) locate the smallest enclosing JavaScript
    `function name(...) { ... }` block containing the `restrictImageSize(<X>, 1280)` call (found
    via simple brace-depth counting, not a full JS parser); (b) within that same local scope only,
    take the argument of the first `FileUtils.readFileContent()`/`QfFileUtils.readFileContent()`
    call whose argument differs from `<X>` as "the original path"; and (c) fall back to a
    whole-source search only if no such call exists in that local scope (e.g. if the resize logic
    is factored into its own small helper function). Scoping to the enclosing function first
    (rather than searching the whole file indiscriminately) specifically avoids a real, confirmed
    collision risk: this project's own already-shipped widget QML legitimately calls
    `FileUtils.readFileContent()` for several wholly unrelated bundled reference-data reads (the
    KTSN lookup CSV via `qpbLoadCsv`, the national accepted-taxa list via
    `qpbLoadNationalKtsnSet`, the pending write-back request via `qpbPollPendingWriteBack`) whose
    own, differently-scoped local path variables (confirmed, by inspection, to also be named
    `absPath` in several of these unrelated functions, following this codebase's own established
    naming convention) must not be misidentified as "the original attachment path." **Disclosed,
    not resolved, limitation:** a correct implementation that reuses and reassigns one single
    local variable name for both the original path and (after the original bytes have already been
    read) the temporary path, within the very same function, would not be structurally
    distinguishable — by this or any purely textual check — from an incorrect implementation that
    resizes the original attachment file in place. This mirrors this same file's own precedent for
    disclosing a heuristic's limitation rather than silently treating it as airtight (e.g. note 11
    above's `test_fr109_project_plugin_matches_the_pending_requests_uuid_before_applying_it`,
    explicitly documented as this project's "weakest check"). See also the corresponding
    "Ambiguities" entry below.

    Specifically:
    - `test_ac088_widget_writes_original_photo_bytes_to_a_new_temporary_file` (element (1)) —
      requires a `FileUtils.writeFileContent(<tempFilePath>, <content>)` call whose second argument
      is *not* a literal empty string (distinguishing it from the element-(4) cleanup call).
    - `test_ac088_widget_calls_restrict_image_size_only_against_the_temporary_file_with_maximum_1280`
      (element (2), positive and negative together) — requires a `FileUtils.restrictImageSize(<X>,
      1280)` call, and additionally requires that `<X>` is never the identified "original
      attachment path" for *any* `restrictImageSize()` call found (not just the first).
    - `test_ac088_widget_reads_the_resized_bytes_back_from_the_temporary_file` (element (3)) —
      requires a call matching AC-QPB-088's own literal spelling, plain `FileUtils.readFileContent(
      <tempFilePath>)` — deliberately *not* matching `QfFileUtils.readFileContent(...)`, which
      FR-QPB-101 (further revised; Decision Log D-46)'s own text still uses for the original
      photo-byte read specifically; Decision Log D-52's own "Naming note, disclosed not resolved"
      leaves this naming question open, and this test does not silently resolve it either.
    - `test_ac088_widget_clears_the_temporary_file_with_empty_content_never_delete_files` (element
      (4), positive and negative together) — requires `FileUtils.deleteFiles(` to be wholly absent
      from the widget's QML (a plain substring check, the strongest, most confidently-assertable
      negative in this section, mirroring `test_fr109_project_plugin_never_clears_the_pending_
      request_via_delete_files`'s identical convention for the project plugin), and requires a
      `FileUtils.writeFileContent(<tempFilePath>, "")` (or `''`) cleanup call.
    - `test_ac088_resize_mechanism_runs_in_order_and_resized_bytes_precede_the_plantnet_request` —
      ties elements (1)–(4) together by character-offset position (write < restrictImageSize <
      read-back < cleanup), and additionally requires the read-back to occur before the widget's
      one and only `new XMLHttpRequest()` call (the confirmed Pl@ntNet-submission mechanism,
      Decision Log D-31/D-46, unaffected by D-52) — a reasonable, spec-grounded proxy for "the
      resized bytes are what end up in the request," since submission cannot occur before the
      request object exists. This cannot, and does not claim to, prove by static text alone that
      the specific *variable* holding the resized bytes is what is actually assembled into the
      multipart body (that would require executing the QML) — it proves only that every required
      step is present and correctly ordered, the necessary precondition for that outcome.

    **Confirmed by an actual test run performed during this test-design round**
    (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/
    test_post_mvp_identification_plugin.py -q -k ac088`): all 15 parametrized `test_ac088_*` test
    invocations **FAIL**, exactly as expected for a not-yet-implemented mechanism (`15 failed, 21
    deselected in 228.40s`); a full `tests/acceptance/` run (`.venv/bin/python -m pytest
    tests/acceptance -q`) confirms **223 passed, 26 skipped, 15 failed in 689.80s** — the 15
    failures are exactly the new `test_ac088_*` invocations above, and no other, previously-passing
    test in the suite regressed (see this file's 2026-08-25 header addendum for why 223, not 214,
    is the correct comparison baseline).
13. **AC-QPB-095 (Decision Log D-54) — the new `test_ac095_*` structural tests, what each checks,
    and the disclosed heuristics they rely on.** All five `test_ac095_*` tests in
    `test_post_mvp_identification_plugin.py` (parametrized, 3 layer combos each) inspect only the
    generated widget QML *source text* returned by `inspect_identification_widget()`'s existing
    `qml_code` field (no harness-contract change was needed) — never loading, executing, or
    rendering it through any real QML/QField engine. Each is a *necessary, not sufficient* check.

    **The `modelData` anchor.** Neither FR-QPB-109 nor AC-QPB-095 mandates a specific QML component
    for "one candidate card each" — some per-item delegate mechanism must exist, and QML's own
    built-in `modelData` property (automatically exposed to a `Repeater`/`ListView` delegate whose
    model is a plain array of objects) is the natural, idiomatic mechanism for this, and is exactly
    how this widget's own pre-existing, already-shipped candidate-card content is already
    implemented (confirmed by inspecting `qfield_builder/qml_plugin.py`'s existing
    `Repeater { id: qpbCandidateRepeater ... }` delegate during this test-design round). These
    tests use a `modelData` reference as the signal that a given `Image`/attribution/visibility
    construction is "bound to this specific candidate." **Disclosed limitation:** an alternative,
    equally spec-conformant implementation that displays exactly three per-candidate blocks through
    some other QML mechanism not exposing per-item data via `modelData` (e.g. index-based
    `Repeater.itemAt(i)` access) would not be structurally detected by these checks.

    **The literal "Pl@ntNet" text.** This project's own existing, already-shipped QML consistently
    writes "Pl@ntNet" using a Unicode-escape device rather than a literal `@` character in every one
    of its own user-facing string literals (confirmed by inspection of `qfield_builder/
    qml_plugin.py`). The specification's own literal attribution text uses a plain `@` character.
    The relevant test (`test_ac095_attribution_text_combines_author_plantnet_and_cc_by_sa_per_
    candidate`) accepts either spelling, so neither convention is unfairly marked non-conformant.

    Specifically:
    - `test_ac095_widget_contains_an_image_element_bound_to_model_data_per_candidate` (element (1))
      — requires at least one balanced `Image { ... }` QML block (found via brace-depth counting,
      the same assumption `_enclosing_function_span`/`_brace_block_span` rely on) whose `source:`
      property expression references `modelData`.
    - `test_ac095_small_s_size_variant_is_selected_for_the_representative_image` (element (1)'s
      size-variant clause) — a whole-widget-source heuristic (not scoped to the Image block found
      above), searching for a `url`-named identifier followed by a `.s`/`["s"]` accessor, anchored
      on Pl@ntNet's own confirmed `url: {o, m, s}` field shape. **Disclosed limitation:** cannot
      prove this specific access is what actually feeds the Image element's `source` property (that
      extraction most plausibly happens in the candidate-construction JavaScript, not the
      declarative Image element itself) — it only proves *some* code selects the `s` variant.
    - `test_ac095_attribution_text_combines_author_plantnet_and_cc_by_sa_per_candidate` (element
      (2)) — anchors on the brand-new (pre-D-54, confirmed absent) literal substring "CC BY-SA",
      then requires the literal "Pl@ntNet" text, a bare-word `author` reference, and a `modelData`
      reference, all within a bounded proximity window of it, so the check cannot be satisfied by
      these signals appearing coincidentally, unrelated to each other, elsewhere in this ~1700-line
      file.
    - `test_ac095_image_and_attribution_are_guarded_by_a_conditional_check` (element (3),
      graceful degradation) — requires the modelData-bound Image element, and the smallest
      balanced QML block enclosing the "CC BY-SA" text (found via a whole-file stack-based
      brace scan, `_smallest_enclosing_brace_block`), to each carry a conditional guard: either a
      `visible:` property referencing `modelData`, or (for the Image element only) a ternary
      (`?:`) expression — mirroring this widget's own pre-existing convention for exactly this kind
      of per-candidate conditional display (its existing warning-text Label already reads
      `visible: modelData.warning_text.length > 0`). **Disclosed limitation:** proves only that
      *some* conditional construct exists, not that it is logically correct, and cannot confirm the
      visual absence of a broken-image placeholder on an actual screen (AC-QPB-096's own residual
      manual QA).
    - `test_ac095_image_element_has_an_error_status_handling_guard` (element (4), FR-QPB-109's
      separate image-load-failure-isolation clause) — requires the modelData-bound Image element to
      contain both `onStatusChanged` and `Image.Error` (QML's own standard `Image.status` API, not a
      project-specific convention). **Disclosed limitation, this section's own weakest check** (
      mirroring note 11's `uuid`-check precedent): finding this handler does not prove its body
      actually leaves the rest of the candidate's Column content untouched, nor does its absence
      prove a failure *would* corrupt the display.

    **Confirmed by an actual test run performed during this test-design round**
    (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/
    test_post_mvp_plantnet_request_shape.py tests/acceptance/qfield_project_builder/
    test_post_mvp_identification_plugin.py -k "ac094 or related_images or ac095" -q`): all 16 new
    test invocations (1 AC-QPB-094 request-shape test + 15 parametrized `test_ac095_*` invocations)
    **FAIL**, exactly as expected for a not-yet-implemented mechanism (`16 failed, 54 deselected in
    217.34s`); a full `tests/acceptance/` run (`.venv/bin/python -m pytest tests/acceptance -q`)
    confirms **238 passed, 27 skipped, 16 failed in 903.27s** — the 16 failures are exactly the new
    tests above, and no other, previously-passing test in the suite regressed.
14. **AC-QPB-099 (Decision Log D-60, confirmed by D-64) — the new `test_ac099_*` structural
    tests, what each checks, and their disclosed limitations.** All three `test_ac099_*` tests in
    `test_post_mvp_identification_plugin.py` (parametrized, 3 layer combos each — 9 test
    invocations total) inspect only the generated widget QML *source text* via
    `inspect_identification_widget()`'s existing `qml_code` field (no harness-contract change
    needed) — never loading, executing, or rendering it. Each is a *necessary, not sufficient*
    check.

    - `test_ac099_direct_match_constructs_direct_scientific_name_from_tag_stripped_taxon_full_nm`
      (element (1)) — requires the literal identifier `direct_scientific_name` to appear
      as the target of an assignment, and that either the assignment's own right-hand expression or
      the wider QML source references this codebase's own already-confirmed, already-shipped
      `qpbStripEmTags` tag-stripping function (the same one `accepted_scientific_name`'s existing
      construction already uses) and the `taxon_full_nm` column. **Disclosed limitation:** cannot
      confirm this assignment is reached only when a direct match is genuinely found (that would
      require tracing/executing the surrounding control flow), only that the construction exists
      somewhere with the right shape.
    - `test_ac099_display_and_persistence_prefer_accepted_then_direct_then_raw_plantnet_name`
      (element (2)) — searches for a `||`-fallback-chain pattern reading
      `accepted_scientific_name || ... direct_scientific_name || ...`, ending in a final fallback
      expression that itself references `scientificName` (Pl@ntNet's own raw field) — mirroring the
      already-shipped, already-confirmed Korean-name chain
      (`ktsnMatch.accepted_korean_name || ktsnMatch.direct_korean_name || null`) this codebase
      already uses in `qpbHandlePlantNetResponse`/`qpbSelectCandidate`, but with a non-`null` final
      fallback (Pl@ntNet has no Korean-name-equivalent field to fall back to, but does have its own
      raw scientific name). **Disclosed limitation:** a single regex match against the whole file
      cannot, by itself, confirm this exact chain is what is actually assigned to *both* the
      candidate-card display property *and* the value passed to the selection-persistence call
      (FR-QPB-109's own "both... must use" requirement) — only that the chain exists at least once
      somewhere in the generated source. This mirrors this file's own established, disclosed
      precedent for similarly loose checks (e.g. note 11's `uuid`-check, note 12/13's own
      heuristic-identification notes).
    - `test_ac099_no_direct_match_branch_is_structurally_unchanged_no_direct_scientific_name_
      constructed` (element (3)) — the loosest check in this section: confirms only that the
      existing, literal "KTSN match not found" disclosure text still appears verbatim somewhere in
      the generated source (i.e. this entry did not remove or reword it). It does **not**, and
      cannot, trace the no-match branch's own control flow to confirm no `direct_scientific_name`
      value is constructed *specifically within that branch* — a stronger claim than a static-text
      check can support without executing the QML.

    **Confirmed by an actual test run performed during this test-design round**
    (`.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_symbol_styling.py
    tests/acceptance/qfield_project_builder/test_ktsn_lookup_table.py
    tests/acceptance/qfield_project_builder/test_post_mvp_identification_plugin.py
    tests/acceptance/qfield_project_builder/test_post_mvp_ktsn_matching.py
    tests/acceptance/qfield_project_builder/test_qgis_project_config.py -q`): 6 of the 9
    `test_ac099_*` invocations (elements 1/2 above) **FAIL**, exactly as expected for a
    not-yet-implemented mechanism — a direct inspection of `qfield_builder/qml_plugin.py` during
    this round confirmed
    `qpbMatchKtsn`/`qpbHandlePlantNetResponse`/`qpbSelectCandidate` construct no
    `direct_scientific_name` value of any kind. The remaining 3 invocations (element 3,
    `test_ac099_no_match_branch_unchanged_no_direct_scientific_name_constructed`) legitimately
    **PASS** already — see this file's own module-level 2026-08-26/D-60/D-64 addendum for why.
    See that same addendum at the top of this file for the combined run's full pass/fail/skip
    counts (which also include
    the separate D-65/D-66/D-67/D-68 rounds' own new tests).

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **FR-QPB-109's "identification timestamp/API-model version when available" has no defined
  schema column anywhere in the approved specification.** Section 7/8 (the common GeoPackage rules
  and the Type 1/2/3 survey schemas) define `selected_korean_name`, `selected_scientific_name`,
  `selected_ktsn`, `identification_score`, `occurrence_probability`, and `identification_status` as
  the full set of Pl@ntNet-related columns — no `identification_timestamp` or
  `api_model_version`-equivalent column is defined anywhere (confirmed by a full read of Sections
  7, 8.1–8.3, and a targeted search of the whole specification for "timestamp"/"model version").
  FR-QPB-109 nonetheless requires persisting this information "when available." This is a genuine
  specification omission, not a test-design ambiguity: there is no schema column to assert a value
  was written to. No test invents one. This is recorded as `test_post_mvp_manual_qfield_runtime.py::
  test_fr109_timestamp_and_model_version_persistence_not_testable_pending_schema_clarification`
  (skipped, with the gap explained in its skip reason) so the gap remains individually traceable
  to FR-QPB-109 rather than silently dropped. **This would need a spec-writer pass (a new/revised
  DR item defining the storage column(s)) before an implementer or reviewer could treat FR-QPB-109
  as fully specified.**
- **`correct_list` with more than one candidate entry is unspecified.** A full scan of the real,
  full KTSN CSV performed during test design found ~402 rows (of ~212,397) whose `correct_list` is
  a JSON array with *more than one* entry, each a distinct candidate accepted taxon with its own,
  different `KTSN` value (e.g. KTSN `120000114118` "Ascotis selenaria dianaria" resolves to *two*
  candidates: `120000033289` "Ascotis selenaria"/"네눈쑥가지나방" and `120000033288`
  "Ascotis imparata"/"남방네눈쑥가지나방"). FR-QPB-107's text describes reading a single scalar
  `KTSN` value from "the JSON `KTSN` field," with an explicit rule only for the `KTSN`-vs-`KTNS`
  *key*-name conflict within one object — it does not say which array *entry* is canonical when
  several genuinely different candidate objects are present. This is not a rare corner case (≈0.2%
  of the full CSV, i.e. potentially many real species) and materially affects behavior, so it is
  not guessed at here. `match_ktsn()`'s behavior for a multi-entry `correct_list` is left
  completely untested and unspecified by these tests — see HARNESS_CONTRACT.md function 9's
  matching "known, deliberately-uncovered specification gap" note. **This would need a
  spec-writer/stakeholder decision (which entry is canonical — first entry? all entries surfaced
  as multiple accepted-name candidates? flagged ambiguous like the `KTSN`/`KTNS` case?) before an
  implementer could treat FR-QPB-107 as fully specified for this case.**
- **AC-QPB-070's exact QGIS editor-widget-type-ID string could not be independently confirmed** —
  see automation note 1 above. This did not block test design (the check was restructured around
  a PyQGIS-backed harness function instead of a hardcoded literal), but the implementer should
  confirm the true registered ID against a live QGIS/PyQGIS session (which this test-designer role
  is barred from doing itself) when implementing `inspect_identification_widget`.
- **FR-QPB-039's Pl@ntNet-API-key request/validation workflow is not covered by this round.** It
  is Section 6.5 (MVP-scoped) UI/workflow behavior, not itself a Section 13 artifact-generation or
  pure-rule criterion, and is not one of the FR/AC IDs this round's task scope named. Not tested
  here; flagged so its absence is not mistaken for an oversight.
- **Decision Log D-46's disclosed QGIS-Desktop widget-load failure vs. AC-QPB-001 (MVP, unrevised)
  — non-blocking, not resolved here.** D-46 discloses that the embedded `QML Widget` is expected to
  fail to *load/render* at all in QGIS Desktop once FR-QPB-101's corrected `QfFileUtils`-based
  file-read mechanism is adopted, and AC-QPB-070 (further revised) is scoped to no longer require or
  assert QGIS-Desktop rendering success. D-46 does not, however, state whether that same load
  failure escalates into a project-level "repair"/error warning of the kind the still-unrevised,
  still-in-force AC-QPB-001 requires be absent for "a generated project for any of the four survey
  types" — AC-QPB-001's own wording carries no identification-enabled carve-out. This is a genuine,
  currently-unconfirmed interaction between a post-MVP mechanism change and an MVP criterion, not a
  test-design ambiguity being silently resolved: no test asserts an outcome for it. A documented
  `manual`-marked, skipped placeholder test was added instead (see automation note 6 above and
  `test_post_mvp_identification_plugin.py::test_qgis_desktop_repair_warning_status_when_qml_widget_fails_to_load_not_yet_confirmed`)
  so this open question remains individually traceable rather than silently dropped. **If a future
  implementer or QA pass ever confirms a repair warning actually appears, that would be a concrete
  AC-QPB-001 finding for identification-enabled projects specifically and should be routed back
  through this project's normal defect-triage process, not treated as already covered by Decision
  Log D-46's disclosure (which only concerns the widget's own render failure, not any project-level
  escalation).**
- **AC-QPB-071 (further revised)/AC-QPB-083 (Decision Log D-47) — "`correct_list` values remaining
  valid JSON" does not literally hold for every row of the real source data, and the specification
  does not say what the extraction should do about that.** A full scan of the real, full
  212,397-data-row source CSV performed during this test-design round found 144,917 rows (~68%)
  whose `correct_list` value is an **empty string** — not itself valid JSON — with the remaining
  67,480 rows containing a genuinely valid JSON array (0 malformed values found, consistent with
  the earlier full-file scan recorded in note 2 above). Both FR-QPB-118 and AC-QPB-071 (further
  revised)/AC-QPB-083 state that extracted `correct_list` values must "remain valid JSON," without
  addressing this empty-string case at all — FR-QPB-118's own "does not alter, reformat, or
  revalidate the values within the columns it does carry forward beyond what FR-QPB-105 already
  requires" is the most literal available instruction, but it does not, by itself, resolve whether
  an empty-string source value must (a) pass through unchanged (i.e., an empty string, which is not
  itself valid JSON), or (b) be normalized into some valid-JSON representation (e.g. an empty
  array `[]`) during extraction. Rather than silently inventing either behavior, these tests assert
  only the reading that is directly stated in FR-QPB-118's own text — the value is carried through
  **verbatim**, and is checked for JSON validity **only when the source value is itself non-empty**
  (see `test_post_mvp_reference_bundling.py`'s module docstring and
  `test_ac083_extraction_preserves_ktsn_as_string_and_correct_list_as_valid_json`, which uses a
  fixture deliberately containing one row of each kind). **This would need a spec-writer/
  stakeholder clarification (does an empty-string source value require special-casing during
  extraction, or is "remaining valid JSON" only ever a claim about rows where the source already
  has a value?) before an implementer or reviewer could treat this specific edge case as fully
  specified** — until then, this test suite does not assert either normalization behavior for the
  empty-string case, only pass-through-unchanged.
- **Step 3's literal seven-value phylum match vs. a real-data quote-character artifact (Decision
  Log D-48/AC-QPB-087/AC-QPB-083/AC-QPB-071) — the specification's own literal wording and its own
  cited ground-truth count are in tension for a small, real edge case.** Independent verification
  performed during this round (a full pass over the real, full 212,397-row source CSV) found that
  a small number of rows — an apparent upstream data-serialization artifact affecting every field
  of those specific rows, not only `r200_nm` — carry a literal, stray *extra* pair of double-quote
  characters around their values (e.g. the raw field content is the 3-quote-character sequence
  that Python's own standard `csv` module correctly, unambiguously parses as the literal string
  `"Magnoliophyta"`, quote characters included, rather than `Magnoliophyta`). Two such rows are
  otherwise-`Magnoliophyta` (allowlisted) rows that survive Steps 1-2. FR-QPB-118's Step 3 text
  states only a literal, exact match against the seven allowlisted phylum values, with **no**
  normalization rule of any kind for this artifact (unlike Step 4's explicit `<em>`-tag-stripping/
  whitespace-collapsing normalization rule for `taxon_full_nm`) — yet Decision Log D-48's own
  cited Step 3 ground truth (26,763 -> **21,025**) is only reproducible if these 2 rows are still
  counted as matching `Magnoliophyta`; a strictly literal reading of Step 3's prose alone would
  exclude them, yielding 21,023, not 21,025. This is a genuine, real tension between the
  specification's own prose and its own cited numeric ground truth, not a test-design ambiguity
  being silently resolved: no test in this round asserts *how* an implementation must normalize
  this artifact (e.g. stripping stray leading/trailing quote characters in addition to whitespace
  before the Step 3 comparison). Instead, per the ambiguity-handling procedure: (a) the real-fixture
  `test_ac087_step3_real_full_csv_produces_exactly_21025_survivors` and the real, full end-to-end
  `test_ac071_full_real_reference_dataset_extraction_and_raster_bundling`/
  `test_ac086_step4_real_full_csv_and_xlsx_produces_exactly_20914_survivors` tests assert the
  specification's own explicitly cited final counts (21,025/20,914) as ground truth, since the task
  that authorized this round explicitly stated these are already-orchestrator-verified facts to
  test against, not values for the test-designer to derive or second-guess; and (b) the synthetic
  Step 3 fixture (`ktsn_pipeline_step3_synthetic.csv`) deliberately uses clean, unquoted phylum
  values throughout, so `test_ac087_step3_synthetic_phylum_allowlist_edge_cases` does not depend on
  this specific ambiguity at all. **This would need a spec-writer/stakeholder clarification (should
  Step 3's `r200_nm` comparison strip stray quote characters, or some other normalization, before
  matching against the seven-value allowlist?) before an implementer could treat Step 3's own
  literal-match wording as fully, unambiguously specified for this edge case** — until then, no
  test in this round asserts a specific normalization mechanism, only the specification's own cited
  final counts.
- **FR-QPB-118 (further revised, Decision Log D-48)'s Step 4 NIBR-xlsx-missing/malformed
  failure-handling text has no dedicated acceptance test in this round.** FR-QPB-118's own body
  text states that Step 4 must fail the build early, with a clear message, if the NIBR xlsx
  workbook is missing, or its `관속식물류` sheet is missing, or that sheet lacks a `학명`/`KTSN`
  column — mirroring the same fail-early discipline already established for FR-QPB-105's CSV
  validation. No AC-QPB-### number in this round's assigned task scope (AC-QPB-071/083/084/085/
  086/087) names this specific failure mode, so no dedicated test asserting it was added here; the
  existing FR-QPB-105-driven early-failure tests continue to cover only the source-CSV's own
  missing/malformed-column failure paths, which occur before Step 4 would ever run. This is not a
  silently-invented resolution of an ambiguity — the FR's own text is clear about what should
  happen — it is simply outside this round's assigned scope, flagged here (mirroring this file's
  own established practice, e.g. note 8 above for AC-QPB-077) so it is not mistaken for something
  this round was supposed to close. A future round adding a dedicated test for this failure mode
  would mirror the existing `test_fr105_missing_reference_csv_fails_build_early_with_a_clear_message`/
  `test_ac083_missing_source_csv_fails_early_with_no_partial_project_or_lookup_file` pattern, using
  a `_test_reference_data_dir` fixture whose `tables/2025년 국가생물종목록_v1.0.xlsx` is absent or
  malformed while its KTSN CSV is otherwise valid.
- **FR-QPB-109 (further revised; Decision Log D-50)'s "pending write-back request" text does not
  specify whether a single request carries one field/value pair or several — this round's tests
  deliberately do not assert a specific payload shape.** The specification's own text describes
  the request as carrying "the current feature's own UUID..., the target attribute field name, and
  the value to write" (singular "field name"/"value"), and Decision Log D-50's confirmed-finding
  text likewise describes `changeAttribute(name, value)` — QField's own real API — as taking a
  single name/value pair. However, a real candidate selection (or manual entry) must persist
  *several* columns at once (`selected_korean_name`, `selected_scientific_name`, `selected_ktsn`,
  `identification_score`, `occurrence_probability`, `identification_status`,
  `identification_timestamp`, `identification_model_version`) — the specification's text does not
  say whether this means several separate pending-request files/writes (one per field), a single
  request whose "value" is itself a structured value (e.g. a JSON object/array of name-value
  pairs) that the plugin then loops over calling `changeAttribute()` once per entry, or some other
  shape. This is not resolved here: none of the `test_fr109_*` tests assert a specific request-file
  format/schema, a specific number of `FileUtils.writeFileContent()` call sites, or a specific
  number of `changeAttribute()` calls per applied request — they assert only that these named API
  calls are present somewhere, which is compatible with any of the above shapes. Silently choosing
  one specific shape to assert against would have invented behavior the specification does not
  actually define. **This would benefit from an implementer's own documented design choice (which
  the reviewer can then check for internal consistency), or, if the stakeholder has a preference,
  a spec-writer clarification — but it does not block implementation, since any shape satisfying
  the named API calls and the observable end-to-end persistence outcome (AC-QPB-046(a), confirmed
  via manual/device QA) would satisfy this specification as written.**
- **Whether the confirmed mechanism is actually wired to *both* required trigger points (real
  candidate selection and manual-entry confirmation, per Decision Log D-51) cannot be proven by a
  static-source-text check, and is not claimed to be proven here.** See automation note 11 above
  (points (b)/(c)) for the full reasoning. The `test_fr109_*` tests can confirm the *named
  constituent API calls exist somewhere* in the generated source; they cannot confirm those calls
  are correctly connected to each other, or that both the candidate-selection and manual-entry code
  paths actually reach the write-back call (as opposed to, say, only one of the two paths being
  wired up while the other silently falls back to the old, broken mechanism or does nothing). This
  residual confirmation is exactly what `test_ac046a_brand_new_unsaved_feature_write_back_persists_
  for_candidate_selection_and_manual_entry`'s manual QA steps require a human tester to exercise
  for *both* sub-cases explicitly, precisely because the automated structural check cannot.
- **AC-QPB-088 (Decision Log D-52) — "the original attachment file's own path" is not a
  spec-named identifier, so structurally distinguishing it from the new temporary file's own path
  is a disclosed heuristic, not a proof.** Neither FR-QPB-101 (further revised; Decision Log D-52)
  nor AC-QPB-088 itself names a specific variable/identifier for either the original attachment
  path or the new temporary file's path (unlike, e.g., FR-QPB-109's spec-quoted
  `overlayFeatureFormDrawer`/`changeAttribute`, which are real QField API names). The
  `test_ac088_*` tests therefore identify "the temporary file's own path" unambiguously (anchored
  on the literal, spec-mandated `1280` argument to `restrictImageSize()`), but can only identify
  "the original attachment file's own path" via a scoped, best-effort textual heuristic (see
  automation note 12 above for the full mechanism). This heuristic is deliberately scoped to the
  smallest enclosing JavaScript function specifically to avoid a real, confirmed collision risk
  with this codebase's own already-shipped, wholly unrelated `FileUtils.readFileContent()` calls
  for bundled reference-data reads (the KTSN lookup CSV, the national accepted-taxa list, the
  pending write-back request) — several of which are also confirmed, by inspection, to use the
  identical local variable name `absPath`, following this codebase's own established naming
  convention. Even with that scoping, a hypothetical, otherwise-correct implementation that reuses
  and reassigns one single local variable name for both the original attachment path and the
  temporary file's path, within the very same JavaScript function, would not be structurally
  distinguishable — by this or any purely textual, non-executing check — from an incorrect
  implementation that resizes the original attachment file in place (the very defect AC-QPB-088
  exists to catch). This is not a test-design ambiguity being silently resolved: the specification
  itself simply does not define any naming convention that would let a static check
  unambiguously identify which is which in every conceivable implementation shape, and no test in
  this round asserts more than what this heuristic can actually support. **This does not block
  implementation** — an implementer using two distinctly-named local variables (a natural,
  minimal-diff continuation of this codebase's own existing style, e.g. `qpbReadFileBytes`'s
  existing `absPath` for the original read, plus a newly introduced, differently-named local for
  the temporary copy) would be correctly, positively confirmed by these tests; only a
  same-variable-reuse implementation shape would evade this specific check, and that shape's
  actual correctness would then depend entirely on manual/`device` QA (mirroring this file's
  existing convention for confirming end-to-end runtime behavior no structural check can prove).
- **AC-QPB-095 (Decision Log D-54) — several structural checks rely on disclosed heuristics, not
  proofs, for the same underlying reason as the AC-QPB-088 entry immediately above: neither
  FR-QPB-109 nor AC-QPB-095 names a specific QML component/variable/identifier for most of what
  these checks must locate.** Specifically: (a) the `modelData` anchor used to mean "bound to this
  specific candidate" assumes the natural `Repeater`/`ListView`-delegate QML idiom (and the fact
  that this widget's own pre-existing, unrelated candidate-card content already uses exactly this
  idiom) — an equally spec-conformant implementation using some other per-item mechanism (e.g.
  index-based `Repeater.itemAt(i)` access instead of a delegate's own `modelData`) would not be
  detected; (b) the "small (`s`) size-variant" check is a whole-file heuristic anchored on a
  `url`-named identifier followed by a `.s`/`["s"]` accessor — it cannot prove this specific access
  is what actually feeds the Image element's `source` property, only that some code somewhere
  selects the `s` variant; (c) the graceful-degradation and image-load-failure-isolation checks can
  only detect the *presence* of a conditional/error-handling construct, never confirm it is
  logically correct or that it actually leaves the rest of the candidate's display untouched at
  runtime. None of this is a test-design ambiguity being silently resolved — AC-QPB-095's own text
  is unambiguous about *what* must be true (an Image element bound to the small-variant URL per
  candidate; combined attribution; graceful degradation), it simply does not name specific
  identifiers a static check could match on with certainty, mirroring the AC-QPB-088 entry's
  identical situation immediately above. **This does not block implementation** — an implementer
  following this widget's own existing candidate-card conventions (a `modelData`-bound `Repeater`
  delegate; a `visible:` guard mirroring the existing `warning_text` pattern) would be correctly,
  positively confirmed by these tests; only a materially different, but still spec-conformant,
  implementation shape could evade one or more of these specific checks, and that shape's actual
  correctness would then depend on AC-QPB-096's own manual/`device` QA (which does not depend on
  any of these heuristics).
- **The literal JSON field name for Pl@ntNet's own "related-images list" is not stated by the
  specification's text — a residual, non-blocking gap distinct from what AC-QPB-094/095/096
  actually require.** Decision Log D-54's own text states that each `results[*]` entry "gains a
  related-images list whose entries carry `organ`, `author`, `license`, `date`, and `citation`
  fields, plus a `url` object with `o`/`m`/`s` size-variant URLs," but — unlike
  `species.scientificNameWithoutAuthor` (Decision Log D-37, live-confirmed against the real API by
  a prior test-designer round) — no literal JSON key name is given for the related-images list
  field itself (e.g. whether it is `images`, `relatedImages`, or something else on each `results[*]`
  entry), and this round performed no fresh live network call against the real Pl@ntNet API with
  `include-related-images=true` to confirm it empirically (Decision Log D-54's own confirmed
  findings are the orchestrator's direct documentation research, not a test-designer live
  verification, unlike the base identify-response schema's own D-37 live-verification precedent).
  This does not block any test in this round: AC-QPB-094 concerns only the outgoing request's query
  parameters (unaffected), and AC-QPB-095 concerns only the generated QML's *structural* display
  mechanism (an `Image` element, attribution text, guards) — none of which requires knowing the
  exact response-field name the widget's own JavaScript must parse to populate `modelData`. **This
  would benefit from a future live-network-verification round** (mirroring
  `test_plantnet_live_endpoint_authenticates_and_returns_the_confirmed_schema`'s own precedent, once
  a real Pl@ntNet account/photo combination confirmed to actually return related images is
  available) **before an implementer's own response-parsing code choice could be checked against a
  live-confirmed field name** — until then, no test in this round asserts a specific JSON key for
  this list, and the implementer is free to choose any reasonable field name consistent with
  Pl@ntNet's real (if not yet test-designer-live-confirmed-in-this-round) response shape.
- **Pre-existing, harmless test-name/AC-number mismatch noticed (not introduced) by this round —
  `test_ac106_direct_match_already_accepted_needs_no_further_resolution` in
  `test_post_mvp_ktsn_matching.py`.** This 2026-08-15-era test (predating Decision Log D-66, which
  is where the specification first assigns `AC-QPB-106` to anything at all — confirmed by a full
  search of the approved specification's own text) is functionally an `AC-QPB-042`-family test (it
  sits directly under that section's own `# --- FR-QPB-107 / AC-QPB-042 ...` header and asserts
  exactly the "already-accepted direct match needs no further `correct_list` resolution" rule that
  section's other tests already cover) — its `test_ac106_...` name appears to be a pre-existing
  authoring artifact from before `AC-QPB-106` existed as a real, assigned criterion at all, not a
  reference to this round's own new, unrelated `AC-QPB-106` (the bundled lookup table's index,
  `qfield_project_builder_ktsn_lookup_table.traceability.md`). No functional collision exists (this
  round's own new `AC-QPB-106` test,
  `test_ktsn_lookup_table.py::test_ac106_bundled_lookup_table_has_a_real_index_on_korean_and_
  scientific_name_columns`, lives in a different file/module, so there is no Python name collision
  either), but the coincidence is flagged here rather than silently left for a future reader to
  puzzle over. This is out of this round's own assigned scope to fix (renaming an
  already-approved, already-committed test from a prior round is not something this round's own
  task authorized), and is not touched here.

## Live-verification disclosure (Pl@ntNet, Decision Log D-32/Open Question O-14)

During test design, the real Pl@ntNet API was queried directly (using the real key already present
locally in the gitignored `.env` as `QPB_TEST_PLANTNET_API_KEY`, exactly mirroring the existing
`QPB_TEST_VWORLD_API_KEY` convention) to confirm the request/response contract before writing
assertions against it, rather than guessing. **The literal key value was never written into any
file in this repository, at any point** — only the environment-variable name is referenced, in
test code and in this document. See `test_post_mvp_plantnet_request_shape.py`'s module docstring
and HARNESS_CONTRACT.md function 8 for the confirmed endpoint/auth-scheme/schema details this
unblocked.
