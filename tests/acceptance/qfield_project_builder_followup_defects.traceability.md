# FieldBuild Standalone follow-up defect traceability

Specification: [`specs/fieldbuild-kit-followup-defects.md`](../../specs/fieldbuild-kit-followup-defects.md)

Tests: [`qfield_project_builder/test_fieldbuild_kit_followup_defects.py`](qfield_project_builder/test_fieldbuild_kit_followup_defects.py)

> Status: DRAFT — awaiting stakeholder approval of the acceptance-test artifact.

The new tests reuse the existing `acceptance_api.build_project()`/fake-tile-source seam and the
existing `make_base_config`, `inspect_identification_widget`, and `inspect_editor_widget` fixtures.
No application source, specification, shared document, or existing acceptance test was changed.
The Python acceptance harness cannot drive QField/QML runtime or normal device save/reopen; those
boundaries are explicit `manual`/`device` gates below. No test waits for the former 12-hour
ceiling.

| Approved criterion | Coverage | Classification |
|---|---|---|
| AC-FOLLOWUP-001 | `test_ac_followup_001_progressing_offline_build_completes_with_bounded_cleanup_contract` exercises a progressing fake offline build, completed MBTiles publication, cancellation flag, and absence of partial/temp output. `test_ac_followup_001_progress_beyond_former_12h_ceiling_and_failure_outcomes_on_device` is the accelerated/time-scaled lifecycle gate for progress beyond the former fixed ceiling, bounded request timeout, cancellation, provider error, size failure, actionable outcomes, and cleanup. | auto smoke + manual/device elapsed-time gate |
| AC-FOLLOWUP-002 | `test_ac_followup_002_qml_direct_write_targets_only_active_child_korean_name` structurally checks the active child form/model, UUID/layer context, `selected_korean_name` read-back, and the existing QGIS-derived `selected_scientific_name`/`selected_ktsn` `apply_on_update` + read-only contract. `test_ac_followup_002_type3_child_writeback_and_save_reopen_on_device` covers the real Type 3 Related-records selection and normal save/reopen boundary. | auto structural proxy + manual/device |
| AC-FOLLOWUP-003 | `test_ac_followup_003_explicit_supported_layer_reaches_existing_offline_scenarios` supplies an explicit supported VWorld layer to the existing fake success/metadata path. `test_ac_followup_003_missing_selected_layer_fails_with_existing_selection_error` asserts no silent default and the existing `offline_layer_unavailable` failure. | auto |
| AC-FOLLOWUP-004 | `test_ac_followup_004_size_guard_precedes_fake_tile_fetch_for_valid_selected_layer` uses a valid selected layer plus a fake quota error as a negative control: the size failure must win before fake tile acquisition. `test_ac_followup_004_within_threshold_selected_layer_reaches_tile_source` checks the within-threshold path still reaches a successful fake source. | auto |
| AC-FOLLOWUP-005 | `test_ac_followup_005_type1_identify_is_direct_manual_only_and_separate_from_key_embedding_consent` checks Type 1's `사진으로 동정하기` handler for a direct `qpbRunIdentification()` call, no application-owned consent/OK dialog or dialog opening, and exactly one runtime identification call so photo attachment cannot auto-identify. It covers accepted and declined desktop Pl@ntNet-key embedding consent independently: direct field behavior is unchanged, while only the accepted project embeds the test key. `test_ac_followup_005_type1_direct_identification_and_key_consent_boundary_on_device` remains the explicit real-QField gate. | auto structural proxy + manual/device |
| AC-FOLLOWUP-006 | `test_ac_followup_006_d91_offline_visibility_remains_open_classification` is an explicit skipped/open gate tied to O-FOLLOWUP-001 and the existing D-91 visibility evidence. It does not claim to fix or exclude visibility behavior before D-91 scope/approval is resolved. | manual/open question |
| AC-FOLLOWUP-007 | `test_ac_followup_007_type23_photo_expression_matches_strict_type1_inline_shape` rechecks the existing strict Type 2/3 inline expression shape against Type 1, including direct three-column references and rejection of `relation_aggregate()` and `rel_observation_photo_observation`. It complements the existing strict tests in `test_observation_photo_removal.py` rather than weakening them. | auto structural |
| AC-FOLLOWUP-008 | `test_ac_followup_008_missing_or_blank_key_fails_before_size_or_fake_download` covers absent, empty, and whitespace-only keys with a huge estimate, explicit supported layer, fake success source, and cancel hook; missing-key validation must precede size, acquisition, cancellation, and output. | auto |
| AC-FOLLOWUP-009 | `test_ac_followup_009_successful_offline_outputs_contain_no_vworld_key_anywhere` inspects MBTiles metadata and every file in the generated self-contained mobile transfer folder, including `.qgs`, `MANIFEST.json`, and `VALIDATION_REPORT.json`. | auto |

## Boundary notes

- The existing offline fixture shape in `test_basemap_offline.py` omits `layer`; this new file
  deliberately supplies one for every valid offline build, while retaining one explicit missing-
  selection negative case. Existing tests remain unchanged.
- The write-back test does not require QML `changeAttribute()` calls for either derived field. It
  checks those fields through the existing QGIS `apply_on_update`/read-only inspection contract;
  end-to-end normal save/reopen remains a device gate.
- D-93 supersedes the stale D-90 Type 1 consent boundary: Type 1 joins Type 2/3 on the direct,
  explicit-Identify path. The desktop Pl@ntNet-key embedding consent remains a separate
  project-generation concern, and attachment alone must not auto-identify. D-91 offline visibility
  is intentionally an unresolved open-question boundary, not a follow-up pass/fail claim.
- The automated AC-FOLLOWUP-001 test is only a bounded forward-progress smoke test. The former
  12-hour liveness seam and all distinct failure outcomes require the documented accelerated/manual
  lifecycle gate; it must never be implemented as a real 12-hour wait.

## Execution support

Only authoring-support checks were run after writing this artifact: Python AST parsing and pytest
collection for this new file. The acceptance tests themselves were not executed in this stage.
