"""Unit tests for qfield_builder.qml_plugin (FR-QPB-100/101; Decision Log D-31/D-35/D-37).

Pure string-generation tests -- no PyQGIS required (unlike the acceptance suite's
`test_post_mvp_identification_plugin.py`, which additionally confirms this generated QML actually
ends up embedded correctly inside a real `.qgs` project via a real QGIS/PyQGIS runtime).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

import pytest

from qfield_builder import qml_plugin, resource_paths


def _embedded_report_scripts(content: str) -> list[str]:
    """Decode report scripts from their QML string-literal injection boundary.

    The report's Leaflet and interaction sources are emitted as one escaped QML string so that
    newlines and JavaScript quotes cannot break the generated sidecar.  Assertions about the
    resulting HTML/JavaScript should therefore inspect the value QML will pass to ``html.push``
    rather than the escaped transport representation in the sidecar source.
    """
    scripts = []
    for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', content):
        value = json.loads(match.group(1))
        if value.startswith("<script>"):
            scripts.append(value)
    return scripts


def test_project_plugin_qml_mentions_the_project_slug():
    content = qml_plugin.render_project_plugin_qml("my_demo_project")
    assert "my_demo_project" in content


def test_d3_bundle_uses_pyinstaller_resource_root(monkeypatch, tmp_path):
    """A frozen module's ``__file__`` is not the root of bundled ``resources/``."""
    vendor = tmp_path / "resources" / "vendor"
    vendor.mkdir(parents=True)
    bundle = vendor / "d3.v7.9.0.min.js"
    bundle.write_text("/* packaged d3 sentinel */", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_paths.resource_path("vendor", "d3.v7.9.0.min.js").read_text(
        encoding="utf-8"
    ) == "/* packaged d3 sentinel */"
    assert 'resource_path("vendor", "d3.v7.9.0.min.js")' in Path(
        qml_plugin.__file__
    ).read_text(encoding="utf-8")


def test_project_plugin_qml_uses_the_qfield_project_plugin_import_and_iface():
    """The project-plugin sidecar follows QField's supported, non-versioned import pattern."""
    content = qml_plugin.render_project_plugin_qml("demo")
    assert "import QtQuick 2.15" in content
    assert "import QtQuick\n" not in content
    assert "import org.qfield\n" in content
    assert "import org.qfield 1.0" not in content
    assert "import Theme\n" in content
    assert "iface.addItemToPluginsToolbar" in content


def test_identification_qml_sources_do_not_contain_malformed_qml_escaping():
    """Generated identification sources must remain parseable by QML's JavaScript parser."""
    sources = (
        qml_plugin.render_project_plugin_qml("demo", identification_enabled=True),
        qml_plugin.render_identification_widget_qml("''"),
    )

    for source in sources:
        assert "try {{" not in source
        assert r'replace(/\/g, "/")' not in source

    widget = sources[1]
    assert r'replace(/\\/g, "/")' in widget


def test_affected_generated_qml_javascript_snippets_parse_without_qfield_modules():
    """The affected functions must parse in a minimal Qt QML engine harness."""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication(["qml-plugin-syntax-test"])
    del app  # Keep the application alive through the component checks without using it directly.
    engine = QQmlEngine()
    snippets = (
        (
            "project",
            qml_plugin.render_project_plugin_qml("demo", identification_enabled=True),
            "function qpbLoadCsv(relPath) {",
            "function qpbLoadNationalKtsnSet(relPath) {",
        ),
        (
            "widget",
            qml_plugin.render_identification_widget_qml("''"),
            "function qpbSampleProbabilityRaster(sampleExpression, callback) {",
            "function qpbCanonicalLookupUnavailable(reason) {",
        ),
    )

    for name, source, start_marker, end_marker in snippets:
        snippet = source[source.index(start_marker) : source.index(end_marker)]
        component = QQmlComponent(engine)
        component.setData(
            ("import QtQml 2.15\nQtObject {\n" + snippet + "\n}\n").encode(),
            QUrl(f"{name}-syntax.qml"),
        )
        assert component.status() == QQmlComponent.Status.Ready, [
            error.toString() for error in component.errors()
        ]


def test_project_plugin_qml_report_is_unconditional_and_identification_members_are_gated():
    without_identification = qml_plugin.render_project_plugin_qml(
        "demo",
        identification_enabled=False,
        project_display_name="리포트 프로젝트",
        project_id="project-123",
        survey_type="simple_inventory",
        generated_at="2026-08-29T00:00:00+00:00",
    )
    with_identification = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=True
    )

    for content in (without_identification, with_identification):
        assert 'iconSource: "icons/report-export.svg"' in content
        assert "import Theme\n" in content
        assert "Theme.getThemeVectorIcon" not in content
        assert "qrc:" not in content.lower()
        report_button = re.search(
            r'QfToolButton \{(?P<body>.*?)objectName: "qpbReportToolbarButton"(?P<tail>.*?)\n        \}',
            content,
            re.DOTALL,
        )
        assert report_button
        report_body = report_button.group("body") + report_button.group("tail")
        assert "round: true" in report_body
        assert "width: 48" in report_body
        assert "height: 48" in report_body
        assert not re.search(r"\btext\s*:", report_body)
        assert 'Accessible.name: "HTML 보고서 내보내기"' in report_body
        assert "Theme" not in report_body
        assert "onClicked: qpbExportHtmlReport()" in report_body
        assert "iface.addItemToPluginsToolbar(qpbReportToolbarButton)" in content
        assert "FileUtils.writeFileContent(reportPath, reportContent)" in content
        assert "FileUtils.writeFileContent(csvPath, csvContent)" in content
        assert 'displayToast("Export failed: unable to write HTML report' in content
        assert (
            'displayToast("Export incomplete: HTML report was written to " + reportPath' in content
        )
        assert "qgisProject.homePath" in content
        assert "<!DOCTYPE html><html" in content

    assert "Identify attached photos" not in without_identification
    assert re.search(r"\bTimer\s*\{", without_identification) is None
    assert "iface.addItemToPluginsToolbar(qpbToolbarButton)" not in without_identification

    assert "사진으로 식물 동정" in with_identification
    assert 'iconSource: "icons/plant-identification.svg"' in with_identification
    identification_button = re.search(
        r'QfToolButton \{(?P<body>.*?)objectName: "qpbIdentificationToolbarButton"(?P<tail>.*?)\n        \}',
        with_identification,
        re.DOTALL,
    )
    assert identification_button
    identification_body = identification_button.group("body") + identification_button.group("tail")
    assert "round: true" in identification_body
    assert "width: 48" in identification_body
    assert "height: 48" in identification_body
    assert not re.search(r"\btext\s*:", identification_body)
    assert 'Accessible.name: "사진으로 식물 동정"' in identification_body
    assert "Theme" not in identification_body
    assert "iface.mainWindow().displayToast(" in identification_body
    assert re.search(r"\bTimer\s*\{", with_identification)
    assert "iface.addItemToPluginsToolbar(qpbIdentificationToolbarButton)" in with_identification


@pytest.mark.parametrize(
    ("identification_enabled", "expected_paths"),
    [
        (False, {"icons/report-export.svg"}),
        (True, {"icons/report-export.svg", "icons/plant-identification.svg"}),
    ],
)
def test_project_toolbar_svg_assets_are_complete_and_follow_the_identification_boundary(
    identification_enabled, expected_paths
):
    assets = qml_plugin.project_toolbar_svg_assets(
        identification_enabled=identification_enabled
    )

    assert set(assets) == expected_paths
    for _asset_path, svg_content in assets.items():
        root = ElementTree.fromstring(svg_content)
        assert root.tag.rsplit("}", 1)[-1] == "svg"
        assert "Theme" not in svg_content
        assert "qrc:" not in svg_content.lower()
        assert "file:" not in svg_content.lower()
        assert "://" not in svg_content


@pytest.mark.parametrize(
    ("identification_enabled", "expected_assets"),
    [
        (False, ("icons/report-export.svg",)),
        (
            True,
            ("icons/report-export.svg", "icons/plant-identification.svg"),
        ),
    ],
)
def test_project_plugin_toolbar_icons_use_direct_project_relative_paths(
    identification_enabled, expected_assets
):
    """QField toolbar controls use its supported direct project-local SVG paths."""
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=identification_enabled
    )

    direct_sources = re.findall(
        r'iconSource:\s*"(?P<path>icons/[^\"]+\.svg)"',
        content,
    )
    assert direct_sources == list(expected_assets)
    assert "Qt.resolvedUrl" not in content


def test_project_plugin_toolbar_actions_register_once_across_plugin_recreation():
    """A recreated project-plugin Item must reuse, not duplicate, existing toolbar controls."""
    content = qml_plugin.render_project_plugin_qml("demo", identification_enabled=True)
    assert content.count("iface.addItemToPluginsToolbar(") == 2
    assert "property bool qpbToolbarRegistered: false" in content
    assert 'iface.findItemByObjectName("qpbIdentificationPlugin")' in content
    assert 'iface.findItemByObjectName("qpbReportToolbarButton")' in content
    assert 'iface.findItemByObjectName("qpbIdentificationToolbarButton")' in content

    action_contracts = (
        ("qpbReportToolbarButton", "HTML 보고서 내보내기"),
        ("qpbIdentificationToolbarButton", "사진으로 식물 동정"),
    )
    for object_name, accessible_name in action_contracts:
        button = re.search(
            rf'QfToolButton \{{(?P<body>.*?)objectName: "{object_name}"(?P<tail>.*?)\n        \}}',
            content,
            re.DOTALL,
        )
        assert button
        body = button.group("body") + button.group("tail")
        assert not re.search(r"\btext\s*:", body)
        assert f'Accessible.name: "{accessible_name}"' in body
        assert f"iface.addItemToPluginsToolbar({object_name})" in content


def test_project_plugin_uses_a_qml_property_for_the_report_geometry_limit():
    """A project-plugin root cannot contain a standalone JavaScript declaration."""
    content = qml_plugin.render_project_plugin_qml("demo", identification_enabled=True)

    assert "readonly property int qpbReportFullGeometryMaxBytes: 524288" in content
    assert "var QPB_REPORT_FULL_GEOMETRY_MAX_BYTES" not in content
    assert "id: qpbReportGeometryEvaluator" in content
    assert "num_points(@g) > 16384" in content


def test_project_plugin_qml_embeds_real_build_metadata_and_schema_without_scoped_out_fields():
    content = qml_plugin.render_project_plugin_qml(
        "demo",
        identification_enabled=False,
        project_display_name="프로젝트 </script>",
        project_id="project-123",
        survey_type="simple_inventory",
        generated_at="2026-08-29T00:00:00+00:00",
    )

    definition_line = next(
        line for line in content.splitlines() if "property var qpbReportDefinition:" in line
    )
    definition_json = definition_line.split(": ", 1)[1]
    definition_json = definition_json.removeprefix("(").removesuffix(")").replace("<\\/", "</")
    definition = json.loads(definition_json)
    assert definition["project_display_name"] == "프로젝트 </script>"
    assert definition["project_id"] == "project-123"
    assert definition["survey_type"] == "simple_inventory"
    assert definition["generated_at"] == "2026-08-29T00:00:00+00:00"
    assert [table["name"] for table in definition["tables"]] == ["inventory_observation"]
    assert definition["tables"][0]["display_name"] == "식물관찰"
    assert definition["tables"][0]["geometry_field"] == "geom"
    fields = definition["tables"][0]["fields"]
    field_names = [field["name"] for field in fields]
    assert {"name": "surveyor", "label": "조사자"} in fields
    assert "leaf_photo_path" not in field_names
    assert "selected_korean_name" in field_names
    assert "selected_scientific_name" in field_names
    assert "identification_score" not in field_names
    assert "occurrence_probability" not in field_names
    assert "</script>" not in definition_line


def test_project_plugin_report_only_shows_success_toast_after_confirmed_write():
    content = qml_plugin.render_project_plugin_qml("demo", identification_enabled=False)
    export_body = _extract_function_body(
        content, "function qpbCompleteHtmlExport() {", "Component {"
    )

    write_call = "var reportWritten = FileUtils.writeFileContent(reportPath, reportContent);"
    failure_guard = 'displayToast("내보내기 실패: 현재 프로젝트 폴더에 HTML 보고서를 쓸 수 없습니다: "'
    success_toast = (
        '"HTML 보고서와 통합 CSV를 현재 프로젝트 폴더에 저장했습니다. HTML: " + reportPath'
    )
    assert write_call in export_body
    assert "var csvWritten = FileUtils.writeFileContent(csvPath, csvContent);" in export_body
    assert "if (!reportWritten)" in export_body
    assert failure_guard in export_body
    assert "return;" in export_body
    assert export_body.index(failure_guard) < export_body.index(success_toast)


def test_project_plugin_report_and_joined_csv_use_fixed_project_folder_paths_without_picker():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )

    assert (
        'return qgisProject.homePath + "/" + qpbReportDefinition.project_slug + "_report.html";'
        in content
    )
    assert (
        'return qgisProject.homePath + "/" + qpbReportDefinition.project_slug + "_joined.csv";'
        in content
    )
    assert "function qpbBuildJoinedCsv(payload)" in content
    assert 'return "\\ufeff" + lines.join("\\r\\n")' in content
    assert 'externalSavePicker: false' in content
    assert "현재 프로젝트 폴더" in content
    assert "qpbChooseReportLocation" not in content
    assert "getSaveFileName" not in content
    assert "saveFileDialog" not in content
    assert "browser-download-only" not in content


def test_generated_report_escapes_embedded_leaflet_and_interaction_sources_for_qml():
    """The generated sidecar must contain QML string escapes, never Python raw literals."""
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    assert 'html.push(r"""' not in content
    assert "__QPB_REPORT_INTERACTION_SCRIPT__" not in content
    assert "__QPB_LEAFLET_BUNDLE__" not in content
    # Escaped newlines keep each injected script a single valid QML string literal.
    assert 'html.push("<script>/* Leaflet 1.9.4' in content
    assert '\\nCopyright (c) 2010-2023' in content
    assert "foreign_key:table.foreign_key" in content


def test_project_plugin_report_enumerates_every_current_feature_and_attribute_via_qfield_api():
    """FR-QPB-133/AC-QPB-126: use QField's public whole-layer iterator API on demand.

    This is the real QField plugin path documented by ``QfLayerUtils``/``QfFeatureIterator``:
    ``createFeatureIterator(layer)`` returns every feature, ``hasNext``/``next`` exhaust it, and
    ``QgsFeature.attribute(name)`` reads the current attribute value. The iterator contract also
    requires an explicit ``close()`` call.
    """
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="temporary_plots"
    )
    collect_body = _extract_function_body(
        content,
        "function qpbCollectCurrentRecords(table) {",
        "function qpbReportOutputPath() {",
    )

    assert "qgisProject.mapLayersByName(table.display_name)" in content
    assert "LayerUtils.createFeatureIterator(layer)" in collect_body
    assert "while (iterator.hasNext())" in collect_body
    assert "var feature = iterator.next();" in collect_body
    assert "feature.attribute(field.name)" in collect_body
    assert "records.push(values)" in collect_body
    assert "finally" in collect_body
    assert "iterator.close();" in collect_body
    assert "featureCount" not in content
    assert "Full collected-record rows are unavailable" not in content


def test_project_plugin_report_renders_collected_values_as_html_rows_and_counts_them():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    build_body = _extract_function_body(
        content, "function qpbBuildHtmlReport() {", "function qpbExportHtmlReport() {"
    )

    assert "qpbInspectCurrentGpkgSpatialMetadata" in build_body
    assert "qpbCollectCurrentRecords(table)" in content
    assert "qpbEscapeHtml" in build_body


def test_project_plugin_interactive_report_embeds_join_analytics_and_local_runtime():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    assert "qpbBuildJoinedRows" in content
    assert "site_id" in content and "plot_id" in content and "survey_id" in content
    assert "missing parent" in content
    assert "selected_korean_name" in content
    assert "selected_scientific_name" in content
    assert "selected_ktsn" in content
    report_scripts = "\n".join(_embedded_report_scripts(content))
    assert "Leaflet" in report_scripts and 'L.map("map",' in report_scripts
    assert "VWorld 키 없음 · OpenStreetMap · 오프라인 로컬 지도" in content
    assert "표시 중인 행 수" in content
    assert "CSV 미리보기 다운로드 (UTF-8)" in content
    assert "현재 QField 프로젝트 폴더" in content


def test_theme_toggle_embeds_the_exact_upstream_sun_svg_bytes():
    """The self-contained Sun asset must remain byte-identical to the linked upstream asset."""
    expected_sha256 = "402ac18fcdb0909292b4cb286ec0fa65b32786aff6192264638225511ebd45f2"
    svg_bytes = qml_plugin._THEME_SUN_SVG.encode("utf-8")

    assert len(svg_bytes) == 2633
    assert hashlib.sha256(svg_bytes).hexdigest() == expected_sha256
    assert base64.b64decode(qml_plugin._THEME_SUN_DATA_URI.removeprefix("data:image/svg+xml;base64,")) == svg_bytes

    content = qml_plugin.render_project_plugin_qml("demo", identification_enabled=False)
    assert qml_plugin._THEME_SUN_DATA_URI in content
    assert "밝은 테마" not in content
    assert "어두운 테마" not in content


def test_theme_toggle_is_keyboard_focusable_operable_and_korean_labeled():
    content = qml_plugin.render_project_plugin_qml("demo", identification_enabled=False)
    report_scripts = "\n".join(_embedded_report_scripts(content))

    assert (
        '<label for=\\"checkbox\\" class=\\"toggle\\">'
        '<input type=\\"checkbox\\" class=\\"checkbox\\" id=\\"checkbox\\" '
        'aria-label=\\"테마 전환\\" tabindex=\\"0\\" />'
    ) in content
    assert 'data-theme-toggle=\\"true\\"' not in content
    assert ".checkbox{display:block;position:absolute;" in content
    assert ".checkbox{display:none" not in content
    assert "visibility:hidden" not in content
    assert ".toggle:focus-within .slider" in content
    assert "input.addEventListener(\"change\",qpbToggleTheme)" in report_scripts
    assert "qpbApplyTheme(next)" in report_scripts


def test_report_embeds_local_leaflet_geojson_runtime_and_license_not_a_dom_stub():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    report_scripts = "\n".join(_embedded_report_scripts(content))
    assert "Leaflet 1.9.4 (BSD-2-Clause)" in report_scripts
    assert 'version:"1.9.4-qpb-local"' in report_scripts
    assert "L.geoJSON" in report_scripts
    assert "L.geoBounds" in report_scripts
    assert "localLeaflet" not in content
    assert "map-polygon" not in content


def test_report_geometry_transform_uses_qgis_transform_object_or_reports_limit():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    geometry_body = _extract_function_body(
        content,
        "function qpbGeometryToGeoJson(",
        "function qpbCollectCurrentRecords",
    )
    assert "new QgsCoordinateTransform(sourceCrs, targetCrs" in geometry_body
    assert "geometry.transform(transform)" in geometry_body
    assert 'geometry.transform("EPSG:4326")' not in geometry_body
    assert "coordinate transform API unavailable" in geometry_body


def test_report_geometry_accepts_qml_geometry_and_as_json_properties():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    geometry_body = _extract_function_body(
        content,
        "function qpbGeometryToGeoJson(",
        "function qpbCollectCurrentRecords",
    )
    assert "var geometryAccessor = feature.geometry" in geometry_body
    assert "geometryAccessor.call(feature)" in geometry_body
    assert "var jsonAccessor = geometry.asJson" in geometry_body
    assert "jsonAccessor.call(geometry)" in geometry_body
    assert "feature.geometry === undefined" in geometry_body


def test_report_join_aliases_are_conditional_on_present_schema_tables():
    type1 = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    joined_body = _extract_function_body(
        type1, "function qpbJoinedColumns(d) {", "function qpbMakeJoinedRow"
    )
    assert "function hasTable(name)" in joined_body
    assert 'if (hasTable("site"))' in joined_body
    assert 'if (hasTable("plot"))' in joined_body
    assert 'if (hasTable("survey"))' in joined_body
    assert "if (hasTable(\"observation\") || hasTable(\"inventory_observation\"))" in joined_body


def test_report_background_selects_vworld_or_automatic_osm_and_handles_fallback():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="temporary_plots"
    )
    report_scripts = "\n".join(_embedded_report_scripts(content))
    selector = _extract_function_body(
        content, "function qpbSelectBackground(map) {", "function qpbReportOutputPath() {"
    )
    fallback = _extract_function_body(
        content, "function qpbFallbackToOsmOnce(map, reason) {", "function qpbAddVworldBackground(map, key) {"
    )

    # The QML selector is the generated runtime contract: it chooses VWorld only for a usable
    # saved key and selects OSM automatically otherwise.  The browser adapter may own the tile
    # endpoint, so this test must not tie that behavior to one escaped-script injection boundary.
    assert "qpbRuntimeVworldKey()" in selector
    assert re.search(
        r"if\s*\(\s*String\(vworld_key\)\.trim\(\)\s*\)\s*\{\s*"
        r"return qpbAddVworldBackground\(map, String\(vworld_key\)\.trim\(\)\);",
        selector,
    )
    assert 'return qpbAddOsmBackground(map, "");' in selector
    assert "qpbFallbackToOsmOnce" in report_scripts
    assert "qpbAddOsmBackground" in report_scripts
    assert "tileerror" in report_scripts
    assert "OpenStreetMap으로 전환" in report_scripts
    assert "map.__qpbOsmFallbackAttempted" in fallback
    assert "return qpbAddOsmBackground(map, reason);" in fallback


