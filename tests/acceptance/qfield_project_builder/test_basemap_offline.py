"""Offline VWorld-sourced MBTiles basemap generation (Section 11, Section 18.3).

Covers:
- AC-QPB-018: approved bbox/zoom -> MBTiles tile coverage contains the bbox at every zoom level.
- AC-QPB-019: MBTiles metadata contains correct bounds/format/min/max zoom.
- AC-QPB-020: final .mbtiles size never exceeds 1 GiB.
- AC-QPB-021: an estimate exceeding 900 MiB blocks generation and prompts scope reduction.
- AC-QPB-022: renders correctly in each supported QGIS/QField version — blocked on O-9 (see
  test_qgis_project_config.py's AC-QPB-016 for the identical blocker; not duplicated at length
  here).
- AC-QPB-023: a cancelled in-progress build leaves no partial deliverable.
- AC-QPB-051 (offline half): MOLIT/VWorld KOGL Type-1 attribution present in the offline project
  and MANIFEST.json.
- AC-QPB-052: a quota/authorization/rate-limit error during tile download terminates gracefully,
  with no partial .mbtiles left in the final output folder.
- AC-QPB-056: an offline build references only the local .mbtiles file; no VWorld key anywhere.

Deterministic tile-download behavior (success, quota error, rate-limit error, oversized output)
is exercised via the injectable fake tile source documented in HARNESS_CONTRACT.md, to avoid
live network dependence/flakiness/quota consumption in the acceptance suite. A `network`-marked
smoke test using the real VWorld API is included and skipped by default.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from .conftest import (
    OFFLINE_HARD_LIMIT_BYTES,
    OFFLINE_PREGENERATION_THRESHOLD_BYTES,
    make_base_config,
)

pytestmark = pytest.mark.qgis

FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-FAKE-KEY-OFFLINE"

SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}


def _offline_config(bbox, min_zoom, max_zoom, tile_source):
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": FAKE_VWORLD_KEY,
        "layer": "Base",
        "bbox": bbox,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "tile_source": tile_source,
    }
    return config


def _open_mbtiles(path) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


# --- AC-QPB-018 / AC-QPB-019 ---------------------------------------------------

def test_ac018_ac019_mbtiles_coverage_and_metadata_match_request(acceptance_api, tmp_path):
    config = _offline_config(
        SMALL_BBOX, min_zoom=10, max_zoom=12, tile_source={"fake": {"mode": "success", "tile_bytes": 5000}}
    )
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")
    assert result["basemap_dir"], "expected a basemap_dir for an offline build"

    mbtiles_files = list(Path(result["basemap_dir"]).glob("*.mbtiles"))
    assert mbtiles_files, f"expected a .mbtiles file under {result['basemap_dir']}"
    mbtiles_path = mbtiles_files[0]

    conn = _open_mbtiles(mbtiles_path)
    try:
        metadata = dict(conn.execute("SELECT name, value FROM metadata;").fetchall())
        assert metadata.get("format"), "AC-QPB-019: expected a format entry in MBTiles metadata"
        assert int(metadata["minzoom"]) == 10
        assert int(metadata["maxzoom"]) == 12
        bounds = [float(v) for v in metadata["bounds"].split(",")]
        min_lon_b, min_lat_b, max_lon_b, max_lat_b = bounds
        assert min_lon_b <= SMALL_BBOX["min_lon"] and max_lon_b >= SMALL_BBOX["max_lon"], (
            "AC-QPB-018: MBTiles bounds must contain the approved bbox"
        )
        assert min_lat_b <= SMALL_BBOX["min_lat"] and max_lat_b >= SMALL_BBOX["max_lat"]

        for zoom in (10, 11, 12):
            count = conn.execute(
                "SELECT COUNT(*) FROM tiles WHERE zoom_level = ?;", (zoom,)
            ).fetchone()[0]
            assert count > 0, f"AC-QPB-018: expected at least one tile at zoom {zoom}"
    finally:
        conn.close()


# --- AC-QPB-020 -----------------------------------------------------------------

def test_ac020_final_mbtiles_never_exceeds_1_gib(acceptance_api, tmp_path):
    config = _offline_config(
        SMALL_BBOX, min_zoom=8, max_zoom=13, tile_source={"fake": {"mode": "success", "tile_bytes": 8000}}
    )
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")
    mbtiles_path = next(Path(result["basemap_dir"]).glob("*.mbtiles"))
    size = mbtiles_path.stat().st_size
    assert size <= OFFLINE_HARD_LIMIT_BYTES, (
        f"AC-QPB-020: .mbtiles size {size} exceeds the 1 GiB hard limit"
    )


def test_offline_build_aborts_and_cleans_up_when_actual_output_would_exceed_1_gib(
    acceptance_api, tmp_path
):
    """FR-QPB-083/E-QPB-006 (supports AC-QPB-020): abort + no incomplete temp output on overflow.

    Uses a deliberately oversized fake tile size (bypassing the pre-generation estimate check)
    to exercise the *during-generation* hard-limit abort path distinctly from the
    pre-generation-estimate block path covered by AC-QPB-021.
    """
    config = _offline_config(
        SMALL_BBOX,
        min_zoom=8,
        max_zoom=13,
        tile_source={"fake": {"mode": "oversized", "tile_bytes": 8000}},
    )
    out_dir = tmp_path / "out"
    result = acceptance_api.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result.get("error_code"), "expected a structured error_code for the overflow abort"
    assert not out_dir.exists() or not any(out_dir.iterdir()), (
        "E-QPB-009/E-QPB-006: no partially generated project may remain at the output path"
    )


# --- AC-QPB-021 -----------------------------------------------------------------

def test_ac021_estimate_over_900_mib_blocks_generation(acceptance_api):
    huge_bbox = {"min_lon": 126.0, "min_lat": 33.0, "max_lon": 130.0, "max_lat": 39.0}  # ~all of ROK
    estimate = acceptance_api.estimate_offline_basemap_size(
        huge_bbox, min_zoom=1, max_zoom=18, representative_tile_bytes=20_000
    )
    assert estimate["estimated_bytes"] > OFFLINE_PREGENERATION_THRESHOLD_BYTES
    assert estimate["exceeds_pregeneration_threshold"] is True

    config = _offline_config(
        huge_bbox, min_zoom=1, max_zoom=18, tile_source={"fake": {"mode": "success", "tile_bytes": 20_000}}
    )
    result = acceptance_api.build_project(config, "should_not_be_created")
    assert result["success"] is False
    assert result.get("error_code") == "offline_size_exceeded" or "size" in (
        result.get("error_code") or ""
    ).lower()
    assert not Path("should_not_be_created").exists()


def test_estimate_within_threshold_does_not_block(acceptance_api):
    estimate = acceptance_api.estimate_offline_basemap_size(
        SMALL_BBOX, min_zoom=10, max_zoom=12, representative_tile_bytes=5000
    )
    assert estimate["exceeds_pregeneration_threshold"] is False
    assert estimate["estimated_bytes"] <= OFFLINE_PREGENERATION_THRESHOLD_BYTES


# --- AC-QPB-023 / AC-QPB-052 (offline half of E-QPB-013) -----------------------

def test_ac023_cancelled_build_leaves_no_partial_deliverable(acceptance_api, tmp_path):
    config = _offline_config(
        SMALL_BBOX, min_zoom=10, max_zoom=14, tile_source={"fake": {"mode": "success", "tile_bytes": 5000}}
    )
    config["_test_cancel_after_phase"] = "basemap_download"
    out_dir = tmp_path / "out"
    result = acceptance_api.build_project(config, str(out_dir))
    assert result["cancelled"] is True
    assert result["success"] is False
    assert not out_dir.exists() or not any(out_dir.iterdir()), (
        "AC-QPB-023/E-QPB-010: cancellation must leave no partial deliverable"
    )


@pytest.mark.parametrize("failure_mode", ["quota_error", "auth_error", "rate_limit_error"])
def test_ac052_provider_error_terminates_gracefully_with_no_partial_mbtiles(
    acceptance_api, tmp_path, failure_mode
):
    config = _offline_config(
        SMALL_BBOX,
        min_zoom=10,
        max_zoom=12,
        tile_source={"fake": {"mode": failure_mode, "tile_bytes": 5000}},
    )
    out_dir = tmp_path / "out"
    try:
        result = acceptance_api.build_project(config, str(out_dir))
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"FR-QPB-088: a {failure_mode} must be handled gracefully, not raise: {exc!r}"
        )
    assert result["success"] is False
    message = (result.get("error_message") or "").lower()
    assert message.strip(), "expected a clear, non-technical message"
    technical_jargon = ["traceback", "stack trace", "httperror", "exception"]
    assert not any(term in message for term in technical_jargon)
    assert not out_dir.exists() or not any(out_dir.rglob("*.mbtiles")), (
        f"AC-QPB-052: no partial .mbtiles deliverable may remain after a {failure_mode}"
    )


# --- AC-QPB-056 -----------------------------------------------------------------

def test_ac056_offline_project_references_only_local_mbtiles_no_key_anywhere(
    acceptance_api, tmp_path
):
    config = _offline_config(
        SMALL_BBOX, min_zoom=10, max_zoom=11, tile_source={"fake": {"mode": "success", "tile_bytes": 4000}}
    )
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    assert FAKE_VWORLD_KEY not in qgs_text, "AC-QPB-056: no key in the offline .qgs project"

    for path in Path(result["project_dir"]).rglob("*"):
        if path.is_file():
            try:
                content = path.read_bytes()
            except OSError:
                continue
            assert FAKE_VWORLD_KEY.encode() not in content, f"key found in {path}"

    assert ".mbtiles" in qgs_text.lower(), "expected the .qgs to reference the local .mbtiles file"


# --- AC-QPB-051 (offline half) --------------------------------------------------

def test_ac051_molit_vworld_attribution_present_offline(acceptance_api, tmp_path):
    config = _offline_config(
        SMALL_BBOX, min_zoom=10, max_zoom=11, tile_source={"fake": {"mode": "success", "tile_bytes": 4000}}
    )
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    manifest = json.loads(open(f"{result['project_dir']}/MANIFEST.json", "r", encoding="utf-8").read())
    manifest_text = json.dumps(manifest)
    for text, label in [(qgs_text, "qgs"), (manifest_text, "manifest")]:
        assert "vworld" in text.lower(), f"expected VWorld attribution text in {label}"


# --- Live network smoke test (skipped by default) ------------------------------

@pytest.mark.network
def test_offline_generation_with_real_vworld_api(acceptance_api, tmp_path):
    import os

    real_key = os.environ.get("QPB_TEST_VWORLD_API_KEY")
    if not real_key:
        pytest.skip("QPB_TEST_VWORLD_API_KEY not set")
    config = _offline_config(SMALL_BBOX, min_zoom=15, max_zoom=16, tile_source="vworld")
    config["basemap"]["vworld_api_key"] = real_key
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")


# --- AC-QPB-022 -----------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "AC-QPB-022 requires opening the generated MBTiles layer in 'each explicitly supported "
        "QGIS/QField version', but that version matrix is not yet pinned (Open Question O-9 — "
        "NFR-QPB-001 explicitly says these versions must not be invented without verification). "
        "This test is a placeholder to be parametrized over the release-gate compatibility "
        "matrix once O-9 is resolved; see the traceability notes for this criterion. "
        "test_ac018_ac019_mbtiles_coverage_and_metadata_match_request already automates the "
        "*content-correctness* portion of MBTiles rendering readiness that does not depend on "
        "the specific QGIS/QField version."
    )
)
def test_ac022_mbtiles_renders_correctly_in_every_supported_qgis_qfield_version():
    raise AssertionError("should never run while skipped — see skip reason")
