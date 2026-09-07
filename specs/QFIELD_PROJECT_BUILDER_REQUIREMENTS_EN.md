# QField Project Builder — Product Requirements Draft

**Document purpose:** Input for the spec writer in a spec-driven, clean-room development workflow  
**Primary user:** Ecological field researchers  
**Status:** Draft for review  
**Normative language:** “Must”, “must not”, “should”, and “may” are used in their usual requirements sense.

## Instructions to the Spec Writer

Use this document as the product-level source of truth for the first specification pass. Preserve the existing clean-room scaffold and its technology boundaries. Convert the requirements into traceable functional requirements, non-functional requirements, data contracts, acceptance tests, and architecture decision records. Do not silently resolve the items in Section 15; either obtain a decision or record a clearly labeled, reversible assumption. Do not implement production code until the resulting specification and the required feasibility spikes have been reviewed.

## 1. Product Summary

Build a local-first application named **QField Project Builder**. The application must automate the end-to-end creation of a QField-ready ecological survey project, including:

1. selecting a survey type;
2. creating the correct local GeoPackage schema;
3. importing or drawing survey sites, plots, and an offline-map extent where applicable;
4. generating and configuring a QGIS project;
5. configuring relations, forms, field constraints, symbology, attachments, and relative paths;
6. optionally configuring VWorld online or offline basemaps;
7. optionally integrating Pl@ntNet photo identification, Korean taxon-name resolution, and occurrence-probability lookup; and
8. producing a self-contained folder that can be copied directly between a computer and a smartphone.

The application is intended for ecologists who should not need to create database tables, write SQL, or manually configure QGIS/QField project settings.

## 2. Scope and Hard Constraints

### 2.1 In scope

- A guided project-creation workflow.
- Four ecological survey templates.
- Local GeoPackage creation only.
- QGIS project generation and configuration.
- Online VWorld basemap configuration.
- Optional generation of a bounded offline basemap.
- Optional Pl@ntNet-assisted plant identification.
- Korean name and accepted-name lookup using the supplied KTSN CSV.
- Location-specific occurrence-probability lookup using the supplied GeoTIFF files.
- Direct folder transfer to and from QField on a smartphone.
- Validation reports and end-user transfer instructions.

### 2.2 Explicitly out of scope

- PostgreSQL, PostGIS, or any other remote database.
- QFieldCloud or another cloud database/synchronization service.
- QFieldSync packaging as the final transfer workflow.
- General ecological analysis, dashboards, or publication-ready reporting.
- Requiring users to edit the generated `.qgs` XML manually.
- Choosing a new application technology stack when an existing scaffold already defines one. The implementation must follow the existing scaffold unless a separate architecture decision changes it.

### 2.3 Local-first and network behavior

- All survey records, geometries, relations, selected identifications, and attachment paths must remain in the local project folder.
- The only expected external network requests are:
  - VWorld map requests; and
  - Pl@ntNet identification requests when that optional feature is enabled.
- The UI must clearly disclose that photos submitted for identification are sent to Pl@ntNet.
- When the field device is offline, identification requests must be queued and clearly marked as pending. They must resume only after the user explicitly retries or enables automatic retry when connectivity returns.

## 3. Important GeoPackage Key Design

The user-facing and relational identifier for every domain entity must be a UUID v4, not a sequence or user-visible autoincrementing number.

GeoPackage feature and attribute tables require an integer primary key for standards-compliant row/feature identification. Therefore:

- Each GeoPackage table may contain a hidden physical key such as `fid INTEGER PRIMARY KEY AUTOINCREMENT` when required by GeoPackage/QGIS.
- `fid` is an implementation-only storage identifier. It must never be displayed to the user, copied into business exports as the domain identifier, or used by a domain relation.
- Every domain table must contain a UUID field such as `site_id`, `plot_id`, `survey_id`, `observation_id`, or `community_id`.
- Each UUID field must be `TEXT NOT NULL UNIQUE` and contain a canonical lowercase UUID with hyphens and without braces.
- All application-generated records must receive a UUID v4.
- In QGIS forms, the UUID field must use the UUID Generator widget or the default expression `uuid('WithoutBraces')`, must be read-only, and should normally be hidden.
- Every foreign key must reference the UUID field, never `fid`.
- Database-level foreign-key constraints and matching QGIS project relations must both be created.

This distinction is mandatory: **physical GeoPackage key = hidden `fid`; logical/domain key = UUID**.

## 4. Guided User Workflow

