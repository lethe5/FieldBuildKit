"""Section 13.2 — Pl@ntNet request shape (FR-QPB-104; post-MVP guaranteed-manual baseline).

The real, shipped mechanism that calls Pl@ntNet is the embedded `QML Widget`'s own native
`XMLHttpRequest` (FR-QPB-101) — genuinely QML-runtime behavior this project has no harness for.
What *is* testable, and what this file tests, is the *request-shape rules* FR-QPB-104 describes
(endpoint family, no application-imposed result count, one `organs` value per photo in matching
order, at most 5 photos, JPEG/PNG only) via a pure-Python reference implementation
(`acceptance_api.build_plantnet_identify_request`), plus a live, `network`-marked test that
actually calls the real Pl@ntNet API (`acceptance_api.call_plantnet_identify`) using the real key
in `QPB_TEST_PLANTNET_API_KEY` to confirm the authentication scheme/endpoint/response schema
(Decision Log D-32/Open Question O-14). See HARNESS_CONTRACT.md's "Post-MVP: Section 13" section
for the full rationale on why this pure-Python split is appropriate here specifically.

**The literal Pl@ntNet API key value is never written into this file or any other file in this
repository** — only the environment-variable name `QPB_TEST_PLANTNET_API_KEY` is referenced,
exactly mirroring the existing `QPB_TEST_VWORLD_API_KEY` convention (`tests/unit/test_vworld.py`).

D-98 (2026-09-07) supersedes the fixed-count requirement in the historical notes below.

Live-verification note (performed during test design, 2026-08-15, using the real key already
present locally in the gitignored `.env`): confirmed real endpoint family
`https://my-api.plantnet.org/v2/identify/{project}` (POST, multipart, `api-key`/`nb-results` as
query parameters — `my.plantnet.org` 404s and must not be used); confirmed exactly 3 results are
returned for `nb-results=3`, already in descending-`score` order; confirmed the success envelope
carries `species.scientificNameWithoutAuthor` at the documented path; confirmed the auth-failure
envelope is HTTP 401 with a JSON body. See HARNESS_CONTRACT.md function 8 for the full confirmed
shape.

**2026-08-25 addendum (Decision Log D-54; AC-QPB-094; FR-QPB-104, further revised):** one new
request-shape rule is added -- the request's query parameters must also include
`include-related-images=true`, causing Pl@ntNet to additionally return a representative-image list
per candidate (consumed by FR-QPB-109's new per-candidate image/attribution display, tested
structurally in `test_post_mvp_identification_plugin.py`'s AC-QPB-095 tests). See
`test_requests_related_images_are_included` below, and HARNESS_CONTRACT.md function 7's own
2026-08-25 addendum. This one new offline test is expected to currently FAIL (red): a direct
inspection of `qfield_builder/plantnet_client.py` during this test-design round confirmed its
`query` dict is still exactly `{"project": ..., "nb-results": ...}`, with no
`include-related-images` key.
"""
from __future__ import annotations

import os
import struct
import zlib

import pytest


