# Feature: FieldBuild Kit — QField canonical taxonomy lookup parser defect

> Status: APPROVED
> Owner: spec-writer
> Approved: 2026-09-04
> Approved by: stakeholder/user
> Last updated: 2026-09-04
> Classification: Category A conformance defect
> Baseline: [`specs/qfield-project-builder.md`](qfield-project-builder.md), D-95

## 1. Summary

QField의 사진 동정 결과 처리에서 유효한 canonical taxonomy 레이어와 일치 레코드가
있음에도 `canonical_taxonomy_lookup_failed`가 발생하는 결함을 수정한다. 현재
`qfield_builder/qml_plugin.py`의 `qpbLookupCanonicalTaxonomy()`가 생성하는 중첩
QGIS expression의 괄호가 부족하여 QGIS 3.44의 `QgsExpression` parser가
`Incomplete expression`을 반환하는 것이 로컬 재현 증거다.

이 명세는 승인된 D-95의 canonical workbook, `식물 분류 참조표` 레이어, 후보
표시/selected 필드 결과, fail-closed semantics 및 legacy 호환 정책을 그대로
유지하면서 parser 결함과 그 회귀만 다룬다.

## 2. Functional Requirements

- **FR-CTLD-001 (valid canonical lookup):** 생성 프로젝트에 유효한
  `식물 분류 참조표` canonical layer와 유효한 매칭 레코드가 있고, Pl@ntNet 후보의
  `scientificNameWithoutAuthor`가 해당 레이어의
  `scientific_name_without_authority`와 일치하면, QField의 lookup은
  `canonical_taxonomy_lookup_failed`를 반환하지 않아야 한다. lookup 결과는 canonical
  accepted row에서 `selected_ktsn`, `selected_korean_name`,
  `selected_scientific_name`을 반환해야 하며, 기존 후보 표시 및 후보 선택/write-back
  흐름이 후보를 표시하고 사용할 수 있어야 한다.

- **FR-CTLD-002 (parser-valid expression):** canonical lookup에 사용하는 QGIS
  expression은 QGIS 3.44 `QgsExpression` parser/runtime에서 완전하게 파싱되고
  평가되어야 한다. 현재 expression의 중첩 `with_variable`/`aggregate`/
  `get_feature` 구조와 필요한 lookup 결과 필드는 보존하되, 닫는 괄호 누락이나
  그와 동등한 문법 오류를 포함해서는 안 된다.

- **FR-CTLD-003 (no-match semantics):** canonical layer가 사용 가능하지만
  Pl@ntNet 이름과 일치하는 canonical row가 없으면 기존 no-match 의미를 유지한다.
  이는 전체 canonical lookup을 `canonical_taxonomy_lookup_failed`로 오판하지 않으며,
  해당 후보를 기존 정책에 따라 actionable 후보에서 제외하거나 결과 없음으로
  처리하는 동작이어야 한다. 새로운 임의의 이름/KTSN을 만들어서는 안 된다.

- **FR-CTLD-004 (ambiguous and malformed semantics):** 여러 accepted group에
  매핑되는 이름, 필수 canonical 값이 없는 row, 잘못된 canonical row 또는 canonical
  layer 자체를 사용할 수 없는 경우에는 기존 fail-closed 결과와 이유 코드를
  유지한다. 임의의 후보를 선택하거나 legacy CSV matcher로 자동 전환해서는 안 된다.

- **FR-CTLD-005 (legacy boundary):** 명시적으로 legacy 프로젝트로 판정되는 경우의
  기존 legacy CSV fallback만 유지한다. 새 프로젝트의 canonical lookup 실패를
  legacy fallback으로 바꾸거나, legacy fallback의 조건·우선순위·데이터 소스를
  변경하지 않는다.

## 3. Constraints

- **C-CTLD-001:** 승인된 D-95의 source workbook, accepted-name/synonym grouping,
  authority 제거, canonical layer schema/display name, provenance, project bundling 및
  `selected_*` 결과 계약은 변경하지 않는다.

