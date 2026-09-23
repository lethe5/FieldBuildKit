# Survey Route Planner — approved AC-SRP-066 traceability over approved AC-SRP-063–065

> **APPROVED TEST DESIGN (approval 2026-09-22).** AC-SRP-066 mappings use
> approved clarification checkpoint `cb8f2da`.

> **APPROVED TEST DESIGN (approval 2026-09-22).** The AC-SRP-063–065 mappings below trace
> only to approved D-SRP-064–066 / FR-SRP-061–063 / NFR-SRP-011. Approved AC-SRP-061–062 and
> earlier traceability remains preserved. Any older acknowledgement-gated save row is superseded
> only to the extent stated by D-SRP-064.

> **APPROVED TEST DESIGN (approval 2026-09-22).** AC-SRP-061–062 mappings are approved;
> earlier statuses below are preserved.

> **APPROVED TEST DESIGN (approval 2026-09-21).** The AC-SRP-059 endpoint-snapping
> acceptance baseline is approved. The reviewer correction below remains
> **DRAFT TEST DESIGN — user approval required**.

> Current AC-SRP-049–058 status: **DRAFT TEST DESIGN (2026-09-21)**.
> The approved AC-SRP-001–048 mappings below remain preserved and are not reopened.

> **DRAFT retained-suite reconciliation (2026-09-21).** Stale retained expectations are aligned
> with approved D-SRP-050/053/056/058/059 and AC-SRP-055/057/058; product meaning is unchanged.

> **APPROVED TEST DESIGN — supersession reconciliation (approval 2026-09-17).**
> This approved reconciliation aligns retained AC-SRP-019/022/024/031 executable expectations with approved
> D-SRP-043/045, FR-SRP-041/043 and AC-SRP-043/045. Prior approvals below remain preserved.

> **APPROVED TEST DESIGN (approval 2026-09-16).**
> Approved baseline `bcd6ffc` and its approved AC003/007/008 correction remain preserved.
> Approved D-SRP-031–035, FR-SRP-029–033 and AC-SRP-031–035 expectations remain preserved.
> This approved test-design correction changes evidence provenance and defective fixtures only; it does not approve implementation.
> AC-SRP-036–041 rows are **APPROVED TEST DESIGN (approval 2026-09-17)** and preserve the
> approved AC-SRP-001–035 baseline.
> The supersession reconciliation recorded below is **APPROVED TEST DESIGN (approval 2026-09-17)**.
> D-SRP-042–045, FR-SRP-040–043, NFR-SRP-005, AC-SRP-042–045 and D-UI-SRP-007–010 rows retain
> their **APPROVED TEST DESIGN (approval 2026-09-17)** history. The evidence correction is
> **APPROVED TEST DESIGN (approval 2026-09-17)** and preserves the approved AC-SRP-001–045 meaning.
> The former AC-SRP-046–048 / AC-QPB-149–150 design remains historical. Its evidence-mechanics
> correction below is **APPROVED TEST DESIGN (approval 2026-09-18)**; product requirements are unchanged.
> Tests: [pytest module](survey_route_planner/test_survey_route_planner.py).
> [Design/manual cases](survey_route_planner.test-design.md) · [Harness](survey_route_planner/HARNESS_CONTRACT.md)

All test names below are real collected functions in the linked module. Automated checks are
contract/generated-output tests, not native QField/device evidence. AC-SRP-001–030 retain their
**APPROVED TEST DESIGN / PENDING IMPLEMENTATION AND VERIFICATION** status. AC-SRP-031–035 are
approved requirements with an **APPROVED TEST DESIGN EVIDENCE CORRECTION (approval 2026-09-16)**.
AC-SRP-036–041 have **APPROVED TEST DESIGN (approval 2026-09-17)** status. M01–M10 remain
preserved; M01–M17 are **NOT RUN** and explicitly skipped. Mocked Qt/QML/JavaScript never
counts as native QField/iOS/Android evidence.
AC-SRP-011 remains historical and is mapped to its approved D-SRP-023 supersession; no executable
test asks for the removed remaining-route calculation.

