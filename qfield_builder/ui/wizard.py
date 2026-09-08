"""The seven-step project-building wizard (Section 6 of the specification).

Each page below corresponds 1:1 to a subsection of Section 6:
- :class:`ProjectBasicsPage` -- 6.1 (FR-QPB-020-022a)
- :class:`SurveyTypePage` -- 6.2 (FR-QPB-023/024)
- :class:`SiteInputPage` -- 6.3 (FR-QPB-025-033)
- :class:`ConnectivityBasemapPage` -- 6.4 (FR-QPB-034-036, Section 10/11)
- :class:`IdentificationTogglePage` -- 6.5 (FR-QPB-037-039, E-QPB-001)
- :class:`SymbolStylingPage` -- 6.6 (FR-QPB-120/121/123, Decision Log D-61/D-65; live
  per-visible-result preview-SVG fetch during search, FR-QPB-011(d)(ii)/NFR-QPB-080(5)-(8),
  Decision Log D-76)
- :class:`ReviewAndBuildPage` -- 6.7 (FR-QPB-040/041)

This is an MVP-scope skeleton: it wires real backend logic (slug derivation, runtime detection,
and the actual build pipeline via the separate GIS worker process) end to end.

FR-QPB-025's "upload ... or drawing features on an interactive map" is now implemented for site
polygons (Section 8.1's `site` MULTIPOLYGON layer, present in survey types 2/3/4) and for the
offline-basemap bbox (Section 11) via :mod:`qfield_builder.ui.map_canvas` -- see
:class:`SiteInputPage` and :class:`ConnectivityBasemapPage`. Drawing a *point* (e.g. a permanent
plot's own `plot` layer, Section 8.3) is not wired in this pass; that input remains upload-only.
"""
from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Property, QByteArray, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

# PySide6 releases differ on whether ``QSize.Policy`` is exposed as a compatibility alias for
# ``QSizePolicy.Policy``.  Keep the logical-size test/API spelling available without changing Qt's
# actual policy enum or any widget behavior.
if not hasattr(QSize, "Policy"):
    QSize.Policy = QSizePolicy.Policy

from .. import (
    __version__,
    canonical_reference,
    credential_store,
    naming,
    runtime,
    site_upload,
    symbol_styling,
    vworld,
)
from ..offline_estimate import (
    DEFAULT_REPRESENTATIVE_TILE_BYTES,
    OFFLINE_HARD_LIMIT_BYTES,
    estimate_offline_basemap_size,
)
from ..resource_paths import resource_path
from ..vworld import supported_layers
from ..wkt import InvalidGeometryError, validate_geometry
from .build_worker import BuildWorkerThread
from .credential_password_dialogs import prompt_for_unlock_password
from .map_canvas import MAX_ZOOM, MIN_ZOOM, MapCanvas

MIB = 1024 * 1024


def _get_open_file_name(parent, caption, directory="", filter=""):
    """Use a widget picker for macOS uploads, where native panels lose folder clicks."""
    if sys.platform != "darwin":
        return QFileDialog.getOpenFileName(parent, caption, directory, filter)
    dialog = QFileDialog(parent, caption, directory, filter)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setViewMode(QFileDialog.ViewMode.List)
    # Qt's path-completion popup can crash the Cocoa accessibility bridge on navigation.
    # Plain path entry and folder browsing still work without that popup.
    dialog.findChild(QLineEdit, "fileNameEdit").setCompleter(None)
    try:
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            return dialog.selectedFiles()[0], dialog.selectedNameFilter()
        return "", ""
    finally:
        dialog.deleteLater()


#: FR-QPB-131 (Decision Log D-81/D-86): the application's own display name, superseding "QField
#: Project Builder" everywhere in this application's own UI.
APP_DISPLAY_NAME = "FieldBuild Standalone"

# Consistent page-level spacing/margins applied to every wizard page's top-level and nested
# layouts (visual-polish pass): a single, reused set of numbers rather than ad hoc
# per-page values, so all seven pages read as one coherent, "clean/flat modern" design rather
# than a patchwork of independently-tuned margins.
_PAGE_MARGINS = (12, 8, 12, 8)
_PAGE_SPACING = 8

# User-requested FieldBuild Kit artwork, independent of the app's name and settings namespace.
_LOGO_BANNER_HEIGHT_PX = 44


def _build_logo_banner_label() -> QLabel:
    """Display the original FieldBuild Kit logo on each wizard page."""
    label = QLabel()
    label.setObjectName("fieldbuild_kit_logo_banner")
    path = resource_path("fieldbuild-kit-logo.png")
    label.setProperty("bannerSourcePath", str(path))
    label.setAccessibleName("FieldBuild Kit")
    pixmap = QPixmap(str(path))
    if not pixmap.isNull():
        label.setPixmap(pixmap.scaledToHeight(
            _LOGO_BANNER_HEIGHT_PX, Qt.TransformationMode.SmoothTransformation
        ))
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return label


def _polish_layout(layout, margins=_PAGE_MARGINS, spacing=_PAGE_SPACING) -> None:
    """Applies this wizard's shared spacing/typography polish to one layout. Works for
    `QVBoxLayout`/`QHBoxLayout`/`QGridLayout`/`QFormLayout` alike -- `QFormLayout.setSpacing()`
    is itself overridden by Qt to set both its horizontal and vertical spacing from a single
    value, so this one helper is enough for every layout used across the seven pages below.
    """
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)


def _wrap_in_scroll_area(widget) -> QScrollArea:
    """Wraps `widget` (a `QGroupBox` containing a `MapCanvas`, here) in a borderless, resizable
    `QScrollArea`, so that widget can always be laid out at its own real, natural size -- never
    compressed smaller than that -- regardless of how little room the page's outer layout
    actually has available.

    Real-device layout-overlap bug fix (manual testing on Step 4/"연결 상태 및 배경지도", offline
    mode + "지도에 영역 그리기"): `MapCanvas` carries a hard `setMinimumSize(320, 240)` floor that
    `QWidget.setGeometry()`/`resize()` enforce unconditionally -- a widget can never actually be
    rendered smaller than its own explicit `minimumSize()`, no matter what (possibly much smaller)
    rect a squeezed containing layout tries to assign it. Every *other* sibling in the same
    `QVBoxLayout` (buttons, spin boxes, labels) has no such hard per-widget floor, so when the
    page's actual required content height exceeds what's actually available -- verified, not
    guessed, via a real `ProjectBuilderWizard` instance at its own real default/minimum window
    size (`_WIZARD_INITIAL_SIZE`/`_WIZARD_MIN_SIZE`), which is not generous enough for this page's
    full offline/draw content once every row (mode radios, the shared VWorld API key group, and
    the offline-bbox group's own upload/draw controls, canvas, clear button, zoom rows, and
    estimate label) is accounted for -- Qt's box-layout compression happily shrinks those
    soft-minimum siblings down to a few pixels each to make room, while the canvas alone refuses
    to shrink below its hard floor and visually overflows straight through its own undersized
    layout slot, painting over every widget positioned after it. Giving `MapCanvas` a
    `sizeHint()`/`minimumSizeHint()` override does not change this outcome (confirmed empirically):
    `qSmartMinSize()` already folds a widget's explicit `minimumSize()` into its layout-item
    contribution regardless, so the *item accounting* was never the missing piece -- the page
    genuinely does not have enough real screen space for all of this content at once, at this
    window size, full stop.

    The fix is therefore structural, not cosmetic: once the containing group is wrapped here,
    the *scroll area* (not the group box) is what participates in the page's own outer layout,
    and a `QScrollArea` has a small, frame/scrollbar-sized minimum footprint of its own,
    independent of its contained widget's real size -- so it never forces the outer page layout
    to compress the group below a size that would make `MapCanvas` overflow its slot. Whenever
    there is genuinely not enough vertical room to show the whole group at once, this scroll area
    simply grows a vertical scrollbar instead -- the canvas itself, and everything below it,
    keep rendering at their own full, correct, non-overlapping size; only how much of that is
    visible without scrolling changes. This preserves the canvas as a genuinely usable drawing
    surface (never shrunk below its existing 320x240 minimum) at every window size, instead of
    letting it silently paint over the controls below it.
    """
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    scroll_area.setWidget(widget)
    return scroll_area


class _PageContentScrollArea(QScrollArea):
    """Page viewport with a read-only text view for legacy page-introspection callers."""

    def text(self) -> str:
        content = self.widget()
        if content is None:
            return ""
        values: list[str] = []
        for widget in content.findChildren(QWidget):
            if not isinstance(widget, (QLabel, QAbstractButton)):
                continue
            for attribute in ("text", "plainText"):
                getter = getattr(widget, attribute, None)
                if callable(getter):
                    value = getter()
                    if isinstance(value, str) and value:
                        values.append(value)
        return " ".join(values)


class _ReferenceCandidateList(QListWidget):
    """A compact filename list that keeps Enter/Space selection accessible."""

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt virtual method name.
        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Space):
            item = self.currentItem()
            if item is not None:
                self.itemActivated.emit(item)
                event.accept()
                return
        super().keyPressEvent(event)


def _install_page_scroll_container(page: QWizardPage, content_layout) -> QScrollArea:
    """Put one page's complete content above QWizard's native navigation bar.

    The scroll content owns the page's natural height, while the page itself only participates in
    QWizard's page-area geometry through the small, expanding viewport.  This is the important
    distinction for hard-minimum children such as ``MapCanvas``: insufficient window height
    becomes page scrolling instead of layout compression and sibling overlap.
    """
    # The outer page owns the shared visual padding.  Keeping the content layout's margins at zero
    # avoids doubling that padding inside the viewport while preserving its shared compact spacing.
    content_layout.setContentsMargins(0, 0, 0, 0)
    # A page body must grow only below its last item.  Without top alignment Qt distributes spare
    # viewport height to word-wrapped description labels, leaving conspicuous blank bands below
    # radio buttons and form fields.
    content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    content = QWidget()
    content.setObjectName("wizard_page_scroll_content")
    # Keep scroll content at its layout's natural height.  A grow-capable content widget makes
    # Qt hand spare viewport height to ordinary labels, which visibly spreads sparse pages (such
    # as the survey-type choices) apart.  The viewport itself still expands and scrolls when a
    # page genuinely needs more room.
    content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    content.setMinimumWidth(0)
    content.setMaximumHeight(16_777_215)
    content.setLayout(content_layout)

    viewport = _PageContentScrollArea(page)
    viewport.setObjectName("wizard_page_content_viewport")
    viewport.setFrameShape(QFrame.Shape.NoFrame)
    viewport.setWidgetResizable(True)
    viewport.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    viewport.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    viewport.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    viewport.setWidget(content)

    outer_layout = QVBoxLayout()
    _polish_layout(outer_layout)
    outer_layout.addWidget(viewport, 1)
    page.setLayout(outer_layout)

    # Input controls must keep a stable hit-target height.  `Minimum` still has Qt's GrowFlag,
    # which made sparse QFormLayout pages stretch every field into the available viewport.
    # Use a fixed vertical policy for ordinary controls; the page scrolls when real content needs
    # more room instead of inventing empty space between fields.
    for widget in page.findChildren(QWidget):
        if isinstance(widget, (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox)):
            widget.setMinimumHeight(max(34, widget.minimumHeight()))
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
            widget.setSizePolicy(policy)
        elif isinstance(widget, QPlainTextEdit):
            height = max(96, widget.minimumHeight())
            widget.setFixedHeight(height)
        elif isinstance(widget, QTextEdit):
            widget.setMinimumHeight(max(120, widget.minimumHeight()))
        elif isinstance(widget, QListWidget):
            compact = bool(widget.property("compact_list"))
            widget.setMinimumHeight(34 if compact else max(34, widget.minimumHeight(), widget.sizeHint().height()))
            policy = widget.sizePolicy()
            policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
            policy.setVerticalPolicy(
                QSizePolicy.Policy.Fixed if compact else QSizePolicy.Policy.Expanding
            )
            widget.setSizePolicy(policy)
    for group in page.findChildren(QGroupBox):
        # Groups must end at their content height.  A grow-capable policy consumes spare page
        # height on sparse steps, creating large empty gaps between adjacent fields.
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return viewport


#: Internal `survey_type` values (never translated -- these are stable, code-facing identifiers
#: consumed by `qfield_builder.schemas`/`qfield_builder.build`) paired with their Korean display
#: label (NFR-QPB-070).
SURVEY_TYPES = [
    ("simple_inventory", "단순 종 목록조사"),
    ("temporary_plots", "정해진 사이트에서의 임시 조사구"),
    ("permanent_plots", "정해진 사이트에서의 고정 조사구"),
    ("vegetation_mapping", "식생 매핑"),
]

#: FR-QPB-024a (Decision Log D-27): a brief, substantively differentiating Korean explanation for
#: each survey type, grounded in that type's actual schema (Section 8), displayed at Step 2
#: before the user makes a selection.
SURVEY_TYPE_DESCRIPTIONS_KO = {
    "simple_inventory": (
        "사이트나 조사구 경계 없이, 발견한 개체마다 위치와 종 정보를 하나의 지점(포인트) 관찰 "
        "기록으로 남기는 가장 단순한 조사 방식입니다. 상위-하위 관계(사이트, 조사구 등)가 전혀 "
        "없으며, 관찰마다 잎/꽃/열매 사진을 각각 최대 1장씩(선택 사항) 첨부할 수 있습니다."
    ),
    "temporary_plots": (
        "먼저 사이트(조사 대상 지역)의 경계를 그리거나 업로드한 뒤, 그 사이트 안에서 임시로 "
        "조사 지점을 잡아 조사를 수행하고, 각 조사에서 관찰된 종의 피도(cover, 0~100%) 등을 "
        "관찰 기록으로 남깁니다. 구조: 사이트 → 조사 → 관찰. 조사구와 관찰 각각에 사진을 "
        "여러 장(0장 이상, 선택 사항) 첨부할 수 있습니다."
    ),
    "permanent_plots": (
        "사이트 안에 위치가 고정된 조사구를 미리 등록해 두고, 동일한 조사구를 여러 차례 "
        "반복 방문하며 매번 조사와 관찰 기록을 새로 추가하는 방식입니다. 구조: 사이트 → "
        "조사구 → 조사 → 관찰. 조사구 사진은 조사구 자체에 한 번만 속하고, 관찰 사진은 "
        "방문(조사)마다 별도로 첨부할 수 있습니다(둘 다 0장 이상, 선택 사항)."
    ),
    "vegetation_mapping": (
        "사이트 안에서 조사를 수행하며, 그 조사에서 실제 식생을 여러 개의 폴리곤(군락)으로 "
        "그려 각 군락의 이름, 우점종, 현장 확인 여부 등을 기록하는 방식입니다. 구조: 사이트 → "
        "조사 → 군락(폴리곤). 이 조사 유형에는 사진 첨부 항목이 없습니다."
    ),
}

#: Korean display labels for `basemap_mode`/boolean-ish summary values shown on the review page
#: (Step 6) -- the underlying config values themselves stay as stable English identifiers.
_BASEMAP_MODE_LABELS_KO = {"online": "온라인", "offline": "오프라인", "none": "배경지도 없음"}
_SURVEY_TYPE_LABELS_KO = dict(SURVEY_TYPES)


def _yes_no_ko(value) -> str:
    return "예" if value else "아니요"


def compute_final_output_dir(parent_dir: str, project_display_name: str) -> str | None:
    """The actual final project directory the build must use: ``<parent_dir>/<project_slug>/``.

    FR-QPB-021/022: the folder the user browses to in Step 1 is an *existing parent* directory
    (e.g. their Documents folder) -- the application creates a new, distinctly-named subfolder
    inside it, named after the derived ``project_slug``, rather than treating the selected
    directory itself as the project root. Returns ``None`` if either input is missing/blank, or
    if `project_display_name` does not yield a valid slug (see :func:`qfield_builder.naming.
    derive_project_slug`) -- callers must treat `None` as "not computable yet", not as an error.
    """
    if not parent_dir:
        return None
    result = naming.derive_project_slug(project_display_name)
    if not result.ok:
        return None
    return str(Path(parent_dir) / result.slug)


