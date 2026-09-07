"""Widget-level tests for qfield_builder.ui.map_canvas (offscreen QApplication).

Two complementary ways of exercising a drawing sequence are used here, per the testing brief:

1. Direct calls to the widget's own public drawing-operation methods (`add_polygon_vertex_at`,
   `finish_polygon`, `place_point_at`, `start_bbox_at`/`update_bbox_at`/`finish_bbox_at`) --
   deterministic and independent of how reliably a given CI/sandbox environment delivers
   synthetic mouse events.
2. Directly constructed `QMouseEvent`s fed straight into the widget's real Qt event handlers
   (`mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent`/`mouseDoubleClickEvent`), to prove the
   actual mouse-driven interaction path (not just the underlying helper methods) is wired
   correctly end to end.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from qfield_builder.ui.map_canvas import MAX_ZOOM, MIN_ZOOM, MapCanvas
from qfield_builder.ui.webmercator import lonlat_to_pixel, pixel_to_lonlat
from qfield_builder.wkt import validate_geometry


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_canvas(width=400, height=300, center_lon=127.0, center_lat=37.0, zoom=10) -> MapCanvas:
    canvas = MapCanvas(center_lon=center_lon, center_lat=center_lat, zoom=zoom)
    canvas.resize(width, height)
    return canvas


def _expected_lonlat(canvas: MapCanvas, x: float, y: float) -> tuple[float, float]:
    """An independent (re-derived, not reused-from-the-widget) expected value, computed directly
    from the pure `webmercator` module, for asserting the widget's own coordinate wiring is
    correct -- not merely self-consistent."""
    cx, cy = lonlat_to_pixel(canvas.center()[0], canvas.center()[1], canvas.zoom())
    px = cx + (x - canvas.width() / 2.0)
    py = cy + (y - canvas.height() / 2.0)
    return pixel_to_lonlat(px, py, canvas.zoom())


def _left_mouse_event(event_type: QEvent.Type, x: float, y: float) -> QMouseEvent:
    local_pos = QPointF(x, y)
    return QMouseEvent(
        event_type,
        local_pos,
        local_pos,  # globalPos -- irrelevant here since the widget only ever reads local coords.
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _right_mouse_event(event_type: QEvent.Type, x: float, y: float) -> QMouseEvent:
    """Bug 2 fix: the secondary (right) mouse button always pans, regardless of drawing mode --
    see the "Bug 2 fix" section below."""
    local_pos = QPointF(x, y)
    return QMouseEvent(
        event_type,
        local_pos,
        local_pos,
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )


# ---------------------------------------------------------------------------------------------
# Widget construction / mode switching.
# ---------------------------------------------------------------------------------------------


def test_default_mode_is_pan():
    canvas = _make_canvas()
    assert canvas.mode() == "pan"


def test_set_mode_rejects_unknown_mode():
    canvas = _make_canvas()
    with pytest.raises(ValueError):
        canvas.set_mode("not-a-real-mode")


def test_zoom_is_clamped_to_documented_bounds():
    canvas = _make_canvas()
    canvas.set_view(127.0, 37.0, MAX_ZOOM + 50)
    assert canvas.zoom() == MAX_ZOOM
    canvas.set_view(127.0, 37.0, MIN_ZOOM - 50)
    assert canvas.zoom() == MIN_ZOOM


# ---------------------------------------------------------------------------------------------
# Polygon drawing mode (direct method calls).
# ---------------------------------------------------------------------------------------------


def test_polygon_drawing_via_direct_calls_produces_valid_multipolygon_wkt():
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    canvas.add_polygon_vertex_at(100, 100)
    canvas.add_polygon_vertex_at(300, 100)
    canvas.add_polygon_vertex_at(300, 250)

    wkt = canvas.finish_polygon()

    assert wkt.startswith("MULTIPOLYGON(((")
    assert wkt.endswith(")))")
    validate_geometry(wkt, "MULTIPOLYGON")  # must not raise


def test_polygon_drawing_ring_is_closed():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(50, 50)
    canvas.add_polygon_vertex_at(150, 50)
    canvas.add_polygon_vertex_at(150, 150)
    wkt = canvas.finish_polygon()

    inner = wkt[len("MULTIPOLYGON(((") : -len(")))")]
    points = [tuple(float(v) for v in pair.split()) for pair in inner.split(", ")]
    assert points[0] == points[-1]
    assert len(points) == 4  # 3 distinct vertices + repeated closing vertex


def test_polygon_drawing_vertex_coordinates_match_expected_lonlat():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(120, 80)
    canvas.add_polygon_vertex_at(280, 80)
    canvas.add_polygon_vertex_at(280, 220)
    wkt = canvas.finish_polygon()

    inner = wkt[len("MULTIPOLYGON(((") : -len(")))")]
    points = [tuple(float(v) for v in pair.split()) for pair in inner.split(", ")]

    expected_first = _expected_lonlat(canvas, 120, 80)
    assert points[0][0] == pytest.approx(expected_first[0], abs=1e-9)
    assert points[0][1] == pytest.approx(expected_first[1], abs=1e-9)


def test_finish_polygon_raises_with_fewer_than_three_vertices():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(10, 10)
    canvas.add_polygon_vertex_at(20, 20)
    with pytest.raises(ValueError):
        canvas.finish_polygon()


def test_polygon_drawn_signal_emits_the_same_wkt_finish_polygon_returns():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(10, 10)
    canvas.add_polygon_vertex_at(90, 10)
    canvas.add_polygon_vertex_at(90, 90)

    received = []
    canvas.polygon_drawn.connect(received.append)
    wkt = canvas.finish_polygon()

    assert received == [wkt]


# ---------------------------------------------------------------------------------------------
# Polygon drawing mode via real Qt mouse events (press to add vertex, double-click to finish).
# ---------------------------------------------------------------------------------------------


def test_polygon_drawing_via_real_mouse_events():
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    for x, y in [(60, 60), (220, 60), (220, 200)]:
        canvas.mousePressEvent(_left_mouse_event(QEvent.Type.MouseButtonPress, x, y))
        canvas.mouseReleaseEvent(_left_mouse_event(QEvent.Type.MouseButtonRelease, x, y))

    canvas.mouseDoubleClickEvent(_left_mouse_event(QEvent.Type.MouseButtonDblClick, 220, 200))

    assert canvas.last_polygon_wkt is not None
    validate_geometry(canvas.last_polygon_wkt, "MULTIPOLYGON")


def test_double_click_before_three_vertices_does_not_crash_or_finish():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.mousePressEvent(_left_mouse_event(QEvent.Type.MouseButtonPress, 10, 10))
    canvas.mouseDoubleClickEvent(_left_mouse_event(QEvent.Type.MouseButtonDblClick, 10, 10))
    assert canvas.last_polygon_wkt is None


# ---------------------------------------------------------------------------------------------
# Point drawing mode.
# ---------------------------------------------------------------------------------------------


def test_point_drawing_via_direct_call_produces_valid_point_wkt():
    canvas = _make_canvas()
    canvas.set_mode("point")
    wkt = canvas.place_point_at(200, 150)

    assert wkt.startswith("POINT(")
    validate_geometry(wkt, "POINT")

    expected_lon, expected_lat = _expected_lonlat(canvas, 200, 150)
    lon_str, lat_str = wkt[len("POINT(") : -1].split()
    assert float(lon_str) == pytest.approx(expected_lon, abs=1e-9)
    assert float(lat_str) == pytest.approx(expected_lat, abs=1e-9)


def test_point_drawing_via_real_mouse_click():
    canvas = _make_canvas()
    canvas.set_mode("point")
    canvas.mousePressEvent(_left_mouse_event(QEvent.Type.MouseButtonPress, 50, 40))
    canvas.mouseReleaseEvent(_left_mouse_event(QEvent.Type.MouseButtonRelease, 50, 40))

    assert canvas.last_point_wkt is not None
    validate_geometry(canvas.last_point_wkt, "POINT")


def test_point_drawn_signal_fires():
    canvas = _make_canvas()
    canvas.set_mode("point")
    received = []
    canvas.point_drawn.connect(received.append)
    wkt = canvas.place_point_at(10, 10)
    assert received == [wkt]


# ---------------------------------------------------------------------------------------------
# Bbox drawing mode.
# ---------------------------------------------------------------------------------------------


def test_bbox_drawing_via_direct_calls_produces_correct_min_max():
    canvas = _make_canvas()
    canvas.set_mode("bbox")
    canvas.start_bbox_at(300, 50)  # start at a "top-right"-ish widget position
    canvas.update_bbox_at(250, 100)
    bbox = canvas.finish_bbox_at(50, 200)  # end at a "bottom-left"-ish widget position

    corner_a = _expected_lonlat(canvas, 300, 50)
    corner_b = _expected_lonlat(canvas, 50, 200)

    assert bbox["min_lon"] == pytest.approx(min(corner_a[0], corner_b[0]), abs=1e-9)
    assert bbox["max_lon"] == pytest.approx(max(corner_a[0], corner_b[0]), abs=1e-9)
    assert bbox["min_lat"] == pytest.approx(min(corner_a[1], corner_b[1]), abs=1e-9)
    assert bbox["max_lat"] == pytest.approx(max(corner_a[1], corner_b[1]), abs=1e-9)
    assert bbox["min_lon"] <= bbox["max_lon"]
    assert bbox["min_lat"] <= bbox["max_lat"]


def test_finish_bbox_without_start_raises():
    canvas = _make_canvas()
    canvas.set_mode("bbox")
    with pytest.raises(ValueError):
        canvas.finish_bbox_at(10, 10)


def test_bbox_drawing_via_real_mouse_drag():
    canvas = _make_canvas()
    canvas.set_mode("bbox")

    canvas.mousePressEvent(_left_mouse_event(QEvent.Type.MouseButtonPress, 40, 40))
    canvas.mouseMoveEvent(_left_mouse_event(QEvent.Type.MouseMove, 200, 180))
    canvas.mouseReleaseEvent(_left_mouse_event(QEvent.Type.MouseButtonRelease, 200, 180))

    assert canvas.last_bbox is not None
    bbox = canvas.last_bbox
    assert bbox["min_lon"] <= bbox["max_lon"]
    assert bbox["min_lat"] <= bbox["max_lat"]


def test_bbox_drawn_signal_fires_with_the_finished_bbox():
    canvas = _make_canvas()
    canvas.set_mode("bbox")
    received = []
    canvas.bbox_drawn.connect(received.append)
    canvas.start_bbox_at(10, 10)
    bbox = canvas.finish_bbox_at(100, 100)
    assert received == [bbox]


# ---------------------------------------------------------------------------------------------
# Panning and zooming.
# ---------------------------------------------------------------------------------------------


def test_pan_by_pixels_moves_the_center():
    canvas = _make_canvas(center_lon=0.0, center_lat=0.0, zoom=8)
    original_center = canvas.center()
    canvas.pan_by_pixels(50, 0)
    new_center = canvas.center()
    assert new_center != original_center
    # Panning right (positive dx) should move the visible center's longitude westward (dragging
    # the map surface right reveals more of what's to the west), i.e. the new center lon < old.
    assert new_center[0] < original_center[0]


def test_pan_via_real_mouse_drag_in_pan_mode():
    canvas = _make_canvas(center_lon=10.0, center_lat=10.0, zoom=8)
    canvas.set_mode("pan")
    original_center = canvas.center()

    canvas.mousePressEvent(_left_mouse_event(QEvent.Type.MouseButtonPress, 200, 150))
    canvas.mouseMoveEvent(_left_mouse_event(QEvent.Type.MouseMove, 150, 150))
    canvas.mouseReleaseEvent(_left_mouse_event(QEvent.Type.MouseButtonRelease, 150, 150))

    assert canvas.center() != original_center


def test_zoom_by_changes_zoom_level_and_is_clamped():
    canvas = _make_canvas(zoom=10)
    canvas.zoom_by(2)
    assert canvas.zoom() == 12
    canvas.zoom_by(1000)
    assert canvas.zoom() == MAX_ZOOM


# ---------------------------------------------------------------------------------------------
# Bug 2 fix (FR-QPB-025/Decision Log D-24; see
# tests/acceptance/qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.
# traceability.md's contract rows 2(i)-2(iii)): a right-button mouse drag always pans the view,
# regardless of `self._mode`, without disturbing an in-progress polygon/bbox drawing -- the
# wizard's drawing canvas was previously unpannable while `set_mode("polygon")`/`set_mode("bbox")`
# was active (both real wizard usages hardcode one of those modes and never switch back to "pan").
# ---------------------------------------------------------------------------------------------


def test_right_button_drag_pans_in_bbox_mode_without_disturbing_the_drag_in_progress(monkeypatch):
    canvas = _make_canvas(center_lon=10.0, center_lat=10.0, zoom=8)
    canvas.set_mode("bbox")
    canvas.start_bbox_at(40, 40)  # begin a bbox drag, mirroring the existing bbox-mode setup.
    original_center = canvas.center()
    original_bbox_start = canvas._bbox_start

    pan_calls = []
    original_pan_by_pixels = canvas.pan_by_pixels
    monkeypatch.setattr(
        canvas,
        "pan_by_pixels",
        lambda dx, dy: (pan_calls.append((dx, dy)), original_pan_by_pixels(dx, dy))[-1],
    )

    canvas.mousePressEvent(_right_mouse_event(QEvent.Type.MouseButtonPress, 200, 150))
    canvas.mouseMoveEvent(_right_mouse_event(QEvent.Type.MouseMove, 150, 150))
    canvas.mouseReleaseEvent(_right_mouse_event(QEvent.Type.MouseButtonRelease, 150, 150))

    assert pan_calls, "expected pan_by_pixels to be invoked by the right-button drag"
    assert canvas.center() != original_center
    assert canvas.mode() == "bbox"  # panning must not silently change the drawing mode.
    # The bbox drag already in progress before panning must survive unaffected -- still anchored
    # at its original start corner.
    assert canvas._bbox_start == original_bbox_start

    bbox = canvas.finish_bbox_at(200, 180)
    assert bbox["min_lon"] <= bbox["max_lon"]
    assert bbox["min_lat"] <= bbox["max_lat"]


def test_right_button_drag_pans_in_polygon_mode_without_losing_placed_vertices():
    canvas = _make_canvas(center_lon=10.0, center_lat=10.0, zoom=8)
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(60, 60)
    canvas.add_polygon_vertex_at(220, 60)
    assert len(canvas._vertices) == 2
    original_center = canvas.center()

    canvas.mousePressEvent(_right_mouse_event(QEvent.Type.MouseButtonPress, 200, 150))
    canvas.mouseMoveEvent(_right_mouse_event(QEvent.Type.MouseMove, 100, 100))
    canvas.mouseReleaseEvent(_right_mouse_event(QEvent.Type.MouseButtonRelease, 100, 100))

    assert canvas.center() != original_center
    assert canvas.mode() == "polygon"
    # Panning must never discard in-progress polygon vertices.
    assert len(canvas._vertices) == 2

    canvas.add_polygon_vertex_at(220, 200)
    wkt = canvas.finish_polygon()
    validate_geometry(wkt, "MULTIPOLYGON")


def test_right_button_press_and_release_alone_does_not_add_a_polygon_vertex():
    """A right-button "click" (press+release with no intervening drag) must be treated purely as
    a pan gesture, never as left-click's own polygon-vertex-placement behavior."""
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    canvas.mousePressEvent(_right_mouse_event(QEvent.Type.MouseButtonPress, 60, 60))
    canvas.mouseReleaseEvent(_right_mouse_event(QEvent.Type.MouseButtonRelease, 60, 60))

    assert canvas._vertices == []


