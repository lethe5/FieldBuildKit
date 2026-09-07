"""Unit tests for qfield_builder.paths (DR-QPB-012, AC-QPB-009's invalid_attachment_path split)."""
from __future__ import annotations

import pytest

from qfield_builder.paths import (
    classify_attachment_path,
    escapes_project_root,
    is_malformed_attachment_path,
)

MALFORMED_CASES = [
    ("", "empty"),
    ("   ", "whitespace_only"),
    ("/etc/photos/leaf.jpg", "posix_absolute"),
    ("C:\\Users\\x\\leaf.jpg", "windows_drive_absolute"),
    ("\\\\server\\share\\leaf.jpg", "unc_path"),
    ("file:///Users/x/leaf.jpg", "file_uri"),
]


@pytest.mark.parametrize("value,expected_code", MALFORMED_CASES)
def test_classify_malformed_shapes(value, expected_code):
    assert classify_attachment_path(value) == expected_code


@pytest.mark.parametrize(
    "value",
    ["attachments/leaf.jpg", "attachments/sub/leaf.jpg", "leaf.jpg"],
)
def test_classify_well_formed_relative_paths_returns_none(value):
    assert classify_attachment_path(value) is None


def test_escapes_project_root_true_for_traversal(tmp_path):
    assert escapes_project_root(str(tmp_path), "../../outside/leaf.jpg") is True


def test_escapes_project_root_false_for_ordinary_relative_path(tmp_path):
    assert escapes_project_root(str(tmp_path), "attachments/leaf.jpg") is False


def test_is_malformed_attachment_path_flags_traversal_only_with_project_dir(tmp_path):
    is_bad, shape = is_malformed_attachment_path(
        "../../outside/leaf.jpg", project_dir=str(tmp_path)
    )
    assert is_bad is True
    assert shape == "traversal_escapes_project_root"

    # Without project_dir context, traversal is not flagged by this purely-syntactic classifier
    # (that's exactly why validate_project, which has project_dir, is the one that must catch it).
    is_bad_no_context, shape_no_context = is_malformed_attachment_path("../../outside/leaf.jpg")
    assert is_bad_no_context is False
    assert shape_no_context is None


def test_is_malformed_attachment_path_accepts_well_formed_path(tmp_path):
    is_bad, shape = is_malformed_attachment_path("attachments/leaf.jpg", project_dir=str(tmp_path))
    assert is_bad is False
    assert shape is None


@pytest.mark.parametrize("value,expected_code", MALFORMED_CASES)
def test_is_malformed_attachment_path_covers_all_six_syntactic_shapes(value, expected_code):
    is_bad, shape = is_malformed_attachment_path(value)
    assert is_bad is True
    assert shape == expected_code
