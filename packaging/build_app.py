#!/usr/bin/env python3
"""Package the app without local reference datasets, then check its runtime."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "FieldBuild Standalone"


def main() -> int:
    build_dir = REPO_ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    # Never trust caches, build outputs, or environment paths copied from another machine.
    with tempfile.TemporaryDirectory(prefix="fieldbuild-", dir=build_dir) as temporary:
        workspace = Path(temporary)
        print("앱을 패키징합니다...", flush=True)
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
            "--distpath", str(REPO_ROOT / "dist"),
            "--workpath", str(workspace / "pyinstaller"),
            str(REPO_ROOT / "packaging/qfield_builder.spec"),
        ], cwd=REPO_ROOT, env={
            **os.environ, "PYINSTALLER_CONFIG_DIR": str(workspace / "cache"),
        }, check=True)

    if sys.platform == "darwin":
        output = REPO_ROOT / "dist" / f"{APP_NAME}.app"
        binary = output / "Contents/MacOS" / APP_NAME
    else:
        output = REPO_ROOT / "dist" / APP_NAME
        binary = output / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    subprocess.run([str(binary), "--check-runtime"], cwd=REPO_ROOT, check=True)
    print(f"Built and verified: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
