"""Packaging works in a fresh checkout without any private reference inputs."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_package_without_storage_or_source_overrides(tmp_path, monkeypatch, platform):
    spec = importlib.util.spec_from_file_location("build_app", ROOT / "packaging/build_app.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        builder,
        "sys",
        SimpleNamespace(
            executable=sys.executable,
            platform=platform,
        ),
    )
    for name in (
        "QPB_FILTERED_REFERENCE_ROOT",
        "QPB_CANONICAL_REFERENCE_SOURCE",
        "QPB_REFERENCE_RASTER_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    calls = []

    def run(command, **kwargs):
        assert kwargs["check"] and kwargs["cwd"] == tmp_path
        calls.append(command)
        if "PyInstaller" in command:
            assert "--clean" in command
            assert Path(kwargs["env"]["PYINSTALLER_CONFIG_DIR"]).parent.is_dir()
            assert Path(command[command.index("--workpath") + 1]).parent.is_dir()
        else:
            assert command[1] == "--check-runtime"
            assert command[0].endswith(".exe") == (platform == "win32")
            assert (".app/Contents/MacOS/" in command[0]) == (platform == "darwin")

    monkeypatch.setattr(builder.subprocess, "run", run)
    assert builder.main() == 0
    assert len(calls) == 2
    assert not list(tmp_path.glob("build/fieldbuild-*"))
    assert not (tmp_path / "storage").exists()
