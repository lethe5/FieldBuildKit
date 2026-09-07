"""FR-QPB-008 (Section 5.2, Decision Log D-10): manual QGIS-install-path override, reachable
when automatic detection fails.

**Conformance-gap round.** This is new coverage for an already-approved requirement, added by a
later `test-designer` round after confirming a real, zero-coverage gap: FR-QPB-008 reads "The
application must attempt automatic detection of a supported QGIS installation, and must allow
the user to select the QGIS installation path manually when automatic detection fails." No prior
round ever implemented or tested the manual-override half of this requirement.
`qfield_builder/runtime.py`'s own `_NON_TECHNICAL_MISSING_MESSAGE` already tells the user, by
name, to use a "QGIS 설치 위치 선택..." ("Select QGIS install location...") option, but as of
this round no such option exists anywhere in the codebase: no UI control, and no underlying
function (`detect_qgis_installation()`/`check_runtime()`) that accepts a manually supplied path
at all. See `../qfield_project_builder_qgis_manual_path_override.traceability.md` for the full
report.

Automatic detection being *attempted first* -- the other half of FR-QPB-008 -- already has
existing coverage in `test_runtime_detection.py` (AC-QPB-029: automatic detection forced to fail
-> clear error; AC-QPB-053: automatic detection succeeding on a real QGIS install) and is not
retested here, except for one new test below confirming that a *supplied* manual_path does not
wrongly override an automatic detection that has already succeeded -- an interaction that could
not previously exist or be tested, since manual_path itself is new in this round.

See HARNESS_CONTRACT.md's "New (test-designer conformance-gap round, 2026-08-27)" section for the
exact `check_runtime(force_missing: bool = False, manual_path: str | None = None) -> dict`
contract these tests hold the implementation to, including the new `qgis_prefix_path` return key
and the `force_missing`+`manual_path` interaction this round's tests rely on for determinism.
"""
from __future__ import annotations

import pytest

_TECHNICAL_JARGON = ["traceback", "exception", "stack trace", "nonetype", "errno"]


def _assert_non_technical(message: str) -> None:
    assert isinstance(message, str) and message.strip(), "must include a human-readable message"
    lowered = message.lower()
    assert not any(term in lowered for term in _TECHNICAL_JARGON), (
        f"error message must be non-technical, got: {message!r}"
    )


def test_check_runtime_return_dict_includes_a_qgis_prefix_path_key(check_runtime_with_manual_path):
    """Documents this round's additive return-shape extension: `check_runtime()` must always
    include a `qgis_prefix_path` key (`str | None`), not merely when a caller happens to look for
    it -- needed so a caller (and this file's own later tests) can discover an already-verified
    install path to use as a manual-override target, since this harness has no way to fabricate a
    working fake QGIS installation directory."""
    result = check_runtime_with_manual_path(force_missing=True)
    assert "qgis_prefix_path" in result
    assert result["qgis_prefix_path"] is None, (
        "force_missing=True with no manual_path must report no install path, mirroring "
        f"'available': False -- got {result}"
    )


def test_manual_path_override_is_ignored_when_blank(check_runtime_with_manual_path):
    """An empty-string manual_path must behave identically to omitting it entirely -- FR-QPB-008
    describes a real, user-supplied path, not an empty/cancelled-picker placeholder standing in
    for one."""
    omitted = check_runtime_with_manual_path(force_missing=True)
    blank = check_runtime_with_manual_path(force_missing=True, manual_path="")
    assert blank == omitted, (
        f"an empty-string manual_path must be treated the same as no manual path at all -- got "
        f"omitted={omitted!r}, blank={blank!r}"
    )


def test_manual_path_override_is_rejected_cleanly_when_it_points_at_a_non_qgis_directory(
    check_runtime_with_manual_path, tmp_path
):
    """FR-QPB-008/FR-QPB-009: a manually supplied path that is not a usable QGIS installation must
    fail cleanly, with a clear, non-technical, actionable message distinct from the generic
    "no installation found anywhere, try the manual option" message shown *before* the user had
    tried the manual option -- never a crash, and never silently reported as available.

    `force_missing=True` deterministically simulates "automatic detection found nothing usable"
    (the pre-existing, documented test seam -- see HARNESS_CONTRACT.md function 1 and this round's
    extension note), isolating the manual-path-specific outcome from whatever real QGIS
    installation state the machine actually running this suite happens to have.
    """
    bogus_path = tmp_path / "not_a_qgis_install"
    bogus_path.mkdir()
    (bogus_path / "readme.txt").write_text("definitely not a QGIS installation", encoding="utf-8")

    baseline = check_runtime_with_manual_path(force_missing=True)
    overridden = check_runtime_with_manual_path(force_missing=True, manual_path=str(bogus_path))

    assert overridden["available"] is False, (
        "a manual path that is not a genuinely usable QGIS installation must never be reported "
        f"as available -- got {overridden}"
    )
    assert overridden["qgis_prefix_path"] is None
    _assert_non_technical(overridden["message"])
    assert overridden["message"] != baseline["message"], (
        "the failure message for a rejected manual path must be specific to that outcome, not "
        "byte-for-byte the same generic 'no installation found anywhere, try the manual option' "
        "message already shown before the user ever supplied one -- repeating that identical "
        "generic text after a manual path has actually been tried and failed would be confusing "
        f"and non-actionable. Got the identical message both times: {overridden['message']!r}"
    )


