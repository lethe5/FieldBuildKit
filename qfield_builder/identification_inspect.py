"""`inspect_identification_widget()` (HARNESS_CONTRACT.md function 10; AC-QPB-070).

PyQGIS-backed, like :mod:`qfield_builder.validate`: re-opens the generated `.qgs` project and
inspects the given layer's attribute form for the embedded "Identify attached photos" `QML Widget`
action added by :func:`qfield_builder.qgis_worker._add_identification_widget`.

Empirical finding from this implementation round (see completion report): the real, confirmed
PyQGIS mechanism for a "QML Widget" is `QgsAttributeEditorQmlElement` (`Qgis.AttributeEditorType.
QmlElement`) -- a standalone attribute-editor-form element (like the Html/Text/Spacer/Relation
elements already visible in `qgis.core`), not a per-field `QgsEditorWidgetSetup` type string as
this project's own `HARNESS_CONTRACT.md` speculated it might be (by analogy to
"RelationReference"/"ExternalResource"). Confirmed further: after a `.qgs` project is written and
re-read, `QgsAttributeEditorContainer.findElements(Qgis.AttributeEditorType.QmlElement)` returns
elements typed as the generic base class `QgsAttributeEditorElement` in PyQGIS's Python bindings
(unlike a freshly-constructed, not-yet-round-tripped element, which is already the correctly
downcast `QgsAttributeEditorQmlElement`) -- calling `.qmlCode()` directly on the re-read object
raises `AttributeError`; an explicit `sip.cast(element, QgsAttributeEditorQmlElement)` is required
first. This module accounts for that.

2026-08-24 addendum (Decision Log D-50/D-51; HARNESS_CONTRACT.md function 10): the return contract
now also includes a `qml_code` key -- the exact raw QML/JavaScript source text of the widget's own
`qmlCode()` (`""` when no widget is found), so callers can assert on the *literal content* of the
generated QML (e.g. `test_post_mvp_identification_plugin.py`'s `test_fr109_*` tests), not merely
whether some non-empty source exists at all.

**Layer lookup (Decision Log D-80/D-84 fix):** `layer_name` is, and every existing caller across
this suite already passes, the target layer's own underlying GeoPackage *table* name -- this
function locates the layer via :func:`qfield_builder.layer_lookup.find_layer_by_table_name` rather
than `lyr.name() == layer_name`, so it keeps working unchanged now that a domain layer's own
`.name()` may be a Section 8.7-confirmed Korean display name instead of its table name
(DR-QPB-078/FR-QPB-130). Discovered as a real regression by this same round's own required
full-acceptance-suite verification pass; fixed here for the identical reason and via the identical
mechanism as `qfield_builder.field_alias_inspect`/`qfield_builder.editor_widget_inspect`/
`qfield_builder.layer_renderer_inspect` (see `qfield_builder.layer_lookup`'s own module docstring).
"""
from __future__ import annotations

from pathlib import Path

from .layer_lookup import find_layer_by_table_name

_EMPTY_RESULT = {
    "qml_widget_field_found": False,
    "qml_widget_field_name": None,
    "embedded_in_attribute_form": False,
    "qml_code_present": False,
    "qml_code": "",
}


def _inspect_identification_widget_pyqgis(project_dir: str, layer_name: str) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import Qgis, QgsAttributeEditorQmlElement, QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = dict(_EMPTY_RESULT)

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject()
    project.read(str(qgs_candidates[0]))

    layer = find_layer_by_table_name(project, layer_name)
    if layer is None:
        return result

    root = layer.editFormConfig().invisibleRootContainer()
    found = root.findElements(Qgis.AttributeEditorType.QmlElement)
    if not found:
        return result

    element = found[0]
    try:
        qml_code = element.qmlCode()
    except AttributeError:
        # Empirically confirmed (see module docstring): a round-tripped (write-then-read) .qgs
        # project returns the generic base-class wrapper here; downcast explicitly.
        try:
            import sip
        except ImportError:  # pragma: no cover - PyQt6/other binding fallback
            from PyQt5 import sip
        element = sip.cast(element, QgsAttributeEditorQmlElement)
        qml_code = element.qmlCode()

    result["qml_widget_field_found"] = True
    result["qml_widget_field_name"] = element.name()
    result["embedded_in_attribute_form"] = True
    result["qml_code_present"] = bool(qml_code and qml_code.strip())
    result["qml_code"] = qml_code or ""
    return result


def inspect_identification_widget(project_dir: str, layer_name: str) -> dict:
    """Wraps AC-QPB-070; see HARNESS_CONTRACT.md function 10 for the exact contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.validate._open_with_pyqgis`.
    """
    direct = _inspect_identification_widget_pyqgis(project_dir, layer_name)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.identification_inspect",
        "_inspect_identification_widget_pyqgis",
        {"project_dir": project_dir, "layer_name": layer_name},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)
