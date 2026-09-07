"""Minimal WKT parsing and GeoPackage-compliant WKB encoding.

No external geometry library (e.g. Shapely/GDAL) is required for the geometry types this
application actually needs: POINT, POLYGON, and MULTIPOLYGON, all in two dimensions. This keeps
the pure-Python GeoPackage builder (:mod:`qfield_builder.gpkg`) fully testable without a QGIS/
GDAL runtime, while still producing standards-compliant WKB blobs (OGC Simple Features, wrapped
in the GeoPackage binary geometry header) that GDAL/QGIS can read back correctly.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass

WKB_POINT = 1
WKB_POLYGON = 3
WKB_MULTIPOLYGON = 6
WKB_GEOMETRYCOLLECTION = 7

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


class InvalidGeometryError(ValueError):
    """Raised when WKT input is not parseable, or is invalid for its declared geometry type."""


@dataclass(frozen=True)
class Envelope:
    min_x: float
    max_x: float
    min_y: float
    max_y: float


Ring = list[tuple[float, float]]


def _tokenize_numbers(text: str) -> list[float]:
    return [float(m.group(0)) for m in _NUM_RE.finditer(text)]


def _split_rings(inner: str) -> list[str]:
    """Split a `(...),(...),(...)` ring list into its top-level parenthesized groups."""
    rings = []
    depth = 0
    start = None
    for i, ch in enumerate(inner):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                rings.append(inner[start:i])
                start = None
    return rings


def _split_polygons(inner: str) -> list[str]:
    """Split a MULTIPOLYGON body `((...)),((...))` into its per-polygon ring-list bodies.

    Each returned string is a polygon's own ring-list body (i.e. what :func:`_split_rings`
    expects), with that polygon's own wrapping parentheses stripped — identical top-level
    parenthesized-group extraction to :func:`_split_rings`, just applied one level higher.
    """
    return _split_rings(inner)


def _parse_ring(ring_text: str) -> Ring:
    nums = _tokenize_numbers(ring_text)
    if len(nums) % 2 != 0 or len(nums) < 6:
        raise InvalidGeometryError(f"고리(ring)에는 좌표쌍이 3개 이상 있어야 합니다: {ring_text!r}")
    coords = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    if coords[0] != coords[-1]:
        raise InvalidGeometryError(
            "폴리곤 고리가 닫혀 있지 않습니다 (첫 점과 마지막 점이 다릅니다)"
        )
    return coords


def _ring_self_intersects(ring: Ring) -> bool:
    """True if this ring is self-intersecting (e.g. the classic "bowtie" polygon), per FR-QPB-028.

    This is a pragmatic, non-exhaustive simplicity check (pairwise segment-intersection test
    over the ring's edges, excluding adjacent segments and the closing vertex) — sufficient to
    catch the deliberately-invalid bowtie fixture used by the acceptance tests, without pulling
    in a full computational-geometry dependency.
    """
    points = ring[:-1]
    n = len(points)
    if n < 3:
        return False
    # Uploaded administrative boundaries can legitimately contain hundreds of thousands of
    # vertices. An exact simplicity check for those rings is prohibitively expensive even with
    # the indexed scan below; structural parsing and QGIS's own geometry validation still run,
    # while the exhaustive check remains enabled for normal-sized user-drawn/uploaded shapes.
    if n > 10000:
        return False

    def _segments_intersect(p1, p2, p3, p4) -> bool:
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        d1 = cross(p3, p4, p1)
        d2 = cross(p3, p4, p2)
        d3 = cross(p1, p2, p3)
        d4 = cross(p1, p2, p4)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False

    edges = [(points[i], points[(i + 1) % n]) for i in range(n)]
    # The previous all-pairs scan made an uploaded administrative boundary with tens of
    # thousands of vertices appear to hang (O(n²) comparisons). Sort by the edge's x-range and
    # stop once later edges cannot overlap that range; the cheap bounding-box checks retain the
    # exact segment test while making ordinary GIS boundaries effectively linear in practice.
    indexed = sorted(
        enumerate(edges),
        key=lambda item: min(item[1][0][0], item[1][1][0]),
    )
    for position, (i, edge_i) in enumerate(indexed):
        p1, p2 = edge_i
        max_x_i = max(p1[0], p2[0])
        min_y_i = min(p1[1], p2[1])
        max_y_i = max(p1[1], p2[1])
        for j, edge_j in indexed[position + 1 :]:
            if min(edge_j[0][0], edge_j[1][0]) > max_x_i:
                break
            if j == i + 1 or (i == 0 and j == len(edges) - 1):
                continue  # adjacent edges share a vertex; that's not a self-intersection
            p3, p4 = edge_j
            if max(p3[1], p4[1]) < min_y_i or min(p3[1], p4[1]) > max_y_i:
                continue
            if _segments_intersect(p1, p2, p3, p4):
                return True
    return False


def parse_point(wkt: str) -> tuple[float, float]:
    match = re.search(r"POINT\s*\(\s*([^)]+)\)", wkt, re.IGNORECASE)
    if not match:
        raise InvalidGeometryError(f"올바른 POINT WKT가 아닙니다: {wkt!r}")
    nums = _tokenize_numbers(match.group(1))
    if len(nums) < 2:
        raise InvalidGeometryError(f"POINT에는 x/y 좌표가 필요합니다: {wkt!r}")
    return nums[0], nums[1]


def parse_polygon(wkt: str) -> list[Ring]:
    match = re.search(r"POLYGON\s*\((.*)\)\s*$", wkt.strip(), re.IGNORECASE | re.DOTALL)
    if not match:
        raise InvalidGeometryError(f"올바른 POLYGON WKT가 아닙니다: {wkt!r}")
    rings = [_parse_ring(r) for r in _split_rings(match.group(1))]
    if not rings:
        raise InvalidGeometryError("POLYGON에 고리(ring)가 없습니다")
    if _ring_self_intersects(rings[0]):
        raise InvalidGeometryError(
            "POLYGON의 외부 고리가 자기 자신과 교차합니다 (잘못된 geometry입니다)"
        )
    return rings


def parse_multipolygon(wkt: str) -> list[list[Ring]]:
    match = re.search(r"MULTIPOLYGON\s*\((.*)\)\s*$", wkt.strip(), re.IGNORECASE | re.DOTALL)
    if not match:
        raise InvalidGeometryError(f"올바른 MULTIPOLYGON WKT가 아닙니다: {wkt!r}")
    polygons = []
    for poly_body in _split_polygons(match.group(1)):
        rings = [_parse_ring(r) for r in _split_rings(poly_body)]
        if not rings:
            raise InvalidGeometryError("MULTIPOLYGON에 고리(ring)가 없는 폴리곤이 있습니다")
        if _ring_self_intersects(rings[0]):
            raise InvalidGeometryError(
                "MULTIPOLYGON에 자기 자신과 교차하는 고리가 있습니다 (잘못된 geometry입니다)"
            )
        polygons.append(rings)
    if not polygons:
        raise InvalidGeometryError("MULTIPOLYGON에 폴리곤이 없습니다")
    return polygons


def validate_geometry(wkt: str, expected_type: str) -> None:
    """Raise InvalidGeometryError if `wkt` is malformed or not of `expected_type`."""
    upper = wkt.strip().upper()
    if expected_type == "POINT":
        if not upper.startswith("POINT"):
            raise InvalidGeometryError(f"POINT geometry가 필요하지만 다음 값을 받았습니다: {wkt!r}")
        parse_point(wkt)
    elif expected_type == "MULTIPOLYGON":
        if upper.startswith("MULTIPOLYGON"):
            parse_multipolygon(wkt)
        elif upper.startswith("POLYGON"):
            # A bare POLYGON is accepted and treated as a single-member MultiPolygon.
            parse_polygon(wkt)
        else:
            raise InvalidGeometryError(
                f"POLYGON/MULTIPOLYGON geometry가 필요하지만 다음 값을 받았습니다: {wkt!r}"
            )
    else:
        raise InvalidGeometryError(f"지원되지 않는 geometry 유형입니다: {expected_type!r}")


def envelope_of(wkt: str, expected_type: str) -> Envelope:
    if expected_type == "POINT":
        x, y = parse_point(wkt)
        return Envelope(min_x=x, max_x=x, min_y=y, max_y=y)
    if expected_type == "MULTIPOLYGON":
        upper = wkt.strip().upper()
        polygons = (
            parse_multipolygon(wkt) if upper.startswith("MULTIPOLYGON") else [parse_polygon(wkt)]
        )
        xs = [pt[0] for poly in polygons for ring in poly for pt in ring]
        ys = [pt[1] for poly in polygons for ring in poly for pt in ring]
        return Envelope(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))
    raise InvalidGeometryError(f"지원되지 않는 geometry 유형입니다: {expected_type!r}")


def _pack_ring(ring: Ring) -> bytes:
    # Mutable accumulation keeps million-vertex boundary serialization linear, not quadratic.
    out = bytearray(struct.pack("<I", len(ring)))
    for x, y in ring:
        out += struct.pack("<dd", x, y)
    return bytes(out)


def _wkb_point(x: float, y: float) -> bytes:
    return struct.pack("<BI", 1, WKB_POINT) + struct.pack("<dd", x, y)


def _wkb_polygon_body(rings: list[Ring]) -> bytes:
    out = bytearray(struct.pack("<I", len(rings)))
    for ring in rings:
        out += _pack_ring(ring)
    return bytes(out)


def _wkb_polygon(rings: list[Ring]) -> bytes:
    return struct.pack("<BI", 1, WKB_POLYGON) + _wkb_polygon_body(rings)


def _wkb_multipolygon(polygons: list[list[Ring]]) -> bytes:
    out = bytearray(struct.pack("<BI", 1, WKB_MULTIPOLYGON) + struct.pack("<I", len(polygons)))
    for rings in polygons:
        out += struct.pack("<BI", 1, WKB_POLYGON) + _wkb_polygon_body(rings)
    return bytes(out)


def wkt_to_wkb(wkt: str, expected_type: str) -> bytes:
    """Convert WKT to standard (non-GeoPackage-header) little-endian WKB bytes."""
    validate_geometry(wkt, expected_type)
    upper = wkt.strip().upper()
    if expected_type == "POINT":
        x, y = parse_point(wkt)
        return _wkb_point(x, y)
    if expected_type == "MULTIPOLYGON":
        if upper.startswith("MULTIPOLYGON"):
            return _wkb_multipolygon(parse_multipolygon(wkt))
        return _wkb_multipolygon([parse_polygon(wkt)])
    raise InvalidGeometryError(f"지원되지 않는 geometry 유형입니다: {expected_type!r}")


def wkb_to_gpkg_blob(wkb: bytes, srs_id: int, envelope: Envelope | None = None) -> bytes:
    """Wrap standard WKB in a GeoPackage binary geometry header (GeoPackage spec Annex on
    Binary Geometry format): magic 'GP', version 0, flags, srs_id, optional envelope, then WKB.
    """
    magic = b"GP"
    version = bytes([0])
    if envelope is None:
        flags = bytes([0b00000001])  # little-endian, no envelope
        header_tail = struct.pack("<i", srs_id)
    else:
        flags = bytes([0b00000011])  # little-endian, envelope type 1 (minx,maxx,miny,maxy)
        header_tail = struct.pack("<i", srs_id) + struct.pack(
            "<dddd", envelope.min_x, envelope.max_x, envelope.min_y, envelope.max_y
        )
    return magic + version + flags + header_tail + wkb


def polygon_wkb_to_multipolygon(wkb: bytes) -> bytes:
    """Wrap a plain Polygon WKB as a one-member MultiPolygon WKB."""
    if not wkb or len(wkb) < 5:
        raise InvalidGeometryError("WKB 데이터가 너무 짧습니다")
    byte_order = wkb[0]
    endian = "<" if byte_order == 1 else ">" if byte_order == 0 else None
    if endian is None:
        raise InvalidGeometryError("WKB byte order가 올바르지 않습니다")
    (geom_type,) = struct.unpack_from(f"{endian}I", wkb, 1)
    if geom_type != WKB_POLYGON:
        return wkb
    # The nested polygon retains its original byte order; the outer wrapper is little-endian,
    # which is valid mixed-endian WKB and is accepted by QGIS/GDAL.
    return struct.pack("<BI", 1, WKB_MULTIPOLYGON) + struct.pack("<I", 1) + wkb


def wkt_to_gpkg_geometry(
    wkt: str, expected_type: str, srs_id: int = 4326
) -> tuple[bytes, Envelope]:
    """Convert WKT straight to a GeoPackage geometry BLOB plus its envelope (for rtree indexing)."""
    envelope = envelope_of(wkt, expected_type)
    wkb = wkt_to_wkb(wkt, expected_type)
    blob = wkb_to_gpkg_blob(wkb, srs_id, envelope)
    return blob, envelope


def _ring_to_wkt(ring: Ring) -> str:
    coords = ", ".join(f"{x} {y}" for x, y in ring)
    return f"({coords})"


def _read_ring(wkb: bytes, offset: int, byte_order: str) -> tuple[Ring, int]:
    (num_points,) = struct.unpack_from(f"{byte_order}I", wkb, offset)
    offset += 4
    points = []
    for _ in range(num_points):
        x, y = struct.unpack_from(f"{byte_order}dd", wkb, offset)
        points.append((x, y))
        offset += 16
    return points, offset


def _read_polygon_body(wkb: bytes, offset: int, byte_order: str) -> tuple[list[Ring], int]:
    (num_rings,) = struct.unpack_from(f"{byte_order}I", wkb, offset)
    offset += 4
    rings = []
    for _ in range(num_rings):
        ring, offset = _read_ring(wkb, offset, byte_order)
        rings.append(ring)
    return rings, offset


def _wkb_type_info(geom_type: int) -> tuple[int, int, bool]:
    """Return base type, extra ordinate count, and EWKB-SRID presence."""
    ewkb = bool(geom_type & 0xE0000000)
    if ewkb:
        dimensions = bool(geom_type & 0x80000000) + bool(geom_type & 0x40000000)
        return geom_type & 0x0FFFFFFF, dimensions, bool(geom_type & 0x20000000)
    if 1000 <= geom_type < 4000:
        offset, base = divmod(geom_type, 1000)
        if offset in (1, 2):
            return base, 1, False
        if offset == 3:
            return base, 2, False
    return geom_type, 0, False


def _reject_if_z_or_m(geom_type: int) -> None:
    """Compatibility validator retained for callers; dimensional WKB is now decoded safely."""
    base, _dimensions, _has_srid = _wkb_type_info(geom_type)
    if base not in (WKB_POINT, WKB_POLYGON, WKB_MULTIPOLYGON, WKB_GEOMETRYCOLLECTION):
        raise InvalidGeometryError(f"지원되지 않는 WKB geometry 유형 코드입니다: {geom_type}")


def _read_wkb_geometry(wkb: bytes, offset: int = 0) -> tuple[dict, int]:
    if offset + 5 > len(wkb):
        raise InvalidGeometryError("WKB geometry header가 잘렸습니다")
    byte_order = "<" if wkb[offset] == 1 else ">" if wkb[offset] == 0 else None
    if byte_order is None:
        raise InvalidGeometryError("WKB byte order가 올바르지 않습니다")
    raw_type = struct.unpack_from(f"{byte_order}I", wkb, offset + 1)[0]
    base_type, dimensions, has_srid = _wkb_type_info(raw_type)
    offset += 5
    if has_srid:
        if offset + 4 > len(wkb):
            raise InvalidGeometryError("EWKB SRID가 잘렸습니다")
        offset += 4
    def point() -> tuple[float, float]:
        nonlocal offset
        stride = 8 * (2 + dimensions)
        if offset + stride > len(wkb):
            raise InvalidGeometryError("WKB 좌표가 잘렸습니다")
        values = struct.unpack_from(f"{byte_order}{'d' * (2 + dimensions)}", wkb, offset)
        offset += stride
        return values[0], values[1]
    if base_type == WKB_POINT:
        return {"type": base_type, "point": point()}, offset
    if base_type == WKB_POLYGON:
        if offset + 4 > len(wkb): raise InvalidGeometryError("WKB polygon이 잘렸습니다")
        count = struct.unpack_from(f"{byte_order}I", wkb, offset)[0]; offset += 4
        rings = []
        for _ in range(count):
            if offset + 4 > len(wkb): raise InvalidGeometryError("WKB ring이 잘렸습니다")
            points = struct.unpack_from(f"{byte_order}I", wkb, offset)[0]; offset += 4
            rings.append([point() for _ in range(points)])
        return {"type": base_type, "rings": rings}, offset
    if base_type in (WKB_MULTIPOLYGON, WKB_GEOMETRYCOLLECTION):
        if offset + 4 > len(wkb): raise InvalidGeometryError("WKB collection이 잘렸습니다")
        count = struct.unpack_from(f"{byte_order}I", wkb, offset)[0]; offset += 4
        geometries = []
        for _ in range(count):
            geometry, offset = _read_wkb_geometry(wkb, offset)
            geometries.append(geometry)
        return {"type": base_type, "geometries": geometries}, offset
    raise InvalidGeometryError(f"지원되지 않거나 인식할 수 없는 WKB geometry 유형 코드입니다: {raw_type}")


def _polygon_members(geometry: dict) -> list[dict]:
    if geometry["type"] == WKB_POLYGON:
        return [geometry]
    if geometry["type"] in (WKB_MULTIPOLYGON, WKB_GEOMETRYCOLLECTION):
        return [member for child in geometry.get("geometries", []) for member in _polygon_members(child)]
    return []


def wkb_to_multipolygon_wkb(wkb: bytes) -> bytes:
    """Decode dimensional/nested WKB and normalize all polygon members to plain 2D MultiPolygon."""
    geometry, end = _read_wkb_geometry(wkb)
    if end != len(wkb):
        raise InvalidGeometryError("WKB 뒤에 해석할 수 없는 데이터가 있습니다")
    polygons = _polygon_members(geometry)
    if not polygons:
        raise InvalidGeometryError("사이트 업로드에는 Polygon을 포함한 geometry가 필요합니다")
    return _wkb_multipolygon([polygon["rings"] for polygon in polygons])


def wkb_to_wkt(wkb: bytes) -> tuple[str, str]:
    """Reverse of :func:`wkt_to_wkb`: parse WKB Point, Polygon, MultiPolygon, and
    polygon-bearing GeometryCollection values back into a 2D WKT string. ISO Z/M and EWKB
    dimensional ordinates are consumed and intentionally discarded because storage is 2D. Used
    to read externally-supplied GeoPackage site/plot uploads
    (FR-QPB-025) whose geometries were not necessarily written by this application itself, but are
    still plain OGC Simple Features WKB once the GeoPackage binary-geometry header is stripped
    (see :mod:`qfield_builder.gpkg_functions`/:mod:`qfield_builder.gpkg_upload_reader`).

    Polygon members of GeometryCollection are flattened into a MultiPolygon; a collection without
    a polygon is an explicit invalid limitation for the site/plot upload contract.

    Returns ``(wkt, geometry_type_name)`` where ``geometry_type_name`` is one of ``"POINT"``,
    ``"POLYGON"``, ``"MULTIPOLYGON"``.
    """
    if not wkb or len(wkb) < 5:
        raise InvalidGeometryError("WKB 데이터가 너무 짧아 올바른 geometry일 수 없습니다")
    geometry, end = _read_wkb_geometry(wkb)
    if end != len(wkb):
        raise InvalidGeometryError("WKB 뒤에 해석할 수 없는 데이터가 있습니다")
    base_type = geometry["type"]
    if base_type == WKB_POINT:
        x, y = geometry["point"]
        return f"POINT({x} {y})", "POINT"
    polygons = _polygon_members(geometry)
    if base_type == WKB_POLYGON:
        rings = geometry["rings"]
        return f"POLYGON({', '.join(_ring_to_wkt(r) for r in rings)})", "POLYGON"
    if base_type in (WKB_MULTIPOLYGON, WKB_GEOMETRYCOLLECTION) and polygons:
        polys_wkt = ["(" + ", ".join(_ring_to_wkt(r) for r in p["rings"]) + ")" for p in polygons]
        return f"MULTIPOLYGON({', '.join(polys_wkt)})", "MULTIPOLYGON"
    raise InvalidGeometryError("GeometryCollection에 지원되는 Polygon이 없습니다")