def test_zoom_still_works_regardless_of_mode_after_the_pan_mechanism_change():
    """Regression guard (contract row 2(iii)): the pan-mechanism change above must not
    accidentally gate scroll-wheel zoom on mode -- it already isn't gated today."""
    for mode in ("bbox", "polygon"):
        canvas = _make_canvas(zoom=10)
        canvas.set_mode(mode)
        canvas.zoom_by(2)
        assert canvas.zoom() == 12
        canvas.zoom_by(1000)
        assert canvas.zoom() == MAX_ZOOM


# ---------------------------------------------------------------------------------------------
# reset_drawing clears every mode's in-progress/finished state.
# ---------------------------------------------------------------------------------------------


def test_reset_drawing_clears_polygon_point_and_bbox_state():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(0, 0)
    canvas.add_polygon_vertex_at(10, 0)
    canvas.add_polygon_vertex_at(10, 10)
    canvas.finish_polygon()
    assert canvas.last_polygon_wkt is not None

    canvas.reset_drawing()

    assert canvas.last_polygon_wkt is None
    assert canvas.last_point_wkt is None
    assert canvas.last_bbox is None


# ---------------------------------------------------------------------------------------------
# Finished-polygon rendering: regression coverage for the bug where `finish_polygon()` built a
# genuinely closed ring for its returned WKT, but the on-screen overlay kept rendering the
# vertices via `drawPolyline` (an inherently *open* path) regardless of whether the shape had
# been finished -- so the polygon never visually closed on screen, even though the underlying
# geometry/WKT was always correct. A test that only inspects the returned WKT string (e.g.
# `test_polygon_drawing_ring_is_closed` above) would NOT have caught this, since the WKT was
# never the broken part -- these tests instead inspect the widget's own "finished" state and its
# actual rendered pixels.
# ---------------------------------------------------------------------------------------------


