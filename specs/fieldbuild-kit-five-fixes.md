# Feature: FieldBuild Kit — five-fix integration

> Status: DRAFT
> Owner: spec-writer
> Last updated: 2026-09-06
> Scope: corrective release specification; application code and acceptance tests are not part of this artifact

## 1. Summary

This specification integrates five user-reported defects in the FieldBuild Kit wizard,
offline-basemap build, QField photo-identification workflow, and generated HTML report.
It defines the observable behavior required for a correction release while preserving the
existing survey schemas, project format, local-first data model, and report contracts.

This draft also records a stakeholder-approved clarification for offline-map download: MBTiles
generation is working, but the user must be able to choose which currently supported offline
map source/layer is downloaded before the operation starts.

The screenshots supplied with the request are UI-defect evidence, not normative layout
specifications. `/Users/tory/Downloads/test2_report.html` is a generated report artifact used as
diagnostic evidence; the normative report behavior is defined here and in the referenced report
specification.

This draft also records stakeholder-approved display-expression changes. For linked plant
observations shown from a Type 2 or Type 3 survey's Related records, the observation display
expression must use the exact requested Korean-name/scientific-name/coverage format. For the
survey layer present in Types 2–4, the display expression must distinguish records by date plus
surveyor. Existing child-record opening/editing behavior remains unchanged.

This revision also records a stakeholder-approved change to the photo-identification location
source. Location-dependent identification work must use the current survey/plot geometry already
defined by the selected survey type; it must not read GPS or any other location from photo EXIF or
image metadata. The original photo attachment and the existing identification request/candidate
workflow remain in scope.

## 2. Functional Requirements

- **FR-FIX-001 (top branding):** On every FieldBuild Kit wizard page, the full FieldBuild Kit
  logo is displayed at the top of the page content, before the page's step explanation/title or
  instructional copy. The logo must remain visible and must not be replaced by a platform-default
  wizard watermark, side banner, or icon-only mark.

- **FR-FIX-002 (MBTiles operation lifecycle):** An offline MBTiles build must not fail with a
  premature operation-timeout error while tile acquisition or MBTiles writing is still making
  forward progress. The operation timeout policy must accommodate the estimated work for the
  selected extent/zoom range and the existing output-size guard; per-request network timeouts,
  cancellation, and provider errors remain bounded and actionable. A timeout or cancellation must
  leave no partial deliverable and must identify the failed operation and recovery action.

- **FR-FIX-003 (saved related-record write-back):** In QField, when a user opens a plant
  observation through Survey → Related records → plant observation, runs photo plant
  identification, and selects a candidate, the selected Korean name, scientific name, and KTSN
  are applied to that currently edited observation and persist through the normal save/reopen
  cycle. The target is the child observation feature, not the parent survey, a sibling, or a
  feature-list model.

- **FR-FIX-004 (main-screen plugin labels):** The main screen's top-right labels for the “Ex...”
  plugin and the photo-identification plugin must render their complete intended labels without
  clipping or ellipsis at the supported application window sizes. Labels must remain distinguishable
  and usable at the minimum supported size and on the supported platform font metrics.

- **FR-FIX-005 (HTML report integrity and export):** Every generated HTML report must be a
  structurally valid standalone document whose map, joined table, and CSV-download control are
  present inside the document body, initialized exactly once after their target elements exist,
  and usable when opened. The report must preserve the existing interactive map/table behavior,
  and activating CSV download must produce the joined CSV for the explicitly selected all-rows or
  filtered-rows scope, including UTF-8 Korean text and correct CSV quoting.

- **FR-FIX-006 (offline source/layer selection):** Before an offline MBTiles download can start,
  the UI must resolve and display the currently supported offline map choices and require one
  selected source/layer for this download. The offline selector must use the same UI/control
  pattern and the same layer-type choices as the existing online-map layer selector: reuse its
  labels, options, and selection semantics rather than inventing a separate offline selector or
  different layer taxonomy. The current supported catalog is the VWorld provider with the
  capability-advertised layers `Base`, `White`, `Midnight`, `Hybrid`, and `Satellite` (or the
  supported subset currently advertised by VWorld); OpenStreetMap is not an offline-download
  choice because it is only the existing drawing-canvas visual aid. When more than one choice is
  available, the user must explicitly choose exactly one; no provider or layer may be silently
  substituted. When exactly one choice is available, it may be visibly preselected, but the
  resolved choice must still be shown and carried into the download request. The selected layer
  is the layer whose tiles are downloaded into the MBTiles file.

- **FR-FIX-007 (selected-source identity):** The selected offline source/layer must be visible in
  the offline review/progress/completion UI and must be recorded in the completed MBTiles output's
  non-secret metadata, including a stable provider identifier (`VWorld`) and the exact selected
  layer identifier. The generated project's offline basemap reference must continue to point to
  the local completed MBTiles file, and its visible basemap layer/metadata must identify the same
  selected source/layer. The API key must not be included in this identity metadata.

