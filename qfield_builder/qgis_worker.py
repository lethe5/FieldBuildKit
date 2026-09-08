"""Standalone-compatible entry points and the development-only PyQGIS template exporter.

Public build/reprojection functions route to template_project and standalone_gis.
The retained private PyQGIS implementation is used only to refresh templates and
compare compatibility, through scripts/qgis_isolated_probe.py.
"""

from __future__ import annotations

from pathlib import Path

from . import (
    korean_field_aliases,
    korean_layer_display_names,
    korean_relation_display_names,
    probability_raster,
    qml_plugin,
    reference_bundle,
    schemas,
)
from .vworld import (
    ATTRIBUTION_TEXT_EN,
    ATTRIBUTION_TEXT_KO,
    build_gettile_url,
    supported_layers,
)

# Section 13.1 (post-MVP guaranteed-manual baseline): the layer(s), per survey type, that host the
# embedded "Identify attached photos" QML Widget. Type 4 candidates are display-only: users select
# dominant/subdominant species through the two ValueRelation fields, never through write-back.
IDENTIFICATION_TARGET_LAYERS = ("inventory_observation", "observation", "community")

# DR-QPB-072/FR-QPB-124-127 (Decision Log D-66/D-67/D-68): the Korean-name `ValueRelation`
# selection field, and the two fields fully derived from it. Present on exactly the same layers as
# IDENTIFICATION_TARGET_LAYERS above (Types 1-3's `inventory_observation`/`observation`) -- Type
# 4's `community` layer has no `selected_korean_name`/`selected_scientific_name`/`selected_ktsn`
# columns at all (schemas.py), so this feature is naturally scoped away from it (DR-QPB-050,
# O-29) without any extra per-layer check needed here.
KTSN_KOREAN_NAME_FIELD = "selected_korean_name"
KTSN_SCIENTIFIC_NAME_FIELD = "selected_scientific_name"
KTSN_KTSN_FIELD = "selected_ktsn"


def _overlapping_site_id_default_expression() -> str:
    """Return the direct-draw default for a geometry that overlaps a site polygon."""
    site_layer_name = korean_layer_display_names.display_name_for("site").replace("'", "''")
    return (
        "array_first(\n"
        "  overlay_intersects(\n"
        f"    layer := '{site_layer_name}',\n"
        '    expression := "site_id",\n'
        "    limit := 1\n"
        "  )\n"
        ")"
    )


def _community_name_default_expression() -> str:
    """Derive a Type 4 community name from its dominant-species fields."""
    return (
        "CASE "
        "WHEN coalesce(trim(\"dominant_species\"), '') = '' THEN NULL "
        "WHEN coalesce(trim(\"subdominant_species\"), '') = '' THEN \"dominant_species\" "
        "ELSE \"dominant_species\" || '-' || \"subdominant_species\" END"
    )

# Stable relation IDs and Drag & Drop Designer tab layout are derived directly from
# qfield_builder.schemas.TableDef/ForeignKeyDef so the .qgs generator and the GeoPackage builder
# never drift apart (FR-QPB-056: "stable relation IDs").


def _import_pyqgis():
    from qgis.core import (  # noqa: F401
        Qgis,
        QgsAttributeEditorContainer,
        QgsAttributeEditorField,
        QgsAttributeEditorQmlElement,
        QgsAttributeEditorRelation,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsDefaultValue,
        QgsEditFormConfig,
        QgsEditorWidgetSetup,
        QgsFeatureRenderer,
        QgsFieldConstraints,
        QgsLayerTreeGroup,
        QgsLayerTreeLayer,
        QgsMapLayer,
        QgsProject,
        QgsRasterLayer,
        QgsRelation,
        QgsRuleBasedRenderer,
        QgsSimpleFillSymbolLayer,
        QgsSimpleMarkerSymbolLayer,
        QgsSingleSymbolRenderer,
        QgsSnappingConfig,
        QgsSvgMarkerSymbolLayer,
        QgsSymbol,
        QgsVectorFileWriter,
        QgsVectorLayer,
    )

    return {
        "Qgis": Qgis,
        "QgsAttributeEditorContainer": QgsAttributeEditorContainer,
        "QgsAttributeEditorField": QgsAttributeEditorField,
        "QgsAttributeEditorQmlElement": QgsAttributeEditorQmlElement,
        "QgsAttributeEditorRelation": QgsAttributeEditorRelation,
        "QgsCoordinateReferenceSystem": QgsCoordinateReferenceSystem,
        "QgsCoordinateTransform": QgsCoordinateTransform,
        "QgsDefaultValue": QgsDefaultValue,
        "QgsEditFormConfig": QgsEditFormConfig,
        "QgsEditorWidgetSetup": QgsEditorWidgetSetup,
        "QgsFeatureRenderer": QgsFeatureRenderer,
        "QgsFieldConstraints": QgsFieldConstraints,
        "QgsLayerTreeGroup": QgsLayerTreeGroup,
        "QgsLayerTreeLayer": QgsLayerTreeLayer,
        "QgsMapLayer": QgsMapLayer,
        "QgsProject": QgsProject,
        "QgsRasterLayer": QgsRasterLayer,
        "QgsRelation": QgsRelation,
        "QgsRuleBasedRenderer": QgsRuleBasedRenderer,
        "QgsSimpleFillSymbolLayer": QgsSimpleFillSymbolLayer,
        "QgsSimpleMarkerSymbolLayer": QgsSimpleMarkerSymbolLayer,
        "QgsSingleSymbolRenderer": QgsSingleSymbolRenderer,
        "QgsSnappingConfig": QgsSnappingConfig,
        "QgsSvgMarkerSymbolLayer": QgsSvgMarkerSymbolLayer,
        "QgsSymbol": QgsSymbol,
        "QgsVectorLayer": QgsVectorLayer,
        "QgsVectorFileWriter": QgsVectorFileWriter,
    }


# Regex fragments for the save-time attachment-path shape constraint (see
# `_attachment_path_shape_constraint_expression` below). Backslash counts here are deliberately
# empirical, not a typo: each pattern is embedded inside a *QGIS expression* single-quoted string
# literal (one level of backslash-unescaping) whose *value* is then compiled as a PCRE regex
# pattern by `regexp_match` (a second level) — confirmed against a real QGIS 3.44 install that
# this exact number of backslashes is what is needed for `regexp_match` to actually see a
# literal backslash in the compiled pattern, e.g. to match a Windows drive-letter path spelled
# with `\` rather than `/`, or a UNC path's leading `\\`.
_ATTACHMENT_PATH_POSIX_ABSOLUTE_RE = r"^/"
_ATTACHMENT_PATH_WINDOWS_DRIVE_RE = r"^[A-Za-z]:[\\\\/]"
_ATTACHMENT_PATH_UNC_RE = r"^\\\\"
_ATTACHMENT_PATH_URI_SCHEME_RE = r"^[A-Za-z][A-Za-z0-9+.-]*://"


def _attachment_path_shape_constraint_expression(field_name: str) -> str:
    """A QGIS field-constraint expression rejecting the save-time-enforced malformed attachment
    path shapes (empty/whitespace-only, POSIX/Windows-drive-letter/UNC absolute, `file://` URI),
    per HARNESS_CONTRACT.md — while explicitly allowing NULL (no attachment) and `..`-traversal
    (validate_project-only; see that section's rationale) through."""
    field_ref = field_name
    return (
        f"{field_ref} IS NULL OR ("
        f"length(trim({field_ref})) > 0"
        f" AND NOT regexp_match({field_ref}, '{_ATTACHMENT_PATH_POSIX_ABSOLUTE_RE}')"
        f" AND NOT regexp_match({field_ref}, '{_ATTACHMENT_PATH_WINDOWS_DRIVE_RE}')"
        f" AND NOT regexp_match({field_ref}, '{_ATTACHMENT_PATH_UNC_RE}')"
        f" AND NOT regexp_match({field_ref}, '{_ATTACHMENT_PATH_URI_SCHEME_RE}')"
        ")"
    )


def _configure_value_relation_widget(pyqgis: dict, layer, idx: int, ktsn_lookup_layer) -> None:
    """Configure a Korean-name field with the bundled accepted-name ValueRelation widget.

    **Disclosed technical-feasibility caveat (FR-QPB-124's own text, mirroring FR-QPB-111/
    Decision Log D-36):** confirmed, via this round's own real-QGIS-3.44.12 round-trip probe
    (`QgsEditorWidgetSetup("ValueRelation", {...})`), that the widget's own recognized
    configuration keys are exactly `Layer`/`Key`/`Value`/`AllowMulti`/`AllowNull`/
    `OrderByValue`/`UseCompleter`/`FilterExpression`/`NofColumns` -- none of which cap the
    *number of simultaneously displayed matches* at a specific count (e.g. exactly five). No
    "max results shown" configuration key was found anywhere in this widget's documented config
    surface. `UseCompleter=True` (the closest supported mechanism) is configured instead, giving
    a live, as-you-type filter over the full accepted-name list -- narrower than "capped at
    five," but the closest behavior QGIS's own `ValueRelation` widget configuration actually
    supports, exactly as FR-QPB-124's own text anticipates this caveat may resolve.
    """
    QgsEditorWidgetSetup = pyqgis["QgsEditorWidgetSetup"]
    _ktsn_col, kor_col, _sci_col = reference_bundle.ACCEPTED_NAME_LOOKUP_TABLE_COLUMNS
    layer.setEditorWidgetSetup(
        idx,
        QgsEditorWidgetSetup(
            "ValueRelation",
            {
                "Layer": ktsn_lookup_layer.id(),
                # "Key" is the column whose *value* QGIS actually writes into
                # `selected_korean_name` on selection (QgsValueRelationFieldFormatter's raw
                # stored value, confirmed by QGIS issue #30194's own title: "data is saved as
                # Key Column values instead of Value Column values"). FR-QPB-124 requires the
                # plain Korean-name *text* to be written, so "Key" must be the Korean-name
                # column, not the KTSN code column -- otherwise `_derived_ktsn_field_expression`
                # below, which matches this lookup table's `taxon_kor_nm` against the current
                # feature's `selected_korean_name` value, could never find a match.
                "Key": kor_col,
                # "Value" only controls the display label shown in the dropdown/completer; using
                # the same Korean-name column here keeps the displayed text identical to what is
                # actually stored.
                "Value": kor_col,
                "AllowMulti": False,
                "AllowNull": True,
                "OrderByValue": True,
                "UseCompleter": True,
                "FilterExpression": "",
                "NofColumns": 1,
            },
        ),
    )


