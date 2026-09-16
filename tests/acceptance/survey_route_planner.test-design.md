# Survey Route Planner — acceptance test design workflow reconciliation

> **APPROVED — explicit user approval of these reconciled acceptance artifacts, 2026-09-16.**
> Input: approved workflow specification in `specs/survey-route-planner.md` at checkpoint
> `1868b7a`, plus current shared docs and integrated spec. The acceptance checkpoint `ed8ac81`
> remains the approved baseline. This stage authors tests, not implementation or product PASS.

## Current authority and scope

FieldBuild Kit 0.2.9 uses the standalone QGIS-free generator, optional taxonomy, conditional
TIFF inputs and portable generated project folders. Historical QGIS Desktop/runtime/private-data
requirements in inherited tests do not govern new route tests. Existing evidence remains in
`docs/qfield-runtime-verification.md`; earlier macOS QField 4.2.11 loading is not route evidence.
No application implementation/resource files or prior role transcripts were read for this design.

The approved `ed8ac81` suite remains the historical baseline. The 2026-09-15 reconciliation is
retained and extended for D-SRP-020–030, FR-SRP-021–028, NFR-SRP-001–003 and AC-SRP-021–030. No historical PASS, device result or
approval is deleted or reinterpreted. Existing acceptance files with pre-route polygon-only
assumptions remain historical; do not silently weaken them. D-SRP-002 supersedes only the site
geometry restriction, not plot/community/observation semantics.

AC-SRP-011's approved historical “remaining recalculation” text remains traceable, but its old
request/save oracle is no longer executable. D-SRP-023 and FR-SRP-026 supersede it with a missing
control, immutable schema-2 full legs and zero-request completion derivation. Schema-1 fixtures are
kept byte-for-byte and tested as non-mutating legacy reads; they are not silently split into legs.

## Executable boundary

Tests: `survey_route_planner/test_survey_route_planner.py`; contract:
`survey_route_planner/HARNESS_CONTRACT.md`. One new function in the existing acceptance API
runs production actions with synthetic external-boundary inputs. Tests assert captured HTTP/
provider calls, detached and independently reopened storage snapshots, real portable files,
Fiona/SQLite geometry and GPKG metadata/rtree, actual generated panel/button/timer/UI diagnostics,
strict QField-shaped expression-evaluator calls, rendered layout screenshots, builder key UI,
 and generated report data. Workflow additions observe real project layer/field/feature models,
exact committed relative paths, Qt launcher calls, schema documents/legs, rendered completion and
route overlays, visible metrics and device-local project settings. The harness must not copy case values, invent observations or recompute
product state. This is a contract suite, not a separate implementation of routing or storage.
Adapter implementation is a later role.

The missing new function is a distinct explicit skip. Once exposed, exceptions/malformed results
and assertions fail. `FIELDBUILD_REQUIRE_SRP_HARNESS=1` turns absence into failure for implementation
and review. Do not report skips as covered runtime behavior. Six manual placeholders always skip.
No real network requests or purchased keys are needed for this stage. All secret fixtures are
synthetic and may appear only in the already-approved generated-project-variable exception or
intercepted `Authorization` header.

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
- Fresh registered `ors-vroom` projects dispatch matrix and directions to
  `https://api.heigit.org/openrouteservice/v2/...` and POST optimization directly to
  `https://api.heigit.org/vroom/v0`. Requests never append `/post` or use the deprecated host.
  Trailing slashes normalize once. Exact legacy routing and missing/empty/exact legacy optimizer
  values migrate independently; lookalike and mixed custom/self-hosted values remain unchanged.
  Nonempty project/session keys appear only in the three selected requests' `Authorization`
  headers. Hosted defaults reject blank keys before transport; custom/self-hosted endpoints allow
  keyless requests and omit the header.
