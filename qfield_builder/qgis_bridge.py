"""Bridges to a real, detected QGIS Desktop installation's own Python/PyQGIS environment.

This is the fix for the core architectural gap identified in review: PyQGIS is, on many real
QGIS Desktop installations (especially macOS ``.app`` bundles and many Windows installs), *not*
importable from a bare, separately-installed ``python3`` — it only reliably works from inside
that installation's own bundled Python interpreter (or, on supported non-Windows installations,
from inside the QGIS application binary itself, driven via its ``--code <script>`` option). Neither
is "the current
process" (this application's own host Python), and neither is `sys.executable` (which
:mod:`multiprocessing`'s ``spawn`` context re-executes by default) — both of those are simply
whatever interpreter this application itself happens to be running under, which never has PyQGIS
unless the *user's own environment* happens to already provide it (FR-QPB-007a explicitly forbids
relying on a pip-installed PyQGIS to make that so).

Detection strategy (mirrors FR-QPB-008's per-OS install locations / ``QGIS_PREFIX_PATH`` override,
now extended to also record *how* to reach that install's own Python):

1. Look for a per-OS list of plausible QGIS Desktop install roots (plus the
   ``QGIS_PREFIX_PATH``/``QGIS_INSTALL_PATH`` manual override).
2. For each root, enumerate candidate ways to run code inside it:
   - a bundled standalone Python interpreter (with the environment, e.g. ``PYTHONHOME``, that
     interpreter needs to find its own ``qgis`` package) — tried first, since it is faster and
     does not need to drive a full GUI event loop; or, on non-Windows installations only,
   - the QGIS Desktop application binary itself, driven headlessly (``QT_QPA_PLATFORM=offscreen``)
     via its ``--code <script>`` option, as a compatibility fallback for installations that ship
     no standalone Python.
3. Probe each candidate with a minimal ``import qgis.core`` smoke test; the first candidate that
   actually succeeds becomes the cached "bridge target" for the remainder of this process's
   lifetime — every later job dispatch (:func:`run_job`) reuses it without re-probing.

Job dispatch (:func:`run_job`) then genuinely launches a separate OS process using that target,
passing the job (a plain module/function/kwargs triple, all JSON-serializable) via a temp file and
reading the result back via a temp file — never assuming a shared Python object model with the
caller, and never importing ``qgis.*`` in the caller's own process.
"""
from __future__ import annotations

import atexit
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from .resource_paths import repo_or_bundle_root


def _bridge_source_root() -> str:
    """The directory to insert onto the bridge subprocess's own `sys.path` so that
    ``import qfield_builder`` succeeds there, correctly both when running from source and when
    running as a PyInstaller-packaged application.

    The bridge subprocess runs under a *different* Python installation entirely (a real QGIS
    Desktop install's own bundled Python, or its GUI binary driven via ``--code``) -- it needs a
    genuine, real, on-disk ``qfield_builder`` package directory of loose ``.py`` files to import
    from; this package has no non-stdlib runtime dependency other than ``qgis.*`` itself (see
    module docstrings of ``qgis_worker``, ``feature_save``, ``validate``), so no other
    third-party install is required inside the QGIS-owned interpreter.

    - When *not* frozen (running from an unpacked source checkout, e.g. under pytest, ``python
      -m``, or the installed console-script entry point): ``qfield_builder.resource_paths.
      repo_or_bundle_root()`` resolves to the real repo root, which already contains
      ``qfield_builder/`` as a normal, loose-``.py``-file directory -- so that root itself is
      exactly right to put on `sys.path`.
    - When frozen (PyInstaller): ``repo_or_bundle_root()`` resolves to PyInstaller's own
      ``sys._MEIPASS`` extraction root. Once PyInstaller has packaged this application's own
      Python modules into its own ``PYZ`` archive format, there is no real, on-disk directory of
      loose ``qfield_builder/*.py`` source files there for `__file__`-based arithmetic to find
      (that archive format is opaque to the foreign QGIS-owned interpreter this subprocess runs
      under) -- so a *separate*, real, on-disk copy of this package's source is bundled as plain
      **data** instead (see ``packaging/qfield_builder.spec``'s ``datas`` list), at the
      predictable location ``<meipass>/qfield_builder_src/qfield_builder/...``. Putting
      ``<meipass>/qfield_builder_src`` (not ``<meipass>`` itself) on `sys.path` is what makes
      ``import qfield_builder`` resolve to that bundled copy.
    """
    root = repo_or_bundle_root()
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return str(root / "qfield_builder_src")
    return str(root)


# Computed once at import time (not lazily re-resolved on every `run_job`/`run_ad_hoc_script`
# call): `sys.frozen`/`sys._MEIPASS` are established by the PyInstaller bootloader before any of
# this application's own modules are ever imported, in every frozen build, on every platform
# PyInstaller supports -- so there is no meaningful moment during this module's own lifetime where
# re-checking would observe a different answer.
_REPO_ROOT = _bridge_source_root()

_PROBE_TIMEOUT_SECONDS = 30.0
DEFAULT_JOB_TIMEOUT_SECONDS = 180.0
MIN_SUPPORTED_QGIS_VERSION = (3, 44)
_QGIS_VERSION_PATTERN = re.compile(r"^\s*(\d+)\.(\d+)(?:\.(\d+))?")

