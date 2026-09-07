"""Wizard Step 6 — symbol styling configuration (Section 6.6/6.7, Section 9, Section 18.2/18.5;
Decision Log D-61/D-65, closing Open Questions O-24–O-27).

Covers:
- AC-QPB-100: every generated point layer and polygon layer (excluding the Type 4 `community`
  layer, which keeps its existing DR-QPB-051 rule-based renderer) receives a deliberately
  configured minimalist default symbol at build time — a single flat fill plus a thin outline for
  polygons; a small, solid circle marker for points — never QGIS's own undifferentiated default.
- AC-QPB-101: the wizard's offline, build-time-bundled Tabler icon-name index is filtered live, by
  substring, with zero network access; selecting one icon while online fetches its SVG (the single
  network request FR-QPB-011(d) permits) and, on success, every point layer of the generated
  project uses it, with the SVG embedded at a project-relative path; a failed/offline fetch falls
  back to the minimalist default without blocking generation.
- AC-QPB-102 (partial — see the note below and this round's traceability file): no attribution/
  license notice is shown anywhere in the generated project when a downloaded Tabler icon is used
  (MIT license, confirmed). The sibling "compliant User-Agent header / no automatic retry" half of
  AC-QPB-102 is an internal desktop-application HTTP-client-construction concern, not a
  generated-project artifact this harness's black-box convention can reach (mirrors Decision Log
  D-53/D-55's own credential-storage precedent, `tests/acceptance/README.md`) — routed to the
  `implementer` role's own unit-test mandate, not tested here. See
  `qfield_project_builder_symbol_styling.traceability.md` for the full determination.
- AC-QPB-104: the new Step 6 exists between Step 5 and the renumbered Step 7 (a wizard-UI-sequencing
  fact — see the `manual`-marked placeholder near the end of this file, and this round's
  traceability file, for why this specific clause cannot be automated); within one generated
  project, every point layer shares one identical styling choice and every polygon layer shares one
  identical styling choice; and a styling choice made for one generated project is never
  automatically carried over to a separately generated project of the same survey type.

FR-QPB-011(d)'s network-boundary rule (the Tabler SVG-fetch request is permitted strictly and only
after the user has already selected a specific icon by name from the offline bundled index — never
for live search) is exercised indirectly here: `search_bundled_tabler_icon_names` (below) is a pure,
offline function with no network-capable parameters at all, and `build_project`'s own
`symbol_styling.tabler_svg_fetch` fake double is only ever consulted once selection has already
happened in the build config — there is no code path in this harness (or, by construction, in the
generated build config shape) for a "search" action to also trigger an SVG fetch.

See HARNESS_CONTRACT.md's "New (Decision Log D-64–D-69...)" section (functions 13–15, and the
`symbol_styling` `build_project` config/return additions) for the harness surface these tests use,
and its notes on why exact color/outline values and the exact `ValueRelation`-adjacent internal
QGIS strings are not hardcoded here.
"""
from __future__ import annotations

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

# Every survey type's own minimalist-eligible point layer(s) and polygon layer(s), per Section 8 —
# `community` (Type 4) is deliberately excluded from the polygon list: DR-QPB-051/FR-QPB-120 keep
# its own existing rule-based renderer unaffected, it is never minimalist-styled.
POINT_LAYERS_BY_TYPE: dict[str, list[str]] = {
    "simple_inventory": ["inventory_observation"],
    "temporary_plots": ["survey"],
    "permanent_plots": ["plot"],
    "vegetation_mapping": [],
}
MINIMALIST_POLYGON_LAYERS_BY_TYPE: dict[str, list[str]] = {
    "simple_inventory": [],
    "temporary_plots": ["site"],
    "permanent_plots": ["site"],
    "vegetation_mapping": ["site"],
}


def _point_layer_cases():
    return [
        (survey_type, layer)
        for survey_type, layers in POINT_LAYERS_BY_TYPE.items()
        for layer in layers
    ]


def _polygon_layer_cases():
    return [
        (survey_type, layer)
        for survey_type, layers in MINIMALIST_POLYGON_LAYERS_BY_TYPE.items()
        for layer in layers
    ]


