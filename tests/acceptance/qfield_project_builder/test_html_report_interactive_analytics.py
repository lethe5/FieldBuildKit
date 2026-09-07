"""Acceptance coverage for the interactive HTML field-survey report (AC-HRA-001..016).

The acceptance harness can build a real project and inspect its generated project-plugin QML,
but it cannot start QField's QML engine, a browser, or a platform file picker.  The automatic
checks in this module therefore assert the generated report's required data/interaction
constituents, resource boundaries, and escaping guards.  The tests marked ``manual``/``device``
are deliberately skipped placeholders for the end-to-end checks which require a real QField
session and browser.  They are part of the acceptance contract and must not be silently omitted.

The implementer may choose different private names, but the generated sidecar must expose the
same observable behavior.  These tests intentionally accept a small set of equivalent source
spellings (for example ``L.map`` or ``d3.geo``) rather than prescribing an implementation
library beyond the Leaflet/D3 requirement in the specification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

_SURVEY_TYPES = (
    "simple_inventory",
    "temporary_plots",
    "permanent_plots",
    "vegetation_mapping",
)


def _build(acceptance_api, tmp_path, survey_type: str, *, display_name: str = "HTML 분석 리포트"):
    config = make_base_config(survey_type, display_name=display_name)
    result = acceptance_api.build_project(config, str(tmp_path / f"report_{survey_type}"))
    assert result["success"], result.get("error_message")
    return result


def _sidecar(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    path = project_dir / f"{slug}.qml"
    assert path.is_file(), f"expected generated report sidecar: {path}"
    return path.read_text(encoding="utf-8")


def _contains_any(source: str, *patterns: str) -> bool:
    return any(re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _report_runtime(source: str) -> str:
    """Decode the generated inline report scripts from the QML sidecar."""
    scripts = []
    for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source):
        script = json.loads(match.group(1))
        if script.startswith("<script>"):
            scripts.append(script)
    assert scripts, "generated report sidecar must contain an embedded runtime"
    return "\n".join(scripts)


def _function_body(source: str, name: str) -> str:
    """Return one generated JavaScript function body for focused runtime assertions."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, f"generated report runtime must expose a {name} function"
    body, _ = _braced_block(source, match.end() - 1)
    return body


def _braced_block(source: str, opening_brace: int) -> tuple[str, int]:
    """Return the contents and closing position of a balanced source block."""
    assert source[opening_brace] == "{"
    depth = 0
    for position in range(opening_brace, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : position], position
    raise AssertionError("unterminated braced block in generated report source")


def _assert_report_core(source: str, criterion: str) -> None:
    assert _contains_any(source, r"Export HTML Report", r"exportHtmlReport"), criterion
    assert _contains_any(source, r"qpbBuildHtmlReport", r"buildHtmlReport"), criterion
    assert _contains_any(source, r"project_id", r"projectId"), criterion
    assert _contains_any(source, r"survey_type", r"surveyType"), criterion
    assert _contains_any(source, r"generated_at", r"generation"), criterion
    assert _contains_any(source, r"record.?count", r"records\.length"), criterion


# AC-HRA-001 ---------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", _SURVEY_TYPES)
def test_ac001_every_survey_type_has_on_demand_current_data_report_with_metadata(
    acceptance_api, tmp_path, survey_type
):
    source = _sidecar(_build(acceptance_api, tmp_path, survey_type))
    _assert_report_core(
        source,
        "AC-HRA-001: report action must include current-record collection and retained metadata",
    )
    assert _contains_any(source, r"LayerUtils\.createFeatureIterator", r"iterate.*feature"), (
        "AC-HRA-001: report must enumerate current saved features at export time"
    )
    assert not _contains_any(source, r"Timer\s*\{[^}]*report", r"setInterval\([^)]*report"), (
        "AC-HRA-001: report generation must remain on-demand, not periodic/background"
    )


# AC-HRA-002 ---------------------------------------------------------------------------------


