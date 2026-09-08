"""Single multiband occurrence-probability GeoTIFF support.

Runtime operations use standalone_gis (Rasterio), without QGIS or OSGeo imports.
Legacy GDAL helpers remain available to development regression tests only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import struct
import tempfile
import unicodedata
from pathlib import Path

SPECIES_FILENAME_RE = re.compile(r"^bce_inverse_corrected_probability_(.+)\.tif$")
STACK_RELPATH = "reference/rasters/occurrence_probability_multiband.tif"
INDEX_RELPATH = "reference/rasters/occurrence_probability_bands.json"
LAYER_NAME = "occurrence_probability_multiband.tif"
NODATA_VALUE = -9999.0
CACHE_STACK_FILENAME = "occurrence_probability_multiband.tif"
CACHE_INDEX_FILENAME = "occurrence_probability_bands.json"


def _inventory(
    source_dir: str, korean_names: list[str] | None = None,
) -> tuple[list[tuple[str, Path]], list[str], dict | None]:
    root = Path(source_dir)
    if not root.is_dir():
        return (
            [],
            [],
            {
                "error_code": "source_directory_missing",
                "message": f"확률 래스터 원본 폴더가 없습니다: {root}",
            },
        )

    species_by_name: dict[str, Path] = {}
    excluded: list[str] = []
    try:
        entries = sorted(root.rglob("*") if korean_names is not None else root.iterdir())
    except OSError as exc:
        return (
            [],
            [],
            {
                "error_code": "source_unreadable",
                "message": f"확률 래스터 원본 폴더를 읽을 수 없습니다: {root} ({exc})",
            },
        )
    names = {unicodedata.normalize("NFC", name).strip() for name in (korean_names or [])}
    names.discard("")
    for path in entries:
        if not path.is_file():
            excluded.append(path.name)
            continue
        filename = unicodedata.normalize("NFC", path.stem)
        if korean_names is not None:
            if path.suffix.lower() not in {".tif", ".tiff"}:
                excluded.append(path.relative_to(root).as_posix())
                continue
            matches = {name for name in names if name in filename}
            # Prefer 소나무 over 나무; unrelated names in one filename are ambiguous.
            matches = {name for name in matches if not any(name != other and name in other for other in matches)}
            if not matches:
                excluded.append(path.relative_to(root).as_posix())
                continue
            if len(matches) > 1:
                return [], excluded, {
                    "error_code": "species_name_ambiguous",
                    "message": f"파일명에 여러 국명이 포함되어 종을 결정할 수 없습니다: {path.name} ({', '.join(sorted(matches))})",
                }
            korean_name = matches.pop()
        else:
            # Legacy cache/development callers have no workbook; retain their old contract.
            match = SPECIES_FILENAME_RE.fullmatch(path.name)
            if match is None:
                excluded.append(path.name)
                continue
            korean_name = unicodedata.normalize("NFC", match.group(1)).strip()
        if not korean_name:
            return (
                [],
                excluded,
                {
                    "error_code": "species_name_empty",
                    "message": f"국명이 비어 있는 확률 래스터 파일입니다: {path.name}",
                },
            )
        if korean_name in species_by_name:
            return (
                [],
                excluded,
                {
                    "error_code": "species_name_collision",
                    "message": (
                        "Unicode NFC 정규화 후 같은 국명이 중복됩니다: "
                        f"{species_by_name[korean_name].name}, {path.name}"
                    ),
                },
            )
        try:
            if path.stat().st_size <= 0:
                raise OSError("empty file")
            with path.open("rb") as stream:
                header = stream.read(4)
        except OSError as exc:
            return (
                [],
                excluded,
                {
                    "error_code": "source_unreadable",
                    "message": f"확률 래스터 파일을 읽을 수 없습니다: {path.name} ({exc})",
                },
            )
        if header not in (b"II*\x00", b"MM\x00*"):
            return (
                [],
                excluded,
                {
                    "error_code": "source_invalid_raster",
                    "message": f"유효한 TIFF 파일이 아닙니다: {path.name}",
                },
            )
        species_by_name[korean_name] = path

    species = sorted(species_by_name.items(), key=lambda item: item[0])
    if not species:
        return (
            species,
            excluded,
            {
                "error_code": "species_inventory_empty",
                "message": "국명을 확인할 수 있는 종별 확률 TIFF가 없습니다. 파일명에 참조 자료의 국명을 포함해 주세요.",
            },
        )
    return species, excluded, None


def _source_inventory_signature(species: list[tuple[str, Path]]) -> str:
    """Return the lightweight identity used to reject a stale packaged stack cache.

    The release bundle is immutable, so names and byte sizes are sufficient to distinguish its
    raster inventory without re-reading every TIFF while a user waits for a project to be made.
    A cache is only trusted when this identity and the complete band mapping both match.
    """
    inventory = [
        {"name": name, "filename": path.name, "size": path.stat().st_size}
        for name, path in species
    ]
    payload = json.dumps(inventory, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _index_payload(species: list[tuple[str, Path]]) -> dict:
    return {
        "stack_path": STACK_RELPATH,
        "band_count": len(species),
        "mapping": {name: index for index, (name, _path) in enumerate(species, start=1)},
        "source_inventory_signature": _source_inventory_signature(species),
    }


def _cached_stack_matches(
    cache_dir: Path, species: list[tuple[str, Path]]
) -> tuple[Path, Path] | None:
    """Return a verified packaged cache pair, or ``None`` when it must be rebuilt."""
    stack = cache_dir / CACHE_STACK_FILENAME
    index = cache_dir / CACHE_INDEX_FILENAME
    try:
        if stack.stat().st_size <= 4:
            return None
        with stack.open("rb") as stream:
            if stream.read(4) not in (b"II*\x00", b"MM\x00*"):
                return None
        payload = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    expected = _index_payload(species)
    if (
        payload.get("stack_path") != expected["stack_path"]
        or payload.get("band_count") != expected["band_count"]
        or payload.get("mapping") != expected["mapping"]
        or payload.get("source_inventory_signature") != expected["source_inventory_signature"]
    ):
        return None
    return stack, index


def validate_probability_stack_cache(cache_dir: str | Path) -> dict:
    """Validate a self-contained packaged stack/index without the source TIFFs."""
    import rasterio

    from .reference_bundle import _sha256_file

    cache = Path(cache_dir)
    stack = cache / CACHE_STACK_FILENAME
    try:
        payload = json.loads((cache / CACHE_INDEX_FILENAME).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("밴드 인덱스 형식이 올바르지 않습니다.")
        mapping = payload.get("mapping")
        count = payload.get("band_count")
        if (
            payload.get("stack_path") != STACK_RELPATH
            or type(count) is not int
            or count < 1
            or not isinstance(mapping, dict)
            or len(mapping) != count
            or any(not name.strip() or type(band) is not int for name, band in mapping.items())
            or set(mapping.values()) != set(range(1, count + 1))
        ):
            raise ValueError("종별 밴드 매핑이 올바르지 않습니다.")
        if payload.get("stack_sha256") != _sha256_file(stack):
            raise ValueError("다중밴드 TIFF 해시가 인덱스와 다릅니다.")
        with rasterio.open(stack) as dataset:
            if (
                dataset.count != count
                or not dataset.crs
                or dataset.transform.determinant == 0
                or any(value != NODATA_VALUE for value in dataset.nodatavals)
                or any(dataset.descriptions[band - 1] != name for name, band in mapping.items())
            ):
                raise ValueError("다중밴드 TIFF의 밴드/CRS/NoData가 올바르지 않습니다.")
        return payload
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        raise ValueError(
            f"출현확률 다중밴드 캐시를 사용할 수 없습니다: {exc} 앱을 다시 설치해 주세요."
        ) from exc


def _publish_stack(project: Path, staging_stack: Path, staging_index: Path) -> tuple[Path, Path]:
    """Atomically replace the project's stack/index pair, restoring an older pair on failure."""
    final_stack = project / STACK_RELPATH
    final_index = project / INDEX_RELPATH
    final_stack.parent.mkdir(parents=True, exist_ok=True)
    backup_stack = final_stack.with_name(final_stack.name + ".previous")
    backup_index = final_index.with_name(final_index.name + ".previous")
    had_stack = final_stack.exists()
    had_index = final_index.exists()
    try:
        backup_stack.unlink(missing_ok=True)
        backup_index.unlink(missing_ok=True)
        if had_stack:
            os.replace(final_stack, backup_stack)
        if had_index:
            os.replace(final_index, backup_index)
        os.replace(staging_stack, final_stack)
        os.replace(staging_index, final_index)
    except BaseException:
        final_stack.unlink(missing_ok=True)
        final_index.unlink(missing_ok=True)
        if backup_stack.exists():
            os.replace(backup_stack, final_stack)
        if backup_index.exists():
            os.replace(backup_index, final_index)
        raise
    finally:
        backup_stack.unlink(missing_ok=True)
        backup_index.unlink(missing_ok=True)
    return final_stack, final_index


