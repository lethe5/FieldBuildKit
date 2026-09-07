# Feature: FieldBuild Kit wizard layout defect remediation

> Status: APPROVED — UI defect revision after approved Decision Log D-95 (D-96)
> Owner: spec-writer
> Revision: D-96
> Approved: 2026-09-04
> Last updated: 2026-09-04
> Change boundary: specification/documentation only in this revision; no application code, test,
> or Git file is changed

## 1. Summary

This specification addresses the reported macOS desktop wizard layout defect in which the VWorld
API-key area, Pl@ntNet API-key area, and D-95 canonical Excel candidate/preview/selection area
become too small, clipped, overlapped, or hidden behind the bottom wizard buttons. The remedy is a
wizard-wide content-layout contract: every page gets a scrollable content viewport whose geometry
is independent from QWizard's bottom button bar, while the affected Step 4 and Step 5 controls
receive explicit usable-size and keyboard-accessibility requirements.

This is intentionally a post-D-95 follow-up artifact. It does not change D-95's canonical
workbook, provenance, key-consent, generated-project, or reference-material semantics.

## 2. Classification and decision

### 2.1 Classification

- **Primary classification: D — UX/visual-design refinement.** The user-visible behavior and data
  contracts already exist; this revision makes their presentation, layout, resize, and keyboard
  usability observable and testable.
- **Secondary classification: B — specification clarification/omission.** The approved material
  specifies the controls and some prior layout values, but does not define a page-content versus
  bottom-button-bar boundary, scroll behavior for long pages, or a keyboard-accessible Excel
  candidate-selection contract.

### 2.2 Proposed Decision Log D-96

The following is a **draft** decision after D-95 and is not authoritative until the user approves
this specification. The defect is not limited to VWorld, Pl@ntNet, or Excel: the fix is a common
layout contract for all seven wizard pages, with focused acceptance coverage for the reported
Step 4 and Step 5 surfaces. Narrowing the implementation to only those two pages would leave the
same failure mode available on the other pages when descriptions, previews, map controls, or
review output grow.

The page order, page meaning, control actions, data flow, and generated output remain unchanged.

## 3. Evidence from the current repository

The following is implementation evidence, not a claim that the current implementation satisfies
this draft:

| Area | Current code evidence | Defect hypothesis/impact |
|---|---|---|
| Shared layout | `qfield_builder/ui/wizard.py:142-149` applies shared margins `(24, 20, 24, 20)` and spacing `14`, but no page-wide content viewport or explicit `QSizePolicy` is established. | Shared spacing alone does not prevent vertical compression or guarantee a reserved button-bar boundary. |
| Existing scrolling | `wizard.py:152-191` and `602-606` wrap the SiteInput drawing group; `1111-1116` wrap only the ConnectivityBasemap offline group. | These are nested/partial scroll areas. Step 4's VWorld API and layer groups remain outside the scroll area, and Step 5 has no page-wide scroll area. |
| Wizard bounds | `wizard.py:2569-2571` define `(700, 560)` minimum, `(1000, 760)` maximum, `(760, 620)` initial; `2641-2643` apply them. | The current minimum is too small for the combined long-text/API/preview content. A direct page layout can compress soft-minimum siblings while a hard-minimum map or preview remains large. |
| VWorld page | `wizard.py:1018-1117` directly stacks mode radios, `api_key_group`, `online_group`, and the offline group; `1033-1046` use a `QFormLayout` for the key, disclosure, consent, remember, and status controls. | A long disclosure/status message plus mode-specific controls can consume the page's content height and push or compress later controls. |
| VWorld controls | `wizard.py:953-1010` defines `api_key_edit`, masked with `EchoMode.Password`, the online consent label/checkbox, offline-use label, remember checkbox, and credential status label. | These controls are functionally present but have no explicit control minimum-height/expanding policy in this file. |
| Pl@ntNet page | `wizard.py:1525-1607` directly stacks long introduction/key-note text and the `QFormLayout`-based `plantnet_group`; `1609-1636` directly append the D-95 reference group. | The page contains several wrapped paragraphs, API controls, and a preview group in one unscrollable vertical stack, so the lower controls and native bottom buttons can be compressed or obscured. |
| Excel preview | `wizard.py:1613-1622` makes `reference_source_path_edit` read-only and gives `reference_source_preview` only `setMinimumHeight(150)` and `setMaximumHeight(280)`; `1623-1635` append upload/confirm buttons. | A multiline candidate card can be unreadable when the list is compressed, and a fixed maximum height is not a sufficient contract for long content or scaled displays. |
| Excel selection | `wizard.py:1643` connects `reference_source_preview.itemClicked` to candidate selection. | The current evidence names a mouse-click path only; the draft therefore requires equivalent focus/keyboard activation behavior, without changing provenance identity or confirmation semantics. |
| Long text | Word wrapping exists for several labels, including `wizard.py:1558-1565`, `1576-1592`, and `1615-1618`, but no page-wide scroll/height contract accompanies it. | Wrapping can increase height; without a scroll viewport that additional height competes with later controls and the button bar. |
| All pages | `wizard.py` calls `_polish_layout` on page layouts, but the page layout is otherwise direct on ProjectBasics, SurveyType, SiteInput, ConnectivityBasemap, IdentificationToggle, SymbolStyling, and ReviewAndBuild. | The same content/button-bar defect can recur on any page with long descriptions, previews, canvases, or result text; this supports the common-layout scope in D-96. |

