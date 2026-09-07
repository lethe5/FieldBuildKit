# Feature: FieldBuild Kit — QField canonical taxonomy layer-resolution conformance defect

> Status: APPROVED
> Owner: spec-writer
> Last updated: 2026-09-04
> Classification: Category A conformance defect
> Baseline: [`specs/qfield-project-builder.md`](qfield-project-builder.md), D-95, [`specs/fieldbuild-kit-canonical-taxonomy-lookup-defect.md`](fieldbuild-kit-canonical-taxonomy-lookup-defect.md)
> Approval: 2026-09-04 by stakeholder/user

## 1. Summary

최신 빌드에서 유효한 `식물 분류 참조표`가 생성된 `.qgs`와 GeoPackage에 존재함에도
QField 사진 동정 시 `canonical_taxonomy_lookup_failed`가 표시된다. 로컬 진단 결과,
현재 생성 QML은 표시명 `식물 분류 참조표`를 `layer_property()`, `aggregate()`,
`get_feature()`의 대상 레이어로 사용하고 있으며, QGIS 3.44/QField에서는 물리 테이블명
`ktsn_taxonomy_reference`가 해당 expression 레이어 인수로 안정적으로 해석되지 않는다.

이 명세는 새 프로젝트 생성 시 canonical taxonomy layer의 실제 QGIS
`QgsMapLayer.id()`를 생성 시점에 lookup widget/QML에 전달하고, 모든 canonical lookup
expression의 레이어 대상에 그 ID를 사용하는 conformance 결함을 수정한다. D-95의
참조표 내용, 매칭 규칙, 후보 표시, `selected_*` 결과 및 fail-closed 정책은 유지한다.

## 2. Functional Requirements

- **FR-QCLR-001 (project layer ID propagation):** canonical taxonomy layer를 생성
  프로젝트에 등록한 직후 실제 `QgsMapLayer.id()`를 확정하고, 그 값을 생성된 QField
  plugin/widget lookup configuration에 명시적으로 전달해야 한다. 전달 값은 임의로 만든
  테이블명이나 표시명이 아니라 해당 프로젝트의 실제 layer ID여야 한다.

- **FR-QCLR-002 (ID-based expression resolution):** 새로 생성되는 프로젝트의 canonical
  lookup expression에서 `layer_property()`, `aggregate()`, `get_feature()`의 레이어
  대상 인수는 모두 FR-QCLR-001의 project layer ID를 사용해야 한다. 표시명
  `식물 분류 참조표` 또는 물리 테이블명 `ktsn_taxonomy_reference`를 새 프로젝트의
  expression 레이어 대상으로 사용해서는 안 된다. QML/JavaScript 문자열에 삽입할 때는
  QGIS 문자열 리터럴로 안전하게 escape해야 한다.

- **FR-QCLR-003 (layer identity guard):** lookup은 전달된 ID가 현재 expression context에서
  실제 canonical taxonomy layer를 가리키는지 확인해야 한다. 대상 레이어가 없거나,
  이름/필수 필드/참조 역할이 일치하지 않거나, expression context가 유효하지 않으면
  canonical lookup unavailable로 fail-closed해야 하며 임의의 다른 레이어나 물리 테이블을
  추측해 사용해서는 안 된다.

- **FR-QCLR-004 (valid row and selected fields):** 유효한 canonical layer와 매칭 row가
  있으면 기존 D-95/CTLD 계약대로 후보를 표시하고 `selected_ktsn`,
  `selected_korean_name`, `selected_scientific_name`을 보존·전달해야 한다. 레이어 ID를
  사용한다는 이유로 후보 표시, 후보 선택 또는 기존 write-back 흐름이 달라져서는 안 된다.

- **FR-QCLR-005 (fail-closed semantics):** no-match, ambiguous accepted group,
  malformed row, missing layer, invalid ID 또는 missing expression context의 기존
  결과 의미와 reason code를 유지해야 한다. 이러한 경우 임의의 accepted row를 선택하거나
  fabricated `selected_*` 값을 만들지 않아야 한다.

