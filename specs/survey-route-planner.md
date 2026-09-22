# Feature: 도로망 조사 경로 및 조사대상 도형 확장

> Status: **APPROVED clarification D-SRP-067 / FR-SRP-064 / NFR-SRP-012 / AC-SRP-066 (2026-09-22).** The approved baseline through D-SRP-064~066 / FR-SRP-061~063 / NFR-SRP-011 / AC-SRP-063~065 remains unchanged.
> Approved baseline preserved: specification checkpoint `e382c77`; 2026-09-15 approved reconciliation; acceptance checkpoint `ed8ac81`; 2026-09-16 approved workflow/progress slice; D-SRP-031~035, FR-SRP-029~033 and AC-SRP-031~035 approved 2026-09-16; D-SRP-036~041, FR-SRP-034~039, NFR-SRP-004 and AC-SRP-036~041 approved 2026-09-17; D-SRP-042~045, FR-SRP-040~043, NFR-SRP-005 and AC-SRP-042~045 approved 2026-09-17; D-SRP-046~048, FR-SRP-044~046, NFR-SRP-006 and AC-SRP-046~048 approved 2026-09-17; D-SRP-049~056, FR-SRP-047~053, NFR-SRP-007~009 and AC-SRP-049~055 approved 2026-09-18. Target QField device verification remains **NOT RUN (미검증)**.
> Owner: spec-writer
> Extends: [통합 명세](qfield-project-builder.md)
> Test design: [승인된 기준본](../tests/acceptance/survey_route_planner.test-design.md) — FR-SRP-029~039, AC-SRP-031~041 및 NFR-SRP-004까지 2026-09-17 반영·승인됨; 2026-09-18 승인 ID는 아직 반영되지 않음
> Traceability: [승인된 기준본](../tests/acceptance/survey_route_planner.traceability.md) — 이번 승인 slice 또는 현재 구현의 통과 증거 아님


## 0. 문서 권한과 현재 상태 (2026-09-14)

**2026-09-22 저장 성공 후 disabled/focus·읽기 순서 정합 (승인):** 승인된
D-SRP-065/AC-SRP-063의 `candidate 없음` 최우선 disabled 규칙과 AC-SRP-064/NFR-SRP-011의
focus 보존 문구를 저장 button이 성공 후에도 활성 상태와 `activeFocus`를 유지해야
한다는 의미로 읽으면 둘을 동시에 충족할 수 없다. 이는 Category B 내부 충돌이며,
아래 D-SRP-067/FR-SRP-064/NFR-SRP-012/AC-SRP-066은 candidate를 clear하는 성공 상태
갱신에서 disabled 규칙이 항상 우선하고 focus 보존은 다른 editable/control에 앱이
focus를 옮기거나 그 상태를 바꾸지 않는다는 의미임을 제한적으로 명확히 한다.
또한 NFR-SRP-011의 기존 의미를 따라 시각·semantic accessibility 순서를 기본 결과 →
fallback notice(적용 시) → `상세 정보` disclosure(펼쳐진 진단은 이 control 바로 뒤) →
`저장할 경로 이름` → `계산 결과 저장` → disabled reason(적용 시) → 최종 outcome
status(저장 시도 후)로 고정한다. 현재 QML의 다른 순서는 이미 승인된 NFR-SRP-011의
Category A conformance defect이지 새 제품 범위가 아니다. D-SRP-064가 AC-SRP-053/059의
endpoint-gap 표시 위치를 단일 disclosure 내 한 줄로 이미 supersede했으나, 기존 승인
acceptance 산출물에 삭제된 표시 object와 세 위치의 endpoint-gap line을 요구하는 규칙이
남아 있다. 이들은 본 명세 승인 후 fresh test-designer가 현재 표시 계약과 정합하고,
그 구체적 산출물은 별도 사용자 승인을 받아야 한다.

**2026-09-22 실제 기기 저장 관찰 및 UI 단순화 (승인):** 사용자는 실제 QField 기기에서 계산된
경로가 여전히 저장되지 않는 것으로 관찰했고, `지도에 없는 도보 구간 포함` checkbox가 선택 가능한
옵션처럼 보이며 저장을 위해 확인해야 하는 이유도 불명확하다고 보고했다. 사용자의 명시적 Category C
변경은 이 checkbox와 acknowledgement save gate를 제거하고 fallback이 포함되었다는 사실만 exact notice로
항상 알리는 것이다. `ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함` 같은 원시 기술 문구와
중복 endpoint-gap 안내는 기본 화면을 복잡하게 하므로, 필요한 사용자만 펼치는 `상세 정보` 아래 한 번만
제공하는 것은 Category D refinement다. 저장 action이 성공한 경우에만 기존 message 위치를 현재 viewport로
옮기는 구현은 승인된 저장 실패 보존 계약이 화면 밖에 남아 사용자에게 아무 반응이 없는 것처럼 보이게 할
수 있으므로 Category A conformance defect다. 아래 D-SRP-064~065, FR-SRP-061~062, NFR-SRP-011 및
AC-SRP-063~064는 같은 DRAFT slice의 이전 acknowledgement 제안을 대체하며, D-SRP-054/061,
FR-SRP-050/058 및 AC-SRP-051/053/060의 acknowledgement 요구만 명시적으로 supersede한다. 또한
D-SRP-060, FR-SRP-057, NFR-SRP-009 및 AC-SRP-059의 endpoint-gap·raw provenance를 기본 화면 여러 곳에
노출하던 presentation 부분은 D-SRP-064의 단일 disclosure placement로 supersede하되 그 의미와
접근 가능성은 유지한다. fallback의 직선거리 추정 provenance, 시간 사용 불가, 경고 표시와 저장
atomicity는 유지한다. 이번 관찰만으로 실제 persistence 실패의 원인이 controller validation, 저장소
write/readback 또는 다른 단계 중 무엇인지는
입증되지 않았으며, 명세는 원인을 단정하지 않는다. 또한 경로 패널 runtime은 생성 시 각 프로젝트 폴더에
복사되므로 desktop app 재빌드·재설치만으로 기존 생성 프로젝트가 바뀌지 않는 현재 경계를
D-SRP-066/FR-SRP-063/AC-SRP-065가 명시한다. 이 slice는 2026-09-22 사용자가 승인했으며 fresh
test-designer가 acceptance/traceability를 별도 작성하고 그 산출물도 별도 승인받아야 한다.

**2026-09-22 Matrix `snapped_distance`와 desktop credential-store 정합 (승인):** 유효한 ORS
Matrix 응답이 resolved location object의 optional `snapped_distance`를 생략할 수 있는데도 이를 필수
숫자로 검사하여 origin validation 또는 vehicle matrix를 거부하는 현상은 기존 도로 경로 계약의
Category A conformance defect다. 다만 필드 누락과 provider가 명시적으로 반환한 malformed/초과 값을
구분하는 규칙은 기존 문구에 없으므로 D-SRP-062/FR-SRP-059/AC-SRP-061이 최소한으로 명확히 한다.
또한 이 독립 애플리케이션의 현재 identity authority인 `docs/independence.md`와 달리 상속된 통합 명세의
과거 rename/migration 문구를 route-key 저장 경로로 적용하면 `credentials.enc` 위치가 둘로 갈리고 다른
애플리케이션의 비밀을 읽을 수 있다. 이는 Category A conformance defect이며, D-SRP-063/FR-SRP-060/
NFR-SRP-010/AC-SRP-062는 display name과 분리된 기존 `FieldBuild Standalone` app-data namespace 하나만
사용하고 다른 앱 저장소는 읽거나 가져오거나 이동하지 않는 현재 호환성 계약을 기록한다. 이 승인 slice는
기존 승인 이력, 암호화 방식, remember consent 또는 generated-project 평문 전달 예외를 바꾸지 않으며
사용자 승인 전에는 test-designer/implementer 기준이 아니다.

**2026-09-21 ORS 1점 도보 geometry 정합 (승인):** 실제 QField 계산에서 ORS가
`LineString` type과 좌표 한 점, route-level `way_points=[0,0]`을 반환하는 퇴화된 성공 응답이
관찰됐다. 이는 D-SRP-060의 두 점 이상·strictly increasing way-points 계약에는 맞지 않지만, 두 요청
endpoint가 같은 보행 graph 위치로 snap되어 provider 구간이 0이 된 경우를 기존 unmapped fallback으로
안전하게 표현할 수 있는지에 대한 Category B ambiguity다. 아래 D-SRP-061, FR-SRP-058 및 AC-SRP-060은
엄격한 0 metric 조건에서만 기존 `unmapped_estimate/straight_line_lower_bound_m`을 재사용하고 mapped
geometry를 만들지 않는 최소 정합 제안이다. D-SRP-060의 정상 mapped geometry 계약과 그 밖의 malformed
  응답 거부는 유지하며 2026-09-21 사용자가 승인했다.

**2026-09-21 ORS 도보 endpoint snapping 명확화 (승인):** 실제 ORS `foot-hiking`
GeoJSON이 요청한 access/source가 아니라 routing graph에 snap된 좌표에서 시작·끝날 수 있는데도 현재
구현이 geometry endpoint를 요청 좌표와 1 m 이내로 강제하고 provider distance를 요청 좌표 사이
geodesic보다 짧다는 이유로 거부하는 현상은 승인되지 않은 over-validation이다. 그러나 승인된
D-SRP-051/053, FR-SRP-049/050 및 AC-SRP-051은 `access→source`와 `exact`가 요청 좌표 전체의 물리적
연결을 뜻하는지, provider가 실제로 계산한 snapped graph 구간만을 뜻하는지 구분하지 않아 단순한
Category A 제거만으로는 거리·시간을 과장해 설명할 수 있다. 이는 Category B ambiguity다. 아래
D-SRP-060, FR-SRP-057 및 AC-SRP-059는 requested access/source를 immutable marker로 계속 보존하고,
구조가 유효한 provider geometry/metric을 수정 없이 받아들이되 그 범위를 provider-routed graph
구간으로 명시하는 최소 정합이며 2026-09-21 사용자가 승인했다. synthetic connector, 추정 거리/시간, 새 provenance 값 또는
schema 4를 만들지 않는다. 기존 승인 기준과 acceptance artifact는 소급
변경하지 않는다.

**2026-09-19 reviewer-blocker 분류와 최소 정합 제안 (DRAFT):** 이번 correction cycle은
승인된 동작을 구현·검증하는 과정에서 드러난 일곱 항목을 다시 분류한다. (1) callback 시점에
관찰되고 result 생성 전에 닫혀 별도 seal된 provenance를 요구하는 것은 제품 동작이 아니라 승인
acceptance evidence의 신뢰성 문제이므로 Category E acceptance conformance이고 제품 명세 공백이 아니다.
(2) 일반 앱 cold start에서 last-good recovery가 실제로 도달 가능해야 하는 것은 FR-SRP-008/051과
AC-SRP-052/056의 restart/recovery 계약에 대한 Category A conformance다. (5) 모든 visit에서 site,
mode, metric source와 out-and-back 의미를 screen reader로 읽을 수 있어야 하고 `exact_zero`도 제외하지
않는 것은 FR-SRP-049, NFR-SRP-009 및 AC-SRP-053의 Category A conformance다. (7) iOS launcher
false/exception의 exact 문구 `Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요.`는
이미 FR-SRP-053에 고정되어 있으므로 Category A conformance다. 이 네 항목은 새 제품 요구를 만들지 않는다.

반면 (3) 빈 저장소와 settings-only/default write가 언제 schema 3이 되는지, (4) 하나의 legacy route를
mixed route로 저장할 때 같은 문서의 관련 없는 legacy route를 어떻게 보존하면서 D-SRP-057의 schema-3
검증 범위를 표현할지는 승인 문구에 결정적 표현 규칙이 없어 Category B ambiguity다. (6) D-SRP-025/030의
`show_route_line` 재시작·폴더 이동 persistence와 D-SRP-055/AC-SRP-054의 toggle settings-write 0회는
동시에 충족할 수 없는 Category B direct conflict다. 아래 D-SRP-058~059, FR-SRP-055~056 및
AC-SRP-057~058만 이를 최소 정합하며 **2026-09-19 사용자 승인됨**. 기존 승인 요구·acceptance
artifact를 소급 변경하지 않는다.

**2026-09-18 schema-3 visit 검증 명확화 제안:** D-SRP-053은 각 visit에 `layer_id`와
`metric_source`를 저장하도록 승인했지만, 누락된 필드가 있는 저장 문서의 read-time 처리와
`walking_mode`별 허용 provenance 조합을 열거하지 않았다. 이는 새 route mode나 저장 기능을
추가하지 않고 승인된 exact provider provenance와 last-good 보존 의미를 결정적으로 검증하기 위한
Category B clarification이다. 아래 D-SRP-057, FR-SRP-054 및 AC-SRP-056은 **2026-09-18 사용자 승인됨**.
기존 schema 1/2 read-only 호환성과 schema-3 정상 데이터 의미는 바꾸지 않는다.

**2026-09-18 iOS 지도 길안내 변경 제안:** 실제 iPhone/QField에서 `다음 지점 네이버지도 안내`를
누르면 NAVER Maps가 설치되어 있어도 App Store의 해당 앱 페이지가 열리는 현상은, project plugin이
QField host의 `Info.plist`와 `LSApplicationQueriesSchemes`를 바꿀 수 없는 상태에서 `nmap` dispatch의
false 반환을 설치 부재로 간주해 자동 fallback한 결과다. iOS는 Apple Maps HTTPS driving directions를
사용하고 iOS의 NAVER/App Store fallback만 제거한다. Android는 NAVER Maps package-bound navigation과
기존 Google Play fallback을 변경 없이 유지한다. 이는 Category C 사용자 승인 변경이다. 아래 D-SRP-056,
FR-SRP-053 및 AC-SRP-055는 D-SRP-022/D-SRP-039, FR-SRP-025/037 및 AC-SRP-025/039의 iOS provider와
App Store fallback 부분만 명시적으로 supersede하는 제안이었으며 **2026-09-18 승인된 명세 기준**이다.
기존 승인 이력과 Android NAVER dispatch/fallback contract는 보존하며, acceptance 산출물은 별도 단계에서
정합하고 승인받아야 한다.

**2026-09-18 provider 오류 세부정보 제안:** QField 도로 경로 계산에서 provider가
HTTP 404와 원인을 설명하는 본문을 반환해도 transport가 본문을 버려 진단할 수 없는
현상은 기존 FR-SRP-013의 HTTP/응답 오류 처리에 대한 Category A conformance defect다.
어떤 provider 세부정보를 표시해도 비밀·요청·거대/형식 본문을 노출하지 않는지를 고정하는
계약은 Category B clarification이다. 아래 D-SRP-049, FR-SRP-047, NFR-SRP-007 및
AC-SRP-049는 기존 endpoint, authentication, key 저장/노출 금지 계약을 변경하지 않는
제안이었으며 **2026-09-18 승인된 명세 기준**이다. acceptance 산출물은 별도 단계에서 정합하고 승인받아야 한다.

**2026-09-18 차량 접근점·도보 last-mile 제안:** 산간·농촌·비포장 조사지의 original coordinate에
대해 configured radius의 direct ORS `driving-car` snap을 요청하고 반환 access point에서 도보 방문을
분리하는 일은 현재 도로-only 제품 계약에 대한 Category C 변경이다. 아래 D-SRP-050~055,
FR-SRP-048~052, NFR-SRP-008~009 및 AC-SRP-050~054는 원본 조사 좌표를 보존하면서
차량 접근점, 차량 구간과 도보 왕복 방문을 분리하는 제안이었으며 **2026-09-18 승인된 명세 기준**이다. 기존 ORS/VROOM
provider를 그대로 쓰고 새 dependency, 별도 지도 자료 또는 self-hosted 서버를 요구하지 않는다.
acceptance 산출물은 별도 단계에서 정합하고 승인받아야 하며, 기존 승인 기준과 D-SRP-049를
소급 변경하지 않는다.

**2026-09-17 iOS 후속 관찰 승인:** 제공된 iPhone/QField screenshots에서 dark-mode host의
route panel이 light surface와 white foreground를 혼합해 label/help/value/action text를 사실상 읽을
수 없게 만드는 현상은 NFR-SRP-004의 Category A conformance defect이며, supported light/dark host
theme 전반의 상태별 contrast를 명시하는 일은 Category B/D 정합이다. 첫 `조사지` floating label이
상단 route-summary button 아래에 가려지는 현상은 D-SRP-043의 no-collision 계약에 대한 Category A
defect이자 Category D spacing refinement다. `저장할 경로 이름`의 iOS keyboard 미개방은 이미 승인된
D-SRP-042/FR-SRP-040의 Category A defect이며 계약을 변경하지 않고 재확인한다. 오늘 날짜 기반 기본
이름은 Category C 사용자 지시다. 아래 D-SRP-046~048, FR-SRP-044~046, NFR-SRP-006 및
AC-SRP-046~048은 **2026-09-17 승인된 명세 기준**이다. ORS checkbox 문구와 Tabler icon 범위는
통합 명세의 승인된 D-101/D-102를 따른다.

**2026-09-17 승인 실기 관찰 정합:** 실제 QField에서 `저장할 경로 이름`을 눌러도 모바일
소프트 키보드가 열리지 않는 현상과 generated site/`조사지` feature의 이름 label이 보이지 않는
현상은 각각 승인된 FR-SRP-034 및 FR-SRP-039에 대한 Category A conformance defect다. 저장 경로
불러오기 dropdown을 같은 floating-label pattern에 포함하고 모든 label을 outline 상단선에 정확히
걸치도록 맞추는 일, name field 부재 시 stable ID를 label fallback으로 쓰는 일, FieldBuild Kit
wizard Step 7에 ORS key의 용도·미입력·평문 포함 동의를 설명하는 일은 Category D refinement다.
아래 D-SRP-042~045, FR-SRP-040~043, NFR-SRP-005 및 AC-SRP-042~045는 기존 ID와 승인 이력을
보존하는 **2026-09-17 승인 추가안**이다. 정적 문자열/QML/XML 검사는 구현 구조의 자동 proxy일 뿐 모바일
키보드 개방이나 QField 지도 label 실제 렌더링의 PASS 증거가 될 수 없다.

**2026-09-17 승인 후속 정합:** 계산 성공 뒤 경로 이름을 입력·수정하면 재계산 없이 즉시 저장되어야
하는 현상은 FR-SRP-007/008의 Category A conformance defect다. 경로 패널 label 통일, 서버 설정의
초기 접힘, 저장 위치·scope feedback, polygon 조사지 색과 name label은 Category D refinement다.
`VROOM v1.14 서버 URL` 문구 단순화, session key와 동의 기반 평문 project variable의 구분,
설정 snapshot 위치 설명, 공식 플랫폼별 NAVER dispatch/fallback, 방문 순서 밖 completion 입력의
처리는 Category B clarification이다. 아래 D-SRP-036~041, FR-SRP-034~039, NFR-SRP-004 및
AC-SRP-036~041은 기존 승인 ID와 이력을 보존하는 **승인된 명세 기준**이며, acceptance 산출물은 새
test-designer가 별도로 정합하고 승인받아야 한다.

**2026-09-16 승인 사용자 지시 정합:** `조사 경로 계산 대상`, `출발지`,
조사지 layer/ID/name/completion selector의 in-control floating label, `선택 대상`에서만 보이는
선택 안내·현재 수, 지도 중심 출발지의 임시 marker는 Category D UX refinement다. 조사대상 출발
후보가 계산 scope와 정확히 같은 candidate set을 쓰는 규칙은 Category B clarification이다.
유효한 line 조사지에서 새 경로 계산이 `도로 구간 순서 또는 도형이 올바르지 않습니다.`로 실패하는
현상은 이미 승인된 FR-SRP-017/026에 대한 Category A conformance defect이며, 여섯 geometry family에
공통인 provider-response acceptance와 provider/client 오류 구분은 Category B clarification이다.
Point와 Polygon은 아직 실제 QField에서 수동 확인되지 않았으므로 PASS로 간주하지 않는다. 이 승인
slice는 승인된 이력과 stable ID를 보존하며, 아래 supersession과 새 ID가 승인 기준본을 확장한다.

**2026-09-16 승인 변경:** 대상/필드/출발을 project-backed dropdown으로 바꾸고 field label,
조건부 control, 저장 피드백, 방문 안내와 표시 형식을 정리한다(Category C/D). 작동하지 않는
네이버지도 action은 FR-SRP-012의 Category A conformance defect다. 남은 지점 재계산 제거,
완전한 구간 저장, 완료 기반 symbol/남은 지표/경로선 및 경로선 toggle은 Category C/D 변경이다.
아래 새 ID는 2026-09-16 사용자가 승인했으며 기존 승인 이력과 ID를 소급 변경하지 않는다.

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
여기서 `남은 지점 재계산`은 승인된 기준본의 역사적 문구이며, 2026-09-16 승인으로
D-SRP-023이 FR-SRP-006/010의 해당 동작만 명시적으로 대체한다. `WGS84 네이버지도 내비게이션`도
승인된 기준본의 역사적 문구이며, 승인된 D-SRP-056이 iOS provider와 App Store fallback 부분만
Apple Maps/no-fallback 계약으로 대체하고 Android NAVER Maps dispatch와 Google Play fallback은 유지한다.

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
결과를 영구 저장·재사용하며 조사 완료 및 platform별 외부 지도 길안내를 제공한다.
앱에서 조사지를 직접 그릴 때 점/선/면을 선택하고 업로드는 단일/다중 도형을 자동 인식한다.
이번 2026-09-18 승인 확장은 원격 조사지의 원본 좌표를 유지하면서 차량 접근점 사이 도로 경로와 접근점↔조사지
도보 왕복을 별도 계산·저장·표시하고, 지도에 없는 도보 구간은 거리 하한/시간 사용 불가로 정직하게
표시하는 확장이다.

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
- D-SRP-020 (2026-09-16 승인, Category C): 대상 layer/ID/name과 조사대상 출발값은 현재
  project의 실제 layer, field, feature dropdown으로 선택한다. alias/name을 표시하고 QGIS layer ID,
  actual field name, target ID를 저장한다. 생성 프로젝트의 내부 `site` layer는 `조사지`로 보이며
  deterministic default/no-match/refresh 규칙은 D-SRP-026을 따른다.
