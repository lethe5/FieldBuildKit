# Feature: 도로망 조사 경로 및 조사대상 도형 확장

> Status: APPROVED SPECIFICATION — Category B 정합, hosted endpoint migration 및 route-key 전달 결정 (2026-09-15 사용자 승인)
> Approved baseline: prior specification checkpoint `e382c77`; current specification slice approved 2026-09-15; acceptance checkpoint `ed8ac81` 정합 대기
> Owner: spec-writer
> Extends: [통합 명세](qfield-project-builder.md)
> Test design: [승인된 기준본](../tests/acceptance/survey_route_planner.test-design.md) — 승인된 현재 명세에 맞춘 ETA/backend/key 정합 필요
> Traceability: [승인된 기준본](../tests/acceptance/survey_route_planner.traceability.md) — 현재 명세의 통과 증거 아님


## 0. 문서 권한과 현재 상태 (2026-09-14)

**Category C 기준본:** 사용자의 경로 기능 및 도형 확장 지시를 기록한 명세는
2026-09-14 `e382c77`에서 승인되었고 acceptance 산출물은 `ed8ac81`에서 별도로 승인되었다.
그 승인 범위와 기존 FR/AC/Decision ID는 계속 유효하며 현재 승인 정합이 취소하지 않는다.

**Category B 승인 정합:** 구현·검증 중 드러난 ETA wire 형식, 등록 backend 경계,
대표점 규칙, 완료 판정, Type 1 매핑, 이격거리 기본값, 이동 가능한 설정과 저장 형식,
현재 hosted routing/optimizer endpoint의 의미가 기준본만으로는 일관되게 구현·검증되지 않았다.
D-SRP-008~013, D-SRP-015~019와 그에 따른 FR/AC 문구 및 O-SRP-007 해소 방식은
2026-09-15 사용자가 “평문 포함 방식으로 명세 승인”하여 현재 명세 기준이 되었다.
새 test-designer가 acceptance 산출물과 traceability를 별도 정합하고 승인받아야 한다.
[현재 문서 지도](../docs/README.md), [런타임](../docs/standalone.md),
[호환성](../docs/independence.md), [검증 기록](../docs/qfield-runtime-verification.md)을 함께 읽는다.
제품은 FieldBuild Kit, 저장소는 FieldBuildKit, 내부 패키지는 qfield_builder, 현재 버전은 0.2.9이다.

**2026-09-15 추가 분류:** 생성된 유효한 site 레이어가 새 경로 계산에서 CRS/WGS84 안내 오류로
거부되는 현상은 FR-SRP-017에 대한 Category A conformance defect다. 프로젝트 생성 시 route API key
입력 추가는 Category C다. builder의 로컬 암호화 저장소는 QField로 복사되지 않으므로, 사용자가
명시적 위험 고지에 동의하면 생성 프로젝트에 key를 평문으로 포함해 QField가 자동 사용한다.
프로젝트 폴더 접근자는 누구나 key를 읽고 사용할 수 있으며 암호화를 주장하지 않는다. 동의하지 않으면
key를 비운 채 생성하고 QField에서 세션마다 수동 입력한다. 완료 필드·scope 사용 안내는 Category B/D
정합이고, 경로 패널 입력 너비는 Category D다. D-SRP-016~019와 관련 FR/AC 문구는 2026-09-15 승인됐다.

**사용자 확정 범위:** 선택/전체/미조사 대상의 도로망 최적화, Project Plugin 하단 패널,
명시 계산에만 API 호출, 오프라인 영구 경로 조회, 여러 경로, 완료/남은 지점 재계산,
WGS84 네이버지도 내비게이션, 교체 가능한 외부 backend, 오류 시 기존 경로 보존.
초기 직접 입력에서 점·선·면 선택, SHP/ZIP/GPKG의 6가지 단일/다중 도형 자동 인식,
선·면 TSP에는 centroid 사용. 원본 조사 도형과 관계/UUID는 보존한다.

**기술 상태:** D-SRP-004의 ORS matrix/VROOM/directions 조합과 D-SRP-005의
QField FileUtils/이중 JSON 저장은 여전히 기술 후보다. 현재 자동화는 JSON 후보의 fault/restart/move
동작을 검사했지만 실제 QField 파일 API·원자성·복구를 입증하지 않는다. 저장 형식과 무관하게
FR-SRP-008의 보존·오프라인·폴더 이동 의미를 충족해야 한다. Valhalla, 일부 unassigned 전체 실패,
같은 계열 Multi 승격·혼합 계열 거부, Z/M 및 GeometryCollection 정규화와 과거 호출
MULTIPOLYGON 기본값의 기존 범위도 유지한다. 공식 2026-04-28 공지는
`api.openrouteservice.org`를 폐기 예정 주소로 지정하고 HeiGIT service/version 경로로의 이동을
요구했다. 2026-08-27 후속 공지는 즉시 shut-off 대신 기존 주소의 quota를 줄이고 종료일을
2026-09-28로 변경했다. 현재 도달 가능 여부와 관계없이 폐기 주소는 새 프로젝트의 기본값이 아니다.

**현재 구현 증거:** working tree에는 implementation attempt 2가 uncommitted 상태로 있다.
정합 전 자동 결과는 104 passed, 2 contract-failing, 12 skipped이며 실패는 AC-SRP-007의
ISO ETA fixture와 AC-SRP-013의 미등록 `acceptance_backend` token이다. 이 작업물은 요구사항의
근거가 아니고 최종 PASS도 아니다. QField/iOS/Android, 실제 provider 호출, 네이버지도 실행은
수행되지 않았다. 보고서의 포인트 행만 위·경도를 제공하는 계약은 유지하며
TSP centroid를 보고서 좌표로 전용하지 않는다. site 확장이 observation/plot/community의
원래 도형 의미를 바꾸지 않는다. Type 1에는 site가 없으므로 대상 레이어/ID 매핑이 필요하다.

