# Survey route acceptance harness — approved AC-SRP-066 reconciliation over approved AC-SRP-063–065

**APPROVED TEST DESIGN (approval 2026-09-22):** the AC-SRP-066 focus/order extension
uses approved clarification checkpoint `cb8f2da`.

**APPROVED TEST DESIGN (approval 2026-09-22):** the two generated-QML operations and fresh-
build comparison below cover AC-SRP-063–065. Approved AC-SRP-061–062 and earlier harness contracts
remain unchanged except that D-SRP-064 supersedes the historical acknowledgement save gate.

**APPROVED TEST DESIGN (approval 2026-09-22):** AC-SRP-061 Matrix optional-diagnostic and
AC-SRP-062 desktop credential-store coverage is approved. Earlier approved/DRAFT statuses are preserved.

**APPROVED TEST DESIGN (approval 2026-09-21).** The AC-SRP-059 endpoint-snapping
acceptance baseline is approved. The reviewer correction below remains
**DRAFT TEST DESIGN — user approval required**.

**Current AC-SRP-049–058 status: DRAFT TEST DESIGN (2026-09-21).** The approved
AC-SRP-001–048 contract and history below remain preserved and are not reopened.

**DRAFT retained-suite reconciliation (2026-09-21).** Retained operations are interpreted under
approved D-SRP-050/053/056/058/059 and AC-SRP-055/057/058. This corrects stale test oracles only;
it adds no provenance journal, receipt, seal, canned result or application seam.

**APPROVED TEST DESIGN — supersession reconciliation (approval 2026-09-17).** This approved reconciliation changes only how
retained AC-SRP-019/022/024/031 tests consume existing observations under approved D-SRP-043/045,
FR-SRP-041/043 and AC-SRP-043/045. All approval history below remains preserved. No adapter or
driver change is part of this reconciliation.

The adapter contract originating at `ed8ac81`, the approved `bcd6ffc` baseline and its approved
workflow correction remain authority. The D-SRP-031–035 / FR-SRP-029–033 / AC-SRP-031–035
expectations remain approved. The evidence-provenance corrections in this file are
**APPROVED TEST DESIGN (approval 2026-09-16)**. They are an observation/test seam, not a new backend, file format,
application API, or product behavior.

The 2026-09-17 D-SRP-036–041 / FR-SRP-034–039 / NFR-SRP-004 / AC-SRP-036–041 additions below are
**APPROVED TEST DESIGN (approval 2026-09-17)**. They preserve every earlier operation and
observation. Actual QField, Android, iOS and Naver behavior remains user-run and **NOT RUN**.

This approved correction applies the approved supersessions to retained operations: provider settings
start collapsed, the shortened D-SRP-037 labels replace their longer predecessors, Android dispatch
uses the D-SRP-039 package intent, and user-entered later-stop completion is nonmutating under
D-SRP-040. It does not relax any observation provenance or AC-SRP-036–041 requirement.

The D-SRP-042–045 / FR-SRP-040–043 / NFR-SRP-005 / AC-SRP-042–045 / D-UI-SRP-007–010 additions were
approved on 2026-09-17. The evidence-provenance correction below is **APPROVED TEST DESIGN (approval 2026-09-17)**;
it changes no approved product meaning and does not change AC-SRP-001–041. M01–M14 remain user-run
**NOT RUN**.

## Entry point and isolation

Extend the existing `qfield_builder.acceptance_api` with:

```python
run_survey_route_acceptance(*, case: dict, work_dir: str) -> dict
```

Each call creates a disposable standalone project/session inside `work_dir`. The tests provide
scenario data; the adapter drives the **real generated plugin/controller and real build/upload/
drawing/report paths through the buttons and controls a user invokes**. It may inject only
external transport responses or faults, device inputs/launcher results, and storage-boundary
faults. Seed records are input fixtures, not returned evidence. It must not compute route ordering,
centroids, persistence, validation, completion, settings, UI counts or other business state itself;
it must not return canned constants keyed by operation or copy/recalculate expected values from
`case`. Any Python-to-QML/JS bridge is implementer-owned. Generated-script execution with mocked
QField objects is a contract test, not proof of native QField loading. Real QML loading evidence
must identify the actual runtime. No source-string matching or test-only reimplementation is
acceptable.

Use the current QGIS-free standalone generation path; no QGIS Desktop prerequisite or private
reference dataset. With `reference=True`, create/use a tiny fictional valid taxonomy fixture.
Identification transport returns the fictional scientific name `Synthetic species`. No live
network, credentials, device profiles or user-project mutation. Block accidental real transport.

Missing module or missing new function: explicit **unimplemented harness SKIP**, matching the
existing suite convention. Import failure inside an existing module, noncallable function,
missing output keys, adapter exception or assertion mismatch: **ERROR/FAIL**, never skip.
Set `FIELDBUILD_REQUIRE_SRP_HARNESS=1` for implementation/review gates so absence fails.
Do not introduce per-operation skips in a partially implemented adapter.

## Observation vocabulary

Returned dictionaries contain detached snapshots, not references that mutate later. Every panel,
button, HTTP, timer, storage-result and UI-diagnostic value below is observed from the production
generated path. It is never a fabricated constant or a test-side reconstruction of UI/product
state. `requests` is the actual intercepted routing-service HTTP request list **during the measured
action**; setup requests are captured separately. Passive windows cover the complete async action
and queued timer completion, using drained production tasks or a deterministic clock, not an
arbitrary short sleep.
For calculations, retain all backend wire requests as evidence. `submitted_ids`, `request_start`
and `optimizer_request` are normalized views decoded from those captured requests, never copied
from `case`. A provider may make multiple matrix/optimization/directions requests; exact count
is intentionally not prescribed. `optimizer_request` has `objective`, `cost_matrix`,
`return_to_start`. Backend response `backend_order` is injected only at the optimizer transport
boundary; production code must construct road-cost requests and consume/validate the response.
Tests do not demand a globally optimal route or run their own solver.

`ok`, `message`, `listed_ids`, `panel`, `availability`, `summary_counts`, `next_id`,
`loaded_features` are observations of actual controller/UI state after the real action control is
invoked. Messages and `qml_errors` are actual displayed/runtime diagnostics. Messages must explain
the problem in Korean; automated assertions check nonblank text, and manual review checks meaning.
`loaded_features` is a set of functions activated by the produced plugin, not strings found in QML.
`asset_paths` contains every transitive packaged route/report/identification asset path relative
to `project_dir`; `qml_errors` contains actual load/evaluation diagnostics. `panel` records edge,
collapsed row count, and enabled expanded controls normalized to the tokens in the test.
`selection_help` and `completion_help` are observations of rendered inline help and its bound
counts/mode, not summaries synthesized by the adapter. `content_rect`, field/label/help/error
rectangles, overflow state and `screenshot_path` come from a loaded generated panel after layout
settles at the requested viewport width.

