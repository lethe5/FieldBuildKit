"""Regression coverage for the integrated HTML-report generation contract."""

import json
import re

from qfield_builder import qml_plugin


def _standalone_report_runtime(source: str) -> str:
    scripts = []
    for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source):
        script = json.loads(match.group(1))
        if script.startswith("<script>"):
            scripts.append(script)
    return "\n".join(scripts)


def test_integrated_report_embeds_local_analytics_and_stable_column_contract():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="vegetation_mapping"
    )

    assert "gpkg_contents" in source
    assert "gpkg_geometry_columns" in source
    assert "source_table__source_field" in source
    assert "header || column.key" in source
    assert "var d3=" in source
    assert "function renderCharts()" in source
    assert all(label in source for label in ("조사지", "조사구", "조사", "관찰"))
    assert "조사대상" not in source[source.index("function renderCards") :]


def test_integrated_report_runtime_discovers_saved_key_without_emitting_it_as_ui_copy():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    start = source.index("function qpbRuntimeVworldKey()")
    end = source.index("function qpbReportOutputPath()", start)
    key_lookup = source[start:end]

    assert "customProperty" in key_lookup
    assert "customVariables" in key_lookup
    assert "mapLayersByName" in key_lookup
    assert "OpenStreetMap" in source
    assert "tileerror" in source


def test_integrated_report_collects_metadata_declared_records_and_uses_only_explicit_fallback():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="permanent_plots"
    )

    assert "SELECT table_name, data_type FROM gpkg_contents" in source
    assert "SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns" in source
    assert "qpbCollectCurrentRecords({name:String(spatialName)" in source
    assert "collection_mode: \"configured-layer-fallback\"" in source
    assert "spatial.records =" in source


def test_integrated_report_keeps_secret_and_path_fields_out_of_report_surfaces():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory", vworld_key="do-not-emit"
    )
    definition_start = source.index("readonly property var qpbReportDefinition")
    definition_end = source.index("function qpbRuntimeVworldKey", definition_start)
    definition = source[definition_start:definition_end]

    assert '"vworld_key"' not in definition
    assert "qpbIsSensitiveReportField" in source
    assert "qpbReportAttribute" in source
    assert "do-not-emit" not in source
    assert "photo_path" not in definition


def test_integrated_report_normalizes_camel_kebab_sensitive_fields_and_initializes_charts():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="vegetation_mapping"
    )
    runtime = _standalone_report_runtime(source)
    assert 'replace(/([a-z0-9])([A-Z])/g, "$1_$2")' in source
    assert "window.__QPB_RUNTIME_BASEMAP_KEY" in runtime
    assert "QPB_REPORT_DATA" in runtime
    assert (
        "renderCards();renderSummaries();renderSpecies();renderCharts();renderJoined();renderMap();"
        in runtime
    )
    assert "value:Number(s.count)||0};}),cover" in source


def test_integrated_report_uses_saved_path_sql_bridge_and_keeps_partial_tables():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="permanent_plots")

    assert "function qpbSavedGpkgPath()" in source
    assert 'typeof Qt.openDatabaseSync === "function"' in source
    assert "function qpbExecuteSql(sql, gpkgPath)" in source
    assert "성공한 공간 테이블은 유지" in source
    assert "fallback is reserved for complete direct-access failure" in source


def test_integrated_report_uses_korean_visible_basis_and_chart_provenance_validation():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="vegetation_mapping")

    assert 'qpbVisibleLabel(level,\\"__basis__\\")' in source
    assert "function qpbPopupRead" in source
    assert "function qpbPopupObservation" in source
    assert 'qpbPopupRead(source.site,\\"site\\",[\\"site_name\\"])' in source
    assert "values_and_keys_unique" in source
    assert "occurrence_source_rows" in source
    assert "chart_validation:chartValidation" in source


def test_integrated_report_visibly_discloses_semantic_collisions_and_anchor_geometry_limits():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="simple_inventory")
    runtime = _standalone_report_runtime(source)
    details_start = runtime.index("function qpbSemanticCollisionDetails")
    details_end = runtime.index("function renderJoined()", details_start)
    limitation_details = runtime[details_start:details_end]
    cards_start = runtime.index("function renderCards()")
    cards_end = runtime.index("function saveCsv()", cards_start)
    render_cards = runtime[cards_start:cards_end]

    assert "data.semantic_collision_notices||[]" in render_cards
    assert "의미가 같은 원본 열의 값 충돌" in limitation_details
    assert "원본 출처별 열에 각각 유지했습니다" in limitation_details
    assert "aria-label='의미 충돌 세부 사항'" in limitation_details
    assert "data.geometry_limitations||{}" in render_cards
    assert "지도 기준 행의 유효하지 않거나 누락된 도형" in limitation_details
    assert "Object.keys(reasonMap).sort" in limitation_details
    assert "유효한 후속 행은 계속 지도에 표시됩니다" in limitation_details
    assert "통합 표, 기록 상세, CSV, 비공간 집계에 유지됩니다" in limitation_details


def test_integrated_report_decoder_is_xy_only_and_normalizes_geometry_collections():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="vegetation_mapping")

    decoder = source[source.index("function qpbDecodeWkb") : source.index("function qpbCollectGpkgSpatialRows")]
    assert "ewkbZ" in decoder and "ewkbM" in decoder
    assert "isoDimension" in decoder
    assert "(2 + dimensions) * 8" in decoder
    assert 'type:"GeometryCollection"' in decoder
    assert "qpbNormalizeGeoJsonXY" in decoder
    assert 'return [x,y]' in decoder
    assert "polygonMembers" not in decoder


def test_integrated_report_bounds_large_geopackage_geometries_without_serializing_their_blobs():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="temporary_plots")
    collector = source[source.index("function qpbCollectGpkgSpatialRows") : source.index("function qpbInspectCurrentGpkgSpatialMetadata")]

    assert "readonly property int qpbReportFullGeometryMaxBytes: 524288" in source
    assert "function qpbGpkgEnvelopeGeoJson" in source
    assert "geometryByteLength > qpbReportFullGeometryMaxBytes" in collector
    assert 'outcome:"simplified_envelope"' in collector
    assert "length(\" + quotedGeometry + \")" in collector
    assert "substr(\" + quotedGeometry + \", 1, 40)" in collector
    assert "CASE WHEN length(\" + quotedGeometry + \") <= " in collector
    assert "__qpb_geometry_full" in collector
    assert '"SELECT * FROM " + identifier' not in collector
    assert "record._qpbRawGeometry = !hasSourceGeometry ? null" in collector
    assert "byte_size:geometryByteLength" in collector
    assert "대형 도형" in source
    assert "범위 사각형으로 단순화해 표시했습니다" in source


def test_integrated_report_invalid_xy_is_not_repaired_from_zm_and_csv_has_no_ordinates():
    source = qml_plugin.render_project_plugin_qml("demo", survey_type="vegetation_mapping")

    assert 'throw new Error("malformed coordinates")' in source
    assert 'throw new Error("non-finite coordinates")' in source
    assert 'throw new Error("out-of-range coordinates")' in source
    assert "qpbRawGeometry" in source
    scripts = [
        json.loads(match.group(1))
        for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source)
        if json.loads(match.group(1)).startswith("<script>")
    ]
    csv = "\n".join(scripts)
    assert "c.header" in csv
    save_csv = csv[csv.index("function saveCsv()") : csv.index("function qpbDrawBarChart")]
    assert "c.z" not in save_csv.lower() and "c.m" not in save_csv.lower()
