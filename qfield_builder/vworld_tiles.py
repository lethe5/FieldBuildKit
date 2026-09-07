"""VWorld offline tile acquisition: the real downloader, and the deterministic fake test double.

See HARNESS_CONTRACT.md's `build_project` `config["basemap"]["tile_source"]` documentation: the
production default is the real VWorld downloader; `{"fake": {...}}` is an injectable test seam
used by the acceptance suite to exercise success/quota/auth/rate-limit/oversized-output paths
deterministically, without live network access or quota consumption.
"""
from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from .errors import (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderTileResponseError,
    VWorldApiKeyMissingError,
)
from .vworld import build_tile_request_url

# E-QPB-003/FR-QPB-078/NFR-QPB-058: a clear, non-technical, actionable message shown whenever a
# missing/blank VWorld API key would otherwise reach this module's real-downloader path -- see
# `resolve_tile_fetcher` below.
_MISSING_API_KEY_MESSAGE = (
    "오프라인 배경지도를 생성하려면 VWorld API 키가 필요합니다. 마법사의 4단계(연결 상태 및 "
    "배경지도)에서 API 키를 입력한 뒤 다시 시도해 주세요."
)

_OVERSIZED_TILE_BYTES = 300_000_000  # deliberately far larger than any real VWorld tile.


def _is_image_tile(payload: bytes) -> bool:
    """Reject XML/HTML API error bodies before they can become blank MBTiles tiles."""
    return (
        payload.startswith(b"\x89PNG\r\n\x1a\n")
        or payload.startswith(b"\xff\xd8\xff")
        or (payload.startswith(b"RIFF") and payload[8:12] == b"WEBP")
    )


def make_fake_tile_fetcher(mode: str, tile_bytes: int) -> Callable[[int, int, int], bytes]:
    """A deterministic fault-injection double standing in for the real VWorld tile client.

    `mode`: "success" | "quota_error" | "auth_error" | "rate_limit_error" | "oversized".
    """

    def _fetch(z: int, x: int, y: int) -> bytes:
        if mode == "success":
            return b"\x89PNG-fake-tile-" + bytes(max(0, tile_bytes - 15))
        if mode == "oversized":
            return bytes(_OVERSIZED_TILE_BYTES)
        if mode == "quota_error":
            raise ProviderQuotaError(
                "VWorld API로부터 이 API 키의 사용 할당량이 초과되었다는 응답을 받았습니다. "
                "잠시 후 다시 시도하거나 다른 키를 사용해 주세요."
            )
        if mode == "auth_error":
            raise ProviderAuthError(
                "VWorld API가 제공된 API 키를 거부했습니다. 키를 확인한 뒤 다시 시도해 주세요."
            )
        if mode == "rate_limit_error":
            raise ProviderRateLimitError(
                "VWorld API가 이 키의 요청을 일시적으로 제한하고 있습니다. 잠시 기다린 뒤 "
                "다시 시도해 주세요."
            )
        raise ValueError(f"Unknown fake tile_source mode: {mode!r}")

    return _fetch


class _RateLimiter:
    def __init__(self, min_interval_seconds: float):
        self._min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


def make_real_vworld_tile_fetcher(
    api_key: str,
    layer: str,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    min_interval_seconds: float = 0.05,
    request_timeout_seconds: float = 45.0,
) -> Callable[[int, int, int], bytes]:
    """The real VWorld tile downloader (FR-QPB-084/086): bounded rate + retry/backoff.

    Not exercised by the default acceptance-test run (network-marked tests are skipped unless
    ``--run-network`` is passed with a real API key); implemented here as the genuine production
    code path per FR-QPB-011/086/088/089.
    """
    limiter = _RateLimiter(min_interval_seconds)

    def _fetch(z: int, x: int, y: int) -> bytes:
        url = build_tile_request_url(api_key, layer, z, x, y)
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            limiter.wait()
            try:
                with urllib.request.urlopen(  # noqa: S310
                    url, timeout=request_timeout_seconds
                ) as response:
                    tile = response.read()
                if not _is_image_tile(tile):
                    raise ProviderTileResponseError(
                        "VWorld가 지도 이미지가 아닌 오류 응답을 반환했습니다. "
                        "선택한 레이어와 API 키의 서비스 권한을 확인한 뒤 다시 시도해 주세요."
                    )
                return tile
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise ProviderAuthError(
                        "VWorld API가 제공된 API 키를 거부했습니다."
                    ) from exc
                if exc.code == 429:
                    raise ProviderRateLimitError(
                        "VWorld API가 이 키의 요청을 제한하고 있습니다."
                    ) from exc
                if exc.code in (402, 407) or "quota" in str(exc.reason).lower():
                    raise ProviderQuotaError(
                        "VWorld API로부터 사용 할당량이 초과되었다는 응답을 받았습니다."
                    ) from exc
                last_exc = exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                last_exc = exc
            time.sleep(backoff_seconds * (2**attempt))
        raise ProviderRateLimitError(
            f"{max_retries}회 시도 후에도 VWorld 타일을 다운로드할 수 없었습니다: {last_exc}"
        )

    return _fetch


def resolve_tile_fetcher(basemap_config: dict) -> Callable[[int, int, int], bytes]:
    """Resolve the configured `tile_source` (real VWorld by default, fake for tests).

    Bug 1 fix (defense in depth, E-QPB-003/FR-QPB-078/NFR-QPB-058): `qfield_builder.build`'s
    offline branch already raises `VWorldApiKeyMissingError` proactively, before this function is
    ever called, whenever `basemap_config` has no usable key (the normal, expected path for a
    missing key). This function's own `.get()`/blank check below is a second, independent guard
    against a stale/malformed `basemap_config` reaching here by some other path -- so a bare
    `KeyError` repr (the raw defect this round fixes) can never reach the user regardless of how
    this function is reached.
    """
    tile_source = basemap_config.get("tile_source", "vworld")
    if isinstance(tile_source, dict) and "fake" in tile_source:
        fake_cfg = tile_source["fake"]
        return make_fake_tile_fetcher(fake_cfg["mode"], fake_cfg.get("tile_bytes", 5000))
    raw_api_key = basemap_config.get("vworld_api_key")
    api_key = raw_api_key.strip() if isinstance(raw_api_key, str) else ""
    if not api_key:
        raise VWorldApiKeyMissingError(_MISSING_API_KEY_MESSAGE)
    return make_real_vworld_tile_fetcher(api_key=api_key, layer=basemap_config.get("layer", "Base"))
