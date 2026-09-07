# Feature: 통합 HTML report 수정 — 중복 열, GPKG/QGIS 지도, 개요 집계, fallback, 테마

> Status: DRAFT — awaiting user review and explicit approval
> Owner: spec-writer
> Last updated: 2026-09-02
> Extends without replacing: `specs/html-report-integrated-followup.md`, `specs/html-report-integrated-followup-hardening.md`, `specs/html-report-map-valid-geometry-collection.md`, and `specs/html-report-interactive-analytics.md`

## 1. Summary

이 명세는 통합 HTML report에서 동일 의미의 조인 열이 중복으로 노출되는 문제, GeoPackage의
유효한 geometry가 있어도 지도가 비어 보이는 문제, survey type마다 카드 이름·개수·순서·직접
집계 원본이 다른 개요 카드(Types 1–3의 `총 종수` 포함), 통합표와 fallback 상태의 불명확성, 실제로 전환되지 않는 테마
버튼을 함께 수정한다. 통합표·상세·지도는 survey data group의 조인 결과를 계속 사용하지만,
개요 카드는 그 joined row에서 다시 distinct하지 않고 활성 유형에 지정된 schema-defined
레이어의 record/date/name을 직접 집계한다.

첨부 자료를 기준으로 현재 문제를 재현할 수 있는 기준 사례는 다음과 같다. `test2.gpkg`의
`gpkg_contents`에는 `inventory_observation` 공간 테이블이 있고,
`gpkg_geometry_columns`는 `geom`, `POINT`, EPSG:4326을 선언한다. 해당 테이블은 5행 모두
비어 있지 않은 geometry를 가진다. 반면 `test2_joined.csv`에는
`selected_korean_name`과 `inventory_observation__selected_korean_name` 같은 동일 의미의
중복 열이 함께 존재한다. 현재 `test2_report 2.html`은 직접 SQLite 수집 실패 후 fallback을
사용하며, 이 사례의 geometry를 좌표 변환 API 미사용으로 무효 처리하여 지도에 표시하지
않는다.

## 2. Compatibility and terminology

### 2.1 Source authority

- **Survey data group**: 활성 survey type의 schema가 정의하는 `site`, `plot`, `survey`,
  `observation`, `inventory_observation`, `community` 등의 원본 테이블 집합이다.
- **Joined row**: schema에 정의된 UUID/FK 경로를 따라 survey data group을 조인한 하나의
  관찰/커뮤니티 원본 행이다. 조인 결과의 반복된 부모 값은 행 보존을 위해 반복될 수 있다.
- **Observation record**: 표시명이나 geometry가 아니라 관찰 원본 record로 식별된다. 개요의
  `관찰 수`는 Type 1에서 `inventory_observation` 레이어 record 수, Type 2/3에서
  `observation` 레이어 record 수를 직접 센다. Type 4는 식물 관찰 레코드가 없으므로
  `community.community_id`를 관찰 수로 위장하지 않는다.
- **Valid KTSN value**: `selected_ktsn`이 `null`이 아니고, 빈 문자열도 아니며, 공백만으로
  이루어지지 않은 원본 값이다. `총 종수`는 이러한 유효 값의 distinct 수를 직접 source
  layer에서 세며, joined row나 join fan-out으로 값을 반복해도 증가하지 않는다.
- **Overview-card `총 종수` (Types 1–3)**: 이는 species occurrence/chart의 species-key
  cardinality가 아니라 직접 source layer의 valid `selected_ktsn` distinct 수다. 따라서 두
  selected name이 비어 있고 valid KTSN만 있는 record도 이 카드에는 포함되지만, 기존
  FR-HRA-012의 species occurrence/chart group이나 “미동정” bucket에는 포함되지 않는다.
  이 교차 명세 reconciliation은 D-IHRM-008 및 D-HRA-004에 기록한다.
- **Spatial layer authority**: QGIS 프로젝트의 schema-defined 공간 레이어와 그
  `QgsFeature.geometry()`/레이어 CRS를 사용하여 어떤 공간 레이어와 feature가 지도 대상인지
  확인한다. 완전한 저장 데이터 수집의 기본 원본은 현재 저장된 GeoPackage와 그 표준
  metadata이며, QGIS 레이어는 공간 feature의 유효성·CRS·렌더링 가능성을 확인하는
  공간 레이어 기준이다.

