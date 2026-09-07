"""Unit-level guards for D-92's generated saved-feature write-back bridge."""

from qfield_builder import qml_plugin


def test_project_plugin_uses_existing_form_and_layer_uuid_gated_attribute_model():
    source = qml_plugin.render_project_plugin_qml("saved_edit")

    assert 'iface.findItemByObjectName("featureForm")' in source
    assert "request.layer" in source
    assert "qpbReadLayerFromFeatureModel" in source
    assert "model.featureModel.currentLayer" in source
    assert "changeAttribute(fieldName, request.fields[fieldName])" in source
    assert "QfFeatureListForm.model" not in source
    assert "QfMultiFeatureListModel" not in source


def test_project_plugin_searches_nested_relation_popup_after_saved_feature_host():
    """A saved observation nested below Plot → Survey must still reach its own live form."""
    source = qml_plugin.render_project_plugin_qml("saved_nested_edit")
    apply_start = source.index("function qpbApplyPendingWriteBack(request) {")
    apply_end = source.index("function qpbFindMatchingFeatureModel", apply_start)
    apply_body = source[apply_start:apply_end]

    assert "var popupVisited = [];" in apply_body
    assert "qpbFindActiveRelationModel(popup, request, popupVisited)" in apply_body
    assert "qpbFindMatchingFeatureModel(iface.mainWindow()" not in apply_body
    assert apply_body.index("qpbFindActiveRelationModel(existingForm") < apply_body.index(
        "var popupVisited = [];"
    )


def test_project_plugin_uses_qfield_embedded_popup_path_without_global_model_walk():
    """QField 4.2.4 RelationEditorBase names an opened child `embeddedPopup`."""
    source = qml_plugin.render_project_plugin_qml("nested_relation")

    assert '"embeddedPopup", "embeddedFeatureForm"' in source
    assert "var maxNodes = 4096;" in source
    assert "qpbPendingWriteBackMaxAgeMs: 5000" in source
    assert "qpbFindMatchingFeatureModel(iface.mainWindow()" not in source
    assert "A mismatched/unreadable wrapper identifier cannot override the UUID match above." in source


def test_project_plugin_writes_a_bounded_write_back_trace_for_device_diagnosis():
    source = qml_plugin.render_project_plugin_qml("nested_relation")

    assert 'qpb_identification_writeback_trace.json' in source
    assert 'qpbTraceWriteBack("target_not_found", qpbWriteBackSearch)' in source
    assert 'qpbTraceWriteBack("korean_change_rejected"' in source
    assert 'qpbTraceWriteBack("write_applied", qpbWriteBackSearch)' in source


def test_identification_widget_writes_location_and_probability_runtime_trace():
    source = qml_plugin.render_identification_widget_qml("''")

    assert 'qpb_identification_runtime_trace.json' in source
    assert 'qpbTraceRuntime("location_resolved"' in source
    assert 'qpbTraceRuntime("probability_skipped_no_location"' in source
    assert 'qpbTraceRuntime("probability_sample"' in source


def test_identification_widget_writes_to_its_own_live_form_before_queueing():
    """Nested relation popups need no app-wide form traversal when the widget has its form."""
    source = qml_plugin.render_identification_widget_qml("''")

    assert "function qpbApplyCurrentFormWriteBack(fields)" in source
    assert "form.model.changeAttribute(name, value)" in source
    assert "var appliedDirectly = qpbApplyCurrentFormWriteBack(writeFields);" in source
    assert "var queued = appliedDirectly ? false : qpbWriteAttributeWriteBackRequest(writeFields);" in source


def test_widget_request_carries_layer_uuid_and_bounded_lifetime():
    source = qml_plugin.render_identification_widget_qml("''", layer_context="식물관찰")

    assert 'addLayerContext("식물관찰");' in source
    assert "uuid_field: current.uuid_field" in source
    assert "layer: current.layer" in source
    assert "created_at: new Date().getTime()" in source
    assert "if (!current.layer) { return; }" in source