| Approved criterion | Executable test suffix (prefix `test_`) | User-run / remaining boundary |
| --- | --- | --- |
| AC-SRP-001 | `ac001_generated_plugin` (stable loaded-QML control identity; provider-setting child present/enabled but hidden by the initially collapsed D-SRP-038 disclosure) | M01; native imports/API and actual panel coexistence |
| AC-SRP-002 | `ac002_selection` (0/1/3, inline count/help and focused unselected) | M01; actual QField selection API |
| AC-SRP-003 | `ac002_selection`, `ac003_ac010_scope_mapping` (selected ignored by all/uncompleted), `ac003_site_default_mapping` (generated stable QGIS layer ID), `ac003_type1_requires_explicit_mapping`, `ac003_reject_ids` | M01; actual QField layer/mapping controls |
| AC-SRP-004 | `ac004_start_and_return`, `ac004_missing_gps`, `ac008_offline_restart_relocation` | M02/M03; real GNSS, map interaction and moved default |
| AC-SRP-005 | `ac005_road_cost_request` (time/distance) | M02; live `ors-vroom` feasibility, no optimum guarantee |
| AC-SRP-006 | `ac006_failures_preserve_saved` (17 faults), `ac006_ac013_unknown_backend_rejected_before_request`, `ac002_selection[0]` | M02/M03; real connectivity failures |
| AC-SRP-007 | `ac007_result_roundtrip` (raw VROOM relative arrivals supplied/absent; schema-2 ordered from/to IDs, metrics, WGS84 leg geometry and sequence), `ac007_invalid_eta_rejected` (ISO/partial/negative/non-finite) | M02/M05; compare native relative ETA display and road overlay |
| AC-SRP-008 | `ac008_offline_restart_relocation` (routes, stable layer-ID settings, default route-line preference, key cleared) | M03; native process restart and moved folder |
| AC-SRP-009 | `ac009_storage_recovery` (5 faults) | M03; chosen native file API/atomicity proof |
| AC-SRP-010 | `ac003_ac010_scope_mapping`, `ac010_completion` (ordered `0` then `1` persistence), `ac010_completion_write_failure_preserves_state`, `ac010_ac011_ac027_all_complete_uses_saved_full_route`; later-row blocking is independently covered by AC040 | M04; actual layer field refresh, inline help and route-local UI |
| AC-SRP-011 | `ac011_ac026_remaining_recalculation_is_superseded`, `ac010_ac011_ac027_all_complete_uses_saved_full_route` | Historical criterion superseded by AC026/027; M02/M04 verify absent control and zero requests |
| AC-SRP-012 | `ac012_road_and_naver` (official Android package intent plus OS success/refusal and store fallback) | M05; actual Naver destination/app switching |
| AC-SRP-013 | `ac013_ac030_no_network_or_secrets` (5 passive operations), `ac013_backend_settings` (custom/default offset), `ac013_fresh_hosted_defaults_and_authorization`, `ac013_trailing_slashes_are_normalized_once`, `ac013_exact_legacy_default_migration` (5 exact/mixed/lookalike cases), `ac013_custom_self_hosted_urls_allow_no_key`, `ac013_hosted_default_rejects_blank_key_before_request`, `ac006_ac013_unknown_backend_rejected_before_request`, `ac008_offline_restart_relocation` | M01/M02/M03/M05; live hosted/custom transport, queued requests and redacted logs on device |
| AC-SRP-014 | `ac014_direct_drawing` (3 types), `ac014_incomplete_drawing` (4 invalid inputs) | M06; actual visual interaction |
| AC-SRP-015 | `ac015_ac016_uploaded_geometry` (3 formats×6 types), `ac015_ac016_parts_holes_xy`, `ac015_invalid_geometry` | M06; M/GeometryCollection policy still reserved |
| AC-SRP-016 | `ac015_ac016_uploaded_geometry`, `ac016_direct_generated_geometry`, `ac015_ac016_parts_holes_xy` | M06; actual generated layer rendering |
| AC-SRP-017 | `ac017_representatives_numerical` (2 CRS×6), `ac017_generated_geometry_uses_qfield_expression_evaluator` (2 CRS×6 strict generated-QML runs; forbids `geom_to_geojson`, requires supported centroid/transform/x/y), `ac017_projected_control_point`, `ac017_invalid_source_crs_preserves_saved` (production save/reopen/active baseline provenance) | M02/M06; native QField CRS/provider path still user-run |
| AC-SRP-018 | `ac018_ac030_regression_portability` (4 types×reference absent/present) | M06; existing polygon/relations/report/identify native regression |
| AC-SRP-019 | `ac019_builder_key_consent_embeds_only_project_variable` (actual Step 7 warning/consent widget exact-copy observation under D-SRP-045), `ac019_decline_or_blank_uses_manual_session_only` (2), `ac019_key_never_leaks_from_aborted_builder_flow` (2), `ac019_desktop_remember_is_not_qfield_delivery` | M02; actual device automatic/session key use, with redacted evidence only |
| AC-SRP-020 | `ac020_route_panel_fields_fill_available_width` (320/1024 px layout plus screenshots) | M01; actual narrow/wide device layout and touch use |
| AC-SRP-021 | `ac021_layer_dropdown_uses_alias_stable_id_and_site_default`, `ac021_duplicate_label_resolves_by_stable_id`, `ac021_field_refresh_provider_order_defaults_and_stale_values` (5 refresh boundaries), `ac021_no_field_match_and_stale_layer_clear_and_block` | M01; native layer tree/provider model and live schema mutation |
| AC-SRP-022 | `ac022_ac024_labels_guidance_and_conditional_controls` (2 widths × 3 modes, D-SRP-037 `계산 대상`, D-SRP-043 `저장 경로 불러오기`, explicit all scope), `ac022_stale_target_is_cleared_and_blocks_target_start` | M01/M02; native feature-model refresh and touch/keyboard controls |
| AC-SRP-023 | `ac023_storage_feedback_names_exact_committed_relative_path` (2), `ac023_storage_failure_has_no_success_or_secret_feedback` (2) | M03; actual QField FileUtils path and accessible project folder |
| AC-SRP-024 | `ac022_ac024_labels_guidance_and_conditional_controls` (`저장 경로 불러오기` dropdown; editable field remains `저장할 경로 이름`) | M01/M04; native wrapping/readability |
| AC-SRP-025 | `ac025_exact_encoded_android_intent_and_honest_qt_true` (2 caller IDs), `ac025_android_fallback_and_all_refused`, `ac025_non_mobile_has_actionable_error_without_install_dispatch`, retained `ac012_road_and_naver`; iOS branch superseded by AC055 | M05 Android; actual handoff, destination acceptance and guidance |
| AC-SRP-026 | `ac011_ac026_remaining_recalculation_is_superseded`, `ac026_ac035_schema3_complete_immutable_legs_roundtrip` (explicit mixed save, open/roundtrip), `ac026_invalid_schema2_leg_preserves_existing_route` (7 raw route-level/top-level ORS fixture faults), `ac026_provider_total_tolerance` (4 boundaries) | M02/M03; native QField storage roundtrip and UI control absence; separate legacy schema-2 reads retained |
| AC-SRP-027 | `ac010_ac011_ac027_all_complete_uses_saved_full_route`, `ac027_ordered_completion_then_uncheck_creates_out_of_order_gap_and_roundtrip_return` (blocked later-row attempt, then ordered completion and uncheck-created gap; mapped/local; raw intermediate-vertex directions and committed-route provenance), `ac027_completion_overlay_is_blue_accessible_nonpersistent_and_rederived` (3 geometries × mapped/local), `ac027_mapped_write_failure_preserves_overlay_metrics_and_source`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M04; actual map rendering, source writes and recovery |
| AC-SRP-028 | `ac028_metric_formatting_and_bottom_bar` (4 ceil-minute edges), `ac028_route_line_toggle_scope_persistence_move_and_zero_api`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M03/M04; native device-local setting and overlay visibility |
| AC-SRP-029 | `ac029_legacy_schema1_load_is_offline_nonmutating_and_unavailable`, `ac029_explicit_full_recalculation_upgrades_to_schema3`, `ac029_future_schema_is_preserved_and_rejected` (schema 4) | M03/M06; real legacy bytes under QField storage API |
| AC-SRP-030 | `ac018_ac030_regression_portability`, `ac013_ac030_no_network_or_secrets` plus AC002/003/008/009/013–019/021–029 rows above | M01–M06; full native regression and redacted device evidence |
| AC-SRP-031 | `ac031_six_selectors_use_ors_floating_labels_without_collision` (historical six-control subset, 2 widths × empty/value/focus/error; D-SRP-037 shortened labels; distinct loaded-QML object IDs, geometry, style and accessibility; separate-row check scoped to these control labels) | AC043 is final authority for all eight controls; M01 covers native touch/keyboard focus, screen-reader name and device clipping |
| AC-SRP-032 | `ac032_map_start_marker_is_exact_fixed_and_replaced_not_duplicated`; `ac032_map_start_marker_survives_panel_and_calculation_events` (3); `ac032_map_start_marker_removed_at_lifecycle_end` (4); `ac032_map_start_transform_failure_preserves_previous_marker_and_start` (full canvas enumeration and actual provider/storage write capture) | M02; actual QField map item, project-close lifecycle and visual distinction |
| AC-SRP-033 | `ac033_target_candidates_match_preflight_before_required_validation` (3 scopes × 0/1/3); `ac033_candidate_refresh_preserves_valid_id_and_clears_stale_after_changes` (separate model/preflight capture IDs and submitted order) | M01; actual QField selection/schema/completion events |
| AC-SRP-034 | `ac034_selection_guidance_is_selected_only_and_leaves_no_gap` (2 widths × 3 scopes × 0/1/3; visible row coordinates and hidden-item layout absence) | M01; native rendered placement and device accessibility |
| AC-SRP-035 | `ac026_ac035_schema3_complete_immutable_legs_roundtrip` (open/roundtrip documented ORS slices saved as mixed schema 3); `ac035_provider_contract_defects_are_actionable_and_preserve_last_good` (11 raw defects); `ac035_valid_provider_response_forced_client_failure_is_distinct_and_preserves_last_good`; `ac035_six_geometry_families_accept_real_ors_contract_from_approved_representative` (6 real materialized source→generated GPKG/QGS paths) | M02 plus M07 Point, M08 LineString, M09 Polygon; actual QField/live ORS results remain unperformed |
| AC-SRP-036 | `ac036_name_entry_and_changes_save_existing_candidate_without_recalculation`; `ac036_recoverable_save_failure_preserves_candidate_for_corrected_retry` (3); `ac036_calculation_input_change_blocks_stale_candidate`; `ac036_settings_revision_refreshes_candidate_base_without_stale` | M10; native QField focus/input and file-failure retry |
| AC-SRP-037 | `ac037_seven_controls_share_rendered_outlined_floating_label_contract` (2 widths × 5 states; raw loaded-QML rectangles/style/accessibility) | M10; native touch/keyboard/screen reader and clipping |
| AC-SRP-038 | `ac038_api_settings_initially_collapsed_and_toggle_is_passive`; `ac038_key_provenance_and_session_lifetime_are_observed_from_generated_project` (2); `ac038_settings_save_reports_actual_slot_and_excludes_key_and_objective`; `ac038_failed_settings_save_preserves_last_good_and_session_key` | M10; native session lifecycle/FileUtils/accessibility |
| AC-SRP-039 | `ac039_ac055_navigation_open_direct_spy` (retained Android NAVER primary/fallback plus AC055 iOS Apple Maps supersession) | M21 Android and M20 iOS; actual-device handoff remains NOT RUN |
| AC-SRP-040 | `ac040_only_next_in_order_is_checkable_and_blocked_attempt_is_nonmutating` (mapped/local); `ac040_uncheck_gap_and_external_out_of_order_true_keep_full_remaining_contract` (mapped/local); retained AC027 write-failure preservation | M10; native row focus/reason and external layer refresh |
| AC-SRP-041 | `ac041_generated_site_labels_use_configured_name_and_white_halo` (Point/LineString/Polygon); `ac041_generated_polygon_uses_non_gray_accent_distinct_from_route_states` | M10; automated render observations are generated/headless configuration proxies only; native QField label/halo rendering and collision handling remain NOT RUN |
| AC-SRP-042 | `ac042_touch_equivalent_text_input_uses_real_editable_qml_control_without_recalculation` (body + label/notch window taps, immediate focus/caret, zero recovery calls, post-focus IME edits, trim save, candidate/revision/request invariant) | M11 Android and M12 iOS separately; actual OS soft-keyboard opening remains NOT RUN |
| AC-SRP-043 | `ac043_eight_real_controls_center_labels_on_actual_top_outline` (2 widths × 5 states; common component, live border/image top outline, real error object, independent repository/model rereads) | M13; target-QField screenshots, interaction and screen-reader review remain NOT RUN |
| AC-SRP-044 | `ac044_normal_build_persists_six_family_label_contract_without_artifact_edit` (6 geometries × name-field present/missing; endpoint-connected same-name LineStrings; `mergeLines=false`; independent QGS/GPKG structure and conditional PyQGIS readback) | M14; actual target-QField one-label/halo rendering remains NOT RUN |
| AC-SRP-045 | `ac045_step7_copy_order_masking_and_accessibility` (actual widget/layout/focus-chain/QAccessible observations) | Desktop wizard keyboard/screen-reader review remains user-observed |
| AC-SRP-046 | `ac046_theme_structure_uses_host_palette_and_semantic_roles_only` | M15 is authoritative for pixels, thresholds, non-color cues and passive theme-switch state; NOT RUN |
| AC-SRP-047 | `ac047_header_and_first_control_are_distinct_ordered_structures_only` | M16 is authoritative for painted 8 dp clearance, clipping and tap regions; NOT RUN |
| AC-SRP-048 | `ac048_controller_local_date_save_roundtrip_and_next_success_reset` (3 injected timezone/locale boundaries); retained `ac042_touch_equivalent_text_input_uses_real_editable_qml_control_without_recalculation` | M17 is authoritative for iOS caret/soft keyboard and device presentation; NOT RUN |
| AC-QPB-149 | `ac_qpb149_direct_builder_credential_states_and_secret_boundaries` (five independent builder/credential-store states; parsed QGS and encrypted-store readback) | Exact copy is shared with retained AC045 UI seam; no QML/local-socket route-panel harness |
| AC-QPB-150 | `ac_qpb150_symbol_router_excludes_canonical_site_directly`; `ac_qpb150_generated_qgs_keeps_site_base_symbol_after_rename_and_relocation` (Point/MultiPoint) | Existing AC-QPB-100/101 and AC-SRP-030/041/044 regressions retain fallback and unaffected polygon/line/Type4/data behavior; target rendering is user-observed |

