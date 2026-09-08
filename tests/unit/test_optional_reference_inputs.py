"""D-98: real portable builds and wizard selection without private storage assets."""

import json
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
import rasterio
from PySide6.QtWidgets import QApplication, QFileDialog
from rasterio.transform import from_origin

from qfield_builder import build, canonical_reference, probability_raster, qml_plugin, schemas
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
        source = folder / "bce_inverse_corrected_probability_가상풀.tif"
        with rasterio.open(
            source,
            "w",
            driver="GTiff",
            width=2,
            height=2,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            nodata=-9999,
            transform=from_origin(127, 37.02, 0.01, 0.01),
        ) as raster:
            raster.write(np.full((2, 2), 0.25, dtype="float32"), 1)
        original = source.read_bytes()
        config["probability_raster_source_dir"] = str(folder)
    result = build.build_project(config, str(tmp_path / "output"))
    assert result["success"], result
    relocated = tmp_path / "moved" / "project"
    shutil.move(result["project_dir"], relocated)
    doc = ET.parse(relocated / "optional-test.qgs")
    sources = [node.text or "" for node in doc.findall(".//projectlayers/maplayer/datasource")]
    assert not any(str(tmp_path) in value or "storage/" in value for value in sources)
    with sqlite3.connect(relocated / "data/optional-test.gpkg") as db:
        tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
        assert ("ktsn_accepted_name_lookup" in tables) == has_workbook
    assert (relocated / probability_raster.STACK_RELPATH).exists() == has_raster
    manifest = json.loads((relocated / "MANIFEST.json").read_text())
    if has_raster:
        assert source.read_bytes() == original
        assert manifest["probability_raster"]["band_count"] == 1
        with rasterio.open(relocated / probability_raster.STACK_RELPATH) as raster:
            assert raster.read(1)[0, 0] == 0.25
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


def test_sample_download_confirm_clear_and_back_navigation(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    wizard = ProjectBuilderWizard()
    page = wizard.page(4)
    assert page.isComplete()
    download = tmp_path / "sample.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(download), ""))
    page.sample_download_button.click()
    assert download.read_bytes() == SAMPLE.read_bytes()
    assert page.canonical_reference_config() is None
    result = canonical_reference.ingest_canonical_workbook(str(download))
    assert result["accepted_count"] == 2 and result["synonym_count"] == 1
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(download), ""))
    page._browse_reference_source()
    assert not page.isComplete()
    page._confirm_reference_source()
    selected = page.canonical_reference_config()
    assert selected["source_kind"] == "user_upload"
    page.initializePage()
    assert page.isComplete() and page.canonical_reference_config() == selected
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    page.probability_browse_button.click()
    assert page.probability_reference_config() == str(tmp_path)
    page.probability_clear_button.click()
    page.reference_clear_button.click()
    assert page.isComplete()
    assert page.canonical_reference_config() is None
    assert page.probability_reference_config() is None
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
    assert data["written"]["selected_ktsn"] is None
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
    assert data["values"]["selected_ktsn"] is None
