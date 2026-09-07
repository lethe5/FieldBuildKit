"""Wizard Step 6 — live Tabler icon preview-image fetch during search (Section 5.4, FR-QPB-011(d)
(ii), NFR-QPB-080 clauses (5)-(8), Section 18.2; Decision Log D-76, closing Open Question O-35).

Decision Log D-76 supersedes one specific clause of the already-approved, offline-only-search rule
(Decision Log D-65) by adding a second, independently scoped, narrower network-fetch trigger to
FR-QPB-011(d): fetching preview SVG content, live, for the currently visible/matched results of an
in-progress Step 6 icon search, debounced as the user types — never an unbounded background
prefetch of the entire ~5,130-name bundled index, and never for a result not currently rendered on
screen. This is genuinely additional to, and does not replace, the pre-existing fetch-on-selection
mechanism (FR-QPB-011(d)(i)/FR-QPB-121/AC-QPB-101), which is unaffected and not re-tested here.

Covers:
- AC-QPB-117: with no network access available (or every live preview fetch failing/timing out),
  matching icon names are still filtered live from the offline bundled index exactly as before,
  each visible result shows no image in place of a preview, and the user can still select any
  result by name without being blocked and without the application crashing.
- The "never an unbounded background prefetch of the entire bundled index, never for a result not
  currently visible" half of FR-QPB-011(d)(ii) itself, at the level of the new, pure,
  GUI-independent `fetch_tabler_icon_preview_svgs` reference function (HARNESS_CONTRACT.md function
  20): given a set of currently visible/matched names, the function's own fetch scope never
  expands beyond exactly that set.
- That the *existing* AC-QPB-101/FR-QPB-121 offline name-search mechanism
  (`search_bundled_tabler_icon_names`) is unaffected by this round and remains exercised, alongside
  the new preview-fetch function, to demonstrate the two mechanisms have no shared state and no
  dependency on one another (see the "confirmed unaffected, not re-tested" tests below).

Deliberately NOT covered here (see this round's own traceability file for the full, precise routed
`tests/unit/` contract table, and HARNESS_CONTRACT.md's "New (Decision Log D-76)" section /
extended "what these tests deliberately do not invent" list for the reasoning):
- NFR-QPB-080(5): the new preview-fetch request's own compliant `User-Agent` header — an internal
  HTTP-client-construction detail, the same class of criterion this suite has never been able to
  reach for the sibling selection-fetch request either (AC-QPB-102's pre-existing determination).
- NFR-QPB-080(6): real debounce-as-you-type timing — an inherently PySide6 `QTimer`/keystroke-event
  fact this harness cannot drive headlessly.
- NFR-QPB-080(7): real bounded concurrency of in-flight HTTP requests — only meaningfully
  observable against a real, non-fake dispatch mechanism, not a synchronous fake double.
- The literal, on-screen fact that a real preview image actually renders next to a search result
  once a fetch succeeds (see the `manual`-marked placeholder near the end of this file).
"""
from __future__ import annotations

import pytest

_FAKE_SVG_CONTENT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'


def _uniform_fake(mode: str, svg_content: str | None = None) -> dict:
    entry = {"mode": mode}
    if svg_content is not None:
        entry["svg_content"] = svg_content
    return {"fake": {"default": entry}}


# --- FR-QPB-011(d)(ii): never expands beyond the given, currently visible/matched names --------


def test_preview_fetch_reports_exactly_the_given_names_never_more_never_fewer(
    fetch_tabler_icon_preview_svgs,
):
    """FR-QPB-011(d)(ii): 'never an unbounded background prefetch of the entire ~5,130-name
    bundled index, and never fetched for a result that is not currently visible on screen.' This
    reference function's own contract must never silently expand (or narrow) its fetch scope
    beyond exactly the names it was given -- the caller (the debounced wizard UI, routed to
    `tests/unit/test_wizard.py`) is solely responsible for narrowing that set to what is currently
    visible/matched before ever calling this function."""
    names = ["map-pin", "leaf", "home"]
    result = fetch_tabler_icon_preview_svgs(
        names, _uniform_fake("success", _FAKE_SVG_CONTENT)
    )
    assert set(result["requested_names"]) == set(names), (
        f"expected requested_names to exactly match the given visible/matched names — got "
        f"{result['requested_names']}"
    )
    assert set(result["previews"].keys()) == set(names), (
        f"expected exactly one preview entry per given name, nothing more — got "
        f"{sorted(result['previews'].keys())}"
    )


