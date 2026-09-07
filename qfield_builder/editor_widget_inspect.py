"""`inspect_editor_widget()` (HARNESS_CONTRACT.md function 16; FR-QPB-122/FR-QPB-124/FR-QPB-125/
AC-QPB-103/AC-QPB-105/AC-QPB-107).

PyQGIS-backed, like :mod:`qfield_builder.field_alias_inspect`/`qfield_builder.identification_
inspect`: re-opens the generated `.qgs` project, locates the named vector layer and field, and
reports the field's currently configured editor widget type/configuration and default-value
definition via QGIS's own `QgsEditorWidgetSetup`/`QgsDefaultValue` APIs.

This implementer round (FR-QPB-122/AC-QPB-103 only) only needs, and only independently confirmed
against a real, locally installed QGIS 3.44.12 (via `scripts/qgis_isolated_probe.py`, per this
project's hard QGIS-isolation rule -- never a hand-rolled `QgsApplication`/QGIS-binary
invocation), the `widget_type`/`value_map` and `default_value_expression`/`apply_on_update`
portions of this function's contract:

- After a `QgsEditorWidgetSetup("ValueMap", {"map": {...}})` round-trips through a real `.qgs`
  project write-then-read cycle, `setup.type()` is still exactly `"ValueMap"` and
  `setup.config()["map"]` is still a plain `dict[str, str]` (not, e.g., a list of single-entry
  dicts) -- confirmed empirically; no defensive re-shaping of `config()["map"]"` is needed.
  Confirmed separately: a field with no editor widget ever explicitly configured for it reports
  `setup.type() == ""` (QGIS's own "fell through to the plain default text-edit widget" signal),
  matching this function's own documented `""` sentinel.
- `layer.defaultValueDefinition(idx).expression()`/`.applyOnUpdate()` round-trip a
  `QgsDefaultValue` correctly; a field with no default value definition set at all reports an
  empty-string expression, which this function reports back as `default_value_expression = None`
  (not the empty string itself) so callers can use a plain truthiness/`is None` check.

`referenced_layer_name`/`has_filter_or_completer_config` (the `ValueRelation`/`RelationReference`
portion of this function's contract) are implemented using this codebase's own already-shipped
`RelationReference` configuration shape (`{"Relation": <relation_id>}`, `qgis_worker.
_configure_relation_reference_widget`) for the `RelationReference` case, and QGIS's `ValueRelation`
configuration keys (`"Layer"`, `"Key"`, `"Value"`, `"FilterExpression"`, `"UseCompleter"`, ...) for
the `ValueRelation` case.

**FR-QPB-124/125 round (this round): the `ValueRelation` branch is now independently confirmed**
against a real, locally installed QGIS 3.44.12 (via `scripts/qgis_isolated_probe.py`, per this
project's hard QGIS-isolation rule -- never a hand-rolled `QgsApplication`/QGIS-binary invocation),
using a real `qfield_builder.qgis_worker._configure_value_relation_widget`-shaped widget
(`{"Layer": <lookup_layer_id>, "Key": "taxon_kor_nm", "Value": "taxon_kor_nm", "AllowMulti": False,
"AllowNull": True, "OrderByValue": True, "UseCompleter": True, "FilterExpression": "",
"NofColumns": 1}`) round-tripped through a real `QgsProject.write()`/`.read()` cycle:
`setup.type()` is exactly `"ValueRelation"`; `setup.config()["Layer"]` round-trips to the same
layer ID string, and `project.mapLayer(<that id>)` correctly resolves back to the referenced
layer's own `.name()`; `config.get("UseCompleter")` round-trips as the Python `bool` `True`. Also
confirmed: `layer.defaultValueDefinition(idx).expression()`/`.applyOnUpdate()` round-trip a
`QgsDefaultValue("attribute(get_feature(...), ...)", True)` expression correctly and evaluate to
the expected looked-up value against a real feature (including gracefully to `NULL`, not an
exception, when the referencing field has no value yet); `layer.editFormConfig().readOnly(idx)`
round-trips a `form_config.setReadOnly(idx, True)` call correctly.

**Layer lookup, and `referenced_layer_name`'s own reported value (Decision Log D-80/D-84 fix):**
`layer_name` is, and every existing caller across this suite already passes, the target layer's
own underlying GeoPackage *table* name -- every layer lookup in this module (the target layer
itself, and the `RelationReference`/`ValueRelation` widget's own *referenced* layer, both below)
uses :func:`qfield_builder.layer_lookup.table_name_from_layer`/`find_layer_by_table_name` rather
than a plain `lyr.name() == layer_name` scan or a raw `referenced_layer.name()` read, so both the
target-layer lookup and the reported `referenced_layer_name` value keep working, and keep meaning
"the referenced layer's own table name" as every existing caller already expects, now that a
domain layer's own `.name()` may be a Section 8.7-confirmed Korean display name instead of its
table name (DR-QPB-078/FR-QPB-130). See `qfield_builder.layer_lookup`'s own module docstring for
the full rationale.

**Blocking-finding fix round (Key/Value swap correction):** an earlier version of
`_configure_value_relation_widget` configured `"Key": ktsn_col, "Value": kor_col` -- backwards,
since QGIS's `ValueRelation` widget writes the **"Key"** column's value into the edited field on
selection (`QgsValueRelationFieldFormatter`'s documented raw-stored-value semantics; see QGIS
issue #30194) while **"Value"** only drives the dropdown/completer's display label. This meant a
real selection would display the Korean name but actually *store* the KTSN code into
`selected_korean_name`, silently breaking `_derived_ktsn_field_expression`'s lookup (which matches
the lookup table's Korean-name column against `selected_korean_name`'s stored value). Corrected so
`"Key"` is the Korean-name column, matching FR-QPB-124's own text ("The value written to
`selected_korean_name` on selection is the plain Korean-name text itself"). Because neither
`referenced_layer_name` nor `has_filter_or_completer_config` can distinguish a Key/Value swap, this
round adds two new, additive-only result keys -- `value_relation_key_column`/
`value_relation_value_column`, populated verbatim from `config.get("Key")`/`config.get("Value")` --
so a caller (in particular, a regression test) can assert which column is actually the *storage*
column, not merely that a `ValueRelation` widget with some Key/Value pair exists.
"""
from __future__ import annotations

