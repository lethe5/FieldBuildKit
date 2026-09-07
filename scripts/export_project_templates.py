"""Developer-only: run through scripts/qgis_isolated_probe.py --code THIS_FILE.

Export QGIS-authored forms/relations/styles, with no user data or credentials.
QGIS is needed to refresh these assets, never to run the standalone application.
"""

from __future__ import annotations

import copy
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from qgis.core import QgsProject

from qfield_builder import gpkg, qgis_worker, schemas
from qfield_builder.resource_paths import repo_or_bundle_root


def export():
    destination = repo_or_bundle_root() / "qfield_builder" / "templates"
    destination.mkdir(exist_ok=True)
    manifest = {"schema_revision": 1, "survey_types": list(schemas.SURVEY_TYPES)}
    with tempfile.TemporaryDirectory(prefix="qpb-template-export-") as work:
        root = Path(work)
        for survey_type in schemas.SURVEY_TYPES:
            data = root / survey_type / "data" / "template.gpkg"
            qgs = data.parent.parent / "template.qgs"
            gpkg.build_geopackage(str(data), survey_type, "template")
            gpkg.add_ktsn_lookup_table(str(data), "ktsn_lookup", [])
            gpkg.add_ktsn_taxonomy_reference_table(str(data), "ktsn_taxonomy_reference", [])
            qgis_worker._build_qgis_project_pyqgis(
                gpkg_path=str(data),
                qgs_path=str(qgs),
                survey_type=survey_type,
                project_crs="EPSG:5186",
                basemap_config=None,
                identification_enabled=True,
                ktsn_lookup_table_name="ktsn_lookup",
                ktsn_taxonomy_table_name="ktsn_taxonomy_reference",
            )
            tree = ET.parse(qgs)
            for key in ("saveUser", "saveUserFull", "saveDateTime"):
                tree.getroot().attrib.pop(key, None)
            for path in (
                "./projectMetadata/author",
                "./projectMetadata/creation",
                "./projectMetadata/dates",
            ):
                element = tree.find(path)
                if element is not None:
                    element.clear()
            for element in tree.iter("attributeEditorQmlElement"):
                element.text = ""
                for child in element:
                    child.tail = ""
            tree.write(destination / f"{survey_type}.qgs", encoding="utf-8", xml_declaration=True)
            print(f"Exported {survey_type}")

        # Save QGIS's own raster and SVG serialization as small reusable fragments.
        project = QgsProject.instance()
        pyqgis = qgis_worker._import_pyqgis()
        from osgeo import gdal

        raster_path = qgs.parent / "probability.tif"
        raster = gdal.GetDriverByName("GTiff").Create(str(raster_path), 2, 2, 1, gdal.GDT_Float32)
        raster.SetGeoTransform((127, 0.01, 0, 37.02, 0, -0.01))
        raster.SetProjection(pyqgis["QgsCoordinateReferenceSystem"]("EPSG:4326").toWkt())
        raster.GetRasterBand(1).Fill(0.5)
        raster.GetRasterBand(1).SetNoDataValue(-9999)
        raster = None
        probability = qgis_worker._add_probability_raster_layer(
            pyqgis, project, str(qgs), "probability.tif"
        )
        qgis_worker._add_online_basemap_layer(
            pyqgis,
            project,
            {
                "consent_accepted": True,
                "vworld_api_key": "TEMPLATE_KEY",
                "layer": "Base",
            },
        )
        qgis_worker._add_offline_basemap_layer(
            pyqgis, project, "./basemap/offline.mbtiles", {"provider": "VWorld", "layer": "Base"}
        )
        project.write(str(qgs))
        tree = ET.parse(qgs)
        for mode, provider in (("online", "wms"), ("offline", "gdal"), ("probability", "gdal")):
            layer = next(
                e
                for e in tree.findall("./projectlayers/maplayer")
                if e.findtext("provider") == provider
                and ((e.findtext("id") == probability.id()) == (mode == "probability"))
            )
            fragment = ET.Element("fragment")
            fragment.append(copy.deepcopy(layer))
            node = next(
                e
                for e in tree.findall(".//layer-tree-layer")
                if e.get("id") == layer.findtext("id")
            )
            fragment.append(copy.deepcopy(node))
            ET.ElementTree(fragment).write(destination / f"{mode}.xml", encoding="utf-8")
        # An SVG renderer from a real point layer, with the same defaults as main.
        point_data = root / "simple_inventory" / "data" / "template.gpkg"
        point = pyqgis["QgsVectorLayer"](
            f"{point_data}|layername=inventory_observation", "point", "ogr"
        )
        qgis_worker._apply_svg_point_symbology(pyqgis, point, "symbols/template.svg")
        project.addMapLayer(point)
        project.write(str(qgs))
        layer = next(
            e
            for e in ET.parse(qgs).findall("./projectlayers/maplayer")
            if e.findtext("id") == point.id()
        )
        ET.ElementTree(layer.find("renderer-v2")).write(destination / "svg.xml", encoding="utf-8")
        project.clear()
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


export()
