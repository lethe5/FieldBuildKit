"""Real upload-dialog navigation and platform fallback, with synthetic local files."""

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QFileDialog, QLineEdit, QListView

from qfield_builder.ui import wizard


@pytest.mark.parametrize("accept", [True, False])
def test_macos_upload_dialog_enters_folder_and_selects_or_cancels(tmp_path, monkeypatch, accept):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(wizard.sys, "platform", "darwin")
    folder = tmp_path / "한글 폴더"
    folder.mkdir()
    workbook = folder / "sample.xlsx"
    workbook.touch()
    failures = []

    def exercise_dialog():
        dialog = app.activeModalWidget()
        try:
            assert isinstance(dialog, QFileDialog)
            assert dialog.testOption(QFileDialog.Option.DontUseNativeDialog)
            assert dialog.findChild(QLineEdit, "fileNameEdit").completer() is None
            view = dialog.findChild(QListView, "listView")
            for _ in range(100):
                index = view.model().index(str(folder))
                rect = view.visualRect(index)
                if index.isValid() and not rect.isEmpty():
                    break
                QTest.qWait(10)
            assert not rect.isEmpty()
            QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
            QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
            assert dialog.directory().absolutePath() == str(folder)
            if accept:
                dialog.selectFile(str(workbook))
                button = dialog.findChild(QDialogButtonBox).button(
                    QDialogButtonBox.StandardButton.Open
                )
                button.click()
            else:
                dialog.reject()
        except Exception as error:
            failures.append(error)
            if dialog is not None:
                dialog.reject()

    QTimer.singleShot(100, exercise_dialog)
    result = wizard._get_open_file_name(None, "Workbook", str(tmp_path), "Excel (*.xlsx)")
    assert not failures, failures
    assert result == ((str(workbook), "Excel (*.xlsx)") if accept else ("", ""))


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_other_platforms_keep_native_file_picker(monkeypatch, platform):
    monkeypatch.setattr(wizard.sys, "platform", platform)
    calls = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: calls.append(args) or ("chosen.xlsx", "Excel")
    )
    assert wizard._get_open_file_name(None, "Upload", "/local", "Excel") == (
        "chosen.xlsx", "Excel"
    )
    assert calls == [(None, "Upload", "/local", "Excel")]
