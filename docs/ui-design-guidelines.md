# UI / Visual-Design Guidelines

> Owned and updated by: spec-writer
> Scope: durable, observable UI/visual-design conventions for the QField Project Builder desktop
> application (wizard styling, layout, and window sizing). This document is a **guideline**, not
> a traceable specification: nothing here is numbered as a formal FR/NFR/AC, and nothing here
> should be read as introducing or changing a functional or data requirement. Functional/data
> requirements remain exclusively in `specs/qfield-project-builder.md`.

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
  every widget (across all six wizard pages) renders consistently regardless of the host OS's
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

- **Minimum size**: 900 x 700 px (`setMinimumSize`).
- **Maximum size**: 1200 x 820 px (`setMaximumSize`).
- **Initial size**: 1000 x 760 px (`resize`), shown on first display.

These three bounds are shared module-level constants (`_WIZARD_MIN_SIZE`, `_WIZARD_MAX_SIZE`,
`_WIZARD_INITIAL_SIZE`) rather than per-page or per-platform values.

## Draft: wizard content/button-bar layout defect (2026-09-03)

**Status: DRAFT — post-D-95 UI defect revision; not an implemented convention.** The user
reported that the VWorld API area, Pl@ntNet API area, and canonical Excel candidate/preview area
can become clipped, overlapped, or hidden by the bottom wizard buttons. The detailed, traceable
proposal is [fieldbuild-kit-wizard-ui-layout-defect.md](../specs/fieldbuild-kit-wizard-ui-layout-defect.md).

The proposed change is wizard-wide: all seven pages should use a page-level scrollable content
viewport above the native QWizard button bar. Step 4 and Step 5 receive focused API/Excel controls,
keyboard, resize, DPI, and provenance acceptance coverage. Until the draft is approved and
implemented, the numeric values in the preceding sections remain a description of current code,
not a claim that this defect is resolved.

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