def test_ac002_report_source_has_leaflet_or_d3_map_geometry_and_invalid_geometry_notice(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "permanent_plots"))
    assert _contains_any(source, r"L\.map\s*\(", r"leaflet", r"d3\.geo", r"d3\.select"), (
        "AC-HRA-002: generated report must contain a Leaflet/D3 map"
    )
    assert _contains_any(
        source,
        r"geometry",
        r"geom_wkt",
        r"geojson",
        r"coordinates",
    ), "AC-HRA-002: map must consume domain geometry/coordinates"
    assert _contains_any(
        source,
        r"transform",
        r"EPSG:4326",
        r"WGS84",
        r"project CRS",
    ), "AC-HRA-002: project CRS to map CRS transformation must be explicit"
    assert _contains_any(
        source,
        r"invalid geometry",
        r"missing geometry",
        r"geometry.*(?:omitted|excluded|unavailable)",
    ), "AC-HRA-002: unusable geometry must be disclosed, not silently dropped"


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-002 map fidelity requires a real browser/QField report session. Manual QA: "
        "generate Type 1, 2, 3, and 4 projects with point and polygon features in the declared "
        "project CRS; open each report and verify every valid feature is at the transformed WGS84 "
        "location, while missing/invalid geometry remains in the table and limitation notice. "
        "Record QField/browser version and platform."
    )
)
def test_ac002_map_renders_every_valid_point_and_polygon_on_device():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-003 / Decision Log D-HRA-005 ---------------------------------------------------------


def test_ac003_report_runtime_uses_one_leaflet_popup_for_pointer_and_keyboard_activation(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "permanent_plots"))
    runtime = _report_runtime(source)
    render_map = _function_body(runtime, "renderMap")

    assert len(re.findall(r"\.bindPopup\s*\(", render_map)) == 1, (
        "AC-HRA-003/D-HRA-005: each mapped feature must bind one Leaflet popup"
    )
    assert _contains_any(render_map, r"\.on\s*\(\s*['\"]click", r"bindPopup"), (
        "AC-HRA-003/D-HRA-005: mapped features must retain the Leaflet pointer-click path"
    )
    assert not _contains_any(render_map, r"permanent\s*[:=]\s*true"), (
        "AC-HRA-003/D-HRA-005: the feature popup must remain transient"
    )
    keyboard = _function_body(runtime, "qpbMakeFeatureKeyboardAccessible")
    assert _contains_any(keyboard, r"keydown", r"event\.key"), (
        "AC-HRA-003/D-HRA-005: mapped features must retain keyboard activation"
    )
    assert _contains_any(keyboard, r"event\.key\s*===\s*['\"]Enter['\"]", r"\bEnter\b"), (
        "AC-HRA-003/D-HRA-005: keyboard activation must support Enter"
    )
    assert _contains_any(
        keyboard, r"event\.key\s*===\s*['\"] ['\"]", r"Spacebar"
    ), "AC-HRA-003/D-HRA-005: keyboard activation must support Space"
    assert _contains_any(keyboard, r"openPopup\s*\(", r"\.openPopup"), (
        "AC-HRA-003/D-HRA-005: keyboard activation must open the Leaflet popup"
    )

    # The superseded right-side custom surface must not remain as a second activation path or
    # generated HTML host. The existing joined-table/detail data contracts remain covered
    # elsewhere in this module.
    forbidden_custom_surface = (
        r"qpbShowMapDetail",
        r"qpbMapPopup",
        r"class\s*=\s*['\"]map-popup",
        r"\.map-popup\s*\{",
    )
    assert not _contains_any(runtime, *forbidden_custom_surface), (
        "AC-HRA-003/D-HRA-005: feature activation must not render/open a duplicate custom detail panel"
    )

    render_map_lower = render_map.lower()
    assert "bindtooltip" not in render_map_lower and "bindlabel" not in render_map_lower, (
        "AC-HRA-003/D-HRA-005: feature activation must not leave a permanent map label"
    )
    assert "qpb-map-label" not in render_map_lower, (
        "AC-HRA-003/D-HRA-005: generated map must not create permanent feature labels"
    )

    assert _contains_any(
        source,
        r"\.leaflet-popup-pane",
        r"\.leaflet-popup-content-wrapper",
        r"\.leaflet-popup-content",
    ), "AC-HRA-003/D-HRA-005: standalone report must retain Leaflet popup presentation CSS"


