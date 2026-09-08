"""GPKG header-only extent reads and bounded preview-worker lifetimes."""

import shutil
import sqlite3
import threading
import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from rasterio.crs import CRS

from qfield_builder import gpkg_upload_reader as reader
from qfield_builder import site_upload
from qfield_builder.errors import BuildError
from qfield_builder.ui import wizard
from qfield_builder.ui.map_canvas import MapCanvas
from qfield_builder.wkt import Envelope, wkb_to_gpkg_blob, wkt_to_wkb


def _source(path, *, srs=4326, envelope=True):
    xy = (127, 37) if srs == 4326 else (200000, 600000)
    x, y = xy
    wkb = wkt_to_wkb(f"POLYGON(({x} {y},{x+1} {y},{x+1} {y+1},{x} {y}))", "MULTIPOLYGON")
    bounds = Envelope(x, x+1, y, y+1) if envelope else None
    blob = wkb_to_gpkg_blob(wkb, srs, bounds)
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE gpkg_contents(table_name TEXT, data_type TEXT);
            CREATE TABLE gpkg_geometry_columns(table_name TEXT, column_name TEXT,
                geometry_type_name TEXT, srs_id INTEGER);
            CREATE TABLE gpkg_spatial_ref_sys(srs_id INTEGER, organization TEXT,
                organization_coordsys_id INTEGER, definition TEXT);
            CREATE TABLE sites(fid INTEGER PRIMARY KEY, name TEXT, geom BLOB);
            INSERT INTO gpkg_contents VALUES('sites','features');
        """)
        conn.execute("INSERT INTO gpkg_geometry_columns VALUES('sites','geom','POLYGON',?)", (srs,))
        conn.execute("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?)",
                     (srs, "EPSG", srs, CRS.from_epsg(srs).to_wkt()))
        conn.execute("INSERT INTO sites VALUES(1,'서울',?)", (blob,))
    return str(path)


def test_open_is_read_only_and_missing_path_is_not_created(tmp_path):
    missing = tmp_path / "missing.gpkg"
    with pytest.raises(BuildError):
        reader.preview_first_feature_layer(str(missing))
    assert not missing.exists()
    path = _source(tmp_path / "경계 # &.gpkg")
    conn = reader._open(path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("CREATE TABLE forbidden(x)")
    finally:
        conn.close()


@pytest.mark.parametrize("srs", [4326, 5186])
def test_extent_uses_header_not_full_geometry_and_returns_lonlat(tmp_path, monkeypatch, srs):
    path = _source(tmp_path / "boundary.gpkg", srs=srs)
    def forbidden(*args):
        raise AssertionError("Header extent must not decode full geometry")
    monkeypatch.setattr(reader, "wkb_to_multipolygon_wkb", forbidden)
    result = site_upload.read_upload_envelope("gpkg", path)
    assert 126.9 < result["min_lon"] < result["max_lon"] < 129
    assert 36 < result["min_lat"] < result["max_lat"] < 39
    if srs == 4326:
        assert result == {"min_lon": 127, "min_lat": 37, "max_lon": 128, "max_lat": 38}


def test_extent_without_header_envelope_uses_geometry_fallback(tmp_path):
    path = _source(tmp_path / "boundary.gpkg", envelope=False)
    assert reader.read_feature_layer_envelope(path) == {
        "min_lon": 127, "min_lat": 37, "max_lon": 128, "max_lat": 38}


@pytest.mark.parametrize("damage", ["header", "bounds", "crs", "empty"])
def test_invalid_extent_is_reported(tmp_path, damage):
    path = _source(tmp_path / "invalid.gpkg", srs=5186)
    with sqlite3.connect(path) as conn:
        if damage == "header":
            conn.execute("UPDATE sites SET geom = X'4750'")
        elif damage == "bounds":
            import struct
            blob = bytearray(conn.execute("SELECT geom FROM sites").fetchone()[0])
            struct.pack_into("<d", blob, 8, float("inf"))
            conn.execute("UPDATE sites SET geom = ?", (blob,))
        elif damage == "crs":
            conn.execute("DELETE FROM gpkg_spatial_ref_sys")
        else:
            conn.execute("DELETE FROM sites")
    with pytest.raises(BuildError):
        reader.read_feature_layer_envelope(path)


def test_preview_limit_does_not_limit_gpkg_build_and_relocation(tmp_path):
    from qfield_builder.build import build_project
    from qfield_builder.validate import validate_project

    path = _source(tmp_path / "sites.gpkg")
    with sqlite3.connect(path) as conn:
        blob = conn.execute("SELECT geom FROM sites").fetchone()[0]
        conn.executemany("INSERT INTO sites VALUES(?,?,?)", [
            (i, f"서울{i}", blob) for i in range(2, 76)])
    preview = reader.preview_first_feature_layer(path)
    assert preview["feature_count"] == 75
    assert len(preview["sample_attributes"]) == 50
    result = build_project({
        "project_display_name": "GPKG preview",
        "survey_type": "temporary_plots", "identification_enabled": False,
        "sites_upload": {"format": "gpkg", "path": path,
                         "attribute_mapping": {"site_name": "name"}},
    }, str(tmp_path / "output"))
    assert result["success"], result
    moved = tmp_path / "relocated"
    shutil.move(result["project_dir"], moved)
    assert validate_project(str(moved))["success"]
    with sqlite3.connect(next((moved / "data").glob("*.gpkg"))) as conn:
        assert conn.execute("SELECT count(*) FROM site").fetchone()[0] == 75
    conn.close()


def _wait(predicate):
    end = time.monotonic() + 5
    while not predicate() and time.monotonic() < end:
        QTest.qWait(10)
    assert predicate()


@pytest.fixture
def gui(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(wizard, "MapCanvas", lambda: MapCanvas(
        tile_fetcher=lambda *_: b"", tile_cache_dir=str(tmp_path / "tiles")))
    yield app
    app.processEvents()


def _summary(name):
    return {"fields": ["name"], "geometry_type": "POLYGON", "feature_count": 1,
            "sample_attributes": [{"name": name}]}


def test_rapid_reselection_coalesces_work_and_ignores_same_path_old_result(gui, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    calls = []
    def preview(fmt, path):
        calls.append(path)
        if len(calls) == 1:
            entered.set()
            assert release.wait(4)
            return _summary("OLD")
        return _summary("NEW")
    monkeypatch.setattr(site_upload, "preview_summary", preview)
    page = wizard.SiteInputPage()
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    try:
        page.upload_path_edit.setText("a.gpkg")
        _wait(entered.is_set)
        page.upload_path_edit.setText("b.gpkg")
        page.upload_path_edit.setText("a.gpkg")
        QTest.qWait(50)
        assert calls == ["a.gpkg"] and ticks
        release.set()
        _wait(lambda: page._gpkg_preview_worker is None)
        assert calls == ["a.gpkg", "a.gpkg"]
        assert "NEW" in page.preview_list.item(0).text()
        page._update_preview()
        assert len(calls) == 2
        page.upload_path_edit.clear()
        assert page.preview_list.count() == 0
    finally:
        release.set()
        _wait(lambda: page._gpkg_preview_worker is None)
        timer.stop()
        page.deleteLater()


def test_wizard_close_waits_for_active_preview_and_discards_queue(gui, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def preview(*args):
        entered.set()
        assert release.wait(4)
        return _summary("old")
    monkeypatch.setattr(site_upload, "preview_summary", preview)
    window = wizard.ProjectBuilderWizard()
    page = window.page(2)
    finished = []
    window.finished.connect(finished.append)
    try:
        page.upload_path_edit.setText("a.gpkg")
        _wait(entered.is_set)
        page.upload_path_edit.setText("b.gpkg")
        window.done(0)
        assert not finished
        release.set()
        _wait(lambda: bool(finished))
        assert page._gpkg_preview_worker is None
        assert page._gpkg_preview_pending is None
    finally:
        release.set()
        _wait(lambda: page._gpkg_preview_worker is None)
        window.deleteLater()