- D-SRP-021 (2026-09-16 승인, Category D): `조사 경로 계산 대상`, `출발지`, `저장 경로 이름`
  label과 checklist 방문 안내를 추가한다. map/target 출발 control은 해당 mode에서만 보이고 기본
  출발지·경로 저장 성공은 저장 값과 실제 storage path를 함께 알린다.
- D-SRP-022 (2026-09-16 승인, Category A): 네이버지도 action은 NAVER 공식 `/navigation`과
  필수 `appname`을 QField의 `Qt.openUrlExternally`로 전달하고 거부되면 platform 설치 페이지로
  fallback한다. OS 성공 반환은 외부 app 실행·목적지 수락·안내 시작 증거가 아니다. iOS scheme
  whitelist는 generated project가 바꿀 수 없는 host capability이며 Android/iOS에서 별도 검증한다.
- D-SRP-023 (2026-09-16 승인, Category C): `남은 지점 계산`을 제거한다. 최초 계산·저장 때
  모든 leg의 거리, 시간, WGS84 geometry를 저장하고 완료/해제 뒤 남은 metric/geometry는 full
  route에서만 파생한다. 승인 시 FR-SRP-006의 남은 계산 부분과 FR-SRP-010을 supersede한다.
- D-SRP-024 (2026-09-16 승인, Category C/D): 연속 완료 prefix만 traversed로 본다. out-of-order
  완료는 symbol color/check/text에는 반영하지만 앞선 gap이 있으면 인접 leg를 완료로 추정하지 않고
  metric 차감/geometry trim을 앞당기지 않는다. uncheck는 같은 규칙으로 역산한다. mapped Boolean은
  source field, 미매핑 완료는 해당 route가 권위값이며 쓰기 실패는 표시와 저장 상태를 모두 보존한다.
- D-SRP-025 (2026-09-16 승인, Category D): route-line toggle은 line만 숨긴다. default true인
  project-scoped device-local UI preference 하나를 모든 saved route에 적용한다. project-local 설정 파일이
  프로젝트 폴더와 함께 이동하면 panel reopen, app restart와 folder move 뒤에도 유지한다.
- D-SRP-031 (2026-09-16 승인, Category D): FR-SRP-022의 `control 위 label` 배치를 승인 이력으로
  보존하되 그 배치만 supersede한다. `조사 경로 계산 대상`, `출발지`,
  `조사지 레이어`, `조사지 ID 필드`, `조사지 이름 필드`, `조사지 완료 필드(Boolean)`는 ORS 서버
  URL field와 같은 in-control floating-label pattern을 쓴다. 별도 label row나 placeholder-only label은
  쓰지 않으며, 내부 source/role/actual field name과 저장값은 바꾸지 않는다.
- D-SRP-032 (2026-09-16 승인, Category D): 선택 준비 절차와 현재 선택 수는 scope가 `선택 대상`일
  때만 보인다. scope control 바로 아래의 scope 설명 다음 줄에 두고, `전체 대상` 또는 `미조사 대상`으로
  바꾸면 빈 자리 없이 숨긴다. 이는 D-SRP-018의 안내 의미를 유지하면서 정보 계층만 명확히 한다.
- D-SRP-033 (2026-09-16 승인, Category D): `지도 중심을 출발지로 지정`은 현재 map center를
  WGS84 출발 좌표로 확정한 직후 그 위치에 `출발지`임을 색 이외로도 식별할 수 있는 임시 marker
  하나를 표시한다. marker는 지도 이동과 독립적으로 확정 좌표에 머물고 다시 지정하면 이동·교체한다.
  panel collapse/reopen과 계산 성공/실패에는 유지하되 start mode 변경, 값 clear/invalid, project close에는
  제거한다. source/route data에는 쓰지 않고 app restart에 독립 복원하지 않으며 원본 renderer를 바꾸지 않는다.
- D-SRP-034 (2026-09-16 승인, Category B): `조사대상 출발` dropdown은 새 request 없이 현재
  calculation preflight와 동일한 ordered stable-ID candidate set에서만 만든다. `선택 대상`은 현재 선택한
  유효 조사지, `전체 대상`은 전체 유효 조사지, `미조사 대상`은 effective completion이 false인 전체
  유효 조사지다. option population과 기존 선택 보존/clear를 먼저 수행하고, 그 뒤에 target mode의
  required-selection validation을 실행한다. 비어 있는 기존 선택을 먼저 검증해 population 자체를 막지 않는다.
- D-SRP-035 (2026-09-16 승인, Category A/B): 유효한 EPSG:4326 LineString 조사지 5개에서도
  실 ORS 응답을 `도로 구간 순서 또는 도형이 올바르지 않습니다.`로 거부한 현상은 conformance defect다.
  ORS GeoJSON directions의 `properties.segments[]`는 waypoint 사이 section의 distance/duration/steps이고,
  geometry waypoint index sequence는 route-level `properties.way_points[]`다. 초기 `ors-vroom` adapter는
  후자의 연속 index pair로 full LineString을 ordered leg geometry로 나누며, 문서에 없는
  `segments[].way_points`를 요구하지 않는다. Point는 원점, MultiPoint/LineString/MultiLineString/
  Polygon/MultiPolygon은 승인된 source-CRS centroid→WGS84 대표점을 사용한 뒤 source geometry family와
  무관하게 같은 VROOM order와 ORS response validator를 통과한다. provider response 결함과 client
  parsing/validation 결함은 서로 다른 actionable 오류로 알리고 마지막 정상 경로를 보존한다.
- D-SRP-036 (2026-09-17 승인, Category A/B): 성공한 계산 결과(candidate)는 계산 입력과
  계산 시점의 저장 revision에 결합한다. 저장 이름은 계산 입력이 아니므로 `저장할 경로 이름`의
  입력·수정·focus 변화가 candidate를 무효화하거나 재계산을 요구하지 않는다. 저장 직전에는
  candidate가 존재하고 base revision이 아직 같은지만 검사한다. 계산 입력 또는 snapshot revision이
  실제로 바뀐 경우에만 재계산 또는 새 결과 선택을 요구하며, 이름 오류·저장 실패에는 candidate를
  보존하여 수정 후 다시 저장할 수 있게 한다.
- D-SRP-037 (2026-09-17 승인, Category D): 경로 패널의 주요 field/selector는 현재
  `저장할 경로 이름`에서 선호된 outlined floating-label을 공통 pattern으로 쓴다. text field와
  dropdown 모두 label이 outline에 걸쳐 항상 보이고 control 종류, empty/value/focus/error 상태에
  따라 위치가 달라지지 않는다. exact user-facing labels는 `조사지`, `조사지 ID 필드`,
  `조사지 이름 필드`, `조사 완료 필드`, `계산 대상`, `출발지`, `저장할 경로 이름`이다.
  이 결정은 D-SRP-031/FR-SRP-029의 여섯 label 배치와 긴 문구만 supersede하며 stable layer ID,
  actual field name, option value와 저장 의미는 바꾸지 않는다.
- D-SRP-038 (2026-09-17 승인, Category B/D): `API URL/키 설정` section은 panel을 처음 열 때
  접혀 있고 사용자가 명시적으로 펼친다. optimizer label은 version을 UI에 고정하지 않는
  `VROOM 서버 URL`이다. QField에서 직접 입력한 key는 현재 app session의 메모리에만 있고
  `서버 설정 저장 (키 제외)` snapshot에 쓰지 않는다. 단, builder에서 위험 고지에 동의한 project는
  `.qgs` project variable에 평문 key를 포함하며 panel을 열 때 그 값을 session key로 읽는다.
  이는 session field를 settings JSON에 저장한 것이 아니고 암호화도 아니다. key control 근처에는
  `이번 세션만 사용` 또는 `프로젝트 파일의 평문 키 사용 중` 중 실제 source/persistence 상태를
  명확히 표시한다. 일반 서버 설정 저장 성공은 현재 프로젝트 scope와 실제로 쓴
  project-relative `survey-routes.a.json` 또는 `survey-routes.b.json` 경로를 표시하며 key 제외를
  재확인한다. 이 파일은 route와 non-secret settings가 함께 있는 교대 snapshot이다.
- D-SRP-039 (2026-09-17 승인, Category A/B): NAVER handoff는 구현 시점의 NAVER Cloud 공식
  `지도 앱 연동 URL Scheme` 문서가 각 host context에 규정한 형식을 그대로 사용한다. Android
  native/in-app context는 공식 `intent://...#Intent;scheme=nmap;...;package=com.nhn.android.nmap;end`
  형식을 지원하는 host에서 이를 쓰고, iOS는 필수 `appname`을 포함한 공식 `nmap://navigation`
  scheme과 documented App Store fallback을 쓴다. Android에서 intent URL을 host가 처리할 수 없으면
  공식 문서가 허용한 native `nmap://navigation` dispatch와 documented Google Play fallback을
  사용한다. 웹 fallback은 공식 문서가 해당 platform/context와 navigation action에 명시한 경우에만
  그 문서의 URL을 사용하며, 임의의 `map.naver.com` URL이나 추정 parameter를 만들지 않는다.
- D-SRP-040 (2026-09-17 승인, Category B/D): 사용자가 panel에서 완료로 바꿀 수 있는 stop은
  현재 순서상 첫 미완료 stop 하나뿐이다. 그 뒤 stop을 check하려 하면 값을 바꾸지 않고
  `다음 방문 지점부터 순서대로 완료하세요.`와 현재 다음 지점을 표시한다. 이미 완료된 stop은
  현장 기록 정정을 위해 uncheck할 수 있다. 이때 뒤의 완료값은 지우지 않되 D-SRP-024의 prefix
  계산에 따라 `순서 밖 완료`로 표시하고 earliest gap부터 남은 metric/geometry에 포함한다.
  source Boolean에서 처음부터 발견된 out-of-order true도 같은 표시를 쓰고 자동 재계산·자동 해제·
  API 호출을 하지 않는다. 이 규칙은 계산 없이도 안전하게 동작하는 현재 contiguous-prefix 구조를
  유지하면서 실수로 남은 경로를 앞당기는 UX를 막는다.
- D-SRP-041 (2026-09-17 승인, Category D): generated project의 polygon `site`/`조사지` layer는
  회색 계열이 아닌 식별 가능한 accent outline/fill을 사용한다. 기본 제안은 green `#2E7D32`
  outline과 같은 hue의 반투명 fill이며 basemap 위에서 경계를 식별할 수 있어야 한다. 조사지 feature는
  configured name field 값을 지도 label로 표시하고 흰색 buffer/halo를 둘러 배경과 겹쳐도 읽히게
  한다. 빈 name은 label을 만들지 않으며 label text는 data로 취급한다. style/label 설정은 원본
  geometry, configured field value, route completion overlay와 stored route를 바꾸지 않는다.
- D-SRP-042 (2026-09-17 승인, Category A): 실제 QField에서 `저장할 경로 이름`을 눌러도 모바일
  소프트 키보드가 열리지 않는 현상은 D-SRP-036/FR-SRP-034의 입력 가능 계약에 대한 conformance
  defect다. 이 control은 read-only 표시나 pointer-only surface가 아니라 QField가 native text input으로
  인식하는 editable control이어야 한다. 사용자가 control 본문을 누르면 caret/focus가 나타나고 OS
  소프트 키보드가 열리며, 한글·영문 입력, 선택, 삭제와 재입력이 candidate 재계산 없이 동작한다.
  외부 키보드 연결 또는 OS의 소프트 키보드 비활성화처럼 앱이 제어하지 않는 조건은 별도로 기록한다.
- D-SRP-043 (2026-09-17 승인, Category D): `저장 경로 불러오기` dropdown을 D-SRP-037의 공통
  outlined floating-label component에 포함한다. text field와 dropdown의 모든 floating label은 label
  글상자/표면색 notch의 수직 중심이 control의 top outline과 일치해 top border를 가로지르는 한
  기준선을 쓴다. label 전체가 outline 아래로 처지거나 border 위에 떠 있으면 안 되며 empty/value/
  focus/disabled/error 상태와 320 px 이상 viewport에서 그 기준선이 바뀌지 않는다. 이 결정은
  D-SRP-037의 일곱 label을 여덟 label로 확장하고 배치 정밀도를 명시할 뿐 stored option value,
  route ID, selection/load 동작은 바꾸지 않는다.
- D-SRP-044 (2026-09-17 승인, Category A/D): 실제 generated project에서 승인된 name label이
  보이지 않는 현상은 D-SRP-041/FR-SRP-039의 conformance defect다. Point/MultiPoint,
  LineString/MultiLineString, Polygon/MultiPolygon site/`조사지` layer는 geometry family에 맞는
  QGIS/QField label placement를 사용하고 feature마다 하나의 logical label을 그린다. label text는
  trim한 configured name-field 값이 non-empty면 그 값, name field가 없거나 유효하지 않거나 해당
  값이 비어 있으면 trim한 configured stable-ID-field 값, 둘 다 없거나 비어 있으면 label 없음이다.
  임의의 다른 attribute를 추측하지 않는다. 이 fallback은 지도 표시만 위한 것이며 FR-SRP-021의
  required route-name mapping validation을 충족한 것으로 간주하지 않는다. 모든 표시 label은 흰색
  buffer/halo를 사용하고 markup처럼 보이는 값도 inert text로 취급한다. multipart feature의 각 part에
  같은 text를 반복하지 않으며 원본 geometry/attribute/renderer contract와 route overlay를 바꾸지 않는다.
- D-SRP-045 (2026-09-17 승인, Category D): FieldBuild Kit wizard Step 7의 route credential은
  비기술 사용자에게 아래 exact copy와 의미를 제공한다. field/group title은 `ORS API 키 (선택)`이고,
  목적 설명은 `조사 경로를 도로망에 맞춰 계산하고 조사지 방문 순서를 정할 때 사용합니다.`다.
  미입력 설명은 `입력하지 않아도 프로젝트는 만들 수 있습니다. 다만 기본 ORS/HeiGIT 서비스로 경로를
  계산하려면 QField를 열 때마다 키를 입력해야 합니다. 키가 필요 없는 자체 서버를 사용하는 경우에는
  입력하지 않아도 됩니다.`다. 평문 포함 checkbox는 `프로젝트에 API 키를 평문으로 포함하는 데
  동의합니다`이고, 그 바로 앞 경고는 `동의하면 QField가 자동으로 사용하도록 키가 프로젝트 파일에
  암호화되지 않은 글자로 저장됩니다. 프로젝트 폴더를 열 수 있는 사람은 누구나 키를 확인하고 사용할 수
  있습니다. 동의하지 않으면 프로젝트에 키를 넣지 않으며, QField를 열 때마다 직접 입력해야 합니다.`다.
  입력값은 masked로 유지한다. desktop의 `암호화해 기억` 선택은 generated project의 평문 포함 동의와
  별개이며 둘을 같은 저장으로 설명하지 않는다. blank key 또는 non-blank key+동의 거부는 project 생성을
  막지 않고 generated project에서 key를 제외한다; non-blank key+동의만 D-SRP-017의 평문 project
  variable을 만든다.
- D-SRP-046 (2026-09-17 승인, Category A/B/D): route panel은 QField/iOS host가 light 또는 dark
  appearance인 경우 모두 하나의 internally consistent theme palette를 사용한다. host theme를 따르되
  surface와 foreground를 서로 다른 theme에서 섞지 않는다. normal/value/help/summary/action text,
  placeholder, floating label, outline, dropdown indicator, focus, selected/checked, error 및 disabled/read-only
  상태는 NFR-SRP-006의 contrast와 non-color cue를 충족한다. 이는 경로 데이터·provider·저장 형식이나
  basemap theme을 바꾸지 않고 route-panel presentation만 정합한다.
- D-SRP-047 (2026-09-17 승인, Category A/D): expanded panel의 고정 route-summary/header와 scroll
  content 사이에는 첫 `조사지` floating label의 전체 glyph, surface-colored notch 및 control top outline이
  보이는 안전 간격을 둔다. header의 painted bottom(그림자/focus ring 포함)과 label의 painted top 사이
  clear gap은 최소 8 dp이고, 따라서 첫 control top outline은 `label painted height / 2 + 8 dp` 이상 아래에
  놓인다. 현재 18 dp label box를 쓰면 최소 17 dp이며 구현은 20 dp를 권장한다. header와 label/control의
  pointer/touch hit region은 겹치지 않는다. 이 규칙은 320 px 이상 supported width, text scale 및
  empty/value/focus/error/disabled 상태에 적용하며 나머지 vertical rhythm은 변경하지 않는다.
- D-SRP-048 (2026-09-17 승인, Category A/C): D-SRP-042/FR-SRP-040의 real editable native-input
  계약을 iOS에서도 그대로 적용한다. 새 계산이 성공해 새 unsaved candidate가 생길 때
  `저장할 경로 이름`은 QField device의 그 순간 local calendar date를 Gregorian `yyyy-MM-dd`로
  formatting한 뒤 한 칸과 `조사`를 붙인 `yyyy-MM-dd 조사`로 초기화한다(예: `2026-09-17 조사`).
  timezone은 server/UTC/project timezone이 아니라 OS가 QField에 제공하는 device local timezone이며
  locale에 따라 숫자 순서나 구분자를 바꾸지 않는다. explicit `새 경로 계산`의 다음 성공은 새 candidate
  기본값으로 reset한다. 실패한 계산은 기존 candidate/name을 보존한다. 사용자의 입력·수정·삭제는
  현재 candidate에서 자동으로 덮어쓰지 않으며 collapse/reopen, theme change, refresh, save retry는
  reset trigger가 아니다. 저장 성공 뒤 현재 route에는 final trimmed saved name을 유지하고, saved route
  load는 저장된 name을 표시하며 오늘 날짜로 rename하지 않는다.
- D-SRP-049 (2026-09-18 승인, Category A/B): route transport/backend의 실패 경계는
  raw body 대신 최소 실패 레코드 `{stage, http_status, provider_code, provider_message, safe_text}`를
  반환한다. `stage`는 기존 `matrix`/`optimizer`/`directions`와 이번 승인 범위의
  `access-snap`/`walking-directions` 중 하나이고, HTTP non-2xx에서
  `http_status`를 보존한다.
  반환 본문은 JSON으로 parsing을 시도하되 표시 후보는 provider의 scalar internal
  code/message 필드로 한정한다. JSON이 아니면 안전 정제한 text만 fallback으로
  쓰고, empty이거나 HTML이면 단계와 status만 있는 일반 오류를 쓴다. 표시 text는
  Unicode control/format 문자를 공백으로 정규화하고 연속 공백을 합친 뒤 code 64자,
  message/fallback 320자, 완성 진단 512자로 잘라낸다. HTML/markup, request URL/query/body,
  `Authorization`, 알고 있는 API key/credential 값, bearer/token/key/secret 할당으로 의심되는
  내용은 부분 노출하지 않고 해당 세부정보 전체를 생략한다. 화면은
  `행렬(matrix)`/`방문 순서 최적화(optimizer)`/`도로 경로(directions)`/
  `차량 접근점(access-snap)`/`도보 경로(walking-directions)`, HTTP status,
  존재하는 안전한 provider code/message 순서의 간결한 한국어 진단만 표시한다.
  HTTP 404만으로 endpoint unavailable이나 no-result를 추정하지 않고, 반환된 provider
  code/message가 그 분류를 명시할 때만 해당 의미를 표시한다. 성공 응답 본문은
  진단에 전달·표시하지 않으며, 실패는 retry, route/settings write, candidate 폐기를
  일으키지 않고 기존 candidate와 저장 경로를 그대로 보존한다. 새 logging framework,
  dependency 또는 provider별 확장 계층은 추가하지 않는다.