The project-creation wizard must use the following sequence.

### Step 1 — Project basics

Collect:

- project name;
- output directory;
- optional project description;
- project CRS, defaulting to EPSG:5186 for Korean field projects; and
- storage CRS, defaulting to EPSG:4326 for the survey GeoPackage geometry layers described below.

Project names must be sanitized for cross-platform filenames. The UI must show the final folder and file names before creation.

### Step 2 — Survey type

Require exactly one of the following choices:

1. Simple species inventory;
2. Temporary plots at defined sites;
3. Permanent plots at defined sites; or
4. Vegetation mapping.

The selected survey type controls the GeoPackage schema, relations, editable layers, form layout, required photos, and symbology.

### Step 3 — Site and plot inputs

When applicable, allow either:

- upload of a GeoPackage layer;
- upload of a zipped Shapefile containing at least `.shp`, `.shx`, `.dbf`, and preferably `.prj`; or
- drawing features in an interactive map.

Validation requirements:

- site data must be Polygon or MultiPolygon;
- permanent plot data must be Point;
- input CRS must be detected or explicitly supplied by the user;
- invalid geometry must be reported and, only with user approval, repaired;
- imported geometry must be transformed to the configured storage CRS;
- the user must map source attributes to required fields such as `site_name` and, where applicable, `plot_size`;
- imported values must be previewed before they are written; and
- creation must be atomic: invalid input must not leave a partially generated project.

For temporary-plot projects, an uploaded plot-point layer may be used as a set of proposed survey locations. Each point becomes a seed survey record whose date and surveyor remain empty until field collection.

### Step 4 — Connectivity and basemap mode

Ask whether the field site has sufficient connectivity for an online map.

- **Online mode:** configure a VWorld WMTS/XYZ layer using the supplied API key.
- **Offline mode:** require a bounded area and generate a local basemap for that area.

### Step 5 — Optional photo identification

Ask whether photo-based plant identification is required.

- If no, do not request a Pl@ntNet API key and do not add the identification runtime.
- If yes, request a Pl@ntNet API key, validate it without logging it, and enable the photo-identification workflow described in Section 9.

### Step 6 — Review and build

Show a final review containing:

- selected survey type;
- schema summary;
- number of imported sites/plots;
- basemap mode;
- offline extent, zoom/resolution, and estimated size where applicable;
- whether Pl@ntNet is enabled;
- output folder; and
- warnings about embedded VWorld credentials and smartphone folder transfer.

The build must run as an observable job with progress, cancellation, rollback, and a final validation report.

## 5. Common Database Rules

- Database format: one local `.gpkg` file per generated project.
- No remote database connection strings may be generated.
- Geometry storage CRS: EPSG:4326 by default.
- Use `MULTIPOLYGON` for site and community layers and `POINT` for plot or inventory layers.
- Enable spatial indexes on every geometry column.
- Create ordinary indexes on all UUID foreign-key columns and commonly searched name fields.
- Use `ON UPDATE CASCADE` for UUID foreign keys.
- Use `ON DELETE CASCADE` for composition-owned child records unless a later domain decision requires restrictive deletion.
- Use `DEFERRABLE INITIALLY DEFERRED` where supported.
- Ensure `PRAGMA foreign_keys = ON` for every application-managed SQLite connection.
- Validate all foreign keys with `PRAGMA foreign_key_check` before delivery.
- Photo files must never be stored as database BLOBs. Store only paths relative to the project folder.
- Absolute paths must not be written into the GeoPackage or QGIS project.
- Date fields use ISO `YYYY-MM-DD`; timestamps, if added for auditing, use ISO 8601 with timezone.
- Required text must be trimmed and must reject empty strings.

## 6. Draft Schema by Survey Type

The following is a logical schema. A hidden integer `fid` may additionally exist as required by GeoPackage, but every displayed ID and every relation must use the UUID columns below.

### 6.1 Type 1 — Simple species inventory

This survey type must have one editable Point layer and no parent-child domain relation.

#### `inventory_observation` — Point, EPSG:4326