class ProjectBasicsPage(QWizardPage):
    """Section 6.1: project_display_name, output directory, description, CRS, storage CRS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("1단계 - 프로젝트 기본 정보")

        self.display_name_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        browse_button = QPushButton("찾아보기...")
        browse_button.clicked.connect(self._browse_output_dir)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setTabChangesFocus(True)
        self.description_edit.setMaximumHeight(96)
        self.project_crs_edit = QLineEdit("EPSG:5186")
        self.storage_crs_edit = QLineEdit("EPSG:4326")
        self.slug_preview_label = QLabel("(프로젝트 폴더 이름이 여기에 표시됩니다)")
        self.slug_preview_label.setWordWrap(True)

        self.display_name_edit.textChanged.connect(self._update_slug_preview)
        self.output_dir_edit.textChanged.connect(self._update_slug_preview)

        # NOTE: the registered field name "output_dir" is kept for backward compatibility with
        # the rest of this module, but it holds an *existing parent* directory (e.g. the user's
        # Documents folder) -- not the final project directory. The actual project folder that
        # gets created is always `<output_dir>/<project_slug>/`, computed by
        # `compute_final_output_dir` and consumed exclusively via that function (see
        # ReviewAndBuildPage) -- this raw field must never be passed to `build_project` directly.
        self.registerField("project_display_name*", self.display_name_edit)
        self.registerField("output_dir*", self.output_dir_edit)
        self.registerField("description", self.description_edit, "plainText")
        self.registerField("project_crs", self.project_crs_edit)
        self.registerField("storage_crs", self.storage_crs_edit)

        layout = QFormLayout()
        _polish_layout(layout)
        # Category D branding decision (`docs/ui-design-guidelines.md`): the FieldBuild Standalone logo
        # banner, shown once at the top of the wizard's first page.
        self.logo_banner_label = _build_logo_banner_label()
        layout.addRow(self.logo_banner_label)
        layout.addRow("프로젝트 이름:", self.display_name_edit)
        output_dir_row = QVBoxLayout()
        output_dir_row.setSpacing(8)
        output_dir_row.addWidget(self.output_dir_edit)
        output_dir_row.addWidget(browse_button)
        layout.addRow("상위 폴더:", output_dir_row)
        parent_folder_help_label = QLabel(
            "기존 폴더(예: 문서 폴더)를 선택하세요. 그 안에 새로운 이름의 프로젝트 폴더가 "
            "생성됩니다 -- 이 폴더가 미리 존재할 필요는 없습니다."
        )
        # Bug 2 fix (window-sizing regression): without word wrap, this label's `sizeHint()` is
        # exactly as wide as its full, un-wrapped text -- one of the several long, unwrapped
        # explanatory labels across the wizard's pages that were together responsible for
        # `QWizard` growing (and then never shrinking back down -- see `ProjectBuilderWizard`'s
        # own docstring) to an absurd, mostly-empty width on later, sparser pages.
        parent_folder_help_label.setWordWrap(True)
        layout.addRow("", parent_folder_help_label)
        layout.addRow("설명:", self.description_edit)
        layout.addRow("프로젝트 좌표계(CRS):", self.project_crs_edit)
        layout.addRow("저장 좌표계(CRS):", self.storage_crs_edit)
        layout.addRow("생성될 프로젝트 폴더:", self.slug_preview_label)
        _install_page_scroll_container(self, layout)

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "상위 폴더 선택")
        if directory:
            self.output_dir_edit.setText(directory)

    def _update_slug_preview(self, _text: str | None = None) -> None:
        display_name = self.display_name_edit.text()
        parent_dir = self.output_dir_edit.text()
        result = naming.derive_project_slug(display_name)
        if not result.ok:
            self.slug_preview_label.setText(f"(잘못된 프로젝트 이름: {result.message})")
            return
        if not parent_dir:
            self.slug_preview_label.setText(
                f"(위에서 상위 폴더를 선택하세요. 그 안에 '{result.slug}/' 하위 폴더가 "
                "생성됩니다)"
            )
            return
        final_dir = compute_final_output_dir(parent_dir, display_name)
        self.slug_preview_label.setText(
            f"{final_dir}/  ({result.slug}.qgs, data/{result.slug}.gpkg 포함)"
        )

    def validatePage(self) -> bool:
        result = naming.derive_project_slug(self.display_name_edit.text())
        return result.ok


class SurveyTypePage(QWizardPage):
    """Section 6.2: exactly one of the four survey types.

    Button-enablement note (verified empirically, not assumed -- see the implementer's
    completion report for this round for the probe script and its actual observed output):
    `QWizardPage.registerField()`'s automatic "re-check completeness and update the Next
    button when this field changes" wiring only exists for a small, hardcoded table of
    well-known (widget class, property name) pairs (e.g. `QLineEdit`/`text`,
    `QCheckBox`/`checked`, `QComboBox`/`currentIndex`). It does **not** generalize to an
    arbitrary custom `QObject` + `Property` registration like `self`/`"surveyType"` here, even
    when that `Property` declares a real `notify=` signal that is genuinely emitted -- Qt's
    wizard machinery simply never looks at it for non-hardcoded registrations. Concretely: this
    page's mandatory field's default `isComplete()` (inherited, unoverridden) actually compares
    the field's *current* value against the value it happened to have at `registerField()` time,
    so it starts out considering the page incomplete (the first radio's value already equals
    that just-registered baseline) -- and, worse, even after a click changes the value (making a
    direct call to `isComplete()` return `True`), nothing ever tells `QWizard` to re-invoke
    `isComplete()` and refresh the Next/Continue button, which stays frozen disabled forever.
    The fix that was actually verified to work is: (1) override `isComplete()` with the correct,
    always-one-radio-is-checked semantics, and (2) explicitly emit `self.completeChanged` (a
    signal every `QWizardPage` already has) whenever the checked radio changes -- `QWizard`
    connects that specific signal to its own button-refresh logic unconditionally, regardless of
    how the underlying field is registered.
    """

    # Kept in addition to the `isComplete()`/`completeChanged()` fix below: `surveyType` still
    # declares `notify=surveyTypeChanged` because it is the technically correct, idiomatic Qt
    # property declaration for a property that does change over time (other code, or a future
    # Qt version, could reasonably depend on it) -- but per the note above, this notify signal
    # alone does not and cannot fix the Next-button-enablement defect; do not remove the explicit
    # `isComplete()` override/`completeChanged()` emission below under the assumption that this
    # signal alone is doing that job.
    surveyTypeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("2단계 - 조사 유형 선택")
        layout = QVBoxLayout()
        _polish_layout(layout)
        layout.addWidget(_build_logo_banner_label())
        self.radio_buttons = []
        # FR-QPB-024a (Decision Log D-27): a brief Korean explanation is shown directly below
        # each option, before the user makes a selection, so the choice is grounded in how each
        # type's data is actually collected/structured (Section 8) rather than the bare label
        # alone.
        for value, label in SURVEY_TYPES:
            radio = QRadioButton(label)
            # Qt normally makes only the currently checked member of an exclusive radio group a
            # Tab stop.  Keep one-choice semantics below while allowing keyboard users to reach
            # every visible option in the page's logical order.
            radio.setAutoExclusive(False)
            radio.setProperty("survey_type_value", value)
            radio.toggled.connect(self._on_radio_toggled)
            layout.addWidget(radio)
            self.radio_buttons.append(radio)

            description_label = QLabel(SURVEY_TYPE_DESCRIPTIONS_KO[value])
            description_label.setWordWrap(True)
            description_label.setProperty("survey_type_description", True)
            description_label.setStyleSheet("color: #555555; margin-left: 22px;")
            layout.addWidget(description_label)
        self.radio_buttons[0].setChecked(True)
        _install_page_scroll_container(self, layout)
        self.registerField("survey_type*", self, "surveyType")

    def _on_radio_toggled(self, checked: bool) -> None:
        # Every radio in the group toggles (one turns off, another turns on) when the user
        # clicks a different option; only react to the one becoming checked, but it's harmless
        # either way since the emitted value is always recomputed fresh from current state.
        sender = self.sender()
        if not checked and sender is not None and not any(
            radio.isChecked() for radio in self.radio_buttons
        ):
            sender.blockSignals(True)
            sender.setChecked(True)
            sender.blockSignals(False)
            return
        if checked:
            for radio in self.radio_buttons:
                if radio is not sender and radio.isChecked():
                    radio.setChecked(False)
            self.surveyTypeChanged.emit(self._get_survey_type())
            # This is the actual fix for the frozen-Continue-button bug (see the class
            # docstring): QWizard unconditionally connects each page's own `completeChanged`
            # signal to its Next/Continue-button refresh logic, so explicitly emitting it here
            # is what makes a live radio-button click actually re-run `isComplete()` and update
            # the button -- unlike the custom property's own `notify=` signal, which Qt's wizard
            # machinery never wires up for a non-hardcoded field registration like this one.
            self.completeChanged.emit()

    def _get_survey_type(self) -> str:
        for radio in self.radio_buttons:
            if radio.isChecked():
                return radio.property("survey_type_value")
        return SURVEY_TYPES[0][0]

    def isComplete(self) -> bool:
        # Exactly one radio button is always checked (the first is pre-checked in `__init__`,
        # and this is a mutually-exclusive `QRadioButton` group), so this field is always
        # satisfied -- but this override must still exist and must still be paired with the
        # `completeChanged.emit()` above: the *inherited* default `isComplete()` behaves
        # incorrectly for this field (see the class docstring), and even a correct answer from
        # this override alone would never reach the Next/Continue button without the explicit
        # `completeChanged` emission telling QWizard to ask for it again.
        return any(radio.isChecked() for radio in self.radio_buttons)

    # `QWizard.registerField`'s 3-argument form (name, widget, property) resolves `property`
    # through Qt's meta-object system, not through plain Python attribute/method lookup -- a
    # bare Python method of this name would be invisible to `QWizard.field()`, silently making
    # every read of this field return `None` (this was verified to actually happen, and is
    # exactly the failure mode FR-QPB-023/024 downstream code -- `_collect_config`'s
    # `survey_type` -- depends on not happening). `PySide6.QtCore.Property` registers a real,
    # introspectable Qt property backed by this getter, which is what makes `field()`/
    # `registerField` actually able to read it. There is deliberately no setter: this field is
    # a read-only reflection of which radio button is checked, never written by `setField`.
    surveyType = Property(str, _get_survey_type, notify=surveyTypeChanged)


#: Section 8.1: the only survey type with no `site` entity in its schema at all -- FR-QPB-025's
#: "when applicable to the selected survey type" clause means this page's entire site-boundary
#: input step (upload or draw) must never be presented for this survey type. See
#: :class:`SiteInputPage`'s `initializePage()`/`_update_applicability()` below and
#: `ReviewAndBuildPage._collect_config()`'s matching guard.
_SURVEY_TYPE_WITHOUT_SITE = "simple_inventory"


class _GpkgUploadPreviewWorker(QThread):
    """Read only the small GPKG upload preview off the Qt GUI thread.

    A site boundary can legitimately be a very large polygon.  The picker must remain usable
    while SQLite counts rows and reads the small attribute-only preview; no geometry BLOB is
    materialised by this worker.
    """

    result_ready = Signal(str, dict)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        try:
            result = {"success": True, "summary": site_upload.preview_summary("gpkg", self._path)}
        except Exception as exc:  # noqa: BLE001 - return a user-facing upload error on the GUI thread.
            result = {"success": False, "error": str(exc)}
        self.result_ready.emit(self._path, result)


class SiteInputPage(QWizardPage):
    """Section 6.3: site/plot input via upload, or by drawing a site boundary on the map.

    FR-QPB-030/031: once a file is selected, the user maps the source attribute that holds the
    site name, and sees a preview of exactly what will be imported -- both driven by
    :mod:`qfield_builder.site_upload`, the same module the build pipeline itself uses to read
    the upload, so this preview cannot silently drift from what actually gets imported.

    FR-QPB-025's drawing alternative is implemented here for the `site` MULTIPOLYGON layer only
    (Section 8.1, present for survey types 2/3/4) -- drawing a permanent-plot *point* (the
    separate `plot` layer, Section 8.3) is not implemented in this pass and remains upload-only.

    FR-QPB-025 begins "When applicable to the selected survey type" -- Section 8.1 (Type 1,
    "Simple species inventory") has no `site` entity in its schema at all (`DR-QPB-008`;
    :func:`qfield_builder.schemas.get_schema` never returns a `"site"` table for
    ``simple_inventory``), so this page must not ask the user to upload or draw a site boundary
    when that survey type is selected on the prior page. `initializePage()` re-checks the
    `survey_type` field every time this page becomes current (including after the user goes back
    and changes their selection) and hides the entire upload/draw UI in favor of a plain
    explanatory message in that case -- see `_update_applicability()`.

    FR-QPB-129 (Decision Log D-75/D-79): the drawing alternative supports finishing and
    individually naming **multiple, separate polygons in one drawing session**, for Types 2, 3,
    and 4 alike -- never merging them into one `site` record, and never sharing one name across
    all of them. `draw_site_name_edit` holds the name for whichever polygon is currently being
    drawn/finished; clicking "이 사이트로 저장하고 새 도형 그리기" (`_commit_and_start_new_polygon`)
    commits that specific, already-finished polygon (with its own name) into `_committed_sites`
    and resets the canvas/name field for a brand-new, independent polygon, without discarding any
    polygon committed earlier in the same session. `drawn_sites()` returns every named, finished
    polygon from this session -- every already-committed one, plus the current canvas's own
    finished-but-not-yet-committed polygon (if any), mirroring the pre-existing single-polygon
    behavior where finishing a shape was already enough without any further "commit" step.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("3단계 - 사이트/조사구 입력")

        self.input_mode_upload_radio = QRadioButton("파일 업로드")
        self.input_mode_draw_radio = QRadioButton("지도에 사이트 경계 그리기")
        self.input_mode_upload_radio.setChecked(True)
        self._configure_tab_reachable_radio_group(
            (self.input_mode_upload_radio, self.input_mode_draw_radio)
        )

        self.upload_path_edit = QLineEdit()
        browse_button = QPushButton("GeoPackage 또는 Shapefile 선택...")
        browse_button.clicked.connect(self._browse_upload)

        self.site_name_field_combo = QComboBox()
        self.site_name_field_combo.setEnabled(False)

        self.upload_encoding_combo = QComboBox()
        self.upload_encoding_combo.addItem("CP949", "cp949")
        self.upload_encoding_combo.addItem("UTF-8", "utf-8")
        self.upload_encoding_combo.setVisible(False)
        self.upload_encoding_combo.setToolTip(
            "Shapefile DBF 속성값을 읽을 때 사용할 문자 인코딩입니다. 미리보기로 확인하세요."
        )

        self.upload_crs_label = QLabel("원본 좌표계 EPSG 코드 (.prj가 없을 때 필수):")
        self.upload_crs_edit = QLineEdit()
        self.upload_crs_edit.setPlaceholderText("예: 5186 또는 EPSG:5186")
        self.upload_crs_edit.setToolTip(
            "선택한 SHP와 같은 좌표계의 EPSG 코드를 입력하세요. 예: EPSG:5186"
        )
        self.upload_crs_label.setVisible(False)
        self.upload_crs_edit.setVisible(False)
        self._upload_prj_missing: bool | None = None
        self._gpkg_preview_worker: _GpkgUploadPreviewWorker | None = None
        self._gpkg_preview_path: str | None = None
        self._gpkg_preview_summary: dict | None = None

        self.preview_list = QListWidget()
        self.upload_status_label = QLabel("")
        self.upload_status_label.setWordWrap(True)

        self.registerField("sites_upload_path", self.upload_path_edit)
        self.registerField(
            "sites_upload_site_name_field", self.site_name_field_combo, "currentText"
        )
        self.registerField("sites_upload_source_crs", self.upload_crs_edit)

        self.upload_group = QGroupBox("업로드")
        upload_layout = QVBoxLayout()
        upload_layout.setSpacing(8)
        upload_layout.addWidget(self.upload_path_edit)
        upload_layout.addWidget(browse_button)
        upload_layout.addWidget(QLabel("Shapefile DBF 인코딩:"))
        upload_layout.addWidget(self.upload_encoding_combo)
        upload_layout.addWidget(self.upload_crs_label)
        upload_layout.addWidget(self.upload_crs_edit)
        upload_layout.addWidget(QLabel("사이트 이름으로 사용할 원본 속성:"))
        upload_layout.addWidget(self.site_name_field_combo)
        upload_layout.addWidget(QLabel("가져올 항목 미리보기:"))
        upload_layout.addWidget(self.preview_list)
        upload_layout.addWidget(self.upload_status_label)
        self.upload_group.setLayout(upload_layout)

        self.draw_site_name_edit = QLineEdit("그려진 사이트")
        self.draw_map_canvas = MapCanvas()
        self.draw_map_canvas.set_mode("polygon")
        self.draw_map_canvas.polygon_drawn.connect(self._on_polygon_drawn)
        finish_shape_button = QPushButton("도형 완성")
        finish_shape_button.clicked.connect(self._finish_drawn_shape)
        # FR-QPB-129 (Decision Log D-75/D-79): commits the current, already-finished polygon (with
        # its own individually assigned name) as its own separate site, then resets the canvas and
        # name field so a new, completely independent polygon can be started -- without discarding
        # any polygon already committed earlier in this same drawing session.
        commit_and_new_button = QPushButton("이 사이트로 저장하고 새 도형 그리기")
        commit_and_new_button.clicked.connect(self._commit_and_start_new_polygon)
        clear_shape_button = QPushButton("지우기")
        clear_shape_button.clicked.connect(self._clear_drawn_shape)
        self.draw_status_label = QLabel(
            "지도를 클릭해 꼭짓점을 추가한 뒤, '도형 완성'을 클릭하세요(또는 더블클릭)."
        )
        self.draw_status_label.setWordWrap(True)
        self._drawn_site_wkt: str | None = None

        # FR-QPB-129: every polygon already finished, named, and committed this session (via
        # `_commit_and_start_new_polygon`) -- each `{"site_name": str, "geom_wkt": str}`, in the
        # order committed. `committed_sites_list` is a purely visual, read-only echo of this list
        # for the user's own benefit -- it is never read back for `config["sites"]` construction
        # (see `drawn_sites`, which reads `self._committed_sites` directly).
        self._committed_sites: list[dict[str, str]] = []
        self.committed_sites_list = QListWidget()

        self.draw_group = QGroupBox("사이트 경계 그리기")
        draw_layout = QVBoxLayout()
        draw_layout.setSpacing(8)
        draw_layout.addWidget(QLabel("사이트 이름:"))
        draw_layout.addWidget(self.draw_site_name_edit)
        draw_layout.addWidget(self.draw_map_canvas)
        draw_buttons_row = QHBoxLayout()
        draw_buttons_row.setSpacing(8)
        draw_buttons_row.addWidget(finish_shape_button)
        draw_buttons_row.addWidget(commit_and_new_button)
        draw_buttons_row.addWidget(clear_shape_button)
        draw_layout.addLayout(draw_buttons_row)
        draw_layout.addWidget(self.draw_status_label)
        draw_layout.addWidget(QLabel("이번 세션에서 저장된 사이트:"))
        draw_layout.addWidget(self.committed_sites_list)
        self.draw_group.setLayout(draw_layout)

        # Real-device layout-overlap bug fix -- see `_wrap_in_scroll_area`'s own docstring: this
        # group contains `draw_map_canvas` (a `MapCanvas`, with a hard 320x240 minimum size), so
        # it is wrapped in a scroll area rather than added to `layout` directly, exactly like
        # `ConnectivityBasemapPage.offline_group` below.
        self._draw_group_scroll = _wrap_in_scroll_area(self.draw_group)

        layout = QVBoxLayout()
        _polish_layout(layout)
        self.site_input_intro_label = QLabel(
            "사이트/조사구는 GeoPackage나 Shapefile을 업로드하거나, 아래 지도에 직접 "
            "사이트 경계를 그려서 입력할 수 있습니다."
        )
        # Bug 2 fix (window-sizing regression): see the matching comment on `ProjectBasicsPage`'s
        # own parent-folder help label above -- word wrap here.
        self.site_input_intro_label.setWordWrap(True)

        # FR-QPB-025 ("when applicable to the selected survey type"): Type 1 ("Simple species
        # inventory") has no `site` entity at all (Section 8.1, DR-QPB-008), so this page must
        # not ask for a site boundary in that case -- see `_update_applicability()`.
        self.not_applicable_label = QLabel(
            f"이 조사 유형('{_SURVEY_TYPE_LABELS_KO[_SURVEY_TYPE_WITHOUT_SITE]}')은 "
            "사이트/조사구 경계가 없습니다 -- 업로드하거나 그릴 항목이 없습니다. "
            "'다음'을 클릭해 계속하세요."
        )
        self.not_applicable_label.setWordWrap(True)
        self.not_applicable_label.setVisible(False)
        self._applicable = True

        layout.addWidget(_build_logo_banner_label())
        layout.addWidget(self.site_input_intro_label)
        layout.addWidget(self.not_applicable_label)
        layout.addWidget(self.input_mode_upload_radio)
        layout.addWidget(self.input_mode_draw_radio)
        layout.addWidget(self.upload_group)
        layout.addWidget(self._draw_group_scroll)
        _install_page_scroll_container(self, layout)

        self.input_mode_upload_radio.toggled.connect(self._update_input_mode_visibility)
        self._update_input_mode_visibility()

        self.upload_path_edit.textChanged.connect(self._on_upload_path_changed)
        self.site_name_field_combo.currentTextChanged.connect(self._update_preview)
        self.upload_encoding_combo.currentIndexChanged.connect(self._update_preview)

    def initializePage(self) -> None:
        # Re-evaluated every time this page becomes current (including after the user goes back
        # and changes the survey type on Step 2), per FR-QPB-025's "when applicable to the
        # selected survey type" clause -- see the class docstring and `_update_applicability()`.
        survey_type = self.wizard().field("survey_type")
        self._update_applicability(survey_type != _SURVEY_TYPE_WITHOUT_SITE)

    def _update_applicability(self, applicable: bool) -> None:
        self._applicable = applicable
        self.site_input_intro_label.setVisible(applicable)
        self.input_mode_upload_radio.setVisible(applicable)
        self.input_mode_draw_radio.setVisible(applicable)
        self.not_applicable_label.setVisible(not applicable)
        if applicable:
            self._update_input_mode_visibility()
        else:
            # Neither group is shown, and any previously-entered upload path/drawn shape must not
            # silently resurface if the user flips the survey type back and forth -- see
            # `drawn_site_wkt()`'s own defense-in-depth check and
            # `ReviewAndBuildPage._collect_config()`'s matching guard, which never even reads this
            # page's state for `simple_inventory`.
            self.upload_group.setVisible(False)
            self._draw_group_scroll.setVisible(False)

    def _update_input_mode_visibility(self) -> None:
        if not self._applicable:
            return
        use_upload = self.input_mode_upload_radio.isChecked()
        self.upload_group.setVisible(use_upload)
        self._draw_group_scroll.setVisible(not use_upload)

    @staticmethod
    def _configure_tab_reachable_radio_group(radios: tuple[QRadioButton, ...]) -> None:
        """Keep exclusive choices while allowing every radio to receive a Tab stop."""
        for radio in radios:
            radio.setAutoExclusive(False)

        def keep_one_checked(sender: QRadioButton, checked: bool) -> None:
            if checked:
                for radio in radios:
                    if radio is not sender and radio.isChecked():
                        radio.setChecked(False)
            elif not any(radio.isChecked() for radio in radios):
                sender.blockSignals(True)
                sender.setChecked(True)
                sender.blockSignals(False)

        for radio in radios:
            radio.toggled.connect(
                lambda checked, sender=radio: keep_one_checked(sender, checked)
            )

    def _finish_drawn_shape(self) -> None:
        # MapCanvas retains both finish_polygon() and finish_bbox_at() drawing semantics; this
        # wizard page intentionally continues to use the existing polygon workflow.
        try:
            wkt = self.draw_map_canvas.finish_polygon()
        except ValueError as exc:
            self.draw_status_label.setText(str(exc))
            return
        self._on_polygon_drawn(wkt)

    def _on_polygon_drawn(self, wkt: str) -> None:
        try:
            validate_geometry(wkt, "MULTIPOLYGON")
        except InvalidGeometryError as exc:
            self._drawn_site_wkt = None
            self.draw_status_label.setText(f"잘못된 도형입니다: {exc}")
            return
        self._drawn_site_wkt = wkt
        self.draw_status_label.setText(
            "도형이 완성되어 사용할 준비가 되었습니다. 계속해서 다른 사이트를 그리려면 "
            "'이 사이트로 저장하고 새 도형 그리기'를 클릭하세요."
        )

    def _commit_and_start_new_polygon(self) -> None:
        """FR-QPB-129 (Decision Log D-75/D-79): commits the current, already-finished polygon
        (with its own individually assigned name) as its own separate site, then resets the canvas
        and name field so a brand-new, completely independent polygon can be drawn next -- without
        discarding any polygon already committed earlier in this same drawing session."""
        if self._drawn_site_wkt is None:
            self.draw_status_label.setText(
                "먼저 도형을 완성한 뒤('도형 완성' 클릭 또는 더블클릭) 저장하세요."
            )
            return
        name = self.drawn_site_name()
        self._committed_sites.append({"site_name": name, "geom_wkt": self._drawn_site_wkt})
        self.committed_sites_list.addItem(name)
        self.draw_map_canvas.commit_finished_polygon()
        self._drawn_site_wkt = None
        self.draw_site_name_edit.setText("그려진 사이트")
        self.draw_status_label.setText(
            "사이트가 저장되었습니다. 새 도형을 그리려면 지도를 클릭해 꼭짓점을 추가하세요."
        )

    def _clear_drawn_shape(self) -> None:
        """Clears only the *current* in-progress/finished (not-yet-committed) shape -- mirroring
        `MapCanvas.reset_drawing`'s own scope, this never discards a polygon already committed
        earlier this session via `_commit_and_start_new_polygon`."""
        self._drawn_site_wkt = None
        self.draw_map_canvas.reset_drawing()
        self.draw_status_label.setText(
            "지도를 클릭해 꼭짓점을 추가한 뒤, '도형 완성'을 클릭하세요(또는 더블클릭)."
        )

    def drawn_site_wkt(self) -> str | None:
        """The current, finished, validated drawn-site WKT (not yet committed via
        `_commit_and_start_new_polygon`, if any), or ``None`` if drawing mode isn't active or no
        shape has been finished yet (in which case the upload path, if any, applies instead).

        Defense in depth for FR-QPB-025's "when applicable to the selected survey type" clause:
        always ``None`` when this page isn't applicable to the current survey type (Type 1 --
        see `_update_applicability()`), even if a shape was drawn before the user switched back
        to that survey type on Step 2.
        """
        if not self._applicable:
            return None
        if not self.input_mode_draw_radio.isChecked():
            return None
        return self._drawn_site_wkt

    def drawn_site_name(self) -> str:
        return self.draw_site_name_edit.text().strip() or "그려진 사이트"

    def drawn_sites(self) -> list[dict[str, str]]:
        """FR-QPB-129 (Decision Log D-75/D-79): every named, finished polygon from this drawing
        session -- every polygon already committed via `_commit_and_start_new_polygon`, plus the
        current canvas's own finished-but-not-yet-committed polygon (if any), in the order
        finished. Mirrors the pre-existing single-polygon behavior, where finishing a shape was
        already enough without any further "commit" step -- so a session with exactly one
        finished, never-committed polygon still yields a single-element list, unchanged from
        before this requirement existed.

        Returns an empty list under the same conditions `drawn_site_wkt()` returns ``None``
        (drawing not applicable to the current survey type, or upload mode selected), and whenever
        nothing has been finished at all -- zero, one, or many named polygons are all valid
        outcomes of one drawing session (`validatePage()`'s existing "drawing is optional"
        behavior, unchanged by this requirement).
        """
        if not self._applicable:
            return []
        if not self.input_mode_draw_radio.isChecked():
            return []
        sites = list(self._committed_sites)
        if self._drawn_site_wkt:
            sites.append({"site_name": self.drawn_site_name(), "geom_wkt": self._drawn_site_wkt})
        return sites

    def _browse_upload(self) -> None:
        path, _ = _get_open_file_name(
            self,
            "사이트/조사구 파일 선택",
            filter="GeoPackage 또는 Shapefile (*.gpkg *.shp *.zip)",
        )
        if path:
            self.upload_path_edit.setText(path)

    def _on_upload_path_changed(self, path: str) -> None:
        self.site_name_field_combo.blockSignals(True)
        self.site_name_field_combo.clear()
        self.site_name_field_combo.blockSignals(False)
        self.preview_list.clear()
        self.upload_status_label.setText("")

        if not path:
            self.upload_encoding_combo.setVisible(False)
            self.site_name_field_combo.setEnabled(False)
            return

        upload_format = site_upload.infer_format(path)
        if upload_format is None:
            self.upload_encoding_combo.setVisible(False)
            self.site_name_field_combo.setEnabled(False)
            self.upload_status_label.setText(
                "인식할 수 없는 파일 형식입니다. 이 버전에서는 사이트/조사구 업로드에 "
                "GeoPackage(.gpkg), Shapefile(.shp) 또는 압축된 Shapefile(.zip)만 지원됩니다."
            )
            return

        # Do not decode GPKG geometry in this slot.  This signal runs on Qt's GUI thread and
        # previously called `read_first_feature_layer_raw()` through `preview_features()`, which
        # normalised every vertex of a selected site boundary before the user could continue.
        if upload_format == "gpkg":
            self._upload_prj_missing = False
            self.upload_encoding_combo.setVisible(False)
            self.upload_crs_label.setVisible(False)
            self.upload_crs_edit.setVisible(False)
            self.site_name_field_combo.setEnabled(False)
            self._gpkg_preview_path = None
            self._gpkg_preview_summary = None
            self.upload_status_label.setText("GeoPackage 정보를 확인하는 중입니다…")
            worker = _GpkgUploadPreviewWorker(path, self)
            worker.result_ready.connect(self._on_gpkg_preview_ready)
            self._gpkg_preview_worker = worker
            worker.start()
            return

        is_shapefile = upload_format in ("shapefile", "zipped_shapefile")
        try:
            self._upload_prj_missing = is_shapefile and not site_upload.shapefile_has_prj(
                upload_format, path
            )
        except Exception as exc:  # noqa: BLE001 - surfaced honestly to the user.
            self._upload_prj_missing = None
            self.upload_crs_label.setVisible(False)
            self.upload_crs_edit.setVisible(False)
            self.site_name_field_combo.setEnabled(False)
            self.upload_status_label.setText(f"이 파일의 .prj 정보를 확인할 수 없었습니다: {exc}")
            return
        self.upload_crs_label.setVisible(bool(self._upload_prj_missing))
        self.upload_crs_edit.setVisible(bool(self._upload_prj_missing))
        if self._upload_prj_missing:
            self.upload_status_label.setText(
                "이 Shapefile에는 .prj 파일이 없습니다. 원본 좌표계의 EPSG 코드를 입력해야 "
                "생성할 수 있습니다."
            )

        try:
            encoding = self.upload_encoding_combo.currentData() or "cp949"
            self.upload_encoding_combo.setVisible(
                upload_format in ("shapefile", "zipped_shapefile")
            )
            fields = site_upload.list_attribute_fields(upload_format, path, encoding)
        except Exception as exc:  # noqa: BLE001 - surfaced honestly to the user, never swallowed.
            self.site_name_field_combo.setEnabled(False)
            self.upload_status_label.setText(f"이 파일을 읽을 수 없었습니다: {exc}")
            return

        self.site_name_field_combo.setEnabled(bool(fields))
        if fields:
            self.site_name_field_combo.addItems(fields)
        else:
            self.upload_status_label.setText(
                "이 파일에는 매핑하거나 가져올 feature가 없습니다."
            )
        self._update_preview()

    def _on_gpkg_preview_ready(self, path: str, result: dict) -> None:
        """Apply an attribute-only GPKG preview if it still belongs to the selected path."""
        if path != self.upload_path_edit.text():
            return
        if not result.get("success"):
            self.site_name_field_combo.setEnabled(False)
            self.upload_status_label.setText(
                f"이 파일을 읽을 수 없었습니다: {result.get('error') or '알 수 없는 오류'}"
            )
            return

        summary = result["summary"]
        fields = summary.get("fields") or []
        self._gpkg_preview_path = path
        self._gpkg_preview_summary = summary
        self.site_name_field_combo.blockSignals(True)
        self.site_name_field_combo.clear()
        self.site_name_field_combo.addItems(fields)
        self.site_name_field_combo.blockSignals(False)
        self.site_name_field_combo.setEnabled(bool(fields))
        self._update_preview()

    def _update_preview(self, *_args) -> None:
        self.preview_list.clear()
        path = self.upload_path_edit.text()
        if not path:
            return
        upload_format = site_upload.infer_format(path)
        if upload_format is None:
            return

        if upload_format == "gpkg":
            summary = (
                self._gpkg_preview_summary
                if self._gpkg_preview_path == path
                else None
            )
            if summary is None:
                # The background worker will populate this shortly.  Never fall back to a
                # geometry-reading synchronous preview here.
                return
            site_name_field = self.site_name_field_combo.currentText() or None
            rows = summary.get("sample_attributes") or []
            geometry_type = summary.get("geometry_type") or "GEOMETRY"
            for attributes in rows:
                name = attributes.get(site_name_field) if site_name_field else None
                self.preview_list.addItem(f"{name or '가져온 사이트'}  ({geometry_type})")
            total = int(summary.get("feature_count") or 0)
            suffix = ""
            if total > len(rows):
                suffix = f" 처음 {len(rows)}개만 미리 표시합니다."
            self.upload_status_label.setText(f"총 {total}개의 feature를 가져옵니다.{suffix}")
            return

        site_name_field = self.site_name_field_combo.currentText() or None
        try:
            encoding = self.upload_encoding_combo.currentData() or "cp949"
            preview = site_upload.preview_features(
                upload_format, path, site_name_field, encoding
            )
        except Exception as exc:  # noqa: BLE001 - surfaced honestly to the user.
            self.upload_status_label.setText(f"이 파일을 미리 볼 수 없었습니다: {exc}")
            return

        self.upload_status_label.setText(f"{len(preview)}개의 feature를 가져옵니다.")
        for row in preview:
            self.preview_list.addItem(f"{row['site_name']}  ({row['geometry_type']})")

    def validatePage(self) -> bool:
        if self.input_mode_draw_radio.isChecked():
            return True  # Drawing is optional, same as upload -- not every type needs sites.
        path = self.upload_path_edit.text()
        if not path:
            return True  # Upload is optional -- not every survey type requires seed sites.
        upload_format = site_upload.infer_format(path)
        if upload_format is None:
            return False
        if upload_format in ("shapefile", "zipped_shapefile"):
            try:
                requires_crs = (
                    self._upload_prj_missing
                    if self._upload_prj_missing is not None
                    else not site_upload.shapefile_has_prj(upload_format, path)
                )
                if requires_crs:
                    normalized = site_upload.normalize_epsg_code(self.upload_crs_edit.text())
                    self.upload_crs_edit.setText(normalized)
            except Exception as exc:  # noqa: BLE001 - block navigation with actionable feedback.
                self.upload_status_label.setText(str(exc))
                return False
        return True


