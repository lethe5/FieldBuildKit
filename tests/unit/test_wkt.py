"""Unit tests for qfield_builder.wkt (WKT parsing, validity checks, WKB/GeoPackage encoding)."""
from __future__ import annotations

import struct

import pytest

from qfield_builder.wkt import (
    WKB_MULTIPOLYGON,
    WKB_POLYGON,
    InvalidGeometryError,
    envelope_of,
    validate_geometry,
    wkb_to_gpkg_blob,
    wkb_to_wkt,
    wkt_to_gpkg_geometry,
    wkt_to_wkb,
)


def test_nested_polygon_serialization_does_not_recopy_growing_buffers(monkeypatch):
    """Count immutable concatenation work instead of relying on machine-dependent timings."""
    from qfield_builder import wkt

    original_pack = struct.pack
    copied = 0

    class TrackedBytes(bytes):
        def __add__(self, other):
            nonlocal copied
            copied += len(self) + len(other)
            return TrackedBytes(super().__add__(other))

    ring = [(float(i), float(i % 2)) for i in range(1024)]
    ring.append(ring[0])
    packed_ring = original_pack("<I", len(ring)) + b"".join(
        original_pack("<dd", *point) for point in ring
    )
    body = original_pack("<I", 8) + packed_ring * 8
    polygon = original_pack("<BI", 1, 3) + body
    expected = original_pack("<BII", 1, 6, 4) + polygon * 4
    monkeypatch.setattr(wkt.struct, "pack", lambda *args: TrackedBytes(original_pack(*args)))
    actual = wkt._wkb_multipolygon([[ring] * 8] * 4)
    assert actual == expected
    assert type(actual) is bytes
    assert copied <= len(expected) * 4

VALID_MULTIPOLYGON = (
    "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
)
VALID_POLYGON = "POLYGON((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00))"
BOWTIE_POLYGON = "POLYGON((127.00 37.00, 127.01 37.01, 127.00 37.01, 127.01 37.00, 127.00 37.00))"
VALID_POINT = "POINT(127.005 37.005)"


def test_valid_point():
    validate_geometry(VALID_POINT, "POINT")


def test_valid_multipolygon():
    validate_geometry(VALID_MULTIPOLYGON, "MULTIPOLYGON")


def test_bare_polygon_accepted_as_multipolygon():
    validate_geometry(VALID_POLYGON, "MULTIPOLYGON")


def test_bowtie_polygon_is_invalid():
    with pytest.raises(InvalidGeometryError):
        validate_geometry(BOWTIE_POLYGON, "MULTIPOLYGON")


def test_wrong_geometry_type_rejected():
    with pytest.raises(InvalidGeometryError):
        validate_geometry(VALID_POINT, "MULTIPOLYGON")
    with pytest.raises(InvalidGeometryError):
        validate_geometry(VALID_MULTIPOLYGON, "POINT")


def test_unclosed_ring_is_invalid():
    unclosed = "POLYGON((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01))"
    with pytest.raises(InvalidGeometryError):
        validate_geometry(unclosed, "MULTIPOLYGON")


def test_envelope_of_point():
    env = envelope_of(VALID_POINT, "POINT")
    assert env.min_x == env.max_x == 127.005
    assert env.min_y == env.max_y == 37.005


def test_envelope_of_multipolygon():
    env = envelope_of(VALID_MULTIPOLYGON, "MULTIPOLYGON")
    assert env.min_x == pytest.approx(127.00)
    assert env.max_x == pytest.approx(127.01)
    assert env.min_y == pytest.approx(37.00)
    assert env.max_y == pytest.approx(37.01)


def test_wkb_point_round_trip_byte_structure():
    wkb = wkt_to_wkb(VALID_POINT, "POINT")
    byte_order, geom_type = struct.unpack_from("<BI", wkb, 0)
    assert byte_order == 1  # little-endian
    assert geom_type == 1  # WKB Point
    x, y = struct.unpack_from("<dd", wkb, 5)
    assert (x, y) == (127.005, 37.005)


def test_gpkg_blob_has_gp_magic_header():
    blob, _ = wkt_to_gpkg_geometry(VALID_POINT, "POINT", srs_id=4326)
    assert blob[0:2] == b"GP"


