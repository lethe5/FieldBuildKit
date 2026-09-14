# FieldBuild Kit documentation map

Updated 2026-09-14 for version **0.2.8** (frozen). Product: FieldBuild Kit; repository: FieldBuildKit.
This map records document status and source observations, not new approvals or test results.

| Document | Current purpose and status |
| --- | --- |
| [한국어 README](../README.md) / [English README](../README.en.md) | Current user workflow and installation; pending routes clearly separated |
| [Product](product.md) | Current cross-feature requirements, including approved optional-reference changes and draft routing scope |
| [Architecture](architecture.md) | Current standalone call path first; inherited QGIS/server-storage decisions retained as history |
| [Standalone runtime](standalone.md) | Current generation, optional inputs, template processing and versioned changes |
| [Identity/compatibility](independence.md) | Independent app, retained qfield_builder package, build recipe and storage identities |
| [Runtime verification](qfield-runtime-verification.md) | Dated automated/service/user evidence and explicit unverified device behavior; not a blanket PASS |
| [UI guidance](ui-design-guidelines.md) | Current seven-page wizard sizes/scroll containers, approved icons; draft route controls separated |
| [Change control](change-control.md) / [AGENTS.md](../AGENTS.md) | Role boundaries and separate specification/acceptance artifact approvals |
| [Presentation](index.html) | User-facing workflow illustrations, not release or acceptance evidence |
| [Integrated specification](../specs/qfield-project-builder.md) | Approved inherited baseline plus dated amendments; standalone/optional-reference supersessions apply |
| [Wizard layout specification](../specs/fieldbuild-kit-wizard-ui-layout-defect.md) | D-96 approved 2026-09-04; current source contains scroll containers; device/DPI evidence remains separate |
| [Route and geometry specification](../specs/survey-route-planner.md) | APPROVED 2026-09-14: specification approved; acceptance artifacts and implementation/integration unverified |
| [Route test design](../tests/acceptance/survey_route_planner.test-design.md) / [traceability](../tests/acceptance/survey_route_planner.traceability.md) | Existing drafts; specification approved; fresh test-designer reconciliation pending |
| [Windows QGIS bridge draft](../specs/windows-qgis-bridge-runtime.md) | Historical source-product design, superseded as an end-user runtime requirement |

Other dated feature specifications and the original requirements draft remain provenance for their
own decisions. They do not reintroduce QGIS Desktop, compulsory private datasets or credential
migration into the independent app. Preserve FR/AC/Decision IDs and follow explicit later
supersessions. The integrated spec historically reused D-98: include date/title when citing it.

## Current versus requested behavior

The source still uses MULTIPOLYGON for site generation/validation and polygon direct site input.
The requested point/line/polygon selector and Point/LineString/Polygon/MultiPoint/MultiLineString/
MultiPolygon SHP/ZIP/GPKG detection are future work. Existing route helper files do not establish
a working QField plugin. Line/area routing centroids never change the report's point-coordinate
export rule. QGIS-free generation uses active qgis_worker public wrappers that delegate to
template_project and standalone_gis; private PyQGIS helpers are development-only.

This reconciliation adds no application code, executable acceptance tests or test PASS. The next
role receives the approved route spec, integrated spec and shared docs, then updates acceptance
artifacts for a separate approval. Existing generated projects are not automatically migrated.