# Feature: FieldBuild Kit — follow-up Category A defect corrections

> Status: DRAFT — awaiting stakeholder review
> Owner: spec-writer
> Last updated: 2026-08-31
> Scope: follow-up conformance-defect specification; no product-requirement change

## 1. Summary

This specification records the narrowly bounded follow-up Category A defects found while
verifying the existing FieldBuild Kit corrective scope in `specs/fieldbuild-kit-five-fixes.md`
and its related documents. It defines the evidence and observable correction contract for the
implementation and test-design stages; it does not replace, renumber, weaken, or delete any
existing requirement, acceptance criterion, or decision-log entry.

The six findings are: operation-timeout liveness, saved child-observation write-back, offline
selection/test-fixture compatibility and size-guard ordering, D-90/D-91 failure triage, the
exact Type 2/3 photo-expression contract, and offline VWorld-key handling. The write-back
clarification recorded in D-FOLLOWUP-002 below changes only the interpretation of which fields
QML writes directly: the observable result remains the existing Korean-name/scientific-name/KTSN
identification contract, with scientific name and KTSN derived by the existing QGIS contract.

## 2. Functional Requirements

- **FR-FOLLOWUP-001 (operation-timeout liveness):** The offline MBTiles operation must not be
  terminated by the current fixed 12-hour operation-timeout ceiling while tile acquisition or
  MBTiles writing is demonstrably making forward progress. The lifecycle policy must either
  extend with the supported work or otherwise remain live while progress continues. Per-request
  network timeouts, explicit cancellation, provider failures, the 900 MiB pre-generation guard,
  the 1 GiB hard output limit, temporary-output cleanup, and actionable failure reporting remain
  unchanged and mandatory.

- **FR-FOLLOWUP-002 (active child Korean-name write-back):** After photo identification and
  explicit candidate selection in a currently edited child `observation` reached through the
  existing Related records flow, the write-back must target that child feature and directly
  apply its `selected_korean_name` (`국명`) through the active editable QField/QGIS form model.
  The operation must verify the `changeAttribute` result and the resulting Korean-name value
  before reporting the write-back as applied, and the value must survive the normal save/reopen
  cycle. `selected_scientific_name` (`학명`) and `selected_ktsn` (KTSN) are not QML direct
  write-back fields in this follow-up: the existing Korean-name-based QGIS lookup/default/
  apply-on-update contract derives them. The existing target UUID, layer context, parent,
  sibling, list-model exclusion, and candidate-selection rules remain in force.

- **FR-FOLLOWUP-003 (offline selection and acceptance-fixture compatibility):** The existing
  offline selection semantics remain authoritative: a valid supported source/layer must be
  explicitly represented in the offline build request, no unsupported source or silent default
  may be substituted, and OpenStreetMap remains excluded from offline downloads. The acceptance
  fixture/API shape used by the pre-existing offline success, MBTiles metadata, size, and
  attribution tests must be made compatible with that contract by supplying an explicit valid
  supported layer or equivalent test seam. A valid selected layer must not be rejected as
  `offline_layer_unavailable` merely because the fixture omits the field required by the approved
  selection contract.

- **FR-FOLLOWUP-004 (offline size-guard ordering):** For an offline request with a usable VWorld
  key and a valid explicitly selected supported layer, the existing conservative size estimate
  must be evaluated before tile acquisition or MBTiles writing. An estimate above 900 MiB must
  produce the existing size-limit failure and no tile fetch or deliverable; selection validation
  must not be bypassed, and the ordering must not be changed to create a silent default-layer
  path. A request with no usable selected layer may still fail first with the existing
  `offline_layer_unavailable` condition.