- **C-CTLD-002:** 수정 범위는 canonical lookup expression의 생성/파싱/평가와 이에
  필요한 회귀 검증으로 한정한다. Pl@ntNet endpoint, 사진 전송, 확률 래스터 샘플링,
  UI 문구, write-back 필드 정책은 변경하지 않는다.

- **C-CTLD-003:** QField의 runtime expression 평가를 우선 검증하되, 동일 식은 QGIS
  3.44 `QgsExpression` runtime에서도 검증 가능해야 한다. 테스트는 문자열 토큰만
  확인하는 정적 검사로 끝나지 않고 parser/evaluation 결과를 관찰해야 한다.

- **C-CTLD-004:** API key, 사진 bytes 및 개인정보를 테스트 출력/로그에 남기지 않는다.

- **C-CTLD-005:** 이 spec-writer 단계에서는 Python/QML application code와 test file을
  수정하지 않는다. 구현 및 회귀 테스트 변경은 본 명세와 후속 acceptance tests가
  승인된 뒤 각각의 clean-room 단계에서 수행한다.

## 4. Assumptions

- **A-CTLD-001:** 로컬 원인 증거인 “생성된 중첩 expression의 닫는 괄호 하나 부족 →
  QGIS 3.44 parser의 `Incomplete expression`”은 구현/테스트 단계에서 실제
  expression 문자열과 `QgsExpression.hasParserError()` 또는 동등한 parser 결과로
  재확인한다.

- **A-CTLD-002:** D-95가 정의한 canonical layer의 논리 표시명은
  `식물 분류 참조표`이고, lookup에 필요한 필드는
  `scientific_name_without_authority`, `accepted_ktsn`, `ktsn`, `taxon_status`,
  `korean_name`, `scientific_name` 계열이다.

- **A-CTLD-003:** “후보가 표시된다”는 것은 유효한 매칭 후보에 대해 기존 후보 카드가
  생성되고, 카드에 canonical Korean/scientific/KTSN 값이 전달되는 것을 뜻한다.
  사진 API 자체의 네트워크 성공 여부는 이 결함의 parser 회귀 테스트에서 별도
  deterministic response fixture로 대체한다.

## 5. Edge Cases

- **E-CTLD-001:** canonical layer는 존재하지만 lookup 이름과 일치하는 row가 없다.
  `available=true, matched=false` 계열의 기존 의미를 유지한다.

- **E-CTLD-002:** 하나의 정규화된 scientific name이 서로 다른 accepted group에
  연결된다. ambiguous 표시/제외를 유지하고 임의의 accepted row를 고르지 않는다.

- **E-CTLD-003:** 직접 매칭 row 또는 accepted row에 KTSN, 국명, 학명 등 필수값이
  비어 있거나 malformed하다. lookup failure/invalid-row의 기존 fail-closed 의미를
  유지하고 잘못된 `selected_*`를 반환하지 않는다.

- **E-CTLD-004:** canonical layer가 없거나 expression context가 없는 경우. 기존
  `canonical_taxonomy_layer_missing`, `canonical_expression_unavailable` 등
  원인 구분과 fail-closed 동작을 유지한다.

- **E-CTLD-005:** 명시적으로 legacy compatibility project인 경우. canonical parser
  수정으로 legacy CSV lookup의 기존 결과가 바뀌지 않아야 한다.

## 6. Out of Scope

- D-95의 canonical workbook 교체, 레이어 schema/display name 변경, 참조표 재생성,
  provenance 변경 또는 legacy source 제거/복원.
- 새로운 taxonomy matching 규칙, synonym resolution 규칙, ambiguity 해소 규칙 또는
  fallback 정책.
- Pl@ntNet API 호출/인증/timeout, 사진 리사이즈, QField 권한, GPS/현재 위치,
  occurrence-probability raster lookup.
- 후보 카드 디자인, 한국어 문구 변경, 새 write-back 메커니즘 또는 selected 필드의
  직접 입력 정책 변경.