- 8 stops with 2 completed through a configured Boolean field and, separately, through route-local
  storage when no field is mapped; next is the lowest incomplete sequence after immediate refresh
  and restart. Read-only and incompatible-field writes fail visibly and preserve source, saved
  route, active route, check, completed overlay, metrics and next. The historical remaining-route
  request is not executed: the control is absent and completion/uncheck derives from saved full legs
  with zero requests.
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
- The same 12 valid type/CRS cases are generated as actual FieldBuild Kit project layers and then
  calculated through the unchanged generated route QML. Its mock is limited to QField's documented
  `QfExpressionEvaluator` surface: exact writable context properties plus `evaluate()` and
  `evaluate(text)`, with dynamic properties rejected. The trace must set feature/layer/project,
  use supported centroid → transform → x/y expressions, and never execute the unsupported
  `geom_to_geojson` function that reproduced the false generic CRS message. This is a QField-shaped
  runtime contract, not native QField proof.
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
- Builder tests drive the real masked key input. A nonblank value requires a warning that names
  plaintext project storage, folder-reader access/use, lack of encryption and QField automatic use.
  Consent permits exactly one plaintext project variable location and proves automatic header use.
  Decline and blank builds contain no key and accept a session-only key that disappears on restart.
  Cancel/build-failure paths publish no project. Logs, errors, reports, URLs, query, bodies and
  general settings never contain the key; optional desktop remember remains `credentials.enc` and
  is not QField delivery.
- Narrow (320 px) and wide (1024 px) generated panels are loaded and rendered. Measured fields fill
  the common content rectangle, same-row fields split it evenly, labels/help/errors align and wrap,
  and neither viewport has horizontal overflow. Screenshots are test evidence, not device evidence.
- Project dropdown fixtures contain an internal `site` layer and two duplicate `표본구` aliases.
  Layer-tree/provider order and stable IDs are independent oracles. Stored valid IDs and actual field
  names survive reopen; stale selections refresh on layer/schema change and calculate/save preflight.
  Provider-order suffix defaults use mixed-case `_ID`/`_NAME`; no match stays blank and blocks work.
- Workflow UI cases assert exact `조사 경로 계산 대상`, `출발지`, `저장 경로 이름` and checklist
  guidance, mode-only map/target controls and `이름 · ID` target values. Default-start and route-save
  feedback must repeat the independently observed committed filename and project-relative path; a
  commit fault emits no success and no secret-bearing feedback.
- Naver uses an independently percent-encoded exact canonical `/navigation` URL with required
  `appname`. Android and iOS false dispatches each make exactly one package/App Store fallback call;
  true reports only OS request acceptance. Desktop/all-refused paths are actionable errors. Native
  destination acceptance and guidance remain M05 device evidence.
- Schema 2 uses three stops: open stores three legs and roundtrip four. Each raw directions segment
  has independent way-point indexes and non-negative distance/time. Canonical totals are leg sums;
  provider deltas at exactly `max(1 unit, 0.5%)` pass and deltas beyond it fail. Missing, reordered,
  negative/non-finite, non-WGS84 or count-mismatched legs preserve the old route. Completion,
  uncheck, toggle and load leave schema/revision/full legs/totals/geometry byte-equivalent.
- Progression closes only the consecutive prefix: completing stop 3 first leaves all legs and visit
  context; completing stops 1 then 2 leaves only the roundtrip return leg marked `복귀 포함`; unchecking
  stop 1 restores every leg. Point/line completion uses opaque `#1565C0`; polygon uses 35% fill and
  opaque outline. Check and `완료` text accompany color, source renderer/data remain unchanged, and
  restart/load rederive the non-persistent overlay.
- Metric controls cover 0, 1, 3599 and 3601 seconds, ceil-minute formatting, 1.23 km and exact active/
  no-route bottom bars. A default-on route-line preference applies to all routes in one project,
  leaves completion overlays/full geometry/source renderer unchanged, persists across switch/reopen/
  restart/settings-bearing move, and does not affect a separate project's default.
- A schema-1 route keeps line, totals, stops and bytes unchanged offline, shows enhanced remaining
  values as `사용 불가`, infers no legs and explains the one explicit full calculate/save upgrade.
  That explicit action alone may write schema 2 with a higher revision. Future schema is preserved
  and rejected without request or write.
- Regression: four survey types × no reference/fictional reference; retain UUID/relations and
  non-site geometries, execute report and identification paths after relocation, enforce no
  fabricated non-point report coordinates and conditional KTSN. No real private workbook.

## Resolved rules and coverage limits

