"""Offline-basemap tile-count/size estimation (FR-QPB-081/082, DR-QPB-060).

Tile numbering follows the standard slippy-map / Web Mercator (EPSG:3857) XYZ scheme, which is
the scheme VWorld's own documented WMTS/XYZ GetTile endpoints use (FR-QPB-072).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MIB = 1024 * 1024
GIB = 1024 * MIB
OFFLINE_PREGENERATION_THRESHOLD_BYTES = 900 * MIB  # DR-QPB-060
OFFLINE_HARD_LIMIT_BYTES = 1 * GIB  # DR-QPB-060

# Conservative safety multiplier applied atop the representative sample, standing in for "a
# conservative percentile ... rather than only an average" (FR-QPB-082) — since the acceptance
# test seam supplies a single representative_tile_bytes value rather than a distribution, this
# multiplier is the mechanism that keeps the estimate conservative.
SAFETY_MULTIPLIER = 1.15

# The default `representative_tile_bytes` sample size for real VWorld PNG tiles, used both by the
# actual build pipeline (`qfield_builder.build._representative_tile_bytes`) and by the wizard UI's
# live pre-generation size estimate (`qfield_builder.ui.wizard.ConnectivityBasemapPage`), so the
# number the user sees before building and the number the build itself uses can never drift apart.
DEFAULT_REPRESENTATIVE_TILE_BYTES = 15000.0


@dataclass(frozen=True)
class Bbox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


def _lon_to_tile_x(lon: float, zoom: int) -> int:
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    return max(0, min(n - 1, x))


def _lat_to_tile_y(lat: float, zoom: int) -> int:
    n = 2**zoom
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, y))


def tiles_for_zoom(bbox: dict, zoom: int) -> int:
    """Number of XYZ tiles intersecting `bbox` at a single zoom level."""
    min_x = _lon_to_tile_x(bbox["min_lon"], zoom)
    max_x = _lon_to_tile_x(bbox["max_lon"], zoom)
    # Latitude tile-y numbering is inverted (increases southward), so max_lat -> smaller y.
    min_y = _lat_to_tile_y(bbox["max_lat"], zoom)
    max_y = _lat_to_tile_y(bbox["min_lat"], zoom)
    if min_x > max_x:
        min_x, max_x = max_x, min_x
    if min_y > max_y:
        min_y, max_y = max_y, min_y
    return (max_x - min_x + 1) * (max_y - min_y + 1)


def total_tile_count(bbox: dict, min_zoom: int, max_zoom: int) -> int:
    return sum(tiles_for_zoom(bbox, z) for z in range(min_zoom, max_zoom + 1))


def tiles_by_zoom(bbox: dict, min_zoom: int, max_zoom: int) -> dict[int, int]:
    return {z: tiles_for_zoom(bbox, z) for z in range(min_zoom, max_zoom + 1)}


def estimate_offline_basemap_size(
    bbox: dict, min_zoom: int, max_zoom: int, representative_tile_bytes: float
) -> dict:
    """Wraps FR-QPB-081/082/DR-QPB-060. See HARNESS_CONTRACT.md's exact return shape."""
    tile_count = total_tile_count(bbox, min_zoom, max_zoom)
    estimated_bytes = int(math.ceil(tile_count * representative_tile_bytes * SAFETY_MULTIPLIER))
    return {
        "tile_count": tile_count,
        "estimated_bytes": estimated_bytes,
        "exceeds_pregeneration_threshold": estimated_bytes > OFFLINE_PREGENERATION_THRESHOLD_BYTES,
    }