## 4. Functional requirements

These requirements govern the desktop wizard presentation and interaction only. They do not alter
the underlying project configuration or build behavior.

### 4.1 Common wizard geometry and page structure

- **FR-UI-QPB-001:** The wizard shall use a logical-pixel minimum window size of **900 × 700** on
  macOS. It shall use **1000 × 760 logical pixels** as the recommended initial size. The exact
  maximum may remain screen-aware, but the implementation shall not use an unbounded size-hint
  growth policy; a reasonable maximum target is **1200 × 820 logical pixels** when the available
  screen permits it.
- **FR-UI-QPB-002:** The seven pages — ProjectBasicsPage, SurveyTypePage, SiteInputPage,
  ConnectivityBasemapPage, IdentificationTogglePage, SymbolStylingPage, and ReviewAndBuildPage —
  shall share one page-layout pattern. The page's content viewport shall be a `QScrollArea` (or
  functionally equivalent scrollable content container) placed above/outside the QWizard-managed
  bottom button bar. The button bar shall never be a child of the scrollable content.
- **FR-UI-QPB-003:** The outer page `QVBoxLayout` shall use the shared page margins
  `(24, 20, 24, 20)` unless an approved visual review records a different shared value. It shall
  add the content viewport with stretch factor `1`; any page-local end stretch belongs inside the
  scroll content, not between the content viewport and the wizard button bar.
- **FR-UI-QPB-004:** The page content viewport shall use an expanding horizontal and vertical
  size policy, `setWidgetResizable(True)`, vertical scrolling as needed, and no page-level
  horizontal scrolling for ordinary labels and controls. Its child content widget shall be allowed
  to grow vertically without forcing the outer page or button bar to grow beyond the window.
- **FR-UI-QPB-005:** Existing specialized minimums shall be preserved where they represent a
  usable surface: `MapCanvas` shall remain at least **320 × 240 logical pixels**. A scroll bar is
  the permitted response when the complete page cannot fit; shrinking the canvas or overlapping
  later controls is not permitted.
- **FR-UI-QPB-006:** Resizing from the minimum to the recommended/maximal supported size shall
  recompute wrapped-label heights, preview-row heights, and available viewport width without
  losing field values, selected candidates, confirmation state, or scroll-independent wizard
  state. Returning to the minimum shall remain usable and non-overlapping.

### 4.2 Layout policies, text, and control minimums

- **FR-UI-QPB-007:** Page-local `QVBoxLayout` content shall use the shared outer spacing `14`
  pixels; compact nested control rows may use `8–10` pixels. Layouts shall use stretch rather than
  hard-coded empty space to absorb extra height.
- **FR-UI-QPB-008:** All long explanatory, disclosure, status, error, and provenance labels shall
  have word wrapping enabled, a width-responsive height, and no fixed maximum height that can clip
  text. A long `QCheckBox` label shall not be the sole renderer of a multi-line disclosure; the
  full disclosure shall be a separate wrapped label and the checkbox label shall remain short.
