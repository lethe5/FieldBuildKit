# Survey route acceptance harness — DRAFT callback-provenance/storage-compatibility correction

> **DRAFT TEST-DESIGN CORRECTION — pending user approval.** The approved requirements and earlier
> approved acceptance history below remain authoritative. This correction removes circular/canned
> evidence from AC-SRP-049–056 and reconciles retained executable expectations with the approved
> schema-3, access-snap, passive-toggle, platform-neutral-label and local-date supersessions.
>
> **DRAFT attempt-2 correction.** AC050 distinguishes a nonzero snapped source from the legitimate
> exact-zero source/access coordinate; AC053 consumes real pattern/casing/theme/action/source
> observations; AC054 treats payload fields as an observed list. The contract also exposes
> statusless connection failures, content-type-independent valid-JSON parsing, post-origin
> cancel/project-close quiescence, and required-field validation for every schema-3 route.
>
> **DRAFT correction cycle 2.** Empty self-declarations are no longer provenance. Mixed operations
> return field-to-event lineage from actual production calls/runtime readbacks. Request logs retain
> origin validation and the failing transport request; presentation uses semantic before/after
> states and independent renderer rereads; navigation request/write absence comes from installed
> observers. AC-SRP-056 adds visit identity/provenance validation for active and inactive routes.
>
> **DRAFT correction-cycle-2 retry 1.** The test computes mixed-output lineage from a sealed,
> hash-chained raw boundary-event journal instead of accepting operation/field-origin tables or empty
> anti-hardcoding flags. It adds valid schema-1/2 same-identity atomic upgrade/failure cases,
> D-SRP-057 metric semantics and distance corruptions, dynamic repository→QML accessibility binding,
> and actual QAccessible parent/child order for notice-before-calculate.
>
> **DRAFT correction-cycle-2 retry 2.** The event writer closes and emits a detached seal before
> result materialization; callback timing, explicit causal links and pre-existing raw-field bindings
> reject post-result replay or implicit chain ancestry. Exact-zero uses a measured non-identical
> sub-meter fixture, mapped/fallback quantities bind separately on visible/accessibility surfaces,
> and corrupt-newest load, restart and last-good recovery are three actual lifecycle callbacks.
>
> **DRAFT correction cycle 3.** Approved AC-SRP-057–058 are added. Boundary hooks now emit
> observations while production executes and seal the journal before result construction;
> `capture_outputs`, completed-result iteration, result-field classification, `result_source` and
> `bind_result` are forbidden and an AST source verifier plus a deliberate returned-result tamper
> prove the guard fails closed. Recovery must also be reachable through a generated RoutePanel's
> product cold start. Mixed storage preserves tagged legacy variants, and route-line toggle performs
> exactly one settings-only atomic write/readback while preview and legend remain write-free.
>
> **DRAFT correction-cycle-3 retry 1.** Result dictionaries are no longer observable state:
> `ObservedState`, `__setitem__`/`update` journaling and every completed-result capture are rejected.
> Each concrete callback hook declares only its own payload-to-projection schema and appends and
> flushes one JSONL record while that callback is running. The writer is sealed after the last
> callback and before a pure projection; end-of-run bulk JSONL, `dict(result)`,
> `controller.final_state`, post-seal `captured_request`, AST extraction of result assignments and
> one projection list shared by all hooks are invalid. Causal parents are explicit IDs passed from
> the triggering callback, never latest-by-source. Cold start returns a child-owned sealed journal,
> PID, generated-project hash and entry-callback IDs for parent verification. Toggle IO and
> visibility come from storage/QML callback payloads, not constants. Accessibility reads exactly
> five delegates through the actual `Repeater.itemAt(index)`, then reads each `visitValue` and
> `QAccessible` interface directly; exact-zero is index 4.
>
> **DRAFT correction cycle 4.** Delegate enumeration is the actual QML
> `Repeater.itemAt(index)` call; `visitValue` and `QAccessible` are read from that same delegate.
> No fabricated `visual_parent.*` path or repository visit recomputation is evidence. All hook
> schemas are declared and frozen before operation start. Each callback receives its triggering
> `cause_id`, append-flushes its exact callback-owned payload before return, and emits that ID as
> its sole parent. Generic `observed_outputs`, result-building `put`, lazy schema registration,
> completed-result journaling, global current/latest event pointers and latest-by-source lookup are
> rejected. Synthetic keys, Authorization values/headers and raw provider/request wire material
> never enter persisted or ordinary returned evidence. Only an explicitly named transient
> in-memory captured request used by an immediate assertion may contain them, and it is never
> journaled. Navigation is observed by harness wrappers around the imported production
> `controller.navigate` and `navigation.open`; product test-only navigation/observation APIs are
> forbidden.
>
> **DRAFT correction-cycle-4 retry 1.** A global `OUTPUT_FIELDS` table, generated
> `controller.output.*` schemas/events, synthetic `controller.observe` roots, `collect(**values)`
> and any generic function that journals assembled keyword snapshots are rejected. Only concrete,
> named boundary callbacks may journal their fixed schemas. The detached seal contains per-event IO
> receipts: write-return, flush-return, line-visible-during-callback and callback-finish timestamps
> are collected after the corresponding operations and are strictly ordered; precomputed/equal
> times are invalid, including in the cold-start child. Secret scanning covers every disposable
> generated project, storage, journal, seal, log and result file and the exact key/Authorization,
> raw-response, query and fragment markers; persisted provider URLs contain neither query nor
> fragment. Navigation and cold-start entry evidence uses entry/exit wrappers that call the saved
> original imported functions, including production `navigation.open`. A named event emitted
> before an unrelated call is not evidence.
>
> **DRAFT correction-cycle-4 retry 2.** A projected field is accepted only from one concrete
> observer callback whose direct causal parent is the already-open entry event of the production
> wrapper invocation that produced it. The matching exit follows the observation and records the
> saved original callable identity, before/after call counter, actual return identity or exception;
> a new `boundary.productionCall` after action completion, a duplicate `controller.calculate`, or a
> bulk callback receiving an assembled result dictionary is rejected. The four cold-start calls use
> executable nested wrappers in the order `qml.open_panel` → `controller.create` →
> `controller.reload` → `repository.load`, with reverse exits. Dormant wrapper source strings and
> manual events around one component creation are not evidence. Each callback now writes an event
> core with no impossible appended/flushed/finished claims, then the wrapper writes the immediately
> following hash-bound receipt after the core write/flush, visibility reread and real callback
> return. The closed journal hash and seal authenticate both records.

