"""APPROVED AC-SRP-061–062 Matrix/credential-store acceptance extension (2026-09-22).

The approved AC-SRP-059 baseline and all earlier history remain preserved below. The new extension
uses only disposable localhost/app-data fixtures and visibly synthetic credentials.

DRAFT AC-SRP-049–058 direct-observation redesign (2026-09-21).

The approved AC-SRP-001–048 and QPB149–150 history is preserved below.

APPROVED TEST-DESIGN CORRECTION — iOS/QField follow-up (approval 2026-09-18).

The approved history is preserved. This approved correction replaces over-scoped rendered/device proxies for
AC-SRP-046–048 and AC-QPB-149–150; it does not claim device PASS or alter product requirements.

APPROVED TEST-DESIGN SUPERSESSION RECONCILIATION (approval 2026-09-17) — retained
AC-SRP-019/022/024/031 under approved D-SRP-043/045 and FR-SRP-041/043.

The 2026-09-17 approved acceptance baseline, AC-SRP-042–045 evidence correction and approval
history remain authority. This approved reconciliation changes only contradictory legacy executable expectations;
it does not change approved product meaning. M01–M14 remain NOT RUN.

The adapter executes production behavior; only transport/device/file faults are fakes.
See HARNESS_CONTRACT.md. Missing new seam skips; broken existing seam fails.
"""
from __future__ import annotations

import importlib
import hashlib
import json
import math
import os
import re
import shutil
import sys
import threading
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def run(tmp_path):
    try:
        api = importlib.import_module("qfield_builder.acceptance_api")
    except ModuleNotFoundError as exc:
        if exc.name not in {"qfield_builder", "qfield_builder.acceptance_api"}:
            raise
        api = None
    fn = getattr(api, "run_survey_route_acceptance", None)
    if fn is None:
        reason = "SRP harness unimplemented: run_survey_route_acceptance; not product PASS"
        if os.environ.get("FIELDBUILD_REQUIRE_SRP_HARNESS") == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    assert callable(fn)
    return lambda **case: fn(case=case, work_dir=str(tmp_path))


KEY = "SRP_SYNTHETIC_SECRET_94_&/"
FOLLOWUP_ROUTE_NAME = "  오후 조사 경로  "
HOSTED_ROUTING_BASE = "https://api.heigit.org/openrouteservice"
HOSTED_OPTIMIZER_URL = "https://api.heigit.org/vroom/v0"
LEGACY_ROUTING_BASE = "https://api.openrouteservice.org"
LEGACY_OPTIMIZER_URL = "https://api.openrouteservice.org/optimization"
QFIELD_EXPRESSION_EVALUATOR = {
    "native_type": "QfExpressionEvaluator",
    "qml_type": "ExpressionEvaluator",
    "writable_properties": [
        "appExpressionContextScopesGenerator", "attributeFormModel", "expressionText",
        "feature", "layer", "mapSettings", "mode", "project", "variables",
    ],
    "evaluate_arities": [0, 1],
    "allow_dynamic_properties": False,
}
POINTS = [{"id": str(i), "name": f"조사지 {i}", "xy": [127 + i / 1000, 37]} for i in range(12)]
# Directed costs for depot,A,B,C. Time winner O-A-B-C-O = 4; distance O-C-B-A-O = 8.
TIME = [[0, 1, 20, 20], [20, 0, 1, 20], [20, 20, 0, 1], [1, 20, 20, 0]]
DISTANCE = [[0, 30, 30, 2], [2, 0, 30, 30], [30, 2, 0, 30], [30, 30, 2, 0]]
ROAD = {"type": "LineString", "coordinates": [[127, 37], [127.001, 37.003], [127.002, 37]]}
RESULT_ROAD = {"type": "LineString", "coordinates": [
    [127, 37], POINTS[2]["xy"], POINTS[0]["xy"], POINTS[1]["xy"], [127, 37],
]}
LEGS = [
    {"distance_m": 100, "duration_s": 20},
    {"distance_m": 200, "duration_s": 100},
    {"distance_m": 300, "duration_s": 120},
    {"distance_m": 634, "duration_s": 216},
]
DIRECTIONS_LEGS = [
    {"distance": leg["distance_m"], "duration": leg["duration_s"]}
    for leg in LEGS
]
ETA = [60, 180, 300]


def vroom_response(*, include_arrivals):
    """Raw VROOM 1.14 response fixture; ETA comes only from job-step arrival."""
    steps = [
        {"type": "start", "location": [127, 37]},
        {"type": "job", "id": 2, "location": POINTS[2]["xy"]},
        {"type": "job", "id": 0, "location": POINTS[0]["xy"]},
        {"type": "job", "id": 1, "location": POINTS[1]["xy"]},
        {"type": "end", "location": [127, 37]},
    ]
    if include_arrivals:
        for step, arrival in zip(steps, [0, *ETA, 456]):
            step["arrival"] = arrival
    return {
        "code": 0,
        "summary": {"cost": 456, "routes": 1, "unassigned": 0, "duration": 456, "distance": 1234},
        "unassigned": [],
        "routes": [{
            "vehicle": 0,
            "cost": 456,
            "duration": 456,
            "distance": 1234,
            "steps": steps,
        }],
    }


def invalid_vroom_timing(fault):
    """Malformed timing is injected only in the raw optimizer response."""
    response = vroom_response(include_arrivals=True)
    jobs = [step for step in response["routes"][0]["steps"] if step["type"] == "job"]
    if fault == "iso":
        jobs[0]["arrival"] = "2026-09-14T01:00:00Z"
    elif fault == "partial":
        del jobs[-1]["arrival"]
    elif fault == "negative":
        jobs[0]["arrival"] = -1
    elif fault == "nonfinite":
        jobs[0]["arrival"] = float("inf")
    return response


DIRECTIONS_RESPONSE = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"summary": {"distance": 1234, "duration": 456},
                       "segments": DIRECTIONS_LEGS, "way_points": [0, 1, 2, 3, 4]},
        "geometry": RESULT_ROAD,
    }],
}

SITE_LAYER_ID = "site-layer-stable-01"
SCHEMA2_COORDINATES = [
    [127, 37], [127.0004, 37.0002], [127.001, 37.001],
    [127.0014, 37.0013], [127.002, 37.002],
    [127.0026, 37.0025], [127.003, 37.003],
    [127.0015, 37.0012], [127, 37],
]
SCHEMA2_WAY_POINTS = [0, 2, 4, 6, 8]
SCHEMA2_DISTANCES = [100, 200, 300, 400]
SCHEMA2_DURATIONS = [20, 100, 120, 216]


def schema2_directions_response(*, roundtrip, distance_adjustment=0, duration_adjustment=0):
    """Documented ORS GeoJSON: route-level indexes and segments without way_points."""
    count = 4 if roundtrip else 3
    segments = [
        {"distance": SCHEMA2_DISTANCES[i], "duration": SCHEMA2_DURATIONS[i], "steps": []}
        for i in range(count)
    ]
    end = SCHEMA2_WAY_POINTS[count]
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"summary": {
                "distance": sum(SCHEMA2_DISTANCES[:count]) + distance_adjustment,
                "duration": sum(SCHEMA2_DURATIONS[:count]) + duration_adjustment,
            }, "segments": segments, "way_points": SCHEMA2_WAY_POINTS[:count + 1]},
            "geometry": {"type": "LineString", "coordinates": SCHEMA2_COORDINATES[:end + 1]},
        }],
    }


def malformed_schema2_directions(fault):
    """Mutate only documented route-level geometry/way_points or segment metrics."""
    response = schema2_directions_response(roundtrip=True)
    feature = response["features"][0]
    properties = feature["properties"]
    if fault == "missing_leg":
        del properties["segments"][1]
        path = "features[0].properties.segments[1]"
    elif fault == "out_of_order_leg":
        properties["way_points"][2] = 1
        path = "features[0].properties.way_points[2]"
    elif fault == "negative_leg":
        properties["segments"][1]["distance"] = -1
        path = "features[0].properties.segments[1].distance"
    elif fault == "nonfinite_leg":
        properties["segments"][1]["duration"] = float("inf")
        path = "features[0].properties.segments[1].duration"
    elif fault == "invalid_leg_geometry":
        feature["geometry"]["type"] = "Polygon"
        path = "features[0].geometry.type"
    elif fault == "non_wgs84_leg":
        feature["geometry"]["coordinates"][3] = [181, 37]
        path = "features[0].geometry.coordinates[3]"
    elif fault == "mismatched_leg_count":
        properties["way_points"].pop()
        path = "features[0].properties.way_points"
    else:
        raise AssertionError(f"unknown schema-2 fault: {fault}")
    assert all("way_points" not in segment for segment in properties["segments"])
    return response, path


def payload_sha256(value):
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=True,
                         sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def malformed_provider_payload(fault):
    """Return raw malformed provider payloads; the harness must not invent or repair them."""
    optimizer = vroom_response(include_arrivals=True)
    directions = schema2_directions_response(roundtrip=True)
    jobs = [step for step in optimizer["routes"][0]["steps"] if step["type"] == "job"]
    properties = directions["features"][0]["properties"]
    if fault == "missing_order":
        optimizer["routes"][0]["steps"].remove(jobs[1])
    elif fault == "duplicate_order":
        jobs[1]["id"] = jobs[0]["id"]
    elif fault == "unknown_order":
        jobs[1]["id"] = 99
    elif fault == "unassigned_order":
        optimizer["unassigned"] = [{"id": jobs[1]["id"]}]
        optimizer["summary"]["unassigned"] = 1
    elif fault == "missing_way_points":
        del properties["way_points"]
    elif fault == "duplicate_waypoint_index":
        properties["way_points"][2] = properties["way_points"][1]
    elif fault == "invalid_waypoint_index":
        properties["way_points"][-1] = len(SCHEMA2_COORDINATES) + 10
    elif fault == "missing_segment":
        properties["segments"].pop()
    elif fault == "invalid_geometry":
        directions["features"][0]["geometry"] = {"type": "Polygon", "coordinates": []}
    elif fault == "invalid_metric":
        properties["segments"][1]["duration"] = -1
    elif fault == "total_tolerance":
        properties["summary"]["distance"] += 6
    else:
        raise AssertionError(f"unknown provider fixture fault: {fault}")
    return optimizer, directions


def one_stop_vroom_response(target):
    return {
        "code": 0,
        "summary": {"cost": 30, "routes": 1, "unassigned": 0, "duration": 30, "distance": 50},
        "unassigned": [],
        "routes": [{"vehicle": 0, "cost": 30, "duration": 30, "distance": 50, "steps": [
            {"type": "start", "location": [-1, -1], "arrival": 0},
            {"type": "job", "id": 0, "location": target, "arrival": 30},
        ]}],
    }


def one_stop_directions_response(target):
    midpoint = [(-1 + target[0]) / 2, (-1 + target[1]) / 2]
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "summary": {"distance": 50, "duration": 30},
                "segments": [{"distance": 50, "duration": 30, "steps": []}],
                "way_points": [0, 2],
            },
            "geometry": {"type": "LineString", "coordinates": [[-1, -1], midpoint, target]},
        }],
    }


FOLLOWUP_FLOATING_LABELS = {
    "layer": "조사지",
    "id_field": "조사지 ID 필드",
    "name_field": "조사지 이름 필드",
    "completion_field": "조사 완료 필드",
    "scope": "계산 대상",
    "start": "출발지",
    "route_name": "저장할 경로 이름",
}
FINAL_FLOATING_LABELS = {
    **FOLLOWUP_FLOATING_LABELS,
    "saved_route": "저장 경로 불러오기",
}
AC031_FLOATING_LABEL_SUBSET = {
    semantic_id: FINAL_FLOATING_LABELS[semantic_id]
    for semantic_id in ("scope", "start", "layer", "id_field", "name_field", "completion_field")
}
WORKFLOW_LABELS = {
    "scope": "계산 대상",
    "start": "출발지",
    "saved_route": "저장 경로 불러오기",
}
STEP7_ROUTE_KEY_COPY = {
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
NAVER_ANDROID_PACKAGE = "com.nhn.android.nmap"
NAVER_ANDROID_STORE = "market://details?id=com.nhn.android.nmap"
SELECTION_GUIDANCE = (
    "조사지 레이어를 열고 피처 선택/체크 도구로 계산할 조사지를 선택한 뒤 이 패널로 돌아오세요. "
    "현재 선택한 조사지: {count}개"
)
TARGET_FEATURES = [
    {"id": "site-03", "name": "같은 이름", "alt_id": "A-03", "alt_name": "대체 이름", "selected": True,
     "completed": False, "xy": [127.003, 37]},
    {"id": "site-01", "name": "같은 이름", "alt_id": "A-01", "alt_name": "대체 이름", "selected": False,
     "completed": True, "xy": [127.001, 37]},
    {"id": "site-02", "name": "셋째 조사지", "alt_id": "A-02", "alt_name": "대체 셋째", "selected": True,
     "completed": False, "xy": [127.002, 37]},
]


def candidate_fixture(scope, count):
    features = deepcopy(TARGET_FEATURES)
    if scope == "all":
        features = features[:count]
    elif scope == "selected":
        for index, feature in enumerate(features):
            feature["selected"] = index < count
    elif scope == "uncompleted":
        for index, feature in enumerate(features):
            feature["completed"] = index >= count
    else:
        raise AssertionError(f"unknown scope: {scope}")
    expected = [feature["id"] for feature in features if (
        scope == "all" or scope == "selected" and feature["selected"]
        or scope == "uncompleted" and not feature["completed"]
    )]
    return features, expected


def assert_independent_preflight_capture(result, expected_ids):
    model = result["candidate_model_capture"]
    preflight = result["preflight_capture"]
    assert model["source"] == "rendered_target_model"
    assert model["evidence_source"] == "loaded_generated_qml_object_tree"
    assert model["control_object_id"] and model["model_object_id"]
    assert model["visible"] is True and model["enabled"] is True
    assert model["control_rect"]["width"] > 0 and model["control_rect"]["height"] > 0
    assert model["accessibility"]["role"] == "ComboBox"
    assert model["accessibility"]["visible"] is True and model["accessibility"]["enabled"] is True
    assert preflight["source"] == "production_calculation_preflight"
    assert model["capture_id"] != preflight["capture_id"]
    assert model["ordered_ids"] == expected_ids
    assert preflight["submitted_ids"] == expected_ids
    assert preflight["ordered_candidate_ids"] == expected_ids
    assert preflight["transport_requests"] == []
    assert result["target_refresh_validation_order"] == [
        "render_target_model", "capture_calculation_preflight", "validate_required_target",
    ]


def assert_zero_marker_writes(result):
    capture = result["write_capture"]
    assert capture["installed_before_first_action"] is True
    assert capture["source_provider_commit_attempts"] == []
    assert capture["route_storage_commit_attempts"] == []
    assert capture["closed_after_last_action"] is True
    assert capture["source_snapshot_after"] == capture["source_snapshot_before"]
    assert capture["route_storage_snapshot_after"] == capture["route_storage_snapshot_before"]


def schema2_legacy_document(schema=1):
    return {
        "schema": schema,
        "routes": [{
            "route_id": "legacy-route-1", "name": "기존 경로", "revision": 7,
            "distance_m": 600, "duration_s": 240,
            "road_geometry": {"type": "LineString",
                              "coordinates": SCHEMA2_COORDINATES[:SCHEMA2_WAY_POINTS[3] + 1]},
            "stops": [
                {"site_id": str(i), "source_layer": SITE_LAYER_ID, "sequence": i + 1, "completed": False}
                for i in range(3)
            ],
        }],
        "active_route_id": "legacy-route-1",
    }


PROJECT_LAYERS = [
    {"layer_id": "duplicate-a", "source_name": "plots_a", "alias": "표본구", "tree_path": "A/표본구",
     "fields": ["uuid", "plot_id", "display_name", "done"]},
    {"layer_id": SITE_LAYER_ID, "source_name": "site", "alias": "내부 site", "internal_role": "site",
     "fields": ["uuid", "site_id", "site_name", "done"]},
    {"layer_id": "duplicate-b", "source_name": "plots_b", "alias": "표본구", "tree_path": "B/표본구",
     "fields": ["uuid", "manual_code", "manual_title", "SECOND_ID", "SECOND_NAME"]},
]

PORTABLE_SETTINGS = {
    "server_url": "https://routing.invalid/ors",
    "optimizer_url": "https://optimizer.invalid/vroom",
    "backend": "ors-vroom",
    "profile": "driving-car",
    "timeout_ms": 1250,
    "max_road_offset_m": 50,
    "max_access_distance_m": 2000,
    "default_start": [127.123, 37.456],
    "mapping": {"layer": "site", "id": "custom_id", "name": "title", "completed": "done"},
    "show_route_line": True,
}


def ids(route):
    return [stop["site_id"] for stop in route["stops"]]


def generated_layer_id(result, layer_name):
    project = ET.parse(next(Path(result["project_dir"]).glob("*.qgs")))
    matches = [layer.findtext("id") for layer in project.findall("./projectlayers/maplayer")
               if layer.findtext("layername") == layer_name]
    assert len(matches) == 1
    return matches[0]


def read_qgs_labeling(qgs_path, layer_id):
    """Read the generated QGIS labeling nodes, independently of harness observations."""
    project = ET.parse(qgs_path)
    layers = [layer for layer in project.findall("./projectlayers/maplayer")
              if layer.findtext("id") == layer_id]
    assert len(layers) == 1
    layer = layers[0]
    labeling = layer.find("labeling")
    assert labeling is not None
    return {
        "enabled": layer.findtext("labelsEnabled"),
        "type": labeling.get("type"),
        "text_style": dict(labeling.find(".//text-style").attrib),
        "buffer": dict(labeling.find(".//text-buffer").attrib),
        "placement": dict(labeling.find(".//placement").attrib),
        "rendering": dict(labeling.find(".//rendering").attrib),
    }


def no_calls(result):
    assert result["requests"] == []


def rejected(result):
    assert result["saved_before"], "scenario must seed a nonempty saved baseline"
    assert result["ok"] is False
    assert result["message"].strip()
    assert result["saved_after"] == result["saved_before"]


def rects_overlap(first, second):
    return not (first["right"] <= second["left"] or second["right"] <= first["left"]
                or first["bottom"] <= second["top"] or second["bottom"] <= first["top"])


def rect_center_y(rect):
    return (rect["top"] + rect["bottom"]) / 2


def false_xml_flag(value):
    return str(value).strip().lower() in {"0", "false"}


def expected_site_label_expression(*, name_field_present):
    fields = ["display_name", "site_id"] if name_field_present else ["site_id"]
    branches = [
        f'''WHEN trim(coalesce(to_string("{field}"), '')) <> '' THEN trim(to_string("{field}"))'''
        for field in fields
    ]
    return "CASE " + " ".join(branches) + " ELSE NULL END"


def assert_secret_absent(value, *, location):
    encoded = value if isinstance(value, bytes) else str(value).encode()
    if KEY.encode() in encoded:
        pytest.fail(f"synthetic route key leaked into {location}", pytrace=False)


def assert_secret_free_failure(result):
    for field in ("message", "logs", "errors", "qml_errors"):
        assert KEY not in str(result.get(field))
    assert_authorization_only(result, KEY)


def requests_by_kind(result):
    requests = {}
    for request in result["requests"]:
        requests.setdefault(request["kind"], []).append(request)
    return requests


def assert_authorization_only(result, key):
    for request in result["requests"]:
        headers = request["headers"]
        if key is None:
            assert "Authorization" not in headers
        else:
            assert headers.get("Authorization") == key
        without_auth = dict(request, headers={k: v for k, v in headers.items() if k != "Authorization"})
        if key is not None:
            assert key not in str(without_auth)


def assert_no_key_outside_project_variable(result, *, embedded):
    for field in ("general_settings", "logs", "errors", "reports", "message", "qml_errors"):
        assert KEY not in str(result.get(field))
    assert KEY not in str(result.get("persisted_settings"))
    assert_authorization_only(result, KEY if result.get("transport_key_present") else None)
    secret_files = []
    root = Path(result["project_dir"])
    if root.exists():
        for path in root.rglob("*"):
            if path.is_file() and KEY.encode() in path.read_bytes():
                secret_files.append(path.resolve())
    if embedded:
        assert secret_files == [Path(result["qgs_path"]).resolve()]
        assert result["project_variables"] == {"fieldbuild_route_api_key": KEY}
    else:
        assert secret_files == []
        assert "fieldbuild_route_api_key" not in result.get("project_variables", {})


def test_ac001_generated_plugin(run):
    r = run(operation="generate_plugin", identification=True)
    root = Path(r["project_dir"]).resolve()
    assert r["loaded_features"] >= {"routes", "report", "identification"}
    assert r["qml_errors"] == []
    assert r["asset_paths"]
    for relative in r["asset_paths"]:
        path = (root / relative).resolve()
        assert not Path(relative).is_absolute()
        assert path.is_relative_to(root) and path.is_file()
    assert r["panel"]["edge"] == "bottom"
    assert r["panel"]["collapsed_rows"] == 1
    controls = {control["semantic_id"]: control for control in r["panel"]["control_objects"]}
    assert {"targets", "settings", "results", "save", "load"} <= set(controls)
    assert len({control["object_id"] for control in controls.values()}) == len(controls)
    for semantic_id in {"targets", "settings", "results", "save", "load"}:
        control = controls[semantic_id]
        assert control["object_id"] and control["qml_type"]
        assert control["enabled"] is True
        assert control["visible"] is (semantic_id != "settings")
        assert control["object_identity_source"] == "loaded_generated_qml"


@pytest.mark.parametrize("count", [0, 1, 3])
def test_ac002_selection(run, count):
    wanted = POINTS[:count]
    r = run(operation="calculate", scope="selected", features=POINTS,
            selected_ids=[p["id"] for p in wanted], focused_id="11")
    assert r["listed_ids"] == [p["id"] for p in wanted]
    assert r["selection_help"]["recognized_count"] == count
    assert r["selection_help"]["explains_layer_selection"] is True
    assert r["selection_help"]["focus_is_selection"] is False
    if count == 0:
        rejected(r)
        no_calls(r)
    else:
        assert r["ok"] is True
        assert sorted(r["submitted_ids"]) == sorted(p["id"] for p in wanted)
        assert sorted(ids(r["candidate"])) == sorted(r["submitted_ids"])


@pytest.mark.parametrize("scope,expected", [("all", ["0", "1", "2", "3"]), ("uncompleted", ["1", "2", "3"])])
def test_ac003_ac010_scope_mapping(run, scope, expected):
    features = [
        {"custom_id": "0", "title": POINTS[0]["name"], "done": True, "xy": POINTS[0]["xy"]},
        {"custom_id": "1", "title": POINTS[1]["name"], "done": False, "xy": POINTS[1]["xy"]},
        {"custom_id": "2", "title": POINTS[2]["name"], "done": None, "xy": POINTS[2]["xy"]},
        {"custom_id": "3", "title": POINTS[3]["name"], "xy": POINTS[3]["xy"]},
    ]
    r = run(operation="calculate", scope=scope, features=features,
            selected_ids=["3"],
            survey_type="simple_inventory",
            mapping={"layer": "custom_targets", "id": "custom_id", "name": "title", "completed": "done"})
    assert sorted(r["submitted_ids"]) == expected
    assert {s["source_layer"] for s in r["candidate"]["stops"]} == {"custom_targets"}


def test_ac003_site_default_mapping(run):
    features = [{"site_id": p["id"], "site_name": p["name"], "xy": p["xy"]} for p in POINTS[:3]]
    r = run(operation="calculate", scope="all", survey_type="temporary_plots", features=features)
    assert r["submitted_ids"] == ["0", "1", "2"]
    assert {s["source_layer"] for s in r["candidate"]["stops"]} == {
        generated_layer_id(r, "조사지")}


def test_ac003_type1_requires_explicit_mapping(run):
    r = run(operation="calculate", scope="all", survey_type="simple_inventory",
            features=POINTS[:3], mapping=None, seed_saved=True)
    rejected(r)
    no_calls(r)


@pytest.mark.parametrize("bad_ids", [["x", "x"], ["", "y"], [None, "y"]])
def test_ac003_reject_ids(run, bad_ids):
    r = run(operation="calculate", features=[dict(p, id=value) for p, value in zip(POINTS, bad_ids)])
    rejected(r)
    no_calls(r)


@pytest.mark.parametrize("mode", ["gps", "map", "target", "saved_default"])
def test_ac004_start_and_return(run, mode):
    r = run(operation="start", mode=mode, coordinate=[127.123, 37.456], restart=mode == "saved_default")
    assert r["candidate"]["start"] == [127.123, 37.456]
    assert r["candidate"]["end"] == r["candidate"]["start"]
    assert r["request_start"] == r["candidate"]["start"]


def test_ac004_missing_gps(run):
    r = run(operation="start", mode="gps", coordinate=None)
    rejected(r)
    no_calls(r)


@pytest.mark.parametrize("objective,expected", [("time", ["0", "1", "2"]), ("distance", ["2", "1", "0"])])
def test_ac005_road_cost_request(run, objective, expected):
    r = run(operation="road_cost", backend="ors-vroom", features=POINTS[:3], objective=objective,
            time_matrix=TIME, distance_matrix=DISTANCE, backend_order=expected)
    assert r["optimizer_request"]["objective"] == objective
    assert r["optimizer_request"]["cost_matrix"] == (TIME if objective == "time" else DISTANCE)
    assert r["optimizer_request"]["return_to_start"] is True
    assert ids(r["candidate"]) == expected
    assert len(set(ids(r["candidate"]))) == 3
    assert r["candidate"]["optimality_guaranteed"] is False


ERRORS = ["status_0", "network", "http_401", "http_429", "http_500", "timeout", "truncated_json",
          "null_matrix", "unassigned", "disconnected", "off_road", "duplicate_stop", "unknown_stop",
          "missing_stop", "negative_distance", "nonfinite_time", "leg_count"]


@pytest.mark.parametrize("fault", ERRORS)
def test_ac006_failures_preserve_saved(run, fault):
    r = run(operation="calculate_failure", fault=fault, seed_saved=True, key=KEY)
    rejected(r)
    assert r["candidate"] is None
    assert KEY not in str(r["logs"]) and KEY not in str(r["saved_after"])
    assert r["active_after"] == r["active_before"]


@pytest.mark.parametrize("timing", [False, True])
def test_ac007_result_roundtrip(run, timing):
    r = run(operation="result_roundtrip", backend="ors-vroom",
            optimizer_response=vroom_response(include_arrivals=timing),
            directions_response=DIRECTIONS_RESPONSE)
    route = r["reloaded"]
    for field in ("route_id", "name", "backend", "status"):
        assert route[field]
    datetime.fromisoformat(route["created_at"].replace("Z", "+00:00"))
    assert route["distance_m"] == 1234 and route["duration_s"] == 456
    assert ids(route) == ["2", "0", "1"]
    assert [s["sequence"] for s in route["stops"]] == [1, 2, 3]
    assert route["eta"] == (ETA if timing else None)
    assert route["eta_basis"] == ("relative_seconds" if timing else None)
    layer_id = generated_layer_id(r, "조사지")
    references = [{"layer_id": layer_id, "site_id": value} for value in ["2", "0", "1"]]
    coordinates = RESULT_ROAD["coordinates"]
    expected_legs = [{
        "sequence": index + 1,
        "from": "start" if index == 0 else references[index - 1],
        "to": references[index] if index < len(references) else "start",
        **metrics,
        "geometry": {"type": "LineString", "coordinates": coordinates[index:index + 2]},
    } for index, metrics in enumerate(LEGS)]
    assert {stop["source_layer"] for stop in route["stops"]} == {layer_id}
    assert route["road_geometry"] == RESULT_ROAD
    assert route["legs"] == expected_legs
    assert r["saved"] == route
    assert r["availability"]["road_geometry"] is True
    assert r["availability"]["eta"] is timing
    if timing:
        assert all(type(value) in {int, float} for value in route["eta"])


@pytest.mark.parametrize("fault", ["iso", "partial", "negative", "nonfinite"])
def test_ac007_invalid_eta_rejected(run, fault):
    r = run(operation="result_roundtrip", backend="ors-vroom",
            optimizer_response=invalid_vroom_timing(fault), directions_response=None,
            seed_saved=True)
    rejected(r)
    assert r["candidate"] is None
    assert r["active_after"] == r["active_before"]
    assert r["requests"]


def test_ac008_offline_restart_relocation(run):
    r = run(operation="save_two_restart_move", offline=True, clear_session_key=True,
            settings=PORTABLE_SETTINGS, key=KEY)
    assert len(r["saved_before"]) == 2
    assert len({v["route_id"] for v in r["saved_before"]}) == 2
    assert r["saved_after"] == r["saved_before"]
    assert r["active_after"] == r["active_before"]
    assert Path(r["old_dir"]).resolve() != Path(r["project_dir"]).resolve()
    assert not Path(r["old_dir"]).exists()
    assert r["selected_route_ids"] == [v["route_id"] for v in r["saved_before"]]
    expected_settings = {**PORTABLE_SETTINGS, "mapping": {
        **PORTABLE_SETTINGS["mapping"], "layer": generated_layer_id(r, "조사지")}}
    assert r["settings_before"] == expected_settings
    assert r["settings_after"] == expected_settings
    assert r["session_key_present_after"] is False
    assert KEY not in str(r["settings_before"]) and KEY not in str(r["settings_after"])
    assert KEY not in str(r["saved_before"]) and KEY not in str(r["saved_after"])
    assert KEY not in str(r["logs"])
    for path in Path(r["project_dir"]).rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()
    no_calls(r)


@pytest.mark.parametrize("fault", ["partial_write", "storage_full", "corrupt_latest", "all_corrupt", "revision_conflict"])
def test_ac009_storage_recovery(run, fault):
    r = run(operation="storage_fault", fault=fault)
    assert r["last_good_after"] == r["last_good_before"]
    assert r["outcome"] in {"recovered", "rejected"}
    if r["outcome"] == "rejected":
        assert r["message"].strip()
    else:
        assert r["reloaded"] == r["last_good_before"]
    assert r["published_partial"] is False
    no_calls(r)


@pytest.mark.parametrize("completion_source", ["field", "route_stop"])
def test_ac010_completion(run, completion_source):
    mapping = {"layer": "site", "id": "id", "name": "name"}
    if completion_source == "field":
        mapping["completed"] = "done"
    features = [dict(point, done=False) if completion_source == "field" else point for point in POINTS[:8]]
    r = run(operation="complete", features=features, completed_ids=["0", "1"],
            source=completion_source, mapping=mapping)
    assert r["completed_count"] == 2 and r["total_count"] == 8
    assert r["next_id"] == "2"
    assert {s["site_id"] for s in r["active"]["stops"] if s["completed"]} == {"0", "1"}
    assert {s["site_id"] for s in r["reloaded"]["stops"] if s["completed"]} == {"0", "1"}
    assert r["summary_counts"] == [2, 8]
    assert r["completion_help"]["mapped_boolean_only"] is True
    assert r["completion_help"]["blank_mapping_uses_route_local"] is True
    assert r["source_completion_after"] == ({"0": True, "1": True} if completion_source == "field" else {})
    no_calls(r)


@pytest.mark.parametrize("fault", ["read_only", "invalid_type"])
def test_ac010_completion_write_failure_preserves_state(run, fault):
    r = run(operation="completion_write_failure", fault=fault, completed_id="0", seed_saved=True)
    rejected(r)
    assert r["source_completion_after"] == r["source_completion_before"]
    assert r["active_after"] == r["active_before"]
    assert r["next_after"] == r["next_before"]
    no_calls(r)


def test_ac011_ac026_remaining_recalculation_is_superseded(run):
    r = run(operation="route_progression", mode="roundtrip", completion_source="route_stop",
            actions=[{"complete": "0"}, {"complete": "1"}], relocate=False)
    assert "remaining_recalculate" not in r["controls"]
    assert r["states"][-1]["prefix_length"] == 2
    assert r["states"][-1]["remaining_leg_sequences"] == [3, 4]
    assert r["full_route_after"] == r["full_route_before"]
    no_calls(r)


@pytest.mark.parametrize("launch", [True, False])
def test_ac012_road_and_naver(run, launch):
    name = "조사지 A & B/#?"
    r = run(operation="reopen_navigate", road_geometry=ROAD, destination=[127.123, 37.456], name=name,
            platform="android", caller_id=None, launch_results=[launch, True])
    assert r["rendered_geometry"] == ROAD
    assert r["launcher_calls"][0]["url"] == canonical_naver_android_intent(name)
    url = urlsplit(r["launcher_calls"][0]["url"])
    assert url.scheme == "intent" and url.netloc == "navigation"
    query = parse_qs(url.query)
    assert float(query["dlng"][0]) == 127.123 and float(query["dlat"][0]) == 37.456
    assert query["dname"] == [name] and query["appname"] == ["ch.opengis.qfield"]
    assert url.fragment == ("Intent;scheme=nmap;action=android.intent.action.VIEW;"
                            "category=android.intent.category.BROWSABLE;"
                            "package=com.nhn.android.nmap;end")
    if not launch:
        assert r["launcher_calls"][1]["url"] == NAVER_ANDROID_STORE
        assert r["message"].strip()
    assert r["destination_app_success_claimed"] is False
    no_calls(r)


@pytest.mark.parametrize("action", ["expand", "collapse", "complete", "load", "restart"])
def test_ac013_ac030_no_network_or_secrets(run, action):
    r = run(operation="passive_action", action=action, key=KEY)
    no_calls(r)
    assert KEY not in str(r["logs"])
    root = Path(r["project_dir"])
    assert list(root.rglob("*"))
    for path in root.rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()
    assert KEY not in str(r["saved_after"])


@pytest.mark.parametrize("kind,vertices", [("Point", [[127, 37]]), ("LineString", [[127, 37], [127.1, 37.2]]),
                                            ("Polygon", [[127, 37], [127.1, 37], [127, 37.1], [127, 37]])])
def test_ac014_direct_drawing(run, kind, vertices):
    r = run(operation="draw", geometry_type=kind, vertices=vertices, names=["첫 대상", "둘째 대상"])
    assert r["offered_types"] == ["Point", "LineString", "Polygon"]
    assert r["saved_names"] == ["첫 대상", "둘째 대상"]
    assert len(set(r["site_ids"])) == 2
    assert r["geometry_types"] == [kind, kind]
    assert r["finished"] is True


@pytest.mark.parametrize("kind,vertices", [("Point", []), ("LineString", [[1, 1], [1, 1]]),
                                            ("Polygon", [[0, 0], [1, 1]]), ("Polygon", [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]])])