def _stage_cached_stack(cache_stack: Path, cache_index: Path, staging: Path) -> tuple[Path, Path]:
    """Stage the immutable cache without mutating it; hard links avoid a second full copy."""
    staging_stack = staging / CACHE_STACK_FILENAME
    staging_index = staging / CACHE_INDEX_FILENAME
    try:
        os.link(cache_stack, staging_stack)
    except OSError:
        shutil.copy2(cache_stack, staging_stack)
    shutil.copy2(cache_index, staging_index)
    return staging_stack, staging_index


def _dispatch_gdal(func: str, kwargs: dict) -> dict:
    from . import standalone_gis

    try:
        return getattr(standalone_gis, func)(**kwargs)
    except Exception as exc:
        return {"ok": False, "error_code": "raster_operation_failed", "message": str(exc)}


def validate_probability_raster_sources(source_dir: str, *, korean_names: list[str] | None = None) -> dict:
    species, excluded, error = _inventory(source_dir, korean_names)
    if error is not None:
        return {
            "ok": False,
            "discovered_species_count": len(species),
            "excluded_files": excluded,
            **error,
        }
    result = _dispatch_gdal(
        "_validate_sources_gdal",
        {"sources": [{"name": name, "path": str(path)} for name, path in species]},
    )
    return {
        "ok": bool(result.get("ok")),
        "discovered_species_count": len(species),
        "error_code": result.get("error_code"),
        "message": result.get("message", ""),
        "excluded_files": excluded,
    }


