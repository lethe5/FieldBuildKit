# Feature: 확률 래스터 대량 등록 제거 및 생성 타임아웃 수정

> Status: DRAFT — awaiting user review and approval  
> Owner: spec-writer  
> Last updated: 2026-09-06
> Extends: `specs/fieldbuild-kit-identification-probability-raster-fallback.md`,
> `specs/qfield-project-builder.md`

## 1. Summary

출현확률 래스터는 생성 프로젝트의 `reference/` 폴더에 계속 포함하되, 2,532개에 달하는
종별 TIFF를 QGIS 프로젝트의 래스터 레이어로 하나씩 등록하지 않는다. 현재 생성 경로는
약 64MB의 TIFF 전체를 숨은 QGIS 레이어로 등록하면서 QGIS 작업 프로세스가 제한 시간 안에
응답하지 않는 문제가 있으므로, 프로젝트 생성에서는 파일 복사와 결정적 파일 목록만
수행하고, QField 실행 중에는 기존 WorkerScript의 로컬 TIFF 직접 읽기·LZW 디코딩·샘플링을
권위 있는 경로로 사용한다.

이 명세는 기존 확률 래스터 명세의 파일 보존 및 런타임 샘플링 요구를 유지한다. 사용자의
명시적 결정에 따라 **확률 TIFF를 종별 QGIS 래스터 레이어 및 레이어 트리 노드로 등록해야
한다는 기존 요구만 superseded**한다.

## 2. Change classification and Decision Log

### 2.1 Classification

**Category C — stakeholder-approved product change, with a Category A performance/conformance
defect.** 사용자는 생성 실패의 원인을 확인하고 다음을 명시했다: 기존 QGIS 레이어 등록
요구는 폐기하되, TIFF 파일은 생성 프로젝트에 남기고 WorkerScript 직접 샘플링을 사용해야
한다. 현재 구현의 수천 개 레이어 등록은 실제 생성 타임아웃을 유발하는 conformance/performance
defect이며, 이번 명세는 그 변경을 검증 가능한 계약으로 정리한다.

### 2.2 Decision Log

- **D-PRG-001** (2026-09-01, Category C/A): 사용자의 명시적 지시인 **“생성 must
  complete without registering thousands of probability TIFFs as QGIS project map layers;
  keep all reference TIFF files bundled/copied into generated project; WorkerScript/direct
  local-file sampler remains authoritative”**를 반영한다.

- **D-PRG-002** (2026-09-01, supersedes only prior layer-registration condition):
  `fieldbuild-kit-identification-probability-raster-fallback.md` 및 관련 구현에서
  종별 확률 TIFF를 `QgsRasterLayer`, QGIS 프로젝트 map-layer registry, 또는 layer-tree
  node로 미리 등록해야 한다는 조건은 폐기한다. `reference/` 안의 byte-for-byte 파일 보존,
  상대 경로, 결정적 이름 매핑, WorkerScript 샘플링, LZW/CRS/후보별 fallback 규칙은
  폐기하지 않는다.

- **D-PRG-003** (2026-09-01, performance bound): 기준 reference fixture는
  `storage/reference/rasters/bce_inverse_corrected_probability_maps/`의 TIFF 2,532개
  (약 64MB)이다. QGIS bridge의 현재 기본 작업 제한 시간인 180초를 생성 성능의 상한
  검증값으로 사용한다. 이 기준 fixture로 QGIS 프로젝트 생성 호출은
  `worker_timeout` 없이 180초 이내에 반환되어야 한다.

## 3. Functional Requirements

### 3.1 Build-time file persistence without QGIS raster registration

- **FR-PRG-001:** 식별 기능이 활성화된 생성에서 원본 reference raster directory의 모든
  유효한 `.tif` 파일을 생성 프로젝트의
  `reference/rasters/bce_inverse_corrected_probability_maps/` 아래에 복사한다. 원본과
  생성 파일의 내용은 byte-for-byte 동일해야 하며, 파일명·대소문자·Unicode 이름을
  변경하거나 종별 파일을 임의로 생략하지 않는다.

