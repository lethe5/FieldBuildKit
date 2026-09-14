# Survey Route Planner — acceptance test design reconciliation

> **DRAFT — 2026-09-14. Pending explicit user approval of these reconciled acceptance artifacts.**
> Input: approved Category B clarification in `specs/survey-route-planner.md` at checkpoint
> `3b08820`, plus current shared docs and integrated spec. The acceptance checkpoint `ed8ac81`
> remains the approved baseline. This stage authors tests, not implementation or product PASS.

## Current authority and scope

FieldBuild Kit 0.2.8 uses the standalone QGIS-free generator, optional taxonomy, conditional
TIFF inputs and portable generated project folders. Historical QGIS Desktop/runtime/private-data
requirements in inherited tests do not govern new route tests. Existing evidence remains in
`docs/qfield-runtime-verification.md`; earlier macOS QField 4.2.11 loading is not route evidence.
No application implementation/resource files or prior role transcripts were read for this design.

The approved `ed8ac81` suite remains the historical baseline. This draft changes only expectations
affected by D-SRP-008–013 and the listed existing FR/AC. No historical PASS, device result or
approval is deleted or reinterpreted. Existing acceptance files with pre-route polygon-only
assumptions remain historical; do not silently weaken them. D-SRP-002 supersedes only the site
geometry restriction, not plot/community/observation semantics.

## Executable boundary

Tests: `survey_route_planner/test_survey_route_planner.py`; contract:
`survey_route_planner/HARNESS_CONTRACT.md`. One new function in the existing acceptance API
runs production actions with synthetic external-boundary inputs. Tests assert captured HTTP/
provider calls, detached and independently reopened storage snapshots, real portable files,
Fiona/SQLite geometry and GPKG metadata/rtree, actual generated panel/button/timer/UI diagnostics,
and generated report data. The harness must not copy case values, invent observations or recompute
product state. This is a contract suite, not a separate implementation of routing or storage.
Adapter implementation is a later role.

The missing new function is a distinct explicit skip. Once exposed, exceptions/malformed results
and assertions fail. `FIELDBUILD_REQUIRE_SRP_HARNESS=1` turns absence into failure for implementation
and review. Do not report skips as covered runtime behavior. Six manual placeholders always skip.
No real network requests or purchased keys are needed for this stage.

## Fixtures and independent oracles

- 0/1/3 selected from twelve named targets with an independently focused, unselected feature.
  Site-bearing types use the `site/site_id/site_name` default. Type 1 succeeds with explicit
  layer/ID/name mapping and fails before transport without it. Configured completion values cover
  Boolean `true`, `false`, `NULL` and missing; only `true` is complete. Duplicate/empty/null IDs
  fail. With no completion mapping, the actual route-stop control owns completion locally.
- GPS/map/target/saved departure is `[127.123,37.456]`; default route returns to departure.
  Missing GPS cannot become zero coordinates. Saved default is tested after process/session reset.
- Directed depot/A/B/C matrix: time cycle O-A-B-C-O costs 4; reversed cycle costs 80.
  Distance O-C-B-A-O costs 8; forward costs 120. Inputs have identical positions between runs;
  optimizer request must carry the selected road-cost matrix and objective. The test injects
  backend orders and checks response consumption, not global optimality or a private solver.
- Result persistence receives a raw VROOM 1.14 response at the optimizer HTTP boundary. Job
  `steps[].arrival` values `[60,180,300]` remain numeric route-start-relative seconds before and
  after save/restart, paired with `eta_basis=relative_seconds`; no ISO value or top-level
  pre-normalized `route.eta` is injected. A raw response without optional timing/directions data
  keeps ETA basis, legs and road geometry absent instead of inventing an absolute clock or line.
  ISO, partial, negative and non-finite job arrivals reject the candidate and preserve the active
  saved route; present/absent assertions require `eta` and `eta_basis` to remain paired.
- Storage: two distinct saved routes plus active route; session destruction, offline keyless reload,
  moved directory with old location inaccessible; partial write/storage-full/latest corruption/
  all corruption/concurrent revision. No fixed JSON slots or SQLite schema. Observe last-good
  data, stale-writer rejection and unpublished partial candidate through real storage fault seams.
  Server and optimizer URLs, registered backend, profile, timeout, 50 m road offset, default start
  and target mapping move with the folder. The session key does not.
- 8 stops with 2 completed through a configured Boolean field and, separately, through route-local
  storage when no field is mapped; next is the lowest incomplete sequence after immediate refresh
  and restart. 12 with 4 complete produces GPS
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
  EPSG:5186 origin control `POINT(200000 600000)` maps to `[127,38]`. Point uses its original
  coordinate and is reprojected when needed. The other five types always use their source-CRS
  centroid before transformation. Missing/invalid CRS and transformation failure reject the
  candidate, preserve the active saved route and issue no request.
- Naver Korean destination name contains `&/#?`; parse exact URL and assert longitude, latitude,
  decoded destination and no fragment. Launcher refusal needs a visible error; successful OS
  dispatch must not imply arrival or Naver internal acceptance.
