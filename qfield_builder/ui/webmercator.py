"""Pure lon/lat (EPSG:4326) <-> pixel Web Mercator (EPSG:3857) math.

Deliberately dependency-free (no PySide6, no PyQGIS) so it can be unit-tested without a
`QApplication` and without a QGIS runtime -- see the architectural constraint in Section 5.3 of
the specification (the PySide6 UI process must not need PyQGIS) and the sibling module
:mod:`qfield_builder.ui.map_canvas`, which is the only thing in this package that actually turns
this math into an interactive widget.

Uses the standard "Bing Maps tile system" formulation of spherical Web Mercator (the same tile
scheme VWorld's own documented WMTS/XYZ GetTile endpoints use, and the same one
:mod:`qfield_builder.offline_estimate` uses for tile numbering), parameterized by a `zoom` level
and a `tile_size` (default 256px, matching the 256x256 XYZ tile convention). `zoom` may be a
float here (unlike `offline_estimate`'s integer tile-index zoom) because the interactive canvas
supports continuous/smooth zooming, not just snapping to discrete tile-pyramid levels.

The two functions are exact inverses of each other for any latitude strictly between the poles
(mathematically undefined exactly at +/-90 degrees, so callers that need to invert arbitrary
input latitudes -- as opposed to merely projecting a known-valid lon/lat -- should keep away
from the poles, which is a non-issue for this application's real-world use: ecological survey
sites and offline-basemap extents are never located at the poles).
"""
from __future__ import annotations

import math

DEFAULT_TILE_SIZE = 256

# A latitude this close to the poles makes the spherical Mercator projection's `y` pixel value
# grow without bound (the projection is undefined exactly at +/-90 degrees). Clamping here keeps
# `lonlat_to_pixel` well-defined for any input latitude a caller might pass (e.g. from a mis-drawn
# click near the edge of the widget) without ever raising -- callers that need a hard validity
# check should do so themselves (e.g. via `qfield_builder.wkt.validate_geometry`).
_MAX_ABS_LATITUDE = 89.9


def lonlat_to_pixel(
    lon: float, lat: float, zoom: float, tile_size: int = DEFAULT_TILE_SIZE
) -> tuple[float, float]:
    """Project a WGS84 lon/lat to a global (world) pixel coordinate at the given zoom level.

    Pixel (0, 0) is the top-left corner of the whole map at that zoom; `x` increases eastward,
    `y` increases southward -- the same convention as `qfield_builder.offline_estimate`'s tile
    numbering and as on-screen widget pixel coordinates (so callers don't need to flip anything).
    """
    map_size = tile_size * (2.0**zoom)
    x = map_size * (lon + 180.0) / 360.0

    clamped_lat = max(-_MAX_ABS_LATITUDE, min(_MAX_ABS_LATITUDE, lat))
    sin_lat = math.sin(math.radians(clamped_lat))
    y = map_size * (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi))
    return x, y


def pixel_to_lonlat(
    x: float, y: float, zoom: float, tile_size: int = DEFAULT_TILE_SIZE
) -> tuple[float, float]:
    """Inverse of :func:`lonlat_to_pixel`: a global pixel coordinate back to WGS84 lon/lat."""
    map_size = tile_size * (2.0**zoom)
    lon = x / map_size * 360.0 - 180.0
    n = math.pi - (2.0 * math.pi * y) / map_size
    lat = math.degrees(math.atan(math.sinh(n)))
    return lon, lat
