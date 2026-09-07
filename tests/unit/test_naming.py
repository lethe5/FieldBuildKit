"""Unit tests for qfield_builder.naming (FR-QPB-020-022a, Decision Log D-22)."""
from __future__ import annotations

import re

import pytest

from qfield_builder.naming import derive_project_slug, new_project_id

ASCII_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@pytest.mark.parametrize(
    "name",
    [
        "테스트 프로젝트 1",
        "Café Survey — 2026",
        "My  Project!! (v2)",
        "  leading and trailing spaces  ",
        "植生調査プロジェクト",
        "Simple ASCII Name",
    ],
)
def test_derive_slug_success(name):
    result = derive_project_slug(name)
    assert result.ok is True
    assert ASCII_SLUG_RE.match(result.slug)


@pytest.mark.parametrize(
    "name", ["", "   ", "..", "../../etc/passwd", "a/../b", "a\\..\\b", "/", "\\", "."]
)
def test_derive_slug_rejects_blank_and_traversal(name):
    result = derive_project_slug(name)
    assert result.ok is False
    assert result.error_code in ("blank", "path_traversal")


@pytest.mark.parametrize(
    "name", ["CON", "con", "Con", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9", "com5"]
)
def test_derive_slug_rejects_windows_reserved(name):
    result = derive_project_slug(name)
    assert result.ok is False
    assert result.error_code == "reserved_filename"


def test_derive_slug_truncates_to_64_chars():
    long_name = "a very long project display name " * 5
    result = derive_project_slug(long_name)
    assert result.ok is True
    assert len(result.slug) <= 64
    assert not result.slug.endswith("-")


def test_derive_slug_is_deterministic():
    a = derive_project_slug("Café Survey — 2026")
    b = derive_project_slug("Café Survey — 2026")
    assert a.slug == b.slug


def test_pure_cjk_name_produces_nonempty_distinct_fallback_slugs():
    a = derive_project_slug("植生調査プロジェクト")
    b = derive_project_slug("完全に別の名前")
    assert a.ok and b.ok
    assert a.slug and b.slug
    assert a.slug != b.slug


def test_as_dict_matches_harness_contract_shape():
    ok_result = derive_project_slug("Simple Name").as_dict()
    assert set(ok_result.keys()) == {"ok", "slug"}
    assert ok_result["ok"] is True

    bad_result = derive_project_slug("").as_dict()
    assert bad_result["ok"] is False
    assert "error_code" in bad_result and "message" in bad_result


def test_new_project_id_is_a_distinct_uuid_v4():
    import uuid

    a, b = new_project_id(), new_project_id()
    assert a != b
    assert uuid.UUID(a).version == 4
    assert uuid.UUID(b).version == 4
