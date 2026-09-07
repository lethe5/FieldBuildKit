"""Orchestrator-controlled macOS smoke test: the real GUI, end to end.

This test does *not* call `qfield_builder.build.build_project()` directly, and does not stub or
monkeypatch `qfield_builder.qgis_worker.build_qgis_project` (contrast with
`tests/unit/test_wizard.py`'s `_stub_qgis_for_build` fixture). Instead it:

1. Constructs the real, production `qfield_builder.ui.wizard.ProjectBuilderWizard` -- the exact
   class `qfield_builder.ui.app.main()` instantiates -- under `QT_QPA_PLATFORM=offscreen`.
2. Walks through all seven wizard pages exactly as a user would: setting the minimum viable input
   for a Type-1 (`simple_inventory`), no-basemap build on `ProjectBasicsPage`, leaving every other
   page's own defaults untouched (`SurveyTypePage` already defaults its first radio button to
   `simple_inventory`; `SiteInputPage` is left empty -- Type 1 has no site layer to seed;
   `ConnectivityBasemapPage` already defaults to "No basemap"; `IdentificationTogglePage`'s
   checkbox is enabled but left at its own unchecked default), and calling `QWizard.next()` between
   each page (which
   itself calls each page's real `validatePage()`/`isComplete()`/`initializePage()`).
3. Clicks the real `ReviewAndBuildPage.build_button` (`QPushButton.click()`), which is wired to
   `ReviewAndBuildPage._start_build()` -- the exact same slot a real user's mouse click invokes --
   which itself constructs a real `qfield_builder.ui.build_worker.BuildWorkerThread`, which itself
   calls the real `qfield_builder.worker_process.run_job_in_subprocess("build_project", ...)`,
   which spawns a genuinely separate OS process that (via `qfield_builder.runtime`/
   `qfield_builder.qgis_bridge`) dispatches into a real, locally installed QGIS 3.44 installation's
   own PyQGIS environment. Nothing in this test's own call stack calls
   `qfield_builder.build.build_project` or `qfield_builder.qgis_worker.build_qgis_project` itself.
4. Waits for that background `QThread` to finish via a real Qt event loop
   (`QEventLoop.exec()`) that is only ever exited by the worker's own `finished_with_result`
   `Signal` (a queued cross-thread connection back to the main/GUI thread) or by a generous safety
   timeout -- never a blind `time.sleep()` poll.
5. Asserts genuine success: the wizard's own `ReviewAndBuildPage._build_succeeded` flag is `True`,
   the resulting project directory exists on disk with a real `.qgs` file and a real `.gpkg` file,
   and the GeoPackage's actual on-disk schema (tables/columns, queried directly via `sqlite3`,
   independent of anything `qfield_builder.gpkg`/`qfield_builder.schemas` themselves assert in
   their own unit tests) matches what `simple_inventory` (Section 8.1's Type 1) is specified to
   produce, per `qfield_builder.schemas.get_schema("simple_inventory")` -- the same single source
   of truth `qfield_builder.gpkg`/`qfield_builder.qgis_worker` themselves consume.

Requires a real, locally installed, bridgeable QGIS 3.44 installation (see
`qfield_builder.qgis_bridge`) -- skipped otherwise, matching the pattern already established by
`tests/unit/test_worker_process.py`.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from qfield_builder import credential_store, reference_bundle, schemas
from qfield_builder.runtime import check_runtime
from qfield_builder.ui.wizard import (
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    ProjectBasicsPage,
    ProjectBuilderWizard,
    ReviewAndBuildPage,
    SiteInputPage,
    SurveyTypePage,
    SymbolStylingPage,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_REFERENCE_WORKBOOK = (
    _REPO_ROOT / "packaging" / "reference_source" / "tables" / "Rpt_2026-08-29_List.xlsx"
)
_REAL_PROBABILITY_RASTER_DIR = (
    _REPO_ROOT
    / "storage"
    / "reference"
    / "rasters"
    / "bce_inverse_corrected_probability_maps"
)


def _prepare_canonical_reference_root(tmp_path: Path) -> Path:
    """Create a test-owned canonical root with the real raster boundary, never placeholders."""
    if not _CANONICAL_REFERENCE_WORKBOOK.is_file():
        pytest.skip(f"D-95 canonical workbook is not present: {_CANONICAL_REFERENCE_WORKBOOK}")
    if not _REAL_PROBABILITY_RASTER_DIR.is_dir():
        pytest.skip(f"real probability rasters are not present: {_REAL_PROBABILITY_RASTER_DIR}")

    root = tmp_path / "canonical-reference"
    tables = root / "tables"
    tables.mkdir(parents=True)
    shutil.copy2(_CANONICAL_REFERENCE_WORKBOOK, tables / _CANONICAL_REFERENCE_WORKBOOK.name)
    raster_destination = root / "rasters" / "bce_inverse_corrected_probability_maps"
    raster_destination.parent.mkdir(parents=True)
    raster_destination.symlink_to(_REAL_PROBABILITY_RASTER_DIR, target_is_directory=True)
    return root

_QGIS_AVAILABLE = check_runtime()["available"]

# Generous but bounded: this is a real end-to-end build through a real, separately spawned OS
# process (multiprocessing `spawn` worker) that itself launches a *second* real OS process
# (the QGIS-bridge subprocess) -- slower than any purely in-process unit test, but must still
# never hang the test suite indefinitely if something regresses.
_BUILD_WAIT_TIMEOUT_MS = 300_000


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _advance_wizard(wizard: ProjectBuilderWizard, transition_description: str) -> None:
    """Advances `wizard` to its next page, the same way clicking its real "Next" button would
    (`QWizard.next()` itself calls the current page's real `validatePage()`/`isComplete()`, then
    the next page's real `initializePage()`) -- and fails loudly if the transition was blocked.

    `QWizard.next()` is a void Qt slot (it has no useful return value in PySide6), so blocking is
    detected by comparing `currentId()` before and after, exactly as a real user would observe
    "the wizard didn't move to the next page" rather than by any return value.
    """
    id_before = wizard.currentId()
    wizard.next()
    assert wizard.currentId() != id_before, transition_description


def _wait_for_build_worker_thread(worker_thread) -> dict | None:
    """Blocks the calling (main/GUI) thread via a real Qt event loop until `worker_thread`'s
    `finished_with_result` signal fires, or a safety timeout elapses -- never a blind sleep.

    Returns the emitted result dict, or `None` if the safety timeout fired first.
    """
    loop = QEventLoop()
    captured: dict = {}

    def _on_finished(result: dict) -> None:
        captured["result"] = result
        loop.quit()

    worker_thread.finished_with_result.connect(_on_finished)

    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(loop.quit)
    timeout_timer.start(_BUILD_WAIT_TIMEOUT_MS)

    loop.exec()
    timeout_timer.stop()
    return captured.get("result")


@pytest.mark.skipif(not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation")
def test_real_gui_end_to_end_build_produces_a_working_simple_inventory_project(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("REFERENCE_DATA_DIR", str(_prepare_canonical_reference_root(tmp_path)))
    project_display_name = "Smoke Test Project"
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()

    wizard = ProjectBuilderWizard()
    wizard.show()

    # --- Step 1: Project basics (FR-QPB-020-022a) -----------------------------------------
    basics_page = wizard.currentPage()
    assert isinstance(basics_page, ProjectBasicsPage)
    basics_page.display_name_edit.setText(project_display_name)
    basics_page.output_dir_edit.setText(str(parent_dir))
    _advance_wizard(wizard, "Step 1 -> Step 2 transition was blocked")

    # --- Step 2: Survey type (FR-QPB-023/024) ----------------------------------------------
    survey_page = wizard.currentPage()
    assert isinstance(survey_page, SurveyTypePage)
    # Left at its own default: the first radio button ("simple_inventory") is pre-checked.
    assert wizard.field("survey_type") == "simple_inventory"
    _advance_wizard(wizard, "Step 2 -> Step 3 transition was blocked")

    # --- Step 3: Site/plot input (FR-QPB-025-033) ------------------------------------------
    site_page = wizard.currentPage()
    assert isinstance(site_page, SiteInputPage)
    # Type 1 (simple_inventory) has no site layer to seed -- left completely empty, as a real
    # user filling out this minimal Type-1 build would leave it.
    _advance_wizard(wizard, "Step 3 -> Step 4 transition was blocked")

    # --- Step 4: Connectivity/basemap (FR-QPB-034-036) -------------------------------------
    basemap_page = wizard.currentPage()
    assert isinstance(basemap_page, ConnectivityBasemapPage)
    # Left at its own default: "No basemap" is pre-checked.
    assert wizard.field("basemap_mode") == "none"
    _advance_wizard(wizard, "Step 4 -> Step 5 transition was blocked")

    # --- Step 5: Identification toggle (FR-QPB-037-039/E-QPB-001) --------------------------
    # The guaranteed-manual identification baseline (Section 13) is now real, implemented,
    # reviewer-PASSed code (qml_plugin.py/reference_bundle.py/ktsn_match.py), so the checkbox is
    # enabled -- but left unchecked here, matching a real user leaving this optional step at its
    # default for this minimal Type-1 build.
    identification_page = wizard.currentPage()
    assert isinstance(identification_page, IdentificationTogglePage)
    assert not identification_page.enable_checkbox.isChecked()
    assert identification_page.enable_checkbox.isEnabled()
    _advance_wizard(wizard, "Step 5 -> Step 6 transition was blocked")

    # --- Step 6: Symbol styling configuration (FR-QPB-120/121/123) -------------------------
    # Left at its own minimalist default -- matching a real user who takes no further action.
    symbol_styling_page = wizard.currentPage()
    assert isinstance(symbol_styling_page, SymbolStylingPage)
    assert symbol_styling_page.field("symbol_styling_mode") == "minimalist"
    _advance_wizard(wizard, "Step 6 -> Step 7 transition was blocked")

    # --- Step 7: Review and build (FR-QPB-040/041) -----------------------------------------
    review_page = wizard.currentPage()
    assert isinstance(review_page, ReviewAndBuildPage)

    # The real click-triggered path: QPushButton.click() -> ReviewAndBuildPage._start_build()
    # -> a real BuildWorkerThread -> a real worker_process.run_job_in_subprocess("build_project").
    review_page.build_button.click()
    assert review_page._worker_thread is not None, (
        "Clicking Build did not construct a real BuildWorkerThread -- the GUI's own "
        "build-triggering mechanism did not run."
    )

    result = _wait_for_build_worker_thread(review_page._worker_thread)
    assert result is not None, (
        f"The real background build did not complete within {_BUILD_WAIT_TIMEOUT_MS / 1000:.0f}s."
    )

    # The wizard's own state (updated exclusively by the real `_on_build_finished` slot, itself
    # only ever invoked by the real worker thread's own signal) must agree.
    assert review_page._build_succeeded is True, result
    assert review_page.isComplete() is True

    assert result.get("success") is True, result
    project_dir = result["project_dir"]
    qgs_path = result["qgs_path"]
    gpkg_path = result["gpkg_path"]

    from pathlib import Path

    assert Path(project_dir).is_dir()
    assert Path(qgs_path).is_file()
    assert Path(gpkg_path).is_file()
    assert Path(project_dir) == parent_dir / "smoke-test-project"

    # --- GeoPackage schema genuinely matches simple_inventory (Section 8.1, Type 1) -------
    expected_schema = schemas.get_schema("simple_inventory")
    assert set(expected_schema.keys()) == {"inventory_observation"}
    expected_table = expected_schema["inventory_observation"]
    expected_columns = {col.name for col in expected_table.columns} | {
        expected_table.geometry.column
    }

    conn = sqlite3.connect(gpkg_path)
    try:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'gpkg_%' AND name NOT LIKE 'rtree_%' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'qpb_%';"
            ).fetchall()
        }
        # DR-QPB-072/FR-QPB-127 (Decision Log D-66/D-68): every Types 1-3 build now also bundles
        # the accepted-name lookup table unconditionally, alongside the domain survey table.
        assert table_names == {
            "inventory_observation",
            reference_bundle.KTSN_LOOKUP_TABLE_NAME,
        }, table_names

        actual_columns = {
            row[1] for row in conn.execute("PRAGMA table_info('inventory_observation');")
        }
        assert expected_columns <= actual_columns, (expected_columns, actual_columns)

        # `gpkg_contents`/`gpkg_geometry_columns` bookkeeping (real GeoPackage core spec tables)
        # must also genuinely describe this table as a POINT feature layer.
        contents_row = conn.execute(
            "SELECT data_type FROM gpkg_contents WHERE table_name = 'inventory_observation';"
        ).fetchone()
        assert contents_row == ("features",)

        geom_row = conn.execute(
            "SELECT column_name, geometry_type_name FROM gpkg_geometry_columns "
            "WHERE table_name = 'inventory_observation';"
        ).fetchone()
        assert geom_row == (expected_table.geometry.column, expected_table.geometry.geom_type)
    finally:
        conn.close()

    # The result label a real user sees must be the success message, not a failure message.
    assert "프로젝트가 생성되었습니다:" in review_page.result_label.text()
    assert review_page.build_button.isEnabled()
    assert not review_page.progress_bar.isVisible()


@pytest.mark.skipif(not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation")
def test_real_gui_end_to_end_build_with_remember_this_key_persists_to_credentials_enc(
    tmp_path, monkeypatch
):
    """Reviewer round (Decision Log D-53/D-55), Finding 1 regression test.

    Proves "Remember this key" actually persists to the encrypted `credentials.enc` store when
    driven through the *real* subprocess boundary -- `ReviewAndBuildPage.build_button.click()` ->
    the real `BuildWorkerThread` -> the real `worker_process.run_job_in_subprocess("build_project"
    )`, which spawns a genuinely separate `multiprocessing`-`spawn` OS process, exactly like
    `test_real_gui_end_to_end_build_produces_a_working_simple_inventory_project` above -- not
    merely `qfield_builder.build.build_project()` called in-process, which is all
    AC-QPB-058/AC-QPB-082 (`tests/acceptance/`) ever exercise for this area.

    Before this fix, `build_project()`'s own `apply_plantnet_retention_policy` call could never
    succeed in that freshly spawned child process (its own `credential_store` copy was never
    unlocked there), so `credentials.enc` was silently never written despite the checkbox
    appearing to work; this test fails against that prior behavior and passes against the fix
    (persistence now happens directly in the UI process, before the subprocess is even spawned).

    Uses the identification/Pl@ntNet "Remember this key" path (rather than the VWorld online-
    basemap path) so this test needs no live network access at build time: the VWorld online-
    basemap path would additionally exercise a best-effort, network-dependent live WMTS
    capabilities lookup (`vworld.resolve_wmts_layer_details`, which degrades gracefully offline
    but is unrelated to what this test regression-tests) merely to embed the key in the `.qgs`
    file -- irrelevant complexity for a test about *local* encrypted-storage persistence.
    """
    fake_plantnet_key = "FAKE-PLANTNET-KEY-FOR-REMEMBER-SUBPROCESS-TEST"  # noqa: S105 - synthetic.
    monkeypatch.setenv("REFERENCE_DATA_DIR", str(_prepare_canonical_reference_root(tmp_path)))

    # Establishes the encrypted-storage password in *this* (the UI/test) process -- via
    # `tests/unit/conftest.py`'s autouse `_isolate_credential_store` fixture, `app_data_dir()` is
    # already redirected to an isolated `tmp_path` subdirectory, so this never touches any real
    # per-user application-data directory. This also unlocks the session immediately (see
    # `establish_password`'s own docstring), matching a real user who has just set this password.
    credential_store.establish_password("a-real-test-password")  # noqa: S106

    project_display_name = "Remember Key Subprocess Test"
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()

    wizard = ProjectBuilderWizard()
    wizard.show()

    # --- Step 1: Project basics ------------------------------------------------------------
    basics_page = wizard.currentPage()
    assert isinstance(basics_page, ProjectBasicsPage)
    basics_page.display_name_edit.setText(project_display_name)
    basics_page.output_dir_edit.setText(str(parent_dir))
    _advance_wizard(wizard, "Step 1 -> Step 2 transition was blocked")

    # --- Step 2: Survey type (left at its own simple_inventory default) --------------------
    assert wizard.field("survey_type") == "simple_inventory"
    _advance_wizard(wizard, "Step 2 -> Step 3 transition was blocked")

    # --- Step 3: Site/plot input (Type 1 has no site layer to seed) ------------------------
    _advance_wizard(wizard, "Step 3 -> Step 4 transition was blocked")

    # --- Step 4: Connectivity/basemap (left at its own "No basemap" default) ---------------
    assert wizard.field("basemap_mode") == "none"
    _advance_wizard(wizard, "Step 4 -> Step 5 transition was blocked")

    # --- Step 5: Identification toggle -- enable it, enter a fake key, consent, and check
    # "Remember this key" (this is what this test is actually regression-testing) -----------
    identification_page = wizard.currentPage()
    assert isinstance(identification_page, IdentificationTogglePage)
    identification_page.enable_checkbox.setChecked(True)
    identification_page.plantnet_api_key_edit.setText(fake_plantnet_key)
    identification_page.plantnet_consent_checkbox.setChecked(True)
    assert identification_page.plantnet_remember_checkbox.isEnabled(), (
        "the checkbox should be enabled: an encrypted-storage password was already established "
        "above before this page's initializePage() ran"
    )
    identification_page.plantnet_remember_checkbox.setChecked(True)
    _advance_wizard(wizard, "Step 5 -> Step 6 transition was blocked")

    # --- Step 6: Symbol styling configuration (left at its own minimalist default) ---------
    assert isinstance(wizard.currentPage(), SymbolStylingPage)
    _advance_wizard(wizard, "Step 6 -> Step 7 transition was blocked")

    # --- Step 7: Review and build -- the real click-triggered, real-subprocess path --------
    review_page = wizard.currentPage()
    assert isinstance(review_page, ReviewAndBuildPage)

    review_page.build_button.click()
    assert review_page._worker_thread is not None, (
        "Clicking Build did not construct a real BuildWorkerThread -- the GUI's own "
        "build-triggering mechanism did not run."
    )

    result = _wait_for_build_worker_thread(review_page._worker_thread)
    assert result is not None, (
        f"The real background build did not complete within {_BUILD_WAIT_TIMEOUT_MS / 1000:.0f}s."
    )
    assert result.get("success") is True, result
    assert review_page._build_succeeded is True

    # --- The actual regression assertion (Finding 1) ---------------------------------------
    # The key must have actually landed in the encrypted store -- not merely appeared to, via a
    # checkbox that silently no-ops across the real subprocess boundary.
    assert credential_store.credentials_file_path().is_file(), (
        "credentials.enc was never written -- 'Remember this key' silently failed to persist "
        "across the real build-subprocess boundary (Finding 1)."
    )
    raw_bytes = credential_store.credentials_file_path().read_bytes()
    assert fake_plantnet_key.encode("utf-8") not in raw_bytes  # AC-QPB-090: never plaintext.
    assert credential_store.get_remembered_plantnet_key() == fake_plantnet_key

    # No silent-failure signal (Minor Finding 2) should have been raised for this successful case.
    assert review_page._remember_persist_failed is False
    assert "기억하지 못했습니다" not in review_page.result_label.text()
