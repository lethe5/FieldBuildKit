"""Acceptance coverage for the Windows QGIS dedicated-Python bridge.

The suite deliberately runs on the macOS development host.  It simulates a Windows installation
with a temporary directory tree, forces the bridge's platform branch, and spies on subprocess
launches.  No QGIS binary, Windows registry, shell, or host PATH lookup is used.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from qfield_builder import qgis_bridge, runtime

_CONTROLLED_ENV = (
    "PYTHONHOME",
    "PYTHONPATH",
    "QGIS_PREFIX_PATH",
    "GDAL_DATA",
    "QT_PLUGIN_PATH",
    "PATH",
)


def _windows(monkeypatch):
    monkeypatch.setattr(qgis_bridge.platform, "system", lambda: "Windows")


def _write_executable(path: Path, contents: str = "fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    # Windows ignores this bit, but making the fixture executable keeps the test valid if the
    # implementation uses the existing POSIX-friendly `_executable_file` helper on this host.
    path.chmod(0o755)


def _make_install(
    parent: Path,
    patch: int,
    *,
    minor: int = 44,
    env_text: str | None = None,
    missing: tuple[str, ...] = (),
    escaping_python: bool = False,
) -> Path:
    root = parent / f"QGIS 3.{minor}.{patch}"
    (root / "apps" / "Python312").mkdir(parents=True)
    (root / "apps" / "qgis-ltr" / "python").mkdir(parents=True)
    (root / "apps" / "Qt6" / "plugins").mkdir(parents=True)
    (root / "share" / "gdal").mkdir(parents=True)
    (root / "bin").mkdir(parents=True)

    python_path = root / "apps" / "Python312" / "python.exe"
    if escaping_python:
        outside = parent / "outside-python.exe"
        _write_executable(outside)
        python_path.symlink_to(outside)
    elif "python" not in missing:
        _write_executable(python_path)

    if "env" not in missing:
        if env_text is None:
            env_text = "\n".join(
                (
                    f"set PYTHONHOME={root / 'apps' / 'Python312'}",
                    f"QGIS_PREFIX_PATH={root}",
                    f"GDAL_DATA={root / 'share' / 'gdal'}",
                    f"QT_PLUGIN_PATH={root / 'apps' / 'Qt6' / 'plugins'}",
                    f"PATH={root / 'bin'};%PATH%",
                    f"PYTHONPATH={root / 'apps' / 'qgis-ltr' / 'python'};%PYTHONPATH%",
                )
            )
        (root / "bin" / "qgis-ltr-bin.env").write_text(env_text, encoding="utf-8")

    if "prefix" in missing:
        # Remove the directory only after the rest of the fixture is created so the absence is
        # unambiguous to validators that require the selected prefix to be a directory.
        shutil.rmtree(root / "apps" / "qgis-ltr")
    if "pyqgis" in missing:
        (root / "apps" / "qgis-ltr" / "python").rmdir()
    if "gdal" in missing:
        (root / "share" / "gdal").rmdir()
    if "qt" in missing:
        (root / "apps" / "Qt6" / "plugins").rmdir()
    return root


def _target_for(root: Path) -> qgis_bridge.BridgeTarget:
    """Return the dedicated-Python target from a fixture, failing if discovery is incomplete."""
    targets = qgis_bridge._windows_candidates(str(root))
    python_targets = [target for target in targets if target.kind == "python_interpreter"]
    assert python_targets, f"no dedicated Python target discovered for {root}"
    return python_targets[0]


def _reset_bridge_cache(monkeypatch):
    monkeypatch.setattr(qgis_bridge, "_bridge_cache", {"probed": False, "target": None})


def _fake_completed(stdout: str = ""):
    return type("Completed", (), {"stdout": stdout, "stderr": "", "returncode": 0})()


def _capture_job_launch(monkeypatch, launches: list[tuple[list[str], dict]]):
    def fake_run(cmd, *, env, **kwargs):
        launches.append((list(cmd), dict(env)))
        script = Path(cmd[-1]).read_text(encoding="utf-8")
        result_match = re.search(r"^result_file = (.+)$", script, re.MULTILINE)
        assert result_match, "bridge bootstrap must define a result file"
        result_path = Path(ast.literal_eval(result_match.group(1)))
        result_path.write_text(
            json.dumps({"ok": True, "result": {"bridge": "fixture"}}), encoding="utf-8"
        )
        return _fake_completed()

    monkeypatch.setattr(qgis_bridge.subprocess, "run", fake_run)


def test_ac_wqgis_001_discovers_patch_folders_and_orders_highest_patch_first(
    monkeypatch, tmp_path
):
    """AC-WQGIS-001: discovery accepts patched folders and does not require a bare folder."""
    _windows(monkeypatch)
    program_files = tmp_path / "Program Files"
    high = _make_install(program_files, 13)
    low = _make_install(program_files, 7)
    newer = _make_install(program_files, 1, minor=46)
    (program_files / "QGIS 3.44").mkdir(parents=True)
    for name in ("ProgramFiles", "ProgramW6432"):
        monkeypatch.setenv(name, str(program_files))

    roots = qgis_bridge.candidate_install_roots()
    assert str(high) in roots
    assert str(low) in roots
    assert str(newer) in roots
    assert roots.index(str(newer)) < roots.index(str(high)) < roots.index(str(low))
    assert roots.index(str(low)) < roots.index(str(program_files / "QGIS 3.44"))
    assert not any(Path(root).name == "QGIS 3.44" for root in roots[:2])


def test_ac_wqgis_002_selection_is_deterministic_and_falls_through_after_probe_failure(
    monkeypatch, tmp_path
):
    """AC-WQGIS-002: probe order is numeric/deterministic, not enumeration-order dependent."""
    _windows(monkeypatch)
    program_files = tmp_path / "Program Files"
    high = _make_install(program_files, 13)
    low = _make_install(program_files, 7)

    def run_once(enumerated: list[Path]) -> tuple[list[str], str]:
        _reset_bridge_cache(monkeypatch)
        monkeypatch.setattr(
            qgis_bridge, "candidate_install_roots", lambda: [str(p) for p in enumerated]
        )
        probed: list[str] = []

        def fake_probe(target):
            probed.append(target.install_path)
            return (
                target.install_path == str(low),
                "3.44.7" if target.install_path == str(low) else None,
            )

        monkeypatch.setattr(qgis_bridge, "_probe_target", fake_probe)
        selected = qgis_bridge.get_bridge_target(force_reprobe=True)
        assert selected is not None
        return probed, selected.install_path

    first = run_once([low, high])
    second = run_once([high, low])
    assert first == second == ([str(high), str(low)], str(low))


def test_ac_wqgis_003_uses_absolute_qgis_owned_python_not_host_or_gui(
    monkeypatch, tmp_path
):
    """AC-WQGIS-003: valid Windows installs expose apps/Python312/python.exe as target."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    assert target.kind == "python_interpreter"
    assert Path(target.executable) == (root / "apps" / "Python312" / "python.exe").resolve()
    assert Path(target.executable).is_absolute()
    assert target.executable != os.path.abspath(os.sys.executable)
    assert "qgis.exe" not in target.executable.lower()
    assert "qgis-bin.exe" not in target.executable.lower()


