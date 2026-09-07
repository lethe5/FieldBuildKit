# Product Requirements

> Owned and updated by: spec-writer
> Scope: requirements shared across more than one feature specification. Feature-specific requirements belong in that feature's file under `specs/`, not here.

## How to use this file

- Add a section here only when a requirement is genuinely shared across multiple features (e.g. a cross-cutting product goal, a target user group, a non-functional expectation that applies product-wide).
- Every entry should be traceable to a conversation with the user or to an approved spec under `specs/`.
- Keep feature-specific detail out of this file — it belongs in that feature's spec.

## Product: QField Project Builder

Cross-cutting product requirements below are traceable to the stakeholder's explicit statements
during the requirements-clarification conversation for `specs/qfield-project-builder.md` (still
Draft; see that specification for full detail, acceptance criteria, and the decision log). This
section will be revisited when that specification is approved.

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
  downloads for an offline basemap, and, in a later phase, the Pl@ntNet identification API). The
  wizard's interactive drawing canvas additionally fetches OpenStreetMap tiles as an ephemeral,
  UI-only visual aid while the user draws; that imagery is never written into, or referenced by,
  the generated project (see `specs/qfield-project-builder.md` FR-QPB-011 and Decision Log D-24).
- **Field-device support**: generated projects must work with QField on both iOS and Android;
  iOS is the stakeholder's primary field-validation platform, but the product must not rely on
  iOS-only behavior or exclude Android.
- **Transfer model**: generated projects are self-contained folders copied directly between the
  desktop application and a smartphone; QFieldSync packaging is not part of the required
  workflow.