- **FR-FIX-008 (exact Related-records plant-observation display expression):** For Type 2
  (`temporary_plots`) and Type 3 (`permanent_plots`), the `observation` layer reached from a
  survey through the existing `rel_observation_survey` relation (confirmed human-facing relation
  name `식물관찰`) must use exactly this QGIS display expression; the relation row must therefore
  show the expression's result:

  ```qgis
  concat(
    coalesce(selected_korean_name, selected_scientific_name, '미입력'),
    '(', coalesce(to_string(cover), '미입력'), '%)'
  )
  ```

  The preferred label is `selected_korean_name`, then `selected_scientific_name`, then `미입력`,
  followed immediately by coverage in parentheses and a percent sign (for example,
  `상사화(35%)`). The expression's field names, function calls, literals, and concatenation
  structure are normative; the source-level aliases remain `selected_korean_name` → `국명`,
  `selected_scientific_name` → `학명`, and `cover` → `피도`. Each linked observation gets its own
  label in the existing relation order; rows must not be collapsed, aggregated, or reduced. The
  existing action for opening the linked child record must remain available, and the opened child
  must remain the same editable observation feature governed by FR-FIX-003 and the saved-feature
  relation contract.

- **FR-FIX-009 (exact survey display expression):** For the `survey` layer in Type 2
  (`temporary_plots`), Type 3 (`permanent_plots`), and Type 4 (`vegetation_mapping`), the layer
  display expression must be exactly:

  ```qgis
  concat(survey_date, ' ', surveyor)
  ```

  This replaces `coalesce(surveyor, survey_date, 'Survey')` and distinguishes survey records by
  the date followed by a space and the surveyor. Type 1 (`simple_inventory`) has no `survey`
  layer and is not in scope for this requirement.

- **FR-FIX-010 (authoritative photo-identification location source and precedence):** When the
  existing photo-identification button is clicked, every location-dependent part of the existing
  identification workflow (including occurrence-probability/enrichment lookup) must resolve its
  location from the authoritative geometry for the current survey type, using this exact
  precedence and no cross-type fallback. Photo submission, candidate identification, and the
  selected Korean/scientific name and KTSN write-back are a separate identification path: they
  must not be blocked solely because the authoritative location is absent or invalid, and must
  continue as far as the existing workflow allows:

  | Survey type | Identification target | Authoritative location resolution |
  |---|---|---|
  | Type 1 — `simple_inventory` | current `inventory_observation` feature | the current feature's `geom` Point (EPSG:4326) |
  | Type 2 — `temporary_plots` | current `observation` feature | current `observation.survey_id` → `survey.survey_id`, then the related `survey.plot_geom` Point (EPSG:4326) |
  | Type 3 — `permanent_plots` | current `observation` feature | current `observation.survey_id` → `survey.survey_id` → `survey.plot_id` → `plot.plot_id`, then the related `plot.plot_geom` Point (EPSG:4326) |
  | Type 4 — `vegetation_mapping` | no identification target/button | no photo-identification location resolution; the existing `community` layer remains outside this workflow |

  The workflow must not read, parse, or use GPS EXIF or any other image metadata as a location
  source, and must not substitute device GPS, site geometry/centroids, a different survey/plot,
  attachment metadata, or a provider-invented location. When the authoritative location is
  absent or invalid, the location-derived occurrence-probability calculation must be skipped and
  must not be replaced with a numeric zero or another inferred value; the existing unavailable/no-
  probability-data state remains the location-path result. The photo-identification request,
  candidate result, explicit selection, and selected-name/KTSN write-back continue as far as the
  existing workflow allows. When the authoritative location is usable, occurrence probability
  may be calculated from that geometry under the existing enrichment contract. Original
  attachment files and their stored paths/bytes must remain intact; any existing temporary
  upload-copy handling remains governed by the existing identification contract.

## 3. Constraints

- **C-FIX-001:** This specification extends, and does not silently replace, the integrated MVP
  specification `specs/qfield-project-builder.md` and the dedicated specifications named in
  Section 10.

- **C-FIX-002:** No survey schema, relation cardinality, UUID, foreign-key value, attachment
  path, identification candidate-resolution rule, or report data model may be changed solely to
  mask one of these defects.

- **C-FIX-003:** MBTiles generation remains subject to the existing hard output-size limit and
  cleanup-on-cancel/error behavior. A larger operation budget must not permit an output larger than
  the existing limit or an incomplete MBTiles file to be published.

- **C-FIX-004:** Report map backgrounds remain optional network enhancements. Loss of VWorld or
  OpenStreetMap tiles must not prevent local map features, tables, summaries, filtering, sorting,
  detail views, or CSV construction from working.

- **C-FIX-005:** Photo identification continues to use the generated project plugin and embedded
  QML widget architecture established by Decision Log D-31; QGIS Desktop rendering limitations
  and QField platform boundaries remain disclosed as specified by the existing identification
  requirements.

- **C-FIX-006:** Offline source selection is additive to the existing VWorld MBTiles pipeline. It
  must not relax the 900 MiB pre-generation threshold, 1 GiB hard output limit, bounded request
  and operation-timeout behavior, explicit cancellation, provider/size failure handling, or
  cleanup of incomplete output. A failed or cancelled selection/download still publishes no
  partial deliverable.

- **C-FIX-007:** This clarification preserves the existing offline project-reference behavior:
  the generated project uses a relative path to the completed local `.mbtiles` file only; the
  VWorld API key remains transient to tile retrieval and is not written to the generated project,
  MBTiles metadata, manifest, validation report, or transfer folder. It does not add a new
  provider, permit an OpenStreetMap offline package, or require merging multiple sources into one
  MBTiles file.