def test_ac014_incomplete_drawing(run, kind, vertices):
    r = run(operation="draw", geometry_type=kind, vertices=vertices, names=["invalid"])
    assert r["ok"] is False and r["message"].strip()
    assert r["saved_names"] == []


GEOMETRIES = {
    "Point": "POINT (0 0)",
    "LineString": "LINESTRING (0 0, 4 0, 4 2)",
    "Polygon": "POLYGON ((0 0, 6 0, 0 3, 0 0))",
    "MultiPoint": "MULTIPOINT ((0 0), (6 3), (3 6))",
    "MultiLineString": "MULTILINESTRING ((0 0, 4 0), (4 0, 4 2))",
    "MultiPolygon": "MULTIPOLYGON (((0 0, 6 0, 0 3, 0 0)), ((10 0, 12 0, 10 2, 10 0)))",
}


GEOJSON = {
    "Point": {"type": "Point", "coordinates": [0, 0]},
    "LineString": {"type": "LineString", "coordinates": [[0, 0], [4, 0], [4, 2]]},
    "Polygon": {"type": "Polygon", "coordinates": [[[0, 0], [6, 0], [0, 3], [0, 0]]]},
    "MultiPoint": {"type": "MultiPoint", "coordinates": [[0, 0], [6, 3], [3, 6]]},
    "MultiLineString": {"type": "MultiLineString", "coordinates": [[[0, 0], [4, 0]], [[4, 0], [4, 2]]]},
    "MultiPolygon": {"type": "MultiPolygon", "coordinates": [[[[0, 0], [6, 0], [0, 3], [0, 0]]], [[[10, 0], [12, 0], [10, 2], [10, 0]]]]},
}


def geometry_signature(geometry):
    """Fixture comparison: preserve segments/parts/holes, allow ring orientation/start changes."""
    kind, coords = geometry["type"], geometry["coordinates"]
    family = kind.removeprefix("Multi")
    parts = coords if kind.startswith("Multi") else [coords]
    def line(points):
        points = tuple(tuple(p[:2]) for p in points)
        return min(points, points[::-1])
    def ring(points):
        points = tuple(tuple(p[:2]) for p in points[:-1])
        rotations = [points[i:] + points[:i] for i in range(len(points))]
        return min(rotations + [v[::-1] for v in rotations])
    if family == "Point":
        normalized = [tuple(p[:2]) for p in parts]
    elif family == "LineString":
        normalized = [line(p) for p in parts]
    else:
        normalized = [(ring(p[0]), tuple(sorted(ring(h) for h in p[1:]))) for p in parts]
    return family, tuple(sorted(normalized))


def fixture_wkt(geometry, projected=False):
    def encode(value):
        if isinstance(value[0], (int, float)):
            x, y = value
            if projected:
                x, y = x * 100000 + 1000000, y * 100000 + 5000000
            return f"{x} {y}"
        return "(" + ", ".join(encode(v) for v in value) + ")"
    text = encode(geometry["coordinates"])
    return geometry["type"].upper() + " " + ("(" + text + ")" if geometry["type"] == "Point" else text)


@pytest.mark.parametrize("fmt", ["SHP", "ZIP", "GPKG"])
@pytest.mark.parametrize("kind", GEOMETRIES)
def test_ac015_ac016_uploaded_geometry(run, tmp_path, fmt, kind):
    import fiona
    from zipfile import ZipFile

    geom = GEOJSON[kind]
    source = tmp_path / ("source.gpkg" if fmt == "GPKG" else "source.shp")
    schema_type = kind.removeprefix("Multi") if fmt != "GPKG" and kind in {"MultiLineString", "MultiPolygon"} else kind
    with fiona.open(source, "w", driver="GPKG" if fmt == "GPKG" else "ESRI Shapefile", crs="EPSG:4326",
                    schema={"geometry": schema_type, "properties": {"site_name": "str"}}) as dst:
        for name in ["first", "second"]:
            dst.write({"geometry": geom, "properties": {"site_name": name}})
    if fmt == "ZIP":
        source = tmp_path / "upload.zip"
        with ZipFile(source, "w") as archive:
            for member in tmp_path.glob("source.*"):
                archive.write(member, arcname=member.name)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("source.*")}
    r = run(operation="upload_build", source=str(source), survey_type="temporary_plots")
    assert r["detected_type"] == kind
    with fiona.open(r["gpkg_path"], layer="site") as layer:
        rows = list(layer)
        assert len(rows) == 2
        assert {v["properties"]["site_name"] for v in rows} == {"first", "second"}
        assert len({v["properties"]["site_id"] for v in rows}) == 2
        assert all(geometry_signature(v["geometry"]) == geometry_signature(geom) for v in rows)
        actual_types = {v["geometry"]["type"].upper() for v in rows}
    with sqlite3.connect(r["gpkg_path"]) as db:
        metadata, column = db.execute("SELECT geometry_type_name,column_name FROM gpkg_geometry_columns WHERE table_name='site'").fetchone()
        assert actual_types == {metadata.upper()}
        assert db.execute(f'SELECT COUNT(*) FROM "rtree_site_{column}"').fetchone()[0] == 2
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert r["project_geometry_type"].upper() == metadata.upper()
    assert before == {p.name: p.read_bytes() for p in tmp_path.glob("source.*")}


@pytest.mark.parametrize("kind", ["Point", "LineString", "Polygon"])
def test_ac016_direct_generated_geometry(run, kind):
    r = run(operation="direct_build", geometry_type=kind, wkt=GEOMETRIES[kind])
    assert r["stored_family"] == kind
    assert r["metadata_family"] == kind and r["project_family"] == kind
    assert r["rtree_ids"] == r["feature_ids"]


@pytest.mark.parametrize("fault", ["mixed_families", "empty", "invalid_geometry"])
def test_ac015_invalid_geometry(run, fault):
    r = run(operation="geometry_failure", fault=fault)
    assert r["ok"] is False and r["message"].strip()
    assert r["published_features"] == []
    no_calls(r)


@pytest.mark.parametrize("fault", ["missing_crs", "invalid_crs", "transform_failure"])
def test_ac017_invalid_source_crs_preserves_saved(run, fault):
    r = run(operation="generated_geometry_calculate", fault=fault, seed_saved=True,
            evaluator_contract=QFIELD_EXPRESSION_EVALUATOR)
    rejected(r)
    assert r["failure_reason"] == fault
    baseline = r["seed_saved_provenance"]
    assert baseline["created_via"] == "production_save_action"
    assert baseline["route_count"] >= 1 and baseline["active_route_id"]
    assert baseline["independently_reopened_route_id"] == baseline["active_route_id"]
    assert r["active_before"]["route_id"] == baseline["active_route_id"]
    assert_project_relative_file(r, baseline["storage_project_relative_path"])
    assert r["active_after"] == r["active_before"]
    no_calls(r)


# Source-space centroids: line length-weighted (8/3,1/3), triangle area-weighted (2,1).
# MultiPolygon: areas 9 and 2, centroids (2,1) and (32/3,2/3).
CENTROIDS = {"Point": [0, 0], "LineString": [8 / 3, 1 / 3], "Polygon": [2, 1],
             "MultiPoint": [3, 3], "MultiLineString": [8 / 3, 1 / 3], "MultiPolygon": [118 / 33, 31 / 33]}


def expected_wgs84(kind, crs):
    import math

    expected = CENTROIDS[kind]
    if crs == "EPSG:3857":
        x, y = expected[0] * 100000 + 1000000, expected[1] * 100000 + 5000000
        return [math.degrees(x / 6378137), math.degrees(2 * math.atan(math.exp(y / 6378137)) - math.pi / 2)]
    return expected


@pytest.mark.parametrize("crs", ["EPSG:4326", "EPSG:3857"])
@pytest.mark.parametrize("kind", GEOMETRIES)
def test_ac017_representatives_numerical(run, crs, kind):
    geom = GEOJSON[kind]
    expected = expected_wgs84(kind, crs)
    r = run(operation="representative", wkt=fixture_wkt(geom, projected=crs == "EPSG:3857"), crs=crs)
    assert r["coordinate"] == pytest.approx(expected, abs=1e-7)
    assert r["original_after"] == r["original_before"]
    assert r["request_coordinate"] == pytest.approx(expected, abs=1e-7)


@pytest.mark.parametrize("crs", ["EPSG:4326", "EPSG:3857"])
@pytest.mark.parametrize("kind", GEOMETRIES)
def test_ac017_generated_geometry_uses_qfield_expression_evaluator(run, crs, kind):
    expected = expected_wgs84(kind, crs)
    r = run(operation="generated_geometry_calculate", geometry_type=kind,
            wkt=fixture_wkt(GEOJSON[kind], projected=crs == "EPSG:3857"), crs=crs,
            evaluator_contract=QFIELD_EXPRESSION_EVALUATOR)
    assert r["ok"] is True
    assert r["generic_crs_error_shown"] is False
    assert r["request_coordinate"] == pytest.approx(expected, abs=1e-7)
    assert r["original_after"] == r["original_before"]
    evaluator = r["expression_evaluator"]
    assert evaluator["native_type"] == "QfExpressionEvaluator"
    assert evaluator["qml_type"] == "ExpressionEvaluator"
    assert {"feature", "layer", "project"} <= set(evaluator["properties_written"])
    assert not evaluator["unknown_property_writes"]
    assert evaluator["evaluate_calls"]
    assert {call["arity"] for call in evaluator["evaluate_calls"]} <= {0, 1}
    expressions = [call["expression_text"].lower() for call in evaluator["evaluate_calls"]]
    assert all("geom_to_geojson" not in expression for expression in expressions)
    assert any("transform" in expression for expression in expressions)
    assert any("x(" in expression for expression in expressions)
    assert any("y(" in expression for expression in expressions)
    if kind != "Point":
        assert any("centroid" in expression for expression in expressions)
    assert r["qml_errors"] == []


@pytest.mark.parametrize("survey_type", ["simple_inventory", "temporary_plots", "permanent_plots", "vegetation_mapping"])
@pytest.mark.parametrize("reference", [False, True])
def test_ac018_ac030_regression_portability(run, survey_type, reference):
    r = run(operation="regression", survey_type=survey_type, reference=reference, relocate=True)
    assert r["uuid_after"] == r["uuid_before"]
    assert r["relations_after"] == r["relations_before"]
    assert r["non_site_geometry_after"] == r["non_site_geometry_before"]
    assert r["broken_sources"] == [] and r["validation_errors"] == []
    assert r["identification_candidate"]["scientific_name"] == "Synthetic species"
    assert r["report_rows"]
    for row in r["report_rows"]:
        if row["geometry_type"] != "Point":
            assert row["longitude"] is None and row["latitude"] is None
    assert r["ktsn_present"] is reference
    assert r["legacy_polygon_after"] == r["legacy_polygon_before"]
    assert r["existing_user_project_after"] == r["existing_user_project_before"]