class ConnectivityBasemapPage(QWizardPage):
    """Section 6.4/Sections 10-11: online VWorld layer, offline MBTiles, or no basemap.

    Offline mode (FR-QPB-034-036, FR-QPB-080-089, DR-QPB-060-061) accepts a bbox from either an
    uploaded Polygon/MultiPolygon file's bounding envelope, or a bbox drawn directly on the map
    (:mod:`qfield_builder.ui.map_canvas`) -- both eventually populate the same internal
    ``{"min_lon", "min_lat", "max_lon", "max_lat"}`` shape. Before generation, this page shows
    the bbox coordinates, an approximate area, the selected zoom range, the expected tile count,
    and the estimated output size (FR-QPB-081/082), and blocks proceeding
    (:meth:`validatePage`) once the estimate exceeds the 900 MiB pre-generation threshold
    (DR-QPB-060) -- the 1 GiB hard limit itself is enforced by the backend at actual generation
    time (`qfield_builder.build`), but its existence is always shown here too.
    """

    def __init__(self, parent=None, *, fetch_layers_fn=None, password_prompt_fn=None):
        super().__init__(parent)
        self.setTitle("4단계 - 연결 상태 및 배경지도")

        # FR-QPB-071 (revised; Decision Log D-26): the layer list shown here is discovered live
        # from the real VWorld WMTS capabilities endpoint once an API key is entered (see
        # `_refresh_vworld_layers` below) -- `vworld.supported_layers()` is only the fallback/
        # default set shown before a key is entered or if a live query has never succeeded.
        # `fetch_layers_fn`, if supplied, replaces `vworld.fetch_supported_layers` for tests (the
        # same injectable-test-seam convention `MapCanvas(tile_fetcher=...)` already uses).
        self._fetch_layers_fn = (
            fetch_layers_fn if fetch_layers_fn is not None else vworld.fetch_supported_layers
        )
        self._known_vworld_layers: list[str] | None = None

        # NFR-QPB-073/AC-QPB-097 (Decision Log D-53/D-55): the retrieval-time-only password
        # re-prompt shown when a remembered key needs to be decrypted -- `password_prompt_fn`, if
        # supplied, replaces the real, modal `PasswordUnlockDialog` for tests, the same injectable-
        # test-seam convention as `fetch_layers_fn` above.
        self._password_prompt_fn = (
            password_prompt_fn if password_prompt_fn is not None else prompt_for_unlock_password
        )

        self.online_radio = QRadioButton("온라인 (현장에 충분한 인터넷 연결이 있음)")
        self.offline_radio = QRadioButton("오프라인 (로컬 배경지도 생성)")
        self.none_radio = QRadioButton("배경지도 없음")
        self.none_radio.setChecked(True)
        SiteInputPage._configure_tab_reachable_radio_group(
            (self.online_radio, self.offline_radio, self.none_radio)
        )

        self.layer_combo = QComboBox()
        self.layer_combo.addItems(supported_layers())
        # The shared online/offline selector intentionally keeps the online selector's existing
        # default and option vocabulary.  Offline downloads have an additional resolution
        # requirement, though: with multiple choices, the visible initial item is not evidence
        # that the user deliberately chose it.  `activated` is emitted for a user activation of a
        # combo-box item, unlike `currentTextChanged`, which also fires for repopulation and other
        # programmatic changes.
        self._offline_layer_selected_by_user = False
        self._offline_layer_requires_explicit_selection = False
        self.layer_combo.activated.connect(self._on_layer_activated)
        self._refresh_layers_button = QPushButton("레이어 목록 새로고침")
        self._refresh_layers_button.clicked.connect(self._refresh_vworld_layers)
        self.layer_status_label = QLabel(
            "VWorld API 키 (WMTS/TMS API)를 입력한 뒤 '레이어 목록 새로고침'을 눌러 "
            "현재 지원되는 레이어 "
            "목록을 확인하세요. (아래 목록은 새로고침 전까지 표시되는 기본값입니다.)"
        )
        self.layer_status_label.setWordWrap(True)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)  # NFR-QPB-010: masked in UI.

        # Bug 1 fix (checkbox/widget overlap): the full disclosure text is rendered by a
        # separately word-wrapped `QLabel` -- matching this page's own established convention for
        # long text (see `layer_status_label` above and `identification_intro_label`/
        # `identification_key_note_label` on `IdentificationTogglePage`) -- because `QCheckBox`
        # (unlike `QLabel`) does not reliably report a wrapped-text height via its own
        # `sizeHint()`/`heightForWidth()` inside a `QFormLayout` row, so a long checkbox label used
        # to visually overlap `remember_checkbox` rendered directly below it. The checkbox itself
        # now carries only a short, single-line confirmation label; its checked/unchecked state
        # remains the actual gate for `consent_accepted`, unchanged.
        #
        # Reviewer-round fix (FR-QPB-076): this disclosure is true ONLY for the online-layer
        # embedding case -- it must never be shown to an offline-mode user (see
        # `offline_key_usage_label` below and `_update_consent_widgets_visibility`, which shows
        # exactly one of the two, never both, and never this one for offline mode). The trailing
        # sentence is FR-QPB-076's own explicit "clearly distinguishes this online-layer exception
        # from offline MBTiles generation" requirement.
        self.consent_disclosure_label = QLabel(
            ".qgs 프로젝트 파일에 이 API 키가 읽을 수 있는 형태로 포함되며, 프로젝트 폴더를 "
            "받는 사람은 누구나 이 키를 추출할 수 있다는 점을 이해합니다. (오프라인 배경지도 "
            "생성 시에는 이 키가 다운로드에만 일시적으로 사용되며, 생성된 프로젝트에는 포함되지 "
            "않습니다.)"
        )
        self.consent_disclosure_label.setWordWrap(True)
        self.consent_checkbox = QCheckBox("위 내용에 동의합니다")

        # Reviewer-round fix (FR-QPB-076/FR-QPB-078/NFR-QPB-058): offline mode never embeds the
        # key anywhere in the delivered project -- it is used only transiently during tile
        # retrieval (`qfield_builder.build`'s offline branch; `vworld_tiles.resolve_tile_fetcher`).
        # No consent/risk-acceptance checkbox is required for this case (there is nothing to
        # accept -- `build.py`'s offline branch never gates on `consent_accepted`), but the user
        # must still be told accurately what happens to the key they are about to enter, instead
        # of either silently saying nothing or reusing the online-only disclosure text above (which
        # would be factually false here). Shown INSTEAD OF `consent_disclosure_label`/
        # `consent_checkbox` for offline mode -- see `_update_consent_widgets_visibility`.
        self.offline_key_usage_label = QLabel(
            "이 API 키는 오프라인 배경지도 타일을 내려받는 동안에만 일시적으로 사용됩니다. "
            "생성이 완료되면 .qgs 프로젝트 파일, .mbtiles 파일, 매니페스트 등 전달되는 어떤 "
            "파일에도 이 키가 저장되지 않습니다."
        )
        self.offline_key_usage_label.setWordWrap(True)

        # NFR-QPB-018 (revised; Decision Log D-53): no longer the OS credential store -- an
        # application-managed, password-derived, locally-encrypted file (`credentials.enc`).
        # Reviewer-round fix: this "remember this key" mechanism is generic to the VWorld key
        # itself (NFR-QPB-018 is not scoped to the online-layer-embedding case) -- it remains
        # shown and fully functional for BOTH online and offline mode; see
        # `ReviewAndBuildPage._collect_config()`'s offline branch, which now wires this checkbox's
        # state into `config["basemap"]["remember_key"]` exactly like the online branch already
        # does, so it is never a silent no-op in offline mode.
        self.remember_checkbox = QCheckBox("이 키 기억하기 (이 컴퓨터에 암호화하여 저장됨)")
        # NFR-QPB-073: user-facing feedback for the encrypted-storage password flow (first-launch
        # decline, retrieval-time unlock failure) -- kept separate from `layer_status_label`,
        # which is about VWorld's own live layer-discovery status, not credential storage.
        self.credential_status_label = QLabel("")
        self.credential_status_label.setWordWrap(True)

        self.registerField("basemap_mode", self, "basemapMode")
        self.registerField("vworld_api_key", self.api_key_edit)
        self.registerField("vworld_layer", self.layer_combo, "currentText")
        self.registerField("consent_accepted", self.consent_checkbox)
        self.registerField("remember_key", self.remember_checkbox)

        layout = QVBoxLayout()
        _polish_layout(layout)
        layout.addWidget(_build_logo_banner_label())
        layout.addWidget(self.online_radio)
        layout.addWidget(self.offline_radio)
        layout.addWidget(self.none_radio)

        # Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058): the VWorld API key is required for BOTH
        # online and offline mode -- offline MBTiles generation needs it during tile retrieval,
        # exactly like the online WMTS layer does. This is the SAME `api_key_edit`/consent/
        # remember-checkbox widget set for both modes (never duplicated) -- previously it lived
        # only inside `online_group`, so it was never reachable at all when offline mode was
        # selected. It now lives in its own group, shown whenever EITHER online or offline mode
        # is selected, and hidden only for "배경지도 없음" (no basemap) -- see
        # `_update_api_key_group_visibility` below.
        self.api_key_group = QGroupBox("VWorld API 키")
        api_key_layout = QFormLayout()
        api_key_layout.setSpacing(_PAGE_SPACING)
        api_key_layout.addRow("VWorld API 키 (WMTS/TMS API):", self.api_key_edit)
        # Reviewer-round fix (FR-QPB-076): `consent_disclosure_label`/`consent_checkbox` (online
        # embedding risk) and `offline_key_usage_label` (offline transient-use fact) occupy
        # separate rows so `_update_consent_widgets_visibility` can show exactly the one that is
        # factually accurate for the currently selected mode, never both, never neither.
        api_key_layout.addRow("", self.consent_disclosure_label)
        api_key_layout.addRow(self.consent_checkbox)
        api_key_layout.addRow("", self.offline_key_usage_label)
        api_key_layout.addRow(self.remember_checkbox)
        api_key_layout.addRow("", self.credential_status_label)
        self.api_key_group.setLayout(api_key_layout)
        layout.addWidget(self.api_key_group)

        # One selector is deliberately shared by online WMTS and offline MBTiles. The selected
        # value is therefore never allowed to diverge between the two acquisition paths.
        self.online_group = QGroupBox("VWorld 레이어 선택")
        online_layout = QFormLayout()
        online_layout.setSpacing(_PAGE_SPACING)
        layer_row = QHBoxLayout()
        layer_row.setSpacing(8)
        layer_row.addWidget(self.layer_combo)
        layer_row.addWidget(self._refresh_layers_button)
        online_layout.addRow("레이어:", layer_row)
        online_layout.addRow("", self.layer_status_label)
        self.online_group.setLayout(online_layout)
        layout.addWidget(self.online_group)

        self._offline_bbox: dict | None = None
        self._offline_blocked = False

        self.offline_bbox_source_upload_radio = QRadioButton(
            "GeoPackage/Shapefile 폴리곤 업로드 (경계 사각형을 사용)"
        )
        self.offline_bbox_source_draw_radio = QRadioButton("지도에 영역 그리기")
        self.offline_bbox_source_upload_radio.setChecked(True)
        SiteInputPage._configure_tab_reachable_radio_group(
            (self.offline_bbox_source_upload_radio, self.offline_bbox_source_draw_radio)
        )

        self.offline_upload_path_edit = QLineEdit()
        self._offline_upload_browse_button = QPushButton("폴리곤 파일 선택...")
        self._offline_upload_browse_button.clicked.connect(self._browse_offline_upload)

        self.offline_map_canvas = MapCanvas()
        self.offline_map_canvas.set_mode("bbox")
        self.offline_map_canvas.bbox_drawn.connect(self._on_bbox_drawn)
        self._offline_clear_button = QPushButton("그려진 영역 지우기")
        self._offline_clear_button.clicked.connect(self._clear_offline_bbox)

        self.min_zoom_spin = QSpinBox()
        self.min_zoom_spin.setRange(MIN_ZOOM, MAX_ZOOM)
        self.min_zoom_spin.setValue(10)
        self.max_zoom_spin = QSpinBox()
        self.max_zoom_spin.setRange(MIN_ZOOM, MAX_ZOOM)
        self.max_zoom_spin.setValue(16)
        self.min_zoom_spin.valueChanged.connect(self._update_offline_estimate)
        self.max_zoom_spin.valueChanged.connect(self._update_offline_estimate)

        self.offline_estimate_label = QLabel("크기를 예상하려면 영역을 그리거나 업로드하세요.")
        self.offline_estimate_label.setWordWrap(True)

        self.offline_group = QGroupBox("오프라인 배경지도 영역")
        offline_layout = QVBoxLayout()
        offline_layout.setSpacing(8)
        offline_layout.addWidget(self.offline_bbox_source_upload_radio)
        offline_layout.addWidget(self.offline_upload_path_edit)
        offline_layout.addWidget(self._offline_upload_browse_button)
        offline_layout.addWidget(self.offline_bbox_source_draw_radio)
        offline_layout.addWidget(self.offline_map_canvas)
        offline_layout.addWidget(self._offline_clear_button)
        zoom_row = QFormLayout()
        zoom_row.setSpacing(_PAGE_SPACING)
        zoom_row.addRow("최소 줌:", self.min_zoom_spin)
        zoom_row.addRow("최대 줌:", self.max_zoom_spin)
        offline_layout.addLayout(zoom_row)
        offline_layout.addWidget(self.offline_estimate_label)
        self.offline_group.setLayout(offline_layout)

        # Real-device layout-overlap bug fix (Step 4/"연결 상태 및 배경지도", offline mode + "지도에
        # 영역 그리기") -- see `_wrap_in_scroll_area`'s own docstring for the actual, measured root
        # cause: this group contains `offline_map_canvas` (a `MapCanvas`, with a hard 320x240
        # minimum size), so it is wrapped in a scroll area rather than added to `layout` directly.
        self._offline_group_scroll = _wrap_in_scroll_area(self.offline_group)
        layout.addWidget(self._offline_group_scroll)
        _install_page_scroll_container(self, layout)

        self.online_radio.toggled.connect(self._update_layer_group_visibility)
        self.offline_radio.toggled.connect(self._update_layer_group_visibility)
        self.offline_radio.toggled.connect(self._offline_group_scroll.setVisible)
        self.offline_radio.toggled.connect(self._update_offline_layer_selection_status)
        self._update_layer_group_visibility()
        self._offline_group_scroll.setVisible(self.offline_radio.isChecked())

        # Bug 1 fix: `api_key_group` is shown whenever either online or offline mode is selected
        # (both need the key), hidden only for "배경지도 없음" (no basemap).
        self.online_radio.toggled.connect(self._update_api_key_group_visibility)
        self.offline_radio.toggled.connect(self._update_api_key_group_visibility)
        self.none_radio.toggled.connect(self._update_api_key_group_visibility)
        self._update_api_key_group_visibility()

        # Reviewer-round fix (FR-QPB-076): the consent/offline-usage sub-widgets must track mode
        # independently of `api_key_group`'s own online-vs-offline-vs-none visibility above.
        self.online_radio.toggled.connect(self._update_consent_widgets_visibility)
        self.offline_radio.toggled.connect(self._update_consent_widgets_visibility)
        self._update_consent_widgets_visibility()

        self.offline_bbox_source_upload_radio.toggled.connect(
            self._update_offline_bbox_source_visibility
        )
        self._update_offline_bbox_source_visibility()
        self.offline_upload_path_edit.textChanged.connect(self._on_offline_upload_path_changed)

        # NFR-QPB-073/AC-QPB-097 (Decision Log D-53/D-55): deliberately NOT called here.
        # Loading a remembered key is the specific point-of-use retrieval this page's
        # `initializePage()` below performs -- `__init__` fires at wizard-construction time,
        # before the wizard is even shown, which would violate "never at general application
        # startup". See `tests/acceptance/qfield_project_builder_credential_storage_mechanism.
        # traceability.md`'s finding on `QWizardPage.initializePage()` vs `__init__` timing.

    def initializePage(self) -> None:
        self._load_remembered_key()

    def _load_remembered_key(self) -> None:
        """NFR-QPB-018 (revised)/NFR-QPB-073: a key previously stored via "Remember this key"
        must actually be remembered "across sessions" -- reload it from the encrypted local store
        (`qfield_builder.credential_store`) here, at the specific point of use (this page's
        `initializePage()`), so a fresh wizard reflects it instead of always showing an empty
        field as if nothing had ever been remembered. The field keeps `EchoMode.Password`
        (NFR-QPB-010) regardless of whether it was pre-filled this way or typed by the user.

        "Remember this key" itself is only ever offered when an encrypted-storage password has
        been established (NFR-QPB-073's decline-path fallback: otherwise it stays disabled for
        this session, falling back to session-only retention)."""
        self.remember_checkbox.setEnabled(credential_store.is_password_established())
        if not self.remember_checkbox.isEnabled():
            self.remember_checkbox.setToolTip(
                "암호화 저장 비밀번호가 설정되지 않아 사용할 수 없습니다."
            )

        try:
            saved_key = credential_store.get_remembered_key()
        except credential_store.CredentialStoreLockedError:
            # NFR-QPB-073/AC-QPB-097: a remembered key exists but this session has not yet
            # supplied the password -- prompt here, at this specific point of use, never at
            # general application startup.
            password = self._password_prompt_fn(self)
            if password is None:
                return  # User declined; leave the field empty, exactly as if nothing existed.
            try:
                credential_store.unlock_session(password)
            except credential_store.CredentialDecryptionError:
                self.credential_status_label.setText(
                    "비밀번호가 올바르지 않아 저장된 키를 불러올 수 없습니다. 이전에 저장된 "
                    "키는 복구할 수 없으며, 아래에 API 키를 직접 입력해야 합니다."
                )
                return
            except Exception:  # noqa: BLE001 - must never block the wizard.
                return
            try:
                saved_key = credential_store.get_remembered_key()
            except Exception:  # noqa: BLE001 - a credential-store failure must not block wizard.
                saved_key = None
        except Exception:  # noqa: BLE001 - a credential-store failure must not block the wizard.
            saved_key = None
        if saved_key:
            self.api_key_edit.setText(saved_key)
            self.remember_checkbox.setChecked(True)

    def _update_api_key_group_visibility(self, *_args) -> None:
        """Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058): the VWorld API key input
        (`api_key_group`, containing `api_key_edit` and its consent/remember widgets) is required
        for BOTH online and offline mode -- shown whenever either is selected, hidden only for
        "배경지도 없음" (no basemap)."""
        self.api_key_group.setVisible(
            self.online_radio.isChecked() or self.offline_radio.isChecked()
        )

    def _update_consent_widgets_visibility(self, *_args) -> None:
        """Reviewer-round fix (FR-QPB-076): `api_key_group` is shared between online and offline
        mode (see `_update_api_key_group_visibility` above), but the consent/disclosure sub-
        widgets inside it are NOT interchangeable between the two modes -- `consent_disclosure_
        label`'s text ("this key will be embedded in the .qgs file...") is true only for online
        mode (FR-QPB-073/FR-QPB-076) and is simply false for offline mode, which never embeds the
        key anywhere in the delivered project (FR-QPB-078/NFR-QPB-058). This method shows exactly
        one of `consent_disclosure_label`+`consent_checkbox` (online) or `offline_key_usage_label`
        (offline) at a time -- never both, never neither, whenever `api_key_group` itself is
        visible. No consent/risk-acceptance checkbox is shown for offline mode: `build.py`'s
        offline branch never gates on `consent_accepted` (there is no risk to accept), so a
        checkbox there would either be a no-op or would incorrectly imply a risk that does not
        exist for this mode.

        `remember_checkbox`/`credential_status_label` are deliberately NOT toggled here -- that
        mechanism (NFR-QPB-018) is generic to "the VWorld key" the user is about to enter, not
        scoped to the online-embedding case, and remains shown/functional for both modes (see
        `ReviewAndBuildPage._collect_config()`'s offline branch)."""
        is_online = self.online_radio.isChecked()
        self.consent_disclosure_label.setVisible(is_online)
        self.consent_checkbox.setVisible(is_online)
        self.offline_key_usage_label.setVisible(self.offline_radio.isChecked())

    def _get_basemap_mode(self) -> str:
        if self.online_radio.isChecked():
            return "online"
        if self.offline_radio.isChecked():
            return "offline"
        return "none"

    # See `SurveyTypePage.surveyType`'s comment: a real Qt `Property` is required here too, or
    # `wizard.field("basemap_mode")` silently returns `None` instead of this getter's value.
    #
    # Unlike `SurveyTypePage.surveyType`, this field is deliberately registered WITHOUT a
    # trailing `*` (`self.registerField("basemap_mode", self, "basemapMode")` above) -- it is not
    # a mandatory field, so `QWizardPage`'s mandatory-field completeness tracking never consults
    # it to decide whether to enable/disable Next, and the missing-NOTIFY-signal defect that
    # froze `SurveyTypePage`'s Next button does not apply here: there is no button-enablement
    # state for this field to get stuck at. Separately, `wizard.field("basemap_mode")` itself
    # (e.g. in `ReviewAndBuildPage.initializePage()`/`_collect_config()`) always calls this
    # getter fresh at the moment it's read, regardless of NOTIFY -- NOTIFY only affects *when
    # Qt decides to re-check mandatory-field completeness*, not whether a direct `field()` read
    # returns a live value. So there is no "stale value shown in the summary" bug here either.
    basemapMode = Property(str, _get_basemap_mode)

    # ------------------------------------------------------ VWorld layer discovery (D-26) -----

    def _on_layer_activated(self, _index: int) -> None:
        """Record a deliberate offline layer choice made through the shared combo box."""
        if not self.offline_radio.isChecked():
            return
        self._offline_layer_selected_by_user = True
        self._offline_layer_requires_explicit_selection = False

    def _available_vworld_layers(self) -> list[str]:
        """Return the effective current catalog represented by the shared layer selector."""
        known_layers = self.known_vworld_layers()
        if known_layers is not None:
            return known_layers
        return [
            self.layer_combo.itemText(index).strip()
            for index in range(self.layer_combo.count())
            if self.layer_combo.itemText(index).strip()
        ]

    def _offline_layer_is_resolved(self) -> bool:
        selected_layer = self.layer_combo.currentText().strip()
        available_layers = self._available_vworld_layers()
        if not selected_layer or selected_layer not in available_layers:
            return False
        if self._offline_layer_requires_explicit_selection:
            return self._offline_layer_selected_by_user
        # A single currently available choice is the only case where the UI may resolve the
        # selection without an activation.  Multiple choices must always be explicitly chosen.
        return self._offline_layer_selected_by_user or len(available_layers) == 1

    def _update_offline_layer_selection_status(self, checked: bool) -> None:
        if checked and not self._offline_layer_is_resolved():
            self.layer_status_label.setText(
                "오프라인 다운로드 전에 현재 VWorld 레이어 목록에서 오프라인 레이어를 하나 "
                "직접 선택하세요."
            )

    def _refresh_vworld_layers(self) -> None:
        """FR-QPB-071 (revised; Decision Log D-26): query the real VWorld WMTS capabilities
        endpoint for the API key currently entered, and repopulate `layer_combo` with exactly
        what it advertises -- never crashes, never silently keeps a stale list without telling
        the user (see `vworld.VWorldCapabilitiesError`)."""
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            self.layer_status_label.setText(
                "먼저 VWorld API 키를 입력한 뒤 '레이어 목록 새로고침'을 눌러 주세요."
            )
            return

        self.layer_status_label.setText("VWorld 레이어 목록을 불러오는 중입니다...")
        try:
            layers = self._fetch_layers_fn(api_key)
        except Exception as exc:  # noqa: BLE001 - shown to the user; never crashes the wizard.
            self._known_vworld_layers = None
            self._offline_layer_selected_by_user = False
            self._offline_layer_requires_explicit_selection = True
            self.layer_combo.clear()
            self.layer_status_label.setText(str(exc))
            return

        current = self.layer_combo.currentText().strip()
        previous_selection_was_explicit = self._offline_layer_selected_by_user
        self._known_vworld_layers = list(layers)
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        self.layer_combo.addItems(layers)
        if current in layers:
            self.layer_combo.setCurrentText(current)
            self._offline_layer_selected_by_user = previous_selection_was_explicit
            self._offline_layer_requires_explicit_selection = False
        else:
            # QComboBox otherwise selects item zero after `clear()`/`addItems()`.  That would turn
            # a stale layer into a different valid-looking layer, so an invalidated choice must
            # remain visibly unresolved until the user chooses from this refreshed catalog.
            self.layer_combo.setCurrentIndex(-1)
            self._offline_layer_selected_by_user = False
            self._offline_layer_requires_explicit_selection = True
        self.layer_combo.blockSignals(False)
        self.layer_status_label.setText(
            f"VWorld 레이어 목록을 성공적으로 불러왔습니다 ({len(layers)}개)."
        )

    def known_vworld_layers(self) -> list[str] | None:
        """The layer set from the most recent successful live discovery, or `None` if none has
        succeeded yet this session (in which case the fallback/default set applies)."""
        return list(self._known_vworld_layers) if self._known_vworld_layers is not None else None

    def _update_layer_group_visibility(self, *_args) -> None:
        self.online_group.setVisible(
            self.online_radio.isChecked() or self.offline_radio.isChecked()
        )

    # ------------------------------------------------------------ offline bbox source --------

    def _update_offline_bbox_source_visibility(self) -> None:
        use_upload = self.offline_bbox_source_upload_radio.isChecked()
        self.offline_upload_path_edit.setVisible(use_upload)
        self._offline_upload_browse_button.setVisible(use_upload)
        self.offline_map_canvas.setVisible(not use_upload)
        self._offline_clear_button.setVisible(not use_upload)

    def _browse_offline_upload(self) -> None:
        path, _ = _get_open_file_name(
            self,
            "오프라인 배경지도 범위로 사용할 폴리곤 파일 선택",
            filter="GeoPackage 또는 Shapefile (*.gpkg *.shp *.zip)",
        )
        if path:
            self.offline_upload_path_edit.setText(path)

    def _on_offline_upload_path_changed(self, path: str) -> None:
        if not path:
            self._offline_bbox = None
            self._update_offline_estimate()
            return
        upload_format = site_upload.infer_format(path)
        if upload_format is None:
            self._offline_bbox = None
            self.offline_estimate_label.setText(
                "인식할 수 없는 파일 형식입니다. GeoPackage(.gpkg), Shapefile(.shp) 또는 압축된 "
                "Shapefile(.zip)만 "
                "지원됩니다."
            )
            return
        try:
            self._offline_bbox = site_upload.read_upload_envelope(upload_format, path)
        except Exception as exc:  # noqa: BLE001 - surfaced honestly to the user, never swallowed.
            self._offline_bbox = None
            self.offline_estimate_label.setText(f"이 파일을 읽을 수 없었습니다: {exc}")
            return
        self._update_offline_estimate()

    def _on_bbox_drawn(self, bbox: dict) -> None:
        self._offline_bbox = dict(bbox)
        self._update_offline_estimate()

    def _clear_offline_bbox(self) -> None:
        self._offline_bbox = None
        self.offline_map_canvas.reset_drawing()
        self._update_offline_estimate()

    def _update_offline_estimate(self, *_args) -> None:
        self._offline_blocked = False
        if self._offline_bbox is None:
            self.offline_estimate_label.setText("크기를 예상하려면 영역을 그리거나 업로드하세요.")
            return

        min_zoom = self.min_zoom_spin.value()
        max_zoom = self.max_zoom_spin.value()
        if min_zoom > max_zoom:
            self._offline_blocked = True
            self.offline_estimate_label.setText(
                "최소 줌은 최대 줌보다 클 수 없습니다."
            )
            return

        estimate = estimate_offline_basemap_size(
            self._offline_bbox, min_zoom, max_zoom, DEFAULT_REPRESENTATIVE_TILE_BYTES
        )
        bbox = self._offline_bbox
        area_km2 = _approx_bbox_area_km2(bbox)
        estimated_mib = estimate["estimated_bytes"] / MIB
        lines = [
            f"경계상자(Bbox): min_lon={bbox['min_lon']:.6f}, min_lat={bbox['min_lat']:.6f}, "
            f"max_lon={bbox['max_lon']:.6f}, max_lat={bbox['max_lat']:.6f}",
            f"대략적인 면적: {area_km2:.2f} km^2",
            f"줌 레벨: {min_zoom}-{max_zoom}",
            f"예상 타일 개수: {estimate['tile_count']}",
            f"예상 크기: {estimated_mib:.1f} MiB",
            f"하드 한도: 1 GiB ({OFFLINE_HARD_LIMIT_BYTES} 바이트). 사전 생성 한도: 900 MiB.",
        ]
        if estimate["exceeds_pregeneration_threshold"]:
            self._offline_blocked = True
            lines.append(
                "제한됨(BLOCKED): 이 예상치가 900 MiB 사전 생성 한도를 초과합니다. 선택한 영역을 "
                "줄이거나, 최대 줌을 낮추거나, 더 낮은 해상도를 선택한 뒤 계속하세요."
            )
        self.offline_estimate_label.setText("\n".join(lines))

    def offline_config(self) -> dict:
        """The current offline-mode bbox/zoom selection, in the exact shape
        `qfield_builder.build`'s offline-mode branch reads (`basemap["bbox"]`, `["min_zoom"]`,
        `["max_zoom"]`)."""
        selected_layer = self.layer_combo.currentText().strip()
        if not self._offline_layer_is_resolved():
            selected_layer = ""
        return {
            "bbox": self._offline_bbox,
            "min_zoom": self.min_zoom_spin.value(),
            "max_zoom": self.max_zoom_spin.value(),
            "layer": selected_layer,
            "known_vworld_layers": self.known_vworld_layers(),
        }

    def validatePage(self) -> bool:
        if self.offline_radio.isChecked():
            if not self._offline_layer_is_resolved():
                self.layer_status_label.setText(
                    "계속하기 전에 현재 VWorld 레이어 목록에서 오프라인 레이어를 하나 직접 "
                    "선택하세요."
                )
                return False
            if self._offline_bbox is None:
                self.offline_estimate_label.setText(
                    "계속하기 전에 영역을 그리거나 업로드하세요."
                )
                return False
            if self.min_zoom_spin.value() > self.max_zoom_spin.value():
                return False
            if self._offline_blocked:
                return False
        return True