def test_ac_wqgis_004_parses_official_env_as_data_and_filters_unsupported_assignments(
    monkeypatch, tmp_path
):
    """AC-WQGIS-004: set/plain assignments and %NAME% expansion are safe and selective."""
    _windows(monkeypatch)
    root = tmp_path / "QGIS 3.44.13"
    inherited_path = r"C:\Windows\System32;C:\Tools"
    env_text = "\n".join(
        (
            "# comment",
            "@echo off",
            f"set QGIS_ROOT={root}",
            "set PYTHONHOME=%QGIS_ROOT%\\apps\\Python312",
            "QGIS_PREFIX_PATH=%QGIS_ROOT%",
            "PATH=%QGIS_ROOT%\\bin;%PATH%",
            "UNSAFE_SECRET=must-not-reach-child",
            "python.exe --version",
            "",
        )
    )
    root = _make_install(tmp_path, 13, env_text=env_text)
    monkeypatch.setenv("PATH", inherited_path)
    target = _target_for(root)
    effective = qgis_bridge._merged_env(target.env)

    assert effective["PYTHONHOME"].endswith(r"apps\Python312") or effective["PYTHONHOME"].endswith(
        "apps/Python312"
    )
    assert effective["QGIS_PREFIX_PATH"].endswith("QGIS 3.44.13")
    assert "UNSAFE_SECRET" not in effective
    assert "python.exe --version" not in " ".join(effective.values())

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)
        assert kwargs.get("shell", False) is False
        return _fake_completed("QPB_BRIDGE_IMPORT_OK:3.44.13\n")

    monkeypatch.setattr(qgis_bridge.subprocess, "run", fake_run)
    assert qgis_bridge._probe_target(target)[0] is True
    assert calls and all(call.get("shell", False) is False for call in calls)


