"""VWorld basemap configuration: layer discovery, GetTile URL template, and MOLIT attribution text.

Wraps Section 10 of the specification (FR-QPB-070-079). The per-tile GetTile URL scheme/template
is loaded from a version-controlled configuration resource
(`resources/config/vworld_layers.json`) rather than hard-coded in Python, per FR-QPB-072 ("must be
updatable via configuration, without a code change, because the external API may change").

Layer discovery (FR-QPB-071, revised; Decision Log D-26): the application's supported VWorld
layer set is no longer trusted from a hardcoded, Requirements-Draft-derived list. Instead,
:func:`fetch_supported_layers` queries the real VWorld WMTS capabilities endpoint
(``https://api.vworld.kr/req/wmts/1.0.0/{key}/WMTSCapabilities.xml``) and parses the standard OGC
WMTS GetCapabilities XML response (via the standard library's ``xml.etree.ElementTree`` -- no new
third-party XML dependency) to discover every layer identifier the endpoint currently advertises.
:func:`supported_layers` remains as the *fallback/default* known layer set -- used before any live
discovery has happened (e.g. the wizard's layer dropdown before an API key has been entered) and
as a last-resort default if a live query is never attempted -- kept in the same version-controlled
configuration resource as the GetTile URL template, and updated per this revision to the corrected
layer identifiers (`Base`, `White`, `Midnight`, `Hybrid`, `Satellite`) rather than the prior
Requirements-Draft transcription (`Base`, `gray`, `midnight`, `Hybrid`, `Satellite`). No migration
handling for the old `gray`/lowercase-`midnight` spellings is implemented: per explicit
orchestrator confirmation, no project has ever been built or shipped using them (see the
specification's Open Question O-11).

Online-layer WMTS connection details (FR-QPB-072, revised; Decision Log D-29; Open Question O-12):
:func:`parse_wmts_layer_details`/:func:`fetch_wmts_layer_details` extend the same namespace-
agnostic capabilities-XML parsing to also extract, per layer, the ``TileMatrixSet``, tile
``Format`` (MIME type), and ``Style`` identifier that QGIS's native WMTS datasource URI needs to
connect -- these values are not knowable by static inspection (per the specification's own Open
Question O-12) and are discovered from the real capabilities response, not hardcoded.
:func:`build_wmts_layer_uri` assembles the resulting QGIS ``wms``-provider datasource URI used by
:mod:`qfield_builder.qgis_worker`'s ``_add_online_basemap_layer`` for the generated project's
**online** layer only; the offline MBTiles pipeline (:func:`build_tile_request_url`) is unaffected.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from xml.etree import ElementTree

from .resource_paths import resource_path

_RESOURCE_PATH = resource_path("config", "vworld_layers.json")

ATTRIBUTION_TEXT_EN = (
    "This basemap uses the Ministry of Land, Infrastructure and Transport VWorld WMTS/TMS API "
    "under the Korea Open Government License Type 1 (attribution required). "
    "https://www.vworld.kr"
)
ATTRIBUTION_TEXT_KO = (
    "본 배경지도는 국토교통부 VWorld WMTS/TMS API를 공공누리 제1유형(출처표시) 조건에 따라 "
    "사용합니다. https://www.vworld.kr"
)

# FR-QPB-071 (revised; Decision Log D-26): the VWorld WMTS capabilities endpoint -- the same
# VWorld host already used by the GetTile URL template (FR-QPB-072), just a different documented
# path, queried to discover the currently advertised layer set rather than to fetch a map tile.
CAPABILITIES_URL_TEMPLATE = "https://api.vworld.kr/req/wmts/1.0.0/{key}/WMTSCapabilities.xml"

# A namespace-agnostic search is used (see `_local_tag`) because different VWorld API versions/
# environments have been observed to vary the WMTS/OWS XML namespace URIs and prefixes used in
# their capabilities response; matching on local (namespace-stripped) element names is robust to
# that without depending on any specific namespace URI string.
_LAYER_TAG = "Layer"
_IDENTIFIER_TAG = "Identifier"
_FORMAT_TAG = "Format"
_STYLE_TAG = "Style"
_TILE_MATRIX_SET_LINK_TAG = "TileMatrixSetLink"
_TILE_MATRIX_SET_TAG = "TileMatrixSet"

# Matches an EPSG numeric code embedded anywhere in a TileMatrixSet identifier or an OGC URN-form
# SupportedCRS value (e.g. "EPSG:900913", "EPSG:3857", "urn:ogc:def:crs:EPSG::3857").
_EPSG_CODE_PATTERN = re.compile(r"EPSG[:.]{1,2}(\d+)", re.IGNORECASE)


class VWorldCapabilitiesError(RuntimeError):
    """Raised when the VWorld WMTS capabilities endpoint cannot be queried or parsed successfully.

    The message is always a clear, actionable, non-technical description (never a raw network
    traceback or XML parser internals) suitable for direct display to the user, per this
    requirement's "must not crash, and must not silently fall back to a stale hardcoded list
    without telling the user" clause.
    """


def _local_tag(tag: str) -> str:
    """The element's tag name with any XML namespace prefix (`{uri}Name` -> `Name`) stripped."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


