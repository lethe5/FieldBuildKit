# Feature: Interactive map, joined data, and exportable HTML report

> Status: DRAFT — awaiting stakeholder review
> Owner: spec-writer
> Last updated: 2026-09-03
> Extends: existing unconditional HTML report mechanism (FR-QPB-133/134, Decision Logs D-83/D-87)
> Further revised: 2026-08-30 — Category C Decision Log D-HRA-001 supersedes the outside-project
> save-location choice: HTML reports and joined CSV files are saved in the current QField project
> folder, reflecting the QField 4.2.4 external-picker limitation.
> Further revised: 2026-08-30 — Category C Decision Log D-HRA-002 supersedes the prior species-key
> fallback for observations that have only `selected_ktsn`: those observations have no species
> key and are excluded from species aggregation rather than placed in “미동정”.
> Further revised: 2026-09-02 — Category C Decision Log D-HRA-004 reconciles D-HRA-002 with the
> later Types 1–3 overview-card contract: `총 종수` is a direct-layer distinct valid
> `selected_ktsn` count and can therefore include KTSN-only observations, while species
> occurrence/chart grouping and “미동정” behavior remain unchanged.
> Further revised: 2026-08-31 — Category C Decision Log D-HRA-003 makes a saved project VWorld
> API key authoritative for the report background and adds automatic OpenStreetMap fallback.
> Further revised: 2026-09-03 — Category C Decision Log D-HRA-005 changes mapped-feature
> activation to one adjacent Leaflet popup with feature-type-specific minimal content and removes
> the duplicate right-side custom detail panel for feature clicks.

## 1. Summary

Extend the existing QField “Export HTML Report” output from a static schema-and-record table
into an interactive field-survey report. The report will provide a map, a complete joined view of
the survey hierarchy, collapsible summaries, species counts, summary cards, and CSV export while
remaining useful when optional map/network capabilities are unavailable.

The feature is generated from the current project data at the moment the user requests an export;
it must not use build-time snapshots of collected records. The HTML report and joined CSV are
ordinary user-readable files, not a synchronization or upload mechanism.

## 2. Terminology and data scope

The report uses the generated project's schema as the source of truth. The requested Korean
logical levels map to the current schema as follows:

| Report level | Current schema table/display layer | Identifier and join key |
|---|---|---|
| 조사대상 | `site` / `조사지` where present | `site.site_id` |
| 조사 | `survey` / `조사` | `survey.survey_id`; parent FK to `site_id` or `plot_id` |
| 조사구 | `plot` / `고정조사구` where present | `plot.plot_id`; parent FK to `site_id` |
| 식물관찰 | `inventory_observation` or `observation` / `식물관찰` | `inventory_id` or `observation_id`; Type 2/3 parent FK to `survey_id` |

The current Type 3 hierarchy is `site → plot → survey → observation`; Type 2 is
`site → survey → observation`; Type 1 has a standalone `inventory_observation`; and Type 4 has
`site → survey → community` with no `plot` or `observation` table. The report must apply the
same rules to every generated survey type and must not invent rows for a level absent from that
project's schema.

## 3. Functional Requirements

- **FR-HRA-001:** The existing “Export HTML Report” action remains on-demand and user-triggered.
  It must gather the current saved project data at export time and must not run automatically,
  periodically, or in the background.

- **FR-HRA-002:** The generated HTML report must retain the existing report metadata: project
  display name, project ID, survey type, generation timestamp, report-generation timestamp, and
  the actual record counts for every domain table present in the current project.

- **FR-HRA-003:** The report must contain an interactive map implemented with Leaflet and/or D3,
  showing every current domain feature for which usable geometry/coordinates exist. Point and
  polygon geometry must be represented in the correct project CRS/WGS84 transformation required by
  the map. Features without usable geometry remain in the tables and summaries and are not silently
  discarded from the report.

- ~~**FR-HRA-004 (original; superseded by Decision Log D-HRA-003):** A VWorld background option
  must be available for the interactive map when the required VWorld connection, credentials,
  and network access are available in the running environment. The map must show an explicit
  unavailable/offline state instead of failing the entire report when the VWorld service, key, or
  network is unavailable.~~
- **FR-HRA-004 (revised; Decision Log D-HRA-003):** When the current QField project contains a
  saved, usable VWorld API key, the report must use the corresponding VWorld tile background for
  the interactive map. When the project has no usable VWorld key, the report must automatically
  use OpenStreetMap tiles as the background. If the selected remote tile service is unavailable,
  the report must disclose that status and may fall back to the other available background;
  failure of both remote services must leave the local feature layers, map controls, tables,
  summaries, filtering, sorting, detail views, and CSV creation usable with an explicit
  offline-background state. Under the stakeholder's Option 1 decision, the key is not displayed
  in the report UI, but may be embedded in the exported HTML/tile request because standalone
  VWorld tiles require the credential.

