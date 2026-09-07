# Feature: 조사유형 2·3 조사지(site) 폴리곤 투명도

> Status: DRAFT — awaiting user review and approval
> Owner: spec-writer
> Last updated: 2026-09-01
> Extends: `specs/html-report-map-valid-geometry-collection.md`

## 1. Summary

조사유형 2·3에서 별도 표시되는 `site`(조사지) 폴리곤이 배경지도와 그 위의 조사
앵커를 가리지 않도록 투명도를 일정하게 적용한다. 사용자가 말한 “투명도 30%”는
렌더링 불투명도(opacity) 70%(0.70)로 해석한다.

## 2. Decision Log

- **D-MGC-016** (Category B; 2026-09-01): 사용자는 “조사유형 2, 3에서 조사지의
  레이어 투명도를 30%로 지정”하도록 요청했다. 이를 `site` 레이어의 유효
  불투명도 0.70으로 명시한다. 이 결정은 유형 2·3의 별도 site 폴리곤에만 적용하며,
  기존의 공간 앵커, 조인 속성, 데이터 보존 규칙은 변경하지 않는다.
- **D-SOP-001** (Category B; 2026-09-01): 사용자는 유형 2·3에서 조사지(`site`)
  레이어를 입력 가능한 geometry 레이어 순서의 마지막에 두도록 요청했다. 여기서
  “입력 가능한 geometry 레이어 순서”는 생성된 QGIS 프로젝트의 레이어 목록에서
  (1) geometry를 가지며 (2) 해당 프로젝트에서 편집 가능하도록 설정된 레이어만
  원래 목록 순서대로 추출한 부분순서로 정의한다. `site`는 이 부분순서의 마지막
  항목이어야 하며, 비편집·비공간·참조 레이어는 이 순서의 판정 대상에서 제외하고
  기존 목록의 상대적 순서와 HTML report 지도 동작은 유지한다.

## 3. Functional Requirements

- **FR-SOP-001:** 생성되는 조사유형 2의 `site` 폴리곤 레이어는 유효 불투명도
  `0.70`(투명도 30%)로 렌더링되어야 한다.
- **FR-SOP-002:** 생성되는 조사유형 3의 `site` 폴리곤 레이어는 유효 불투명도
  `0.70`(투명도 30%)로 렌더링되어야 한다.
- **FR-SOP-003:** 유형 2·3의 `site` 스타일은 생성된 QGIS 프로젝트에 저장되어야
  하며, 프로젝트를 다시 열어도 `site` 레이어의 유효 불투명도는 `0.70`이어야 한다.
- **FR-SOP-004:** HTML report의 유형 2·3 `site` 지도 feature/layer도 같은 유효
  불투명도 `0.70`으로 표시되어야 한다. 보고서가 복사되거나 오프라인으로 열려도
  로컬 도형 렌더링과 함께 이 스타일이 유지되어야 한다.
- **FR-SOP-005:** `site`의 채움과 외곽선이 함께 렌더링되는 경우, 해당 site 레이어의
  유효 레이어 불투명도 0.70을 일관되게 적용한다. 유형 2·3의 survey/plot 앵커,
  조인 결과, 배경지도에는 이 규칙을 적용하지 않는다.
- **FR-SOP-006:** 생성되는 조사유형 2·3 QGIS 프로젝트에서 `site`는 편집 가능한
  geometry 레이어들의 순서 중 마지막이어야 한다. 이 순서는 생성된 프로젝트
  레이어 목록에서 geometry가 있고 편집 가능하도록 설정된 레이어만 필터링한
  결과이며, 비편집·비공간·참조 레이어는 제외한다. `site`를 마지막으로 배치할
  때에도 그 밖의 레이어들의 상대적 순서, site의 별도 polygon 표시, HTML report의
  지도·표·CSV 동작은 변경하지 않는다.

## 4. Constraints

- **C-SOP-001:** 적용 범위는 유형 2·3에서 별도 렌더링되는 `site` 레이어뿐이다.
  유형 1 inventory, 유형 4 vegetation/community, 유형 2 survey 앵커, 유형 3
  plot/survey 앵커의 기존 스타일과 투명도는 변경하지 않는다.
- **C-SOP-002:** 이 기능은 시각 스타일만 변경한다. geometry, 좌표 앵커 우선순위,
  UUID/FK 조인, 속성/국명·학명·KTSN, 행 수, 필터·정렬, CSV 내용과 출력 형식은
  변경하지 않는다.
- **C-SOP-003:** 스타일 적용은 외부 네트워크, VWorld API 키, 원격 스타일 파일에
  의존하지 않아야 한다.
- **C-SOP-004:** 기존의 site 별도 feature 유지 및 유형별 지도 레이어 순서를
  보존한다.
- **C-SOP-005:** FR-SOP-006의 마지막 위치는 프로젝트의 전체 레이어 목록이 아니라
  편집 가능한 geometry 레이어 부분순서에만 적용한다. 따라서 비편집·비공간·참조
  레이어의 위치를 site 뒤로 이동하거나, HTML report용 지도 feature 순서를 QGIS
  편집 레이어 순서와 동일하게 변경해서는 안 된다.

## 5. Assumptions

