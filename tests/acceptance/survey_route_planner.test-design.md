# Survey Route Planner — APPROVED legacy-expectation supersession reconciliation

> **APPROVED TEST DESIGN — supersession reconciliation (approval 2026-09-17).**
> This approved reconciliation aligns retained AC-SRP-019/022/024/031 executable expectations with the already
> approved D-SRP-043/045, FR-SRP-041/043 and AC-SRP-043/045 authority. It changes no criterion.
> All approval records below remain historical authority and are not reopened by this reconciliation.

> **APPROVED TEST DESIGN (approval 2026-09-16).**
> The approved `bcd6ffc` acceptance baseline and its approved correction remain unchanged authority.
> The approved D-SRP-031–035, FR-SRP-029–033 and AC-SRP-031–035 expectations remain unchanged.
> This approved test-design correction corrects only the evidence provenance and fixture defects identified in review.
> D-SRP-036–041, FR-SRP-034–039, NFR-SRP-004 and AC-SRP-036–041 below are an
> **APPROVED TEST DESIGN (approval 2026-09-17)** extension. The approved baseline is unchanged.
> The supersession reconciliation in this correction is **APPROVED TEST DESIGN (approval 2026-09-17)**.
> D-SRP-042–045, FR-SRP-040–043, NFR-SRP-005, AC-SRP-042–045 and
> D-UI-SRP-007–010 retain their **APPROVED TEST DESIGN (approval 2026-09-17)** history.
> The evidence correction below is **APPROVED TEST DESIGN (approval 2026-09-17)**. It does not change the approved
> AC-SRP-001–045 meaning or claim implementation/device PASS.

> **APPROVED TEST DESIGN (approval 2026-09-18).**
> This additive slice covers approved D-SRP-046–048, FR-SRP-044–046, NFR-SRP-006,
> AC-SRP-046–048, D-101/102, FR-QPB-144/145, NFR-QPB-084 and AC-QPB-149/150.
> It does not reopen prior approved test design or claim iOS/QField PASS.

## Current authority and scope

FieldBuild Kit 0.2.9 uses the standalone QGIS-free generator, optional taxonomy, conditional
TIFF inputs and portable generated project folders. Historical QGIS Desktop/runtime/private-data
requirements in inherited tests do not govern new route tests. Existing evidence remains in
`docs/qfield-runtime-verification.md`; earlier macOS QField 4.2.11 loading is not route evidence.
This correction uses the structured review findings and current raw acceptance output; it changes no
application implementation/resource file.

The approved `bcd6ffc` suite remains the baseline. The 2026-09-15/16 reconciliation is retained and
extended for D-SRP-031–035, FR-SRP-029–033 and AC-SRP-031–035. No historical PASS, device result or
approval is deleted or reinterpreted. The follow-up adds AC-SRP-036–041 without renumbering or
replacing earlier IDs. Existing acceptance files with pre-route polygon-only
assumptions remain historical; do not silently weaken them. D-SRP-002 supersedes only the site
geometry restriction, not plot/community/observation semantics.

This approved correction applies the approved explicit supersessions consistently to retained tests:
D-SRP-037/FR-SRP-035 replace the six older long selector labels, D-SRP-038/FR-SRP-036 make the
provider settings initially collapsed, D-SRP-039/FR-SRP-037 replace Android's old universal `nmap`
oracle with the official package-bound intent, and D-SRP-040/FR-SRP-038 block user-entered later-stop
completion while preserving out-of-order values created by uncheck or an external Boolean refresh.
Because the collapsed ORS field is no longer the active state oracle, retained AC031 compares the
shared typography/insets/padding while requiring any differing color to be backed by a real validation
rectangle and a consistent error color; AC037 keeps the seven-control state matrix. All other retained
assertions and AC-SRP-036–041 evidence requirements remain unchanged.

This approved reconciliation applies the later approved rules to three remaining legacy conflicts. AC019 reads the
actual Step 7 warning widget and exact D-SRP-045 copy instead of an adapter parser tied to obsolete
phrase fragments. AC022/024 expect the saved-route dropdown label `저장 경로 불러오기`, while the
editable route-name field remains `저장할 경로 이름`. AC031 remains a six-control historical subset
for its accessibility/collision evidence; AC043 is the final eight-control authority. Its former
full-rectangle `label_in_control` predicate is superseded because an approved floating label centered
on the top outline necessarily straddles the control boundary. The retained `panel_layout`
`label_clipped` field uses that same full-rectangle test and therefore reports a false positive; this
reconciliation does not treat that adapter defect as evidence or modify the adapter. AC043 still reads the live
label's actual truncation state. The adapter also assigns its first global visible validation
rectangle to every AC031 control, so this reconciliation reports and stops consuming that unassociated value;
AC043 keeps per-control live validation object identity and geometry. AC031 rejects
separate label rows only for those six control labels, so an unrelated action button with matching
text is not classified as a label row. AC043 still rejects a separate label row for every one of the
eight floating controls.

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
route overlays, visible metrics and device-local project settings. Stable QML object identity,
rendered rectangles/style/accessibility, independent production-preflight captures, complete canvas
marker enumeration, actual write observers and generated source/GPKG/QGS provenance are required.
The harness must not copy case values, invent observations or recompute
product state. This is a contract suite, not a separate implementation of routing or storage.
Adapter implementation is a later role.

