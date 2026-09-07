"""Unit tests for the Bug 3 fix (FR-QPB-055 revised; Decision Log D-71; AC-QPB-110):
`Basemap` must end up last (highest children-index) of the three required root layer-tree groups,
so it renders beneath both `Survey data` and `Reference`.

`_add_reference_group`/`_add_basemap_group_after_survey_and_reference` only ever call
`project.layerTreeRoot().addGroup(...)` -- no other `qgis.*` API -- so this is exercised entirely
offline, with a minimal fake root/project recording `addGroup()` calls in their real call order
(mirroring a real `QgsLayerTreeGroup`'s own `children()` list order), matching this module's own
existing precedent (`test_qgis_worker_online_basemap.py`'s fake `_FakeLayerTreeRoot`/`_FakeProject`
for exercising `qgis_worker` functions without a real PyQGIS environment).
"""
from __future__ import annotations

from qfield_builder import qgis_worker


class _FakeLayerTreeGroup:
    def __init__(self, name):
        self.name = name
        self._checked = False

    def setItemVisibilityChecked(self, checked):
        self._checked = checked

    def itemVisibilityChecked(self):
        return self._checked


class _FakeLayerTreeRoot:
    def __init__(self):
        # The real `QgsLayerTreeGroup.children()` list order, in the order `addGroup()` was
        # actually called -- exactly what AC-QPB-110 reads from a real generated `.qgs` file.
        self.children_order: list[str] = []

    def addGroup(self, name):
        self.children_order.append(name)
        return _FakeLayerTreeGroup(name)

    def findGroup(self, name):
        return _FakeLayerTreeGroup(name) if name in self.children_order else None


class _FakeProject:
    def __init__(self):
        self._root = _FakeLayerTreeRoot()

    def layerTreeRoot(self):
        return self._root


def test_add_reference_group_creates_only_reference():
    """`_add_reference_group` must create "Reference" only -- "Basemap" is deliberately NOT
    created here (see `_add_basemap_group_after_survey_and_reference` below for why)."""
    project = _FakeProject()
    qgis_worker._add_reference_group(project)
    assert project.layerTreeRoot().children_order == ["Reference"]


def test_basemap_group_ends_up_last_when_added_after_survey_and_reference():
    """Mirrors `_build_qgis_project_pyqgis`'s own real call order: `_add_reference_group` (early,
    so the KTSN lookup layer can be loaded into "Reference"), then "Survey data" is created by
    `_add_domain_layers` (simulated here by a direct `addGroup("Survey data")` call, mirroring
    that function's own first statement), then `_add_basemap_group_after_survey_and_reference`."""
    project = _FakeProject()
    qgis_worker._add_reference_group(project)
    project.layerTreeRoot().addGroup("Survey data")
    qgis_worker._add_basemap_group_after_survey_and_reference(project)

    children = project.layerTreeRoot().children_order
    assert children == ["Reference", "Survey data", "Basemap"]

    basemap_index = children.index("Basemap")
    assert basemap_index > children.index("Survey data")
    assert basemap_index > children.index("Reference")


def test_basemap_group_is_findable_after_being_added():
    """`_add_online_basemap_layer`/`_add_offline_basemap_layer` locate "Basemap" via
    `findGroup("Basemap")` well after this call -- confirm it is still findable once added this
    way (not just present in the raw children-order list)."""
    project = _FakeProject()
    qgis_worker._add_reference_group(project)
    project.layerTreeRoot().addGroup("Survey data")
    qgis_worker._add_basemap_group_after_survey_and_reference(project)

    assert project.layerTreeRoot().findGroup("Basemap") is not None
