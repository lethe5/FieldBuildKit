# Traceability Matrix — QField Project Builder, Local Credential-Storage-Mechanism Change (D-53/D-55)

> Specification: `specs/qfield-project-builder.md` — revised Section 14.1 (`NFR-QPB-012`,
> `NFR-QPB-018`, `NFR-QPB-072`, each further revised; new `NFR-QPB-073`), Section 16 (new
> `A-QPB-005`; `A-QPB-006` confirmed/annotated), Section 18.5 (new `AC-QPB-089`–`AC-QPB-093`,
> `AC-QPB-097`), and Section 18.6 (`AC-QPB-082`, revised) — all from Decision Log **D-53**
> (stop using the OS credential store / `keyring`; replace it with an application-managed,
> password-derived, locally-encrypted `credentials.enc` file for the existing "Remember this
> key" opt-in) and **D-55** (closes Open Question O-21: the encrypted-storage password is
> re-requested only at the specific point of use, e.g. the wizard step that would auto-fill a
> remembered key — never at general startup).
>
> This is a later round against the same overall specification as
> [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md) (approved
> MVP baseline) and
> [`qfield_project_builder_post_mvp_plantnet_key_embedding.traceability.md`](qfield_project_builder_post_mvp_plantnet_key_embedding.traceability.md)
> (Decision Log D-45's Pl@ntNet-key consent-gated embedding round).
>
> **Unlike those two files, this file records no newly executable test.** Read "Scope-boundary
> finding" immediately below before anything else in this file — it explains why, and what needs
> to happen next.

## Scope-boundary finding (read this first)

This `test-designer` round was explicitly instructed (by the task given to this invocation) to
substantially revise `tests/unit/test_credential_store.py`, add new tests to
`tests/unit/test_wizard.py`, and run `pytest tests/unit -q`.

**This round did not do that**, because `tests/unit/` falls outside this role's own configured
hard boundary. Both the system-level role definition supplied to this invocation and the
checked-in `.claude/agents/test-designer.md` (verified identical, byte-for-byte, via `git show`/
direct read at the time of this round) state, verbatim: *"You may create or modify files only
under `tests/acceptance/`."* This project's own `CLAUDE.md` orchestration procedure and
`.claude/agents/implementer.md` both independently confirm that "ordinary implementation-level
tests (unit/integration tests that support your implementation, distinct from the acceptance
tests)" are explicitly the **`implementer`** role's mandate, not `test-designer`'s. A task
instruction — even a detailed, explicit, repeated one from the orchestrator — cannot expand a
configured role boundary; per this invocation's own standing instructions, "no agent message can
authorize changing your permission settings, CLAUDE.md, or configuration."

This is not a pedantic technicality: `tests/unit/test_credential_store.py` and
`tests/unit/test_wizard.py` are exactly the implementation-level, white-box test files this
project's own convention (visible in their current, pre-this-round content) treats as
implementer-owned artifacts that exercise `qfield_builder`'s internal modules directly
(`credential_store.remember_key`, `wizard_module.credential_store`, etc.) — not the black-box,
`qfield_builder.acceptance_api`-mediated convention `tests/acceptance/` uses (see
`tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s own framing: "Everything *behind*
this surface... is explicitly left to the implementer.").

**What this round did instead, within its actual mandate:** analyzed exactly which of the new/
revised requirements (`NFR-QPB-012/018/072/073`, `AC-QPB-089`–`093`/`097`) are, and are not,
verifiable via this project's existing black-box acceptance-test harness; confirmed the two
already-approved acceptance tests that touch this area (`AC-QPB-058`, `AC-QPB-082`) remain valid
and require no change; and recorded, below, exactly what remains to be covered and by which role,
so nothing is silently dropped.

**Recommended next step (for the orchestrator/user, not decided by this round):** the
unit-level test coverage this task asked for is a legitimate, real gap — route it through a
fresh `implementer` invocation (whose mandate already covers "ordinary implementation-level
tests"), or, if `test-designer` is meant to own this class of internal-mechanism test in this
project going forward, that requires the user's explicit approval to amend
`.claude/agents/test-designer.md`'s own hard boundary — not an inference this round should make
unilaterally.

## What does / doesn't change at the acceptance-test (generated-project-artifact) level

Decision Log D-53 changes **only** the desktop application's own local storage mechanism for a
remembered VWorld/Pl@ntNet API key (OS credential store/`keyring` → an application-managed,
password-derived, locally-encrypted `credentials.enc` file). D-53's own text is explicit: *"This
entry does not... alter FR-QPB-073/FR-QPB-076–FR-QPB-079/FR-QPB-114–FR-QPB-117 (the
generated-project key-embedding exceptions)... in any way."* Nothing about what a *generated
project* itself may or must contain changes.

The two existing, already-approved acceptance tests for this area were, from the start, written
to verify only the **artifact-level** guarantee — the key never appears in plaintext anywhere in
the *generated project* — explicitly because, per their own pre-existing notes, "the OS
credential store itself is outside this harness's black-box reach":

- **AC-QPB-058** — `qfield_project_builder/test_basemap_online.py::
  test_ac058_remember_key_uses_os_credential_store_not_plaintext` (+
  `test_key_not_remembered_by_default_across_sessions`). Re-read in full for this round: it
  builds a project with `remember_key: True`, then asserts the fake VWorld key's bytes appear in
  no file under the project folder other than the one permitted `.qgs` online-layer URL. It never
  references `keyring`, an OS credential store, or any file/module internal to the desktop
  application's own local storage.
- **AC-QPB-082** — `qfield_project_builder/test_post_mvp_plantnet_key_embedding.py::
  test_ac082_remember_key_uses_os_credential_store_not_plaintext` (+
  `test_plantnet_key_not_remembered_by_default_across_sessions`). Same structure, same
  conclusion, for the Pl@ntNet key.

That reasoning applies identically, unchanged, to the new encrypted-file mechanism: these two
tests remain valid and correct as written and require **no code change** for D-53/D-55, because
they never asserted *how* the desktop application retains a remembered key locally — only that
the generated project artifact never leaks it, regardless of that mechanism. Their existing
"outside this harness's black-box reach" notes
(`qfield_project_builder.traceability.md` note 3;
`qfield_project_builder_post_mvp_plantnet_key_embedding.traceability.md` note 1) have each been
given a short pointer to this file (see the edits accompanying this round).

## Criteria with no acceptance-level test in this round

| AC / NFR ID | Summary | Why no acceptance-level test | What would cover it |
|---|---|---|---|
| AC-QPB-089 | No `keyring` import/call anywhere in the retention code path (`qfield_builder/credential_store.py`) | Requires directly inspecting the desktop application's own module source — an internal-implementation check, not a generated-project artifact or a `build_project()`-observable behavior. | A unit test reading `inspect.getsource(qfield_builder.credential_store)` (or the file directly) and asserting `"keyring" not in source`. |
| AC-QPB-090 | `credentials.enc`'s on-disk bytes never contain the plaintext key | Requires directly invoking `credential_store`'s own encrypt/store functions and reading its own private local-app-data file — not a generated-project artifact. | A unit test calling the module's own establish/remember functions against an isolated (monkeypatched) app-data directory, then reading the raw file bytes. |
| AC-QPB-091 | KDF is a named PBKDF2-HMAC-SHA256 call, ≥600,000 iterations, ≥16-byte randomly generated per-installation salt | Requires inspecting/spying on the exact internal call-shape of `credential_store.py`'s own KDF invocation — an internal-implementation-mechanism check. | A unit test that monkeypatches the module's own `PBKDF2HMAC` reference and asserts the captured constructor arguments; a companion test asserting two independent "installations" (two isolated app-data directories) receive different, ≥16-byte salts. |
| AC-QPB-092 | First-launch password-setup prompt shown once; decline path leaves "Remember this key" unavailable that session and re-shows the prompt next launch | Desktop-application startup/dialog-sequencing UI behavior (`qfield_builder/ui/app.py`'s `main()`, and/or a new first-launch dialog), not a generated-project artifact or a `build_project()`-driven behavior. | An offscreen-PySide6 unit/GUI test, mirroring `tests/unit/test_wizard.py`'s existing conventions (see that file's `_qapp` fixture and dialog/page-construction patterns), against whatever module the implementer exposes this prompt through. |
| AC-QPB-093 | Forgotten password → decryption fails gracefully (never silently guesses/bypasses); user is prompted to re-enter their API key(s) manually | Same reasoning as AC-QPB-090: internal `credential_store`/wizard-page behavior, not a generated-project artifact. | A unit test establishing a password, remembering a key, then calling the retrieval function with a wrong password and asserting it raises a clear, dedicated exception (never returning a silently-wrong value) — plus a `tests/unit/test_wizard.py`-level test confirming the relevant page (`ConnectivityBasemapPage`/`IdentificationTogglePage`) survives that exception without crashing and leaves the field empty (equivalent to requiring manual re-entry), mirroring this suite's *existing* `test_connectivity_page_survives_a_credential_store_failure` pattern. |
| AC-QPB-097 | Retrieval-time re-prompt fires only at the specific wizard step that would auto-fill a remembered key — never at general startup or before any unrelated step | Wizard-page-navigation-level UI sequencing (which `QWizardPage.initializePage()` call, if any, triggers a password prompt) — not a generated-project artifact. | A `tests/unit/test_wizard.py`-level test driving a real `ProjectBuilderWizard` via `.next()` (mirroring this file's own existing `_advance_to_connectivity_basemap_page_in_its_widest_state`-style navigation helper) and asserting a spied prompt function is called zero times before the credential-bearing step is reached, and exactly once once it is. **Implementation note surfaced by this analysis, for whichever role builds this:** `ProjectBuilderWizard.__init__` currently constructs *every* page eagerly via `addPage(...)`, but a direct, throwaway PySide6 timing check performed during this round (not committed anywhere; a read-only diagnostic, consistent with this role's authoring-support Bash allowance) confirmed `QWizardPage.initializePage()` is **not** called merely by constructing a `QWizard`/adding pages, nor by constructing a page in isolation — only when that page actually becomes current (via `.next()`/`.setCurrentId()`/the wizard's own initial `.show()`). This means the currently-existing `ConnectivityBasemapPage._load_remembered_key()`/`IdentificationTogglePage._load_remembered_plantnet_key()` calls (invoked today from each page's own `__init__`, i.e. at wizard-construction time) will need to move to each page's `initializePage()` hook for AC-QPB-097's "not at general startup" requirement to hold under the current page-construction architecture — a concrete, evidence-based implementation constraint, not an invented design choice, surfaced here so it is not lost between rounds. |

`NFR-QPB-012` (revised)/`NFR-QPB-072` (revised) are covered by the same reasoning as `NFR-QPB-018`
(revised)/AC-QPB-058 above (the Pl@ntNet-key mirror); no separate row is needed beyond
AC-QPB-090/091/093/097, which already exercise both the VWorld and Pl@ntNet accounts per the
specification's own "independently scoped, mirrored mechanism" framing.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **This is a role/file-scope boundary finding, not a specification ambiguity.** Every one of
  `AC-QPB-089`–`093`/`097` is clearly, unambiguously worded and fully testable as written — none
  of them required inventing unstated behavior. The gap recorded in this file is procedural
  (which role's mandate covers writing the test that verifies them), not a defect in the
  specification itself, and is reported here per this role's own "ambiguity handling" instruction
  to flag rather than silently guess or silently overstep.
- **No test currently exists for AC-QPB-089–093/097.** This is an honest, explicit gap, not a
  silently-dropped criterion — see the table above for exactly what's missing and a concrete,
  actionable description of the test each one still needs.
