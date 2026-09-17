"""Acceptance bridge for generated route modules and real desktop/build geometry paths.

Device inputs and routing replies are injected; application algorithms remain in generated JS.
"""
from __future__ import annotations

import json
import hashlib
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


def _generated_site_style(case, work):
    import xml.etree.ElementTree as ET
    import fiona

    kind = case["geometry_type"]
    name_field = case["name_field"]
    source = work / ("site-style-source-" + uuid.uuid4().hex[:8] + ".gpkg")

    def geometry(index):
        x, y = 127 + index * .012, 37 + index * .008
        if kind == "Point":
            return {"type": kind, "coordinates": [x, y]}
        if kind == "LineString":
            return {"type": kind, "coordinates": [[x, y], [x + .007, y + .005]]}
        return {"type": kind, "coordinates": [[
            [x, y], [x + .007, y], [x + .007, y + .005], [x, y + .005], [x, y]
        ]]}

    with fiona.open(
        source,
        "w",
        driver="GPKG",
        layer="source_site",
        crs="EPSG:4326",
        schema={"geometry": kind, "properties": {name_field: "str"}},
    ) as target:
        for index, name in enumerate(case["names"]):
            target.write({"geometry": geometry(index), "properties": {name_field: name}})

    def read_source():
        with fiona.open(source, layer="source_site") as provider:
            return [{
                "attributes": dict(row.properties),
                "geometry": {"type": row.geometry.type, "coordinates": row.geometry.coordinates},
            } for row in provider]

    source_before = read_source()
    result = _build(
        work,
        sites_upload={
            "format": "gpkg",
            "path": str(source),
            "attribute_mapping": {"site_name": name_field},
        },
        survey_route={"name_field": name_field},
        storage_crs="EPSG:4326",
    )
    root = ET.parse(result["qgs_path"])
    layer = next(item for item in root.findall("./projectlayers/maplayer")
                 if item.findtext("datasource", "").endswith("|layername=site"))
    labeling = layer.find("labeling/settings/text-style")
    buffer = labeling.find("text-buffer")
    options = {item.get("name"): item.get("value") for item in layer.findall("./renderer-v2//Option[@name]")}

    def color(value):
        red, green, blue = (int(part) for part in value.split(",")[:3])
        return f"#{red:02X}{green:02X}{blue:02X}"

    base = {}
    if kind == "Polygon":
        base = {"outline_color": color(options["outline_color"]), "fill_color": color(options["color"]),
                "fill_opacity": int(options["color"].split(",")[3]) / 255}

    with fiona.open(result["gpkg_path"], layer="site") as provider:
        generated = [{
            "attributes": dict(row.properties),
            "geometry": {"type": row.geometry.type, "coordinates": row.geometry.coordinates},
        } for row in provider]

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QBrush, QFont, QImage, QPainter, QPainterPath, QPen, QPolygonF
    from PySide6.QtWidgets import QApplication

    global _APP
    _APP = QApplication.instance() or QApplication([])

    def qcolor(value):
        channels = [int(part) for part in value.split(",")[:4]]
        return QColor(*channels)

    if kind == "Polygon":
        outline_color, fill_color = qcolor(options["outline_color"]), qcolor(options["color"])
    elif kind == "LineString":
        outline_color = fill_color = qcolor(options["line_color"])
    else:
        outline_color = fill_color = qcolor(options["color"])
    text_color = qcolor(labeling.get("textColor"))
    halo_color = qcolor(buffer.get("bufferColor"))

    def coordinate_points(value):
        if isinstance(value, (list, tuple)) and len(value) >= 2 and all(
            isinstance(item, (int, float)) for item in value[:2]
        ):
            return [(float(value[0]), float(value[1]))]
        points = []
        for child in value or []:
            points.extend(coordinate_points(child))
        return points

    all_points = [point for feature in generated for point in coordinate_points(feature["geometry"]["coordinates"])]
    west, east = min(point[0] for point in all_points), max(point[0] for point in all_points)
    south, north = min(point[1] for point in all_points), max(point[1] for point in all_points)
    dx, dy = max(east - west, .01), max(north - south, .01)

    def screen(point):
        return QPointF(36 + (point[0] - west + dx * .08) / (dx * 1.16) * 440,
                       244 - (point[1] - south + dy * .08) / (dy * 1.16) * 184)

    def count_color(image, target):
        expected = target.rgba()
        return sum(image.pixel(x, y) == expected for y in range(image.height()) for x in range(image.width()))

    rendered_labels = []
    renderings = {}
    for basemap_index, basemap in enumerate(case["basemaps"]):
        background = QColor("#F8FAFC" if basemap == "light" else "#111827")
        image = QImage(512, 280, QImage.Format_ARGB32_Premultiplied)
        image.fill(background)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.setPen(QPen(outline_color, 4))
        painter.setBrush(QBrush(fill_color))
        anchors = []
        for feature in generated:
            points = coordinate_points(feature["geometry"]["coordinates"])
            pixels = [screen(point) for point in points]
            if kind == "Point":
                painter.drawEllipse(pixels[0], 8, 8)
            elif kind == "LineString":
                path = QPainterPath(pixels[0])
                for point in pixels[1:]:
                    path.lineTo(point)
                painter.drawPath(path)
            else:
                painter.drawPolygon(QPolygonF(pixels))
            anchors.append(QPointF(sum(point.x() for point in pixels) / len(pixels),
                                   sum(point.y() for point in pixels) / len(pixels)))
        painter.end()
        outline_pixels = count_color(image, outline_color)
        geometry_pixels = sum(
            image.pixelColor(x, y) != background
            for y in range(image.height()) for x in range(image.width())
        )
        white_before = count_color(image, halo_color)

        painter = QPainter(image)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        font = QFont("Sans Serif", int(float(labeling.get("fontSize") or 10)))
        for feature, anchor in zip(generated, anchors):
            value = feature["attributes"].get(name_field)
            if value is None or str(value) == "":
                continue
            text_path = QPainterPath()
            text_path.addText(anchor + QPointF(10, -8), font, str(value))
            # The generated style stores the buffer in millimetres. Render at the standard
            # 96-DPI conversion so a 1 mm QGIS halo remains a visible band around the glyphs.
            painter.strokePath(
                text_path,
                QPen(halo_color, max(2.0, float(buffer.get("bufferSize")) * 96 / 25.4 * 2)),
            )
            painter.fillPath(text_path, text_color)
            if basemap_index == 0:
                rendered_labels.append({
                    "text": str(value),
                    "inert_text": True,
                    "executed_actions": [],
                    "render_surface": "QPainterPath.addText",
                })
        painter.end()
        image_path = work / f"site-style-{kind.lower()}-{basemap}.png"
        if not image.save(str(image_path)):
            raise RuntimeError("site style render image could not be saved")
        renderings[basemap] = {
            "outline_visible": outline_pixels > 0,
            "fill_visible": geometry_pixels > outline_pixels,
            "label_halo_visible": count_color(image, halo_color) > white_before,
            "image_path": str(image_path),
            "observed_outline_pixels": outline_pixels,
            "observed_geometry_pixels": geometry_pixels,
        }

    route_source = (Path(result["project_dir"]) / "qfield_routes" / "RoutePanel.qml").read_text(encoding="utf-8")

    def runtime_color(pattern):
        match = re.search(pattern, route_source, re.S)
        if not match:
            raise RuntimeError("generated route style could not be observed")
        return match.group(1).upper()

    renderer_before = ET.tostring(layer.find("renderer-v2"), encoding="unicode")
    renderer_after = ET.tostring(next(
        item for item in ET.parse(result["qgs_path"]).findall("./projectlayers/maplayer")
        if item.findtext("datasource", "").endswith("|layername=site")
    ).find("renderer-v2"), encoding="unicode")
    return {
        "generated_artifact_provenance": {"source": "fieldbuild_generation_path",
            "materialized_source_path": str(source), "generated_project_path": result["qgs_path"],
            "generated_gpkg_path": result["gpkg_path"]},
        "labeling": {"field": name_field, "buffer_color": color(buffer.get("bufferColor")),
            "buffer_enabled": buffer.get("bufferDraw") == "1", "buffer_width": float(buffer.get("bufferSize"))},
        "rendered_labels": rendered_labels,
        "blank_label_artifacts": [label for label in rendered_labels if label["text"] == ""],
        "source_features_before": source_before, "source_features_after": read_source(),
        "source_renderer_contract_before": renderer_before,
        "source_renderer_contract_after": renderer_after,
        "basemap_renderings": renderings,
        "base_style": base,
        "completion_overlay_style": {"color": runtime_color(r'overlayColor:\s*"(#[0-9A-Fa-f]{6})"')},
        "route_line_style": {"color": runtime_color(r'id:\s*roadFactory.*?color:\s*"(#[0-9A-Fa-f]{6})"')},
        "start_marker_style": {"color": runtime_color(r'id:\s*startMarkerFactory.*?color:\s*"(#[0-9A-Fa-f]{6})"')},
    }