def _derived_ktsn_field_expression(ktsn_lookup_layer, value_column: str) -> str:
    """FR-QPB-125 (Decision Log D-67): a `QgsDefaultValue` expression looking up, in the bundled
    accepted-name lookup table, the row whose `taxon_kor_nm` matches `selected_korean_name`'s
    current value, and returning that row's `value_column` (`taxon_full_nm` for
    `selected_scientific_name`, `ktsn` for `selected_ktsn`). Confirmed (this round's own real-QGIS
    probe) to evaluate correctly, including gracefully to NULL (no crash) when
    `selected_korean_name` has no value yet."""
    _ktsn_col, kor_col, _sci_col = reference_bundle.ACCEPTED_NAME_LOOKUP_TABLE_COLUMNS
    lookup_layer_id = ktsn_lookup_layer.id()
    return (
        f"attribute(get_feature('{lookup_layer_id}', '{kor_col}', "
        f"\"{KTSN_KOREAN_NAME_FIELD}\"), '{value_column}')"
    )


def _configure_derived_ktsn_field(
    pyqgis: dict, layer, idx: int, value_column: str, ktsn_lookup_layer
) -> None:
    """FR-QPB-125 (Decision Log D-67): configures `selected_scientific_name`/`selected_ktsn` as
    fully derived, read-only fields -- a `QgsDefaultValue` expression with `applyOnUpdate=True`
    (QField's "apply default upon update," confirmed by this round's own real-QGIS probe to
    re-evaluate identically for a brand-new feature and for an existing, already-saved feature
    reopened later), plus the field's own edit-form read-only flag."""
    QgsDefaultValue = pyqgis["QgsDefaultValue"]
    expression = _derived_ktsn_field_expression(ktsn_lookup_layer, value_column)
    layer.setDefaultValueDefinition(idx, QgsDefaultValue(expression, True))
    form_config = layer.editFormConfig()
    form_config.setReadOnly(idx, True)
    layer.setEditFormConfig(form_config)


def _configure_widget_for_column(
    pyqgis: dict,
    layer,
    col: schemas.ColumnDef,
    table: schemas.TableDef,
    ktsn_lookup_layer=None,
):
    QgsEditorWidgetSetup = pyqgis["QgsEditorWidgetSetup"]
    QgsDefaultValue = pyqgis["QgsDefaultValue"]
    QgsFieldConstraints = pyqgis["QgsFieldConstraints"]

    fields = layer.fields()
    idx = fields.indexOf(col.name)
    if idx < 0:
        return

    if col.name == "qpb_plot_geometry_wkt":
        # QField evaluates current_parent_value() against the immediate embedded form.  Capture
        # the plot's own geometry there, then copy it once into the immediate survey parent.
        # This operational field stays in the existing form model but is never user input.
        expression = (
            "geom_to_wkt($geometry)"
            if table.name == "plot"
            else "current_parent_value('qpb_plot_geometry_wkt')"
        )
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))
        layer.setDefaultValueDefinition(idx, QgsDefaultValue(expression, table.name == "plot"))
        alias = korean_field_aliases.alias_for(table.name, col.name)
        if alias:
            layer.setFieldAlias(idx, alias)
        form_config = layer.editFormConfig()
        form_config.setReadOnly(idx, True)
        layer.setEditFormConfig(form_config)
        return

    if col.is_uuid_pk:
        # A primary key is immutable.  Applying this default on update regenerated the parent's
        # UUID while editing and orphaned daughter rows.  UuidGenerator keeps the field available
        # to QField relation forms without changing the previously working form UI.
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))
        layer.setDefaultValueDefinition(idx, QgsDefaultValue("uuid('WithoutBraces')", False))
        form_config = layer.editFormConfig()
        form_config.setReadOnly(idx, True)
        layer.setEditFormConfig(form_config)
        return

    # FR-QPB-119/Section 8.5 (Decision Log D-56/D-57/D-58): every other visible field -- including
    # UUID foreign-key fields shown as RelationReference pickers -- gets a Korean display alias.
    alias = korean_field_aliases.alias_for(table.name, col.name)
    if alias:
        layer.setFieldAlias(idx, alias)

    if col.name in ("observed_at", "survey_date", "captured_at"):
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("DateTime", {}))
        if col.default_sql:
            layer.setDefaultValueDefinition(idx, QgsDefaultValue("now()", True))
    elif col.default_sql:
        # Any other column with a GeoPackage-level `DEFAULT` (e.g. `identification_status`'s
        # `'not_requested'`, `is_field_checked`'s `0`) also needs an equivalent QGIS-expression
        # default value definition set explicitly. Without this, `QgsVectorLayerUtils.
        # createFeature`/the real attribute form leave the field NULL for a caller-omitted value,
        # which then fails this same column's own NOT NULL/check-expression hard constraint
        # (FR-QPB-057) instead of quietly picking up its intended default — the GeoPackage-level
        # SQL default alone is not something QGIS's own field-constraint validation consults.
        # `default_sql` values here (a quoted string literal, or a bare `0`/`1`) already happen to
        # be valid QGIS expression syntax as-is, unlike the `date('now')`/`datetime('now')` SQL
        # function calls handled above via `now()`.
        layer.setDefaultValueDefinition(idx, QgsDefaultValue(col.default_sql, False))

    # A directly drawn Type 2 survey or Type 3 plot belongs to the first intersecting site.
    # Type 4 community records have no site_id column (they remain linked via survey_id).
    if col.name == "site_id" and table.name in {"survey", "plot"} and table.geometry is not None:
        layer.setDefaultValueDefinition(
            idx, QgsDefaultValue(_overlapping_site_id_default_expression(), False)
        )

    if table.name == "community" and col.name == "community_name":
        layer.setDefaultValueDefinition(
            idx, QgsDefaultValue(_community_name_default_expression(), True)
        )

    if col.name == "cover":
        layer.setEditorWidgetSetup(
            idx, QgsEditorWidgetSetup("Range", {"Min": 0, "Max": 100, "Step": 1})
        )

    if col.name == "is_field_checked":
        layer.setEditorWidgetSetup(
            idx, QgsEditorWidgetSetup("CheckBox", {"CheckedState": "1", "UncheckedState": "0"})
        )

    if col.name == "organ":
        value_map = {v: v for v in ("leaf", "flower", "fruit", "bark", "auto")}
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueMap", {"map": value_map}))

    if col.name == "identification_status":
        # FR-QPB-122 (Decision Log D-63, confirmed by D-69): constrain the field to its existing
        # five-value enum via a native ValueMap editor widget, replacing the plain default
        # text-edit widget it previously fell through to. Displayed option text keeps the raw
        # English enum strings as both keys and values -- no Korean-language value-label
        # translation (Decision Log D-69) -- mirroring the `organ` ValueMap widget's own
        # identical-keys/values precedent immediately above. This is a presentation/entry-
        # constraint change only: it does not alter the column's SQL type, `CHECK` constraint
        # (`_identification_status_col`, `qfield_builder/schemas.py`), or default value, both of
        # which are (re)applied elsewhere in this same function using the unrelated `col`
        # attributes (`col.default_sql`, `col.check_sql`), unaffected by this widget setup.
        value_map = {v: v for v in schemas._IDENTIFICATION_STATUS_VALUES}
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueMap", {"map": value_map}))

    # DR-QPB-072/FR-QPB-124/FR-QPB-125 (Decision Log D-66/D-67/D-68): the Korean-name
    # `ValueRelation` selection widget and its two fully derived, read-only fields. Only
    # configured when a bundled accepted-name lookup table layer was actually loaded for this
    # project (`ktsn_lookup_layer` is `None` for Type 4, which has no matching columns anyway --
    # see `KTSN_KOREAN_NAME_FIELD` and friends' own module-level comment).
    if ktsn_lookup_layer is not None:
        if col.name == KTSN_KOREAN_NAME_FIELD:
            _configure_value_relation_widget(pyqgis, layer, idx, ktsn_lookup_layer)
        elif col.name == KTSN_SCIENTIFIC_NAME_FIELD:
            _configure_derived_ktsn_field(pyqgis, layer, idx, "taxon_full_nm", ktsn_lookup_layer)
        elif col.name == KTSN_KTSN_FIELD:
            _configure_derived_ktsn_field(pyqgis, layer, idx, "ktsn", ktsn_lookup_layer)
        elif table.name == "community" and col.name in {"dominant_species", "subdominant_species"}:
            _configure_value_relation_widget(pyqgis, layer, idx, ktsn_lookup_layer)

    if col.is_attachment_path:
        layer.setEditorWidgetSetup(
            idx,
            QgsEditorWidgetSetup(
                "ExternalResource",
                {"RelativeStorage": 1, "DocumentViewer": 1, "FileWidget": True},
            ),
        )
        # HARNESS_CONTRACT.md ("Save-time vs. validate_project-only enforcement for
        # invalid_attachment_path"): a static, per-feature QGIS field-constraint expression must
        # reject an empty/whitespace-only value, a POSIX absolute path, a Windows drive-letter
        # absolute path, a UNC path, or a `file://` URI at save time (DR-QPB-012, FR-QPB-057).
        # `..`-traversal is deliberately excluded here (validate_project-only; requires resolving
        # against the project's own on-disk location, which this static per-feature expression
        # does not have). This is a QGIS-expression-only constraint (`QgsFieldConstraints.
        # ConstraintExpression`, evaluated by QGIS's own expression engine at the form/API layer)
        # — deliberately not folded into `col.check_sql` (a literal SQLite `CHECK` clause baked
        # into the GeoPackage itself, evaluated by SQLite/QField's own storage engine on every
        # insert, which has no `regexp_match` function available and would break every insert).
        layer.setConstraintExpression(
            idx,
            _attachment_path_shape_constraint_expression(col.name),
            description="must be a well-formed relative attachment path",
        )
        layer.setFieldConstraint(
            idx,
            QgsFieldConstraints.ConstraintExpression,
            QgsFieldConstraints.ConstraintStrengthHard,
        )

    if col.name == "notes":
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("TextEdit", {"IsMultiline": True}))

    # FR-QPB-057: enforce mandatory attributes with hard constraints, not only UI labels.
    if col.not_null:
        layer.setFieldConstraint(
            idx, QgsFieldConstraints.ConstraintNotNull, QgsFieldConstraints.ConstraintStrengthHard
        )
    if col.check_sql:
        layer.setConstraintExpression(idx, col.check_sql, description=col.comment or col.name)
        layer.setFieldConstraint(
            idx,
            QgsFieldConstraints.ConstraintExpression,
            QgsFieldConstraints.ConstraintStrengthHard,
        )


