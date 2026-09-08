"""Reads an externally-supplied GeoPackage's first feature layer for site/plot uploads.

FR-QPB-025 allows uploading "a GeoPackage layer" for site/plot input, in addition to a zipped
Shapefile (see :mod:`qfield_builder.shapefile_reader`). This module opens an arbitrary
user-supplied ``.gpkg`` file (not one this application necessarily created itself) via plain
:mod:`sqlite3` -- consistent with this codebase's GDAL-free approach elsewhere (:mod:`qfield_
builder.gpkg`, :mod:`qfield_builder.shapefile_reader`) -- and reads back the geometry and
attributes of the first vector ("features") layer it contains, converting the file's GeoPackage-
header-wrapped WKB geometries back to WKT via :mod:`qfield_builder.wkt`.

This is intentionally minimal: exactly one feature layer is read (the first one listed in
``gpkg_contents``, ordered by table name for determinism); if an uploaded GeoPackage genuinely
has more than one feature layer, only the first is imported. Geometry types supported are those
:func:`qfield_builder.wkt.wkb_to_wkt` already knows how to round-trip: POINT, POLYGON,
MULTIPOLYGON (2D only, no Z/M) -- sufficient for the site (Polygon/MultiPolygon) and plot (Point)
uploads FR-QPB-025/026 require.
"""
from __future__ import annotations

import math
import sqlite3
import struct
from pathlib import Path

from .errors import BuildError
from .gpkg_functions import _wkb_envelope, envelope_from_gpkg_blob, strip_gpkg_geometry_header
from .wkt import (
    WKB_MULTIPOLYGON,
    WKB_POLYGON,
    _reject_if_z_or_m,
    _wkb_type_info,
    wkb_to_multipolygon_wkb,
    wkb_to_wkt,
)


def _open(gpkg_path: str) -> sqlite3.Connection:
    conn = None
    try:
        conn = sqlite3.connect(Path(gpkg_path).resolve().as_uri() + "?mode=ro", uri=True)
        # Force a real read so a non-SQLite file fails fast, inside this function's own
        # error handling, rather than surfacing an unguarded sqlite3.DatabaseError later.
        conn.execute("PRAGMA schema_version;")
    except sqlite3.Error as exc:
        if conn is not None:
            conn.close()
        raise BuildError(
            "malformed_upload", f"업로드한 GeoPackage를 열 수 없었습니다: {exc}"
        ) from exc
    return conn


def read_feature_layer_envelope(gpkg_path: str) -> dict:
    """Read per-feature header extents, then convert the union to WGS84 for map selection.

    This is an extent preview, not a substitute for full build-time geometry validation.
    Only envelope-less or collection geometries need the existing complete decoder.
    """
    from rasterio.crs import CRS
    from rasterio.errors import RasterioError
    from rasterio.warp import transform_bounds

    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        geom = _geometry_column(conn, table)
        qt = '"' + table.replace('"', '""') + '"'
        qg = '"' + geom.replace('"', '""') + '"'
        srs_id = conn.execute(
            "SELECT srs_id FROM gpkg_geometry_columns WHERE table_name = ?", (table,)
        ).fetchone()[0]
        if srs_id == 4326:
            crs = CRS.from_epsg(4326)
        else:
            srs = conn.execute(
                "SELECT organization, organization_coordsys_id, definition "
                "FROM gpkg_spatial_ref_sys WHERE srs_id = ?", (srs_id,)
            ).fetchone()
            if not srs:
                raise ValueError("원본 좌표계를 확인할 수 없습니다.")
            crs = (CRS.from_epsg(int(srs[1])) if str(srs[0]).upper() == "EPSG"
                   else CRS.from_wkt(srs[2]))
        bounds = None
        for rowid, prefix in conn.execute(
            f"SELECT rowid, substr({qg}, 1, 77) FROM {qt} WHERE {qg} IS NOT NULL"
        ):
            if len(prefix) < 8 or prefix[:2] != b"GP":
                raise ValueError("GeoPackage geometry 헤더가 올바르지 않습니다.")
            envelope_type = (prefix[3] >> 1) & 7
            if envelope_type not in range(5):
                raise ValueError("GeoPackage envelope 유형이 올바르지 않습니다.")
            wkb_header = strip_gpkg_geometry_header(prefix)
            if len(wkb_header) < 5 or wkb_header[0] not in (0, 1):
                raise ValueError("WKB geometry 헤더가 잘렸거나 올바르지 않습니다.")
            raw_type = struct.unpack_from("<I" if wkb_header[0] else ">I", wkb_header, 1)[0]
            base_type, _, _ = _wkb_type_info(raw_type)
            if envelope_type and base_type in (WKB_POLYGON, WKB_MULTIPOLYGON):
                envelope = envelope_from_gpkg_blob(prefix)
            else:
                blob = conn.execute(
                    f"SELECT {qg} FROM {qt} WHERE rowid = ?", (rowid,)
                ).fetchone()[0]
                normalized = wkb_to_multipolygon_wkb(strip_gpkg_geometry_header(blob))
                envelope = _wkb_envelope(normalized)
            if envelope is None:
                continue
            values = (envelope.min_x, envelope.min_y, envelope.max_x, envelope.max_y)
            if (not all(math.isfinite(v) for v in values)
                    or values[0] > values[2] or values[1] > values[3]):
                raise ValueError("도형 범위 값이 올바르지 않습니다.")
            bounds = values if bounds is None else (
                min(bounds[0], values[0]), min(bounds[1], values[1]),
                max(bounds[2], values[2]), max(bounds[3], values[3]),
            )
        if bounds is None:
            raise BuildError("empty_upload", "이 파일에는 범위를 계산할 feature가 없습니다.")
        west, south, east, north = transform_bounds(crs, "EPSG:4326", *bounds)
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError("경위도로 변환한 도형 범위가 올바르지 않습니다.")
        return {"min_lon": west, "min_lat": south, "max_lon": east, "max_lat": north}
    except (sqlite3.Error, ValueError, struct.error, RasterioError) as exc:
        raise BuildError("malformed_upload", f"GeoPackage 범위를 읽을 수 없습니다: {exc}") from exc
    finally:
        conn.close()


