# Independent application

FieldBuild Standalone starts at version 0.1.0 with a fresh local Git repository and no remote.
Its initial source snapshot was derived from FieldBuild Kit commit
`b7c6c14` (QGIS-free experimental branch). The original repository and installed app are retained.
The inherited `qfield_builder` Python package name and QPB survey-format identifiers remain
internal compatibility details; no import, symlink, Git worktree or submodule points to the
original repository.

| Identity | Independent value |
| --- | --- |
| App name | FieldBuild Standalone |
| Python distribution / command | fieldbuild-standalone |
| macOS bundle ID | kr.re.nie.fieldbuild-standalone |
| Initial version | 0.1.0 |
| macOS app data | ~/Library/Application Support/FieldBuild Standalone |
| Windows app data | %APPDATA%/FieldBuild Standalone |
| App-data override | FIELDBUILD_STANDALONE_APP_DATA_DIR |

The application never automatically reads or imports credentials from FieldBuild Kit or
QField Project Builder. First launch establishes its own password and remembered API keys.

The local reference raster collection, filtered lookup data and probability cache were copied
as independent regular files into `storage/reference`; no hard links or source-repository
dependencies are used. Reference data remains excluded from Git. The canonical workbook
candidate and its hash manifest remain tracked in `packaging/reference_source`.
A fresh clone on another computer must provision the raster collection before packaging.
No user uploads, generated survey projects, real .env files, credentials, virtual environment
or old build outputs were imported.

Inherited `specs/` and acceptance traceability documents describe the source application's
history. For current runtime behavior use `docs/standalone.md`; for independent app identity
use this document. Legacy requirements to migrate credentials are superseded here.

Validation includes QGIS-free project-generation tests, credential-isolation tests,
independent package metadata and the packaged app's `--check-runtime` command.
In this repository's own virtual environment, 96 focused tests and 3 wizard-branding tests
passed. The CLI runtime check and `pip check` passed as well.
The inherited report/wizard test issues documented in `docs/standalone.md` remain separate.
