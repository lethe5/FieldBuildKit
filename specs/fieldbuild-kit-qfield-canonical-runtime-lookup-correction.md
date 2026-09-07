# Feature: FieldBuild Kit — QField canonical taxonomy runtime-lookup correction

> Status: APPROVED
> Owner: spec-writer
> Last updated: 2026-09-04
> Approved: 2026-09-04 by stakeholder/user
> Classification: Category A conformance defect; proposed Category B specification correction
> Baseline: [`specs/qfield-project-builder.md`](qfield-project-builder.md), Decision Log D-95; [`specs/fieldbuild-kit-canonical-taxonomy-lookup-defect.md`](fieldbuild-kit-canonical-taxonomy-lookup-defect.md); [`specs/fieldbuild-kit-qfield-canonical-layer-resolution-defect.md`](fieldbuild-kit-qfield-canonical-layer-resolution-defect.md)

## 1. Summary

iPhone QField에서 새 canonical 프로젝트의 GeoPackage에
`ktsn_taxonomy_reference`가 존재하고 `Reference` 그룹에 `식물 분류 참조표`가
표시되어도, 사진 동정은 계속 `canonical_taxonomy_lookup_failed`로 종료한다. 이는
승인된 D-95의 valid Pl@ntNet 이름 → accepted 국명·학명·KTSN 결과 계약을 충족하지
못한 **Category A conformance defect**다.

기존 CTLD/QCLR의 QGIS expression 기반 parser/layer-ID 보정은 QGIS Desktop 및
QField-shaped 검증에서는 통과했지만 실제 iPhone QField에서는 이 결과를 만들지
못했다. 따라서 새 canonical 프로젝트에서 사용할 QField 런타임 조회 매체가 D-95에
명시되어 있지 않은 점은 **Category B specification omission**으로 취급한다.

이 초안은 사진 동정이 활성화된 새 Type 1–3 canonical 프로젝트에만, canonical
GeoPackage 테이블에서 결정적으로 파생한 작고 project-relative한 런타임 조회 리소스를
추가하도록 제안한다. QField widget은 canonical 후보 매칭에 이 리소스를 직접 읽고,
`layer_property()`/`aggregate()`/`get_feature()` 같은 복합 QGIS expression을
canonical 조회의 권위 경로로 사용하지 않는다. 원본 workbook은 계속 프로젝트에
포함하지 않으며, GeoPackage reference table/layer는 데스크톱과 HTML report의
권위 데이터로 그대로 남는다.

## 2. Functional Requirements

- **FR-QCR-001 (new-project runtime lookup resource):** 사진 기반 식별이 활성화된 새
  Type 1–3 canonical 프로젝트는 project-relative한 canonical runtime lookup
  resource를 포함해야 한다. 그 경로와 schema/pipeline revision, record count, byte
  size, SHA-256은 generated project의 provenance metadata에 기록되어야 한다. 경로는
  절대 경로가 아니어야 하며, resource는 프로젝트 폴더 바깥의 파일을 참조해서는 안 된다.

- **FR-QCR-002 (bounded derived data scope):** runtime lookup resource는 같은 build에서
  검증된 `ktsn_taxonomy_reference`의 canonical mapping에서만 파생해야 한다. 각
  lookup record는 다음 값만 포함하거나 이 값만으로 재현 가능해야 한다.

  - 비교 키: `scientific_name_without_authority`
  - accepted 결과: `accepted_ktsn`, accepted row의 `korean_name`, accepted row의
    보존된 raw `scientific_name`
  - schema 검증 및 deterministic ordering에 필요한 비식별 technical metadata

  원본 workbook의 행, URL, 분류 계층, 사진/API key/위치정보, legacy CSV/XLSX의 원문은
  resource에 포함해서는 안 된다. resource는 별도의 taxonomy source of truth가 아니라
  동일 build의 canonical table에 대한 최소 runtime projection이다.

- **FR-QCR-003 (deterministic canonical matching):** 새 canonical 프로젝트의 QField
  identification runtime은 Pl@ntNet `scientificNameWithoutAuthor`를 FR-QCR-002의 비교
  키와 비교해야 한다. 정확히 하나의 accepted group으로 해결되고 accepted Korean name,
  raw scientific name, accepted KTSN이 모두 유효하면, 후보에 그 세 값을 전달해야 한다.
  synonym key도 해당 accepted group의 결과를 사용해야 하며, synonym 자체를 accepted
  결과로 승격해서는 안 된다.

