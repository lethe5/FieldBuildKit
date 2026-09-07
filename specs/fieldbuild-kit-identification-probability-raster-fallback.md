# Feature: 사진 동정의 종별 출현확률 래스터 샘플링 및 비차단 fallback

> Status: DRAFT — awaiting user review and approval
> Owner: spec-writer
> Last updated: 2026-09-06
> Extends: `specs/fieldbuild-kit-report-wizard-followup.md`, `specs/qfield-project-builder.md`,
> and the existing Pl@ntNet/KTSN/occurrence-probability contracts

## 1. Summary

조사유형 1·2·3에서 `사진으로 동정하기`를 실행하면 동정 결과의 각 후보 종에 대응하는
출현확률 래스터를 찾아 조사유형별 authoritative location에서 샘플링한다. 일부 종에
래스터가 없거나 현재 QField 빌드에서 사용할 수 있는 래스터 샘플링 경로가 없더라도, 이는
확률만 unavailable로 처리하는 비차단 상태이며 Pl@ntNet 동정, 후보 표시·선택, 기존
write-back 및 저장 흐름은 계속되어야 한다.

이 명세는 기존 EXIF 금지, 조사유형별 authoritative location, 후보 선택, write-back,
저장/reopen, 확률값·NoData 규칙을 유지하면서 “기기 내 래스터 샘플링 지원이 확인되지
않았습니다” 오류가 전체 동정을 막지 않도록 하는 보완이다.

## 2. 변경 분류 및 Decision Log

### 2.1 분류

**Category B — specification clarification/omission.** 기존 명세는 on-device probability
sampling을 in-scope으로 두고 위치가 없을 때 확률 계산을 생략하도록 했지만, (a) 후보 종별
래스터 파일 부재와 (b) QField/QGIS 샘플링 capability 부재가 동정 전체를 막지 않아야 한다는
실행 가능한 fallback 경계를 충분히 분리하지 않았다.

### 2.2 Decision Log

- **D-PRF-001** (2026-09-01, Category B clarification): 사용자는 다음과 같이
  명확히 했다: **“확률 계산은 필요합니다. 래스터는
  `storage/reference/rasters/bce_inverse_corrected_probability_maps`에 종별로 존재하며
  일부 종은 래스터가 없습니다. … 기기 내 raster sampling capability 경고는 전체 동정
  hard-block이어서는 안 되며, 가능한 실제 앱/QGIS 경로 또는 bundled/reference raster
  sampling 경로를 사용. EXIF 금지 및 위치 없음이면 동정은 진행하되 확률만 unavailable.”**
  이 보정은 기존 확률 계산 및 authoritative-location 요구를 약화하지 않는다. 래스터가
  있으면 가능한 지원 경로로 계산을 시도하고, 종별 래스터 부재·유효하지 않은 위치·지원
  경로 실패는 확률의 비가용 사유로만 처리한다.

- ~~**D-PRF-002** (2026-09-01, Category B clarification): 사용자는 조사유형 2·3에서도
  사진 동정이 수행되므로 유형 1과 동일하게 종별 출현확률 래스터를 샘플링해야 한다고
  명확히 했다. Type 2는 `survey` geometry/location을 사용하고, Type 3은 `plot`
  geometry/location을 우선하며 plot이 없거나 유효하지 않을 때 `survey` geometry/location을
  fallback으로 사용한다.~~ **Superseded by D-PRF-003.**

- **D-PRF-003** (2026-09-06, Category A conformance defect): The supplied 85-second iPhone
  recording confirms that Type 3 photo identification opened from a nested `observation` can
  use a non-authoritative location. This corrects behavior already required by FR-FIX-010:
  Type 3 occurrence probability uses only the authoritative `plot.plot_geom` reached through
  the current relation chain, including the current in-memory plot geometry while its plot and
  survey have not yet been saved. A missing or invalid plot geometry makes probability
  unavailable; it does not authorize a `survey` fallback or block identification.

## 3. Functional Requirements

### 3.1 Type 1 동정 및 종별 래스터

- **FR-PRF-001:** 조사유형 1의 `inventory_observation` 폼에서 사용자가
  `사진으로 동정하기`를 클릭하면 기존 Pl@ntNet 동정 요청을 시작하고, 동정 결과가
  반환된 각 후보 종에 대해 기존 KTSN/국명 해석 결과를 사용해 대응하는 확률 래스터를
  찾는다. 래스터 탐색은 다음 프로젝트 기준 경로를 사용한다.

  ```text
  storage/reference/rasters/bce_inverse_corrected_probability_maps/
  ```

  기존에 정의된 종명 기반 파일명 규칙
  `bce_inverse_corrected_probability_{KTSN Korean name}.tif`를 유지하며, 이번 보정은
  파일명 규칙이나 래스터 데이터 자체를 변경하지 않는다.

