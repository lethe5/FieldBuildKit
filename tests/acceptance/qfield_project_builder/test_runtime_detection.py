"""QGIS/PyQGIS/GDAL runtime detection and verification (Section 5.2, E-QPB-002).

Covers:
- AC-QPB-029: no compatible QGIS installation -> clear, non-technical error, not a crash/silent
  failure, when a build is attempted.
- AC-QPB-053: a detected QGIS 3.44 LTR installation on Windows/macOS passes runtime verification
  without a separately pip-installed PyQGIS (FR-QPB-007a/FR-QPB-009).
"""
from __future__ import annotations

import pytest

from .conftest import make_base_config


def test_missing_runtime_produces_a_clear_actionable_error_not_a_crash(
    acceptance_api, tmp_path
):
    """AC-QPB-029 / E-QPB-002.

    Uses the documented `force_missing` test hook (see HARNESS_CONTRACT.md) so this is
    reproducible regardless of whether the machine actually running the suite happens to have
    QGIS installed.
    """
    info = acceptance_api.check_runtime(force_missing=True)
    assert info["available"] is False
    message = info["message"]
    assert isinstance(message, str) and message.strip(), "must include a human-readable message"
    lowered = message.lower()
    technical_jargon = ["traceback", "exception", "stack trace", "nonetype", "errno"]
    assert not any(term in lowered for term in technical_jargon), (
        f"error message must be non-technical, got: {message!r}"
    )

    config = make_base_config("simple_inventory")
    # A build attempted while the runtime is (simulated to be) unavailable must not raise, and
    # must not silently "succeed" with no project.
    try:
        result = acceptance_api.build_project(
            {**config, "_test_force_missing_runtime": True}, str(tmp_path / "out")
        )
    except Exception as exc:  # noqa: BLE001 - this is exactly the failure mode under test
        pytest.fail(
            "build_project must return a structured error result for a missing runtime, "
            f"not raise an exception: {exc!r}"
        )
    assert result["success"] is False
    assert result.get("error_code"), "a missing-runtime failure must report a structured error_code"
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir()), (
        "no partially generated project may be left behind (E-QPB-009)"
    )


@pytest.mark.qgis
def test_detected_qgis_344_lts_passes_verification_without_pip_installed_pyqgis(acceptance_api):
    """AC-QPB-053: runtime verification succeeds using the QGIS-Desktop-supplied PyQGIS only."""
    info = acceptance_api.check_runtime()
    assert info["available"] is True, (
        "this test is marked `qgis` and gated on check_runtime() already reporting availability; "
        f"got: {info}"
    )
    # FR-QPB-007a: PyQGIS must come from the detected QGIS Desktop install, not a separate pip
    # install. We cannot inspect *how* the implementation sourced PyQGIS from a black-box test,
    # but we can assert the reported message does not claim a pip-based PyQGIS was used/required.
    message = info.get("message", "")
    assert "pip install pyqgis" not in message.lower()
    assert "pip install qgis" not in message.lower()