- **C-FIX-008:** The offline source/layer selector must mirror the existing online-map layer
  selector's control behavior and supported layer-type vocabulary. This is a reuse/consistency
  requirement, not permission to create an offline-only option or to expand the supported provider
  set.

- **C-FIX-009:** FR-FIX-008 and FR-FIX-009 are display-only corrections. They must use the
  existing fields, relation ID/name convention, relation cardinality, UUIDs, foreign keys, and
  child-form navigation. They must not add a field, change a field alias, change a relation
  definition, reorder linked records, or replace the existing child-record open/edit action.

- **C-FIX-010:** The two requested expressions are literal QGIS-expression contracts. No
  `trim()`, `nullif()`, extra fallback label, alias substitution, prefix/suffix wording, or other
  preprocessing may be added in a way that changes either expression. NULL and blank-value
  behavior is addressed only in the edge cases below and must not silently rewrite the expressions.

- **C-FIX-011:** FR-FIX-010 must use only the existing schema fields, geometry columns, foreign-key
  relations, and survey-type set. It must not add a location field, alter a geometry field or CRS,
  change relation cardinality/identity, introduce a new survey type, or add a new identification
  provider or location service.

- **C-FIX-012:** Photo EXIF and image metadata are not an authoritative or trusted location source.
  The implementation must not extract, persist, log, or send a separate location value derived
  from them. Existing photo bytes may continue to be submitted to the existing identification
  provider under the existing disclosure and request contract; this requirement does not authorize
  rewriting or deleting the original attachment to sanitize metadata.

- **C-FIX-013:** A location is usable only when the required current-feature identity and relation
  chain resolve to one matching geometry of the authoritative field/type, with finite coordinates
  in the geometry's existing CRS. Location-derived occurrence probability may be calculated only
  from such a usable geometry. Missing, ambiguous, mismatched, empty, or invalid geometry must
  fail closed for that probability calculation, must not be replaced by a less authoritative
  source, and must not block the location-independent photo-identification request, candidate
  selection, or selected-name/KTSN write-back when the existing workflow otherwise permits them.

## 4. Assumptions

- **A-FIX-001:** “Fieldbuild kit logo” means the full supplied FieldBuild Kit logo asset, not the
  square icon mark alone.

- **A-FIX-002:** The MBTiles defect is an operation-level timeout/lifecycle defect, not a request
  to remove cancellation, provider-error reporting, or the existing 1 GiB output discipline.

- **A-FIX-003:** “Photo plant identification write-back” means the three selected identity fields
  already defined by the saved-feature identification specification; candidate scoring, timestamp,
  model version, and probability metadata follow that specification when available.

- **A-FIX-004:** “Complete labels” means the current product labels represented by the Ex... and
  photo-identification plugin actions; the fix must not rename or remove either plugin.

- **A-FIX-005:** The existing FR-QPB-071 VWorld capabilities-discovery contract remains the
  authority for which VWorld layers are available at a given time. The current known choices are
  `Base`, `White`, `Midnight`, `Hybrid`, and `Satellite`; this clarification does not invent or
  imply support for another provider. The OSM tiles used by the drawing canvas remain outside the
  offline MBTiles pipeline.

- **A-FIX-006:** For FR-FIX-008, `selected_korean_name`, `selected_scientific_name`, and `cover`
  are the authoritative Type 2/3 child fields, with source-level aliases `국명`, `학명`, and
  `피도`; `cover` retains its existing required integer 0–100 meaning. The exact expression is
  the stakeholder-approved label contract, so the prior `국명`/`피도값` prefixed wording is not
  retained as the current display format.

- **A-FIX-007:** The survey display-expression requirement applies only to the survey tables
  actually present in Types 2–4. Type 2 permits a nullable `survey_date` and optional non-blank
  `surveyor` for seed-survey compatibility; Type 3 and Type 4 require non-blank `surveyor` and
  Type 3/4 `survey_date` is required. The exact expression intentionally supplies no `Survey`
  fallback.

- **A-FIX-008:** The supported survey types remain exactly the four schema keys
  `simple_inventory` (Type 1), `temporary_plots` (Type 2), `permanent_plots` (Type 3), and
  `vegetation_mapping` (Type 4). The existing identification target/button is present only on
  Type 1's `inventory_observation` and Type 2/3's `observation`; Type 4's `community` has no such
  button.

- **A-FIX-009:** The authoritative geometry definitions are the existing EPSG:4326 fields in the
  generated schema: Type 1 `inventory_observation.geom`, Type 2 `survey.plot_geom`, and Type 3
  `plot.plot_geom`. Type 2 `observation` and Type 3 `survey` have no geometry of their own, so
  their existing foreign-key chains are required to reach the location.

- **A-FIX-010:** “Location” in FR-FIX-010 means the coordinate context used by the existing
  location-dependent occurrence-probability/enrichment path. It does not authorize adding a
  coordinate field to the Pl@ntNet request or changing the existing provider endpoint/request
  shape. If no usable authoritative geometry exists, the location-independent photo-
  identification request must still proceed under the existing workflow, including candidate
  result and selected Korean/scientific name and KTSN write-back as far as that workflow allows,
  while occurrence probability is not calculated and the location-dependent path reports its
  existing unavailable/no-probability-data state.

## 5. Edge Cases

- **E-FIX-001:** A wizard page has little vertical space or a long explanation. The logo remains
  above the explanation without overlapping controls; the page remains navigable.