from pathlib import Path

from .layer_lookup import find_layer_by_table_name, table_name_from_layer

_EMPTY_RESULT = {
    "widget_type": "",
    "value_map": None,
    "referenced_layer_name": None,
    "has_filter_or_completer_config": None,
    "default_value_expression": None,
    "apply_on_update": None,
    "is_read_only": None,
    # Additive-only fields (this round's Blocking Finding 1 fix): populated only for a
    # ValueRelation widget, exposing exactly which lookup-table column QGIS's own
    # QgsValueRelationFieldFormatter will actually write into the edited field ("Key") versus
    # which column only drives the dropdown/completer's display label ("Value"). Needed because
    # `referenced_layer_name`/`has_filter_or_completer_config` alone cannot distinguish a
    # Key/Value column swap -- see qfield_builder.qgis_worker._configure_value_relation_widget's
    # own docstring and QGIS issue #30194 for why this distinction matters.
    "value_relation_key_column": None,
    "value_relation_value_column": None,
}


def _referenced_layer_name_for_relation_reference(project, config: dict) -> str | None:
    relation_id = config.get("Relation")
    if not relation_id:
        return None
    relation = project.relationManager().relation(relation_id)
    if relation is None or not relation.isValid():
        return None
    referenced_layer = relation.referencedLayer()
    return table_name_from_layer(referenced_layer) if referenced_layer is not None else None


def _referenced_layer_name_for_value_relation(project, config: dict) -> str | None:
    layer_id = config.get("Layer")
    if not layer_id:
        return None
    referenced_layer = project.mapLayer(layer_id)
    return table_name_from_layer(referenced_layer) if referenced_layer is not None else None


