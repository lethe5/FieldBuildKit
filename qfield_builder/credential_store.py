"""Independent encrypted API-key storage for FieldBuild Standalone.

Keys are session-only unless remembered. Remembered values are encrypted with
PBKDF2-HMAC-SHA256 (600,000 iterations and a random salt) and Fernet.
The store lives in this app's own platform-specific application-data directory.
The application never imports credentials from either source application.
"""
from __future__ import annotations

import base64
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

#: A-QPB-005: this application's own, newly introduced application-data-directory convention --
#: no such convention existed anywhere in this specification/codebase before Decision Log D-53.
#: Renamed by Decision Log D-81/D-86 (FR-QPB-131's application rename to "FieldBuild Standalone") from
#: this constant's own prior value -- see `_LEGACY_APP_DATA_DIR_NAME` below and NFR-QPB-081's
#: required one-time migration.
_APP_DATA_DIR_NAME = "FieldBuild Standalone"

#: NFR-QPB-081 (Decision Log D-81/D-86): this application's application-data-directory name prior
#: to FR-QPB-131's rename -- kept only so `legacy_app_data_dir()`/`migrate_legacy_credentials()`
#: below can find and copy forward (never move, never delete) an already-remembered key from a
#: pre-rename installation. Never used for any new write by this module.
_LEGACY_APP_DATA_DIR_NAME = "QField Project Builder"
_CREDENTIALS_FILENAME = "credentials.enc"

#: Defense-in-depth test/diagnostic seam only -- never read by any normal application code path
#: decision. Lets a test (or a one-off, self-contained diagnostic script) redirect this module's
#: notion of "the app-data directory" without monkeypatching `app_data_dir` itself, so this
#: module's real, unmodified filesystem logic never has to touch a real user's actual per-user
#: application-data directory. `tests/unit/conftest.py` uses the (equivalent, preferred)
#: `monkeypatch.setattr(credential_store, "app_data_dir", ...)` seam instead; this env var exists
#: purely as an additional, independent safety net.
_APP_DATA_DIR_ENV_OVERRIDE = "FIELDBUILD_STANDALONE_APP_DATA_DIR"

#: NFR-QPB-018/072/073, AC-QPB-091: a named, concrete KDF with an explicit work factor -- never a
#: default/unspecified iteration count.
PBKDF2_ITERATIONS = 600_000
#: AC-QPB-091: a randomly generated, per-installation salt of at least 16 bytes -- never fixed/
#: hardcoded.
SALT_BYTES = 16
_DERIVED_KEY_LENGTH_BYTES = 32

#: A fixed, non-secret plaintext, encrypted once at `establish_password()` time and stored
#: alongside the salt, so a later `unlock_session()` call can verify a supplied password is
#: correct (AC-QPB-093) even before any key has ever actually been remembered.
_VERIFIER_PLAINTEXT = b"fieldbuild-standalone-credential-store-verifier-v1"

_VWORLD_FIELD = "vworld_api_key"
_PLANTNET_FIELD = "plantnet_api_key"


class CredentialStoreError(Exception):
    """Base class for this module's own dedicated exceptions."""


class PasswordNotEstablishedError(CredentialStoreError):
    """Raised by `unlock_session` when no encrypted-storage password has ever been established
    (NFR-QPB-073's first-launch setup step must run before this)."""


class CredentialStoreLockedError(CredentialStoreError):
    """Raised by `get_remembered_key`/`get_remembered_plantnet_key`/`remember_key`/
    `remember_plantnet_key` when a remembered value exists (or is being stored) but the current
    application session has not yet unlocked the encrypted store via `unlock_session`/
    `establish_password` -- callers (the wizard UI) must prompt for the password at that specific
    point of use (NFR-QPB-073/AC-QPB-097) and retry, never silently guess or bypass it."""


class CredentialDecryptionError(CredentialStoreError):
    """AC-QPB-093: raised by `unlock_session` when the supplied password fails to verify against
    the stored salt/verifier -- the dedicated, never-silently-guessed/brute-forced/bypassed
    failure mode for a forgotten password. Any previously remembered key is then permanently
    unrecoverable; the caller must fall back to manual key entry."""


#: Process-lifetime ("this application session") cache of the derived Fernet key, set either by
#: `establish_password` (first-launch setup) or `unlock_session` (retrieval-time re-prompt).
#: NFR-QPB-073/AC-QPB-097: supplied at most once per session, never re-requested at every
#: retrieval point within the same run once already supplied.
_unlocked_fernet_key: bytes | None = None

_session_key: str | None = None
_plantnet_session_key: str | None = None