- **E-FIX-002:** An MBTiles operation is slow but still progressing, a tile request is slow, the
  provider returns an error, the user cancels, or the estimated output crosses the hard limit.
  These outcomes must be distinguishable; only a successful completed build may publish the
  final file.

- **E-FIX-003:** The related-record child form is not mounted yet, its UUID does not match the
  identification request, or the child save fails. No other feature is updated, no false success
  is shown, and the request remains diagnosable or a clear non-success is reported.

- **E-FIX-004:** A label is long, localized, or rendered with a wider supported font. The action
  remains readable and accessible at the supported minimum window size; truncation is not used as
  the normal solution.

- **E-FIX-005:** A report has no records, missing/invalid geometry, no network, filtered rows, or
  field values containing commas, quotes, newlines, Korean text, or HTML-looking strings. Empty
  states and limitations remain explicit, values remain inert, and CSV output remains valid.

- **E-FIX-006:** The effective offline catalog may contain several supported VWorld layers, one
  supported layer, or no usable supported layer. Several require an explicit single choice; one
  may be shown as the only resolved choice; no usable choice must block offline download with a
  clear actionable message and must not silently fall back to an unsupported provider or layer.

- **E-FIX-008:** The online and offline selectors must expose the same labels/options and equivalent
  single-selection behavior. A difference between the two selectors is a specification failure,
  not a reason to add a new offline-only map choice.

- **E-FIX-007:** If the supported catalog changes after the user selected a layer, the stale choice
  must be invalidated or revalidated before download; a completed output must never claim a
  different source/layer from the one actually downloaded.

- **E-FIX-009:** FR-FIX-008's exact expression handles NULL name values by trying
  `selected_korean_name`, then `selected_scientific_name`, then `미입력`; a NULL `cover` is shown
  as `미입력`, while a stored coverage value of `0` remains `0`. The expression does not contain
  blank-string or whitespace normalization: empty/whitespace-only stored text is evaluated by
  QGIS according to the exact expression, and no `trim()`/`nullif()` behavior may be added
  silently. If only one name field is NULL, the other available name remains the preferred label.

- **E-FIX-010:** If a survey has multiple linked plant observations, every linked observation must
  have its own combined `국명`/`피도값` label, including observations with different, duplicate, or
  partially missing values. The existing relation order is retained; no first-row-only display,
  deduplication, summary, or silent omission is permitted. If there are no linked observations,
  the existing empty Related-records state remains unchanged.

- **E-FIX-011:** Selecting, tapping, or otherwise using the existing action on a Related-records
  entry must still open that entry's child observation form for inspection and editing. The new
  label must not turn the row into a non-interactive summary, open the parent survey instead, or
  cause edits to a sibling observation; normal save/reopen behavior remains governed by the
  existing child-record contract.

- **E-FIX-012:** For FR-FIX-009, the exact expression is used even when Type 2 seed-survey data
  contains a NULL/blank date or optional surveyor. QGIS evaluates the expression as written; the
  implementation must not restore the old `Survey` fallback or silently reorder the two fields.
  Type 3 and Type 4's schema constraints normally prevent blank required values, but their
  display expression remains the same exact expression.

- **E-FIX-013:** The current feature has no attachment, or an attachment cannot be read. Existing
  photo-identification behavior remains responsible for reporting that condition; no EXIF/GPS
  fallback is attempted. If photo bytes are otherwise available but location geometry is not,
  the photo-identification request and candidate flow continue as far as the existing workflow
  allows, while location-derived occurrence probability is not calculated, reports the existing
  no-location/no-probability-data state, and never displays a numeric zero.

- **E-FIX-014:** The authoritative geometry is NULL, empty, invalid, the wrong geometry type,
  non-finite, outside valid coordinate bounds, or cannot be reached through the required current
  feature UUID/foreign-key chain. The location-dependent operation must fail closed for location:
  it must not use EXIF, other image metadata, device GPS, site geometry, a centroid, a stale
  related record, or a different record as a substitute. Only the location-derived occurrence-
  probability calculation is skipped, and the user receives a clear unavailable/no-probability-
  data result consistent with the existing workflow while the photo-identification request
  continues normally as far as existing photo/provider conditions allow.

- **E-FIX-015:** A Type 3 observation has a missing, ambiguous, or mismatched `survey_id`/`plot_id`
  relation, or the resolved plot has missing/invalid `plot_geom`. The Type 3 plot chain is treated
  as unresolved for location-derived occurrence probability; the Type 3 button does not silently
  fall back to the survey, site, observation, or photo location, and the photo-identification
  request continues as far as the existing workflow allows.

- **E-FIX-016:** A photo contains valid EXIF GPS, conflicting EXIF GPS, or other embedded location
  metadata that differs from the survey/plot geometry. The metadata is ignored as location input;
  the authoritative geometry remains the only eligible location source. The original attachment
  bytes/path remain unchanged, and the existing photo submission and candidate-selection workflow
  remains available.

- **E-FIX-017:** Identification is disabled or the current layer is outside the existing
  identification target set. No identification button is added and no new location resolution is
  attempted; Type 4 remains outside this workflow.

## 6. Out of Scope

