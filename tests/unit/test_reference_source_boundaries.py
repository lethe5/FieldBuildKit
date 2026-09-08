"""Non-GUI contracts for the D-95 source and release boundaries."""

from __future__ import annotations

from pathlib import Path

from qfield_builder import build as build_module
from qfield_builder import reference_bundle
from qfield_builder import runtime as runtime_module


def _minimal_config(**overrides) -> dict:
    config = {
        "project_display_name": "Source boundary test",
        "survey_type": "simple_inventory",
        "basemap": {"mode": "none"},
        "identification_enabled": False,
    }
    config.update(overrides)
    return config


def _stub_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "check_runtime",
        lambda **_kwargs: {"available": True, "message": "stub", "qgis_prefix_path": None},
    )
    monkeypatch.setattr(build_module, "runtime", runtime_module)


def test_normal_build_does_not_downgrade_to_legacy_sources(tmp_path, monkeypatch):
    repo_root = tmp_path / "checkout"
    reference_root = repo_root / "storage" / "reference"
    (reference_root / "tables").mkdir(parents=True)
    (reference_root / "tables" / "tb_leco_nib_ktsn_dtl_gat.csv").write_text(
        "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list\n",
        encoding="utf-8",
    )
    (reference_root / "rasters" / "bce_inverse_corrected_probability_maps").mkdir(
        parents=True
    )
    monkeypatch.setattr(build_module, "repo_or_bundle_root", lambda: repo_root)
    _stub_runtime(monkeypatch)
    monkeypatch.setattr(
        build_module.reference_bundle,
        "validate_reference_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("normal canonical build reached legacy validation")
        ),
    )

    result = build_module.build_project(_minimal_config(), str(tmp_path / "output"))

    assert result["success"] is True
    assert result["ktsn_lookup_table_name"] is None


def test_test_reference_override_also_requires_explicit_compatibility_mode(tmp_path, monkeypatch):
    legacy_root = tmp_path / "legacy-reference"
    (legacy_root / "tables").mkdir(parents=True)
    (legacy_root / "tables" / "tb_leco_nib_ktsn_dtl_gat.csv").write_text(
        "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list\n",
        encoding="utf-8",
    )
    (legacy_root / "rasters" / "bce_inverse_corrected_probability_maps").mkdir(
        parents=True
    )
    _stub_runtime(monkeypatch)

    result = build_module.build_project(
        _minimal_config(_test_reference_data_dir=str(legacy_root)), str(tmp_path / "output")
    )

    assert result["success"] is True
    assert result["ktsn_lookup_table_name"] is None


def test_missing_explicit_canonical_path_never_falls_back_even_in_compatibility_mode(
    tmp_path, monkeypatch
):
    legacy_root = tmp_path / "legacy-reference"
    (legacy_root / "tables").mkdir(parents=True)
    (legacy_root / "tables" / "tb_leco_nib_ktsn_dtl_gat.csv").write_text(
        "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list\n",
        encoding="utf-8",
    )
    (legacy_root / "rasters" / "bce_inverse_corrected_probability_maps").mkdir(
        parents=True
    )
    _stub_runtime(monkeypatch)

    result = build_module.build_project(
        _minimal_config(
            _test_reference_data_dir=str(legacy_root),
            reference_compatibility_mode=build_module.LEGACY_REFERENCE_COMPATIBILITY_MODE,
            canonical_reference_path=str(tmp_path / "missing-canonical.xlsx"),
        ),
        str(tmp_path / "output"),
    )

    assert result["success"] is False
    assert result["error_code"] == "reference_data_missing"
    assert "확정한 canonical" in result["error_message"]


def test_explicit_legacy_compatibility_predicate_is_narrow():
    assert build_module._legacy_reference_compatibility_requested(
        {"reference_compatibility_mode": build_module.LEGACY_REFERENCE_COMPATIBILITY_MODE}
    )
    assert not build_module._legacy_reference_compatibility_requested({})
    assert not build_module._legacy_reference_compatibility_requested(
        {"reference_compatibility_mode": "legacy"}
    )


def test_only_fictional_workbook_is_distributed():
    from qfield_builder.canonical_reference import ingest_canonical_workbook

    root = Path(__file__).resolve().parents[2]
    workbook = root / "resources/samples/taxonomy_sample.xlsx"
    result = ingest_canonical_workbook(str(workbook))
    assert result["success"]
    assert result["row_count"] == 3
    assert all(row["ktsn"].startswith("sample-") for row in result["rows"])
    assert not (root / "packaging/reference_source/tables/Rpt_2026-08-29_List.xlsx").exists()


def test_release_staging_materializes_canonical_outputs_without_workbook_copy(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    workbook = repo_root / "resources/samples/taxonomy_sample.xlsx"
    raster_dir = tmp_path / "provisioned-rasters"
    raster_dir.mkdir()
    (raster_dir / "example.tif").write_bytes(b"test-raster")
    destination = tmp_path / "filtered-reference"

    reference_bundle.prepare_filtered_reference_bundle(
        workbook, destination, raster_dir=raster_dir
    )

    assert not list(destination.rglob("*.xlsx"))
    assert (destination / "filtered" / "ktsn_lookup.csv").is_file()
    raster_output = (
        destination / "rasters" / "bce_inverse_corrected_probability_maps" / "example.tif"
    )
    assert raster_output.read_bytes() == b"test-raster"
    assert (destination / "bundle_manifest.json").is_file()


def test_release_entry_points_have_no_legacy_source_dependency():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "packaging" / "build_macos_app.sh").read_text(encoding="utf-8")
    prepare = (repo_root / "packaging" / "prepare_reference_bundle.py").read_text(encoding="utf-8")
    source = (repo_root / "qfield_builder" / "reference_bundle.py").read_text(encoding="utf-8")
    release_body = source.split("def prepare_filtered_reference_bundle", 1)[1].split(
        "def _extract_ktsn_lookup_csv", 1
    )[0]

    for text in (script, prepare, release_body):
        assert "tb_leco_nib_ktsn_dtl_gat.csv" not in text
        assert "2025년 국가생물종목록_v1.0.xlsx" not in text
    assert "packaging/build_app.py" in script
    assert "--canonical-workbook" not in script
    assert "--source \"" not in script