- D-SRP-050 (2026-09-18 승인, Category C): 조사지 대표점은 계속 source coordinate다. provider에
  보내거나 저장·표시할 때도 `source_coordinate`로 보존하며 source feature geometry/attribute/
  renderer를 이동·수정하지 않는다. 차량용 `access_coordinate`는 별도 파생값이다. 새 계산은
  `/v2/snap/driving-car/json`에 모든 original site `source_coordinate`를 현재 계산 순서 그대로 담은
  단일 batched request를 보내고 필수 `radius`에는 `max_access_distance_m`를 그대로 쓴다. 기본값은
  2,000 m, 허용 설정 범위는 350~5,000 m다. 응답의 snapped point 또는 `null`을 input 순서에 1:1로
  대응하며 각 site에는 반환된 point 하나만 access point로 채택한다. provider의 documented batch
  한도를 계산 전 검사하고 한도를 넘으면 actionable preflight error로 중단한다. provider가 설정 반경을
  거부하거나 더 작은 값으로 제한한다는 HTTP/code/message를 반환하면 D-SRP-049의 안전한 provider
  오류를 표시하고 중단하며, radius를 줄이거나 여러 좌표를 생성·탐색하는 silent workaround를 하지
  않는다. `null`이면 해당 site name/stable ID와 설정 한도를 표시하고 전체 candidate를 만들지 않는다.
  좌표 순서를 바꾸거나 source를 access point로 덮어쓰지 않는다. 기존 route origin 동작은 유지하되
  origin은 계산 전에 이미 `driving-car` routing 가능한 위치여야 한다. 이 slice는 origin을 snap하거나
  origin walking leg를 만들지 않으며, origin routing 실패는 `지도 위치 출발` 또는 도로 위의 저장
  출발지를 사용하라는 actionable start error로 끝난다.
- D-SRP-051 (2026-09-18 승인, Category C/B): 각 site에 D-SRP-050이 반환한 단일 access point와
  original source 사이 `foot-hiking` directions를 요청해 geometry와 distance/duration을 확정한다.
  source와 access가 1 m 이하로 같으면 walking은 exact zero이며 foot request를 생략한다. provider가
  mapped foot route 없음이라고 명시하면 그 site의 반환된 단일 access point와 source 사이 geodesic을
  `straight_line_lower_bound_m`으로 저장·표시하고 walking duration은
  `null/사용 불가`, geometry는 source-access 직선이며 mode는 `unmapped_estimate`다. HTTP/network/
  timeout, malformed response 또는 서로 다른 foot 응답의 metric 불일치는 no-path로 간주하지 않고
  전체 계산을 실패시킨다. 따라서 provider 장애를 추정 fallback으로 숨기지 않는다.
  모든 방문은 access→source에서 조사→같은 access로 복귀하는 out-and-back이다. 다음 차량 구간이
  있는 stop, roundtrip return 전 stop과 open route의 마지막 stop도 동일하며, 한 방향 provider
  walking metric/geometry를 두 배/정방향+역방향으로 명시적으로 저장한다. 별도 one-way 선택은 이번
  범위가 아니다.
- D-SRP-052 (2026-09-18 승인, Category B): 새 계산의 순서는 (1) local preflight와 원본 좌표 snapshot,
  origin의 vehicle-routable 조건 확인, (2) original site 좌표 전체의 단일 batched car access snap,
  (3) 각 반환 access point의 walking directions 또는 명시적 unmapped fallback,
  (4) access coordinates만 쓰는 `driving-car` matrix, (5) 기존 VROOM
  optimization, (6) ordered access coordinates만 쓰는 `driving-car` directions, (7) 완전한 candidate
  validation이다. VROOM objective는 차량 matrix만 최적화한다. walking 방문비용은 순서에 무관하므로
  차량 cost로 가장하지 않는다. snap의 `null`은 site와 한도, 좌표/OSM coverage/한도 설정 확인 방법을
  보여주며, provider의 radius 거부/cap 또는 origin routing 실패는 D-SRP-049의 안전한 provider 내용과
  D-SRP-050의 start/radius action을 보여준다. 어느 필수 stage든 실패하면 후속 stage, 자동 retry와
  write는 없고 이전 unsaved candidate,
  saved route, active revision과 설정을 보존한다. explicit no-foot-path만 D-SRP-051 fallback으로 계속한다.
- D-SRP-053 (2026-09-18 승인, Category C): mixed route의 저장 schema는 `3`이다. route는 기존
  identity/name/revision/backend/snapshot과 함께 `vehicle_legs[]`, `visits[]`, `vehicle_totals`,
  `walking_totals`, `combined_totals`를 가진다. 각 visit은 `{layer_id, site_id, source_coordinate,
  access_coordinate, access_offset_m, walking_mode, walking_legs[2], metric_source}`를 저장하고
  walking leg는 `{direction: outbound|return, distance_m, duration_s|null, geometry}`다. mapped return
  geometry는 provider outbound geometry의 exact reverse이고 metric은 같으며, exact-zero visit은 두 leg의
  distance/duration이 0이고 geometry는 `null`이다. fallback 두 leg는 각각 같은 geodesic lower-bound와
  `null` duration 및 서로 반대인 straight LineString이다. vehicle leg의 from/to는 start 또는
  access-coordinate visit reference이고 기존 finite metric/WGS84 LineString 검증을 따른다.
  `vehicle_totals`는 exact `{distance_m,duration_s}`, `walking_totals`는
  `{mapped_distance_m,lower_bound_distance_m,duration_s|null,unavailable_duration_count}`다.
  `combined_totals`는 모든 walking leg가 mapped/exact-zero일 때만 exact `{distance_m,duration_s}`이고
  fallback이 하나라도 있으면 `null`이다. 따라서 lower-bound를 exact total에 합치거나 unknown time을
  숫자로 추정하지 않는다.
  schema 1/2는 read-time request/write/추정 없이 기존 의미로 계속 열고, explicit 새 계산·저장만 schema
  3을 만든다. schema 3을 모르는 이전 reader는 기존 future-schema 규칙대로 bytes를 보존하고 거부한다.
- D-SRP-054 (2026-09-18 승인, Category D): panel과 bottom summary는 `차량` 거리/시간과 `도보`
  거리/시간을 분리한다. 모두 provider metric이면 combined도 표시할 수 있으나 어느 값도 중복 합산하지
  않는다. fallback walking은 `직선거리 하한 · 경로/시간 사용 불가`와 affected site를 표시하고 저장 전
  `지도에 없는 도보 구간 포함` acknowledgement를 요구한다. 차량선은 기존 solid style, mapped walking은
  purple dashed line, unmapped fallback은 더 촘촘한 dotted straight line과 warning marker를 쓴다.
  adaptive contrasting casing을 두고 `차량 경로`/`도보 경로`/`지도 경로 없음` text+line-pattern legend를
  panel과 map에 제공한다. 색만으로 mode를 구분하지 않으며 light/dark basemap과 route-panel theme에서
  읽혀야 한다. completion prefix는 site 방문과 access 복귀가 끝난 뒤 complete로 보며, completed stop의
  inbound vehicle leg와 해당 walking roundtrip을 remaining totals/overlay에서 함께 제외한다.
- D-SRP-055 (2026-09-18 승인, Category B/E): explicit calculate 전 안내는 ORS에 source coordinates,
  반환된 access coordinates와 route geometry request가 전송됨을 알린다. ORS에는
  site name, source layer attributes, stable business ID나 completion을 보내지 않고 request-local integer
  index만 쓴다. VROOM에는 access coordinates와 cost matrix 및 request-local index만 보낸다. request/
  response body는 로그·오류·project settings에 남기지 않고, 저장에는 D-SRP-053의 최종
  source/access/route geometry만 둔다. D-SRP-049 redaction은 모든 새 stage에 적용한다. 계산·fallback
  preview·legend/toggle은 source feature, completion field, route/settings storage를 쓰지 않으며,
  사용자의 explicit save만 atomic schema-3 route commit을 수행한다.
- D-SRP-056 (2026-09-18 승인, Category C): 외부 길안내 action은 platform-neutral label
  `다음 지점 지도 안내`를 사용한다. iOS에서는 NAVER custom scheme 대신 Apple의 공식 HTTPS unified
  Maps URL `https://maps.apple.com/directions?destination=<latitude>,<longitude>&mode=driving`을
  `Qt.openUrlExternally`에 정확히 한 번 전달한다. `destination`은 현재 next stop의 저장된 WGS84
  representative coordinate이고 순서는 latitude,longitude다. Apple의 `/directions` 계약에 목적지
  표시 이름 parameter가 문서화되어 있지 않으므로 현재 URL에는 이름을 넣지 않는다. 향후 공식 문서가
  coordinate와 함께 쓰는 destination-name parameter를 명시하더라도 별도 승인 전에는 추정 parameter를
  추가하지 않는다. Android는 D-SRP-039의 NAVER package-bound `intent://` destination dispatch를
  포함한 기존 dispatch와 Google Play fallback을 D-SRP-039, FR-SRP-037 및 AC-SRP-039 그대로 유지한다.
  iOS는 Apple Maps HTTPS primary launcher가 false를 반환하거나 exception이 발생해도 NAVER `nmap`,
  App Store 또는 web page를 추가 실행하지 않고 설치·지원 환경 확인 안내로 끝낸다. 이 결정은
  D-SRP-022/D-SRP-039, FR-SRP-025/037 및 AC-SRP-025/039의 iOS NAVER provider와 iOS App Store fallback
  부분만 supersede한다. Android NAVER destination/encoding/dispatch/fallback 계약과 OS request만 확인
  가능하다는 기존 증거 경계는 변경하지 않는다.
- D-SRP-057 (2026-09-18 승인, Category B): schema 3의 모든 route와 모든 visit은 active 여부와
  관계없이 D-SRP-053의 필수 구조를 검증한다. 각 visit의 `layer_id`와 `site_id`는 non-empty string이며
  해당 route stop의 configured stable layer/feature identity와 정확히 1:1 대응하고,
  `metric_source`는 non-empty string이다. 허용 조합은 `walking_mode=mapped`와
  `metric_source=ors-foot-hiking`, `walking_mode=exact_zero`와 `metric_source=exact_zero`,
  `walking_mode=unmapped_estimate`와 `metric_source=straight_line_lower_bound_m`뿐이다. 각 조합의
  walking leg metric/geometry/null 의미는 D-SRP-051/053을 그대로 따른다. 필드 누락, unknown mode/source,
  조합 불일치 또는 stop identity 불일치가 하나라도 있으면 reader는 schema-3 문서 전체를 repair,
  request 또는 write 없이 거부하고 기존 bytes와 last-good route를 보존한다. schema 1/2에는 이 검증을
  소급 적용하지 않는다.
- D-SRP-058 (2026-09-19 승인, Category B): 경로가 없는 fresh/default in-memory document와
  settings-only save는 mixed route를 생성하지 않으며 schema 3으로 승격하지 않는다. fresh/default는
  disk write 없이 schema 2 의미로 시작하고, 사용자가 일반 설정만 명시적으로 저장하면 schema 2를 쓴다.
  schema 1/2 read는 계속 write-free이며, schema 1에서 settings-only write가 필요한 경우에도 최대 schema
  2까지만 승격한다. top-level schema 3 전환은 validated mixed candidate의 explicit save에서만 일어난다.
  이 전환 때 `routes[]`의 새 mixed route는 `route_schema: 3`과 D-SRP-053/057 구조를 가지며, 선택한 동일
  identity의 legacy route만 대체한다. 관련 없는 schema-1/2 route는 삭제하거나 mixed provenance를
  추정하지 않고 기존 route fields를 그대로 둔 채 원래 top-level schema를 값으로 한
  `route_schema: 1|2`를 붙여 같은 schema-3 document 안의 read-only legacy variant로 보존한다.
  `active_id`는 mixed와 legacy variant의 합집합에서 유일한 `route_id`를 가리킨다. schema-3 reader는
  `route_schema: 3` route에 D-SRP-057 전체를 적용하고 `route_schema: 1|2`에는 해당 legacy schema의
  기존 validator/표시 제한만 적용한다. 이미 승인된 untagged homogeneous schema-3 route는 호환성을
  위해 `route_schema: 3`으로 읽되 read-time write는 하지 않으며, 이후 정상 write는 discriminator를
  명시한다. unknown discriminator, legacy marker와 mixed-only fields의 모순, duplicate identity 또는
  어느 variant의 validation 실패도 문서 전체를 repair/write 없이 거부하고 bytes와 last-good을 보존한다.
- D-SRP-059 (2026-09-19 승인, Category B): `show_route_line`은 D-SRP-025/030의 persistent
  project-scoped device-local preference가 우선한다. 사용자의 toggle은 route object, route revision,
  source/completion data를 바꾸지 않고 provider request도 만들지 않지만, 값이 실제로 바뀌면 오직
  `settings.show_route_line`을 기존 atomic settings snapshot 경로에 저장할 수 있고 저장해야 한다.
  따라서 D-SRP-055와 AC-SRP-054의 toggle write 0회는 route/source/completion write 0회로 좁혀 읽으며
  settings write 금지에는 적용하지 않는다. 저장 성공 뒤 panel reopen/app restart/settings를 포함한
  folder move에서 같은 값이 복구된다. 저장 실패는 현재 저장된 preference와 route/revision을 보존하고
  실패 feedback을 제공하며 성공으로 보고하지 않는다. preview와 legend를 보는 것만으로는 여전히 어떤
  write도 만들지 않는다.
- D-SRP-060 (2026-09-21 승인, Category B): D-SRP-051의 `foot-hiking` request 좌표는 immutable
  `access_coordinate`와 `source_coordinate`지만, ORS directions geometry의 시작·끝은 해당 profile의
  routing graph에 snap된 provider endpoint일 수 있다. mapped 응답은 GeoJSON feature 하나, 두 개 이상의
  finite WGS84 coordinate를 가진 LineString, finite non-negative summary distance/duration, 요청한 두
  waypoint에 대응하는 segment 하나, 그리고 route-level `properties.way_points`의 정확히 두 strictly
  increasing integer index가 각각 geometry의 첫 index `0`과 마지막 index를 가리킬 때 구조적으로
  유효하다. summary와 segment metric은 D-SRP-028의 distance/duration tolerance 안에서 일치해야 한다.
  이 조건을 만족하면 geometry 첫·끝과 requested access/source 사이 거리는 acceptance 조건이 아니며,
  provider distance를 requested access-source geodesic의 lower bound로 검사하지 않는다. provider의
  distance/duration/geometry는 `ors-foot-hiking`이 반환한 graph 구간 그대로 저장하고 return geometry만
  exact reverse한다. requested coordinate를 geometry endpoint로 바꾸거나 geometry를 requested marker까지
  직선으로 연장하거나 gap 거리/시간을 provider metric에 더하지 않는다. 기존 schema 3의
  `source_coordinate`, `access_coordinate`, geometry endpoint와 `metric_source=ors-foot-hiking`만으로
  provenance가 분리되므로 새 필드, mode, metric source 또는 schema version은 추가하지 않는다.
  UI/map/screen reader는 source/access marker를 requested coordinate에 그대로 표시하고 mapped dashed
  line은 provider graph geometry만 표시한다. mapped walking distance/time 및 이를 더한 combined total은
  `ORS 경로 기준`이며 requested marker와 provider endpoint 사이 gap은 포함하지 않는다고 계산 결과,
  저장 경로 detail 및 legend/accessibility text에서 알린다. 이를 access→source 전체의 연속 경로 또는
  완전한 현장 이동 거리/시간이라고 표현하지 않는다. explicit no-path와 exact-zero 의미는
  D-SRP-051/053 그대로이며, malformed structure/way_points/metric mismatch는 여전히 전체 계산 실패다.
- D-SRP-061 (2026-09-21 승인, Category B): D-SRP-060의 정상 mapped 구조와 별도로, walking directions가
  feature 하나, `geometry.type=LineString`, 정확히 한 개의 finite WGS84 coordinate, segment 정확히 하나,
  route-level `way_points=[0,0]`, summary와 segment의 distance/duration이 모두 숫자 `0`인 응답을 반환하면
  adapter는 이를 저장 가능한 mapped geometry나 `exact_zero`로 만들지 않고 해당 visit의 명시적
  `unmapped_estimate/straight_line_lower_bound_m`으로 분류한다. 요청한 access와 source 사이 geodesic
  왕복을 직선거리 하한으로 사용하고 duration과 combined total은 기존 D-SRP-051 fallback처럼 `null`,
  geometry는 요청 좌표 사이 dotted 직선이며 저장 전 확인을 요구한다. 한 점을 복제해 2점 LineString을
  만들거나 mapped 0 m/0 s, synthetic connector 또는 endpoint-gap metric으로 저장하지 않는다. 한 점인데
  metric이 non-zero/non-finite/missing이거나 segment/way-points/feature 수가 다르거나 summary와 segment가
  일치하지 않으면 provider-response failure로 중단하고 fallback, 후속 vehicle request와 write는 0회이며
  last-good candidate/saved route를 보존한다.
- D-SRP-062 (2026-09-22 승인, Category A/B): Matrix response의 `snapped_distance`는 optional
  provider diagnostic이다. 이 tolerance는 vehicle matrix의 `sources[]` 각 항목과 origin-validation
  1×1 matrix의 `sources[0]` 및 `destinations[0]`에 동일하게 적용한다. object/array의 기존 cardinality,
  origin resolved `location`, duration 및 vehicle cost-matrix 검증은 그대로 유지한다. 해당 object에
  `snapped_distance` property가 없으면 이격거리 정보가 없는 것으로 받아들이고 그 사실만으로 계산을
  거부하거나 `0`으로 대체하지 않는다. property가 존재하면 finite non-negative number여야 하며,
  string, `null`, `NaN`/infinity 또는 음수는 malformed provider response다. vehicle `sources[]`의 present
  값이 `max_road_offset_m`을 초과하면 기존과 같이 전체 계산 실패다. origin-validation은 present 값을
  유효성 검사하되 이 값으로 출발 좌표를 이동하거나 새 offset threshold를 만들지 않는다.
- D-SRP-063 (2026-09-22 승인, Category A): 이 독립 FieldBuild Kit desktop app의 remembered
  VWorld/Pl@ntNet/route key는 display name과 별개인 기존 compatibility namespace 하나에 함께 둔다.
  canonical file은 macOS `~/Library/Application Support/FieldBuild Standalone/credentials.enc`, Windows
  `%APPDATA%\FieldBuild Standalone\credentials.enc`다. 정상 runtime은 display-name 폴더 또는 과거/다른
  application의 `FieldBuild Kit`/`QField Project Builder` 저장소를 대체 후보로 탐색, 읽기, import, merge,
  copy, move 또는 delete하지 않는다. 기존 canonical store는 현재 password와 remembered keys를 migration
  없이 계속 사용한다. `FIELDBUILD_STANDALONE_APP_DATA_DIR`은 격리 test/diagnostic override일 뿐 두 번째
  production store나 자동 migration source가 아니다. 이는 `docs/independence.md`의 현재 runtime authority가
  상속된 `specs/qfield-project-builder.md`의 역사적 rename/migration 문구보다 우선한다는 적용 기록이다.
- D-SRP-064 (2026-09-22 승인, Category C/D): 같은 ID로 작성했던 이전 DRAFT acknowledgement 제안을
  대체한다. D-SRP-054/061, FR-SRP-050/058 및 AC-SRP-051/053/060에서 fallback 저장 전에
  acknowledgement를 요구하고 미확인 상태의 저장을 막던 부분만 supersede한다. D-SRP-060,
  FR-SRP-057, NFR-SRP-009 및 AC-SRP-059의 endpoint-gap·raw provenance 표시 위치는 아래의 단일
  disclosure로 좁혀 읽는다. UI에서
  `지도에 없는 도보 구간 포함` checkbox와 그 대체 checkbox를 모두 제거하고, fallback의 존재는 선택
  항목이 아닌 계산 결과로 취급한다. `walking_mode=unmapped_estimate` visit이 하나 이상인 candidate와
  saved route에는 simple vehicle/walking distance·time totals와 함께 exact visible notice
  `실제 도로 경로를 못 찾은 구간을 직선거리 추정치로 포함하였습니다.`를 접히지 않은 기본 결과 영역에
  정확히 한 번 표시한다. 이 notice는 숨기거나 확인할 수 있는 control이 아니며, fallback provenance,
  `null` duration, dotted geometry 및 warning marker는 기존 승인 계약대로 유지한다.

  결과 영역은 exact label `상세 정보`인 disclosure를 제공하고 최초 candidate 표시와 saved-route load에서
  기본으로 접는다. raw `walking_mode`/`metric_source`, access/source coordinate, provider/source 구분,
  affected visit별 name/ID·mode·metric source·시간 사용 불가 사유를 포함한 진단과 endpoint-gap detail은
  이 disclosure 안에만 둔다. mapped visit이 하나 이상이고 endpoint gap 의미가 적용되면 exact
  `ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함`을 route-level 설명으로 disclosure 안에 정확히
  한 번만 표시하며 visit card, totals, legend 또는 disclosure의 다른 행에 반복하지 않는다. disclosure의
  펼침/접힘은 표시만 바꾸며 candidate, 저장 payload, route/settings/source data 또는 save enablement를
  바꾸거나 provider request를 만들지 않는다.