def test_manual_path_override_is_rejected_cleanly_when_the_path_does_not_exist_at_all(
    check_runtime_with_manual_path, tmp_path
):
    """A manual path that does not even exist on disk must produce the same clean, non-crashing
    failure behavior as an existing-but-wrong directory -- FR-QPB-009's "never a crash, never
    silent failure" guarantee applies here too, not only to the no-path-supplied case
    AC-QPB-029 already covers."""
    missing_path = tmp_path / "does_not_exist_at_all"
    assert not missing_path.exists()

    try:
        result = check_runtime_with_manual_path(force_missing=True, manual_path=str(missing_path))
    except Exception as exc:  # noqa: BLE001 - this is exactly the failure mode under test
        pytest.fail(
            "check_runtime(manual_path=...) must return a structured failure result for a "
            f"nonexistent manual path, not raise an exception: {exc!r}"
        )
    assert result["available"] is False
    assert result["qgis_prefix_path"] is None
    _assert_non_technical(result["message"])


@pytest.mark.qgis
def test_manual_path_override_succeeds_against_a_genuinely_valid_qgis_installation(
    check_runtime_with_manual_path,
):
    """FR-QPB-008's core positive case: supplying a real, valid QGIS installation path via manual
    override must actually change the detection outcome from unavailable to available -- not
    merely report available because automatic detection happened to succeed on its own (which is
    already covered by AC-QPB-053 and does not by itself prove the override mechanism exists or
    works).

    Uses this machine's own, really-detected QGIS installation path (reported via
    `check_runtime()`'s own `qgis_prefix_path` -- this round's other new contract addition) as a
    stand-in for "a real QGIS install a user might manually point at" -- this harness has no way
    to fabricate a working fake QGIS installation directory. `force_missing=True` forces automatic
    detection to be treated as having failed, so the only way this test can observe
    `available: True` is if `manual_path` was genuinely consulted and independently
    verified -- proving the override mechanism itself works.
    """
    detected = check_runtime_with_manual_path()
    if not detected.get("available") or not detected.get("qgis_prefix_path"):
        pytest.skip(
            "no working QGIS bridge with a reported qgis_prefix_path was detected on this "
            f"machine (real automatic detection returned {detected!r}); this test needs a real, "
            "already-verified install path to use as a manual-override target"
        )

    overridden = check_runtime_with_manual_path(
        force_missing=True, manual_path=detected["qgis_prefix_path"]
    )
    assert overridden["available"] is True, (
        "a manual_path pointing at a genuinely valid, already-verified QGIS installation must be "
        f"honored even when automatic detection is simulated as having failed -- got {overridden}"
    )


@pytest.mark.qgis
def test_automatic_detection_takes_precedence_over_an_ignored_manual_path_when_it_already_succeeds(
    check_runtime_with_manual_path, tmp_path
):
    """FR-QPB-008 frames manual selection as available "when automatic detection fails" -- a
    fallback, not a first-class override that can occur even while automatic detection is already
    working. Supplying a bogus manual_path must not break an already-successful automatic
    detection."""
    bogus_path = tmp_path / "not_a_qgis_install"
    bogus_path.mkdir()

    result = check_runtime_with_manual_path(manual_path=str(bogus_path))
    assert result["available"] is True, (
        "when automatic detection already succeeds on its own (force_missing not set), a "
        f"caller-supplied manual_path -- even an invalid one -- must not override that success "
        f"-- got {result}"
    )


# --- FR-QPB-008, wizard-reachability half (manual/GUI-dependent; not automatable here) ----------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "FR-QPB-008 requires that the user be able to 'select the QGIS installation path "
        "manually when automatic detection fails' -- a literal, on-screen PySide6 wizard/"
        "error-dialog UI control (a button, menu action, or dialog offering a folder/file picker) "
        "reachable from the missing-runtime error state, that actually calls the manual-override "
        "verification logic exercised headlessly above. This is a UI-content/reachability fact, "
        "not a generated-project artifact or a pure, GUI-independent logic function -- mirroring "
        "this suite's own established convention for exactly this category of criterion (e.g. "
        "AC-QPB-104's wizard-step-sequencing placeholder in test_symbol_styling.py). This "
        "project's hard QGIS-isolation rule is unrelated to this specific gap (it concerns "
        "QGIS/QApplication construction, not the PySide6 wizard), but no automated GUI-driving "
        "mechanism exists in this harness either way."
        "\n\nManual QA steps: (1) On a machine with no compatible QGIS installation detectable "
        "(or with a real QGIS install temporarily renamed/moved so automatic detection fails), "
        "launch the desktop application and reach the point where the missing-runtime error "
        "message is shown (e.g. attempting Step 7's 'Build'). (2) Confirm the error state offers "
        "a concrete, clickable 'QGIS 설치 위치 선택...' ('Select QGIS install location...') "
        "control -- not merely text mentioning the option by name, as it does today (see "
        "qfield_builder/runtime.py's _NON_TECHNICAL_MISSING_MESSAGE). (3) Use it to pick a real, "
        "valid QGIS installation's folder via a native file/folder picker dialog. (4) Confirm the "
        "application re-attempts runtime verification against that path and, on success, "
        "proceeds normally (the build becomes available). (5) Repeat, picking an invalid folder "
        "instead, and confirm a clear, non-technical, actionable failure message is shown, "
        "matching the headlessly-verified check_runtime(manual_path=...) contract tested above."
    )
)
def test_wizard_exposes_a_working_select_qgis_install_location_control():
    raise AssertionError("should never run while skipped — see skip reason")
