# Feature: FieldBuild Kit QField HTML report — spatial reliability and field-facing refresh

> Status: DRAFT — awaiting user review and explicit approval
> Owner: spec-writer
> Last updated: 2026-09-04
> Extends: `specs/html-report-integrated-data-map-summary-theme.md`, `specs/html-report-integrated-followup-hardening.md`, `specs/html-report-map-valid-geometry-collection.md`, and `specs/html-report-interactive-analytics.md`

## 1. Summary

This integrated change makes the QField-exported, self-contained HTML report reliable for
spatial field records and substantially quieter for ordinary readers. It keeps the existing
map, integrated table, CSV, theme, print, reduced-motion, keyboard, and local-first contracts,
while moving technical provenance and collection capability detail behind an opt-in diagnostic
surface.

Evidence fixture: `/Users/tory/Downloads/toolbar-validation-theme-import_report 2.html` is a
Type 1 (`simple_inventory`) report generated on 2026-09-04. Its direct saved-GeoPackage SQLite
path was unavailable (`SQLite bridge unavailable`); the configured loaded-layer fallback supplied
three `inventory_observation` records; and all three were labeled `empty geometry`. This fixture
does **not** establish that the source geometries were empty. It establishes a QField fallback
serialization/diagnostic defect that this change must address.

## 2. Scope, terminology, and required classification

### 2.1 Change-control classification

All requested behavior is a **Category C — stakeholder-approved product change**. The diagnostic
controls are Category C rather than internal-only hardening because their visibility, wording,
and privacy boundary are a user-facing report contract. This specification is intentionally
narrow: it neither authorizes implementation nor reclassifies a future proven implementation
failure as a specification change.

### 2.2 Terms

- **Normal report**: the default view intended for a field worker or report recipient.
- **Diagnostics**: a closed, explicit opt-in `details`/equivalent section for technical support
  information. It is not shown in print by default.
- **Spatial anchor**: the source record whose geometry owns a map feature. Child joins provide
  attributes only and never replace the anchor coordinates.
- **Actual empty geometry**: the selected source geometry is explicitly null or empty according
  to the source/runtime geometry API. A failed read, serializer exception, unavailable method,
  unknown CRS, or failed transform is not an actual empty geometry.
- **Serialization failure**: a non-empty or emptiness-unverified source geometry cannot be
  converted into valid GeoJSON XY coordinates by the available QField-compatible serializer or
  its permitted local fallback.
- **Transform failure**: a decoded XY geometry cannot be converted from its known non-WGS84 CRS
  to WGS84. It is distinct from actual empty geometry and serialization failure.
- **Meaningful chart**: a chart whose applicable source has at least one valid plotted value or
  category after the chart's stated aggregation rule. A zero-row/non-applicable chart is not
  meaningful.

### 2.3 Unchanged spatial-anchor policy

The following anchor decisions remain authoritative and must be applied consistently by direct
collection and loaded-layer fallback:

| Survey type | Map contexts and anchor |
|---|---|
| Type 1 `simple_inventory` | Each eligible `inventory_observation` geometry is its own anchor. |
| Type 2 `temporary_plots` | Render `site` separately; joined observation context is anchored to `survey`. Observation geometry never replaces it. |
| Type 3 `permanent_plots` | Render `site` separately; joined observation context is anchored to `plot`, falling back only to its linked `survey` geometry when the plot geometry is unavailable. |
| Type 4 `vegetation_mapping` | Render eligible `community` geometry only; do not fabricate plant-observation features. |

## 3. Functional requirements

### 3.1 Spatial collection, serialization, and truthful map state

- **FR-FBKR-001:** For every schema-defined eligible spatial anchor, report generation must
  collect geometry through the existing read-only direct GeoPackage path when available. If that
  path is unavailable, it may use only the already permitted QField loaded-layer fallback; that
  fallback must attempt QField-compatible geometry serialization for every collected anchor.
  A fallback record with an emptiness-unverified geometry must not be classified as empty merely
  because direct GeoPackage access is unavailable.

