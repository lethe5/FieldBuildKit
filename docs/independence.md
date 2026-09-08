# Independent application

This independent application began as FieldBuild Standalone at version 0.1.0.
From 0.2.8, its product name is **FieldBuild Kit** and its repository is
[lethe5/FieldBuildKit](https://github.com/lethe5/FieldBuildKit).
Its initial source snapshot was derived from FieldBuild Kit commit
`b7c6c14` (QGIS-free experimental branch). The original repository and installed app are retained.
The inherited `qfield_builder` Python package name and QPB survey-format identifiers remain
internal compatibility details; no import, symlink, Git worktree or submodule points to the
original repository.

| Identity | Independent value |
| --- | --- |
| App name | FieldBuild Kit |
| Python distribution / command | fieldbuild-kit |
| macOS bundle ID | kr.re.nie.fieldbuild-standalone |
| Initial version | 0.1.0 |
| macOS app data | ~/Library/Application Support/FieldBuild Standalone |
| Windows app data | %APPDATA%/FieldBuild Standalone |
| App-data override | FIELDBUILD_STANDALONE_APP_DATA_DIR |

The bundle ID, app-data directory, diagnostic environment variable and encrypted-store verifier
retain their existing values across the 0.2.8 product rename. Existing users keep their password
and remembered API keys without migration or re-entry. These are internal compatibility
identifiers, not the displayed product name.

The application never automatically reads or imports credentials from the original source
application (also named FieldBuild Kit) or QField Project Builder. A fresh installation
establishes its own password and remembered API keys.

The local reference raster collection, filtered lookup data and probability cache were copied
as independent regular files into `storage/reference`; no hard links or source-repository
dependencies are used. From 0.2.0 these files are optional project inputs and remain excluded from Git.
The full canonical workbook and its pinned manifest are no longer tracked or packaged.
A fresh clone can run and package the app without provisioning any reference data.
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