def test_ac003_report_runtime_uses_minimal_observation_and_site_popup_allow_lists(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "permanent_plots"))
    runtime = _report_runtime(source)
    popup_builder = _function_body(runtime, "qpbMapFeatureDetail")
    popup_label_helpers = "\n".join(
        (
            popup_builder,
            _function_body(runtime, "qpbKoreanFieldLabel"),
            _function_body(runtime, "qpbVisibleLabel"),
        )
    )

    for label in ("조사일", "조사자", "국명", "학명"):
        assert label in popup_label_helpers, (
            f"AC-HRA-003/D-HRA-005: observation popup must support the labeled field {label!r}"
        )
    assert _contains_any(
        popup_builder,
        r"(?:anchor|table|feature)[A-Za-z_]*\s*={2,3}\s*['\"]site['\"]",
        r"['\"]site['\"]\s*={2,3}\s*(?:anchor|table|feature)",
        r"site_name",
        r"조사지명",
    ), (
        "AC-HRA-003/D-HRA-005: site/조사지 popup must select the site's name"
    )
    assert _contains_any(popup_builder, r"escapeHtml", r"qpbEscapeHtml", r"\besc\s*\("), (
        "AC-HRA-003/D-HRA-005: popup values must use the existing escaping path"
    )

    # A generic for-in-attrs projection would expose every observation field. The revised
    # contract requires an explicit minimal allow-list instead.
    assert not re.search(
        r"for\s*\([^)]*\bin\s+[^)]*(?:attrs|attributes)[^)]*\)",
        popup_builder,
        flags=re.IGNORECASE | re.DOTALL,
    ), "AC-HRA-003/D-HRA-005: popup must not enumerate all technical/raw fields"

    forbidden_popup_text = (
        r"고정\s*UUID",
        r"\bUUID\b",
        r"\bKTSN\b",
        r"연결된\s*(?:상위|조사)\s*(?:기록|문맥)",
        r"관찰\s*기록",
    )
    assert not _contains_any(popup_builder, *forbidden_popup_text), (
        "AC-HRA-003/D-HRA-005: popup content must exclude UUID, KTSN, FK, parent, and other "
        "technical/detail fields"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-003/D-HRA-005 requires a real report browser session. Manual QA: seed a Type 3 "
        "report with point/polygon observations and a site/조사지, then pointer-click and use "
        "Enter/Space keyboard activation. For each activation verify exactly one transient "
        "Leaflet popup is adjacent to the feature, no right-side custom detail panel appears, "
        "and no permanent map label remains. Observation popups must contain only 조사일, 조사자, "
        "국명, 학명; site/조사지 popups must contain only the site name. Include UUID/FK/KTSN, "
        "an extra observation field, and <script>alert(1)</script> values; verify technical fields "
        "are absent and all displayed values are readable inert text. Confirm the feature remains "
        "at its required geometry."
    )
)
def test_ac003_feature_activation_shows_one_minimal_escaped_leaflet_popup_in_browser():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-004/005 ------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", _SURVEY_TYPES)
def test_ac004_ac005_join_source_declares_uuid_fk_hierarchies_and_absent_levels(
    acceptance_api, tmp_path, survey_type
):
    source = _sidecar(_build(acceptance_api, tmp_path, survey_type))
    assert _contains_any(source, r"joined", r"join", r"relationship"), (
        "AC-HRA-004/005: report must provide a joined table"
    )
    assert _contains_any(source, r"site_id", r"plot_id", r"survey_id", r"inventory_id"), (
        "AC-HRA-004/005: joins must use stable UUID/FK columns"
    )
    assert _contains_any(source, r"조사대상", r"조사지", r"site"), (
        "AC-HRA-004/005: joined report must include site level when schema defines it"
    )
    assert _contains_any(source, r"조사", r"survey"), (
        "AC-HRA-004/005: joined report must include survey level when schema defines it"
    )
    assert _contains_any(source, r"empty", r"없음", r"null", r"absent", r"not applicable"), (
        "AC-HRA-005: schema-absent levels must be represented as empty, not fabricated"
    )
    assert _contains_any(source, r"missing parent", r"orphan", r"부모 없음", r"integrity"), (
        "AC-HRA-004: orphan child must remain visible with an integrity marker"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-004/005 joined-row correctness requires saved records in QField and a browser. "
        "Manual QA: seed Type 3 site→plot→survey→observation records including a parent with "
        "multiple observations and one orphan FK; verify one row per child, parent context, orphan "
        "marker/count, and Type 1/2/4 absent levels are empty with no fabricated rows."
    )
)
def test_ac004_ac005_joined_rows_preserve_relationships_for_all_survey_types_on_device():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-006 ---------------------------------------------------------------------------------