The missing new function is a distinct explicit skip. Once exposed, exceptions/malformed results
and assertions fail. `FIELDBUILD_REQUIRE_SRP_HARNESS=1` turns absence into failure for implementation
and review. Do not report skips as covered runtime behavior. Fourteen manual placeholders always skip.
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
- Builder tests drive the real masked key input. A nonblank value reads the actual Step 7 warning
  widget and requires the exact D-SRP-045 warning and consent copy. The observed copy explicitly says
  QField automatically uses the key, the project stores unencrypted characters, and anyone who can
  open the project folder can inspect and use the key.
  Consent permits exactly one plaintext project variable location and proves automatic header use.
  Decline and blank builds contain no key and accept a session-only key that disappears on restart.
  Cancel/build-failure paths publish no project. Logs, errors, reports, URLs, query, bodies and
  general settings never contain the key; optional desktop remember remains `credentials.enc` and
  is not QField delivery.
- Narrow (320 px) and wide (1024 px) generated panels are loaded and rendered. Measured fields fill
  the common content rectangle, same-row fields split it evenly, labels/help/errors align and wrap,
  and neither viewport has horizontal overflow. Screenshots are test evidence, not device evidence.
- At 320 and 1024 px, AC031's historical six `계산 대상`/`출발지`/`조사지`/ID/name/completion
  selector subset runs empty, value, focus
  and error states. Their rendered in-control floating-label signatures are compared with the ORS
  server URL TextField in the same state. Independent rectangles reject label/option/validation
  option collision; AC043 retains authoritative per-control validation collision and live
  truncation/clipping evidence. AC031
  does not require the label box to sit wholly below the top outline.
  Separate label rows for those six labels, placeholder-only accessible names and mapping writes are
  forbidden. AC043 remains final authority for all eight controls.
- Scope guidance runs selected/all/uncompleted with 0/1/3 selected features at both widths. The
  common explanation always occupies the first row after scope. Only selected inserts the exact
  procedure/count row next; all/uncompleted put the next control at normal spacing with no hidden row.
- Map-center start captures exact WGS84 coordinates, renders one high-contrast marker with visible
  `출발지`, remains fixed through pan/zoom, and moves rather than duplicates on recapture. Separate
  lifecycle cases retain it through collapse/reopen and calculation success/failure, remove it for
  mode change, clear/invalid and project close, and preserve the prior marker on transform failure.
  Renderer/source/saved-route writes attributed to the marker are independently empty.
- Project dropdown fixtures contain an internal `site` layer and two duplicate `표본구` aliases.
  Layer-tree/provider order and stable IDs are independent oracles. Stored valid IDs and actual field
  names survive reopen; stale selections refresh on layer/schema change and calculate/save preflight.
  Provider-order suffix defaults use mixed-case `_ID`/`_NAME`; no match stays blank and blocks work.
- Workflow UI cases assert exact `계산 대상`, `출발지`, `저장 경로 불러오기` and checklist
  guidance, mode-only map/target controls and `이름 · ID` target values. Default-start and route-save
  feedback must repeat the independently observed committed filename and project-relative path; a
  commit fault emits no success and no secret-bearing feedback.
- Target candidates use provider-order IDs `site-03`, `site-01`, `site-02`, including duplicate
  `같은 이름` labels. Selected/all/uncompleted each run exact 0/1/3 sets; rendered options and the
  independently captured production calculation preflight submitted IDs/order must match. Distinct
  capture IDs prevent reuse of the rendered model as preflight evidence. Population precedes
  required validation. A transition sequence covers QField selection, completion, scope and
  ID/name mapping refresh, valid-ID preservation, stale-ID clear and `이름 · ID` disambiguation.
- Naver uses independently percent-encoded platform-specific `/navigation` oracles with required
  `appname`: the official package-bound Android intent and iOS `nmap` scheme. Android and iOS false
  dispatches each make exactly one package/App Store fallback call;
  true reports only OS request acceptance. Desktop/all-refused paths are actionable errors. Native
  destination acceptance and guidance remain M05 device evidence.
