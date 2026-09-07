"""The shared build must prepare fresh inputs before invoking PyInstaller."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def builder(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    spec = importlib.util.spec_from_file_location("build_app", ROOT / "packaging/build_app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / "copied repo 한글"
    root.mkdir()
    monkeypatch.setattr(module, "REPO_ROOT", root)
    canonical = root / "canonical.xlsx"
    canonical.write_bytes(b"test workbook")
    rasters = root / "rasters"
    rasters.mkdir()
    monkeypatch.setenv("QPB_CANONICAL_REFERENCE_SOURCE", str(canonical))
    monkeypatch.setenv("QPB_REFERENCE_RASTER_DIR", str(rasters))
    monkeypatch.setenv("QPB_FILTERED_REFERENCE_ROOT", "old copied cache")
    return module


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_build_prepares_validates_packages_and_checks_output(builder, monkeypatch, platform):
    monkeypatch.setattr(builder, "sys", SimpleNamespace(
        executable=sys.executable, platform=platform,
    ))
    events = []
    references = []

    def validate(root):
        events.append("validate")
        references.append(root)

    def run(command, **kwargs):
        assert kwargs["check"] is True
        assert kwargs["cwd"] == builder.REPO_ROOT
        if "--destination" in command:
            events.append("prepare")
            assert command[0] == sys.executable
            reference = Path(command[command.index("--destination") + 1])
            assert reference.parent.is_dir()
            assert not reference.exists()
        elif "PyInstaller" in command:
            events.append("package")
            assert command[0] == sys.executable
            assert "--clean" in command
            assert kwargs["env"]["QPB_FILTERED_REFERENCE_ROOT"] == str(references[0])
            assert Path(command[command.index("--workpath") + 1]).parent == references[0].parent
        else:
            events.append("runtime")
            assert command[1] == "--check-runtime"
            assert command[0].endswith(".exe") == (platform == "win32")
            assert (".app/Contents/MacOS/" in command[0]) == (platform == "darwin")

    monkeypatch.setattr(builder, "validate_prepared_reference", validate)
    monkeypatch.setattr(builder.subprocess, "run", run)
    assert builder.main() == 0
    assert events == ["prepare", "validate", "package", "validate", "runtime"]
    assert not references[0].parent.exists()
    assert references[1].is_relative_to(builder.REPO_ROOT / "dist")


@pytest.mark.parametrize("failure", ["missing_sources", "prepare", "validate"])
def test_bad_sources_or_cache_never_start_packaging(builder, monkeypatch, failure):
    previous = builder.REPO_ROOT / "dist" / "previous-app"
    previous.parent.mkdir()
    previous.write_bytes(b"keep previous build")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert "PyInstaller" not in command
        if failure == "prepare":
            raise subprocess.CalledProcessError(1, command)

    def validate(root):
        raise ValueError("invalid cache")

    monkeypatch.setattr(builder.subprocess, "run", run)
    monkeypatch.setattr(builder, "validate_prepared_reference", validate)
    if failure == "missing_sources":
        monkeypatch.setenv("QPB_REFERENCE_RASTER_DIR", str(builder.REPO_ROOT / "missing"))
    with pytest.raises((SystemExit, ValueError, subprocess.CalledProcessError)):
        builder.main()
    assert len(calls) == (0 if failure == "missing_sources" else 1)
    assert previous.read_bytes() == b"keep previous build"
    assert not list(builder.REPO_ROOT.glob("build/fieldbuild-*"))


def test_spec_refuses_an_unprepared_direct_build(monkeypatch):
    monkeypatch.delenv("QPB_FILTERED_REFERENCE_ROOT", raising=False)
    spec = ROOT / "packaging/qfield_builder.spec"
    prefix = spec.read_text(encoding="utf-8").split("gis_datas, gis_binaries, gis_imports =")[0]
    with pytest.raises(SystemExit, match="build_app.py"):
        exec(compile(prefix, str(spec), "exec"), {"SPECPATH": str(ROOT / "packaging")})
