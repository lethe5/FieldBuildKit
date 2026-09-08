"""Clean-room tests for the D-96 wizard layout contract.

These tests deliberately construct the real PySide6 pages and run a real layout pass.  They do
not accept source-text assertions or a widget's unlaid-out size hint as proof that the UI is safe.
The tests are expected to be red until the approved D-96 contract is implemented.

Traceability IDs:
    TD-UI-QPB-001/002/004/005/006; AC-UI-QPB-001--006, 010--014, 020--023,
    AC-UI-QPB-030--036; C-UI-QPB-002--006.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QWidget,
    QWizard,
    QWizardPage,
)

from qfield_builder.ui import wizard as wizard_module
from qfield_builder.ui.wizard import (
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    ProjectBuilderWizard,
    ReviewAndBuildPage,
    SiteInputPage,
    SurveyTypePage,
    SymbolStylingPage,
)

PAGE_TYPES = (
    wizard_module.ProjectBasicsPage,
    SurveyTypePage,
    SiteInputPage,
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    SymbolStylingPage,
    ReviewAndBuildPage,
)
MINIMUM_SIZE = QSize(900, 600)
RECOMMENDED_SIZE = QSize(1000, 620)
SUPPORTED_MAX_TARGET = QSize(1200, 820)
EXPECTED_MARGINS = (12, 8, 12, 8)
EXPECTED_OUTER_SPACING = 8


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def wizard():
    instance = ProjectBuilderWizard()
    instance.resize(MINIMUM_SIZE)
    instance.show()
    QApplication.processEvents()
    yield instance
    instance.close()
    QApplication.processEvents()


def _process_layout() -> None:
    QApplication.processEvents()
    QApplication.processEvents()


def _page_scroll_area(page: QWizardPage) -> QScrollArea:
    """Return the page-level viewport, not one of the page's optional nested scrollers."""
    layout = page.layout()
    assert layout is not None
    direct_scroll_areas = [
        layout.itemAt(index).widget()
        for index in range(layout.count())
        if isinstance(layout.itemAt(index).widget(), QScrollArea)
    ]
    assert len(direct_scroll_areas) == 1, (
        f"{type(page).__name__} must expose exactly one direct page content viewport; "
        f"found {len(direct_scroll_areas)}"
    )
    return direct_scroll_areas[0]


def _mapped_rect(widget: QWidget, ancestor: QWidget) -> QRect:
    return QRect(widget.mapTo(ancestor, QPoint(0, 0)), widget.size())


def _visible_native_buttons(wizard: QWizard) -> list[QPushButton]:
    return [
        wizard.button(button_kind)
        for button_kind in (
            QWizard.WizardButton.BackButton,
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton,
        )
        if wizard.button(button_kind) is not None and wizard.button(button_kind).isVisible()
    ]


def _assert_no_layout_sibling_overlap(container: QWidget, root: QWidget) -> None:
    layout = container.layout()
    if layout is None:
        return
    visible_widgets: list[QWidget] = []
    nested_layouts: list[tuple[object, QWidget]] = []
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget()
        if widget is not None:
            if widget.isVisible():
                visible_widgets.append(widget)
        elif item.layout() is not None:
            nested_layouts.append((item.layout(), container))

    for index, first in enumerate(visible_widgets):
        first_rect = _mapped_rect(first, root)
        for second in visible_widgets[index + 1 :]:
            second_rect = _mapped_rect(second, root)
            assert not first_rect.intersects(second_rect), (
                f"{type(container).__name__} siblings overlap after a real layout pass: "
                f"{first!r}={first_rect}, {second!r}={second_rect}"
            )

    for nested_layout, parent in nested_layouts:
        _assert_layout_sibling_overlap_for_layout(nested_layout, parent, root)
    for widget in visible_widgets:
        if isinstance(widget, QScrollArea) and widget.widget() is not None:
            _assert_no_layout_sibling_overlap(widget.widget(), root)
        else:
            _assert_no_layout_sibling_overlap(widget, root)


