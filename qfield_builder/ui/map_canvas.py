"""An interactive drawing canvas for site/plot/bbox input on a map (FR-QPB-025, FR-QPB-080).

Background imagery -- OpenStreetMap tiles, graticule fallback: per direct stakeholder feedback
from using the packaged app (drawing a real site boundary with *no* geographic context at all was
found genuinely hard to use), this widget now renders real OpenStreetMap XYZ raster tiles
(:mod:`qfield_builder.ui.osm_tiles`) as its background, for whatever tiles are currently in view.
This is a **visual aid only**: fetched tile imagery is never written into, or referenced by, the
generated QField project output, and is entirely separate from the application's actual
offline/online VWorld basemap-generation pipeline (Sections 10/11) -- this widget never touches
that pipeline, and that pipeline never touches this module.

The plain lon/lat graticule (grid lines with coordinate labels) this widget always painted is kept
as an always-drawn base layer underneath the tiles, rather than removed: it is the fallback for
any tile that hasn't loaded yet or failed to fetch (no network, a timeout, a non-200 response,
...), so this widget's actual job -- per FR-QPB-025/080, producing a geometrically correct WGS84
geometry or bbox -- never depends on tile availability, and drawing remains 100% correct and
usable with zero network access. See :class:`OsmTileLayer` for the async fetch/cache/fallback
mechanics.

Only PySide6/Qt (including `QtNetwork`, for the OSM tile fetch) and
:mod:`qfield_builder.ui.webmercator`/:mod:`qfield_builder.ui.osm_tiles` are used here -- never
`qgis.*` -- per the Section 5.3 process-separation constraint (the PySide6 UI process must not
need PyQGIS).

Supports three independent drawing modes, each producing WGS84 (EPSG:4326) output:

- ``"polygon"``: click to add vertices; an explicit "finish" (double-click, or calling
  :meth:`MapCanvas.finish_polygon` from a "Finish shape" button) closes the ring and returns a
  ``MULTIPOLYGON`` WKT string (this application's site/community geometry type). A finished
  polygon can then either be re-opened for further editing (calling `add_polygon_vertex_at` again,
  the pre-existing behavior), or committed into a per-session list of independent, separately
  finished polygons via :meth:`MapCanvas.commit_finished_polygon`, which also clears all
  in-progress/finished state so a brand-new, unrelated polygon can be started next without
  disturbing any previously committed one (FR-QPB-129/Decision Log D-75/D-79 -- multiple, separate
  polygons in one drawing session, each later individually named by `qfield_builder.ui.wizard`'s
  `SiteInputPage`). See :attr:`MapCanvas.finished_polygons`.
- ``"point"``: a single click places a point and returns a ``POINT`` WKT string.
- ``"bbox"``: click-and-drag draws a rectangle and returns a
  ``{"min_lon", "min_lat", "max_lon", "max_lat"}`` dict (the same shape
  :func:`qfield_builder.offline_estimate.estimate_offline_basemap_size` and
  :mod:`qfield_builder.build` expect).

There is also a ``"pan"`` mode (left-button mouse-drag panning while ``self._mode == "pan"``) and
scroll-wheel zooming, the latter active regardless of drawing mode, for navigating the view
before/while drawing. **Bug 2 fix (FR-QPB-025/Decision Log D-24):** additionally, a right-button
mouse drag always pans -- regardless of ``self._mode`` -- so a user can recenter the view while in
the middle of placing polygon vertices or dragging a bbox, without losing that in-progress
drawing and without needing to switch modes.

Every drawing operation is exposed as a plain method (`add_polygon_vertex_at`, `finish_polygon`,
`place_point_at`, `start_bbox_at`/`update_bbox_at`/`finish_bbox_at`) taking *widget-local pixel*
coordinates, in addition to being wired to the real Qt mouse event handlers below -- so tests (and
any future keyboard/accessibility entry point) can drive the widget deterministically without
depending on how reliably a given test environment delivers synthetic mouse events.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap, QPolygonF, QWheelEvent
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QLabel, QWidget

from . import osm_tiles, webmercator

# A real VWorld/XYZ tile pyramid realistically tops out somewhere in the high teens/low twenties
# (VWorld's own documented layers commonly support up to z=19-20 depending on layer/area). 0..20
# is used as the practical, documented bound for both this widget's own live view zoom and (via
# `qfield_builder.ui.wizard`'s reuse of these same constants) the offline-basemap min/max zoom
# spin boxes -- comfortably covering real usable VWorld detail without inviting a zoom selection
# that would need enormous, clearly-unreasonable tile counts.
MIN_ZOOM = 0
MAX_ZOOM = 20

DEFAULT_TILE_SIZE = 256

MODE_PAN = "pan"
MODE_POLYGON = "polygon"
MODE_POINT = "point"
MODE_BBOX = "bbox"
_VALID_MODES = (MODE_PAN, MODE_POLYGON, MODE_POINT, MODE_BBOX)


def _nice_grid_step(span_degrees: float) -> float:
    """A "nice" degree step for graticule lines, aiming for ~5-8 lines across `span_degrees`."""
    if span_degrees <= 0:
        return 0.001
    steps = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 45, 90)
    target = span_degrees / 6.0
    for step in steps:
        if step >= target:
            return step
    return steps[-1]


class OsmTileLayer(QObject):
    """Fetches, caches, and hands out already-fetched OSM tile pixmaps for a `MapCanvas`.

    :meth:`get_pixmap` never blocks the caller: it returns the cached pixmap immediately if one
    is already available, otherwise it kicks off an asynchronous fetch (unless one for that exact
    tile is already in flight or has already permanently failed this session) and returns `None`
    right away -- so `MapCanvas._paint_osm_tiles` always has a well-defined "not available yet"
    outcome to fall back to the graticule for, and a repaint is only ever triggered later, via
    `tile_updated`, once the fetch actually resolves (success or failure).

    Two fetch mechanisms:

    - Production default (`fetch_fn=None`): a real `QNetworkAccessManager` GET request per tile,
      with a real, policy-compliant identifying `User-Agent` (:data:`osm_tiles.USER_AGENT`) and a
      bounded transfer timeout, so a stalled request can never hang the widget.
    - Test seam (`fetch_fn` supplied): a synchronous, injectable `Callable[[int, int, int],
      bytes]` standing in for the network, mirroring
      :func:`qfield_builder.vworld_tiles.make_fake_tile_fetcher`'s fake-tile-source pattern --
      used by this project's own tests so the default (no-network) test run never depends on live
      network access.

    Every outcome (success, HTTP/network error, empty body, or a test double raising) is recorded
    so a given `(z, x, y)` is fetched at most once per `OsmTileLayer` lifetime -- satisfying
    OpenStreetMap's tile usage policy's caching expectation and avoiding any repeated-retry
    request storm against a tile that is genuinely unreachable.
    """

    tile_updated = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        cache: osm_tiles.TileCache | None = None,
        fetch_fn: Callable[[int, int, int], bytes] | None = None,
    ):
        super().__init__(parent)
        self._cache = cache if cache is not None else osm_tiles.TileCache()
        self._fetch_fn = fetch_fn
        # The real QNetworkAccessManager is only constructed for the real (non-test-double) path
        # -- tests that inject `fetch_fn` never need a Qt network stack at all.
        self._network_manager: QNetworkAccessManager | None = (
            None if fetch_fn is not None else QNetworkAccessManager(self)
        )
        self._pending: set[osm_tiles.TileKey] = set()
        self._failed: set[osm_tiles.TileKey] = set()

    def get_pixmap(self, z: int, x: int, y: int) -> QPixmap | None:
        """The cached pixmap for tile (z, x, y), or `None` (having kicked off a fetch) if it
        isn't available right now -- never blocks, never raises."""
        key = (z, x, y)
        data = self._cache.get(key)
        if data is not None:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                return pixmap
            return None  # Cached bytes didn't decode as an image -- treat as unavailable.
        if key in self._pending or key in self._failed:
            return None
        self._start_fetch(key)
        return None

    def _start_fetch(self, key: osm_tiles.TileKey) -> None:
        self._pending.add(key)
        z, x, y = key

        if self._fetch_fn is not None:
            try:
                data = self._fetch_fn(z, x, y)
            except Exception:  # noqa: BLE001 - any fetch failure falls back to the graticule.
                self._pending.discard(key)
                self._failed.add(key)
                self.tile_updated.emit()
                return
            self._pending.discard(key)
            self._cache.put(key, data)
            self.tile_updated.emit()
            return

        request = QNetworkRequest(QUrl(osm_tiles.build_tile_url(z, x, y)))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, osm_tiles.USER_AGENT)
        request.setTransferTimeout(15_000)  # never let a stalled request hang indefinitely.
        assert self._network_manager is not None
        reply = self._network_manager.get(request)
        reply.finished.connect(lambda: self._on_reply_finished(reply, key))

    def _on_reply_finished(self, reply: QNetworkReply, key: osm_tiles.TileKey) -> None:
        self._pending.discard(key)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._failed.add(key)
                return
            data = bytes(reply.readAll())
            if not data:
                self._failed.add(key)
                return
            self._cache.put(key, data)
        finally:
            reply.deleteLater()
            self.tile_updated.emit()


