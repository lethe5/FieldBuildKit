# Feature: Saved plant-observation identification edit write-back

> Status: DRAFT — awaiting stakeholder review
> Owner: spec-writer
> Decision Log: D-92 in `specs/qfield-project-builder.md`
> Last updated: 2026-08-30

## 1. Summary

When a user reopens an already-saved plant-observation feature and selects a Pl@ntNet
identification candidate, the selected Korean name, scientific name, and KTSN must be written
back to that same existing feature and survive the normal QField save action. This applies both
to direct observation-layer editing and to the Type 3 relation path `조사지 → 조사 → 식물관찰`.

This is a Category C product change. It supersedes only the existing/already-saved-feature
branch of Decision Log D-50/FR-QPB-109/AC-QPB-046, which previously described this behavior as a
permanent limitation. The historical limitation remains recorded in the integrated
specification and is not deleted.

## 2. Functional Requirements

- **FR-SFE-001:** For an existing, already-saved Type 1, Type 2, or Type 3 plant-observation
  feature reopened in QField's edit form, selecting a displayed Pl@ntNet candidate must update
  that feature's `selected_korean_name`, `selected_scientific_name`, and `selected_ktsn` values.
  The values must use the existing KTSN/accepted-name resolution and scientific-name preference
  rules; this feature does not introduce a second name-resolution algorithm.

- **FR-SFE-002:** FR-SFE-001 must work when the existing feature is opened directly from its
  observation layer, and when a Type 3 observation is opened through the relation path
  `조사지 → 조사 → 식물관찰`.

- **FR-SFE-003:** The write-back target must be the currently edited observation feature identified
  by the request UUID and layer context. The implementation must not write to the parent
  `조사지`/`조사` feature, a different observation, a list model, or a newly-created feature.

- **FR-SFE-004:** After candidate selection, the values must appear in the open edit form and must
  survive the user's normal QField save action. Reopening the feature after saving must show the
  same three selected values in the GeoPackage-backed form.

- **FR-SFE-005:** Existing candidate-selection persistence semantics remain in force alongside
  FR-SFE-001: `identification_status` is `"complete"`; the candidate score and available
  occurrence probability are persisted; available identification timestamp/model-version values
  are persisted; and unavailable optional values remain `NULL`, per FR-QPB-109 and AC-QPB-073.
  This requirement does not change the separate `"manual"` status rules.

- **FR-SFE-006:** For a Type 3 relation edit, saving the observation must preserve its existing
  observation UUID and `survey_id` foreign-key relation, and must not modify the parent survey,
  parent site, or sibling observations as a side effect.

- **FR-SFE-007:** The existing brand-new/not-yet-saved Add-feature behavior established by
  Decision Log D-50/D-51 remains supported. The existing-feature change must not regress that
  path. Manual identification entry on an already-saved feature remains outside this change and
  retains the previously specified behavior unless separately approved.

- **FR-SFE-008:** The project plugin must resolve the active existing-feature edit form before
  applying a pending request. The public QField model used for the write must be an active
  `FeatureForm.model`/`QfAttributeFormModel` (or an equivalent documented QField model) whose
  `changeAttribute()` operation targets the request UUID. A `QfFeatureListForm.model`/
  `QfMultiFeatureListModel` that only lists features is not a valid write target.

## 3. Technical Feasibility and QField API Boundary

The official QField API documents:

- project-plugin access through `iface.findItemByObjectName()` and access to the main window;
- `FeatureForm.model` as a `QfAttributeFormModel` property;
- `QfAttributeFormModel.changeAttribute()` and `save()` for changing and saving the current
  feature; and
- `EmbeddedFeatureForm` as the relation/embedded-form component family.