def _configure_relation_reference_widget(pyqgis: dict, layer, fk_field: str, relation_id: str):
    QgsEditorWidgetSetup = pyqgis["QgsEditorWidgetSetup"]
    fields = layer.fields()
    idx = fields.indexOf(fk_field)
    if idx < 0:
        return
    layer.setEditorWidgetSetup(
        idx,
        QgsEditorWidgetSetup(
            "RelationReference",
            {"Relation": relation_id, "ShowForm": True, "AllowNULL": False, "OrderByValue": True},
        ),
    )


def _build_drag_and_drop_form(
    pyqgis: dict, layer, table: schemas.TableDef, child_relations: list[str]
):
    """FR-QPB-057: Drag and Drop Designer form, organized into tabs, with child relations."""
    QgsAttributeEditorContainer = pyqgis["QgsAttributeEditorContainer"]
    QgsAttributeEditorField = pyqgis["QgsAttributeEditorField"]
    QgsAttributeEditorRelation = pyqgis["QgsAttributeEditorRelation"]
    QgsEditFormConfig = pyqgis["QgsEditFormConfig"]

    form_config = layer.editFormConfig()
    form_config.setLayout(QgsEditFormConfig.TabLayout)
    fields = layer.fields()

    # `layer.editFormConfig().invisibleRootContainer()` is not an empty container to begin with:
    # QGIS pre-populates it, by its own default, with a flat, ungrouped `QgsAttributeEditorField`
    # for every field on the layer (including the physical `fid` primary key) before this function
    # ever runs. Without clearing that default content first, the organized "Details"/"Related
    # records" containers built below would merely be *added alongside* that pre-existing flat
    # field list rather than replacing it -- producing every intentionally organized field twice
    # (once flat/ungrouped at the root, once inside "Details") and leaving `fid` as a plain,
    # visible, ungrouped field, which directly violates FR-QPB-057's "hide `fid`... from normal
    # entry" clause (confirmed empirically against a real QGIS 3.44 install/generated `.qgs` XML).
    # `fid` is never a member of `table.columns` (see `qfield_builder.schemas`), so once the root
    # container is cleared and rebuilt from only the intentionally organized containers below,
    # `fid` achieves genuine field-tree absence -- it is not merely hidden by editor-widget type,
    # it is not present in the attribute-editor-form tree at all.
    invisible_root = form_config.invisibleRootContainer()
    invisible_root.clear()

    root = QgsAttributeEditorContainer("Details", invisible_root)
    for col in table.columns:
        idx = fields.indexOf(col.name)
        if idx >= 0:
            root.addChildElement(QgsAttributeEditorField(col.name, idx, root))

    # Bug fix (stakeholder report): "Details" must be added to `invisible_root` before "Related
    # records" so it is the first tab, not the second -- the workflow is "fill in Details first,
    # then add daughter/child records". `QgsAttributeEditorContainer`'s own tab ordering (for a
    # `TabLayout`-configured form) is simply the order its children were added to their parent via
    # `addChildElement` -- confirmed empirically (see the implementer's completion report for this
    # round) against a real generated `.qgs` project's `<attributeEditorForm>` XML, where each
    # child tab element is serialized in `invisibleRootContainer().children()` order.
    invisible_root.addChildElement(root)

    project = pyqgis["QgsProject"].instance()
    if child_relations:
        related_container = QgsAttributeEditorContainer("Related records", invisible_root)
        for relation_id in child_relations:
            relation = project.relationManager().relation(relation_id)
            if relation is not None and relation.isValid():
                related_container.addChildElement(
                    QgsAttributeEditorRelation(relation, related_container)
                )
        invisible_root.addChildElement(related_container)

    layer.setEditFormConfig(form_config)


from .form_expressions import (  # noqa: E402
    _authoritative_location_expression,
    _identification_photo_paths_expression,
)


def _add_identification_widget(
    pyqgis: dict,
    layer,
    table: schemas.TableDef,
    survey_type: str,
    project_crs: str = "EPSG:4326",
    canonical_reference_enabled: bool = False,
    canonical_layer_id: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
    candidate_selection_enabled: bool = True,
):
    """FR-QPB-101 (revised; Decision Log D-31): embeds the guaranteed-baseline "Identify attached
    photos" action as a `QgsAttributeEditorQmlElement` directly inside the layer's own attribute
    form -- confirmed (see this module's own probe during implementation) to be a standalone
    attribute-editor-form element (`Qgis.AttributeEditorType.QmlElement`), not a per-field editor
    widget setup string, unlike "RelationReference"/"ExternalResource". It is added as a child of
    the same "Details" container `_build_drag_and_drop_form` already built, so it appears alongside
    the record's ordinary fields rather than requiring a second top-level container.
    """
    QgsAttributeEditorQmlElement = pyqgis["QgsAttributeEditorQmlElement"]

    form_config = layer.editFormConfig()
    invisible_root = form_config.invisibleRootContainer()

    details_container = None
    for child in invisible_root.children():
        if child.name() == "Details":
            details_container = child
            break
    target_container = details_container if details_container is not None else invisible_root

    qml_code = qml_plugin.render_identification_widget_qml(
        _identification_photo_paths_expression(table),
        # The approved product change applies to every photo-identification widget in Type 1/2/3:
        # the user already initiated the attempt by pressing the action, so no application-owned
        # consent/OK popup is inserted between the button and the existing identification flow.
        # Type 4 uses the same request flow only to display candidates; it never writes a
        # candidate back because the user chooses a dominant/subdominant field explicitly.
        immediate_identification=True,
        # D-92: carry the generated layer's stable QField display name in the pending request so
        # the project plugin can verify both layer and UUID before touching an active model.
        layer_context=korean_layer_display_names.display_name_for(table.name),
        location_expression=_authoritative_location_expression(
            survey_type, table.name, project_crs
        ),
        canonical_reference_enabled=canonical_reference_enabled,
        canonical_layer_id=canonical_layer_id,
        canonical_runtime_lookup_resource=canonical_runtime_lookup_resource,
        candidate_selection_enabled=candidate_selection_enabled,
    )
    element = QgsAttributeEditorQmlElement(qml_plugin.QML_WIDGET_ELEMENT_NAME, target_container)
    element.setQmlCode(qml_code)
    target_container.addChildElement(element)

    # Real QgsVectorLayer always exposes this setter. Keep the helper tolerant of the minimal
    # layer doubles used by the renderer contract tests, while preserving the real-project path.
    set_edit_form_config = getattr(layer, "setEditFormConfig", None)
    if callable(set_edit_form_config):
        set_edit_form_config(form_config)


def _apply_display_expression(layer, table: schemas.TableDef):
    if table.display_expression:
        layer.setDisplayExpression(table.display_expression)


