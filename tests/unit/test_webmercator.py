"""Pure-logic tests for qfield_builder.ui.webmercator (no QApplication needed)."""
from __future__ import annotations

import pytest

from qfield_builder.ui import webmercator


@pytest.mark.parametrize("zoom", [0, 1, 5, 10, 15, 18])
@pytest.mark.parametrize(
    "lon,lat",
    [
        (0.0, 0.0),
        (127.5, 36.5),
        (-179.9, -85.0),
        (179.9, 85.0),
        (127.024612, 37.532600),  # Seoul
        (0.001, 0.001),
    ],
)
def test_pixel_lonlat_round_trip(zoom, lon, lat):
    x, y = webmercator.lonlat_to_pixel(lon, lat, zoom)
    round_trip_lon, round_trip_lat = webmercator.pixel_to_lonlat(x, y, zoom)
    assert round_trip_lon == pytest.approx(lon, abs=1e-6)
    assert round_trip_lat == pytest.approx(lat, abs=1e-6)


def test_lonlat_to_pixel_x_increases_eastward():
    zoom = 8
    x1, _ = webmercator.lonlat_to_pixel(0.0, 0.0, zoom)
    x2, _ = webmercator.lonlat_to_pixel(10.0, 0.0, zoom)
    assert x2 > x1


def test_lonlat_to_pixel_y_increases_southward():
    zoom = 8
    _, y1 = webmercator.lonlat_to_pixel(0.0, 10.0, zoom)
    _, y2 = webmercator.lonlat_to_pixel(0.0, -10.0, zoom)
    assert y2 > y1


def test_lonlat_to_pixel_center_of_map_is_map_size_over_two():
    zoom = 4
    tile_size = 256
    map_size = tile_size * (2**zoom)
    x, y = webmercator.lonlat_to_pixel(0.0, 0.0, zoom, tile_size)
    assert x == pytest.approx(map_size / 2.0)
    assert y == pytest.approx(map_size / 2.0)


def test_higher_zoom_doubles_pixel_scale():
    lon, lat = 30.0, 20.0
    x_low, y_low = webmercator.lonlat_to_pixel(lon, lat, 5)
    x_high, y_high = webmercator.lonlat_to_pixel(lon, lat, 6)
    # Going up one zoom level doubles the map size, and therefore (for a fixed lon/lat that is
    # not the exact center of the projection) roughly doubles its pixel coordinates.
    assert x_high == pytest.approx(x_low * 2.0, rel=1e-9)


def test_custom_tile_size_is_respected():
    lon, lat, zoom = 45.0, 10.0, 6
    x_256, y_256 = webmercator.lonlat_to_pixel(lon, lat, zoom, tile_size=256)
    x_512, y_512 = webmercator.lonlat_to_pixel(lon, lat, zoom, tile_size=512)
    assert x_512 == pytest.approx(x_256 * 2.0)
    assert y_512 == pytest.approx(y_256 * 2.0)
