"""Relative attachment-path validation.

DR-QPB-012; HARNESS_CONTRACT.md's `invalid_attachment_path`.

Photo files must never be stored as database BLOBs; only paths relative to the project folder
may be stored, and absolute paths must never be written into the GeoPackage or QGIS project
(DR-QPB-012). This module classifies malformed attachment-path shapes and distinguishes them
from the separate "well-formed path, but the referenced file is missing" failure mode
(`broken_attachment_reference`), per HARNESS_CONTRACT.md's save-time vs. validate_project-only
enforcement split.
"""
from __future__ import annotations

import os
import re
from pathlib import Path, PureWindowsPath

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^\\\\")


def classify_attachment_path(raw_path) -> str | None:
    """Classify a stored attachment-path value as malformed, or None if syntactically well-formed.

    This is the subset of checks that do *not* require filesystem/project-location context —
    i.e. exactly the six shapes HARNESS_CONTRACT.md commits `attempt_feature_save` to rejecting
    at save time via a static per-feature field constraint: empty, whitespace-only, POSIX
    absolute, Windows drive-letter absolute, UNC, and `file://` URI. `..`-traversal is
    deliberately NOT classified here (see :func:`escapes_project_root`).
    """
    if raw_path is None:
        return "empty"
    if not isinstance(raw_path, str):
        return "empty"
    if raw_path == "":
        return "empty"
    if raw_path.strip() == "":
        return "whitespace_only"
    if raw_path.lower().startswith("file://"):
        return "file_uri"
    if _UNC_RE.match(raw_path):
        return "unc_path"
    if _WINDOWS_DRIVE_RE.match(raw_path):
        return "windows_drive_absolute"
    if raw_path.startswith("/"):
        return "posix_absolute"
    if PureWindowsPath(raw_path).is_absolute():
        return "windows_drive_absolute"
    return None


def escapes_project_root(project_dir: str, relative_path: str) -> bool:
    """True if `relative_path`, resolved against `project_dir`, escapes the project root.

    Requires filesystem/project-location context (the actual project folder location), unlike
    :func:`classify_attachment_path`'s purely syntactic checks — see HARNESS_CONTRACT.md.
    """
    root = os.path.normpath(os.path.abspath(project_dir))
    candidate = os.path.normpath(os.path.join(root, relative_path))
    try:
        Path(candidate).relative_to(root)
        return False
    except ValueError:
        return True


def is_malformed_attachment_path(
    raw_path, project_dir: str | None = None
) -> tuple[bool, str | None]:
    """Full malformed-path check, including `..`-traversal when `project_dir` is supplied.

    Returns (is_malformed, shape_code). `shape_code` is one of the classify_attachment_path
    codes, or "traversal_escapes_project_root".
    """
    shape = classify_attachment_path(raw_path)
    if shape is not None:
        return True, shape
    if project_dir is not None and ".." in Path(raw_path).parts:
        if escapes_project_root(project_dir, raw_path):
            return True, "traversal_escapes_project_root"
    return False, None