`floating_selectors` records AC031's historical six-control subset by semantic ID from the loaded
generated-QML object tree. AC043's `final_floating_label_geometry` operation remains final authority
for the exact eight-control set. Each AC031 observation includes distinct stable control/label object IDs,
actual QML types, visible/enabled state, exact accessibility role/name/state, control/label/option/
validation rectangles, clipping, focus state and rendered style metrics. The ORS server URL
reference metrics are captured from its separate live object in the same state. Source constants,
semantic text tables, copied input values and synthesized visual signatures are not evidence.
`rendered_scope_rows` is the ordered list of actual visible layout items with object IDs and
coordinates; gaps are derived from adjacent bottom/top coordinates. `qml_scope_items` records the
real hidden guidance object's visibility and lack of a layout rectangle, while
`visible_layout_semantic_ids` enumerates the whole visible layout. Constant row-name/gap lists do
not satisfy the contract.

Candidate model and preflight evidence are separate captures. `candidate_model_capture` reads the
rendered target model after production refresh from the loaded-QML object tree and includes distinct
control/model object IDs, actual control rectangle, visible/enabled state and accessibility state.
`preflight_capture` invokes the production
calculation preflight, records its independently returned ordered candidate and submitted stable
IDs, and records zero transport requests. Their capture IDs differ. For transition states the same
two captures are repeated after each real selection/completion/scope/mapping event. The adapter may
not derive either capture from the other or from `case`.

`map_start_marker` snapshots include the current production start value and a complete enumeration
of every rendered map-canvas marker, with the canvas count, stable object ID, semantic role,
coordinate, visible text, accessible name, visibility and measured contrast. A panel/controller
pointer or a list containing only the expected start-marker object is insufficient. Map pan/zoom,
panel reopen, calculation and lifecycle actions drive the actual generated map/panel objects.
`write_capture` installs source-provider and route-storage commit observers before the first action,
closes them after the last action, lists every commit attempt, and independently hashes/decodes
source and route storage before/after. Constant empty write lists are not evidence.

Route snapshots expose `route_id`, `name`, `created_at` (ISO-8601), `backend`, `status`, `start`,
`end` (WGS84 lon/lat arrays), `distance_m`, `duration_s`, `revision`, `stops`; stops expose
`site_id` (string), `source_layer`, `sequence` (normalized one-based), `completed` (Boolean).
Optional `eta` and `eta_basis` are `None` if unavailable and occur together. New schema-2 routes always
expose complete `legs` and `road_geometry`; only legacy schema-1 snapshots may lack legs. `eta` and
`eta_basis` occur together. For `ors-vroom`, job-step VROOM `arrival` numbers become unchanged
relative seconds and `eta_basis` is `relative_seconds`; no current time or `created_at` is used to
invent an epoch. Associated availability flags must match actual UI disclosure.
`optimality_guaranteed` records whether the UI claims a proven optimum. Ordering/units are
normalized for assertion only; storage layout is unrestricted.

`saved_before/after`, `last_good_before/after`, `completed_before/after`, `uuid_before/after`,
`relations_before/after`, `non_site_geometry_before/after`, `legacy_polygon_before/after`,
`existing_user_project_before/after` are actual decoded records or bytes read independently
before and after operations. At least one nonempty baseline must be seeded for each comparison;
equal empty maps are not evidence. Preserve valid bytes/records outside the intended update.
Do not mask a rewrite of data through normalization that discards required fields.
`active_before/after` identifies the active saved route. `logs` includes emitted UI/runtime/
transport/file diagnostics, including failure logs; never include real secrets.
Whenever `seed_saved=True`, `seed_saved_provenance` must show that a nonempty route was created by
the production save action, committed to the returned project-relative storage path, independently
reopened, and selected active before the measured failure. Copying a seed fixture directly into an
`active_before` result is not acceptable.

`transport_settings` is decoded from the actual provider-registry dispatch and intercepted
external transport calls, including server and optimizer URLs, profile, timeout, road-offset,
objective and session key. It is never copied from the input settings object. `persisted_settings`
and `settings_before/after` are decoded independently from actual project-local storage after the
relevant save/restart/move. `session_key_present_after` observes session memory after restart.
Storage result snapshots are independently reopened from committed bytes, not echoed from the
candidate sent to the save action.

Every captured request exposes `kind` (`matrix`, `optimizer` or `directions`), `method`, exact
`url`, decoded `query`, `headers` and `body`. The same request cannot be represented by two kinds.
The adapter blocks real network access. It must preserve the actual generated URL and headers so
the tests can distinguish routing-base suffix construction from a complete optimizer endpoint and
prove that a key appears only as the `Authorization` header value.

For `generated_geometry_calculate`, the supplied evaluator contract is a strict QField-shaped
surface for QML's `ExpressionEvaluator`, backed by the documented `QfExpressionEvaluator`: only
the listed writable properties exist, dynamic properties are rejected, and only `evaluate()` and
`evaluate(expressionText)` are invokable. The adapter executes the generated route QML unchanged
against this strict object and records property writes and each expression/arity. It must not add
aliases such as `currentFeature`, `currentLayer`, `expression` or `evaluateExpression`. Executed
representative expressions must use QGIS-supported centroid/transform/x/y operations and must not
use the unsupported `geom_to_geojson` function. This is a QField-shaped contract run, not native
QField evidence.

## Scenarios (exact `operation` values)