- **FR-FOLLOWUP-005 (D-90/D-91 finding triage and boundary):** The Type 1 consent-gate behavior
  remains unchanged by this follow-up. A failure of
  `test_d90_d91_identify_and_layer_visibility.py::test_ac134...` in the Type 1 branch is to be
  recorded and handled as a separate baseline/regression finding, not fixed by removing or
  weakening the Type 1 gate. The offline layer-visibility failure is not silently classified as
  either a follow-up conformance defect or an unrelated defect until the open question in
  Section 8 is resolved against the approval status and scope of the existing D-91 material.

- **FR-FOLLOWUP-006 (photo-removal expression conformance):** The Type 2 and Type 3
  `observation` photo-identification expression must continue to conform exactly to the existing
  approved expression contract represented by AC-QPB-113 and
  `test_observation_photo_removal.py`: it reads the three inline photo-path columns using the
  same structural mechanism as Type 1, contains no `relation_aggregate()` path, and does not
  reference the removed `rel_observation_photo_observation` relation. The observed expression
  shape failures are conformance defects; tests must not be weakened and the approved contract
  must not be rewritten.

- **FR-FOLLOWUP-007 (offline missing-key path):** Offline mode must collect and pass the VWorld
  API key required by the existing MVP `build_project` contract. If the key is missing or blank,
  the build must fail before size estimation, tile acquisition, or MBTiles writing with a clear,
  non-technical, actionable message, never a raw `KeyError` representation or uncaught exception.
  When present, the key remains transient and may be used only for tile retrieval; it must not
  appear in MBTiles metadata, the generated project, `MANIFEST.json`, `VALIDATION_REPORT.json`,
  or any mobile transfer-folder file. This does not add a new secret-storage or offline-map
  selection behavior.

## 3. Constraints

- **C-FOLLOWUP-001:** `specs/fieldbuild-kit-five-fixes.md`, its existing FR-FIX/AC-FIX IDs, and
  all related existing decision logs remain authoritative and must not be edited, deleted,
  renumbered, or weakened by this follow-up.

- **C-FOLLOWUP-002:** This is a Category A conformance-defect correction scope. It must restore
  existing approved observable behavior and test conformance; it must not turn an implementation
  defect into a new product capability, new provider, new data model, or changed selection
  semantic.

- **C-FOLLOWUP-003:** The write-back target is the active child observation feature. QML directly
  writes and verifies only `selected_korean_name`; scientific name and KTSN must be left to the
  existing QGIS lookup/default/apply-on-update derivation contract. No separate direct
  `changeAttribute` success assertion for those derived fields is authorized by this follow-up.

- **C-FOLLOWUP-004:** UUID and layer-context verification, normal QField save behavior, relation
  identity, parent/sibling isolation, and fail-closed behavior for an unverified active model
  remain mandatory. A list model is never an editable write target.

- **C-FOLLOWUP-005:** Offline builds remain subject to the supported VWorld catalog, explicit
  single-layer selection, transient-key/no-secret-output rules, 900 MiB pre-generation
  threshold, 1 GiB hard output limit, bounded request behavior, cancellation, provider-error
  handling, and cleanup of incomplete output.

- **C-FOLLOWUP-006:** The current acceptance failures are evidence for follow-up verification;
  this spec-writing task changes no QML, Python application code, or test file. Such changes may
  occur only after this specification and the subsequent acceptance tests are separately approved
  under the repository workflow.

## 4. Assumptions

- **A-FOLLOWUP-001:** Per the user's request, `specs/fieldbuild-kit-five-fixes.md` is the
  baseline approved corrective scope for this follow-up, and the existing related specs,
  traceability files, and MVP harness contract are reference evidence rather than replacement
  requirements.

- **A-FOLLOWUP-002:** The existing QGIS lookup/default/apply-on-update behavior keyed by the
  child observation's `selected_korean_name` is the authoritative source for deriving
  `selected_scientific_name` and `selected_ktsn`; no new derivation algorithm is introduced.

- **A-FOLLOWUP-003:** “Normal save/reopen” means the existing QField child-observation edit
  form save followed by reopening the same feature from the same relation/direct path. It does
  not mean a QML-only in-memory display or a new persistence mechanism.

