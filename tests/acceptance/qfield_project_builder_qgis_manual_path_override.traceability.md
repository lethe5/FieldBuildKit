# Traceability Matrix — QField Project Builder, Manual QGIS Install-Path Override

> Specification: `specs/qfield-project-builder.md`, Section 5.2 (`FR-QPB-008`, `FR-QPB-009`),
> Decision Log D-10 (Section 19), Section 18.5 (`AC-QPB-029`, cross-referenced below).
>
> This is a **conformance-gap round**, not new feature elicitation and not a specification change.
> `FR-QPB-008` has been part of the approved MVP baseline since the original specification (it is
> not new), and reads: "The application must attempt automatic detection of a supported QGIS
> installation, and must allow the user to select the QGIS installation path manually when
> automatic detection fails." (Decision Log D-10.) This round confirmed, independently, that this
> requirement's manual-override half has **zero implementation and zero prior test coverage**:
>
> 1. `qfield_builder/runtime.py`'s `_NON_TECHNICAL_MISSING_MESSAGE` (the error shown when no QGIS
>    installation is detected) literally names a `'QGIS 설치 위치 선택...'` ("Select QGIS install
>    location...") option, in the exact wording a user would see.
> 2. No such option exists anywhere in the codebase — confirmed by inspection of
>    `qfield_builder/ui/wizard.py` (no button, dialog, file/folder picker, or any other UI
>    mechanism letting a user manually specify a QGIS installation path) and of
>    `qfield_builder/runtime.py` (`detect_qgis_installation()`/`check_runtime()` take no
>    path-override parameter at all — there is no code path anywhere that could even accept a
>    manually-specified path if a UI existed to collect one).
> 3. No acceptance test anywhere referenced `FR-QPB-008` before this round (only a passing mention
>    in `HARNESS_CONTRACT.md`'s own top-of-document rationale text, never a test or a dedicated
>    traceability row).
>
> This is Category A (conformance defect against an already-approved requirement) per this
> project's own `docs/change-control.md` categories — the fix is to the implementation, not the
> requirement; the requirement's own text is unchanged and is treated here as clear and
> sufficient, not ambiguous.
>
> Tests: `tests/acceptance/qfield_project_builder/test_qgis_manual_path_override.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (test-designer conformance-gap round, 2026-08-27)" section — extends the existing function 1
> (`check_runtime`) with a new `manual_path` parameter, a clarified `force_missing` interaction,
> and a new `qgis_prefix_path` return key.

## What this round covers, and its own scope note

FR-QPB-008 has two independent halves:

1. **Automatic detection is attempted first.** Already implemented and already covered by
   existing tests — confirmed, not retested (see "Confirmed pre-existing coverage" below).
2. **A manual QGIS-install-path override is reachable and functional when automatic detection
   fails.** Zero coverage before this round. This round adds real, automatable acceptance-test
   coverage for the underlying *verification logic* (does supplying a valid/invalid manual path
   actually change the detection outcome correctly), plus a `manual`-marked placeholder for the
   on-screen wizard control itself — this project's hard QGIS-isolation rule bars driving an
   interactive PySide6 dialog from an automated test, and this suite's own established convention
   (mirrors `AC-QPB-104`'s wizard-step-sequencing placeholder) is to test the underlying logic
   headlessly while documenting the UI wiring itself as a `manual`-marked placeholder.

This round also adds one new test exercising an interaction that could not previously exist (since
`manual_path` itself is new): confirming a supplied manual path does **not** wrongly override an
automatic detection that has already succeeded — restating FR-QPB-008's own "manual...when
automatic detection fails" wording precisely (manual override is a fallback, not a first-class
replacement for automatic detection).

## Confirmed pre-existing coverage (not retested)

`FR-QPB-008`'s "automatic detection is attempted first" half already has real coverage in
`test_runtime_detection.py`, confirmed by this round's own review rather than assumed:

- `test_missing_runtime_produces_a_clear_actionable_error_not_a_crash` (`AC-QPB-029`) — automatic
  detection forced to fail (via the pre-existing `force_missing` seam) produces a clear,
  non-technical error, not a crash.
- `test_detected_qgis_344_lts_passes_verification_without_pip_installed_pyqgis` (`AC-QPB-053`,
  `qgis`-marked) — automatic detection succeeding on a real, detected QGIS installation.

Between these two, both directions of "automatic detection is attempted" (success and failure) are
already exercised. No new test is added for this half; see the traceability table below for how
`FR-QPB-008`'s "attempted first" clause is mapped onto this existing coverage, plus this round's
own new precedence test covering the *interaction* with the (new) manual override specifically.

## Genuinely out of this harness's reach, not silently claimed as covered

**The literal, on-screen wizard/error-dialog control itself.** FR-QPB-008 requires the user be
able to "select the QGIS installation path manually" — a real, clickable UI mechanism (a button,
menu action, or folder-picker dialog) reachable from the missing-runtime error state. This
project's hard QGIS-isolation rule is unrelated to this specific gap (it concerns QGIS/
`QApplication` construction, not the PySide6 wizard), but no automated GUI-driving mechanism
exists in this harness at all, for any PySide6 dialog, mirroring the exact same posture this
suite's `AC-QPB-104` wizard-step-sequencing placeholder (`test_symbol_styling.py`) already
established for a structurally identical situation. A documented, `manual`-marked, skipped
placeholder is added instead —
`test_wizard_exposes_a_working_select_qgis_install_location_control` — covering only the
UI-reachability half; the underlying verification logic the control would call is fully covered by
real, automated tests (see table below).

## Design choices this round made, and why

- **`check_runtime`'s existing signature is extended additively (`manual_path` parameter, new
  `qgis_prefix_path` return key), rather than inventing a brand-new, differently-named harness
  function.** `check_runtime` is already the established entry point wrapping FR-QPB-008/
  FR-QPB-009 (function 1 of `HARNESS_CONTRACT.md`); extending it in place — mirroring this file's
  own precedent for `match_ktsn`'s purely additive `direct_scientific_name` return-key addition
  (Decision Log D-60/D-64) — avoids proliferating a second, overlapping runtime-detection surface.
  See `HARNESS_CONTRACT.md`'s own extension section for the exact contract.
- **`force_missing`'s existing meaning is preserved exactly for every existing caller
  (`manual_path` omitted); its meaning is only extended for the new case where `manual_path` is
  also supplied.** This is a deliberate, minimal, backward-compatible refinement — the pre-existing
  `test_missing_runtime_produces_a_clear_actionable_error_not_a_crash` test is confirmed to keep
  passing unmodified under this extension (it never passes `manual_path`).
- **The "valid manual path succeeds" case is tested against this machine's own real, already
  auto-detected QGIS installation path (via the new `qgis_prefix_path` return key), not a
  fabricated fake install directory.** This harness has no way to construct a working fake QGIS
  installation without a real one — mirroring the exact same constraint that already makes
  `test_detected_qgis_344_lts_passes_verification_without_pip_installed_pyqgis` `qgis`-marked
  rather than unconditionally runnable. `force_missing=True` is layered on top so that
  `available: True` can only be explained by `manual_path` genuinely having been consulted and
  verified — not by automatic detection quietly still working despite the flag.
- **No new numbered acceptance-criterion ID is introduced.** Section 18.5 of the approved
  specification has no dedicated `AC-###` for FR-QPB-008's manual-override clause specifically
  (only `AC-QPB-029`, which covers FR-QPB-009's missing-runtime error-message requirement). Per
  this round's own task framing and this project's clean-room rules (`test-designer` must not
  invent specification content), the new tests below are traced directly to `FR-QPB-008`/
  `FR-QPB-009` rather than to a fabricated new AC ID. Assigning one, if desired, is a `spec-writer`
  decision, not made here.

## Traceability table

| FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| FR-QPB-008 (automatic-detection-first half) | Automatic detection is attempted before any manual override is relevant | `test_runtime_detection.py::test_missing_runtime_produces_a_clear_actionable_error_not_a_crash` (AC-QPB-029), `test_runtime_detection.py::test_detected_qgis_344_lts_passes_verification_without_pip_installed_pyqgis` (AC-QPB-053) | auto (**pre-existing, confirmed, not new**) |
| FR-QPB-008 (manual-override precedence) | A supplied manual path must not override an automatic detection that has already succeeded | `test_qgis_manual_path_override.py::test_automatic_detection_takes_precedence_over_an_ignored_manual_path_when_it_already_succeeds` | auto (`qgis`-marked; skipped when no real QGIS is detected on the machine running the suite) |
| FR-QPB-008 (manual-override return-shape contract) | `check_runtime()` always reports a `qgis_prefix_path` key, needed to discover a known-good manual-override target | `test_qgis_manual_path_override.py::test_check_runtime_return_dict_includes_a_qgis_prefix_path_key` | auto |
| FR-QPB-008 (manual-override input handling) | An empty-string manual path is treated identically to no override at all | `test_qgis_manual_path_override.py::test_manual_path_override_is_ignored_when_blank` | auto |
| FR-QPB-008 / FR-QPB-009 (manual-override negative case: invalid directory) | A manual path pointing at a real but non-QGIS directory is rejected with a clear, non-technical, distinct-from-generic failure message, never a crash | `test_qgis_manual_path_override.py::test_manual_path_override_is_rejected_cleanly_when_it_points_at_a_non_qgis_directory` | auto |
| FR-QPB-008 / FR-QPB-009 (manual-override negative case: nonexistent path) | A manual path that does not exist on disk at all is rejected cleanly, never a crash | `test_qgis_manual_path_override.py::test_manual_path_override_is_rejected_cleanly_when_the_path_does_not_exist_at_all` | auto |
| FR-QPB-008 (manual-override positive case) | A manual path pointing at a genuinely valid, already-verified QGIS installation actually changes the detection outcome to available | `test_qgis_manual_path_override.py::test_manual_path_override_succeeds_against_a_genuinely_valid_qgis_installation` | auto (`qgis`-marked; skipped when no real, bridge-verified QGIS install with a reported `qgis_prefix_path` exists on the machine running the suite) |
| FR-QPB-008 (wizard UI reachability) | A real, clickable "select QGIS install location" control is reachable from the missing-runtime error state and actually invokes the manual-override logic | `test_qgis_manual_path_override.py::test_wizard_exposes_a_working_select_qgis_install_location_control` | **manual** (documented, skipped — see the "genuinely out of this harness's reach" note above) |

## Ambiguities / gaps found (routing recommendation, not silently resolved)

None found in FR-QPB-008/FR-QPB-009's own text — both are clear and sufficient as written, per the
orchestrator's own framing of this task, confirmed by this round's own review. Two secondary
observations, reported rather than silently resolved:

1. **No numbered `AC-###` exists for FR-QPB-008's manual-override clause specifically** (see
   "Design choices" above) — the new tests trace directly to the FR text itself, matching this
   round's own task framing. If the stakeholder wants a dedicated `AC-QPB-###` recorded in Section
   18.5 for this (mirroring how nearly every other functional requirement in this specification
   has at least one numbered acceptance criterion), that is a `spec-writer` housekeeping item, not
   a defect in the tests added here.
2. **The exact contract for how a UI would collect `manual_path` (a folder picker vs. a raw text
   field vs. something else) is left unspecified**, matching FR-QPB-008's own text, which does not
   mandate a specific input mechanism — only that manual selection be possible. The `manual`-marked
   placeholder test's own suggested QA steps mention a "folder/file picker dialog" as the most
   natural implementation, but this is a suggestion for the eventual `implementer`, not an
   additional requirement asserted by any test here.