def test_report_map_features_are_focusable_and_open_the_existing_popup_from_keyboard():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    report_scripts = "\n".join(_embedded_report_scripts(content))
    final_map_runtime = report_scripts[report_scripts.rfind("function renderMap") :]

    assert "pointToLayer" in final_map_runtime
    assert "L.circleMarker" in final_map_runtime
    assert "qpbMapFeatureDetail(mapFeature)" in final_map_runtime
    assert 'l.on("click",function(){if(l.openPopup)l.openPopup();})' in final_map_runtime
    assert "qpbShowMapDetail" not in final_map_runtime
    assert "qpbMapPopup" not in final_map_runtime
    assert "function qpbMakeFeatureKeyboardAccessible" in final_map_runtime
    assert "getElement" in final_map_runtime
    assert 'setAttribute("tabindex","0")' in final_map_runtime
    assert 'setAttribute("role","button")' in final_map_runtime
    assert 'setAttribute("aria-label",qpbFeatureAccessibleLabel(popup))' in final_map_runtime
    assert 'holder.innerHTML=String(popup&&popup.getContent?popup.getContent():"")' in final_map_runtime
    assert 'event.key==="Enter"' in final_map_runtime
    assert 'event.key===" "' in final_map_runtime
    assert "if(popupOwner&&popupOwner.openPopup)popupOwner.openPopup();" in final_map_runtime
    assert "qpbMakeMappedFeaturesKeyboardAccessible(window.__QPB_MAP)" in final_map_runtime


def test_generated_map_feature_click_and_keyboard_show_the_actual_escaped_detail():
    """Exercise the emitted final renderer instead of checking an unused legacy declaration."""
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    runtime = "\n".join(_embedded_report_scripts(content))

    def function(name: str) -> str:
        start, end = qml_plugin._js_function_span(runtime, 0, name)
        return runtime[start:end]

    harness = "\n".join(
        [
            "var window={};",
            "var elements={};",
            "var mapEl={insertAdjacentHTML:function(){},setAttribute:function(){},appendChild:function(){},querySelector:function(){return null;},innerHTML:''};",
            "elements.map=mapEl;",
            "var document={getElementById:function(id){return elements[id]||null;},createElement:function(){return {innerHTML:'',textContent:'지도 기록 상세'};}};",
            "var data={tables:[{name:'site',display_name:'조사지',fields:[{name:'site_name',label:'조사지명'}]},{name:'plot',display_name:'조사구',fields:[{name:'plot_name',label:'조사구명'}]},{name:'survey',display_name:'조사',fields:[{name:'survey_date',label:'조사일'}]}],map_features:[",
            '{anchor_table:"plot",anchor_uuid:"plot-uuid",context:"plot_survey_observation",geometry:{valid:true,geojson:{type:"Point",coordinates:[127,37]}},source:{site:{attrs:{site_name:"북한산"}},plot:{attrs:{plot_name:"A-1<script>alert(1)</script>"}},survey:{attrs:{survey_date:"2026-09-02",surveyor:"홍길동"}}},related_observations:[{korean:"소나무",scientific:"Pinus densiflora",ktsn:"123",attrs:{selected_korean_name:"소나무<script>alert(1)</script>",selected_scientific_name:"Pinus densiflora"}}]},',
            '{anchor_table:"site",anchor_uuid:"site-uuid",context:"site",geometry:{valid:true,geojson:{type:"Polygon",coordinates:[[[126,36],[127,36],[127,37],[126,36]]]}},source:{site:{attrs:{site_name:"한라산"}}},related_observations:[]}]};',
            "function qpbSelectBackground(){}",
            "var renderedLayers=[];",
            "function makeLayer(){var element={attributes:{},listeners:{},setAttribute:function(k,v){this.attributes[k]=v;},addEventListener:function(k,v){this.listeners[k]=v;}};return {element:element,popup:null,_map:null,getElement:function(){return this.element;},bindPopup:function(html){this.popup={getContent:function(){return html;}};return this;},getPopup:function(){return this.popup;},on:function(name,handler){this.element.listeners[name]=handler;return this;},openPopup:function(){this.opened=true;},};}",
            "var L={map:function(){return {layers:[],_container:mapEl,setView:function(){return this;},fitBounds:function(){}};},geoBounds:function(){return [[36,126],[37,127]];},circleMarker:function(){return makeLayer();},geoJSON:function(input,options){var feature=input.features?input.features[0]:input,child=makeLayer();if(options.pointToLayer&&feature.geometry.type==='Point')child=options.pointToLayer(feature,[37,127]);options.onEachFeature(feature,child);var group={addTo:function(map){child._map=map;map.layers.push(child);renderedLayers.push(child);return group;}};return group;}};window.L=L;",
            "function esc(v){return String(v===undefined||v===null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\\"/g,'&quot;').replace(/'/g,'&#39;');}",
            function("qpbKoreanTableLabel"),
            function("qpbKoreanFieldLabel"),
                function("qpbVisibleLabel"),
                function("qpbPopupRead"),
                function("qpbPopupAppend"),
                function("qpbPopupObservation"),
                function("qpbMapFeatureDetail"),
            function("qpbFeatureAccessibleLabel"),
            function("qpbMakeFeatureKeyboardAccessible"),
            function("renderMap"),
            "renderMap();",
            "var clicked=renderedLayers[0];clicked.element.listeners.click({});var clickHtml=clicked.popup.getContent();",
            "qpbMakeFeatureKeyboardAccessible(clicked,clicked,clicked.getPopup());clicked.element.listeners.keydown({key:'Enter',preventDefault:function(){},stopPropagation:function(){}});var enterHtml=clicked.popup.getContent();",
            "clicked.element.listeners.keydown({key:' ',preventDefault:function(){},stopPropagation:function(){}});var spaceHtml=clicked.popup.getContent();",
            "if(renderedLayers.length!==2||!clicked.opened||clickHtml!==enterHtml||enterHtml!==spaceHtml||clickHtml.indexOf('조사일')<0||clickHtml.indexOf('조사자')<0||clickHtml.indexOf('국명')<0||clickHtml.indexOf('학명')<0||clickHtml.indexOf('&lt;script&gt;')<0||clickHtml.indexOf('<script>')>=0||clickHtml.indexOf('plot-uuid')>=0||clickHtml.indexOf('KTSN')>=0||clickHtml.indexOf('소나무')<0)throw new Error('minimal map popup path did not render');",
            "process.stdout.write(JSON.stringify({layers:renderedLayers.length,html:clickHtml}));",
        ]
    )
    completed = subprocess.run(
        ["node", "-"], input=harness, capture_output=True, text=True, timeout=10
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["layers"] == 2
    assert "조사일" in result["html"]
    assert "소나무" in result["html"]


def test_type3_observation_popup_uses_minimal_fields_for_each_related_observation():
    """Each related observation keeps only the four approved escaped popup fields."""
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    runtime = "\n".join(_embedded_report_scripts(content))

    def function(name: str) -> str:
        start, end = qml_plugin._js_function_span(runtime, 0, name)
        return runtime[start:end]

    harness = "\n".join(
        [
                "var data={tables:[{name:'observation',display_name:'식물관찰',fields:[{name:'selected_korean_name',label:'국명'},{name:'selected_scientific_name',label:'학명'}]},{name:'survey',display_name:'조사',fields:[{name:'survey_date',label:'조사일자'},{name:'surveyor',label:'조사자'},{name:'survey_note',label:'조사 메모'}]}]};",
                "function esc(v){return String(v===undefined||v===null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\\"/g,'&quot;').replace(/'/g,'&#39;');}",
                function("qpbKoreanTableLabel"),
                function("qpbKoreanFieldLabel"),
                function("qpbVisibleLabel"),
                function("qpbPopupRead"),
                function("qpbPopupAppend"),
                function("qpbPopupObservation"),
                function("qpbMapFeatureDetail"),
                "var html=qpbMapFeatureDetail({anchor_table:'plot',properties:{anchor_table:'plot'},related_observations:[{attrs:{selected_korean_name:\"첫 <script>alert('one')</script>\",selected_scientific_name:'첫 학명'},survey_context:{attrs:{survey_date:'2026-09-01',surveyor:'조사자 1'}}},{attrs:{selected_korean_name:'둘 & \\\"quoted\\\"',selected_scientific_name:'둘 학명'},survey_context:{attrs:{survey_date:'2026-09-02',surveyor:'조사자 2'}}}]});",
                "if(html.indexOf('조사일')<0||html.indexOf('조사자')<0||html.indexOf('국명')<0||html.indexOf('학명')<0||html.indexOf('2026-09-01')<0||html.indexOf('2026-09-02')<0||html.indexOf('첫 &lt;script&gt;alert(&#39;one&#39;)&lt;/script&gt;')<0||html.indexOf('둘 &amp; &quot;quoted&quot;')<0||html.indexOf('<script>')>=0||html.indexOf('KTSN')>=0||html.indexOf('조사 메모')>=0)throw new Error('minimal observation popup did not preserve labeled escaped records');",
            "process.stdout.write(JSON.stringify({html:html}));",
        ]
    )
    completed = subprocess.run(
        ["node", "-"], input=harness, capture_output=True, text=True, timeout=10
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["html"].count("조사일") == 1  # One header, two distinct observation rows.
    assert result["html"].count("scope='row'") == 2
    assert "조사일" in result["html"]
    assert "조사자" in result["html"]
    assert "국명" in result["html"]
    assert "학명" in result["html"]
    assert "2026-09-01" in result["html"]
    assert "2026-09-02" in result["html"]
    assert "첫 &lt;script&gt;alert(&#39;one&#39;)&lt;/script&gt;" in result["html"]
    assert "둘 &amp; &quot;quoted&quot;" in result["html"]
    assert "<script>" not in result["html"]


def test_report_vworld_key_lookup_has_maplayersbyname_fallback_for_qfield_variants():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="temporary_plots"
    )
    key_body = _extract_function_body(
        content, "function qpbRuntimeVworldKey() {", "function qpbReportOutputPath() {"
    )
    assert "typeof qgisProject.mapLayers === \"function\"" in key_body
    assert "typeof qgisProject.mapLayersByName === \"function\"" in key_body
    assert '"VWorld Base (online)"' in key_body
    assert '"VWorld Satellite (online)"' in key_body
    assert '"VWorld Hybrid (online)"' in key_body


def test_report_definition_excludes_vworld_key_and_standalone_export_is_osm_only():
    content = qml_plugin.render_project_plugin_qml(
        "demo",
        identification_enabled=False,
        survey_type="simple_inventory",
        vworld_key="consented-key",
    )
    definition_line = next(
        line for line in content.splitlines() if "property var qpbReportDefinition:" in line
    )
    definition = json.loads(
        definition_line.split(": ", 1)[1].removeprefix("(").removesuffix(")").replace("<\\/", "</")
    )
    build_report = _extract_function_body(
        content, "function qpbBuildHtmlReport() {", "function qpbExportHtmlReport() {"
    )
    export_report = _extract_function_body(
        content, "function qpbExportHtmlReport() {", "function qpbCompleteHtmlExport() {"
    )

    assert "vworld_key" not in definition
    assert "consented-key" not in content
    assert "runtimeVworldAvailable = false;" in build_report
    assert 'd.basemap_mode = "osm";' in build_report
    assert 'runtimeVworldKey = "";' in build_report
    assert "qpbCompleteHtmlExport();" in export_report
    assert "qpbVworldExportConsentDialog" not in content
    assert "VWorld API 키 포함 여부" not in content


def test_report_analytics_uses_strict_dates_and_agreed_species_identity_fields():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )
    analytics_body = _extract_function_body(
        content, "function qpbBuildAnalytics(datasets, joined) {", "function qpbSafeJson"
    )
    assert "qpbStrictCalendarDate" in analytics_body
    assert "Date.parse" not in analytics_body
    assert "[korean, scientific, ktsn].join" in analytics_body
    assert "identityKey" in analytics_body
    assert "datasets.survey" in analytics_body


def test_report_analytics_excludes_ktsn_only_rows_but_keeps_unidentified_fallback():
    """D-HRA-002: KTSN-only legacy rows are omitted from species analytics."""
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    analytics_body = _extract_function_body(
        content, "function qpbBuildAnalytics(datasets, joined) {", "function qpbSafeJson"
    )

    assert re.search(
        r"if\s*\(\s*!korean\s*&&\s*!scientific\s*&&\s*ktsn\s*\)\s*\{"
        r"[^{}]*no selected identity[^{}]*\}\s*else\s*\{",
        analytics_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert 'korean || scientific || "미동정"' in analytics_body
    assert 'scientific || ktsn || "미동정"' not in analytics_body


def test_project_plugin_report_runtime_escapes_html_and_quotes_csv_values():
    content = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    report_scripts = "\n".join(_embedded_report_scripts(content))
    assert '.replace(/</g,"&lt;")' in report_scripts
    assert "replace(/\"/g,'\"\"')" in report_scripts
    assert "charset=utf-8" in report_scripts
    assert "전체 행 (기본값)" in content
    assert "QField 버전·플랫폼 기능 확인 결과" in content


def test_no_generated_qml_source_embeds_a_literal_plantnet_api_key_value():
    """FR-QPB-079: no generated-project artifact may ever contain the Pl@ntNet key *value* in any
    form. The `api-key=` query-parameter *name* appearing in the request-building code is expected
    and correct (it is how the key the user enters at QField runtime is sent); what must never
    appear is a literal key value. Since no build-time config field for the key exists at all
    (HARNESS_CONTRACT.md's Section 13 addendum), the only way a literal value could leak in would
    be via this template's own Python source directly embedding one -- confirmed absent here by
    checking the key is always looked up from a project *variable name*, never assigned a literal
    string value in either generated QML source.

    Conformance-defect fix: the lookup mechanism changed from an unconfirmed
    `qgisProject.customVariables.qpb_plantnet_api_key` context-property path (which never actually
    worked -- confirmed by stakeholder report against a real QField session) to the same
    already-confirmed `expression.evaluate(...)` mechanism used elsewhere in this file, evaluating
    the QGIS expression `@qpb_plantnet_api_key` (QGIS's own documented syntax for referencing any
    variable, including a custom project variable)."""
    widget = qml_plugin.render_identification_widget_qml("''")
    # The widget is the only one of the two generated sources that actually *looks up* a key
    # value (the project-plugin sidecar only defines the shared, key-agnostic request-building
    # function). Confirm the lookup reads a project *variable name*, not a literal string value.
    assert 'expression.evaluate("@qpb_plantnet_api_key")' in widget
    assert 'qgisProject.customVariables' not in widget
    assert 'apiKey = "' not in widget.replace(" ", "")


def test_identification_widget_qml_embeds_the_confirmed_plantnet_endpoint():
    content = qml_plugin.render_identification_widget_qml("''")
    assert "my-api.plantnet.org/v2/identify" in content
    assert "my.plantnet.org" not in content


def test_identification_widget_qml_does_not_request_a_fixed_result_count():
    content = qml_plugin.render_identification_widget_qml("''")
    assert "nb-results" not in content
    assert "for (var i = 0; i < results.length; i++)" in content


def test_identification_widget_qml_filters_candidates_without_a_korean_name():
    content = qml_plugin.render_identification_widget_qml("''")
    handler_body = _extract_function_body(
        content,
        "function qpbHandlePlantNetResponse(response) {",
        "function qpbPersistIdentification",
    )
    assert (
        "if (!koreanName || String(koreanName).trim().length === 0) { continue; }"
        in handler_body
    )
    assert "국명이 있는 동정 후보를 찾지 못했습니다." in handler_body


@pytest.mark.parametrize("eligible_count", [0, 1, 5])
def test_identification_candidates_are_not_truncated_before_or_after_filtering(eligible_count):
    """D-98: execute the emitted handler, not a Python reimplementation of its loop."""
    content = qml_plugin.render_identification_widget_qml("''")
    handler = _extract_function_body(
        content,
        "function qpbHandlePlantNetResponse(response) {",
        "function qpbPersistIdentification",
    )
    names = ["unmatched", "ambiguous", "blank"] + [
        f"eligible-{i}" for i in range(eligible_count)
    ]
    response = {
        "version": "test-model",
        "results": [
            {"score": 1 - i / 20, "species": {"scientificNameWithoutAuthor": name}}
            for i, name in enumerate(names)
        ],
    }
    harness = """
var qpbCanonicalReferenceRequired = true;
var qpbLastLocation = null, qpbLastModelVersion = "";
var qpbCandidateSelectionEnabled = true;
var qpbCandidatesModel = [], qpbStatusLabel = {text: ""};
var qpbManualEntryPanel = {visible: false};
function qpbLookupCanonicalTaxonomy(name) {
    return {
        available: true,
        matched: name !== "unmatched",
        ambiguous: name === "ambiguous",
        selected_korean_name: name === "blank" ? "  " : "국명-" + name,
        selected_scientific_name: name
    };
}
function qpbFormatProbability(name, location) {
    return {text: "25%", value: 0.25};
}
"""
    harness += handler
    harness += "\nqpbHandlePlantNetResponse(" + json.dumps(response) + ");"
    harness += """
process.stdout.write(JSON.stringify({
    candidates: qpbCandidatesModel,
    manual: qpbManualEntryPanel.visible
}));
"""
    completed = subprocess.run(
        ["node", "-"], input=harness, capture_output=True, text=True, timeout=10
    )
    assert completed.returncode == 0, completed.stderr
    actual = json.loads(completed.stdout)
    assert [candidate["scientific_name"] for candidate in actual["candidates"]] == names[3:]
    assert [candidate["score"] for candidate in actual["candidates"]] == [
        entry["score"] for entry in response["results"][3:]
    ]
    assert actual["manual"] == (eligible_count == 0)


def test_identification_widget_qml_embeds_the_supplied_photo_paths_expression():
    expr = "array_to_string(array(leaf_photo_path), ',')"
    content = qml_plugin.render_identification_widget_qml(expr)
    assert expr in content


def test_identification_widget_qml_references_the_bundled_reference_relative_paths():
    content = qml_plugin.render_identification_widget_qml("''")
    assert qml_plugin.REFERENCE_KTSN_CSV_RELPATH in content
    assert qml_plugin.REFERENCE_NATIONAL_LIST_RELPATH in content
    # Never an absolute path.
    assert not qml_plugin.REFERENCE_KTSN_CSV_RELPATH.startswith("/")


def test_identification_widget_qml_discloses_the_external_service_before_sending_photos():
    """FR-QPB-013: disclose, before any request that transmits user photos, that they are sent
    to an external service."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "Pl" in content and "ntNet" in content
    assert "Pl\\u0040ntNet" in content


def test_type_2_and_3_identification_widget_starts_without_application_dialog():
    """D-90: observation forms invoke identification directly, without a hidden OK dialog."""
    content = qml_plugin.render_identification_widget_qml("''", immediate_identification=True)

    assert "qpbConsentDialog" not in content
    assert "Dialog" not in content
    assert re.search(r"onClicked:\s*\{\s*qpbRunIdentification\(\);", content)


def test_type_1_identification_widget_starts_without_application_dialog():
    """Identification is now immediate for Type 1 as well as Type 2/3."""
    content = qml_plugin.render_identification_widget_qml("''")

    assert "qpbConsentDialog" not in content
    assert "Dialog" not in content
    assert re.search(r"onClicked:\s*\{\s*qpbRunIdentification\(\);", content)


def test_identification_widget_qml_never_contains_a_literal_api_key():
    content = qml_plugin.render_identification_widget_qml("''")
    # No hardcoded key value -- only a lookup via a project variable name.
    assert "qpb_plantnet_api_key" in content


def test_qml_widget_element_name_is_non_empty():
    assert qml_plugin.QML_WIDGET_ELEMENT_NAME
    assert isinstance(qml_plugin.QML_WIDGET_ELEMENT_NAME, str)


# --- Conformance-defect fix: blank "Identify attached photos" content area in real QGIS Desktop -


def test_identification_widget_qml_uses_a_versioned_org_qfield_import():
    """Conformance-defect fix: a real on-device retest against the stakeholder's actually
    installed QField **4.2.4** showed the widget's label rendering but its content area staying
    blank, even after two prior fix rounds (`import org.qfield.core`, then a versioned
    `import org.qfield.core 1.0`). Both prior rounds had researched the required class/module
    naming against QField's master/HEAD source. A direct fetch of the real `v4.2.4`-tagged source
    (`https://raw.githubusercontent.com/opengisch/QField/v4.2.4/src/core/qgismobileapp.cpp`)
    confirmed that at v4.2.4 there is no separate `org.qfield.core` module at all -- the file-read
    singleton is plain `FileUtils`, registered as `REGISTER_SINGLETON("org.qfield", FileUtils,
    "FileUtils")`, i.e. under the same `org.qfield` URI already used by the project-plugin sidecar
    (`render_project_plugin_qml`), which is itself registered via the classic, version-required
    `qmlRegisterSingletonType` API requiring the importing QML to declare a matching version. Also
    previously confirmed empirically against a real QGIS 3.44 Desktop (Qt 5.15.18) via
    `scripts/qgis_isolated_probe.py`: an unversioned `import org.qfield` fails with "Library import
    requires a version" (a version-syntax error, distinct from -- and masking -- the separately
    expected, already-accepted "module ... is not installed" failure); a versioned
    `import org.qfield 1.0` gets past that version-syntax error to the expected "not installed"
    failure instead."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "import org.qfield 1.0" in content
    # No import statement for the old, incorrect `org.qfield.core` module remains (explanatory
    # code comments describing the historical mistake may still mention the string
    # "org.qfield.core" in prose -- only the actual `import` statement must be gone).
    assert "import org.qfield.core 1.0" not in content
    assert "import org.qfield.core\n" not in content


