#!/usr/bin/env python3
"""Build from freshly prepared reference data on the current operating system."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_reference_bundle import validate_prepared_reference

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "FieldBuild Standalone"


def main() -> int:
    canonical = Path(os.environ.get(
        "QPB_CANONICAL_REFERENCE_SOURCE",
        REPO_ROOT / "packaging/reference_source/tables/Rpt_2026-08-29_List.xlsx",
    )).resolve()
    rasters = Path(os.environ.get(
        "QPB_REFERENCE_RASTER_DIR",
        REPO_ROOT / "storage/reference/rasters/bce_inverse_corrected_probability_maps",
    )).resolve()
    if not canonical.is_file() or not rasters.is_dir():
        raise SystemExit(
            "빌드 원본이 없습니다. canonical workbook과 개별 TIFF 폴더를 준비하세요.\n"
            f"Workbook: {canonical}\nTIFF: {rasters}"
        )
    build_dir = REPO_ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    # Never trust caches, build outputs, or environment paths copied from another machine.
    with tempfile.TemporaryDirectory(prefix="fieldbuild-", dir=build_dir) as temporary:
        workspace = Path(temporary)
        reference = workspace / "reference"
        print("현재 원본에서 참조 자료와 다중밴드 캐시를 새로 생성합니다...", flush=True)
        subprocess.run([
            sys.executable, str(REPO_ROOT / "packaging/prepare_reference_bundle.py"),
            "--canonical-workbook", str(canonical), "--raster-dir", str(rasters),
            "--source-manifest",
            str(REPO_ROOT / "packaging/reference_source/canonical_source_manifest.json"),
            "--destination", str(reference),
        ], cwd=REPO_ROOT, check=True)
        validate_prepared_reference(reference)
        environment = os.environ.copy()
        environment["QPB_FILTERED_REFERENCE_ROOT"] = str(reference)
        environment["QPB_CANONICAL_REFERENCE_SOURCE"] = str(canonical)
        print("새 캐시 검증 완료. 앱을 패키징합니다...", flush=True)
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
            "--distpath", str(REPO_ROOT / "dist"),
            "--workpath", str(workspace / "pyinstaller"),
            str(REPO_ROOT / "packaging/qfield_builder.spec"),
        ], cwd=REPO_ROOT, env=environment, check=True)

    if sys.platform == "darwin":
        output = REPO_ROOT / "dist" / f"{APP_NAME}.app"
        binary = output / "Contents/MacOS" / APP_NAME
        resources = output / "Contents/Resources"
    else:
        output = REPO_ROOT / "dist" / APP_NAME
        binary = output / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
        resources = output / "_internal"
    validate_prepared_reference(resources / "storage/reference")
    subprocess.run([str(binary), "--check-runtime"], cwd=REPO_ROOT, check=True)
    print(f"Built and verified: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
