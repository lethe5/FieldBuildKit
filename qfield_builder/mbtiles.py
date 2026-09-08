"""MBTiles offline basemap generation (Section 11 of the specification).

Builds a standards-compliant MBTiles 1.3 SQLite file (metadata + tiles tables) directly via
:mod:`sqlite3` — no GDAL dependency required. Tile *acquisition* is delegated to a caller-supplied
``tile_fetcher`` callable, so the pure generation/packaging logic (DR-QPB-061, FR-QPB-084) is
testable independently of any real or fake network client; see :mod:`qfield_builder.vworld_tiles`
for the production VWorld downloader and the deterministic fake used by the acceptance tests.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from .errors import BuildCancelledError, OfflineOutputOverflowError
from .offline_estimate import OFFLINE_HARD_LIMIT_BYTES, tiles_by_zoom


class TileCoord(NamedTuple):
    z: int
    x: int
    y: int


def iter_tile_coords(bbox: dict, min_zoom: int, max_zoom: int):
    from .offline_estimate import _lat_to_tile_y, _lon_to_tile_x

    for z in range(min_zoom, max_zoom + 1):
        min_x = _lon_to_tile_x(bbox["min_lon"], z)
        max_x = _lon_to_tile_x(bbox["max_lon"], z)
        min_y = _lat_to_tile_y(bbox["max_lat"], z)
        max_y = _lat_to_tile_y(bbox["min_lat"], z)
        if min_x > max_x:
            min_x, max_x = max_x, min_x
        if min_y > max_y:
            min_y, max_y = max_y, min_y
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                yield TileCoord(z=z, x=x, y=y)


def _tms_row(y: int, z: int) -> int:
    """Convert an XYZ row to the TMS (MBTiles spec) row convention (Y flipped)."""
    return (2**z - 1) - y


def _create_mbtiles_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB
        );
        CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);
        """
    )


def build_mbtiles(
    output_path: str,
    bbox: dict,
    min_zoom: int,
    max_zoom: int,
    tile_fetcher: Callable[[int, int, int], bytes],
    name: str = "FieldBuild Kit offline basemap",
    hard_limit_bytes: int = OFFLINE_HARD_LIMIT_BYTES,
    should_cancel: Callable[[], bool] | None = None,
    provider: str = "VWorld",
    layer: str = "Base",
    on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """Download/write tiles into a temporary MBTiles file, then return coverage metadata.

    Raises :class:`qfield_builder.errors.BuildCancelledError` if `should_cancel()` becomes true,
    or :class:`qfield_builder.errors.OfflineOutputOverflowError` if the in-progress output would
    exceed `hard_limit_bytes` (FR-QPB-083/E-QPB-006) — in both cases, the partial temp file at
    `output_path` is removed before raising, so no incomplete deliverable is ever left behind.
    Provider errors raised by `tile_fetcher` (quota/auth/rate-limit) propagate unchanged after the
    same cleanup.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial_output = output.with_name(output.name + ".partial")
    for candidate in (output, partial_output):
        if candidate.exists():
            candidate.unlink()

    conn = sqlite3.connect(str(partial_output))
    try:
        _create_mbtiles_schema(conn)
        tile_count = 0
        total_bytes = 0
        try:
            for coord in iter_tile_coords(bbox, min_zoom, max_zoom):
                if should_cancel is not None and should_cancel():
                    raise BuildCancelledError()
                tile_bytes = tile_fetcher(coord.z, coord.x, coord.y)
                total_bytes += len(tile_bytes)
                if total_bytes > hard_limit_bytes:
                    raise OfflineOutputOverflowError(
                        "생성 중인 오프라인 배경지도가 1 GiB 한도를 초과하게 됩니다. 선택한 영역, "
                        "줌 범위, 또는 해상도를 줄인 뒤 다시 시도해 주세요."
                    )
                conn.execute(
                    "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) "
                    "VALUES (?, ?, ?, ?);",
                    (coord.z, coord.x, _tms_row(coord.y, coord.z), tile_bytes),
                )
                tile_count += 1
                if on_progress is not None:
                    try:
                        on_progress(
                            {
                                "phase": "basemap_download",
                                "completed_tiles": tile_count,
                            }
                        )
                    except Exception:  # noqa: BLE001 - heartbeat delivery is advisory only.
                        pass
        except BaseException:
            conn.close()
            if partial_output.exists():
                partial_output.unlink()
            raise

        bounds = f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
        metadata_rows = [
            ("name", name),
            ("format", "png"),
            ("bounds", bounds),
            ("minzoom", str(min_zoom)),
            ("maxzoom", str(max_zoom)),
            ("type", "baselayer"),
            ("version", "1.3"),
            ("description", "Offline VWorld-sourced basemap generated by FieldBuild Kit"),
            ("provider", provider),
            ("layer", layer),
            ("source_provider", provider),
            ("source_layer", layer),
        ]
        conn.executemany("INSERT INTO metadata (name, value) VALUES (?, ?);", metadata_rows)
        conn.commit()
    except BaseException:
        if partial_output.exists():
            partial_output.unlink()
        raise
    finally:
        conn.close()

    final_size = partial_output.stat().st_size
    if final_size > hard_limit_bytes:
        partial_output.unlink()
        raise OfflineOutputOverflowError(
            "생성된 오프라인 배경지도가 1 GiB 한도를 초과합니다. 선택한 영역, 줌 범위, 또는 "
            "해상도를 줄인 뒤 다시 시도해 주세요."
        )

    partial_output.replace(output)

    return {
        "tile_count": tile_count,
        "size_bytes": final_size,
        "tiles_by_zoom": tiles_by_zoom(bbox, min_zoom, max_zoom),
        "bounds": bounds,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
    }