# ---------------------------------------------------------------------------------------------
# A-QPB-005: the application-data-directory convention.
# ---------------------------------------------------------------------------------------------


def _platform_named_app_data_dir(name: str) -> Path:
    """A-QPB-005's per-platform application-data-directory convention, parameterized on the
    directory's own name -- shared by `app_data_dir()` (current, `FieldBuild Standalone`-named directory)
    and `legacy_app_data_dir()` (NFR-QPB-081's pre-rename, `QField Project Builder`-named
    directory) below, so both stay in sync with the exact same per-platform path convention and
    never drift independently."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / name

    # A-QPB-005 only names macOS/Windows conventions (this project's two MVP platforms,
    # NFR-QPB-030). This is a reasonable, harmless default for any other platform (e.g. Linux,
    # used by this project's own dev/CI environment) so this module never crashes outright there.
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / name


def app_data_dir() -> Path:
    """This application's own local, writable, per-installation application-data directory
    (A-QPB-005). A plain module-level function (not a constant) so tests can monkeypatch it
    directly to an isolated directory -- exactly like this project's existing `fetch_layers_fn`-
    style injectable-test-seam convention -- and so this module's real, unmodified filesystem
    logic never has to run against a real user's actual per-user application-data directory from
    a test."""
    override = os.environ.get(_APP_DATA_DIR_ENV_OVERRIDE)
    if override:
        return Path(override)
    return _platform_named_app_data_dir(_APP_DATA_DIR_NAME)


def legacy_app_data_dir() -> Path:
    """NFR-QPB-081 (Decision Log D-81/D-86): the pre-rename, `QField Project Builder`-named
    application-data directory this application used before FR-QPB-131's rename to "FieldBuild
    Kit". Consulted only by `migrate_legacy_credentials()` below, and only ever read -- never
    written to or deleted -- mirroring `app_data_dir()`'s own monkeypatchable-module-level-function
    convention so tests can point this at an isolated directory too."""
    return _platform_named_app_data_dir(_LEGACY_APP_DATA_DIR_NAME)


def credentials_file_path() -> Path:
    return app_data_dir() / _CREDENTIALS_FILENAME


def migrate_legacy_credentials() -> bool:
    """Compatibility no-op: independent apps never import another app's credentials."""
    return False


def _load_store() -> dict | None:
    path = credentials_file_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # A corrupted/unreadable file is treated the same as "nothing established/remembered"
        # rather than crashing the application -- there is no way to recover its contents anyway.
        return None


def _write_store(store: dict) -> None:
    """Minor Finding 3 (reviewer round, D-53/D-55): written atomically -- a temp file in the same
    directory, then `os.replace()` (an atomic rename on both POSIX and Windows) -- so a crash or
    power loss mid-write can never leave `credentials.enc` half-written/corrupted. Written to the
    same directory (not the OS's generic temp directory) so the final `os.replace()` is guaranteed
    to be an atomic same-filesystem rename, not a cross-filesystem copy. `_load_store()` already
    treats a corrupted/unreadable file as "nothing established" (see its own docstring), so this is
    hardening consistent with this project's existing atomicity discipline (E-QPB-009), not a fix
    for a previously-observed corruption."""
    path = credentials_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{_CREDENTIALS_FILENAME}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(json.dumps(store))
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp_name)
        raise