### 2.2 Survey-type map and card mapping

기존 Type 1–4 anchor 규칙과 UUID/FK 조인, one-to-many 행 보존은 그대로 유지한다.

| 유형 | 통합 조인 | 지도 anchor | 개요 카드와 직접 집계 원본 |
|---|---|---|---|
| Type 1 `simple_inventory` | `inventory_observation` | `inventory_observation.geom` | **표시 순서:** `총 조사일 수`: `inventory_observation.observed_at`의 유효 calendar date distinct 수; `관찰 수`: `inventory_observation` 레이어 record 수; `총 종수`: 유효한 `inventory_observation.selected_ktsn`의 distinct 수. `조사지 수`·`조사구 수` 카드는 없음. |
| Type 2 `temporary_plots` | `site → survey → observation` | `survey.plot_geom`; `site`는 별도 polygon | **표시 순서:** `조사지 수`: `site` 레이어 record 수; `조사구 수`: `survey` 레이어 record 수; `총 조사일 수`: `survey.survey_date`의 유효 calendar date distinct 수; `관찰 수`: `observation` 레이어 record 수; `총 종수`: 유효한 `observation.selected_ktsn`의 distinct 수. |
| Type 3 `permanent_plots` | `site → plot → survey → observation` | `plot.plot_geom`; 없으면 `survey` fallback | **표시 순서:** `조사지 수`: `site` 레이어 record 수; `조사구 수`: `plot` 레이어 record 수; `총 조사일 수`: `survey.survey_date`의 유효 calendar date distinct 수; `관찰 수`: `observation` 레이어 record 수; `총 종수`: 유효한 `observation.selected_ktsn`의 distinct 수. |
| Type 4 `vegetation_mapping` | `site → survey → community` | `community.community_geom`; `site`는 기존 규칙에 따름 | **표시 순서(변경 없음):** `조사지 수`: `site` 레이어 record 수; `고유군락 수`: `community.community_name`의 distinct 수; `총군락 수`: `community` 레이어 record 수; `총 조사일 수`: `survey.survey_date`의 유효 calendar date distinct 수. `조사구 수`·`관찰 수`·`총 종수` 카드는 없음. |

## 3. Functional Requirements

### 3.1 Join-first integrated data and duplicate semantic columns

- **FR-IHRM-001:** Report 생성은 먼저 활성 survey type의 모든 접근 가능한 survey data
  group을 원본 안정 ID와 schema UUID/FK 경로로 조인한 뒤, 통합표·상세·차트·CSV가 동일한
  joined-row 집합을 사용하도록 해야 한다. 지도 anchor의 개수나 부모 레코드의 반복 횟수가
  관찰 행을 대신할 수 없다. 개요 카드는 §3.3의 유형별 직접 레이어 집계 계약을 따르며,
  joined-row 집합을 카드 count의 원본으로 사용하지 않는다.
- **FR-IHRM-002:** 통합표의 논리 필드는 원본 table, field, FK 경로 및 의미 별칭을 포함한
  provenance identity로 먼저 분류해야 한다. 단순히 화면 표시명이나 평탄화된 문자열만으로
  서로 다른 source field를 동일 열로 합치면 안 된다.
- **FR-IHRM-003:** 동일 joined row에서 같은 의미로 분류된 source field가 모두 존재하고
  값이 동일하면(0, `false`, 빈 문자열, `null`을 임의로 누락시키지 않음) canonical 열
  하나만 통합표와 CSV에 노출한다. source-to-canonical 매핑은 payload/detail에도 동일하게
  적용되어야 하며, `selected_korean_name`과
  `inventory_observation__selected_korean_name`은 이 규칙으로 한 번만 표시된다.
- **FR-IHRM-004:** 값이 없는 source와 값이 있는 source는 값 있는 source를 canonical 열에
  표시할 수 있지만, source 값의 존재 여부와 선택된 provenance를 기술 메타데이터에
  보존해야 한다. 두 source가 모두 없으면 빈 값으로 표시한다.
- **FR-IHRM-005:** 동일 의미 source field의 present 값이 서로 다르거나 한쪽이 `null`이고
  다른 쪽이 비어 있지 않은 값이면 조용히 덮어쓰지 않는다. 해당 필드는 source별 안정
  provenance 열로 분리하고, 사용자에게 충돌이 있었음을 표시한다. 분리 열은
  `source_table__source_field` 정규화 키와 결정적인 `_2`, `_3` suffix 규칙을 사용하며
  값은 원래 source 열에 그대로 남아야 한다.
