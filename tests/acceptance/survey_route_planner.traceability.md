# Survey Route Planner — APPROVED legacy-expectation supersession reconciliation

> **APPROVED TEST DESIGN (approval 2026-09-18).** AC-SRP-049–055 and mappings for D-SRP-049–056,
> FR-SRP-047–053 and NFR-SRP-007–009 are additive to the preserved approved history.
> M18–M21 are NOT RUN and cannot be satisfied by automated fixtures.

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
| AC-SRP-025 | `ac025_exact_encoded_android_intent_and_honest_qt_true` (2 caller IDs), `ac025_mobile_fallback_and_all_refused` (retained Android intent/store only under D-SRP-056), `ac025_non_mobile_has_actionable_error_without_install_dispatch`, retained `ac012_road_and_naver` | Android remains M05/M21; superseded iOS provider/fallback is covered by AC-SRP-055/M20 |
| AC-SRP-026 | `ac011_ac026_remaining_recalculation_is_superseded`, `ac026_ac035_schema2_complete_immutable_legs_roundtrip` (open/roundtrip), `ac026_invalid_schema2_leg_preserves_existing_route` (7 raw route-level/top-level fault documents with exact provenance and no segment-level way_points), `ac026_provider_total_tolerance` (4 boundaries) | M02/M03; native QField storage roundtrip and UI control absence |
| AC-SRP-027 | `ac010_ac011_ac027_all_complete_uses_saved_full_route`, `ac027_ordered_completion_then_uncheck_creates_out_of_order_gap_and_roundtrip_return` (blocked later-row attempt, then ordered completion and uncheck-created gap; mapped/local; raw intermediate-vertex directions and committed-route provenance), `ac027_completion_overlay_is_blue_accessible_nonpersistent_and_rederived` (3 geometries × mapped/local), `ac027_mapped_write_failure_preserves_overlay_metrics_and_source`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M04; actual map rendering, source writes and recovery |
| AC-SRP-028 | `ac028_metric_formatting_and_bottom_bar` (4 ceil-minute edges), `ac028_route_line_toggle_scope_persistence_move_and_zero_api`, `ac027_ac028_progression_survives_restart_recovery_offline_move` | M03/M04; native device-local setting and overlay visibility |
| AC-SRP-029 | `ac029_legacy_schema1_load_is_offline_nonmutating_and_unavailable`, `ac029_explicit_full_recalculation_is_only_schema2_upgrade`, `ac029_future_schema_is_preserved_and_rejected` | M03/M06; real legacy bytes under QField storage API |
| AC-SRP-030 | `ac018_ac030_regression_portability`, `ac013_ac030_no_network_or_secrets` plus AC002/003/008/009/013–019/021–029 rows above | M01–M06; full native regression and redacted device evidence |
| AC-SRP-031 | `ac031_six_selectors_use_ors_floating_labels_without_collision` (historical six-control subset, 2 widths × empty/value/focus/error; D-SRP-037 shortened labels; distinct loaded-QML object IDs, geometry, style and accessibility; separate-row check scoped to these control labels) | AC043 is final authority for all eight controls; M01 covers native touch/keyboard focus, screen-reader name and device clipping |
| AC-SRP-032 | `ac032_map_start_marker_is_exact_fixed_and_replaced_not_duplicated`; `ac032_map_start_marker_survives_panel_and_calculation_events` (3); `ac032_map_start_marker_removed_at_lifecycle_end` (4); `ac032_map_start_transform_failure_preserves_previous_marker_and_start` (full canvas enumeration and actual provider/storage write capture) | M02; actual QField map item, project-close lifecycle and visual distinction |
| AC-SRP-033 | `ac033_target_candidates_match_preflight_before_required_validation` (3 scopes × 0/1/3); `ac033_candidate_refresh_preserves_valid_id_and_clears_stale_after_changes` (separate model/preflight capture IDs and submitted order) | M01; actual QField selection/schema/completion events |
| AC-SRP-034 | `ac034_selection_guidance_is_selected_only_and_leaves_no_gap` (2 widths × 3 scopes × 0/1/3; visible row coordinates and hidden-item layout absence) | M01; native rendered placement and device accessibility |
| AC-SRP-035 | `ac026_ac035_schema2_complete_immutable_legs_roundtrip` (open/roundtrip documented ORS slices); `ac035_provider_contract_defects_are_actionable_and_preserve_last_good` (11 raw defects); `ac035_valid_provider_response_forced_client_failure_is_distinct_and_preserves_last_good`; `ac035_six_geometry_families_accept_real_ors_contract_from_approved_representative` (6 real materialized source→generated GPKG/QGS paths) | M02 plus M07 Point, M08 LineString, M09 Polygon; actual QField/live ORS results remain unperformed |
| AC-SRP-036 | `ac036_name_entry_and_changes_save_existing_candidate_without_recalculation`; `ac036_recoverable_save_failure_preserves_candidate_for_corrected_retry` (3); `ac036_only_real_input_or_revision_change_blocks_stale_candidate` (2) | M10; native QField focus/input and file-failure retry |
| AC-SRP-037 | `ac037_seven_controls_share_rendered_outlined_floating_label_contract` (2 widths × 5 states; raw loaded-QML rectangles/style/accessibility) | M10; native touch/keyboard/screen reader and clipping |
| AC-SRP-038 | `ac038_api_settings_initially_collapsed_and_toggle_is_passive`; `ac038_key_provenance_and_session_lifetime_are_observed_from_generated_project` (2); `ac038_settings_save_reports_actual_slot_and_excludes_key_and_objective`; `ac038_failed_settings_save_preserves_last_good_and_session_key` | M10; native session lifecycle/FileUtils/accessibility |
| AC-SRP-039 | `ac039_platform_specific_official_primary_dispatch` (Android/iOS); `ac039_official_install_fallback_once_and_no_inferred_web_url` (Android/iOS) | M10; actual-device app/store handoff remains NOT RUN |
| AC-SRP-040 | `ac040_only_next_in_order_is_checkable_and_blocked_attempt_is_nonmutating` (mapped/local); `ac040_uncheck_gap_and_external_out_of_order_true_keep_full_remaining_contract` (mapped/local); retained AC027 write-failure preservation | M10; native row focus/reason and external layer refresh |
| AC-SRP-041 | `ac041_generated_site_labels_use_configured_name_and_white_halo` (Point/LineString/Polygon); `ac041_generated_polygon_uses_non_gray_accent_distinct_from_route_states` | M10; automated render observations are generated/headless configuration proxies only; native QField label/halo rendering and collision handling remain NOT RUN |
| AC-SRP-042 | `ac042_touch_equivalent_text_input_uses_real_editable_qml_control_without_recalculation` (body + label/notch window taps, immediate focus/caret, zero recovery calls, post-focus IME edits, trim save, candidate/revision/request invariant) | M11 Android and M12 iOS separately; actual OS soft-keyboard opening remains NOT RUN |
| AC-SRP-043 | `ac043_eight_real_controls_center_labels_on_actual_top_outline` (2 widths × 5 states; common component, live border/image top outline, real error object, independent repository/model rereads) | M13; target-QField screenshots, interaction and screen-reader review remain NOT RUN |
| AC-SRP-044 | `ac044_normal_build_persists_six_family_label_contract_without_artifact_edit` (6 geometries × name-field present/missing; endpoint-connected same-name LineStrings; `mergeLines=false`; independent QGS/GPKG structure and conditional PyQGIS readback) | M14; actual target-QField one-label/halo rendering remains NOT RUN |
| AC-SRP-045 | `ac045_step7_copy_order_masking_and_accessibility` (actual widget/layout/focus-chain/QAccessible observations) | Desktop wizard keyboard/screen-reader review remains user-observed |
| AC-SRP-046 | `ac046_theme_structure_uses_host_palette_and_semantic_roles_only` | M15 is authoritative for pixels, thresholds, non-color cues and passive theme-switch state; NOT RUN |
| AC-SRP-047 | `ac047_header_and_first_control_are_distinct_ordered_structures_only` | M16 is authoritative for painted 8 dp clearance, clipping and tap regions; NOT RUN |
| AC-SRP-048 | `ac048_controller_local_date_save_roundtrip_and_next_success_reset` (3 injected timezone/locale boundaries); retained `ac042_touch_equivalent_text_input_uses_real_editable_qml_control_without_recalculation` | M17 is authoritative for iOS caret/soft keyboard and device presentation; NOT RUN |
| AC-SRP-049 | `ac049_provider_http_failure_preserves_stage_status_and_safe_json_detail` (5 stages); `ac049_unsafe_or_unusable_provider_body_has_no_detail` (9 unsafe/unusable bodies); `ac049_plain_text_is_bounded_and_success_body_never_enters_error_ui`; `ac049_404_meaning_comes_only_from_provider_content` (explicit endpoint/no-result/generic) | M18; live provider response behavior remains NOT RUN |
| AC-SRP-050 | `ac050_single_ordered_access_snap_uses_originals_and_exact_radius` (0.35/2/5 km); `ac050_access_boundary_failures_stop_pipeline_and_preserve_last_good` (null/batch/radius/origin) | M18; live ORS snap/routing coverage remains NOT RUN |
| AC-SRP-051 | `ac051_mapped_zero_and_open_last_visits_are_out_and_back`; `ac051_explicit_no_path_requires_ack_and_keeps_duration_unknown`; `ac051_transient_or_invalid_walking_failure_is_never_downgraded` (4) | M18; live foot-hiking/no-path classification remains NOT RUN |
| AC-SRP-052 | `ac052_schema3_exact_roundtrip_recovery_move_and_completion_are_offline` (mapped/fallback); `ac052_legacy_load_and_future_rejection_preserve_bytes` (schema 1/2 plus future) | M18; target QField native file/recovery behavior remains NOT RUN |
| AC-SRP-053 | `ac053_mixed_route_visual_accessibility_proxy_is_distinct_and_passive` (2 widths × 2 themes) | M19 authoritative native render/grayscale/screen-reader gate; NOT RUN |
| AC-SRP-054 | `ac054_exact_stage_sequence_privacy_and_no_incidental_writes`; `ac054_each_stage_failure_stops_all_later_requests_and_writes` (7 stages); `ac054_status_actions_remain_redacted_and_nonretrying` (401/403/404/429/5xx/timeout/radius); AC049/050/051 fail-fast matrices | M18; redacted live-provider confirmation remains NOT RUN |
| AC-SRP-055 | `ac055_ios_uses_exact_apple_maps_once_without_any_fallback` (true/false/exception); `ac055_navigation_coordinates_are_canonical_and_android_contract_is_unchanged` (4 boundaries); `ac055_invalid_navigation_coordinate_never_dispatches_or_mutates` (7 invalid inputs); retained Android-only AC039 tests | M20 iOS and M21 Android handoff; NOT RUN |
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
| D-SRP-049; FR-SRP-047 | AC-SRP-049 bounded stage/status/detail/redaction tests; AC-SRP-054 fail-fast privacy; M18 |
| D-SRP-050; FR-SRP-048 | AC-SRP-050 ordered single-batch snap/radius/source preservation and boundary failures; AC-SRP-054 sequence/privacy; M18 |
| D-SRP-051; FR-SRP-049 | AC-SRP-051 mapped/zero/no-path/transient out-and-back tests; AC-SRP-052 schema roundtrip; M18 |
| D-SRP-052; FR-SRP-052 | AC-SRP-049–051 fail-fast preservation plus AC-SRP-054 exact stage sequence; M18 |
| D-SRP-053; FR-SRP-051 | AC-SRP-052 schema-3 totals/provenance/recovery/compatibility tests; M18 |
| D-SRP-054; FR-SRP-050 | AC-SRP-053 generated presentation/accessibility proxy; M19 authoritative device gate |
| D-SRP-055; FR-SRP-052 | AC-SRP-054 notice/request-shape/privacy/no-write test plus all injected failure boundaries; M18 |
| D-SRP-056; FR-SRP-053 | AC-SRP-055 exact iOS Apple Maps/no-fallback, canonical-coordinate and unchanged Android tests; M20–M21 |
| D-101; FR-QPB-144; NFR-QPB-084 | AC-QPB-149 five-state direct builder/QGS/encrypted-store boundary |
| D-102; FR-QPB-145; NFR-QPB-084 | AC-QPB-150 direct symbol routing + generated-QGS rename/relocation; existing fallback/regression coverage reused |
| NFR-SRP-001 | AC-SRP-022/024 320px proxy plus M01 touch/keyboard |
| NFR-SRP-002 | AC-SRP-027 color+check+text proxy plus M04 |
| NFR-SRP-003 | AC-SRP-026–029 zero-request offline/restart/load/move tests plus M02–M04 |
| NFR-SRP-004 | AC-SRP-037–038/040–041 320px/render/accessibility proxies plus M10 native verification |
| NFR-SRP-005 | AC-SRP-042–044 explicitly bounded automatic proxies plus M11–M14 NOT RUN device evidence |
| NFR-SRP-006 | AC-SRP-046/047 structural checks and AC-SRP-048 controller boundary plus M15–M17 NOT RUN authoritative iOS evidence |
| NFR-SRP-007 | AC-SRP-049 64/320/512 limits, normalization, all-or-nothing redaction and no raw-body retention; M18 |
| NFR-SRP-008 | AC-SRP-050 exact configured radius/single batch/no probes plus AC-SRP-054 sequence and privacy; M18 |
| NFR-SRP-009 | AC-SRP-053 automatic structural/accessibility proxy plus authoritative M19 device evidence |

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
