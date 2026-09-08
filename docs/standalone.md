# FieldBuild Kit

Independent repository, branch `main`; see [app identity and separation](independence.md).
This app replaces the installed-QGIS requirement in the earlier MVP specification.
No QGIS discovery, PyQGIS import,
or QGIS subprocess is used by the application build workflow.

## Run

```sh
.venv/bin/python -m pip install -e '.[ui,dev,packaging]'
.venv/bin/python -m qfield_builder.ui.app
```

Local taxonomy workbooks are optional. From 0.2.5, optional probability TIFFs require both
Pl@ntNet photo identification and a selected, validated taxonomy workbook.
A fresh clone and app packaging need no `storage` assets. API key
consent, encrypted key retention, survey choices, uploads, and the generated QField plugin are
unchanged. QField is still required on the field device.

## What runs locally

- GeoPackage and MBTiles creation reuse the existing SQLite implementation.
- Four QGIS-authored templates preserve forms, field constraints, aliases, relationships,
  display expressions and styles. The writer adjusts paths, optional layers, CRS, keys and SVG
  markers. Identification QML comes from the existing shared renderer.
- Fiona transforms uploaded geometries; Rasterio creates and reads probability stacks. These
  wheels supply their own GIS libraries; the user does not install QGIS or a separate GDAL SDK.
  Stacks are written in windows to avoid loading an entire source raster into memory.
- Validation checks local layer sources, schema fields, relations, lookup references,
  visibility, rasters, manifest files and database integrity. It reports `structure_valid` and
  `qgis_open_checked: false`; `opens_without_repair_warning` is null because opening in QGIS
  was not attempted. Failed structural validation prevents publication of the build.

The old PyQGIS exporter and inspection helpers remain for development and comparison. They are
not runtime fallbacks. They cannot rescue a missing or broken standalone dependency.

## Trial build and verification

The local macOS ARM64 trial bundle is `dist/FieldBuild Kit.app` (0.2.8).
It is built in this independent repository. It includes the small fictional workbook sample and independent GIS libraries; private
workbooks, probability rasters and caches are excluded. The bundle is unsigned for
distribution; its executable supports `--check-runtime` without opening the wizard.

In 0.2.1, macOS file uploads use a Qt file picker to work around native open panels that
ignore folder double-clicks. Excel, site and offline-extent uploads share this picker.
Path entry remains available without the completion popup, which caused a Cocoa accessibility
crash during verification. Save dialogs and directory pickers retain their existing behavior.
Verification: 66 related tests passed (4 unrelated DPI variants skipped), including real
dialog navigation into a Korean-named folder, file selection/cancellation and platform fallback.
The macOS GUI check also reached the sample workbook preview and enabled Next after confirmation;
the packaged runtime check passed. No generated-project behavior changed in that fix.

From 0.2.2, a valid taxonomy upload is immediately ready for generation; the separate
confirmation button is removed. Selecting an earlier upload also revalidates it automatically.
Invalid uploads block progression until replaced or cleared, and the build still checks the
validated file hash. Cancelling the picker preserves the previous selection.
Verification: 90 related tests passed; 8 cases were skipped (4 separate-process DPI variants
and 4 optional private-workbook cases). In the macOS test app, selecting the sample workbook
displayed the preview and validation-success message with Next enabled immediately and no
confirmation button. The 0.2.2 bundle build and packaged runtime check passed.

From 0.2.3, generated projects store an initial and full map extent in the selected project
CRS, using survey geometry, then offline map coverage, then Korea as the fallback. This avoids
opening worldwide imagery at an unsuitable scale in EPSG:5186. Verification and the user's
confirmation are recorded in `docs/qfield-runtime-verification.md`.

From 0.2.4, file uploads again use the platform-native file picker, matching step 1's native
directory picker. Report tables and both CSV exports omit UUID/FK and integrity display columns,
coalesce repeated hierarchy aliases, and use Korean headers. Internal identities and missing-parent
diagnostics remain available. Point-based rows include latitude/longitude in WGS84 decimal degrees
with eight decimal places; absent, invalid, untransformable, and non-point geometry never produces
invented coordinates. This applies to projects generated with the new app. The user confirmed
verification of the delivered build; evidence is recorded in `docs/qfield-runtime-verification.md`.

From 0.2.5, the TIFF folder selector appears only while photo identification is enabled and a
valid taxonomy workbook is selected. Disabling identification or clearing/invalidating the
workbook clears the TIFF selection. Without a workbook, generated GeoPackages, QGIS forms and
report definitions omit `selected_ktsn`; Korean and scientific names remain editable.

TIFF filenames must contain a Korean name from the selected workbook, such as `소나무.tif` or
`지역_소나무_2026.tiff`; no fixed prefix is required. Subfolders and case-insensitive `.tif`/`.tiff`
extensions are supported. Names are Unicode-normalized; a longer containing species name takes
precedence, while unrelated multiple matches and duplicate files for one species are rejected.
Files without matching names are excluded. Inputs must remain single-band and share a grid,
CRS and data type. NoData may be -9999 or NaN, including mixed input files. Generated stacks
normalize NaN to -9999 while preserving valid values and leaving source files untouched.
From 0.2.6, the taxonomy upload box permanently displays the instruction to upload the national
vascular-plant species list including synonyms; validation and clear-selection messages do not
replace this instruction.
From 0.2.7, this fixed notice also warns that uploading the reference restricts plant-name
entry to accepted names in the national species list.

Standalone tests pass with QGIS and OSGeo imports forbidden. In the source branch before
repository separation, all 24 generated project combinations were separately opened by
isolated QGIS 3.44.13: layers, relations and renderers
were valid. This is desktop compatibility evidence, not an iOS/Android field test.

The broader repository suite is not green: 12 failures in the existing canonical-widget/HTML
report tests and the first wizard failure (`progress_updated` missing from a test double) were
also reproduced from the source repository's untouched `main` snapshot. The unrestricted wizard run additionally
aborted during an upload-preview thread teardown. Those pre-existing areas were not rewritten
as part of this runtime experiment.

## Templates and regression checks

Template files are package data in `qfield_builder/templates/` and are included in wheels and
PyInstaller bundles. They contain no credentials, survey records or developer profile paths.
Refresh them whenever schema, relation, widget or style configuration in the developer exporter
changes. Changes to shared QML are picked up at project creation time.

```sh
# Developer machine only, with QGIS installed. The probe isolates the real QGIS profile.
.venv/bin/python scripts/qgis_isolated_probe.py --code scripts/export_project_templates.py
.venv/bin/python -m pytest -q tests/unit/test_standalone.py
```

The standalone test suite forbids QGIS/OSGeo imports and bridge calls and builds all 24
survey/basemap/identification combinations, checks relocation, missing files, key escaping,
MBTiles readability, probability pixels and projected uploads. The development-only
`verify_template_compatibility.py` can read those outputs back using isolated QGIS.

This changes the historical runtime and validation contracts; tests asserting QGIS discovery
or a real QGIS open during normal generation must use the new standalone contract. Legacy
QGIS-inspector acceptance tests are development compatibility checks, not prerequisites on an
end user's machine. Mobile QField behavior still needs a real-device smoke test before release.

Independent-library API references: [Rasterio windowed I/O](https://rasterio.readthedocs.io/en/latest/topics/windowed-rw.html)
and [Fiona manual](https://fiona.readthedocs.io/en/stable/manual.html).
