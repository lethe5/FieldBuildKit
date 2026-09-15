# Change Control: Classifying and Routing User Feedback

This document is the detailed reference for the triage policy summarized in `AGENTS.md`'s
"User-feedback triage and change control" section. It exists so the orchestrator (and any
subagent that needs the full rationale) can classify incoming feedback correctly without
guessing, and so the same category is always routed through the same artifacts in the same
order — regardless of whether the user happens to label their own feedback as a "bug," a
"change," a "UX complaint," or nothing at all.

Per [AGENTS.md](../AGENTS.md), scope authorization does not approve an unseen specification or
acceptance artifact. Category C below preserves the user decision; the concrete revised artifacts
still require their stage approvals before test design/implementation. No DRAFT is checkpointed.

The user is never required to pre-classify their own feedback. Classification is the
orchestrator's job, every time, using the categories below.

## The six categories

### A. Conformance defect

The implementation failed to satisfy an already-approved, sufficiently explicit requirement
(an existing `FR-`/`DR-`/`NFR-`/`AC-` in the approved specification, or an unambiguous existing
acceptance test). The requirement itself is not in question — only whether the code satisfies it.

**Route:**
- Do not change the requirement to match the implementation.
- Fix the implementation.
- Add or strengthen a regression test.
- Update traceability only if the fix changes which test(s) satisfy the criterion.
- A fresh reviewer verifies the fix against the *existing* approved requirement — not against
  the implementer's own account of what they fixed.

### B. Specification clarification or omission

The user's intended behavior is consistent with the product's established direction, but the
approved specification is ambiguous, incomplete, or missing a testable detail needed to build or
verify it.

**Route:**
- A fresh `spec-writer` adds the minimum necessary clarification to the authoritative
  specification (never the raw stakeholder-requirements source file).
- Record the clarification in the specification's own decision log with a stable ID.
- Preserve original intent; do not expand scope beyond what's needed to remove the ambiguity.
- Update acceptance criteria, tests, and traceability before treating this as resolved.
- Verify the implementation against the clarified requirement.

### C. Stakeholder-approved product change

The user explicitly directed behavior that changes or supersedes an earlier approved
requirement. The user's own explicit, unambiguous prior instruction *is* the approval — do not
ask them to re-approve a decision they already made, but do formally reconcile the specification
so the decision and its rationale are preserved rather than silently overwritten.

**Route:**
- A fresh `spec-writer` updates the authoritative specification and its decision log to record
  what was superseded, the user's instruction that authorized it, and why.
- Evaluate and record data-compatibility, migration, generated-project-compatibility, and
  platform implications where relevant.
- Update acceptance criteria, tests, and traceability.
- Verify the implementation against the revised specification.
- Never silently rewrite history: the superseded requirement's text and rationale stay visible
  in the decision log, marked as superseded, not deleted.
- If the "change" is only *inferred* from context rather than explicitly directed by the user,
  it is not yet approved — present it as a proposed change and get explicit approval before
  treating it as authoritative. Do not conflate "the user would probably want this" with "the
  user said this."

### D. UX or visual-design refinement

Functional behavior remains valid; presentation, wording, information hierarchy, interaction
flow, spacing, styling, accessibility, or usability is being improved.

**Route:**
- Record durable UI/visual conventions in `docs/ui-design-guidelines.md` (or an equivalent
  UI-scoped guideline doc) — not in the core product specification, which stays reserved for
  functional/data requirements.
- Express requirements as observable review criteria wherever practical (a described visual
  state, a screenshot-comparable layout rule) rather than vague adjectives.
