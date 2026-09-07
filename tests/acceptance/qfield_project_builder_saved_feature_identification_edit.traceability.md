# D-92 traceability — saved plant-observation identification edit write-back

Specification: [`specs/saved-feature-identification-edit.md`](../../specs/saved-feature-identification-edit.md)

Tests: [`qfield_project_builder/test_saved_feature_identification_edit.py`](qfield_project_builder/test_saved_feature_identification_edit.py)

The generated-artifact checks are necessary structural checks only.  This Python harness has no
QField/QML runtime, cannot open a saved feature, and cannot perform a physical-device save/reopen.
The explicitly `device`/`manual`-marked tests are therefore required QA placeholders, not silently
passed claims.

| Criterion | Coverage |
|---|---|
| AC-SFE-001 | `test_ac001_saved_type_1_2_and_3_direct_edit_round_trip_on_device` — explicit real-device placeholder covering direct Type 1, Type 2, and Type 3 observation-layer edit, save, and reopen. |
| AC-SFE-002 | `test_ac002_type_3_relation_path_preserves_uuid_fk_parent_and_siblings_on_device` — explicit real-device placeholder for `조사지 → 조사 → 식물관찰`, UUID/FK, parent, and sibling integrity. |
| AC-SFE-003 | `test_ac003_direct_saved_edit_updates_only_intended_observation_on_device` — explicit device placeholder for no duplicate and no cross-observation mutation, including existing candidate metadata. |
| AC-SFE-004 | `test_ac004_terminal_accepted_name_is_persisted_for_direct_and_relation_edits_on_device` — explicit device placeholder for terminal `정명` resolution in both paths. |
| AC-SFE-005 | `test_ac005_plugin_is_structurally_fail_closed_until_uuid_and_model_context_match` covers static retry/UUID/model/delete guards; `test_ac005_unmounted_or_uuid_mismatched_model_is_fail_closed_on_device` is the required runtime diagnostic/retention placeholder. |
| AC-SFE-006 | `test_ac006_release_device_verification_record_for_direct_and_type3_paths` — explicit release-device placeholder requiring QField version/platform evidence and both paths. |
| AC-SFE-007 | `test_ac007_existing_feature_lookup_is_distinct_and_targets_active_attribute_form_model` — generated QML structural check for distinct existing-form lookup, active `FeatureForm.model`/attribute model, UUID/layer context, all three selected fields, relation traversal, and no feature-list write target. |
| AC-SFE-008 | `test_ac007_existing_feature_lookup_is_distinct_and_targets_active_attribute_form_model` supplies the automated no-list-model structural guard; `test_ac008_unreachable_existing_attribute_model_is_reported_as_concrete_qfield_limitation` is the required target-runtime limitation-reporting placeholder. |

## Harness boundary and interpretation

No test claims that static source text proves QField execution or persistence.  AC-SFE-001–006 and
the runtime portions of AC-SFE-005/008 remain device/manual evidence gates.  The structural test
requires a request layer context in addition to a domain UUID, and rejects
`QfFeatureListForm.model`/`QfMultiFeatureListModel` as an editable target.  It does not prescribe
private QML internals or a particular traversal implementation.