- **FR-FBKR-002:** A QField-compatible serialization path must produce standard WGS84 GeoJSON
  from the anchor's runtime geometry and its layer CRS. It must use a runtime geometry export
  supported in the target QField environment, with a local geometry/WKB/WKT-compatible fallback
  when the preferred export is unavailable. For EPSG:4326 input, valid X/Y coordinates must use
  the identity path and must not require a coordinate-transform API. For another known CRS, an
  explicit local/runtime transform to WGS84 is required. GeoJSON coordinate order is longitude,
  latitude.

- **FR-FBKR-003:** Serialized report geometry must retain XY ordinates only. Z and M are removed;
  they must not be presented, used as substitute X/Y, or used to infer a coordinate. Geometry,
  CRS, UUID/FK relations, and source data remain read-only.

- **FR-FBKR-004:** Each map-eligible record must receive one deterministic geometry outcome:
  `valid`, `actual_empty`, `serialization_failure`, `transform_failure`, `malformed_xy`,
  `unsupported_geometry`, or another stable, Korean-translated reason defined by the report.
  `actual_empty` is permitted only after an explicit empty/null result from the selected source
  geometry. A serializer exception, absent geometry export capability, raw decode failure, or
  unavailable direct path must use its applicable non-empty outcome. An unknown CRS is a
  transform/capability limitation, not empty geometry.

- **FR-FBKR-005:** One record's geometry failure must exclude only that map geometry. Its readable
  attributes, established joins, integrated-table row, CSV row, source-record summaries, and
  applicable analytics remain available. Other valid anchors must render. No coordinates may be
  invented from attributes, related rows, centroids, photos, display text, or nearby geometry.

- **FR-FBKR-006:** The normal map state must be truthful and concise. It must say how many local
  records are shown, or that none can be shown, and must distinguish actual empty geometry from
  records unavailable because of serialization/transform/capability failure. It must never say
  `유효한 도형 없음` when an eligible geometry is valid, and must never imply that a
  serialization failure proves that source geometry is empty. Reason-by-reason collection and
  capability detail belongs in Diagnostics.

- **FR-FBKR-007:** Direct-collection and fallback status must remain semantically truthful. The
  normal report exposes a short Korean collection state such as collected-record count and
  whether completeness is limited/unknown. Diagnostics alone identifies the direct path that
  failed, fallback source, successful table/row scopes, known omissions, unverified scopes, and
  geometry outcome counts. Neither surface may claim a complete saved-GeoPackage inventory when
  direct collection failed and completeness is unverified.

### 3.2 Field-facing hierarchy, table language, and diagnostics

- **FR-FBKR-008:** Replace the normal-output section titled `원본 스키마와 현재 기록` with a concise
  Korean data-collection status section. It may state collected record counts, the applicable
  survey level, and a short limitation summary, but it must not list raw schema field names,
  source inventories, UUIDs, internal machine keys, or technical paths by default.

- **FR-FBKR-009:** Raw schema, source inventory/completeness, stable UUIDs, collection method,
  and project-relative internal locations may appear only in a closed opt-in Diagnostics section.
  iOS sandbox absolute paths (including `/var/mobile/Containers/...`) must never appear in the
  report—normal view, Diagnostics, printed output, CSV, map popup, status message, or error.
  Any required location wording uses a Korean logical/project-relative description instead.

- **FR-FBKR-010:** The normal integrated table, map popups, summaries, and CSV headers must use
  concise Korean names. Internal identifiers (`id`, UUID, UUID/FK variants, source table keys,
  runtime paths, collection modes, and technical provenance keys) are hidden from the normal
  integrated table and popups. Existing stable identities remain available only through
  Diagnostics and internal payloads required for correct joins.

- **FR-FBKR-011:** Repeated semantically identical user-facing fields must render once. This
  includes duplicate `비고` values that arose through joins or source flattening. If values are
  genuinely conflicting, preserve every source value and expose clear Korean provenance labels
  such as `관찰 비고` and `조사 비고`; do not expose raw keys such as
  `inventory_observation__notes`. Equal values may not be duplicated. All normal labels for
  bases, exclusions, limitations, and empty/non-applicable states must be Korean rather than
  untranslated English/machine terminology.