def test_gpkg_blob_without_envelope_omits_envelope_bytes():
    wkb = wkt_to_wkb(VALID_POINT, "POINT")
    blob = wkb_to_gpkg_blob(wkb, srs_id=4326, envelope=None)
    # magic(2) + version(1) + flags(1) + srs_id(4) = 8 header bytes, then WKB directly.
    assert blob[8:] == wkb
    (srs_id,) = struct.unpack_from("<i", blob, 4)
    assert srs_id == 4326


# ---------------------------------------------------------------------------------------------
# wkb_to_wkt: round trips for POINT / POLYGON (with a hole) / MULTIPOLYGON, verified against
# known-correct WKT strings (not just "it didn't crash").
# ---------------------------------------------------------------------------------------------

POLYGON_WITH_HOLE = (
    "POLYGON("
    "(127.00 37.00, 127.10 37.00, 127.10 37.10, 127.00 37.10, 127.00 37.00), "
    "(127.02 37.02, 127.02 37.04, 127.04 37.04, 127.04 37.02, 127.02 37.02)"
    ")"
)


def test_wkb_to_wkt_point_round_trip():
    wkb = wkt_to_wkb(VALID_POINT, "POINT")
    wkt, geom_type = wkb_to_wkt(wkb)
    assert geom_type == "POINT"
    assert wkt == "POINT(127.005 37.005)"


def test_wkb_to_wkt_polygon_round_trip():
    wkb = wkt_to_wkb(VALID_POLYGON, "MULTIPOLYGON")  # writer always emits MultiPolygon WKB
    wkt, geom_type = wkb_to_wkt(wkb)
    assert geom_type == "MULTIPOLYGON"
    assert wkt == (
        "MULTIPOLYGON(((127.0 37.0, 127.01 37.0, 127.01 37.01, 127.0 37.01, 127.0 37.0)))"
    )


def test_wkb_to_wkt_polygon_with_hole_round_trip():
    # Exercise the raw single-Polygon WKB path (_wkb_polygon/_read_polygon_body) directly, since
    # this application's own writer (wkt_to_wkb) always upgrades bare POLYGON WKT to a
    # single-member MultiPolygon -- a plain WKB Polygon (type code 3) is exactly what an
    # externally-authored GeoPackage's `site`/`plot` layer could still legitimately contain, and
    # is the code path FR-QPB-025 uploads must also round-trip correctly, holes included.
    from qfield_builder.wkt import _wkb_polygon, parse_polygon

    rings = parse_polygon(POLYGON_WITH_HOLE)
    assert len(rings) == 2  # exterior ring + one interior ring (hole)
    wkb = _wkb_polygon(rings)

    wkt, geom_type = wkb_to_wkt(wkb)
    assert geom_type == "POLYGON"
    assert wkt == (
        "POLYGON("
        "(127.0 37.0, 127.1 37.0, 127.1 37.1, 127.0 37.1, 127.0 37.0), "
        "(127.02 37.02, 127.02 37.04, 127.04 37.04, 127.04 37.02, 127.02 37.02)"
        ")"
    )


def test_wkb_to_wkt_multipolygon_multiple_polygons_round_trip():
    multi = (
        "MULTIPOLYGON("
        "((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)), "
        "((128.00 38.00, 128.01 38.00, 128.01 38.01, 128.00 38.01, 128.00 38.00))"
        ")"
    )
    wkb = wkt_to_wkb(multi, "MULTIPOLYGON")
    wkt, geom_type = wkb_to_wkt(wkb)
    assert geom_type == "MULTIPOLYGON"
    assert wkt == (
        "MULTIPOLYGON("
        "((127.0 37.0, 127.01 37.0, 127.01 37.01, 127.0 37.01, 127.0 37.0)), "
        "((128.0 38.0, 128.01 38.0, 128.01 38.01, 128.0 38.01, 128.0 38.0))"
        ")"
    )


def test_wkb_to_wkt_too_short_is_rejected():
    with pytest.raises(InvalidGeometryError):
        wkb_to_wkt(b"\x01\x01")


def test_wkb_to_wkt_unrecognized_type_code_is_rejected():
    bogus = struct.pack("<BI", 1, 999) + struct.pack("<dd", 1.0, 2.0)
    with pytest.raises(InvalidGeometryError):
        wkb_to_wkt(bogus)


# ---------------------------------------------------------------------------------------------
# wkb_to_wkt: dimensional WKB must consume extra ordinates safely.
# ---------------------------------------------------------------------------------------------


