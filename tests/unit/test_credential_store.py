"""Unit tests for qfield_builder.credential_store (Decision Log D-53/D-55).

Covers the application-managed, password-derived, locally-encrypted "remember this key"
mechanism that replaces the prior OS-credential-store (`keyring`) implementation entirely:

- AC-QPB-089: no `keyring` import/call anywhere in this module's own source.
- AC-QPB-090: a remembered key's plaintext value never appears in `credentials.enc`'s raw bytes.
- AC-QPB-091: the KDF is a named PBKDF2-HMAC-SHA256 call with an explicit iteration count of at
  least 600,000 and a randomly generated, per-installation salt of at least 16 bytes.
- AC-QPB-093: a forgotten/incorrect password fails decryption explicitly (a dedicated exception,
  never a silent guess/bypass), and the user must fall back to manual key entry.
- A-QPB-005: the new application-data-directory convention (macOS/Windows paths, `credentials.enc`
  filename).
- Bug 2 regression (carried over from the pre-D-53 implementation): whitespace/control characters
  around a key are stripped both on store and on retrieve.

Every test in this file relies on `tests/unit/conftest.py`'s autouse `_isolate_credential_store`
fixture, which points `credential_store.app_data_dir()` at a fresh, test-owned temporary directory
-- this suite never reads, writes, or deletes anything under a real user's actual per-user
application-data directory. No literal, real-looking API key value is used anywhere in this file
(all are synthetic placeholders, e.g. `MY-REAL-KEY`, distinguishable at a glance).
"""
from __future__ import annotations

import ast
import inspect
import json

import pytest

from qfield_builder import credential_store

# Captured at import time, before this module (or any per-test monkeypatching) can affect the
# `sys.platform`-dependent branch inside `app_data_dir()` -- this project's own established
# convention for referring to a "real" implementation that a later monkeypatch may shadow (see
# the pre-D-53 revision of this same file for the precedent).
_REAL_APP_DATA_DIR = credential_store.app_data_dir

# A key with a leading space, an embedded/trailing newline, and a trailing tab -- the same class
# of corruption the pre-D-53 implementation's own regression test covered.
DIRTY_KEY = " MY-REAL-KEY\n\t"
CLEAN_KEY = "MY-REAL-KEY"

PASSWORD = "correct horse battery staple"  # noqa: S105 - a synthetic test password, not a secret.
WRONG_PASSWORD = "definitely not the right password"  # noqa: S105


# --------------------------------------------------------------------------------------------
# AC-QPB-089: no `keyring` import/call anywhere in this module's retention code path.
# --------------------------------------------------------------------------------------------