| Approved decision/requirement | Acceptance mapping |
| --- | --- |
| D-SRP-020, D-SRP-026; FR-SRP-021 | AC-SRP-021 dropdown tests; AC-SRP-022 stale target |
| D-SRP-021; FR-SRP-022–024 | AC-SRP-022–024 UI, feedback and guidance tests |
| D-SRP-022; FR-SRP-025 | AC-SRP-025 launcher tests and M05 |
| D-SRP-023, D-SRP-027–028; FR-SRP-026 | AC-SRP-026 schema-2/supersession tests; AC-SRP-029 legacy tests |
| D-SRP-024, D-SRP-029–030; FR-SRP-027 | AC-SRP-027 progression, write-preservation and overlay tests |
| D-SRP-025, D-SRP-030; FR-SRP-028 | AC-SRP-028 metric/bottom-bar/toggle tests |
| D-SRP-031; FR-SRP-029 | AC-SRP-031 four-state/six-selector rendered layout and accessibility tests; M01 |
| D-SRP-032; FR-SRP-032 | AC-SRP-034 selected-only exact guidance/count/row-gap tests; M01 |
| D-SRP-033; FR-SRP-030 | AC-SRP-032 exact marker coordinate, count, pan/replace/preserve/remove/write-boundary tests; M02 |
| D-SRP-034; FR-SRP-031 | AC-SRP-033 exact ordered candidate/preflight sets and refresh/validation sequence; M01 |
| D-SRP-035; FR-SRP-033 | AC-SRP-035 route-level ORS slicing, six-family integration, provider negatives and distinct client failure; M02/M07–M09 |
| D-SRP-036; FR-SRP-034 | AC-SRP-036 candidate identity, zero-request name changes, retry preservation and stale causes; M10 |
| D-SRP-037; FR-SRP-035; D-UI-SRP-001 | AC-SRP-037 seven-control loaded-QML layout/accessibility matrix; M10 |
| D-SRP-038; FR-SRP-036; D-UI-SRP-002–003 | AC-SRP-038 disclosure, provenance, A/B readback, exclusion and failure tests; M10 |
| D-SRP-039; FR-SRP-037; D-UI-SRP-006 | AC-SRP-039 official platform URL/fallback captures; M10 |
| D-SRP-040; FR-SRP-038; D-UI-SRP-004 | AC-SRP-040 enabled-row, blocked mutation, gap/out-of-order and zero-request tests; M10 |
| D-SRP-041; FR-SRP-039; D-UI-SRP-005 | AC-SRP-041 generated renderer/label/halo/inert-data tests; M10 |
| D-SRP-042; FR-SRP-040; D-UI-SRP-007 | AC-SRP-042 unrecovered body/label-overlap touch proxy; M11 Android and M12 iOS keyboard cases |
| D-SRP-043; FR-SRP-041; D-UI-SRP-008 | AC-SRP-043 common-component live outline/error/readback matrix; M13 target-QField review |
| D-SRP-044; FR-SRP-042; D-UI-SRP-009 | AC-SRP-044 connected-line no-merge normal-build QGS/GPKG and conditional PyQGIS readback; M14 target-QField map render |
| D-SRP-045; FR-SRP-043; D-UI-SRP-010 | AC-SRP-045 actual Step 7 layout/focus/QAccessible, four-state build and secret-boundary tests |
| D-SRP-046; FR-SRP-044; D-UI-SRP-011 | AC-SRP-046 static semantic-theme structure; authoritative M15 |
| D-SRP-047; FR-SRP-045; D-UI-SRP-012 | AC-SRP-047 static header/control separation; authoritative M16 |
| D-SRP-048; FR-SRP-046; D-UI-SRP-013 | AC-SRP-048 controller clock/save/load/reset boundary + retained AC042 wiring; authoritative M17 |
| D-101; FR-QPB-144; NFR-QPB-084 | AC-QPB-149 five-state direct builder/QGS/encrypted-store boundary |
| D-102; FR-QPB-145; NFR-QPB-084 | AC-QPB-150 direct symbol routing + generated-QGS rename/relocation; existing fallback/regression coverage reused |
| NFR-SRP-001 | AC-SRP-022/024 320px proxy plus M01 touch/keyboard |
| NFR-SRP-002 | AC-SRP-027 color+check+text proxy plus M04 |
| NFR-SRP-003 | AC-SRP-026–029 zero-request offline/restart/load/move tests plus M02–M04 |
| NFR-SRP-004 | AC-SRP-037–038/040–041 320px/render/accessibility proxies plus M10 native verification |
| NFR-SRP-005 | AC-SRP-042–044 explicitly bounded automatic proxies plus M11–M14 NOT RUN device evidence |
| NFR-SRP-006 | AC-SRP-046/047 structural checks and AC-SRP-048 controller boundary plus M15–M17 NOT RUN authoritative iOS evidence |

