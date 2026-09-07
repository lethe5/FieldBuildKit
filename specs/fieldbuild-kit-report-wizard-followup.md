# Feature: FieldBuild Kit — report and wizard follow-up corrections

> Status: DRAFT — awaiting user review and approval
> Owner: spec-writer
> Last updated: 2026-08-31
> Scope: report resilience/identity/localization, photo-identification trigger correction, and wizard map-layout refinement; no application code or tests are changed by this artifact

## 1. Summary

This follow-up records five explicitly requested changes against the existing FieldBuild Kit
report, identification, and wizard contracts. It preserves the existing local-first data model,
UUID/FK joins, CSV behavior, identification candidate/write-back/location rules, and secret
handling while making the requested report fallback, visible identity columns, Korean wording,
immediate identification trigger, and map-layout behavior independently testable.

The attached `/Users/tory/Downloads/type1-1_report.html` is diagnostic evidence only. It is not a
requirements source, does not define a new schema, and does not authorize copying its current
markup or wording into the product.

## 2. Item classification

| Item | Classification | Reason and routing |
|---|---|---|
| 1. Report without a VWorld key / with failed VWorld tiles | **A — conformance defect** | Existing report requirements already require a non-fatal remote-background failure and usable local report functions; this follow-up makes the no-key and failed-tile paths explicit against that contract. |
| 2. `국명`, `학명`, `KTSN` in the user-facing table | **A — conformance defect** | The existing report contract names these identity fields as visible/filterable joined data; the diagnostic report carries the values in records but does not expose all three as user-facing table columns. No new identity data model is introduced. |
| 3. Korean translation of user-facing English | **D — UX/visual-design refinement** | This changes wording and information presentation, not data meaning or behavior. Stable internal keys/codes remain governed separately below. |
| 4. Immediate `사진으로 동정하기` action without the current consent/OK popup | **C — explicit stakeholder-approved product change** | The user explicitly directed removal of the application-authored popup and immediate start of the existing request. This supersedes the prior Type 1 gate and the Type 2/3 boundary only through the new decision record below. |
| 5. Step 4/background-map canvas sizing and resize behavior | **D — UX/visual-design refinement** | This improves usable layout, visibility, and accessibility while preserving map data, drawing semantics, and wizard flow. |

The classification does not authorize changing an existing approved specification in place. The
new IDs below are additive and stable; historical IDs and decision-log text remain in their
original files.

## 3. Evidence boundary and current-shape observations

The attached Type 1 report was inspected only to identify the current failure/shape being followed
up:

- `definition.vworld_key` is blank, while the report contains four `inventory_observation` rows.
- The row attributes and joined values contain `selected_korean_name`,
  `selected_scientific_name`, and `selected_ktsn`, but the current joined-table `columns` array
  does not expose all three as user-facing columns.
- The current artifact visibly contains English strings such as `Species key`, `Occurrence
  count`, `record count`, `No records / empty`, `download`, and `feature detection`.
- The artifact records invalid geometry because coordinate transformation is unavailable. This
  is evidence that geometry capability must be disclosed; it is not permission to discard local
  geometry or to replace the existing geometry/CRS contract.

These observations inform the acceptance fixtures and review scenarios only. They do not make the
attached report's four species, UUIDs, timestamps, platform paths, or current implementation
strings normative.

## 4. Functional Requirements

### 4.1 Report fallback, local data, and secret boundary — Item 1 / Category A

- **FR-RWF-001:** A report must be generated, saved, opened, and usable when the current project
  has no usable VWorld API key. Report creation and local rendering must not call VWorld with a
  blank, missing, undefined, or placeholder key.

- **FR-RWF-002:** When no usable VWorld key exists, the report must select OpenStreetMap as the
  automatic remote-background fallback when the service is available. The UI must disclose in
  natural Korean that VWorld is unavailable because no usable key is configured and that
  OpenStreetMap is being used or attempted. The report must show the applicable
  OpenStreetMap attribution.