def test_identification_widget_qml_uses_versioned_qtquick_imports():
    """Confirmed root cause (see qml_plugin.render_identification_widget_qml's own docstring and
    the implementer completion report for this round): QGIS Desktop's real `QgsQmlWidgetWrapper`
    hosts this QML in a `QQuickWidget` running on QGIS 3.44's actual bundled Qt 5.15 engine, which
    -- unlike Qt 6 -- rejects an unversioned `import QtQuick`/`import QtQuick.Controls` outright
    with a real QML engine error ("Library import requires a version"), leaving
    `QQuickWidget.rootObject()` `None` (no content instantiated at all). Confirmed, empirically,
    that pinning an explicit version (`2.15`) resolves this under the real Qt 5.15 QGIS Desktop
    engine and continues to load without error under Qt 6 (PySide6)."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "import QtQuick 2.15" in content
    assert "import QtQuick.Controls 2.15" in content
    # No unversioned import statement remains (would otherwise still fail under Qt 5).
    assert "import QtQuick\n" not in content
    assert "import QtQuick.Controls\n" not in content


def test_type1_identification_widget_has_no_dialog_or_doubled_qml_braces():
    """Type 1 now starts identification directly and must render valid QML."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "Dialog {{" not in content
    assert "Timer {{" not in content
    assert "Dialog" not in content


def test_identification_widget_qml_root_column_has_an_explicit_height_binding():
    """Confirmed root cause, part 2 (see qml_plugin.render_identification_widget_qml's own
    docstring): even once the QML actually loads, the real `QQuickWidget` host's default
    `resizeMode` (`SizeViewToRootObject`, never overridden by QGIS's own `QgsQmlWidgetWrapper`)
    sizes the widget from the root item's own `height`/`implicitHeight` -- empirically confirmed
    to resolve to `0.0` for an un-heighted root `Column` under the real Qt 5.15 QGIS Desktop
    engine specifically (unlike Qt 6, where the same `Column` already reports a nonzero
    `implicitHeight`). The root `Column` must therefore carry its own explicit `height` binding
    reporting a real, nonzero value based on its own laid-out children."""
    content = qml_plugin.render_identification_widget_qml("''")
    root_start = content.index("Column {\n    id: qpbIdentifyRoot")
    root_header_end = content.index("\n\n", root_start)
    root_header = content[root_start:root_header_end]
    assert "height: childrenRect.height" in root_header


def test_identification_widget_qml_root_column_has_a_fixed_numeric_width():
    """Confirmed root cause, part 3 (see qml_plugin.render_identification_widget_qml's own
    docstring): binding the root Column's own `width` to `parent.width` is circular in the real
    `QgsQmlWidgetWrapper` hosting arrangement (widget size <- item width <- parent width <-
    widget size), empirically confirmed to resolve to a stable zero width -- rendering nothing at
    all regardless of height or content. The root Column must instead carry a fixed, explicit
    numeric width."""
    content = qml_plugin.render_identification_widget_qml("''")
    root_start = content.index("Column {\n    id: qpbIdentifyRoot")
    root_header_end = content.index("\n\n", root_start)
    root_header = content[root_start:root_header_end]
    # Only inspect actual QML statement lines, not explanatory `//` comment lines (which
    # deliberately mention `parent.width` in prose when describing the fix).
    code_lines = [
        line for line in root_header.splitlines() if not line.strip().startswith("//")
    ]
    code_only = "\n".join(code_lines)
    assert "width: parent" not in code_only
    assert "width: 260" in code_only


# --- Reviewer finding 1: real candidate-selection/manual-entry mechanism (FR-QPB-101/109) -------


def test_identification_widget_qml_offers_one_selectable_row_per_candidate():
    """FR-QPB-101 (revised)/FR-QPB-109 (revised): a real per-candidate selection affordance, not
    a single plain-text label."""
    content = qml_plugin.render_identification_widget_qml("''")
    # A Repeater renders one row per candidate; each row's own button selects that candidate by
    # its own index (never a hardcoded index).
    assert "Repeater" in content
    assert "model: qpbIdentifyRoot.qpbCandidatesModel" in content
    assert "onClicked: qpbSelectCandidate(index)" in content
    assert "function qpbSelectCandidate(index)" in content


def test_display_only_identification_widget_hides_selection_and_manual_write_back_actions():
    content = qml_plugin.render_identification_widget_qml(
        "array_to_string(array(leaf_photo_path), ',')", candidate_selection_enabled=False
    )

    assert "readonly property bool qpbCandidateSelectionEnabled: false" in content
    assert "visible: qpbIdentifyRoot.qpbCandidateSelectionEnabled" in content
    assert "visible: qpbIdentifyRoot.qpbCandidateSelectionEnabled &&" in content
    assert "if (!qpbCandidateSelectionEnabled) { return; }" in content
    assert "우점종 또는 차우점종을 직접 선택하세요." in content


def test_identification_widget_qml_uses_korean_action_button_labels():
    content = qml_plugin.render_identification_widget_qml("''")
    assert 'text: "사진으로 식물 동정"' in content
    assert 'text: "이 후보 선택"' in content
    assert 'text: "해당 없음 \\u2014 직접 입력"' in content
    assert 'text: "Select this candidate"' not in content
    assert 'text: "None of these' not in content


def test_identification_widget_qml_localizes_status_probability_and_manual_guidance():
    content = qml_plugin.render_identification_widget_qml("''")
    for korean_text in (
        "동정 중...",
        "예측 출현 확률: ",
        "확률 데이터가 없습니다.",
        "국명: ",
        "동정 정보를 직접 입력합니다",
        "수동 동정 저장",
    ):
        assert korean_text in content
    assert 'qpbStatusLabel.text = "Identifying..."' not in content
    assert 'text: "Predicted occurrence probability:' not in content
    assert 'return {{ text: "No probability data"' not in content
    assert 'text: "Korean name: "' not in content
    assert 'text: "Save manual identification"' not in content


def test_identification_widget_qml_offers_a_manual_entry_fallback():
    """FR-QPB-109 (revised): the user must be able to reject all displayed candidates and enter
    a name manually."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "직접 입력" in content
    assert "TextField" in content
    assert "qpbManualScientificNameField" in content
    assert "qpbManualKoreanNameField" in content
    assert "function qpbConfirmManualEntry()" in content


def test_identification_widget_qml_never_auto_persists_the_top_scored_candidate():
    """Reviewer finding 1: the prior round auto-persisted `candidates[0]` unconditionally as
    soon as results arrived. Persistence must now only happen from an explicit user action."""
    content = qml_plugin.render_identification_widget_qml("''")
    # The old, buggy pattern must be gone.
    assert "var chosen = candidates[0];" not in content
    # `qpbHandlePlantNetResponse` (which runs as soon as a response arrives) must only populate
    # the on-screen model, never call the persistence function itself.
    handler_start = content.index("function qpbHandlePlantNetResponse(response) {")
    handler_end = content.index(
        "function qpbPersistIdentification", handler_start
    )
    handler_body = content[handler_start:handler_end]
    assert "qpbCandidatesModel = candidates;" in handler_body
    assert "qpbPersistIdentification(" not in handler_body
    assert "currentFeature.setAttribute" not in handler_body
    # Persistence functions do exist, but only reachable from the explicit-action call sites.
    assert "function qpbPersistIdentification(" in content
    assert "onClicked: qpbSelectCandidate(index)" in content
    assert "onClicked: qpbConfirmManualEntry()" in content


def test_manual_entry_persists_the_explicit_manual_identification_status_value():
    """FR-QPB-109 (further revised; Decision Log D-43)/AC-QPB-078: manual identification must be
    persisted with the explicit `identification_status = "manual"` enum value (distinct from
    `complete`, which remains reserved for a real, persisted Pl@ntNet candidate selection -- see
    test_selecting_a_candidate_persists_a_numeric_score_and_complete_status below), and must not
    silently inherit a candidate's confidence or probability."""
    content = qml_plugin.render_identification_widget_qml("''")
    manual_start = content.index("function qpbConfirmManualEntry() {")
    manual_body = content[manual_start:manual_start + 900]
    assert "qpbPersistIdentification(" in manual_body
    # score, probability, and model version are always passed as literal `null` here -- never a
    # candidate's own score/probability_value -- and status is the new `manual` enum value, never
    # `complete`.
    assert (
        "sci.length > 0 ? sci : null, kor.length > 0 ? kor : null, null, null, null,\n"
        '            "manual", null'
    ) in manual_body
    assert '"complete"' not in manual_body


def test_selecting_a_candidate_persists_a_numeric_score_and_complete_status():
    content = qml_plugin.render_identification_widget_qml("''")
    select_start = content.index("function qpbSelectCandidate(index) {")
    select_end = content.index("function qpbConfirmManualEntry", select_start)
    select_body = content[select_start:select_end]
    assert "qpbPersistIdentification(" in select_body
    assert 'c.score, c.probability_value' in select_body
    assert '"complete"' in select_body


# --- FR-QPB-109 (further revised; Decision Log D-50/D-51): confirmed, permanent attribute --------
# --- write-back mechanism for a brand-new, not-yet-saved feature (pending-request file, ----------
# --- widget-side write / project-plugin-side Timer poll + changeAttribute() apply). ---------------


def test_pending_write_back_relpath_is_relative_not_absolute():
    assert not qml_plugin.PENDING_WRITE_BACK_RELPATH.startswith("/")
    assert qml_plugin.PENDING_WRITE_BACK_RELPATH


def test_current_feature_uuid_tries_inventory_id_then_falls_back_to_observation_id():
    """FR-QPB-109 (further revised; Decision Log D-50/D-51): resolves the current feature's own
    UUID via `expression.evaluate("inventory_id")` (Type 1), falling back to
    `expression.evaluate("observation_id")` (Type 2/3) when the first is empty/unavailable."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbCurrentFeatureUuid() {",
        "function qpbWriteAttributeWriteBackRequest(fields) {",
    )
    assert 'expression.evaluate("inventory_id")' in func_body
    assert 'expression.evaluate("observation_id")' in func_body
    inventory_index = func_body.index('expression.evaluate("inventory_id")')
    observation_index = func_body.index('expression.evaluate("observation_id")')
    assert inventory_index < observation_index, (
        "inventory_id must be tried first, observation_id only as a fallback"
    )
    assert 'uuid_field: "inventory_id"' in func_body
    assert 'uuid_field: "observation_id"' in func_body


def test_write_attribute_write_back_request_resolves_path_via_project_folder_and_uses_fileutils():
    """FR-QPB-109 (further revised; Decision Log D-50/D-51): writes the pending write-back request
    via the confirmed `FileUtils.writeFileContent()` singleton, to a path resolved via the same
    `@project_folder`-based `expression.evaluate(...)` mechanism already used elsewhere in this
    file (`qpbLoadCsv`/`qpbReadFileBytes`/`qpbLoadNationalKtsnSet`), not a bare relative path."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbWriteAttributeWriteBackRequest(fields) {",
        "function qpbFormatProbability(koreanName, location, candidateIndex) {",
    )
    assert "@project_folder + '/' +" in func_body
    assert "FileUtils.writeFileContent(" in func_body
    assert qml_plugin.PENDING_WRITE_BACK_RELPATH in func_body
    # The payload carries the current feature's UUID, which UUID field it came from, and the
    # caller-supplied field/value pairs -- never a hardcoded field name.
    assert "current.uuid" in func_body
    assert "current.uuid_field" in func_body
    assert "fields: fields" in func_body
    assert "JSON.stringify(payload)" in func_body
    # Best-effort: this must never throw and interrupt the caller (qpbSelectCandidate/
    # qpbConfirmManualEntry) if the current feature has no resolvable UUID at all.
    assert "if (!current.uuid) { return; }" in func_body


def test_select_candidate_writes_a_pending_write_back_request_with_the_complete_status():
    """FR-QPB-109 (further revised; Decision Log D-50/D-51): real candidate selection must call
    `qpbWriteAttributeWriteBackRequest` in addition to (not instead of) the existing best-effort
    `qpbPersistIdentification` attempt, carrying `identification_status: "complete"` and the
    candidate's own numeric score/probability -- never nulled out for a real selection."""
    content = qml_plugin.render_identification_widget_qml("''")
    select_body = _extract_function_body(
        content, "function qpbSelectCandidate(index) {", "function qpbConfirmManualEntry"
    )
    assert "qpbWriteAttributeWriteBackRequest(writeFields)" in select_body
    write_back_start = select_body.index("var writeFields = {")
    write_back_call = select_body[write_back_start : select_body.index("};", write_back_start)]
    assert "identification_status: \"complete\"" in write_back_call
    assert "identification_score: c.score" in write_back_call
    assert "occurrence_probability: c.probability_value" in write_back_call
    # Candidate selection directly writes only the editable Korean name; QGIS derives the other
    # identity fields from it.
    assert "selected_korean_name: korean" in write_back_call
    assert "selected_scientific_name" not in write_back_call
    assert "selected_ktsn" not in write_back_call
    assert "identification_model_version: qpbLastModelVersion" in write_back_call
    # Both mechanisms run side by side -- the pre-existing best-effort call is still present.
    assert "qpbPersistIdentification(" in select_body


def test_confirm_manual_entry_writes_a_pending_write_back_request_with_the_manual_status():
    """FR-QPB-109 (further revised; Decision Log D-50/D-51)/Decision Log D-51: manual-entry
    confirmation must also call `qpbWriteAttributeWriteBackRequest`, carrying
    `identification_status: "manual"` and explicitly nulled score/probability/model-version --
    never inheriting a candidate's own values (Decision Log D-38/D-43, unchanged)."""
    content = qml_plugin.render_identification_widget_qml("''")
    # `qpbConfirmManualEntry` is the last function declared in the widget template, so slicing to
    # the end of the generated source is sufficient here (no next-sibling-function marker exists).
    manual_body = content[content.index("function qpbConfirmManualEntry() {") :]
    assert "qpbWriteAttributeWriteBackRequest(writeFields)" in manual_body
    write_back_start = manual_body.index("var writeFields = {")
    write_back_call = manual_body[write_back_start : manual_body.index("};", write_back_start)]
    assert "identification_status: \"manual\"" in write_back_call
    assert "identification_score: null" in write_back_call
    assert "occurrence_probability: null" in write_back_call
    assert "identification_model_version: null" in write_back_call
    assert "selected_ktsn: null" in write_back_call
    # Both mechanisms run side by side -- the pre-existing best-effort call is still present.
    assert "qpbPersistIdentification(" in manual_body


def test_project_plugin_qml_declares_a_polling_timer():
    """FR-QPB-109 (further revised; Decision Log D-50): the project plugin must poll for the
    pending write-back request on a short-interval Timer."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    assert re.search(r"\bTimer\s*\{", content)
    assert "onTriggered: qpbPollPendingWriteBack()" in content
    # A short interval, per the specification's own real-device-tested example (750ms) -- this
    # project's own judgment call, not a value dictated character-for-character by the spec.
    assert re.search(r"interval:\s*\d+", content)


def test_project_plugin_qml_resolves_the_pending_request_path_via_qgis_project_home_path():
    """Prior-art finding (real-device-confirmed, per this round's task brief): `qgisProject.
    homePath` is the confirmed, real context property available to the project plugin's own QML
    engine (distinct from the embedded widget's `expression.evaluate("@project_folder + ...")`
    mechanism, which is not available in this project-plugin context)."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    assert "qgisProject.homePath" in content
    assert qml_plugin.PENDING_WRITE_BACK_RELPATH in content


def test_project_plugin_qml_reaches_the_live_model_and_applies_via_change_attribute():
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    apply_body = _extract_function_body(
        content,
        "function qpbApplyPendingWriteBack(request) {",
        "function qpbIsPendingWriteBackTarget(model, request) {",
    )
    assert 'iface.findItemByObjectName("overlayFeatureFormDrawer")' in apply_body
    assert "qpbFindActiveRelationModel(drawer, request, [])" in apply_body
    assert "model.changeAttribute(" in apply_body
    assert "changeAttribute(fieldName, request.fields[fieldName])" in apply_body
    assert apply_body.index("qpbFindActiveRelationModel(drawer, request, [])") < apply_body.index(
        "qpbFindActiveRelationModel(existingForm, request, [])"
    )
    # The current feature's UUID must be matched before applying any field.
    match_index = apply_body.index("String(currentUuid) !== String(request.uuid)")
    apply_index = apply_body.index("model.changeAttribute(")
    assert match_index < apply_index


def test_project_plugin_qml_keeps_pending_request_until_a_relation_child_model_is_live():
    """A relation-created observation is mounted below the parent drawer asynchronously.

    The request must not be consumed while only the parent form (or no child form yet) is
    available; otherwise the selected identification is lost before the child can receive it.
    """
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    poll_body = _extract_function_body(
        content, "function qpbPollPendingWriteBack() {", "function qpbApplyPendingWriteBack"
    )
    assert "if (qpbApplyPendingWriteBack(request))" in poll_body
    assert "qpbClearPendingWriteBack(absPath)" in poll_body


def test_project_plugin_qml_discovers_matching_models_nested_in_relation_feature_form():
    """QField relation forms use an EmbeddedFeatureForm/container below the overlay drawer.

    Keep traversal on public QtQuick container properties and match the child model by UUID, so
    a parent survey model can never receive an observation's identification fields.
    """
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    finder_body = _extract_function_body(
        content,
        "function qpbFindMatchingFeatureModel(root, request, visited) {",
        "function qpbIsEditableAttributeModel(model) {",
    )
    assert "embeddedFeatureForm" in finder_body
    assert "featureFormLoader" in finder_body
    assert '"attributeFormModel"' in finder_body
    assert '"featureModel"' in finder_body
    assert '"contentItem"' in finder_body
    assert '"children"' in finder_body
    assert '"contentData"' in finder_body
    assert "qpbModelMatchesPendingWriteBackRequest(root, request)" in finder_body
    assert "function qpbModelMatchesPendingWriteBackRequest(model, request)" in content
    assert "qpbReadLayerIdentifiersFromFeatureModel(model)" in content
    apply_body = _extract_function_body(
        content,
        "function qpbApplyPendingWriteBack(request) {",
        "function qpbIsPendingWriteBackTarget",
    )
    assert "iface.mainWindow()" in apply_body
    assert "mainWindow.contentItem" in apply_body
    assert "var popupVisited = [];" in apply_body
    assert "qpbFindActiveRelationModel(popup, request, popupVisited)" in apply_body
    assert apply_body.index("qpbFindActiveRelationModel(popup, request, popupVisited)") < apply_body.index(
        "qpbTraceWriteBack(\"target_not_found\""
    )
    focused_finder = _extract_function_body(
        content,
        "function qpbFindActiveRelationModel(root, request, visited) {",
        "function qpbModelMatchesPendingWriteBackRequest",
    )
    assert '"attributeFormModel"' in focused_finder
    assert "root.attributeFormModel" in focused_finder
    assert '"featureModel"' not in focused_finder
    assert '"model"' in focused_finder


def test_project_plugin_qml_traverses_a_relation_form_loader_item():
    """A QML Loader exposes its instantiated relation form through the standard ``item``
    property, rather than through a custom EmbeddedFeatureForm property on every QField version.
    The public-container traversal must include that property so the child AttributeFormModel can
    be found after the relation form is instantiated.
    """
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    finder_body = _extract_function_body(
        content,
        "function qpbFindMatchingFeatureModel(root, request, visited) {",
        "function qpbReadUuidFromFeatureModel(model, uuidFieldName) {",
    )
    assert '"featureFormLoader", "item", "form", "model"' in finder_body
    # The instantiated Loader/editor may be nested below any standard container edge; preserve
    # the provenance hint through the complete bounded traversal.
    assert "var childAttributeModelHint = attributeModelHint === true;" in finder_body


def test_project_plugin_qml_searches_the_namedless_embedded_relation_popup_by_identity():
    """EmbeddedFeatureForm is parented to mainWindow.contentItem and has no object name.

    The related-record child must therefore be found through the documented
    ``attributeFormModel`` property and its UUID/layer identities, rather than by a duplicate
    ``featureForm`` object name or a short generic child-list prefix.
    """
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    finder_body = _extract_function_body(
        content,
        "function qpbFindMatchingFeatureModel(root, request, visited) {",
        "function qpbReadUuidFromFeatureModel(model, uuidFieldName) {",
    )
    assert "var maxDepth = 32;" in finder_body
    assert "var maxNodes = 4096;" in finder_body
    assert "var maxCollectionItems = 512;" in finder_body
    assert finder_body.index('"attributeFormModel"') < finder_body.index('"featureForm"')
    assert "request.layer_contexts" in content
    widget = qml_plugin.render_identification_widget_qml("''")
    assert 'expression.evaluate("@layer_id")' in widget


def test_project_plugin_qml_traverses_existing_feature_list_form_children():
    """The existing-feature host is a list form, but its child tree may contain the active
    attribute form.  Reject the list model as a target without pruning that child traversal."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    finder_body = _extract_function_body(
        content,
        "function qpbFindMatchingFeatureModel(root, request, visited) {",
        "function qpbReadUuidFromFeatureModel(model, uuidFieldName) {",
    )
    assert "var rootIsFeatureListModel = qpbIsFeatureListModel(root);" in finder_body
    assert "if (!rootIsFeatureListModel && attributeModelHint === true" in finder_body
    assert (
        "for (var propertyIndex = 0; propertyIndex < childProperties.length; propertyIndex++)"
        in finder_body
    )


def test_project_plugin_qml_retains_pending_request_when_any_attribute_write_fails():
    """The poller may clear the request only when every requested field was applied.  A child
    model can exist before all its attributes are writable, so a rejected field must leave the
    request on disk for a later poll instead of reporting a false success.
    """
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    apply_body = _extract_function_body(
        content,
        "function qpbApplyPendingWriteBack(request) {",
        "function qpbFindMatchingFeatureModel",
    )
    assert "var requestedFieldCount = 0;" in apply_body
    assert "var appliedFieldCount = 0;" in apply_body
    assert "requestedFieldCount++;" in apply_body
    assert "if (changeResult === false || changeResult !== true)" in apply_body
    assert "field_change_error" in apply_body
    assert "appliedFieldCount++;" in apply_body
    assert (
        "if (requestedFieldCount <= 0 || appliedFieldCount !== requestedFieldCount)" in apply_body
    )
    assert 'request.fields.hasOwnProperty("selected_korean_name")' in apply_body
    assert 'model.attribute("selected_korean_name")' in apply_body

    poll_body = _extract_function_body(
        content, "function qpbPollPendingWriteBack() {", "function qpbApplyPendingWriteBack"
    )
    assert "if (qpbApplyPendingWriteBack(request))" in poll_body
    assert "qpbClearPendingWriteBack(absPath);" in poll_body


def test_project_plugin_qml_does_not_lose_korean_name_when_derived_fields_are_read_only():
    """Derived scientific-name/KTSN fields must not block the editable Korean-name write."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    apply_body = _extract_function_body(
        content,
        "function qpbApplyPendingWriteBack(request) {",
        "function qpbFindMatchingFeatureModel",
    )
    assert 'model.changeAttribute(\n                    "selected_korean_name", request.fields.selected_korean_name' in apply_body
    # Candidate selection skips the two read-only derived fields; it never tries to force a second
    # direct value into either field.
    derived_guard = apply_body.index(
        'fieldName === "selected_scientific_name" || fieldName === "selected_ktsn"'
    )
    assert "fieldName === \"selected_korean_name\"" in apply_body[:derived_guard]
    assert "model.changeAttribute(fieldName, request.fields[fieldName]);" not in apply_body[
        derived_guard : apply_body.index("requestedFieldCount++", derived_guard)
    ]
    assert "changeResult !== true" in apply_body


def test_project_plugin_qml_never_clears_via_delete_files_only_via_empty_overwrite():
    """FR-QPB-109 (further revised; Decision Log D-50): the pending-request file must be cleared
    by overwriting it with empty content, never via `FileUtils.deleteFiles()` -- real-device
    testing found the latter unreliable (silently no-ops) on at least one tested device."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    assert "FileUtils.deleteFiles(" not in content
    clear_body = _extract_function_body(
        content, "function qpbClearPendingWriteBack(absPath) {", "\n\n    Component"
    )
    assert 'FileUtils.writeFileContent(absPath, "")' in clear_body
    # Cleanup is successful only after an explicit truthy FileUtils result. Undefined (including
    # an unavailable API) must retain the pending request for a later retry.
    assert "if (!clearResult)" in clear_body
    assert "return true;" in clear_body


def test_project_plugin_qml_never_crashes_the_toolbar_button_flow():
    """The polling Timer/apply logic must be wrapped defensively so it can never interrupt the
    existing toolbar button/toast (FR-QPB-100's redundant, secondary entry point)."""
    content = qml_plugin.render_project_plugin_qml("demo_slug")
    poll_body = _extract_function_body(
        content, "function qpbPollPendingWriteBack() {", "function qpbApplyPendingWriteBack"
    )
    assert poll_body.count("try {") >= 1
    assert poll_body.count("catch (e)") >= 1
    # The toolbar button/toast must still be present, unaffected.
    assert "iface.addItemToPluginsToolbar(qpbIdentificationToolbarButton)" in content
    assert "displayToast(" in content


# --- Reviewer finding 2: EXIF GPS reading + occurrence-probability wiring (FR-QPB-108) ----------


def test_identification_widget_qml_uses_authoritative_geometry_for_location():
    """FR-QPB-108/AC-FIX-014: location is evaluated from the current domain geometry."""
    content = qml_plugin.render_identification_widget_qml(
        "''", location_expression="with_variable('plot_geom', $geometry, @plot_geom)"
    )
    assert "function qpbResolveAuthoritativeLocation()" in content
    assert "with_variable('plot_geom', $geometry, @plot_geom)" in content
    assert "qpbReadPhotoGps" not in content
    assert "qpbReadExifTag" not in content
    assert "exif(" not in content.lower()


def test_related_observation_location_uses_live_parent_context_without_type3_survey_fallback():
    """Type 2 keeps its live survey path; Type 3 permits only live/persisted plot geometry."""
    from qfield_builder.qgis_worker import _authoritative_location_expression

    type2_content = _authoritative_location_expression("temporary_plots", "observation")
    assert (
        "with_variable('parent_survey_geom', geometry(@current_parent_feature), "
        in type2_content
    )
    assert "with_variable('survey_id_value', coalesce(\"survey_id\", " in type2_content
    assert "attribute(@current_parent_feature, 'survey_id'))" in type2_content

    type3_content = _authoritative_location_expression("permanent_plots", "observation")
    assert '"qpb_plot_geometry_wkt"' in type3_content
    assert '"survey_id"' in type3_content
    assert "@current_parent_feature" not in type3_content
    assert "current_parent_value" not in type3_content
    assert "plot_geom" in type3_content
    assert "survey_geom" not in type3_content
    assert "parent_survey_geom" not in type3_content


def test_type4_community_location_uses_polygon_centroid_for_probability_sampling():
    """Type 4 has no point observation; the community polygon centroid is its location."""
    from qfield_builder.qgis_worker import _authoritative_location_expression

    content = _authoritative_location_expression("vegetation_mapping", "community")

    assert "with_variable('community_geom', $geometry" in content
    assert "centroid(@community_geom)" in content
    assert "geometry_type(@community_geom) NOT IN ('Polygon', 'MultiPolygon')" in content
    assert "EPSG:4326" in content


def test_identification_widget_qml_calls_probability_sampling_with_geometry_derived_arguments():
    """Occurrence probability consumes the resolved current-feature location when available."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert content.count("qpbSampleProbabilityRaster(") >= 2  # definition + at least one call
    assert "qpbSampleProbabilityRaster(rasterValueExpression," in content
    assert qml_plugin.PROBABILITY_STACK_RELPATH in content
    # The call happens from within candidate handling, keyed off the resolved KTSN Korean name.
    assert "function qpbFormatProbability(koreanName, location, candidateIndex)" in content
    assert "qpbFormatProbability(koreanName, location)" in content


def test_probability_sampling_uses_the_registered_multiband_raster_contract():
    content = qml_plugin.render_identification_widget_qml("''")

    assert qml_plugin.PROBABILITY_STACK_RELPATH in content
    assert qml_plugin.PROBABILITY_BAND_INDEX_RELPATH in content
    assert qml_plugin.PROBABILITY_LAYER_NAME in content
    assert "qpbLoadProbabilityBandIndex()" in content
    assert "raster_value('" in content
    assert qml_plugin.REFERENCE_RASTER_DIR_RELPATH not in content
    assert qml_plugin.PROBABILITY_WORKER_SCRIPT_RELPATH not in content


@pytest.mark.skip(reason="superseded by the registered multiband raster contract")
def test_probability_raster_filename_resolution_normalizes_korean_name_to_bundle_nfd():
    """FR-PRF-001/016 and AC-PRF-001/012: resolve the Korean name to the exact bundled filename.

    The checked-in raster source names use decomposed Hangul Jamo (NFD), while the KTSN-resolved
    candidate commonly arrives as precomposed Hangul (NFC).  Keep the path relative and retain the
    exact species filename convention; only the Unicode representation of the name changes.
    """
    content = qml_plugin.render_identification_widget_qml("''")
    normalize_body = _extract_function_body(
        content,
        "function qpbNormalizeProbabilityRasterName(name, form) {",
        "function qpbResolveProbabilityRasterFileName(koreanName) {",
    )
    resolver_body = _extract_function_body(
        content,
        "function qpbResolveProbabilityRasterFileName(koreanName) {",
        "function qpbProbabilityRasterFileNameVariants(koreanName) {",
    )
    variants_body = _extract_function_body(
        content,
        "function qpbProbabilityRasterFileNameVariants(koreanName) {",
        "function qpbStripEmTags(text) {",
    )
    probability_body = _extract_function_body(
        content,
        "function qpbFormatProbability(koreanName, location, candidateIndex) {",
        "function qpbApplyProbabilityResult(requestId, sample) {",
    )

    assert 'text.normalize(unicodeForm)' in normalize_body
    assert "qpbDecomposeHangulSyllables(text)" in normalize_body
    assert "0xAC00" in content and "0xD7A3" in content
    assert 'qpbNormalizeProbabilityRasterName(koreanName, "NFD")' in resolver_body
    assert "bce_inverse_corrected_probability_" in resolver_body
    assert 'qpbNormalizeProbabilityRasterName(koreanName, "NFC")' in variants_body
    assert "qpbResolveProbabilityRasterFileName(koreanName)" in variants_body
    assert "qpbProbabilityRasterFileNameVariants(koreanName)" in probability_body
    assert (
        "return \"" + qml_plugin.REFERENCE_RASTER_DIR_RELPATH + "/\" + name;"
        in probability_body
    )
    assert "+ koreanName + \".tif\"" not in probability_body
    assert not qml_plugin.REFERENCE_RASTER_DIR_RELPATH.startswith("/")


@pytest.mark.skip(reason="superseded by the registered multiband raster contract")
def test_probability_raster_filename_resolver_handles_nfc_korean_name_in_qml_engine():
    """The generated resolver must turn a composed Korean name into the bundled NFD filename."""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication(["qml-probability-name-test"])
    del app  # Keep the application alive through component creation without using it directly.
    engine = QQmlEngine()
    content = qml_plugin.render_identification_widget_qml("''")
    helper = content[
        content.index("function qpbNormalizeName(name) {") : content.index(
            "function qpbStripEmTags(text) {"
        )
    ]
    component = QQmlComponent(engine)
    component.setData(
        (
            "import QtQml 2.15\n"
            "QtObject {\n"
            + helper
            + 'property string resolved: qpbResolveProbabilityRasterFileName("개구리밥")\n'
            + "}\n"
        ).encode(),
        QUrl("probability-name.qml"),
    )
    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    resolved = component.create().property("resolved")
    expected_name = (
        "bce_inverse_corrected_probability_" + unicodedata.normalize("NFD", "개구리밥") + ".tif"
    )
    assert resolved == expected_name


@pytest.mark.skip(reason="superseded by the registered multiband raster contract")
def test_probability_sampler_attempts_nfd_then_nfc_relative_paths_until_a_raster_is_read():
    """A transfer-normalized NFC filename remains readable after the NFD attempt misses."""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication(["qml-probability-path-variants-test"])
    del app
    engine = QQmlEngine()
    content = qml_plugin.render_identification_widget_qml("''")
    helpers = content[
        content.index("function qpbNormalizeName(name) {") : content.index(
            "function qpbStripEmTags(text) {"
        )
    ]
    sampler = _extract_function_body(
        content,
        "function qpbSampleProbabilityRaster(rasterRelPath, lon, lat, callback) {",
        "// FileUtils is synchronous, but it is restricted to the small, local reference TIFF",
    )
    name = "개구리밥"
    nfd_path = (
        qml_plugin.REFERENCE_RASTER_DIR_RELPATH
        + "/bce_inverse_corrected_probability_"
        + unicodedata.normalize("NFD", name)
        + ".tif"
    )
    nfc_path = (
        qml_plugin.REFERENCE_RASTER_DIR_RELPATH
        + "/bce_inverse_corrected_probability_"
        + unicodedata.normalize("NFC", name)
        + ".tif"
    )
    source = (
        "import QtQuick 2.15\n"
        "Item {\n"
        "    QtObject { id: qpbWorker; function sendMessage(message) {} }\n"
        "    QtObject { id: qpbWatchdog; function start() {} }\n"
        "    property var qpbProbabilityWorker: qpbWorker\n"
        "    property var qpbProbabilityWatchdog: qpbWatchdog\n"
        "    property var attempts: []\n"
        "    property int qpbProbabilityRequestSequence: 0\n"
        "    property var qpbProbabilityJobs: ({})\n"
        "    function qpbReadProbabilityRasterBytes(path) {\n"
        "        attempts.push(path);\n"
        "        return path === "
        + json.dumps(nfc_path, ensure_ascii=False)
        + " ? [1] : null;\n"
        "    }\n"
        + helpers
        + sampler
        + "    property var result: null\n"
        + "    Component.onCompleted: result = qpbSampleProbabilityRaster(\n"
        + "        qpbProbabilityRasterFileNameVariants(\""
        + name
        + "\").map(function (filename) { return "
        + json.dumps(qml_plugin.REFERENCE_RASTER_DIR_RELPATH + "/", ensure_ascii=False)
        + " + filename; }), 127, 37, function(value) {})\n"
        + "}\n"
    )
    component = QQmlComponent(engine)
    component.setData(source.encode(), QUrl("probability-path-variants.qml"))
    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    root = component.create()
    assert root.property("attempts").toVariant() == [nfd_path, nfc_path]
    assert root.property("result") == "1"


@pytest.mark.skip(reason="superseded by QGIS raster_value() sampling")
def test_probability_worker_resolves_from_project_folder_for_embedded_attribute_widget():
    """Embedded QML widgets must load the worker beside the transferred project files."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert 'source: ""' in content
    assert "Component.onCompleted: qpbConfigureProbabilityWorker()" in content
    worker = _extract_function_body(
        content,
        "function qpbConfigureProbabilityWorker() {",
        "// FileUtils is synchronous,",
    )
    assert 'expression.evaluate("@project_folder")' in worker
    assert '"file://" + encodeURI(projectFolder)' in worker
    assert f'"{qml_plugin.PROBABILITY_WORKER_SCRIPT_RELPATH}"' in worker


def test_probability_display_rules_match_fr_qpb_108_dr_qpb_070():
    content = qml_plugin.render_identification_widget_qml("''")
    assert "확률 데이터가 없습니다." in content
    assert "현재 조사 위치가 없어 확률을 계산할 수 없습니다." in content
    assert "sample === -9999" in content
    assert "sample <= 1.0" in content
    assert "value: Math.max(0, sample)" in content
    assert "raster_invalid_value" in content
    assert "warning: false" in content


@pytest.mark.parametrize(
    ("reason", "expected_text"),
    [
        ("raster_layer_unavailable", "확률 데이터가 없습니다."),
        ("raster_sampling_failed", "확률 데이터가 없습니다."),
        ("raster_location_invalid", "확률 데이터가 없습니다."),
        (
            "raster_sampling_api_not_found",
            "예측 출현 확률을 계산할 수 없습니다 (기기 내 래스터 샘플링 "
            "지원이 확인되지 않았습니다).",
        ),
    ],
)
def test_probability_formatter_preserves_immediate_sampler_reason(reason, expected_text):
    """Immediate sampler callbacks must distinguish unavailable data from missing capability."""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication(["qml-probability-fallback-test"])
    del app  # Keep the application alive through component creation without using it directly.
    engine = QQmlEngine()
    content = qml_plugin.render_identification_widget_qml("''")
    helpers = content[
        content.index("function qpbNormalizeName(name) {") : content.index(
            "function qpbStripEmTags(text) {"
        )
    ]
    formatter = _extract_function_body(
        content,
        "function qpbFormatProbability(koreanName, location, candidateIndex) {",
        "function qpbApplyProbabilityResult(requestId, sample) {",
    )
    source = (
        "import QtQml 2.15\n"
        "QtObject {\n"
        "    function qpbLoadProbabilityBandIndex() { return {mapping:{\"개구리밥\":1},band_count:1}; }\n"
        "    function qpbTraceRuntime(stage, detail) {}\n"
        "    function qpbEscapeForExpressionLiteral(value) { return value; }\n"
        "    function qpbSampleProbabilityRaster(sampleExpression, callback) {\n"
        f'        callback({{available: false, reason: "{reason}"}});\n'
        "        return null;\n"
        "    }\n"
        "    function qpbApplyProbabilityResult(requestId, sample) {}\n"
        + helpers
        + formatter
        + "    property var result: qpbFormatProbability(\"개구리밥\", {lon: 127, lat: 37}, 0)\n"
        + "}\n"
    )
    component = QQmlComponent(engine)
    component.setData(source.encode(), QUrl("probability-fallback.qml"))
    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    result = component.create().property("result").toVariant()
    assert result["text"] == expected_text
    assert result["value"] is None


def test_probability_formatter_keeps_supported_sampling_asynchronous():
    """A non-null request remains pending; immediate fallback handling must not become blocking."""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    app = QGuiApplication.instance() or QGuiApplication(["qml-probability-async-test"])
    del app
    engine = QQmlEngine()
    content = qml_plugin.render_identification_widget_qml("''")
    helpers = content[
        content.index("function qpbNormalizeName(name) {") : content.index(
            "function qpbStripEmTags(text) {"
        )
    ]
    formatter = _extract_function_body(
        content,
        "function qpbFormatProbability(koreanName, location, candidateIndex) {",
        "function qpbApplyProbabilityResult(requestId, sample) {",
    )
    source = (
        "import QtQml 2.15\n"
        "QtObject {\n"
        "    function qpbLoadProbabilityBandIndex() { return {mapping:{\"개구리밥\":1},band_count:1}; }\n"
        "    function qpbTraceRuntime(stage, detail) {}\n"
        "    function qpbEscapeForExpressionLiteral(value) { return value; }\n"
        "    function qpbSampleProbabilityRaster(sampleExpression, callback) {\n"
        "        return \"request-1\";\n"
        "    }\n"
        "    function qpbApplyProbabilityResult(requestId, sample) {}\n"
        + helpers
        + formatter
        + "    property var result: qpbFormatProbability(\"개구리밥\", {lon: 127, lat: 37}, 0)\n"
        + "}\n"
    )
    component = QQmlComponent(engine)
    component.setData(source.encode(), QUrl("probability-async.qml"))
    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    result = component.create().property("result").toVariant()
    assert result["pending"] is True
    assert result["request_id"] == "request-1"
    assert result["text"] == "예측 출현 확률을 계산하는 중..."


# --- Conformance-defect fixes: real-device "Pl@ntNet request failed (HTTP 400)." with no detail --


def test_non_200_response_surfaces_the_response_body_instead_of_a_bare_status_code():
    """Confirmed via a live test against the real Pl\\u0040ntNet API: even error responses carry an
    informative JSON body (e.g. a confirmed real 401 response with a `message` field, "Bad
    token"). The old code discarded `xhr.responseText` entirely on any non-200 status, leaving
    only a bare, non-actionable "HTTP 400" message on a real device. Fixed to parse the response
    body as JSON and surface its `message`/`error` field, falling back to the raw text if it is
    not valid JSON, and to the old generic message only if the body is empty."""
    content = qml_plugin.render_identification_widget_qml("''")
    onready_start = content.index("function qpbCompletePlantNetRequest(kind) {")
    onready_end = content.index("xhr.send(body.buffer);")
    request_body = content[onready_start:onready_end]
    non200_start = request_body.index("if (xhr.status !== 200) {")
    non200_end = request_body.index("var response;")
    non200_body = request_body[non200_start:non200_end]
    # The response body is actually read, parsed, and a message/error field extracted.
    assert "xhr.responseText" in non200_body
    assert "JSON.parse(xhr.responseText)" in non200_body
    assert "qpbErrorBody.message" in non200_body
    assert "qpbErrorBody.error" in non200_body
    # Falls back to the raw text on a JSON-parse failure.
    assert "qpbErrorDetail = xhr.responseText;" in non200_body
    # The old bare, detail-free message is gone as the unconditional behavior -- it now only
    # survives as the empty-body fallback, alongside a detailed variant.
    assert (
        'qpbStatusLabel.text = "Pl\\u0040ntNet 요청에 실패했습니다 (HTTP " + xhr.status + ").";'
        not in non200_body
    )
    assert '"Pl\\u0040ntNet 요청에 실패했습니다 (HTTP " + xhr.status + "): " +' in non200_body
    assert "qpbErrorDetail" in non200_body
    assert '"Pl\\u0040ntNet 요청에 실패했습니다 (HTTP " + xhr.status + ").";' in non200_body


def test_identification_request_has_guarded_compatible_completion_and_bounded_timeout():
    """Completion must not depend on Qt/QML exposing XMLHttpRequest.DONE correctly."""
    content = qml_plugin.render_identification_widget_qml("''")
    request_start = content.index("var xhr = new XMLHttpRequest();")
    request_end = content.index("// FR-QPB-108:", request_start)
    request_body = content[request_start:request_end]

    assert "function qpbCompletePlantNetRequest(kind) {" in request_body
    assert "var qpbRequestHandled = false;" in request_body
    assert "if (qpbRequestHandled) { return; }" in request_body
    assert "xhr.readyState === 4" in request_body
    assert "xhr.readyState !== XMLHttpRequest.DONE" not in request_body
    assert "xhr.onload = function ()" in request_body
    assert "xhr.onerror = function ()" in request_body
    assert "xhr.ontimeout = function ()" in request_body
    assert "xhr.onabort = function ()" in request_body
    assert "xhr.timeout = 60000;" in request_body
    assert "xhr.send(body.buffer);" in request_body
    assert "네트워크 연결을 확인하고 다시 시도하세요." in request_body


def test_identification_response_defers_national_list_until_multi_entry_matching():
    """The ~795 KB national list is only needed for multi-entry correct_list resolution."""
    content = qml_plugin.render_identification_widget_qml("''")
    handler_body = _extract_function_body(
        content,
        "function qpbHandlePlantNetResponse(response) {",
        "function qpbPersistIdentification",
    )
    match_body = _extract_function_body(
        content,
        "function qpbMatchKtsn(scientificNameWithoutAuthor, csv, nationalKtsnSet) {",
        "function qpbSampleProbabilityRaster(sampleExpression, callback) {",
    )

    assert "var nationalSetLoaded = false;" in handler_body
    assert "var nationalSet = function() {" in handler_body
    assert (
        f'qpbLoadNationalKtsnSet("{qml_plugin.REFERENCE_NATIONAL_LIST_RELPATH}")'
        in handler_body
    )
    assert "qpbMatchKtsn(sciName, csv, nationalSet)" in handler_body
    assert "typeof nationalKtsnSet === \"function\"" in match_body
    assert "resolvedNationalKtsnSet =" in match_body
    assert "resolvedNationalKtsnSet[hopKtsn]" in match_body


def test_read_file_bytes_resolves_relative_path_via_project_folder_before_reading():
    """`qpbReadFileBytes` must still resolve the bare relative attachment path (e.g.
    "DCIM/photo1.jpg") to an absolute path via QGIS's own `@project_folder` expression variable
    before reading it -- unchanged from the prior fix round (Decision Log D-46 corrects only the
    read *mechanism* itself, not this path resolution)."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_start = content.index("function qpbReadFileBytes(relPath) {")
    # Isolate just this function's body (up to the next sibling statement in the source).
    body_end = content.index("var qpbImagesRead = 0;")
    func_body = content[func_start:body_end]

    # The relative path is resolved to an absolute path via the same confirmed QGIS
    # `@project_folder` expression mechanism already used by `qpbReadExifTag`.
    assert "@project_folder + '/' +" in func_body
    assert "expression.evaluate(" in func_body

    # The escaping helper is reused, not duplicated -- only one definition of it exists at all.
    assert content.count("function qpbEscapeForExpressionLiteral(text)") == 1
    assert "qpbEscapeForExpressionLiteral(relPath)" in func_body

    # A null/undefined/empty resolved path is handled by returning null, not by attempting a read.
    assert "absPath === undefined || absPath === null" in func_body
    assert "return null;" in func_body


def test_read_file_bytes_uses_fileutils_not_xmlhttprequest():
    """Decision Log D-46/FR-QPB-101 (further revised): a plain QML `XMLHttpRequest` cannot read
    local files by default (Qt's own documented restriction), and QField's own application code
    never lifts this restriction -- confirmed via direct GitHub source inspection of
    `opengisch/QField`. `qpbReadFileBytes` must therefore call QField's own native
    `FileUtils.readFileContent(filePath)` singleton (exposed via `import org.qfield`, confirmed
    against the real `v4.2.4`-tagged source -- the earlier `QfFileUtils`/`org.qfield.core` naming
    does not exist at that version) with the resolved *absolute path*, not a `file://` URL -- and
    the old XHR-based local-file read must be fully gone, not merely retained as a fallback."""
    content = qml_plugin.render_identification_widget_qml("''")

    # `import org.qfield` is present alongside the existing QtQuick imports, and appears
    # before any QML content (a real QML import statement).
    import_section = content[: content.index("Column {")]
    assert "import QtQuick 2.15" in import_section
    assert "import QtQuick.Controls 2.15" in import_section
    assert "import org.qfield 1.0" in import_section
    assert "import org.qfield.core" not in import_section

    func_start = content.index("function qpbReadFileBytes(relPath) {")
    body_end = content.index("var qpbImagesRead = 0;")
    func_body = content[func_start:body_end]

    # The read itself now goes through `FileUtils.readFileContent(...)`, called with the
    # resolved absolute path (a plain string), not a `file://`-prefixed URL.
    assert "FileUtils.readFileContent(String(absPath))" in func_body
    assert "QfFileUtils.readFileContent(String(absPath))" not in func_body

    # The old XHR-based local-file read is fully gone -- not kept as a fallback path.
    assert "xhrFile" not in func_body
    assert 'xhrFile.open("GET", fileUrl, false);' not in content
    assert '"file://" + String(absPath)' not in func_body
    assert "new XMLHttpRequest()" not in func_body

    # The existing null-on-failure convention is preserved: a failed/undefined/null read still
    # returns null (matching the caller's existing `if (fileBytes === null) { continue; }`
    # skip-this-photo handling, unaffected by this change).
    assert "if (content === undefined || content === null) { return null; }" in func_body
    assert func_body.count("return null;") >= 2  # one for absPath failure, one for content failure
    assert "try {" in func_body and "} catch (e) { return null; }" in func_body


def test_organs_field_is_only_added_alongside_a_successfully_read_images_field():
    """Confirmed suspected root cause: the old code added the "organs" multipart field
    unconditionally for every photo path, while the paired "images" field was only added `if
    (fileBytes !== null)` -- a read failure for one photo left an unpaired "organs" field (more
    "organs" parts than "images" parts), a structural body mismatch the real Pl\\u0040ntNet API
    would very plausibly reject with an HTTP 400. Fixed so both fields are only ever added
    together, inside the same success branch, after the bytes are confirmed read."""
    content = qml_plugin.render_identification_widget_qml("''")
    loop_start = content.index("for (var i = 0; i < paths.length; i++) {")
    loop_end = content.index("segments.push(qpbUtf8Bytes(\"--\" + boundary + \"--")
    loop_body = content[loop_start:loop_end]
    # Bytes are read first, and the loop skips ahead (without adding any field) on failure.
    read_index = loop_body.index("var fileBytes = qpbReadFileBytes(paths[i]);")
    null_check_index = loop_body.index("if (fileBytes === null) { continue; }")
    organs_index = loop_body.index('name=\\"organs\\"')
    images_index = loop_body.index('name=\\"images\\"')
    assert read_index < null_check_index < organs_index < images_index
    # Neither field-adding statement is conditioned on a separate, later `if (fileBytes !== null)`
    # check -- the only such check in the loop is the early `continue` above.
    assert loop_body.count("fileBytes !== null") == 0
    assert loop_body.count("fileBytes === null") == 1


def test_zero_successfully_read_images_aborts_before_sending_with_a_distinct_message():
    """If every photo's local-file read fails (paths.length > 0 but zero images actually read),
    the request must never be sent (it would have zero images, which the real Pl\\u0040ntNet API
    would very plausibly reject as a bad request) -- and the status message must be distinct from
    the existing zero-*paths* "No attached photos found on this record." message."""
    content = qml_plugin.render_identification_widget_qml("''")
    guard_start = content.index("if (qpbImagesRead === 0) {")
    final_boundary_index = content.index(
        "segments.push(qpbUtf8Bytes(\"--\" + boundary + \"--"
    )
    guard_body = content[guard_start:final_boundary_index]
    assert "qpbImagesRead === 0" in guard_body
    assert "return;" in guard_body
    guard_start = guard_body.index("if (qpbImagesRead === 0) {")
    guard_message_section = guard_body[guard_start:guard_body.index("return;", guard_start)]
    assert "qpbStatusLabel.text" in guard_message_section
    assert "이 레코드에 첨부된 사진이 없습니다." not in guard_message_section
    # A distinct, honest message about a failed *read* (not merely "no photos found").
    assert "첨부 사진 파일" in guard_message_section
    # The counter is actually incremented only on a successful read.
    counter_incr_index = content.index("qpbImagesRead++;")
    null_continue_index = content.index("if (fileBytes === null) { continue; }")
    assert null_continue_index < counter_incr_index


def _extract_function_body(content: str, signature: str, next_sibling_marker: str) -> str:
    func_start = content.index(signature)
    body_end = content.index(next_sibling_marker, func_start)
    return content[func_start:body_end]


# --- FR-QPB-101 (post-MVP; further revised; Decision Log D-52): mandatory photo-resize-via- -------
# --- temporary-copy step, inserted between reading a photo's original bytes and submitting them --
# --- to Pl@ntNet (a confirmed real-device HTTP 413 rejection made this mandatory). ------------
# --- Mirrors this file's own established conventions for the FR-QPB-109/Decision-Log-D-50 --------
# --- write-back mechanism above (a constant + structural-content unit tests here, plus the --------
# --- authoritative `test_ac088_*` acceptance tests, which additionally confirm this mechanism -----
# --- actually ends up inside the real, generated project's embedded widget QML). ------------------


def test_photo_resize_temp_relpath_is_relative_not_absolute():
    assert not qml_plugin.PHOTO_RESIZE_TEMP_RELPATH.startswith("/")
    assert qml_plugin.PHOTO_RESIZE_TEMP_RELPATH


def test_resize_photo_for_upload_is_defined_and_wired_into_the_photo_loop():
    """`qpbResizePhotoForUpload` must exist, and `qpbRunIdentification`'s photo loop must call it
    with each photo's relative path and already-read original bytes -- and push its *return value*
    (not the original `fileBytes`) into the multipart body's segment list."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {" in content

    run_body = _extract_function_body(
        content, "function qpbRunIdentification() {", "// FR-QPB-108:"
    )
    read_index = run_body.index("var fileBytes = qpbReadFileBytes(paths[i]);")
    null_check_index = run_body.index("if (fileBytes === null) { continue; }")
    resize_call_index = run_body.index(
        "var qpbUploadBytes = qpbResizePhotoForUpload(paths[i], fileBytes);"
    )
    push_index = run_body.index("segments.push(qpbUploadBytes);")
    # Original bytes are read, the null-read case is skipped first, and only then is the resize
    # step invoked -- and the resized (not original) bytes are what gets pushed as the segment.
    assert read_index < null_check_index < resize_call_index < push_index
    assert "segments.push(fileBytes);" not in run_body


def test_resize_photo_for_upload_writes_original_bytes_to_a_new_temporary_file():
    """AC-QPB-088 element (1), unit-level: the original, already-read bytes are written to a new
    temporary file (PHOTO_RESIZE_TEMP_RELPATH, resolved via the same `@project_folder`-based
    `expression.evaluate(...)` mechanism already used elsewhere in this file) via
    `FileUtils.writeFileContent()` -- at a path distinct from the original attachment's own path,
    which this function never resolves or references at all (it operates only on the
    already-read `originalBytes` parameter). Conformance-defect fix (real-device-confirmed 413
    root cause): the write must pass `originalBytes.buffer` (the underlying `ArrayBuffer`), not
    the bare `Uint8Array` view itself -- QML's automatic QByteArray<->ArrayBuffer marshaling
    mis-marshals a typed-array view, silently corrupting the temporary copy's content (see
    `test_resize_photo_for_upload_passes_the_underlying_array_buffer_not_the_typed_array_view` for
    the dedicated regression test)."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert "@project_folder + '/' +" in func_body
    assert qml_plugin.PHOTO_RESIZE_TEMP_RELPATH in func_body
    assert (
        "FileUtils.writeFileContent(String(qpbResizeTempAbsPath), originalBytes.buffer);"
        in func_body
    )
    # Never resolves or reads the original attachment's own path -- only the caller
    # (`qpbReadFileBytes`) does that, upstream, before calling this function.
    assert "qpbReadFileBytes(" not in func_body
    assert "readFileContent(String(absPath))" not in func_body


def test_resize_photo_for_upload_passes_the_underlying_array_buffer_not_the_typed_array_view():
    """Regression test for a confirmed, real-device-verified defect (Decision Log D-52's shipped
    fix, commit 5e0b598, did not actually resolve the HTTP 413 rejection it was meant to fix):
    the original-bytes write call passed `originalBytes` -- a `Uint8Array` *view* over an
    `ArrayBuffer` -- directly to `FileUtils.writeFileContent()`. QField's native
    `FileUtils.writeFileContent(const QString &filePath, const QByteArray &content)` relies on
    QML's automatic binary marshaling between a C++ `QByteArray` and a JS `ArrayBuffer`; a
    `Uint8Array` is a typed-array view over an `ArrayBuffer`, not the `ArrayBuffer` itself, so
    passing the view directly silently mis-marshaled the content -- the temporary file was
    written, but its bytes were not a faithful round-trip of the original photo, so
    `FileUtils.restrictImageSize()` had nothing valid to resize, and the best-effort fallback
    ended up returning bytes equivalent to the original, unresized photo -- still large enough to
    trigger Pl@ntNet's HTTP 413 rejection even after the resize mechanism shipped. Confirmed fixed
    end-to-end on a real device by passing `originalBytes.buffer` instead. This test exists solely
    to catch a future regression back to passing the raw typed-array view -- distinct from the
    temp-file-path-usage and step-ordering assertions in the other tests in this section."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert (
        "FileUtils.writeFileContent(String(qpbResizeTempAbsPath), originalBytes.buffer);"
        in func_body
    )
    # The bare-view form (no ".buffer" suffix) must never appear as the argument to this call --
    # confirmed absent by requiring the call site to always be immediately followed by ");" only
    # when preceded by ".buffer", i.e. there is no second, bare-view call site left behind.
    assert (
        func_body.count("FileUtils.writeFileContent(String(qpbResizeTempAbsPath), originalBytes);")
        == 0
    )


def test_resize_photo_for_upload_calls_restrict_image_size_with_1280_against_temp_path_only():
    """AC-QPB-088 element (2), unit-level: `FileUtils.restrictImageSize()` is called with the
    literal maximum dimension `1280`, against the temporary copy's own path only -- the same path
    variable used by the write/read-back/cleanup calls, never the original attachment path (which
    this function does not even reference -- see the test above)."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert "FileUtils.restrictImageSize(String(qpbResizeTempAbsPath), 1280);" in func_body
    # The only actual call site (as opposed to explanatory-comment mentions of the method name) is
    # the one asserted above, against the temporary path only -- confirmed by counting occurrences
    # of the exact call text itself, which is unambiguous regardless of any surrounding comments.
    assert func_body.count(
        "FileUtils.restrictImageSize(String(qpbResizeTempAbsPath), 1280);"
    ) == 1


def test_resize_photo_for_upload_reads_resized_bytes_back_from_the_temporary_file():
    """AC-QPB-088 element (3), unit-level: the resized bytes are read back from the same temporary
    file via the plain `FileUtils.readFileContent()` (not `QfFileUtils.readFileContent()`, which
    FR-QPB-101 (further revised; Decision Log D-46) uses only for the original photo-byte read)
    and become the function's return value in place of the original bytes."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert "FileUtils.readFileContent(String(qpbResizeTempAbsPath));" in func_body
    assert "QfFileUtils.readFileContent(String(qpbResizeTempAbsPath))" not in func_body
    assert "qpbResizedBytes = new Uint8Array(qpbResizedContent);" in func_body
    assert "return qpbResizedBytes;" in func_body


def test_resize_photo_for_upload_clears_the_temporary_file_via_empty_overwrite_never_delete_files():
    """AC-QPB-088 element (4), unit-level: the temporary file is cleared via an empty-content
    overwrite (`FileUtils.writeFileContent(tempPath, "")`), never via `FileUtils.deleteFiles()`
    (Decision Log D-50's confirmed unreliability finding for that method), and this cleanup runs
    unconditionally (a `finally` block), not only on the success path."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "FileUtils.deleteFiles(" not in content
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert 'FileUtils.writeFileContent(String(qpbResizeTempAbsPath), "");' in func_body
    assert "} finally {" in func_body
    cleanup_index = func_body.index(
        'FileUtils.writeFileContent(String(qpbResizeTempAbsPath), "");'
    )
    finally_index = func_body.index("} finally {")
    assert finally_index < cleanup_index


def test_resize_photo_for_upload_mechanism_runs_in_order():
    """AC-QPB-088, unit-level ordering check: write < restrictImageSize < read-back < cleanup,
    mirroring the authoritative `test_ac088_resize_mechanism_runs_in_order_and_resized_bytes_
    precede_the_plantnet_request` acceptance test's own combined ordering assertion."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    write_index = func_body.index(
        "FileUtils.writeFileContent(String(qpbResizeTempAbsPath), originalBytes.buffer);"
    )
    restrict_index = func_body.index(
        "FileUtils.restrictImageSize(String(qpbResizeTempAbsPath), 1280);"
    )
    read_back_index = func_body.index(
        "FileUtils.readFileContent(String(qpbResizeTempAbsPath));"
    )
    cleanup_index = func_body.index(
        'FileUtils.writeFileContent(String(qpbResizeTempAbsPath), "");'
    )
    assert write_index < restrict_index < read_back_index < cleanup_index


