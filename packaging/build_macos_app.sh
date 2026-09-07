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
exec "$PYTHON" packaging/build_app.py
