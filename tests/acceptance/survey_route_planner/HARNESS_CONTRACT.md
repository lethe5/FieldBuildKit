# Survey route acceptance harness — APPROVED, 2026-09-14

Specification checkpoint: `e382c77` (approved specification). This adapter contract and its tests
are **APPROVED by explicit user acceptance-artifact approval on 2026-09-14**. It is an observation/test seam,
not a new backend, file format, application API, or approved product behavior.

## Entry point and isolation

Extend the existing `qfield_builder.acceptance_api` with:

```python
run_survey_route_acceptance(*, case: dict, work_dir: str) -> dict
```

Each call creates a disposable standalone project/session inside `work_dir`. The tests provide
scenario data; the adapter drives the **real generated plugin/controller and real build/upload/
drawing/report paths**, injecting only external device inputs, transport responses and storage
faults. It must not compute route ordering, centroid, persistence, validation or business state
itself; it must not return canned expected output keyed by operation. Any Python-to-QML/JS bridge
is implementer-owned. Generated-script execution with mocked QField objects is a contract test,
not proof of native QField loading. Real QML loading evidence must identify the actual runtime.
No source-string matching or test-only reimplementation is acceptable.

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

Returned dictionaries contain detached snapshots, not references that mutate later.
`requests` is the actual intercepted routing-service request list **during the measured action**;
setup requests are captured separately. Passive windows cover the complete async action and
queued completion, using drained tasks or a deterministic clock, not an arbitrary short sleep.
For calculations, retain all backend wire requests as evidence. `submitted_ids`, `request_start`
and `optimizer_request` are normalized views decoded from those captured requests, never copied
from `case`. A provider may make multiple matrix/optimization/directions requests; exact count
is intentionally not prescribed. `optimizer_request` has `objective`, `cost_matrix`,
`return_to_start`. Backend response `backend_order` is injected only at the optimizer transport
boundary; production code must construct road-cost requests and consume/validate the response.
Tests do not demand a globally optimal route or run their own solver.

`ok`, `message`, `listed_ids`, `panel`, `availability`, `summary_counts`, `next_id`,
`loaded_features` are observations of actual controller/UI state. Messages must explain the
problem in Korean; automated assertions check nonblank text, and manual review checks meaning.
`loaded_features` is a set of functions activated by the produced plugin, not strings found in QML.
`asset_paths` contains every transitive packaged route/report/identification asset path relative
to `project_dir`; `qml_errors` contains actual load/evaluation diagnostics. `panel` records edge,
collapsed row count, and enabled expanded controls normalized to the tokens in the test.

Route snapshots expose `route_id`, `name`, `created_at` (ISO-8601), `backend`, `status`, `start`,
`end` (WGS84 lon/lat arrays), `distance_m`, `duration_s`, `revision`, `stops`; stops expose
`site_id` (string), `source_layer`, `sequence` (normalized one-based), `completed` (Boolean).
Optional `eta`, `legs`, `road_geometry` are `None` if unavailable; associated availability flags
must match actual UI disclosure. `optimality_guaranteed` records whether the UI claims a proven
optimum. Ordering/units are normalized for assertion only; storage layout is unrestricted.

`saved_before/after`, `last_good_before/after`, `completed_before/after`, `uuid_before/after`,
`relations_before/after`, `non_site_geometry_before/after`, `legacy_polygon_before/after`,
`existing_user_project_before/after` are actual decoded records or bytes read independently
before and after operations. At least one nonempty baseline must be seeded for each comparison;
equal empty maps are not evidence. Preserve valid bytes/records outside the intended update.
Do not mask a rewrite of data through normalization that discards required fields.
`active_before/after` identifies the active saved route. `logs` includes emitted UI/runtime/
transport/file diagnostics, including failure logs; never include real secrets.

## Scenarios (exact `operation` values)