def _derive_fernet_key(password: str, salt: bytes, iterations: int) -> bytes:
    """NFR-QPB-018/072 (revised)/AC-QPB-091: PBKDF2-HMAC-SHA256, named and concrete, producing a
    32-byte key -- `cryptography`'s `PBKDF2HMAC`, not a hand-assembled/novel construction."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_DERIVED_KEY_LENGTH_BYTES,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


# ---------------------------------------------------------------------------------------------
# NFR-QPB-073: first-launch password setup, and the retrieval-time-only re-prompt (D-55/O-21).
# ---------------------------------------------------------------------------------------------


def is_password_established() -> bool:
    """NFR-QPB-073/AC-QPB-092: whether an encrypted-storage password has ever been established
    (this launch or a previous one) -- decides whether the first-launch setup prompt must be
    shown, and whether "Remember this key" may be offered at all this session."""
    store = _load_store()
    return bool(store and "salt" in store and "verifier" in store)


def is_unlocked() -> bool:
    """Whether the current application session already has a derived key cached -- from having
    just established a new password this session, or from a prior, successful `unlock_session`
    call this session -- so no further password prompt is needed."""
    return _unlocked_fernet_key is not None


def lock_session() -> None:
    """Clears this session's cached derived key (e.g. so a test can simulate a fresh application
    launch without a real process restart)."""
    global _unlocked_fernet_key
    _unlocked_fernet_key = None


def establish_password(password: str) -> None:
    """NFR-QPB-073 first-launch setup step (AC-QPB-092): creates a brand-new random salt and
    verifier and (over)writes `credentials.enc` with them, discarding any previously stored
    encrypted key material -- a *new* password/salt pair can never decrypt ciphertext produced
    under a previous, different derived key anyway, so there is nothing usable left to keep. This
    is also the mechanism by which a user who forgot a previous password may "establish a new
    password... to resume 'Remember this key' behavior going forward" (NFR-QPB-073). Also unlocks
    the current session with the newly established password, so the user is never immediately
    asked to re-enter the very password they just chose."""
    salt = os.urandom(SALT_BYTES)
    key = _derive_fernet_key(password, salt, PBKDF2_ITERATIONS)
    verifier = Fernet(key).encrypt(_VERIFIER_PLAINTEXT).decode("ascii")
    _write_store(
        {
            "salt": base64.b64encode(salt).decode("ascii"),
            "iterations": PBKDF2_ITERATIONS,
            "verifier": verifier,
        }
    )
    global _unlocked_fernet_key
    _unlocked_fernet_key = key


def unlock_session(password: str) -> None:
    """NFR-QPB-073/AC-QPB-097 retrieval-time re-prompt: verifies `password` against the
    established salt/verifier and, if correct, caches the derived key for the rest of this
    application session. Raises `PasswordNotEstablishedError` if no password has ever been
    established, or `CredentialDecryptionError` (AC-QPB-093) if `password` is wrong -- this
    module never silently guesses, brute-forces, or bypasses a forgotten password."""
    store = _load_store()
    if store is None or "salt" not in store or "verifier" not in store:
        raise PasswordNotEstablishedError(
            "암호화 저장을 위한 비밀번호가 아직 설정되지 않았습니다."
        )
    salt = base64.b64decode(store["salt"])
    iterations = int(store.get("iterations", PBKDF2_ITERATIONS))
    key = _derive_fernet_key(password, salt, iterations)
    try:
        plaintext = Fernet(key).decrypt(store["verifier"].encode("ascii"))
    except InvalidToken as exc:
        raise CredentialDecryptionError(
            "비밀번호가 올바르지 않아 저장된 키를 복호화할 수 없습니다. 이전에 기억된 키는 "
            "복구할 수 없으며, API 키를 직접 다시 입력해야 합니다."
        ) from exc
    if plaintext != _VERIFIER_PLAINTEXT:
        raise CredentialDecryptionError("비밀번호 확인에 실패했습니다.")
    global _unlocked_fernet_key
    _unlocked_fernet_key = key


def _require_unlocked_fernet() -> Fernet:
    if _unlocked_fernet_key is None:
        raise CredentialStoreLockedError(
            "저장된 키를 사용하려면 먼저 암호화 저장 비밀번호를 확인해야 합니다."
        )
    return Fernet(_unlocked_fernet_key)


def _remember_field(field_name: str, api_key: str) -> None:
    fernet = _require_unlocked_fernet()  # Never touches disk if locked -- see docstring above.
    store = _load_store() or {}
    store[field_name] = fernet.encrypt(api_key.strip().encode("utf-8")).decode("ascii")
    _write_store(store)


def _forget_field(field_name: str) -> None:
    store = _load_store()
    if not store or field_name not in store:
        return
    store.pop(field_name, None)
    _write_store(store)


def _get_field(field_name: str) -> str | None:
    store = _load_store()
    if not store or field_name not in store:
        return None
    fernet = _require_unlocked_fernet()
    try:
        return fernet.decrypt(store[field_name].encode("ascii")).decode("utf-8").strip()
    except InvalidToken as exc:
        raise CredentialDecryptionError(
            "저장된 키를 복호화할 수 없습니다. 비밀번호가 올바르지 않거나 저장된 값이 "
            "손상되었습니다."
        ) from exc


# ------------------------------------------------------------------- VWorld key (NFR-QPB-018) ---


def remember_key(api_key: str) -> None:
    """NFR-QPB-018 (revised): persist `api_key`, encrypted, in `credentials.enc`. Raises
    `CredentialStoreLockedError` if the current session has not unlocked the encrypted store yet
    (see `apply_retention_policy`, which already treats that as "must not block the build")."""
    _remember_field(_VWORLD_FIELD, api_key)


def forget_remembered_key() -> None:
    _forget_field(_VWORLD_FIELD)


def get_remembered_key() -> str | None:
    """Returns the previously remembered VWorld key, or `None` if nothing is remembered. Raises
    `CredentialStoreLockedError` if a key *is* remembered but the session has not yet unlocked the
    encrypted store (the caller -- `qfield_builder.ui.wizard` -- must prompt for the password at
    that specific point of use and retry; see NFR-QPB-073/AC-QPB-097)."""
    return _get_field(_VWORLD_FIELD)


def set_session_key(api_key: str | None) -> None:
    """Session-only retention (no "Remember this key" opt-in): in-memory for this process only."""
    global _session_key
    _session_key = api_key


def get_session_key() -> str | None:
    return _session_key


def apply_retention_policy(api_key: str, remember: bool) -> bool:
    """Applies NFR-QPB-018 (revised)'s retention policy: always sets the in-memory, this-process-
    only session key; additionally persists `api_key` into the encrypted store when `remember` is
    true and the store is currently unlocked in *this* process.

    Returns `True` unless `remember` was requested but persisting actually failed (most commonly
    because the encrypted store is locked in this process -- see the module docstring's "real
    desktop application" note below) -- Minor Finding 2 (reviewer round, D-53/D-55): callers that
    want to surface a user-facing signal for a failed "Remember this key" request may check this
    return value. A `False` return is informational only; it must never block the build
    (NFR-QPB-073), exactly as before this return value existed.

    Real desktop application note (Finding 1, reviewer round, D-53/D-55): `qfield_builder.build.
    build_project()` -- the only caller of this function -- always runs inside a freshly spawned
    `multiprocessing`-`spawn` OS worker process in the real application
    (`qfield_builder.worker_process.run_job_in_subprocess`), a fresh Python interpreter that
    re-imports this module from scratch and can never have already unlocked the encrypted store.
    This call therefore always finds the store locked (and returns `False` for a `remember=True`
    request) in that real, subprocess-driven path -- by design, not a bug: the actual persistence
    for the real desktop application now happens earlier, directly in the UI process, at the one
    point it is guaranteed to already be unlocked -- see `qfield_builder.ui.wizard.
    ReviewAndBuildPage._persist_remembered_keys()`. This function's own call site inside
    `build.py` remains load-bearing for the *direct*, in-process `build_project()` call the
    acceptance-test harness (`qfield_builder.acceptance_api`) and this module's own unit tests
    use, where no subprocess boundary exists and this call is the only, sufficient persistence
    step."""
    api_key = api_key.strip()
    set_session_key(api_key)
    if not remember:
        return True
    try:
        remember_key(api_key)
        return True
    except Exception:  # noqa: BLE001 - a credential-store failure must not block the build
        return False


# ---------------------------------------------------------------------------------------------
# NFR-QPB-072 (revised; Decision Log D-45/D-53): the Pl@ntNet-key mirror of the functions above.
# Kept as separate functions (rather than adding an `account=` parameter to the VWorld functions
# above) so the two credentials' retention remain visibly, independently scoped -- exactly as
# NFR-QPB-019 (revised) requires -- and so no existing VWorld call site's signature changes.
# ---------------------------------------------------------------------------------------------


def remember_plantnet_key(api_key: str) -> None:
    """NFR-QPB-072 (revised): mirrors `remember_key` for the Pl@ntNet key."""
    _remember_field(_PLANTNET_FIELD, api_key)


def forget_remembered_plantnet_key() -> None:
    _forget_field(_PLANTNET_FIELD)


def get_remembered_plantnet_key() -> str | None:
    """Mirrors `get_remembered_key` for the Pl@ntNet key -- same `CredentialStoreLockedError`
    contract."""
    return _get_field(_PLANTNET_FIELD)


def set_session_plantnet_key(api_key: str | None) -> None:
    """Session-only retention (no "Remember this key" opt-in): in-memory for this process only."""
    global _plantnet_session_key
    _plantnet_session_key = api_key


def get_session_plantnet_key() -> str | None:
    return _plantnet_session_key


def apply_plantnet_retention_policy(api_key: str, remember: bool) -> bool:
    """Mirrors `apply_retention_policy` for the Pl@ntNet key -- same return-value contract (Minor
    Finding 2) and the same real-desktop-application caveat (Finding 1) documented there."""
    api_key = api_key.strip()
    set_session_plantnet_key(api_key)
    if not remember:
        return True
    try:
        remember_plantnet_key(api_key)
        return True
    except Exception:  # noqa: BLE001 - a credential-store failure must not block the build
        return False
