"""Regression test for the QGIS profile/config isolation fix in `qfield_builder.qgis_bridge`.

Background (a reviewer-confirmed defect from a prior implementation round): every call through
`qfield_builder.acceptance_api.build_project()` (and `check_runtime()`) used to leave an ~86 KB
real QGIS style-library SQLite file (`symbology-style.db`) in the process's current working
directory. Root cause: `QgsApplication`/`initQgis()` was constructed with no isolated
`QGIS_CUSTOM_CONFIG_PATH` (or equivalent profile directory) established beforehand, so a real QGIS
install fell back to writing profile-scoped files (the style DB, `QGIS.ini`, etc.) relative to
whatever directory the process happened to be launched from.

Confirmed empirically (against a real, locally installed QGIS 3.44.12) while diagnosing this:

- A bare `import qgis.core` alone does not write anything into the cwd.
- Setting `QGIS_CUSTOM_CONFIG_PATH` *without* ever constructing a `QgsApplication` does **not**
  prevent the stray write either — QGIS logs "Application path not initialized" to stderr and
  silently ignores the env var in that case. This is exactly why
  `qfield_builder.qgis_worker._build_qgis_project_pyqgis` (which deliberately never constructs a
  `QgsApplication` itself) used to reproduce the defect: nothing in its own call chain ever
  constructed one at all, so `QgsSymbol.defaultSymbol` (used by its own community-layer
  symbology) fell back to a bare relative `symbology-style.db` path.
- Constructing `QgsApplication` + calling `initQgis()` *with* `QGIS_CUSTOM_CONFIG_PATH` already
  set, before anything else touches `qgis.core`, is what actually works.

These tests are skipped entirely on any machine with no real, bridgeable QGIS Desktop
installation (mirroring `tests/unit/test_worker_process.py`'s existing gating pattern) — the
defect (and its fix) can only be genuinely exercised against a real PyQGIS runtime, not a stub.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from qfield_builder import qgis_bridge
from qfield_builder.acceptance_api import build_project, check_runtime

_BRIDGE_TARGET = qgis_bridge.get_bridge_target()

pytestmark = pytest.mark.skipif(
    _BRIDGE_TARGET is None,
    reason="requires a real, bridgeable QGIS Desktop installation",
)

# DR-QPB-008: sites/communities are MULTIPOLYGON geometry.
_SAMPLE_SITE_POLYGON_WKT = (
    "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
)


def _vegetation_mapping_config() -> dict:
    """A minimal, valid `build_project()` config for `survey_type="vegetation_mapping"`.

    Deliberately chosen (over e.g. `simple_inventory`) because it has a `community` layer, which
    `qfield_builder.qgis_worker._apply_community_symbology` gives a rule-based renderer built from
    `QgsSymbol.defaultSymbol(...)` — exactly the call that, pre-fix, lazily triggered QGIS's
    default-style machinery with no `QgsApplication` ever constructed on that code path, causing
    the stray `symbology-style.db` write into the invoking cwd.
    """
    return {
        "project_display_name": "Profile Isolation Regression Test",
        "description": "qgis_bridge profile isolation regression fixture",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": "vegetation_mapping",
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "sites": [{"site_name": "Site A", "geom_wkt": _SAMPLE_SITE_POLYGON_WKT}],
    }


def test_build_project_from_clean_cwd_leaves_no_qgis_artifacts_in_cwd(tmp_path, monkeypatch):
    """The exact reviewer-reported repro, end to end: `build_project()`, launched from a clean,
    empty cwd, must not leave `symbology-style.db` (or anything else) in that cwd — while still
    genuinely succeeding at building a real project (this must not merely hide the side effect by
    silently breaking the actual functionality)."""
    clean_cwd = tmp_path / "clean_cwd"
    clean_cwd.mkdir()
    output_dir = tmp_path / "output"  # deliberately outside clean_cwd
    monkeypatch.chdir(clean_cwd)

    runtime_info = check_runtime()
    assert runtime_info["available"] is True, runtime_info["message"]

    result = build_project(_vegetation_mapping_config(), str(output_dir))

    # Real functionality must remain intact.
    assert result["success"] is True, result.get("error_message")
    assert result["cancelled"] is False
    assert result["qgs_path"] and os.path.isfile(result["qgs_path"])
    assert result["gpkg_path"] and os.path.isfile(result["gpkg_path"])

    # The actual regression check: nothing was written directly into the invoking cwd.
    cwd_contents = set(os.listdir(clean_cwd))
    assert cwd_contents == set(), (
        f"QGIS wrote unexpected file(s)/directory(ies) directly into the invoking cwd: "
        f"{cwd_contents}"
    )


def test_check_runtime_from_clean_cwd_leaves_no_qgis_artifacts_in_cwd(tmp_path, monkeypatch):
    """`check_runtime()` (which probes for a working bridge via a genuinely separate PyQGIS
    subprocess) must not leave any file behind in the invoking cwd either."""
    clean_cwd = tmp_path / "clean_cwd_check_runtime"
    clean_cwd.mkdir()
    monkeypatch.chdir(clean_cwd)

    # Forces a fresh probe subprocess (rather than reusing this test session's already-cached
    # bridge target) so the probe itself genuinely runs from this clean cwd.
    qgis_bridge.get_bridge_target(force_reprobe=True)

    info = check_runtime()
    assert info["available"] is True, info["message"]
    assert set(os.listdir(clean_cwd)) == set()


def _run_isolated_script_in_bridge_target(script: str, cwd: Path, timeout: float = 60.0):
    """Runs `script` directly inside the detected bridge target's own Python/PyQGIS environment,
    from `cwd`, *without* pre-supplying an isolated `QGIS_CUSTOM_CONFIG_PATH` the way `run_job`
    does — this is what lets this module's own `ensure_qgis_application` (rather than `run_job`'s
    own profile-directory bookkeeping) be the thing under test. Mirrors the same
    `python_interpreter` vs. `gui_code` branching `qgis_bridge._probe_target`/`run_job` use."""
    target = _BRIDGE_TARGET
    assert target is not None
    env = dict(os.environ)
    env.update(target.env)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Deliberately does NOT set QGIS_CUSTOM_CONFIG_PATH here: this exercises
    # `ensure_qgis_application`'s own from-scratch isolation fallback
    # (`_ensure_isolated_profile_env`), not a directory pre-supplied by a caller such as `run_job`.
    env.pop("QGIS_CUSTOM_CONFIG_PATH", None)

    if target.kind == "python_interpreter":
        cmd = [target.executable, "-c", script]
    else:
        script_path = cwd / "_qpb_profile_isolation_script.py"
        script_path.write_text(script, encoding="utf-8")
        cmd = [target.executable, "--nologo", "--code", str(script_path)]

    return subprocess.run(
        cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout
    )


_ENSURE_QGIS_APPLICATION_SCRIPT = """\
import sys
sys.path.insert(0, {repo_root!r})
from qfield_builder.qgis_bridge import ensure_qgis_application
from qgis.core import QgsApplication, QgsSymbol, QgsWkbTypes