- ~~**FR-HRA-005 (original; superseded by Decision Log D-HRA-005):** Clicking a mapped feature
  must show a readable detail view containing the feature's report-level table/layer name, stable
  domain UUID, human-readable field labels and values, and its joined parent context when that
  context exists. The detail view must escape values as HTML and must not expose raw HTML supplied
  as field data.~~
- **FR-HRA-005 (revised; Decision Log D-HRA-005):** When a mapped feature is activated by the
  existing Leaflet pointer-click or keyboard-activation path, the report must show exactly one
  transient Leaflet popup adjacent to the clicked feature. The same feature activation must not
  render or open the duplicate right-side custom detail panel. For an observation feature, the
  popup must display only the four labeled fields `조사일`, `조사자`, `국명`, and `학명`; it must
  not display the feature/layer name, UUID, joined parent context, or any other observation field.
  For a site/`조사지` feature, the popup must display only the site's name. No feature-identifying
  label may remain permanently visible on the map after activation ends. Popup values must remain
  readable inert text through the existing HTML-escaping path.

- **FR-HRA-006:** The report must provide one complete joined interactive table for all applicable
  levels in the current project. For Type 3, each row represents the relationship
  `조사대상(site) → 조사구(plot) → 조사(survey) → 식물관찰(observation)`; for Type 2 it is
  `조사대상 → 조사 → 식물관찰`; for Type 1 it is the standalone 식물관찰 record; and for
  Type 4 it is the applicable `조사대상 → 조사 → 군락` data with absent levels represented as
  empty rather than fabricated values.

- **FR-HRA-007:** The joined table must preserve one-to-many relationships without data loss or
  accidental deduplication. A child row with a missing parent must remain visible with an explicit
  missing-parent marker and must be counted in an integrity summary. A parent with multiple
  children must produce the corresponding number of joined rows.

- **FR-HRA-008:** The joined table must support client-side filtering across all visible joined
  fields, including at least 조사대상 name, 조사 date, 조사구 name, Korean species name,
  scientific species name, KTSN when present, and free-text notes. Filtering must update the
  visible row count without changing the underlying collected data.

- **FR-HRA-009:** The joined table must support sorting by every visible column, with stable,
  deterministic handling of null/empty values and numeric/date values. Sorting must not mutate
  the GeoPackage or the source data represented by the report.

- **FR-HRA-010:** The report must provide a joined-CSV save action. The CSV must contain the same
  joined rows and visible field values as the report's joined table, include a header row with
  stable machine-readable column names, use UTF-8, and correctly quote commas, quotes, newlines,
  and non-ASCII Korean text. CSV export must use the currently filtered or all joined rows only
  according to an explicitly visible user choice; the default choice must be stated in the UI.

- **FR-HRA-011:** The report must provide collapsible sections for 조사대상, 조사, and 조사구
  summaries. Each section must show its record count and a concise per-record summary, and its
  expanded/collapsed state must not remove records from the joined table or map.

- ~~**FR-HRA-012 (original; superseded by Decision Log D-HRA-002):** The report must show species occurrence counts grouped by a deterministic species key. For Types 1–3, the key is the selected Korean name when present, otherwise the selected scientific name, otherwise an explicit “미동정” bucket; the display must include the scientific name and KTSN when those values are available. The count must count observation rows, not map vertices, parent rows, or duplicate joined projections. For Type 4, `dominant_species` may be shown in a separate community-species summary and must not be silently conflated with plant-observation counts.~~
- **FR-HRA-012 (revised; Decision Log D-HRA-002):** The report must show species occurrence
  counts grouped by a deterministic species key. For Types 1–3, the key is the selected Korean
  name when present, otherwise the selected scientific name. When both selected names are empty
  and `selected_ktsn` is non-empty, the observation has no species key: it is excluded from
  species occurrence counts and must not be placed in a separate “미동정” bucket. When all three
  selected species fields are empty, the explicit “미동정” bucket remains the fallback. The
  display must include the scientific name and KTSN when those values are available for a keyed
  observation. The count must count observation rows, not map vertices, parent rows, or duplicate
  joined projections. For Type 4, `dominant_species` may be shown in a separate community-species
  summary and must not be silently conflated with plant-observation counts. This species-key
  contract also governs species occurrence charts; it is distinct from the newer overview-card
  `총 종수` measure in the revised FR-HRA-013.