| Operation | Required driving steps and returned evidence |
| --- | --- |
| `generate_plugin` | Generate portable project with routing, reports and identification enabled. Load/evaluate produced sidecar; collect asset closure, feature registration, panel state and errors. `panel.control_objects` comes from stable loaded-QML object identity and includes semantic ID, object ID, QML type and actual visible/enabled state; matching legacy text is not control-presence evidence. After expanding the main route panel without expanding `API URL/키 설정`, the provider-setting child must be present and enabled but hidden; target/result/save/load controls remain visible. |
| `calculate` | Seed provided features; apply selection/scope/mapping. Site-bearing types default to `site/site_id/site_name`; Type 1 must receive explicit layer/id/name mapping and completion mapping is optional. Focus alone does not select. Press calculate. Return list, requests, candidate, preserved saved state and status. Defaults: valid GPS, return-to-start, deterministic successful transport. |
| `start` | Choose GPS/map/target/saved default at supplied coordinate; saved default is set, session destroyed and reloaded before calculation. Invalid GPS is missing, never replaced with zero. |
| `road_cost` | Supply directed matrix fixture from mocked road backend, capture real normalized optimizer request, inject requested valid optimizer order; return production candidate. Objective time and distance must select corresponding matrix. |
| `calculate_failure` | Start with saved active route, inject named transport/response defect, calculate. `off_road` exceeds an explicitly configured limit, not an invented default. Return candidate=None and unchanged saved/active state. |
| `result_roundtrip` | Inject the supplied raw VROOM 1.14 `optimizer_response` at the optimizer HTTP boundary and optional raw ORS GeoJSON `directions_response` at its HTTP boundary; calculate, save, destroy session, and reopen from actual storage. Extract job `steps[].arrival` as numeric relative seconds; do not accept a pre-normalized `route.eta`. Return independently decoded `saved` and `reloaded` snapshots. Missing optional timing/directions values stay absent. With `seed_saved=True`, ISO, partial, negative or non-finite job arrivals reject the candidate and preserve the independently reopened saved/active route. |
| `save_two_restart_move` | Apply supplied project settings, retain the key only in session, save two different named routes, select both, retain active second route, destroy session, physically move the entire folder, make the old location inaccessible, and reopen offline with the key removed. Only restart/select/load requests count in `requests`. Return independently decoded route/settings before/after, both selected IDs, old/new paths and session-key presence. |
| `storage_fault` | Seed valid route and update candidate. Inject failure at actual storage commit boundary: truncated write, full storage, newest copy corrupt, every readable store corrupt, or stale revision after independent update. Never hardcode two slots/JSON. For all-corrupt, immutable external last-good capture proves original data retained; explicit refusal is acceptable, fabricated recovery is not. Stale writer must not overwrite newer committed data. `published_partial` observes whether any consumer saw incomplete candidate. |
| `complete` | Seed 8 stops in ID order. Attempt supplied IDs in list order through the configured actual layer Boolean field, or through local route-stop UI when no completion field is mapped. Only the earliest incomplete row may change; a later-row attempt is nonmutating. Observe immediately, reopen and return `reloaded`. Only explicit Boolean `true` is complete; `false`, `NULL` and a missing field are incomplete. Dates/observation existence must not infer completion. |
| `completion_write_failure` | Seed a mapped Boolean field and nonempty saved/active route, then attempt one completion change through the real panel with a read-only layer or incompatible field type. Return independently reread source values, saved/active route and next-target state before/after. Display the write error and preserve all prior state. |
| `route_progression` | Consume the supplied raw schema-2 ORS directions response at the transport boundary, create/save the full route through production, independently reopen it, then perform completion/uncheck actions through mapped Boolean or route-local controls. A later incomplete stop attempted through the panel must leave the effective state unchanged; ordered checks advance the prefix, and unchecking an earlier stop may preserve a later true value as out-of-order. The raw fixture contains intermediate road vertices and route-level `properties.way_points`; segments contain no `way_points`. `route_seed_provenance` binds the captured response hash to the committed route ID/revision and actual project-relative storage path. Observe each effective completion set, consecutive prefix, next target, visit context, remaining leg sequences/metrics/geometry and bottom state. Optional restart, last-good recovery, offline reopen and physical folder move must independently reload the same derived state. No routing request is allowed after seeding. The superseded `remaining` operation/control must not be exposed. |
| `reopen_navigate` | Reload saved supplied LineString offline, activate render path, navigate to provided destination/name with injected platform and OS launcher Boolean result. Return every exact launched URL, rendered geometry, message and any success claim. Its retained AC012/025 use is Android-only: official package-bound intent and Google Play fallback. iOS navigation is superseded and observed directly through AC055's production `navigation.open` Apple Maps boundary. No claim about Android NAVER's internal success follows from OS dispatch alone. |
| `passive_action` | Seed saved route with synthetic key retained only in session; perform action and inspect whole generated folder and full logs. `complete` changes actual completion; `restart` destroys session; `load` loads saved route. |
| `configured_calculate` | Seed a saved active route, apply each supplied setting through the production project/session settings path and press calculate. With `fresh_project=True`, omit endpoint fields and observe generated defaults. Migrate only the exact legacy defaults before dispatch and the next normal settings save; normalize one trailing separator; preserve every other custom/self-hosted URL. Dispatch registered `ors-vroom` and return `transport_settings`, full request records, independently decoded `persisted_settings`, diagnostics and saved/active before/after. Hosted defaults require a key before any request; custom/self-hosted endpoints permit no key and omit `Authorization`. The calculation remains an unsaved preview. Omitted road offset defaults to 1000 m. An unknown provider ID fails before registry transport dispatch and preserves the saved/active route. A session key may reach request headers only; it must not enter persisted settings, project files, logs or errors. |
| `builder_route_key` | Drive the real FieldBuild Kit route-key input and build action. Return the actual password echo mode plus the real Step 7 widget observations, project publication result, generated `.qgs` path and independently decoded project variables/general settings. Retained AC019 reads the warning/consent widget text and requires D-SRP-045's complete exact copy; a phrase-fragment `warning_disclosures` parser is not acceptance evidence. Consent embeds the key only in generated project variable `fieldbuild_route_api_key`; run the generated QField route calculation without injecting a session key and record project-variable use. Decline or blank input publishes without the variable and exposes session-only manual entry; when `manual_session_key` is supplied, calculate once and prove it disappears after restart. `cancel` and `generation_failure` publish no project and clean temporary plaintext. Optional desktop remember uses the existing app-local `credentials.enc` and is never reported as QField delivery. Return full logs/errors/reports/request records for leakage checks. |
| `draw` | Drive real geometry selector, vertices, finish control and per-target naming twice where two names supplied. Separate records and unique IDs; invalid/incomplete shapes are not published. Headless widget interaction is acceptable; do not bypass drawing with seed config. |
| `upload_build` | Read supplied real SHP/ZIP/GPKG through production upload path, generate actual GPKG and project in EPSG:4326, return gpkg_path, detected_type and generated project_geometry_type. Types normalize spelling but retain single/multi distinction. |
| `direct_build` | Drive drawing/direct-input generation with supplied WKT's vertices, then inspect generated metadata, actual geometry, feature/rtree IDs and project layer family. |
| `geometry_failure` | Supply a real mixed-family, empty, invalid-geometry, missing-CRS, invalid-CRS or untransformable source to production ingestion and representative request; no partial publication/network. When `seed_saved=True`, first create a nonempty route through the production calculate/save action, independently reopen it from actual storage, select it active, and return `seed_saved_provenance` plus saved/active before/after observations. |
| `geometry_roundtrip` | Produce real input dataset with supplied WKT records, invoke upload/build and read stored geometries. Return stored_geometries (GeoJSON mappings) and metadata/storage comparison. Same-family promotion is allowed, never part loss. |
| `representative` | Use supplied WKT+CRS, derive the representative through the production path and capture its external-request coordinate. Point uses the original coordinate; MultiPoint, LineString, MultiLineString, Polygon and MultiPolygon use one source-CRS centroid before WGS84 conversion. Return coordinate and original_before/after source bytes/geometry. No test policy switch may alter production behavior. |
| `generated_geometry_calculate` | Materialize the supplied WKT+CRS as a real one-feature vector source, drive the normal FieldBuild Kit generation path to a distinct GPKG and QGS project, load the unchanged generated route QML, select the feature from that generated project layer and press calculate. `generated_geometry_provenance` returns the three actual paths, generated layer name, supplied WKT hash/CRS and confirms the calculation feature came from the generated project layer with no fixture-feature injection. Tests independently reopen both source and GPKG and parse the QGS datasource. Return the evaluator trace, exact request coordinate, original geometry before/after, QML diagnostics and whether the generic CRS message appeared. Valid WGS84/projected inputs must reach transport. When raw optimizer/directions responses and `save_and_reopen` are supplied, run the same production calculation through provider validation and storage, returning submitted/order IDs, provider validity and the independently reopened route. For a supplied missing/invalid CRS or transform fault, create and independently reopen a nonempty saved/active baseline first, execute the same generated runtime path, make no request and return a precise failure reason with unchanged route state and baseline provenance. |
| `regression` | Build each survey type with and without fictional taxonomy, preserve representative pre-existing polygon fixture and a separate existing-user-project copy. Generate then relocate; validate sources/schema/relations, execute existing identification/report paths with synthetic response, read report row geometry/coordinates and KTSN presence. Type1 uses explicitly mapped inventory layer/ID; do not invent default site. Return actual before/after identities, non-site shapes, report rows and validation errors. |
| `panel_layout` | Load the actual generated expanded route panel at the requested viewport width and requested empty/value/focus/error selector state, wait for bindings/layout to settle, render a screenshot, and return measured scroll-content, editable/selector field, label/help/error rectangles and horizontal-overflow state. When requested, traverse the loaded generated-QML object tree and observe AC031's historical six-control subset plus the separate ORS server URL reference object: stable object IDs/types, visible/enabled/focus state, accessibility role/name/state, actual rectangles and rendered style metrics. `separate_label_rows` is interpreted only for those six control labels; unrelated action-button text is outside that field's AC031 assertion. The legacy full-rectangle `label_in_control` Boolean is not an oracle because AC043 requires the label center to straddle the top outline. `label_clipped` currently reuses that containment rule and is a known false-positive adapter observation. `validation_text_rect` currently copies the first global visible validation rectangle to every control and is not per-control evidence. Retained AC031 consumes neither defective field; this approved reconciliation does not modify the adapter. AC043 independently enforces exact outline geometry, per-control live validation collision, live truncation/clipping state and no separate row for all eight final controls. Do not infer or copy geometry, style or accessibility from source text, constants or `case`. |
| `project_dropdowns` | Create the supplied actual vector layers in layer-tree/provider order, open the generated panel and drive the listed reopen/layer/schema/preflight actions. Return observed layer options `{label, layer_id, source_name}`, stored stable IDs, provider-order actual field names, selected values, validation/enabled state and the refresh triggers emitted by production. Duplicate aliases, removed IDs and schema changes are fixture state, not adapter decisions. |
| `route_workflow_ui` | Load the generated panel at the requested width, select the real start mode, scope and actual project features, then observe exact labels/guidance, including saved-route dropdown `저장 경로 불러오기`, conditional control visibility, target option label/value pairs, stale-target handling, wrap rectangles and overflow. The editable route-name field remains `저장할 경로 이름`. Enumerate every visible row after scope from the live layout with object ID and coordinates, and independently record the hidden guidance object's visibility/layout rect. Candidate observation captures the rendered target model, then separately invokes production calculation preflight with transport blocked and captures its submitted IDs/order; distinct capture IDs and the real event order prove the model was not reused as preflight evidence. QField selection, completion, scope and mapping transitions drive their real refresh triggers; valid selected IDs are preserved and stale IDs are cleared before required-target validation. |
| `storage_feedback` | Save a default start or named route through its real control, optionally fault the commit boundary, and independently reopen committed storage. Return the exact user feedback and exact committed project-relative path. A success path must resolve to an existing file inside `project_dir`; failure must emit no success. Capture all diagnostics for synthetic-secret leakage checks. |
| `schema2_roundtrip` | Calculate from the retained raw schema-2-shaped ORS optimizer/directions fixture, validate and atomically save the resulting explicit mixed route as schema 3, then restart and independently reopen it. ORS input follows the documented GeoJSON contract: route-level `feature.properties.way_points`, segments without `way_points`, and full LineString geometry. Slice each vehicle leg inclusively between consecutive route-level indexes. Return the full document/route, candidate, provider-valid flag, actual error category/reference/stage and old saved/active state. AC026 malformed directions payloads are constructed entirely in the test module by mutating route-level `properties.way_points`, top-level `geometry`, or documented segment metrics/count; the adapter receives no `fault` selector. `fault_provenance` records the captured-response path/hash and proves segment-level `way_points` were absent. Malformed optimizer/directions payloads are supplied raw and are never repaired by the adapter. `client_processing_fault=after_provider_validation:leg_mapping` is the single forced local-failure seam and may fire only after the unchanged payload passes provider validation. After save, drive complete/uncheck/toggle/load and return immutable full-route snapshots plus requests limited to those actions. Provider totals may be adjusted to exercise the `max(1 unit, 0.5%)` boundary; canonical saved totals come from ordered immutable legs. Separate legacy schema-1/2 reads remain read-only fixtures. |
| `map_start_marker` | Load the generated panel and live map, select map-start mode, capture supplied map centers through the real control, and drive pan/zoom, recapture, panel collapse/reopen, calculation success/failure, mode change, clear/invalidate and project close actions. Traverse the whole canvas marker collection after every action and return its count plus every marker's object identity, role, coordinate, visible text, accessible name, visibility and measured contrast. Install actual source-provider and route-storage commit observers before the first action and return their complete attempt logs plus independent before/after storage snapshots in `write_capture`; a panel/controller pointer or constant empty lists are invalid. A transform fault is injected only at the coordinate-transform boundary and must leave the prior valid start/marker intact. |
| `completion_overlay` | Complete/uncheck/recomplete one actual Point, LineString or Polygon feature through mapped or route-local state, restart and load. Return normalized rendered overlays, check/text state, source renderer and source bytes before/after. Overlay observations come from the production map-item/render path, not QML source strings. |
| `metric_display` | Render an active and no-route bottom bar from supplied metric inputs and return the visible formatted strings. |
| `route_line_toggle` | Create two saved routes and a separate project, turn the generated route-line control off, switch route, reopen panel, restart and move the folder with its settings while offline. Return actual overlay visibility, project-scoped preference storage path, completed overlay/source/full-route snapshots and action-window requests. |
| `legacy_route` | Materialize supplied schema-1, schema-2 or future-schema bytes, then load offline or explicitly invoke full calculate-and-save. Return independently read bytes/documents, visible legacy totals/line/stops/unavailable state, inferred legs, writes and requests. Load never repairs/splits/writes; only the explicit mixed calculation may issue requests and publish schema 3 with normal revision semantics. Settings-only legacy upgrades remain capped at schema 2. Schema 4+ remains byte-preserved and rejected. |

