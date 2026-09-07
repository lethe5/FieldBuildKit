"""`inspect_field_aliases()` (HARNESS_CONTRACT.md function 12; DR-QPB-071/FR-QPB-119/Section 8.5/
AC-QPB-098; Decision Log D-56/D-57/D-58).

PyQGIS-backed, like :mod:`qfield_builder.identification_inspect`: re-opens the generated `.qgs`
project, locates the named vector layer, and reads back each of its fields' currently configured
alias via QGIS's own field-alias mechanism (`QgsField.alias()` -- deliberately *not*
`QgsVectorLayer.attributeDisplayName()`, which substitutes the field's own name as a display
fallback when no alias is set and would therefore make an intentionally-unset alias, the UUID
primary-key case, indistinguishable from a set-but-coincidentally-identical alias; see
HARNESS_CONTRACT.md function 12 for the full rationale).

**Layer lookup (Decision Log D-80/D-84 fix):** `layer_name` is, and every existing caller across
this suite already passes, the target layer's own underlying GeoPackage *table* name -- this
function locates the layer via :func:`qfield_builder.layer_lookup.find_layer_by_table_name` rather
than `lyr.name() == layer_name`, so it keeps working unchanged now that a domain layer's own
`.name()` may be a Section 8.7-confirmed Korean display name instead of its table name
(DR-QPB-078/FR-QPB-130). See `qfield_builder.layer_lookup`'s own module docstring for the full
rationale.
"""
from __future__ import annotations

from pathlib import Path

from .layer_lookup import find_layer_by_table_name

_EMPTY_RESULT = {
    "field_names": [],
    "aliases": {},
}


def _inspect_field_aliases_pyqgis(project_dir: str, layer_name: str) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = {"field_names": [], "aliases": {}}

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject()
    project.read(str(qgs_candidates[0]))

    layer = find_layer_by_table_name(project, layer_name)
    if layer is None:
        return result

    fields = layer.fields()
    field_names = [f.name() for f in fields]
    aliases = {name: fields.field(name).alias() for name in field_names}

    result["field_names"] = field_names
    result["aliases"] = aliases
    return result


def inspect_field_aliases(project_dir: str, layer_name: str) -> dict:
    """Wraps AC-QPB-098; see HARNESS_CONTRACT.md function 12 for the exact contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.identification_inspect.inspect_identification_widget`.
    """
    direct = _inspect_field_aliases_pyqgis(project_dir, layer_name)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.field_alias_inspect",
        "_inspect_field_aliases_pyqgis",
        {"project_dir": project_dir, "layer_name": layer_name},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)