def _approx_bbox_area_km2(bbox: dict) -> float:
    """A rough equirectangular-approximation area in km^2, for FR-QPB-081's "area" display only
    -- never used for the 900 MiB/1 GiB size decisions, which rely solely on
    `estimate_offline_basemap_size`'s tile-count-based math."""
    km_per_degree_lat = 111.32
    mean_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2.0
    km_per_degree_lon = 111.32 * math.cos(math.radians(mean_lat))
    height_km = abs(bbox["max_lat"] - bbox["min_lat"]) * km_per_degree_lat
    width_km = abs(bbox["max_lon"] - bbox["min_lon"]) * km_per_degree_lon
    return max(0.0, height_km * width_km)


class IdentificationTogglePage(QWizardPage):
    """Section 6.5/FR-QPB-037-039/E-QPB-001: the guaranteed-manual identification baseline
    (Section 13) is now real, implemented, reviewer-PASSed code -- `qfield_builder/qml_plugin.py`
    (project plugin + embedded "Identify attached photos" `QML Widget`), `qfield_builder/
    reference_bundle.py` (FR-QPB-112/113 KTSN/probability-raster bundling), and `qfield_builder/
    ktsn_match.py` (FR-QPB-106/107 matching) -- so this page no longer presents it as a future,
    unavailable feature (the E-QPB-001 condition that required that framing no longer holds).
    E-QPB-001's underlying honesty principle still applies in full, though: this page must not
    overclaim certainty the specification itself does not claim.

    **Pl@ntNet API-key field (Decision Log D-45, superseding this page's prior "deliberately no
    key field" design)**: FR-QPB-079's prior blanket exclusion of the Pl@ntNet key from any
    embedding exception is now superseded, for the Pl@ntNet key specifically, by new
    FR-QPB-114-117 -- a second, narrowly scoped, consent-gated exception mirroring the existing
    VWorld online-basemap key exception (FR-QPB-073/FR-QPB-076-079) as closely as possible. Per
    FR-QPB-117, this page now collects the Pl@ntNet key as a masked secret input (mirroring
    `ConnectivityBasemapPage.api_key_edit`'s `EchoMode.Password` treatment of the VWorld key);
    per FR-QPB-115, a separate, explicit, mandatory consent checkbox (not merely an informational
    label) is required before the key is embedded into the generated project, mirroring
    `ConnectivityBasemapPage.consent_checkbox`'s disclosure content and structure but naming
    Pl@ntNet/this project's Pl@ntNet identification feature specifically; per FR-QPB-116, if
    consent is declined, the key is never embedded anywhere, and the identification feature (the
    `<project_slug>.qml` plugin + embedded `QML Widget`) remains present, falling back to manual
    in-QField key entry -- this page's prior fallback disclosure text still applies to that
    decline path. Collecting the key here (FR-QPB-117) does not by itself authorize embedding it;
    only the accepted consent checkbox does (FR-QPB-115).
    """

    def __init__(self, parent=None, *, password_prompt_fn=None):
        super().__init__(parent)
        self.setTitle("5단계 - 사진 기반 식별 (선택 사항)")
        self.enable_checkbox = QCheckBox(
            "Pl@ntNet 사진 식별 사용 (첨부된 사진 식별 기능)"
        )
        self.registerField("identification_enabled", self.enable_checkbox)

        # NFR-QPB-073/AC-QPB-097 (Decision Log D-53/D-55): mirrors
        # `ConnectivityBasemapPage`'s own injectable password-prompt seam.
        self._password_prompt_fn = (
            password_prompt_fn if password_prompt_fn is not None else prompt_for_unlock_password
        )

        layout = QVBoxLayout()
        _polish_layout(layout)
        identification_intro_label = QLabel(
            "사용 설정하면, 생성되는 프로젝트에 QField용 프로젝트 플러그인과 '첨부된 사진 "
            "식별' 기능이 포함됩니다. 이 기능은 관찰 기록에 첨부된 사진을 Pl@ntNet에 보내 "
            "상위 후보를 받습니다. 참조 엑셀을 선택하면 국명(한글명) 조회 및 국가생물종목록 "
            "정명 대조를 수행합니다. 출현 확률은 현재 조사/조사구 geometry에서 위치를 확인할 수 "
            "있고 로컬 확률 TIFF를 선택했을 때만 조회합니다. 위치나 TIFF가 없으면 사진 "
            "식별은 계속하지만 위치 기반 출현 확률 조회는 건너뜁니다(현장에서, 기기 내에서 직접 "
            "조회하며, 이 온디바이스 "
            "동작 방식은 아직 완전히 확정되지 않은 기술적 불확실성이 있습니다 -- 실패 시에도 "
            "관찰 기록 자체는 안전하게 보존됩니다). 자동으로 실행되는 기능이 아니라, 사용자가 "
            "'첨부된 사진 식별'을 직접 눌러야 하는 수동 실행 방식입니다. 세 후보 모두 채택하지 "
            "않고 이름을 직접 입력할 수도 있습니다."
        )

        # FR-QPB-117 (Decision Log D-45): the Pl@ntNet API key, collected as a masked secret
        # input, mirroring `ConnectivityBasemapPage.api_key_edit`'s treatment of the VWorld key.
        self.plantnet_api_key_edit = QLineEdit()
        self.plantnet_api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )  # NFR-QPB-010: masked in UI.

        # FR-QPB-115 (Decision Log D-45): a mandatory, explicit confirmation checkbox -- not
        # merely an informational label -- mirroring `ConnectivityBasemapPage.consent_checkbox`'s
        # disclosure content and structure, but naming Pl@ntNet/this project's Pl@ntNet
        # identification feature specifically.
        #
        # Bug 1 fix (checkbox/widget overlap): mirrors `ConnectivityBasemapPage.consent_checkbox`'s
        # structural fix above -- the full disclosure text is rendered by a separately
        # word-wrapped `QLabel` (this page's own established convention; see
        # `identification_intro_label`/`identification_key_note_label`), and the `QCheckBox`
        # itself carries only a short, single-line confirmation label. Its checked/unchecked state
        # remains the actual gate for `plantnet_consent_accepted`, unchanged.
        self.plantnet_consent_disclosure_label = QLabel(
            ".qgs 프로젝트 파일에 이 Pl@ntNet API 키가 읽을 수 있는 형태로(프로젝트 변수로) "
            "포함되며, 프로젝트 폴더를 받는 사람은 누구나 이 키를 추출할 수 있다는 점을 "
            "이해합니다. 가능하다면 Pl@ntNet 계정 설정에서 이 프로젝트 전용의, 사용량/할당량이 "
            "제한된 키를 사용하는 것을 권장합니다. 이는 온라인 VWorld 배경지도 키에 이미 적용 "
            "중인 것과 동일한 종류의, 공개하고 동의를 받은 위험입니다."
        )
        self.plantnet_consent_disclosure_label.setWordWrap(True)
        self.plantnet_consent_checkbox = QCheckBox("위 내용에 동의합니다")
        # NFR-QPB-072 (revised; Decision Log D-53): no longer the OS credential store -- an
        # application-managed, password-derived, locally-encrypted file (`credentials.enc`).
        self.plantnet_remember_checkbox = QCheckBox(
            "이 키 기억하기 (이 컴퓨터에 암호화하여 저장됨)"
        )
        # NFR-QPB-073: mirrors `ConnectivityBasemapPage.credential_status_label`.
        self.plantnet_credential_status_label = QLabel("")
        self.plantnet_credential_status_label.setWordWrap(True)

        identification_key_note_label = QLabel(
            "위 Pl@ntNet API 키는 아래 동의 체크박스를 선택해야만 생성되는 프로젝트에 포함됩니다 "
            "(FR-QPB-115). 동의하지 않으면 키는 어디에도 포함되지 않으며, '첨부된 사진 식별' "
            "기능 자체는 그대로 유지되지만 현장 조사자가 QField 안에서 직접 자신의 Pl@ntNet API "
            "키를 프로젝트 변수로 입력해야 합니다 -- 그 순간부터는 그 키가 휴대폰(QField "
            "프로젝트)에 존재하게 되어 그 프로젝트 폴더나 기기에 접근할 수 있는 사람이라면 누구나 "
            "추출할 수 있다는 점을 유의하세요 -- 클라이언트 측 키는 비밀로 간주해서는 안 됩니다."
        )
        # Bug 2 fix (window-sizing regression): this specific label -- on this specific page --
        # was the single largest contributor to the reported defect (verified empirically: before
        # this fix, this page's own `sizeHint()` width was the *widest* of all six pages, at 1365
        # logical px, wider even than the map-canvas-bearing `SiteInputPage`/
        # `ConnectivityBasemapPage` pages, purely because this long line of text had nowhere to
        # wrap). See the matching comments on `ProjectBasicsPage`/`SiteInputPage`'s own intro
        # labels above for the other two contributors. Both labels below keep that word-wrap fix.
        identification_intro_label.setWordWrap(True)
        identification_key_note_label.setWordWrap(True)
        layout.addWidget(_build_logo_banner_label())
        layout.addWidget(identification_intro_label)
        layout.addWidget(self.enable_checkbox)

        self.plantnet_group = QGroupBox("Pl@ntNet API 키 (선택 사항)")
        plantnet_layout = QFormLayout()
        plantnet_layout.setSpacing(_PAGE_SPACING)
        plantnet_layout.addRow("Pl@ntNet API 키:", self.plantnet_api_key_edit)
        plantnet_layout.addRow("", self.plantnet_consent_disclosure_label)
        plantnet_layout.addRow(self.plantnet_consent_checkbox)
        plantnet_layout.addRow(self.plantnet_remember_checkbox)
        plantnet_layout.addRow("", self.plantnet_credential_status_label)
        self.plantnet_group.setLayout(plantnet_layout)
        layout.addWidget(self.plantnet_group)
        layout.addWidget(identification_key_note_label)

        # D-95: the canonical taxonomy source is selected on this (existing) Step 5 page so the
        # wizard does not need a second, disruptive step-number migration. Discovery is fresh on
        # each visit; a preview is never treated as confirmation. The controls are also useful
        # when identification is disabled because Types 1-3 still materialize the lookup table.
        self.reference_source_path_edit = QLineEdit()
        self.reference_source_path_edit.setReadOnly(True)
        self.reference_source_status_label = QLabel(
            "이명정보를 포함한 관속식물류 국가생물종목록 엑셀 파일을 참조 자료로 이용하세요. "
            "선택하지 않으면 국명·학명·KTSN을 직접 입력합니다. 샘플은 가상 데이터입니다."
        )
        self.reference_source_status_label.setWordWrap(True)
        self.reference_source_preview = _ReferenceCandidateList()
        self.reference_source_preview.setProperty("compact_list", True)
        self.reference_source_preview.setMinimumHeight(34)
        self.reference_source_preview.setMaximumHeight(112)
        self.reference_source_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reference_sheet_preview_label = QLabel("선택한 참조표 미리보기 (처음 3행)")
        self.reference_sheet_preview_label.setVisible(False)
        self.reference_sheet_preview = QTableWidget(0, 0)
        self.reference_sheet_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reference_sheet_preview.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reference_sheet_preview.setAlternatingRowColors(True)
        self.reference_sheet_preview.setMinimumHeight(190)
        self.reference_sheet_preview.setVisible(False)
        # Candidate/upload cards grow to their wrapped content.  The page-level scroll viewport,
        # rather than this preview widget, owns vertical scrolling for long sample sets.
        reference_browse_button = QPushButton("사용자 .xlsx 업로드...")
        reference_browse_button.clicked.connect(self._browse_reference_source)
        reference_confirm_button = QPushButton("선택한 참조 자료 확인")
        reference_confirm_button.clicked.connect(self._confirm_reference_source)
        reference_group = QGroupBox("식물 분류 참조 자료 (선택 사항)")
        reference_layout = QVBoxLayout()
        reference_layout.addWidget(self.reference_source_status_label)
        reference_layout.addWidget(self.reference_source_preview)
        reference_layout.addWidget(self.reference_sheet_preview_label)
        reference_layout.addWidget(self.reference_sheet_preview)
        reference_layout.addWidget(self.reference_source_path_edit)
        reference_layout.addWidget(reference_browse_button)
        reference_layout.addWidget(reference_confirm_button)
        self.reference_clear_button = QPushButton("참조 자료 선택 해제")
        self.reference_clear_button.clicked.connect(self._clear_reference_source)
        reference_layout.addWidget(self.reference_clear_button)
        self.sample_download_button = QPushButton("가상 샘플 Excel 다운로드...")
        self.sample_download_button.clicked.connect(self._download_reference_sample)
        reference_layout.addWidget(self.sample_download_button)
        reference_group.setLayout(reference_layout)
        layout.addWidget(reference_group)
        raster_group = QGroupBox("출현 확률 TIFF (선택 사항)")
        raster_layout = QVBoxLayout(raster_group)
        raster_note = QLabel(
            "로컬 폴더에서 bce_inverse_corrected_probability_국명.tif 파일을 읽습니다. "
            "단일 밴드, 동일 격자·좌표계·자료형, NoData=-9999가 필요합니다. "
            "선택하지 않으면 출현 확률 조회를 생략합니다."
        )
        raster_note.setWordWrap(True)
        raster_layout.addWidget(raster_note)
        self.probability_source_path_edit = QLineEdit()
        self.probability_source_path_edit.setReadOnly(True)
        self.probability_source_path_edit.setPlaceholderText("선택한 TIFF 폴더 없음")
        raster_layout.addWidget(self.probability_source_path_edit)
        self.probability_browse_button = QPushButton("로컬 TIFF 폴더 선택...")
        self.probability_browse_button.clicked.connect(self._browse_probability_source)
        raster_layout.addWidget(self.probability_browse_button)
        self.probability_clear_button = QPushButton("TIFF 폴더 선택 해제")
        self.probability_clear_button.clicked.connect(self.probability_source_path_edit.clear)
        raster_layout.addWidget(self.probability_clear_button)
        layout.addWidget(raster_group)
        _install_page_scroll_container(self, layout)
        self.reference_source_preview.setFixedHeight(40)

        # Each UI item carries its own candidate object. In particular, source_kind is explicit
        # metadata from discovery/upload, never inferred later from a path or filename.
        self._reference_candidates: dict[str, dict] = {}
        self._selected_reference_candidate: dict | None = None
        self._confirmed_reference_source: dict | None = None
        self.reference_source_preview.itemClicked.connect(self._select_reference_candidate)
        self.reference_source_preview.itemActivated.connect(self._select_reference_candidate)

        self.registerField("plantnet_api_key", self.plantnet_api_key_edit)
        self.registerField("plantnet_consent_accepted", self.plantnet_consent_checkbox)
        self.registerField("plantnet_remember_key", self.plantnet_remember_checkbox)

        # FR-QPB-117's key-collection group is only meaningful once photo identification itself
        # is opted into -- mirrors `ConnectivityBasemapPage.online_group`'s visibility tied to
        # `online_radio`.
        self.enable_checkbox.toggled.connect(self.plantnet_group.setVisible)
        self.plantnet_group.setVisible(self.enable_checkbox.isChecked())

        # NFR-QPB-073/AC-QPB-097 (Decision Log D-53/D-55): deliberately NOT called here -- see
        # `ConnectivityBasemapPage.__init__`'s matching comment. Moved to `initializePage()`
        # below so this only ever runs at the point of actual page navigation.

    def initializePage(self) -> None:
        self._load_remembered_plantnet_key()

    def nextId(self) -> int:  # noqa: N802 - Qt API name.
        # Type 4 has no point layer, so its point-symbol page is not applicable.
        if str(self.wizard().field("survey_type") or "") == "vegetation_mapping":
            return 6  # ReviewAndBuildPage in this wizard's fixed page order.
        return super().nextId()

    def isComplete(self) -> bool:
        return (
            not self.reference_source_path_edit.text()
            or self._confirmed_reference_source is not None
        )

    def _clear_reference_source(self) -> None:
        self.reference_source_path_edit.clear()
        self._confirmed_reference_source = None
        self._selected_reference_candidate = None
        self._reference_candidates.clear()
        self.reference_source_preview.clear()
        self.reference_sheet_preview.clear()
        self.reference_sheet_preview.setVisible(False)
        self.reference_sheet_preview_label.setVisible(False)
        self.reference_source_status_label.setText(
            "참조 자료 없음: 국명·학명·KTSN을 직접 입력합니다."
        )
        self.completeChanged.emit()

    def _download_reference_sample(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "가상 참조 자료 샘플 저장", "taxonomy_sample.xlsx", "Excel workbook (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            shutil.copyfile(resource_path("samples", "taxonomy_sample.xlsx"), path)
        except OSError as exc:
            QMessageBox.warning(self, "샘플 저장 실패", f"샘플 파일을 저장할 수 없습니다: {exc}")
            return
        self.reference_source_status_label.setText(
            "가상 샘플을 저장했습니다. 안내 시트에서 입력 규칙을 확인하세요. "
            "샘플은 자동으로 프로젝트에 적용되지 않습니다."
        )

    def _browse_probability_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "출현 확률 TIFF 폴더 선택")
        if path:
            self.probability_source_path_edit.setText(path)

    def probability_reference_config(self) -> str | None:
        return self.probability_source_path_edit.text().strip() or None

    def _select_reference_candidate(self, item) -> None:
        candidate_key = item.data(Qt.ItemDataRole.UserRole)
        candidate = self._reference_candidates.get(candidate_key)
        if candidate:
            self._selected_reference_candidate = dict(candidate)
            self.reference_source_path_edit.setText(candidate["path"])
            self._show_reference_sheet_preview(candidate)
            self._confirmed_reference_source = None
            self.reference_source_status_label.setText(
                "선택한 파일의 미리보기를 확인했습니다. 계속하려면 ‘선택한 참조 자료 확인’을 누르세요."
            )
            self.completeChanged.emit()

    def _browse_reference_source(self) -> None:
        path, _ = _get_open_file_name(
            self, "식물 분류 참조 .xlsx 선택", "", "Excel workbook (*.xlsx)"
        )
        if not path:
            return
        self.reference_source_path_edit.setText(path)
        self._confirmed_reference_source = None
        preview = canonical_reference.inspect_ktsn_source_candidates(
            str(Path(path).parent), upload_path=path
        ).get("upload")
        upload_candidate = dict(preview or {
            "filename": Path(path).name,
            "source_kind": "user_upload",
            "validation_status": "invalid",
            "error_message": "업로드 파일 미리보기를 만들 수 없습니다.",
        })
        # The upload route owns this provenance classification, including when the selected file
        # happens to have the same name/path as a bundled candidate.
        upload_candidate["source_kind"] = "user_upload"
        upload_candidate["path"] = path
        self._selected_reference_candidate = upload_candidate
        self._show_reference_sheet_preview(upload_candidate)
        self.reference_source_preview.addItem(upload_candidate.get("filename") or "이름 없음")
        upload_item = self.reference_source_preview.item(self.reference_source_preview.count() - 1)
        upload_key = f"user_upload:{path}:{self.reference_source_preview.count()}"
        upload_item.setData(Qt.ItemDataRole.UserRole, upload_key)
        self._reference_candidates[upload_key] = upload_candidate
        if preview and preview.get("validation_status") == "valid":
            self.reference_source_status_label.setText(
                "업로드 파일 미리보기가 유효합니다. 파일/시트/헤더/샘플 행을 확인한 뒤 "
                "확인 버튼을 눌러 확정하세요."
            )
        else:
            self.reference_source_status_label.setText(
                (preview or {}).get("error_message") or "업로드 파일을 검증하지 못했습니다."
            )
        self.completeChanged.emit()

    def _show_reference_sheet_preview(self, candidate: dict) -> None:
        """Render all source workbook columns for the selected sample rows."""
        rows = list(candidate.get("source_rows") or candidate.get("sample_rows") or [])
        source_columns = candidate.get("source_columns")
        if source_columns:
            columns = [(column, column) for column in source_columns]
        else:
            columns = (
                ("status", "정이명"), ("korean_name", "대표국명"), ("scientific_name", "학명"),
                ("ktsn", "KTSN"), ("phylum", "Phylum"), ("class", "Class"),
                ("order", "Order"), ("family", "Family"), ("genus", "Genus"),
            )
        table = self.reference_sheet_preview
        table.clear()
        table.setRowCount(len(rows))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([label for _, label in columns])
        for row_index, row in enumerate(rows):
            for column_index, (key, _) in enumerate(columns):
                table.setItem(row_index, column_index, QTableWidgetItem(str(row.get(key) or "")))
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        self.reference_sheet_preview_label.setVisible(True)
        table.setVisible(True)

    def _confirm_reference_source(self) -> None:
        path = self.reference_source_path_edit.text().strip()
        if not path:
            self.reference_source_status_label.setText("먼저 .xlsx 참조 자료를 선택하세요.")
            self.completeChanged.emit()
            return
        candidate = self._selected_reference_candidate
        if not candidate or candidate.get("path") != path:
            self._confirmed_reference_source = None
            self.reference_source_status_label.setText(
                "미리보기에서 확인할 참조 자료를 다시 선택해 주세요."
            )
            self.completeChanged.emit()
            return
        source_kind = candidate.get("source_kind")
        if source_kind not in {"bundled_candidate", "user_upload"}:
            self._confirmed_reference_source = None
            self.reference_source_status_label.setText(
                "참조 자료의 출처를 확인할 수 없습니다. 다시 선택하거나 .xlsx를 업로드해 주세요."
            )
            self.completeChanged.emit()
            return
        result = canonical_reference.ingest_canonical_workbook(path, source_kind=source_kind)
        if not result.get("success"):
            self._confirmed_reference_source = None
            self.reference_source_status_label.setText(result.get("error_message", "참조 자료 검증에 실패했습니다."))
            self.completeChanged.emit()
            return
        self._confirmed_reference_source = {
            "path": path, "source_kind": source_kind,
            "sha256": result["provenance"]["sha256"],
            "source_filename": result["provenance"]["source_filename"],
            "validation_status": result["provenance"].get("validation_result", "valid"),
        }
        self.reference_source_status_label.setText(
            f"참조 자료를 확인했습니다: {Path(path).name} (종류: "
            f"{'사용자 업로드' if source_kind == 'user_upload' else '내장 후보'}, 검증: 유효)"
        )
        self.completeChanged.emit()

    def validatePage(self) -> bool:
        if self.isComplete():
            return True
        self.reference_source_status_label.setText(
            "선택한 .xlsx의 미리보기를 확인하거나 참조 자료 선택을 해제하세요."
        )
        return False

    def canonical_reference_config(self) -> dict | None:
        return dict(self._confirmed_reference_source) if self._confirmed_reference_source else None

    def _load_remembered_plantnet_key(self) -> None:
        """NFR-QPB-072 (revised)/NFR-QPB-073: mirrors `ConnectivityBasemapPage.
        _load_remembered_key`'s VWorld treatment -- reload a previously "remembered" Pl@ntNet key
        from the encrypted local store (`qfield_builder.credential_store`) so a fresh wizard
        reflects it, rather than always showing an empty field. The field keeps
        `EchoMode.Password` (NFR-QPB-010) regardless."""
        self.plantnet_remember_checkbox.setEnabled(credential_store.is_password_established())
        if not self.plantnet_remember_checkbox.isEnabled():
            self.plantnet_remember_checkbox.setToolTip(
                "암호화 저장 비밀번호가 설정되지 않아 사용할 수 없습니다."
            )

        try:
            saved_key = credential_store.get_remembered_plantnet_key()
        except credential_store.CredentialStoreLockedError:
            # NFR-QPB-073/AC-QPB-097: a remembered key exists but this session has not yet
            # supplied the password -- prompt here, at this specific point of use.
            password = self._password_prompt_fn(self)
            if password is None:
                return
            try:
                credential_store.unlock_session(password)
            except credential_store.CredentialDecryptionError:
                self.plantnet_credential_status_label.setText(
                    "비밀번호가 올바르지 않아 저장된 키를 불러올 수 없습니다. 이전에 저장된 "
                    "키는 복구할 수 없으며, 아래에 API 키를 직접 입력해야 합니다."
                )
                return
            except Exception:  # noqa: BLE001 - must never block the wizard.
                return
            try:
                saved_key = credential_store.get_remembered_plantnet_key()
            except Exception:  # noqa: BLE001 - a credential-store failure must not block wizard.
                saved_key = None
        except Exception:  # noqa: BLE001 - a credential-store failure must not block the wizard.
            saved_key = None
        if saved_key:
            self.plantnet_api_key_edit.setText(saved_key)
            self.plantnet_remember_checkbox.setChecked(True)