def _assert_layout_sibling_overlap_for_layout(layout, parent: QWidget, root: QWidget) -> None:
    visible_widgets: list[QWidget] = []
    nested_layouts: list[tuple[object, QWidget]] = []
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget()
        if widget is not None:
            if widget.isVisible():
                visible_widgets.append(widget)
        elif item.layout() is not None:
            nested_layouts.append((item.layout(), parent))
    for index, first in enumerate(visible_widgets):
        first_rect = _mapped_rect(first, root)
        for second in visible_widgets[index + 1 :]:
            second_rect = _mapped_rect(second, root)
            assert not first_rect.intersects(second_rect), (
                f"nested layout siblings overlap: {first!r}={first_rect}, {second!r}={second_rect}"
            )
    for nested_layout, nested_parent in nested_layouts:
        _assert_layout_sibling_overlap_for_layout(nested_layout, nested_parent, root)


def _set_long_content_state(wizard: ProjectBuilderWizard, page_index: int) -> None:
    page = wizard.page(page_index)
    if isinstance(page, SiteInputPage):
        page._applicable = True
        page.input_mode_draw_radio.setChecked(True)
        page._update_input_mode_visibility()
    elif isinstance(page, ConnectivityBasemapPage):
        page.online_radio.setChecked(True)
    elif isinstance(page, IdentificationTogglePage):
        page.enable_checkbox.setChecked(True)
    _process_layout()


def _show_page(wizard: ProjectBuilderWizard, page_index: int) -> QWizardPage:
    wizard.setCurrentId(page_index)
    _set_long_content_state(wizard, page_index)
    _process_layout()
    return wizard.currentPage()


def _interactive_descendants(root: QWidget) -> list[QWidget]:
    types = (
        QAbstractButton,
        QComboBox,
        QLineEdit,
        QListWidget,
        QPlainTextEdit,
        QAbstractSpinBox,
    )
    return [
        widget
        for widget in root.findChildren(QWidget)
        if isinstance(widget, types) and widget.isVisible() and widget.isEnabled()
    ]


def _has_semantic_name(widget: QWidget) -> bool:
    explicit = widget.accessibleName().strip()
    if explicit:
        return True
    for attribute in ("text", "placeholderText", "toolTip"):
        value = getattr(widget, attribute, lambda: "")()
        if isinstance(value, str) and value.strip():
            return True
    ancestor = widget.parentWidget()
    while ancestor is not None:
        for label in ancestor.findChildren(QLabel):
            if label.isVisible() and label.text().strip():
                return True
        ancestor = ancestor.parentWidget()
    return False


def _visible_text_except_secret(page: QWidget) -> Iterable[str]:
    for widget in page.findChildren(QWidget):
        if widget is getattr(page, "api_key_edit", None):
            continue
        if widget is getattr(page, "plantnet_api_key_edit", None):
            continue
        for attribute in ("text", "toolTip", "accessibleName", "placeholderText"):
            value = getattr(widget, attribute, lambda: "")()
            if isinstance(value, str):
                yield value


def test_td_ui_qpb_000_wizard_uses_required_minimum_and_recommended_initial_size():
    """FR-UI-QPB-001; AC-UI-QPB-001/003 and C-UI-QPB-006."""
    instance = ProjectBuilderWizard()
    assert instance.minimumSize() == MINIMUM_SIZE
    assert instance.size() == RECOMMENDED_SIZE
    assert instance.maximumSize().width() >= RECOMMENDED_SIZE.width()
    assert instance.maximumSize().height() >= RECOMMENDED_SIZE.height()
    assert instance.maximumSize().width() <= SUPPORTED_MAX_TARGET.width()
    assert instance.maximumSize().height() <= SUPPORTED_MAX_TARGET.height()
    instance.close()


def test_td_ui_qpb_001_all_seven_pages_have_scroll_viewport_above_native_bar(wizard):
    """AC-UI-QPB-001/002/003/006 and FR-UI-QPB-001/002/003/004/006."""
    assert wizard.minimumSize() == MINIMUM_SIZE
    assert wizard.sizeHint().width() <= wizard.maximumWidth()
    assert wizard.maximumWidth() <= SUPPORTED_MAX_TARGET.width()
    assert wizard.maximumHeight() <= SUPPORTED_MAX_TARGET.height()

    for page_index, page_type in enumerate(PAGE_TYPES):
        page = _show_page(wizard, page_index)
        assert isinstance(page, page_type)
        viewport = _page_scroll_area(page)
        assert viewport.widgetResizable() is True
        assert viewport.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert viewport.sizePolicy().horizontalPolicy() in (
            QSize.Policy.Expanding,
            QSize.Policy.MinimumExpanding,
        )
        assert viewport.sizePolicy().verticalPolicy() in (
            QSize.Policy.Expanding,
            QSize.Policy.MinimumExpanding,
        )

        native_buttons = _visible_native_buttons(wizard)
        assert native_buttons, "the native QWizard navigation bar must remain visible"
        viewport_rect = _mapped_rect(viewport, wizard)
        first_button_top = min(_mapped_rect(button, wizard).top() for button in native_buttons)
        assert viewport_rect.bottom() <= first_button_top
        assert all(_mapped_rect(button, wizard).bottom() <= wizard.height() for button in native_buttons)
        _assert_no_layout_sibling_overlap(page, wizard)


