# Survey Route Planner — acceptance traceability

> **APPROVED workflow reconciliation — explicit user acceptance-artifact approval, 2026-09-16.**
> Approved specification input: `1868b7a`. Approved acceptance baseline: `ed8ac81`.
> This approval does not approve implementation or technology.
> Tests: [pytest module](survey_route_planner/test_survey_route_planner.py).
> [Design/manual cases](survey_route_planner.test-design.md) · [Harness](survey_route_planner/HARNESS_CONTRACT.md)

All test names below are real collected functions in the linked module. Automated checks are
contract/generated-output tests, not native QField/device evidence. Status for every criterion:
**APPROVED TEST DESIGN / PENDING IMPLEMENTATION AND VERIFICATION**. Six manual placeholders remain
explicitly skipped. Mocked Qt/QML/JavaScript never counts as native QField/iOS/Android evidence.
AC-SRP-011 remains historical and is mapped to its approved D-SRP-023 supersession; no executable
test asks for the removed remaining-route calculation.

| Approved criterion | Executable test suffix (prefix `test_`) | User-run / remaining boundary |
| --- | --- | --- |
| AC-SRP-001 | `ac001_generated_plugin` | M01; native imports/API and actual panel coexistence |
| AC-SRP-002 | `ac002_selection` (0/1/3, inline count/help and focused unselected) | M01; actual QField selection API |
| AC-SRP-003 | `ac002_selection`, `ac003_ac010_scope_mapping` (selected ignored by all/uncompleted), `ac003_site_default_mapping`, `ac003_type1_requires_explicit_mapping`, `ac003_reject_ids` | M01; actual QField layer/mapping controls |
| AC-SRP-004 | `ac004_start_and_return`, `ac004_missing_gps`, `ac008_offline_restart_relocation` | M02/M03; real GNSS, map interaction and moved default |
| AC-SRP-005 | `ac005_road_cost_request` (time/distance) | M02; live `ors-vroom` feasibility, no optimum guarantee |
| AC-SRP-006 | `ac006_failures_preserve_saved` (17 faults), `ac006_ac013_unknown_backend_rejected_before_request`, `ac002_selection[0]` | M02/M03; real connectivity failures |
| AC-SRP-007 | `ac007_result_roundtrip` (raw VROOM relative arrivals supplied/absent), `ac007_invalid_eta_rejected` (ISO/partial/negative/non-finite) | M02/M05; compare native relative ETA display and road overlay |
| AC-SRP-008 | `ac008_offline_restart_relocation` (routes, non-secret settings, key cleared) | M03; native process restart and moved folder |
| AC-SRP-009 | `ac009_storage_recovery` (5 faults) | M03; chosen native file API/atomicity proof |
| AC-SRP-010 | `ac003_ac010_scope_mapping`, `ac010_completion`, `ac010_completion_write_failure_preserves_state`, `ac010_ac011_ac027_all_complete_uses_saved_full_route` | M04; actual layer field refresh, inline help and route-local UI |
| AC-SRP-011 | `ac011_ac026_remaining_recalculation_is_superseded`, `ac010_ac011_ac027_all_complete_uses_saved_full_route` | Historical criterion superseded by AC026/027; M02/M04 verify absent control and zero requests |
| AC-SRP-012 | `ac012_road_and_naver` (OS success/refusal) | M05; actual Naver destination/app switching |
| AC-SRP-013 | `ac013_ac030_no_network_or_secrets` (5 passive operations), `ac013_backend_settings` (custom/default offset), `ac013_fresh_hosted_defaults_and_authorization`, `ac013_trailing_slashes_are_normalized_once`, `ac013_exact_legacy_default_migration` (5 exact/mixed/lookalike cases), `ac013_custom_self_hosted_urls_allow_no_key`, `ac013_hosted_default_rejects_blank_key_before_request`, `ac006_ac013_unknown_backend_rejected_before_request`, `ac008_offline_restart_relocation` | M01/M02/M03/M05; live hosted/custom transport, queued requests and redacted logs on device |
| AC-SRP-014 | `ac014_direct_drawing` (3 types), `ac014_incomplete_drawing` (4 invalid inputs) | M06; actual visual interaction |
| AC-SRP-015 | `ac015_ac016_uploaded_geometry` (3 formats×6 types), `ac015_ac016_parts_holes_xy`, `ac015_invalid_geometry` | M06; M/GeometryCollection policy still reserved |
| AC-SRP-016 | `ac015_ac016_uploaded_geometry`, `ac016_direct_generated_geometry`, `ac015_ac016_parts_holes_xy` | M06; actual generated layer rendering |
| AC-SRP-017 | `ac017_representatives_numerical` (2 CRS×6), `ac017_generated_geometry_uses_qfield_expression_evaluator` (2 CRS×6 strict generated-QML runs; forbids `geom_to_geojson`, requires supported centroid/transform/x/y), `ac017_projected_control_point`, `ac017_invalid_source_crs_preserves_saved` | M02/M06; native QField CRS/provider path still user-run |
| AC-SRP-018 | `ac018_ac030_regression_portability` (4 types×reference absent/present) | M06; existing polygon/relations/report/identify native regression |
| AC-SRP-019 | `ac019_builder_key_consent_embeds_only_project_variable`, `ac019_decline_or_blank_uses_manual_session_only` (2), `ac019_key_never_leaks_from_aborted_builder_flow` (2), `ac019_desktop_remember_is_not_qfield_delivery` | M02; actual device automatic/session key use, with redacted evidence only |
| AC-SRP-020 | `ac020_route_panel_fields_fill_available_width` (320/1024 px layout plus screenshots) | M01; actual narrow/wide device layout and touch use |
| AC-SRP-021 | `ac021_layer_dropdown_uses_alias_stable_id_and_site_default`, `ac021_duplicate_label_resolves_by_stable_id`, `ac021_field_refresh_provider_order_defaults_and_stale_values` (5 refresh boundaries), `ac021_no_field_match_and_stale_layer_clear_and_block` | M01; native layer tree/provider model and live schema mutation |
| AC-SRP-022 | `ac022_ac024_labels_guidance_and_conditional_controls` (2 widths × 3 modes), `ac022_stale_target_is_cleared_and_blocks_target_start` | M01/M02; native feature-model refresh and touch/keyboard controls |
| AC-SRP-023 | `ac023_storage_feedback_names_exact_committed_relative_path` (2), `ac023_storage_failure_has_no_success_or_secret_feedback` (2) | M03; actual QField FileUtils path and accessible project folder |
| AC-SRP-024 | `ac022_ac024_labels_guidance_and_conditional_controls` | M01/M04; native wrapping/readability |
| AC-SRP-025 | `ac025_exact_encoded_naver_url_and_honest_qt_true` (2 caller IDs), `ac025_mobile_fallback_and_all_refused` (Android/iOS), `ac025_non_mobile_has_actionable_error_without_install_dispatch`, retained `ac012_road_and_naver` | M05 separately on Android/iOS; actual handoff, destination acceptance and guidance |
| AC-SRP-026 | `ac011_ac026_remaining_recalculation_is_superseded`, `ac026_schema2_complete_immutable_legs_roundtrip` (open/roundtrip), `ac026_invalid_schema2_leg_preserves_existing_route` (7 faults), `ac026_provider_total_tolerance` (4 boundaries) | M02/M03; native QField storage roundtrip and UI control absence |
| AC-SRP-027 | `ac010_ac011_ac027_all_complete_uses_saved_full_route`, `ac027_prefix_out_of_order_uncheck_and_roundtrip_return` (mapped/local), `ac027_completion_overlay_is_blue_accessible_nonpersistent_and_rederived` (3 geometries × mapped/local), `ac027_mapped_write_failure_preserves_overlay_metrics_and_source`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M04; actual map rendering, source writes and recovery |
| AC-SRP-028 | `ac028_metric_formatting_and_bottom_bar` (4 ceil-minute edges), `ac028_route_line_toggle_scope_persistence_move_and_zero_api`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M03/M04; native device-local setting and overlay visibility |
| AC-SRP-029 | `ac029_legacy_schema1_load_is_offline_nonmutating_and_unavailable`, `ac029_explicit_full_recalculation_is_only_schema2_upgrade`, `ac029_future_schema_is_preserved_and_rejected` | M03/M06; real legacy bytes under QField storage API |
| AC-SRP-030 | `ac018_ac030_regression_portability`, `ac013_ac030_no_network_or_secrets` plus AC002/003/008/009/013–019/021–029 rows above | M01–M06; full native regression and redacted device evidence |