@lru_cache(maxsize=1)
def _config() -> dict:
    if _RESOURCE_PATH.exists():
        return json.loads(_RESOURCE_PATH.read_text(encoding="utf-8"))
    # Defensive fallback so a missing/uninstalled resource file never crashes the app; the
    # authoritative, updatable copy still lives in resources/config/vworld_layers.json.
    return {
        "layers": ["Base", "White", "Midnight", "Hybrid", "Satellite"],
        "url_template": "https://api.vworld.kr/req/wmts/1.0.0/{key}/{layer}/{z}/{y}/{x}.png",
        "default_wmts_crs": "EPSG:3857",
        "default_wmts_tile_matrix_set": "EPSG:900913",
        "default_wmts_format": "image/png",
        "default_wmts_style": "default",
    }


def supported_layers() -> list[str]:
    """The fallback/default known VWorld layer set.

    This is **not** the authoritative discovery mechanism required by FR-QPB-071 (revised) --
    that is :func:`fetch_supported_layers`, which queries the live VWorld WMTS capabilities
    endpoint. This function remains as: (1) the layer list shown before the user has entered a
    VWorld API key (the capabilities endpoint requires the key in its URL, so nothing can be
    queried yet); and (2) a last-resort default if a live capabilities query has never
    successfully completed. As of this revision the five layers listed here are the five
    currently known to be advertised by the real endpoint (`Base`, `White`, `Midnight`, `Hybrid`,
    `Satellite`) -- this corrects the prior Requirements-Draft transcription (`gray`,
    lowercase-`midnight`).
    """
    return list(_config()["layers"])


def parse_wmts_capabilities_xml(xml_text: str) -> list[str]:
    """Parse a WMTS GetCapabilities XML document and return every advertised layer identifier.

    Looks for ``<Layer>`` elements (any XML namespace) and reads each one's own ``<Identifier>``
    child (the standard OGC WMTS convention; VWorld's response uses the `ows:Identifier` element,
    matched here by local name only, namespace-agnostically -- see :func:`_local_tag`).

    Raises :class:`VWorldCapabilitiesError` if the text is not parseable XML, or is parseable but
    contains no recognizable ``Layer``/``Identifier`` pair.
    """
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise VWorldCapabilitiesError(
            "The VWorld map-layer list could not be read because the server's response was not "
            "valid XML. Please try again later, or contact VWorld support if this continues."
        ) from exc

    layers: list[str] = []
    for element in root.iter():
        if _local_tag(element.tag) != _LAYER_TAG:
            continue
        for child in element:
            if _local_tag(child.tag) == _IDENTIFIER_TAG:
                identifier = (child.text or "").strip()
                if identifier:
                    layers.append(identifier)
                break

    if not layers:
        raise VWorldCapabilitiesError(
            "The VWorld map-layer list could not be read because the server's response did not "
            "contain any recognizable layer information. Please try again later, or contact "
            "VWorld support if this continues."
        )
    return layers


