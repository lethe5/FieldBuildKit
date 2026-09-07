"""Section 13.10 — unconditional HTML-report project-plugin support (D-83/D-85/D-87).

The report mechanism and ``<project_slug>.qml`` sidecar are present for every generated project;
there is no report-enable configuration key. Identification-specific content in that shared
sidecar remains conditional on ``identification_enabled``.

Coverage:
- AC-QPB-123: every survey type, with identification both disabled and enabled, has the slug-
  named sidecar and a distinct "Export HTML Report" toolbar registration without a report toggle.
- AC-QPB-124: the report source constructs HTML with no externally hosted resources.
- AC-QPB-125: the report output path is rooted at the generated project folder.
- AC-QPB-126: manual/device-only fidelity QA, still gated by Open Question O-41.
- AC-QPB-127: executable coverage of both D-87 identification-content branches.

The generated sidecar is read directly from ``build_project()``'s output, following the existing
AC-QPB-069 acceptance-test precedent; no acceptance-harness extension is needed.
"""

from __future__ import annotations

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
_REPORT_LABEL = "Export HTML Report"
_IDENTIFICATION_REMINDER_LABEL = "Identify attached photos"
_ADD_TO_TOOLBAR_RE = re.compile(r"iface\.addItemToPluginsToolbar\(\s*(\w+)\s*\)")
_TIMER_RE = re.compile(r"\bTimer\s*\{")


def _build_project(
    acceptance_api,
    tmp_path,
    survey_type: str,
    *,
    identification_enabled: bool,
    display_name: str = "HTML 리포트 테스트 프로젝트",
):
    config = make_base_config(survey_type, display_name=display_name)
    config["identification_enabled"] = identification_enabled
    state = "identification_on" if identification_enabled else "identification_off"
    out_dir = tmp_path / f"proj_{survey_type}_{state}"
    return acceptance_api.build_project(config, str(out_dir))


def _read_plugin_qml_source(result: dict) -> str:
    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    assert slug, "build_project() must report project_slug"
    plugin_path = project_dir / f"{slug}.qml"
    assert plugin_path.is_file(), (
        f"expected the unconditional <project_slug>.qml sidecar at {plugin_path} "
        "(FR-QPB-090/100; Decision Log D-87)"
    )
    assert plugin_path.parent == Path(result["qgs_path"]).parent
    return plugin_path.read_text(encoding="utf-8")


def _assert_report_toolbar_registration(plugin_source: str) -> None:
    assert _REPORT_LABEL in plugin_source, (
        "AC-QPB-123: expected the literal 'Export HTML Report' label in the generated sidecar"
    )
    assert _ADD_TO_TOOLBAR_RE.search(plugin_source), (
        "AC-QPB-123/FR-QPB-133: expected iface.addItemToPluginsToolbar(item) in the generated "
        "sidecar"
    )


@pytest.fixture(scope="module")
def html_report_result_without_identification(acceptance_api, tmp_path_factory):
    """One identification-disabled build result for shared AC-QPB-124/125 inspection."""
    tmp_path = tmp_path_factory.mktemp("html_report_plugin_without_identification")
    result = _build_project(
        acceptance_api,
        tmp_path,
        "simple_inventory",
        identification_enabled=False,
    )
    assert result["success"], result.get("error_message")
    return result


# --- AC-QPB-123 -------------------------------------------------------------------------------


@pytest.mark.parametrize("survey_type", _SURVEY_TYPES)
@pytest.mark.parametrize("identification_enabled", [False, True])
def test_ac123_report_sidecar_and_toolbar_button_are_unconditional_without_report_toggle(
    acceptance_api,
    tmp_path,
    survey_type,
    identification_enabled,
):
    result = _build_project(
        acceptance_api,
        tmp_path,
        survey_type,
        identification_enabled=identification_enabled,
    )
    assert result["success"], result.get("error_message")
    plugin_source = _read_plugin_qml_source(result)
    _assert_report_toolbar_registration(plugin_source)

    if identification_enabled:
        add_calls = _ADD_TO_TOOLBAR_RE.findall(plugin_source)
        assert len(set(add_calls)) >= 2, (
            "AC-QPB-123: with identification enabled, the report toolbar entry must be "
            "structurally distinct from the identification reminder registration; found "
            f"{add_calls!r}"
        )


# --- AC-QPB-124 -------------------------------------------------------------------------------

# Neither FR-QPB-133 nor AC-QPB-124 fixes a handler identifier, so this deliberately looks for
# HTML-resource-shaped external references across the generated sidecar. It does not reject
# unrelated API URL strings that are not used as HTML resources.
_EXTERNAL_RESOURCE_RE = re.compile(
    r"(?:"
    r"<(?:script|link|img|iframe|source|video|audio|embed|object)\b[^>]*"
    r'\b(?:src|href|data)\s*=\s*["\']https?://'
    r"|url\(\s*[\"']?https?://"
    r"|@import\s+(?:url\(\s*)?[\"']?https?://"
    r")",
    re.IGNORECASE,
)