## 1. Summary
QField 프로젝트 플러그인에서 선택한 조사대상을 도로망 기준으로 방문 순서 최적화하고,
결과를 영구 저장·재사용하며 조사 완료 및 네이버지도 내비게이션을 제공한다.
앱에서 조사지를 직접 그릴 때 점/선/면을 선택하고 업로드는 단일/다중 도형을 자동 인식한다.

## 2. Decision Log
- D-SRP-001 (2026-09-14, Category C): 첨부 요구사항에 따라 QField Project Plugin으로
  구현한다. Python QGIS plugin 또는 QField 본체 수정은 하지 않는다.
- D-SRP-002 (Category C): 사용자 추가 지시로 기존 site MULTIPOLYGON 전용 입력 규칙을
  확장한다. FR-QPB-025~028 및 site geometry 데이터 계약 중 폴리곤 전용 부분은
  이 문서 FR-SRP-014~017이 우선한다. 기존 폴리곤 허용/검증 및 관계/UUID 의미는 유지한다.
  최초 구현 메모의 “Point만 허용, 폴리곤 centroid 금지”는 폐기한다.
- D-SRP-003 (Category C): 선과 면은 원본 CRS에서 centroid를 계산한 후 EPSG:4326으로
  변환한다. MultiPoint도 피처당 하나의 centroid로 대표하며 원본 도형은 그대로 보존한다.
  Point는 그대로 변환한다. centroid가 도로와 멀면 자동으로 다른 대표점을 고르지 않는다.
- D-SRP-004 (기술 후보 — 명세 승인, 실현 가능성 검증 전): 초기 backend는 ORS matrix + VROOM + ORS directions.
  거리/시간 행렬을 사용하며 backend 계약은 교체 가능하게 분리한다. Valhalla 자체 구현은
  이번 범위가 아니다. API 서버 운영 및 API key 구매/발급은 구현 범위 밖이다.
- D-SRP-005 (기술 후보 — 명세 승인, 실현 가능성 검증 전): QField 4.2.4의 프로젝트 내 FileUtils로 이중 JSON 사본에
  route/route_stop/LineString을 저장한다. “GeoPackage 등” 영구 저장의 후보이며 실제 충족 여부는 검증 전이다.
  기존 조사 GPKG와 분리한다. QML 임의 SQLite transaction API를 추정하지 않는다.
- D-SRP-006 (2026-09-14에 폐기): 앱 버전을 0.2.8로 유지하던 지침.
- D-SRP-014 (2026-09-14, Category C): 사용자가 앱 버전을 0.2.9로 변경하고
  AGENTS.md의 0.2.8 고정 문구를 삭제하도록 명시했다.
- D-SRP-007: 작업 저장소는 사용자 지시로 fieldbuild_standalone. 이전 qfield_builder의
  삭제된 파일 상태는 건드리지 않는다.
- D-SRP-008 (2026-09-14 제안, 2026-09-15 승인, Category B): 승인된 범위를 바꾸지 않고 구현 중
  확인된 contract 공백만 정합한다. 기존 `e382c77`/`ed8ac81` 승인 이력은 유지하며, 이 명세 slice의
  승인이 기존 acceptance 파일 변경까지 승인하지는 않는다.
- D-SRP-009 (2026-09-15 승인, Category B): 초기 등록 provider ID는 `ors-vroom`이다. VROOM 1.14의
  `steps[].arrival`은 숫자 초 단위이며 초기 provider에는 절대시각 epoch 계약이 없으므로,
  저장·노출하는 `eta[]`도 경로 시작 기준의 숫자 초이고 `eta_basis`는
  `relative_seconds`다. 둘은 함께 제공하거나 함께 생략한다. ISO 시각을 만들거나 현재 시각을
  epoch로 추정하지 않는다. 미래 절대 ETA는 provider 계약이 명시적인 route epoch와
  절대시각을 제공하는 별도 승인 변경으로 다룬다.
- D-SRP-010 (2026-09-15 승인, Category B): 교체 가능 backend는 등록된 provider interface와
  transport boundary를 뜻한다. 선택한 등록 provider가 routing base/optimizer endpoint/profile/
  timeout/key/offset 설정을
  전달받는다. 미등록 ID는 request 전 거부하고 기존 저장 경로를 보존한다. acceptance는
  production에 가짜 provider token을 추가하지 않고 등록된 `ors-vroom`과 외부 transport seam으로
  설정 전달을 검사한다. key는 로그·오류·보고서·URL·query·요청 body에 노출하지 않으며,
  D-SRP-017에 동의한 generated project variable만 저장 예외다.
- D-SRP-011 (Category B, 기존 승인 규칙의 명료화): D-SRP-003을 도형 6유형에 일관되게
  적용한다. Point는 원래 점을, MultiPoint/LineString/MultiLineString/Polygon/MultiPolygon은
  피처마다 원본 CRS에서 계산한 centroid 하나를 대표점으로 삼고 그 뒤 WGS84로 변환한다.
  원본 도형은 수정하지 않는다. source CRS가 없거나 유효하지 않거나 대표점/변환을 만들 수 없으면
  계산 후보를 거부하고 기존 저장 경로를 보존한다. 이는 새 도형 규칙이 아니라 사용자 지시와
  승인된 D-SRP-003의 일관된 해석이다.