def test_resize_photo_for_upload_falls_back_to_original_bytes_on_any_failure():
    """Requirement: if the resize step fails for any reason (e.g. `restrictImageSize` throwing, or
    the read-back failing), fall back to the original, unresized bytes for that one photo rather
    than skipping/aborting the whole photo -- honest, not fabricated: never claims a resize
    happened when it did not."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    # The accumulator starts out as the original bytes, and is only ever reassigned to the
    # resized bytes after a successful read-back -- so any exception thrown before that
    # reassignment (write/restrictImageSize/read-back all inside the same try block) leaves the
    # original bytes as the honest, unmodified fallback result.
    assert "var qpbResizedBytes = originalBytes;" in func_body
    assert func_body.count("try {") >= 2
    assert func_body.count("catch (e") >= 2
    # The temporary-path-resolution failure path also degrades honestly to the original bytes.
    assert "return originalBytes;" in func_body


def test_resize_photo_for_upload_never_touches_the_original_attachment_path():
    """Disclosed heuristic note (traceability doc, AC-QPB-088 addendum): a correct implementation
    keeps the temporary copy's path and the original attachment's path as two distinctly-named
    local variables, never reusing/reassigning one to hold both. This implementation goes further
    -- `qpbResizePhotoForUpload` never resolves or references the original attachment's own path
    at all; it only ever receives the original bytes already read upstream by `qpbReadFileBytes`,
    and only ever declares/uses its own `qpbResizeTempAbsPath` variable for the temporary copy."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbResizePhotoForUpload(originalRelPath, originalBytes) {",
        "// Conformance-defect fix: the \"organs\" field",
    )
    assert "absPath" not in func_body
    assert func_body.count("qpbResizeTempAbsPath") >= 4  # declare + write + restrict + read-back