| Item | Treatment without weakening invariant requirements |
| --- | --- |
| O-SRP-002 provider/QField API/version/profile support | Registered initial `ors-vroom` wire behavior is tested at intercepted transport boundaries; actual service and each device version still need verification. No real service call or optimum claim. |
| O-SRP-003 source CRS centroid order/MultiPoint | Resolved at `bd625d6`. All 12 type/CRS numerical cases and all 12 generated-QML cases run unconditionally; no test-side policy switch exists. |
| O-SRP-004 storage mechanism | Assert restart/move/integrity/atomic publication and revision semantics independently of file format. Actual QField file API and recovery feasibility are unverified. |
| O-SRP-005 completion/Type 1/offset/settings | Resolved at `bd625d6`: strict Boolean completion, Type 1 explicit mapping, 1000 m default and project-local non-secrets are acceptance gates. |
| O-SRP-006 hosted endpoints/migration/auth | Resolved at `bd625d6`: current HeiGIT defaults, exact legacy migration, custom preservation and request-header-only authentication are executable gates. |
| O-SRP-007 generated-project key | Resolved at `bd625d6`: explicit plaintext consent permits one generated project variable; decline/blank stays manual-session only. |
| Candidate Z/M and GeometryCollection policy | XY and polygon holes covered; Z candidate exercised. M and polygon-bearing GeometryCollection need fixtures once normalization policy is fixed; preserving prior compatible behavior remains required. |
| Zero input and missing mapping | Zero selected, no remaining and invalid IDs covered. Type 1 without explicit layer/ID/name mapping fails before transport. |
| Generated QML and desktop UI | Adapter executes actual generated logic and real widgets. Native QField import compatibility, touchscreen layout and OS navigation need manual evidence. |
| D-SRP-020–030 workflow | Executable proxy gates cover actual project models, storage commits, launcher dispatch, schema documents, derived progression/render state and offline persistence. Native provider ordering, FileUtils/overlay rendering, touch/keyboard and mobile app handoff remain M01–M05. |

A complete per-criterion map means tests/design are present; it does not mean every criterion has
fully automated proof. The six manual/native gaps prevent blanket PASS until user-run evidence exists.

## User-run device and real-service cases — NOT RUN

Record date, app artifact/hash, OS/device, QField version, Naver version, provider/API/profile,
project CRS/type, input IDs, expected vs observed result, screenshots/redacted logs, and verdict.
Run iOS and Android separately; one platform's PASS is not the other's. User performs QField
operation per AGENTS.md; automated sidecar checks never substitute for this evidence.

| Case | Steps and expected result | AC |
| --- | --- | --- |
| M01 | On iOS and Android, move/open the generated folder and inspect the actual project layer dropdown order, duplicate-label disambiguation, `조사지` default and provider-order field lists. Rename/remove a disposable field/layer, reopen and verify refresh, fallback or blank blocking. At 320px-class and wide devices verify exact labels/guidance, mode-only controls, target `이름 · ID`, wrapping, touch and keyboard access. | 001–003,013,020–024; NFR-001 |
| M02 | Build one consented and one declined project using only a synthetic key and redact evidence. Verify device key sourcing, GPS/map/target/saved start and a small real `ors-vroom` open and roundtrip route. Reopen schema 2 and compare every leg/total/full line. Finish/unfinish stops and verify zero provider traffic; no `남은 지점 계산` control exists. | 004–007,013,017,019,022–023,026; NFR-003 |
| M03 | Save two routes and default start, confirm feedback points to actual accessible project-relative settings/route files, turn route line off, switch routes, reopen panel, terminate/restart offline, then move the whole folder with settings and repeat. Preference, full route, completion overlay and progression remain identical; use only a disposable copy for corruption/recovery. | 008–009,013,023,026–029; NFR-003 |
| M04 | For mapped Boolean and route-local completion, complete point/line/polygon targets in order and out of order, close the gap, then uncheck. Verify Blue 800 opacity/fill, check and `완료` text, visit context, trimmed line, km/time/bottom bar and roundtrip return. Force a disposable write failure and verify every visual/metric/source value stays unchanged. | 010–011,024,027–028; NFR-002–003 |
| M05 | Separately on Android and iOS with Naver installed, invoke a Korean/special-character target, verify exact destination and begin guidance manually. Repeat without/disabled app handler to verify package/App Store fallback and all-refused error. Record that Qt true proves only OS request acceptance; it is not handoff/destination/guidance proof. | 012–013,025 |
| M06 | Desktop direct point/line/polygon drawing, invalid finish and two named sites; upload all six types. Open moved outputs on both device platforms, inspect each geometry/style/form. Existing polygons, UUID relations, observation/plot/community and report/identification remain functional; report non-point rows have no centroid-derived coordinates. Run the schema-1 unavailable/read-only case on a disposable legacy copy. | 014–018,029–030 |

## Stage validation

Exact commands, counts and limitations are in the traceability file. Syntax/collection and local
fixture/oracle checks validate test design only. Full legacy suite and live services are outside
this drafting stage. No approvals, product implementation PASS, device PASS or release is claimed.
