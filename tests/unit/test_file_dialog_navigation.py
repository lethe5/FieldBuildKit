"""File uploads use the platform-native QFileDialog entry point, like folder selection."""

import pytest
from PySide6.QtWidgets import QFileDialog

from qfield_builder.ui import wizard


@pytest.mark.parametrize(
    "selection", [("/local/한글 폴더/sample.xlsx", "Excel (*.xlsx)"), ("", "")]
)
def test_upload_uses_native_file_picker_and_preserves_selection(monkeypatch, selection):
    calls = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: calls.append(args) or selection
    )
    assert wizard._get_open_file_name(None, "Upload", "/local", "Excel (*.xlsx)") == selection
    assert calls == [(None, "Upload", "/local", "Excel (*.xlsx)")]
