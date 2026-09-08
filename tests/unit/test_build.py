"""Integration tests for qfield_builder.build.build_project.

Since no real QGIS/PyQGIS runtime is available in this environment, `qfield_builder.runtime.
check_runtime` and `qfield_builder.qgis_worker.build_qgis_project` are monkeypatched here to a
deterministic stub (`available=True` / a minimal-but-real `.qgs` XML write) so the *orchestration*
logic in build.py — atomicity, rollback, naming, offline MBTiles pipeline, manifest/README/
validation-report generation, cancellation, consent handling — is exercised end-to-end without
requiring PyQGIS itself. The real PyQGIS-calling implementation in qgis_worker.py is exercised
only by the (environment-gated, `qgis`-marked) acceptance suite; see the completion report for
which specific behaviors this cannot verify in this sandbox.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from qfield_builder import build as build_module
from qfield_builder import mbtiles as mbtiles_module
from qfield_builder import qgis_worker as qgis_worker_module
from qfield_builder import runtime as runtime_module
from qfield_builder import validate as validate_module
from qfield_builder.errors import BuildCancelledError

# DR-QPB-072/FR-QPB-127 (Decision Log D-66/D-68): every Types 1-3 build now resolves/validates
# reference data unconditionally (FR-QPB-105, further revised; Decision Log D-70), not only when
# `identification_enabled`.  The canonical D-95 workbook is selected explicitly below; the small
# fixture directory contributes only a test raster sidecar and cannot trigger legacy fallback.
_REFERENCE_DATA_VALID_SAMPLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "acceptance"
    / "qfield_project_builder"
    / "fixtures"
    / "reference_data_valid_sample"
)
_CANONICAL_REFERENCE_WORKBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "samples"
    / "taxonomy_sample.xlsx"
)

SITE_WKT = "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
INVALID_POLYGON_WKT = (
    "POLYGON((127.00 37.00, 127.01 37.01, 127.00 37.01, 127.01 37.00, 127.00 37.00))"
)
POINT_WKT = "POINT(127.005 37.005)"


def _fake_check_runtime(force_missing: bool = False, manual_path: str | None = None):
    if force_missing:
        return {
            "available": False,
            "message": "No compatible QGIS installation found.",
            "qgis_prefix_path": None,
        }
    return {
        "available": True,
        "message": "Stubbed QGIS runtime for unit testing.",
        "qgis_prefix_path": None,
    }


#: Populated by `_fake_build_qgis_project` on every call, so tests can assert on exactly what
#: `qfield_builder.build.build_project` resolved and passed through for `svg_relative_path`
#: (FR-QPB-120/FR-QPB-121, Decision Log D-61/D-65) without needing a real PyQGIS runtime.
_last_svg_relative_path_seen: list[str | None] = []
_last_probability_raster_relative_path_seen: list[str | None] = []


def _fake_build_qgis_project(
    gpkg_path,
    qgs_path,
    survey_type,
    project_crs,
    basemap_config,
    mbtiles_relative_path=None,
    identification_enabled=False,
    plantnet_config=None,
    svg_relative_path=None,
    ktsn_lookup_table_name=None,
    ktsn_taxonomy_table_name=None,
    canonical_runtime_lookup_resource=None,
    probability_raster_relative_path=None,
):
    from pathlib import Path

    _last_svg_relative_path_seen.append(svg_relative_path)
    _last_probability_raster_relative_path_seen.append(probability_raster_relative_path)

    online_key_embedded = False
    if basemap_config and basemap_config.get("mode") == "online":
        online_key_embedded = bool(basemap_config.get("consent_accepted"))
        key_fragment = basemap_config.get("vworld_api_key", "") if online_key_embedded else ""
    else:
        key_fragment = ""

    # FR-QPB-114-116 (Decision Log D-45): mirrors the VWorld consent-gated stub above, but for
    # the Pl@ntNet key project variable.
    plantnet_key_embedded = bool(plantnet_config and plantnet_config.get("consent_accepted"))
    plantnet_fragment = (
        plantnet_config.get("api_key", "") if plantnet_key_embedded and plantnet_config else ""
    )

    Path(qgs_path).parent.mkdir(parents=True, exist_ok=True)
    Path(qgs_path).write_text(
        f"<qgis projectname='stub'><!-- {key_fragment} --><layer>{gpkg_path}</layer>"
        f"<!-- {plantnet_fragment} --><!-- svg:{svg_relative_path} --></qgis>",
        encoding="utf-8",
    )
    return {
        "online_key_embedded": online_key_embedded,
        "plantnet_key_embedded": plantnet_key_embedded,
    }


@pytest.fixture(autouse=True)
def _stub_qgis(monkeypatch):
    monkeypatch.setattr(runtime_module, "check_runtime", _fake_check_runtime)
    monkeypatch.setattr(build_module, "runtime", runtime_module)
    monkeypatch.setattr(qgis_worker_module, "build_qgis_project", _fake_build_qgis_project)
    monkeypatch.setattr(build_module.qgis_worker, "build_qgis_project", _fake_build_qgis_project)
    # The fake builder deliberately writes only a minimal XML project and has no live QGIS layer
    # tree.  Make the unit seam's validation result explicit, instead of relying on the production
    # no-PyQGIS fallback (which must fail closed when visibility cannot be inspected).
    monkeypatch.setattr(validate_module, "_open_with_pyqgis", lambda _qgs_path: (True, False, []))
    _last_svg_relative_path_seen.clear()
    _last_probability_raster_relative_path_seen.clear()


def _base_config(survey_type: str, display_name: str = "Test Project") -> dict:
    config = {
        "project_display_name": display_name,
        "description": "Unit test fixture project",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": survey_type,
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "_test_reference_data_dir": str(_REFERENCE_DATA_VALID_SAMPLE_DIR),
        "canonical_reference_path": str(_CANONICAL_REFERENCE_WORKBOOK_PATH),
    }
    if survey_type in ("temporary_plots", "permanent_plots", "vegetation_mapping"):
        config["sites"] = [{"site_name": "Site A", "geom_wkt": SITE_WKT}]
    if survey_type == "permanent_plots":
        config["plots"] = [{"plot_name": "Plot A-1", "geom_wkt": POINT_WKT, "plot_size": "10x10"}]
    return config


@pytest.mark.parametrize(
    "survey_type", ["simple_inventory", "temporary_plots", "permanent_plots", "vegetation_mapping"]
)
def test_successful_build_produces_expected_artifacts(tmp_path, survey_type):
    config = _base_config(survey_type)
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert result["project_dir"] == str(out_dir)
    assert result["project_id"]
    assert result["project_slug"] == "test-project"
    assert (out_dir / f"{result['project_slug']}.qgs").exists()
    assert (out_dir / "data" / f"{result['project_slug']}.gpkg").exists()
    assert (out_dir / "attachments").is_dir()
    assert (out_dir / "MANIFEST.json").exists()
    assert (out_dir / "VALIDATION_REPORT.json").exists()
    assert (out_dir / "README_TRANSFER_KO.md").exists()
    plugin_path = out_dir / f"{result['project_slug']}.qml"
    assert plugin_path.exists()
    plugin_source = plugin_path.read_text(encoding="utf-8")
    assert "HTML 보고서 내보내기" in plugin_source
    assert "Identify attached photos" not in plugin_source
    assert re.search(r"\bTimer\s*\{", plugin_source) is None
    assert (out_dir / "icons" / "report-export.svg").is_file()
    assert not (out_dir / "icons" / "plant-identification.svg").exists()
    manifest = json.loads((out_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["required_files"]["identification_plugin"] == plugin_path.name
    assert result["gpkg_path"] == str(out_dir / "data" / f"{result['project_slug']}.gpkg")
    assert result["qgs_path"] == str(out_dir / f"{result['project_slug']}.qgs")


def test_type4_identification_bundles_and_registers_the_probability_stack(tmp_path, monkeypatch):
    """The display-only Type 4 widget still needs a stack to sample at its polygon centroid."""
    def fake_build_probability_stack(_source_dir, project_dir, cache_dir=None):
        del cache_dir
        stack = Path(project_dir) / "reference/rasters/occurrence_probability_multiband.tif"
        index = Path(project_dir) / "reference/rasters/occurrence_probability_bands.json"
        stack.parent.mkdir(parents=True, exist_ok=True)
        stack.write_bytes(b"test-stack")
        index.write_text('{"band_count": 1, "mapping": {}}', encoding="utf-8")
        return {"success": True, "discovered_species_count": 1}

    monkeypatch.setattr(
        build_module.probability_raster, "build_probability_stack", fake_build_probability_stack
    )
    config = _base_config("vegetation_mapping")
    config["identification_enabled"] = True
    config["probability_raster_source_dir"] = str(_REFERENCE_DATA_VALID_SAMPLE_DIR)
    out_dir = tmp_path / "out"

    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert _last_probability_raster_relative_path_seen == [
        "reference/rasters/occurrence_probability_multiband.tif"
    ]
    assert (out_dir / "reference/rasters/occurrence_probability_multiband.tif").is_file()
    manifest = json.loads((out_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["probability_raster"]["band_count"] == 1


def test_successful_build_does_not_create_durable_validation_report_sidecar(tmp_path):
    """A durable report beside the output is reserved for failed validation diagnostics."""
    out_dir = tmp_path / "out"

    result = build_module.build_project(_base_config("simple_inventory"), str(out_dir))

    assert result["success"] is True, result
    assert (out_dir / "VALIDATION_REPORT.json").exists()
    assert not (tmp_path / "out.VALIDATION_REPORT.json").exists()


def test_two_builds_get_distinct_project_ids(tmp_path):
    a = build_module.build_project(_base_config("simple_inventory"), str(tmp_path / "a"))
    b = build_module.build_project(_base_config("simple_inventory"), str(tmp_path / "b"))
    assert a["success"] and b["success"]
    assert a["project_id"] != b["project_id"]
    import uuid

    assert uuid.UUID(a["project_id"]).version == 4
    assert uuid.UUID(b["project_id"]).version == 4


def test_invalid_display_name_is_rejected_without_creating_output(tmp_path):
    config = _base_config("simple_inventory", display_name="..")
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "path_traversal"
    assert not out_dir.exists()


def test_missing_runtime_returns_structured_error(tmp_path):
    config = _base_config("simple_inventory")
    config["_test_force_missing_runtime"] = True
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "runtime_missing"
    assert not out_dir.exists()


def test_existing_nonempty_output_directory_is_not_overwritten(tmp_path):
    out_dir = tmp_path / "existing"
    out_dir.mkdir()
    sentinel = out_dir / "sentinel.txt"
    sentinel.write_text("do not touch")

    result = build_module.build_project(_base_config("simple_inventory"), str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "output_dir_exists"
    assert sentinel.read_text() == "do not touch"


def test_existing_empty_output_directory_is_not_overwritten(tmp_path):
    """E-QPB-008/AC-QPB-030: an already-existing but *empty* output directory must be rejected
    exactly like a non-empty one — neither E-QPB-008 nor AC-QPB-030 carries an emptiness
    qualifier, so an empty pre-existing directory is not a green light to delete/replace it."""
    out_dir = tmp_path / "existing_empty"
    out_dir.mkdir()

    result = build_module.build_project(_base_config("simple_inventory"), str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "output_dir_exists"
    assert out_dir.exists()
    assert not any(out_dir.iterdir())


def test_invalid_geometry_is_rejected_and_leaves_no_partial_output(tmp_path):
    config = _base_config("temporary_plots")
    config["sites"] = [{"site_name": "Invalid Site", "geom_wkt": INVALID_POLYGON_WKT}]
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "invalid_geometry"
    assert not out_dir.exists()


def test_failed_validation_preserves_durable_report_without_promoting_project(
    tmp_path, monkeypatch
):
    config = _base_config("simple_inventory")
    out_dir = tmp_path / "out"
    report = {
        "opens_without_repair_warning": False,
        "missing_layer_warning": False,
        "issues": [
            {
                "code": "layer_tree_visibility_unverified",
                "message": "visibility could not be inspected",
            }
        ],
    }
    monkeypatch.setattr(validate_module, "validate_project", lambda _project_dir: report)

    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is False
    assert result["error_code"] == "project_validation_failed"
    assert not out_dir.exists()
    report_path = result["validation_report_path"]
    assert report_path
    assert Path(report_path).exists()
    assert json.loads(Path(report_path).read_text(encoding="utf-8")) == report
    assert result["validation_report"] == report


def test_online_consent_declined_omits_key_and_layer(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "online",
        "vworld_api_key": "SUPER-SECRET-KEY",
        "layer": "Base",
        "consent_accepted": False,
        "remember_key": False,
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    assert result["manifest_security_warning"] is False
    for path in out_dir.rglob("*"):
        if path.is_file():
            assert "SUPER-SECRET-KEY" not in path.read_text(encoding="utf-8", errors="ignore")


def test_online_consent_accepted_embeds_key_only_in_qgs(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "online",
        "vworld_api_key": "SUPER-SECRET-KEY",
        "layer": "Base",
        "consent_accepted": True,
        "remember_key": False,
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    assert result["manifest_security_warning"] is True

    qgs_text = open(result["qgs_path"], encoding="utf-8").read()
    assert "SUPER-SECRET-KEY" in qgs_text

    manifest = json.loads((out_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest_text = json.dumps(manifest)
    assert "SUPER-SECRET-KEY" not in manifest_text
    assert manifest["security"]["online_layer_key_embedded_warning"] is True

    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix != ".qgs":
            assert "SUPER-SECRET-KEY" not in path.read_text(encoding="utf-8", errors="ignore")


def test_offline_build_success_produces_mbtiles_under_hard_limit(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
            "vworld_api_key": "FAKE",
            "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    mbtiles_path = out_dir / "basemap" / "offline.mbtiles"
    assert mbtiles_path.exists()
    assert mbtiles_path.stat().st_size <= 1024 * 1024 * 1024

    qgs_text = open(result["qgs_path"], encoding="utf-8").read()
    assert "FAKE" not in qgs_text


def test_offline_build_remember_key_actually_persists_the_key(tmp_path):
    """Reviewer-round fix (compounding issue found alongside the FR-QPB-076 disclosure-text
    defect): the wizard's "remember this key" checkbox is shown and enabled for offline mode too
    (`ConnectivityBasemapPage`), but before this fix `_collect_config()`'s offline branch never
    read `remember_key`, so checking it silently had no effect at all -- neither an error nor any
    other indication the request was ignored. This mirrors the existing online-mode coverage of
    the same underlying `apply_retention_policy` mechanism (see
    `test_credential_store.py`/`test_wizard.py`'s equivalent online-mode assertions) but for
    offline mode specifically, which had zero coverage of this mechanism before."""
    from qfield_builder import credential_store as credential_store_module

    credential_store_module.establish_password("a-real-password")  # noqa: S106

    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
            "vworld_api_key": "OFFLINE-KEY-TO-REMEMBER",
            "layer": "Base",
        "remember_key": True,
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True

    # The critical assertion: the key must actually be in the encrypted store now, not silently
    # dropped -- this is exactly what the reviewer's finding calls a "silent no-op".
    assert credential_store_module.get_remembered_key() == "OFFLINE-KEY-TO-REMEMBER"

    # Never written into the delivered project output itself (NFR-QPB-058) -- the encrypted store
    # lives entirely outside `out_dir`, mirroring the online-mode assertions above.
    for path in out_dir.rglob("*"):
        if path.is_file():
            assert "OFFLINE-KEY-TO-REMEMBER" not in path.read_text(
                encoding="utf-8", errors="ignore"
            )


def test_offline_build_remember_key_false_does_not_persist_anything(tmp_path):
    """Companion regression check: when `remember_key` is `False` (or absent), nothing is written
    to the encrypted store for offline mode -- mirrors the existing online-mode convention."""
    from qfield_builder import credential_store as credential_store_module

    credential_store_module.establish_password("a-real-password")  # noqa: S106

    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
            "vworld_api_key": "SHOULD-NOT-BE-REMEMBERED",
            "layer": "Base",
        "remember_key": False,
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    assert credential_store_module.get_remembered_key() is None


def test_offline_build_missing_vworld_api_key_fails_fast_with_actionable_message(tmp_path):
    """Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058): `build.py`'s own proactive check, exercised
    directly here at the unit level (mirroring the acceptance suite's own equivalent, offline/
    `qgis`-marked coverage in
    `tests/acceptance/qfield_project_builder/test_offline_vworld_api_key_collection.py`, which
    this unit test does not duplicate -- it instead pins that the failure happens *before* any
    other offline-mode work, using `_test_cancel_after_phase`-style fast-fail semantics)."""
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        # Deliberately no "vworld_api_key" at all.
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "vworld_api_key_missing"
    message = result.get("error_message") or ""
    assert message.strip()
    assert message != "'vworld_api_key'"
    assert not out_dir.exists()


def test_offline_build_blank_vworld_api_key_fails_fast_with_actionable_message(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "   ",  # present but blank -- must be treated the same as missing.
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "vworld_api_key_missing"
    assert not out_dir.exists()


def test_offline_missing_key_wins_over_test_download_cancellation_hook(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    config["_test_cancel_after_phase"] = "basemap_download"

    result = build_module.build_project(config, str(tmp_path / "out"))

    assert result["success"] is False
    assert result["cancelled"] is False
    assert result["error_code"] == "vworld_api_key_missing"


def test_offline_build_blocked_by_pregeneration_estimate(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
            "vworld_api_key": "FAKE",
            "layer": "Base",
        "bbox": {"min_lon": 126.0, "min_lat": 33.0, "max_lon": 130.0, "max_lat": 39.0},
        "min_zoom": 1,
        "max_zoom": 18,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 20000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "offline_size_exceeded"
    assert not out_dir.exists()


@pytest.mark.parametrize("failure_mode", ["quota_error", "auth_error", "rate_limit_error"])
def test_offline_build_provider_errors_terminate_gracefully(tmp_path, failure_mode):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "FAKE",
        "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": failure_mode, "tile_bytes": 5000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"]
    assert not out_dir.exists()
    assert not any(out_dir.rglob("*.mbtiles")) if out_dir.exists() else True


def test_offline_build_oversized_output_aborts_and_cleans_up(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "FAKE",
        "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 8,
        "max_zoom": 13,
        "tile_source": {"fake": {"mode": "oversized", "tile_bytes": 8000}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is False
    assert result["error_code"]
    assert not out_dir.exists()


def test_cancellation_during_basemap_download_leaves_no_partial_output(tmp_path):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "FAKE",
        "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 14,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    config["_test_cancel_after_phase"] = "basemap_download"
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["cancelled"] is True
    assert result["success"] is False
    assert not out_dir.exists()


def test_build_project_passes_production_cancel_callback_into_mbtiles(tmp_path, monkeypatch):
    config = _base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "FAKE",
        "layer": "Base",
        "bbox": {"min_lon": 127.0, "min_lat": 37.0, "max_lon": 127.01, "max_lat": 37.01},
        "min_zoom": 10,
        "max_zoom": 12,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 5000}},
    }
    def cancel_callback() -> bool:
        return False

    seen: dict[str, object] = {}

    def fake_build_mbtiles(*_args, **kwargs):
        seen["should_cancel"] = kwargs["should_cancel"]
        raise BuildCancelledError("cancelled in the MBTiles operation")

    monkeypatch.setattr(mbtiles_module, "build_mbtiles", fake_build_mbtiles)
    out_dir = tmp_path / "out"

    result = build_module.build_project(config, str(out_dir), should_cancel=cancel_callback)

    assert seen["should_cancel"] is cancel_callback
    assert result["cancelled"] is True
    assert result["error_code"] == "cancelled"
    assert not out_dir.exists()


def test_no_temp_directories_leaked_after_build(tmp_path):
    import tempfile
    from pathlib import Path

    tmp_root = Path(tempfile.gettempdir())
    before = {p.name for p in tmp_root.glob("qpb-build-*")}
    config = _base_config("simple_inventory")
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    after = {p.name for p in tmp_root.glob("qpb-build-*")}
    assert after - before == set()


def test_output_dir_exists_message_does_not_offer_a_replace_with_backup_operation(tmp_path):
    """Fix for reviewer observation 1: the application has no built-in "replace with backup"
    operation, so the output_dir_exists error message must not imply one exists. It must only
    instruct the user to choose a different project name or a different output folder."""
    out_dir = tmp_path / "existing"
    out_dir.mkdir()

    result = build_module.build_project(_base_config("simple_inventory"), str(out_dir))
    assert result["success"] is False
    assert result["error_code"] == "output_dir_exists"
    message = result["error_message"] or ""
    assert "백업" not in message  # "backup"
    assert "교체" not in message  # "replace"
    assert "다른" in message and (  # "different"
        "이름" in message or "폴더" in message  # "name" / "folder"
    )


def test_finalization_time_race_with_newly_appeared_destination_is_not_overwritten(
    tmp_path, monkeypatch
):
    """Fix for reviewer observation 2: if a destination directory appears *after* the initial
    existence check but *before* the finalization move (e.g. another process wins a race), the
    build must abort cleanly, must never delete or move into that destination, and must report
    output_dir_exists -- exactly like the initial-time check. This exercises the finalization
    check specifically (not the initial check) by making the destination appear as a side effect
    of qgis_worker.build_qgis_project, which runs after the initial existence check but before
    the finalization move.
    """
    import tempfile
    from pathlib import Path as _Path

    out_dir = tmp_path / "out"
    assert not out_dir.exists()

    def _fake_build_qgis_project_then_create_destination(
        gpkg_path,
        qgs_path,
        survey_type,
        project_crs,
        basemap_config,
        mbtiles_relative_path=None,
        identification_enabled=False,
        plantnet_config=None,
        svg_relative_path=None,
        ktsn_lookup_table_name=None,
        ktsn_taxonomy_table_name=None,
        canonical_runtime_lookup_resource=None,
    ):
        result = _fake_build_qgis_project(
            gpkg_path,
            qgs_path,
            survey_type,
            project_crs,
            basemap_config,
            mbtiles_relative_path,
            identification_enabled,
            plantnet_config,
            svg_relative_path,
            ktsn_lookup_table_name,
            ktsn_taxonomy_table_name,
            canonical_runtime_lookup_resource,
        )
        # Simulate another process/thread winning a race and creating the destination
        # directory in between the initial check and the finalization move.
        out_dir.mkdir(parents=True)
        (out_dir / "sentinel.txt").write_text("do not touch")
        return result

    monkeypatch.setattr(
        build_module.qgis_worker,
        "build_qgis_project",
        _fake_build_qgis_project_then_create_destination,
    )

    tmp_root = _Path(tempfile.gettempdir())
    before = {p.name for p in tmp_root.glob("qpb-build-*")}

    config = _base_config("simple_inventory")
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is False
    assert result["error_code"] == "output_dir_exists"

    # The destination directory that appeared mid-build must be left completely untouched.
    assert out_dir.exists()
    sentinel = out_dir / "sentinel.txt"
    assert sentinel.exists()
    assert sentinel.read_text() == "do not touch"
    assert set(p.name for p in out_dir.iterdir()) == {"sentinel.txt"}

    # This build's own temp artifacts must still be cleaned up.
    after = {p.name for p in tmp_root.glob("qpb-build-*")}
    assert after - before == set()


def test_manifest_records_correct_survey_type_and_ids(tmp_path):
    config = _base_config("permanent_plots")
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    manifest = json.loads((out_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["survey_type"] == "permanent_plots"
    assert manifest["project_id"] == result["project_id"]
    assert manifest["project_slug"] == result["project_slug"]


def test_seed_sites_and_plots_are_written_to_the_gpkg(tmp_path):
    config = _base_config("permanent_plots")
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))
    assert result["success"] is True
    conn = sqlite3.connect(result["gpkg_path"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM site;").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM plot;").fetchone()[0] == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------------------------
# FR-QPB-120/FR-QPB-121/AC-QPB-101 (Decision Log D-61/D-65): `_resolve_symbol_styling` and
# `build_project`'s own `symbol_styling`/`symbols_dir` config/return additions. The real PyQGIS
# symbology application itself is covered by `test_qgis_worker_symbol_styling.py` (qgis-marked);
# this file's own `_stub_qgis` fixture (above) stubs `qgis_worker.build_qgis_project`, so these
# tests exercise `build.py`'s own orchestration -- resolving the fetch, embedding the SVG file,
# and reporting `symbols_dir` -- without requiring a real QGIS runtime.
# ---------------------------------------------------------------------------------------------

_FAKE_SVG_CONTENT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'


def test_build_omitting_symbol_styling_never_creates_a_symbols_dir_and_passes_none_through(
    tmp_path,
):
    config = _base_config("simple_inventory")
    result = build_module.build_project(config, str(tmp_path / "out"))

    assert result["success"] is True
    assert result["symbols_dir"] is None
    assert not (tmp_path / "out" / "symbols").exists()
    assert _last_svg_relative_path_seen == [None]


def test_build_with_explicit_minimalist_mode_never_creates_a_symbols_dir(tmp_path):
    config = _base_config("simple_inventory")
    config["symbol_styling"] = {"mode": "minimalist"}
    result = build_module.build_project(config, str(tmp_path / "out"))

    assert result["success"] is True
    assert result["symbols_dir"] is None
    assert _last_svg_relative_path_seen == [None]


def test_build_with_successful_tabler_fetch_embeds_the_svg_and_reports_symbols_dir(tmp_path):
    config = _base_config("simple_inventory")
    config["symbol_styling"] = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert result["symbols_dir"] == str(out_dir / "symbols")
    svg_path = out_dir / "symbols" / "map-pin.svg"
    assert svg_path.is_file()
    assert svg_path.read_text(encoding="utf-8") == _FAKE_SVG_CONTENT
    assert _last_svg_relative_path_seen == ["symbols/map-pin.svg"]


def test_type4_ignores_point_symbol_styling_and_creates_no_symbols_dir(tmp_path):
    config = _base_config("vegetation_mapping")
    config["symbol_styling"] = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    out_dir = tmp_path / "out"

    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert result["symbols_dir"] is None
    assert not (out_dir / "symbols").exists()
    assert _last_svg_relative_path_seen == [None]


@pytest.mark.parametrize("failure_mode", ["network_error", "http_error", "timeout"])
def test_build_with_failed_tabler_fetch_falls_back_without_blocking_generation(
    tmp_path, failure_mode
):
    config = _base_config("simple_inventory")
    config["symbol_styling"] = {
        "mode": "tabler_icon",
        "tabler_icon_name": "map-pin",
        "tabler_svg_fetch": {"fake": {"mode": failure_mode, "svg_content": ""}},
    }
    out_dir = tmp_path / f"out_{failure_mode}"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert result["symbols_dir"] is None
    assert not (out_dir / "symbols").exists()
    assert _last_svg_relative_path_seen == [None]


def test_build_with_tabler_icon_mode_but_no_icon_name_falls_back_to_minimalist(tmp_path):
    """FR-QPB-121: 'the user does not select an icon' -> the minimalist default remains in use;
    never a build failure, even though `mode` is `"tabler_icon"`."""
    config = _base_config("simple_inventory")
    config["symbol_styling"] = {"mode": "tabler_icon", "tabler_icon_name": ""}
    result = build_module.build_project(config, str(tmp_path / "out"))

    assert result["success"] is True, result
    assert result["symbols_dir"] is None
    assert _last_svg_relative_path_seen == [None]


def test_build_with_a_different_icon_name_embeds_it_under_its_own_filename(tmp_path):
    config = _base_config("simple_inventory")
    config["symbol_styling"] = {
        "mode": "tabler_icon",
        "tabler_icon_name": "leaf",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert (out_dir / "symbols" / "leaf.svg").is_file()
    assert _last_svg_relative_path_seen == ["symbols/leaf.svg"]


def test_build_rejects_a_malformed_icon_name_without_reaching_the_fetch_or_creating_a_file(
    tmp_path, monkeypatch
):
    """`_resolve_symbol_styling`'s own defensive `is_valid_icon_name_shape` check (mirrors
    `symbol_styling.fetch_tabler_icon_svg_real`'s own guard): a malformed name is treated the
    same as "no icon selected," never reaching the fetch dispatcher at all."""

    def _fail(*_a, **_k):
        raise AssertionError("resolve_svg_fetch must not be called for a malformed icon name")

    monkeypatch.setattr(build_module.symbol_styling, "resolve_svg_fetch", _fail)

    config = _base_config("simple_inventory")
    config["symbol_styling"] = {
        "mode": "tabler_icon",
        "tabler_icon_name": "../../etc/passwd",
        "tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": _FAKE_SVG_CONTENT}},
    }
    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    assert result["symbols_dir"] is None
    assert not (out_dir / "symbols").exists()