- **FR-PRF-002:** Type 1의 확률 계산 위치는 현재 편집 중인
  `inventory_observation`의 유효한 geometry에서 얻은 authoritative location이다. 이
  location을 래스터의 CRS로 변환하고, 래스터 extent 안에서 해당 pixel을 샘플링한다.
  Type 1에 존재하지 않는 별도 survey/plot 위치를 임의로 만들거나 사용하지 않는다.

- **FR-PRF-003 (revised; D-PRF-003):** Type 2 uses `survey` geometry/location. Type 3 uses
  only the authoritative `plot` geometry/location reached from the current nested observation;
  it must use the current in-memory plot geometry when the plot and survey are not yet saved.
  A missing or invalid Type 3 plot geometry makes probability unavailable and must not fall back
  to survey geometry. Type 2/3 photo identification and probability results use the same
  species-raster lookup, coordinate transformation, sampling, and non-blocking fallback rules
  as Type 1. EXIF/device GPS and photo metadata are not location sources for any type.

- **FR-PRF-004:** 래스터가 존재하고 authoritative location이 유효하며 샘플링이 성공한
  경우, 해당 후보의 occurrence probability를 기존 0–1 값으로 반환·표시하고, 기존
  백분율 표시 규칙과 후보 선택/저장 규칙을 유지한다.

### 3.2 샘플링 capability와 fallback 경계

- **FR-PRF-005:** 래스터 샘플링은 지원되는 실제 앱/QGIS 경로 또는 프로젝트에 번들된
  reference raster를 읽는 실제 sampling 경로를 사용해야 한다. 구현은 target QField/QGIS
  환경에서 실제로 접근 가능한 경로를 검증하고, 단지 capability가 있다고 가정한 뒤
  성공으로 표시해서는 안 된다.

- **FR-PRF-006:** QField 빌드에서 특정 기기 내 raster sampling capability가 확인되지
  않거나, 선택한 앱/QGIS/reference sampling 경로가 없거나 실패·예외·timeout을 반환하면
  해당 후보의 확률을 unavailable로 처리한다. 이 상태는 사용자에게 한국어로 표시할 수
  있는 비차단 경고/상태이며, Pl@ntNet 동정 요청, 후보 목록 표시, 사용자의 후보 선택,
  기존 write-back 및 정상 저장을 막는 hard-block 또는 성공 전제조건이 아니다.

- **FR-PRF-007:** capability 경고와 후보 종별 래스터 부재는 서로 구분 가능한 진단 상태로
  보존한다. 래스터 파일이 없는 종은 그 후보에 대해서만 확률 unavailable로 표시하고,
  다른 후보의 래스터 샘플링 시도를 막지 않는다. 일부 후보의 확률을 계산하지 못했다는
  이유로 전체 후보 목록을 숨기거나 동정 요청을 취소하지 않는다.

- **FR-PRF-008:** 확률 sampling의 실패 상태를 동정 자체의 `failed` 상태로 잘못 기록하지
  않는다. 실제 Pl@ntNet 요청/응답 또는 기존 동정 검증이 성공하면 동정 후보와 기존
  `identification_status`/write-back 흐름은 기존 규칙에 따르고, probability만 null 또는
  기존 unavailable 표현을 사용한다.

### 3.3 위치·값·저장 규칙

- **FR-PRF-009:** authoritative geometry가 누락·무효이거나 location 변환이 실패하면
  location-dependent probability만 unavailable로 처리하고 동정·후보 표시·후보 선택·
  write-back·저장을 계속한다. 위치 없음은 확률 0으로 대체하지 않는다.

- **FR-PRF-010:** 사진의 EXIF GPS, 기타 image metadata, device GPS, attachment metadata,
  site centroid, provider-invented location은 위치 산출·샘플링·저장에 사용하지 않는다.
  사진 파일은 기존 동정 요청에 필요한 방식으로만 읽고 위치 정보원으로 해석하지 않는다.

- **FR-PRF-011:** 래스터가 NoData를 반환하거나, CRS가 없거나 유효하지 않거나, 변환된
  위치가 extent 밖이거나, 샘플 값이 기존 0–1 계약을 벗어나면 그 후보의 확률을
  unavailable로 처리한다. 이를 0 또는 임의의 대체값으로 저장하지 않는다.