def test_ac_wqgis_005_probe_and_job_receive_all_canonical_environment_values(
    monkeypatch, tmp_path
):
    """AC-WQGIS-005/006: probe and dispatched job share the validated child environment."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    for name in _CONTROLLED_ENV:
        monkeypatch.setenv(name, f"inherited-conflict-{name}")

    probe_envs: list[dict] = []

    def fake_probe_run(cmd, *, env, **kwargs):
        probe_envs.append(dict(env))
        return _fake_completed("QPB_BRIDGE_IMPORT_OK:3.44.13\n")

    monkeypatch.setattr(qgis_bridge.subprocess, "run", fake_probe_run)
    assert qgis_bridge._probe_target(target)[0]
    assert probe_envs
    effective = probe_envs[0]
    assert all(name in effective for name in _CONTROLLED_ENV)
    assert effective["QGIS_PREFIX_PATH"] == str(root)
    pyqgis = str((root / "apps" / "qgis-ltr" / "python").resolve())
    assert pyqgis in effective["PYTHONPATH"].split(";")
    assert effective["PYTHONHOME"] != "inherited-conflict-PYTHONHOME"
    assert effective["PATH"] != "inherited-conflict-PATH"

    launches: list[tuple[list[str], dict]] = []
    _capture_job_launch(monkeypatch, launches)
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: target)
    result = qgis_bridge.run_job("fixture.module", "fixture_func", {})
    assert result and result["ok"] is True
    assert len(launches) == 1
    assert all(name in launches[0][1] for name in _CONTROLLED_ENV)
    assert launches[0][1]["QGIS_PREFIX_PATH"] == str(root)
    assert pyqgis in launches[0][1]["PYTHONPATH"].split(";")


def test_ac_wqgis_006_removes_windowsapps_and_keeps_qgis_paths_first(
    monkeypatch, tmp_path
):
    """AC-WQGIS-006: child PATH excludes aliases and cannot shadow canonical QGIS Python."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    monkeypatch.setenv(
        "PATH",
        ";".join(
            (
                r"C:\Users\tester\AppData\Local\Microsoft\WindowsApps",
                r"C:\shadow-python",
                str(root / "bin"),
                r"C:\Windows\System32",
            )
        ),
    )
    effective = qgis_bridge._merged_env(target.env)
    entries = effective["PATH"].split(";")
    normalized = [entry.replace("/", "\\").rstrip("\\").lower() for entry in entries]
    assert not any(entry.endswith(r"microsoft\windowsapps") for entry in normalized)
    qgis_entries = [str(root / "bin").replace("/", "\\").lower()]
    assert normalized.index(qgis_entries[0]) == 0
    assert target.executable == str((root / "apps" / "Python312" / "python.exe").resolve())


@pytest.mark.parametrize("invalid", ["missing", "escape", "symlink"])
def test_ac_wqgis_007_rejects_invalid_installations_before_probe(
    monkeypatch, tmp_path, invalid
):
    """AC-WQGIS-007: missing, escaping, and symlinked required paths fail closed."""
    _windows(monkeypatch)
    if invalid == "missing":
        root = _make_install(tmp_path, 13, missing=("python",))
    elif invalid == "symlink":
        root = _make_install(tmp_path, 13, escaping_python=True)
    else:
        root = _make_install(
            tmp_path,
            13,
            env_text="PYTHONHOME=%ROOT%\\..\\outside\\Python312\nQGIS_PREFIX_PATH=%ROOT%",
        )

    monkeypatch.setattr(
        qgis_bridge, "_probe_target", lambda target: pytest.fail("invalid path probed")
    )
    _reset_bridge_cache(monkeypatch)
    monkeypatch.setattr(qgis_bridge, "candidate_install_roots", lambda: [str(root)])
    assert qgis_bridge.get_bridge_target(force_reprobe=True) is None

    source = Path(qgis_bridge.__file__).read_text(encoding="utf-8")
    assert "str(env)" not in source
    assert "repr(env)" not in source