def _apply_community_symbology(pyqgis: dict, layer):
    """DR-QPB-051: rule-based renderer, is_field_checked true -> green hatch, else red hatch."""
    QgsRuleBasedRenderer = pyqgis["QgsRuleBasedRenderer"]
    QgsSymbol = pyqgis["QgsSymbol"]

    def _hatch_symbol(color_name: str):
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(_qcolor(color_name))
        layer_props = {"color": color_name, "lineangle": "45"}
        try:
            from qgis.core import QgsSimpleFillSymbolLayer

            fill = QgsSimpleFillSymbolLayer.create(layer_props)
            symbol.changeSymbolLayer(0, fill)
        except Exception:  # noqa: BLE001 - best-effort styling; presence of the rule matters most
            pass
        return symbol

    root_rule = QgsRuleBasedRenderer.Rule(None)
    true_rule = QgsRuleBasedRenderer.Rule(_hatch_symbol("green"), 0, 0, "is_field_checked = true")
    false_rule = QgsRuleBasedRenderer.Rule(_hatch_symbol("red"), 0, 0, "ELSE")
    root_rule.appendChild(true_rule)
    root_rule.appendChild(false_rule)
    renderer = QgsRuleBasedRenderer(root_rule)
    layer.setRenderer(renderer)


def _qcolor(name: str):
    from qgis.PyQt.QtGui import QColor

    return QColor(name)


# FR-QPB-120 (Decision Log D-61/D-65): "a single flat fill color plus a thin, contrasting
# outline" for polygons; "a small, solid circle marker" for points. Neither the specification nor
# AC-QPB-100 (HARNESS_CONTRACT.md function 15's own rationale) mandates a specific color -- only
# the structural shape (one SimpleFill/SimpleMarker symbol layer; a circle marker shape) is
# tested -- so these are a reasonable, muted, low-saturation default, easily changed later if a
# stakeholder-specific palette is ever requested.
_MINIMALIST_POINT_FILL_COLOR = "49,130,189,255"  # muted blue
_MINIMALIST_POINT_OUTLINE_COLOR = "20,20,20,255"
_MINIMALIST_POINT_SIZE = "3"
_MINIMALIST_POLYGON_FILL_COLOR = "222,235,247,180"  # pale blue, semi-transparent
_MINIMALIST_POLYGON_OUTLINE_COLOR = "60,60,60,255"

#: FR-QPB-121/AC-QPB-101: a fixed, reasonable display size (millimetres, QGIS's own symbol-size
#: unit default) for a fetched Tabler SVG used as a point-marker symbol -- not specified by the
#: requirement text, which only requires that the SVG actually be used as the marker.
_SVG_MARKER_SIZE = 6.0

# D-MGC-016: QGIS expresses transparency as layer opacity, so the requested 30% transparency
# is persisted as 70% opacity.  Keep this value scoped to the separately rendered site layer in
# Types 2 and 3; other polygon layers and all point layers retain their existing styles.
_SITE_LAYER_OPACITY = 0.70
_COMMUNITY_LAYER_OPACITY = 0.70
_COMMUNITY_SNAP_TOLERANCE_PIXELS = 20.0


def _apply_minimalist_point_symbology(pyqgis: dict, layer) -> None:
    """FR-QPB-120: a small, solid circle marker -- exactly one `SimpleMarker` symbol layer."""
    QgsSymbol = pyqgis["QgsSymbol"]
    QgsSimpleMarkerSymbolLayer = pyqgis["QgsSimpleMarkerSymbolLayer"]
    QgsSingleSymbolRenderer = pyqgis["QgsSingleSymbolRenderer"]

    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    marker = QgsSimpleMarkerSymbolLayer.create(
        {
            "name": "circle",
            "color": _MINIMALIST_POINT_FILL_COLOR,
            "outline_color": _MINIMALIST_POINT_OUTLINE_COLOR,
            "outline_width": "0.4",
            "size": _MINIMALIST_POINT_SIZE,
        }
    )
    symbol.changeSymbolLayer(0, marker)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def _apply_minimalist_polygon_symbology(pyqgis: dict, layer) -> None:
    """FR-QPB-120: a single flat fill color plus a thin, contrasting outline -- exactly one
    `SimpleFill` symbol layer, no gradient/pattern."""
    QgsSymbol = pyqgis["QgsSymbol"]
    QgsSimpleFillSymbolLayer = pyqgis["QgsSimpleFillSymbolLayer"]
    QgsSingleSymbolRenderer = pyqgis["QgsSingleSymbolRenderer"]

    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    fill = QgsSimpleFillSymbolLayer.create(
        {
            "color": _MINIMALIST_POLYGON_FILL_COLOR,
            "outline_color": _MINIMALIST_POLYGON_OUTLINE_COLOR,
            "outline_width": "0.3",
            "style": "solid",
            "outline_style": "solid",
        }
    )
    symbol.changeSymbolLayer(0, fill)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def _apply_site_outline_symbology(pyqgis: dict, layer, survey_type: str) -> None:
    """Show Type 2–4 site boundaries without a polygon fill."""
    if survey_type not in {"temporary_plots", "permanent_plots", "vegetation_mapping"}:
        return
    QgsSymbol = pyqgis["QgsSymbol"]
    QgsSimpleFillSymbolLayer = pyqgis["QgsSimpleFillSymbolLayer"]
    QgsSingleSymbolRenderer = pyqgis["QgsSingleSymbolRenderer"]

    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    outline = QgsSimpleFillSymbolLayer.create(
        {
            "style": "no",
            "outline_color": _MINIMALIST_POLYGON_OUTLINE_COLOR,
            "outline_width": "0.5",
            "outline_style": "solid",
        }
    )
    symbol.changeSymbolLayer(0, outline)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def _apply_site_layer_opacity(layer, survey_type: str) -> None:
    """Apply the Type 2/3 site transparency to the QGIS layer itself.

    ``QgsMapLayer.setOpacity`` is serialized into ``<layerOpacity>`` by QGIS, which keeps the
    style intact after reopening or moving the generated project.  The guard is deliberately
    based on survey type rather than table presence so Type 4's site layer remains unchanged.
    """
    if survey_type not in {"temporary_plots", "permanent_plots"}:
        return
    setter = getattr(layer, "setOpacity", None)
    if not callable(setter):
        raise RuntimeError(
            "QGIS site layer does not expose setOpacity; cannot persist 30% transparency."
        )
    setter(_SITE_LAYER_OPACITY)


def _configure_community_digitizing(project, pyqgis: dict, layers: dict, survey_type: str) -> None:
    """Enable vertex snapping and prevent overlaps while digitizing Type 4 communities."""
    if survey_type != "vegetation_mapping":
        return
    community = layers.get("community")
    site = layers.get("site")
    if community is None or site is None:
        return
    Qgis = pyqgis["Qgis"]
    QgsSnappingConfig = pyqgis["QgsSnappingConfig"]

    snapping = project.snappingConfig()
    snapping.setEnabled(True)
    snapping.setMode(Qgis.SnappingMode.AdvancedConfiguration)
    vertex_snap = QgsSnappingConfig.IndividualLayerSettings(
        True,
        Qgis.SnappingType.Vertex,
        _COMMUNITY_SNAP_TOLERANCE_PIXELS,
        Qgis.MapToolUnit.Pixels,
    )
    snapping.setIndividualLayerSettings(community, vertex_snap)
    snapping.setIndividualLayerSettings(site, vertex_snap)
    project.setSnappingConfig(snapping)
    project.setAvoidIntersectionsMode(Qgis.AvoidIntersectionsMode.AvoidIntersectionsLayers)
    project.setAvoidIntersectionsLayers([community])

    setter = getattr(community, "setOpacity", None)
    if not callable(setter):
        raise RuntimeError("QGIS community layer does not expose setOpacity.")
    setter(_COMMUNITY_LAYER_OPACITY)


def _layer_is_editable_geometry(layer, table_def: schemas.TableDef) -> bool:
    """Return whether a generated domain layer belongs to the editable geometry subset.

    Domain layers are created as editable project layers by ``_add_domain_layers``.  A provider
    or future schema may nevertheless mark one read-only; honor that flag when the binding
    exposes it.  ``isEditable()`` is intentionally not used because it reports whether an edit
    session is currently active, not whether the project layer is configured for editing.
    """
    if table_def.geometry is None:
        return False
    for method_name in ("readOnly", "isReadOnly"):
        method = getattr(layer, method_name, None)
        if callable(method):
            try:
                return not bool(method())
            except Exception:  # noqa: BLE001 - missing provider state should not reorder a layer.
                break
    return True


def _move_site_layer_last_among_editable_geometry_layers(
    project, layers: dict, schema: dict[str, schemas.TableDef], survey_type: str
) -> None:
    """Move Type 2–4 ``site`` to the end of the editable-geometry subset.

    The layer tree node is moved, rather than rebuilding it, so its forms, visibility, and group
    membership remain intact.  Non-editable/non-spatial nodes retain their relative order; the
    site is inserted immediately after the last eligible geometry node.
    """
    if survey_type not in {"temporary_plots", "permanent_plots", "vegetation_mapping"}:
        return
    site = layers.get("site")
    site_def = schema.get("site")
    if site is None or site_def is None or not _layer_is_editable_geometry(site, site_def):
        return

    site_node = project.layerTreeRoot().findLayer(site.id())
    if site_node is None or site_node.parent() is None:
        raise RuntimeError("Generated site layer is missing from the Survey data layer tree.")
    parent = site_node.parent()
    children = list(parent.children())
    eligible_nodes = []
    layer_by_id = {layer.id(): (table_name, layer) for table_name, layer in layers.items()}
    for node in children:
        entry = layer_by_id.get(node.layerId())
        if entry is None:
            continue
        table_name, layer = entry
        if _layer_is_editable_geometry(layer, schema[table_name]):
            eligible_nodes.append(node)
    if site_node not in eligible_nodes:
        return

    target_index = max(children.index(node) for node in eligible_nodes)
    current_index = children.index(site_node)
    if current_index == target_index:
        return

    # Do not remove the only node first. In some QGIS executions (observed in a generated
    # direct-draw project), removing that final tree node also drops the layer from the project's
    # map-layer registry before it can be reattached. That leaves a valid `site` table in the
    # GeoPackage but no `조사지` layer in the saved .qgs. Keep one live node at every point:
    # clone it at its destination, then remove only the original node.
    clone_node = getattr(site_node, "clone", None)
    insert_child_node = getattr(parent, "insertChildNode", None)
    remove_child_node = getattr(parent, "removeChildNode", None)
    if not all(callable(method) for method in (clone_node, insert_child_node, remove_child_node)):
        raise RuntimeError("QGIS layer tree cannot safely reorder the generated site layer.")
    replacement_node = clone_node()
    if replacement_node is None:
        raise RuntimeError("QGIS layer tree failed to clone the generated site layer.")
    # Insert after the last eligible geometry node while the original site node is still present.
    # Since site currently occurs at or before that target, this is its final slot after removal.
    insert_child_node(target_index + 1, replacement_node)
    remove_child_node(site_node)


