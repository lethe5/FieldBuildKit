from __future__ import annotations

import sqlite3
import struct
import zipfile

import pytest

from qfield_builder import build, gpkg, gpkg_upload_reader
from qfield_builder.site_upload import UploadFeature
from qfield_builder.wkt import Envelope


def _square_wkb() -> bytes:
    ring = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    return (
        struct.pack("<BI", 1, 3)
        + struct.pack("<I", 1)
        + struct.pack("<I", len(ring))
        + b"".join(struct.pack("<dd", x, y) for x, y in ring)
    )


def test_gpkg_upload_preview_never_selects_or_decodes_geometry_blobs(tmp_path):
    """Choosing a large site GeoPackage remains a metadata operation, not a geometry import."""
    source = tmp_path / "large-site.gpkg"
    conn = sqlite3.connect(source)
    try:
        conn.executescript(
            """
            CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT);
            CREATE TABLE gpkg_geometry_columns (
                table_name TEXT, column_name TEXT, geometry_type_name TEXT,
                srs_id INTEGER, z TINYINT, m TINYINT
            );
            CREATE TABLE sites (fid INTEGER PRIMARY KEY, name TEXT, geom BLOB);
            INSERT INTO gpkg_contents VALUES ('sites', 'features');
            INSERT INTO gpkg_geometry_columns VALUES ('sites', 'geom', 'MULTIPOLYGON', 4326, 0, 0);
            INSERT INTO sites VALUES (1, '첫 조사지', X'00010203');
            INSERT INTO sites VALUES (2, '둘째 조사지', X'00010203');
            """
        )
        conn.commit()
    finally:
        conn.close()

    preview = gpkg_upload_reader.preview_first_feature_layer(str(source), max_rows=1)

    assert preview == {
        "fields": ["name"],
        "geometry_type": "MULTIPOLYGON",
        "feature_count": 2,
        "sample_attributes": [{"name": "첫 조사지"}],
    }


def test_uploaded_gpkg_sites_keep_binary_geometry(monkeypatch):
    raw = _square_wkb()
    monkeypatch.setattr(
        build.gpkg_upload_reader,
        "first_feature_layer_info",
        lambda _path: {"table_name": "boundaries", "srs_id": 4326},
    )
    monkeypatch.setattr(
        build.gpkg_upload_reader,
        "read_first_feature_layer_raw",
        lambda _path: [
            {
                "attributes": {"name": "경계"},
                "geom_wkb": raw,
                "envelope": Envelope(0, 1, 0, 1),
                "geometry_type": "POLYGON",
            }
        ],
    )
    monkeypatch.setattr(
        build.site_upload,
        "read_upload_features",
        lambda *_args: (_ for _ in ()).throw(AssertionError("WKT 경로가 호출되면 안 됩니다")),
    )

    sites = build._resolve_sites_from_upload(
        {
            "format": "gpkg",
            "path": "large-boundary.gpkg",
            "attribute_mapping": {"site_name": "name"},
        }
    )

    assert sites == [
        {
            "site_name": "경계",
            "geom_wkb": raw,
            "geom_envelope": Envelope(0, 1, 0, 1),
        }
    ]


def test_uploaded_shapefile_features_use_upload_feature_attributes(monkeypatch):
    monkeypatch.setattr(build.site_upload, "shapefile_has_prj", lambda *_args: False)
    monkeypatch.setattr(
        build.site_upload,
        "read_upload_features",
        lambda *_args: [
            UploadFeature(
                attributes={"name": "경계"},
                geom_wkt="MULTIPOLYGON(((127 37, 127.01 37, 127.01 37.01, 127 37.01, 127 37)))",
            )
        ],
    )

    sites = build._resolve_sites_from_upload(
        {
            "format": "shapefile",
            "path": "boundary.shp",
            "attribute_mapping": {"site_name": "name"},
            "source_crs": "EPSG:4326",
        }
    )

    assert sites == [
        {
            "site_name": "경계",
            "geom_wkt": "MULTIPOLYGON(((127 37, 127.01 37, 127.01 37.01, 127 37.01, 127 37)))",
        }
    ]