- Redesigning the overall wizard, changing the supplied brand identity, or changing plugin names.
- Replacing the MBTiles provider, changing the survey layer schema, or removing offline-size limits.
- Adding new identification providers, changing accepted-name/KTSN resolution, or migrating old
  generated projects.
- Adding a new location schema, device-GPS/manual-coordinate fallback, image-metadata service,
  photo-metadata sanitization feature, or provider/location parameter not already present in the
  existing identification contract.
- Replacing the standalone report with a server-rendered application or requiring remote scripts.
- Changing the report's project-folder output boundary or adding upload/synchronization behavior.
- Any application-code or test-file change as part of this spec-writing artifact.

## 7. Acceptance Criteria

- **AC-FIX-001:** Given each supported FieldBuild Kit wizard page, when the page is rendered at
  the supported minimum window size, then the full logo is visible at the top of the page content,
  above the step explanation/title and instructional copy, with no overlap, clipping, or platform
  default watermark replacing it.

- **AC-FIX-002:** Given an offline-basemap request within the existing supported extent/zoom and
  output-size limits, when tile acquisition and MBTiles writing continue making progress beyond
  the former premature timeout boundary, then the build remains active until completion or an
  explicit user cancellation/provider failure/size-limit failure, and a valid final MBTiles file
  is published only after successful completion. Given cancellation, timeout, provider failure,
  or size-limit failure, then no partial MBTiles deliverable remains and the UI reports the
  specific outcome with an actionable next step.

- **AC-FIX-003:** Given a saved Type 3 project and a plant observation opened through
  `조사지 → 조사 → 식물관찰` / Related records, when the user runs photo identification and selects
  a candidate, then the open child form shows the candidate's Korean name, scientific name, and
  KTSN; after normal save and reopen, those same values are persisted on that child observation,
  its UUID and `survey_id` are unchanged, and its parent/sibling records are unchanged.

- **AC-FIX-004:** Given the main screen at the supported minimum window size and supported
  platform font metrics, when the top-right plugin actions are rendered, then both the Ex... action
  label and the photo-identification action label are fully readable, not clipped or ellipsized,
  and remain separately actionable. The same remains true after resizing within the supported
  window range and under Korean localization.

- **AC-FIX-005:** Given a generated report containing at least one valid geometry, joined rows,
  Korean/non-ASCII values, and a filterable field, when the report is opened in a supported
  browser, then the document parses as valid HTML, the map renders once with local features,
  the joined table renders once with its rows, and the CSV control is visible and clickable inside
  the document body. After filtering and choosing the filtered/all-rows option, activating the
  control produces a UTF-8 joined CSV containing exactly the selected rows, stable headers, and
  correctly quoted values. Given no network or no valid geometry, the report still renders its
  local table and explicit map/offline state and the CSV control remains usable.

- **AC-FIX-006:** Given offline mode and an effective supported catalog containing the current
  VWorld choices (or a capability-advertised subset), when the user reaches offline download
  review, then the UI presents the provider/layer choice before download using the same control
  pattern, labels/options, and selection semantics as the existing online-map layer selector.
  When at least two choices are available, download cannot start until exactly one is explicitly
  selected; it must not silently use `Base` or another default. When exactly one choice is
  available, that choice is visibly resolved and included in the request. The selected layer is
  the layer actually used for MBTiles acquisition. OpenStreetMap is not listed as an offline
  choice.

- **AC-FIX-007:** Given a valid selected VWorld layer and an offline build within the existing
  extent/zoom and size limits, when the build is reviewed, downloaded, completed, and opened,
  then the selected provider/layer is shown in the offline UI, recorded in non-secret MBTiles
  metadata, and identifiable in the generated project's offline basemap layer/metadata. The
  output references the local `.mbtiles` file relatively, contains no API key, and the source/layer
  identity matches the tiles that were downloaded.

- **AC-FIX-008:** Given offline mode with no usable supported source/layer after the existing
  VWorld availability/discovery rules are applied, when the user attempts to continue, then the
  UI blocks the download and reports that no supported offline map is available with an actionable
  recovery instruction. No MBTiles file is published, no unsupported provider/layer is substituted,
  and the existing size-estimate, timeout/cancellation, and cleanup behavior remains unchanged.

- **AC-FIX-009:** Given a Type 2 or Type 3 project with one linked `observation` under a `survey`,
  when the survey's `Related records` surface is inspected, then the observation layer's display
  expression is exactly the FR-FIX-008 expression and the `식물관찰` entry evaluates to
  `상사화(35%)` for `selected_korean_name = 상사화`, `selected_scientific_name = 상사화`, and
  `cover = 35`, rather than the prior `국명`/`피도값` prefixed wording.

- **AC-FIX-010:** Given a Type 2 or Type 3 survey with multiple linked observations, when its
  Related records are inspected, then every linked observation appears exactly once and each row
  displays its own result from the exact FR-FIX-008 expression in the existing relation order,
  including rows whose values are duplicates or differ from neighboring rows. No row is collapsed
  into a survey-level summary and no linked observation is omitted.

- **AC-FIX-011:** Given linked observations covering the relevant NULL-value combinations, when
  Related records are inspected, then the exact FR-FIX-008 expression renders a NULL Korean name
  by falling back to the scientific name and renders both names NULL as `미입력`; NULL `cover`
  renders as `미입력`, and `cover = 0` renders as `0`. The resulting labels contain no added
  `국명:` or `피도값:` prefixes. Empty/whitespace-only strings are not reinterpreted beyond the
  exact expression's QGIS semantics. With no linked observations, the existing empty state
  remains unchanged.