- ~~**FR-HRA-013 (original; superseded by Decision Log D-HRA-002):** The report must show summary cards for total species count, 조사대상 count, 조사구 count, and observation-day count. Total species count is the number of distinct non-empty species keys in the applicable observation data; 조사대상 and 조사구 counts are distinct current records in their respective tables (zero where the table is absent); and observation-day count is the number of distinct valid calendar dates from the applicable observation/survey date fields, with an explicit “날짜 없음”/unknown indication for records that have no valid date rather than an invented date.~~
- ~~**FR-HRA-013 (revised; Decision Log D-HRA-002; overview-card total-species portion superseded by Decision Log D-HRA-004):** The report must show summary cards for
  total species count, 조사대상 count, 조사구 count, and observation-day count. Total species
  count is the number of distinct species keys produced by FR-HRA-012; an observation whose two
  selected name fields are empty and whose only selected species value is `selected_ktsn` produces
  no key and is excluded from this count. 조사대상 and 조사구 counts are distinct current
  records in their respective tables (zero where the table is absent); and observation-day count
  is the number of distinct valid calendar dates from the applicable observation/survey date
  fields, with an explicit “날짜 없음”/unknown indication for records that have no valid date
  rather than an invented date.~~
- **FR-HRA-013 (revised; Decision Log D-HRA-004):** For the Type 1–3 overview card specifically
  labeled `총 종수`, the value is the distinct count of valid `selected_ktsn` values read directly
  from the schema-defined source layer: `inventory_observation` for Type 1 and `observation` for
  Types 2/3. This is an overview-card measure, not the cardinality of the FR-HRA-012 species-key
  groups: a record with both selected names empty and only a valid `selected_ktsn` therefore
  counts in `총 종수`, while remaining excluded from species occurrence/chart grouping and
  “미동정”. Joined rows, aliases, and join fan-out must not supply or inflate this count. `null`,
  empty-string, and whitespace-only KTSN values are excluded and disclosed; an empty present
  source layer yields `0`, while an absent required source layer is disclosed rather than silently
  treated as `0`. Type 4 has no `총 종수`/species overview card. The exact type-specific card
  order and the direct-layer source/date contracts are defined by
  `specs/html-report-integrated-data-map-summary-theme.md` §2.2 and FR-IHRM-012–014.

- ~~**FR-HRA-014 (original; superseded by Decision Log D-HRA-001):** The report must provide a user-visible save-location choice for the HTML report and joined CSV. The default project-folder location remains available, and the user must be able to choose a writable location outside the project folder through the supported QField/QML file-picker or save-location API. The selected path must be shown before or at confirmation, must not be silently replaced by a project-relative fallback, and a failure to obtain/write the selected location must produce an actionable non-success message.~~
- **FR-HRA-014 (revised; Decision Log D-HRA-001):** The report must save both the HTML report and
  joined CSV in the current QField project folder. QField 4.2.4 does not expose a supported
  project-plugin file/directory picker or save-location API for writing these outputs outside that
  folder, so no outside-project destination choice is required or may be claimed. The UI must show
  the project-folder destination and exact resulting paths; a failure to write there must produce
  an actionable non-success message and must not be reported as a successful export.

- **FR-HRA-015:** The report must remain a standalone HTML document: all report code, CSS, and
  required Leaflet/D3 library code must be embedded or otherwise packaged so that the report's
  data tables, summaries, filtering, sorting, and CSV construction work without fetching a remote
  script, stylesheet, font, or image. VWorld and OpenStreetMap map tiles are runtime network
  enhancements; their absence must not prevent the rest of the local report from rendering.

- **FR-HRA-016:** All displayed and exported field values must be escaped/quoted safely. The
  report must never execute JavaScript or HTML supplied in collected field values, notes, names,
  UUIDs, or project metadata.

- **FR-HRA-017:** The report must disclose data limitations in the UI: missing parent references,
  invalid geometry, missing dates, VWorld-to-OpenStreetMap fallback or unavailable remote
  background, the QField 4.2.4
  project-folder-only save limitation, and any records omitted only because the current schema does
  not define that level. A report-generation or project-folder-write failure must not be presented
  as a successfully complete report.

## 4. Constraints

- **C-HRA-001:** This feature extends, and does not silently weaken, FR-QPB-133/134. The report
  remains on-demand, project-specific, and portable; it must not change the existing project's
  GeoPackage records, relations, schema, UUIDs, attachments, or layer visibility.

- **C-HRA-002:** The complete joined data must be based on the current GeoPackage-backed records
  and established schema foreign keys. Display-layer names are for presentation only; joins must
  use the stable UUID/FK columns, never row position, display text, or geometry coincidence.

- **C-HRA-003:** Existing FR-QPB-133's exclusion of photo contents/references and identification
  metadata is superseded only if a later stakeholder-approved change explicitly adds them. This
  extension does not itself require photo files, photo paths, Pl@ntNet metadata, probability
  values, or other attachments in the report except the explicitly requested species fields
  (`selected_korean_name`, `selected_scientific_name`, `selected_ktsn`) needed for the species
  summary.

