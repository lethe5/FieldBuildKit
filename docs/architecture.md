# Architectural Decisions

Current application: **FieldBuild Kit**, an independent, QGIS-free app.
See [current runtime](standalone.md) and [independent app identity](independence.md).
The records below are inherited source-project history; their QGIS installation and
credential-migration requirements do not apply to this app.

> Owned and updated by: spec-writer (in consultation with the user)
> Scope: architectural decisions shared across more than one feature. Feature-specific implementation detail belongs in that feature's spec or in the implementer's code, not here.

## How to use this file

- Record a decision here only once the user has explicitly made or confirmed it.
- Use a lightweight decision-record style per entry: the decision, the date, the reason, and any alternatives considered.
- Cross-cutting concerns relevant to a QField-building tool (e.g. how QGIS/QField project files are represented, offline-first data capture, coordinate reference systems, sync strategy) belong here once decided — not before.

## Deployment and runtime architecture (2026-08-10)

Source: explicit stakeholder decision recorded in `specs/qfield-project-builder.md` (Draft;
Decision Log D-9 through D-11, D-19). This is the first application-technology decision made for
this repository; it replaces the earlier "no technology stack chosen" placeholder for this
product below.

- **Application type**: a locally installed, single-user **native desktop application**, not a
  browser-based or server-hosted web application. There is no remote application server and no
  PostgreSQL or other remote database.
- **UI technology**: Python + PySide6/Qt.
- **Supported desktop platforms**: Windows and macOS, both first-class at the source/packaging-
  configuration level (no platform-only assumption may be introduced into either). For the MVP
  release, macOS is the first platform actually packaged and delivered as a built artifact; a
  built Windows installer/executable is a required subsequent-release task, explicitly deferred
  by direct stakeholder instruction (see `specs/qfield-project-builder.md` Decision Log D-25).
- **Process separation**: the PySide6 UI runs in its own process. All QGIS/PyQGIS/GDAL
  operations (GeoPackage creation, QGIS project generation/configuration, layer/relation/form
  setup, offline MBTiles generation) run in a separate local GIS worker process, using the
  Python/PyQGIS environment supplied by a QGIS Desktop installation detected on the user's
  machine. The worker initializes `QgsApplication` headlessly (no QGIS GUI) and exchanges jobs,
  progress, results, warnings, and errors with the UI process. This separation exists because the
  UI and the QGIS runtime may use different Qt Python bindings/versions; no data is sent to a
  remote worker or server. The exact inter-process communication mechanism is not yet decided
  (see the open question in `specs/qfield-project-builder.md`, Open Question O-1).
- **QGIS/PyQGIS runtime dependency**: the minimum supported runtime is **QGIS 3.44**, with all
  later QGIS Desktop versions eligible on both Windows and macOS. QGIS Desktop is a host
  dependency detected at runtime (with manual override), not bundled by the application
  installer in the MVP. PyQGIS must not be installed separately (e.g. via `pip`); it is supplied
  by the detected QGIS Desktop installation. QGIS 4.x is not an MVP target. The exact
  tested patch/OS/GDAL/QField version matrix is a release-gate item, tracked in
  `specs/qfield-project-builder.md`.
- **Mobile field-device support**: generated projects must work with QField on both iOS and
  Android; iOS is the primary field-validation platform, but the product must not rely on
  iOS-only behavior or exclude Android.
- **Storage**: because this is a local, single-user desktop application with no server
  component, the storage locations described below (`REFERENCE_DATA_DIR`, `UPLOAD_DATA_DIR`,
  `WORK_DATA_DIR`, `GENERATED_PROJECT_DIR`) resolve to plain local filesystem paths on the user's
  own machine for this product. The previously open question of mapping these same variable
  names to Docker volumes, bind mounts, or object storage does not apply to this local desktop
  deployment; it may still be relevant if a different, server-hosted product is ever built on
  this same repository convention, but that is not this product's deployment model.

## File and storage structure

This is a repository-layout convention, not a storage-backend decision — no backend has been
chosen (see the open question at the end of this section).

1. Small, immutable application resources — QGIS/QField project templates, `.qml` styles, survey
   schema / form-definition files — live under `resources/` and are version-controlled.
2. Small, deterministic test data lives under `tests/fixtures/` and is version-controlled.
3. Large datasets and anything generated or uploaded at runtime live under `storage/` and are
   excluded from Git (see `.gitignore`); only `.gitkeep` placeholders are tracked there, to keep
   the directory structure itself represented in the repo.
4. Application code must obtain storage locations from configuration/environment variables (see
   `.env.example`: `REFERENCE_DATA_DIR`, `UPLOAD_DATA_DIR`, `WORK_DATA_DIR`,
   `GENERATED_PROJECT_DIR`), never from hard-coded absolute paths.
5. `storage/reference/`, `storage/uploads/`, and `storage/projects/` hold persistent data and
   should be included in the deployment backup policy (once one exists).
6. `storage/work/` holds reproducible, temporary intermediate files and may be cleaned according
   to a retention policy rather than backed up.
7. Deployed environments may map these same configured paths to Docker volumes, bind mounts,
   dedicated server storage, or an object-storage-backed implementation — which of these to use
   is a separate, not-yet-made decision and does not affect this structure or the variable names.

Layout:

```text
resources/
├── qgis-templates/   # immutable QGIS/QField project templates shipped with the app
├── styles/           # version-controlled .qml styles and presentation resources
└── schemas/          # version-controlled survey schema / form-definition resources

tests/fixtures/
├── rasters/          # small raster files used only by automated tests
└── vectors/          # small vector files used only by automated tests

storage/
├── reference/
│   ├── rasters/      # production/local reference raster datasets
│   └── vectors/      # production/local reference vector datasets
├── uploads/          # original user-uploaded files
├── work/             # temporary, reproducible intermediate processing files
└── projects/         # generated QField project packages and related outputs
```

**Open question (not decided here):** whether reference rasters are copied into offline QField
packages as-is, transformed/tiled, or exposed through an online map service is an unresolved
product requirement, to be settled through the spec-driven workflow rather than assumed by
directory layout.