| Field | Type | Required | Rule |
|---|---|---:|---|
| `inventory_id` | TEXT UUID | yes | logical identifier; unique; read-only |
| `observed_at` | DATETIME | yes | default `now()` |
| `surveyor` | TEXT | yes | non-empty |
| `selected_korean_name` | TEXT | after identification | final user-selected Korean name |
| `selected_scientific_name` | TEXT | after identification | final user-selected scientific name |
| `selected_ktsn` | TEXT | no | accepted KTSN when available |
| `identification_score` | REAL | no | 0–1 |
| `occurrence_probability` | REAL | no | 0–1; null when unavailable |
| `leaf_photo_1_path` | TEXT | yes | relative Attachment path |
| `flower_photo_1_path` | TEXT | yes | relative Attachment path |
| `fruit_photo_1_path` | TEXT | yes | relative Attachment path |
| `extra_photo_1_path` | TEXT | no | relative Attachment path |
| `extra_photo_1_organ` | TEXT | conditional | `leaf`, `flower`, or `fruit` |
| `extra_photo_2_path` | TEXT | no | relative Attachment path |
| `extra_photo_2_organ` | TEXT | conditional | `leaf`, `flower`, or `fruit` |
| `identification_status` | TEXT | yes | `not_requested`, `pending`, `complete`, or `failed` |
| `notes` | TEXT | no | multiline text |
| `geom` | POINT | yes | feature location |

Rationale for the fixed photo fields: this survey template must remain relation-free, while Pl@ntNet accepts at most five photos for a single identification request. The three required fields ensure at least one leaf, flower, and fruit image; two optional fields allow additional images.

### 6.2 Type 2 — Temporary plots at defined sites

Core relationship:

`site (1) → (many) survey (1) → (many) observation`

#### `site` — MultiPolygon, EPSG:4326

| Field | Type | Required | Rule |
|---|---|---:|---|
| `site_id` | TEXT UUID | yes | logical identifier; unique |
| `site_name` | TEXT | yes | searchable display field |
| `site_geom` | MULTIPOLYGON | yes | survey-site boundary |

#### `survey` — Point, EPSG:4326

| Field | Type | Required | Rule |
|---|---|---:|---|
| `survey_id` | TEXT UUID | yes | logical identifier; unique |
| `site_id` | TEXT UUID | yes | FK → `site.site_id` |
| `survey_date` | DATE | yes | default current date |
| `surveyor` | TEXT | yes | non-empty |
| `plot_size` | TEXT | yes | human-readable plot dimensions |
| `plot_geom` | POINT | yes | temporary plot location |

#### `observation` — no geometry

| Field | Type | Required | Rule |
|---|---|---:|---|
| `observation_id` | TEXT UUID | yes | logical identifier; unique |
| `survey_id` | TEXT UUID | yes | FK → `survey.survey_id` |
| `selected_korean_name` | TEXT | yes after selection | final chosen name |
| `selected_scientific_name` | TEXT | yes after selection | final chosen name |
| `selected_ktsn` | TEXT | no | accepted KTSN when available |
| `cover` | INTEGER | yes | 0–100 inclusive |
| `identification_score` | REAL | no | 0–1 |
| `occurrence_probability` | REAL | no | 0–1; null when unavailable |
| `identification_status` | TEXT | yes | controlled status value |
| `notes` | TEXT | no | multiline text |

#### Photo tables

- `survey_photo(photo_id UUID, survey_id UUID FK, path TEXT, captured_at DATETIME, notes TEXT)`
- `observation_photo(photo_id UUID, observation_id UUID FK, path TEXT, organ TEXT, captured_at DATETIME)`

Rules:

- Each temporary `survey` must have at least one related `survey_photo` before field completion.
- Each plant `observation` must have at least one related `observation_photo`.
- `organ` must be one of `leaf`, `flower`, `fruit`, `bark`, or `auto`.
- Up to five selected observation photos may be submitted in one Pl@ntNet request; all submitted photos must represent the same individual plant.

### 6.3 Type 3 — Permanent plots at defined sites

Core relationship:

`site (1) → (many) plot (1) → (many) survey (1) → (many) observation`

#### `site` — MultiPolygon, EPSG:4326

Use the same fields and rules as Type 2.

#### `plot` — Point, EPSG:4326

| Field | Type | Required | Rule |
|---|---|---:|---|
| `plot_id` | TEXT UUID | yes | logical identifier; unique |
| `site_id` | TEXT UUID | yes | FK → `site.site_id` |
| `plot_name` | TEXT | yes | searchable display field |
| `plot_size` | TEXT | yes | human-readable dimensions |
| `plot_geom` | POINT | yes | fixed plot location |

#### `survey` — no geometry

| Field | Type | Required | Rule |
|---|---|---:|---|
| `survey_id` | TEXT UUID | yes | logical identifier; unique |
| `plot_id` | TEXT UUID | yes | FK → `plot.plot_id` |
| `survey_date` | DATE | yes | default current date |
| `surveyor` | TEXT | yes | non-empty |