> **APPROVED TEST DESIGN — 2026-09-18 mixed-access/Apple Maps slice (approval 2026-09-18).** This additive contract covers
> approved D-SRP-049–056, FR-SRP-047–053, NFR-SRP-007–009 and AC-SRP-049–055. It preserves
> the approved harness history below. The approved D-SRP-056 supersession narrows retained iOS
> NAVER expectations to Android and makes AC-SRP-055 authoritative for iOS.

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

For AC-SRP-049–058, dispatching to `tests/unit/survey_route_mixed_driver.js` or any equivalent
operation switch that returns preassembled result dictionaries is forbidden. The adapter must not
inject `math` or any other name into `builtins`, replace captured request bodies after execution,
wrap values with comparison-only classes, or add expected field sets/formatting/classification to
the returned payload. Test modules import their own oracle dependencies. Expected URL, number,
classification, line-pattern and payload-field values are calculated only by the test and compared
with unchanged production observations.

Every mixed operation returns `production_provenance`, captured by runtime instrumentation rather
than declared from the operation name. It contains the actual driver path, independently verifiable
production-source paths/hashes, generated-QML artifact identity where applicable, and a
`boundary_event_journal`. Named boundary hooks are installed before the operation starts. Each
actual callback appends and flushes one UTF-8 JSONL event-core record containing only facts known at
serialization time. After that core is visible and the concrete observer callback really returns,
its wrapper immediately appends the next JSONL record: a receipt bound to the event-core line hash.
Thus records strictly alternate event/receipt; a receipt cannot be deferred or associated with a
later callback. The journal file exists before the operation, records event-then-receipt mode and
separate event/receipt flush counts, and cannot be synthesized from an in-memory list at the end. The writer is
closed and separately sealed after the last callback and before any result dictionary is
constructed. Provenance gives its path, seal path, run ID, SHA-256, byte/event counts,
file-creation/hook-install/operation-start/operation-completion/finalization/result-construction-start monotonic
timestamps, registered hook definitions and the empty list of post-finalize append attempts. The seal
independently repeats the run/hash/event/receipt/record counts, length, final-event hash,
final-record-line hash, finalization time, hook-registry hash, separate flush counts, final
callback-finish time and the canonical receipt-list hash. Each receipt binds the exact preceding
event line and core-event hash to the real times after core `write` returned, after core `flush`
returned, after the successful visibility reread and after the concrete callback returned. Event
cores contain none of `event_appended_at_monotonic_ns`, `event_flushed_at_monotonic_ns` or
`callback_finished_at_monotonic_ns`: a line cannot truthfully claim operations that happen only
after it is serialized. Receipt times are strictly increasing and are never `observed_at` offsets.
The same alternating receipt contract applies to the independent cold-start child. The executable test
reads both files twice and requires them unchanged.
Every hook and its exact callback-owned schema is registered and the registry is frozen before any
operation callback can run; registering a hook or deriving its schema from callback payload keys
inside the writer is invalid. Each registered hook records its `hook_id`, registration timestamp,
actual `implementation_path` and SHA-256, concrete
`implementation_symbol`, exact callback boundary and callback-owned `observation_schema` mapping
raw payload paths to optional top-level projection paths, all declared before execution. Schemas are
not a shared superset: every event's payload equals its concrete hook schema. A global
`OUTPUT_FIELDS`, any generated `controller.output.*` hook, synthetic `controller.observe` root,
`collect(**values)`, generic source/boundary/raw dispatcher or arbitrary assembled keyword snapshot
is not a callback boundary. Only concrete named callbacks with fixed schemas are allowed. The test independently
hashes that source and the canonical registry. Each hash-chained event core was emitted inside that actual
callback and has unique event/callback IDs, callback start/observation timestamps, zero-based `sequence`,
`previous_event_sha256`, canonical `event_sha256`, the explicit `cause_id` argument supplied by the
triggering callback, matching zero-or-one `parent_event_ids`, plus causal
links to those callbacks, an observer naming the real production source and boundary, a matching
`callback_owner` and the detached callback-owned `callback_payload`. Actual append/flush/completion
times come only from the immediately following journal receipt, which the final seal authenticates,
not from fields computed before the event write. It has one approved
source (`production_call`, `controller_state`, `captured_transport`, `captured_storage`,
`loaded_artifact`, `accessibility_interface`, `source_layer_reread`, `signal_delivery`,
`navigation_launcher`, `render_observation`), and the raw observed production field paths/values;
`raw_observed_fields` equals `callback_payload` exactly.
The hash-chain predecessor is never an implicit causal parent. A root production callback receives
`cause_id=null`; every callback it triggers receives that exact event ID, and
`originating_event_ids` equals the resulting empty-or-singleton parent list. Global
current/latest-production/storage event variables, latest-event-by-source lookup and a
generic relation to every prior production event are invalid. Each
callback may publish explicit observations containing a unique observation ID, dotted callback
payload path, raw value, optional pre-registered top-level projection path and the exact
`producer_entry_event_id` before the seal. A projected callback has exactly one projected field and
its sole direct parent is that pre-existing production-wrapper entry; one bulk callback may not
receive or project an assembled result dictionary. Its receipt finishes before the matching wrapper
exit begins. Each production wrapper emits an entry/exit pair with one invocation ID, saved-original
callable ID, before/after original-call counter, and actual returned/threw outcome. The original is
called exactly once between the pair. Nested wrapper entries point to their already-open outer entry;
production-call events need not publish an output. No generic output
capture may inspect the completed result. `capture_outputs`, generic `observed_outputs`, a
result-building `put`, `dict(result)`, a synthetic
`controller.final_state`, iteration over `result` or its keys/items,
field-name source classification, `output_bindings`, `result_source`, `bind_result`, or any post-result
replay into the journal is forbidden. A dict subclass such as `ObservedState`, a journal append from
`__setitem__`, `update` or `setdefault`, and a helper returning all prior production events as parents
are equally forbidden. So are AST extraction of result-assignment field names, one projection list
reused across hooks, end-of-run bulk JSONL writing and copying `captured_request` after the seal.
Result construction is a pure post-seal projection of registered callback payload paths. The only
non-projected exception is an explicitly named transient `captured_request`/`captured_requests`
value held in memory for an immediate request-shape assertion. It must never be copied into the
JSONL, seal, evidence/project files, logs, diagnostics or ordinary result fields. Exact synthetic
keys, Authorization values/headers, raw provider responses/bodies, and raw request URL/query/body
markers are scanned byte-for-byte across the returned result and every generated project, storage,
journal, seal, log and result file in the disposable run. A persisted `server_url` or
`optimizer_url` must have its query and fragment stripped, or the value must be rejected before any
persistence. Production-call counts are computed from callback records.