## Approved supersession reconciliation (2026-09-17; preserved)

| Retained artifact contradiction | Approved controlling rule | Corrected retained expectation |
| --- | --- | --- |
| AC001 required the provider URL field to be visible whenever the main panel was expanded. | D-SRP-038; FR-SRP-036 | The settings child remains present/enabled but is hidden until `API URL/키 설정` is explicitly expanded. |
| AC010 and AC027 tried to check a later incomplete stop through the user surface and expected the value to persist. | D-SRP-040; FR-SRP-038 | Later-row attempts are nonmutating; ordinary completion fixtures use ordered IDs, and out-of-order state is created by uncheck or external Boolean refresh. |
| AC022/031 expected the superseded long selector labels. | D-SRP-037; FR-SRP-035; D-UI-SRP-001 | Retained tests use `조사지`, `조사 완료 필드`, and `계산 대상` while preserving IDs, values, layout and accessibility evidence. |
| AC031 compared state-dependent error colors with the now-collapsed ORS field's normal colors. | D-SRP-037; FR-SRP-035; D-UI-SRP-001 | Compare shared component typography/insets/padding; require a real validation rectangle and consistent error color when colors differ. AC037 retains the full seven-control state matrix. |
| AC012/025 treated `nmap://navigation` as the Android primary dispatch. | D-SRP-039; FR-SRP-037; D-UI-SRP-006 | Android uses the exact package-bound intent; iOS retains the exact `nmap` scheme; each platform uses its exact documented store fallback. |

This table changes only contradictory expectations. AC-SRP-036–041, raw evidence provenance,
storage readback, zero-request checks, secret boundaries and manual-device limitations are unchanged.

## APPROVED legacy-expectation supersession reconciliation (approval 2026-09-17)

| Retained artifact contradiction | Approved controlling rule | Approved corrected retained expectation |
| --- | --- | --- |
| AC019's `warning_disclosures` evidence parser recognized obsolete fragments such as `읽고 사용할` and `암호화되지 않습니다`, so the approved exact warning produced four false negatives. | D-SRP-045; FR-SRP-043; AC-SRP-045 | Read the actual Step 7 warning and consent widgets, require the complete approved exact copy, and explicitly retain QField automatic use, unencrypted project characters, folder-reader inspection/use and plaintext consent semantics. |
| AC022/024 still expected `저장 경로 이름` for the saved-route dropdown. | D-SRP-043; FR-SRP-041; AC-SRP-043 | Require dropdown label `저장 경로 불러오기`; keep editable text-field label `저장할 경로 이름`. |
| AC031 treated its six controls as a closed final set, required each label box to be wholly inside its control, reused that containment test as `label_clipped`, copied the first global validation rectangle to every control, and a global text matcher classified `저장 경로 불러오기` action-button descendants as separate label rows. | D-SRP-043; FR-SRP-041; AC-SRP-043 | Keep the six AC031 controls as a strict historical subset for accessibility/option collision, stop consuming the defective containment, `label_clipped` and unassociated validation fields, scope separate-row rejection to those six control labels, and retain AC043's exact eight controls with per-control live validation and truncation/clipping evidence as final authority. The adapter defects are reported, not accepted or modified. |

This approved reconciliation does not weaken AC019 secret/key semantics, AC031 accessibility/collision evidence, or
AC043/045 exact-copy and eight-control requirements. It changes no adapter, driver, application,
unit test, specification or approved UI-guidance artifact.

## DRAFT retained-suite supersession reconciliation (2026-09-21)

| Stale retained expectation | Approved controlling rule | DRAFT corrected expectation |
| --- | --- | --- |
| AC008 omitted the newly persisted access radius. | D-SRP-050; AC-SRP-050 | Portable settings include default `max_access_distance_m=2000`. |
| AC013 required only matrix/optimizer/directions requests. | D-SRP-050/052 | Exact successful request kinds also include origin validation and access snap. |
| AC019 required plaintext wording inside the exact consent checkbox label. | D-SRP-045; AC-SRP-045 | Consent remains exactly `위 내용에 동의합니다`; plaintext risk is verified in the separate exact warning widget. |
| AC025/039 retained iOS NAVER/App Store behavior. | D-SRP-056; FR-SRP-053; AC-SRP-055 | iOS uses Apple Maps HTTPS once with no fallback; Android NAVER/Google Play remains required. |
| AC026/029/035 expected a new explicit mixed save to remain schema 2. | D-SRP-053/058; AC-SRP-052/057 | Explicit mixed save is schema 3; schema-1/2 legacy read and settings-only tests remain distinct. |
| AC036 treated every snapshot revision as candidate-stale. | D-SRP-059; AC-SRP-058 | Calculation-input change is stale; successful settings-only route-line toggle preserves the candidate and refreshes its base revision. |

M01–M21 remain user-run **NOT RUN**. No automated proxy is promoted to device evidence.

Verification: design verifier **PASS**; **399 collected**; focused reconciliation
**72 passed, 327 deselected**; full module **378 passed, 21 skipped**. No implementation RED remains.

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