- D-SRP-065 (2026-09-22 승인, Category A/D): `계산 결과 저장` button의 disabled state는
  button과 같은 viewport에 항상 보이는 한 줄 이유를 제공한다. 우선순위는 (1) candidate 없음:
  `저장할 수 없음: 먼저 새 경로를 계산하세요.`, (2) mapping invalid: `저장할 수 없음: ` 뒤에 현재
  mapping validation 문구다. fallback 유무, D-SRP-064 notice의 표시 또는 `상세 정보`의 펼침/접힘은
  저장 활성화 조건이 아니다. 다른 기존 validation 조건이 충족되면 fallback이 있어도 button이
  활성화되고 별도 확인 없이 저장을 시도할 수 있다. 활성화된 button을 누른 뒤 controller가 success,
  false, validation exception, storage write/readback failure 또는 revision conflict 중 어느 결과를
  반환하더라도 최종 success/error message를
  같은 status element에 설정하고 그 element 전체를 현재 scroll viewport 안으로 가져온다. success만
  scroll하는 비대칭은 허용하지 않는다. message는 screen-reader status로 한 번 announce하며 실패를
  성공으로 표현하거나 기존 candidate/last-good route를 지우지 않는다.
- D-SRP-066 (2026-09-22 승인, Category D/E): `qfield_routes/` runtime은 FieldBuild Kit가 프로젝트를
  생성할 때 그 output project folder에 복사되는 project-local asset이다. 따라서 source 수정, desktop
  app rebuild 또는 reinstall은 이미 생성되어 QField로 전달된 프로젝트 폴더를 자동 수정하지 않는다.
  이 slice의 동작은 이를 포함한 FieldBuild Kit로 새 output에 생성한 프로젝트부터 적용한다. 기존
  생성 프로젝트에 적용하려면 원본 입력과 사용자 수집 데이터를 보존하는 별도 승인된 refresh/migration
  절차가 있거나, 사용자가 안전한 새 output으로 재생성한 뒤 필요한 데이터를 명시적으로 이전해야 한다.
  현재 범위는 in-place updater를 새로 만들거나 기존 project folder를 묵시적으로 덮어쓰지 않는다.
  route 기능이 포함된 project build의 완료 summary/help는 exact disclosure `경로 패널 코드는 생성된
  프로젝트에 포함됩니다. FieldBuild Kit만 업데이트해도 기존 생성 프로젝트는 자동으로 바뀌지 않습니다.`를
  제공한다.
- D-SRP-067 (2026-09-22 승인, Category B/A): D-SRP-065의 disabled 우선순위는 save
  outcome을 포함한 모든 상태 갱신에 즉시 적용한다. 성공적 저장이 candidate를 clear하면
  `candidate 없음`이 다른 규칙에 앞서 save button을 disable하고 exact reason `저장할 수 없음:
  먼저 새 경로를 계산하세요.`를 같이 표시한다. focus 보존을 위한 enabled-state 예외,
  `saveFocusRetained` 또는 그와 동등한 별도 상태를 두지 않는다. 저장 시도 직전 save button에
  focus가 있었더라도 disable에 따라 플랫폼이 `activeFocus`를 clear하는 것은 허용하며,
  앱은 그 focus를 disabled button에 강제로 복구하거나 경로 이름·disclosure·다른 control로
  옮기지 않는다. AC-SRP-064/NFR-SRP-011의 focus 보존은 이 application-initiated focus
  transfer 및 다른 editable/control state 변경이 없음을 뜻하며, disabled save button의
  `activeFocus` 유지를 뜻하지 않는다. route name text와 disclosure 펼침/접힘 상태는
  outcome과 관계없이 보존한다. AC-SRP-064의 status가 save control `위쪽`에 있다는 fixture
  표현은 status를 시도 전 viewport 밖에 두는 조건으로만 읽고 semantic 배치 근거로 사용하지
  않는다. 시각 배치, keyboard traversal과 screen-reader reading order는 NFR-SRP-012의 exact
  순서를 같이 따른다. D-SRP-064의 승인된 presentation supersession에 따라 AC-SRP-053/059의
  데이터·geometry·provenance·accessibility 의미는 유지하되, 삭제된 기본/legend/saved-detail
  object나 endpoint-gap line 3개를 현재 표시 object로 요구하지 않고 `상세 정보` 내
  route-level exact line 1개만 요구한다.

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
  **2026-09-16 승인 supersession:** D-SRP-023/FR-SRP-026 승인으로 `남은 지점 계산` 버튼과
  그 API 호출만 폐기하며, 명시적인 새 전체 경로 계산에서만 API를 호출하는 나머지 규칙은 유지한다.
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
  **2026-09-16 승인 supersession:** D-SRP-023/FR-SRP-026 승인으로 이 요구사항 전체를 대체한다.
  완료/해제에 따른 남은 값은 저장된 immutable full-route leg에서만 파생하며 API를 호출하지 않는다.
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

### 3.1 2026-09-16 승인 기능 개정

- FR-SRP-021: target-layer dropdown은 현재 project의 지원 vector layer를 alias/display name으로
  표시하고 stable QGIS layer ID를 저장한다. 생성 프로젝트의 내부 `site` layer는 `조사지`로 표시하고
  유효한 기존 선택이 없을 때 기본 선택한다. ID/name dropdown은 선택 layer의 actual field name을
  표시·저장한다. 유효한 수동 선택 보존, provider-order `_id`/`_name` default, layer-change refresh와
  no-match 처리는 D-SRP-026을 따른다.
- FR-SRP-022: scope/start 위 label은 `조사 경로 계산 대상`, `출발지`다. 지도 중심 지정은
  `지도 위치 출발`, target dropdown은 `조사대상 출발`에서만 보인다. target은 current effective
  target의 `이름 · ID`를 표시하고 실제 ID를 값으로 쓰며 mapping/layer 변경으로 사라지면 clear한다.
- FR-SRP-023: 기본 출발지 저장 성공은 WGS84 `경도, 위도` 또는 CRS가 명시된 project-visible 좌표와
  실제로 commit된 project-local settings 파일명/상대 경로를 표시한다. 경로 저장 성공은 최종 route
  name과 사용자가 프로젝트 폴더에서 접근할 수 있는 실제 route storage 파일명/상대 경로를 표시한다.
  실패 시 성공 문구를 보이지 않고 key, Authorization 값, key-bearing URL/query를 포함하지 않는다.
- FR-SRP-024: checklist 위에 `방문 순서대로 이동하고, 조사를 마친 지점을 체크하세요.`를 두고
  saved-route dropdown 위에 `저장 경로 이름`을 둔다. route name을 표시하고 route ID를 값으로 쓴다.
- FR-SRP-025: next-stop action은
  `nmap://navigation?dlat=<lat>&dlng=<lng>&dname=<encoded-name>&appname=<caller-id>`를 쓴다.
  모든 query 값은 URL-encode하며 `appname`은 필수다. caller-id는 runtime package/bundle ID,
  표준 QField fallback은 `ch.opengis.qfield`다. QField는 `Qt.openUrlExternally`로 primary URL을 연다.
  Android/iOS primary dispatch가 false면 NAVER Android package `com.nhn.android.nmap` 또는 iOS App
  Store ID `311867728`의 platform install page를 한 번 연다. true이면 fallback 없이 OS가 요청을
  수락했다는 사실만 알리고 앱 실행·목적지 수락·안내 시작을 단정하지 않는다. primary와 fallback이
  모두 거부되거나 비-mobile이면 설치/지원 기기 확인이 가능한 오류를 보인다.
- FR-SRP-026: `남은 지점 계산` button은 없다. 최초 계산 저장에는 start→stops와 open/roundtrip
  종단까지 모든 leg의 finite non-negative distance/time과 WGS84 LineString을 immutable full-route로
  저장해야 한다. 누락·순서 불일치·invalid 값은 candidate를 저장하지 않고 기존 route를 보존한다.
  완료/해제/표시 toggle/load는 full-route leg나 합계/geometry를 변경하지 않는다.
- FR-SRP-027: stop check 성공 즉시 해당 site symbol을 미완료 색에서 완료 색으로 바꾸고 check/text
  상태도 함께 표시한다. D-SRP-029의 완료 prefix leg 거리/시간/geometry를 remaining display에서 뺀다.
  out-of-order, uncheck, mapped Boolean, route-local completion, open/roundtrip, restart/recovery/offline/
  folder move는 같은 파생 결과를 만든다. full route는 보존하며 request 0회다.
- FR-SRP-028: 거리는 km 소수점 2자리, 시간은 seconds를 올림한 `X시간 YY분`이다. bottom bar는
  `경로명 · 완료수/전체수 · 남은 0.00 km · X시간 YY분`, no-route는
  `조사 경로 · 0/0 · 남은 0.00 km · 0시간 00분`이다. zero-hour는 `YY분`으로 줄여도 된다.
  펼친 panel에 default on인 `경로선 표시` toggle을 둔다. toggle은 API를 호출하거나 저장 route
  geometry를 변경하지 않고 overlay만 숨기며 D-SRP-030의 preference로 복구한다.

### 3.2 2026-09-16 승인 경로 패널 UX·대상 범위·응답 검증 정합

- FR-SRP-029 (2026-09-16 승인): `조사 경로 계산 대상`, `출발지`, `조사지 레이어`, `조사지 ID 필드`,
  `조사지 이름 필드`, `조사지 완료 필드(Boolean)`의 이름은 각 selector의 control chrome 안에서
  ORS 서버 URL field와 같은 방식으로 떠 있는 작은 label로 표시한다. 값, focus, empty 상태에서도
  label을 계속 읽을 수 있고 option text·validation text와 겹치지 않아야 한다. 이 여섯 label을 위한
  별도 row를 두지 않으며 placeholder를 유일한 accessible name으로 쓰지 않는다. 내부 layer role/source
  `site`, stable layer ID와 actual field name 저장 계약은 그대로 유지하고 모든 사용자 노출 명칭은
  `조사지`를 쓴다. FR-SRP-022의 `scope/start 위 label` 배치만 supersede한다.
- FR-SRP-030 (2026-09-16 승인): start mode가 `지도 위치 출발`일 때 `지도 중심을 출발지로 지정`을 누르면
  활성 map center를 project CRS에서 WGS84로 변환하여 start 값으로 확정하고, 성공과 동시에 정확히 그
  위치에 high-contrast `출발지` 임시 marker 하나를 표시한다. map pan/zoom 뒤 marker는 선택 좌표에
  고정되며 재지정은 기존 marker를 새 좌표로 이동·교체하고 중복 marker를 만들지 않는다. panel
  collapse/reopen과 계산 성공/실패에는 유지한다. start mode 변경, start clear/invalid 또는 project
  close에는 즉시 제거하고 source feature, 원본 renderer, saved route geometry에는 쓰지 않으며 app
  restart에 독립적으로 복원하지 않는다. 좌표 변환 실패는 기존 유효 start/marker를 보존하고 원인을 알린다.
- FR-SRP-031 (2026-09-16 승인): `조사대상 출발` dropdown은 계산 직전 preflight가 현재 scope에 대해 반환할
  ordered candidate와 exact stable-ID set이 같아야 한다. `선택 대상`은 현재 QField에서 선택한 유효
  조사지, `전체 대상`은 선택 여부와 무관한 전체 유효 조사지, `미조사 대상`은 전체 유효 조사지 중
  effective completion이 false인 항목만 포함한다. option은 조사지 이름을 먼저 표시하고 stable ID를
  `이름 · ID`로 함께 보여 같은 이름도 구분하며 실제 값은 ID다. layer/mapping/scope/current selection/
  completion 변경 때 API 없이 option을 먼저 갱신하고, 기존 ID가 새 set에 있으면 보존하며 없으면
  clear한 뒤 target mode의 필수 선택 오류를 표시한다. 빈 target을 먼저 검증하여 option population을
  중단하면 안 된다. invalid feature의 처리와 계산 차단은 기존 ID/CRS/geometry/completion preflight와 같다.
- FR-SRP-032 (2026-09-16 승인): scope selector의 공통 설명 바로 아래에
  `조사지 레이어를 열고 피처 선택/체크 도구로 계산할 조사지를 선택한 뒤 이 패널로 돌아오세요. 현재 선택한 조사지: N개`
  를 표시하되 scope가 `선택 대상`일 때만 보인다. `N`은 현재 인식한 선택 수이며 0/1/N 계산 차단·목록·
  request 의미는 FR-SRP-002를 그대로 따른다. `전체 대상`과 `미조사 대상`에서는 이 안내와 count를
  모두 숨기고 빈 layout row를 남기지 않는다.
- FR-SRP-033 (2026-09-16 승인): 여섯 source geometry type은 FR-SRP-017의 대표점으로 정규화한 뒤 같은 provider
  response 계약을 쓴다. Point는 원래 점, MultiPoint/LineString/MultiLineString/Polygon/
  MultiPolygon은 source CRS centroid를 WGS84로 변환한다. VROOM job order는 요청 stable ID의 정확한
  1회 permutation이어야 하고 missing/duplicate/unknown/unassigned ID는 provider-order defect다.
  ORS GeoJSON directions는 route-level `feature.properties.way_points`의 strictly increasing integer
  index sequence와 full WGS84 `feature.geometry` LineString을 사용한다. 각 ordered leg `i`는
  `way_points[i]..way_points[i+1]` 좌표 slice와 같은 위치의 `properties.segments[i]` distance/duration으로
  만든다. open/roundtrip leg 수·끝 index, finite coordinate/metric, LineString과 D-SRP-028 total tolerance가
  유효하면 source가 점·선·면인지와 관계없이 결과를 받아야 한다. ORS가 문서화하지 않은
  `segments[].way_points`를 요구하거나 road geometry가 원본 조사지 geometry type/vertex/containment와
  다르다는 이유로 거부하지 않는다. snapping에 따른 대표점과 road endpoint 차이는 승인된 이격거리
  규칙으로만 판정한다.

  malformed/missing provider order·waypoint index·segment·geometry·metric은 대상/구간 번호와
  missing/duplicate/invalid 원인을 밝히는 provider-response 오류로 거부하고 기존 경로를 보존한다.
  provider contract를 충족한 응답의 local parsing/mapping/validation 실패는 `앱이 경로 응답을 처리하지
  못했습니다` 계열의 client-processing 오류로 구분하여 처리 단계와 재시도 안내를 제공하고 기존 경로를
  보존한다. 유효한 응답에 통합 문구 `도로 구간 순서 또는 도형이 올바르지 않습니다.`만 표시해서는 안
  되며 어떤 오류에도 key, Authorization, key-bearing URL/query 또는 원시 secret-bearing payload를 넣지 않는다.

### 3.3 2026-09-17 승인 경로 패널 후속 정합

- FR-SRP-034 (2026-09-17 승인): 새 경로 계산이 성공하면 결과와 그 base revision을 저장 가능한 candidate로
  유지한다. 이후 `저장할 경로 이름`을 입력하거나 바꾸는 동작은 calculation input change가 아니며
  API request, candidate 폐기 또는 재계산 요구를 만들지 않는다. 같은 base revision에서 non-empty
  trim name으로 `계산 결과 저장`을 누르면 즉시 그 이름으로 저장한다. 빈 이름, 저장 I/O 실패 또는
  recoverable validation 오류는 candidate를 보존하고 수정·재시도를 허용한다. 실제 계산 입력이나
  snapshot revision이 바뀐 경우에는 어떤 값이 바뀌었는지 알리는 stale-result feedback과 함께 저장을
  막으며 기존 저장 경로와 candidate payload를 보존한다.
- FR-SRP-035 (2026-09-17 승인): `조사지`, `조사지 ID 필드`, `조사지 이름 필드`, `조사 완료 필드`,
  `계산 대상`, `출발지`, `저장할 경로 이름` control은 D-SRP-037의 동일한 outlined floating-label
  component를 사용한다. dropdown의 indicator와 option text에도 label notch, 내부 여백, focus/error
  outline이 충돌하지 않아야 한다. label은 항상 보이는 accessible name이며 placeholder로 대체하지
  않는다. `조사 완료 필드`의 Boolean/blank 의미는 별도 help text가 설명한다.
- FR-SRP-036 (2026-09-17 승인): `API URL/키 설정` disclosure는 panel initial open에서 접혀 있고 사용자가
  명시적으로 펼치거나 다시 접을 수 있다. 펼치기 자체는 request와 저장을 하지 않는다. 내부에는
  `ORS 서버 URL`, `VROOM 서버 URL`, backend/profile, masked API key, timeout, road offset, objective와
  `서버 설정 저장 (키 제외)`를 둔다. key source/persistence 상태를 D-SRP-038 문구로 표시하고 manual
  key는 app session 종료 때 폐기한다. save action은 key/objective를 제외한 현재 non-secret 설정을
  route와 같은 project-local two-slot snapshot에 commit하고, 성공 때 현재 프로젝트 scope,
  실제 상대 경로 `survey-routes.a.json` 또는 `survey-routes.b.json`, `키 제외`를 한 feedback에 표시한다.
  실패 때 success 문구를 보이지 않고 기존 정상 snapshot과 입력 중 key를 보존한다.
- FR-SRP-037 (2026-09-17 승인): 다음 지점 NAVER action은 runtime platform/context를 판별해 D-SRP-039의
  공식 Android 또는 iOS dispatch를 만든다. 목적지 WGS84 latitude/longitude, name과 host를 식별하는
  필수 `appname`을 official navigation parameter로 URL-encode한다. Android intent를 지원하는 host는
  official package-bound intent form, iOS는 official `nmap://navigation` form을 우선한다. primary
  dispatch를 처리하지 못하면 해당 platform 공식 install fallback을 한 번만 실행한다. navigation용
  web fallback은 NAVER 공식 문서가 그 platform/context에서 지원하는 URL을 명시한 경우에만 제공한다.
  모든 fallback이 실패하면 설치·지원 환경을 확인할 actionable error를 보이며, OS dispatch 성공을
  앱 실행·목적지 수락·안내 시작으로 보고하지 않는다.
- FR-SRP-038 (2026-09-17 승인): active saved route checklist에서 check 가능 상태는 순번이 가장 빠른 미완료
  stop 하나뿐이다. 뒤 stop은 disabled 상태와 `순서대로 완료` 이유를 accessible text로 제공하고,
  사용자가 시도할 수 있는 surface에서는 값을 쓰지 않은 채 다음 stop 이름/순번을 feedback으로 보인다.
  완료 stop은 정정을 위해 uncheck 가능하다. uncheck 또는 외부 Boolean field 갱신으로 gap 뒤에
  completed stop이 남으면 해당 row를 `순서 밖 완료`로 표시하고 D-SRP-024의 contiguous-prefix
  remaining 값에 포함한다. gap을 닫으면 기존 true 값이 prefix에 들어오며 request/recalculation 없이
  metric/geometry가 갱신된다. mapped write 실패는 기존 check/source/overlay/metric을 모두 보존한다.
- FR-SRP-039 (2026-09-17 승인): generated project의 polygon `조사지` layer는 D-SRP-041의 non-gray accent
  outline과 translucent fill을 저장하여 light/dark basemap에서 회색 경계로 보이지 않게 한다.
  point/line/polygon 조사지에는 configured name field 기반 label을 표시하고 흰색 buffer/halo로
  map background와 feature fill에서 분리한다. empty/null name은 label 없음으로 처리하고 field value를
  실행 가능한 markup으로 해석하지 않는다. label과 base symbology는 completion overlay, route line,
  start marker와 시각적으로 구분되며 원본 geometry/attribute를 수정하지 않는다.

### 3.4 2026-09-17 승인 QField 실기 결함·wizard 설명 정합

- FR-SRP-040 (2026-09-17 승인): QField route panel의 `저장할 경로 이름`은 focusable/editable text input이어야
  한다. touch로 본문을 누르면 caret와 focus가 보이고 target mobile OS의 soft keyboard가 열려야 하며,
  입력·수정·삭제한 최종 text는 FR-SRP-034의 trim/save 계약에 그대로 전달되어야 한다. focus/input은
  route candidate, base revision 또는 routing API request를 바꾸지 않는다.
- FR-SRP-041 (2026-09-17 승인): `조사지`, `조사지 ID 필드`, `조사지 이름 필드`, `조사 완료 필드`, `계산 대상`,
  `출발지`, `저장할 경로 이름`, `저장 경로 불러오기` 여덟 control은 D-SRP-043의 동일한 outlined
  floating-label component와 top-outline 중심선을 사용한다. dropdown indicator, selected route text,
  focus/error state와 label이 겹치지 않고 accessible name은 placeholder에만 의존하지 않는다.
- FR-SRP-042 (2026-09-17 승인): generated point/multipoint, line/multiline, polygon/multipolygon `조사지` layer는
  D-SRP-044의 name→stable-ID→no-label fallback expression, geometry-family별 placement,
  one-label-per-feature 및 흰색 buffer/halo를 project style에 저장한다. 생성물을 다른 기기로 옮기거나
  다시 열어도 같은 style contract를 유지한다.
- FR-SRP-043 (2026-09-17 승인): FieldBuild Kit wizard Step 7은 D-SRP-045의 exact purpose, blank-key behavior,
  plaintext warning과 consent copy를 masked route-key input 옆에 읽기 순서대로 표시한다. key 없이
  계속하기, key 입력 후 consent 거부, consent 후 생성, desktop-only encrypted remember의 네 상태를
  구분하고, 사용자가 consent하지 않은 key를 generated `.qgs`, 일반 설정, 로그, 오류 또는 summary에
  포함하지 않는다.

### 3.5 2026-09-17 iOS 후속 관찰 정합 (승인)