def test_td_ui_qpb_002_page_and_content_layout_policies_are_explicit(wizard):
    """FR-UI-QPB-003/004/007/008/009/010; AC-UI-QPB-001/002."""
    for page_index in range(len(PAGE_TYPES)):
        page = _show_page(wizard, page_index)
        outer = page.layout()
        assert outer is not None
        margins = outer.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == EXPECTED_MARGINS
        assert outer.spacing() == EXPECTED_OUTER_SPACING
        viewport = _page_scroll_area(page)
        viewport_index = next(
            index for index in range(outer.count()) if outer.itemAt(index).widget() is viewport
        )
        assert outer.stretch(viewport_index) == 1
        content = viewport.widget()
        assert content is not None
        assert content.maximumHeight() >= 1_000_000
        assert content.sizePolicy().verticalPolicy() == QSize.Policy.Fixed
        assert content.sizePolicy().horizontalPolicy() in (
            QSize.Policy.Expanding,
            QSize.Policy.MinimumExpanding,
        )
        content_layout = content.layout()
        assert content_layout is not None
        assert content_layout.spacing() == EXPECTED_OUTER_SPACING
        assert content_layout.alignment() & Qt.AlignmentFlag.AlignTop
        for group in page.findChildren(wizard_module.QGroupBox):
            assert group.sizePolicy().verticalPolicy() == QSize.Policy.Fixed


def test_td_ui_qpb_003_minimum_controls_and_long_text_are_not_compressed(wizard):
    """FR-UI-QPB-005/008/009/010; AC-UI-QPB-001/010/020/030/031."""
    for page_index in range(len(PAGE_TYPES)):
        page = _show_page(wizard, page_index)
        for control in _interactive_descendants(page):
            assert control.focusPolicy() != Qt.FocusPolicy.NoFocus, repr(control)
            minimum_height = 96 if isinstance(control, QPlainTextEdit) else 34
            assert control.height() >= minimum_height, (
                f"interactive control was compressed below its clickable minimum: {control!r} "
                f"height={control.height()} minimum={minimum_height}"
            )
            if isinstance(control, (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox)):
                assert control.sizePolicy().verticalPolicy() == QSize.Policy.Fixed
        for label in page.findChildren(QLabel):
            if not label.isVisible() or not label.wordWrap():
                continue
            required_height = label.heightForWidth(max(1, label.width()))
            if required_height > 0:
                assert label.height() >= required_height
                if label.property("survey_type_description"):
                    assert label.height() <= required_height + EXPECTED_OUTER_SPACING, (
                        "survey-type explanatory text must stay at its content height; spare "
                        "page space belongs below the final item, not below each choice"
                    )

    description = wizard.page(0).description_edit
    assert description.minimumHeight() >= 96


def test_td_ui_qpb_004_vworld_online_and_offline_controls_remain_reachable_and_secret(wizard):
    """FR-UI-QPB-011--014; AC-UI-QPB-010--014 and C-UI-QPB-002."""
    page = _show_page(wizard, 3)
    assert isinstance(page, ConnectivityBasemapPage)
    for mode_radio in (page.online_radio, page.offline_radio):
        mode_radio.setChecked(True)
        _process_layout()
        assert page.api_key_group.isVisible()
        assert page.api_key_edit.isVisible()
        assert page.layer_combo.isVisible()
        assert page._refresh_layers_button.isVisible()
        assert page.remember_checkbox.isVisible()
        assert page.credential_status_label.isVisible()
        if mode_radio is page.online_radio:
            assert page.consent_checkbox.isVisible()
            assert page.consent_disclosure_label.isVisible()
            assert not page.offline_key_usage_label.isVisible()
        else:
            assert page.offline_key_usage_label.isVisible()
            assert not page.consent_checkbox.isVisible()
            assert not page.consent_disclosure_label.isVisible()

    secret = "VWORLD-UI-SECRET-DO-NOT-LEAK"
    page.api_key_edit.setText(secret)
    assert page.api_key_edit.echoMode() == QLineEdit.EchoMode.Password
    assert secret not in "\n".join(_visible_text_except_secret(page))
    page.layer_status_label.setText("레이어 목록을 불러오지 못했습니다. " * 30)
    _process_layout()
    assert page.layer_status_label.height() >= page.layer_status_label.heightForWidth(
        max(1, page.layer_status_label.width())
    )
    _assert_no_layout_sibling_overlap(page, wizard)