@dataclass(frozen=True)
class WmtsLayerDetails:
    """Per-layer WMTS connection details extracted from a real capabilities response.

    These are exactly the values QGIS's native WMTS provider (the `wms` provider key, used for
    both WMS and WMTS connections) needs, beyond the capabilities URL itself and the layer
    identifier, to build a working datasource URI (FR-QPB-072, revised; Decision Log D-29):
    which ``TileMatrixSet`` to use, which tile ``Format`` (MIME type) to request, and which
    ``Style`` to request. ``crs`` is normally derived from the tile-matrix-set identifier, but a
    configured layer-specific fallback may state it explicitly when the identifier itself does
    not encode an EPSG code (for example VWorld's ``GoogleMapsCompatible`` Satellite fallback).
    Live capabilities values remain authoritative whenever they are available.
    """

    identifier: str
    tile_matrix_set: str
    format: str
    style: str
    crs: str | None = None


def parse_wmts_layer_details(xml_text: str) -> dict[str, WmtsLayerDetails]:
    """Parse a WMTS GetCapabilities XML document and return, per advertised layer identifier, the
    ``TileMatrixSet``/``Format``/``Style`` values QGIS's native WMTS datasource URI needs
    (FR-QPB-072, revised; Decision Log D-29; Open Question O-12).

    Per the OGC WMTS 1.0.0 schema, each ``<Layer>`` element contains: one or more
    ``<TileMatrixSetLink><TileMatrixSet>`` entries (the first one found is used); one or more
    ``<Format>`` entries (the first one found is used); and one or more ``<Style>`` entries, each
    with its own ``<ows:Identifier>`` child and an optional ``isDefault="true"`` attribute (the
    style marked ``isDefault`` is used, falling back to the first declared style if none is
    marked default). Matching is namespace-agnostic (local tag names only), mirroring
    :func:`parse_wmts_capabilities_xml`/:func:`_local_tag`.

    A ``<Layer>`` entry missing any one of an identifier, tile matrix set, format, or style is
    silently omitted from the result (it does not have enough information for a QGIS WMTS
    connection); this function itself never raises for that reason -- callers (e.g.
    :func:`fetch_wmts_layer_details`) are responsible for reporting a missing/incomplete layer to
    the user. It raises :class:`VWorldCapabilitiesError` only if `xml_text` is not parseable XML
    at all.
    """
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise VWorldCapabilitiesError(
            "The VWorld map layer connection details could not be read because the server's "
            "response was not valid XML. Please try again later, or contact VWorld support if "
            "this continues."
        ) from exc

    details: dict[str, WmtsLayerDetails] = {}
    for element in root.iter():
        if _local_tag(element.tag) != _LAYER_TAG:
            continue

        identifier: str | None = None
        tile_matrix_set: str | None = None
        tile_format: str | None = None
        default_style: str | None = None
        first_style: str | None = None

        for child in element:
            tag = _local_tag(child.tag)
            if tag == _IDENTIFIER_TAG and identifier is None:
                identifier = (child.text or "").strip() or None
            elif tag == _FORMAT_TAG and tile_format is None:
                tile_format = (child.text or "").strip() or None
            elif tag == _TILE_MATRIX_SET_LINK_TAG and tile_matrix_set is None:
                for grandchild in child:
                    if _local_tag(grandchild.tag) == _TILE_MATRIX_SET_TAG:
                        tile_matrix_set = (grandchild.text or "").strip() or None
                        break
            elif tag == _STYLE_TAG:
                style_id = None
                for grandchild in child:
                    if _local_tag(grandchild.tag) == _IDENTIFIER_TAG:
                        style_id = (grandchild.text or "").strip() or None
                        break
                if style_id:
                    if first_style is None:
                        first_style = style_id
                    if (child.get("isDefault") or "").strip().lower() == "true":
                        default_style = style_id

        if identifier is None or tile_matrix_set is None or tile_format is None:
            continue
        style = default_style or first_style
        if style is None:
            continue
        details[identifier] = WmtsLayerDetails(
            identifier=identifier,
            tile_matrix_set=tile_matrix_set,
            format=tile_format,
            style=style,
        )

    return details