- **FR-PRF-012:** 실제 후보를 선택하면 기존 동정 write-back/save/reopen 계약을 유지한다.
  확률을 계산할 수 있으면 기존 occurrence-probability 필드에 값을 저장하고, 계산할 수
  없으면 그 필드를 null/unavailable 상태로 저장하되 `selected_korean_name` 직접
  write-back과 기존 QGIS lookup에 의한 학명·KTSN 파생, 후보 점수·동정 상태 및 UUID/
  layer/parent/sibling isolation 규칙은 변경하지 않는다.

### 3.4 조사유형 경계 및 회귀

- **FR-PRF-013:** Type 1은 현재 단일 inventory observation geometry를 사용한다. Type 2와
  Type 3은 FR-PRF-003의 survey/plot authoritative location을 사용한다. Type 4
  `community`에는 식물 사진 동정 또는 occurrence-probability sampling 대상을 새로
  만들지 않는다.

- **FR-PRF-014:** 사진 첨부만으로 자동 동정을 시작하지 않는 기존 규칙, 사용자가 명시적으로
  `사진으로 동정하기`를 눌러 시작하는 규칙, Pl@ntNet key 수집·embedding consent,
  privacy·후보 선택·write-back·정상 저장/reopen 규칙은 그대로 유지한다.

- **FR-PRF-015:** 이 보정은 reference raster를 프로젝트에 포함시키는 기존 bundling,
  래스터 파일명·값의 의미·CRS 계약, KTSN/accepted-name lookup 알고리즘 또는 새로운
  외부 probability provider를 추가하거나 변경하지 않는다.

- **FR-PRF-016 (revised; D-PRF-003):** Type 1·2·3에서 Pl@ntNet 동정 후보와 종 식별값이 반환되면 각 후보의
  resolved Korean name을 기존 파일명 매핑에 적용해
  `storage/reference/rasters/bce_inverse_corrected_probability_maps` 아래의 종별 raster를
  찾고, 각각의 authoritative location에서 독립적으로 샘플링한다. Type 1은
  `inventory_observation`, Type 2는 `survey`, Type 3은 `plot`만 사용한다. 래스터가 없는
  후보도 샘플링 대상에서 조용히 탈락시키지 않고 unavailable
  상태로 보존한다.

## 4. Constraints

- **C-PRF-001:** 동정 성공 여부와 occurrence probability 계산 성공 여부는 별개의 상태다.
  probability unavailable은 동정 hard failure가 될 수 없다.
- **C-PRF-002:** 모든 위치 기반 계산은 조사유형별 authoritative location만 사용해야 하며
  EXIF/device/attachment/provider 위치로 fallback할 수 없다.
- **C-PRF-003:** reference raster는 현재 프로젝트의 상대 경로와 기존 배포/번들 규칙을
  따라 접근해야 한다. 절대 경로를 생성 프로젝트나 사용자 데이터에 저장하지 않는다.
- **C-PRF-004:** 기존 probability 값의 범위, NoData, CRS 변환, out-of-extent 처리와
  후보/동정 저장 semantics를 약화하지 않는다.
- **C-PRF-005:** capability 탐지·sampling 실패 처리는 QField 세션을 종료하거나 무한
  재시도하지 않는 bounded, 비차단 경로여야 한다.
- **C-PRF-006:** 사용자에게 표시되는 상태와 오류는 한국어로 제공하되, 기존 machine-readable
  enum/필드명과 내부 진단 코드는 안정성을 위해 유지할 수 있다.

## 5. Assumptions

- **A-PRF-001:** Type 1의 “현재 authoritative location”은 현재 편집 중인
  `inventory_observation` geometry이며, geometry가 유효할 때만 확률 sampling에 사용한다.
- **A-PRF-002:** 종별 raster 파일 매칭은 기존 KTSN accepted Korean name 해석과 현재
  프로젝트에 번들된 raster filename convention을 따른다. 이번 명세는 새로운 fuzzy
  filename matching을 승인하지 않는다.
- **A-PRF-003:** “가능한 실제 앱/QGIS 경로 또는 bundled/reference raster sampling 경로”는
  target QField/QGIS에서 실제 호출·접근 가능한 sampling 경로를 뜻한다. 정확한 QField API
  또는 QGIS API 선택은 이 명세가 고정하지 않으며, implementer가 target 환경에서 검증해
  결과를 보고한다.