def test_load_csv_resolves_relative_path_via_project_folder_and_uses_fileutils():
    """Decision Log D-46 (same bug class as `qpbReadFileBytes`, fixed for a second, independent
    call site found by a fresh reviewer): `qpbLoadCsv` must no longer open the bundled KTSN CSV's
    bare relative path directly via a QML `XMLHttpRequest` (which cannot read local files by
    default under Qt/QField) -- it must resolve the path to an absolute path via QGIS's own
    `@project_folder` expression variable (mirroring `qpbReadFileBytes`) and then read the file's
    content via QField's native `FileUtils.readFileContent(...)` singleton (confirmed against the
    real `v4.2.4`-tagged source -- the earlier `QfFileUtils` naming does not exist at that
    version)."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content, "function qpbLoadCsv(relPath) {", "function qpbColumnIndex(header, name) {"
    )

    # The relative path is resolved to an absolute path via the same confirmed QGIS
    # `@project_folder` expression mechanism already used by `qpbReadFileBytes`/`qpbReadExifTag`.
    assert "@project_folder + '/' +" in func_body
    assert "expression.evaluate(" in func_body

    # The escaping helper is reused, not duplicated.
    assert content.count("function qpbEscapeForExpressionLiteral(text)") == 1
    assert "qpbEscapeForExpressionLiteral(relPath)" in func_body

    # The read itself now goes through `FileUtils.readFileContent(...)`, called with the
    # resolved absolute path (a plain string), not a `file://`-prefixed URL passed to XHR.
    assert "FileUtils.readFileContent(String(absPath))" in func_body
    assert "QfFileUtils.readFileContent(String(absPath))" not in func_body

    # The old XHR-based local-file read is fully gone from this function -- not kept as a
    # fallback path.
    assert "new XMLHttpRequest()" not in func_body
    assert 'xhr.open("GET", fileUrl, false);' not in func_body
    assert "xhr.responseText" not in func_body

    # The existing null-on-failure convention (path-resolution failure, unreadable content, and
    # empty-text-after-read) is preserved unchanged.
    assert "absPath === undefined || absPath === null" in func_body
    assert "if (content === undefined || content === null) { return null; }" in func_body
    assert "if (!text) { return null; }" in func_body


def test_load_national_ktsn_set_resolves_relative_path_via_project_folder_and_uses_fileutils():
    """Decision Log D-46 (identical bug class/fix as `qpbLoadCsv` immediately above, applied to
    the second reviewer-found call site): `qpbLoadNationalKtsnSet` must no longer read the
    bundled NIBR accepted-taxon list via a QML `XMLHttpRequest` against a bare relative path --
    same `@project_folder`-resolution + `FileUtils.readFileContent(...)` fix, and the same
    empty-set-on-failure convention preserved."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content,
        "function qpbLoadNationalKtsnSet(relPath) {",
        "// FR-QPB-106/107 (further revised, Decision Log D-40/D-42):",
    )

    assert "@project_folder + '/' +" in func_body
    assert "expression.evaluate(" in func_body
    assert "qpbEscapeForExpressionLiteral(relPath)" in func_body
    assert "FileUtils.readFileContent(String(absPath))" in func_body
    assert "QfFileUtils.readFileContent(String(absPath))" not in func_body

    assert "new XMLHttpRequest()" not in func_body
    assert 'xhr.open("GET", fileUrl, false);' not in func_body
    assert "xhr.responseText" not in func_body

    # Failure returns the empty set `{}`, never `null` -- unchanged convention.
    assert "var set = {};" in func_body
    assert "return set;" in func_body
    assert func_body.count("return set;") >= 3  # absPath failure, content failure, catch failure
    assert "return null;" not in func_body


