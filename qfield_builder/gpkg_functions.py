"""Python implementations of the GeoPackage SQL functions the RTree-maintenance triggers need.

The standard GeoPackage R*Tree Spatial Indexes extension trigger set (see :mod:`qfield_builder.
gpkg`) calls ``ST_MinX``/``ST_MaxX``/``ST_MinY``/``ST_MaxY``/``ST_IsEmpty`` SQL functions. A real
QGIS/GDAL installation registers native implementations of these automatically when it opens a
GeoPackage. Because this package also needs to create/seed GeoPackages, and read them back for
`validate_project`, entirely through plain :mod:`sqlite3` connections (no GDAL dependency for
those code paths — see module docstring in :mod:`qfield_builder.gpkg`), this module provides
pure-Python equivalents and registers them on any such connection, so those triggers work
identically whether the connection was opened by GDAL or by this application's own tooling.
"""
from __future__ import annotations

import sqlite3
import struct

from .wkt import Envelope


def _parse_gpkg_geometry_header(blob: bytes) -> tuple[int, bytes]:
    """Return (envelope_type, remaining_wkb_bytes) from a GeoPackage geometry BLOB header."""
    if blob is None or len(blob) < 8 or blob[0:2] != b"GP":
        raise ValueError("Not a GeoPackage geometry blob")
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    is_little_endian = bool(flags & 0x01)
    endian = "<" if is_little_endian else ">"
    offset = 4
    (srs_id,) = struct.unpack_from(f"{endian}i", blob, offset)  # noqa: F841 (kept for clarity)
    offset += 4
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    offset += envelope_sizes.get(envelope_type, 0)
    return envelope_type, blob[offset:]


def _wkb_envelope(wkb: bytes) -> Envelope | None:
    from .wkt import wkb_to_wkt, envelope_of
    text, kind = wkb_to_wkt(wkb)
    return envelope_of(text, kind)


def _envelope_from_blob(blob) -> Envelope | None:
    if blob is None:
        return None
    # Prefer the XY envelope already present in the GeoPackage header.  Walking every WKB
    # coordinate here is needlessly expensive for the RTree triggers when importing a large
    # administrative boundary.
    return envelope_from_gpkg_blob(bytes(blob))


def strip_gpkg_geometry_header(blob: bytes) -> bytes:
    """Return the plain OGC WKB body of a GeoPackage binary-geometry BLOB (header stripped).

    Public wrapper around :func:`_parse_gpkg_geometry_header` for callers outside this module
    (e.g. :mod:`qfield_builder.gpkg_upload_reader`) that need the raw WKB bytes, not just the
    envelope this module itself computes from them.
    """
    _envelope_type, wkb = _parse_gpkg_geometry_header(bytes(blob))
    return wkb


def envelope_from_gpkg_blob(blob: bytes) -> Envelope | None:
    """Read the XY envelope stored in a GeoPackage geometry header.

    Uploaded administrative boundaries can contain millions of vertices.  When the source
    GeoPackage includes the normal XY envelope (envelope type 1), reading it from the header is
    constant-time and avoids walking every WKB coordinate merely to rebuild the destination
    RTree index.  For files without a header envelope we fall back to the linear WKB scan.
    """
    raw = bytes(blob)
    if len(raw) < 8 or raw[:2] != b"GP":
        raise ValueError("Not a GeoPackage geometry blob")
    flags = raw[3]
    envelope_type = (flags >> 1) & 0x07
    endian = "<" if flags & 0x01 else ">"
    offset = 8
    if envelope_type in (1, 2, 3, 4):
        if len(raw) < offset + 32:
            raise ValueError("GeoPackage geometry envelope is truncated")
        min_x, max_x, min_y, max_y = struct.unpack_from(f"{endian}dddd", raw, offset)
        return Envelope(min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
    return _wkb_envelope(_parse_gpkg_geometry_header(raw)[1])


def st_is_empty(blob) -> int:
    try:
        return 0 if _envelope_from_blob(blob) is not None else 1
    except (ValueError, struct.error):
        return 1


def st_min_x(blob):
    env = _envelope_from_blob(blob)
    return None if env is None else env.min_x


def st_max_x(blob):
    env = _envelope_from_blob(blob)
    return None if env is None else env.max_x


def st_min_y(blob):
    env = _envelope_from_blob(blob)
    return None if env is None else env.min_y


def st_max_y(blob):
    env = _envelope_from_blob(blob)
    return None if env is None else env.max_y


def register_gpkg_functions(conn: sqlite3.Connection) -> None:
    """Register ST_MinX/ST_MaxX/ST_MinY/ST_MaxY/ST_IsEmpty on a plain sqlite3 connection.

    Safe/idempotent to call on every connection this application opens itself. Has no effect on
    (and is unnecessary for) connections GDAL/QGIS opens on its own, since GDAL registers its own
    native versions of the same function names.
    """
    conn.create_function("ST_IsEmpty", 1, st_is_empty, deterministic=True)
    conn.create_function("ST_MinX", 1, st_min_x, deterministic=True)
    conn.create_function("ST_MaxX", 1, st_max_x, deterministic=True)
    conn.create_function("ST_MinY", 1, st_min_y, deterministic=True)
    conn.create_function("ST_MaxY", 1, st_max_y, deterministic=True)