def _icon_from_svg_content(svg_content: str, size: int = 20) -> QIcon | None:
    """Rasterizes a fetched preview SVG's raw content into a small `QIcon` for the Step 6 results
    list (FR-QPB-011(d)(ii)/AC-QPB-117). Never raises -- malformed/unrenderable SVG content
    degrades to `None` (no preview image for that one result) exactly like a failed network
    fetch, never blocking search, never blocking selection, never crashing the wizard."""
    try:
        renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
        if not renderer.isValid():
            return None
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            renderer.render(painter)
        finally:
            painter.end()
        return QIcon(pixmap)
    except Exception:  # noqa: BLE001 - a bad preview image must never crash the wizard.
        return None


class _TablerPreviewFetchWorker(QThread):
    """Runs `symbol_styling.dispatch_preview_fetches_real` (FR-QPB-011(d)(ii)) on a background
    thread so waiting for the bounded-concurrency batch of live preview-SVG HTTP fetches never
    blocks the PySide6 UI event loop -- mirrors `BuildWorkerThread`'s identical rationale for the
    separate GIS-build subprocess wait. One name's fetch failing, or the dispatch call itself
    raising unexpectedly, never crashes this thread or drops any other name's own result
    (NFR-QPB-080(8)/AC-QPB-117)."""

    result_ready = Signal(list, dict)

    def __init__(self, icon_names: list[str], dispatch_fn, parent=None):
        super().__init__(parent)
        self._icon_names = list(icon_names)
        self._dispatch_fn = dispatch_fn

    def run(self) -> None:
        try:
            result = self._dispatch_fn(
                self._icon_names,
                on_result=lambda name, preview: self.result_ready.emit(
                    [name], {"previews": {name: preview}}
                ),
            )
        except Exception as exc:  # noqa: BLE001 - a failing preview batch must never crash.
            result = {
                "requested_names": self._icon_names,
                "previews": {
                    name: {
                        "success": False,
                        "svg_content": None,
                        "error": f"unexpected_error:{exc}",
                    }
                    for name in self._icon_names
                },
            }
        self.result_ready.emit(self._icon_names, result)


