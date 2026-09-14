"""APPROVED acceptance artifacts, approved specification checkpoint e382c77.

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
POINTS = [{"id": str(i), "name": f"조사지 {i}", "xy": [127 + i / 1000, 37]} for i in range(12)]
# Directed costs for depot,A,B,C. Time winner O-A-B-C-O = 4; distance O-C-B-A-O = 8.
TIME = [[0, 1, 20, 20], [20, 0, 1, 20], [20, 20, 0, 1], [1, 20, 20, 0]]
DISTANCE = [[0, 30, 30, 2], [2, 0, 30, 30], [30, 2, 0, 30], [30, 30, 2, 0]]
ROAD = {"type": "LineString", "coordinates": [[127, 37], [127.001, 37.003], [127.002, 37]]}


def ids(route):
    return [stop["site_id"] for stop in route["stops"]]


def no_calls(result):
    assert result["requests"] == []


def rejected(result):
    assert result["saved_before"], "scenario must seed a nonempty saved baseline"
    assert result["ok"] is False
    assert result["message"].strip()
    assert result["saved_after"] == result["saved_before"]


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
    if count == 0:
        rejected(r)
        no_calls(r)
    else:
        assert r["ok"] is True
        assert sorted(r["submitted_ids"]) == sorted(p["id"] for p in wanted)
        assert sorted(ids(r["candidate"])) == sorted(r["submitted_ids"])


@pytest.mark.parametrize("scope,expected", [("all", ["0", "1", "2"]), ("uncompleted", ["1", "2"])])
def test_ac003_scope_mapping(run, scope, expected):
    features = [{"custom_id": p["id"], "title": p["name"], "done": p["id"] == "0", "xy": p["xy"]} for p in POINTS[:3]]
    r = run(operation="calculate", scope=scope, features=features,
            mapping={"layer": "custom_targets", "id": "custom_id", "name": "title", "completed": "done"})
    assert sorted(r["submitted_ids"]) == expected
    assert {s["source_layer"] for s in r["candidate"]["stops"]} == {"custom_targets"}


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
    r = run(operation="road_cost", features=POINTS[:3], objective=objective,
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
    assert KEY not in r["logs"] and KEY not in str(r["saved_after"])
    assert r["active_after"] == r["active_before"]


@pytest.mark.parametrize("extras", [False, True])
def test_ac007_result_roundtrip(run, extras):
    supplied = {"distance_m": 1234.5, "duration_s": 456, "order": ["2", "0", "1"],
                "road_geometry": ROAD if extras else None,
                "eta": ["2026-09-14T01:00:00Z", "2026-09-14T01:02:00Z", "2026-09-14T01:04:00Z"] if extras else None,
                "legs": [{"distance_m": 100, "duration_s": 20}] * 4 if extras else None}
    r = run(operation="result_roundtrip", response=supplied)
    route = r["reloaded"]
    for field in ("route_id", "name", "backend", "status"):
        assert route[field]
    datetime.fromisoformat(route["created_at"].replace("Z", "+00:00"))
    assert route["distance_m"] == 1234.5 and route["duration_s"] == 456
    assert ids(route) == supplied["order"]
    assert [s["sequence"] for s in route["stops"]] == [1, 2, 3]
    for field in ("road_geometry", "eta", "legs"):
        assert route[field] == supplied[field]
        assert r["availability"][field] is extras


def test_ac008_offline_restart_relocation(run):
    r = run(operation="save_two_restart_move", offline=True, clear_session_key=True)
    assert len(r["saved_before"]) == 2
    assert len({v["route_id"] for v in r["saved_before"]}) == 2
    assert r["saved_after"] == r["saved_before"]
    assert r["active_after"] == r["active_before"]
    assert Path(r["old_dir"]).resolve() != Path(r["project_dir"]).resolve()
    assert r["selected_route_ids"] == [v["route_id"] for v in r["saved_before"]]
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
    r = run(operation="complete", features=POINTS[:8], completed_ids=["0", "2"], source=completion_source)
    assert r["completed_count"] == 2 and r["total_count"] == 8
    assert r["next_id"] == "1"
    assert {s["site_id"] for s in r["active"]["stops"] if s["completed"]} == {"0", "2"}
    assert r["summary_counts"] == [2, 8]
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
    assert KEY not in r["logs"]
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


@pytest.mark.parametrize("fault", ["mixed_families", "empty", "invalid_geometry", "unknown_crs"])
def test_ac015_ac017_invalid_geometry(run, fault):
    r = run(operation="geometry_failure", fault=fault)
    assert r["ok"] is False and r["message"].strip()
    assert r["published_features"] == []
    no_calls(r)


# Source-space centroids: line length-weighted (8/3,1/3), triangle area-weighted (2,1).
# MultiPolygon: areas 9 and 2, centroids (2,1) and (32/3,2/3).
CENTROIDS = {"Point": [0, 0], "LineString": [8 / 3, 1 / 3], "Polygon": [2, 1],
             "MultiPoint": [3, 3], "MultiLineString": [8 / 3, 1 / 3], "MultiPolygon": [118 / 33, 31 / 33]}


@pytest.mark.parametrize("crs", ["EPSG:4326", "EPSG:3857"])
@pytest.mark.parametrize("kind", GEOMETRIES)
def test_ac017_representatives_numerical(run, crs, kind):
    # Conditional proposal assertion: O-SRP-003 remains open, see design; not a silent policy decision.
    if kind != "Point" and (crs != "EPSG:4326" or kind == "MultiPoint"):
        if os.environ.get("FIELDBUILD_SRP_CENTROID_POLICY") != "source_crs_centroid":
            pytest.skip("O-SRP-003 candidate policy unresolved; opt-in characterization only")
    import math

    geom = GEOJSON[kind]
    expected = CENTROIDS[kind]
    if crs == "EPSG:3857":
        x, y = expected[0] * 100000 + 1000000, expected[1] * 100000 + 5000000
        expected = [math.degrees(x / 6378137), math.degrees(2 * math.atan(math.exp(y / 6378137)) - math.pi / 2)]
    r = run(operation="representative", wkt=fixture_wkt(geom, projected=crs == "EPSG:3857"), crs=crs,
            candidate_policy="source_crs_centroid")
    assert r["coordinate"] == pytest.approx(expected, abs=1e-7)
    assert r["original_after"] == r["original_before"]
    assert r["request_coordinate"] == pytest.approx(expected, abs=1e-7)


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


def test_ac013_backend_settings(run):
    settings = {"server_url": "https://routing.invalid/custom", "backend": "acceptance_backend",
                "profile": "car", "timeout_ms": 1250, "max_road_offset_m": 50, "key": KEY}
    r = run(operation="configured_calculate", settings=settings)
    assert r["effective_settings"] == settings
    assert r["requests"]
    assert KEY not in r["logs"] and KEY not in str(r["saved_after"])
