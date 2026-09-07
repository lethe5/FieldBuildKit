"""Unit tests for qfield_builder.worker_process (Section 5.3, FR-QPB-010, A-QPB-001).

Exercises the real multiprocessing-based IPC mechanism end-to-end using the `check_runtime` job
(deterministic via `force_missing=True`), confirming actual OS-level process separation works.
`build_qgis_project`/`build_project` outcomes now genuinely depend on whether this machine has a
real, bridgeable QGIS installation (see `qfield_builder.qgis_bridge`) — these tests assert the
*shape* of the result in both cases rather than assuming either one.
"""
from __future__ import annotations

import multiprocessing as mp

import pytest

from qfield_builder.runtime import check_runtime
from qfield_builder.worker_process import run_job_in_subprocess

_QGIS_AVAILABLE = check_runtime()["available"]


def test_check_runtime_job_runs_in_a_genuinely_separate_process():
    outcome = run_job_in_subprocess("check_runtime", {"force_missing": True}, timeout_seconds=30)
    assert outcome["ok"] is True
    assert outcome["result"]["available"] is False
    assert outcome["result"]["message"]


def test_unknown_job_name_raises_value_error():
    with pytest.raises(ValueError):
        run_job_in_subprocess("not_a_real_job", {})


def test_build_qgis_project_job_reports_structured_failure_for_nonexistent_geopackage():
    outcome = run_job_in_subprocess(
        "build_qgis_project",
        {
            "gpkg_path": "/nonexistent/does-not-matter.gpkg",
            "qgs_path": "/nonexistent/does-not-matter.qgs",
            "survey_type": "simple_inventory",
            "project_crs": "EPSG:5186",
            "basemap_config": None,
        },
        timeout_seconds=30,
    )
    # Whether or not a real QGIS bridge is available on this machine, a nonexistent GeoPackage
    # path must be reported as a structured failure, never hang the caller or silently succeed
    # (E-QPB-015).
    assert outcome["ok"] is False
    assert outcome["error"]


@pytest.mark.skipif(not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation")
def test_build_qgis_project_job_succeeds_with_a_real_geopackage(tmp_path):
    """When a real QGIS bridge is available, the worker process genuinely generates a `.qgs`
    project — proving the multiprocessing-spawned worker's call into
    `qfield_builder.qgis_worker.build_qgis_project` really reaches a working PyQGIS runtime via
    `qfield_builder.qgis_bridge`, not merely a structured failure."""
    from qfield_builder import gpkg, naming

    gpkg_path = str(tmp_path / "test.gpkg")
    gpkg.build_geopackage(
        gpkg_path,
        "simple_inventory",
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgs_path = str(tmp_path / "test.qgs")
    outcome = run_job_in_subprocess(
        "build_qgis_project",
        {
            "gpkg_path": gpkg_path,
            "qgs_path": qgs_path,
            "survey_type": "simple_inventory",
            "project_crs": "EPSG:5186",
            "basemap_config": None,
        },
        timeout_seconds=60,
    )
    assert outcome["ok"] is True, outcome
    assert outcome["result"] == {
        "online_key_embedded": False,
        "vworld_key_saved": False,
        "plantnet_key_embedded": False,
        "probability_raster_registration_count": 0,
    }


def test_build_project_job_runs_end_to_end_through_the_subprocess(tmp_path):
    """The real production path: the whole build_project pipeline, run inside the worker
    process, proving the job dispatches into build.build_project via IPC and returns a
    well-formed result dict either way."""
    config = {
        "project_display_name": "Worker Process Test",
        "survey_type": "simple_inventory",
        "basemap": {"mode": "none"},
        # Deterministic regardless of whether this machine has QGIS (see HARNESS_CONTRACT.md);
        # this test is about the IPC mechanism, not runtime detection itself.
        "_test_force_missing_runtime": True,
    }
    outcome = run_job_in_subprocess(
        "build_project",
        {"config": config, "output_dir": str(tmp_path / "out")},
        timeout_seconds=60,
    )
    assert outcome["ok"] is True
    result = outcome["result"]
    assert set(result.keys()) >= {"success", "cancelled", "error_code", "error_message"}
    assert result["success"] is False
    assert result["error_code"] == "runtime_missing"


def test_build_project_job_propagates_user_cancellation_to_structured_result(tmp_path):
    """The production worker boundary must pass cancellation into build_project itself.

    Setting the event before launch makes this deterministic and also proves cancellation wins
    over the runtime check; a worker that ignored the event would instead return runtime_missing
    for this fixture.
    """
    cancel_event = mp.get_context("spawn").Event()
    cancel_event.set()
    output_dir = tmp_path / "cancelled"

    outcome = run_job_in_subprocess(
        "build_project",
        {
            "config": {
                "project_display_name": "Cancelled Worker Build",
                "survey_type": "simple_inventory",
                "_test_force_missing_runtime": True,
            },
            "output_dir": str(output_dir),
        },
        timeout_seconds=30,
        cancel_event=cancel_event,
    )

    assert outcome["ok"] is True, outcome
    result = outcome["result"]
    assert result["success"] is False
    assert result["cancelled"] is True
    assert result["error_code"] == "cancelled"
    assert not output_dir.exists()
