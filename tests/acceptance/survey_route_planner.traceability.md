# Survey Route Planner — acceptance traceability

> **APPROVED, 2026-09-14 — user explicitly approved acceptance artifacts on 2026-09-14; implementation verification pending.**
> Specification approved at `e382c77`; this artifact does not approve implementation/technology.
> Tests: [pytest module](survey_route_planner/test_survey_route_planner.py).
> [Design/manual cases](survey_route_planner.test-design.md) · [Harness](survey_route_planner/HARNESS_CONTRACT.md)

All test names below are real collected functions in the linked module. Automated checks are
contract/generated-output tests, not native QField/device evidence. Status for every criterion:
**PENDING IMPLEMENTATION/VERIFICATION**. Six manual placeholders remain explicitly skipped.
The previous PLANNED file-name list is superseded; its draft history remains in Git.

| Approved criterion | Executable test suffix (prefix `test_`) | User-run / remaining boundary |
| --- | --- | --- |
| AC-SRP-001 | `ac001_generated_plugin` | M01; native imports/API and actual panel coexistence |
| AC-SRP-002 | `ac002_selection` (0/1/3 and focused unselected) | M01; actual QField selection API |
| AC-SRP-003 | `ac003_scope_mapping`, `ac003_reject_ids` | M01; Type1 default and NULL mapping open |
| AC-SRP-004 | `ac004_start_and_return`, `ac004_missing_gps` | M02; real GNSS and map interaction |
| AC-SRP-005 | `ac005_road_cost_request` (time/distance) | M02; actual road provider/profile feasibility, no optimum guarantee |
| AC-SRP-006 | `ac006_failures_preserve_saved` (17 faults), `ac002_selection[0]` | M02/M03; real connectivity failures |
| AC-SRP-007 | `ac007_result_roundtrip` (optional values supplied/absent) | M02/M05; compare native display and road overlay |
| AC-SRP-008 | `ac008_offline_restart_relocation` | M03; native process restart and moved folder |
| AC-SRP-009 | `ac009_storage_recovery` (5 faults) | M03; chosen native file API/atomicity proof |
| AC-SRP-010 | `ac010_completion`, `ac010_ac011_no_remaining` | M04; actual layer field refresh, NULL mapping open |
| AC-SRP-011 | `ac011_remaining_revision` (preview/save/failure), `ac010_ac011_no_remaining` | M04; current GPS+8 and completed history |
| AC-SRP-012 | `ac012_road_and_naver` (OS success/refusal) | M05; actual Naver destination/app switching |
| AC-SRP-013 | `ac013_no_network_or_secrets` (5 passive operations), `ac013_backend_settings` | M01/M03/M05; queued network and logs on device |
| AC-SRP-014 | `ac014_direct_drawing` (3 types), `ac014_incomplete_drawing` (4 invalid inputs) | M06; actual visual interaction |
| AC-SRP-015 | `ac015_ac016_uploaded_geometry` (3 formats×6 types), `ac015_ac016_parts_holes_xy`, `ac015_ac017_invalid_geometry` | M06; M/GeometryCollection policy still reserved |
| AC-SRP-016 | `ac015_ac016_uploaded_geometry`, `ac016_direct_generated_geometry`, `ac015_ac016_parts_holes_xy` | M06; actual generated layer rendering |
| AC-SRP-017 | `ac017_representatives_numerical` (2 CRS×6), `ac017_projected_control_point`, `ac015_ac017_invalid_geometry` | M02/M06; O-SRP-003 candidate policy gated, no final AC017 PASS |
| AC-SRP-018 | `ac018_regression_portability` (4 types×reference absent/present) | M06; existing polygon/relations/report/identify native regression |

## Stage verification record (2026-09-14)

Working directory: `D:\오민우 Project\vibe_coding\fieldbuild_standalone`.
No application source/resource inspection, application modifications, Git mutations, real services,
QField operation or legacy-suite replay was performed by this test-designer.

```powershell
.venv-win\Scripts\python.exe -m pytest tests/acceptance/survey_route_planner -q --collect-only -p no:cacheprovider
.venv-win\Scripts\python.exe -m pytest tests/acceptance/survey_route_planner -q -rs -p no:cacheprovider
.venv-win\Scripts\python.exe tests/acceptance/survey_route_planner/verify_design.py
git diff --check -- tests/acceptance
```

- Collection: **118 cases**, exit 0.
- Draft execution: **118 skipped**, exit 0: **112** missing
  `run_survey_route_acceptance`, **6** explicitly user-run QField cases. **0 product PASS**.
  The missing adapter fixture is encountered before policy gates; these are not 112 policy skips.
- Initial design-check attempt: exit 1, missing optional Shapely. Removed that unnecessary
  dependency, using literal GeoJSON fixtures, Fiona and standard-library ring/part comparisons.
- Final design-only check: syntax and all 18 AC IDs found; 6 documented centroid fixtures,
  6 independent Fiona Mercator transformation controls, 1 EPSG:5186 control and **18 actual
  SHP/ZIP/GPKG input fixtures verified**, exit 0. This verifies fixture construction and numeric
  transformation oracles, not application centroid or upload behavior.
- Initial whitespace check found one extra EOF blank line in the acceptance README; corrected. Final whitespace check passed (exit 0); Git LF/CRLF normalization warnings are informational.

Implementation/review must set `FIELDBUILD_REQUIRE_SRP_HARNESS=1`, run actual assertions and report
counts independently. Candidate centroid policy requires the explicit opt-in named in design;
that setting does not itself constitute user approval. Current skipped product tests and
unperformed M01–M06 prevent any overall acceptance PASS.