- **FR-IHRM-006:** 모든 출력 열은 유일한 내부 key, 한 번의 위치, 한 번의 visible label
  mapping을 가져야 한다. 열 정렬·필터·상세·CSV는 동일한 column definition을 사용해야
  하며, unchanged schema/data를 재생성하면 동일한 key·순서·값 mapping을 산출해야 한다.

### 3.2 GeoPackage geometry and QGIS spatial-layer map collection

- **FR-IHRM-007:** 기본 수집은 현재 저장된 GPKG를 read-only로 열고
  `gpkg_contents`, `gpkg_geometry_columns`, 필요한 `gpkg_spatial_ref_sys`를 검사하여
  등록된 접근 가능 공간 테이블, geometry column, geometry type, source CRS, 원본 record
  identity 및 모든 허용 attribute를 수집해야 한다. 현재 로드된 레이어 목록만으로 완전성을
  판단하면 안 된다.
- **FR-IHRM-008:** 수집된 공간 테이블은 활성 survey type의 schema-defined QGIS 공간
  레이어와 table/geometry-column identity를 대조한다. QGIS feature geometry와 레이어 CRS를
  지도용 serialized geometry의 기준으로 사용하며, GPKG 행과 QGIS feature는 안정 UUID로
  연결한다. `test2.gpkg` 기준 `inventory_observation.geom`의 5개 EPSG:4326 POINT는 모두
  map-eligible 후보가 되어야 한다.
- **FR-IHRM-009:** geometry는 GPKG binary header/WKB 또는 QGIS geometry에서 X/Y를 읽고,
  source CRS가 EPSG:4326이면 좌표 변환 API가 없어도 X/Y identity 경로로 WGS84 GeoJSON을
  생성해야 한다. 다른 CRS는 QGIS의 명시적 coordinate transform으로 EPSG:4326/WGS84로
  변환한다. Z/M은 제거하며 좌표를 Z/M, 속성, FK, centroid 또는 다른 레코드에서 발명하지
  않는다.
- **FR-IHRM-010:** 빈 geometry, malformed WKB, non-finite/out-of-range X/Y, 알 수 없는 CRS,
  변환 실패는 해당 record만 map-invalid로 표시하고 원본 attribute·joined row·개요 집계·CSV는
  보존한다. 한 행의 실패가 같은 테이블의 다른 행 수집 또는 렌더링을 중단시키면 안 된다.
- **FR-IHRM-011:** Type 1–4 지도는 기존 anchor 규칙을 따른다. 유효한 local geometry가 한
  개라도 있으면 전역 `유효한 도형 없음`을 표시하지 않는다. eligible feature가 하나도
  없을 때만 그 메시지와 invalid/missing/omitted 사유 및 개수를 표시한다.

### 3.3 Overview cards

- **FR-IHRM-012:** 개요 카드는 survey data group 조인과 독립적으로, 활성 유형의
  schema-defined source layer에서 직접 집계해야 한다. 각 카드의 입력은 해당 layer의 record,
  date field, name field 또는 KTSN field이며, joined row·join fan-out·통합표 행 수를 투영하거나
  distinct-count의 원본으로 사용하면 안 된다.
