# Feature: HTML report map valid-geometry collection

> Status: DRAFT — awaiting user review and approval
> Owner: spec-writer
> Last updated: 2026-09-01
> Extends: `specs/html-report-interactive-analytics.md`

## 1. Summary

Fix the HTML report map empty state that currently appears as “유효한 도형 없음” when valid
geometry exists in a spatial parent or survey layer but observation geometry is absent. The report
must build map records around spatial anchor layers, preserve the anchor geometry/coordinates, and
join the required ancestor/anchor context and child observation identity attributes onto the
observation-level result for display. It must preserve the
existing local-first report, Type 1–Type 4 relationships, identity fields, table interactions, CSV
behavior, geometry limitations, and data-integrity/privacy rules.

### Normative map data model

The report uses an explicit survey-type map/report model. The spatial record that owns the
applicable map context supplies the authoritative coordinates; joined child records supply
attributes only. Observation geometry never replaces the coordinates of a survey- or
plot-centred joined feature.

- **Type 1 simple inventory:** only the single active inventory layer exists in the context. Its
  valid geometry is rendered as-is; no additional join or fabricated parent layer is created.
- **Type 2 temporary plots:** the `site` polygon is rendered as a separate map layer/feature
  collection. The joined result contains the permitted non-secret attributes from `site`, `survey`,
  and `observation`, with one row per observation. Its map feature is survey-anchored: it uses the
  `survey` geometry/coordinates while carrying the joined site/survey context and each related
  observation's `국명`, `학명`, `KTSN`, stable UUID, and other permitted attributes. The site
  geometry remains a separate polygon and is never substituted for the survey geometry. An
  observation geometry, even when valid, cannot replace survey coordinates.
- **Type 3 permanent plots:** the `site` polygon is rendered separately. The joined result contains
  the permitted non-secret attributes from `site`, `plot`, `survey`, and `observation`, with one row
  per observation. Its map feature is plot-anchored and uses `plot` geometry/coordinates; a valid
  `survey` geometry is the fallback only when the plot geometry is unavailable. The joined feature
  carries the repeated site/plot/survey context needed to interpret each observation row. The site
  geometry remains a separate polygon and is never substituted for the plot/survey geometry.
  Observation geometry cannot replace either plot or survey coordinates.
- **Type 4 vegetation mapping:** only valid vegetation/community polygons are rendered. The
  report does not fabricate plant-observation joins or plant-observation map features.

The source row authority remains one row per joined observation in the attribute/join table where
applicable. Map features follow the spatial-anchor aggregation rule: one feature per spatial anchor
with a complete, deterministic collection of related child attributes. A separately rendered
`site` or vegetation/community polygon remains a distinct feature and is not used as a substitute
for a joined survey/plot anchor.

## 2. Functional Requirements

- **FR-MGC-001:** At export time, collect current records from the survey schema's available
  domain layers for the active survey type. Build the map feature collection from every eligible
  anchor spatial record whose
  schema-declared geometry is valid and serializable. Enrich that feature with related child
  attributes through the established UUID/FK joins. Valid parent or survey geometry must render
  even when all observation records lack geometry.

- **FR-MGC-002:** A map-eligible layer must be both schema-defined for the active survey type and
  available through the existing project-layer lookup/feature iteration path. Eligibility is
  survey-type-specific: Type 1 is the single inventory layer; Type 2 is `site` plus the
  survey-anchored survey–observation context; Type 3 is `site` plus the plot-anchored
  plot–survey–observation context; and Type 4 is vegetation/community polygons only. Non-spatial
  tables remain data-only. Geometry must never be inferred from a foreign key, parent/child
  relationship, centroid, attribute, photo, raster, or coincidence with another feature.

- **FR-MGC-003:** Emit map contexts in this deterministic order, restricted to records/layers that
  are eligible and actually present: Type 1 `inventory_observation` (the sole active layer);
  Type 2 `site`, then the survey–observation joined context; Type 3 `site`, then the
  plot–survey–observation joined context; Type 4 vegetation/community polygons only. Within each
  context, retain deterministic source iteration order. Order must not depend on display names,
  UUIDs, geometry validity, or joined-row order. Observation is not an independent map anchor in
  the Type 2 or Type 3 joined context.