- **FR-RWF-003:** When a usable saved VWorld key exists, the report must select and attempt VWorld
  as the active background under the existing D-HRA-003 policy. If VWorld tile loading fails, the report must
  disclose the failure in Korean and attempt OpenStreetMap when possible. If both remote
  backgrounds fail, the report must remain usable with a clearly labeled offline-background
  state.

- **FR-RWF-004:** Remote-background failure, missing key, or fallback transition must not prevent
  any of the following from working: report opening, local feature rendering when geometry is
  usable, map controls, joined table, summaries, filtering, sorting, record detail views, and
  CSV construction/download. The report must initialize each affected surface at most once.

- **FR-RWF-005:** Local feature geometry and attributes must be retained independently of remote
  tiles. A usable local geometry must remain eligible for the local feature layer even when the
  background is offline. A missing, invalid, or untransformable geometry may remain excluded from
  the rendered map under the existing geometry contract, but its raw record/diagnostic state and
  non-geometry data must remain available in tables, summaries, and details with a limitation
  notice.

- **FR-RWF-006:** Existing secret rules remain unchanged. The VWorld key must not appear in
  visible status text, labels, details, summaries, CSV output, diagnostics, logs, or newly
  introduced metadata. The narrow D-HRA-003 Option 1 allowance for a saved key to remain in
  standalone HTML tile-request data when VWorld is used is preserved exactly as an existing
  exception; this follow-up adds no further credential exposure and does not require a key when
  the fallback path is used.

### 4.2 Identity columns and existing table contracts — Item 2 / Category A

- **FR-RWF-007:** For Type 1, Type 2, and Type 3 reports, the user-facing joined table must
  include the three consecutive columns labeled exactly `국명`, `학명`, and `KTSN`, in that
  order. Their values must be shown for every applicable joined row, including empty values.

- **FR-RWF-008:** Identity-column source mapping is fixed and uses the existing fields only:

  | Survey type | Report record | `국명` | `학명` | `KTSN` |
  |---|---|---|---|---|
  | Type 1 (`simple_inventory`) | `inventory_observation` | `selected_korean_name` | `selected_scientific_name` | `selected_ktsn` |
  | Type 2 (`temporary_plots`) | child `observation` | `selected_korean_name` | `selected_scientific_name` | `selected_ktsn` |
  | Type 3 (`permanent_plots`) | child `observation` | `selected_korean_name` | `selected_scientific_name` | `selected_ktsn` |

  The values must come from the observation represented by that row, not from a parent, sibling,
  map marker, species-count projection, or arbitrary first matching record.

- **FR-RWF-009:** The existing Type 1/2/3 joined rows, one-to-many expansion, UUID/FK joins,
  orphan markers, source-record identity, filtering, deterministic sorting, HTML escaping, and
  UTF-8 quoted CSV behavior remain unchanged. Filtering must include the three identity columns;
  sorting must work on each of them; and CSV must include the same values shown in the selected
  all-rows or filtered-rows scope.

- **FR-RWF-010:** Existing species aggregation rules remain authoritative. A KTSN-only
  observation with both names empty remains in joined data with an empty `국명` and `학명`, but
  contributes no species key/count under D-HRA-002. A record with all three identity fields empty
  follows the existing `미동정` rule. No report row may be fabricated to fill an identity column.

- **FR-RWF-011:** Type 4 (`vegetation_mapping`) remains a community-oriented report with no
  plant-observation identity source. It must not fabricate Type 1/2/3 observation rows or values.
  If a shared table layout displays the three identity columns for consistency, Type 4 cells
  must be empty or an explicitly localized not-applicable marker; otherwise the columns may be
  omitted for the absent level. This choice must not change Type 4 data or joins.

### 4.3 Korean user-facing wording and internal identifiers — Item 3 / Category D