| Operation | Required driving steps and returned evidence |
| --- | --- |
| `generate_plugin` | Generate portable project with routing, reports and identification enabled. Load/evaluate produced sidecar; collect asset closure, feature registration, panel state and errors. |
| `calculate` | Seed provided features; apply selection/scope/mapping (default site/site_id/site_name). Focus alone does not select. Press calculate. Return list, requests, candidate, preserved saved state and status. Defaults: valid GPS, return-to-start, deterministic successful transport. |
| `start` | Choose GPS/map/target/saved default at supplied coordinate; saved default is set, session destroyed and reloaded before calculation. Invalid GPS is missing, never replaced with zero. |
| `road_cost` | Supply directed matrix fixture from mocked road backend, capture real normalized optimizer request, inject requested valid optimizer order; return production candidate. Objective time and distance must select corresponding matrix. |
| `calculate_failure` | Start with saved active route, inject named transport/response defect, calculate. `off_road` exceeds an explicitly configured limit, not an invented default. Return candidate=None and unchanged saved/active state. |
| `result_roundtrip` | Supply response values through provider-normalized transport, calculate, save, destroy session, reopen from actual storage. Missing optional data stays absent. |
| `save_two_restart_move` | Save two different named routes, select both, retain active second route, destroy session, physically move entire folder, make old location inaccessible, reopen offline with key removed. Only restart/select/load requests count in `requests`. Return before/after, both selected IDs, old/new paths. |
| `storage_fault` | Seed valid route and update candidate. Inject failure at actual storage commit boundary: truncated write, full storage, newest copy corrupt, every readable store corrupt, or stale revision after independent update. Never hardcode two slots/JSON. For all-corrupt, immutable external last-good capture proves original data retained; explicit refusal is acceptable, fabricated recovery is not. Stale writer must not overwrite newer committed data. `published_partial` observes whether any consumer saw incomplete candidate. |
| `complete` | Seed 8 stops in ID order. Mark 0 and 2 through configured actual layer completion field or local route-stop UI. Observe immediately, reopen and ensure persistence. Route uses explicit Boolean completion fixture; dates/observation existence must not infer completion. |
| `remaining` | Seed route in ID order, mark supplied completed IDs, then press remaining with supplied GPS. Observe request; `preview` stops before saving; `save` persists; `failure` injects backend timeout. Preserve completed records and route identity; successful save increases revision. No remaining stops must not call backend. |
| `reopen_navigate` | Reload saved supplied LineString offline, activate render path, navigate to provided destination/name with injected OS launcher Boolean result. Return exact launched URL, rendered geometry, message and any success claim. No claim about Naver's internal success from OS dispatch alone. |
| `passive_action` | Seed saved route with synthetic key retained only in session; perform action and inspect whole generated folder and full logs. `complete` changes actual completion; `restart` destroys session; `load` loads saved route. |
| `configured_calculate` | Apply each setting through production settings path and calculate. Return effective settings observed at backend boundary and request evidence. Custom backend token names an injected test transport using the replaceable production backend interface, not a mandated provider. |
| `draw` | Drive real geometry selector, vertices, finish control and per-target naming twice where two names supplied. Separate records and unique IDs; invalid/incomplete shapes are not published. Headless widget interaction is acceptable; do not bypass drawing with seed config. |
| `upload_build` | Read supplied real SHP/ZIP/GPKG through production upload path, generate actual GPKG and project in EPSG:4326, return gpkg_path, detected_type and generated project_geometry_type. Types normalize spelling but retain single/multi distinction. |
| `direct_build` | Drive drawing/direct-input generation with supplied WKT's vertices, then inspect generated metadata, actual geometry, feature/rtree IDs and project layer family. |
| `geometry_failure` | Supply real mixed-family, empty, invalid or unknown-CRS source to production ingestion and representative request; no partial publication/network. Return published_features. |
| `geometry_roundtrip` | Produce real input dataset with supplied WKT records, invoke upload/build and read stored geometries. Return stored_geometries (GeoJSON mappings) and metadata/storage comparison. Same-family promotion is allowed, never part loss. |
| `representative` | Use supplied WKT+CRS, derive representative through production path and capture its external-request coordinate. Return coordinate and original_before/after source bytes/geometry. Candidate policy parameter labels the provisional oracle, it must not switch product behavior solely to pass a test. |
| `regression` | Build each survey type with and without fictional taxonomy, preserve representative pre-existing polygon fixture and a separate existing-user-project copy. Generate then relocate; validate sources/schema/relations, execute existing identification/report paths with synthetic response, read report row geometry/coordinates and KTSN presence. Type1 uses explicitly mapped inventory layer/ID; do not invent default site. Return actual before/after identities, non-site shapes, report rows and validation errors. |

Fault names and their semantics are literal parameters in the test module. `status_0`, network,
HTTP 401/429/500, timeout and truncated JSON are transport-boundary faults; malformed matrix,
unassigned, disconnected, off-road, duplicate/unknown/missing stop, negative distance,
nonfinite time and mismatched leg count are actual malformed provider payloads. Include synthetic
key in provider error text to verify redaction; do not repair bad input in the adapter.

## Unresolved policy boundary

O-SRP-002/004 do not block observable integration/persistence tests: chosen APIs/storage must
satisfy them and obtain real-version verification. O-SRP-003 still reserves source-CRS centroid
order and MultiPoint centroid. Numerical tests implement that **candidate oracle**, not a new
approved requirement: set `FIELDBUILD_SRP_CENTROID_POLICY=source_crs_centroid` to run policy-dependent cases as characterization, report separately and obtain policy closure
before using them as final conformance gate. O-SRP-005 NULL semantics, Type1 default and settings
portability need clarification; use explicit Boolean mapping, explicit Type1 mapping and configured
road-offset threshold here. These limited fixtures do not claim coverage of unresolved defaults.