- **A-PRF-004:** 여러 Pl@ntNet 후보가 반환되면 확률 availability는 후보별로 독립적으로
  계산·표시하며, 선택된 후보의 값만 기존 persistence 규칙에 따라 저장한다.

## 6. Edge Cases

- **E-PRF-001:** Type 1·2·3 후보 종에 대응하는 `.tif`가 없다. 해당 후보에만 확률
  unavailable을 표시하고 후보 목록, 선택, write-back, 저장은 계속한다.
- **E-PRF-002:** Type 1·2·3의 authoritative geometry가 null, empty, invalid, 변환 불가
  또는 extent 밖이다. 동정은 계속하고 확률만 unavailable로 처리하며 EXIF/device GPS를
  사용하지 않는다.
- **E-PRF-003:** 유효한 Type 1·2·3 authoritative location과 raster가 있지만 QField 빌드가
  sampling capability를 노출하지 않는다. 가능한 다른 실제 앱/QGIS/reference 경로를
  bounded하게 시도하고, 모두 불가능하면 capability warning과 unavailable 상태를 남긴 채
  동정을 계속한다.
- **E-PRF-004:** sampling API가 예외를 던지거나 timeout한다. 세션을 중단하지 않고 해당
  후보의 확률만 unavailable로 처리한다.
- **E-PRF-005:** 한 후보는 유효한 확률을 얻고 다른 후보는 raster missing/NoData다. 후보별
  상태를 보존하며 유효한 후보의 확률을 unavailable 후보 때문에 지우지 않는다.
- **E-PRF-006:** raster가 NoData, invalid CRS, out-of-extent 또는 범위 밖 값을 반환한다.
  확률은 0으로 바꾸지 않고 unavailable로 처리한다.
- **E-PRF-007:** 사용자가 확률 unavailable 상태에서 후보를 선택한다. 기존 selected Korean
  name 직접 write-back, scientific/KTSN lookup-derived 값, candidate metadata, status,
  normal save/reopen 흐름을 그대로 수행하고 probability만 null/unavailable로 남긴다.
- **E-PRF-008 (revised; D-PRF-003):** Type 2/3의 authoritative survey/plot location은 유효하지만 sampling
  capability 또는 종별 raster가 없다. Type 2는 survey 위치, Type 3은 plot 위치에서 후보별
  샘플링을 시도한다. 본 명세의 비차단 규칙을 적용하되 기존 Type
  2/3 relation, location priority, write-back 및 저장 semantics는 바꾸지 않는다.
- **E-PRF-009:** Type 4 community form 또는 community-only record가 동정 요청 대상처럼
  보인다. 새로운 동정/확률 경로를 추가하지 않고 기존 Type 4 경계를 유지한다.

## 7. Out of Scope

- QField core, QGIS core, 운영체제 또는 기기 이미지의 수정/포크/배포.
- 새로운 확률 모델, 새로운 raster provider, 종별 raster 생성·보정·재투영.
- EXIF 또는 device GPS를 보조 위치로 허용하는 것.
- 위치가 없을 때 site centroid, 마지막 GPS, 사진 위치 또는 임의 기본 위치를 사용하는 것.
- Type 4 community에 식물 사진 동정 또는 식물별 확률을 추가하는 것.
- 새로운 candidate UI, 자동 후보 선택, 첨부 즉시 동정, 새로운 write-back 알고리즘.
- 기존 Pl@ntNet key 동의/embedding, KTSN lookup, UUID/FK/relation, schema 또는 CSV/report
  계약 변경.

## 8. Acceptance Criteria

- **AC-PRF-001:** Given a Type 1 observation with a valid authoritative geometry and a
  candidate whose resolved Korean name has a matching bundled raster, when the user clicks
  `사진으로 동정하기` and the candidate result is returned, then the system samples the
  candidate raster at the transformed authoritative location and exposes a valid 0–1
  occurrence probability using the existing display rule.

- **AC-PRF-002:** Given a Type 1 observation with a valid authoritative geometry and a returned
  candidate with no matching raster file, when identification completes, then that candidate is
  shown with Korean unavailable/no-data probability status, while the identification result,
  candidate list, candidate selection, and existing write-back/save path remain available.

- **AC-PRF-003:** Given a Type 1 observation with a valid authoritative geometry and a matching
  raster, when the target QField build does not expose the initially attempted raster sampling
  capability, then an actually available app/QGIS or bundled/reference sampling path is tried
  within a bounded flow; if no supported path succeeds, only probability is unavailable and the
  identification/candidate/write-back flow is not hard-blocked by the capability warning.