- **FR-RWF-012:** All user-facing English prose in the generated report and the directly related
  report/identification/wizard surfaces must be replaced by natural Korean, including headings,
  buttons, status text, empty states, table controls, detail labels, limitation notices, and
  capability/status text. The following translations are the minimum required semantic mapping:

  | Current meaning | Required Korean user-facing wording |
  |---|---|
  | Species key | 종 식별값 |
  | Occurrence count | 출현 횟수 |
  | record count / visible row count | 기록 수 / 표시 중인 행 수 |
  | No records / empty | 기록 없음 |
  | download | 다운로드 |
  | feature detection | 기능 확인 상태 |
  | Joined table / joined data | 통합 표 / 통합 데이터 |
  | stable UUID | 고정 UUID |
  | joined parent context | 연결된 상위 기록 |
  | invalid/missing geometry | 유효하지 않거나 누락된 도형 |

  Equivalent natural Korean is allowed when it preserves the same user-visible meaning. English
  section-kicker text such as `OVERVIEW`, `ANALYTICS`, `LOCAL FEATURES`, `RECORD SUMMARY`, and
  `SOURCE RECORDS` must not remain as user-facing prose.

- **FR-RWF-013:** The photo-identification control shown to the user must use the natural Korean
  label `사진으로 동정하기`, while
  preserving its existing manual-identification meaning. The requirement is behavioral as well
  as linguistic: clicking the control starts the existing identification attempt immediately as
  specified in Section 4.4.

- **FR-RWF-014:** `VWorld`, `OpenStreetMap`, `FieldBuild Kit`, `KTSN`, scientific names, and
  necessary file-format/technical identifiers may remain unchanged. Stable internal field keys,
  enum values, codes, UUIDs, EPSG identifiers, and machine-readable CSV headers are not required
  to be translated.

- **FR-RWF-015:** Internal field keys/codes may remain as secondary, clearly identified metadata
  for data identification, for example in a subordinate detail or header annotation. They must
  never replace the primary Korean label, must be escaped as data, and must not be presented as
  unexplained user-facing English prose. Whether to show a secondary key is presentation-only;
  retaining it is optional and is not a reason to leave English UI copy untranslated.

- **FR-RWF-016:** This localization requirement applies to FieldBuild Kit-generated report and
  related product surfaces. It does not require translating third-party QGIS/QField UI or
  provider-owned attribution text; required attribution and preserved proper names remain
  visible under their existing license/branding rules.

### 4.4 Immediate photo identification — Item 4 / Category C

- **FR-RWF-017:** For a Type 1 `inventory_observation`, Type 2 `observation`, or Type 3
  `observation` feature with the existing photo-identification control available, clicking
  `사진으로 동정하기` must immediately start the existing manual identification request path.
  There must be no application-authored consent dialog, confirmation popup, modal, or intermediate
  `OK` action between the click and the identification attempt.

- **FR-RWF-018:** The immediate trigger applies equally to Type 1, Type 2, and Type 3. Type 4
  `community` remains excluded because it has no plant-photo identification target/control.
  Attaching a photo alone still must not start identification automatically; the explicit button
  click remains required.

- **FR-RWF-019:** This change preserves the existing identification workflow after the click:
  existing photo attachment reading/preparation and original-file preservation; Pl@ntNet request
  behavior; candidate list and explicit candidate selection; candidate score/probability and
  identification metadata persistence where available; selected Korean/scientific name/KTSN
  write-back and its existing direct-vs-derived field mechanism; UUID/layer/parent/sibling
  isolation; normal save/reopen behavior; and fail-closed behavior when the active form/model is
  not verified.

- **FR-RWF-020:** This change preserves the existing location rules. Location-dependent
  occurrence-probability/enrichment must use only the current survey-type authoritative geometry
  and existing relation chain. It must not use photo EXIF, image metadata, device GPS, site
  centroid, attachment metadata, or a provider-invented location. Missing/invalid authoritative
  geometry skips the location-dependent calculation without blocking the location-independent
  identification/candidate/write-back path when that path otherwise permits progress.

- **FR-RWF-021:** The desktop wizard's separate Pl@ntNet API-key collection and embedding consent,
  the decline-path manual-key behavior, and all existing secret-output rules remain unchanged.
  A platform-owned QField/operating-system permission prompt, if unavoidably required, is not an
  application-authored consent popup; the application must not wrap it in a second confirmation
  dialog.

