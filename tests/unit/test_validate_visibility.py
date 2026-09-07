"""Fail-closed unit coverage for live layer-tree visibility validation."""
from __future__ import annotations

from pathlib import Path

from qfield_builder import qgis_bridge, validate


class _Node:
    def __init__(self, *, layer_id=None, checked=True, children=None):
        self._layer_id = layer_id
        self._checked = checked
        self._children = list(children or [])

    def layerId(self):
        return self._layer_id

    def children(self):
        return self._children

    def itemVisibilityChecked(self):
        return self._checked


class _Root:
    def __init__(self, groups):
        self._groups = groups

    def findGroup(self, name):
        return self._groups.get(name)


class _Project:
    def __init__(self, map_layers, groups):
        self._map_layers = map_layers
        self._root = _Root(groups)

    def mapLayers(self):
        return self._map_layers

    def layerTreeRoot(self):
        return self._root


def _groups(*, checked=True, node_checked=True):
    return {
        name: _Node(
            checked=checked,
            children=[_Node(layer_id=f"{name}-layer", checked=node_checked)],
        )
        for name in ("Survey data", "Reference", "Basemap")
    }


def test_empty_map_layers_still_checks_required_groups_and_fails_closed():
    project = _Project({}, {})

    issues = validate._layer_tree_visibility_issues(project)
    codes = [issue["code"] for issue in issues]

    assert "layer_tree_visibility_unverified" in codes
    assert codes.count("layer_tree_group_missing") == 3


def test_visibility_verification_rejects_truthy_string_values():
    project = _Project({"Survey data-layer": object()}, _groups(node_checked="false"))

    issues = validate._layer_tree_visibility_issues(project)

    assert any(issue["code"] == "layer_tree_node_unchecked" for issue in issues)


def test_visibility_verification_accepts_only_real_true_boolean():
    visible = _Project({"Survey data-layer": object()}, _groups(node_checked=True))
    truthy_object = _Project({"Survey data-layer": object()}, _groups(node_checked=object()))

    assert not any(
        issue["code"] == "layer_tree_node_unchecked"
        for issue in validate._layer_tree_visibility_issues(visible)
    )
    assert any(
        issue["code"] == "layer_tree_node_unchecked"
        for issue in validate._layer_tree_visibility_issues(truthy_object)
    )


def test_empty_project_is_rejected_by_standalone_structure_validation(tmp_path, monkeypatch):
    qgs_path = Path(tmp_path) / "project.qgs"
    qgs_path.write_text("<qgis/>", encoding="utf-8")
    monkeypatch.setattr(validate, "_open_with_pyqgis_direct", lambda _path: None)
    monkeypatch.setattr(qgis_bridge, "run_job", lambda *_args, **_kwargs: None)

    opened_ok, missing_layer, warnings = validate._open_with_pyqgis(str(qgs_path))

    assert opened_ok is False
    assert missing_layer is False
    assert warnings[0]["code"] == "project_structure_invalid"
