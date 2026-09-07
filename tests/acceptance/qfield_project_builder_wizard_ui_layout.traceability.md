# Traceability Matrix — FieldBuild Standalone wizard UI layout defect (D-96)

> Input: approved `specs/fieldbuild-kit-wizard-ui-layout-defect.md` and the shared conventions in
> `docs/ui-design-guidelines.md`.
>
> This is a clean-room test-design artifact. It changes no application code, specification, or
> Git state. The tests intentionally exercise the real PySide6 widgets after Qt layout/event
> processing; source-text checks and unlaid-out static size hints are not accepted as layout proof.

## Test artifacts

| Test-design ID | Artifact | Coverage role | Execution class |
|---|---|---|---|
| TD-UI-QPB-001/002/004/005/006 | `tests/unit/test_wizard_ui_layout.py` | Seven-page geometry, viewport/button-bar boundary, layout policies, control floors, API/Excel interaction, focus traversal, secret redaction, resize, and configured Qt scale-factor geometry | headless Qt; real layout pass |
| TD-UI-QPB-003/005 | `tests/acceptance/qfield_project_builder/test_wizard_ui_layout.py::test_ac_ui_qpb_999_macos_cocoa_manual_scaled_native_smoke` | Cocoa/native visual, scaled-display, focus-ring, logo, and packaged-app smoke | `manual` + `skip`; intentionally unavailable in headless harness |
| TD-UI-QPB-001/003/004 | `tests/acceptance/qfield_project_builder/test_wizard_ui_layout.py::test_ac_ui_qpb_001_real_wizard_keeps_scrollable_pages_above_native_buttons` | Acceptance-level real wizard smoke over all seven pages and native buttons | headless Qt; real geometry |
| TD-UI-QPB-003/004/005/006 | `tests/acceptance/qfield_project_builder/test_wizard_ui_layout.py::test_ac_ui_qpb_010_step4_and_step5_key_and_excel_surfaces_are_reachable` | Step 4 online/offline and Step 5 Pl@ntNet/reference smoke | headless Qt; real widget state |

The existing regression suite remains part of the acceptance evidence and is not duplicated here:

| Preserved contract | Existing evidence |
|---|---|
| Logo/page behavior | `tests/unit/test_wizard.py::test_wizard_page_hierarchy_contains_a_widget_showing_the_fieldbuild_kit_logo_banner`, `::test_wizard_page_titles_are_in_korean`, and the page-specific behavior tests |
| VWorld/Pl@ntNet masking, consent, remember semantics | `tests/unit/test_wizard.py::test_identification_toggle_page_has_masked_plantnet_api_key_field`, `::test_connectivity_page_*credential*`, `::test_collect_config_*api_key*`, and `tests/acceptance/qfield_project_builder/test_post_mvp_plantnet_key_embedding.py` |
| Canonical provenance, materialized tables, no raw source copy | `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac145_release_datas_and_runtime_candidate_path_share_storage_boundary` and `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_project_regression.py::test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` |
| Existing candidate/confirmation fail-closed behavior | `tests/unit/test_wizard.py` canonical-reference/identification tests plus the new `test_td_ui_qpb_006_*` cases |

## Acceptance-criterion matrix