- **FR-IHRM-013:** 카드의 이름·개수·집계는 §2.2의 유형별 mapping을 정확히 따라야 한다.
  카드의 표시 순서도 다음과 같이 정확히 따라야 한다.
  - Type 1은 순서대로 `총 조사일 수`, `관찰 수`, `총 종수`를 표시한다. 전자는
    `inventory_observation.observed_at`의 유효 calendar date를 distinct하여 세고, 둘째는
    `inventory_observation` 레이어 record 수를 세며, 셋째는 유효한
    `inventory_observation.selected_ktsn` 값을 distinct하여 센다.
  - Type 2는 순서대로 `조사지 수`, `조사구 수`, `총 조사일 수`, `관찰 수`, `총 종수`를
    표시한다. `조사지 수`는 `site` 레이어 record 수, `조사구 수`는 `survey` 레이어 record 수,
    `총 조사일 수`는 `survey.survey_date`의 유효 calendar date distinct 수, `관찰 수`는
    `observation` 레이어 record 수, `총 종수`는 유효한 `observation.selected_ktsn`의 distinct
    수이다.
  - Type 3은 순서대로 `조사지 수`, `조사구 수`, `총 조사일 수`, `관찰 수`, `총 종수`를
    표시한다. `조사지 수`는 `site` 레이어 record 수, `조사구 수`는 `plot` 레이어 record 수,
    `총 조사일 수`는 `survey.survey_date`의 유효 calendar date distinct 수, `관찰 수`는
    `observation` 레이어 record 수, `총 종수`는 유효한 `observation.selected_ktsn`의 distinct
    수이다.
  - Type 4는 기존 순서대로 `조사지 수`, `고유군락 수`, `총군락 수`, `총 조사일 수`만 표시한다.
    `조사지 수`는 `site` 레이어 record 수, `고유군락 수`는 실제 schema field
    `community.community_name`의 distinct 수, `총군락 수`는 `community` 레이어 record 수,
    `총 조사일 수`는 `survey.survey_date`의 유효 calendar date distinct 수이다. `community`를
    관찰 수로 라벨링하지 않으며 `조사구 수`, `관찰 수`, `총 종수` 카드는 없다.
- **FR-IHRM-014:** 각 카드의 source layer가 활성 schema에 존재하지만 0행이거나 집계 대상
  값이 하나도 없으면 값 `0`을 표시한다. 필요한 hierarchy/source layer가 schema에 없으면
  `해당 레벨 부재`로 명시하며 `0`으로 대체하지 않는다. 단, §2.2에서 해당 유형에 의도적으로
  정의하지 않은 카드는 렌더링하지 않는다. 유효하지 않거나 누락된 날짜는 `총 조사일 수`에
  포함하지 않고 그 개수를 limitation으로 표시하며, `null`·빈 문자열·공백만인 KTSN은 `총 종수`에
  포함하지 않고 그 제외 개수를 limitation으로 표시한다. 카드에는 직접 source layer와
  date/name/KTSN distinct basis가 보인다.

### 3.4 Integrated table, fallback disclosure, and theme

- **FR-IHRM-015:** 로컬 source가 하나라도 접근 가능하면 통합표 DOM/데이터 모델을 반드시
  생성하고, zero-row source도 안정적인 header와 빈 상태를 렌더링해야 한다. 통합표가
  비어 보이는 경우에도 원인은 empty data, collection error, join error, render error 중
  하나로 사용자에게 구분되어야 한다.
- **FR-IHRM-016:** 직접 GPKG 접근이 실패할 때만 허용된 QGIS loaded spatial-layer
  fallback을 사용한다. fallback 사용 시 실패한 direct path, fallback source, 성공한
  table/row 목록, 알려진 누락 table/row, 확인할 수 없는 scope와 count를 표시해야 하며,
  `complete`, `전체 수집`, `완전한 GPKG inventory`라고 주장하면 안 된다. fallback으로
  성공한 행은 지도·통합표·상세·카드·필터·정렬·CSV에서 계속 사용할 수 있어야 한다.
- **FR-IHRM-017:** 직접 수집 중 특정 공간 테이블/행만 실패한 경우 성공한 다른 공간 테이블과
  행을 유지하고, 실패 범위를 직접-access partial limitation으로 표시한다. 전체 fallback으로
  실패 범위를 숨기거나 0으로 대체하면 안 된다.
- **FR-IHRM-018:** report는 밝은/어두운 테마 토글 버튼을 제공해야 한다. 클릭과 키보드
  활성화가 모두 `document.documentElement`의 실제 theme state와 CSS 변수/표면을 바꾸고,
  버튼의 label 및 `aria-pressed`가 현재 상태와 일치해야 한다. 가능한 경우 localStorage에
  preference를 저장하고, 저장소 접근 불가 시에도 현재 문서 안에서는 전환되어야 한다.
  테마 변경은 map view, joined filter/sort, expanded sections, selected detail, chart state,
  source data 및 CSV header를 변경하지 않는다.

## 4. Constraints

- **C-IHRM-001:** 기존 spec의 Type 1–4 schema, UUID/FK join, anchor/fallback, CSV quoting,
  local-first, secret/attachment exclusion, QField project-folder output, Leaflet/D3 local
  bundling 요구는 계속 적용한다. 이 명세는 기존 ID를 삭제·재번호화·약화하지 않는다.
