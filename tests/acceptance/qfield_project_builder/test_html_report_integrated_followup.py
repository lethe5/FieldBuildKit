"""Acceptance coverage for specs/html-report-integrated-followup.md (AC-IRF-001..017).

This module is deliberately feature-local.  It uses the repository's isolated acceptance
``build_project`` seam and inspects the generated report sidecar; it never opens a user's QGIS
profile, edits a GeoPackage, or calls a tile service.  The static checks are executable contract
checks, not implementation snapshots: equivalent function names are accepted where the observable
contract is unambiguous.  Browser/QField stateful behavior remains an explicit skipped gate below.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

_TYPES = ("simple_inventory", "temporary_plots", "permanent_plots", "vegetation_mapping")
_FAKE_KEY = "IRF-ACCEPTANCE-KEY-DO-NOT-LEAK"


def _build(acceptance_api, tmp_path: Path, survey_type: str, *, key: str | None = None) -> tuple[dict, str]:
    config = make_base_config(survey_type, display_name="통합 HTML 리포트 수락 테스트")
    if key is not None:
        config["basemap"] = {
            "mode": "online",
            "layer": "Base",
            "consent_accepted": True,
            "remember_key": False,
            "vworld_api_key": key,
        }
    result = acceptance_api.build_project(config, str(tmp_path / survey_type))
    assert result["success"], result.get("error_message")
    path = Path(result["project_dir"]) / f"{result['project_slug']}.qml"
    assert path.is_file(), f"missing generated report sidecar: {path}"
    return result, path.read_text(encoding="utf-8")


def _has(source: str, *patterns: str) -> bool:
    return any(re.search(pattern, source, re.I | re.S) for pattern in patterns)


def _require(source: str, criterion: str, *patterns: str) -> None:
    assert _has(source, *patterns), f"{criterion}: missing required report contract {patterns!r}"


def _function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, f"missing generated report function {name!r}"
    tail = source[match.end() :]
    next_function = re.search(r"\bfunction\s+[A-Za-z_$][\w$]*\s*\(", tail)
    return tail[: next_function.start()] if next_function else tail


def test_ac001_saved_vworld_key_is_runtime_selected_and_osm_is_keyless_default(acceptance_api, tmp_path):
    _, keyed = _build(acceptance_api, tmp_path / "keyed", "simple_inventory", key=_FAKE_KEY)
    _, keyless = _build(acceptance_api, tmp_path / "keyless", "simple_inventory")
    for source in (keyed, keyless):
        _require(source, "AC-IRF-001", r"vworld", r"openstreetmap")
        _require(source, "AC-IRF-001", r"saved|runtime|customProperty|customVariables")
        _require(source, "AC-IRF-001", r"attribution|국토교통부|contributors")
    assert _FAKE_KEY not in keyed, "AC-IRF-001: configured key must not be emitted as report text"
    assert _has(keyless, r"!.*(?:vworldKey|savedKey|runtimeKey|vworld_key).*openstreetmap", r"no.*key.*openstreetmap"), (
        "AC-IRF-001: keyless reports must choose OSM without a placeholder VWorld request"
    )


def test_ac002_background_failure_is_nonfatal_and_preserves_all_local_capabilities(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "permanent_plots")
    for token in ("tileerror", "fallback", "offline", "유효한 도형", "OpenStreetMap"):
        assert token.lower() in source.lower(), f"AC-IRF-002: missing failure/fallback token {token!r}"
    for capability in ("renderMap", "renderJoined", "renderCards", "renderSpecies", "saveCsv", "qpbToggleTheme"):
        assert capability in source, f"AC-IRF-002: local capability {capability!r} must survive tile failure"
    assert _has(source, r"FallbackAttempted|fallbackAttempted|attempt.*once|once.*alternate"), (
        "AC-IRF-002: alternate background must be attempted at most once"
    )


@pytest.mark.parametrize("survey_type", _TYPES)
def test_ac003_current_gpkg_spatial_metadata_collects_every_table_and_attributes(acceptance_api, tmp_path, survey_type):
    _, source = _build(acceptance_api, tmp_path, survey_type)
    _require(source, "AC-IRF-003", r"gpkg_contents", r"gpkg_geometry_columns")
    _require(source, "AC-IRF-003", r"geometry.?column|geometry_field|geometry_field")
    _require(source, "AC-IRF-003", r"source.?table|table.?identity|source_identity")
    _require(source, "AC-IRF-003", r"source.?crs|geometry.?crs|srs_id")
    _require(source, "AC-IRF-003", r"raw.?record|source.?record|record.?identity")
    _require(source, "AC-IRF-003", r"non.?spatial|not spatial|geometry.*none")
    _require(source, "AC-IRF-003", r"read.?only|current.*saved|export.*time")


@pytest.mark.parametrize("survey_type,anchor", [
    ("simple_inventory", "inventory_observation"),
    ("temporary_plots", "survey"),
    ("permanent_plots", "plot"),
    ("vegetation_mapping", "community"),
])
def test_ac004_type_specific_anchor_rules_and_fk_join_boundaries(acceptance_api, tmp_path, survey_type, anchor):
    _, source = _build(acceptance_api, tmp_path, survey_type)
    _require(source, "AC-IRF-004", anchor, r"anchor.?table|anchor_uuid|map_features")
    _require(source, "AC-IRF-004", r"foreign.?key|foreign_key|site_id|plot_id|survey_id")
    _require(source, "AC-IRF-004", r"one.?to.?many|related_observations|child")
    _require(source, "AC-IRF-004", r"observation.*(?:never|not).*(?:anchor|replace)|anchor.*observation")
    if survey_type == "permanent_plots":
        _require(source, "AC-IRF-004", r"plot.*(?:fallback|geometry unavailable)|survey.*fallback")


def test_ac005_geometry_validity_crs_serialization_and_truthful_global_empty_state(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "permanent_plots")
    _require(source, "AC-IRF-005", r"valid.*geometry|geometry.*valid|unusable")
    _require(source, "AC-IRF-005", r"EPSG:4326|WGS84|transform")
    _require(source, "AC-IRF-005", r"reason|limitations|geometry_limitations")
    _require(source, "AC-IRF-005", r"유효한 도형 없음")
    assert _has(source, r"if\s*\([^)]*(?:valid|rendered).*[\s\S]{0,800}유효한 도형 없음"), (
        "AC-IRF-005: the empty-map notice must be conditional on zero valid eligible features"
    )


def test_ac006_one_to_many_anchor_is_single_feature_but_all_children_and_orphan_rows_survive(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "temporary_plots")
    _require(source, "AC-IRF-006", r"map_features.*(?:anchor|unique)|anchor.*once|dedup")
    _require(source, "AC-IRF-006", r"related_observations|child.*collection|one.?to.?many")
    _require(source, "AC-IRF-006", r"orphan|integrity|상위 기록 누락|고아")
    _require(source, "AC-IRF-006", r"joined.*rows|allRows|CSV")
    _require(source, "AC-IRF-006", r"stable.*order|deterministic|localeCompare")


def test_ac007_columns_are_collision_free_normalized_and_byte_stable_for_csv(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "permanent_plots")
    _require(source, "AC-IRF-007", r"duplicate|collision|overwrite|integrity")
    _require(source, "AC-IRF-007", r"source_table__source_field|normalize|normalized|slug")
    _require(source, "AC-IRF-007", r"_2|_3|suffix|source.?schema.?order")
    _require(source, "AC-IRF-007", r"unique.*header|headers.*unique|Set\(")
    _require(source, "AC-IRF-007", r"stable.*header|header.*stable|schema.*order")
    _require(source, "AC-IRF-007", r"byte.?identical|repeat.*export|unchanged")


def test_ac008_visible_labels_are_concise_korean_and_identity_csv_contract_is_preserved(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "simple_inventory")
    for identity in ("국명", "학명", "KTSN"):
        assert identity in source, f"AC-IRF-008: missing required visible identity label {identity!r}"
    _require(source, "AC-IRF-008", r"CSV.*header|columns.*key|machine.?readable")
    _require(source, "AC-IRF-008", r"display.*label|korean|한국어|alias")
    _require(source, "AC-IRF-008", r"one.*header|header.*column|duplicate.*header")
    joined_body = _function_body(source, "renderJoined")
    assert not _has(joined_body, r"<small>[\s\S]{0,80}(?:\.key|internal.?header|source_field)"), (
        "AC-IRF-008: raw machine-readable headers must not be shown in the normal table"
    )


@pytest.mark.parametrize("survey_type", _TYPES)
def test_ac009_overview_cards_are_explicit_korean_distinct_source_level_counts(acceptance_api, tmp_path, survey_type):
    _, source = _build(acceptance_api, tmp_path, survey_type)
    overview_body = _function_body(source, "renderCards") + _function_body(source, "renderSummaries")
    for label in ("조사지", "조사구", "조사", "관찰"):
        assert label in overview_body, f"AC-IRF-009: missing overview level {label!r}"
    assert "조사대상" not in overview_body, "AC-IRF-009: ambiguous site label 조사대상 must not be used in overview"
    _require(source, "AC-IRF-009", r"distinct|Set\(|stable.?id|uuid")
    _require(source, "AC-IRF-009", r"해당 레벨 부재|not applicable|absent")
    _require(source, "AC-IRF-009", r"source.*table|aggregation.*basis|통합 행 수")
    _require(source, "AC-IRF-009", r"siteCount|plotCount|surveyCount|observationCount")


def test_ac010_d3_charts_use_defined_source_aggregations_and_truthful_numeric_empty_states(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "vegetation_mapping")
    _require(source, "AC-IRF-010", r"d3(?:\.js)?|d3\.select|d3\.scale")
    for title in ("종별 출현", "평균 피도", "군락별 면적"):
        assert title in source, f"AC-IRF-010: missing Korean chart title {title!r}"
    _require(source, "AC-IRF-010", r"occurrence|출현.*횟수|species.*count")
    _require(source, "AC-IRF-010", r"average|평균|cover|피도")
    _require(source, "AC-IRF-010", r"community.*area|군락.*면적|area")
    _require(source, "AC-IRF-010", r"Number\(|isNaN|numeric|invalid.*excluded|제외")
    _require(source, "AC-IRF-010", r"empty|기록 없음|not applicable|해당 없음")
    assert _has(source, r"d3\.pie|pie\s*\(", r"d3\.arc|arc\s*\(", r"pie chart"), (
        "AC-IRF-010: at least one interactive pie chart path is required"
    )
    _require(source, "AC-IRF-010", r"bar|rect|scaleBand")


def test_ac011_theme_toggle_is_accessible_and_state_preserving(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "permanent_plots")
    _require(source, "AC-IRF-011", r"themeToggle|theme-toggle")
    _require(source, "AC-IRF-011", r"aria-pressed|aria-label|keyboard|keydown")
    _require(source, "AC-IRF-011", r"localStorage|themeStorage|prefers-color-scheme")
    _require(source, "AC-IRF-011", r"filter|sort|expanded|selected|chart")
    _require(source, "AC-IRF-011", r"CSV|saveCsv|columns")
    _require(source, "AC-IRF-011", r"light|dark|어두운|밝은")


def test_ac012_escaping_utf8_csv_and_secret_attachment_boundaries_are_explicit(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "simple_inventory")
    _require(source, "AC-IRF-012", r"escapeHtml|textContent|createTextNode")
    _require(source, "AC-IRF-012", r"replace\([^)]*\\\"|csvCell|quote|RFC")
    _require(source, "AC-IRF-012", r"UTF-8|utf-8|charset=utf-8|\\ufeff")
    _require(source, "AC-IRF-012", r"credential|secret|attachment|photo|path.*omit|omitted")
    _require(source, "AC-IRF-012", r"diagnostic|log|normal.*report|user.?visible")
    assert _FAKE_KEY not in source, "AC-IRF-012: credentials must not appear in report surfaces"


def test_ac013_export_consent_is_explicit_key_scoped_and_fail_closed(acceptance_api, tmp_path):
    """Consent must govern the export artifact, not merely the initial map selection."""
    _, source = _build(acceptance_api, tmp_path, "simple_inventory", key=_FAKE_KEY)
    _require(source, "AC-IRF-013", r"미포함", r"포함")
    _require(source, "AC-IRF-013", r"(?:팝업|dialog|confirm|messageDialog)")
    _require(source, "AC-IRF-013", r"(?:HTML|파일).*(?:노출|공개|expos|inspect)|expos.*HTML")
    _require(source, "AC-IRF-013", r"default.*(?:미포함|omit)|(?:미포함|omit).*default")
    _require(source, "AC-IRF-013", r"cancel|취소|close|닫")
    _require(source, "AC-IRF-013", r"(?:not|false|미포함).*(?:write|저장|export)|export.*(?:not|false|미포함)")
    _require(source, "AC-IRF-013", r"(?:affirm|explicit|명시|동의|consent).*(?:include|포함)")
    _require(source, "AC-IRF-013", r"(?:include|포함).*(?:vworld|VWorld).*(?:key|키)")
    _require(source, "AC-IRF-013", r"(?:omit|미포함).*(?:openstreetmap|OpenStreetMap|OSM)")
    # The secret may occur only in the affirmative private-runtime branch, never in payload/CSV.
    _require(source, "AC-IRF-013", r"payload.*(?:key|credential|secret).*(?:omit|exclude|없음)|(?:key|credential|secret).*(?:not|never).*(?:payload|CSV)")
    assert _FAKE_KEY not in source, "AC-IRF-013: acceptance key must not be build-time embedded"


def test_ac014_missing_key_is_keyless_osm_export_without_include_choice(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "simple_inventory")
    _require(source, "AC-IRF-014", r"(?:missing|blank|whitespace|usable).*(?:key|키)")
    _require(source, "AC-IRF-014", r"(?:openstreetmap|OpenStreetMap|OSM).*(?:export|standalone|독립)")
    _require(source, "AC-IRF-014", r"(?:no|without|없|미포함).*(?:blank|empty|placeholder).*(?:vworld|VWorld)")
    _require(source, "AC-IRF-014", r"(?:include|포함).*(?:disabled|unavailable|hidden|없|미제공)")
    assert _has(source, r"!\s*[^;]*(?:vworld|VWorld)[^;]*(?:key|키)[^;]*(?:osm|OSM|openstreetmap)")


@pytest.mark.parametrize("survey_type", _TYPES)
def test_ac015_direct_sqlite_reads_actual_spatial_rows_and_reports_only_authorized_fallback(
    acceptance_api, tmp_path, survey_type
):
    _, source = _build(acceptance_api, tmp_path, survey_type)
    _require(source, "AC-IRF-015", r"gpkg_contents", r"gpkg_geometry_columns")
    _require(source, "AC-IRF-015", r"executeSql|sqlite|SQLite|read.?only")
    _require(source, "AC-IRF-015", r"SELECT[\s\S]{0,240}(?:FROM|from)[\s\S]{0,240}(?:table|table_name|geometry)")
    _require(source, "AC-IRF-015", r"(?:actual|current|raw).*(?:row|record)|records.*(?:actual|current|raw)")
    _require(source, "AC-IRF-015", r"geometry.?column|geometry_field")
    _require(source, "AC-IRF-015", r"source.?crs|srs_id|geometry.?crs")
    _require(source, "AC-IRF-015", r"attributes|attrs")
    _require(source, "AC-IRF-015", r"payload|report.*data|map_features|tables")
    _require(source, "AC-IRF-015", r"loaded.?layer|configured.?layer|fallback")
    _require(source, "AC-IRF-015", r"direct.*(?:impossible|unavailable|fail)|inaccessible|접근.*불가")
    _require(source, "AC-IRF-015", r"(?:limitation|completeness|완전성|제한).*(?:omitted|uncollected|누락|미수집)")
    # A direct SQLite branch must not silently downgrade to loaded layers after metadata succeeds.
    direct_body = _function_body(source, "qpbInspectCurrentGpkgSpatialMetadata")
    assert _has(direct_body, r"executeSql[\s\S]{0,1800}(?:records|attributes|geometry_column|source_crs)"), (
        "AC-IRF-015: direct SQLite mode must place actual rows and their geometry/attributes in payload"
    )
    assert _has(direct_body, r"(?:catch|if)[\s\S]{0,1200}(?:fallback|loaded.?layer|inaccessible)"), (
        "AC-IRF-015: direct-access failure must be the explicit fallback boundary"
    )


def test_ac016_official_d3_bundle_is_local_and_chart_initialization_validates_aggregates(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "vegetation_mapping")
    _require(source, "AC-IRF-016", r"d3\.js|d3\.v[0-9]|D3\.js")
    _require(source, "AC-IRF-016", r"official|Copyright.*Mike Bostock|d3js\.org|d3js")
    _require(source, "AC-IRF-016", r"(?:local|bundle|inline|single.?file).*(?:d3|chart)|(?:d3|chart).*(?:local|bundle|inline)")
    assert not _has(source, r"<script[^>]+src=[\"']https?://[^\"']*d3", r"import\s+.*https?://.*d3"), (
        "AC-IRF-016: d3 must not be a remote dependency"
    )
    _require(source, "AC-IRF-016", r"(?:validate|validation).*(?:chart|d3|초기화)|(?:chart|d3|초기화).*(?:validate|validation)")
    _require(source, "AC-IRF-016", r"(?:initialized|initialization|초기화).*(?:occurrence|출현)")
    _require(source, "AC-IRF-016", r"(?:initialized|initialization|초기화).*(?:cover|피도)")
    _require(source, "AC-IRF-016", r"(?:initialized|initialization|초기화).*(?:area|면적)")
    _require(source, "AC-IRF-016", r"(?:unavailable|limited|제한|사용 불가).*(?:chart|analytics|분석)")
    _require(source, "AC-IRF-016", r"(?:source.?row|raw.?row).*(?:aggregation|집계)|(?:aggregation|집계).*(?:source.?row|raw.?row)")
    _require(source, "AC-IRF-016", r"(?:occurrence|출현).*(?:average|평균).*(?:area|면적)|(?:area|면적).*(?:average|평균).*(?:occurrence|출현)")


def test_ac017_dimensional_wkb_discards_zm_and_supports_all_xy_geometry_types(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "vegetation_mapping")
    _require(source, "AC-IRF-017", r"qpbDecodeWkb|WKB|dimensional|dimension")
    for geometry_type in (
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
        "GeometryCollection",
    ):
        assert geometry_type in source, f"AC-IRF-017: dimensional {geometry_type} must be supported"
    _require(source, "AC-IRF-017", r"Z/M|z/m|hasZ|hasM|includeZ|includeM")
    _require(source, "AC-IRF-017", r"discard|drop|strip|remove|ignore|slice\s*\(\s*0\s*,\s*2\s*\)|X/Y")
    _require(source, "AC-IRF-017", r"ISO|1000|2000|3000|0x80000000|0x40000000|EWKB")
    _require(source, "AC-IRF-017", r"EPSG:4326|WGS.?84|qpbTransformGeoJson")


def test_ac017_invalid_xy_is_retained_with_limitation_and_never_fabricated_from_zm(
    acceptance_api, tmp_path
):
    _, source = _build(acceptance_api, tmp_path, "permanent_plots")
    decoder = _function_body(source, "qpbDecodeWkb")
    collector = _function_body(source, "qpbCollectGpkgSpatialRows")
    _require(source, "AC-IRF-017", r"malformed.*(?:X/Y|coordinate)|invalid.*(?:X/Y|coordinate)")
    _require(source, "AC-IRF-017", r"valid\s*:\s*false|invalid geometry|malformed coordinates")
    _require(source, "AC-IRF-017", r"reason|limitation|geometry_limitations")
    _require(source, "AC-IRF-017", r"(?:renderMap|mapFeatures|map features)[\s\S]{0,1400}geometry\.valid")
    _require(source, "AC-IRF-017", r"Z/M.*(?:not|never|no|without)|(?:not|never|no|without).*Z/M")
    assert _has(decoder, r"(?:invalid|malformed|finite|NaN|isFinite|throw)"), (
        "AC-IRF-017: WKB decoder must reject malformed/non-finite X/Y"
    )
    assert _has(collector, r"records[\s\S]{0,1400}(?:valid|reason|geometry)"), (
        "AC-IRF-017: invalid source rows must remain in report records with a reason"
    )
    assert not _has(collector, r"(?:Z|M)[^\n]{0,80}(?:fallback|coordinate|geometry)"), (
        "AC-IRF-017: invalid X/Y must not obtain fabricated coordinates from Z/M"
    )


def test_ac017_table_and_csv_contract_excludes_zm_coordinates_and_values(acceptance_api, tmp_path):
    _, source = _build(acceptance_api, tmp_path, "simple_inventory")
    collector = _function_body(source, "qpbCollectGpkgSpatialRows")
    joined = _function_body(source, "renderJoined")
    csv = _function_body(source, "saveCsv")
    _require(source, "AC-IRF-017", r"attributes|attrs|report.*(?:table|data)")
    _require(source, "AC-IRF-017", r"CSV|saveCsv|csvCell")
    _require(source, "AC-IRF-017", r"Z/M|z/m|ordinate|coordinate")
    _require(source, "AC-IRF-017", r"(?:exclude|omit|remove|strip|discard|ignore).*(?:Z/M|Z|M)|(?:Z/M|Z|M).*(?:exclude|omit|remove|strip|discard|ignore)")
    assert not _has(collector, r"attrs\s*\[[^\]]*(?:^|[_ ])(?:z|m)(?:$|[_ ])[^\]]*\]")
    assert not _has(joined, r"(?:z|m)[-_ ]?(?:coordinate|ordinate)|coordinate[-_ ]?(?:z|m)")
    assert not _has(csv, r"(?:z|m)[-_ ]?(?:coordinate|ordinate)|coordinate[-_ ]?(?:z|m)")
    assert _has(csv, r"cols\s*=\s*data\.columns|data\.columns[\s\S]{0,600}csvCell"), (
        "AC-IRF-017: CSV must serialize the filtered report column contract, not geometry ordinates"
    )


@pytest.mark.network
@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(reason="AC-IRF-001/002 require live VWorld/OSM failure injection and a QField/browser session")
def test_ac001_ac002_live_background_selection_fallback_and_offline_local_usability():
    raise AssertionError("manual/network gate is documented by the skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(reason="AC-IRF-004..012 stateful browser/QField behavior requires runtime evidence")
def test_ac004_through_ac012_browser_state_preservation_and_csv_round_trip():
    raise AssertionError("manual/device gate is documented by the skip reason")
