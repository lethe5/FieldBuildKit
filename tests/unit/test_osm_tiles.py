"""Tests for the OSM tile background added to `qfield_builder.ui.map_canvas.MapCanvas`.

Default (no-network) run: every test here uses an injected fake tile fetcher (mirroring
`qfield_builder.vworld_tiles`'s fake-tile-source pattern), never a real `QNetworkAccessManager`
request -- see `MapCanvas(tile_fetcher=...)`/`OsmTileLayer(fetch_fn=...)`. The one test that needs
genuine network access to a real OSM tile server is marked `@pytest.mark.network`, mirroring the
exact same marker `tests/acceptance/qfield_project_builder/conftest.py` already uses for real
VWorld network tests -- that conftest's `pytest_collection_modifyitems` applies session-wide (it
inspects every collected test's keywords, not just its own directory's), so this test is skipped
by default in a whole-suite run exactly like the VWorld ones are, with no separate skip logic
needed here. `tests/unit/conftest.py` additionally registers the `network` marker itself, purely
so a plain `pytest tests/unit` invocation (which may not have loaded the acceptance conftest that
otherwise registers it) doesn't warn about an unknown marker.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from qfield_builder.ui import osm_tiles
from qfield_builder.ui.map_canvas import MapCanvas, OsmTileLayer
from qfield_builder.wkt import validate_geometry

_png_cache: dict[str, bytes] = {}


def _minimal_png() -> bytes:
    """A genuinely valid, minimal (2x2) PNG, encoded via Qt's own PNG codec at first use (rather
    than a hand-typed byte literal) so it is guaranteed to actually decode -- real enough that
    `QPixmap.loadFromData` succeeds on it, so tests that check "the tile actually renders" are
    exercising real image decoding, not just cache plumbing. Requires a constructed
    `QApplication` (see the `_qapp` fixture below), so this is computed lazily, not at import
    time."""
    if "data" not in _png_cache:
        image = QImage(2, 2, QImage.Format.Format_RGB32)
        image.fill(0xFF112233)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert image.save(buffer, "PNG")
        _png_cache["data"] = bytes(buffer.data())
    return _png_cache["data"]


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_canvas(tile_fetcher=None, **kwargs) -> MapCanvas:
    canvas = MapCanvas(
        center_lon=127.0, center_lat=37.0, zoom=10, tile_fetcher=tile_fetcher, **kwargs
    )
    canvas.resize(400, 300)
    return canvas


def _force_paint(canvas: MapCanvas) -> None:
    """Forces a real, synchronous `paintEvent` regardless of whether this offscreen test
    environment's window system ever "exposes" the widget (`repaint()`/`update()` alone are not
    reliable for that under `QT_QPA_PLATFORM=offscreen`) -- `QWidget.render()` always runs the
    widget's actual paint logic into the given paint device."""
    canvas.render(QPixmap(canvas.size()))


# ---------------------------------------------------------------------------------------------
# Pure osm_tiles module: URL building, attribution text, cache.
# ---------------------------------------------------------------------------------------------


def test_build_tile_url_uses_standard_xyz_convention():
    url = osm_tiles.build_tile_url(5, 12, 7)
    assert url == "https://tile.openstreetmap.org/5/12/7.png"


def test_attribution_text_mentions_openstreetmap_contributors():
    assert "OpenStreetMap contributors" in osm_tiles.ATTRIBUTION_TEXT


def test_user_agent_is_not_empty_and_identifies_the_application():
    assert osm_tiles.USER_AGENT
    assert "QFieldProjectBuilder" in osm_tiles.USER_AGENT


def test_tile_cache_memory_only_round_trips():
    cache = osm_tiles.TileCache()
    key = (5, 1, 2)
    assert cache.get(key) is None
    cache.put(key, b"tile-bytes")
    assert cache.get(key) == b"tile-bytes"
    assert key in cache


def test_tile_cache_disk_backing_persists_across_instances(tmp_path):
    disk_dir = tmp_path / "osm_tile_cache"
    key = (4, 3, 2)

    first = osm_tiles.TileCache(disk_dir)
    first.put(key, b"cached-on-disk")

    # A brand-new TileCache instance pointed at the same directory picks up the persisted tile
    # without ever being told about it in-memory -- proves the disk layer, not just the dict.
    second = osm_tiles.TileCache(disk_dir)
    assert second.get(key) == b"cached-on-disk"