def _tiny_synthetic_png() -> bytes:
    """A minimal, valid, dependency-free-generated PNG (no Pillow/other imaging dependency),
    used only to exercise the live Pl@ntNet API's authentication/endpoint/response *schema* -- not
    to test real plant-identification accuracy, which is not what FR-QPB-104/AC-QPB-040 require of
    this test."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    width = height = 4
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _y in range(height):
        raw += b"\x00"
        for _x in range(width):
            raw += bytes((60, 140, 60))
    idat = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# --- offline request-shape rules (FR-QPB-104) ---------------------------------------


def test_default_project_is_all_when_unspecified(build_plantnet_identify_request):
    result = build_plantnet_identify_request(["leaf.jpg"], ["leaf"])
    assert result["ok"], result
    assert result["query"]["project"] == "all"


def test_endpoint_matches_the_confirmed_real_endpoint_family(build_plantnet_identify_request):
    result = build_plantnet_identify_request(["leaf.jpg"], ["leaf"], project="all")
    assert result["ok"], result
    assert result["url"].startswith("https://my-api.plantnet.org/v2/identify/all"), (
        f"expected the live-confirmed real endpoint family, got {result['url']!r}"
    )


def test_requests_without_a_result_count_limit(build_plantnet_identify_request):
    result = build_plantnet_identify_request(["leaf.jpg"], ["leaf"])
    assert result["ok"], result
    assert "nb-results" not in result["query"], (
        "FR-QPB-104/D-98: no application-imposed result count"
    )


def test_requests_related_images_are_included(build_plantnet_identify_request):
    """D-54 related images remain enabled; D-98 removes only the result count."""
    result = build_plantnet_identify_request(["leaf.jpg"], ["leaf"])
    assert result["ok"], result
    assert result["query"].get("include-related-images") is True, (
        "AC-QPB-094 (FR-QPB-104, further revised; Decision Log D-54): expected the request's "
        "query parameters to include include-related-images=true "
        f"-- got query={result['query']!r}"
    )


def test_organs_count_must_match_photo_count(build_plantnet_identify_request):
    result = build_plantnet_identify_request(
        ["leaf.jpg", "flower.jpg"], ["leaf"]  # 2 photos, 1 organ
    )
    assert result["ok"] is False
    assert result["error_code"] == "organ_count_mismatch"


def test_organs_are_preserved_in_matching_order(build_plantnet_identify_request):
    result = build_plantnet_identify_request(
        ["a.jpg", "b.jpg", "c.jpg"], ["leaf", "flower", "fruit"]
    )
    assert result["ok"], result
    assert result["organs"] == ["leaf", "flower", "fruit"]
    assert result["photo_paths"] == ["a.jpg", "b.jpg", "c.jpg"]


def test_accepts_exactly_five_photos(build_plantnet_identify_request):
    photos = [f"p{i}.jpg" for i in range(5)]
    organs = ["leaf"] * 5
    result = build_plantnet_identify_request(photos, organs)
    assert result["ok"], result


def test_rejects_more_than_five_photos(build_plantnet_identify_request):
    photos = [f"p{i}.jpg" for i in range(6)]
    organs = ["leaf"] * 6
    result = build_plantnet_identify_request(photos, organs)
    assert result["ok"] is False
    assert result["error_code"] == "too_many_photos"


@pytest.mark.parametrize("bad_name", ["photo.gif", "photo.bmp", "photo.tiff", "photo"])
def test_rejects_unsupported_photo_formats(build_plantnet_identify_request, bad_name):
    result = build_plantnet_identify_request([bad_name], ["leaf"])
    assert result["ok"] is False
    assert result["error_code"] == "unsupported_photo_format"


@pytest.mark.parametrize("good_name", ["photo.jpg", "photo.JPEG", "photo.png", "photo.PNG"])
def test_accepts_jpeg_and_png_case_insensitively(build_plantnet_identify_request, good_name):
    result = build_plantnet_identify_request([good_name], ["leaf"])
    assert result["ok"], result


def test_request_shape_never_carries_raw_photo_bytes(build_plantnet_identify_request):
    """Request-construction-layer support for FR-QPB-104's "never log photo binary data" -- the
    returned shape must reference paths/filenames only, never embedded byte content."""
    result = build_plantnet_identify_request(["leaf.jpg"], ["leaf"])
    assert result["ok"], result
    serialized = repr(result)
    assert "leaf.jpg" in serialized
    # No binary/base64-ish giant payload should ever appear in a pure request-shape description.
    assert len(serialized) < 2000


# --- live network variant (skipped by default; run with --run-network and a real key) ----------


@pytest.mark.network
def test_plantnet_live_endpoint_authenticates_and_returns_the_confirmed_schema(
    call_plantnet_identify, tmp_path
):
    real_key = os.environ.get("QPB_TEST_PLANTNET_API_KEY")
    if not real_key:
        pytest.skip("QPB_TEST_PLANTNET_API_KEY not set")

    photo_path = tmp_path / "leaf.png"
    photo_path.write_bytes(_tiny_synthetic_png())

    outcome = call_plantnet_identify([str(photo_path)], ["leaf"], real_key)
    assert outcome["http_status"] == 200, outcome
    body = outcome["body"]
    assert isinstance(body, dict)
    assert "results" in body
    results = body["results"]
    assert results, "AC-QPB-040: this successful plant fixture must return candidates"

    scores = [entry["score"] for entry in results]
    assert all(0.0 <= s <= 1.0 for s in scores), "FR-QPB-104: confidence scores are 0-1"
    assert scores == sorted(scores, reverse=True), (
        "AC-QPB-040: results must be ordered by descending Pl@ntNet score"
    )
    for entry in results:
        assert "scientificNameWithoutAuthor" in entry["species"], (
            "FR-QPB-104: species.scientificNameWithoutAuthor must be present for KTSN matching"
        )


@pytest.mark.network
def test_plantnet_live_endpoint_rejects_an_invalid_key_without_losing_the_observation(
    call_plantnet_identify, tmp_path
):
    """FR-QPB-104: authentication failure must be handled, not crash/lose the observation. This
    test deliberately uses an invalid key (not `QPB_TEST_PLANTNET_API_KEY`) -- it needs no real
    key/`--run-network`-gated secret to demonstrate the auth-failure envelope shape, but is kept
    under the `network` marker because it still performs a real HTTPS call."""
    photo_path = tmp_path / "leaf.png"
    photo_path.write_bytes(_tiny_synthetic_png())

    outcome = call_plantnet_identify(
        [str(photo_path)], ["leaf"], "INVALID-TEST-KEY-0000"
    )
    assert outcome["http_status"] == 401
    assert outcome["body"] is not None and outcome["body"].get("error") == "Unauthorized"
