# FieldBuild Kit

[한국어](README.md) · **English**

A desktop application for **creating ecological field-survey projects for QField without
installing QGIS Desktop**. Its Korean-language wizard configures survey types, basemaps and
optional reference data, then generates a project folder with forms and relationships.
This guide describes **app version 0.2.8**.

## Install and run

Check the files attached to the relevant version on
[GitHub Releases](https://github.com/lethe5/FieldBuildKit/releases).
Choose a package matching your operating system and CPU architecture. GitHub's `Source code`
archives contain source files, not a runnable app bundle.

- **macOS**: Extract the distribution archive, move `FieldBuild Kit.app` to Applications
  and open it. The currently verified local build targets Apple Silicon (ARM64).
- **Windows**: When a release provides a Windows package, extract it and run
  `FieldBuild Kit.exe` while keeping the entire folder, including `_internal`.
  Moving only the executable will not work. Native Windows build instructions are below;
  consult the release notes for actual package availability and verification status.

The packaged app requires **no separate Python, QGIS Desktop or GDAL installation**.
The current macOS build has no distribution Developer ID signature or notarization.
If macOS blocks it because the developer cannot be verified, confirm its source and follow
[Apple's instructions for opening apps](https://support.apple.com/ko-kr/102445).

Install **QField separately** on the device used for fieldwork. See the
[official QField installation guide](https://docs.qfield.org/get-started/)
for Android, iOS and desktop installations.

## Create a project

1. **Project basics**: Set the name, parent output folder and coordinate systems.
2. **Survey type**: Choose one of the four types below.
3. **Sites and plots**: Draw boundaries or upload local spatial data where needed.
   Simple species inventories skip this step.
4. **Connectivity and basemap**: Choose no basemap, online VWorld or offline VWorld.
5. **Photo identification and references**: Enable Pl@ntNet if needed and optionally select
   a taxonomy workbook and probability TIFFs. Projects can be created without references.
6. **Symbol styling**: Choose point symbols. Vegetation mapping skips this step.
7. **Review and build**: Review the settings and generate the project folder.

| Survey type | Recording structure |
| --- | --- |
| Simple species inventory | Point observations with locations and species, without site boundaries |
| Temporary plots within sites | Site → survey → observation, with survey locations and species cover |
| Permanent plots within sites | Site → fixed plot → survey → observation, supporting repeat visits |
| Vegetation mapping | Site → survey → community, recording vegetation as polygons |

## Taxonomy reference — optional

In step 5, upload an **Excel `.xlsx` national vascular-plant species list including synonyms**.
The app previews and validates the selection, then applies a valid workbook automatically.
Replace or clear an invalid workbook before proceeding.

> **Uploading the reference restricts plant-name entry to accepted names in the national species list.**

- **With a workbook**: Accepted-name selection provides scientific-name and KTSN lookup.
  Survey types that record species observations include a KTSN field.
- **Without a workbook**: Enter Korean and scientific names manually. **No KTSN field is
  generated.** Pl@ntNet provides scientific-name candidates without KTSN matching.
- **Sample download**: Use the app's `가상 샘플 Excel 다운로드...` button to inspect the format.
  The [same sample workbook](resources/samples/taxonomy_sample.xlsx) is included in this repository.
  Its `Data Sheet` has 23 columns and two header rows. The two accepted taxa and one synonym
  are **fictional**; read the `안내` instruction sheet. The sample is never applied automatically.

The raw workbook is not copied into the project. Only derived lookup tables and provenance
are included. If the source changes after validation, upload it again.

## Occurrence-probability TIFFs — optional

The TIFF folder selector appears **only when Pl@ntNet photo identification is enabled and a
valid taxonomy workbook has been uploaded**. Removing either prerequisite clears the TIFF
selection. Without TIFFs, project creation and photo identification still work; occurrence
probability lookup is omitted.

- The selected folder and its subfolders are searched for `.tif` and `.tiff` files;
  extension matching is case-insensitive.
- **Each filename must contain a Korean name from the uploaded workbook.** Examples:
  `소나무.tif` and `지역_소나무_2026.tiff`. No fixed prefix such as
  `bce_inverse_corrected_probability_` is required.
- A more specific name takes precedence over a contained shorter name. Unrelated names in
  one filename or multiple files for the same species produce an error. Files without a
  matching workbook name are excluded.
- Inputs must be **single-band** and share dimensions, grid, CRS and data type.
- **NoData may be `-9999` or `NaN`**, including a mixture across input files. Generation
  normalizes NaN cells to `-9999`, preserving other values and the original files.

Selected TIFFs become a project-local multiband TIFF. The full national species list,
probability TIFFs and `storage/` caches are excluded from the app and Git. The app still
includes Qt UI components and GIS libraries, which account for much of its size.

## API keys and connectivity

| Feature | Requirements |
| --- | --- |
| Online VWorld basemap | VWorld API key and internet access during use |
| Offline VWorld basemap | VWorld API key and internet access during generation; the generated area and zoom range work offline in the field |
| Pl@ntNet photo identification | Pl@ntNet API key and internet access when requesting identification |
| Local probability lookup | TIFFs included under the conditions above; raster sampling itself needs no internet |

Choosing `이 키 기억하기` stores the API key in this computer's encrypted credential store.
Unlock it with the password established in the app. A forgotten password cannot recover
previously stored keys.

**Encrypted computer storage and embedding keys in a project are separate choices.** Online
VWorld and Pl@ntNet keys embedded with consent can be read by anyone who receives the project
folder. Declining Pl@ntNet key embedding preserves the identification feature, but a key must
then be configured directly in QField before use. Requesting photo identification sends the
selected photos to the Pl@ntNet service.

## Transfer to QField and export reports

Copy the **entire generated project folder** to the QField device and open its `.qgs` file.
Do not transfer only the `.qgs` or `.gpkg`. **Do not repackage these projects with QFieldSync.**
After fieldwork, close the project in QField and copy the entire folder back to the computer.
Each project includes `README_TRANSFER_KO.md` with Korean transfer instructions.

A project contains the following files; some folders depend on the selected features.

```text
project-folder/
├── project.qgs              # Open in QField
├── project.qml              # Project features and report tools
├── data/                    # Survey GeoPackage
├── attachments/             # Attached photos
├── icons/                   # Tool icons
├── reference/               # Optional taxonomy/probability references
├── basemap/                 # Optional offline basemap
├── MANIFEST.json            # Project inventory
├── VALIDATION_REPORT.json   # Generation-time validation
└── README_TRANSFER_KO.md    # Device transfer instructions
```

QField's **HTML 보고서 내보내기** action writes `project_report.html` and `project_joined.csv`
to the project folder. The HTML offers a searchable, sortable joined table and an additional
CSV download. Joined tables and CSVs use Korean headers and omit displayed UUID, foreign-key
and integrity-status columns. Internal identities remain available for relationships and
missing-parent diagnostics.

Rows whose final geometry is a point include **WGS84 decimal latitude and longitude to eight
decimal places**. Missing or untransformable coordinates remain blank; no centroid coordinates
are invented for polygons. App updates apply to **newly generated projects** and do not
modify existing projects automatically.

## Run from source and package

These instructions are for developers. The project declares **Python 3.10 or later**;
the current local verification environment uses Python 3.12. Run commands from the downloaded
repository. Neither `storage/` nor private reference data is required.

### macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[ui,dev,packaging]'
.venv/bin/fieldbuild-kit

# Build the distributable app and check its runtime
.venv/bin/python packaging/build_app.py
```

The output is `dist/FieldBuild Kit.app`. The separate `dist/FieldBuild Kit/`
build output need not accompany the macOS app. `bash packaging/build_macos_app.sh` invokes
the same build workflow.

### Windows PowerShell

```powershell
py -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -e ".[ui,dev,packaging]"
.\.venv-win\Scripts\fieldbuild-kit.exe

# Build natively on Windows
.\.venv-win\Scripts\python.exe packaging/build_app.py
```

Distribute the entire `dist/FieldBuild Kit/` output folder. Create a fresh environment
on the target operating system instead of copying another operating system's virtual environment.

Packaging uses a fresh PyInstaller work directory and runs `--check-runtime` on the completed
executable. No reference-data preparation or special `QPB_*` environment overrides are needed.

### Development checks

Run the related automated checks on macOS with the command below. Tests that execute generated
report JavaScript also require a `node` executable.

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/unit/test_optional_reference_inputs.py tests/unit/test_standalone.py tests/unit/test_probability_raster_cache.py tests/unit/test_wizard_ui_layout.py tests/unit/test_file_dialog_navigation.py tests/acceptance/qfield_project_builder/test_fieldbuild_kit_qfield_html_report_refresh.py
```

Structural validation and automated tests are separate from actual QField device verification.
Some DPI/mobile checks require separate environments, and the inherited full suite retains
known failures. See the [verification record](docs/qfield-runtime-verification.md) for tested
scope and limitations.

## Further reading and support

- [Korean README](README.md)
- [Standalone implementation and change history](docs/standalone.md)
- [App separation background](docs/independence.md)
- [Verification record](docs/qfield-runtime-verification.md)
- [Report an issue](https://github.com/lethe5/FieldBuildKit/issues): Include app, operating
  system and QField versions with reproduction steps. Do not post API keys or personal data.

The `specs/` directory and older acceptance documents also retain requirements from earlier
implementations. Refer to this README and the latest change notes for current user-facing behavior.