- **C-HRA-004:** No network service may be required for local report rendering, table interaction,
  summaries, or CSV creation. VWorld or OpenStreetMap background tiles may be unavailable without
  invalidating those local functions.

- ~~**C-HRA-005 (original; superseded by Decision Log D-HRA-001):** Output paths must obey the selected platform's QField sandbox and permission rules. The implementation must use an approved user-facing path-selection mechanism and must not bypass platform security through arbitrary filesystem APIs.~~
- **C-HRA-005 (revised; Decision Log D-HRA-001):** Output paths must obey the selected platform's
  QField sandbox and permission rules. On the target QField 4.2.4 runtime, the HTML report and
  joined CSV must be written only to the current project folder because no supported
  project-plugin external save-location picker/API is exposed. The implementation must not bypass
  platform security through arbitrary filesystem APIs or claim unsupported outside-project output.

- **C-HRA-006:** Geometry transformation must be explicit and deterministic. A geometry that
  cannot be transformed or serialized must be reported as invalid for the map, while its
  non-geometry attributes remain eligible for tables and counts.

- **C-HRA-007:** The report must be usable with zero records, one-to-many relationships, null
  optional fields, duplicate display names, malformed dates, missing parents, and large datasets
  within the target QField memory/performance envelope. No fixed maximum row count may be invented
  by the report implementation.

- **C-HRA-008:** The implementation must respect licenses and attribution requirements for
  embedded Leaflet/D3 code, VWorld imagery, and OpenStreetMap tiles. Required notices and the
  active/fallback background status must be included in the report or its generated metadata
  without making local report interaction dependent on a remote page.

- **C-HRA-009 (Decision Log D-HRA-005):** The mapped-feature popup change is limited to the
  feature-click/keyboard-activation presentation and interaction surface. It must not change
  GeoPackage records, schema, joins, stable identifiers, map geometry, CRS transformation, table
  rows, summaries, or CSV output.

## 5. Assumptions

- **A-HRA-001:** “조사대상” means the current `site`/`조사지` level for projects that define it.
  This terminology is recorded as an assumption because the current schema's confirmed display
  label is `조사지`, not `조사대상`; if the stakeholder means a different table, the mapping must
  be revised before implementation.

- **A-HRA-002:** The requested “종별 출현횟수” means counts of observation records, not counts of
  distinct sites, 조사구, or map features. The species-key precedence is defined in FR-HRA-012
  pending stakeholder confirmation.

- **A-HRA-003:** A generated project can expose enough QField/QML-visible information to enumerate
  every current feature and read its attributes/geometry. This is not yet confirmed for the
  target QField build; the existing report feature records a similar feasibility boundary in
  Open Question O-41.

- **A-HRA-004:** “Leaflet/D3 지도” permits Leaflet for map rendering and D3 (or equivalent local
  DOM/SVG logic) for charts/table interaction, provided the report visibly delivers the requested
  map and interactions. If the stakeholder requires both libraries simultaneously, that must be
  confirmed in the open questions.

- **A-HRA-005:** The report is primarily a QField-generated artifact intended to be opened in a
  desktop/mobile browser after transfer. For the target QField 4.2.4 runtime, the supported output
  destination is the current project folder; platform-specific external path-picker behavior is not
  assumed or required.

## 6. Edge Cases

- **E-HRA-001:** The project has no records. The map, joined table, summaries, counts, and CSV
  remain valid empty states; summary cards show zero and no fake “unknown” feature is added.

- **E-HRA-002:** A child FK does not match any parent UUID. The child appears once with a
  localized missing-parent marker, and the report includes the orphan count in its integrity
  notice.

- **E-HRA-003:** A parent has zero, one, or many children. Parent summaries remain present even
  with zero children, and one-to-many children are not collapsed into a single arbitrary child.

- **E-HRA-004:** A feature has invalid, missing, or unsupported geometry/CRS. It remains in the
  joined table and counts, is excluded only from the map layer, and is included in the limitation
  notice.

- **E-HRA-005:** Dates are null, malformed, timezone-bearing, or mixed DATE/DATETIME values. Valid
  values are normalized to calendar dates using one documented rule; invalid/null values are not
  counted as observation days and are reported as unknown-date records.

- ~~**E-HRA-006 (original; superseded by Decision Log D-HRA-002):** Two records share the same Korean or scientific display name. They are grouped into one species key only when the defined key fields agree; stable UUIDs remain available in details and rows so records are never mistaken for one another.~~
- **E-HRA-006 (revised; Decision Log D-HRA-002):** Two records share the same Korean or
  scientific display name. They are grouped into one species key only when the defined key
  fields agree; stable UUIDs remain available in details and rows so records are never mistaken
  for one another. An observation with both selected name fields empty and only a non-empty
  `selected_ktsn` remains visible in joined data and any eligible map/detail views, but contributes
  no species occurrence/chart group or “미동정” bucket. Under the narrower overview-card
  reconciliation in D-HRA-004, that same valid direct-layer KTSN does contribute once to the
  Types 1–3 `총 종수` card, independently of its lack of a species key. An observation with all
  three selected species fields empty follows the explicit “미동정” fallback in FR-HRA-012.

