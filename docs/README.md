# FieldBuild Kit documentation map

Updated 2026-09-14 for version **0.2.8** (frozen). Product: FieldBuild Kit; repository: FieldBuildKit.
This map records document status and source observations, not new approvals or test results.

| Document | Current purpose and status |
| --- | --- |
| [한국어 README](../README.md) / [English README](../README.en.md) | Current user workflow and installation; uncommitted route attempt and DRAFT clarification separated from available behavior |
| [Product](product.md) | Current cross-feature requirements, including approved route scope and the pending Category B clarification |
| [Architecture](architecture.md) | Current standalone call path first; inherited QGIS/server-storage decisions retained as history |
| [Standalone runtime](standalone.md) | Current generation, optional inputs, template processing and versioned changes |
| [Identity/compatibility](independence.md) | Independent app, retained qfield_builder package, build recipe and storage identities |
| [Runtime verification](qfield-runtime-verification.md) | Dated automated/service/user evidence and explicit unverified device behavior; not a blanket PASS |
| [UI guidance](ui-design-guidelines.md) | Current seven-page wizard sizes/scroll containers and approved icons; route UI remains unverified implementation work |
| [Change control](change-control.md) / [AGENTS.md](../AGENTS.md) | Role boundaries and separate specification/acceptance artifact approvals |
| [Presentation](index.html) | User-facing workflow illustrations, not release or acceptance evidence |
| [Integrated specification](../specs/qfield-project-builder.md) | Approved inherited baseline plus dated amendments; standalone/optional-reference supersessions apply |
| [Wizard layout specification](../specs/fieldbuild-kit-wizard-ui-layout-defect.md) | D-96 approved 2026-09-04; current source contains scroll containers; device/DPI evidence remains separate |
| [Route and geometry specification](../specs/survey-route-planner.md) | Approved baseline `e382c77`; Category B contract clarification DRAFT pending user approval |
| [Route test design](../tests/acceptance/survey_route_planner.test-design.md) / [traceability](../tests/acceptance/survey_route_planner.traceability.md) | Approved checkpoint `ed8ac81`; ETA/backend and clarified-default reconciliation follows only after spec approval |
| [Windows QGIS bridge draft](../specs/windows-qgis-bridge-runtime.md) | Historical source-product design, superseded as an end-user runtime requirement |

Other dated feature specifications and the original requirements draft remain provenance for their
own decisions. They do not reintroduce QGIS Desktop, compulsory private datasets or credential
migration into the independent app. Preserve FR/AC/Decision IDs and follow explicit later
supersessions. The integrated spec historically reused D-98: include date/title when citing it.

## Current versus requested behavior

The last approved/released behavior remains polygon-based. The working tree contains uncommitted
implementation attempt 2 for point/line/polygon input, six upload geometry types and routing; its
files are evidence to verify, not requirement authority or proof of a working QField plugin.
Line/area routing centroids never change the report's point-coordinate export rule. QGIS-free
generation continues through the active qgis_worker wrappers to template_project/standalone_gis;
private PyQGIS helpers remain development-only.

Before contract reconciliation the automated result was 104 passed, 2 contract-failing and
12 skipped. The two failures are AC-SRP-007's ISO ETA fixture versus VROOM relative seconds and
AC-SRP-013's unregistered `acceptance_backend` token. Native QField/iOS/Android, live provider and
Naver execution remain unperformed; there is no final PASS or merge claim. This documentation-only
Category B draft changes no code or acceptance artifact. After explicit spec approval, a fresh
test-designer must update the affected acceptance artifacts for separate approval. Existing
generated projects are not automatically migrated. Version remains 0.2.8.