# --- AC-QPB-100 ------------------------------------------------------------------


@pytest.mark.parametrize("survey_type,layer_name", _point_layer_cases())
def test_ac100_point_layer_has_a_minimalist_single_symbol_circle_marker_renderer(
    inspect_layer_renderer, built_project_by_type, survey_type, layer_name
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    info = inspect_layer_renderer(result["project_dir"], layer_name)
    assert info["renderer_class"] == "QgsSingleSymbolRenderer", (
        f"AC-QPB-100/FR-QPB-120: {survey_type}.{layer_name} must receive a deliberately configured "
        f"single-symbol renderer, not a rule-based/categorized/graduated one — got {info}"
    )
    assert "SimpleMarker" in info["symbol_layer_types"], (
        f"AC-QPB-100/FR-QPB-120: {survey_type}.{layer_name}'s point marker must be a SimpleMarker "
        f"symbol layer (small, solid circle marker) — got {info}"
    )
    assert info["marker_shape"] == "circle", (
        f"AC-QPB-100/FR-QPB-120 ('a small, solid circle marker for every point layer'): "
        f"{survey_type}.{layer_name}'s marker shape must be 'circle' — got {info}"
    )


@pytest.mark.parametrize("survey_type,layer_name", _polygon_layer_cases())
def test_ac100_polygon_layer_has_a_minimalist_single_symbol_fill_renderer(
    inspect_layer_renderer, built_project_by_type, survey_type, layer_name
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    info = inspect_layer_renderer(result["project_dir"], layer_name)
    assert info["renderer_class"] == "QgsSingleSymbolRenderer", (
        f"AC-QPB-100/FR-QPB-120: {survey_type}.{layer_name} must receive a deliberately configured "
        f"single-symbol renderer, not a rule-based/categorized/graduated one — got {info}"
    )
    assert "SimpleFill" in info["symbol_layer_types"], (
        f"AC-QPB-100/FR-QPB-120 ('a single flat fill color plus a thin, contrasting outline for "
        f"every polygon layer'): {survey_type}.{layer_name} must use a SimpleFill symbol layer — "
        f"got {info}"
    )


def test_ac100_type4_community_layer_keeps_its_own_rule_based_renderer_unaffected(
    inspect_layer_renderer, built_project_by_type
):
    """FR-QPB-120's own explicit carve-out: `community` (Type 4) is excluded from minimalist
    styling and keeps DR-QPB-051's existing rule-based (field-checked) renderer, unaffected by this
    entry — negative control, confirming AC-QPB-100 is not misapplied to it. Complements (does not
    replace)
    `test_geopackage_schema_by_type.py::test_ac015_community_symbology_rule_exists_in_qgs_project`,
    which already confirms the rule-based renderer's own is_field_checked content via raw `.qgs`
    text; this test confirms the *renderer class* itself, via the new `inspect_layer_renderer`
    harness function, to directly support AC-QPB-100's own "excluding the Type 4 community layer"
    clause.
    """
    result = built_project_by_type("vegetation_mapping")
    assert result["success"], result.get("error_message")

    info = inspect_layer_renderer(result["project_dir"], "community")
    assert info["renderer_class"] != "QgsSingleSymbolRenderer", (
        f"FR-QPB-120: the community layer must keep its own DR-QPB-051 rule-based renderer, not "
        f"receive the minimalist single-symbol treatment — got {info}"
    )


# --- AC-QPB-101, clause 1 (offline, live, filtered search) -----------------------------------


def test_search_bundled_tabler_icon_names_filters_case_insensitively_by_substring(
    search_bundled_tabler_icon_names,
):
    result = search_bundled_tabler_icon_names("home")
    assert result["matches"], "expected at least one bundled icon name matching 'home'"
    assert all("home" in name.lower() for name in result["matches"]), (
        f"FR-QPB-121: every returned match must contain the query as a substring "
        f"(case-insensitive) — got {result['matches']}"
    )

    upper_result = search_bundled_tabler_icon_names("HOME")
    assert set(upper_result["matches"]) == set(result["matches"]), (
        "FR-QPB-121: the search must be case-insensitive"
    )


def test_search_bundled_tabler_icon_names_reports_a_real_nontrivial_bundled_index(
    search_bundled_tabler_icon_names,
):
    """FR-QPB-121/Decision Log D-65: a real, build-time-bundled static index of Tabler icon names
    (~6,184 names at time of research) must exist — not asserting the exact count (Decision Log
    D-65's own text is explicit this may drift as Tabler's icon set changes over time), only that
    the bundled index is real and non-trivial (not an empty/stub list)."""
    result = search_bundled_tabler_icon_names("")
    assert result["total_bundled_names"] > 1000, (
        f"FR-QPB-121: expected a real, non-trivial bundled Tabler icon-name index — got "
        f"total_bundled_names={result['total_bundled_names']}"
    )


def test_search_bundled_tabler_icon_names_returns_no_matches_for_a_nonexistent_query(
    search_bundled_tabler_icon_names,
):
    result = search_bundled_tabler_icon_names("zzz_definitely_not_a_real_tabler_icon_name_zzz")
    assert result["matches"] == []


# --- AC-QPB-101, clauses 2/3 (select -> fetch -> embed; fallback on failure) ------------------


def _build_with_symbol_styling(acceptance_api, tmp_path, survey_type, symbol_styling, name="proj"):
    config = make_base_config(survey_type)
    config["symbol_styling"] = symbol_styling
    out_dir = tmp_path / name
    return acceptance_api.build_project(config, str(out_dir))


_FAKE_SVG_CONTENT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'


def test_ac101_successful_selection_embeds_the_svg_and_every_point_layer_uses_it(
    acceptance_api, inspect_layer_renderer, tmp_path
):
    symbol_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    result = _build_with_symbol_styling(
        acceptance_api, tmp_path, "simple_inventory", symbol_styling
    )
    assert result["success"], result.get("error_message")
    assert result.get("symbols_dir"), (
        "AC-QPB-101/FR-QPB-121: expected build_project() to report a symbols_dir once a Tabler "
        f"icon was successfully fetched — got {result}"
    )

    info = inspect_layer_renderer(result["project_dir"], "inventory_observation")
    assert "SvgMarker" in info["symbol_layer_types"], (
        f"AC-QPB-101/FR-QPB-121: every point layer must use the fetched SVG as its marker symbol "
        f"once selection succeeds — got {info}"
    )
    assert info["svg_relative_path"], "expected a project-relative SVG path to be reported"


def test_ac101_embedded_svg_is_referenced_by_a_project_relative_path_inside_the_output_folder(
    acceptance_api, inspect_layer_renderer, tmp_path
):
    """FR-QPB-121/FR-QPB-091/DR-QPB-012: the downloaded SVG must be embedded into the generated
    project's own output folder and referenced only by a path relative to the project folder —
    never an absolute path, and never a path outside the project's own folder tree."""
    from pathlib import Path

    symbol_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "leaf",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    result = _build_with_symbol_styling(
        acceptance_api, tmp_path, "simple_inventory", symbol_styling, name="proj_relpath"
    )
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    info = inspect_layer_renderer(result["project_dir"], "inventory_observation")
    svg_relative_path = info["svg_relative_path"]
    assert svg_relative_path, "expected a reported project-relative SVG path"
    assert not svg_relative_path.startswith("/"), "must be a relative path, not POSIX-absolute"
    assert ":" not in svg_relative_path[:3], "must not be a Windows drive-letter absolute path"

    resolved = (project_dir / svg_relative_path).resolve()
    assert str(resolved).startswith(str(project_dir.resolve())), (
        f"the embedded SVG's own resolved path ({resolved}) must remain inside the generated "
        f"project's own folder tree ({project_dir.resolve()})"
    )
    assert resolved.is_file(), f"expected the embedded SVG file to actually exist at {resolved}"

    symbols_dir = result.get("symbols_dir")
    assert symbols_dir, "expected build_project() to report symbols_dir"
    assert Path(symbols_dir).resolve() == (project_dir / Path(symbols_dir).name).resolve() or str(
        Path(symbols_dir).resolve()
    ).startswith(str(project_dir.resolve())), "symbols_dir must be inside the project folder"


@pytest.mark.parametrize("failure_mode", ["network_error", "http_error", "timeout"])
def test_ac101_failed_fetch_falls_back_to_the_minimalist_default_without_blocking_generation(
    acceptance_api, inspect_layer_renderer, tmp_path, failure_mode
):
    symbol_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": failure_mode, "svg_content": ""}},
    }
    result = _build_with_symbol_styling(
        acceptance_api, tmp_path, "simple_inventory", symbol_styling, name=f"proj_{failure_mode}"
    )
    assert result["success"], (
        f"FR-QPB-121: a failed SVG fetch ({failure_mode}) must not block project generation — "
        f"{result.get('error_message')}"
    )
    assert not result.get("symbols_dir"), (
        "expected no symbols_dir to be reported when the fetch failed"
    )

    info = inspect_layer_renderer(result["project_dir"], "inventory_observation")
    assert "SvgMarker" not in info["symbol_layer_types"], (
        f"FR-QPB-121: on a failed fetch, the minimalist default marker must remain in use, not a "
        f"partially-applied SVG marker — got {info}"
    )
    assert "SimpleMarker" in info["symbol_layer_types"] and info["marker_shape"] == "circle", (
        f"FR-QPB-120/FR-QPB-121: the minimalist default (small, solid circle marker) must remain "
        f"the point-marker symbol after a failed fetch — got {info}"
    )


# --- AC-QPB-102 (generated-project half only — see module docstring) -------------------------


def _scan_project_text_for_tabler_mentions(project_dir) -> list[str]:
    from pathlib import Path

    hits = []
    root = Path(project_dir)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".qgs", ".json", ".md", ".txt", ".qml"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "tabler" in text.lower():
            hits.append(str(path))
    return hits


def test_ac102_no_attribution_or_license_notice_appears_anywhere_in_the_generated_project(
    acceptance_api, tmp_path
):
    """AC-QPB-102/NFR-QPB-080 (revised, Decision Log D-65): Tabler Icons is confirmed MIT-licensed
    — no attribution/license notice is legally required, and none may be shown, anywhere in the
    generated project. Scans every text-like file in the generated project's own output folder for
    any mention of "tabler" (case-insensitive) — the only source such a notice could ever come
    from, since no other Tabler-related content exists anywhere in this application."""
    symbol_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    result = _build_with_symbol_styling(
        acceptance_api, tmp_path, "simple_inventory", symbol_styling, name="proj_no_attribution"
    )
    assert result["success"], result.get("error_message")

    hits = _scan_project_text_for_tabler_mentions(result["project_dir"])
    assert hits == [], (
        f"AC-QPB-102/NFR-QPB-080 (revised): no attribution/license notice may appear anywhere in "
        f"the generated project (MIT license, confirmed) — found 'tabler' mentioned in: {hits}"
    )


# --- Live network confirmation (opt-in) --------------------------------------------------------


@pytest.mark.network
def test_network_tabler_icon_svg_fetch_returns_a_real_svg_response(fetch_tabler_icon_svg):
    """See HARNESS_CONTRACT.md function 13's own disclosed limitation: this round did not itself
    re-verify Tabler's exact download URL shape live; only the general response shape is asserted
    here (HTTP 200, an svg+xml-family content type, SVG-looking body text)."""
    result = fetch_tabler_icon_svg("home")
    assert result["http_status"] == 200
    assert result["content_type"] and "svg" in result["content_type"].lower()
    assert result["svg_text"] and result["svg_text"].lstrip().startswith(("<svg", "<?xml"))


# --- AC-QPB-104 --------------------------------------------------------------------------------


def test_ac104_within_one_project_every_point_layer_shares_the_same_symbol_choice(
    acceptance_api, inspect_layer_renderer, tmp_path
):
    """AC-QPB-104: 'all point layers of that project share one identical styling choice.' Written
    generically (iterating every point layer this survey type's own schema defines) so it would
    catch a regression if the schema ever gained a second point layer for one survey type; under
    the *current* schema (Section 8), every survey type has at most one minimalist-eligible point
    layer, so this assertion is structurally vacuous today for any single survey type — disclosed
    here, not hidden. See `test_ac104_symbol_styling_choice_is_not_carried_over_between_separately_
    generated_projects` below for the criterion's other, non-vacuous half."""
    symbol_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    for survey_type, layers in POINT_LAYERS_BY_TYPE.items():
        if len(layers) < 2:
            continue  # nothing to compare within this project — see docstring
        out_name = f"proj_uniform_{survey_type}"
        result = _build_with_symbol_styling(
            acceptance_api, tmp_path, survey_type, symbol_styling, name=out_name
        )
        assert result["success"], result.get("error_message")
        infos = [inspect_layer_renderer(result["project_dir"], layer) for layer in layers]
        svg_paths = {info["svg_relative_path"] for info in infos}
        assert len(svg_paths) == 1, (
            f"AC-QPB-104: every point layer of {survey_type} must share the same styling choice — "
            f"got {svg_paths}"
        )


def test_ac104_symbol_styling_choice_is_not_carried_over_between_separately_generated_projects(
    acceptance_api, inspect_layer_renderer, tmp_path
):
    """AC-QPB-104: 'neither project's Step 6 styling choice is automatically carried over to the
    other — each build's styling choice is made fresh.' Builds project A with a Tabler icon
    selected, then project B of the same survey type with no symbol_styling config at all (the
    wizard's own minimalist default), and confirms B is not contaminated by A's prior choice."""
    tabler_styling = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    project_a = _build_with_symbol_styling(
        acceptance_api, tmp_path, "simple_inventory", tabler_styling, name="proj_a_tabler"
    )
    assert project_a["success"], project_a.get("error_message")

    config_b = make_base_config("simple_inventory")
    # symbol_styling deliberately omitted entirely — must not inherit project A's choice.
    project_b = acceptance_api.build_project(config_b, str(tmp_path / "proj_b_default"))
    assert project_b["success"], project_b.get("error_message")

    info_b = inspect_layer_renderer(project_b["project_dir"], "inventory_observation")
    assert "SvgMarker" not in info_b["symbol_layer_types"], (
        "AC-QPB-104: a separately generated project must not automatically inherit a prior "
        f"project's Tabler icon choice — got {info_b}"
    )
    assert "SimpleMarker" in info_b["symbol_layer_types"] and info_b["marker_shape"] == "circle", (
        f"AC-QPB-104: project B must use its own fresh minimalist default — got {info_b}"
    )


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-QPB-104's first clause requires confirming that the wizard actually presents a new "
        "Step 6, 'Symbol styling configuration' (FR-QPB-123), between the existing Step 5 "
        "(optional photo identification toggle) and the renumbered Step 7 (Review and build) — a "
        "literal, on-screen PySide6 wizard-UI-sequencing fact, not a generated-project artifact "
        "this harness's black-box build_project()/validate_project() convention can reach, and not "
        "a pure, GUI-independent logic function the way FR-QPB-121's own search-filter logic is "
        "(see test_search_bundled_tabler_icon_names_* above). This project's hard QGIS-isolation "
        "rule is unrelated to this specific gap (it concerns QGIS/QApplication construction, not "
        "the PySide6 wizard), but no automated GUI-driving mechanism exists in this harness either "
        "way, mirroring this suite's own established 'what these tests deliberately do not invent' "
        "exclusion for 'UI widget/event names.'"
        "\n\nManual QA steps: (1) Launch the desktop wizard and complete Steps 1-5 for any survey "
        "type. (2) Confirm the very next step displayed is titled (or otherwise clearly "
        "identifiable as) 'Symbol styling configuration,' offering the minimalist default and a "
        "Tabler icon search. (3) Proceed from that step and confirm the next step displayed is "
        "'Review and build' (FR-QPB-040/041), not a step skipped or reordered."
    )
)
def test_ac104_wizard_presents_the_new_step6_between_step5_and_the_renumbered_step7():
    raise AssertionError("should never run while skipped -- see skip reason")