- **FR-MGC-004:** Each rendered map feature retains the anchor source table/layer name, stable UUID,
  anchor geometry, and enough relationship context for the existing escaped detail view. Map
  construction is spatial-anchor-first: the selected anchor record supplies the rendered geometry
  and coordinates, while established UUID/FK joins supply permitted non-secret context attributes
  from all required ancestors and children. For Type 2, each joined observation row includes site,
  survey, and observation attributes; for Type 3, each joined observation row includes site, plot,
  survey, and observation attributes. A spatial parent is one map feature per anchor source record,
  not one feature per child joined row. Existing UUID/FK joins and one-to-many joined-table
  cardinality remain unchanged.

- **FR-MGC-012:** Select the spatial anchor from the active survey type and joined-context
  ownership, never from child geometry availability or child specificity. Type 1 uses its sole
  inventory layer. Type 2 uses `survey` for the survey–observation joined context and renders
  `site` separately. Type 3 uses `plot` for the plot–survey–observation joined context, falling
  back to `survey` only when the plot geometry is unavailable, and renders `site` separately.
  Type 4 uses vegetation/community polygons only. Observation is never selected as the coordinate
  source for a Type 2 or Type 3 joined feature. A valid child geometry never replaces or mutates
  the selected anchor geometry.

- **FR-MGC-013:** Join child attributes to the selected Type 2 or Type 3 spatial anchor only
  through the existing relation UUID/FK path. For one anchor with multiple related observations,
  aggregate a complete child collection in deterministic source iteration order; if source order is
  unavailable, use stable child UUID order. Preserve every child record and its `국명`, `학명`,
  `KTSN`, stable UUID, and other permitted identifiers in the anchor feature's related
  attributes/details. For each Type 2 joined observation row, also preserve the linked `site` and
  `survey` permitted attributes; for each Type 3 joined observation row, preserve the linked `site`,
  `plot`, and `survey` permitted attributes. Repeated site/anchor context across observation rows is
  required where necessary to keep observation-level row authority. The map feature remains one
  feature for the anchor, with one marker/geometry, and no child may be selected by arbitrary row
  order, display name, or geometry. A label may de-duplicate repeated display values, but the
  underlying context/child collection, joined rows, and CSV output must remain complete and
  unchanged.

- **FR-MGC-016:** The Type 2 and Type 3 joined attribute table is observation-row authoritative and
  must expose the complete permitted non-secret join context. Type 2 rows contain site + survey +
  observation attributes and use survey geometry/coordinates for the corresponding joined map
  feature. Type 3 rows contain site + plot + survey + observation attributes and use plot
  geometry/coordinates, with survey geometry only as the documented plot fallback. The separately
  rendered site polygon remains present but does not replace or remove site attributes from the
  joined result. Missing parent attributes remain empty/marked according to existing integrity
  behavior; they must not be fabricated from geometry, display text, or unrelated rows.

- **FR-MGC-014:** If a Type 2 joined observation has no resolvable survey anchor, or a Type 3 joined
  observation has no resolvable plot anchor and no valid survey fallback, retain the joined row in
  the attribute table and mark the relationship/geometry limitation in the existing integrity
  context; do not render it from observation geometry. In Type 3, a valid survey geometry may
  render the joined feature only as the documented plot-geometry fallback. A Type 2 or Type 3
  observation geometry is never an independent child-only substitute. Type 1 and Type 4 follow
  their own single-layer/polygon rules. If no eligible anchor has valid geometry, emit no joined map
  feature but retain all records, attributes, joins, and limitation reasons in the report.

- **FR-MGC-015:** When child identity is displayed on a Type 2 or Type 3 anchor feature, the
  selected anchor's geometry and coordinates are authoritative and must not be replaced by a child's
  geometry, centroid, photo location, or coordinate value. Type 3 survey fallback must be visibly
  marked as fallback in the existing detail/integrity context. Missing or invalid parent geometry
  is a limitation of that joined context, never permission to promote observation geometry into the
  parent's coordinate.

- **FR-MGC-005:** Transform source coordinates explicitly to EPSG:4326/WGS84 before map
  serialization. Preserve geometry type and coordinate structure. Current schema `POINT` and
  `MULTIPOLYGON` geometries are supported; unknown CRS, unavailable transformation, malformed
  JSON, empty/null geometry, non-finite coordinates, unsupported geometry, or transformation
  failure make that record unusable for the map.