#### `observation` — no geometry

Use the same observation fields and rules as Type 2, with `survey_id` referencing the permanent-plot survey.

#### Photo tables

- `plot_photo(photo_id UUID, plot_id UUID FK, path TEXT, captured_at DATETIME, notes TEXT)`
- `observation_photo(photo_id UUID, observation_id UUID FK, path TEXT, organ TEXT, captured_at DATETIME)`

Rules:

- Each permanent `plot` must have at least one related `plot_photo`.
- Plot photos belong to the permanent plot rather than to each repeated survey.
- Each plant `observation` must have at least one related `observation_photo`.

### 6.4 Type 4 — Vegetation mapping

Core relationship:

`site (1) → (many) survey (1) → (many) community`

#### `site` — MultiPolygon, EPSG:4326

Use the same fields and rules as Type 2.

#### `survey` — no geometry

| Field | Type | Required | Rule |
|---|---|---:|---|
| `survey_id` | TEXT UUID | yes | logical identifier; unique |
| `site_id` | TEXT UUID | yes | FK → `site.site_id` |
| `survey_date` | DATE | yes | default current date |
| `surveyor` | TEXT | yes | non-empty |

#### `community` — MultiPolygon, EPSG:4326

| Field | Type | Required | Rule |
|---|---|---:|---|
| `community_id` | TEXT UUID | yes | logical identifier; unique |
| `survey_id` | TEXT UUID | yes | FK → `survey.survey_id` |
| `community_name` | TEXT | yes | searchable display field |
| `dominant_species` | TEXT | yes | manually entered or selected |
| `is_field_checked` | BOOLEAN | yes | default false |
| `community_geom` | MULTIPOLYGON | yes | mapped vegetation polygon |
| `notes` | TEXT | no | multiline text |

Rule-based symbology must distinguish field verification status:

- `is_field_checked = true`: green hatch/pattern;
- all other values: red hatch/pattern.

## 7. QGIS Project Generation

The application must generate the QGIS project through supported QGIS/PyQGIS APIs where possible. It must not rely on fragile string replacement in `.qgs` XML as the primary implementation method.

### 7.1 Project files and paths

- Generate an uncompressed `.qgs` project unless a compatibility test explicitly approves `.qgz`.
- Store the `.qgs` and `.gpkg` inside the same project folder tree.
- Use relative paths for the GeoPackage, attachments, basemap, plugin, and reference assets.
- Set the configured project CRS and enable on-the-fly transformation.
- Load every required GeoPackage layer, including non-spatial tables used by relations.
- Do not load internal GeoPackage metadata tables into the layer tree.
- Group layers into `Survey data`, `Basemap`, and `Reference` groups.

### 7.2 QGIS relations

- Create one QGIS project relation for every database foreign key.
- Use stable relation IDs such as `rel_survey_site`, `rel_observation_survey`, and `rel_photo_observation`.
- Use Composition strength for owned child records, including observations and photo rows.
- Add child relations to parent forms so users can create observations or photos from the parent feature.
- Foreign-key fields must use Relation Reference widgets with a human-readable display expression.

### 7.3 Attribute forms

Use the Drag and Drop Designer and organize forms into clear tabs or groups. At minimum:

- hide `fid` and UUID fields from normal entry;
- keep UUID values non-editable;
- use Date/Time widgets with current date/time defaults;
- use Relation Reference widgets for foreign keys;
- enable opening referenced forms where useful;
- use Range for `cover`, with minimum 0, maximum 100, and step 1;
- use Checkbox for `is_field_checked`, default false;
- use Value Map for controlled categorical values;
- use Attachment widgets for photo-path fields;
- configure attachment paths as relative paths;
- require mandatory attributes with hard constraints, not only UI labels;
- use multiline text widgets for notes; and
- add embedded relation widgets for child observations and photo galleries.

For related photo tables, configure the QField gallery relation behavior by setting the child `path` field to the Attachment widget and including the relation in the parent form.

### 7.4 Layer display and project properties

- Set each layer's display expression to a useful human-readable field, such as `site_name`, `plot_name`, `survey_date`, `selected_korean_name`, or `community_name`.
- Make reference/extents non-identifiable and read-only where appropriate.
- Make survey data searchable where useful.
- Enable transaction behavior appropriate for related edits.
- Enable evaluation of provider-side/default values where required, while ensuring UUID generation also works in QField.
- Validate that a parent and its new child records can be created and saved in one field workflow.

