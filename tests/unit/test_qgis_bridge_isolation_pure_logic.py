"""Pure-logic regression tests for `qfield_builder.qgis_bridge`'s profile-isolation guardrail.

These tests require no real QGIS/PyQGIS installation at all -- they exercise
`_assert_settings_dir_is_sandboxed`, `_ensure_isolated_profile_env`, and `_merged_env` directly as
plain Python path/environment logic. This is deliberate: the guardrail must be provably correct on
every machine (including CI with no QGIS installed at all), not merely "observed to work" against
one real installation.

Background: a prior round of this project's own development had an ad hoc diagnostic command
delete a real user's actual, persistent QGIS profile directory. A follow-up review of the first
isolation fix found it was not strict enough -- it treated "anywhere under the system temp
directory" as approved, rather than requiring the specific, fresh, invocation-owned directory this
process itself just created. These tests target exactly that distinction.

Every test in this file uses `monkeypatch` to replace `qgis_bridge._real_qgis_profile_roots` with a
fake, test-local path standing in for "a real, persistent profile location" -- never the genuine
`~/Library/Application Support/QGIS` (or platform equivalent) -- so nothing here ever touches, or
even references, the actual real profile on the machine running these tests.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from qfield_builder import qgis_bridge


@pytest.fixture(autouse=True)
def _fake_real_profile_root(tmp_path, monkeypatch):
    """Replaces the real, persistent profile root(s) with a test-local fake for every test in
    this file, so no test ever needs to reference (or risks touching) the genuine location."""
    fake_root = tmp_path / "fake_real_qgis_profile_root"
    monkeypatch.setattr(qgis_bridge, "_real_qgis_profile_roots", lambda: [fake_root])
    return fake_root


def test_settings_dir_equal_to_expected_root_is_accepted(tmp_path):
    """A valid invocation-owned profile directory: `settings_dir == expected_root` must pass."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    qgis_bridge._assert_settings_dir_is_sandboxed(str(expected_root), expected_root)


def test_settings_dir_strict_descendant_of_expected_root_is_accepted(tmp_path):
    """QGIS resolving to a *subdirectory* of the invocation-owned root (the real-world case,
    e.g. `<owned>/profiles/default/`) must also pass."""
    expected_root = tmp_path / "owned"
    (expected_root / "profiles" / "default").mkdir(parents=True)
    qgis_bridge._assert_settings_dir_is_sandboxed(
        str(expected_root / "profiles" / "default"), expected_root
    )


def test_real_profile_root_itself_is_rejected(tmp_path, _fake_real_profile_root):
    """An inherited real-profile path: `settings_dir` pointing exactly at the (faked) real,
    persistent profile root must always be rejected, regardless of `expected_root`."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    _fake_real_profile_root.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(_fake_real_profile_root), expected_root)


def test_subdirectory_of_real_profile_root_is_rejected(tmp_path, _fake_real_profile_root):
    """A subdirectory of the (faked) real profile root must also be rejected -- not just an
    exact match on the root itself."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    sub = _fake_real_profile_root / "profiles" / "default"
    sub.mkdir(parents=True)
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(sub), expected_root)