class MapCanvas(QWidget):
    """A pannable/zoomable OSM-tile (graticule-fallback) map that can draw a polygon, point, or
    bbox -- see this module's own docstring for the tile/graticule background design."""

    polygon_drawn = Signal(str)
    point_drawn = Signal(str)
    bbox_drawn = Signal(dict)

    def __init__(
        self,
        parent=None,
        *,
        center_lon: float = 127.5,
        center_lat: float = 36.5,
        zoom: float = 7,
        tile_fetcher: Callable[[int, int, int], bytes] | None = None,
        tile_cache_dir: str | None = None,
    ):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMouseTracking(True)

        self._center_lon = center_lon
        self._center_lat = center_lat
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        self._mode = MODE_PAN

        self._vertices: list[tuple[float, float]] = []
        self._polygon_finished = False
        self.last_polygon_wkt: str | None = None

        # FR-QPB-129/Decision Log D-75/D-79: polygons committed via `commit_finished_polygon` in
        # this drawing session, in the order they were committed. `_finished_polygons` holds each
        # committed WKT string; `_finished_polygon_vertices` holds the matching raw vertex list
        # (parallel, same order, never containing the duplicated closing vertex) purely so
        # `_paint_drawing_overlay` can keep rendering them on screen without having to re-parse
        # WKT -- committing a new polygon never mutates an earlier, already-committed entry.
        self._finished_polygons: list[str] = []
        self._finished_polygon_vertices: list[list[tuple[float, float]]] = []

        self._point: tuple[float, float] | None = None
        self.last_point_wkt: str | None = None

        self._bbox_start: tuple[float, float] | None = None
        self._bbox_end: tuple[float, float] | None = None
        self._bbox_dragging = False
        self.last_bbox: dict | None = None

        self._panning = False
        self._pan_last_pos: QPointF | None = None

        # --- OSM tile background (visual aid only -- see module docstring) -------------------
        self._tile_layer = OsmTileLayer(
            self, cache=osm_tiles.TileCache(tile_cache_dir), fetch_fn=tile_fetcher
        )
        self._tile_layer.tile_updated.connect(self.update)

        # ODbL-required "(c) OpenStreetMap contributors" attribution -- always visible whenever
        # OSM tiles are the active background (i.e. always, for this widget, since the graticule
        # is only ever a same-widget *fallback*, not a separate non-OSM mode a user can pick).
        self._osm_attribution_label = QLabel(osm_tiles.ATTRIBUTION_TEXT, self)
        self._osm_attribution_label.setStyleSheet(
            "background-color: rgba(255, 255, 255, 190); color: black; padding: 1px 4px; "
            "font-size: 10px;"
        )
        self._osm_attribution_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._position_attribution_label()

    # ------------------------------------------------------------------ view state -----------

    def set_view(self, center_lon: float, center_lat: float, zoom: float) -> None:
        self._center_lon = center_lon
        self._center_lat = center_lat
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def center(self) -> tuple[float, float]:
        return self._center_lon, self._center_lat

    # ------------------------------------------------------------------- OSM tile background --

    def tile_layer(self) -> OsmTileLayer:
        """The `OsmTileLayer` backing this canvas's background (fetch/cache/fallback state)."""
        return self._tile_layer

    def osm_attribution_text(self) -> str:
        """The exact text of the always-visible ODbL attribution label."""
        return self._osm_attribution_label.text()

    def osm_attribution_visible(self) -> bool:
        """Whether the ODbL attribution label is currently visible (always True once shown --
        OSM tiles are this widget's only background, the graticule is just their fallback)."""
        return self._osm_attribution_label.isVisible()

    def _position_attribution_label(self) -> None:
        label = self._osm_attribution_label
        label.adjustSize()
        margin = 4
        label.move(margin, max(0, self.height() - label.height() - margin))
        label.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._position_attribution_label()

    def set_mode(self, mode: str) -> None:
        if mode not in _VALID_MODES:
            raise ValueError(f"Unsupported drawing mode: {mode!r}")
        self._mode = mode
        self.update()

    def mode(self) -> str:
        return self._mode

    def reset_drawing(self) -> None:
        """Clear any in-progress or finished (not-yet-committed) drawing in every mode (does not
        change the view). Deliberately does **not** clear polygons already committed this session
        via `commit_finished_polygon` -- mirroring `SiteInputPage`'s existing "지우기"/Clear button
        semantics (clearing a mistake in the *current* shape must never silently discard sites
        already finished and saved earlier in the same session). Use
        `clear_finished_polygons` to also clear those."""
        self._vertices = []
        self._polygon_finished = False
        self.last_polygon_wkt = None
        self._point = None
        self.last_point_wkt = None
        self._bbox_start = None
        self._bbox_end = None
        self._bbox_dragging = False
        self.last_bbox = None
        self.update()

    def clear_finished_polygons(self) -> None:
        """Discards every polygon committed this session via `commit_finished_polygon`, without
        touching any other in-progress/finished drawing state. A separate operation from
        `reset_drawing` on purpose -- see that method's own docstring."""
        self._finished_polygons = []
        self._finished_polygon_vertices = []
        self.update()

    # ------------------------------------------------------------- coordinate mapping --------

    def _center_pixel(self) -> tuple[float, float]:
        return webmercator.lonlat_to_pixel(
            self._center_lon, self._center_lat, self._zoom, DEFAULT_TILE_SIZE
        )

    def widget_to_lonlat(self, x: float, y: float) -> tuple[float, float]:
        cx, cy = self._center_pixel()
        px = cx + (x - self.width() / 2.0)
        py = cy + (y - self.height() / 2.0)
        return webmercator.pixel_to_lonlat(px, py, self._zoom, DEFAULT_TILE_SIZE)

    def lonlat_to_widget(self, lon: float, lat: float) -> tuple[float, float]:
        cx, cy = self._center_pixel()
        px, py = webmercator.lonlat_to_pixel(lon, lat, self._zoom, DEFAULT_TILE_SIZE)
        return px - cx + self.width() / 2.0, py - cy + self.height() / 2.0

    # ------------------------------------------------------- drawing-mode operations --------
    # Each of these takes widget-local pixel coordinates and is safe to call directly (from a
    # test, or from a future non-mouse input path) as well as from the Qt event handlers below.

    def add_polygon_vertex_at(self, x: float, y: float) -> None:
        # Placing a new vertex re-opens a previously-finished shape for further editing -- it
        # must go back to rendering as an open, in-progress polyline (not a closed ring) until
        # `finish_polygon` is called again.
        self._polygon_finished = False
        self._vertices.append(self.widget_to_lonlat(x, y))
        self.update()

    def finish_polygon(self) -> str:
        """Close the current polygon ring and return its WKT as ``MULTIPOLYGON(((...)))``.

        Raises :class:`ValueError` if fewer than 3 vertices have been placed -- a ring needs at
        least 3 distinct points to be a valid polygon (matching
        :func:`qfield_builder.wkt.validate_geometry`'s own minimum).
        """
        if len(self._vertices) < 3:
            raise ValueError("도형을 완성하려면 최소 3개의 점이 필요합니다.")
        ring = list(self._vertices)
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        coords = ", ".join(f"{lon} {lat}" for lon, lat in ring)
        wkt = f"MULTIPOLYGON((({coords})))"
        self.last_polygon_wkt = wkt
        self._polygon_finished = True
        self.update()
        self.polygon_drawn.emit(wkt)
        return wkt

    def is_polygon_finished(self) -> bool:
        """Whether the in-progress polygon has been finished (closed) -- used by
        :meth:`_paint_drawing_overlay` to decide whether to render an open polyline (still being
        drawn) or a genuinely closed ring (finished), and exposed here so tests can verify this
        state directly."""
        return self._polygon_finished

    @property
    def finished_polygons(self) -> list[str]:
        """Every polygon committed this session via `commit_finished_polygon`, in the order they
        were committed (FR-QPB-129/Decision Log D-75/D-79). Returns a fresh copy each time, so the
        caller mutating the returned list can never affect this widget's own internal state."""
        return list(self._finished_polygons)

    def commit_finished_polygon(self) -> str:
        """Commits the currently finished polygon (the shape most recently produced by
        `finish_polygon`) into `finished_polygons`, then clears all in-progress/finished polygon
        state so a brand-new, completely independent polygon can be started next -- without
        merging with, or in any way disturbing, any polygon already committed earlier this session
        (FR-QPB-129/Decision Log D-75/D-79). Unlike calling `add_polygon_vertex_at` again after
        `finish_polygon` (which re-opens the *same* shape for further editing, this widget's
        pre-existing behavior, unchanged by this method), this always starts a genuinely separate
        shape.

        Raises :class:`ValueError` if the current polygon has not been finished yet (call
        `finish_polygon` first).
        """
        if not self._polygon_finished or self.last_polygon_wkt is None:
            raise ValueError(
                "먼저 도형을 완성해야 합니다 ('도형 완성'을 클릭하거나 더블클릭하세요)."
            )
        self._finished_polygons.append(self.last_polygon_wkt)
        self._finished_polygon_vertices.append(list(self._vertices))
        self._vertices = []
        self._polygon_finished = False
        self.last_polygon_wkt = None
        self.update()
        return self._finished_polygons[-1]

    def place_point_at(self, x: float, y: float) -> str:
        lon, lat = self.widget_to_lonlat(x, y)
        self._point = (lon, lat)
        wkt = f"POINT({lon} {lat})"
        self.last_point_wkt = wkt
        self.point_drawn.emit(wkt)
        self.update()
        return wkt

    def start_bbox_at(self, x: float, y: float) -> None:
        lonlat = self.widget_to_lonlat(x, y)
        self._bbox_start = lonlat
        self._bbox_end = lonlat
        self._bbox_dragging = True
        self.update()

    def update_bbox_at(self, x: float, y: float) -> None:
        if not self._bbox_dragging:
            return
        self._bbox_end = self.widget_to_lonlat(x, y)
        self.update()

    def finish_bbox_at(self, x: float, y: float) -> dict:
        """Finish a bbox drag and return ``{"min_lon", "min_lat", "max_lon", "max_lat"}``.

        Raises :class:`ValueError` if no drag was ever started (:meth:`start_bbox_at` was not
        called first).
        """
        if self._bbox_start is None:
            raise ValueError("진행 중인 영역(bbox) 드래그가 없습니다.")
        self._bbox_end = self.widget_to_lonlat(x, y)
        (lon1, lat1), (lon2, lat2) = self._bbox_start, self._bbox_end
        bbox = {
            "min_lon": min(lon1, lon2),
            "min_lat": min(lat1, lat2),
            "max_lon": max(lon1, lon2),
            "max_lat": max(lat1, lat2),
        }
        self.last_bbox = bbox
        self._bbox_dragging = False
        self.bbox_drawn.emit(bbox)
        self.update()
        return bbox

    def pan_by_pixels(self, dx: float, dy: float) -> None:
        cx, cy = self._center_pixel()
        self._center_lon, self._center_lat = webmercator.pixel_to_lonlat(
            cx - dx, cy - dy, self._zoom, DEFAULT_TILE_SIZE
        )
        self.update()

    def zoom_by(self, steps: float) -> None:
        self.set_view(self._center_lon, self._center_lat, self._zoom + steps)

    # ------------------------------------------------------------------ Qt event handlers ----

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.RightButton:
            # Bug 2 fix (FR-QPB-025/Decision Log D-24): a secondary mouse button always pans,
            # regardless of `self._mode` -- mirroring `wheelEvent`'s existing "zoom works
            # regardless of mode" pattern -- so a user can always recenter the view without
            # disrupting an in-progress polygon/bbox drawing (never touches `_vertices`,
            # `_bbox_start`/`_bbox_end`, or `_bbox_dragging`).
            self._panning = True
            self._pan_last_pos = event.position()
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        pos = event.position()
        if self._mode == MODE_PAN:
            self._panning = True
            self._pan_last_pos = pos
        elif self._mode == MODE_POLYGON:
            self.add_polygon_vertex_at(pos.x(), pos.y())
        elif self._mode == MODE_POINT:
            self.place_point_at(pos.x(), pos.y())
        elif self._mode == MODE_BBOX:
            self.start_bbox_at(pos.x(), pos.y())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        pos = event.position()
        if self._panning and self._pan_last_pos is not None:
            # Covers both left-button drag in MODE_PAN and the mode-independent secondary-button
            # drag started in `mousePressEvent` above.
            dx = pos.x() - self._pan_last_pos.x()
            dy = pos.y() - self._pan_last_pos.y()
            self.pan_by_pixels(dx, dy)
            self._pan_last_pos = pos
        elif self._mode == MODE_BBOX and self._bbox_dragging:
            self.update_bbox_at(pos.x(), pos.y())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self._pan_last_pos = None
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        pos = event.position()
        if self._mode == MODE_PAN:
            self._panning = False
            self._pan_last_pos = None
        elif self._mode == MODE_BBOX and self._bbox_dragging:
            self.finish_bbox_at(pos.x(), pos.y())
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if self._mode == MODE_POLYGON:
            try:
                self.finish_polygon()
            except ValueError:
                pass  # Not enough vertices yet -- silently ignore the double-click.
        event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt override
        steps = event.angleDelta().y() / 120.0
        self.zoom_by(steps)
        event.accept()

    # ------------------------------------------------------------------------- painting -----

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002 - Qt override
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor(235, 240, 245))
            self._paint_graticule(painter)  # always drawn -- the fallback for any missing tile.
            self._paint_osm_tiles(painter)  # drawn on top wherever a tile is already available.
            self._paint_drawing_overlay(painter)
        finally:
            painter.end()

    def _paint_osm_tiles(self, painter: QPainter) -> None:
        """Draws every already-cached OSM tile visible in the current viewport over the
        graticule, kicking off (asynchronous, non-blocking) fetches for any visible tile that
        isn't cached yet. Tiles that fail to fetch, or simply haven't resolved yet, are left
        alone here -- the graticule painted just before this is already visible underneath them,
        which is this widget's entire offline/failure fallback."""
        integer_zoom = max(0, min(osm_tiles.OSM_MAX_TILE_ZOOM, round(self._zoom)))
        scale = 2.0 ** (self._zoom - integer_zoom)
        tile_size = DEFAULT_TILE_SIZE * scale
        n_tiles = 2**integer_zoom

        cx, cy = self._center_pixel()
        world_x0 = cx - self.width() / 2.0
        world_y0 = cy - self.height() / 2.0
        world_x1 = cx + self.width() / 2.0
        world_y1 = cy + self.height() / 2.0

        tile_x_min = math.floor((world_x0 / scale) / DEFAULT_TILE_SIZE)
        tile_x_max = math.floor((world_x1 / scale) / DEFAULT_TILE_SIZE)
        tile_y_min = math.floor((world_y0 / scale) / DEFAULT_TILE_SIZE)
        tile_y_max = math.floor((world_y1 / scale) / DEFAULT_TILE_SIZE)

        for tile_y in range(tile_y_min, tile_y_max + 1):
            if tile_y < 0 or tile_y >= n_tiles:
                continue  # Above the north pole or below the south pole -- no such tile.
            for tile_x in range(tile_x_min, tile_x_max + 1):
                wrapped_x = tile_x % n_tiles  # The tile grid wraps around the antimeridian.
                pixmap = self._tile_layer.get_pixmap(integer_zoom, wrapped_x, tile_y)
                if pixmap is None:
                    continue
                widget_x = tile_x * tile_size - world_x0
                widget_y = tile_y * tile_size - world_y0
                painter.drawPixmap(
                    QRectF(widget_x, widget_y, tile_size, tile_size),
                    pixmap,
                    QRectF(pixmap.rect()),
                )

    def _paint_graticule(self, painter: QPainter) -> None:
        lon0, lat0 = self.widget_to_lonlat(0, 0)
        lon1, lat1 = self.widget_to_lonlat(self.width(), self.height())
        min_lon, max_lon = min(lon0, lon1), max(lon0, lon1)
        min_lat, max_lat = min(lat0, lat1), max(lat0, lat1)
        step = _nice_grid_step(max(max_lon - min_lon, max_lat - min_lat))

        painter.setPen(QPen(QColor(180, 190, 200)))

        lon = math.floor(min_lon / step) * step
        while lon <= max_lon + step:
            x, _ = self.lonlat_to_widget(lon, min_lat)
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            painter.drawText(QPointF(x + 2, 12), f"{lon:.4g}")
            lon += step

        lat = math.floor(min_lat / step) * step
        while lat <= max_lat + step:
            _, y = self.lonlat_to_widget(min_lon, lat)
            painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
            painter.drawText(QPointF(2, max(y - 2, 12)), f"{lat:.4g}")
            lat += step

    def _paint_drawing_overlay(self, painter: QPainter) -> None:
        pen = QPen(QColor(200, 30, 30))
        pen.setWidth(2)

        if self._mode == MODE_POLYGON and self._finished_polygon_vertices:
            # AC-QPB-116: every polygon already committed this session must stay visibly present
            # (as a closed ring) while a new, separate one is drawn -- rendered in a distinct,
            # muted color so it's never confused with the actively-in-progress shape below.
            committed_pen = QPen(QColor(120, 120, 130))
            committed_pen.setWidth(2)
            painter.setPen(committed_pen)
            for vertices in self._finished_polygon_vertices:
                points = [QPointF(*self.lonlat_to_widget(lon, lat)) for lon, lat in vertices]
                painter.drawPolygon(QPolygonF(points))

        painter.setPen(pen)

        if self._mode == MODE_POLYGON and self._vertices:
            points = [QPointF(*self.lonlat_to_widget(lon, lat)) for lon, lat in self._vertices]
            if self._polygon_finished:
                # Finished shapes must render as an unambiguous closed ring -- `drawPolygon`
                # (unlike `drawPolyline`) always draws the closing segment back to the first
                # point, matching the closed ring that `finish_polygon` already builds for WKT.
                painter.drawPolygon(QPolygonF(points))
            else:
                painter.drawPolyline(QPolygonF(points))
            for point in points:
                painter.drawEllipse(point, 3, 3)

        if self._mode == MODE_POINT and self._point is not None:
            x, y = self.lonlat_to_widget(*self._point)
            painter.drawEllipse(QPointF(x, y), 5, 5)

        if self._mode == MODE_BBOX and self._bbox_start is not None and self._bbox_end is not None:
            x0, y0 = self.lonlat_to_widget(*self._bbox_start)
            x1, y1 = self.lonlat_to_widget(*self._bbox_end)
            painter.drawRect(QRectF(QPointF(x0, y0), QPointF(x1, y1)))