- D-SRP-012 (2026-09-15 승인, Category B): 완료는 선택한 완료 필드 값이 명시적 Boolean `true`일 때만
  완료다. `false`/`NULL`/missing은 미완료이고 완료 필드를 매핑하지 않은 경우에만
  `route_stop.completed`를 쓴다. site가 있는 유형은 `site/site_id/site_name`을 기본 매핑으로 쓴다.
  site가 없는 Type 1은 계산 전에 layer/id/name을 명시해야 하고 완료 필드는 선택 사항이다.
  최대 도로 이격 기본값은 1000 m이고 변경 가능하며 초과 후보는 저장하지 않는다.
- D-SRP-013 (2026-09-15 승인, Category B/C): routing-base/optimizer-endpoint/backend/profile/timeout/
  max-road-offset/default-start와
  layer/id/name/optional-completion 매핑은 non-secret 프로젝트 설정으로 폴더 안에 저장되어 폴더와
  함께 이동한다. API key 자동 전달에 동의한 경우에는 D-SRP-017의 고지·동의를 거쳐 generated project
  variable에 key를 평문으로 포함한다. 동의하지 않으면 프로젝트에 key를 넣지 않고 QField 세션에서
  수동 입력할 수 있다. 어느 경우에도 key 없이 저장 경로를 오프라인으로 열 수 있다. 이중 JSON은 현재 구현 후보일 뿐이며 저장 형식이 바뀌어도
  atomic publication, last-good 보존, revision 충돌 거부, 다중 경로·오프라인·폴더 이동 의미는 같다.
- D-SRP-015 (2026-09-15 승인, Category B): 초기 `ors-vroom`의 현재 hosted 기본값은
  routing base `https://api.heigit.org/openrouteservice`와 optimizer endpoint
  `https://api.heigit.org/vroom/v0`이다. routing base에는 provider가
  `/v2/matrix/{profile}`과 `/v2/directions/{profile}/geojson`을 붙이며 optimizer URL은 완전한
  POST endpoint로 그대로 사용하고 `/post`를 덧붙이지 않는다. 사용자 입력 끝의 `/`는 경로 구분자 하나로 정규화하지만
  `/openrouteservice`나 `/v2`를 다시 덧붙이지 않는다. `api.openrouteservice.org`는 2026-04-28
  공식 폐기 공지의 이전 주소이고 새 프로젝트 기본값 또는 자동 fallback으로 사용하지 않는다.
  사용자가 입력한 별도 routing base와 optimizer endpoint는 `http` 또는 `https`의 custom/self-hosted
  계약으로 그대로 유지하며 HeiGIT 주소로 바꾸지 않는다. 프로젝트 평문 variable 또는 QField 세션에
  수동 입력한 API key는 값이 있으면 선택된 두 endpoint의 HTTP `Authorization` header에만 전달한다. hosted HeiGIT
  기본값으로 계산할 때는 비어 있는 key를 request 전에 거부한다. custom/self-hosted endpoint는
  key 없는 배포를 허용하고 빈 `Authorization` header를 만들지 않는다.
  기존 프로젝트를 열 때 routing base가 trailing slash를 제외하고 정확히
  `https://api.openrouteservice.org`이면 새 hosted routing base로, optimizer endpoint가
  missing/empty 또는 정확히 `https://api.openrouteservice.org/optimization`이면 새 hosted optimizer로
  요청 전에 migration한다. 두 값은 각각 독립적으로 판정한다. 그 밖의 non-empty 사용자 입력 주소는
  host/path가 비슷해도 custom으로 간주하여 수정하지 않는다. migration은 API를 호출하거나 key를
  생성·저장하지 않으며 다음 정상 설정 저장에 반영한다.
- D-SRP-016 (2026-09-15, Category A 기록): FieldBuild Kit가 생성한 유효한 대상
  레이어와 도형은 선언된 source CRS에서 FR-SRP-017의 대표점을 계산하고 WGS84로 변환할 수 있어야
  한다. 새 경로 계산에서 이 입력을 일반적인 “조사대상 원본 CRS와 WGS84 좌표 변환을 확인하세요”로
  거부하는 것은 기존 계약의 실패다. 실제 source CRS missing/invalid, 도형 invalid 또는 변환 실패는
  계속 명확히 거부하고 기존 저장 경로를 보존한다.
- D-SRP-017 (2026-09-15 승인, Category C): FieldBuild Kit 프로젝트 생성 흐름에 masked ORS/HeiGIT
  route API key 입력을 추가한다. key를 입력하면 생성 전에 “생성 프로젝트에 평문으로 포함되며,
  프로젝트 폴더에 접근할 수 있는 사람은 누구나 key를 읽고 사용할 수 있다”는 경고와 자동 전달 동의를
  명시적으로 받는다. 동의하면 generated project variable에 평문으로 포함해 QField가 자동 사용한다.
  이는 암호화 저장이 아니다. 동의를 거부하면 key 입력을 비우거나 폐기하고 프로젝트를 계속 생성할 수
  있으며, 필요한 경우 QField에서 세션마다 수동 입력한다. builder의 기존 `credentials.enc`는 로컬
  app-data 저장소이므로 복사되는 프로젝트 폴더의 QField 자동 전달 수단으로 간주하지 않는다.
  key는 로그·오류·보고서·URL·query·요청 body에 넣지 않으며, 선택된 routing/optimizer 요청의
  `Authorization` header와 동의한 generated project variable 외에는 기록하지 않는다.