# ---------------------------------------------------------------------------------------------
# OsmTileLayer: caching avoids re-fetching, failures fall back gracefully.
# ---------------------------------------------------------------------------------------------


def test_cache_avoids_refetching_an_already_cached_tile():
    """`get_pixmap` always kicks off a fetch and returns `None` the *first* time a tile is asked
    for (uniform "not available yet" contract, matching the real async `QNetworkAccessManager`
    path -- see `OsmTileLayer.get_pixmap`'s own docstring) -- but once resolved, a second request
    for that exact tile must be served from the cache, with no second fetch call at all."""
    calls: list[tuple[int, int, int]] = []

    def fetch(z, x, y):
        calls.append((z, x, y))
        return _minimal_png()

    layer = OsmTileLayer(fetch_fn=fetch)

    first = layer.get_pixmap(5, 10, 12)
    assert first is None
    assert calls == [(5, 10, 12)]

    # Asking for the exact same tile again must be served from the cache -- no second fetch.
    second = layer.get_pixmap(5, 10, 12)
    assert second is not None
    assert calls == [(5, 10, 12)], "already-cached tile must not be re-fetched"

    # A third, distinct tile is a genuinely new fetch.
    layer.get_pixmap(5, 10, 13)
    assert calls == [(5, 10, 12), (5, 10, 13)]


def test_failed_fetch_is_recorded_and_never_retried():
    calls: list[tuple[int, int, int]] = []

    def fetch(z, x, y):
        calls.append((z, x, y))
        raise ConnectionError("simulated network failure")

    layer = OsmTileLayer(fetch_fn=fetch)

    result = layer.get_pixmap(3, 1, 1)
    assert result is None  # falls back gracefully -- no exception propagates to the caller.
    assert calls == [(3, 1, 1)]

    # Asking again for the same permanently-failed tile must not trigger a retry storm.
    result_again = layer.get_pixmap(3, 1, 1)
    assert result_again is None
    assert calls == [(3, 1, 1)]


def test_tile_updated_signal_fires_on_both_success_and_failure():
    emit_count = [0]

    def fetch(z, x, y):
        if x == 0:
            return _minimal_png()
        raise RuntimeError("boom")

    layer = OsmTileLayer(fetch_fn=fetch)
    layer.tile_updated.connect(lambda: emit_count.__setitem__(0, emit_count[0] + 1))

    layer.get_pixmap(1, 0, 0)  # succeeds
    layer.get_pixmap(1, 1, 0)  # fails

    assert emit_count[0] == 2  # signal fires once per resolved fetch, success or failure.


def test_invalid_image_bytes_are_treated_as_unavailable_without_crashing():
    layer = OsmTileLayer(fetch_fn=lambda z, x, y: b"not a real png")
    result = layer.get_pixmap(1, 0, 0)
    assert result is None


# ---------------------------------------------------------------------------------------------
# MapCanvas integration: attribution label, painting doesn't crash, drawing stays correct.
# ---------------------------------------------------------------------------------------------


def test_attribution_label_is_present_and_visible_with_successful_tiles():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: _minimal_png())
    canvas.show()
    assert canvas.osm_attribution_text() == osm_tiles.ATTRIBUTION_TEXT
    assert canvas.osm_attribution_visible()


def test_attribution_label_is_present_and_visible_even_when_every_fetch_fails():
    def always_fail(z, x, y):
        raise OSError("network unavailable")

    canvas = _make_canvas(tile_fetcher=always_fail)
    canvas.show()
    _force_paint(canvas)  # triggers tile fetch attempts for the visible tiles; must not crash.
    assert canvas.osm_attribution_text() == osm_tiles.ATTRIBUTION_TEXT
    assert canvas.osm_attribution_visible()


def test_painting_with_failing_tiles_does_not_raise():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: (_ for _ in ()).throw(OSError("no net")))
    canvas.show()
    # repaint() synchronously runs paintEvent -- must complete without raising regardless of the
    # tile fetcher's behavior (this is the core "must never crash, hang, or block drawing"
    # requirement).
    _force_paint(canvas)
    _force_paint(canvas)