- **FR-PRG-002:** 확률 TIFF는 생성 중 `QgsRasterLayer`로 열거나 QGIS project map-layer
  registry에 등록하지 않는다. 확률 TIFF를 위한 QGIS `QgsLayerTreeLayer` 또는 종별
  layer-tree node도 생성하지 않는다. 일반 survey/site/plot/observation/community,
  basemap, KTSN lookup 등 기존 비확률 레이어의 생성·순서는 변경하지 않는다.

- **FR-PRG-003:** 생성 프로젝트의 manifest 또는 동등한 검증 가능한 파일 목록에는 각
  번들 TIFF의 프로젝트 상대 경로가 결정적으로 기록되어야 한다. 목록은 정렬된 파일명
  기준으로 생성하며, absolute path, 원본 컴퓨터 경로, 비밀값, 사진 첨부 경로를 포함하지
  않는다. 기존 manifest의 `required_files.reference` 목록을 재사용해도 된다.

- **FR-PRG-004:** 선택적으로 lightweight probability index를 함께 생성할 수 있다. 생성할
  경우 index에는 종 식별에 필요한 안정적인 파일명/상대 경로와 선택적인 크기·digest만
  기록하고, TIFF를 QGIS 레이어로 해석하게 만드는 layer ID나 datasource 등록 정보를
  기록하지 않는다. index는 WorkerScript가 사용해도 되고 사용하지 않아도 되지만,
  filename mapping의 권위는 기존 resolved Korean name 및 파일명 규칙에 있다.

- **FR-PRG-005:** 생성 프로젝트를 저장하고 다시 열었을 때도 모든 번들 TIFF가 동일한
  프로젝트 상대 경로에 존재하며, QML `@project_folder` 기반 직접 파일 읽기 경로로
  접근할 수 있어야 한다. QGIS 프로젝트 재오픈을 위해 TIFF를 map layer로 등록하는
  우회는 허용하지 않는다.

### 3.2 Authoritative runtime sampling path

- **FR-PRG-006:** QField 런타임의 출현확률 계산은 프로젝트 폴더의 상대 TIFF 파일을
  읽어 별도 WorkerScript에서 수행하는 direct local-file sampler를 권위 있는 경로로
  사용한다. TIFF 바이트 전달, TIFF metadata 해석, TIFF LZW MSB-first 디코딩, pixel
  선택은 기존 확률 래스터 명세의 계약을 유지한다.

- **FR-PRG-007:** 런타임 샘플러는 확률 계산을 위해 QGIS에 종별 래스터 레이어가 등록되어
  있다고 가정하거나 `raster_value()` 등 동기 QGIS expression fallback에 의존하지
  않는다. 프로젝트 map-layer registry에 종별 확률 레이어가 없어도 직접 파일 샘플링이
  동작해야 한다.

- **FR-PRG-008 (revised; D-PRF-003):** 기존 조사유형별 authoritative location을 그대로
  유지한다. 유형 1은 `inventory_observation`, 유형 2는 `survey`, 유형 3은 현재 nested
  observation에서 도달한 `plot`만 사용하며, plot과 survey가 아직 저장되지 않았으면 현재
  in-memory plot geometry를 사용한다. plot geometry가 없거나 무효이면 probability는
  unavailable이고 survey fallback은 사용하지 않는다. 프로젝트 CRS에서 래스터 CRS로
  변환하는 규칙도 유지한다.

- **FR-PRG-009:** 종별 파일명 매핑은 기존 resolved Korean name과
  `bce_inverse_corrected_probability_{Korean name}.tif` 규칙을 따른다. 파일이 존재하지
  않거나 직접 읽을 수 없는 후보는 해당 후보만 probability unavailable로 표시하며,
  다른 후보의 샘플링·동정·후보 선택을 중단하지 않는다.

- **FR-PRG-010:** NoData, 잘못된 TIFF metadata/CRS, 범위 밖 좌표, invalid/non-finite
  sample, LZW decoding failure는 0 또는 임의의 값으로 대체하지 않고 해당 후보만
  unavailable로 처리한다. sampling timeout/watchdog은 기존 bounded 비차단 계약을
  유지하며 동정 전체를 실패시키지 않는다.