## 8. Basemap Requirements

### 8.1 VWorld credentials and online layer

Collect the VWorld API key as a secret input. Mask it in the UI and never include it in logs or diagnostic exports.

Support VWorld layers from the documented set:

- `Base`
- `gray`
- `midnight`
- `Hybrid`
- `Satellite`

The documented XYZ/WMTS GetTile URL pattern is:

```text
http://api.vworld.kr/req/wmts/1.0.0/{key}/{layer}/{z}/{y}/{x}.png
```

Prefer HTTPS when the VWorld endpoint supports it. The implementation must allow the scheme and URL template to be updated in configuration without a code change because external API endpoints may change.

Because QField needs the online URL at runtime, the VWorld key may be present in the generated project URL. Before creation, the UI must explicitly warn the user that anyone receiving the project folder may be able to read and use that key.

### 8.2 Offline extent input

Offline mode must accept either:

- an extent drawn on the map; or
- a Polygon/MultiPolygon from an uploaded GeoPackage or zipped Shapefile.

Use the envelope/bbox of the selected geometry as the MBTiles download extent. Download every map tile that intersects the bbox; edge tiles may extend to normal tile boundaries. Polygon clipping is not required.

The UI must show:

- bbox coordinates;
- area;
- selected minimum and maximum zoom levels;
- expected tile count;
- estimated output size; and
- a visible 1 GiB hard limit.

### 8.3 Offline size gate

- The final `.mbtiles` file must not exceed **1 GiB (1,073,741,824 bytes)**.
- Use **900 MiB** as the pre-generation acceptance threshold to preserve overhead and estimation error.
- Estimate size from tile count and representative `Content-Length` samples where possible. Use a conservative percentile and safety multiplier rather than only an average.
- If the estimate exceeds 900 MiB, block creation and ask the user to reduce bbox size, reduce maximum zoom, or choose a lower resolution.
- Generate into a temporary location and monitor size during creation.
- If the final output exceeds 1 GiB, abort, remove the incomplete temporary output, and return the user to extent/resolution selection.
- VWorld request quotas, rate limits, retries, and caching terms must be respected. The user must confirm that their intended offline caching is permitted by the applicable VWorld terms.

### 8.4 Offline MBTiles generation

The canonical offline basemap format is **MBTiles**. The application must generate one MBTiles file from the selected VWorld layer for the user-approved bbox and zoom-level range.

The required pipeline is:

1. determine all VWorld tiles intersecting the approved bbox at every selected zoom level;
2. display the tile count and conservative size estimate before downloading;
3. download/render the required tiles while respecting VWorld authentication, quota, rate-limit, retry, and caching requirements;
4. write the tiles and required metadata into a standards-compatible `.mbtiles` file in a temporary build directory;
5. verify that the MBTiles coverage contains the approved bbox and that its minimum and maximum zoom levels match the user's selection;
6. verify that the final MBTiles file does not exceed 1 GiB; and
7. add the MBTiles layer to the QGIS project using a relative path.

Do **not** run QGIS/GDAL **Build Overviews** as a separate step. The generated MBTiles file already contains its multi-resolution tile pyramid through the stored zoom levels.

The MBTiles metadata must include, at minimum, a stable name, format, geographic bounds, minimum zoom, and maximum zoom. Tile-row orientation and metadata must be verified against the explicitly supported QGIS and QField versions. The app must not report success until the generated MBTiles opens in the project and renders at representative locations and zoom levels.

## 9. Photo Identification and Taxon Resolution

### 9.1 Execution context

Immediate identification after adding a photo in smartphone QField requires a QField project plugin or equivalent supported QField runtime extension. Therefore, when Pl@ntNet is enabled, the generated project must include a project-specific QML/JavaScript plugin sidecar with the same base name as the `.qgs` file.

The plugin must:

- request permission before activation as required by QField;
- detect or expose a clear action for identifying a newly attached observation;
- read the selected relative attachment files;
- read EXIF GPS when present;
- call Pl@ntNet when connected;
- queue the request when offline;
- display the top three candidates;
- run KTSN and probability enrichment;
- allow one candidate to be selected; and
- update the correct GeoPackage record without changing `fid` or breaking UUID relations.

Before full implementation, perform a clean-room feasibility spike covering attachment-change detection, multipart HTTP requests, EXIF access, feature updates, and raster sampling in the supported QField versions. If silent attachment hooks are not stable, provide an explicit **Identify attached photos** button immediately after the feature is saved; do not pretend that unsupported automatic behavior exists.

