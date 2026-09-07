"""`inspect_layer_renderer()` (HARNESS_CONTRACT.md function 15; FR-QPB-120/FR-QPB-121/
AC-QPB-100/AC-QPB-101/AC-QPB-104; Decision Log D-61/D-65).

PyQGIS-backed, like :mod:`qfield_builder.field_alias_inspect`: re-opens the generated `.qgs`
project, locates the named vector layer, and reports a small set of semantic, derived facts about
its configured renderer/symbol -- deliberately not the exact fill/outline color or any raw
internal QGIS symbol-layer-property dict/XML (see HARNESS_CONTRACT.md function 15's own
rationale).

**Layer lookup (Decision Log D-80/D-84 fix):** `layer_name` is, and every existing caller across
this suite already passes, the target layer's own underlying GeoPackage *table* name -- this
function locates the layer via :func:`qfield_builder.layer_lookup.find_layer_by_table_name` rather
than `lyr.name() == layer_name`, so it keeps working unchanged now that a domain layer's own
`.name()` may be a Section 8.7-confirmed Korean display name instead of its table name
(DR-QPB-078/FR-QPB-130). See `qfield_builder.layer_lookup`'s own module docstring for the full
rationale.
"""
from __future__ import annotations

import os
from pathlib import Path

from .layer_lookup import find_layer_by_table_name

_EMPTY_RESULT = {
    "renderer_class": "",
    "symbol_layer_types": [],
    "marker_shape": None,
    "svg_relative_path": None,
    "fill_style": None,
}


def _inspect_layer_renderer_pyqgis(project_dir: str, layer_name: str) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject, QgsSimpleMarkerSymbolLayerBase
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = dict(_EMPTY_RESULT)
    result["symbol_layer_types"] = []

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject()
    project.read(str(qgs_candidates[0]))

    layer = find_layer_by_table_name(project, layer_name)
    if layer is None:
        return result

    renderer = layer.renderer()
    if renderer is None:
        return result
    result["renderer_class"] = type(renderer).__name__

    symbol = None
    get_symbol = getattr(renderer, "symbol", None)
    if callable(get_symbol):
        try:
            symbol = get_symbol()
        except TypeError:
            # QgsFeatureRenderer subclasses that don't genuinely implement `symbol()` (e.g.
            # QgsRuleBasedRenderer) still inherit the base class's own placeholder, which raises
            # rather than returning a usable QgsSymbol -- nothing further to report here, which is
            # correct: AC-QPB-100's own negative control only needs `renderer_class` for this case.
            symbol = None

    if symbol is None:
        return result

    for i in range(symbol.symbolLayerCount()):
        symbol_layer = symbol.symbolLayer(i)
        layer_type = symbol_layer.layerType()
        result["symbol_layer_types"].append(layer_type)

        if layer_type == "SimpleMarker" and result["marker_shape"] is None:
            try:
                result["marker_shape"] = QgsSimpleMarkerSymbolLayerBase.encodeShape(
                    symbol_layer.shape()
                )
            except Exception:  # noqa: BLE001 - best-effort; absence is reported as None.
                pass
        elif layer_type == "SvgMarker" and result["svg_relative_path"] is None:
            try:
                resolved_path = symbol_layer.path()
                result["svg_relative_path"] = os.path.relpath(resolved_path, start=project_dir)
            except Exception:  # noqa: BLE001 - best-effort; absence is reported as None.
                pass
        elif layer_type == "SimpleFill" and result["fill_style"] is None:
            try:
                result["fill_style"] = symbol_layer.properties().get("style")
            except Exception:  # noqa: BLE001 - best-effort; absence is reported as None.
                pass

    return result


def inspect_layer_renderer(project_dir: str, layer_name: str) -> dict:
    """Wraps AC-QPB-100/AC-QPB-101/AC-QPB-104; see HARNESS_CONTRACT.md function 15 for the exact
    contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.field_alias_inspect.inspect_field_aliases`.
    """
    direct = _inspect_layer_renderer_pyqgis(project_dir, layer_name)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.layer_renderer_inspect",
        "_inspect_layer_renderer_pyqgis",
        {"project_dir": project_dir, "layer_name": layer_name},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)