| Spec ID | Observable contract | Automated test(s) | Class |
|---|---|---|---|
| AC-UI-QPB-001 | At 900×700 each page has no post-layout overlap or clipped content and the native bar is visible | `test_td_ui_qpb_001_all_seven_pages_have_scroll_viewport_above_native_bar`; `test_td_ui_qpb_003_minimum_controls_and_long_text_are_not_compressed`; `test_ac_ui_qpb_001_real_wizard_keeps_scrollable_pages_above_native_buttons` | headless geometry |
| AC-UI-QPB-002 | Long content scrolls within the page while the bottom bar stays fixed; no ordinary horizontal page overflow | `test_td_ui_qpb_001_all_seven_pages_have_scroll_viewport_above_native_bar`; `test_td_ui_qpb_002_page_and_content_layout_policies_are_explicit` | headless geometry/structure |
| AC-UI-QPB-003 | 900×700, 1000×760, supported maximum resize round-trip reflows and retains state | `test_td_ui_qpb_000_wizard_uses_required_minimum_and_recommended_initial_size`; `test_td_ui_qpb_009_resize_round_trip_retains_state_and_bar` | headless geometry/state |
| AC-UI-QPB-004 | 100/125/150/200% logical-size result remains usable and scrollable | `test_td_ui_qpb_008_logical_geometry_at_configured_qt_dpi_scale` (one process per `QT_SCALE_FACTOR`); `test_ac_ui_qpb_999_macos_cocoa_manual_scaled_native_smoke` | headless scale matrix + manual Cocoa |
| AC-UI-QPB-005 | Tab/Shift+Tab reaches controls and native buttons with visible focus | `test_td_ui_qpb_007_keyboard_tab_shift_tab_enter_space_and_names`; manual smoke placeholder | headless keyboard + manual visual |
| AC-UI-QPB-006 | Typing/toggling/opening/activating/preview scrolling does not cover content or native buttons | `test_td_ui_qpb_001_all_seven_pages_have_scroll_viewport_above_native_bar`; `test_td_ui_qpb_006_excel_candidate_keyboard_activation_is_not_confirmation`; `test_td_ui_qpb_009_resize_round_trip_retains_state_and_bar` | headless geometry/interaction |
| AC-UI-QPB-010 | Step 4 online controls and long status remain readable/actionable | `test_td_ui_qpb_004_vworld_online_and_offline_controls_remain_reachable_and_secret`; `test_ac_ui_qpb_010_step4_and_step5_key_and_excel_surfaces_are_reachable` | headless widget/geometry |
| AC-UI-QPB-011 | Step 4 offline key, disclosure, layer/source/canvas/zoom/estimate controls remain reachable; canvas floor preserved | `test_td_ui_qpb_011_offline_map_canvas_scrolls_inside_page_without_covering_controls`; existing `test_offline_map_canvas_keeps_its_full_320x240_usable_minimum_size`; existing `test_offline_map_canvas_does_not_overlap_*`; `test_td_ui_qpb_001_all_seven_pages_have_scroll_viewport_above_native_bar` | headless geometry |
| AC-UI-QPB-012 | VWorld key remains masked and absent from non-field UI text | `test_td_ui_qpb_004_vworld_online_and_offline_controls_remain_reachable_and_secret`; existing credential-store and config tests | headless security regression |
| AC-UI-QPB-013 | Online consent is separate and keyboard-toggleable; offline shows transient-use disclosure only | `test_td_ui_qpb_004_vworld_online_and_offline_controls_remain_reachable_and_secret`; existing `test_connectivity_page_offline_mode_never_shows_the_online_only_embedding_disclosure`; existing consent/config tests | headless widget/state |
| AC-UI-QPB-014 | Refresh status grows without clipping/displacing layer controls or bottom buttons | `test_td_ui_qpb_004_vworld_online_and_offline_controls_remain_reachable_and_secret` | headless post-layout geometry |
| AC-UI-QPB-020 | Step 5 Pl@ntNet text/key/disclosure/consent/remember/status remains reachable by scroll | `test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct`; acceptance Step 5 smoke | headless widget/geometry |
| AC-UI-QPB-021 | Pl@ntNet key remains masked and absent from visible explanatory/status text | `test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct`; existing `test_identification_toggle_page_has_masked_plantnet_api_key_field` | headless security regression |
| AC-UI-QPB-022 | Step 5 keyboard traversal reaches enable/key/consent/remember/reference/native buttons | `test_td_ui_qpb_007_keyboard_tab_shift_tab_enter_space_and_names`; manual focus-ring portion | headless keyboard + manual visual |
| AC-UI-QPB-023 | Consent and remember remain independent after geometry/state updates | `test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct`; existing Pl@ntNet consent/config tests | headless state + regression |
| AC-UI-QPB-030 | Candidate rows show filename/source/status/sheet/header/sample rows without overlap | `test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct` | headless rendered item content/geometry |
| AC-UI-QPB-031 | Long preview rows can scroll within preview/page and never move the native bar | `test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct`; `test_td_ui_qpb_006_excel_candidate_keyboard_activation_is_not_confirmation` | headless widget/geometry |
| AC-UI-QPB-032 | User upload path, status, preview, upload, and confirm recovery controls remain reachable; invalid input fails closed | `test_td_ui_qpb_006_user_upload_preserves_path_and_source_kind_and_recovery_controls` | headless widget/state |
| AC-UI-QPB-033 | Keyboard candidate activation matches selection, but explicit confirmation remains required | `test_td_ui_qpb_006_excel_candidate_keyboard_activation_is_not_confirmation` | headless keyboard/state |
| AC-UI-QPB-034 | Long/normalized display text does not alter actual path or source kind | `test_td_ui_qpb_006_user_upload_preserves_path_and_source_kind_and_recovery_controls`; candidate actual-path assertion; existing canonical provenance tests | headless provenance |
| AC-UI-QPB-035 | Invalid/missing/changed source status wraps/scrolls and leaves recovery available | `test_td_ui_qpb_006_user_upload_preserves_path_and_source_kind_and_recovery_controls`; existing canonical validation/fail-closed tests | headless widget/state |
| AC-UI-QPB-036 | Layout work does not introduce raw workbook copies or remove materialized provenance | D-95 canonical release boundary `test_ac145_release_datas_and_runtime_candidate_path_share_storage_boundary`; generated-project boundary `test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` | generated-artifact regression |

