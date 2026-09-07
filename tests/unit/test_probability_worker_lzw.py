"""Focused executable checks for the TIFF/LZW probability worker decoder."""
from __future__ import annotations

import base64
import json
import struct
import subprocess
from pathlib import Path

import pytest

from qfield_builder import qml_plugin


def _pack_msb(codes: list[tuple[int, int]]) -> list[int]:
    bits: list[int] = []
    for value, width in codes:
        bits.extend((value >> shift) & 1 for shift in range(width - 1, -1, -1))
    packed: list[int] = []
    for start in range(0, len(bits), 8):
        byte = 0
        for bit in bits[start : start + 8]:
            byte = (byte << 1) | bit
        packed.append(byte << (8 - min(8, len(bits) - start)))
    return packed


def _encode_msb_lzw(payload: bytes) -> list[int]:
    dictionary = {bytes([value]): value for value in range(256)}
    next_code, width = 258, 9
    codes: list[tuple[int, int]] = [(256, width)]
    current = b""
    for value in payload:
        candidate = current + bytes([value])
        if candidate in dictionary:
            current = candidate
            continue
        codes.append((dictionary[current], width))
        dictionary[candidate] = next_code
        next_code += 1
        if next_code == (1 << width) and width < 12:
            width += 1
        current = bytes([value])
    if current:
        codes.append((dictionary[current], width))
    codes.append((257, width))
    return _pack_msb(codes)


def _run_worker_value(source: str, mode: str, value: object) -> object:
    script = """
const vm = require('vm');
const source = Buffer.from(process.argv[1], 'base64').toString('utf8');
const mode = process.argv[2];
const value = JSON.parse(process.argv[3]);
const context = { WorkerScript: { sendMessage() {} } };
vm.createContext(context);
vm.runInContext(source + '\\nthis.__lzw = lzw; this.__sample = sample;', context);
process.stdout.write(JSON.stringify(mode === 'lzw'
  ? context.__lzw(value)
  : context.__sample(value)));
"""
    completed = subprocess.run(
        [
            "node",
            "-e",
            script,
            base64.b64encode(source.encode()).decode(),
            mode,
            json.dumps(value),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _small_lzw_tiff(second_value=0.75) -> bytes:
    # Two little-endian float32 pixels: 0.25 and 0.75.  The compressed strip is
    # intentionally encoded MSB-first, as required by TIFF 6.0 LZW.
    pixels = struct.pack("<ff", 0.25, second_value)
    compressed = bytes(_encode_msb_lzw(pixels))
    ifd_offset = 8
    entry_count = 12
    ifd_size = 2 + entry_count * 12 + 4
    strip_offset = ifd_offset + ifd_size
    scale_offset = strip_offset + len(compressed)
    tie_offset = scale_offset + 24
    entries = [
        (256, 4, 1, struct.pack("<I", 2)),
        (257, 4, 1, struct.pack("<I", 1)),
        (258, 3, 1, struct.pack("<H", 32) + b"\0\0"),
        (259, 3, 1, struct.pack("<H", 5) + b"\0\0"),
        (262, 3, 1, struct.pack("<H", 1) + b"\0\0"),
        (273, 4, 1, struct.pack("<I", strip_offset)),
        (277, 3, 1, struct.pack("<H", 1) + b"\0\0"),
        (278, 4, 1, struct.pack("<I", 1)),
        (279, 4, 1, struct.pack("<I", len(compressed))),
        (339, 3, 1, struct.pack("<H", 3) + b"\0\0"),
        (33550, 12, 3, struct.pack("<I", scale_offset)),
        (33922, 12, 6, struct.pack("<I", tie_offset)),
    ]
    ifd = struct.pack("<H", entry_count)
    for tag, kind, count, value in entries:
        ifd += struct.pack("<HHI", tag, kind, count) + value
    ifd += struct.pack("<I", 0)
    return b"II" + struct.pack("<H", 42) + struct.pack("<I", ifd_offset) + ifd + compressed + struct.pack(
        "<ddd", 1.0, 1.0, 0.0
    ) + struct.pack("<dddddd", 0.0, 0.0, 0.0, 128.0, 38.0, 0.0)


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        ([(256, 9), (65, 9), (66, 9), (258, 9), (260, 9), (257, 9)], "ABABABA"),
    ],
)
def test_worker_decodes_msb_first_kwkwk_stream(codes, expected):
    decoded = _run_worker_value(
        qml_plugin.PROBABILITY_WORKER_SCRIPT, "lzw", _pack_msb(codes)
    )
    assert bytes(decoded).decode() == expected


def test_worker_decodes_dynamic_width_msb_first_stream():
    payload = bytes(range(256)) * 8
    decoded = _run_worker_value(
        qml_plugin.PROBABILITY_WORKER_SCRIPT, "lzw", _encode_msb_lzw(payload)
    )
    assert bytes(decoded) == payload


def test_worker_samples_little_endian_float32_from_lzw_tiff():
    result = _run_worker_value(
        qml_plugin.PROBABILITY_WORKER_SCRIPT,
        "sample",
        {"bytes": list(_small_lzw_tiff()), "lon": 129.5, "lat": 37.5},
    )
    assert result == {"ok": True, "value": pytest.approx(0.75)}


@pytest.mark.parametrize("value", [-0.25, -0.00001, -12000, 0, 0.75, 1, -9999, 1.25])
def test_worker_clamps_negative_probability_but_preserves_nodata(value):
    result = _run_worker_value(
        qml_plugin.PROBABILITY_WORKER_SCRIPT, "sample",
        {"bytes": list(_small_lzw_tiff(value)), "lon": 129.5, "lat": 37.5},
    )
    if value == -9999 or value > 1:
        assert not result["ok"]
    else:
        assert result == {"ok": True, "value": pytest.approx(max(0, value))}


def test_real_bundled_tiff_matches_independent_rasterio_value():
    rasterio = pytest.importorskip("rasterio")
    raster = next(
        Path("storage/reference/rasters/bce_inverse_corrected_probability_maps").glob("*.tif"),
        None,
    )
    if raster is None:
        pytest.skip("bundled probability TIFFs are not present")
    with rasterio.open(raster) as dataset:
        values = dataset.read(1)
        valid = (values >= 0) & (values <= 1)
        rows, columns = valid.nonzero()
        if len(rows) == 0:
            pytest.skip("bundled TIFF has no valid probability cell")
        row, column = int(rows[0]), int(columns[0])
        lon, lat = dataset.xy(row, column)
        expected = float(values[row, column])
    result = _run_worker_value(
        qml_plugin.PROBABILITY_WORKER_SCRIPT,
        "sample",
        {"bytes": list(raster.read_bytes()), "lon": lon, "lat": lat},
    )
    assert result["ok"] is True
    assert result["value"] == pytest.approx(expected, rel=1e-5, abs=1e-7)
