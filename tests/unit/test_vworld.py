"""Unit tests for qfield_builder.vworld (Section 10, FR-QPB-071 revised/072 revised/074,
Decision Log D-26/D-29, Open Question O-12).

Layer discovery (`fetch_supported_layers`/`parse_wmts_capabilities_xml`) and the online-layer
WMTS connection-detail extraction (`fetch_wmts_layer_details`/`parse_wmts_layer_details`/
`build_wmts_layer_uri`) are tested entirely offline via realistic fixture XML and an injected
`fetch_fn` -- no real network access is required for the default test run. The one test that
genuinely queries the real VWorld capabilities endpoint is marked `@pytest.mark.network`
(mirroring the exact convention already used by
`tests/acceptance/qfield_project_builder/test_basemap_online.py` and
`tests/unit/test_osm_tiles.py`) and is skipped by default.

Live-verification note (Open Question O-12): no real VWorld API key was available in the
implementation environment (`QPB_TEST_VWORLD_API_KEY` unset), so the exact `TileMatrixSet`/
`Format`/`Style` values a real VWorld capabilities response advertises per layer were *not*
confirmed against the live endpoint. `SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS` below is
instead structured per the standard OGC WMTS 1.0.0 GetCapabilities schema (the same schema shape
already relied on by the pre-existing `SAMPLE_CAPABILITIES_XML` fixture) -- this is a realistic
but unverified stand-in; the values within it (e.g. `EPSG:900913`, `image/png`) are common WMTS
conventions, not confirmed VWorld-specific values.
"""
from __future__ import annotations

import pytest

from qfield_builder.vworld import (
    ATTRIBUTION_TEXT_EN,
    VWorldCapabilitiesError,
    WmtsLayerDetails,
    build_gettile_url,
    build_tile_request_url,
    build_wmts_layer_uri,
    clear_capabilities_cache,
    fetch_capabilities_xml,
    fetch_supported_layers,
    fetch_wmts_layer_details,
    parse_wmts_capabilities_xml,
    parse_wmts_layer_details,
    resolve_wmts_layer_details,
    supported_layers,
)

# A representative WMTS GetCapabilities XML fixture naming the five currently-known VWorld
# layers, in the same shape (namespaced `ows:Identifier` inside each `Layer`) the real VWorld
# endpoint is documented to return.
SAMPLE_CAPABILITIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink">
  <Contents>
    <Layer>
      <ows:Title>Base map</ows:Title>
      <ows:Identifier>Base</ows:Identifier>
    </Layer>
    <Layer>
      <ows:Title>White map</ows:Title>
      <ows:Identifier>White</ows:Identifier>
    </Layer>
    <Layer>
      <ows:Title>Midnight map</ows:Title>
      <ows:Identifier>Midnight</ows:Identifier>
    </Layer>
    <Layer>
      <ows:Title>Hybrid overlay</ows:Title>
      <ows:Identifier>Hybrid</ows:Identifier>
    </Layer>
    <Layer>
      <ows:Title>Satellite imagery</ows:Title>
      <ows:Identifier>Satellite</ows:Identifier>
    </Layer>
  </Contents>
</Capabilities>
"""

# A realistic OGC WMTS 1.0.0-standard capabilities fixture that additionally includes, per
# <Layer>, the <Style>/<Format>/<TileMatrixSetLink><TileMatrixSet> children a real WMTS server
# (VWorld included) advertises -- see the module docstring's live-verification note: this is
# built against the OGC WMTS 1.0.0 schema shape, not confirmed against a real VWorld response.
SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink">
  <Contents>
    <Layer>
      <ows:Title>Base map</ows:Title>
      <ows:Identifier>Base</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <TileMatrixSetLink>
        <TileMatrixSet>EPSG:900913</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>
    <Layer>
      <ows:Title>Satellite imagery</ows:Title>
      <ows:Identifier>Satellite</ows:Identifier>
      <Style>
        <ows:Identifier>satellite-style</ows:Identifier>
      </Style>
      <Format>image/jpeg</Format>
      <TileMatrixSetLink>
        <TileMatrixSet>EPSG:900913</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>
    <Layer>
      <ows:Title>Incomplete layer (missing TileMatrixSetLink)</ows:Title>
      <ows:Identifier>Incomplete</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
    </Layer>
  </Contents>
  <TileMatrixSet>
    <ows:Identifier>EPSG:900913</ows:Identifier>
    <ows:SupportedCRS>urn:ogc:def:crs:EPSG::900913</ows:SupportedCRS>
  </TileMatrixSet>
</Capabilities>
"""


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_capabilities_cache()
    yield
    clear_capabilities_cache()


