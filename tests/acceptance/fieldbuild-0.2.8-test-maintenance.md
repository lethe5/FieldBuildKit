# FieldBuild 0.2.8 test maintenance

Verified on Windows on 2026-09-08. Baseline: `a3d1af5`.
The user requested that this follow-up remain part of version **0.2.8**.

## Current expectations

- Type 4 community records support optional leaf, flower and fruit photos, one per field.
  There is no photo child table. When enabled, the identification widget displays candidates
  without writing observation identity fields. The wizard description must match this schema.
- Attachment and embedded-QML structural checks inspect the generated QGS XML directly.
  These checks do not claim that PyQGIS or a physical QField device has executed the project.
- With a taxonomy reference, derived scientific-name/KTSN values are not written as editable
  form attributes. Without a reference, the scientific-name field remains writable. Candidate
  selection and manual write-back are exercised as JavaScript, not inferred from old literals.
- The no-workbook GUI smoke fixture expects the no-reference schema, without `selected_ktsn`.
- Report fixtures support the current explicit SQL geometry projection. They supply small
  provider-shaped geometry objects; this is not a real SQLite/BLOB or large-geometry test.
- Report assertions identify rows by stable source ID, retain distinct zero/false values,
  expect generated latitude/longitude attributes, and recognize guarded renderer calls.
  Function extraction no longer assumes renderer declaration order.
- Mocked macOS packaging paths are normalized before comparison on Windows. This does not
  substitute for building or running the app on macOS.

## Verification

- Focused description, photo, QML, report, packaging, upload-performance and GUI suite:
  **70 passed** (`build/0.2.8-description-tests.log`).
- Optional workbook/TIFF combinations, relocated generated folders, standalone builds and
  final edited-test rechecks: **97 passed** (`build/0.2.8-final-generation.log`). These runs
  overlap; their counts must not be added as a unique-test total.
- Windows PyInstaller build succeeded. The final EXE's `--check-runtime` exited **0** from
  outside the repository. All three version declarations are `0.2.8`.
- Changed Python files: existing Ruff diagnostics **28 -> 24**, with no new diagnostics.
  `git diff --check` passed. Existing lint is not represented as clean.

## Separate pre-existing failures and limits

An expanded run of the three integrated-report acceptance modules changed from
**31 passed / 27 failed / 2 skipped** with the baseline fixture adapter to
**46 passed / 12 failed / 2 skipped** with the updated adapter. Every remaining failed test
also failed with the baseline adapter; no new failed test appeared. The baseline was loaded
in memory from Git, without reverting working files.

The remaining failures are in `test_html_report_integrated_data_map_summary_theme.py`
(AC001, AC004, AC007, AC010, AC011), `test_html_report_integrated_followup.py`
(AC002, AC005, AC013, AC017), and `test_html_report_integrated_followup_hardening.py`
(AC018, AC019, AC020). They involve historical ID-column/export expectations and source-text
contracts; they were not deleted, skipped, or declared resolved by this maintenance change.
Logs: `build/0.2.8-report-acceptance.log` and `build/0.2.8-report-acceptance-baseline.log`.

The previously recorded VWorld status-label layout failure is also outside this change.
This is scoped verification, not a claim that the entire repository suite is green or that
live APIs, macOS, or QField device behavior were retested. No remote release was published.

## TIFF streaming follow-up (same 0.2.8)

Baseline: `bef0289`. Branch: `codex/0.2.8-tiff-performance`.

- The standalone writer validates each open source immediately before copying its blocks,
  using the same metadata checks as the standalone validation API. It no longer performs a
  separate metadata-only pass or reopens the first source for its output profile. Only one
  input and the output remain open at a time; no unbounded dataset cache was introduced.
- Coordinate system, grid, data type, single-band and NoData checks remain mandatory.
  A late failure closes the output and discards staging without replacing a previous result.
- Lossless DEFLATE uses level 6 instead of 9. Both byte orders of BigTIFF are accepted by the
  source/cache header checks; Rasterio still validates actual source datasets.
- Focused streaming, optional-input, relocated-project, standalone and cache tests:
  **101 passed** (`build/0.2.8-tiff-tests.log`). New streaming tests pass Ruff; changed production
  files have **8 -> 7** existing diagnostics and no new diagnostics.
