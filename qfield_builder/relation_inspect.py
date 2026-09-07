"""`inspect_relations()` (HARNESS_CONTRACT.md function 18; FR-QPB-128/Section 8.6/AC-QPB-111;
Decision Log D-73/D-77).

PyQGIS-backed, like :mod:`qfield_builder.field_alias_inspect`/:mod:`qfield_builder.
identification_inspect`: re-opens the generated `.qgs` project and reads back every relation
currently registered on the project's own `QgsProject.relationManager()` -- the same manager
`_add_relations()` (`qfield_builder.qgis_worker`) populates one relation into, per foreign key
(FR-QPB-056), keyed by each relation's own `id()` (`QgsRelation.id()`), together with that same
relation's separate, human-facing display name (`QgsRelation.name()`) -- the property FR-QPB-128
requires be a Section 8.6-confirmed Korean name instead of the raw relation-ID string.
"""
from __future__ import annotations

from pathlib import Path

_EMPTY_RESULT = {
    "relation_ids": [],
    "names": {},
}


def _inspect_relations_pyqgis(project_dir: str) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = {"relation_ids": [], "names": {}}

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject()
    project.read(str(qgs_candidates[0]))

    relations = project.relationManager().relations()
    result["relation_ids"] = list(relations.keys())
    result["names"] = {
        relation_id: relation.name() for relation_id, relation in relations.items()
    }
    return result


def inspect_relations(project_dir: str) -> dict:
    """Wraps AC-QPB-111; see HARNESS_CONTRACT.md function 18 for the exact contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.field_alias_inspect.inspect_field_aliases`.
    """
    direct = _inspect_relations_pyqgis(project_dir)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.relation_inspect",
        "_inspect_relations_pyqgis",
        {"project_dir": project_dir},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)
