# Feature: HTML report integrated follow-up — GeoPackage spatial data, stable columns, and analytics

> Status: DRAFT — awaiting user review and explicit approval
> Owner: spec-writer
> Last updated: 2026-09-02
> Extends: `specs/html-report-interactive-analytics.md`, `specs/html-report-map-valid-geometry-collection.md`, and `specs/fieldbuild-kit-report-wizard-followup.md`

## 1. Summary

This follow-up integrates the requested HTML-report behavior: immediately before HTML export, ask
whether the saved VWorld API key may be included; default to omission and use OpenStreetMap for a
standalone HTML in that case, or include the key only after an explicit warning/confirmation. It
opens the project GeoPackage directly as SQLite to collect all registered spatial tables, renders
FK-joined data around the existing survey-type spatial anchors, and locally bundles official d3.js
with verified analytics. It also defines collision-free report columns, a stable CSV header
contract, explicit overview-card semantics, a light/dark theme toggle, and preservation of the
existing map/table/filter/sort/detail/CSV behavior. For geometry dimensionality, the report uses
only valid X/Y ordinates: Z/M dimensions are explicitly discarded during geometry normalization
and are never added to table or CSV attributes.

This is a specification-only change. It does not modify application code, generated projects,
fixtures, tests, or existing specification files.

## 2. Compatibility and terminology

The current saved GeoPackage and its `gpkg_contents`/`gpkg_geometry_columns` metadata are the
report's source of truth. A “spatial table” is an accessible GeoPackage table with a declared
geometry column. A “spatial anchor” is the geometry-bearing record selected by the existing
Type 1–Type 4 rules; FK-joined records contribute attributes and context, not replacement
coordinates.

The existing anchor rules remain unchanged:

| Survey type | Joined report row | Joined map feature anchor |
|---|---|---|
| Type 1 | standalone `inventory_observation` | its own valid geometry |
| Type 2 | `site` → `survey` → `observation`, one row per observation | `survey`; observation geometry never substitutes |
| Type 3 | `site` → `plot` → `survey` → `observation`, one row per observation | `plot`, or `survey` only when plot geometry is unavailable |
| Type 4 | `site` → `survey` → `community` | valid vegetation/community geometry; no plant-observation row |

## 3. Functional Requirements

### 3.1 Saved VWorld setting and basemap fallback

- ~~**FR-IRF-001 (original; superseded by D-IRF-004):** At report generation, the report must
read the current generated project's saved VWorld API-key/configuration variable using the existing
project configuration contract. A non-empty, non-whitespace, structurally usable value is
“usable”; the literal key value must not be displayed in report UI, tables, details, CSV,
diagnostics, or logs.~~
- ~~**FR-IRF-002 (original; superseded by D-IRF-004):** If a usable saved VWorld value exists, the
report must select VWorld as the initial background and use it for tile requests under the existing
D-HRA-003 credential rule. If no usable value exists, the report must select OpenStreetMap
automatically and show its attribution.~~
- **FR-IRF-022 (D-IRF-004 revised VWorld export consent):** Immediately before HTML export, when
  the project has a usable saved VWorld API key, the report flow must show a confirmation popup
  asking whether to include the key in the standalone HTML. The default selection is `미포함`.
  The popup must state that choosing `포함` stores the key in the HTML and may expose it to anyone
  who obtains the file. Choosing `미포함` must produce a standalone HTML that uses OpenStreetMap
  (with attribution) and must not store the key in HTML, CSV, report payload, map/detail data,
  diagnostics, or logs. Choosing `포함` must store the key in the HTML and use VWorld, while the
  exposure warning remains explicit. Cancel, close, or equivalent dismissal must abort export and
  must not create or overwrite the HTML/CSV output.
- **FR-IRF-023:** If no usable saved VWorld key exists, export must use a key-free standalone HTML
  using OpenStreetMap with attribution and must make no blank-key VWorld request.
- **FR-IRF-003:** If the selected background fails, the report must disclose the active status in
  Korean and attempt the other permitted background once when possible. If both fail, the report
  remains usable with a clearly labeled offline-background state. Remote tiles must never gate
  local geometry, joined data, summaries, charts, filtering, sorting, details, theme switching,
  or CSV export.