- **FR-QCR-004 (QField-independent canonical lookup path):** 새 canonical 프로젝트의
  canonical candidate lookup은 project-local runtime resource만으로 완료되어야 한다.
  이 경로는 canonical 결과를 얻기 위해 `layer_property()`, `aggregate()`,
  `get_feature()` 또는 QField의 QGIS expression engine에 의존해서는 안 된다.
  Feature form context는 사진 경로·write-back 대상 등 기존 form 용도로 유지할 수 있지만,
  canonical taxonomy mapping 실패를 expression layer resolution으로 판단해서는 안 된다.

- **FR-QCR-005 (fail-closed semantics):** resource가 누락·읽기 불가·비어 있음·schema
  불일치·필수 accepted 값 누락·internal consistency validation 실패인 경우 canonical
  lookup은 available=false로 종료하고, stable diagnostic reason
  `canonical_taxonomy_lookup_resource_unavailable` 또는
  `canonical_taxonomy_lookup_resource_invalid`을 반환해야 한다. 하나의 comparison key가
  둘 이상 accepted KTSN에 연결되면 `ambiguous`; resource가 정상이지만 key가 없으면
  `matched=false` no-match로 처리한다. 어느 경우에도 임의의 `selected_*` 값이나 후보를
  만들거나 partial selected 값을 write-back해서는 안 된다.

- **FR-QCR-006 (no fallback across canonical/legacy boundary):** 새 canonical 프로젝트의
  runtime-resource failure는 legacy CSV matcher, canonical GeoPackage expression lookup,
  display-name lookup, physical-table-name lookup으로 자동 전환해서는 안 된다. 반대로
  explicit `legacy_reference_compatibility` 프로젝트의 existing CSV branch와 선택
  조건·데이터 source·결과는 변경하지 않는다.

- **FR-QCR-007 (GPKG and reporting preservation):** D-95의
  `ktsn_taxonomy_reference` GeoPackage table 및 `식물 분류 참조표` QGIS Reference-layer
  contract는 유지한다. HTML report taxonomy aggregation과 desktop/reference-table
  inspection은 이 GeoPackage table을 계속 사용해야 하며, runtime lookup resource를
  report data source로 사용하거나 원본 workbook을 project에 복사해서는 안 된다.

- **FR-QCR-008 (atomic generation and old-project boundary):** runtime resource의
  materialization, schema validation 및 provenance write가 완료되지 않으면 canonical
  identification-enabled build는 promote되지 않아야 하며 partial delivered project를
  남겨서는 안 된다. 이미 생성된 canonical 프로젝트에는 resource를 자동 생성하거나
  migration하지 않는다. 이 초안이 승인되면 FR-QCLR-001–003/007과
  AC-QCLR-001–003/005/007–008의 **new-project expression/layer-ID route만** 새
  projects에서 supersede한다; D-95와 CTLD의 data/result/fail-closed requirements와
  explicit legacy compatibility behavior는 supersede하지 않는다.

## 3. Constraints

- **C-QCR-001:** D-95의 canonical source workbook, accepted-before-synonym grouping,
  authority removal, `ktsn_taxonomy_reference` schema, accepted-only compatibility projection,
  user-visible layer names, provenance identity, raw-workbook exclusion, and selected-field
  contract must not change.

- **C-QCR-002:** This correction establishes a data-access contract, not a mandatory file
  serialization technology. The implementation may choose a compact QField-readable text/data
  serialization, but it must expose the FR-QCR-001 provenance fields and satisfy the exact
  record scope and runtime behavior above. It may not store the projection only in process
  memory or rely on an external/network service.

- **C-QCR-003:** The canonical runtime resource may be generated only for a Type 1–3 project
  with identification enabled. D-95's canonical GeoPackage tables remain required independently
  of identification. Type 4 gains neither an identification resource nor an invented taxonomy
  mapping flow.

- **C-QCR-004:** The build and runtime must not log or export API keys, photo bytes, precise
  location, workbook rows, or the original workbook path outside the project. Provenance may
  contain the confirmed source filename, source hash, revisions, counts, and the relative
  resource metadata specified by FR-QCR-001.

