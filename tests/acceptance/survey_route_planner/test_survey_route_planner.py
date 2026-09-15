"""DRAFT acceptance reconciliation for approved specification checkpoint bd625d6.

The adapter executes production behavior; only transport/device/file faults are fakes.
See HARNESS_CONTRACT.md. Missing new seam skips; broken existing seam fails.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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
        "properties": {"summary": {"distance": 1234, "duration": 456}, "segments": DIRECTIONS_LEGS},
        "geometry": ROAD,
    }],
}

PORTABLE_SETTINGS = {
    "server_url": "https://routing.invalid/ors",
    "optimizer_url": "https://optimizer.invalid/vroom",
    "backend": "ors-vroom",
    "profile": "driving-car",
    "timeout_ms": 1250,
    "max_road_offset_m": 50,
    "default_start": [127.123, 37.456],
    "mapping": {"layer": "custom_targets", "id": "custom_id", "name": "title", "completed": "done"},
}


def ids(route):
    return [stop["site_id"] for stop in route["stops"]]


def no_calls(result):
    assert result["requests"] == []


def rejected(result):
    assert result["saved_before"], "scenario must seed a nonempty saved baseline"
    assert result["ok"] is False
    assert result["message"].strip()
    assert result["saved_after"] == result["saved_before"]


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
    assert {"targets", "settings", "results", "save", "load"} <= set(r["panel"]["controls"])


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
    assert {s["source_layer"] for s in r["candidate"]["stops"]} == {"site"}


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


@pytest.mark.parametrize("extras", [False, True])
def test_ac007_result_roundtrip(run, extras):
    r = run(operation="result_roundtrip", backend="ors-vroom",
            optimizer_response=vroom_response(include_arrivals=extras),
            directions_response=DIRECTIONS_RESPONSE if extras else None)
    route = r["reloaded"]
    for field in ("route_id", "name", "backend", "status"):
        assert route[field]
    datetime.fromisoformat(route["created_at"].replace("Z", "+00:00"))
    assert route["distance_m"] == 1234 and route["duration_s"] == 456
    assert ids(route) == ["2", "0", "1"]
    assert [s["sequence"] for s in route["stops"]] == [1, 2, 3]
    assert route["eta"] == (ETA if extras else None)
    assert route["eta_basis"] == ("relative_seconds" if extras else None)
    assert route["road_geometry"] == (ROAD if extras else None)
    assert route["legs"] == (LEGS if extras else None)
    assert r["saved"] == route
    for field in ("road_geometry", "eta", "legs"):
        assert r["availability"][field] is extras
    if extras:
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
    assert r["settings_before"] == PORTABLE_SETTINGS
    assert r["settings_after"] == PORTABLE_SETTINGS
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
    r = run(operation="complete", features=features, completed_ids=["0", "2"],
            source=completion_source, mapping=mapping)
    assert r["completed_count"] == 2 and r["total_count"] == 8
    assert r["next_id"] == "1"
    assert {s["site_id"] for s in r["active"]["stops"] if s["completed"]} == {"0", "2"}
    assert {s["site_id"] for s in r["reloaded"]["stops"] if s["completed"]} == {"0", "2"}
    assert r["summary_counts"] == [2, 8]
    assert r["completion_help"]["mapped_boolean_only"] is True
    assert r["completion_help"]["blank_mapping_uses_route_local"] is True
    assert r["source_completion_after"] == ({"0": True, "2": True} if completion_source == "field" else {})
    no_calls(r)


@pytest.mark.parametrize("fault", ["read_only", "invalid_type"])
def test_ac010_completion_write_failure_preserves_state(run, fault):
    r = run(operation="completion_write_failure", fault=fault, completed_id="0", seed_saved=True)
    rejected(r)
    assert r["source_completion_after"] == r["source_completion_before"]
    assert r["active_after"] == r["active_before"]
    assert r["next_after"] == r["next_before"]
    no_calls(r)


@pytest.mark.parametrize("outcome", ["preview", "save", "failure"])
def test_ac011_remaining_revision(run, outcome):
    r = run(operation="remaining", features=POINTS, completed_ids=["0", "1", "2", "3"],
            gps=[127.55, 37.66], outcome=outcome)
    assert sorted(r["submitted_ids"], key=int) == [str(i) for i in range(4, 12)]
    assert r["request_start"] == [127.55, 37.66]
    assert r["completed_after"] == r["completed_before"]
    if outcome == "save":
        assert r["saved_after"]["revision"] > r["saved_before"]["revision"]
        assert r["saved_after"]["route_id"] == r["saved_before"]["route_id"]
    else:
        assert r["saved_after"] == r["saved_before"]
    if outcome == "failure":
        assert r["ok"] is False and r["message"].strip()


@pytest.mark.parametrize("launch", [True, False])
def test_ac012_road_and_naver(run, launch):
    name = "조사지 A & B/#?"
    r = run(operation="reopen_navigate", road_geometry=ROAD, destination=[127.123, 37.456], name=name, launch_result=launch)
    assert r["rendered_geometry"] == ROAD
    url = urlsplit(r["launched_url"])
    assert url.scheme == "nmap" and url.netloc == "navigation"
    query = parse_qs(url.query)
    assert float(query["dlng"][0]) == 127.123 and float(query["dlat"][0]) == 37.456
    assert query["dname"] == [name] and not url.fragment
    if not launch:
        assert r["message"].strip()
    assert r["destination_app_success_claimed"] is False
    no_calls(r)


@pytest.mark.parametrize("action", ["expand", "collapse", "complete", "load", "restart"])
def test_ac013_no_network_or_secrets(run, action):
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
def test_ac018_regression_portability(run, survey_type, reference):
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


@pytest.mark.parametrize("case", ["M01_panel_selection", "M02_start_backend", "M03_offline_recovery", "M04_completion",
                                  "M05_naver", "M06_drawing_regression"])
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


def test_ac010_ac011_no_remaining(run):
    r = run(operation="remaining", features=POINTS[:1], completed_ids=["0"], gps=[127, 37], outcome="save")
    assert r["next_id"] is None
    assert r["submitted_ids"] == []
    assert r["message"].strip()
    assert r["saved_before"] == r["saved_after"]
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
    assert set(requests) == {"matrix", "optimizer", "directions"}
    expected = {"matrix": f"{routing_base}/v2/matrix/driving-car",
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
    assert r["warning_disclosures"] == {
        "plaintext_project": True, "folder_access_can_read_and_use": True,
        "not_encrypted": True, "qfield_automatic_use": True,
    }
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