- **FR-MGC-006:** Unusable geometry is omitted only from rendered map features, retained with its
  source record and non-geometry attributes in report data, and counted in the existing geometry
  limitation notice with a stable reason. Non-spatial records are not geometry failures and do not
  inflate that count.

- **FR-MGC-007:** Show “유효한 도형 없음” only when the complete eligible spatial collection has
  zero valid features. If no eligible spatial layer/record exists, disclose that state separately
  when distinguishable; if eligible records exist but all geometry is unusable, disclose that
  limitation. Any valid local feature suppresses the no-valid-geometry state.

- **FR-MGC-008:** Preserve the existing joined table and report behavior: Type 1–Type 4 schema
  relationships and stable UUIDs; `국명`, `학명`, and `KTSN` columns; filtering across visible
  fields; deterministic sorting; visible-row counts; and filtered/all-row UTF-8 CSV export.
  Map-layer inclusion must not alter species/date aggregation or duplicate joined rows.

- **FR-MGC-009:** Type 4 `dominant_species` remains separate community data. A Type 4 map feature
  must not fabricate a Type 1–Type 3 observation, plant identity, or plant-observation geometry.
  Absent hierarchy levels remain empty rather than synthesized.

- **FR-MGC-010:** Local features, map controls, details, summaries, filtering, sorting, and CSV
  must work without network access or a VWorld API key. Existing VWorld-first/OpenStreetMap
  fallback, attribution, and offline status remain optional background enhancements and must not
  gate local rendering.

- **FR-MGC-011:** The standalone report keeps all local map/data code embedded or packaged locally.
  Collected values are escaped in HTML/details and safely quoted in CSV. Secrets, credentials,
  API keys, attachment paths, and photo contents must not be added to map properties, visible
  details, CSV, diagnostics, or logs.

## 3. Constraints

- **C-MGC-001:** `qfield_builder/schemas.py` remains the source of truth. This feature does not
  add or alter tables, geometry columns, CRS declarations, relations, UUIDs, forms, or layer
  visibility.
- **C-MGC-002:** Joins use established UUID/FK columns only; display text, row position, geometry
  coincidence, and coordinate proximity are not join keys.
- **C-MGC-003:** Collection and rendering are read-only with respect to QField/GeoPackage data.
- **C-MGC-004:** Existing report output location, local-first behavior, licenses/attribution,
  escaped rendering, CSV contract, and limitation disclosures remain in force.
- **C-MGC-005:** No remote script, stylesheet, geocoder, spatial API, or basemap is required for
  local report operation.

## 4. Assumptions

- **A-MGC-001:** “Spatial survey” means a schema-defined `survey` table with a geometry field; it
  does not authorize adding geometry to current Type 2–4 `survey` definitions where none exists.
- **A-MGC-002:** “Available” means resolvable and iterable through the report's existing runtime
  layer APIs. An inaccessible layer is a disclosed limitation, not a reason to synthesize data.
- **A-MGC-003:** Runtime layer CRS is authoritative for transformation. EPSG:4326/WGS84 is the
  map interchange CRS; coordinates are interpreted as longitude/latitude in GeoJSON order after
  transformation, with no numeric guessing or axis swapping.
- **A-MGC-004:** Existing report collection can retain all source records and attributes even when
  a record's geometry is unusable.

## 5. Edge Cases

- **E-MGC-001:** All observations lack geometry but a valid site, plot, survey, or other eligible
  parent exists: parent features render and the empty-state message is absent.
- **E-MGC-002:** Only non-spatial tables exist, including `observation`, `survey_photo`, or
  `plot_photo`: no map feature is emitted; their records remain eligible for existing tables.
- **E-MGC-003:** One eligible layer mixes valid, missing, null, empty, malformed, unsupported, and
  untransformable geometries: valid records render, unusable records remain in report data, and
  reason counts are accurate.
- **E-MGC-004:** A layer cannot be found, iterated, or transformed: report generation remains
  usable, the limitation is disclosed, and no replacement geometry or layer is fabricated.
- **E-MGC-005:** A parent has multiple children or a child has a missing parent: map feature count
  follows the survey-type spatial-anchor rules: one Type 2 survey anchor or one Type 3 plot/survey
  fallback anchor with a complete, deterministic child collection; no observation-only replacement
  feature is emitted for Type 2 or Type 3. Joined rows and orphan markers follow existing FK
  behavior.