- Schema 2 uses three stops: open stores three legs and roundtrip four. The raw ORS feature has one
  route-level `properties.way_points` array with intermediate road vertices; segments deliberately
  lack `way_points` and contain only per-leg metrics/steps. Consecutive top-level index pairs slice
  exact inclusive leg LineStrings. Canonical totals are leg sums;
  provider deltas at exactly `max(1 unit, 0.5%)` pass and deltas beyond it fail. Missing, reordered,
  negative/non-finite, non-WGS84 or count-mismatched legs preserve the old route. Completion,
  uncheck, toggle and load leave schema/revision/full legs/totals/geometry byte-equivalent.
- Provider negatives are raw optimizer missing/duplicate/unknown/unassigned order and raw directions
  missing/duplicate/out-of-range top-level waypoint index, missing segment, invalid top-level
  geometry, invalid metric and total-tolerance breach. Each returns a provider-response category and
  affected ID/index/field/leg while preserving last-good route and secrets. One unchanged valid
  payload is forced to fail only after provider validation at local leg mapping; it must instead be
  a client-processing error with retry guidance and the same preservation.
- Point, MultiPoint, LineString, MultiLineString, Polygon and MultiPolygon each pass the approved
  source-CRS representative through a real WKT+CRS source, production-generated GPKG/QGS layer and
  actual generated QML calculation, one-job VROOM order,
  documented one-leg ORS GeoJSON, save and independent reopen. Road geometry may have intermediate
  vertices unrelated to the source shape. These six runs are automated contract evidence, not native
  QField evidence; M07–M09 keep actual QField Point/Line/Polygon outcomes manual.
- AC031 observes the retained six-control subset as distinct loaded-QML selector and label objects,
  while AC043 remains the final eight-control authority. AC031's separate-row check is scoped to the
  six observed control labels and does not treat unrelated action buttons as label rows. It preserves
  their actual rectangles,
  visible/enabled/focus state, accessibility role/name/state and rendered style metrics alongside a
  separately observed ORS reference object. Text tables, source constants and synthesized signatures
  are not evidence. AC034 computes gaps from actual visible row coordinates and verifies hidden
  guidance has neither a layout rectangle nor a visible-layout entry.
- AC032 enumerates the entire canvas marker collection after each action and surrounds the action
  sequence with source-provider and route-storage commit observers. Empty commit logs count only
  when those observers cover the full window and independent before/after snapshots match.
- AC026 malformed directions are constructed in the test module by changing only route-level
  `properties.way_points`, top-level `geometry`, or documented segment metric/count fields.
  `segments[].way_points` remains absent and each rejection carries the captured input path/hash.
  AC027 consumes the raw directions fixture with intermediate vertices, saves through production,
  and binds its hash to the independently reopened route ID/revision/storage path.
- AC001 proves panel controls by stable loaded-QML identity and visible/enabled state. AC017 invalid
  CRS cases first save, reopen and activate a nonempty production baseline with storage provenance.
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

### 2026-09-17 follow-up fixtures and independent oracles

- AC-SRP-036 starts from a candidate produced by raw optimizer/directions responses and a separately
  read saved base revision. Focus plus two name edits must preserve the full candidate and calculation
  inputs with zero new requests. The test trims `  오후 조사 경로  ` independently and compares the
  stored route after removing only persistence-owned identity/name/timestamp/revision fields. Blank,
  I/O and recoverable-validation attempts must retain that candidate for a corrected save. Separate
  input-change and external-revision fixtures are the only stale cases.
- AC-SRP-037 uses seven exact semantic labels at 320 and 1024 px across empty/value/focus/error/disabled.
  It compares raw relative label geometry, font, outline, notch and padding across text/dropdown
  controls and checks raw intersections with value, indicator and error rectangles. The object tree,
  screenshot and accessibility state must come from the loaded generated QML; stored values are
  compared before/after so a visual adapter cannot substitute changed selections.
- AC-SRP-038 opens a fresh session collapsed, expands/collapses twice, and captures zero requests/writes.
  Manual and consented-project keys are separate build/session fixtures with independent `.qgs`
  readback. Two actual saves must expose both A/B relative paths and independently decoded settings;
  synthetic key and objective are excluded. A commit fault preserves last-good bytes and the in-memory key.
- AC-SRP-039 constructs exact official URL oracles in the test: Android package-bound intent, iOS
  `nmap://navigation`, Google Play `market://details?id=com.nhn.android.nmap`, and App Store
  `http://itunes.apple.com/app/id311867728?mt=8`. Korean/special-character destination and appname
  are encoded independently. Current official guidance supplies no navigation web URL for this
  native fixture, so inferred `map.naver.com` dispatch is forbidden. Actual handoff remains M10.