_BOOTSTRAP_TEMPLATE = """\
import importlib
import json
import os
import sys
import traceback

sys.path.insert(0, {repo_root!r})

job_file = {job_file!r}
result_file = {result_file!r}

try:
    # Establishes an isolated QGIS profile/config directory and constructs `QgsApplication`
    # *before* the dispatched job's own module is even imported, so nothing in this process ever
    # touches `qgis.core` without a `QgsApplication` already having been constructed. Confirmed
    # empirically (against a real, locally installed QGIS 3.44.12): a job function that never
    # constructs a `QgsApplication` at all but still lazily touches a default style/symbol (e.g.
    # `QgsSymbol.defaultSymbol`) otherwise silently writes a stray `symbology-style.db` relative
    # to this process's cwd -- setting `QGIS_CUSTOM_CONFIG_PATH` alone, without ever constructing
    # a `QgsApplication`, does *not* prevent this (QGIS logs "Application path not initialized"
    # and ignores the env var in that case). See `qfield_builder.qgis_bridge.
    # ensure_qgis_application` for the exact mechanism and its own docstring for more detail.
    from qfield_builder.qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    with open(job_file, "r", encoding="utf-8") as _f:
        _job = json.load(_f)
    _module = importlib.import_module(_job["module"])
    _func = getattr(_module, _job["func"])
    _result = _func(**_job.get("kwargs", {{}}))
    _payload = {{"ok": True, "result": _result}}
except Exception as _exc:  # noqa: BLE001 - must always report a structured result, never hang.
    _payload = {{"ok": False, "error": str(_exc), "traceback": traceback.format_exc()}}

try:
    with open(result_file, "w", encoding="utf-8") as _f:
        json.dump(_payload, _f)
finally:
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - best-effort flush only.
        pass
    # `--code`-driven QGIS GUI binaries would otherwise fall through into their normal
    # interactive event loop; a plain interpreter also exits cleanly via this same call, so a
    # single unconditional hard-exit is used for both bridge kinds.
    os._exit(0)
"""

_IMPORT_PROBE_SCRIPT = """\
import sys
try:
    import qgis.core as _c
except Exception as _e:  # noqa: BLE001 - reported back verbatim; never a crash.
    print("QPB_BRIDGE_IMPORT_FAILED:" + str(_e))
    sys.exit(0)
print("QPB_BRIDGE_IMPORT_OK:" + str(_c.Qgis.QGIS_VERSION))
"""

_IMPORT_PROBE_SCRIPT_EXIT = _IMPORT_PROBE_SCRIPT + "\nimport os\nos._exit(0)\n"


@dataclass(frozen=True)
class BridgeTarget:
    """One concrete, working way to run Python code inside a real QGIS install's own PyQGIS."""

    kind: str  # "python_interpreter" | "gui_code"
    executable: str
    env: dict
    install_path: str
    qgis_version: str | None = None


def qgis_version_tuple(version: str | None) -> tuple[int, int, int] | None:
    """Return QGIS's numeric version prefix, ignoring its release-name suffix."""
    match = _QGIS_VERSION_PATTERN.match(str(version or ""))
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def is_supported_qgis_version(version: str | None) -> bool:
    """Only QGIS 3.44.0 and later are eligible bridge runtimes."""
    parsed = qgis_version_tuple(version)
    return parsed is not None and parsed[:2] >= MIN_SUPPORTED_QGIS_VERSION


class QgisProfileIsolationError(RuntimeError):
    """Raised when QGIS's resolved settings directory is not a sandboxed, throwaway directory.

    This is a hard, fail-closed safety check, independent of anything the approved specification
    requires. During this project's own development, an ad hoc diagnostic command run outside
    this module (not through any function here) deleted a real user's actual, persistent QGIS
    profile directory. This exception exists so that any future bug, environment quirk, or
    misuse that would cause a real `QgsApplication` to resolve its settings directory to a real,
    persistent profile location instead aborts immediately, before QGIS can read, write, or (via
    some unrelated command) delete anything there — rather than silently proceeding.
    """


def _real_qgis_profile_roots() -> list[Path]:
    """The real, persistent, per-user QGIS profile root(s) this process must never resolve into.

    These are the directories a real QGIS installation uses by default when
    `QGIS_CUSTOM_CONFIG_PATH` is *not* set — i.e. exactly the location every function in this
    module exists to avoid. Deliberately independent of whether any of these paths currently
    exist on this machine (a fresh machine with no QGIS profile yet must still be protected
    against ever having this process create one).
    """
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return [home / "Library" / "Application Support" / "QGIS"]
    if system == "Windows":
        roots = []
        for var in ("APPDATA", "LOCALAPPDATA"):
            value = os.environ.get(var)
            if value:
                roots.append(Path(value) / "QGIS")
        return roots
    return [home / ".local" / "share" / "QGIS", home / ".qgis3", home / ".qgis2"]


def _assert_not_a_real_profile_root(resolved: Path) -> None:
    """Defense-in-depth: never allow `resolved` to be, or be inside, a real QGIS profile root.

    Checked independently of `_assert_settings_dir_is_sandboxed`'s main "is it the expected
    invocation-owned directory" check, so that even a bug in the expected-root bookkeeping still
    cannot result in accepting a real profile location.
    """
    for forbidden in _real_qgis_profile_roots():
        forbidden_resolved = forbidden.resolve() if forbidden.exists() else forbidden.absolute()
        if resolved == forbidden_resolved or forbidden_resolved in resolved.parents:
            raise QgisProfileIsolationError(
                f"Refusing to continue: path ({resolved}) is the real, persistent QGIS profile "
                f"location ({forbidden_resolved}), not an isolated throwaway directory. Aborting "
                "before QGIS can read, write, or delete anything there."
            )


def _assert_settings_dir_is_sandboxed(settings_dir: str | None, expected_root: Path | None) -> None:
    """Fails closed unless `settings_dir` resolves to `expected_root` or a strict descendant of it.

    `expected_root` must be the *specific*, freshly created, invocation-owned directory this
    exact invocation established (via `_ensure_isolated_profile_env`) — never merely "somewhere
    under the system temp directory". The system temp directory itself, or an arbitrary path
    that happens to live under it but was not created by this invocation, is deliberately
    treated as untrusted, not approved: only a directory this invocation itself just created and
    can account for is trusted. Both paths are resolved (`Path.resolve()`, which follows and
    collapses symlinks) before comparison specifically so that a symlink inside the expected
    root pointing outside it — including one pointing at a real profile location — is caught by
    the descendant check below, rather than compared by raw string prefix.

    Called immediately after every `QgsApplication` construction, both before and after
    `initQgis()` (see `ensure_qgis_application`) — never trust that the isolation *setup* code
    worked; verify the actual, resolved outcome every time instead. This is a fail-fast,
    fail-closed check: it aborts further processing in this process the moment a violation is
    detected. It does **not** retroactively undo, and cannot guarantee the absence of, any read
    or write QGIS itself may already have performed between resolving its settings path
    internally and the moment this function runs — see `ensure_qgis_application`'s own
    docstring for the honest scope of what the pre-/post-`initQgis()` checks each do and do not
    cover.
    """
    if not settings_dir:
        raise QgisProfileIsolationError(
            "Refusing to continue: QGIS did not report a settings directory at all "
            "(qgisSettingsDirPath() returned empty/None), so isolation cannot be confirmed."
        )
    resolved = Path(settings_dir).resolve()
    _assert_not_a_real_profile_root(resolved)
    if expected_root is None:
        raise QgisProfileIsolationError(
            "Refusing to continue: no invocation-owned profile directory was established before "
            "QGIS initialization, so isolation cannot be confirmed against anything specific."
        )
    expected_resolved = expected_root.resolve()
    if resolved != expected_resolved and expected_resolved not in resolved.parents:
        raise QgisProfileIsolationError(
            f"Refusing to continue: QGIS's resolved settings directory ({resolved}) is not the "
            f"same as, or a descendant of, the fresh directory this invocation created and owns "
            f"({expected_resolved}). The system temporary directory root and any other path — "
            "even one that happens to live under it — are not treated as approved merely by "
            "location; only a directory this specific invocation itself just created is trusted."
        )