def test_ac_wqgis_008_failed_python_probe_never_launches_a_windows_qgis_gui(
    monkeypatch, tmp_path
):
    """AC-WQGIS-008: import failure is unavailable/fall-through, never GUI validation."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    launches: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        launches.append(list(cmd))
        return _fake_completed("QPB_BRIDGE_IMPORT_FAILED:fixture failure\n")

    monkeypatch.setattr(qgis_bridge.subprocess, "run", fake_run)
    monkeypatch.setattr(qgis_bridge, "_candidate_targets", lambda: [target])
    _reset_bridge_cache(monkeypatch)
    assert qgis_bridge.get_bridge_target(force_reprobe=True) is None
    assert launches
    assert all(
        not any(gui in part.lower() for gui in ("qgis.exe", "qgis-bin.exe", "qgis-ltr-bin.exe"))
        for command in launches
        for part in command
    )
    assert all("--code" not in command for command in launches)


def test_ac_wqgis_009_no_usable_installation_returns_structured_unavailable_result(
    monkeypatch
):
    """AC-WQGIS-009: no candidate is a normal unavailable result, not host-Python fallback."""
    _windows(monkeypatch)
    monkeypatch.setattr(runtime, "_try_import_pyqgis_in_current_process", lambda: (False, None))
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: None)
    monkeypatch.setattr(qgis_bridge, "any_plausible_install_dir_exists", lambda: False)
    info = runtime.detect_qgis_installation()
    assert info.available is False
    assert info.message.strip()
    assert "traceback" not in info.message.lower()
    assert "exception" not in info.message.lower()


def test_ac_wqgis_010_successful_target_is_cached_and_job_reuses_it(
    monkeypatch, tmp_path
):
    """AC-WQGIS-010/011: cached target and job use one dedicated executable/environment."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    probe_count = 0

    def fake_probe(candidate):
        nonlocal probe_count
        probe_count += 1
        return True, "3.44.13"

    monkeypatch.setattr(qgis_bridge, "_candidate_targets", lambda: [target])
    monkeypatch.setattr(qgis_bridge, "_probe_target", fake_probe)
    _reset_bridge_cache(monkeypatch)
    first = qgis_bridge.get_bridge_target(force_reprobe=True)
    second = qgis_bridge.get_bridge_target()
    assert first == second
    assert probe_count == 1

    launches: list[tuple[list[str], dict]] = []
    _capture_job_launch(monkeypatch, launches)
    result = qgis_bridge.run_job("fixture.module", "fixture_func", {})
    assert result and result["ok"] is True
    assert launches[0][0][0] == target.executable
    assert launches[0][1]["QGIS_PREFIX_PATH"] == str(root)


def test_ac_wqgis_011_macos_branch_never_consults_windows_logic(monkeypatch):
    """AC-WQGIS-011: Darwin keeps existing roots/candidates and GUI compatibility fallback."""
    monkeypatch.setattr(qgis_bridge.platform, "system", lambda: "Darwin")
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files\QGIS 3.44.13")
    monkeypatch.setenv("WindowsApps", r"C:\WindowsApps")
    windows_called = False

    def forbidden_windows(*args, **kwargs):
        nonlocal windows_called
        windows_called = True
        pytest.fail("Windows candidate logic was consulted on macOS")

    monkeypatch.setattr(qgis_bridge, "_windows_candidates", forbidden_windows)
    roots = qgis_bridge.candidate_install_roots()
    assert all("Program Files" not in root for root in roots)
    assert all("WindowsApps" not in root for root in roots)
    assert qgis_bridge._candidates_for_root("/not-a-real-macos-qgis.app") == []
    assert windows_called is False

    source = Path(qgis_bridge.__file__).read_text(encoding="utf-8")
    assert 'if system == "Windows"' in source
    assert 'if system == "Darwin"' in source


def test_ac_wqgis_012_discovery_and_job_setup_do_not_mutate_host_environment(
    monkeypatch, tmp_path
):
    """AC-WQGIS-012: all QGIS-specific values are child-only overrides."""
    _windows(monkeypatch)
    root = _make_install(tmp_path, 13)
    target = _target_for(root)
    for name in _CONTROLLED_ENV:
        monkeypatch.setenv(name, f"host-value-{name}")
    before = {name: os.environ.get(name) for name in _CONTROLLED_ENV}

    effective = qgis_bridge._merged_env(target.env)
    assert {name: os.environ.get(name) for name in _CONTROLLED_ENV} == before
    assert effective["QGIS_PREFIX_PATH"] == str(root)
    assert effective["QGIS_PREFIX_PATH"] != before["QGIS_PREFIX_PATH"]

    launches: list[tuple[list[str], dict]] = []
    _capture_job_launch(monkeypatch, launches)
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: target)
    assert qgis_bridge.run_job("fixture.module", "fixture_func", {})["ok"] is True
    assert {name: os.environ.get(name) for name in _CONTROLLED_ENV} == before