def _apply_svg_point_symbology(pyqgis: dict, layer, svg_relative_path: str) -> None:
    """FR-QPB-121/AC-QPB-101: replaces the minimalist default point marker with the fetched
    Tabler icon's SVG, referenced by a path relative to the project's own folder (never an
    absolute path -- FR-QPB-091/DR-QPB-012/FR-QPB-121). Empirically confirmed (this round's
    implementer completion report has the probe script/output) that QGIS's own `SvgMarker` symbol
    layer both writes and re-reads this exact relative-path string correctly across a real
    `QgsProject.write()`/`QgsProject.read()` round-trip, and continues to resolve correctly even
    after the whole project folder is moved to a new location -- QGIS resolves it relative to the
    project's own current directory each time, not a path baked in at generation time.
    """
    QgsSymbol = pyqgis["QgsSymbol"]
    QgsSvgMarkerSymbolLayer = pyqgis["QgsSvgMarkerSymbolLayer"]
    QgsSingleSymbolRenderer = pyqgis["QgsSingleSymbolRenderer"]

    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    svg_layer = QgsSvgMarkerSymbolLayer(svg_relative_path)
    svg_layer.setSize(_SVG_MARKER_SIZE)
    symbol.changeSymbolLayer(0, svg_layer)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def _apply_symbol_styling(
    pyqgis: dict,
    schema: dict[str, schemas.TableDef],
    layers: dict,
    svg_relative_path: str | None,
) -> None:
    """FR-QPB-120/FR-QPB-121 (Decision Log D-61/D-65): minimalist default point/polygon symbology
    for every generated project, applied uniformly across every point layer and, separately,
    every polygon layer of the project (per-survey-type scope, never per-individual-layer --
    AC-QPB-104) -- except the Type 4 `community` layer, which keeps DR-QPB-051's own existing
    rule-based renderer (applied separately, by `_apply_community_symbology`, before this
    function runs), completely unaffected by this feature.

    `svg_relative_path`, when given (a successfully fetched and embedded Tabler icon, FR-QPB-121/
    AC-QPB-101), replaces the minimalist default point-marker symbol for **every** point layer of
    this project; when `None` (no Tabler icon selected, or a failed/offline fetch -- FR-QPB-121's
    "generation is not blocked" fallback), every point layer receives the minimalist default
    marker instead.
    """
    for table_name, table_def in schema.items():
        if table_name == "community":
            continue  # DR-QPB-051's own rule-based renderer, unaffected by this feature.
        geometry = table_def.geometry
        if geometry is None:
            continue  # A non-spatial table has no renderer/symbol to configure.
        layer = layers[table_name]
        if geometry.geom_type == "POINT":
            if svg_relative_path:
                _apply_svg_point_symbology(pyqgis, layer, svg_relative_path)
            else:
                _apply_minimalist_point_symbology(pyqgis, layer)
        else:
            # DR-QPB-008: the only other geometry type in this schema is MULTIPOLYGON.
            _apply_minimalist_polygon_symbology(pyqgis, layer)


def _visibility_is_checked(value) -> bool:
    """Return whether *value* is the genuine checked state exposed by QGIS/Qt.

    Visibility verification must not coerce strings, integers, or arbitrary truthy objects.  QGIS
    bindings generally return ``bool`` but older bindings can expose the Qt checked enum.
    """
    if type(value) is bool:
        return value is True

    try:
        from qgis.PyQt.QtCore import Qt
    except ImportError:
        return False

    checked = getattr(Qt, "Checked", None)
    if checked is None:
        check_state = getattr(Qt, "CheckState", None)
        checked = getattr(check_state, "Checked", None) if check_state is not None else None
    return checked is not None and type(value) is type(checked) and value == checked


def _set_layer_tree_node_visible(node, visible: bool = True) -> None:
    """Set and verify a generated layer-tree node's checked/visible state.

    D-91 is a generation invariant, so silently accepting a node without the QGIS setter (or
    without a way to read the resulting state back) would make a project that may open hidden.
    Treat both cases as a build error.  Real ``QgsLayerTreeNode`` instances expose both methods;
    the strict behavior also makes incomplete test doubles fail loudly instead of hiding a
    regression in the project assembly path.
    """
    setter = getattr(node, "setItemVisibilityChecked", None)
    verifier = getattr(node, "itemVisibilityChecked", None)
    if not callable(setter):
        raise RuntimeError(
            "Generated layer-tree node does not expose setItemVisibilityChecked; "
            "cannot guarantee default visibility."
        )
    if not callable(verifier):
        raise RuntimeError(
            "Generated layer-tree node does not expose itemVisibilityChecked; "
            "cannot verify default visibility."
        )
    try:
        setter(bool(visible))
        checked = verifier()
    except Exception as exc:  # noqa: BLE001 - a visibility failure must fail closed.
        raise RuntimeError(f"Unable to verify generated layer-tree visibility: {exc}") from exc
    if _visibility_is_checked(checked) != bool(visible):
        raise RuntimeError(
            "Generated layer-tree node visibility did not match the requested state."
        )


def _set_all_layer_tree_nodes_visible(project) -> None:
    """Re-assert visibility for every generated group and layer immediately before saving."""

    def visit(parent) -> None:
        for child in parent.children():
            layer_getter = getattr(child, "layer", None)
            layer = layer_getter() if callable(layer_getter) else None
            is_probability = bool(
                layer is not None
                and layer.customProperty("fieldbuildkit/probability_raster", False)
            )
            _set_layer_tree_node_visible(child, visible=not is_probability)
            visit(child)

    visit(project.layerTreeRoot())


