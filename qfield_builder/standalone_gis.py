"""GIS operations using independently packaged Rasterio/Fiona, never a QGIS installation."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from pathlib import Path

import fiona
import numpy as np
import rasterio
from fiona.transform import transform_geom
from rasterio.warp import transform
from rasterio.windows import Window

from .errors import BuildError

NODATA = -9999.0


def reproject_uploaded_gpkg_layer(source_path, source_layer_name, destination_path, target_crs):
    return _reproject(source_path, destination_path, target_crs, layer=source_layer_name)


def reproject_uploaded_shapefile(source_path, destination_path, target_crs, source_crs=None):
    return _reproject(source_path, destination_path, target_crs, source_crs=source_crs)


def _reproject(source_path, destination_path, target_crs, *, layer=None, source_crs=None):
    if Path(destination_path).exists():
        raise BuildError("output_dir_exists", "좌표 변환 출력 파일이 이미 존재합니다.")
    Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
    with fiona.open(source_path, layer=layer) as source:
        crs = source.crs_wkt or source_crs
        if not crs:
            raise BuildError("missing_upload_crs", "업로드 자료의 좌표계를 확인할 수 없습니다.")
        schema = dict(source.schema, geometry="MultiPolygon")
        with fiona.open(
            destination_path, "w", driver="GPKG", layer="reprojected", schema=schema, crs=target_crs
        ) as output:
            for feature in source:
                geometry = feature.geometry
                if geometry is None or geometry.type not in ("Polygon", "MultiPolygon"):
                    raise BuildError("invalid_geometry", "사이트 자료는 폴리곤이어야 합니다.")
                geometry = transform_geom(crs, target_crs, geometry)
                if geometry.type == "Polygon":
                    geometry = {"type": "MultiPolygon", "coordinates": [geometry.coordinates]}
                output.write({"geometry": geometry, "properties": dict(feature.properties)})
    return {"success": True, "output_path": destination_path}


def _source_metadata(source, baseline):
    """Validate the open dataset used by either a metadata check or the streaming writer."""
    if source.count != 1:
        return None, {
            "ok": False,
            "error_code": "source_not_single_band",
            "message": f"단일 밴드 래스터가 아닙니다: {Path(source.name).name}",
        }
    if source.nodata != NODATA and not (source.nodata is not None and math.isnan(source.nodata)):
        return None, {
            "ok": False,
            "error_code": "source_nodata_incompatible",
            "message": "확률 래스터 NoData 값은 -9999 또는 NaN이어야 합니다.",
        }
    if not source.crs or source.transform.determinant == 0:
        return None, {
            "ok": False,
            "error_code": "source_geometry_incompatible",
            "message": "확률 래스터의 좌표계 또는 격자가 유효하지 않습니다.",
        }
    metadata = (source.width, source.height, source.transform, source.crs, source.dtypes)
    if baseline is not None and metadata != baseline:
        return None, {
            "ok": False,
            "error_code": "source_geometry_incompatible",
            "message": "확률 래스터의 격자/좌표계/자료형이 일치하지 않습니다.",
        }
    return metadata, None


def _validate_sources_gdal(sources):
    baseline = None
    for item in sources:
        with rasterio.open(item["path"]) as source:
            baseline, error = _source_metadata(source, baseline)
            if error:
                return error
    return {"ok": bool(sources), "error_code": None if sources else "source_empty"}


def _build_probability_stack_gdal(sources, output_path):
    if not sources:
        return {"ok": False, "error_code": "source_empty"}
    baseline = None
    # Only the output and the current input stay open. Failed staging is never published.
    with ExitStack() as stack:
        for band, item in enumerate(sources, start=1):
            with rasterio.open(item["path"]) as source:
                baseline, error = _source_metadata(source, baseline)
                if error:
                    return error
                if band == 1:
                    profile = source.profile.copy()
                    profile.update(
                        driver="GTiff", count=len(sources), nodata=NODATA,
                        compress="deflate", zlevel=6, interleave="band",
                        predictor=3 if profile["dtype"].startswith("float") else 2,
                        BIGTIFF="IF_SAFER",
                    )
                    output = stack.enter_context(rasterio.open(output_path, "w", **profile))
                for _, window in source.block_windows(1):
                    values = source.read(1, window=window)
                    values[np.isnan(values)] = NODATA
                    output.write(values, band, window=window)
            output.set_band_description(band, item["name"])
            output.update_tags(band, QPB_SOURCE_BASENAME=Path(item["path"]).name)
    return {"ok": True}


def _inspect_probability_stack_gdal(stack_path, sources):
    with rasterio.open(stack_path) as stack:
        represented = stack.count == len(sources)
        values_match = nodata_match = represented
        for band, item in enumerate(sources, start=1):
            if band > stack.count:
                break
            represented &= (
                stack.descriptions[band - 1] == item["name"]
                and stack.tags(band).get("QPB_SOURCE_BASENAME") == Path(item["path"]).name
            )
            with rasterio.open(item["path"]) as source:
                nodata_match &= stack.nodatavals[band - 1] == NODATA and (
                    source.nodata == NODATA or (source.nodata is not None and math.isnan(source.nodata))
                )
                same_grid = (
                    source.shape == stack.shape
                    and source.crs == stack.crs
                    and source.transform == stack.transform
                )
                values_match &= same_grid
                if same_grid:
                    for _, window in source.block_windows(1):
                        expected = source.read(1, window=window)
                        expected[np.isnan(expected)] = NODATA
                        values_match &= np.array_equal(
                            expected,
                            stack.read(band, window=window),
                            equal_nan=True,
                        )
        return {
            "ok": True,
            "report": {
                "valid": bool(represented and values_match and nodata_match),
                "band_count": stack.count,
                "source_files_represented_once": bool(represented),
                "pixel_crosscheck": {
                    "values_match": bool(values_match),
                    "nodata_match": bool(nodata_match),
                },
                "metadata": {"nodata": stack.nodata},
            },
        }


def _sample_probability_gdal(stack_path, band, lon, lat):
    with rasterio.open(stack_path) as source:
        if not source.crs or not 1 <= band <= source.count:
            return {"ok": False, "reason": "raster_layer_unavailable"}
        xs, ys = transform("EPSG:4326", source.crs, [lon], [lat])
        row, col = source.index(xs[0], ys[0])
        if not (0 <= row < source.height and 0 <= col < source.width):
            return {"ok": False, "reason": "raster_missing_nodata_or_outside_extent"}
        value = float(source.read(band, window=Window(col, row, 1, 1))[0, 0])
        if not math.isfinite(value) or value == source.nodatavals[band - 1]:
            return {"ok": False, "reason": "raster_missing_nodata_or_outside_extent"}
        if value > 1:
            return {"ok": False, "reason": "raster_invalid_value"}
        return {"ok": True, "value": max(0.0, value)}


def _inspect_probability_project_pyqgis(project_dir):
    """Compatibility entry point for structural raster-layer inspection."""
    root = Path(project_dir)
    candidates = sorted(root.glob("*.qgs"))
    layers, nodes = [], []
    if candidates:
        document = ET.parse(candidates[0])
        for layer in document.findall("./projectlayers/maplayer"):
            source = layer.findtext("datasource", "")
            if "occurrence_probability_multiband" not in source:
                continue
            with rasterio.open(root / source) as raster:
                layers.append(
                    {
                        "id": layer.findtext("id"),
                        "datasource": source,
                        "valid": raster.count > 0 and raster.crs is not None,
                    }
                )
            if document.find(f".//layer-tree-layer[@id='{layer.findtext('id')}']") is not None:
                nodes.append({"layer_id": layer.findtext("id")})
    return {"ok": True, "probability_layers": layers, "probability_layer_tree_nodes": nodes}