- AC-SRP-040 uses a three-stop schema-2 fixture. It compares complete state snapshots around blocked
  later-row attempts, then observes one-at-a-time enabling. Fully completed→uncheck and external
  `[false,true,false]` create a visible `순서 밖 완료` gap with the original full remaining line;
  closing the gap derives the known final leg without any routing request.
- Retained AC-SRP-001 observes the server-setting child as present and enabled but initially hidden
  behind the collapsed disclosure. Retained AC-SRP-010 completes `0` then `1` so its Boolean/source
  persistence assertions do not demand a forbidden later-row mutation. Retained AC-SRP-027 first
  proves a later-row attempt leaves the full state unchanged, then creates its out-of-order gap by
  unchecking an earlier completed row. AC-SRP-040 remains the detailed independent blocked-action test.
- AC-SRP-041 generates real Point/LineString/Polygon projects with normal, empty, null and markup-looking
  names. Generated QGS/GPKG paths and source bytes anchor the evidence. Headless/generated-style
  observations are configuration proxies for configured-field text, white halo, no empty artifact
  and inert markup; they are not QField map-canvas render evidence. Polygon light/dark proxy renders
  use green `#2E7D32` outline/translucent fill and remain distinct from blue completion/route and
  orange start treatments without changing source geometry, attributes or renderer contract.

### 2026-09-17 device-defect follow-up fixtures and independent oracles — APPROVED TEST DESIGN correction

- AC-SRP-042 creates a candidate through real optimizer/directions boundaries and loads the actual
  generated route-name control. Separate window-dispatched taps hit the field body and label/notch
  overlap. Focus/caret is read immediately after each tap; no `forceActiveFocus` or equivalent recovery
  may occur, and a failed tap remains a test failure. Korean/Latin IME commits start only after focus,
  followed by selection, deletion and replacement. Every event preserves candidate/base revision and
  emits zero provider requests; real save/reopen observes the trimmed name. This is only an input-wiring
  proxy. M11 and M12 retain Android and iOS soft-keyboard evidence as NOT RUN.
- AC-SRP-043 expands the approved matrix to exactly eight controls, including `저장 경로 불러오기`,
  at 320 and 1024 px across empty/value/focus/disabled/error. It reads raw live-object label/notch
  rectangles and a top-outline observation from live border geometry or rendered-image edge detection;
  both vertical centers must be within `max(1 px, outline-width/2)` of that line. Error rectangles come
  from visible validation objects. Each state independently rereads repository values and the live
  selected-route model before/after, using distinct observation IDs. All controls share the common
  component with no separate label row. Constants, copied state and synthesized geometry are forbidden.
  M13 retains target-QField screenshot/interaction review.
- AC-SRP-044 drives the normal build path, without post-generation editing, for all six geometry
  types with present/missing name-field fixtures. Tests independently hash and reopen the generated
  QGS and GPKG, inspect the real layer schema/features and QGIS labeling XML for enabled
  name→stable-ID→blank expression, family placement, white buffer, `labelPerPart=false` and
  `mergeLines=false`. The LineString fixture adds same-name endpoint-connected features so a merge
  regression is visible. Python-reimplemented expression output is not runtime evidence: exact expression
  structure is checked independently, and only an available PyQGIS `QgsExpression` may report evaluated
  results. An unavailable runtime records its actual probe diagnostic and no runtime claims. These are
  configuration proxies only; M14 retains one-visible-label-per-feature and halo evidence in QField.
- AC-SRP-045 observes the actual Step 7 Qt widget tree and parent-layout order for blank, key without
  consent, key with consent and desktop remember-only builds. It reads focus order through
  `QWidget.nextInFocusChain` and queries real `QAccessible` interfaces. An unavailable interface is
  recorded as unavailable, never as a true constant. Exact title/purpose/blank/warning/consent copy,
  masking and wrapping are asserted. The synthetic key must be absent
  from summary/log/error/general settings/diagnostics and every artifact except the one explicitly
  consented QGS project-variable occurrence. Assertions and harness diagnostics use redacted failure
  messages so test output cannot print the synthetic secret.

### 2026-09-17 iOS/QField and integrated-builder follow-up fixtures — APPROVED TEST DESIGN (approval 2026-09-18)

- AC-SRP-046 renders each light/dark × normal/value/empty/focus/selected/checked/error/disabled
  state from loaded generated QML. The test independently computes WCAG ratios from raw screenshot
  pixel pairs: text is at least 4.5:1 and boundaries/indicators/focus affordances at least 3:1.
  State roles require a non-color cue. A separate light→dark→light run keeps values, live focus,
  candidate, route and scroll identical while request/write captures remain empty. Source color
  literals and headless pixels are bounded proxies; M15 is the final iOS evidence.
