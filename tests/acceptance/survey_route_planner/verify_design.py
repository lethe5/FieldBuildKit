"""Draft callback-provenance/storage-compatibility correction verifier.

AC-SRP-049–058 are approved requirements and M18–M21 remain NOT RUN. This draft verifies the
corrected acceptance artifacts only; no application code is executed.
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
assert {f"{i:03d}" for i in range(1, 59)} <= coverage
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
contract = path.with_name("HARNESS_CONTRACT.md").read_text(encoding="utf-8")
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
                                       "M17_ios_local_date_name_lifecycle",
                                       "M18_live_ors_mixed_route",
                                       "M19_mixed_route_visual_accessibility",
                                       "M20_ios_apple_maps_handoff",
                                       "M21_android_naver_regression"])
assert module.canonical_naver_url("조사지 A & B/#?") == (
    "nmap://navigation?dlat=37.456&dlng=127.123&dname="
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
legacy2 = module.schema2_legacy_document(schema=2)
assert legacy2["schema"] == 2 and len(legacy2["routes"][0]["legs"]) == 3
assert sum(leg["distance_m"] for leg in legacy2["routes"][0]["legs"]) == legacy2["routes"][0]["distance_m"]
assert sum(leg["duration_s"] for leg in legacy2["routes"][0]["legs"]) == legacy2["routes"][0]["duration_s"]
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
    'operation="settings_snapshot_save"', 'operation="platform_map_dispatch"',
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
assert module.canonical_apple_maps_url() == (
    "https://maps.apple.com/directions?destination=37.456,127.123&mode=driving"
)
assert module.MIXED_SITES[0]["xy"] == [127.1, 37.1]
assert module.MIXED_ACCESS[0] == [127.1035, 37.1]
assert module.MIXED_SITES[1]["xy"] != module.MIXED_ACCESS[1]
assert 0 < module.geodesic_distance_m(module.MIXED_SITES[1]["xy"], module.MIXED_ACCESS[1]) <= 1
assert module.MIXED_SITES[0]["xy"] != module.EXACT_ZERO_ACCESS
assert 0 < module.geodesic_distance_m(module.MIXED_SITES[0]["xy"], module.EXACT_ZERO_ACCESS) <= 1
assert module.SCHEMA3_ROUTE_REQUIRED_FIELDS == {
    "vehicle_legs", "visits", "vehicle_totals", "walking_totals", "combined_totals",
}
assert module.SCHEMA3_VISIT_REQUIRED_FIELDS == {"layer_id", "site_id", "metric_source"}
assert module.SCHEMA3_ALLOWED_WALKING_PROVENANCE == {
    ("mapped", "ors-foot-hiking"),
    ("exact_zero", "exact_zero"),
    ("unmapped_estimate", "straight_line_lower_bound_m"),
}
assert module.APPLE_MAPS_FAILURE_MESSAGE == (
    "Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요."
)
for legacy_schema in (1, 2):
    heterogeneous = module.heterogeneous_legacy_document(legacy_schema)
    assert heterogeneous["schema"] == legacy_schema and len(heterogeneous["routes"]) == 2
    assert len({route["route_id"] for route in heterogeneous["routes"]}) == 2
assert len(module.SCHEMA3_VISIT_CORRUPTIONS) == 20
assert all(operation in source for operation in [
    'operation="provider_http_failure"', 'operation="mixed_route_calculate"',
    'operation="mixed_route_roundtrip"', 'operation="mixed_route_compatibility"',
    'operation="mixed_route_presentation"', 'operation="platform_map_dispatch"',
])
assert 'import math' in source
assert 'canonical_expected_url' not in source
assert 'survey_route_mixed_driver.js' in source
assert "MIXED_EVIDENCE_FIELDS" not in source
assert all(token in source for token in [
    '"production_provenance"', 'assert self_declared_flag not in provenance',
    '"boundary_event_journal"', '"raw_observed_fields"', '"observations"',
    '"parent_event_ids"',
    '"controller.calculate"', '"backend.calculate"', '"repository.save"',
    '"repository.load"', '"navigation.open"', '"qml.render_route"',
    'document["schema"] == 3',
    'assert_schema3_document_contract', 'seed_schema3_routes_with_production=2',
    '"repaired_document"] is None',
])
ac050_source = inspect.getsource(module.test_ac050_single_ordered_access_snap_uses_originals_and_exact_radius)
assert "nonzero_snapped_sources" in ac050_source
assert 'if site["xy"] != access' in ac050_source
assert 'for site in MIXED_SITES)' not in ac050_source
ac053_source = inspect.getsource(module.test_ac053_mixed_route_visual_accessibility_proxy_is_distinct_and_passive)
assert all(token in ac053_source for token in [
    '"contrasting_casing"', '"non_color_cue"', '"object_ids"',
    '"presentation_provenance"', '"theme_observation"', '"action_observations"',
    '"source_layer_observation"',
])
assert 'r["line_classes"] == {' not in ac053_source
assert 'set(r["vroom_payload_fields"]) <=' in inspect.getsource(
    module.test_ac054_exact_stage_sequence_privacy_and_no_incidental_writes)
assert all(name in source for name in [
    "test_ac049_valid_json_body_is_parsed_even_without_truthful_content_type",
    "test_ac049_statusless_transport_failure_has_connection_action_without_http_status",
    "test_ac052_every_schema3_route_rejects_required_field_omission",
    "test_ac054_lifecycle_after_origin_validation_starts_no_later_request_or_write",
    "test_ac050_origin_null_with_finite_snapped_distance_stops_before_access_snap",
    "test_ac056_every_active_and_inactive_visit_corruption_rejects_whole_document",
    "test_ac056_three_allowed_visit_provenance_pairs_roundtrip_exactly",
    "test_ac052_selected_schema1_and_schema2_route_upgrade_atomically_replaces_identity",
    "test_ac052_failed_schema1_and_schema2_upgrade_preserves_selected_route_and_bytes",
    "test_ac053_every_visit_accessibility_tracks_dynamic_site_mode_source_and_roundtrip",
    "test_ac053_mapped_provider_and_unmapped_lower_bound_stay_separate_on_all_surfaces",
    "test_ac052_ac056_product_cold_start_panel_recovers_last_good_without_mutation",
    "test_ac052_ac056_exact_zero_totals_stay_exact_and_separate",
    "test_ac052_ac053_fallback_totals_stay_lower_bound_and_duration_unknown",
    "test_ac057_no_file_default_open_is_schema2_in_memory_and_write_free",
    "test_ac057_settings_or_default_only_save_never_promotes_beyond_schema2",
    "test_ac057_untagged_homogeneous_schema3_reads_without_write_then_tags_next_write",
    "test_ac057_marker_corruption_and_duplicates_fail_atomically",
    "test_ac058_route_line_toggle_is_one_atomic_settings_only_write_and_persists",
    "test_ac058_preview_and_legend_are_write_free",
    "test_ac058_toggle_failure_rolls_back_and_reports_actionable_feedback",
])
assert all(token in contract for token in [
    "content type is missing or misleading", "http_status=null",
    "source_coordinate == access_coordinate", "immediately after origin validation",
    "including inactive routes", "presentation_provenance", "computes field lineage",
    "location=null", "source-layer rereads", "actual `QAccessible` parent/child traversal",
    "explicit production recalculation plus save", "No metric-source/value literal",
    "closed and separately sealed", "before any result dictionary is constructed",
    "`result_source`", "`bind_result`", "`capture_outputs`", "post-result replay",
    "explicit causal links", "product cold start", "route_schema",
    "non-identical source/access coordinates", "preceding valid route",
    "three separate real lifecycle callbacks", "straight-line lower bounds",
])
provenance_source = inspect.getsource(module.assert_mixed_boundary_event_lineage)
assert all(token in provenance_source for token in [
    '"boundary_event_journal"', '"event_id"', '"previous_event_sha256"',
    '"parent_event_ids"', '"raw_observed_fields"', '"observations"',
    '"seal_path"', '"finalized_at_monotonic_ns"',
    '"result_construction_started_at_monotonic_ns"',
    '"append_attempts_after_finalize"', '"capture_phase"] == "boundary_callback"',
    '"causal_parent_observations"', '"hook_id"',
    "_contains_forbidden_replay_key", "_lineage_from_boundary_events(events)",
    "_assert_result_matches_boundary_lineage", "_assert_tampered_result_is_rejected",
    "MIXED_EVENT_REQUIRED_ANCESTOR_SOURCES.get",
])
driver_guard_source = inspect.getsource(module.assert_boundary_driver_has_no_result_replay)
assert all(token in driver_guard_source for token in [
    "ast.parse", "capture_outputs", "result.items()", "result.keys()",
    "_iterates_completed_result(node.iter)", "output_bindings", "field_name_inference",
])
assert "assert_boundary_driver_has_no_result_replay" in inspect.getsource(module.run)
tamper_guard_source = inspect.getsource(module._assert_tampered_result_is_rejected)
assert all(token in tamper_guard_source for token in [
    "deepcopy(result)", 'tampered[field] = {"tampered_result_source": field}',
    "pytest.raises(AssertionError)", "_assert_result_matches_boundary_lineage",
])
provider_evidence = inspect.getsource(module.assert_actual_failed_provider_request)
assert 'requests[0]["kind"] == "origin-validation"' in provider_evidence
assert 'requests[failed["request_index"]] == failed["request"]' in provider_evidence
preflight_source = inspect.getsource(module.test_ac050_access_boundary_failures_stop_pipeline_and_preserve_last_good)
assert '"controller_state_after_explicit_calculate"' in preflight_source
assert '"derived_from_case_input"' in preflight_source
presentation_source = inspect.getsource(module.test_ac053_mixed_route_visual_accessibility_proxy_is_distinct_and_passive)
assert all(token in presentation_source for token in [
    '"before_state"', '"after_state"', '"rendered_window_geometry"',
    '"source_layer_renderer_reread"', '"accessibility_observations"',
    '"QAccessible.queryAccessibleInterface"', '"loaded_route_readback"',
])
assert '"before_capture_id"' not in presentation_source and '"after_capture_id"' not in presentation_source
dynamic_visit_accessibility = inspect.getsource(
    module.test_ac053_every_visit_accessibility_tracks_dynamic_site_mode_source_and_roundtrip)
assert all(token in dynamic_visit_accessibility for token in [
    'visit_value_fixtures=["all-modes-a", "all-modes-b"]',
    '"visit_accessibility_binding_observations"', '"captured_storage"',
    '"site_id": visit["site_id"]', '"walking_mode": visit["walking_mode"]',
    '"metric_source": visit["metric_source"]', '"roundtrip": True',
    'SCHEMA3_ALLOWED_WALKING_PROVENANCE', '"왕복"',
    "dynamic_values[:3] != dynamic_values[3:]",
])
notice_source = inspect.getsource(module.test_ac054_exact_stage_sequence_privacy_and_no_incidental_writes)
assert "coordinate_notice_acknowledged" not in notice_source
assert all(token in notice_source for token in [
    '"visual_order"', '"accessibility_order_observation"',
    '"QAccessible parent/child traversal"', '"calculate_button_signal_observation"',
    '"acknowledgement_required"] is False',
])
assert "childItems" not in notice_source
navigation_source = inspect.getsource(module.assert_navigation_has_observed_no_route_or_storage_activity)
assert all(token in navigation_source for token in [
    '"observer_installed_before_action"', '"routing-provider-request-log"',
    '"route-storage-write-log"', '"events"] == []',
])
ac056_source = inspect.getsource(
    module.test_ac056_every_active_and_inactive_visit_corruption_rejects_whole_document)
assert all(token in ac056_source for token in [
    'actions=["load-reject", "restart", "recover-last-good"]', '"last_good_after"',
    '"defaulted_fields"', '"inferred_fields"', '"corrupted_route_was_active"',
    '"visit_counts"] == [2, 2]', '"corrupted_visit_index"', '"corrupt_newest"] is True',
    '"load_rejection_observation"', '"restart_observation"', '"recovery_observation"',
    'recover["selected_route"] == seed["last_good_route"]',
    'recover["selected_document_sha256"] != seed["corrupt_document_sha256"]',
    "assert_lifecycle_observation_is_journal_event",
])
distance_source = inspect.getsource(module.assert_visit_distance_semantics)
assert all(token in distance_source for token in [
    "geodesic_distance_m", 'visit["access_offset_m"]', 'abs=0.01',
    '0 < lower_bound <= 1.0', 'provider_observation["response"]',
    'list(reversed(',
])
exact_roundtrip_source = inspect.getsource(
    module.test_ac056_three_allowed_visit_provenance_pairs_roundtrip_exactly)
assert 'visit["source_coordinate"] != visit["access_coordinate"]' in exact_roundtrip_source
assert any(parameter.values[0].get("field") == "access_offset_m"
           and parameter.values[0].get("walking_mode") == "exact_zero"
           for parameter in module.SCHEMA3_VISIT_CORRUPTIONS)
quantity_source = inspect.getsource(
    module.test_ac053_mapped_provider_and_unmapped_lower_bound_stay_separate_on_all_surfaces)
assert all(token in quantity_source for token in [
    'quantity_fixtures=["mixed-a", "mixed-b"]', '"quantity_binding_observations"',
    '"mapped_provider_distance"', '"mapped_provider_duration"',
    '"straight_line_lower_bound"', '"visible_readbacks"', '"accessibility_readbacks"',
    '"render_observation"', '"QAccessible.queryAccessibleInterface"',
    '"exact_walking_total_present"] is False',
    '"summed_mapped_plus_lower_bound_present"] is False',
])
upgrade_source = inspect.getsource(
    module.test_ac052_selected_schema1_and_schema2_route_upgrade_atomically_replaces_identity)
assert all(token in upgrade_source for token in [
    'action="explicit-recalculate-and-save"', 'replacements == [r["saved_route"]]',
    '"atomic_replace_observation"', '"commit_count"] == 1',
    'assert_schema3_document_contract', '"route_schema"] == 3',
    'if key != "route_schema"', '"listed_route_ids"', '"loaded_legacy_route"',
])
failed_upgrade_source = inspect.getsource(
    module.test_ac052_failed_schema1_and_schema2_upgrade_preserves_selected_route_and_bytes)
assert all(token in failed_upgrade_source for token in [
    '"bytes_after"] == r["bytes_before"]', '"last_good_after"] == r["last_good_before"]',
    '"successful_storage_commits"] == []', '"saved_document"] == legacy',
])
cold_start_source = inspect.getsource(
    module.test_ac052_ac056_product_cold_start_panel_recovers_last_good_without_mutation)
assert all(token in cold_start_source for token in [
    'action="product-cold-start-open-panel"', '"prior_panel_destroyed"] is True',
    '"RoutePanel.Component.onCompleted"', '"Controller.create"', '"Controller.reload"',
    '"Repository.load"', '"qml.open_panel"', '"controller.create"', '"controller.reload"',
    '"corrupt_newest_bytes_after"] == r["corrupt_newest_bytes_before"]',
    '"provider_requests"] == r["storage_writes_after_corruption"] == []',
])
schema_boundary_source = inspect.getsource(
    module.test_ac057_settings_or_default_only_save_never_promotes_beyond_schema2)
assert all(token in schema_boundary_source for token in [
    '"settings-only-save"', '"default-start-only-save"', '"schema"] == 2',
    '"route_schema" not in route',
    '"successful_storage_commits"] == 1', '"readback_document"',
])
marker_failure_source = inspect.getsource(
    module.test_ac057_marker_corruption_and_duplicates_fail_atomically)
assert all(token in marker_failure_source for token in [
    '"unknown-route-schema"', '"legacy-marker-with-mixed-fields"',
    '"mixed-marker-with-legacy-fields"', '"duplicate-route-identity"',
    '"legacy-variant-corruption"', '"mixed-variant-corruption"',
    '"bytes_after"] == r["bytes_before"]', '"last_good_after"] == r["last_good_before"]',
])
toggle_source = inspect.getsource(
    module.test_ac058_route_line_toggle_is_one_atomic_settings_only_write_and_persists)
assert all(token in toggle_source for token in [
    '"toggle-off"', '"panel-reopen"', '"cold-restart"', '"move-with-settings"',
    '"toggle-on"', '"atomic_commit_count"] == 1', '"readback_count"] == 1',
    '"changed_paths"] == ["settings.show_route_line"]',
    '"route_after"] == r["route_before"]', '"revision_after"] == r["revision_before"]',
])
apple_source = inspect.getsource(module.test_ac055_ios_uses_exact_apple_maps_once_without_any_fallback)
assert 'r["message"] == APPLE_MAPS_FAILURE_MESSAGE' in apple_source
assert 'assert "평문" in consent' not in source
assert 'fresh_project=True, seed_saved=True' not in source
assert source.count('seed_fixture_settings=False') == 2
assert 'must not install any synthetic endpoint setting (including `vroom.invalid`)' in contract
assert '{"select": [0, 13]}' in source
assert "\"ios\", canonical_naver_url" not in source
assert "NAVER_IOS_STORE" not in source
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
print("Design checks: DRAFT callback-provenance/storage-compatibility correction is internally consistent; "
      "approved AC001-058/QPB149-150 history and M01-M21 NOT RUN boundaries are preserved. "
      "No application tests executed.")