- **C-IHRM-002:** GPKG/QGIS 수집과 report 렌더링은 read-only이다. source schema, geometry,
  CRS, record, UUID, relation을 수정하거나 자동 repair하지 않는다.
- **C-IHRM-003:** join key는 schema-defined UUID/FK뿐이다. 표시명, 동일 좌표, 행 위치,
  근접성, centroid, photo/path는 join 또는 geometry 보정 수단이 아니다.
- **C-IHRM-004:** local report 기능은 네트워크·VWorld key·원격 tile 없이도 동작해야 한다.
  원격 basemap 실패는 local geometry, 통합표, 카드, 테마, CSV를 막지 않는다.
- **C-IHRM-005:** 일반 사용자 표/카드/차트/상세에는 raw long English source name이나 내부
  machine key를 표시하지 않는다. 기술 dictionary/provenance가 필요하면 명시적인 제한/상세
  영역에서만 보인다.
- **C-IHRM-006:** 이 단계는 명세만 변경한다. acceptance tests, application code, fixtures,
  generated artifacts 및 Git checkpoint는 사용자 승인 후 별도 역할에서 처리한다.
- **C-IHRM-007:** `총 종수`는 Type 1의 `inventory_observation.selected_ktsn` 또는 Type 2/3의
  `observation.selected_ktsn`을 직접 읽어서만 계산한다. join 결과, 표시용 alias, 관찰 record
  수 또는 다른 종명 field로 KTSN을 보완·추정·중복 제거하지 않으며, 동일 source record/value가
  join으로 여러 번 나타나도 한 번만 계산한다.

## 5. Assumptions

- **A-IHRM-001:** 첨부된 `test2.gpkg`의 4326 POINT는 정상적인 직접 GPKG 또는 QGIS geometry
  읽기 경로로 해석할 수 있으며, 동일 사례에서 좌표 변환 API 부재만으로 무효 처리하지 않는다.
- **A-IHRM-002:** `selected_korean_name`, `selected_scientific_name`, `selected_ktsn`은
  기존 보고서의 identity alias 규칙에 따라 동일 의미 비교 후보가 될 수 있다. 의미가 다른
  source field는 같은 visible label을 가져도 병합하지 않는다.
- **A-IHRM-003:** 날짜 key는 ISO-like datetime에서 calendar date 부분을 사용하고, 형식이
  불명확하거나 달력상 유효하지 않은 값은 세지 않고 limitation으로 남긴다.
- **A-IHRM-004:** Type 2의 `survey`는 임시 조사구의 조사구 수 대용이며, 이는 사용자 요구에
  따른 카드 표시 규칙이다. Type 3의 조사구는 `plot` 원본이다.
- **A-IHRM-005:** fallback은 기존 허용 범위인 loaded QGIS spatial layer 수집에 한정된다.
  새로운 임의 table 탐색 API나 외부 서버를 fallback으로 도입하지 않는다.
- **A-IHRM-006:** 현행 source schema에서 `selected_ktsn`은 Type 1의
  `inventory_observation`과 Type 2/3의 `observation`에 존재한다. `총 종수`의 유효성 판정은
  값이 `null`·빈 문자열·공백 전용인지에 한정하며, 그 밖의 KTSN 정규화나 유효성 보정은 이
  명세에서 요구하지 않는다.

## 6. Edge Cases

- **E-IHRM-001:** 동일 semantic source가 모든 행에서 같은 값이면 canonical 열 하나만 남기고,
  값이 다른 행이 하나라도 있으면 source별 열과 충돌 notice를 유지한다.
- **E-IHRM-002:** `0`, `false`, `""`, present `null`, absent key를 서로 같은 값으로 추정하지
  않는다. 값의 presence와 final-key mapping을 보존한다.
- **E-IHRM-003:** 여러 source field가 같은 normalized base key를 만들면 schema order에 따라
  `_2`, `_3`를 부여한다. 반복 export에서 suffix가 바뀌면 안 된다.
- **E-IHRM-004:** direct GPKG access가 불가하지만 fallback에서 `inventory_observation`의
  5행을 읽을 수 있는 경우, 5행은 표시하되 direct GPKG의 전체 table/row 완전성은 unknown으로
  표시한다.
- **E-IHRM-005:** 한 geometry row가 malformed이어도 같은 table의 다음 valid row는 계속
  map-render한다. invalid row는 table/CSV/비geometry 집계에 남는다.
