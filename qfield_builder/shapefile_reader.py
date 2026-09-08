"""Minimal, dependency-free ESRI Shapefile (.shp/.dbf) reader.

Supports exactly what FR-QPB-025/026 needs: Point (shape type 1) and Polygon (shape type 5)
records, with attributes from the companion .dbf. Both standalone ``.shp`` files and ZIP bundles
are accepted. This is intentionally minimal (no Z/M shapes, no MultiPatch, no PolyLine) —
sufficient for site (Polygon) and plot (Point) uploads.
"""
from __future__ import annotations

import struct
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError

SHAPE_TYPE_POINT = 1
SHAPE_TYPE_POLYGON = 5
SUPPORTED_ENCODINGS = ("cp949", "utf-8")


def _normalize_encoding(encoding: str) -> str:
    normalized = str(encoding or "cp949").strip().lower().replace("_", "-")
    if normalized == "utf8":
        normalized = "utf-8"
    if normalized not in SUPPORTED_ENCODINGS:
        raise BuildError(
            "unsupported_encoding",
            "Shapefile 문자 인코딩은 CP949 또는 UTF-8만 선택할 수 있습니다.",
        )
    return normalized


@dataclass
class ShapeRecord:
    shape_type: int
    # For points: [(x, y)] with one element. For polygons: list of rings, each a list of (x, y).
    rings: list[list[tuple[float, float]]]
    attributes: dict


def _read_dbf(dbf_bytes: bytes, encoding: str = "cp949") -> list[dict]:
    encoding = _normalize_encoding(encoding)
    if len(dbf_bytes) < 32:
        raise BuildError("malformed_upload", "DBF 파일이 너무 짧아 올바르지 않습니다.")
    num_records = struct.unpack_from("<I", dbf_bytes, 4)[0]
    header_len = struct.unpack_from("<H", dbf_bytes, 8)[0]
    record_len = struct.unpack_from("<H", dbf_bytes, 10)[0]

    fields = []
    offset = 32
    while offset < header_len - 1 and dbf_bytes[offset] != 0x0D:
        name = dbf_bytes[offset : offset + 11].split(b"\x00")[0].decode(
            encoding, errors="replace"
        )
        field_type = chr(dbf_bytes[offset + 11])
        length = dbf_bytes[offset + 16]
        fields.append((name, field_type, length))
        offset += 32

    records = []
    body_offset = header_len
    for i in range(num_records):
        start = body_offset + i * record_len
        raw = dbf_bytes[start : start + record_len]
        if not raw or raw[0:1] == b"*":
            continue
        rec = {}
        pos = 1
        for name, field_type, length in fields:
            raw_value = raw[pos : pos + length].decode(encoding, errors="replace").strip()
            if field_type in ("N", "F"):
                try:
                    rec[name] = float(raw_value) if raw_value else None
                except ValueError:
                    rec[name] = None
            else:
                rec[name] = raw_value
            pos += length
        records.append(rec)
    return records


def _read_shp(shp_bytes: bytes) -> list[ShapeRecord]:
    if len(shp_bytes) < 100:
        raise BuildError("malformed_upload", "SHP 파일이 너무 짧아 올바르지 않습니다.")
    shapes = []
    offset = 100  # skip the fixed-length header
    while offset < len(shp_bytes):
        if offset + 8 > len(shp_bytes):
            break
        content_len_words = struct.unpack_from(">I", shp_bytes, offset + 4)[0]
        content_start = offset + 8
        content_len_bytes = content_len_words * 2
        shape_type = struct.unpack_from("<I", shp_bytes, content_start)[0]

        if shape_type == SHAPE_TYPE_POINT:
            x, y = struct.unpack_from("<dd", shp_bytes, content_start + 4)
            shapes.append(ShapeRecord(shape_type=shape_type, rings=[[(x, y)]], attributes={}))
        elif shape_type == SHAPE_TYPE_POLYGON:
            pos = content_start + 4 + 32  # skip bbox
            num_parts = struct.unpack_from("<I", shp_bytes, pos)[0]
            pos += 4
            num_points = struct.unpack_from("<I", shp_bytes, pos)[0]
            pos += 4
            parts = list(struct.unpack_from(f"<{num_parts}I", shp_bytes, pos))
            pos += 4 * num_parts
            points = []
            for _ in range(num_points):
                px, py = struct.unpack_from("<dd", shp_bytes, pos)
                points.append((px, py))
                pos += 16
            parts.append(num_points)
            rings = [points[parts[i] : parts[i + 1]] for i in range(len(parts) - 1)]
            shapes.append(ShapeRecord(shape_type=shape_type, rings=rings, attributes={}))
        else:
            shapes.append(ShapeRecord(shape_type=shape_type, rings=[], attributes={}))

        offset = content_start + content_len_bytes
    return shapes