# --- fallback/default layer set (unchanged mechanism, corrected naming) ------------------------


def test_supported_layers_matches_the_corrected_documented_set():
    assert set(supported_layers()) == {"Base", "White", "Midnight", "Hybrid", "Satellite"}


def test_supported_layers_no_longer_uses_the_old_gray_lowercase_midnight_spellings():
    layers = supported_layers()
    assert "gray" not in layers
    assert "midnight" not in layers  # lowercase; "Midnight" (capitalized) is correct now.


# --- GetTile URL template (FR-QPB-072, unchanged mechanics) ------------------------------------


def test_build_gettile_url_embeds_key_and_layer():
    url = build_gettile_url("MY-KEY", "Base")
    assert "MY-KEY" in url
    assert "/Base/" in url
    assert url.startswith("https://")
    assert "{z}" in url and "{y}" in url and "{x}" in url


def test_build_gettile_url_uses_jpeg_for_satellite():
    assert build_gettile_url("MY-KEY", "Satellite").endswith(
        "/Satellite/{z}/{y}/{x}.jpeg"
    )


def test_build_gettile_url_rejects_unsupported_layer():
    with pytest.raises(ValueError):
        build_gettile_url("KEY", "NotALayer")


def test_build_gettile_url_accepts_a_layer_from_an_explicit_known_layers_list():
    # Simulates the wizard passing through a live-discovered layer set that includes a layer not
    # in the static fallback list -- FR-QPB-071 requires supporting "every layer [the endpoint]
    # advertises", not only the five currently known ones.
    url = build_gettile_url("KEY", "SomeNewLayer", known_layers=["Base", "SomeNewLayer"])
    assert "/SomeNewLayer/" in url


def test_build_tile_request_url_substitutes_concrete_coordinates():
    url = build_tile_request_url("KEY", "White", z=12, x=100, y=200)
    assert "/12/200/100.png" in url
    assert "{z}" not in url


def test_build_tile_request_url_uses_jpeg_for_satellite():
    url = build_tile_request_url("KEY", "Satellite", z=12, x=100, y=200)

    assert url.endswith("/Satellite/12/200/100.jpeg")


# --- Bug 2 defense-in-depth: a key with embedded/surrounding whitespace must never reach a URL
# unstripped -- these are the last line of defense (the wizard/credential store are expected to
# already strip; see tests/unit/test_wizard.py and tests/unit/test_credential_store.py). ---------


def test_build_gettile_url_strips_whitespace_from_the_key():
    url = build_gettile_url("MY-KEY\n", "Base")
    assert "MY-KEY\n" not in url
    assert "MY-KEY/" in url


def test_build_tile_request_url_strips_whitespace_from_the_key():
    url = build_tile_request_url(" MY-KEY \t", "White", z=12, x=100, y=200)
    assert " " not in url
    assert "\t" not in url
    assert "MY-KEY/White/12/200/100.png" in url


def test_attribution_text_mentions_molit_and_vworld_and_kogl():
    assert "vworld" in ATTRIBUTION_TEXT_EN.lower()
    assert "ministry of land" in ATTRIBUTION_TEXT_EN.lower()
    assert "korea open government license" in ATTRIBUTION_TEXT_EN.lower()


# --- WMTS capabilities XML parsing (FR-QPB-071 revised, Decision Log D-26) ---------------------


def test_parse_wmts_capabilities_xml_extracts_all_five_layer_identifiers():
    layers = parse_wmts_capabilities_xml(SAMPLE_CAPABILITIES_XML)
    assert layers == ["Base", "White", "Midnight", "Hybrid", "Satellite"]


def test_parse_wmts_capabilities_xml_is_namespace_agnostic():
    # A differently-prefixed (but equivalent) namespace declaration must still parse correctly --
    # matching is done by local (namespace-stripped) element name, not a hardcoded namespace URI.
    xml_text = SAMPLE_CAPABILITIES_XML.replace("ows:", "owsalt:").replace(
        'xmlns:ows="http://www.opengis.net/ows/1.1"',
        'xmlns:owsalt="http://www.opengis.net/ows/1.1"',
    )
    layers = parse_wmts_capabilities_xml(xml_text)
    assert set(layers) == {"Base", "White", "Midnight", "Hybrid", "Satellite"}