def _no_network_tile_fetcher(z: int, x: int, y: int) -> bytes:  # noqa: ARG001
    """A synchronous tile-fetch stand-in that always fails fast (mirroring the fake-fetcher
    pattern `tests/unit/test_osm_tiles.py` uses), so this section's rendering assertions are
    never affected by, or dependent on, real network access."""
    raise RuntimeError("no network access in tests")


def _make_no_network_canvas(width=400, height=300) -> MapCanvas:
    canvas = MapCanvas(
        center_lon=127.0, center_lat=37.0, zoom=10, tile_fetcher=_no_network_tile_fetcher
    )
    canvas.resize(width, height)
    return canvas


def _render_to_image(canvas: MapCanvas):
    """Forces a real, synchronous `paintEvent` (mirroring `test_osm_tiles.py`'s `_force_paint` --
    `update()`/`repaint()` alone are not reliably delivered under `QT_QPA_PLATFORM=offscreen`, but
    `QWidget.render()` always runs the widget's actual paint logic) and returns the result as a
    `QImage` for pixel-level inspection."""
    pixmap = QPixmap(canvas.size())
    canvas.render(pixmap)
    return pixmap.toImage()


_DRAWING_PEN_COLOR = QColor(200, 30, 30)


def _count_pen_colored_pixels(image) -> int:
    """How many pixels of `image` are (approximately) the drawing overlay's pen color -- used to
    detect whether a given segment was actually rendered, without depending on exactly which
    pixel it falls on."""
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                abs(color.red() - _DRAWING_PEN_COLOR.red()) <= 10
                and abs(color.green() - _DRAWING_PEN_COLOR.green()) <= 10
                and abs(color.blue() - _DRAWING_PEN_COLOR.blue()) <= 10
            ):
                count += 1
    return count