_qgs_application = None  # Module-level reference keeping the QgsApplication singleton alive.
# Set once, the first time `ensure_qgis_application` actually constructs an application in this
# process; used only to re-verify (never to re-establish) isolation on a later call that finds an
# application already exists.
_last_expected_profile_root: Path | None = None

# The env var a real QGIS install actually respects for where to root its profile/config
# directory (`<this path>/profiles/<profile-name>/...`, holding `QGIS.ini`, `symbology-style.db`,
# `qgis.db`, etc.) — confirmed empirically against a real, locally installed QGIS 3.44.12
# (`/Applications/QGIS.app/Contents/MacOS/python3.12`): with this env var set *and* a
# `QgsApplication` constructed (`QgsApplication([], False)` + `initQgis()`) before anything else
# touches `qgis.core`, every profile-scoped file QGIS writes lands under it, and the process's own
# cwd stays untouched. Critically, setting this env var *without* ever constructing a
# `QgsApplication` first does **not** work on its own — confirmed empirically that a bare
# `import qgis.core` followed directly by a PyQGIS call that lazily touches a default style (e.g.
# `QgsSymbol.defaultSymbol`, used by this codebase's own community-layer symbology) still writes
# a `symbology-style.db` relative to the cwd in that case, logging "Application path not
# initialized" to stderr and silently ignoring the env var — this is exactly the reviewer-reported
# defect's root cause (`qfield_builder.qgis_worker._build_qgis_project_pyqgis` never constructs a
# `QgsApplication` at all). The fix is therefore establishing this env var *and* constructing
# `QgsApplication` unconditionally before *any* job code runs (see `_BOOTSTRAP_TEMPLATE` and
# `ensure_qgis_application` below), not merely setting the env var.
_QGIS_PROFILE_ENV_VAR = "QGIS_CUSTOM_CONFIG_PATH"

# Every temp profile directory `_ensure_isolated_profile_env` has created in this process — one
# per call, always, since that function never trusts or reuses an inherited value (see its own
# docstring). Removed on interpreter shutdown, best-effort: this is *not* the primary fix (the
# primary fix is that QGIS never writes into the invoking cwd in the first place, regardless of
# whether this cleanup ever runs) — merely tidying up so per-run profile directories do not
# accumulate indefinitely under the OS temp directory across many runs of this application.
_created_profile_dirs: list[str] = []


def _cleanup_created_profile_dirs() -> None:
    while _created_profile_dirs:
        profile_dir = _created_profile_dirs.pop()
        shutil.rmtree(profile_dir, ignore_errors=True)


atexit.register(_cleanup_created_profile_dirs)


def _ensure_isolated_profile_env() -> Path:
    """Unconditionally creates a fresh, per-invocation profile directory, pre-created on disk,
    and points `QGIS_CUSTOM_CONFIG_PATH` at it — returning the resolved `Path` so the caller can
    pass it on as the `expected_root` for `_assert_settings_dir_is_sandboxed`.

    Never trusts, reuses, or extends any value already present in `os.environ`, even one this
    same module set moments earlier for a *different* invocation in this same process, and even
    one a direct parent process specifically pre-supplied via `_merged_env` for this exact
    subprocess (that value is deliberately re-created here too, rather than trusted). Only a
    directory this exact call itself just created is ever treated as trustworthy — "already set
    to something plausible" is not a substitute for "created by, and owned by, this invocation".
    """
    profile_dir = Path(tempfile.mkdtemp(prefix="qpb-qgis-profile-"))
    os.environ[_QGIS_PROFILE_ENV_VAR] = str(profile_dir)
    _created_profile_dirs.append(str(profile_dir))
    return profile_dir.resolve()