- **AC-PRF-004:** Given a Type 1 observation with missing, invalid, or untransformable geometry,
  when the user runs photo identification, then no probability is calculated or stored, the UI
  reports probability unavailable, EXIF/device/photo metadata is not used as a substitute, and
  Pl@ntNet identification, candidate selection, write-back, and normal save/reopen remain
  operable.

- **AC-PRF-005:** Given a Type 1 observation with valid location and raster, when sampling
  returns NoData, invalid CRS, out-of-extent, malformed, non-finite, or out-of-range data, then
  probability is unavailable rather than zero or an invented value, and the identification
  result and candidate flow continue.

- **AC-PRF-006:** Given multiple Type 1 candidates where at least one has a valid raster sample
  and at least one has a missing raster or sampling failure, when candidates are displayed, then
  availability is recorded per candidate; the valid probability remains visible and the
  unavailable candidate does not cancel, hide, or invalidate the whole candidate set.

- **AC-PRF-007:** Given a candidate selected while probability is unavailable, when the existing
  write-back and normal save/reopen flow runs, then selected Korean name is written directly,
  scientific name and KTSN follow the existing Korean-name lookup/default mechanism, existing
  identification status/candidate metadata rules remain intact, probability is null/unavailable,
  and UUID/layer/parent/sibling records are unchanged.

- **AC-PRF-008 (revised; D-PRF-003):** Given Type 2 and Type 3 observations with valid
  authoritative locations, when photo identification and probability enrichment run, then Type 2
  samples each returned candidate's species-specific raster at the `survey` location and Type 3
  samples it at the `plot` location only. The same missing-raster, NoData, out-of-extent, CRS,
  capability, exception, and timeout cases are non-blocking per candidate, and no
  EXIF/device/photo location is used.

- **AC-PRF-009:** Given Type 4 community data, when its form and generated project are inspected,
  then no new plant-photo identification or occurrence-probability sampling target is present,
  and existing Type 4 behavior is unchanged.

- **AC-PRF-010:** Given a generated Type 1/2/3 project and a photo with EXIF GPS, when the
  identification/probability path is exercised, then the sampled location comes only from the
  survey-type authoritative geometry, EXIF/device/attachment location is not read for sampling
  or persisted, and a valid identification can still complete when probability is unavailable.

- **AC-PRF-011:** Given an app/QGIS/reference sampling exception or timeout, when the user runs
  identification, then the QField session remains usable, no unbounded retry occurs, the
  candidate request is not silently discarded, and the user receives a localized non-blocking
  probability-unavailable state.

- **AC-PRF-012 (revised; D-PRF-003):** Given Type 1, Type 2, or Type 3 photo-identification candidates and the
  corresponding authoritative geometry, when identification returns, then the system attempts
  species-specific raster sampling for every returned candidate using the type-specific location
  rule: `inventory_observation` for Type 1, `survey` for Type 2, and `plot` only for Type 3. A
  missing raster makes only that candidate unavailable; it does not remove
  the candidate or prevent candidate selection, write-back, save, or reopen.

- **AC-PRF-013:** Given a Type 3 `site → plot → survey → observation` add/edit flow in which the
  current plot and survey have not yet been saved but the current plot has valid `plot_geom`, when
  photo identification is opened from the nested observation and a candidate is returned, then
  occurrence probability is sampled from that current plot geometry. Given that plot geometry is
  missing or invalid, then probability is unavailable without a survey-geometry fallback, while
  identification, candidate selection, and the existing save flow remain available.

## 9. Traceability

| Requirement | Acceptance criteria |
|---|---|
| FR-PRF-001–004 | AC-PRF-001, AC-PRF-002, AC-PRF-006, AC-PRF-008 |
| FR-PRF-005–008 | AC-PRF-003, AC-PRF-005, AC-PRF-008, AC-PRF-011 |
| FR-PRF-009–012 | AC-PRF-004, AC-PRF-005, AC-PRF-007, AC-PRF-010 |
| FR-PRF-013–016 | AC-PRF-008, AC-PRF-009, AC-PRF-012, AC-PRF-013 |
| C-PRF-001–006 | AC-PRF-003–005, AC-PRF-007, AC-PRF-010, AC-PRF-011 |

## 10. Open Questions

없음. 정확한 sampling API 또는 구현 경로는 명세의 observable contract를 충족하는 범위에서
implementer가 target QField/QGIS 환경을 검증해 선택할 수 있다.
