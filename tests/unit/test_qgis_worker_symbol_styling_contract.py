"""Dependency-free symbol-routing contract checks."""

from qfield_builder import qgis_worker


def test_tabler_svg_excludes_only_canonical_site(monkeypatch):
    class Geometry:
        geom_type = "POINT"

    class Table:
        geometry = Geometry()

    layers = {"site": object(), "plot": object(), "observation": object()}
    svg_layers = []
    minimalist_layers = []
    monkeypatch.setattr(
        qgis_worker, "_apply_svg_point_symbology",
        lambda _pyqgis, layer, _path: svg_layers.append(layer),
    )
    monkeypatch.setattr(
        qgis_worker, "_apply_minimalist_point_symbology",
        lambda _pyqgis, layer: minimalist_layers.append(layer),
    )

    qgis_worker._apply_symbol_styling(
        {}, {name: Table() for name in layers}, layers, "symbols/map-pin.svg"
    )

    assert minimalist_layers == [layers["site"]]
    assert svg_layers == [layers["plot"], layers["observation"]]
