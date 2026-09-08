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

Reference data is optional. A fresh clone can run and package the app with no `storage/`
folder and no private Excel/TIFF files. In wizard step 5:

- Choose a local taxonomy `.xlsx`, inspect its preview, then confirm it. Without a workbook,
  species fields remain editable and Pl@ntNet displays scientific-name candidates without KTSN
  matching. A selected invalid/changed file stops generation; it is never silently ignored.
- Download `taxonomy_sample.xlsx` for the expected 23-column, two-header-row `Data Sheet`
  layout. Its three rows (two accepted names and one synonym) are fictional, clearly labeled in
  the `안내` sheet, and are never automatically used in a project.
- Optionally choose a local probability TIFF folder. Files must be named
  `bce_inverse_corrected_probability_<Korean name>.tif`, single-band, share grid/CRS/data type,
  and use NoData `-9999`. Selected sources are validated and merged into a portable multiband
  TIFF inside the generated project. No source folder or old `storage` cache is modified.
  Without TIFFs, generation and photo identification work without occurrence probabilities.

The full `Rpt_2026-08-29_List.xlsx` and probability maps are user-owned local inputs, excluded
from the app and Git. Existing local files can be selected at their current locations. Existing
QField projects keep their embedded lookup tables and rasters. New projects carry only the
selected workbook's derived tables/provenance and the selected raster stack, not the raw workbook.

## Build on macOS or Windows

Use the current operating system's Python environment, with `.[ui,dev,packaging]` installed:

```sh
python packaging/build_app.py
```

Packaging uses a fresh PyInstaller work directory and `--clean`, then checks the finished
app's runtime. It requires no reference-data preparation, datasets or `QPB_*` source overrides.
`packaging/prepare_reference_bundle.py` remains a development utility for explicit legacy
reference fixtures, outside the app packaging path.

On Windows, create a native environment instead of using a copied macOS `.venv`:

```powershell
py -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -e ".[ui,dev,packaging]"
.\.venv-win\Scripts\python.exe packaging/build_app.py
```

Copy the entire output folder `dist/FieldBuild Standalone/` when distributing on Windows,
including `_internal/`; the `.exe` alone is not sufficient.

The existing macOS shortcut delegates to the same build entry point:

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