def _derive_crs_from_tile_matrix_set(tile_matrix_set: str) -> str:
    """Best-effort CRS derivation from a TileMatrixSet identifier (e.g. `EPSG:900913`) -- the
    common WMTS convention of naming a TileMatrixSet after the CRS it represents. Falls back to
    the version-controlled configuration resource's `default_wmts_crs` (Web Mercator, EPSG:3857,
    the near-universal CRS for XYZ/WMTS raster basemaps) if the identifier does not embed a
    recognizable EPSG code. This fallback is a documented, updatable assumption -- not a value
    confirmed against a real VWorld capabilities response (see Open Question O-12) -- and should
    be revisited once a real VWorld API key is available to verify it.
    """
    match = _EPSG_CODE_PATTERN.search(tile_matrix_set)
    if match:
        return f"EPSG:{match.group(1)}"
    return str(_config().get("default_wmts_crs", "EPSG:3857"))


def build_wmts_layer_uri(
    api_key: str, layer: str, details: WmtsLayerDetails, crs: str | None = None
) -> str:
    """Build the QGIS native-WMTS datasource URI for the generated project's **online** VWorld
    layer (FR-QPB-072, revised; Decision Log D-29), for use with ``QgsRasterLayer(uri, name,
    "wms")`` -- QGIS's `wms` provider key also handles WMTS connections.

    Connects via the capabilities endpoint URL itself (`url=`), with `layers`/`styles`/`format`/
    `tileMatrixSet` naming the specific layer/style/format/tile-matrix-set QGIS should negotiate
    from that capabilities document -- QGIS itself resolves the actual GetTile requests from
    these at runtime; this application never hands QGIS a manually built per-tile GetTile
    template for this online layer (contrast :func:`build_tile_request_url`, used only by the
    unaffected offline MBTiles pipeline).

    `crs`, if not supplied, is derived from `details.tile_matrix_set` (see
    :func:`_derive_crs_from_tile_matrix_set`).
    """
    resolved_crs = crs or details.crs or _derive_crs_from_tile_matrix_set(details.tile_matrix_set)
    # Bug 2 defense-in-depth: strip whitespace/control characters (e.g. an accidentally embedded
    # newline) from the key here too, as the last line of defense before it is embedded in a
    # URL -- callers are expected to already strip (see `wizard.py`'s `_collect_config` and
    # `credential_store.py`), but this function must never crash on a key that reaches it
    # unstripped.
    capabilities_url = CAPABILITIES_URL_TEMPLATE.format(key=api_key.strip())
    ordered_params = [
        ("tileMatrixSet", details.tile_matrix_set),
        ("crs", resolved_crs),
        ("layers", details.identifier),
        ("styles", details.style),
        ("format", details.format),
        ("url", capabilities_url),
    ]
    return "&".join(
        f"{key}={urllib.parse.quote(str(value), safe=':/')}" for key, value in ordered_params
    )


def fetch_capabilities_xml(
    api_key: str, fetch_fn: Callable[[str], str] | None = None, timeout_seconds: float = 15.0
) -> str:
    """Fetch the raw WMTS GetCapabilities XML text for `api_key`.

    `fetch_fn`, if supplied, is a synchronous ``Callable[[str], str]`` (the capabilities URL ->
    the raw response text) standing in for the real network request -- the same test-seam pattern
    used elsewhere in this codebase (e.g. `qfield_builder.ui.osm_tiles`'s injectable tile
    fetcher), so this can be exercised offline in tests without any live network access.

    Raises :class:`VWorldCapabilitiesError` (never a raw network exception) if the request fails
    for any reason: network error, timeout, non-2xx response, or an empty response body.
    """
    # Bug 2 defense-in-depth: see `build_wmts_layer_uri`'s matching comment.
    url = CAPABILITIES_URL_TEMPLATE.format(key=api_key.strip())
    if fetch_fn is not None:
        try:
            return fetch_fn(url)
        except VWorldCapabilitiesError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized into a clear, actionable error below.
            raise VWorldCapabilitiesError(
                "Could not retrieve the VWorld map-layer list right now. Please check your "
                "internet connection and VWorld API key, then try again."
            ) from exc

    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310
            data = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VWorldCapabilitiesError(
            "Could not retrieve the VWorld map-layer list right now. Please check your internet "
            "connection and VWorld API key, then try again."
        ) from exc

    if not data:
        raise VWorldCapabilitiesError(
            "The VWorld map-layer list could not be read because the server returned an empty "
            "response. Please try again later, or contact VWorld support if this continues."
        )
    return data.decode("utf-8", errors="replace")