def test_polygon_is_not_finished_until_finish_polygon_is_called():
    canvas = _make_no_network_canvas()
    canvas.set_mode("polygon")
    assert canvas.is_polygon_finished() is False

    canvas.add_polygon_vertex_at(60, 60)
    canvas.add_polygon_vertex_at(220, 60)
    canvas.add_polygon_vertex_at(220, 200)
    assert canvas.is_polygon_finished() is False

    canvas.finish_polygon()
    assert canvas.is_polygon_finished() is True


def test_reset_drawing_clears_the_finished_flag():
    canvas = _make_no_network_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(60, 60)
    canvas.add_polygon_vertex_at(220, 60)
    canvas.add_polygon_vertex_at(220, 200)
    canvas.finish_polygon()
    assert canvas.is_polygon_finished() is True

    canvas.reset_drawing()

    assert canvas.is_polygon_finished() is False


def test_adding_a_vertex_after_finishing_reopens_the_shape_for_editing():
    canvas = _make_no_network_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(60, 60)
    canvas.add_polygon_vertex_at(220, 60)
    canvas.add_polygon_vertex_at(220, 200)
    canvas.finish_polygon()
    assert canvas.is_polygon_finished() is True

    canvas.add_polygon_vertex_at(60, 200)

    assert canvas.is_polygon_finished() is False