def ensure_qgis_application():
    """Initializes a headless `QgsApplication` in the *current* process, idempotently.

    Section 5.3 requires that "the worker initializes ``QgsApplication`` without a GUI" before
    performing QGIS/PyQGIS/GDAL operations. Beyond being a literal spec requirement, this turns
    out to matter concretely: without a real `QgsApplication`/Qt event loop ever having been
    constructed in the process, `QgsProject.read()`'s parallel-provider-preloading feature (used
    for any project containing a raster layer backed by the `gdal` provider, e.g. an offline
    MBTiles basemap) has been observed to deadlock — its background worker thread signals
    completion back to the main thread via a queued connection that is never delivered without a
    running Qt event dispatcher on the main thread, which a bare `import qgis.core` does not, by
    itself, set up. Every PyQGIS-calling function in this codebase
    (:mod:`qfield_builder.qgis_worker`, :mod:`qfield_builder.feature_save`,
    :mod:`qfield_builder.validate`) calls this before touching `QgsProject`/`QgsVectorLayer`/etc.,
    whether it ends up running directly in-process or inside a bridge-dispatched subprocess.
    `_BOOTSTRAP_TEMPLATE` additionally calls this unconditionally before dispatching to *any* job
    function, including ones (like `qfield_builder.qgis_worker._build_qgis_project_pyqgis`) that
    never call it themselves — see that template's own comment for why.

    Also establishes an isolated, per-run QGIS profile/config directory (via
    `_ensure_isolated_profile_env`) before constructing `QgsApplication`, so a real QGIS
    installation never writes profile-scoped files (e.g. `symbology-style.db`) into this
    process's own cwd — see `_QGIS_PROFILE_ENV_VAR`'s module-level comment for the empirical
    detail on why the *order* here (env var set, then `QgsApplication` constructed, before
    anything else touches `qgis.core`) is what actually matters.

    Safe to call more than once per process (returns the existing instance if already
    initialized) and safe to call even where PyQGIS is not importable at all — callers are
    expected to have already imported `qgis.core` themselves before calling this.

    Deliberately keeps a module-level reference to the created `QgsApplication`: SIP/PyQt owns
    the underlying C++ object from the Python side here (it was constructed from Python), so if
    nothing keeps the Python wrapper object alive, it is garbage-collected — silently destroying
    the *real* `QApplication` singleton along with it, even though `QgsApplication.instance()`
    briefly returned non-`None` right after construction. Without this, callers that don't keep
    their own reference (e.g. calling this for its side effect only, as every caller in this
    codebase does) would reproduce exactly the deadlock this function exists to avoid, just one
    step further down: `QEventLoop::exec()` fails outright with "QEventLoop: Cannot be used
    without QApplication" once the (garbage-collected) application is gone.

    Profile isolation is checked *twice*, deliberately: once after `QgsApplication(...)` is
    constructed but before `initQgis()` runs, and again immediately after `initQgis()` returns.
    Be precise about what each check does and does not guarantee, and about an empirical
    constraint this design works around: confirmed against a real, locally installed QGIS
    3.44.12, `QgsApplication.qgisSettingsDirPath()` itself reports an *empty string* until after
    `initQgis()` has run — it is not yet meaningful at the pre-`initQgis()` point. The
    pre-`initQgis()` check therefore validates the *configured* `QGIS_CUSTOM_CONFIG_PATH`
    environment variable directly (i.e. the value QGIS is about to read from), not QGIS's own
    not-yet-resolved settings path; this still has real value, as it catches the case where
    something between `_ensure_isolated_profile_env()` and `initQgis()` mutated that variable
    away from what this invocation just established. `initQgis()` is where the heavier
    provider/projection-database loading happens and is where most of QGIS's own real file I/O
    against the settings directory actually occurs, so the *post*-`initQgis()` check — against
    the real, resolved `qgisSettingsDirPath()` — is the more consequential of the two
    operationally, but by construction it can only detect a violation *after* `initQgis()` has
    already run: it aborts before any of *this application's* subsequent code executes, but it
    cannot retroactively undo, and does not prove the absence of, whatever `initQgis()` itself
    may already have read or written by the time this function returns control. Neither check is
    a guarantee that zero I/O occurred before it ran; both are fail-fast/fail-closed aborts on
    the earliest evidence available to this process, not a guarantee of prevention.
    """
    global _qgs_application, _last_expected_profile_root
    from qgis.core import QgsApplication

    existing = QgsApplication.instance()
    if existing is not None:
        # An application already exists in this process (a second call to this function within
        # the same process's lifetime); isolation cannot be re-established retroactively here,
        # only re-verified against whatever expected root this process originally established.
        _assert_settings_dir_is_sandboxed(
            QgsApplication.qgisSettingsDirPath(), _last_expected_profile_root
        )
        return existing
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    expected_root = _ensure_isolated_profile_env()
    _last_expected_profile_root = expected_root
    app = QgsApplication([], False)
    # Pre-`initQgis()` check: validates the *configured environment variable*, not
    # `qgisSettingsDirPath()` (empirically empty/meaningless at this point — see docstring above).
    _assert_settings_dir_is_sandboxed(os.environ.get(_QGIS_PROFILE_ENV_VAR), expected_root)
    app.initQgis()
    # Post-`initQgis()` check: validates QGIS's own actual, resolved settings directory.
    _assert_settings_dir_is_sandboxed(QgsApplication.qgisSettingsDirPath(), expected_root)
    _qgs_application = app
    return app


def _merged_env(overrides: dict, profile_dir: str | None = None) -> dict:
    """Builds a subprocess environment, deliberately never letting an inherited
    `QGIS_CUSTOM_CONFIG_PATH` survive into the child's *starting* environment.

    `env = dict(os.environ)` may copy in a stale or unrelated `QGIS_CUSTOM_CONFIG_PATH` — e.g.
    left over in this process's own environment from an earlier call in the same process, or
    inherited from whatever shell/session launched this process. When `profile_dir` is given,
    it is always assigned directly (`env[_QGIS_PROFILE_ENV_VAR] = profile_dir`), never merely
    `setdefault`, specifically so the spawned worker's process environment is never even
    momentarily seeded with an inherited value — this must hold even though
    `_ensure_isolated_profile_env` (called from `ensure_qgis_application`, itself called
    unconditionally by every bootstrap template) would independently create and use its own
    fresh directory regardless of what it finds; the two are independent, defense-in-depth
    layers, not a "the callee will fix it anyway" excuse for looseness here.
    """
    env = dict(os.environ)
    if platform.system() == "Windows":
        # Windows QGIS has a fragile, installer-owned runtime environment.  Keep the host
        # process untouched, but make the child environment explicit and deterministic.  The
        # target builder supplies the canonical values; empty values are preferable to silently
        # inheriting a conflicting host value when this helper is called without a target.
        for name in (
            "PYTHONHOME",
            "PYTHONPATH",
            "QGIS_PREFIX_PATH",
            "GDAL_DATA",
            "QT_PLUGIN_PATH",
        ):
            env[name] = str(overrides.get(name, ""))
        qgis_path = str(overrides.get("PATH", ""))
        inherited_path = str(os.environ.get("PATH", ""))
        env["PATH"] = _windows_merged_path(qgis_path, inherited_path)
        for name, value in overrides.items():
            if name not in {
                "PYTHONHOME",
                "PYTHONPATH",
                "QGIS_PREFIX_PATH",
                "GDAL_DATA",
                "QT_PLUGIN_PATH",
                "PATH",
            }:
                env[name] = value
    else:
        # Preserve the established macOS/Linux behavior exactly.
        env.update(overrides)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    if profile_dir is not None:
        env[_QGIS_PROFILE_ENV_VAR] = profile_dir
    return env