- **A-FOLLOWUP-004:** The offline fake tile source remains a test-only dependency-injection seam.
  It may be used to make the success, size, metadata, and attribution checks deterministic, but
  it must not bypass production validation of a selected supported layer or the key secrecy
  contract.

- **A-FOLLOWUP-005:** The D-90 Type 1 consent-gate expectation is an explicit boundary in the
  existing D-90 material. D-91's initial-visibility material is currently documented as draft
  pending stakeholder review, so its relationship to this Category A follow-up remains open.

## 5. Edge Cases

- **E-FOLLOWUP-001:** Tile acquisition or MBTiles writing continues to emit forward progress
  after the former 12-hour boundary. The operation remains active and may complete; it is not
  treated as wedged solely because elapsed wall-clock time exceeded that ceiling.

- **E-FOLLOWUP-002:** The offline operation stops making progress, is explicitly cancelled, hits
  a provider failure, exceeds the pre-generation estimate, or exceeds the hard output size. The
  outcome remains distinguishable and no partial MBTiles deliverable is published.

- **E-FOLLOWUP-003:** A matching child model exists but one of the three derived-field values is
  not yet refreshed. The write-back success decision is based on successful Korean-name
  application and the existing QGIS derivation/save contract; QML must not write a second copy
  of the scientific name or KTSN to force convergence.

- **E-FOLLOWUP-004:** More than one form/model is mounted, or the child form is still mounting.
  Only the active child observation with matching UUID and layer may receive the Korean-name
  write; otherwise the request remains diagnosable/pending or fails closed under the existing
  lifecycle rules.

- **E-FOLLOWUP-005:** An offline fixture omits `layer`, supplies an unsupported layer, or
  supplies a supported layer plus an oversized estimate. The first two cases exercise the
  existing selection failure; only the valid selected-layer case reaches the size guard, and the
  oversized case must not reach tile fetching.

- **E-FOLLOWUP-006:** The offline key is absent, blank, or present with a deterministic fake
  source. Missing/blank key handling remains actionable and artifact-free; a present key does
  not authorize putting the key into output metadata or the transfer folder.

- **E-FOLLOWUP-007:** A Type 2/3 expression still uses the legacy relation aggregate, removed
  relation, or a structurally different inline expression. This is a conformance failure even
  if a weaker test happens to produce a passing result.

- **E-FOLLOWUP-008:** The D-90 Type 1 consent test fails while Type 2/3 behavior remains correct.
  The Type 1 result is reported separately; this follow-up does not convert that failure into a
  request to remove Type 1 consent.

- **E-FOLLOWUP-009:** The offline visibility test fails for a reason not covered by the approved
  five-fix scope. It remains an explicitly open classification question and must not be resolved
  by changing the five-fix selection, timeout, write-back, expression, or key contracts.

## 6. Out of Scope

- Changing any existing requirement, acceptance ID, traceability mapping, or decision log in the
  baseline or related specifications.
- Removing the Type 1 consent gate, changing D-90's Type 2/3 immediate-identify semantics, or
  changing D-91's product semantics before its scope is resolved and approved.
- Requiring QML to write `selected_scientific_name` or `selected_ktsn` directly, adding a second
  name-resolution algorithm, or changing the existing QGIS lookup/default/apply-on-update
  contract.
- Adding a new offline provider, changing the supported VWorld layer catalog, silently selecting
  a layer, weakening the 900 MiB/1 GiB guards, or exposing the VWorld key in any output.
- Replacing the exact Type 2/3 inline photo-path expression contract or weakening its tests.
- Migrating already-generated projects, changing schema/relation/UUID definitions, changing
  QField core, or adding a native API.
- Editing QML, Python application code, or tests in this spec-writing task. Those are subsequent
  clean-room implementation/test-designer activities after approval.

## 7. Acceptance Criteria