def test_finished_polygon_renders_a_visually_closed_ring_not_just_a_closed_wkt():
    canvas = _make_no_network_canvas()
    canvas.set_mode("polygon")
    canvas.add_polygon_vertex_at(60, 60)
    canvas.add_polygon_vertex_at(220, 60)
    canvas.add_polygon_vertex_at(220, 200)

    before_image = _render_to_image(canvas)
    before_count = _count_pen_colored_pixels(before_image)

    canvas.finish_polygon()

    after_image = _render_to_image(canvas)
    after_count = _count_pen_colored_pixels(after_image)

    # The three vertices/edges already on screen before finishing are unchanged by finishing:
    # finishing must add strictly more pen-colored pixels on screen (the newly-drawn closing
    # segment from the last vertex back to the first), not merely leave the rendered image the
    # same as it was while the shape was still open.
    assert after_count > before_count


# ---------------------------------------------------------------------------------------------
# Multi-polygon drawing sessions (FR-QPB-129; Decision Log D-75/D-79; AC-QPB-115/116). Routed
# contract: tests/acceptance/qfield_project_builder_multi_polygon_site_drawing.traceability.md,
# "tests/unit/test_map_canvas.py -- multi-polygon drawing-session mechanism" table, rows 1-4.
# ---------------------------------------------------------------------------------------------