- **E-HRA-007:** A field contains HTML/JavaScript-looking text, commas, quotes, newlines, or
  Korean characters. HTML output is escaped and CSV output is RFC-compatible quoted UTF-8.

- ~~**E-HRA-008 (original; superseded by Decision Log D-HRA-003):** VWorld cannot be reached or
  its key is unavailable. The report loads with a clearly labeled unavailable background, local
  feature layers and all non-map functions intact.~~
- **E-HRA-008 (revised; Decision Log D-HRA-003):** If the project has a usable saved VWorld API
  key, VWorld is attempted first; if there is no usable key, OpenStreetMap is selected
  automatically. If the selected service cannot load, the report discloses the failure and may
  attempt the alternate background. If neither remote service loads, the report keeps local
  feature layers and all non-map functions intact with a clearly labeled offline-background
  state. The key is not displayed in the report UI. Because Option 1 selects VWorld in a
  standalone exported HTML file, the credential may be present in that file's tile-request data;
  this is an explicit accepted trade-off for VWorld-first behavior.

- ~~**E-HRA-009 (original; superseded by Decision Log D-HRA-001):** The user cancels the location picker or selects a non-writable/out-of-sandbox path. No partial success toast is shown; the report remains available in memory and the user is offered a retry or the explicitly chosen project-folder destination.~~
- **E-HRA-009 (revised; Decision Log D-HRA-001):** QField 4.2.4 provides no supported external
  location picker for this project-plugin export. If the current project folder is unavailable or
  not writable, no partial or false-success message is shown; the report remains available in
  memory and the UI provides an actionable retry/write-error message without silently redirecting
  the output elsewhere.

- **E-HRA-010:** The dataset is too large for a single in-memory interactive rendering pass. The
  implementation must surface a clear limitation/error and preserve data integrity; it must not
  silently truncate rows or counts.

## 7. Out of Scope

- Editing, deleting, or synchronizing GeoPackage records from the report.
- Uploading the report or CSV to QFieldCloud, VWorld, or another remote service.
- Automatic report generation after every save or on project close.
- Including original photo files, attachment paths, EXIF, Pl@ntNet candidate lists, occurrence
  probability rasters, or identification audit metadata beyond the three explicitly used species
  fields.
- Changing survey schemas, relation definitions, UUID defaults, layer visibility, or QField's
  native feature forms.
- Replacing the existing report with a server-rendered dashboard or a report that requires a
  remote JavaScript bundle.

## 8. Acceptance Criteria

- **AC-HRA-001:** Given a generated project of each supported survey type, when the user taps
  “Export HTML Report,” then a report is generated from the current saved records and retains the
  existing project metadata and per-table record counts.

- **AC-HRA-002:** Given a project containing point/polygon domain features, when the report is
  opened, then its Leaflet/D3-based map shows every valid feature in the correct location and
  records invalid/missing geometry without dropping those features from the report data.

- ~~**AC-HRA-003 (original; superseded by Decision Log D-HRA-005):** Given a mapped feature,
  when the user clicks it, then a detail view displays its stable UUID, escaped labeled
  attributes, and all available joined parent context.~~
- **AC-HRA-003 (revised; Decision Log D-HRA-005):** Given a mapped point or polygon feature, when
  the user pointer-clicks it or uses the existing keyboard activation path, then exactly one
  transient Leaflet popup appears adjacent to that feature and no duplicate right-side custom
  detail panel appears. If the feature is an observation, the popup contains only the labeled
  values `조사일`, `조사자`, `국명`, and `학명`; if the feature is a site/`조사지`, it contains
  only the site name. Popup values are readable inert escaped text, and no permanent feature
  label is left on the map. The feature remains at the geometry location required by AC-HRA-002.

- **AC-HRA-004:** Given a Type 3 project with site, plot, survey, and observation rows, when the
  report's joined table is opened, then each observation is joined through the UUID/FK chain to
  its correct site, plot, and survey, one-to-many rows are preserved, and missing-parent rows are
  visible with an integrity marker.

- **AC-HRA-005:** Given Type 1, Type 2, and Type 4 projects, when their joined tables are opened,
  then each table uses only the levels defined by that project's schema, with absent levels shown
  as empty and no fabricated records.

- **AC-HRA-006:** Given joined rows containing Korean text, nulls, dates, numeric values, notes,
  and duplicate display names, when the user filters and sorts the table, then filtering spans
  the visible joined fields, sorting is deterministic/type-appropriate, and no source record is
  changed or silently removed from the unfiltered dataset.