### 9.2 Pl@ntNet request

- Endpoint family: `/v2/identify/{project}`.
- Default project: `all`, unless a more appropriate supported flora is selected by the user.
- Request exactly three results using `nb-results=3`.
- Use `species.scientificNameWithoutAuthor` as the normalized scientific name for KTSN matching.
- Preserve the full API scientific name and authorship for display/audit.
- Confidence scores are 0–1 and must be displayed consistently, preferably as both a score and percentage.
- Supply one `organs` value for each submitted photo in matching order.
- Submit no more than five JPEG/PNG photos representing the same plant individual in one request.
- Handle authentication failure, quota exhaustion, timeout, non-plant rejection, malformed responses, and no-result responses without losing the observation.
- Never log the API key or photo binary data.

### 9.3 Required reference assets

The application expects these assets in the existing scaffold:

```text
storage/reference/tables/tb_leco_nib_ktsn_dtl_gat.csv
storage/reference/rasters/bce_inverse_corrected_probability_maps/
```

Project creation must fail early with a clear message when Pl@ntNet/KTSN enrichment is enabled but the CSV is missing or lacks required columns.

Required CSV columns:

- `ktsn`
- `taxon_full_nm`
- `taxon_kor_nm`
- `taxon_jm_nm`
- `correct_list`

The loader must explicitly handle file encoding, preserve KTSN values as strings, and validate JSON in `correct_list`.

### 9.4 Direct KTSN name match

For each of the top three Pl@ntNet candidates:

1. Read `species.scientificNameWithoutAuthor`.
2. Normalize it by trimming leading/trailing whitespace and collapsing repeated internal whitespace.
3. Normalize each CSV `taxon_full_nm` by removing literal `<em>` and `</em>` tags, trimming, and collapsing repeated whitespace.
4. Perform an exact normalized match. Do not use fuzzy matching in the initial version.
5. If a row matches, display its `taxon_kor_nm` as the direct Korean-name match.
6. If no row matches, show `KTSN match not found`; do not fabricate a Korean name.

### 9.5 Accepted-name resolution

Use `taxon_jm_nm` as the nomenclatural-status field because the workflow compares it with the literal value `정명`.

- If `taxon_jm_nm == '정명'`, use the matched row as the accepted KTSN record.
- Otherwise, parse `correct_list` as a JSON array/table.
- Read the accepted KTSN from the JSON `KTSN` field.
- For defensive compatibility, the parser may accept the misspelling `KTNS`, but it must emit a validation warning.
- Look up the accepted KTSN in the CSV `ktsn` column.
- From the accepted row, display:
  - `KTSN Korean name` = accepted row `taxon_kor_nm`;
  - `KTSN scientific name` = accepted row `taxon_full_nm` after removing `<em>` tags; and
  - `KTSN` = accepted row `ktsn`.
- If accepted-name resolution fails, retain the direct match and visibly mark accepted-name data as unavailable.

**Assumption requiring confirmation:** because `taxon_jm_nm` is compared with `정명`, this draft treats it as a status field, not a Korean-name field. The accepted Korean name is therefore taken from the accepted row's `taxon_kor_nm`.

### 9.6 Occurrence-probability lookup

If the attached photo contains valid EXIF GPS coordinates:

1. For each top-three candidate, obtain the resolved `KTSN Korean name`.
2. Construct the expected filename:

```text
storage/reference/rasters/bce_inverse_corrected_probability_maps/
bce_inverse_corrected_probability_{KTSN Korean name}.tif
```

3. Open the matching raster if it exists.
4. Interpret EXIF longitude/latitude as WGS 84 (EPSG:4326).
5. Transform the coordinate to the raster CRS.
6. Confirm the point lies inside the raster extent.
7. Sample the pixel value at that location.
8. Treat NoData, missing files, invalid CRS, or out-of-extent points as unavailable, not as zero.
9. Display the valid value beside the Pl@ntNet confidence score as `Predicted occurrence probability`.

Probability values are assumed to be in the range 0–1 and should be displayed as percentages. Values outside 0–1 must trigger an asset-validation error unless raster metadata defines another documented scale.

If the photo has no GPS, show `No photo GPS — probability unavailable` and continue to show the top-three identification candidates.

### 9.7 Candidate selection and persistence

Each candidate card must display:

