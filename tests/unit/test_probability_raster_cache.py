"""Fast-path checks for the packaged multiband probability-raster cache."""

import json
from pathlib import Path

from qfield_builder import probability_raster


def _write_tiff(path: Path) -> None:
    path.write_bytes(b"II*\x00cached-test-raster")


def test_matching_packaged_cache_is_materialized_without_dispatching_gdal(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    _write_tiff(source / "bce_inverse_corrected_probability_테스트종.tif")
    species, _excluded, error = probability_raster._inventory(str(source))
    assert error is None

    cache = tmp_path / "cache"
    cache.mkdir()
    _write_tiff(cache / probability_raster.CACHE_STACK_FILENAME)
    (cache / probability_raster.CACHE_INDEX_FILENAME).write_text(
        json.dumps(probability_raster._index_payload(species), ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(
        probability_raster,
        "_dispatch_gdal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("GDAL must not run")),
    )

    result = probability_raster.build_probability_stack(
        str(source), str(tmp_path / "project"), cache_dir=str(cache)
    )

    assert result["success"] is True
    assert result["cache_reused"] is True
    assert Path(result["stack_path"]).read_bytes() == (
        cache / probability_raster.CACHE_STACK_FILENAME
    ).read_bytes()


def test_cache_with_a_different_source_inventory_is_rejected(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    source_raster = source / "bce_inverse_corrected_probability_테스트종.tif"
    _write_tiff(source_raster)
    species, _excluded, error = probability_raster._inventory(str(source))
    assert error is None

    cache = tmp_path / "cache"
    cache.mkdir()
    _write_tiff(cache / probability_raster.CACHE_STACK_FILENAME)
    stale_index = probability_raster._index_payload(species)
    stale_index["source_inventory_signature"] = "stale"
    (cache / probability_raster.CACHE_INDEX_FILENAME).write_text(
        json.dumps(stale_index, ensure_ascii=False), encoding="utf-8"
    )

    assert probability_raster._cached_stack_matches(cache, species) is None
