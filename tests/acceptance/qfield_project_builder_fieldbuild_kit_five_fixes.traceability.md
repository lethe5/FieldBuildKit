# FieldBuild Standalone five-fix integration traceability

Specification: [`specs/fieldbuild-kit-five-fixes.md`](../../specs/fieldbuild-kit-five-fixes.md)

Tests: [`qfield_project_builder/test_fieldbuild_kit_five_fixes.py`](qfield_project_builder/test_fieldbuild_kit_five_fixes.py)

The automated tests use the existing isolated `acceptance_api`/`build_project()` contract and one
new narrow `inspect_display_expressions(project_dir)` seam documented in
[`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).
The Python acceptance harness cannot run the PySide6 wizard, a supported browser, or QField/QML on
a physical device. Those runtime portions are explicit skipped `manual`/`device` acceptance gates,
with concrete steps in the test's skip reason; they are not silently treated as passing.

| Approved criterion | Coverage |
|---|---|
| AC-FIX-001 | `test_acfix001_full_logo_is_above_content_on_every_wizard_page` — manual minimum-window wizard check for the full logo, ordering, overlap, clipping, and watermark replacement. |
| AC-FIX-002 | `test_acfix002_successful_offline_build_publishes_only_a_completed_mbtiles_file` checks successful publication; `test_acfix002_progress_timeout_cancel_provider_and_size_outcomes_are_distinct` is the manual lifecycle gate for progress beyond the former timeout, cancellation, request timeout, provider failure, size failure, cleanup, and actionable outcome reporting. Existing `test_basemap_offline.py` cleanup/size/provider tests remain supporting regression coverage. |
| AC-FIX-003 | `test_acfix003_type3_generated_identification_path_targets_saved_child_fields` checks generated write-back constituents; `test_acfix003_type3_related_child_write_back_survives_save_reopen_on_device` is the Type 3 Related-records save/reopen gate for the child fields, UUID, FK, parent, and siblings. |
| AC-FIX-004 | `test_acfix004_top_right_plugin_labels_are_complete_and_actionable` — manual minimum-size, resize, Korean-localization, font-metrics, readability, and independent-actionability check. |
| AC-FIX-005 | `test_acfix005_report_source_contains_body_map_table_and_single_runtime_entrypoints` checks generated report constituents; `test_acfix005_report_map_table_and_csv_are_integrated_and_usable` is the browser/QField gate for valid standalone HTML, one-time initialization after target elements exist, map/table/CSV body placement, filtered/all-row scope, UTF-8 Korean values, quoting, and no-network/no-geometry resilience. |
| AC-FIX-006 | `test_acfix006_offline_selector_mirrors_online_layer_selector_and_controls_download` — manual comparison of the offline selector with the online selector, explicit single-choice behavior, capability-advertised VWorld options, selected-layer acquisition, and OSM exclusion. |
| AC-FIX-007 | `test_acfix007_selected_offline_layer_is_recorded_without_api_key` checks selected VWorld/layer identity in MBTiles metadata and generated project output, relative local MBTiles reference, and API-key exclusion. The AC-FIX-006 manual gate also verifies the UI identity and actual selected tile source. |
| AC-FIX-008 | `test_acfix008_empty_or_stale_offline_catalog_fails_closed_without_partial_output` — manual no-supported-source and stale-selection revalidation gate, including no substitution and no partial output. |
| AC-FIX-009 | `test_acfix009_observation_display_expression_is_exact` (Type 2 and Type 3) compares the configured `observation` display expression literally to the approved contract. |
| AC-FIX-010 | `test_acfix010_acfix011_related_observations_are_distinct_and_editable_on_device` — manual multiple-child, duplicate-value, relation-order, and no-omission gate. |
| AC-FIX-011 | `test_acfix010_acfix011_related_observations_are_distinct_and_editable_on_device` — manual NULL/zero/empty-state display and exact fallback semantics gate; `test_acfix012_acfix013_survey_and_child_display_behavior_survives_refresh` also checks child action and post-save label refresh. |
| AC-FIX-012 | `test_acfix012_acfix013_survey_and_child_display_behavior_survives_refresh` — manual existing child open/edit/save/reopen and UUID/FK integrity gate. |
| AC-FIX-013 | `test_acfix013_survey_display_expression_is_exact` (Type 2, Type 3, and Type 4) compares the configured `survey` expression literally and rejects the old fallback; the manual companion covers Type 2 seed NULL/blank evaluation and refresh behavior. |
| AC-FIX-014 | `test_acfix014_identification_qml_uses_domain_location_and_no_image_metadata` checks Type 1–3 generated identification source for the authoritative geometry-chain vocabulary and absence of EXIF/photo-GPS/device-GPS paths; `test_acfix014_type4_has_no_identification_target_or_location_path` checks Type 4 exclusion; `test_acfix015_acfix016_invalid_location_does_not_block_identification_or_mutate_photo` is the manual precedence/privacy/runtime gate. |
| AC-FIX-015 | `test_acfix015_acfix016_invalid_location_does_not_block_identification_or_mutate_photo` — manual missing/invalid/ambiguous/wrong-type/non-finite/out-of-bounds geometry gate verifying only occurrence probability is skipped, no numeric zero/fallback is produced, and identification/candidate/selection/write-back continue. |
| AC-FIX-016 | `test_acfix014_identification_qml_uses_domain_location_and_no_image_metadata` checks the generated source boundary; `test_acfix015_acfix016_invalid_location_does_not_block_identification_or_mutate_photo` — manual EXIF/image-metadata/device-GPS exclusion, authoritative-source, original attachment path/bytes, candidate, and save/reopen gate. |
| AC-FIX-017 | `test_acfix017_qfield_4211_related_daughter_is_immediately_visible_once_after_save` — explicit QField 4.2.11 iOS acceptance script. This is intentionally device-only: the existing harness can inspect relation configuration, but cannot drive QField's related-record save, immediate-parent list refresh, navigation, or reopen lifecycle. |

## Harness boundary

The exact QGIS expressions are inspected through the real generated project using the isolated
harness seam; the acceptance test does not construct `QgsApplication` or evaluate a hand-written
fixture expression. QField-side runtime claims (wizard rendering, report DOM/runtime behavior,
relation-row interaction, saved-feature persistence, request/context inspection, and attachment
byte preservation) are deliberately recorded as manual/device gates because the existing Python
acceptance environment cannot execute those hosts.

No approved criterion was left uncovered due to ambiguity. The test design does not add a new
provider, schema field, fallback location, report data model, or display-expression normalization.

## Execution

Automated generated-artifact checks:

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_fieldbuild_kit_five_fixes.py -q
```

To inspect the complete manual/device checklist without attempting to run skipped gates:

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_fieldbuild_kit_five_fixes.py --collect-only -q
```
