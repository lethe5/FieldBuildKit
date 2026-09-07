"""Regression test for the offline MBTiles basemap layer's CRS (stakeholder bug report:
"Offline basemap (MBTiles) 는 CRS가 3857이니까 이걸 설정해줘야해. 지금 설정이 안되어있어" -- the
offline basemap layer's CRS should be set to EPSG:3857, but wasn't).

Confirmed root cause: `qfield_builder.qgis_worker._add_offline_basemap_layer` constructed a
`QgsRasterLayer` for the generated `.mbtiles` file but never called `.setCrs(...)` on it, so the
layer was left to whatever (if anything) GDAL's own MBTiles driver auto-detects. MBTiles is a
fixed-CRS tile format -- every `.mbtiles` file is always EPSG:3857 (Web Mercator) per the format's
own spec -- so the fix sets this explicitly rather than relying on driver auto-detection.

This exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.mbtiles.build_mbtiles`
+ `qfield_builder.qgis_worker.build_qgis_project`) against a real, generated `.mbtiles` file and
inspects the actual generated `.qgs` XML's `<srs>`/`<spatialrefsys>` element for the offline
basemap `maplayer`, mirroring `test_qgis_worker_drag_and_drop_form.py`'s own convention (a fake/
mocked `pyqgis` dict cannot reproduce real GDAL MBTiles-driver CRS-detection behavior). Skipped
when no real, bridgeable QGIS/PyQGIS runtime is available, matching that same file's convention.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from qfield_builder import gpkg, mbtiles, naming, qgis_worker
from qfield_builder.runtime import check_runtime
from qfield_builder.vworld_tiles import make_fake_tile_fetcher

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

_SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}


def _build_offline_project(tmp_path: Path) -> ET.Element:
    survey_type = "simple_inventory"
    gpkg_path = tmp_path / f"{survey_type}.gpkg"
    qgs_path = tmp_path / f"{survey_type}.qgs"
    mbtiles_path = tmp_path / "basemap" / "offline.mbtiles"

    gpkg.build_geopackage(
        str(gpkg_path),
        survey_type,
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    mbtiles.build_mbtiles(
        str(mbtiles_path), _SMALL_BBOX, 10, 12, make_fake_tile_fetcher("success", 5000)
    )

    basemap_config = {
        "mode": "offline",
        "layer": "Base",
        "bbox": _SMALL_BBOX,
        "min_zoom": 10,
        "max_zoom": 12,
    }
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=survey_type,
        project_crs="EPSG:4326",
        basemap_config=basemap_config,
        mbtiles_relative_path="./basemap/offline.mbtiles",
        offline_source_identity={"provider": "VWorld", "layer": "Base"},
    )
    return ET.parse(str(qgs_path)).getroot()


def _offline_basemap_maplayer(root: ET.Element) -> ET.Element:
    for maplayer in root.iter("maplayer"):
        layername_el = maplayer.find("layername")
        if layername_el is not None and layername_el.text == "Offline basemap (MBTiles)":
            return maplayer
    raise AssertionError("expected a maplayer named 'Offline basemap (MBTiles)' in the .qgs XML")


def test_offline_basemap_layer_has_a_crs_set_at_all(tmp_path: Path):
    """Before the fix, the layer's CRS was left entirely unset -- confirm a real `<srs>` element
    with a genuinely valid, non-empty authid is now present, not merely absent-but-tolerated."""
    root = _build_offline_project(tmp_path)
    maplayer = _offline_basemap_maplayer(root)

    srs_el = maplayer.find("srs")
    assert srs_el is not None, "expected a <srs> element on the offline basemap maplayer"
    authid_el = srs_el.find("spatialrefsys/authid")
    assert authid_el is not None and authid_el.text, (
        "expected a non-empty <authid> under the offline basemap layer's <srs>/<spatialrefsys>"
    )


def test_offline_basemap_layer_crs_is_epsg_3857(tmp_path: Path):
    """The actual regression assertion: MBTiles is always Web Mercator -- the layer's CRS must be
    exactly EPSG:3857, not merely "some" valid CRS."""
    root = _build_offline_project(tmp_path)
    maplayer = _offline_basemap_maplayer(root)

    authid_el = maplayer.find("srs/spatialrefsys/authid")
    assert authid_el is not None
    assert authid_el.text == "EPSG:3857"
