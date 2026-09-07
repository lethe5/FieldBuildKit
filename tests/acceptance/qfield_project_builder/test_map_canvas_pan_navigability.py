"""Bug 2 (Category A conformance defect; test-designer conformance-gap round, 2026-08-27): the
wizard's interactive drawing canvas (`qfield_builder.ui.map_canvas.MapCanvas`) cannot be panned
while a user is actually drawing a site/plot boundary or an offline bbox extent, making any area
of interest that is not already near the canvas's fixed initial view center literally unreachable
through the wizard's own UI.

`FR-QPB-025` ("...or drawing features on an interactive map") and Decision Log **D-24** (which
added real OpenStreetMap tile imagery to this exact canvas specifically because "the stakeholder
found the graticule-only canvas hard to use in practice") together establish that this canvas must
be genuinely navigable to locate a real survey site -- not merely capable of drawing a shape
somewhere on a fixed, uncontrollable view. A canvas whose view can never be recentered away from
its hardcoded default center fails to be "interactive" (FR-QPB-025's own word) for any site outside
its immediate default viewport, by any ordinary reading of that word. This round independently
re-verified the reported root cause by direct code reading of `qfield_builder/ui/map_canvas.py`
and `qfield_builder/ui/wizard.py` (not by trusting the bug report handed to this round at face
value):

- `MapCanvas` already has fully working pan support: `MODE_PAN`, `pan_by_pixels()`, and
  `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` branches (map_canvas.py:423-461) that pan
  on left-button drag when `self._mode == MODE_PAN`. Scroll-wheel zoom (`wheelEvent` ->
  `zoom_by()`, line 470-473) is unconditional -- confirmed by direct reading that it works
  regardless of `self._mode`.
- BUT both real usages of this widget in the wizard hardcode a non-pan mode and expose no way to
  switch into pan mode: `SiteInputPage.__init__` (`wizard.py:400`,
  `self.draw_map_canvas.set_mode("polygon")`) and `ConnectivityBasemapPage.__init__`
  (`wizard.py:732`, `self.offline_map_canvas.set_mode("bbox")`). Neither page ever calls
  `set_mode("pan")` again, offers a mode-toggle control, or wires any secondary input path (a
  modifier key, an alternate mouse button, or a UI toggle) that would invoke panning while in
  `"polygon"`/`"bbox"` mode -- confirmed by inspecting every `set_mode`/`MODE_PAN` reference in
  `wizard.py`.
- `MapCanvas.mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` (map_canvas.py:423-460)
  contain no `event.modifiers()` check anywhere, and every branch where
  `event.button() != Qt.MouseButton.LeftButton` falls through to
  `super().mousePressEvent(event)`/`super().mouseReleaseEvent(event)` and returns immediately --
  confirming there is no existing right-button (or other secondary-button) pan path in the widget
  itself either; this is not merely a missing wizard-level wiring gap.
- Net effect, confirmed by the stakeholder's own real-device report ("Cannot pan a map, so it is
  hard to make a rectangle where I want."): a user can zoom the wizard's drawing canvas in/out
  (centered on the current, fixed view center) but can never recenter the view while actually
  drawing -- if the real area of interest is not already near the canvas's initial default center
  (`center_lon=127.5, center_lat=36.5`), it is literally unreachable through this UI.

**Textual-grounding note (transparency, not a request for spec change -- the orchestrating task
explicitly frames this as an already-diagnosed Category A conformance gap, and this round
independently confirmed the root cause above rather than merely accepting that framing).**
`specs/qfield-project-builder.md`'s own literal text does not contain the word "pan" anywhere, and
Decision Log D-24's own fix for the prior "hard to use in practice" complaint was adding OSM tile
imagery, not a pan-while-drawing capability specifically. This round's contract below is grounded
in FR-QPB-025's "interactive map" wording plus D-24's own stated rationale (a canvas that is "hard
to use in practice" to locate a real site), not a literal transcription of explicit spec prose
about panning. This is reported here per this role's ambiguity-handling duty to flag an
interpretive step rather than silently treat it as beyond question -- while still proceeding to
specify and cover it, per the orchestrating task's own explicit, well-evidenced direction.

**What this file covers, and what it does not.** `MapCanvas` is a plain PySide6 `QWidget` with no
`qfield_builder.acceptance_api`-mediated surface at all (unlike `build_project()`/
`check_runtime()`, etc.) -- exercising its own mouse-event/mode-gating logic requires directly
constructing and driving the widget, which is exactly the class of "PySide6 wizard's own code
structure" testing `HARNESS_CONTRACT.md`'s own "what these tests deliberately do not invent"
section already excludes, and which this suite's own established precedent
(`../qfield_project_builder_credential_storage_mechanism.traceability.md`'s "Scope-boundary
finding") treats as the `implementer` role's `tests/unit/` mandate, not `test-designer`'s
`tests/acceptance/`-only file-scope boundary. This file therefore contains only the genuinely
GUI-reachability-only half of this gap -- a `manual`-marked placeholder, mirroring the established
`AC-QPB-104`/`FR-QPB-008` precedent (`test_symbol_styling.py`, `test_qgis_manual_path_override.py`)
-- for a real human confirming they can actually drag/scroll to reach an arbitrary location on
screen without losing their in-progress drawing. See
`../qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md` for
the fully specified, offscreen-automatable contract a `tests/unit/test_map_canvas.py`-level test
must satisfy for the headlessly-testable half of this gap (which secondary-interaction mechanism
the implementer chooses -- a modifier+left-click-drag, a right-button drag, or an explicit
pan-mode-toggle control -- is left open there; the *effect* the contract requires is specified
precisely).
"""
from __future__ import annotations