- **AC-HRA-007:** Given a table view with a filter applied, when the user chooses CSV export and
  confirms the visible/all-rows choice, then the saved UTF-8 CSV has the same selected joined rows,
  stable headers, correct quoting, and the exact Korean/non-ASCII values shown by the report.

- **AC-HRA-008:** Given 조사대상, 조사, and 조사구 records, when the user expands or collapses
  each summary section, then each section displays its record count and concise summaries while
  the joined table and map retain all records.

- ~~**AC-HRA-009 (original; superseded by Decision Log D-HRA-002):** Given observations with selected Korean names, scientific names, KTSN, missing names, and repeated records, when the report is generated, then species occurrence counts use the specified deterministic key and count observation rows exactly once; Type 4 community dominant species is not silently counted as an observation.~~
- **AC-HRA-009 (revised; Decision Log D-HRA-002):** Given observations with selected Korean
  names, scientific names, KTSN, missing names, an observation with both selected names empty and
  only `selected_ktsn` populated, and repeated records, when the report is generated, then
  species occurrence counts use the specified deterministic key and count each keyed observation
  row exactly once. The KTSN-only observation remains available in the joined report data but
  contributes no species occurrence/chart group and is not placed in “미동정”; its separate
  overview-card treatment is defined by revised AC-HRA-010. A record with all three selected
  species fields empty follows the explicit “미동정” fallback. Type 4 community dominant species
  is not silently counted as an observation.

- ~~**AC-HRA-010 (original; superseded by Decision Log D-HRA-002):** Given valid and missing dates across the applicable survey/observation records, when summary cards are displayed, then total species, 조사대상, 조사구, and distinct valid observation-day counts are correct, with missing/invalid dates disclosed rather than fabricated.~~
- ~~**AC-HRA-010 (revised; Decision Log D-HRA-002; overview-card total-species portion superseded by Decision Log D-HRA-004):** Given valid and missing dates across the
  applicable survey/observation records, including an observation with both selected names empty
  and only `selected_ktsn` populated, when summary cards are displayed, then total species follows
  FR-HRA-012 and excludes that KTSN-only observation, while 조사대상, 조사구, and distinct valid
  observation-day counts are correct. Missing/invalid dates are disclosed rather than fabricated.~~
- **AC-HRA-010 (revised; Decision Log D-HRA-004):** Given Types 1–3 direct source layers with
  valid and invalid KTSN values, KTSN-only observations, and joined rows that repeat those source
  records, when overview cards are displayed, then `총 종수` equals the distinct valid
  `selected_ktsn` count from the applicable direct source layer and includes each KTSN-only value
  once. The same KTSN-only observation remains excluded from FR-HRA-012 species occurrence/chart
  groups and “미동정”; missing/invalid dates and invalid KTSN values are disclosed rather than
  fabricated or counted. Type 4 displays no `총 종수`/species card. The type-specific
  direct-layer, empty-versus-absent, and no-join-fan-out assertions are traced to AC-IHRM-008/009/013.

- ~~**AC-HRA-011 (original; superseded by Decision Log D-HRA-003):** Given network access and a
  valid configured VWorld connection, when the user enables the VWorld background, then VWorld
  imagery appears beneath local features; given no network/key, the same report still opens and
  all local table, summary, filter, sort, detail, and CSV functions remain usable with an explicit
  unavailable-background notice.~~
- **AC-HRA-011 (revised; Decision Log D-HRA-003):** Given a current QField project with a usable
  saved VWorld API key and network access, when the report opens, then VWorld imagery appears
  beneath local features and the UI discloses the active background and required attribution.
  Given no usable saved VWorld key and network access, when the report opens, then OpenStreetMap
  tiles are selected automatically and the UI discloses that fallback and its attribution. Given
  an unavailable selected service, the report attempts the other background when possible and
  discloses the result; given both services unavailable or no network, the report still opens and
  local feature layers, map controls, table, summary, filtering, sorting, detail, and CSV
  functions remain usable with an explicit offline-background notice. The VWorld API key is not
  displayed in the report UI; under Option 1 it may be present in exported tile-request data.

- **AC-HRA-012:** Given a report containing field values such as `<script>alert(1)</script>`, quotes,
  commas, and newlines, when it is opened and exported, then the values render as inert text and
  appear in the CSV as correctly escaped fields without executing or corrupting adjacent columns.

- ~~**AC-HRA-013 (original; superseded by Decision Log D-HRA-001):** Given a user who chooses a writable directory outside the project folder, when the user confirms HTML and CSV export, then both files are written to the selected location and the UI reports the exact paths; given cancellation, denial, or an invalid location, then no false-success message or silent project-folder fallback occurs.~~
- **AC-HRA-013 (revised; Decision Log D-HRA-001):** Given QField 4.2.4 and a writable current
  project folder, when the user confirms HTML and joined-CSV export, then both files are written in
  that project folder and the UI reports their exact paths. Given an unavailable or non-writable
  project folder, no false-success message or silent alternate-destination fallback occurs; an
  actionable write failure is reported and the in-memory report remains available.