- AC-SRP-047 uses 320/1024 px, 1.0/1.3 supported text-scale fixtures and all five required states.
  It measures the complete painted header bottom and first label painted top in rendered pixels,
  converts by observed device-pixel ratio and requires at least 8 dp. Actual window hit tests must
  route label/control taps to the first control and header taps to collapse, with disjoint hit regions,
  no clipping and no horizontal overflow. M16 remains final iOS screenshot/tap evidence.
- AC-SRP-048 injects UTC instants only at the platform-clock boundary for Seoul, Los Angeles and
  Kiritimati, independently derives the device-local Gregorian date with `zoneinfo`, and holds locale
  variable. It observes the exact default after successful calculation, actual selection/delete/
  Korean+Latin input events, preservation across passive/retry/failure actions, trimmed save/load and
  reset only on the next explicit successful calculation. Automated input events do not prove an iOS
  soft keyboard; M17 remains NOT RUN.
- AC-QPB-149 extends the existing actual Step 7 widget/build fixture to blank-with-both-checked,
  non-blank-neither, consent-only, remember-only and both. QGS parsing and isolated encrypted-store
  reopen independently prove the two destinations. Raw key scans cover visible copy, diagnostics,
  ordinary settings and artifacts, allowing exactly one consented QGS occurrence and no plaintext
  desktop occurrence.
- AC-QPB-150 normally builds Point/MultiPoint canonical `site` plus every eligible non-site semantic
  point layer in the fixture. QGS parsing before/after alternate display names and folder relocation
  keys exclusion to canonical table/role, proves the selected relative SVG on all eligible non-site
  point layers, and compares geometry/attributes/labels/relations/route overlays. No-icon and failed-
  fetch fixtures prove the existing minimalist fallback; polygon/line site and Type 4 remain unchanged.

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
| D-SRP-036–041 follow-up | Generated-asset/contract gates cover name-only save, rendered labels/disclosure, key provenance and snapshot exclusion, exact URL dispatch, ordered checklist state and generated styling. Native QField accessibility/rendering, atomic file behavior and mobile handoff remain M10. |
| D-SRP-042–045 follow-up | Loaded-control and generated-artifact proxies cover editable/input-method wiring, exact eight-control geometry, six-family QGS/GPKG labeling configuration and Step 7 copy/secret boundaries. Android/iOS soft keyboards and actual QField layout/map rendering remain M11–M14. |
| D-SRP-046–048 follow-up | Rendered-QML pixel/geometry/input-lifecycle proxies cover contrast thresholds, passive theme switching, header clearance/hit routing and device-local default naming. Actual iOS/QField appearance, taps and soft keyboard remain M15–M17. |
| D-101/102 integrated builder follow-up | Actual Step 7 build/store readback and generated-QGS relocation fixtures cover independent key destinations and canonical-site icon exclusion. Desktop screen-reader behavior and target-QField rendering remain user-observed boundaries. |

A complete per-criterion map means tests/design are present; it does not mean every criterion has
fully automated proof. The seventeen manual/native cases prevent blanket PASS until user-run evidence exists.

## User-run device and real-service cases — NOT RUN

Record date, app artifact/hash, OS/device, QField version, Naver version, provider/API/profile,
project CRS/type, input IDs, expected vs observed result, screenshots/redacted logs, and verdict.
Run iOS and Android separately; one platform's PASS is not the other's. User performs QField
operation per AGENTS.md; automated sidecar checks never substitute for this evidence.