Transport fault names and their semantics are literal parameters in the test module. `status_0`, network,
HTTP 401/429/500, timeout and truncated JSON are transport-boundary faults; malformed matrix,
unassigned, disconnected, off-road, duplicate/unknown/missing stop, negative distance,
nonfinite time, mismatched leg count and ISO/partial/negative/non-finite VROOM arrivals are actual
malformed provider payloads. Include synthetic
key in provider error text to verify redaction; do not repair bad input in the adapter.

For AC-SRP-026, every directions defect is a raw response already mutated by the test module.
`missing_leg` removes `features[0].properties.segments[1]`; `out_of_order_leg` changes
route-level `features[0].properties.way_points[2]`; negative/nonfinite leg faults change the
corresponding segment distance/duration; invalid/non-WGS84 geometry changes top-level
`features[0].geometry`; mismatched count shortens route-level `properties.way_points`. No fixture,
driver or adapter may add, read or mutate `segments[].way_points`.

For AC-SRP-035, optimizer order faults are missing, duplicate, unknown and unassigned job IDs.
Directions faults are missing/duplicate/out-of-range route-level waypoint indexes, missing segment,
invalid top-level geometry, invalid/non-finite/negative segment metric and out-of-tolerance summary.
Provider failures expose the actual provider-response category and affected target ID, waypoint,
field or one-based leg. A contract-valid payload followed by the explicit forced local seam exposes
the distinct client-processing category, `leg_mapping` stage and retry guidance. Both paths preserve
the last-good saved/active route and redact the synthetic key outside captured Authorization headers.