### 3.3 Existing identification and data contracts

- **FR-PRG-011:** 유형 1·2·3에서 사용자가 `사진으로 동정하기`를 클릭하면 기존
  Pl@ntNet 동정·후보 표시·후보 선택 흐름을 유지하고, 확률 계산 성공 여부를 동정
  자체의 성공/실패와 분리한다. 유형 4는 기존대로 식물 사진 동정 및 확률 계산 대상에서
  제외한다.

- **FR-PRG-012:** EXIF GPS, 사진 metadata, device GPS, provider-invented location,
  site centroid 또는 임의 기본 위치를 확률 위치로 사용하지 않는다. authoritative
  geometry가 없거나 유효하지 않으면 동정은 계속하고 확률만 unavailable로 처리한다.

- **FR-PRG-013:** 확률이 계산되면 기존 0–1 값과 백분율 표시를 사용하고, 계산되지 않으면
  후보별 unavailable 상태를 보존한다. 선택된 후보의 occurrence-probability 저장,
  `selected_korean_name` 직접 write-back, QGIS lookup으로 파생되는 학명·KTSN, 동정
  상태, UUID/FK/relation, save/reopen semantics는 변경하지 않는다.

- **FR-PRG-014:** 기존 HTML report의 지도·표·CSV·한글 UI·오프라인 렌더링 동작과 조사
  유형별 공간 조인 규칙은 유지한다. 확률 TIFF를 QGIS 레이어로 등록하지 않는다는
  build-time 변경이 report payload, identity columns, spatial anchor, CSV escaping에
  영향을 주어서는 안 된다.

## 4. Constraints

- **C-PRG-001:** 기준 2,532개 TIFF를 종별 QGIS 레이어로 등록하는 구현은 금지한다.
  확률 TIFF map-layer registry 수와 probability layer-tree node 수는 0이어야 한다.
- **C-PRG-002:** 생성 프로젝트에는 TIFF 파일 전체가 포함되어야 하며, 큰 파일 세트를
  “생성 속도 개선”을 이유로 일부만 복사하거나 압축된 단일 파일로 대체할 수 없다.
- **C-PRG-003:** 모든 reference 경로는 project-relative여야 하며 생성 `.qgs`, manifest,
  QML, report, 로그에 원본 절대 경로·API key·PlantNet key·사진 절대 경로를 노출하지
  않는다.
- **C-PRG-004:** QGIS 프로젝트 생성 호출은 기준 fixture에서 bridge 기본 제한 시간
  180초 안에 반환해야 하며 `worker_timeout` 오류를 정상적인 결과로 간주하지 않는다.
- **C-PRG-005:** WorkerScript 직접 샘플러의 LZW, CRS, 위치 우선순위, timeout/watchdog,
  candidate-only unavailable semantics를 레이어 등록 제거 때문에 약화할 수 없다.
- **C-PRG-006:** 기존 생성 프로젝트의 호환성을 위해 이번 변경 이후 생성되는 새 프로젝트는
  반드시 새 계약을 따르며, 이미 생성된 프로젝트에 종별 QGIS 레이어를 자동 제거하거나
  기존 파일을 삭제하는 migration은 수행하지 않는다.

## 5. Assumptions

- **A-PRG-001:** `storage/reference/rasters/bce_inverse_corrected_probability_maps/`는
  기준 배포 자료이며, 현재 fixture에는 TIFF 2,532개와 약 64MB의 데이터가 있다.
- **A-PRG-002:** 기존 reference bundle validator가 유효한 TIFF 집합을 확정하고, build
  단계의 copy/manifest 흐름이 그 집합을 결정적으로 제공할 수 있다.
- **A-PRG-003:** QField에서 `@project_folder`와 `FileUtils`를 통해 프로젝트 내부의
  상대 TIFF를 읽을 수 있으며, WorkerScript가 직접 디코딩·샘플링하는 기존 경로를
  유지한다.
