"""Unit tests for `qfield_builder.qgis_bridge.get_bridge_target_for_path` (FR-QPB-008, Decision
Log D-10) -- the real, subprocess-based verification mechanism `runtime.py`'s manual
QGIS-install-path override reuses.

These are pure-logic tests: `_candidates_for_root`/`_probe_target` are monkeypatched so nothing
here spawns a real subprocess or depends on this machine's actual QGIS installation state (that
end-to-end confirmation is covered separately by the `qgis`-marked acceptance tests in
tests/acceptance/qfield_project_builder/test_qgis_manual_path_override.py).
"""
from __future__ import annotations

import pytest

from qfield_builder import qgis_bridge


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("3.42.9", False),
        ("3.44.0", True),
        ("3.46.1-Solothurn", True),
        ("4.0.0", True),
        (None, False),
    ],
)
def test_qgis_version_support_starts_at_344(version, expected):
    assert qgis_bridge.is_supported_qgis_version(version) is expected


def test_get_bridge_target_for_path_returns_none_for_no_candidates(monkeypatch):
    monkeypatch.setattr(qgis_bridge, "_candidates_for_root", lambda _root: [])
    assert qgis_bridge.get_bridge_target_for_path("/some/path") is None


def test_get_bridge_target_for_path_probes_each_candidate_until_one_succeeds(monkeypatch):
    candidate_a = qgis_bridge.BridgeTarget(
        kind="python_interpreter", executable="/a/python3", env={}, install_path="/root"
    )
    candidate_b = qgis_bridge.BridgeTarget(
        kind="python_interpreter", executable="/b/python3", env={}, install_path="/root"
    )
    monkeypatch.setattr(
        qgis_bridge, "_candidates_for_root", lambda _root: [candidate_a, candidate_b]
    )

    probed = []

    def _fake_probe(target):
        probed.append(target.executable)
        if target is candidate_a:
            return False, None
        return True, "3.44.5"

    monkeypatch.setattr(qgis_bridge, "_probe_target", _fake_probe)

    result = qgis_bridge.get_bridge_target_for_path("/root")

    assert probed == ["/a/python3", "/b/python3"]
    assert result is not None
    assert result.executable == "/b/python3"
    assert result.qgis_version == "3.44.5"
    assert result.install_path == "/root"


def test_get_bridge_target_for_path_returns_none_when_no_candidate_probes_ok(monkeypatch):
    candidate = qgis_bridge.BridgeTarget(
        kind="gui_code", executable="/x/QGIS", env={}, install_path="/root"
    )
    monkeypatch.setattr(qgis_bridge, "_candidates_for_root", lambda _root: [candidate])
    monkeypatch.setattr(qgis_bridge, "_probe_target", lambda _target: (False, None))

    assert qgis_bridge.get_bridge_target_for_path("/root") is None


def test_get_bridge_target_for_path_rejects_an_importable_pre_344_runtime(monkeypatch):
    candidate = qgis_bridge.BridgeTarget(
        kind="python_interpreter", executable="/x/python3", env={}, install_path="/root"
    )
    monkeypatch.setattr(qgis_bridge, "_candidates_for_root", lambda _root: [candidate])
    monkeypatch.setattr(qgis_bridge, "_probe_target", lambda _target: (True, "3.42.9"))

    assert qgis_bridge.get_bridge_target_for_path("/root") is None


def test_get_bridge_target_for_path_is_not_cached(monkeypatch):
    """Unlike `get_bridge_target`'s own deliberate per-process cache, a manually supplied path is
    a one-off override that must be re-probed fresh on every call."""
    candidate = qgis_bridge.BridgeTarget(
        kind="python_interpreter", executable="/x/python3", env={}, install_path="/root"
    )
    monkeypatch.setattr(qgis_bridge, "_candidates_for_root", lambda _root: [candidate])

    call_count = {"n": 0}

    def _fake_probe(_target):
        call_count["n"] += 1
        return True, "3.44.1"

    monkeypatch.setattr(qgis_bridge, "_probe_target", _fake_probe)

    qgis_bridge.get_bridge_target_for_path("/root")
    qgis_bridge.get_bridge_target_for_path("/root")

    assert call_count["n"] == 2


def test_get_bridge_target_for_path_handles_nonexistent_directory_without_raising(tmp_path):
    """A real (unmocked) call against a directory that does not exist at all must return `None`
    cleanly -- no candidate is ever produced, so no subprocess is ever spawned."""
    missing = tmp_path / "does_not_exist"
    assert not missing.exists()
    assert qgis_bridge.get_bridge_target_for_path(str(missing)) is None
