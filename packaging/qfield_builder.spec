# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FieldBuild Standalone (entry point: ``qfield_builder.ui.app:main``).

Cross-platform by design (per this project's packaging requirement): this spec file itself
contains no macOS-only assumption. The macOS-specific step below -- the ``BUNDLE(...)``
call, which produces a macOS ``.app`` bundle on top of PyInstaller's own OS-agnostic ``EXE``/
``COLLECT`` "onedir" output -- is guarded by ``sys.platform == "darwin"`` and simply does not run
on Windows/Linux, where that same onedir output (a folder containing a native launcher executable)
is already the appropriate, OS-native packaged artifact; no separate Windows-only spec is needed.
Shared build orchestration and output verification live in ``packaging/build_app.py``.
``packaging/build_macos_app.sh`` is a compatibility wrapper for that entry point.

This is an MVP, unsigned, local-test build: no code-signing identity is available in this
environment (see the main README's "Opening an unsigned build on macOS" section), and this spec
deliberately never attempts to sign or notarize anything (``codesign_identity=None`` below is
literal, not a placeholder to fill in later without also updating the README's instructions).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

# This spec file lives at <repo_root>/packaging/qfield_builder.spec. PyInstaller `exec()`s spec
# files without a real `__file__` in scope, but always injects `SPECPATH` (the directory
# containing the spec file itself) into the spec's execution namespace -- that is the documented,
# supported way a `.spec` file is meant to locate itself and its own repository root.
REPO_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - PyInstaller-injected spec global.
# FR-QPB-131 (Decision Log D-81/D-86): "FieldBuild Standalone" supersedes "QField Project Builder" as
# this application's own display name, including the PyInstaller packaging configuration's own
# bundle name.
APP_NAME = "FieldBuild Standalone"
APP_VERSION = "0.2.8"
gis_datas, gis_binaries, gis_imports = [], [], []
for package in ("rasterio", "fiona"):
    package_datas, package_binaries, package_imports = collect_all(package)
    gis_datas.extend(package_datas)
    gis_binaries.extend(package_binaries)
    gis_imports.extend(package_imports)

a = Analysis(
    # A separate bootstrap script, not `qfield_builder/ui/app.py` itself -- see
    # `packaging/entry_point.py`'s own docstring for why (PyInstaller's `Analysis` runs whatever
    # script it is given as a package-less `__main__` module, which breaks `app.py`'s own
    # relative import of `.wizard`).
    [str(REPO_ROOT / "packaging" / "entry_point.py")],
    pathex=[str(REPO_ROOT)],
    binaries=gis_binaries,
    # `resources/` is this application's small, immutable, version-controlled resource directory
    # (see README.md's "File and storage structure") -- bundled here, and resolved at runtime via
    # `qfield_builder.resource_paths` (which consults `sys._MEIPASS` in a packaged build, rather
    # than an `__file__`-relative path that would silently miss the bundled copy once PyInstaller
    # has packaged this application's own Python modules into its own archive format).
    datas=[
        (str(REPO_ROOT / "resources"), "resources"),
    ] + gis_datas + collect_data_files("qfield_builder", includes=["templates/*"]),
    hiddenimports=gis_imports,
    hookspath=[str(REPO_ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    # The desktop UI is Widgets-based. Generated QML runs in QField, not this app.
    excludes=[
        "qgis", "osgeo", "PIL",  # Pillow is used to build icons, not by the runtime UI.
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQml",
        "PySide6.QtVirtualKeyboard",
    ],
    noarchive=False,
)
# Exclude ICU DLLs that conflict with Qt in Windows builds.
if sys.platform == "win32":
    a.binaries = [
        entry
        for entry in a.binaries
        if entry[0].lower() not in {"icuuc.dll", "icudt78.dll"}
    ]

# Keep Korean/English Qt catalogs and omit build-only artwork copies. BUNDLE below
# still installs the actual macOS app icon; the on-screen logo remains in resources.
a.datas = [
    entry for entry in a.datas
    if entry[0].replace("\\", "/") not in {
        "resources/app-icon-glass.icns",
        "resources/fieldbuild-kit-icon.icns",
        "resources/fieldbuild-kit-icon-mark.png",
    }
    and (
        not entry[0].replace("\\", "/").startswith((
            "PySide6/Qt/translations/", "PySide6/translations/",
        ))
        or entry[0].endswith(("_ko.qm", "_ko_KR.qm", "_en.qm", "_en_US.qm", "_en_GB.qm"))
    )
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

# macOS-only: wrap the OS-agnostic onedir COLLECT output above into a real double-clickable
# `.app` bundle. On Windows/Linux, `coll` (the onedir folder produced above) is already the
# packaged artifact for this platform, and this block does not run there.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        # Category D branding decision (`docs/ui-design-guidelines.md`, "Branding: logo asset and
        # its two confirmed uses"): regenerated from only the icon-mark sub-region of
        # resources/fieldbuild-kit-logo.png (never the full wide lockup or the wordmark text) --
        # see packaging/generate_app_icon.py, which produced this file from
        # resources/fieldbuild-kit-icon-mark.png.
        icon=str(REPO_ROOT / "resources" / "fieldbuild-kit-icon.icns"),
        bundle_identifier="kr.re.nie.fieldbuild-standalone",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "FieldBuild Standalone",
        },
    )