### 3.2 Direct GeoPackage spatial collection and anchor-based display

- **FR-IRF-004:** Report generation must open the project's GPKG file directly as SQLite, inspect
  `gpkg_contents` and `gpkg_geometry_columns`, and collect every accessible registered spatial
  table, including every actual row, geometry value, all attributes, source table identity,
  geometry-column identity, source CRS, and raw record identity. It must not depend on which
  layers are currently loaded in the project. Collection is read-only and occurs from current
  saved data at export time.
- **FR-IRF-024:** Only when direct SQLite access to the project GPKG is impossible may report
  generation use currently loaded-layer data as a fallback. The report must disclose that
  fallback, identify inaccessible or uncollected tables/rows and the resulting completeness
  limitation, and must not present fallback data as a complete direct-GPKG inventory.
- ~~**FR-IRF-005 (original; superseded by D-IRF-005):** Every collected geometry-bearing record
  must be classified as valid or unusable using the existing explicit CRS transformation and
  serialization contract. Valid geometries are represented in map interchange CRS EPSG:4326/WGS84;
  unusable geometry remains in report data with a stable reason and is omitted only from rendered
  geometry.~~
- **FR-IRF-026:** Every collected geometry-bearing record must be normalized using only its X/Y
  ordinates, then transformed to EPSG:4326/WGS84 when those X/Y values are valid. For Point,
  LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, and GeometryCollection values,
  any Z and/or M ordinates in dimensional WKB or equivalent geometry input must be explicitly
  discarded before serialization and display. The normalized report geometry must contain no Z/M
  ordinates, and Z/M values must not be copied into table or CSV attributes. A geometry with
  valid Z/M values but missing or malformed X/Y values is unusable under the existing invalid-
  geometry limitation contract; it must be retained with a stable reason and omitted from rendered
  geometry. No coordinate may be invented from Z/M, attributes, or another source.
- **FR-IRF-006:** For Type 1–Type 4, map rendering must use the anchor table and fallback order
  in Section 2. The report must join permitted ancestor/child attributes to that anchor by
  established UUID/FK relationships, preserve one-to-many rows, and expose the anchor geometry
  together with its joined context. Observation geometry must never move, duplicate, or replace
  a Type 2/3 anchor.
- **FR-IRF-007:** A valid geometry in any eligible spatial table suppresses the false global
  “유효한 도형 없음” state. That message is allowed only when the complete eligible spatial
  collection has zero valid rendered features. Missing/unusable geometry, inaccessible tables,
  orphan FK rows, and non-spatial tables must be disclosed separately and must not delete source
  rows or fabricate coordinates.
- **FR-IRF-008:** Spatial tables not selected as a Type 1–Type 4 anchor must still be retained in
  the report's collected-source data and limitation/inventory information. They may be displayed
  as source spatial data, but must not be promoted to a survey anchor or used to invent a relation
  absent from the schema.
- **FR-IRF-009:** Existing Type 1–Type 4 FK joins, orphan markers, stable UUIDs, source-record
  identity, species/date aggregation, filtering, sorting, HTML escaping, and UTF-8 quoted CSV
  behavior remain in force. No row may be collapsed merely because several rows share one anchor.

### 3.3 Collision-free columns and machine-readable CSV headers

- **FR-IRF-010:** Before rendering the integrated table, the report must validate that each output
  column has exactly one internal identity and one position. Duplicate source fields, duplicate
  aliases, accidental repeated joins, and collisions from different tables must be detected and
  reported as a generation/data-integrity error or resolved by the deterministic rule below; they
  must never silently overwrite values.
- **FR-IRF-011:** Every integrated-table column must have a unique stable internal header. Existing
  machine-readable headers remain unchanged. A newly exposed field uses normalized ASCII
  `source_table__source_field`; normalization lowercases, converts non-alphanumeric runs to `_`,
  trims separators, and appends `_2`, `_3`, etc. in deterministic source-schema order for any
  collision. The same source table/field always maps to the same header across exports.
- **FR-IRF-012:** Required user-facing identity columns remain consecutive and labeled exactly
  `국명`, `학명`, `KTSN`, while their stable CSV headers remain the established machine-readable
  headers. Any internal header-to-display mapping must preserve the source table/field identity.