- **AC-HRA-014:** Given an empty project, when the report is generated, then it contains valid empty
  map/table/summary states, zero-valued summary cards, and a valid header-only joined CSV.

- **AC-HRA-015:** Given a copied report opened without network access, when the user uses its local
  table, summary, filtering, sorting, detail, and CSV features, then they work without fetching
  remote scripts, stylesheets, fonts, or images. VWorld/OpenStreetMap backgrounds may be
  explicitly absent and the report must disclose the offline state.

- ~~**AC-HRA-016 (original; superseded by Decision Log D-HRA-001):** Given a target QField build where full-layer enumeration, VWorld tiles, or an external save-location picker is not exposed to project plugins, when implementation verification is performed, then the limitation is reported with the exact QField version/platform and no false claim of complete data, map, or outside-folder export support is made.~~
- **AC-HRA-016 (revised; Decision Log D-HRA-001):** Given target QField 4.2.4, when implementation
  verification is performed, then the report records the exact QField version/platform and
  explicitly reports the project-folder-only output boundary because no supported external
  save-location picker is exposed to project plugins. Any separate full-layer-enumeration or
  VWorld limitation is likewise reported, and no false claim of complete data, map, or
  outside-folder export support is made.

## 9. Open Questions

- **O-HRA-001:** Does “조사대상” intentionally mean the existing `site` layer displayed as
  `조사지`, or is a separate 조사대상 table/field intended? This determines the final join
  vocabulary and summary-card label.

- **O-HRA-002:** The existing standalone-report requirement forbids external images/resources,
  while VWorld background tiles are normally remote images. Should VWorld be an optional,
  network-dependent enhancement as specified here, or should the builder package an offline
  background/snapshot instead? This must be resolved before treating the VWorld part as fully
  conformant to FR-QPB-133.

- **O-HRA-003:** Should both Leaflet and D3 be mandatory in the generated document, or is Leaflet
  for the map plus a small embedded table/chart implementation sufficient? This affects bundle
  size, licensing notices, and implementation shape.

- ~~**O-HRA-004 (original; closed by Decision Log D-HRA-001):** Does the target QField version expose a supported user-facing file/directory save picker that permits project-plugin writes outside the project folder on iOS, Android, and the release-verification desktop platform? If not, the outside-folder requirement needs a separate QField-side API decision or a documented platform-specific limitation.~~
- **O-HRA-004 (closed; Decision Log D-HRA-001):** The target QField 4.2.4 runtime does not expose
  a supported project-plugin file/directory save picker or API for these report outputs outside
  the project folder. The stakeholder therefore selected the current project folder as the fixed
  destination for both the HTML report and joined CSV; no outside-folder implementation is claimed.

- **O-HRA-005:** Is the current report's exclusion of identification metadata still intended for
  this extension, while the three selected species fields are included for occurrence counts? If
  KTSN, identification status, confidence, or timestamps should also be visible in the joined
  table, that is a scope decision and must be added explicitly.

- **O-HRA-006:** What maximum project size/row count and interaction latency are acceptable on the
  release-verification QField devices? The implementation must not invent a truncation threshold;
  a measurable target is needed for performance acceptance.

- **O-HRA-007:** For observation-day cards, should the date come from `survey.survey_date`, an
  observation timestamp if one is later added, or the survey date inherited by each observation?
  This draft uses valid survey/observation dates according to the applicable schema and counts
  distinct calendar days, but the precedence should be confirmed.

## 10. Decision Log

- **D-HRA-001** (Category C; closes O-HRA-004; supersedes the outside-project save-location
  portions of FR-HRA-014, C-HRA-005, E-HRA-009, AC-HRA-013, and AC-HRA-016): The stakeholder
  explicitly directed that **HTML 리포트와 joined CSV는 현재 QField 프로젝트 폴더에 저장**. Both
  outputs therefore use the current QField project folder as their single supported destination;
  the UI reports the exact paths, and a project-folder write failure is an actionable failure with
  no false-success message or silent alternate destination. The prior requirement for a
  user-selectable writable location outside the project folder is retained above as superseded
  history, not deleted. This decision reflects the target QField **4.2.4** limitation: its
  project-plugin API exposes no supported user-facing file/directory picker or save-location API
  for these outputs outside the current project folder. Implementations and verification must
  report that compatibility boundary honestly and must not claim outside-project export support;
  the data/map limitations covered by AC-HRA-016 remain independently applicable.