- D-SRP-018 (2026-09-15 승인, Category B/D): `선택 대상`은 QField의 대상 레이어
  피처 선택/체크 상태, `전체 대상`은 선택과 무관한 전체 유효 피처, `미조사 대상`은 전체 중
  FR-SRP-009의 effective completion이 false인 피처다. 완료 Boolean 필드가 비어 있으면 경로별
  완료 체크를 쓰고, 매핑하면 해당 source feature의 Boolean 값을 읽고 쓴다. 패널은 이 준비 절차와
  현재 선택 수를 inline help/label로 설명한다.
- D-SRP-019 (2026-09-15 승인, Category D): 펼친 경로 패널의 editable form field와 selector는
  scroll content의 사용 가능한 너비를 일관된 좌우 margin 안에서 사용한다. 한 행의 여러 field는
  그 너비를 균등하게 나누며 좁은 고정폭·왼쪽 몰림을 만들지 않는다.

## 3. Functional Requirements
- FR-SRP-001: 생성 프로젝트에 기존 보고서/식별 플러그인과 공존하는 하단 접이식 패널.
  접힌 상태는 한 줄의 경로명/완료수. 펼친 상태는 대상·설정·결과·저장·불러오기 제공.
- FR-SRP-002: 확인된 QField Project Plugin API로 현재 선택을
  읽는다. 선택 0개는 명확한 안내 및 계산 금지. 목록의 단순 focus를 선택으로 간주하지 않는다.
  `선택 대상` 옆 inline help는 사용자가 QField에서 대상 레이어를 열고 피처 선택/체크 도구로
  계산할 피처를 체크한 뒤 패널로 돌아오도록 안내하며 현재 인식한 선택 수를 표시한다.
- FR-SRP-003: `선택 대상`/`전체 대상`/`미조사 대상` 범위를 제공하고 각각 QField 선택/체크된
  피처만, 선택과 무관한 전체 유효 피처, 전체 중 effective completion이 false인 피처로 정의한다.
  레이어와 ID, 이름, 완료 필드를 설정 가능하게 한다.
  site가 있는 조사 유형은 `site/site_id/site_name`을 기본값으로 한다. site가 없는 Type 1은
  계산 전 layer/id/name 명시가 필수이고 완료 필드는 선택이다.
- FR-SRP-004: 출발은 GPS 기본. 지도 지정, 특정 조사대상, 저장 기본 출발지도 제공한다.
  기본은 출발로 복귀하는 순회. 저장 기본 출발지는 프로젝트 설정으로 폴더와 함께 이동한다.
  GPS 미수신은 계산 실패 사유를 알리고 좌표를 조작하지 않는다.
- FR-SRP-005: 외부 backend가 실제 도로망의 시간 또는 거리 비용을 최소화하는
  방문 순서를 얻는다. 초기 등록 provider ID는 `ors-vroom`이며 provider interface는 교체 가능하게
  유지한다. 직선거리 TSP로 대체하지 않고 최적해 보장을 주장하지 않는다.
- FR-SRP-006: 명시적인 새 계산/남은 지점 계산 버튼에서만 API를 호출한다.
  펼치기/재시작/불러오기/완료표시에는 네트워크 요청 0회.
- FR-SRP-007: 결과에 고유 route_id, 이름, 생성일, 출발/도착, backend, 상태,
  전체 거리(m)/시간(s), 각 site_id/순번/완료를 저장한다. ETA/구간 거리·시간 및
  도로 LineString은 제공 여부를 표시하고 미제공 값을 만들지 않는다. 초기 `ors-vroom`의
  optional `eta[]`는 방문 순서와 같은 길이의 경로 시작 기준 숫자 초이며, 제공 시
  `eta_basis = "relative_seconds"`를 함께 저장·노출한다. 절대 ISO ETA를 추정하지 않는다.
- FR-SRP-008: 다중 경로 목록/활성 경로는 프로젝트 폴더 내 영구 저장하며 오프라인 재시작과
  전체 폴더 이동 후 재로드 가능. 저장 실패·부분 쓰기·손상 시 기존 정상 사본을 보존하고
  stale revision은 새 정상 사본을 덮어쓰지 않는다. 이 의미는 저장 형식에 독립적이다.
- FR-SRP-009: 기존 완료 필드가 설정되면 이를 읽어 활성 목록에 반영한다. 없으면
  `route_stop.completed`를 사용한다. 완료 필드가 있으면 명시적 Boolean `true`만 완료이며
  `false`/`NULL`/missing은 미완료다. 완료 필드 입력에는 “source layer의 Boolean field 이름이며
  비우면 이 저장 경로 안에서만 완료 상태를 관리한다”는 inline 설명을 제공한다. 매핑된 경우
  경로 행의 완료 check가 편집 가능한 source feature에 true/false를 저장하고 scope/다음 지점에
  즉시 반영한다. 저장할 수 없으면 권한/필드 형식 안내와 함께 기존 값을 보존한다. 다음 지점은
  미완료 중 순번 최소값이다.
- FR-SRP-010: 남은 지점만 현재 GPS로 재계산하며 완료 지점 기록은 유지한다.
  결과를 저장하기 전/실패 시 기존 저장 데이터 불변. revision을 증가시켜 업데이트한다.
- FR-SRP-011: backend가 제공한 도로 LineString을 지도에 표시한다. 미제공이면 도로선 없음으로 안내한다. 저장 경로를 다시 열면 저장 도형 사용.
- FR-SRP-012: nmap://navigation 목적지 좌표/이름 인코딩; 외부 URL 실행 실패 안내.
  OS가 실행 성공 후 앱 내부 상태를 회신하지 않는 한 그 이후의 성공 여부를 단정하지 않는다.
