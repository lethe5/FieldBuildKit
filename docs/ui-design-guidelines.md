# UI / Visual-Design Guidelines

> Owned and updated by: spec-writer
> Scope: durable, observable UI/visual-design conventions for the FieldBuild Kit desktop
> application (wizard styling, layout, and window sizing). This document is a **guideline**, not
> a traceable specification: nothing here is numbered as a formal FR/NFR/AC, and nothing here
> should be read as introducing or changing a functional or data requirement. Functional/data
> requirements remain in the relevant `specs/` feature artifact; see [documentation map](README.md).

## How to use this file

- Record a convention here only once it is actually implemented and stable, or once the
  stakeholder has explicitly directed it — this file documents real, current visual conventions,
  not proposals.
- If a functional requirement (e.g. what data a page collects, what a control does) needs to
  change, that belongs in `specs/qfield-project-builder.md`, not here.
- Known, unresolved cosmetic gaps should be recorded honestly as open items below, not silently
  marked resolved.

## Provenance

These conventions were introduced during a post-MVP-approval "macOS release checkpoint"
implementation phase, as a category-D (UX/visual-design refinement) pass over the existing
six-step wizard. They are cross-referenced from `specs/qfield-project-builder.md`'s Decision Log
(see the closing note following D-25), which records that these are intentionally kept out of the
core specification's numbered requirements, per this project's documentation-structure
conventions.

Source of truth for the exact values below: `qfield_builder/ui/app.py`
(`_apply_flat_modern_style()` and the module-level palette/stylesheet constants) and
`qfield_builder/ui/wizard.py` (`_PAGE_MARGINS`, `_PAGE_SPACING`, `_WIZARD_MIN_SIZE`,
`_WIZARD_MAX_SIZE`, `_WIZARD_INITIAL_SIZE`, and the `QWizard.WizardStyle.ModernStyle` selection).
If those values are changed in the code, this document should be updated to match — it describes
the actual current behavior, not an aspirational target.

## Application-wide Qt style and palette

- **Qt widget style**: `QApplication.setStyle("Fusion")`. Fusion is applied application-wide so
  every widget (across all seven wizard pages) renders consistently regardless of the host OS's
  native widget theme.
- **Wizard style**: `QWizard.WizardStyle.ModernStyle`, set explicitly via
  `self.setWizardStyle(QWizard.WizardStyle.ModernStyle)` in `ProjectBuilderWizard`. This was a
  deliberate fix: `QWizard`'s own platform-resolved default style rendered an unwanted placeholder
  watermark image on macOS, and `ModernStyle` is the style that does not render that pixmap role.
  Do not leave `QWizard`'s style unset/default, and do not switch to a different `WizardStyle`
  without re-checking the watermark behavior on every supported platform.
- **Palette** (a plain, light, neutral "clean/flat modern" palette — no dark mode, no saturated
  "branded" colors, a single restrained accent color for selection/focus/default-button
  highlighting):

  | Role | Hex value | Used for |
  |---|---|---|
  | Window background | `#f2f2f5` | `QPalette.Window`, `QPalette.Button` |
  | Base background | `#ffffff` | `QPalette.Base` (text-entry widget backgrounds) |
  | Alternate base | `#ececed` | `QPalette.AlternateBase` |
  | Text | `#1d1d1f` | `QPalette.WindowText`, `QPalette.Text`, `QPalette.ButtonText`, `QPalette.ToolTipText` |
  | Disabled text | `#9a9a9e` | Disabled-state `WindowText`/`Text`/`ButtonText`; also `QPalette.PlaceholderText` |
  | Border | `#c9c9cd` | Stylesheet borders on group boxes and input widgets (not a `QPalette` role) |
  | Accent | `#0a7cff` | `QPalette.Link`, `QPalette.LinkVisited`, `QPalette.Highlight`; default-button background; progress-bar chunk |
  | Accent text (on accent) | `#ffffff` | `QPalette.HighlightedText`; default-button text |
  | Bright/attention text | `#ff3b30` | `QPalette.BrightText` |

- **Base font size**: the application does not force a specific font family; it takes
  `QApplication`'s own default font and, if that font reports a positive point size, raises it to
  at least **11pt** (`font.setPointSize(max(font.pointSize(), 11))`). This is a floor, not a fixed
  size — a platform default already at or above 11pt is left unchanged.