def test_ac006_joined_table_source_has_filter_sort_null_date_numeric_and_stable_data_paths(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "permanent_plots"))
    assert _contains_any(source, r"filter", r"includes\(", r"indexOf"), (
        "AC-HRA-006: joined table must support client-side filtering"
    )
    assert _contains_any(source, r"sort", r"localeCompare", r"numeric", r"Date\.parse"), (
        "AC-HRA-006: joined table must support deterministic typed sorting"
    )
    assert _contains_any(source, r"null", r"undefined", r"empty", r"stable"), (
        "AC-HRA-006: null/empty values require deterministic handling"
    )
    assert _contains_any(source, r"visible.*count", r"filtered.*count", r"rowCount", r"length"), (
        "AC-HRA-006: filtering must update visible row count"
    )
    assert _contains_any(source, r"original", r"allRows", r"joinedRows", r"source"), (
        "AC-HRA-006: filtering/sorting must preserve an unfiltered source collection"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-006 interaction requires a browser. Manual QA: use Korean/English duplicate names, "
        "nulls, ISO date/datetime, numeric and note values; filter each required visible field, "
        "sort every column twice, verify stable null ordering and visible count, and confirm the "
        "GeoPackage/unfiltered row set is unchanged."
    )
)
def test_ac006_filter_and_sort_joined_table_without_mutating_source_in_browser():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-007/012 ------------------------------------------------------------------------------


def test_ac007_ac012_report_source_has_utf8_csv_action_visible_choice_and_safe_escaping(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "simple_inventory"))
    assert _contains_any(source, r"CSV", r"csv", r"save.*joined"), (
        "AC-HRA-007: report must expose a joined CSV save action"
    )
    assert _contains_any(source, r"UTF-8", r"utf-8", r"charset=utf-8", r"text/csv"), (
        "AC-HRA-007: CSV must be UTF-8"
    )
    assert _contains_any(source, r"quote", r"escape", r"replace\([^)]*\\\"", r"RFC"), (
        "AC-HRA-007/012: CSV fields must be quoted/escaped"
    )
    assert _contains_any(source, r"filtered", r"all rows", r"allRows", r"visible rows"), (
        "AC-HRA-007: filtered/all-row export choice must be visible"
    )
    assert _contains_any(source, r"escapeHtml", r"textContent", r"createTextNode"), (
        "AC-HRA-012: HTML values must be inert"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-007/012 export behavior requires a browser and save picker. Manual QA: enter or "
        "collect Korean text, commas, quotes, newlines and <script>alert(1)</script>; filter rows; "
        "choose filtered versus all rows (verify the default is stated); save CSV; parse it as UTF-8 "
        "RFC-compatible CSV and verify exact values/row selection and no script execution."
    )
)
def test_ac007_ac012_csv_matches_selected_rows_and_escapes_adversarial_values():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-008 ---------------------------------------------------------------------------------


