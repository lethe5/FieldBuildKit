"""D-98: real portable builds and wizard selection without private storage assets."""

import json
import shutil
import sqlite3
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
import rasterio
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton
from rasterio.transform import from_origin

from qfield_builder import build, canonical_reference, probability_raster, qml_plugin, schemas, validate
from qfield_builder.ui import wizard as wizard_module
from qfield_builder.ui.wizard import ProjectBuilderWizard

SAMPLE = Path(__file__).resolve().parents[2] / "resources/samples/taxonomy_sample.xlsx"
POLYGON = "MULTIPOLYGON(((127 37,127.01 37,127.01 37.01,127 37.01,127 37)))"


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
@pytest.mark.parametrize("identification", [False, True])
@pytest.mark.parametrize("inputs", ["none", "workbook", "rasters", "both"])
def test_optional_inputs_build_and_relocate(
    tmp_path, monkeypatch, survey_type, identification, inputs
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Normal builds must not discover storage or legacy references")

    monkeypatch.setattr(build, "_resolve_reference_data_dir", forbidden)
    monkeypatch.setenv("REFERENCE_DATA_DIR", str(tmp_path / "unusable-private-data"))
    config = {
        "project_display_name": "Optional test",
        "survey_type": survey_type,
        "identification_enabled": identification,
    }
    if survey_type != "simple_inventory":
        config["sites"] = [{"site_name": "Synthetic site", "geom_wkt": POLYGON}]
    has_workbook = inputs in ("workbook", "both")
    has_raster = inputs in ("rasters", "both")
    if has_workbook:
        config["canonical_reference_path"] = str(SAMPLE)
    if has_raster:
        folder = tmp_path / "local TIFF 한글"
        folder.mkdir()
        source = folder / "지역_가상풀_2026.TIFF"
        with rasterio.open(
            source,
            "w",
            driver="GTiff",
            width=2,
            height=2,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            nodata=float("nan"),
            transform=from_origin(127, 37.02, 0.01, 0.01),
        ) as raster:
            raster.write(np.array([[0.25, np.nan], [0.25, 0.25]], dtype="float32"), 1)
        original = source.read_bytes()
        config["probability_raster_source_dir"] = str(folder)
    result = build.build_project(config, str(tmp_path / "output"))
    if has_raster and not (identification and has_workbook):
        assert not result["success"]
        assert result["error_code"] == "probability_prerequisites_missing"
        assert not (tmp_path / "output").exists()
        return
    assert result["success"], result
    relocated = tmp_path / "moved" / "project"
    shutil.move(result["project_dir"], relocated)
    assert validate.validate_project(str(relocated))["success"]
    doc = ET.parse(relocated / "optional-test.qgs")
    sources = [node.text or "" for node in doc.findall(".//projectlayers/maplayer/datasource")]
    assert not any(str(tmp_path) in value or "storage/" in value for value in sources)
    with sqlite3.connect(relocated / "data/optional-test.gpkg") as db:
        tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
        assert ("ktsn_accepted_name_lookup" in tables) == has_workbook
        for name in ("observation", "inventory_observation"):
            if name in tables:
                fields = [row[1] for row in db.execute(f'PRAGMA table_info("{name}")')]
                assert ("selected_ktsn" in fields) == has_workbook
    for layer in doc.findall(".//projectlayers/maplayer"):
        fields = [field.get("name") for field in layer.findall("./fieldConfiguration/field")]
        if "selected_korean_name" in fields:
            assert ("selected_ktsn" in fields) == has_workbook
            for element in layer.findall(".//attributeEditorField"):
                assert fields[int(element.get("index"))] == element.get("name")
            for element in layer.findall("./aliases/alias"):
                assert fields[int(element.get("index"))] == element.get("field")
    plugin = (relocated / "optional-test.qml").read_text()
    definition = json.loads(plugin.split("readonly property var qpbReportDefinition: ")[1].splitlines()[0][1:-1])
    reported_fields = [field["name"] for table in definition["tables"] for field in table["fields"]]
    assert ("selected_ktsn" in reported_fields) == (has_workbook and survey_type != "vegetation_mapping")
    assert (relocated / probability_raster.STACK_RELPATH).exists() == has_raster
    manifest = json.loads((relocated / "MANIFEST.json").read_text())
    if has_raster:
        assert source.read_bytes() == original
        assert manifest["probability_raster"]["band_count"] == 1
        with rasterio.open(relocated / probability_raster.STACK_RELPATH) as raster:
            assert raster.read(1)[0, 0] == 0.25
            assert raster.nodata == -9999 and raster.read(1)[0, 1] == -9999
        assert sorted(p.name for p in folder.iterdir()) == [source.name]
    if not has_workbook:
        identity = doc.find(".//fieldConfiguration/field[@name='selected_korean_name']/editWidget")
        if identity is not None:
            assert identity.get("type") == "TextEdit"
    assert not list(relocated.rglob("*.xlsx"))


@pytest.mark.parametrize("key", ["canonical_reference_path", "probability_raster_source_dir"])
def test_invalid_selected_input_is_not_silently_omitted(tmp_path, key):
    output = tmp_path / "output"
    result = build.build_project(
        {
            "project_display_name": "Invalid",
            "survey_type": "simple_inventory",
            key: str(tmp_path / "missing"),
        },
        str(output),
    )
    assert not result["success"]
    assert not output.exists()


def test_online_satellite_uses_supported_zoom_range(tmp_path):
    result = build.build_project(
        {
            "project_display_name": "Satellite test",
            "survey_type": "simple_inventory",
            "basemap": {
                "mode": "online", "layer": "Satellite", "consent_accepted": True,
                "vworld_api_key": "synthetic-key",
            },
        },
        str(tmp_path / "output"),
    )
    assert result["success"], result
    doc = ET.parse(result["qgs_path"])
    sources = [e.text for e in doc.findall(".//projectlayers/maplayer/datasource")]
    assert any("zmin=6&zmax=19" in source for source in sources)


def test_sample_download_upload_validates_automatically_and_preserves_navigation(
    tmp_path, monkeypatch, wait_reference_validation
):
    app = QApplication.instance() or QApplication([])
    wizard = ProjectBuilderWizard()
    page = wizard.page(4)
    assert page.isComplete()
    page.enable_checkbox.setChecked(False)
    assert page.raster_group.isHidden()
    assert all("선택한 참조 자료 확인" not in b.text() for b in page.findChildren(QPushButton))
    download = tmp_path / "sample.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(download), ""))
    page.sample_download_button.click()
    assert download.read_bytes() == SAMPLE.read_bytes()
    assert page.canonical_reference_config() is None
    result = canonical_reference.ingest_canonical_workbook(str(download))
    assert result["accepted_count"] == 2 and result["synonym_count"] == 1
    monkeypatch.setattr(wizard_module, "_get_open_file_name", lambda *a, **k: (str(download), ""))
    page._browse_reference_source()
    wait_reference_validation(page)
    assert page.isComplete()
    selected = page.canonical_reference_config()
    assert selected["source_kind"] == "user_upload"
    assert selected["sha256"] == result["provenance"]["sha256"]
    page.initializePage()
    assert page.isComplete() and page.canonical_reference_config() == selected
    assert page.raster_group.isHidden()
    page.enable_checkbox.setChecked(True)
    assert not page.raster_group.isHidden()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    page.probability_browse_button.click()
    assert page.probability_reference_config() == str(tmp_path)
    page.enable_checkbox.setChecked(False)
    assert page.raster_group.isHidden() and page.probability_reference_config() is None
    page.enable_checkbox.setChecked(True)
    page.probability_browse_button.click()
    page.probability_clear_button.click()
    page.reference_clear_button.click()
    assert page.isComplete()
    assert page.canonical_reference_config() is None
    assert page.probability_reference_config() is None
    wizard.close()
    app.processEvents()


def test_invalid_upload_clears_validated_reference_and_reselection_recovers(tmp_path, monkeypatch, wait_reference_validation):
    app = QApplication.instance() or QApplication([])
    wizard = ProjectBuilderWizard()
    page = wizard.page(4)
    valid = tmp_path / "valid.xlsx"
    invalid = tmp_path / "invalid.xlsx"
    shutil.copyfile(SAMPLE, valid)
    invalid.write_bytes(b"not a workbook")
    chosen = str(valid)
    monkeypatch.setattr(wizard_module, "_get_open_file_name", lambda *a, **k: (chosen, ""))
    page._browse_reference_source()
    wait_reference_validation(page)
    original = page.canonical_reference_config()
    assert page.isComplete() and original
    page.enable_checkbox.setChecked(True)
    page.probability_source_path_edit.setText(str(tmp_path))
    chosen = str(invalid)
    page._browse_reference_source()
    wait_reference_validation(page)
    assert not page.isComplete()
    assert page.canonical_reference_config() is None
    assert page.raster_group.isHidden() and page.probability_reference_config() is None
    assert page.reference_source_status_label.text()
    page._select_reference_candidate(page.reference_source_preview.item(0))
    assert page.isComplete() and page.canonical_reference_config() == original
    chosen = ""  # Cancelling the picker preserves the previous valid selection.
    page._browse_reference_source()
    assert page.canonical_reference_config() == original
    valid.write_bytes(b"changed after upload")
    page._select_reference_candidate(page.reference_source_preview.item(0))
    assert not page.isComplete() and page.canonical_reference_config() is None
    page.reference_clear_button.click()
    assert page.isComplete()
    wizard.close()
    app.processEvents()


def test_no_workbook_plantnet_candidate_retains_scientific_name_and_no_fake_ktsn():
    source = qml_plugin.render_identification_widget_qml(
        "array()", taxonomy_reference_available=False
    )

    def function(name, end_marker=None):
        start = source.index("function " + name)
        end = source.index(end_marker, start) if end_marker else source.index("\n    }", start) + 6
        return source[start:end]

    script = (
        """
var qpbCanonicalReferenceRequired=false, qpbLastLocation=null, qpbLastModelVersion='';
var qpbCandidatesModel=[], qpbManualEntryPanel={}, qpbStatusLabel={};
var qpbCandidateSelectionEnabled=true;
var qpbWriteBackMode='', written=null;
function qpbFormatProbability(){return {text:'없음',value:null};}
function qpbRefreshCandidateProbabilities(){}
function qpbPersistIdentification(){return true;}
function qpbTraceRuntime(){}
var form={model:{changeAttribute:function(name,value){
    if(!written)written={};written[name]=value;return true;
}}};
"""
        + function("qpbHandlePlantNetResponse", "\n    // Compatibility hook")
        + function("qpbSelectCandidate")
        + function("qpbApplyCurrentFormWriteBack")
        + """
qpbHandlePlantNetResponse({results:[{score:0.8,species:{
scientificName:'Exemplaria alpha Demo',scientificNameWithoutAuthor:'Exemplaria alpha'}}]});
var candidates=qpbCandidatesModel;
qpbSelectCandidate(0);
process.stdout.write(JSON.stringify({candidates:candidates,written:written}));
"""
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert len(data["candidates"]) == 1
    assert data["written"]["selected_scientific_name"] == "Exemplaria alpha Demo"
    assert "selected_ktsn" not in data["written"]
    assert data["written"]["selected_korean_name"] is None


def test_no_workbook_pending_writeback_applies_identity_fields():
    source = qml_plugin.render_project_plugin_qml(
        "optional", taxonomy_reference_available=False
    )
    start = source.index("function qpbApplyPendingWriteBack(request)")
    end = source.index("function qpbIsPendingWriteBackTarget", start)
    script = """
var values={}, qpbWriteBackSearch={};
var model={changeAttribute:function(name,value){values[name]=value;return true;},
    attribute:function(name){return values[name];}};
var iface={findItemByObjectName:function(){return {};}};
function qpbBeginWriteBackSearch(){}
function qpbFindActiveRelationModel(){return model;}
function qpbIsPendingWriteBackTarget(){return true;}
function qpbReadUuidFromFeatureModel(){return 'test-uuid';}
function qpbTraceWriteBack(){}
""" + source[start:end] + """
var ok=qpbApplyPendingWriteBack({uuid:'test-uuid',uuid_field:'uuid',write_back_mode:'candidate',
 fields:{selected_korean_name:null,
         selected_scientific_name:'Exemplaria alpha',selected_ktsn:null}});
process.stdout.write(JSON.stringify({ok:ok,values:values}));
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["ok"]
    assert data["values"]["selected_scientific_name"] == "Exemplaria alpha"
    assert "selected_ktsn" not in data["values"]


def test_probability_filename_matching_uses_reference_names_and_rejects_ambiguity(tmp_path):
    folder = tmp_path / "하위 폴더"
    folder.mkdir()
    filename = unicodedata.normalize("NFD", "지역_큰가상풀_2026.TIFF")
    source = folder / filename
    source.write_bytes(b"II*\x00test")
    unrelated = tmp_path / "다른종.tif"
    unrelated.write_bytes(b"II*\x00test")
    names = ["가상풀", "큰가상풀", "예시나무"]
    species, excluded, error = probability_raster._inventory(str(tmp_path), names)
    assert error is None and species == [("큰가상풀", source)]
    assert unrelated.name in excluded
    other = tmp_path / "큰가상풀_예시나무.tif"
    other.write_bytes(b"II*\x00test")
    assert probability_raster._inventory(str(tmp_path), names)[2]["error_code"] == "species_name_ambiguous"
    other.rename(tmp_path / "큰가상풀_duplicate.tif")
    assert probability_raster._inventory(str(tmp_path), names)[2]["error_code"] == "species_name_collision"


@pytest.mark.parametrize("nodata_values", [(float("nan"), float("nan")), (float("nan"), -9999)])
def test_probability_nan_sources_normalize_without_changing_valid_values(tmp_path, nodata_values):
    folder = tmp_path / "source"
    folder.mkdir()
    names = ["가상풀", "예시나무"]
    originals = {}
    for name, nodata in zip(names, nodata_values):
        source = folder / f"예측_{name}_결과.tiff"
        with rasterio.open(
            source, "w", driver="GTiff", width=2, height=2, count=1, dtype="float32",
            crs="EPSG:4326", nodata=nodata, transform=from_origin(127, 38, 0.1, 0.1),
        ) as raster:
            raster.write(np.array([[0.25, nodata], [-0.1, 1.2]], dtype="float32"), 1)
        originals[source] = source.read_bytes()
    output = tmp_path / "project"
    result = probability_raster.build_probability_stack(str(folder), str(output), korean_names=names)
    assert result["success"], result
    report = probability_raster.inspect_probability_stack(result["stack_path"], str(folder), korean_names=names)
    assert report["valid"] and report["pixel_crosscheck"]["nodata_match"]
    with rasterio.open(result["stack_path"]) as raster:
        assert raster.nodata == -9999
        for band in (1, 2):
            np.testing.assert_array_equal(
                raster.read(band), np.array([[0.25, -9999], [-0.1, 1.2]], dtype="float32")
            )
    for name in names:
        def sample(lon, lat):
            return probability_raster.sample_probability_candidate(
                str(output), name, {"lon": lon, "lat": lat}
            )
        assert sample(127.05, 37.95)["value"] == 0.25
        assert sample(127.15, 37.95)["reason"] == "raster_missing_nodata_or_outside_extent"
        assert sample(127.05, 37.85)["value"] == 0
        assert sample(127.15, 37.85)["reason"] == "raster_invalid_value"
    assert all(source.read_bytes() == original for source, original in originals.items())


@pytest.mark.parametrize("nodata", [None, 0, float("inf")])
def test_probability_rejects_unsupported_nodata(tmp_path, nodata):
    with rasterio.open(
        tmp_path / "가상풀.tif", "w", driver="GTiff", width=1, height=1, count=1,
        dtype="float32", crs="EPSG:4326", nodata=nodata,
        transform=from_origin(127, 38, 0.1, 0.1),
    ) as raster:
        raster.write(np.array([[0.25]], dtype="float32"), 1)
    result = probability_raster.validate_probability_raster_sources(str(tmp_path), korean_names=["가상풀"])
    assert not result["ok"] and result["error_code"] == "source_nodata_incompatible"