- Pl@ntNet scientific name;
- Pl@ntNet confidence;
- direct Korean-name match, when available;
- KTSN accepted Korean name;
- KTSN accepted scientific name;
- KTSN identifier;
- predicted occurrence probability, when available; and
- a concise warning for missing/ambiguous enrichment.

When the user selects one of the three candidates, persist at least:

- final Korean name;
- final scientific name;
- accepted KTSN when available;
- Pl@ntNet score;
- occurrence probability when available;
- identification status `complete`; and
- identification timestamp and API/model version when available.

The user must be able to reject all three candidates and enter a name manually. Manual identification must be marked as manual and must not silently inherit a candidate's confidence or probability.

## 10. Generated Folder and Transfer Workflow

The generated result must be a self-contained directory similar to:

```text
<project_name>/
  <project_name>.qgs
  <project_name>.qml                 # only when the QField plugin is enabled
  data/
    <project_name>.gpkg
  attachments/
    inventory/
    surveys/
    plots/
    observations/
  basemap/
    <offline_basemap>.mbtiles        # offline mode only
  reference/                         # only assets required at QField runtime
  README_TRANSFER_KO.md
  VALIDATION_REPORT.json
  MANIFEST.json
```

The exact folder names may be adjusted by the scaffold, but all references must remain relative and the folder must remain portable as a unit.

### Mandatory transfer notice

Generate a Korean end-user notice with the following meaning:

> Do not package this GeoPackage project with QFieldSync. QFieldSync packaging can replace primary-key behavior with `fid` and may remove or alter foreign-key-based relations. Copy the entire generated project folder, including the `.qgs`, `.gpkg`, attachments, plugin, reference assets, and offline basemap, directly to the smartphone. Open the local project in QField. After fieldwork, close the project and copy the entire folder back from the smartphone to the computer. Do not copy only the GeoPackage and do not rename or move files inside the folder.

Also explain Android and iOS file-transfer options in non-technical language and advise the user to keep a backup before replacing an older desktop copy.

## 11. Secrets and Privacy

- Mask VWorld and Pl@ntNet keys in the UI.
- Exclude keys from application logs, validation reports, analytics, crash reports, and screenshots generated by tests.
- Store the Pl@ntNet key outside the GeoPackage. Prefer the operating-system credential store or another existing scaffold-approved secret mechanism.
- If the QField runtime requires the Pl@ntNet key on the phone, disclose where it is stored and that folder recipients may be able to extract it. Do not claim that a client-side key is secret.
- Store the VWorld key in the generated project only when required for the runtime URL and only after the explicit warning in Section 8.1.
- Do not transmit survey database records to either external API.
- Remove EXIF data only if the user selects a privacy option; otherwise preserve it because GPS is required for probability lookup.

## 12. Validation and Acceptance Criteria

### 12.1 Database acceptance

- The generated GeoPackage opens in QGIS without a repair warning.
- Every domain UUID is valid, unique, and non-null.
- No domain relation references `fid`.
- `PRAGMA foreign_key_check` returns no rows.
- Geometry types and CRS match the selected survey template.
- Spatial indexes exist for all geometry layers.
- Cover values outside 0–100 are rejected.
- Required photo and completion constraints behave as specified.

### 12.2 QGIS/QField acceptance

- The `.qgs` opens with no missing-layer warning after the entire folder is moved to a different absolute path.
- Parent forms can create and display child records.
- UUID values are generated in both QGIS Desktop and QField and cannot be edited accidentally.
- Relation Reference widgets display human-readable names rather than UUIDs.
- Attachment paths are relative and remain valid after a computer → phone → computer round trip.
- Vegetation polygons switch between red and green hatch based on `is_field_checked`.
- The project opens in all explicitly supported QGIS and QField versions.

### 12.3 Basemap acceptance

- Online VWorld layers load with a valid key.
- Offline MBTiles coverage contains the approved bbox for every selected zoom level.
- MBTiles metadata contains the correct bounds, format, minimum zoom, and maximum zoom.
- The final `.mbtiles` file is no larger than 1 GiB.
- The MBTiles renders correctly in the supported QGIS and QField versions at representative locations and zoom levels.
- Cancelling generation leaves no partial deliverable in the final folder.

### 12.4 Identification acceptance

- A valid one-plant request returns and displays exactly the top three results.
- Results are ordered by descending Pl@ntNet score.
- `<em>` tags are removed correctly before matching/display.
- Accepted-name resolution follows `correct_list` and KTSN correctly.
- A synonym/non-`정명` fixture resolves to the accepted KTSN row.
- Missing, malformed, and multiple accepted-name entries are handled deterministically and visibly.
- EXIF WGS 84 coordinates are transformed to the raster CRS before sampling.
- NoData, no GPS, missing raster, and out-of-bounds cases display unavailable rather than zero.
- Selecting a candidate updates only the intended observation and preserves UUID relations.
- Offline requests queue without data loss and can be retried.