def test_ac008_report_source_has_collapsible_schema_level_summaries_with_semantic_korean_labels_and_counts(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "permanent_plots"))
    assert _contains_any(source, r"<details", r"<summary", r"collaps", r"aria-expanded"), (
        "AC-HRA-008: summaries must be collapsible"
    )
    summary_renderer = re.search(
        r"function\s+renderSummaries\s*\([^)]*\)\s*\{.*?document\.getElementById\(\s*\\?[\"']summaries\\?[\"']\s*\)",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert summary_renderer, "AC-HRA-008: report must render schema-level summaries"
    renderer_source = summary_renderer.group(0).replace(r'\"', '"').replace(r"\'", "'")
    for schema_level, korean_label in (("site", "조사지"), ("survey", "조사"), ("plot", "조사구")):
        assert re.search(
            rf'\{{\s*n\s*:\s*["\']{schema_level}["\']\s*,\s*l\s*:\s*["\']{korean_label}["\']\s*\}}',
            renderer_source,
            flags=re.IGNORECASE,
        ), f"AC-HRA-008: {schema_level} summary must use the Korean label {korean_label!r}"
    assert "조사대상" not in renderer_source, (
        "AC-HRA-008: the deprecated ambiguous label 조사대상 must not name a schema-level summary"
    )
    assert re.search(
        r"if\s*\(\s*!t\s*\)\s*continue\s*;\s*out\s*\+=\s*[\"']<details>",
        renderer_source,
        flags=re.IGNORECASE,
    ), "AC-HRA-008: summary sections must be emitted only for schema-defined levels"
    assert re.search(
        r"names\[i\]\.l\s*\+\s*[\"']\s*기록\s*수\s*:\s*[\"']\s*\+\s*t\.records\.length",
        renderer_source,
        flags=re.IGNORECASE,
    ), (
        "AC-HRA-008: every schema-level summary must display that level's record count"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-008 requires browser interaction. Manual QA: in a Type 3 report, expand/collapse 조사지, 조사, and "
        "조사구 independently; verify counts and concise record summaries, then confirm the map and "
        "joined table retain all rows in every state."
    )
)
def test_ac008_collapsing_summaries_does_not_remove_map_or_joined_rows():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-009/010 ------------------------------------------------------------------------------


def test_ac009_ac010_report_source_has_species_precedence_counts_and_date_cards(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "simple_inventory"))
    assert _contains_any(source, r"selected_korean_name", r"Korean.*name", r"한국명"), (
        "AC-HRA-009: species key must consider selected Korean name"
    )
    assert _contains_any(source, r"selected_scientific_name", r"scientific.*name", r"학명"), (
        "AC-HRA-009: species key must consider selected scientific name"
    )
    assert _contains_any(source, r"selected_ktsn", r"KTSN"), (
        "AC-HRA-009: species display must include KTSN when present"
    )
    assert _contains_any(source, r"미동정", r"unidentified", r"unknown species"), (
        "AC-HRA-009: missing names must use an explicit unidentified bucket"
    )
    assert _contains_any(source, r"species", r"종별", r"occurrence"), (
        "AC-HRA-009: report must show species occurrence counts"
    )
    assert _contains_any(source, r"dominant_species", r"community", r"군락"), (
        "AC-HRA-009: Type 4 community species must remain a separate concept"
    )
    assert _contains_any(source, r"observation.?day", r"날짜", r"survey_date", r"date"), (
        "AC-HRA-010: report must compute observation-day summary"
    )
    assert _contains_any(source, r"날짜 없음", r"unknown date", r"invalid date", r"missing date"), (
        "AC-HRA-010: invalid/missing dates must be disclosed"
    )