def test_arbitrary_non_temp_path_is_rejected(tmp_path):
    """An inherited arbitrary non-temp path (e.g. somewhere under the user's home directory,
    unrelated to any temp directory at all) must be rejected even though it is not the real
    profile root either -- it is simply not the invocation-owned directory."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    arbitrary = tmp_path / "not_owned_by_anyone"
    arbitrary.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(arbitrary), expected_root)


def test_system_temp_root_itself_is_not_automatically_approved(monkeypatch, tmp_path):
    """The system temp directory *root* itself must not be treated as an approved profile
    location merely by virtue of being "under temp" -- only the specific, fresh, invocation-owned
    subdirectory is trusted. Simulated here by making `expected_root` a subdirectory of a fake
    temp root, then asserting the fake temp root itself (an ancestor, not `expected_root` or a
    descendant of it) is rejected as `settings_dir`.
    """
    fake_temp_root = tmp_path / "fake_system_temp"
    fake_temp_root.mkdir()
    monkeypatch.setattr(qgis_bridge.tempfile, "gettempdir", lambda: str(fake_temp_root))
    expected_root = fake_temp_root / "qpb-qgis-profile-abc123"
    expected_root.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(fake_temp_root), expected_root)


def test_arbitrary_temp_path_not_created_by_this_invocation_is_rejected(tmp_path):
    """A *different* directory that also happens to live under the system temp root, but was not
    the directory this specific invocation created and owns, must still be rejected -- "lives
    under temp" is not sufficient; it must be `expected_root` (or a descendant of it) exactly."""
    expected_root = tmp_path / "owned-by-this-invocation"
    expected_root.mkdir()
    unrelated_sibling = tmp_path / "owned-by-a-different-invocation"
    unrelated_sibling.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(unrelated_sibling), expected_root)


def test_symlink_escaping_expected_root_into_a_persistent_profile_is_rejected(
    tmp_path, _fake_real_profile_root
):
    """A symlink *inside* the invocation-owned directory that points outside it -- specifically
    at a (faked) real, persistent profile location -- must be rejected. `Path.resolve()` follows
    the symlink to its real target before comparison, so the "is it a descendant of
    expected_root" check (and the independent "is it a real profile root" check) both operate on
    where the path actually leads, not its literal on-disk location inside the owned directory.
    """
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    _fake_real_profile_root.mkdir()
    escape_link = expected_root / "profiles"
    escape_link.symlink_to(_fake_real_profile_root, target_is_directory=True)
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(escape_link), expected_root)


def test_symlink_escaping_expected_root_into_an_unrelated_directory_is_rejected(tmp_path):
    """Same as above, but escaping into an unrelated (non-"real-profile", just not-owned)
    directory -- confirms the *descendant-of-expected-root* check alone (not only the
    real-profile-root check) also catches a symlink escape."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    unrelated = tmp_path / "unrelated-escape-target"
    unrelated.mkdir()
    escape_link = expected_root / "escape"
    escape_link.symlink_to(unrelated, target_is_directory=True)
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(escape_link), expected_root)


def test_partially_nonexistent_but_contained_path_is_accepted(tmp_path):
    """A settings dir that does not exist yet, but whose path is a legitimate, non-traversing
    subpath of `expected_root` (as `QgsApplication.qgisSettingsDirPath()` may report a path QGIS
    has not created a moment before it does), must still resolve as a valid descendant."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    not_yet_created = expected_root / "profiles" / "default"
    qgis_bridge._assert_settings_dir_is_sandboxed(str(not_yet_created), expected_root)


