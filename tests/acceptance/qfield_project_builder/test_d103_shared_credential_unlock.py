"""APPROVED acceptance tests for D-103 / clarified NFR-QPB-073 and AC-QPB-097.

These tests exercise the real encrypted store and the three real wizard-page consumers against
one disposable ``credentials.enc``.  They never access user app data or reveal a real key.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from qfield_builder import credential_store
from qfield_builder.ui.wizard import (
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    ReviewAndBuildPage,
)


PASSWORD = "acceptance-only-d103-password"
VWORLD = "SYNTHETIC-D103-VWORLD"
PLANTNET = "SYNTHETIC-D103-PLANTNET"
ROUTE = "SYNTHETIC-D103-ORS"


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    app_data = tmp_path / "app-data"
    legacy_data = tmp_path / "legacy-app-data"
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: app_data)
    monkeypatch.setattr(credential_store, "legacy_app_data_dir", lambda: legacy_data)
    credential_store.lock_session()
    credential_store.set_session_key(None)
    credential_store.set_session_plantnet_key(None)
    credential_store.set_session_route_key(None)
    yield
    credential_store.lock_session()
    credential_store.set_session_key(None)
    credential_store.set_session_plantnet_key(None)
    credential_store.set_session_route_key(None)


def _seed_three_remembered_keys() -> None:
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(VWORLD)
    credential_store.remember_plantnet_key(PLANTNET)
    credential_store.remember_route_key(ROUTE)
    credential_store.lock_session()


def test_ac_qpb097_one_successful_unlock_is_shared_across_pages_revisits_and_review_persistence():
    _seed_three_remembered_keys()
    prompts = []

    def prompt(_parent=None):
        prompts.append("accepted")
        return PASSWORD

    basemap = ConnectivityBasemapPage(password_prompt_fn=prompt)
    plantnet = IdentificationTogglePage(password_prompt_fn=prompt)
    review = ReviewAndBuildPage(password_prompt_fn=prompt)

    # First point of use unlocks the one canonical store. Every later key-type/page read reuses it.
    basemap._load_remembered_key()
    plantnet._load_remembered_plantnet_key()
    review._load_remembered_route_key()
    plantnet._load_remembered_plantnet_key()
    basemap._load_remembered_key()
    review._load_remembered_route_key()

    assert prompts == ["accepted"]
    assert basemap.api_key_edit.text() == VWORLD
    assert plantnet.plantnet_api_key_edit.text() == PLANTNET
    assert review.route_api_key_edit.text() == ROUTE
    assert all((basemap.remember_checkbox.isChecked(),
                plantnet.plantnet_remember_checkbox.isChecked(),
                review.route_key_remember_checkbox.isChecked()))

    # The production review/build persistence boundary must reuse the same unlocked session.
    updated = {
        "basemap": {"vworld_api_key": VWORLD + "-UPDATED", "remember_key": True},
        "plantnet": {"api_key": PLANTNET + "-UPDATED", "remember_key": True},
        "survey_route": {"api_key": ROUTE + "-UPDATED", "remember_key": True},
    }
    review._maybe_unlock_for_remembering(updated)

    assert prompts == ["accepted"]
    assert credential_store.get_remembered_key() == VWORLD + "-UPDATED"
    assert credential_store.get_remembered_plantnet_key() == PLANTNET + "-UPDATED"
    assert credential_store.get_remembered_route_key() == ROUTE + "-UPDATED"
    assert credential_store.credentials_file_path().is_file()
    assert list(credential_store.credentials_file_path().parent.glob("credentials.enc")) == [
        credential_store.credentials_file_path()
    ]


@pytest.mark.parametrize("outcome", ["cancel", "wrong-password"])
def test_ac_qpb097_cancel_and_wrong_password_do_not_unlock_or_auto_retry(outcome):
    _seed_three_remembered_keys()
    prompts = []

    def prompt(_parent=None):
        prompts.append(outcome)
        return None if outcome == "cancel" else "synthetic-wrong-password"

    page = IdentificationTogglePage(password_prompt_fn=prompt)
    page._load_remembered_plantnet_key()

    assert prompts == [outcome]
    assert credential_store.is_unlocked() is False
    assert page.plantnet_api_key_edit.text() == ""
    if outcome == "wrong-password":
        assert "직접 입력" in page.plantnet_credential_status_label.text()