### 12.5 Portability acceptance

- Copy the generated folder to a new path and open it successfully.
- Copy it to a test smartphone, add/edit data and photos, close QField, copy the complete folder back, and open it successfully on desktop QGIS.
- No QFieldSync packaging step is required or invoked.
- `MANIFEST.json` identifies all required files and can detect a missing attachment, plugin, database, or basemap before transfer.

## 13. Failure Handling

- Never leave a partially generated project at the final output path.
- Write into a temporary build directory, validate, and atomically promote it to the chosen final directory.
- If the final directory already exists, do not overwrite it silently. Offer a new name or an explicit replace workflow with backup.
- Surface actionable errors for missing QGIS runtime, unsupported QGIS/QField version, invalid API key, malformed spatial upload, invalid CSV schema, invalid `correct_list` JSON, missing raster, offline-map size overflow, and disk-space shortage.
- A failure in optional Pl@ntNet validation must not destroy an otherwise valid project draft; it should allow the user to disable identification and continue.

## 14. Implementation Notes for the Spec Writer

These notes are requirements boundaries, not a mandated internal design:

- Prefer QGIS/PyQGIS and GDAL/OGR APIs for project, layer, geometry, raster, and form configuration.
- Do not handcraft a nominal `.gpkg` as an arbitrary SQLite file without also creating and validating required GeoPackage metadata.
- Do not assume a browser-only frontend can keep API keys secret.
- Treat the QField identification extension as a separate runtime component with its own compatibility tests.
- Pin and document the supported QGIS, QField, GDAL, and GeoPackage versions.
- Add fixtures for all four schemas, Korean text, synonym resolution, missing KTSN matches, EXIF with and without GPS, raster CRS transformation, and 1 GiB size-boundary behavior.
- The reference Word documents describe older sequence-based PostgreSQL examples. This specification overrides them with local GeoPackage storage and UUID domain identifiers.

## 15. Open Decisions to Confirm Before Implementation

1. Confirm that Type 1 requires at least one image for each of leaf, flower, and fruit, as drafted, rather than at least one image total.
2. Confirm that the accepted Korean name must come from the accepted row's `taxon_kor_nm`; `taxon_jm_nm` is treated only as the status field containing `정명`.
3. Confirm the exact JSON shape and capitalization used in `correct_list`, especially `KTSN` versus `KTNS`.
4. Confirm that occurrence raster values are probabilities in the range 0–1 and document their NoData value.
5. Confirm whether immediate in-field Pl@ntNet results are mandatory or whether post-field processing on the desktop is an acceptable fallback when a QField plugin capability is unavailable.
6. Confirm the supported QGIS and QField version matrix.
7. Confirm that VWorld licensing and API terms permit the intended offline MBTiles caching workflow.
8. Confirm whether all probability rasters must be available on the smartphone or whether probability enrichment may wait until the project folder returns to the desktop.

## 16. Reference Basis

This draft derives the initial domain schema and QGIS configuration from the supplied supporting documents:

- temporary plot: `site → survey → observation`;
- permanent plot: `site → plot → survey → observation`;
- vegetation map: `site → survey → community`;
- site/community MultiPolygon geometry and survey/plot Point geometry in EPSG:4326;
- QGIS relations, Drag and Drop Designer forms, Relation Reference, Range, Value Map, project properties, searchable display fields, and rule-based vegetation symbology;
- VWorld WMTS/XYZ setup; and
- direct whole-folder transfer due to the reported QFieldSync GeoPackage relation/key issue.

Current official behavior should also be checked against:

- QField attachment and multiple-photo documentation: <https://docs.qfield.org/how-to/project-setup/pictures/>
- QField relation/gallery documentation: <https://docs.qfield.org/how-to/project-setup/relation-reference-widget/>
- QField plugin documentation: <https://docs.qfield.org/reference/plugins/>
- Pl@ntNet identify API: <https://my.plantnet.org/doc/api/identify>
- QGIS `uuid()` expression: <https://docs.qgis.org/latest/en/docs/user_manual/expressions/functions_list.html>
- OGC GeoPackage feature-table key requirement: <https://www.geopackage.org/spec140/>
