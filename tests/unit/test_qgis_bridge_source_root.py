"""Regression tests for `qfield_builder.qgis_bridge._bridge_source_root`.

Background: a stakeholder clicking "Build" in a real packaged macOS ``.app`` hit
``No module named 'qfield_builder'`` inside the separate QGIS-Python subprocess `qgis_bridge`
launches. Root cause: `qgis_bridge`'s old `_REPO_ROOT = Path(__file__).resolve().parent.parent`
only resolves to a genuine, importable `qfield_builder` package directory when running from an
unpacked source checkout -- once PyInstaller packages this application's own modules into its own
`PYZ` archive format, that same `__file__`-relative arithmetic points at a path with no real,
loose `.py`-file `qfield_builder/` package for the foreign QGIS-owned interpreter to import.

These tests exercise `_bridge_source_root()`'s branching directly (no real QGIS/PyQGIS
installation needed), mirroring how `tests/unit/test_resource_paths.py` already tests the
equivalent `sys.frozen`/`sys._MEIPASS` branching in `qfield_builder.resource_paths` (the
established convention this fix reuses rather than inventing a new one).
"""
from __future__ import annotations

from pathlib import Path

from qfield_builder import qgis_bridge


def test_bridge_source_root_is_the_real_repo_root_when_not_frozen(monkeypatch):
    """Unfrozen (source checkout, pytest, `python -m`, console-script entry point): must resolve
    to the real repo root, which already contains a genuine, loose-`.py`-file `qfield_builder/`
    package directory -- this must keep working exactly as before this fix, since the whole
    existing test suite (and acceptance tests) depend on it."""
    monkeypatch.delattr("sys.frozen", raising=False)
    root = qgis_bridge._bridge_source_root()
    assert (Path(root) / "qfield_builder").is_dir()
    assert (Path(root) / "qfield_builder" / "qgis_bridge.py").is_file()


def test_bridge_source_root_ignores_frozen_flag_without_meipass(monkeypatch):
    """`sys.frozen` alone, without `sys._MEIPASS` ever having been set, must not be trusted --
    only a genuine PyInstaller extraction root is -- mirroring
    `resource_paths.repo_or_bundle_root`'s identical guard."""
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.delattr("sys._MEIPASS", raising=False)
    root = qgis_bridge._bridge_source_root()
    assert (Path(root) / "qfield_builder").is_dir()


def test_bridge_source_root_uses_bundled_data_copy_when_frozen(monkeypatch, tmp_path):
    """When frozen, must resolve to `<meipass>/qfield_builder_src` -- the predictable location
    `packaging/qfield_builder.spec` bundles a real, loose-`.py`-file copy of `qfield_builder` at
    (as plain PyInstaller `datas`, not relying on its own opaque `PYZ` code archive) -- *not*
    `<meipass>` itself (which has no `qfield_builder/` package directory of its own; only
    `qfield_builder_src/qfield_builder/` does)."""
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    root = qgis_bridge._bridge_source_root()
    assert root == str(tmp_path / "qfield_builder_src")


def test_bridge_source_root_frozen_result_is_genuinely_importable(monkeypatch, tmp_path):
    """End-to-end sanity check of the frozen branch: given a bundled data copy laid out exactly
    the way `packaging/qfield_builder.spec` lays it out (`<meipass>/qfield_builder_src/
    qfield_builder/...`), the path `_bridge_source_root()` returns, once inserted onto `sys.path`,
    must make `import qfield_builder` succeed and resolve to *that* bundled copy -- exactly what
    the separate QGIS-Python subprocess's bootstrap script needs (see `_BOOTSTRAP_TEMPLATE`'s
    `sys.path.insert(0, {repo_root!r})`)."""
    import subprocess
    import sys as sys_module

    bundled_pkg_dir = tmp_path / "qfield_builder_src" / "qfield_builder"
    bundled_pkg_dir.mkdir(parents=True)
    (bundled_pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (bundled_pkg_dir / "qgis_bridge.py").write_text("MARKER = 'bundled-copy'\n", encoding="utf-8")

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    root = qgis_bridge._bridge_source_root()

    proc = subprocess.run(
        [
            sys_module.executable,
            "-c",
            f"import sys; sys.path.insert(0, {root!r}); import qfield_builder.qgis_bridge as m; "
            "print(m.MARKER)",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "bundled-copy"


def test_module_level_repo_root_matches_unfrozen_default():
    """`qgis_bridge._REPO_ROOT` (computed once at import time) must equal the real repo root in
    this (unfrozen) test process -- the same value the old, pre-fix `_REPO_ROOT` computed, so
    nothing regresses for the normal from-source case."""
    assert (Path(qgis_bridge._REPO_ROOT) / "qfield_builder").is_dir()