- **AC-FIX-012:** Given a linked observation displayed under `식물관찰`, when the user uses the
  existing entry action to open it, edits the child record, saves normally, and reopens it, then
  the same child observation form is opened and remains editable, its UUID and `survey_id` are
  unchanged, and no parent or sibling record is modified. The combined Related-records label
  reflects the saved child values after the normal refresh/reopen cycle.

- **AC-FIX-013:** Given a Type 2, Type 3, or Type 4 generated project, when the `survey` layer's
  display expression is inspected, then it is exactly `concat(survey_date, ' ', surveyor)` and
  not `coalesce(surveyor, survey_date, 'Survey')`. Type 1 has no `survey` layer and is excluded.
  Given a Type 2 seed survey with a nullable/blank value, the expression remains unchanged and
  is evaluated according to QGIS semantics without an added fallback label.

- **AC-FIX-014:** Given identification is enabled and a valid current feature is opened, when the
  photo-identification button is clicked with a photo whose embedded GPS differs from the domain
  geometry, then the location context used by the location-dependent identification path is,
  respectively: Type 1 `inventory_observation.geom`; Type 2 the `survey.plot_geom` reached by the
  current observation's `survey_id`; and Type 3 the `plot.plot_geom` reached by the current
  observation's `survey_id` then the survey's `plot_id`. The result uses no photo EXIF/image
  metadata, device GPS, or alternate provider, and Type 4 has no identification button/location
  path.

- **AC-FIX-015:** Given a Type 1/2/3 identification target with missing, ambiguous, mismatched,
  empty, invalid, wrong-type, non-finite, or out-of-bounds authoritative geometry, when the user
  clicks the photo-identification button, then no EXIF/image-metadata/device/site/centroid fallback
  is used, no location value is sent or persisted for the location-dependent path, and the
  location-derived occurrence-probability calculation is skipped. The photo-identification
  request continues normally as far as the existing workflow allows: with valid photo bytes and
  existing provider conditions, it produces the candidate result, supports explicit selection,
  and performs the selected Korean/scientific name and KTSN write-back under the existing save
  contract. The user receives the existing unavailable/no-probability-data outcome for the
  location path, never numeric zero, and the missing/invalid location does not by itself block
  identification.

- **AC-FIX-016:** Given an enabled generated Type 1, Type 2, or Type 3 project and an attached photo
  containing GPS EXIF or other location metadata, when the button is clicked and the identification
  flow completes, then inspection shows no EXIF/image-metadata location extraction or derived
  location field in the request/context, the authoritative geometry is the only location source,
  and the original attachment path and bytes are unchanged. Existing photo bytes/attachments,
  candidate selection, and save/reopen write-back behavior remain available under their existing
  contracts.

- **AC-FIX-017:** Given QField 4.2.11 and a new daughter feature added through an existing parent
  feature's Related records workflow, when the daughter is saved successfully and the user returns
  to that immediate parent, then the parent Related records list shows that daughter exactly once
  using the existing relation display. After navigating away and reopening the parent and its
  Related records, the same GeoPackage-backed daughter remains present exactly once; no duplicate,
  transient-only row, or unrelated child is shown.

## 8. Compatibility and Scope Notes

- This is a corrective overlay for existing contracts, not a new survey type or data migration.
- Existing requirements for branding/window identity (FR-QPB-131/132), offline MBTiles
  generation and cleanup (FR-QPB-083/084 and related DR-QPB-060/061), project-plugin/photo
  identification and write-back (FR-QPB-100/101/109, Decision Logs D-31 and D-92), and report
  export/analytics (FR-QPB-133/134 and `specs/html-report-interactive-analytics.md`) remain in
  force unless this document states a narrower defect correction.
- The saved related-record path is governed in detail by
  `specs/saved-feature-identification-edit.md` (FR-SFE-001/002 and AC-SFE-001/002). Its
  fail-closed UUID and active-form safeguards remain mandatory.
- The report artifact's observed malformed placement of controls after `</html>` and duplicated
  initialization fragments are evidence motivating AC-FIX-005; they are not themselves an
  implementation prescription beyond the observable document and runtime contract.
- The current identification implementation's EXIF behavior is superseded for this corrective
  release by FR-FIX-010: the existing first-photo EXIF-GPS read used by probability enrichment is
  no longer an allowed location source. The existing button, photo-byte handling, provider,
  candidate/KTSN flow, and write-back contract remain otherwise in force.
- Existing generated projects without the corrected plugin/report are not retroactively migrated;
  newly generated projects and newly exported reports must satisfy this specification.

## 9. Decision Log

- **D-FIX-001** (2026-08-31, Category A/B): Integrate the five reported corrections in one
  Draft specification. The supplied screenshots and generated report are evidence, while the
  acceptance criteria in this document are authoritative. This decision adds no new product
  capability beyond restoring the referenced contracts.

- **D-FIX-002** (2026-08-31, Category B): Treat operation timeout as a lifecycle defect: active
  progress, cancellation, provider failure, and output-size failure must be distinguishable, and
  a fixed premature wall-clock cutoff must not terminate a progressing supported build. Existing
  per-request bounds and cleanup obligations remain.