def _open_source_metadata(
    gdal, item: dict, baseline: dict | None
) -> tuple[dict | None, dict | None]:
    dataset = gdal.Open(item["path"], gdal.GA_ReadOnly)
    if dataset is None:
        return None, {
            "error_code": "source_invalid_raster",
            "message": f"래스터를 열 수 없습니다: {Path(item['path']).name}",
        }
    band = dataset.GetRasterBand(1) if dataset.RasterCount == 1 else None
    if band is None:
        return None, {
            "error_code": "source_not_single_band",
            "message": f"단일 밴드 래스터가 아닙니다: {Path(item['path']).name}",
        }
    metadata = {
        "width": dataset.RasterXSize,
        "height": dataset.RasterYSize,
        "geotransform": tuple(dataset.GetGeoTransform()),
        "projection": dataset.GetProjectionRef() or "",
        "data_type": band.DataType,
        "nodata": band.GetNoDataValue(),
    }
    if metadata["nodata"] != NODATA_VALUE and not (
        metadata["nodata"] is not None and math.isnan(metadata["nodata"])
    ):
        return None, {
            "error_code": "source_nodata_incompatible",
            "message": f"NoData 값은 -9999 또는 NaN이어야 합니다: {Path(item['path']).name}",
        }
    metadata["nodata"] = NODATA_VALUE  # Output uses one portable sentinel for all bands.
    if baseline is not None and metadata != baseline:
        return None, {
            "error_code": "source_geometry_incompatible",
            "message": f"공통 격자/CRS/자료형과 호환되지 않습니다: {Path(item['path']).name}",
        }
    return metadata, None


def _validate_sources_gdal(sources: list[dict]) -> dict:
    from osgeo import gdal

    gdal.UseExceptions()
    baseline = None
    for item in sources:
        metadata, error = _open_source_metadata(gdal, item, baseline)
        if error is not None:
            return {"ok": False, **error}
        if baseline is None:
            baseline = metadata
    return {"ok": True, "error_code": None, "message": "확률 래스터 원본이 유효합니다."}


