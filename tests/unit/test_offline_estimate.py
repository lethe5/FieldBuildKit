"""Unit tests for qfield_builder.offline_estimate (FR-QPB-081/082, DR-QPB-060)."""
from __future__ import annotations

from qfield_builder.offline_estimate import (
    OFFLINE_HARD_LIMIT_BYTES,
    OFFLINE_PREGENERATION_THRESHOLD_BYTES,
    estimate_offline_basemap_size,
    tiles_for_zoom,
    total_tile_count,
)

SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}
HUGE_BBOX = {"min_lon": 126.0, "min_lat": 33.0, "max_lon": 130.0, "max_lat": 39.0}


def test_thresholds_match_spec_byte_values():
    assert OFFLINE_PREGENERATION_THRESHOLD_BYTES == 900 * 1024 * 1024
    assert OFFLINE_HARD_LIMIT_BYTES == 1024 * 1024 * 1024


def test_tiles_for_zoom_is_at_least_one_for_a_nonempty_bbox():
    assert tiles_for_zoom(SMALL_BBOX, 5) >= 1
    assert tiles_for_zoom(SMALL_BBOX, 15) >= 1


def test_tile_count_increases_monotonically_with_zoom():
    counts = [tiles_for_zoom(SMALL_BBOX, z) for z in range(5, 16)]
    for earlier, later in zip(counts, counts[1:], strict=False):
        assert later >= earlier


def test_total_tile_count_is_sum_across_zoom_range():
    total = total_tile_count(SMALL_BBOX, 10, 12)
    assert total == sum(tiles_for_zoom(SMALL_BBOX, z) for z in (10, 11, 12))


def test_small_bbox_estimate_within_threshold():
    result = estimate_offline_basemap_size(SMALL_BBOX, 10, 12, 5000)
    assert result["exceeds_pregeneration_threshold"] is False
    assert result["estimated_bytes"] <= OFFLINE_PREGENERATION_THRESHOLD_BYTES
    assert result["tile_count"] > 0


def test_huge_bbox_wide_zoom_range_exceeds_threshold():
    result = estimate_offline_basemap_size(HUGE_BBOX, 1, 18, 20000)
    assert result["exceeds_pregeneration_threshold"] is True
    assert result["estimated_bytes"] > OFFLINE_PREGENERATION_THRESHOLD_BYTES


def test_estimate_return_shape_matches_harness_contract():
    result = estimate_offline_basemap_size(SMALL_BBOX, 10, 10, 1000)
    expected_keys = {"tile_count", "estimated_bytes", "exceeds_pregeneration_threshold"}
    assert set(result.keys()) == expected_keys
    assert isinstance(result["tile_count"], int)
    assert isinstance(result["estimated_bytes"], int)
    assert isinstance(result["exceeds_pregeneration_threshold"], bool)


def test_larger_representative_tile_bytes_increases_estimate():
    small = estimate_offline_basemap_size(SMALL_BBOX, 10, 12, 1000)
    large = estimate_offline_basemap_size(SMALL_BBOX, 10, 12, 100000)
    assert large["estimated_bytes"] > small["estimated_bytes"]