def _finish_a_triangle(canvas: MapCanvas, x0: float, y0: float) -> str:
    """Draws and finishes a small, non-degenerate triangle whose vertices are anchored at
    ``(x0, y0)`` -- a small helper so each test below can easily draw several non-overlapping
    polygons in the same session without repeating the same three calls each time."""
    canvas.add_polygon_vertex_at(x0, y0)
    canvas.add_polygon_vertex_at(x0 + 40, y0)
    canvas.add_polygon_vertex_at(x0 + 40, y0 + 40)
    return canvas.finish_polygon()


def test_commit_finished_polygon_starts_a_genuinely_new_independent_polygon():
    """Contract row 1: finishing one polygon, committing it, then drawing and finishing a second,
    separate polygon must never merge the second's vertices with the first's already-finished
    shape."""
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    wkt_1 = _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()

    wkt_2 = _finish_a_triangle(canvas, 200, 200)

    assert wkt_1 != wkt_2

    inner_2 = wkt_2[len("MULTIPOLYGON(((") : -len(")))")]
    points_2 = [tuple(float(v) for v in pair.split()) for pair in inner_2.split(", ")]
    # 3 distinct vertices + the repeated closing vertex -- never the first triangle's 3 vertices
    # appended/merged in (which would make this 7, not 4).
    assert len(points_2) == 4

    expected_first_vertex = _expected_lonlat(canvas, 200, 200)
    assert points_2[0][0] == pytest.approx(expected_first_vertex[0], abs=1e-9)
    assert points_2[0][1] == pytest.approx(expected_first_vertex[1], abs=1e-9)


def test_commit_finished_polygon_raises_if_nothing_has_been_finished_yet():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    with pytest.raises(ValueError):
        canvas.commit_finished_polygon()

    # Vertices placed but the ring not yet closed via finish_polygon() -- still not committable.
    canvas.add_polygon_vertex_at(10, 10)
    canvas.add_polygon_vertex_at(50, 10)
    with pytest.raises(ValueError):
        canvas.commit_finished_polygon()


def test_finished_polygons_accumulates_each_committed_polygon_in_order():
    """Contract row 2: every committed polygon accumulates in an inspectable collection, in the
    order finished, and committing a later polygon never mutates an earlier one's own stored
    WKT."""
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    assert canvas.finished_polygons == []

    wkt_1 = _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()
    assert canvas.finished_polygons == [wkt_1]

    wkt_2 = _finish_a_triangle(canvas, 200, 200)
    canvas.commit_finished_polygon()
    assert canvas.finished_polygons == [wkt_1, wkt_2]

    wkt_3 = _finish_a_triangle(canvas, 20, 200)
    canvas.commit_finished_polygon()
    assert canvas.finished_polygons == [wkt_1, wkt_2, wkt_3]

    # Mutating the returned list must never affect this widget's own internal state.
    returned = canvas.finished_polygons
    returned.append("not a real wkt")
    returned[0] = "mutated"
    assert canvas.finished_polygons == [wkt_1, wkt_2, wkt_3]


