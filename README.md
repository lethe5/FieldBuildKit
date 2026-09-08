# FieldBuild Standalone

**한국어** · [English](README.en.md)

QGIS Desktop을 설치하지 않고 **QField 현장 생태조사 프로젝트를 만드는 데스크톱 앱**입니다.
한국어 마법사에서 조사 유형, 배경지도, 선택 참조 자료를 설정하면 조사 폼과 관계가 구성된
프로젝트 폴더를 생성합니다. 이 문서는 **앱 0.2.7**을 기준으로 합니다.

▶ [웹 발표자료에서 주요 기능과 사용 흐름 보기](https://lethe5.github.io/fieldbuild_standalone/)

## 설치 및 실행

배포 파일은 [GitHub Releases](https://github.com/lethe5/fieldbuild_standalone/releases)의
해당 버전에 첨부된 파일을 확인하세요. 운영체제와 CPU 종류에 맞는 파일을 선택합니다.
GitHub의 `Source code` 압축파일은 실행 앱이 아닌 소스 코드입니다.

- **macOS**: 배포 압축파일을 풀고 `FieldBuild Standalone.app`을 응용 프로그램 폴더로
  옮긴 뒤 실행합니다. 현재 로컬 빌드 검증 환경은 Apple Silicon(ARM64)입니다.
- **Windows**: Windows 배포 파일이 제공되는 버전에서는 압축을 푼 폴더 전체를 유지한 채
  `FieldBuild Standalone.exe`를 실행합니다. `_internal` 폴더를 포함해야 하며 `.exe`만
  옮기면 실행되지 않습니다. Windows용 빌드 방법은 아래에 있으며, 실제 배포·검증 여부는
  해당 릴리스 안내를 확인하세요.

배포 앱을 사용하는 경우 **Python, QGIS Desktop, GDAL을 별도로 설치할 필요가 없습니다.**
현재 macOS 빌드는 배포용 개발자 서명·공증을 받지 않았습니다. 개발자 확인 경고로 실행이
차단되면 출처를 확인한 뒤 [Apple의 앱 열기 안내](https://support.apple.com/ko-kr/102445)를
따르세요.

현장에서 프로젝트를 열 기기에는 **QField를 별도로 설치**해야 합니다.
[QField 공식 설치 안내](https://docs.qfield.org/get-started/)에서 Android·iOS·데스크톱용
설치 방법을 확인할 수 있습니다.

## 프로젝트 만들기

1. **프로젝트 기본 정보**: 이름, 저장할 상위 폴더, 좌표계 등을 설정합니다.
2. **조사 유형**: 아래 네 가지 중 조사 목적에 맞는 유형을 선택합니다.
3. **사이트/조사구 입력**: 필요한 경계를 그리거나 로컬 공간 자료를 업로드합니다.
   단순 종 목록조사는 이 단계를 건너뜁니다.
4. **연결 상태 및 배경지도**: 배경지도 없음, 온라인 VWorld, 오프라인 VWorld 중 선택합니다.
5. **사진 기반 식별 및 참조 자료**: Pl@ntNet 사용 여부를 설정하고, 필요하면 식물 분류표와
   출현확률 TIFF를 선택합니다. 참조 자료 없이도 프로젝트를 생성할 수 있습니다.
6. **기호 스타일**: 포인트 기호를 설정합니다. 식생 매핑에서는 이 단계를 건너뜁니다.
7. **검토 및 생성**: 설정을 확인하고 프로젝트 폴더를 생성합니다.

| 조사 유형 | 기록 방식 |
| --- | --- |
| 단순 종 목록조사 | 사이트 경계 없이 관찰 위치와 종 정보를 포인트로 기록 |
| 정해진 사이트에서의 임시 조사구 | 사이트 → 조사 → 관찰 구조로 조사 지점과 종별 피도를 기록 |
| 정해진 사이트에서의 고정 조사구 | 사이트 → 고정 조사구 → 조사 → 관찰 구조로 반복 방문 기록 |
| 식생 매핑 | 사이트 → 조사 → 군락 구조로 식생을 폴리곤으로 기록 |

## 식물 분류 참조 자료 — 선택 사항

5단계에서 **이명정보를 포함한 국가생물종목록(관속식물류) Excel `.xlsx` 파일**을 업로드합니다.
파일을 선택하면 미리보기와 검증을 진행하고, 유효한 자료는 자동 적용합니다.
잘못된 파일은 다시 선택하거나 선택을 해제해야 다음 단계로 진행할 수 있습니다.

> **주의: 참조 자료를 업로드하면 식물 이름은 국가생물종목록에 있는 정명만 입력할 수 있습니다.**

- **분류표가 있을 때**: 정명 선택에 따른 학명·KTSN 조회를 사용합니다. KTSN 필드는
  종 관찰을 기록하는 유형에서 생성됩니다.
- **분류표가 없을 때**: 국명·학명을 직접 입력하며 **KTSN 필드는 생성하지 않습니다.**
  Pl@ntNet은 KTSN 연결 없이 학명 후보를 제공합니다.
- **샘플 다운로드**: 앱의 `가상 샘플 Excel 다운로드...` 버튼으로 입력 구조를 확인할 수 있습니다.
  [동일한 샘플 파일](resources/samples/taxonomy_sample.xlsx)도 저장소에 포함되어 있습니다.
  `Data Sheet`는 23개 열과 2개 머리글 행으로 구성됩니다. 정명 2개·이명 1개의 **가상 데이터**이며,
  `안내` 시트를 읽고 사용하세요. 샘플은 프로젝트에 자동으로 적용되지 않습니다.

원본 Excel은 프로젝트에 복사하지 않습니다. 선택한 자료에서 생성한 조회 테이블과 출처 정보만
프로젝트에 포함합니다. 검증 후 원본 파일이 바뀌면 다시 업로드해야 합니다.

## 출현확률 TIFF — 선택 사항

**Pl@ntNet 사진 식별을 켜고 유효한 식물 분류 참조 자료를 업로드한 경우에만** TIFF 폴더
선택 항목이 나타납니다. 두 조건 중 하나를 해제하면 선택했던 TIFF 경로도 지워집니다.
TIFF를 선택하지 않아도 프로젝트 생성과 사진 식별은 가능하며 출현확률 조회만 생략합니다.

- 선택 폴더와 하위 폴더에서 `.tif`·`.tiff` 파일을 찾습니다. 확장자 대소문자는 구분하지 않습니다.
- **파일명에 업로드한 분류표의 국명이 포함되어야 합니다.** 예: `소나무.tif`,
  `지역_소나무_2026.tiff`. `bce_inverse_corrected_probability_` 같은 고정 접두사는 필요 없습니다.
- 이름이 겹치면 더 구체적인 국명을 사용합니다. 서로 다른 국명이 한 파일명에 함께 있거나,
  같은 종의 파일이 여러 개이면 오류로 안내합니다. 분류표 국명과 일치하지 않는 파일은 제외합니다.
- 각 TIFF는 **단일 밴드**여야 하며 크기·격자·좌표계·자료형이 같아야 합니다.
- **NoData는 `-9999` 또는 `NaN`을 허용**하고 두 종류를 섞어서 입력할 수 있습니다.
  생성 시 NaN 셀을 `-9999`로 통일하며 나머지 값과 원본 파일은 유지합니다.

선택한 TIFF는 프로젝트 내부의 다중밴드 TIFF로 구성됩니다. 전체 국가생물종목록, 확률 TIFF,
`storage/` 캐시는 앱과 Git에 포함되지 않습니다. 앱 용량에는 Qt 화면 구성 요소와 GIS 처리
라이브러리가 포함되므로, 참조 자료를 제외해도 실행 앱 자체에는 일정한 용량이 필요합니다.

## API 키와 인터넷 연결

| 기능 | 필요한 항목 |
| --- | --- |
| 온라인 VWorld 배경지도 | VWorld API 키, 사용 시 인터넷 연결 |
| 오프라인 VWorld 배경지도 | 생성 시 VWorld API 키와 인터넷 연결; 생성한 영역·줌 범위는 현장에서 오프라인 사용 |
| Pl@ntNet 사진 식별 | Pl@ntNet API 키, 식별 요청 시 인터넷 연결 |
| 로컬 출현확률 조회 | 위 조건으로 프로젝트에 포함한 TIFF; 래스터 조회 자체에는 인터넷 불필요 |

`이 키 기억하기`를 선택하면 API 키를 이 컴퓨터의 암호화 저장소에 보관합니다. 앱에서 설정한
비밀번호로 잠금을 해제하며, 비밀번호를 잊으면 이전에 저장한 키를 복구할 수 없습니다.

**컴퓨터의 암호화 저장과 프로젝트에 키를 포함하는 것은 별개입니다.** 동의하여 프로젝트에
포함한 온라인 VWorld·Pl@ntNet 키는 프로젝트 폴더를 받는 사람이 읽을 수 있습니다.
Pl@ntNet 키 포함에 동의하지 않아도 식별 기능은 유지되지만, 사용하려면 QField에서 키를
직접 설정해야 합니다. 사진 식별을 요청하면 해당 사진이 Pl@ntNet 서비스로 전송됩니다.

## QField로 이동 및 리포트 출력

생성된 **프로젝트 폴더 전체**를 QField 기기로 복사한 뒤 폴더 안의 `.qgs` 파일을 엽니다.
`.qgs`나 `.gpkg`만 따로 옮기지 마세요. 이 앱의 프로젝트는 **QFieldSync로 다시 패키징하지 않습니다.**
현장 조사 후에도 QField에서 프로젝트를 닫고 폴더 전체를 컴퓨터로 복사합니다.
자세한 이동 방법은 각 프로젝트의 `README_TRANSFER_KO.md`에 있습니다.

프로젝트에는 다음 파일이 들어갑니다. 선택 기능에 따라 일부 폴더가 추가됩니다.

```text
프로젝트 폴더/
├── 프로젝트.qgs             # QField에서 열 파일
├── 프로젝트.qml             # 프로젝트 기능과 리포트 도구
├── data/                    # 조사 데이터 GeoPackage
├── attachments/             # 첨부 사진
├── icons/                   # 도구 아이콘
├── reference/               # 선택한 분류·확률 참조 자료
├── basemap/                 # 선택한 오프라인 배경지도
├── MANIFEST.json            # 프로젝트 구성 정보
├── VALIDATION_REPORT.json   # 생성 시 검증 결과
└── README_TRANSFER_KO.md    # 기기 간 이동 안내
```

QField의 **HTML 보고서 내보내기** 기능은 프로젝트 폴더에 `프로젝트_report.html`과
`프로젝트_joined.csv`를 저장합니다. HTML의 통합표를 검색·정렬하고 CSV로 추가 다운로드할 수 있습니다.
통합표와 CSV는 한국어 열 이름을 사용하며 UUID·외래 키·무결성 상태 표시 열을 제외합니다.
관계 연결과 누락 진단에 필요한 내부 식별자는 유지합니다.

최종 geometry가 포인트인 행에는 **WGS84 십진수 위도·경도(소수점 8자리)**를 제공합니다.
좌표가 없거나 변환할 수 없으면 빈 값으로 두며, 폴리곤에서 임의의 중심점 좌표를 만들지 않습니다.
앱 업데이트는 **새로 생성하는 프로젝트에 적용**됩니다. 기존 프로젝트는 자동 변경되지 않습니다.

## 소스 코드로 실행 및 빌드

개발자용 절차입니다. 프로젝트의 Python 요구 조건은 **3.10 이상**이며, 현재 로컬 검증 환경은
Python 3.12입니다. 저장소를 내려받은 폴더에서 실행하세요. `storage/`나 개인 참조 자료는 필요 없습니다.

### macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[ui,dev,packaging]'
.venv/bin/fieldbuild-standalone

# 배포 앱 생성 및 실행 환경 검사
.venv/bin/python packaging/build_app.py
```

출력은 `dist/FieldBuild Standalone.app`입니다. `dist/FieldBuild Standalone/`은 별도 빌드 산출물이므로
macOS 앱 배포에 함께 넣지 않아도 됩니다. `bash packaging/build_macos_app.sh`도 같은 빌드 절차를 실행합니다.

### Windows PowerShell

```powershell
py -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -e ".[ui,dev,packaging]"
.\.venv-win\Scripts\fieldbuild-standalone.exe

# Windows 환경에서 직접 빌드
.\.venv-win\Scripts\python.exe packaging/build_app.py
```

출력인 `dist/FieldBuild Standalone/` 폴더 전체를 배포합니다. 다른 운영체제에서 만든 가상환경을
복사하지 말고, 배포할 운영체제에서 새로 환경을 구성하세요.

빌드는 매번 새 PyInstaller 작업 폴더에서 진행하고, 완성된 실행 파일의 `--check-runtime` 검사를
수행합니다. 참조 데이터 준비나 별도 `QPB_*` 환경변수는 필요하지 않습니다.

### 개발 검증

macOS에서 관련 자동 검사는 다음과 같이 실행할 수 있습니다. 생성된 리포트 JavaScript를
검사하는 테스트에는 `node` 실행 파일도 필요합니다.

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/unit/test_optional_reference_inputs.py tests/unit/test_standalone.py tests/unit/test_probability_raster_cache.py tests/unit/test_wizard_ui_layout.py tests/unit/test_file_dialog_navigation.py tests/acceptance/qfield_project_builder/test_fieldbuild_kit_qfield_html_report_refresh.py
```

앱의 구조 검사와 자동 테스트는 실제 기기에서의 QField 검증과 구분합니다. 일부 DPI·모바일
검사는 별도 환경이 필요하며, 과거 전체 테스트에는 알려진 실패가 남아 있습니다.
[검증 기록](docs/qfield-runtime-verification.md)에서 통과 범위와 제한을 확인하세요.

## 추가 문서 및 문의

- [영어 README](README.en.md)
- [독립 실행 구현 및 변경 기록](docs/standalone.md)
- [앱 분리 배경](docs/independence.md)
- [검증 기록](docs/qfield-runtime-verification.md)
- [문제 신고](https://github.com/lethe5/fieldbuild_standalone/issues): 앱·운영체제·QField 버전과
  재현 순서를 적어 주세요. API 키와 개인정보가 포함된 자료는 공개 게시하지 마세요.

`specs/`와 과거 acceptance 문서에는 이전 구현의 요구 사항도 남아 있습니다.
현재 사용자 동작은 이 README와 최신 변경 기록을 우선 참고하세요.
