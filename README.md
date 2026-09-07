# FieldBuild Standalone

An independent desktop application for creating ecological-survey projects for QField.
QGIS Desktop is not required. This repository starts a new Git history at version **0.1.0**.

The app uses QGIS-authored templates, SQLite, Rasterio and Fiona. Four survey types,
online/offline VWorld basemaps, photo identification and portable project folders are retained.

## Run

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[ui,dev,packaging]'
.venv/bin/fieldbuild-standalone
```

## Reference data

The canonical workbook candidate is tracked under `packaging/reference_source/tables/`.
The local independent copy in `storage/reference/` contains the workbook, probability rasters
and derived caches. Large datasets remain excluded from Git. When cloning elsewhere, supply
the approved rasters under `storage/reference/rasters/bce_inverse_corrected_probability_maps/`
and copy the canonical workbook to `storage/reference/tables/`.

Packaged apps include only the merged multiband probability TIFF and its band index, not the
individual source TIFFs. Source TIFFs remain local build inputs and are not deleted. The packaged
cache is checked against its TIFF hash, band metadata and source inventory; a missing or damaged
cache requires reinstalling/rebuilding the app, not downloading individual TIFFs at runtime.
New multiband TIFFs use lossless DEFLATE compression without changing probability values,
NoData, band mapping or spatial metadata.

## macOS build

```sh
bash packaging/build_macos_app.sh
"dist/FieldBuild Standalone.app/Contents/MacOS/FieldBuild Standalone" --check-runtime
```

The output is `dist/FieldBuild Standalone.app`, with a separate bundle identifier and credential
store. It can coexist with FieldBuild Kit. This is an unsigned local trial build; mobile QField
compatibility still requires device testing before release.
The app excludes Pillow (retained as an icon-generation build dependency), build-only artwork
copies and Qt translation catalogs other than Korean/English. UI images use Qt, and reference
workbooks are read as tabular data without spreadsheet image extraction.

## Checks

```sh
.venv/bin/python -m pytest -q tests/unit/test_standalone.py tests/unit/test_independent_identity.py tests/unit/test_credential_store.py tests/unit/test_app.py tests/unit/test_runtime.py tests/unit/test_validate_visibility.py
```

See [app separation](docs/independence.md) and [standalone implementation](docs/standalone.md).
The old specifications and acceptance traceability are retained as historical references.
The inherited full test suite has known report/wizard failures documented in the standalone notes.