def _first_feature_table(conn: sqlite3.Connection) -> str:
    try:
        row = conn.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type = 'features' "
            "ORDER BY table_name LIMIT 1;"
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise BuildError(
            "malformed_upload", f"올바른 GeoPackage가 아닙니다 (gpkg_contents 누락): {exc}"
        ) from exc
    if row is None:
        raise BuildError(
            "malformed_upload", "업로드한 GeoPackage에 feature 레이어가 없습니다."
        )
    return row[0]


def _geometry_column(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute(
        "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?;", (table,)
    ).fetchone()
    if row is None:
        raise BuildError(
            "malformed_upload",
            f"GeoPackage 테이블 '{table}'에 등록된 geometry 컬럼이 없습니다.",
        )
    return row[0]


def first_feature_layer_info(gpkg_path: str) -> dict:
    """Return the first feature layer's table name and declared GeoPackage SRS ID.

    The build pipeline uses this metadata to detect when an uploaded layer needs to be
    transformed into the generated project's storage CRS before its geometry is copied.
    """
    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        row = conn.execute(
            "SELECT srs_id FROM gpkg_geometry_columns WHERE table_name = ?;", (table,)
        ).fetchone()
        if row is None:
            raise BuildError(
                "malformed_upload",
                f"GeoPackage 테이블 '{table}'에 등록된 geometry 컬럼이 없습니다.",
            )
        return {"table_name": table, "srs_id": int(row[0])}
    finally:
        conn.close()


def _attribute_columns(conn: sqlite3.Connection, table: str, geom_col: str) -> list[str]:
    cols = [row[1] for row in conn.execute(f'PRAGMA table_info("{table}");').fetchall()]
    return [c for c in cols if c not in ("fid", geom_col)]


def list_feature_layer_fields(gpkg_path: str) -> list[str]:
    """Return the first feature layer's non-geometry attribute column names."""
    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        geom_col = _geometry_column(conn, table)
        return _attribute_columns(conn, table, geom_col)
    finally:
        conn.close()


def preview_first_feature_layer(
    gpkg_path: str, *, max_rows: int = 50
) -> dict:
    """Return a bounded, geometry-free preview of the first feature layer.

    Selecting an upload in the wizard must not decode every geometry merely to fill a
    name-field combo box.  In particular, a single administrative-boundary polygon
    can contain millions of vertices.  This helper deliberately never selects the
    geometry BLOB: it returns the declared GeoPackage geometry type, the count of
    non-null geometry records, and at most ``max_rows`` attribute dictionaries.

    Full geometry decoding remains the build pipeline's responsibility, after the
    user has explicitly clicked ``생성``.
    """
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1")

    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        geom_col = _geometry_column(conn, table)
        attr_cols = _attribute_columns(conn, table, geom_col)
        geometry_row = conn.execute(
            "SELECT geometry_type_name FROM gpkg_geometry_columns WHERE table_name = ?;",
            (table,),
        ).fetchone()
        geometry_type = str(geometry_row[0] if geometry_row and geometry_row[0] else "GEOMETRY")
        try:
            total = conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{geom_col}" IS NOT NULL;'
            ).fetchone()[0]
            select_cols = ", ".join(f'"{column}"' for column in attr_cols)
            if select_cols:
                rows = conn.execute(
                    f'SELECT {select_cols} FROM "{table}" '
                    f'WHERE "{geom_col}" IS NOT NULL LIMIT ?;',
                    (max_rows,),
                ).fetchall()
                samples = [dict(zip(attr_cols, row, strict=False)) for row in rows]
            else:
                rows = conn.execute(
                    f'SELECT 1 FROM "{table}" WHERE "{geom_col}" IS NOT NULL LIMIT ?;',
                    (max_rows,),
                ).fetchall()
                samples = [{} for _ in rows]
        except sqlite3.DatabaseError as exc:
            raise BuildError(
                "malformed_upload", f"GeoPackage 테이블 '{table}'을(를) 읽을 수 없었습니다: {exc}"
            ) from exc
        return {
            "fields": attr_cols,
            "geometry_type": geometry_type,
            "feature_count": int(total),
            "sample_attributes": samples,
        }
    finally:
        conn.close()


