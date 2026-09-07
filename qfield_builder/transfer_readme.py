"""`README_TRANSFER_KO.md` generation (FR-QPB-093).

Korean-language end-user transfer notice: warns against QFieldSync packaging, instructs copying
the entire folder (not just the GeoPackage) to and from the phone, and covers both Android and
iOS in non-technical language.
"""
from __future__ import annotations

from pathlib import Path

README_FILENAME = "README_TRANSFER_KO.md"


def build_readme_transfer_ko(project_display_name: str) -> str:
    return f"""# QField 프로젝트 이동 안내 ({project_display_name})

## 중요: QFieldSync를 사용하지 마세요

이 프로젝트는 QFieldSync로 패키징하지 마십시오. QFieldSync는 UUID 기반의 기본 키/관계 구조를
GeoPackage의 숨겨진 `fid` 기반 구조로 바꾸거나, 외래 키 기반 관계(foreign key relation)를
제거하거나 변경할 수 있습니다. 이 프로젝트 폴더는 QFieldSync 없이 그대로 사용할 수 있도록
이미 준비되어 있습니다.

## 컴퓨터 → 스마트폰

1. 생성된 프로젝트 폴더 전체를 복사하십시오. `.qgs` 프로젝트 파일, `.gpkg`(GeoPackage)
   데이터베이스, `attachments`(첨부 사진) 폴더, 오프라인 배경지도(`basemap`, 있는 경우)를
   포함한 폴더 전체를 반드시 함께 복사해야 합니다. **GeoPackage(.gpkg) 파일만 복사하지
   마십시오.**
2. **Android**: USB 케이블로 연결한 뒤 파일 관리자(또는 QField 앱 내 가져오기 기능)를 사용해
   폴더 전체를 휴대폰의 저장 공간으로 복사하십시오.
3. **iOS**: Finder(또는 iTunes) 파일 공유, AirDrop, 또는 iCloud Drive/파일 앱을 통해 폴더
   전체를 QField 앱이 접근할 수 있는 위치로 복사하십시오.
4. QField 앱에서 복사한 폴더 안의 `.qgs` 프로젝트 파일을 여십시오.

## 현장 조사 후: 스마트폰 → 컴퓨터

1. 현장 조사를 마치면 QField에서 프로젝트를 닫으십시오.
2. 휴대폰에 있는 프로젝트 폴더 **전체**를 다시 컴퓨터로 복사하십시오.
3. 폴더 안의 파일 이름을 바꾸거나, 파일을 다른 위치로 옮기거나, 일부 파일만 복사하지
   마십시오. 파일 구조가 바뀌면 관계와 사진 첨부가 깨질 수 있습니다.
4. 기존 데스크톱 사본을 새 사본으로 교체하기 전에, 안전을 위해 기존 폴더를 백업해 두는 것을
   권장합니다.

## 요약

- QFieldSync를 사용하지 마십시오.
- 항상 프로젝트 폴더 **전체**를 복사하십시오 (GeoPackage만 복사하지 마십시오).
- Android와 iOS 모두 지원됩니다.
- 폴더 내부의 파일 이름을 바꾸거나 이동하지 마십시오.
"""


def write_readme_transfer_ko(project_dir: str, project_display_name: str) -> str:
    path = Path(project_dir) / README_FILENAME
    path.write_text(build_readme_transfer_ko(project_display_name), encoding="utf-8")
    return str(path)