- FR-SRP-013: routing base URL, optimizer endpoint URL, backend, profile, key, timeout,
  허용 도로 이격거리 설정. 초기 `ors-vroom` hosted 기본값은 routing base
  `https://api.heigit.org/openrouteservice`, optimizer endpoint `https://api.heigit.org/vroom/v0`다.
  provider는 정규화한 routing base에 `/v2/matrix/{profile}`과
  `/v2/directions/{profile}/geojson`을 정확히 한 번 붙이고 optimizer endpoint에 직접 POST한다.
  optimizer endpoint 뒤에 `/post` 또는 다른 suffix를 만들지 않는다.
  새 프로젝트는 폐기된 `api.openrouteservice.org`를 기본값이나 fallback으로 사용하지 않는다.
  사용자가 입력한 `http`/`https` custom 또는 self-hosted 두 주소는 저장·재로드하고 자동으로
  HeiGIT 주소나 다른 경로로 치환하지 않는다.
  기본 허용 도로 이격거리는 1000 m다. 선택한 등록 provider에 server/profile/timeout/key/offset을
  전달하고 미등록 backend는 request 전에 거부한다. 하나의 사용자가 입력한 key는 값이 있을 때
  선택된 routing/optimizer 요청의 `Authorization` header에만 전달하고 URL, query, body, 보고서,
  로그 또는 오류에는 넣지 않는다. D-SRP-017에 동의한 generated project variable만 저장 예외다.
  hosted HeiGIT 기본값은 빈 key를 request 전에 거부하고,
  custom/self-hosted 주소는 key 없는 구성을 허용하며 빈 인증 header를 전송하지 않는다.
  key는 D-SRP-017의 동의에 따른 generated project 평문 variable 또는 QField 세션 메모리에서
  가져오며, 나머지 설정과
  기본 출발지·대상 매핑은 프로젝트 폴더 안에 저장한다. timeout/network/HTTP/응답 오류,
  도로 연결 불가·이격거리 초과·일부 unassigned를 전체 계산 실패로 처리하고 기존 경로를 보존한다.
  기존 프로젝트의 routing base가 trailing slash를 제외하고 정확히
  `https://api.openrouteservice.org`인 경우에만 새 hosted routing base로 바꾼다. optimizer endpoint는
  missing/empty 또는 정확히 `https://api.openrouteservice.org/optimization`인 경우에만 새 hosted
  optimizer endpoint로 바꾼다. 두 필드는 독립적으로 migration하고, 그 밖의 non-empty custom/
  self-hosted 값은 보존한다. 이 migration은 request 전 적용하고 다음 정상 설정 저장에 반영한다.
- FR-SRP-014: 앱 직접 입력에 Point, LineString, Polygon 선택. 점은 1개 좌표,
  선은 서로 다른 2개 이상, 면은 유효한 닫힌 고리. 완료 및 여러 대상 저장 제공.
- FR-SRP-015: 지원 업로드 형식(SHP/ZIP/GPKG)의 Point/LineString/Polygon 및
  MultiPoint/MultiLineString/MultiPolygon 자동 인식. 피처 및 다중 부분을 누락하지 않는다.
  서로 다른 도형 계열을 하나의 site 레이어에 섞는 입력은 명확히 거부한다.
- FR-SRP-016: 생성 GPKG의 site 도형 메타데이터와 실제 저장 도형 계열을 일치시킨다.
  단일/다중 혼합은 같은 계열의 Multi 유형으로 승격 가능. 기존 UUID/관계 유지.
- FR-SRP-017: 선·면(단일/다중)은 centroid로 TSP에 전달하며 원본 도형을 수정하지 않는다.
  Point는 원래 점을 사용한다. MultiPoint도 피처마다 centroid 하나를 쓴다. Point를 제외한
  5유형 centroid는 source CRS에서 계산한 뒤 WGS84로 변환하며 원본 도형은 그대로 둔다.
  외부 전송 좌표는 항상 WGS84 [longitude, latitude]다. source CRS가 없거나 유효하지 않거나
  빈/잘못된 도형 또는 변환 불가 입력이면 계산 후보를 거부하고 기존 저장 경로를 보존한다.
  FieldBuild Kit가 정상 생성·검증한 대상 레이어와 유효한 Point/MultiPoint/LineString/
  MultiLineString/Polygon/MultiPolygon은 같은 계약으로 대표점과 WGS84 좌표를 만들 수 있어야 하며,
  새 경로 계산에서 포괄적인 CRS 안내 오류로 거짓 거부하면 안 된다.
- FR-SRP-018: 생성·검증·표시·첨부 업로드 경로에 도형 확장을 일관되게 적용한다.
  기존 폴리곤 프로젝트의 재생성/검증 및 기존 식별/보고서 기능을 회귀 검사한다.
- FR-SRP-019: FieldBuild Kit 프로젝트 생성 흐름은 masked ORS/HeiGIT route API key 입력과 값의
  용도를 설명한다. key를 입력한 경우 생성 전에 프로젝트 평문 포함, 폴더 접근자의 읽기·사용 가능성,
  암호화되지 않음을 명시하는 경고와 QField 자동 전달 동의를 받는다. 동의하면 generated project
  variable에 평문으로 포함하고, 거부하면 key를 비우거나 폐기한 뒤 프로젝트 생성을 계속하여 QField
  세션 수동 입력을 허용한다. key는 로그·오류·보고서·URL·query·요청 body에 넣지 않는다. builder
  장치에서 선택적으로 기억하는 경우 기존 app-local `credentials.enc` 보안 계약을 재사용할 수 있지만
  그것은 QField 전달 수단이 아니다.