- FR-SRP-044 (2026-09-17 승인): route panel은 D-SRP-046/NFR-SRP-006의 theme-aware palette를 summary/header,
  scroll surface, text/help/labels, outlined text fields/dropdowns, checkbox, buttons, status/error 및 disabled
  states에 일관되게 적용한다. system light↔dark 변경 뒤에도 현재 값, focus, candidate, route 및 scroll
  position을 잃지 않고 routing request나 persistence write를 만들지 않는다.
- FR-SRP-045 (2026-09-17 승인): expanded panel의 첫 `조사지` outlined control은 D-SRP-047의 top safe spacing과
  disjoint hit regions을 지켜 floating label/notch/top outline이 header에 가려지거나 header tap으로
  처리되지 않게 한다.
- FR-SRP-046 (2026-09-17 승인): `저장할 경로 이름`은 승인된 FR-SRP-040의 iOS native edit contract를 유지하고,
  새 successful candidate마다 D-SRP-048의 exact local-date default를 제공한다. default도 일반 editable
  text이므로 사용자는 전부 선택, 한글/영문 수정, 삭제 및 교체할 수 있고 save에는 final trim 값만 쓴다.

### 3.6 2026-09-18 provider HTTP 오류 세부정보 정합 (승인)

- FR-SRP-047 (2026-09-18 승인): `matrix`, `optimizer`, `directions`, `access-snap`,
  `walking-directions` 각 HTTP 요청은 실패
  레코드에 해당 stage를 포함한다. non-2xx면 HTTP status를 잃지 않고 D-SRP-049의
  allowlist/sanitization/length 규칙으로 JSON provider code/message 또는 non-JSON text fallback을
  만든다. 패널은 예를 들어 `도로 경로(directions) 요청 실패 · HTTP 404 ·
  <provider code>: <provider message>` 형태로 존재하는 항목만 간결하게 표시한다.
  provider detail이 empty, unsafe 또는 HTML이면 `<stage> 요청 실패 · HTTP <status>`로
  fallback한다. network/timeout처럼 HTTP status가 없는 실패도 stage를 표시하되 status를
  만들지 않는다. 404의 의미는 provider content가 명시한 경우만 endpoint-unavailable
  또는 no-result로 구분하고, 그렇지 않으면 일반 HTTP 404로 남긴다. 오류 표시로
  인한 자동 retry/API request, route/settings write, candidate/revision 변경은 0회이며 기존
  candidate와 저장 경로를 보존한다. 2xx 성공 본문은 이 진단에 포함하지 않는다.

### 3.7 2026-09-18 차량 접근점·도보 last-mile 경로 (승인)

- FR-SRP-048 (2026-09-18 승인): 새 계산은 각 조사지의 승인된 representative WGS84 좌표를
  immutable `source_coordinate`로 snapshot하고 D-SRP-050의 original-coordinate batched snap으로 별도
  `access_coordinate`를 찾는다. `max_access_distance_m` 설정은 `차량 최대 접근 거리`로 표시하고 기본 2.00 km,
  허용 0.35~5.00 km이며 project-local non-secret settings로 저장·이동한다. 요청은 모든 original site
  좌표를 순서대로 `locations`에 넣고 설정값을 필수 `radius`로 넣은 단일 `driving-car` snap batch다.
  각 응답 위치는 input 순서의 해당 site에만 대응하며 `null`은 site name/ID와 configured radius를 밝힌
  actionable failure다. provider의 radius 거부/cap은 안전한 provider 오류로 끝내고 radius 축소,
  추가 snap input 생성 또는 별도 후보 탐색으로 우회하지 않는다. 기존 origin은 vehicle-routable이어야 하며 자동 snap이나
  origin walking leg 없이 도로 위의 map/saved start를 선택하라는 actionable error를 제공한다. source
  feature와 좌표는 모든 성공/실패/save/load에서 byte-for-byte 불변이다.
- FR-SRP-049 (2026-09-18 승인): 반환된 단일 access point와 source 사이 walking 검증은 D-SRP-051을
  따른다. mapped `foot-hiking` path가 있으면 provider distance/duration/geometry를 쓰고 왕복 방문으로
  저장한다. 명시적 no-path만 straight-line lower-bound+duration unavailable fallback을 허용하며
  `driving-car` route나 provider walking route라고 표시하지 않는다. vehicle matrix/VROOM/directions에는
  source가 아니라 chosen access coordinate만 들어간다. open/roundtrip 모두 모든 site의 walking visit은
  out-and-back이며 optimization objective와 vehicle totals에는 walking metric을 섞지 않는다.
- FR-SRP-050 (2026-09-18 승인): 계산 preview, saved-route detail, bottom remaining summary와 map은
  vehicle/walking distance와 duration을 별도 label로 표시한다. all-mapped일 때만 정확한 combined
  distance/duration을 추가할 수 있다. fallback이 있으면 walking distance를 `직선거리 하한`으로,
  walking/combined time을 `사용 불가`로 보이고 affected sites와 acknowledgement를 저장 전에 제공한다.
  route overlay와 legend는 D-SRP-054의 solid/dashed/dotted pattern, text, warning marker와 contrast casing을
  사용한다. route-line toggle은 세 route line class를 함께 숨기되 access/source/warning marker와 legend의
  현재 state 설명을 보존한다.
- FR-SRP-051 (2026-09-18 승인): explicit save는 validated mixed candidate를 schema 3으로 atomic commit한다.
  D-SRP-053의 vehicle legs, visits, original/access coordinates, exact provider metric provenance,
  fallback lower-bound/unavailable state와 separate totals가 restart, last-good recovery, offline reopen과
  project-folder move 뒤 동일해야 한다. completion/uncheck/load/toggle은 request 0회이며 vehicle leg와
  walking visit을 수정하지 않고 D-SRP-054의 prefix-derived remaining view만 다시 만든다. schema 1/2
  route의 표시·보존과 명시 재계산 upgrade는 D-SRP-027을 유지한다.
- FR-SRP-052 (2026-09-18 승인): controller는 D-SRP-052의 stage order와 D-SRP-049의 safe error record를
  사용한다. 401/403은 key/permission, 404는 configured endpoint 확인(본문이 명시하지 않으면 원인 단정
  없음), 429는 quota/wait, 5xx는 provider 재시도, timeout/network는 연결/timeout 확인을 action으로
  제공한다. snap의 `null`은 해당 site와 configured radius를, provider radius 거부/cap은 안전한
  `access-snap` detail과 설정 확인 action을, origin routing 실패는 도로 위 map/saved start 선택 action을
  보인다. transient walking failure를 no-path fallback으로 바꾸지 않는다. UI는 explicit
  calculate 전에 D-SRP-055 coordinate-sharing notice를 제공하고 어떤 실패에도 automatic retry, source/
  completion/settings/route write, candidate/revision loss를 만들지 않는다.
- FR-SRP-054 (2026-09-18 승인): schema-3 candidate save와 offline load/recovery는 모든 active/inactive
  route의 각 visit에 대해 D-SRP-057의 required identity/provenance fields와 허용
  `walking_mode`/`metric_source` 조합을 검증한다. 하나라도 invalid하면 부분 route 채택, default 보충,
  mode/source 추정 또는 문서 재저장 없이 전체 schema-3 문서를 거부하고 원본 bytes와 last-good route를
  보존한다.

### 3.8 2026-09-18 iOS Apple Maps 길안내 변경 (승인)

- FR-SRP-053 (2026-09-18 승인): 사용자가 `다음 지점 지도 안내`를 누르면 controller는 active route의
  earliest incomplete next stop 하나를 읽고 그 stop의 WGS84 coordinate를 `[longitude, latitude]`로
  해석한다. 두 값은 number이며 finite이고 latitude `[-90, 90]`, longitude `[-180, 180]` 범위여야 한다.
  각 값은 locale과 무관한 base-10 fixed 7자리 소수로 반올림한 뒤 trailing zero와 trailing decimal point를
  제거하고 negative zero를 `0`으로 정규화한다. NaN/Infinity, 지수 표기, 공백, locale decimal/group
  separator 또는 범위 밖 값은 URL을 만들지 않고 next-stop coordinate 오류를 표시한다. iOS URL은
  parameter order까지 exact
  `https://maps.apple.com/directions?destination=<latitude>,<longitude>&mode=driving`이며 현재
  destination name parameter는 0개다. Android URL은 승인된 package-bound NAVER intent를 같은
  normalized destination과 percent-encoded stop name/required `appname`으로 만든다. name과 `appname`은
  UTF-8 `encodeURIComponent` 의미로 각각 한 번만 encode하며 query delimiter나 fragment를 값에서
  주입할 수 없다. Android dispatch/fallback 순서와 결과 처리는 D-SRP-039/FR-SRP-037을 변경 없이 따른다.
  primary 호출 true에는 platform 공통으로
  `지도 앱에 길안내를 요청했습니다. 앱 실행·목적지 수락·안내 시작 여부는 확인할 수 없습니다.`를
  표시한다. iOS false/exception에는 `Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를
  확인하세요.`를 표시하고 iOS launcher는 primary 1회, fallback 0회다. Android 실패와 Google Play
  fallback은 기존 FR-SRP-037의 횟수·안내를 그대로 따른다. invalid coordinate는 모든 platform에서
  launcher 0회다. 모든 success/failure/validation path는 source feature·completion, candidate,
  active/saved route, revision, settings와 route storage를 쓰거나 바꾸지 않고 routing API도 호출하지 않는다.

### 3.9 2026-09-19 storage compatibility와 route-line preference 정합 (승인)

- FR-SRP-055 (2026-09-19 승인): empty/default initialization, schema-1/2 load 및 settings-only save는
  D-SRP-058의 schema 경계를 지킨다. explicit mixed candidate save가 top-level schema 3으로 전환할 때
  selected same-identity legacy route만 mixed route로 교체하고 다른 모든 legacy route를 route-level
  discriminator와 원래 fields로 계속 list/load할 수 있게 보존한다. mixed와 legacy variant 각각을 자기
  schema로 검증하며 어느 하나라도 invalid하면 atomic commit 또는 load/recovery 전체를 거부한다.
- FR-SRP-056 (2026-09-19 승인): route-line toggle은 세 line class의 visibility와
  `settings.show_route_line`만 함께 바꾼다. 성공한 변경은 panel reopen, app restart와 settings 파일을
  포함한 folder move 뒤 복구되고 provider request, route object/revision, source/completion write는 0회다.
  settings write/readback 실패에는 저장된 값과 route 상태를 유지하고 actionable failure를 표시한다.

### 3.10 2026-09-21 ORS 도보 endpoint snapping 명확화 (승인)

- FR-SRP-057 (2026-09-21 승인): walking directions adapter는 D-SRP-060의 documented GeoJSON
  structure, route-level `way_points`, WGS84 LineString 및 metric consistency를 response boundary에서
  검증한다. schema-3 reader는 저장된 mapped leg의 기존 finite metric, LineString, reverse geometry,
  provenance와 totals를 검증하되, requested access/source와 provider geometry endpoint의 1 m equality 또는
  provider distance와 requested access-source geodesic의 lower-bound 관계는 검증하지 않는다.
  계산·저장·재로드는 requested `access_coordinate`/`source_coordinate`와 provider-returned
  distance/duration/geometry를 각각 수정 없이
  보존하고, map과 접근 가능한 UI는 requested marker, provider-routed dashed line, `ORS 경로 기준 · 요청
  좌표까지의 endpoint gap 미포함` 의미를 함께 전달한다. gap을 직선 connector, fallback,
  `unmapped_estimate`, exact total 또는 provider metric으로 만들지 않는다. 구조가 잘못되었거나
  `way_points`가 full geometry의 첫/마지막 index를 cover하지 않거나 summary/segment metric이 tolerance
  밖이면 기존 candidate/saved route를 보존한 provider-response failure로 끝나며 fallback, 후속 vehicle
  request와 write는 0회다.

### 3.11 2026-09-21 ORS 1점 도보 geometry fallback (승인)

- FR-SRP-058 (2026-09-21 승인): walking directions adapter는 D-SRP-061의 한 점·zero-metric 응답을 정상 mapped
  LineString validation 전에 좁게 식별해 기존 explicit no-path와 동일한 fallback payload로 전달한다.
  controller, repository, map style, acknowledgement 및 totals schema는 기존
  `unmapped_estimate/straight_line_lower_bound_m` 경로를 그대로 사용하며 새 mode, metric source, schema,
  dependency 또는 provider request를 추가하지 않는다. D-SRP-061 조건을 하나라도 충족하지 않는 한 점
  또는 다른 malformed response는 현재의 안전한 구조 진단과 atomic failure를 유지한다.

### 3.12 2026-09-22 Matrix optional diagnostic 및 desktop store 정합 (승인)

- FR-SRP-059 (2026-09-22 승인): Matrix adapter는 D-SRP-062의 세 response location 범위에서
  `snapped_distance` 누락을 허용한다. present 값만 finite/non-negative와 vehicle maximum을 검사하며,
  missing 값을 `0`, requested-to-resolved 거리 또는 다른 추정값으로 합성하지 않는다. 누락 외의 기존
  response 구조/metric/location 결함과 present invalid/초과 값은 정확한 stage의 provider-response
  failure로 끝나고 후속 request/write 없이 last-good candidate와 saved route를 보존한다.
- FR-SRP-060 (2026-09-22 승인): Step 7의 desktop `Remember this key`는 D-SRP-063의 canonical
  `FieldBuild Standalone/credentials.enc`만 사용한다. route key는 기존 VWorld/Pl@ntNet keys와 같은 encrypted
  store 및 consent/password lifecycle을 재사용하지만 generated project folder로 복사되지 않는다.
  FieldBuild Kit display rename은 store path를 바꾸거나 migration을 시작하지 않으며, 다른 application
  namespace의 credential file 존재 여부와 내용은 모든 정상/실패 branch에서 관찰·변경하지 않는다.

### 3.13 2026-09-22 fallback notice·상세 정보·결과 가시성·배포 경계 (승인)

- FR-SRP-061 (2026-09-22 승인): fallback visit이 하나 이상인 candidate와 saved route는 D-SRP-064의
  exact notice를 simple user-facing totals와 함께 기본 결과 영역에 정확히 한 번 표시한다. fallback
  acknowledgement checkbox/control은 존재하지 않으며 fallback만을 이유로 저장을 disable하거나 추가
  확인을 요구하지 않는다. `상세 정보` disclosure는 기본으로 접혀 있고 raw metric source/mode,
  per-visit diagnostics와 endpoint-gap detail을 내부에만 표시한다. endpoint-gap 설명은 적용되는 route마다
  disclosure 안에 최대 한 번만 렌더링한다. disclosure의 상태는 저장 payload나 저장 가능 여부에 영향을
  주지 않으며, all-mapped/exact-zero-only 결과에는 fallback notice가 없고 기존 저장 흐름을 유지한다.
- FR-SRP-062 (2026-09-22 승인): explicit save를 실제로 시도할 수 있는 상태에서는 이름 validation,
  stale calculation/revision, repository validation, write/readback과 success를 포함한 모든 종료 경로가
  하나의 visible/accessibility status contract를 사용한다. save가 true인 경우뿐 아니라 false를 반환하거나
  exception을 처리한 경우에도 결과 message를 현재 viewport로 가져오고 한 번 announce한다. failure에는
  가능한 범위의 구체적이고 비밀이 제거된 원인과 재시도/재계산/다시 불러오기 등 이미 승인된 action을
  표시하며 candidate와 last-good saved route를 보존한다. 이 가시성 변경을 실제 저장 성공의 증거 또는
  이번 기기 관찰의 persistence root-cause 수정으로 주장하지 않는다.
- FR-SRP-063 (2026-09-22 승인): FieldBuild Kit는 route 기능을 포함해 새로 생성한 프로젝트의
  `qfield_routes/`가 그 생성 시점 source와 일치하도록 bundle하고 build 완료 시 D-SRP-066 disclosure를
  표시한다. desktop binary/source update 뒤에도 기존 output project의 embedded route files와 수집 data는
  자동 변경하지 않는다. acceptance와 release handoff는 어느 FieldBuild Kit build로 어느 project output을
  새로 생성했는지 구분하고, 기존 output을 그대로 연 기기 관찰을 새 bundle의 검증으로 기록하지 않는다.

### 3.14 2026-09-22 저장 성공 후 disabled/focus 정합 (승인)

- FR-SRP-064 (2026-09-22 승인): save success가 candidate를 clear하는 같은 UI update에서
  save button을 disable하고 candidate-none reason을 표시한다. 성공 status는 현재 viewport에
  전체가 보이고 screen-reader status로 한 번 announce하며, 이 feedback을 위해 button을 enabled로
  남기지 않는다. 앱은 focus를 disabled button에 복구하거나 다른 control로 옮기지 않고,
  route name text와 disclosure state를 보존한다. 실패 outcome은 기존 candidate/last-good
  보존과 D-SRP-065의 정상 enabled/disabled 규칙을 그대로 따른다.

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
max road offset, 이번 승인 범위의 max access distance, default start, layer/id/name/optional completion mapping이다. API key는 이 일반 설정에서
제외하며, 자동 전달에 동의한 경우에만 별도 generated project variable에 평문으로 포함한다. 이 값은
암호화되지 않고 프로젝트 폴더 접근자가 읽고 사용할 수 있다.
저장 형식은 규범이 아니며 소비자는 상대 경로로 동일한 route/revision/settings 의미를 복구해야 한다.
초기 hosted routing base는 version 없는 `https://api.heigit.org/openrouteservice`이고, provider가
그 뒤에 ORS `/v2/...` 경로를 붙인다. optimizer 설정은 완전한 endpoint
`https://api.heigit.org/vroom/v0`다. 여기에 `/post`를 붙이지 않는다. custom/self-hosted 주소는 이 두
역할을 같은 방식으로 구분한다. 기존 프로젝트 migration은 D-SRP-015의 exact-match 값만 바꾸며
경로 데이터, key 및 다른 설정을 변경하지 않는다.

### 4.1 2026-09-16 승인 data / compatibility decisions

- D-SRP-026 (Category C): layer option은 `{label, layer_id, source_name}`이며 current project의 지원
  vector layer를 QGIS layer-tree/provider 순서로 나열한다. label은 alias/display name, 없으면 source
  name이며 duplicate label은 layer-tree path와 stable layer ID로 구분한다. 저장값/현재 선택의 valid
  layer ID를 먼저 보존한다. 유효한 선택이 없고 생성 프로젝트의 내부 role/source가 `site`인 layer가
  있으면 그 첫 option을 `조사지`로 표시·선택한다. field option은 provider가 돌려준 순서를 바꾸지 않고
  actual field name을 표시·저장한다. refresh 때 현재 수동/저장 field가 선택 layer에 아직 있으면
  보존한다. 없으면 ID는 actual name이 case-insensitive `_id`, name은 `_name`으로 끝나는 첫 field를 각각
  고른다. match가 없으면 해당 값은 blank이고 계산/저장은 명확한 field 선택 오류로 막는다. layer
  선택 변경, panel reopen, project layer/schema change, calculate/save 직전에 field option을 refresh하며
  stale 값은 위 규칙으로 교체하거나 blank로 지운다.
- D-SRP-027 (Category C): 새 저장물 top-level schema는 `2`이고 route `revision`은 별도
  edit/concurrency 값이다. reader는 schema 1/2를 지원한다. schema 1 legacy route는 automatic request,
  geometry/leg 추정, read-time write 없이 full route line/total/stops를 그대로 열고 보존한다. complete
  leg가 없으면 남은 거리·시간·trimmed overlay를 `사용 불가`로 표시하고 향상된 남은 동작에는 새 전체
  경로 계산·저장 1회가 필요함을 알린다. 그 명시 작업만 schema 2를 쓰며 silent split은 금지한다.
  future schema는 덮어쓰지 않고 보존한 채 명확히 거부한다.
  **2026-09-18 승인 supersession:** mixed vehicle/walking route의 explicit 새 계산·저장은
  D-SRP-053의 schema 3을 쓰며 schema 1/2 read-only compatibility와 future-schema byte preservation은
  그대로 유지한다.
- D-SRP-028 (Category C): stop 수 `n`에서 open은 `n`, roundtrip은 `n+1` leg를 방문 순서로 저장한다.
  각 leg는 sequence, start 또는 `{layer_id, site_id}` from/to, finite non-negative `distance_m`/
  `duration_s`, WGS84 GeoJSON LineString을 가진다. canonical totals와 full route display geometry는
  immutable leg의 합/순서 결합으로 복구 가능해야 한다. provider total과 `max(1 m, 0.5%)` 및
  `max(1 s, 0.5%)` 안에서 일치하지 않으면 candidate를 거부한다. 완료, toggle, load는 leg를 수정하지
  않으며 새 명시 계산만 atomic commit으로 새 revision의 full-route를 만든다.
- D-SRP-029 (Category C/D): consecutive effective-complete prefix 길이 `k`에서 start부터 첫 `k` stop의
  inbound leg만 traversed다. remaining visit context는 earliest incomplete stop에서 시작한다. open
  remaining은 leg `k..n-1`, roundtrip은 `k..n`이고 모든 stop 완료 뒤 roundtrip return leg는
  `복귀 포함`으로 남는다. gap 뒤 out-of-order completed stop은 visit context에 계속 보이며 그 양쪽
  인접 leg를 완료로 추정하지 않는다. 따라서 앞선 gap이 닫혀 consecutive prefix에 들어오기 전에는
  그 stop 때문에 거리·시간·geometry를 차감하지 않는다. uncheck는 `k`를 다시 계산해 차감된 leg를
  즉시 복원한다. mapped Boolean write와 route-local write는 성공 뒤에만 UI/derived view를 바꾸며
  실패하면 source, route, check, symbol, metric, overlay를 모두 이전 상태로 보존한다.