def _executable_file(path: Path) -> bool:
    return path.is_file() and os.access(str(path), os.X_OK)


_WINDOWS_CONTROLLED_ENV = (
    "PYTHONHOME",
    "PYTHONPATH",
    "QGIS_PREFIX_PATH",
    "GDAL_DATA",
    "QT_PLUGIN_PATH",
    "PATH",
)
_WINDOWS_ENV_REFERENCE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")
_WINDOWS_INSTALL_NAME = re.compile(
    r"^QGIS (?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?$", re.IGNORECASE
)


def _windows_install_version(path: Path) -> tuple[int, int, int] | None:
    match = _WINDOWS_INSTALL_NAME.fullmatch(path.name)
    if match is None:
        return None
    return int(match.group("major")), int(match.group("minor")), int(match.group("patch") or 0)


def _windows_path_entries(value: str) -> list[str]:
    """Split a Windows path-list value even when tests emulate Windows on POSIX."""
    return [entry.strip().strip('"') for entry in str(value).split(";") if entry.strip()]


def _windows_normalize_path_text(value: str) -> Path:
    # The acceptance suite mocks platform.system() on the development macOS host.  Translating
    # separators there keeps the same textual Windows env file useful without changing real
    # Windows behavior, where pathlib already understands backslashes.
    text = str(value).strip().strip('"')
    if os.name != "nt":
        text = text.replace("\\", os.sep)
    return Path(text)


def _windows_expand_env(assignments: dict[str, str]) -> dict[str, str]:
    """Expand ordinary ``%NAME%`` references without invoking a command interpreter."""
    inherited = {str(key).casefold(): str(value) for key, value in os.environ.items()}
    resolving: set[str] = set()

    def resolve(name: str) -> str:
        key = name.casefold()
        # In a batch file, PATH/PYTHONPATH references in their own assignment mean the inherited
        # value, not the assignment currently being constructed.
        if key in {"path", "pythonpath"}:
            return inherited.get(key, "")
        if key in resolving:
            return "%" + name + "%"
        matching_key = next(
            (candidate for candidate in assignments if candidate.casefold() == key), None
        )
        if matching_key is None:
            return inherited.get(key, "%" + name + "%")
        resolving.add(key)
        value = _WINDOWS_ENV_REFERENCE.sub(
            lambda match: resolve(match.group(1)), assignments[matching_key]
        )
        resolving.remove(key)
        return value

    return {key: resolve(key) for key in assignments}


def _parse_windows_qgis_env(env_file: Path) -> dict[str, str] | None:
    """Read QGIS's env file as data; unsupported batch commands are ignored."""
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    assignments: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "@")):
            continue
        if line.lower().startswith("rem "):
            continue
        if line.lower().startswith("set "):
            line = line[4:].lstrip()
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        assignments[key] = value
    expanded = _windows_expand_env(assignments)
    if any("%" in value for value in expanded.values()):
        # An unresolved reference is ambiguous and must not become a child-process path.
        return None
    return expanded


def _windows_resolved_inside(root: Path, candidate: Path) -> Path | None:
    """Return a resolved in-root path, rejecting traversal and escaping symlinks."""
    try:
        root_resolved = root.resolve(strict=True)
        candidate_resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        return None
    return candidate_resolved


def _windows_required_path(root: Path, relative: str, *, file: bool = False) -> Path | None:
    candidate = root / relative
    if candidate.is_symlink():
        return None
    resolved = _windows_resolved_inside(root, candidate)
    if resolved is None:
        return None
    if file:
        return resolved if resolved.is_file() else None
    return resolved if resolved.is_dir() else None


def _windows_env_path_is_safe(root: Path, value: str) -> bool:
    """Validate an installation path from the official env file without trusting it."""
    if not value or "%" in value:
        return False
    path = _windows_normalize_path_text(value)
    if not path.is_absolute():
        path = root / path
    return _windows_resolved_inside(root, path) is not None


def _windows_path_key(value: str) -> str:
    return str(value).replace("/", "\\").rstrip("\\").casefold()


def _windows_merged_path(canonical: str, inherited: str) -> str:
    """Put canonical QGIS directories first and remove WindowsApps/duplicates."""
    entries: list[str] = []
    seen: set[str] = set()
    for entry in _windows_path_entries(canonical) + _windows_path_entries(inherited):
        key = _windows_path_key(entry)
        if key.endswith(r"microsoft\windowsapps") or not key or key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return ";".join(entries)


def _windows_target_env(root: Path, parsed: dict[str, str]) -> dict[str, str] | None:
    """Build only the controlled child variables for a validated Windows QGIS install."""
    python_home = _windows_required_path(root, os.path.join("apps", "Python312"))
    prefix = _windows_required_path(root, os.path.join("apps", "qgis-ltr"))
    pyqgis = _windows_required_path(root, os.path.join("apps", "qgis-ltr", "python"))
    gdal = _windows_required_path(root, os.path.join("share", "gdal"))
    qt_plugins = _windows_required_path(root, os.path.join("apps", "Qt6", "plugins"))
    if not all((python_home, prefix, pyqgis, gdal, qt_plugins)):
        return None

    # Validate explicit installation paths in the official file, but use resolved canonical
    # paths for the child so a conflicting env assignment cannot redirect the bridge.
    for name in ("PYTHONHOME", "QGIS_PREFIX_PATH"):
        if name in parsed and not _windows_env_path_is_safe(root, parsed[name]):
            return None
    for name in ("GDAL_DATA", "QT_PLUGIN_PATH"):
        if name in parsed and not _windows_env_path_is_safe(root, parsed[name]):
            return None

    qgis_dirs = [root / "bin", python_home]
    for relative in (os.path.join("apps", "qgis-ltr", "bin"), os.path.join("apps", "Qt6", "bin")):
        optional = _windows_required_path(root, relative)
        if optional is not None:
            qgis_dirs.append(optional)
    official_path = [entry for entry in _windows_path_entries(parsed.get("PATH", ""))]
    canonical_path = ";".join(str(path) for path in qgis_dirs + official_path)
    return {
        "PYTHONHOME": str(python_home),
        "PYTHONPATH": str(pyqgis),
        "QGIS_PREFIX_PATH": str(root.resolve()),
        "GDAL_DATA": str(gdal),
        "QT_PLUGIN_PATH": str(qt_plugins),
        "PATH": canonical_path,
        "PYTHONNOUSERSITE": "1",
    }


