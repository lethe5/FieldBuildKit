"""Shared layer-lookup helpers for the real-PyQGIS-backed acceptance-harness inspection functions
(`qfield_builder.field_alias_inspect`, `qfield_builder.editor_widget_inspect`,
`qfield_builder.layer_renderer_inspect`, `qfield_builder.layer_names_inspect`).

**Why this module exists (DR-QPB-078/FR-QPB-130; Decision Log D-80/D-84).** Before that
requirement existed, a generated layer's own `QgsMapLayer.name()` and its underlying GeoPackage
table name were always the identical string (`QgsVectorLayer(uri, table_name, "ogr")`'s third
constructor argument, never overridden), so every one of the pre-existing PyQGIS-backed harness
functions above safely located a target layer via a plain `lyr.name() == some_table_name` scan.
DR-QPB-078/FR-QPB-130 (Section 8.7) breaks that assumption: a domain layer's own `.name()` is now
its Section 8.7-confirmed Korean display text, never again equal to the raw table name every
existing acceptance-test call site still (correctly) passes as the lookup key. Every one of those
functions must therefore resolve a target layer by its underlying table name instead, parsed from
the layer's own OGR data source -- the same connection-string convention
`qfield_builder.qgis_worker._add_domain_layers`/`_add_ktsn_lookup_layer` construct verbatim when
first loading a layer: `uri = f"{gpkg_path}|layername={table_name}"`. This module factors that
parsing logic (and the "find the layer with this table name" scan built on top of it) into one
place, shared by every function that needs it, rather than duplicating it four times.
"""
from __future__ import annotations

_LAYERNAME_PARAM = "layername="


def table_name_from_layer(layer) -> str | None:
    """Returns the GeoPackage table name embedded in `layer`'s own OGR data-source URI/connection
    string (`<gpkg_path>|layername=<table_name>`), or `None` if `layer`'s own source has no
    `layername=` component at all -- in particular, a WMTS/XYZ/raster basemap layer, which is
    never GeoPackage-table-backed, or any other non-OGR-GeoPackage layer.
    """
    if layer is None:
        return None
    source = layer.source() or ""
    for part in source.split("|"):
        part = part.strip()
        if part.startswith(_LAYERNAME_PARAM):
            return part[len(_LAYERNAME_PARAM):]
    return None


def find_layer_by_table_name(project, table_name: str):
    """Locates the map layer on `project` whose own underlying GeoPackage table name (per
    `table_name_from_layer` above) equals `table_name`. Returns `None` if no such layer exists.

    This is the stable, requirement-proof replacement for the pre-existing
    `for lyr in project.mapLayers().values(): if lyr.name() == layer_name: ...` pattern -- see
    this module's own docstring for why that pattern stopped being safe once DR-QPB-078/FR-QPB-130
    shipped.
    """
    for lyr in project.mapLayers().values():
        if table_name_from_layer(lyr) == table_name:
            return lyr
    return None