- **D-FIX-003** (2026-08-31, Category B): Treat the Related records path as an existing-feature
  edit covered by the saved-feature identification contract, not as a new observation creation
  flow. The child observation UUID is the write-back identity.

- **D-FIX-004** (2026-08-31, Category B): Treat report map/table/CSV failures as one standalone
  report-integrity correction. The report must retain offline-safe local functionality and the
  existing project-folder save boundary.

- **D-FIX-005** (2026-08-31, Category C — stakeholder-approved product change/clarification):
  The stakeholder explicitly reported: **“MBTiles 다운로드되는 것 다시 확인하였음. 그런데 오프라인
  지도 다운로드 시 어떤 지도를 받을지 선택하는 게 없음.”** (“I checked again that MBTiles
  downloads work. However, when downloading an offline map, there is no choice of which map to
  receive.”) This supersedes any implicit assumption that the offline pipeline may silently use
  one default map/layer at download time; it does not supersede the working MBTiles pipeline or
  any prior lifecycle, size, timeout, cancellation, cleanup, licensing, or offline-reference
  requirement. Each new offline download must resolve one supported source/layer, with an explicit
  single choice when multiple supported VWorld layers are available, visible resolution when only
  one is available, and a blocked/actionable no-source state when none is available. The currently
  supported choices remain VWorld's capability-advertised layers `Base`, `White`, `Midnight`,
  `Hybrid`, and `Satellite`; the existing OpenStreetMap drawing-canvas visual aid is not promoted
  into an offline provider. The selected identity must be reflected in UI and non-secret output
  metadata, while the generated project continues to reference only the local relative MBTiles
  file and never the VWorld API key. Existing Decision Log entries D-FIX-001 through D-FIX-004
  remain intact and are not erased or renumbered by this clarification.

- **D-FIX-006** (2026-08-31, Category C — stakeholder-approved clarification): The stakeholder
  explicitly added: **“offline map selection must use the same UI/control pattern and the same
  layer-type choices as the existing online-map layer selection. Update the Draft spec to say the
  offline download source/layer selector mirrors the online map layer-type selector, reusing its
  labels/options/selection semantics; selected layer is the one used for MBTiles. Do not invent a
  different selector.”** Accordingly, FR-FIX-006/AC-FIX-006 require the offline selector to be
  the online layer-type selector's equivalent reuse, including its labels, options, and
  single-selection behavior. The chosen layer is the actual MBTiles tile source. This clarification
  changes neither the current supported VWorld layer catalog nor the explicit exclusion of the OSM
  drawing-canvas visual aid, and it leaves all existing MBTiles size, timeout, cancellation,
  cleanup, relative-reference, and API-key handling requirements in force. No prior decision-log
  entry is deleted, reworded, or renumbered.

- **D-FIX-007** (2026-08-31, Category C — stakeholder-approved Related-records display change):
  The stakeholder explicitly requested that, when linked plant observations are inspected from a
  survey layer's `Related records`, each linked entry show the Korean common name (`국명`) and
  coverage value (`피도값`) together. The attached `/Users/tory/Downloads/IMG_9808.jpg` is
  non-normative evidence of the current behavior, where the entry shows only `상사화`; it is not a
  layout or implementation instruction. Based on the authoritative existing conventions, the
  child is the `observation` table reached through stable relation ID `rel_observation_survey`,
  whose confirmed relation display name is `식물관찰`; the source fields are
  `selected_korean_name` (alias `국명`) and `cover` (alias `피도`). The required combined display
  is therefore `국명: <value> · 피도값: <value>`, with `미입력` for NULL/blank values and `0`
  preserved as a real coverage value. This adds no schema or relation change, preserves the
  existing relation order and one-row-per-child behavior, and explicitly preserves the existing
  action for opening and editing the child observation. No prior decision-log entry is deleted,
  reworded, or renumbered.

- **D-FIX-008** (2026-08-31, Category C — stakeholder-approved product change): The stakeholder
  explicitly superseded the draft's prior Related-records display wording and directed that the
  linked plant-observation entries use exactly:

  ```qgis
  concat(
    coalesce(selected_korean_name, selected_scientific_name, '미입력'),
    '(', coalesce(to_string(cover), '미입력'), '%)'
  )
  ```

  This changes the current label result to Korean name, then scientific name, then `미입력`,
  immediately followed by `(coverage%)` (for example `상사화(35%)`), and supersedes only
  D-FIX-007's prior `국명: ... · 피도값: ...` display wording. D-FIX-007's relation scope,
  one-row-per-child behavior, existing order, and child open/edit behavior remain preserved.
  The stakeholder also explicitly directed that the survey layer's prior
  `coalesce(surveyor, survey_date, 'Survey')` display expression be replaced exactly by:

  ```qgis
  concat(survey_date, ' ', surveyor)
  ```

  The survey-expression change applies to the `survey` layers in Types 2–4, the only survey
  layers present in the authoritative schema; Type 1 has no `survey` layer. NULL/blank behavior
  is not used to alter either exact expression or to restore a fallback. No prior decision-log
  entry is deleted, reworded, or renumbered; D-FIX-007 remains the historical record of the
  earlier stakeholder-approved wording that this entry supersedes.