def test_parse_wmts_capabilities_xml_rejects_malformed_xml():
    with pytest.raises(VWorldCapabilitiesError):
        parse_wmts_capabilities_xml("<Capabilities><Layer>not closed")


def test_parse_wmts_capabilities_xml_rejects_xml_with_no_layers():
    with pytest.raises(VWorldCapabilitiesError):
        parse_wmts_capabilities_xml("<Capabilities><Contents/></Capabilities>")


# --- WMTS per-layer connection-detail parsing (FR-QPB-072 revised, D-29, Open Question O-12) ----


def test_parse_wmts_layer_details_extracts_tile_matrix_set_format_and_default_style():
    details = parse_wmts_layer_details(SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS)
    base = details["Base"]
    assert base == WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )


def test_parse_wmts_layer_details_falls_back_to_the_first_style_when_none_is_marked_default():
    details = parse_wmts_layer_details(SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS)
    satellite = details["Satellite"]
    assert satellite.style == "satellite-style"
    assert satellite.format == "image/jpeg"
    assert satellite.tile_matrix_set == "EPSG:900913"


def test_parse_wmts_layer_details_omits_a_layer_missing_required_connection_details():
    details = parse_wmts_layer_details(SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS)
    # "Incomplete" has no <TileMatrixSetLink> at all -- not enough information for a QGIS WMTS
    # connection, so it must be silently omitted rather than half-populated.
    assert "Incomplete" not in details


def test_parse_wmts_layer_details_is_namespace_agnostic():
    xml_text = SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS.replace("ows:", "owsalt:").replace(
        'xmlns:ows="http://www.opengis.net/ows/1.1"',
        'xmlns:owsalt="http://www.opengis.net/ows/1.1"',
    )
    details = parse_wmts_layer_details(xml_text)
    assert details["Base"].style == "default"


def test_parse_wmts_layer_details_rejects_malformed_xml():
    with pytest.raises(VWorldCapabilitiesError):
        parse_wmts_layer_details("<Capabilities><Layer>not closed")


def test_parse_wmts_layer_details_returns_empty_dict_for_layers_with_no_details_at_all():
    # SAMPLE_CAPABILITIES_XML (the pre-existing, name-only fixture) has no Style/Format/
    # TileMatrixSetLink children at all -- every layer should be omitted, not crash.
    details = parse_wmts_layer_details(SAMPLE_CAPABILITIES_XML)
    assert details == {}


def test_fetch_wmts_layer_details_returns_the_parsed_details_for_the_requested_layer():
    details = fetch_wmts_layer_details(
        "MY-KEY", "Base", fetch_fn=lambda url: SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS  # noqa: ARG005
    )
    assert details.identifier == "Base"
    assert details.tile_matrix_set == "EPSG:900913"
    assert details.format == "image/png"
    assert details.style == "default"


def test_fetch_wmts_layer_details_raises_a_clear_error_for_a_layer_missing_connection_details():
    with pytest.raises(VWorldCapabilitiesError):
        fetch_wmts_layer_details(
            "MY-KEY",
            "Incomplete",
            fetch_fn=lambda url: SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS,  # noqa: ARG005
        )


def test_fetch_wmts_layer_details_caches_within_session_by_default():
    call_count = 0

    def _counting_fetch(url: str) -> str:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS

    fetch_wmts_layer_details("MY-KEY", "Base", fetch_fn=_counting_fetch)
    fetch_wmts_layer_details("MY-KEY", "Base", fetch_fn=_counting_fetch)
    assert call_count == 1


# --- QGIS native-WMTS datasource URI construction (FR-QPB-072 revised, D-29, AC-QPB-068) --------


def test_build_wmts_layer_uri_contains_the_capabilities_url_and_all_required_parameters():
    details = WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )
    uri = build_wmts_layer_uri("MY-KEY", "Base", details)
    assert "url=https://api.vworld.kr/req/wmts/1.0.0/MY-KEY/WMTSCapabilities.xml" in uri
    assert "layers=Base" in uri
    assert "styles=default" in uri
    assert "format=image/png" in uri or "format=image%2Fpng" in uri
    assert "tileMatrixSet=EPSG:900913" in uri or "tileMatrixSet=EPSG%3A900913" in uri
    assert "crs=" in uri