- D-SRP-030 (Category D): completed feature에는 원본 layer renderer/source data를 바꾸지 않는
  non-persistent route overlay를 적용한다. point/line은 `#1565C0`(Blue 800) 100% stroke/symbol,
  polygon은 `#1565C0` 35% fill과 100% outline을 쓰고 checklist check와 `완료` text를 함께 표시한다.
  이 overlay는 point/line/polygon과 mapped/route-local completion에 동일하며 uncheck 때 제거하고
  restart/load 때 저장 completion에서 다시 파생한다. `show_route_line`은 default true인 project-scoped
  device-local non-secret UI preference로 project-local settings 파일에 저장한다. toggle off는 route-line
  overlay만 제거하고 completed overlay/full-route data는 유지한다. route 전환, panel reopen, app restart,
  settings 파일을 포함한 folder move 뒤 복구하며 API를 호출하지 않는다. settings/route commit feedback은
  실제 파일명과 project-relative path를 반환하고 path에는 secret이나 URL query가 없다.

### 4.2 2026-09-16 승인 non-functional requirements

- NFR-SRP-001: 새 label/control/guidance/metric/feedback은 320 px 폭에서 overflow 없이 touch/keyboard로 동작한다.
- NFR-SRP-002: 완료는 색만으로 전달하지 않고 check와 text/state indicator를 함께 제공한다.
- NFR-SRP-003: refresh, completion/uncheck, toggle, restart/load는 offline에서 동작하고 route request 0회다.
- NFR-SRP-004 (2026-09-17 승인): outlined labels, disclosure, persistence feedback, disabled-row
  reason, map label와 halo는 320 px panel 및 supported light/dark basemap에서 잘림·겹침 없이 읽히고
  keyboard/touch와 screen-reader accessible name/state를 유지한다.
- NFR-SRP-005 (2026-09-17 승인): 모바일 입력과 지도 렌더링에 대한 증거 수준을 구분한다.
  자동 검사는 editable/focus/input-method wiring, generated project의 labeling enablement/expression/
  placement/buffer와 floating-label geometry를 proxy로 확인할 수 있다. 정적 문자열 존재, QML/XML
  source inspection 또는 desktop/headless render만으로 실제 QField의 OS soft keyboard 개방이나
  device map canvas의 feature label/halo 표시를 PASS로 판정하지 않는다. 해당 항목은 지원을 주장하는
  각 mobile OS의 실제 QField에서 사용자 수동 증거가 있어야 PASS이며, 미수행은 `미검증`으로 남긴다.
- NFR-SRP-006 (2026-09-17 승인): supported iOS/QField light/dark appearance에서 route panel의 normal
  text, floating labels, help/status/error text, field values/placeholders 및 enabled action labels은 각 실제
  background에 대해 WCAG contrast ratio 4.5:1 이상을 유지한다. control outline, focus ring, checkbox/
  dropdown indicator와 large/icon-only affordance는 인접 색에 대해 3:1 이상이며 focus/error/selected/
  checked/disabled 상태는 색만으로 구분하지 않는다. disabled text도 삭제된 것처럼 보이지 않도록
  label/value와 disabled reason에 대해 4.5:1 이상을 유지한다. 기준 palette는
  light `{surface #F8FAFC, text #111827, muted #334155, outline #64748B}`와 dark
  `{surface #111827, text #F9FAFB, muted #CBD5E1, outline #94A3B8}`이고 focus `#2563EB`, error는
  각 theme에서 위 contrast threshold를 만족하는 red variant를 쓴다. exact implementation colors는
  동일하거나 더 높은 contrast로 바꿀 수 있지만 state matrix와 semantic meaning은 바꾸지 않는다.
- NFR-SRP-007 (2026-09-18 승인): provider 오류 진단은 최대 512 Unicode 문자이며
  단일 화면 message와 screen-reader status에서 동일한 정제 결과를 제공한다. 응답
  parsing/sanitization은 기존 runtime/standard 기능만 쓰고 새 dependency와 logging subsystem을
  요구하지 않는다. malformed/huge body에서도 전체 본문을 UI에 복사하거나
  비밀·HTML·control 문자를 표시하지 않고 bounded generic error로 안전하게 종료한다.
- NFR-SRP-008 (2026-09-18 승인): access snap은 `max_access_distance_m`, provider snap radius와
  documented location/batch limit로 bounded되고 UI cancel/project close 뒤 추가 request를 시작하지
  않는다. 동일 input/settings/provider responses는 동일 input-order access mapping/schema-3 bytes
  (생성시각·route ID 제외)를 만든다. 요청 좌표를 생성하거나 원본 외 위치를 탐색하지 않으며 raw
  provider body를 영구 저장하거나 화면에 덤프하지 않는다.
- NFR-SRP-009 (2026-09-18 승인): vehicle/mapped-walking/unmapped line, legend, warning,
  separate totals와 unavailable state는 320 px와 supported light/dark theme에서 잘림 없이 보이고
  keyboard/screen reader가 mode, site, metric source, out-and-back 및 unavailable 이유를 읽을 수 있다.
  line casing은 basemap에 대해 3:1 visual boundary를 만들고 dash/dot/text/icon을 함께 써서 color vision
  deficiency 또는 grayscale에서도 세 mode를 구분한다. map screenshot은 실제 target QField 증거이며
  source color literal만으로 PASS하지 않는다.
- NFR-SRP-010 (2026-09-22 승인): credential-store path 판정과 route-key retention은 fail-isolated다.
  canonical store 밖의 credential file/directory를 발견, 열기, 복사, 병합, 이동, 삭제하거나 그 존재를
  로그·UI·report에 노출하지 않는다. 테스트는 disposable override directory만 사용하고 실제 사용자
  app-data 또는 다른 앱의 비밀을 읽거나 수정하지 않는다. path mismatch 또는 store failure는 project
  build를 막거나 plaintext fallback을 만들지 않고 기존 session-only/명시 consent 경계를 유지한다.
- NFR-SRP-011 (2026-09-22 승인): D-SRP-064~065의 notice, `상세 정보`, disabled reason과 save status는
  320 px 이상 supported viewport와 light/dark theme에서 저장 control과 함께 읽을 수 있고 horizontal
  scroll, clipping 또는 다른 control과의 overlap이 없어야 한다. dynamic count/name이 길면 wrap하되
  기본 결과, notice, disclosure, 저장 control과 결과 status의 읽기 순서를 유지한다. disclosure가 접힌
  상태에서는 복잡한 내부 문자열을 기본 reading flow에 중복 노출하지 않고, 펼친 상태에서는 label과
  각 diagnostic의 의미를 keyboard/screen reader로 접근할 수 있어야 한다. save attempt 하나당 최종
  outcome을 한 번만 announce한다. viewport 이동은 keyboard focus, 입력한 route name, disclosure state와
  candidate를 바꾸지 않는다.
