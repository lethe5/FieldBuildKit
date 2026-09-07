"""Unit tests for qfield_builder.mbtiles (Section 11, DR-QPB-060/061, FR-QPB-083/084)."""
from __future__ import annotations

import sqlite3

import pytest

from qfield_builder.errors import BuildCancelledError, OfflineOutputOverflowError
from qfield_builder.mbtiles import build_mbtiles
from qfield_builder.vworld_tiles import make_fake_tile_fetcher

SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}


def test_build_mbtiles_success_writes_expected_metadata_and_tiles(tmp_path):
    out = tmp_path / "basemap" / "offline.mbtiles"
    result = build_mbtiles(
        str(out), SMALL_BBOX, 10, 12, make_fake_tile_fetcher("success", 5000)
    )
    assert out.exists()
    conn = sqlite3.connect(str(out))
    try:
        metadata = dict(conn.execute("SELECT name, value FROM metadata;").fetchall())
        assert metadata["format"] == "png"
        assert int(metadata["minzoom"]) == 10
        assert int(metadata["maxzoom"]) == 12
        bounds = [float(v) for v in metadata["bounds"].split(",")]
        assert bounds[0] <= SMALL_BBOX["min_lon"]
        assert bounds[2] >= SMALL_BBOX["max_lon"]
        for zoom in (10, 11, 12):
            count = conn.execute(
                "SELECT COUNT(*) FROM tiles WHERE zoom_level = ?;", (zoom,)
            ).fetchone()[0]
            assert count > 0
    finally:
        conn.close()
    assert result["tile_count"] > 0
    assert result["size_bytes"] == out.stat().st_size


def test_build_mbtiles_never_exceeds_hard_limit_bytes(tmp_path):
    out = tmp_path / "basemap" / "offline.mbtiles"
    result = build_mbtiles(
        str(out), SMALL_BBOX, 8, 13, make_fake_tile_fetcher("success", 8000)
    )
    assert result["size_bytes"] <= 1024 * 1024 * 1024


def test_oversized_generation_aborts_and_removes_partial_file(tmp_path):
    out = tmp_path / "basemap" / "offline.mbtiles"
    with pytest.raises(OfflineOutputOverflowError):
        build_mbtiles(str(out), SMALL_BBOX, 8, 13, make_fake_tile_fetcher("oversized", 8000))
    assert not out.exists()
    assert not out.parent.exists() or not any(out.parent.iterdir())


def test_cancellation_removes_partial_file(tmp_path):
    out = tmp_path / "basemap" / "offline.mbtiles"
    with pytest.raises(BuildCancelledError):
        build_mbtiles(
            str(out),
            SMALL_BBOX,
            10,
            14,
            make_fake_tile_fetcher("success", 5000),
            should_cancel=lambda: True,
        )
    assert not out.exists()


def test_build_mbtiles_reports_forward_progress_after_each_inserted_tile(tmp_path):
    out = tmp_path / "basemap" / "offline.mbtiles"
    progress = []

    result = build_mbtiles(
        str(out),
        SMALL_BBOX,
        10,
        11,
        make_fake_tile_fetcher("success", 4000),
        on_progress=progress.append,
    )

    assert result["tile_count"] == len(progress)
    assert progress
    assert progress[-1] == {
        "phase": "basemap_download",
        "completed_tiles": result["tile_count"],
    }


def test_provider_errors_propagate_and_leave_no_partial_file(tmp_path):
    from qfield_builder.errors import ProviderAuthError, ProviderQuotaError, ProviderRateLimitError

    for mode, exc_type in [
        ("quota_error", ProviderQuotaError),
        ("auth_error", ProviderAuthError),
        ("rate_limit_error", ProviderRateLimitError),
    ]:
        out = tmp_path / mode / "offline.mbtiles"
        with pytest.raises(exc_type):
            build_mbtiles(str(out), SMALL_BBOX, 10, 12, make_fake_tile_fetcher(mode, 5000))
        assert not out.exists()


def test_tms_row_conversion_flips_y_axis():
    from qfield_builder.mbtiles import _tms_row

    assert _tms_row(0, 3) == 7
    assert _tms_row(7, 3) == 0