- **AC-FOLLOWUP-001:** Given a supported offline build whose tile acquisition or MBTiles writer
  continues to report forward progress beyond the former fixed 12-hour boundary, when the
  operation is allowed to continue, then it is not terminated by that boundary and can publish a
  valid MBTiles result after the existing coverage, metadata, and size checks pass. Given a
  controlled no-progress, cancellation, provider-error, or size-limit outcome, then the matching
  existing failure is reported and no partial deliverable remains.

- **AC-FOLLOWUP-002:** Given a saved Type 3 project with a child `observation` opened through
  `조사지 → 조사 → 식물관찰`, when a photo-identification candidate is selected, then the active
  child model receives `changeAttribute("selected_korean_name", <selected Korean name>)` with
  an accepted result, the child model reads back that Korean name, and normal save/reopen shows
  the same Korean name on the same observation. Its UUID and `survey_id` remain unchanged, and
  no parent or sibling is changed. The acceptance check does not require QML to call
  `changeAttribute` for `selected_scientific_name` or `selected_ktsn`; it verifies instead that
  the existing QGIS lookup/default/apply-on-update contract derives the expected scientific name
  and KTSN after the normal save/reopen cycle.

- **AC-FOLLOWUP-003:** Given the existing offline success, MBTiles coverage/metadata, size, and
  attribution test scenarios, when their test configurations pass through the approved offline
  selection contract, then each valid scenario carries one explicit supported VWorld layer and
  reaches its intended success/metadata/size/attribution assertion without
  `offline_layer_unavailable`. A scenario with no valid selection still fails with the existing
  `offline_layer_unavailable` behavior rather than silently selecting a layer.

- **AC-FOLLOWUP-004:** Given a valid offline VWorld key and one explicitly selected supported
  layer whose conservative estimate exceeds 900 MiB, when the build is invoked, then it returns
  the existing offline-size failure before any tile-fetch/write call, publishes no MBTiles, and
  leaves the 1 GiB hard limit unchanged. Given an estimate within the threshold, the valid
  selected-layer path reaches the existing tile source and can complete under the existing hard
  limit.

- **AC-FOLLOWUP-005:** Given the D-90 Type 1 boundary test, the existing Type 1 consent gate
  remains present and its failure, if any, is reported as a separate baseline/regression finding.
  This follow-up's implementation and tests do not remove, bypass, or weaken that gate.

- **AC-FOLLOWUP-006:** Given the offline visibility failure observed in the full run, the
  follow-up record identifies it as unresolved under O-FOLLOWUP-001 until the D-91 approval/scope
  question is answered. No implementation or test result may claim that this follow-up fixes or
  excludes the visibility behavior without that classification decision.

- **AC-FOLLOWUP-007:** Given a newly generated Type 2 or Type 3 project with identification
  enabled, the `observation` photo-path expression matches the existing Type 1 inline mechanism
  after field-name normalization, directly references the three inline photo-path columns, and
  contains neither `relation_aggregate()` nor `rel_observation_photo_observation`. The existing
  expression-shape tests remain strict and pass without weakening or reinterpretation.

- **AC-FOLLOWUP-008:** Given offline mode with no VWorld key or a blank key, when `build_project`
  is invoked, then it returns `success: false` with a non-blank actionable message that is not
  the raw `"'vworld_api_key'"` representation and does not raise, before size estimation, tile
  acquisition, or MBTiles writing. Given a valid key and explicit supported fake-layer test
  configuration, the missing-key failure path is not triggered.

- **AC-FOLLOWUP-009:** Given a successful offline build with a valid key, inspection of the
  generated MBTiles metadata, `.qgs`, `MANIFEST.json`, `VALIDATION_REPORT.json`, and all files in
  the mobile transfer folder finds no VWorld API key; the key is used only for tile retrieval.

## 8. Open Questions