`boundary.productionCall`, `wrappedEntry`, `wrappedExit` and equivalent manual marker APIs are
forbidden in operation assembly code. A production-call record can originate only from an installed
wrapper that invokes the saved original. Every wrapper entry starts before operation completion;
every projected observation lies between that same invocation's entry and exit. A later duplicate
`controller.calculate` created only to parent a completed observation therefore fails both source
and runtime checks. For cold start the four imported concrete functions are distinct nested wrappers:
`qml.open_panel` contains `controller.create`, which contains `controller.reload`, which contains
`repository.load`; their exits are reversed. Runtime counters, original return/exception evidence
and ordering are mandatory. Merely storing wrapper-looking source strings while manually emitting
four names around `component.create` is rejected.

The executable test reads and hashes the journal itself, validates hook-before-operation timing,
finalization, chain and explicit causal parent order, and computes field lineage from raw callback
payloads without accepting the result dictionary as an input. It mutates a returned field and,
separately, replaces an event's originating parents with every prior production event; both tamper
checks must raise. An AST verifier reads the actual driver source and rejects completed-result
iteration, output capture/classification, result-mutation journaling, wholesale parent collection
and the forbidden symbols. Every mixed-operation output field consumed by AC-SRP-049–058—and, to avoid a
declaration loophole, every returned top-level output except `production_provenance` and the
explicit transient request capture—must have exactly one
event ID and raw observation equal to the
returned value. Source-type causal rules, rather than returned field names, require captured
transport/storage/artifact, controller, renderer, accessibility, signal and launcher observations
to descend from explicit production-call parents; render and accessibility observations also descend
from captured storage. Empty `adapter_postprocessed_fields`,
`case_copied_result_fields`, `fixture_expected_values_used_as_results`, `hardcoded_result_fields`,
`unattributed_result_fields`, an adapter-created `field_origins` table, or an
`evidence_integrity`/operation table are forbidden rather than accepted as proof. A copied source
hash, declared call list, synthesized journal after execution, or event whose observer boundary is
the input `case` is not evidence. An observation rooted at a `case.*`, `fixture.*`, `expected.*` or
`result.*` raw path is likewise rejected.

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
Optional `eta` and `eta_basis` are `None` if unavailable and occur together. New calculations save
schema 3 and expose complete vehicle legs, visits, totals and `road_geometry`; legacy schema 1/2
remain read-only compatible and schema-1 snapshots may lack legs. `eta` and
`eta_basis` occur together. For `ors-vroom`, job-step VROOM `arrival` numbers become unchanged
relative seconds and `eta_basis` is `relative_seconds`; no current time or `created_at` is used to
invent an epoch. Associated availability flags must match actual UI disclosure.
Every route in a schema-3 document, including inactive routes, must contain `vehicle_legs`,
`visits`, `vehicle_totals`, `walking_totals` and `combined_totals`. Loading a schema-3 document
with any one omitted rejects the whole document without repair or write; schema 1/2 retain their
approved read-only compatibility.
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

