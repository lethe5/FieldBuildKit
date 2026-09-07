# Traceability Matrix — QField Project Builder, Symbol Styling Configuration (Wizard Step 6)

> Specification: `specs/qfield-project-builder.md`, Section 6.6/6.7, Section 9 (`FR-QPB-011`
> further revised/`FR-QPB-120`/`FR-QPB-121`/`FR-QPB-123`), Section 14.1 (`NFR-QPB-080`, revised),
> Section 18.2/18.5 (`AC-QPB-100`–`102`/`104`) — Decision Log D-61 (draft proposal) confirmed and
> completed by Decision Log D-65, closing Open Questions O-24–O-27.
>
> This is a **later, separate `test-designer` round against the same overall specification** as
> `qfield_project_builder.traceability.md` (the approved MVP baseline), recorded as its own file
> per this project's established convention (see `tests/acceptance/README.md`), so the
> already-approved MVP/post-MVP traceability records are not touched by this round's additions.
>
> Tests: `tests/acceptance/qfield_project_builder/test_symbol_styling.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (Decision Log D-64–D-69...)" section (functions 13–15: `fetch_tabler_icon_svg`,
> `search_bundled_tabler_icon_names`, `inspect_layer_renderer`; the `symbol_styling`
> `build_project` config/return additions).

## What this round covers, and what it deliberately does not

FR-QPB-011's own clause (d) (the new, single permitted Tabler network destination), FR-QPB-120
(minimalist default styling), FR-QPB-121 (Tabler icon search/download), FR-QPB-123 (the new wizard
Step 6), and NFR-QPB-080 (network safeguards) are all confirmed, non-provisional requirement text
as of Decision Log D-65 (2026-08-26). New AC-QPB-100–102/104 make this independently testable.

**Genuinely out of this harness's reach, not silently claimed as covered:**

1. **AC-QPB-102's "compliant `User-Agent` header / no automatic retry" clause.** This is an
   internal desktop-application HTTP-client-construction detail (does the single Tabler SVG-fetch
   request carry a specific header; does the calling code retry automatically on failure) — not a
   generated-project artifact this harness's black-box `build_project()`/`validate_project()`
   convention can reach, and this suite has no established mechanism anywhere (for VWorld, OSM, or
   Pl@ntNet) for asserting on an outgoing HTTP request's own header/retry construction from within
   an acceptance test. This is the same category of criterion Decision Log D-53/D-55's own
   credential-storage round already established a precedent for (`tests/acceptance/README.md`'s
   "Local credential-storage-mechanism change" section): "these criteria concern the desktop
   application's own internal storage/UI mechanism, not a generated-project artifact this harness's
   black-box convention can reach, and the unit-level tests they require fall under the
   `implementer` role's mandate, not `test-designer`'s file-scope boundary." This round applies the
   identical determination here and adds no acceptance test for this half of AC-QPB-102. The
   sibling half — no attribution/license notice anywhere in the *generated project* — **is**
   testable and **is** tested (`test_ac102_no_attribution_or_license_notice_appears_anywhere_in_the_generated_project`).
2. **AC-QPB-104's first clause — the wizard literally presenting a new Step 6 between Step 5 and
   the renumbered Step 7.** A PySide6-wizard-UI-sequencing fact, not a generated-project artifact,
   and not a pure, GUI-independent logic function the way FR-QPB-121's own search-filter logic is
   (which **is** exposed headlessly via the new `search_bundled_tabler_icon_names()` function and
   **is** tested). This matches this suite's own long-established "what these tests deliberately do
   not invent" exclusion for "UI widget/event names" (`HARNESS_CONTRACT.md`). A documented,
   `manual`-marked, skipped placeholder is added instead —
   `test_ac104_wizard_presents_the_new_step6_between_step5_and_the_renumbered_step7` — mirroring
   this suite's own established convention (e.g.
   `test_post_mvp_identification_plugin.py::test_qgis_desktop_repair_warning_status_when_qml_widget_fails_to_load_not_yet_confirmed`).
   AC-QPB-104's other two clauses (uniform styling within one project; not carried over between
   separately generated projects) **are** testable via `build_project()` and **are** tested.
3. **The exact Tabler SVG download URL template.** Decision Log D-65's own confirmed technical
   finding establishes *that* a public, no-auth, static SVG source exists and is MIT-licensed, but
   this test-designer round did not itself perform a live confirmation of the *exact* download URL
   shape (unlike the VWorld/Pl@ntNet precedent, where an earlier round called the real endpoint
   itself with a real key during test design). The one `network`-marked live test
   (`test_network_tabler_icon_svg_fetch_returns_a_real_svg_response`) asserts only the general
   response shape (HTTP 200, an `svg+xml`-family content type, SVG-looking body text) — see
   HARNESS_CONTRACT.md function 13's own disclosed limitation. This is not itself a coverage gap
   against any specific FR/AC text (no requirement mandates a specific URL template), only an
   honesty disclosure about what was, and was not, independently re-verified this round.

## Design choices this round made, and why (so a future round is not left guessing)

- **Color/outline-exact assertions are deliberately not made.** FR-QPB-120's own text does not
  mandate a specific fill/outline color; this test-designer round has no way to independently
  confirm QGIS's own unmodified default single-symbol color/outline shape without a live QGIS
  instance (barred by this project's hard QGIS-isolation rule). `inspect_layer_renderer()`
  therefore reports only structural facts (renderer class, symbol-layer types, marker shape,
  embedded-SVG path) — see HARNESS_CONTRACT.md function 15's own note, and the existing,
  comparably loose `test_geopackage_schema_by_type.py::test_ac015_community_symbology_rule_exists_in_qgs_project`
  precedent this mirrors.
- **AC-QPB-104's "every point layer shares one identical styling choice" clause is structurally
  vacuous under the current schema.** Every survey type in Section 8 has at most one
  minimalist-eligible point layer (`inventory_observation`, `survey`, or `plot`) and, separately,
  at most one minimalist-eligible polygon layer (`site` — `community` is explicitly excluded).
  `test_ac104_within_one_project_every_point_layer_shares_the_same_symbol_choice` is written
  generically (iterating every point layer a given survey type's schema defines) so it would catch
  a regression if the schema ever gained a second point/polygon layer for one survey type, but
  under the schema as it stands today it has nothing to compare for any single survey type — this
  is disclosed explicitly in the test's own docstring, not hidden. The criterion's other,
  genuinely non-vacuous half (styling not automatically carried over between two separately
  generated projects of the same survey type) is fully, meaningfully testable and is tested
  (`test_ac104_symbol_styling_choice_is_not_carried_over_between_separately_generated_projects`).
- **`build_project()`'s new `symbol_styling.tabler_svg_fetch` config is fake-double-only, never a
  "real" mode.** The real Tabler fetch is exercised only by the separate, standalone
  `fetch_tabler_icon_svg()` live test (function 13), never through `build_project()` itself —
  mirroring how this suite's existing real VWorld tile download is exercised via its own,
  separate `network`-marked path, never through `build_project()`'s own fake-double tests. This
  keeps every `build_project()`-based test in this file fast, deterministic, and independent of
  live network availability.

## Forward-pointing annotation (2026-08-28/29; Decision Log D-76) — non-destructive, recorded here, not altering this round's own rows

Decision Log D-76 adds a second, independently permitted network-fetch trigger to `FR-QPB-011(d)`
(clause `(d)(ii)`: a live preview-image fetch during search) and annotates `AC-QPB-101` "not
altered in substance" to note that the fetch-on-selection mechanism it already describes below is
now one of two independently permitted fetch triggers. This does **not** change anything in this
round's own table below: `AC-QPB-101`'s own text, the tests that verify it, and every other
row/finding in this file remain exactly as this round left them, since D-76 explicitly does not
reopen, reword, or alter this mechanism's own already-approved substance. The new fetch trigger's
own coverage (new `AC-QPB-117`, and the still-open `NFR-QPB-080` clauses (5)-(8) safeguards for it)
is recorded in a separate, later round's own file,
[`qfield_project_builder_tabler_icon_preview_fetch.traceability.md`](qfield_project_builder_tabler_icon_preview_fetch.traceability.md)
(new test file `test_tabler_icon_preview_fetch.py`), per this project's own established convention
of keeping a later round's additions in their own file rather than editing an already-approved
round's rows in place.

## Traceability table

| AC ID / FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-100 | Every point/polygon layer (excluding Type 4 `community`) receives a deliberately configured minimalist single-symbol renderer — single flat fill + thin outline for polygons; small, solid circle marker for points — never QGIS's own undifferentiated default | `test_symbol_styling.py::test_ac100_point_layer_has_a_minimalist_single_symbol_circle_marker_renderer` (parametrized, 3 point-layer cases), `::test_ac100_polygon_layer_has_a_minimalist_single_symbol_fill_renderer` (parametrized, 3 polygon-layer cases), `::test_ac100_type4_community_layer_keeps_its_own_rule_based_renderer_unaffected` (negative control) | auto (proxy — PyQGIS-backed `inspect_layer_renderer`; structural, not color-exact — see design-choices note above) |
| AC-QPB-101, clause 1 (offline, live-filtered search) | The bundled Tabler icon-name index is filtered live, by substring, with zero network access | `test_symbol_styling.py::test_search_bundled_tabler_icon_names_filters_case_insensitively_by_substring`, `::test_search_bundled_tabler_icon_names_reports_a_real_nontrivial_bundled_index`, `::test_search_bundled_tabler_icon_names_returns_no_matches_for_a_nonexistent_query` | auto (pure, offline `search_bundled_tabler_icon_names`; see note 1 below on the "zero network access" half) |
| AC-QPB-101, clauses 2/3 (select -> fetch -> embed; fallback on failure) | On success, the fetched SVG is used as every point layer's marker and embedded at a project-relative path; on failure/offline, the minimalist default remains in use and generation is not blocked | `test_symbol_styling.py::test_ac101_successful_selection_embeds_the_svg_and_every_point_layer_uses_it`, `::test_ac101_embedded_svg_is_referenced_by_a_project_relative_path_inside_the_output_folder`, `::test_ac101_failed_fetch_falls_back_to_the_minimalist_default_without_blocking_generation` (parametrized: network_error/http_error/timeout) | auto (proxy — `build_project()`'s `symbol_styling.tabler_svg_fetch.fake` double + `inspect_layer_renderer`) |
| AC-QPB-102 (generated-project half) | No attribution/license notice anywhere in the generated project when a Tabler icon is used (MIT license, confirmed) | `test_symbol_styling.py::test_ac102_no_attribution_or_license_notice_appears_anywhere_in_the_generated_project` | auto |
| AC-QPB-102 (internal HTTP-client half — `User-Agent`/no-retry) | The single SVG-fetch request carries a compliant `User-Agent` header and does not retry automatically | *(none — see "genuinely out of this harness's reach," item 1 above)* | **not covered by this round** — routed to the `implementer` role's own unit-test mandate |
| AC-QPB-104, clause 1 (wizard Step 6 exists between Step 5 and the renumbered Step 7) | A literal, on-screen wizard-UI-sequencing fact | `test_symbol_styling.py::test_ac104_wizard_presents_the_new_step6_between_step5_and_the_renumbered_step7` | **manual** (documented, skipped) |
| AC-QPB-104, clauses 2/3 (uniform per-project styling; not carried over between separately generated projects) | Every point/polygon layer of one project shares an identical styling choice; a styling choice is never automatically inherited by a later, separately generated project | `test_symbol_styling.py::test_ac104_within_one_project_every_point_layer_shares_the_same_symbol_choice` (structurally vacuous under the current schema — see design-choices note), `::test_ac104_symbol_styling_choice_is_not_carried_over_between_separately_generated_projects` | auto |
| FR-QPB-011(d) (network-boundary rule — no numbered AC beyond AC-QPB-101/102 above) | The Tabler SVG-fetch request is permitted strictly and only after the user has already selected a specific icon by name; searching never triggers a network request | Indirectly, via `search_bundled_tabler_icon_names`'s own network-parameter-free contract (no test here can positively prove "zero packets sent" — see note 1) and `build_project()`'s config shape itself having no code path from "search" to a fetch | auto (structural/by-construction) + disclosed limitation (note 1) |

## Notes on automation approach

1. **"Zero network access" during search is not, and cannot be, positively proven by this
   round.** `search_bundled_tabler_icon_names()` is specified (HARNESS_CONTRACT.md function 14) to
   take no network-capable parameters and perform no network I/O, and its tests confirm its
   *filtering logic* is correct — but no test in this suite, for any feature (OSM tile fetching,
   VWorld basemap tiles, or this search function), positively demonstrates "no network packet was
   ever sent" via, e.g., a network-blocking test harness. This project has no such mechanism
   anywhere yet. This is disclosed here rather than silently assumed proven.
2. **`REFERENCE_DATA_VALID_SAMPLE_DIR`-style shared fixtures were not needed for this round** —
   symbol styling has no dependency on the KTSN reference-data pipeline at all; every fixture in
   `test_symbol_styling.py` is either a small, self-contained inline SVG string
   (`_FAKE_SVG_CONTENT`) or a `make_base_config()`-based build with no reference-data override.

## Ambiguities / gaps found (routing recommendation, not silently resolved)

None found specific to this round's own assigned scope (FR-QPB-011(d)/FR-QPB-120/121/123/
NFR-QPB-080/AC-QPB-100–102/104) beyond the two "genuinely out of this harness's reach" items
already itemized above, which are determinations about *this harness's testing boundary*, not
ambiguities in the specification's own requirement text.