- **FR-IRF-013:** Long original English source names and internal headers must not be shown in the
  normal user-facing table, cards, chart labels, or detail labels. The user-facing label must be
  concise Korean or an approved domain label. The full machine-readable header remains available
  in the CSV header and may appear only in an explicit technical/data-dictionary context.
- **FR-IRF-014:** CSV export must include one header per visible/exported column, no duplicate header
  strings, stable ordering, UTF-8 encoding, and correct quoting. Repeated exports of unchanged
  source schema/data must produce identical headers and header order regardless of filtering,
  sorting, theme, or map state.

### 3.4 Overview cards and aggregation semantics

- **FR-IRF-015:** The report overview must show cards for the applicable levels `조사지`, `조사구`,
  `조사`, and `관찰`, with a Korean meaning and aggregation basis on every card. The `조사지`
  card represents the `site` source level; the ambiguous label `조사대상` must not be used. Each
  card must state the source table/level, whether it is a distinct-record count or an expanded
  joined-row count, and how an unavailable level is represented. For each survey type, a level
  that is not present in that type's schema must be shown explicitly as either `0` (when the
  applicable source table is present but has no records) or `해당 레벨 부재` (when the level is
  not part of the survey type), never left blank or implied.
- **FR-IRF-016:** Card counts must be computed from distinct source stable IDs for source-level
  cards: 조사지=`site`, 조사구=`plot`, 조사=`survey`, 관찰=`inventory_observation` for Type 1,
  `observation` for Types 2/3, and the applicable Type 4 community source only when the existing
  report contract defines it as an observation-level card. A joined one-to-many projection must
  not inflate these source counts; the report may show a separate clearly labeled “통합 행 수”
  count. For Type 1, where `site` is not an applicable source level, the `조사지` card must show
  `해당 레벨 부재`; for Types 2–4, the `조사지` value is the distinct `site` count, including
  `0` when the source table is applicable but contains no records.
- **FR-IRF-017:** Existing species occurrence, total-species, observation-day, and Type 4
  community aggregation rules remain authoritative. Chart/card aggregation must use source rows,
  not anchor-feature count or duplicated joined projections.

### 3.5 Theme toggle and d3.js charts

- **FR-IRF-018:** The report must provide an accessible light/dark theme toggle button with a
  visible Korean label/state, keyboard and pointer activation, and a deterministic default theme.
  Switching theme must preserve current map view, filters, sort, expanded sections, selected
  detail, chart selections, and data; it must not rewrite source data or CSV headers.
- **FR-IRF-019:** The report must include the official d3.js distribution as a locally bundled
  asset inside the single HTML file (no remote d3 dependency) and render interactive charts for
  (a) species occurrence count, (b) average cover, and (c) community area. Each chart must have a
  Korean title, unit/aggregation-basis text, accessible data labels or equivalent table, and a
  truthful empty state when its source data is absent.
- **FR-IRF-020:** Species occurrence is the count of applicable observation source rows grouped by
  the existing deterministic species key. Average cover is the arithmetic mean of numeric,
  non-null cover values for the applicable species/group; zero is a valid value and must not be
  treated as missing. Community area is the sum of numeric, non-null area values per community
  (or the existing community grouping key) and must not count plant observations. Invalid or
  missing numeric values are excluded and counted in the chart's limitation note.
- **FR-IRF-021:** Bar and pie charts must support interaction through hover/focus or equivalent
  selection feedback, show the selected category/value in a readable detail or tooltip, and keep
  values consistent with the underlying source aggregation. Chart interaction must not mutate
  records, joins, or export scope.
- **FR-IRF-025:** Chart initialization must validate that the locally bundled d3.js is present and
  that each of the three chart datasets is initialized from the defined source-row aggregation.
  The report must expose a deterministic validation result or limitation state; it must not render
  a plausible chart from missing, uninitialized, or duplicated aggregation data.

## 4. Constraints

- **C-IRF-001:** Existing specification files and all existing FR/DR/NFR/AC/Decision Log IDs are
  historical contracts. They must not be deleted, renumbered, reused, weakened, or silently
  rewritten by this follow-up.
- ~~**C-IRF-002 (original scope rule; superseded by D-IRF-004):** This follow-up may supersede only
  the specific conflicting behavior recorded in Decision Log D-IRF-001 below; all non-conflicting
  HRA/MGC/RWF behavior remains in force.~~
