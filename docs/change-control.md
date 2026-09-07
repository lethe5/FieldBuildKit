# Change Control: Classifying and Routing User Feedback

This document is the detailed reference for the triage policy summarized in `CLAUDE.md`'s
"User-feedback triage and change control" section. It exists so the orchestrator (and any
subagent that needs the full rationale) can classify incoming feedback correctly without
guessing, and so the same category is always routed through the same artifacts in the same
order — regardless of whether the user happens to label their own feedback as a "bug," a
"change," a "UX complaint," or nothing at all.

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

Do not perform broad refactoring unrelated to the reconciliation itself, and do not commit or
push without the user's explicit, per-checkpoint approval (see `CLAUDE.md`'s Git checkpoint
rules).