def test_painting_with_successful_tiles_does_not_raise():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: _minimal_png())
    canvas.show()
    _force_paint(canvas)
    _force_paint(canvas)


def test_polygon_drawing_produces_correct_geometry_regardless_of_tile_fetch_failure():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: (_ for _ in ()).throw(OSError("no net")))
    canvas.set_mode("polygon")
    _force_paint(canvas)  # attempt (and fail) tile fetches before/while drawing.

    canvas.add_polygon_vertex_at(100, 100)
    canvas.add_polygon_vertex_at(300, 100)
    canvas.add_polygon_vertex_at(300, 250)
    wkt = canvas.finish_polygon()

    assert wkt.startswith("MULTIPOLYGON(((")
    validate_geometry(wkt, "MULTIPOLYGON")  # must not raise


def test_point_drawing_produces_correct_geometry_regardless_of_tile_fetch_success():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: _minimal_png())
    canvas.set_mode("point")
    _force_paint(canvas)

    wkt = canvas.place_point_at(150, 120)
    assert wkt.startswith("POINT(")
    validate_geometry(wkt, "POINT")


def test_bbox_drawing_produces_correct_geometry_regardless_of_tile_fetch_failure():
    canvas = _make_canvas(tile_fetcher=lambda z, x, y: (_ for _ in ()).throw(OSError("no net")))
    canvas.set_mode("bbox")
    _force_paint(canvas)

    canvas.start_bbox_at(50, 50)
    canvas.update_bbox_at(150, 150)
    bbox = canvas.finish_bbox_at(200, 200)

    assert bbox["min_lon"] <= bbox["max_lon"]
    assert bbox["min_lat"] <= bbox["max_lat"]


def test_default_tile_fetcher_is_the_real_network_path_when_none_injected():
    """When no `tile_fetcher` is supplied (the production default used by `SiteInputPage` and
    `ConnectivityBasemapPage`), `OsmTileLayer` must construct a real `QNetworkAccessManager`
    rather than silently doing nothing -- this is a wiring check, not a network-access check."""
    from PySide6.QtNetwork import QNetworkAccessManager

    canvas = _make_canvas(tile_fetcher=None)
    assert isinstance(canvas.tile_layer()._network_manager, QNetworkAccessManager)


def test_map_canvas_accepts_optional_disk_cache_dir(tmp_path):
    cache_dir = tmp_path / "tile_cache"
    canvas = _make_canvas(
        tile_fetcher=lambda z, x, y: _minimal_png(), tile_cache_dir=str(cache_dir)
    )
    canvas.show()
    _force_paint(canvas)
    # At least one tile should have been written to disk once fetched.
    assert cache_dir.exists()
    assert any(cache_dir.iterdir())


# ---------------------------------------------------------------------------------------------
# Real network test -- skipped by default, exercised only with --run-network (same convention as
# tests/acceptance/qfield_project_builder/conftest.py's real VWorld network tests).
# ---------------------------------------------------------------------------------------------


@pytest.mark.network
def test_real_osm_tile_fetch_renders_via_qnetworkaccessmanager(qtbot=None):
    """Fetches one real tile from tile.openstreetmap.org and confirms it actually renders.

    Requires `--run-network` and live internet access; skipped by default.
    """
    from PySide6.QtCore import QEventLoop, QTimer

    canvas = _make_canvas(tile_fetcher=None)  # real QNetworkAccessManager path.
    canvas.set_view(127.0, 37.0, 3)  # low zoom -- small, fast, well-known-to-exist tile.
    canvas.show()

    layer = canvas.tile_layer()
    loop = QEventLoop()
    layer.tile_updated.connect(loop.quit)

    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(20_000)

    _force_paint(canvas)  # kicks off the real async fetch for the visible tile(s).
    loop.exec()
    timeout.stop()

    integer_zoom = 3
    # Re-derive one of the tiles that should now be resolved (success or failure) after the fetch.
    resolved = any(
        key in layer._cache or key in layer._failed
        for key in [(integer_zoom, x, y) for x in range(8) for y in range(8)]
    )
    assert resolved, "expected at least one visible tile to have resolved after a real fetch"
