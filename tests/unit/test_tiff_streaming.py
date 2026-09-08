"""TIFF streaming keeps input validation and atomic publication without repeated opens."""

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin

from qfield_builder import probability_raster as pr
from qfield_builder import standalone_gis as gis


def _write(path, **changes):
    profile = dict(
        driver="GTiff", width=2, height=2, count=1, dtype="float32", nodata=-9999,
        crs="EPSG:4326", transform=from_origin(127, 38, 0.1, 0.1),
    )
    profile.update(changes)
    values = np.full((profile["count"], profile["height"], profile["width"]), 0.25,
                     dtype=profile["dtype"])
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(values)


def test_build_opens_each_source_once_and_preserves_pixels(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    names = ["가상풀", "예시나무"]
    for name in names:
        _write(source / f"{name}.tif")
    original_open = rasterio.open
    counts, handles, output_options = Counter(), [], []

    def tracked_open(path, *args, **kwargs):
        dataset = original_open(path, *args, **kwargs)
        if Path(path).parent == source:
            counts[Path(path).name] += 1
            handles.append(dataset)
        elif args and args[0] == "w":
            output_options.append(kwargs)
        return dataset

    monkeypatch.setattr(gis.rasterio, "open", tracked_open)
    result = pr.build_probability_stack(str(source), str(tmp_path / "project"), korean_names=names)
    assert result["success"], result
    assert counts == {f"{name}.tif": 1 for name in names}
    assert all(dataset.closed for dataset in handles)
    assert output_options[0]["zlevel"] == 6
    with original_open(result["stack_path"]) as dataset:
        assert dataset.descriptions == tuple(names)
        np.testing.assert_array_equal(dataset.read(), np.full((2, 2, 2), 0.25))


@pytest.mark.parametrize("change,code", [
    ({"nodata": 0}, "source_nodata_incompatible"),
    ({"count": 2}, "source_not_single_band"),
    ({"width": 3}, "source_geometry_incompatible"),
    ({"dtype": "float64"}, "source_geometry_incompatible"),
    ({"crs": "EPSG:3857"}, "source_geometry_incompatible"),
    ({"crs": None}, "source_geometry_incompatible"),
    ({"transform": Affine(0, 0, 127, 0, 0, 38)}, "source_geometry_incompatible"),
    ({"corrupt": True}, "raster_operation_failed"),
])
def test_late_invalid_source_preserves_previous_stack_and_cleans_staging(tmp_path, change, code):
    source = tmp_path / "source"
    source.mkdir()
    names = ["가상풀", "예시나무"]
    for name in names:
        _write(source / f"{name}.tif")
    project = tmp_path / "project"
    result = pr.build_probability_stack(str(source), str(project), korean_names=names)
    assert result["success"], result
    previous = {Path(result[key]): Path(result[key]).read_bytes()
                for key in ("stack_path", "index_path")}
    last = source / f"{names[-1]}.tif"
    if change.get("corrupt"):
        last.write_bytes(b"II*\x00broken")
    else:
        _write(last, **change)
    result = pr.build_probability_stack(str(source), str(project), korean_names=names)
    assert not result["success"] and result["error_code"] == code
    assert all(path.read_bytes() == content for path, content in previous.items())
    assert not list(tmp_path.glob(".qpb-probability-*"))


@pytest.mark.parametrize("endian", ["LITTLE", "BIG"])
def test_real_bigtiff_is_accepted_as_source_and_cache(tmp_path, endian):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "가상풀.tif"
    _write(path, BIGTIFF="YES", ENDIANNESS=endian)
    assert path.read_bytes()[:4] in (b"II+\x00", b"MM\x00+")
    result = pr.validate_probability_raster_sources(str(source), korean_names=["가상풀"])
    assert result["ok"], result
    result = pr.build_probability_stack(str(source), str(tmp_path / "project"),
                                        korean_names=["가상풀"])
    assert result["success"], result
    assert pr.inspect_probability_stack(result["stack_path"], str(source),
                                         korean_names=["가상풀"])["valid"]
    species, _, error = pr._inventory(str(source), ["가상풀"])
    assert error is None
    cache = tmp_path / "cache"
    cache.mkdir()
    cached_stack = cache / pr.CACHE_STACK_FILENAME
    _write(cached_stack, BIGTIFF="YES", ENDIANNESS=endian)
    cached_index = cache / pr.CACHE_INDEX_FILENAME
    cached_index.write_text(json.dumps(pr._index_payload(species)), encoding="utf-8")
    assert pr._cached_stack_matches(cache, species) == (cached_stack, cached_index)
