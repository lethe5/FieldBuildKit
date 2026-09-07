# Traceability Matrix — QField Project Builder, Multiple Named Polygons in One Site-Drawing Session (Types 2/3/4)

> Specification: `specs/qfield-project-builder.md` — Decision Log **D-75** (Section 19, the
> stakeholder-directed workflow/UX change to the site-input wizard step and drawing canvas for
> Type 2/Type 3, "multiple, separate polygons in one drawing session... each finished polygon
> individually, manually named by the user"), Decision Log **D-79** (Section 19, extending
> D-75/FR-QPB-129's scope to Type 4 as well, by the stakeholder's explicit answer "Yes apply to
> Type 4 as well"); new `FR-QPB-129` (Section 6.3); new `AC-QPB-115` (Section 18.1), new
> `AC-QPB-116` (Section 18.5).
>
> This is a new-feature `test-designer` round following the approved D-75/D-79 specification
> revision — not a conformance-gap round. Both Decision Log entries are explicit that "the actual
> code changes to `qfield_builder/ui/map_canvas.py` and `qfield_builder/ui/wizard.py` are
> `test-designer`/`implementer` work for a future round, now unblocked by this clarified
> specification" — this file and its companion test file are that `test-designer` work.
>
> Tests: `tests/acceptance/qfield_project_builder/test_multi_polygon_site_drawing.py`.
> Test harness contract: no `HARNESS_CONTRACT.md` change was needed. This round's core, automated
> coverage uses the existing `build_project()` contract (function 4) unchanged — Decision Log
> D-75 itself confirms, by direct code reading, that `config["sites"]` is *already* documented and
> implemented as a list of `{"site_name", "geom_wkt"}` dicts (`HARNESS_CONTRACT.md`'s own function-4
> section, "sites (list of dicts, when applicable to survey_type)... each
> `{"site_name": str, "geom_wkt": str}`"), so no contract addition was required to exercise it with
> two or more entries.

## What this round independently confirmed by direct code reading (per this round's own
instructions, not merely trusting Decision Log D-75's own text at face value)

- **`qfield_builder/build.py`'s `_resolve_seed_sites()`/`build_project()` already accept
  `config["sites"]` as a list, validating each entry's geometry individually and returning it
  unchanged for `gpkg.build_geopackage()` to consume** (`build.py:89-109`) — confirmed directly;
  this function requires **no** change for this requirement. `qfield_builder/gpkg.py::
  build_geopackage()` (`gpkg.py:328-338`) then loops over `seed_sites` and executes one
  `INSERT INTO "site"` per entry, each with its own `site_id`/`site_name`/`site_geom` — confirmed
  directly; this is exactly the one-record-per-entry behavior AC-QPB-115 requires, and it is
  already exactly how the pre-existing GeoPackage/Shapefile upload path
  (`_resolve_sites_from_upload()`) already works today.
- **`qfield_builder/schemas.py` confirms Type 1 (`simple_inventory`) has no `site` table in its
  schema at all** — `_build_simple_inventory()` (`schemas.py:157-189`) returns only
  `inventory_observation`; `_site_table()` (`schemas.py:192-202`) is called only from
  `_build_temporary_plots()`, `_build_permanent_plots()`, and `_build_vegetation_mapping()`
  (Types 2, 3, 4). This confirms this feature is naturally inapplicable to Type 1 — per this
  round's own instructions, **no test in this round asserts anything about Type 1's non-existent
  site mechanism**; this is recorded here as a confirmed finding, not encoded as an assertion.
- **`qfield_builder/ui/map_canvas.py`'s `MapCanvas` is still single-polygon-only as of this
  round** — `self._vertices`/`self.last_polygon_wkt` are singular instance state, `polygon_drawn`
  emits one WKT string, and calling `add_polygon_vertex_at()` again after `finish_polygon()`
  re-opens the *same* shape for further editing rather than starting a second, independent one
  (confirmed by direct reading of `map_canvas.py:201-364`, matching Decision Log D-75's own
  identical finding).
- **`qfield_builder/ui/wizard.py`'s `SiteInputPage` is still single-site-only as of this round** —
  exactly one `draw_site_name_edit` field (`wizard.py:487`), one `_drawn_site_wkt` value
  (`wizard.py:499`), and `ReviewAndBuildPage._collect_config()`'s site-collection step
  (`wizard.py:1720-1728`) builds `config["sites"]` as a single-element list,
  `[{"site_name": site_input_page.drawn_site_name(), "geom_wkt": drawn_site_wkt}]` — confirmed by
  direct reading, matching Decision Log D-75's own identical finding.
- **`SiteInputPage.validatePage()` already treats drawing as optional** (`wizard.py:696` region)
  — zero drawn sites is already valid today; this must remain true after the multi-polygon change
  (regression guard specified in the routed contract table below, since a real `validatePage()`
  check is a PySide6-widget fact this file cannot exercise directly).

## Scope-boundary finding (read this first) — same, doubly/triply-established precedent as prior rounds

`MapCanvas` and `SiteInputPage` are plain PySide6 `QWidget`/`QWizardPage` objects with no
`qfield_builder.acceptance_api`-mediated surface at all (unlike `build_project()`/
`check_runtime()`, etc.). Exercising their own mouse-event/session-state/config-collection logic
requires directly constructing and driving live Qt objects — exactly the class of "PySide6
wizard's own code structure" testing `HARNESS_CONTRACT.md`'s own "what these tests deliberately do
not invent" section already excludes from this black-box harness, and which this suite's own
established precedent treats as the `implementer` role's `tests/unit/` mandate, not
`test-designer`'s `tests/acceptance/`-only file-scope boundary — both the checked-in system role
definition and `.claude/agents/test-designer.md` state, verbatim, "You may create or modify files
only under `tests/acceptance/`." This is now at least the third independent `test-designer` round
to reach this same conclusion for this exact reason:

- `qfield_project_builder_credential_storage_mechanism.traceability.md` (Decision Log D-53/D-55)
  established the underlying principle for `qfield_builder.credential_store`'s own internals.
- `qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md`
  applied it to `MapCanvas`/`SiteInputPage`/`ConnectivityBasemapPage` directly — the same two
  files this round's own routed contract (below) extends further, for a different mechanism
  (multi-polygon sessions rather than pan-while-drawing).
- `qfield_project_builder_app_rename_version_and_branding.traceability.md` applied it again to
  `ProjectBuilderWizard`'s window title/version display and `credential_store`'s directory
  migration.

This round follows the same precedent, applied to a fourth mechanism: `MapCanvas`'s multi-polygon
drawing-session state, and `SiteInputPage`'s per-polygon naming and `config["sites"]`-list
construction. The orchestrating task's own suggestion that this round specify a precise routed
contract for `tests/unit/test_wizard.py`/`tests/unit/test_map_canvas.py` (rather than writing those
files itself) is followed for exactly this reason — mirroring the same reasoning the app-rename
round gave when it received a structurally identical instruction: a task instruction cannot expand
this role's own configured hard boundary, and no agent message can authorize changing this role's
tools/permissions/configuration.

## What this round covers with real, automated tests (`test_multi_polygon_site_drawing.py`)

The core, most valuable, fully-automatable half of this requirement: `config["sites"]` is already
documented and implemented as a list, so `build_project()` can be exercised directly with two or
more `{"site_name", "geom_wkt"}` entries — exactly the shape a fixed `SiteInputPage`/`MapCanvas`
must eventually produce at the end of a multi-polygon drawing session — without needing to drive
the PySide6 UI at all.

| Test | What it verifies | Survey types | FR/AC basis |
|---|---|---|---|
| `test_ac115_two_named_polygons_in_one_session_produce_two_separate_site_records` | Given two named `{"site_name", "geom_wkt"}` entries, the generated GeoPackage's `site` table has exactly 2 records, each with the correct, individually-assigned name and geometry envelope — never merged, never a shared name. Also exercises AC-QPB-116's own GeoPackage-level assertion ("both named polygons are available for inclusion in the generated project"). | Type 2, Type 3, Type 4 (parametrized) | FR-QPB-129, AC-QPB-115, AC-QPB-116 |
| `test_ac115_three_named_polygons_in_one_session_produce_three_separate_site_records` | Generalizes the above to 3 polygons, guarding against an implementation that special-cases "exactly 2" | Type 2, Type 3, Type 4 (parametrized) | FR-QPB-129, AC-QPB-115 |
| `test_ac115_never_merges_multiple_polygons_into_one_multipolygon_record` | Explicit differential/negative guard: a single record spanning both input polygons' combined envelope (the specifically-superseded behavior) never occurs | Type 2 (representative) | FR-QPB-129, AC-QPB-115, Decision Log D-75's own "never merged" clause |
| `test_ac115_duplicate_site_names_across_distinct_polygons_are_not_deduplicated` | FR-QPB-129 clause (2)'s explicit "no uniqueness constraint across these names is required" — two distinctly-drawn polygons sharing an identical name still produce two separate records, never collapsed | Type 3 (representative) | FR-QPB-129 clause (2) |

All four were run against the current, pre-implementation codebase (see "Empirical result" below
for the exact outcome and why).

**Type 1 (`simple_inventory`) is deliberately absent from every test above and from every
parametrization list.** Per this round's own instructions and the confirmed finding above (no
`site` table exists in Type 1's schema at all), writing a test asserting any particular outcome
for Type 1's site mechanism would be inventing behavior for a mechanism that does not exist — this
is not an oversight.

One `manual`-marked placeholder, mirroring the established `AC-QPB-104`/`FR-QPB-008`/
`FR-QPB-025`-D-24 (`test_map_canvas_pan_navigability.py`) convention exactly, covers the genuinely
human/GUI-interaction-only fact neither this round's automated tests nor any headless mechanism
can confirm:

| Test | What it documents |
|---|---|
| `test_wizard_can_draw_and_individually_name_multiple_separate_polygons_in_one_session` | A real human, using a real mouse, finishing one polygon, naming it, starting and finishing a second (and third) separate polygon without losing the first, and confirming the resulting generated project's `site` layer matches — for each of Type 2, Type 3, and Type 4 |

## What this round routes to `tests/unit/` (fully specified, not authored here)

Mirrors this suite's own established convention (`qfield_project_builder_offline_vworld_key_and_
canvas_pan_conformance_gaps.traceability.md`'s exact routing structure) for the genuinely
PySide6-widget-internal half of this requirement: fully specified below as a contract a future
`implementer`/`test-designer` round must satisfy, not authored as executable code in this round
(this role may create/modify files only under `tests/acceptance/`).

### `tests/unit/test_map_canvas.py` — multi-polygon drawing-session mechanism

**Illustrative-only naming note**, mirroring the app-rename round's own identical disclaimer: the
exact name/signature of any new `MapCanvas` method (e.g. a plausible `start_new_polygon()`, or a
plausible `finished_polygons` list attribute) is not mandated by this contract — FR-QPB-129 itself
explicitly leaves "the exact UI mechanics... left to the implementer." Only the input/output
behavior below is required.

| # | What it must verify | Exact assertions (`tests/unit/test_map_canvas.py`-level, mirroring this codebase's existing `test_polygon_drawing_via_direct_calls_produces_valid_multipolygon_wkt`/`test_bbox_drawing_via_direct_calls_produces_correct_min_max` direct-call conventions) |
|---|---|---|
| 1 | `MapCanvas` supports finishing one polygon, then starting and finishing a second, separate polygon in the same session, without the second's vertices merging with the first's already-finished shape | Construct a `MapCanvas`, `set_mode("polygon")`, call `add_polygon_vertex_at()` for a first, non-degenerate ring and `finish_polygon()` to get `wkt_1`; then invoke whichever new entry point the implementer adds to explicitly commit that finished shape and begin a fresh one (mirroring this round's own finding that today's `add_polygon_vertex_at()` after `finish_polygon()` incorrectly re-opens the *same* shape — that specific behavior must no longer occur for this new entry point); add vertices for a second, non-overlapping ring and call `finish_polygon()` again to get `wkt_2`. Assert `wkt_1 != wkt_2`, `wkt_1` reconstructs exactly the first ring's coordinates, and `wkt_2` reconstructs exactly the second ring's coordinates only (not the first ring's vertices appended/merged in). |
| 2 | Every finished-and-committed polygon in a session accumulates in an inspectable collection, each independently retrievable together with the WKT it was actually finished with | After committing two separate finished polygons per row 1, assert some enumerable, public collection (e.g. a plausible `canvas.finished_polygons` list — exact attribute name left to the implementer) contains exactly the two distinct WKT strings, in the order finished, and that finishing a later polygon never mutates an earlier, already-committed one's own stored WKT. |
| 3 | A polygon in progress (vertices already placed, not yet finished) is unaffected by an earlier polygon in the same session having already been finished and committed | Commit one finished polygon (row 1), then call `add_polygon_vertex_at()` for a second polygon without finishing it, and assert those in-progress vertices are still present/reconstructable via the widget's own existing in-progress-drawing-state accessor (mirroring this codebase's existing `test_map_canvas.py` conventions for inspecting `_vertices`/equivalent) — mirrors AC-QPB-116's own "the first polygon's own finished shape and assigned name are preserved... the canvas correctly begins a new, independent shape" requirement, isolated to the canvas-widget layer specifically (naming is `SiteInputPage`'s own responsibility — see the `tests/unit/test_wizard.py` contract below). |
| 4 (regression guard) | Zoom/pan continue to work identically regardless of this change | Re-run the existing zoom/pan tests (e.g. `test_zoom_by_changes_zoom_level_and_is_clamped`, and — if the `../qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md` round's own routed `MODE_POLYGON` pan contract has by then been implemented — its own pan-while-drawing test) with a multi-polygon session already in progress (one polygon already committed per row 1), confirming this round's change does not accidentally disturb either mechanism. |

### `tests/unit/test_wizard.py` — per-polygon naming and `config["sites"]` list construction

| # | What it must verify | Exact assertions (`tests/unit/test_wizard.py`-level, mirroring this codebase's existing offscreen `QApplication`/wizard-construction/navigation conventions) |
|---|---|---|
| 5 | `SiteInputPage` lets the user assign/confirm a distinct name for each individual finished polygon — not one shared `draw_site_name_edit` value applied to every polygon in the session — defaulting to a non-blank, per-polygon fallback name (mirroring the existing single-shape default, `"그려진 사이트"`) when a given polygon's own name is left blank | Construct a `SiteInputPage` under the existing offscreen `QApplication` fixture; drive two separate finish-and-commit interactions (via whichever new `MapCanvas`-level entry point row 1 above establishes, plus whatever new per-polygon name-entry UI the implementer adds); assert the page exposes some enumerable collection of `(name, wkt)` pairs, one per finished polygon (e.g. a plausible new `drawn_sites()` method returning `list[{"site_name": str, "geom_wkt": str}]`, superseding the existing single-value `drawn_site_wkt()`/`drawn_site_name()` pair), with each polygon's own individually confirmed name attached to only that polygon; and that leaving one specific polygon's own name blank produces a non-blank fallback for that polygon only (e.g. `"그려진 사이트"` or a distinguishable per-polygon variant of it), without altering any other, already-named polygon in the same session. |
| 6 | `ReviewAndBuildPage._collect_config()`'s site-collection step (or its Type-4-reaching equivalent) builds `config["sites"]` as a list with exactly one `{"site_name", "geom_wkt"}` entry per named, finished polygon from the current drawing session — reusing the exact list contract `_resolve_seed_sites()`/`_resolve_sites_from_upload()` already implement, confirmed above to require no `qfield_builder/build.py` change | Build a real `ProjectBuilderWizard` for each of Type 2/Type 3/Type 4 in turn (mirroring this suite's existing wizard-navigation helper conventions), fill required upstream fields, reach `SiteInputPage`, drive a two-polygon (then, separately, a three-polygon) drawing session via row 1/5's new entry points, advance to `ReviewAndBuildPage`, call `_collect_config()`, and assert `config["sites"]` is a list of exactly that many entries, each `{"site_name": <the name assigned to that specific polygon>, "geom_wkt": <that polygon's own WKT>}`, matching 1:1 (in order) the polygons/names actually driven into the page — this is a regression guard directly against the existing, pre-this-round single-element-list construction at `wizard.py:1726-1728` (`config["sites"] = [{"site_name": site_input_page.drawn_site_name(), "geom_wkt": drawn_site_wkt}]`), which this contract requires be replaced with the multi-entry equivalent. |
| 7 (regression guard) | Zero, one, or many named polygons are all valid outcomes of one drawing session — `SiteInputPage.validatePage()`'s existing "drawing is optional" behavior is unchanged, and the pre-existing single-polygon path still produces a correctly single-element list | Construct a `SiteInputPage`, drive zero finish-polygon interactions, and assert `validatePage()` still returns `True` (the pre-existing, already-passing zero-sites case, confirmed unaffected); separately, drive exactly one finished, named polygon and assert the resulting `config["sites"]`-equivalent collection has exactly one, correctly-shaped entry (confirming this round's change is additive to, not a breaking change of, the existing one-polygon path). |
| 8 (Type 4 specific) | The identical `SiteInputPage`/`MapCanvas` multi-polygon mechanism is reachable and produces the same `config["sites"]` list shape when `survey_type` is `vegetation_mapping` specifically, not only `temporary_plots`/`permanent_plots` | Repeat row 6's wizard-level assertion with `survey_type = "vegetation_mapping"` as its own, separately-run case (Decision Log D-79's own scope extension) — not merely inferred from the Type 2/3 cases, since D-79 is a textually distinct decision from D-75's original Type-2/3-only text, and `SiteInputPage`'s own applicability gate (`_SURVEY_TYPE_WITHOUT_SITE`, currently only excluding Type 1) must correctly continue to treat Type 4 as applicable. |

Neither `tests/unit/test_map_canvas.py` nor `tests/unit/test_wizard.py` is modified by this round;
the tables above are the complete, actionable specification for whichever round picks this up
next — mirroring the identical "not a `manual`-marked placeholder, but not authored here either"
treatment the offline-VWorld-key/canvas-pan round already established for structurally identical
PySide6-widget facts.

## Full traceability table

| ID | Summary | Test(s) | Automation |
|---|---|---|---|
| FR-QPB-129 / AC-QPB-115 (core record-count/naming/geometry assertion, Types 2/3/4) | `build_project()` with 2 named polygons produces exactly 2 separate, correctly-named/geometried `site` records | `test_multi_polygon_site_drawing.py::test_ac115_two_named_polygons_in_one_session_produce_two_separate_site_records` (parametrized over `temporary_plots`/`permanent_plots`/`vegetation_mapping`) | auto (`qgis`-marked) |
| FR-QPB-129 / AC-QPB-115 (generalization beyond exactly 2, Types 2/3/4) | Same, with 3 named polygons | `test_multi_polygon_site_drawing.py::test_ac115_three_named_polygons_in_one_session_produce_three_separate_site_records` (parametrized) | auto (`qgis`-marked) |
| FR-QPB-129 / Decision Log D-75 ("never merged" negative guard) | No single record's envelope spans multiple input polygons' combined extent | `test_multi_polygon_site_drawing.py::test_ac115_never_merges_multiple_polygons_into_one_multipolygon_record` | auto (`qgis`-marked) |
| FR-QPB-129 clause (2) ("no uniqueness constraint on names") | Two distinct polygons sharing an identical assigned name still produce two separate records | `test_multi_polygon_site_drawing.py::test_ac115_duplicate_site_names_across_distinct_polygons_are_not_deduplicated` | auto (`qgis`-marked) |
| AC-QPB-116 (GeoPackage-level half: "both named polygons are available for inclusion in the generated project") | Covered by the same two-polygon test as AC-QPB-115 above (identical `build_project()`-observable outcome) | `test_multi_polygon_site_drawing.py::test_ac115_two_named_polygons_in_one_session_produce_two_separate_site_records` | auto (`qgis`-marked) |
| AC-QPB-116 (mid-session half: "the first polygon's own finished shape and assigned name are preserved... the canvas correctly begins a new, independent shape") | *(no test in this round — see the routed contract table, rows 1/3/5)* | **routed to `tests/unit/test_map_canvas.py`/`tests/unit/test_wizard.py`**, not yet written | routed |
| FR-QPB-129 (per-polygon naming; `SiteInputPage` UI mechanism) | *(no test in this round — see the routed contract table, row 5)* | **routed to `tests/unit/test_wizard.py`**, not yet written | routed |
| FR-QPB-129 (`config["sites"]` multi-entry list construction) | *(no test in this round — see the routed contract table, rows 6/8)* | **routed to `tests/unit/test_wizard.py`**, not yet written | routed |
| FR-QPB-129 clause (4) / `SiteInputPage.validatePage()` "drawing is optional" (regression guard) | *(no test in this round — see the routed contract table, row 7)* | **routed to `tests/unit/test_wizard.py`**, not yet written | routed |
| FR-QPB-129/AC-QPB-115/AC-QPB-116 (real, on-screen, human GUI-interaction fact) | A real human can draw, finish, and individually name multiple separate polygons in one session, for Types 2/3/4, and see the correct result in the generated project | `test_multi_polygon_site_drawing.py::test_wizard_can_draw_and_individually_name_multiple_separate_polygons_in_one_session` | **manual** (documented, skipped) |
| Type 1 (`simple_inventory`) — no `site` layer at all | Confirmed by direct code reading (`qfield_builder/schemas.py`) — feature naturally inapplicable; no test written | *(none — deliberately no test; see "What this round covers" section above)* | n/a (out of scope, confirmed inapplicable, not silently skipped without explanation) |

Every criterion this round was asked to cover (`FR-QPB-129`, `AC-QPB-115`, `AC-QPB-116`, the Type-1
negative control, and the routed `tests/unit/` contract) appears above, mapped to either a real
automated test, a `manual`-marked placeholder, a fully-specified routed contract, or an explicit
"confirmed inapplicable, no test" finding — nothing is silently dropped.

## Empirical result (run against the current, pre-implementation codebase)

Ran `python -m pytest tests/acceptance/qfield_project_builder/test_multi_polygon_site_drawing.py
-v` locally as part of this round's own authoring-support verification (per this role's permitted
use of `Bash` for read-only/authoring-support purposes — no application code was run to "make
things pass," and no QGIS/PyQGIS process or `QgsApplication` was constructed by this verification
step; it only invokes this repository's own already-existing, pre-existing `pytest`/
`qfield_builder.acceptance_api` entry points exactly as every other test in this suite already
does).

