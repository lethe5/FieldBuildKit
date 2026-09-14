"""APPROVED design-only fixture/oracle check; never executes application code."""
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
assert {f"{i:03d}" for i in range(1, 19)} <= coverage
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
print("Design checks: syntax; 18 AC IDs; 6 documented centroid fixtures; 6 Mercator controls; 1 EPSG:5186 control; 18 real upload fixtures verified. No application tests executed.")