@pytest.mark.parametrize("case", ["M01_project_dropdowns_layout", "M02_schema2_live_route",
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
def test_manual_qfield_device(case):
    pytest.skip(f"User-run QField iOS/Android case {case}; see test design. No device PASS implied.")

@pytest.mark.parametrize("source_wkts,expected", [
    (["POINT (1 2)", "MULTIPOINT ((3 4), (5 6))"], [{"type": "Point", "coordinates": [1, 2]}, {"type": "MultiPoint", "coordinates": [[3, 4], [5, 6]]}]),
    (["LINESTRING (0 0, 1 1)", "MULTILINESTRING ((2 2, 3 3), (4 4, 5 5))"], [{"type": "LineString", "coordinates": [[0, 0], [1, 1]]}, {"type": "MultiLineString", "coordinates": [[[2, 2], [3, 3]], [[4, 4], [5, 5]]]}]),
    (["POLYGON ((0 0, 6 0, 6 6, 0 6, 0 0),(1 1, 1 2, 2 2, 2 1, 1 1))"], [{"type": "Polygon", "coordinates": [[[0, 0], [6, 0], [6, 6], [0, 6], [0, 0]], [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]]}]),
    (["POINT Z (1 2 50)"], [{"type": "Point", "coordinates": [1, 2]}]),
])
def test_ac015_ac016_parts_holes_xy(run, source_wkts, expected):
    r = run(operation="geometry_roundtrip", wkts=source_wkts, crs="EPSG:4326")
    assert len(r["stored_geometries"]) == len(expected)
    for actual, wanted in zip(r["stored_geometries"], expected):
        assert geometry_signature(actual) == geometry_signature(wanted)
    assert r["metadata_matches_storage"] is True


def test_ac017_projected_control_point(run):
    r = run(operation="representative", wkt="POINT (200000 600000)", crs="EPSG:5186")
    assert r["coordinate"] == pytest.approx([127, 38], abs=1e-7)
    assert r["original_after"] == r["original_before"]


def test_ac010_ac011_ac027_all_complete_uses_saved_full_route(run):
    r = run(operation="route_progression", mode="open", completion_source="route_stop",
            actions=[{"complete": "0"}, {"complete": "1"}, {"complete": "2"}], relocate=False)
    state = r["states"][-1]
    assert state["next_id"] is None
    assert state["prefix_length"] == 3
    assert state["remaining_leg_sequences"] == []
    assert state["remaining_distance_m"] == 0 and state["remaining_duration_s"] == 0
    assert r["full_route_after"] == r["full_route_before"]
    no_calls(r)


@pytest.mark.parametrize("configured_offset,expected_offset", [(50, 50), (None, 1000)])
def test_ac013_backend_settings(run, configured_offset, expected_offset):
    settings = {"server_url": "https://routing.invalid/ors",
                "optimizer_url": "https://optimizer.invalid/vroom", "backend": "ors-vroom",
                "profile": "driving-car", "timeout_ms": 1250, "objective": "distance", "key": KEY}
    if configured_offset is not None:
        settings["max_road_offset_m"] = configured_offset
    r = run(operation="configured_calculate", settings=settings, seed_saved=True)
    assert r["transport_settings"] == dict(settings, max_road_offset_m=expected_offset)
    expected_persisted = dict(settings, max_road_offset_m=expected_offset)
    expected_persisted.pop("key")
    expected_persisted.pop("objective")
    assert {key: r["persisted_settings"][key] for key in expected_persisted} == expected_persisted
    assert "key" not in r["persisted_settings"]
    assert r["requests"]
    assert r["saved_before"] and r["saved_after"] == r["saved_before"]
    assert r["active_after"] == r["active_before"]
    assert KEY not in str(r["logs"]) and KEY not in str(r["persisted_settings"])
    assert KEY not in str(r.get("message")) and KEY not in str(r.get("qml_errors"))
    root = Path(r["project_dir"])
    for path in root.rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()


def assert_provider_urls(result, routing_base, optimizer_url):
    requests = requests_by_kind(result)
    assert set(requests) == {"origin-validation", "access-snap", "matrix", "optimizer", "directions"}
    expected = {"origin-validation": f"{routing_base}/v2/matrix/driving-car",
                "access-snap": f"{routing_base}/v2/snap/driving-car/json",
                "matrix": f"{routing_base}/v2/matrix/driving-car",
                "directions": f"{routing_base}/v2/directions/driving-car/geojson",
                "optimizer": optimizer_url}
    assert all({request["url"] for request in requests[kind]} == {url} for kind, url in expected.items())
    assert all(request["method"] == "POST" for request in result["requests"])
    assert all("/vroom/v0/post" not in request["url"] for request in result["requests"])


def test_ac013_fresh_hosted_defaults_and_authorization(run):
    r = run(operation="configured_calculate", settings={"backend": "ors-vroom", "profile": "driving-car",
                                                         "key": KEY}, fresh_project=True, seed_saved=True)
    assert r["transport_settings"]["server_url"] == HOSTED_ROUTING_BASE
    assert r["transport_settings"]["optimizer_url"] == HOSTED_OPTIMIZER_URL
    assert_provider_urls(r, HOSTED_ROUTING_BASE, HOSTED_OPTIMIZER_URL)
    assert_authorization_only(r, KEY)
    assert all("api.openrouteservice.org" not in request["url"] for request in r["requests"])


def test_ac013_trailing_slashes_are_normalized_once(run):
    settings = {"server_url": HOSTED_ROUTING_BASE + "/", "optimizer_url": HOSTED_OPTIMIZER_URL + "/",
                "backend": "ors-vroom", "profile": "driving-car", "key": KEY}
    r = run(operation="configured_calculate", settings=settings, seed_saved=True)
    assert_provider_urls(r, HOSTED_ROUTING_BASE, HOSTED_OPTIMIZER_URL)
    assert r["persisted_settings"]["server_url"] == HOSTED_ROUTING_BASE
    assert r["persisted_settings"]["optimizer_url"] == HOSTED_OPTIMIZER_URL
    assert_authorization_only(r, KEY)


@pytest.mark.parametrize("server_url,optimizer_url,expected_server,expected_optimizer", [
    (LEGACY_ROUTING_BASE, None, HOSTED_ROUTING_BASE, HOSTED_OPTIMIZER_URL),
    (LEGACY_ROUTING_BASE + "/", "", HOSTED_ROUTING_BASE, HOSTED_OPTIMIZER_URL),
    ("https://routing.example/ors", LEGACY_OPTIMIZER_URL,
     "https://routing.example/ors", HOSTED_OPTIMIZER_URL),
    (LEGACY_ROUTING_BASE, "https://optimizer.example/custom",
     HOSTED_ROUTING_BASE, "https://optimizer.example/custom"),
    (LEGACY_ROUTING_BASE + "/custom", LEGACY_OPTIMIZER_URL,
     LEGACY_ROUTING_BASE + "/custom", HOSTED_OPTIMIZER_URL),
])
def test_ac013_exact_legacy_default_migration(run, server_url, optimizer_url, expected_server, expected_optimizer):
    settings = {"server_url": server_url, "backend": "ors-vroom", "profile": "driving-car", "key": KEY}
    if optimizer_url is not None:
        settings["optimizer_url"] = optimizer_url
    r = run(operation="configured_calculate", settings=settings, seed_saved=True)
    assert r["persisted_settings"]["server_url"] == expected_server
    assert r["persisted_settings"]["optimizer_url"] == expected_optimizer
    assert_provider_urls(r, expected_server, expected_optimizer)
    assert_authorization_only(r, KEY)


def test_ac013_custom_self_hosted_urls_allow_no_key(run):
    settings = {"server_url": "http://routing.local/ors/",
                "optimizer_url": "https://optimizer.local/vroom/custom/", "backend": "ors-vroom",
                "profile": "driving-car"}
    r = run(operation="configured_calculate", settings=settings, seed_saved=True)
    assert_provider_urls(r, "http://routing.local/ors", "https://optimizer.local/vroom/custom")
    assert r["persisted_settings"]["server_url"] == "http://routing.local/ors"
    assert r["persisted_settings"]["optimizer_url"] == "https://optimizer.local/vroom/custom"
    assert_authorization_only(r, None)


def test_ac013_hosted_default_rejects_blank_key_before_request(run):
    r = run(operation="configured_calculate", settings={"backend": "ors-vroom", "profile": "driving-car"},
            fresh_project=True, seed_saved=True)
    rejected(r)
    assert r["active_after"] == r["active_before"]
    no_calls(r)


def test_ac019_builder_key_consent_embeds_only_project_variable(run):
    r = run(operation="builder_route_key", input_key=KEY, consent=True, outcome="success",
            calculate_after_build=True)
    assert r["key_input_echo_mode"] == "password"
    assert r["consent_required"] is True
    observed = {widget["semantic_id"]: widget for widget in r["widgets"]}
    warning = observed["route_key_plaintext_warning"]["text"]
    consent = observed["route_key_consent"]["text"]
    assert warning == STEP7_ROUTE_KEY_COPY["plaintext_warning"]
    assert consent == STEP7_ROUTE_KEY_COPY["consent"]
    assert "QField가 자동으로 사용하도록" in warning
    assert "암호화되지 않은 글자" in warning
    assert "프로젝트 폴더를 열 수 있는 사람은 누구나 키를 확인하고 사용할 수 있습니다." in warning
    assert r["qfield_key_source"] == "project_variable"
    assert r["transport_key_present"] is True
    assert_no_key_outside_project_variable(r, embedded=True)


@pytest.mark.parametrize("input_key,consent", [(KEY, False), ("", None)])
def test_ac019_decline_or_blank_uses_manual_session_only(run, input_key, consent):
    r = run(operation="builder_route_key", input_key=input_key, consent=consent, outcome="success",
            manual_session_key=KEY, calculate_after_build=True)
    assert r["key_input_echo_mode"] == "password"
    assert r["manual_session_available"] is True
    assert r["qfield_key_source"] == "session"
    assert r["session_key_present_after_restart"] is False
    assert r["transport_key_present"] is True
    assert_no_key_outside_project_variable(r, embedded=False)


@pytest.mark.parametrize("outcome", ["cancel", "generation_failure"])
def test_ac019_key_never_leaks_from_aborted_builder_flow(run, outcome):
    r = run(operation="builder_route_key", input_key=KEY, consent=True, outcome=outcome)
    assert r["project_published"] is False
    assert r["transport_key_present"] is False
    no_calls(r)
    assert_no_key_outside_project_variable(r, embedded=False)


def test_ac019_desktop_remember_is_not_qfield_delivery(run):
    r = run(operation="builder_route_key", input_key=KEY, consent=False, remember=True, outcome="success")
    assert Path(r["desktop_credential_store"]).name == "credentials.enc"
    assert r["remembered_key_available_to_qfield"] is False
    assert r["manual_session_available"] is True
    assert r["transport_key_present"] is False
    assert_no_key_outside_project_variable(r, embedded=False)


@pytest.mark.parametrize("viewport_width", [320, 1024])
def test_ac020_route_panel_fields_fill_available_width(run, viewport_width):
    r = run(operation="panel_layout", viewport_width=viewport_width)
    left, right = r["content_rect"]["left"], r["content_rect"]["right"]
    assert 0 <= left < right <= viewport_width
    rows = {}
    for field in r["fields"]:
        assert left <= field["left"] < field["right"] <= right
        rows.setdefault(field["row"], []).append(field)
    assert rows
    for fields in rows.values():
        assert min(field["left"] for field in fields) == pytest.approx(left, abs=1)
        assert max(field["right"] for field in fields) == pytest.approx(right, abs=1)
        assert max(field["right"] - field["left"] for field in fields) - min(
            field["right"] - field["left"] for field in fields) <= 1
    assert all(item["left"] == pytest.approx(left, abs=1) for item in r["labels_help_errors"])
    assert all(item["right"] <= right + 1 and item["wrap_enabled"] for item in r["labels_help_errors"])
    assert r["horizontal_overflow"] is False
    screenshot = Path(r["screenshot_path"])
    assert screenshot.is_file() and screenshot.stat().st_size > 0


@pytest.mark.parametrize("viewport_width", [320, 1024])
@pytest.mark.parametrize("selector_state", ["empty", "value", "focus", "error"])
def test_ac031_six_selectors_use_ors_floating_labels_without_collision(run, viewport_width, selector_state):
    mapping = {"layer_id": SITE_LAYER_ID, "id_field": "site_id", "name_field": "site_name",
               "completion_field": "completed"}
    r = run(operation="panel_layout", viewport_width=viewport_width, selector_state=selector_state,
            observe_floating_labels=True, stored_mapping=mapping)
    assert set(AC031_FLOATING_LABEL_SUBSET) < set(FINAL_FLOATING_LABELS)
    assert set(r["floating_selectors"]) == set(AC031_FLOATING_LABEL_SUBSET)
    assert not [row for row in r["separate_label_rows"]
                if row["text"] in AC031_FLOATING_LABEL_SUBSET.values()]
    assert r["placeholder_only_accessible_names"] == []
    assert r["horizontal_overflow"] is False
    assert r["qml_runtime"]["loaded_generated_qml"] is True
    assert Path(r["qml_runtime"]["generated_qml_path"]).is_file()
    selector_object_ids = set()
    label_object_ids = set()
    for selector_id, expected_label in AC031_FLOATING_LABEL_SUBSET.items():
        selector = r["floating_selectors"][selector_id]
        selector_object_ids.add(selector["control_object_id"])
        label_object_ids.add(selector["label_object_id"])
        assert selector["evidence_source"] == "loaded_generated_qml_object_tree"
        assert selector["control_object_id"] and selector["label_object_id"]
        assert selector["control_object_id"] != selector["label_object_id"]
        assert selector["visible"] is True and selector["enabled"] is True
        assert selector["label"] == expected_label
        assert selector["label_visible"] is True
        assert selector["accessibility"] == {
            "role": "ComboBox", "name": expected_label, "visible": True, "enabled": True,
        }
        reference_style = r["ors_server_url_reference"]["style_metrics"]
        assert {key: selector["style_metrics"][key] for key in
                ("font_pixel_size", "top_inset", "top_padding", "bottom_padding")} == {
                    key: reference_style[key] for key in
                    ("font_pixel_size", "top_inset", "top_padding", "bottom_padding")}
        if selector["style_metrics"]["normal_color"] != reference_style["normal_color"]:
            assert selector["style_metrics"]["normal_color"] == selector["style_metrics"]["focus_color"]
        assert selector["control_rect"]["width"] > 0 and selector["control_rect"]["height"] > 0
        assert selector["label_rect"]["width"] > 0 and selector["label_rect"]["height"] > 0
        if selector["option_text_rect"] is not None:
            assert not rects_overlap(selector["label_rect"], selector["option_text_rect"])
        if selector_state == "focus":
            assert selector["focus_indicator_visible"] is True
    assert len(selector_object_ids) == len(AC031_FLOATING_LABEL_SUBSET)
    assert len(label_object_ids) == len(AC031_FLOATING_LABEL_SUBSET)
    assert r["stored_mapping_after"] == r["stored_mapping_before"] == mapping
    no_calls(r)


def test_ac006_ac013_unknown_backend_rejected_before_request(run):
    settings = {"server_url": "https://routing.invalid/ors",
                "optimizer_url": "https://optimizer.invalid/vroom", "backend": "unknown-backend",
                "profile": "driving-car", "timeout_ms": 1250, "max_road_offset_m": 50,
                "objective": "time", "key": KEY}
    r = run(operation="configured_calculate", settings=settings, seed_saved=True)
    rejected(r)
    no_calls(r)
    assert r["active_after"] == r["active_before"]
    assert "key" not in r["persisted_settings"]
    assert KEY not in str(r["logs"]) and KEY not in str(r["saved_after"])
    assert KEY not in str(r.get("message")) and KEY not in str(r.get("qml_errors"))
    for path in Path(r["project_dir"]).rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()


def test_ac021_layer_dropdown_uses_alias_stable_id_and_site_default(run):
    r = run(operation="project_dropdowns", layers=PROJECT_LAYERS, stored_mapping=None,
            actions=["open", "reopen"])
    assert [option["layer_id"] for option in r["layer_options"]] == [
        layer["layer_id"] for layer in PROJECT_LAYERS]
    assert len({option["label"] for option in r["layer_options"]}) == len(PROJECT_LAYERS)
    assert all(option["label"].startswith("표본구") for option in
               [r["layer_options"][0], r["layer_options"][2]])
    site = next(option for option in r["layer_options"] if option["layer_id"] == SITE_LAYER_ID)
    assert site == {"label": "조사지", "layer_id": SITE_LAYER_ID, "source_name": "site"}
    assert r["selected_layer_id"] == SITE_LAYER_ID
    assert r["stored_mapping"]["layer_id"] == SITE_LAYER_ID


def test_ac021_duplicate_label_resolves_by_stable_id(run):
    r = run(operation="project_dropdowns", layers=PROJECT_LAYERS,
            stored_mapping={"layer_id": "duplicate-b", "id_field": "manual_code", "name_field": "manual_title"},
            actions=["open", "save", "reopen"])
    assert r["selected_layer_id"] == "duplicate-b"
    assert r["selected_fields"] == {"id": "manual_code", "name": "manual_title"}
    assert r["stored_mapping"]["layer_id"] == "duplicate-b"
    assert r["field_options"] == PROJECT_LAYERS[2]["fields"]


@pytest.mark.parametrize("trigger", ["layer_change", "panel_reopen", "schema_change", "calculate_preflight", "save_preflight"])
def test_ac021_field_refresh_provider_order_defaults_and_stale_values(run, trigger):
    fields = ["uuid", "first_ID", "first_NAME", "second_id", "second_name"]
    r = run(operation="project_dropdowns", layers=PROJECT_LAYERS, selected_layer_id="duplicate-b",
            stored_mapping={"layer_id": "duplicate-b", "id_field": "gone_id", "name_field": "gone_name"},
            refreshed_fields=fields, actions=[trigger])
    assert r["field_options"] == fields
    assert r["selected_fields"] == {"id": "first_ID", "name": "first_NAME"}
    assert r["refresh_triggers"] == [trigger]


def test_ac021_no_field_match_and_stale_layer_clear_and_block(run):
    r = run(operation="project_dropdowns",
            layers=[{"layer_id": "only", "source_name": "targets", "alias": "대상", "fields": ["uuid", "title"]}],
            stored_mapping={"layer_id": "removed", "id_field": "old_id", "name_field": "old_name"},
            actions=["open", "calculate_preflight", "save_preflight"])
    assert r["selected_layer_id"] is None
    assert r["selected_fields"] == {"id": None, "name": None}
    assert r["calculate_enabled"] is False and r["save_enabled"] is False
    assert r["validation_message"].strip()
    no_calls(r)


@pytest.mark.parametrize("viewport_width", [320, 1024])
@pytest.mark.parametrize("start_mode,visible", [
    ("gps", {"map_center": False, "target": False}),
    ("map", {"map_center": True, "target": False}),
    ("target", {"map_center": False, "target": True}),
])
def test_ac022_ac024_labels_guidance_and_conditional_controls(run, viewport_width, start_mode, visible):
    r = run(operation="route_workflow_ui", viewport_width=viewport_width, start_mode=start_mode,
            scope="all", targets=[{"id": "site-01", "name": "첫 조사지", "selected": False}],
            selected_target_id="site-01")
    assert r["labels"] == WORKFLOW_LABELS
    assert r["guidance"] == "방문 순서대로 이동하고, 조사를 마친 지점을 체크하세요."
    assert r["controls_visible"]["map_center"] is visible["map_center"]
    assert r["controls_visible"]["target"] is visible["target"]
    assert r["target_options"] == [{"label": "첫 조사지 · site-01", "value": "site-01"}]
    assert r["selected_target_id"] == "site-01"
    assert r["horizontal_overflow"] is False
    assert all(item["wrap_enabled"] for item in r["label_guidance_rects"])


def test_ac022_stale_target_is_cleared_and_blocks_target_start(run):
    r = run(operation="route_workflow_ui", viewport_width=320, start_mode="target",
            targets=[{"id": "site-02", "name": "둘째 조사지"}], selected_target_id="removed",
            mapping_changed=True)
    assert r["selected_target_id"] is None
    assert r["calculate_enabled"] is False and r["validation_message"].strip()
    no_calls(r)


@pytest.mark.parametrize("viewport_width", [320, 1024])
@pytest.mark.parametrize("scope", ["selected", "all", "uncompleted"])
@pytest.mark.parametrize("count", [0, 1, 3])
def test_ac034_selection_guidance_is_selected_only_and_leaves_no_gap(run, viewport_width, scope, count):
    features, expected_ids = candidate_fixture(scope, count)
    r = run(operation="route_workflow_ui", viewport_width=viewport_width, start_mode="target",
            scope=scope, targets=features, selected_target_id=None, observe_candidate_preflight=True)
    assert r["common_scope_guidance"].strip()
    expected_rows = ["common_scope_guidance"]
    if scope == "selected":
        expected_rows.append("selection_guidance")
        assert r["selection_guidance"] == SELECTION_GUIDANCE.format(count=count)
        assert r["selection_count"] == count == len(expected_ids)
    else:
        assert r["selection_guidance"] is None and r["selection_count"] is None
    expected_rows.append("next_control")
    rows = r["rendered_scope_rows"]
    assert [row["semantic_id"] for row in rows] == expected_rows
    assert len({row["object_id"] for row in rows}) == len(rows)
    assert all(row["visible"] is True and row["rect"]["height"] > 0 for row in rows)
    rendered = {row["semantic_id"]: row["rendered_text"] for row in rows}
    assert rendered["common_scope_guidance"] == r["common_scope_guidance"]
    if scope == "selected":
        assert rendered["selection_guidance"] == SELECTION_GUIDANCE.format(count=count)
    actual_gaps = [second["rect"]["top"] - first["rect"]["bottom"]
                   for first, second in zip(rows, rows[1:])]
    assert actual_gaps == pytest.approx([r["standard_vertical_spacing"]] * len(actual_gaps), abs=1)
    if scope != "selected":
        hidden = r["qml_scope_items"]["selection_guidance"]
        assert hidden["visible"] is False and hidden["layout_rect"] is None
        assert "selection_guidance" not in r["visible_layout_semantic_ids"]
    assert r["unattributed_visible_scope_rows"] == []
    no_calls(r)


@pytest.mark.parametrize("scope", ["selected", "all", "uncompleted"])
@pytest.mark.parametrize("count", [0, 1, 3])
def test_ac033_target_candidates_match_preflight_before_required_validation(run, scope, count):
    features, expected_ids = candidate_fixture(scope, count)
    r = run(operation="route_workflow_ui", viewport_width=320, start_mode="target", scope=scope,
            targets=features, selected_target_id=None, observe_candidate_preflight=True)
    expected_options = [{"label": f"{feature['name']} · {feature['id']}", "value": feature["id"]}
                        for feature in features if feature["id"] in expected_ids]
    assert r["target_options"] == expected_options
    assert_independent_preflight_capture(r, expected_ids)
    assert r["selected_target_id"] is None
    assert r["validation_message"].strip()
    no_calls(r)


def test_ac033_candidate_refresh_preserves_valid_id_and_clears_stale_after_changes(run):
    transitions = [
        {"action": "qfield_selection", "selected_ids": ["site-03", "site-01"]},
        {"action": "qfield_selection", "selected_ids": ["site-02"]},
        {"action": "scope", "scope": "uncompleted"},
        {"action": "completion", "completed_ids": ["site-01", "site-02"]},
        {"action": "mapping", "id_field": "alt_id", "name_field": "alt_name"},
    ]
    r = run(operation="route_workflow_ui", viewport_width=320, start_mode="target", scope="selected",
            targets=deepcopy(TARGET_FEATURES), selected_target_id="site-03",
            candidate_transitions=transitions, observe_candidate_preflight=True)
    states = r["candidate_states"]
    expected_states = [["site-03", "site-02"], ["site-03", "site-01"], ["site-02"],
                       ["site-03", "site-02"], ["site-03"], ["A-03"]]
    for state, expected_ids in zip(states, expected_states):
        assert_independent_preflight_capture(state, expected_ids)
    assert states[0]["selected_target_id"] == states[1]["selected_target_id"] == "site-03"
    assert states[2]["selected_target_id"] is None and states[2]["validation_message"].strip()
    assert states[-1]["target_options"] == [{"label": "대체 이름 · A-03", "value": "A-03"}]
    assert all(state["refresh_before_validation"] is True for state in states)
    no_calls(r)


def test_ac032_map_start_marker_is_exact_fixed_and_replaced_not_duplicated(run):
    first = [127.1234567, 37.4567891]
    second = [127.2234567, 37.5567891]
    r = run(operation="map_start_marker", project_crs="EPSG:4326", actions=[
        {"action": "capture_center", "center": first},
        {"action": "pan_zoom", "center": [128, 38], "zoom": 17},
        {"action": "capture_center", "center": second},
    ])
    captured, panned, replaced = r["states"]
    assert captured["start_wgs84"] == pytest.approx(first, abs=1e-9)
    assert captured["canvas_marker_count"] == len(captured["canvas_markers"]) == 1
    marker = captured["canvas_markers"][0]
    assert marker["semantic_role"] == "start_marker" and marker["object_id"]
    assert marker["coordinate"] == pytest.approx(first, abs=1e-9)
    assert marker["visible_text"] == "출발지" and marker["accessible_name"] == "출발지"
    assert marker["visible"] is True and marker["contrast_ratio"] >= 3
    assert panned["canvas_markers"] == captured["canvas_markers"]
    assert replaced["start_wgs84"] == pytest.approx(second, abs=1e-9)
    assert replaced["canvas_marker_count"] == len(replaced["canvas_markers"]) == 1
    assert replaced["canvas_markers"][0]["coordinate"] == pytest.approx(second, abs=1e-9)
    assert_zero_marker_writes(r)
    assert r["source_renderer_after"] == r["source_renderer_before"]


@pytest.mark.parametrize("event", ["panel_collapse_reopen", "calculation_failure", "calculation_success"])
def test_ac032_map_start_marker_survives_panel_and_calculation_events(run, event):
    r = run(operation="map_start_marker", project_crs="EPSG:4326", seed_center=[127.1, 37.1],
            actions=[{"action": event}])
    assert r["states"][0]["canvas_markers"] == r["states"][-1]["canvas_markers"]
    assert r["states"][-1]["canvas_marker_count"] == len(r["states"][-1]["canvas_markers"]) == 1
    assert_zero_marker_writes(r)
    assert r["saved_route_geometry_after"] == r["saved_route_geometry_before"]


@pytest.mark.parametrize("event", ["mode_change", "clear", "invalidate", "project_close"])
def test_ac032_map_start_marker_removed_at_lifecycle_end(run, event):
    r = run(operation="map_start_marker", project_crs="EPSG:4326", seed_center=[127.1, 37.1],
            actions=[{"action": event}])
    assert r["states"][0]["canvas_marker_count"] == len(r["states"][0]["canvas_markers"]) == 1
    assert r["states"][-1]["canvas_marker_count"] == 0 and r["states"][-1]["canvas_markers"] == []
    assert_zero_marker_writes(r)


def test_ac032_map_start_transform_failure_preserves_previous_marker_and_start(run):
    r = run(operation="map_start_marker", project_crs="EPSG:4326", seed_center=[127.1, 37.1],
            actions=[{"action": "capture_center", "center": [200000, 600000],
                      "transform_fault": "untransformable"}])
    assert r["states"][-1]["start_wgs84"] == r["states"][0]["start_wgs84"]
    assert r["states"][-1]["canvas_markers"] == r["states"][0]["canvas_markers"]
    assert r["states"][-1]["canvas_marker_count"] == len(r["states"][-1]["canvas_markers"]) == 1
    assert r["states"][-1]["message"].strip()
    assert_zero_marker_writes(r)


def assert_project_relative_file(result, relative):
    path = Path(relative)
    root = Path(result["project_dir"]).resolve()
    resolved = (root / path).resolve()
    assert not path.is_absolute() and resolved.is_relative_to(root) and resolved.is_file()
    return resolved


def route_calculation_payload(route):
    """Compare calculation output independently of persistence-owned identity/name fields."""
    return {key: deepcopy(value) for key, value in route.items()
            if key not in {"route_id", "name", "created_at", "revision"}}


@pytest.mark.parametrize("action", ["save_default_start", "save_route"])
def test_ac023_storage_feedback_names_exact_committed_relative_path(run, action):
    r = run(operation="storage_feedback", action=action, key=KEY,
            coordinate=[127.123, 37.456], route_name="오전 경로")
    feedback = r["feedback"]
    assert feedback["success"] is True
    assert feedback["project_relative_path"] == r["committed_project_relative_path"]
    assert feedback["filename"] == Path(feedback["project_relative_path"]).name
    assert feedback["project_relative_path"] in feedback["text"]
    assert feedback["filename"] in feedback["text"]
    assert_project_relative_file(r, feedback["project_relative_path"])
    if action == "save_default_start":
        assert all(value in feedback["text"] for value in ("127.123", "37.456"))
    else:
        assert "오전 경로" in feedback["text"]
    exposed = str(feedback) + str(r["logs"]) + str(r["errors"])
    assert "Authorization" not in str(feedback)
    assert KEY not in exposed and quote(KEY, safe="") not in exposed


@pytest.mark.parametrize("action", ["save_default_start", "save_route"])
def test_ac023_storage_failure_has_no_success_or_secret_feedback(run, action):
    r = run(operation="storage_feedback", action=action, key=KEY, fault="commit_failure",
            coordinate=[127.123, 37.456], route_name="실패 경로")
    assert r["feedback"]["success"] is False
    assert r["success_feedback_count"] == 0 and r["committed_project_relative_path"] is None
    assert r["saved_after"] == r["saved_before"]
    exposed = str(r["feedback"]) + str(r["logs"]) + str(r["errors"])
    assert "Authorization" not in str(r["feedback"])
    assert KEY not in exposed and quote(KEY, safe="") not in exposed


def canonical_naver_query(name, caller_id="ch.opengis.qfield"):
    return ("navigation?dlat=37.456&dlng=127.123&dname="
            f"{quote(name, safe='')}&appname={quote(caller_id, safe='')}")


def canonical_naver_android_intent(name, caller_id="ch.opengis.qfield"):
    query = canonical_naver_query(name, caller_id)
    return (f"intent://{query}#Intent;scheme=nmap;action=android.intent.action.VIEW;"
            "category=android.intent.category.BROWSABLE;package=com.nhn.android.nmap;end")


@pytest.mark.parametrize("caller_id", [None, "org.example.fieldbuild"])
def test_ac025_exact_encoded_android_intent_and_honest_qt_true(run, caller_id):
    name = "조사지 A & B/#?"
    effective = caller_id or "ch.opengis.qfield"
    r = run(operation="reopen_navigate", road_geometry=ROAD, destination=[127.123, 37.456], name=name,
            platform="android", caller_id=caller_id, launch_results=[True])
    assert r["launcher_calls"] == [{"url": canonical_naver_android_intent(name, effective),
                                     "via": "Qt.openUrlExternally", "result": True}]
    assert r["os_request_accepted"] is True and r["fallback_count"] == 0
    assert r["claims"] == {"app_started": False, "destination_accepted": False, "navigation_started": False}
    no_calls(r)


def test_ac025_android_fallback_and_all_refused(run):
    expected_primary = canonical_naver_android_intent("목적지")
    r = run(operation="reopen_navigate", road_geometry=ROAD, destination=[127.123, 37.456], name="목적지",
            platform="android", caller_id=None, launch_results=[False, False])
    assert [call["url"] for call in r["launcher_calls"]] == [expected_primary, NAVER_ANDROID_STORE]
    assert len(r["launcher_calls"]) == 2 and r["fallback_count"] == 1
    assert r["fallback"]["platform"] == "android"
    assert r["fallback"]["identifier"] == NAVER_ANDROID_PACKAGE
    assert NAVER_ANDROID_PACKAGE in r["launcher_calls"][1]["url"]
    assert r["message"].strip() and r["claims"]["navigation_started"] is False
    no_calls(r)


def test_ac025_non_mobile_has_actionable_error_without_install_dispatch(run):
    r = run(operation="reopen_navigate", road_geometry=ROAD, destination=[127.123, 37.456], name="목적지",
            platform="desktop", caller_id=None, launch_results=[])
    assert r["launcher_calls"] == [] and r["fallback_count"] == 0
    assert r["message"].strip()
    no_calls(r)


@pytest.mark.parametrize("roundtrip,expected_count", [(False, 3), (True, 4)])
def test_ac026_ac035_schema3_complete_immutable_legs_roundtrip(run, roundtrip, expected_count):
    r = run(operation="schema2_roundtrip", return_to_start=roundtrip, layer_id=SITE_LAYER_ID,
            directions_response=schema2_directions_response(roundtrip=roundtrip),
            post_save_actions=["complete", "uncheck", "toggle", "load"])
    document, route = r["reloaded_document"], r["reloaded_route"]
    assert document["schema"] == 3 and document == r["saved_document"]
    assert route["route_schema"] == 3
    assert len(route["legs"]) == expected_count
    assert [leg["sequence"] for leg in route["legs"]] == list(range(1, expected_count + 1))
    assert route["legs"][0]["from"] == "start"
    for index in range(3):
        assert route["legs"][index]["to"] == {"layer_id": SITE_LAYER_ID, "site_id": str(index)}
    for index, leg in enumerate(route["legs"]):
        assert leg["distance_m"] >= 0 and leg["duration_s"] >= 0
        assert leg["geometry"]["type"] == "LineString"
        assert all(-180 <= xy[0] <= 180 and -90 <= xy[1] <= 90 for xy in leg["geometry"]["coordinates"])
        start, end = SCHEMA2_WAY_POINTS[index:index + 2]
        assert leg["geometry"]["coordinates"] == SCHEMA2_COORDINATES[start:end + 1]
    if roundtrip:
        assert route["legs"][-1]["to"] == "start"
    assert route["road_geometry"]["coordinates"] == SCHEMA2_COORDINATES[:SCHEMA2_WAY_POINTS[expected_count] + 1]
    assert route["distance_m"] == sum(leg["distance_m"] for leg in route["legs"])
    assert route["duration_s"] == sum(leg["duration_s"] for leg in route["legs"])
    assert r["immutable_snapshots"] and all(snapshot == r["immutable_snapshots"][0]
                                              for snapshot in r["immutable_snapshots"])
    assert "remaining_recalculate" not in r["controls"]
    assert r["post_save_requests"] == []


@pytest.mark.parametrize("fault,reference", [
    ("missing_order", "0"),
    ("duplicate_order", "2"),
    ("unknown_order", "99"),
    ("unassigned_order", "0"),
    ("missing_way_points", "way_points"),
    ("duplicate_waypoint_index", "2"),
    ("invalid_waypoint_index", str(len(SCHEMA2_COORDINATES) + 10)),
    ("missing_segment", "4"),
    ("invalid_geometry", "geometry"),
    ("invalid_metric", "2"),
    ("total_tolerance", "distance"),
])
def test_ac035_provider_contract_defects_are_actionable_and_preserve_last_good(run, fault, reference):
    optimizer_response, directions_response = malformed_provider_payload(fault)
    r = run(operation="schema2_roundtrip", return_to_start=True, layer_id=SITE_LAYER_ID,
            optimizer_response=optimizer_response, directions_response=directions_response,
            seed_saved=True, key=KEY)
    rejected(r)
    assert r["candidate"] is None and r["active_after"] == r["active_before"]
    assert r["error_category"] == "provider_response"
    assert r["error_reference"] == reference and reference in r["message"]
    assert r["provider_contract_valid"] is False
    assert_secret_free_failure(r)


def test_ac035_valid_provider_response_forced_client_failure_is_distinct_and_preserves_last_good(run):
    r = run(operation="schema2_roundtrip", return_to_start=True, layer_id=SITE_LAYER_ID,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True), seed_saved=True, key=KEY,
            client_processing_fault="after_provider_validation:leg_mapping")
    rejected(r)
    assert r["candidate"] is None and r["active_after"] == r["active_before"]
    assert r["provider_contract_valid"] is True
    assert r["error_category"] == "client_processing"
    assert r["error_stage"] == "leg_mapping"
    assert "처리" in r["message"] and r["retry_guidance_visible"] is True
    assert_secret_free_failure(r)


@pytest.mark.parametrize("kind", GEOMETRIES)
def test_ac035_six_geometry_families_accept_real_ors_contract_from_approved_representative(run, kind):
    import fiona

    expected = expected_wgs84(kind, "EPSG:4326")
    supplied_wkt = fixture_wkt(GEOJSON[kind])
    directions_response = one_stop_directions_response(expected)
    r = run(operation="generated_geometry_calculate", geometry_type=kind,
            wkt=supplied_wkt, crs="EPSG:4326",
            evaluator_contract=QFIELD_EXPRESSION_EVALUATOR,
            target_id="geometry-site", return_to_start=False, save_and_reopen=True,
            optimizer_response=one_stop_vroom_response(expected),
            directions_response=directions_response)
    assert r["ok"] is True and r["generic_crs_error_shown"] is False
    assert r["request_coordinate"] == pytest.approx(expected, abs=1e-7)
    assert r["submitted_ids"] == r["optimizer_order_ids"] == ["geometry-site"]
    assert r["original_after"] == r["original_before"]
    assert r["provider_contract_valid"] is True
    provenance = r["generated_geometry_provenance"]
    source_path = Path(provenance["materialized_source_path"]).resolve()
    gpkg_path = Path(provenance["generated_gpkg_path"]).resolve()
    qgs_path = Path(provenance["generated_project_path"]).resolve()
    assert source_path.is_file() and gpkg_path.is_file() and qgs_path.is_file()
    assert len({source_path, gpkg_path, qgs_path}) == 3
    with fiona.open(source_path) as source:
        source_rows = list(source)
        assert source.crs.to_epsg() == 4326 and len(source_rows) == 1
        assert geometry_signature(source_rows[0]["geometry"]) == geometry_signature(GEOJSON[kind])
    with fiona.open(gpkg_path, layer=provenance["generated_layer_name"]) as generated:
        generated_rows = list(generated)
        assert generated.crs.to_epsg() == 4326 and len(generated_rows) == 1
        assert geometry_signature(generated_rows[0]["geometry"]) == geometry_signature(GEOJSON[kind])
        assert str(generated_rows[0]["properties"]["site_id"]) == "geometry-site"
    project_sources = [node.text or "" for node in ET.parse(qgs_path).findall(".//datasource")]
    assert any(gpkg_path.name in value and provenance["generated_layer_name"] in value
               for value in project_sources)
    assert provenance["supplied_wkt_sha256"] == hashlib.sha256(supplied_wkt.encode()).hexdigest()
    assert provenance["supplied_crs"] == "EPSG:4326"
    assert provenance["calculation_feature_origin"] == "generated_project_layer"
    assert provenance["fixture_feature_injected"] is False
    route = r["reloaded_route"]
    assert len(route["legs"]) == 1
    assert route["legs"][0]["geometry"] == directions_response["features"][0]["geometry"]
    assert r["qml_errors"] == []


@pytest.mark.parametrize("fault", ["missing_leg", "out_of_order_leg", "negative_leg", "nonfinite_leg",
                                    "invalid_leg_geometry", "non_wgs84_leg", "mismatched_leg_count"])
def test_ac026_invalid_schema2_leg_preserves_existing_route(run, fault):
    directions_response, fault_path = malformed_schema2_directions(fault)
    r = run(operation="schema2_roundtrip", return_to_start=True, layer_id=SITE_LAYER_ID,
            directions_response=directions_response, seed_saved=True)
    rejected(r)
    assert r["candidate"] is None and r["active_after"] == r["active_before"]
    assert r["fault_provenance"] == {
        "source": "captured_directions_transport_response",
        "input_path": fault_path,
        "payload_sha256": payload_sha256(directions_response),
        "segment_way_points_present": False,
    }


@pytest.mark.parametrize("fault,reason,index", [
    ("invalid_leg_geometry", "type", None),
    ("non_wgs84_leg", "범위", 3),
])
def test_ac026_invalid_linestring_reports_safe_structural_reason(run, fault, reason, index):
    directions_response, _ = malformed_schema2_directions(fault)
    r = run(operation="schema2_roundtrip", return_to_start=True,
            layer_id=SITE_LAYER_ID, directions_response=directions_response,
            seed_saved=True)
    rejected(r)
    assert reason in r["message"]
    if index is not None:
        assert f"coordinates[{index}]" in r["message"]
    assert "181" not in r["message"]


@pytest.mark.parametrize("distance_adjustment,duration_adjustment,accepted", [
    (5, 0, True), (5.01, 0, False), (0, 2.28, True), (0, 2.29, False),
])
def test_ac026_provider_total_tolerance(run, distance_adjustment, duration_adjustment, accepted):
    r = run(operation="schema2_roundtrip", return_to_start=True, layer_id=SITE_LAYER_ID, seed_saved=True,
            directions_response=schema2_directions_response(roundtrip=True,
                distance_adjustment=distance_adjustment, duration_adjustment=duration_adjustment))
    if accepted:
        assert r["ok"] is True
        assert r["reloaded_route"]["distance_m"] == 1000
        assert r["reloaded_route"]["duration_s"] == 456
    else:
        rejected(r)


@pytest.mark.parametrize("completion_source", ["field", "route_stop"])
def test_ac027_ordered_completion_then_uncheck_creates_out_of_order_gap_and_roundtrip_return(run, completion_source):
    raw_directions = schema2_directions_response(roundtrip=True)
    r = run(operation="route_progression", mode="roundtrip", completion_source=completion_source,
            actions=[{"complete": "2"}, {"complete": "0"}, {"complete": "1"},
                     {"complete": "2"}, {"uncheck": "0"}],
            relocate=False, directions_response=raw_directions)
    provenance = r["route_seed_provenance"]
    assert provenance["source"] == "captured_directions_transport_response"
    assert provenance["payload_sha256"] == payload_sha256(raw_directions)
    assert provenance["committed_route_id"] == r["full_route_before"]["route_id"]
    assert provenance["committed_revision"] == r["full_route_before"]["revision"]
    assert_project_relative_file(r, provenance["storage_project_relative_path"])
    assert r["full_route_before"]["road_geometry"]["coordinates"] == SCHEMA2_COORDINATES
    assert [leg["geometry"]["coordinates"] for leg in r["full_route_before"]["legs"]] == [
        SCHEMA2_COORDINATES[start:end + 1]
        for start, end in zip(SCHEMA2_WAY_POINTS, SCHEMA2_WAY_POINTS[1:])
    ]
    initial, blocked_later, first, second, all_targets, out_of_order = r["states"]
    assert (initial["prefix_length"], initial["remaining_leg_sequences"]) == (0, [1, 2, 3, 4])
    assert (initial["remaining_distance_m"], initial["remaining_duration_s"]) == (1000, 456)
    assert initial["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES
    assert blocked_later == initial
    assert (first["prefix_length"], first["remaining_leg_sequences"]) == (1, [2, 3, 4])
    assert (first["remaining_distance_m"], first["remaining_duration_s"]) == (900, 436)
    assert first["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES[SCHEMA2_WAY_POINTS[1]:]
    assert (second["prefix_length"], second["remaining_leg_sequences"]) == (2, [3, 4])
    assert (second["remaining_distance_m"], second["remaining_duration_s"]) == (700, 336)
    assert second["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES[SCHEMA2_WAY_POINTS[2]:]
    assert (all_targets["prefix_length"], all_targets["remaining_leg_sequences"]) == (3, [4])
    assert (all_targets["remaining_distance_m"], all_targets["remaining_duration_s"]) == (400, 216)
    assert all_targets["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES[SCHEMA2_WAY_POINTS[3]:]
    assert all_targets["remaining_note"] == "복귀 포함"
    assert (out_of_order["prefix_length"], out_of_order["remaining_leg_sequences"]) == (0, [1, 2, 3, 4])
    assert out_of_order["remaining_geometry"] == initial["remaining_geometry"]
    assert out_of_order["completed_ids"] == ["1", "2"] and out_of_order["next_id"] == "0"
    assert r["full_route_after"] == r["full_route_before"]
    no_calls(r)


@pytest.mark.parametrize("geometry_type", ["Point", "LineString", "Polygon"])
@pytest.mark.parametrize("completion_source", ["field", "route_stop"])
def test_ac027_completion_overlay_is_blue_accessible_nonpersistent_and_rederived(run, geometry_type, completion_source):
    r = run(operation="completion_overlay", geometry_type=geometry_type, completion_source=completion_source,
            color="#1565C0", actions=["complete", "uncheck", "complete", "restart", "load"])
    completed = r["states"][1]
    assert completed["check"] is True and completed["state_text"] == "완료"
    assert completed["overlay"]["color"] == "#1565C0" and completed["overlay"]["persistent"] is False
    if geometry_type == "Polygon":
        assert completed["overlay"]["fill_opacity"] == pytest.approx(.35)
        assert completed["overlay"]["outline_opacity"] == 1
    else:
        assert completed["overlay"]["opacity"] == 1
    assert r["states"][2]["overlay"] is None
    assert r["states"][-1]["overlay"] == r["states"][-2]["overlay"]
    assert r["source_renderer_after"] == r["source_renderer_before"]
    assert r["source_data_after"] == r["source_data_before"]
    no_calls(r)


def test_ac027_mapped_write_failure_preserves_overlay_metrics_and_source(run):
    r = run(operation="completion_write_failure", fault="read_only", completed_id="0", seed_saved=True)
    rejected(r)
    for field in ("source_completion", "active", "next", "overlay", "metrics", "check"):
        assert r[f"{field}_after"] == r[f"{field}_before"]
    no_calls(r)


@pytest.mark.parametrize("seconds,expected", [(0, {"0시간 00분", "00분"}), (1, {"01분", "0시간 01분"}),
                                                (3599, {"1시간 00분"}), (3601, {"1시간 01분"})])
def test_ac028_metric_formatting_and_bottom_bar(run, seconds, expected):
    r = run(operation="metric_display", route_name="오전 경로", completed=2, total=3,
            remaining_distance_m=1234, remaining_duration_s=seconds)
    assert r["distance_text"] == "1.23 km" and r["duration_text"] in expected
    assert r["bottom_bar"] == f"오전 경로 · 2/3 · 남은 1.23 km · {r['duration_text']}"
    assert r["no_route_bottom_bar"] == "조사 경로 · 0/0 · 남은 0.00 km · 0시간 00분"


def test_ac028_route_line_toggle_scope_persistence_move_and_zero_api(run):
    r = run(operation="route_line_toggle", offline=True, move_folder=True,
            transitions=["off", "route_switch", "panel_reopen", "app_restart", "folder_move"])
    assert r["initial_show_route_line"] is True
    assert all(state["show_route_line"] is False for state in r["states"])
    assert r["other_project_initial_show_route_line"] is True
    assert r["saved_geometry_after"] == r["saved_geometry_before"]
    assert r["completed_overlay_after"] == r["completed_overlay_before"]
    assert r["source_renderer_after"] == r["source_renderer_before"]
    assert_project_relative_file(r, r["preference_project_relative_path"])
    assert Path(r["old_dir"]).resolve() != Path(r["project_dir"]).resolve() and not Path(r["old_dir"]).exists()
    no_calls(r)


def test_ac027_ac028_progression_survives_restart_recovery_offline_move(run):
    r = run(operation="route_progression", mode="roundtrip", completion_source="field",
            actions=[{"complete": "0"}, {"complete": "2"}], relocate=True,
            restart=True, recover_latest=True, offline=True)
    assert r["reloaded_state"] == r["states"][-1]
    assert r["recovered_state"] == r["states"][-1]
    assert r["moved_state"] == r["states"][-1]
    assert r["full_route_after"] == r["full_route_before"]
    no_calls(r)


def test_ac029_legacy_schema1_load_is_offline_nonmutating_and_unavailable(run):
    legacy = schema2_legacy_document()
    r = run(operation="legacy_route", document=legacy, action="load", offline=True)
    assert r["loaded_document"] == legacy
    assert r["storage_bytes_after"] == r["storage_bytes_before"]
    assert r["displayed_full_geometry"] == legacy["routes"][0]["road_geometry"]
    assert r["displayed_totals"] == {"distance_m": 600, "duration_s": 240}
    assert r["displayed_stops"] == legacy["routes"][0]["stops"]
    assert r["remaining"] == {"distance": "사용 불가", "time": "사용 불가", "geometry": "사용 불가"}
    assert r["message_requires_new_full_calculation_and_save"] is True
    assert r["inferred_legs"] == [] and r["writes"] == []
    no_calls(r)


def test_ac029_explicit_full_recalculation_upgrades_to_schema3(run):
    legacy = schema2_legacy_document()
    r = run(operation="legacy_route", document=legacy, action="explicit_calculate_and_save", offline=False,
            directions_response=schema2_directions_response(roundtrip=False))
    assert r["saved_document"]["schema"] == 3
    assert r["saved_route"]["route_schema"] == 3
    assert r["saved_route"]["route_id"] == "legacy-route-1"
    assert r["saved_route"]["revision"] > 7 and len(r["saved_route"]["legs"]) == 3
    assert r["requests"], "the only permitted migration request is the explicit full calculation"


def test_ac029_future_schema_is_preserved_and_rejected(run):
    future = schema2_legacy_document(schema=4)
    r = run(operation="legacy_route", document=future, action="load", offline=True)
    assert r["ok"] is False and r["message"].strip()
    assert r["storage_bytes_after"] == r["storage_bytes_before"]
    assert r["writes"] == []
    no_calls(r)


def test_ac036_name_entry_and_changes_save_existing_candidate_without_recalculation(run):
    r = run(operation="candidate_name_save", seed_saved=True,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True),
            actions=[{"focus_name": True}, {"set_name": "초안"},
                     {"set_name": FOLLOWUP_ROUTE_NAME}, {"save": True}])
    assert r["calculation_requests"], "setup must create the candidate through production calculation"
    candidate = r["candidate_after_calculation"]
    assert candidate and r["base_revision_after_calculation"] == r["saved_before"]["revision"]
    for state in r["name_action_states"]:
        assert state["candidate"] == candidate
        assert state["base_revision"] == r["base_revision_after_calculation"]
        assert state["calculation_inputs"] == r["calculation_inputs_after_calculation"]
        assert state["requests"] == []
    assert r["saved_route"]["name"] == FOLLOWUP_ROUTE_NAME.strip()
    assert r["reloaded_route"] == r["saved_route"]
    assert route_calculation_payload(r["saved_route"]) == route_calculation_payload(candidate)
    assert_project_relative_file(r, r["committed_project_relative_path"])


@pytest.mark.parametrize("first_attempt", ["blank_name", "io_failure", "recoverable_validation"])
def test_ac036_recoverable_save_failure_preserves_candidate_for_corrected_retry(run, first_attempt):
    r = run(operation="candidate_name_save", seed_saved=True,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True),
            actions=[{"set_name": "   " if first_attempt == "blank_name" else "재시도 경로"},
                     {"save": True, "fault": first_attempt},
                     {"set_name": "복구된 경로"}, {"save": True}])
    failed, corrected, saved = r["attempt_states"]
    assert failed["ok"] is False and failed["message"].strip()
    assert failed["candidate"] == r["candidate_after_calculation"]
    assert failed["saved_routes"] == r["saved_routes_before"]
    assert corrected["candidate"] == failed["candidate"]
    assert saved["ok"] is True and saved["saved_route"]["name"] == "복구된 경로"
    assert route_calculation_payload(saved["saved_route"]) == route_calculation_payload(failed["candidate"])
    assert all(state["requests"] == [] for state in r["attempt_states"])


def test_ac036_calculation_input_change_blocks_stale_candidate(run):
    stale_change = "calculation_input"
    r = run(operation="candidate_name_save", seed_saved=True,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True),
            actions=[{"set_name": "저장 시도"}, {"make_stale": stale_change}, {"save": True}])
    assert r["save_ok"] is False and stale_change in r["stale_reason"]
    assert r["message"].strip() and r["candidate_after"] == r["candidate_before"]
    assert r["saved_routes_after"] == r["saved_routes_before"]
    assert r["requests_after_calculation"] == []


def test_ac036_settings_revision_refreshes_candidate_base_without_stale(run):
    r = run(operation="candidate_name_save", seed_saved=True,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True),
            actions=[{"make_stale": "snapshot_revision"}])
    state = r["name_action_states"][-1]
    assert state["candidate"] == r["candidate_after_calculation"]
    assert state["base_revision"] > r["base_revision_after_calculation"]
    assert r["saved_routes_after"] == r["saved_routes_before"]
    assert r["requests_after_calculation"] == []


@pytest.mark.parametrize("viewport_width", [320, 1024])
@pytest.mark.parametrize("control_state", ["empty", "value", "focus", "error", "disabled"])
def test_ac037_seven_controls_share_rendered_outlined_floating_label_contract(run, viewport_width, control_state):
    r = run(operation="followup_panel_ui", viewport_width=viewport_width,
            control_state=control_state, labels=FOLLOWUP_FLOATING_LABELS)
    assert r["qml_runtime"]["loaded_generated_qml"] is True
    assert Path(r["qml_runtime"]["generated_qml_path"]).is_file()
    assert r["horizontal_overflow"] is False and Path(r["screenshot_path"]).is_file()
    controls = r["floating_controls"]
    assert set(controls) == set(FOLLOWUP_FLOATING_LABELS)
    reference = None
    for semantic_id, exact_label in FOLLOWUP_FLOATING_LABELS.items():
        control = controls[semantic_id]
        assert control["evidence_source"] == "loaded_generated_qml_object_tree"
        assert control["label"] == exact_label and control["accessible_name"] == exact_label
        assert control["placeholder_is_accessible_name"] is False
        assert control["control_kind"] in {"text", "dropdown"}
        assert control["label_visible"] is True and control["separate_label_row"] is False
        assert control["state"] == control_state
        assert not rects_overlap(control["label_rect"], control["value_rect"])
        if control["indicator_rect"] is not None:
            assert not rects_overlap(control["label_rect"], control["indicator_rect"])
        if control["error_rect"] is not None:
            assert not rects_overlap(control["control_rect"], control["error_rect"])
        signature = (control["label_rect"]["top"] - control["control_rect"]["top"],
                     control["label_rect"]["left"] - control["control_rect"]["left"],
                     control["label_rect"]["height"], control["font_pixel_size"],
                     control["outline_width"], control["top_padding"], control["notch_padding"])
        reference = signature if reference is None else reference
        assert signature == reference
        assert control["accessibility"]["role"] in {"ComboBox", "EditableText"}
        assert control["accessibility"]["enabled"] is (control_state != "disabled")
    assert r["stored_values_after"] == r["stored_values_before"]


def test_ac038_api_settings_initially_collapsed_and_toggle_is_passive(run):
    r = run(operation="settings_disclosure", viewport_width=320,
            actions=["open_panel", "expand", "collapse", "expand"], manual_session_key=KEY)
    initial, expanded, collapsed, reexpanded = r["states"]
    assert initial["title"] == "API URL/키 설정" and initial["expanded"] is False
    assert initial["key_value_visible"] is False
    assert expanded["expanded"] is True and collapsed["expanded"] is False and reexpanded["expanded"] is True
    assert expanded["values"] == reexpanded["values"]
    assert expanded["labels"]["optimizer_url"] == "VROOM 서버 URL"
    assert expanded["key_masked"] is True and KEY not in str(r["states"])
    assert expanded["accessible_state"] == "expanded" and collapsed["accessible_state"] == "collapsed"
    assert r["requests"] == [] and r["writes"] == [] and r["horizontal_overflow"] is False


@pytest.mark.parametrize("key_source,source_text", [
    ("manual", "이번 세션만 사용"),
    ("consented_project_variable", "프로젝트 파일의 평문 키 사용 중"),
])
def test_ac038_key_provenance_and_session_lifetime_are_observed_from_generated_project(run, key_source, source_text):
    r = run(operation="settings_key_provenance", key_source=key_source, key=KEY,
            builder_consent=key_source == "consented_project_variable")
    assert Path(r["generated_project_path"]).is_file()
    assert r["source_message"] == source_text and r["key_masked"] is True
    assert KEY not in str(r["rendered_panel"]) and KEY not in str(r["diagnostics"])
    if key_source == "manual":
        assert r["key_after_session_restart"] is None
        assert KEY.encode() not in Path(r["generated_project_path"]).read_bytes()
    else:
        assert r["project_variable_plaintext_warning_visible"] is True
        assert r["project_variable_read_from_qgs"] == KEY
        assert r["key_after_session_restart"] == KEY


def test_ac038_settings_save_reports_actual_slot_and_excludes_key_and_objective(run):
    r = run(operation="settings_snapshot_save", key=KEY, objective="distance", save_count=2,
            settings={"server_url": "https://routing.invalid/ors",
                      "optimizer_url": "https://optimizer.invalid/vroom", "timeout_ms": 4321})
    assert len(r["commits"]) == 2
    assert {commit["project_relative_path"] for commit in r["commits"]} == {
        "survey-routes.a.json", "survey-routes.b.json"}
    for commit in r["commits"]:
        assert_project_relative_file(r, commit["project_relative_path"])
        assert commit["project_scope"] == r["project_scope"]
        assert commit["project_relative_path"] in commit["feedback"]
        assert "키 제외" in commit["feedback"] and commit["success"] is True
        assert KEY not in str(commit) and "objective" not in commit["readback_settings"]
    assert r["reloaded_routes"] == r["routes_before_save"]
    assert r["reloaded_settings"] == r["commits"][-1]["readback_settings"]


def test_ac038_failed_settings_save_preserves_last_good_and_session_key(run):
    r = run(operation="settings_snapshot_save", key=KEY, objective="duration", save_count=1,
            seed_last_good=True, fault="commit_failure")
    assert r["success_feedback_count"] == 0 and r["feedback"]["success"] is False
    assert r["snapshot_after"] == r["snapshot_before"]
    assert r["session_key_after"] == KEY and KEY not in str(r["feedback"])
    assert r["requests"] == []


@pytest.mark.parametrize("completion_source", ["field", "route_stop"])
def test_ac040_only_next_in_order_is_checkable_and_blocked_attempt_is_nonmutating(run, completion_source):
    r = run(operation="ordered_completion_checklist", completion_source=completion_source,
            directions_response=schema2_directions_response(roundtrip=False),
            actions=[{"attempt_complete": "1"}, {"complete": "0"},
                     {"attempt_complete": "2"}, {"complete": "1"}, {"complete": "2"}])
    initial = r["states"][0]
    assert [row["completion_enabled"] for row in initial["rows"]] == [True, False, False]
    assert all(row["disabled_reason"] == "다음 방문 지점부터 순서대로 완료하세요."
               for row in initial["rows"][1:])
    for blocked in r["blocked_attempts"]:
        assert blocked["feedback_next_id"] == blocked["expected_next_id"]
        assert blocked["after"] == blocked["before"]
        assert blocked["requests"] == [] and blocked["writes"] == []
    assert [state["next_id"] for state in r["successful_states"]] == ["1", "2", None]
    assert [state["enabled_incomplete_ids"] for state in r["successful_states"]] == [["1"], ["2"], []]
    assert all(state["requests"] == [] for state in r["states"])


@pytest.mark.parametrize("completion_source", ["field", "route_stop"])
def test_ac040_uncheck_gap_and_external_out_of_order_true_keep_full_remaining_contract(run, completion_source):
    r = run(operation="ordered_completion_checklist", completion_source=completion_source,
            directions_response=schema2_directions_response(roundtrip=False),
            initial_completed_ids=["0", "1", "2"],
            actions=[{"uncheck": "0"}, {"external_completed_ids": ["1"]}, {"complete": "0"}])
    unchecked, external_gap, closed = r["states"][1:]
    for state in (unchecked, external_gap):
        assert state["prefix_length"] == 0 and state["next_id"] == "0"
        assert state["remaining_leg_sequences"] == [1, 2, 3]
        assert state["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES[:SCHEMA2_WAY_POINTS[3] + 1]
        out_of_order = [row for row in state["rows"] if row["site_id"] in state["completed_ids"]]
        assert out_of_order and all(row["state_text"] == "순서 밖 완료" and row["checked"] for row in out_of_order)
        assert all(row["non_color_state_indicator"] for row in out_of_order)
    assert closed["prefix_length"] == 2 and closed["next_id"] == "2"
    assert closed["remaining_leg_sequences"] == [3]
    assert closed["remaining_geometry"]["coordinates"] == SCHEMA2_COORDINATES[
        SCHEMA2_WAY_POINTS[2]:SCHEMA2_WAY_POINTS[3] + 1]
    assert all(state["requests"] == [] for state in r["states"])


@pytest.mark.parametrize("geometry_type", ["Point", "LineString", "Polygon"])
def test_ac041_generated_site_labels_use_configured_name_and_white_halo(run, geometry_type):
    names = ["일반 이름", "", None, "<b onclick='run()'>표시만</b>"]
    r = run(operation="generated_site_style", geometry_type=geometry_type,
            name_field="display_name", names=names, basemaps=["light", "dark"])
    provenance = r["generated_artifact_provenance"]
    assert provenance["source"] == "fieldbuild_generation_path"
    assert Path(provenance["generated_project_path"]).is_file()
    assert Path(provenance["generated_gpkg_path"]).is_file()
    assert r["labeling"]["field"] == "display_name" and r["labeling"]["buffer_color"].upper() == "#FFFFFF"
    assert r["labeling"]["buffer_enabled"] is True and r["labeling"]["buffer_width"] > 0
    assert [label["text"] for label in r["rendered_labels"]] == [names[0], names[3]]
    assert all(label["inert_text"] is True and label["executed_actions"] == [] for label in r["rendered_labels"])
    assert r["blank_label_artifacts"] == []
    assert r["source_features_after"] == r["source_features_before"]
    assert r["source_renderer_contract_after"] == r["source_renderer_contract_before"]
    assert set(r["basemap_renderings"]) == {"light", "dark"}


def test_ac041_generated_polygon_uses_non_gray_accent_distinct_from_route_states(run):
    r = run(operation="generated_site_style", geometry_type="Polygon", name_field="display_name",
            names=["면 조사지"], basemaps=["light", "dark"], include_route_states=True)
    style = r["base_style"]
    assert style["outline_color"].upper() == "#2E7D32"
    assert style["fill_color"].upper() == "#2E7D32" and 0 < style["fill_opacity"] < 1
    assert style["outline_color"].upper() not in {"#808080", "#888888", "#A0A0A0"}
    for rendering in r["basemap_renderings"].values():
        assert rendering["outline_visible"] is True and rendering["fill_visible"] is True
        assert rendering["label_halo_visible"] is True
    assert len({r["base_style"]["outline_color"], r["completion_overlay_style"]["color"],
                r["route_line_style"]["color"], r["start_marker_style"]["color"]}) == 4
    assert r["source_features_after"] == r["source_features_before"]


@pytest.mark.parametrize("touch_target", ["field_body", "label_notch_overlap"])
def test_ac042_touch_equivalent_text_input_uses_real_editable_qml_control_without_recalculation(
        run, touch_target):
    r = run(operation="route_name_text_input_proxy", seed_saved=True,
            optimizer_response=vroom_response(include_arrivals=True),
            directions_response=schema2_directions_response(roundtrip=True),
            input_events=[
                {"touch_body": True, "touch_target": touch_target}, {"text": "오후 route"},
                {"select": [3, 8]}, {"delete_selection": True}, {"text": " 조사 경로  "},
            ], save=True)
    assert r["qml_runtime"]["loaded_generated_qml"] is True
    control = r["route_name_control"]
    assert control["evidence_source"] == "loaded_generated_qml_object"
    assert control["object_id"] and control["qml_type"] in {"TextField", "TextInput"}
    assert control["enabled"] is True and control["editable"] is True and control["read_only"] is False
    assert control["accepts_input_method"] is True and control["input_method_enabled"] is True
    touch = r["input_states"][1]
    assert touch["event_source"] == "touch_equivalent_event"
    assert touch["target_region"] == touch_target
    assert touch["target_rect_source"] == "loaded_generated_qml_object_geometry"
    assert touch["delivered_via"] == "window_pointer_event"
    assert touch["focus_checked_before_any_recovery"] is True
    assert touch["focused_object_id"] == control["object_id"]
    assert touch["active_focus"] is True and touch["cursor_visible"] is True
    assert touch["cursor_position"] >= 0
    assert r["focus_recovery_api_invocations"] == []
    assert r["input_states"][2]["event_source"] == "input_method_commit_event"
    assert r["input_states"][2]["active_focus"] is True
    assert all(state["focus_recovery_api_invocations"] == [] for state in r["input_states"])
    assert r["selection_event_observed"] is True and r["deletion_event_observed"] is True
    assert r["final_control_text"] == "오후  조사 경로  "
    assert r["saved_route"]["name"] == "오후  조사 경로"
    for state in r["input_states"]:
        assert state["candidate"] == r["candidate_after_calculation"]
        assert state["base_revision"] == r["base_revision_after_calculation"]
        assert state["requests"] == []
    assert r["claims"].get("os_soft_keyboard_opened") is not True
    assert r["evidence_scope"] == "automatic_input_wiring_proxy_not_device_keyboard"


@pytest.mark.parametrize("viewport_width", [320, 1024])
@pytest.mark.parametrize("control_state", ["empty", "value", "focus", "disabled", "error"])
def test_ac043_eight_real_controls_center_labels_on_actual_top_outline(run, viewport_width, control_state):
    r = run(operation="final_floating_label_geometry", viewport_width=viewport_width,
            control_state=control_state)
    assert r["qml_runtime"]["loaded_generated_qml"] is True
    assert Path(r["screenshot_path"]).is_file()
    assert r["horizontal_overflow"] is False
    controls = r["floating_controls"]
    assert set(controls) == set(FINAL_FLOATING_LABELS) and len(controls) == 8
    assert len({control["object_id"] for control in controls.values()}) == 8
    assert len({control["label_object_id"] for control in controls.values()}) == 8
    reference_style = None
    for semantic_id, exact_label in FINAL_FLOATING_LABELS.items():
        control = controls[semantic_id]
        assert control["evidence_source"] == "loaded_generated_qml_object_geometry"
        assert control["label"] == exact_label and control["accessible_name"] == exact_label
        assert control["placeholder_is_accessible_name"] is False
        assert control["state"] == control_state and control["label_visible"] is True
        assert control["separate_label_row"] is False and control["clipped"] is False
        assert control["shared_component_source"] == r["shared_floating_component_source"]
        assert control["shared_component_type"] == r["shared_floating_component_type"]
        outline = control["top_outline_observation"]
        assert outline["source"] in {"live_background_border_geometry", "rendered_image_edge_detection"}
        assert outline["observation_id"] and outline["object_id"]
        assert outline["source"] != "constant"
        assert outline["border_width"] == control["outline_width"]
        tolerance = max(1.0, control["outline_width"] / 2)
        assert abs(rect_center_y(control["label_rect"]) - outline["y"]) <= tolerance
        assert abs(rect_center_y(control["notch_rect"]) - outline["y"]) <= tolerance
        assert not rects_overlap(control["label_rect"], control["value_rect"])
        if control["indicator_rect"] is not None:
            assert not rects_overlap(control["label_rect"], control["indicator_rect"])
        if control_state == "error":
            assert control["error_rect"] is not None
            assert control["error_observation_source"] == "live_validation_object_geometry"
            assert control["error_object_id"]
            assert not rects_overlap(control["control_rect"], control["error_rect"])
        else:
            assert control["error_rect"] is None
        style = (control["font_pixel_size"], control["font_weight"], control["outline_width"],
                 control["left_inset"], control["notch_padding"], control["top_padding"])
        reference_style = style if reference_style is None else reference_style
        assert style == reference_style
    saved = controls["saved_route"]
    assert saved["control_kind"] == "dropdown" and saved["selected_route_id"] == r["selected_route_id_after"]
    assert r["selected_route_id_after"] == r["selected_route_id_before"]
    assert r["selected_route_observation_before"]["source"] == "live_saved_route_model"
    assert r["selected_route_observation_after"]["source"] == "live_saved_route_model"
    assert (r["selected_route_observation_before"]["observation_id"]
            != r["selected_route_observation_after"]["observation_id"])
    assert r["stored_values_observation_before"]["source"] == "independent_repository_readback"
    assert r["stored_values_observation_after"]["source"] == "independent_repository_readback"
    assert (r["stored_values_observation_before"]["observation_id"]
            != r["stored_values_observation_after"]["observation_id"])
    assert r["stored_values_after"] == r["stored_values_before"]


@pytest.mark.parametrize("geometry_type", list(GEOMETRIES))
@pytest.mark.parametrize("name_field_present", [True, False])
def test_ac044_normal_build_persists_six_family_label_contract_without_artifact_edit(
        run, geometry_type, name_field_present):
    import fiona

    features = [
        {"stable_id": stable_id, "name": name, "xy": [127 + index / 1000, 37],
         "geometry": deepcopy(GEOJSON[geometry_type])}
        for index, (stable_id, name) in enumerate([
            ("ID-01", "  이름  "), ("  ID-02  ", "   "), ("", ""),
            ("ID-04", "<b onclick='run()'>표시만</b>"),
        ])
    ]
    if geometry_type == "LineString":
        features.extend([
            {"stable_id": "ID-LINK-A", "name": "연결선", "xy": [127.01, 37.01],
             "geometry": {"type": "LineString", "coordinates": [[10, 10], [11, 10]]}},
            {"stable_id": "ID-LINK-B", "name": "연결선", "xy": [127.02, 37.01],
             "geometry": {"type": "LineString", "coordinates": [[11, 10], [12, 10]]}},
        ])
    r = run(operation="generated_site_label_contract", geometry_type=geometry_type,
            wkt=fixture_wkt(GEOJSON[geometry_type]), crs="EPSG:4326",
            name_field="display_name" if name_field_present else None,
            stable_id_field="site_id", features=features, build_via="normal_project_build")
    provenance = r["generated_artifact_provenance"]
    assert provenance["source"] == "normal_fieldbuild_generation_path"
    assert provenance["artifact_post_edits"] == [] and provenance["fixture_injected_after_build"] is False
    qgs_path = Path(provenance["generated_project_path"])
    gpkg_path = Path(provenance["generated_gpkg_path"])
    assert qgs_path.is_file() and gpkg_path.is_file()
    assert hashlib.sha256(qgs_path.read_bytes()).hexdigest() == provenance["final_qgs_sha256"]
    assert hashlib.sha256(gpkg_path.read_bytes()).hexdigest() == provenance["final_gpkg_sha256"]
    with fiona.open(gpkg_path, layer=provenance["generated_layer_name"]) as layer:
        rows = list(layer)
        assert len(rows) == len(features)
        assert layer.schema["geometry"] == geometry_type
        assert [str(row["properties"].get("site_id") or "") for row in rows] == [
            feature["stable_id"] for feature in features]
        assert ("display_name" in layer.schema["properties"]) is name_field_present
    config = read_qgs_labeling(qgs_path, provenance["generated_layer_id"])
    assert config["enabled"] == "1" and config["type"] == "simple"
    assert config["text_style"].get("isExpression") == "1"
    expression = config["text_style"].get("fieldName", "")
    assert expression == expected_site_label_expression(name_field_present=name_field_present)
    assert config["buffer"].get("bufferDraw") == "1"
    assert config["buffer"].get("bufferColor", "").replace(" ", "") in {
        "255,255,255,255", "255,255,255", "#ffffff", "#ffffffff"}
    expected_placement = {"Point": {"0", "1", "6"}, "MultiPoint": {"0", "1", "6"},
                          "LineString": {"2", "3"}, "MultiLineString": {"2", "3"},
                          "Polygon": {"4", "5", "7", "8"},
                          "MultiPolygon": {"4", "5", "7", "8"}}[geometry_type]
    assert config["placement"].get("placement") in expected_placement
    assert false_xml_flag(config["rendering"].get("labelPerPart"))
    assert false_xml_flag(config["rendering"].get("mergeLines"))
    expected_labels = (["이름", "ID-02", "<b onclick='run()'>표시만</b>"]
                       if name_field_present else ["ID-01", "ID-02", "ID-04"])
    assert not ({"evaluated_texts", "blank_feature_label_count", "arbitrary_field_fallbacks",
                 "markup_executed_actions"} & set(r.get("expression_proxy", {})))
    runtime = r["qgis_runtime"]
    assert runtime["probe_attempted"] is True
    if runtime["available"]:
        assert runtime["api_source"] == "QgsProject/QgsPalLayerSettings/QgsExpression"
        assert runtime["project_loaded"] is True
        assert runtime["labeling_enabled"] is True
        assert runtime["expression"] == expression
        assert runtime["placement"] == config["placement"].get("placement")
        assert runtime["buffer_enabled"] is True
        assert runtime["buffer_color"].upper() == "#FFFFFF"
        assert runtime["label_per_part"] is False and runtime["merge_lines"] is False
        assert runtime["expression_evaluator"] == "QgsExpression"
        assert runtime["expression_errors"] == []
        assert runtime["evaluated_texts"] == expected_labels + (
            ["연결선", "연결선"] if geometry_type == "LineString" and name_field_present else
            ["ID-LINK-A", "ID-LINK-B"] if geometry_type == "LineString" else [])
    else:
        assert runtime["diagnostic"].strip()
        assert runtime["runtime_claims"] == []
    assert r["claims"].get("qfield_device_label_rendered") is not True
    assert r["evidence_scope"] == "generated_qgs_gpkg_proxy_not_qfield_canvas"


def test_ac045_step7_copy_order_masking_and_accessibility(run):
    r = run(operation="builder_step7_route_credentials", state="key_without_consent",
            input_key=KEY, consent=False, remember=False, outcome="success")
    expected_order = ["route_key", "route_key_purpose", "route_key_blank_behavior",
                      "route_key_plaintext_warning", "route_key_consent", "route_key_remember"]
    widgets = r["widgets"]
    assert r["widget_tree_observation"] == {"source": "actual_qt_widget_tree",
                                            "semantic_ids": expected_order}
    assert [widget["semantic_id"] for widget in widgets] == expected_order
    assert r["focus_chain_observation"]["source"] == "QWidget.nextInFocusChain"
    assert r["focus_chain_observation"]["semantic_ids"] == [
        "route_key", "route_key_consent", "route_key_remember"]
    observed = {widget["semantic_id"]: widget for widget in widgets}
    assert observed["route_key"]["echo_mode"] == "password"
    assert observed["route_key_consent"]["text"] == STEP7_ROUTE_KEY_COPY["consent"]
    assert observed["route_key_remember"]["text"] == STEP7_ROUTE_KEY_COPY["remember"]
    for widget in widgets:
        accessibility = widget["accessibility_observation"]
        if accessibility["available"]:
            assert accessibility["source"] == "QAccessible.queryAccessibleInterface"
            assert accessibility["name"].strip() and accessibility["role"]
        else:
            assert accessibility["diagnostic"].strip()


@pytest.mark.parametrize("state", ["blank", "key_without_consent", "consent_only", "remember_only", "both"])
def test_ac_qpb149_direct_builder_credential_states_and_secret_boundaries(run, state):
    key, consent, remember, embedded = {
        # Checked boxes with a blank key prove that neither destination receives a secret.
        "blank": ("", True, True, False),
        "key_without_consent": (KEY, False, False, False),
        "consent_only": (KEY, True, False, True),
        "remember_only": (KEY, False, True, False),
        "both": (KEY, True, True, True),
    }[state]
    r = run(operation="builder_route_credentials_boundary", state=state, input_key=key,
            consent=consent, remember=remember, outcome="success")
    assert r["build_success"] is True
    assert r["copy"] == {"consent": STEP7_ROUTE_KEY_COPY["consent"],
                          "remember": STEP7_ROUTE_KEY_COPY["remember"]}
    retained = bool(key) and remember
    credential_path = Path(r["desktop_credential_store"])
    assert credential_path.is_file() is retained
    if credential_path.is_file():
        assert KEY.encode() not in credential_path.read_bytes()
    assert r["desktop_retention_readback"] == {
        "present": retained,
        "source": "encrypted_credentials_store",
        "plaintext_at_rest": False,
    }
    assert r["generated_project_variable_count"] == (1 if embedded else 0)
    if embedded:
        value = r["project_variables"].get("fieldbuild_route_api_key")
        if value != KEY:
            pytest.fail("consented project variable did not preserve the submitted synthetic key", pytrace=False)
    else:
        assert "fieldbuild_route_api_key" not in r["project_variables"]
    for field in ("summary", "logs", "errors", "general_settings", "diagnostics"):
        assert_secret_absent(r.get(field), location=field)
    secret_files = []
    for artifact in map(Path, r["artifact_paths"]):
        assert artifact.is_file()
        if KEY.encode() in artifact.read_bytes():
            secret_files.append(artifact.resolve())
    if embedded:
        assert secret_files == [Path(r["qgs_path"]).resolve()]
        assert r["project_variable_occurrences"] == 1
    else:
        assert secret_files == []
    assert r["test_output_secret_redacted"] is True


def _route_panel_source():
    return (Path(__file__).parents[3] / "qfield_builder/qfield_routes/RoutePanel.qml").read_text(encoding="utf-8")


def test_ac046_theme_structure_uses_host_palette_and_semantic_roles_only():
    source = _route_panel_source()
    assert "SystemPalette" in source and "darkAppearance" in source
    for role in ("surfaceColor", "foregroundColor", "mutedColor", "outlineColor", "focusColor", "errorColor"):
        assert f"property color {role}" in source
    assert "palette.text: foregroundColor" in source
    assert "palette.placeholderText: mutedColor" in source


def test_ac047_header_and_first_control_are_distinct_ordered_structures_only():
    source = _route_panel_source()
    positions = [source.index(token) for token in (
        'objectName:"routeSummaryButton"', 'objectName:"routeScroll"',
        'objectName:"routeContent"', 'objectName:"layerEdit"')]
    assert positions == sorted(positions)
    assert 'onClicked:panel.expanded=!panel.expanded' in source
    assert 'objectName:"routeScroll";visible:panel.expanded' in source


def test_ac047_first_floating_label_has_real_content_top_clearance(run):
    observed = run(operation="route_workflow_ui", viewport_width=320,
                   start_mode="gps", scope="all", targets=[])
    gap = observed["first_floating_label_gap"]
    assert gap["gap"] >= 8
    assert gap["label_rect"]["bottom"] <= gap["control_rect"]["bottom"]


@pytest.mark.parametrize("instant_utc,device_timezone,locale", [
    ("2026-09-16T15:30:00+00:00", "Asia/Seoul", "ko_KR"),
    ("2026-09-17T01:00:00+00:00", "America/Los_Angeles", "en_US"),
    ("2026-09-17T23:30:00+00:00", "Pacific/Kiritimati", "de_DE"),
])
def test_ac048_controller_local_date_save_roundtrip_and_next_success_reset(
        instant_utc, device_timezone, locale):
    first_instant = datetime.fromisoformat(instant_utc)
    second_iso = datetime.fromtimestamp(first_instant.timestamp() + 86400, tz=timezone.utc).isoformat()

    def expected(instant):
        local = datetime.fromisoformat(instant).astimezone(ZoneInfo(device_timezone))
        return f"{local.year:04d}-{local.month:02d}-{local.day:02d} 조사"

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the production controller boundary")
    controller = Path(__file__).parents[3] / "qfield_builder/qfield_routes/controller.js"
    script = r'''const fs=require('fs'),vm=require('vm');const context=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);let now=process.argv[2],fail=false;
let disk={revision:0,slot:'a',data:{schema:2,routes:[],active_id:'',settings:{}}};const clone=x=>JSON.parse(JSON.stringify(x));
const make=()=>context.create({now:()=>new Date(now),uuid:()=>String(Date.now()),gps:()=>[127,37],
repository:{load:()=>clone(disk),save:(io,base,data,revision)=>{disk={revision:revision+1,slot:disk.slot==='a'?'b':'a',data:clone(data)};return clone(disk);}},
features:()=>[{id:'A',name:'A',coordinate:[127,37],completed:false}],geometry:{coordinate:x=>x},
backend:{calculate:async(s,list)=>{if(fail)throw new Error('fixture failure');return {stops:list,distance_m:2,duration_s:2,road_geometry:{type:'LineString',coordinates:[[127,37],[127,37],[127,37]]},legs:[{distance_m:1,duration_s:1,geometry:{type:'LineString',coordinates:[[127,37],[127,37]]}},{distance_m:1,duration_s:1,geometry:{type:'LineString',coordinates:[[127,37],[127,37]]}}]};}}});
(async()=>{let c=make();c.configure({optimizer_url:'https://fixture.invalid'});await c.calculate(false);const initial=c.state.candidate.name;
c.save('  현장 route 이름  ');c=make();const loaded=c.active().name;now=process.argv[3];await c.calculate(false);const next=c.state.candidate.name;
const before=JSON.stringify(c.state.candidate);fail=true;const failed=await c.calculate(false);process.stdout.write(JSON.stringify({initial,loaded,next,failed,preserved:before===JSON.stringify(c.state.candidate)}));})().catch(e=>{console.error(e);process.exit(1)});'''
    env = os.environ.copy(); env.update({"TZ": device_timezone, "LANG": locale, "LC_ALL": locale})
    result = subprocess.run([node, "-e", script, str(controller), instant_utc, second_iso],
                            capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed == {"initial": expected(instant_utc), "loaded": "현장 route 이름",
                        "next": expected(second_iso), "failed": False, "preserved": True}


def test_ac_qpb150_symbol_router_excludes_canonical_site_directly(monkeypatch):
    from qfield_builder import qgis_worker, schemas
    schema = schemas.get_schema("permanent_plots", site_geometry_type="POINT")
    layers = {name: object() for name, definition in schema.items() if definition.geometry is not None}
    svg, minimalist = [], []
    monkeypatch.setattr(qgis_worker, "_apply_svg_point_symbology", lambda _q, layer, _p: svg.append(layer))
    monkeypatch.setattr(qgis_worker, "_apply_minimalist_point_symbology", lambda _q, layer: minimalist.append(layer))
    monkeypatch.setattr(qgis_worker, "_apply_minimalist_polygon_symbology", lambda _q, _layer: None)
    qgis_worker._apply_symbol_styling({}, schema, layers, "symbols/map-pin.svg")
    eligible = {name for name, definition in schema.items()
                if definition.geometry is not None and definition.geometry.geom_type == "POINT"
                and name not in {"site", "community"}}
    assert minimalist == [layers["site"]]
    assert set(svg) == {layers[name] for name in eligible}


def _qgs_symbol_contract(qgs_path):
    records = {}
    for layer in ET.parse(qgs_path).getroot().findall("./projectlayers/maplayer"):
        datasource = layer.findtext("datasource", "")
        match = re.search(r"(?:^|\|)layername=([^|]+)", datasource)
        if match:
            records[match.group(1)] = {
                "display_name": layer.findtext("layername"),
                "classes": {node.get("class") for node in layer.findall(".//layer")},
                "svg_values": {node.get("value") for node in layer.findall(".//*[@value]")
                               if "symbols/" in node.get("value", "")},
            }
    return records


@pytest.mark.parametrize("site_geometry", ["Point", "MultiPoint"])
def test_ac_qpb150_generated_qgs_keeps_site_base_symbol_after_rename_and_relocation(
        tmp_path, site_geometry):
    from qfield_builder import schemas
    from qfield_builder.survey_route_acceptance import _build
    styling = {"mode": "tabler_icon", "tabler_icon_name": "map-pin", "tabler_svg_fetch":
               {"fake": {"mode": "success", "svg_content": '<svg xmlns="http://www.w3.org/2000/svg"/>'}}}
    wkt = "POINT(127 37)" if site_geometry == "Point" else "MULTIPOINT((127 37),(127.1 37.1))"
    result = _build(tmp_path, survey_type="permanent_plots", site_geometry_type=site_geometry.upper(),
                    sites=[{"site_id": "site-1", "site_name": "조사지", "geom_wkt": wkt}],
                    symbol_styling=styling)
    project_dir = Path(result["project_dir"]); moved = tmp_path / "moved"; shutil.copytree(project_dir, moved)
    qgs_path = next(moved.glob("*.qgs")); tree = ET.parse(qgs_path)
    site_node = next(node for node in tree.getroot().findall("./projectlayers/maplayer")
                     if "layername=site" in node.findtext("datasource", ""))
    site_node.find("layername").text = "Survey sites"; tree.write(qgs_path, encoding="utf-8", xml_declaration=True)
    records = _qgs_symbol_contract(qgs_path)
    schema = schemas.get_schema("permanent_plots", site_geometry_type=site_geometry.upper())
    eligible = {name for name, definition in schema.items()
                if definition.geometry is not None and definition.geometry.geom_type == "POINT"
                and name not in {"site", "community"}}
    assert "SvgMarker" not in records["site"]["classes"] and records["site"]["svg_values"] == set()
    assert records["site"]["display_name"] == "Survey sites"
    for table in eligible:
        assert "SvgMarker" in records[table]["classes"]
        assert records[table]["svg_values"] == {"symbols/map-pin.svg"}
        assert (moved / "symbols/map-pin.svg").is_file()


# DRAFT AC-SRP-049–058 harness redesign: observe production JS, HTTP, files and QML directly.
ROUTE_MODULES = Path(__file__).parents[3] / "qfield_builder" / "qfield_routes"
DIRECT_NODE = r"""
const fs=require("fs"),vm=require("vm"),http=require("http");
const input=JSON.parse(process.argv[1]);
function load(name){const c=vm.createContext({});vm.runInContext(fs.readFileSync(input.modules[name],"utf8"),c,{filename:input.modules[name]});return c;}
const backend=load("backend"),repository=load("repository"),controller=load("controller"),navigation=load("navigation");
let writeAttempts=0,writeSuccesses=0,providerRequestAttempts=0,failWrites=false;
function io(){
  return {exists:p=>fs.existsSync(p),read:p=>fs.readFileSync(p,"utf8"),write:(p,v)=>{
    writeAttempts++;if(failWrites)return false;fs.mkdirSync(require("path").dirname(p),{recursive:true});
    fs.writeFileSync(p,v);writeSuccesses++;return true;}};
}
function transport(request){
  providerRequestAttempts++;
  return new Promise((resolve,reject)=>{
    const target=new URL(request.url),body=JSON.stringify(request.body);
    const req=http.request({hostname:target.hostname,port:target.port,path:target.pathname+target.search,
      method:request.method,headers:Object.assign({},request.headers,{"Content-Length":Buffer.byteLength(body)})},res=>{
      const chunks=[];res.on("data",chunk=>chunks.push(chunk));res.on("end",()=>{
        const text=Buffer.concat(chunks).toString("utf8"),type=String(res.headers["content-type"]||"");
        if(res.statusCode<200||res.statusCode>=300){reject(backend.httpError(request.stage,res.statusCode,text,type,input.secret||""));return;}
        try{resolve(text?JSON.parse(text):{});}catch(error){reject(error);}
      });
    });
    req.setTimeout(request.timeout_ms||2000,()=>req.destroy(new Error("timeout")));
    req.on("error",reject);req.end(body);
  });
}
function fsIo(){return io();}
function serializeError(error){return {message:String(error&&error.message||error),stage:error&&error.stage||null,
  http_status:error&&error.http_status||null,safe_record:error&&error.safe_record||null,
  classification:error&&error.classification||null,suggested_actions:error&&error.suggested_actions||[]};}
function makeController(base,features){
  return controller.create({base,io:fsIo(),repository:{load:repository.load,save:repository.save},
    backend:{calculate:backend.calculate},transport,features:()=>features||[],
    geometry:{coordinate:value=>{if(!Array.isArray(value)||value.length<2)throw new Error("coordinate");return value.slice();}},
    gps:()=>input.start||[127,37],uuid:()=>input.uuid||"mixed-new",now:()=>new Date("2026-09-21T00:00:00Z"),
    projectKey:()=>input.secret||"",navigation:{open:navigation.open},openUrl:url=>{launcherCalls.push(url);return true;},
    platform:()=>input.platform||"ios",callerId:()=>input.caller_id||"ch.opengis.qfield"});
}
let launcherCalls=[];
(async()=>{
  let out={};
  if(input.operation==="backend"){
    try{out.result=await backend.calculate(input.settings,input.targets,input.start,input.roundtrip,transport);out.ok=true;}
    catch(error){out.ok=false;out.error=serializeError(error);}
  }else if(input.operation==="navigation"){
    let calls=[];let count=0;
    const opener=url=>{calls.push(url);count++;if(input.throw_on===count)throw new Error("launcher");return (input.open_results||[])[count-1]===true;};
    let stop=input.stop;if(input.special==="nan")stop={coordinate:[NaN,37],name:"x",site_id:"x"};
    if(input.special==="infinity")stop={coordinate:[127,Infinity],name:"x",site_id:"x"};
    try{out.result=navigation.open(stop,opener,input.platform,input.caller_id);out.ok=true;}catch(error){out.ok=false;out.error=serializeError(error);}
    out.calls=calls;
  }else if(input.operation==="repo_save"){
    const saved=repository.save(fsIo(),input.base,input.document,input.expected_revision);
    out={saved,files:fs.readdirSync(require("path").dirname(input.base)).sort(),writeAttempts,writeSuccesses};
  }else if(input.operation==="repo_load"){
    try{out.loaded=repository.load(fsIo(),input.base);out.ok=true;}catch(error){out.ok=false;out.error=serializeError(error);}
    out.writeAttempts=writeAttempts;out.writeSuccesses=writeSuccesses;
  }else if(input.operation==="repo_recovery"){
    const a=repository.save(fsIo(),input.base,input.good,0);
    const b=repository.save(fsIo(),input.base,input.good,a.revision);
    const corruptPath=input.base+"."+b.slot+".json",payload=JSON.stringify(input.corrupt);
    const lastGoodPath=input.base+"."+a.slot+".json",lastGoodBefore=fs.readFileSync(lastGoodPath,"utf8");
    fs.writeFileSync(corruptPath,JSON.stringify({revision:b.revision,checksum:repository.checksum(payload),payload}));
    const corruptBefore=fs.readFileSync(corruptPath,"utf8"),attemptsBefore=writeAttempts;
    try{out.loaded=repository.load(fsIo(),input.base);out.ok=true;}catch(error){out.ok=false;out.error=serializeError(error);}
    out.corrupt_bytes_before=corruptBefore;out.corrupt_bytes_after=fs.readFileSync(corruptPath,"utf8");
    out.last_good_bytes_before=lastGoodBefore;out.last_good_bytes_after=fs.readFileSync(lastGoodPath,"utf8");
    out.repository_writes_during_load=writeAttempts-attemptsBefore;
    out.provider_request_attempts=providerRequestAttempts;
  }else if(input.operation==="controller_flow"){
    if(input.document)repository.save(fsIo(),input.base,input.document,0);
    const instance=makeController(input.base,input.features);
    instance.state.roundtrip=input.roundtrip===true;
    instance.configure(input.settings);
    const calculated=await instance.calculate(input.replace_active===true);
    const candidate=instance.state.candidate?JSON.parse(JSON.stringify(instance.state.candidate)):null;
    if(input.acknowledge_unmapped===true)instance.acknowledgeUnmapped(true);
    const saved=calculated?instance.save(input.name||"혼합 경로"):false;
    out={calculated,saved,candidate,snapshot:instance.state.snapshot,state_message:instance.state.message,
      progress:instance.progress(),writeAttempts,writeSuccesses};
  }else if(input.operation==="controller_failure"){
    if(input.document)repository.save(fsIo(),input.base,input.document,0);
    const instance=makeController(input.base,input.features);
    instance.state.roundtrip=input.roundtrip===true;
    instance.configure(input.settings);
    const snapshotBefore=JSON.parse(JSON.stringify(instance.state.snapshot));
    const candidateBefore=instance.state.candidate?JSON.parse(JSON.stringify(instance.state.candidate)):null;
    const attemptsBefore=writeAttempts,successesBefore=writeSuccesses;
    const calculated=await instance.calculate(input.replace_active===true);
    out={calculated,candidate_before:candidateBefore,
      candidate_after:instance.state.candidate?JSON.parse(JSON.stringify(instance.state.candidate)):null,
      snapshot_before:snapshotBefore,snapshot_after:instance.state.snapshot,
      state_message:instance.state.message,last_error:instance.state.lastError,
      providerRequestAttempts,writeAttempts:writeAttempts-attemptsBefore,
      writeSuccesses:writeSuccesses-successesBefore};
  }else if(input.operation==="controller_state"){
    if(input.document)repository.save(fsIo(),input.base,input.document,0);
    const instance=makeController(input.base,input.features);
    const before=JSON.stringify(instance.state.snapshot.data),revision=instance.state.snapshot.revision;
    failWrites=input.fail_write===true;
    let result=null;
    if(input.action==="toggle")result=instance.toggleRouteLine(input.value);
    if(input.action==="settings")result=instance.saveSettings();
    out={result,before,after:instance.state.snapshot.data,revision_before:revision,
      revision_after:instance.state.snapshot.revision,show_route_line:instance.state.showRouteLine,
      message:instance.state.message,progress:instance.progress(),writeAttempts,writeSuccesses};
  }
  process.stdout.write(JSON.stringify(out));
})().catch(error=>{console.error(error&&error.stack||error);process.exit(1);});
"""


def _direct_node(operation, tmp_path, **payload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for direct production-JavaScript acceptance")
    data = {
        "operation": operation,
        "modules": {name: str(ROUTE_MODULES / f"{name}.js")
                    for name in ("backend", "controller", "repository", "navigation")},
        **payload,
    }
    result = subprocess.run(
        [node, "-e", DIRECT_NODE, json.dumps(data, ensure_ascii=False)],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@contextmanager
def _route_http(responder):
    records = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            body = json.loads(raw or b"{}")
            record = {
                "method": self.command,
                "path": self.path,
                "headers": {key.lower(): value for key, value in self.headers.items()},
                "body": body,
            }
            records.append(record)
            status, content_type, response = responder(record, len(records))
            payload = response if isinstance(response, bytes) else (
                response.encode("utf-8") if isinstance(response, str)
                else json.dumps(response, ensure_ascii=False).encode("utf-8"))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", records
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


MIXED_SOURCE = [127.01, 37.01]
MIXED_ACCESS = [127.009, 37.009]
MIXED_START = [127.0, 37.0]
MIXED_TARGET = {
    "source_layer": "site-layer", "site_id": "site-a", "name": "농촌 A",
    "coordinate": MIXED_SOURCE, "completed": False,
}


def _settings(base, secret="SRP_DIRECT_SYNTHETIC_SECRET"):
    return {
        "backend": "ors-vroom", "server_url": base, "optimizer_url": base + "/optimizer",
        "profile": "driving-car", "timeout_ms": 3000, "max_road_offset_m": 1000,
        "max_access_distance_m": 2000, "snap_batch_limit": 3500,
        "objective": "time", "key": secret,
    }


def _is_origin_validation_matrix(record):
    body = record["body"]
    locations = body.get("locations")
    return ("/v2/matrix/" in record["path"]
            and body.get("sources") == [0] and body.get("destinations") == [1]
            and isinstance(locations, list) and len(locations) == 2
            and locations[0] == locations[1])


def _is_vehicle_matrix(record):
    body = record["body"]
    return ("/v2/matrix/" in record["path"]
            and body.get("locations") == [MIXED_START, MIXED_ACCESS]
            and "sources" not in body and "destinations" not in body)


def _provider_responder(*, access=MIXED_ACCESS, fail_stage=None, status=503,
                        failure=None, malformed_walking=False, origin_response=None,
                        vehicle_response=None):
    matrix_calls = 0

    def respond(record, _sequence):
        nonlocal matrix_calls
        path, body = record["path"], record["body"]
        stage = None
        if "/v2/matrix/" in path:
            matrix_calls += 1
            stage = "origin-validation" if _is_origin_validation_matrix(record) else "matrix"
        elif "/v2/snap/" in path:
            stage = "access-snap"
        elif "/foot-hiking/" in path:
            stage = "walking-directions"
        elif path == "/optimizer":
            stage = "optimizer"
        elif "/v2/directions/" in path:
            stage = "directions"
        legacy_origin_body = {
            "locations": [MIXED_START], "metrics": ["duration"], "resolve_locations": True,
        }
        if stage == fail_stage and body != legacy_origin_body:
            return status, "application/json", failure or {"error": {"code": "PROVIDER_FAILURE", "message": "fixture failure"}}
        if stage == "origin-validation" or body == legacy_origin_body:
            response = origin_response if origin_response is not None else {
                "durations": [[0]],
                "sources": [{"location": MIXED_START, "snapped_distance": 0}],
                "destinations": [{"location": MIXED_START, "snapped_distance": 0}],
            }
            return 200, "application/json", response
        if stage == "access-snap":
            return 200, "application/json", {"locations": [{"location": access}]}
        if stage == "walking-directions":
            if malformed_walking:
                return 200, "application/json", {"features": []}
            return 200, "application/json", {"type": "FeatureCollection", "features": [{
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [access, MIXED_SOURCE]},
                "properties": {"summary": {"distance": 150, "duration": 120},
                               "segments": [{"distance": 150, "duration": 120}],
                               "way_points": [0, 1]},
            }]}
        if stage == "matrix":
            response = vehicle_response if vehicle_response is not None else {
                "durations": [[0, 600], [600, 0]], "distances": [[0, 1000], [1000, 0]],
                "sources": [{"snapped_distance": 0}, {"snapped_distance": 0}],
            }
            return 200, "application/json", response
        if stage == "optimizer":
            return 200, "application/json", {
                "code": 0, "unassigned": [],
                "routes": [{"distance": 1000, "duration": 600,
                            "steps": [{"type": "start"}, {"type": "job", "id": 0}]}],
            }
        if stage == "directions":
            return 200, "application/json", {"features": [{
                "geometry": {"type": "LineString", "coordinates": [MIXED_START, access]},
                "properties": {"summary": {"distance": 1000, "duration": 600},
                               "segments": [{"distance": 1000, "duration": 600}],
                               "way_points": [0, 1]},
            }]}
        return 404, "application/json", {"error": {"message": "unexpected fixture path"}}

    return respond


def _legacy_route(route_id, *, schema=2):
    coordinate = [127.02, 37.02] if route_id.endswith("b") else MIXED_SOURCE
    geometry = {"type": "LineString", "coordinates": [MIXED_START, coordinate]}
    route = {
        "route_id": route_id, "name": route_id, "revision": 1, "start": MIXED_START,
        "end": coordinate, "roundtrip": False, "backend": "ors-vroom",
        "stops": [{"source_layer": "site-layer", "site_id": "site-a", "name": "농촌 A",
                   "sequence": 1, "completed": False, "coordinate": coordinate}],
        "distance_m": 1000, "duration_s": 600, "road_geometry": geometry,
        "legs": [{"sequence": 1, "from": "start",
                  "to": {"layer_id": "site-layer", "site_id": "site-a"},
                  "distance_m": 1000, "duration_s": 600, "geometry": geometry}],
        "eta": None, "eta_basis": None,
    }
    if schema == 1:
        route.pop("legs")
        route.pop("road_geometry")
        route.pop("distance_m")
        route.pop("duration_s")
    return route


def _legacy_document(schema=2):
    return {
        "schema": schema, "active_id": "legacy-a",
        "routes": [_legacy_route("legacy-a", schema=schema), _legacy_route("legacy-b", schema=schema)],
        "settings": {"show_route_line": True},
    }


def _backend_run(tmp_path, responder, *, radius=2000, secret="SRP_DIRECT_SYNTHETIC_SECRET"):
    with _route_http(responder) as (base, records):
        observed = _direct_node(
            "backend", tmp_path, settings={**_settings(base, secret), "max_access_distance_m": radius},
            targets=[MIXED_TARGET], start=MIXED_START, roundtrip=False, secret=secret,
        )
    return observed, records


@pytest.mark.parametrize("stage", ["matrix", "optimizer", "directions"])
def test_ac049_http_failure_preserves_actual_stage_status_and_stops(stage, tmp_path):
    observed, records = _backend_run(
        tmp_path, _provider_responder(
            fail_stage=stage, status=429,
            failure={"error": {"code": " RATE_LIMIT\u202e ", "message": " wait   before retry "}},
        ))
    assert observed["ok"] is False
    assert observed["error"]["stage"] == stage
    assert observed["error"]["http_status"] == 429
    assert observed["error"]["safe_record"]["provider_code"] == "RATE_LIMIT"
    assert observed["error"]["safe_record"]["provider_message"] == "wait before retry"
    assert records[-1]["method"] == "POST"
    assert all(record["method"] == "POST" for record in records)


@pytest.mark.parametrize("body,content_type", [
    ("", "text/plain"),
    ("<html>failure</html>", "text/html"),
    ("Authorization: Bearer SRP_DIRECT_SYNTHETIC_SECRET", "text/plain"),
    ('{"error":{"code":"key=SRP_DIRECT_SYNTHETIC_SECRET","message":"secret"}}', "application/json"),
])
def test_ac049_unsafe_http_body_has_no_detail_or_secret(body, content_type, tmp_path):
    def responder(record, sequence):
        if sequence == 1:
            return 401, content_type, body
        return _provider_responder()(record, sequence)
    observed, _ = _backend_run(tmp_path, responder)
    assert observed["ok"] is False
    record = observed["error"]["safe_record"]
    assert record["provider_code"] is record["provider_message"] is record["safe_text"] is None
    assert "SRP_DIRECT_SYNTHETIC_SECRET" not in json.dumps(observed, ensure_ascii=False)


@pytest.mark.parametrize("radius", [350, 2000, 5000])
def test_ac050_single_batched_snap_uses_original_coordinates_and_exact_radius(radius, tmp_path):
    observed, records = _backend_run(tmp_path, _provider_responder(), radius=radius)
    assert observed["ok"] is True
    snap = [record for record in records if "/v2/snap/driving-car/json" in record["path"]]
    assert len(snap) == 1
    assert snap[0]["body"] == {"locations": [MIXED_SOURCE], "radius": radius}
    vehicle = [record for record in records if _is_vehicle_matrix(record)]
    assert len(vehicle) == 1
    assert observed["result"]["stops"][0]["coordinate"] == MIXED_SOURCE


def test_ac050_origin_validation_is_explicit_1x1_and_resolved_coordinates_are_validation_only(tmp_path):
    resolved = [MIXED_START[0] + 0.0001, MIXED_START[1] + 0.0001]
    origin_response = {
        "durations": [[0.25]],
        "sources": [{"location": resolved, "snapped_distance": 12.5}],
        "destinations": [{"location": resolved, "snapped_distance": 12.5}],
    }
    with _route_http(_provider_responder(origin_response=origin_response)) as (base, records):
        result = _direct_node(
            "controller_flow", tmp_path,
            base=str(tmp_path / "origin-validation" / "routes"),
            document=_legacy_document(),
            features=[{"id": "site-a", "name": "농촌 A",
                       "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(base), start=MIXED_START, roundtrip=False,
            replace_active=True, name="출발지 불변 경로",
        )
    assert result["calculated"] is result["saved"] is True
    origin = records[0]
    assert origin["path"] == "/v2/matrix/driving-car"
    assert origin["body"] == {
        "locations": [MIXED_START, MIXED_START],
        "sources": [0], "destinations": [1],
        "metrics": ["duration"], "resolve_locations": True,
    }
    access_snap = records[1]
    assert access_snap["body"] == {"locations": [MIXED_SOURCE], "radius": 2000}
    assert resolved not in access_snap["body"]["locations"]
    vehicle_matrix = records[-3]
    assert vehicle_matrix["body"]["locations"] == [MIXED_START, MIXED_ACCESS]
    vehicle_directions = records[-1]
    assert vehicle_directions["body"]["coordinates"] == [MIXED_START, MIXED_ACCESS]
    route = next(route for route in result["snapshot"]["data"]["routes"]
                 if route["route_schema"] == 3)
    assert route["start"] == MIXED_START
    assert route["stops"][0]["coordinate"] == MIXED_SOURCE
    assert route["visits"][0]["source_coordinate"] == MIXED_SOURCE
    assert resolved not in json.loads(json.dumps(route))["vehicle_legs"][0]["geometry"]["coordinates"]


@pytest.mark.parametrize("defect", [
    "unresolved_source", "unresolved_destination", "null_duration", "invalid_duration",
])
def test_ac050_invalid_origin_1x1_response_stops_with_actionable_start_error(defect, tmp_path):
    response = {
        "durations": [[0]],
        "sources": [{"location": MIXED_START, "snapped_distance": 0}],
        "destinations": [{"location": MIXED_START, "snapped_distance": 0}],
    }
    if defect == "unresolved_source":
        response["sources"][0]["location"] = None
    elif defect == "unresolved_destination":
        response["destinations"][0]["location"] = None
    elif defect == "null_duration":
        response["durations"][0][0] = None
    else:
        response["durations"][0][0] = "invalid"
    observed, records = _backend_run(
        tmp_path, _provider_responder(origin_response=response))
    assert observed["ok"] is False
    assert observed["error"]["stage"] == "origin-validation"
    assert observed["error"]["suggested_actions"] == ["map_start", "saved_start"]
    assert "도로 위" in observed["error"]["message"]
    assert [record["path"] for record in records] == ["/v2/matrix/driving-car"]


def test_ac050_null_snap_and_batch_limit_stop_without_downstream_request(tmp_path):
    null_result, records = _backend_run(tmp_path, _provider_responder(access=None))
    assert null_result["ok"] is False
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json"]
    assert "농촌 A" in null_result["error"]["message"] and "2.00 km" in null_result["error"]["message"]
    with _route_http(_provider_responder()) as (base, batch_records):
        result = _direct_node(
            "backend", tmp_path, settings={**_settings(base), "snap_batch_limit": 1},
            targets=[MIXED_TARGET, {**MIXED_TARGET, "site_id": "site-b"}],
            start=MIXED_START, roundtrip=False,
        )
    assert result["ok"] is False and batch_records == []


@pytest.mark.parametrize("mode", ["mapped", "exact_zero", "unmapped_estimate"])
def test_ac051_actual_backend_emits_roundtrip_walking_contract(mode, tmp_path):
    access = MIXED_SOURCE if mode == "exact_zero" else MIXED_ACCESS
    if mode == "unmapped_estimate":
        responder = _provider_responder(
            access=access, fail_stage="walking-directions", status=404,
            failure={"error": {"code": "NO_FOOT_ROUTE", "message": "no foot route found"}},
        )
    else:
        responder = _provider_responder(access=access)
    observed, records = _backend_run(tmp_path, responder)
    assert observed["ok"] is True
    visit = observed["result"]["visits"][0]
    assert visit["walking_mode"] == mode and visit["trip_multiplier"] == 2
    assert [leg["direction"] for leg in visit["walking_legs"]] == ["outbound", "return"]
    if mode == "exact_zero":
        assert not any("/foot-hiking/" in record["path"] for record in records)
        assert all(leg == {"direction": leg["direction"], "distance_m": 0,
                           "duration_s": 0, "geometry": None}
                   for leg in visit["walking_legs"])
    elif mode == "unmapped_estimate":
        assert visit["metric_source"] == "straight_line_lower_bound_m"
        assert all(leg["duration_s"] is None for leg in visit["walking_legs"])
        assert observed["result"]["combined_totals"] is None
    else:
        assert visit["metric_source"] == "ors-foot-hiking"
        assert visit["walking_legs"][1]["geometry"]["coordinates"] == list(
            reversed(visit["walking_legs"][0]["geometry"]["coordinates"]))


def test_ac051_ors_2010_no_routable_point_is_explicit_unmapped_only(tmp_path):
    explicit, records = _backend_run(tmp_path / "explicit", _provider_responder(
        fail_stage="walking-directions", status=404,
        failure={"error": {"code": 2010, "message":
                            "Could not find routable point within a radius of 350.0 meters "
                            "of specified coordinate 1: 126.9408626 36.2151360."}},
    ))
    assert explicit["ok"] is True
    visit = explicit["result"]["visits"][0]
    assert visit["walking_mode"] == "unmapped_estimate"
    assert visit["metric_source"] == "straight_line_lower_bound_m"
    assert all(leg["duration_s"] is None for leg in visit["walking_legs"])
    assert explicit["result"]["walking_totals"]["duration_s"] is None
    assert explicit["result"]["combined_totals"] is None
    assert any(record["path"] == "/optimizer" for record in records)

    generic, generic_records = _backend_run(tmp_path / "generic", _provider_responder(
        fail_stage="walking-directions", status=404,
        failure={"error": {"code": 2010, "message": "fixture failure"}},
    ))
    assert generic["ok"] is False
    assert [record["path"] for record in generic_records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson"]


def test_ac051_malformed_walking_response_does_not_fallback_or_continue(tmp_path):
    observed, records = _backend_run(tmp_path, _provider_responder(malformed_walking=True))
    assert observed["ok"] is False
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson"]
    assert "도보" in observed["error"]["message"]


def test_ac051_unmapped_save_requires_acknowledgement_and_keeps_null_totals(tmp_path):
    responder = _provider_responder(
        fail_stage="walking-directions", status=404,
        failure={"error": {"code": "NO_FOOT_ROUTE", "message": "no foot route found"}},
    )
    with _route_http(responder) as (base, _records):
        common = {
            "document": _legacy_document(),
            "features": [{"id": "site-a", "name": "농촌 A",
                          "coordinate": MIXED_SOURCE, "completed": False}],
            "settings": _settings(base), "start": MIXED_START, "roundtrip": False,
            "replace_active": True, "name": "fallback 경로",
        }
        blocked = _direct_node(
            "controller_flow", tmp_path,
            base=str(tmp_path / "fallback-blocked" / "routes"), **common,
        )
        accepted = _direct_node(
            "controller_flow", tmp_path,
            base=str(tmp_path / "fallback-accepted" / "routes"),
            acknowledge_unmapped=True, **common,
        )
    assert blocked["calculated"] is True and blocked["saved"] is False
    assert "지도에 없는 도보 구간 포함" in blocked["state_message"]
    assert accepted["saved"] is True
    route = next(route for route in accepted["snapshot"]["data"]["routes"]
                 if route["route_schema"] == 3)
    assert route["walking_totals"]["duration_s"] is None
    assert route["combined_totals"] is None


# APPROVED TEST DESIGN (approval 2026-09-22): generated-QML unmapped-save click regression.
def _unmapped_save_qml_click(tmp_path, *, fault=""):
    """Build a disposable project and drive its generated acknowledgement/save controls."""
    from qfield_builder.survey_route_acceptance import _build

    generated = _build(tmp_path / ("failure" if fault else "success"), sites=[{
        "site_id": "site-a", "site_name": "농촌 A", "geom_wkt": "POINT(127.01 37.01)",
    }], site_geometry_type="POINT")
    driver = Path(__file__).parent / "unmapped_save_qml_driver.py"
    payload = {
        "project_dir": generated["project_dir"],
        "case": {
            "operation": "unmapped_save_qml_click",
            "route_name": "현장 fallback 경로",
            "fault": fault,
            "features": [{"id": "site-a", "name": "농촌 A", "xy": [127.01, 37.01]}],
        },
    }
    completed = subprocess.run(
        [sys.executable, str(driver)], input=json.dumps(payload), text=True,
        encoding="utf-8", errors="replace", capture_output=True, timeout=45,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_ac036_ac051_ac052_unmapped_generated_qml_click_saves_schema3_and_reports_path(tmp_path):
    observed = _unmapped_save_qml_click(tmp_path)
    controls = observed["qml_controls"]
    assert observed["qml_runtime"]["loaded_generated_qml"] is True
    assert controls["acknowledgement_object_name"] == "unmappedAcknowledgement"
    assert controls["save_object_name"] == "saveRouteButton"
    assert controls["save_enabled_before_ack"] is False
    assert controls["acknowledgement_checked"] is True
    assert controls["save_enabled_after_ack"] is True

    route_name = observed["route_name_input"].strip()
    relative_path = observed["committed_project_relative_path"]
    assert observed["save_ok"] is True
    assert observed["candidate_after_click"] is None
    assert relative_path in {"survey-routes.a.json", "survey-routes.b.json"}
    assert route_name in observed["message_after_click"]
    assert relative_path in observed["message_after_click"]
    assert observed["feedback_in_viewport"] is True

    document = observed["document_after_click"]
    reopened_document = observed["independently_reopened_document"]
    assert document == reopened_document
    assert document["schema"] == 3
    assert observed["route_after_click"] == observed["independently_reopened_route"]
    route = observed["route_after_click"]
    assert route["route_schema"] == 3
    assert route["name"] == route_name
    assert route["visits"][0]["walking_mode"] == "unmapped_estimate"
    assert route["walking_totals"]["duration_s"] is None
    assert route["combined_totals"] is None
    assert observed["load_enabled_after_click"] is True
    assert observed["independently_reopened_load_enabled"] is True
    assert any(item["route_id"] == route["route_id"]
               for item in observed["independently_reopened_list"])


def test_ac036_unmapped_generated_qml_save_failure_keeps_candidate_and_shows_error(tmp_path):
    observed = _unmapped_save_qml_click(tmp_path, fault="commit_failure")
    assert observed["qml_controls"]["save_enabled_after_ack"] is True
    assert observed["save_ok"] is False
    assert observed["candidate_after_click"] == observed["candidate_before_click"]
    assert observed["document_after_click"] is None
    assert observed["route_after_click"] is None
    assert observed["listed_after_click"] == []
    assert observed["load_enabled_after_click"] is False
    assert observed["committed_project_relative_path"] is None
    assert "저장 실패" in observed["message_after_click"]
    assert "저장했습니다" not in observed["message_after_click"]
    assert observed["feedback_in_viewport"] is True


def _saved_mixed_document(tmp_path):
    with _route_http(_provider_responder()) as (base, records):
        base_path = str(tmp_path / "project" / "survey-routes")
        result = _direct_node(
            "controller_flow", tmp_path, base=base_path, document=_legacy_document(),
            features=[{"id": "site-a", "name": "농촌 A", "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(base), start=MIXED_START, roundtrip=False, replace_active=True,
            name="저장 혼합 경로", secret="SRP_DIRECT_SYNTHETIC_SECRET",
        )
    assert result["calculated"] is True
    assert result["saved"] is True
    return result, records, Path(base_path)


def _saved_active_inactive_schema3_document(tmp_path):
    result, records, _ = _saved_mixed_document(tmp_path / "mapped")
    document = result["snapshot"]["data"]
    cases = [
        ("mixed-exact", _provider_responder(access=MIXED_SOURCE), False),
        ("mixed-unmapped", _provider_responder(
            fail_stage="walking-directions", status=404,
            failure={"error": {"code": "NO_FOOT_ROUTE", "message": "no foot route found"}},
        ), True),
    ]
    final_base = None
    for route_id, responder, acknowledge in cases:
        final_base = tmp_path / route_id / "routes"
        with _route_http(responder) as (provider_base, new_records):
            result = _direct_node(
                "controller_flow", tmp_path, base=str(final_base), document=document,
                features=[{"id": "site-a", "name": "농촌 A",
                           "coordinate": MIXED_SOURCE, "completed": False}],
                settings=_settings(provider_base), start=MIXED_START, roundtrip=False,
                replace_active=False, acknowledge_unmapped=acknowledge,
                name=route_id, uuid=route_id,
            )
        assert result["calculated"] is True and result["saved"] is True
        document = result["snapshot"]["data"]
        records.extend(new_records)
    return document, records, final_base


AC056_ALLOWED_MODE_SOURCES = {
    ("mapped", "ors-foot-hiking"),
    ("exact_zero", "exact_zero"),
    ("unmapped_estimate", "straight_line_lower_bound_m"),
}
AC056_VISIT_CORRUPTIONS = [
    ("missing", "layer_id", None), ("blank", "layer_id", " "),
    ("missing", "site_id", None), ("blank", "site_id", "\t"),
    ("missing", "metric_source", None), ("blank", "metric_source", " "),
    ("identity_mismatch", "layer_id", "other-layer"),
    ("identity_mismatch", "site_id", "other-site"),
    ("unknown", "walking_mode", "unknown"),
    ("unknown", "metric_source", "unknown"),
    *(("disallowed_pair", "walking_mode/metric_source", pair)
      for pair in sorted({
          ("mapped", "exact_zero"),
          ("mapped", "straight_line_lower_bound_m"),
          ("exact_zero", "ors-foot-hiking"),
          ("exact_zero", "straight_line_lower_bound_m"),
          ("unmapped_estimate", "ors-foot-hiking"),
          ("unmapped_estimate", "exact_zero"),
      })),
]


def test_ac052_ac057_production_save_roundtrips_schema3_and_preserves_legacy(tmp_path):
    result, _, base = _saved_mixed_document(tmp_path)
    document = result["snapshot"]["data"]
    assert document["schema"] == 3
    assert {route["route_id"] for route in document["routes"]} == {"legacy-a", "legacy-b"}
    selected = next(route for route in document["routes"] if route["route_id"] == "legacy-a")
    unrelated = next(route for route in document["routes"] if route["route_id"] == "legacy-b")
    assert selected["route_schema"] == 3
    assert unrelated["route_schema"] == 2
    assert unrelated["name"] == "legacy-b"
    moved = tmp_path / "moved"
    shutil.move(base.parent, moved)
    reopened = _direct_node("repo_load", tmp_path, base=str(moved / base.name))
    assert reopened["ok"] is True
    assert reopened["loaded"]["data"] == document
    assert reopened["writeAttempts"] == 0


def test_ac054_actual_http_sequence_and_privacy_boundary(tmp_path):
    secret = "SRP_DIRECT_SYNTHETIC_SECRET"
    observed, records = _backend_run(tmp_path, _provider_responder(), secret=secret)
    assert observed["ok"] is True
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson", "/v2/matrix/driving-car",
        "/optimizer", "/v2/directions/driving-car/geojson",
    ]
    optimizer = next(record for record in records if record["path"] == "/optimizer")
    wire = json.dumps(optimizer["body"], ensure_ascii=False)
    assert "농촌 A" not in wire and "site-a" not in wire and "site-layer" not in wire
    assert optimizer["body"]["jobs"] == [{"id": 0, "location_index": 1}]
    assert all(record["headers"]["authorization"] == secret for record in records)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


@pytest.mark.parametrize("platform,results,expected", [
    ("ios", [True], ["https://maps.apple.com/directions?destination=37.456,127.123&mode=driving"]),
    ("ios", [False], ["https://maps.apple.com/directions?destination=37.456,127.123&mode=driving"]),
    ("android", [False, True], [
        "intent://navigation?dlat=37.456&dlng=127.123&dname=%ED%95%9C%EA%B8%80%20%26%20%23%25%20&appname=org.example%2F%23%25#Intent;scheme=nmap;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.nhn.android.nmap;end",
        "market://details?id=com.nhn.android.nmap",
    ]),
])
def test_ac039_ac055_navigation_open_direct_spy(platform, results, expected, tmp_path):
    observed = _direct_node(
        "navigation", tmp_path, platform=platform, open_results=results,
        caller_id="org.example/#%", stop={"coordinate": [127.123, 37.456],
                                          "name": "한글 & #% ", "site_id": "site-a"},
    )
    assert observed["calls"] == expected
    if platform == "ios" and results == [False]:
        assert observed["ok"] is False
        assert observed["error"]["message"] == "Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요."
    elif platform == "ios":
        assert observed["result"]["os_request_accepted"] is True
        assert "확인할 수 없습니다" in observed["result"]["message"]


@pytest.mark.parametrize("coordinate,special", [
    ([180, 90], None), ([-180, -90], None), ([127.123456789, -0.0], None),
    (["127.1", 37], None), ([181, 37], None), ([127, 91], None),
    ([127, 37], "nan"), ([127, 37], "infinity"),
])
def test_ac055_coordinate_normalization_or_rejection(coordinate, special, tmp_path):
    observed = _direct_node(
        "navigation", tmp_path, platform="ios", open_results=[True], special=special,
        stop={"coordinate": coordinate, "name": "x", "site_id": "x"},
    )
    valid = special is None and all(isinstance(value, (int, float)) for value in coordinate) and abs(coordinate[0]) <= 180 and abs(coordinate[1]) <= 90
    assert len(observed["calls"]) == (1 if valid else 0)
    if coordinate == [127.123456789, -0.0]:
        assert observed["calls"] == [
            "https://maps.apple.com/directions?destination=0,127.1234568&mode=driving"]


def test_ac056_three_allowed_combinations_roundtrip_active_and_inactive(tmp_path):
    document, _, base = _saved_active_inactive_schema3_document(tmp_path)
    mixed = [route for route in document["routes"] if route["route_schema"] == 3]
    assert len(mixed) == 3
    assert {route["route_id"] for route in mixed} > {document["active_id"]}
    assert {(visit["walking_mode"], visit["metric_source"])
            for route in mixed for visit in route["visits"]} == AC056_ALLOWED_MODE_SOURCES
    moved = tmp_path / "allowed-moved"
    shutil.move(base.parent, moved)
    reopened = _direct_node("repo_load", tmp_path, base=str(moved / base.name))
    assert reopened["ok"] is True
    assert reopened["loaded"]["data"] == document
    assert reopened["writeAttempts"] == 0


@pytest.mark.parametrize("route_state", ["active", "inactive"])
def test_ac056_corrupt_visit_recovery_preserves_bytes_and_last_good(route_state, tmp_path):
    good, _, _ = _saved_active_inactive_schema3_document(tmp_path)
    mixed = [route for route in good["routes"] if route["route_schema"] == 3]
    target_id = (good["active_id"] if route_state == "active" else
                 next(route["route_id"] for route in mixed
                      if route["route_id"] != good["active_id"]))
    for index, (kind, field, value) in enumerate(AC056_VISIT_CORRUPTIONS):
        corrupt = deepcopy(good)
        visit = next(route for route in corrupt["routes"]
                     if route["route_id"] == target_id)["visits"][0]
        if kind == "missing":
            visit.pop(field)
        elif kind == "disallowed_pair":
            visit["walking_mode"], visit["metric_source"] = value
        else:
            visit[field] = value
        recovered = _direct_node(
            "repo_recovery", tmp_path,
            base=str(tmp_path / f"recovery-{route_state}-{index}" / "routes"),
            good=good, corrupt=corrupt,
        )
        case = (route_state, kind, field, value)
        assert recovered["ok"] is True, case
        assert recovered["loaded"]["data"] == good, case
        assert recovered["loaded"]["recovered"] is True, case
        assert recovered["corrupt_bytes_after"] == recovered["corrupt_bytes_before"], case
        assert recovered["last_good_bytes_after"] == recovered["last_good_bytes_before"], case
        assert recovered["repository_writes_during_load"] == 0, case
        assert recovered["provider_request_attempts"] == 0, case


@pytest.mark.parametrize("corruption", [
    "unknown_marker", "legacy_with_mixed", "mixed_without_mixed", "duplicate_identity",
])
def test_ac057_variant_corruption_recovery_is_atomic(corruption, tmp_path):
    result, _, _ = _saved_mixed_document(tmp_path)
    good = result["snapshot"]["data"]
    corrupt = deepcopy(good)
    mixed = next(route for route in corrupt["routes"] if route["route_schema"] == 3)
    legacy = next(route for route in corrupt["routes"] if route["route_schema"] == 2)
    if corruption == "unknown_marker":
        legacy["route_schema"] = 99
    elif corruption == "legacy_with_mixed":
        legacy["visits"] = deepcopy(mixed["visits"])
    elif corruption == "mixed_without_mixed":
        mixed.pop("visits")
    else:
        legacy["route_id"] = mixed["route_id"]
    recovered = _direct_node(
        "repo_recovery", tmp_path, base=str(tmp_path / "variants" / "routes"),
        good=good, corrupt=corrupt,
    )
    assert recovered["loaded"]["data"] == good
    assert recovered["corrupt_bytes_after"] == recovered["corrupt_bytes_before"]
    assert recovered["last_good_bytes_after"] == recovered["last_good_bytes_before"]
    assert recovered["repository_writes_during_load"] == 0
    assert recovered["provider_request_attempts"] == 0


def test_ac057_schema3_rejects_schema1_marker_with_schema2_legs_and_preserves_bytes(tmp_path):
    result, _, _ = _saved_mixed_document(tmp_path)
    good = result["snapshot"]["data"]
    assert good["schema"] == 3
    corrupt = deepcopy(good)
    legacy = next(route for route in corrupt["routes"] if route["route_schema"] == 2)
    assert "legs" in legacy
    legacy["route_schema"] = 1
    recovered = _direct_node(
        "repo_recovery", tmp_path, base=str(tmp_path / "schema1-legs" / "routes"),
        good=good, corrupt=corrupt,
    )
    assert recovered["ok"] is True
    assert recovered["loaded"]["data"] == good
    assert recovered["loaded"]["recovered"] is True
    assert recovered["corrupt_bytes_after"] == recovered["corrupt_bytes_before"]
    assert recovered["last_good_bytes_after"] == recovered["last_good_bytes_before"]
    assert recovered["repository_writes_during_load"] == 0
    assert recovered["provider_request_attempts"] == 0


def test_ac057_default_and_settings_only_never_promote_to_schema3(tmp_path):
    base = str(tmp_path / "default" / "routes")
    fresh = _direct_node("controller_state", tmp_path, base=base, action="none")
    assert fresh["after"]["schema"] == 2 and fresh["writeSuccesses"] == 0
    settings = _direct_node("controller_state", tmp_path, base=base, action="settings")
    assert settings["result"] and settings["after"]["schema"] == 2
    schema1 = _direct_node(
        "controller_state", tmp_path, base=str(tmp_path / "schema1" / "routes"),
        document=_legacy_document(schema=1), action="settings",
    )
    assert schema1["result"] and schema1["after"]["schema"] == 2


def test_ac057_schema1_settings_upgrade_then_mixed_save_keeps_legacy_schema1(tmp_path):
    upgraded = _direct_node(
        "controller_state", tmp_path, base=str(tmp_path / "upgrade-first" / "routes"),
        document=_legacy_document(schema=1), action="settings",
    )
    assert upgraded["after"]["schema"] == 2
    with _route_http(_provider_responder()) as (base, _records):
        saved = _direct_node(
            "controller_flow", tmp_path, base=str(tmp_path / "upgrade-then-mixed" / "routes"),
            document=upgraded["after"],
            features=[{"id": "site-a", "name": "농촌 A",
                       "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(base), start=MIXED_START, roundtrip=False,
            replace_active=True, name="혼합 전환",
        )
    assert saved["saved"] is True
    unrelated = next(route for route in saved["snapshot"]["data"]["routes"]
                     if route["route_id"] == "legacy-b")
    assert unrelated["route_schema"] == 1
    assert "legs" not in unrelated


def test_ac058_toggle_persists_exact_setting_through_restart_and_folder_move(tmp_path):
    base = tmp_path / "toggle-project" / "routes"
    toggled = _direct_node(
        "controller_state", tmp_path, base=str(base), document=_legacy_document(),
        action="toggle", value=False,
    )
    assert toggled["result"] is True and toggled["show_route_line"] is False
    assert toggled["after"]["settings"]["show_route_line"] is False
    assert toggled["after"]["routes"] == _legacy_document()["routes"]
    assert toggled["writeSuccesses"] == 2  # seed plus one atomic slot write
    moved = tmp_path / "toggle-moved"
    shutil.move(base.parent, moved)
    reopened = _direct_node("controller_state", tmp_path, base=str(moved / "routes"), action="none")
    assert reopened["show_route_line"] is False
    assert reopened["writeSuccesses"] == 0


def test_ac058_toggle_write_failure_rolls_back_and_reports_failure(tmp_path):
    observed = _direct_node(
        "controller_state", tmp_path, base=str(tmp_path / "toggle-fail" / "routes"),
        document=_legacy_document(), action="toggle", value=False, fail_write=True,
    )
    assert observed["result"] is False
    assert observed["show_route_line"] is True
    assert observed["after"]["settings"]["show_route_line"] is True
    assert observed["revision_after"] == observed["revision_before"]
    assert "실패" in observed["message"] and "저장" in observed["message"]


def test_ac053_qml_runtime_reads_real_tree_repeater_and_qaccessible(run):
    sites = [
        {"id": f"access-{index}", "name": f"접근성 조사지 {index}",
         "xy": [127.31 + index / 100, 37.31 + index / 100]}
        for index in range(5)
    ]
    observed = run(
        operation="mixed_route_presentation", viewport_width=320, theme="light",
        include_fallback=True, actions=["preview", "legend"],
    )
    visit_observed = run(
        operation="mixed_route_presentation", viewport_width=320, theme="light",
        include_fallback=True, sites=sites,
        visit_value_fixtures=["five-visits-all-modes-a"],
        exact_zero_visit_index=4,
        actions=["reload-each-visit-value-route"],
    )
    assert {key: value["pattern"] for key, value in observed["line_classes"].items()} == {
        "vehicle": "solid", "mapped_walking": "dashed", "unmapped_walking": "dotted"}
    assert observed["warning_marker"]["visible"] is True
    for result, actions in ((observed, ["preview", "legend"]),
                            (visit_observed, ["reload-each-visit-value-route"])):
        boundary = result["passive_boundary_observation"]
        assert boundary["provider_attempts"] == []
        assert boundary["storage_write_attempts"] == []
        assert boundary["provider_attempt_count"] == len(boundary["provider_attempts"])
        assert boundary["storage_write_attempt_count"] == len(boundary["storage_write_attempts"])
        assert [item["action"] for item in boundary["action_windows"]] == actions
        for window in boundary["action_windows"]:
            assert window["provider_attempt_count_before"] == 0
            assert window["provider_attempt_count_after"] == 0
            assert window["storage_write_attempt_count_before"] == 0
            assert window["storage_write_attempt_count_after"] == 0
            assert window["product_operation_completed"] is True
    interfaces = observed["accessibility_observations"]
    assert interfaces
    assert all(item["source"] in {
        "QAccessible.queryAccessibleInterface",
        "QML Accessible attached property runtime readback",
    } for item in interfaces)
    assert all(item["object_id"] and item["name"].strip() for item in interfaces)
    delegate_runs = visit_observed["visit_accessibility_binding_observations"]
    assert delegate_runs
    for run_observation in delegate_runs:
        model = run_observation["delegate_model_observation"]["value"]
        assert model["creation"] == "QML Repeater delegate"
        assert model["enumeration"] == "Repeater.itemAt(index)"
        delegates = [item["value"] for item in run_observation["delegate_readback_observations"]]
        assert model["delegate_count"] == len(delegates)
        assert all(item["lookup"] == "Repeater.itemAt(index)" for item in delegates)
        assert all(item["qaccessible"]["source"] == "QAccessible.queryAccessibleInterface"
                   for item in delegates)


# APPROVED AC-SRP-059 baseline; DRAFT reviewer correction to evidence/negative coverage.
SNAPPED_PROVIDER_GEOMETRY = {
    "type": "LineString",
    "coordinates": [[127.0094, 37.0094], [127.0095, 37.00955], [127.0096, 37.0096]],
}
SNAPPED_DISTANCE_M = 30
SNAPPED_DURATION_S = 20
ENDPOINT_GAP_DISCLOSURE = "ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함"


def _geodesic_m(first, second):
    radius = 6371008.8
    lat1, lat2 = math.radians(first[1]), math.radians(second[1])
    dlat = lat2 - lat1
    dlon = math.radians(second[0] - first[0])
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(value))


def _snapped_walking_response():
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": deepcopy(SNAPPED_PROVIDER_GEOMETRY),
        "properties": {
            "summary": {"distance": SNAPPED_DISTANCE_M, "duration": SNAPPED_DURATION_S},
            "segments": [{"distance": SNAPPED_DISTANCE_M, "duration": SNAPPED_DURATION_S}],
            "way_points": [0, 2],
        },
    }]}


def _one_point_zero_walking_response():
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[127.0095, 37.0095]]},
        "properties": {
            "summary": {"distance": 0, "duration": 0},
            "segments": [{"distance": 0, "duration": 0}],
            "way_points": [0, 0],
        },
    }]}


def _walking_response_responder(response):
    default = _provider_responder()

    def respond(record, sequence):
        if "/v2/directions/foot-hiking/geojson" in record["path"]:
            return 200, "application/geo+json", deepcopy(response)
        return default(record, sequence)

    return respond


def _snapped_saved_document(tmp_path):
    document = _legacy_document()
    records = []
    final_base = None
    for route_id in ("snapped-a", "snapped-b"):
        final_base = tmp_path / route_id / "survey-routes"
        with _route_http(_walking_response_responder(_snapped_walking_response())) as (provider, captured):
            result = _direct_node(
                "controller_flow", tmp_path, base=str(final_base), document=document,
                features=[{"id": "site-a", "name": "농촌 A",
                           "coordinate": MIXED_SOURCE, "completed": False}],
                settings=_settings(provider), start=MIXED_START, roundtrip=False,
                replace_active=False, name=route_id, uuid=route_id,
            )
        assert result["calculated"] is True and result["saved"] is True
        document = result["snapshot"]["data"]
        records.extend(captured)
    return document, records, final_base


def test_ac059_snapped_provider_geometry_is_mapped_without_connector_or_gap_metric(tmp_path):
    assert _geodesic_m(SNAPPED_PROVIDER_GEOMETRY["coordinates"][0], MIXED_ACCESS) > 1
    assert _geodesic_m(SNAPPED_PROVIDER_GEOMETRY["coordinates"][-1], MIXED_SOURCE) > 1
    assert SNAPPED_DISTANCE_M < _geodesic_m(MIXED_ACCESS, MIXED_SOURCE)
    observed, records = _backend_run(
        tmp_path, _walking_response_responder(_snapped_walking_response()))
    assert observed["ok"] is True
    visit = observed["result"]["visits"][0]
    assert visit["walking_mode"] == "mapped"
    assert visit["metric_source"] == "ors-foot-hiking"
    assert visit["access_coordinate"] == MIXED_ACCESS
    assert visit["source_coordinate"] == MIXED_SOURCE
    outbound, inbound = visit["walking_legs"]
    assert outbound == {
        "direction": "outbound", "distance_m": SNAPPED_DISTANCE_M,
        "duration_s": SNAPPED_DURATION_S, "geometry": SNAPPED_PROVIDER_GEOMETRY,
    }
    assert inbound == {
        **outbound, "direction": "return",
        "geometry": {"type": "LineString",
                     "coordinates": list(reversed(SNAPPED_PROVIDER_GEOMETRY["coordinates"]))},
    }
    assert observed["result"]["walking_totals"] == {
        "mapped_distance_m": 2 * SNAPPED_DISTANCE_M,
        "lower_bound_distance_m": 0,
        "duration_s": 2 * SNAPPED_DURATION_S,
        "unavailable_duration_count": 0,
    }
    assert not any(record["path"].endswith("/optimizer") for record in records[:3])


def test_ac059_schema3_active_inactive_restart_offline_move_exact_roundtrip(tmp_path):
    document, records, base = _snapped_saved_document(tmp_path)
    assert document["schema"] == 3
    snapped = {route["route_id"]: route for route in document["routes"]
               if route["route_id"] in {"snapped-a", "snapped-b"}}
    assert set(snapped) == {"snapped-a", "snapped-b"}
    assert document["active_id"] == "snapped-b"
    for route_id, route in snapped.items():
        assert route["route_schema"] == 3
        visit = route["visits"][0]
        assert set(visit) == {
            "layer_id", "site_id", "site_name", "source_coordinate", "access_coordinate",
            "access_offset_m", "walking_mode", "walking_legs", "trip_multiplier", "metric_source",
        }
        assert visit["source_coordinate"] == MIXED_SOURCE
        assert visit["access_coordinate"] == MIXED_ACCESS
        assert visit["walking_mode"] == "mapped"
        assert visit["metric_source"] == "ors-foot-hiking"
        assert visit["walking_legs"][0]["geometry"] == SNAPPED_PROVIDER_GEOMETRY
        assert visit["walking_legs"][0]["distance_m"] == SNAPPED_DISTANCE_M
        assert visit["walking_legs"][0]["duration_s"] == SNAPPED_DURATION_S
        assert visit["walking_legs"][1]["geometry"]["coordinates"] == list(
            reversed(SNAPPED_PROVIDER_GEOMETRY["coordinates"]))
    assert any(route_id != document["active_id"] for route_id in snapped)
    assert sum("/v2/directions/foot-hiking/geojson" in record["path"] for record in records) == 2
    moved = tmp_path / "snapped-moved"
    shutil.move(base.parent, moved)
    reopened = _direct_node("repo_load", tmp_path, base=str(moved / base.name))
    assert reopened["ok"] is True
    assert reopened["loaded"]["data"] == document
    assert reopened["writeAttempts"] == 0


def _invalid_snapped_response(fault):
    response = _snapped_walking_response()
    feature = response["features"][0]
    properties = feature["properties"]
    if fault == "missing_way_points":
        properties.pop("way_points")
    elif fault == "non_array_way_points":
        properties["way_points"] = "0,2"
    elif fault == "wrong_length_way_points":
        properties["way_points"] = [0]
    elif fault == "non_integer_way_points":
        properties["way_points"] = [0, 1.5]
    elif fault == "non_increasing_way_points":
        properties["way_points"] = [2, 0]
    elif fault == "non_covering_start":
        properties["way_points"] = [1, 2]
    elif fault == "non_covering_end":
        properties["way_points"] = [0, 1]
    elif fault == "multiple_segments":
        properties["segments"].append({"distance": 0, "duration": 0})
    elif fault == "multiple_features":
        response["features"].append(deepcopy(feature))
    elif fault == "features_object_array_like":
        response["features"] = {"0": deepcopy(feature), "length": 1}
    elif fault == "invalid_geometry":
        feature["geometry"] = {"type": "Point", "coordinates": [127.0095, 37.0095]}
    elif fault == "invalid_summary":
        properties["summary"]["distance"] = -1
    elif fault == "invalid_segment":
        properties["segments"][0].pop("duration")
    elif fault == "distance_tolerance_mismatch":
        properties["summary"]["distance"] = SNAPPED_DISTANCE_M + 1.01
    elif fault == "duration_tolerance_mismatch":
        properties["summary"]["duration"] = SNAPPED_DURATION_S + 1.01
    else:
        raise AssertionError(fault)
    return response


@pytest.mark.parametrize("fault", [
    "missing_way_points", "non_array_way_points", "wrong_length_way_points",
    "non_integer_way_points", "non_increasing_way_points", "non_covering_start",
    "non_covering_end", "multiple_segments", "multiple_features", "features_object_array_like",
    "invalid_geometry",
    "invalid_summary", "invalid_segment", "distance_tolerance_mismatch",
    "duration_tolerance_mismatch",
])
def test_ac059_malformed_walking_contract_stops_before_vehicle_write_and_preserves_last_good(
        fault, tmp_path):
    with _route_http(_walking_response_responder(_invalid_snapped_response(fault))) as (provider, records):
        observed = _direct_node(
            "controller_failure", tmp_path,
            base=str(tmp_path / fault / "survey-routes"), document=_legacy_document(),
            features=[{"id": "site-a", "name": "농촌 A",
                       "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(provider), start=MIXED_START, roundtrip=False,
            replace_active=True,
        )
    assert observed["calculated"] is False
    assert observed["snapshot_after"] == observed["snapshot_before"]
    assert observed["candidate_after"] == observed["candidate_before"]
    assert observed["writeAttempts"] == observed["writeSuccesses"] == 0
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson",
    ]
    assert observed["last_error"]["category"] == "provider_response"
    assert observed["state_message"].strip()


def test_ac060_one_point_zero_route_reuses_existing_unmapped_contract(tmp_path):
    observed, records = _backend_run(
        tmp_path, _walking_response_responder(_one_point_zero_walking_response()))
    assert observed["ok"] is True
    visit = observed["result"]["visits"][0]
    assert visit["walking_mode"] == "unmapped_estimate"
    assert visit["metric_source"] == "straight_line_lower_bound_m"
    assert visit["access_coordinate"] == MIXED_ACCESS
    assert visit["source_coordinate"] == MIXED_SOURCE
    outbound, inbound = visit["walking_legs"]
    assert outbound["geometry"] == {
        "type": "LineString", "coordinates": [MIXED_ACCESS, MIXED_SOURCE]}
    assert inbound["geometry"]["coordinates"] == [MIXED_SOURCE, MIXED_ACCESS]
    assert outbound["duration_s"] is None and inbound["duration_s"] is None
    assert outbound["distance_m"] == pytest.approx(_geodesic_m(MIXED_ACCESS, MIXED_SOURCE))
    assert observed["result"]["walking_totals"] == {
        "mapped_distance_m": 0,
        "lower_bound_distance_m": pytest.approx(2 * outbound["distance_m"]),
        "duration_s": None,
        "unavailable_duration_count": 2,
    }
    assert observed["result"]["combined_totals"] is None
    assert any(record["path"] == "/optimizer" for record in records)
    assert [127.0095, 37.0095] not in outbound["geometry"]["coordinates"]


def test_ac060_one_point_zero_route_requires_existing_unmapped_acknowledgement(tmp_path):
    responder = _walking_response_responder(_one_point_zero_walking_response())
    with _route_http(responder) as (base, _records):
        common = {
            "document": _legacy_document(),
            "features": [{"id": "site-a", "name": "농촌 A",
                          "coordinate": MIXED_SOURCE, "completed": False}],
            "settings": _settings(base), "start": MIXED_START, "roundtrip": False,
            "replace_active": True, "name": "1점 fallback 경로",
        }
        blocked = _direct_node(
            "controller_flow", tmp_path,
            base=str(tmp_path / "one-point-blocked" / "routes"), **common)
        accepted = _direct_node(
            "controller_flow", tmp_path,
            base=str(tmp_path / "one-point-accepted" / "routes"),
            acknowledge_unmapped=True, **common)
    assert blocked["calculated"] is True and blocked["saved"] is False
    assert "지도에 없는 도보 구간 포함" in blocked["state_message"]
    assert accepted["saved"] is True
    route = next(route for route in accepted["snapshot"]["data"]["routes"]
                 if route["route_schema"] == 3)
    assert route["visits"][0]["walking_mode"] == "unmapped_estimate"
    assert route["walking_totals"]["duration_s"] is None


def _invalid_one_point_response(fault):
    response = _one_point_zero_walking_response()
    feature = response["features"][0]
    properties = feature["properties"]
    if fault == "nonzero_summary_distance":
        properties["summary"]["distance"] = 1
    elif fault == "nonzero_segment_duration":
        properties["segments"][0]["duration"] = 1
    elif fault == "missing_summary_duration":
        properties["summary"].pop("duration")
    elif fault == "nonnumeric_segment_distance":
        properties["segments"][0]["distance"] = "0"
    elif fault == "bad_way_points":
        properties["way_points"] = [0, 1]
    elif fault == "zero_coordinates":
        feature["geometry"]["coordinates"] = []
    elif fault == "two_coordinates_zero_way_points":
        feature["geometry"]["coordinates"].append([127.0095, 37.0095])
    elif fault == "multiple_segments":
        properties["segments"].append({"distance": 0, "duration": 0})
    elif fault == "multiple_features":
        response["features"].append(deepcopy(feature))
    else:
        raise AssertionError(fault)
    return response


@pytest.mark.parametrize("fault", [
    "nonzero_summary_distance", "nonzero_segment_duration",
    "missing_summary_duration", "nonnumeric_segment_distance", "bad_way_points",
    "zero_coordinates", "two_coordinates_zero_way_points", "multiple_segments",
    "multiple_features",
])
def test_ac060_invalid_degenerate_variants_fail_atomically_without_fallback(fault, tmp_path):
    responder = _walking_response_responder(_invalid_one_point_response(fault))
    with _route_http(responder) as (provider, records):
        observed = _direct_node(
            "controller_failure", tmp_path,
            base=str(tmp_path / fault / "survey-routes"), document=_legacy_document(),
            features=[{"id": "site-a", "name": "농촌 A",
                       "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(provider), start=MIXED_START, roundtrip=False,
            replace_active=True,
        )
    assert observed["calculated"] is False
    assert observed["snapshot_after"] == observed["snapshot_before"]
    assert observed["candidate_after"] == observed["candidate_before"]
    assert observed["writeAttempts"] == observed["writeSuccesses"] == 0
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson",
    ]
    assert observed["last_error"]["category"] == "provider_response"


def test_ac059_qml_observes_requested_markers_provider_line_and_exact_gap_disclosure(run):
    observed = run(
        operation="mixed_route_presentation", viewport_width=320, theme="light",
        sites=[{"id": "site-a", "name": "농촌 A", "xy": MIXED_SOURCE}],
        snapped_endpoint_fixture={
            "requested_access_coordinate": MIXED_ACCESS,
            "requested_source_coordinate": MIXED_SOURCE,
            "provider_geometry": SNAPPED_PROVIDER_GEOMETRY,
            "distance_m": SNAPPED_DISTANCE_M,
            "duration_s": SNAPPED_DURATION_S,
            "way_points": [0, 2],
        },
        actions=["preview", "legend", "reload-each-visit-value-route"],
    )
    endpoint = observed["snapped_endpoint_observation"]
    access_markers = endpoint["access_marker_observations"]
    assert len(access_markers) == 1
    assert access_markers[0]["object_id"]
    assert access_markers[0]["object_name"]
    assert access_markers[0]["coordinate_property"] == "accessCoordinate"
    assert access_markers[0]["coordinate"] == MIXED_ACCESS
    source_features = endpoint["source_feature_observations"]
    assert len(source_features) == 1
    assert source_features[0]["provider_layer_id"]
    assert source_features[0]["provider_feature_id"] is not None
    assert source_features[0]["coordinate_source"] == "provider feature geometry"
    assert source_features[0]["coordinate"] == MIXED_SOURCE
    rendered_lines = endpoint["walking_line_observations"]
    assert len(rendered_lines) == 1
    assert rendered_lines[0]["object_id"]
    assert rendered_lines[0]["object_name"]
    assert rendered_lines[0]["coordinates_property"] == "coordinates"
    assert rendered_lines[0]["coordinates"] == SNAPPED_PROVIDER_GEOMETRY["coordinates"]
    assert rendered_lines[0]["line_pattern"] == "dashed"
    visit_model = endpoint["visit_model_observation"]
    assert visit_model["model_source"] in {"panel.candidate.visits", "panel.route.visits"}
    assert len(visit_model["visits"]) == 1
    visit = visit_model["visits"][0]
    assert visit["access_coordinate"] == MIXED_ACCESS
    assert visit["source_coordinate"] == MIXED_SOURCE
    assert visit["walking_mode"] == "mapped"
    assert visit["metric_source"] == "ors-foot-hiking"
    assert visit["walking_legs"] == [
        {"direction": "outbound", "distance_m": SNAPPED_DISTANCE_M,
         "duration_s": SNAPPED_DURATION_S, "geometry": SNAPPED_PROVIDER_GEOMETRY},
        {"direction": "return", "distance_m": SNAPPED_DISTANCE_M,
         "duration_s": SNAPPED_DURATION_S,
         "geometry": {"type": "LineString", "coordinates": list(reversed(
             SNAPPED_PROVIDER_GEOMETRY["coordinates"]))}},
    ]
    totals = endpoint["walking_totals_observation"]
    assert totals["model_source"] in {
        "panel.candidate.walking_totals", "panel.routeProgress.remaining_walking"}
    assert totals["value"] == {
        "mapped_distance_m": 2 * SNAPPED_DISTANCE_M,
        "lower_bound_distance_m": 0,
        "duration_s": 2 * SNAPPED_DURATION_S,
        "unavailable_duration_count": 0,
    }
    # These zeroes are derived here from complete runtime enumerations, never supplied by the harness.
    connector_lines = [line for line in rendered_lines
                       if line["coordinates"] != SNAPPED_PROVIDER_GEOMETRY["coordinates"]]
    gap_metric_or_duration = (
        totals["value"]["mapped_distance_m"] - sum(
            leg["distance_m"] for leg in visit["walking_legs"]),
        totals["value"]["duration_s"] - sum(
            leg["duration_s"] for leg in visit["walking_legs"]),
    )
    assert connector_lines == []
    assert gap_metric_or_duration == (0, 0)
    assert endpoint["source_coordinate_write_attempts"] == []
    disclosures = observed["endpoint_gap_disclosures"]
    assert set(disclosures) == {"calculation_result", "saved_detail", "legend_accessibility"}
    for context, disclosure in disclosures.items():
        assert disclosure["text"] == ENDPOINT_GAP_DISCLOSURE, context
        assert disclosure["accessible_name"] == ENDPOINT_GAP_DISCLOSURE, context
        assert disclosure["object_id"], context
        assert disclosure["source"] in {
            "QAccessible.queryAccessibleInterface",
            "QML Accessible attached property runtime readback",
        }
    boundary = observed["passive_boundary_observation"]
    assert boundary["provider_attempts"] == []
    assert boundary["storage_write_attempts"] == []
    assert boundary["source_write_attempts"] == []


# AC-SRP-061: Matrix optional snapped_distance -----------------------------------------------

_MISSING_DIAGNOSTIC = object()
_NONFINITE_JSON_NUMBER = object()


def _matrix_location_responses(slot, value):
    origin = {
        "durations": [[0]],
        "sources": [{"location": MIXED_START, "snapped_distance": 0}],
        "destinations": [{"location": MIXED_START, "snapped_distance": 0}],
    }
    vehicle = {
        "durations": [[0, 600], [600, 0]],
        "distances": [[0, 1000], [1000, 0]],
        "sources": [{"snapped_distance": 0}, {"snapped_distance": 0}],
    }
    row = {
        "origin_source": origin["sources"][0],
        "origin_destination": origin["destinations"][0],
        "vehicle_source_0": vehicle["sources"][0],
        "vehicle_source_1": vehicle["sources"][1],
    }[slot]
    if value is _MISSING_DIAGNOSTIC:
        row.pop("snapped_distance")
    elif value is _NONFINITE_JSON_NUMBER:
        row["snapped_distance"] = "__NONFINITE_JSON_NUMBER__"
    else:
        row["snapped_distance"] = value

    def encoded(document):
        if value is not _NONFINITE_JSON_NUMBER:
            return document
        return json.dumps(document, separators=(",", ":")).replace(
            '"__NONFINITE_JSON_NUMBER__"', "1e309")

    if slot.startswith("origin_"):
        origin = encoded(origin)
    else:
        vehicle = encoded(vehicle)
    return origin, vehicle


def _controller_provider_run(tmp_path, responder, *, expect_success, name):
    with _route_http(responder) as (base, records):
        operation = "controller_flow" if expect_success else "controller_failure"
        observed = _direct_node(
            operation, tmp_path,
            base=str(tmp_path / name / "survey-routes"), document=_legacy_document(),
            features=[{"id": "site-a", "name": "농촌 A",
                       "coordinate": MIXED_SOURCE, "completed": False}],
            settings=_settings(base), start=MIXED_START, roundtrip=False,
            replace_active=True, name="Matrix diagnostic 경로",
        )
    return observed, records


@pytest.mark.parametrize("slot", [
    "origin_source", "origin_destination", "vehicle_source_0", "vehicle_source_1",
])
def test_ac061_missing_snapped_distance_independently_allows_calculation_and_save(slot, tmp_path):
    origin, vehicle = _matrix_location_responses(slot, _MISSING_DIAGNOSTIC)
    observed, records = _controller_provider_run(
        tmp_path, _provider_responder(origin_response=origin, vehicle_response=vehicle),
        expect_success=True, name="missing-" + slot,
    )
    assert observed["calculated"] is observed["saved"] is True
    route = next(route for route in observed["snapshot"]["data"]["routes"]
                 if route.get("route_schema") == 3)
    assert "snapped_distance" not in json.dumps(route, ensure_ascii=False)
    assert [record["path"] for record in records] == [
        "/v2/matrix/driving-car", "/v2/snap/driving-car/json",
        "/v2/directions/foot-hiking/geojson", "/v2/matrix/driving-car",
        "/optimizer", "/v2/directions/driving-car/geojson",
    ]


@pytest.mark.parametrize("slot,expected_stage", [
    ("origin_source", "origin-validation"),
    ("origin_destination", "origin-validation"),
    ("vehicle_source_0", "matrix"),
    ("vehicle_source_1", "matrix"),
])
@pytest.mark.parametrize("invalid", [
    pytest.param("12.5", id="string"),
    pytest.param(None, id="null"),
    pytest.param(_NONFINITE_JSON_NUMBER, id="nonfinite"),
    pytest.param(-0.01, id="negative"),
])
def test_ac061_present_invalid_snapped_distance_fails_at_its_stage_and_preserves_state(
        slot, expected_stage, invalid, tmp_path):
    origin, vehicle = _matrix_location_responses(slot, invalid)
    observed, records = _controller_provider_run(
        tmp_path, _provider_responder(origin_response=origin, vehicle_response=vehicle),
        expect_success=False, name=f"invalid-{slot}-{id(invalid)}",
    )
    assert observed["calculated"] is False
    assert observed["snapshot_after"] == observed["snapshot_before"]
    assert observed["candidate_after"] == observed["candidate_before"]
    assert observed["writeAttempts"] == observed["writeSuccesses"] == 0
    assert observed["last_error"]["stage"] == expected_stage
    expected_count = 1 if expected_stage == "origin-validation" else 4
    assert len(records) == expected_count
    assert not any(record["path"] == "/optimizer" for record in records)
    assert not any("/v2/directions/driving-car/" in record["path"] for record in records)


@pytest.mark.parametrize("distance,success", [(1000, True), (1000.01, False)])
def test_ac061_vehicle_snapped_distance_honors_inclusive_configured_maximum(
        distance, success, tmp_path):
    origin, vehicle = _matrix_location_responses("vehicle_source_1", distance)
    observed, records = _controller_provider_run(
        tmp_path, _provider_responder(origin_response=origin, vehicle_response=vehicle),
        expect_success=success, name="boundary-" + str(distance),
    )
    if success:
        assert observed["calculated"] is observed["saved"] is True
        assert records[-1]["path"] == "/v2/directions/driving-car/geojson"
    else:
        assert observed["calculated"] is False
        assert observed["snapshot_after"] == observed["snapshot_before"]
        assert observed["candidate_after"] == observed["candidate_before"]
        assert observed["writeAttempts"] == observed["writeSuccesses"] == 0
        assert observed["last_error"]["stage"] == "matrix"
        assert records[-1]["path"] == "/v2/matrix/driving-car"


def _structurally_invalid_matrix_responses(fault):
    origin, vehicle = _matrix_location_responses("origin_source", 0)
    if fault == "origin_sources_cardinality":
        origin["sources"] = []
    elif fault == "origin_destinations_object":
        origin["destinations"] = {"0": origin["destinations"][0]}
    elif fault == "origin_location":
        origin["sources"][0]["location"] = None
    elif fault == "origin_duration":
        origin["durations"] = [[None]]
    elif fault == "vehicle_sources_cardinality":
        vehicle["sources"].pop()
    elif fault == "vehicle_sources_object":
        vehicle["sources"] = {"0": vehicle["sources"][0], "1": vehicle["sources"][1]}
    elif fault == "vehicle_duration":
        vehicle["durations"][0][1] = None
    elif fault == "vehicle_distance":
        vehicle["distances"][0][1] = "1000"
    else:
        raise AssertionError(fault)
    return origin, vehicle


@pytest.mark.parametrize("fault,expected_stage", [
    ("origin_sources_cardinality", "origin-validation"),
    ("origin_destinations_object", "origin-validation"),
    ("origin_location", "origin-validation"),
    ("origin_duration", "origin-validation"),
    ("vehicle_sources_cardinality", "matrix"),
    ("vehicle_sources_object", "matrix"),
    ("vehicle_duration", "matrix"),
    ("vehicle_distance", "matrix"),
])
def test_ac061_optional_diagnostic_does_not_relax_matrix_structure_or_metrics(
        fault, expected_stage, tmp_path):
    origin, vehicle = _structurally_invalid_matrix_responses(fault)
    observed, records = _controller_provider_run(
        tmp_path, _provider_responder(origin_response=origin, vehicle_response=vehicle),
        expect_success=False, name="structure-" + fault,
    )
    assert observed["calculated"] is False
    assert observed["snapshot_after"] == observed["snapshot_before"]
    assert observed["candidate_after"] == observed["candidate_before"]
    assert observed["writeAttempts"] == observed["writeSuccesses"] == 0
    assert observed["last_error"]["stage"] == expected_stage
    assert len(records) == (1 if expected_stage == "origin-validation" else 4)


# AC-SRP-062: canonical desktop credential store ----------------------------------------------

_ROUTE_CREDENTIAL = "SRP_ROUTE_KEY_SYNTHETIC_62"
_CREDENTIAL_PASSWORD = "acceptance-only-password-62"


def _configure_fake_app_data(monkeypatch, tmp_path, platform):
    from qfield_builder import credential_store

    monkeypatch.delenv(credential_store._APP_DATA_DIR_ENV_OVERRIDE, raising=False)
    monkeypatch.setattr(credential_store.sys, "platform", platform)
    if platform == "darwin":
        home = tmp_path / "home"
        monkeypatch.setattr(
            credential_store.Path, "home", classmethod(lambda _cls: home))
        root = home / "Library" / "Application Support"
    else:
        root = tmp_path / "Roaming"
        monkeypatch.setenv("APPDATA", str(root))
    return credential_store, root


def _directory_snapshot(path):
    if not path.exists():
        return None
    return [
        (item.relative_to(path).as_posix(), item.is_dir(), None if item.is_dir() else item.read_bytes())
        for item in sorted(path.rglob("*"))
    ]


def _seed_sibling(path, state):
    if state == "absent":
        return
    path.mkdir(parents=True)
    if state == "populated":
        (path / "credentials.enc").write_bytes(b"SIBLING-STORE-MUST-REMAIN-BYTE-IDENTICAL")
        (path / "sibling-state.txt").write_text("unchanged", encoding="utf-8")


@pytest.mark.parametrize("platform,fieldbuild_state,qpb_state", [
    ("darwin", "absent", "absent"),
    ("darwin", "empty", "populated"),
    ("win32", "populated", "empty"),
    ("win32", "populated", "populated"),
])
def test_ac062_canonical_platform_store_shares_three_keys_and_ignores_siblings(
        platform, fieldbuild_state, qpb_state, monkeypatch, tmp_path):
    credential_store, root = _configure_fake_app_data(monkeypatch, tmp_path, platform)
    canonical = root / "FieldBuild Standalone"
    siblings = [root / "FieldBuild Kit", root / "QField Project Builder"]
    _seed_sibling(siblings[0], fieldbuild_state)
    _seed_sibling(siblings[1], qpb_state)
    sibling_before = [_directory_snapshot(path) for path in siblings]
    credential_store.lock_session()
    credential_store.set_session_route_key(None)
    try:
        assert credential_store.credentials_file_path() == canonical / "credentials.enc"
        credential_store.establish_password(_CREDENTIAL_PASSWORD)
        credential_store.remember_key("SYNTHETIC-VWORLD-62")
        credential_store.remember_plantnet_key("SYNTHETIC-PLANTNET-62")
        credential_store.remember_route_key(_ROUTE_CREDENTIAL)
        encrypted = (canonical / "credentials.enc").read_bytes()
        assert all(secret not in encrypted for secret in (
            b"SYNTHETIC-VWORLD-62", b"SYNTHETIC-PLANTNET-62",
            _ROUTE_CREDENTIAL.encode(),
        ))
        credential_store.lock_session()
        credential_store.unlock_session(_CREDENTIAL_PASSWORD)
        assert credential_store.get_remembered_key() == "SYNTHETIC-VWORLD-62"
        assert credential_store.get_remembered_plantnet_key() == "SYNTHETIC-PLANTNET-62"
        assert credential_store.get_remembered_route_key() == _ROUTE_CREDENTIAL
        assert credential_store.migrate_legacy_credentials() is False
        assert [_directory_snapshot(path) for path in siblings] == sibling_before
    finally:
        credential_store.lock_session()
        credential_store.set_session_route_key(None)


def test_ac062_diagnostic_override_uses_exactly_one_disposable_store(monkeypatch, tmp_path):
    from qfield_builder import credential_store

    override = tmp_path / "diagnostic-override"
    sibling = tmp_path / "FieldBuild Kit"
    _seed_sibling(sibling, "populated")
    sibling_before = _directory_snapshot(sibling)
    monkeypatch.setenv(credential_store._APP_DATA_DIR_ENV_OVERRIDE, str(override))
    credential_store.lock_session()
    credential_store.set_session_route_key(None)
    try:
        credential_store.establish_password(_CREDENTIAL_PASSWORD)
        assert credential_store.apply_route_retention_policy(_ROUTE_CREDENTIAL, True) is True
        path = credential_store.credentials_file_path()
        assert path == override / "credentials.enc"
        assert [item.relative_to(override).as_posix() for item in override.rglob("*")] == [
            "credentials.enc"]
        credential_store.lock_session()
        credential_store.unlock_session(_CREDENTIAL_PASSWORD)
        assert credential_store.get_remembered_route_key() == _ROUTE_CREDENTIAL
        assert _directory_snapshot(sibling) == sibling_before
    finally:
        credential_store.lock_session()
        credential_store.set_session_route_key(None)


@pytest.mark.parametrize("case,key,remember,store_failure", [
    ("remember-off", _ROUTE_CREDENTIAL, False, False),
    ("blank", "   ", True, False),
    ("store-failure", _ROUTE_CREDENTIAL, True, True),
])
def test_ac062_nonretained_branches_build_without_store_or_plaintext_fallback(
        case, key, remember, store_failure, monkeypatch, tmp_path):
    from qfield_builder import build as build_module
    from qfield_builder import credential_store

    store_dir = tmp_path / case / "FieldBuild Standalone"
    project_dir = tmp_path / case / "generated-project"
    siblings = [tmp_path / case / "FieldBuild Kit", tmp_path / case / "QField Project Builder"]
    for sibling in siblings:
        _seed_sibling(sibling, "populated")
    sibling_before = [_directory_snapshot(path) for path in siblings]
    monkeypatch.setenv(credential_store._APP_DATA_DIR_ENV_OVERRIDE, str(store_dir))
    credential_store.lock_session()
    credential_store.set_session_route_key(None)
    if store_failure:
        def fail_remember(_key):
            raise OSError("synthetic credential-store failure")
        monkeypatch.setattr(credential_store, "remember_route_key", fail_remember)
    try:
        result = build_module.build_project({
            "project_display_name": "AC062 retention " + case,
            "survey_type": "temporary_plots",
            "basemap": {"mode": "none"},
            "survey_route": {
                "api_key": key,
                "consent_accepted": False,
                "remember_key": remember,
            },
        }, str(project_dir))
        assert result["success"] is True
        assert not credential_store.credentials_file_path().exists()
        assert credential_store.get_session_route_key() == key.strip()
        files = [path for path in project_dir.rglob("*") if path.is_file()]
        assert not any(path.name == "credentials.enc" for path in files)
        assert not any(_ROUTE_CREDENTIAL.encode() in path.read_bytes() for path in files)
        normal_surfaces = json.dumps(result, ensure_ascii=False)
        assert _ROUTE_CREDENTIAL not in normal_surfaces
        assert str(credential_store.credentials_file_path()) not in normal_surfaces
        assert [_directory_snapshot(path) for path in siblings] == sibling_before
    finally:
        credential_store.lock_session()
        credential_store.set_session_route_key(None)


def test_ac062_remembered_route_key_is_not_copied_or_exposed_by_builder_ui(run):
    observed = run(
        operation="builder_step7_route_credentials", state="remember-only",
        input_key=_ROUTE_CREDENTIAL, consent=False, remember=True, outcome="success",
    )
    credential_path = Path(observed["desktop_credential_store"])
    assert observed["build_success"] is True
    assert observed["desktop_retention_readback"] == {
        "present": True,
        "source": "encrypted_credentials_store",
        "plaintext_at_rest": False,
    }
    assert observed["key_input_echo_mode"] == "password"
    route_widget = next(widget for widget in observed["widgets"]
                        if widget["semantic_id"] == "route_key")
    assert route_widget["echo_mode"] == "password"
    assert _ROUTE_CREDENTIAL not in json.dumps(
        route_widget["accessibility_observation"], ensure_ascii=False)
    for widget in observed["widgets"]:
        if widget["semantic_id"] != "route_key":
            assert _ROUTE_CREDENTIAL not in widget["text"]
    safe_surfaces = {name: observed[name] for name in (
        "summary", "logs", "errors", "reports", "message", "qml_errors", "diagnostics")}
    serialized = json.dumps(safe_surfaces, ensure_ascii=False)
    assert _ROUTE_CREDENTIAL not in serialized
    assert str(credential_path) not in serialized
    artifacts = [Path(path) for path in observed["artifact_paths"]]
    assert not any(path.name == "credentials.enc" for path in artifacts)
    assert not any(_ROUTE_CREDENTIAL.encode() in path.read_bytes() for path in artifacts)
    assert observed["remembered_key_available_to_qfield"] is False