- **E-MGC-010:** A survey has a valid geometry and two observations with different identities but no
  valid observation geometry: one survey-anchored map feature renders at the survey coordinates and
  displays both child identity sets in source order; the joined table and CSV still contain two rows.
- **E-MGC-011:** A Type 2 survey has no valid geometry and an observation has valid geometry: the
  observation remains report data only and the joined map feature is omitted (apart from any
  separately valid `site` polygon). No survey coordinate is fabricated and observation geometry is
  not promoted.
- **E-MGC-012:** Both survey and observation have valid geometry in Type 2: exactly one joined
  feature keeps the survey geometry and carries the observation identity; observation geometry does
  not create a replacement or additional observation anchor. In Type 3, the analogous feature
  keeps plot geometry, or survey geometry only when plot geometry is unavailable.
- **E-MGC-013:** A Type 3 plot has no valid geometry while its joined survey has valid geometry:
  the joined feature renders at the survey coordinates and is marked as using the documented
  fallback. If neither plot nor survey geometry is valid, the joined row remains report data only.
- **E-MGC-014:** Type 2 or Type 3 has a valid site polygon and no valid joined survey/plot anchor:
  the site polygon still renders separately, while joined observations remain in the table with the
  linked site context and appropriate geometry limitation. If a joined survey/plot anchor is valid,
  the same site context is included in each observation-level joined row even though the site
  polygon remains a separate map feature.
- **E-MGC-015:** A Type 2 joined result contains site and survey context alongside each observation
  row, while its joined map feature uses survey coordinates and the site polygon remains a separate
  feature. A Type 3 joined result contains site, plot, and survey context alongside each observation
  row, while its joined map feature uses plot coordinates or the documented survey fallback and the
  site polygon remains separate. Repeated context values across rows are preserved.
- **E-MGC-006:** The dataset has zero records or zero valid eligible geometries: the report renders
  its existing empty tables/summaries and a truthful map state without throwing.
- **E-MGC-007:** Valid local geometry exists while VWorld/OSM, network, or key is unavailable:
  local map and all local report functions remain usable with an explicit background status.
- **E-MGC-008:** Type 4 contains `dominant_species` but no observation table: community data may be
  shown, while plant-observation identity and rows are not created.
- **E-MGC-009:** Names, notes, IDs, or layer values contain HTML/script-like text or non-ASCII
  characters: displayed text is inert and CSV remains correctly encoded and quoted.

## 6. Out of Scope

- Adding geometry to existing schema tables or changing Type 1–Type 4 relationships.
- Deriving geometry from photos, EXIF/GPS metadata, rasters, attributes, FK values, centroids, or
  external services.
- Changing species matching, identification write-back, date/species aggregation, output paths,
  basemap policy, or report visual design beyond the map data/state needed by this feature.
- Modifying production code or tests as part of this specification artifact.

## 7. Acceptance Criteria

- **AC-MGC-001:** Given one project of each supported survey type, when the report is opened, then
  Type 1 renders the sole inventory layer; Type 2 renders a separate site polygon and survey-
  anchored survey–observation features; Type 3 renders a separate site polygon and plot-anchored
  plot–survey–observation features with survey fallback when plot geometry is unavailable; and Type
  4 renders vegetation/community polygons only. Each rendered feature uses its documented anchor
  coordinates and “유효한 도형 없음” is absent whenever any eligible feature is valid.
- **AC-MGC-002:** Given one project of each supported survey type, when map data is generated, then
  only the survey-type-eligible schema-defined spatial contexts are emitted in the exact FR-MGC-003
  order, and non-spatial tables emit zero map features.
- **AC-MGC-003:** Given mixed valid and unusable geometries in an eligible layer, when the report is
  opened, then every valid geometry is rendered as EPSG:4326/WGS84 with preserved type/coordinates,
  every unusable record remains in report data, and limitation counts/reasons exclude non-spatial
  rows.
- **AC-MGC-004:** Given Type 2 or Type 3 joined data with one spatial parent, multiple children, and
  one orphan child, when map features and the joined table are inspected, then the Type 2 survey or
  Type 3 plot/survey-fallback anchor appears once at its authoritative coordinates with a complete
  deterministic collection of related child `국명`/`학명`/`KTSN` values, all child rows remain, and
  the orphan is not rendered from observation geometry; it retains the existing integrity marker
  and limitation without receiving a parent coordinate.
