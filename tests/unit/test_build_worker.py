"""Regression tests for offline worker lifecycle budgeting."""
from __future__ import annotations

from qfield_builder.ui.build_worker import build_operation_timeout_seconds


def test_offline_operation_budget_has_no_fixed_twelve_hour_ceiling():
    bbox = {"min_lon": 126.0, "min_lat": 33.0, "max_lon": 130.0, "max_lat": 39.0}
    config = {
        "basemap": {
            "mode": "offline",
            "bbox": bbox,
            "min_zoom": 1,
            "max_zoom": 18,
        }
    }

    assert build_operation_timeout_seconds(config) > 12 * 60 * 60


def test_non_offline_operation_keeps_a_bounded_baseline_budget():
    assert build_operation_timeout_seconds({"basemap": {"mode": "none"}}) == 30 * 60
