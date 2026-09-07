#!/usr/bin/env python3
"""Prepare the D-95 canonical-derived reference staging tree for PyInstaller."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the helper executable from a clean checkout without requiring callers to construct a
# PYTHONPATH. The macOS release script still sets PYTHONPATH explicitly for its chosen interpreter.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qfield_builder.reference_bundle import (  # noqa: E402
    prepare_filtered_reference_bundle,
    validate_canonical_release_source,
)
from qfield_builder.probability_raster import prepare_probability_stack_cache  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-workbook",
        required=True,
        type=Path,
        help="the explicitly provisioned D-95 canonical workbook",
    )
    parser.add_argument(
        "--raster-dir",
        required=True,
        type=Path,
        help="the separately provisioned probability-raster directory",
    )
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="tracked canonical source metadata used to verify the provisioned workbook",
    )
    args = parser.parse_args()
    if args.source_manifest:
        validate_canonical_release_source(args.canonical_workbook, args.source_manifest)
    prepare_filtered_reference_bundle(
        str(args.canonical_workbook),
        str(args.destination),
        raster_dir=args.raster_dir,
    )
    cache_result = prepare_probability_stack_cache(
        str(args.destination / "rasters" / "bce_inverse_corrected_probability_maps"),
        str(args.destination / "probability_cache"),
    )
    if not cache_result.get("success"):
        raise RuntimeError(
            cache_result.get("error_message") or "출현확률 다중밴드 캐시를 생성하지 못했습니다."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