- NFR-SRP-012 (2026-09-22 승인): NFR-SRP-011의 reading-order 계약을 시각 배치,
  keyboard traversal과 screen reader 모두에서 다음 semantic 순서로 적용한다: (1) simple 기본
  결과, (2) fallback notice(적용 시), (3) `상세 정보` disclosure와 펼쳐진 내용, (4) `저장할
  경로 이름`, (5) `계산 결과 저장`, (6) disabled reason(적용 시), (7) save attempt의 최종
  outcome status(시도 후). 접힌 진단은 reading/accessibility flow에 노출하지 않는다.
  status를 viewport에 가져오는 동작은 순서를 바꾸거나 다른 editable/control에 focus를
  이동시키지 않는다. save success 후 disabled 된 save button이 플랫폼 규칙에 따라
  `activeFocus`를 잃는 것은 이 계약의 위반이 아니다.

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
| AC-SRP-011 | 12중 4완료 재계산은 GPS+8개만 요청하고 4개 기록 유지. 이 승인 기준본 문구는 이력으로 보존하되, 2026-09-16 승인된 D-SRP-023/FR-SRP-026/AC-SRP-026이 supersede하여 해당 control/request는 0개가 된다. |
| AC-SRP-012 | 지도 도로선 재표시와 인코딩된 nmap URL/실패 안내 |
| AC-SRP-013 | 새 프로젝트의 등록 `ors-vroom` 기본 설정이 matrix `https://api.heigit.org/openrouteservice/v2/matrix/{profile}`, directions `https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson`, optimizer POST `https://api.heigit.org/vroom/v0`를 요청하고 `/vroom/v0/post` 및 `api.openrouteservice.org` 요청은 0회; routing base 끝 `/`도 중복 경로 없음; 기존 exact routing default와 missing/empty 또는 exact legacy optimizer만 각각 migration하고 혼합된 custom 값은 보존; 사용자 입력 custom/self-hosted routing base와 완전한 optimizer endpoint를 저장·재로드하여 치환 없이 같은 경로로 요청; server/profile/timeout/offset과 project variable 또는 session의 non-empty key를 transport 경계에 전달하고 key는 선택된 요청의 `Authorization` header에만 존재; hosted 기본값의 빈 key는 request 전 거부, key 없는 custom 요청은 인증 header 생략; 펼침/접힘/완료/불러오기 API 0회; key의 URL·query·body·보고서·로그·오류 노출 없음; 나머지 설정 폴더 이동 보존 |
| AC-SRP-014 | 직접 점/선/면 선택·완료·다중 대상 저장, 미완성 도형 안내 |
| AC-SRP-015 | SHP/ZIP/GPKG × 6유형 자동 판별·XY/다중 부분 보존 |
| AC-SRP-016 | 업로드/직접 입력→GPKG 메타데이터/rtree→생성 프로젝트 도형 일치 |
| AC-SRP-017 | FieldBuild Kit가 생성·검증한 투영 CRS와 WGS84 test site의 6유형에서 새 경로 계산이 포괄적 CRS 오류 없이 Point 원점/MultiPoint·선·면 source-CRS centroid→WGS84를 생성; 원본 불변; 실제 source CRS missing/invalid/변환 실패 시 명확한 거부와 기존 경로 보존 |
| AC-SRP-018 | 기존 폴리곤/관계/식별/보고서 회귀 및 옮겨진 생성물 검사 |
| AC-SRP-019 | 프로젝트 생성 UI에 masked route key 입력이 있고, 입력 시 평문 포함·폴더 접근자의 읽기/사용 가능·비암호화를 명시한 경고와 consent가 존재; 동의하면 generated project variable의 평문 key로 QField가 자동 사용; 거부·blank이면 key 없이 생성되고 QField session 수동 입력 가능; 입력·거부·취소·생성 실패에서 key가 로그/오류/보고서/URL/query/body/non-secret 일반 설정에 없음; 선택적 desktop remember는 기존 `credentials.enc`만 사용하고 QField 전달로 간주하지 않음 |
| AC-SRP-020 | 최소·넓은 panel viewport에서 모든 editable/select field가 공통 좌우 margin 안의 available width를 사용하고, 같은 행 field는 균등 분할하며, label/help/error 기준선·wrap과 horizontal overflow를 layout/screenshot으로 검사 |
| AC-SRP-021 | current project vector layer dropdown이 alias/display name과 stable layer ID를 roundtrip하고 내부 `site`를 `조사지`로 표시·기본 선택한다. layer 변경/refresh 때 field list를 provider order로 다시 읽고 valid manual/stored actual field를 보존하며, 없으면 첫 case-insensitive `_id`/`_name` suffix field를 각각 선택하고 no-match는 blank+명확한 validation+계산/저장 차단이 된다. duplicate label/stale layer도 stable ID로 결정적으로 처리한다. |
| AC-SRP-022 | 작은 `조사 경로 계산 대상`/`출발지` label이 각 control 위에 있고 map-center control은 `지도 위치 출발`에서만, target dropdown은 `조사대상 출발`에서만 보인다. target option은 `이름 · ID`를 표시하고 ID를 저장하며 stale target은 clear/block한다. |
| AC-SRP-023 | default-start save 성공이 좌표와 실제 project-local settings 파일명/상대 경로, route save 성공이 final name과 사용자가 접근할 실제 project-folder storage 파일명/상대 경로를 표시한다. 실패 시 success 0회이고 모든 feedback/path에서 secret·Authorization·key-bearing query 노출은 0회다. |
| AC-SRP-024 | checklist 위의 `방문 순서대로 이동하고, 조사를 마친 지점을 체크하세요.`와 saved-route selector 위의 작은 `저장 경로 이름` label이 narrow/wide layout에서 읽히고 wrap된다. |
| AC-SRP-025 | next-site가 exact `nmap://navigation?dlat=<lat>&dlng=<lng>&dname=<encoded>&appname=<caller-id>`를 required/encoded query로 `Qt.openUrlExternally`에 전달한다. Android/iOS primary true는 OS-request-only feedback과 fallback 0회, false는 각각 `com.nhn.android.nmap`/App Store `311867728` install page 1회, all-refused/non-mobile은 actionable error다. 실제 mobile handoff/목적지/안내 수락은 사용자 기기 acceptance이며 Qt true만으로 PASS하지 않는다. |
| AC-SRP-026 | open/roundtrip가 n/n+1 ordered complete leg와 합계/full geometry를 schema 2에 저장하고 completion/toggle/load가 그 immutable data를 바꾸지 않는다. invalid/missing leg 또는 total tolerance 실패는 기존 route를 보존하며 `남은 지점 계산` control/request는 0개다. |
| AC-SRP-027 | point/line/polygon 완료가 원본 renderer/source를 바꾸지 않는 D-SRP-030의 `#1565C0` overlay+check+text로 보이고 uncheck 때 제거된다. in-order prefix만 차감/trim하며 earliest incomplete 뒤 out-of-order completed stop과 양쪽 leg는 gap이 닫힐 때까지 visit context/remaining에 남는다. mapped/route-local write success와 failure-preserve-state, open/roundtrip return, restart/recovery/offline/folder-move가 같은 결과이고 API request는 0회다. |
| AC-SRP-028 | distance는 km 소수점 2자리, duration은 ceil-minute `X시간 YY분` 또는 zero-hour `YY분`이고 bottom bar는 active/no-route 모두 remaining distance/time을 표시한다. default-on line toggle은 saved geometry/completed overlay를 바꾸지 않고 API 0회이며 project-scoped device-local preference가 route switch/panel reopen/app restart/settings 동반 folder move 뒤 유지된다. |
| AC-SRP-029 | schema 1 legacy route를 offline에서 full line/total/stops 그대로 load/retain하고 remaining enhanced 값은 unavailable+새 전체 계산 1회 안내로 표시한다. automatic write/request/leg split 추정은 0회이며 explicit recalculation/save만 schema 2를 만들고 route revision 의미를 유지한다. future schema는 보존/거부한다. |
| AC-SRP-030 | 기존 point/line/polygon/6유형 geometry·centroid/WGS84와 선택 0/1/N·scope 동작, 다중 route/last-good/revision/restart/recovery/offline/folder-move storage, key/header/generated-variable 및 로그·오류·feedback secret 경계가 2026-09-16 변경 전 승인 규칙대로 회귀 통과한다. completion/toggle/load에는 routing API 호출이 없다. |
| AC-SRP-031 (2026-09-16 승인) | narrow/wide, empty/value/focus/error 상태에서 scope/start/layer/ID/name/completion 여섯 selector가 ORS 서버 URL field와 같은 in-control floating label을 계속 표시하고 별도 label row·겹침·잘림·placeholder-only accessible name은 0개다. UI text는 `조사지`를 쓰고 stable layer ID/actual field 저장값은 불변이다. |
| AC-SRP-032 (2026-09-16 승인) | map을 pan한 뒤 `지도 중심을 출발지로 지정`하면 당시 center에 식별 가능한 `출발지` marker가 즉시 정확히 1개 생긴다. 이후 pan/zoom에는 고정, 재지정에는 이동/교체, collapse/reopen과 계산 성공/실패에는 유지되고 mode 변경·clear/invalid·project close에는 제거된다. source/renderer/saved route write는 0회이고 변환 실패는 기존 marker/start를 보존한다. |
| AC-SRP-033 (2026-09-16 승인) | 0/1/N 및 중복 이름 fixture에서 target dropdown stable-ID set/order가 같은 순간의 calculation preflight와 정확히 일치한다. selected/all/uncompleted 전환, QField selection, completion, layer/mapping 변경은 API 0회로 options를 먼저 갱신하고 `이름 · ID`를 보인다. 유효한 기존 ID는 보존, stale ID는 clear한 다음 required error가 나타나며 empty-target 선검증 때문에 options가 비는 경우는 없다. |
| AC-SRP-034 (2026-09-16 승인) | `선택 대상`에서만 scope 설명 바로 다음 줄에 exact 선택 절차와 `현재 선택한 조사지: N개`가 표시되고 0/1/N과 FR-SRP-002 결과가 일치한다. `전체 대상`/`미조사 대상`에는 해당 안내·count·빈 row가 없으며 scope 공통 설명은 유지된다. |
| AC-SRP-035 (2026-09-16 승인) | Point 원점 및 MultiPoint/LineString/MultiLineString/Polygon/MultiPolygon source-CRS centroid fixture가 같은 stable-ID VROOM order와 ORS validator를 통과한다. `segments[]`에 `way_points`가 없고 route-level `properties.way_points`만 있는 유효 ORS GeoJSON fixture를 index-pair별 leg로 저장하며 open/roundtrip count/order/LineString/metric/total을 승인한다. missing/duplicate/unassigned order, invalid top-level index, segment/geometry/metric/tolerance defect는 원인·ID/구간을 밝힌 provider 오류와 기존 경로 보존이 되고, contract-valid fixture의 forced local parser failure는 별도 client-processing 오류가 된다. 실제 QField Point/Line/Polygon 수동 결과는 각각 수행된 경우에만 PASS로 기록한다. |
| AC-SRP-036 (2026-09-17 승인) | 계산 성공 뒤 API request 0회 상태에서 경로 이름을 처음 입력하거나 여러 번 수정해 즉시 저장하면 마지막 trim name과 동일한 candidate route가 저장된다. name focus/change는 candidate와 base revision을 바꾸지 않는다. blank name·I/O failure는 candidate/기존 경로를 보존해 재시도할 수 있고, 실제 calculation input 또는 snapshot revision 변경만 구체적인 stale feedback과 함께 저장을 막는다. |
| AC-SRP-037 (2026-09-17 승인) | 320 px 및 wide viewport의 empty/value/focus/error 상태에서 text/dropdown 일곱 control이 exact `조사지`, `조사지 ID 필드`, `조사지 이름 필드`, `조사 완료 필드`, `계산 대상`, `출발지`, `저장할 경로 이름` outlined floating label을 같은 위치·크기·여백으로 유지한다. label/option/indicator/error의 겹침·별도 label row·placeholder-only accessible name은 0개이고 stable stored values는 불변이다. |
| AC-SRP-038 (2026-09-17 승인) | 새 panel session에서 `API URL/키 설정`은 접혀 있고 펼침/접힘에 request·write가 없다. 펼치면 `VROOM 서버 URL` exact label과 masked key가 보인다. manual key는 session 종료 후 복구되지 않고 settings save snapshot에 없으며, consented project variable key는 `.qgs` 평문 source 경고와 함께 session에 로드된다. save 성공 feedback은 현재 프로젝트, 실제 `survey-routes.a.json`/`.b.json` 상대 경로와 key 제외를 표시하고 readback 값에 key/objective가 없으며 route와 non-secret settings가 함께 복구된다. 실패는 success 0회와 last-good 보존이다. |
| AC-SRP-039 (2026-09-17 승인) | Android supported host는 공식 package-bound navigation intent, iOS는 official `nmap://navigation`과 required encoded destination/appname을 사용한다. primary 불가 때 해당 공식 Google Play/App Store fallback은 1회, 지원되지 않은 임의 web URL은 0회다. 공식 문서가 navigation web fallback을 명시한 fixture에서만 그 exact documented URL을 사용한다. dispatch 결과는 OS request로만 보고하며 Android/iOS 실제 handoff는 기기별로 검증한다. |
| AC-SRP-040 (2026-09-17 승인) | 1→2→3 route에서 stop 2/3은 stop 1 전 check 불가이고 시도 시 값·source·overlay·metric·geometry·revision·API가 불변이며 next-stop feedback이 보인다. 순서대로 check하면 하나씩 enable된다. 완료 stop uncheck 또는 mapped source의 out-of-order true는 뒤 true를 `순서 밖 완료`로 보존하고 earliest gap부터 remaining에 포함하며, gap closure 때 API 없이 prefix metric/geometry가 갱신된다. write failure는 모든 기존 상태를 보존한다. |
| AC-SRP-041 (2026-09-17 승인) | generated polygon 조사지가 gray가 아닌 visible accent outline/fill로 light/dark basemap에서 식별되고 point/line/polygon 조사지 label이 configured name field와 정확히 일치하며 흰색 buffer/halo를 가진다. null/empty name label은 없고 markup-looking text는 inert하다. source geometry/attribute/renderer contract, completion overlay, route line과 start marker는 변경·혼동되지 않는다. |
| AC-SRP-042 (2026-09-17 승인) | 실제 target QField mobile에서 외부 keyboard를 분리하고 OS soft keyboard를 켠 상태로 `저장할 경로 이름` 본문을 누르면 caret/focus와 soft keyboard가 나타난다. 한글·영문 입력, 선택, 삭제, 재입력 뒤 계산 request 0회로 마지막 trim name이 저장되고 candidate/revision은 불변이다. 자동 proxy는 editable/focus/input-method wiring과 save flow를 검사하되 keyboard 개방 PASS를 대신하지 않으며, 지원을 주장하는 각 OS의 수동 결과를 별도로 기록한다. |
| AC-SRP-043 (2026-09-17 승인) | 320 px 및 wide viewport의 empty/value/focus/disabled/error 상태에서 여덟 exact label이 같은 typography/inset/notch를 쓰고 각 label box의 수직 중심이 top outline과 일치해 border line을 가로지른다. `저장 경로 불러오기`도 같은 floating label을 사용하며 indicator/selected text와 겹치지 않는다. label 전체가 border 아래로 처지거나 위로 뜨는 상태, 별도 label row, clipping, horizontal scroll, placeholder-only accessible name은 0개다. 구조/geometry 자동 검사는 가능한 proxy이고 target QField screenshot/interaction review가 실제 배치의 최종 증거다. |
| AC-SRP-044 (2026-09-17 승인) | spaced fixture의 Point/MultiPoint, LineString/MultiLineString, Polygon/MultiPolygon 각 feature가 target QField의 적절한 zoom에서 정확히 하나의 readable label과 흰색 halo를 보인다. non-empty name은 exact trimmed name, name field missing/invalid 또는 value empty는 exact trimmed stable ID, 둘 다 없거나 empty면 label 0개이며 multipart part별 중복과 arbitrary-field fallback은 없다. markup-looking text는 inert이고 source/overlay는 불변이다. generated `.qgs`의 labeling enablement/expression/placement/buffer 자동 검사는 proxy일 뿐 device screenshot/manual render PASS를 대신하지 않는다. |
| AC-SRP-045 (2026-09-17 승인) | wizard Step 7에서 masked `ORS API 키 (선택)` field 다음 읽기 순서에 D-SRP-045의 exact purpose와 blank-key 설명, exact plaintext warning과 consent label이 보이고 keyboard/screen-reader로 접근 가능하다. blank 또는 consent 거부는 생성 성공+generated key 0개+QField 세션 입력 안내, non-blank+consent는 평문 project variable 1개+review warning, desktop remember만 선택한 상태는 generated key 0개다. 네 상태 모두 raw key가 summary/log/error/general settings에 없으며 copy가 ORS 경로·방문 순서 용도와 평문 위험을 기술 용어 없이 구분한다. |
| AC-SRP-046 (2026-09-17 승인) | 같은 project/candidate를 target iOS QField의 light와 dark appearance에서 열고 normal/value/empty/focus/selected/checked/error/disabled 상태를 capture하면 summary, 모든 label/value/help/action/status가 읽히며 NFR-SRP-006의 4.5:1/3:1 threshold를 측정 통과한다. theme 전환은 값·focus·candidate·route·scroll을 보존하고 request/write는 0회다. screenshot/pixel measurement와 실제 기기 interaction이 최종 증거이며 source의 color literal 존재만으로 PASS하지 않는다. |
| AC-SRP-047 (2026-09-17 승인) | 320 px 이상 narrow/wide iOS QField에서 expanded header의 painted bottom과 첫 `조사지` label painted top 사이가 최소 8 dp이고 label/notch/top outline이 전부 보인다. empty/value/focus/error/disabled 및 supported text scale에서 clipping/overlap/horizontal scroll은 0개이며 label/control tap은 header collapse를 trigger하지 않고 header tap만 collapse한다. geometry 자동 검사는 proxy이고 실제 screenshot/tap 결과를 함께 기록한다. |
| AC-SRP-048 (2026-09-17 승인) | device local date가 2026-09-17인 fixture에서 새 successful candidate는 exact `2026-09-17 조사`를 editable input에 보인다. iOS tap→caret→soft keyboard 뒤 수정/삭제한 final trim name이 request 0회로 저장된다. collapse/theme/refresh/save retry와 실패 계산은 name을 보존하고, 다음 explicit successful calculation은 그때의 local date default로 reset한다. UTC와 local date가 다른 boundary fixture는 local date를 택하며 locale 변경에도 `yyyy-MM-dd 조사` 형식이 유지된다. saved-route load는 stored name을 보존한다. |
| AC-SRP-049 (2026-09-18 승인) | matrix/optimizer/directions 각 fixture의 non-2xx가 exact stage와 HTTP status를 보존한다. JSON의 safe scalar provider code/message는 control/format 문자·연속 공백이 정규화되고 64/320/512자 제한 안에서 간결한 한국어 진단에 표시된다. plain-text 본문은 320자 안전 fallback, empty/HTML/markup/malformed/secret-like/Authorization/known-key/key-bearing URL·query·body/huge-body fixture는 detail 0개와 generic stage+status만 표시한다. 서로 다른 provider content의 404 endpoint-unavailable/no-result는 그 content가 명시한 분류만 표시하고 content 없는 404는 둘 중 하나로 추정하지 않는다. 모든 실패에서 자동 retry/request, route/settings write, candidate/revision 변경은 0회이고 기존 candidate/saved route는 동일하며, 2xx 본문은 error UI에 노출되지 않는다. |
| AC-SRP-050 (2026-09-18 승인) | 350 m보다 멀지만 2 km 안의 `driving-car` graph point로 snap 가능한 rural site를 포함한 ordered site fixture를 계산하면 단일 `/v2/snap/driving-car/json` request의 `locations`가 original site 좌표와 같은 순서이고 required `radius`가 exact 2000이다. 응답 point/null은 input 순서에 1:1 대응하고 모든 vehicle request는 반환 access coordinates만 쓰며 original representative/source feature bytes는 before/after/save/reload에서 동일하다. `null`, documented batch-limit 초과, provider radius reject/cap 각각은 name/ID·2.00 km 또는 안전한 provider detail과 설정/좌표/OSM 확인 action으로 실패하고 후속 walking/matrix/optimizer/directions/write 0회 및 기존 candidate/saved route 불변이다. 0.35/2/5 km 설정 모두 original site 외 snap input 생성, 후보 탐색, radius 자동 축소와 추가 snap request가 0회다. routable origin은 기존 동작을 유지하고 non-routable origin은 자동 snap/origin walking leg 없이 도로 위 map/saved start를 쓰라는 오류로 끝난다. |
| AC-SRP-051 (2026-09-18 승인) | mapped foot fixture는 각 site에 반환된 단일 access point에서 original source까지 exact foot-hiking distance/duration/geometry의 왕복을 저장한다. ≤1 m fixture는 walking zero와 foot request 0회다. explicit no-path fixture는 그 access point의 exact geodesic 왕복 lower-bound, null time, dotted line과 `지도 경로 없음`을 만들고 acknowledgement 전 save를 막는다. HTTP/timeout/malformed/mismatched foot fixture는 fallback 0개, 후속 vehicle request/write 0회와 last-good 보존이다. open과 roundtrip의 마지막 stop을 포함한 모든 visit은 out-and-back이고 VROOM cost에는 walking metric이 없다. |
| AC-SRP-052 (2026-09-18 승인) | all-mapped와 one-fallback mixed candidates가 schema 3의 vehicle legs, visits, source/access coordinates, trip multiplier, metric source와 separate totals를 exact roundtrip한다. fallback route의 walking/combined duration은 null이며 숫자 0이나 추정값이 아니다. restart/recovery/offline/folder move와 complete→uncheck는 request 0회로 같은 full data와 prefix-derived vehicle/walking remaining state를 복원한다. schema 1/2 load는 bytes/write/request 불변이고 explicit recalculation/save만 schema 3을 만들며 older-reader future-schema rejection은 bytes를 보존한다. |
| AC-SRP-053 (2026-09-18 승인) | 320 px 및 wide target QField의 light/dark basemap에서 solid vehicle, dashed mapped walking, dotted unmapped segment와 warning marker가 contrasting casing 및 text+pattern legend로 color/grayscale 모두 구분된다. preview/detail/bottom summary와 screen reader가 vehicle and walking distance/time, 왕복, metric source 및 unavailable reason을 별도로 전달하고 fallback affected site/acknowledgement를 보인다. toggle/completion은 immutable data와 source renderer를 바꾸지 않고 expected overlays/totals만 갱신한다. 자동 style 검사는 proxy이며 실제 device screenshot/interaction을 최종 증거로 기록한다. |
| AC-SRP-054 (2026-09-18 승인) | captured request sequence는 preflight/origin validation→single batched access-snap→per-site walking directions 또는 explicit fallback→driving matrix→optimizer→driving directions→validation이고 각 injected stage failure 뒤 request/write가 없다. 401/403/404/429/5xx/timeout과 provider radius reject/cap은 D-SRP-049 길이/redaction 및 FR-SRP-052 action을 보이며 raw key, Authorization, URL query/body, raw response, source attributes/name/business ID는 UI/log/storage에 없다. coordinate-sharing notice 뒤 explicit calculate만 original source와 returned access coordinates를 ORS에 보내고 VROOM은 access/cost/request-local integer만 받는다. original source 외 생성 좌표와 automatic radius change는 0회다. cancel/project close와 preview/legend/toggle은 추가 request 및 source/completion/settings/route write 0회다. |
| AC-SRP-055 (2026-09-18 승인) | button의 exact label은 Android/iOS 모두 `다음 지점 지도 안내`다. `[127.123, 37.456]` next stop의 iOS tap은 exact `https://maps.apple.com/directions?destination=37.456,127.123&mode=driving`만 `Qt.openUrlExternally`에 한 번 전달하고 NAVER/App Store/Google Play/web URL과 destination-name parameter는 0개다. iOS primary false/exception도 total launcher 1회, fallback 0회와 actionable Apple Maps error로 끝난다. Android tap은 같은 normalized destination에 D-SRP-039/FR-SRP-037/AC-SRP-039의 exact package-bound NAVER intent와 기존 Google Play fallback을 변경 없이 사용한다. Korean, `&`, `#`, `%`, whitespace가 포함된 Android stop name/caller ID는 UTF-8로 각각 한 번만 encode되어 parameter/fragment를 주입하지 않는다. boundary, excess-decimal rounding/trimming 및 negative-zero fixture는 FR-SRP-053의 canonical coordinate를 만들고 NaN/Infinity/string/지수표기 유도/범위 밖 fixture는 launcher 0회와 coordinate 오류가 된다. primary true는 exact OS-request-only status를 보이고 app/destination/navigation success claim은 false이며, Android fallback 결과도 앱 실행·목적지 수락·안내 시작으로 주장하지 않는다. 모든 branch는 routing request와 source/completion/candidate/route/revision/settings/storage write 0회다. 자동 fixture는 URL·call count·state preservation proxy일 뿐이며, target iOS QField에서 Apple Maps가 exact next-stop destination과 driving directions를 표시하는지와 target Android QField에서 NAVER Maps가 exact destination 및 기존 fallback behavior를 받는지는 OS/QField/device version과 함께 사용자 handoff로 각각 검증한다. 미수행 결과는 PASS가 아니라 `미검증`이다. |
| AC-SRP-056 (2026-09-18 승인) | production save로 만든 active+inactive route가 있는 schema-3 문서에서 각 visit의 `layer_id`, `site_id`, `metric_source` 누락·blank, stop identity 불일치, unknown `walking_mode`/`metric_source`, 그리고 `mapped/ors-foot-hiking`, `exact_zero/exact_zero`, `unmapped_estimate/straight_line_lower_bound_m` 외 mode/source 조합을 하나씩 주입하면 load/recovery가 문서 전체를 거부한다. 모든 case에서 repair/default/추정, provider request와 storage write는 0회이고 원본 bytes와 last-good route는 동일하다. 세 허용 조합의 정상 문서는 restart/offline/folder move 뒤 exact roundtrip한다. schema 1/2 fixture는 기존 read-only 의미로 계속 열린다. |
| AC-SRP-057 (2026-09-19 승인) | no-file/default open은 write 0회와 schema-2 in-memory 의미를 보이고, 최초 settings-only save 및 schema-1 settings-only upgrade는 top-level schema가 3이 아니다. 두 개 이상의 schema-1/2 route 중 하나를 explicit recalculation+save하면 document만 schema 3이 되고 selected identity 하나는 `route_schema: 3` mixed route로 교체되며 unrelated routes는 원래 fields와 `route_schema: 1|2`로 모두 남아 list/load된다. active ID, names, revisions와 legacy bytes/semantics는 삭제·mixed 추정 없이 보존된다. untagged homogeneous schema-3 fixture는 write 없이 mixed로 열리고 다음 정상 write에 marker가 생긴다. mixed/legacy corruption, unknown marker, marker/content contradiction 또는 duplicate identity는 전체 commit/load/recovery 실패, provider/storage 후속 동작 0회와 이전 bytes/last-good 보존이다. |
| AC-SRP-058 (2026-09-19 승인) | default-on toggle을 off로 바꾸면 정확히 한 번의 atomic settings write/readback 뒤 route line 세 class만 숨고 route/source/completion/revision은 불변이다. panel reopen, cold restart와 settings 동반 folder move에서 off가 복구되며 다시 on 저장도 같다. preview/legend view는 write 0회다. settings write/readback failure는 success 0회, persisted preference와 route 상태 불변 및 actionable feedback이고 모든 branch의 provider request는 0회다. |
| AC-SRP-059 (2026-09-21 승인) | 두 requested coordinate가 각각 유효한 `foot-hiking` graph point로 snap되어 geometry 첫·끝이 requested access/source에서 1 m보다 멀고 provider distance가 requested access-source geodesic보다 짧은 ORS-shaped fixture도, feature 1개·finite WGS84 LineString·summary·segment 1개·route-level `way_points=[0,last]`와 D-SRP-028 metric tolerance를 만족하면 mapped visit으로 승인한다. schema 3 save/restart/offline/folder move는 requested source/access와 provider distance/duration/geometry를 각각 exact roundtrip하고 return geometry만 reverse하며 schema/version/mode/metric source를 새로 만들지 않는다. map과 screen reader는 requested source/access marker와 provider dashed geometry를 서로 다른 좌표에 그대로 표시하고 `ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함`을 전달하며 synthetic connector, gap metric/time, fallback과 source 좌표 이동은 0개다. missing/non-covering/non-integer/non-increasing `way_points`, invalid geometry/summary/segment 또는 tolerance 밖 metric fixture는 전체 계산 실패, fallback/후속 vehicle request/write 0회 및 last-good 보존이다. |
| AC-SRP-060 (2026-09-21 승인) | ORS-shaped walking fixture가 feature 1개, `LineString` 좌표 정확히 1개, segment 1개, route-level `way_points=[0,0]`, summary와 segment distance/duration 모두 숫자 0이면 계산은 해당 visit만 `unmapped_estimate/straight_line_lower_bound_m`으로 만들고 requested access↔source geodesic 왕복 lower-bound, null duration/combined total, dotted line, 영향 조사지 안내와 저장 acknowledgement를 사용한다. mapped geometry/metric, duplicated point, connector, 새 mode/schema/request는 0개이며 source/access는 불변이다. distance 또는 duration이 non-zero/non-finite/missing, summary/segment 불일치, `[0,0]` 외 way-points, 좌표 0개/2개 이상인 malformed 변형은 fallback과 후속 vehicle request/write 0회로 실패하고 기존 candidate/saved route를 보존한다. 정상 2점 이상 mapped fixture와 explicit 2010/no-path fixture는 각각 AC-SRP-059와 AC-SRP-051 의미를 유지한다. |
| AC-SRP-061 (2026-09-22 승인) | 동일한 성공 계산 fixture에서 (a) origin-validation `sources[0]`, (b) origin-validation `destinations[0]`, (c) vehicle matrix `sources[]` 각각의 `snapped_distance`만 독립적으로 생략해도 기존 valid location/duration/matrices로 계산·저장이 성공하고 missing 값을 합성하지 않는다. 같은 각 위치에 present string/null/non-finite/negative 값을 하나씩 넣으면 해당 stage에서 provider-response failure, 후속 request/write 0회와 last-good 보존이다. vehicle source의 present 값은 configured maximum 이하 boundary에서 성공하고 초과 시 기존 이격거리 실패이며, object/cardinality, origin location/duration 또는 matrix metric 결함은 계속 실패한다. |
| AC-SRP-062 (2026-09-22 승인) | isolated macOS/Windows path resolution은 remembered route key를 각각 exact `~/Library/Application Support/FieldBuild Standalone/credentials.enc`와 `%APPDATA%\FieldBuild Standalone\credentials.enc`에만 암호화 저장·재로드한다. FieldBuild Kit display name 및 `FieldBuild Kit`/`QField Project Builder` sibling stores의 absent/present/populated 조합은 canonical path와 readback을 바꾸지 않으며 sibling bytes와 directory state는 전후 동일하다. diagnostic override는 명시한 disposable directory의 `credentials.enc` 하나만 사용한다. remember off/blank/store failure는 새 file 또는 plaintext fallback을 만들지 않고, 어느 branch도 desktop store를 generated project에 복사하거나 secret/path를 일반 로그·UI·report에 노출하지 않는다. |
| AC-SRP-063 (2026-09-22 승인) | mapped visit과 fallback visit 2개가 섞인 candidate 및 이를 저장해 다시 연 route는 접히지 않은 결과 영역에 simple vehicle/walking distance·time totals와 exact `실제 도로 경로를 못 찾은 구간을 직선거리 추정치로 포함하였습니다.`를 각각 표시하고 notice는 화면과 screen reader에 정확히 한 번만 존재한다. `지도에 없는 도보 구간 포함` 또는 다른 acknowledgement checkbox/control은 0개이며, 다른 기존 validation이 유효하면 fallback 상태에서도 save button이 활성화되어 추가 확인 없이 저장 성공 fixture를 commit한다. `상세 정보`는 최초 표시/load에서 접혀 있어 raw `walking_mode`/`metric_source`, per-visit diagnostics와 endpoint-gap 문구가 기본 결과에 노출되지 않는다. 펼치면 affected visit별 진단과 적용 route당 exact `ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함` 한 줄만 보이고 visit card/totals/legend에는 같은 endpoint-gap line이 0개다. 펼침/접힘 전후 candidate/payload/request/write count와 save enablement는 동일하다. all-mapped/exact-zero-only candidate에는 fallback notice가 없고, candidate 없음과 invalid mapping만 D-SRP-065의 인접 disabled reason을 보인다. |
| AC-SRP-064 (2026-09-22 승인) | 320 px 및 wide viewport에서 message/status가 save control 위쪽의 현재 viewport 밖에 있도록 scroll한 뒤, (a) successful commit, (b) blank name, (c) stale calculation input, (d) snapshot revision conflict, (e) repository write false, (f) readback mismatch, (g) injected exception을 각각 한 번 발생시킨다. 모든 case에서 final success/error status 전체가 자동으로 현재 viewport 안에 보이고 screen reader에 정확히 한 번 announce된다. (a)만 success와 candidate clear/new active route를 보이며 (b)~(g)는 success 0회, 원인별 redacted actionable failure, candidate와 last-good saved bytes/revision 보존을 보인다. scroll/focus/name/disclosure state 변화, 추가 provider request 또는 자동 retry는 0회다. 자동 QML test는 success/false/exception branch와 scroll target/announcement wiring의 proxy이고 실제 target QField touch/viewport 결과는 별도 사용자 기기 evidence 전까지 `미검증`이다. |
| AC-SRP-065 (2026-09-22 승인) | 동일한 pre-existing generated project fixture와 이 slice를 포함한 FieldBuild Kit로 새 output에 생성한 fixture를 비교한다. 새 output의 `qfield_routes/`만 D-SRP-064~065 behavior를 포함하고 build 완료 summary/help에 D-SRP-066 exact disclosure가 보인다. desktop app rebuild/reinstall만 수행한 pre-existing output은 route files, collected GPKG, route storage와 project settings bytes가 전후 동일하며 새 동작을 포함한다고 주장하지 않는다. 새 output을 QField에 명시적으로 전달해 연 target-device test만 이 slice의 실기 검증으로 기록한다. in-place overwrite/migration과 수집 data deletion은 0회다. |
| AC-SRP-066 (2026-09-22 승인) | candidate가 있고 nonblank route name·valid mapping인 상태에서 save button을 focus하고 disclosure를 펼친 뒤 성공 저장한다. 같은 outcome update에서 candidate는 `null`, 새 route는 active, save button은 disabled, candidate-none exact reason은 visible/accessibility text이며 enabled 예외 상태는 0개다. 최종 success status 전체는 viewport에 보이고 한 번 announce된다. 플랫폼이 disabled button의 `activeFocus`를 clear해도 허용하되, 앱이 focus를 save button에 복구하거나 route-name/disclosure/다른 control로 옮기는 횟수는 0회이고 route name text와 disclosure expanded state는 전후 동일하다. 320 px/light와 wide/dark에서 live visual item order, keyboard traversal 및 accessibility tree는 기본 결과 → fallback notice → `상세 정보`(펼쳐진 내용 포함) → `저장할 경로 이름` → `계산 결과 저장` → disabled reason → outcome status 순서이며 overlap/clipping/horizontal scroll은 0개다. AC-SRP-053/059 의미의 current presentation evidence는 requested markers, provider geometry/metrics/provenance, totals, fallback warning/accessibility와 `상세 정보` 내 endpoint-gap exact line 1개이며, 삭제된 calculation-result/saved-detail/legend object 또는 endpoint-gap line 3개를 요구하지 않는다. 자동 QML 관찰은 proxy이며 실제 target QField touch/screen-reader 결과는 사용자 기기 evidence 전까지 `미검증`이다. |