## AC-SRP-031–035 pre-approval verification record (2026-09-16; preserved)

Working directory and branch: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`,
`fix/qfield-project-plugin-loading`. This test-designer changed only the five acceptance artifacts
listed above; no application/unit-test/specification files or Git state were modified by this role.
Commands used the repository interpreter, `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`,
`QT_QPA_PLATFORM=offscreen`, no pytest cache and no real network/device operation.

- Collection: `.\.venv-win\Scripts\python.exe -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py --collect-only -q -p no:cacheprovider`. Result: **278 collected**, exit 0.
- Design verifier: `.\.venv-win\Scripts\python.exe tests/acceptance/survey_route_planner/verify_design.py`. Result: exit 0. It verified 35 AC IDs, M01–M09, route-level `way_points`, absence of segment-level `way_points`, observable open/roundtrip slicing, eleven malformed provider payloads, six floating labels, selected-only count text and all retained fixture/oracle checks. It executed no application behavior.
- Required-mode slice: `$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; $env:QT_QPA_PLATFORM='offscreen'; $env:FIELDBUILD_REQUIRE_SRP_HARNESS='1'; .\.venv-win\Scripts\python.exe -m pytest tests\acceptance\survey_route_planner\test_survey_route_planner.py -q -p no:cacheprovider --tb=line --basetemp 'C:\Users\Public\Documents\ESTsoft\CreatorTemp\FieldBuildKit-srp-draft-01a09d30' -k 'ac031 or ac032 or ac033 or ac034 or ac035'`. Result: **65 failed, 213 deselected**, exit 1, 84.54 s. Failures were 8 missing `floating_selectors` observations, 18 missing scoped-guidance/row observations, 10 missing candidate/preflight observations, 9 unsupported `map_start_marker` cases, and 20 ORS/provider/client/six-family cases. The current implementation rejects the corrected valid route-level-`way_points` ORS fixture before leg slicing and therefore cannot yet seed the last-good route for the negative cases. These are expected implementation/harness failures; no expectation was weakened.
- An earlier identical required-mode attempt without explicit `--basetemp` reached the same red test stream but pytest session cleanup hit `PermissionError: [WinError 5]` on its shared `pytest-current` path. The controlled-basetemp rerun above is the authoritative result.
- Acceptance-only `git diff --check` over the five edited files: exit 0; Git emitted informational LF/CRLF warnings only.

M01–M09 remain **NOT RUN**. In particular, M07 Point, M08 LineString and M09 Polygon have no actual
QField/live-ORS verdict. The approved requirements and this approved test-design evidence correction do not
establish product, native QField or overall stakeholder acceptance PASS.

## Evidence-correction draft verification record (2026-09-16)

Working directory and branch: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`,
`fix/qfield-project-plugin-loading`. This test-designer changed only the five acceptance artifacts
listed above; no application, unit-test, specification or Git state was modified by this role.
Commands used the repository interpreter, `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, no pytest
cache, and an explicit disposable base temp for required-mode checks.

- Collection: `.\.venv-win\Scripts\python.exe -m pytest tests\acceptance\survey_route_planner\test_survey_route_planner.py --collect-only -q -p no:cacheprovider`. Result: **278 collected**, exit 0.
- Design verifier: `.\.venv-win\Scripts\python.exe tests\acceptance\survey_route_planner\verify_design.py`. Result: exit 0. It checked the 35 AC IDs plus the corrected AC001/017/022/026/027/031–035 fixture and evidence-provenance tokens; it executes no application behavior.
- Required-mode AC022/024 fixture matrix: **6 passed, 272 deselected**, exit 0; explicit `all` scope removes the prior selected-scope contradiction for all widths/start modes. Separate bounded evidence probes covering AC001, AC017, AC026, AC027 and AC031–035 produced **16 expected failures**, exit 1. Failures were missing loaded-QML control/object/style evidence, missing nonempty invalid-CRS baseline, missing rendered-row/model-preflight/canvas/write/generated-artifact/fault provenance, and the route-progression driver failing while consuming the supplied raw intermediate-vertex directions response. Expectations were not weakened.
- Acceptance-only `git diff --check` over the five edited files: exit 0; Git emitted informational LF/CRLF warnings only.

M01–M09 remain **NOT RUN**. The bounded run is evidence that the corrected acceptance contract is
currently red; it is not product, native-QField, device or live-provider acceptance evidence.

## Supersession-correction approval record (2026-09-17)

Status: **APPROVED TEST DESIGN (approval 2026-09-17)**. Working directory and branch:
`D:\오민우 Project\vibe_coding\fieldbuild_standalone`, `fix/qfield-project-plugin-loading`.
This test-designer changed only the five survey-route acceptance artifacts. No application code,
unit test, approved specification/UI-guidance file or Git state was modified. All runs used the
repository interpreter, UTF-8/no-bytecode/offscreen settings, required harness mode, no pytest cache
and distinct disposable base-temp directories.

- Design verifier: exit 0. It checked 41 AC IDs, the retained evidence-provenance guards and the
  exact correction oracles: hidden initial settings child, ordered AC010 fixture, shortened labels,
  Android intent/iOS scheme and blocked-later/uncheck-created progression.
- Corrected old-conflict selector (`ac001`, `ac010_completion`, `ac012`, `ac031`, `ac022/ac024`,
  `ac025` and corrected `ac027`): **27 passed, 285 deselected**, exit 0, 40.60 s.
- AC-SRP-036–041 selector: **33 passed, 279 deselected**, exit 0, 42.65 s. No AC036–041 assertion
  was relaxed to obtain this result.
- Full required-mode module: **302 passed, 10 skipped**, exit 0, 435.47 s. The skips are exactly
  M01–M10 with their explicit “No device PASS implied” reasons.

Against the supplied raw implementation result (**278 passed, 24 failed, 10 skipped**), every one
of the 24 failures maps to the approved supersessions in the table above. The corrected full run has
no remaining automated implementation failure. Native QField, device rendering/accessibility,
live provider behavior and actual Android/iOS Naver handoff remain unperformed and cannot be marked
PASS from this run.

## AC-SRP-042–045 approval record (2026-09-17)

Status: **APPROVED TEST DESIGN (approval 2026-09-17)**. Collection found **343 cases**. The design
verifier passed all 45 AC IDs, exact-copy/oracle and evidence-boundary guards. The focused required-mode
run selected 27 new automated cases and produced **27 failed, 316 deselected** in 37.51 s: the current
acceptance driver reports the four new operations as unsupported (1 AC042, 10 AC043, 12 AC044 and
4 AC045 cases). This is an implementation/harness gap, not evidence that native keyboard/rendering
was exercised. The manual selector produced **14 skipped, 329 deselected**; M11–M14 remain NOT RUN.
Acceptance-only `git diff --check` passed with informational line-ending warnings only.

The first probe found and corrected two test-artifact defects: incomplete AC044 fixture geometry keys
and secret-bearing default pytest IDs for AC045. The authoritative rerun uses complete geometry rows
and redacted state-only IDs; no application finding is assigned to either corrected artifact issue.

### Approved evidence correction (2026-09-17)

Status: **APPROVED TEST DESIGN (approval 2026-09-17)**. AC042 now rejects any focus recovery and covers the label/notch
hit region; AC043 requires live outline/error geometry plus independent before/after readbacks; AC044
requires connected same-name LineStrings, `mergeLines=false`, and honest PyQGIS availability; AC045
requires actual layout, focus-chain and QAccessible observations. M01–M14 remain NOT RUN.

Verification: design verifier passed; collection found **344 cases**. The corrected focused selector
produced **28 failed, 316 deselected**: AC042 2 missing touch-target observations (with recovery still
present in the driver), AC043 10 missing common-component observations, AC044 12 `mergeLines=1`
configuration failures, and AC045 4 missing actual widget-tree observations. The manual selector was
**14 skipped, 330 deselected**; all M01–M14 remain NOT RUN. Acceptance-only `git diff --check` passed
with informational line-ending warnings.

## APPROVED legacy-expectation reconciliation verification (2026-09-17)

Status: **APPROVED TEST DESIGN — supersession reconciliation (approval 2026-09-17)**. Supplied full results changed from
**315 passed, 15 failed, 14 skipped** to **330 passed, 14 skipped** after reconciling only the retained
expectations mapped in the approved table above. The exact affected selector changed from **15 failed,
329 deselected** to **15 passed, 329 deselected**. Approved AC042–045 remained green at **28 passed,
316 deselected**. Collection remained **344 cases**; the exact manual selector remained **14 skipped,
330 deselected**, so M01–M14 are still NOT RUN.

The design verifier and acceptance-only `git diff --check` passed. The unchanged `panel_layout`
adapter's containment-derived clipping and global validation-rectangle fields are recorded defects,
not accepted evidence; AC043's live per-control observations retain final authority. No application,
adapter/driver, unit-test, specification or UI-guidance change is required. This reconciliation is
**APPROVED TEST DESIGN (approval 2026-09-17)**.

## DRAFT AC-SRP-049–058 traceability redesign (2026-09-21)

> DRAFT correction (2026-09-21; user approval required): AC-SRP-050/054 add the executable
> provider-valid origin 1x1 matrix regression. This is Category A coverage of existing
> D-SRP-050/052 and FR-SRP-048/052; it changes no product requirement.

Harness contract: survey_route_planner/HARNESS_CONTRACT.md, section
“DRAFT AC-SRP-049–058 direct-observation redesign”.

| Criterion | Direct automated evidence | Remaining manual evidence |
| --- | --- | --- |
| AC-SRP-049 | ac049 HTTP failure and unsafe-body tests over actual localhost traffic | M18 live-provider wording/status |
| AC-SRP-050 | ac050 explicit origin 1x1 request/response, validation-only resolved-coordinate and saved-start immutability tests; single-batch/radius and null/batch/origin-response-stop tests; actual HTTP bodies and source/result comparison | M18 live rural snap/source inspection |
| AC-SRP-051 | ac051 mapped/exact-zero/unmapped and malformed-walking tests | M18 live mapped/no-path behavior |
| AC-SRP-052 | ac052/ac057 production-save roundtrip; real slot files, separate-process reopen and moved folder | M03 target-QField offline/recovery |
| AC-SRP-053 | ac053 QML runtime object-tree/Repeater/QAccessible test plus raw provider/file callback slices and before/after counters for each exercised passive product action; canned empty boundary results fail | M19 pixels, contrast, interaction and screen reader |
| AC-SRP-054 | ac050/ac054 semantic origin-stage and actual HTTP sequence/privacy tests plus file-wide secret scan | M18 live consent/provider boundary |
| AC-SRP-055 | ac055 navigation.open direct-spy and coordinate tests | M20 iOS and M21 Android handoff |
| AC-SRP-056 | ac056 three production-saved active/inactive schema-3 routes cover all three allowed pairs; active+inactive corruption covers required missing/blank fields, both identity mismatches, unknown values and all six disallowed cross-pairs with raw corrupt/last-good bytes and request/write counters | M03 target-QField recovery |
| AC-SRP-057 | ac057 variant-corruption and schema-boundary tests, exact top-level-schema-3 `route_schema: 1` plus schema-2 `legs` contradiction, and AC052 selected replacement/legacy preservation | M03 list/load compatibility |
| AC-SRP-058 | ac058 restart/move and write-failure tests plus passive QML assertion | M03 persistence and M19 visual behavior |

| Requirement group | Criteria |
| --- | --- |
| D-SRP-049 / FR-SRP-047 / NFR-SRP-007 | AC049, AC054 |
| D-SRP-050–052 / FR-SRP-048–049,052 | AC050–051, AC054 |
| D-SRP-053–055 / FR-SRP-050–052 / NFR-SRP-008–009 | AC052–054 |
| D-SRP-056 / FR-SRP-053 | AC055 |
| D-SRP-057 / FR-SRP-054 | AC056 |
| D-SRP-058–059 / FR-SRP-055–056 | AC057–058 |

M01–M21 remain **NOT RUN**. Automated success never substitutes for native QField, live ORS,
Apple Maps or NAVER device verification.

Correction verification: design verifier **PASS**; **403 collected**; focused AC049–058
**47 passed, 356 deselected**. The DRAFT semantic-selector correction distinguishes the duplicate
origin pair with explicit `sources:[0]`/`destinations:[1]` from the actual start/access vehicle
matrix without those indexes; no location-count stage heuristic remains. The full acceptance file
is **382 passed, 21 skipped**. M01–M21 remain **NOT RUN**; user approval is required.

## APPROVED AC-SRP-059 baseline and reviewer-correction traceability (approved 2026-09-22)

Baseline status: **APPROVED TEST DESIGN (approval 2026-09-21).** Correction status:
**APPROVED TEST DESIGN (approval 2026-09-22).** The approved history and the separately tracked
AC-SRP-049–058 status remain preserved.

| Criterion | Direct automated evidence | Remaining manual evidence |
| --- | --- | --- |
| AC-SRP-059 valid provider contract | `ac059_snapped_provider_geometry_is_mapped_without_connector_or_gap_metric` over actual localhost traffic and production backend return | M18 live configured ORS snapped response |
| AC-SRP-059 persistence/reader | `ac059_schema3_active_inactive_restart_offline_move_exact_roundtrip` over two production saves, real schema-3 slot files, separate-process reopen and moved folder | M03 target-QField restart/offline/move |
| AC-SRP-059 malformed response atomicity | `ac059_malformed_walking_contract_stops_before_vehicle_write_and_preserves_last_good` (15 raw fixture mutations, including an object-shaped `features` array impostor) over production controller/repository snapshots and actual request/write counters | M18 live malformed-provider wording is not required; provider service remains synthetic |
| AC-SRP-059 map/UI/accessibility | `test_ac059_qml_observes_current_requested_markers_provider_line_and_one_gap_detail` over enumerated loaded-QML requested markers, actual provider features/lines, visit model, walking totals and the single live details disclosure; the test derives connector/gap absence from runtime enumerations | M19 target-QField pixels, map alignment and screen-reader speech |

| Requirement group | Criterion |
| --- | --- |
| D-SRP-060 / FR-SRP-057 | AC-SRP-059 |

The valid fixture independently proves both endpoint gaps exceed 1 m and provider distance is shorter than
the requested-coordinate geodesic. The persistence test retains existing schema 3, `mapped`, and
`ors-foot-hiking`; the negative matrix retains last-good state and stops before vehicle routing/write. No
test accepts a non-Array `features` member, connector, gap metric/time, fallback, coordinate movement, new
provenance field or schema bump. Harness-provided copied coordinates or constant zero absence counts are not evidence.
M01–M21 remain **NOT RUN**.

Verification: design verifier **PASS**; **420 collected**; focused AC059 **14 passed, 3 failed,
403 deselected**. The three intended RED results are valid snapped-provider rejection, the dependent
active/inactive save/restart/offline/move path, and missing loaded-QML snapped-marker/provider-line/disclosure
observations. Existing AC056 corruption coverage remains the authority for all other schema-3 visit validation;
AC059 changes only endpoint-equality and requested-geodesic lower-bound rejection. Acceptance-only
`git diff --check` passed. M01–M21 remain **NOT RUN**.

The verification above belongs to the approved baseline. The reviewer correction's pre-approval
verification record remains preserved below; it does not relabel that historical run.

Correction verification: **421 collected**; design verifier **intended RED** at the hard-coded-zero
driver guard; authoritative focused AC059 **16 passed, 2 failed, 403 deselected**. The two intended
failures are acceptance of the object-shaped `features` impostor and absence of direct runtime
`access_marker_observations`. Acceptance-only `git diff --check` passed. An initial sandboxed run's
18 localhost-bind failures are environment noise, not product evidence. M01–M21 remain **NOT RUN**.

## APPROVED AC-SRP-061–062 traceability (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22)**. Approved requirement authority is `d4f8266`.

| Requirement / criterion | Direct automated evidence | Explicit boundary |
| --- | --- | --- |
| D-SRP-062; FR-SRP-059; AC-SRP-061 — missing optional diagnostic | `test_ac061_missing_snapped_distance_independently_allows_calculation_and_save` covers origin source, origin destination and both vehicle source rows over actual localhost response payloads, production controller/save and request capture; saved schema-3 route contains no synthesized field | No live ORS call |
| D-SRP-062; FR-SRP-059; AC-SRP-061 — present invalid and atomicity | `test_ac061_present_invalid_snapped_distance_fails_at_its_stage_and_preserves_state` crosses four locations with string/null/JSON non-finite/negative and proves exact request cutoff, zero write and last-good snapshot/candidate preservation | Provider wording beyond stage/actionability is not prescribed |
| D-SRP-062; FR-SRP-059; AC-SRP-061 — vehicle maximum and retained validation | `test_ac061_vehicle_snapped_distance_honors_inclusive_configured_maximum` covers 1000/1000.01 m; `test_ac061_optional_diagnostic_does_not_relax_matrix_structure_or_metrics` covers origin/vehicle object-cardinality, location and metric defects | Existing max setting is used; no inferred origin threshold |
| D-SRP-063; FR-SRP-060; NFR-SRP-010; AC-SRP-062 — canonical macOS/Windows store and sibling isolation | `test_ac062_canonical_platform_store_shares_three_keys_and_ignores_siblings` uses simulated platform roots below `tmp_path`, real encryption/readback for VWorld/Pl@ntNet/route fields, and byte-for-byte sibling snapshots across absent/empty/populated combinations | No real user app-data is opened |
| D-SRP-063; NFR-SRP-010; AC-SRP-062 — diagnostic override | `test_ac062_diagnostic_override_uses_exactly_one_disposable_store` proves the exact override path, one final file, encrypted route readback and sibling immutability | Override is test/diagnostic only, not a production migration source |
| FR-SRP-060; NFR-SRP-010; AC-SRP-062 — remember off, blank and failure | `test_ac062_nonretained_branches_build_without_store_or_plaintext_fallback` drives real builds for all three branches, including a write-boundary fault; it proves publication, session behavior, absent store/project copy/plaintext and redacted result | Synthetic fault only; no real disk-full/user store |
| FR-SRP-060; NFR-SRP-010; AC-SRP-062 — desktop-only and non-leakage | `test_ac062_remembered_route_key_is_not_copied_or_exposed_by_builder_ui` drives the real Step 7 Qt/build path and checks password echo/accessibility, encrypted readback, generated artifacts, QField unavailability and normal UI/log/report/runtime surfaces | Test-only evidence fields may expose the disposable path, never the key; native screen capture is not claimed |

The design verifier guards all fixture locations, the valid-JSON `1e309` non-finite case, state/write
assertions, both sibling names, shared three-key readback, non-retained project scans and UI/log/report
redaction assertions. M01–M21 remain **NOT RUN** and are not required to establish these desktop/localhost
criteria.

Verification: design verifier **PASS**; **475 collected**; authoritative focused AC-SRP-061/062 result
**22 passed, 17 failed, 436 deselected**. AC-SRP-062 is green in all nine cases. AC-SRP-061 is intentionally
RED for four missing-diagnostic success cases and thirteen vehicle-stage diagnostics; current vehicle
provider-response failures preserve state and stop correctly but do not retain the required `matrix` stage.
An initial restricted run's 31 loopback-bind failures are environment noise, not product evidence.

## APPROVED unmapped-save QML click conformance traceability (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22)**.

| Approved authority | Direct automated evidence | Remaining device evidence |
| --- | --- | --- |
| FR-SRP-034; AC-SRP-036 | `test_ac036_ac051_ac052_unmapped_generated_qml_click_saves_schema3_and_reports_path` drives the generated checkbox and save button by pointer event; `test_ac036_unmapped_generated_qml_save_failure_keeps_candidate_and_shows_error` proves candidate/error retention through the same save control | Target iPhone/QField tap result reported by user; retest after implementation |
| AC-SRP-051 | Success test observes save disabled before and enabled after the real generated acknowledgement click; no direct controller acknowledgement is accepted | Native checkbox/touch semantics remain user-run |
| FR-SRP-051; AC-SRP-052 | Success test independently reads schema-3 slot storage, reopens the identical document/route, and observes saved-list/load availability | Target-QField restart/folder-move remains M03 |
| D-SRP-021; FR-SRP-023 | Success test requires the current viewport to contain feedback with the final name and actual project-relative slot path; failure test forbids success text | Native visual placement remains user-run |

Collection: **477 tests**. Focused result: **1 passed, 1 failed, 475 deselected**. The intended RED is the
successful click's `feedback_in_viewport == false`: schema-3 commit/readback, candidate clearing and exact
name/path content all succeed, but the committed success is outside the current save-control viewport. The
injected write-failure case passes with exact candidate retention and a visible production error.

### APPROVED unmapped-save observation-timing correction traceability (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22)**. The approved authority and expectations in the table
above remain unchanged.

| Approved authority preserved | Approved evidence correction | Guard |
| --- | --- | --- |
| AC-SRP-051 checked/enabled transition | Capture `unmappedAcknowledgement.checked` immediately after its real pointer click, before save/reopen; return the captured Boolean rather than querying the old control after `open_panel()` replaces the panel | Design verifier enforces click → capture → save → reopen ordering and retains the success assertion `acknowledgement_checked is True` |
| FR-SRP-034/051; AC-SRP-036/052 save and persistence behavior | No change to the real save-button click, schema-3 commit/readback, candidate clearing, list/load/reopen, exact visible name/path, or failure-retention/error observations | Existing success/failure assertions remain required |

Preserved raw implementation history: the first authoritative rerun was **1 failed, 1 passed** at the stale
checkbox observation, while the immediate unchanged rerun was **2 passed**. The corrected harness therefore
required repeated independent focused invocations before approval; the three stable runs below satisfied that
condition, and the user approved the correction on 2026-09-22.

Approved corrected-harness verification: design verifier **PASS**; **477 collected**; three separate
localhost-enabled focused invocations each returned **2 passed, 475 deselected** (2.58 s, 2.20 s and 2.02 s).
The prior restricted-sandbox invocation returned **2 failed, 475 deselected** only because both disposable
localhost binds were denied with `PermissionError`; it is not conformance evidence. M01–M21 remain **NOT RUN**.

## APPROVED AC-SRP-063–065 traceability (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22).** Authority is approved checkpoint `d31bf65`.

| Approved authority | Direct automated evidence | Explicit boundary |
| --- | --- | --- |
| D-SRP-064; FR-SRP-061; AC-SRP-063 — exact notice, no acknowledgement, no fallback save gate | `test_ac051_ac063_unmapped_save_needs_no_acknowledgement_and_keeps_null_totals`, `test_ac060_ac063_one_point_zero_route_saves_without_unmapped_acknowledgement`, `test_ac063_mixed_result_has_one_notice_no_ack_and_default_collapsed_details` | Generated Qt/QML and production-controller evidence; native touch remains M22 |
| D-SRP-064; FR-SRP-061; NFR-SRP-011; AC-SRP-063 — collapsed exact details, raw diagnostics inside, one endpoint-gap line, disclosure purity | Mixed-result test at 320/light and 1024/dark compares candidate/payload/request/write/save state around expand-collapse | QAccessible/layout proxy, not native speech/device rendering |
| D-SRP-065; FR-SRP-061; AC-SRP-063 — disabled reasons and nonfallback absence | Mixed test checks exact candidate-none and mapping-adjacent reasons; `test_ac063_nonfallback_results_have_no_fallback_notice_or_save_gate` covers all-mapped/exact-zero-only | Existing validation supplies the mapping suffix |
| D-SRP-065; FR-SRP-062; NFR-SRP-011; AC-SRP-064 — every save outcome visible and announced once | `test_ac064_ac066_every_save_outcome_is_visible_once_and_preserves_required_state` crosses seven outcomes at both viewport/theme pairs | One visible QAccessible `StatusBar` is the announcement proxy; native speech remains M22 |
| FR-SRP-062; AC-SRP-064 — success/failure state, atomicity and no retry | Same test requires success-only clear/new active; failures preserve candidate plus independent last-good data/revision/bytes and focus/name/disclosure | Synthetic false/readback/exception; no real disk-full |
| D-SRP-066; FR-SRP-063; AC-SRP-065 — fresh bundle and immutable existing output | `test_ac065_fresh_build_bundles_current_runtime_and_never_updates_existing_project` compares runtime byte trees and exact completion disclosure | Desktop build only; no implicit update claim |
| D-SRP-067; FR-SRP-064; AC-SRP-066 — immediate success disable and focus | Same seven-outcome test observes synchronous candidate clear/save disable/exact reason, simulated platform focus clear, no focus-recovery API, no transfer, and preserved name/disclosure | Qt focus behavior is a proxy; native touch remains M22 |
| NFR-SRP-012; AC-SRP-066 — exact semantic order and layout | Same test compares live coordinate, QAccessible and Tab orders at both viewport/theme pairs and rejects overlap/clipping/overflow | Native screen-reader speech/order remains M22 |
| AC-SRP-053/059 current presentation under D-SRP-067 | AC059 current-presentation test plus AC063 mixed-result test require runtime markers/geometry/provenance/totals/fallback accessibility and exactly one details endpoint-gap line | M19/M22 device pixels and speech remain `미검증` |
| AC-SRP-063–066 target-device evidence | `test_ac063_ac064_ac065_ac066_target_qfield_handoff_is_user_run_and_unverified` is explicitly skipped | M22 remains `미검증` until user transfer/open |

Historical acknowledgement-click rows above remain as historical evidence only; D-SRP-064 explicitly
supersedes their current acknowledgement/gate expectation and the old click driver is removed.

## APPROVED AC-SRP-064/066 Qt observation-boundary correction traceability (2026-09-23)

Status: **APPROVED TEST DESIGN (approval 2026-09-23).** This corrects acceptance evidence only; approved
specification checkpoint `cb8f2da` and all product behavior remain unchanged.

| Approved authority preserved | Approved evidence correction | Guard |
| --- | --- | --- |
| AC-SRP-064 status starts outside and ends fully visible | Stabilize live rendered geometry, explicitly place `saveStatus` wholly outside the viewport, assert `outside: true`, then require post-attempt `fully_visible: true` | Design verifier requires the bounded render-settle and explicit outside-position helper; no timed sleep |
| D-SRP-067; FR-SRP-064; AC-SRP-066 no application focus transfer/recovery | Permit only `None` or an unnamed non-focusable Qt scope after platform clear; reject every named target, focusable-control ancestor, and save-button focus-recovery API | Detailed focus observations retain object name, Qt class, accessible role and focusable-control identity |
| AC-SRP-063–066 remaining state, order, endpoint and device boundaries | Existing success-disable, exact disabled reason, route-name/disclosure preservation, semantic order, one endpoint-gap detail, announcement, atomicity and M22 assertions are unchanged | Existing verifier/test assertions remain required |

## APPROVED AC-SRP-066 layout restoration / AC-SRP-067 traceability (2026-09-23)

Status: **APPROVED — explicitly approved by the stakeholder on 2026-09-23.**

| Approved authority | Direct automated evidence | Boundary / current result |
| --- | --- | --- |
| AC-SRP-066 result/save block after calculate controls; existing internal order unchanged | `test_ac064_ac066_every_save_outcome_is_visible_once_and_preserves_required_state` now includes actual live calculate controls in raw geometry/accessibility ordering at both viewport/theme pairs | Intentionally RED: committed QML places `basic_result` before `calculation_controls`; M22 remains `미검증` |
| D-SRP-068; AC-SRP-067 stage/status/actionability/accessibility | `test_ac067_origin_validation_http_403_is_actionable_redacted_and_atomic` checks matching live status/QAccessible name, exact `origin-validation`, HTTP 403 and neutral key/permission action | Intentionally RED only at missing key/permission action text |
| D-SRP-049; D-SRP-068; AC-SRP-067 redaction and safe-detail allowlist | Same parametrized test crosses unsafe text and safe JSON provider-message fixtures; normal UI/log/storage surfaces exclude secret, `Authorization`, query and unsafe raw response | Synthetic localhost only; no live provider diagnosis |
| AC-SRP-067 cutoff/atomicity | Same test requires exactly one origin request, zero downstream/retry/write, identical candidate/document/revision and byte-identical route slots | Direct disposable storage snapshots; no user project touched |