- FR-SRP-020: 펼친 경로 패널의 TextField, ComboBox 및 기타 editable/selection field는 동일한
  좌우 content margin 사이의 available width를 채운다. 두 field가 한 행을 공유하면 같은 너비로
  나누고, scroll viewport 폭이 바뀌어도 한쪽의 좁은 고정폭이나 불필요한 빈 오른쪽 영역이 생기지
  않는다. label/help/error는 같은 좌우 기준선에 맞추고 필요한 경우 wrap한다.

## 4. Data / Compatibility
새 프로젝트 생성만 도형 메타데이터를 변경한다. 사용자의 기존 GPKG를 자동 마이그레이션하지
않는다. 기본 도형 유형을 지정하지 않은 과거 호출은 MULTIPOLYGON 기본값을 유지한다.
업로드 Z/M은 기존 저장소의 2D 정규화 정책을 유지하되 XY와 다중 부분을 보존한다.
기존 polygon-bearing GeometryCollection 정규화는 호환성 경로로 유지한다.
route_stop의 site_id는 설정한 레이어 ID 필드의 문자열 값이며 실제 소스 레이어도 저장한다.
완료 상태를 임의로 관찰 레코드 존재 여부나 날짜에서 추정하지 않는다.

`eta[]`는 방문 stop 순서와 1:1 대응하는 non-negative finite number 배열이다. 초기 provider의
값은 VROOM `steps[].arrival`에서 job step만 추출한 경로 시작 기준 초이며
`eta_basis = "relative_seconds"`다. 제공하지 않으면 `eta`와 `eta_basis`는 모두 absent/null이고,
한쪽만 있거나 길이·숫자 검증이 실패한 결과는 저장 후보가 아니다. `created_at`은 경로 레코드의
생성시각일 뿐 ETA epoch가 아니다.

프로젝트 이동 대상 non-secret 설정은 routing base URL, optimizer endpoint URL, provider ID, profile, timeout,
max road offset, default start, layer/id/name/optional completion mapping이다. API key는 이 일반 설정에서
제외하며, 자동 전달에 동의한 경우에만 별도 generated project variable에 평문으로 포함한다. 이 값은
암호화되지 않고 프로젝트 폴더 접근자가 읽고 사용할 수 있다.
저장 형식은 규범이 아니며 소비자는 상대 경로로 동일한 route/revision/settings 의미를 복구해야 한다.
초기 hosted routing base는 version 없는 `https://api.heigit.org/openrouteservice`이고, provider가
그 뒤에 ORS `/v2/...` 경로를 붙인다. optimizer 설정은 완전한 endpoint
`https://api.heigit.org/vroom/v0`다. 여기에 `/post`를 붙이지 않는다. custom/self-hosted 주소는 이 두
역할을 같은 방식으로 구분한다. 기존 프로젝트 migration은 D-SRP-015의 exact-match 값만 바꾸며
경로 데이터, key 및 다른 설정을 변경하지 않는다.

## 5. Acceptance Criteria
| ID | 관찰 가능한 조건 및 결과 |
|---|---|
| AC-SRP-001 | 생성 QML은 기존 플러그인 기능과 경로 패널을 로드하고 상대 경로 자산 포함 |
| AC-SRP-002 | 선택 inline help가 QField 대상 레이어 피처 선택/체크 절차와 인식 수를 표시; 선택 0/1/N에서 각각 안내·계산 금지/1개/정확히 선택 N개 목록 및 요청; focus-only 0개 |
| AC-SRP-003 | 선택/전체/미조사가 각각 checked selection/선택 무관 전체/effective completion false 전체를 사용; site 유형 기본 매핑, Type 1 명시 layer/id/name, optional 완료 매핑, 중복/빈 ID 거부 |
| AC-SRP-004 | GPS 유효/무효, 지도 지정, 대상 지정, 프로젝트-local 기본 출발지 저장/복구/폴더 이동 및 순회 |
| AC-SRP-005 | 등록 `ors-vroom`이 도로 비대칭 행렬의 시간/거리 비용으로 요청 생성, 모든 지점 1회 할당 |
| AC-SRP-006 | 미등록 backend request 전 거부 및 0/네트워크/HTTP/timeout/잘린 JSON/null 행렬/unassigned/이격거리 초과 시 기존 경로 불변 |
| AC-SRP-007 | 거리/시간/순번 검증·저장; optional `eta[]` 숫자 상대초 + `eta_basis=relative_seconds` 동시 roundtrip; ISO/한쪽만/잘못된 길이 거부; LineString 미제공 표시 |
| AC-SRP-008 | 2개 이상 경로와 non-secret 설정 저장·선택·재시작·폴더 이동 후 동일 데이터 복구, key 없이 API 0회 |
| AC-SRP-009 | 저장 형식과 무관하게 부분 쓰기·저장 손상·갱신 충돌에서 정상 경로 보존/안전한 복구 또는 명확한 거부 |
| AC-SRP-010 | 완료 inline help가 Boolean source field와 빈 값의 route-local 의미를 설명; mapped field의 true/false/NULL/missing과 no-field 로컬 완료를 즉시 scope/다음 지점에 반영; mapped write success와 권한/형식 실패 시 원값 보존; 2/8 완료 계산 |
| AC-SRP-011 | 12중 4완료 재계산은 GPS+8개만 요청하고 4개 기록 유지 |
| AC-SRP-012 | 지도 도로선 재표시와 인코딩된 nmap URL/실패 안내 |
| AC-SRP-013 | 새 프로젝트의 등록 `ors-vroom` 기본 설정이 matrix `https://api.heigit.org/openrouteservice/v2/matrix/{profile}`, directions `https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson`, optimizer POST `https://api.heigit.org/vroom/v0`를 요청하고 `/vroom/v0/post` 및 `api.openrouteservice.org` 요청은 0회; routing base 끝 `/`도 중복 경로 없음; 기존 exact routing default와 missing/empty 또는 exact legacy optimizer만 각각 migration하고 혼합된 custom 값은 보존; 사용자 입력 custom/self-hosted routing base와 완전한 optimizer endpoint를 저장·재로드하여 치환 없이 같은 경로로 요청; server/profile/timeout/offset과 project variable 또는 session의 non-empty key를 transport 경계에 전달하고 key는 선택된 요청의 `Authorization` header에만 존재; hosted 기본값의 빈 key는 request 전 거부, key 없는 custom 요청은 인증 header 생략; 펼침/접힘/완료/불러오기 API 0회; key의 URL·query·body·보고서·로그·오류 노출 없음; 나머지 설정 폴더 이동 보존 |
| AC-SRP-014 | 직접 점/선/면 선택·완료·다중 대상 저장, 미완성 도형 안내 |
| AC-SRP-015 | SHP/ZIP/GPKG × 6유형 자동 판별·XY/다중 부분 보존 |
| AC-SRP-016 | 업로드/직접 입력→GPKG 메타데이터/rtree→생성 프로젝트 도형 일치 |
| AC-SRP-017 | FieldBuild Kit가 생성·검증한 투영 CRS와 WGS84 test site의 6유형에서 새 경로 계산이 포괄적 CRS 오류 없이 Point 원점/MultiPoint·선·면 source-CRS centroid→WGS84를 생성; 원본 불변; 실제 source CRS missing/invalid/변환 실패 시 명확한 거부와 기존 경로 보존 |
| AC-SRP-018 | 기존 폴리곤/관계/식별/보고서 회귀 및 옮겨진 생성물 검사 |
| AC-SRP-019 | 프로젝트 생성 UI에 masked route key 입력이 있고, 입력 시 평문 포함·폴더 접근자의 읽기/사용 가능·비암호화를 명시한 경고와 consent가 존재; 동의하면 generated project variable의 평문 key로 QField가 자동 사용; 거부·blank이면 key 없이 생성되고 QField session 수동 입력 가능; 입력·거부·취소·생성 실패에서 key가 로그/오류/보고서/URL/query/body/non-secret 일반 설정에 없음; 선택적 desktop remember는 기존 `credentials.enc`만 사용하고 QField 전달로 간주하지 않음 |
| AC-SRP-020 | 최소·넓은 panel viewport에서 모든 editable/select field가 공통 좌우 margin 안의 available width를 사용하고, 같은 행 field는 균등 분할하며, label/help/error 기준선·wrap과 horizontal overflow를 layout/screenshot으로 검사 |