### 2026-09-17 follow-up operations

These operations extend the same entry point. Their observations must come from production-generated
QML/project assets and independently reopened files. Source-text matches, expected values copied from
`case`, adapter-calculated UI state, and canned per-operation dictionaries are invalid evidence.

| Operation | Required driving steps and returned evidence |
| --- | --- |
| `candidate_name_save` | Create a real candidate through the captured optimizer/directions boundaries, then drive focus, text changes and save through the generated panel. Snapshot the detached candidate, base revision, calculation inputs and request/write capture after every action. Recoverable blank-name/validation/I/O faults are injected only at their real boundary; a corrected retry uses the same candidate. A calculation-input change is stale. A settings-only `show_route_line` revision change preserves the candidate and refreshes its base revision under D-SRP-059/AC058. Saved/reloaded routes and the actual committed relative path come from storage readback. |
| `followup_panel_ui` | Load the actual generated panel at 320/1024 px in empty/value/focus/error/disabled states, render a screenshot and traverse the live QML object tree. Return all seven controls with raw control/label/value/indicator/error rectangles, kind, outline/notch/font/padding metrics, stable object identity, exact accessibility name/role/state and stored values before/after. Do not return a precomputed pass/signature. |
| `settings_disclosure` | Start a new generated-panel session, observe initial disclosure state, then expand/collapse/re-expand through its real control. Return rendered labels/masking/accessibility state, preserved input values and complete request/storage-write captures; toggling must be passive. |
| `settings_key_provenance` | For manual input, enter the synthetic key into the masked generated panel and restart the app session. For project provenance, build with plaintext consent, independently parse the generated `.qgs` project variable, then open/restart the panel. Return the source message, warning/masking observations and actual post-restart key source without exposing the value in UI/diagnostics. |
| `settings_snapshot_save` | Save through `서버 설정 저장 (키 제외)` using the production two-slot repository. Independently read the committed A/B file(s), route and settings, and report actual project scope/path. Capture the session key and objective before save but prove neither exists in readback settings. A commit fault preserves the independently captured last-good bytes and session key and emits no success treatment. |
| `platform_naver_dispatch` | Superseded retained operation; it is no longer acceptance evidence because its generated-panel click label and iOS NAVER behavior predate D-SRP-056. AC039/055 instead call production `navigation.open` directly with an opener spy. Android still requires the exact package-bound NAVER intent and Google Play fallback; iOS requires the exact Apple Maps HTTPS URL once and no fallback. |
| `ordered_completion_checklist` | Seed a real schema-2 route from the raw directions fixture, render the generated checklist, and drive blocked/allowed checks, uncheck and external Boolean refresh. Return every row's enabled/checked/accessibility/reason/state text, next-stop feedback, source/write/overlay/revision/metrics/geometry snapshots and per-action routing requests. A blocked later row performs no write. `순서 밖 완료` and prefix-derived remaining state come from production after the actual event. |
| `generated_site_style` | Materialize the requested Point/LineString/Polygon and names through the normal generation path. Return source/GPKG/QGS paths, independently reread source features/renderer contract, parsed generated renderer/label configuration and actual light/dark rendering observations. Label observations enumerate real rendered labels and inert activation results; empty/null records create no artifact. Route/completion/start styles come from the same rendered project when requested. |

### 2026-09-17 device-defect follow-up operations — APPROVED TEST DESIGN evidence correction

These operations return observations from real loaded controls or normal generated artifacts. They
must never report OS soft-keyboard opening or QField map-canvas labels as automated PASS evidence.

