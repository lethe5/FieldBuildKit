"""Create portable QField projects from QGIS-authored templates, without PyQGIS."""

from __future__ import annotations

import math
import sqlite3
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from contextlib import closing
from pathlib import Path

from rasterio.crs import CRS
from rasterio.warp import transform_bounds

from . import probability_raster, qml_plugin, schemas, vworld
from .form_expressions import (
    _authoritative_location_expression,
    _identification_photo_paths_expression,
)

TEMPLATES = Path(__file__).parent / "templates"


def _set_text(parent, path, value):
    element = parent.find(path)
    if element is None:
        element = ET.SubElement(parent, path)
    element.text = str(value)


def _set_crs(element, crs):
    crs = CRS.from_user_input(crs)
    element.clear()
    element.set("nativeFormat", "Wkt")
    authority = crs.to_authority()
    for key, value in {
        "wkt": crs.to_wkt(),
        "proj4": crs.to_proj4(),
        "srsid": "0",
        "srid": str(crs.to_epsg() or 0),
        "authid": ":".join(authority) if authority else "",
        "description": ":".join(authority) if authority else "Custom CRS",
        "projectionacronym": crs.to_dict().get("proj", ""),
        "ellipsoidacronym": "",
        "geographicflag": str(crs.is_geographic).lower(),
    }.items():
        _set_text(element, key, value)


def _remove_layer(root, layer):
    layer_id = layer.findtext("id")
    root.find("projectlayers").remove(layer)
    for parent in root.iter():
        for child in list(parent):
            if child.get("id") == layer_id:
                parent.remove(child)


def _set_initial_view(root, gpkg_path, schema, project_crs, offline_path=None):
    """Open on survey data (or offline coverage/Korea), never on worldwide XYZ bounds."""
    bounds = []
    with closing(sqlite3.connect(gpkg_path)) as conn:
        for table in schema.values():
            if table.geometry is None:
                continue
            # These indexes are populated by the GeoPackage builder, including uploaded sites.
            index = f"rtree_{table.name}_{table.geometry.column}"
            row = conn.execute(
                f'SELECT min(minx), min(miny), max(maxx), max(maxy) FROM "{index}"'
            ).fetchone()
            if row[0] is not None:
                bounds.append(transform_bounds(f"EPSG:{table.geometry.srs_id}", "EPSG:4326", *row))
    if not bounds and offline_path:
        import rasterio

        with rasterio.open(offline_path) as raster:
            bounds.append(transform_bounds(raster.crs, "EPSG:4326", *raster.bounds))
    if bounds:
        west, south = min(b[0] for b in bounds), min(b[1] for b in bounds)
        east, north = max(b[2] for b in bounds), max(b[3] for b in bounds)
        dx, dy = max((east - west) * 0.1, 0.001), max((north - south) * 0.1, 0.001)
        bounds = (west - dx, south - dy, east + dx, north + dy)
    else:
        bounds = (124.5, 33.0, 132.0, 39.0)
    extent = transform_bounds("EPSG:4326", project_crs, *bounds)
    if not all(math.isfinite(value) for value in extent):
        raise ValueError("선택한 프로젝트 좌표계로 초기 지도 범위를 변환할 수 없습니다.")
    coordinates = dict(zip(("xmin", "ymin", "xmax", "ymax"), map(str, extent), strict=True))
    settings = root.find("ProjectViewSettings")
    for name in ("DefaultViewExtent", "PresetFullExtent"):
        element = ET.SubElement(settings, name, coordinates)
        _set_crs(ET.SubElement(element, "spatialrefsys"), project_crs)
    # QField reads the named mapcanvas, while QGIS also uses ProjectViewSettings.
    canvas = ET.SubElement(root, "mapcanvas", {"name": "theMapCanvas"})
    rectangle = ET.SubElement(canvas, "extent")
    for name, value in coordinates.items():
        _set_text(rectangle, name, value)
    _set_text(canvas, "rotation", 0)
    destination = ET.SubElement(canvas, "destinationsrs")
    _set_crs(ET.SubElement(destination, "spatialrefsys"), project_crs)


def _add_raster(root, mode, source, name, group_name):
    fragment = ET.parse(TEMPLATES / f"{mode}.xml").getroot()
    layer, node = fragment.find("maplayer"), fragment.find("layer-tree-layer")
    _set_text(layer, "datasource", source)
    _set_text(layer, "layername", name)
    node.set("source", source)
    node.set("name", name)
    root.find("projectlayers").append(layer)
    group = root.find(f"./layer-tree-group/layer-tree-group[@name='{group_name}']")
    group.append(node)
    ET.SubElement(root.find("layerorder"), "layer", {"id": layer.findtext("id")})
    return layer