- Real supplied data: 2,531 matched single-band TIFFs, 184,975,604 decoded pixel bytes.
  The instrumented stack-only run changed from **40.025 s to 20.611 s** (about 48.5% faster),
  and source dataset opens from **5,063 to 2,531**. Pixel block reads remain **25,310**, one
  pass over source pixels. These are separate single runs on this Windows PC, not statistical
  benchmarks or end-to-end application timing.
- Output size changed from **47,004,745 to 49,008,181 bytes** (about 4.3% larger).
  A separate complete source/output crosscheck passed for every band, pixel and NoData value.
  That diagnostic took 61.879 s and is not added to the application's generation path.
- Original inputs were opened read-only. Diagnostic output was confined to temporary folders.
  Existing app builds were preserved; the updated build is in `dist/windows-0.2.8-tiff`.
- PyInstaller completed successfully and the new EXE's `--check-runtime` exited **0** from
  outside the repository. `git diff --check` passed.
- All version declarations remain **0.2.8**, as explicitly requested. QField/macOS/live-API
  execution and remote publication are not part of this follow-up.

## SHP upload preview follow-up (same 0.2.8)

Baseline: `90ff823`. Branch: `codex/0.2.8-shp-preview`.

- SHP/ZIP selection reads the SHP header, SHX/DBF count metadata and at most 50 attribute
  samples. It reuses the existing DBF decoder, with no new runtime dependency. Field-name
  discovery no longer reads all coordinates. Full geometry reads/validation remain in the
  build path; preview success is not full geometry validation.
- The GUI reuses samples when the name field changes, blocks duplicate combo population
  signals, and invalidates samples on file/encoding changes or clearing the selection.
- These small local metadata reads remain synchronous. Without both DBF and SHX, the
  fallback scans record headers; seeking in such a ZIP can still require decompression.
  This change does not claim constant-time previews for network drives or incomplete archives.
- Supplied `BND_SIDO_PG.shp`: 86,988,364 bytes, 17 regions, 5,433,279 coordinates.
  In the current UI code, selection changed from **12.848 s to 0.003239 s**; full geometry
  reads changed from **3 to 0**. Name mapping changed from **4.249 s to 0.000049 s**, with
  no further file read. These are individual Windows measurements, not packaged-EXE timings
  or statistical benchmarks. Original data was read-only.
- **132 passed** in the SHP/GPKG/optional-input/standalone regression run; **24 passed** in
  focused upload-page tests. Logs: `build/0.2.8-shp-regression.log` and
  `build/0.2.8-shp-wizard-focused.log`. The tests cover bounded reads, ZIP, CP949/UTF-8,
  missing sidecars, selection failures, and actual SHP/ZIP generation of all 75 sites despite
  a 50-row preview limit, followed by relocated-project validation.
- The old wizard test using a stub QGS still fails with `Project contains no layers` under
  both baseline and updated readers; it was not weakened. Baseline log:
  `build/0.2.8-shp-baseline.log`. A broader legacy fake-GPKG-path run also terminated in its
  Qt worker lifecycle; it is not counted as passed. This is not a full GUI-suite certification.
- Changed reader/helper/new-test files pass Ruff. The wizard retains its 13 existing
  diagnostics with no new diagnostics. `git diff --check` passed.
- Windows build: `dist/windows-0.2.8-shp`; previous builds preserved. The new EXE's
  `--check-runtime` exited **0** outside the repository. Version declarations remain **0.2.8**.
  No macOS/QField device/live-API run or remote release publication was performed.

## GPKG loading follow-up (same 0.2.8)

Baseline: `9a91007`. Branch: `codex/0.2.8-gpkg-loading`.

- Attribute previews already use a row limit and do not decode geometry. The redundant
  geometry walk was in offline-map extent selection. It now reads each feature's header
  extent and transforms the combined bounds from the source CRS into WGS84. Missing
  envelopes and collection geometries retain the existing full-decoder fallback. Full
  build-time geometry validation is unchanged; a successful preview is not validation.
- Source connections are read-only, including Unicode/URI-special-character paths. A
  nonexistent selected file no longer creates an empty SQLite file.
- Only one preview worker runs at a time; rapid changes retain only the latest pending
  request. A request ID rejects stale results even for A -> B -> A selection. Closing the
  wizard discards queued requests and waits for the active worker without blocking Qt.
- Supplied `BND_SIDO_PG.gpkg`: 87,314,432 bytes, 17 regions, EPSG:5186. Original standalone
  attribute preview: **0.0994 s**. Original extent calculation: **2.2876 s**, incorrectly
  returning projected coordinates as longitude/latitude. Updated extent calls in the UI
  process: **0.6461 s first call**, then **0.1135 / 0.1108 / 0.1123 s**. A separate cold
  process took **1.4438 s**, including first rasterio/PROJ imports. Do not describe the warm
  result as cold-start performance or as the speedup of the already-light attribute preview.
