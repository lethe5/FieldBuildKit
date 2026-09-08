"""Bounded SHP previews must not materialize geometry or reload for name mapping."""

import shutil
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import fiona
import pytest
from PySide6.QtWidgets import QApplication

from qfield_builder import shapefile_reader, site_upload
from qfield_builder.build import build_project
from qfield_builder.ui import wizard
from qfield_builder.ui.map_canvas import MapCanvas
from qfield_builder.validate import validate_project


def _source(tmp_path, *, zipped=False, encoding="cp949", count=75, omit=()):
    folder = tmp_path / "source"
    folder.mkdir()
    shp = folder / "sites.shp"
    schema = {"geometry": "Polygon", "properties": {"NAME": "str", "ALT": "str"}}
    with fiona.open(shp, "w", driver="ESRI Shapefile", crs="EPSG:4326", encoding=encoding,
                    schema=schema) as dst:
        for i in range(count):
            dst.write({"geometry": {"type": "Polygon", "coordinates": [
                [(127, 37), (128, 37), (128, 38), (127, 37)]]},
                "properties": {"NAME": f"서울{i}", "ALT": f"대안{i}"}})
    for suffix in omit:
        shp.with_suffix(suffix).unlink()
    if not zipped:
        return "shapefile", str(shp)
    archive = tmp_path / "sites.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as dst:
        for source in folder.iterdir():
            dst.write(source, "nested/" + source.name)
    return "zipped_shapefile", str(archive)


@pytest.mark.parametrize("zipped", [False, True])
@pytest.mark.parametrize("encoding", ["cp949", "utf-8"])
def test_preview_matches_full_import_without_geometry(tmp_path, monkeypatch, zipped, encoding):
    fmt, path = _source(tmp_path, zipped=zipped, encoding=encoding)
    expected = site_upload.read_upload_features(fmt, path, encoding)
    def forbidden(*args, **kwargs):
        raise AssertionError("Preview must not decode coordinates or construct WKT")
    monkeypatch.setattr(shapefile_reader, "_read_shp", forbidden)
    monkeypatch.setattr(shapefile_reader, "shape_to_wkt", forbidden)
    summary = site_upload.preview_summary(fmt, path, encoding)
    assert summary["feature_count"] == 75
    assert summary["geometry_type"] == "POLYGON"
    assert summary["sample_attributes"] == [f.attributes for f in expected[:50]]
    assert site_upload.list_attribute_fields(fmt, path, encoding) == ["NAME", "ALT"]


@pytest.mark.parametrize("zipped", [False, True])
@pytest.mark.parametrize("omit", [(".dbf",), (".shx",), (".dbf", ".shx")])
def test_missing_optional_sidecars_keep_count_and_preview(tmp_path, zipped, omit):
    fmt, path = _source(tmp_path, zipped=zipped, omit=omit, count=3)
    summary = site_upload.preview_summary(fmt, path)
    assert summary["feature_count"] == 3
    assert len(summary["sample_attributes"]) == 3
    assert summary["fields"] == ([] if ".dbf" in omit else ["NAME", "ALT"])


def test_preview_reads_only_shp_header_and_bounded_dbf_rows(tmp_path, monkeypatch):
    fmt, path = _source(tmp_path)
    original_open = Path.open
    streams = {}
    def tracked(source, *args, **kwargs):
        handle = original_open(source, *args, **kwargs)
        if source.suffix in (".shp", ".dbf") and args == ("rb",):
            wrapped = MagicMock(wraps=handle)
            wrapped.__enter__.return_value = wrapped
            wrapped.__exit__.side_effect = handle.__exit__
            streams[source.suffix] = wrapped
            return wrapped
        return handle
    monkeypatch.setattr(Path, "open", tracked)
    site_upload.preview_summary(fmt, path)
    streams[".shp"].read.assert_called_once_with(100)
    sizes = [call.args[0] for call in streams[".dbf"].read.call_args_list]
    assert all(size > 0 for size in sizes)
    assert sum(sizes) < Path(path).with_suffix(".dbf").stat().st_size


def test_gui_reads_once_reuses_mapping_and_reloads_encoding_or_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _, path = _source(tmp_path, encoding="utf-8")
    monkeypatch.setattr(wizard, "MapCanvas", lambda: MapCanvas(
        tile_fetcher=lambda *_: b"", tile_cache_dir=str(tmp_path / "tiles")))
    original = site_upload.preview_summary
    calls = []
    def tracked(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(site_upload, "preview_summary", tracked)
    page = wizard.SiteInputPage()
    page.upload_path_edit.setText(path)
    assert len(calls) == 1
    assert page.preview_list.count() == 50
    assert "75" in page.upload_status_label.text()
    page.site_name_field_combo.setCurrentText("ALT")
    assert len(calls) == 1
    page.upload_encoding_combo.setCurrentIndex(1)
    assert len(calls) == 2
    page.site_name_field_combo.setCurrentText("ALT")
    assert "대안0" in page.preview_list.item(0).text()
    assert len(calls) == 2
    page.upload_path_edit.clear()
    assert page.preview_list.count() == 0
    page.upload_path_edit.setText(path)
    assert len(calls) == 3
    # A failed selection must not retain the previous upload's preview.
    page.upload_path_edit.setText(str(Path(path).with_name("missing.shp")))
    assert page.preview_list.count() == 0
    assert not page.site_name_field_combo.isEnabled()
    page.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("zipped", [False, True])
def test_preview_limit_does_not_limit_built_sites_and_project_relocates(tmp_path, zipped):
    fmt, path = _source(tmp_path, zipped=zipped)
    assert len(site_upload.preview_summary(fmt, path)["sample_attributes"]) == 50
    result = build_project({
        "project_display_name": "SHP import", "survey_type": "temporary_plots",
        "basemap": {"mode": "none"}, "identification_enabled": False,
        "sites_upload": {"format": fmt, "path": path, "encoding": "cp949",
                         "attribute_mapping": {"site_name": "NAME"}},
    }, str(tmp_path / "project"))
    assert result["success"], result.get("error_message")
    with sqlite3.connect(result["gpkg_path"]) as conn:
        rows = conn.execute("SELECT site_name, site_geom FROM site").fetchall()
    assert len(rows) == 75
    assert {row[0] for row in rows} == {f"서울{i}" for i in range(75)}
    assert all(bytes(row[1]).startswith(b"GP") for row in rows)
    moved = tmp_path / "relocated"
    shutil.copytree(result["project_dir"], moved)
    assert validate_project(str(moved))["success"]
