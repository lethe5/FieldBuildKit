"""Real builds with every QGIS/OSGeo import and bridge call forbidden."""

from __future__ import annotations

import builtins
import json
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fiona
import numpy as np
import pytest
import rasterio
from openpyxl import Workbook
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from qfield_builder import (
    build,
    canonical_reference,
    probability_raster,
    qgis_bridge,
    reference_bundle,
    runtime,
    schemas,
    validate,
)
from qfield_builder.standalone_gis import reproject_uploaded_gpkg_layer

RASTERS = reference_bundle.RASTER_DIR_RELATIVE_SUBPATH
POLYGON = "MULTIPOLYGON(((127 37,127.01 37,127.01 37.01,127 37.01,127 37)))"


@pytest.fixture(autouse=True)
def no_qgis(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"qgis", "osgeo"}:
            raise AssertionError(f"Forbidden runtime import: {name}")
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("QGIS bridge must never be called")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(qgis_bridge, "run_job", forbidden)
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", forbidden)


@pytest.fixture
def reference(tmp_path):
    root = tmp_path / "reference"
    rasters = root / RASTERS
    rasters.mkdir(parents=True)
    for name, value in (("소나무", 0.25), ("참나무", 0.75)):
        with rasterio.open(
            rasters / f"bce_inverse_corrected_probability_{name}.tif",
            "w",
            driver="GTiff",
            height=4,
            width=4,
            count=1,
            dtype="float32",
            nodata=-9999,
            crs="EPSG:4326",
            transform=from_origin(127, 37.04, 0.01, 0.01),
        ) as dataset:
            pixels = np.full((4, 4), value, dtype="float32")
            pixels[0, 0] = -9999
            dataset.write(pixels, 1)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data Sheet"
    sheet.append(list(canonical_reference.SOURCE_COLUMNS))
    sheet.append([None] * len(canonical_reference.SOURCE_COLUMNS))
    row = {
        "No": 1,
        "관리분류군": "관속식물류",
        "정이명여부": "정명",
        "학명": "Pinus densiflora Siebold & Zucc.",
        "대표국명": "소나무",
        "URL": canonical_reference.CANONICAL_URL_PREFIX + "000000000001",
    }
    sheet.append([row.get(name) for name in canonical_reference.SOURCE_COLUMNS])
    workbook.save(root / "canonical.xlsx")
    return root


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
@pytest.mark.parametrize("mode", ["none", "online", "offline"])
@pytest.mark.parametrize("identification", [False, True])
def test_build_and_relocate_without_qgis(
    tmp_path, monkeypatch, reference, survey_type, mode, identification
):
    raster_sources = reference / RASTERS
    with MemoryFile() as image:
        with image.open(driver="PNG", width=256, height=256, count=3, dtype="uint8") as raster:
            raster.write(np.full((3, 256, 256), 255, dtype="uint8"))
        tile = image.read()
    monkeypatch.setattr(build, "resolve_tile_fetcher", lambda cfg: lambda z, x, y: tile)
    config = {
        "project_display_name": "Standalone 한글 & test",
        "survey_type": survey_type,
        "canonical_reference_path": str(reference / "canonical.xlsx"),
        "_test_reference_data_dir": str(reference),
        "identification_enabled": identification,
        "probability_raster_source_dir": str(raster_sources) if identification else None,
        "plantnet": {"consent_accepted": True, "api_key": "plant<&\"'key"},
        "basemap": {
            "mode": mode,
            "layer": "Base",
            "consent_accepted": True,
            "vworld_api_key": "test-vworld-key",
            "min_zoom": 10,
            "max_zoom": 10,
            "bbox": {"min_lon": 127, "max_lon": 127.01, "min_lat": 37, "max_lat": 37.01},
        },
    }
    if survey_type != "simple_inventory":
        config["sites"] = [{"site_name": "테스트", "geom_wkt": POLYGON}]
    destination = tmp_path / "output"
    result = build.build_project(config, str(destination))
    assert result["success"], json.dumps(result, ensure_ascii=False, indent=2)
    document = ET.parse(result["qgs_path"])
    assert document.find("transaction").get("mode") == "BufferedGroups"
    reference_ids = {
        node.get("id")
        for node in document.findall(
            "./layer-tree-group/layer-tree-group[@name='Reference']//layer-tree-layer"
        )
    }
    # UUID generation must remain active without displaying primary keys in the form.
    for layer in document.findall("./projectlayers/maplayer"):
        table_name = layer.findtext("datasource", "").split("|layername=")[-1]
        containers = layer.findall("./attributeEditorForm/attributeEditorContainer")
        names = [container.get("name") for container in containers]
        assert not {"Details", "Related records"} & set(names)
        if containers and layer.findtext("layername") != "식물관찰":
            expected_names = ["상세 정보"]
            if layer.find(".//attributeEditorRelation") is not None:
                expected_names.append("관련 기록")
            assert names == expected_names
        is_reference = layer.findtext("id") in reference_ids
        is_photo = table_name in schemas.photo_tables_for(survey_type)
        assert layer.findtext("flags/Searchable") == (
            "0" if is_reference or is_photo else "1"
        ), table_name
        if is_reference or is_photo:
            # Only search participation changes, not visibility, access or identification.
            assert layer.findtext("flags/Identifiable") == ("0" if is_reference else "1")
            assert layer.findtext("flags/Removable") == "1"
            assert layer.findtext("flags/Private") == "0"
        table = schemas.get_schema(survey_type).get(table_name)
        if table is None:
            continue
        field = table.uuid_pk
        widget = layer.find(f"./fieldConfiguration/field[@name='{field}']/editWidget")
        assert widget.get("type") == "UuidGenerator", (table_name, field)
        default = layer.find(f"./defaults/default[@field='{field}']")
        assert default.get("expression") == "uuid('WithoutBraces')"
        assert default.get("applyOnUpdate") == "0"
        assert layer.findtext("editorlayout") == "tablayout"
        assert layer.find(f".//attributeEditorField[@name='{field}']") is None
        if table.foreign_key:
            foreign_key = table.foreign_key.column
            widget = layer.find(
                f"./fieldConfiguration/field[@name='{foreign_key}']/editWidget"
            )
            assert widget.get("type") == "RelationReference"
            assert layer.find(f".//attributeEditorField[@name='{foreign_key}']") is not None
    observation_layers = document.findall("./projectlayers/maplayer[layername='식물관찰']")
    assert len(observation_layers) == (0 if survey_type == "vegetation_mapping" else 1)
    for layer in observation_layers:
        tabs = layer.findall("./attributeEditorForm/attributeEditorContainer")
        assert [tab.get("name") for tab in tabs] == ["관찰 정보", "식별 정보"]
        assert all(tab.get("type") == "Tab" and tab.get("groupBox") == "0" for tab in tabs)
        observation_items = [item for item in tabs[0] if item.tag != "labelStyle"]
        observation_names = [item.get("name") for item in observation_items]
        fruit_index = observation_names.index("fruit_photo_path")
        assert observation_names[fruit_index + 1] == "notes"
        assert observation_names[fruit_index + 2:] == (
            ["Identify attached photos"] if identification else []
        )
        assert [
            item.get("name") for item in tabs[1] if item.tag != "labelStyle"
        ] == [
            "identification_score",
            "occurrence_probability",
            "identification_timestamp",
            "identification_model_version",
            "identification_status",
        ]
        assert [
            name for name in observation_names if name.endswith("_photo_path")
        ] == ["leaf_photo_path", "flower_photo_path", "fruit_photo_path"]
        # A moved field must not also remain in its previous tab.
        all_fields = layer.findall("./attributeEditorForm//attributeEditorField")
        names = [item.get("name") for item in all_fields]
        assert len(names) == len(set(names))
    widget = document.find(".//attributeEditorQmlElement")
    assert (widget is not None) == identification
    if identification:
        assert "".join(widget.itertext()).count("import QtQuick 2.15") == 1
        assert probability_raster.inspect_probability_stack(
            str(destination / probability_raster.STACK_RELPATH), str(raster_sources)
        )["valid"]
        assert len(list((destination / "reference").rglob("*.tif"))) == 1
        with rasterio.open(destination / probability_raster.STACK_RELPATH) as stack:
            assert stack.compression == rasterio.enums.Compression.deflate
        sample = probability_raster.sample_probability_candidate(
            str(destination), "소나무", {"lon": 127.015, "lat": 37.025}
        )
        assert sample["value"] == pytest.approx(0.25), sample
    if mode == "offline":
        assert "test-vworld-key" not in Path(result["qgs_path"]).read_text()
        with rasterio.open(destination / "basemap/offline.mbtiles") as raster:
            assert raster.crs.to_epsg() == 3857
            assert raster.read().size > 0
        # Empty surveys should still open at offline coverage, not the Korea fallback.
        if survey_type == "simple_inventory":
            from rasterio.warp import transform

            x, y = transform("EPSG:4326", "EPSG:5186", [127.005], [37.005])
            extent = document.find("mapcanvas/extent")
            west, south, east, north = [
                float(extent.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")
            ]
            assert west < x[0] < east and south < y[0] < north
            assert east - west < 50_000 and north - south < 50_000
    if identification:
        values = document.findall("./properties/Variables/variableValues/value")
        assert "plant<&\"'key" in [value.text for value in values]
    moved = tmp_path / "moved folder 한글"
    shutil.move(str(destination), moved)
    report = validate.validate_project(str(moved))
    assert report["success"], report
    assert report["qgis_open_checked"] is False
    assert report["opens_without_repair_warning"] is None
    # A broken relation or missing source must not pass structural validation.
    gpkg = next((moved / "data").glob("*.gpkg"))
    gpkg.rename(gpkg.with_suffix(".missing"))
    assert not validate.validate_project(str(moved))["success"]
    gpkg.with_suffix(".missing").rename(gpkg)


@pytest.mark.parametrize("damage", ["missing_stack", "missing_index", "json", "mapping", "pixels"])
def test_cache_only_rejects_damaged_assets(tmp_path, reference, damage):
    cache = reference / "probability_cache"
    result = probability_raster.prepare_probability_stack_cache(
        str(reference / RASTERS), str(cache)
    )
    assert result["success"], result
    shutil.move(str(reference / "rasters"), str(tmp_path / "source-rasters"))
    stack, index = cache / probability_raster.CACHE_STACK_FILENAME, cache / (
        probability_raster.CACHE_INDEX_FILENAME
    )
    if damage == "missing_stack":
        stack.unlink()
    elif damage == "missing_index":
        index.unlink()
    elif damage == "json":
        index.write_text("[]")
    elif damage == "mapping":
        payload = json.loads(index.read_text())
        payload["mapping"]["소나무"] = 99
        index.write_text(json.dumps(payload))
    else:
        with rasterio.open(stack, "r+") as dataset:
            dataset.write(np.zeros((4, 4), dtype="float32"), 1)
    with pytest.raises(reference_bundle.ReferenceDataInvalidError):
        reference_bundle.validate_probability_reference(reference)
    output = tmp_path / "output"
    result = probability_raster.build_probability_stack(
        str(reference / RASTERS), str(output), cache_dir=str(cache)
    )
    assert not result["success"]
    assert result["error_code"] == "probability_cache_invalid"
    assert not output.exists()


def test_cache_only_rejects_stale_manifest(tmp_path, reference):
    packaged = tmp_path / "packaged"
    reference_bundle.prepare_filtered_reference_bundle(
        reference / "canonical.xlsx", packaged, raster_dir=reference / RASTERS
    )
    assert probability_raster.prepare_probability_stack_cache(
        str(reference / RASTERS), str(packaged / "probability_cache")
    )["success"]
    shutil.move(str(packaged / "rasters"), str(tmp_path / "source-rasters"))
    manifest = packaged / reference_bundle.FILTERED_MANIFEST_NAME
    payload = json.loads(manifest.read_text())
    next(iter(payload["raster_files"].values()))["size"] += 1
    manifest.write_text(json.dumps(payload))
    with pytest.raises(reference_bundle.ReferenceDataInvalidError, match="inventory"):
        reference_bundle.validate_filtered_reference_data(packaged)


@pytest.mark.parametrize("update", ["pixels", "add", "remove"])
def test_release_preparation_rebuilds_cache_from_updated_sources(tmp_path, reference, update):
    """Old hashes never constrain valid updates to the current TIFF input set."""
    root = Path(__file__).resolve().parents[2]
    destination = tmp_path / "prepared"
    command = [
        sys.executable, str(root / "packaging/prepare_reference_bundle.py"),
        "--canonical-workbook", str(reference / "canonical.xlsx"),
        "--raster-dir", str(reference / RASTERS), "--destination", str(destination),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    cache = destination / "probability_cache"
    before = probability_raster.validate_probability_stack_cache(cache)
    pine = reference / RASTERS / "bce_inverse_corrected_probability_소나무.tif"
    if update == "pixels":
        with rasterio.open(pine, "r+") as raster:
            pixels = raster.read(1)
            pixels[1, 1] = 0.5
            raster.write(pixels, 1)
    elif update == "add":
        shutil.copyfile(pine, pine.with_name("bce_inverse_corrected_probability_새종.tif"))
    else:
        (reference / RASTERS / "bce_inverse_corrected_probability_참나무.tif").unlink()
    source_hashes = {
        path.name: reference_bundle._sha256_file(path)
        for path in (reference / RASTERS).glob("*.tif")
    }
    subprocess.run(command, check=True, capture_output=True, text=True)
    after = probability_raster.validate_probability_stack_cache(cache)
    assert before["stack_sha256"] != after["stack_sha256"]
    assert after["band_count"] == {"pixels": 2, "add": 3, "remove": 1}[update]
    assert probability_raster.inspect_probability_stack(
        str(cache / probability_raster.CACHE_STACK_FILENAME), str(reference / RASTERS)
    )["valid"]
    manifest = json.loads((destination / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert {name: entry["sha256"] for name, entry in manifest["raster_files"].items()} == (
        source_hashes
    )
    assert {
        path.name: reference_bundle._sha256_file(path)
        for path in (reference / RASTERS).glob("*.tif")
    } == source_hashes


@pytest.mark.parametrize("damage", ["missing_hash", "wrong_hash"])
def test_spec_ignores_legacy_cache_even_with_original_rasters(
    tmp_path, reference, monkeypatch, damage
):
    root = Path(__file__).resolve().parents[2]
    destination = tmp_path / "prepared"
    reference_bundle.prepare_filtered_reference_bundle(
        str(reference / "canonical.xlsx"), str(destination), raster_dir=reference / RASTERS
    )
    cache = destination / "probability_cache"
    assert probability_raster.prepare_probability_stack_cache(
        str(reference / RASTERS), str(cache)
    )["success"]
    index = cache / probability_raster.CACHE_INDEX_FILENAME
    payload = json.loads(index.read_text(encoding="utf-8"))
    if damage == "missing_hash":
        del payload["stack_sha256"]
    else:
        payload["stack_sha256"] = "0" * 64
    index.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("QPB_FILTERED_REFERENCE_ROOT", str(destination))
    spec = root / "packaging/qfield_builder.spec"
    prefix = spec.read_text(encoding="utf-8").split("gis_datas, gis_binaries, gis_imports =")[0]
    scope = {"SPECPATH": str(root / "packaging")}
    exec(compile(prefix, str(spec), "exec"), scope)
    assert "FILTERED_REFERENCE_ROOT" not in scope


def test_runtime_does_not_discover_qgis():
    assert runtime.check_runtime()["available"]
    assert runtime.check_runtime()["backend"] == "standalone"


def test_probability_pixels_nodata_and_mismatched_grid(tmp_path, reference):
    result = probability_raster.build_probability_stack(str(reference / RASTERS), str(tmp_path))
    assert result["success"], result
    sample = probability_raster.sample_probability_candidate(
        str(tmp_path), "소나무", {"lon": 127.015, "lat": 37.025}
    )
    assert sample["value"] == pytest.approx(0.25), sample
    source = reference / RASTERS / "bce_inverse_corrected_probability_참나무.tif"
    with rasterio.open(source, "r+") as dataset:
        dataset.transform = from_origin(128, 37.04, 0.01, 0.01)
    assert not probability_raster.validate_probability_raster_sources(str(reference / RASTERS))[
        "ok"
    ]


def test_projected_upload_preserves_geometry_and_attributes(tmp_path):
    source, output = tmp_path / "source.gpkg", tmp_path / "output.gpkg"
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                (200000, 500000),
                (200100, 500000),
                (200100, 500100),
                (200000, 500100),
                (200000, 500000),
            ]
        ],
    }
    with fiona.open(
        source,
        "w",
        driver="GPKG",
        layer="sites",
        crs="EPSG:5186",
        schema={"geometry": "Polygon", "properties": {"name": "str"}},
    ) as data:
        data.write({"geometry": geometry, "properties": {"name": "한글 사이트"}})
    reproject_uploaded_gpkg_layer(str(source), "sites", str(output), "EPSG:4326")
    with fiona.open(output) as data:
        feature = next(iter(data))
        lon, lat = feature.geometry.coordinates[0][0][0]
        assert lon == pytest.approx(127, abs=0.001)
        assert 36 < lat < 38
        assert feature.properties["name"] == "한글 사이트"


def test_templates_have_no_workstation_data_or_embedded_widget_code():
    from qfield_builder.template_project import TEMPLATES

    for path in TEMPLATES.glob("*.qgs"):
        text = path.read_text()
        assert "saveUser=" not in text and "/Users/" not in text
        assert "import QtQuick" not in text


def test_optional_lookup_svg_crs_and_declined_keys(tmp_path):
    from qfield_builder import gpkg, template_project

    data, project = tmp_path / "data.gpkg", tmp_path / "project.qgs"
    gpkg.build_geopackage(str(data), "simple_inventory", "test")
    icon = tmp_path / "symbols" / "test.svg"
    icon.parent.mkdir()
    icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"/>')
    result = template_project.build_qgis_project(
        str(data),
        str(project),
        "simple_inventory",
        "EPSG:3857",
        {"mode": "online", "consent_accepted": False, "vworld_api_key": "secret-vworld"},
        plantnet_config={"consent_accepted": False, "api_key": "secret-plantnet"},
        svg_relative_path="symbols/test.svg",
    )
    assert not result["online_key_embedded"] and not result["plantnet_key_embedded"]
    assert "secret-" not in project.read_text()
    assert template_project.inspect_project(str(project))[0]
    document = ET.parse(project)
    assert document.findtext("./projectCrs/spatialrefsys/authid") == "EPSG:3857"
    assert (
        document.find(".//layer[@class='SvgMarker']//Option[@value='symbols/test.svg']") is not None
    )


@pytest.mark.parametrize("invalid_database", [False, True])
def test_inspect_project_closes_sqlite_connections(tmp_path, monkeypatch, invalid_database):
    from qfield_builder import gpkg, template_project

    data, project = tmp_path / "data.gpkg", tmp_path / "project.qgs"
    gpkg.build_geopackage(str(data), "simple_inventory", "test")
    template_project.build_qgis_project(
        str(data), str(project), "simple_inventory", "EPSG:4326", None
    )
    if invalid_database:
        data.write_bytes(b"not a SQLite database")
    connections = []
    connect = sqlite3.connect

    def track_connection(*args, **kwargs):
        conn = connect(*args, **kwargs)
        connections.append(conn)  # Retain references so GC cannot hide an unclosed connection.
        return conn

    monkeypatch.setattr(template_project.sqlite3, "connect", track_connection)
    try:
        valid, _, issues = template_project.inspect_project(str(project))
        assert valid is not invalid_database
        if invalid_database:
            assert any(issue["code"] == "project_structure_invalid" for issue in issues)
        assert connections
        for conn in connections:
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                conn.execute("SELECT 1")
    finally:
        for conn in connections:
            conn.close()


def test_app_runtime_check_does_not_start_wizard(monkeypatch):
    from qfield_builder.ui import app

    def forbidden(*args):
        raise AssertionError("Runtime check must not start the GUI")

    monkeypatch.setattr(app, "QApplication", forbidden)
    assert app.main(["fieldbuild", "--check-runtime"]) == 0
