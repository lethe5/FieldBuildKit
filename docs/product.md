# Product Requirements

> Owned and updated by: spec-writer
> Scope: requirements shared across more than one feature specification. Feature-specific requirements belong in that feature's file under `specs/`, not here.

## How to use this file

- Add a section here only when a requirement is genuinely shared across multiple features (e.g. a cross-cutting product goal, a target user group, a non-functional expectation that applies product-wide).
- Every entry should be traceable to a conversation with the user or to an approved spec under `specs/`.
- Keep feature-specific detail out of this file — it belongs in that feature's spec.

## Product: FieldBuild Kit

Cross-cutting product requirements below are traceable to the stakeholder's explicit statements
during the requirements-clarification conversation for [integrated specification](../specs/qfield-project-builder.md), with later independent-app
changes in [standalone runtime](standalone.md) and [identity/compatibility](independence.md).
The original baseline is approved; each later amendment retains its own approval status.

- **Target users**: ecological field researchers who need to run structured vegetation/species
  surveys without writing SQL or manually configuring QGIS/QField. The intended end users are
  Korean; the application's own UI (labels, buttons, instructions, validation/warning/progress
  messages, dialogs, error messages) is in Korean, with a narrow carve-out for internal
  identifiers, file-format terms (e.g. `.gpkg`, `.qgs`), and proper names (e.g. VWorld, QField,
  Pl@ntNet) where translation would be inappropriate. This governs only this application's own
  UI, not the third-party UI of QGIS Desktop or QField (see
  `specs/qfield-project-builder.md` §14.5, NFR-QPB-070, Decision Log D-28).
- **Deployment model**: a locally installed, single-user native desktop application (not a
  hosted or browser-based web application), with no remote application server and no
  PostgreSQL or other remote database.
- **Platforms**: Windows and macOS are both first-class targets at the source/design level — the
  application's source and packaging configuration must remain genuinely cross-platform. For the
  MVP release specifically, macOS is the first platform packaged and delivered; a built Windows
  installer/executable is a required subsequent-release task, deferred by explicit stakeholder
  direction rather than descoped (see `specs/qfield-project-builder.md` Decision Log D-25).
- **Local-first data**: all survey records, geometries, relations, and attachment paths remain
  in a local GeoPackage-based project folder; the only network access affecting the delivered
  project is to explicitly selected external services (an online VWorld basemap, VWorld tile
  downloads for an offline basemap, and the optional Pl@ntNet identification API). The
  wizard's interactive drawing canvas additionally fetches OpenStreetMap tiles as an ephemeral,
  UI-only visual aid while the user draws; that imagery is never written into, or referenced by,
  the generated project (see `specs/qfield-project-builder.md` FR-QPB-011 and Decision Log D-24).
- **Field-device support**: generated projects must work with QField on both iOS and Android;
  iOS is the stakeholder's primary field-validation platform, but the product must not rely on
  iOS-only behavior or exclude Android.
- **Transfer model**: generated projects are self-contained folders copied directly between the
  desktop application and a smartphone; QFieldSync packaging is not part of the required
  workflow.

## Current scope and documentation status (2026-09-14)

Current version is **0.2.8**, frozen by user instruction. QGIS Desktop is not an app runtime
requirement. Python/PySide6 with packaged independent GIS libraries creates portable QField
folders; QField remains separately installed on the field device. Platform delivery and actual
verification claims must follow [runtime evidence](qfield-runtime-verification.md), not the
historical macOS-first delivery plan above. No new release or platform test is implied here.

The seven-page wizard supports four survey types. Taxonomy is optional; a valid upload applies
automatically. Without it, names are manual and KTSN is absent. Probability TIFF input requires
both taxonomy and photo identification; current filename/NoData rules are in [README](../README.md).
Remembered keys remain in this independent app's encrypted store; legacy credential migration
is superseded. Current reports use Korean display headers, omit UUID/FK display columns, preserve
internal identities, and export coordinates only for usable point rows. Existing generated
projects embed their own QML and are not automatically updated by changing the desktop app.

**Approved baseline with Category B clarification pending:**
[survey-route-planner](../specs/survey-route-planner.md) baseline `e382c77` and acceptance checkpoint
`ed8ac81` cover road-network visit optimization, project-local multiple routes/offline retrieval,
completion/reoptimization, failure preservation, Naver navigation, point/line/polygon drawing and
six upload geometry types. Original geometries remain unchanged; non-Point representative points
are only for routing. Network calls occur only on an explicit calculation.

The clarification DRAFT proposes a registered initial `ors-vroom` provider, numeric relative-second
ETA with explicit basis metadata, source-CRS centroids, strict Boolean completion, explicit Type 1
mapping, a configurable 1000 m road-offset default, project-local non-secret settings and a
session-only API key. Double JSON remains a storage candidate; required persistence behavior is
format-independent. Implementation attempt 2 is uncommitted and its pre-reconciliation automated
result is 104 passed, 2 contract-failing and 12 skipped. Native QField/iOS/Android and live provider/
Naver behavior are unperformed, so no implementation or final PASS is claimed.

Use the [documentation map](README.md) to distinguish current behavior, draft work and history.
