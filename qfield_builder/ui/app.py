"""Desktop application entry point (FR-QPB-001/002: PySide6, Windows + macOS)."""
from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .. import credential_store
from .credential_password_dialogs import prompt_for_setup_password
from .wizard import ProjectBuilderWizard

# A refined, neutral "clean/flat modern" palette (stakeholder direction: "Apply Qt's Fusion
# style with a refined neutral palette, better spacing/typography, and flat modern widget
# styling -- closest to what current native macOS/Windows apps look like, without a large
# rewrite"). Deliberately a plain, light, professional palette -- no dark mode, no saturated
# "branded" colours -- just clean neutrals plus a single, restrained accent colour used for
# selection/focus/default-button highlighting.
_WINDOW_BG = "#f2f2f5"
_BASE_BG = "#ffffff"
_ALT_BASE_BG = "#ececed"
_TEXT_COLOR = "#1d1d1f"
_DISABLED_TEXT_COLOR = "#9a9a9e"
_BORDER_COLOR = "#c9c9cd"
_ACCENT_COLOR = "#0a7cff"
_ACCENT_TEXT_COLOR = "#ffffff"

# A modest, flat-modern widget stylesheet layered on top of the Fusion style + palette above:
# subtle rounded corners and consistent padding on the most common input widgets, and a plain
# bordered/titled look for QGroupBox (used throughout the wizard's pages to group related
# fields). This intentionally stays generic/structural (no page-specific selectors) so it is a
# one-time, app-wide styling change rather than something that needs to be repeated per page.
_STYLESHEET = f"""
QGroupBox {{
    font-weight: 600;
    border: 1px solid {_BORDER_COLOR};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
}}
QPushButton {{
    padding: 4px 12px;
    border: 1px solid {_BORDER_COLOR};
    border-radius: 4px;
    background-color: {_WINDOW_BG};
}}
QPushButton:default {{
    background-color: {_ACCENT_COLOR};
    color: {_ACCENT_TEXT_COLOR};
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QListWidget {{
    padding: 4px 6px;
    border: 1px solid {_BORDER_COLOR};
    border-radius: 4px;
    background-color: {_BASE_BG};
}}
QProgressBar {{
    border: 1px solid {_BORDER_COLOR};
    border-radius: 4px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {_ACCENT_COLOR};
    border-radius: 4px;
}}
"""


def _build_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(_WINDOW_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(_TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.Base, QColor(_BASE_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(_ALT_BASE_BG))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(_BASE_BG))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(_TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.Text, QColor(_TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.Button, QColor(_WINDOW_BG))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(_TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff3b30"))
    palette.setColor(QPalette.ColorRole.Link, QColor(_ACCENT_COLOR))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(_ACCENT_COLOR))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(_ACCENT_COLOR))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(_ACCENT_TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(_DISABLED_TEXT_COLOR))

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(_DISABLED_TEXT_COLOR))

    return palette


def _apply_flat_modern_style(app: QApplication) -> None:
    """FR-independent visual-polish pass: Qt's Fusion style plus the refined neutral palette
    and flat widget styling above, and a slightly more readable base font size than Qt's
    platform default (the stakeholder's own reported reaction to real screenshots was that the
    prior, unstyled default looked cramped/dated). This never touches what any wizard page
    collects or how the build pipeline works -- it is purely `QApplication`-level presentation.
    """
    app.setStyle("Fusion")
    app.setPalette(_build_palette())

    font = app.font()
    if font.pointSize() > 0:
        font.setPointSize(max(font.pointSize(), 11))
    app.setFont(font)

    app.setStyleSheet(_STYLESHEET)


def maybe_prompt_for_first_launch_password(setup_prompt_fn=None) -> None:
    """NFR-QPB-073/AC-QPB-092 (Decision Log D-53): on the first launch of this application, or on
    any subsequent launch where no encrypted-storage password has yet been established (including
    after a prior decline), prompt the user to set one -- before the main wizard window ever
    appears. This is never a general access-gate: if the user declines/skips, no password is
    established, "Remember this key" stays unavailable/disabled for that session (enforced by
    `ConnectivityBasemapPage`/`IdentificationTogglePage`'s own `credential_store.
    is_password_established()` check), and this same prompt is shown again the next time this
    function runs (i.e. the next launch).

    `setup_prompt_fn`, if supplied, replaces the real, modal `PasswordSetupDialog` for tests --
    the same injectable-test-seam convention used throughout `qfield_builder.ui.wizard`."""
    if credential_store.is_password_established():
        return
    prompt_fn = setup_prompt_fn if setup_prompt_fn is not None else prompt_for_setup_password
    password = prompt_fn()
    if password:
        credential_store.establish_password(password)


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv
    if "--check-runtime" in arguments:
        from ..runtime import check_runtime

        result = check_runtime()
        if sys.stdout is not None:
            print(result["message"])
        return 0 if result["available"] else 1
    app = QApplication(argv if argv is not None else sys.argv)
    _apply_flat_modern_style(app)
    # This independent application starts with its own credential store.
    maybe_prompt_for_first_launch_password()
    wizard = ProjectBuilderWizard()
    wizard.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
