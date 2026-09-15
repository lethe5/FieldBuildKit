# Survey Route Planner — acceptance traceability

> **DRAFT reconciliation, 2026-09-15 — pending explicit user acceptance-artifact approval.**
> Approved specification input: `bd625d6`. Approved acceptance baseline: `ed8ac81`.
> This draft does not approve implementation or technology.
> Tests: [pytest module](survey_route_planner/test_survey_route_planner.py).
> [Design/manual cases](survey_route_planner.test-design.md) · [Harness](survey_route_planner/HARNESS_CONTRACT.md)

All test names below are real collected functions in the linked module. Automated checks are
contract/generated-output tests, not native QField/device evidence. Status for every criterion:
**DRAFT TEST / PENDING IMPLEMENTATION AND VERIFICATION**. Six manual placeholders remain
explicitly skipped. Mocked Qt/QML/JavaScript never counts as native QField/iOS/Android evidence.

| Approved criterion | Executable test suffix (prefix `test_`) | User-run / remaining boundary |
| --- | --- | --- |
| AC-SRP-001 | `ac001_generated_plugin` | M01; native imports/API and actual panel coexistence |
| AC-SRP-002 | `ac002_selection` (0/1/3, inline count/help and focused unselected) | M01; actual QField selection API |
| AC-SRP-003 | `ac002_selection`, `ac003_ac010_scope_mapping` (selected ignored by all/uncompleted), `ac003_site_default_mapping`, `ac003_type1_requires_explicit_mapping`, `ac003_reject_ids` | M01; actual QField layer/mapping controls |
| AC-SRP-004 | `ac004_start_and_return`, `ac004_missing_gps`, `ac008_offline_restart_relocation` | M02/M03; real GNSS, map interaction and moved default |
| AC-SRP-005 | `ac005_road_cost_request` (time/distance) | M02; live `ors-vroom` feasibility, no optimum guarantee |
| AC-SRP-006 | `ac006_failures_preserve_saved` (17 faults), `ac006_ac013_unknown_backend_rejected_before_request`, `ac002_selection[0]` | M02/M03; real connectivity failures |
| AC-SRP-007 | `ac007_result_roundtrip` (raw VROOM relative arrivals; optionals supplied/absent), `ac007_invalid_eta_rejected` (ISO/partial/negative/non-finite) | M02/M05; compare native relative ETA display and road overlay |
| AC-SRP-008 | `ac008_offline_restart_relocation` (routes, non-secret settings, key cleared) | M03; native process restart and moved folder |
| AC-SRP-009 | `ac009_storage_recovery` (5 faults) | M03; chosen native file API/atomicity proof |
| AC-SRP-010 | `ac003_ac010_scope_mapping`, `ac010_completion`, `ac010_completion_write_failure_preserves_state`, `ac010_ac011_no_remaining` | M04; actual layer field refresh, inline help and route-local UI |
| AC-SRP-011 | `ac011_remaining_revision` (preview/save/failure), `ac010_ac011_no_remaining` | M04; current GPS+8 and completed history |
| AC-SRP-012 | `ac012_road_and_naver` (OS success/refusal) | M05; actual Naver destination/app switching |
| AC-SRP-013 | `ac013_no_network_or_secrets` (5 passive operations), `ac013_backend_settings` (custom/default offset), `ac013_fresh_hosted_defaults_and_authorization`, `ac013_trailing_slashes_are_normalized_once`, `ac013_exact_legacy_default_migration` (5 exact/mixed/lookalike cases), `ac013_custom_self_hosted_urls_allow_no_key`, `ac013_hosted_default_rejects_blank_key_before_request`, `ac006_ac013_unknown_backend_rejected_before_request`, `ac008_offline_restart_relocation` | M01/M02/M03/M05; live hosted/custom transport, queued requests and redacted logs on device |
| AC-SRP-014 | `ac014_direct_drawing` (3 types), `ac014_incomplete_drawing` (4 invalid inputs) | M06; actual visual interaction |
| AC-SRP-015 | `ac015_ac016_uploaded_geometry` (3 formats×6 types), `ac015_ac016_parts_holes_xy`, `ac015_invalid_geometry` | M06; M/GeometryCollection policy still reserved |
| AC-SRP-016 | `ac015_ac016_uploaded_geometry`, `ac016_direct_generated_geometry`, `ac015_ac016_parts_holes_xy` | M06; actual generated layer rendering |
| AC-SRP-017 | `ac017_representatives_numerical` (2 CRS×6), `ac017_generated_geometry_uses_qfield_expression_evaluator` (2 CRS×6 strict generated-QML runs; forbids `geom_to_geojson`, requires supported centroid/transform/x/y), `ac017_projected_control_point`, `ac017_invalid_source_crs_preserves_saved` | M02/M06; native QField CRS/provider path still user-run |
| AC-SRP-018 | `ac018_regression_portability` (4 types×reference absent/present) | M06; existing polygon/relations/report/identify native regression |
| AC-SRP-019 | `ac019_builder_key_consent_embeds_only_project_variable`, `ac019_decline_or_blank_uses_manual_session_only` (2), `ac019_key_never_leaks_from_aborted_builder_flow` (2), `ac019_desktop_remember_is_not_qfield_delivery` | M02; actual device automatic/session key use, with redacted evidence only |
| AC-SRP-020 | `ac020_route_panel_fields_fill_available_width` (320/1024 px layout plus screenshots) | M01; actual narrow/wide device layout and touch use |

## Draft-stage verification record (2026-09-15)

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