- **FR-UI-QPB-009:** Ordinary single-line fields, combo boxes, spin boxes, checkboxes, and
  push-buttons in the affected pages shall provide at least **34 logical pixels** of clickable
  height (or the platform style's larger native minimum). Multiline descriptions/status editors
  shall provide an intentional minimum surface of at least **96 logical pixels** where the
  existing field is meant for user text. No control may rely on a height that collapses to a few
  pixels under layout pressure.
- **FR-UI-QPB-010:** The page content container and nested groups shall use expanding or minimum-
  expanding policies appropriate to their role. A content widget shall not have a hard maximum
  height that prevents scrolling, and a preview shall not be assigned a fixed height that is
  smaller than its readable minimum.

### 4.3 VWorld API and basemap controls (Step 4)

- **FR-UI-QPB-011:** When online or offline mode is selected, the complete VWorld control set shall
  remain reachable in the scrollable content: `api_key_edit`, the mode-appropriate disclosure or
  offline-use notice, `consent_checkbox` when applicable, `remember_checkbox`,
  `credential_status_label`, `layer_combo`, `_refresh_layers_button`, `layer_status_label`, and
  the selected offline source/drawing, zoom, clear, and estimate controls.
- **FR-UI-QPB-012:** The VWorld API key shall remain a masked secret input. The layout change shall
  not expose its value in labels, preview text, status text, logs, or diagnostic output.
- **FR-UI-QPB-013:** The online consent disclosure and checkbox shall remain separate, readable,
  and clickable. The offline transient-use disclosure shall remain mode-specific and shall not be
  replaced by the online embedding-risk disclosure. The existing consent gate for embedding a
  VWorld key and the offline no-delivery-key rule remain unchanged.
- **FR-UI-QPB-014:** The VWorld layer selector and refresh button shall remain in one visually and
  keyboard-reachable control row or an equivalent accessible grouping. A refreshed/failed status
  message may grow vertically and shall scroll instead of clipping or displacing the controls
  below it.

### 4.4 Pl@ntNet and canonical Excel controls (Step 5)

- **FR-UI-QPB-015:** When the page is shown, the Pl@ntNet control set shall remain readable and
  reachable: `enable_checkbox`, `plantnet_api_key_edit`, `plantnet_consent_disclosure_label`,
  `plantnet_consent_checkbox`, `plantnet_remember_checkbox`, and
  `plantnet_credential_status_label`, plus the surrounding explanatory text.
- **FR-UI-QPB-016:** The Pl@ntNet API key shall remain masked. The explicit consent checkbox shall
  remain the only authorization for embedding the key in the generated project; the remember
  checkbox shall continue to mean encrypted local retention, not project embedding consent.
- **FR-UI-QPB-017:** The D-95 reference group shall remain fully usable on the existing Step 5
  page: read-only selected filename/path, candidate status, candidate preview, automatic bundled
  candidates, `사용자 .xlsx 업로드...`, and `선택한 참조 자료 확인` shall all be visible or
  reachable through the page scroll viewport. This remains true even when the identification
  option is disabled for a Type 1–3 project that still materializes the reference tables.
- **FR-UI-QPB-018:** Each candidate preview shall show, without clipping or overlap, the filename,
  source kind, validation status, sheet name, header-row information, and bounded sample rows
  supplied by the canonical-reference inspection path. The preview list shall have a readable
  minimum height of **240 logical pixels** at the wizard minimum, a preferred height of about
  **300 logical pixels** at the recommended size, and shall remain vertically scrollable for
  additional candidates or wrapped rows. The preview shall not use a restrictive maximum height
  that makes the sample content unreadable.
- **FR-UI-QPB-019:** Selecting a bundled candidate or user-upload candidate shall remain distinct
  from confirming it. The filename/path shown to the user may be normalized for display, but the
  selected candidate's actual path and explicit `source_kind` shall remain the identity used for
  confirmation and provenance.
- **FR-UI-QPB-020:** A user shall be able to focus, select, and activate a candidate with mouse,
  Tab/Shift-Tab, arrow keys, and Space/Enter (or the native equivalent). Keyboard activation shall
  perform the same candidate-selection state transition as the existing click path and shall not
  bypass the explicit `선택한 참조 자료 확인` step.
- **FR-UI-QPB-021:** Long validation/error/provenance messages in the reference group shall wrap
  and remain readable. Invalid workbook, missing sheet/header, changed-after-selection, and
  unconfirmed-candidate states shall preserve their current fail-closed behavior without hiding
  the control needed to recover.

## 5. Constraints and preserved contracts

- **C-UI-QPB-001:** This draft changes layout, sizing, scrolling, wrapping, and interaction reach;
  it does not change wizard page order, survey types, basemap semantics, Excel validation rules,
  candidate confirmation semantics, build outputs, or generated-project schema.
- **C-UI-QPB-002:** Preserve all existing security behavior: VWorld and Pl@ntNet keys remain
  masked; explicit online VWorld and Pl@ntNet inclusion-consent checkboxes remain mandatory for
  their respective project-embedding exceptions; no key is added to logs/reports/diagnostic
  exports; and encrypted local “remember this key” retention remains opt-in and independent from
  project embedding.
- **C-UI-QPB-003:** Preserve D-95 canonical-reference behavior: the approved workbook remains the
  sole canonical source for new Type 1–3 builds; bundled candidates and user uploads retain their
  explicit `source_kind`; filename, sheet, header rows, sample rows, validation status, SHA-256,
  source filename, and pipeline/schema provenance remain available to the existing workflow; a
  candidate preview never equals confirmation; and a changed/invalid/unconfirmed source remains
  fail-closed.
- **C-UI-QPB-004:** The original workbook shall not be copied into generated projects as a result
  of this layout work. Generated projects continue to contain only the already-approved
  materialized reference tables/provenance, never the raw source workbook.
- **C-UI-QPB-005:** The native QWizard bottom button bar and its navigation semantics remain
  outside the scrollable page content and remain visible/actionable at all supported window sizes.
- **C-UI-QPB-006:** Logical-pixel values are targets for Qt layout geometry. The implementation
  shall rely on Qt's DPI-aware metrics and shall not assume that a physical pixel equals one
  logical pixel.

## 6. Assumptions

- **A-UI-QPB-001:** The supported macOS desktop environment includes ordinary laptop/desktop
  displays around 1440 × 900 logical pixels; the proposed 900 × 700 minimum and 1000 × 760
  recommended initial size are intended to fit that class of display while leaving system chrome
  room. If the supported display baseline differs, the size values require explicit revision.
- **A-UI-QPB-002:** QWizard's existing native Back/Next/Finish/Cancel bar remains the product's
  button bar; this draft does not authorize replacing it with a custom navigation footer.
- **A-UI-QPB-003:** The reference preview remains bounded to the existing sample-row contract
  from `canonical_reference.inspect_ktsn_source_candidates`; “scrollable long preview” means the
  preview control can reveal all supplied candidate rows/wrapped text, not that an unbounded raw
  workbook is rendered in full.
- **A-UI-QPB-004:** The attached screenshot is treated as symptom evidence. The repository has no
  screenshot file named by this request, so pixel-for-pixel reconstruction is not a prerequisite
  for this specification.

## 7. Edge cases

- **E-UI-QPB-001:** At the 900 × 700 minimum, Step 4 in offline/drawing mode has a 320 × 240
  canvas plus VWorld key/layer and estimate controls. The page must show a scrollbar; it must not
  shrink the canvas or paint over controls below it.
- **E-UI-QPB-002:** At the 900 × 700 minimum, Step 5 has identification text, a visible/expanded
  Pl@ntNet group, and the reference group. All controls remain reachable by scrolling, including
  the two Excel buttons and the bottom wizard buttons.
- **E-UI-QPB-003:** A very long filesystem path, Korean NFC/NFD filename, long validation message,
  or multiple candidate rows must wrap or scroll without horizontal page overflow or loss of the
  underlying path/source identity.
- **E-UI-QPB-004:** A remembered key that triggers the existing password prompt, a declined
  password prompt, a failed layer refresh, an invalid workbook, or a changed-after-selection
  workbook may add status text. The new status must expand/scroll inside content and must not
  cover the next/finish button.
- **E-UI-QPB-005:** At 125%, 150%, and 200% macOS/Qt scaled display settings, control labels may
  occupy more lines. This is an expected scroll condition, not permission to clip, overlap, or hide
  the bottom button bar.
- **E-UI-QPB-006:** Returning backward and forward between pages, toggling online/offline/none,
  enabling/disabling Pl@ntNet, selecting a bundled candidate, and uploading a user workbook must
  preserve the existing field and confirmation-state semantics while recalculating geometry.

## 8. Out of scope

- Changing D-95's canonical workbook contents, schema, validation pipeline, matching rules,
  taxonomy aggregation, or provenance fields.
- Changing API endpoints, key-storage cryptography, consent wording semantics, generated-project
  embedding exceptions, or the no-raw-workbook-copy rule.
- Adding new wizard pages, changing page order, redesigning the native button bar, or replacing
  Qt controls with a new UI framework.
- Fixing unrelated domain/build defects or changing application code/tests in this specification
  revision.

## 9. Acceptance criteria

Each criterion is independently verifiable. The criteria below are design/functional acceptance
targets for a later test-designer handoff; no acceptance-test file is modified by this draft.

### 9.1 Common page and button-bar criteria

- **AC-UI-QPB-001:** Given the wizard on each of its seven pages at 900 × 700 logical pixels,
  when the page is rendered in its longest normal content state, then no visible label, field,
  group, preview row, canvas, or button overlaps another; clipped text is not accepted; and the
  native Back/Next/Finish/Cancel buttons remain fully visible and clickable.
- **AC-UI-QPB-002:** Given any page whose complete content exceeds the available page viewport,
  when the user scrolls vertically, then the content is revealed inside the page viewport while the
  bottom button bar remains fixed and visible throughout; horizontal page overflow is absent for
  ordinary text and controls.
- **AC-UI-QPB-003:** Given the wizard at 900 × 700, 1000 × 760, and the supported maximum,
  when it is resized down and back up, then wrapped text reflows, preview rows remain readable,
  page state is retained, and the bottom buttons never disappear behind content.
- **AC-UI-QPB-004:** Given Qt/macOS scale factors corresponding to 100%, 125%, 150%, and 200%,
  when each page is rendered at its supported minimum logical size, then the same no-clipping,
  no-overlap, fixed-button-bar result holds; additional content is scrollable.
- **AC-UI-QPB-005:** Given keyboard-only navigation from the first focusable control on each page,
  when the user presses Tab/Shift-Tab, then every interactive control and the native wizard buttons
  receive focus in a logical order, each focus state is visibly distinct, and no focus target is
  unreachable because it is below an unscrollable region.
- **AC-UI-QPB-006:** Given the current page, when a user types into an input, toggles a checkbox or
  radio, opens a combo box, activates a button, or scrolls a preview, then the action does not
  cause geometry overlap or move the bottom button bar over the content.

### 9.2 VWorld/API criteria

- **AC-UI-QPB-010:** Given Step 4 in online mode at the minimum size, then the VWorld API key
  field, layer combo, refresh button, online disclosure, consent checkbox, remember checkbox, and
  any credential/layer status are each readable and actionable without overlap; long status text
  scrolls or reflows inside content.
- **AC-UI-QPB-011:** Given Step 4 in offline mode at the minimum size, then the masked VWorld key,
  remember checkbox, offline-use disclosure, layer selector/refresh controls, upload/draw source
  controls, 320 × 240 canvas minimum, zoom controls, clear action, estimate, and native wizard
  buttons are all reachable; the canvas never paints over controls below it.
- **AC-UI-QPB-012:** Given a VWorld key is entered or loaded from the existing remembered-key
  path, when the field is rendered, then its echo mode remains Password and no rendered label,
  status, preview, or tooltip displays the key value.
- **AC-UI-QPB-013:** Given online mode, when the user tabs through the consent disclosure and
  checkbox and toggles the checkbox with keyboard, then the checkbox remains the existing explicit
  gate for project-key embedding. Given offline mode, the online disclosure/checkbox is not shown
  as if offline embedding were occurring, and the transient-use message remains readable.
- **AC-UI-QPB-014:** Given a VWorld layer refresh success or failure, when the status message grows
  or changes, then it remains wrapped/readable, the layer control remains usable, and the native
  bottom buttons remain visible.

### 9.3 Pl@ntNet/API criteria

- **AC-UI-QPB-020:** Given Step 5 with identification enabled, then the intro text, Pl@ntNet key
  field, disclosure, consent checkbox, remember checkbox, credential status, and key note are
  readable and individually clickable at 900 × 700 using page scrolling as needed.
- **AC-UI-QPB-021:** Given a Pl@ntNet key is entered or loaded, when the field is rendered, then
  its echo mode remains Password and the key is absent from all visible explanatory/status text.
- **AC-UI-QPB-022:** Given keyboard-only navigation on Step 5, then the user can reach and toggle
  `enable_checkbox`, focus/type the key, toggle consent and remember, reach the reference controls,
  and reach the native wizard buttons without a focus trap or clipped focus indicator.
- **AC-UI-QPB-023:** Given the Pl@ntNet consent checkbox is toggled, when page geometry updates,
  then the checkbox remains the existing consent gate for key embedding; the remember checkbox
  remains a separate encrypted-retention choice; no layout change alters either value.

### 9.4 Reference Excel criteria

- **AC-UI-QPB-030:** Given Step 5 with one or more bundled `.xlsx` candidates, then each visible
  candidate card/list row displays filename, source kind, validation status, sheet, header rows,
  and the supplied sample rows without clipping or overlap at the minimum and recommended sizes.
- **AC-UI-QPB-031:** Given a candidate preview whose wrapped rows exceed the viewport, when the
  user scrolls the preview, then every supplied preview row can be read; scrolling is contained
  in the preview/page content and does not move or cover the native bottom button bar.
- **AC-UI-QPB-032:** Given a user selects `사용자 .xlsx 업로드...`, chooses a valid or invalid
  workbook, and returns to Step 5, then the read-only filename/path, preview/status, and both upload
  and confirm controls remain reachable; invalid input remains visibly fail-closed.
- **AC-UI-QPB-033:** Given a candidate is highlighted with mouse or keyboard, when the user activates
  it, then the same selection state is established as the existing click path; the user must still
  press `선택한 참조 자료 확인` to confirm, and the Next/Finish button state follows the existing
  `isComplete`/confirmation semantics.
- **AC-UI-QPB-034:** Given a displayed filename uses macOS Unicode normalization or a long path,
  when the candidate is selected and confirmed, then the actual source path and `bundled_candidate`
  versus `user_upload` provenance remain correct even if display text wraps or normalizes.
- **AC-UI-QPB-035:** Given a confirmed source is later changed, unreadable, missing its required
  sheet/header, or otherwise invalid, when validation runs, then the existing error/fail-closed
  behavior is shown in wrapped/scrollable status text and no layout state hides the recovery action.
- **AC-UI-QPB-036:** Given a valid D-95 source is confirmed and a project is generated in a later
  implementation round, then the layout remediation has not caused the raw workbook to be copied
  into the project; existing materialized tables and provenance remain the only generated
  reference artifacts.

## 10. Test-design handoff request (tests intentionally not changed)

After explicit approval of this DRAFT, a fresh `test-designer` should create/update acceptance
coverage without receiving implementation assumptions beyond this specification:

| Test-design ID | Requested verification | Traceability |
|---|---|---|
| TD-UI-QPB-001 | Real constructed wizard geometry at 900 × 700, 1000 × 760, and supported maximum; assert page viewport/button-bar separation and no intersecting visible widget geometries. | AC-UI-QPB-001–004, 006 |
| TD-UI-QPB-002 | Structural Qt inspection of page-wide `QScrollArea`, `setWidgetResizable`, `QVBoxLayout` stretch, margins/spacing, size policies, control minimums, and preserved 320 × 240 canvas minimum. | FR-UI-QPB-002–010; AC-UI-QPB-001–004 |
| TD-UI-QPB-003 | Manual/screenshot matrix for all seven pages, including Step 4 online/offline and Step 5 identification-enabled/disabled states, at minimum/recommended sizes. | D-96; AC-UI-QPB-001, 010–011, 020, 030 |
| TD-UI-QPB-004 | Qt keyboard/focus traversal using Tab/Shift-Tab, arrows, Space/Enter; specifically candidate highlight/activation and native wizard buttons. | FR-UI-QPB-020; AC-UI-QPB-005–006, 013, 022, 033 |
| TD-UI-QPB-005 | macOS/Qt scaled-display rendering at 100/125/150/200%, including long Korean text, long paths, status/error messages, and wrapped preview rows. | AC-UI-QPB-004, 014, 021, 031, 035 |
| TD-UI-QPB-006 | Regression checks for Password echo modes, consent gates, encrypted remember semantics, candidate `source_kind`/actual path, confirmation gating, and no raw-workbook copy/provenance behavior. | C-UI-QPB-002–004; AC-UI-QPB-012–013, 021, 023, 033–036 |

The test-designer should place the resulting traceability mapping under
`tests/acceptance/` only after this specification is explicitly approved. This draft itself does
not create or edit a test file.

## 11. Open questions

- **O-UI-QPB-001:** Confirm the proposed macOS logical sizes: 900 × 700 minimum and 1000 × 760
  recommended initial size. If the supported display baseline or product preference requires
  different values, the user should approve the replacement values before implementation.
- **O-UI-QPB-002:** Confirm that the common all-seven-page scroll-container decision in proposed
  D-96 is intended, with Step 4/Step 5 as the primary defect acceptance surfaces.

## 12. Approval gate

This document remains **DRAFT** after approved D-95. No test-designer, implementer, or reviewer
work may proceed against D-96 until the user explicitly approves this specification. No
application source, test, or Git state was changed in producing this document.