| Operation | Required driving steps and returned evidence |
| --- | --- |
| `route_name_text_input_proxy` | Generate and calculate a real candidate, locate the loaded route-name QML control, and run separate body and label/notch-overlap cases. Deliver each pointer event through the window hit-test path. Record focus/caret immediately after delivery, before any other API call, together with target-region geometry, hit/focused object IDs and an explicit recovery-call log. `forceActiveFocus`, `requestActivate`, direct focus assignment or equivalent recovery is forbidden; the log must stay empty and a failed touch remains failed. Only after observed focus may the driver send Korean/Latin IME commit, selection, deletion and replacement events. Capture control text, candidate, base revision and provider requests after every event; save through the real control and independently reopen the trimmed name. `claims.os_soft_keyboard_opened` stays absent/false and `evidence_scope` identifies an automatic wiring proxy. |
| `final_floating_label_geometry` | Load the unchanged generated QML at 320/1024 px for empty/value/focus/disabled/error states. Traverse the live object tree for the eight exact controls and identify their common component. Return distinct control/label IDs and raw control/label/notch/value/indicator rectangles. Observe the top outline either from the live background object's verifiable border rectangle/width or from image edge detection; call it `top_outline_observation`, not a painted-border claim. Error state must return the actual visible validation object's ID and rectangle; other states return no error rectangle. Before and after each state, independently reread stored values from the repository and the selected route ID from the live model, with distinct observation IDs and sources. Copied dictionaries, constant source labels, synthesized error rectangles and separate label rows are invalid. |
| `generated_site_label_contract` | Drive the normal FieldBuild Kit build path for all six geometry families without QGS/GPKG post-editing. The LineString fixture includes two same-name features sharing an endpoint. Return paths, hashes and generated layer ID/name so tests independently reopen the artifacts. XML configuration must disable both `labelPerPart` and `mergeLines`; this prevents multipart duplication and same-text connected-feature merging before labeling. The test independently validates the exact generated expression structure and feature rows. Do not return Python-reimplemented expression results as QGIS observations. Probe PyQGIS and record probe provenance: when available, load the QGS and use `QgsProject`, `QgsPalLayerSettings` and `QgsExpression` for configuration and per-feature results; when unavailable, return `available=false`, the actual diagnostic and an empty runtime-claims list. Both paths remain configuration evidence; target QField rendering stays M14 NOT RUN. |
| `builder_step7_route_credentials` | Retained AC-SRP-045-only UI seam: expose real Step 7 widget order, focus chain, masking, exact copy and actual-or-unavailable accessibility observations for one representative state. Credential destination combinations belong to the direct boundary below. |
| `builder_route_credentials_boundary` | Without loading QML, a wizard page, or a local socket, submit blank+both-checked, non-blank+neither, consent-only, remember-only and both directly through the production builder/credential-store boundary. Return only the two exact checkbox strings, build result, parsed QGS variables, artifact paths, redacted diagnostics, and isolated encrypted-store readback (`present`, provenance, plaintext-at-rest boolean). Never return the key. Only non-blank consent may create one QGS project-variable occurrence; only non-blank remember may create encrypted desktop retention. |

### 2026-09-18 iOS/QPB evidence-boundary correction — APPROVED TEST DESIGN (approval 2026-09-18)

No new route-panel or symbol harness operation is required. AC-SRP-046/047 use source-level stable
structure checks only; M15/M16 own rendered contrast, painted clearance and tap-region verdicts.
AC-SRP-048 executes production `controller.js` directly with an injected clock/timezone and in-memory
repository; the retained AC-SRP-042 control proxy covers editable/input-method wiring, while M17 owns
OS soft-keyboard evidence. AC-QPB-150 calls the production symbol router directly and parses a normal
generated QGS after relocation. The superseded five operations are intentionally absent.

For settings/navigation constants, the test module supplies independent exact oracles; the adapter
must expose captured calls/files rather than validate them. `requests` always means routing-provider
requests, while `launcher_calls` records OS URL dispatch and storage observers record file commits.

## Verification boundary

O-SRP-003, O-SRP-005, O-SRP-006 and O-SRP-007 are resolved by approved checkpoint `bd625d6`; centroid, Boolean
completion, Type 1 mapping, 1000 m offset and project-local setting cases are unconditional
conformance tests. O-SRP-002/004 still require real-version/device verification: automated
generated QML/JS and mocked external boundaries do not prove native QField FileUtils behavior,
atomicity, iOS/Android loading, real provider operation or Naver execution.
Likewise, desktop/headless input and generated QGS/QGIS labeling configuration do not prove that a
mobile OS opened its soft keyboard or that QField drew a readable label/halo. Those verdicts stay
with M11–M14 until separately observed on each applicable device/platform.

## 2026-09-16 observation additions

All file paths returned for UI feedback are exact slash-normalized paths relative to `project_dir`,
paired with the independently observed committed path and filename. They may not be synthesized
from a configured route name. `launcher_calls` records every actual `Qt.openUrlExternally` call in
order with URL, Boolean return and call surface. A true return means only that the OS accepted the
open request; `claims` separately records and must not invent app launch, destination acceptance or
navigation start. Mobile fallback records its platform and package/App Store identifier.

Schema-2 legs expose `sequence`, `from`, `to`, finite non-negative distance/time and WGS84 GeoJSON
LineString. `from`/`to` is literal `start` or `{layer_id, site_id}`. Full-route immutable snapshots
include document schema, route revision, totals, ordered legs and full display geometry. Progression
snapshots include prefix length, remaining leg sequence, visit context, metrics/geometry, completed
IDs, check/text and overlay. Map overlay style is normalized only after rendering: Point/LineString
use `#1565C0` at opacity 1; Polygon uses that color at fill opacity .35 and outline opacity 1.
Renderer/source comparisons use nonempty bytes or full decoded records.

The old `remaining` operation is deliberately removed from this contract. AC-SRP-011 remains in
historical traceability, but D-SRP-023/FR-SRP-026 require no remaining-calculation control and zero
routing requests for completion, uncheck, toggle, restart or load.

## DRAFT AC-SRP-049–058 direct-observation redesign (2026-09-21)

> DRAFT correction (2026-09-21; user approval required): a matrix request is observed as
> `origin-validation` only when it explicitly selects one source and one destination from two
> identical immutable-origin locations (`sources:[0]`, `destinations:[1]`). Location-count
> heuristics are not evidence. The raw request and raw response must expose the finite 1x1
> duration and both resolved endpoint locations. Resolved provider coordinates may be compared
> for validation but must not replace the original start in any later request or saved route.
> Malformed endpoint/metric fixtures are provider responses, not adapter policy switches.

This section supersedes only the mixed-route callback-journal design that followed the approved
AC-SRP-001–048 baseline. No provenance journal, causal lineage, event core, receipt, seal,
field-origin table, callback ancestry, result-source metadata or completed-result capture is an
acceptance boundary.

The smallest sufficient boundaries are:

1. Node loads the repository copies of backend.js, controller.js, repository.js and navigation.js
   with vm.runInContext and calls their real functions. Spies exist only at HTTP, file, clock,
   feature, and OS-launcher boundaries. No product algorithm or expected output dictionary is
   copied into the harness.
2. A disposable 127.0.0.1 HTTP server records actual method, path, headers and parsed body.
   Responses inject provider success/failure only. Assertions use those records and real JS
   return/errors. The server is in memory; request/response bodies and credentials are never written.