- **C-QCR-005:** This spec-writer stage changes no application source or tests. A fresh
  test-designer may create acceptance tests only after explicit stakeholder approval.

## 4. Assumptions

- **A-QCR-001:** The observed generated projects contain both the local GeoPackage
  `ktsn_taxonomy_reference` table and the displayed `식물 분류 참조표` layer. Their presence
  alone does not establish that QField can execute the current complex cross-layer expression
  path.

- **A-QCR-002:** The canonical projection is bounded by the selected workbook's canonical
  rows (8,042 rows in the current fixture, but no fixed row count is a product invariant), so
  materializing a minimal on-device lookup resource is feasible without bundling the workbook.

- **A-QCR-003:** A `scientificNameWithoutAuthor` is valid for this contract only when it equals
  a nonblank stored comparison key and resolves to exactly one accepted group with all three
  required accepted outputs. Network success, photograph quality, and Pl@ntNet confidence remain
  outside this correction.

## 5. Edge Cases

- **E-QCR-001:** A resource is present but provenance points to a different path, hash, record
  count, schema revision, or build's canonical identity. The build-time integrity validation
  fails before promotion; if a damaged delivered resource is encountered on-device, runtime
  fails closed as resource-invalid.

- **E-QCR-002:** The resource is deleted, unreadable, truncated, or has an unknown schema.
  Runtime returns the specified unavailable/invalid reason and does not query the GPKG through
  expressions or legacy data.

- **E-QCR-003:** A valid resource contains no exact comparison key. This is a normal no-match,
  not a resource-unavailable error; no candidate is offered from that result.

- **E-QCR-004:** A comparison key appears in rows mapped to distinct accepted KTSNs. This is
  ambiguous and no accepted result is guessed. Repeated records for the same comparison key and
  the same accepted output are not ambiguous by themselves.

- **E-QCR-005:** The resource has a matching accepted KTSN but one of Korean name, scientific
  name, or KTSN is blank/malformed. It is resource-invalid for that match and no selected value
  is written.

- **E-QCR-006:** A new project has identification disabled. No runtime resource is required and
  no identification widget/lookup route is activated; the canonical reference GPKG remains
  available as D-95 requires.

- **E-QCR-007:** An old canonical project lacks the new resource. It is not migrated in place
  and must not silently reinterpret its old QML configuration as the new format. Explicit legacy
  compatibility projects retain their existing separate branch unchanged.

## 6. Out of Scope

- Changing the canonical workbook selection/upload workflow, its content, row count, or D-95
  ingestion rules.
- Changing Pl@ntNet API requests, timeouts, candidate ranking, photos, GPS, probability rasters,
  candidate-card design, or the existing write-back field policy.
- Changing the legacy CSV source, matcher, migration behavior, or historical-project data.
- Replacing the GeoPackage reference table/layer with the runtime resource, or using the runtime
  resource as an HTML report source.
- Making a raw source workbook, full legacy dataset, or remote taxonomy service part of the
  QField runtime.

## 7. Acceptance Criteria

- **AC-QCR-001 (projection/provenance):** Given a validated canonical Type 1–3 build with
  identification enabled, when the delivered project is inspected, then it contains one
  project-relative runtime lookup resource and provenance that declares its relative path,
  schema/pipeline revision, record count, byte size, and SHA-256. The resource's parsed records
  contain only FR-QCR-002-permitted mapping/technical fields, are derived from the same build's
  `ktsn_taxonomy_reference`, and the raw workbook, legacy CSV/XLSX, API key, photo bytes, and
  absolute source paths are absent.

- **AC-QCR-002 (deterministic accepted/synonym mapping):** Given small accepted-row and synonym
  fixtures plus a deterministic `scientificNameWithoutAuthor`, when the generated QField runtime
  lookup reads the resource, then an accepted key and a synonym key each yield the same accepted
  Korean name, preserved raw accepted scientific name, and accepted KTSN. The candidate model and
  subsequent selected-field write-back input receive exactly those three values.

- **AC-QCR-003 (expression independence):** Given a newly generated canonical project, when the
  canonical candidate lookup path loaded by QField is inspected and executed with a deterministic
  response fixture, then it reads the declared project-local resource and produces the
  AC-QCR-002 result without calling `layer_property()`, `aggregate()`, or `get_feature()` for
  canonical mapping. A test that merely proves the GeoPackage layer exists, or only evaluates a
  Desktop QGIS expression, does not satisfy this criterion.