- **C-IRF-003:** GeoPackage inspection, collection, joining, and report generation are read-only;
  no schema, relation, geometry column, CRS, UUID, or source record may be added or changed.
- **C-IRF-004:** Joins use established UUID/FK values only. Display text, row position, geometry
  coincidence, centroid, proximity, photo metadata, or invented keys are not join mechanisms.
- **C-IRF-005:** The report remains standalone for local functions: no remote script, stylesheet,
  font, image, chart library, or spatial service is required. VWorld/OSM tiles are runtime
  enhancements and d3.js must be locally bundled.
- ~~**C-IRF-006 (original credential boundary; superseded by D-IRF-004):** Secrets, attachment
  paths, photo contents, and credentials are excluded from normal report data, user-visible
  labels, CSV, diagnostics, and logs; the existing narrow VWorld tile-request exception remains
  unchanged.~~
- **C-IRF-008 (D-IRF-004 security/function trade-off):** The default and key-free export path
  preserves the no-secret boundary. The explicit include path enables VWorld tiles in a portable
  standalone file, but the API key is recoverable by anyone who possesses or can inspect that
  HTML. Inclusion is permitted only after the warning and affirmative choice; cancellation/close
  is fail-closed for export.
- **C-IRF-007:** This task changes only this specification file. Acceptance-test design and
  implementation require later explicit approval gates.
- **C-IRF-009:** Geometry dimensionality normalization is limited to discarding Z/M and using
  valid X/Y for map display. It does not add coordinate-derived fields to the integrated table or
  CSV, and it does not change source GeoPackage schema or records.

## 5. Assumptions

- **A-IRF-001:** `조사지` refers to the existing `site` level. The report uses only `조사지` for
  this overview concept and does not create a new table or a second alias card.
- **A-IRF-002:** The saved VWorld API key/configuration is readable through the existing generated
  project contract at report-generation time and is not expected to be newly entered in the
  report. The popup controls only whether that already-saved value is embedded in the export.
- **A-IRF-003:** “평균 피도” means the existing applicable numeric cover field(s) in observation
  data; if no unambiguous cover field exists for a survey type, the chart reports not applicable
  rather than guessing a field.
- **A-IRF-004:** “군락별 면적” means the existing numeric area attribute on Type 4 community
  records; geometry-derived area is not substituted unless an already approved contract says so.
- **A-IRF-005:** The report may retain a technical column dictionary in generated data for stable
  CSV mapping, but it is not part of the normal user-facing table.

## 6. Edge Cases

- **E-IRF-001:** Missing, blank, whitespace-only, malformed, or unavailable VWorld setting selects
  OSM without a blank-key request; if both services fail, local report functions remain usable.
- **E-IRF-002:** A GeoPackage has spatial metadata but a table cannot be opened, iterated, or CRS-
  transformed: its limitation is counted and disclosed; other spatial tables still render.
- **E-IRF-003:** Valid site geometry exists while observation geometry is absent: the site and the
  applicable Type 2/3 anchor behavior render according to the type rule, and the false empty map
  state is not shown.
- **E-IRF-004:** One anchor has many child observations, including different identities: exactly
  one anchor feature is emitted with a deterministic child collection, while every child remains
  one joined table/CSV row.
- **E-IRF-005:** Missing/orphan FK, duplicate display names, nulls, and duplicate source field
  names do not cause overwrite or row loss; orphan and collision diagnostics are explicit.
- **E-IRF-006:** Two source fields normalize to the same header: suffix allocation follows source
  schema order and is stable across repeated exports.
- **E-IRF-007:** All source field names are long English names: normal labels remain concise and
  Korean, while CSV retains deterministic machine headers and values.
- **E-IRF-008:** Zero observations, no cover values, or no community area values produce truthful
  zero/empty/not-applicable chart states and never fabricated values.
- **E-IRF-009:** Theme switching while a filter, sort, map selection, or chart selection is active
  preserves that state exactly.
- **E-IRF-010:** The user closes or cancels the VWorld inclusion popup: no HTML or CSV is written,
  and an existing output at the target path is not overwritten.