- **A-PRG-004:** 현재 QGIS bridge의 기본 호출 제한은 180초이며, 이 값은 무작위 장비
  성능 목표가 아니라 기준 fixture의 생성 타임아웃 회귀를 측정하는 acceptance bound다.
- **A-PRG-005:** reference 파일의 누락은 build-time reference validation에서 발견될 수
  있지만, 후보 종에 대응하는 TIFF가 없는 경우는 정상적인 후보별 unavailable 상태다.

## 6. Edge Cases

- **E-PRG-001:** TIFF 파일 하나가 누락되거나 복사에 실패한다. 전체 reference bundle의
  무결성 검증은 실패해야 하며, 부분 bundle을 성공으로 보고하지 않는다.
- **E-PRG-002:** 종 후보에 대응하는 TIFF만 없다. 해당 후보만 unavailable로 남기고 다른
  후보·동정·write-back·저장은 계속한다.
- **E-PRG-003:** 생성 프로젝트를 다른 컴퓨터 또는 QField 기기로 복사해 `.qgs`를
  재오픈한다. 절대 경로 없이 project-relative TIFF가 직접 열려야 하며, QGIS 레이어
  registry에 종별 확률 레이어가 없어도 샘플러는 같은 파일을 찾아야 한다.
- **E-PRG-004:** 파일명에 한글 또는 Unicode normalization 차이가 있다. 기존 NFC 및
  resolved Korean name 매핑 규칙을 사용해 deterministic path를 계산하며, 원본 파일을
  조용히 다른 종 파일로 대체하지 않는다.
- **E-PRG-005:** QGIS project tree visibility 재설정이 발생한다. 확률 TIFF layer node가
  애초에 없으므로 visibility pass가 직접 샘플링 경로를 변경하거나 복구할 수 없다.
- **E-PRG-006:** QGIS worker가 180초에 근접한다. per-TIFF layer creation 없이 생성이
  진행되어야 하며, timeout을 확률 계산 단계로 미루거나 무시해 성공 처리해서는 안 된다.
- **E-PRG-007:** 유효한 위치가 없거나 래스터가 NoData/extent 밖이다. 확률만 unavailable로
  남기고 후보 선택, 국명 write-back, 학명·KTSN lookup, save/reopen을 계속한다.
- **E-PRG-008 (revised; D-PRF-003):** 유형 3의 plot geometry가 없거나 무효다. probability를
  unavailable로 처리하고 survey, EXIF/device GPS, site centroid로 대체하지 않는다.

## 7. Out of Scope

- 새로운 확률 모델·래스터 데이터·provider·재투영 생성.
- QGIS/QField core 수정, QGIS layer registry에 다른 비확률 레이어를 등록하는 방식 변경.
- 기존 생성 프로젝트에서 이미 등록된 확률 레이어를 삭제하는 migration.
- TIFF를 하나의 QGIS virtual raster 또는 다른 대체 포맷으로 변환하는 것.
- 새로운 동정 UI, 후보 선택 방식, write-back 알고리즘, Type 4 동정.
- EXIF/device GPS 허용, 외부 위치 provider 추가, API key/사진 경로 노출 허용.

## 8. Acceptance Criteria

- **AC-PRG-001:** Given the reference fixture containing exactly 2,532 TIFF files, when a
  Type 1/2/3 identification-enabled project is generated, then every source TIFF is copied
  byte-for-byte under the project's `reference/rasters/bce_inverse_corrected_probability_maps/`
  directory and the generated manifest contains a deterministic project-relative entry for
  each file.

- **AC-PRG-002:** Given the same generation, when the saved `.qgs` is inspected, then the
  number of probability-raster `QgsMapLayer` entries is exactly 0 and the number of
  probability-raster layer-tree nodes is exactly 0; no per-species `QgsRasterLayer` registration
  or equivalent hidden lookup layer exists.

- **AC-PRG-003:** Given the reference fixture, when the QGIS project-generation worker is
  invoked through the normal bridge, then it returns a successful result within the existing
  180-second default job timeout and does not return `worker_timeout`.

