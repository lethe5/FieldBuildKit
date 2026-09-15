"""Acceptance bridge for generated route modules and real desktop/build geometry paths.

Device inputs and routing replies are injected; application algorithms remain in generated JS.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import build, site_upload, wkt

_APP = None


def _build(work: Path, **config):
    options = {"project_display_name": "Synthetic route " + uuid.uuid4().hex[:8], "survey_type": "temporary_plots", "basemap": {"mode": "none"}}
    options.update(config)
    result = build.build_project(options, str(work / ("project-" + uuid.uuid4().hex[:8])))
    if not result["success"]:
        raise RuntimeError(result["error_message"])
    return result


def _node(case, project_dir):
    driver = Path(__file__).resolve().parent.parent / "tests/unit/survey_route_qml_driver.py"
    proc = subprocess.run([sys.executable, str(driver)], input=json.dumps({"case": case, "project_dir": project_dir}), text=True, encoding="utf-8", errors="replace", capture_output=True, check=False, timeout=45)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)


def _geojson(text):
    kind, coords = wkt.geometry_data(text)
    names = {v.upper(): v for v in ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")}
    return {"type": names[kind], "coordinates": coords}


def _source_geojson(text):
    """Parse a WKT fixture without applying the product's dimensional normalization."""
    match = re.fullmatch(r"\s*([A-Za-z]+)\s*(ZM|Z|M)?\s*(\(.*\))\s*", text, re.S | re.I)
    if not match:
        raise ValueError("invalid source fixture WKT")
    kind, dimensions, body = match[1].upper(), (match[2] or "").upper(), match[3]
    names = {v.upper(): v for v in ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon")}
    if kind not in names:
        raise ValueError("unsupported source fixture WKT")
    tokens = re.findall(r"[(),]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", body)
    position = 0
    def group():
        nonlocal position
        if position >= len(tokens) or tokens[position] != "(":raise ValueError("invalid source fixture WKT")
        position += 1;result=[]
        while position < len(tokens) and tokens[position] != ")":
            if tokens[position] == "(":result.append(group())
            else:
                point=[]
                while position < len(tokens) and tokens[position] not in (",", ")", "("):
                    point.append(float(tokens[position]));position += 1
                if len(point) != 2 + len(dimensions):raise ValueError("invalid source fixture coordinate")
                result.append(point)
            if position < len(tokens) and tokens[position] == ",":position += 1
        if position >= len(tokens):raise ValueError("invalid source fixture WKT")
        position += 1;return result
    coordinates=group()
    if position != len(tokens):raise ValueError("invalid source fixture WKT")
    if kind == "POINT":coordinates=coordinates[0]
    if kind == "MULTIPOINT":coordinates=[v[0] if isinstance(v,list) and len(v)==1 and isinstance(v[0],list) else v for v in coordinates]
    return {"type":names[kind],"coordinates":coordinates}


def _draw(case):
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton
    from .ui.wizard import SiteInputPage
    _APP = QApplication.instance() or QApplication([])
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)
    kinds = [page.geometry_type_combo.itemData(i) for i in range(page.geometry_type_combo.count())]
    page.geometry_type_combo.setCurrentIndex(kinds.index(case["geometry_type"]))
    canvas = page.draw_map_canvas
    canvas.resize(600, 400)
    vertices = case["vertices"]
    if vertices:
        canvas.set_view(vertices[0][0], vertices[0][1], 8)
    finish = next(b for b in page.findChildren(QPushButton) if b.text() == "도형 완성")
    commit = next(b for b in page.findChildren(QPushButton) if b.text() == "이 사이트로 저장하고 새 도형 그리기")
    for name in case.get("names", ["그린 대상"]):
        page.draw_site_name_edit.setText(name)
        for x,y in vertices:
            px,py = canvas.lonlat_to_widget(x,y)
            if case["geometry_type"] == "Point": canvas.place_point_at(px,py)
            else: canvas.add_polygon_vertex_at(px,py)
        finish.click()
        if not page.drawn_site_wkt(): break
        commit.click()
    rows = page.drawn_sites()
    result = {"ok": bool(rows), "message": page.draw_status_label.text(), "offered_types": kinds, "saved_names": [r["site_name"] for r in rows], "geometry_types": [_geojson(r["geom_wkt"])["type"] for r in rows], "finished": bool(rows)}
    page.deleteLater()
    _APP.processEvents()
    return result, rows


