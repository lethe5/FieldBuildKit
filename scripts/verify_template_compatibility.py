"""Developer-only QGIS read-back of standalone test outputs.

Run via qgis_isolated_probe.py with QPB_STANDALONE_TEST_ROOT pointing to the
pytest --basetemp directory from tests/unit/test_standalone.py.
"""

from __future__ import annotations

import os
from pathlib import Path

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

root = Path(os.environ["QPB_STANDALONE_TEST_ROOT"])
projects = sorted({path.resolve() for path in root.glob("*/moved folder 한글/*.qgs")})
assert len(projects) == 24, f"Expected 24 generated projects, got {len(projects)}"
for path in projects:
    project = QgsProject()
    assert project.read(str(path)), path
    for layer in project.mapLayers().values():
        assert layer.isValid(), (path, layer.name())
        if isinstance(layer, QgsVectorLayer):
            for field in layer.fields():
                widget = layer.editorWidgetSetup(layer.fields().indexFromName(field.name()))
                if widget.type() == "ValueRelation":
                    assert project.mapLayer(widget.config()["Layer"]) is not None
            if layer.isSpatial():
                assert layer.renderer() is not None, (path, layer.name(), "missing renderer")
        if isinstance(layer, QgsRasterLayer):
            assert layer.renderer() is not None, (path, layer.name(), "missing raster renderer")
    for relation in project.relationManager().relations().values():
        assert relation.isValid(), (path, relation.name())
    variables = project.customVariables()
    if "qpb_plantnet_api_key" in variables:
        assert variables["qpb_plantnet_api_key"] == "plant<&\"'key"
    project.clear()
print(f"QGIS read-back: {len(projects)} projects; all layers, relations and renderers valid.")
