"""Selected-file validation must not scan neighbours, block Qt, or revive stale inputs."""
import hashlib
import shutil
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from qfield_builder import canonical_reference as reference
from qfield_builder.ui import wizard as ui

SAMPLE = Path(__file__).resolve().parents[2] / "resources/samples/taxonomy_sample.xlsx"


def test_upload_reads_only_selected_workbook_once(tmp_path, monkeypatch, wait_reference_validation):
    app = QApplication.instance() or QApplication([])
    wizard = ui.ProjectBuilderWizard()
    page = wizard.page(4)
    selected = tmp_path / "한글 참조.xlsx"
    shutil.copyfile(SAMPLE, selected)
    (tmp_path / "unrelated.xlsx").write_bytes(b"not a workbook")
    calls = []
    ingest = reference.ingest_canonical_workbook

    def counted(path, **kwargs):
        calls.append(Path(path))
        assert Path(path) == selected
        return ingest(path, **kwargs)

    def no_discovery(*args, **kwargs):
        pytest.fail("Upload must not discover the containing directory")

    monkeypatch.setattr(reference, "ingest_canonical_workbook", counted)
    monkeypatch.setattr(reference, "inspect_ktsn_source_candidates", no_discovery)
    monkeypatch.setattr(ui, "_get_open_file_name", lambda *a, **k: (str(selected), ""))
    page._browse_reference_source()
    wait_reference_validation(page)
    assert page.isComplete()
    assert calls == [selected]
    assert page.canonical_reference_config()["sha256"] == hashlib.sha256(selected.read_bytes()).hexdigest()
    assert page.reference_sheet_preview.rowCount() == 3
    page._select_reference_candidate(page.reference_source_preview.item(0))
    assert calls == [selected]  # Confirm/reselect reuses validation, but still verifies the digest.
    selected.write_bytes(b"modified")
    page._select_reference_candidate(page.reference_source_preview.item(0))
    assert not page.isComplete() and page.canonical_reference_config() is None
    wizard.close()
    app.processEvents()


@pytest.mark.parametrize("action", ["clear", "reselect", "close", "error"])
def test_slow_validation_keeps_qt_responsive_and_handles_lifecycle(
    monkeypatch, wait_reference_validation, action
):
    app = QApplication.instance() or QApplication([])
    wizard = ui.ProjectBuilderWizard()
    page = wizard.page(4)
    wizard.show()
    monkeypatch.setattr(ui, "_get_open_file_name", lambda *a, **k: (str(SAMPLE), ""))
    page._browse_reference_source()
    wait_reference_validation(page)
    previous = page.canonical_reference_config()
    original = reference.preview_canonical_workbook
    release = Event()

    def slow(path):
        assert release.wait(5), "Test worker was not released"
        if action == "error":
            raise OSError("synthetic read failure")
        return original(path)

    monkeypatch.setattr(reference, "preview_canonical_workbook", slow)
    ticks = []
    try:
        page._browse_reference_source()
        assert not page.isComplete() and page.canonical_reference_config() is None
        assert not page.reference_browse_button.isEnabled()
        QTimer.singleShot(0, lambda: ticks.append(True))
        QTest.qWait(20)
        assert ticks  # The GUI dispatches events while the reader is blocked.
        assert page._reference_preview_worker.isRunning()
        if action == "clear":
            page._clear_reference_source()
        elif action == "reselect":
            page._select_reference_candidate(page.reference_source_preview.item(0))
        elif action == "close":
            wizard.reject()
            assert wizard.isVisible()  # Destruction is deferred until the QThread finishes.
    finally:
        release.set()
        wait_reference_validation(page)
    assert page.reference_browse_button.isEnabled()
    if action == "clear":
        assert page.isComplete() and page.canonical_reference_config() is None
        assert page.reference_source_preview.count() == 0
    elif action == "reselect":
        assert page.canonical_reference_config() == previous
        assert page.reference_source_preview.count() == 1
    elif action == "close":
        assert not wizard.isVisible()
    else:
        assert not page.isComplete() and "synthetic read failure" in page.reference_source_status_label.text()
    wizard.close()
    app.processEvents()
