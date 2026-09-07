"""Shared pytest setup for tests/unit.

Makes PySide6's ``QApplication`` reliably able to locate its own Qt platform plugins for the
offscreen GUI tests in this directory (e.g. ``test_wizard.py``), regardless of where this
repository happens to be checked out on the host machine.

Why this is needed: on at least one verified environment, Qt's own directory-enumeration
mechanism (``QDir.entryList()``, used internally by Qt's plugin factory loader to *discover*
platform plugins in a directory) reproducibly returns an empty listing for the installed
PySide6 platform-plugins directory -- even though Python's own ``os.listdir()`` on that exact
same directory, and directly ``dlopen()``-ing or ``QPluginLoader``-loading one of those exact
plugin files by its full path, both work fine. Further isolation on that environment showed the
determining factor was *which process created the directory being enumerated*: a directory
freshly created and populated by the very same Python/pytest process that then asks Qt to
enumerate it (e.g. via ``shutil.copytree``) reproducibly comes back empty to `QDir`, regardless
of which parent directory it lives under (this was tested and ruled out) -- but the identical
content, copied into an otherwise-identical fresh directory by a *separate* subprocess (plain
``cp -R``), enumerates correctly for the very same Python process afterwards. This points to a
process-provenance-based sandboxing/entitlement restriction on that environment's directory
enumeration, not a code-signing ("Gatekeeper") problem, and not anything wrong with the installed
PySide6 package itself -- see the implementer's completion report for this round for the full
diagnostic steps.

The fix here is narrowly scoped to *this test suite's own process environment*: copy the
installed platform-plugin files into a fresh directory (created via ``tempfile.mkdtemp()``,
never touching anything outside that self-created directory) using a separate ``cp -R``
subprocess on macOS specifically (matching the isolation above), and point ``QT_PLUGIN_PATH`` at
the copy before any ``QApplication`` is ever constructed. This has no effect on production
behavior (``qfield_builder/ui/app.py`` is untouched) and is a no-op cost-wise on platforms where
this restriction does not apply (elsewhere, a plain in-process copy is used).
"""
from __future__ import annotations

import atexit
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    # Registered here too (in addition to tests/acceptance/qfield_project_builder/conftest.py,
    # which also defines the `--run-network` option itself) so a plain `pytest tests/unit` run
    # never warns about an unregistered marker for tests/unit/test_osm_tiles.py's
    # `@pytest.mark.network`-marked real-OSM-tile-fetch test -- see that conftest's own
    # `network` marker/`--run-network` option, which this mirrors and is skipped-by-default under
    # the exact same convention.
    config.addinivalue_line(
        "markers", "network: requires live network access to a real external API/tile server"
    )
    config.addinivalue_line(
        "markers", "legacy_compatibility: explicitly exercises the pre-D-95 source contract"
    )


def _copy_platforms_dir(src: Path, dst: Path) -> None:
    if sys.platform == "darwin":
        # See module docstring: on macOS, populate `dst` via a genuinely separate `cp`
        # subprocess rather than an in-process `shutil.copytree` -- observed to be required for
        # Qt's own directory enumeration to later find the copied files in this environment.
        subprocess.run(["cp", "-R", str(src), str(dst)], check=True)
    else:
        shutil.copytree(src, dst)


def _ensure_qt_platform_plugins_are_discoverable() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # IMPORTANT: this must run, and QT_PLUGIN_PATH must be set, *before* PySide6 is ever
    # imported anywhere in the process. Importing PySide6 has the side effect of registering its
    # own bundled plugin directory with Qt immediately (independent of QT_PLUGIN_PATH), and Qt
    # caches its resolved plugin search paths the first time they are needed -- setting
    # QT_PLUGIN_PATH afterwards (even from within the same still-running process) is too late to
    # change anything. `importlib.util.find_spec` resolves PySide6's install location without
    # importing/executing it, so this ordering constraint can be satisfied.
    spec = importlib.util.find_spec("PySide6")
    if spec is None or not spec.origin:
        return  # PySide6 isn't installed in this environment; nothing for this hook to do.

    original_platforms_dir = Path(spec.origin).parent / "Qt" / "plugins" / "platforms"
    if not original_platforms_dir.is_dir():
        return

    temp_plugins_root = Path(tempfile.mkdtemp(prefix="qpb-qt-plugins-"))
    _copy_platforms_dir(original_platforms_dir, temp_plugins_root / "platforms")
    os.environ["QT_PLUGIN_PATH"] = str(temp_plugins_root)
    atexit.register(shutil.rmtree, str(temp_plugins_root), ignore_errors=True)


_ensure_qt_platform_plugins_are_discoverable()


@pytest.fixture(autouse=True)
def _isolate_credential_store(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Hard isolation guard (Decision Log D-53/D-55; extended by D-81/D-86's rename):
    `qfield_builder.credential_store` now persists an application-managed, locally-encrypted
    `credentials.enc` file under this application's own real, per-user application-data directory
    (`app_data_dir()`, A-QPB-005 -- e.g. `~/Library/Application Support/FieldBuild Standalone/` on
    macOS), rather than the OS credential store this project used before (`keyring`/Keychain/
    Credential Manager -- now removed entirely, AC-QPB-089).

    Every test in this suite must be hermetic and must never read from, write to, or delete from
    that real, persistent, per-user directory -- exactly the class of external, per-user
    application state this project's isolation rules forbid touching from test/diagnostic code.
    This now also covers `legacy_app_data_dir()` (NFR-QPB-081), the pre-rename, `QField Project
    Builder`-named directory `migrate_legacy_credentials()` reads from -- pointed here at a
    sibling, isolated, non-existent-by-default directory, never the real one, for the same
    reason.

    This autouse fixture points `credential_store.app_data_dir()`/`legacy_app_data_dir()` at
    fresh, test-owned `tmp_path` subdirectories instead, so every `credential_store` function
    (`is_password_established`, `establish_password`, `unlock_session`,
    `remember_key`/`get_remembered_key`/`forget_remembered_key`, their Pl@ntNet mirrors, and
    `migrate_legacy_credentials`) runs its real, unmodified implementation against isolated,
    empty-by-default directories -- never the real ones. It also resets this module's own
    process-lifetime ("this application session") state -- the cached unlocked derived key and
    the two in-memory session-only key slots -- before and after every test, so a password
    established/unlocked by one test can never leak into another. A test that wants to exercise a
    *specific* remembered-key or migration scenario can still explicitly
    `monkeypatch.setattr(wizard_module.credential_store, "get_remembered_key", ...)` (or
    similar), or call the module's own real `establish_password`/`remember_key`/
    `migrate_legacy_credentials` functions against these isolated directories (re-pointing
    `app_data_dir`/`legacy_app_data_dir` again, per-test, as needed) -- both remain fully
    supported."""
    from qfield_builder import credential_store as credential_store_module

    isolated_app_data_dir = tmp_path / "app-data"
    isolated_legacy_app_data_dir = tmp_path / "legacy-app-data"
    monkeypatch.setattr(credential_store_module, "app_data_dir", lambda: isolated_app_data_dir)
    monkeypatch.setattr(
        credential_store_module, "legacy_app_data_dir", lambda: isolated_legacy_app_data_dir
    )

    credential_store_module.lock_session()
    credential_store_module.set_session_key(None)
    credential_store_module.set_session_plantnet_key(None)
    yield
    credential_store_module.lock_session()
    credential_store_module.set_session_key(None)
    credential_store_module.set_session_plantnet_key(None)