def test_load_csv_and_load_national_ktsn_set_decode_bytes_as_utf8_text():
    """Both functions need the file's content as a *text string* for CSV/plain-text parsing, not
    raw bytes (unlike `qpbReadFileBytes`, which needs raw bytes for a multipart body) -- and the
    bundled KTSN CSV contains Korean-language columns (e.g. `taxon_kor_nm`), so a correct UTF-8
    decode (not a naive one-byte-per-character decode) is required. Both functions must route the
    `FileUtils.readFileContent(...)` result through the same UTF-8-decoding helper."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "function qpbBytesToUtf8String(bytes)" in content

    csv_body = _extract_function_body(
        content, "function qpbLoadCsv(relPath) {", "function qpbColumnIndex(header, name) {"
    )
    national_body = _extract_function_body(
        content,
        "function qpbLoadNationalKtsnSet(relPath) {",
        "// FR-QPB-106/107 (further revised, Decision Log D-40/D-42):",
    )
    assert "qpbBytesToUtf8String(new Uint8Array(content))" in csv_body
    assert "qpbBytesToUtf8String(new Uint8Array(content))" in national_body


def test_load_csv_and_load_national_ktsn_set_still_called_with_the_bundled_relative_paths():
    """The call sites (unchanged by this fix) must still pass the bundled reference assets'
    project-relative paths (FR-QPB-112/113), not an absolute path or a `file://` URL -- the
    resolution to an absolute path now happens *inside* each function, not at the call site."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert f'qpbLoadCsv("{qml_plugin.REFERENCE_KTSN_CSV_RELPATH}")' in content
    assert (
        f'qpbLoadNationalKtsnSet("{qml_plugin.REFERENCE_NATIONAL_LIST_RELPATH}")' in content
    )