import pytest


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "FR-QPB-025/Decision Log D-24 require the wizard's drawing canvas to be genuinely usable "
        "to locate a real survey site -- which requires that a real user can actually pan/recenter "
        "the view while in the middle of drawing a polygon or a bbox, not merely zoom in place. "
        "This is a literal, on-screen PySide6 mouse-interaction/reachability fact (can a real "
        "user, using a real mouse/trackpad, actually drag the map to a different location while "
        "drawing is in progress, without losing their in-progress shape) -- not a "
        "generated-project artifact this harness's black-box build_project()/validate_project() "
        "convention can reach, and not a pure, GUI-independent logic function. No automated "
        "GUI-driving mechanism exists in this harness for this, mirroring this suite's own "
        "established convention for exactly this category of criterion (e.g. AC-QPB-104's "
        "wizard-step-sequencing placeholder in test_symbol_styling.py, and FR-QPB-008's "
        "wizard-control-reachability placeholder in test_qgis_manual_path_override.py)."
        "\n\nManual QA steps: (1) Launch the desktop wizard and reach Step 3 (site/plot input); "
        "choose 'draw on map' and begin placing polygon vertices at a location near the canvas's "
        "default initial view. (2) Without finishing the shape, attempt to pan/recenter the map to "
        "a genuinely different location (e.g. a different province) using whatever interaction the "
        "implementer has wired up (a modifier+drag, a secondary mouse button, or an explicit "
        "pan-mode toggle control). (3) Confirm the view actually recenters, the already-placed "
        "vertices are NOT lost or reset by panning, and the user can then resume placing vertices "
        "at the new location and finish the shape normally (matching the underlying "
        "MapCanvas.pan_by_pixels()/mode-gating contract specified in this round's traceability "
        "file). (4) Repeat at Step 4 (offline extent), 'draw area on map,' confirming the same "
        "panning capability is reachable both before starting a bbox drag and (if the chosen "
        "interaction allows it) mid-drag, and that scroll-wheel zoom (already confirmed working in "
        "every mode) continues to work throughout. (5) Confirm the resulting drawn shape/bbox, "
        "once finished, is geometrically correct for the newly panned-to location (not silently "
        "still anchored to the original default view)."
    )
)
def test_wizard_drawing_canvas_can_be_panned_to_reach_an_arbitrary_location_while_drawing():
    raise AssertionError("should never run while skipped — see skip reason")
