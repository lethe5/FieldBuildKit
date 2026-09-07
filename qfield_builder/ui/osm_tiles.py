"""OpenStreetMap XYZ raster tile support for :mod:`qfield_builder.ui.map_canvas`.

This is a **visual aid only** for the interactive drawing canvas -- fetched tile imagery is never
written into, or referenced by, the generated QField project output (no ``.mbtiles``, no
reference in the ``.qgs``, nothing persisted alongside a build). It exists purely so a user has
real geographic context while drawing a site boundary/point/bbox in the wizard UI. This is
entirely separate from, and must never be confused with, the application's actual offline/online
VWorld basemap generation pipeline (:mod:`qfield_builder.vworld_tiles`, Sections 10/11 of the
specification) -- nothing in this module is used by, or referenced from, that pipeline.

Everything in this module that does *not* need Qt's networking stack (the URL template, the
attribution text, the required User-Agent string, and the on-disk/in-memory cache) is kept
dependency-free from `PySide6.QtNetwork` so it can be unit-tested in isolation; the actual async
HTTP fetch (via `QNetworkAccessManager`) lives in :mod:`qfield_builder.ui.map_canvas`'s
``OsmTileLayer``, which is the only thing here that touches the Qt event loop.

OpenStreetMap's tile usage policy (https://operations.osmfoundation.org/policies/tiles/) requires:

- a valid, identifying ``User-Agent`` on every request (not a generic/default HTTP client
  string) -- see :data:`USER_AGENT` below.
- no heavy bulk/automated fetching -- this module only ever fetches the handful of tiles actually
  visible in a desktop-sized widget at a time (never a bulk crawl), and every fetch result (success
  or failure) is cached so the same tile is never re-requested once resolved.
- client-side caching of already-fetched tiles -- see :class:`TileCache`.
- visible "(c) OpenStreetMap contributors" attribution wherever the tiles are displayed (a real
  ODbL licensing requirement, not optional polish) -- see :data:`ATTRIBUTION_TEXT`, rendered by
  ``MapCanvas`` as an always-visible child label whenever OSM tiles are the active background.
"""
from __future__ import annotations

from pathlib import Path

# Standard OSM slippy-map XYZ tile endpoint (the "main" OSM tile server).
TILE_URL_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# OSM's tile usage policy requires a real, identifying User-Agent -- not a generic urllib/Qt
# default. This identifies the application and its purpose; there is no stable public support
# contact for this tool to embed, so the project name/version itself is the identifying token
# (the same standard practice recommended for small/hobby tools without a dedicated ops contact).
USER_AGENT = "QFieldProjectBuilder/0.1 (desktop drawing-canvas visual aid; not a bulk crawler)"

# ODbL-required attribution text, displayed by MapCanvas whenever OSM tiles are the active
# background.
ATTRIBUTION_TEXT = "© OpenStreetMap contributors"

# tile.openstreetmap.org's own documented practical maximum zoom for raster tiles is 19 (some
# areas render blank beyond that); MapCanvas's own live-view zoom can go higher (up to
# `map_canvas.MAX_ZOOM`, shared with the VWorld offline-zoom bounds) but OSM tile fetches are
# clamped to this ceiling rather than requesting tiles that don't exist.
OSM_MAX_TILE_ZOOM = 19

TileKey = tuple[int, int, int]


def build_tile_url(z: int, x: int, y: int) -> str:
    """The standard XYZ slippy-map tile URL for tile (z, x, y)."""
    return TILE_URL_TEMPLATE.format(z=z, x=x, y=y)


class TileCache:
    """An in-memory (and optionally disk-backed) cache of already-fetched tile bytes.

    Keyed by ``(z, x, y)`` per OSM's tile-usage-policy recommendation that clients cache
    already-fetched tiles rather than re-requesting them (e.g. when panning back over an
    already-seen area). The in-memory layer is always active; a disk layer is only used if
    `disk_dir` is supplied (deliberately not enabled by default -- see
    :mod:`qfield_builder.ui.map_canvas`'s own docstring for why the shipped widget only opts into
    it with an explicit, caller-supplied directory).
    """

    def __init__(self, disk_dir: str | Path | None = None):
        self._memory: dict[TileKey, bytes] = {}
        self._disk_dir = Path(disk_dir) if disk_dir else None
        if self._disk_dir is not None:
            self._disk_dir.mkdir(parents=True, exist_ok=True)

    def _disk_path(self, key: TileKey) -> Path:
        z, x, y = key
        return self._disk_dir / f"{z}_{x}_{y}.png"  # type: ignore[union-attr]

    def get(self, key: TileKey) -> bytes | None:
        cached = self._memory.get(key)
        if cached is not None:
            return cached
        if self._disk_dir is not None:
            path = self._disk_path(key)
            if path.exists():
                data = path.read_bytes()
                self._memory[key] = data
                return data
        return None

    def put(self, key: TileKey, data: bytes) -> None:
        self._memory[key] = data
        if self._disk_dir is not None:
            self._disk_path(key).write_bytes(data)

    def __contains__(self, key: TileKey) -> bool:
        return self.get(key) is not None