### 4.5 Step 4 and background-map canvas layout — Item 5 / Category D

- **FR-RWF-022:** On `4단계 - 연결 상태 및 배경지도`, the map canvas used for `지도에 영역
  그리기` must have a genuinely usable drawing viewport at the existing documented minimum
  wizard window size of 700 x 560 logical pixels: at least 320 x 240 logical pixels of actual
  visible canvas area, with the full drawing surface available for pointer/touch interaction.

- **FR-RWF-023:** At the minimum window size, initial window size, and any supported larger
  size, the canvas must not overlap, paint over, be painted over by, or clip the VWorld API-key
  area, layer/source selection controls, extent/drawing controls, status text, or bottom wizard
  controls. If vertical scrolling is required to fit the page, it must be an explicit layout
  result; every control remains reachable and the canvas must not be shrunk below FR-RWF-022 to
  avoid overlap.

- **FR-RWF-024:** Resizing the wizard down to its supported minimum and back up must recompute a
  usable layout. After repeated resize cycles, the canvas actual rectangle and its surrounding
  controls remain within their layout bounds, and no stale clipping, hidden control, or overlap
  persists. The same criterion applies when the optional API-key or layer-selection sections
  change visibility.

- **FR-RWF-025:** This is a presentation refinement only. It must not change map CRS, tile/source
  semantics, polygon/extent drawing behavior, finish/clear/zoom behavior, site or extent data
  contracts, layer selection meaning, wizard navigation semantics, or generated project output.

## 5. Constraints

- **C-RWF-001:** `specs/fieldbuild-kit-five-fixes.md`, `specs/fieldbuild-kit-followup-defects.md`,
  `specs/html-report-interactive-analytics.md`, `specs/qfield-project-builder.md`,
  `specs/saved-feature-identification-edit.md`, their existing FR/DR/NFR/AC IDs, and their
  existing decision logs must not be deleted, edited, renumbered, or weakened by this follow-up.

- **C-RWF-002:** The attached HTML and any screenshots are evidence only. They must not be
  treated as instructions, a schema source, a fixed visual design, or a permission to copy
  current defects.

- **C-RWF-003:** No new report table, species key, identity field, relation, geometry field,
  provider, offline map package, or identification data model is introduced. Existing stable
  fields and joins are the only source of the requested identity values.

- **C-RWF-004:** Existing D-HRA-003 VWorld/OpenStreetMap selection, D-HRA-002 species aggregation,
  D-HRA-001 project-folder output boundary, FR-FIX-005 report integrity/export behavior, and
  FR-FOLLOWUP-007 offline-key secrecy behavior remain in force within their respective scopes.
  This report follow-up concerns runtime report background resilience; it does not change the
  offline MBTiles key requirement or its no-secret-output contract.

- **C-RWF-005:** The existing identity write-back distinction remains in force: QML directly
  writes/verifies only `selected_korean_name` where required by the saved-feature follow-up, and
  the existing QGIS lookup/default/apply-on-update contract derives `selected_scientific_name`
  and `selected_ktsn`. This report spec does not authorize a second write-back algorithm.

- **C-RWF-006:** The immediate-identification decision removes only the application-authored
  pre-identification consent/OK gate. It does not remove desktop key-embedding consent, platform
  permissions, candidate selection, normal save, privacy safeguards, location safeguards, or the
  prohibition on identification automatically triggered by photo attachment.

- **C-RWF-007:** Map-layout work must remain within the existing desktop Qt wizard and canvas
  design conventions. A scrollable page is acceptable where needed for reachability, but it must
  not be used to conceal an overlap or to turn the canvas into an unusable sliver.

- **C-RWF-008:** This spec-writing task modifies specification/documentation artifacts only. No
  QML, Python, generated project, test, fixture, traceability, or implementation file is changed
  here. Test design and implementation require later approval gates.

## 6. Assumptions

- **A-RWF-001:** Per the user's instruction, the cited existing specifications are the baseline
  contracts for this follow-up even where their repository status headers still say Draft. Their
  status text and content are not altered in this task.

