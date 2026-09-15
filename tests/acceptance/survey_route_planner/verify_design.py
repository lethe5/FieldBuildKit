"""DRAFT bd625d6 design-only fixture/oracle check; never executes application code."""
import ast
import importlib.util
import math
import re
import tempfile
from pathlib import Path

import fiona
from fiona.transform import transform

path = Path(__file__).with_name("test_survey_route_planner.py")
ast.parse(path.read_text(encoding="utf-8-sig"))
spec = importlib.util.spec_from_file_location("srp_test_design", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
coverage = set(re.findall(r"ac(\d{3})", path.read_text(encoding="utf-8-sig")))
assert {f"{i:03d}" for i in range(1, 21)} <= coverage
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
print("Design checks: syntax; 20 AC IDs; raw VROOM relative arrivals/no route.eta; 4 invalid timing fixtures; current/legacy endpoint constants; strict QfExpressionEvaluator surface and supported centroid/transform/x/y expression assertions; portable non-secret settings; 6 documented centroid fixtures; 6 Mercator controls; 1 EPSG:5186 control; 18 real upload fixtures verified. No application tests executed.")
