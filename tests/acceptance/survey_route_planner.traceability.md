# Survey Route Planner — acceptance traceability

> **DRAFT reconciliation, 2026-09-14 — pending explicit user acceptance-artifact approval.**
> Approved Category B specification input: `3b08820`. Approved acceptance baseline: `ed8ac81`.
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
| AC-SRP-002 | `ac002_selection` (0/1/3 and focused unselected) | M01; actual QField selection API |
| AC-SRP-003 | `ac003_ac010_scope_mapping`, `ac003_site_default_mapping`, `ac003_type1_requires_explicit_mapping`, `ac003_reject_ids` | M01; actual QField layer/mapping controls |
| AC-SRP-004 | `ac004_start_and_return`, `ac004_missing_gps`, `ac008_offline_restart_relocation` | M02/M03; real GNSS, map interaction and moved default |
| AC-SRP-005 | `ac005_road_cost_request` (time/distance) | M02; live `ors-vroom` feasibility, no optimum guarantee |
| AC-SRP-006 | `ac006_failures_preserve_saved` (17 faults), `ac006_ac013_unknown_backend_rejected_before_request`, `ac002_selection[0]` | M02/M03; real connectivity failures |
| AC-SRP-007 | `ac007_result_roundtrip` (raw VROOM relative arrivals; optionals supplied/absent), `ac007_invalid_eta_rejected` (ISO/partial/negative/non-finite) | M02/M05; compare native relative ETA display and road overlay |
| AC-SRP-008 | `ac008_offline_restart_relocation` (routes, non-secret settings, key cleared) | M03; native process restart and moved folder |
| AC-SRP-009 | `ac009_storage_recovery` (5 faults) | M03; chosen native file API/atomicity proof |
| AC-SRP-010 | `ac003_ac010_scope_mapping`, `ac010_completion`, `ac010_ac011_no_remaining` | M04; actual layer field refresh and route-local UI |
| AC-SRP-011 | `ac011_remaining_revision` (preview/save/failure), `ac010_ac011_no_remaining` | M04; current GPS+8 and completed history |
| AC-SRP-012 | `ac012_road_and_naver` (OS success/refusal) | M05; actual Naver destination/app switching |
| AC-SRP-013 | `ac013_no_network_or_secrets` (5 passive operations), `ac013_backend_settings` (custom/default offset), `ac006_ac013_unknown_backend_rejected_before_request`, `ac008_offline_restart_relocation` | M01/M03/M05; live transport, queued requests and logs on device |
| AC-SRP-014 | `ac014_direct_drawing` (3 types), `ac014_incomplete_drawing` (4 invalid inputs) | M06; actual visual interaction |
| AC-SRP-015 | `ac015_ac016_uploaded_geometry` (3 formats×6 types), `ac015_ac016_parts_holes_xy`, `ac015_invalid_geometry` | M06; M/GeometryCollection policy still reserved |
| AC-SRP-016 | `ac015_ac016_uploaded_geometry`, `ac016_direct_generated_geometry`, `ac015_ac016_parts_holes_xy` | M06; actual generated layer rendering |
| AC-SRP-017 | `ac017_representatives_numerical` (2 CRS×6, unconditional), `ac017_projected_control_point`, `ac017_invalid_source_crs_preserves_saved` | M02/M06; native CRS/provider path still user-run |
| AC-SRP-018 | `ac018_regression_portability` (4 types×reference absent/present) | M06; existing polygon/relations/report/identify native regression |

## Draft-stage verification record (2026-09-14)

Working directory: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`.
No application source/resource inspection, application modifications, Git mutations, real services,
QField operation or legacy-suite replay was performed by this test-designer. Required-mode execution
uses only the public acceptance seam and does not turn mocked external boundaries into native proof.

Commands use `PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`,
`FIELDBUILD_REQUIRE_SRP_HARNESS=1`, a unique pytest base temp, and raw logs under
`C:\Users\Public\Documents\ESTsoft\CreatorTemp\FieldBuildKit-route-verification\test-design-reconcile-retry`.
Exact commands, counts and failures are recorded after the draft run.

The design verifier checks syntax, all 18 AC IDs, the six documented centroid controls, raw VROOM
numeric arrival fixtures, portable setting fixtures and 18 real SHP/ZIP/GPKG input fixtures. These
are fixture/oracle checks, not application centroid/upload behavior. Current automated results and
unperformed M01–M06 cannot establish overall acceptance PASS.

- Collection: **128 cases**, exit 0.
- Design-only verifier: exit 0; syntax, all 18 AC IDs, raw relative-arrival and four malformed
  timing fixtures, portable non-secret settings, six documented centroid fixtures, six independent
  Mercator controls, one EPSG:5186 control and 18 real upload fixtures passed.
- Required-mode acceptance: **106 passed, 16 failed, 6 skipped**, exit 1. The skips are exactly
  M01–M06. Failures remain as implementation/harness conformance gaps: AC003 accepted omitted
  Type 1 mapping (1); AC007 did not consume the raw optimizer order and accepted four malformed
  timing payloads (6); AC008 omitted independently reopened portable-setting observations (1);
  AC010 omitted post-restart completion observations (2); AC017 accepted missing/invalid/failed
  CRS cases and omitted preservation evidence (3); AC013 omitted registered transport/persistence
  observations for configured and unknown providers (3). The AC007 successful cases stop at the
  wrong-order assertion, so they do not yet establish ETA or optional-value roundtrip behavior.
- Whitespace check: exit 0; Git emitted only informational LF/CRLF normalization warnings.

Raw outputs: `collect-only.txt`, `verify-design.txt`, `required-mode-final.txt` and
`diff-check.txt` in the verification directory above. No failure was weakened to match the current
implementation.