- **D-HRA-002** (Category C; supersedes the species-key fallback portions of FR-HRA-012 and,
  before D-HRA-004, the corresponding total-species-card portions of FR-HRA-013, E-HRA-006, and
  AC-HRA-009/010): The stakeholder explicitly directed: “selected_korean_name과
  selected_scientific_name이 모두 비어 있고 selected_ktsn만 있는 관찰은 종 집계에서 없는
  케이스로 처리(미동정 종으로 별도 집계하지 않음).” Accordingly, for Types 1–3, an observation
  with both selected name fields empty and a non-empty `selected_ktsn` produces no species key and
  contributes neither to species occurrence counts/charts nor “미동정”; it remains available in
  joined report data and other applicable record/map/detail views. The prior fallback rule
  (selected Korean name, otherwise scientific name, otherwise “미동정” for every name-missing
  observation) is retained above as superseded history, not deleted; the revised rule keeps that
  “미동정” fallback only for records where all three selected species fields are empty. Type 4
  `dominant_species` remains separate from plant-observation counts. D-HRA-004 later supersedes
  only this decision's former exclusion of KTSN-only values from the Types 1–3 overview-card
  `총 종수`; it does not alter this species-key, chart, or “미동정” rule.

- **D-HRA-004** (2026-09-02, Category C; reconciles D-HRA-002 with D-IHRM-007; supersedes only
  the Types 1–3 overview-card total-species portions of revised FR-HRA-013, E-HRA-006,
  AC-HRA-009/010, and the corresponding wording in D-HRA-002): The stakeholder explicitly
  directed that Types 1–3 display `총 종수` as the distinct valid `selected_ktsn` count. The later
  card contract is therefore a direct-layer KTSN measure, not a species-occurrence aggregation:
  it reads Type 1 `inventory_observation.selected_ktsn` and Type 2/3
  `observation.selected_ktsn`, includes valid KTSN-only values, excludes and discloses only
  `null`, empty, or whitespace-only values, and is insulated from joined-row aliases and join
  fan-out. It preserves D-HRA-002's KTSN-only exclusion from species occurrence/chart grouping
  and “미동정”, preserves empty-versus-absent disclosure, and adds no Type 4 species card. The
  normative type mapping and detailed acceptance traceability are in
  `specs/html-report-integrated-data-map-summary-theme.md` §2.1–2.2, FR-IHRM-012–014, and
  AC-IHRM-008/009/013.

- **D-HRA-003** (Category C; supersedes the VWorld-only/unavailable-background behavior in
  FR-HRA-004, FR-HRA-015, FR-HRA-017, C-HRA-004, C-HRA-008, E-HRA-008, AC-HRA-011, and
  AC-HRA-015): The stakeholder explicitly directed: “사용하는 프로젝트에 VWorld API key가
  저장된 경우 그걸 이용하고 없는 경우에는 오픈스트리트맵을 이용.” The report therefore
  reads the current QField project's saved VWorld API-key configuration: a usable key selects
  VWorld first, while a missing or unusable key selects
  OpenStreetMap automatically. The key is not displayed in the report UI; Option 1 accepts that
  standalone HTML tile-request data may contain the key. If the selected service cannot be reached, the report may try the
  alternate background; if neither remote service is available, local feature/map/table/detail/
  summary/filter/sort/CSV functions remain usable with a clearly disclosed offline state. Active
  background, fallback/offline status, and the applicable VWorld/OpenStreetMap attribution must
  be visible in the report. This decision changes only background selection and failure disclosure;
  joined-data, geometry, and standalone-local-report contracts are unchanged. The prior behavior
  that treated VWorld as the sole optional background and merely labeled it unavailable is
  retained above as superseded history, not deleted.

- **D-HRA-005** (2026-09-03, Category C — stakeholder-approved mapped-feature popup change):
  The stakeholder explicitly directed: **“only one popup should appear next to the clicked
  feature; remove the duplicate right-side custom detail panel for feature clicks”**;
  **“observation-feature popup should display only 조사일, 조사자, 국명, 학명”**; and **“when the
  clicked feature is a site/조사지, display only the site name.”** The stakeholder further directed
  that **“Leaflet feature click and keyboard activation, readable escaped content, map geometry,
  and no permanent labels”** be preserved. This supersedes only the feature-click detail-content
  and duplicate-panel portions of FR-HRA-005 and AC-HRA-003: a pointer click or existing keyboard
  activation now opens exactly one transient Leaflet popup adjacent to the clicked feature, with
  only the specified observation fields or site name. The prior UUID, layer-name, and joined-parent
  detail requirement is retained above as superseded history, not deleted. The change is
  display-only: source records, joins, identifiers, geometry/CRS, table rows, summaries, and CSV
  output are unaffected. Downstream acceptance-test and traceability updates are intentionally
  deferred to the separate test-designer approval gate; no test file is changed by this artifact.
