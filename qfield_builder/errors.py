"""Structured build errors.

`build_project` must return `{"success": False, "error_code": ..., "error_message": ...}` rather
than raise an uncaught exception (HARNESS_CONTRACT.md). Internally, the build pipeline raises
these typed exceptions so each stage can fail fast; the top-level orchestrator
(:mod:`qfield_builder.build`) catches `BuildError` and converts it to the structured result.
"""
from __future__ import annotations


class BuildError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class RuntimeMissingError(BuildError):
    def __init__(self, message: str):
        super().__init__("runtime_missing", message)


class OutputDirectoryExistsError(BuildError):
    def __init__(self, message: str):
        super().__init__("output_dir_exists", message)


class InvalidNameError(BuildError):
    def __init__(self, message: str, sub_code: str = "invalid_name"):
        super().__init__(sub_code, message)


class InvalidGeometryBuildError(BuildError):
    def __init__(self, message: str):
        super().__init__("invalid_geometry", message)


class OfflineSizeExceededError(BuildError):
    def __init__(self, message: str):
        super().__init__("offline_size_exceeded", message)


class OfflineOutputOverflowError(BuildError):
    def __init__(self, message: str):
        super().__init__("offline_output_exceeded_hard_limit", message)


class VWorldApiKeyMissingError(BuildError):
    """E-QPB-003/FR-QPB-078/NFR-QPB-058: offline MBTiles generation genuinely needs a VWorld API
    key during tile retrieval. Raised proactively (before `vworld_tiles.resolve_tile_fetcher()`
    is ever called, and therefore before any network I/O) whenever offline mode has no usable
    key, so a missing/blank key produces this clear, non-technical, actionable message instead of
    the raw `KeyError` repr a bare `basemap_config["vworld_api_key"]` dict index used to raise."""

    def __init__(self, message: str):
        super().__init__("vworld_api_key_missing", message)


class ProviderQuotaError(BuildError):
    def __init__(self, message: str):
        super().__init__("vworld_quota_exceeded", message)


class ProviderAuthError(BuildError):
    def __init__(self, message: str):
        super().__init__("vworld_authorization_error", message)


class ProviderRateLimitError(BuildError):
    def __init__(self, message: str):
        super().__init__("vworld_rate_limited", message)


class ProviderTileResponseError(BuildError):
    def __init__(self, message: str):
        super().__init__("vworld_invalid_tile_response", message)


class BuildCancelledError(BuildError):
    def __init__(self, message: str = "빌드가 취소되었습니다."):
        super().__init__("cancelled", message)


class OnlineConsentRequiredError(BuildError):
    def __init__(self, message: str):
        super().__init__("consent_required", message)


class ReferenceDataMissingError(BuildError):
    """FR-QPB-105: the KTSN reference CSV or probability-raster directory is missing."""

    def __init__(self, message: str):
        super().__init__("reference_data_missing", message)


class ReferenceDataInvalidError(BuildError):
    """FR-QPB-105: the KTSN reference CSV is missing one or more required columns."""

    def __init__(self, message: str):
        super().__init__("reference_data_invalid_columns", message)
