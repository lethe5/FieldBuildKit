# Traceability Matrix — QField Project Builder, Offline VWorld-Key Collection and Drawing-Canvas Pan Navigability (conformance-gap round)

> Specification: `specs/qfield-project-builder.md` —
> `E-QPB-003` (Section 15), `FR-QPB-078`/`NFR-QPB-058` (Section 11), `FR-QPB-025` (Section 6.3),
> Decision Log **D-24** (Section 19), `NFR-QPB-060` (Section 5.4).
>
> This is a **conformance-gap round**, not new feature elicitation and not a specification change,
> covering two independent, real, already-diagnosed defects found via manual UI testing of the
> built desktop app (per the orchestrating task). Both are gaps against already-approved
> requirement text; no spec change is needed or wanted. This round independently re-verified both
> reported root causes by direct code reading before writing any test, rather than trusting the
> bug reports handed to this round at face value — see each bug's own section below and each new
> test file's own module docstring for the exact confirmation trail (file/line references).
>
> Tests:
> `tests/acceptance/qfield_project_builder/test_offline_vworld_api_key_collection.py` (Bug 1),
> `tests/acceptance/qfield_project_builder/test_map_canvas_pan_navigability.py` (Bug 2).
> Test harness contract: no `HARNESS_CONTRACT.md` change was needed — Bug 1's automated coverage
> uses the existing `build_project()` contract (function 4) unchanged; neither bug's
> PySide6-widget-internal half is exposed through `qfield_builder.acceptance_api` (see "Genuinely
> out of this harness's reach" below for why, and where that coverage is routed instead).

## Bug 1 — offline basemap generation never collects the VWorld API key

### Root cause (independently re-confirmed by this round)

- `qfield_builder/ui/wizard.py`'s `ConnectivityBasemapPage.__init__` places `self.api_key_edit`
  (the VWorld key input, line 662) only inside `self.online_group` (`online_layout.addRow("VWorld
  API 키:", self.api_key_edit)`, line 710); `self.online_group`'s visibility is tied solely to
  `self.online_radio` (line 768: `self.online_radio.toggled.connect(self.online_group.
  setVisible)`). The key input is never shown for offline mode.
- `ConnectivityBasemapPage.offline_config()` (line 981-989) returns exactly
  `{"bbox", "min_zoom", "max_zoom"}` — never `vworld_api_key`.
- `ReviewAndBuildPage._collect_config()` (line 1439-1473) only adds `"vworld_api_key"` to
  `config["basemap"]` when `mode == "online"` (line 1450-1462); for `"offline"` (line 1471-1473) it
  calls `basemap_page.offline_config()`, confirmed above to never include it.
- `qfield_builder/vworld_tiles.py::resolve_tile_fetcher()` (line 114-122) does a raw
  `basemap_config["vworld_api_key"]` dict index with no `.get()`/fallback whenever `tile_source`
  is not an injected `{"fake": ...}` double — this raises `KeyError` while evaluating
  `make_real_vworld_tile_fetcher`'s `api_key=...` argument, strictly before any network I/O.
- `qfield_builder/build.py::build_project()`'s outermost `except Exception as exc: ...
  error_message=str(exc)` (line 505-507) **does** catch this `KeyError` — `build_project()` never
  raises an uncaught exception to its caller. But `str(KeyError("vworld_api_key"))` is the literal
  text `"'vworld_api_key'"`, a bare Python dict-key repr — not a clear, non-technical, actionable
  message — and that text is exactly what the wizard's `result_label` shows
  (`f"생성 실패: {result.get('error_message') or result.get('error_code')}"`, wizard.py:1685),
  matching the stakeholder's own real screenshot ("생성 실패: 'vworld_api_key'") verbatim.

**This is a message-quality defect against `E-QPB-003`'s "actionable error" wording, not an
uncaught-exception-propagation defect** — confirmed `build_project()` already never crashes on
this input; it just returns an unhelpful message.

### What this round covers with a real, automated acceptance test

`test_offline_vworld_api_key_collection.py::
test_offline_missing_vworld_api_key_fails_with_actionable_message_not_raw_keyerror` — an
offline-mode `build_project()` call whose `config["basemap"]` has no `vworld_api_key` at all
(simulating today's actual wizard output, and guarding against a future regression once the
wizard is fixed) must return `success: False` with a non-blank `error_message` that is neither the
bare `KeyError` repr (`"'vworld_api_key'"`) nor generic technical jargon, and must never raise. No
live network access or real API key is needed — the `KeyError` this exercises happens before any
network I/O (see root-cause notes above). A companion positive-path test
(`test_offline_with_vworld_api_key_present_does_not_hit_the_missing_key_failure_path`) pins that,
once the key IS present (the shape a fixed wizard must produce), this specific failure mode does
not occur.

### Genuinely out of this harness's reach — routed to `tests/unit/test_wizard.py`

The wizard-widget-internal halves of Bug 1 — whether `api_key_edit` is actually reachable when
offline mode is selected in a real wizard (Bug 1(a)), and whether `ReviewAndBuildPage.
_collect_config()` actually wires a typed-in key into `config["basemap"]` once fixed (Bug 1(b)) —
both require directly constructing and driving real PySide6 `QWizardPage` objects. This is exactly
the class of "PySide6 wizard's own code structure" testing `HARNESS_CONTRACT.md`'s own "what these
tests deliberately do not invent" section already excludes from this black-box,
`qfield_builder.acceptance_api`-mediated harness, and which this suite's own established precedent
(`qfield_project_builder_credential_storage_mechanism.traceability.md`'s "Scope-boundary finding")
treats as the `implementer` role's `tests/unit/` mandate, not `test-designer`'s
`tests/acceptance/`-only file-scope boundary — both the checked-in system role definition and
`.claude/agents/test-designer.md` state, verbatim, "You may create or modify files only under
`tests/acceptance/`." **Both halves are genuinely offscreen-automatable (not merely GUI-reachable
by a human) — they are not treated as `manual`-marked placeholders**, because
`tests/unit/test_wizard.py` already contains near-identical, already-passing precedent for exactly
this shape of assertion (e.g. lines 813-825: `page.show()` then
`assert page.offline_upload_path_edit.isVisible()` / `assert not page.offline_map_canvas.
isVisible()` after toggling the offline bbox-source radio buttons) — `isVisible()` reliably
reflects real Qt visibility once a page/widget is `.show()`n, even under the `QT_QPA_PLATFORM=
offscreen` this project's `tests/unit/conftest.py` already configures. The exact contract:

| # | What it must verify | Exact assertions (`tests/unit/test_wizard.py`-level) |
|---|---|---|
| 1(a) | The VWorld key input control is genuinely reachable (visible and enabled) once offline mode is selected — mirroring the existing pattern at `test_wizard.py:813-825` for `offline_upload_path_edit`/`offline_map_canvas` | Construct a `ConnectivityBasemapPage`, call `page.show()`, set `page.offline_radio.setChecked(True)`, and assert `page.api_key_edit.isVisible() is True` and `page.api_key_edit.isEnabled() is True`. A companion assertion should confirm the pre-existing online-mode case is unaffected: with `page.online_radio.setChecked(True)`, `page.api_key_edit.isVisible() is True` also holds (today's already-correct case) — the fix must not regress the online path while fixing the offline path. |
| 1(b) | `ReviewAndBuildPage._collect_config()` includes a non-empty `vworld_api_key` in `config["basemap"]` for offline mode when the user has entered one | Build a real `ProjectBuilderWizard` (mirroring this file's own existing wizard-navigation helpers, e.g. `_advance_to_connectivity_basemap_page_in_its_widest_state`-style patterns already used elsewhere in this file), fill the required upstream fields, reach `ConnectivityBasemapPage`, set `basemap_page.offline_radio.setChecked(True)`, set `basemap_page.api_key_edit.setText("test-offline-key")`, supply an offline bbox via the page's own existing `_on_bbox_drawn({"min_lon": ..., "min_lat": ..., "max_lon": ..., "max_lat": ...})` direct-call hook (the same deterministic-drawing convention `test_map_canvas.py` already establishes for driving drawing without depending on synthetic mouse-event delivery), advance to `ReviewAndBuildPage`, call `review_page._collect_config()`, and assert `config["basemap"]["vworld_api_key"] == "test-offline-key"`. A companion regression assertion should confirm the existing online-mode collection (`config["basemap"]["vworld_api_key"]` when `mode == "online"`, already implemented and presumably already covered) is unaffected by the fix. |

Neither of these is a `manual`-marked placeholder in `test_offline_vworld_api_key_collection.py`
(unlike Bug 2's genuinely human-only half below) — both are fully specifiable, offscreen-testable
facts; they are simply outside this role's own file-scope boundary to author directly. No test
file or executable code for either is added by this round; this table is the complete, actionable
specification for whichever round picks this up next.

## Bug 2 — the wizard's drawing canvas cannot be panned while drawing

### Root cause (independently re-confirmed by this round)

- `MapCanvas` already has fully working pan support: `MODE_PAN`, `pan_by_pixels()`, and
  `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` branches (`map_canvas.py:423-461`) that
  pan on left-button drag only when `self._mode == MODE_PAN`. Scroll-wheel zoom (`wheelEvent` ->
  `zoom_by()`, line 470-473) is unconditional — confirmed it works regardless of `self._mode`.
- Both real usages of this widget in the wizard hardcode a non-pan mode with no way back to pan
  mode: `SiteInputPage.__init__` (`wizard.py:400`, `self.draw_map_canvas.set_mode("polygon")`) and
  `ConnectivityBasemapPage.__init__` (`wizard.py:732`, `self.offline_map_canvas.set_mode("bbox")`).
  Neither page calls `set_mode("pan")` again or exposes any mode-toggle control or secondary input
  path (modifier key, alternate mouse button) — confirmed by inspecting every `set_mode`/
  `MODE_PAN` reference in `wizard.py`.
- `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` contain no `event.modifiers()` check
  anywhere, and every branch where `event.button() != Qt.MouseButton.LeftButton` falls through to
  `super().mousePressEvent(event)`/`super().mouseReleaseEvent(event)` and returns immediately —
  confirming there is no existing secondary-button pan path in the widget itself either, not just
  a missing wizard-level wiring gap.
- Net effect, confirmed by the stakeholder's own real-device report ("Cannot pan a map, so it is
  hard to make a rectangle where I want."): the user can zoom in place but can never recenter the
  view while drawing — an area of interest not already near the hardcoded default center
  (`center_lon=127.5, center_lat=36.5`) is literally unreachable through this UI.

### Textual-grounding note (transparency, not a request for spec change)

`specs/qfield-project-builder.md`'s own literal text does not contain the word "pan" anywhere.
Decision Log D-24's own fix for the prior "hard to use in practice" complaint was adding OSM tile
imagery, not a pan-while-drawing capability specifically. This round's contract below is grounded
in `FR-QPB-025`'s "interactive map" wording plus D-24's own stated rationale (a canvas that is
"hard to use in practice" for locating a real site), not a literal transcription of explicit spec
prose about panning: a canvas whose view can never be recentered away from a hardcoded default
fails to be "interactive" (FR-QPB-025's own word) for any site outside its immediate default
viewport, by any ordinary reading of that word. This is flagged here per this role's
ambiguity-handling duty, rather than silently treated as beyond question — but this round still
proceeds to specify and cover it, per the orchestrating task's own explicit, well-evidenced
direction (a real, verbatim stakeholder complaint plus this round's own independent code-reading
confirmation of the mechanism). **If the stakeholder/orchestrator would prefer this recorded as an
explicit spec clarification (Category B) rather than left as this traceability file's own
textual-grounding argument, that is a `spec-writer` decision this round does not make
unilaterally.**

### What this round covers with a `manual`-marked placeholder

`test_map_canvas_pan_navigability.py::
test_wizard_drawing_canvas_can_be_panned_to_reach_an_arbitrary_location_while_drawing` — a real
human, using a real mouse/trackpad, confirming they can pan/recenter the view while a shape is
in progress, without losing the in-progress drawing, at both Step 3 (site drawing) and Step 4
(offline extent drawing). Mirrors the established `AC-QPB-104`/`FR-QPB-008` precedent exactly.

### Genuinely out of this harness's reach — routed to `tests/unit/test_map_canvas.py`

The underlying mechanism — some input path that actually calls `pan_by_pixels()`/moves
`self._center_lon`/`self._center_lat` while `self._mode` is `MODE_BBOX` or `MODE_POLYGON` — is a
plain PySide6 `QWidget` mouse-event/mode-gating fact, fully offscreen-automatable (this exact
codebase already proves this: `test_map_canvas.py::test_pan_via_real_mouse_drag_in_pan_mode`
already drives synthetic `QMouseEvent`s against this same widget and asserts on `canvas.center()`
before/after — it just never exercises panning while `self._mode` is `"bbox"`/`"polygon"`, which
is precisely the zero-coverage gap this bug is about), but has no `qfield_builder.acceptance_api`
surface at all — `MapCanvas` is never exposed through that black-box contract, unlike
`build_project()`/`check_runtime()`. Per the same file-scope-boundary reasoning as Bug 1(a)/(b)
above, this is not authored as an executable test by this round. The exact contract, deliberately
**implementation-mechanism-agnostic** (which secondary interaction the implementer chooses is left
open; only the required *effect* is specified, matching this suite's own established convention —
see `HARNESS_CONTRACT.md`'s "New (test-designer conformance-gap round...)" precedent for
specifying an as-yet-unimplemented contract via assertions rather than dictating an implementation
choice):

| # | What it must verify | Exact assertions (`tests/unit/test_map_canvas.py`-level) |
|---|---|---|
| 2(i) | Some input path exists that pans the view while `self._mode` is `MODE_BBOX`, without disturbing any bbox drag already in progress | Construct a `MapCanvas`, `set_mode("bbox")`, call `start_bbox_at(x, y)` to begin a drag (mirroring `test_bbox_drawing_via_direct_calls_produces_correct_min_max`'s existing setup), then exercise whichever secondary-interaction path the implementer chose (e.g. a right-button `QMouseEvent` drag sequence, or a `Qt.KeyboardModifier`-carrying left-button drag sequence, or a `set_mode("pan")`-then-restore toggle triggered by a UI control) and assert `canvas.center()` changes and/or `pan_by_pixels` is observably invoked (e.g. via a `monkeypatch`/spy on the method), **and** that the in-progress bbox drag state (`canvas._bbox_start`, or equivalently `finish_bbox_at(...)` still producing a bbox anchored at the original `start_bbox_at` corner) is unaffected by the pan — i.e. panning must recenter the *view*, not silently cancel or corrupt the drag already in progress. |
| 2(ii) | Same as 2(i), but for `MODE_POLYGON` with vertices already placed | `set_mode("polygon")`, call `add_polygon_vertex_at(x1, y1)` and `add_polygon_vertex_at(x2, y2)` (mirroring `test_polygon_drawing_via_direct_calls_produces_valid_multipolygon_wkt`'s existing setup), exercise the same secondary interaction as 2(i), and assert the view recenters **and** the two already-placed vertices are still present and unchanged (`len(canvas._vertices) == 2`, or an equivalent public accessor if the implementer adds one) — panning must never discard in-progress polygon vertices. |
| 2(iii) | Zoom continues to work identically regardless of the pan-mechanism change (regression guard) | Re-run the existing `test_zoom_by_changes_zoom_level_and_is_clamped` (or an equivalent) with `self._mode` set to `"bbox"`/`"polygon"` explicitly, confirming this round's fix does not accidentally gate zoom on mode (it already isn't gated today — this is a regression guard, not new behavior). |

No test file or executable code for this half is added by this round; the table above is the
complete, actionable specification for whichever round picks this up next.

## Traceability table

| ID | Summary | Test(s) | Automation |
|---|---|---|---|
| E-QPB-003 / FR-QPB-078 / NFR-QPB-058 (offline generation with no VWorld key at all) | A missing VWorld API key in offline mode fails with a clear, non-technical, actionable message — never the raw `KeyError` repr, never an uncaught exception | `test_offline_vworld_api_key_collection.py::test_offline_missing_vworld_api_key_fails_with_actionable_message_not_raw_keyerror` | auto (`qgis`-marked) |
| E-QPB-003 / FR-QPB-078 (offline generation with the key present, companion/regression) | Once `vworld_api_key` is present for offline mode, this specific failure mode does not occur | `test_offline_vworld_api_key_collection.py::test_offline_with_vworld_api_key_present_does_not_hit_the_missing_key_failure_path` | auto (`qgis`-marked) |
| FR-QPB-078 / NFR-QPB-058 (wizard-widget reachability of the offline key input, Bug 1(a)) | The VWorld key input control is actually visible/enabled once offline mode is selected in a real wizard | *(no test in this round — see "Genuinely out of this harness's reach" table, row 1(a))* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| FR-QPB-078 / NFR-QPB-058 (wizard `_collect_config()` wiring, Bug 1(b)) | A typed-in offline-mode VWorld key actually reaches `config["basemap"]["vworld_api_key"]` | *(no test in this round — see "Genuinely out of this harness's reach" table, row 1(b))* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| FR-QPB-025 / Decision Log D-24 (drawing-canvas pan reachability, human-confirmed half) | A real human can pan/recenter the wizard's drawing canvas while a shape is in progress, without losing it | `test_map_canvas_pan_navigability.py::test_wizard_drawing_canvas_can_be_panned_to_reach_an_arbitrary_location_while_drawing` | **manual** (documented, skipped) |
| FR-QPB-025 / Decision Log D-24 (drawing-canvas pan mechanism, offscreen-automatable half) | Some input path pans the view while `self._mode` is `MODE_BBOX`/`MODE_POLYGON`, without disturbing in-progress drawing state; zoom is unaffected | *(no test in this round — see "Genuinely out of this harness's reach" table, rows 2(i)-2(iii))* | **routed to `tests/unit/test_map_canvas.py`**, not yet written |

## Ambiguities / gaps found (routing recommendation, not silently resolved)

1. **Bug 1's own requirement text (`E-QPB-003`/`FR-QPB-078`/`NFR-QPB-058`) is clear and sufficient
   as written** — no ambiguity found. "Missing entirely" is treated as a specific case of
   `E-QPB-003`'s "unverifiable" (there is nothing to verify when the key was never collected at
   all); this is a straightforward application of the existing text, not an invented behavior.
2. **Bug 2's contract is grounded in an interpretive reading of `FR-QPB-025`/Decision Log D-24,
   not a literal spec sentence about panning** — see the "Textual-grounding note" above. This
   round proceeded to cover it anyway, per the orchestrating task's own explicit, well-evidenced
   direction, but flags this interpretive step for the user's/spec-writer's awareness rather than
   silently asserting it is beyond question.
3. **No numbered `AC-###` exists for either gap.** Mirroring the immediately preceding
   `qgis_manual_path_override` round's own precedent (Section 18's numbering has no dedicated
   entries for `E-QPB-003`'s "actionable error" clause, `FR-QPB-078`'s key-collectibility
   implication, or `FR-QPB-025`'s navigability implication specifically), the new tests trace
   directly to the FR/E/NFR/Decision-Log text itself. If the stakeholder wants dedicated
   `AC-QPB-###` entries recorded in Section 18 for either, that is a `spec-writer` decision, not
   made here.
4. **Which secondary-interaction mechanism fixes Bug 2 is deliberately left unspecified** by this
   round (a modifier+left-click-drag, a right-button drag, or an explicit pan-mode-toggle
   control) — `FR-QPB-025` does not mandate a specific input mechanism, only that the canvas be
   genuinely navigable; the contract table above specifies only the required *effect*, not the
   *mechanism*, mirroring `FR-QPB-008`'s own "the exact contract for how a UI would collect
   `manual_path`... is left unspecified" precedent.
