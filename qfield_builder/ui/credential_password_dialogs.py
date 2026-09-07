"""Qt dialogs for the encrypted local credential-storage password (NFR-QPB-073, Decision Log
D-53/D-55).

Two distinct dialogs, matching two distinct, deliberately different trigger points:

- :class:`PasswordSetupDialog` -- the first-launch (or still-not-yet-established) encrypted-
  storage password *setup* prompt (AC-QPB-092). Shown once, before the main wizard window ever
  appears, only when no encrypted-storage password has yet been established. Always offers a
  "건너뛰기" (skip) action, because this password must never function as a general application
  access-gate (NFR-QPB-073): declining leaves "Remember this key" unavailable for that session and
  falls back to the pre-existing session-only retention, and the same prompt is shown again at the
  next launch.
- :class:`PasswordUnlockDialog` -- the retrieval-time-*only* re-prompt for an *already-
  established* password (NFR-QPB-073/AC-QPB-097, closing Open Question O-21 per Decision Log
  D-55). Shown only at the specific point of use where a previously remembered VWorld/Pl@ntNet key
  would otherwise be auto-filled -- never at general application startup, never as a blanket gate
  before any other, unrelated part of the application.

Both are plain, thin `QDialog` wrappers around user input; all of the actual cryptography and
persistence logic they ultimately drive lives entirely in `qfield_builder.credential_store`, which
has no Qt dependency of its own and can be exercised/unit-tested independently of these dialogs.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class PasswordSetupDialog(QDialog):
    """AC-QPB-092: the first-launch encrypted-storage password setup prompt."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("암호화 저장 비밀번호 설정")
        self.setModal(True)

        intro_label = QLabel(
            "VWorld/Pl@ntNet API 키를 \"이 키 기억하기\"로 저장하려면, 이 컴퓨터에 암호화하여 "
            "저장하는 데 사용할 비밀번호를 설정하세요. 이 비밀번호는 저장된 키를 암호화하는 "
            "용도로만 사용되며, 이 앱의 다른 기능을 사용하는 데는 필요하지 않습니다. 지금 "
            "건너뛰어도 필요할 때 다시 물어봅니다. 이 비밀번호를 잊어버리면 이전에 저장된 키는 "
            "복구할 수 없습니다."
        )
        intro_label.setWordWrap(True)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_edit = QLineEdit()
        self._confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self._error_label = QLabel("")
        self._error_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("비밀번호:", self._password_edit)
        form.addRow("비밀번호 확인:", self._confirm_edit)

        buttons = QDialogButtonBox()
        self._set_button = buttons.addButton("설정", QDialogButtonBox.ButtonRole.AcceptRole)
        self._skip_button = buttons.addButton("건너뛰기", QDialogButtonBox.ButtonRole.RejectRole)
        self._set_button.clicked.connect(self._on_set_clicked)
        self._skip_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._result_password: str | None = None

    def _on_set_clicked(self) -> None:
        password = self._password_edit.text()
        confirm = self._confirm_edit.text()
        if not password:
            self._error_label.setText("비밀번호를 입력해주세요.")
            return
        if password != confirm:
            self._error_label.setText("비밀번호 확인이 일치하지 않습니다.")
            return
        self._result_password = password
        self.accept()

    def password(self) -> str | None:
        """The password the user set, or `None` if they skipped/cancelled/closed the dialog."""
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        return self._result_password


class PasswordUnlockDialog(QDialog):
    """NFR-QPB-073/AC-QPB-097: the retrieval-time-only re-prompt for an already-established
    encrypted-storage password."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("저장된 키 사용을 위한 비밀번호")
        self.setModal(True)

        intro_label = QLabel(
            "이전에 \"이 키 기억하기\"로 저장한 API 키를 불러오려면 암호화 저장 비밀번호를 "
            "입력하세요. 취소하면 저장된 키를 불러오지 않으며, 아래에서 직접 입력할 수 "
            "있습니다."
        )
        intro_label.setWordWrap(True)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("비밀번호:", self._password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def password(self) -> str | None:
        """The password the user entered, or `None` if they cancelled/closed the dialog."""
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        return self._password_edit.text()


def prompt_for_setup_password(parent: QWidget | None = None) -> str | None:
    """Default, real `PasswordSetupDialog`-backed prompt function -- the production
    implementation of the injectable `setup_prompt_fn` seam `qfield_builder.ui.app` accepts."""
    dialog = PasswordSetupDialog(parent)
    dialog.exec()
    return dialog.password()


def prompt_for_unlock_password(parent: QWidget | None = None) -> str | None:
    """Default, real `PasswordUnlockDialog`-backed prompt function -- the production
    implementation of the injectable `password_prompt_fn` seam the wizard pages below accept."""
    dialog = PasswordUnlockDialog(parent)
    dialog.exec()
    return dialog.password()
