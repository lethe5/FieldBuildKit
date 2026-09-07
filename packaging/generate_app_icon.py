#!/usr/bin/env python3
"""Regenerates the packaged macOS app's own icon from the icon-mark sub-region of
``resources/fieldbuild-kit-logo.png`` -- see ``docs/ui-design-guidelines.md``'s "Branding: logo
asset and its two confirmed uses" section, and Decision Log D-81/D-86 (the application rename to
"FieldBuild Standalone") in ``specs/qfield-project-builder.md``.

That guidelines section confirms the logo asset's own composition (a wide, ~3:1 horizontal lockup:
a roughly-square icon mark -- layered map tiles with a location pin -- on the left, and the
"FieldBuild Standalone" wordmark to its right) and requires the regenerated app icon to be cropped from
*only* the icon-mark sub-region, never the full wide lockup and never the wordmark text, but
deliberately leaves the exact crop rectangle/pixel dimensions to the implementer.

``_ICON_MARK_BBOX`` below is that implementer-chosen crop rectangle, *not* an eyeballed guess: it
is the icon mark's own tight, non-transparent pixel bounding box within the 2172x724px source
image, found by directly inspecting that image's alpha channel (every column/row containing any
non-fully-transparent pixel). That inspection also confirmed a clean, unambiguous >=58px-wide
fully transparent gap (source-image columns 437-494) separates the icon mark from the "F" of
"FieldBuild" immediately to its right -- i.e. there is no ambiguity about where the icon mark ends
and the wordmark begins. A fixed padding (`_CROP_PADDING_PX`, comfortably inside that transparent
gap on the icon mark's right edge) is added on every side before squaring the crop around its own
center, so the icon mark's own edges are never cut off tight.

macOS-only, like the sibling ``packaging/build_macos_app.sh``: the final ``.iconset -> .icns``
assembly step below shells out to Apple's own ``iconutil`` command-line tool, which only exists on
macOS. The crop/resize steps use Pillow -- a packaging-time-only dependency (see ``pyproject.
toml``'s ``packaging`` optional-dependency group, ``pip install -e '.[packaging]'``), never a
runtime dependency of the application itself.

Usage:
    packaging/generate_app_icon.py

Output (both under ``resources/``, both version-controlled):
    fieldbuild-kit-icon-mark.png -- the square, cropped icon-mark source image (kept as a
                                     real, inspectable, checked-in intermediate asset, not just a
                                     throwaway temp file).
    fieldbuild-kit-icon.icns     -- the full macOS iconset, referenced by
                                     ``packaging/qfield_builder.spec``'s ``BUNDLE(icon=...)``.

Never touches anything outside this repository's own ``resources/`` directory and a fresh,
self-created ``tempfile.mkdtemp()`` working directory for the intermediate ``.iconset`` folder
(removed again before this script exits).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = REPO_ROOT / "resources" / "fieldbuild-kit-logo.png"
ICON_MARK_PATH = REPO_ROOT / "resources" / "fieldbuild-kit-icon-mark.png"
ICNS_PATH = REPO_ROOT / "resources" / "fieldbuild-kit-icon.icns"

# See this module's own docstring above for how this rectangle was derived: the icon mark's own
# tight, non-transparent bounding box within the 2172x724px source logo -- (left, top, right,
# bottom), right/bottom exclusive, in source-image pixel coordinates.
_ICON_MARK_BBOX = (81, 157, 436, 509)
_CROP_PADDING_PX = 16

# The standard macOS .iconset filename/pixel-size pairs `iconutil -c icns` requires.
_ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def _square_crop_icon_mark(logo: Image.Image) -> Image.Image:
    """Pads `_ICON_MARK_BBOX` by `_CROP_PADDING_PX` on every side, then squares the resulting
    rectangle around its own center (rather than around the source image's own center), so the
    crop stays centered on the icon mark itself regardless of the mark's own aspect ratio."""
    left, top, right, bottom = _ICON_MARK_BBOX
    left -= _CROP_PADDING_PX
    top -= _CROP_PADDING_PX
    right += _CROP_PADDING_PX
    bottom += _CROP_PADDING_PX
    side = max(right - left, bottom - top)
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    square_left = round(center_x - side / 2)
    square_top = round(center_y - side / 2)
    return logo.crop((square_left, square_top, square_left + side, square_top + side))


def main() -> int:
    if sys.platform != "darwin":
        print(
            "This script assembles a macOS .icns file (via `iconutil`) and must be run on macOS.",
            file=sys.stderr,
        )
        return 1

    logo = Image.open(LOGO_PATH).convert("RGBA")
    icon_mark = _square_crop_icon_mark(logo)
    icon_mark.save(ICON_MARK_PATH)
    print(f"Wrote {ICON_MARK_PATH} ({icon_mark.width}x{icon_mark.height})")

    work_dir = Path(tempfile.mkdtemp(prefix="fieldbuild-kit-iconset-"))
    try:
        iconset_dir = work_dir / "icon.iconset"
        iconset_dir.mkdir()
        for filename, size in _ICONSET_SIZES:
            resized = icon_mark.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(iconset_dir / filename)

        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(ICNS_PATH)],
            check=True,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    print(f"Wrote {ICNS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