class SymbolStylingPage(QWizardPage):
    """Section 6.6/FR-QPB-120/FR-QPB-121/FR-QPB-123 (Decision Log D-61/D-65): accept the
    minimalist default point/polygon styling with no further action, or search Tabler's offline,
    build-time-bundled icon-name index (`qfield_builder.symbol_styling.
    search_bundled_tabler_icon_names`) and select one SVG icon to use as this project's own
    point-marker symbol -- applied uniformly to every point layer of the survey type already
    selected at Step 2 (FR-QPB-120's confirmed per-survey-type, not-per-layer, scope), never
    persisted or reused automatically by a later, separately generated project (AC-QPB-104).

    The final SVG fetch this page's own choice can ever cause at build time (FR-QPB-011(d)(i):
    fetching the *selected* icon's SVG content) happens later (`qfield_builder.build.
    _resolve_symbol_styling`), only once an icon has actually been selected here -- this page's
    own name-filtering search-as-you-type is always offline (FR-QPB-121), never a network
    request.

    A second, independent, narrower network-fetch trigger is also permitted here
    (FR-QPB-011(d)(ii)/NFR-QPB-080 clauses (5)-(8); Decision Log D-76): after the user's typing
    briefly settles (debounced, `_PREVIEW_FETCH_DEBOUNCE_MS`), a live preview SVG is fetched for
    each icon name currently visible in `results_list` -- never for a name not currently shown,
    never the full bundled index -- with bounded concurrency
    (`symbol_styling.PREVIEW_FETCH_MAX_CONCURRENCY`) on a background thread
    (`_TablerPreviewFetchWorker`) so it never blocks the UI. A missing/failed preview simply
    leaves that result's row without an icon; search-by-name and selection-by-name remain fully
    functional at all times regardless of this fetch's outcome (AC-QPB-117). This is purely
    additive to, and shares no state with, the pre-existing fetch-on-selection mechanism above.
    """

    #: FR-QPB-121's search itself is unbounded (filters the complete, ~6,184-name bundled index,
    #: Decision Log D-65); this cap is purely a UI/list-widget readability choice for this
    #: desktop-wizard search box, not a requirement of the specification itself -- distinct from,
    #: and unrelated to, FR-QPB-124's later, separate "no more than five displayed matches" cap
    #: for the KTSN accepted-name lookup dropdown.
    _MAX_DISPLAYED_MATCHES = 100

    #: NFR-QPB-080(6): "a fetch must not be issued on every keystroke, only after the user's
    #: input has briefly settled." The exact interval is an implementation detail the
    #: specification explicitly leaves to the implementer (mirrors Decision Log D-27/D-75).
    _PREVIEW_FETCH_DEBOUNCE_MS = 350

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("6단계 - 기호 스타일 설정")

        self.minimalist_radio = QRadioButton(
            "기본 미니멀 스타일 사용 (원형 점 기호 + 단색 채우기, 추가 작업 불필요)"
        )
        self.tabler_radio = QRadioButton("Tabler 아이콘을 검색하여 점 기호로 사용")
        self.minimalist_radio.setChecked(True)
        SiteInputPage._configure_tab_reachable_radio_group(
            (self.minimalist_radio, self.tabler_radio)
        )
        self.minimalist_radio.toggled.connect(self._on_mode_toggled)

        layout = QVBoxLayout()
        _polish_layout(layout)

        intro_label = QLabel(
            "이번에 생성할 프로젝트의 모든 지점(포인트) 레이어와 모든 폴리곤 레이어에 적용될 "
            "기호 스타일을 선택하세요. 이 선택은 프로젝트 전체에 한 번만 적용되며(레이어마다 "
            "따로 설정하지 않음), 나중에 같은 조사 유형으로 새 프로젝트를 생성하더라도 이번 "
            "선택이 자동으로 이어지지 않습니다 -- 매번 새로 선택합니다."
        )
        intro_label.setWordWrap(True)
        layout.addWidget(_build_logo_banner_label())
        layout.addWidget(intro_label)
        layout.addWidget(self.minimalist_radio)
        layout.addWidget(self.tabler_radio)

        self.tabler_group = QGroupBox("Tabler 아이콘 검색 (이름 검색 + 온라인 미리보기)")
        tabler_layout = QVBoxLayout()
        tabler_layout.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("아이콘 이름으로 검색 (예: leaf, map-pin)")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(24, 24))
        self.results_list.currentTextChanged.connect(self._on_icon_selected)
        self.selected_icon_label = QLabel("선택된 아이콘 없음")
        tabler_note_label = QLabel(
            "이름은 앱에 내장된 목록에서 검색하며, 미리보기 이미지는 온라인으로 불러옵니다. "
            "목록에서 "
            "아이콘을 하나 선택하면, 그 아이콘의 SVG 파일 하나만 Tabler로부터 다운로드하여 "
            "프로젝트에 포함시킵니다. 다운로드에 실패하거나(네트워크 없음 등) 아이콘을 선택하지 "
            "않으면, 기본 미니멀 점 기호가 그대로 사용되며 프로젝트 생성은 계속 진행됩니다."
        )
        tabler_note_label.setWordWrap(True)
        tabler_layout.addWidget(self.search_edit)
        tabler_layout.addWidget(self.results_list)
        tabler_layout.addWidget(self.selected_icon_label)
        tabler_layout.addWidget(tabler_note_label)
        self.tabler_group.setLayout(tabler_layout)
        layout.addWidget(self.tabler_group)

        _install_page_scroll_container(self, layout)

        self.registerField("symbol_styling_mode", self, "symbolStylingMode")

        self.tabler_radio.toggled.connect(self.tabler_group.setVisible)
        self.tabler_group.setVisible(self.tabler_radio.isChecked())

        self._selected_icon_name: str | None = None

        # FR-QPB-011(d)(ii)/NFR-QPB-080(6): a live preview-fetch batch is dispatched only after
        # the user's typing briefly settles, never once per keystroke -- a single, reused,
        # single-shot timer restarted on every keystroke achieves exactly that debounce.
        self._preview_debounce_timer = QTimer(self)
        self._preview_debounce_timer.setSingleShot(True)
        self._preview_debounce_timer.timeout.connect(self._dispatch_preview_fetch)

        # The real, production dispatch mechanism (bounded concurrency, NFR-QPB-080(7)) -- an
        # instance attribute (rather than calling `symbol_styling.dispatch_preview_fetches_real`
        # directly) so a test can inject a fake/failing double without needing to monkeypatch the
        # `symbol_styling` module itself.
        self._preview_fetch_dispatch = symbol_styling.dispatch_preview_fetches_real
        self._preview_worker: _TablerPreviewFetchWorker | None = None

    def _on_mode_toggled(self, _checked: bool) -> None:
        # Switching back to the minimalist default clears any icon previously chosen while
        # searching, so a stale selection can never silently survive a mode change back and forth
        # (FR-QPB-120: "accept the minimalist default... with no further action").
        if self.minimalist_radio.isChecked():
            self._selected_icon_name = None
            self.selected_icon_label.setText("선택된 아이콘 없음")
            self._preview_debounce_timer.stop()

    def _on_search_text_changed(self, text: str) -> None:
        # FR-QPB-121/FR-QPB-011(d)(i): filtered live, offline, from the bundled index -- never a
        # network request. The one *selection* network request this feature ever makes happens
        # only later, at build time, once an icon has actually been selected (`_on_icon_selected`
        # below only records the chosen *name*; nothing here or there ever fetches SVG content).
        result = symbol_styling.search_bundled_tabler_icon_names(text)
        self.results_list.clear()
        self.results_list.addItems(result["matches"][: self._MAX_DISPLAYED_MATCHES])

        # FR-QPB-011(d)(ii)/NFR-QPB-080(6): (re)start the debounce timer for the second,
        # independent live preview-fetch trigger -- restarting on every keystroke, rather than
        # firing immediately, is exactly what "not on every keystroke, only after input has
        # briefly settled" requires. Nothing to fetch when the results list is empty.
        self._preview_debounce_timer.stop()
        if self.results_list.count() > 0:
            self._preview_debounce_timer.start(self._PREVIEW_FETCH_DEBOUNCE_MS)

    def _dispatch_preview_fetch(self) -> None:
        # FR-QPB-011(d)(ii): only for the icon names actually visible/matched on screen right
        # now -- never an unbounded background prefetch of the full bundled index, never for a
        # result not currently rendered here.
        visible_names = [
            self.results_list.item(i).text() for i in range(self.results_list.count())
        ]
        if not visible_names:
            return
        worker = _TablerPreviewFetchWorker(visible_names, self._preview_fetch_dispatch, self)
        worker.result_ready.connect(self._on_preview_fetch_result_ready)
        worker.finished.connect(worker.deleteLater)
        self._preview_worker = worker
        worker.start()

    def _on_preview_fetch_result_ready(self, _requested_names: list, result: dict) -> None:
        # AC-QPB-117/NFR-QPB-080(8): a missing/failed preview simply leaves that one result's row
        # without an icon -- never blocks search, never blocks selection, never crashes. Applied
        # by matching on the result's own icon *name* against whatever `results_list` currently
        # shows, so a late-arriving batch for a since-superseded search never misapplies an icon
        # to an unrelated row.
        previews = result.get("previews", {}) if isinstance(result, dict) else {}
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            preview = previews.get(item.text())
            if not preview or not preview.get("success") or not preview.get("svg_content"):
                continue
            icon = _icon_from_svg_content(preview["svg_content"])
            if icon is not None:
                item.setIcon(icon)

    def _on_icon_selected(self, text: str) -> None:
        # `currentTextChanged` also fires with an empty string whenever `results_list.clear()`
        # runs at the start of every new search keystroke -- ignored here so a previously made
        # selection survives the user refining/adjusting their search text afterwards. The only
        # way to actually change or clear a selection is clicking a different result, or
        # switching back to the minimalist-default radio button (`_on_mode_toggled` above).
        if not text:
            return
        self._selected_icon_name = text
        self.selected_icon_label.setText(f"선택된 아이콘: {text}")

    def selected_tabler_icon_name(self) -> str | None:
        """The icon name currently selected from the search results, or `None` if none has been
        selected yet (in which case the minimalist default applies even if `tabler_radio` is
        checked -- the same defensive "no icon selected -> minimalist default" fallback
        `qfield_builder.build._resolve_symbol_styling` applies at build time, FR-QPB-121)."""
        return self._selected_icon_name

    def _get_symbol_styling_mode(self) -> str:
        return "tabler_icon" if self.tabler_radio.isChecked() else "minimalist"

    # See `ConnectivityBasemapPage.basemapMode`'s own comment: a real Qt `Property` is required
    # here too, or `wizard.field("symbol_styling_mode")` would silently return `None` instead of
    # this getter's value. Not mandatory (no trailing `*`) -- the minimalist default is always a
    # complete, valid choice requiring no further action (FR-QPB-120), so this page never blocks
    # the wizard's Next/Continue button.
    symbolStylingMode = Property(str, _get_symbol_styling_mode)


