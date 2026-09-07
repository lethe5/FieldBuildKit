"""Acceptance coverage for the approved D-UI-HRA-001 report refinement.

The generated report is assembled by the project-plugin QML sidecar, so the automatic checks
build a project and inspect the generated HTML-producing source.  Those checks cover observable
HTML/CSS/JS contracts without prescribing private implementation names.  They do not claim that
CSS has been laid out correctly in a browser; the skipped ``manual`` checks are the required
browser/print/accessibility evidence gates for rendered behavior.

Functional report behavior remains covered by the existing AC-HRA acceptance module.  This file
only adds the design-review layer and explicit regression guards for the functional behaviors
that D-UI-HRA-001 says must survive the visual refinement.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis


def _build_report(acceptance_api, tmp_path):
    config = make_base_config("permanent_plots", display_name="현장 HTML 보고서")
    result = acceptance_api.build_project(config, str(tmp_path / "ui_refinement_report"))
    assert result["success"], result.get("error_message")
    return result


def _sidecar(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    path = project_dir / f"{result['project_slug']}.qml"
    assert path.is_file(), f"expected generated report sidecar: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report_source(acceptance_api, tmp_path_factory):
    return _sidecar(_build_report(acceptance_api, tmp_path_factory.mktemp("html_report_ui")))


def _has(source: str, *patterns: str) -> bool:
    return any(re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, f"generated report must expose a {name} function"
    opening = match.end() - 1
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : position]
    raise AssertionError(f"unterminated generated report function {name!r}")


def _style_blocks(source: str) -> list[str]:
    return re.findall(r"<style\b[^>]*>(.*?)</style\s*>", source, flags=re.IGNORECASE | re.DOTALL)


_HTML_OPENING_TAG_RE = re.compile(
    r"""
    <(?P<tag>[A-Za-z][A-Za-z0-9:-]*)
    (?P<attributes>
        (?:
            \s+
            [A-Za-z_:][A-Za-z0-9:_.-]*
            (?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s\"'=<>`]+))?
        )*
    )
    \s*/?>
    """,
    flags=re.VERBOSE | re.DOTALL,
)

_HTML_ATTRIBUTE_RE = re.compile(
    r"""
    \s+
    (?P<name>[A-Za-z_:][A-Za-z0-9:_.-]*)
    (?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s\"'=<>`]+))?
    """,
    flags=re.VERBOSE | re.DOTALL,
)


def _inline_style_opening_tags(source: str) -> list[str]:
    """Return syntactically valid opening tags that carry a ``style`` attribute.

    The QML sidecar embeds both report markup and JavaScript.  Matching ``<...style=``
    across arbitrary source lets a JavaScript comparison such as ``i < features.length``
    run into a later ``var style =`` declaration.  Walk only valid opening-tag attributes
    so script bodies cannot masquerade as report markup.
    """
    inline_style_tags = []
    for opening_tag in _HTML_OPENING_TAG_RE.finditer(source):
        attributes = opening_tag.group("attributes")
        position = 0
        while position < len(attributes):
            attribute = _HTML_ATTRIBUTE_RE.match(attributes, position)
            assert attribute is not None, "opening-tag matcher returned unparseable attributes"
            if attribute.group("name").lower() == "style":
                inline_style_tags.append(opening_tag.group(0))
                break
            position = attribute.end()
    return inline_style_tags


_EXTERNAL_HTML_RESOURCE_RE = re.compile(
    r"(?:"
    r"<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*"
    r"\b(?:src|href|data)\s*=\s*['\"]https?://"
    r"|url\(\s*['\"]?https?://"
    r"|@import\s+(?:url\(\s*)?['\"]?https?://"
    r")",
    flags=re.IGNORECASE,
)


# DAC-HRA-001 -------------------------------------------------------------------------------


def test_dac001_design_refinement_preserves_existing_report_data_and_behavior_contract(
    report_source,
):
    """Static guard for the presentation-only boundary; full behavior is mapped to AC-HRA tests."""
    required_contract = (
        r"qpbCollectCurrentRecords",
        r"qpbBuildJoinedRows",
        r"qpbBuildAnalytics",
        r"qpbBuildJoinedCsv",
        r"qpbEscapeHtml",
        r"qpbGeometryToGeoJson",
        r"qpbExportHtmlReport",
        r"project_id",
        r"survey_type",
        r"selected_korean_name",
        r"selected_scientific_name",
        r"selected_ktsn",
        r"qpbReportOutputPath",
        r"qpbJoinedCsvOutputPath",
    )
    missing = [token for token in required_contract if not _has(report_source, token)]
    assert not missing, (
        "DAC-HRA-001: visual refinement must retain existing report data/output behavior "
        f"constituents; missing {missing!r}"
    )


# DAC-HRA-002 -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("<section class='card' style='color: red'>", ["<section class='card' style='color: red'>"]),
        ("<div data-description='style=not-an-attribute'>", []),
        ("<script>for (var i = 0; i < features.length; i++) { var style = {}; }</script>", []),
    ),
)
def test_dac002_inline_style_detector_reads_opening_tag_attributes(source, expected):
    assert _inline_style_opening_tags(source) == expected


def test_dac002_report_has_one_embedded_style_block_no_inline_styles_or_new_html_dependencies(
    report_source,
):
    blocks = _style_blocks(report_source)
    assert re.search(r"<!doctype\s+html|<html\b", report_source, re.IGNORECASE), (
        "DAC-HRA-002: report must remain a standalone HTML document"
    )
    assert len(blocks) == 1, "DAC-HRA-002: structural CSS must be in one document-level style block"
    inline_style_tags = _inline_style_opening_tags(report_source)
    assert not inline_style_tags, (
        "DAC-HRA-002: generated HTML must not contain inline style attributes; found "
        f"{inline_style_tags[0]!r}"
    )
    external = _EXTERNAL_HTML_RESOURCE_RE.search(report_source)
    assert external is None, (
        "DAC-HRA-002: no new remote HTML resource may be required; found "
        f"{external.group(0)!r}"
    )
    assert _has(report_source, r"<script", r"function", r"addEventListener"), (
        "DAC-HRA-002: required local runtime code must remain embedded"
    )
    css = "\n".join(blocks)
    for component in (r"\.card", r"\.toolbar", r"#map", r"table", r"details|summary|panel"):
        assert _has(css, component), (
            "DAC-HRA-002: cards, toolbar, map, details, and table need a coherent shared style layer"
        )
    assert _has(css, r"border-radius", r"gap", r"background(?:-color)?", r"border"), (
        "DAC-HRA-002: report components need consistent surface, border, radius, and spacing tokens"
    )


# DAC-HRA-003 -------------------------------------------------------------------------------


def test_dac003_css_defines_375px_responsive_shell_and_contained_table_scrolling(report_source):
    css = "\n".join(_style_blocks(report_source))
    assert re.search(r"@media\s*\([^)]*max-width\s*:", css, re.IGNORECASE), (
        "DAC-HRA-003: responsive CSS breakpoint is required"
    )
    assert _has(css, r"overflow-x\s*:\s*auto", r"overflow-x\s*:\s*scroll"), (
        "DAC-HRA-003: a wide joined table must scroll inside its own region"
    )
    assert _has(css, r"table[^{}]*[-_]?(?:wrap|container|region)", r"table-wrap", r"table-container"), (
        "DAC-HRA-003: table overflow must be attached to a labeled/container region"
    )
    assert _has(css, r"box-sizing\s*:\s*border-box", r"min-width\s*:\s*0", r"max-width\s*:\s*100%"), (
        "DAC-HRA-003: the page shell must have an explicit narrow-layout containment rule"
    )


# DAC-HRA-004 -------------------------------------------------------------------------------


def test_dac004_sections_have_stable_anchors_and_responsive_sticky_table_of_contents(report_source):
    assert _has(report_source, r"table.?of.?contents", r"\bTOC\b", r"toc"), (
        "DAC-HRA-004: report must provide a table of contents for multi-section reports"
    )
    assert _has(report_source, r"href\s*=\s*['\"]#", r"location\.hash", r"scrollIntoView"), (
        "DAC-HRA-004: section navigation must use anchor-linked targets"
    )
    assert _has(report_source, r"position\s*:\s*sticky"), (
        "DAC-HRA-004: wider layouts must support sticky navigation"
    )
    assert _has(report_source, r"scroll-margin-top", r"scroll-padding-top", r"padding-top"), (
        "DAC-HRA-004: anchored headings/focused content need an offset from sticky navigation"
    )
    assert _has(report_source, r"@media", r"position\s*:\s*(?:static|relative)", r"display\s*:\s*(?:block|flex)"), (
        "DAC-HRA-004: narrow layouts must collapse sticky navigation into normal flow"
    )


# DAC-HRA-005 -------------------------------------------------------------------------------


def test_dac005_theme_toggle_persists_and_does_not_replace_report_state(report_source):
    assert _has(report_source, r"localStorage\.getItem", r"localStorage\s*\[\s*['\"]getItem"), (
        "DAC-HRA-005: report must restore the persisted theme when storage is available"
    )
    assert _has(report_source, r"localStorage\.setItem", r"localStorage\s*\[\s*['\"]setItem"), (
        "DAC-HRA-005: report must persist the selected theme"
    )
    assert _has(report_source, r"data-theme", r"classList\.(?:add|toggle|remove)", r"theme")
    assert _has(report_source, r"dark", r"light"), "DAC-HRA-005: both theme states must be represented"
    assert _has(report_source, r"aria-pressed", r"aria-label", r"role\s*=\s*['\"]button"), (
        "DAC-HRA-005: the theme control needs an accessible name/state"
    )
    assert _has(report_source, r"try\s*\{[\s\S]{0,500}localStorage", r"storage.*unavailable", r"catch\s*\("), (
        "DAC-HRA-005: storage failure must not block the current-document toggle"
    )


# DAC-HRA-006 -------------------------------------------------------------------------------


def test_dac006_print_css_keeps_report_content_and_hides_control_chrome(report_source):
    css = "\n".join(_style_blocks(report_source))
    assert re.search(r"@media\s+print", css, re.IGNORECASE), (
        "DAC-HRA-006: report must provide a print stylesheet"
    )
    assert _has(css, r"display\s*:\s*none", r"visibility\s*:\s*hidden"), (
        "DAC-HRA-006: print CSS must hide navigation/control-only chrome"
    )
    assert _has(css, r"background(?:-color)?\s*:\s*(?:white|#fff|#ffffff)", r"color\s*:\s*#(?:111|000|1d1d1f)"), (
        "DAC-HRA-006: print CSS must establish readable light surfaces/text"
    )
    assert _has(report_source, r"map", r"joinedTable", r"cards", r"limitations"), (
        "DAC-HRA-006: printable report content must include map, summaries, table, and notices"
    )


# DAC-HRA-007 -------------------------------------------------------------------------------


def test_dac007_reduced_motion_minimizes_nonessential_motion_without_removing_controls(report_source):
    css = "\n".join(_style_blocks(report_source))
    assert re.search(r"prefers-reduced-motion\s*:\s*reduce", css, re.IGNORECASE), (
        "DAC-HRA-007: CSS must respect prefers-reduced-motion"
    )
    reduced = re.search(
        r"@media\s*\([^)]*prefers-reduced-motion\s*:\s*reduce[^)]*\)\s*\{(.*)",
        css,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert reduced and _has(reduced.group(1), r"transition\s*:\s*(?:none|0s)", r"animation\s*:\s*(?:none|0s)"), (
        "DAC-HRA-007: reduced-motion rules must disable or minimize transitions/animations"
    )
    assert _has(report_source, r"map", r"filter", r"sort", r"csvButton"), (
        "DAC-HRA-007: reduced motion must not remove map/table/CSV controls"
    )


# DAC-HRA-008 -------------------------------------------------------------------------------


def test_dac008_map_is_a_coherent_card_with_local_feature_and_offline_states(report_source):
    css = "\n".join(_style_blocks(report_source))
    assert _has(css, r"#map", r"\.map[-_]?(?:card|panel)")
    assert _has(css, r"height\s*:\s*\d", r"min-height\s*:\s*\d"), (
        "DAC-HRA-008: map card needs a stable readable height"
    )
    assert _has(css, r"border", r"border-radius", r"background(?:-color)?"), (
        "DAC-HRA-008: map card needs surface/border framing"
    )
    assert _has(report_source, r"L\.geoJSON", r"geojson", r"circleMarker", r"marker"), (
        "DAC-HRA-008: local geometry must remain rendered through the existing map path"
    )
    assert _has(report_source, r"invalid", r"missing geometry", r"no valid geometry"), (
        "DAC-HRA-008: invalid/missing geometry must remain explicitly disclosed"
    )
    assert _has(report_source, r"offline", r"no network", r"unavailable"), (
        "DAC-HRA-008: the map needs an explicit offline/background failure state"
    )
    assert _has(report_source, r"attribution", r"OpenStreetMap contributors", r"VWorld"), (
        "DAC-HRA-008: background attribution/status must remain visible"
    )


# DAC-HRA-009 -------------------------------------------------------------------------------


def test_dac009_joined_table_preserves_rows_filters_sorts_and_integrity_markers(report_source):
    required = (
        r"joinedTable",
        r"allRows",
        r"visibleRows",
        r"applyFilter",
        r"data-sort",
        r"missing parent|orphan|integrity",
        r"null|empty",
        r"localeCompare|Number\(|strictDate",
    )
    missing = [token for token in required if not _has(report_source, token)]
    assert not missing, f"DAC-HRA-009: joined-table behavior tokens missing: {missing!r}"
    assert _has(report_source, r"allRows\s*\.slice", r"source", r"qpbJoinedRows"), (
        "DAC-HRA-009: filtering/sorting must operate on a retained source collection"
    )
    assert _has(
        report_source,
        r"document\.getElementById\(.{0,80}visibleCount.{0,80}\)\.textContent\s*="
        r"[^;]{0,200}(?:visible\s+row\s+count|표시\s*중인\s*행\s*수)"
        r"[^;]{0,200}visibleRows\.length[^;]{0,100}allRows\.length",
    ), (
        "DAC-HRA-009: localized visible-row feedback must report the filtered visible-row "
        "count and retained source-row count"
    )
    assert _has(report_source, r"visibleRows\s*=\s*allRows\.filter", r"applyFilter.*renderJoined"), (
        "DAC-HRA-009: filtering must recompute visible rows and refresh their displayed count"
    )


# DAC-HRA-010 -------------------------------------------------------------------------------


def test_dac010_csv_action_preserves_explicit_scope_utf8_headers_and_escaping(report_source):
    required = (
        r"csvButton",
        r"csvChoice",
        r"filtered",
        r"all rows|allRows",
        r"UTF-8|utf-8|charset=utf-8",
        r"columns",
        r"replace\([^)]*['\"]{2}",
        r"Blob",
    )
    missing = [token for token in required if not _has(report_source, token)]
    assert not missing, f"DAC-HRA-010: CSV contract tokens missing: {missing!r}"
    assert _has(report_source, r"joined\.csv", r"qpbBuildJoinedCsv"), (
        "DAC-HRA-010: CSV must remain the existing joined-row export"
    )


# DAC-HRA-011 / Decision Log D-HRA-005 --------------------------------------------------------


def test_dac011_map_activation_uses_one_minimal_leaflet_popup_and_escaped_values(report_source):
    map_renderer = _function_body(report_source, "renderMap")
    popup_builder = _function_body(report_source, "qpbMapFeatureDetail")
    assert len(re.findall(r"\.bindPopup\s*\(", map_renderer)) == 1, (
        "DAC-HRA-011/D-HRA-005: each mapped feature must bind one Leaflet popup"
    )
    assert _has(report_source, r"bindPopup", r"leaflet-popup"), (
        "DAC-HRA-011/D-HRA-005: mapped features must use a Leaflet popup"
    )
    for label in ("조사일", "조사자", "국명", "학명"):
        assert label in report_source, (
            f"DAC-HRA-011/D-HRA-005: observation popup label {label!r} must remain available"
        )
    assert _has(report_source, r"site_name", r"조사지명", r"site.*name"), (
        "DAC-HRA-011/D-HRA-005: site/조사지 popup must use only its name"
    )
    assert _has(report_source, r"keydown", r"event\.key"), (
        "DAC-HRA-011/D-HRA-005: the existing keyboard activation path must open the popup"
    )
    assert _has(report_source, r"event\.key\s*===\s*['\"]Enter['\"]", r"\bEnter\b"), (
        "DAC-HRA-011/D-HRA-005: keyboard activation must support Enter"
    )
    assert _has(report_source, r"event\.key\s*===\s*['\"] ['\"]", r"Spacebar"), (
        "DAC-HRA-011/D-HRA-005: keyboard activation must support Space"
    )
    assert _has(report_source, r"openPopup\s*\(", r"\.openPopup"), (
        "DAC-HRA-011/D-HRA-005: keyboard activation must open the Leaflet popup"
    )
    assert _has(popup_builder, r"qpbEscapeHtml", r"function esc", r"\besc\s*\("), (
        "DAC-HRA-011/D-HRA-005: popup values must remain inert/escaped"
    )
    assert not _has(
        report_source,
        r"qpbShowMapDetail",
        r"qpbMapPopup",
        r"class\s*=\s*['\"]map-popup",
        r"\.map-popup\s*\{",
    ), "DAC-HRA-011/D-HRA-005: no duplicate right-side custom detail panel may remain"
    for technical in (
        r"고정\s*UUID",
        r"\bKTSN\b",
        r"연결된\s*(?:상위|조사)\s*(?:기록|문맥)",
    ):
        assert not _has(popup_builder, technical), (
            f"DAC-HRA-011/D-HRA-005: technical popup content must be excluded ({technical!r})"
        )
    css = "\n".join(_style_blocks(report_source))
    assert _has(css, r"\.leaflet-popup-pane", r"\.leaflet-popup-content-wrapper"), (
        "DAC-HRA-011/D-HRA-005: Leaflet popup presentation must remain styled"
    )
    assert not _has(map_renderer, r"bindTooltip", r"bindLabel", r"qpb-map-label"), (
        "DAC-HRA-011/D-HRA-005: feature activation must not leave a permanent map label"
    )


# DAC-HRA-012 -------------------------------------------------------------------------------


def test_dac012_korean_content_is_utf8_and_not_lost_by_the_visual_layer(report_source):
    assert _has(report_source, r"charset\s*=\s*['\"]?utf-8", r"charset=utf-8"), (
        "DAC-HRA-012: report document must declare UTF-8"
    )
    korean_tokens = (r"lang=['\"]ko", r"조사지", r"통합 표", r"국명", r"비고", r"저장 위치")
    missing = [token for token in korean_tokens if not _has(report_source, token)]
    assert not missing, f"DAC-HRA-012: Korean report content tokens missing: {missing!r}"
    deprecated_labels = (r"조사대상", r"한국명")
    present_deprecated = [token for token in deprecated_labels if _has(report_source, token)]
    assert not present_deprecated, (
        "DAC-HRA-012: report-visible Korean labels must use the agreed current terms 조사지 and 국명; "
        f"deprecated labels found: {present_deprecated!r}"
    )
    assert _has(report_source, r"qpbEscapeHtml", r"function esc"), (
        "DAC-HRA-012: Korean field values must use the existing escaped text path"
    )
    assert _has(report_source, r"text/csv;charset=utf-8", r"UTF-8", r"utf-8"), (
        "DAC-HRA-012: Korean content must remain represented in UTF-8 CSV output"
    )


# DAC-HRA-013 -------------------------------------------------------------------------------


def test_dac013_initialization_has_one_sequence_and_theme_changes_do_not_duplicate_views(
    report_source,
):
    assert _has(report_source, r"DOMContentLoaded", r"document\.ready", r"\(function\(\)"), (
        "DAC-HRA-013: browser initialization entry point must be explicit"
    )
    init_sequence = re.compile(
        r"function\s+qpbInitializeReport\s*\(\s*\)\s*\{[^}]{0,500}?"
        r"renderCards\(\)\s*;\s*renderSummaries\(\)\s*;\s*renderSpecies\(\)\s*;"
        r"(?:renderCharts\(\)\s*;\s*)?renderJoined\(\)\s*;\s*renderMap\(\)\s*;"
        r"\s*qpbSyncSummaryState\(\)\s*;\s*"
        r"document\.getElementById\([^)]*\)\.addEventListener",
        flags=re.IGNORECASE,
    )
    assert len(init_sequence.findall(report_source)) == 1, (
        "DAC-HRA-013: map/table/cards/summary accessibility/controls must have exactly one "
        "initialization sequence"
    )
    assert _has(report_source, r"theme", r"localStorage"), (
        "DAC-HRA-013: theme changes must be represented separately from initial rendering"
    )


# DAC-HRA-014 -------------------------------------------------------------------------------


def test_dac014_output_paths_remain_current_project_folder_only(report_source):
    assert _has(report_source, r"qgisProject\.homePath", r"current project folder"), (
        "DAC-HRA-014: report output must remain rooted in the current project folder"
    )
    assert _has(report_source, r"qpbReportOutputPath", r"\.html"), (
        "DAC-HRA-014: exact HTML output path must remain present"
    )
    assert _has(report_source, r"qpbJoinedCsvOutputPath", r"joined\.csv"), (
        "DAC-HRA-014: exact joined-CSV output path must remain present"
    )
    assert _has(report_source, r"output_paths", r"HTML:", r"Joined CSV:"), (
        "DAC-HRA-014: the report must show exact resulting paths"
    )


# DAC-HRA-015 -------------------------------------------------------------------------------


def test_dac015_keyboard_focus_labels_and_non_color_accessibility_hooks_are_present(report_source):
    css = "\n".join(_style_blocks(report_source))
    assert _has(css, r":focus-visible", r":focus\b"), (
        "DAC-HRA-015: every interactive control needs a visible focus treatment"
    )
    assert _has(css, r"outline\s*:", r"box-shadow\s*:"), (
        "DAC-HRA-015: focus treatment must be visually distinct, not color-only"
    )
    assert _has(report_source, r"aria-label", r"aria-live", r"aria-expanded", r"aria-pressed"), (
        "DAC-HRA-015: report controls/statuses need accessible names and state"
    )
    assert _has(report_source, r"<label", r"label", r"placeholder"), (
        "DAC-HRA-015: filter/control labels must remain discoverable"
    )
    assert _has(report_source, r"tabindex", r"button", r"select", r"input"), (
        "DAC-HRA-015: keyboard-reachable controls must remain represented"
    )


# Browser/manual evidence gates ----------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Browser/manual DAC-HRA-003/004/015 gate: open a generated report at exactly 375 CSS px "
        "and at a wide desktop width. Verify no page-level horizontal scroll; the table alone may "
        "scroll inside its labeled region. Verify header/cards/toolbar/map/details/notices remain "
        "readable and actionable, TOC changes from sticky to normal flow on narrow layout, every "
        "section anchor lands without being covered, and keyboard-only focus order reaches the theme "
        "toggle, TOC, filter, sortable headers, summaries, map detail, CSV controls, and detail "
        "actions. Check visible non-color-only focus and WCAG contrast: 4.5:1 normal text, 3:1 "
        "large text/controls, in both themes. Record browser/version and viewport dimensions."
    )
)
def test_dac003_dac004_dac015_browser_responsive_navigation_focus_and_contrast_gate():
    raise AssertionError("should never run while skipped — see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Browser/manual DAC-HRA-005/006/007 gate: exercise a seeded report with an active filter, "
        "sort order, expanded details, map state, and CSV scope. Toggle light/dark and confirm none "
        "of those states are lost; reload and confirm localStorage restores the theme. Open print "
        "preview and verify metadata, cards, local map/status, joined data, details, limitations, "
        "Korean text, and table columns are readable/unclipped while TOC/control-only chrome is not "
        "distracting. Emulate prefers-reduced-motion: reduce and confirm controls work without "
        "waiting for animation. Record browser/version and print engine."
    )
)
def test_dac005_dac006_dac007_browser_theme_print_and_reduced_motion_gate():
    raise AssertionError("should never run while skipped — see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Browser/manual DAC-HRA-008/009/010/011/012 gate: seed valid point/polygon features, "
        "invalid/missing geometry, one-to-many children, an orphan, nulls, Korean text, and "
        "adversarial HTML/CSV values including commas, quotes, newlines and <script> text. Verify "
        "all usable local features render, invalid records remain in table/details, offline map "
        "status is explicit, collapsing summaries does not remove map/table rows, filtering and "
        "every-column sorting remain deterministic, and filtered/all UTF-8 CSV exports contain the "
        "exact selected existing rows with correct quoting. Pointer-click and Enter/Space-activate "
        "point/polygon features and confirm exactly one transient adjacent Leaflet popup, no "
        "right-side custom detail panel, observation-only labels 조사일/조사자/국명/학명, site-only "
        "name content, preserved geometry, no permanent map labels, and inert escaped values; "
        "UUID/FK/KTSN and other technical fields must not appear in those popups."
    )
)
def test_dac008_dac009_dac010_dac011_dac012_browser_data_and_component_regression_gate():
    raise AssertionError("should never run while skipped — see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Browser/manual DAC-HRA-013/014 gate: open and reload the same report repeatedly, toggle "
        "theme between reloads, and verify exactly one map, one set of controls/handlers, one table "
        "row projection, and one summary/detail view. Verify the report names the current QField "
        "project folder and exact HTML/CSV paths, writes both there, and offers no outside-project "
        "picker, upload, synchronization, or alternate destination. Record QField/browser versions "
        "and the project-folder path used."
    )
)
def test_dac013_dac014_browser_reload_and_project_folder_boundary_gate():
    raise AssertionError("should never run while skipped — see skip reason")