- **FR-QCLR-006 (legacy boundary):** 명시적으로 `legacy_reference_compatibility`인
  프로젝트의 CSV lookup과 fallback 조건·우선순위·데이터 소스는 변경하지 않는다. 새
  canonical 프로젝트의 layer-resolution 실패를 legacy CSV lookup으로 자동 전환해서는
  안 된다.

- **FR-QCLR-007 (old generated-project compatibility):** 이미 생성된 프로젝트에 새로
  생성된 embedded canonical layer ID가 없을 수 있음을 명시적으로 처리해야 한다.
  호환 경로는 다음 안전한 순서를 따른다.

  1. embedded canonical layer ID가 있으면 해당 ID만 사용한다.
  2. embedded ID가 없고 기존 프로젝트에 정확한 표시명 `식물 분류 참조표`가 있는
     경우에만 documented display-name compatibility fallback을 시도한다. 이 fallback은
     `layer_property()`, `aggregate()`, `get_feature()`에 동일한 정확한 표시명만
     사용하며, 물리 테이블명 추측이나 다른 레이어 자동 선택을 하지 않는다.
  3. 표시명 fallback이 해석되지 않거나 대상이 canonical layer임을 검증할 수 없으면
     canonical unavailable로 종료한다.

  이 호환 경로에서도 legacy CSV fallback은 허용하지 않는다. 새 프로젝트에는
  display-name fallback을 사용하지 않는다.

## 3. Constraints

- **C-QCLR-001:** 승인된 D-95와 CTLD의 source workbook, canonical schema, accepted-name/
  synonym grouping, authority 제거, layer display name, provenance, bundle layout 및
  selected-field 계약을 변경하지 않는다.

- **C-QCLR-002:** 수정 범위는 canonical taxonomy layer identity의 생성 시 전달,
  QGIS expression layer resolution, old-project compatibility 및 이에 필요한 회귀
  검증으로 한정한다. Pl@ntNet API, 사진 전송·리사이즈, GPS/현재 위치, 확률 래스터,
  UI 문구, write-back 필드 정책은 변경하지 않는다.

- **C-QCLR-003:** ID 기반 expression은 QGIS 3.44의 `QgsExpression` parser와 evaluator,
  그리고 QField-shaped generated QML context에서 같은 의미로 평가되어야 한다. 문자열
  token 존재만 검사하는 테스트로 conformance를 입증할 수 없다.

- **C-QCLR-004:** 생성 프로젝트마다 layer ID가 다를 수 있으므로 테스트는 고정 UUID를
  요구하지 않는다. 대신 생성된 `.qgs`의 canonical layer `id()`와 생성 QML/widget에
  전달된 ID가 정확히 일치하는지 검증한다.

- **C-QCLR-005:** API key, 사진 bytes, 위치정보 및 개인정보를 테스트 출력·로그에
  남기지 않는다.

- **C-QCLR-006:** 이 spec-writer 단계에서는 Python/QML application code와 test file을
  수정하지 않는다. 구현 및 테스트 변경은 본 명세와 후속 acceptance tests가 승인된
  뒤 clean-room 단계에서 수행한다.

## 4. Assumptions

- **A-QCLR-001:** 생성 프로젝트의 canonical layer는 GeoPackage의 물리 테이블
  `ktsn_taxonomy_reference`에서 열리지만 QGIS project layer의 논리 표시명은
  `식물 분류 참조표`이다.

- **A-QCLR-002:** `QgsMapLayer.id()`는 해당 생성 프로젝트 안에서 expression layer
  reference로 사용할 수 있는 안정적인 식별자이며, 프로젝트 저장·재로드 후에도
  generated QML이 참조할 값과 일치한다.

- **A-QCLR-003:** 현재 `canonical_taxonomy_lookup_failed`의 직접 원인은 유효
  참조표 행 자체의 부재가 아니라, expression layer argument의 layer-resolution
  불일치이다. 구현 단계에서 QGIS 3.44 parser/evaluator와 generated project fixture로
  이 원인을 재확인한다.