- **A-SOP-001:** “투명도 30%”는 QGIS/HTML 렌더링에서 사람이 관찰하는 유효
  불투명도 70%를 뜻하며, 구현 방식(레이어 opacity 또는 동등한 채움/외곽선
  스타일)은 결과가 동일하면 제한하지 않는다.
- **A-SOP-002:** 유효한 site geometry만 렌더링한다. geometry가 없거나 유효하지
  않은 site의 경우 기존 geometry 제한사항·표·조인 보존 규칙을 따른다.
- **A-SOP-003:** HTML report는 기존 지도 데이터 모델의 별도 `site` map context를
  사용하며, site 투명도는 해당 context의 렌더링 스타일로 전달된다.

## 6. Edge Cases

- **E-SOP-001:** 유형 2·3에 site가 여러 개 있으면 모든 유효 site feature에 동일하게
  0.70을 적용하고, feature별 geometry와 속성을 섞거나 합치지 않는다.
- **E-SOP-002:** site polygon과 survey/plot 앵커가 겹쳐도 앵커의 좌표·geometry·조인
  속성은 변경하지 않고 site만 0.70으로 표시한다.
- **E-SOP-003:** VWorld/OSM 배경지도가 없거나 네트워크가 차단되어도 site의 로컬
  polygon과 0.70 스타일은 렌더링된다.
- **E-SOP-004:** site geometry가 전혀 유효하지 않으면 “유효한 도형 없음” 및 기존
  제한사항 처리를 따르며, 투명도 설정 때문에 보고서 생성이 실패해서는 안 된다.

## 7. Out of Scope

- 색상, 선 굵기, 대시 패턴, 라벨, 유형 2·3의 편집 가능한 geometry 레이어 부분순서
  에서 `site`를 마지막으로 두는 요구사항을 제외한 레이어 순서, 지도 확대 범위의
  변경.
- survey/plot/observation/community 등 site 이외 레이어의 투명도 조정.
- geometry 변환·정제, 조인 로직, HTML 표·CSV·통계·필터·정렬 변경.
- 새로운 배경지도, 외부 스타일 서비스, QGIS 스키마 또는 데이터 마이그레이션.

## 8. Acceptance Criteria

- **AC-SOP-001:** 유형 2 프로젝트를 생성하고 QGIS 프로젝트와 report를 열었을 때,
  별도 `site` 폴리곤이 존재하며 QGIS 프로젝트와 HTML report에서 모두 유효
  불투명도 `0.70`(투명도 30%)으로 표시된다.
- **AC-SOP-002:** 유형 3 프로젝트를 생성하고 QGIS 프로젝트와 report를 열었을 때,
  별도 `site` 폴리곤이 존재하며 QGIS 프로젝트와 HTML report에서 모두 유효
  불투명도 `0.70`(투명도 30%)으로 표시된다.
- **AC-SOP-003:** 유형 1·4 및 유형 2·3의 survey/plot 앵커를 비교했을 때, 해당
  레이어의 기존 geometry, 좌표, 스타일 계약이 site 투명도 변경으로 달라지지
  않는다.
- **AC-SOP-004:** 유형 2·3의 동일 입력에 대해 투명도 변경 전후를 비교했을 때,
  조인 attribute table과 CSV의 행 수·필드·값(국명·학명·KTSN 포함)이 동일하다.
- **AC-SOP-005:** 유효 site geometry가 있고 배경지도 키·네트워크가 없는 복사된
  report를 열었을 때, site polygon이 로컬 지도에 0.70 불투명도로 표시되고
  기존 앵커 geometry·상세·표·CSV가 계속 동작한다.
- **AC-SOP-006:** site geometry가 누락·무효인 유형 2·3 입력에서 report 생성이
  중단되지 않고 기존 제한사항/“유효한 도형 없음” 처리를 수행하며, 0.70 스타일
  적용 시도가 다른 유효 geometry나 데이터 보존을 손상시키지 않는다.
- **AC-SOP-007:** 유형 2·3 프로젝트를 생성했을 때, 생성된 전체 레이어 목록에서
  geometry를 가지며 편집 가능하도록 설정된 레이어만 원래 순서대로 추출하면
  `site`가 그 목록의 마지막 항목이다. 비편집·비공간·참조 레이어는 판정에서
  제외되고, 그 레이어들의 상대적 순서와 HTML report 지도 레이어/feature 동작은
  변경되지 않는다.

## 9. Traceability

| Requirement | Acceptance criteria | Verification surface |
|---|---|---|
| FR-SOP-001–002 | AC-SOP-001–002 | 유형 2·3 QGIS project/report site layer style |
| FR-SOP-003–004 | AC-SOP-001–002, AC-SOP-005 | generated project round-trip; standalone local HTML report |
| FR-SOP-005; C-SOP-001, C-SOP-004 | AC-SOP-003, AC-SOP-005 | site-only style scope and existing map layer order |
| FR-SOP-006; C-SOP-005; D-SOP-001 | AC-SOP-007 | generated project editable geometry-layer subset order |
| C-SOP-002; A-SOP-002 | AC-SOP-003–004, AC-SOP-006 | geometry/join/table/CSV regression checks |
| C-SOP-003; A-SOP-003; E-SOP-003 | AC-SOP-005–006 | offline/local report rendering |

## 10. Open Questions

- 없음.