For the mixed-access slice, request `kind` additionally admits `access-snap` and
`walking-directions`. A captured request includes only its bounded decoded wire record; raw response
bodies are not retained in result/log/settings evidence. Every calculated scenario returns the
actual ordered stage trace, automatic-retry list, write capture, immutable before/after candidate,
saved route, revision, settings and source-feature snapshots. Failure setup must seed nonempty saved
and candidate state through production actions. Constant empty lists or copied `case` snapshots are
not preservation evidence.

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
| `result_roundtrip` | Inject the supplied raw VROOM 1.14 `optimizer_response` at the optimizer HTTP boundary and optional raw ORS GeoJSON `directions_response` at its HTTP boundary; calculate, save schema 3, destroy session, and reopen from actual storage. Extract job `steps[].arrival` as numeric relative seconds; do not accept a pre-normalized `route.eta`. Return independently decoded `saved_document`/`reloaded_document` and route snapshots with mandatory vehicle legs, visits and separate totals. Missing optional timing/directions values stay absent. With `seed_saved=True`, ISO, partial, negative or non-finite job arrivals reject the candidate and preserve the independently reopened saved/active route. |
| `save_two_restart_move` | Apply supplied project settings, retain the key only in session, save two different named routes, select both, retain active second route, destroy session, physically move the entire folder, make the old location inaccessible, and reopen offline with the key removed. Only restart/select/load requests count in `requests`. Return independently decoded route/settings before/after, both selected IDs, old/new paths and session-key presence. |
| `storage_fault` | Seed valid route and update candidate. Inject failure at actual storage commit boundary: truncated write, full storage, newest copy corrupt, every readable store corrupt, or stale revision after independent update. Never hardcode two slots/JSON. For all-corrupt, immutable external last-good capture proves original data retained; explicit refusal is acceptable, fabricated recovery is not. Stale writer must not overwrite newer committed data. `published_partial` observes whether any consumer saw incomplete candidate. |
| `complete` | Seed 8 stops in ID order. Attempt supplied IDs in list order through the configured actual layer Boolean field, or through local route-stop UI when no completion field is mapped. Only the earliest incomplete row may change; a later-row attempt is nonmutating. Observe immediately, reopen and return `reloaded`. Only explicit Boolean `true` is complete; `false`, `NULL` and a missing field are incomplete. Dates/observation existence must not infer completion. |
| `completion_write_failure` | Seed a mapped Boolean field and nonempty saved/active route, then attempt one completion change through the real panel with a read-only layer or incompatible field type. Return independently reread source values, saved/active route and next-target state before/after. Display the write error and preserve all prior state. |
| `route_progression` | Consume the supplied raw schema-2 ORS directions response at the transport boundary, create/save the full route through production, independently reopen it, then perform completion/uncheck actions through mapped Boolean or route-local controls. A later incomplete stop attempted through the panel must leave the effective state unchanged; ordered checks advance the prefix, and unchecking an earlier stop may preserve a later true value as out-of-order. The raw fixture contains intermediate road vertices and route-level `properties.way_points`; segments contain no `way_points`. `route_seed_provenance` binds the captured response hash to the committed route ID/revision and actual project-relative storage path. Observe each effective completion set, consecutive prefix, next target, visit context, remaining leg sequences/metrics/geometry and bottom state. Optional restart, last-good recovery, offline reopen and physical folder move must independently reload the same derived state. No routing request is allowed after seeding. The superseded `remaining` operation/control must not be exposed. |
| `reopen_navigate` | Retained Android/desktop baseline only. Reload saved supplied LineString offline, activate render path, and invoke the platform-neutral `다음 지점 지도 안내` action with injected OS launcher results. Android uses the official package-bound NAVER intent and Google Play fallback; desktop reports an actionable unsupported-host error. iOS is authoritative only in `platform_map_dispatch` under D-SRP-056/AC-SRP-055. |
| `passive_action` | Seed saved route with synthetic key retained only in session; perform action and inspect whole generated folder and full logs. `complete` changes actual completion; `restart` destroys session; `load` loads saved route. |
| `configured_calculate` | Seed a saved active route, apply each supplied setting through the production project/session settings path and press calculate. With `fresh_project=True`, the case also passes `seed_fixture_settings=False`: the driver must not install any synthetic endpoint setting (including `vroom.invalid`) before the generated project is loaded, must omit endpoint fields, and must observe the generated defaults. Migrate only the exact legacy defaults before dispatch and the next normal settings save; normalize one trailing separator; preserve every other custom/self-hosted URL. Dispatch registered `ors-vroom` and return `transport_settings`, full request records, independently decoded `persisted_settings`, diagnostics and saved/active before/after. Hosted defaults require a key before any request; custom/self-hosted endpoints permit no key and omit `Authorization`. The calculation remains an unsaved preview. Omitted road offset defaults to 1000 m. An unknown provider ID fails before registry transport dispatch and preserves the saved/active route. A session key may reach request headers only; it must not enter persisted settings, project files, logs or errors. |
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
| `schema2_roundtrip` | Historical operation name for the retained AC026/035 ORS-leg fixture. Calculate from raw optimizer/directions plus the mandatory access-snap boundary, validate and atomically save schema 3, restart and independently reopen it. The zero-walking fixture produces exact-zero visits while preserving the route-level `way_points` leg oracle. All malformed-payload and preservation requirements remain unchanged; post-save completion/toggle/load do not mutate immutable route data. |
| `map_start_marker` | Load the generated panel and live map, select map-start mode, capture supplied map centers through the real control, and drive pan/zoom, recapture, panel collapse/reopen, calculation success/failure, mode change, clear/invalidate and project close actions. Traverse the whole canvas marker collection after every action and return its count plus every marker's object identity, role, coordinate, visible text, accessible name, visibility and measured contrast. Install actual source-provider and route-storage commit observers before the first action and return their complete attempt logs plus independent before/after storage snapshots in `write_capture`; a panel/controller pointer or constant empty lists are invalid. A transform fault is injected only at the coordinate-transform boundary and must leave the prior valid start/marker intact. |
| `completion_overlay` | Complete/uncheck/recomplete one actual Point, LineString or Polygon feature through mapped or route-local state, restart and load. Return normalized rendered overlays, check/text state, source renderer and source bytes before/after. Overlay observations come from the production map-item/render path, not QML source strings. |
| `metric_display` | Render an active and no-route bottom bar from supplied metric inputs and return the visible formatted strings. |
| `route_line_toggle` | Create two saved routes and a separate project, turn the generated route-line control off, switch route, reopen the panel, cold restart and move the folder with settings. The first project remains off through every lifecycle while the unrelated project starts default-on. Return actual overlay visibility, completed overlay/source/full-route snapshots, independently observed route/settings commit attempts and route revisions. The value change performs exactly one atomic settings-only write/readback with changed path `settings.show_route_line`; route writes, revision change and provider requests remain zero. |
| `legacy_route` | Materialize supplied schema-1/2 or unknown-future bytes, then load offline or explicitly invoke full calculate-and-save. Load never repairs/splits/writes; only the explicit action may issue requests and publish schema 3 with normal revision semantics. Schema 3 is current, not a future-schema fixture; use an actually unknown value such as 99 for rejection. |

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
| `candidate_name_save` | Create a real candidate through the captured provider boundaries, then drive focus, text changes and save through the generated panel. Snapshot candidate, base revision, calculation inputs and request/write capture after every action. A real calculation-input change or independently committed route snapshot revision is stale. A route-line toggle follows D-SRP-059: it performs one settings-only atomic write/readback, no route write/revision/provider request, does not stale the candidate, and the same candidate can still be saved. Return `toggle_observation` from installed storage observers, not a constant. |
| `followup_panel_ui` | Load the actual generated panel at 320/1024 px in empty/value/focus/error/disabled states, render a screenshot and traverse the live QML object tree. Return all seven controls with raw control/label/value/indicator/error rectangles, kind, outline/notch/font/padding metrics, stable object identity, exact accessibility name/role/state and stored values before/after. Do not return a precomputed pass/signature. |
| `settings_disclosure` | Start a new generated-panel session, observe initial disclosure state, then expand/collapse/re-expand through its real control. Return rendered labels/masking/accessibility state, preserved input values and complete request/storage-write captures; toggling must be passive. |
| `settings_key_provenance` | For manual input, enter the synthetic key into the masked generated panel and restart the app session. For project provenance, build with plaintext consent, independently parse the generated `.qgs` project variable, then open/restart the panel. Return the source message, warning/masking observations and actual post-restart key source without exposing the value in UI/diagnostics. |
| `settings_snapshot_save` | Save through `서버 설정 저장 (키 제외)` using the production two-slot repository. Independently read the committed A/B file(s), route and settings, and report actual project scope/path. Capture the session key and objective before save but prove neither exists in readback settings. A commit fault preserves the independently captured last-good bytes and session key and emits no success treatment. |
| `platform_naver_dispatch` | Historical operation name retained only as prior design history; no executable test invokes it. D-SRP-056 supersedes its visible label and iOS behavior. Current Android/iOS coverage uses `platform_map_dispatch`. |
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