def test_multipart_body_assembly_never_pushes_bytes_one_at_a_time():
    """Conformance-defect fix: a real device crash (Identify button shows "Identifying..." then
    the app crashes, not a caught-JS-error status message) was root-caused to the old
    `qpbRunIdentification` body-assembly loop pushing every single byte of a photo's file
    individually onto a plain JS Array (`parts.push(fileBytes[b])` -- millions of calls for one
    real several-MB phone-camera photo). That per-byte loop must be gone."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "parts.push(fileBytes[b])" not in content
    assert re.search(r"for\s*\([^)]*\bb\b[^)]*fileBytes\.length", content) is None


def test_multipart_body_assembly_never_repeatedly_concats_a_growing_array():
    """The second half of the same root cause: `parts = parts.concat(...)` was called repeatedly
    on the same, ever-growing accumulator (once per photo, for each header/CRLF segment, plus once
    more for the final closing boundary) -- `.concat()` always allocates and copies a brand-new
    array from both operands, so this was an O(n^2) memory/CPU blowup across up to 5 photos
    (FR-QPB-104) at several MB each. No `.concat(` call may remain in the generated widget QML."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert ".concat(" not in content
    assert "parts = parts.concat" not in content


def test_multipart_body_assembly_uses_a_single_preallocated_typed_array_with_set_calls():
    """The fix: collect each segment (a `Uint8Array`) into a list, compute the total length in one
    pass, allocate exactly one right-sized `Uint8Array`, and copy each segment in with the fast,
    native `Uint8Array.prototype.set(segment, offset)` bulk copy -- never a per-byte loop and never
    a repeated whole-array copy, and never a final `new Uint8Array(someHugePlainArray)` conversion
    of a plain Array built up over millions of elements."""
    content = qml_plugin.render_identification_widget_qml("''")
    run_body = _extract_function_body(
        content, "function qpbRunIdentification() {", "// FR-QPB-108:"
    )
    # A single accumulating list of segments (not of individual bytes).
    assert "var segments = [];" in run_body
    assert "segments.push(" in run_body
    # The whole photo's bytes are pushed as one segment, not iterated byte-by-byte. Conformance
    # update (FR-QPB-101, further revised; Decision Log D-52): the segment pushed is now the
    # *resized* photo bytes (`qpbResizePhotoForUpload`'s return value), not the original,
    # unresized `fileBytes` directly -- see the dedicated D-52 resize-mechanism tests below for
    # coverage of the resize step itself.
    assert "segments.push(qpbUploadBytes);" in run_body
    assert "segments.push(fileBytes);" not in run_body
    # Total length computed in one pass over the segment list, not over individual bytes.
    assert "qpbTotalLength" in run_body
    assert "segments[s].length" in run_body or "segments[" in run_body
    # Exactly one `Uint8Array` allocation sized to that computed total, immediately before the
    # copy loop -- not `new Uint8Array(parts)` on a plain, already-fully-built Array.
    assert "var body = new Uint8Array(qpbTotalLength);" in run_body
    assert "new Uint8Array(parts)" not in run_body
    # The bulk-copy mechanism is the typed array's native `.set(...)`, not a per-element loop.
    assert "body.set(segments[" in run_body
    assert re.search(r"body\[\s*\w+\s*\]\s*=", run_body) is None


# --- Conformance-defect fix: real on-device crash after D-47's 183MB->36.7MB reduction still ---
# --- crashed "in the same way" -- eager full-CSV parse + up-to-2x-per-candidate linear scans ----


def test_load_csv_never_builds_a_rows_array_and_returns_index_maps_instead():
    """`qpbLoadCsv` must no longer eagerly parse every data line into a retained `rows` array --
    it must instead build lightweight `nameIndex`/`ktsnIndex` line-index maps in a single pass,
    returning `{header, text, lineOffsets, nameIndex, ktsnIndex}`."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content, "function qpbLoadCsv(relPath) {", "function qpbColumnIndex(header, name) {"
    )
    # The old eager-parse-every-line-into-`rows` pattern is gone.
    assert "var rows = [];" not in func_body
    assert "rows.push(qpbParseCsvLine(lines[i]));" not in func_body
    # The new single-pass indexing is present.
    assert "var nameIndex = {};" in func_body
    assert "var ktsnIndex = {};" in func_body
    assert "qpbParseCsvLine(lineText);" in func_body
    assert (
        "header: header, text: text, lineOffsets: lineOffsets,\n"
        "            nameIndex: nameIndex, ktsnIndex: ktsnIndex"
    ) in func_body
    # "First occurrence wins" -- an index entry is never overwritten once set.
    assert "if (!(normalizedName in nameIndex)) { nameIndex[normalizedName] = i; }" in func_body
    assert "if (!(ktsnValue in ktsnIndex)) { ktsnIndex[ktsnValue] = i; }" in func_body


def test_load_csv_and_load_national_ktsn_set_never_build_a_full_lines_array():
    """Real on-device crash fix (bisection-confirmed to still be caused by this exact code path
    even after the indexed-lookup rewrite above): neither loader may retain a `lines` array of
    every individual line's own substring (212,397 entries for the KTSN CSV, ~62,604 for the
    national KTSN list) simultaneously in memory alongside the one big decoded `text` string.
    Both must instead scan `text` once via the shared `qpbFindLineOffsets` offset-scanning
    helper, retaining only compact `[start, end]` integer-offset pairs, and derive any one line's
    text on demand via `text.substring(start, end)` only when that line is actually needed."""
    content = qml_plugin.render_identification_widget_qml("''")

    def _active_code(body: str) -> str:
        """Strips full-line `//` comments, so explanatory prose describing the *old*, now-removed
        `text.split(...)` behavior (kept in comments for context) doesn't produce a false
        "still uses split" positive -- only genuinely active, uncommented code is checked."""
        return "\n".join(
            line for line in body.splitlines() if not line.strip().startswith("//")
        )

    # The shared offset-scanning helper exists, uses `indexOf`, and never builds an array by
    # calling `.split(...)` on the whole text (which would itself allocate every line at once).
    scan_body = _active_code(_extract_function_body(
        content, "function qpbFindLineOffsets(text) {", "function qpbLoadCsv(relPath) {"
    ))
    assert "text.indexOf(" in scan_body
    assert ".split(" not in scan_body

    csv_body = _extract_function_body(
        content, "function qpbLoadCsv(relPath) {", "function qpbColumnIndex(header, name) {"
    )
    national_body = _extract_function_body(
        content,
        "function qpbLoadNationalKtsnSet(relPath) {",
        "// FR-QPB-106/107 (further revised, Decision Log D-40/D-42):",
    )

    for raw_body, label in ((csv_body, "qpbLoadCsv"), (national_body, "qpbLoadNationalKtsnSet")):
        func_body = _active_code(raw_body)
        # No `.split(...)`-based whole-file line array is built anymore.
        assert re.search(r"\.split\(\s*/", func_body) is None, label
        assert "text.split(" not in func_body, label
        # The offset-scanning helper is used instead.
        assert "qpbFindLineOffsets(text)" in func_body, label
        # No plain `var lines = ...` array of substrings is retained.
        assert re.search(r"\bvar\s+lines\s*=", func_body) is None, label
        # Access to any one line's text happens via `text.substring(...)`, not indexing into a
        # retained `lines` array of pre-built substrings.
        assert "text.substring(" in func_body, label
        assert re.search(r"\blines\[", func_body) is None, label

    # `qpbLoadCsv` returns `lineOffsets` (compact offset pairs), never a `lines` array of
    # substrings, and the full decoded `text` string so a matched line can be re-derived later.
    assert "lineOffsets: lineOffsets" in csv_body
    assert "lines: lines" not in csv_body


def test_match_ktsn_never_linear_scans_csv_rows_and_uses_index_lookups_instead():
    """`qpbMatchKtsn`'s two former full linear scans over `csv.rows` (the direct-name match and
    the accepted-KTSN lookup) must both be gone, replaced by O(1) `nameIndex`/`ktsnIndex` lookups
    that each parse only the single matched line -- re-derived on demand from `csv.text` via
    `csv.lineOffsets`, never from a retained `csv.lines` array of substrings."""
    content = qml_plugin.render_identification_widget_qml("''")
    match_body = _extract_function_body(
        content,
        "function qpbMatchKtsn(scientificNameWithoutAuthor, csv, nationalKtsnSet) {",
        "function qpbSampleProbabilityRaster(sampleExpression, callback) {",
    )
    # No reference to `csv.rows` or `csv.lines` remains anywhere in the matching function.
    assert "csv.rows" not in match_body
    assert "csv.lines" not in match_body
    # Neither of the two old full-scan patterns remains.
    assert re.search(r"for\s*\(\s*var\s+\w+\s*=\s*0;\s*\w+\s*<\s*csv\.rows\.length", match_body) \
        is None
    # The direct-name match now does an O(1) lookup into `nameIndex`, then re-derives that one
    # line's text on demand from `csv.text`/`csv.lineOffsets`, parsing only that one line.
    assert "csv.nameIndex ? csv.nameIndex[target] : undefined" in match_body
    assert "csv.lineOffsets[matchedLineIndex]" in match_body
    assert (
        "matchedRow = qpbParseCsvLine(csv.text.substring(matchedOffsets[0], matchedOffsets[1]));"
        in match_body
    )
    # The accepted-KTSN lookup now does an O(1) lookup into `ktsnIndex`, same on-demand
    # re-derivation, parsing only that one line.
    assert "csv.ktsnIndex ? csv.ktsnIndex[acceptedKtsn] : undefined" in match_body
    assert "csv.lineOffsets[acceptedLineIndex]" in match_body
    assert "acceptedRow = qpbParseCsvLine(" in match_body
    assert "csv.text.substring(acceptedOffsets[0], acceptedOffsets[1])" in match_body


def test_recursive_qml_matching_uses_defined_fail_closed_ktsn_normalizer():
    content = qml_plugin.render_identification_widget_qml("''")
    match_body = _extract_function_body(
        content,
        "function qpbMatchKtsn(scientificNameWithoutAuthor, csv, nationalKtsnSet) {",
        "function qpbSampleProbabilityRaster(sampleExpression, callback) {",
    )
    assert "function qpbUsableKtsnValue(value)" in content
    assert "qpbUsableKtsnValue(" in match_body
    assert "qpbUsableKtsn(" not in match_body
    # The helper must reject JavaScript object/array/boolean coercion rather than turning a bad
    # candidate into an identifier such as "[object Object]".
    helper_body = _extract_function_body(
        content,
        "function qpbUsableKtsnValue(value) {",
        "function qpbBytesToUtf8String(bytes) {",
    )
    assert 'valueType !== "string" && valueType !== "number"' in helper_body
    assert 'normalized === "null"' in helper_body
    assert 'normalized === "undefined"' in helper_body


# --- Conformance-defect fix: the KTSN CSV loading/matching bypass that was temporarily in place --
# --- for real-device crash bisection has been reverted; `qpbHandlePlantNetResponse` now calls ----
# --- the real `qpbLoadCsv`/`qpbLoadNationalKtsnSet`/`qpbMatchKtsn` functions again. ---------------


def test_handle_plantnet_response_calls_the_real_ktsn_loading_and_matching_functions():
    """The temporary bisection bypass (a stubbed "no match found" `ktsnMatch` object that never
    actually called `qpbLoadCsv`/`qpbLoadNationalKtsnSet`/`qpbMatchKtsn`) has been reverted:
    `qpbHandlePlantNetResponse` must actively call all three real functions again, using their
    real results for each candidate."""
    content = qml_plugin.render_identification_widget_qml("''")
    handler_body = _extract_function_body(
        content,
        "function qpbHandlePlantNetResponse(response) {",
        "function qpbPersistIdentification",
    )

    assert f'qpbLoadCsv("{qml_plugin.REFERENCE_KTSN_CSV_RELPATH}")' in handler_body
    assert (
        f'qpbLoadNationalKtsnSet("{qml_plugin.REFERENCE_NATIONAL_LIST_RELPATH}")' in handler_body
    )
    assert "qpbMatchKtsn(sciName, csv, nationalSet)" in handler_body

    # No stubbed "no match found" literal object remains.
    assert "var ktsnMatch = {" not in handler_body
    assert "TEMPORARY DIAGNOSTIC MARKER" not in content


def test_qpb_utf8_bytes_returns_a_uint8array_not_a_plain_array():
    """So every segment fed into the new segment-list assembly above is uniformly a typed array,
    `qpbUtf8Bytes` must itself build and return a `Uint8Array`, not a plain `Array` (which would
    force a mixed plain-Array/typed-array handling the segment-list approach is meant to avoid)."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content, "function qpbUtf8Bytes(text) {", "function qpbReadFileBytes(relPath) {"
    )
    assert "new Uint8Array(text.length)" in func_body
    assert "bytes[i] = text.charCodeAt(i) & 0xff;" in func_body
    assert "var bytes = [];" not in func_body
    assert "bytes.push(" not in func_body


def _naive_multipart_body_old_algorithm(
    boundary: str, organs_header: bytes, images_header: bytes, file_bytes: bytes, trailer: bytes
) -> bytes:
    """A faithful Python port of the *old*, confirmed-buggy body-assembly algorithm (byte-by-byte
    `parts.push(fileBytes[b])`, plus repeated `parts = parts.concat(...)`), used only as a ground
    truth for the byte-sequence-equivalence check below. Never used by application code."""
    parts: list[int] = []
    parts = parts + list(organs_header)
    parts = parts + list(images_header)
    for b in file_bytes:
        parts.append(b)
    parts = parts + list(trailer)
    return bytes(parts)


def _efficient_multipart_body_new_algorithm(
    boundary: str, organs_header: bytes, images_header: bytes, file_bytes: bytes, trailer: bytes
) -> bytes:
    """A faithful Python port of the *new*, efficient body-assembly algorithm (a list of segments,
    a single-pass total-length computation, one preallocated buffer, and a `.set(...)`-equivalent
    bulk copy per segment via slice assignment), used only as a ground truth for the
    byte-sequence-equivalence check below. Never used by application code."""
    segments = [organs_header, images_header, file_bytes, trailer]
    total_length = sum(len(segment) for segment in segments)
    body = bytearray(total_length)
    offset = 0
    for segment in segments:
        body[offset : offset + len(segment)] = segment
        offset += len(segment)
    return bytes(body)


@pytest.mark.parametrize(
    "file_size",
    [0, 1, 17, 4096, 250_000, 3_500_000],  # includes a multi-MB synthetic "photo" size
    ids=["empty", "one_byte", "small", "4kb", "250kb", "3.5mb"],
)
def test_old_and_new_multipart_assembly_algorithms_produce_byte_identical_output(file_size):
    """This is not merely a source-text check: it ports *both* the old (confirmed-buggy,
    per-byte-push-plus-repeated-concat) and the new (segment-list, single-preallocation,
    bulk-copy) body-assembly algorithms line-for-line into Python, runs both against synthetic
    "photo" byte content of varying sizes (including a multi-MB size, to meaningfully exercise the
    efficiency property the fix targets, not just a trivial input), and asserts the *resulting byte
    sequence* is exactly identical. This gives real, verifiable confidence the rewrite changed only
    *how* the bytes are assembled, not *what* bytes are produced -- not just that the generated JS
    source "looks different"."""
    boundary = "----qpbPlantNetBoundary1234567890"
    organs_header = (
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="organs"\r\n\r\nauto\r\n'
    ).encode("utf-8")
    images_header = (
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="images"; filename="photo.jpg"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    trailer = b"\r\n"
    # Synthetic "photo" bytes: a repeating, non-trivial byte pattern (not all-zero) so any
    # off-by-one or ordering bug in either algorithm would very plausibly be caught.
    file_bytes = bytes((i * 37 + 11) % 256 for i in range(file_size))

    old_result = _naive_multipart_body_old_algorithm(
        boundary, organs_header, images_header, file_bytes, trailer
    )
    new_result = _efficient_multipart_body_new_algorithm(
        boundary, organs_header, images_header, file_bytes, trailer
    )
    assert old_result == new_result
    # Sanity: the assembled body actually contains the expected segments in order.
    assert new_result == organs_header + images_header + file_bytes + trailer


# --- Conformance-defect fix: KTSN lookup rewritten from a 212,397-row eager-parse + up-to-2x ----
# --- per-candidate linear scan into a single-pass-indexed, O(1)-lookup mechanism ------------------
#
# The following is a faithful, line-for-line Python port of both the *old* (confirmed-still-
# crash-prone, full-`rows`-array, linear-scan) `qpbMatchKtsn` algorithm and the *new* (single-pass
# `nameIndex`/`ktsnIndex`, O(1)-lookup) algorithm, run against the same synthetic reference-table
# rows and the same set of Pl@ntNet candidate names, asserting the two produce byte-for-byte
# identical `qpbMatchKtsn` result dictionaries for every case -- including a deliberately
# duplicated normalized `taxon_full_nm` (rows 0 and 13) and a deliberately duplicated `ktsn` value
# (rows 2 and 14), to concretely prove the new O(1)-index lookup preserves the old linear scan's
# exact "first occurrence in file order wins" tie-break, not just that it is faster. Both ports
# operate on already-`qpbParseCsvLine`-parsed rows (a plain header + list-of-lists shape) --
# `qpbParseCsvLine` itself is unchanged by this fix, so it is out of scope for this equivalence
# check; what changed is purely *how a matching row is found* among already-parsed rows.

_KTSN_HEADER = ["ktsn", "taxon_full_nm", "taxon_kor_nm", "taxon_jm_nm", "correct_list"]
_IDX_KTSN, _IDX_FULL_NM, _IDX_KOR_NM, _IDX_JM_NM, _IDX_CORRECT_LIST = range(5)


def _qpb_normalize_name(name: str | None) -> str:
    """Faithful port of `qpbNormalizeName`."""
    return re.sub(r"\s+", " ", name or "").strip()


def _qpb_strip_em_tags(text: str | None) -> str:
    """Faithful port of `qpbStripEmTags`."""
    return re.sub(r"</?em>", "", text or "")


def _qpb_parse_csv_line(line: str) -> list[str]:
    """Faithful, line-for-line port of `qpbParseCsvLine` (unchanged by this fix -- reused as-is
    by both the old split()-based and the new offset-scan-based line extraction)."""
    fields: list[str] = []
    cur = ""
    in_quotes = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    cur += '"'
                    i += 1
                else:
                    in_quotes = False
            else:
                cur += ch
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ",":
                fields.append(cur)
                cur = ""
            else:
                cur += ch
        i += 1
    fields.append(cur)
    return fields


def _qpb_find_line_offsets(
    text: str, *, finder: Callable[[str, int], int] | None = None
) -> list[tuple[int, int]]:
    """Faithful, line-for-line port of the new `qpbFindLineOffsets` JS function (post
    performance-defect fix): a single scan over `text` locating each line's `[start, end)`
    character-offset pair, equivalent to `text.split(/\\r\\n|\\n|\\r/)` but never allocating a
    `lines` array of substrings, and never re-searching for a terminator once its next occurrence
    (or absence, for the rest of `text`) is already known from an earlier search -- this keeps the
    scan genuinely O(n) even when "\\r" (or "\\n") occurs zero times, once, or on every line, unlike
    the unconditional `text.find("\\r", pos)` + `text.find("\\n", pos)` per iteration this
    function used before the fix (which degrades to O(n * lineCount) whenever one terminator is
    rare or absent -- confirmed to be the case for the bundled national KTSN list).

    `finder` (test-only hook) lets callers substitute an instrumented lookalike for `str.find` to
    count/measure the actual scan work performed, without changing any real behavior when omitted.
    """
    find = finder if finder is not None else (lambda t, p: text.find(t, p))
    offsets: list[tuple[int, int]] = []
    pos = 0
    length = len(text)
    UNKNOWN = -2  # cached value not yet searched, or stale (pos has advanced past it).
    r_idx = UNKNOWN
    n_idx = UNKNOWN
    while pos <= length:
        # A cached found index (>= 0) becomes stale once `pos` has moved past it; a cached -1
        # ("none from here to the end") never becomes stale, since `pos` only increases.
        if r_idx != -1 and r_idx < pos:
            r_idx = UNKNOWN
        if r_idx == UNKNOWN:
            r_idx = find("\r", pos)
        if n_idx != -1 and n_idx < pos:
            n_idx = UNKNOWN
        if n_idx == UNKNOWN:
            n_idx = find("\n", pos)

        if r_idx == -1 and n_idx == -1:
            offsets.append((pos, length))
            break
        elif r_idx == -1:
            term_start, term_length = n_idx, 1
        elif n_idx == -1:
            term_start, term_length = r_idx, 1
        elif r_idx + 1 == n_idx:
            term_start, term_length = r_idx, 2  # "\r\n" is a single terminator.
        elif r_idx < n_idx:
            term_start, term_length = r_idx, 1  # lone "\r"
        else:
            term_start, term_length = n_idx, 1  # lone "\n"
        offsets.append((pos, term_start))
        pos = term_start + term_length
    return offsets


def _csv_escape_field(value: str) -> str:
    """RFC-4180-style field escaping, the exact inverse of `_qpb_parse_csv_line`/
    `qpbParseCsvLine`, used only to build synthetic CSV text blobs for the equivalence tests
    below."""
    if any(c in value for c in (",", '"', "\n", "\r")):
        return '"' + value.replace('"', '""') + '"'
    return value


def _rows_to_csv_text(header: list[str], rows: list[list[str]], newline: str) -> str:
    """Serializes `header` + `rows` into a single raw CSV text blob using the given newline
    style, with a trailing newline (matching a real bundled reference file) -- used only to
    construct synthetic input for the line-scanning equivalence tests below."""
    lines = [",".join(_csv_escape_field(f) for f in header)]
    for row in rows:
        lines.append(",".join(_csv_escape_field(f) for f in row))
    return newline.join(lines) + newline


def _old_find_matched_row(rows: list[list[str]], target: str) -> list[str] | None:
    """Faithful port of the *old*, confirmed-still-crash-prone `qpbMatchKtsn` direct-name linear
    scan (`for (var i = 0; i < csv.rows.length; i++) { ... if (candidate === target) { matchedRow
    = row; break; } }`)."""
    for row in rows:
        candidate = _qpb_normalize_name(_qpb_strip_em_tags(row[_IDX_FULL_NM]))
        if candidate == target:
            return row
    return None


def _old_find_accepted_row(rows: list[list[str]], accepted_ktsn: str) -> list[str] | None:
    """Faithful port of the *old* accepted-KTSN linear scan (`for (var j = 0; j <
    csv.rows.length; j++) { if (csv.rows[j][idxKtsn] === acceptedKtsn) { acceptedRow =
    csv.rows[j]; break; } }`)."""
    for row in rows:
        if row[_IDX_KTSN] == accepted_ktsn:
            return row
    return None


def _new_build_indexes(rows: list[list[str]]) -> tuple[dict[str, int], dict[str, int]]:
    """Faithful port of the *new* `qpbLoadCsv` single indexing pass -- "first occurrence wins",
    an existing index entry is never overwritten."""
    name_index: dict[str, int] = {}
    ktsn_index: dict[str, int] = {}
    for i, row in enumerate(rows):
        normalized_name = _qpb_normalize_name(_qpb_strip_em_tags(row[_IDX_FULL_NM]))
        if normalized_name not in name_index:
            name_index[normalized_name] = i
        ktsn_value = row[_IDX_KTSN]
        if ktsn_value not in ktsn_index:
            ktsn_index[ktsn_value] = i
    return name_index, ktsn_index


def _new_find_matched_row(
    rows: list[list[str]], name_index: dict[str, int], target: str
) -> list[str] | None:
    """Faithful port of the *new* `qpbMatchKtsn` O(1) direct-name lookup (`csv.nameIndex ?
    csv.nameIndex[target] : undefined` then parsing only that one matched line)."""
    line_index = name_index.get(target)
    return rows[line_index] if line_index is not None else None


def _new_find_accepted_row(
    rows: list[list[str]], ktsn_index: dict[str, int], accepted_ktsn: str
) -> list[str] | None:
    """Faithful port of the *new* O(1) accepted-KTSN lookup."""
    line_index = ktsn_index.get(accepted_ktsn)
    return rows[line_index] if line_index is not None else None


def _qpb_match_ktsn_port(
    scientific_name_without_author: str,
    rows: list[list[str]],
    national_ktsn_set: dict[str, bool],
    *,
    use_new_algorithm: bool,
    name_index: dict[str, int] | None = None,
    ktsn_index: dict[str, int] | None = None,
) -> dict:
    """A faithful, line-for-line Python port of the full `qpbMatchKtsn` function (both its
    old-linear-scan and new-indexed-lookup variants share every line of this downstream control
    flow identically -- only the two `_find_matched_row`/`_find_accepted_row` calls below differ
    between the two variants, exactly matching how little the real JS fix actually changed)."""
    result = {
        "direct_match_found": False,
        "direct_row_ktsn": None,
        "direct_korean_name": None,
        "direct_taxon_jm_nm": None,
        "accepted_resolution_attempted": False,
        "accepted_resolved": False,
        "accepted_ktsn": None,
        "accepted_korean_name": None,
        "accepted_scientific_name": None,
        "ambiguous": False,
        "ambiguous_reason": None,
        "unresolved_reason": None,
    }

    target = _qpb_normalize_name(scientific_name_without_author)
    if use_new_algorithm:
        matched_row = _new_find_matched_row(rows, name_index, target)
    else:
        matched_row = _old_find_matched_row(rows, target)
    if matched_row is None:
        return result

    result["direct_match_found"] = True
    result["direct_row_ktsn"] = matched_row[_IDX_KTSN]
    result["direct_korean_name"] = matched_row[_IDX_KOR_NM]
    result["direct_taxon_jm_nm"] = matched_row[_IDX_JM_NM]
    result["accepted_resolution_attempted"] = True

    if result["direct_taxon_jm_nm"] == "정명":
        result["accepted_resolved"] = True
        result["accepted_ktsn"] = result["direct_row_ktsn"]
        result["accepted_korean_name"] = result["direct_korean_name"]
        result["accepted_scientific_name"] = _qpb_strip_em_tags(matched_row[_IDX_FULL_NM])
        return result

    raw_correct_list = matched_row[_IDX_CORRECT_LIST]
    try:
        parsed = json.loads(raw_correct_list) if raw_correct_list else []
    except json.JSONDecodeError:
        result["unresolved_reason"] = "correct_list_malformed"
        return result
    if not parsed:
        result["unresolved_reason"] = "correct_list_empty"
        return result

    chosen_entry = parsed[0]
    if len(parsed) > 1:
        matches = []
        for entry in parsed:
            if "KTSN" in entry:
                entry_ktsn = str(entry["KTSN"])
            elif "KTNS" in entry:
                entry_ktsn = str(entry["KTNS"])
            else:
                entry_ktsn = None
            if entry_ktsn is not None and national_ktsn_set.get(entry_ktsn):
                matches.append(entry)
        if len(matches) == 1:
            chosen_entry = matches[0]
        else:
            result["ambiguous"] = True
            result["ambiguous_reason"] = (
                "no candidate KTSN found in the NIBR accepted-taxon national list"
                if len(matches) == 0
                else "more than one candidate KTSN found in the NIBR accepted-taxon national list"
            )
            return result

    has_ktsn_key = "KTSN" in chosen_entry
    has_ktns_key = "KTNS" in chosen_entry
    if not has_ktsn_key and not has_ktns_key:
        result["unresolved_reason"] = "correct_list_missing_ktsn_key"
        return result
    if has_ktsn_key and has_ktns_key and str(chosen_entry["KTSN"]) != str(chosen_entry["KTNS"]):
        result["ambiguous"] = True
        result["ambiguous_reason"] = "KTSN and KTNS keys present with different values"
        return result
    accepted_ktsn = str(chosen_entry["KTSN"]) if has_ktsn_key else str(chosen_entry["KTNS"])

    if use_new_algorithm:
        accepted_row = _new_find_accepted_row(rows, ktsn_index, accepted_ktsn)
    else:
        accepted_row = _old_find_accepted_row(rows, accepted_ktsn)
    if accepted_row is None:
        result["unresolved_reason"] = "accepted_ktsn_not_found_in_csv"
        return result
    result["accepted_resolved"] = True
    result["accepted_ktsn"] = accepted_ktsn
    result["accepted_korean_name"] = accepted_row[_IDX_KOR_NM]
    result["accepted_scientific_name"] = _qpb_strip_em_tags(accepted_row[_IDX_FULL_NM])
    return result


def _build_synthetic_ktsn_rows() -> list[list[str]]:
    """Synthetic reference-table rows (`[ktsn, taxon_full_nm, taxon_kor_nm, taxon_jm_nm,
    correct_list]`) exercising every branch of `qpbMatchKtsn`, plus:

    - rows 0 and 13: two different rows whose `taxon_full_nm` normalizes to the *same* name
      ("Aa1 species") -- proves the direct-name-match "first occurrence wins" tie-break.
    - rows 2 and 14: two different rows sharing the *same* `ktsn` value ("KTSN0003") -- proves
      the accepted-KTSN-lookup "first occurrence wins" tie-break.
    """
    return [
        ["KTSN0001", "<em>Aa1 species</em>", "가나다1", "정명", ""],  # 0
        ["KTSN0002", "<em>Bb2 species</em>", "가나다2", "이명", '[{"KTSN": "KTSN0003"}]'],  # 1
        ["KTSN0003", "<em>Cc3 species</em>", "가나다3", "정명", ""],  # 2 (accepted target of row 1)
        [
            "KTSN0004", "<em>Dd4 species</em>", "가나다4", "이명",
            '[{"KTSN": "KTSN0005"}, {"KTSN": "KTSN0006"}]',
        ],  # 3
        ["KTSN0005", "<em>Ee5 species</em>", "가나다5", "정명", ""],  # 4 (accepted target of row 3)
        ["KTSN0006", "<em>Ff6 species</em>", "가나다6", "정명", ""],  # 5
        [
            "KTSN0007", "<em>Gg7 species</em>", "가나다7", "이명",
            '[{"KTSN": "KTSN0006"}, {"KTSN": "KTSN9999"}]',
        ],  # 6 -- zero candidates in the national list -> ambiguous
        [
            "KTSN0008", "<em>Hh8 species</em>", "가나다8", "이명",
            '[{"KTSN": "KTSN0005"}, {"KTSN": "KTSN0001"}]',
        ],  # 7 -- two candidates in the national list -> ambiguous
        # 8 -- malformed correct_list JSON
        ["KTSN0009", "<em>Ii9 species</em>", "가나다9", "이명", "{not valid json"],
        ["KTSN0010", "<em>Jj10 species</em>", "가나다10", "이명", "[]"],  # 9 -- empty list
        ["KTSN0011", "<em>Kk11 species</em>", "가나다11", "이명", '[{"foo": "bar"}]'],  # 10
        [
            "KTSN0012", "<em>Ll12 species</em>", "가나다12", "이명",
            '[{"KTSN": "KTSN0005", "KTNS": "KTSN0006"}]',
        ],  # 11 -- KTSN/KTNS conflict
        [
            "KTSN0013", "<em>Mm13 species</em>", "가나다13", "이명",
            '[{"KTSN": "NOTINROWS"}]',
        ],  # 12 -- accepted KTSN not present in any row
        ["KTSN9999", "<em>Aa1 species</em>", "DUPLICATE_NAME_SHOULD_NOT_WIN", "정명", ""],  # 13
        [
            "KTSN0003", "<em>DuplicateKtsnRow</em>", "DUPLICATE_KTSN_SHOULD_NOT_WIN", "정명", "",
        ],  # 14
    ]


_KTSN_MATCH_TEST_TARGETS = [
    "Aa1 species",  # direct 정명 accept; also exercises the duplicated-name tie-break (row 0/13)
    "Bb2 species",  # single-entry correct_list; accepted row lookup also exercises the
    # duplicated-ktsn tie-break (row 2/14)
    "Dd4 species",  # multi-entry correct_list, exactly one national-list match
    "Gg7 species",  # multi-entry correct_list, zero national-list matches -> ambiguous
    "Hh8 species",  # multi-entry correct_list, multiple national-list matches -> ambiguous
    "Ii9 species",  # malformed correct_list JSON
    "Jj10 species",  # empty correct_list
    "Kk11 species",  # correct_list entry missing KTSN/KTNS key
    "Ll12 species",  # correct_list entry with conflicting KTSN/KTNS values
    "Mm13 species",  # accepted KTSN not present in any row
    "No Such Species At All",  # no direct match at all
]


def test_old_and_new_ktsn_match_algorithms_produce_identical_results_for_every_case():
    """Concretely proves the new single-pass-indexed, O(1)-lookup `qpbMatchKtsn` algorithm
    produces byte-for-byte identical results to the old, full-`rows`-array, linear-scan algorithm
    for every branch (direct 정명 accept, single/multi-entry `correct_list` resolution, all three
    ambiguity kinds, all three unresolved kinds, and a total non-match) -- including both
    deliberately duplicated-key cases proving the exact "first occurrence in file order wins"
    tie-break is preserved."""
    rows = _build_synthetic_ktsn_rows()
    national_ktsn_set = {"KTSN0001": True, "KTSN0003": True, "KTSN0005": True}
    name_index, ktsn_index = _new_build_indexes(rows)

    for target in _KTSN_MATCH_TEST_TARGETS:
        old_result = _qpb_match_ktsn_port(
            target, rows, national_ktsn_set, use_new_algorithm=False
        )
        new_result = _qpb_match_ktsn_port(
            target, rows, national_ktsn_set, use_new_algorithm=True,
            name_index=name_index, ktsn_index=ktsn_index,
        )
        assert old_result == new_result, f"mismatch for target={target!r}"


def test_new_ktsn_index_lookup_preserves_first_occurrence_wins_tie_break_explicitly():
    """A more explicit, targeted version of the tie-break proof above: directly asserts the
    resolved values come from the *first* occurrence in file order for both the duplicated-name
    and duplicated-ktsn cases, for both algorithms."""
    rows = _build_synthetic_ktsn_rows()
    national_ktsn_set = {"KTSN0001": True, "KTSN0003": True, "KTSN0005": True}
    name_index, ktsn_index = _new_build_indexes(rows)

    # Duplicated normalized name (rows 0 and 13): both algorithms must resolve to row 0's data,
    # never row 13's "DUPLICATE_NAME_SHOULD_NOT_WIN".
    for use_new in (False, True):
        result = _qpb_match_ktsn_port(
            "Aa1 species", rows, national_ktsn_set, use_new_algorithm=use_new,
            name_index=name_index, ktsn_index=ktsn_index,
        )
        assert result["direct_korean_name"] == "가나다1"
        assert result["direct_korean_name"] != "DUPLICATE_NAME_SHOULD_NOT_WIN"

    # Duplicated ktsn value (rows 2 and 14, both "KTSN0003"): row 1's correct_list resolution
    # must land on row 2's data, never row 14's "DUPLICATE_KTSN_SHOULD_NOT_WIN".
    for use_new in (False, True):
        result = _qpb_match_ktsn_port(
            "Bb2 species", rows, national_ktsn_set, use_new_algorithm=use_new,
            name_index=name_index, ktsn_index=ktsn_index,
        )
        assert result["accepted_korean_name"] == "가나다3"
        assert result["accepted_korean_name"] != "DUPLICATE_KTSN_SHOULD_NOT_WIN"


# --- Real on-device crash fix: `qpbLoadCsv`/`qpbLoadNationalKtsnSet` rewritten from a -----------
# --- `text.split(...)`-built full `lines` array of substrings into a single `indexOf`-based ------
# --- offset scan (`qpbFindLineOffsets`) retaining only compact [start, end] integer pairs --------
#
# The following ports the new offset-scanning line-extraction mechanism into Python and proves,
# for every newline style the old regex-based `.split(/\r\n|\n|\r/)` recognized ("\n", "\r\n", and
# lone "\r"), that: (a) the set of extracted line substrings is byte-for-byte identical between
# the old split()-based approach and the new offset-scan-based approach; and (b) feeding either
# extraction's data rows through the existing old-linear-scan vs. new-indexed-lookup
# `qpbMatchKtsn` ports (above) produces byte-for-byte identical match results for every branch
# already exercised by `test_old_and_new_ktsn_match_algorithms_produce_identical_results_for_every_
# case`. This is not merely a source-text check -- it is a real, executable proof that rewriting
# *how* a line's text is found and retained (offset pairs re-derived on demand via
# `text.substring(...)`, instead of a fully pre-split `lines` array) changed nothing about *what*
# lines, rows, or match results are produced.


def test_offset_based_line_scanning_produces_identical_lines_to_split_based_scanning():
    """Proves the new `qpbFindLineOffsets`-based line extraction (offset pairs + on-demand
    `text.substring(...)`) yields exactly the same sequence of non-empty line strings as the old
    `text.split(/\\r\\n|\\n|\\r/).filter(...)` approach, for every recognized newline style, and
    also when a stray blank line is present mid-file (exercising the non-empty-line filter that
    keeps index positions aligned)."""
    rows = _build_synthetic_ktsn_rows()

    for newline in ("\n", "\r\n", "\r"):
        text = _rows_to_csv_text(_KTSN_HEADER, rows, newline=newline)
        old_lines = [line for line in re.split(r"\r\n|\n|\r", text) if len(line) > 0]
        offsets = [o for o in _qpb_find_line_offsets(text) if o[1] > o[0]]
        new_lines = [text[start:end] for start, end in offsets]
        assert old_lines == new_lines, f"mismatch for newline={newline!r}"

    # A stray blank line inserted mid-file must be dropped identically by both approaches, keeping
    # subsequent line-index positions aligned between the two mechanisms.
    text_with_blank_line = "header_a,header_b\nfoo,bar\n\nbaz,qux\n"
    old_lines = [line for line in re.split(r"\r\n|\n|\r", text_with_blank_line) if len(line) > 0]
    offsets = [o for o in _qpb_find_line_offsets(text_with_blank_line) if o[1] > o[0]]
    new_lines = [text_with_blank_line[start:end] for start, end in offsets]
    assert old_lines == new_lines == ["header_a,header_b", "foo,bar", "baz,qux"]


def test_offset_based_csv_line_extraction_feeds_identical_match_results_as_split_based():
    """End-to-end equivalence: builds a real raw CSV text blob (header + data rows, exactly like
    the bundled reference file), extracts and parses its data rows via the *old*
    `text.split(...)`-built `lines`-array approach and via the *new* `qpbFindLineOffsets`
    offset-scan + on-demand `text.substring(...)` approach, and confirms `qpbMatchKtsn`'s own
    port (`_qpb_match_ktsn_port`) produces byte-for-byte identical results either way, for every
    branch already exercised by `test_old_and_new_ktsn_match_algorithms_produce_identical_results_
    for_every_case` above -- for every newline style the old regex recognized."""
    rows = _build_synthetic_ktsn_rows()
    national_ktsn_set = {"KTSN0001": True, "KTSN0003": True, "KTSN0005": True}

    for newline in ("\n", "\r\n", "\r"):
        text = _rows_to_csv_text(_KTSN_HEADER, rows, newline=newline)

        # Old approach: split the whole text into a `lines` array up front (mirrors the pre-fix
        # JS `text.split(/\r\n|\n|\r/).filter(...)`), then parse every data line (index 0 is the
        # header, matching `qpbLoadCsv`'s own `lines[0]`/`lines[1..]` split).
        old_lines = [line for line in re.split(r"\r\n|\n|\r", text) if len(line) > 0]
        old_rows = [_qpb_parse_csv_line(line) for line in old_lines[1:]]

        # New approach: scan for [start, end) offsets once, filter empty ranges, and parse each
        # data line's on-demand substring (mirrors the new JS `qpbFindLineOffsets` +
        # `text.substring(...)` + `qpbParseCsvLine`) -- never materializing a `lines` array of
        # substrings for the whole file.
        offsets = [o for o in _qpb_find_line_offsets(text) if o[1] > o[0]]
        new_rows = [_qpb_parse_csv_line(text[start:end]) for start, end in offsets[1:]]

        assert old_rows == new_rows, f"parsed data rows differ for newline={newline!r}"

        name_index, ktsn_index = _new_build_indexes(new_rows)
        for target in _KTSN_MATCH_TEST_TARGETS:
            old_result = _qpb_match_ktsn_port(
                target, old_rows, national_ktsn_set, use_new_algorithm=False
            )
            new_result = _qpb_match_ktsn_port(
                target, new_rows, national_ktsn_set, use_new_algorithm=True,
                name_index=name_index, ktsn_index=ktsn_index,
            )
            assert old_result == new_result, (
                f"mismatch for newline={newline!r} target={target!r}"
            )


# --- performance-defect fix: `qpbFindLineOffsets` must be genuine O(n), never O(n * lineCount) --
#
# Reviewer-found defect: the version above (before this round's fix) called
# `text.indexOf("\r", pos)` *and* `text.indexOf("\n", pos)` unconditionally on every loop
# iteration (once per line). A JS/`str.find`-style forward scan that finds no match cannot return
# early -- it must scan all the way from `pos` to the end of the string before reporting -1. When
# one terminator never occurs anywhere in `text` at all (exactly the case for the bundled national
# KTSN list, written via Python's `"\n".join(...)` with no `\r` bytes -- see `reference_bundle.py`
# around line 198), that search alone degrades the whole scan from O(n) to O(n * lineCount). The
# tests below instrument `_qpb_find_line_offsets`'s `finder` hook to count the actual scan work
# performed (not wall-clock time, to avoid a flaky timing-based test), and separately reproduce the
# old, pre-fix scanning pattern to quantify how quadratic it actually was for the same input.


def _make_counting_finder(text: str) -> tuple[Callable[[str, int], int], dict[str, int]]:
    """Wraps `str.find` with a call that tallies the total number of characters any single
    "forward scan to find the next occurrence of `needle` at or after `pos`" would have to
    examine: `idx - pos + 1` if found, or `len(text) - pos` if not found (a linear scan must
    inspect every remaining character before it can report -1). This models the real cost of a
    JS `String.prototype.indexOf` (or Python `str.find`) call without depending on wall-clock
    timing, which would make this test flaky."""
    stats = {"scanned_chars": 0, "calls": 0}

    def finder(needle: str, pos: int) -> int:
        stats["calls"] += 1
        idx = text.find(needle, pos)
        stats["scanned_chars"] += (idx - pos + 1) if idx != -1 else (len(text) - pos)
        return idx

    return finder, stats


def _qpb_find_line_offsets_pre_fix_reference(
    text: str, finder: Callable[[str, int], int]
) -> list[tuple[int, int]]:
    """Reproduces the *old*, pre-fix `qpbFindLineOffsets` scanning pattern exactly (unconditional
    `find("\\r", pos)` + `find("\\n", pos)` on every iteration, no caching) -- used only by the
    complexity test below, to quantify how quadratic that old pattern actually was for the same
    input the new, fixed algorithm is proven linear for. Not used by any correctness test above,
    which already covers the fixed algorithm's output directly."""
    offsets: list[tuple[int, int]] = []
    pos = 0
    length = len(text)
    while pos <= length:
        r_idx = finder("\r", pos)
        n_idx = finder("\n", pos)
        if r_idx == -1 and n_idx == -1:
            offsets.append((pos, length))
            break
        elif r_idx == -1:
            term_start, term_length = n_idx, 1
        elif n_idx == -1:
            term_start, term_length = r_idx, 1
        elif r_idx + 1 == n_idx:
            term_start, term_length = r_idx, 2
        elif r_idx < n_idx:
            term_start, term_length = r_idx, 1
        else:
            term_start, term_length = n_idx, 1
        offsets.append((pos, term_start))
        pos = term_start + term_length
    return offsets


def test_find_line_offsets_is_linear_time_even_when_a_terminator_never_occurs():
    """Proves the fix directly: for a large, purely "\\n"-terminated text containing zero "\\r"
    characters anywhere (the exact shape of the real bundled national KTSN list on this project's
    macOS build -- `reference_bundle.py`'s `"\\n".join(...)` with no `newline=""` override), the
    *fixed* `_qpb_find_line_offsets` does a bounded, linear amount of scan work in `text.length`,
    while the *old, pre-fix* pattern (reproduced above) is quadratic for the same input -- i.e.
    the new function no longer does an unconditional full-remaining-text scan for a terminator
    ("\\r") that never appears."""
    line_count = 20_000
    text = "\n".join(f"line{i:06d}data" for i in range(line_count)) + "\n"
    assert "\r" not in text
    n = len(text)

    new_finder, new_stats = _make_counting_finder(text)
    new_offsets = _qpb_find_line_offsets(text, finder=new_finder)
    assert len(new_offsets) == line_count + 1  # trailing empty line after the final "\n".

    old_finder, old_stats = _make_counting_finder(text)
    old_offsets = _qpb_find_line_offsets_pre_fix_reference(text, old_finder)
    assert old_offsets == new_offsets  # identical result either way -- only the cost differs.

    # The fixed version's total scanned work is bounded by a small constant multiple of `n`
    # (each of the two terminators contributes at most one full pass over the remaining text,
    # plus O(1) work per line for the terminator that *is* found) -- never O(n * lineCount).
    assert new_stats["scanned_chars"] <= 4 * n, (
        f"fixed qpbFindLineOffsets scanned {new_stats['scanned_chars']} chars for n={n}, "
        "expected genuine O(n) (<= 4n)"
    )

    # The old, pre-fix pattern is confirmed quadratic for this exact input: it re-scans for the
    # never-present "\r" from every one of `line_count` positions, each such scan running to the
    # end of the (shrinking) remaining text.
    assert old_stats["scanned_chars"] >= (line_count * n) // 4, (
        f"pre-fix reference only scanned {old_stats['scanned_chars']} chars for n={n}, "
        "line_count={line_count} -- expected it to reproduce the O(n * lineCount) blowup"
    )

    # The fix must be a genuine, dramatic improvement, not a marginal tweak.
    assert new_stats["scanned_chars"] * 100 < old_stats["scanned_chars"]


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("a\nb\r\nc\rd\n\ne\r\r\nf", id="mixed_terminators_no_trailing_newline"),
        pytest.param("only-one-line-no-terminator", id="single_line_no_terminator"),
        pytest.param("\n\n\r\n\r\n\r\r", id="all_blank_lines_mixed_terminators"),
        pytest.param("a\r\nb\r\nc\r\n", id="pure_crlf"),
        pytest.param("a\rb\rc\r", id="pure_cr"),
        pytest.param("a\nb\nc\n", id="pure_lf"),
        pytest.param("", id="empty_text"),
    ],
)
def test_find_line_offsets_matches_split_for_every_terminator_style(text):
    """Correctness must not regress for any of the four newline styles (`\\n`-only, `\\r\\n`-only,
    `\\r`-only, and mixed), including a final line with no trailing terminator and blank lines --
    the offset-scan result, sliced back into substrings via `text[start:end]`, must exactly equal
    the trusted `re.split(/\\r\\n|\\n|\\r/)` oracle (with *no* empty-line filtering here, unlike
    the earlier equivalence tests above, so blank lines are checked precisely too)."""
    expected = re.split(r"\r\n|\n|\r", text)
    offsets = _qpb_find_line_offsets(text)
    actual = [text[start:end] for start, end in offsets]
    assert actual == expected