def test_ac009_ac010_report_source_excludes_ktsn_only_from_species_aggregation(
    acceptance_api, tmp_path
):
    """D-HRA-002/D-HRA-004: a KTSN-only observation is not a species or 미동정.

    This is intentionally a source-level acceptance check.  The report may choose different
    helper names, but its analytics loop must have an explicit branch for the state where both
    display-name fields are empty and KTSN is populated.  That branch may be a no-op exclusion
    paired with an ``else`` that owns species mutation, so long as species aggregation cannot
    happen for KTSN-only rows and date aggregation continues afterward.  Under D-HRA-004, the
    separate direct-layer overview-card measure may count that KTSN; it must not change this
    species-key path.  The all-fields-empty fallback remains required for genuine unidentified
    observations.
    """
    source = _sidecar(_build(acceptance_api, tmp_path, "simple_inventory"))
    analytics_start = source.find("function qpbBuildAnalytics")
    analytics_end = source.find("function qpbGeometryLimitations", analytics_start)
    assert analytics_start >= 0 and analytics_end > analytics_start, (
        "AC-HRA-009/010: species analytics implementation must be inspectable"
    )
    analytics = source[analytics_start:analytics_end]

    # The guard must distinguish KTSN-only from a genuinely unidentified row and must leave the
    # record available to the report's joined/raw data path.  A no-op exclusion branch is
    # semantically valid when all species-group mutation is isolated in its eligible ``else``
    # branch; date aggregation must remain after that decision.
    ktsn_only_guard = re.search(
        r"if\s*\(\s*!\s*korean\s*&&\s*!\s*scientific\s*&&\s*ktsn\s*\)\s*\{",
        analytics,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert ktsn_only_guard, (
        "AC-HRA-009/010 (D-HRA-002): names-empty/KTSN-only observations must have an explicit "
        "no-species-key exclusion branch"
    )
    excluded_branch, excluded_end = _braced_block(analytics, ktsn_only_guard.end() - 1)
    eligible_match = re.match(r"\s*else\s*\{", analytics[excluded_end + 1 :])
    assert eligible_match, (
        "AC-HRA-009/010 (D-HRA-002): an explicit KTSN-only exclusion must isolate species "
        "aggregation in an eligible else branch"
    )
    eligible_opening = excluded_end + 1 + eligible_match.end() - 1
    eligible_branch, eligible_end = _braced_block(analytics, eligible_opening)
    species_mutation = r"(?:group\.count\s*\+=|species\s*\[[^\]]+\]\s*=)"
    assert not re.search(species_mutation, excluded_branch, flags=re.IGNORECASE), (
        "AC-HRA-009/010 (D-HRA-002): KTSN-only exclusion branch must not mutate a species group"
    )
    assert re.search(species_mutation, eligible_branch, flags=re.IGNORECASE), (
        "AC-HRA-009/010 (D-HRA-002): species-group mutation must be confined to the eligible "
        "branch, not the KTSN-only exclusion"
    )
    assert _contains_any(analytics[eligible_end + 1 :], r"dateValue", r"calendarDate", r"dates"), (
        "AC-HRA-010 (D-HRA-002): date aggregation must continue after KTSN-only species exclusion"
    )
    assert not re.search(
        r"\bkey\s*:\s*korean\s*\|\|\s*scientific\s*\|\|\s*ktsn",
        eligible_branch,
        flags=re.IGNORECASE,
    ), (
        "AC-HRA-009/010 (D-HRA-002): selected_ktsn must not become a species identity-key "
        "fallback; only Korean/scientific names may form the key"
    )
    assert _contains_any(analytics, r"all three", r"미동정", r"unidentified", r"unknown species"), (
        "AC-HRA-009: all-three-fields-empty observations must retain the explicit unidentified "
        "fallback"
    )
    assert _contains_any(source, r"qpbJoinedRows", r"joined", r"qpbCollectCurrentRecords"), (
        "AC-HRA-009 (D-HRA-002): KTSN-only observations must remain available in report data "
        "outside species aggregation"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-009/010 data-count correctness requires a browser report with seeded observations. "
        "Manual QA: include Korean-only (name only), scientific-only (scientific name only), "
        "KTSN-only (both names empty, selected_ktsn populated), all-fields-empty unidentified, "
        "and repeated rows. Verify Korean-only and scientific-only each form their expected species "
        "keys, while every KTSN-only row remains in joined/raw/detail/map data and contributes no "
        "species occurrence/chart group or 미동정 row. For Types 1–3, verify 총 종수 is the "
        "direct-layer distinct valid selected_ktsn count: it includes each KTSN-only value once "
        "without join fan-out, independently of the species chart. Verify only the all-fields-empty "
        "row enters 미동정; Type 4 has no 총 종수/species card and dominant_species remains a "
        "separate community summary; also verify distinct site/plot/day cards and missing-date "
        "disclosure."
    )
)
def test_ac009_ac010_species_and_summary_cards_are_correct_on_real_report_data():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-011 / Decision Log D-HRA-003 ---------------------------------------------------------


_REPORT_VWORLD_KEY = "ACCEPTANCE-TEST-REPORT-VWORLD-KEY-0000"


def _report_online_config(*, key: str | None, consent_accepted: bool) -> dict:
    """Build config for report-background selection checks.

    This deliberately uses a fake key: the structural checks must not call the remote service or
    claim that a non-existent key produces imagery.  The real-device gate below is the only place
    that verifies the live VWorld/OSM tile outcome.
    """
    config = make_base_config("temporary_plots")
    config["basemap"] = {
        "mode": "online",
        "layer": "Base",
        "consent_accepted": consent_accepted,
        "remember_key": False,
    }
    if key is not None:
        config["basemap"]["vworld_api_key"] = key
    return config