def _output_geometry(result):
    import fiona
    with fiona.open(result["gpkg_path"], layer="site") as layer:
        rows = list(layer)
    with sqlite3.connect(result["gpkg_path"]) as db:
        metadata = db.execute("SELECT geometry_type_name FROM gpkg_geometry_columns WHERE table_name='site'").fetchone()[0]
        ids = [r[0] for r in db.execute("SELECT fid FROM site ORDER BY fid")]
        tree = [r[0] for r in db.execute("SELECT id FROM rtree_site_site_geom ORDER BY id")]
    db.close()
    import xml.etree.ElementTree as ET
    layers = ET.parse(result["qgs_path"]).findall("./projectlayers/maplayer")
    layer = next(l for l in layers if l.findtext("datasource", "").endswith("|layername=site"))
    return {"gpkg_path": result["gpkg_path"], "stored_geometries": [json.loads(json.dumps({"type":r.geometry.type,"coordinates":r.geometry.coordinates})) for r in rows], "metadata_matches_storage": all(r.geometry.type.upper()==metadata for r in rows), "project_geometry_type": layer.findtext("wkbType"), "stored_family": rows[0].geometry.type.removeprefix("Multi") if rows else None, "metadata_family": metadata.removeprefix("MULTI").title().replace("Linestring", "LineString"), "project_family": layer.findtext("wkbType").removeprefix("Multi"), "feature_ids": ids, "rtree_ids": tree, "site_ids": [r.properties["site_id"] for r in rows]}


def _project_variables(qgs_path):
    import xml.etree.ElementTree as ET
    root = ET.parse(qgs_path).getroot()
    names = [node.text or "" for node in root.findall("./properties/Variables/variableNames/value")]
    values = [node.text or "" for node in root.findall("./properties/Variables/variableValues/value")]
    return dict(zip(names, values))


def _project_general_settings(qgs_path):
    import xml.etree.ElementTree as ET
    properties = ET.parse(qgs_path).getroot().find("./properties")
    if properties is None:
        return {}
    return {
        child.tag: ET.tostring(child, encoding="unicode")
        for child in properties
        if child.tag != "Variables"
    }