### 2026-09-18 mixed-access operations — approved meaning, DRAFT evidence correction

| Operation | Required driving steps and returned evidence |
| --- | --- |
| `provider_http_failure` | Through the generated QML calculate control and production controller/backend, create and independently reopen nonempty saved/candidate baselines, then inject one HTTP or statusless transport result at the real transport stage. The ordinary `requests` log retains only bounded non-sensitive request summaries, including origin validation and the failed request identity/hash. `failed_transport_observation` points back to that summary and records status/sanitized classification, never raw response/body/request URL/query/body. A stage copied from `case` is not evidence. An explicitly named transient in-memory `captured_request` may expose the failed request only to the immediate request-shape/hash assertion and is never journaled or persisted. Return the production minimal record, live message-label diagnostic, classification/action, raw-body-retention flag and independently observed state/write/retry snapshots. Production first attempts JSON parsing for a syntactically valid body even when content type is missing or misleading. `status_0`/network records have `http_status=null`, never synthesize HTTP 0, and expose an actionable connection check. Sanitization is performed only by production. Status 200 is a bounded negative oracle: its body must never enter error UI. |
| `mixed_route_calculate` | Observe the actual coordinate-sharing notice object and accessibility interface before delivering the explicit calculate-button signal. The approved specification requires notice, not a new notice acknowledgement; report `acknowledgement_required=false`. Visual order comes from rendered geometry. Accessibility order comes from actual `QAccessible` parent/child traversal with parent/interface/object IDs and the traversal sequence; QML `childItems` DFS is forbidden. The notice precedes calculate in that observed traversal, and the first request starts after the signal. Execute production preflight/origin validation, one ordered batched `driving-car` snap, per-site walking validation, matrix, optimizer, driving directions and candidate validation. `preflight_observation` is controller state after the click, never `case.access_fault`. Retain origin validation in `requests`. An origin response with `location=null` remains failure even if `snapped_distance` is finite, and starts no access-snap/downstream/write. Cancel or project close delivered immediately after origin validation also starts no later work. Return exact request/stage traces, snap/radius/origin workaround observations, request payload field sets, before/after source/state/storage snapshots and the actual candidate. The exact-zero case may legitimately have `source_coordinate == access_coordinate`; only a nonzero snapped source is forbidden from downstream vehicle payloads. `batch-limit` is rejected before transport. Only an explicit no-foot-path response may continue as unmapped lower-bound, and its save acknowledgement is separate from the coordinate-sharing notice. |
| `mixed_route_roundtrip` | Create the requested external walking fixture (mapped, exact-zero or explicit no-path) through generated QML and production controller/backend, explicitly save schema 3 through the real save control/repository, independently reopen committed bytes, then perform restart, last-good recovery when requested, offline open, physical folder relocation and complete→uncheck through real controls. `lifecycle_route_observations` independently reread restart/offline/move state; each allowed visit pair must exact-roundtrip. For unmapped visits, the independently calculated source/access geodesic equals `access_offset_m` and both leg distances within 0.01 m. The executable exact-zero fixture deliberately uses non-identical source/access coordinates with `0 < geodesic <= 1 m`; its preserved `access_offset_m` equals that measured geodesic within 0.01 m while both leg distance/duration values stay zero and both geometries stay null. Identical coordinates remain valid under the approved `<=1 m` product rule; the fixture only prevents assuming every exact-zero offset is literally zero. Mapped request endpoints and outbound distance/duration/geometry come from the captured `foot-hiking` response, and return metrics match it with exact reversed geometry. Echoing the candidate as saved/reloaded, constructing a schema wrapper in the harness, or calculating remaining counts in the harness is forbidden. |
| `mixed_route_compatibility` | Materialize exact supplied storage bytes and run production repository/controller/panel paths. No-file/default open is schema-2 in memory and write-free; settings-only or default-start-only save from no file or schema 1 writes at most schema 2. An explicit production recalculation plus save makes a top-level schema-3 document: the selected same-ID route is tagged `route_schema: 3`, while every unrelated legacy route preserves all original fields plus `route_schema: 1|2` and remains listable/loadable. Untagged homogeneous schema 3 loads without write and receives markers on its next normal write. Unknown markers, duplicate identity, invalid variants and marker/content contradictions fail load/recovery/commit atomically with bytes and last-good unchanged. Existing visit corruption still performs three separate real lifecycle callbacks. A separate corrupt-newest case destroys the seed process/session and starts a distinct `subprocess.Popen` child with a different OS PID. The child returns its own immutable artifact containing PID/parent PID/return code, a canonical generated-project manifest/hash, selected route/document hash, entry-callback event IDs and its own closed/sealed callback JSONL. The parent embeds that artifact, independently hashes and verifies it, and journals both receipt and verification. Each child entry ID identifies the entry phase of an executable external harness wrapper around the actual `qml.open_panel`, imported `controller.create`, `controller.reload` or imported `repository.load` function. The four entries nest in that order, their exits reverse, and each pair records saved-original identity, a single call-counter increment, and actual return/exception only after the original returns. Dormant wrapper strings or four manual events around one component creation, direct `productionCall("name")`/`wrappedEntry`/`wrappedExit`, a fixed returned `entry_path`, UUID or loaded flag are not evidence. Alternating child event/receipt records prove each event core was written, flushed and visible and its concrete callback returned before the receipt was appended and before its wrapper exit. The child must select the preceding valid route as last-good with corrupt and last-good bytes unchanged and zero provider/write activity. Direct harness-only `recoverLastGood` invocation cannot satisfy this case. |
| `mixed_route_presentation` | Commit and independently reload real schema-3 routes, then load the generated `RoutePanel.qml` object tree/map at supplied width/theme. `presentation_provenance` observes effective width/palette, real overlay objects, all three patterns/casings/non-color cues, legends and warning marker. Preview, legend, complete and uncheck events use semantic before/after state and remain write-free where the product contract says so. Before/after renderer values are independent source-layer rereads. For two changed all-mode documents containing exactly five visits, enumerate the actual Repeater delegates only through `Repeater.itemAt(index)`, read that returned delegate's `visitValue` property and query that same delegate's `QAccessible` interface directly. No fabricated `visual_parent.itemAt(index)` path/ID is returned. The accessible site name/ID, walking mode, metric source, out-and-back meaning and distance/time follow those delegate values; exact-zero is index 4 and no visit may be omitted. Repository visits are not returned or recomputed as an accessibility oracle, and fixed `visitAccessibility0/1/2` objects are invalid. Separate visible and accessibility objects bind mapped provider distance/time and fallback straight-line lower bounds without summing them as exact walking totals. No metric-source/value literal or operation/fixture mapping may serve as the oracle. A real route-line toggle records actual storage-before, atomic commit and reopened readback callback events for each successful value change; the test derives the single commit and sole `settings.show_route_line` change from those payloads. Success-feedback visibility is not an AC-SRP-058 requirement. It preserves route/source/completion/revision and provider inactivity, survives panel reopen, a real cold restart and folder move with settings, and restores on write/readback failure with actionable callback-observed failure feedback. Each off/on line visibility is reread from the actual QML objects after the action, never overlaid from an expected Boolean. Preview and legend install storage observers and produce zero observed writes. It remains a generated/headless proxy only. |
| `platform_map_dispatch` | Save and independently reload an active route through production repository/controller, install routing-request and route-storage-write observers, then locate and invoke the loaded generated QML control whose exact label is `다음 지점 지도 안내`. The harness monkeypatches/wraps the imported production `controller.navigate` and actual imported `Navigation.open` function without changing product code. Its executable wrapper emits an entry event, calls the saved original with the original receiver/arguments, then emits a causally linked exit event with `returned|threw` and launcher count; source inspection proves that ordering. A pre-recorded `wrappedCall("navigation.open")`/named event is invalid. Both functions remain separately distinguishable from every real external `Qt.openUrlExternally` call/result/exception; product code must not expose `navigationBoundary`, an observation callback or another test-only navigation API. Even an invalid coordinate rejected by `checkedCoordinate` produces the real `Navigation.open` entry and throwing exit with launcher count zero. `request_observation` and `write_observation` identify the installed observer/source and return their observed empty event logs; hardcoded `routing_requests=[]`/`writes=[]` mirrors are not evidence. Independently reread state and revision before/after. iOS permits one Apple Maps HTTPS call and no fallback; Android retains NAVER intent/Google Play fallback. The harness never returns a production-computed expected URL for a circular test comparison. |