def _assert_ac011_background_contract(source: str) -> None:
    """Check observable generated-source constituents without prescribing private function names."""
    assert _contains_any(source, r"VWorld", r"vworld", r"VWORLD"), (
        "AC-HRA-011/D-HRA-003: report must support VWorld background selection"
    )
    assert _contains_any(source, r"OpenStreetMap", r"openstreetmap", r"osm"), (
        "AC-HRA-011/D-HRA-003: report must contain the automatic OpenStreetMap fallback"
    )
    assert _contains_any(source, r"tileLayer", r"tile layer", r"tile-layer"), (
        "AC-HRA-011/D-HRA-003: VWorld and OpenStreetMap must be map background layers"
    )
    assert _contains_any(source, r"tile\.openstreetmap\.org", r"openstreetmap\.org"), (
        "AC-HRA-011/D-HRA-003: expected a concrete OpenStreetMap tile endpoint"
    )
    assert _contains_any(source, r"offline", r"unavailable", r"network"), (
        "AC-HRA-011/D-HRA-003: unavailable remote backgrounds must be explicit"
    )
    assert _contains_any(source, r"fallback", r"other background", r"alternate"), (
        "AC-HRA-011/D-HRA-003: selected-service failure must disclose/attempt fallback"
    )
    assert _contains_any(source, r"attribution", r"국토교통부"), (
        "AC-HRA-011/D-HRA-003: active background attribution must be visible"
    )
    assert _contains_any(source, r"OpenStreetMap contributors", r"OpenStreetMap"), (
        "AC-HRA-011/D-HRA-003: OpenStreetMap attribution must be represented"
    )
    assert _contains_any(source, r"vworld_key", r"vworld.*key", r"VWorld.*key"), (
        "AC-HRA-011/D-HRA-003: saved VWorld-key state must drive selection"
    )
    assert _contains_any(source, r"qpbRuntimeVworldKey", r"saved.*VWorld.*key"), (
        "AC-HRA-011/D-HRA-003: report must read the current project's saved key"
    )
    assert _contains_any(source, r"tileerror", r"onerror", r"load.*error"), (
        "AC-HRA-011/D-HRA-003: tile-service failure must be handled without aborting the report"
    )


def test_ac011_report_source_selects_vworld_key_first_and_osm_without_key(
    acceptance_api, tmp_path
):
    keyed = acceptance_api.build_project(
        _report_online_config(key=_REPORT_VWORLD_KEY, consent_accepted=True),
        str(tmp_path / "report_with_vworld_key"),
    )
    assert keyed["success"], keyed.get("error_message")
    keyed_source = _sidecar(keyed)
    _assert_ac011_background_contract(keyed_source)

    no_key = acceptance_api.build_project(
        _report_online_config(key=None, consent_accepted=False),
        str(tmp_path / "report_without_vworld_key"),
    )
    assert no_key["success"], no_key.get("error_message")
    no_key_source = _sidecar(no_key)
    _assert_ac011_background_contract(no_key_source)

    # The saved key is a runtime capability input, not report/UI data.  Its literal must not be
    # copied into the generated project-plugin source even when online-basemap consent exists.
    assert _REPORT_VWORLD_KEY not in keyed_source


