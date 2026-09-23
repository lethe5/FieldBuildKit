"""DRAFT AC-SRP-049–058 direct-observation verifier (2026-09-21).

Approved baseline plus approved iOS/QPB evidence-boundary correction verifier (approval 2026-09-18).

The approved 2026-09-17 baseline and AC-SRP-042–045 correction remain preserved; no application
code is executed.
"""
import ast
import importlib.util
import inspect
import math
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import fiona
from fiona.transform import transform

path = Path(__file__).with_name("test_survey_route_planner.py")
ast.parse(path.read_text(encoding="utf-8-sig"))
spec = importlib.util.spec_from_file_location("srp_test_design", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
coverage = set(re.findall(r"ac(\d{3})", path.read_text(encoding="utf-8-sig")))
assert {f"{i:03d}" for i in range(1, 49)} <= coverage
wire = module.vroom_response(include_arrivals=True)
route = wire["routes"][0]
arrivals = [step["arrival"] for step in route["steps"] if step["type"] == "job"]
assert arrivals == module.ETA and all(type(value) in {int, float} for value in arrivals)
assert "eta" not in route
assert all("arrival" not in step for step in module.vroom_response(include_arrivals=False)["routes"][0]["steps"])
invalid_arrivals = {}
for fault in ["iso", "partial", "negative", "nonfinite"]:
    steps = module.invalid_vroom_timing(fault)["routes"][0]["steps"]
    invalid_arrivals[fault] = [step.get("arrival") for step in steps if step["type"] == "job"]
assert isinstance(invalid_arrivals["iso"][0], str)
assert invalid_arrivals["partial"][-1] is None
assert invalid_arrivals["negative"][0] < 0
assert not math.isfinite(invalid_arrivals["nonfinite"][0])
assert module.PORTABLE_SETTINGS["backend"] == "ors-vroom"
assert module.PORTABLE_SETTINGS["max_road_offset_m"] == 50
assert module.PORTABLE_SETTINGS["max_access_distance_m"] == 2000
assert "key" not in module.PORTABLE_SETTINGS
assert module.HOSTED_ROUTING_BASE == "https://api.heigit.org/openrouteservice"
assert module.HOSTED_OPTIMIZER_URL == "https://api.heigit.org/vroom/v0"
assert module.LEGACY_ROUTING_BASE not in {module.HOSTED_ROUTING_BASE, module.HOSTED_OPTIMIZER_URL}
evaluator = module.QFIELD_EXPRESSION_EVALUATOR
assert evaluator["native_type"] == "QfExpressionEvaluator"
assert evaluator["qml_type"] == "ExpressionEvaluator"
assert {"expressionText", "feature", "layer", "project"} <= set(evaluator["writable_properties"])
assert evaluator["evaluate_arities"] == [0, 1]
assert evaluator["allow_dynamic_properties"] is False
source = path.read_text(encoding="utf-8-sig")
assert 'operation="remaining"' not in source
assert "remaining_recalculation_is_superseded" in source
assert all(case in source for case in ["M01_project_dropdowns_layout", "M02_schema2_live_route",
                                       "M03_offline_storage_toggle", "M04_completion_progression_overlays",
                                       "M05_naver_android_ios", "M06_geometry_regression",
                                       "M07_qfield_ors_point", "M08_qfield_ors_line",
                                       "M09_qfield_ors_polygon", "M10_followup_panel_device",
                                       "M11_android_route_name_soft_keyboard",
                                       "M12_ios_route_name_soft_keyboard",
                                       "M13_qfield_eight_floating_labels",
                                       "M14_qfield_six_geometry_labels",
                                       "M15_ios_light_dark_contrast_matrix",
                                       "M16_ios_header_spacing_and_tap_regions",
                                       "M17_ios_local_date_name_lifecycle"])
assert module.canonical_naver_query("조사지 A & B/#?") == (
    "navigation?dlat=37.456&dlng=127.123&dname="
    + quote("조사지 A & B/#?", safe="") + "&appname=ch.opengis.qfield")
assert module.canonical_naver_android_intent("조사지 A & B/#?") == (
    "intent://navigation?dlat=37.456&dlng=127.123&dname="
    + quote("조사지 A & B/#?", safe="")
    + "&appname=ch.opengis.qfield#Intent;scheme=nmap;action=android.intent.action.VIEW;"
      "category=android.intent.category.BROWSABLE;package=com.nhn.android.nmap;end")
assert module.NAVER_ANDROID_STORE == "market://details?id=com.nhn.android.nmap"
for roundtrip, count in [(False, 3), (True, 4)]:
    response = module.schema2_directions_response(roundtrip=roundtrip)
    feature = response["features"][0]
    assert len(feature["properties"]["segments"]) == count
    assert feature["properties"]["way_points"] == module.SCHEMA2_WAY_POINTS[:count + 1]
    assert all("way_points" not in segment for segment in feature["properties"]["segments"])
    assert len(feature["geometry"]["coordinates"]) == module.SCHEMA2_WAY_POINTS[count] + 1
    assert feature["properties"]["summary"]["distance"] == sum(module.SCHEMA2_DISTANCES[:count])
    assert feature["properties"]["summary"]["duration"] == sum(module.SCHEMA2_DURATIONS[:count])
schema2_fault_paths = {
    "missing_leg": "features[0].properties.segments[1]",
    "out_of_order_leg": "features[0].properties.way_points[2]",
    "negative_leg": "features[0].properties.segments[1].distance",
    "nonfinite_leg": "features[0].properties.segments[1].duration",
    "invalid_leg_geometry": "features[0].geometry.type",
    "non_wgs84_leg": "features[0].geometry.coordinates[3]",
    "mismatched_leg_count": "features[0].properties.way_points",
}
for fault, expected_path in schema2_fault_paths.items():
    response, actual_path = module.malformed_schema2_directions(fault)
    assert actual_path == expected_path
    assert all("way_points" not in segment
               for segment in response["features"][0]["properties"]["segments"])
    assert module.payload_sha256(response)
assert "fault=fault" not in inspect.getsource(module.test_ac026_invalid_schema2_leg_preserves_existing_route)
assert module.DIRECTIONS_RESPONSE["features"][0]["properties"]["way_points"] == [0, 1, 2, 3, 4]
assert all("way_points" not in segment
           for segment in module.DIRECTIONS_RESPONSE["features"][0]["properties"]["segments"])
for fault, _ in [
    ("missing_order", "0"), ("duplicate_order", "2"), ("unknown_order", "99"),
    ("unassigned_order", "0"), ("missing_way_points", "way_points"),
    ("duplicate_waypoint_index", "2"), ("invalid_waypoint_index", "19"),
    ("missing_segment", "4"), ("invalid_geometry", "geometry"),
    ("invalid_metric", "2"), ("total_tolerance", "distance"),
]:
    optimizer, directions = module.malformed_provider_payload(fault)
    assert optimizer != module.vroom_response(include_arrivals=True) or directions != module.schema2_directions_response(roundtrip=True)
legacy = module.schema2_legacy_document()
assert legacy["schema"] == 1 and legacy["routes"][0]["revision"] == 7
assert "legs" not in legacy["routes"][0]
assert [layer["layer_id"] for layer in module.PROJECT_LAYERS] == [
    "duplicate-a", module.SITE_LAYER_ID, "duplicate-b"]
assert module.PROJECT_LAYERS[2]["fields"][-2:] == ["SECOND_ID", "SECOND_NAME"]
assert all(text in source for text in ["계산 대상", "출발지", "저장할 경로 이름",
                                       "저장 경로 불러오기",
                                       "방문 순서대로 이동하고, 조사를 마친 지점을 체크하세요.",
                                       "조사지", "조사지 ID 필드", "조사지 이름 필드",
                                       "조사 완료 필드", "현재 선택한 조사지: {count}개",
                                       "#1565C0", "사용 불가", "복귀 포함"])
assert module.AC031_FLOATING_LABEL_SUBSET == {
    "scope": "계산 대상", "start": "출발지", "layer": "조사지",
    "id_field": "조사지 ID 필드", "name_field": "조사지 이름 필드",
    "completion_field": "조사 완료 필드",
}
assert module.FOLLOWUP_FLOATING_LABELS == {
    "layer": "조사지", "id_field": "조사지 ID 필드", "name_field": "조사지 이름 필드",
    "completion_field": "조사 완료 필드", "scope": "계산 대상", "start": "출발지",
    "route_name": "저장할 경로 이름",
}
assert module.FINAL_FLOATING_LABELS == {
    **module.FOLLOWUP_FLOATING_LABELS,
    "saved_route": "저장 경로 불러오기",
}
assert set(module.AC031_FLOATING_LABEL_SUBSET) < set(module.FINAL_FLOATING_LABELS)
assert len(module.AC031_FLOATING_LABEL_SUBSET) == 6 and len(module.FINAL_FLOATING_LABELS) == 8
assert module.WORKFLOW_LABELS == {
    "scope": "계산 대상", "start": "출발지", "saved_route": "저장 경로 불러오기",
}
assert module.WORKFLOW_LABELS["saved_route"] != "저장 경로 이름"
assert module.FINAL_FLOATING_LABELS["route_name"] == "저장할 경로 이름"
assert module.STEP7_ROUTE_KEY_COPY == {
    "title": "ORS API 키 (선택)",
    "purpose": "조사 경로를 도로망에 맞춰 계산하고 조사지 방문 순서를 정할 때 사용합니다.",
    "blank_behavior": (
        "입력하지 않아도 프로젝트는 만들 수 있습니다. 다만 기본 ORS/HeiGIT 서비스로 경로를 "
        "계산하려면 QField를 열 때마다 키를 입력해야 합니다. 키가 필요 없는 자체 서버를 사용하는 "
        "경우에는 입력하지 않아도 됩니다."
    ),
    "plaintext_warning": (
        "동의하면 QField가 자동으로 사용하도록 키가 프로젝트 파일에 암호화되지 않은 글자로 "
        "저장됩니다. 프로젝트 폴더를 열 수 있는 사람은 누구나 키를 확인하고 사용할 수 있습니다. "
        "동의하지 않으면 프로젝트에 키를 넣지 않으며, QField를 열 때마다 직접 입력해야 합니다."
    ),
    "consent": "위 내용에 동의합니다",
    "remember": "이 키 기억하기 (이 컴퓨터에 암호화하여 저장됨)",
}
assert module.false_xml_flag("0") and module.false_xml_flag("false")
assert not module.false_xml_flag("1") and not module.false_xml_flag("true")
assert module.expected_site_label_expression(name_field_present=True) == (
    '''CASE WHEN trim(coalesce(to_string("display_name"), '')) <> '' THEN trim(to_string("display_name")) '''
    '''WHEN trim(coalesce(to_string("site_id"), '')) <> '' THEN trim(to_string("site_id")) ELSE NULL END'''
)
assert module.expected_site_label_expression(name_field_present=False) == (
    '''CASE WHEN trim(coalesce(to_string("site_id"), '')) <> '' THEN trim(to_string("site_id")) ELSE NULL END'''
)
assert all(operation in source for operation in [
    'operation="candidate_name_save"', 'operation="followup_panel_ui"',
    'operation="settings_disclosure"', 'operation="settings_key_provenance"',
    'operation="settings_snapshot_save"',
    'operation="ordered_completion_checklist"', 'operation="generated_site_style"',
    'operation="route_name_text_input_proxy"', 'operation="final_floating_label_geometry"',
    'operation="generated_site_label_contract"', 'operation="builder_step7_route_credentials"',
    'operation="builder_route_credentials_boundary"',
])
assert all(token in source for token in [
    '"evidence_source"] == "loaded_generated_qml_object_tree"',
    '"generated_artifact_provenance"', '"project_variable_read_from_qgs"',
    '"candidate_after_calculation"', '"snapshot_after"] == r["snapshot_before"',
    '"state_text"] == "순서 밖 완료"', '"inert_text"] is True',
])
assert 'scope="all", targets=' in inspect.getsource(module.test_ac022_ac024_labels_guidance_and_conditional_controls)
ac019_source = inspect.getsource(module.test_ac019_builder_key_consent_embeds_only_project_variable)
assert '"warning_disclosures"' not in ac019_source
assert 'observed["route_key_plaintext_warning"]["text"]' in ac019_source
assert 'STEP7_ROUTE_KEY_COPY["plaintext_warning"]' in ac019_source
assert all(fragment in ac019_source for fragment in [
    "암호화되지 않은 글자", "확인하고 사용할", "QField가 자동으로 사용하도록",
])
assert all(old_fragment not in ac019_source for old_fragment in [
    '"평문" in warning', "읽고 사용할", "암호화되지 않습니다", '"QField", "자동 사용"',
])
ac031_source = inspect.getsource(module.test_ac031_six_selectors_use_ors_floating_labels_without_collision)
assert "AC031_FLOATING_LABEL_SUBSET" in ac031_source and "FINAL_FLOATING_LABELS" in ac031_source
assert 'row["text"] in AC031_FLOATING_LABEL_SUBSET.values()' in ac031_source
assert 'selector["label_in_control"] is True' not in ac031_source
assert 'selector["label_clipped"]' not in ac031_source
assert 'selector["validation_text_rect"]' not in ac031_source
assert 'control["visible"] is (semantic_id != "settings")' in inspect.getsource(module.test_ac001_generated_plugin)
assert 'completed_ids=["0", "1"]' in inspect.getsource(module.test_ac010_completion)
assert "canonical_naver_android_intent" in inspect.getsource(module.test_ac012_road_and_naver)
assert "canonical_naver_android_intent" in inspect.getsource(module.test_ac025_exact_encoded_android_intent_and_honest_qt_true)
assert "blocked_later == initial" in inspect.getsource(
    module.test_ac027_ordered_completion_then_uncheck_creates_out_of_order_gap_and_roundtrip_return)
assert all(token in source for token in [
    '"control_objects"', '"object_identity_source"', '"seed_saved_provenance"',
    '"loaded_generated_qml_object_tree"', '"style_metrics"', '"accessibility"',
    '"candidate_model_capture"', '"preflight_capture"', '"rendered_scope_rows"',
    '"visible_layout_semantic_ids"', '"canvas_marker_count"', '"canvas_markers"',
    '"write_capture"', '"route_seed_provenance"', '"fault_provenance"',
    '"generated_geometry_provenance"', '"materialized_source_path"',
    '"generated_gpkg_path"', '"generated_project_path"',
    '"accepts_input_method"] is True', '"os_soft_keyboard_opened") is not True',
    '"focus_recovery_api_invocations"] == []', '"label_notch_overlap"',
    '"top_outline_observation"', '"live_background_border_geometry"',
    '"stored_values_observation_after"', '"live_validation_object_geometry"',
    'read_qgs_labeling(qgs_path', '"artifact_post_edits"] == []',
    'false_xml_flag(config["rendering"].get("mergeLines"))', '"ID-LINK-A"', '"ID-LINK-B"',
    '"expression_evaluator"] == "QgsExpression"', '"runtime_claims"] == []',
    '"qfield_device_label_rendered") is not True',
    '"test_output_secret_redacted"] is True',
    '"desktop_retention_readback"] ==',
])
assert all(forbidden not in source for forbidden in [
    '"floating_label_visual"', '"marker_source_writes"', '"marker_route_writes"',
    '"scope_following_row_gaps"', '"preflight_candidate_ids"',
    '"painted_control_outline_geometry"',
    'operation="route_panel_theme_contrast_proxy"',
    'operation="route_panel_theme_switch_proxy"',
    'operation="route_panel_header_spacing_proxy"',
    'operation="route_name_local_date_lifecycle"',
    'operation="generated_site_tabler_exclusion"',
])
assert '"geom_to_geojson" not in expression' in source
assert all(token in source for token in ['"centroid" in expression', '"transform" in expression',
                                         '"x(" in expression', '"y(" in expression'])
for kind, center in module.CENTROIDS.items():
    x, y = center[0] * 100000 + 1000000, center[1] * 100000 + 5000000
    lon, lat = transform("EPSG:3857", "EPSG:4326", [x], [y])
    oracle = [math.degrees(x / 6378137), math.degrees(2 * math.atan(math.exp(y / 6378137)) - math.pi / 2)]
    assert [lon[0], lat[0]] == module.pytest.approx(oracle, abs=1e-7)
lon, lat = transform("EPSG:5186", "EPSG:4326", [200000], [600000])
assert [lon[0], lat[0]] == module.pytest.approx([127, 38], abs=1e-7)


class FixtureChecked(Exception):
    pass


count = 0
for fmt in ["SHP", "ZIP", "GPKG"]:
    for kind, source in module.GEOMETRIES.items():
        def inspect_source(**case):
            uri = "zip://" + case["source"] if fmt == "ZIP" else case["source"]
            with fiona.open(uri) as layer:
                rows = list(layer)
            assert len(rows) == 2
            assert all(module.geometry_signature(row["geometry"]) == module.geometry_signature(module.GEOJSON[kind]) for row in rows)
            raise FixtureChecked
        with tempfile.TemporaryDirectory() as directory:
            try:
                module.test_ac015_ac016_uploaded_geometry(inspect_source, Path(directory), fmt, kind)
            except FixtureChecked:
                count += 1
assert count == 18
print("Design checks: approved AC001-045 history preserved; approved AC046-048/QPB149-150 correction "
      "uses bounded structure/controller/builder/symbol boundaries; superseded operations are absent; "
      "M01-M17 remain NOT RUN. No application tests executed.")

# DRAFT AC-SRP-049–058 direct-observation design checks.
test_source = path.read_text(encoding="utf-8-sig")
coverage = set(re.findall(r"ac(\d{3})", test_source))
assert {f"{i:03d}" for i in range(1, 59)} <= coverage
for required in (
    "_direct_node", "_route_http", "_provider_responder",
    "_is_origin_validation_matrix", "_is_vehicle_matrix",
    "test_ac049_http_failure_preserves_actual_stage_status_and_stops",
    "test_ac050_single_batched_snap_uses_original_coordinates_and_exact_radius",
    "test_ac050_origin_validation_is_explicit_1x1_and_resolved_coordinates_are_validation_only",
    "test_ac050_invalid_origin_1x1_response_stops_with_actionable_start_error",
    "test_ac051_actual_backend_emits_roundtrip_walking_contract",
    "test_ac052_ac057_production_save_roundtrips_schema3_and_preserves_legacy",
    "test_ac053_qml_runtime_reads_real_tree_repeater_and_qaccessible",
    "test_ac054_actual_http_sequence_and_privacy_boundary",
    "test_ac039_ac055_navigation_open_direct_spy",
    "test_ac056_three_allowed_combinations_roundtrip_active_and_inactive",
    "test_ac056_corrupt_visit_recovery_preserves_bytes_and_last_good",
    "test_ac057_variant_corruption_recovery_is_atomic",
    "test_ac057_schema3_rejects_schema1_marker_with_schema2_legs_and_preserves_bytes",
    "test_ac058_toggle_persists_exact_setting_through_restart_and_folder_move",
):
    assert required in test_source
assert all(name in test_source for name in (
    "M18_live_ors_mixed_route", "M19_mixed_route_visual_accessibility",
    "M20_ios_apple_maps_handoff", "M21_android_naver_regression",
))
assert "ThreadingHTTPServer" in test_source
origin_success_source = inspect.getsource(
    module.test_ac050_origin_validation_is_explicit_1x1_and_resolved_coordinates_are_validation_only)
assert all(token in origin_success_source for token in (
    '"locations": [MIXED_START, MIXED_START]', '"sources": [0]', '"destinations": [1]',
    '"metrics": ["duration"]', '"resolve_locations": True',
    'access_snap["body"] == {"locations": [MIXED_SOURCE], "radius": 2000}',
    'route["start"] == MIXED_START', 'route["visits"][0]["source_coordinate"] == MIXED_SOURCE',
))
origin_failure_source = inspect.getsource(
    module.test_ac050_invalid_origin_1x1_response_stops_with_actionable_start_error)
assert all(token in origin_failure_source for token in (
    '"unresolved_source"', '"unresolved_destination"', '"null_duration"',
    '"invalid_duration"', '["map_start", "saved_start"]',
    '["/v2/matrix/driving-car"]',
))
origin_selector_source = inspect.getsource(module._is_origin_validation_matrix)
assert all(token in origin_selector_source for token in (
    'body.get("sources") == [0]', 'body.get("destinations") == [1]',
    'len(locations) == 2', 'locations[0] == locations[1]',
))
vehicle_selector_source = inspect.getsource(module._is_vehicle_matrix)
assert all(token in vehicle_selector_source for token in (
    'body.get("locations") == [MIXED_START, MIXED_ACCESS]',
    '"sources" not in body', '"destinations" not in body',
))
assert not re.search(r'len\([^\n]*locations[^\n]*\)\s*(?:==|>)\s*1', test_source)
assert 'fs.readFileSync(input.modules[name],"utf8")' in test_source
assert "repository.checksum(payload)" in test_source
assert "navigation.open(stop,opener" in test_source
assert "QAccessible.queryAccessibleInterface" in test_source
assert "Repeater.itemAt(index)" in test_source
assert module.AC056_ALLOWED_MODE_SOURCES == {
    ("mapped", "ors-foot-hiking"),
    ("exact_zero", "exact_zero"),
    ("unmapped_estimate", "straight_line_lower_bound_m"),
}
assert len(module.AC056_VISIT_CORRUPTIONS) == 16
assert {(kind, field) for kind, field, _ in module.AC056_VISIT_CORRUPTIONS} >= {
    ("missing", "layer_id"), ("blank", "layer_id"),
    ("missing", "site_id"), ("blank", "site_id"),
    ("missing", "metric_source"), ("blank", "metric_source"),
    ("identity_mismatch", "layer_id"), ("identity_mismatch", "site_id"),
    ("unknown", "walking_mode"), ("unknown", "metric_source"),
}
assert sum(kind == "disallowed_pair"
           for kind, _, _ in module.AC056_VISIT_CORRUPTIONS) == 6
ac053_source = inspect.getsource(module.test_ac053_qml_runtime_reads_real_tree_repeater_and_qaccessible)
assert all(token in ac053_source for token in (
    'result["passive_boundary_observation"]', 'boundary["provider_attempts"]',
    'boundary["storage_write_attempts"]', 'boundary["action_windows"]',
    'window["provider_attempt_count_before"]',
    'window["provider_attempt_count_after"]',
    'window["storage_write_attempt_count_before"]',
    'window["storage_write_attempt_count_after"]',
    'window["product_operation_completed"] is True',
))
assert 'observed["provider_requests"] == []' not in ac053_source
assert 'passive_write_observers' not in ac053_source
ac057_schema1_legs_source = inspect.getsource(
    module.test_ac057_schema3_rejects_schema1_marker_with_schema2_legs_and_preserves_bytes)
assert 'good["schema"] == 3' in ac057_schema1_legs_source
assert 'legacy["route_schema"] = 1' in ac057_schema1_legs_source
assert '"legs" in legacy' in ac057_schema1_legs_source
assert all(token in ac057_schema1_legs_source for token in (
    'recovered["corrupt_bytes_after"] == recovered["corrupt_bytes_before"]',
    'recovered["last_good_bytes_after"] == recovered["last_good_bytes_before"]',
    'recovered["repository_writes_during_load"] == 0',
    'recovered["provider_request_attempts"] == 0',
))
for production_name in ("backend.js", "controller.js", "repository.js", "navigation.js"):
    production = path.parents[3] / "qfield_builder" / "qfield_routes" / production_name
    production_source = production.read_text(encoding="utf-8")
    assert "SRP_DIRECT_SYNTHETIC_SECRET" not in production_source
    assert not re.search(r"\b(?:testOnly|acceptanceOnly)\b", production_source)
print("survey route AC049-058 direct-observation design verified")

# APPROVED AC-SRP-059 baseline and reviewer correction checks (approval 2026-09-22).
test_source = path.read_text(encoding="utf-8-sig")
coverage = set(re.findall(r"ac(\d{3})", test_source))
assert {f"{i:03d}" for i in range(1, 61)} <= coverage
for required in (
    "SNAPPED_PROVIDER_GEOMETRY", "ENDPOINT_GAP_DISCLOSURE",
    "test_ac059_snapped_provider_geometry_is_mapped_without_connector_or_gap_metric",
    "test_ac059_schema3_active_inactive_restart_offline_move_exact_roundtrip",
    "test_ac059_malformed_walking_contract_stops_before_vehicle_write_and_preserves_last_good",
    "test_ac059_qml_observes_current_requested_markers_provider_line_and_one_gap_detail",
):
    assert required in test_source
valid = module._snapped_walking_response()
feature = valid["features"][0]
assert valid["type"] == "FeatureCollection"
assert len(valid["features"]) == 1
assert feature["type"] == "Feature"
assert feature["geometry"] == module.SNAPPED_PROVIDER_GEOMETRY
assert all(len(coordinate) == 2 and all(math.isfinite(value) for value in coordinate)
           and abs(coordinate[0]) <= 180 and abs(coordinate[1]) <= 90
           for coordinate in feature["geometry"]["coordinates"])
assert feature["properties"]["way_points"] == [0, 2]
assert len(feature["properties"]["segments"]) == 1
assert module._geodesic_m(feature["geometry"]["coordinates"][0], module.MIXED_ACCESS) > 1
assert module._geodesic_m(feature["geometry"]["coordinates"][-1], module.MIXED_SOURCE) > 1
assert module.SNAPPED_DISTANCE_M < module._geodesic_m(module.MIXED_ACCESS, module.MIXED_SOURCE)
faults = {
    "missing_way_points", "non_array_way_points", "wrong_length_way_points",
    "non_integer_way_points", "non_increasing_way_points", "non_covering_start",
    "non_covering_end", "multiple_segments", "multiple_features", "invalid_geometry",
    "features_object_array_like",
    "invalid_summary", "invalid_segment", "distance_tolerance_mismatch",
    "duration_tolerance_mismatch",
}
for fault in faults:
    assert module._invalid_snapped_response(fault) != valid
positive_source = inspect.getsource(
    module.test_ac059_snapped_provider_geometry_is_mapped_without_connector_or_gap_metric)
assert all(token in positive_source for token in (
    'visit["walking_mode"] == "mapped"', 'visit["metric_source"] == "ors-foot-hiking"',
    'visit["access_coordinate"] == MIXED_ACCESS', 'visit["source_coordinate"] == MIXED_SOURCE',
    '"geometry": SNAPPED_PROVIDER_GEOMETRY', 'list(reversed(SNAPPED_PROVIDER_GEOMETRY["coordinates"]))',
))
negative_source = inspect.getsource(
    module.test_ac059_malformed_walking_contract_stops_before_vehicle_write_and_preserves_last_good)
assert all(token in negative_source for token in (
    'observed["snapshot_after"] == observed["snapshot_before"]',
    'observed["candidate_after"] == observed["candidate_before"]',
    'observed["writeAttempts"] == observed["writeSuccesses"] == 0',
    '"/v2/directions/foot-hiking/geojson"',
))
qml_source = inspect.getsource(
    module.test_ac059_qml_observes_current_requested_markers_provider_line_and_one_gap_detail)
assert all(token in qml_source for token in (
    'observed["current_presentation"]',
    'endpoint["access_marker_observations"]',
    'endpoint["source_feature_observations"]',
    'endpoint["walking_line_observations"]',
    'endpoint["visit_model_observation"]',
    'endpoint["walking_totals_observation"]',
    'connector_lines == []',
    'gap_metric_or_duration == (0, 0)',
    'endpoint["source_coordinate_write_attempts"] == []',
    'endpoint["endpoint_gap_details"] == [{',
    '"accessible_name": ENDPOINT_GAP_DISCLOSURE',
    '"inside_details": True',
))
driver_source = (path.parent / "route_ui_simplification_qml_driver.py").read_text(
    encoding="utf-8-sig")
assert "'synthetic_connector_count':0" not in driver_source
assert "'gap_metric_or_duration_count':0" not in driver_source
assert all(token in driver_source for token in (
    "'access_marker_observations'", "'source_feature_observations'",
    "'walking_line_observations'", "'visit_model_observation'",
    "'walking_totals_observation'", "getCppPointer(",
    "object_value(", "current_fixture_rows()",
))
assert '"way_points": [0, 1]' in inspect.getsource(module._provider_responder)
print("survey route AC059 reviewer correction verified; M01-M21 remain NOT RUN")

for required in (
    "_one_point_zero_walking_response",
    "test_ac060_one_point_zero_route_reuses_existing_unmapped_contract",
    "test_ac060_ac063_one_point_zero_route_saves_without_unmapped_acknowledgement",
    "test_ac060_invalid_degenerate_variants_fail_atomically_without_fallback",
):
    assert required in test_source
one_point = module._one_point_zero_walking_response()
one_feature = one_point["features"][0]
assert one_feature["geometry"]["type"] == "LineString"
assert len(one_feature["geometry"]["coordinates"]) == 1
assert one_feature["properties"] == {
    "summary": {"distance": 0, "duration": 0},
    "segments": [{"distance": 0, "duration": 0}],
    "way_points": [0, 0],
}
ac060_faults = {
    "nonzero_summary_distance", "nonzero_segment_duration",
    "missing_summary_duration", "nonnumeric_segment_distance", "bad_way_points",
    "zero_coordinates", "two_coordinates_zero_way_points", "multiple_segments",
    "multiple_features",
}
assert all(module._invalid_one_point_response(fault) != one_point for fault in ac060_faults)
positive_ac060 = inspect.getsource(
    module.test_ac060_one_point_zero_route_reuses_existing_unmapped_contract)
assert all(token in positive_ac060 for token in (
    'visit["walking_mode"] == "unmapped_estimate"',
    'visit["metric_source"] == "straight_line_lower_bound_m"',
    'visit["access_coordinate"] == MIXED_ACCESS',
    'visit["source_coordinate"] == MIXED_SOURCE',
    'observed["result"]["combined_totals"] is None',
))
negative_ac060 = inspect.getsource(
    module.test_ac060_invalid_degenerate_variants_fail_atomically_without_fallback)
assert all(token in negative_ac060 for token in (
    'observed["snapshot_after"] == observed["snapshot_before"]',
    'observed["candidate_after"] == observed["candidate_before"]',
    'observed["writeAttempts"] == observed["writeSuccesses"] == 0',
))
print("survey route AC060 one-point fallback design verified; implementation expected RED")

assert {"061", "062"} <= coverage
for slot in (
    "origin_source", "origin_destination", "vehicle_source_0", "vehicle_source_1",
):
    origin, vehicle = module._matrix_location_responses(slot, module._MISSING_DIAGNOSTIC)
    rows = {
        "origin_source": origin["sources"][0],
        "origin_destination": origin["destinations"][0],
        "vehicle_source_0": vehicle["sources"][0],
        "vehicle_source_1": vehicle["sources"][1],
    }
    assert "snapped_distance" not in rows[slot]
    assert sum("snapped_distance" in row for row in (
        origin["sources"][0], origin["destinations"][0], *vehicle["sources"])) == 3
origin, vehicle = module._matrix_location_responses(
    "vehicle_source_1", module._NONFINITE_JSON_NUMBER)
assert isinstance(vehicle, str) and "1e309" in vehicle and "Infinity" not in vehicle
ac061_negative = inspect.getsource(
    module.test_ac061_present_invalid_snapped_distance_fails_at_its_stage_and_preserves_state)
assert all(token in ac061_negative for token in (
    'observed["snapshot_after"] == observed["snapshot_before"]',
    'observed["candidate_after"] == observed["candidate_before"]',
    'observed["writeAttempts"] == observed["writeSuccesses"] == 0',
    'not any(record["path"] == "/optimizer"',
))
assert "(1000, True), (1000.01, False)" in test_source
assert all(fault in test_source for fault in (
    "origin_sources_cardinality", "origin_destinations_object", "origin_location",
    "origin_duration", "vehicle_sources_cardinality", "vehicle_sources_object",
    "vehicle_duration", "vehicle_distance",
))

ac062_platform = inspect.getsource(
    module.test_ac062_canonical_platform_store_shares_three_keys_and_ignores_siblings)
assert all(token in ac062_platform for token in (
    'root / "FieldBuild Standalone"', 'root / "FieldBuild Kit"',
    'root / "QField Project Builder"', 'get_remembered_key()',
    'get_remembered_plantnet_key()', 'get_remembered_route_key()',
    '[_directory_snapshot(path) for path in siblings] == sibling_before',
))
ac062_nonretained = inspect.getsource(
    module.test_ac062_nonretained_branches_build_without_store_or_plaintext_fallback)
assert all(token in ac062_nonretained for token in (
    'result["success"] is True', 'not credential_store.credentials_file_path().exists()',
    'not any(path.name == "credentials.enc"',
    'not any(_ROUTE_CREDENTIAL.encode() in path.read_bytes()',
    '[_directory_snapshot(path) for path in siblings] == sibling_before',
))
ac062_ui = inspect.getsource(
    module.test_ac062_remembered_route_key_is_not_copied_or_exposed_by_builder_ui)
assert all(token in ac062_ui for token in (
    'observed["key_input_echo_mode"] == "password"',
    '"summary", "logs", "errors", "reports", "message", "qml_errors", "diagnostics"',
    'str(credential_path) not in serialized',
    'observed["remembered_key_available_to_qfield"] is False',
))
print("survey route AC061-062 matrix/credential-store design verified; no real app-data used")

# APPROVED AC-SRP-066 reconciliation (approval 2026-09-22): exact UI, focus and ordering observations.
assert {"063", "064", "065", "066"} <= coverage
ac051_save = inspect.getsource(
    module.test_ac051_ac063_unmapped_save_needs_no_acknowledgement_and_keeps_null_totals)
ac060_save = inspect.getsource(
    module.test_ac060_ac063_one_point_zero_route_saves_without_unmapped_acknowledgement)
assert "acknowledge_unmapped" not in ac051_save + ac060_save
assert 'accepted["saved"] is True' in ac051_save + ac060_save

ac063 = inspect.getsource(
    module.test_ac063_mixed_result_has_one_notice_no_ack_and_default_collapsed_details)
assert all(token in ac063 for token in (
    'observed["acknowledgement_control_count"] == 0',
    'observed["fallback_notice_screen_count"] == 1',
    'len(observed["fallback_notice_accessible"]) == 1',
    'observed["details_before"]["expanded"] is False',
    'observed["endpoint_gap_default_visible_count"] == 0',
    'observed["endpoint_gap_expanded_count"] == 1',
    'observed["endpoint_gap_inside_details"] == [True]',
    'observed["candidate_after_toggle"] == observed["candidate_before"]',
    'observed["payload_after_toggle"] == observed["payload_before"]',
    'observed["request_count_after_toggle"] == observed["request_count_before_toggle"]',
    'observed["write_count_after_toggle"] == observed["write_count_before_toggle"]',
    'saved["save_ok"] is True',
))
ac064 = inspect.getsource(
    module.test_ac064_ac066_every_save_outcome_is_visible_once_and_preserves_required_state)
assert all(token in ac064 for token in (
    'observed["status_viewport_before"]["outside"] is True',
    'observed["status_viewport_after"]["fully_visible"] is True',
    'len(observed["announcement_proxy_matches"]) == 1',
    'observed["provider_request_count_after"] == observed["provider_request_count_before"]',
    'observed["candidate_after"] == observed["candidate_before"]',
    'observed["document_after"] == observed["document_before"]',
    'observed["persisted_revision_after"] == observed["persisted_revision_before"]',
    'observed["last_good_bytes_unchanged"] is True',
    'observed["app_focus_recovery_api_occurrences"] == 0',
    'observed["save_enabled_immediate"] is False',
    'focus["object_name"] == "" and focus["focusable_control"] is None',
    'observed["focus_after"]["object_name"] == "saveRouteButton"',
    'semantic["visual_order"] == semantic["expected_order"]',
    'semantic["accessibility_order"] == semantic["expected_order"]',
    'observed["keyboard_traversal"] == [',
))
assert all(outcome in test_source for outcome in (
    '"success"', '"blank_name"', '"stale_input"', '"revision_conflict"',
    '"write_false"', '"readback_mismatch"', '"exception"',
))

qml_driver = (path.parent / "route_ui_simplification_qml_driver.py").read_text(
    encoding="utf-8-sig")
assert all(token in qml_driver for token in (
    "operation set changed", "branch marker changed", "QTest.mouseClick",
    "fallbackNotice", "routeDetailsDisclosure", "routeDetailsContent", "saveStatus",
    "acknowledgement_control_count", "endpoint_gap_inside_details",
    "status_viewport_before", "announcement_proxy_matches", "last_good_bytes_unchanged",
    "save_enabled_immediate", "focus_after_platform_clear", "focus_transitions",
    "focusable_control", "place_outside_view", "settle_render_geometry",
    "app_focus_recovery_api_occurrences", "keyboard_traversal", "semantic_order",
    "current_presentation",
))
assert qml_driver.count("current_y=float(flickable.property('contentY') or 0)") == 1
assert qml_driver.count(
    "max(0,current_y+within.y()-flickable.height()/2+item.height()/2)") == 1
assert "max(0,within.y()-flickable.height()/2+item.height()/2)" not in qml_driver
assert "067" in coverage
assert "calculation_controls" in qml_driver
assert "fault_stage" in qml_driver and "origin_http_failure" in qml_driver
ac067 = inspect.getsource(
    module.test_ac067_origin_validation_http_403_is_actionable_redacted_and_atomic)
assert all(token in ac067 for token in (
    '"origin-validation"', '"HTTP 403"', 'observed["request_count_after_failure"] == 1',
    'observed["write_count_after_failure"] == 0',
    'observed["candidate_after"] == observed["candidate_before"]',
    'observed["document_after"] == observed["document_before"]',
    'observed["route_files_after"] == observed["route_files_before"]',
    'secret not in normal', '"Authorization" not in normal', '"api_key=" not in normal',
))
assert "acknowledgeUnmapped(" not in qml_driver
assert not (path.parent / "unmapped_save_qml_driver.py").exists()

ac059 = inspect.getsource(
    module.test_ac059_qml_observes_current_requested_markers_provider_line_and_one_gap_detail)
assert all(token in ac059 for token in (
    'endpoint["access_marker_observations"]',
    'endpoint["source_feature_observations"]',
    'endpoint["walking_line_observations"]',
    'endpoint["walking_totals_observation"]',
    'endpoint["endpoint_gap_details"] == [{',
    '"inside_details": True',
))
assert "endpoint_gap_disclosures" not in ac059

ac065 = inspect.getsource(
    module.test_ac065_fresh_build_bundles_current_runtime_and_never_updates_existing_project)
assert all(token in ac065 for token in (
    '_tree_bytes(new_project / "qfield_routes") == _tree_bytes(source_runtime)',
    '_tree_bytes(preexisting) == before',
    'splitlines().count(BUILD_RUNTIME_DISCLOSURE) == 1',
))
manual = inspect.getsource(module.test_ac063_ac064_ac065_ac066_target_qfield_handoff_is_user_run_and_unverified)
assert "pytest.skip" in manual and "미검증" in manual and "target QField" in manual
print("survey route AC066 approved reconciliation verified; target QField remains 미검증")

# APPROVED AC-SRP-068 reopen-evidence correction guard over the approved design.
assert "068" in coverage
ac068_success = inspect.getsource(
    module.test_ac068_addition_order_roundoff_saves_once_without_recalculation_or_rewrite)
assert all(token in ac068_success for token in (
    'nonzero_differences', '0 < difference <= 1e-6',
    'observed["write_attempts"] == observed["write_successes"] == 1',
    'observed["committed_slot_readbacks"] == 1',
    'observed["backend_calculations"] == observed["provider_requests"] == 0',
    'observed["automatic_retries"] == 0', 'observed["aggregate_rewritten"] is False',
    'observed["reopened"]["data"] == observed["snapshot_after"]["data"]',
    'observed["reopened"]["revision"] == observed["snapshot_after"]["revision"]',
    'observed["reopened"]["slot"] == observed["snapshot_after"]["slot"]',
    'observed["reopened"]["recovered"] is False',
    'fixture["optimized_ids"]', 'observed["active"]["walking_totals"] == candidate_totals',
    'observed["active"]["walking_totals"]["duration_s"] is None',
    'observed["active"]["combined_totals"] is None',
    'observed["active"]["walking_totals"]["unavailable_duration_count"] == 6',
))
ac068_boundary = inspect.getsource(
    module.test_ac068_numeric_walking_aggregate_tolerance_is_inclusive_and_bounded)
assert all(token in ac068_boundary for token in (
    'field', 'fallback', 'delta', 'accepted', '_assert_ac068_no_save_side_effects',
))
ac068_tokens = (
    '(0.0, True), (1e-6, True), (2e-6, False)',
    '("mapped_distance_m", False)', '("lower_bound_distance_m", True)',
    '("duration_s", False)', '["negative", "nonfinite", "type_invalid"]',
    '(False, "count_mismatch")', '(True, "count_mismatch")',
    '(False, "duration_null")', '(True, "duration_nonnull")',
    '(False, "combined_null")', '(True, "combined_nonnull")',
)
assert not [token for token in ac068_tokens if token not in test_source], [
    token for token in ac068_tokens if token not in test_source]
ac068_failure = inspect.getsource(module._assert_ac068_no_save_side_effects)
assert all(token in ac068_failure for token in (
    'observed["write_attempts"] == observed["write_successes"] == 0',
    'observed["provider_requests"] == observed["backend_calculations"] == 0',
    'observed["automatic_retries"] == 0', 'observed["candidate_preserved"] is True',
    'observed["snapshot_after"] == observed["snapshot_before"]',
    'observed["files_after"] == observed["files_before"]',
    'observed["reopened"] == observed["snapshot_before"]',
))
assert 'input.operation==="walking_total_explicit_save"' in module.DIRECT_NODE
print("survey route AC068 approved walking-total save-roundoff design verified")