def test_in_progress_vertices_for_a_new_polygon_are_unaffected_by_an_earlier_commit():
    """Contract row 3: a polygon in progress (vertices already placed, not yet finished) is
    unaffected by an earlier polygon in the same session having already been finished and
    committed -- mirrors AC-QPB-116's "the canvas correctly begins a new, independent shape"."""
    canvas = _make_canvas()
    canvas.set_mode("polygon")

    _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()

    assert canvas._vertices == []
    assert canvas.is_polygon_finished() is False

    canvas.add_polygon_vertex_at(300, 30)
    canvas.add_polygon_vertex_at(300, 90)

    expected_v1 = _expected_lonlat(canvas, 300, 30)
    expected_v2 = _expected_lonlat(canvas, 300, 90)
    assert canvas._vertices == [
        pytest.approx(expected_v1, abs=1e-9),
        pytest.approx(expected_v2, abs=1e-9),
    ]
    assert canvas.is_polygon_finished() is False
    # The already-committed polygon must remain exactly as it was, untouched by drawing a second.
    assert len(canvas.finished_polygons) == 1


def test_zoom_and_pan_still_work_with_a_committed_polygon_already_in_the_session():
    """Contract row 4 (regression guard): zoom/pan continue to work identically regardless of this
    change, re-run with a multi-polygon session already in progress."""
    canvas = _make_canvas(center_lon=10.0, center_lat=10.0, zoom=10)
    canvas.set_mode("polygon")
    _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()

    canvas.zoom_by(2)
    assert canvas.zoom() == 12
    canvas.zoom_by(1000)
    assert canvas.zoom() == MAX_ZOOM
    canvas.set_view(10.0, 10.0, 10)

    original_center = canvas.center()
    canvas.mousePressEvent(_right_mouse_event(QEvent.Type.MouseButtonPress, 200, 150))
    canvas.mouseMoveEvent(_right_mouse_event(QEvent.Type.MouseMove, 150, 150))
    canvas.mouseReleaseEvent(_right_mouse_event(QEvent.Type.MouseButtonRelease, 150, 150))

    assert canvas.center() != original_center
    assert canvas.mode() == "polygon"
    # Panning while a polygon is already committed must never disturb that commit.
    assert len(canvas.finished_polygons) == 1


def test_reset_drawing_does_not_discard_already_committed_polygons():
    """`reset_drawing` (used by `SiteInputPage`'s "지우기"/Clear button) must only clear the
    *current* in-progress/finished shape -- clearing a mistake in the shape being drawn right now
    must never silently discard a polygon already finished and committed earlier this session."""
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    committed_wkt = _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()

    canvas.add_polygon_vertex_at(300, 30)  # an in-progress, not-yet-finished second polygon
    canvas.reset_drawing()

    assert canvas.finished_polygons == [committed_wkt]
    assert canvas._vertices == []
    assert canvas.last_polygon_wkt is None


def test_clear_finished_polygons_removes_every_committed_polygon():
    canvas = _make_canvas()
    canvas.set_mode("polygon")
    _finish_a_triangle(canvas, 20, 20)
    canvas.commit_finished_polygon()
    _finish_a_triangle(canvas, 200, 200)
    canvas.commit_finished_polygon()
    assert len(canvas.finished_polygons) == 2

    canvas.clear_finished_polygons()

    assert canvas.finished_polygons == []


def test_committed_polygon_remains_visibly_rendered_while_drawing_a_new_one():
    """AC-QPB-116: "the first polygon's own finished shape and assigned name are preserved... the
    canvas correctly begins a new, independent shape" -- the canvas-widget half of this (the
    first, already-committed shape must remain visibly rendered on screen) is verified here via
    real pixel inspection, mirroring `test_finished_polygon_renders_a_visually_closed_ring_not_
    just_a_closed_wkt`'s own established convention."""
    canvas = _make_no_network_canvas()
    canvas.set_mode("polygon")
    _finish_a_triangle(canvas, 60, 60)
    canvas.commit_finished_polygon()

    canvas.add_polygon_vertex_at(220, 220)
    canvas.add_polygon_vertex_at(260, 220)

    image = _render_to_image(canvas)
    committed_pen_color = QColor(120, 120, 130)
    committed_pixels = 0
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if (
                abs(color.red() - committed_pen_color.red()) <= 10
                and abs(color.green() - committed_pen_color.green()) <= 10
                and abs(color.blue() - committed_pen_color.blue()) <= 10
            ):
                committed_pixels += 1
    assert committed_pixels > 0, (
        "the already-committed polygon must remain visibly rendered on screen while a second, "
        "separate polygon is being drawn"
    )