- **A-QCLR-004:** “QField-shaped” 검증은 실제 QField 애플리케이션을 pytest 프로세스에
  포함한다는 뜻이 아니라, QField가 로드하는 generated `.qgs`/QML과 동일한 property,
  expression context, deterministic response fixture를 사용해 후보 표시 경로를
  관찰하는 것을 뜻한다. 실제 iPhone/QField 로딩은 별도의 device gate로 남긴다.

## 5. Edge Cases

- **E-QCLR-001:** 새 프로젝트의 canonical layer ID가 QML에 비어 있거나 누락되어 있다.
  lookup은 canonical unavailable로 fail-closed하고 물리 테이블명으로 추측하지 않는다.

- **E-QCLR-002:** QML에 전달된 ID가 존재하지만 `식물 분류 참조표`가 아닌 다른 레이어를
  가리킨다. identity guard가 이를 거부하고 canonical unavailable로 처리한다.

- **E-QCLR-003:** 프로젝트 저장·재로드 후 ID가 변경되거나 generated QML의 ID와 `.qgs`
  ID가 다르다. generated-project conformance 검증에서 실패해야 하며, runtime은 잘못된
  레이어를 선택하지 않고 unavailable로 처리한다.

- **E-QCLR-004:** old generated project에 embedded ID가 없지만 정확한 표시명의 canonical
  layer가 있다. documented compatibility fallback으로 lookup을 시도하고, 정상 매칭이면
  기존 후보/selected 결과를 보존한다.

- **E-QCLR-005:** old generated project에 표시명 layer도 없거나 표시명은 있으나 필수
  필드가 없다. canonical unavailable로 처리하며 legacy CSV로 전환하지 않는다.

- **E-QCLR-006:** canonical layer는 해석되지만 scientific name no-match, ambiguous
  group, malformed row가 발생한다. CTLD에서 정의한 matched/ambiguous/invalid-row
  semantics를 그대로 유지한다.

## 6. Out of Scope

- D-95 canonical workbook의 내용·행 수·필드명·정/이명 처리·분류 계층 추출 변경.
- GeoPackage 물리 테이블명 또는 사용자에게 보이는 canonical layer 표시명 변경.
- 새로운 taxonomy matching, synonym resolution, ambiguity 해소 또는 KTSN 정책.
- Pl@ntNet endpoint/authentication/timeout, 사진 처리, QField 권한, GPS 및 확률 래스터.
- 후보 카드 디자인, 한국어 문구, selected-field write-back 정책 변경.
- legacy compatibility 프로젝트의 CSV 데이터 또는 fallback 정책 변경.
- 새 프로젝트에 대해 layer display name/physical table-name 기반 lookup을 병행하는
  추가 heuristic.

## 7. Acceptance Criteria

각 기준은 독립적으로 PASS/FAIL 판정할 수 있어야 하며, 후속 acceptance-test traceability
문서에서 동일한 안정 ID를 사용한다.

- **AC-QCLR-001 (generated ID propagation):** deterministic generated project를
  생성하면 `.qgs`의 canonical taxonomy `QgsMapLayer.id()`와 generated QML/widget에
  전달된 canonical layer ID가 정확히 일치하고, 전달 값이 물리 테이블명이나 표시명이
  아님을 확인할 수 있어야 한다.

- **AC-QCLR-002 (all expression targets use ID):** 생성된 canonical lookup에 실제로
  사용되는 expression을 추출해 QGIS 3.44에서 parse/evaluate하면
  `layer_property()`, `aggregate()`, `get_feature()`가 모두 embedded project layer
  ID를 대상으로 해야 하며, parser/evaluator 오류가 없어야 한다. 새 프로젝트 expression
  대상에 `식물 분류 참조표` 또는 `ktsn_taxonomy_reference`가 남아 있으면 FAIL이다.