def test_build_wmts_layer_uri_never_contains_a_per_tile_gettile_template():
    # AC-QPB-068: must NOT contain a manually constructed per-tile XYZ URL template, and must NOT
    # be a `type=xyz` datasource.
    details = WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )
    uri = build_wmts_layer_uri("MY-KEY", "Base", details)
    assert "type=xyz" not in uri
    assert "{z}" not in uri and "{y}" not in uri and "{x}" not in uri
    assert "/Base/" not in uri  # no per-tile GetTile path segment for the layer


def test_build_wmts_layer_uri_derives_crs_from_an_epsg_style_tile_matrix_set_identifier():
    details = WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )
    uri = build_wmts_layer_uri("MY-KEY", "Base", details)
    assert "crs=EPSG:900913" in uri or "crs=EPSG%3A900913" in uri


def test_build_wmts_layer_uri_strips_whitespace_from_the_key():
    """Bug 2 regression: the capabilities URL embedded in this datasource URI (`url=...`) must
    never contain a raw newline/whitespace from the key -- this is exactly the shape of URL that
    crashed with `URL can't contain control characters.` when QGIS tried to connect to it."""
    details = WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )
    uri = build_wmts_layer_uri("MY-KEY\n", "Base", details)
    assert "MY-KEY\n" not in uri
    assert "url=https://api.vworld.kr/req/wmts/1.0.0/MY-KEY/WMTSCapabilities.xml" in uri


def test_build_wmts_layer_uri_falls_back_to_the_configured_default_crs_when_unrecognizable():
    details = WmtsLayerDetails(
        identifier="Custom",
        tile_matrix_set="GoogleMapsCompatible",
        format="image/png",
        style="default",
    )
    uri = build_wmts_layer_uri("MY-KEY", "Custom", details)
    assert "crs=EPSG:3857" in uri or "crs=EPSG%3A3857" in uri


def test_build_wmts_layer_uri_accepts_an_explicit_crs_override():
    details = WmtsLayerDetails(
        identifier="Base", tile_matrix_set="EPSG:900913", format="image/png", style="default"
    )
    uri = build_wmts_layer_uri("MY-KEY", "Base", details, crs="EPSG:4326")
    assert "crs=EPSG:4326" in uri or "crs=EPSG%3A4326" in uri


def test_satellite_fallback_keeps_its_native_wmts_connection_values():
    """An offline/invalid-key build must not flatten Satellite to generic WMTS defaults."""
    details = resolve_wmts_layer_details(
        "MY-KEY",
        "Satellite",
        # The fixture deliberately has no WMTS details, exercising the configured fallback.
        fetch_fn=lambda url: SAMPLE_CAPABILITIES_XML,  # noqa: ARG005
    )

    assert details == WmtsLayerDetails(
        identifier="Satellite",
        tile_matrix_set="GoogleMapsCompatible",
        format="image/jpeg",
        style="default",
        crs="EPSG:3857",
    )
    uri = build_wmts_layer_uri("MY-KEY", "Satellite", details)
    assert "tileMatrixSet=GoogleMapsCompatible" in uri
    assert "crs=EPSG:3857" in uri
    assert "layers=Satellite" in uri
    assert "format=image/jpeg" in uri or "format=image%2Fjpeg" in uri
    assert "EPSG:900913" not in uri
    assert "image/png" not in uri


def test_resolve_wmts_layer_details_can_skip_generation_time_network_io():
    def _must_not_fetch(_url):
        raise AssertionError("project generation must not request capabilities")

    details = resolve_wmts_layer_details(
        "MY-KEY", "Satellite", fetch_fn=_must_not_fetch, allow_network=False
    )

    assert details.identifier == "Satellite"
    assert details.tile_matrix_set == "GoogleMapsCompatible"
    assert details.format == "image/jpeg"


# --- fetch_capabilities_xml / fetch_supported_layers (offline via injected fetch_fn) ------------


def test_fetch_capabilities_xml_uses_injected_fetch_fn_with_the_documented_url():
    captured_urls = []

    def _fake_fetch(url: str) -> str:
        captured_urls.append(url)
        return SAMPLE_CAPABILITIES_XML

    xml_text = fetch_capabilities_xml("MY-KEY", fetch_fn=_fake_fetch)
    assert xml_text == SAMPLE_CAPABILITIES_XML
    assert captured_urls == [
        "https://api.vworld.kr/req/wmts/1.0.0/MY-KEY/WMTSCapabilities.xml"
    ]


