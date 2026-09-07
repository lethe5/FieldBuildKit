"""Read back generated layer display expressions through the isolated PyQGIS path."""
from __future__ import annotations

from pathlib import Path

from .layer_lookup import find_layer_by_table_name


def _inspect_display_expressions_pyqgis(project_dir: str) -> dict | None:
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()
    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return {"display_expressions": {}}

    project = QgsProject()
    project.read(str(qgs_candidates[0]))
    expressions: dict[str, str] = {}
    for table_name in ("observation", "survey"):
        layer = find_layer_by_table_name(project, table_name)
        if layer is not None:
            expressions[table_name] = layer.displayExpression()
    return {"display_expressions": expressions}


def inspect_display_expressions(project_dir: str) -> dict:
    direct = _inspect_display_expressions_pyqgis(project_dir)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.display_expression_inspect",
        "_inspect_display_expressions_pyqgis",
        {"project_dir": project_dir},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]
    return {"display_expressions": {}}