def _generated_site_label_contract(case, work):
    """Observe labeling written by the normal builder without modifying its artifacts."""
    import xml.etree.ElementTree as ET

    import fiona

    source = work / ("site-label-source-" + uuid.uuid4().hex[:8] + ".gpkg")
    name_field = case.get("name_field")
    stable_source_field = "stable_id"
    properties = {stable_source_field: "str"}
    if name_field:
        properties[name_field] = "str"
    with fiona.open(
        source,
        "w",
        driver="GPKG",
        layer="source_site",
        crs=case.get("crs", "EPSG:4326"),
        schema={"geometry": case["geometry_type"], "properties": properties},
    ) as target:
        for feature in case["features"]:
            values = {stable_source_field: feature["stable_id"]}
            if name_field:
                values[name_field] = feature["name"]
            target.write({"geometry": feature["geometry"], "properties": values})

    mapping = {"site_id": stable_source_field}
    if name_field:
        mapping["site_name"] = name_field
    route = {"id_field": case["stable_id_field"], "name_field": name_field}
    result = _build(
        work,
        sites_upload={
            "format": "gpkg",
            "path": str(source),
            "attribute_mapping": mapping,
        },
        survey_route=route,
        storage_crs=case.get("crs", "EPSG:4326"),
    )
    qgs_path = Path(result["qgs_path"])
    gpkg_path = Path(result["gpkg_path"])
    root = ET.parse(qgs_path).getroot()
    layer = next(
        item for item in root.findall("./projectlayers/maplayer")
        if item.findtext("datasource", "").endswith("|layername=site")
    )
    qgis_runtime = {
        "available": False,
        "probe_attempted": True,
        "runtime_claims": [],
    }
    qgis_app = None
    owns_qgis_app = False
    try:
        from qgis.core import (
            QgsApplication,
            QgsExpression,
            QgsExpressionContext,
            QgsExpressionContextUtils,
            QgsProject,
        )

        qgis_app = QgsApplication.instance()
        if qgis_app is None:
            qgis_app = QgsApplication([], False)
            qgis_app.initQgis()
            owns_qgis_app = True
        project = QgsProject()
        if not project.read(str(qgs_path)):
            raise RuntimeError("QgsProject could not load the generated project")
        qgis_layer = project.mapLayer(layer.findtext("id"))
        if qgis_layer is None:
            raise RuntimeError("generated site layer was not found by its QGIS layer ID")
        labeling = qgis_layer.labeling()
        if labeling is None:
            raise RuntimeError("generated site layer has no QGIS labeling configuration")
        settings = labeling.settings()
        expression = QgsExpression(settings.fieldName)
        context = QgsExpressionContext()
        context.appendScopes([
            QgsExpressionContextUtils.globalScope(),
            QgsExpressionContextUtils.projectScope(project),
            QgsExpressionContextUtils.layerScope(qgis_layer),
        ])
        evaluated_texts = []
        expression_errors = []
        for feature in qgis_layer.getFeatures():
            context.setFeature(feature)
            value = expression.evaluate(context)
            if expression.hasEvalError():
                expression_errors.append(expression.evalErrorString())
            elif value is not None and str(value) != "":
                evaluated_texts.append(str(value))
        placement = getattr(settings.placement, "value", settings.placement)
        text_format = settings.format()
        qgis_runtime.update({
            "available": True,
            "api_source": "QgsProject/QgsPalLayerSettings/QgsExpression",
            "project_loaded": True,
            "labeling_enabled": bool(qgis_layer.labelsEnabled()),
            "expression": settings.fieldName,
            "placement": str(int(placement)),
            "buffer_enabled": bool(text_format.buffer().enabled()),
            "buffer_color": text_format.buffer().color().name().upper(),
            "label_per_part": bool(settings.labelPerPart),
            "merge_lines": bool(settings.mergeLines),
            "expression_evaluator": "QgsExpression",
            "expression_errors": expression_errors,
            "evaluated_texts": evaluated_texts,
            "runtime_claims": ["generated_project_label_configuration_and_expression_evaluation"],
            "diagnostic": "",
        })
        project.clear()
    except Exception as exc:
        qgis_runtime["diagnostic"] = f"{type(exc).__name__}: {exc}"
    finally:
        if owns_qgis_app and qgis_app is not None:
            qgis_app.exitQgis()

    return {
        "generated_artifact_provenance": {
            "source": "normal_fieldbuild_generation_path",
            "materialized_source_path": str(source),
            "generated_project_path": str(qgs_path),
            "generated_gpkg_path": str(gpkg_path),
            "generated_layer_id": layer.findtext("id"),
            "generated_layer_name": "site",
            "artifact_post_edits": [],
            "fixture_injected_after_build": False,
            "final_qgs_sha256": hashlib.sha256(qgs_path.read_bytes()).hexdigest(),
            "final_gpkg_sha256": hashlib.sha256(gpkg_path.read_bytes()).hexdigest(),
        },
        "expression_proxy": {},
        "qgis_runtime": qgis_runtime,
        "claims": {},
        "evidence_scope": "generated_qgs_gpkg_proxy_not_qfield_canvas",
    }


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
    from PySide6.QtGui import QAccessible
    from PySide6.QtWidgets import QApplication, QLineEdit, QWidget
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
        widgets = [
            ("route_key", page.route_api_key_edit),
            ("route_key_purpose", page.route_key_purpose_label),
            ("route_key_blank_behavior", page.route_key_blank_behavior_label),
            ("route_key_plaintext_warning", page.route_key_warning_label),
            ("route_key_consent", page.route_key_consent_checkbox),
            ("route_key_remember", page.route_key_remember_checkbox),
        ]
        widget_ids = {id(widget): semantic_id for semantic_id, widget in widgets}

        def layout_path(widget):
            parts = []
            current = widget
            while current is not None and current is not page:
                parent = current.parentWidget()
                if parent is None:
                    break
                layout = parent.layout()
                index = layout.indexOf(current) if layout is not None else -1
                parts.append(f"{parent.metaObject().className()}[{index:04d}]")
                current = parent
            return "/".join(reversed(parts))

        widget_tree_ids = [
            widget_ids[id(widget)]
            for widget in page.findChildren(QWidget)
            if id(widget) in widget_ids
        ]
        focus_chain_ids = []
        current = page.route_api_key_edit
        for _ in range(256):
            semantic_id = widget_ids.get(id(current))
            if semantic_id and semantic_id not in focus_chain_ids:
                focus_chain_ids.append(semantic_id)
            current = current.nextInFocusChain()
            if current is page.route_api_key_edit:
                break
        observed_widgets = []
        for semantic_id, widget in widgets:
            text = widget.text() if hasattr(widget, "text") else ""
            interface = QAccessible.queryAccessibleInterface(widget)
            if interface is None:
                accessibility = {
                    "available": False,
                    "diagnostic": (
                        "QAccessible.queryAccessibleInterface returned no interface for "
                        + widget.metaObject().className()
                    ),
                }
            else:
                accessibility = {
                    "available": True,
                    "source": "QAccessible.queryAccessibleInterface",
                    "name": interface.text(QAccessible.Name),
                    "role": interface.role().name,
                }
            observed_widgets.append({
                "semantic_id": semantic_id,
                "title": page.route_key_group.title() if semantic_id == "route_key" else "",
                "text": text,
                "echo_mode": (
                    "password"
                    if semantic_id == "route_key"
                    and widget.echoMode() == QLineEdit.EchoMode.Password
                    else None
                ),
                "word_wrap": bool(widget.wordWrap()) if hasattr(widget, "wordWrap") else False,
                "visible": not widget.isHidden(),
                "layout_observation_source": "actual_parent_layout",
                "layout_path": layout_path(widget),
                "accessibility_observation": accessibility,
                "described_as_project_delivery": (
                    "프로젝트에" in text and "평문" in text
                    if semantic_id == "route_key_remember" else None
                ),
            })
        artifact_paths = sorted(
            str(path) for path in project_dir.rglob("*") if path.is_file()
        ) if published else []
        project_key_occurrences = (
            qgs_path.read_text(encoding="utf-8").count(key) if key and qgs_path.is_file() else 0
        )
        safe_fields = {
            "summary": page.summary_view.toPlainText(),
            "logs": result["logs"],
            "errors": result["errors"],
            "general_settings": general_settings,
            "diagnostics": {"reports": result["reports"], "message": result["message"]},
        }
        result.update({
            "step": 7,
            "build_success": published,
            "widgets": observed_widgets,
            "widget_tree_observation": {
                "source": "actual_qt_widget_tree",
                "semantic_ids": widget_tree_ids,
            },
            "focus_chain_observation": {
                "source": "QWidget.nextInFocusChain",
                "semantic_ids": [
                    semantic_id for semantic_id in focus_chain_ids
                    if semantic_id in {"route_key", "route_key_consent", "route_key_remember"}
                ],
            },
            "generated_project_variable_count": int("fieldbuild_route_api_key" in variables),
            "review_plaintext_warning_visible": bool(
                key and case.get("consent") and not page.route_key_warning_label.isHidden()
            ),
            "qfield_session_key_guidance_visible": bool(
                "fieldbuild_route_api_key" not in variables
                and not page.route_key_blank_behavior_label.isHidden()
            ),
            "summary": safe_fields["summary"],
            "diagnostics": safe_fields["diagnostics"],
            "artifact_paths": artifact_paths,
            "project_variable_occurrences": project_key_occurrences,
            "test_output_secret_redacted": not key or key not in json.dumps(
                safe_fields, ensure_ascii=False
            ),
        })
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
    if op in {"builder_route_key", "builder_step7_route_credentials"}:
        return _builder_route_key(case, work)
    if op == "settings_key_provenance":
        result = _build(work, **({"survey_route": {"api_key": case["key"], "consent_accepted": True}}
                                if case["key_source"] == "consented_project_variable" else {}))
        return _node(case, result["project_dir"])
    if op == "generated_site_style":
        return _generated_site_style(case, work)
    if op == "generated_site_label_contract":
        return _generated_site_label_contract(case, work)
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
        route_result=run(case={**case,"operation":"generated_geometry_calculate"},work_dir=work_dir)
        coordinate=route_result["request_coordinate"]
        return {**route_result,"coordinate":coordinate}
    if op == "generate_plugin":
        result = _build(work, identification_enabled=True)
        observed = _qml_probe(result, work)
        observed["project_dir"] = result["project_dir"]
        observed["loaded_features"] = set(observed.get("loaded_features", []))
        observed["asset_paths"] = [str(p.relative_to(result["project_dir"])) for p in Path(result["project_dir"]).rglob("*") if p.is_file() and p.suffix in (".qml", ".js", ".svg")]
        return observed
    if op == "generated_geometry_calculate":
        if not case.get("wkt"):
            result = _build(work, sites=[{"site_id":"geometry-site", "site_name":"생성 조사지", "geom_wkt":"POINT(127.001 37.001)"}], site_geometry_type="POINT")
            gpkg = Path(result["gpkg_path"])
            before = gpkg.read_bytes()
            observed = _node(case, result["project_dir"])
            observed["original_before"] = before.hex()
            observed["original_after"] = gpkg.read_bytes().hex()
            return observed
        import fiona
        source = work / ("generated-geometry-source-" + uuid.uuid4().hex[:8] + ".gpkg")
        shape = _geojson(case["wkt"])
        target_id = str(case.get("target_id", "geometry-site"))
        with fiona.open(source, "w", driver="GPKG", crs=case["crs"],
                        schema={"geometry": shape["type"], "properties": {"site_id": "str", "site_name": "str"}}) as dst:
            dst.write({"geometry": shape, "properties": {"site_id": target_id, "site_name": "생성 경로 대상"}})
        result = _build(work, sites_upload={"format": "gpkg", "path": str(source),
            "attribute_mapping": {"site_id": "site_id", "site_name": "site_name"}}, storage_crs="EPSG:4326")
        gpkg = Path(result["gpkg_path"])
        before = gpkg.read_bytes()
        observed = _node(case, result["project_dir"])
        observed["original_before"] = before.hex()
        observed["original_after"] = gpkg.read_bytes().hex()
        observed["generated_geometry_provenance"].update({
            "materialized_source_path": str(source), "generated_gpkg_path": str(gpkg),
            "generated_project_path": str(result["qgs_path"]), "generated_layer_name": "site",
            "supplied_wkt_sha256": hashlib.sha256(case["wkt"].encode()).hexdigest(),
            "supplied_crs": case["crs"],
        })
        return observed
    if op == "regression":
        return _regression(case, work)
    result = _build(work, survey_type=case.get("survey_type", "temporary_plots"))
    if op == "panel_layout" and case.get("stored_mapping") and "layers" not in case:
        # Materialize the persisted fixture identity in the project, including tree/relation refs.
        import xml.etree.ElementTree as ET
        project = Path(result["qgs_path"])
        site = next(layer for layer in ET.parse(project).findall("./projectlayers/maplayer")
                    if layer.findtext("datasource", "").endswith("|layername=site"))
        project.write_text(project.read_text(encoding="utf8").replace(
            site.findtext("id"), case["stored_mapping"]["layer_id"]), encoding="utf8")
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
