#!/usr/bin/env bash
# Build only this independent app, using its own environment and reference files.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script builds the macOS application." >&2
    exit 1
fi
PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo "Create .venv and install .[ui,dev,packaging] first." >&2
    exit 1
fi
CANONICAL_REFERENCE="${QPB_CANONICAL_REFERENCE_SOURCE:-$REPO_ROOT/packaging/reference_source/tables/Rpt_2026-08-29_List.xlsx}"
RASTER_REFERENCE_DIR="${QPB_REFERENCE_RASTER_DIR:-$REPO_ROOT/storage/reference/rasters/bce_inverse_corrected_probability_maps}"
FILTERED_STAGE="$REPO_ROOT/build/filtered-reference"
"$PYTHON" packaging/prepare_reference_bundle.py \
    --canonical-workbook "$CANONICAL_REFERENCE" \
    --raster-dir "$RASTER_REFERENCE_DIR" \
    --source-manifest packaging/reference_source/canonical_source_manifest.json \
    --destination "$FILTERED_STAGE"
QPB_FILTERED_REFERENCE_ROOT="$FILTERED_STAGE" QPB_CANONICAL_REFERENCE_SOURCE="$CANONICAL_REFERENCE" \
    "$PYTHON" -m PyInstaller --noconfirm --distpath dist --workpath build \
    packaging/qfield_builder.spec
APP_BINARY="$REPO_ROOT/dist/FieldBuild Standalone.app/Contents/MacOS/FieldBuild Standalone"
"$APP_BINARY" --check-runtime
echo "Built: $REPO_ROOT/dist/FieldBuild Standalone.app (unsigned local trial)"