- **AC-QCLR-003 (valid canonical candidate):** QGIS 3.44 context에 ID로 해석되는
  canonical layer와 deterministic valid row, Pl@ntNet response fixture를 제공하면
  `canonical_taxonomy_lookup_failed` 없이 후보 카드가 표시되고, 후보 결과에
  `selected_ktsn`, `selected_korean_name`, `selected_scientific_name`이 canonical
  accepted row의 값으로 유지되어야 한다.

- **AC-QCLR-004 (fail-closed matrix):** ID 누락/오류, non-canonical target,
  missing context/layer, no-match, ambiguous 및 malformed row를 각각 실행하면 각
  case가 기존 CTLD reason/matched semantics를 유지하고, 임의 후보·임의 selected 값·
  자동 legacy fallback을 생성하지 않아야 한다.

- **AC-QCLR-005 (old-project compatibility):** embedded ID가 없는 old-project fixture에서
  정확한 표시명 canonical layer가 있으면 documented display-name fallback으로 유효한
  후보를 표시할 수 있어야 한다. 표시명 layer가 없거나 검증할 수 없으면 canonical
  unavailable로 종료해야 하며 CSV matcher를 호출하지 않아야 한다.

- **AC-QCLR-006 (legacy boundary):** 명시적 `legacy_reference_compatibility` fixture의
  CSV lookup 결과와 branch 선택은 defect 수정 전 계약과 동일해야 하며, canonical branch의
  ID-resolution 실패가 legacy branch를 자동으로 활성화하지 않아야 한다.

- **AC-QCLR-007 (saved/reloaded generated project):** 생성 프로젝트를 저장한 뒤 다시
  로드하는 deterministic round trip에서도 `.qgs` layer ID와 generated QML/widget ID가
  일치하고, 동일한 QField-shaped response fixture가 AC-QCLR-003과 같은 후보 및
  `selected_*` 결과를 내야 한다.

- **AC-QCLR-008 (QField-shaped runtime path):** QField가 로드하는 것과 동일한 generated
  QML/plugin response-handler path에서 valid/no-match/ambiguous/malformed 결과를
  관찰할 수 있어야 하며, valid case는 failure label 없이 후보를 표시하고 failure cases는
  기존 fail-closed UI 상태를 표시해야 한다. 실제 기기 테스트가 가능한 경우 iPhone
  QField에서 사진 동정 버튼을 눌러 valid 후보가 보이는 것을 별도 수동 증거로 기록한다.

## 8. Traceability Direction

후속 test-designer는 다음 매핑을 유지해야 한다.

| Requirement / acceptance | Required evidence |
|---|---|
| FR/AC-QCLR-001 | Generated `.qgs` layer ID, generated QML/widget configuration, exact equality assertion |
| FR/AC/AC-QCLR-002 | Captured production expression plus isolated QGIS 3.44 parser/evaluator result; assert every layer target uses ID |
| FR/AC-QCLR-003 | Valid canonical GeoPackage/project fixture and deterministic Pl@ntNet response; candidate model and all three `selected_*` values |
| FR/AC-QCLR-004 | Parameterized fail-closed matrix for missing/invalid ID, wrong layer, missing context, no-match, ambiguous and malformed row |
| FR/AC-QCLR-005 | Old-project fixture with/without display-name layer; exact compatibility fallback and unavailable outcomes; prove no CSV call |
| FR/AC-QCLR-006 | Explicit legacy fixture and branch instrumentation/result comparison |
| FR/AC-QCLR-007 | Save/reload project round-trip and re-evaluation using the same deterministic fixture |
| FR/AC/AC-QCLR-008 | QField-shaped generated QML/plugin execution; optional device evidence recorded separately and without secrets |

The test-designer must add acceptance tests and a traceability file without modifying D-95 or
the approved CTLD specification. Tests must use isolated temporary projects/layers and must not
read or alter the user's live QGIS profile.

## 9. Open Questions

- 없음. 본 문서는 표시명 fallback을 old generated project의 호환 정책으로 제안한다. 단,
  이 새 명세는 현재 사용자 승인을 받지 않았으므로 승인 전에는 테스트 설계·구현·커밋을
  진행하지 않는다.