- The nine automated (`qgis`-marked) test cases (2 polygon-count-parametrized tests × 3 survey
  types = 6, plus 3 single-case tests) **passed** against the current, already-implemented
  `qfield_builder/build.py`/`qfield_builder/gpkg.py` — confirming empirically, not merely by
  static code reading, that Decision Log D-75's own claim ("this is exactly the target end-state
  data model, and it requires no backend/build-pipeline change whatsoever") is correct: the
  backend already fully supports this requirement today, and this round's tests genuinely
  exercise real, already-correct behavior rather than merely encoding an assumption.
- The one `manual`-marked test **skipped** cleanly, as intended.
- See this round's own completion report (returned to the orchestrator/user, not written as a
  file in this directory) for the exact `pytest` output.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

1. **No genuine ambiguity was found in FR-QPB-129/AC-QPB-115/AC-QPB-116/Decision Log D-75/D-79
   themselves.** Every requirement text this round was asked to cover is clear, internally
   consistent, and fully testable as written (at least for the `build_project()`-observable half);
   the routing recorded above is a role/file-scope-boundary matter (which role's mandate covers
   authoring a `tests/unit/`-level PySide6 test), not a defect in the requirement text — mirroring
   the identical finding the app-rename round and the offline-VWorld-key/canvas-pan round each
   already recorded for their own, structurally identical situations.
2. **The exact new `MapCanvas`/`SiteInputPage` API surface for committing a finished polygon and
   starting a new one is deliberately left unspecified**, mirroring FR-QPB-129's own explicit "the
   exact UI mechanics... are not dictated by this requirement and are left to the implementer"
   text (itself mirroring Decision Log D-27's precedent for implementation-authored UI copy/API
   shape). The routed contract tables above specify only the required *effect*, not the *method
   name/signature*.
3. **This round did not attempt to independently verify AC-QPB-116's own mid-session PySide6
   half** (whether a live `MapCanvas`/`SiteInputPage` instance genuinely preserves an
   already-finished polygon while a second is drawn) — that mechanism does not exist in the
   current codebase yet (confirmed above), so there is nothing to empirically verify today;
   the routed contract specifies what a future implementation must satisfy once it exists.