@pytest.mark.network
@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-011/D-HRA-003 requires a real QField 4.2.4 project-plugin report session. "
        "(1) Open a current project with a usable saved VWorld API key and network access; verify "
        "VWorld imagery appears beneath local features, the active-background status identifies "
        "VWorld, and the VWorld/국토교통부 attribution is visible. (2) Open an equivalent project "
        "with no usable saved VWorld key and network access; verify OpenStreetMap is selected "
        "automatically and its attribution is visible. (3) Make the selected service unavailable "
        "and verify the alternate background is attempted and the resulting status is disclosed. "
        "(4) Disable network or make both services unavailable; verify the report still opens and "
        "local map controls, feature layers, table, summary, filtering, sorting, detail, and CSV "
        "remain usable with an explicit offline-background state. Inspect the report/UI and confirm "
        "the VWorld API key is not displayed in the UI (Option 1 permits it in exported "
        "tile-request data). "
        "Do not treat tile failure as report failure."
    )
)
def test_ac011_vworld_key_first_osm_fallback_and_offline_report_are_nonfatal_on_device():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-013 ---------------------------------------------------------------------------------


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-013 requires a real QField 4.2.4 project-plugin export on each target platform. "
        "With a writable current project folder, confirm the UI names that project-folder "
        "destination and reports the exact HTML and joined-CSV paths, then verify both files are "
        "written at those paths. Make the current project folder unavailable or non-writable and "
        "verify an actionable write error, no false-success message, no silent alternate-destination "
        "fallback, and continued access to the in-memory report. No external path picker is part of "
        "this contract."
    )
)
def test_ac013_project_folder_html_and_csv_paths_and_write_failures_are_reported():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-014 ---------------------------------------------------------------------------------


def test_ac014_empty_project_report_source_has_zero_and_header_only_empty_states(
    acceptance_api, tmp_path
):
    result = _build(acceptance_api, tmp_path, "simple_inventory")
    source = _sidecar(result)
    assert _contains_any(source, r"No records", r"empty", r"records\.length\s*===?\s*0"), (
        "AC-HRA-014: report must render valid empty states"
    )
    assert _contains_any(source, r"0", r"zero"), "AC-HRA-014: empty summary cards must be zero"
    assert _contains_any(source, r"header", r"CSV", r"csv"), (
        "AC-HRA-014: empty joined CSV must still have a header"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-014 requires opening the exported file. Manual QA: export a genuinely empty Type 1, "
        "2, 3 and 4 project; verify valid empty map/table/summary, zero cards, no fabricated unknown "
        "feature, and a parseable header-only joined CSV."
    )
)
def test_ac014_empty_project_is_valid_in_browser_and_csv_parser():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-015 ---------------------------------------------------------------------------------


_EXTERNAL_RESOURCE_RE = re.compile(
    r"(?:<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*"
    r"\b(?:src|href|data)\s*=\s*['\"]https?://|url\(\s*['\"]?https?://|"
    r"@import\s+(?:url\(\s*)?['\"]?https?://)",
    flags=re.IGNORECASE,
)


def test_ac015_report_sidecar_embeds_local_runtime_without_external_resources(
    acceptance_api, tmp_path
):
    source = _sidecar(_build(acceptance_api, tmp_path, "simple_inventory"))
    assert re.search(r"<!doctype html|<html", source, flags=re.IGNORECASE), (
        "AC-HRA-015: report must construct a standalone HTML document"
    )
    external = _EXTERNAL_RESOURCE_RE.search(source)
    assert external is None, f"AC-HRA-015: external report resource found: {external.group(0)!r}"
    assert _contains_any(source, r"<style", r"stylesheet", r"CSS"), (
        "AC-HRA-015: report styling must be embedded/packaged locally"
    )
    assert _contains_any(source, r"<script", r"function", r"addEventListener"), (
        "AC-HRA-015: local report interaction code must be embedded/packaged"
    )


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-015 offline-copy behavior requires a browser/device. Manual QA: copy the report to "
        "a separate folder, open with network disabled, and exercise local table, summary, filter, "
        "sort, detail and CSV; capture a network log proving no remote script/style/font/image was "
        "needed. VWorld may be absent with an explicit notice."
    )
)
def test_ac015_copied_report_works_without_network_in_browser():
    raise AssertionError("should never run while skipped — see skip reason")


# AC-HRA-016 ---------------------------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-HRA-016 is a QField 4.2.4 capability and project-folder-only audit. On each target "
        "platform, record the exact QField version/platform, verify that project plugins expose no "
        "supported external save-location picker/API, and verify the report explicitly states the "
        "project-folder-only HTML/CSV boundary. Separately record full-layer-enumeration and VWorld "
        "availability/limitations. The report must not claim complete data/map coverage or "
        "outside-folder export support when those capabilities are unavailable."
    )
)
def test_ac016_qfield_424_capability_and_project_folder_boundary_are_reported_honestly():
    raise AssertionError("should never run while skipped — see skip reason")