Within a top-level schema-3 document, only a `route_schema: 3` route (or retained untagged
homogeneous schema-3 route) uses the mixed visit contract. Its only allowed visit pairs are
`mapped/ors-foot-hiking`, `exact_zero/exact_zero`, and
`unmapped_estimate/straight_line_lower_bound_m`; every visit also has nonblank `layer_id`, `site_id`
and `metric_source`, with layer/site identity matching its route stop. Tagged `route_schema: 1|2`
routes use their legacy validator and contain no inferred mixed fields. Validation applies equally
to active and inactive routes and to normal load and recovery.

Provider failure fixtures use bounded synthetic data only. They must not make live ORS calls or
claim endpoint/provider availability. Presentation automation cannot claim color/contrast,
screen-reader or interaction PASS on target QField. M18–M21 remain the authoritative user-run
live-provider/device gates.

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

Schema-3 vehicle legs retain the approved `sequence`, `from`, `to`, finite non-negative distance/time
and WGS84 GeoJSON LineString contract. `from`/`to` is literal `start` or `{layer_id, site_id}`.
Legacy schema-2 reads preserve the same historical leg shape. Full-route immutable snapshots
include document schema, route revision, totals, ordered legs and full display geometry. Progression
snapshots include prefix length, remaining leg sequence, visit context, metrics/geometry, completed
IDs, check/text and overlay. Map overlay style is normalized only after rendering: Point/LineString
use `#1565C0` at opacity 1; Polygon uses that color at fill opacity .35 and outline opacity 1.
Renderer/source comparisons use nonempty bytes or full decoded records.

The old `remaining` operation is deliberately removed from this contract. AC-SRP-011 remains in
historical traceability, but D-SRP-023/FR-SRP-026 require no remaining-calculation control and zero
routing requests for completion, uncheck, toggle, restart or load.