def test_preview_fetch_never_expands_to_the_rest_of_the_bundled_index(
    fetch_tabler_icon_preview_svgs, search_bundled_tabler_icon_names
):
    """Structural companion to the test above, phrased directly against FR-QPB-011(d)(ii)'s own
    '~5,130-name bundled index' language: given a small subset of real, currently-matched bundled
    names, the function's own reported scope stays exactly that subset, never ballooning toward
    the size of the complete bundled index."""
    total_bundled = search_bundled_tabler_icon_names("")["total_bundled_names"]
    assert total_bundled > 1000, (
        "sanity check: expected a real, non-trivial bundled Tabler icon-name index"
    )

    visible_subset = search_bundled_tabler_icon_names("map")["matches"][:3]
    assert 0 < len(visible_subset) < total_bundled, (
        "expected a small, real, strict subset of the full bundled index to test against"
    )

    result = fetch_tabler_icon_preview_svgs(
        visible_subset, _uniform_fake("success", _FAKE_SVG_CONTENT)
    )
    assert set(result["requested_names"]) == set(visible_subset)
    assert len(result["previews"]) == len(visible_subset)


# --- AC-QPB-117 / NFR-QPB-080(8): graceful, per-result degradation -----------------------------


def test_preview_fetch_reports_svg_content_for_every_name_on_success(
    fetch_tabler_icon_preview_svgs,
):
    names = ["map-pin", "leaf"]
    result = fetch_tabler_icon_preview_svgs(
        names, _uniform_fake("success", _FAKE_SVG_CONTENT)
    )
    for name in names:
        preview = result["previews"][name]
        assert preview["success"] is True
        assert preview["svg_content"] == _FAKE_SVG_CONTENT
        assert preview["error"] is None


@pytest.mark.parametrize("failure_mode", ["network_error", "http_error", "timeout"])
def test_preview_fetch_all_results_failing_never_raises_and_shows_no_image_for_every_result(
    fetch_tabler_icon_preview_svgs, failure_mode
):
    """AC-QPB-117: 'with no network access available (or every live preview fetch
    failing/timing out) ... each visible result shows no image (or a name-only/placeholder row)
    in place of a preview ... without the application crashing.' Exercised here at this function's
    own level: every one of several given names failing at once must not raise, and must report a
    clean 'no image' outcome (success is False, svg_content is None) for every one of them."""
    names = ["map-pin", "leaf", "home"]
    result = fetch_tabler_icon_preview_svgs(names, _uniform_fake(failure_mode))
    assert set(result["previews"].keys()) == set(names), (
        "every given name must still be reported even when every fetch fails — a total failure "
        "must never drop, omit, or raise instead of reporting a result"
    )
    for name in names:
        preview = result["previews"][name]
        assert preview["success"] is False
        assert preview["svg_content"] is None
        assert preview["error"], (
            f"expected a non-empty error code for a failed fetch — got {preview}"
        )


def test_preview_fetch_gracefully_degrades_one_failing_result_without_affecting_its_siblings(
    fetch_tabler_icon_preview_svgs,
):
    """AC-QPB-117: 'a missing/failed preview must simply show no image ... for that one result' —
    i.e. per-result granularity, not an all-or-nothing batch outcome. One result's own preview
    fetch failing must never affect any other, currently-succeeding result's own preview."""
    names = ["map-pin", "leaf", "home"]
    fake = {
        "fake": {
            "default": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT},
            "overrides": {"leaf": {"mode": "network_error"}},
        }
    }
    result = fetch_tabler_icon_preview_svgs(names, fake)

    assert result["previews"]["map-pin"]["success"] is True
    assert result["previews"]["map-pin"]["svg_content"] == _FAKE_SVG_CONTENT
    assert result["previews"]["home"]["success"] is True
    assert result["previews"]["home"]["svg_content"] == _FAKE_SVG_CONTENT

    leaf = result["previews"]["leaf"]
    assert leaf["success"] is False
    assert leaf["svg_content"] is None
    assert leaf["error"] == "network_error"

    # Every name is still reported -- the one failure did not block, omit, or crash the batch.
    assert set(result["previews"].keys()) == set(names)


# --- AC-QPB-117: search-by-name and selection remain fully functional regardless of preview -----
# --- fetch outcome (offline-safe graceful degradation, the criterion's other, structural half) --