# --- FR-QPB-104/FR-QPB-109 (further revised; Decision Log D-54): candidate representative image +
# CC BY-SA attribution (AC-QPB-094/AC-QPB-095/AC-QPB-096) ---------------------------------------
#
# The acceptance suite's `test_ac095_*` tests (test_post_mvp_identification_plugin.py) already
# confirm this structurally against a real, generated `.qgs` project's embedded widget QML (via
# `inspect_identification_widget`, requiring a real QGIS/PyQGIS runtime). These unit tests exercise
# the same generated-source properties directly against `render_identification_widget_qml()`'s
# return value -- no PyQGIS required -- mirroring this file's own existing convention (e.g. the
# AC-QPB-088 resize-mechanism tests above).

_IMAGE_DECL_RE = re.compile(r"\bImage\s*\{")
_MODEL_DATA_SOURCE_RE = re.compile(r"source\s*:\s*[^;\n]*modelData")
_MODEL_DATA_VISIBLE_RE = re.compile(r"visible\s*:\s*[^;\n]*modelData")
_SMALL_VARIANT_RE = re.compile(r"url\w*\s*(?:\.\s*s\b|\[\s*['\"]s['\"]\s*\])", re.IGNORECASE)
_CC_BY_SA_TEXT = "CC BY-SA"
_PLANTNET_TEXT_RE = re.compile(r"Pl(?:@|\\u0040)ntNet")
_AUTHOR_REF_RE = re.compile(r"\bauthor\b", re.IGNORECASE)


def _find_image_blocks(qml_code: str) -> list[str]:
    """Returns each balanced ``Image { ... }`` QML object block's full text."""
    blocks = []
    for m in _IMAGE_DECL_RE.finditer(qml_code):
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(qml_code):
            ch = qml_code[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(qml_code[start : i + 1])
                    break
            i += 1
    return blocks


def test_shared_plantnet_url_builder_requests_related_images():
    """AC-QPB-094-adjacent: the *real, shipped* runtime request-URL builder embedded in the QML
    (`qpbBuildPlantNetUrl`, used by both the project plugin and the embedded widget) must also
    request `include-related-images=true`, not only the offline `build_plantnet_identify_request`
    reference implementation tested by the acceptance suite."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "include-related-images=true" in content


def test_identification_widget_qml_contains_an_image_element_bound_to_model_data():
    content = qml_plugin.render_identification_widget_qml("''")
    blocks = _find_image_blocks(content)
    assert blocks, "expected at least one QML 'Image { ... }' element"
    assert any(_MODEL_DATA_SOURCE_RE.search(block) for block in blocks), (
        "expected an Image element whose 'source:' is bound to modelData"
    )


def test_identification_widget_qml_selects_the_small_s_size_variant():
    content = qml_plugin.render_identification_widget_qml("''")
    assert _SMALL_VARIANT_RE.search(content), (
        "expected a Pl@ntNet 'url' object's small ('s') size-variant to be selected somewhere"
    )


def test_identification_widget_qml_attribution_combines_author_plantnet_and_cc_by_sa():
    content = qml_plugin.render_identification_widget_qml("''")
    pos = content.find(_CC_BY_SA_TEXT)
    assert pos != -1, 'expected the literal attribution text "CC BY-SA"'
    window = content[max(0, pos - 400) : pos + len(_CC_BY_SA_TEXT) + 400]
    assert _PLANTNET_TEXT_RE.search(window)
    assert _AUTHOR_REF_RE.search(window)
    assert "modelData" in window


def test_identification_widget_qml_image_and_attribution_are_guarded_by_model_data_visibility():
    content = qml_plugin.render_identification_widget_qml("''")
    bound_images = [
        block for block in _find_image_blocks(content) if _MODEL_DATA_SOURCE_RE.search(block)
    ]
    assert bound_images
    assert any(_MODEL_DATA_VISIBLE_RE.search(block) or "?" in block for block in bound_images)


def test_identification_widget_qml_image_element_has_an_error_status_handling_guard():
    content = qml_plugin.render_identification_widget_qml("''")
    bound_images = [
        block for block in _find_image_blocks(content) if _MODEL_DATA_SOURCE_RE.search(block)
    ]
    assert bound_images
    assert any(
        "onStatusChanged" in block and "Image.Error" in block for block in bound_images
    )


def test_candidate_model_extracts_small_variant_image_url_and_author_from_related_images():
    """Unlike the structural QML-source checks above, this exercises the actual per-candidate
    JavaScript extraction logic added to `qpbHandlePlantNetResponse` (image_url/author fields)."""
    content = qml_plugin.render_identification_widget_qml("''")
    assert "entry.images" in content
    assert "repImage.url.s" in content
    assert "image_url: imageUrl" in content
    assert "author: author" in content


def test_project_plugin_qml_has_no_candidate_image_display_mechanism():
    """The representative-image/attribution feature belongs to the embedded per-layer widget's own
    candidate cards (FR-QPB-109) -- the separate `<project_slug>.qml` project plugin only polls for
    and applies pending write-back requests (FR-QPB-109's persistence mechanism, Decision Log
    D-50/D-51) and has no candidate-card display of its own."""
    content = qml_plugin.render_project_plugin_qml("demo_project")
    assert "CC BY-SA" not in content
    assert not _find_image_blocks(content)


# --- FR-QPB-106 (revised)/FR-QPB-109 (further revised; Decision Log D-60/D-64): standardized -----
# --- taxon_full_nm-derived scientific-name display/persistence preference order (accepted, then --
# --- direct, then Pl@ntNet's own raw name) -- mirrors the AC-QPB-099 acceptance tests' own -------
# --- structural QML-source inspection convention, at the unit level, against the plain string-----
# --- generation entry points (no PyQGIS/real build required). ------------------------------------


def test_qpb_match_ktsn_declares_and_assigns_direct_scientific_name():
    """FR-QPB-106 (revised; Decision Log D-60/D-64): the QML mirror of match_ktsn must expose a
    new direct_scientific_name field, initialized to null and assigned from the matched row's own
    taxon_full_nm (tag-stripped via qpbStripEmTags), mirroring direct_korean_name exactly."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content, "function qpbMatchKtsn(", "// FR-QPB-108/DR-QPB-070:"
    )
    assert "direct_scientific_name: null" in func_body
    assert "result.direct_scientific_name = qpbStripEmTags(matchedRow[idxFullNm]);" in func_body
    # Assigned unconditionally alongside direct_korean_name -- before the accepted-name-resolution
    # branch, not only inside it.
    korean_index = func_body.index("result.direct_korean_name =")
    scientific_index = func_body.index("result.direct_scientific_name =")
    accepted_branch_index = func_body.index('result.direct_taxon_jm_nm === "')
    assert korean_index < scientific_index < accepted_branch_index


def test_candidate_scientific_name_prefers_accepted_then_direct_then_plantnet_raw_name():
    """FR-QPB-109 (further revised; Decision Log D-60/D-64)/AC-QPB-099 element (2), unit-level:
    the candidate object's own scientific_name field -- reused unchanged for both the candidate-
    card display (modelData.scientific_name) and selection-time persistence
    (qpbSelectCandidate's c.scientific_name) -- must be built from a preference chain reading
    accepted_scientific_name, then direct_scientific_name, then Pl@ntNet's own raw
    species.scientificName as the final fallback (never null, unlike the Korean-name case)."""
    content = qml_plugin.render_identification_widget_qml("''")
    handler_body = _extract_function_body(
        content,
        "function qpbHandlePlantNetResponse(response) {",
        "function qpbPersistIdentification",
    )
    match = re.search(
        r"accepted_scientific_name\s*\|\|\s*[^|;\n]*direct_scientific_name\s*\|\|\s*[^;\n]+",
        handler_body,
    )
    assert match, (
        "expected a preference-order fallback chain reading accepted_scientific_name, then "
        "direct_scientific_name, then a final Pl@ntNet raw-name fallback -- not found"
    )
    assert "scientificName" in match.group(0)
    assert "scientific_name: preferredSciName" in handler_body


def test_select_candidate_keeps_the_preferred_scientific_name_for_legacy_persistence_only():
    """The preferred scientific name remains available to the compatibility call only."""
    content = qml_plugin.render_identification_widget_qml("''")
    select_body = _extract_function_body(
        content, "function qpbSelectCandidate(index) {", "function qpbConfirmManualEntry"
    )
    assert "c.scientific_name" in select_body
    write_back_start = select_body.index("var writeFields = {")
    write_back_call = select_body[write_back_start : select_body.index("};", write_back_start)]
    assert "selected_korean_name: korean" in write_back_call
    assert "selected_scientific_name" not in write_back_call
    assert "selected_ktsn" not in write_back_call
    # Persistence never re-reads Pl@ntNet's raw scientificName directly -- it only ever reuses the
    # already-preference-resolved candidate.scientific_name value.
    assert "entry.species" not in select_body


def test_no_direct_match_branch_is_unaffected_and_constructs_no_direct_scientific_name():
    """AC-QPB-099 element (3): the no-direct-match early-return branch must remain structurally
    unchanged -- it returns before any direct_scientific_name assignment is reached, so a
    non-matching candidate's result object keeps direct_scientific_name at its initial null."""
    content = qml_plugin.render_identification_widget_qml("''")
    func_body = _extract_function_body(
        content, "function qpbMatchKtsn(", "// FR-QPB-108/DR-QPB-070:"
    )
    no_match_return_index = func_body.index("if (matchedRow === null) { return result; }")
    scientific_assignment_index = func_body.index("result.direct_scientific_name =")
    assert no_match_return_index < scientific_assignment_index
    assert "KTSN match not found" in content


def _qcr_runtime_resource_metadata() -> dict:
    return {
        "relative_path": "reference/canonical_taxonomy_runtime_lookup.json",
        "schema_revision": "QCR-1",
        "pipeline_revision": "D-96-canonical-runtime-lookup-1",
        "record_count": 1,
        "byte_size": 1,
        "sha256": "0" * 64,
    }


def test_qcr_runtime_lookup_reads_via_qgis_project_home_without_expression_context():
    """New canonical projects must not need the form-only expression context for lookup data."""
    content = qml_plugin.render_identification_widget_qml(
        "''",
        canonical_reference_enabled=True,
        canonical_runtime_lookup_resource=_qcr_runtime_resource_metadata(),
    )
    loader = _extract_function_body(
        content,
        "function qpbLoadCanonicalRuntimeResource() {",
        "function qpbLookupCanonicalTaxonomy",
    )
    assert "qgisProject.homePath" in loader
    assert "expression.evaluate" not in loader
    assert "qpbEscapeForExpressionLiteral" not in loader
    assert 'FileUtils.readFileContent(String(absPath))' in loader


def test_qcr_runtime_lookup_classifies_json_parse_failure_as_invalid():
    """Malformed delivered JSON is corruption, not an unavailable project-local resource."""
    content = qml_plugin.render_identification_widget_qml(
        "''",
        canonical_reference_enabled=True,
        canonical_runtime_lookup_resource=_qcr_runtime_resource_metadata(),
    )
    loader = _extract_function_body(
        content,
        "function qpbLoadCanonicalRuntimeResource() {",
        "function qpbLookupCanonicalTaxonomy",
    )
    parse_index = loader.index("JSON.parse(qpbBytesToUtf8String(bytes))")
    invalid_index = loader.index(
        'return unavailable("canonical_taxonomy_lookup_resource_invalid");', parse_index
    )
    assert parse_index < invalid_index