def test_partially_nonexistent_path_that_escapes_via_traversal_is_rejected(tmp_path):
    """A settings dir that does not exist yet *and* whose path uses `..` traversal to escape
    `expected_root` upward must be rejected -- non-existence must never be a way to bypass the
    descendant check."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    escaping_nonexistent = expected_root / ".." / "escaped" / "does-not-exist"
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(escaping_nonexistent), expected_root)


def test_none_settings_dir_is_rejected(tmp_path):
    """QGIS reporting no settings directory at all must fail closed, not be treated as vacuously
    fine."""
    expected_root = tmp_path / "owned"
    expected_root.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(None, expected_root)


def test_none_expected_root_is_rejected_even_for_an_otherwise_plausible_dir(tmp_path):
    """A missing `expected_root` (no invocation-owned directory was ever established) must fail
    closed even if `settings_dir` looks like a perfectly reasonable temp-ish path -- there must
    always be a specific, known-owned directory to check against, never a vibe-based check."""
    plausible_dir = tmp_path / "looks-fine"
    plausible_dir.mkdir()
    with pytest.raises(qgis_bridge.QgisProfileIsolationError):
        qgis_bridge._assert_settings_dir_is_sandboxed(str(plausible_dir), None)


def test_ensure_isolated_profile_env_always_creates_a_fresh_directory(monkeypatch):
    """`_ensure_isolated_profile_env` must never trust, extend, or reuse a pre-existing
    `QGIS_CUSTOM_CONFIG_PATH` -- even a plausible-looking one -- and must always create and
    return a brand-new directory of its own on every call."""
    monkeypatch.setenv(qgis_bridge._QGIS_PROFILE_ENV_VAR, "/some/pre-existing/inherited/value")
    try:
        first = qgis_bridge._ensure_isolated_profile_env()
        # Compared via `.resolve()` on both sides: `_ensure_isolated_profile_env` sets the raw,
        # unresolved `mkdtemp()` path into `os.environ` and returns the fully resolved `Path` --
        # on macOS these legitimately differ as strings (`/var/...` vs. `/private/var/...`, since
        # `/var` is itself a symlink) while still naming the same real directory.
        assert Path(os.environ[qgis_bridge._QGIS_PROFILE_ENV_VAR]).resolve() == first
        assert str(first) != "/some/pre-existing/inherited/value"
        assert first.is_dir()

        second = qgis_bridge._ensure_isolated_profile_env()
        assert second != first, "a second call must create a distinct fresh directory, not reuse"
        assert Path(os.environ[qgis_bridge._QGIS_PROFILE_ENV_VAR]).resolve() == second
    finally:
        for created in list(qgis_bridge._created_profile_dirs):
            qgis_bridge._created_profile_dirs.remove(created)
            import shutil

            shutil.rmtree(created, ignore_errors=True)


def test_merged_env_overwrites_an_inherited_real_profile_path(
    tmp_path, monkeypatch, _fake_real_profile_root
):
    """Environment merging: a pre-existing `QGIS_CUSTOM_CONFIG_PATH` pointing at the (faked)
    real, persistent profile root must be overwritten by `_merged_env`'s `profile_dir`, not
    inherited into the child's starting environment."""
    _fake_real_profile_root.mkdir()
    monkeypatch.setenv(qgis_bridge._QGIS_PROFILE_ENV_VAR, str(_fake_real_profile_root))
    fresh = tmp_path / "fresh-profile"
    fresh.mkdir()
    env = qgis_bridge._merged_env({}, profile_dir=str(fresh))
    assert env[qgis_bridge._QGIS_PROFILE_ENV_VAR] == str(fresh)
    assert env[qgis_bridge._QGIS_PROFILE_ENV_VAR] != str(_fake_real_profile_root)


def test_merged_env_overwrites_an_inherited_arbitrary_non_temp_path(tmp_path, monkeypatch):
    """Environment merging: a pre-existing `QGIS_CUSTOM_CONFIG_PATH` pointing at some arbitrary,
    unrelated, non-temp path must also always be overwritten, not merely `setdefault`-preserved."""
    arbitrary = tmp_path / "some" / "arbitrary" / "inherited" / "path"
    arbitrary.mkdir(parents=True)
    monkeypatch.setenv(qgis_bridge._QGIS_PROFILE_ENV_VAR, str(arbitrary))
    fresh = tmp_path / "fresh-profile-2"
    fresh.mkdir()
    env = qgis_bridge._merged_env({"SOME_OTHER_VAR": "x"}, profile_dir=str(fresh))
    assert env[qgis_bridge._QGIS_PROFILE_ENV_VAR] == str(fresh)
    assert env["SOME_OTHER_VAR"] == "x"


def test_merged_env_without_profile_dir_leaves_var_untouched(monkeypatch):
    """When no `profile_dir` is supplied at all (not a code path any bridge function currently
    takes, but a documented contract of the helper itself), `_merged_env` must not invent or
    clear the variable -- it only ever overrides when a caller explicitly hands it a directory
    to use."""
    monkeypatch.setenv(qgis_bridge._QGIS_PROFILE_ENV_VAR, "whatever-was-there")
    env = qgis_bridge._merged_env({})
    assert env[qgis_bridge._QGIS_PROFILE_ENV_VAR] == "whatever-was-there"
