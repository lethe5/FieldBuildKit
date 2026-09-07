"""Unit tests for qfield_builder.ui.app's first-launch encrypted-storage password setup prompt
(NFR-QPB-073/AC-QPB-092, Decision Log D-53).

`qfield_builder.ui.app.main()` itself blocks on a real Qt event loop (`QApplication.exec()`), so
it is not directly unit-testable; the actual prompt-or-not decision this covers is factored out
into the standalone, directly-testable `maybe_prompt_for_first_launch_password()` function, which
`main()` calls before ever constructing/showing the wizard. These tests rely on
`tests/unit/conftest.py`'s autouse `_isolate_credential_store` fixture for a fresh, isolated
app-data directory per test.
"""
from __future__ import annotations

from qfield_builder import credential_store
from qfield_builder.ui import app as app_module


def test_prompts_when_no_password_has_ever_been_established():
    """AC-QPB-092: given the application is launched with no encrypted-storage password yet
    established, the first-launch setup prompt is shown before the main window would appear."""
    prompt_calls = []

    def _fake_setup_prompt():
        prompt_calls.append(True)
        return "a-real-password"

    app_module.maybe_prompt_for_first_launch_password(setup_prompt_fn=_fake_setup_prompt)

    assert prompt_calls == [True]
    assert credential_store.is_password_established()


def test_declining_the_prompt_establishes_no_password_and_leaves_remember_unavailable():
    """AC-QPB-092 decline path: no password is established, and (per
    `ConnectivityBasemapPage`/`IdentificationTogglePage`'s own `is_password_established()` check)
    "Remember this key" stays unavailable/disabled for that session."""
    app_module.maybe_prompt_for_first_launch_password(setup_prompt_fn=lambda: None)

    assert not credential_store.is_password_established()


def test_the_prompt_is_shown_again_at_the_next_launch_after_a_decline():
    """AC-QPB-092: "the same prompt is shown again at the next launch" -- modelled here as a
    second call to this function within the same process, since declining never persists
    anything that would make `is_password_established()` return True."""
    app_module.maybe_prompt_for_first_launch_password(setup_prompt_fn=lambda: None)
    assert not credential_store.is_password_established()

    second_call_prompts = []

    def _fake_setup_prompt():
        second_call_prompts.append(True)
        return None

    app_module.maybe_prompt_for_first_launch_password(setup_prompt_fn=_fake_setup_prompt)

    assert second_call_prompts == [True]


def test_does_not_prompt_at_all_once_a_password_is_already_established():
    """Never a general access-gate shown on every launch -- once established (this launch or a
    previous one), subsequent launches must not show the setup prompt again."""
    credential_store.establish_password("already-set-up-password")  # noqa: S106
    credential_store.lock_session()  # A later launch would not start out "unlocked" either.

    prompt_calls = []

    def _fake_setup_prompt():
        prompt_calls.append(True)
        return "irrelevant"

    app_module.maybe_prompt_for_first_launch_password(setup_prompt_fn=_fake_setup_prompt)

    assert prompt_calls == []


def test_falls_back_to_the_real_password_setup_dialog_function_when_no_seam_is_supplied(
    monkeypatch,
):
    """Confirms `main()`'s real (non-test) call site actually wires up the production dialog
    function when no injectable test seam is supplied, not merely that the seam works when a
    fake is passed explicitly."""
    calls = []
    monkeypatch.setattr(
        app_module, "prompt_for_setup_password", lambda: calls.append(True) or "a-password"
    )

    app_module.maybe_prompt_for_first_launch_password()

    assert calls == [True]
    assert credential_store.is_password_established()