| Case | Steps and expected result | AC |
| --- | --- | --- |
| M01 | On iOS and Android, move/open the generated folder and inspect the actual project layer dropdown order, duplicate-label disambiguation, `조사지` default and provider-order field lists. Rename/remove a disposable field/layer, reopen and verify refresh, fallback or blank blocking. At 320px-class and wide devices verify all six in-control floating labels in empty/value/focus/error states, selected-only guidance/count, no hidden gap, exact target `이름 · ID`, wrapping, touch and keyboard access. | 001–003,013,020–024,031,033–034; NFR-001 |
| M02 | Build one consented and one declined project using only a synthetic key and redact evidence. Verify device key sourcing, GPS/map/target/saved start and a small real `ors-vroom` open and roundtrip route. Capture the map center marker, pan/zoom, recapture, collapse/reopen, calculate success/failure and every removal lifecycle. Reopen schema 2 and compare every route-level-waypoint slice/total/full line. Finish/unfinish stops and verify zero provider traffic; no `남은 지점 계산` control exists. | 004–007,013,017,019,022–023,026,032,035; NFR-003 |
| M03 | Save two routes and default start, confirm feedback points to actual accessible project-relative settings/route files, turn route line off, switch routes, reopen panel, terminate/restart offline, then move the whole folder with settings and repeat. Preference, full route, completion overlay and progression remain identical; use only a disposable copy for corruption/recovery. | 008–009,013,023,026–029; NFR-003 |
| M04 | For mapped Boolean and route-local completion, attempt a later target and verify it is blocked, complete point/line/polygon targets in order, then create a gap by unchecking or externally changing the source Boolean. Verify Blue 800 opacity/fill, check and `완료`/`순서 밖 완료` text, visit context, trimmed line, km/time/bottom bar and roundtrip return. Force a disposable write failure and verify every visual/metric/source value stays unchanged. | 010–011,024,027–028,040; NFR-002–004 |
| M05 | Separately on Android and iOS with Naver installed, invoke a Korean/special-character target, verify exact destination and begin guidance manually. Repeat without/disabled app handler to verify package/App Store fallback and all-refused error. Record that Qt true proves only OS request acceptance; it is not handoff/destination/guidance proof. | 012–013,025 |
| M06 | Desktop direct point/line/polygon drawing, invalid finish and two named sites; upload all six types. Open moved outputs on both device platforms, inspect each geometry/style/form. Existing polygons, UUID relations, observation/plot/community and report/identification remain functional; report non-point rows have no centroid-derived coordinates. Run the schema-1 unavailable/read-only case on a disposable legacy copy. | 014–018,029–030 |
| M07 | In actual QField, create/select a disposable Point 조사지, calculate a small real ORS open route and inspect the target ID/order, one route-level-waypoint leg, road line and saved/reopened values. Record redacted request/response evidence and mark PASS only after performing it. | 017,030,035 |
| M08 | Repeat M07 with an asymmetric LineString whose approved centroid differs from its first vertex and bounding-box center. Verify the representative sent, ORS acceptance and reopened leg; automated QML evidence does not substitute for this result. | 017,030,035 |
| M09 | Repeat M07 with an asymmetric Polygon whose approved centroid differs from its first vertex and bounding-box center. Verify the source renderer/geometry remains unchanged. | 017,030,035 |
| M10 | On actual QField Android and iOS, verify the seven labels and initially collapsed settings disclosure at 320px class width with keyboard/touch/screen reader; confirm manual/project key provenance and A/B feedback without exposing a key. Save a calculated candidate after name-only edits and recoverable failure. Exercise ordered completion/gap display, light/dark polygon and name-halo rendering, then separately verify Android package intent and iOS nmap handoff/store fallback. Record each platform result; automated URL/QML checks do not substitute. | 036–041; NFR-004 |
| M11 | On supported Android with no external keyboard and OS soft keyboard enabled, tap the actual `저장할 경로 이름` body. Record QField/app/OS versions and redacted evidence for caret/focus, soft keyboard, Korean/Latin input, selection, deletion, correction, trim save, zero recalculation and unchanged candidate/revision. Automated QML input events do not substitute. | 042; NFR-005 |
| M12 | Repeat M11 separately on supported iOS. Do not reuse the Android verdict. Record any OS-level keyboard suppression condition separately from an app failure. | 042; NFR-005 |
| M13 | In target QField at 320px class and a wide viewport, capture empty/value/focus/disabled/error screenshots and interaction/accessibility review for all eight exact controls. Confirm every label/notch center crosses the visible top outline, `저장 경로 불러오기` has no separate label row, and there is no collision, clipping or horizontal scroll. | 043; NFR-005 |
| M14 | Open a normal-build spaced six-geometry fixture in target QField at suitable zoom. Capture each feature's single readable label and white halo for name, stable-ID fallback and no-label cases; verify multipart features do not repeat per part and markup remains inert. Automated XML/QGIS/headless evidence does not substitute. | 044; NFR-005 |
| M15 | On the same supported iPhone/iOS QField project and candidate, capture light and dark appearance for normal/value/empty/focus/selected/checked/error/disabled states. Measure every summary/label/value/help/action/status foreground against its actual background and boundaries/indicators/focus cues against adjacent colors; record the 4.5:1/3:1 results and non-color cues. Switch themes while focused/scrolled and confirm values, candidate, route and scroll persist with no request/write. | 046; NFR-006 |
| M16 | On target iOS QField at 320 px-class and wide supported viewports/text scales, capture the expanded header and first `조사지` control in empty/value/focus/error/disabled states. Measure at least 8 dp between complete painted header bottom and label top; verify full label/notch/outline, no overlap/clipping/scroll, label/control taps focus only the control and only header taps collapse. | 047; NFR-006 |
| M17 | Set a disposable iOS device fixture so local date is 2026-09-17, calculate a new route and observe exact `2026-09-17 조사`. Tap for caret/soft keyboard, select/delete and enter Korean/Latin text, then verify trim save with zero recalculation. Repeat collapse, theme change, refresh, retry, failed calculation, next-day successful calculation, locale change and saved-route load; record the local-date reset/preservation boundary. | 048; NFR-005–006 |

