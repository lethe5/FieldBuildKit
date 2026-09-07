"""Unit tests for qfield_builder.resource_paths.

Covers the packaging-related defect this round fixes: an `__file__`-relative resource path
(the previous approach in `qfield_builder.vworld`) silently stops resolving to the real, bundled
`resources/` directory once PyInstaller packages this application (see
`packaging/qfield_builder.spec`), because `__file__` then points into PyInstaller's own archive
format rather than a real directory on disk. `qfield_builder.resource_paths` fixes this by
consulting `sys.frozen`/`sys._MEIPASS` (the convention PyInstaller sets on every platform it
packages for) instead.
"""
from __future__ import annotations

from pathlib import Path

from qfield_builder import resource_paths


def test_repo_or_bundle_root_is_the_real_repo_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr("sys.frozen", raising=False)
    root = resource_paths.repo_or_bundle_root()
    assert (root / "qfield_builder").is_dir()
    assert (root / "resources").is_dir()


def test_repo_or_bundle_root_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    assert resource_paths.repo_or_bundle_root() == tmp_path


def test_repo_or_bundle_root_ignores_frozen_flag_without_meipass(monkeypatch):
    # `sys.frozen` alone, without `sys._MEIPASS` ever having been set, must not be trusted --
    # only the actual PyInstaller-set extraction root is.
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.delattr("sys._MEIPASS", raising=False)
    root = resource_paths.repo_or_bundle_root()
    assert (root / "qfield_builder").is_dir()


def test_repo_or_bundle_root_uses_bundle_parent_for_bridge_source_layout(monkeypatch, tmp_path):
    """The QGIS bridge imports its loose package copy from ``<bundle>/qfield_builder_src``."""
    bundle_root = tmp_path / "FieldBuild Standalone.app" / "Contents" / "MacOS"
    source_package = bundle_root / "qfield_builder_src" / "qfield_builder"
    source_package.mkdir(parents=True)
    (bundle_root / "resources" / "vendor").mkdir(parents=True)
    (bundle_root / "resources" / "vendor" / "d3.v7.9.0.min.js").write_text(
        "bundled d3", encoding="utf-8"
    )
    resource_module = source_package / "resource_paths.py"
    resource_module.write_text("", encoding="utf-8")

    monkeypatch.delattr("sys.frozen", raising=False)
    monkeypatch.setattr(resource_paths, "__file__", str(resource_module))

    assert resource_paths.repo_or_bundle_root() == bundle_root
    assert resource_paths.resource_path("vendor", "d3.v7.9.0.min.js").read_text(
        encoding="utf-8"
    ) == "bundled d3"


def test_resource_path_joins_repo_or_bundle_root_and_resources():
    path = resource_paths.resource_path("config", "vworld_layers.json")
    expected = resource_paths.repo_or_bundle_root() / "resources" / "config" / "vworld_layers.json"
    assert path == expected
    assert path.is_file()


def test_resource_path_under_frozen_root(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    (tmp_path / "resources" / "config").mkdir(parents=True)
    (tmp_path / "resources" / "config" / "vworld_layers.json").write_text("{}", encoding="utf-8")

    path = resource_paths.resource_path("config", "vworld_layers.json")
    assert path == Path(tmp_path) / "resources" / "config" / "vworld_layers.json"
    assert path.is_file()


def test_reference_path_uses_bundle_root_storage_boundary():
    expected = resource_paths.repo_or_bundle_root() / "storage" / "reference" / "tables"
    assert resource_paths.reference_path("tables") == expected
    assert resource_paths.reference_path("tables", "Rpt_2026-08-29_List.xlsx") == (
        expected / "Rpt_2026-08-29_List.xlsx"
    )


def test_reference_path_under_frozen_root(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    tables = tmp_path / "storage" / "reference" / "tables"
    tables.mkdir(parents=True)
    workbook = tables / "Rpt_2026-08-29_List.xlsx"
    workbook.write_bytes(b"bundle candidate")

    assert resource_paths.reference_path("tables") == tables
    assert resource_paths.reference_path("tables", workbook.name) == workbook