- **FR-FBKR-012:** Diagnostics must preserve the existing privacy boundary: no API keys,
  credentials, attachment/photo contents, or sandbox absolute paths may be rendered or exported.
  Its technical detail must be inert/escaped and keyboard-operable.

### 3.3 Purposeful responsive analytics cards

- **FR-FBKR-013:** Analytics are rendered as independent chart cards, not a fixed sequence of
  disconnected headings and chart placeholders. Each visible card contains a Korean title, a
  concise Korean aggregation basis, an accessible chart or summary graphic, and an equivalent
  textual value list/table usable without interpreting color or graphics. Cards form a responsive
  grid that adapts to narrow iPhone and desktop widths without horizontal page overflow.

- **FR-FBKR-014:** The applicable chart-card set is fixed as follows:

  - Type 1: species-observation occurrence only.
  - Types 2 and 3: species-observation occurrence, plus mean cover only when one or more valid
    numeric cover values exist.
  - Type 4: community area only when one or more valid numeric area values exist, plus relevant
    composition only when one or more non-empty community composition values (for example,
    `dominant_species`) exist.

  Type 4 must not label community records as plant observations. Existing species-key rules,
  including the older KTSN-only exclusion from species-observation grouping, remain unchanged.

- **FR-FBKR-015:** A non-applicable, empty, or invalid-only chart card is hidden rather than
  shown with `기록 없음`, `해당 없음`, an empty graphic, or a blank reserved slot. If no meaningful
  analytics cards exist, the report hides the analytics section and its table-of-contents entry.
  Invalid numeric values are excluded from the applicable calculation and summarized in Korean
  limitation text when that exclusion materially affects a visible card.

- **FR-FBKR-016:** Chart accessibility must preserve the existing report's keyboard and
  reduced-motion behavior: no interaction may require a pointer, focus indicators remain visible,
  charts do not communicate solely by color, and keyboard-accessible chart elements (when
  interactive) announce their Korean label and value. Print output remains readable through the
  card title, basis, and textual equivalent.

### 3.4 Noise reduction and retained report behavior

- **FR-FBKR-017:** A VWorld control is rendered only when a usable runtime VWorld key is actually
  available without embedding the key in the report. When no key is available, no disabled,
  no-op, or explanatory VWorld switch is shown. Local map operation and optional OpenStreetMap or
  offline background behavior remain non-blocking; detailed background/capability fallback
  information belongs in Diagnostics.

- **FR-FBKR-018:** The refreshed report remains one self-contained local HTML file. It retains
  the existing integrated table's row preservation, filter, sort, keyboard sorting, visible-row
  count, and safe UTF-8 CSV behavior; the map's local feature operation; light/dark theme;
  print stylesheet; reduced-motion handling; escaped rendering; and no-network operation. Any
  intentional supersession in this specification is limited to the display hierarchy and wording
  stated here, not to source data, join authority, CSV data preservation, or accessibility.

## 4. Constraints

- **C-FBKR-001:** Existing Type 1–4 schemas, UUID/FK join rules, spatial-anchor policy in §2.3,
  source-record aggregation rules, geometry non-fabrication rule, and local-first/privacy
  constraints continue unchanged unless this specification expressly supersedes their report
  presentation.
- **C-FBKR-002:** Report collection, geometry serialization, and rendering are read-only. The
  report must not repair, migrate, reproject in place, or modify GeoPackage/QField data.
- **C-FBKR-003:** No remote script, stylesheet, service, geocoder, or network connection may be
  required to serialize local geometry, render local records, view the table, or export CSV.
- **C-FBKR-004:** This DRAFT creates only this specification. It authorizes no production-code,
  test, fixture, generated-artifact, Git, or external-device changes before the required approval
  gates.

## 5. Assumptions

- **A-FBKR-001:** The target physical fixture is QField 4.2.4 on iPhone/iOS, as represented by
  the evidence artifact. The manual gate is required because desktop/QGIS mocks alone cannot
  establish QField runtime geometry serialization behavior.
- **A-FBKR-002:** Existing source definitions provide the chart inputs named here: observation
  species identity for Types 1–3, `cover` where that survey type records it, and Type 4 community
  area/composition fields where present. A missing schema field makes its card non-applicable.
