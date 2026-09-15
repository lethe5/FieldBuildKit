# Survey route acceptance harness — DRAFT reconciliation, 2026-09-15

Specification checkpoint: `bd625d6` (approved service, key, CRS-defect and usability clarification). The earlier adapter
contract and tests remain approved at `ed8ac81`; this reconciliation is **DRAFT pending explicit
user acceptance-artifact approval**. It is an observation/test seam, not a new backend, file
format, application API, or product behavior.

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

Route snapshots expose `route_id`, `name`, `created_at` (ISO-8601), `backend`, `status`, `start`,
`end` (WGS84 lon/lat arrays), `distance_m`, `duration_s`, `revision`, `stops`; stops expose
`site_id` (string), `source_layer`, `sequence` (normalized one-based), `completed` (Boolean).
Optional `eta`, `eta_basis`, `legs`, `road_geometry` are `None` if unavailable; `eta` and
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
| `generate_plugin` | Generate portable project with routing, reports and identification enabled. Load/evaluate produced sidecar; collect asset closure, feature registration, panel state and errors. |
| `calculate` | Seed provided features; apply selection/scope/mapping. Site-bearing types default to `site/site_id/site_name`; Type 1 must receive explicit layer/id/name mapping and completion mapping is optional. Focus alone does not select. Press calculate. Return list, requests, candidate, preserved saved state and status. Defaults: valid GPS, return-to-start, deterministic successful transport. |
| `start` | Choose GPS/map/target/saved default at supplied coordinate; saved default is set, session destroyed and reloaded before calculation. Invalid GPS is missing, never replaced with zero. |
| `road_cost` | Supply directed matrix fixture from mocked road backend, capture real normalized optimizer request, inject requested valid optimizer order; return production candidate. Objective time and distance must select corresponding matrix. |
| `calculate_failure` | Start with saved active route, inject named transport/response defect, calculate. `off_road` exceeds an explicitly configured limit, not an invented default. Return candidate=None and unchanged saved/active state. |
| `result_roundtrip` | Inject the supplied raw VROOM 1.14 `optimizer_response` at the optimizer HTTP boundary and optional raw ORS GeoJSON `directions_response` at its HTTP boundary; calculate, save, destroy session, and reopen from actual storage. Extract job `steps[].arrival` as numeric relative seconds; do not accept a pre-normalized `route.eta`. Return independently decoded `saved` and `reloaded` snapshots. Missing optional timing/directions values stay absent. With `seed_saved=True`, ISO, partial, negative or non-finite job arrivals reject the candidate and preserve the independently reopened saved/active route. |
| `save_two_restart_move` | Apply supplied project settings, retain the key only in session, save two different named routes, select both, retain active second route, destroy session, physically move the entire folder, make the old location inaccessible, and reopen offline with the key removed. Only restart/select/load requests count in `requests`. Return independently decoded route/settings before/after, both selected IDs, old/new paths and session-key presence. |
| `storage_fault` | Seed valid route and update candidate. Inject failure at actual storage commit boundary: truncated write, full storage, newest copy corrupt, every readable store corrupt, or stale revision after independent update. Never hardcode two slots/JSON. For all-corrupt, immutable external last-good capture proves original data retained; explicit refusal is acceptable, fabricated recovery is not. Stale writer must not overwrite newer committed data. `published_partial` observes whether any consumer saw incomplete candidate. |
| `complete` | Seed 8 stops in ID order. Mark supplied IDs through the configured actual layer Boolean field, or through local route-stop UI when no completion field is mapped. Observe immediately, reopen and return `reloaded`. Only explicit Boolean `true` is complete; `false`, `NULL` and a missing field are incomplete. Dates/observation existence must not infer completion. |
| `completion_write_failure` | Seed a mapped Boolean field and nonempty saved/active route, then attempt one completion change through the real panel with a read-only layer or incompatible field type. Return independently reread source values, saved/active route and next-target state before/after. Display the write error and preserve all prior state. |
| `remaining` | Seed route in ID order, mark supplied completed IDs, then press remaining with supplied GPS. Observe request; `preview` stops before saving; `save` persists; `failure` injects backend timeout. Preserve completed records and route identity; successful save increases revision. No remaining stops must not call backend. |
| `reopen_navigate` | Reload saved supplied LineString offline, activate render path, navigate to provided destination/name with injected OS launcher Boolean result. Return exact launched URL, rendered geometry, message and any success claim. No claim about Naver's internal success from OS dispatch alone. |
| `passive_action` | Seed saved route with synthetic key retained only in session; perform action and inspect whole generated folder and full logs. `complete` changes actual completion; `restart` destroys session; `load` loads saved route. |
| `configured_calculate` | Seed a saved active route, apply each supplied setting through the production project/session settings path and press calculate. With `fresh_project=True`, omit endpoint fields and observe generated defaults. Migrate only the exact legacy defaults before dispatch and the next normal settings save; normalize one trailing separator; preserve every other custom/self-hosted URL. Dispatch registered `ors-vroom` and return `transport_settings`, full request records, independently decoded `persisted_settings`, diagnostics and saved/active before/after. Hosted defaults require a key before any request; custom/self-hosted endpoints permit no key and omit `Authorization`. The calculation remains an unsaved preview. Omitted road offset defaults to 1000 m. An unknown provider ID fails before registry transport dispatch and preserves the saved/active route. A session key may reach request headers only; it must not enter persisted settings, project files, logs or errors. |
| `builder_route_key` | Drive the real FieldBuild Kit route-key input and build action. Return the actual password echo mode, warning/consent disclosures, project publication result, generated `.qgs` path and independently decoded project variables/general settings. Consent embeds the key only in generated project variable `fieldbuild_route_api_key`; run the generated QField route calculation without injecting a session key and record project-variable use. Decline or blank input publishes without the variable and exposes session-only manual entry; when `manual_session_key` is supplied, calculate once and prove it disappears after restart. `cancel` and `generation_failure` publish no project and clean temporary plaintext. Optional desktop remember uses the existing app-local `credentials.enc` and is never reported as QField delivery. Return full logs/errors/reports/request records for leakage checks. |
| `draw` | Drive real geometry selector, vertices, finish control and per-target naming twice where two names supplied. Separate records and unique IDs; invalid/incomplete shapes are not published. Headless widget interaction is acceptable; do not bypass drawing with seed config. |
| `upload_build` | Read supplied real SHP/ZIP/GPKG through production upload path, generate actual GPKG and project in EPSG:4326, return gpkg_path, detected_type and generated project_geometry_type. Types normalize spelling but retain single/multi distinction. |
| `direct_build` | Drive drawing/direct-input generation with supplied WKT's vertices, then inspect generated metadata, actual geometry, feature/rtree IDs and project layer family. |
| `geometry_failure` | Supply a real mixed-family, empty, invalid-geometry, missing-CRS, invalid-CRS or untransformable source to production ingestion and representative request; no partial publication/network. When `seed_saved=True`, seed a saved active route first and return saved/active before/after observations so representative/CRS failure preservation is independently verified. |
| `geometry_roundtrip` | Produce real input dataset with supplied WKT records, invoke upload/build and read stored geometries. Return stored_geometries (GeoJSON mappings) and metadata/storage comparison. Same-family promotion is allowed, never part loss. |
| `representative` | Use supplied WKT+CRS, derive the representative through the production path and capture its external-request coordinate. Point uses the original coordinate; MultiPoint, LineString, MultiLineString, Polygon and MultiPolygon use one source-CRS centroid before WGS84 conversion. Return coordinate and original_before/after source bytes/geometry. No test policy switch may alter production behavior. |
| `generated_geometry_calculate` | Generate and validate a real FieldBuild Kit project containing the supplied valid geometry/CRS, load the unchanged generated route QML with the strict evaluator contract above, select its feature and press calculate. Return the evaluator trace, exact request coordinate, original geometry before/after, QML diagnostics and whether the generic CRS message appeared. Valid WGS84/projected inputs must reach transport. For a supplied missing/invalid CRS or transform fault, seed a nonempty saved/active route, execute the same generated runtime path, make no request and return a precise failure reason with unchanged route state. |
| `regression` | Build each survey type with and without fictional taxonomy, preserve representative pre-existing polygon fixture and a separate existing-user-project copy. Generate then relocate; validate sources/schema/relations, execute existing identification/report paths with synthetic response, read report row geometry/coordinates and KTSN presence. Type1 uses explicitly mapped inventory layer/ID; do not invent default site. Return actual before/after identities, non-site shapes, report rows and validation errors. |
| `panel_layout` | Load the actual generated expanded route panel at the requested viewport width, wait for bindings/layout to settle, render a screenshot, and return measured scroll-content, editable/selector field, label/help/error rectangles and horizontal-overflow state. Do not infer geometry from source text. |

Fault names and their semantics are literal parameters in the test module. `status_0`, network,
HTTP 401/429/500, timeout and truncated JSON are transport-boundary faults; malformed matrix,
unassigned, disconnected, off-road, duplicate/unknown/missing stop, negative distance,
nonfinite time, mismatched leg count and ISO/partial/negative/non-finite VROOM arrivals are actual
malformed provider payloads. Include synthetic
key in provider error text to verify redaction; do not repair bad input in the adapter.

## Verification boundary

O-SRP-003, O-SRP-005, O-SRP-006 and O-SRP-007 are resolved by approved checkpoint `bd625d6`; centroid, Boolean
completion, Type 1 mapping, 1000 m offset and project-local setting cases are unconditional
conformance tests. O-SRP-002/004 still require real-version/device verification: automated
generated QML/JS and mocked external boundaries do not prove native QField FileUtils behavior,
atomicity, iOS/Android loading, real provider operation or Naver execution.
