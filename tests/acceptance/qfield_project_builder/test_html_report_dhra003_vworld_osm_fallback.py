"""D-HRA-003 acceptance coverage for HTML-report map-background selection.

The Python harness can build a project and inspect the generated project-plugin QML, but it
cannot run the QField project-plugin engine, a browser, or a real tile service.  Automatic tests
therefore check the generated source's observable key-selection, fallback, failure-status,
attribution, and secret-boundary constituents.  The end-to-end tile and offline behavior remains
an explicit real-QField/browser placeholder below.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

_FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-DHRA003-VWORLD-KEY-0000"


def _build_report_project(acceptance_api, tmp_path, *, key: str | None):
    config = make_base_config("simple_inventory", display_name="D-HRA-003 배경지도 테스트")
    config["basemap"] = {
        "mode": "online",
        "layer": "Base",
        "consent_accepted": key is not None,
        "remember_key": False,
    }
    if key is not None:
        config["basemap"]["vworld_api_key"] = key
    result = acceptance_api.build_project(config, str(tmp_path / ("with_key" if key else "no_key")))
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])
    plugin_path = project_dir / f"{result['project_slug']}.qml"
    assert plugin_path.is_file(), f"expected generated report plugin at {plugin_path}"
    return result, plugin_path.read_text(encoding="utf-8")


def _has(source: str, *patterns: str) -> bool:
    return any(re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _function_body(source: str, function_name: str) -> str:
    """Return a generated JavaScript function body with a string-aware brace scan."""
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


def test_dhra003_standalone_report_is_key_free_osm_only(acceptance_api, tmp_path):
    """A local exported report cannot retrieve QField credentials, so it uses OSM safely."""
    _, keyed_source = _build_report_project(
        acceptance_api, tmp_path / "keyed", key=_FAKE_VWORLD_KEY
    )
    _, no_key_source = _build_report_project(acceptance_api, tmp_path / "no_key", key=None)

    for source in (keyed_source, no_key_source):
        build_report = _function_body(source, "qpbBuildHtmlReport")
        assert "runtimeVworldAvailable = false;" in build_report
        assert 'd.basemap_mode = "osm";' in build_report
        assert 'runtimeVworldKey = "";' in build_report
        assert _has(source, r"tile\.openstreetmap\.org", r"openstreetmap\.org")
        assert "VWorld API 키 포함 여부" not in source
        assert "qpbVworldExportConsentDialog" not in source

    assert _FAKE_VWORLD_KEY not in keyed_source


def test_dhra003_remote_failure_keeps_local_report_usable_and_discloses_state(
    acceptance_api, tmp_path
):
    """FR-HRA-004/017, C-HRA-004, AC-HRA-011: tile failure is non-fatal and diagnosable."""
    _, source = _build_report_project(acceptance_api, tmp_path, key=None)

    assert _has(source, r"tileerror", r"tile.*error", r"onerror"), (
        "D-HRA-003: selected-background tile failures must be handled"
    )
    assert _has(source, r"offline", r"unavailable", r"network.*fail"), (
        "D-HRA-003: remote-background failure must be disclosed"
    )
    assert _has(source, r"fallback", r"alternate", r"other background", r"OpenStreetMap"), (
        "D-HRA-003: selected-service failure must permit/describe alternate background handling"
    )

    # Local report capabilities must remain present independently of remote tile success.
    for local_capability in (
        "renderMap",
        "renderJoined",
        "renderSummaries",
        "renderSpecies",
        "saveCsv",
        "qpbBuildHtmlReport",
    ):
        assert local_capability in source, (
            f"D-HRA-003: local report capability {local_capability!r} must survive tile failure"
        )


def test_dhra003_osm_attribution_status_and_key_not_displayed(
    acceptance_api, tmp_path
):
    """The key-free standalone report exposes OSM attribution/status, never the key."""
    _, source = _build_report_project(
        acceptance_api, tmp_path / "keyed", key=_FAKE_VWORLD_KEY
    )

    assert _FAKE_VWORLD_KEY not in source
    assert _has(
        source,
        r"OpenStreetMap[^\n]{0,160}(?:attribution|contributors)",
        r"OpenStreetMap contributors",
    ), "D-HRA-003: OpenStreetMap attribution must be visible when applicable"
    assert _has(source, r"OpenStreetMap 배경지도 확인", r"OpenStreetMap 배경지도 요청 중"), (
        "D-HRA-003: the key-free report must state its OSM background"
    )


def test_dhra003_export_never_embeds_the_saved_key(acceptance_api, tmp_path):
    """D-HRA-003: a standalone local export stays key-free and reports OSM."""
    _, source = _build_report_project(acceptance_api, tmp_path, key=_FAKE_VWORLD_KEY)

    build_report = _function_body(source, "qpbBuildHtmlReport")
    export_report = _function_body(source, "qpbExportHtmlReport")
    assert _FAKE_VWORLD_KEY not in source
    assert "runtimeVworldAvailable = false;" in build_report
    assert 'runtimeVworldKey = "";' in build_report
    assert 'd.basemap_mode = "osm";' in build_report
    assert "qpbCompleteHtmlExport();" in export_report
    assert "qpbVworldExportConsentDialog" not in source
    assert "VWorld API 키 포함 여부" not in source


@pytest.mark.device
@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "D-HRA-003 requires a real QField 4.2.4 project-plugin report session and browser. "
        "Open the standalone report with and without a saved VWorld key and verify that it "
        "does not expose a VWorld control or serialize the key, and that it reports/uses "
        "OpenStreetMap contributors attribution. Disable network and verify local feature "
        "layers, table, summary, filtering, "
        "sorting, detail, and CSV remain usable with an explicit offline-background state. "
        "Inspect the report UI and confirm the VWorld API key is not displayed or serialized. "
        "Record exact "
        "QField version/platform and browser/device evidence."
    )
)
def test_dhra003_vworld_key_first_osm_fallback_and_offline_resilience_on_device():
    raise AssertionError("should never run while skipped -- see skip reason")
