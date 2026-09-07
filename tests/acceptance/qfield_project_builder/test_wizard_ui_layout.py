"""Acceptance smoke coverage for the approved D-96 wizard layout defect contract.

The detailed widget-policy, focus-chain, candidate-activation, and secret-redaction checks live
under ``tests/unit/`` because they require direct construction of the PySide6 UI. These acceptance
smokes intentionally exercise the same real wizard at user-facing states and verify the
page/button-bar boundary after Qt has laid out visible widgets.

Traceability IDs: TD-UI-QPB-001/003/004/005; AC-UI-QPB-001--006, 010--014, 020--023,
AC-UI-QPB-030--036; C-UI-QPB-005/006.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QScrollArea, QWizard

from qfield_builder.ui.wizard import (
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    ProjectBasicsPage,
    ProjectBuilderWizard,
    ReviewAndBuildPage,
    SiteInputPage,
    SurveyTypePage,
    SymbolStylingPage,
)


MINIMUM_SIZE = QSize(900, 700)
RECOMMENDED_SIZE = QSize(1000, 760)
PAGE_TYPES = (
    ProjectBasicsPage,
    SurveyTypePage,
    SiteInputPage,
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    SymbolStylingPage,
    ReviewAndBuildPage,
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _layout(wizard: QWizard, page_index: int):
    wizard.setCurrentId(page_index)
    QApplication.processEvents()
    page = wizard.currentPage()
    outer = page.layout()
    assert outer is not None
    viewport = next(
        (
            outer.itemAt(index).widget()
            for index in range(outer.count())
            if isinstance(outer.itemAt(index).widget(), QScrollArea)
        ),
        None,
    )
    assert viewport is not None, f"page {page_index} lacks its page-level content viewport"
    return page, viewport


def _rect(widget, root) -> QRect:
    return QRect(widget.mapTo(root, QPoint(0, 0)), widget.size())


def test_ac_ui_qpb_001_real_wizard_keeps_scrollable_pages_above_native_buttons(qapp):
    """AC-UI-QPB-001--006: seven-page real-wizard acceptance smoke."""
    wizard = ProjectBuilderWizard()
    try:
        wizard.show()
        QApplication.processEvents()
        assert wizard.minimumSize() == MINIMUM_SIZE
        assert wizard.size() == RECOMMENDED_SIZE
        for page_index, page_type in enumerate(PAGE_TYPES):
            wizard.resize(MINIMUM_SIZE)
            page, viewport = _layout(wizard, page_index)
            assert isinstance(page, page_type)
            assert viewport.widgetResizable() is True
            assert viewport.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            visible_buttons = [
                wizard.button(button_kind)
                for button_kind in (
                    QWizard.WizardButton.BackButton,
                    QWizard.WizardButton.NextButton,
                    QWizard.WizardButton.FinishButton,
                    QWizard.WizardButton.CancelButton,
                )
                if wizard.button(button_kind) is not None and wizard.button(button_kind).isVisible()
            ]
            assert visible_buttons
            viewport_rect = _rect(viewport, wizard)
            assert viewport_rect.bottom() <= min(_rect(button, wizard).top() for button in visible_buttons)
            assert all(_rect(button, wizard).bottom() <= wizard.height() for button in visible_buttons)
    finally:
        wizard.close()


def test_ac_ui_qpb_010_step4_and_step5_key_and_excel_surfaces_are_reachable(qapp, monkeypatch):
    """AC-UI-QPB-010--014, 020--023, 030--036: affected surfaces acceptance smoke."""
    monkeypatch.setattr(
        "qfield_builder.ui.wizard.canonical_reference.inspect_ktsn_source_candidates",
        lambda *_args, **_kwargs: {
            "candidates": [
                {
                    "path": "/tmp/acceptance-canonical.xlsx",
                    "filename": "acceptance-canonical.xlsx",
                    "source_kind": "bundled_candidate",
                    "validation_status": "valid",
                    "sheet_name": "Sheet1",
                    "header_rows": [1],
                    "sample_rows": [{"scientific_name": "Plantus testensis", "ktsn": "7"}],
                }
            ]
        },
    )
    wizard = ProjectBuilderWizard()
    try:
        wizard.show()
        QApplication.processEvents()
        wizard.resize(MINIMUM_SIZE)
        basemap, _ = _layout(wizard, 3)
        assert isinstance(basemap, ConnectivityBasemapPage)
        basemap.online_radio.setChecked(True)
        QApplication.processEvents()
        assert basemap.api_key_edit.echoMode() == QLineEdit.EchoMode.Password
        assert all(
            control.isVisible()
            for control in (
                basemap.api_key_edit,
                basemap.consent_checkbox,
                basemap.remember_checkbox,
                basemap.layer_combo,
                basemap._refresh_layers_button,
            )
        )
        basemap.offline_radio.setChecked(True)
        QApplication.processEvents()
        assert basemap.api_key_edit.isVisible()
        assert basemap.offline_key_usage_label.isVisible()
        assert not basemap.consent_checkbox.isVisible()

        step5, viewport = _layout(wizard, 4)
        assert isinstance(step5, IdentificationTogglePage)
        step5.enable_checkbox.setChecked(True)
        QApplication.processEvents()
        assert step5.plantnet_api_key_edit.echoMode() == QLineEdit.EchoMode.Password
        assert step5.plantnet_group.isVisible()
        assert step5.reference_source_preview.minimumHeight() == 40
        assert step5.reference_source_preview.maximumHeight() == 40
        assert step5.reference_source_preview.count() == 1
        assert viewport.widgetResizable() is True
    finally:
        wizard.close()


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "AC-UI-QPB-004/005 and the final visual portion of AC-UI-QPB-001--006 require a real "
        "Cocoa display and packaged/native QWizard. Manual smoke: on macOS, launch the built "
        "app at 100%, 125%, 150%, and 200% display scaling; visit all seven pages at 900x700 "
        "and 1000x760; exercise Step 4 online/offline, Step 5 identification on/off, long "
        "Korean/path/status text, candidate scrolling, Tab/Shift+Tab/Enter/Space, and resize "
        "minimum -> recommended -> maximum -> minimum. Confirm no clipping/overlap, visible "
        "native Back/Next/Finish/Cancel bar, visible focus ring, correct logo, masked keys, "
        "consent gates, and no raw workbook copy. This skipped marker is intentional when Cocoa "
        "is unavailable; it is not represented as an automated pass."
    )
)
def test_ac_ui_qpb_999_macos_cocoa_manual_scaled_native_smoke():
    raise AssertionError("manual Cocoa smoke is intentionally skipped")
