"""Generated projects open at survey scale instead of reprojecting a global basemap."""

import xml.etree.ElementTree as ET

import pytest
from rasterio.warp import transform

from qfield_builder import gpkg, schemas, template_project


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
@pytest.mark.parametrize("crs", ["EPSG:5186", "EPSG:3857", "EPSG:4326"])
def test_empty_project_opens_on_korea(tmp_path, survey_type, crs):
    data, project = tmp_path / "data.gpkg", tmp_path / "project.qgs"
    gpkg.build_geopackage(str(data), survey_type, "test")
    template_project.build_qgis_project(str(data), str(project), survey_type, crs, None)
    root = ET.parse(project)
    canvas = root.find("./mapcanvas[@name='theMapCanvas']")
    assert canvas is not None
    assert canvas.findtext("destinationsrs/spatialrefsys/authid") == crs
    values = {k: float(canvas.findtext("extent/" + k)) for k in ("xmin", "ymin", "xmax", "ymax")}
    # Seoul and Jeju must both be in the opening view, without a worldwide extent.
    xs, ys = transform("EPSG:4326", crs, [126.98, 126.53], [37.57, 33.5])
    assert all(values["xmin"] < x < values["xmax"] for x in xs)
    assert all(values["ymin"] < y < values["ymax"] for y in ys)
    assert values["xmax"] - values["xmin"] < (12 if crs == "EPSG:4326" else 1_500_000)
    for name in ("DefaultViewExtent", "PresetFullExtent"):
        extent = root.find("ProjectViewSettings/" + name)
        assert {k: float(v) for k, v in extent.attrib.items()} == values
        assert extent.findtext("spatialrefsys/authid") == crs


@pytest.mark.parametrize("point_only", [False, True])
def test_survey_geometry_sets_local_extent_in_project_crs(tmp_path, point_only):
    data, project = tmp_path / "data.gpkg", tmp_path / "project.qgs"
    gpkg.build_geopackage(
        str(data),
        "permanent_plots",
        "test",
        seed_sites=[
            {
                "site_name": "Test site",
                "geom_wkt": "MULTIPOLYGON(((127 37,127.01 37,127.01 37.01,127 37.01,127 37)))",
            }
        ],
        seed_plots=[{"plot_name": "Test plot", "geom_wkt": "POINT(127.005 37.005)"}],
    )
    if point_only:
        with gpkg._connect(str(data)) as conn:
            conn.execute("UPDATE site SET site_geom = NULL")
    template_project.build_qgis_project(
        str(data),
        str(project),
        "permanent_plots",
        "EPSG:5186",
        None,
    )
    root = ET.parse(project)
    extent = root.find("mapcanvas/extent")
    west, south, east, north = [float(extent.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")]
    xs, ys = transform("EPSG:4326", "EPSG:5186", [127.005], [37.005])
    assert west < xs[0] < east and south < ys[0] < north
    assert 100 < east - west < 2000 and 100 < north - south < 2000