## 6. API 근거 / 검증 경계
VROOM 근거는 초기 provider가 대상으로 삼은 **v1.14.0 tag**에 고정한다. 공식 문서는 timing을
초 단위로 정의하고 relative planning horizon이면 `arrival`도 그 시작 기준이라고 명시한다.
초기 provider 계약에 절대 epoch가 없으므로 D-SRP-009는 이를 `relative_seconds`로 정규화한다.
- https://github.com/VROOM-Project/vroom/blob/v1.14.0/docs/API.md

openrouteservice 공식 directions 문서는 GeoJSON route feature의 `properties.segments`를 waypoint 사이
section(distance/duration/steps) 목록으로, geometry waypoint index를 별도의 route-level
`properties.way_points`로 정의한다. FR-SRP-033은 이 구조를 따르며 segment 내부의 비문서화 index를
가정하지 않는다. 같은 공식 FAQ는 directions의 입력 start/end가 routable road에서 멀면 기본 최대
350 m 범위 안에서 point를 찾고, 그 범위에도 graph point가 없을 때 `Could not find point`가 된다고
설명한다. 따라서 D-SRP-060은 requested coordinate와 route geometry endpoint의 1 m 일치를 ORS response
contract로 만들지 않고, 공식 response의 geometry/summary/segment/route-level `way_points`를 provider
graph 구간의 권위값으로 사용한다.
- https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/requests-and-return-types
- https://giscience.github.io/openrouteservice/frequently-asked-questions

openrouteservice 공식 snapping 문서는 profile별 graph edge로 point를 snap하고 지정 반경에 적합한
edge가 없으면 input 순서의 `null`을 반환한다고 정의한다. request body는 `locations`와 필수 `radius`를
직접 받으며 endpoint configuration은 한 request의 location batch limit를 문서화한다. hosted API
reference와 2026 endpoint migration 표는 `api.heigit.org/openrouteservice/v2/snap`을 공개 endpoint로
포함한다. D-SRP-050은 original site 좌표만 한 ordered batch로 보내고 configured radius를 그대로
사용한다. provider가 radius를 거부·제한하거나 documented batch limit를 넘는 경우 오류를 그대로
드러내며 추가 snap input 생성, 자동 반경 축소 또는 별도 후보 탐색으로 우회하지 않는다. live hosted limit과
QField transport 동작은 O-SRP-002 검증 대상으로 남긴다.
- https://giscience.github.io/openrouteservice/api-reference/endpoints/snapping/
- https://giscience.github.io/openrouteservice/frequently-asked-questions
- https://openrouteservice.org/dev/
- https://openrouteservice.org/restrictions/

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

2026-09-16 navigation 정합 근거: NAVER guide는 `/navigation` destination parameter, 필수
`appname`, Android package, iOS App Store ID와 설치 fallback 책임을 명시한다. QField official
plugin snippet은 `Qt.openUrlExternally` 사용을 지원한다. Qt contract에서 `true`는 OS open 요청
성공일 뿐 외부 app 실행이나 URL 수락 결과는 아니다.
- https://guide.ncloud-docs.com/docs/maps-url-scheme
- https://github.com/opengisch/QField/blob/master/docs/snippets.md
- https://doc.qt.io/qt-6/qdesktopservices.html#openUrl
- https://github.com/opengisch/QField/blob/master/CMakeLists.txt

**2026-09-17 승인 정합:** 같은 NAVER 공식 문서는 Android mobile app/in-app/mobile-web
context의 package-bound intent handling과 Google Play fallback, iOS의 direct `nmap` scheme,
`LSApplicationQueriesSchemes` host requirement와 App Store fallback을 서로 다른 절차로 제시한다.
FR-SRP-037은 generated project가 host manifest capability를 만들 수 있다고 가정하지 않으며,
navigation web URL은 공식 문서가 해당 context에 명시한 경우에만 채택한다.

**2026-09-18 iOS 변경 근거:** Qt 공식 `QDesktopServices::openUrl` 문서는 iOS에서 application이
query할 custom URL scheme을 host application의 `Info.plist` `LSApplicationQueriesSchemes`에 선언해야
한다고 명시한다. FieldBuild Kit의 generated project plugin은 QField host bundle manifest를 수정하지
않으므로 `nmap` false 반환을 NAVER Maps 미설치로 해석할 수 없고, false 뒤 App Store를 자동 실행하면
실제 설치 상태와 모순될 수 있다. Apple 공식 unified Maps URL은 iOS 18.4 이상에서 `/directions`의
`destination`에 address, place name 또는 latitude,longitude coordinate를 받고 `mode=driving`을 지원한다.
공식 directions parameter 표에는 destination display-name parameter가 없으므로 D-SRP-056/FR-SRP-053은
이름을 URL에 넣지 않고 exact coordinate를 destination으로 쓴다. target iOS/QField/device에서 URL이
Apple Maps로 handoff되고 exact 목적지와 차량 길안내를 표시하는지는 AC-SRP-055의 필수 사용자 기기
검증이며 자동 launcher true만으로 PASS하지 않는다.
- https://developer.apple.com/documentation/mapkit/unified-map-urls
- https://doc.qt.io/qt-6/qdesktopservices.html#openUrl

실제 QField/iOS Apple Maps와 Android NAVER Maps 실행 검증은 AGENTS.md에 따라 사용자 수행 항목이다.
자동 QML/JS 검사를 실기 검증으로 기록하지 않는다. 서버 실호출 미실행도 구분한다.

**2026-09-17 승인 증거 경계:** route-name control에 `editable`, focus 또는 input-method 관련
property가 있고 테스트 driver가 text를 주입할 수 있다는 사실은 AC-SRP-042의 자동 proxy다. 그것만으로
Android/iOS soft keyboard가 실제로 열렸다고 판정하지 않는다. generated `.qgs`에 label expression,
placement와 white buffer가 있다는 사실은 AC-SRP-044의 자동 proxy다. 그것만으로 QField map canvas에서
point/line/polygon label이 실제로 보인다고 판정하지 않는다. 수동 증거에는 QField/OS version,
device, project fixture, zoom/basemap, 수행한 gesture와 관찰 결과를 함께 기록한다.

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
- **O-SRP-008 (2026-09-16 해결):** 이해관계자가 D-SRP-031~035, FR-SRP-029~033,
  AC-SRP-031~035와 `docs/ui-design-guidelines.md`의 같은 UI convention을 승인했다. 이 slice는
  approved baseline을 확장하며 acceptance 산출물과 구현은 아직 이 승인을 반영·검증하지 않았다.
- **O-SRP-009 (실기 검증 대기):** 실제 QField line 조사지의 현재 실패는 재현됐지만 corrected
  provider parsing은 검증되지 않았다. Point와 Polygon은 아직 수동 확인되지 않았고 MultiPoint/
  MultiLineString/MultiPolygon도 별도 증거가 필요하다. 자동 fixture와 실제 QField 결과를 구분한다.
- **O-SRP-010 (실기 검증 대기; 2026-09-17 명세 승인 비차단):** target QField Android host가 NAVER의
  package-bound `intent://`를 `Qt.openUrlExternally`로 직접 처리하는지는 실제 기기와 당시 공식 문서로
  확인한다. 기존 iOS `nmap` whitelist와 automatic store/web fallback 검증 질문은 승인된 D-SRP-056과
  O-SRP-014의 Apple Maps handoff 검증으로 supersede된다. 지원하지 않는 branch에는 추정 URL을 추가하지
  않고 actionable install/host 안내로 끝낸다.
- **O-SRP-011 (2026-09-17 명세 승인·실기 검증 대기):** D-SRP-042~045, FR-SRP-040~043,
  NFR-SRP-005 및 AC-SRP-042~045는 이해관계자 승인을 받았다. 요구 의미에 미결정 제품 질문은 없으며,
  soft keyboard와 rendered map label은 NFR-SRP-005에 따라 target QField 기기 검증 전까지
  PASS가 아니라 **NOT RUN (`미검증`)**이다.
- **O-SRP-012 (2026-09-18 해결·명세 승인):** 이해관계자가 provider HTTP 오류 세부정보의
  D-SRP-049, FR-SRP-047, NFR-SRP-007 및 AC-SRP-049를 승인했다. 이 명세 승인은 기존 endpoint,
  authentication 또는 key 저장/노출 금지 계약을 바꾸지 않으며, fresh test-designer의
  acceptance/traceability 정합과 그 산출물의 별도 승인은 아직 필요하다.
- **O-SRP-013 (2026-09-18 해결·명세 승인, 실기 검증 대기):** 이해관계자가 D-SRP-050~055,
  FR-SRP-048~052, NFR-SRP-008~009 및 AC-SRP-050~054의 mixed vehicle/walking 계약을 승인했다.
  승인된 제품 결정은 default 2 km/허용 0.35~5 km를 radius로 쓰는 original-site ordered single snap
  batch, input-order access point, 모든 stop의 out-and-back, provider foot path 우선, explicit no-path의
  straight-line lower-bound+time unavailable, schema 3과 fallback save acknowledgement다. origin은 기존
  동작과 vehicle-routable 조건을 유지하고 이 slice에서는 자동 snap 또는 origin walking leg를 만들지
  않는다. acceptance/traceability 정합과 승인은 별도 단계이며, hosted snap/foot-hiking의 live quota,
  QField transport와 실제 산간 fixture는 O-SRP-002와 함께 **NOT RUN (`미검증`)**이다.
- **O-SRP-014 (2026-09-18 명세 승인·실기 검증 대기):** 이해관계자가 D-SRP-056, FR-SRP-053 및
  AC-SRP-055의 iOS NAVER Maps/App Store fallback을 Apple Maps HTTPS/no-fallback으로 바꾸는 계약을
  승인했다. Android의 package-bound NAVER intent와 Google Play fallback은 기존 승인 계약 그대로다.
  target iOS/QField에서 official HTTPS URL이 Apple Maps의 exact next-stop driving destination으로
  handoff되는지, target Android/QField에서 package-bound NAVER intent가 exact destination을 받는지는
  각각 사용자 기기 검증 전까지 PASS가 아니라 **NOT RUN (`미검증`)**이다. unified Apple Maps URL의
  공식 최소 OS와 실제 target OS/QField version을 함께 기록한다. iOS 지원 밖 host를 성공으로 주장하거나
  store/web fallback으로 우회하지 않으며 Android 검증은 기존 fallback을 포함한다.
- **O-SRP-015 (2026-09-19 CLOSED — 사용자 승인됨):** reviewer blockers 중 제품 명세상 실제
  ambiguity/conflict는 empty/settings-only schema 경계, mixed save 때 unrelated legacy route 보존 표현,
  persistent `show_route_line`과 toggle settings-write 금지의 충돌뿐이다. D-SRP-058~059,
  FR-SRP-055~056 및 AC-SRP-057~058은 이를 정합하는 승인 기준이다.
  callback evidence, product cold-start recovery, 모든 visit의 accessibility 및 exact Apple Maps error copy는
  각각 기존 acceptance/product 요구의 conformance 문제이므로 새 ID를 만들지 않았다.
- **O-SRP-016 (2026-09-21 해결·명세 승인):** ORS directions가 request coordinate를 routing graph에
  snap하는데도 mapped geometry endpoint 일치를 강제한 문제는 D-SRP-060, FR-SRP-057 및 AC-SRP-059의
  Category B clarification으로 정합했다. 이 승인 기준은 schema 3 또는 provenance enum을 늘리지 않고 provider
  graph 구간과 requested marker의 의미를 분리한다. acceptance 산출물은 별도 단계에서 정합하고 승인받아야 한다.
- **O-SRP-017 (2026-09-22 해결·명세 승인):** D-SRP-062~063, FR-SRP-059~060,
  NFR-SRP-010 및 AC-SRP-061~062는 optional Matrix diagnostic과 independent-app credential namespace의
  현재 계약을 구체화하며 2026-09-22 사용자가 승인했다. fresh test-designer가 acceptance/traceability를
  별도 작성하고 그 산출물도 별도 승인받아야 한다. 이 명세 승인은 기존 acceptance 산출물을 변경하거나
  그 변경을 미리 승인하지 않는다.
- **O-SRP-018 (2026-09-22 해결·명세 승인):** D-SRP-064~066, FR-SRP-061~063,
  NFR-SRP-011 및 AC-SRP-063~065는 fallback을 선택 옵션처럼 보이게 하던 acknowledgement와 save gate를
  제거하고 exact visible notice와 default-collapsed `상세 정보`로 단순화한다. 같은 ID의 이전 DRAFT
  acknowledgement 제안을 대체하며, D-SRP-054/061, FR-SRP-050/058 및 AC-SRP-051/053/060의
  acknowledgement 요구만 supersede한다. D-SRP-060, FR-SRP-057, NFR-SRP-009 및 AC-SRP-059의 복잡한
  기술 문구 표시 위치는 단일 disclosure로 좁힌다. fallback provenance·warning·시간 사용 불가, 모든 save
  outcome의 viewport/accessibility feedback, 저장 atomicity/last-good 및 project-local route runtime의
  배포 경계는 유지한다. 실제 기기 persistence failure의 원인을 단정하지 않는다. fresh
  test-designer가 acceptance/traceability를 정합하며, 그 산출물도 별도 승인이 필요하다.
- **O-SRP-019 (2026-09-22 해결·명세 승인):** D-SRP-067, FR-SRP-064,
  NFR-SRP-012 및 AC-SRP-066은 save success 후 candidate-none disabled 규칙이 focus 보존보다
  우선함, enabled-state 예외 금지, application-initiated focus transfer 금지, route name/disclosure
  보존과 exact semantic order를 명확히 한다. QML reading order 오류는 NFR-SRP-011의 Category A
  conformance defect로 남으며 새 제품 요구로 분류하지 않는다. D-SRP-064에 반하는
  AC-SRP-053/059의 기존 presentation acceptance 규칙과 AC-SRP-064의 save-button
  active-focus 동일성 규칙은 fresh test-designer가 정합하고 별도 승인을
  받아야 한다.

### 승인된 slice의 acceptance 정합 범위

**승인된 clarification acceptance 정합 범위:** fresh test-designer는
**D-SRP-067 / FR-SRP-064 / NFR-SRP-012 / AC-SRP-066**을 기준으로 최소한 다음 현재
acceptance 산출물을 정합한다: `tests/acceptance/survey_route_planner/test_survey_route_planner.py`의
AC-SRP-059 three-disclosure 및 AC-SRP-064 success-focus assertion,
`tests/acceptance/survey_route_planner.test-design.md`의 AC-SRP-053/059 presentation·AC-SRP-064 focus 설계,
`tests/acceptance/survey_route_planner.traceability.md`의 해당 evidence mapping,
`tests/acceptance/survey_route_planner/HARNESS_CONTRACT.md`의 three-object/focus observation 계약,
`tests/acceptance/survey_route_planner/verify_design.py`의 해당 guard, 그리고
`tests/acceptance/survey_route_planner/route_ui_simplification_qml_driver.py`의 disabled/focus/semantic-order
관찰. 지워진 presentation object와 endpoint-gap line 3개를 다시 만들어 test를 맞추지 않는다.
acceptance 외 implementation support driver에 같은 구 관찰이 남아 있다면 test-designer는
요구 evidence만 기록하고, 승인된 test 산출물을 받은 implementer가 이를 정합한다.
현재 해당 파일에는 `tests/unit/survey_route_qml_driver.py`의 `endpoint_gap_disclosures`
three-object 관찰이 포함된다. 이 명세
승인은 저 acceptance 파일을 수정하거나 수정 내용을 미리 승인하지 않는다.

2026-09-22 승인된 저장 설명/feedback slice에 따라 fresh test-designer는 **D-SRP-064~066,
FR-SRP-061~063, NFR-SRP-011 및 AC-SRP-063~065**를 기준으로
fallback exact notice·acknowledgement control 0개·fallback과 무관한 save enablement, 기본 접힘
`상세 정보`와 endpoint-gap line 1개 제한, 모든 save true/false/exception의 viewport 이동·단일 announcement·state 보존,
새 output과 기존 embedded project의 deployment boundary를 각각 독립 test item으로 추가한다. 실제
target QField save와 scroll/touch 결과는 자동 source inspection만으로 PASS 처리하지 않는다.

2026-09-21 명세 승인에 따라 fresh test-designer는 **D-SRP-060, FR-SRP-057 및 AC-SRP-059**를 기준으로 requested endpoint에서 1 m보다
멀리 snap되고 provider distance가 requested geodesic보다 짧지만 documented GeoJSON/way_points/metric은
유효한 fixture, way_points/structure/metric negative fixture, schema-3 exact roundtrip과 provider-only
geometry/UI disclosure를 acceptance design/traceability에 추가한다. 이 명세 승인은 acceptance 파일을
수정하거나 그 변경을 미리 승인하지 않는다.

2026-09-18 iOS 지도 변경 명세 승인에 따라 새 test-designer는 **D-SRP-056, FR-SRP-053 및
AC-SRP-055**를 acceptance design/traceability에 추가하고, 기존 AC-SRP-025/039의 iOS NAVER 및
App Store fallback 기대만 명시적 supersession으로 바꾼다. canonical coordinate,
platform-neutral label, iOS exact Apple Maps HTTPS URL, Android exact package-bound NAVER intent,
Android의 기존 Google Play fallback, launcher true/false/exception의 honest status와 iOS fallback/write
0회, target-device handoff를 각각 독립
항목으로 둔다. 이 문서는 acceptance 파일을 수정하거나 그 변경을 미리 승인하지 않는다.

2026-09-18 명세 승인에 따라 새 test-designer는 **D-SRP-049~055, FR-SRP-047~052,
NFR-SRP-007~009, AC-SRP-049~054**를 acceptance design/traceability에 추가한다. 특히
original-coordinate snap batch와 radius/provider-error 경계, origin non-snapping, all-stop out-and-back,
mapped/unmapped walking provenance, schema-3 compatibility,
partial-stage failure/redaction과 target-QField legend/style evidence를 독립적으로 검사한다. 이 문서는 현재
acceptance 파일을 수정하거나 그 변경을 미리 승인하지 않는다.

새 test-designer는 승인된 이력을 보존하면서
**D-SRP-031~035, FR-SRP-029~033, AC-SRP-031~035**를 acceptance test design과 traceability에
추가한다. 특히 target option population-before-validation, selected/all/uncompleted exact candidate set,
route-level `properties.way_points` leg slicing, provider/client error category와 여섯 geometry family의
동일 response acceptance를 독립적으로 검사한다. 이 문서는 acceptance 파일을 수정하거나 승인하지 않는다.

2026-09-17 명세 승인 뒤 새 test-designer는 **D-SRP-036~041, FR-SRP-034~039,
NFR-SRP-004, AC-SRP-036~041**을 acceptance design/traceability에 별도로 추가한다. 특히 name-only
save, key source와 snapshot exclusion, actual settings slot feedback, platform-specific NAVER dispatch,
next-in-order completion, polygon accent와 name-field halo를 독립적으로 검사한다.

2026-09-17 명세 승인 뒤 새 test-designer는 **D-SRP-042~045, FR-SRP-040~043,
NFR-SRP-005, AC-SRP-042~045**를 acceptance design/traceability에 추가한다. keyboard/label render는
자동 proxy와 실제 QField 수동 criterion을 별도 test item/evidence column으로 나누고, 정적 문자열 검사를
수동 PASS에 연결하지 않는다. name-field missing/value-empty/ID-missing, 여섯 geometry type, multipart
one-label-per-feature, Step 7의 네 key/consent 상태를 각각 fixture로 둔다.

2026-09-16 명세 승인 뒤 새 test-designer는 기존 artifact를 보존하면서
**FR-SRP-021~028, D-SRP-020~030, NFR-SRP-001~003, AC-SRP-021~030**을 정합한다.
FR-SRP-006/010의 remaining recalculation 기대는 D-SRP-023의 supersession으로 바꾸고 schema 1
fixture를 보존한 채 schema 2 leg/progression fixture를 추가한다. Android/iOS Naver 검증은 OS
dispatch와 app-internal acceptance를 분리한다.

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
승인된 기준본 및 이번 slice의 2026-09-17 이해관계자 승인 유지 → 새 test-designer 정합 → acceptance 산출물 승인 →
새 implementer 정합 → 검사 → 새 reviewer. 이번 문서 정합에서 앱 테스트·실서비스·QField 기기 검사를 실행하지
않았고 implementation attempt 2의 기존 104 passed/2 failed/12 skipped를 최종 PASS로 승격하지 않는다.
