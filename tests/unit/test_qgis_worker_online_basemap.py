"""Unit tests for `qfield_builder.qgis_worker._add_online_basemap_layer` (FR-QPB-072 revised;
Decision Log D-29; AC-QPB-068).

`_add_online_basemap_layer` only receives an already-built `pyqgis` dict (a lookup of already-
imported `qgis.core` classes) and a `project`-like object -- it never imports `qgis.core` itself
-- so it can be exercised entirely offline, without a real QGIS/PyQGIS environment, by supplying
minimal fake stand-ins for `QgsRasterLayer` and the project/layer-tree objects it calls. This
mirrors this module's own top-of-file guarantee: "every `qgis.*` import is... local to the
functions that need it, so importing this *module*... never requires PyQGIS to be installed".
"""
from __future__ import annotations

import pytest

from qfield_builder import qgis_worker
from qfield_builder.vworld import VWorldCapabilitiesError, clear_capabilities_cache

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
  </Contents>
</Capabilities>
"""


class _FakeRasterLayer:
    """Minimal stand-in for `QgsRasterLayer`: records constructor args and metadata calls."""

    def __init__(self, uri, name, provider):
        self.uri = uri
        self.name = name
        self.provider = provider
        self._abstract = ""
        self._metadata = _FakeMetadata()

    def setAbstract(self, text):
        self._abstract = text

    def metadata(self):
        return self._metadata

    def setMetadata(self, metadata):
        self._metadata = metadata


class _FakeMetadata:
    def __init__(self):
        self._abstract = ""

    def abstract(self):
        return self._abstract

    def setAbstract(self, text):
        self._abstract = text


class _FakeLayerTreeGroup:
    def __init__(self):
        self.added_layers = []
        self._checked = False

    def setItemVisibilityChecked(self, checked):
        self._checked = checked

    def itemVisibilityChecked(self):
        return self._checked

    def addLayer(self, layer):
        self.added_layers.append(layer)
        return _FakeLayerTreeLayer()


class _FakeLayerTreeLayer:
    def __init__(self):
        self._checked = False

    def setItemVisibilityChecked(self, checked):
        self._checked = checked

    def itemVisibilityChecked(self):
        return self._checked


class _FakeLayerTreeRoot:
    def __init__(self):
        self._basemap_group = _FakeLayerTreeGroup()

    def findGroup(self, name):
        return self._basemap_group if name == "Basemap" else None


class _FakeProject:
    def __init__(self):
        self.added_map_layers = []
        self._root = _FakeLayerTreeRoot()

    def addMapLayer(self, layer, add_to_legend):  # noqa: ARG002 - mirrors real QgsProject signature
        self.added_map_layers.append(layer)

    def layerTreeRoot(self):
        return self._root


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_capabilities_cache()
    yield
    clear_capabilities_cache()


def _pyqgis():
    return {"QgsRasterLayer": _FakeRasterLayer}


def _basemap_config(**overrides):
    config = {
        "mode": "online",
        "consent_accepted": True,
        "vworld_api_key": "MY-KEY",
        "layer": "Base",
        "known_vworld_layers": ["Base", "White", "Midnight", "Hybrid", "Satellite"],
    }
    config.update(overrides)
    return config


def _fetch_fn(url):  # noqa: ARG001
    return SAMPLE_CAPABILITIES_XML_WITH_WMTS_DETAILS


def _add_online_basemap_layer_with_fake_fetch(project, basemap_config):
    """Calls `_add_online_basemap_layer` with `vworld.fetch_capabilities_xml` monkeypatched to
    use an injected fetch function instead of live network access -- the same test-seam pattern
    `fetch_wmts_layer_details`/`fetch_capabilities_xml` already support via `fetch_fn=`, applied
    here via a direct monkeypatch since `_add_online_basemap_layer` itself does not expose a
    `fetch_fn` parameter (it calls `vworld.fetch_wmts_layer_details` with only two arguments,
    matching how the real GIS worker process calls it during a real build)."""
    from qfield_builder import vworld as vworld_module

    original = vworld_module.fetch_capabilities_xml

    def _patched(api_key, fetch_fn=None, timeout_seconds=15.0):  # noqa: ARG001
        return original(api_key, fetch_fn=_fetch_fn, timeout_seconds=timeout_seconds)

    vworld_module.fetch_capabilities_xml = _patched
    try:
        return qgis_worker._add_online_basemap_layer(_pyqgis(), project, basemap_config)
    finally:
        vworld_module.fetch_capabilities_xml = original


def test_online_layer_returns_true_and_is_added_to_the_basemap_group_when_consent_accepted():
    project = _FakeProject()
    result = _add_online_basemap_layer_with_fake_fetch(project, _basemap_config())

    assert result is True
    assert len(project.added_map_layers) == 1
    layer = project.added_map_layers[0]
    assert layer in project._root._basemap_group.added_layers
    assert layer.name == "VWorld Base (online)"


def test_online_layer_uses_the_wms_provider_key_for_the_native_wmts_connection():
    project = _FakeProject()
    _add_online_basemap_layer_with_fake_fetch(project, _basemap_config())
    layer = project.added_map_layers[0]
    assert layer.provider == "wms"


def test_online_layer_uri_uses_the_documented_vworld_xyz_template():
    project = _FakeProject()
    _add_online_basemap_layer_with_fake_fetch(project, _basemap_config())
    layer = project.added_map_layers[0]

    assert "type=xyz" in layer.uri
    assert "https://api.vworld.kr/req/wmts/1.0.0/MY-KEY/Base/{z}/{y}/{x}.png" in layer.uri
    assert "WMTSCapabilities.xml" not in layer.uri


def test_online_layer_sets_attribution_abstract_and_metadata():
    project = _FakeProject()
    _add_online_basemap_layer_with_fake_fetch(project, _basemap_config())
    layer = project.added_map_layers[0]

    assert layer._abstract == qgis_worker.ATTRIBUTION_TEXT_EN
    assert layer.metadata().abstract() == qgis_worker.ATTRIBUTION_TEXT_EN


def test_online_layer_returns_false_and_adds_nothing_without_consent():
    project = _FakeProject()
    result = _add_online_basemap_layer_with_fake_fetch(
        project, _basemap_config(consent_accepted=False)
    )

    assert result is False
    assert project.added_map_layers == []


def test_online_layer_rejects_a_layer_name_not_in_known_vworld_layers():
    project = _FakeProject()
    with pytest.raises(ValueError):
        _add_online_basemap_layer_with_fake_fetch(
            project, _basemap_config(layer="NotALayer", known_vworld_layers=["Base"])
        )


def test_online_layer_uses_the_selected_non_satellite_vworld_xyz_endpoint():
    project = _FakeProject()
    result = _add_online_basemap_layer_with_fake_fetch(
        project,
        _basemap_config(layer="White", known_vworld_layers=["Base", "White"]),
    )

    assert result is True
    layer = project.added_map_layers[0]
    assert "type=xyz" in layer.uri
    assert "/MY-KEY/White/{z}/{y}/{x}.png" in layer.uri


def test_online_satellite_layer_uses_the_same_portable_xyz_path():
    project = _FakeProject()
    result = _add_online_basemap_layer_with_fake_fetch(
        project, _basemap_config(layer="Satellite")
    )

    assert result is True
    layer = project.added_map_layers[0]
    assert layer.provider == "wms"
    assert "type=xyz" in layer.uri
    assert "/MY-KEY/Satellite/{z}/{y}/{x}.jpeg" in layer.uri


def test_online_layer_never_requires_live_network_access_to_succeed():
    project = _FakeProject()

    result = qgis_worker._add_online_basemap_layer(_pyqgis(), project, _basemap_config())

    assert result is True
    layer = project.added_map_layers[0]
    assert "type=xyz" in layer.uri


def test_online_layer_does_not_request_capabilities_while_building_the_project(monkeypatch):
    project = _FakeProject()

    from qfield_builder import vworld as vworld_module

    monkeypatch.setattr(
        vworld_module,
        "fetch_capabilities_xml",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network requested")),
    )
    assert qgis_worker._add_online_basemap_layer(_pyqgis(), project, _basemap_config()) is True
