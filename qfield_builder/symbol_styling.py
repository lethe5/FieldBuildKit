"""Symbol styling: minimalist default point/polygon symbology (FR-QPB-120) and the offline
Tabler icon-name search / on-demand SVG fetch used for point-marker symbols (FR-QPB-121,
FR-QPB-011(d), NFR-QPB-080; Decision Log D-61/D-65), plus the live, per-visible-result preview-SVG
fetch permitted during search (FR-QPB-011(d)(ii), NFR-QPB-080 clauses (5)-(8), AC-QPB-117;
Decision Log D-76).

This module contains everything about this feature that does **not** need PyQGIS:

- The bundled, build-time, offline Tabler icon-name index and its pure, case-insensitive
  substring search (``search_bundled_tabler_icon_names`` -- HARNESS_CONTRACT.md function 14).
- The single permitted fetch-on-selection network request (FR-QPB-011(d)(i)): fetching one
  already-selected icon's raw SVG source from Tabler's own public source, never a live
  search/autocomplete request. Two entry points exist for this, matching a real, existing
  dependency-injection precedent already used for VWorld tile downloads
  (:mod:`qfield_builder.vworld_tiles`):

  - :func:`fetch_tabler_icon_svg` -- a **test-only, real-network reference implementation**
    (HARNESS_CONTRACT.md function 13), used only by this application's own standalone
    ``network``-marked acceptance test. Nothing in the production build pipeline calls this
    function directly.
  - :func:`resolve_svg_fetch` -- the function :mod:`qfield_builder.build` actually calls. It
    dispatches to the real fetch by default, or to a deterministic fault-injection double when
    ``symbol_styling.tabler_svg_fetch.fake`` is present in the build config (a test seam, exactly
    mirroring ``qfield_builder.vworld_tiles.resolve_tile_fetcher``'s ``tile_source.fake``
    convention) -- never changes the production default when omitted.

- The second, independently permitted live-preview-fetch trigger added by Decision Log D-76
  (FR-QPB-011(d)(ii)): fetching a preview SVG, live, for each of the currently visible/matched
  results of an in-progress Step 6 search -- never an unbounded prefetch of the entire bundled
  index, never for a result not currently rendered on screen. Two entry points exist here too,
  mirroring the fetch-on-selection pair above:

  - :func:`fetch_tabler_icon_preview_svgs` -- a **pure, offline, GUI-independent reference
    implementation** (HARNESS_CONTRACT.md function 20), fake-double-only (there is no "real
    network" mode -- see its own docstring), used by the acceptance suite.
  - :func:`dispatch_preview_fetches_real` -- the real, production, bounded-concurrency dispatch
    mechanism the wizard's ``SymbolStylingPage`` (:mod:`qfield_builder.ui.wizard`) actually calls,
    once per debounced search settle, for exactly the names currently visible on screen. Reuses
    :func:`fetch_tabler_icon_svg_real` per name (so it automatically carries the same compliant
    ``TABLER_USER_AGENT`` header and single-attempt-per-name discipline the existing
    selection-fetch already has, NFR-QPB-080 clauses (1)/(2)/(5)); one name's failure -- or an
    unexpected exception -- never blocks or drops any other name's own result (NFR-QPB-080(8),
    AC-QPB-117).

PyQGIS-calling code that actually *applies* the resulting symbol (minimalist default marker/fill,
or a fetched SVG marker) to a generated project's layers lives in
:mod:`qfield_builder.qgis_worker` instead, per this codebase's existing convention that no
``qgis.*`` import appears outside the functions/modules that genuinely need a real PyQGIS runtime.

Bundled icon-name index provenance
-----------------------------------
``resources/tabler/icon_names.txt`` is a plain, one-name-per-line, sorted, deduplicated list of
every icon name under ``icons/outline/`` in the official ``github.com/tabler/tabler-icons``
repository (MIT-licensed, confirmed -- Decision Log D-65), captured at implementation time via
that repository's own public Git Trees API (5,130 names; Tabler also publishes a smaller,
strictly-overlapping "filled" style variant set for a subset of these same names, not bundled
separately here -- see this round's implementer completion report for the full reasoning). This
is a static, version-controlled resource, bundled the same way ``resources/config/
vworld_layers.json`` already is (see :mod:`qfield_builder.resource_paths`) -- refreshing it (as
Tabler's own icon set grows over time) is an ordinary, manual, build-time data update, never a
runtime network operation.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from .resource_paths import resource_path

_ICON_NAMES_RESOURCE_PARTS = ("tabler", "icon_names.txt")

#: FR-QPB-011(d)/NFR-QPB-080(1): the single SVG-fetch request this feature ever makes must carry
#: a compliant, identifying User-Agent header.
TABLER_USER_AGENT = "QFieldProjectBuilder/0.1 (+https://github.com/tabler/tabler-icons; icon-fetch)"

#: Tabler's own public, unauthenticated static-file source for one icon's raw SVG (Decision
#: Log D-65's confirmed research: `github.com/tabler/tabler-icons`, MIT-licensed, no API key/
#: sign-up required). Uses the "outline" style, matching the bundled name index above.
TABLER_SVG_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg"
)

#: Every bundled Tabler icon name is a lowercase, hyphen-separated slug (confirmed against the
#: real, complete bundled index above) -- validated defensively before either a filesystem write
#: or a URL is built from a caller-supplied `tabler_icon_name`, so a malformed/hostile value can
#: never reach either.
_ICON_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_DEFAULT_FETCH_TIMEOUT_SECONDS = 10.0


def is_valid_icon_name_shape(icon_name: str) -> bool:
    """Whether `icon_name` has the shape every bundled Tabler icon name has (lowercase,
    hyphen-separated slug) -- does not confirm it is actually present in the bundled index."""
    return bool(icon_name) and bool(_ICON_NAME_RE.match(icon_name))


@lru_cache(maxsize=1)
def _bundled_icon_names() -> tuple[str, ...]:
    path = resource_path(*_ICON_NAMES_RESOURCE_PARTS)
    if not path.is_file():
        return ()
    return tuple(
        line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def search_bundled_tabler_icon_names(query: str) -> dict:
    """FR-QPB-121/HARNESS_CONTRACT.md function 14: a pure, offline, case-insensitive substring
    filter over the bundled Tabler icon-name index. Never performs network I/O of any kind --
    this is the offline half of FR-QPB-121; fetching a *selected* icon's SVG content is a
    distinct, separate action (:func:`resolve_svg_fetch`, below), gated by FR-QPB-011(d).

    Returns ``{"matches": list[str], "total_bundled_names": int}``.
    """
    names = _bundled_icon_names()
    query_lower = (query or "").strip().lower()
    if not query_lower:
        matches: list[str] = []
    else:
        matches = [name for name in names if query_lower in name.lower()]
    return {"matches": matches, "total_bundled_names": len(names)}


def _http_get(url: str, timeout: float) -> tuple[int, str | None, bytes | None]:
    """One, single-attempt HTTPS GET (NFR-QPB-080(2): no automatic retry loop), carrying the
    compliant, identifying User-Agent header NFR-QPB-080(1) requires. Returns
    ``(http_status, content_type, body_bytes)`` -- ``http_status`` is ``0`` (never a real HTTP
    status code) for a network-level failure that never reached a server response at all (DNS
    failure, connection refused, timeout, ...), distinguishing it from a real non-200 HTTP
    response.
    """
    request = urllib.request.Request(url, headers={"User-Agent": TABLER_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = getattr(response, "status", None) or response.getcode()
            content_type = response.headers.get("Content-Type")
            body = response.read()
            return status, content_type, body
    except urllib.error.HTTPError as exc:
        content_type = exc.headers.get("Content-Type") if exc.headers is not None else None
        return exc.code, content_type, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None, None


def fetch_tabler_icon_svg(icon_name: str, timeout: float = _DEFAULT_FETCH_TIMEOUT_SECONDS) -> dict:
    """HARNESS_CONTRACT.md function 13: a **test-only, real-network-calling reference
    implementation**, used exclusively by this application's own ``network``-marked live test
    confirming Tabler's public SVG-source endpoint. Nothing in the production build pipeline
    calls this function -- see :func:`resolve_svg_fetch` for the function `qfield_builder.build`
    actually uses.

    Returns ``{"http_status": int, "content_type": str | None, "svg_text": str | None}``.
    """
    url = TABLER_SVG_URL_TEMPLATE.format(name=icon_name)
    status, content_type, body = _http_get(url, timeout)
    svg_text = body.decode("utf-8", errors="replace") if body is not None else None
    return {"http_status": status, "content_type": content_type, "svg_text": svg_text}


def fetch_tabler_icon_svg_real(
    icon_name: str, timeout: float = _DEFAULT_FETCH_TIMEOUT_SECONDS
) -> dict:
    """The real, production Tabler SVG-fetch request (FR-QPB-011(d)) -- the one network request
    this feature ever makes, and only once the user has already selected `icon_name` from the
    offline bundled index (never for search). One attempt only (NFR-QPB-080(2): no automatic
    retry loop); carries the compliant, identifying User-Agent header (NFR-QPB-080(1)).

    Returns ``{"success": bool, "svg_content": str | None, "error": str | None}``. `error`, when
    present, is one of ``"invalid_icon_name"``, ``"network_error"``, or ``"http_error:<status>"``
    -- matching the shape of the acceptance-test fault-injection double's own `mode` values
    (`"network_error"`/`"http_error"`/`"timeout"`), which this function's own real failure modes
    are reported the same way for.
    """
    if not is_valid_icon_name_shape(icon_name):
        return {"success": False, "svg_content": None, "error": "invalid_icon_name"}

    url = TABLER_SVG_URL_TEMPLATE.format(name=icon_name)
    status, _content_type, body = _http_get(url, timeout)
    if status == 200 and body is not None:
        return {
            "success": True,
            "svg_content": body.decode("utf-8", errors="replace"),
            "error": None,
        }
    if status == 0:
        return {"success": False, "svg_content": None, "error": "network_error"}
    return {"success": False, "svg_content": None, "error": f"http_error:{status}"}


def _fake_svg_fetch(fake_config: dict) -> dict:
    """The deterministic fault-injection double for the single Tabler SVG-fetch request --
    mirrors :func:`qfield_builder.vworld_tiles.make_fake_tile_fetcher`'s own precedent. `mode` is
    one of ``"success"``/``"network_error"``/``"http_error"``/``"timeout"`` (HARNESS_CONTRACT.md's
    `build_project` config additions for this round)."""
    mode = fake_config.get("mode")
    if mode == "success":
        return {"success": True, "svg_content": fake_config.get("svg_content", ""), "error": None}
    if mode in ("network_error", "http_error", "timeout"):
        return {"success": False, "svg_content": None, "error": mode}
    raise ValueError(f"Unknown fake symbol_styling.tabler_svg_fetch mode: {mode!r}")


def resolve_svg_fetch(symbol_styling_config: dict, icon_name: str) -> dict:
    """Resolves the configured Tabler SVG-fetch mechanism for `qfield_builder.build`: the real
    network fetch (:func:`fetch_tabler_icon_svg_real`) by default, or the deterministic fake
    double when ``symbol_styling_config["tabler_svg_fetch"]["fake"]`` is present -- a test seam,
    analogous to dependency injection, that never changes the production default when omitted
    (mirrors :func:`qfield_builder.vworld_tiles.resolve_tile_fetcher` exactly).

    Returns ``{"success": bool, "svg_content": str | None, "error": str | None}``.
    """
    fetch_config = symbol_styling_config.get("tabler_svg_fetch")
    if fetch_config and "fake" in fetch_config:
        return _fake_svg_fetch(fetch_config["fake"])
    return fetch_tabler_icon_svg_real(icon_name)


# --- Live preview-SVG fetch during search (FR-QPB-011(d)(ii), NFR-QPB-080(5)-(8), AC-QPB-117; ---
# --- Decision Log D-76) -------------------------------------------------------------------------


#: NFR-QPB-080(7): "concurrency for in-flight preview fetches must be bounded to a small,
#: reasonable number at any one time -- never one unbounded, simultaneous request fired per every
#: currently visible result at once." The exact bound is an implementation detail the
#: specification explicitly leaves to the implementer (mirrors the debounce-interval precedent,
#: Decision Log D-27/D-75) -- chosen conservatively here, well below this page's own
#: `_MAX_DISPLAYED_MATCHES = 100` UI cap.
PREVIEW_FETCH_MAX_CONCURRENCY = 4


def fetch_tabler_icon_preview_svgs(icon_names: list[str], preview_svg_fetch: dict) -> dict:
    """HARNESS_CONTRACT.md function 20 (Decision Log D-76): a **pure, offline, GUI-independent
    reference implementation** of "fetch a preview SVG for each of a given set of currently
    visible/matched icon names, degrading gracefully per name on failure" -- mirrors
    :func:`search_bundled_tabler_icon_names`'s own precedent for exposing a pure piece of this
    feature's logic headlessly, independently of the PySide6 keystroke/debounce event this
    function itself never touches.

    `preview_svg_fetch` is **fake-double-only** here -- there is no "real network" mode;
    ``preview_svg_fetch["fake"]`` is always required (mirrors this module's own established
    ``tabler_svg_fetch.fake`` convention, function 13/15's sibling selection-fetch double). The
    real, production, bounded-concurrency dispatch mechanism the wizard widget actually calls is
    :func:`dispatch_preview_fetches_real`, below -- never this function.

    ``preview_svg_fetch["fake"]`` shape::

        {
          "default": {"mode": "success" | "network_error" | "http_error" | "timeout",
                      "svg_content": str},
          "overrides": {              # optional
            "<icon_name>": {"mode": ..., "svg_content": str},   # same shape, per-name
          },
        }

    ``"default"`` applies to every name in `icon_names` not individually listed in
    ``"overrides"``; `mode`/`svg_content` have the identical meaning
    :func:`_fake_svg_fetch`'s own ``tabler_svg_fetch.fake`` convention already gives them.

    Returns ``{"requested_names": list[str], "previews": {<icon_name>: {"success": bool,
    "svg_content": str | None, "error": str | None}, ...}}`` -- `requested_names` is exactly
    `icon_names`, unchanged, unexpanded, in the same order (FR-QPB-011(d)(ii): never an unbounded
    background prefetch of the entire bundled index, never for a result not currently visible);
    `previews` always has exactly one entry per given name, regardless of that name's own fetch
    outcome -- one name's failure never raises, never omits, and never blocks any other name's
    own entry from being reported (AC-QPB-117).
    """
    fake_config = preview_svg_fetch["fake"]
    default_entry = fake_config["default"]
    overrides = fake_config.get("overrides", {})
    previews = {
        name: _fake_svg_fetch(overrides.get(name, default_entry)) for name in icon_names
    }
    return {"requested_names": list(icon_names), "previews": previews}


def dispatch_preview_fetches_real(
    icon_names: list[str],
    fetch_one=None,
    max_workers: int = PREVIEW_FETCH_MAX_CONCURRENCY,
) -> dict:
    """The real, production live-preview-fetch dispatch mechanism
    (FR-QPB-011(d)(ii)/NFR-QPB-080 clauses (5)-(8); Decision Log D-76) -- called by the wizard's
    ``SymbolStylingPage`` (:mod:`qfield_builder.ui.wizard`) once per debounced search settle, for
    exactly the icon names currently visible/matched on screen at that moment. The caller is
    solely responsible for narrowing `icon_names` to that visible set and for debouncing how
    often this is called (NFR-QPB-080(6)) -- this function itself never expands the given set and
    has no notion of "search" or "keystroke" at all.

    Concurrency is bounded to `max_workers` (NFR-QPB-080(7)) via a small thread pool, rather than
    firing one unbounded, simultaneous request per visible name at once. Each name is fetched via
    `fetch_one` (defaults to :func:`fetch_tabler_icon_svg_real`, the same per-icon fetch function
    the existing fetch-on-selection mechanism already uses -- so this automatically carries the
    identical compliant `TABLER_USER_AGENT` header and single-attempt-per-name discipline,
    NFR-QPB-080 clauses (1)/(2)/(5), without duplicating that logic here).

    One name's fetch failing, or raising unexpectedly, never blocks or drops any other name's own
    result, and never propagates out of this function (NFR-QPB-080(8)/AC-QPB-117): every name in
    `icon_names` is guaranteed an entry in the returned `"previews"` dict.

    Returns the identical shape :func:`fetch_tabler_icon_preview_svgs` returns:
    ``{"requested_names": list[str], "previews": {<name>: {"success": bool, "svg_content": str |
    None, "error": str | None}, ...}}``.
    """
    if fetch_one is None:
        fetch_one = fetch_tabler_icon_svg_real

    if not icon_names:
        return {"requested_names": [], "previews": {}}

    previews: dict[str, dict] = {}
    worker_count = max(1, min(max_workers, len(icon_names)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_name = {executor.submit(fetch_one, name): name for name in icon_names}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                previews[name] = future.result()
            except Exception as exc:  # noqa: BLE001 -- one name's crash must never sink the batch
                previews[name] = {
                    "success": False,
                    "svg_content": None,
                    "error": f"unexpected_error:{exc}",
                }
    return {"requested_names": list(icon_names), "previews": previews}