## 6. API 근거 / 검증 경계
VROOM 근거는 초기 provider가 대상으로 삼은 **v1.14.0 tag**에 고정한다. 공식 문서는 timing을
초 단위로 정의하고 relative planning horizon이면 `arrival`도 그 시작 기준이라고 명시한다.
초기 provider 계약에 절대 epoch가 없으므로 D-SRP-009는 이를 `relative_seconds`로 정규화한다.
- https://github.com/VROOM-Project/vroom/blob/v1.14.0/docs/API.md

현재 hosted endpoint와 key migration 근거는 openrouteservice의 공식 공지다. 2026-04-28 공지는
directions/matrix를 `api.heigit.org/openrouteservice/v2/...`, optimization을
`api.heigit.org/vroom/v0`으로 옮기고 기존 key가 새 주소에서 유효하다고 명시했다. 최초 공지의
2026-08-24 shut-off 일정은 2026-08-27 후속 공지에서 기존 주소 quota 10%와 2026-09-28 종료로
변경되었다. 이 일정 차이는 deprecated 주소를 기본값에서 제거해야 한다는 결론을 바꾸지 않는다.
- https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912
- https://ask.openrouteservice.org/t/reducing-the-quota-of-deprecated-api-api-openrouteservice-org/8013
- https://api.heigit.org/vroom/v0

아래는 기존 조사 후보 링크다. QField 4.2.4와 org.qfield는 지원 버전/API 확정이 아니며,
실제 대상 버전에서 기능과 import를 확인해야 한다. 승인된 provider timing 결론은 아래
unpinned 링크에 의존하지 않는다.
- https://github.com/opengisch/QField/blob/v4.2.4/src/qml/qgismobileapp.qml
- https://github.com/opengisch/QField/blob/v4.2.4/src/core/multifeaturelistmodel.h
- https://github.com/opengisch/QField/blob/v4.2.4/src/core/expressionevaluator.h
- https://github.com/opengisch/QField/blob/v4.2.4/src/core/utils/fileutils.cpp
- https://github.com/opengisch/QField/blob/v4.2.4/src/core/utils/layerutils.h
- https://github.com/opengisch/QField/blob/v4.2.4/src/qml/GeometryRenderer.qml
- https://github.com/opengisch/QField/blob/v4.2.4/src/qml/MapCanvasPointHandler.qml
- https://api.qfield.org/snippets/
- https://giscience.github.io/openrouteservice/api-reference/endpoints/optimization/
- https://guide.ncloud-docs.com/docs/maps-url-scheme

실제 QField/iOS/Android와 네이버지도 실행 검증은 AGENTS.md에 따라 사용자 수행 항목이다.
자동 QML/JS 검사를 실기 검증으로 기록하지 않는다. 서버 실호출 미실행도 구분한다.

## 7. 현재 생성 경로와 후속 변경 위치

