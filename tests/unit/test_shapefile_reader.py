"""Unit tests for qfield_builder.shapefile_reader, using minimal synthetic .shp/.dbf fixtures.

These fixtures are constructed by hand (via `struct`) rather than depending on a real shapefile
library, since no such dependency is available/needed elsewhere in this codebase — this keeps
the test deterministic and dependency-free while still exercising the real binary parsing logic.
"""
from __future__ import annotations

import struct
import zipfile

import pytest

from qfield_builder.errors import BuildError
from qfield_builder.shapefile_reader import (
    SHAPE_TYPE_POINT,
    SHAPE_TYPE_POLYGON,
    read_shapefile,
    read_zipped_shapefile,
    shape_to_wkt,
)


def _shp_header(shape_type: int) -> bytes:
    header = bytearray(100)
    struct.pack_into(">I", header, 0, 9994)  # file code
    struct.pack_into("<I", header, 32, shape_type)
    return bytes(header)


def _polygon_record(points: list[tuple[float, float]]) -> bytes:
    ring = points + [points[0]]
    content = struct.pack("<I", SHAPE_TYPE_POLYGON)
    content += struct.pack("<dddd", 0, 0, 1, 1)  # bbox (unused by the reader)
    content += struct.pack("<I", 1)  # num parts
    content += struct.pack("<I", len(ring))  # num points
    content += struct.pack("<I", 0)  # part start index
    for x, y in ring:
        content += struct.pack("<dd", x, y)
    return content


def _point_record(x: float, y: float) -> bytes:
    return struct.pack("<I", SHAPE_TYPE_POINT) + struct.pack("<dd", x, y)


def _wrap_record(content: bytes) -> bytes:
    header = struct.pack(">II", 1, len(content) // 2)
    return header + content


def _build_shp(shape_type: int, content: bytes) -> bytes:
    return _shp_header(shape_type) + _wrap_record(content)


def _build_dbf(field_name: str, value: str, encoding: str = "ascii") -> bytes:
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<I", header, 4, 1)  # 1 record
    field_desc_len = 32
    header_len = 32 + field_desc_len + 1
    record_len = 1 + 20  # deletion flag + one 20-char field
    struct.pack_into("<H", header, 8, header_len)
    struct.pack_into("<H", header, 10, record_len)

    field_desc = bytearray(32)
    name_bytes = field_name.encode("ascii")[:10]
    field_desc[0 : len(name_bytes)] = name_bytes
    field_desc[11] = ord("C")
    field_desc[16] = 20  # length

    terminator = b"\x0d"
    record = b" " + value.ljust(20).encode(encoding)
    eof = b"\x1a"
    return bytes(header) + bytes(field_desc) + terminator + record + eof


def _zip_of(shp: bytes, dbf: bytes, tmp_path) -> str:
    zip_path = tmp_path / "sites.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("sites.shp", shp)
        zf.writestr("sites.dbf", dbf)
    return str(zip_path)


def test_read_polygon_shapefile_with_attributes(tmp_path):
    shp = _build_shp(
        SHAPE_TYPE_POLYGON,
        _polygon_record([(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01)]),
    )
    dbf = _build_dbf("NAME", "Site A")
    zip_path = _zip_of(shp, dbf, tmp_path)

    shapes = read_zipped_shapefile(zip_path)
    assert len(shapes) == 1
    assert shapes[0].attributes["NAME"] == "Site A"
    wkt = shape_to_wkt(shapes[0], "MULTIPOLYGON")
    assert wkt.startswith("POLYGON((127.0 37.0")


def test_read_standalone_shapefile_with_sibling_dbf(tmp_path):
    shp_path = tmp_path / "sites.SHP"
    shp_path.write_bytes(
        _build_shp(
            SHAPE_TYPE_POLYGON,
            _polygon_record([(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01)]),
        )
    )
    # Use a lower-case sidecar to cover case-insensitive extension discovery.
    (tmp_path / "sites.dbf").write_bytes(_build_dbf("NAME", "Standalone"))

    shapes = read_shapefile(str(shp_path))
    assert len(shapes) == 1
    assert shapes[0].attributes["NAME"] == "Standalone"


def test_shapefile_dbf_encoding_can_be_selected(tmp_path):
    shp_path = tmp_path / "korean.shp"
    shp_path.write_bytes(
        _build_shp(
            SHAPE_TYPE_POLYGON,
            _polygon_record([(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01)]),
        )
    )
    (tmp_path / "korean.dbf").write_bytes(_build_dbf("NAME", "식물관찰", "cp949"))

    cp949_shapes = read_shapefile(str(shp_path), "cp949")
    utf8_shapes = read_shapefile(str(shp_path), "utf-8")
    assert cp949_shapes[0].attributes["NAME"] == "식물관찰"
    assert utf8_shapes[0].attributes["NAME"] != "식물관찰"


def test_read_point_shapefile(tmp_path):
    shp = _build_shp(SHAPE_TYPE_POINT, _point_record(127.005, 37.005))
    dbf = _build_dbf("NAME", "Plot A-1")
    zip_path = _zip_of(shp, dbf, tmp_path)

    shapes = read_zipped_shapefile(zip_path)
    assert len(shapes) == 1
    wkt = shape_to_wkt(shapes[0], "POINT")
    assert wkt == "POINT(127.005 37.005)"


def test_missing_shp_component_raises_build_error(tmp_path):
    zip_path = tmp_path / "broken.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("sites.dbf", _build_dbf("NAME", "x"))
    with pytest.raises(BuildError):
        read_zipped_shapefile(str(zip_path))


def test_not_a_zip_file_raises_build_error(tmp_path):
    bogus = tmp_path / "not_a_zip.zip"
    bogus.write_bytes(b"this is not a zip file")
    with pytest.raises(BuildError):
        read_zipped_shapefile(str(bogus))