- **AC-MGC-008:** Given a survey with valid geometry and multiple observations with different
  `국명`/`학명`/`KTSN` values but no observation geometry, when the map is generated, then exactly one
  survey-anchored feature appears at the survey coordinates and exposes all child identity values in
  source order; the joined table and CSV retain one row per observation.
- **AC-MGC-009:** Given Type 2 survey data without usable survey geometry and an observation with
  valid geometry, when the map is generated, then the observation remains report data only and no
  observation-only feature is emitted. The missing-survey limitation is disclosed and no survey
  geometry is synthesized.
- **AC-MGC-010:** Given valid survey and observation geometries in Type 2, when the map is generated,
  then exactly one survey-anchored joined feature retains the survey coordinates and joined
  observation identity; no separate observation feature is emitted. Given equivalent Type 3 data,
  the feature retains plot coordinates, or survey coordinates only when plot geometry is unavailable.
  Joining child identity does not move or duplicate the selected anchor.
- **AC-MGC-011:** Given Type 2 data with linked site, survey, and multiple observation records, when
  the joined map and attribute table are inspected, then the site polygon is rendered separately,
  each observation-level joined row contains the permitted site + survey + observation attributes,
  and the corresponding joined map feature uses survey geometry/coordinates. Given Type 3 data with
  linked site, plot, survey, and multiple observations, each row contains the permitted site + plot
  + survey + observation attributes, the site polygon remains separate, and the joined map feature
  uses plot geometry/coordinates or survey geometry only as the documented plot fallback. Repeated
  site/anchor context is preserved and no observation row is collapsed or duplicated.
- **AC-MGC-005:** Given valid local geometry and no network, VWorld key, or remote tile service, when
  the copied report is opened offline, then local map features, details, summaries, `국명`/`학명`/
  `KTSN`, filtering, sorting, and CSV remain usable without remote code or spatial data.
- **AC-MGC-006:** Given Type 4 community records with `dominant_species`, when map and joined data
  are generated, then valid community geometry may render but no fabricated plant-observation row,
  plant identity, or observation geometry appears.
- **AC-MGC-007:** Given duplicate names, nulls, HTML/script-like values, Korean text, credentials,
  and attachment paths, when the report and CSV are inspected, then identity columns and existing
  filter/sort/CSV behavior are preserved, HTML is inert, and secrets/attachment paths are absent
  from map properties, details, CSV, diagnostics, and logs.

## 8. Out-of-scope future items

Future runtime layers that expose geometry without a schema geometry declaration, and future
per-layer map styles for observation or other newly spatial layers, require separate approved
changes. They are not compatibility behavior for this feature and do not alter the Type 1–Type 4
rules above.

## 9. Traceability

| Requirement | Acceptance criteria | Existing source/contract |
|---|---|---|
| FR-MGC-001–003 | AC-MGC-001, AC-MGC-002 | `qml_plugin.py` report collection; `schemas.py` `TableDef`/`GeometryDef`; FR-HRA-001/003 |
| FR-MGC-004, FR-MGC-008–009, FR-MGC-012–016 | AC-MGC-001, AC-MGC-004, AC-MGC-006–011 | Spatial-anchor geometry preservation; Type 1–Type 4 UUID/FK joins; site/anchor context in Type 2/3 joined rows; FR-HRA-005–012; current identity aliases |
| FR-MGC-005–007, FR-MGC-009–011 | AC-MGC-001, AC-MGC-002, AC-MGC-003, AC-MGC-005 | `qpbGeometryToGeoJson`; FR-HRA-003/017; C-HRA-006; geometry limitation UI |
| FR-MGC-014–015 | AC-MGC-004, AC-MGC-005, AC-MGC-007, AC-MGC-009–010 | FR-HRA-015–017; C-HRA-004/008; CSV/escaping acceptance coverage |
| C-MGC-001–005; A-MGC-001–004; E-MGC-001–015 | AC-MGC-001–011 | `test_html_report_export.py`, `test_html_report_interactive_analytics.py`, `test_html_report_dhra003_vworld_osm_fallback.py`, `test_html_report_ui_refinement.py` |