def test_ac124_generated_html_report_content_has_no_external_resource_references(
    html_report_result_without_identification,
):
    plugin_source = _read_plugin_qml_source(html_report_result_without_identification)

    assert re.search(r"<html", plugin_source, re.IGNORECASE), (
        "AC-QPB-124: expected the report handler to construct an HTML document"
    )
    external_ref = _EXTERNAL_RESOURCE_RE.search(plugin_source)
    assert external_ref is None, (
        "AC-QPB-124: report HTML must not reference an externally hosted resource; found "
        f"{external_ref.group(0)!r}"
    )


# --- AC-QPB-125 -------------------------------------------------------------------------------

_HOME_PATH_NEAR_HTML_RE = re.compile(r"qgisProject\.homePath[\s\S]{0,400}?\.html")
_ABS_PATH_HTML_LITERAL_RE = re.compile(r'["\'](?:/[^"\']*|[A-Za-z]:\\[^"\']*)\.html["\']')


def test_ac125_output_path_is_project_relative_via_qgis_project_home_path(
    html_report_result_without_identification,
):
    plugin_source = _read_plugin_qml_source(html_report_result_without_identification)

    assert _HOME_PATH_NEAR_HTML_RE.search(plugin_source), (
        "AC-QPB-125: expected the report .html path to be constructed from "
        "qgisProject.homePath (or the established equivalent project-root context)"
    )
    abs_literal = _ABS_PATH_HTML_LITERAL_RE.search(plugin_source)
    assert abs_literal is None, (
        "AC-QPB-125: report output must not use a hardcoded absolute path; found "
        f"{abs_literal.group(0)!r}"
    )


# --- AC-QPB-126 (manual/device placeholder; Open Question O-41) -------------------------------


@pytest.mark.device
@pytest.mark.skip(
    reason=(
        "AC-QPB-126 remains manual/device-only and gated on Open Question O-41. On a real QField "
        "device (or QGIS Desktop subject to D-46), open a generated project containing saved "
        "domain records; tap 'Export HTML Report'; confirm a standalone .html file is written "
        "inside the project folder and, offline, shows the correct survey type, record counts, "
        "project_display_name, project_id, generation date, and every current stored domain "
        "record/value. Report inability to enumerate full GeoPackage layers from QML against "
        "O-41; do not accept a schema-only or placeholder report as passing."
    )
)
def test_ac126_generated_report_reflects_actual_current_project_data_on_a_real_device():
    raise AssertionError("should never run while skipped — see skip reason")


# --- AC-QPB-127 / FR-QPB-038/090/100 (Decision Log D-87) ------------------------------------


def test_ac127_identification_disabled_keeps_report_but_omits_identification_components(
    acceptance_api,
    tmp_path,
):
    result = _build_project(
        acceptance_api,
        tmp_path,
        "simple_inventory",
        identification_enabled=False,
        display_name="식별 비활성 리포트 프로젝트",
    )
    assert result["success"], result.get("error_message")
    plugin_source = _read_plugin_qml_source(result)

    _assert_report_toolbar_registration(plugin_source)
    assert _IDENTIFICATION_REMINDER_LABEL not in plugin_source, (
        "AC-QPB-127/FR-QPB-038: identification-disabled sidecar must omit the 'Identify "
        "attached photos' reminder button"
    )
    assert _TIMER_RE.search(plugin_source) is None, (
        "AC-QPB-127/FR-QPB-038: identification-disabled sidecar must omit the identification "
        "write-back polling Timer"
    )


def test_ac127_identification_enabled_keeps_report_and_adds_identification_components(
    acceptance_api,
    tmp_path,
):
    result = _build_project(
        acceptance_api,
        tmp_path,
        "simple_inventory",
        identification_enabled=True,
        display_name="식별 활성 리포트 프로젝트",
    )
    assert result["success"], result.get("error_message")
    plugin_source = _read_plugin_qml_source(result)

    _assert_report_toolbar_registration(plugin_source)
    assert _IDENTIFICATION_REMINDER_LABEL in plugin_source, (
        "AC-QPB-127: identification-enabled sidecar must contain the 'Identify attached "
        "photos' reminder button"
    )
    assert _TIMER_RE.search(plugin_source), (
        "AC-QPB-127/FR-QPB-100/109: identification-enabled sidecar must contain the "
        "identification write-back polling Timer"
    )
    add_calls = _ADD_TO_TOOLBAR_RE.findall(plugin_source)
    assert len(set(add_calls)) >= 2, (
        "AC-QPB-127: report and identification reminder must be distinct toolbar entries; found "
        f"{add_calls!r}"
    )
