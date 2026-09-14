# Survey Route Planner — acceptance test design

> **APPROVED — 2026-09-14. Acceptance artifacts explicitly approved by the user; implementation verification pending.**
> Input: approved `specs/survey-route-planner.md` at checkpoint `e382c77` plus current shared
> docs and integrated spec. This stage authors tests, not implementation or product PASS.

## Current authority and scope

FieldBuild Kit 0.2.8 uses the standalone QGIS-free generator, optional taxonomy, conditional
TIFF inputs and portable generated project folders. Historical QGIS Desktop/runtime/private-data
requirements in inherited tests do not govern new route tests. Existing evidence remains in
`docs/qfield-runtime-verification.md`; earlier macOS QField 4.2.11 loading is not route evidence.
No application implementation/resource files or prior role transcripts were read for this design.

The previous route design/traceability listed future JS/Python files and had no execution evidence.
Those plans are replaced by the concrete pytest module below; Git retains that draft history.
No historical PASS, device result or approval is deleted or reinterpreted. Existing acceptance
files with pre-route polygon-only assumptions remain historical; do not silently weaken them.
D-SRP-002 supersedes only the site geometry restriction, not plot/community/observation semantics.

## Executable boundary

Tests: `survey_route_planner/test_survey_route_planner.py`; contract:
`survey_route_planner/HARNESS_CONTRACT.md`. One new function in the existing acceptance API
runs production actions with synthetic transport/device/storage inputs. Tests assert captured
requests, detached saved snapshots, real portable files, independently reopened Fiona/SQLite
geometry and GPKG metadata/rtree, actual UI state, and generated report data. This is a contract
suite, not a separate implementation of routing or storage. Adapter implementation is a later role.

The missing new function is a distinct explicit skip. Once exposed, exceptions/malformed results
and assertions fail. `FIELDBUILD_REQUIRE_SRP_HARNESS=1` turns absence into failure for implementation
and review. Do not report skips as covered runtime behavior. Six manual placeholders always skip.
No real network requests or purchased keys are needed for this stage.

## Fixtures and independent oracles

- 0/1/3 selected from twelve named targets with an independently focused, unselected feature.
  Configured ID/name/completion fields, custom source layer, duplicate/empty/null IDs;
  all/uncompleted scopes and explicit Type1 mapping. Dates/observation existence are not completion.
- GPS/map/target/saved departure is `[127.123,37.456]`; default route returns to departure.
  Missing GPS cannot become zero coordinates. Saved default is tested after process/session reset.
- Directed depot/A/B/C matrix: time cycle O-A-B-C-O costs 4; reversed cycle costs 80.
  Distance O-C-B-A-O costs 8; forward costs 120. Inputs have identical positions between runs;
  optimizer request must carry the selected road-cost matrix and objective. The test injects
  backend orders and checks response consumption, not global optimality or a private solver.
- Storage: two distinct saved routes plus active route; session destruction, offline keyless reload,
  moved directory with old location inaccessible; partial write/storage-full/latest corruption/
  all corruption/concurrent revision. No fixed JSON slots or SQLite schema. Observe last-good
  data, stale-writer rejection and unpublished partial candidate through real storage fault seams.
- 8 stops with 2 completed; next is lowest incomplete sequence. 12 with 4 complete produces GPS
  plus exactly 8 remaining jobs. Preview/failure cannot change saved state; save increases revision
  and preserves route identity/completed records. All complete produces no backend request.
- Real SHP, ZIP and GPKG fixtures × Point/LineString/Polygon/MultiPoint/MultiLineString/MultiPolygon.
  Two named records each; actual source files remain unchanged; reread output feature count,
  topology/parts, unique IDs, metadata, rtree count, integrity and project geometry. Additional
  same-family single/multi, polygon hole and Z→XY fixtures prevent simple-count-only acceptance.
  Point/line/polygon direct drawing drives real controls; invalid/degenerate/bow-tie cases reject.
- Numerical WGS84 oracles use asymmetric line and triangle: line centroid `(8/3,1/3)` from lengths
  4 and 2, triangle `(2,1)`. MultiLine matches length weighting; two polygons areas 9 and 2 yield
  `(118/33,31/33)`. MultiPoint candidate `(3,3)` averages three points. These deliberately differ
  from first vertex and bounding-box center.
- For EPSG:3857, scale fixture XY by 100,000 then translate by `(1,000,000,5,000,000)`; calculate
  source centroid analytically and inverse Web Mercator using radius 6,378,137. A nontrivial
  northing span distinguishes centroid-before-transform from transform-before-centroid. Tolerance
  `1e-7` degrees accommodates numeric rounding while detecting swapped axes/wrong CRS/order.
  EPSG:5186 origin control `POINT(200000 600000)` maps to `[127,38]`. Point transformation is
  unconditional; provisional centroid policy cases are explicitly separated below.