# Session-level cache (FR-QPB-071's "reasonably cached-within-session" allowance): once a live
# capabilities query has succeeded for a given API key during this application run, it is not
# re-queried on every call -- callers that genuinely need a fresh query (e.g. an explicit
# "Refresh" action) can pass `use_cache=False`.
_capabilities_cache: dict[str, list[str]] = {}


def fetch_supported_layers(
    api_key: str,
    fetch_fn: Callable[[str], str] | None = None,
    use_cache: bool = True,
) -> list[str]:
    """FR-QPB-071 (revised): discover the VWorld layer set currently advertised for `api_key`.

    Queries the VWorld WMTS capabilities endpoint (or `fetch_fn`, if supplied, for tests) and
    parses the response via :func:`parse_wmts_capabilities_xml`. Raises
    :class:`VWorldCapabilitiesError` (never crashes the caller, never silently substitutes the
    static fallback list) if the endpoint cannot be reached or the response cannot be parsed --
    callers must catch this and show its message to the user.
    """
    if use_cache and api_key in _capabilities_cache:
        return list(_capabilities_cache[api_key])

    xml_text = fetch_capabilities_xml(api_key, fetch_fn=fetch_fn)
    layers = parse_wmts_capabilities_xml(xml_text)

    if use_cache:
        _capabilities_cache[api_key] = list(layers)
    return list(layers)


_layer_details_cache: dict[tuple[str, str], WmtsLayerDetails] = {}


def fetch_wmts_layer_details(
    api_key: str,
    layer: str,
    fetch_fn: Callable[[str], str] | None = None,
    use_cache: bool = True,
) -> WmtsLayerDetails:
    """FR-QPB-072 (revised; Decision Log D-29): discover the `TileMatrixSet`/`Format`/`Style`
    values QGIS's native WMTS provider needs to connect to `layer`, from the real capabilities
    response for `api_key` (Open Question O-12 -- these are not knowable by static inspection).

    Queries the same capabilities endpoint as :func:`fetch_supported_layers` (or `fetch_fn`, if
    supplied, for tests) and parses it via :func:`parse_wmts_layer_details`. Raises
    :class:`VWorldCapabilitiesError` (never crashes the caller) if the endpoint cannot be reached,
    the response cannot be parsed, or `layer` is not present in the response with a complete set
    of connection details.
    """
    cache_key = (api_key, layer)
    if use_cache and cache_key in _layer_details_cache:
        return _layer_details_cache[cache_key]

    xml_text = fetch_capabilities_xml(api_key, fetch_fn=fetch_fn)
    details_by_layer = parse_wmts_layer_details(xml_text)
    if layer not in details_by_layer:
        raise VWorldCapabilitiesError(
            f"The VWorld map layer '{layer}' does not currently advertise the connection details "
            "(tile matrix set, format, or style) this application needs in order to connect to "
            "it. Please choose a different layer, or try refreshing the layer list."
        )

    details = details_by_layer[layer]
    if use_cache:
        _layer_details_cache[cache_key] = details
    return details


def _configured_wmts_fallback_details(layer: str) -> WmtsLayerDetails:
    """Return the documented native-WMTS fallback for ``layer``.

    The generic values preserve the existing fallback for layers without a dedicated entry. A
    per-layer entry is necessary where VWorld exposes a native layer with a different matrix-set,
    CRS, or tile format; otherwise an offline build could serialize a datasource that QField
    cannot negotiate when it is later opened with a real key.
    """
    config = _config()
    by_layer = config.get("wmts_fallbacks", {})
    layer_values = by_layer.get(layer, {}) if isinstance(by_layer, dict) else {}
    if not isinstance(layer_values, dict):
        layer_values = {}

    explicit_crs = layer_values.get("crs")
    return WmtsLayerDetails(
        identifier=layer,
        tile_matrix_set=str(
            layer_values.get(
                "tile_matrix_set", config.get("default_wmts_tile_matrix_set", "EPSG:900913")
            )
        ),
        format=str(layer_values.get("format", config.get("default_wmts_format", "image/png"))),
        style=str(layer_values.get("style", config.get("default_wmts_style", "default"))),
        crs=str(explicit_crs) if explicit_crs else None,
    )


