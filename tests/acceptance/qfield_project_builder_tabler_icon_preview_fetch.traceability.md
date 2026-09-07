# Traceability Matrix — QField Project Builder, Live Tabler Icon Preview-Fetch During Search (Wizard Step 6)

> Specification: `specs/qfield-project-builder.md` — Decision Log **D-76** (the stakeholder's
> explicit choice of Decision Log D-72's disclosed option (b), "live per-result SVG fetch during
> search"); revised `FR-QPB-011(d)` (Section 5.4, new clause `(d)(ii)`); revised `NFR-QPB-080`
> (Section 5.4, new clauses (5)-(8)); `AC-QPB-101` (Section 18.2, annotated, not altered in
> substance); new `AC-QPB-117` (Section 18.2).
>
> This is a **later, separate `test-designer` round against the same overall specification** as
> `qfield_project_builder_symbol_styling.traceability.md` (the Decision Log D-61/D-65 baseline for
> this same wizard Step 6 feature), recorded as its own file per this project's established
> convention (see `tests/acceptance/README.md`), so that already-approved traceability record is
> not touched by this round's additions.
>
> Tests: `tests/acceptance/qfield_project_builder/test_tabler_icon_preview_fetch.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (Decision Log D-76)" section (new function 20, `fetch_tabler_icon_preview_svgs`), and its
> extended "what these tests deliberately do not invent" list.

## What D-76 actually decided (read this first — not re-decided here)

Decision Log D-76 supersedes one specific clause of the already-approved, offline-only-search rule
(Decision Log D-65): `FR-QPB-011(d)`'s prior "this clause never authorizes any live
search/autocomplete network request... searching the bundled icon-name index is always offline"
sentence is struck through (not deleted) and superseded, **narrowly**, for one new case only — a
second, independently scoped, additional network-fetch trigger, `(d)(ii)`: fetching preview SVG
content, live, for the currently visible/matched results of an in-progress Step 6 search,
debounced as the user types. This is genuinely additive:

- The client-side name-filtering/search mechanism itself (`search_bundled_tabler_icon_names`,
  FR-QPB-121) remains entirely offline and unchanged.
- The pre-existing fetch-on-selection mechanism (`(d)(i)`, FR-QPB-121/AC-QPB-101) remains
  completely unaffected — a user's final icon selection still triggers its own single fetch
  exactly as before, regardless of whether a preview for that icon was already fetched during
  search.
- The new `(d)(ii)` permission is strictly bounded: never an unbounded background prefetch of the
  entire ~5,130-name bundled index; never for a result not currently rendered on screen.
- `NFR-QPB-080` gains new clauses (5)-(8): (5) the same compliant `User-Agent` header the existing
  selection-fetch request already carries; (6) debouncing (not on every keystroke); (7) bounded,
  reasonable concurrency (never one unbounded simultaneous request per visible result); (8) —
  critically — graceful degradation: search-by-name and selection-by-name must remain fully
  functional with zero network access at all times, and a missing/failed preview must simply show
  no image for that one result, never blocking search, never blocking selection, never crashing.

This round's job is to test this already-decided, already-approved requirement text — not to
re-litigate Decision Log D-72's own four-option investigation or D-76's choice among them.

## Genuinely out of this harness's reach, not silently claimed as covered

This feature is, at its operational core, live keystroke-driven PySide6 UI behavior with real
debounce timing and real concurrency bounding — a structurally different class of fact than a
`build_project()`-generated project artifact or a pure, GUI-independent logic function. Mirroring
this suite's own now-repeatedly-established precedent (`qfield_project_builder_credential_storage_
mechanism.traceability.md`; `qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_
gaps.traceability.md`; `qfield_project_builder_app_rename_version_and_branding.traceability.md`) —
even a fact that is, in principle, offscreen-automatable is routed to `tests/unit/`, not authored
directly here, when what is actually being asserted is "the PySide6 wizard's own code structure /
real HTTP-client construction," not a generated-project artifact or a pure logic function:

1. **NFR-QPB-080(5) — the new preview-fetch request's own compliant `User-Agent` header.** Exactly
   the same class of criterion as `AC-QPB-102`'s already-established, pre-existing determination
   for the sibling selection-fetch request (`qfield_project_builder_symbol_styling.traceability.
   md`'s "genuinely out of this harness's reach," item 1): an internal HTTP-client-construction
   detail, not a generated-project artifact, and this suite has no established mechanism anywhere
   (VWorld, OSM, Pl@ntNet, or the existing Tabler selection-fetch) for asserting on an outgoing
   HTTP request's own header construction from within a black-box acceptance test. Routed to
   `tests/unit/` in full (see the routed contract table below).
2. **NFR-QPB-080(6) — real debounce-as-you-type timing.** Inherently a PySide6 `QTimer`/keystroke-
   event fact ("a fetch must not be issued on every keystroke, only after the user's input has
   briefly settled") — not reachable without actually driving the real widget's real event loop.
   Routed to `tests/unit/` in full.
3. **NFR-QPB-080(7) — real bounded concurrency of in-flight HTTP requests.** A synchronous fake
   double (the only kind this harness's black-box, deterministic-test convention uses anywhere —
   see `qfield_project_builder_symbol_styling.traceability.md`'s own "fake-double-only, never a
   real mode" design-choice note for the sibling selection-fetch) has no meaningful way to
   demonstrate *real* concurrent HTTP dispatch; a thread-pool/async-task bound is only observable
   against a real, non-fake dispatch mechanism. Routed to `tests/unit/` in full.
4. **The literal, on-screen fact that a preview image actually renders next to a search result
   once a fetch succeeds.** A PySide6-rendering fact, not a generated-project artifact and not a
   pure logic function — mirrors the already-established `AC-QPB-104` wizard-step-sequencing
   precedent exactly. A `manual`-marked, skipped placeholder is added instead
   (`test_preview_images_actually_render_next_to_visible_search_results_as_the_user_types`).

**What is, deliberately, covered here, and why it is a principled distinction rather than a
loophole.** The one part of this new fetch trigger that genuinely is "a pure, GUI-independent
logic function" — mirroring `search_bundled_tabler_icon_names`'s own established precedent exactly
— is: *given a set of currently visible/matched icon names (already narrowed and already
debounced by the caller), fetch each one's preview, degrading gracefully per name on failure,
never expanding beyond the given set.* That contract does not depend on PySide6, on real network
timing, or on real thread/async concurrency to test meaningfully — it is exposed headlessly via
new function 20, `fetch_tabler_icon_preview_svgs`, and *is* tested directly here, exactly the way
`search_bundled_tabler_icon_names` (function 14) already is.

## What this round deliberately does NOT re-test (confirmed unaffected instead)

Per the task's own instruction to confirm rather than redundantly re-test already-covered ground:

- **The offline name-search mechanism itself (`AC-QPB-101`'s first clause, `FR-QPB-121`)** is
  unaffected by Decision Log D-76 and remains fully covered by the already-committed,
  already-passing `test_symbol_styling.py::test_search_bundled_tabler_icon_names_*` tests. This
  round does not duplicate those tests; it does, however, add one new test
  (`test_search_by_name_is_unaffected_by_a_fully_failed_preview_fetch_batch`) that positively
  demonstrates the *interaction* case Decision Log D-76 newly introduces — search called again
  immediately after a batch of visible results' preview fetches all failed — which the pre-existing
  D-65-era tests could not have covered (the preview-fetch mechanism did not exist yet when they
  were written).
- **The fetch-on-selection mechanism (`AC-QPB-101`'s second/third clauses, `FR-QPB-011(d)(i)`)**
  is completely unaffected by Decision Log D-76 (confirmed directly by the specification text
  itself: "this entry does not change... the final SVG fetch-on-selection mechanism... which
  remains exactly as Decision Log D-65 approved it") and remains fully covered by the
  already-committed, already-passing `test_symbol_styling.py::test_ac101_*` tests
  (`test_ac101_successful_selection_embeds_the_svg_and_every_point_layer_uses_it`,
  `::test_ac101_embedded_svg_is_referenced_by_a_project_relative_path_inside_the_output_folder`,
  `::test_ac101_failed_fetch_falls_back_to_the_minimalist_default_without_blocking_generation`).
  This round adds no new test that duplicates them, and instead adds one new, narrowly scoped test
  (`test_selection_fetch_mechanism_is_a_structurally_separate_config_from_preview_fetch`)
  confirming, from the *new* preview-fetch function's own side, that its return contract shares no
  key or state with `build_project()`'s own `symbol_styling.tabler_svg_fetch` selection-fetch
  config — i.e. that the two mechanisms cannot cross-contaminate each other by construction.
- **`AC-QPB-102`'s existing "no attribution/license notice anywhere in the generated project"
  half** is unaffected (NFR-QPB-080's clause (3) removal is untouched by this entry) and remains
  covered by the existing `test_symbol_styling.py::test_ac102_no_attribution_or_license_notice_
  appears_anywhere_in_the_generated_project`. Not re-tested here.

## Traceability table

| ID | Summary | Test(s) | Automation |
|---|---|---|---|
| FR-QPB-011(d)(ii) — never expands beyond the given visible/matched names | The preview-fetch reference function's own fetch scope never silently expands beyond exactly the names it was given (never an unbounded prefetch of the full ~5,130-name index; never for a name not currently visible) | `test_tabler_icon_preview_fetch.py::test_preview_fetch_reports_exactly_the_given_names_never_more_never_fewer`, `::test_preview_fetch_never_expands_to_the_rest_of_the_bundled_index` | auto (new function 20) |
| NFR-QPB-080(8) / AC-QPB-117 — graceful, non-crashing, non-blocking degradation on failure | Every given name is still reported (never raises, never omits) when some or all previews fail; a failed preview shows `success: False`/`svg_content: None` for that one result only | `test_tabler_icon_preview_fetch.py::test_preview_fetch_all_results_failing_never_raises_and_shows_no_image_for_every_result` (parametrized: network_error/http_error/timeout), `::test_preview_fetch_gracefully_degrades_one_failing_result_without_affecting_its_siblings` | auto (new function 20) |
| AC-QPB-117 — search-by-name remains fully functional regardless of preview outcome | The offline name-search mechanism (`search_bundled_tabler_icon_names`, unaffected by this entry) still works, and returns the identical match set, even after a batch of visible results' preview fetches all failed | `test_tabler_icon_preview_fetch.py::test_search_by_name_is_unaffected_by_a_fully_failed_preview_fetch_batch` | auto |
| AC-QPB-117 — success-path preview reporting (needed as a positive control for the failure-path tests above) | On success, every given name's preview reports `success: True` and the expected SVG content | `test_tabler_icon_preview_fetch.py::test_preview_fetch_reports_svg_content_for_every_name_on_success` | auto (new function 20) |
| AC-QPB-101 (unaffected; annotated, not altered in substance, by D-76) — fetch-on-selection mechanism completely unaffected | The pre-existing selection-fetch mechanism shares no return key/state with the new preview-fetch function; cannot be cross-contaminated by it | `test_tabler_icon_preview_fetch.py::test_selection_fetch_mechanism_is_a_structurally_separate_config_from_preview_fetch` (new, narrowly scoped) — the mechanism itself remains covered, unmodified, by the already-committed `test_symbol_styling.py::test_ac101_*` tests (see "What this round deliberately does NOT re-test" above) | auto |
| NFR-QPB-080(5) — compliant `User-Agent` header on the preview-fetch request | *(no test in this round — see routed contract table below)* | **routed to `tests/unit/test_symbol_styling.py`**, not yet written |
| NFR-QPB-080(6) — debounced, not fired on every keystroke | *(no test in this round — see routed contract table below)* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| NFR-QPB-080(7) — bounded, reasonable real concurrency of in-flight requests | *(no test in this round — see routed contract table below)* | **routed to `tests/unit/test_wizard.py`** (and/or `tests/unit/test_symbol_styling.py`, depending on where the implementer places the real dispatch mechanism), not yet written |
| AC-QPB-117 (the genuinely visual half — a preview image actually renders on screen) | *(manual placeholder)* | `test_tabler_icon_preview_fetch.py::test_preview_images_actually_render_next_to_visible_search_results_as_the_user_types` | **manual** (documented, skipped) |

Every criterion this round was asked to cover (`FR-QPB-011(d)(ii)`, `NFR-QPB-080` clauses (5)-(8),
`AC-QPB-117`, and confirmation that `AC-QPB-101`/the offline half of `FR-QPB-121` are unaffected)
appears above, mapped to either a real automated test, a `manual`-marked placeholder, or a fully
specified routed contract — nothing is silently dropped.

## Routed `tests/unit/` contract table (not authored by this round — `test-designer` may only
create/modify files under `tests/acceptance/`)

The following is a precise specification of what a future `implementer`-authored
`tests/unit/test_wizard.py`/`tests/unit/test_symbol_styling.py` round must satisfy for the *actual*
debounce/concurrency/User-Agent/graceful-degradation mechanism wired into the real
`SymbolStylingPage` widget and its real, production preview-fetch dispatch code. This table
specifies the required **behavior**, not an exact internal API — mirroring this project's own
established convention of leaving exact implementation-level naming/mechanism to the implementer
where the specification itself does not dictate one (e.g. Decision Log D-27/D-75, and this exact
file's sibling round's own "Illustrative-only naming note" in `qfield_project_builder_app_rename_
version_and_branding.traceability.md`).

| Requirement | Summary | Exact assertions a future `tests/unit/`-level test must satisfy |
|---|---|---|
| NFR-QPB-080(6) — debounced | A preview fetch must not be issued on every keystroke; only after the user's input has briefly settled. The exact debounce interval is an implementation detail, not dictated by the specification. | Construct the real `SymbolStylingPage` under an offscreen `QApplication`; simulate several rapid, successive `search_edit` text changes within a short window (e.g. via repeated `setText()`/`textChanged` emission, or `QTest.keyClicks`); assert the real preview-fetch dispatch mechanism (whatever function/method the implementer wires to it) is invoked at most once for that rapid burst, only after the burst stops and some settle interval elapses — not once per individual text change. A `QSignalSpy`-style call-count assertion, or a monkeypatched stand-in for the real dispatch call, is an acceptable mechanism; the exact debounce interval value itself must not be hardcoded as a required constant unless the implementer's own chosen value is being regression-tested against itself. |
| NFR-QPB-080(7) — bounded concurrency | Concurrency for in-flight preview fetches must be bounded to a small, reasonable number at any one time — never one unbounded, simultaneous request fired per every currently visible result at once. | Drive (or directly invoke) the real production dispatch mechanism with a large number of currently-visible names (e.g. 20+, matching this suite's own `_MAX_DISPLAYED_MATCHES = 100` UI cap in `SymbolStylingPage`) using a real or realistic concurrency-observable double (e.g. a fake HTTP layer that records the maximum number of simultaneously-open/in-flight calls via a counter guarded by a lock/semaphore, or inspecting a real bounded thread-pool's/async-semaphore's own configured max-worker value if the implementation exposes one); assert the observed (or configured) maximum concurrent in-flight count is small relative to the total number of visible names (e.g. strictly less than the total when the total is large) — never equal to firing all of them at once. |
| NFR-QPB-080(5) — compliant `User-Agent` header | Every preview-fetch request must carry the same compliant, identifying `User-Agent` header the existing selection-fetch request already uses (`qfield_builder.symbol_styling.TABLER_USER_AGENT` in the current, pre-D-76 codebase). | Confirm the real preview-fetch dispatch code path constructs its outgoing HTTP request(s) using the identical `TABLER_USER_AGENT` constant/value the existing `_http_get`/`fetch_tabler_icon_svg_real` functions already use (by direct code inspection and/or a unit test that intercepts the constructed `urllib.request.Request`/equivalent object and asserts its `User-Agent` header equals `TABLER_USER_AGENT`) — extending, not duplicating or diverging from, the existing constant. |
| NFR-QPB-080(8) / AC-QPB-117 — real, on-widget graceful degradation | Given the real `SymbolStylingPage`, when every preview fetch fails/is unavailable (simulated via a monkeypatched/injected failing dispatch function), the results list must still populate from `search_bundled_tabler_icon_names` exactly as before, remain selectable (`_on_icon_selected` still fires and updates `selected_tabler_icon_name()`), and no exception may propagate out of the text-changed handler or the Qt event loop. | Construct the real `SymbolStylingPage` under an offscreen `QApplication`; monkeypatch/inject a preview-fetch double that always fails (mirroring `fetch_tabler_icon_preview_svgs`'s own `network_error`/`http_error`/`timeout` fake modes at the acceptance level); type a query with real matches into `search_edit`; assert `results_list` still populates with the expected matches, selecting a result via the existing `results_list.setCurrentItem`/`currentTextChanged` mechanism still updates `selected_tabler_icon_name()`, and no unhandled exception is raised or logged as an unhandled Qt slot error during any of this. |

**Illustrative-only naming note:** none of the above mandates a specific new function/method name
(e.g. a plausible `SymbolStylingPage._on_preview_fetch_debounce_timeout`) or a specific concurrency
primitive (thread pool, `asyncio`, `QNetworkAccessManager`'s own built-in connection limits, or
otherwise) — only the input/output behavior above is required, mirroring this project's own
established convention (Decision Log D-27/D-75; this file's own sibling round's identical framing)
of leaving exact implementation-level mechanism to the implementer where the approved specification
text itself does not dictate one.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

None found in the approved requirement text itself (`FR-QPB-011(d)(ii)`, `NFR-QPB-080` clauses
(5)-(8), `AC-QPB-117`) — Decision Log D-76's own text is precise about scope (which fetch trigger
is added, what it must never do) and about which safeguards are required (User-Agent parity,
debouncing, bounded concurrency, graceful degradation), and explicitly defers exact debounce
interval/concurrency-bound values to implementer discretion, mirroring an established convention
this specification already uses elsewhere (Decision Log D-27/D-75) rather than leaving that
looseness unexplained. The determinations above (which parts are testable from
`tests/acceptance/`'s own black-box convention vs. routed to `tests/unit/`) are procedural
role/file-scope-boundary judgments, not ambiguities or gaps in the specification's own requirement
text — mirroring the identical distinction three prior rounds already drew for analogous
PySide6-widget-internal/HTTP-client-internal facts (see "Genuinely out of this harness's reach"
above for the specific precedents cited).

One genuinely new design choice this round made, recorded so a future round is not left guessing:
new function 20's fake-double config shape (`{"fake": {"default": {...}, "overrides": {name:
{...}}}}`) is this round's own invention — the approved specification text does not, and could not,
dictate a Python test-seam shape. It was designed to directly mirror the existing, established
`tabler_svg_fetch.fake` convention's `{"mode": ..., "svg_content": ...}` entry shape as closely as
possible while additionally supporting AC-QPB-117's explicit "per that one result" per-name
granularity requirement, which the existing single-fetch double (built for exactly one name at a
time) has no need to support. If a future round finds the real implementation's own natural
per-name fake-injection shape differs, that is an ordinary harness-contract refinement, not a
specification ambiguity.