- Updated UI measurement: selection handler returned in **0.000265 s**, asynchronous
  completion in **0.7747 s**, name-field change in **0.000220 s**, with 17 preview rows.
  These are individual source-code Windows measurements, not EXE benchmarks. Header reads
  still scale with feature count/I/O; envelope-less geometries still require full parsing.
- Correct WGS84 extent: approximately **124.5891, 33.0286, 131.9578, 38.6216**.
  Actual-file generation completed in **7.0145 s**, retained all **17 sites**, and passed
  validation after moving the generated folder. Original size/mtime were unchanged. The
  temporary generated project was cleaned up, not retained as a release artifact.
- **137 passed** in the GPKG/SHP/optional-input/standalone regression run, including invalid
  headers/bounds/CRS, envelope fallback, Qt responsiveness, stale-result rejection, shutdown,
  and 75-feature GPKG generation despite the 50-row preview limit followed by relocation.
  Logs: `build/0.2.8-gpkg-regression.log`, `build/0.2.8-gpkg-real-generation.log`.
  Initial new-test mistakes (survey-type and destination-table names) were corrected and
  the complete scoped run was rerun; failed attempts are not counted as passed.
- Reader/helper/new-test files pass Ruff. Wizard diagnostics remain **13 -> 13**, with
  no new diagnostics. Previously recorded unrelated legacy failures remain separate; this
  is not a claim that the whole GUI/repository test suite is green.
- Windows build: `dist/windows-0.2.8-gpkg`, preserving previous build folders. Its EXE's
  `--check-runtime` exited **0** outside the repository. All three version declarations
  remain **0.2.8 -> 0.2.8**, explicitly requested. No macOS/QField/live-API execution,
  remote push, tag, or release publication was performed.

## Large-polygon HTML report follow-up (same 0.2.8)

Baseline: `09d7591`. Branch: `codex/0.2.8-large-report`.

- Root cause: the existing 512 KiB SQL/BLOB guard only covered direct GeoPackage access.
  The loaded-layer fallback could serialize the entire geometry to WKT/JSON, expand it into
  JavaScript coordinates, and duplicate it into the report. A JavaScript exception handler
  cannot recover from a native/V8 out-of-memory termination.