def build_probability_stack(
    source_dir: str, project_dir: str, *, cache_dir: str | None = None,
    korean_names: list[str] | None = None,
) -> dict:
    cached = None
    if cache_dir and not Path(source_dir).exists():
        # Packaged apps contain only the immutable stack and band index.
        try:
            payload = validate_probability_stack_cache(cache_dir)
        except ValueError as exc:
            return {
                "success": False,
                "error_code": "probability_cache_invalid",
                "error_message": str(exc),
            }
        species, excluded, error = [], [], None
        species_count = payload["band_count"]
        cached = (Path(cache_dir) / CACHE_STACK_FILENAME, Path(cache_dir) / CACHE_INDEX_FILENAME)
    else:
        species, excluded, error = _inventory(source_dir, korean_names)
        species_count = len(species)
    if error is not None:
        return {
            "success": False,
            "discovered_species_count": len(species),
            "error_code": error["error_code"],
            "error_message": error["message"],
            "excluded_files": excluded,
        }

    project = Path(project_dir)
    project.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".qpb-probability-", dir=project.parent))
    try:
        if cache_dir and cached is None:
            cached = _cached_stack_matches(Path(cache_dir), species)
        if cached is not None:
            staging_stack, staging_index = _stage_cached_stack(*cached, staging)
            final_stack, final_index = _publish_stack(project, staging_stack, staging_index)
            return {
                "success": True,
                "error_code": None,
                "error_message": None,
                "stack_path": str(final_stack),
                "index_path": str(final_index),
                "discovered_species_count": species_count,
                "excluded_files": excluded,
                "cache_reused": True,
            }

        staging_stack = staging / CACHE_STACK_FILENAME
        result = _dispatch_gdal(
            "_build_probability_stack_gdal",
            {
                "sources": [{"name": name, "path": str(path)} for name, path in species],
                "output_path": str(staging_stack),
            },
        )
        if not result.get("ok"):
            return {
                "success": False,
                "error_code": result.get("error_code") or "stack_build_failed",
                "error_message": result.get("message") or "다중밴드 확률 래스터 생성 실패",
                "excluded_files": excluded,
            }

        index_payload = _index_payload(species)
        staging_index = staging / CACHE_INDEX_FILENAME
        staging_index.write_text(
            json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        final_stack, final_index = _publish_stack(project, staging_stack, staging_index)
        return {
            "success": True,
            "error_code": None,
            "error_message": None,
            "stack_path": str(final_stack),
            "index_path": str(final_index),
            "discovered_species_count": len(species),
            "excluded_files": excluded,
            "cache_reused": False,
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def prepare_probability_stack_cache(source_dir: str, cache_dir: str) -> dict:
    """Create the immutable, package-time cache that makes project generation fast."""
    from .reference_bundle import _sha256_file

    cache = Path(cache_dir)
    cache.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=".qpb-probability-cache-", dir=cache.parent))
    staging = cache.parent / f".{cache.name}.tmp"
    try:
        result = build_probability_stack(source_dir, str(scratch / "project"))
        if not result.get("success"):
            return result
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        os.replace(Path(result["stack_path"]), staging / CACHE_STACK_FILENAME)
        os.replace(Path(result["index_path"]), staging / CACHE_INDEX_FILENAME)
        index_path = staging / CACHE_INDEX_FILENAME
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        payload["stack_sha256"] = _sha256_file(staging / CACHE_STACK_FILENAME)
        index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        validate_probability_stack_cache(staging)
        shutil.rmtree(cache, ignore_errors=True)
        os.replace(staging, cache)
        return {
            **result,
            "cache_dir": str(cache),
            "stack_path": str(cache / CACHE_STACK_FILENAME),
            "index_path": str(cache / CACHE_INDEX_FILENAME),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)


def _build_probability_stack_gdal(sources: list[dict], output_path: str) -> dict:
    import numpy as np
    from osgeo import gdal

    gdal.UseExceptions()
    baseline = None
    for item in sources:
        metadata, error = _open_source_metadata(gdal, item, baseline)
        if error is not None:
            return {"ok": False, **error}
        if baseline is None:
            baseline = metadata
    if baseline is None:
        return {"ok": False, "error_code": "source_empty", "message": "원본이 없습니다."}

    driver = gdal.GetDriverByName("GTiff")
    output = driver.Create(
        output_path,
        baseline["width"],
        baseline["height"],
        len(sources),
        baseline["data_type"],
        options=["COMPRESS=LZW", "PREDICTOR=3", "INTERLEAVE=BAND", "BIGTIFF=IF_SAFER"],
    )
    if output is None:
        return {"ok": False, "error_code": "stack_create_failed", "message": "GeoTIFF 생성 실패"}
    output.SetGeoTransform(baseline["geotransform"])
    output.SetProjection(baseline["projection"])
    try:
        for band_number, item in enumerate(sources, start=1):
            source = gdal.Open(item["path"], gdal.GA_ReadOnly)
            source_band = source.GetRasterBand(1)
            target_band = output.GetRasterBand(band_number)
            pixels = source_band.ReadAsArray()
            pixels[np.isnan(pixels)] = NODATA_VALUE
            target_band.WriteArray(pixels)
            target_band.SetNoDataValue(NODATA_VALUE)
            target_band.SetDescription(item["name"])
            target_band.SetMetadataItem("QPB_SOURCE_BASENAME", Path(item["path"]).name)
            source = None
        output.FlushCache()
    finally:
        output = None
    check = gdal.Open(output_path, gdal.GA_ReadOnly)
    if check is None or check.RasterCount != len(sources):
        return {
            "ok": False,
            "error_code": "stack_validation_failed",
            "message": "생성 결과 검증 실패",
        }
    check = None
    return {"ok": True}