def read_zipped_shapefile(zip_path: str, encoding: str = "cp949") -> list[ShapeRecord]:
    """E-QPB-004: malformed/incomplete shapefile uploads must raise a BuildError, not crash."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            shp_name = next((n for n in names if n.lower().endswith(".shp")), None)
            dbf_name = next((n for n in names if n.lower().endswith(".dbf")), None)
            if shp_name is None:
                raise BuildError(
                    "malformed_upload",
                    "업로드한 압축 Shapefile에 필수 구성 요소인 .shp 파일이 없습니다.",
                )
            shp_bytes = zf.read(shp_name)
            dbf_bytes = zf.read(dbf_name) if dbf_name else b""
    except zipfile.BadZipFile as exc:
        raise BuildError(
            "malformed_upload", "업로드한 파일이 올바른 zip 압축 파일이 아닙니다."
        ) from exc

    shapes = _read_shp(shp_bytes)
    attributes = _read_dbf(dbf_bytes, encoding) if dbf_bytes else [{} for _ in shapes]
    for shape, attrs in zip(shapes, attributes, strict=False):
        shape.attributes = attrs
    return shapes


def read_shapefile(shp_path: str, encoding: str = "cp949") -> list[ShapeRecord]:
    """Read a standalone ``.shp`` file and an optional sibling ``.dbf`` file.

    The companion DBF is discovered next to the selected SHP file (case-insensitively).  An SHP
    without a DBF is still valid and produces features with empty attributes, just like the ZIP
    upload path.
    """
    path = Path(shp_path)
    try:
        shp_bytes = path.read_bytes()
    except OSError as exc:
        raise BuildError("malformed_upload", f"SHP 파일을 읽을 수 없었습니다: {exc}") from exc
    dbf_path = path.with_suffix(".dbf")
    if not dbf_path.exists():
        dbf_path = next(
            (
                candidate
                for candidate in path.parent.iterdir()
                if candidate.stem.lower() == path.stem.lower()
                and candidate.suffix.lower() == ".dbf"
            ),
            dbf_path,
        )
    try:
        dbf_bytes = dbf_path.read_bytes() if dbf_path.exists() else b""
    except OSError as exc:
        raise BuildError("malformed_upload", f"DBF 파일을 읽을 수 없었습니다: {exc}") from exc

    shapes = _read_shp(shp_bytes)
    attributes = _read_dbf(dbf_bytes, encoding) if dbf_bytes else [{} for _ in shapes]
    for shape, attrs in zip(shapes, attributes, strict=False):
        shape.attributes = attrs
    return shapes


def ring_to_wkt(ring: list[tuple[float, float]]) -> str:
    coords = ", ".join(f"{x} {y}" for x, y in ring)
    return f"({coords})"


def preview_shapefile(path: str, encoding: str = "cp949", *, zipped=False, max_rows=50):
    """Read headers and a bounded attribute sample, never decode polygon coordinates.

    Full geometry validation still belongs to read_shapefile/the build pipeline.
    """
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1")
    encoding = _normalize_encoding(encoding)
    try:
        with ExitStack() as stack:
            if zipped:
                archive = stack.enter_context(zipfile.ZipFile(path))
                names = archive.namelist()
                shp_name = next(n for n in names if n.lower().endswith(".shp"))
                dbf_name = next((n for n in names if n.lower().endswith(".dbf")), None)
                shx_name = next((n for n in names
                                 if n.lower() == str(Path(shp_name).with_suffix(".shx"))
                                 .replace("\\", "/").lower()), None)
                shp = stack.enter_context(archive.open(shp_name))
                dbf = stack.enter_context(archive.open(dbf_name)) if dbf_name else None
                shp_size = archive.getinfo(shp_name).file_size
                shx_size = archive.getinfo(shx_name).file_size if shx_name else None
            else:
                source = Path(path)
                companions = {p.suffix.lower(): p for p in source.parent.iterdir()
                              if p.stem.lower() == source.stem.lower()}
                shp = stack.enter_context(source.open("rb"))
                dbf = (stack.enter_context(companions[".dbf"].open("rb"))
                       if ".dbf" in companions else None)
                shp_size = source.stat().st_size
                shx_size = companions[".shx"].stat().st_size if ".shx" in companions else None
            header = shp.read(100)
            if len(header) != 100 or struct.unpack_from(">I", header)[0] != 9994:
                raise ValueError("올바른 SHP 헤더가 아닙니다.")
            shape_type = struct.unpack_from("<I", header, 32)[0]
            geometry_type = {1: "POINT", 5: "POLYGON"}.get(shape_type)
            if geometry_type is None:
                raise ValueError(f"지원되지 않는 shapefile shape 유형입니다: {shape_type}")
            dbf_header = None
            dbf_count = None
            if dbf is not None:
                dbf_header = bytearray(dbf.read(32))
                if len(dbf_header) != 32:
                    raise ValueError("DBF 헤더가 너무 짧습니다.")
                dbf_count, header_len, record_len = struct.unpack_from("<IHH", dbf_header, 4)
                if header_len < 33 or record_len < 1:
                    raise ValueError("DBF 헤더 길이가 올바르지 않습니다.")
                dbf_header.extend(dbf.read(header_len - 32))
                if len(dbf_header) != header_len:
                    raise ValueError("DBF 헤더가 잘렸습니다.")
                struct.pack_into("<I", dbf_header, 4, 1)
            if shx_size is not None and shx_size >= 100 and (shx_size - 100) % 8 == 0:
                count = (shx_size - 100) // 8
            elif dbf_count is not None:
                count = dbf_count
            else:
                # ponytail: without DBF/SHX, ZIP seeking may decompress the stream; no coordinates
                # are materialized. Add an indexed metadata path only if this rare case matters.
                count = 0
                while shp.tell() < shp_size:
                    record = shp.read(8)
                    if len(record) != 8:
                        raise ValueError("SHP 레코드 헤더가 잘렸습니다.")
                    size = struct.unpack_from(">I", record, 4)[0] * 2
                    if size < 4 or shp.tell() + size > shp_size:
                        raise ValueError("SHP 레코드 길이가 올바르지 않습니다.")
                    shp.seek(size, 1)
                    count += 1
            samples = []
            if dbf_header is not None:
                for _ in range(dbf_count):
                    if len(samples) >= min(count, max_rows):
                        break
                    record = dbf.read(record_len)
                    if len(record) != record_len:
                        raise ValueError("DBF 레코드가 잘렸습니다.")
                    samples.extend(_read_dbf(bytes(dbf_header) + record, encoding))
            fields = list(samples[0]) if samples else []
            samples.extend({} for _ in range(min(count, max_rows) - len(samples)))
            return {"fields": fields, "geometry_type": geometry_type,
                    "feature_count": count, "sample_attributes": samples}
    except (OSError, ValueError, StopIteration, struct.error, zipfile.BadZipFile) as exc:
        raise BuildError(
            "malformed_upload", f"Shapefile 미리보기를 읽을 수 없습니다: {exc}"
        ) from exc


def shape_to_wkt(shape: ShapeRecord, expected_type: str) -> str:
    if shape.shape_type == SHAPE_TYPE_POINT:
        x, y = shape.rings[0][0]
        return f"POINT({x} {y})"
    if shape.shape_type == SHAPE_TYPE_POLYGON:
        rings_wkt = ", ".join(ring_to_wkt(r) for r in shape.rings)
        return f"POLYGON({rings_wkt})"
    raise BuildError(
        "malformed_upload",
        f"지원되지 않거나 인식할 수 없는 shapefile shape 유형입니다: {shape.shape_type}",
    )