| 소스 | 검토할 책임 |
| --- | --- |
| `qfield_builder/ui/wizard.py`, `site_upload.py`, `gpkg_upload_reader.py`, `shapefile_reader.py`, `wkt.py` | 현재 site MULTIPOLYGON 중심 입력·검증을 점/선/면과 6유형 업로드로 확장 |
| `qfield_builder/build.py`, `schemas.py`, `gpkg.py` | 도형 계약·저장·인덱스·관계·검증 |
| `qfield_builder/qgis_worker.py` 공개 wrapper → `template_project.py`, `standalone_gis.py` | 실제 템플릿/도형 처리; 남은 개발용 PyQGIS 구현과 구분 |
| `qfield_builder/templates/`, `qml_plugin.py` | 도형별 레이어/스타일과 기존 보고서·식별 플러그인 공존 |
| `qfield_builder/qfield_routes/` (현재 uncommitted 후보), 패키지 자원 설정 | UI/controller, provider registry/transport, 저장, 좌표, 내비게이션 분리 및 상대 경로 배포 |

파일 목록은 영향 분석이지 구현 완료 목록이 아니다. QGIS Desktop 의존을 다시 추가하지 않는다.
내부 패키지명·build recipe·QPB 형식·bundle ID·암호화 저장소 식별자도 바꾸지 않는다.

## 8. 미정 사항과 승인/검증 순서

- **O-SRP-001 (해결):** 2026-09-14 명세 checkpoint `e382c77`과 acceptance checkpoint
  `ed8ac81`이 각각 승인되었고, 현재 명세 정합 slice는 2026-09-15 별도로 승인되었다.
- **O-SRP-002:** 실제 QField/iOS/Android 대상 버전에서 선택/GPS/파일/지도/모듈 API 검증,
  ORS/VROOM 또는 Valhalla API 버전·한도·profile 및 시간/거리 기준 지원 검증 후 기술 선택 확정.
  D-SRP-015는 현재 hosted 주소 조합만 고정하며 live quota와 service capability를 검증한 것으로
  보지 않는다.
  기존 macOS QField 4.2.11 기록은 경로 기능 검증이 아니다.
- **O-SRP-003 (해결):** 승인된 D-SRP-003과 사용자 centroid 지시를 D-SRP-011/FR-SRP-017에
  일관되게 풀었다. 6유형 대표점 순서와 source CRS 실패 조건 외에 새 geometry 정책은 없다.
- **O-SRP-004 (부분 해결):** 저장 형식과 독립적인 보존/재시작/이동/revision 의미는
  D-SRP-013에서 고정한다. 이중 JSON 후보의 native QField FileUtils·원자성·복구 실현 가능성은
  계속 미검증이며 형식 확정 전 실제 기기 검증이 필요하다.
- **O-SRP-005 (해결):** D-SRP-012/013이 Boolean 완료, Type 1 명시 매핑,
  1000 m 기본 이격거리, non-secret 프로젝트 설정 이동과 승인된 key 전달 선택지를 구체화한다.
- **O-SRP-006 (해결):** D-SRP-015/FR-SRP-013이 현재 HeiGIT hosted 기본값,
  routing base와 완전한 optimizer endpoint의 구분, 사용자 입력 key 인증 경계, custom/self-hosted
  주소 보존과 exact-match legacy default migration을 구체화한다. provider별 별도 credential 또는 서로 다른 auth scheme 지원은 승인된
  범위가 아니며 필요 시 별도 제품 결정이다.
- **O-SRP-007 (2026-09-15 해결):** 사용자가 “평문 포함 방식으로 명세 승인”했다. masked builder
  입력 뒤 명시적 위험 경고와 consent를 받고 generated project variable에 평문으로 넣어 QField가
  자동 사용한다. 폴더 접근자는 누구나 key를 읽고 사용할 수 있으며 암호화를 주장하지 않는다.
  consent를 거부하면 blank key로 생성하고 QField session에서 수동 입력할 수 있다.

### 승인 뒤 acceptance 정합 범위

승인된 현재 명세를 기준으로 새 test-designer가
**FR-SRP-001~005, FR-SRP-007~010, FR-SRP-013, FR-SRP-017, FR-SRP-019~020**과
**AC-SRP-001~010, AC-SRP-013, AC-SRP-017, AC-SRP-019~020**을 정합한다. 특히 현재
`test_ac007_result_roundtrip`의 ISO `eta` fixture는 숫자 상대초/`eta_basis` 계약으로,
`test_ac013_backend_settings`의 `acceptance_backend`는 등록 `ors-vroom` + 외부 transport seam으로
바뀌어야 한다. 같은 AC-SRP-013 정합은 fresh default의 HeiGIT matrix/directions/VROOM URL,
`/post` suffix 0회, deprecated host 0회, exact default migration, trailing slash 정규화,
user-entered key의 hosted/custom 인증 경계와 custom/self-hosted URL roundtrip도 검증해야 한다.
이 문서는 acceptance 파일을 수정하거나 그 변경을
미리 승인하지 않는다.

Phase 1은 패널·선택 목록·GPS, Phase 2는 backend·최적 순서, Phase 3은 영구 저장·재시작,
Phase 4는 제공된 도로선·네이버지도, Phase 5는 완료·남은 대상·다중 경로다.
각 단계에서 기존 기능 회귀를 확인한다. 도형 확장은 생성·선택·좌표의 횡단 작업으로 함께 계획한다.
현재 명세 승인 완료 → 새 test-designer 정합 → acceptance 산출물 승인 → 새 implementer
정합 → 검사 → 새 reviewer. 이번 문서 정합에서 앱 테스트·실서비스·QField 기기 검사를 실행하지
않았고 implementation attempt 2의 기존 104 passed/2 failed/12 skipped를 최종 PASS로 승격하지 않는다.