- **A-RWF-002:** For report identity display, `selected_korean_name`,
  `selected_scientific_name`, and `selected_ktsn` are the authoritative existing fields and map
  respectively to `국명`, `학명`, and `KTSN`.

- **A-RWF-003:** The existing documented wizard minimum size is 700 x 560 logical pixels and
  the existing canvas functional floor is 320 x 240 logical pixels. These values are used as
  measurable review baselines; changing the supported window-size policy would be a separate
  decision.

- **A-RWF-004:** “사용자가 보는 영어 문구” means FieldBuild Kit-authored report and related
  product copy. Scientific Latin names, brands, license-required attribution, stable internal
  keys, and machine-readable codes are not English prose requiring translation.

- **A-RWF-005:** “즉시 기존 사진 동정 요청을 시작” means the click enters the existing request
  validation/request state immediately. It does not require a network request to succeed, and it
  does not bypass existing missing-photo, missing-key, offline, provider-error, or form-target
  validation.

- **A-RWF-006:** Type 4's absence of a plant-observation identity source and identification
  control remains authoritative. No Type 4 behavior is inferred from the Type 1/2/3 request.

## 7. Edge Cases

- **E-RWF-001:** No VWorld key is present, blank, whitespace-only, malformed, or unavailable at
  report generation. No blank-key VWorld request is made; OpenStreetMap is attempted; if it also
  fails, the local-only report remains usable and states the offline condition in Korean.

- **E-RWF-002:** A usable VWorld key exists but VWorld returns tile errors, times out, or is
  unreachable. The report keeps local features/data, attempts OpenStreetMap once according to the
  existing fallback policy, and exposes the final active/fallback/offline state without showing
  the key.

- **E-RWF-003:** Both remote backgrounds fail after the map has initialized. No duplicate map or
  duplicate fallback layer is created; local geometry, table rows, details, summaries, filters,
  sorting, and CSV remain usable.

- **E-RWF-004:** Geometry is valid and local while the remote background is unavailable. The
  feature remains visible in the local map layer. Geometry is missing/invalid/untransformable:
  the record remains in data/details and receives the existing limitation treatment.

- **E-RWF-005:** An identity value is null, blank, a duplicate display name, scientific-only,
  KTSN-only, or contains Korean/HTML-looking text. The correct row remains present; blank values
  remain blank; the D-HRA-002 aggregation rule applies; HTML is inert and CSV quoting remains
  correct.

- **E-RWF-006:** A Type 2/3 one-to-many join contains multiple observations with different
  identity values. Each child row shows its own `국명`/`학명`/`KTSN`; no parent value or first-child
  value is broadcast to the other rows.

- **E-RWF-007:** A Type 4 report has no plant-observation rows. It contains no fabricated
  identity values and no `사진으로 동정하기` control for `community`.

- **E-RWF-008:** The report has zero rows. It opens with Korean empty states, zero/appropriate
  summaries, visible identity-column headers where the applicable Type 1/2/3 table exists, and
  a valid header-only CSV under the existing contract.

- **E-RWF-009:** The user clicks `사진으로 동정하기` while the Type 1/2/3 form is open and the
  current platform would otherwise show an application popup behind the form. No application
  popup is inserted; existing request-level validation/error UI remains usable in the active
  form context.

- **E-RWF-010:** QField or the operating system displays its own unavoidable permission prompt.
  It is not wrapped in a second app-authored consent/OK prompt, and all existing privacy and
  credential-consent boundaries remain intact.

- **E-RWF-011:** Identification is offline, there is no usable Pl@ntNet key, no supported photo,
  or no verified active form/model. The immediate click still enters the existing request
  validation/error/pending state; it does not silently identify, write another feature, or claim
  a successful candidate write-back.

- **E-RWF-012:** Authoritative Type 1/2/3 survey/plot geometry is missing or invalid. Photo
  identification and candidate/write-back proceed as allowed by the existing workflow, while
  occurrence-probability/enrichment reports its existing unavailable/no-data state and does not
  use EXIF or device location.