3. Repository checks use real disposable slot files. They compare bytes and file lists before/after,
   move the project folder, and start a separate Node process for cold reopen. Fixture corruption is
   written outside the product and checksums are recomputed by the real repository.checksum.
4. QML checks execute generated RoutePanel.qml and read actual object properties, signal effects,
   Repeater.itemAt(index) delegates and QAccessible interfaces. A mirrored proxy model or canned
   presentation dictionary is not evidence.
5. navigation.open is called directly with an opener spy. Assertions cover exact URLs, call counts,
   errors and honest OS-request-only status. A minimal controller integration may verify state
   propagation; URL construction remains owned by navigation.js.
6. Static checks are limited to forbidden product test seams and embedded synthetic secrets.
   They do not authenticate runtime observations or require a journal implementation.

The automated API returns ordinary raw observations only: production return/error values, HTTP
records, slot bytes/file names, QML properties/interfaces, and launcher calls. Tests derive their
expectations independently from the approved specification. File-wide secret scans cover every
disposable generated project and storage file.

For `mixed_route_presentation`, install the existing real provider-dispatch and file-write
observers before setup and retain their raw callback collections. After the production save/reopen
setup, record the current collection lengths as the passive-window start indexes; do not clear the
collections. Invoke every requested preview/detail/legend or visit-reload action through its real
product operation. Return the raw post-index provider/write slices, their lengths, and one
`action_windows` row per requested action with before/after lengths and whether that product
operation completed. Literal empty arrays, fabricated boundary dictionaries, a controller pointer,
or action names copied without invoking the operation are invalid evidence. This is an ordinary
counter/slice observation, not a journal, span, receipt, seal or completed-result protocol.

AC056 first creates three schema-3 routes through production save: mapped/ors-foot-hiking,
exact_zero/exact_zero and unmapped_estimate/straight_line_lower_bound_m. At least one is active and
at least one inactive. Cold offline reopen after a folder move must roundtrip all three. The
corruption matrix runs against both an active and inactive schema-3 route and includes missing and
blank `layer_id`, `site_id` and `metric_source`; layer and site identity mismatch; unknown mode and
source; and all six cross-pairings outside the three allowed mode/source pairs. Recovery returns raw
corrupt and last-good slot bytes before/after plus actual provider/write counters. Every corrupt
case must select the unchanged last-good document without repair, request or write.

AC057 separately mutates a top-level schema-3 document's retained legacy route to
`route_schema: 1` while leaving its schema-2-only `legs` field present. Load/recovery must reject
that exact marker/content contradiction, preserve corrupt and last-good slot bytes byte-for-byte,
and make zero provider or storage-write attempts.

AC-SRP-049–058 retain their full approved semantics: safe bounded provider failure details;
single-batch access snap and source immutability; mapped/exact-zero/unmapped walking; schema-3
visits, metric provenance and totals; request ordering/privacy/write absence; platform navigation;
active and inactive visit validation; legacy/mixed storage compatibility; and persistent
route-line preference. M01–M21 remain user-run and **NOT RUN** until recorded on the named target.

## APPROVED AC-SRP-059 baseline and reviewer correction (approved 2026-09-22)

This additive contract uses the same production-JavaScript, localhost HTTP, real slot-file and loaded-QML
boundaries above. It does not add a provenance journal, duplicate the ORS parser, or infer provider behavior.

- The valid response is a GeoJSON FeatureCollection whose `features` member is an actual Array containing
  exactly one GeoJSON Feature with a finite WGS84 LineString, one segment, finite non-negative
  summary/segment metrics and route-level `properties.way_points=[0,last]`. Both provider geometry endpoints
  are independently more than 1 m from the immutable requested access/source coordinates, and the provider
  distance is independently shorter than requested access-to-source geodesic distance. HTTP records and the
  production return value prove acceptance as `mapped` / `ors-foot-hiking` without a connector or fallback.
- Two production controller saves create the same snapped contract as active and inactive schema-3 routes.
  A separate Node process reopens the real files only after the provider server has closed and the project
  folder has moved. Assertions compare the complete document and exact requested coordinates, provider
  metrics, outbound geometry, exact reversed return geometry, schema, mode and metric source.
- `controller_failure` seeds a last-good route through the production repository, then records the production
  controller snapshot/candidate and actual provider/file counters around one calculation. Raw response mutations
  cover missing/non-array/wrong-length/non-integer/non-increasing/non-covering `way_points`, multiple segments or
  features, an object-shaped `features` value with numeric key `0` and `length: 1`, invalid geometry/summary/segment,
  and distance/duration mismatch outside D-SRP-028 tolerance. Every
  case must stop after walking directions, preserve the last-good snapshot/candidate, and make zero post-seed
  writes, fallback requests, vehicle matrix/optimizer/directions requests or retries.
- `mixed_route_presentation` receives the snapped fixture only at its provider boundary and returns raw loaded-QML
  observations. `snapped_endpoint_observation.access_marker_observations` enumerates every access-marker QML
  object from `walkingItems`, including its real object identity/name and runtime `accessCoordinate` property.
  `source_feature_observations` enumerates the actual source provider feature(s), including provider layer/feature
  identity and geometry-derived coordinate. `walking_line_observations` enumerates every rendered walking-line QML
  object, including real object identity/name and runtime `coordinates` and `linePattern` properties.
  `visit_model_observation` returns the complete actual candidate-or-route `visits` array and names that runtime
  model source; `walking_totals_observation` returns the actual candidate walking totals or saved-route progress
  totals and names that runtime model source. The acceptance test derives connector count from the complete line
  enumeration and gap metric/time from exact leg-versus-total arithmetic. The harness must not echo fixture/source
  input coordinates into observations or return `synthetic_connector_count`, `gap_metric_or_duration_count`, or
  any other constant absence claim. Actual source-write callback slices remain required.
  The later D-SRP-064/D-SRP-067 presentation supersedes the historical three-object observation. Current
  evidence reads one live endpoint-gap object inside expanded details, including object identity, visible text
  and QAccessible name. Literal dictionaries assembled from input fixture values, source-text matching, or
  copied expected strings are invalid evidence.

M01–M21 remain **NOT RUN**. This automated contract does not claim live ORS snapping, native QField pixels,
screen-reader speech, or device interaction.

## APPROVED AC-SRP-061–062 Matrix diagnostic and desktop credential-store extension (2026-09-22)