- **AC-QCR-004 (fail-closed matrix):** Given fixtures for missing/unreadable resource, unknown
  schema, truncated/malformed record, provenance/resource consistency failure, no-match,
  multi-accepted-group ambiguity, and blank accepted output, when each lookup runs, then it
  returns the exact FR-QCR-005 category/reason and creates no candidate or `selected_*` values.
  No fixture may invoke the legacy CSV branch or a canonical QGIS-expression fallback.

- **AC-QCR-005 (preservation boundaries):** Given the same generated project, when the
  GeoPackage, layer tree, report input, and explicit legacy fixture are inspected, then
  `ktsn_taxonomy_reference` and `식물 분류 참조표` remain present and report aggregation reads
  the GeoPackage, while the explicit legacy fixture preserves its pre-correction CSV behavior.
  A new canonical runtime-resource failure must not activate either legacy or expression lookup.

- **AC-QCR-006 (generation/old-project boundaries):** Given an enabled build where resource
  generation or validation fails, when build promotion is attempted, then no partial delivered
  project is promoted and the error identifies the resource stage. Given identification-disabled
  Type 1–3 and Type 4 builds, no runtime resource is required. Given an old canonical fixture
  lacking the resource, it is not rewritten/migrated during open/export.

- **AC-QCR-007 (actual QField device gate):** Given a newly generated,
  identification-enabled canonical project transferred unchanged to iPhone QField and a real
  Pl@ntNet response whose `scientificNameWithoutAuthor` is known to match the resource, when the
  user presses `사진으로 동정하기`, then QField displays the canonical candidate without
  `canonical_taxonomy_lookup_failed`; selecting it makes Korean name, scientific name, and KTSN
  available to the existing write-back flow. The validation record must identify the app/project
  build and response comparison key but must not record API keys, photo bytes, or precise
  coordinates. This device gate is required evidence for release of this correction; Desktop-QGIS
  or QField-shaped simulation alone is insufficient.

## 8. Traceability Direction

After approval, the test-designer must add acceptance coverage and a traceability mapping for
this draft without weakening D-95, CTLD, or the legacy branch. Required evidence is:

| Requirement / acceptance | Required evidence |
|---|---|
| FR/AC-QCR-001 | Generated project inspection, parsed runtime resource, and provenance/path/hash/count/schema assertions |
| FR/AC-QCR-002 | Accepted and synonym deterministic fixtures with exact three-value candidate/write-back model assertions |
| FR/AC-QCR-003 | Execution/instrumentation of the generated QField lookup route proving local-resource read and absence of canonical expression calls |
| FR/AC-QCR-004 | Parameterized unavailable/invalid/no-match/ambiguous/malformed matrix; no candidate, selected value, legacy, or expression fallback |
| FR/AC-QCR-005 | GeoPackage/layer/report source assertions plus explicit legacy compatibility regression |
| FR/AC-QCR-006 | Atomic build failure, disabled/Type 4 boundaries, and no-old-project-migration fixture |
| AC-QCR-007 | Recorded iPhone QField manual device evidence after automated acceptance coverage passes |

## 9. Proposed Decision Log Entry

- **D-96 (DRAFT; proposed Category B correction to the D-95 runtime-access omission):** The
  stakeholder-reported iPhone failure proves that the previously approved expression/layer-ID
  implementation route does not satisfy D-95's canonical lookup outcome on QField, despite the
  local GeoPackage table/layer being present. For newly generated Type 1–3 projects with photo
  identification enabled, add a minimal project-local canonical runtime lookup projection with
  explicit provenance and fail-closed semantics. The projection replaces only the new-project
  canonical QGIS-expression route; it does not replace the canonical GeoPackage reference table,
  report source, canonical workbook policy, or explicit legacy CSV compatibility branch. Existing
  canonical projects are not migrated. This decision is **proposed only** and has no authority
  until the stakeholder approves this specification.

## 10. Open Questions

- None blocking specification approval. The physical serialization/filename is deliberately an
  implementation choice within C-QCR-002, provided the generated project exposes the testable
  provenance and runtime contract above.
