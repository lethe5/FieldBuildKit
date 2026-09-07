# FieldBuild Standalone (0.1.0)

Independent repository, branch `main`; see [app identity and separation](independence.md).
This app replaces the installed-QGIS requirement in the earlier MVP specification.
No QGIS discovery, PyQGIS import,
or QGIS subprocess is used by the application build workflow.

## Run

```sh
.venv/bin/python -m pip install -e '.[ui,dev,packaging]'
.venv/bin/python -m qfield_builder.ui.app
```

The existing canonical workbook and probability raster inputs are still required. API key
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

The local macOS ARM64 trial bundle is `dist/FieldBuild Standalone.app` (0.1.0).
It is built in this independent repository. It includes the canonical reference
workbook, probability rasters/cache and independent GIS libraries. The bundle is unsigned for
distribution; its executable supports `--check-runtime` without opening the wizard.

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
