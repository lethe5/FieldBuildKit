"""Unit tests for qfield_builder.plantnet_client (FR-QPB-104, revised; Decision Log D-37).

The acceptance suite (tests/acceptance/qfield_project_builder/test_post_mvp_plantnet_request_shape.
py) already exercises `build_plantnet_identify_request`'s request-shape rules extensively and
`call_plantnet_identify` against the real, live API. This file covers what that suite does not:
`call_plantnet_identify`'s offline error-handling paths (network failure, non-JSON body), using a
monkeypatched `urlopen` so no live network access is required.
"""
from __future__ import annotations

import io
import json
from urllib import error as urllib_error

import pytest

from qfield_builder import plantnet_client


def test_build_request_url_uses_the_confirmed_endpoint_template():
    result = plantnet_client.build_plantnet_identify_request(["a.jpg"], ["leaf"], project="k-korea")
    assert result["ok"] is True
    assert result["url"] == "https://my-api.plantnet.org/v2/identify/k-korea"


def test_build_request_query_includes_include_related_images_true(tmp_path):
    """FR-QPB-104 (further revised; Decision Log D-54; AC-QPB-094): see also
    test_post_mvp_plantnet_request_shape.py::test_requests_related_images_are_included."""
    result = plantnet_client.build_plantnet_identify_request(["a.jpg"], ["leaf"])
    assert result["ok"] is True
    assert result["query"]["include-related-images"] is True
    assert "nb-results" not in result["query"]


def test_call_plantnet_identify_requests_include_related_images_true(tmp_path, monkeypatch):
    """The real, live-network-calling function must also request related images -- not just the
    offline reference-shape function `build_plantnet_identify_request` checked above."""
    photo = tmp_path / "leaf.jpg"
    photo.write_bytes(b"fake-jpeg-bytes")

    captured = {}

    class _FakeResponse(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    def _fake_urlopen(request, *_args, **_kwargs):
        captured["url"] = request.full_url
        return _FakeResponse(b'{"results":[]}')

    monkeypatch.setattr(plantnet_client.urllib_request, "urlopen", _fake_urlopen)
    plantnet_client.call_plantnet_identify([str(photo)], ["leaf"], "fake-key")
    assert "include-related-images=true" in captured["url"]
    assert "nb-results" not in captured["url"]


def test_call_plantnet_identify_handles_a_network_error_without_raising(tmp_path, monkeypatch):
    photo = tmp_path / "leaf.jpg"
    photo.write_bytes(b"not a real jpeg but bytes are enough for this offline test")

    def _raise_url_error(*_args, **_kwargs):
        raise urllib_error.URLError("simulated DNS failure")

    monkeypatch.setattr(plantnet_client.urllib_request, "urlopen", _raise_url_error)

    outcome = plantnet_client.call_plantnet_identify([str(photo)], ["leaf"], "fake-key")
    assert outcome["http_status"] == 0
    assert outcome["body"] is None
    assert "simulated DNS failure" in outcome["raw_text"]


def test_call_plantnet_identify_parses_a_successful_json_body(tmp_path, monkeypatch):
    photo = tmp_path / "leaf.jpg"
    photo.write_bytes(b"fake-jpeg-bytes")

    response_payload = {"results": [{"score": 0.9, "species": {"scientificName": "Foo bar"}}]}

    class _FakeResponse(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    def _fake_urlopen(*_args, **_kwargs):
        return _FakeResponse(json.dumps(response_payload).encode("utf-8"))

    monkeypatch.setattr(plantnet_client.urllib_request, "urlopen", _fake_urlopen)

    outcome = plantnet_client.call_plantnet_identify([str(photo)], ["leaf"], "fake-key")
    assert outcome["http_status"] == 200
    assert outcome["body"] == response_payload


def test_call_plantnet_identify_handles_an_http_error_with_a_json_body(tmp_path, monkeypatch):
    photo = tmp_path / "leaf.jpg"
    photo.write_bytes(b"fake-jpeg-bytes")

    error_payload = {"statusCode": 401, "error": "Unauthorized", "message": "Bad token"}

    def _raise_http_error(*_args, **_kwargs):
        raise urllib_error.HTTPError(
            url="https://my-api.plantnet.org/v2/identify/all",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(json.dumps(error_payload).encode("utf-8")),
        )

    monkeypatch.setattr(plantnet_client.urllib_request, "urlopen", _raise_http_error)

    outcome = plantnet_client.call_plantnet_identify([str(photo)], ["leaf"], "invalid-key")
    assert outcome["http_status"] == 401
    assert outcome["body"] == error_payload


def test_call_plantnet_identify_never_includes_the_api_key_in_the_returned_shape(
    tmp_path, monkeypatch
):
    photo = tmp_path / "leaf.jpg"
    photo.write_bytes(b"fake-jpeg-bytes")

    class _FakeResponse(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(
        plantnet_client.urllib_request, "urlopen", lambda *a, **k: _FakeResponse(b'{"results":[]}')
    )
    outcome = plantnet_client.call_plantnet_identify([str(photo)], ["leaf"], "super-secret-key")
    assert "super-secret-key" not in repr(outcome)


def test_build_request_rejects_invalid_inputs_before_any_network_call():
    result = plantnet_client.build_plantnet_identify_request([], [])
    assert result["ok"] is True
    result_mismatch = plantnet_client.build_plantnet_identify_request(["a.jpg", "b.jpg"], ["leaf"])
    assert result_mismatch["ok"] is False
    assert result_mismatch["error_code"] == "organ_count_mismatch"


@pytest.mark.parametrize("num_photos", [6, 10])
def test_build_request_rejects_more_than_five_photos(num_photos):
    photos = [f"p{i}.jpg" for i in range(num_photos)]
    organs = ["leaf"] * num_photos
    result = plantnet_client.build_plantnet_identify_request(photos, organs)
    assert result["ok"] is False
    assert result["error_code"] == "too_many_photos"