def inspect_probability_stack(stack_path: str, source_dir: str, *, korean_names: list[str] | None = None) -> dict:
    species, _excluded, error = _inventory(source_dir, korean_names)
    if error is not None:
        return {"valid": False, "error_code": error["error_code"]}
    result = _dispatch_gdal(
        "_inspect_probability_stack_gdal",
        {
            "stack_path": stack_path,
            "sources": [{"name": name, "path": str(path)} for name, path in species],
        },
    )
    if not result.get("ok"):
        return {
            "valid": False,
            "band_count": 0,
            "source_files_represented_once": False,
            "pixel_crosscheck": {"values_match": False, "nodata_match": False},
            "metadata": {"nodata": None},
        }
    return result["report"]


def _inspect_probability_stack_gdal(stack_path: str, sources: list[dict]) -> dict:
    import numpy as np
    from osgeo import gdal

    gdal.UseExceptions()
    stack = gdal.Open(stack_path, gdal.GA_ReadOnly)
    if stack is None:
        return {"ok": False, "message": "스택을 열 수 없습니다."}
    represented = True
    values_match = True
    nodata_match = True
    for band_number, item in enumerate(sources, start=1):
        source = gdal.Open(item["path"], gdal.GA_ReadOnly)
        source_band = source.GetRasterBand(1)
        stack_band = stack.GetRasterBand(band_number)
        if stack_band is None:
            represented = values_match = nodata_match = False
            break
        represented = represented and stack_band.GetDescription() == item["name"]
        represented = represented and (
            stack_band.GetMetadataItem("QPB_SOURCE_BASENAME") == Path(item["path"]).name
        )
        source_nodata = source_band.GetNoDataValue()
        nodata_match = nodata_match and stack_band.GetNoDataValue() == NODATA_VALUE and (
            source_nodata == NODATA_VALUE or (source_nodata is not None and math.isnan(source_nodata))
        )
        expected = source_band.ReadAsArray()
        expected[np.isnan(expected)] = NODATA_VALUE
        values_match = values_match and np.array_equal(expected, stack_band.ReadAsArray())
        source = None
    first_nodata = stack.GetRasterBand(1).GetNoDataValue() if stack.RasterCount else None
    report = {
        "valid": bool(
            stack.RasterCount == len(sources) and represented and values_match and nodata_match
        ),
        "band_count": stack.RasterCount,
        "source_files_represented_once": represented,
        "pixel_crosscheck": {"values_match": values_match, "nodata_match": nodata_match},
        "metadata": {"nodata": first_nodata},
    }
    return {"ok": True, "report": report}