def _inspect_editor_widget_pyqgis(
    project_dir: str, layer_name: str, field_name: str
) -> dict | None:
    """Real-QGIS inspection, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject
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

    fields = layer.fields()
    idx = fields.indexOf(field_name)
    if idx < 0:
        return result

    setup = layer.editorWidgetSetup(idx)
    widget_type = setup.type() or ""
    config = setup.config() or {}
    result["widget_type"] = widget_type

    if widget_type == "ValueMap":
        raw_map = config.get("map")
        value_map: dict = {}
        if isinstance(raw_map, dict):
            value_map = dict(raw_map)
        elif isinstance(raw_map, list):
            # Defensive only -- not observed in this round's own real-QGIS round-trip probe
            # (see module docstring), which confirmed a plain dict. Kept in case a different
            # QGIS version ever serializes "map" as a list of single-entry dicts instead.
            for entry in raw_map:
                if isinstance(entry, dict):
                    value_map.update(entry)
        result["value_map"] = value_map

    if widget_type == "RelationReference":
        result["referenced_layer_name"] = _referenced_layer_name_for_relation_reference(
            project, config
        )
    elif widget_type == "ValueRelation":
        result["referenced_layer_name"] = _referenced_layer_name_for_value_relation(
            project, config
        )
        use_completer = bool(config.get("UseCompleter"))
        filter_expression = config.get("FilterExpression") or ""
        result["has_filter_or_completer_config"] = bool(
            use_completer or str(filter_expression).strip()
        )
        result["value_relation_key_column"] = config.get("Key")
        result["value_relation_value_column"] = config.get("Value")

    default_def = layer.defaultValueDefinition(idx)
    expression = default_def.expression() if default_def is not None else ""
    if expression:
        result["default_value_expression"] = expression
        result["apply_on_update"] = bool(default_def.applyOnUpdate())

    result["is_read_only"] = bool(layer.editFormConfig().readOnly(idx))

    return result


def inspect_editor_widget(project_dir: str, layer_name: str, field_name: str) -> dict:
    """Wraps AC-QPB-103 (and, for a later round, AC-QPB-105/AC-QPB-107); see HARNESS_CONTRACT.md
    function 16 for the exact contract.

    Tries a direct, in-process PyQGIS call first; if PyQGIS is not importable in this process,
    dispatches the same call through :mod:`qfield_builder.qgis_bridge`, mirroring
    :func:`qfield_builder.field_alias_inspect.inspect_field_aliases`.
    """
    direct = _inspect_editor_widget_pyqgis(project_dir, layer_name, field_name)
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.editor_widget_inspect",
        "_inspect_editor_widget_pyqgis",
        {"project_dir": project_dir, "layer_name": layer_name, "field_name": field_name},
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    return dict(_EMPTY_RESULT)


_EMPTY_DERIVED_DEFAULT_VALUES_RESULT = {"found": False, "values": {}}


def _evaluate_default_values_after_setting_attribute_pyqgis(
    project_dir: str, layer_name: str, set_field_name: str, set_field_value, read_field_names
) -> dict | None:
    """Test-support function (Blocking Finding 1 fix round): genuinely *evaluates* one or more
    fields' configured `QgsDefaultValue` expression -- rather than only inspecting its static
    text -- against a synthetic feature whose `set_field_name` attribute is `set_field_value`.
    Used to empirically confirm FR-QPB-125's `selected_scientific_name`/`selected_ktsn` derivation
    actually resolves to the correct, non-NULL accepted values once `selected_korean_name` holds
    the value a real `ValueRelation` selection would write.

    **Deliberately opens the project via the global `QgsProject.instance()` singleton, unlike this
    module's other functions above (which use a fresh, non-singleton `QgsProject()`).** Confirmed
    empirically (this round, via `scripts/qgis_isolated_probe.py`, in two independently fresh
    subprocesses) that `_derived_ktsn_field_expression`'s `get_feature('<lookup_layer_id>', ...)`
    expression only resolves the referenced lookup layer when it is registered in the *global*
    project singleton -- a separately-read, non-singleton `QgsProject()` instance, even one that
    successfully loads the same layer under the same layer ID, does not make `get_feature()`
    resolve it. This exactly mirrors how a real, single, long-running QGIS Desktop/QField session
    actually holds "the current project" via `QgsProject.instance()`, so using the singleton here
    is not a test-only workaround of a production limitation -- it is what makes this test
    faithfully reproduce real usage. (This is a distinct, pre-existing characteristic of this
    dispatched-subprocess-per-call test harness/`get_feature()` combination, not part of the
    Key/Value swap defect this round fixes; not applicable to
    :mod:`qfield_builder.feature_save`, which is unrelated to this round's own scope.)

    Returns `{"found": bool, "values": {field_name: resolved_value_or_None, ...}}`. Returns None
    if PyQGIS is not importable here.
    """
    try:
        from qgis.core import QgsFeature, QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    result = dict(_EMPTY_DERIVED_DEFAULT_VALUES_RESULT)
    result["values"] = {name: None for name in read_field_names}

    qgs_candidates = list(Path(project_dir).glob("*.qgs"))
    if not qgs_candidates:
        return result

    project = QgsProject.instance()
    project.read(str(qgs_candidates[0]))

    layer = find_layer_by_table_name(project, layer_name)
    if layer is None:
        return result

    fields = layer.fields()
    if fields.indexOf(set_field_name) < 0:
        return result

    feature = QgsFeature(fields)
    feature.setAttribute(set_field_name, set_field_value)

    values = {}
    for read_field_name in read_field_names:
        idx = fields.indexOf(read_field_name)
        values[read_field_name] = layer.defaultValue(idx, feature) if idx >= 0 else None

    result["found"] = True
    result["values"] = values
    return result


def evaluate_default_values_after_setting_attribute(
    project_dir: str, layer_name: str, set_field_name: str, set_field_value, read_field_names
) -> dict:
    """Public wrapper for `_evaluate_default_values_after_setting_attribute_pyqgis`, mirroring
    `inspect_editor_widget`'s own direct-call/bridge-fallback pattern."""
    direct = _evaluate_default_values_after_setting_attribute_pyqgis(
        project_dir, layer_name, set_field_name, set_field_value, read_field_names
    )
    if direct is not None:
        return direct

    from . import qgis_bridge

    outcome = qgis_bridge.run_job(
        "qfield_builder.editor_widget_inspect",
        "_evaluate_default_values_after_setting_attribute_pyqgis",
        {
            "project_dir": project_dir,
            "layer_name": layer_name,
            "set_field_name": set_field_name,
            "set_field_value": set_field_value,
            "read_field_names": read_field_names,
        },
    )
    if outcome is not None and outcome.get("ok") and outcome.get("result") is not None:
        return outcome["result"]

    result = dict(_EMPTY_DERIVED_DEFAULT_VALUES_RESULT)
    result["values"] = {name: None for name in read_field_names}
    return result