- **AC-PRG-004:** Given a generated project reopened from its own folder, when the project
  manifest and project-relative paths are checked, then all 2,532 TIFFs remain available without
  absolute source paths, and the project can be reopened without adding probability TIFFs to
  the QGIS layer tree.

- **AC-PRG-005:** Given a Type 1 candidate with a matching bundled TIFF, when the user starts
  identification and the WorkerScript samples the candidate at a valid authoritative location,
  then the result is read from the project-local TIFF direct sampler, returns the expected 0–1
  value, and does not require a QGIS probability raster layer.

- **AC-PRG-006 (revised; D-PRF-003):** Given Type 2 and Type 3 candidates with matching bundled
  TIFFs, when probability sampling runs, then Type 2 uses survey location and Type 3 uses only
  the current plot location, including the existing project-CRS-to-raster-CRS transform. An
  unsaved Type 3 plot/survey flow uses the current in-memory plot geometry; missing/invalid plot
  geometry makes probability unavailable without a survey fallback.

- **AC-PRG-007:** Given candidates where one TIFF is missing, unreadable, NoData, out of extent,
  invalid, or has an invalid CRS, when identification completes, then only that candidate is
  marked probability unavailable; the other candidates, candidate selection, identification,
  write-back, and save/reopen remain available.

- **AC-PRG-008:** Given a valid bundled TIFF encoded with the supported little-endian float32
  LZW format, when the WorkerScript samples it, then the MSB-first LZW decoder and pixel result
  match the independent reference value, including strip dictionary reset behavior.

- **AC-PRG-009:** Given a sampler exception or watchdog timeout, when identification is in
  progress, then the candidate receives a bounded unavailable result, the user-facing
  identification flow does not hang or become failed solely because of probability sampling,
  and no synchronous QGIS `raster_value()` expression call is required.

- **AC-PRG-010:** Given Type 1, Type 2, and Type 3 records with missing/invalid authoritative
  geometry, when the user starts identification, then identification continues, probability is
  unavailable rather than zero, and EXIF GPS/device GPS/photo metadata is not consulted.

- **AC-PRG-011:** Given a Type 4 community record, when the project is generated and reopened,
  then no plant-photo identification or probability-raster sampling path is added, while the
  existing Type 4 vegetation/community behavior remains unchanged.

- **AC-PRG-012:** Given a generated report from a Type 1/2/3 project, when map/table/CSV
  behavior is exercised, then existing spatial anchors, site/survey/plot/observation joins,
  국명·학명·KTSN columns, filtering, sorting, escaping, offline rendering, and no-secret/no-
  photo-path guarantees are unchanged by removal of QGIS probability layers.

## 9. Traceability

| Requirement | Acceptance criteria |
|---|---|
| FR-PRG-001, FR-PRG-003, FR-PRG-005 | AC-PRG-001, AC-PRG-004 |
| FR-PRG-002 | AC-PRG-002, AC-PRG-003, AC-PRG-004 |
| FR-PRG-004 | AC-PRG-001, AC-PRG-002 |
| FR-PRG-006, FR-PRG-007 | AC-PRG-005, AC-PRG-008, AC-PRG-009 |
| FR-PRG-008 | AC-PRG-006, AC-PRG-010 |
| FR-PRG-009, FR-PRG-010 | AC-PRG-007, AC-PRG-008, AC-PRG-009 |
| FR-PRG-011, FR-PRG-013 | AC-PRG-007, AC-PRG-009, AC-PRG-011 |
| FR-PRG-012 | AC-PRG-010 |
| FR-PRG-014 | AC-PRG-012 |
| C-PRG-001, C-PRG-004 | AC-PRG-002, AC-PRG-003 |
| C-PRG-002, C-PRG-003, C-PRG-006 | AC-PRG-001, AC-PRG-004, AC-PRG-012 |
| C-PRG-005 | AC-PRG-005 through AC-PRG-011 |

## 10. Open Questions

없음. lightweight index는 선택 사항이며, 구현하지 않더라도 기존 manifest의 정렬된
`required_files.reference` 목록이 결정적 파일 목록 계약을 충족한다.