- 이미 생성된 프로젝트의 migration.

## 7. Acceptance Criteria

- **AC-CTLD-001:** QGIS 3.44 runtime에 유효한 canonical taxonomy layer와 하나의
  deterministic matched row를 준비하고, 생성된 canonical lookup expression을
  `QgsExpression`으로 파싱/평가했을 때 parser error가 없어야 한다. 평가는
  `selected_ktsn`, `selected_korean_name`, `selected_scientific_name`을 포함한
  유효한 lookup map을 반환해야 한다. `Incomplete expression` 또는
  `canonical_taxonomy_lookup_failed`는 실패다.

- **AC-CTLD-002:** QField identification response fixture에 canonical 매칭 후보가
  하나 이상 있을 때, canonical lookup 후 후보 모델에 후보가 표시되고 해당 후보의
  `selected_ktsn`, `selected_korean_name`, `selected_scientific_name` 값이 canonical
  accepted row의 값과 일치해야 한다. 이 검증은 실제 Pl@ntNet API key/사진 bytes를
  사용하지 않는 deterministic runtime regression test여야 한다.

- **AC-CTLD-003:** 유효한 canonical layer에서 no-match, ambiguous, malformed-row
  fixture를 각각 평가했을 때, 기존의 no-match/ambiguous/invalid fail-closed 결과와
  reason semantics가 유지되어야 하며 임의의 selected 값이 반환되지 않아야 한다.

- **AC-CTLD-004:** canonical layer가 없거나 expression context가 없는 fixture에서
  기존 canonical-unavailable reason이 반환되어야 한다. 이 경우에도 legacy CSV
  matcher가 자동 호출되어서는 안 된다.

- **AC-CTLD-005:** 명시적 `legacy_reference_compatibility` fixture에서는 기존 legacy
  CSV lookup 경로가 계속 사용되고, canonical parser defect fix가 legacy fallback의
  결과/선택 조건을 변경하지 않아야 한다.

- **AC-CTLD-006:** regression suite는 generated QML에서 실제로 사용되는 expression
  문자열을 대상으로 해야 하며, 괄호 수나 특정 문자열 token만 맞는지 검사하는
  정적 테스트만으로 AC-CTLD-001/002를 충족했다고 판정하지 않아야 한다.

## 8. Traceability and Existing-Spec Decision

이 결함은 D-95의 요구사항 변경이 아니라 승인된 요구사항의 conformance defect다.
따라서 승인된 [`specs/qfield-project-builder.md`](qfield-project-builder.md)의 내용을
수정하거나 새 Decision Log를 추가할 필요가 없다.

구현 단계에서는 다음 D-95 항목과 추적성을 연결해야 한다.

| Defect criterion | Existing D-95 baseline | Required test evidence |
|---|---|---|
| AC-CTLD-001/002 | FR-QPB-140, canonical lookup behavior in §13.3a, and the approved D-95 canonical project regression contract | QGIS 3.44 parser/evaluation runtime test plus QField-shaped candidate-model regression |
| AC-CTLD-003/004 | D-95 fail-closed behavior and canonical-layer availability contract | no-match/ambiguous/malformed/missing-layer fixtures |
| AC-CTLD-005 | D-95 explicit legacy compatibility boundary | legacy compatibility regression fixture |
| AC-CTLD-006 | D-95 generated-project QML/runtime contract | generated-QML expression extraction followed by actual parser/evaluation |

후속 `test-designer`는 새 acceptance traceability 파일을 작성하고, 기존
`test_d95_canonical_ktsn_project_regression.py` 및 관련 QML/runtime test와의 중복 여부를
판단해야 한다. 본 단계에서는 기존 acceptance test나 traceability 파일을 수정하지
않는다.

## 9. Open Questions

- 없음. 사용자 제공 원인과 D-95의 보존 범위가 충분히 구체적이므로, 추가적인 제품
  선택이나 legacy 정책 결정은 필요하지 않다.