## Stage validation

This approved correction changed only the five survey-route acceptance artifacts. It did not edit
application code, unit tests, approved specifications/UI guidance or Git state. Commands used the
repository interpreter with `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`,
`QT_QPA_PLATFORM=offscreen`, `FIELDBUILD_REQUIRE_SRP_HARNESS=1`, no pytest cache and separate
disposable base-temp directories.

- Design verifier: exit 0; 41 AC IDs and every retained provenance/provider/geometry/fixture guard
  passed, including the four explicit supersession corrections. It executes no application behavior.
- Corrected conflict slice: **27 passed, 285 deselected**, exit 0, in 40.60 s.
- Unchanged AC-SRP-036–041 slice: **33 passed, 279 deselected**, exit 0, in 42.65 s.
- Full survey-route acceptance suite: **302 passed, 10 skipped**, exit 0, in 435.47 s. The ten skips
  are exactly M01–M10 and remain user-run native QField/device/live-service evidence.

The original **278 passed, 24 failed, 10 skipped** result therefore contained 24 contradictory old
expectations and no remaining automated implementation failure after correction. This correction is
**APPROVED TEST DESIGN (approval 2026-09-17)**. The automated pass does not establish M01–M10, native QField,
Android/iOS Naver handoff, live ORS, device rendering or release acceptance.

## AC-SRP-042–045 approval record (2026-09-17)

Status: **APPROVED TEST DESIGN (approval 2026-09-17)**. This test-designer changed only the five
allowed survey-route acceptance artifacts. No application code, unit test, specification, UI-guidance
file or Git state was modified. Commands used the repository interpreter, UTF-8/no-bytecode/offscreen
settings, required harness mode, no pytest cache and a dedicated disposable base-temp directory.

- Collection: **343 cases**, exit 0. The increase is 27 AC-SRP-042–045 automated cases and four
  manual placeholders; M01–M10 are preserved.
- Design verifier: exit 0. It checked syntax, all 45 AC IDs, exact eight labels and Step 7 copy,
  normal-build QGS/GPKG evidence tokens, explicit no-keyboard/no-QField-render claims, and M01–M14.
- Focused required-mode selector `ac042 or ac043 or ac044 or ac045`: **27 failed, 316 deselected**,
  exit 1, in 37.51 s. Every authoritative failure is the expected missing acceptance operation:
  `route_name_text_input_proxy` (1), `final_floating_label_geometry` (10),
  `generated_site_label_contract` (12) or `builder_step7_route_credentials` (4). The current harness
  cannot yet produce the required loaded-control/artifact/widget evidence, so no product criterion is
  marked PASS.
- Manual selector: **14 skipped, 329 deselected**, exit 0. M11 Android and M12 iOS keyboard checks,
  M13 target-QField eight-label screenshots and M14 target-QField six-geometry label rendering are
  explicitly NOT RUN.
- Acceptance-only `git diff --check`: exit 0; Git emitted only informational LF/CRLF warnings.

An initial focused probe exposed two test-design defects before the authoritative rerun: AC044 fixture
rows lacked runtime-compatible geometry/coordinate keys, and AC045's default pytest parameter IDs
printed the synthetic key. The fixture was completed and AC045 now parameterizes only redacted state
names. The rerun above contains only unsupported-operation failures; these corrected test defects are
not attributed to the application. OS soft-keyboard opening and QField label rendering remain wholly
unperformed and cannot be inferred from the automated failures.

### Approved evidence correction (2026-09-17)

Status: **APPROVED TEST DESIGN (approval 2026-09-17)**. The approved criterion text and original approval record above
remain unchanged. This correction rejects focus recovery, copied/synthetic UI geometry, Python label
evaluation presented as runtime evidence, line-label merging, and constant accessibility/order claims.
M01–M14 remain NOT RUN; automated failures are not native-device results.

- Collection: **344 cases**, exit 0. AC042 now has separate body and label/notch-overlap cases.
- Design verifier: exit 0; all 45 AC IDs, corrected evidence fields, no-merge sensitivity and explicit
  M01–M14 boundaries passed without executing application behavior.
- Focused required-mode selector `ac042 or ac043 or ac044 or ac045`: **28 failed, 316 deselected**,
  exit 1, 32.85 s. The exact first failures were 2 missing touch-target observations (the current driver
  still contains focus recovery), 10 missing common-component observations, 12 generated QGS files with
  `mergeLines=1`, and 4 missing actual widget-tree observations. These are meaningful product/harness
  failures; no native-device result is inferred.