def test_search_by_name_is_unaffected_by_a_fully_failed_preview_fetch_batch(
    search_bundled_tabler_icon_names, fetch_tabler_icon_preview_svgs
):
    """AC-QPB-117 / FR-QPB-121 (unaffected by Decision Log D-76): the offline, client-side
    name-filtering search itself must remain fully functional 'with no network access available
    (or every live preview fetch failing/timing out).' `search_bundled_tabler_icon_names` takes no
    parameter derived from, and has no code path connected to, any preview-fetch outcome at all
    (confirmed by its own existing, unaffected contract, HARNESS_CONTRACT.md function 14) -- this
    test demonstrates that directly: calling it again after a batch of visible results' preview
    fetches all failed returns exactly the same match set it always would."""
    search_result = search_bundled_tabler_icon_names("map")
    assert search_result["matches"], "expected at least one bundled icon name matching 'map'"

    preview_result = fetch_tabler_icon_preview_svgs(
        search_result["matches"][:3], _uniform_fake("network_error")
    )
    assert all(not p["success"] for p in preview_result["previews"].values())

    search_result_again = search_bundled_tabler_icon_names("map")
    assert search_result_again["matches"] == search_result["matches"], (
        "AC-QPB-117: offline name-search must remain fully functional and unaffected by a "
        "preceding, fully-failed preview-fetch batch"
    )


def test_selection_fetch_mechanism_is_a_structurally_separate_config_from_preview_fetch(
    fetch_tabler_icon_preview_svgs,
):
    """AC-QPB-101/FR-QPB-011(d)(i) (unaffected by Decision Log D-76 -- confirmed, not re-tested in
    full here; see `test_symbol_styling.py`'s own already-committed, already-passing selection-
    fetch tests, which this round leaves untouched). This test confirms, at the level of the new
    preview-fetch function's own contract, that it has no return key, side effect, or shared state
    that could plausibly feed into or block `build_project()`'s own, entirely separate
    `symbol_styling.tabler_svg_fetch` selection-fetch config -- the two mechanisms take
    independent inputs (a list of currently-visible names vs. one already-selected name) and
    return independent, non-overlapping result shapes, by construction."""
    names = ["map-pin", "leaf"]
    result = fetch_tabler_icon_preview_svgs(names, _uniform_fake("network_error"))
    # The preview-fetch function's own return contract (HARNESS_CONTRACT.md function 20) has
    # exactly two top-level keys -- neither of which is, or resembles, a selection/build-time key
    # (e.g. `symbols_dir`, `success` at the top level) that a subsequent `build_project()` call
    # could possibly read back from here. A failed preview batch cannot leak into, or block, a
    # later, entirely separate selection-fetch/build.
    assert set(result.keys()) == {"requested_names", "previews"}


# --- Manual placeholder: genuinely visual-only fact --------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Decision Log D-76/NFR-QPB-080's own live preview-fetch feature is, at its core, a "
        "literal, on-screen visual fact: a real user, online, typing into the Step 6 search box, "
        "actually sees a small preview image render next to each currently visible/matched result "
        "as they type (debounced), not merely 'no crash / falls back to no image' when it fails "
        "or is unavailable (which new AC-QPB-117 and this file's automated tests above already "
        "cover). This is not a generated-project artifact this harness's black-box "
        "build_project()/validate_project() convention can reach, and not a pure, GUI-independent "
        "logic function the way the new fetch_tabler_icon_preview_svgs() reference function's own "
        "fetch-and-degrade-gracefully contract is (see the tests above) -- mirroring this suite's "
        "own established 'what these tests deliberately do not invent' exclusion for literal "
        "on-screen PySide6 rendering facts (e.g. AC-QPB-104's wizard-step-sequencing placeholder)."
        "\n\nManual QA steps: (1) Launch the desktop wizard with a live network connection and "
        "reach Step 6 (Symbol styling configuration). (2) Select "
        "'Tabler 아이콘을 검색하여 점 기호로 사용' and type a query with several real matches "
        "(e.g. 'map'). (3) Confirm that, shortly "
        "after typing settles (debounced, not on every keystroke), a small preview image appears "
        "next to each currently visible matched result, not just its name. (4) Disconnect network "
        "access mid-search and confirm the currently visible results' rows simply show no image "
        "(or a name-only/placeholder row) without any error dialog, crash, or block on continuing "
        "to search or select a result by name."
    )
)
def test_preview_images_actually_render_next_to_visible_search_results_as_the_user_types():
    raise AssertionError("should never run while skipped -- see skip reason")
