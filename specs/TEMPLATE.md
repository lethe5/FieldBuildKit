# Feature: <feature name>

> Status: DRAFT | APPROVED
> Owner: spec-writer
> Last updated: <date>

## 1. Summary

One or two sentences: what this feature is and why it exists.

## 2. Functional Requirements

Numbered, unambiguous statements of what the system must do.

- FR-1: ...
- FR-2: ...

## 3. Constraints

Non-negotiable limits: technical, regulatory, ecological/field-data integrity, performance, offline/connectivity, etc.

- C-1: ...

## 4. Assumptions

Things taken as given because they were stated by the user, or because clarification is pending. Anything here that turns out to be wrong should trigger a spec update, not a silent implementation workaround.

- A-1: ...

## 5. Edge Cases

Situations outside the normal/happy path that the implementation must handle deliberately (not just "whatever the code happens to do").

- E-1: ...

## 6. Out of Scope

Explicitly excluded from this feature, to prevent scope creep during implementation.

- ...

## 7. Acceptance Criteria

Each criterion must be independently testable and independently verifiable as PASS/FAIL. Use stable IDs — they are referenced by the acceptance-test traceability mapping and by the reviewer's verdict. Do not renumber existing IDs once a specification is approved; add new ones instead.

- **AC-1**: Given <context>, when <action>, then <observable, measurable outcome>.
- **AC-2**: ...

## 8. Open Questions

Anything still unresolved that needs the user's input before this spec can be approved.

- ...