- Registered `ors-vroom` configuration supplies distinct server/optimizer URLs, profile, timeout,
  objective, road offset and synthetic session key. The harness observes them at provider dispatch
  and actual intercepted external calls. The unknown-backend case fails before any request and
  preserves saved/active state. A configured calculation is preview-only and preserves the same
  saved/active state. Omitted road offset reaches transport as the 1000 m default.
- Synthetic route key is checked against whole generated folder, persisted settings, saved route
  data and full logs.
  Passive operations count *all queued routing requests* after setup, including delayed tasks.
  Existing basemap traffic is isolated, not confused with routing API calls.
- Regression: four survey types × no reference/fictional reference; retain UUID/relations and
  non-site geometries, execute report and identification paths after relocation, enforce no
  fabricated non-point report coordinates and conditional KTSN. No real private workbook.

## Resolved rules and coverage limits

| Item | Treatment without weakening invariant requirements |
| --- | --- |
| O-SRP-002 provider/QField API/version/profile support | Registered initial `ors-vroom` wire behavior is tested at intercepted transport boundaries; actual service and each device version still need verification. No real service call or optimum claim. |
| O-SRP-003 source CRS centroid order/MultiPoint | Resolved at `3b08820`. All 12 type/CRS numerical cases run unconditionally; no test-side policy switch exists. |
| O-SRP-004 storage mechanism | Assert restart/move/integrity/atomic publication and revision semantics independently of file format. Actual QField file API and recovery feasibility are unverified. |
| O-SRP-005 completion/Type 1/offset/settings | Resolved at `3b08820`: strict Boolean completion, Type 1 explicit mapping, 1000 m default, project-local non-secrets and session-only key are acceptance gates. |
| Candidate Z/M and GeometryCollection policy | XY and polygon holes covered; Z candidate exercised. M and polygon-bearing GeometryCollection need fixtures once normalization policy is fixed; preserving prior compatible behavior remains required. |
| Zero input and missing mapping | Zero selected, no remaining and invalid IDs covered. Type 1 without explicit layer/ID/name mapping fails before transport. |
| Generated QML and desktop UI | Adapter executes actual generated logic and real widgets. Native QField import compatibility, touchscreen layout and OS navigation need manual evidence. |

A complete per-criterion map means tests/design are present; it does not mean every criterion has
fully automated proof. The six manual/native gaps prevent blanket PASS until user-run evidence exists.

## User-run device and real-service cases — NOT RUN

Record date, app artifact/hash, OS/device, QField version, Naver version, provider/API/profile,
project CRS/type, input IDs, expected vs observed result, screenshots/redacted logs, and verdict.
Run iOS and Android separately; one platform's PASS is not the other's. User performs QField
operation per AGENTS.md; automated sidecar checks never substitute for this evidence.

| Case | Steps and expected result | AC |
| --- | --- | --- |
| M01 | Move generated folder to device, permit plugin, verify report/identify and bottom single-row name/completion panel. Expand/collapse while manipulating map. Select 0/1/N, focus unselected row, verify site defaults, configure Type 1 layer/ID/name and omit it once. Lists follow actual selection; zero and missing Type 1 mapping are clearly blocked. | 001–003,013 |
| M02 | Disable GNSS, calculate and see actionable failure. Enable valid GPS; test map/target/saved departure after reopen, default return. Configure real `ors-vroom` with user-entered key and chosen time/distance profile, calculate a small known road detour/asymmetric route, compare provider jobs/units/order/road response and numeric relative ETA. Capture redacted provider evidence; no assertion of globally optimal route. | 004–007,017 |
| M03 | Save two routes, activate each, close app fully, remove connectivity and session key, reopen; move whole folder and repeat. Data/road line/next target remain identical. Simulate copied-project corrupted storage only, observe safe recovery/refusal; never corrupt real user data. Passive actions produce zero routing-service traffic. | 008,009,011,013 |
| M04 | Set configured layer values to Boolean true/false/NULL/missing then return to the panel, and repeat without a completion field using route-local controls. Verify 2/8 summary/next, then 4/12 complete and remaining calculation from current GPS sends 8 stops, saves higher revision, retains completed history. Cancel or fail calculation and check old saved route. | 010,011 |
| M05 | Reload saved road geometry offline and compare map. Navigate to Korean/special-character destination in installed Naver; verify target coordinates. Test OS launch refusal/unavailable handler and useful error. OS dispatch alone is not proof of app-internal success. | 007,012,013 |
| M06 | Desktop direct point/line/polygon drawing, invalid finish and two named sites; upload all six types. Open moved outputs on device, inspect each geometry/style/form. Existing polygons, UUID relations, observation/plot/community and report/identification remain functional; report non-point rows have no centroid-derived coordinates. | 014–018 |

## Stage validation

Exact commands, counts and limitations are in the traceability file. Syntax/collection and local
fixture/oracle checks validate test design only. Full legacy suite and live services are outside
this drafting stage. No approvals, product implementation PASS, device PASS or release is claimed.
