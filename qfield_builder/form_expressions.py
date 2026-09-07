"""QField form expressions shared by the template writer and development exporter."""

from __future__ import annotations

from . import korean_layer_display_names, schemas


def _identification_photo_paths_expression(table: schemas.TableDef) -> str:
    """Builds a QGIS expression that, evaluated against the *current* feature, yields a
    comma-separated list of that feature's own relative attachment paths -- the exact expression
    the embedded QML Widget's `expression.evaluate(...)` call needs (FR-QPB-101, revised;
    confirmed real mechanism, docs.qfield.org "Define QML Widgets").

    Table-name-agnostic: Type 1's `inventory_observation`, Type 2/3's `observation`, and Type
    4's `community` store their photos as inline attachment-path columns. No identification target
    reads a related photo-child table.
    """
    photo_fields = [c.name for c in table.columns if c.is_attachment_path]
    if not photo_fields:
        return "''"
    array_expr = ",".join(photo_fields)
    return f"array_to_string(array_remove_all(array({array_expr}), NULL), ',')"


def _authoritative_location_expression(
    survey_type: str, table_name: str, project_crs: str = "EPSG:4326"
) -> str:
    """Return a fail-closed WGS84 expression for the authoritative survey/plot geometry.

    The generated GeoPackage is stored in the project CRS.  The expression therefore performs
    the CRS conversion while it still has QGIS's authoritative geometry/CRS machinery available;
    the embedded widget receives WGS84 coordinates only after that conversion succeeds.
    """
    # The generated GeoPackage domain layers are registered with their schema CRS (EPSG:4326),
    # while ``project_crs`` is only the QGIS project display CRS (normally EPSG:5186).  `$geometry`
    # and geometries returned by get_feature() are expressed in the source layer CRS, not the
    # project CRS.  Using the project CRS here silently transforms valid WGS84 coordinates as if
    # they were metre-based Korean-grid coordinates and commonly samples a zero-valued cell.
    # Keep the argument for API compatibility, but always use the actual generated layer CRS.
    source_crs = "EPSG:4326"
    project_crs_hint = str(project_crs or "").replace("*/", "").replace("\n", " ")
    expression_prefix = (
        f"/* project CRS hint: {project_crs_hint}; source layer CRS: {source_crs} */ "
    )

    def wgs84_point(geometry_variable: str) -> str:
        return expression_prefix + (
            f"with_variable('wgs84_geom', transform(@{geometry_variable}, "
            f"'{source_crs}', 'EPSG:4326'), "
            f"if(@wgs84_geom IS NULL OR is_empty(@wgs84_geom) OR "
            f"geometry_type(@wgs84_geom) <> 'Point', NULL, "
            f"to_string(x(@wgs84_geom) || '|' || y(@wgs84_geom))))"
        )

    def wgs84_centroid(geometry_variable: str) -> str:
        return expression_prefix + (
            f"with_variable('wgs84_geom', transform(centroid(@{geometry_variable}), "
            f"'{source_crs}', 'EPSG:4326'), "
            f"if(@wgs84_geom IS NULL OR is_empty(@wgs84_geom) OR "
            f"geometry_type(@wgs84_geom) <> 'Point', NULL, "
            f"to_string(x(@wgs84_geom) || '|' || y(@wgs84_geom))))"
        )

    if survey_type == "simple_inventory" and table_name == "inventory_observation":
        return expression_prefix + (
            "with_variable('g', $geometry, if(@g IS NULL OR is_empty(@g) OR "
            "geometry_type(@g) <> 'Point', NULL, " + wgs84_point("g") + "))"
        )
    # ``get_feature()`` resolves a QGIS *layer name*, not the raw GeoPackage table name.  The
    # generated project deliberately presents these layers under Korean display names, so using
    # ``survey``/``plot`` here silently returns NULL on device even when the parent record exists.
    survey_layer_name = korean_layer_display_names.display_name_for("survey").replace("'", "''")
    plot_layer_name = korean_layer_display_names.display_name_for("plot").replace("'", "''")

    if survey_type == "temporary_plots" and table_name == "observation":
        return expression_prefix + (
            # A related-record add form can be opened while its parent survey is still unsaved.
            # Its foreign key is copied into the child by QField, but `get_feature()` searches
            # the provider and therefore cannot find that pending survey.  Read the live parent
            # form geometry first; only fall back to the persisted survey lookup for an existing
            # parent/reopened observation.
            "with_variable('parent_survey_geom', geometry(@current_parent_feature), "
            "with_variable('survey_id_value', coalesce(\"survey_id\", "
            "attribute(@current_parent_feature, 'survey_id')), "
            f"with_variable('survey_feature', get_feature('{survey_layer_name}', "
            "'survey_id', @survey_id_value), "
            "with_variable('persisted_survey_geom', if(@survey_feature IS NULL, NULL, "
            "geometry(@survey_feature)), "
            "with_variable('plot_geom', if(@parent_survey_geom IS NOT NULL AND "
            "NOT is_empty(@parent_survey_geom) AND geometry_type(@parent_survey_geom) = 'Point', "
            "@parent_survey_geom, @persisted_survey_geom), "
            "if(@plot_geom IS NULL OR is_empty(@plot_geom) OR "
            "geometry_type(@plot_geom) <> 'Point', NULL, " + wgs84_point("plot_geom") + "))))))"
        )
    if survey_type == "permanent_plots" and table_name == "observation":
        return expression_prefix + (
            # The QML widget evaluates against the observation itself.  Read the snapshot copied
            # into this record at form creation, not a nested parent-form context.  Saved/reopened
            # records still fall back through observation.survey_id to the authoritative plot.
            "with_variable('snapshot_plot_wkt', \"qpb_plot_geometry_wkt\", "
            "with_variable('snapshot_plot_geom', if(@snapshot_plot_wkt IS NULL OR "
            "trim(@snapshot_plot_wkt) = '', NULL, geom_from_wkt(@snapshot_plot_wkt)), "
            "with_variable('survey_id_value', \"survey_id\", "
            f"with_variable('survey_feature', get_feature('{survey_layer_name}', "
            "'survey_id', @survey_id_value), "
            "with_variable('plot_id_value', if(@survey_feature IS NULL, NULL, "
            "attribute(@survey_feature, 'plot_id')), "
            f"with_variable('plot_feature', get_feature('{plot_layer_name}', "
            "'plot_id', @plot_id_value), "
            "with_variable('persisted_plot_geom', if(@plot_feature IS NULL, NULL, "
            "geometry(@plot_feature)), "
            "with_variable('plot_geom', if(@snapshot_plot_geom IS NOT NULL AND "
            "NOT is_empty(@snapshot_plot_geom) AND "
            "geometry_type(@snapshot_plot_geom) = 'Point', @snapshot_plot_geom, "
            "@persisted_plot_geom), "
            "if(@plot_geom IS NULL OR is_empty(@plot_geom) OR "
            "geometry_type(@plot_geom) <> 'Point', NULL, " + wgs84_point("plot_geom") + ")))))))))"
        )
    if survey_type == "vegetation_mapping" and table_name == "community":
        # Type 4 records are community polygons, not point observations.  Their centroid is the
        # authoritative location for probability sampling; photo GPS is intentionally not used.
        return expression_prefix + (
            "with_variable('community_geom', $geometry, if(@community_geom IS NULL OR "
            "is_empty(@community_geom) OR geometry_type(@community_geom) NOT IN "
            "('Polygon', 'MultiPolygon'), NULL, " + wgs84_centroid("community_geom") + "))"
        )
    return expression_prefix + "NULL"