- **E-IRF-011:** Direct GPKG SQLite access fails or a registered spatial table cannot be opened or
  iterated: fallback is used only for the direct-access failure case, and the report discloses
  the scope limitation and stable reasons for omissions.
- **E-IRF-012:** Official d3.js is missing, malformed, or fails initialization: the report remains
  usable, marks chart analytics unavailable/limited, and does not claim validated chart values.
- **E-IRF-013:** A dimensional WKB geometry contains valid X/Y plus Z, M, or ZM ordinates: the
  displayed geometry is the corresponding two-dimensional X/Y geometry after WGS84 transformation,
  with no Z/M values in its serialized coordinates or table/CSV attributes. If X/Y is missing,
  non-finite, truncated, structurally malformed, or otherwise invalid while Z/M is present, the
  record follows the existing invalid-geometry limitation with no fabricated coordinate.

## 7. Out of Scope

- Editing, deleting, synchronizing, or migrating GeoPackage records or schema.
- Adding new survey types, new anchor rules, new relations, new geometry fields, or new cover/
  area attributes.
- Deriving coordinates from photos, EXIF, GPS, attributes, FK values, centroids, or external
  spatial services.
- Translating third-party attribution/proper names or changing the existing output-location and
  secret contracts.
- Modifying code or tests in this specification-writing task.

## 8. Acceptance Criteria

- ~~**AC-IRF-001 (original; superseded by D-IRF-004):** Given a project with a usable saved
  VWorld value, report generation emits a report whose initial background mode is VWorld and whose
  UI contains attribution but not the key. Given no usable value, the initial mode is OSM and no
  blank/placeholder VWorld request occurs.~~
- **AC-IRF-013:** Given a usable saved VWorld key, immediately before export the popup defaults to
  `미포함` and states the file-exposure warning for `포함`. `미포함` exports HTML using OSM and
  contains no key in HTML/CSV/payload/map/detail/diagnostics/logs; `포함` exports HTML using VWorld
  with the key embedded and the warning remains explicit. Cancel/close writes neither output and
  does not overwrite an existing target.
- **AC-IRF-014:** Given no usable key, export proceeds with key-free OSM HTML without a blank-key
  VWorld request and without offering a usable include choice.
- **AC-IRF-002:** Given VWorld or OSM failure, the report attempts the permitted alternate once,
  shows the final Korean active/fallback/offline state, and keeps local map, joined table, cards,
  charts, filtering, sorting, detail, theme toggle, and CSV usable.
- **AC-IRF-003:** Given a GeoPackage containing at least two geometry-column tables and one
  non-spatial table, report data contains every accessible spatial table's records, geometry
  column, CRS, attributes, and source identity; the non-spatial table is not counted as a geometry
  failure.
- **AC-IRF-015:** Given a project whose loaded-layer set omits one or more registered spatial
  tables, direct SQLite reads of `gpkg_contents`/`gpkg_geometry_columns` still include every
  accessible registered table's actual rows, geometry, CRS, and attributes in payload/tables/map
  features. When direct access is unavailable, loaded-layer fallback is used only then and the
  report identifies the omitted/unverified scope and completeness limitation.
- **AC-IRF-004:** Given representative Type 1, Type 2, Type 3, and Type 4 data, the map uses
  exactly the Section 2 anchor/fallback rules, preserves one joined row per source observation or
  community row, retains site/community geometries as separate eligible features, and never emits
  an observation-only replacement for a Type 2/3 anchor.
- **AC-IRF-005:** Given at least one valid geometry in the eligible collection and other missing or
  invalid geometries, the report renders the valid feature(s), retains every invalid source row
  with reason, and does not show “유효한 도형 없음”. With zero valid eligible features, it shows
  that message plus the applicable reason/count disclosure.
- **AC-IRF-006:** Given a one-to-many Type 2/3 anchor with two children and one orphan, the anchor
  appears once with both child identity values in deterministic order, all three child rows remain
  in the integrated table/CSV, and the orphan has its integrity marker without fabricated geometry.
- **AC-IRF-007:** Given joined fields from different tables with the same display name and source
  fields that normalize to the same slug, the integrated-table validator reports no silent
  overwrite; output headers are unique, deterministic, and follow `source_table__source_field`
  plus numeric suffixes. Repeating export with unchanged schema yields byte-identical header rows.