- **E-IHRM-006:** GPKG metadata에는 geometry table이 있으나 QGIS layer가 로드되지 않으면,
  직접 GPKG 수집 결과를 사용하고 QGIS layer availability limitation만 별도 표시한다.
- **E-IHRM-007:** source CRS가 4326인데 QGIS transform 객체가 없으면 direct XY identity를
  사용한다. non-4326 transform이 불가하면 해당 row만 map-invalid로 남긴다.
- **E-IHRM-008:** Type 3 plot geometry가 없고 survey geometry가 valid이면 survey fallback을
  사용하고 상세에 fallback 출처를 표시한다. observation geometry는 대체 좌표가 아니다.
- **E-IHRM-009:** §2.2에서 카드 source로 지정된 `site`, `plot`, `survey`, `observation`,
  `inventory_observation`, `community` 레이어가 존재하지만 0행이면 해당 카드 값은 0이다.
  필요한 hierarchy/source layer가 schema에 없으면 `해당 레벨 부재`이며, Type 1의
  `조사지 수`/`조사구 수`와 Type 4의 `조사구 수`/`관찰 수`/`총 종수`처럼 mapping에서 정의하지
  않은 카드는 표시하지 않는다.
- **E-IHRM-010:** `inventory_observation.observed_at` 또는 `survey.survey_date`에 같은
  유효 calendar date가 여러 record에 있어도 날짜 카드는 하루로 센다. invalid/missing date는
  총 조사일 수에 포함하지 않고 건수를 표시한다.
- **E-IHRM-011:** 테마 버튼을 반복 클릭하거나 localStorage가 차단되어도 현재 DOM 상태,
  button state와 label은 일치해야 한다.
- **E-IHRM-012:** 하나의 `site`, `plot`, `survey`, `observation`, 또는 `community` record가
  one-to-many join으로 여러 통합표 행에 나타나더라도 카드 값은 바뀌지 않는다. 카드는 joined
  row가 아니라 지정된 직접 source layer의 record/date/name/KTSN만 사용한다. Type 4에서
  `community_name` 값이 하나도 없으면 `고유군락 수`는 0이고, 같은 이름을 가진 여러
  `community` record는 하나의 고유군락으로 센다.
- **E-IHRM-013:** Type 1의 `inventory_observation.selected_ktsn` 또는 Type 2/3의
  `observation.selected_ktsn`이 `null`, 빈 문자열 또는 공백만이면 `총 종수`에서 제외하고
  limitation에 제외 건수를 보인다. 유효한 동일 KTSN 값이 여러 direct source record에 있거나
  하나 이상의 joined row에 반복되어도 `총 종수`에는 한 번만 센다. 유효 KTSN이 하나도 없으면
  `총 종수`는 0이다.

## 7. Out of Scope

- GeoPackage 데이터/스키마/geometry를 수정·repair·migrate하거나 새로운 survey type을 추가하는 일.
- FK가 없는 source를 proximity, display text, centroid, photo, 날짜, 행 위치로 추정하여
  join하거나 geometry를 생성하는 일.
- QField/QGIS third-party UI 자체의 테마 변경 또는 원격 basemap 서비스의 안정성 보장.
- 사용자 요구와 무관한 새 차트, 새 카드, 새 저장 위치, 새 credential 노출 경로.
- 이 Draft 승인 전의 acceptance-test 작성, application 구현, Git commit/push.

## 8. Acceptance Criteria

- **AC-IHRM-001:** Given the attached `test2_joined.csv`, when the integrated report data model
  is generated, then same-semantic `selected_korean_name` and
  `inventory_observation__selected_korean_name` values are represented by one canonical
  visible/export column, and the same rule applies to the corresponding scientific/KTSN fields.
  The five source observation values remain unchanged.
- **AC-IHRM-002:** Given two same-semantic source fields with equal values, missing values, and
  present `0`/`false`/`null`, when table/detail/payload/CSV are generated, then no falsey value is
  lost, one canonical column is used only when the equality/presence rule allows it, and the
  source-to-canonical provenance is stable.
- **AC-IHRM-003:** Given a row where same-semantic source fields differ, when the report is
  generated, then no source value is overwritten or silently selected; source-specific stable
  columns retain both values, the collision is visibly disclosed, and repeated export gives the
  same suffix/key/order.