def test_module_source_contains_no_keyring_import():
    source = inspect.getsource(credential_store)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(alias.name.split(".")[0] == "keyring" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or node.module.split(".")[0] != "keyring"


def test_module_source_contains_no_keyring_attribute_call():
    """Guards against a `keyring.xxx(...)` call reached via some indirect import alias -- the
    prose mention of "keyring" in this module's own docstring (explaining what it replaces) is
    deliberately not what this asserts against; only an actual `keyring.<attr>` call pattern."""
    source = inspect.getsource(credential_store)
    assert "keyring." not in source


# --------------------------------------------------------------------------------------------
# A-QPB-005: the application-data-directory convention.
# --------------------------------------------------------------------------------------------


def test_app_data_dir_uses_the_macos_convention(monkeypatch):
    """NFR-QPB-018 (further revised)/NFR-QPB-072 (further revised), Decision Log D-81/D-86: the
    application-data directory is named "FieldBuild Standalone," not the pre-rename "QField Project
    Builder.\""""
    monkeypatch.setattr(credential_store.sys, "platform", "darwin")
    monkeypatch.delenv("FIELDBUILD_STANDALONE_APP_DATA_DIR", raising=False)
    result = _REAL_APP_DATA_DIR()
    assert result.parts[-3:] == ("Library", "Application Support", "FieldBuild Standalone")


def test_app_data_dir_uses_the_windows_convention(monkeypatch, tmp_path):
    monkeypatch.setattr(credential_store.sys, "platform", "win32")
    monkeypatch.delenv("FIELDBUILD_STANDALONE_APP_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    result = _REAL_APP_DATA_DIR()
    assert result == tmp_path / "Roaming" / "FieldBuild Standalone"


def test_credentials_file_path_is_named_credentials_enc(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    assert credential_store.credentials_file_path() == tmp_path / "credentials.enc"


# --------------------------------------------------------------------------------------------
# NFR-QPB-081 (Decision Log D-81/D-86): the pre-rename, legacy application-data-directory name,
# and the one-time, copy-only credential-store migration into the new, "FieldBuild Standalone"-named
# directory.
# --------------------------------------------------------------------------------------------

_REAL_LEGACY_APP_DATA_DIR = credential_store.legacy_app_data_dir


def test_legacy_app_data_dir_uses_the_pre_rename_macos_name(monkeypatch):
    """The legacy directory this application used before Decision Log D-81/D-86's rename --
    "QField Project Builder," never "FieldBuild Standalone" -- so `migrate_legacy_credentials()` below
    looks in the right place for a pre-rename installation's own stored key."""
    monkeypatch.setattr(credential_store.sys, "platform", "darwin")
    result = _REAL_LEGACY_APP_DATA_DIR()
    assert result.parts[-3:] == ("Library", "Application Support", "QField Project Builder")


def test_legacy_app_data_dir_uses_the_pre_rename_windows_name(monkeypatch, tmp_path):
    monkeypatch.setattr(credential_store.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    result = _REAL_LEGACY_APP_DATA_DIR()
    assert result == tmp_path / "Roaming" / "QField Project Builder"


def test_migrate_legacy_credentials_fresh_install_is_a_no_op(tmp_path, monkeypatch):
    """AC-QPB-119: given a fresh install with no pre-existing `QField Project Builder`-named
    application-data directory anywhere, migration is a clean no-op: no error, and no
    `credentials.enc` is created until a key is actually remembered."""
    new_dir = tmp_path / "new"
    legacy_dir = tmp_path / "legacy-does-not-exist"
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: new_dir)
    monkeypatch.setattr(credential_store, "legacy_app_data_dir", lambda: legacy_dir)

    migrated = credential_store.migrate_legacy_credentials()

    assert migrated is False
    assert not credential_store.credentials_file_path().exists()
    assert not new_dir.exists()


def test_independent_app_never_reads_legacy_credentials(monkeypatch):
    def forbidden():
        raise AssertionError("Another app's credential store must not be consulted")

    monkeypatch.setattr(credential_store, "legacy_app_data_dir", forbidden)
    assert credential_store.migrate_legacy_credentials() is False


def test_migrate_legacy_credentials_never_overwrites_an_already_populated_new_store(
    tmp_path, monkeypatch
):
    """AC-QPB-121: given both an old (legacy-named) directory and a new-named directory already
    populated with their own, independent `credentials.enc` files, migration is a no-op in both
    directions -- the new directory's own file is authoritative and is never overwritten/merged,
    and the legacy directory's file is likewise left completely untouched."""
    legacy_dir = tmp_path / "legacy"
    new_dir = tmp_path / "new"

    monkeypatch.setattr(credential_store, "app_data_dir", lambda: legacy_dir)
    monkeypatch.setattr(credential_store, "legacy_app_data_dir", lambda: legacy_dir)
    credential_store.establish_password("legacy-password")  # noqa: S106
    credential_store.remember_key("LEGACY-KEY")
    legacy_credentials_bytes_before = (legacy_dir / "credentials.enc").read_bytes()
    credential_store.lock_session()

    monkeypatch.setattr(credential_store, "app_data_dir", lambda: new_dir)
    credential_store.establish_password("new-password")  # noqa: S106
    credential_store.remember_key("NEW-KEY")
    new_credentials_bytes_before = (new_dir / "credentials.enc").read_bytes()
    credential_store.lock_session()

    migrated = credential_store.migrate_legacy_credentials()

    assert migrated is False
    assert (new_dir / "credentials.enc").read_bytes() == new_credentials_bytes_before
    assert (legacy_dir / "credentials.enc").read_bytes() == legacy_credentials_bytes_before


# --------------------------------------------------------------------------------------------
# AC-QPB-091: named PBKDF2-HMAC-SHA256, >= 600,000 iterations, >= 16-byte random per-installation
# salt.
# --------------------------------------------------------------------------------------------


def test_kdf_parameters_meet_the_minimum_bar():
    assert credential_store.PBKDF2_ITERATIONS >= 600_000
    assert credential_store.SALT_BYTES >= 16


def test_establish_password_calls_a_named_pbkdf2_hmac_sha256_kdf_with_required_parameters(
    monkeypatch,
):
    captured_kwargs = {}
    real_pbkdf2hmac = credential_store.PBKDF2HMAC

    def _spy_pbkdf2hmac(*, algorithm, length, salt, iterations):
        captured_kwargs["algorithm"] = algorithm
        captured_kwargs["length"] = length
        captured_kwargs["salt"] = salt
        captured_kwargs["iterations"] = iterations
        return real_pbkdf2hmac(
            algorithm=algorithm, length=length, salt=salt, iterations=iterations
        )

    monkeypatch.setattr(credential_store, "PBKDF2HMAC", _spy_pbkdf2hmac)

    credential_store.establish_password(PASSWORD)

    assert captured_kwargs["iterations"] >= 600_000
    assert len(captured_kwargs["salt"]) >= 16
    assert type(captured_kwargs["algorithm"]).__name__ == "SHA256"


def test_two_independent_installations_receive_different_random_salts(tmp_path, monkeypatch):
    dir_a = tmp_path / "install-a"
    dir_b = tmp_path / "install-b"

    monkeypatch.setattr(credential_store, "app_data_dir", lambda: dir_a)
    credential_store.establish_password(PASSWORD)
    store_a = json.loads(credential_store.credentials_file_path().read_text(encoding="utf-8"))

    credential_store.lock_session()
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: dir_b)
    credential_store.establish_password(PASSWORD)
    store_b = json.loads(credential_store.credentials_file_path().read_text(encoding="utf-8"))

    assert store_a["salt"] != store_b["salt"]


def test_established_password_stores_iteration_count_alongside_salt(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    store = json.loads(credential_store.credentials_file_path().read_text(encoding="utf-8"))
    assert store["iterations"] >= 600_000
    import base64

    assert len(base64.b64decode(store["salt"])) >= 16


# --------------------------------------------------------------------------------------------
# AC-QPB-090: a remembered key's plaintext value never appears anywhere in `credentials.enc`'s
# raw bytes.
# --------------------------------------------------------------------------------------------


def test_remembered_key_plaintext_never_appears_in_the_encrypted_file(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)

    raw_bytes = credential_store.credentials_file_path().read_bytes()
    assert CLEAN_KEY.encode("utf-8") not in raw_bytes


def test_remembered_plantnet_key_plaintext_never_appears_in_the_encrypted_file(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_plantnet_key(CLEAN_KEY)

    raw_bytes = credential_store.credentials_file_path().read_bytes()
    assert CLEAN_KEY.encode("utf-8") not in raw_bytes


def test_remembered_key_round_trips_through_encryption(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)

    assert credential_store.get_remembered_key() == CLEAN_KEY


# --------------------------------------------------------------------------------------------
# Locked-session behaviour: reading/writing a remembered key before the encrypted store has been
# unlocked this session must never silently succeed with wrong data -- it must raise a dedicated
# exception the caller (the wizard UI) is expected to handle by prompting for the password.
# --------------------------------------------------------------------------------------------


def test_get_remembered_key_raises_locked_error_when_a_key_exists_but_session_is_locked(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)
    credential_store.lock_session()  # Simulates a fresh application launch.

    with pytest.raises(credential_store.CredentialStoreLockedError):
        credential_store.get_remembered_key()


def test_get_remembered_key_returns_none_when_nothing_is_remembered_even_if_unlocked(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    assert credential_store.get_remembered_key() is None


def test_remember_key_raises_locked_error_instead_of_silently_persisting_when_locked(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    # Already creates credentials.enc (salt/verifier only, no key material yet).
    credential_store.establish_password(PASSWORD)
    credential_store.lock_session()

    with pytest.raises(credential_store.CredentialStoreLockedError):
        credential_store.remember_key(CLEAN_KEY)

    # Confirms this never silently wrote a (would-be-locked) key to disk -- the file still only
    # contains what `establish_password` itself wrote (salt/iterations/verifier), never a
    # `vworld_api_key` entry.
    store = json.loads(credential_store.credentials_file_path().read_text(encoding="utf-8"))
    assert credential_store._VWORLD_FIELD not in store


def test_unlock_session_with_correct_password_allows_retrieval_after_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)
    credential_store.lock_session()

    assert not credential_store.is_unlocked()
    credential_store.unlock_session(PASSWORD)
    assert credential_store.is_unlocked()
    assert credential_store.get_remembered_key() == CLEAN_KEY


# --------------------------------------------------------------------------------------------
# AC-QPB-093: a forgotten/incorrect password fails decryption explicitly -- never silently
# guessed, brute-forced, or bypassed -- and the user must fall back to manual entry.
# --------------------------------------------------------------------------------------------


def test_unlock_session_with_wrong_password_raises_a_dedicated_decryption_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)
    credential_store.lock_session()

    with pytest.raises(credential_store.CredentialDecryptionError):
        credential_store.unlock_session(WRONG_PASSWORD)


def test_a_forgotten_password_never_eventually_succeeds_after_repeated_wrong_attempts(
    tmp_path, monkeypatch
):
    """The forgotten-password consequence must be a clean, explicit failure -- not a crash, not a
    silently-wrong value, and not eventually succeeding on retry with the same wrong password."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)
    credential_store.lock_session()

    for _attempt in range(3):
        with pytest.raises(credential_store.CredentialDecryptionError):
            credential_store.unlock_session(WRONG_PASSWORD)

    # The session must still be locked -- a failed unlock attempt must never leave a partially
    # "unlocked" state that `get_remembered_key()` would trust.
    assert not credential_store.is_unlocked()
    with pytest.raises(credential_store.CredentialStoreLockedError):
        credential_store.get_remembered_key()


def test_establishing_a_new_password_after_forgetting_the_old_one_discards_stale_ciphertext(
    tmp_path, monkeypatch
):
    """NFR-QPB-073: "may establish a new encrypted-storage password to resume 'Remember this key'
    behavior going forward" -- the old, now-permanently-undecryptable ciphertext must not linger
    forever; establishing a fresh password starts from a clean slate."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(CLEAN_KEY)

    credential_store.establish_password("a-brand-new-password")  # noqa: S106

    assert credential_store.is_unlocked()
    assert credential_store.get_remembered_key() is None


def test_unlock_session_without_any_established_password_raises_a_distinct_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    with pytest.raises(credential_store.PasswordNotEstablishedError):
        credential_store.unlock_session(PASSWORD)


# --------------------------------------------------------------------------------------------
# NFR-QPB-073/AC-QPB-092: first-launch decline path -- session-only fallback.
# --------------------------------------------------------------------------------------------


def test_is_password_established_is_false_before_any_password_is_ever_set(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    assert credential_store.is_password_established() is False


def test_apply_retention_policy_falls_back_to_session_only_when_no_password_established(
    tmp_path, monkeypatch
):
    """Decline path (NFR-QPB-073): "Remember this key" silently has no persisted effect when no
    encrypted-storage password has ever been established -- the build must not be blocked, and
    the key must still be retained for the current session."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)

    credential_store.apply_retention_policy(DIRTY_KEY, remember=True)

    assert credential_store.get_session_key() == CLEAN_KEY
    assert not credential_store.credentials_file_path().is_file()


def test_apply_plantnet_retention_policy_falls_back_to_session_only_when_no_password_established(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)

    credential_store.apply_plantnet_retention_policy(DIRTY_KEY, remember=True)

    assert credential_store.get_session_plantnet_key() == CLEAN_KEY
    assert not credential_store.credentials_file_path().is_file()


# --------------------------------------------------------------------------------------------
# Bug 2 regression (carried over unchanged): whitespace/control characters are stripped both on
# store and on retrieve.
# --------------------------------------------------------------------------------------------


def test_remember_key_strips_whitespace_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_key(DIRTY_KEY)
    assert credential_store.get_remembered_key() == CLEAN_KEY


def test_get_remembered_key_self_heals_a_pre_existing_corrupted_stored_value(
    tmp_path, monkeypatch
):
    """Simulates a value already saved with embedded whitespace from before this fix shipped --
    reading it back must return the cleaned value, not perpetuate the corruption. `_remember_field`
    itself always strips (there is no lower-level entry point that doesn't), so the dirty value is
    seeded by writing directly into the on-disk store, bypassing this module's functions
    entirely -- exactly modelling "data already on disk from an older version of this code"."""
    from cryptography.fernet import Fernet

    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    store = json.loads(credential_store.credentials_file_path().read_text(encoding="utf-8"))
    dirty_ciphertext = Fernet(credential_store._unlocked_fernet_key).encrypt(
        DIRTY_KEY.encode("utf-8")
    )
    store[credential_store._VWORLD_FIELD] = dirty_ciphertext.decode("ascii")
    credential_store.credentials_file_path().write_text(json.dumps(store), encoding="utf-8")

    assert credential_store.get_remembered_key() == CLEAN_KEY


def test_apply_retention_policy_strips_before_session_and_persisted_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    credential_store.apply_retention_policy(DIRTY_KEY, remember=True)

    assert credential_store.get_session_key() == CLEAN_KEY
    assert credential_store.get_remembered_key() == CLEAN_KEY


def test_apply_retention_policy_strips_the_session_key_even_when_not_remembered(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.apply_retention_policy(DIRTY_KEY, remember=False)
    assert credential_store.get_session_key() == CLEAN_KEY
    assert credential_store.get_remembered_key() is None


# --------------------------------------------------------------------------------------------
# Pl@ntNet key (NFR-QPB-072 mirror).
# --------------------------------------------------------------------------------------------


def test_remember_plantnet_key_strips_whitespace_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.remember_plantnet_key(DIRTY_KEY)
    assert credential_store.get_remembered_plantnet_key() == CLEAN_KEY


def test_get_remembered_plantnet_key_returns_none_when_nothing_is_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    assert credential_store.get_remembered_plantnet_key() is None


def test_apply_plantnet_retention_policy_strips_before_session_and_persisted_storage(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    credential_store.apply_plantnet_retention_policy(DIRTY_KEY, remember=True)

    assert credential_store.get_session_plantnet_key() == CLEAN_KEY
    assert credential_store.get_remembered_plantnet_key() == CLEAN_KEY


def test_vworld_and_plantnet_keys_are_independently_scoped(tmp_path, monkeypatch):
    """NFR-QPB-019 (revised): neither credential's retention state leaks into the other's."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    credential_store.remember_key("VWORLD-ONLY-KEY")
    credential_store.remember_plantnet_key("PLANTNET-ONLY-KEY")

    assert credential_store.get_remembered_key() == "VWORLD-ONLY-KEY"
    assert credential_store.get_remembered_plantnet_key() == "PLANTNET-ONLY-KEY"

    credential_store.forget_remembered_key()
    assert credential_store.get_remembered_key() is None
    assert credential_store.get_remembered_plantnet_key() == "PLANTNET-ONLY-KEY"


# --------------------------------------------------------------------------------------------
# Finding 1 fix (reviewer round, D-53/D-55): `apply_retention_policy`/
# `apply_plantnet_retention_policy` now return whether a requested "remember" actually persisted,
# so `qfield_builder.ui.wizard.ReviewAndBuildPage` (which now calls these directly in the UI
# process, per that fix) can tell success from failure. The real cross-process regression itself
# (a real build through the actual subprocess boundary) is covered by
# `tests/unit/test_smoke_gui.py::
# test_real_gui_end_to_end_build_with_remember_this_key_persists_to_credentials_enc` -- these
# tests only cover the return-value contract these two functions now expose.
# --------------------------------------------------------------------------------------------


def test_apply_retention_policy_returns_true_when_persisted_successfully(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    assert credential_store.apply_retention_policy(CLEAN_KEY, remember=True) is True


def test_apply_retention_policy_returns_true_when_remember_not_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)

    assert credential_store.apply_retention_policy(CLEAN_KEY, remember=False) is True


def test_apply_retention_policy_returns_false_when_remember_requested_but_store_is_locked(
    tmp_path, monkeypatch
):
    """Reproduces, at the `credential_store` level, exactly the condition Finding 1 identified:
    `remember=True` requested while the encrypted store is locked in the calling process (e.g.
    the real, freshly spawned build-worker subprocess, whose own module-level "unlocked" state is
    always `None`) -- this must be reported via the return value, never raise, and must still
    record the session-only key regardless (NFR-QPB-073: never blocks the build)."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.lock_session()  # Simulates a fresh process that never unlocked the store.

    assert credential_store.apply_retention_policy(CLEAN_KEY, remember=True) is False
    assert credential_store.get_session_key() == CLEAN_KEY


def test_apply_plantnet_retention_policy_returns_false_when_remember_requested_but_store_is_locked(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)
    credential_store.lock_session()

    assert credential_store.apply_plantnet_retention_policy(CLEAN_KEY, remember=True) is False
    assert credential_store.get_session_plantnet_key() == CLEAN_KEY


# --------------------------------------------------------------------------------------------
# Minor Finding 3 (reviewer round, D-53/D-55): `credentials.enc` is written atomically (temp file
# in the same directory, then `os.replace()`), so a crash mid-write can never corrupt it.
# --------------------------------------------------------------------------------------------


def test_write_store_never_leaves_a_temp_file_behind_on_success(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)
    credential_store.establish_password(PASSWORD)

    tmp_prefix = f".{credential_store._CREDENTIALS_FILENAME}."
    leftover_tmp_files = [p for p in tmp_path.iterdir() if p.name.startswith(tmp_prefix)]
    assert leftover_tmp_files == []
    assert credential_store.credentials_file_path().is_file()


def test_write_store_uses_a_same_directory_temp_file_and_atomic_replace(tmp_path, monkeypatch):
    """Directly verifies the atomicity mechanism itself (not just its absence of side effects):
    the temp file is created in the same directory as the final file (guaranteeing `os.replace()`
    is a same-filesystem, atomic rename), and `os.replace` -- not a non-atomic `shutil.move`/
    `write_text` -- is what actually publishes the final file."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)

    observed_tmp_dirs = []
    real_mkstemp = credential_store.tempfile.mkstemp

    def _spy_mkstemp(*args, **kwargs):
        observed_tmp_dirs.append(kwargs.get("dir"))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(credential_store.tempfile, "mkstemp", _spy_mkstemp)

    replace_calls = []
    real_replace = credential_store.os.replace

    def _spy_replace(src, dst):
        replace_calls.append((src, dst))
        return real_replace(src, dst)

    monkeypatch.setattr(credential_store.os, "replace", _spy_replace)

    credential_store.establish_password(PASSWORD)

    assert observed_tmp_dirs == [str(tmp_path)]
    assert len(replace_calls) == 1
    assert replace_calls[0][1] == credential_store.credentials_file_path()


def test_write_store_cleans_up_its_temp_file_if_the_replace_step_itself_fails(
    tmp_path, monkeypatch
):
    """A failure after the temp file is written (e.g. a disk error at the final `os.replace()`
    step) must not leave a stray temp file behind forever."""
    monkeypatch.setattr(credential_store, "app_data_dir", lambda: tmp_path)

    def _broken_replace(src, dst):
        raise OSError("simulated disk failure during the atomic rename step")

    monkeypatch.setattr(credential_store.os, "replace", _broken_replace)

    with pytest.raises(OSError):
        credential_store.establish_password(PASSWORD)

    tmp_prefix = f".{credential_store._CREDENTIALS_FILENAME}."
    leftover_tmp_files = [p for p in tmp_path.iterdir() if p.name.startswith(tmp_prefix)]
    assert leftover_tmp_files == []
    assert not credential_store.credentials_file_path().is_file()