- **AC-IRF-008:** Given long English source names, normal table/card/chart/detail labels do not
  display those raw names; the CSV contains stable machine-readable headers, exactly one header per
  exported column, and the existing `국명`, `학명`, `KTSN` values/header contract is preserved.
- **AC-IRF-009:** Given records at each available hierarchy level, each overview card states its
  meaning/source/basis and its value equals the distinct stable-ID count for that source level;
  one-to-many joins do not inflate it. The site-level card is labeled exactly `조사지`, never
  `조사대상`: for Type 1 it shows `해당 레벨 부재`, and for Types 2–4 it shows the distinct
  `site` count, including `0` when the applicable `site` source has no records. Any other level
  absent because it is not part of the survey type is labeled `해당 레벨 부재`; an applicable
  empty source level is shown as `0`.
- **AC-IRF-010:** Given observations with known species, cover values including zero, missing/invalid
  cover, and Type 4 communities with known/missing area, d3.js renders interactive bar/pie species
  occurrence, average-cover, and community-area charts whose displayed values equal the defined
  source-row arithmetic and whose limitation/empty states are truthful.
- **AC-IRF-016:** Given a single-file export, local official d3.js is present and chart
  initialization validation succeeds for species occurrence, average cover, and community area;
  each displayed aggregate equals the defined source-row arithmetic. If the local bundle or
  initialization is unavailable, the report exposes a truthful unavailable/limited state rather
  than an unvalidated chart.
- **AC-IRF-011:** Given an active filter, sort, expanded card, selected map detail, and chart
  selection, switching light → dark → light preserves each state and changes only theme styling;
  keyboard activation of the toggle works and CSV headers/data are unchanged.
- **AC-IRF-012:** Given HTML/script-like values, commas, quotes, newlines, Korean text, duplicate
  names, and secrets, displayed values are inert, CSV is valid UTF-8 and correctly quoted, and no
  key/credential/attachment path appears in normal report surfaces, diagnostics, or logs.
- **AC-IRF-017:** Given valid dimensional WKB or equivalent geometry for Point, LineString, Polygon,
  MultiPoint, MultiLineString, MultiPolygon, and GeometryCollection with X/Y plus Z, M, or ZM
  ordinates, the report discards Z/M, transforms the remaining X/Y geometry to EPSG:4326/WGS84,
  and displays only the resulting two-dimensional geometry. The integrated table and CSV contain
  no Z/M coordinate columns or copied Z/M values. Given Z/M values without valid X/Y, or malformed
  X/Y structure, the record is retained as invalid with the existing stable limitation reason,
  is omitted from rendered geometry, and receives no fabricated coordinate.

## 9. Open Questions

- **O-IRF-001:** Which exact saved project variable/configuration path is the authoritative VWorld
  source on every supported platform? The implementation must use the existing contract; confirm
  the concrete name before test design if more than one exists.
- **O-IRF-002:** Which existing field names are authoritative for “피도” across Type 1–3? If the
  schema has multiple cover fields, stakeholder selection is required before implementation.
- **O-IRF-003 (resolved by D-IRF-003):** The former terminology question is closed by the
  stakeholder decision: the overview uses `조사지` for the `site` count, does not use the
  ambiguous `조사대상` label, and explicitly distinguishes `0` from `해당 레벨 부재`. This is
  retained only to preserve the existing ID and is no longer an open question.
## 10. Decision Log

- **D-IRF-001** (2026-09-01, Category C/B — explicit integrated follow-up): The stakeholder
  explicitly requested that the report read the saved VWorld key/variable, use VWorld when
  available and OSM otherwise; directly collect GeoPackage spatial tables including geometry;
  display FK-joined data around existing spatial anchors; validate duplicate/colliding columns;
  hide long English names while preserving stable CSV headers; clarify overview-card semantics;
  add a light/dark toggle; and add d3.js interactive charts for species occurrence, average cover,
  and community area. This decision adds FR/AC-IRF-001–012 and supersedes only conflicting
  assumptions or out-of-scope statements in earlier draft report specs. It does not delete or
  reuse any prior ID, alter the existing Type 1–Type 4 anchor rules, or permit source-data loss.