- **AC-IHRM-004:** Given source fields whose normalized names collide, when filtered, sorted,
  detailed, and exported, then every output projection uses one shared unique column definition,
  CSV headers are unique and deterministic, and values stay under the exact source-assigned final
  key.
- **AC-IHRM-005:** Given the attached `test2.gpkg`, when the report is generated, then metadata
  identifies `inventory_observation.geom` as `POINT` in EPSG:4326, five non-null geometry rows are
  collected, and the report does not classify them as invalid solely because a coordinate
  transform API is unavailable.
- **AC-IHRM-006:** Given the same GPKG and a QGIS spatial layer for `inventory_observation`, when
  the map opens, then all five valid local POINT features render at their WGS84 coordinates,
  feature details retain their stable inventory UUID and joined attributes, and
  `유효한 도형 없음` is absent.
- **AC-IHRM-007:** Given one malformed geometry row and at least one valid later row, when the
  report is generated, then generation succeeds, the valid row renders, the malformed row remains
  in the integrated table/detail/CSV and non-geometry counts, and its stable invalid reason appears
  in the limitation notice.
- **AC-IHRM-008:** Given Type 1–4 fixtures, when cards are rendered, then each type displays
  exactly the card names, number, and order in §2.2: Type 1 displays `총 조사일 수`, `관찰 수`,
  `총 종수`; Type 2/3 display `조사지 수`, `조사구 수`, `총 조사일 수`, `관찰 수`, `총 종수`;
  and Type 4, unchanged, displays `조사지 수`, `고유군락 수`, `총군락 수`, `총 조사일 수`.
  Type 4 displays no `총 종수`, uses the actual `community.community_name` field for
  `고유군락 수`, and never labels community rows as observations.
- **AC-IHRM-009:** Given Type 1–4 fixtures with direct schema-defined layer records, when cards
  are computed, then Type 1 counts `inventory_observation` records and distinct valid
  `observed_at` dates and distinct valid `inventory_observation.selected_ktsn` values; Type 2
  counts `site`, `survey`, and `observation` layer records, distinct valid `survey.survey_date`
  dates, and distinct valid `observation.selected_ktsn` values; Type 3 counts `site`, `plot`,
  and `observation` layer records, distinct valid `survey.survey_date` dates, and distinct valid
  `observation.selected_ktsn` values; and Type 4 counts `site` and `community` layer records,
  distinct `community.community_name` values, and distinct valid `survey.survey_date` dates.
  For Types 1–3, valid KTSN values from records with both selected name fields empty are included
  in `총 종수` despite being excluded from species occurrence/chart groups and “미동정” under
  FR-HRA-012.
  A record or KTSN value repeated by a joined one-to-many result does not change any card value.
  Missing/invalid dates, invalid KTSN values, and absent-versus-empty source layers are separately
  disclosed.
- **AC-IHRM-010:** Given locally readable source data with zero or more joined rows, when the
  report opens, then the integrated table is present with its stable header and truthful empty or
  populated state. Filter, sort, detail, and CSV use the same joined-row data set.
- **AC-IHRM-011:** Given direct GPKG failure with a successful partial fallback, when the report
  opens, then fallback source, failed path, successful reads, known omissions, unknown/unverified
  scope and non-complete status are visible; successful fallback rows remain usable in table,
  map, details, cards, filter, sort and CSV.
- **AC-IHRM-012:** Given a report in light theme, when the user clicks or keyboard-activates the
  theme button, then the document visibly changes to dark theme, the button label and
  `aria-pressed` change accordingly, and a second activation returns to light theme without
  changing rows, filters, sort, map state, expanded sections, details or CSV headers. If storage
  is available, reopening honors the saved preference; if not, current-document switching still
  works.
- **AC-IHRM-013:** Given Type 1–3 direct source layers containing duplicate valid KTSN values,
  KTSN-only records whose two selected name fields are empty, `null`, empty-string, and
  whitespace-only `selected_ktsn` values, plus joined rows that repeat those source records, when
  `총 종수` is computed, then it equals the number of distinct valid KTSN values in the specified
  direct source layer, including each valid KTSN-only value; every invalid KTSN is excluded and
  disclosed in the limitation; neither duplicate direct records nor join repetition inflates the
  count; and the KTSN-only records remain excluded from species occurrence/chart grouping and
  “미동정”.

## 9. Open Questions