def _set_variables(root, variables):
    properties = root.find("properties")
    old = properties.find("Variables")
    if old is not None:
        properties.remove(old)
    container = ET.SubElement(properties, "Variables")
    names = ET.SubElement(container, "variableNames", {"type": "QStringList"})
    values = ET.SubElement(container, "variableValues", {"type": "QStringList"})
    for name, value in variables.items():
        ET.SubElement(names, "value").text = name
        ET.SubElement(values, "value").text = value


def build_qgis_project(
    gpkg_path: str,
    qgs_path: str,
    survey_type: str,
    project_crs: str,
    basemap_config: dict | None,
    mbtiles_relative_path: str | None = None,
    identification_enabled: bool = False,
    plantnet_config: dict | None = None,
    route_config: dict | None = None,
    svg_relative_path: str | None = None,
    ktsn_lookup_table_name: str | None = None,
    ktsn_taxonomy_table_name: str | None = None,
    offline_source_identity: dict | None = None,
    probability_raster_relative_path: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
) -> dict:
    with sqlite3.connect(gpkg_path) as geometry_db:
        site_row = geometry_db.execute("SELECT geometry_type_name FROM gpkg_geometry_columns WHERE table_name='site'").fetchone()
    geometry_db.close()
    site_kind = site_row[0] if site_row else "MULTIPOLYGON"
    schema = schemas.get_schema(survey_type, taxonomy_reference_available=bool(ktsn_lookup_table_name), site_geometry_type=site_kind)
    root = ET.parse(TEMPLATES / f"{survey_type}.qgs").getroot()
    project_dir = Path(qgs_path).parent.resolve()
    relative_data = "./" + Path(gpkg_path).resolve().relative_to(project_dir).as_posix()
    root.set("projectname", Path(qgs_path).stem)
    _set_text(root, "title", Path(qgs_path).stem)
    _set_crs(root.find("projectCrs/spatialrefsys"), project_crs)
    main_annotation_crs = root.find("main-annotation-layer/srs/spatialrefsys")
    if main_annotation_crs is not None:
        _set_crs(main_annotation_crs, project_crs)
    replacements = {"./data/template.gpkg": relative_data}
    for element in root.iter():
        if element.text:
            for old, new in replacements.items():
                element.text = element.text.replace(old, new)
        for key, value in element.attrib.items():
            for old, new in replacements.items():
                value = value.replace(old, new)
            element.set(key, value)
    layers = list(root.findall("./projectlayers/maplayer"))
    requested_site_name_field = str(
        (route_config.get("name_field") if route_config is not None else "site_name") or ""
    ).strip()
    requested_site_id_field = str(
        (route_config.get("id_field") if route_config is not None else "site_id") or ""
    ).strip()
    taxonomy_layer = next(
        e
        for e in layers
        if e.findtext("datasource", "").endswith("layername=ktsn_taxonomy_reference")
    )
    taxonomy_id = taxonomy_layer.findtext("id") if ktsn_taxonomy_table_name else None
    for layer in layers:
        table_name = layer.findtext("datasource", "").split("|layername=")[-1]
        if table_name == "site":
            with closing(sqlite3.connect(gpkg_path)) as connection:
                actual_fields = {row[1] for row in connection.execute('PRAGMA table_info("site")')}
            configured_fields = {field.get("name") for field in layer.findall("./fieldConfiguration/field")}
            for name in (
                requested_site_id_field,
                requested_site_name_field,
                "_fb_route_lon",
                "_fb_route_lat",
            ):
                if name and name in actual_fields and name not in configured_fields:
                    field = ET.SubElement(layer.find("fieldConfiguration"), "field", {"name": name})
                    ET.SubElement(field, "editWidget", {"type": "Hidden" if name.startswith("_fb_") else "TextEdit"})
        if not ktsn_lookup_table_name:
            for parent in layer.iter():
                for child in list(parent):
                    if child.get("name") == "selected_ktsn" or child.get("field") == "selected_ktsn":
                        parent.remove(child)
            # QGIS stores both names and positional indexes in form/table configuration.
            fields = [field.get("name") for field in layer.findall("./fieldConfiguration/field")]
            for element in layer.iter():
                name = element.get("field") or element.get("name")
                if name in fields:
                    for key in ("index", "idx"):
                        if key in element.attrib:
                            element.set(key, str(fields.index(name)))
            for widget in layer.findall(".//editWidget[@type='ValueRelation']"):
                widget.set("type", "TextEdit")
                for child in list(widget):
                    widget.remove(child)
            for field_name in ("selected_scientific_name", "selected_ktsn"):
                default = layer.find(f"./defaults/default[@field='{field_name}']")
                if default is not None:
                    default.set("expression", "")
                    default.set("applyOnUpdate", "0")
                editable = layer.find(f"./editable/field[@name='{field_name}']")
                if editable is not None:
                    editable.set("editable", "1")
        requested = {
            "ktsn_lookup": ktsn_lookup_table_name,
            "ktsn_taxonomy_reference": ktsn_taxonomy_table_name,
        }
        if table_name in requested:
            if not requested[table_name]:
                _remove_layer(root, layer)
                continue
            source = f"{relative_data}|layername={requested[table_name]}"
            _set_text(layer, "datasource", source)
            for node in root.iter("layer-tree-layer"):
                if node.get("id") == layer.findtext("id"):
                    node.set("source", source)
        for parent in layer.iter():
            for element in list(parent):
                if element.tag != "attributeEditorQmlElement":
                    continue
                if not identification_enabled:
                    parent.remove(element)
                else:
                    element.text = qml_plugin.render_identification_widget_qml(
                        _identification_photo_paths_expression(schema[table_name]),
                        immediate_identification=True,
                        layer_context=layer.findtext("layername"),
                        location_expression=_authoritative_location_expression(
                            survey_type, table_name, project_crs
                        ),
                        canonical_reference_enabled=bool(taxonomy_id),
                        taxonomy_reference_available=bool(ktsn_lookup_table_name),
                        canonical_layer_id=taxonomy_id,
                        canonical_runtime_lookup_resource=canonical_runtime_lookup_resource,
                        candidate_selection_enabled=table_name != "community",
                    )
        table = schema.get(table_name)
        if table_name == "site":
            family = site_kind.removeprefix("MULTI")
            layer.set("geometry", {"POINT": "Point", "LINESTRING": "Line", "POLYGON": "Polygon"}[family])
            _set_text(layer, "wkbType", {"POINT": "Point", "LINESTRING": "LineString", "POLYGON": "Polygon", "MULTIPOINT": "MultiPoint", "MULTILINESTRING": "MultiLineString", "MULTIPOLYGON": "MultiPolygon"}[site_kind])
            if family != "POLYGON":
                old = layer.find("renderer-v2")
                if old is not None: layer.remove(old)
                renderer = ET.SubElement(layer, "renderer-v2", {"type": "singleSymbol"})
                symbols = ET.SubElement(renderer, "symbols")
                symbol = ET.SubElement(symbols, "symbol", {"name": "0", "type": "marker" if family == "POINT" else "line", "alpha": "1"})
                symbol_layer = ET.SubElement(symbol, "layer", {"class": "SimpleMarker" if family == "POINT" else "SimpleLine", "enabled": "1"})
                options = ET.SubElement(symbol_layer, "Option", {"type": "Map"})
                for key, value in ({"name": "circle", "color": "44,117,183,255", "size": "3"} if family == "POINT" else {"line_color": "44,117,183,255", "line_width": "0.6"}).items():
                    ET.SubElement(options, "Option", {"name": key, "value": value, "type": "QString"})
            else:
                renderer = layer.find("renderer-v2")
                fill = renderer.find(".//layer[@class='SimpleFill']/Option[@type='Map']")
                for option in fill.findall("Option"):
                    if option.get("name") == "color":
                        option.set("value", "46,125,50,76,rgb:0.1803922,0.4901961,0.1960784,0.2980392")
                    elif option.get("name") == "outline_color":
                        option.set("value", "46,125,50,255,rgb:0.1803922,0.4901961,0.1960784,1")
                    elif option.get("name") == "style":
                        option.set("value", "solid")
                _set_text(layer, "layerOpacity", "1")
            old_labeling = layer.find("labeling")
            if old_labeling is not None:
                layer.remove(old_labeling)
            def field_ref(name):
                return '"' + name.replace('"', '""') + '"'

            label_fields = [
                name for name in (requested_site_name_field, requested_site_id_field)
                if name and name in actual_fields
            ]
            branches = [
                "WHEN trim(coalesce(to_string({field}), '')) <> '' "
                "THEN trim(to_string({field}))".format(field=field_ref(name))
                for name in label_fields
            ]
            expression = "CASE " + " ".join(branches) + " ELSE NULL END" if branches else "NULL"
            placement = {"POINT": "0", "LINESTRING": "2", "POLYGON": "4"}[family]
            labeling = ET.SubElement(layer, "labeling", {"type": "simple"})
            settings = ET.SubElement(labeling, "settings")
            text_style = ET.SubElement(settings, "text-style", {
                "fieldName": expression,
                "isExpression": "1",
                "fontFamily": "Sans Serif",
                "fontSize": "10",
                "fontSizeUnit": "Point",
                "fontWeight": "50",
                "opacity": "1",
                "textColor": "0,0,0,255",
            })
            ET.SubElement(text_style, "text-buffer", {
                "bufferDraw": "1", "bufferColor": "255,255,255,255", "bufferOpacity": "1",
                "bufferSize": "1", "bufferSizeUnits": "MM"
            })
            ET.SubElement(settings, "text-format", {"multilineAlign": "0", "wrapChar": ""})
            ET.SubElement(settings, "placement", {
                "placement": placement, "centroidInside": "1", "fitInPolygonOnly": "0"
            })
            ET.SubElement(settings, "rendering", {
                "drawLabels": "1", "displayAll": "0", "limitNumLabels": "0",
                "labelPerPart": "0", "mergeLines": "0",
            })
            layer.set("labelsEnabled", "1")
            _set_text(layer, "labelsEnabled", "1")
        if (
            svg_relative_path
            and table_name != "site"
            and table
            and table.geometry
            and table.geometry.geom_type == "POINT"
        ):
            renderer = ET.parse(TEMPLATES / "svg.xml").getroot()
            for option in renderer.iter("Option"):
                if option.get("name") == "name" and option.get("value") == "symbols/template.svg":
                    option.set("value", svg_relative_path)
            old = layer.find("renderer-v2")
            if old is not None:
                layer.remove(old)
            layer.append(renderer)

    basemap = basemap_config or {}
    _set_initial_view(
        root, gpkg_path, schema, project_crs,
        project_dir / mbtiles_relative_path
        if basemap.get("mode") == "offline" and mbtiles_relative_path else None,
    )
    online_key_embedded = False
    variables = {}
    if basemap.get("mode") == "online" and basemap.get("consent_accepted"):
        name = basemap.get("layer", "Base")
        url = vworld.build_gettile_url(
            basemap.get("vworld_api_key", ""), name, known_layers=basemap.get("known_vworld_layers")
        )
        _add_raster(
            root,
            "online",
            f"type=xyz&url={url}&zmin={6 if name == 'Satellite' else 0}&zmax=19",
            f"VWorld {name} (online)",
            "Basemap",
        )
        online_key_embedded = True
        key = str(basemap.get("vworld_api_key") or "").strip()
        if key:
            variables["qpb_vworld_api_key"] = key
    elif basemap.get("mode") == "offline" and mbtiles_relative_path:
        identity = offline_source_identity or basemap.get("offline_source_identity") or {}
        if not identity.get("provider") or not identity.get("layer"):
            raise ValueError("Offline basemap source identity is required.")
        layer = _add_raster(
            root, "offline", "./" + mbtiles_relative_path, "Offline basemap (MBTiles)", "Basemap"
        )
        for option in layer.findall("./customproperties/Option/Option"):
            for key in ("provider", "layer"):
                if option.get("name") == f"fieldbuildkit/{key}":
                    option.set("value", str(identity[key]))
        _set_text(
            layer,
            "abstract",
            f"{vworld.ATTRIBUTION_TEXT_EN} Source: {identity['provider']} / {identity['layer']}.",
        )
    if probability_raster_relative_path:
        import rasterio

        layer = _add_raster(
            root,
            "probability",
            "./" + probability_raster_relative_path,
            probability_raster.LAYER_NAME,
            "Reference",
        )
        with rasterio.open(project_dir / probability_raster_relative_path) as raster:
            _set_crs(layer.find("srs/spatialrefsys"), raster.crs)
            # Drop the export fixture's cached extent; QField reads the actual raster bounds.
            for extent in layer.findall("extent"):
                layer.remove(extent)
    plantnet_key_embedded = bool(plantnet_config and plantnet_config.get("consent_accepted"))
    if plantnet_key_embedded:
        variables["qpb_plantnet_api_key"] = str(plantnet_config.get("api_key") or "")
    route_key = str((route_config or {}).get("api_key") or "").strip()
    route_key_embedded = bool(route_key and (route_config or {}).get("consent_accepted"))
    if route_key_embedded:
        variables["fieldbuild_route_api_key"] = route_key
    _set_variables(root, variables)
    Path(qgs_path).parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(qgs_path, encoding="utf-8", xml_declaration=True)
    if route_key_embedded and "]]>" not in route_key:
        # QGIS accepts CDATA in QStringList values.  It also keeps the user's
        # explicit plaintext-project consent literal: readers can see the exact
        # key rather than only its XML entity representation.
        path = Path(qgs_path)
        document = path.read_text(encoding="utf-8")
        encoded = f"<value>{escape(route_key)}</value></variableValues>"
        document = document.replace(
            encoded, f"<value><![CDATA[{route_key}]]></value></variableValues>", 1
        )
        path.write_text(document, encoding="utf-8")
    return {
        "online_key_embedded": online_key_embedded,
        "vworld_key_saved": "qpb_vworld_api_key" in variables,
        "plantnet_key_embedded": plantnet_key_embedded,
        "route_key_embedded": route_key_embedded,
        "probability_raster_registration_count": int(bool(probability_raster_relative_path)),
    }