class ReviewAndBuildPage(QWizardPage):
    """Section 6.7: review summary, observable build job, progress, and final report."""

    def __init__(self, parent=None, *, password_prompt_fn=None):
        super().__init__(parent)
        self.setTitle("7단계 - 검토 및 생성")

        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        # The review summary is read-only output, not an input target.  Keeping it out of the Tab
        # chain lets Shift-Tab from the build action return to the native wizard bar/page controls.
        self.summary_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.build_button = QPushButton("생성")
        self.build_button.clicked.connect(self._start_build)
        self.cancel_build_button = QPushButton("생성 취소")
        self.cancel_build_button.clicked.connect(self._cancel_build)
        self.cancel_build_button.setVisible(False)
        # FR-QPB-008 (Decision Log D-10): reachable "select QGIS install location manually"
        # control, shown only once automatic (and any previously supplied manual) detection has
        # actually failed -- see `_start_build`/`_on_select_qgis_install_location`. Hidden by
        # default: this page must not suggest a manual override is needed before a runtime check
        # has ever actually failed.
        self.select_qgis_path_button = QPushButton("QGIS 설치 위치 선택...")
        self.select_qgis_path_button.clicked.connect(self._on_select_qgis_install_location)
        self.select_qgis_path_button.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)

        layout = QVBoxLayout()
        _polish_layout(layout)
        layout.addWidget(_build_logo_banner_label())
        layout.addWidget(self.summary_view)
        layout.addWidget(self.build_button)
        layout.addWidget(self.cancel_build_button)
        layout.addWidget(self.select_qgis_path_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.result_label)
        _install_page_scroll_container(self, layout)

        self._worker_thread: BuildWorkerThread | None = None
        self._build_succeeded = False
        # Minor Finding 2 (reviewer round, D-53/D-55): whether the most recent build's "Remember
        # this key" request(s) failed to actually persist -- see `_persist_remembered_keys`/
        # `_on_build_finished`.
        self._remember_persist_failed = False

        # FR-QPB-008: session-local only (never persisted across application restarts, matching
        # this project's deliberate no-`QSettings` convention) -- once a manually selected path has
        # been independently verified via `runtime.check_runtime(manual_path=...)`, it is reused
        # for subsequent build attempts within this same running wizard instance, so the user does
        # not have to re-pick it on every "생성" click.
        self._manual_qgis_path: str | None = None

        # NFR-QPB-073: mirrors `ConnectivityBasemapPage`'s injectable password-prompt seam --
        # used only by `_maybe_unlock_for_remembering` below, at the point a newly-checked
        # "Remember this key" request is actually about to be encrypted and persisted.
        self._password_prompt_fn = (
            password_prompt_fn if password_prompt_fn is not None else prompt_for_unlock_password
        )

    def initializePage(self) -> None:
        wizard = self.wizard()
        final_output_dir = compute_final_output_dir(
            wizard.field("output_dir"), wizard.field("project_display_name")
        )
        survey_type_value = wizard.field("survey_type")
        basemap_mode_value = wizard.field("basemap_mode")
        self.setTitle(
            "6단계 - 검토 및 생성"
            if survey_type_value == "vegetation_mapping"
            else "7단계 - 검토 및 생성"
        )
        summary_lines = [
            f"프로젝트 이름: {wizard.field('project_display_name')}",
            f"조사 유형: {_SURVEY_TYPE_LABELS_KO.get(survey_type_value, survey_type_value)}",
            f"배경지도 모드: {_BASEMAP_MODE_LABELS_KO.get(basemap_mode_value, basemap_mode_value)}",
            f"상위 폴더: {wizard.field('output_dir')}",
            f"생성될 프로젝트 폴더: {final_output_dir}",
            f"사진 식별 사용 여부: {_yes_no_ko(wizard.field('identification_enabled'))}",
        ]
        if survey_type_value != "vegetation_mapping":
            summary_lines.append(f"기호 스타일: {self._symbol_styling_summary_ko(wizard)}")
        reference_source = wizard.page(4).canonical_reference_config()
        if reference_source:
            source_kind = (
                "사용자 업로드"
                if reference_source.get("source_kind") == "user_upload"
                else "내장 후보"
            )
            validation_status = reference_source.get("validation_status", "valid")
            summary_lines.extend(
                [
                    f"참조 자료 파일명: {reference_source.get('source_filename') or Path(reference_source['path']).name}",
                    f"참조 자료 종류: {source_kind}",
                    f"참조 자료 검증 상태: {'유효' if validation_status == 'valid' else validation_status}",
                ]
            )
        else:
            summary_lines.append("식물 분류 참조 자료: 없음 (직접 입력)")
        probability_source = wizard.page(4).probability_reference_config()
        summary_lines.append(f"출현 확률 TIFF 폴더: {probability_source or '없음'}")
        if wizard.field("basemap_mode") == "online" and wizard.field("consent_accepted"):
            summary_lines.append(
                "경고: 생성되는 .qgs 프로젝트 파일에 VWorld API 키가 포함됩니다. 프로젝트 "
                "폴더를 받는 사람은 누구나 이 키를 추출할 수 있습니다."
            )
        if wizard.field("identification_enabled") and wizard.field("plantnet_consent_accepted"):
            # FR-QPB-115/NFR-QPB-071 (Decision Log D-45): mirrors the VWorld warning above.
            summary_lines.append(
                "경고: 생성되는 .qgs 프로젝트 파일에 Pl@ntNet API 키가 프로젝트 변수로 "
                "포함됩니다. 프로젝트 폴더를 받는 사람은 누구나 이 키를 추출할 수 있습니다."
            )
        if wizard.field("basemap_mode") == "offline":
            basemap_page: ConnectivityBasemapPage = wizard.page(3)
            offline_cfg = basemap_page.offline_config()
            summary_lines.append(
                f"오프라인 배경지도 출처: VWorld / {offline_cfg.get('layer') or '선택되지 않음'}"
            )
            if offline_cfg["bbox"] is not None:
                estimate = estimate_offline_basemap_size(
                    offline_cfg["bbox"],
                    offline_cfg["min_zoom"],
                    offline_cfg["max_zoom"],
                    DEFAULT_REPRESENTATIVE_TILE_BYTES,
                )
                summary_lines.append(f"오프라인 배경지도 범위: {offline_cfg['bbox']}")
                summary_lines.append(
                    f"오프라인 줌 레벨: {offline_cfg['min_zoom']}-{offline_cfg['max_zoom']}, "
                    f"예상 타일 수: {estimate['tile_count']}, "
                    f"예상 크기: {estimate['estimated_bytes'] / MIB:.1f} MiB "
                    f"(사전 생성 한도 900 MiB, 하드 한도 1 GiB)"
                )
        summary_lines.append(
            "참고: 생성된 프로젝트 폴더 전체를 휴대폰과 주고받으세요. QFieldSync로 패키징하지 "
            "마세요(README_TRANSFER_KO.md 참고)."
        )
        self.summary_view.setPlainText("\n".join(summary_lines))

    def _symbol_styling_summary_ko(self, wizard) -> str:
        """FR-QPB-040's review-screen "schema summary" -- a short, human-readable restatement of
        Step 6's own choice (Section 6.6/FR-QPB-123), mirroring the other summary lines above."""
        symbol_styling_page: SymbolStylingPage = wizard.page(5)
        icon_name = symbol_styling_page.selected_tabler_icon_name()
        if wizard.field("symbol_styling_mode") == "tabler_icon" and icon_name:
            return f"Tabler 아이콘 '{icon_name}' (점 기호)"
        return "기본 미니멀 스타일"

    def _collect_config(self) -> dict:
        wizard = self.wizard()
        config: dict = {
            "project_display_name": wizard.field("project_display_name"),
            "description": wizard.field("description"),
            "project_crs": wizard.field("project_crs"),
            "storage_crs": wizard.field("storage_crs"),
            "survey_type": wizard.field("survey_type"),
            "basemap": {"mode": wizard.field("basemap_mode")},
            "identification_enabled": bool(wizard.field("identification_enabled")),
        }
        if config["basemap"]["mode"] == "online":
            config["basemap"].update(
                {
                    # Bug 2 fix: strip whitespace/control characters (e.g. an accidentally
                    # embedded newline from a paste) from the key before it ever reaches the
                    # VWorld URL builders or the credential store -- see the matching defensive
                    # stripping in `credential_store.py` and `vworld.py`.
                    "vworld_api_key": (wizard.field("vworld_api_key") or "").strip(),
                    "layer": wizard.field("vworld_layer"),
                    "consent_accepted": bool(wizard.field("consent_accepted")),
                    "remember_key": bool(wizard.field("remember_key")),
                }
            )
            # FR-QPB-071 (revised; Decision Log D-26): pass through the live-discovered layer set
            # (if the user successfully refreshed it) so the build pipeline validates the chosen
            # layer against what the endpoint actually advertised, not just the static fallback
            # list -- see `qgis_worker._add_online_basemap_layer`'s `known_layers=` use.
            basemap_page: ConnectivityBasemapPage = wizard.page(3)
            known_layers = basemap_page.known_vworld_layers()
            if known_layers is not None:
                config["basemap"]["known_vworld_layers"] = known_layers
        elif config["basemap"]["mode"] == "offline":
            basemap_page: ConnectivityBasemapPage = wizard.page(3)
            config["basemap"].update(basemap_page.offline_config())
            # Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058): offline MBTiles generation genuinely
            # needs the VWorld API key during tile retrieval too -- the SAME `vworld_api_key`
            # field as online mode (`api_key_group` is now shared between both modes; see its
            # docstring in `ConnectivityBasemapPage.__init__`). Stripped, mirroring the
            # online-mode convention just above.
            config["basemap"]["vworld_api_key"] = (wizard.field("vworld_api_key") or "").strip()
            # Reviewer-round fix (compounding issue, FR-QPB-076 finding): `remember_checkbox` is
            # shown and enabled for offline mode too (see `ConnectivityBasemapPage.__init__`'s
            # docstring on why NFR-QPB-018's "remember this key" mechanism is not scoped to the
            # online-embedding case) -- it must actually have an effect here, exactly like the
            # online branch above, rather than being silently ignored. No `consent_accepted` key
            # is added for offline mode: FR-QPB-076's consent step concerns the online-embedding
            # risk specifically, and `build.py`'s offline branch never reads it.
            config["basemap"]["remember_key"] = bool(wizard.field("remember_key"))

        if config["identification_enabled"]:
            # FR-QPB-114-117 (Decision Log D-45): mirrors the VWorld `basemap` online-mode
            # config shape above for the Pl@ntNet key.
            config["plantnet"] = {
                # Bug 2 fix: see the matching `vworld_api_key` stripping above.
                "api_key": (wizard.field("plantnet_api_key") or "").strip(),
                "consent_accepted": bool(wizard.field("plantnet_consent_accepted")),
                "remember_key": bool(wizard.field("plantnet_remember_key")),
            }

        # Only explicit, confirmed local selections enter the build config.
        reference_source = wizard.page(4).canonical_reference_config()
        if reference_source:
            config["canonical_reference_path"] = reference_source["path"]
            config["canonical_source_kind"] = reference_source["source_kind"]
            config["canonical_reference_sha256"] = reference_source["sha256"]
        probability_source = wizard.page(4).probability_reference_config()
        if probability_source:
            config["probability_raster_source_dir"] = probability_source

        # FR-QPB-120/FR-QPB-121/FR-QPB-123 (Decision Log D-61/D-65): Step 6's symbol-styling
        # choice. `symbol_styling` is only ever added when the user both chose Tabler-icon mode
        # AND actually selected an icon from the search results -- otherwise it is omitted
        # entirely, which `qfield_builder.build.build_project` already treats as "use the
        # minimalist default" (HARNESS_CONTRACT.md: `mode` defaults to `"minimalist"` when this
        # key is omitted). This mirrors `SymbolStylingPage.selected_tabler_icon_name()`'s own
        # docstring: choosing Tabler mode without ever picking an icon still falls back to the
        # minimalist default, never a build failure.
        if config["survey_type"] != "vegetation_mapping":
            symbol_styling_page: SymbolStylingPage = wizard.page(5)
            if (
                wizard.field("symbol_styling_mode") == "tabler_icon"
                and symbol_styling_page.selected_tabler_icon_name()
            ):
                config["symbol_styling"] = {
                    "mode": "tabler_icon",
                    "tabler_icon_name": symbol_styling_page.selected_tabler_icon_name(),
                }

        # FR-QPB-025 ("when applicable to the selected survey type"): Type 1 ("Simple species
        # inventory") has no `site` entity in its schema at all (Section 8.1, DR-QPB-008), so no
        # `sites`/`sites_upload` entry must ever be produced for it here -- regardless of
        # `SiteInputPage`'s own UI-visibility state (`_update_applicability()`/`drawn_sites()`
        # already guard this too, but this is the authoritative point that decides what actually
        # reaches the build pipeline). FR-QPB-129 (Decision Log D-75/D-79): applies identically to
        # Types 2, 3, and 4 -- every survey type whose schema declares a `site` table at all.
        if config["survey_type"] != _SURVEY_TYPE_WITHOUT_SITE:
            # FR-QPB-025/FR-QPB-129: one or more drawn site boundaries bypass the upload path
            # entirely (`build.py::_resolve_seed_sites` checks `config["sites"]` before
            # `sites_upload`) -- `drawn_sites()` returns one `{"site_name", "geom_wkt"}` entry per
            # named, finished polygon from the drawing session (zero, one, or many), reusing the
            # exact list contract `_resolve_seed_sites()`/`_resolve_sites_from_upload()` already
            # implement for the upload path, requiring no `qfield_builder/build.py` change.
            site_input_page: SiteInputPage = wizard.page(2)
            drawn_sites = site_input_page.drawn_sites()
            if drawn_sites:
                config["sites"] = drawn_sites
            else:
                upload_path = wizard.field("sites_upload_path")
                if upload_path:
                    upload_format = site_upload.infer_format(upload_path)
                    site_name_field = wizard.field("sites_upload_site_name_field") or None
                    upload_config = {
                        "format": upload_format,
                        "path": upload_path,
                        "attribute_mapping": {"site_name": site_name_field},
                    }
                    if upload_format in ("shapefile", "zipped_shapefile"):
                        upload_config["encoding"] = (
                            site_input_page.upload_encoding_combo.currentData() or "cp949"
                        )
                        if site_input_page._upload_prj_missing:
                            upload_config["source_crs"] = site_upload.normalize_epsg_code(
                                site_input_page.upload_crs_edit.text()
                            )
                    config["sites_upload"] = upload_config
        # FR-QPB-008: threads any already-verified manual QGIS-install-path override through to
        # `build_project` (see `build.build_project`'s own comment), since the actual build runs
        # in a separate worker process where automatic detection must be re-attempted from
        # scratch. Omitted entirely (never a `None`/empty entry) when no manual override has been
        # verified this session, matching this module's own established "absent key means default
        # behavior" convention (e.g. `sites_upload` above).
        if self._manual_qgis_path:
            config["_manual_qgis_path"] = self._manual_qgis_path
        return config

    def _start_build(self) -> None:
        runtime_info = runtime.check_runtime(manual_path=self._manual_qgis_path)
        if not runtime_info["available"]:
            self.result_label.setText(runtime_info["message"])
            # FR-QPB-008: only ever shown once a runtime check has actually failed -- see
            # `_on_select_qgis_install_location`.
            self.select_qgis_path_button.setVisible(False)
            return
        self.select_qgis_path_button.setVisible(False)

        wizard = self.wizard()
        final_output_dir = compute_final_output_dir(
            wizard.field("output_dir"), wizard.field("project_display_name")
        )
        if final_output_dir is None:
            self.result_label.setText(
                "생성할 프로젝트 폴더를 결정할 수 없습니다. 1단계로 돌아가 프로젝트 이름과 "
                "상위 폴더를 확인해 주세요."
            )
            return

        self.build_button.setEnabled(False)
        self.cancel_build_button.setEnabled(True)
        self.cancel_build_button.setVisible(True)
        self.progress_bar.setVisible(True)
        if wizard.field("basemap_mode") == "offline":
            offline_page: ConnectivityBasemapPage = wizard.page(3)
            self.result_label.setText(
                f"VWorld / {offline_page.layer_combo.currentText().strip()} 오프라인 배경지도를 "
                "포함한 프로젝트를 생성하는 중입니다..."
            )
        else:
            self.result_label.setText("프로젝트를 생성하는 중입니다...")

        self._remember_persist_failed = False
        config = self._collect_config()
        self._maybe_unlock_for_remembering(config)
        # NEVER pass the raw selected parent directory to build_project -- it must always
        # receive the final, slug-derived project directory computed above (FR-QPB-021/022).
        self._worker_thread = BuildWorkerThread(config, final_output_dir, self)
        self._worker_thread.finished_with_result.connect(self._on_build_finished)
        self._worker_thread.progress_updated.connect(self._on_build_progress)
        self._worker_thread.start()

    def _on_build_progress(self, progress: dict) -> None:
        """Show the active build stage so a long input can be diagnosed without guessing."""
        stage = str(progress.get("stage") or "프로젝트 생성")
        elapsed = progress.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)):
            self.result_label.setText(f"{stage} 중... ({elapsed:.1f}초)")
        else:
            self.result_label.setText(f"{stage} 중...")

    def _cancel_build(self) -> None:
        """Request cancellation through the live worker; cleanup is completed in the worker."""
        if self._worker_thread is None:
            return
        self.cancel_build_button.setEnabled(False)
        self.result_label.setText("생성 취소를 요청했습니다. 진행 중인 작업을 정리하는 중입니다...")
        self._worker_thread.cancel()

    def _on_select_qgis_install_location(self) -> None:
        """FR-QPB-008: manual QGIS-install-path override, reachable once automatic detection has
        already failed (`select_qgis_path_button` is only visible in that state -- see
        `_start_build`). Opens a native folder picker (`QFileDialog.getExistingDirectory`) and
        re-verifies runtime detection rooted at the selected folder via the same real,
        subprocess-based `qgis_bridge` verification automatic detection uses
        (`runtime.check_runtime(manual_path=...)`), never a lighter-weight heuristic.

        On success: the selection is remembered for the remainder of this running wizard
        instance's session (`_manual_qgis_path`; never persisted across application restarts --
        this project deliberately has no `QSettings`/cross-session-settings mechanism), the
        control is hidden again, and the result label confirms the build is now available. On
        failure: shows the new, override-specific failure message from `check_runtime()` --
        distinct from the original generic "no installation found anywhere" message already
        shown before this control was used -- never that original generic text again.
        """
        directory = QFileDialog.getExistingDirectory(self, "QGIS 설치 위치 선택")
        if not directory:
            return
        runtime_info = runtime.check_runtime(manual_path=directory)
        if runtime_info["available"]:
            self._manual_qgis_path = directory
            self.select_qgis_path_button.setVisible(False)
            self.result_label.setText(
                "지정한 위치에서 QGIS 설치를 확인했습니다. 이제 '생성' 버튼을 눌러 프로젝트 "
                "생성을 계속 진행할 수 있습니다."
            )
        else:
            self.result_label.setText(runtime_info["message"])

    def _maybe_unlock_for_remembering(self, config: dict) -> None:
        """NFR-QPB-073: if the user opted into "Remember this key" for a key this session has
        not yet unlocked the encrypted store for (e.g. an encrypted-storage password was
        established in an earlier session, but nothing has been retrieved yet this session to
        have already unlocked it -- the most common first-use-of-"remember" case), prompt here,
        at the point a key is actually about to be encrypted and persisted.

        Never blocks the build itself (NFR-QPB-073: "must remain fully usable without ever
        supplying this password"): if the user declines/cancels, or no encrypted-storage password
        has ever been established at all (the decline-path fallback), the build proceeds
        regardless -- "Remember this key" simply has no persisted effect this time, exactly as if
        the checkbox had not been checked.

        Finding 1 fix (reviewer round, D-53/D-55): once the store is confirmed unlocked (either
        it already was, or this method just unlocked it), this method now also actually persists
        the requested key(s) itself, via `_persist_remembered_keys` below -- rather than relying
        on `qfield_builder.build.build_project()`'s own `apply_retention_policy`/
        `apply_plantnet_retention_policy` calls, which the real desktop application can never
        reach successfully, because `build_project()` always runs inside a freshly spawned,
        separate OS worker process (`qfield_builder.worker_process.run_job_in_subprocess`) whose
        own `credential_store` copy was never unlocked -- a fresh `multiprocessing`-`spawn`
        interpreter re-imports that module from scratch, so its module-level "unlocked" state is
        always `None` regardless of anything unlocked in this (the UI) process. Persisting here,
        in the UI process, is the one point this is guaranteed to actually be reachable."""
        wants_vworld_remember = bool(config.get("basemap", {}).get("remember_key"))
        wants_plantnet_remember = bool(config.get("plantnet", {}).get("remember_key"))
        if not (wants_vworld_remember or wants_plantnet_remember):
            return
        if not credential_store.is_unlocked():
            if not credential_store.is_password_established():
                return  # NFR-QPB-073 decline-path fallback: nothing to unlock or persist into.
            try:
                password = self._password_prompt_fn(self)
                if not password:
                    return
                credential_store.unlock_session(password)
            except Exception:  # noqa: BLE001 - a failed/declined unlock must never block the build.
                return
        self._persist_remembered_keys(config, wants_vworld_remember, wants_plantnet_remember)

    def _persist_remembered_keys(
        self, config: dict, wants_vworld_remember: bool, wants_plantnet_remember: bool
    ) -> None:
        """Finding 1 fix (reviewer round, D-53/D-55): actually writes a requested "Remember this
        key" key into the encrypted `credentials.enc` store, from this (the UI) process, which
        `_maybe_unlock_for_remembering` above has just confirmed is unlocked. See that method's
        own docstring for why this can no longer be left to `build_project()` alone.

        Reuses `credential_store.apply_retention_policy`/`apply_plantnet_retention_policy` (rather
        than calling `remember_key`/`remember_plantnet_key` directly) so this also updates the
        same in-memory, this-process session-key slots those functions already maintain, exactly
        as `build_project()`'s own (now real-subprocess-unreachable, but still in-process-valid)
        call to the same functions always has.

        Minor Finding 2 (reviewer round, D-53/D-55): tracks whether persistence actually
        succeeded in `self._remember_persist_failed`, so `_on_build_finished` can surface a
        best-effort, non-blocking, user-facing signal rather than failing completely silently."""
        if wants_vworld_remember:
            vworld_key = config.get("basemap", {}).get("vworld_api_key", "")
            if not credential_store.apply_retention_policy(vworld_key, True):
                self._remember_persist_failed = True
        if wants_plantnet_remember:
            plantnet_key = config.get("plantnet", {}).get("api_key", "")
            if not credential_store.apply_plantnet_retention_policy(plantnet_key, True):
                self._remember_persist_failed = True

    def _on_build_finished(self, result: dict) -> None:
        self.progress_bar.setVisible(False)
        self.build_button.setEnabled(True)
        self.cancel_build_button.setEnabled(False)
        self.cancel_build_button.setVisible(False)
        self._build_succeeded = bool(result.get("success"))
        if self._build_succeeded:
            message = f"프로젝트가 생성되었습니다: {result.get('project_dir')}"
            if result.get("basemap_provider") and result.get("basemap_layer"):
                message += (
                    f"\n오프라인 배경지도: {result['basemap_provider']} / "
                    f"{result['basemap_layer']}"
                )
            if self._remember_persist_failed:
                # Minor Finding 2 (reviewer round, D-53/D-55): a best-effort, non-blocking signal
                # -- the build itself still succeeded and is reported as such above.
                message += (
                    "\n참고: 입력하신 API 키를 암호화 저장소에 기억하지 못했습니다. 이번 "
                    "세션에서는 계속 사용할 수 있지만, 다음 실행 시 다시 입력해야 할 수 "
                    "있습니다."
                )
            self.result_label.setText(message)
        elif result.get("cancelled"):
            self.result_label.setText(
                "생성이 취소되었습니다. 부분 파일은 삭제되었습니다. 다시 생성하려면 '생성'을 "
                "눌러 주세요."
            )
        else:
            self.result_label.setText(
                f"생성 실패: {result.get('error_message') or result.get('error_code')}"
            )
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._build_succeeded