- **A-FBKR-003:** The previous direct-GeoPackage and loaded-layer fallback paths remain the only
  permitted collection paths. This change improves their serialization and disclosure, not their
  authority or scope.

## 6. Edge cases

- **E-FBKR-001:** A Type 1 loaded-layer fallback returns three records whose runtime geometry
  cannot be serialized. All three remain records, are classified as serialization failure rather
  than actual empty geometry, appear in table/CSV/appropriate summaries, and produce a truthful
  zero-rendered-map state.
- **E-FBKR-002:** A Type 1 loaded-layer fallback returns three valid EPSG:4326 point geometries
  while direct SQLite is unavailable. All three serialize as XY-only WGS84 GeoJSON and render on
  the map; the normal status says collection completeness is limited/unverified, not that the
  records are empty or fully inventoried.
- **E-FBKR-003:** One valid anchor follows a malformed, transform-failed, or actual-empty anchor.
  The valid anchor still renders, while each excluded record retains its distinct reason.
- **E-FBKR-004:** Type 3 has no plot geometry but has valid linked survey geometry. The documented
  survey fallback renders; observation geometry is not promoted. A Type 2 observation geometry
  likewise never replaces an unavailable survey anchor.
- **E-FBKR-005:** Equal `notes` values from several joined sources appear once as `비고`. Differing
  values appear as Korean-provenanced fields, with no raw English/schema key exposed in normal
  output.
- **E-FBKR-006:** A Type 2/3 project has species observations but no valid cover; it shows only
  the species card. A Type 4 project has valid community area but no composition; it shows only
  community area. A project with no meaningful analytic input has no analytics section or TOC
  item.
- **E-FBKR-007:** The report has no VWorld key, is opened offline, and contains valid local map
  geometry. It has no VWorld control but still renders local geometry, preserves normal map/table
  behavior, and reports no network dependency as a data failure.
- **E-FBKR-008:** An iOS-exported path is available to the generator. It is replaced by an
  appropriate Korean logical/project-relative location description or omitted; no sandbox UUID
  path leaks to any report surface.

## 7. Out of scope

- Changing QField or QGIS itself, adding new collection sources, or guaranteeing a remote
  basemap.
- Altering source schemas, field values, geometry, UUID/FK relations, survey types, or the
  established species-key algorithm.
- Adding analytics beyond the type-specific card set in FR-FBKR-014.
- Implementing this specification, creating/altering tests or fixtures, exporting a physical
  fixture, or committing/pushing changes during this specification stage.

## 8. Acceptance criteria

- **AC-FBKR-001 — physical QField/iPhone geometry gate (manual):** Given a physical iPhone with
  QField 4.2.4 and a Type 1 fixture containing three known non-empty EPSG:4326
  `inventory_observation` points, when the report is generated on-device with direct GeoPackage
  SQLite unavailable and the permitted loaded-layer fallback active, then the exported local HTML
  renders all three point anchors at their recorded XY locations; no record is labeled actual
  empty solely because of the failed direct path; the normal report identifies limited/unverified
  collection truthfully; and Diagnostics identifies the fallback and geometry outcome counts. The
  gate records device/QField version, fixture identifier, generated-report timestamp, visible
  point count, and screenshots of the map and closed/open Diagnostics. A desktop-only automated
  result cannot PASS this criterion.

- **AC-FBKR-002 — outcome classification:** Given fixtures covering explicit empty/null geometry,
  a valid EPSG:4326 geometry, a serializer failure, an unknown/non-transformable CRS, and malformed
  XY, when reports are generated through direct and permitted fallback paths, then each affected
  record receives the correct distinct geometry outcome; valid EPSG:4326 XY does not require a
  transform API; and no non-empty/unknown geometry failure is labeled actual empty.

- **AC-FBKR-003 — anchor and row preservation:** Given fixtures for Types 1–4 including malformed
  or unavailable anchor geometry, when map/table/CSV are inspected, then every type uses the
  §2.3 anchor, valid anchors render despite other failures, failed geometry affects only map
  rendering, and no child or substitute geometry is promoted or invented.