- Use automated tests for the functional aspects that happen to be adjacent (e.g. "the button
  still triggers the same action") and screenshot/manual review criteria for the genuinely
  visual aspects.
- Never change domain behavior, data structures, or generated-project output under the label of
  a visual refinement — if a "UX fix" would do that, it is not actually category D.

### E. Internal hardening, diagnostics, packaging, or developer tooling

The change affects diagnostics, logging, packaging, tests, build tooling, internal resilience,
or maintainability, without changing user-facing product behavior.

**Route:**
- Do not add it to the product specification unless it creates a real user-visible, security,
  privacy, deployment, or support contract (e.g. "the app must show this permission-prompt
  guidance" is a real support contract; "we refactored the build script" is not).
- Document it in the appropriate engineering/packaging documentation (e.g. `README.md`'s
  packaging section, `docs/architecture.md`) when it needs to be discoverable later.
- Add focused technical tests.
- Keep shipped diagnostic surfaces minimal and consistent with prior decisions — a diagnostic
  hook that was useful for one investigation is not automatically worth shipping permanently.
  If retaining one is a genuine, deliberate product/support decision, say so explicitly and get
  the user's confirmation; do not let "it might be useful again" default to "keep it forever."

### F. Pre-existing or unrelated issue

The issue was discovered while working on something else, but isn't caused by and doesn't need
to be fixed as part of the current change.

**Route:**
- Record it separately, with its evidence, impact, and urgency — don't let it silently expand
  the scope of whatever you were actually asked to do.
- A flaky test caused by an unrelated pre-existing design choice (e.g. scanning a shared system
  temp directory) is a separate hardening item unless it's actively blocking reliable
  verification right now, in which case it must still be called out as pre-existing/unrelated
  even while you work around it for this one verification pass.

## How to classify in practice

1. **The user does not need to label anything.** Read what they actually said, check it against
   the approved specification and existing acceptance tests, and classify every distinct item
   yourself.
2. **One message can contain several items in different categories.** Split them. Don't force a
   single classification onto a compound request.
3. **State the classification and reason up front**, briefly, before doing the work — this is
   for the user's benefit (so they can correct a misclassification early) and for whoever reviews
   the work later.
4. **Proceed without stopping to ask** when the evidence supports a safe, unambiguous
   classification — most conformance defects (A), UX refinements (D), and internal-tooling items
   (E) fall here.
5. **Stop and ask** only when: the item is category C but the user's intent is genuinely
   ambiguous (not just "this seems like a change"); the classification is genuinely unclear and
   two plausible readings would lead to materially different product behavior, data structures,
   compatibility, security, privacy, or scope; or resolving it would require an action outside
   this repository, a destructive/irreversible step, or new credentials.
6. **Never let one role quietly do another role's job.** A conformance defect (A) never becomes
   a spec change to dodge fixing the code. An acceptance test never gets edited "to match
   current behavior" instead of being treated as a real defect (A) or a real, approved change
   (C) that updates the spec *first*. An inferred product change never gets implemented before
   its approval is real, not assumed.
7. **Every completed item leaves something durable behind**: for A, a regression test; for B/C,
   an updated spec and decision log entry plus updated acceptance criteria/traceability; for D,
   an updated UI guideline document; for E, updated engineering/packaging documentation where
   it's genuinely needed. An item that's "done" but leaves no trace of what was decided or why is
   not actually done — it will just get re-litigated the next time someone touches that code.

## Reconciling several items together (e.g. a retrospective audit)

When multiple items need reconciling at once (for example, catching up a working tree that
accumulated several rounds of user-directed fixes before anyone formally routed them through
`spec-writer`/`test-designer`), work in this order:

1. Specification and decision history first, for every B/C item.
2. Acceptance criteria, tests, and traceability next.
3. Implementation only where a genuine gap remains after 1–2 (most conformance defects, category
   A, will already have been fixed with their own regression test at the time — don't assume the
   implementation is correct just because it shipped; independently verify it against the
   reconstructed requirement).
4. Mechanical verification.
5. Independent, fresh, clean-room review, working from the approved specification, acceptance
   criteria, and the actual diff — never from any implementer's conversational account of their
   own work.

Do not perform broad refactoring unrelated to the reconciliation itself. Follow the
"Branches, checkpoints and merging" section of `AGENTS.md`: retain explicit specification/test
artifact approvals and separate checkpoints; local commits/merges use the existing standing
authorization without a second per-commit approval request. Pushes require explicit per-push
authorization.

## Approved Category B/C case: survey-route provider contract (2026-09-14~15)

The approved route baseline (`e382c77`) and acceptance checkpoint (`ed8ac81`) remain in force.
Uncommitted implementation attempt 2 exposed two direct contract conflicts and several default
omissions: VROOM 1.14 numeric arrival seconds versus AC-SRP-007 ISO fixtures; registered production
providers versus AC-SRP-013's unknown backend token; and incomplete representative-point,
completion, Type 1, road-offset, portable-settings and persistence-format rules. A later source
inspection also found the deprecated `api.openrouteservice.org` routing default and an empty
optimizer default. The current official service paths require a routing base that resolves to
`api.heigit.org/openrouteservice/v2/...` and the complete VROOM endpoint
`https://api.heigit.org/vroom/v0`, while preserving explicit custom/self-hosted configuration.

The spec-writer route updated
`specs/survey-route-planner.md` D-SRP-008–013 and D-SRP-015–019 with existing and additive FR/AC IDs.
The same slice records: a Category A false-CRS rejection against FR-SRP-017; a Category C masked
builder route-key input; Category B/D scope and completion-field help; and Category D full-width
panel fields. On 2026-09-15 the user approved the specification and resolved O-SRP-007 in favor of
an explicit warning and consent followed by plaintext key embedding in the generated project for
automatic QField use. Anyone with the project folder can read and use that key; the artifact does
not claim encryption. A user who declines may leave the key blank and enter it manually for each
QField session. In all paths the key remains excluded from logs, errors, reports, URLs, query
parameters and request bodies. This reconciliation changes no application or acceptance file. A
fresh test-designer must revise AC-SRP-007/AC-SRP-013 tests and the other affected traceability/default
coverage for separate approval. The uncommitted attempt, its 104 passed/2 contract-failing/12
skipped result and automated double-JSON checks are implementation evidence, not requirement
authority, native QField proof or final PASS.

The official 2026-04-28 notice originally scheduled `api.openrouteservice.org` shut-off for
2026-08-24. Its 2026-08-27 follow-up says the host was not shut down immediately, reduced its quota
to 10%, and moved shut-off to 2026-09-28. The specification records both notices and treats the host
as deprecated regardless of temporary reachability; this avoids turning a changing external
timeline into fallback behavior.