def _route_project_settings(project_dir):
    records = []
    for path in Path(project_dir).glob("survey-routes.*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and isinstance(record.get("revision"), int):
            records.append(record)
    if not records:
        return {}
    return max(records, key=lambda record: record["revision"]).get("data", {}).get("settings", {})


def _builder_reports(project_dir, build_result):
    reports = []
    seen = set()
    paths = list(Path(project_dir).glob("*VALIDATION_REPORT*.json")) if Path(project_dir).is_dir() else []
    report_path = build_result.get("validation_report_path")
    if report_path:
        paths.append(Path(report_path))
    for path in paths:
        try:
            resolved = path.resolve()
            if resolved in seen:
                continue
            reports.append(json.loads(path.read_text(encoding="utf-8")))
            seen.add(resolved)
        except (OSError, ValueError):
            continue
    if build_result.get("validation_report") and not reports:
        reports.append(build_result["validation_report"])
    return reports


def _builder_route_key(case, work):
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLineEdit
    from . import credential_store
    from .ui.wizard import ProjectBuilderWizard, compute_final_output_dir

    _APP = QApplication.instance() or QApplication([])
    store_dir = work / ("credentials-" + uuid.uuid4().hex[:8])
    previous_store = os.environ.get(credential_store._APP_DATA_DIR_ENV_OVERRIDE)
    os.environ[credential_store._APP_DATA_DIR_ENV_OVERRIDE] = str(store_dir)
    credential_store.lock_session()
    credential_store.set_session_route_key(None)
    wizard = None
    try:
        key = str(case.get("input_key") or "")
        remember = bool(case.get("remember"))
        if remember:
            credential_store.establish_password("acceptance-only-password")
        wizard = ProjectBuilderWizard()
        display_name = "Synthetic route key " + uuid.uuid4().hex[:8]
        output_parent = work
        if case.get("outcome") == "generation_failure":
            output_parent = work / ("blocked-parent-" + uuid.uuid4().hex[:8])
            output_parent.write_text("builder storage fault", encoding="utf-8")
        wizard.setField("project_display_name", display_name)
        wizard.setField("output_dir", str(output_parent))
        survey_page = wizard.page(1)
        for radio in survey_page.radio_buttons:
            if radio.property("survey_type_value") == "temporary_plots":
                radio.setChecked(True)
                break
        page = wizard.page(6)
        page.route_api_key_edit.setText(key)
        page.route_key_consent_checkbox.setChecked(bool(case.get("consent")))
        page.route_key_remember_checkbox.setChecked(remember)
        warning = page.route_key_warning_label.text()
        project_dir = Path(compute_final_output_dir(str(output_parent), display_name))
        observed_results = []
        progress = []
        real_finished = page._on_build_finished
        real_progress = page._on_build_progress

        def observe_finished(result):
            observed_results.append(json.loads(json.dumps(result)))
            real_finished(result)

        def observe_progress(update):
            progress.append(json.loads(json.dumps(update)))
            real_progress(update)

        page._on_build_finished = observe_finished
        page._on_build_progress = observe_progress
        page.build_button.click()
        worker = page._worker_thread
        if case.get("outcome") == "cancel" and worker is not None:
            page.cancel_build_button.click()
        deadline = time.monotonic() + 120
        while worker is not None and (worker.isRunning() or not observed_results):
            _APP.processEvents()
            if time.monotonic() > deadline:
                worker.cancel()
                worker.wait(5000)
                raise RuntimeError("builder route-key action did not settle")
            time.sleep(0.005)
        _APP.processEvents()
        built = observed_results[-1] if observed_results else {
            "success": False,
            "cancelled": False,
            "error_code": "builder_not_started",
            "error_message": page.result_label.text(),
        }
        qgs_candidates = list(project_dir.glob("*.qgs")) if project_dir.is_dir() else []
        qgs_path = Path(built.get("qgs_path") or (qgs_candidates[0] if qgs_candidates else project_dir / "unpublished.qgs"))
        published = bool(page.isComplete() and qgs_path.is_file())
        variables = _project_variables(qgs_path) if published else {}
        general_settings = _project_general_settings(qgs_path) if published else {}
        routed = {}
        if published:
            node_case = {"operation": "route_key_availability", "scope": "all", "survey_type": "temporary_plots"}
            if case.get("calculate_after_build"):
                node_case["operation"] = "calculate"
                if variables.get("fieldbuild_route_api_key"):
                    node_case["use_project_key"] = True
                else:
                    node_case["key"] = str(case.get("manual_session_key") or "")
                    node_case["restart_after_calculate"] = True
            routed = _node(node_case, str(project_dir))
        requests = routed.get("requests", [])
        manual_key = str(case.get("manual_session_key") or "")
        project_key = variables.get("fieldbuild_route_api_key", "")
        expected_transport_key = project_key or manual_key
        authorization_values = [request.get("headers", {}).get("Authorization") for request in requests]
        transport_key_present = bool(requests) and bool(expected_transport_key) and all(
            value == expected_transport_key for value in authorization_values
        )
        if transport_key_present and project_key:
            qfield_key_source = "project_variable"
        elif transport_key_present and manual_key:
            qfield_key_source = "session"
        else:
            qfield_key_source = None
        credential_path = credential_store.credentials_file_path()
        remembered = bool(
            remember and credential_path.is_file()
            and credential_store.get_remembered_route_key() == key.strip()
        )
        qfield_credential_copies = list(project_dir.rglob("credentials.enc")) if published else []
        route_key_input = routed.get("route_key_input", {})
        result = {
            "key_input_echo_mode": "password" if page.route_api_key_edit.echoMode() == QLineEdit.EchoMode.Password else str(page.route_api_key_edit.echoMode()),
            "consent_required": bool(key and page.route_key_consent_checkbox.isEnabled()),
            "warning_disclosures": {
                "plaintext_project": "평문" in warning,
                "folder_access_can_read_and_use": all(word in warning for word in ("프로젝트 폴더", "읽고 사용할")),
                "not_encrypted": "암호화되지 않습니다" in warning,
                "qfield_automatic_use": all(word in (warning + page.route_key_consent_checkbox.text()) for word in ("QField", "자동 사용")),
            },
            "project_published": published,
            "project_dir": str(project_dir),
            "qgs_path": str(qgs_path),
            "project_variables": variables,
            "general_settings": general_settings,
            "persisted_settings": _route_project_settings(project_dir) if published else {},
            "logs": {"builder_progress": progress, "builder_message": page.result_label.text(), "route_runtime": routed.get("logs", "")},
            "errors": [] if published else [value for value in (built.get("error_code"), built.get("error_message")) if value],
            "reports": _builder_reports(project_dir, built),
            "message": routed.get("message", ""),
            "qml_errors": routed.get("qml_errors", []),
            "requests": requests,
            "transport_key_present": transport_key_present,
            "qfield_key_source": qfield_key_source,
            "manual_session_available": bool(route_key_input.get("available") and route_key_input.get("enabled") and route_key_input.get("password_echo")),
            "session_key_present_after_restart": bool(routed.get("session_key_present_after_restart")),
            "desktop_credential_store": str(credential_path),
            "remembered_key_available_to_qfield": bool(remembered and qfield_credential_copies),
        }
        return result
    finally:
        if wizard is not None:
            page = wizard.page(6)
            worker = page._worker_thread if page is not None else None
            if worker is not None and worker.isRunning():
                worker.cancel()
                worker.wait(5000)
            wizard.deleteLater()
            _APP.processEvents()
        credential_store.lock_session()
        credential_store.set_session_route_key(None)
        if previous_store is None:
            os.environ.pop(credential_store._APP_DATA_DIR_ENV_OVERRIDE, None)
        else:
            os.environ[credential_store._APP_DATA_DIR_ENV_OVERRIDE] = previous_store


def run(*, case: dict, work_dir: str):
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    op = case["operation"]
    if op == "builder_route_key":
        return _builder_route_key(case, work)
    if op in {"draw", "direct_build"}:
        actual = dict(case)
        if op == "direct_build":
            shape = _geojson(case["wkt"])
            actual["vertices"] = [shape["coordinates"]] if shape["type"] == "Point" else shape["coordinates"][0] if shape["type"] == "Polygon" else shape["coordinates"]
        observation, rows = _draw(actual)
        if rows:
            output = _build(work, sites=rows, site_geometry_type=case["geometry_type"].upper())
            observed = _output_geometry(output)
            observation.update(observed)
        else:
            observation["site_ids"] = []
        return observation
    if op in {"upload_build", "geometry_roundtrip"}:
        if op == "geometry_roundtrip":
            import fiona
            source = work / "source-roundtrip.gpkg"
            with fiona.open(source, "w", driver="GPKG", crs=case["crs"], schema={"geometry":"Unknown","properties":{"site_name":"str"}}) as dst:
                for i,text in enumerate(case["wkts"]): dst.write({"geometry":_source_geojson(text),"properties":{"site_name":str(i)}})
            with fiona.open(source) as layer:
                source_geometries=[json.loads(json.dumps({"type":row.geometry.type,"coordinates":row.geometry.coordinates})) for row in layer]
        else: source = Path(case["source"])
        fmt = site_upload.infer_format(str(source))
        records = site_upload.read_upload_features(fmt, str(source), "utf-8")
        detected = _geojson(records[0].geom_wkt)["type"] if records else None
        result = _build(work, sites_upload={"format":fmt,"path":str(source),"encoding":"utf-8","attribute_mapping":{"site_name":"site_name"}}, storage_crs="EPSG:4326")
        return {**_output_geometry(result),"detected_type":detected,**({"source_geometries":source_geometries} if op=="geometry_roundtrip" else {})}
    if op == "geometry_failure":
        if case["fault"] in {"missing_crs", "invalid_crs", "transform_failure"}:
            result = _build(work)
            return _node(case, result["project_dir"])
        import fiona
        source = work / "invalid.gpkg"
        crs = None if case["fault"]=="unknown_crs" else "EPSG:4326"
        shapes = [{"type":"Point","coordinates":[0,0]}]
        if case["fault"]=="mixed_families": shapes.append({"type":"LineString","coordinates":[[0,0],[1,1]]})
        if case["fault"]=="empty": shapes=[None]
        if case["fault"]=="invalid_geometry": shapes=[{"type":"Polygon","coordinates":[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}]
        with fiona.open(source,"w",driver="GPKG",crs=crs,schema={"geometry":"Unknown","properties":{"site_name":"str"}}) as dst:
            for g in shapes: dst.write({"geometry":g,"properties":{"site_name":"invalid"}})
        result = build.build_project({"project_display_name":"Invalid","survey_type":"temporary_plots","sites_upload":{"format":"gpkg","path":str(source)},"basemap":{"mode":"none"}},str(work/"invalid-output"))
        return {"ok":result["success"],"message":result["error_message"] or "", "requests":[],"published_features":[] if not result["success"] else _output_geometry(result)["stored_geometries"]}
    if op == "representative":
        result = _build(work)
        original=work/"representative-source.wkt"
        original.write_text(case["wkt"],encoding="utf-8")
        before=original.read_bytes()
        route_result=_node({"operation":"generated_geometry_calculate","wkt":case["wkt"],"crs":case["crs"]},result["project_dir"])
        coordinate=route_result["request_coordinate"]
        return {"coordinate":coordinate,"request_coordinate":coordinate,"original_before":before,"original_after":original.read_bytes()}
    if op == "generate_plugin":
        result = _build(work, identification_enabled=True)
        observed = _qml_probe(result, work)
        observed["project_dir"] = result["project_dir"]
        observed["loaded_features"] = set(observed.get("loaded_features", []))
        observed["asset_paths"] = [str(p.relative_to(result["project_dir"])) for p in Path(result["project_dir"]).rglob("*") if p.is_file() and p.suffix in (".qml", ".js", ".svg")]
        return observed
    if op == "generated_geometry_calculate":
        # The generated project supplies the production QML/JS.  The QField-shaped
        # driver supplies the source feature and layer CRS so projected fixtures do
        # not get written into the builder's fixed WGS84 site store.
        result = _build(work)
        gpkg = Path(result["gpkg_path"])
        before = gpkg.read_bytes()
        observed = _node(case, result["project_dir"])
        observed["original_before"] = before.hex()
        observed["original_after"] = gpkg.read_bytes().hex()
        return observed
    if op == "regression":
        return _regression(case, work)
    result = _build(work, survey_type=case.get("survey_type", "temporary_plots"))
    return _node(case,result["project_dir"])


def _qml_probe(result, work, widget_source=None):
    driver = Path(__file__).resolve().parent.parent / "tests/unit/survey_route_qml_probe.py"
    proc = subprocess.run([sys.executable, str(driver)], input=json.dumps({"project_dir":result["project_dir"],"qml_path":str(Path(result["qgs_path"]).with_suffix(".qml")),"work_dir":str(work),"widget_source":widget_source}), text=True,encoding="utf-8",errors="replace",capture_output=True,timeout=45)
    if proc.returncode:raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)


def _regression(case, work):
    import xml.etree.ElementTree as ET
    import fiona
    from unittest.mock import patch
    from . import schemas, gpkg, canonical_reference, html_report_refresh_bridge, validate
    config = {"survey_type":case["survey_type"],"identification_enabled":True}
    if case["reference"]:
        from openpyxl import Workbook
        book=Workbook();sheet=book.active;sheet.title="Data Sheet"
        sheet.append(list(canonical_reference.SOURCE_COLUMNS));sheet.append([None]*len(canonical_reference.SOURCE_COLUMNS))
        row={"No":1,"관리분류군":"관속식물류","정이명여부":"정명","학명":"Synthetic species","대표국명":"가상식물","URL":canonical_reference.CANONICAL_URL_PREFIX+"000000000001"}
        sheet.append([row.get(k) for k in canonical_reference.SOURCE_COLUMNS]);source=work/"fictional.xlsx";book.save(source);config["canonical_reference_path"]=str(source)
    if case["survey_type"]!="simple_inventory":config.update(sites=[{"site_name":"선 대상","geom_wkt":"LINESTRING(127 37,127.001 37.001)"}],site_geometry_type="LINESTRING")
    result=_build(work,**config)
    schema=schemas.get_schema(case["survey_type"],taxonomy_reference_available=case["reference"])
    db=gpkg._connect(result["gpkg_path"])
    ids={}
    for name,table in schema.items():
        existing=db.execute(f'SELECT "{table.uuid_pk}" FROM "{name}" LIMIT 1').fetchone()
        if existing:ids[name]=existing[0];continue
        values={table.uuid_pk:str(uuid.uuid4())}
        if table.foreign_key:values[table.foreign_key.column]=ids[table.foreign_key.ref_table]
        for column in table.columns:
            if column.name in values:continue
            if column.name=="selected_scientific_name":values[column.name]="Synthetic species"
            elif column.name=="selected_korean_name":values[column.name]="가상식물"
            elif column.not_null and column.default_sql is None:values[column.name]="Synthetic" if column.sql_type=="TEXT" else 0
        if table.geometry:
            text="POINT(127 37)" if table.geometry.geom_type=="POINT" else "MULTIPOLYGON(((127 37,127.001 37,127 37.001,127 37)))"
            values[table.geometry.column]=wkt.wkt_to_gpkg_geometry(text,table.geometry.geom_type)[0]
        columns=','.join('"'+key+'"' for key in values);marks=','.join('?' for _ in values)
        db.execute(f'INSERT INTO "{name}" ({columns}) VALUES ({marks})',list(values.values()));ids[name]=values[table.uuid_pk]
    db.commit();db.close()
    (Path(result["project_dir"])/"Synthetic").write_bytes(b"fictional attachment")
    def snapshot(output):
        conn=sqlite3.connect(output["gpkg_path"])
        uuids={name:[r[0] for r in conn.execute(f'SELECT "{table.uuid_pk}" FROM "{name}" ORDER BY fid')] for name,table in schema.items()}
        geometry={name:[r[0].hex() for r in conn.execute(f'SELECT "{table.geometry.column}" FROM "{name}" WHERE "{table.geometry.column}" IS NOT NULL')] for name,table in schema.items() if table.geometry and name!="site"}
        conn.close()
        relations=[ET.tostring(r,encoding="unicode") for r in ET.parse(output["qgs_path"]).findall("./relations/relation")]
        if not relations:relations=[ET.tostring(ET.parse(output["qgs_path"]).find("./relations"),encoding="unicode")]
        return uuids,geometry,relations
    before=snapshot(result)
    legacy=_build(work,sites=[{"site_name":"기존 면","geom_wkt":"POLYGON((127 37,127.01 37,127 37.01,127 37))"}])
    legacy_bytes=Path(legacy["gpkg_path"]).read_bytes()
    existing=work/"existing-user-project";shutil.copytree(legacy["project_dir"],existing)
    user_before={str(p.relative_to(existing)):p.read_bytes() for p in existing.rglob("*") if p.is_file()}
    old=Path(result["project_dir"]);moved=old.with_name(old.name+"-moved");shutil.move(old,moved)
    for key in ("project_dir","gpkg_path","qgs_path"):
        result[key]=str(moved/(Path(result[key]).relative_to(old))) if key!="project_dir" else str(moved)
    after=snapshot(result)
    document=ET.parse(result["qgs_path"])
    widget=next(e.text for e in document.findall(".//attributeEditorQmlElement") if e.text)
    probe=_qml_probe(result,work,widget)
    if probe.get("widget_errors") or not probe.get("identification_candidate"):raise RuntimeError(str(probe))
    layers=[]
    for name,table in schema.items():
        with fiona.open(result["gpkg_path"],layer=name) as source:
            features=[]
            for row in source:
                shape={"type":row.geometry.type,"coordinates":row.geometry.coordinates} if row.geometry else None
                features.append({"attributes":dict(row.properties),"geometry":{"asJson":{"return":shape}} if shape else None})
            layers.append({"name":name,"fields":[c.name for c in table.columns],"geometry_column":table.geometry.column if table.geometry else None,"crs_authid":"EPSG:4326","features":features})
    provider={"project":{"survey_type":case["survey_type"],"project_slug":Path(result["qgs_path"]).stem},"loaded_layers":layers,"direct_gpkg":{"available":False}}
    generated=Path(result["qgs_path"]).with_suffix(".qml").read_text(encoding="utf-8")
    with patch.object(html_report_refresh_bridge,"render_project_plugin_qml",return_value=generated):
        report=html_report_refresh_bridge.render_html_report_refresh_fixture({"qgis_provider":provider,"html_runtime":{}})
    if not report["success"]:raise RuntimeError(report["error_message"])
    report_payload=report["bridge"]["qml"]["report_payload"]
    (work/"report-payload.json").write_text(json.dumps(report_payload,ensure_ascii=False),encoding="utf-8")
    rows=[]
    for row in report_payload.get("joined",[]):
        attrs=row.get("values",row)
        anchor={"simple_inventory":"inventory_observation","temporary_plots":"survey","permanent_plots":"plot","vegetation_mapping":"community"}[case["survey_type"]]
        source_id=row.get("source_values",{}).get(anchor+"_uuid")
        layer=next(l for l in layers if l["name"]==anchor)
        feature=next((f for f in layer["features"] if f["attributes"].get(schema[anchor].uuid_pk)==source_id),None)
        geometry=feature["geometry"]["asJson"]["return"] if feature and feature["geometry"] else {}
        rows.append({"geometry_type":geometry.get("type","None"),"longitude":attrs.get("report__longitude"),"latitude":attrs.get("report__latitude")})
    checked=validate.validate_project(result["project_dir"])
    columns=[]
    conn=sqlite3.connect(result["gpkg_path"])
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        columns.extend(r[1] for r in conn.execute(f'PRAGMA table_info("{name}")'))
    conn.close()
    return {"uuid_before":before[0],"uuid_after":after[0],"non_site_geometry_before":before[1],"non_site_geometry_after":after[1],"relations_before":before[2],"relations_after":after[2],"legacy_polygon_before":legacy_bytes,"legacy_polygon_after":Path(legacy["gpkg_path"]).read_bytes(),"existing_user_project_before":user_before,"existing_user_project_after":{str(p.relative_to(existing)):p.read_bytes() for p in existing.rglob("*") if p.is_file()},"broken_sources":[issue for issue in checked.get("issues",[]) if "source" in str(issue)],"validation_errors":checked.get("issues",[]),"report_rows":rows,"identification_candidate":probe["identification_candidate"],"ktsn_present":any("ktsn" in name.lower() for name in columns)}