def resolve_wmts_layer_details(
    api_key: str,
    layer: str,
    fetch_fn: Callable[[str], str] | None = None,
    use_cache: bool = True,
    allow_network: bool = True,
) -> WmtsLayerDetails:
    """Best-effort resolution of `layer`'s WMTS connection details for project *generation*.

    Attempts a real, live capabilities query first (:func:`fetch_wmts_layer_details`) -- Open
    Question O-12's preferred path, using the genuine `TileMatrixSet`/`Format`/`Style` values a
    real VWorld capabilities response advertises whenever that query succeeds. If the live query
    fails for any reason (no network access, an invalid/placeholder API key, or the response not
    naming `layer` with a complete set of connection details), this function falls back to the
    version-controlled configuration resource's documented values instead of raising. The
    generic defaults apply to ordinary layers; entries under ``wmts_fallbacks`` preserve native
    layer-specific values where required. These values are documented, updatable assumptions
    rather than a replacement for a successful live capabilities response.

    This function never raises. Project generation must not depend on live network access or a
    genuine API key succeeding at generation time (e.g. this application's own test/CI
    environment, or a user generating a project before confirming their key online) -- QGIS
    itself performs the authoritative connection negotiation against the real capabilities
    endpoint the resulting datasource URI points at, at the moment a real user actually opens the
    generated project with a working key and live network access (FR-QPB-072, revised).
    """
    if not allow_network:
        return _configured_wmts_fallback_details(layer)
    try:
        return fetch_wmts_layer_details(api_key, layer, fetch_fn=fetch_fn, use_cache=use_cache)
    except VWorldCapabilitiesError:
        return _configured_wmts_fallback_details(layer)


def clear_capabilities_cache() -> None:
    """Test/diagnostic seam: clear the session-level capabilities cache."""
    _capabilities_cache.clear()
    _layer_details_cache.clear()


def build_gettile_url(api_key: str, layer: str, known_layers: list[str] | None = None) -> str:
    """The documented WMTS/XYZ GetTile URL template with `{z}/{y}/{x}` left as QGIS placeholders.

    `known_layers`, if supplied, is used as the validation set (e.g. the wizard's live-discovered
    layer list); otherwise the fallback/default set from :func:`supported_layers` is used. Actual
    per-tile GetTile URL mechanics (FR-QPB-072) are unaffected by FR-QPB-071's discovery-mechanism
    revision.
    """
    allowed = known_layers if known_layers is not None else supported_layers()
    if layer not in allowed:
        raise ValueError(f"Unsupported VWorld layer: {layer!r}")
    template = _config()["url_template"]
    # Bug 2 defense-in-depth: see `build_wmts_layer_uri`'s matching comment.
    url = template.format(key=api_key.strip(), layer=layer, z="{z}", y="{y}", x="{x}")
    # Satellite is served as JPEG in both online XYZ and offline concrete-tile requests.
    return url.removesuffix(".png") + ".jpeg" if layer == "Satellite" else url


def build_tile_request_url(api_key: str, layer: str, z: int, x: int, y: int) -> str:
    """A concrete, fully-substituted tile-download URL (used by the offline tile downloader)."""
    template = _config()["url_template"]
    # Bug 2 defense-in-depth: see `build_wmts_layer_uri`'s matching comment.
    url = template.format(key=api_key.strip(), layer=layer, z=z, y=y, x=x)
    # VWorld Satellite is the sole built-in raster layer served as JPEG rather than PNG.
    # The layer-specific WMTS fallback above uses the same format.
    return url.removesuffix(".png") + (".jpeg" if layer == "Satellite" else ".png")
