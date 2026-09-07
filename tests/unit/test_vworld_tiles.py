"""Unit tests for qfield_builder.vworld_tiles.resolve_tile_fetcher.

Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058; conformance-gap round, 2026-08-27): a missing/blank
`vworld_api_key` used to reach a raw `basemap_config["vworld_api_key"]` dict index here, raising an
uncaught-by-this-module `KeyError` whose `str()` is the bare `"'vworld_api_key'"` repr -- the exact
defect the stakeholder's own screenshot showed ("생성 실패: 'vworld_api_key'"). This is now guarded
here directly (in addition to, and independently of, `qfield_builder.build`'s own proactive
`VWorldApiKeyMissingError` check before this function is ever called -- see that module's own
tests) so a bare `KeyError` can never reach the user regardless of how this function is reached.
"""
from __future__ import annotations

import pytest

from qfield_builder.errors import ProviderTileResponseError, VWorldApiKeyMissingError
from qfield_builder.vworld_tiles import make_real_vworld_tile_fetcher, resolve_tile_fetcher


def test_resolve_tile_fetcher_raises_actionable_error_when_key_missing_entirely():
    basemap_config = {"layer": "Base"}  # no "vworld_api_key" key at all.
    with pytest.raises(VWorldApiKeyMissingError) as exc_info:
        resolve_tile_fetcher(basemap_config)
    message = str(exc_info.value)
    assert message.strip()
    assert message != "'vworld_api_key'"  # never the raw KeyError repr
    assert "vworld_api_key" not in message  # never leaks the raw dict-key name either


def test_resolve_tile_fetcher_raises_actionable_error_when_key_is_blank():
    basemap_config = {"vworld_api_key": "   ", "layer": "Base"}
    with pytest.raises(VWorldApiKeyMissingError):
        resolve_tile_fetcher(basemap_config)


def test_resolve_tile_fetcher_never_raises_a_bare_key_error():
    """Regression guard for the exact defect: this must never be a plain `KeyError` (whose
    `str()` is the bare `"'vworld_api_key'"` repr the stakeholder's screenshot showed), even
    though `VWorldApiKeyMissingError` is itself a subclass of `Exception`, not `KeyError`."""
    basemap_config: dict = {}
    with pytest.raises(Exception) as exc_info:  # noqa: PT011 - deliberately broad, see assert below
        resolve_tile_fetcher(basemap_config)
    assert not isinstance(exc_info.value, KeyError)


def test_resolve_tile_fetcher_succeeds_when_key_present():
    basemap_config = {"vworld_api_key": "REAL-KEY", "layer": "Base"}
    fetcher = resolve_tile_fetcher(basemap_config)
    assert callable(fetcher)


def test_resolve_tile_fetcher_fake_tile_source_never_needs_a_key():
    """The `{"fake": {...}}` test-seam path never reads `vworld_api_key` at all -- confirmed
    unaffected by this round's defensive fix."""
    basemap_config = {"tile_source": {"fake": {"mode": "success", "tile_bytes": 4000}}}
    fetcher = resolve_tile_fetcher(basemap_config)
    assert callable(fetcher)
    assert fetcher(1, 0, 0)  # never raises, never needs a key


class _Response:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.body


def test_real_fetcher_uses_satellite_jpeg_and_keeps_xyz_row(monkeypatch):
    requested: list[str] = []

    def fake_urlopen(url, timeout):
        requested.append(url)
        return _Response(b"\xff\xd8\xff\xe0image")

    monkeypatch.setattr("qfield_builder.vworld_tiles.urllib.request.urlopen", fake_urlopen)
    fetch = make_real_vworld_tile_fetcher("KEY", "Satellite", min_interval_seconds=0)

    assert fetch(10, 873, 401).startswith(b"\xff\xd8\xff")
    assert requested == [
        "https://api.vworld.kr/req/wmts/1.0.0/KEY/Satellite/10/401/873.jpeg"
    ]


def test_real_fetcher_rejects_non_image_response(monkeypatch):
    monkeypatch.setattr(
        "qfield_builder.vworld_tiles.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response(b"<?xml version='1.0'?><ExceptionReport/>"),
    )
    fetch = make_real_vworld_tile_fetcher("KEY", "Base", min_interval_seconds=0)

    with pytest.raises(ProviderTileResponseError):
        fetch(10, 873, 401)


def test_real_fetcher_retries_read_timeout(monkeypatch):
    attempts = 0

    def fake_urlopen(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("The read operation timed out")
        return _Response(b"\x89PNG\r\n\x1a\nimage")

    monkeypatch.setattr("qfield_builder.vworld_tiles.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("qfield_builder.vworld_tiles.time.sleep", lambda _seconds: None)
    fetch = make_real_vworld_tile_fetcher(
        "KEY", "Base", max_retries=2, min_interval_seconds=0
    )

    assert fetch(10, 873, 401).startswith(b"\x89PNG")
    assert attempts == 2