## Functional/constraint coverage

| Spec IDs | Coverage |
|---|---|
| FR-UI-QPB-001 | `test_td_ui_qpb_000_*` plus acceptance smoke: exact 900×700 minimum and 1000×760 initial size; finite maximum bounded by the 1200×820 target |
| FR-UI-QPB-002--006 | `test_td_ui_qpb_001_*`, `test_td_ui_qpb_002_*`, `test_td_ui_qpb_003_*`, `test_td_ui_qpb_008_*`, `test_td_ui_qpb_009_*`; manual native smoke for Cocoa-only rendering |
| FR-UI-QPB-007--010 | `test_td_ui_qpb_002_*` and `test_td_ui_qpb_003_*` inspect real layout margins/spacing/policies, clickable heights, wrapping, and scrollable content |
| FR-UI-QPB-011--014 | `test_td_ui_qpb_004_*` plus existing Step 4 API/canvas tests |
| FR-UI-QPB-015--021 | `test_td_ui_qpb_005_*`, `test_td_ui_qpb_006_*`, `test_td_ui_qpb_007_*`, and existing canonical-reference tests |
| C-UI-QPB-001 | Existing page-order and behavior tests in `tests/unit/test_wizard.py`; seven-page enumeration in `test_td_ui_qpb_001_*` |
| C-UI-QPB-002 | New VWorld/Pl@ntNet secret-redaction assertions plus existing masking, consent, encrypted-remember, and key-embedding tests |
| C-UI-QPB-003 | New candidate actual-path/source-kind tests plus existing canonical preview/confirmation/provenance tests |
| C-UI-QPB-004 | Existing no-raw-workbook acceptance tests, explicitly mapped to AC-UI-QPB-036 |
| C-UI-QPB-005--006 | Native `QWizard` button inspection in `test_td_ui_qpb_001_*` and logical-size/DPI tests; Cocoa display behavior is explicitly manual/skip |

## Manual boundary

The manual test is not a hidden pass condition. It is marked `@pytest.mark.manual` and
`@pytest.mark.skip` because this harness cannot supply a native Cocoa display, packaged app, real
macOS scaling modes, or reliable visual inspection of focus rings/logo rendering. When available,
run the documented matrix from the skip reason and record the result separately. Headless tests
remain responsible for measurable geometry, widget reachability, keyboard event behavior, and
security/provenance state; they do not claim to prove native Cocoa pixels.

The former `test_offline_map_canvas_overlap_reproduces_without_the_scroll_area_fix` was removed
from the active contract. It monkeypatched only the old nested wrapper and asserted a pre-D-96
overlap; once D-96 made the page-level `QScrollArea` the actual layout boundary, that setup no
longer represented a product path. Its coverage is replaced by the positive
`test_td_ui_qpb_011_offline_map_canvas_scrolls_inside_page_without_covering_controls` regression,
which asserts the page viewport, scrollability, 320x240 canvas floor, and post-layout non-overlap
together.

## Verification policy for this design round

Tests were not executed by design. Only Python AST/syntax validation is permitted for this round.
