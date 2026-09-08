"""Shared site/plot upload reading (Section 7.4, FR-QPB-025/030/031).

A single place that knows how to read a site/plot upload file (a standalone or zipped Shapefile or a
GeoPackage) into a uniform, source-format-agnostic shape: raw source attributes plus a WKT
geometry. Both the build pipeline (:mod:`qfield_builder.build`, which actually writes the
imported features into the generated GeoPackage) and the wizard UI (which needs to populate an
attribute-mapping combo box and show an import preview, per FR-QPB-030/031, *before* a build is
ever started) call into this module, so the preview the user sees is guaranteed to reflect
exactly what the build will import -- not a separate, potentially-drifting re-implementation.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import gpkg_upload_reader, shapefile_reader
from .errors import BuildError
from .wkt import envelope_of

# Maps a recognized upload file extension to the `sites_upload.format` value the build pipeline
# understands (see tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md).
EXTENSION_TO_FORMAT = {
    ".zip": "zipped_shapefile",
    ".shp": "shapefile",
    ".gpkg": "gpkg",
}


@dataclass(frozen=True)
class UploadFeature:
    attributes: dict
    geom_wkt: str


def infer_format(path: str) -> str | None:
    """Infer a `sites_upload.format` value from a file path's extension, or None if unrecognized."""
    return EXTENSION_TO_FORMAT.get(Path(path).suffix.lower())


def normalize_epsg_code(value: str | int | None) -> str:
    """Normalize a user-supplied EPSG code to ``EPSG:<number>``.

    This intentionally validates the input shape here, while QGIS performs the authoritative
    validation that the numeric code actually exists when a reprojection is needed.
    """
    text = str(value or "").strip().upper()
    if text.startswith("EPSG:"):
        text = text[5:].strip()
    if not text.isdigit() or not (0 < int(text) <= 999999):
        raise BuildError(
            "invalid_upload_crs",
            "SHP 원본 좌표계는 EPSG 코드로 입력해야 합니다(예: 5186 또는 EPSG:5186).",
        )
    return f"EPSG:{int(text)}"


def shapefile_has_prj(fmt: str, path: str) -> bool:
    """Return whether a standalone or zipped Shapefile has its companion ``.prj`` file."""
    if fmt == "shapefile":
        source = Path(path)
        try:
            return any(
                candidate.stem.lower() == source.stem.lower()
                and candidate.suffix.lower() == ".prj"
                for candidate in source.parent.iterdir()
            )
        except OSError as exc:
            raise BuildError("malformed_upload", f"SHP 파일을 확인할 수 없었습니다: {exc}") from exc
    if fmt != "zipped_shapefile":
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuildError(
            "malformed_upload", "업로드한 파일이 올바른 zip 압축 파일이 아닙니다."
        ) from exc

    shp_name = next((name for name in names if name.lower().endswith(".shp")), None)
    if shp_name is None:
        return False
    shp_stem = Path(shp_name).stem.lower()
    return any(
        Path(name).stem.lower() == shp_stem and Path(name).suffix.lower() == ".prj"
        for name in names
    )


def read_upload_features(
    fmt: str, path: str, encoding: str = "cp949"
) -> list[UploadFeature]:
    """Read every feature; ``encoding`` applies to Shapefile DBF attributes."""
    if fmt == "zipped_shapefile":
        shapes = shapefile_reader.read_zipped_shapefile(path, encoding)
        features = []
        for shape in shapes:
            wkt = shapefile_reader.shape_to_wkt(shape, "MULTIPOLYGON")
            features.append(UploadFeature(attributes=dict(shape.attributes), geom_wkt=wkt))
        return features
    if fmt == "shapefile":
        shapes = shapefile_reader.read_shapefile(path, encoding)
        features = []
        for shape in shapes:
            wkt = shapefile_reader.shape_to_wkt(shape, "MULTIPOLYGON")
            features.append(UploadFeature(attributes=dict(shape.attributes), geom_wkt=wkt))
        return features
    if fmt == "gpkg":
        records = gpkg_upload_reader.read_first_feature_layer(path)
        return [
            UploadFeature(attributes=dict(record["attributes"]), geom_wkt=record["geom_wkt"])
            for record in records
        ]
    raise BuildError("unsupported_upload_format", f"지원되지 않는 업로드 형식입니다: {fmt!r}")