def test_fetch_capabilities_xml_strips_whitespace_from_the_key_before_building_the_url():
    """Bug 2 regression: a key with an embedded/trailing newline (e.g. from a stray keystroke or
    a paste) used to crash with `URL can't contain control characters.` -- the key must be
    stripped before it is ever substituted into the capabilities URL."""
    captured_urls = []

    def _fake_fetch(url: str) -> str:
        captured_urls.append(url)
        return SAMPLE_CAPABILITIES_XML

    xml_text = fetch_capabilities_xml("MY-KEY\n", fetch_fn=_fake_fetch)
    assert xml_text == SAMPLE_CAPABILITIES_XML
    assert captured_urls == [
        "https://api.vworld.kr/req/wmts/1.0.0/MY-KEY/WMTSCapabilities.xml"
    ]


def test_fetch_capabilities_xml_wraps_a_raising_fetch_fn_in_a_clear_error():
    def _failing_fetch(url: str) -> str:  # noqa: ARG001
        raise ConnectionError("simulated network failure")

    with pytest.raises(VWorldCapabilitiesError):
        fetch_capabilities_xml("MY-KEY", fetch_fn=_failing_fetch)


def test_fetch_supported_layers_returns_the_parsed_live_layer_set():
    layers = fetch_supported_layers(
        "MY-KEY", fetch_fn=lambda url: SAMPLE_CAPABILITIES_XML  # noqa: ARG005
    )
    assert layers == ["Base", "White", "Midnight", "Hybrid", "Satellite"]


def test_fetch_supported_layers_propagates_a_clear_error_and_never_crashes_ambiguously():
    def _malformed_fetch(url: str) -> str:  # noqa: ARG001
        return "not xml at all <<<"

    with pytest.raises(VWorldCapabilitiesError):
        fetch_supported_layers("MY-KEY", fetch_fn=_malformed_fetch)


def test_fetch_supported_layers_caches_within_session_by_default():
    call_count = 0

    def _counting_fetch(url: str) -> str:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return SAMPLE_CAPABILITIES_XML

    fetch_supported_layers("MY-KEY", fetch_fn=_counting_fetch)
    fetch_supported_layers("MY-KEY", fetch_fn=_counting_fetch)
    assert call_count == 1, "a second call for the same key must be served from the session cache"


def test_fetch_supported_layers_use_cache_false_forces_a_fresh_query():
    call_count = 0

    def _counting_fetch(url: str) -> str:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return SAMPLE_CAPABILITIES_XML

    fetch_supported_layers("MY-KEY", fetch_fn=_counting_fetch)
    fetch_supported_layers("MY-KEY", fetch_fn=_counting_fetch, use_cache=False)
    assert call_count == 2


# --- Live network variant (skipped by default; run with --run-network and a real API key) ------


@pytest.mark.network
def test_fetch_supported_layers_against_the_real_vworld_endpoint():
    """Requires `--run-network` and a real VWorld API key exported as
    `QPB_TEST_VWORLD_API_KEY`; skipped by default (mirrors the acceptance suite's own
    `--run-network`-gated real VWorld tests)."""
    import os

    real_key = os.environ.get("QPB_TEST_VWORLD_API_KEY")
    if not real_key:
        pytest.skip("QPB_TEST_VWORLD_API_KEY not set")
    layers = fetch_supported_layers(real_key, use_cache=False)
    assert isinstance(layers, list) and layers


@pytest.mark.network
def test_fetch_wmts_layer_details_against_the_real_vworld_endpoint():
    """Requires `--run-network` and a real VWorld API key exported as
    `QPB_TEST_VWORLD_API_KEY`; skipped by default. Open Question O-12: this is the one test that
    would confirm the real TileMatrixSet/Format/Style values VWorld's capabilities response
    actually advertises -- it was not possible to run this against a real key in the
    implementation environment (see the module docstring's live-verification note)."""
    import os

    real_key = os.environ.get("QPB_TEST_VWORLD_API_KEY")
    if not real_key:
        pytest.skip("QPB_TEST_VWORLD_API_KEY not set")
    layers = fetch_supported_layers(real_key, use_cache=False)
    assert layers
    details = fetch_wmts_layer_details(real_key, layers[0], use_cache=False)
    assert details.tile_matrix_set
    assert details.format
    assert details.style
