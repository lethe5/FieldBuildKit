"""Unit-level contract checks for the D-95 canonical KTSN transformation seams.

The implementation-level module name is deliberately not prescribed here.  The acceptance API
is the clean-room seam: these tests fail with a useful assertion until the new functions are
exposed, while existing pre-D-95 code remains importable.
"""
from __future__ import annotations

import pytest

from qfield_builder import acceptance_api


def _function(name: str):
    function = getattr(acceptance_api, name, None)
    assert callable(function), f"D-95 unit seam is missing: acceptance_api.{name}"
    return function


@pytest.mark.parametrize(
    ("raw", "scientific", "without_authority", "authority"),
    [
        (
            "  Genus   species  (  Author  )Other  ",
            "Genus species (Author) Other",
            "Genus species",
            "(Author) Other",
        ),
        ("Genus species B. Author", "Genus species B. Author", "Genus species", "B. Author"),
        ("Genus species", "Genus species", "Genus species", ""),
    ],
)
def test_r_equivalent_cleaner_is_pure_and_does_not_replace_raw_name(
    raw, scientific, without_authority, authority
):
    result = _function("normalize_canonical_scientific_name")(raw)
    assert result == {
        "scientific_name_normalized": scientific,
        "scientific_name_without_authority": without_authority,
        "authority": authority,
    }


def test_url_prefix_extraction_preserves_leading_zero_as_text():
    extract = _function("extract_canonical_ktsn")
    result = extract("https://species.nibr.go.kr/species-detail/000000000007")
    assert result["ktsn"] == "000000000007"
    assert isinstance(result["ktsn"], str)


def test_normalizer_returns_no_authority_marker_when_marker_is_absent():
    result = _function("normalize_canonical_scientific_name")("Genus species subsp. minor")
    assert result["authority"] == ""
    assert result["scientific_name_without_authority"] == "Genus species subsp. minor"
