"""Unit tests for `qfield_builder.layer_lookup` (Decision Log D-80/D-84's shared table-name-based
layer-lookup helper, used by `qfield_builder.field_alias_inspect`/`qfield_builder.editor_widget_
inspect`/`qfield_builder.layer_renderer_inspect`/`qfield_builder.layer_names_inspect`).

Pure-Python tests against small fake layer/project stand-ins -- no PyQGIS needed. The real,
PyQGIS-backed end-to-end behavior is exercised by `test_layer_lookup_regression.py` (`qgis`-marked/
skipped without a real, bridgeable QGIS installation) and by every acceptance/unit test that calls
one of the four functions above.
"""
from __future__ import annotations

from qfield_builder import layer_lookup


class _FakeLayer:
    def __init__(self, name: str, source: str | None):
        self._name = name
        self._source = source

    def name(self) -> str:
        return self._name

    def source(self) -> str | None:
        return self._source


class _FakeProject:
    def __init__(self, layers: dict[str, _FakeLayer]):
        self._layers = layers

    def mapLayers(self) -> dict:
        return self._layers


def test_table_name_from_layer_parses_the_layername_parameter():
    layer = _FakeLayer("조사지", "/tmp/project.gpkg|layername=site")
    assert layer_lookup.table_name_from_layer(layer) == "site"


def test_table_name_from_layer_parses_a_relative_datasource_path():
    """Mirrors the real, relative datasource string a generated `.qgs` file actually stores
    (FR-QPB-052/DR-QPB-052-adjacent path-storage convention)."""
    layer = _FakeLayer("식물관찰", "./data/simple_inventory.gpkg|layername=inventory_observation")
    assert layer_lookup.table_name_from_layer(layer) == "inventory_observation"


def test_table_name_from_layer_returns_none_for_a_non_gpkg_source():
    """A WMTS/XYZ basemap layer's own source has no `layername=` component at all."""
    layer = _FakeLayer(
        "VWorld Base (online)",
        "type=xyz&url=https://api.vworld.kr/req/wmts/1.0.0/KEY/Base/%7Bz%7D/%7By%7D/%7Bx%7D.png",
    )
    assert layer_lookup.table_name_from_layer(layer) is None


def test_table_name_from_layer_returns_none_for_an_empty_source():
    layer = _FakeLayer("Untitled", "")
    assert layer_lookup.table_name_from_layer(layer) is None


def test_table_name_from_layer_returns_none_for_none_layer():
    assert layer_lookup.table_name_from_layer(None) is None


def test_find_layer_by_table_name_matches_regardless_of_the_layers_own_name():
    """The core Decision Log D-80/D-84 regression guard: a layer's own `.name()` may be anything
    at all (a Section 8.7 Korean display name, or something else entirely) -- lookup must succeed
    based purely on the underlying table name parsed from the layer's own data source."""
    layer = _FakeLayer("식물관찰", "/tmp/p.gpkg|layername=inventory_observation")
    project = _FakeProject({"id1": layer})
    assert layer_lookup.find_layer_by_table_name(project, "inventory_observation") is layer


def test_find_layer_by_table_name_returns_none_when_no_layer_matches():
    layer = _FakeLayer("조사", "/tmp/p.gpkg|layername=survey")
    project = _FakeProject({"id1": layer})
    assert layer_lookup.find_layer_by_table_name(project, "site") is None


def test_find_layer_by_table_name_picks_the_correct_layer_among_several():
    site_layer = _FakeLayer("조사지", "/tmp/p.gpkg|layername=site")
    survey_layer = _FakeLayer("조사", "/tmp/p.gpkg|layername=survey")
    project = _FakeProject({"a": site_layer, "b": survey_layer})
    assert layer_lookup.find_layer_by_table_name(project, "site") is site_layer
    assert layer_lookup.find_layer_by_table_name(project, "survey") is survey_layer