def read_first_feature_layer(gpkg_path: str) -> list[dict]:
    """Read the first feature layer's rows.

    Returns ``[{"attributes": {col: value, ...}, "geom_wkt": str}, ...]``. Rows with a NULL
    geometry are skipped. Raises :class:`qfield_builder.errors.BuildError` (``malformed_upload``)
    if the file is not a readable GeoPackage, has no feature layer, or contains a geometry type
    this application cannot round-trip.
    """
    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        geom_col = _geometry_column(conn, table)
        attr_cols = _attribute_columns(conn, table, geom_col)
        select_cols = ", ".join(f'"{c}"' for c in [*attr_cols, geom_col])
        try:
            rows = conn.execute(f'SELECT {select_cols} FROM "{table}";').fetchall()
        except sqlite3.DatabaseError as exc:
            raise BuildError(
                "malformed_upload", f"GeoPackage 테이블 '{table}'을(를) 읽을 수 없었습니다: {exc}"
            ) from exc

        results = []
        for row in rows:
            attrs = dict(zip(attr_cols, row[:-1], strict=False))
            geom_blob = row[-1]
            if geom_blob is None:
                continue
            try:
                wkb = strip_gpkg_geometry_header(bytes(geom_blob))
                wkt, _geom_type = wkb_to_wkt(wkb)
            except Exception as exc:  # noqa: BLE001 - re-raised as a structured BuildError below.
                raise BuildError(
                    "malformed_upload",
                    f"테이블 '{table}'의 geometry를 해독할 수 없었습니다: {exc}",
                ) from exc
            results.append({"attributes": attrs, "geom_wkt": wkt})
        return results
    finally:
        conn.close()


def read_first_feature_layer_raw(gpkg_path: str) -> list[dict]:
    """Read uploaded features without materialising giant geometries as WKT strings.

    The build pipeline only needs to copy the source 2D polygon WKB into the generated
    GeoPackage.  Converting a large administrative boundary WKB to WKT and parsing it back was
    both wasteful and, combined with ring-simplicity checks, made project creation appear to
    hang.  The returned records contain the plain WKB body and the source header envelope.
    """
    conn = _open(gpkg_path)
    try:
        table = _first_feature_table(conn)
        geom_col = _geometry_column(conn, table)
        attr_cols = _attribute_columns(conn, table, geom_col)
        select_cols = ", ".join(f'"{c}"' for c in [*attr_cols, geom_col])
        try:
            rows = conn.execute(f'SELECT {select_cols} FROM "{table}";').fetchall()
        except sqlite3.DatabaseError as exc:
            raise BuildError(
                "malformed_upload", f"GeoPackage 테이블 '{table}'을(를) 읽을 수 없었습니다: {exc}"
            ) from exc

        results = []
        for row in rows:
            attrs = dict(zip(attr_cols, row[:-1], strict=False))
            geom_blob = row[-1]
            if geom_blob is None:
                continue
            try:
                raw_blob = bytes(geom_blob)
                wkb = strip_gpkg_geometry_header(raw_blob)
                if len(wkb) < 5:
                    raise ValueError("WKB 데이터가 너무 짧습니다")
                if wkb[0] not in (0, 1):
                    raise ValueError("WKB byte order가 올바르지 않습니다")
                byte_order = "<" if wkb[0] == 1 else ">"
                (geom_type,) = struct.unpack_from(f"{byte_order}I", wkb, 1)
                _reject_if_z_or_m(geom_type)
                # Decode the complete nested geometry tree, consume Z/M ordinates safely, and
                # normalize polygon members (including GeometryCollection members) to the
                # application's plain 2D MultiPolygon storage contract.
                normalized_wkb = wkb_to_multipolygon_wkb(wkb)
                # Normal GeoPackage blobs carry an XY envelope in their header, so this stays
                # constant-time even for million-vertex boundaries.  Only nonstandard blobs
                # without an envelope need the linear fallback scan.
                envelope = envelope_from_gpkg_blob(raw_blob)
                if envelope is None:
                    envelope = _wkb_envelope(wkb)
            except Exception as exc:  # noqa: BLE001 - re-raised as a structured BuildError below.
                raise BuildError(
                    "malformed_upload",
                    f"테이블 '{table}'의 geometry를 해독할 수 없었습니다: {exc}",
                ) from exc
            results.append(
                {
                    "attributes": attrs,
                    "geom_wkb": normalized_wkb,
                    "envelope": envelope,
                    "geometry_type": "POLYGON" if geom_type == WKB_POLYGON else "MULTIPOLYGON",
                }
            )
        return results
    finally:
        conn.close()