- **D-FIX-009** (2026-08-31, Category C — stakeholder-approved product change): The stakeholder
  explicitly directed: **“when the user clicks the photo-identification button, do not extract GPS
  from the photo EXIF. Use the current survey location or fixed-survey-plot location instead,
  namely the geometry/location from the survey layer or the related plot layer as appropriate.”**
  This supersedes, for this corrective release's photo-identification location behavior, the prior
  EXIF-based baseline recorded in the existing identification requirements and implementation
  evidence: the embedded widget's `qpbReadExifTag`/`qpbReadPhotoGps` path reads GPS tags from the
  first submitted photo and the response handler uses that coordinate for probability enrichment.
  The earlier EXIF behavior and its history are not deleted or rewritten here; this new entry is
  the stable record of what is superseded and why. The approved precedence is exact: Type 1 uses
  the current `inventory_observation.geom`; Type 2 follows the current `observation.survey_id` to
  `survey.plot_geom`; Type 3 follows `observation.survey_id` to `survey.plot_id` to `plot.plot_geom`;
  Type 4 has no identification button and remains outside the workflow. Missing, invalid,
  ambiguous, or mismatched geometry fails closed for the location-dependent path, with no EXIF,
  image-metadata, device-GPS, site, centroid, or stale-record fallback; the existing
  location-independent photo request/candidate/write-back flow remains available when its normal
  conditions are met. No schema, relation, provider, photo attachment, or original photo-byte
  contract is changed, and no new location field or metadata-sanitization feature is introduced.
  This entry preserves D-FIX-001 through D-FIX-008 and all prior identification decision history;
  it adds the explicit privacy/security boundary that image metadata is not read, logged, persisted,
  or transmitted as a location value, even though the existing photo bytes may continue to be sent
  to the existing identification provider under its existing disclosure.

- **D-FIX-010** (2026-08-31, Category C — stakeholder-approved product clarification): The
  stakeholder explicitly clarified: **“when the current survey/plot location is absent or invalid,
  the photo-identification request must continue normally, but occurrence probability based on
  location must not be calculated. Identification itself (photo submission, candidate result,
  selected Korean/scientific name and KTSN write-back) continues as far as the existing workflow
  allows. Do not extract EXIF, image metadata, or device GPS.”** This supersedes the earlier draft
  interpretation that missing, invalid, ambiguous, or mismatched location could block the entire
  photo-identification request. The earlier fail-closed wording remains valid only for the
  location-derived occurrence-probability calculation: it must not use a fallback or inferred
  location, and it must report the existing unavailable/no-probability-data state rather than a
  numeric zero. The location-independent photo request, candidate flow, explicit selection, and
  selected-name/KTSN write-back remain available under their existing conditions. D-FIX-009's
  exact Type 1–3 geometry precedence, Type 4 exclusion, and privacy/security prohibition on
  extracting, persisting, logging, or sending EXIF/image-metadata/device-GPS location remain in
  force. No prior decision-log entry is deleted, reworded, or renumbered; this entry records and
  supersedes only the earlier missing/invalid-location blocking interpretation.

- **D-FIX-011** (2026-09-06, Category A conformance defects): The supplied 85-second iPhone
  recording confirms two failures against existing behavior: (1) Type 3 nested-observation
  probability must use authoritative plot geometry even before the plot and survey are saved, as
  recorded in D-PRF-003; and (2) QField 4.2.11 does not immediately show a successfully saved
  daughter in its immediate parent's Related records list. AC-FIX-017 records only the existing
  relation-list refresh and persistence outcome; it adds no relation, schema, navigation, or
  display behavior.

## 10. References

- `specs/TEMPLATE.md` — specification structure and stable acceptance-ID convention.
- `specs/qfield-project-builder.md` — integrated MVP requirements, especially FR-QPB-083/084,
  FR-QPB-100/101/109, FR-QPB-131/132, FR-QPB-133/134, and their related AC/DR/Decision Logs.
- `specs/saved-feature-identification-edit.md` — existing-feature and Type 3 relation write-back
  contract, FR-SFE-001/002 and AC-SFE-001/002.
- `specs/html-report-interactive-analytics.md` — map, joined table, filtering, standalone HTML,
  offline behavior, and CSV contract, FR-HRA-001–017 and AC-HRA-001–016.
- `qfield_builder/schemas.py` — authoritative supported survey types, observation fields, geometry
  fields, `cover` integer range, `rel_observation_survey` relation definition, and the Type 2/3
  `survey_id`/`plot_id` location chains.
- `qfield_builder/korean_field_aliases.py` — authoritative field aliases `국명` and `피도`.
- `qfield_builder/korean_relation_display_names.py` — authoritative relation display name
  `rel_observation_survey` → `식물관찰`.
- `qfield_builder/qgis_worker.py` — existing display-expression and embedded relation-form
  configuration conventions.
- `qfield_builder/qml_plugin.py` — current identification button, attachment-byte workflow, and
  historical EXIF-GPS/probability path inspected for this change.
- `docs/product.md`, `docs/architecture.md`, `docs/ui-design-guidelines.md`, and
  `docs/change-control.md` — local-first, process-boundary, branding/layout, and change-routing
  constraints.
- Evidence artifact: `/Users/tory/Downloads/test2_report.html` (generated report; non-normative).

## 11. Open Questions

- None required to implement the observable corrections. If the supported minimum window size,
  exact Ex... label text, or target QField version/platform changes, update this Draft before
  approval rather than silently choosing new compatibility boundaries.
