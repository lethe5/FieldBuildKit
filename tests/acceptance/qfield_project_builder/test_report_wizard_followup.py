"""Acceptance coverage for the approved report/wizard follow-up (AC-RWF-001..014).

The existing acceptance harness can build real project artifacts and inspect generated QML, but it
does not host a browser, QField, or an interactive Qt wizard session.  This module therefore keeps
the automated assertions at the artifact/source/data boundary and records the remaining browser,
device, and visual-layout checks as explicit skips.  It uses only the shared acceptance fixtures;
the supplied diagnostic HTML is intentionally not a normative fixture.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
import re
from pathlib import Path

import pytest

from .conftest import make_base_config, open_gpkg

pytestmark = pytest.mark.qgis

TYPE_1_TO_3 = ("simple_inventory", "temporary_plots", "permanent_plots")
IDENTIFICATION_TARGETS = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}
REPORT_VWORLD_KEY = "ACCEPTANCE-RWF-VWORLD-KEY-NOT-DATA"


def _build(
    acceptance_api,
    tmp_path: Path,
    survey_type: str,
    *,
    identification_enabled: bool = False,
    basemap: dict | None = None,
):
    config = make_base_config(
        survey_type,
        display_name=f"RWF acceptance {survey_type}",
    )
    config["identification_enabled"] = identification_enabled
    if basemap is not None:
        config["basemap"] = basemap
    result = acceptance_api.build_project(config, str(tmp_path / f"rwf_{survey_type}"))
    assert result["success"], result.get("error_message")
    return result


def _sidecar(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    path = project_dir / f"{result['project_slug']}.qml"
    assert path.is_file(), f"expected generated report/plugin sidecar: {path}"
    return path.read_text(encoding="utf-8")


def _widget(inspect_identification_widget, result: dict, layer_name: str) -> str:
    report = inspect_identification_widget(result["project_dir"], layer_name)
    assert report.get("qml_widget_field_found") is True, report
    source = report.get("qml_code", "")
    assert source.strip(), "expected non-empty generated identification QML"
    return source


def _function_body(source: str, function_name: str) -> str:
    """Return one JavaScript function body using a string-aware brace scan."""
    match = re.search(rf"\bfunction\s+{re.escape(function_name)}\s*\(", source)
    assert match, f"expected generated function {function_name}()"
    opening = source.find("{", match.end())
    assert opening >= 0, f"expected opening brace for {function_name}()"
    depth = 0
    quote = None
    escaped = False
    for index in range(opening, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"unterminated generated function {function_name}()")


def _strip_js_comments(source: str) -> str:
    """Remove JS/QML comments without treating ``https://`` string data as a comment."""
    output: list[str] = []
    quote = None
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if quote:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
            output.append(char)
            index += 1
        elif char == "/" and next_char == "/":
            newline = source.find("\n", index + 2)
            if newline < 0:
                break
            output.append("\n")
            index = newline + 1
        elif char == "/" and next_char == "*":
            end = source.find("*/", index + 2)
            if end < 0:
                break
            output.append("\n" * source[index : end + 2].count("\n"))
            index = end + 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


