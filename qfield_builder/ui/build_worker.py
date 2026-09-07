"""QThread wrapper around the separate GIS worker process (Section 5.3).

The build itself (GeoPackage/`.qgs`/basemap generation) already runs in its own OS process via
:mod:`qfield_builder.worker_process` (spawned with :mod:`multiprocessing`). This module's
`QThread` exists only so that *waiting* for that subprocess to finish does not block the PySide6
UI's own event loop/repaint — it is not the FR-QPB-010 process boundary itself, just ordinary Qt
UI responsiveness.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .. import worker_process
from ..offline_estimate import total_tile_count


def build_operation_timeout_seconds(config: dict) -> float:
    """Return a lifecycle budget based on the selected offline work, not a fixed cutoff."""
    baseline = 30 * 60
    basemap = config.get("basemap") or {}
    if basemap.get("mode") != "offline" or not basemap.get("bbox"):
        return float(baseline)
    try:
        tile_count = total_tile_count(
            basemap["bbox"], int(basemap["min_zoom"]), int(basemap["max_zoom"])
        )
    except (KeyError, TypeError, ValueError):
        return float(baseline)
    # This is an idle budget, not a total-operation ceiling.  The worker sends a heartbeat after
    # each successfully fetched/inserted tile, and worker_process resets this budget on every
    # heartbeat.  A genuinely wedged operation is still bounded by the budget, while a large
    # operation is never killed merely because its total elapsed time crossed a fixed 12-hour
    # limit.  Per-request networking remains bounded in vworld_tiles.make_real_vworld_tile_fetcher.
    return float(max(baseline, 120 + tile_count * 2))


class BuildWorkerThread(QThread):
    finished_with_result = Signal(dict)
    progress_updated = Signal(dict)

    def __init__(self, config: dict, output_dir: str, parent=None):
        super().__init__(parent)
        self._config = config
        self._output_dir = output_dir
        # This event is shared with the spawned build process. QThread interruption alone cannot
        # reach that process, while this event lets build_project/build_mbtiles observe a real
        # user cancellation and execute their normal rollback path.
        self._cancel_event = worker_process.create_cancel_event()

    def cancel(self) -> None:
        """Request cooperative cancellation of the spawned build and its MBTiles writer."""
        self._cancel_event.set()

    def run(self) -> None:
        outcome = worker_process.run_job_in_subprocess(
            "build_project",
            {"config": self._config, "output_dir": self._output_dir},
            timeout_seconds=build_operation_timeout_seconds(self._config),
            cancel_event=self._cancel_event,
            progress_callback=self.progress_updated.emit,
        )
        if outcome.get("ok"):
            self.finished_with_result.emit(outcome["result"])
        else:
            self.finished_with_result.emit(
                {
                    "success": False,
                    "cancelled": outcome.get("error_code") == "cancelled",
                    "error_code": outcome.get("error_code", "worker_process_failed"),
                    "error_message": outcome.get(
                        "error", "GIS 작업 프로세스에서 예기치 않은 오류가 발생했습니다."
                    ),
                }
            )