- **O-FOLLOWUP-001:** Should the observed failure of the offline layer-visibility test be included
  in this follow-up as a Category A conformance defect, or tracked separately as a pre-existing/
  unrelated issue? The existing D-91 material defines an initial visibility requirement but is
  explicitly marked draft and awaiting stakeholder review, while the approved five-fix baseline
  does not define that behavior. Until the stakeholder resolves this question (or approves D-91
  in a way that establishes its authority), this follow-up leaves the classification open and
  does not change visibility semantics.

## 9. Decision Log

- **D-FOLLOWUP-001** (2026-08-31, Category A scope registration): The six reviewer findings are
  recorded as follow-up conformance-defect work against already-established contracts. This
  entry adds no provider, schema, relation, selection, consent, or user-visible product change.
  The existing five-fix specification, related MVP/post-MVP specifications, acceptance tests,
  and traceability files remain unchanged and authoritative.

- **D-FOLLOWUP-002** (2026-08-31, explicit stakeholder clarification; supersedes only the
  prior direct-write interpretation, not the observable identification outcome): The stakeholder
  clarified that write-back for the current child observation must directly enter only
  `selected_korean_name` (`국명`). `selected_scientific_name` (`학명`) and `selected_ktsn`
  (KTSN) must be recomputed from that Korean-name field by the existing QGIS lookup/default/
  apply-on-update contract; QML does not directly write those fields and no separate
  `changeAttribute` success assertion for them is required. The prior interpretation in the
  existing corrective material that all three fields must be directly applied by the QML
  write-back path is retained historically but is superseded by this entry. The observable
  requirement remains that, after explicit candidate selection and normal save/reopen, the
  child observation has the selected Korean name and the existing QGIS contract's derived
  scientific name and KTSN. FR-FIX-003/AC-FIX-003 and the FR-FIX-015/016 dependency language
  are not deleted or renumbered; their “three values persist” outcome is read with this
  clarified direct-vs-derived mechanism boundary.

- **D-FOLLOWUP-003** (2026-08-31, Category A triage boundary): D-90 explicitly preserves the
  Type 1 consent gate, so a Type 1 consent-gate expectation failure is separate baseline/
  regression evidence and not a reason to change Type 1. D-91's offline visibility failure is
  recorded as O-FOLLOWUP-001 because D-91 is still draft pending approval and the five-fix
  baseline does not establish the same requirement. No existing D-90/D-91 decision entry is
  modified.

## 10. References

- `specs/TEMPLATE.md` — required specification structure and stable acceptance-ID convention.
- `specs/fieldbuild-kit-five-fixes.md` — baseline corrective requirements, especially
  FR-FIX-002/003/006–010, C-FIX-003/006/007, E-FIX-002/003/006/013–016, and AC-FIX-002/003/
  006–016.
- `specs/qfield-project-builder.md` — existing MVP offline MBTiles/key contracts
  (FR-QPB-080–089, NFR-QPB-058, AC-QPB-018–023/051/052/056), post-MVP identification contracts,
  D-90/D-91/D-92, and their approval/open-question status.
- `specs/saved-feature-identification-edit.md` — active child-form target, UUID/layer checks,
  normal save/reopen, and fail-closed behavior for saved-feature write-back.
- `docs/product.md`, `docs/architecture.md`, and `docs/change-control.md` — local-first
  architecture, process boundaries, secret handling context, and Category A/B/C/F routing.
- `tests/acceptance/qfield_project_builder/test_basemap_offline.py` — existing offline
  success/size/metadata/attribution and cleanup scenarios.
- `tests/acceptance/qfield_project_builder/test_offline_vworld_api_key_collection.py` and
  `tests/acceptance/qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md`
  — missing-key conformance evidence and MVP harness contract.
- `tests/acceptance/qfield_project_builder/test_d90_d91_identify_and_layer_visibility.py` and
  its traceability file — Type 1 consent boundary and offline visibility evidence.
- `tests/acceptance/qfield_project_builder/test_observation_photo_removal.py` and its
  traceability file — exact Type 2/3 inline-expression conformance contract.