- Naver Korean destination name contains `&/#?`; parse exact URL and assert longitude, latitude,
  decoded destination and no fragment. Launcher refusal needs a visible error; successful OS
  dispatch must not imply arrival or Naver internal acceptance.
- Synthetic route key is checked against whole generated folder, saved route data and full logs.
  Passive operations count *all queued routing requests* after setup, including delayed tasks.
  Existing basemap traffic is isolated, not confused with routing API calls.
- Regression: four survey types × no reference/fictional reference; retain UUID/relations and
  non-site geometries, execute report and identification paths after relocation, enforce no
  fabricated non-point report coordinates and conditional KTSN. No real private workbook.

## Outstanding decisions and coverage limits

| Item | Treatment without weakening invariant requirements |
| --- | --- |
| O-SRP-002 provider/QField API/version/profile support | Provider-neutral request and behavior contract; actual service and each device version still need verification. No ORS/VROOM/Valhalla import or SDK assumed. |
| O-SRP-003 source CRS centroid order/MultiPoint | Numerical candidate tests exist. Non-Point projected and MultiPoint cases skip unless `FIELDBUILD_SRP_CENTROID_POLICY=source_crs_centroid`; opt-in characterizes this proposal only. Policy must be closed by specification authority before a final AC017 verdict. No test chooses another representative. |
| O-SRP-004 storage mechanism | Assert restart/move/integrity/atomic publication and revision semantics independently of file format. Actual QField file API and recovery feasibility are unverified. |
| O-SRP-005 completion NULL/Type1 default/settings migration | Explicit Boolean fields and explicit Type1 mapping tested. NULL interpretation, default layer and key/server portability remain open; nonempty failure messages are necessary but manual language review remains. |
| Candidate Z/M and GeometryCollection policy | XY and polygon holes covered; Z candidate exercised. M and polygon-bearing GeometryCollection need fixtures once normalization policy is fixed; preserving prior compatible behavior remains required. |
| Zero input and missing mapping | Zero selected, no remaining and invalid IDs covered. Type1 default choice is not silently replaced with a nonexistent site. |
| Generated QML and desktop UI | Adapter executes actual generated logic and real widgets. Native QField import compatibility, touchscreen layout and OS navigation need manual evidence. |

A complete per-criterion map means tests/design are present; it does not mean every criterion has
fully automated proof. Conditional policies and manual gaps prevent blanket PASS until resolved.

## User-run device and real-service cases — NOT RUN

Record date, app artifact/hash, OS/device, QField version, Naver version, provider/API/profile,
project CRS/type, input IDs, expected vs observed result, screenshots/redacted logs, and verdict.
Run iOS and Android separately; one platform's PASS is not the other's. User performs QField
operation per AGENTS.md; automated sidecar checks never substitute for this evidence.

| Case | Steps and expected result | AC |
| --- | --- | --- |
| M01 | Move generated folder to device, permit plugin, verify report/identify and bottom single-row name/completion panel. Expand/collapse while manipulating map. Select 0/1/N, focus unselected row, change layer and configure ID/name fields. Lists follow actual selection; zero is clearly blocked. | 001–003,013 |
| M02 | Disable GNSS, calculate and see actionable failure. Enable valid GPS; test map/target/saved departure after reopen, default return. Configure real provider with user-entered key and chosen time/distance profile, calculate small known road detour/asymmetric route, compare provider jobs/units/order/road response. Capture redacted provider evidence; no assertion of globally optimal route. | 004–007,017 |
| M03 | Save two routes, activate each, close app fully, remove connectivity and session key, reopen; move whole folder and repeat. Data/road line/next target remain identical. Simulate copied-project corrupted storage only, observe safe recovery/refusal; never corrupt real user data. Passive actions produce zero routing-service traffic. | 008,009,011,013 |
| M04 | Change configured layer completion directly then return to panel, and repeat without a completion field. Verify 2/8 summary/next, then 4/12 complete and remaining calculation from current GPS sends 8 stops, saves higher revision, retains completed history. Cancel or fail calculation and check old saved route. | 010,011 |
| M05 | Reload saved road geometry offline and compare map. Navigate to Korean/special-character destination in installed Naver; verify target coordinates. Test OS launch refusal/unavailable handler and useful error. OS dispatch alone is not proof of app-internal success. | 007,012,013 |
| M06 | Desktop direct point/line/polygon drawing, invalid finish and two named sites; upload all six types. Open moved outputs on device, inspect each geometry/style/form. Existing polygons, UUID relations, observation/plot/community and report/identification remain functional; report non-point rows have no centroid-derived coordinates. | 014–018 |

## Stage validation

Exact commands, counts and limitations are in the traceability file. Syntax/collection and local
fixture/oracle checks validate test design only. Full legacy suite and live services are outside
this drafting stage. No approvals, product implementation PASS, device PASS or release is claimed.