ensure_qgis_application()
# A real PyQGIS call that lazily touches QGIS's default style/symbol machinery -- exactly what,
# pre-fix, fell back to writing a stray `symbology-style.db` relative to the cwd whenever nothing
# had already constructed a `QgsApplication`.
symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PolygonGeometry)
assert symbol is not None
print("QPB_ENSURE_QGIS_APPLICATION_OK")
print("QPB_SETTINGS_DIR:" + QgsApplication.qgisSettingsDirPath())
sys.stdout.flush()
sys.stderr.flush()
import os
os._exit(0)
"""


def test_ensure_qgis_application_direct_construction_leaves_no_qgis_artifacts_in_cwd(tmp_path):
    """Exercises the *in-process* code path (`qfield_builder.qgis_bridge.ensure_qgis_application`)
    directly and in isolation from `run_job`'s own profile-directory bookkeeping: run a small
    script, from a clean cwd, that does nothing but call `ensure_qgis_application()` and then a
    real PyQGIS default-style lookup. Must not leave anything in that cwd, and must genuinely
    succeed (proving `ensure_qgis_application`'s own isolation logic — not just `run_job`'s — is
    what prevents the stray write).

    Also asserts `ensure_qgis_application` actually used a fresh, isolated *temp* profile
    directory (`QgsApplication.qgisSettingsDirPath()` resolving under the OS temp directory,
    with this module's own `qpb-qgis-profile-` prefix) rather than merely "not the cwd": confirmed
    empirically while diagnosing this fix that `ensure_qgis_application`'s pre-fix behavior — it
    already constructed a real `QgsApplication`, just without ever setting
    `QGIS_CUSTOM_CONFIG_PATH` first — never actually wrote into the cwd either (only
    `qfield_builder.qgis_worker._build_qgis_project_pyqgis`'s "never construct a `QgsApplication`
    at all" case did that); instead it silently wrote into an *uncontrolled, persistent* OS
    per-user profile directory outside this application's own temp/app-owned locations
    (`~/Library/Application Support/QGIS/profiles/default/` on macOS, distinct from — and outside
    the control of — this fix's isolated per-run directory). Asserting the *isolated* location is
    what makes this assertion a genuine pre/post-fix differentiator rather than a tautology; see
    the completion report for the exact pre-fix/post-fix comparison run to confirm this.
    """
    clean_cwd = tmp_path / "clean_cwd_ensure_qgis_application"
    clean_cwd.mkdir()
    script = _ENSURE_QGIS_APPLICATION_SCRIPT.format(repo_root=qgis_bridge._REPO_ROOT)

    proc = _run_isolated_script_in_bridge_target(script, clean_cwd)

    assert "QPB_ENSURE_QGIS_APPLICATION_OK" in proc.stdout, (
        f"script failed to run genuine PyQGIS init; stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    cwd_contents = set(os.listdir(clean_cwd))
    assert cwd_contents == set(), (
        f"ensure_qgis_application() left unexpected file(s)/directory(ies) in the invoking cwd: "
        f"{cwd_contents}"
    )

    settings_dir_line = next(
        (line for line in proc.stdout.splitlines() if line.startswith("QPB_SETTINGS_DIR:")), None
    )
    assert settings_dir_line is not None, f"missing settings dir marker; stdout={proc.stdout!r}"
    settings_dir = settings_dir_line[len("QPB_SETTINGS_DIR:") :].strip()
    assert "qpb-qgis-profile-" in settings_dir, (
        "ensure_qgis_application() did not use an isolated, app-owned temp profile directory "
        f"(settings dir was {settings_dir!r}) -- it must never fall back to an uncontrolled, "
        "persistent OS-default profile location any more than it may write into the cwd."
    )