def _add_domain_layers(pyqgis: dict, project, gpkg_path: str, schema: dict[str, schemas.TableDef]):
    """FR-QPB-054: load every required layer (including non-spatial relation tables) into the
    project, grouped under "Survey data" (FR-QPB-055); return {table_name: QgsVectorLayer}.

    DR-QPB-078/FR-QPB-130 (Section 8.7; Decision Log D-80/D-84): every loaded layer's own display
    name (`QgsMapLayer.setName()`) is then set to its Section 8.7-confirmed Korean text -- in
    place of the raw GeoPackage table name QGIS/QField otherwise shows by default -- distinct from,
    and unrelated to, the layer's own underlying data-source table name (`layer_name` on the
    `QgsVectorLayer` constructor, and every `layers` dict key below), which is completely
    unaffected and continues to be used verbatim wherever this codebase looks a layer up by its
    table identity.
    """
    QgsVectorLayer = pyqgis["QgsVectorLayer"]
    QgsLayerTreeGroup = pyqgis["QgsLayerTreeGroup"]

    survey_group: QgsLayerTreeGroup = project.layerTreeRoot().addGroup("Survey data")
    _set_layer_tree_node_visible(survey_group)
    layers: dict[str, object] = {}
    for table_name in schema:
        uri = f"{gpkg_path}|layername={table_name}"
        layer = QgsVectorLayer(uri, table_name, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Failed to load layer {table_name!r} from {gpkg_path!r}")
        layer.setName(korean_layer_display_names.display_name_for(table_name))
        project.addMapLayer(layer, False)
        layer_node = survey_group.addLayer(layer)
        _set_layer_tree_node_visible(layer_node)
        layers[table_name] = layer
    return layers


def _add_relations(pyqgis: dict, project, schema: dict[str, schemas.TableDef], layers: dict):
    """FR-QPB-056: one relation per FK, stable IDs, composition strength for owned children.

    FR-QPB-128/Section 8.6 (Decision Log D-73/D-77): the relation's own stable ID
    (`QgsRelation.setId()`) is completely unaffected by this requirement and remains the raw
    `fk.relation_id` string (depended on by `relation_aggregate()` expressions elsewhere and by
    this function's own returned `relation_ids_by_parent`/`relation_ids_by_child` maps). Only the
    relation's separate, human-facing display name (`QgsRelation.setName()`) is set to the
    Section 8.6-confirmed Korean text instead of that same raw ID string.
    """
    QgsRelation = pyqgis["QgsRelation"]

    relation_ids_by_child: dict[str, list[str]] = {}
    relation_ids_by_parent: dict[str, list[str]] = {}
    for table_name, table_def in schema.items():
        fk = table_def.foreign_key
        if fk is None:
            continue
        relation = QgsRelation()
        relation.setId(fk.relation_id)
        relation.setName(korean_relation_display_names.display_name_for(fk.relation_id))
        relation.setReferencingLayer(layers[table_name].id())
        relation.setReferencedLayer(layers[fk.ref_table].id())
        relation.addFieldPair(fk.column, fk.ref_column)
        if fk.composition:
            relation.setStrength(relation.RelationStrength.Composition)
        if relation.isValid():
            project.relationManager().addRelation(relation)
        relation_ids_by_child.setdefault(table_name, []).append(fk.relation_id)
        relation_ids_by_parent.setdefault(fk.ref_table, []).append(fk.relation_id)
    return relation_ids_by_parent


def _configure_forms_and_widgets(
    pyqgis: dict,
    schema: dict[str, schemas.TableDef],
    layers: dict,
    relations_by_parent: dict,
    identification_enabled: bool = False,
    ktsn_lookup_layer=None,
    survey_type: str | None = None,
    project_crs: str = "EPSG:4326",
    canonical_reference_enabled: bool = False,
    canonical_layer_id: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
):
    for table_name, table_def in schema.items():
        layer = layers[table_name]
        for col in table_def.columns:
            _configure_widget_for_column(
                pyqgis, layer, col, table_def, ktsn_lookup_layer=ktsn_lookup_layer
            )
        if table_def.foreign_key is not None:
            _configure_relation_reference_widget(
                pyqgis, layer, table_def.foreign_key.column, table_def.foreign_key.relation_id
            )
        _apply_display_expression(layer, table_def)
        child_relations = relations_by_parent.get(table_name, [])
        _build_drag_and_drop_form(pyqgis, layer, table_def, child_relations)
        if identification_enabled and table_name in IDENTIFICATION_TARGET_LAYERS:
            _add_identification_widget(
                pyqgis, layer, table_def, survey_type or "", project_crs,
                canonical_reference_enabled=canonical_reference_enabled,
                canonical_layer_id=canonical_layer_id,
                canonical_runtime_lookup_resource=canonical_runtime_lookup_resource,
                candidate_selection_enabled=table_name != "community",
            )
        layer.updateFields()


def _configure_transactions(pyqgis: dict, project, layers: dict):
    """Keep related GeoPackage edits in one deferred-FK transaction."""
    Qgis = pyqgis["Qgis"]
    # Persist the Project Properties → Data Sources option, not only a transient provider
    # property.  QField then evaluates a new parent's UUID default as the form opens, before a
    # related daughter form needs to copy the foreign key.
    try:
        project.setFlag(Qgis.ProjectFlag.EvaluateDefaultValuesOnProviderSide, True)
    except (AttributeError, TypeError):
        pass
    try:
        project.setTransactionMode(Qgis.TransactionMode.AutomaticGroups)
    except (AttributeError, TypeError):
        try:
            project.setAutoTransaction(True)
        except AttributeError:
            pass
    for layer in layers.values():
        # FR-QPB-060: evaluate provider-side/default values (e.g. the UUID default expression)
        # so generated UUIDs also work correctly when a feature is created in QField.
        try:
            layer.dataProvider().setProviderProperty(
                layer.dataProvider().EvaluateDefaultValues, True
            )
        except AttributeError:
            pass


def _add_reference_group(project):
    """FR-QPB-055 (revised; Decision Log D-71): only "Reference" is created here, early -- it
    must exist before the KTSN accepted-name lookup layer (if any) is loaded into it as its first
    layer, below. "Basemap" is deliberately NOT created here -- see
    `_add_basemap_group_after_survey_and_reference` below for why it must be added later."""
    reference_group = project.layerTreeRoot().addGroup("Reference")
    _set_layer_tree_node_visible(reference_group)


def _add_basemap_group_after_survey_and_reference(project):
    """FR-QPB-055 (revised; Decision Log D-71/AC-QPB-110): `Basemap` must end up last (highest
    children-index) of the three required root layer-tree groups, so it renders beneath both
    `Survey data` and `Reference` -- `QgsLayerTreeGroup.addGroup()` appends to the end of the
    parent's existing children, so simply calling this only after both `Survey data`
    (`_add_domain_layers`) and `Reference` (`_add_reference_group`) already exist is sufficient to
    guarantee that order; no explicit re-ordering of existing nodes is needed."""
    basemap_group = project.layerTreeRoot().addGroup("Basemap")
    _set_layer_tree_node_visible(basemap_group)


def _add_ktsn_lookup_layer(pyqgis: dict, project, gpkg_path: str, table_name: str):
    """DR-QPB-072 (Decision Log D-66): loads the bundled accepted-name lookup table (already
    created inside `gpkg_path` by :func:`qfield_builder.gpkg.add_ktsn_lookup_table`) as the first
    layer to actually populate the "Reference" layer-tree group (FR-QPB-055) -- which must already
    exist (:func:`_add_reference_group`) by the time this runs.

    Configured non-identifiable and read-only, per FR-QPB-059's existing "Reference/extent layers
    must be non-identifiable and read-only where appropriate" convention -- confirmed (this
    round's own real-QGIS-3.44.12 round-trip probe) that `QgsVectorLayer.setReadOnly(True)` and
    clearing the `Identifiable` bit from `QgsMapLayer.setFlags(...)` both round-trip correctly
    through a real `QgsProject.write()`/`.read()` cycle.

    DR-QPB-078/FR-QPB-130's own scope extension (Decision Log D-84) sets this layer's own display
    name (`QgsMapLayer.setName()`) to Section 8.7's confirmed "인정 국명 조회표" -- in place of the
    raw GeoPackage table name -- distinct from, and unrelated to, `table_name` itself, which is
    completely unaffected and continues to be used verbatim wherever this codebase looks this
    layer up by its table identity.
    """
    QgsVectorLayer = pyqgis["QgsVectorLayer"]
    QgsMapLayer = pyqgis["QgsMapLayer"]

    uri = f"{gpkg_path}|layername={table_name}"
    layer = QgsVectorLayer(uri, table_name, "ogr")
    if not layer.isValid():
        raise RuntimeError(
            f"Failed to load KTSN accepted-name lookup table layer {table_name!r} from "
            f"{gpkg_path!r}"
        )
    layer.setName(korean_layer_display_names.KTSN_LOOKUP_LAYER_DISPLAY_NAME)
    project.addMapLayer(layer, False)
    reference_group = project.layerTreeRoot().findGroup("Reference")
    if reference_group is not None:
        layer_node = reference_group.addLayer(layer)
        _set_layer_tree_node_visible(layer_node)

    layer.setReadOnly(True)
    layer.setFlags(QgsMapLayer.LayerFlags(QgsMapLayer.Removable | QgsMapLayer.Searchable))
    layer.setDisplayExpression("taxon_kor_nm")
    return layer


def _add_ktsn_taxonomy_reference_layer(pyqgis: dict, project, gpkg_path: str, table_name: str):
    """Load the D-95 canonical taxonomy attributes table before its compatibility projection."""
    QgsVectorLayer = pyqgis["QgsVectorLayer"]
    QgsMapLayer = pyqgis["QgsMapLayer"]
    # Keep the provider table name in the URI, but give QGIS a neutral construction name so its
    # generated layer ID cannot accidentally become a table-name-derived lookup target. The saved
    # project still exposes the Korean display name below, and the ID passed to the widget remains
    # the actual QgsMapLayer.id().
    layer = QgsVectorLayer(f"{gpkg_path}|layername={table_name}", "qpb_canonical_taxonomy", "ogr")
    if not layer.isValid():
        raise RuntimeError(f"식물 분류 참조표를 GeoPackage에서 열 수 없습니다: {gpkg_path!r}")
    layer.setName(korean_layer_display_names.KTSN_TAXONOMY_LAYER_DISPLAY_NAME)
    aliases = {
        "ktsn": "KTSN", "source_no": "원본 No", "taxon_status": "정/이명",
        "korean_name": "국명", "scientific_name": "원문 학명",
        "scientific_name_without_authority": "학명(명명자 제거)", "authority": "명명자",
        "naming_year": "명명년도", "phylum_scientific_name": "문",
        "phylum_korean_name": "문 국명", "class_scientific_name": "강",
        "class_korean_name": "강 국명", "order_scientific_name": "목",
        "order_korean_name": "목 국명", "family_scientific_name": "과",
        "family_korean_name": "과 국명", "genus_scientific_name": "속",
        "genus_korean_name": "속 국명", "accepted_ktsn": "인정 KTSN",
        "source_url": "원본 URL", "content_available": "콘텐츠 여부", "source_row": "원본 행",
    }
    for field in layer.fields():
        alias = aliases.get(field.name())
        if alias:
            field.setAlias(alias)
    project.addMapLayer(layer, False)
    reference_group = project.layerTreeRoot().findGroup("Reference")
    if reference_group is not None:
        node = reference_group.addLayer(layer)
        _set_layer_tree_node_visible(node)
    layer.setReadOnly(True)
    layer.setFlags(QgsMapLayer.LayerFlags(QgsMapLayer.Removable | QgsMapLayer.Searchable))
    layer.setDisplayExpression("korean_name")
    return layer


def _add_probability_raster_layer(pyqgis: dict, project, qgs_path: str, relative_path: str):
    """Register the one project-local multiband probability raster in ``Reference``."""
    QgsMapLayer = pyqgis["QgsMapLayer"]
    QgsRasterLayer = pyqgis["QgsRasterLayer"]

    absolute_path = Path(qgs_path).parent / relative_path
    layer = QgsRasterLayer(str(absolute_path), probability_raster.LAYER_NAME, "gdal")
    if not layer.isValid():
        raise RuntimeError(f"다중밴드 확률 래스터를 열 수 없습니다: {relative_path}")
    layer.setName(probability_raster.LAYER_NAME)
    layer.setCustomProperty("fieldbuildkit/probability_raster", True)
    layer.setFlags(QgsMapLayer.LayerFlags(QgsMapLayer.Removable | QgsMapLayer.Searchable))
    project.addMapLayer(layer, False)
    reference_group = project.layerTreeRoot().findGroup("Reference")
    if reference_group is None:
        raise RuntimeError("Reference 레이어 그룹을 찾을 수 없습니다.")
    node = reference_group.addLayer(layer)
    # The raster is a lookup source for raster_value(), not a display layer. Keep it registered
    # and addressable by QGIS expressions, but save its layer-tree checkbox unchecked.
    _set_layer_tree_node_visible(node, visible=False)
    return layer


def _add_online_basemap_layer(pyqgis: dict, project, basemap_config: dict) -> bool:
    """FR-QPB-035/070-079: online VWorld layer; returns True iff the API key was embedded.

    VWorld's WMTS capabilities connection is not reliably consumed by QField for Base, White,
    Midnight and Hybrid (Satellite is a misleading exception).  Use the documented concrete
    GetTile template as a QGIS ``type=xyz`` source instead.  This bypasses mobile WMTS
    negotiation, reuses the URL form already used for offline MBTiles, and keeps both generation
    and project opening free of a second capabilities request.

    `known_vworld_layers`, if supplied by the wizard's explicit refresh, remains the validation
    set.  The offline MBTiles pipeline is unchanged.
    """
    QgsRasterLayer = pyqgis["QgsRasterLayer"]

    consent_accepted = bool(basemap_config.get("consent_accepted"))
    api_key = basemap_config.get("vworld_api_key", "")
    layer_name = basemap_config.get("layer", "Base")

    if not consent_accepted:
        # FR-QPB-077: no consent -> no key embedded, no immediately-usable online layer.
        return False

    known_layers = basemap_config.get("known_vworld_layers")
    allowed_layers = known_layers if known_layers is not None else supported_layers()
    if layer_name not in allowed_layers:
        raise ValueError(f"Unsupported VWorld layer: {layer_name!r}")

    tile_url = build_gettile_url(api_key, layer_name, known_layers=known_layers)
    uri = f"type=xyz&url={tile_url}&zmin={6 if layer_name == 'Satellite' else 0}&zmax=19"
    raster_layer = QgsRasterLayer(uri, f"VWorld {layer_name} (online)", "wms")
    project.addMapLayer(raster_layer, False)
    basemap_group = project.layerTreeRoot().findGroup("Basemap")
    if basemap_group is not None:
        layer_node = basemap_group.addLayer(raster_layer)
        _set_layer_tree_node_visible(layer_node)
    raster_layer.setAbstract(ATTRIBUTION_TEXT_EN)
    _set_layer_attribution(raster_layer)
    return True


def _set_plantnet_project_variable(project, plantnet_config: dict | None) -> bool:
    """FR-QPB-114 (Decision Log D-45): mirrors `_add_online_basemap_layer`'s VWorld consent gate,
    but for the Pl@ntNet key -- sets the `qpb_plantnet_api_key` QGIS project variable (the exact
    name the embedded `QML Widget` identification action reads at runtime via
    `expression.evaluate("@qpb_plantnet_api_key")`) iff consent was accepted; returns whether the
    key was embedded. Never writes the key anywhere else -- no GeoPackage/`.qml`/manifest-content/
    log/temp-filename access happens here at all.
    """
    if not plantnet_config or not plantnet_config.get("consent_accepted"):
        # FR-QPB-116: no consent -> no key embedded anywhere.
        return False

    from qgis.core import QgsExpressionContextUtils

    api_key = plantnet_config.get("api_key", "")
    QgsExpressionContextUtils.setProjectVariable(project, "qpb_plantnet_api_key", api_key)
    return True


def _set_vworld_project_variable(project, basemap_config: dict | None) -> bool:
    """Persist the consented VWorld value in the saved QGIS project variable.

    The report plugin reads this variable at export time.  Keeping the value in the existing
    project-configuration boundary avoids baking it into the QML sidecar or GeoPackage; the
    report only exposes the derived background mode and uses the value for the tile request.
    """
    if not basemap_config or not basemap_config.get("consent_accepted"):
        return False
    api_key = str(basemap_config.get("vworld_api_key") or "").strip()
    if not api_key:
        return False
    from qgis.core import QgsExpressionContextUtils

    QgsExpressionContextUtils.setProjectVariable(project, "qpb_vworld_api_key", api_key)
    return True


def _add_offline_basemap_layer(
    pyqgis: dict,
    project,
    mbtiles_relative_path: str,
    offline_source_identity: dict | None = None,
):
    QgsRasterLayer = pyqgis["QgsRasterLayer"]
    QgsCoordinateReferenceSystem = pyqgis["QgsCoordinateReferenceSystem"]
    # The build orchestrator resolves and validates this identity before reaching the worker.
    # Never manufacture ``VWorld / Base`` here: direct/low-level callers must either pass the
    # resolved identity or fail closed, otherwise a missing selection can be falsely recorded as
    # a Base download in the generated project's metadata.
    if not isinstance(offline_source_identity, dict):
        raise ValueError(
            "Offline basemap source identity is required; no explicit VWorld layer was resolved."
        )
    provider_name = str(offline_source_identity.get("provider") or "").strip()
    layer_name = str(offline_source_identity.get("layer") or "").strip()
    if not provider_name or not layer_name:
        raise ValueError(
            "Offline basemap source identity is incomplete; no explicit VWorld layer was resolved."
        )
    # Keep the stable layer title used by existing projects; the selected source identity is
    # carried in the abstract and custom properties below so it is visible without changing the
    # layer's user-facing role name.
    raster_layer = QgsRasterLayer(mbtiles_relative_path, "Offline basemap (MBTiles)", "gdal")
    raster_layer.setName("Offline basemap (MBTiles)")
    # Bug fix (stakeholder report): MBTiles is a fixed-CRS tile format -- every `.mbtiles` file is
    # always EPSG:3857 (Web Mercator) per the format's own spec, regardless of what (if anything)
    # GDAL's own MBTiles driver reports back for this layer's CRS. Set it explicitly rather than
    # rely on driver auto-detection, so the generated `.qgs` project's offline basemap layer always
    # has a valid, correct CRS instead of an empty/undefined one.
    raster_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    project.addMapLayer(raster_layer, False)
    basemap_group = project.layerTreeRoot().findGroup("Basemap")
    if basemap_group is not None:
        layer_node = basemap_group.addLayer(raster_layer)
        _set_layer_tree_node_visible(layer_node)
    raster_layer.setAbstract(f"{ATTRIBUTION_TEXT_EN} Source: {provider_name} / {layer_name}.")
    raster_layer.setCustomProperty("fieldbuildkit/provider", provider_name)
    raster_layer.setCustomProperty("fieldbuildkit/layer", layer_name)
    _set_layer_attribution(raster_layer)


def _set_layer_attribution(layer):
    try:
        metadata = layer.metadata()
        metadata.setAbstract(ATTRIBUTION_TEXT_EN)
        layer.setMetadata(metadata)
    except Exception:  # noqa: BLE001 - attribution is also guaranteed via MANIFEST.json/README
        pass


def _set_project_attribution(project):
    metadata = project.metadata()
    abstract = (metadata.abstract() + "\n" if metadata.abstract() else "") + (
        f"{ATTRIBUTION_TEXT_EN}\n{ATTRIBUTION_TEXT_KO}"
    )
    metadata.setAbstract(abstract)
    project.setMetadata(metadata)


def reproject_uploaded_gpkg_layer(
    source_path: str,
    source_layer_name: str,
    destination_path: str,
    target_crs: str,
) -> dict:
    from .standalone_gis import reproject_uploaded_gpkg_layer as reproject

    return reproject(source_path, source_layer_name, destination_path, target_crs)


def reproject_uploaded_shapefile(
    source_path: str,
    destination_path: str,
    target_crs: str,
    source_crs: str | None = None,
) -> dict:
    from .standalone_gis import reproject_uploaded_shapefile as reproject

    return reproject(source_path, destination_path, target_crs, source_crs)


def _reproject_uploaded_gpkg_layer_pyqgis(
    source_path: str,
    source_layer_name: str,
    destination_path: str,
    target_crs: str,
) -> dict:
    """PyQGIS implementation for :func:`reproject_uploaded_gpkg_layer`."""
    pyqgis = _import_pyqgis()
    QgsCoordinateReferenceSystem = pyqgis["QgsCoordinateReferenceSystem"]
    QgsCoordinateTransform = pyqgis["QgsCoordinateTransform"]
    QgsProject = pyqgis["QgsProject"]
    QgsVectorFileWriter = pyqgis["QgsVectorFileWriter"]
    QgsVectorLayer = pyqgis["QgsVectorLayer"]

    source = QgsVectorLayer(
        f"{source_path}|layername={source_layer_name}", source_layer_name, "ogr"
    )
    if not source.isValid():
        raise RuntimeError(f"업로드 GeoPackage 레이어를 열 수 없습니다: {source_layer_name!r}")

    destination_crs = QgsCoordinateReferenceSystem(target_crs)
    if not destination_crs.isValid():
        raise RuntimeError(f"유효하지 않은 저장 좌표계입니다: {target_crs!r}")

    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "reprojected_upload"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    options.ct = QgsCoordinateTransform(
        source.crs(), destination_crs, QgsProject.instance().transformContext()
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        source,
        str(destination),
        QgsProject.instance().transformContext(),
        options,
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"업로드 GeoPackage 레이어 변환 실패: {result[1] or result[0]}")
    return {"path": str(destination), "layer_name": options.layerName}


def _reproject_uploaded_shapefile_pyqgis(
    source_path: str,
    destination_path: str,
    target_crs: str,
    source_crs: str | None = None,
) -> dict:
    """PyQGIS implementation for :func:`reproject_uploaded_shapefile`."""
    pyqgis = _import_pyqgis()
    QgsCoordinateReferenceSystem = pyqgis["QgsCoordinateReferenceSystem"]
    QgsCoordinateTransform = pyqgis["QgsCoordinateTransform"]
    QgsProject = pyqgis["QgsProject"]
    QgsVectorFileWriter = pyqgis["QgsVectorFileWriter"]
    QgsVectorLayer = pyqgis["QgsVectorLayer"]

    source = QgsVectorLayer(str(source_path), Path(source_path).stem, "ogr")
    if not source.isValid():
        raise RuntimeError(f"업로드 SHP를 열 수 없습니다: {source_path!r}")

    if source_crs:
        detected_source_crs = QgsCoordinateReferenceSystem(source_crs)
        if not detected_source_crs.isValid():
            raise RuntimeError(f"유효하지 않은 SHP 원본 좌표계입니다: {source_crs!r}")
        source.setCrs(detected_source_crs)
    elif not source.crs().isValid():
        raise RuntimeError(
            "SHP에 .prj 파일이 없어 원본 좌표계를 확인할 수 없습니다. EPSG 코드를 입력해 주세요."
        )

    destination_crs = QgsCoordinateReferenceSystem(target_crs)
    if not destination_crs.isValid():
        raise RuntimeError(f"유효하지 않은 저장 좌표계입니다: {target_crs!r}")

    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "reprojected_upload"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    options.ct = QgsCoordinateTransform(
        source.crs(), destination_crs, QgsProject.instance().transformContext()
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        source,
        str(destination),
        QgsProject.instance().transformContext(),
        options,
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"업로드 SHP 변환 실패: {result[1] or result[0]}")
    return {"path": str(destination), "layer_name": options.layerName}


def build_qgis_project(
    gpkg_path: str,
    qgs_path: str,
    survey_type: str,
    project_crs: str,
    basemap_config: dict | None,
    mbtiles_relative_path: str | None = None,
    identification_enabled: bool = False,
    plantnet_config: dict | None = None,
    svg_relative_path: str | None = None,
    ktsn_lookup_table_name: str | None = None,
    ktsn_taxonomy_table_name: str | None = None,
    offline_source_identity: dict | None = None,
    probability_raster_relative_path: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
) -> dict:
    kwargs = locals()
    from .template_project import build_qgis_project as build_template

    return build_template(**kwargs)


def _build_qgis_project_pyqgis(
    gpkg_path: str,
    qgs_path: str,
    survey_type: str,
    project_crs: str,
    basemap_config: dict | None,
    mbtiles_relative_path: str | None = None,
    identification_enabled: bool = False,
    plantnet_config: dict | None = None,
    svg_relative_path: str | None = None,
    ktsn_lookup_table_name: str | None = None,
    ktsn_taxonomy_table_name: str | None = None,
    offline_source_identity: dict | None = None,
    probability_raster_relative_path: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
) -> dict:
    """The actual PyQGIS-calling implementation. Only ever runs where PyQGIS is importable —
    either directly in-process, or inside the bridge subprocess dispatched by
    :func:`build_qgis_project` above. Raises `ImportError` if PyQGIS is not importable here.

    Deliberately does *not* call :func:`qfield_builder.qgis_bridge.ensure_qgis_application`:
    unlike the read-path deadlock this application's `validate`/`feature_save` modules work
    around (see their own call sites of that function), `QgsProject.instance()` here is already
    usable for building/writing a project without an explicit `QgsApplication`; constructing one
    only at this point (after `qgis.core` submodules have already been used without one) has been
    observed to leave `QgsProject`'s global singleton state inconsistent enough to crash on the
    very next call.
    """
    pyqgis = _import_pyqgis()

    QgsCoordinateReferenceSystem = pyqgis["QgsCoordinateReferenceSystem"]
    QgsProject = pyqgis["QgsProject"]

    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem(project_crs))
    # FR-QPB-052: layer/basemap data sources must be stored relative to the project file, not
    # absolute. Confirmed empirically against a real QGIS 3.44 install that this actually makes
    # each layer's `datasource` element relative (e.g. `./data/<slug>.gpkg|layername=...`) —
    # `QgsProject.write()` unconditionally also serializes a `<Paths><Absolute>false</Absolute>
    # </Paths>` element regardless of this setting (confirmed against a minimal, freshly-cleared
    # project with nothing else touched at all), which is simply how QGIS itself always writes
    # `.qgs` files; it is not specific to this setting and not something PyQGIS exposes any way to
    # suppress.
    try:
        from qgis.core import Qgis as _Qgis

        project.setFilePathStorage(_Qgis.FilePathType.Relative)
    except (ImportError, AttributeError):
        project.writeEntry("Paths", "/Absolute", False)

    schema = schemas.get_schema(survey_type)

    # DR-QPB-072 (Decision Log D-66): the "Reference" group must exist before the KTSN
    # accepted-name lookup layer (if any) is loaded into it as its first layer, below.
    _add_reference_group(project)

    layers = _add_domain_layers(pyqgis, project, gpkg_path, schema)
    _move_site_layer_last_among_editable_geometry_layers(project, layers, schema, survey_type)

    # FR-QPB-055 (revised; Decision Log D-71/AC-QPB-110): "Basemap" is added only now, after both
    # "Survey data" (just above) and "Reference" (just above that) already exist as root-level
    # groups, so it ends up last by children-index -- and therefore renders beneath both, instead
    # of on top of them.
    _add_basemap_group_after_survey_and_reference(project)

    ktsn_lookup_layer = None
    ktsn_taxonomy_layer = None
    if ktsn_taxonomy_table_name:
        ktsn_taxonomy_layer = _add_ktsn_taxonomy_reference_layer(
            pyqgis, project, gpkg_path, ktsn_taxonomy_table_name
        )
    if ktsn_lookup_table_name:
        ktsn_lookup_layer = _add_ktsn_lookup_layer(
            pyqgis, project, gpkg_path, ktsn_lookup_table_name
        )

    probability_raster_registration_count = 0
    if probability_raster_relative_path:
        _add_probability_raster_layer(pyqgis, project, qgs_path, probability_raster_relative_path)
        probability_raster_registration_count = 1

    relations_by_parent = _add_relations(pyqgis, project, schema, layers)
    _configure_forms_and_widgets(
        pyqgis,
        schema,
        layers,
        relations_by_parent,
        identification_enabled=identification_enabled,
        ktsn_lookup_layer=ktsn_lookup_layer,
        survey_type=survey_type,
        project_crs=project_crs,
        canonical_reference_enabled=bool(ktsn_taxonomy_table_name),
        canonical_layer_id=(ktsn_taxonomy_layer.id() if ktsn_taxonomy_layer is not None else None),
        canonical_runtime_lookup_resource=canonical_runtime_lookup_resource,
    )
    _configure_transactions(pyqgis, project, layers)

    if "community" in layers:
        _apply_community_symbology(pyqgis, layers["community"])

    # FR-QPB-120/FR-QPB-121 (Decision Log D-61/D-65): minimalist default point/polygon symbology
    # for every generated project (excluding the `community` layer just handled above), or the
    # fetched Tabler icon SVG in place of the default point marker, when one was successfully
    # embedded (`svg_relative_path`).
    _apply_symbol_styling(pyqgis, schema, layers, svg_relative_path)
    _apply_site_outline_symbology(pyqgis, layers.get("site"), survey_type)
    _apply_site_layer_opacity(layers.get("site"), survey_type)
    _configure_community_digitizing(project, pyqgis, layers, survey_type)

    online_key_embedded = False
    if basemap_config is not None:
        mode = basemap_config.get("mode")
        if mode == "online":
            online_key_embedded = _add_online_basemap_layer(pyqgis, project, basemap_config)
        elif mode == "offline" and mbtiles_relative_path:
            _add_offline_basemap_layer(
                pyqgis,
                project,
                mbtiles_relative_path,
                offline_source_identity or basemap_config.get("offline_source_identity"),
            )

    plantnet_key_embedded = _set_plantnet_project_variable(project, plantnet_config)
    vworld_key_saved = _set_vworld_project_variable(project, basemap_config)

    _set_project_attribution(project)

    # Re-assert the complete tree after all optional reference/basemap nodes have been added and
    # immediately before serialization. This protects the saved `.qgs` default state from any
    # later QGIS operation that may have reset a node's checked flag.
    _set_all_layer_tree_nodes_visible(project)
    Path(qgs_path).parent.mkdir(parents=True, exist_ok=True)
    project.write(qgs_path)

    return {
        "online_key_embedded": online_key_embedded,
        "vworld_key_saved": vworld_key_saved,
        "plantnet_key_embedded": plantnet_key_embedded,
        "probability_raster_registration_count": probability_raster_registration_count,
    }