- The plugin now uses QField's native `ExpressionEvaluator` with the current feature/layer.
  QGIS counts vertices before serialization; above 16,384 vertices it bounds the geometry
  natively, then transforms the small rectangle to WGS84. Smaller shapes retain their rings
  and coordinates (WKT output precision: eight decimal places). The evaluator releases the
  current feature after every row. The original geometry/attributes are never edited.
  The API was checked against the [QField 4.2.4 evaluator header](https://github.com/opengisch/QField/blob/v4.2.4/src/core/expressionevaluator.h).
- This is **report-display approximation**, not geometry simplification in the saved project.
  Existing report limitation details disclose the approximate rectangles. Missing/invalid
  geometry stays in non-spatial records; native evaluation failures do not retry an unsafe
  full serialization. Legacy text serializers reject oversized strings before parsing.
- Fixed the hex-string branch in the byte/prefix readers: strings were previously treated
  as generic array-like values before their hexadecimal decoder could run. Test adapters
  now include the production WKT/prefix helpers instead of silently omitting them.
- Actual source: `BND_SIDO_PG.gpkg`, 87,314,432 bytes, 17 regions, EPSG:5186. A local QA run
  executed the emitted expression using installed QGIS 3.44.13 against all 17 real features,
  then supplied its native results/attributes to the emitted loaded-layer collector and HTML
  builder. This is an offline integration bridge, **not an actual QField application run**.
- The largest real feature has **2,604,179 vertices**. The old serializer, with its real WGS84
  WKT, terminated with **JavaScript heap out of memory**, exit **134**, in an isolated Node
  process limited to 128 MiB. The updated pipeline succeeded at the same limit: **17/17 valid
  map features**, **12 approximate rectangles / 5 detailed shapes**, HTML **5,309,699 bytes**,
  JavaScript heap **33,887,160 bytes after generation** (not peak/RSS). Source size/mtime stayed
  unchanged. Evidence: `build/large-report-qa/results.json`, `baseline-stderr.log`,
  `large-report.html`, and `build/0.2.8-large-report-real.log`.
- Focused report/plugin checks: **183 passed, 4 existing skips, 4 deselected**. Independent
  optional-input/build/relocation checks: **88 passed**. New executable tests cover guarding
  before serialization, releasing feature references, empty/failure/next-row distinction,
  retaining a small polygon hole, and decoding array/hex header envelopes.
- The four deselections were first run and failed with both current and baseline code:
  manual-entry write-back's historical KTSN expectation, plus three HTML source-text tests
  for renderer ordering, function ordering, and the old CSV `c.header` spelling. They remain
  failures, not fixed/skipped tests. Logs: `0.2.8-large-report-baseline-test.log`,
  `0.2.8-large-report-baseline-html.log`, `0.2.8-large-report-verified.log`, and
  `0.2.8-large-report-build-regression.log` under `build/`. The initial combined native/Qt
  run exited `-1073740791` before finishing; it is not counted as a pass. The same native
  termination reproduced with baseline production code in `0.2.8-large-report-baseline-combined.log`.
  Separate scoped processes completed as above; the underlying combined-process issue was
  not fixed here.
- New tests and production plugin pass Ruff; the other touched files have no additional
  Ruff diagnostics relative to baseline. `git diff --check` passed. An outdated constant-name
  assertion in the size-guard test was aligned with the existing QML property name.
- Windows build: `dist/windows-0.2.8-report`; EXE `--check-runtime` exited **0** outside the
  repository. Version declarations stay **0.2.8 -> 0.2.8**, as requested. Earlier builds and
  existing user projects/reports were not overwritten. Existing generated QML/HTML does not
  update just by replacing the builder EXE; new exports need the updated project plugin.
- Browser UI verification was blocked by the in-app browser's local-file URL security policy;
  no alternate browser/server workaround was used and no browser interaction is claimed.
  QField device/macOS/live API checks and remote publication were not performed.

## Exported report UI and native evaluator follow-up (same 0.2.8)

Baseline: `8fd3b4f`. Branch: `codex/0.2.8-report-ui`.

- The user's `w-type2-v0-2-8_report.html` contained 17 sites, one survey and two
  observations, but zero map features: all 18 spatial conversions reported failure.
  The earlier native-expression QA above returned a QVariantMap directly and therefore
  did **not** reproduce QField's actual API boundary. QField 4.2.4's
  [implementation](https://github.com/opengisch/QField/blob/v4.2.4/src/core/expressionevaluator.cpp)
  returns `value.toString()`. A map became an empty string. The expression now emits
  `to_json(map(...))`, and the collector parses only a size-limited JSON string.
  Native vertex limits, coordinate transformation, feature release and failure handling remain.
- Bar charts now label the Y axis `출현 횟수 (회)` / `평균 피도 (%)`. Cover chart and
  its accessible value table display Korean names only. Composite species identity remains
  in the aggregation/validation key; index-based bar positions avoid overlap when distinct
  taxa share a Korean name. Existing exported composite labels have a display-only fallback.
- Site/survey/plot disclosures were genuinely empty: the effective renderer only emitted
  a summary heading. They now contain escaped attribute tables, with existing Korean aliases
  and identifier-column filtering; empty datasets receive an explicit empty-state message.
- Map loading text is removed on both populated and empty results. Empty-state insertion
  no longer reconstructs Leaflet's DOM via `innerHTML +=`.
- Actual-file QA: native QGIS 3.44.13 evaluated the emitted **JSON-string** expression on
  saved project features. The shipped collector/HTML builder then ran in a 128 MiB Node heap.
  Output: `build/report-ui-qa/w-type2-v0-2-8_report-fixed.html`, **5,328,071 bytes**,
  **17 map features (12 approximate rectangles / 5 detailed boundaries)**; the exported
  one survey and two observations and the original taxonomy snapshot were preserved.
  Cover values: 나팔꽃 5, 주걱개망초 11. Heap after generation: **64,013,112 bytes**
  (not peak/RSS). Original report and GeoPackage size/mtime were unchanged.
- Important data limitation: the local saved project copy contains no survey/observation
  rows, unlike the supplied HTML. Its GeoPackage cannot recover that survey's missing
  coordinates. The repaired copy therefore honestly retains **one geometry failure**;
  it does not invent a position. Restoring that point requires the latest saved GeoPackage.
  This does not prevent the 17 recoverable site geometries from being included.
- Checks: **187 passed, 4 pre-existing skips, 4 deselected** in report/plugin tests;
  **88 passed** in independent optional-input/build/relocation tests. The same four previously
  documented baseline failures remain separate, not reported as fixed. Final focused run:
  **8 passed**, including QField string returns, numeric simplification flags, chart labels,
  duplicate Korean names, disclosure content/escaping and zero/nonzero map loading completion.
  All embedded scripts in the repaired HTML pass Node syntax checking. Changed Python files
  pass Ruff and `git diff --check`. No browser-rendering or QField application run is claimed.
- Windows output: `dist/windows-0.2.8-report-ui/FieldBuild Standalone`; packaged
  `--check-runtime` exited **0** outside the repository. All three declarations remain
  **0.2.8 -> 0.2.8**. Existing apps, projects and reports were preserved. Replacing the
  builder does not automatically update an existing project's QML or already-exported HTML.
  No macOS/live-service verification, push, tag or remote release was performed.

## Shape-preserving report boundary follow-up (same 0.2.8)

Baseline: `920156a`. Branch: `codex/0.2.8-report-boundaries`.
The user confirmed the other report UI fixes and requested actual boundary shapes instead
of bounding rectangles.

- Reused QGIS's native `simplify` (Douglas-Peucker) expression. Shapes with at most 16,384
  vertices remain unchanged apart from existing WGS84 conversion/output precision. Larger
  shapes start with a tolerance of 1/10,000 of their maximum bounding-box dimension, in
  their own CRS units. If necessary, three further passes double the tolerance and operate
  on the already reduced native geometry. Native serialization requires at most 32,768
  vertices; existing text-size checks also remain. A shape still exceeding the cap is
  disclosed as unavailable, never replaced by a box or serialized in full.
- Both loaded-feature collection and large saved-GPKG rows use the shared native path.
  Saved rows look up the loaded native geometry by the configured UUID, with expression
  literals escaped. SQL still avoids fetching large BLOBs. If no matching native layer/
  stable identity is available, the attribute row remains with a geometry limitation.
  Simplification is display-only, not a change to the project database. Independently
  simplified neighboring polygons are not guaranteed to form an exact shared-edge coverage;
  this display is not intended for measurement or topology editing.
- Larger shapes exposed four copies of the geometry in HTML: tables, map features,
  collection datasets and metadata rows. Removed the latter two unused HTML copies, retaining
  metadata/counts and the complete in-memory payload for native exports. Browser renderers
  already consume tables/map features. Regression coverage verifies the native payload is
  unchanged and canonical HTML records remain intact.
- Real source `BND_SIDO_PG.gpkg`: all 17 features passed the emitted native expression and
  real project-layer lookup. **5,433,279 -> 205,185 vertices**, maximum **28,266** per feature;
  maximum absolute relative area change **0.019018813%**, measured in original EPSG:5186.
  Small-feature vertex counts were unchanged. Source size/mtime remained unchanged.
  `build/report-boundary-qa/shape-results.json` records each region; `boundary-preview.png`
  was rendered with QGIS and visually inspected for boundaries/islands. This is a static
  cartographic QA image, **not a browser or QField application screenshot**.
- The supplied report's recovered site geometry now has no rectangular substitutes.
  HTML: **11,395,908 bytes**; generation succeeded in a **128 MiB Node heap** with
  **87,325,240 bytes** allocated after generation (not peak/RSS). Before removing duplicate
  HTML geometry, the shape-rich report failed the 128 MiB run; that attempt is not a pass.
  The previously missing survey position still cannot be recovered from the older local
  GPKG. Its single failure remains disclosed; the survey, two observations, cover statistics
  and reference snapshot are preserved. Original user HTML/GPKG were not overwritten.
- Report/plugin checks: **190 passed, 4 pre-existing skips, 4 deselected**. The four known
  baseline failures remain as documented above. Two initial source-signature test failures
  were corrected to locate the function by name rather than a fixed argument count; the
  entire scoped group was rerun successfully. Optional input/build/relocation: **88 passed**.
  New checks exercise native caps/no-box failure, direct-row UUID lookup/escaping, and
  HTML duplicate removal without changing native records. Embedded report scripts pass
  syntax checks; production/new geometry tests pass Ruff; legacy test-file lint debt remains.
- Build: `dist/windows-0.2.8-boundaries/FieldBuild Standalone`. Version declarations remain
  **0.2.8 -> 0.2.8**. Packaged `--check-runtime` exited **0** outside the repository.
  Prior outputs are preserved. Generated projects need the updated QML
  to use the new report exporter; replacing the builder alone does not patch existing files.
  Actual QField/browser/mobile/macOS checks and remote publication were not performed.

## Type 2/3 plot popup tables (same 0.2.8)

Baseline: `9da7ccd`. Branch: `codex/0.2.8-popup-tables`.

- Reused the existing Leaflet popup and logical-field readers. Survey/plot anchors now show
  available site/plot names above a table with `번호`, `조사일`, `조사자`, `국명`, `학명`.
  One observation is one row; each observation retains its own survey context. No merging,
  sorting, record truncation, identifier exposure or changes to source records/CSV occur.
  Missing values show an em dash; empty plots show an explicit no-observations message.
  Site-name-only and Type 1 observation popups retain their existing behavior.
- Added scoped popup styles: row borders/striping, sticky column headings, keyboard-focusable
  scrolling and a bounded table height. Plot popup dimensions are capped by the map size;
  wide tables scroll horizontally on narrow screens. The general report table minimum width
  does not override the popup's narrower table rule. Existing theme variables are reused.
- Removed a duplicate popup renderer definition, leaving one effective implementation in the
  generated script. Initial tests exposed the older duplicate taking precedence; that result
  was corrected before rebuilding. Tests also now recognize a single column heading and the
  additional Leaflet size-options argument rather than expecting the old repeated text.
- Report/plugin checks: **196 passed, 4 pre-existing skips, 4 deselected**. The same four
  previously documented baseline failures remain separate. Optional-input/build/relocation:
  **88 passed**. New executable tests cover 120 rows for both anchor types, mixed survey
  contexts, missing names, HTML escaping, input immutability, empty plots, unchanged other
  popups and 240/900-pixel map widths. Shipped embedded scripts pass syntax checks.
- `build/popup-qa/popup-preview.html` uses the emitted popup functions/styles with synthetic
  Type 2 (four rows) and Type 3 (three survey dates, twelve rows) examples. This is a static
  layout preview, not evidence of an actual browser/QField interaction. Production and new
  UI tests pass Ruff; legacy test-file lint debt is unchanged. `git diff --check` passed.
- Build: `dist/windows-0.2.8-popup/FieldBuild Standalone`; `--check-runtime` exited **0**
  outside the repository. All three declarations remain **0.2.8 -> 0.2.8**. Earlier apps,
  projects and reports were preserved. Existing projects need the updated generated QML,
  followed by report re-export; installing the builder does not alter old QML/HTML files.
  No dependency was added. No browser/QField/macOS/live-service run or remote publication
  was performed.

## Scientific-name chart fallback and cover form units (same 0.2.8)

Baseline: `fb849a5`. Branch: `codex/0.2.8-species-labels`.

- Species occurrence and mean-cover charts use one display rule: trimmed Korean name,
  otherwise trimmed scientific name, otherwise `미동정`. The accessible value tables use
  the same rule. The X-axis title is now `종명 (국명/학명)`. Internal species identity,
  aggregation keys, counts and cover values are unchanged; identifiers are not a name fallback.
- Cover statistics retain separate Korean/scientific display fields. The existing composite
  key remains intact. Legacy composite-label payloads (including the old `국명 미입력`
  placeholder) also support scientific-name fallback. Species data itself is not overwritten.
- Changed the common observation `cover` alias and both Type 2/3 packaged QGS templates
  to `피도(%)`. Updated matching unit/acceptance expectations. This is a display-alias change,
  not a renamed database column or conversion of stored numeric values.
- Checks: **210 passed, 4 pre-existing skips, 4 deselected** in the report/plugin/alias group;
  the four baseline failures remain as documented above. Independent optional-input/build/
  relocation tests: **88 passed**, now also asserting `피도(%)` in real generated QGS files
  while QGIS imports/bridge calls are forbidden. New chart tests cover null, missing and
  whitespace-only names, Korean priority, scientific fallback, both names missing, legacy
  labels, consistent value tables and input immutability. All four survey types' embedded
  report scripts pass syntax checks. Changed production/unit files pass Ruff and diff checks.
- Windows build: `dist/windows-0.2.8-labels/FieldBuild Standalone`; packaged
  `--check-runtime` exited **0** outside the repository. All three version declarations stay
  **0.2.8 -> 0.2.8**. Existing generated projects/reports remain unchanged: form aliases need
  updated project settings, and reports need the updated QML followed by re-export.
  No new dependency, browser/QField/macOS/live-service execution or remote publication.