References: [QField API overview](https://api.qfield.org/), [FeatureForm](https://api.qfield.org/QField/classFeatureForm/), [QfAttributeFormModel](https://api.qfield.org/QField/classQfAttributeFormModel/), and [QfAppInterface](https://api.qfield.org/QField/classQfAppInterface/).

The current project-plugin mechanism already uses the documented `iface` entry point and a
pending request file. The implementation may first try the existing-feature host
(`iface.findItemByObjectName("featureForm")`) and then perform bounded, cycle-safe traversal of
public Qt/QField object-container properties to locate the active nested `FeatureForm.model` or
relation `EmbeddedFeatureForm.attributeFormModel`. Traversal is sufficient only if the target
model is actually exposed through that runtime object graph and its UUID can be verified.

The implementation must not assume that the existing feature-list object's public `model` is the
editable attribute model: QField documents `QfFeatureListForm.model` as a
`QfMultiFeatureListModel`, while `FeatureForm.model` is the attribute-form model. It must never
call `changeAttribute()` on the list model or select a model solely because it is the first model
found.

Whether recursive traversal reaches the existing-feature form in the target QField build is an
implementer-verification item, not an assertion that private QML internals are stable. If the
active `QfAttributeFormModel` remains unreachable through the public plugin-visible object graph,
the generated project plugin alone cannot satisfy FR-SFE-001. The implementer must then report a
concrete QField API/core limitation and identify the required QField-side change (for example, a
public current-edit-form/model accessor or write-back invokable). It must not claim persistence,
write to an unrelated model, or silently clear the request. A QField application/native change is
not authorized by this specification unless that concrete finding is presented for a subsequent
stakeholder decision.

## 4. Constraints

- **C-SFE-001:** UUID identity and all existing relations must remain intact. The hidden GeoPackage
  `fid` is not a substitute for the domain UUID and must not be changed or exposed as the request
  identity.
- **C-SFE-002:** Candidate selection remains explicit; this change does not authorize automatic
  identification after attachment and does not change the Type 2/3 immediate-identify interaction
  decision in D-90.
- **C-SFE-003:** The request must be applied only after the active form/model and UUID match are
  verified. Ambiguous or unverified targets are fail-closed.
- **C-SFE-004:** Existing generated projects without the updated plugin are not migrated by the
  desktop builder. Newly generated projects must contain the updated mechanism.
- **C-SFE-005:** The QField version/platform used for manual verification must be recorded; this
  specification does not invent a minimum QField version beyond the project's existing target
  conventions.

## 5. Assumptions

- **A-SFE-001:** The user instruction **"2번이야"** in response to the explicit distinction
  between (1) an unsaved Add form and (2) an existing saved feature reopened for editing means
  the requested scope is the second case.
- **A-SFE-002:** The user's requested “국명과 학명, ktsn에 동정된 정보” means the three persisted
  fields named in FR-SFE-001; existing candidate metadata persistence remains governed by
  FR-SFE-005.
- **A-SFE-003:** The Type 3 relation path refers to the generated stable relation chain and does
  not require changing relation definitions, cardinality, or composition strength.

## 6. Edge Cases

- **E-SFE-001:** A request for an existing feature arrives while the relation child form is still
  mounting. The request remains pending and is retried until the bounded request lifetime/normal
  plugin cleanup policy applies; it is not consumed after a failed lookup.
- **E-SFE-002:** Multiple forms/models are simultaneously present. Only the model whose current
  feature UUID and observation layer match the request may receive the write.
- **E-SFE-003:** A model exposes the expected shape but rejects one or more attribute changes. No
  partial success may be reported as complete; the request must remain diagnosable and the user
  must receive a clear non-success indication.
- **E-SFE-004:** The selected candidate has no accepted-name match or has an ambiguous enrichment.
  Existing FR-QPB-106/107 fallback and disclosure rules apply; the write-back must still target
  only the selected observation.
- **E-SFE-005:** The user cancels the edit or the form fails its existing hard constraints.
  The feature must not be reported as successfully persisted; existing QField save/validation
  behavior remains authoritative.
- **E-SFE-006:** The existing feature has a missing/invalid UUID. The implementation must fail
  closed and must not fall back to `fid`, parent UUID, or list position.

## 7. Out of Scope

- Changing QField core, shipping a forked QField binary, or adding a native API without a separate
  stakeholder decision after a concrete unreachable-model finding.
- Persisting manual name entry for an already-saved feature; that is a separate product decision.
- Changing the accepted-name lookup-table contents, recursive `correct_list` resolution, relation
  IDs/names, schema fields, or UUID default-value configuration.
- Changing the old feature's already-saved values merely by opening the form; only an explicit
  candidate selection triggers this write-back.

## 8. Acceptance Criteria

- **AC-SFE-001:** Given a saved Type 1, Type 2, or Type 3 plant-observation feature reopened in
  QField, when the user runs Identify and selects a candidate, then the open form shows the
  candidate's selected Korean name, standardized scientific name, and KTSN, and after normal save
  and reopen the GeoPackage-backed feature contains those same three values.
- **AC-SFE-002:** Given a saved Type 3 project and an observation opened through
  `조사지 → 조사 → 식물관찰`, when a candidate is selected and the observation is saved, then the
  selected Korean name, scientific name, and KTSN are persisted on that observation; its UUID and
  `survey_id` are unchanged; and the parent/sibling records are unchanged.
- **AC-SFE-003:** Given a saved observation opened directly from its observation layer, when a
  candidate is selected and saved, then only the intended observation's candidate fields and the
  existing candidate metadata fields are updated; no duplicate observation is created and no
  other observation is changed.
- **AC-SFE-004:** Given a candidate whose accepted-name resolution reaches a terminal `정명` row,
  when the candidate is selected in either direct or Type 3 relation edit, then the persisted
  three fields use that resolved Korean name, scientific name, and KTSN, not an intermediate alias.
- **AC-SFE-005:** Given an active edit form whose model is not yet mounted or whose UUID does not
  match the pending request, when the plugin polls, then it does not clear the request, does not
  write any other feature/model, and eventually reports a clear non-success diagnostic if no
  matching model becomes available.
- **AC-SFE-006:** Given a real candidate selection on a saved existing feature and a QField version
  used for release verification, when the end-to-end flow is exercised on-device for both direct
  and Type 3 relation paths, then AC-SFE-001/002 pass and the verification record names the QField
  version/platform. This is a real-device criterion; the automated harness may cover only the
  generated-QML structure and fail-closed behavior.
- **AC-SFE-007:** Given a generated project plugin, when its write-back implementation is
  structurally inspected, then it contains an existing-feature lookup path distinct from the
  Add-feature `overlayFeatureFormDrawer` path, verifies the request UUID against the active
  attribute-form model, applies all requested fields through `changeAttribute()`, and never uses a
  `QfFeatureListForm.model`/list model as the write target.
- **AC-SFE-008:** Given a target QField runtime where the active existing-feature
  `QfAttributeFormModel` is not reachable through the plugin-visible object graph, when the
  implementation verification is performed, then the result is reported as a concrete QField API
  limitation with no false persistence claim and no unrelated-feature write. This criterion does
  not authorize silently weakening AC-SFE-001/002.

## 9. Open Questions

- **O-SFE-001:** Does the specific release-verification QField build expose the existing-feature
  `FeatureForm.model` (or an equivalent active `QfAttributeFormModel`) through the public object
  graph reachable from `iface.findItemByObjectName("featureForm")`/`iface.mainWindow()`? The answer
  determines whether bounded recursive traversal is sufficient or a QField core/API change is
  required. This is an implementer-verification gate; if unresolved after the permitted
  implementation attempts, the concrete limitation must be returned to the stakeholder rather
  than hidden behind a fallback.