- **E-RWF-013:** The Step 4 page is at minimum size, an optional API-key/layer section is shown or
  hidden, or the window is resized repeatedly. The canvas remains at least 320 x 240, controls
  are not occluded/clipped, and any required page scroll remains explicit and operable.

## 8. Out of Scope

- Editing or rewriting the existing specifications, IDs, acceptance tests, traceability files,
  or historical decision logs.
- Adding a new VWorld/OpenStreetMap/offline provider, changing VWorld layer semantics, changing
  MBTiles behavior, or changing report save-location behavior.
- Adding identity fields to the GeoPackage, changing schema/relation/UUID/FK definitions, or
  changing species aggregation rules.
- Removing the existing narrow D-HRA-003 standalone-HTML tile-request exception, or adding any
  new secret-storage/output exception.
- Automatic identification after photo attachment, identification for Type 4, a new candidate
  selection UI, a new write-back algorithm, or a new location source.
- Translating third-party QGIS/QField screens or required license/attribution proper names.
- Changing map data, CRS, tile/drawing semantics, polygon meaning, generated project output, or
  wizard navigation to solve the canvas layout issue.
- Modifying application code, tests, fixtures, generated reports, or test traceability as part
  of this spec-writing task.

## 9. Acceptance Criteria

- **AC-RWF-001 (no-key report resilience):** Given a Type 1, Type 2, or Type 3 project with no
  usable VWorld key, when the report is generated and opened, then generation succeeds without a
  blank-key VWorld request; the report loads with a Korean no-key/fallback status, attempts
  OpenStreetMap, and keeps the map, local features with usable geometry, joined table, summaries,
  filter, sort, details, and CSV usable. If OpenStreetMap is unavailable too, the same report
  remains usable with an explicit Korean offline-background status.

- **AC-RWF-002 (key-present and VWorld failure):** Given a usable saved VWorld key, when VWorld
  tiles succeed, then VWorld is the active background with visible attribution and no visible key
  value. Given VWorld tile failure, then the report discloses the failure, attempts OpenStreetMap
  when possible, and otherwise remains usable in the explicit offline state without duplicate map
  initialization or exposed credentials.

- **AC-RWF-003 (local geometry/data preservation):** Given records with usable and unusable local
  geometry and a failed remote background, when the report opens, then every usable local feature
  remains in the local map layer, every record remains in the joined/source data and details, and
  invalid/missing geometry is disclosed under the existing limitation rule rather than silently
  dropped.

- **AC-RWF-004 (identity columns and Type 1–3 mapping):** Given representative Type 1, Type 2,
  and Type 3 joined data, when the user-facing table is rendered, then it contains the exact
  columns `국명`, `학명`, and `KTSN`, and each row displays values sourced from that row's
  `selected_korean_name`, `selected_scientific_name`, and `selected_ktsn`. Type 2/3 one-to-many
  children retain their individual values, and no parent/sibling/first-row value is substituted.

- **AC-RWF-005 (identity interaction preservation):** Given identity values including nulls,
  duplicates, scientific-only, KTSN-only, Korean HTML-looking text, and all-empty values, when
  the user filters/sorts the joined table and exports all or filtered rows, then the three
  identity columns retain correct values, KTSN-only/all-empty aggregation follows D-HRA-002,
  HTML is escaped as inert text, and UTF-8 CSV headers/values/quoting match the visible selected
  rows without mutating source data.

- **AC-RWF-006 (Type 4 boundary):** Given a Type 4 project, when its report is rendered, then no
  fabricated plant-observation identity row or identification control appears; if the shared
  table includes the identity columns, all Type 4 cells are empty or explicitly localized as not
  applicable.

- **AC-RWF-007 (Korean user-facing copy):** Given a generated report and the directly related
  report/identification/wizard surfaces, when all visible headings, controls, statuses, empty
  states, details, and limitations are inspected, then no FieldBuild Kit-authored English prose
  remains for the meanings covered by FR-RWF-012. The required mappings include `종 식별값`,
  `출현 횟수`, `기록 수`, `기록 없음`, `다운로드`, and `기능 확인 상태`; brands, scientific
  names, required attribution, and permitted internal keys remain correct.

