"""Real, PyQGIS-backed regression test for minimalist default point/polygon symbology and the
Tabler-icon SVG-marker mechanism (FR-QPB-120/FR-QPB-121; AC-QPB-100/AC-QPB-101/AC-QPB-104;
Decision Log D-61/D-65).

Exercises the real PyQGIS-calling pipeline end-to-end (`qfield_builder.gpkg.build_geopackage` +
`qfield_builder.qgis_worker.build_qgis_project`) and reads the renderer/symbol back via
`qfield_builder.layer_renderer_inspect.inspect_layer_renderer`, mirroring the existing convention
in `test_qgis_worker_field_aliases.py` (skipped when no real, bridgeable QGIS/PyQGIS runtime is
available on this machine). The acceptance suite's `test_symbol_styling.py` is the authoritative,
exhaustive coverage of this same behavior; this file is a smaller, implementation-level
regression check colocated with this codebase's other `qgis_worker` unit tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfield_builder import gpkg, layer_renderer_inspect, naming, qgis_bridge, qgis_worker, schemas
from qfield_builder.runtime import check_runtime

_QGIS_AVAILABLE = check_runtime()["available"]

pytestmark = pytest.mark.skipif(
    not _QGIS_AVAILABLE, reason="requires a real, bridgeable QGIS installation"
)

# Mirrors tests/acceptance/qfield_project_builder/test_symbol_styling.py's own POINT_LAYERS_BY_TYPE
# / MINIMALIST_POLYGON_LAYERS_BY_TYPE tables (Section 8) -- kept in sync deliberately, not
# imported, since that acceptance file must never be imported from implementation-level tests.
POINT_LAYERS_BY_TYPE: dict[str, list[str]] = {
    "simple_inventory": ["inventory_observation"],
    "temporary_plots": ["survey"],
    "permanent_plots": ["plot"],
    "vegetation_mapping": [],
}
MINIMALIST_POLYGON_LAYERS_BY_TYPE: dict[str, list[str]] = {
    "simple_inventory": [],
    "temporary_plots": ["site"],
    "permanent_plots": ["site"],
    "vegetation_mapping": ["site"],
}

SITE_OUTLINE_TYPES = ("temporary_plots", "permanent_plots", "vegetation_mapping")


def _build_project(tmp_path: Path, survey_type: str, svg_relative_path: str | None = None) -> str:
    gpkg_path = tmp_path / f"{survey_type}.gpkg"
    qgs_path = tmp_path / f"{survey_type}.qgs"
    gpkg.build_geopackage(
        str(gpkg_path),
        survey_type,
        naming.new_project_id(),
        seed_sites=[],
        seed_plots=[],
        seed_temporary_plot_points=[],
    )
    qgis_worker.build_qgis_project(
        gpkg_path=str(gpkg_path),
        qgs_path=str(qgs_path),
        survey_type=survey_type,
        project_crs="EPSG:4326",
        basemap_config=None,
        svg_relative_path=svg_relative_path,
    )
    return str(tmp_path)


@pytest.mark.parametrize(
    "survey_type,layer_name",
    [(t, layer) for t, layers in POINT_LAYERS_BY_TYPE.items() for layer in layers],
)
def test_point_layer_gets_minimalist_single_symbol_circle_marker(
    tmp_path: Path, survey_type: str, layer_name: str
):
    project_dir = _build_project(tmp_path, survey_type)
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, layer_name)

    assert info["renderer_class"] == "QgsSingleSymbolRenderer"
    assert "SimpleMarker" in info["symbol_layer_types"]
    assert info["marker_shape"] == "circle"
    assert info["svg_relative_path"] is None


@pytest.mark.parametrize(
    "survey_type,layer_name",
    [(t, layer) for t, layers in MINIMALIST_POLYGON_LAYERS_BY_TYPE.items() for layer in layers],
)
def test_polygon_layer_gets_minimalist_single_symbol_fill(
    tmp_path: Path, survey_type: str, layer_name: str
):
    project_dir = _build_project(tmp_path, survey_type)
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, layer_name)

    assert info["renderer_class"] == "QgsSingleSymbolRenderer"
    assert "SimpleFill" in info["symbol_layer_types"]


@pytest.mark.parametrize("survey_type", SITE_OUTLINE_TYPES)
def test_site_layer_uses_outline_only_symbology(tmp_path: Path, survey_type: str):
    project_dir = _build_project(tmp_path, survey_type)
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, "site")

    assert info["renderer_class"] == "QgsSingleSymbolRenderer"
    assert info["symbol_layer_types"] == ["SimpleFill"]
    assert info["fill_style"] == "no"


def test_type4_community_enables_vertex_snapping_avoids_overlap_and_uses_70_percent_opacity(
    tmp_path: Path,
):
    project_dir = _build_project(tmp_path, "vegetation_mapping")
    qgs_path = Path(project_dir) / "vegetation_mapping.qgs"
    script_path = tmp_path / "inspect-community-digitizing.py"
    script_path.write_text(
        f"""
import json
from qgis.core import Qgis, QgsProject