def test_td_ui_qpb_005_plantnet_and_reference_group_remain_scrollable_and_distinct(wizard, monkeypatch):
    """FR-UI-QPB-015--021; AC-UI-QPB-020--023 and AC-UI-QPB-030--036."""
    candidate_path = "/tmp/fieldbuild-canonical.xlsx"
    monkeypatch.setattr(
        wizard_module.canonical_reference,
        "inspect_ktsn_source_candidates",
        lambda *_args, **_kwargs: {
            "recommended_filename": "2025년 국가생물종목록_v1.0.xlsx",
            "candidates": [
                {
                    "path": candidate_path,
                    "filename": "2025년 국가생물종목록_v1.0.xlsx",
                    "source_kind": "bundled_candidate",
                    "validation_status": "valid",
                    "sheet_name": "국가생물종지식정보시스템",
                    "header_rows": [4, 5],
                    "sample_rows": [
                        {
                            "status": "accepted",
                                "korean_name": f"긴 설명 샘플 {index} " + "가나다라마바사" * 12,
                                "scientific_name": "Plantus testensis " + "longus " * 18,
                            "ktsn": str(123456789 + index),
                        }
                        for index in range(12)
                    ],
                }
            ],
        },
    )
    candidate = wizard_module.canonical_reference.inspect_ktsn_source_candidates("")["candidates"][0]
    monkeypatch.setattr(
        wizard_module.canonical_reference, "inspect_ktsn_source_candidates",
        lambda *a, **k: {"upload": candidate},
    )
    monkeypatch.setattr(wizard_module, "_get_open_file_name", lambda *a, **k: (candidate_path, ""))
    page = _show_page(wizard, 4)
    page._browse_reference_source()
    assert isinstance(page, IdentificationTogglePage)
    assert page.plantnet_api_key_edit.echoMode() == QLineEdit.EchoMode.Password
    page.enable_checkbox.setChecked(True)
    _process_layout()
    assert page.plantnet_group.isVisible()
    assert page.plantnet_consent_disclosure_label.isVisible()
    assert page.plantnet_consent_checkbox.isVisible()
    assert page.plantnet_remember_checkbox.isVisible()
    assert page.plantnet_credential_status_label.isVisible()
    assert page.reference_source_preview.minimumHeight() == 40
    assert page.reference_source_preview.maximumHeight() == 40
    assert (
        page.reference_source_preview.verticalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    assert page.reference_source_preview.count() == 1
    candidate_item = page.reference_source_preview.item(0)
    assert candidate_item.text() == "2025년 국가생물종목록_v1.0.xlsx"
    page._select_reference_candidate(candidate_item)
    assert page.reference_sheet_preview.isVisible()
    assert page.reference_sheet_preview.item(0, 1).text().startswith("긴 설명 샘플")

    secret = "PLANTNET-UI-SECRET-DO-NOT-LEAK"
    page.plantnet_api_key_edit.setText(secret)
    assert secret not in "\n".join(_visible_text_except_secret(page))
    page.plantnet_consent_checkbox.setChecked(True)
    page.plantnet_remember_checkbox.setChecked(False)
    assert page.plantnet_consent_checkbox.isChecked()
    assert not page.plantnet_remember_checkbox.isChecked()
    page.plantnet_remember_checkbox.setChecked(True)
    assert page.plantnet_consent_checkbox.isChecked()
    assert page.plantnet_remember_checkbox.isChecked()


def test_td_ui_qpb_006_excel_candidate_keyboard_activation_validates_selection(wizard, monkeypatch):
    """Selecting a valid uploaded candidate is sufficient; no second confirmation button."""
    candidate_path = str(
        Path(__file__).resolve().parents[2] / "resources/samples/taxonomy_sample.xlsx"
    )
    monkeypatch.setattr(wizard_module, "_get_open_file_name", lambda *a, **k: (candidate_path, ""))
    page = _show_page(wizard, 4)
    page._browse_reference_source()
    assert page.isComplete()
    selected = page.canonical_reference_config()
    preview = page.reference_source_preview
    preview.setCurrentRow(0)
    preview.setFocus()
    for key in (Qt.Key.Key_Enter, Qt.Key.Key_Space):
        QTest.keyClick(preview, key)
        _process_layout()
        assert page.reference_source_path_edit.text() == candidate_path
        assert page.isComplete() and page.canonical_reference_config() == selected
    assert all("선택한 참조 자료 확인" not in b.text() for b in page.findChildren(QPushButton))


def test_td_ui_qpb_006_user_upload_preserves_path_and_source_kind_and_recovery_controls(
    wizard, monkeypatch, tmp_path
):
    """AC-UI-QPB-032/034/035; C-UI-QPB-003/004."""
    upload_path = tmp_path / ("very-long-" * 12 + "-참조.xlsx")
    monkeypatch.setattr(
        wizard_module,
        "_get_open_file_name",
        lambda *_args, **_kwargs: (str(upload_path), "Excel workbook (*.xlsx)"),
    )
    monkeypatch.setattr(
        wizard_module.canonical_reference,
        "inspect_ktsn_source_candidates",
        lambda *_args, **kwargs: (
            {
                "upload": {
                    "filename": upload_path.name,
                    "source_kind": "user_upload",
                    "validation_status": "invalid",
                    "sheet_name": None,
                    "header_rows": [],
                    "sample_rows": [
                        {
                            "status": "rejected",
                            "korean_name": f"업로드 샘플 {index} " + "가나다라마바사" * 12,
                            "scientific_name": "Plantus uploadensis " + "uploadus " * 18,
                            "ktsn": str(987654320 + index),
                        }
                        for index in range(12)
                    ],
                    "error_message": "필수 시트/헤더를 찾지 못했습니다. " * 12,
                }
            }
            if kwargs.get("upload_path")
            else {"candidates": []}
        ),
    )
    page = _show_page(wizard, 4)
    assert isinstance(page, IdentificationTogglePage)
    page._browse_reference_source()
    _process_layout()
    assert page.reference_source_path_edit.text() == str(upload_path)
    assert page._selected_reference_candidate["source_kind"] == "user_upload"
    assert page.reference_source_preview.count() == 1
    upload_item = page.reference_source_preview.item(0)
    assert upload_item.text() == upload_path.name
    assert page.reference_sheet_preview.isVisible()
    assert page.reference_sheet_preview.item(0, 1).text().startswith("업로드 샘플")
    assert any("사용자 .xlsx 업로드" in button.text() for button in page.findChildren(QPushButton))
    assert all("선택한 참조 자료 확인" not in b.text() for b in page.findChildren(QPushButton))
    assert page._confirmed_reference_source is None
    _assert_no_layout_sibling_overlap(page, wizard)


def test_td_ui_qpb_007_keyboard_tab_shift_tab_enter_space_and_names(wizard):
    """FR-UI-QPB-020; AC-UI-QPB-005/006/013/022 and C-UI-QPB-005."""
    for page_index in range(len(PAGE_TYPES)):
        page = _show_page(wizard, page_index)
        controls = _interactive_descendants(page)
        assert controls, type(page).__name__
        assert all(_has_semantic_name(control) for control in controls), (
            f"every interactive control needs a Qt-visible accessible name: "
            f"{[control for control in controls if not _has_semantic_name(control)]!r}"
        )

        first = controls[0]
        first.setFocus()
        seen: set[int] = set()
        native_buttons = _visible_native_buttons(wizard)
        for _ in range(len(controls) * 3 + 8):
            focused = QApplication.focusWidget()
            if focused in controls or focused in native_buttons:
                seen.add(id(focused))
            if focused is None:
                break
            QTest.keyClick(focused, Qt.Key.Key_Tab)
            _process_layout()
        assert {id(control) for control in controls}.issubset(seen), (
            f"Tab traversal skipped interactive controls on {type(page).__name__}: "
            f"missing={[control for control in controls if id(control) not in seen]!r}"
        )
        assert {id(button) for button in native_buttons}.issubset(seen), (
            f"Tab traversal did not reach native QWizard buttons on {type(page).__name__}"
        )

        last = controls[-1]
        last.setFocus()
        QTest.keyClick(last, Qt.Key.Key_Backtab)
        _process_layout()
        assert QApplication.focusWidget() is not None
        assert QApplication.focusWidget() in controls or QApplication.focusWidget() in _visible_native_buttons(wizard)

    # Space activates the existing checkbox behavior; Enter is covered by the candidate test and
    # native QWizard buttons are intentionally included in the traversal assertions above.
    page = _show_page(wizard, 3)
    page.online_radio.setChecked(True)
    page.consent_checkbox.setFocus()
    original = page.consent_checkbox.isChecked()
    QTest.keyClick(page.consent_checkbox, Qt.Key.Key_Space)
    assert page.consent_checkbox.isChecked() is not original


@pytest.mark.parametrize("scale_factor", (1.0, 1.25, 1.5, 2.0))
def test_td_ui_qpb_008_logical_geometry_at_configured_qt_dpi_scale(wizard, scale_factor):
    """AC-UI-QPB-004/005; C-UI-QPB-006.

    Qt's scale factor is process-global, so changing it after QApplication construction would not
    test the display system. Each parameter is therefore an opt-in headless run: invoke pytest
    with ``QT_SCALE_FACTOR=<value>`` (or the equivalent macOS display setting) to execute that
    case. The separate acceptance manual smoke below covers Cocoa's actual display pipeline.
    """
    configured = os.environ.get("QT_SCALE_FACTOR")
    if configured is None:
        pytest.skip("run this case in a separate process with QT_SCALE_FACTOR set")
    try:
        actual_configured = float(configured)
    except ValueError:
        pytest.skip(f"QT_SCALE_FACTOR is not numeric: {configured!r}")
    if actual_configured != pytest.approx(scale_factor):
        pytest.skip(f"this process is configured for QT_SCALE_FACTOR={actual_configured}")

    assert QApplication.primaryScreen() is not None
    assert QApplication.primaryScreen().devicePixelRatio() == pytest.approx(scale_factor, rel=0.05)
    for page_index in range(len(PAGE_TYPES)):
        _show_page(wizard, page_index)
        _assert_no_layout_sibling_overlap(wizard.currentPage(), wizard)
        assert _visible_native_buttons(wizard)
        assert wizard.width() >= MINIMUM_SIZE.width()
        assert wizard.height() >= MINIMUM_SIZE.height()


def test_td_ui_qpb_009_resize_round_trip_retains_state_and_bar(wizard):
    """FR-UI-QPB-006; AC-UI-QPB-003/006."""
    page = _show_page(wizard, 4)
    assert isinstance(page, IdentificationTogglePage)
    page.enable_checkbox.setChecked(True)
    page.plantnet_api_key_edit.setText("retained-only-in-memory-test-value")
    for size in (MINIMUM_SIZE, RECOMMENDED_SIZE, SUPPORTED_MAX_TARGET):
        target = QSize(
            min(size.width(), wizard.maximumWidth()), min(size.height(), wizard.maximumHeight())
        )
        wizard.resize(target)
        _process_layout()
        assert page.enable_checkbox.isChecked()
        assert page.plantnet_api_key_edit.text() == "retained-only-in-memory-test-value"
        assert _visible_native_buttons(wizard)
        _assert_no_layout_sibling_overlap(page, wizard)


def test_td_ui_qpb_010_logo_and_existing_page_functionality_remain_present(wizard):
    """C-UI-QPB-001; regression guard for existing logo/page behavior."""
    first_page = wizard.page(0)
    logo = first_page.findChild(QLabel, "fieldbuild_kit_logo_banner")
    assert logo is not None
    assert not logo.pixmap().isNull()
    assert wizard.page(1).findChildren(QRadioButton)
    assert wizard.page(2).findChildren(QRadioButton)
    assert wizard.page(3).findChildren(QRadioButton)
    assert wizard.page(5).findChildren(QRadioButton)
    assert wizard.page(6).findChildren(QPushButton)