def _iso_z_point_wkb(x: float, y: float, z: float) -> bytes:
    """A PointZ WKB using the ISO SQL/MM "extended" convention (+1000 type-code offset) that
    GeoPackage/GDAL/QGIS actually write (e.g. QGIS's "Include Z dimension" layer option)."""
    return struct.pack("<BI", 1, 1001) + struct.pack("<ddd", x, y, z)


def _ewkb_z_point_wkb(x: float, y: float, z: float) -> bytes:
    """A PointZ WKB using the PostGIS/EWKB high-bit Z flag convention (0x80000000)."""
    return struct.pack("<BI", 1, 0x80000001) + struct.pack("<ddd", x, y, z)


def test_wkb_to_wkt_decodes_iso_extended_z_point_as_xy():
    wkb = _iso_z_point_wkb(127.0, 37.0, 55.0)
    assert wkb_to_wkt(wkb) == ("POINT(127.0 37.0)", "POINT")


def test_wkb_to_wkt_decodes_iso_extended_m_point_as_xy():
    # PointM uses the +2000 offset per the same ISO SQL/MM convention.
    wkb = struct.pack("<BI", 1, 2001) + struct.pack("<ddd", 127.0, 37.0, 12.5)
    assert wkb_to_wkt(wkb) == ("POINT(127.0 37.0)", "POINT")


def test_wkb_to_wkt_decodes_iso_extended_zm_point_as_xy():
    # PointZM uses the +3000 offset.
    wkb = struct.pack("<BI", 1, 3001) + struct.pack("<dddd", 127.0, 37.0, 55.0, 12.5)
    assert wkb_to_wkt(wkb) == ("POINT(127.0 37.0)", "POINT")


def test_wkb_to_wkt_decodes_ewkb_high_bit_z_point_as_xy():
    wkb = _ewkb_z_point_wkb(127.0, 37.0, 55.0)
    assert wkb_to_wkt(wkb) == ("POINT(127.0 37.0)", "POINT")


def test_wkb_to_wkt_decodes_z_dimensioned_polygon_as_xy():
    # A PolygonZ (ISO extended type code 1003) must be rejected before any coordinate is
    # misread -- this is the exact silent-corruption scenario the fix addresses: without the
    # fix, the stride-16-bytes-per-point reader would misinterpret the extra Z ordinates as
    # extra 2D points/garbage coordinates instead of raising.
    ring = [(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01), (127.0, 37.0)]
    body = struct.pack("<I", 1)  # num rings
    body += struct.pack("<I", len(ring))  # num points
    for x, y in ring:
        body += struct.pack("<ddd", x, y, 10.0)  # x, y, z per point
    wkb = struct.pack("<BI", 1, 1003) + body
    assert wkb_to_wkt(wkb)[1] == "POLYGON"


def test_wkb_to_wkt_decodes_z_dimensioned_nested_polygon_in_multipolygon():
    # Defense-in-depth: even if an (invalid/inconsistent) MultiPolygon container claims to be
    # plain 2D but its nested Polygon sub-geometry is itself Z-flavored, that must be rejected
    # too, rather than misreading the nested polygon's coordinates.
    ring = [(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01), (127.0, 37.0)]
    nested_body = struct.pack("<I", 1)
    nested_body += struct.pack("<I", len(ring))
    for x, y in ring:
        nested_body += struct.pack("<ddd", x, y, 10.0)
    nested_polygon_z = struct.pack("<BI", 1, 1003) + nested_body
    wkb = struct.pack("<BI", 1, WKB_MULTIPOLYGON) + struct.pack("<I", 1) + nested_polygon_z
    assert wkb_to_wkt(wkb)[1] == "MULTIPOLYGON"


def test_wkb_to_wkt_flattens_nested_geometry_collection_polygon():
    ring = [(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01), (127.0, 37.0)]
    polygon = struct.pack("<BI", 1, WKB_POLYGON) + struct.pack("<II", 1, len(ring))
    polygon += b"".join(struct.pack("<dd", x, y) for x, y in ring)
    nested = struct.pack("<BI", 1, 7) + struct.pack("<I", 1) + polygon
    wkb = struct.pack("<BI", 1, 7) + struct.pack("<I", 1) + nested
    wkt, geom_type = wkb_to_wkt(wkb)
    assert geom_type == "MULTIPOLYGON"
    assert wkt.startswith("MULTIPOLYGON(")