project = QgsProject()
assert project.read({str(qgs_path)!r})
community = next(layer for layer in project.mapLayers().values() if layer.name() == "군락")
site = next(layer for layer in project.mapLayers().values() if layer.name() == "조사지")
snapping = project.snappingConfig()
settings = snapping.individualLayerSettings(community)
site_settings = snapping.individualLayerSettings(site)
print(json.dumps({{
    "enabled": snapping.enabled(),
    "mode": int(snapping.mode()),
    "vertex": int(settings.typeFlag()) == int(Qgis.SnappingType.Vertex),
    "site_vertex": int(site_settings.typeFlag()) == int(Qgis.SnappingType.Vertex),
    "tolerance": settings.tolerance(),
    "avoid_mode": int(project.avoidIntersectionsMode()),
    "avoid_layers": [layer.id() for layer in project.avoidIntersectionsLayers()],
    "community_id": community.id(),
    "opacity": community.opacity(),
}}))
""",
        encoding="utf-8",
    )
    outcome = qgis_bridge.run_ad_hoc_script(str(script_path), timeout=60)
    assert outcome and outcome["ok"], outcome
    result = json.loads(outcome["stdout"])
    assert result["enabled"] is True
    assert result["mode"] == 3  # Qgis.SnappingMode.AdvancedConfiguration
    assert result["vertex"] is True
    assert result["site_vertex"] is True
    assert result["tolerance"] == pytest.approx(20.0)
    assert result["avoid_mode"] == 2  # Qgis.AvoidIntersectionsMode.AvoidIntersectionsLayers
    assert result["avoid_layers"] == [result["community_id"]]
    assert result["opacity"] == pytest.approx(0.70)


def test_community_layer_is_unaffected_by_minimalist_styling(tmp_path: Path):
    project_dir = _build_project(tmp_path, "vegetation_mapping")
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, "community")

    assert info["renderer_class"] == "QgsRuleBasedRenderer"
    assert info["renderer_class"] != "QgsSingleSymbolRenderer"


def test_non_geometry_tables_have_no_renderer_configured(tmp_path: Path):
    """FR-QPB-120 only applies to point/polygon layers -- `_apply_symbol_styling` deliberately
    skips any table whose `schemas.TableDef.geometry` is `None` (e.g. `observation` in Types
    2/3). Confirmed empirically (see this round's implementer completion report): a non-spatial
    `QgsVectorLayer` genuinely has no renderer at all (`layer.renderer() is None`), unlike a
    spatial layer, which QGIS always assigns some default renderer to on creation -- this is not
    a crash/lookup-failure case, it is the real, expected shape for this specific table."""
    project_dir = _build_project(tmp_path, "temporary_plots")
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, "observation")
    assert info["renderer_class"] == ""
    assert info["symbol_layer_types"] == []


def test_svg_relative_path_is_applied_to_every_point_layer_when_given(tmp_path: Path):
    """FR-QPB-121/AC-QPB-101/AC-QPB-104: when a Tabler icon has already been fetched and embedded
    (the `svg_relative_path` this function receives), every point layer of the project uses it as
    its marker symbol -- never a mix of some point layers using it and others still on the
    minimalist default."""
    svg_dir = tmp_path / "symbols"
    svg_dir.mkdir()
    (svg_dir / "map-pin.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>', encoding="utf-8"
    )

    project_dir = _build_project(
        tmp_path, "simple_inventory", svg_relative_path="symbols/map-pin.svg"
    )
    info = layer_renderer_inspect.inspect_layer_renderer(project_dir, "inventory_observation")

    assert info["renderer_class"] == "QgsSingleSymbolRenderer"
    assert "SvgMarker" in info["symbol_layer_types"]
    assert "SimpleMarker" not in info["symbol_layer_types"]
    assert info["svg_relative_path"] == "symbols/map-pin.svg"


def test_svg_relative_path_survives_moving_the_whole_project_folder(tmp_path: Path):
    """FR-QPB-091/DR-QPB-012/FR-QPB-121: the embedded SVG must be referenced by a genuinely
    project-relative path, resolvable correctly even after the whole project folder is moved to a
    different location -- not a path baked in absolute at generation time."""
    import shutil

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    svg_dir = build_dir / "symbols"
    svg_dir.mkdir()
    (svg_dir / "leaf.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>', encoding="utf-8"
    )
    _build_project(build_dir, "simple_inventory", svg_relative_path="symbols/leaf.svg")
    # (`_build_project`'s own `tmp_path` parameter name is just "the directory to build into" --
    # `build_dir` here is not pytest's own `tmp_path` fixture, only this test's outer one is.)

    moved_dir = tmp_path / "moved"
    shutil.move(str(build_dir), str(moved_dir))

    info = layer_renderer_inspect.inspect_layer_renderer(str(moved_dir), "inventory_observation")
    assert info["svg_relative_path"] == "symbols/leaf.svg"
    resolved = moved_dir / info["svg_relative_path"]
    assert resolved.is_file()


@pytest.mark.parametrize("survey_type", schemas.SURVEY_TYPES)
def test_every_survey_type_builds_without_a_symbology_error(tmp_path: Path, survey_type: str):
    """A broad smoke check: every survey type's own generated project builds successfully with
    the new symbol-styling step wired in (no crash from an unexpected schema shape)."""
    project_dir = _build_project(tmp_path, survey_type)
    assert (Path(project_dir) / f"{survey_type}.qgs").is_file()