class _VisibleHtmlSurface(HTMLParser):
    """Collect literal HTML text and user-facing attribute values only."""

    _VISIBLE_ATTRIBUTES = frozenset(
        {"alt", "aria-label", "aria-labelledby", "label", "placeholder", "title", "value"}
    )
    _NON_VISIBLE_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._NON_VISIBLE_TAGS:
            self._hidden_depth += 1
        if self._hidden_depth == 0:
            self.values.extend(
                value for name, value in attrs
                if name.lower() in self._VISIBLE_ATTRIBUTES and value
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._hidden_depth == 0:
            self.values.extend(
                value for name, value in attrs
                if name.lower() in self._VISIBLE_ATTRIBUTES and value
            )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._NON_VISIBLE_TAGS and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._hidden_depth == 0 and data.strip():
            self.values.append(data)


def _iter_js_string_literals(source: str):
    """Yield ``(raw_value, start, end)`` for JS/QML string literals, sans comments."""
    quote = None
    escaped = False
    start = None
    for index, char in enumerate(source):
        if quote is None:
            if char in "'\"`":
                quote = char
                start = index + 1
            continue
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            assert start is not None
            yield source[start:index], start - 1, index + 1
            quote = None
            start = None


def _decode_js_literal(raw_value: str) -> str:
    """Decode only the escapes relevant to visible generated copy."""
    return re.sub(r"\\([\\'\"`])", r"\1", raw_value).replace("\\n", "\n")


def _report_user_facing_surface(source: str) -> str:
    """Return literal report HTML text/attributes, excluding executable/source metadata."""
    code = _strip_js_comments(source)
    values: list[str] = []

    def collect_html(fragment: str) -> None:
        parser = _VisibleHtmlSurface()
        parser.feed(fragment)
        values.extend(parser.values)

    for raw_value, start, end in _iter_js_string_literals(code):
        value = _decode_js_literal(raw_value)
        if "<" in value and ">" in value:
            collect_html(value)
            continue
        preceding = code[max(0, start - 220):start]
        if re.search(
            r"\b(?:textContent|innerHTML|title|aria-label|aria-labelledby|placeholder|alt|value)\b"
            r"|\b(?:label|heading|status|emptyState|detail|notice|capability)\s*:",
            preceding.rstrip(),
            re.IGNORECASE,
        ) and re.search(
            r"(?:textContent|innerHTML|title|aria-label|aria-labelledby|placeholder|alt|value)\s*(?:=|:)\s*$"
            r"|(?:label|heading|status|emptyState|detail|notice|capability)\s*:\s*$",
            preceding,
            re.IGNORECASE,
        ):
            values.append(value)
    for match in re.finditer(
        r"\bsetAttribute\(\s*(['\"])(?:aria-label|aria-labelledby|title|placeholder|alt|value)\1"
        r"\s*,\s*(['\"])(.*?)\2",
        code,
        re.DOTALL | re.IGNORECASE,
    ):
        values.append(_decode_js_literal(match.group(3)))
    return "\n".join(values)


def _qml_user_facing_surface(source: str) -> str:
    """Return QML text-bearing properties and translation-call values, not QML source."""
    code = _strip_js_comments(source)
    values: list[str] = []
    property_pattern = re.compile(
        r"\b(?:text|title|placeholderText|toolTip|accessibleName|displayText)\s*:\s*"
        r"(?:qsTr\(\s*)?(['\"])(.*?)\1",
        re.DOTALL,
    )
    values.extend(
        match.group(2)
        for match in property_pattern.finditer(code)
    )
    values.extend(
        match.group(2)
        for match in re.finditer(r"\bqsTr\(\s*(['\"])(.*?)\1", code, re.DOTALL)
    )
    return "\n".join(values)


def _report_definition(source: str) -> dict:
    marker = "qpbReportDefinition:"
    start = source.find(marker)
    assert start >= 0, "expected embedded report definition"
    object_start = source.find("{", start)
    assert object_start >= 0, "expected JSON report-definition object"
    decoder = json.JSONDecoder()
    definition, _end = decoder.raw_decode(source[object_start:])
    assert isinstance(definition, dict)
    return definition


def _online_report_basemap(*, key: str | None, consent: bool = False) -> dict:
    config = {
        "mode": "online",
        "layer": "Base",
        "consent_accepted": consent,
        "remember_key": False,
    }
    if key is not None:
        config["vworld_api_key"] = key
    return config


def _assert_report_local_runtime_contract(source: str) -> None:
    code = _strip_js_comments(source)
    assert re.search(r"<html[^>]*lang=['\"]ko['\"]", code, re.IGNORECASE)
    assert "qpbCollectCurrentRecords" in code
    assert "qpbBuildJoinedRows" in code
    assert "qpbBuildAnalytics" in code
    assert "qpbGeometryLimitations" in code
    assert "qpbCsvCell" in code or "csvCell" in code
    assert re.search(r"qpbEscapeHtml|escapeHtml", code)
    assert re.search(r"qpbInitializeReport\s*\(\s*\)\s*\{[^{}]*reportInitialized", code)
    assert re.search(r"reportInitialized\s*=\s*true", code)
    assert re.search(r"DOMContentLoaded[\s\S]{0,100}\{\s*once\s*:\s*true", code)


# AC-RWF-001 / AC-RWF-002 / AC-RWF-003 / AC-RWF-004 / AC-RWF-006 -----------------------------


@pytest.mark.parametrize("survey_type", TYPE_1_TO_3)
def test_ac001_no_usable_vworld_key_keeps_report_generation_and_fallback_guarded(
    acceptance_api, tmp_path, survey_type
):
    result = _build(
        acceptance_api,
        tmp_path,
        survey_type,
        basemap=_online_report_basemap(key=None),
    )
    source = _strip_js_comments(_sidecar(result))
    _assert_report_local_runtime_contract(source)

    selected = _function_body(source, "qpbSelectBackground")
    assert re.search(r"vworld_key[\s\S]{0,140}trim\(\)[\s\S]{0,160}qpbAddVworldBackground", selected)
    assert not re.search(r"qpbAddVworldBackground\s*\(\s*map\s*,\s*['\"]['\"]", source)
    assert "OpenStreetMap" in source
    assert re.search(r"키가\s*없|키\s*없음|사용할\s*수\s*없|설정되지", source)
    assert "오프라인" in source
    for token in ("통합", "필터", "정렬", "CSV", "기록"):
        assert token in source, f"no-key report must retain local {token} surface"


def test_ac002_key_first_vworld_failure_fallback_and_offline_status_are_nonfatal_and_singleton(
    acceptance_api, tmp_path
):
    result = _build(
        acceptance_api,
        tmp_path,
        "temporary_plots",
        basemap=_online_report_basemap(key=REPORT_VWORLD_KEY, consent=True),
    )
    source = _strip_js_comments(_sidecar(result))

    assert REPORT_VWORLD_KEY not in source, "VWorld key must not be copied into report/UI source"
    assert "qpbRuntimeVworldKey" in source
    assert re.search(r"api\.vworld\.kr", source)
    assert re.search(r"OpenStreetMap", source)
    assert re.search(r"tileerror|onerror|load.*error", source, re.IGNORECASE)
    assert re.search(r"qpbFallbackToOsmOnce", source)
    fallback = _function_body(source, "qpbFallbackToOsmOnce")
    assert re.search(r"FallbackAttempted|fallbackAttempted|__qpbOsmFallbackAttempted", fallback)
    assert re.search(r"offline|오프라인", source, re.IGNORECASE)
    assert re.search(r"attribution|OpenStreetMap contributors|국토교통부", source, re.IGNORECASE)
    assert "qpbAddOsmBackground(map,reason)" in source or "qpbAddOsmBackground" in source
    assert re.search(r"if\s*\([^)]*OsmBackground[^)]*\)\s*return", source)


def test_ac003_local_geometry_and_non_geometry_data_survive_background_failure(
    acceptance_api, tmp_path
):
    result = _build(
        acceptance_api,
        tmp_path,
        "permanent_plots",
        basemap=_online_report_basemap(key=None),
    )
    conn = open_gpkg(Path(result["gpkg_path"]))
    try:
        site_count, non_null_site_geometry = conn.execute(
            "SELECT COUNT(*), COUNT(site_geom) FROM site;"
        ).fetchone()
        plot_count, non_null_plot_geometry = conn.execute(
            "SELECT COUNT(*), COUNT(plot_geom) FROM plot;"
        ).fetchone()
    finally:
        conn.close()
    assert site_count == 1 and non_null_site_geometry == 1
    assert plot_count == 1 and non_null_plot_geometry == 1

    source = _strip_js_comments(_sidecar(result))
    geometry = _function_body(source, "qpbGeometryToGeoJson")
    assert re.search(r"missing geometry|invalid geometry|unavailable", geometry, re.IGNORECASE)
    assert re.search(r"serialRecords\.push|records.*push", source)
    assert re.search(r"joined|qpbBuildJoinedRows", source)
    assert re.search(r"geometry_limitations|qpbGeometryLimitations", source)
    assert re.search(r"valid geometry only|invalid.*remain.*tables|유효하지", source, re.IGNORECASE)


# AC-RWF-004 / AC-RWF-005 / AC-RWF-006 ---------------------------------------------------------


@pytest.mark.parametrize("survey_type", TYPE_1_TO_3)
def test_ac004_identity_columns_have_exact_order_and_authoritative_row_mapping(
    acceptance_api, tmp_path, survey_type
):
    result = _build(acceptance_api, tmp_path, survey_type)
    source = _strip_js_comments(_sidecar(result))
    definition = _report_definition(source)
    observation_table = next(
        table
        for table in definition["tables"]
        if table["name"] == IDENTIFICATION_TARGETS[survey_type]
    )
    fields = {field["name"]: field for field in observation_table["fields"]}
    assert [fields[name]["label"] for name in (
        "selected_korean_name",
        "selected_scientific_name",
        "selected_ktsn",
    )] == ["국명", "학명", "KTSN"]

    columns = _function_body(source, "qpbJoinedColumns")
    identity_adds = re.search(
        r'add\(\s*["\']selected_korean_name["\']\s*,\s*["\']국명["\']\s*\)'
        r'[\s\S]{0,240}'
        r'add\(\s*["\']selected_scientific_name["\']\s*,\s*["\']학명["\']\s*\)'
        r'[\s\S]{0,240}'
        r'add\(\s*["\']selected_ktsn["\']\s*,\s*["\']KTSN["\']\s*\)',
        columns,
    )
    assert identity_adds, "identity columns must be consecutive and ordered 국명, 학명, KTSN"

    row_builder = _function_body(source, "qpbMakeJoinedRow")
    assert re.search(r"attrs\.selected_korean_name", row_builder)
    assert re.search(r"attrs\.selected_scientific_name", row_builder)
    assert re.search(r"attrs\.selected_ktsn", row_builder)
    assert re.search(r"===\s*undefined[\s\S]{0,100}=\s*[\"']?[\"']?", row_builder)
    joined = _function_body(source, "qpbBuildJoinedRows")
    assert re.search(r"leafRecords|leafRecords\.length", joined)
    assert re.search(r"rows\.push", joined)
    assert re.search(r"append\(\s*[\"']observation[\"']", joined)


def test_ac005_identity_filters_sorting_csv_scope_and_escaping_preserve_existing_rows(
    acceptance_api, tmp_path
):
    source = _strip_js_comments(
        _sidecar(_build(acceptance_api, tmp_path, "temporary_plots"))
    )
    assert re.search(r"allRows\s*=|allRows", source)
    assert re.search(r"allRows\.filter|data\.columns\.length", source)
    assert re.search(r"visibleRows\.sort", source)
    assert re.search(r"localeCompare|Number\(|strictDate", source)
    assert re.search(r"data-sort|aria-sort", source)
    assert re.search(r"selected_korean_name|selected_scientific_name|selected_ktsn", source)
    csv = _function_body(source, "qpbBuildJoinedCsv")
    assert re.search(r"columns[\s\S]{0,180}joined|rows", csv)
    assert re.search(r"replace\(/\"/g,\s*['\"]\"\"['\"]\)|replace\(/\"/g", csv)
    assert "\\ufeff" in csv or "UTF-8" in csv or "utf-8" in csv
    assert re.search(r"filtered|all.?rows|visibleRows", source, re.IGNORECASE)
    assert re.search(r"qpbEscapeHtml|escapeHtml", source)


def test_ac006_type4_report_has_no_fabricated_plant_identity_or_identification_target(
    acceptance_api, inspect_identification_widget, tmp_path
):
    result = _build(acceptance_api, tmp_path, "vegetation_mapping", identification_enabled=True)
    source = _strip_js_comments(_sidecar(result))
    definition = _report_definition(source)
    names = {table["name"] for table in definition["tables"]}
    assert "community" in names
    assert "observation" not in names
    assert "inventory_observation" not in names
    community = next(table for table in definition["tables"] if table["name"] == "community")
    assert not {
        "selected_korean_name",
        "selected_scientific_name",
        "selected_ktsn",
    }.intersection({field["name"] for field in community["fields"]})
    report = inspect_identification_widget(result["project_dir"], "community")
    assert report["qml_widget_field_found"] is False


# AC-RWF-007 / AC-RWF-008 -----------------------------------------------------------------------


_FORBIDDEN_VISIBLE_ENGLISH = (
    "Species key",
    "Occurrence count",
    "record count",
    "visible row count",
    "No records",
    "No species records",
    "Joined table",
    "Joined data",
    "stable UUID",
    "joined parent context",
    "invalid/missing geometry",
    "OVERVIEW",
    "ANALYTICS",
    "LOCAL FEATURES",
    "RECORD SUMMARY",
    "SOURCE RECORDS",
    "HTML Report",
    "Export HTML Report",
    "Identify attached photos",
    "Joined feature detail",
)


def _assert_korean_report_copy(source: str) -> None:
    code = _report_user_facing_surface(source)
    required = (
        "종 식별값",
        "출현 횟수",
        "기록 수",
        "표시 중인 행 수",
        "기록 없음",
        "다운로드",
        "기능 확인 상태",
        "통합 표",
        "고정 UUID",
        "연결된 상위 기록",
        "유효하지 않거나 누락된 도형",
        "HTML 보고서",
        "내보내기",
    )
    for text in required:
        assert text in code, f"required Korean report meaning is missing: {text}"
    for phrase in _FORBIDDEN_VISIBLE_ENGLISH:
        assert phrase.lower() not in code.lower(), f"untranslated FieldBuild Standalone copy remains: {phrase}"


@pytest.mark.parametrize("survey_type", TYPE_1_TO_3 + ("vegetation_mapping",))
def test_ac007_generated_report_and_related_surface_use_korean_fieldbuild_copy(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type
):
    result = _build(acceptance_api, tmp_path, survey_type, identification_enabled=True)
    source = _sidecar(result)
    _assert_korean_report_copy(source)
    if survey_type in TYPE_1_TO_3:
        widget = _widget(inspect_identification_widget, result, IDENTIFICATION_TARGETS[survey_type])
        widget_copy = _qml_user_facing_surface(widget)
        assert "사진으로 동정하기" in widget_copy
        assert not any(
            phrase.lower() in widget_copy.lower()
            for phrase in _FORBIDDEN_VISIBLE_ENGLISH
        )


def test_ac008_proper_names_and_internal_keys_remain_distinct_secondary_metadata(
    acceptance_api, tmp_path
):
    source = _strip_js_comments(_sidecar(_build(acceptance_api, tmp_path, "simple_inventory")))
    for proper_name in ("VWorld", "OpenStreetMap", "FieldBuild Standalone", "KTSN"):
        assert proper_name in source
    assert re.search(r"f\.label[\s\S]{0,180}f\.name|field\.label[\s\S]{0,180}field\.name", source)
    assert re.search(r"qpbEscapeHtml|escapeHtml", source)
    assert re.search(r"selected_korean_name|selected_scientific_name|selected_ktsn", source)
    assert "국명" in source and "학명" in source and "KTSN" in source


# AC-RWF-009 / AC-RWF-010 / AC-RWF-011 ---------------------------------------------------------


def _runtime_identification_calls(source: str) -> list[str]:
    declaration = re.search(r"function\s+qpbRunIdentification\s*\(", source)
    calls = []
    for match in re.finditer(r"\bqpbRunIdentification\s*\(\s*\)", source):
        if declaration and declaration.start() <= match.start() < declaration.end():
            continue
        calls.append(match.group(0))
    return calls


@pytest.mark.parametrize("survey_type", TYPE_1_TO_3)
def test_ac009_all_type1_to_3_identify_buttons_start_immediately_without_app_gate(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type
):
    result = _build(
        acceptance_api,
        tmp_path,
        survey_type,
        identification_enabled=True,
    )
    source = _strip_js_comments(
        _widget(inspect_identification_widget, result, IDENTIFICATION_TARGETS[survey_type])
    )
    button = re.search(r"id\s*:\s*qpbIdentifyButton[\s\S]{0,500}", source)
    assert button, "expected generated photo-identification button"
    assert "text: \"사진으로 동정하기\"" in button.group(0)
    handler = source[source.find("onClicked:", button.start()) :]
    assert re.search(r"onClicked\s*:[\s\S]{0,260}qpbRunIdentification\s*\(\s*\)", handler)
    assert "qpbConsentDialog" not in source
    assert not re.search(r"\b(open|show)\s*\(", handler)
    assert not re.search(r"\bDialog\s*\{", source)
    assert len(_runtime_identification_calls(source)) == 1


def test_ac010_identification_workflow_writeback_and_location_boundaries_remain_intact(
    acceptance_api, inspect_identification_widget, tmp_path
):
    for survey_type in TYPE_1_TO_3:
        result = _build(
            acceptance_api,
            tmp_path / survey_type,
            survey_type,
            identification_enabled=True,
        )
        widget = _strip_js_comments(
            _widget(inspect_identification_widget, result, IDENTIFICATION_TARGETS[survey_type])
        )
        plugin = _strip_js_comments(_sidecar(result))
        combined = f"{widget}\n{plugin}"
        assert "qpbCurrentPhotoPaths" in widget
        assert "qpbBuildPlantNetUrl" in widget
        assert "qpbSelectCandidate" in widget
        assert "qpbWriteAttributeWriteBackRequest" in widget
        assert re.search(r"changeAttribute\s*\(\s*[\"']selected_korean_name", plugin)
        assert re.search(r"selected_scientific_name[\s\S]{0,180}selected_ktsn", plugin)
        assert re.search(r"selected_scientific_name[\s\S]{0,220}continue", plugin)
        assert re.search(r"selected_ktsn[\s\S]{0,220}continue", plugin)
        assert "featureForm" in plugin and "embeddedFeatureForm" in plugin
        assert re.search(r"uuid|layer", plugin, re.IGNORECASE)
        location = _function_body(widget, "qpbResolveAuthoritativeLocation")
        assert "expression.evaluate" in location
        assert "isFinite" in location
        assert re.search(r"-180|180|90", location)
        assert not re.search(r"EXIF|GPS|imageMetadata|device\.location|centroid", combined, re.IGNORECASE)
        if survey_type == "simple_inventory":
            assert "geom" in combined
        elif survey_type == "temporary_plots":
            assert "survey_id" in combined and "plot_geom" in combined
        else:
            assert "survey_id" in combined and "plot_id" in combined and "plot_geom" in combined


def test_ac010_type4_is_excluded_and_photo_attachment_alone_is_not_a_trigger(
    acceptance_api, inspect_identification_widget, tmp_path
):
    result = _build(acceptance_api, tmp_path, "vegetation_mapping", identification_enabled=True)
    report = inspect_identification_widget(result["project_dir"], "community")
    assert report["qml_widget_field_found"] is False
    for survey_type in TYPE_1_TO_3:
        target_result = _build(
            acceptance_api,
            tmp_path / f"manual_only_{survey_type}",
            survey_type,
            identification_enabled=True,
        )
        source = _strip_js_comments(
            _widget(
                inspect_identification_widget,
                target_result,
                IDENTIFICATION_TARGETS[survey_type],
            )
        )
        assert len(_runtime_identification_calls(source)) == 1
        assert "onAccepted" not in source or "qpbRunIdentification" not in source


def test_ac011_privacy_location_and_authoritative_geometry_fail_closed_are_source_guarded(
    acceptance_api, inspect_identification_widget, tmp_path
):
    for survey_type in TYPE_1_TO_3:
        result = _build(
            acceptance_api,
            tmp_path / f"location_{survey_type}",
            survey_type,
            identification_enabled=True,
        )
        source = _strip_js_comments(
            _widget(inspect_identification_widget, result, IDENTIFICATION_TARGETS[survey_type])
        )
        location = _function_body(source, "qpbResolveAuthoritativeLocation")
        assert re.search(r"return\s+null", location)
        assert re.search(r"parts\.length|isFinite|out.of.bounds|<\s*-?180|>\s*180", location)
        assert "qpbLastLocation = qpbResolveAuthoritativeLocation()" in source
        assert re.search(r"photo|identification", source, re.IGNORECASE)
        assert not re.search(r"EXIF|GPS|imageMetadata|device\.location|photo.*location", source, re.IGNORECASE)


# AC-RWF-012 / AC-RWF-013 ----------------------------------------------------------------------


def test_ac012_ac013_step4_canvas_floor_scroll_layout_and_drawing_semantics_are_declared():
    from qfield_builder.ui import map_canvas, wizard

    wizard_source = Path(wizard.__file__).read_text(encoding="utf-8")
    canvas_source = Path(map_canvas.__file__).read_text(encoding="utf-8")
    assert re.search(r"QSize\(\s*700\s*,\s*560\s*\)|setMinimumSize\(\s*700\s*,\s*560\s*\)", wizard_source)
    assert re.search(r"setMinimumSize\(\s*320\s*,\s*240\s*\)", canvas_source)
    assert "QScrollArea" in wizard_source
    assert re.search(r"setWidgetResizable\(\s*True\s*\)", wizard_source)
    assert re.search(r"offline_group\s*\)\s*\n?\s*return|_offline_group_scroll", wizard_source)
    assert "offline_map_canvas" in wizard_source
    assert re.search(r"set_mode\(\s*[\"']bbox[\"']\s*\)", wizard_source)
    assert re.search(r"set_mode\(\s*[\"']polygon[\"']\s*\)", wizard_source)
    assert "finish_polygon" in wizard_source and "finish_bbox" in wizard_source
    assert "setVisible" in wizard_source
    assert "resize" in canvas_source or "resizeEvent" in canvas_source


# AC-RWF-014 ----------------------------------------------------------------------------------


def test_ac014_report_is_standalone_and_one_time_local_initialization_is_present(
    acceptance_api, tmp_path
):
    source = _strip_js_comments(_sidecar(_build(acceptance_api, tmp_path, "simple_inventory")))
    assert re.search(r"<style[\s>]|<script[\s>]", source, re.IGNORECASE)
    external_resource = re.compile(
        r"(?:<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*"
        r"\b(?:src|href|data)\s*=\s*['\"]https?://|"
        r"url\(\s*['\"]?https?://|@import\s+(?:url\(\s*)?['\"]?https?://)",
        re.IGNORECASE,
    )
    assert external_resource.search(source) is None
    assert source.count("function qpbInitializeReport") == 1
    assert re.search(r"if\s*\(\s*reportInitialized\s*\)\s*return", source)
    assert re.search(r"reportInitialized\s*=\s*true", source)
    assert re.search(r"renderMap\s*\(\s*\)", source)
    assert re.search(r"renderJoined\s*\(\s*\)", source)
    assert re.search(r"DOMContentLoaded[\s\S]{0,100}once\s*:\s*true", source)


# Explicit browser/device/visual acceptance boundaries ------------------------------------------------


@pytest.mark.network
@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-RWF-001..003/006 require a real standalone report session. Open equivalent Type 1, "
        "Type 2, and Type 3 reports with no key, a usable VWorld key, VWorld tile failure, OSM "
        "failure, and both services unavailable. Verify the Korean active/fallback/offline state, "
        "attribution, one map initialization, local features/tables/summaries/details/filter/sort/CSV, "
        "and that the key value is never visible. Do not treat tile failure as report failure."
    )
)
def test_ac001_ac002_ac003_ac004_report_runtime_fallback_and_local_functions_in_browser():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.device
@pytest.mark.skip(
    reason=(
        "AC-RWF-004/005/006 require a browser with seeded records. For Type 1/2/3, include "
        "one-to-many children with distinct identity values, null/blank/scientific-only/KTSN-only/"
        "all-empty/HTML-looking values, an orphan, and valid plus invalid geometry. Verify exact "
        "국명/학명/KTSN values per child, filtering and sorting on each identity column, unchanged "
        "source rows, and UTF-8 quoted all/filtered CSV. For Type 4 verify community-only data."
    )
)
def test_ac004_ac005_ac006_identity_and_type4_report_behavior_in_browser():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-RWF-009..011 require real QField forms and save/reopen. In Type 1, Type 2, and Type 3, "
        "attach a photo, verify attachment alone does not identify, click exactly 사진으로 동정하기, "
        "verify no application consent/confirmation/OK gate, then complete candidate selection and "
        "normal save/reopen. Check UUID/layer/parent/sibling isolation, selected identity write-back, "
        "original photo bytes/path, platform permission separation, and EXIF/device-GPS exclusion. "
        "Repeat with missing/invalid authoritative geometry and confirm only location-dependent data "
        "is unavailable. For Type 4, verify that candidates are display-only and neither species "
        "field is written automatically."
    )
)
def test_ac009_ac010_ac011_immediate_identification_and_boundaries_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-RWF-007/008 requires visual review of every FieldBuild Standalone-authored report, related "
        "identification, and desktop wizard surface. Verify natural Korean for all headings, buttons, "
        "statuses, empty states, table controls, detail/limitation/capability copy; allow only the "
        "spec-approved proper names, scientific names, file-format terms, and clearly identified "
        "internal keys/codes. Third-party provider attribution and QGIS/QField UI are excluded."
    )
)
def test_ac007_ac008_all_user_facing_copy_is_localized_in_supported_surfaces():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-RWF-012/013 requires a running desktop wizard and visual geometry checks. At 700x560 "
        "verify Step 4's actual canvas is at least 320x240 and fully pointer/touch reachable; key, "
        "layer/source, drawing/extent, status, and wizard controls do not overlap or clip. Repeat "
        "minimum/initial/larger sizes, key/layer section shown/hidden, and repeated down/up resize "
        "cycles. Confirm polygon/bbox/extent/finish/clear/zoom/navigation and generated output are "
        "unchanged."
    )
)
def test_ac012_ac013_step4_canvas_visual_layout_and_resize_stability():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.device
@pytest.mark.skip(
    reason=(
        "AC-RWF-014 requires copying an exported report to a separate location and opening it with "
        "network disabled. Verify no remote script/style/font/image is needed, each map/table/summary "
        "surface initializes once, and local data/filter/sort/detail/CSV remain usable after reload."
    )
)
def test_ac014_copied_report_is_standalone_and_local_on_browser_device():
    raise AssertionError("should never run while skipped -- see skip reason")