- **AC-RWF-008 (internal-key distinction):** Given a report that retains internal keys or codes
  as secondary annotations, when it is opened and values are rendered, then the primary labels
  are Korean, secondary keys are clearly subordinate/identified and HTML-escaped, and machine
  readable CSV keys remain stable. A report that omits optional secondary keys still satisfies
  this criterion if all primary Korean labels and data contracts are present.

- **AC-RWF-009 (immediate identification across Type 1–3):** Given an open Type 1, Type 2, or
  Type 3 photo-observation form with the existing photo-identification control, when the user
  clicks `사진으로 동정하기`, then the existing identification attempt/request state begins
  without an application-authored consent/confirmation popup, modal, or intermediate `OK`. This
  is true even when the form is a Type 2/3 related child form and no popup can be reached behind
  it.

- **AC-RWF-010 (identification boundary and preserved workflow):** Given equivalent Type 1/2/3
  forms and the Type 4 community form, when the relevant controls are exercised, then Type 1/2/3
  click behavior is immediate, Type 4 has no identification target, photo attachment alone does
  not identify, desktop Pl@ntNet-key embedding consent remains separate, candidate selection and
  existing write-back/save/reopen rules remain in force, unverified targets fail closed, and no
  parent/sibling/list-model record is changed.

- **AC-RWF-011 (privacy and location boundary):** Given an identification request with EXIF GPS,
  missing/invalid authoritative survey/plot geometry, or a valid authoritative geometry, when the
  existing workflow runs, then no EXIF/device/provider-invented location is used or persisted;
  probability/enrichment uses only the existing authoritative geometry when valid, skips with the
  existing unavailable state when invalid, and the location-independent candidate/write-back path
  remains governed by its existing rules.

- **AC-RWF-012 (minimum Step 4 layout):** Given the wizard at 700 x 560 logical pixels on
  `4단계 - 연결 상태 및 배경지도`, when the background-map/`지도에 영역 그리기` view is shown,
  then the actual visible canvas is at least 320 x 240 logical pixels; the API-key area,
  layer/source selection, drawing/extent controls, status text, and wizard controls are neither
  overlapped nor clipped, and every control remains reachable.

- **AC-RWF-013 (resize stability and semantics):** Given the Step 4 page at minimum, initial, and
  larger supported sizes, when the user repeatedly resizes and toggles optional key/layer areas,
  then the canvas remains usable and within its layout bounds, no stale overlap/clipping occurs,
  and the existing map CRS, tile/source, drawing, finish/clear/zoom, selection, navigation, and
  generated data semantics are unchanged.

- **AC-RWF-014 (standalone/local initialization):** Given a copied report opened with no network,
  when the user reloads it and uses map/table/detail/summary/filter/sort/CSV controls, then local
  report code initializes each surface once, no remote script/style/font/image is required for
  those local functions, and the Korean offline/fallback state remains visible.

## 10. Open Questions

- **None blocking approval.** The user explicitly supplied the product decision for immediate
  identification and the requested Type 1/2/3 versus Type 4 scope. Existing D-HRA-003's narrow
  standalone-HTML VWorld tile-request credential exception is treated as preserved secret policy,
  not re-decided here. If the stakeholder instead intends to revoke that already-approved
  exception, that would be a separate explicit credential-policy change and is not assumed by
  this follow-up.

## 11. Decision Log

- **D-RWF-001** (2026-08-31, Category A — report fallback conformance registration): The no-key,
  failed-VWorld, local-only, and local-data-preservation cases in FR-RWF-001–006 and
  AC-RWF-001–003 are conformance work against the existing FR-HRA-003/004/005/006/008/009/010/
  015/016/017, E-HRA-004/007/008, AC-HRA-002/003/004/006/007/011/012/014/015/016, FR-FIX-005,
  C-FIX-004, and FR-FOLLOWUP-007 boundaries. This entry changes no existing requirement or
  secret policy and adds no provider.