- **AC-FBKR-004 — normal status versus diagnostics:** Given direct collection failure with a
  successful partial loaded-layer fallback, when the report opens, then normal output contains a
  concise Korean collection state with no raw schema, UUID, internal path, failed-path, or
  capability jargon; closed Diagnostics contains the direct/fallback source, successful reads,
  known omissions, unverified scope, and per-outcome map limitations; and neither claims a
  complete direct inventory.

- **AC-FBKR-005 — privacy and Korean field presentation:** Given joined rows with equal and
  conflicting notes, internal IDs, raw English source names, source inventory metadata, and an
  iOS sandbox absolute path, when normal report, Diagnostics, map popup, print view, and CSV are
  inspected, then equal semantic values occur once; conflicts retain all values under clear
  Korean provenance labels; normal table/popups hide internal identifiers; normal basis and
  limitation wording is Korean; UUIDs/raw source inventory are opt-in Diagnostics only; and the
  absolute sandbox path is absent everywhere.

- **AC-FBKR-006 — analytics applicability and accessibility:** Given one fixture for each type
  and combinations of missing/valid species, cover, community-area, and community-composition
  data, when the report opens at iPhone and desktop widths, then visible cards exactly follow
  FR-FBKR-014; empty/non-applicable cards and a wholly empty analytics section/TOC item are
  hidden; each visible card has a Korean title, Korean basis, accessible non-color-only chart,
  and textual equivalent; keyboard, focus, reduced-motion, and print behavior remain usable.

- **AC-FBKR-007 — retained report behavior:** Given a local copied report with no network and no
  VWorld key, when a user filters, sorts by keyboard, changes theme, opens Diagnostics, prints,
  and exports all/filtered UTF-8 CSV, then the existing map/table/CSV/theme/print/reduced-motion/
  keyboard behaviors continue; no VWorld switch appears; and no behavior exposes a credential or
  requires network access.

## 9. Open questions

None. The user fixed the product direction, fallback boundary, and physical-device verification
gate. The implementation role must select the compatible runtime serializer without expanding the
permitted source or anchor policy.

## 10. Decision log and superseded behavior

- **D-FBKR-001** (2026-09-04, Category C — QField fallback geometry reliability): The evidence
  fixture shows three fallback-supplied Type 1 records all labeled `empty geometry` after direct
  SQLite became unavailable. This supersedes any behavior that treats failed/unavailable fallback
  geometry serialization as proof of empty geometry. It preserves XY-only output, per-row
  isolation, and the existing Type 1–4 anchor rules.
- **D-FBKR-002** (2026-09-04, Category C — field-facing status and opt-in diagnostics): This
  supersedes the normal-report presentation of `원본 스키마와 현재 기록`, default raw inventories,
  UUID display, technical paths, and verbose fallback/capability disclosure. It preserves their
  support value only inside closed Diagnostics and permanently excludes iOS sandbox absolute
  paths.
- **D-FBKR-003** (2026-09-04, Category C — analytic card applicability): This supersedes the
  prior always-rendered occurrence/cover/area chart slots and their empty placeholders. It
  preserves the existing species-key aggregation rules and introduces the explicit type-specific
  chart-card matrix in FR-FBKR-014.
- **D-FBKR-004** (2026-09-04, Category C — Korean de-duplication and identifier suppression):
  This supersedes normal-output exposure of repeated semantic fields, raw English/internal labels,
  and internal IDs. It preserves source values when they truly conflict and the deterministic
  provenance/collision behavior required by prior report specifications.
- **D-FBKR-005** (2026-09-04, Category C — conditional VWorld surface): This supersedes the
  unconditional/no-key VWorld control and visible technical background fallback messaging. It
  does not supersede the existing non-blocking VWorld/OSM/offline map policy or its no-secret
  requirement.

## 11. References and approval gate

Normative references: `CLAUDE.md`, `docs/change-control.md`, `specs/TEMPLATE.md`, and the four
extended report specifications named in this document header.

This specification is **DRAFT**. It requires the user's explicit approval before a fresh
test-designer may create acceptance tests and traceability. Implementation must additionally wait
for approval of those acceptance artifacts.