def list_attribute_fields(fmt: str, path: str, encoding: str = "cp949") -> list[str]:
    """The source attribute field names available for FR-QPB-030's attribute-mapping step.

    Reads the file's first feature layer to discover the fields actually present. Returns an
    empty list if the upload has no features (nothing to map, and nothing to preview).
    """
    if fmt == "gpkg":
        # Field names are available directly from the schema, even for an empty layer.
        return gpkg_upload_reader.list_feature_layer_fields(path)
    if fmt in ("shapefile", "zipped_shapefile"):
        return preview_summary(fmt, path, encoding, max_rows=1)["fields"]
    features = read_upload_features(fmt, path, encoding)
    if not features:
        return []
    return list(features[0].attributes.keys())


def read_upload_envelope(fmt: str, path: str, encoding: str = "cp949") -> dict:
    """FR-QPB-080: the overall bounding envelope of every Polygon/MultiPolygon feature in an
    uploaded GeoPackage or Shapefile (standalone or zipped), for use as an offline-basemap bbox
    source (an alternative to drawing the bbox directly on the map -- see
    :mod:`qfield_builder.ui.map_canvas`).

    Returns ``{"min_lon", "min_lat", "max_lon", "max_lat"}`` covering every feature in the file.
    Raises :class:`BuildError` if the file has no features, and
    :class:`qfield_builder.wkt.InvalidGeometryError` if a feature's geometry is not a Polygon or
    MultiPolygon (this offline-extent source only supports those two types, per FR-QPB-080).
    """
    if fmt == "gpkg":
        return gpkg_upload_reader.read_feature_layer_envelope(path)
    features = read_upload_features(fmt, path, encoding)
    if not features:
        raise BuildError(
            "empty_upload", "이 파일에는 범위를 계산할 feature가 없습니다."
        )
    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")
    for feature in features:
        envelope = envelope_of(feature.geom_wkt, "MULTIPOLYGON")
        min_lon = min(min_lon, envelope.min_x)
        max_lon = max(max_lon, envelope.max_x)
        min_lat = min(min_lat, envelope.min_y)
        max_lat = max(max_lat, envelope.max_y)
    return {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat}


def preview_features(
    fmt: str, path: str, site_name_field: str | None, encoding: str = "cp949"
) -> list[dict]:
    """FR-QPB-031: a preview of what will actually be imported, given the chosen attribute mapping.

    Returns ``[{"site_name": str, "geometry_type": str}, ...]`` -- one row per source feature.
    """
    if fmt == "gpkg":
        raw_features = gpkg_upload_reader.read_first_feature_layer_raw(path)
        return [
            {
                "site_name": (
                    feature["attributes"].get(site_name_field) if site_name_field else None
                )
                or "가져온 사이트",
                "geometry_type": feature["geometry_type"],
            }
            for feature in raw_features
        ]
    features = read_upload_features(fmt, path, encoding)
    preview = []
    for feature in features:
        name = feature.attributes.get(site_name_field) if site_name_field else None
        geometry_type = feature.geom_wkt.split("(", 1)[0].strip()
        preview.append({"site_name": name or "가져온 사이트", "geometry_type": geometry_type})
    return preview


def preview_summary(
    fmt: str, path: str, encoding: str = "cp949", *, max_rows: int = 50
) -> dict:
    """Read the metadata/attribute sample needed by the upload page, without geometry decoding.

    The returned attributes are intentionally not converted into names here.  The GUI can map
    them immediately when a different name field is selected, without reopening the upload.
    """
    if fmt == "gpkg":
        return gpkg_upload_reader.preview_first_feature_layer(path, max_rows=max_rows)

    if fmt in ("shapefile", "zipped_shapefile"):
        return shapefile_reader.preview_shapefile(
            path, encoding, zipped=fmt == "zipped_shapefile", max_rows=max_rows
        )

    features = read_upload_features(fmt, path, encoding)
    rows = features[:max_rows]
    return {
        "fields": list(rows[0].attributes.keys()) if rows else [],
        "geometry_type": None,
        "feature_count": len(features),
        "sample_attributes": [dict(feature.attributes) for feature in rows],
        "sample_geometry_types": [
            feature.geom_wkt.split("(", 1)[0].strip() for feature in rows
        ],
    }