- **D-RWF-002** (2026-08-31, Category A — identity-column conformance registration): The
  `국명`/`학명`/`KTSN` table requirements in FR-RWF-007–011 and AC-RWF-004–006 make the existing
  report's already-required identity data observable in the user-facing table. They preserve
  current Type 1/2/3 fields, D-HRA-002 aggregation, joins, filtering, sorting, escaping, and
  CSV contracts; they do not add a GeoPackage field or alter a data model.

- **D-RWF-003** (2026-08-31, Category D — Korean wording and canvas-layout refinement
  registration): The Korean-copy requirements in FR-RWF-012–016 and the Step 4 layout requirements
  in FR-RWF-022–025 are presentation refinements with measurable review criteria. They do not
  translate third-party UI, change domain behavior, or change map/drawing semantics. Existing
  internal identifiers remain available as optional secondary identifiers and stable CSV keys.

- **D-RWF-004** (2026-08-31, Category C — explicit stakeholder change; **supersedes only the
  application-authored pre-identification consent/OK gate for the Type 1/2/3 Identify control**):
  The stakeholder explicitly directed: **“`사진으로 동정하기` 버튼을 누르면 현재 뜨는
  consent/OK 팝업을 보여주지 않고 즉시 기존 사진 동정 요청을 시작해야 한다.”** The prior
  Type 1 consent-gate requirement in the preceding FR-QPB-101/Decision Log D-13/D-14/D-31
  identification history is retained as historical text but is superseded for this narrow
  interaction. Existing D-90's Type 2/3 immediate-identify decision is also retained as history;
  this entry extends the same no-application-popup rule to Type 1 and supersedes D-90's explicit
  Type 1 exclusion/scope boundary only for that trigger interaction. Type 4 remains excluded.
  This entry does not remove automatic-identification prohibition after attachment, desktop
  Pl@ntNet-key embedding consent, manual-key decline behavior, platform-owned permission prompts,
  candidate selection, write-back/save/reopen, privacy, or authoritative-location rules. No
  existing decision-log entry is edited or deleted by this artifact.

- **D-RWF-005** (2026-08-31, Category D — measurable layout refinement): The existing
  `4단계 - 연결 상태 및 배경지도` minimum-window/canvas evidence is made a stable review
  contract: at 700 x 560 the drawing canvas must remain at least 320 x 240 and must not overlap
  key/layer/status/wizard controls; resize must preserve a usable area. This is a UI-only
  refinement and does not alter map or drawing semantics.

## 12. References

- `CLAUDE.md` and `.claude/agents/spec-writer.md` — clean-room role, approval gate, and
  spec-only boundary.
- `specs/fieldbuild-kit-five-fixes.md` — existing corrective report, identification, location,
  and wizard contracts, especially FR-FIX-005/010 and C-FIX-004/012/013.
- `specs/fieldbuild-kit-followup-defects.md` — existing fallback/key secrecy, saved-child
  write-back, D-90/D-91 boundary, and conformance follow-up rules.
- `specs/html-report-interactive-analytics.md` — D-HRA-001/002/003, joined data, geometry,
  fallback, CSV, escaping, and standalone report contracts.
- `specs/qfield-project-builder.md` — existing Type 1/2/3/4 schemas, identification workflow,
  privacy/location rules, D-90 Type 2/3 decision, and related acceptance IDs.
- `specs/saved-feature-identification-edit.md` — active child-form targeting, UUID/layer checks,
  derived-field write-back, normal save/reopen, and fail-closed rules.
- `docs/product.md` — Korean product UI boundary, local-first storage, and OSM drawing-canvas
  visual-aid boundary.
- `docs/architecture.md` — local desktop/process/storage architecture.
- `docs/ui-design-guidelines.md` — current 700 x 560 wizard minimum and UI/layout conventions.
- `docs/change-control.md` — A/C/D classification and non-destructive supersession routing.
- `/Users/tory/Downloads/type1-1_report.html` — diagnostic evidence only; current report data/UI
  shape is not normative.