# Bug 2 fix (window-sizing regression): bounds this wizard's overall window size so that a
# real, packaged-app defect (reported by the stakeholder as a ~3222px-wide, almost entirely empty
# window on the sparse "Step 5 - Photo identification" page) cannot recur. `QWizard` grows to
# accommodate whichever page has had the largest natural content size *at any point during this
# wizard instance's lifetime*, and never shrinks back down for a later, sparser page -- this is
# documented Qt behavior (its internal page-area layout uses a size-hint-driven, monotonically
# non-shrinking geometry policy), not a bug in Qt itself, so the fix belongs here rather than in
# Qt. The three specific unwrapped long labels that were the single largest concrete contributors
# to that defect (`ProjectBasicsPage`'s parent-folder help text, `SiteInputPage`'s intro text, and
# -- empirically the single biggest one, at 1365 logical px wide before this fix --
# `IdentificationTogglePage`'s own intro text) are fixed at their own definitions above via
# `setWordWrap(True)`; the bounds below are a second, independent, structural safety net so that
# no single page's content -- present now, or added by any future change -- can ever again dictate
# an unboundedly large window for every other page. Chosen empirically (see the implementer's
# completion report for this round for the exact `sizeHint()`/`adjustSize()` measurements used to
# pick these numbers) to comfortably fit the widest genuinely-content-heavy pages (the
# `MapCanvas`-bearing drawing/offline-basemap states of `SiteInputPage`/`ConnectivityBasemapPage`,
# and `ConnectivityBasemapPage`'s online-VWorld-consent state) while remaining a small fraction of
# the reported defect's ~3222px width.
_WIZARD_MIN_SIZE = (900, 600)
_WIZARD_MAX_SIZE = (1200, 820)
_WIZARD_INITIAL_SIZE = (1000, 620)


def _initialize_safe_wizard_pixmaps(wizard: QWizard) -> None:
    """Install local pixmaps before Qt can resolve its platform defaults.

    On macOS, Qt 6.11's default ``QWizard::pixmap()`` path can pass a null URL to
    ``NSBundle.bundleWithURL`` when the wizard is shown.  That Objective-C exception is not
    catchable from Python and terminates the process.  Supplying a valid, application-owned
    pixmap for every role prevents the fallback lookup while keeping the wizard's actual branding
    in its page widgets (the FieldBuild Standalone logo banner is independent of QWizard's decoration
    pixmaps).  A transparent pixel is intentional: it is a valid local pixmap, not a path to a
    missing resource, and ModernStyle does not need a watermark/background image.
    """
    safe_pixmap = QPixmap(1, 1)
    safe_pixmap.fill(Qt.GlobalColor.transparent)
    for role in (
        QWizard.WizardPixmap.WatermarkPixmap,
        QWizard.WizardPixmap.LogoPixmap,
        QWizard.WizardPixmap.BannerPixmap,
        QWizard.WizardPixmap.BackgroundPixmap,
    ):
        wizard.setPixmap(role, safe_pixmap)


class ProjectBuilderWizard(QWizard):
    """The top-level seven-step wizard (Section 6).

    See the `_WIZARD_MIN_SIZE`/`_WIZARD_MAX_SIZE` module-level comment just above for the
    window-sizing fix applied in `__init__` below.

    Watermark/placeholder-image fix (visual-polish pass): every screenshot of this wizard shown
    to the stakeholder displayed a dated-looking tuxedo/bow-tie placeholder graphic down the
    left side of every page. Traced to its actual root cause (not guessed): this codebase never
    calls `QWizard.setPixmap()`/`setWizardStyle()` anywhere, so a plain `QWizard()` is left to
    Qt's own default `wizardStyle()` auto-detection, which -- on a real macOS Cocoa run, where
    `QApplication`'s active `QStyle` was previously the platform's native "macintosh" style --
    resolves to `QWizard.WizardStyle.MacStyle`. Empirically confirmed by direct probing
    (constructing a plain `QWizard`, explicitly setting `wizardStyle(QWizard.WizardStyle.
    MacStyle)`, and rendering it): `MacStyle` paints a `QWizard.WizardPixmap.BackgroundPixmap`
    down the left side whenever no custom background pixmap has been set via `setPixmap()` --
    and Qt itself ships a *built-in, non-empty default* for exactly that pixmap role (confirmed
    via `QWizard().pixmap(QWizard.WizardPixmap.BackgroundPixmap).isNull()` returning `False` on
    a totally default, freshly-constructed `QWizard`, before any code in this repository runs),
    which is literally the tuxedo/bow-tie image seen in every screenshot. Neither `ClassicStyle`
    nor `ModernStyle` render that pixmap role at all (confirmed the same way), so the genuine,
    correct fix is to stop `QWizard`'s auto-detection from ever choosing `MacStyle` in the first
    place: explicitly requesting `ModernStyle` below (which also fits the stakeholder's own
    "clean/flat modern" direction -- a plain banner-less, watermark-less page layout) rather than
    leaving this to platform-dependent, native-style-driven auto-detection.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._direct_page_for_programmatic_navigation: QWizardPage | None = None
        # FR-QPB-131/FR-QPB-132 (Decision Log D-81/D-82/D-86): the application's own display name,
        # plus its currently running version (`qfield_builder.__version__`), visible in the
        # wizard's own window title without requiring the user to inspect a file or run a command.
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{__version__}")
        # Initialize these before selecting the style or adding pages.  Both operations can cause
        # QWizard to query a decoration pixmap during the first show/restart sequence.
        _initialize_safe_wizard_pixmaps(self)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.addPage(ProjectBasicsPage(self))
        self.addPage(SurveyTypePage(self))
        self.addPage(SiteInputPage(self))
        self.addPage(ConnectivityBasemapPage(self))
        self.addPage(IdentificationTogglePage(self))
        self.addPage(SymbolStylingPage(self))
        self.addPage(ReviewAndBuildPage(self))

        self.setMinimumSize(*_WIZARD_MIN_SIZE)
        self.setMaximumSize(*_WIZARD_MAX_SIZE)
        self.resize(*_WIZARD_INITIAL_SIZE)

    def done(self, result: int) -> None:
        """Keep a running build's QThread alive until cancellation has cleaned up its worker."""
        review = self.page(6)
        worker = review._worker_thread if review is not None else None
        if worker is not None and worker.isRunning():
            review._cancel_build()
            return
        super().done(result)

    def setCurrentId(self, page_id: int) -> None:  # noqa: N802 - Qt API name.
        """Allow inspection callers to show an arbitrary page without filling earlier fields.

        ``QWizard.setCurrentId`` follows the normal forward-validation path on this Qt build, so
        a direct request for page 4 is ignored while page 1's mandatory fields are blank.  The
        desktop navigation buttons still use Qt's ordinary validated path; this small programmatic
        path only makes the public ``setCurrentId`` operation useful for page previews, diagnostics,
        and accessibility/layout tooling.  It deliberately does not alter any field or
        confirmation state and does not call point-of-use credential loaders.
        """
        target = self.page(page_id)
        if target is None:
            return
        native_current = super().currentPage()
        current = self._direct_page_for_programmatic_navigation or native_current
        if current is target:
            self._prepare_programmatic_preview_buttons(page_id)
            return

        # Let QWizard own the initial page and ordinary same-page calls.  Once a direct page is
        # requested, swap the page widgets in the existing page frame while keeping the native
        # button bar untouched and visible.
        if current is None or (self._direct_page_for_programmatic_navigation is None and page_id == super().currentId()):
            super().setCurrentId(page_id)
            return

        geometry = current.geometry()
        current.hide()
        target.setGeometry(geometry)
        target.show()
        target.raise_()
        self._direct_page_for_programmatic_navigation = target
        self._prepare_programmatic_preview_buttons(page_id)

    def currentPage(self) -> QWizardPage | None:  # noqa: N802 - Qt API name.
        if self._direct_page_for_programmatic_navigation is not None:
            return self._direct_page_for_programmatic_navigation
        return super().currentPage()

    def _prepare_programmatic_preview_buttons(self, page_id: int) -> None:
        """Keep the native bar in the focus chain while a page is shown programmatically."""
        last_page_id = self.pageIds()[-1] if self.pageIds() else -1
        next_button = self.button(QWizard.WizardButton.NextButton)
        finish_button = self.button(QWizard.WizardButton.FinishButton)
        if next_button is not None:
            next_button.setVisible(page_id != last_page_id)
        if finish_button is not None:
            finish_button.setVisible(page_id == last_page_id)
        for button_kind in (
            QWizard.WizardButton.BackButton,
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton,
        ):
            button = self.button(button_kind)
            if button is not None and button.isVisible():
                # This path is for non-mutating page inspection.  Real user navigation retains
                # QWizard's normal enabled/disabled validation state.
                button.setEnabled(True)