- **Structural widget stylesheet** (layered on top of the Fusion style + palette above; kept
  generic/structural, with no page-specific selectors, so it is a one-time app-wide change):
  - `QGroupBox`: `font-weight: 600`, 1px solid border in the border color above, `border-radius:
    6px`, `margin-top: 10px`, `padding-top: 8px`; the group box title is positioned at the top
    margin, offset 10px from the left.
  - `QPushButton`: `padding: 4px 12px`, 1px solid border in the border color above,
    `border-radius: 4px`, window-background-color background (same neutral fill as
    `QPalette.Button`/`QPalette.Window`) -- so ordinary buttons ("Browse...", "Add photo", etc.)
    read as clearly bordered, clickable controls, consistent with the bordered look already given
    to text-entry widgets and group boxes.
  - `QPushButton:default` (the wizard's Next/Finish-style default button): accent-color
    background, accent-text-color text. This overrides the plain border/background above -- the
    default button keeps its existing accent treatment unchanged.
  - `QLineEdit`, `QPlainTextEdit`, `QTextEdit`, `QComboBox`, `QSpinBox`, `QListWidget`: `padding:
    4px 6px`, 1px solid border in the border color above, `border-radius: 4px`, base-color
    background.
  - `QProgressBar`: 1px solid border in the border color above, `border-radius: 4px`, centered
    text; `QProgressBar::chunk` uses the accent color with `border-radius: 4px`.

## Page layout: margins and spacing

Every wizard page's top-level and nested layouts use one shared, reused set of numbers
(`qfield_builder/ui/wizard.py`'s `_polish_layout()` helper), rather than independently-tuned
per-page values:

- **Page margins** (left, top, right, bottom): **12, 8, 12, 8** px.
- **Layout spacing**: **8** px between items, for the outer page layout. Nested rows use the same
  compact rhythm unless an interactive map requires its own fixed minimum surface.
- **Vertical growth:** ordinary group boxes use a minimum vertical size policy. Surplus page
  height stays below the content rather than being distributed into empty group-box interiors.

## Wizard window sizing

`ProjectBuilderWizard` bounds its own overall window size rather than leaving it fully
user-resizable or letting it grow unbounded to fit the largest page:

- **Minimum size**: 900 x 600 px (`setMinimumSize`).
- **Maximum size**: 1200 x 820 px (`setMaximumSize`).
- **Initial size**: 1000 x 620 px (`resize`), shown on first display.

These three bounds are shared module-level constants (`_WIZARD_MIN_SIZE`, `_WIZARD_MAX_SIZE`,
`_WIZARD_INITIAL_SIZE`) rather than per-page or per-platform values.

## Wizard content/button-bar layout (D-96; reconciled 2026-09-14)

[The layout specification](../specs/fieldbuild-kit-wizard-ui-layout-defect.md) records approval
on 2026-09-04. Current `wizard.py` implements `_PageContentScrollArea` and
`_install_page_scroll_container` for scrollable content above the native wizard button bar.
The minimum/initial heights above match current source (600/620 px). This corrects the old
"draft/not implemented" description; it does not claim every DPI or mobile check passed.
Later taxonomy auto-validation removes the separate candidate confirmation action; selected
valid uploads become ready immediately, as documented in [standalone](standalone.md).

## Resolved cosmetic gaps

- **Non-default `QPushButton` border/background (previously an open gap).** Ordinary, non-default
  push buttons (e.g. "Browse...", "Add photo") previously had only `padding` and `border-radius`
  from the structural stylesheet, with no explicit `border`/`background-color` of their own — they
  fell back to whatever the Fusion style rendered for an unstyled button, which looked visually
  inconsistent with the bordered look already given to text-entry widgets and group boxes. Fixed
  by adding an explicit `border: 1px solid #c9c9cd` (the same border color used elsewhere) and a
  `background-color` matching the window-background color (`#f2f2f5`, the same fill already used
  for `QPalette.Button`/`QPalette.Window`) to the `QPushButton` rule — see the updated rule in the
  palette/stylesheet table above. `QPushButton:default` is unchanged and still overrides this with
  its accent-color treatment.

## Branding: logo asset and its two confirmed uses (2026-08-28)

**Source asset.** `resources/fieldbuild-kit-logo.png` (2172x724px, RGBA PNG) is the
stakeholder-supplied logo asset for the application's "FieldBuild Kit" name, following the rename
recorded in `specs/qfield-project-builder.md`'s Decision Log D-81 (the rename decision itself) and
D-86 (the specific name corrected from "QFieldKit" to "FieldBuild Kit"), both confirmed 2026-08-28.
Its actual composition, confirmed by direct visual inspection of the file so a future reader does
not need to re-open the image to understand what it contains: a horizontal lockup consisting of
(a) a distinct, roughly-square icon mark on the left — a stack of layered map tiles (green/teal/
dark tones) with a location pin on top — occupying roughly the left third of the image's width as
a genuinely square-ish, cleanly separable sub-region, and (b) the "FieldBuild Kit" wordmark, in a
dark-green/bright-green two-tone treatment, to the right of the icon mark.

**Confirmed decision: two uses.** Asked directly (multi-select), the stakeholder confirmed both of
the following uses for this one source asset:

1. **Wizard banner.** Displayed as a banner at the top of the desktop wizard's own UI. Exact
   placement — every wizard page vs. only the first page — is left to implementer discretion,
   consistent with this document's own convention for implementer-authored UI-detail decisions
   (mirroring, e.g., the version-display placement left to implementer discretion by Decision Log
   D-82/D-27 in the specification).
2. **macOS app icon.** Replaces `resources/app-icon-glass.icns`, currently referenced by
   `packaging/qfield_builder.spec`, as the packaged macOS application's own icon. Because an app
   icon must be square and this source asset is a wide horizontal lockup, the new icon must be
   regenerated from **only the icon-mark sub-region** described above (the map-layers-with-pin
   graphic) — never the full wide image and never the wordmark text. Cropping/regenerating a
   proper square icon, and (on macOS) a full `.icns` iconset at the standard multiple resolutions,
   from that sub-region is implementer work; this entry does not specify an exact crop rectangle or
   pixel dimensions.

**Category D, no spec-level change.** This is a pure branding/asset-placement decision: no
wizard step's behavior, no generated-project output, and no acceptance criterion changes as a
result. Per this project's Category D ("UX/visual-design refinement") routing convention
(`CLAUDE.md`'s "User-feedback triage and change control" section; `docs/change-control.md`), it is
recorded here, not as new FR/AC text in `specs/qfield-project-builder.md`.

**Reconciliation is bundled implementer work, not itemized here.** Per Decision Log D-81/D-86's
own "test-designer/implementer discovery work" framing for locating every remaining literal
occurrence of the prior application name, every other place `resources/app-icon-glass.icns` or the
prior "QField Project Builder"/"QFieldKit" branding is referenced (application source, packaging
configuration, README, in-app text, etc.) should be reconciled with this new logo asset and the
"FieldBuild Kit" name as part of the same implementer pass that lands the wizard banner and the
regenerated app icon — not itemized file-by-file in this document.

**Status.** Confirmed by the stakeholder; not yet implemented as of this entry. Once implemented,
this section should be updated in place to record the actual banner placement chosen and the
actual icon-generation mechanism/output paths used, mirroring this document's existing "describes
actual current behavior, not an aspirational target" discipline (see Provenance above) — update
this section, or add a short dated follow-up note, rather than leaving it silently stale.

## Draft: standalone HTML report visual refinement (2026-08-31)

**Status: DRAFT — user-directed design change; awaiting specification approval before any
implementation or test work.**

**Applies to:** the standalone HTML artifact generated by `qfield_builder/qml_plugin.py`. This is
a Category-D visual refinement of the report described by `specs/fieldbuild-kit-five-fixes.md`
and `specs/html-report-interactive-analytics.md`; it does not introduce a new report data model,
change report behavior, or move generated output.

**Non-normative evidence note:** the supplied screenshot and existing report artifact may be used
for comparison and defect discovery only. They are evidence, not a visual or functional
instruction, and the two report specifications remain authoritative for behavior.

### Decision Log

- **D-UI-HRA-001** (2026-08-31, Category D — user-directed visual refinement; supersedes none):
  The user explicitly directed: **“make the generated HTML report prettier using the installed
  html-report skill from Sologa/codex-html-report-skill.”** The design basis is the installed
  `html-report` skill's quality bar: a polished, self-contained single HTML document that is
  responsive at 375px, has persisted dark mode, print and reduced-motion support, anchor-linked
  sections with a sticky table of contents, coherent report components, accessible focus and
  contrast, and no inline `style` attributes. This entry records presentation only. All prior
  report decisions and history remain intact, including local/offline-safe behavior, joined-data
  semantics, CSV behavior, Korean text, escaping, one-time initialization, and current
  project-folder output.

### Visual and interaction direction

- **Document shell:** Use one polished, self-contained HTML document. Keep structural CSS in a
  single document-level `<style>` block; do not add `style="..."` attributes. Existing embedded
  report libraries and the already-approved runtime map-tile enhancement remain the only allowed
  dependency boundary: do not add remote scripts, stylesheets, fonts, images, analytics, or
  service calls.
- **Hierarchy:** Present a clear report header with project metadata, a summary-card row, and
  visually distinct sections for the map, analytics/joined data, record details, and limitations
  or status notices. Use one restrained accent, readable surface/border treatments, consistent
  corner radii and spacing, and a clear distinction between primary actions and secondary controls.
- **Navigation:** Every report section heading has a unique stable `id` and an adjacent anchor
  link. When the report has more than two top-level sections, show a sticky table of contents on
  wider viewports; it must collapse or become a normal-flow navigation block on narrow screens.
  Navigation must not cover headings, map content, table headers, or focused controls.
- **Toolbar and controls:** Keep filter/search, sort affordances, CSV scope choice/action, map
  controls, detail actions, collapsible-summary controls, and the dark-mode control visually
  grouped and clearly labeled. Controls must wrap without clipping and must retain their existing
  behavior and labels where those labels are part of the report contract.
- **Map:** Give the map a stable card-like frame with a readable height, clear local-feature
  contrast, visible background/attribution/status treatment, and an explicit empty/offline state.
  The styling must distinguish local features from a VWorld/OpenStreetMap background without
  implying that remote tiles are required for local map interaction.
- **Joined table:** Keep the joined table legible inside a responsive container. Preserve visible
  filter state, row-count feedback, deterministic sort affordances, null/orphan markers, Korean
  values, and the existing filtered/all-rows CSV choice. A wide table may scroll inside its own
  labeled region on small screens, but the page itself must not overflow horizontally.
- **Details and summaries:** Use consistent cards/details panels for summary counts, per-record
  detail, integrity notices, and limitations. Collapsing a summary must remain a presentation
  change only: it must not remove rows from the joined table or features from the map.
- **Theme:** Provide a visible light/dark toggle with an accessible name and state. Persist the
  user's choice in `localStorage` and restore it on the next open; if storage is unavailable, the
  toggle still works for the current document without blocking report use. Both themes must keep
  Korean text, map features, controls, tables, notices, and focus indicators readable.
- **Print and motion:** Include a print stylesheet that produces a readable, unclipped report with
  appropriate light surfaces, visible data, and no control-only clutter. Respect
  `prefers-reduced-motion: reduce` by removing or shortening non-essential transitions and
  animations; map/table/detail controls must remain usable.
- **Accessibility:** Keyboard focus must be visibly distinct on every interactive control, focus
  order must follow the document hierarchy, and color must not be the sole signal for state or
  status. Text and control labels must meet a contrast target of at least 4.5:1 for normal text
  and 3:1 for large text or controls against their adjacent surfaces.

### Design-review acceptance criteria

These are stable design-review criteria for this Category-D entry, not new formal FR/NFR/AC
requirements. They must be reviewed alongside the functional acceptance criteria already present
in the two report specifications.

- **DAC-HRA-001:** Given the existing report data and generation flow, the refinement changes
  presentation only: no report field, join key, relationship, geometry payload, species/date
  aggregation rule, or other data-model element is added, removed, renamed, or reinterpreted.
- **DAC-HRA-002:** Given a generated report opened from the current project folder, one HTML file
  contains the report markup, CSS, and required local runtime code; no new remote dependency is
  required for rendering, filtering, sorting, details, summaries, or CSV construction, and no
  element uses a `style` attribute.
- **DAC-HRA-003:** At a 375px-wide viewport, the report has no page-level horizontal overflow;
  the header, cards, sticky/flow navigation, toolbar, notices, map, detail panel, and controls
  remain readable and actionable; any wide joined table scroll is contained within the table
  region and does not move the page shell.
- **DAC-HRA-004:** With at least three report sections present, each section heading has a unique
  stable anchor target, every table-of-contents link reaches its target, and the sticky navigation
  does not obscure the target heading or focused content on desktop or mobile layouts.
- **DAC-HRA-005:** Toggling light/dark mode updates the report without losing the current filter,
  sort, expanded-details, map, or CSV-selection state; reopening the same report restores the
  selected theme from `localStorage` when available.
- **DAC-HRA-006:** Print preview produces readable project metadata, summary cards, local map
  content/status, joined data, detail/limitation content, and Korean text without clipped cards or
  table columns; nonessential navigation and control chrome is not printed as distracting content.
- **DAC-HRA-007:** Under `prefers-reduced-motion: reduce`, non-essential CSS/JS motion is disabled
  or minimized and all report actions remain available without requiring animation completion.
- **DAC-HRA-008:** The map card renders all usable local features exactly as before, keeps invalid
  or missing-geometry records available outside the map, shows an explicit no-network/no-valid-
  geometry state, and keeps local map interaction usable when both remote backgrounds fail.
- **DAC-HRA-009:** The joined table still renders exactly the existing joined rows, preserves
  one-to-many rows and orphan markers, filters across its existing visible fields, sorts each
  visible column deterministically, and updates visible-row feedback without mutating source data.
- **DAC-HRA-010:** The CSV action remains visible and keyboard/mouse actionable, its filtered/all-
  rows choice is explicit, and the exported UTF-8 CSV contains exactly the chosen existing joined
  rows with stable headers and correct quoting for commas, quotes, newlines, Korean text, and
  other non-ASCII values.
- ~~**DAC-HRA-011 (original; superseded for mapped-feature activation by Decision Log D-HRA-005):**
  Clicking a mapped feature or opening a record detail still exposes the same stable UUID,
  human-readable labels, values, and joined-parent context; HTML-looking field data remains inert
  text in cards, details, tables, notices, popups, and metadata.~~
- **DAC-HRA-011 (reconciled; Decision Log D-HRA-005):** Mapped-feature pointer clicks and the
  existing keyboard activation path use the core specification's one-popup contract: exactly one
  transient Leaflet popup is adjacent to the clicked feature, with no duplicate right-side custom
  detail panel. Observation popups show only `조사일`, `조사자`, `국명`, and `학명`; site/`조사지`
  popups show only the site name. Popup values remain inert escaped text and feature labels are not
  permanently visible on the map. Other report data, geometry, and export behavior remain governed
  by the core specification.
- **DAC-HRA-012:** A report with Korean metadata, labels, field values, notes, empty states, and
  limitation notices displays without mojibake or clipping, and the same Korean content remains
  correctly encoded in CSV output.
- **DAC-HRA-013:** Opening or reloading the report performs one initialization of the map, table,
  controls, event handlers, and summary/detail views: no duplicate map, controls, rows, event
  effects, or initialization fragments appear after one or more reloads or theme changes.
- **DAC-HRA-014:** The report continues to show the current project-folder destination and exact
  resulting HTML/CSV paths; the visual refinement adds no outside-project picker, upload,
  synchronization, or alternate output location.
- **DAC-HRA-015:** Keyboard-only review reaches the theme toggle, navigation links, filter/sort
  controls, collapsible sections, map feature details, CSV controls, and detail actions in a
  logical order; each focused control has a visible non-color-only focus treatment and no
  contrast failure is apparent in either theme.

**Implementation status:** Implemented (2026-08-31). Final section order is overview, map, survey
summary, species, joined table, and source records. The implemented theme uses light/dark surface,
ink, border, accent, warning, map, and focus tokens; print output keeps report content and hides
navigation/control chrome; the existing project-folder output boundary and optional/offline map
background remain unchanged. This metadata records observed implementation details only and does
not change the approved criteria or report data/output contract.

## QField plugin toolbar action icons (2026-09-04)

**Status: implemented (2026-09-04); stakeholder-approved Category D convention.** The QField plugin
toolbar's two primary actions use compact, icon-only, round controls rather than large text
buttons:

- **HTML report export:** QField `Theme` icon `ic_file_download_white_24dp`.
- **Photo plant identification:** QField `Theme` icon `ic_search_white_24dp`.

The toolbar controls have no visible text. Their accessible action names remain Korean —
`HTML 보고서 내보내기` and `사진으로 식물 동정` respectively — and each maintains a
48px-class touch target. This convention changes presentation only: it does not alter either
action's callback, plugin registration, feature-form identification control, data, or semantics.

**Category B correction — Decision Log D-97 (APPROVED, 2026-09-04).**
The preceding `Theme` identifiers and the criterion requiring them are retained as historical,
superseded presentation guidance. iPhone-QField evidence showed blank icon targets and duplicate
toolbar controls, so icon-source portability and registration count are now generated-project
requirements in `specs/qfield-project-builder.md` FR-QPB-143 and AC-QPB-147–148 rather than a
best-effort visual convention. The corrected active convention is:

- Every generated project contains the self-contained, project-local
  `icons/report-export.svg`; an identification-enabled project additionally contains
  `icons/plant-identification.svg`. Neither toolbar icon depends on a QField `Theme` identifier,
  `qrc:` resource, or external SVG resource.
- The identification-enabled sidecar has exactly two 48px-by-48px icon-only `QfToolButton`
  controls, one per asset, each registered once. When identification is disabled, the
  unconditional report-export control remains alone and the plant-identification control/asset
  remains absent under the existing sidecar-content boundary.
- No button text is visible. The accessible Korean action names remain exactly
  `HTML 보고서 내보내기` and `사진으로 식물 동정`; their existing callbacks, the
  feature-form `사진으로 동정하기` control, consent/key boundaries, and the
  `<project_slug>.qml` project-plugin convention are unchanged.
- iPhone QField visual verification is required to confirm two nonblank icon targets and no
  duplicate registration for the identification-enabled case, because no local test runner
  emulates QField iOS.

### Design-review criteria

- The QField toolbar shows exactly the two compact round icon controls above, with no visible
  `Export HTML Report` or `사진으로 식물 동정` button text.
- Each icon resolves through the specified existing QField `Theme` icon identifier and has its
  corresponding Korean accessible action name.
- Each toolbar target remains approximately 48px square or larger, and activating it invokes the
  same existing action as before.
- The feature-form photo-identification control and the plugin registration surface are unchanged.

### Corrected design-review criteria — Decision Log D-97 (APPROVED)

- The `Theme`-identifier criterion above is superseded only for these two plugin-toolbar icons;
  their Korean accessible names, no-visible-text treatment, and 48px target size remain active.
- Structural review confirms the required project-local SVG file(s), each `QfToolButton`'s
  project-relative SVG source, exactly-once registration, and the applicable one- versus
  two-button condition.
- iPhone QField review confirms the rendered icon target(s) are nonblank and nonduplicated and
  that activating each retains its existing action.

## Route and geometry controls (approved baseline; implementation unverified)

The initial point/line/polygon drawing selection and collapsible QField bottom route panel baseline,
including the 2026-09-15 provider clarification and the approved 2026-09-16 workflow/progress slice,
are recorded in [survey-route-planner](../specs/survey-route-planner.md). Native QField/iOS/Android
layout and interaction remain unverified, so these controls are not established shipped visual
conventions. Expanding the panel or loading a saved route must not trigger optimization. Existing
toolbar icon requirements remain active; adding route UI must preserve existing report/identification
actions and avoid duplicate registrations.

### In-control labels, scoped guidance and map-start marker (approved 2026-09-16)

This approved Category D convention implements D-SRP-031~033 without changing stored layer IDs,
actual field names, route data or source renderers.

- The scope, start, target-layer, ID-field, name-field and optional completion-field selectors use
  an in-control floating label matching the visual treatment of the ORS server URL field. The exact
  labels are `조사 경로 계산 대상`, `출발지`, `조사지 레이어`, `조사지 ID 필드`,
  `조사지 이름 필드` and `조사지 완료 필드(Boolean)`. They sit within the control chrome rather
  than in separate rows, stay legible for empty/value/focus/error states, and reserve enough inset
  that selected option text never collides with them. A placeholder is not the only accessible name.
- User-facing copy says `조사지`; internal `site` roles/source names and actual field values remain
  technical stored identifiers. Target options lead with the site name and show the stable ID as
  `이름 · ID`. The choices refresh before an empty required target is validated, so a blank current
  value cannot prevent the dropdown from showing the current scope's candidates.
- The general scope explanation remains directly below the scope selector. Only for `선택 대상`, the
  next line reads `조사지 레이어를 열고 피처 선택/체크 도구로 계산할 조사지를 선택한 뒤 이 패널로
  돌아오세요. 현재 선택한 조사지: N개`. `전체 대상` and `미조사 대상` hide this line and its
  layout space. Validation remains below the related control/help group.
- After `지도 중심을 출발지로 지정`, the captured center shows exactly one high-contrast temporary
  start marker with a non-color `출발지` cue. Panning does not move it; choosing the center again moves
  the same marker. It survives panel collapse/reopen and calculation success/failure so the user can
  verify the input, then disappears when the start mode changes, the value is cleared/invalidated or
  the project closes. It is visually distinct from route lines, incomplete/completed site symbols and
  the current-position indicator.

#### Approved design-review criteria

- At 320px and wider panel widths, all six floating labels remain visible without a separate label
  row, clipping, collision, horizontal scrolling or loss of keyboard/touch focus indication.
- Screenshots for all three scopes show the common explanation; only the `선택 대상` screenshot shows
  the selection procedure/count immediately after it, with no blank row in the other two states.
- A map interaction review shows one marker at the captured center, a fixed marker after pan/zoom, a
  moved rather than duplicated marker after reselection, and removal at every specified lifecycle end.
- A duplicate-name fixture shows `이름 · ID` target options; a blank/stale selection still shows the
  newly populated choices before displaying the required-selection error.

### Route-panel follow-up convention (approved 2026-09-17)

**Status: APPROVED — 2026-09-17.** This Category B/D follow-up mirrors
D-SRP-036~041 and FR-SRP-034~039 in
[survey-route-planner](../specs/survey-route-planner.md). It preserves the approved 2026-09-16
behavior above except where this approved slice explicitly replaces label wording/presentation and
out-of-order checklist input. It does not change stable layer IDs, actual field names, route data,
source attributes or the original layer geometry.

#### Approved design decisions (2026-09-17)

- **D-UI-SRP-001 (approved 2026-09-17):** Use one outlined floating-label component for both text fields and dropdowns.
  The label rests in the control outline with a surface-colored notch behind it, remains visible in
  empty, value, focus, disabled and error states, and reserves space for dropdown indicators and
  selected text. Apply it to the exact labels `조사지`, `조사지 ID 필드`, `조사지 이름 필드`,
  `조사 완료 필드`, `계산 대상`, `출발지` and `저장할 경로 이름`. This supersedes only the six
  longer label strings and their in-control placement in the approved convention above. Help text,
  validation, stored values and target options retain their existing meanings.
- **D-UI-SRP-002 (approved 2026-09-17):** Put the road-provider controls inside an `API URL/키 설정` disclosure that is
  collapsed when the route panel first opens. Its collapsed summary does not show a key value.
  Expanding it shows `ORS 서버 URL`, `VROOM 서버 URL`, backend/profile, masked API key, timeout,
  road offset, objective and `서버 설정 저장 (키 제외)`. The disclosure retains a clear expanded
  state, a touch/keyboard target and an accessible expanded/collapsed state.
- **D-UI-SRP-003 (approved 2026-09-17):** Place persistence copy beside the masked key and save action. A manually entered
  key reads `이번 세션만 사용`; a key loaded from the consented plaintext project variable reads
  `프로젝트 파일의 평문 키 사용 중` and keeps the plaintext warning visible without revealing the
  value. Successful non-secret settings save feedback identifies the current project scope, the
  actual project-relative `survey-routes.a.json` or `survey-routes.b.json` path, and `키 제외`.
  Failure feedback uses the same status region and never resembles success.
- **D-UI-SRP-004 (approved 2026-09-17):** In the visit checklist, the earliest incomplete stop is the only incomplete row
  with an enabled completion checkbox. Later incomplete rows remain readable but disabled and expose
  `다음 방문 지점부터 순서대로 완료하세요.` through visible or accessible reason text. Completed
  rows remain enabled for uncheck. If uncheck or an external Boolean field creates a gap before a
  later completed stop, show the later row as `순서 밖 완료`; keep the check and completion color,
  and use text or an icon so color is not the only signal. Show the current next stop in feedback
  when a user attempts an unavailable completion action.
- **D-UI-SRP-005 (approved 2026-09-17):** Generated polygon `조사지` uses a visible non-gray accent outline and a related
  translucent fill; the approved default is green `#2E7D32`. It remains distinct from the blue
  completion overlay, blue route line and orange start marker on supported light and dark basemaps.
  Point, line and polygon site features display the configured name-field value as a map label with
  a white buffer/halo. Empty names produce no label, and data that resembles markup remains inert
  text. Labels avoid unnecessary overlap where the map renderer supports collision handling.
- **D-UI-SRP-006 (approved 2026-09-17):** Keep one user-facing action, `다음 지점 네이버지도 안내`, while adapting the
  handoff to the runtime platform. Android uses the official package-bound navigation intent where
  the host supports it and otherwise only an official documented native fallback; iOS uses the
  official `nmap` navigation scheme and documented App Store fallback. Feedback distinguishes
  `운영체제에 실행 요청`, `설치 페이지 열림` and actionable failure. It never claims that navigation
  started. A web fallback is shown only when NAVER officially documents one for that platform and
  context; the UI does not expose or construct an inferred web address.

#### Approved design-review criteria (2026-09-17)

- At 320px and wider panel widths, all seven exact labels use the same outline notch, typography,
  inset and focus/error treatment across text fields and dropdowns, with no collision, clipping,
  separate label row, horizontal scroll or placeholder-only accessible name.
- On first panel expansion, `API URL/키 설정` is collapsed. Repeated expand/collapse preserves
  entered values and makes no network request or write. Expanded screenshots show `VROOM 서버 URL`,
  the masked key and the correct session/plaintext-project source message without exposing a key.
- A successful server-settings save shows current-project scope, the exact written A/B snapshot
  relative path and `키 제외`; a failed save shows no success treatment and retains the previous
  valid snapshot. The path/status region wraps at narrow width and contains no secret.
- In a three-stop fixture, only stop 1 is initially checkable; completing it enables stop 2, then
  stop 3. Later rows explain why they are disabled. Unchecking an earlier completed stop leaves any
  later true rows visibly marked `순서 밖 완료`, moves the next-stop cue to the earliest gap and
  keeps every row keyboard-readable.
- Light/dark-basemap screenshots show a clearly non-gray polygon outline/fill and configured-name
  labels with a visible white halo. Base site, completed site, route and start-marker treatments are
  distinguishable without relying only on color; empty names create no blank label artifacts.
- Android and iOS device review confirms platform-appropriate handoff and documented store fallback.
  Each visible status reports only what the host observed, and no undocumented navigation web URL
  appears when the official guide provides none for that runtime context.

### QField device defects and Step 7 copy (approved 2026-09-17)

**Status: APPROVED — 2026-09-17. Device validation: NOT RUN.** This Category A/D follow-up mirrors
D-SRP-042~045 and FR-SRP-040~043 in
[survey-route-planner](../specs/survey-route-planner.md). The approved D-UI-SRP-001~006 baseline
above remains unchanged except where this approved slice explicitly extends it.

#### Approved design decisions (2026-09-17)

- **D-UI-SRP-007 (approved 2026-09-17, Category A):** `저장할 경로 이름` is a real editable mobile text field.
  Tapping its body in QField gives it focus, shows a caret and requests the OS soft keyboard. Korean
  and Latin input, selection, deletion and correction remain available without recalculation. A
  static `TextField`/label string or programmatic text assignment is not evidence that a device
  keyboard opened.
- **D-UI-SRP-008 (approved 2026-09-17, Category D):** Add `저장 경로 불러오기` to the shared outlined
  floating-label component, for eight route controls in total. The vertical center of every label
  box and its surface-colored notch aligns with the control's top outline, so the label visibly
  crosses that border. No label may sit wholly below the line or float above it. The alignment is
  identical for text fields and dropdowns in empty, value, focus, disabled and error states; the
  dropdown arrow and selected text retain their own clear space.
- **D-UI-SRP-009 (approved 2026-09-17, Category A/D):** Every generated point/multipoint, line/multiline and
  polygon/multipolygon `조사지` feature uses one geometry-appropriate map label with a white
  halo. Its text is the trimmed configured name, falling back to the trimmed configured stable ID
  when the name field is missing/invalid or the feature's name is empty. If both are absent/empty,
  no label is drawn; no unrelated field is guessed. Multipart features do not repeat the same label
  per part, and markup-looking values remain inert text. This display fallback does not satisfy or
  bypass required route-name mapping validation.
- **D-UI-SRP-010 (approved 2026-09-17, Category D):** FieldBuild Kit wizard Step 7 presents the masked field title
  `ORS API 키 (선택)` followed in reading order by these exact user-facing strings:
  - Purpose: `조사 경로를 도로망에 맞춰 계산하고 조사지 방문 순서를 정할 때 사용합니다.`
  - Empty-key behavior: `입력하지 않아도 프로젝트는 만들 수 있습니다. 다만 기본 ORS/HeiGIT 서비스로
    경로를 계산하려면 QField를 열 때마다 키를 입력해야 합니다. 키가 필요 없는 자체 서버를 사용하는
    경우에는 입력하지 않아도 됩니다.`
  - Plaintext warning: `동의하면 QField가 자동으로 사용하도록 키가 프로젝트 파일에 암호화되지 않은
    글자로 저장됩니다. 프로젝트 폴더를 열 수 있는 사람은 누구나 키를 확인하고 사용할 수 있습니다.
    동의하지 않으면 프로젝트에 키를 넣지 않으며, QField를 열 때마다 직접 입력해야 합니다.`
  - Consent checkbox: `프로젝트에 API 키를 평문으로 포함하는 데 동의합니다`
  Desktop encrypted remembering remains a separate choice and is never described as QField delivery
  or project-file encryption.

#### Approved design-review and evidence criteria (2026-09-17)

- On every claimed supported mobile OS, a target-QField review with no external keyboard connected
  confirms tap → caret/focus → soft keyboard → Korean/Latin edit → save. Source inspection and an
  automated text-injection test may be recorded only as proxies, never as the device PASS.
- At 320px and wider widths, screenshots for every state show all eight label centers on the same
  top-outline axis, with a visible notch and no sag, float, collision, clipping, separate label row
  or horizontal scrolling. A geometry assertion can supplement but does not replace the QField view.
- A spaced six-geometry fixture at an appropriate zoom shows one visible label and white halo for
  every feature, including name, missing-name-field, empty-name and missing-name-and-ID cases.
  Generated-project XML/style inspection proves configuration only; the QField map screenshot and
  observation prove rendering.
- Step 7 review covers blank key, entered key with consent declined, entered key with consent, and
  desktop remember without project consent. The exact copy remains visible/wrapped and accessible;
  only the consented state describes and produces plaintext project inclusion.

### iOS route-panel theme, header clearance and default route name (approved 2026-09-17)

**Status: APPROVED — 2026-09-17.** This Category A/B/C/D slice mirrors
D-SRP-046~048, FR-SRP-044~046, NFR-SRP-006 and AC-SRP-046~048. It is based on the supplied iPhone
QField screenshots and does not change the approved route/provider/storage contract.

#### Approved design decisions

- **D-UI-SRP-011 (approved 2026-09-17, Category A/B/D):** The route panel follows the active QField/iOS
  light/dark appearance with one internally consistent palette. It must never combine a light
  surface with dark-theme white foregrounds, or the inverse. All user-readable text meets 4.5:1;
  boundaries, indicators and focus cues meet 3:1. State meaning is not conveyed by color alone.
- **D-UI-SRP-012 (approved 2026-09-17, Category A/D):** Measure the first control from the route-summary
  header's complete painted bottom, including shadow/focus treatment. Keep at least 8 dp clear to
  the painted top of the `조사지` floating label; equivalently the control's top outline sits at
  least `label painted height / 2 + 8 dp` below it (17 dp for the current 18 dp label, 20 dp
  recommended). Header and first-control hit regions are disjoint at every supported width.
- **D-UI-SRP-013 (approved 2026-09-17, Category A/C):** `저장할 경로 이름` remains a real editable iOS input.
  Each explicit successful new calculation initializes a new candidate to exact
  `yyyy-MM-dd 조사`, using the QField device's local Gregorian calendar date at success time.
  User edits persist through collapse, theme change, refresh, save retry and calculation failure;
  the next successful new calculation resets the new candidate. Loading a saved route preserves
  its stored name.
- **D-UI-SRP-014 (approved 2026-09-17, Category D/B):** The ORS consent and desktop-retention checkbox labels
  match the established VWorld wording exactly: `위 내용에 동의합니다` and
  `이 키 기억하기 (이 컴퓨터에 암호화하여 저장됨)`. Reading order and adjacent explanatory
  copy must preserve the distinct meanings: the first authorizes plaintext inclusion in the
  generated project for QField, while the second authorizes encrypted retention on this desktop
  only. Neither selection implies the other.

#### Required state matrix

| State | Light appearance | Dark appearance | Non-color cue |
|---|---|---|---|
| Panel/header/control surface | light surface with dark foreground | dark surface with light foreground | component boundary/elevation remains visible |
| Normal value/help/label | at least 4.5:1 on its actual surface | at least 4.5:1 on its actual surface | persistent text/accessible name |
| Empty/placeholder | at least 4.5:1 and distinct from a committed value | at least 4.5:1 and distinct from a committed value | placeholder semantics; floating label remains present |
| Focus | readable text plus 3:1 focus outline | readable text plus 3:1 focus outline | visible outline and caret, not hue alone |
| Error | readable error label/message and outline | readable error label/message and outline | explicit message/icon/state description |
| Selected/checked | readable selected value/label | readable selected value/label | checkmark/selection indicator and accessible checked state |
| Disabled/read-only | label/value and disabled reason remain readable | label/value and disabled reason remain readable | disabled property plus reason; not opacity alone |

Reference tokens are light `{surface #F8FAFC, text #111827, muted #334155, outline #64748B}` and
dark `{surface #111827, text #F9FAFB, muted #CBD5E1, outline #94A3B8}`, with focus `#2563EB` and
a theme-specific error red that meets the same thresholds. Implementations may use higher-contrast
equivalents; the matrix and semantics are normative, not the mechanism.

#### Approved design-review criteria

- Real iOS QField screenshots cover every matrix row in light and dark appearance, with measured
  ratios. Static QML literals or desktop/headless rendering are proxy evidence only.
- At 320 px and wider, including supported text scaling, the first label/notch/outline remains
  fully visible below the header with the specified gap. Tapping it focuses the control and never
  collapses the header.
- With no external keyboard, the route-name field supports tap, caret, soft keyboard, Korean and
  Latin editing, selection and deletion. A local/UTC date-boundary fixture proves the local date,
  and locale changes do not alter `yyyy-MM-dd 조사`.
- Step 7 shows both exact checkbox labels, masked key input and adjacent plaintext/encrypted-storage
  explanations. Blank key, declined consent, project consent only, desktop remember only and both
  selections preserve their specified independent behavior without secret disclosure.