This extension is **APPROVED TEST DESIGN (approval 2026-09-22)**. It adds no application API. AC-SRP-061
reuses the existing direct production-JavaScript `backend`, `controller_flow`, and `controller_failure`
operations plus the disposable localhost transport. Raw Matrix response objects are varied only at the
provider boundary. `snapped_distance` is independently omitted or made present-invalid in origin
`sources[0]`, origin `destinations[0]`, and each vehicle `sources[]` row. A JSON numeric literal `1e309`
is used for the non-finite case so the response is syntactically valid JSON and the runtime receives a
non-finite Number. Success evidence is the production save/reopen snapshot and captured request sequence;
failure evidence is the production controller's unchanged snapshot/candidate, exact stage, actual request
cutoff, and zero post-seed write attempts. The test adapter must not default, calculate, or echo a missing
diagnostic.

AC-SRP-062 uses `qfield_builder.credential_store`'s public password/remember/readback API and
`qfield_builder.build.build_project()` directly. Platform inputs (`sys.platform`, `Path.home`, `APPDATA`),
the documented diagnostic override, and the credential-write fault are external-boundary injections. Every
writable path is below pytest's disposable `tmp_path`; no real user app-data path is opened. Tests may inspect
the resulting encrypted bytes, generated project tree, builder result/log/report surfaces, and actual Qt
password/accessibility observations, but never return or print a decrypted key. `FieldBuild Kit` and
`QField Project Builder` sibling trees are snapshotted byte-for-byte before and after normal store use.
Remember-off, blank and injected-store-failure builds must still publish without a credential file or
plaintext fallback. The diagnostic override must contain exactly one final `credentials.enc`; atomic temp
files may exist only transiently inside that same disposable directory and must be absent at observation.

## APPROVED unmapped-save generated-QML click correction (2026-09-22)

This correction is **APPROVED TEST DESIGN (approval 2026-09-22)**.

`unmapped_save_qml_click` must load the generated `RoutePanel.qml`, produce an unmapped candidate through
the existing HTTP fixture, scroll each named control into the live `ScrollView`, and deliver pointer events
to `unmappedAcknowledgement` and `saveRouteButton`. Direct controller acknowledgement or save invocation is
not evidence. Return raw control checked/enabled state, the current viewport intersection of `messageLabel`,
candidate before/after, real slot path/document, active route, saved-list/load state, and an independent panel
reopen readback. A write-boundary failure may be injected only at `FileUtils.writeFileContent`; it must return
the unchanged candidate and visible production error with no committed/listed route. The splice is
acceptance-only, reuses the canonical QML driver, and must fail closed when its exact insertion markers move.

### APPROVED acceptance-evidence observation-timing correction (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22)**. The approved click contract above remains unchanged.

The generated checkbox's `checked` state must be captured immediately after the real
`unmappedAcknowledgement` pointer click and before the save click or any successful independent panel reopen.
Reading that property from the pre-save control only after `open_panel()` has scheduled the old panel for
deletion is stale-object evidence and is not accepted. The verifier must enforce the ordering
acknowledgement click → checked-state capture → save click → independent reopen. All approved save,
persistence, feedback, failure-retention and exact-control expectations remain unchanged.

## APPROVED AC-SRP-063–065 result/save/deployment extension (2026-09-22)

Status: **APPROVED TEST DESIGN (approval 2026-09-22).** D-SRP-064 supersedes the preceding
acknowledgement-click contract as a current expectation; that prose is retained only as history.

`route_ui_simplification` loads the actual generated panel and returns candidate-none/invalid-mapping
disabled reasons; screen and QAccessible fallback-notice counts; every old acknowledgement-labelled
QObject count; default/expanded/collapsed detail text and endpoint-gap ancestry; candidate/payload,
provider/write and save-enabled snapshots around toggles; and real no-ack save/reopen evidence.

Stable generated-panel observation anchors are `saveDisabledReason`, `fallbackNotice`,
`routeDetailsDisclosure`, `routeDetailsContent`, and `saveStatus`. The disclosure's accessible name is
exact `상세 정보`. These anchors are not a new service API.

`save_outcome_visibility` production-saves a last-good route, calculates a second candidate, and drives
the actual `saveRouteButton` handler for success, blank name, stale input, repository revision conflict,
write false, readback mismatch and injected exception. It returns status geometry relative to the live
ScrollView, all visible QAccessible objects named by the final message, candidate and independent
repository snapshots, valid-slot bytes/revision, focus/name/disclosure state, request count and write
count. One QAccessible `StatusBar` is the announcement proxy, not proof of native speech.

AC-SRP-065 reuses the public desktop build flow and compares complete byte maps. The new output runtime
must equal source; the builder is never pointed at the pre-existing output; and `logs.builder_message`
must contain the exact D-SRP-066 disclosure once. The new driver contains no `acknowledgeUnmapped` call
or replacement acknowledgement helper. M22 stays skipped and **NOT RUN (`미검증`)**.

## APPROVED AC-SRP-066 disabled/focus/order extension (2026-09-22)

`save_outcome_visibility` uses a mixed candidate with expanded details. It records candidate, save-enabled
state and disabled-reason visibility immediately after the real handler returns, before draining queued work.
For success it then clears button focus to emulate allowed platform behavior; the final focus trace must show
no application restore or transfer. The generated runtime is also checked for a save-button focus-recovery API
occurrence so an already-focused no-op cannot hide a forbidden call.

The driver obtains visual group bounds from live items, QAccessible order from live accessible objects, and
Tab order from real key events. The applicable order is basic result, fallback notice, details disclosure,
expanded content, route name, save button, disabled reason, outcome status. It returns raw layout rectangles,
overlaps, truncation and overflow rather than a precomputed pass. The same operation exposes current AC053/059
marker, source-feature, provider-line, visit/totals, fallback-warning and single-details-gap observations.
M22 remains user-run and **NOT RUN (`미검증`)**.

## APPROVED AC-SRP-064/066 Qt observation-boundary correction (2026-09-23)

Status: **APPROVED TEST DESIGN (approval 2026-09-23).** The approved harness contracts above remain
unchanged except for these evidence-oracle corrections.

`save_outcome_visibility` must settle live QML geometry through bounded rendered frames, without a timed
sleep, before recording layout. It must then place `saveStatus` wholly outside the current Flickable
viewport and return an `outside` predicate derived from raw item/viewport coordinates. After the actual
save handler and queued reveal, it settles geometry again and returns the existing full-visibility result.

Focus observations must return the active item's object name, Qt class, accessible role and nearest
focusable-control identity. On successful disable/platform clear, only no active item or an unnamed item
with no focusable-control identity is admissible. A named item or any actual focusable control is an
application-visible transfer and must fail; generated save-button focus recovery remains forbidden.
Failure outcomes continue to retain `saveRouteButton`. All state, order, endpoint-detail and announcement
fields remain required.