| Approved decision/requirement | Acceptance mapping |
| --- | --- |
| D-SRP-020, D-SRP-026; FR-SRP-021 | AC-SRP-021 dropdown tests; AC-SRP-022 stale target |
| D-SRP-021; FR-SRP-022–024 | AC-SRP-022–024 UI, feedback and guidance tests |
| D-SRP-022; FR-SRP-025 | AC-SRP-025 launcher tests and M05 |
| D-SRP-023, D-SRP-027–028; FR-SRP-026 | AC-SRP-026 schema-2/supersession tests; AC-SRP-029 legacy tests |
| D-SRP-024, D-SRP-029–030; FR-SRP-027 | AC-SRP-027 progression, write-preservation and overlay tests |
| D-SRP-025, D-SRP-030; FR-SRP-028 | AC-SRP-028 metric/bottom-bar/toggle tests |
| NFR-SRP-001 | AC-SRP-022/024 320px proxy plus M01 touch/keyboard |
| NFR-SRP-002 | AC-SRP-027 color+check+text proxy plus M04 |
| NFR-SRP-003 | AC-SRP-026–029 zero-request offline/restart/load/move tests plus M02–M04 |

## Earlier draft-stage verification record (2026-09-15; preserved)

Working directory: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`.
No application source/resource modifications, specification changes, Git mutations, real services,
QField operation or legacy-suite replay was performed by this test-designer. Required-mode execution
uses only the public acceptance seam and does not turn mocked external boundaries into native proof.

Commands use `PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`,
`FIELDBUILD_REQUIRE_SRP_HARNESS=1`, a unique pytest base temp, and raw logs under
`C:\Users\Public\Documents\ESTsoft\CreatorTemp\FieldBuildKit-route-verification\test-design-bd625d6`.
Exact commands, counts and failures are recorded after the draft run.

The design verifier checks syntax, all 20 AC IDs, the strict QfExpressionEvaluator surface and
supported-expression assertions, current/legacy endpoint constants, six documented centroid controls,
raw VROOM numeric arrival fixtures, portable setting fixtures and 18 real SHP/ZIP/GPKG input fixtures. These
are fixture/oracle checks, not application centroid/upload behavior. Current automated results and
unperformed M01–M06 cannot establish overall acceptance PASS.

- Collection: **159 cases**, exit 0.
- Design-only verifier: exit 0; syntax, all 20 AC IDs, raw relative-arrival and four malformed
  timing fixtures, current/legacy endpoint constants, the strict QfExpressionEvaluator surface and
  supported centroid/transform/x/y expression assertions, portable non-secret settings, six
  documented centroid fixtures, six independent Mercator controls, one EPSG:5186 control and 18
  real upload fixtures passed.
- Required-mode acceptance: **114 passed, 39 failed, 6 skipped**, exit 1, in 232.38 seconds. The
  skips are exactly M01–M06. The 39 expected pre-implementation failures are selection inline
  help/count observations (3), completion help and mapped-write preservation (4), generated
  QField-shaped valid/failing CRS paths including the `geom_to_geojson` regression (15), hosted/
  custom endpoint, migration and authentication contracts (9), builder key consent/session/
  leakage contracts (6), and narrow/wide panel layout screenshots (2). Existing passing cases are
  retained evidence only; this run is not product PASS.
- Whitespace check: exit 0; Git emitted only informational LF/CRLF normalization warnings.

Raw outputs: `collect-only.txt`, `verify-design.txt`, `required-mode.txt` and
`diff-check.txt` in the verification directory above. No failure was weakened to match the current
implementation.

## Workflow draft-stage verification record (2026-09-16)

Working directory and branch: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`,
`fix/qfield-project-plugin-loading`. No application/unit-test/specification changes, Git mutations,
live requests or device operations were performed. Commands used the repository interpreter,
`PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, and no pytest cache.

- Collection command: `.\.venv-win\Scripts\python.exe -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py --collect-only -q -p no:cacheprovider`. Result: **212 collected**, exit 0.
- Design verifier: `.\.venv-win\Scripts\python.exe tests/acceptance/survey_route_planner/verify_design.py`. Result: exit 0; syntax, all 30 AC IDs, removal of the old `remaining` operation, M01–M06, canonical encoded Naver URL, schema-2 open/roundtrip raw fixtures, schema-1 legacy fixture, dropdown/provider-order defaults, workflow/overlay/legacy text and all earlier fixture/oracle checks passed. It executes no application behavior.
- Focused required-mode command selected AC021–029 plus the AC011/026 supersession via `-k 'ac021 or ac022 or ac023 or ac024 or ac025 or ac026 or ac027 or ac028 or ac029'`. Result: **2 passed, 57 failed, 153 deselected**, exit 1, 93.12 s. The two passing cases were retained AC007 raw timing roundtrips that the selector also matched before their final trace-only rename. All 57 intended new/supersession cases were product/harness red: unsupported `project_dropdowns`, `route_workflow_ui`, `storage_feedback`, extended `reopen_navigate`, `schema2_roundtrip`, `route_progression`, `completion_overlay`, `metric_display`, `route_line_toggle`, and `legacy_route` observations, plus the expanded mapped-write state contract. These are pre-implementation failures, not collection/design errors.
- `git diff --check -- <five changed acceptance files>`: exit 0; only informational LF/CRLF warnings.

M01–M06 remain **NOT RUN**. The run does not establish native QField, Android/iOS, Naver,
FileUtils/atomic storage, live provider or product acceptance PASS.
