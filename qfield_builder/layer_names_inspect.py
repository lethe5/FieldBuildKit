"""`inspect_layer_names()` (HARNESS_CONTRACT.md function 19; DR-QPB-078/FR-QPB-130/Section 8.7/
AC-QPB-118; Decision Log D-80/D-84).

PyQGIS-backed, like :mod:`qfield_builder.field_alias_inspect`/:mod:`qfield_builder.relation_
inspect`: re-opens the generated `.qgs` project and reads back every GeoPackage-table-backed
layer's own currently configured name (`QgsMapLayer.name()`) -- the property
`_add_domain_layers()`/`_add_ktsn_lookup_layer()` (`qfield_builder.qgis_worker`) now set, via
`.setName()`, to the Section 8.7-confirmed Korean display text, in place of the raw GeoPackage
table name QGIS/OGR would otherwise default to.

Identifies each layer by its own underlying GeoPackage table name
(:func:`qfield_builder.layer_lookup.table_name_from_layer`), parsed from the layer's own OGR data
source -- never by the layer's own current `.name()`, which is exactly the property this
requirement changes and is therefore unusable as a stable lookup key (see HARNESS_CONTRACT.md
function 19's own rationale). This naturally excludes any layer that is not backed by a real
GeoPackage-table data source with a `layername=` connection parameter -- in particular, the
online/offline basemap layer (a WMTS/XYZ/raster-tile source, never a GeoPackage vector layer) is
never a member of this function's own output, by construction, without an explicit allowlist.
"""
from __future__ import annotations

from pathlib import Path

from .layer_lookup import table_name_from_layer

_EMPTY_RESULT = {
    "table_names": [],
    "names": {},
}


def _inspect_layer_names_pyqgis(project_dir: str) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = {"table_names": [], "names": {}}

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject()
    project.read(str(qgs_candidates[0]))

    names: dict[str, str] = {}
    for lyr in project.mapLayers().values():
        table_name = table_name_from_layer(lyr)
        if table_name is None:
            continue
        names[table_name] = lyr.name()

    result["table_names"] = list(names.keys())
    result["names"] = names
    return result


def inspect_layer_names(project_dir: str) -> dict:
    """Wraps AC-QPB-118; see HARNESS_CONTRACT.md function 19 for the exact contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.field_alias_inspect.inspect_field_aliases`.
    """
    direct = _inspect_layer_names_pyqgis(project_dir)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.layer_names_inspect",
        "_inspect_layer_names_pyqgis",
        {"project_dir": project_dir},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)