None for the five requested behaviors. Existing unresolved questions in the extended Draft specs
remain governed by their own approval process and are not silently resolved by this document.

## 10. Decision Log

- **D-IHRM-001** (2026-09-02, Category C — duplicate semantic join columns): The stakeholder
  explicitly requested removal of repeated fields such as `selected_korean_name` and
  `inventory_observation__selected_korean_name`. Equal same-semantic values collapse to one
  canonical column; differing values remain source-provenanced rather than being overwritten.
- **D-IHRM-002** (2026-09-02, Category C — GPKG/QGIS geometry authority): The stakeholder
  explicitly requested that the map-not-displayed issue be resolved from actual GeoPackage
  geometry and QGIS spatial-layer data. A valid EPSG:4326 X/Y geometry must not be rejected solely
  because a transform API is unavailable; invalidity is isolated per row.
- **D-IHRM-003** (2026-09-02, Category C — join-first overview semantics): The stakeholder
  initially defined overview metrics using the survey data group join. This decision is
  superseded for card aggregation by D-IHRM-006; joined rows remain normative for the integrated
  table, detail, chart, CSV, and map-related requirements.
- **D-IHRM-004** (2026-09-02, Category C — integrated table and fallback transparency): The
  stakeholder explicitly required the integrated table to load and fallback limitations to be
  shown. Partial success must remain visible without a false complete-inventory claim.
- **D-IHRM-005** (2026-09-02, Category C — functional theme toggle): The stakeholder explicitly
  required the light/dark button to work in the generated report, including stateful UI feedback.
- **D-IHRM-006** (2026-09-02, Category C — type-specific direct-layer overview cards): The
  stakeholder explicitly replaced the prior joined-row card aggregation with direct
  schema-defined layer aggregation. Type-specific card names and counts are authoritative:
  Type 1 uses `inventory_observation`; Type 2 uses `site`, `survey`, and `observation`; Type 3
  uses `site`, `plot`, `survey`, and `observation`; Type 4 uses `site`, `survey`, and `community`,
  with `community.community_name` as the unique-community field. This replacement does not alter
  the existing join, map, or integrated-table contracts.
- **D-IHRM-007** (2026-09-02, Category C — Types 1–3 total-species overview card): The
  stakeholder explicitly instructed, “survey Type 1, 2, and 3 must each display a `총 종수`
  overview card.” The card directly distinct-counts valid `selected_ktsn` values from
  `inventory_observation` for Type 1 and `observation` for Types 2/3; `null`, empty, and
  whitespace-only values are excluded, and Type 4 has no such card. This addition supersedes the
  earlier type-specific card count/order statement in D-IHRM-006, §2.2, and FR-IHRM-013 only to
  the extent of adding this card and its stated placement; all other type-specific cards and
  their order remain as previously specified.
- **D-IHRM-008** (2026-09-02, Category C — reconciliation with D-HRA-002): The stakeholder
  clarified that the Types 1–3 overview-card label `총 종수` is the direct-layer distinct valid
  `selected_ktsn` measure in D-IHRM-007, including valid KTSN-only records. This is deliberately
  separate from the older species occurrence/chart species-key aggregation: under D-HRA-002,
  KTSN-only records remain excluded from those groups and must not create a “미동정” bucket. This
  decision supersedes only D-HRA-002's former exclusion from the overview-card total-species
  summary, preserving its species-key behavior, all direct-layer/no-join-fan-out rules,
  empty/invalid disclosure, and Type 4's lack of a species card. The mirrored historical and
  acceptance pointers are D-HRA-004, FR-HRA-013, and AC-HRA-010.

## 11. References and approval gate

Normative references: `CLAUDE.md`, `docs/change-control.md`, `docs/product.md`,
`docs/architecture.md`, `specs/TEMPLATE.md`, `specs/html-report-integrated-followup.md`,
`specs/html-report-integrated-followup-hardening.md`,
`specs/html-report-map-valid-geometry-collection.md`, and
`specs/html-report-interactive-analytics.md`.

Observed fixtures: `/Users/tory/Downloads/test2.gpkg`,
`/Users/tory/Downloads/test2_joined.csv`, and `/Users/tory/Downloads/test2_report 2.html`.

This document remains DRAFT until the user explicitly approves it. After approval, a fresh
test-designer may create acceptance tests and traceability. Implementation must wait for the
separate acceptance-test approval gate.
