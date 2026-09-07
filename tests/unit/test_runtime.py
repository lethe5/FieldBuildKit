"""Unit tests for qfield_builder.runtime (Section 5.2, E-QPB-002, AC-QPB-029/053, FR-QPB-008)."""
from __future__ import annotations

import pytest

from qfield_builder import qgis_bridge, runtime
from qfield_builder.runtime import check_runtime, detect_qgis_installation


def test_force_missing_is_deterministic_and_non_technical():
    info = check_runtime(force_missing=True)
    assert info["available"] is False
    message = info["message"].lower()
    for jargon in ("traceback", "exception", "stack trace", "nonetype", "errno"):
        assert jargon not in message


def test_check_runtime_return_shape():
    info = check_runtime()
    # FR-QPB-008 (conformance-gap round, 2026-08-27): `qgis_prefix_path` is now always present,
    # not merely on a successful bridge-verified detection.
    assert set(info.keys()) == {"available", "message", "qgis_prefix_path", "backend"}
    assert info["backend"] == "standalone"
    assert isinstance(info["available"], bool)
    assert isinstance(info["message"], str) and info["message"].strip()


def test_check_runtime_without_force_missing_never_raises():
    # Regardless of whether this sandbox happens to have a QGIS installation, this must never
    # raise — it always returns a structured dict (E-QPB-002).
    info = check_runtime(force_missing=False)
    assert "available" in info


# -------------------------------------------------------------------------------------------
# FR-QPB-008 (Decision Log D-10): manual QGIS-install-path override.
#
# Real bridge-based verification (`get_bridge_target`/`get_bridge_target_for_path`) is exercised
# end-to-end by the `qgis`-marked acceptance tests in
# tests/acceptance/qfield_project_builder/test_qgis_manual_path_override.py, which require a real,
# locally installed QGIS. These unit tests instead use `monkeypatch` to isolate the pure
# precedence/plumbing logic in `runtime.py` itself from whether this machine happens to have a
# real QGIS installation at all.
# -------------------------------------------------------------------------------------------


def test_check_runtime_always_includes_qgis_prefix_path_key_even_with_force_missing():
    info = check_runtime(force_missing=True)
    assert "qgis_prefix_path" in info
    assert info["qgis_prefix_path"] is None


def test_force_missing_with_blank_manual_path_matches_force_missing_alone():
    omitted = check_runtime(force_missing=True)
    blank = check_runtime(force_missing=True, manual_path="")
    assert blank == omitted


def test_force_missing_with_whitespace_only_manual_path_is_treated_as_blank():
    omitted = check_runtime(force_missing=True)
    whitespace_only = check_runtime(force_missing=True, manual_path="   ")
    assert whitespace_only == omitted


def test_manual_path_is_never_consulted_when_automatic_detection_already_succeeds(monkeypatch):
    """FR-QPB-008: manual override is a fallback, only relevant once automatic detection fails."""
    monkeypatch.setattr(
        runtime, "_try_import_pyqgis_in_current_process", lambda: (True, "3.44.1")
    )

    def _fail_if_called(_path: str):
        raise AssertionError("manual path must not be consulted when automatic detection succeeds")

    monkeypatch.setattr(qgis_bridge, "get_bridge_target_for_path", _fail_if_called)

    info = check_runtime(manual_path="/some/bogus/path")
    assert info["available"] is True


def test_manual_path_is_consulted_only_after_automatic_detection_fails(monkeypatch):
    monkeypatch.setattr(
        runtime, "_try_import_pyqgis_in_current_process", lambda: (False, None)
    )
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: None)

    calls: list[str] = []

    def _fake_get_bridge_target_for_path(path: str):
        calls.append(path)
        return qgis_bridge.BridgeTarget(
            kind="python_interpreter",
            executable="/fake/python3",
            env={},
            install_path=path,
            qgis_version="3.44.9",
        )

    monkeypatch.setattr(
        qgis_bridge, "get_bridge_target_for_path", _fake_get_bridge_target_for_path
    )

    info = detect_qgis_installation(manual_path="/fake/qgis/install").as_dict()

    assert calls == ["/fake/qgis/install"]
    assert info["available"] is True
    assert info["qgis_prefix_path"] == "/fake/qgis/install"


def test_manual_path_rejection_message_is_distinct_from_generic_missing_message(monkeypatch):
    monkeypatch.setattr(
        runtime, "_try_import_pyqgis_in_current_process", lambda: (False, None)
    )
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: None)
    monkeypatch.setattr(qgis_bridge, "get_bridge_target_for_path", lambda _path: None)
    monkeypatch.setattr(qgis_bridge, "any_plausible_install_dir_exists", lambda: False)

    generic = detect_qgis_installation().as_dict()
    manual_rejected = detect_qgis_installation(manual_path="/bogus/path").as_dict()

    assert manual_rejected["available"] is False
    assert manual_rejected["qgis_prefix_path"] is None
    assert manual_rejected["message"] != generic["message"]
    lowered = manual_rejected["message"].lower()
    for jargon in ("traceback", "exception", "stack trace", "nonetype", "errno"):
        assert jargon not in lowered


def test_manual_path_never_raises_for_a_bridge_probe_returning_none(monkeypatch, tmp_path):
    """A manual path that does not resolve to any working bridge target must produce a clean
    failure result, never propagate an exception -- mirroring FR-QPB-009's crash-free guarantee."""
    monkeypatch.setattr(
        runtime, "_try_import_pyqgis_in_current_process", lambda: (False, None)
    )
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda: None)

    missing_path = tmp_path / "does_not_exist"
    try:
        info = check_runtime(force_missing=True, manual_path=str(missing_path))
    except Exception as exc:  # noqa: BLE001 - this is exactly the failure mode under test
        pytest.fail(f"check_runtime(manual_path=...) must not raise, got: {exc!r}")
    assert info["available"] is False
    assert info["qgis_prefix_path"] is None


def test_as_dict_always_includes_qgis_prefix_path():
    from qfield_builder.runtime import RuntimeInfo

    info = RuntimeInfo(available=False, message="x").as_dict()
    assert info == {"available": False, "message": "x", "qgis_prefix_path": None}