def sample_probability_candidate(project_dir: str, korean_name: str, location: dict) -> dict:
    project = Path(project_dir)
    try:
        index = json.loads((project / INDEX_RELPATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False, "value": None, "reason": "band_index_unavailable"}
    normalized = unicodedata.normalize("NFC", str(korean_name).strip())
    mapping = index.get("mapping")
    band = mapping.get(normalized) if isinstance(mapping, dict) else None
    if (
        not isinstance(band, int)
        or isinstance(band, bool)
        or not 1 <= band <= index.get("band_count", 0)
    ):
        return {"available": False, "value": None, "reason": "band_mapping_unavailable"}
    if index.get("stack_path") != STACK_RELPATH:
        return {"available": False, "value": None, "reason": "band_index_invalid"}
    try:
        lon = float(location["lon"])
        lat = float(location["lat"])
    except (KeyError, TypeError, ValueError):
        return {"available": False, "value": None, "reason": "raster_location_invalid"}
    if not math.isfinite(lon) or not math.isfinite(lat):
        return {"available": False, "value": None, "reason": "raster_location_invalid"}
    result = _dispatch_gdal(
        "_sample_probability_gdal",
        {"stack_path": str(project / STACK_RELPATH), "band": band, "lon": lon, "lat": lat},
    )
    if not result.get("ok"):
        return {
            "available": False,
            "value": None,
            "reason": result.get("reason", "raster_sampling_failed"),
        }
    return {"available": True, "value": result["value"]}


def _sample_probability_gdal(stack_path: str, band: int, lon: float, lat: float) -> dict:
    from osgeo import gdal

    gdal.UseExceptions()
    dataset = gdal.Open(stack_path, gdal.GA_ReadOnly)
    if dataset is None or band < 1 or band > dataset.RasterCount:
        return {"ok": False, "reason": "raster_layer_unavailable"}
    gt = dataset.GetGeoTransform()
    determinant = gt[1] * gt[5] - gt[2] * gt[4]
    if determinant == 0:
        return {"ok": False, "reason": "raster_crs_invalid"}
    pixel = math.floor((gt[5] * (lon - gt[0]) - gt[2] * (lat - gt[3])) / determinant)
    line = math.floor((-gt[4] * (lon - gt[0]) + gt[1] * (lat - gt[3])) / determinant)
    if pixel < 0 or line < 0 or pixel >= dataset.RasterXSize or line >= dataset.RasterYSize:
        return {"ok": False, "reason": "raster_missing_nodata_or_outside_extent"}
    raster_band = dataset.GetRasterBand(band)
    raw = raster_band.ReadRaster(pixel, line, 1, 1, buf_type=gdal.GDT_Float32)
    if raw is None or len(raw) != 4:
        return {"ok": False, "reason": "raster_sampling_failed"}
    value = float(struct.unpack("=f", raw)[0])
    if not math.isfinite(value) or value == NODATA_VALUE:
        return {"ok": False, "reason": "raster_missing_nodata_or_outside_extent"}
    if value > 1.0:
        return {"ok": False, "reason": "raster_invalid_value"}
    return {"ok": True, "value": max(0.0, value)}


def inspect_probability_project(project_dir: str) -> dict:
    project = Path(project_dir)
    reference_files = (
        [
            path.relative_to(project).as_posix()
            for path in sorted((project / "reference").rglob("*"))
            if path.is_file()
        ]
        if (project / "reference").is_dir()
        else []
    )
    try:
        index = json.loads((project / INDEX_RELPATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index = {}
    try:
        raw_manifest = json.loads((project / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw_manifest = {}
    result = _dispatch_gdal("_inspect_probability_project_pyqgis", {"project_dir": str(project)})
    layers = result.get("probability_layers", []) if result.get("ok") else []
    nodes = result.get("probability_layer_tree_nodes", []) if result.get("ok") else []
    serialized = json.dumps(index, ensure_ascii=False) + json.dumps(
        raw_manifest.get("probability_raster", {}), ensure_ascii=False
    )
    absolute_pattern = re.compile(r"(?:[A-Za-z]:[\\/]|/Users/|/private/|/tmp/)")
    leaks = absolute_pattern.findall(serialized)
    probability_manifest = raw_manifest.get("probability_raster") or {}
    return {
        "probability_layers": layers,
        "probability_layer_tree_nodes": nodes,
        "reference_files": reference_files,
        "band_index_mapping": index.get("mapping", {}),
        "manifest": probability_manifest,
        "absolute_path_leaks": leaks,
    }


def _inspect_probability_project_pyqgis(project_dir: str) -> dict:
    try:
        from qgis.core import QgsProject, QgsRasterLayer
    except ImportError:
        return {"ok": False, "probability_layers": [], "probability_layer_tree_nodes": []}

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()
    candidates = sorted(Path(project_dir).glob("*.qgs"))
    if not candidates:
        return {"ok": True, "probability_layers": [], "probability_layer_tree_nodes": []}
    project = QgsProject()
    project.read(str(candidates[0]))
    layers = []
    nodes = []
    for layer in project.mapLayers().values():
        if not isinstance(layer, QgsRasterLayer):
            continue
        if not (
            bool(layer.customProperty("fieldbuildkit/probability_raster", False))
            or "occurrence_probability_multiband" in layer.source()
        ):
            continue
        layers.append(
            {"valid": bool(layer.isValid()), "datasource": layer.source(), "id": layer.id()}
        )
        node = project.layerTreeRoot().findLayer(layer.id())
        if node is not None:
            nodes.append({"layer_id": layer.id()})
    return {"ok": True, "probability_layers": layers, "probability_layer_tree_nodes": nodes}