- **D-IRF-002** (2026-09-01, Category B — clarification): “유효한 도형 없음” is a global eligible-
  collection state, not an observation-layer-only state. Any valid eligible spatial feature makes
  the state false; unusable records remain disclosed data. This clarifies the intent of the prior
  MGC geometry-preservation requirements without changing their anchor precedence.
- **D-IRF-003** (2026-09-01, Category C — stakeholder-approved terminology and empty-level behavior):
  The stakeholder approved removing the ambiguous overview term `조사대상`. The `site` record
  count must be displayed as `조사지`. When a survey type has no applicable `site` level, the
  overview must explicitly show `해당 레벨 부재`; when the level is applicable but has no site
  records, it must show `0`. The same explicit distinction applies to other hierarchy cards.
  This supplements FR-IRF-015/016 and AC-IRF-009 without deleting or renumbering any existing
  requirement or decision-log ID.
- **D-IRF-004** (2026-09-01, Category C/B — explicit stakeholder-approved VWorld consent, direct
  GPKG authority, and local d3 verification): The stakeholder explicitly directed: “HTML report
  export 직전에 VWorld API key를 HTML에 포함할지 묻는 확인 팝업을 띄운다. 기본 선택은 미포함.
  미포함이면 독립 HTML은 OSM을 사용하고 key는 HTML/CSV/payload/detail에 저장하지 않는다.
  포함을 선택하면 key를 HTML에 저장해 VWorld를 사용하되, 키가 파일을 가진 사람에게 노출될
  수 있다는 경고를 명시한다. 취소/닫기는 export를 중단한다.” The stakeholder further directed
  that the project GPKG be opened directly as SQLite, with all actual rows, geometry, CRS, and
  attributes registered in `gpkg_contents` and `gpkg_geometry_columns` included in report
  payload/tables/map features, independent of currently loaded layers; loaded-layer fallback is
  allowed only when direct access is impossible and its limitation must be reported. Official
  d3.js must be local in the single HTML, with initialization and species occurrence, average
  cover, and community area aggregation verified. This supersedes the conflicting VWorld-first or
  blanket-no-embedded-key text preserved above in FR-IRF-001/002, C-IRF-006, and AC-IRF-001 only.
  The existing Korean overview labels (`조사지`, `조사구`, `조사`, `관찰`), deduplicated visible
  columns/stable CSV headers, Type 1–4 anchor joins, and map/table/filter/sort/detail/CSV behavior
  remain unchanged. The security/function trade-off is explicit: omission is the default and
  protects the key; affirmative inclusion enables portable VWorld rendering but exposes the key
  to anyone who possesses or inspects the HTML.
- **D-IRF-005** (2026-09-02, Category C — explicit stakeholder-approved geometry dimensionality
  change): The stakeholder explicitly directed: “HTML report가 GeoPackage/QGIS geometry를 읽을 때
  Z/M 차원은 보존하지 않고 명시적으로 제거하며 X/Y 좌표만 사용한다. Point/LineString/Polygon/
  Multi*/GeometryCollection 및 dimensional WKB의 Z/M ordinate는 버리고, X/Y가 유효한 geometry만
  WGS84로 변환하여 표시한다. Z/M만 유효하고 X/Y가 없거나 malformed하면 기존 invalid geometry
  limitation을 따른다. 표/CSV 속성에는 Z/M 좌표를 추가하지 않는다.” This supersedes the
  conflicting geometry-type/coordinate-structure preservation wording retained above in
  FR-IRF-005 and inherited geometry-preservation text for this integrated HTML-report behavior;
  it does not delete or renumber any existing ID, alter source GeoPackage data/schema, or permit
  coordinate invention. Z/M-only or malformed-X/Y records remain subject to the existing invalid
  geometry limitation contract.

## 11. References and approval gate

Normative references: `CLAUDE.md`, `docs/change-control.md`,
`specs/html-report-interactive-analytics.md`, `specs/html-report-map-valid-geometry-collection.md`,
`specs/fieldbuild-kit-report-wizard-followup.md`, and `specs/TEMPLATE.md`.

This document remains DRAFT until the user explicitly approves it. After approval, a fresh
test-designer may create acceptance tests and traceability; implementation must wait for the
separate acceptance-test approval gate.
