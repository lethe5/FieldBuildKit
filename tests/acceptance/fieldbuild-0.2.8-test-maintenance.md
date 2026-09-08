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