def inspect_project(qgs_path: str) -> tuple[bool, bool, list[dict]]:
    """Check local sources, table/field/relation references and layer visibility, without QGIS.

    This validates structure, not QField rendering or a real QgsProject.read().
    """
    issues = []

    def issue(code, message):
        issues.append({"code": code, "message": message})

    try:
        root = ET.parse(qgs_path).getroot()
        if root.tag != "qgis":
            raise ValueError("Expected a QGIS project document")
        layers = root.findall("./projectlayers/maplayer")
        if not layers:
            raise ValueError("Project contains no layers")
        ids = [layer.findtext("id") for layer in layers]
        if None in ids or len(set(ids)) != len(ids):
            raise ValueError("Missing or duplicate layer IDs")
        groups = root.findall("./layer-tree-group/layer-tree-group")
        for name in ("Survey data", "Reference", "Basemap"):
            group = next((g for g in groups if g.get("name") == name), None)
            if group is None:
                issue("layer_tree_group_missing", f"Missing group: {name}")
            elif group.get("checked") != "Qt::Checked":
                issue("layer_tree_group_unchecked", f"Unchecked group: {name}")
        fields = {}
        for layer in layers:
            layer_id = layer.findtext("id")
            nodes = root.findall(f"./layer-tree-group/.//layer-tree-layer[@id='{layer_id}']")
            hidden = (
                layer.find(
                    "./customproperties/Option/Option[@name='fieldbuildkit/probability_raster']"
                )
                is not None
            )
            if len(nodes) != 1:
                issue("layer_tree_node_missing", f"Missing/duplicate layer node: {layer_id}")
            elif nodes[0].get("checked") != "Qt::Checked" and not hidden:
                issue("layer_tree_node_unchecked", f"Unchecked layer: {layer_id}")
            source = layer.findtext("datasource", "")
            provider = layer.findtext("provider")
            if provider == "wms":
                if not source.startswith("type=xyz&url=https://"):
                    issue("invalid_layer_source", f"Unsupported online layer: {layer_id}")
                continue
            path = Path(qgs_path).parent / source.split("|", 1)[0]
            if not path.is_file():
                issue("missing_layer_source", f"Missing local source for {layer_id}")
                continue
            if provider == "ogr":
                table = source.split("|layername=")[-1]
                with closing(
                    sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
                ) as conn:
                    columns = {
                        row[1]
                        for row in conn.execute("SELECT * FROM pragma_table_info(?)", (table,))
                    }
                    fields[layer_id] = columns
                    if not columns:
                        issue("missing_layer_table", f"Missing table: {table}")
                    for field in layer.findall("./fieldConfiguration/field"):
                        if field.get("name") not in columns:
                            issue(
                                "missing_layer_field", f"Missing field: {table}.{field.get('name')}"
                            )
                    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        issue("invalid_geopackage", f"Invalid GeoPackage: {table}")
            elif provider == "gdal":
                import rasterio

                with rasterio.open(path) as dataset:
                    if not dataset.crs or dataset.count < 1:
                        issue("invalid_raster", f"Invalid raster: {layer_id}")
            else:
                issue("invalid_layer_source", f"Unsupported provider: {provider}")
        for relation in root.findall("./relations/relation"):
            for pair in relation.findall("fieldRef"):
                for side in ("referencing", "referenced"):
                    if pair.get(f"{side}Field") not in fields.get(
                        relation.get(f"{side}Layer"), set()
                    ):
                        issue("invalid_relation", f"Broken relation: {relation.get('id')}")
        for option in root.findall(".//editWidget[@type='ValueRelation']/config/Option/Option"):
            if option.get("name") == "Layer" and option.get("value") not in ids:
                issue("invalid_lookup", "ValueRelation refers to a missing layer")
    except (ET.ParseError, OSError, ValueError, sqlite3.Error) as exc:
        issue("project_structure_invalid", str(exc))
    return not issues, any(i["code"].startswith("missing_layer") for i in issues), issues