def _macos_candidates(app_bundle_dir: str) -> list[BridgeTarget]:
    macos_dir = Path(app_bundle_dir) / "Contents" / "MacOS"
    frameworks_dir = Path(app_bundle_dir) / "Contents" / "Frameworks"
    candidates: list[BridgeTarget] = []
    if not macos_dir.is_dir():
        return candidates
    for py in sorted(macos_dir.glob("python3.*")):
        if _executable_file(py):
            candidates.append(
                BridgeTarget(
                    kind="python_interpreter",
                    executable=str(py),
                    env={"PYTHONHOME": str(frameworks_dir), "PYTHONNOUSERSITE": "1"},
                    install_path=app_bundle_dir,
                )
            )
    gui_binary = macos_dir / "QGIS"
    if _executable_file(gui_binary):
        candidates.append(
            BridgeTarget(
                kind="gui_code", executable=str(gui_binary), env={}, install_path=app_bundle_dir
            )
        )
    return candidates


def _windows_candidates(root_dir: str) -> list[BridgeTarget]:
    root = Path(root_dir)
    if platform.system() != "Windows":
        return []
    if root.is_symlink():
        return []
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return []
    if not root.is_dir():
        return []

    env_file = root / "bin" / "qgis-ltr-bin.env"
    if env_file.is_symlink() or not env_file.is_file():
        return []
    parsed = _parse_windows_qgis_env(env_file)
    if parsed is None:
        return []
    executable = _windows_required_path(
        root, os.path.join("apps", "Python312", "python.exe"), file=True
    )
    if executable is None or not _executable_file(executable):
        return []
    child_env = _windows_target_env(root, parsed)
    if child_env is None:
        return []
    # Windows intentionally has no wrapper-batch or QGIS-GUI fallback.  The dedicated Python
    # executable is absolute and is used for both import validation and dispatched jobs.
    return [
        BridgeTarget(
            kind="python_interpreter",
            executable=str(executable),
            env=child_env,
            install_path=str(root),
        )
    ]


def _linux_candidates(root_dir: str) -> list[BridgeTarget]:
    candidates: list[BridgeTarget] = []
    for py in (f"{root_dir}/bin/python3", "/usr/bin/python3"):
        if _executable_file(Path(py)):
            candidates.append(
                BridgeTarget(
                    kind="python_interpreter", executable=py, env={}, install_path=root_dir
                )
            )
    for gui in (f"{root_dir}/bin/qgis",):
        if _executable_file(Path(gui)):
            candidates.append(
                BridgeTarget(kind="gui_code", executable=gui, env={}, install_path=root_dir)
            )
    return candidates


def candidate_install_roots() -> list[str]:
    """Plausible QGIS Desktop install roots for this OS, manual override first (FR-QPB-008)."""
    system = platform.system()
    roots: list[str] = []
    env_override = os.environ.get("QGIS_PREFIX_PATH") or os.environ.get("QGIS_INSTALL_PATH")
    if env_override:
        roots.append(env_override)
    if system == "Darwin":
        roots += ["/Applications/QGIS.app", "/Applications/QGIS-LTR.app"]
    elif system == "Windows":
        program_files: list[Path] = []
        for name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = os.environ.get(name)
            if value:
                program_files.append(Path(value))
        if not program_files:
            program_files.append(Path(r"C:\Program Files"))

        patched: list[tuple[tuple[int, int, int], str, Path]] = []
        bare: list[tuple[str, Path]] = []
        for base in program_files:
            try:
                children = list(base.iterdir()) if base.is_dir() else []
            except OSError:
                children = []
            for child in children:
                version = _windows_install_version(child)
                if version is None or version[:2] < MIN_SUPPORTED_QGIS_VERSION or not child.is_dir():
                    continue
                path_key = str(child.absolute()).casefold()
                if child.name.count(".") == 1:
                    bare.append((path_key, child))
                else:
                    patched.append((version, path_key, child))
            # Retain the historical bare path as a compatibility candidate even when it is not
            # present; a manual/legacy install can appear after a later filesystem change.
            legacy = base / "QGIS 3.44"
            if not any(existing == legacy for _, existing in bare):
                bare.append((str(legacy.absolute()).casefold(), legacy))

        seen: set[str] = {str(Path(root).absolute()).casefold() for root in roots}
        for _, _, child in sorted(
            patched, key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1])
        ):
            key = str(child.absolute()).casefold()
            if key not in seen:
                roots.append(str(child))
                seen.add(key)
        for _, child in sorted(bare, key=lambda item: item[0]):
            key = str(child.absolute()).casefold()
            if key not in seen:
                roots.append(str(child))
                seen.add(key)
        for compatibility in (Path(r"C:\OSGeo4W64"), Path(r"C:\OSGeo4W")):
            key = str(compatibility.absolute()).casefold()
            if key not in seen:
                roots.append(str(compatibility))
                seen.add(key)
    else:
        roots += ["/usr", "/usr/local"]
    return roots


def _candidates_for_root(root_dir: str) -> list[BridgeTarget]:
    system = platform.system()
    if system == "Darwin":
        return _macos_candidates(root_dir)
    if system == "Windows":
        return _windows_candidates(root_dir)
    return _linux_candidates(root_dir)