- Manual selector: **14 skipped, 330 deselected**, exit 0. M01–M14 are explicitly NOT RUN.
- Acceptance-only `git diff --check`: exit 0 with informational LF/CRLF warnings only.

## APPROVED legacy-expectation reconciliation verification (2026-09-17)

Status: **APPROVED TEST DESIGN — supersession reconciliation (approval 2026-09-17)**. This reconciliation changes only the
five survey-route acceptance artifacts. It changes no application, runtime adapter/driver, unit test,
approved specification/UI-guidance file or Git state. Earlier approval records above remain preserved.

- Supplied pre-correction full result: **315 passed, 15 failed, 14 skipped**. The exact affected
  selector independently reproduced **15 failed, 329 deselected**.
- Design verifier: exit 0. It now guards the D-SRP-045 exact-copy widget observation against the old
  warning parser, rejects `저장 경로 이름` as the saved-route dropdown label while preserving
  `저장할 경로 이름` for the editable field, and requires AC031's six controls to remain a strict
  subset of AC043's eight-control final authority.
- Corrected affected selector: **15 passed, 329 deselected**, exit 0, in 27.08 s.
- Approved AC042–045 focused selector: **28 passed, 316 deselected**, exit 0, in 32.68 s.
- Collection: **344 cases**, exit 0. Manual selector: **14 skipped, 330 deselected**, exit 0;
  M01–M14 remain NOT RUN.
- Full required-mode module: **330 passed, 14 skipped**, exit 0, in 484.56 s. There are no remaining
  automated failures and no product-code change is required for this reconciliation.
- Acceptance-only `git diff --check`: exit 0 with informational LF/CRLF warnings only.

The unchanged `panel_layout` adapter still has three obsolete observations: full-rectangle
`label_in_control`, a `label_clipped` value derived from the same containment rule, and one global
validation rectangle copied to every control. They contradict or cannot prove the approved
outline-centered/per-control geometry. This approved reconciliation reports those adapter defects and stops consuming
them in AC031; it does not accept them as evidence or modify runtime code. AC043 retains live
per-control outline, truncation, validation identity/geometry and collision evidence for all eight
controls. The green automated run does not convert M01–M14 into device PASS.

## AC-SRP-046–048 / AC-QPB-149–150 approval record (approval 2026-09-18)

Status: **APPROVED TEST DESIGN (approval 2026-09-18).** This fresh test-designer changed only
the five acceptance artifacts listed by `git diff --stat`; no application, unit-test, specification,
UI-guidance or Git state was modified. The prior unapproved partial edit was inspected and corrected.

- Collection: `PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py --collect-only -q -p no:cacheprovider` → **392 collected**, exit 0.
- Focused collection: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py --collect-only -q -p no:cacheprovider -k 'ac046 or ac047 or ac048 or qpb149 or qpb150'` → **49/392 collected, 343 deselected**, exit 0.
- Design verifier: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tests/acceptance/survey_route_planner/verify_design.py` → exit 0; approved AC001–048/QPB149–150 operations/oracles, exact checkbox copy, canonical-site identity guards and M01–M17 NOT RUN markers passed. It executes no application behavior. A preceding system-Python attempt failed before the verifier with `ModuleNotFoundError: No module named 'fiona'`; the repository venv rerun is authoritative.
- Focused required-mode attempt: `PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen FIELDBUILD_REQUIRE_SRP_HARNESS=1 .venv/bin/python -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py -q -p no:cacheprovider --tb=line --basetemp /tmp/fieldbuild-srp-ios-followup -k 'ac046 or ac047 or ac048 or qpb149 or qpb150'` → **49 failed, 343 deselected** in 19.23 s, but every failure occurred before product observation because the sandbox denied the harness's localhost bind with `PermissionError: [Errno 1] Operation not permitted`. This run is environment evidence only, not an implementation verdict.
- The allowed-local-socket retry and isolated verbose probes produced no usable pytest completion summary and were stopped rather than treated as evidence. Static implementation inspection still identifies the expected pre-implementation gaps: the four AC046–048 operations and `generated_site_tabler_exclusion` are absent from the acceptance adapter; the current ORS checkbox remains the superseded long consent string; and `desktop_retention_readback` is absent. No expectation was weakened around those gaps.
- Manual selector: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/acceptance/survey_route_planner/test_survey_route_planner.py -q -p no:cacheprovider -k 'manual_qfield_device'` → **17 skipped, 375 deselected**, exit 0. M15–M17 and all prior M01–M14 are explicitly NOT RUN; no iOS/QField/device PASS is claimed.
- Acceptance-only `git diff --check` over the five changed files: exit 0, no output.
