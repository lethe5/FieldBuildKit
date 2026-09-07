"""Run expensive standalone GIS jobs in a separate local process.

The PySide6 UI stays responsive while this worker creates SQLite data, processes
rasters with Rasterio, reprojects uploads with Fiona, and writes template projects.
No installed-QGIS subprocess is needed.
"""
from __future__ import annotations

import multiprocessing as mp
import queue
import time
import traceback
from typing import Any

SUPPORTED_JOBS = (
    "build_qgis_project",
    "check_runtime",
    "build_project",
    "attempt_feature_save",
    "validate_project",
)


def create_cancel_event():
    """Create an Event compatible with the spawn context used by the GIS worker."""
    return mp.get_context("spawn").Event()


def _worker_entrypoint(
    job: dict, result_queue: mp.Queue, cancel_event: Any | None = None
) -> None:
    """Run a standalone job inside the spawned child process."""
    try:
        job_name = job.get("job")
        kwargs = job.get("kwargs", {})
        if job_name == "check_runtime":
            from . import runtime

            result_queue.put({"ok": True, "result": runtime.check_runtime(**kwargs)})
            return
        if job_name == "build_qgis_project":
            from . import qgis_worker

            result_queue.put({"ok": True, "result": qgis_worker.build_qgis_project(**kwargs)})
            return
        if job_name == "build_project":
            from .build import build_project

            should_cancel = cancel_event.is_set if cancel_event is not None else None

            def report_progress(progress: dict) -> None:
                # A closed parent queue must not turn an otherwise valid build into a failed
                # build.  Progress is advisory; the final structured result remains authoritative.
                try:
                    result_queue.put({"kind": "progress", "progress": progress})
                except Exception:  # noqa: BLE001 - the parent may have gone away.
                    pass

            result_queue.put(
                {
                    "ok": True,
                    "result": build_project(
                        **kwargs,
                        should_cancel=should_cancel,
                        progress_callback=report_progress,
                    ),
                }
            )
            return
        if job_name == "attempt_feature_save":
            from .feature_save import attempt_feature_save

            result_queue.put({"ok": True, "result": attempt_feature_save(**kwargs)})
            return
        if job_name == "validate_project":
            from .validate import validate_project

            result_queue.put({"ok": True, "result": validate_project(**kwargs)})
            return
        result_queue.put({"ok": False, "error": f"Unknown job: {job_name!r}"})
    except Exception as exc:  # noqa: BLE001 - must report failure back to the UI, never crash silently.
        result_queue.put({"ok": False, "error": str(exc), "traceback": traceback.format_exc()})


def run_job_in_subprocess(
    job_name: str,
    kwargs: dict,
    timeout_seconds: float = 300.0,
    cancel_event: Any | None = None,
    progress_callback: Any | None = None,
) -> dict:
    """Launch the GIS worker as a genuinely separate OS process and wait for its result.

    Returns `{"ok": True, "result": ...}` or `{"ok": False, "error": str, "traceback": str}` —
    the UI process must treat both as structured outcomes (E-QPB-015: a worker crash must be
    surfaced as an actionable error, never leave the UI hung).
    """
    if job_name not in SUPPORTED_JOBS:
        raise ValueError(f"Unsupported job: {job_name!r}")

    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_worker_entrypoint,
        args=({"job": job_name, "kwargs": kwargs}, result_queue, cancel_event),
    )
    process.start()
    try:
        timeout_budget = max(0.0, timeout_seconds)
        deadline = time.monotonic() + timeout_budget
        timed_out = False
        outcome = None
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    message = result_queue.get(timeout=min(0.25, remaining))
                    if message.get("kind") == "progress":
                        # For a build operation this is a concrete forward-progress signal from
                        # the MBTiles writer.  Treat timeout_seconds as an idle budget so progress
                        # keeps the operation live beyond any former fixed total-time ceiling.
                        deadline = time.monotonic() + timeout_budget
                        if progress_callback is not None:
                            try:
                                progress_callback(message.get("progress") or {})
                            except Exception:  # noqa: BLE001 - UI progress must remain advisory.
                                pass
                        continue
                    outcome = message
                    break
                except queue.Empty:
                    continue
        except Exception:  # noqa: BLE001 - an IPC failure must not hang the UI.
            timed_out = True

        if timed_out or outcome is None:
            # Give a cooperative build a chance to run its normal BuildCancelledError cleanup
            # before the process is terminated. The returned outcome deliberately remains a
            # timeout: this was an operation-budget failure, not a user cancellation.
            if cancel_event is not None:
                cancel_event.set()
            outcome = {
                "ok": False,
                "error_code": "worker_timeout",
                "error": "GIS 작업 프로세스가 제한 시간 내에 응답하지 않았습니다.",
            }
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
        if process.exitcode not in (0, None) and outcome.get("ok"):
            # The process reported success but then crashed on exit — surface defensively.
            outcome = {
                "ok": False,
                "error": (
                    "GIS 작업 프로세스가 비정상적으로 종료되었습니다 "
                    f"(종료 코드: {process.exitcode})."
                ),
            }
        return outcome
    finally:
        if process.is_alive():
            process.terminate()