def _candidate_targets() -> list[BridgeTarget]:
    candidates: list[BridgeTarget] = []
    roots = candidate_install_roots()
    if platform.system() == "Windows":
        # Keep an explicit override first, while making automatic results deterministic even if a
        # caller or filesystem supplies roots in an arbitrary order.
        override = os.environ.get("QGIS_PREFIX_PATH") or os.environ.get("QGIS_INSTALL_PATH")
        explicit = [root for root in roots if override and root == override]
        automatic = [root for root in roots if root not in explicit]

        def sort_key(root: str) -> tuple[int, int, int, int, str]:
            version = _windows_install_version(Path(root))
            if version is not None and version[:2] >= MIN_SUPPORTED_QGIS_VERSION:
                return (0, -version[0], -version[1], -version[2], str(Path(root).absolute()).casefold())
            return (1, 0, 0, 0, str(Path(root).absolute()).casefold())

        roots = explicit + sorted(automatic, key=sort_key)
    for root in roots:
        candidates += _candidates_for_root(root)
    return candidates


def _probe_target(target: BridgeTarget) -> tuple[bool, str | None]:
    """Runs a minimal `import qgis.core` inside `target`. Never raises."""
    with tempfile.TemporaryDirectory(prefix="qpb-probe-") as tmp_dir:
        # A bare `import qgis.core` has not been observed to write anything into the cwd on its
        # own (unlike the job-dispatch path in `run_job`, which does — see `_BOOTSTRAP_TEMPLATE`),
        # but an isolated profile directory is supplied here too, defensively and at negligible
        # cost, tied to this call's own already-managed `tmp_dir` (cleaned up automatically when
        # this `with` block exits). Pre-created on disk (not just a string path) so it is a real
        # directory a caller could `.resolve()` against if this ever needed to be checked; this
        # probe itself never constructs a `QgsApplication`, so no isolation check applies here.
        profile_dir_path = Path(tmp_dir) / "qgis-profile"
        profile_dir_path.mkdir(parents=True, exist_ok=False)
        profile_dir = str(profile_dir_path)
        if target.kind == "python_interpreter":
            cmd = [target.executable, "-c", _IMPORT_PROBE_SCRIPT]
        elif platform.system() != "Windows":
            script_path = Path(tmp_dir) / "probe.py"
            script_path.write_text(_IMPORT_PROBE_SCRIPT_EXIT, encoding="utf-8")
            cmd = [target.executable, "--nologo", "--code", str(script_path)]
        else:
            # A Windows GUI target is never a valid fallback for this bridge.
            return False, None
        try:
            proc = subprocess.run(
                cmd,
                env=_merged_env(target.env, profile_dir=profile_dir),
                capture_output=True,
                text=True,
                timeout=_PROBE_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, None
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("QPB_BRIDGE_IMPORT_OK:"):
                return True, line[len("QPB_BRIDGE_IMPORT_OK:") :].strip() or None
        return False, None


_bridge_cache: dict = {"probed": False, "target": None}


def get_bridge_target(force_reprobe: bool = False) -> BridgeTarget | None:
    """The first working way to reach a real QGIS install's own PyQGIS, cached per-process.

    Caching avoids re-spawning a probe subprocess on every call (this is looked up from
    `runtime.check_runtime()`, which acceptance tests call once per `qgis`-marked test).
    """
    if force_reprobe or not _bridge_cache["probed"]:
        found: BridgeTarget | None = None
        for candidate in _candidate_targets():
            ok, version = _probe_target(candidate)
            if ok and is_supported_qgis_version(version):
                found = replace(candidate, qgis_version=version)
                break
        _bridge_cache["target"] = found
        _bridge_cache["probed"] = True
    return _bridge_cache["target"]


def get_bridge_target_for_path(root_dir: str) -> BridgeTarget | None:
    """Probes a single, caller-supplied candidate QGIS install root directly (FR-QPB-008's manual
    install-path override), using the exact same real, subprocess-based verification
    :func:`get_bridge_target` uses for its own standard per-OS candidate roots -- never a
    "plausible directory exists" check alone. `available=True` for a manual path must only ever
    be reported once this same kind of real PyQGIS-import confirmation has actually happened.

    Deliberately **not cached** (unlike :func:`get_bridge_target`'s per-process cache): a manually
    supplied path is a one-off, user-directed override a caller consults only after automatic
    detection has already failed, not a per-process default worth remembering here. Any
    session-local "remember the last working manual path" behavior is the caller's own concern
    (e.g. the wizard UI), not this module's.

    Safe to call with a nonexistent or non-QGIS `root_dir`: `_candidates_for_root` simply reports
    no candidates for a path that doesn't look like a QGIS install of any recognized shape, and
    this function returns `None` -- never raises.
    """
    for candidate in _candidates_for_root(root_dir):
        ok, version = _probe_target(candidate)
        if ok and is_supported_qgis_version(version):
            return replace(candidate, qgis_version=version)
    return None


def any_plausible_install_dir_exists() -> bool:
    """True if a QGIS-shaped install directory exists, even if no working bridge was found."""
    for root in candidate_install_roots():
        if Path(root).exists():
            return True
    return False


def run_job(
    module: str, func: str, kwargs: dict, timeout: float = DEFAULT_JOB_TIMEOUT_SECONDS
) -> dict | None:
    """Runs `module.func(**kwargs)` inside a real QGIS install's own PyQGIS environment.

    Returns `None` if no working QGIS bridge exists on this machine at all (signalling the
    caller to take whatever "no PyQGIS available" path it would otherwise take). Otherwise
    always returns a structured `{"ok": bool, ...}` dict describing the *job's* outcome — a
    worker crash/timeout is reported the same way a normal exception from `func` itself is,
    never left to hang or raise into the caller (E-QPB-015).
    """
    target = get_bridge_target()
    if target is None:
        return None

    with tempfile.TemporaryDirectory(prefix="qpb-bridge-job-") as tmp_dir:
        job_file = str(Path(tmp_dir) / "job.json")
        result_file = str(Path(tmp_dir) / "result.json")
        script_file = str(Path(tmp_dir) / "bootstrap.py")
        # Pre-created on disk and pre-supplied to the subprocess's own starting environment
        # (before its interpreter even starts), so the child never even momentarily inherits a
        # stale value (see `_merged_env`'s docstring). `ensure_qgis_application` (called
        # unconditionally by `_BOOTSTRAP_TEMPLATE` before the dispatched job runs) then creates
        # its *own* fresh directory anyway via `_ensure_isolated_profile_env` — this one is a
        # defense-in-depth starting value, not something the child is expected to trust as-is.
        # This directory's lifetime is tied to this `with` block, so it is removed automatically
        # once this subprocess has exited and this function is about to return.
        profile_dir_path = Path(tmp_dir) / "qgis-profile"
        profile_dir_path.mkdir(parents=True, exist_ok=False)
        profile_dir = str(profile_dir_path)

        with open(job_file, "w", encoding="utf-8") as f:
            json.dump({"module": module, "func": func, "kwargs": kwargs}, f)

        script = _BOOTSTRAP_TEMPLATE.format(
            repo_root=_REPO_ROOT, job_file=job_file, result_file=result_file
        )
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        if target.kind == "python_interpreter":
            cmd = [target.executable, script_file]
        else:
            cmd = [target.executable, "--nologo", "--code", script_file]

        try:
            subprocess.run(
                cmd,
                env=_merged_env(target.env, profile_dir=profile_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": "QGIS 작업 프로세스가 제한 시간 내에 응답하지 않았습니다.",
                "traceback": None,
            }
        except OSError as exc:
            return {
                "ok": False,
                "error": "QGIS 작업 프로세스를 실행할 수 없습니다.",
                "traceback": str(exc),
            }

        if not os.path.exists(result_file):
            return {
                "ok": False,
                "error": "QGIS 작업 프로세스가 결과를 생성하지 못한 채 종료되었습니다.",
                "traceback": None,
            }
        try:
            with open(result_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "error": "QGIS 작업 프로세스의 결과를 읽을 수 없습니다.",
                "traceback": str(exc),
            }


_AD_HOC_BOOTSTRAP_TEMPLATE = """\
import contextlib
import io
import json
import sys
import traceback

sys.path.insert(0, {repo_root!r})

user_script_file = {user_script_file!r}
result_file = {result_file!r}

_stdout = io.StringIO()
_stderr = io.StringIO()
_payload = {{"ok": False, "settings_dir": None, "stdout": "", "stderr": "", "error": None}}
try:
    from qfield_builder.qgis_bridge import ensure_qgis_application
    from qgis.core import QgsApplication

    ensure_qgis_application()
    _payload["settings_dir"] = QgsApplication.qgisSettingsDirPath()

    with open(user_script_file, "r", encoding="utf-8") as _f:
        _user_code = _f.read()
    with contextlib.redirect_stdout(_stdout), contextlib.redirect_stderr(_stderr):
        exec(compile(_user_code, user_script_file, "exec"), {{"__name__": "__qpb_probe__"}})
    _payload["ok"] = True
except Exception as _exc:  # noqa: BLE001 - always report a structured result, never hang.
    _payload["error"] = f"{{type(_exc).__name__}}: {{_exc}}"
    _payload["traceback"] = traceback.format_exc()
finally:
    _payload["stdout"] = _stdout.getvalue()
    _payload["stderr"] = _stderr.getvalue()

import os

try:
    with open(result_file, "w", encoding="utf-8") as _f:
        json.dump(_payload, _f)
finally:
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - best-effort flush only.
        pass
    os._exit(0)
"""


def run_ad_hoc_script(
    script_path: str, timeout: float = DEFAULT_JOB_TIMEOUT_SECONDS
) -> dict | None:
    """Runs an arbitrary, human/agent-authored diagnostic script inside a real QGIS install's own
    PyQGIS environment, under the exact same profile-isolation guarantees as `run_job`.

    This exists as the **one sanctioned entry point** for ad hoc PyQGIS diagnostics (used by
    `scripts/qgis_isolated_probe.py`), specifically so that nobody — human or agent — ever needs
    to hand-construct a `QgsApplication` or invoke a QGIS binary directly outside this module. It
    always goes through `ensure_qgis_application()` first (which fails closed via
    `_assert_settings_dir_is_sandboxed` if isolation cannot be confirmed), and reports the
    resolved settings directory back to the caller for auditability, regardless of outcome.

    Returns `None` if no working QGIS bridge exists on this machine at all. Otherwise always
    returns a structured dict: `{"ok": bool, "settings_dir": str | None, "stdout": str,
    "stderr": str, "error": str | None, "traceback": str | None}`. `ok` is `False` both for a
    script that raised (including a raised `QgisProfileIsolationError`) and for a worker
    crash/timeout — the caller should always check `error`/`traceback` for detail, and should
    treat a missing/non-sandboxed `settings_dir` as suspicious even if `ok` is `True`.
    """
    target = get_bridge_target()
    if target is None:
        return None

    with tempfile.TemporaryDirectory(prefix="qpb-bridge-adhoc-") as tmp_dir:
        result_file = str(Path(tmp_dir) / "result.json")
        script_file = str(Path(tmp_dir) / "bootstrap.py")
        # Pre-created on disk, and always overridden into the child's starting env by
        # `_merged_env` (never inherited) — see `run_job`'s identical comment for why this
        # matters even though `ensure_qgis_application` also creates its own fresh directory.
        profile_dir_path = Path(tmp_dir) / "qgis-profile"
        profile_dir_path.mkdir(parents=True, exist_ok=False)
        profile_dir = str(profile_dir_path)

        script = _AD_HOC_BOOTSTRAP_TEMPLATE.format(
            repo_root=_REPO_ROOT, user_script_file=str(Path(script_path).resolve()),
            result_file=result_file,
        )
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        if target.kind == "python_interpreter":
            cmd = [target.executable, script_file]
        else:
            cmd = [target.executable, "--nologo", "--code", script_file]

        try:
            subprocess.run(
                cmd,
                env=_merged_env(target.env, profile_dir=profile_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "settings_dir": None, "stdout": "", "stderr": "",
                    "error": "The QGIS diagnostic process did not respond in time."}
        except OSError as exc:
            return {"ok": False, "settings_dir": None, "stdout": "", "stderr": "",
                    "error": f"Failed to launch the QGIS diagnostic process: {exc}"}

        if not os.path.exists(result_file):
            return {"ok": False, "settings_dir": None, "stdout": "", "stderr": "",
                    "error": "The QGIS diagnostic process exited without producing a result."}
        try:
            with open(result_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return {"ok": False, "settings_dir": None, "stdout": "", "stderr": "",
                    "error": f"Could not read the QGIS diagnostic process result: {exc}"}