def test_uploaded_shapefile_without_prj_requires_source_crs(monkeypatch):
    monkeypatch.setattr(build.site_upload, "shapefile_has_prj", lambda *_args: False)

    with pytest.raises(build.BuildError, match="EPSG 코드"):
        build._resolve_sites_from_upload(
            {
                "format": "shapefile",
                "path": "boundary.shp",
                "attribute_mapping": {"site_name": "name"},
            }
        )


def test_uploaded_shapefile_reprojects_when_source_crs_differs(monkeypatch, tmp_path):
    source = tmp_path / "boundary.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("boundary.shp", b"not-read-by-mocked-qgis")
        archive.writestr("boundary.dbf", b"not-read-by-mocked-qgis")

    transformed = tmp_path / "reprojected_shapefile_upload.gpkg"
    calls = []
    monkeypatch.setattr(build.site_upload, "shapefile_has_prj", lambda *_args: False)

    def reproject(**kwargs):
        calls.append(kwargs)
        return {"path": str(transformed), "layer_name": "reprojected_upload"}

    monkeypatch.setattr(build.qgis_worker, "reproject_uploaded_shapefile", reproject)
    monkeypatch.setattr(
        build.gpkg_upload_reader,
        "read_first_feature_layer_raw",
        lambda path: [
            {
                "attributes": {"name": "경계"},
                "geom_wkb": _square_wkb(),
                "envelope": Envelope(126, 127, 37, 38),
                "geometry_type": "POLYGON",
            }
        ],
    )

    sites = build._resolve_sites_from_upload(
        {
            "format": "zipped_shapefile",
            "path": str(source),
            "attribute_mapping": {"site_name": "name"},
            "source_crs": "5186",
        },
        storage_crs="EPSG:4326",
        work_dir=tmp_path,
    )

    assert calls[0]["source_crs"] == "EPSG:5186"
    assert calls[0]["target_crs"] == "EPSG:4326"
    assert calls[0]["source_path"].endswith("uploaded.shp")
    assert sites[0]["site_name"] == "경계"


def test_uploaded_gpkg_sites_reproject_when_source_crs_differs(monkeypatch, tmp_path):
    source = "boundary.gpkg"
    transformed = tmp_path / "reprojected_upload.gpkg"
    calls = []
    monkeypatch.setattr(
        build.gpkg_upload_reader,
        "first_feature_layer_info",
        lambda _path: {"table_name": "boundaries", "srs_id": 5186},
    )

    def reproject(**kwargs):
        calls.append(kwargs)
        return {"path": str(transformed), "layer_name": "reprojected_upload"}

    monkeypatch.setattr(build.qgis_worker, "reproject_uploaded_gpkg_layer", reproject)
    monkeypatch.setattr(
        build.gpkg_upload_reader,
        "read_first_feature_layer_raw",
        lambda path: (
            []
            if path == source
            else [
                {
                    "attributes": {"name": "경계"},
                    "geom_wkb": _square_wkb(),
                    "envelope": Envelope(126, 127, 37, 38),
                    "geometry_type": "MULTIPOLYGON",
                }
            ]
        ),
    )

    sites = build._resolve_sites_from_upload(
        {
            "format": "gpkg",
            "path": source,
            "attribute_mapping": {"site_name": "name"},
        },
        storage_crs="EPSG:4326",
        work_dir=tmp_path,
    )

    assert calls == [
        {
            "source_path": source,
            "source_layer_name": "boundaries",
            "destination_path": str(transformed),
            "target_crs": "EPSG:4326",
        }
    ]
    assert sites[0]["site_name"] == "경계"
    assert sites[0]["geom_wkb"] == _square_wkb()


def test_binary_site_seed_does_not_round_trip_through_wkt(tmp_path, monkeypatch):
    raw = _square_wkb()
    monkeypatch.setattr(
        gpkg,
        "wkt_to_gpkg_geometry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("대형 GPKG geometry는 WKT 재파싱을 하면 안 됩니다")
        ),
    )

    out = tmp_path / "project.gpkg"
    gpkg.build_geopackage(
        str(out),
        "simple_inventory",
        "p1",
        seed_sites=[
            {
                "site_name": "경계",
                "geom_wkb": raw,
                "geom_envelope": Envelope(0, 1, 0, 1),
            }
        ],
    )

    assert out.exists()
