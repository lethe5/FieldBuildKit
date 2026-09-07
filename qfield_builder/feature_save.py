"""Save features using shared schema constraints and SQLite, without QGIS.

The legacy PyQGIS implementation is retained for developer-only comparisons.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import schemas
from .gpkg import new_uuid
from .gpkg_functions import register_gpkg_functions
from .layer_lookup import find_layer_by_table_name
from .paths import classify_attachment_path
from .wkt import InvalidGeometryError, wkt_to_gpkg_geometry


def _find_gpkg_and_survey_type(project_dir: str) -> tuple[str, str]:
    root = Path(project_dir)
    gpkg_candidates = list((root / "data").glob("*.gpkg")) or list(root.glob("*.gpkg"))
    if not gpkg_candidates:
        raise FileNotFoundError(f"No .gpkg file found under {project_dir!r}")
    gpkg_path = str(gpkg_candidates[0])
    conn = sqlite3.connect(gpkg_path)
    try:
        row = conn.execute(
            "SELECT survey_type FROM qpb_schema_metadata ORDER BY created_at DESC LIMIT 1;"
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError(f"No qpb_schema_metadata found in {gpkg_path!r}")
    return gpkg_path, row[0]


def _rejected(field: str | None, reason: str) -> dict:
    return {
        "accepted": False,
        "rejected_field": field,
        "rejected_reason": reason,
        "generated_uuid": None,
    }


def _accepted(generated_uuid: str) -> dict:
    return {
        "accepted": True,
        "rejected_field": None,
        "rejected_reason": None,
        "generated_uuid": generated_uuid,
    }


def _validate_against_constraints(
    table: schemas.TableDef, attributes: dict, geometry_wkt: str | None
) -> dict | None:
    """Returns a rejection dict if a hard constraint fails, else None."""
    for col in table.columns:
        if col.is_uuid_pk:
            continue  # read-only/auto-generated; never validated as caller input.

        value = attributes.get(col.name)

        if col.not_null and (value is None or (isinstance(value, str) and value.strip() == "")):
            if col.default_sql is not None:
                continue  # a DB default exists (e.g. survey_date); absence is fine.
            return _rejected(col.name, f"{col.name} is required and must not be empty.")

        if value is None:
            continue

        if col.name == "cover":
            try:
                cover_value = int(value)
            except (TypeError, ValueError):
                return _rejected(col.name, "cover must be an integer.")
            if cover_value < 0 or cover_value > 100:
                return _rejected(col.name, "cover must be between 0 and 100 inclusive.")

        if isinstance(value, str) and col.check_sql and "length(trim(" in col.check_sql:
            if value.strip() == "":
                return _rejected(col.name, f"{col.name} must not be empty or whitespace-only.")

        if col.name == "organ" and value not in ("leaf", "flower", "fruit", "bark", "auto", None):
            return _rejected(col.name, "organ must be one of leaf/flower/fruit/bark/auto.")

        if col.is_attachment_path:
            shape = classify_attachment_path(value)
            if shape is not None:
                return _rejected(
                    col.name, f"'{value}' is not a valid relative attachment path ({shape})."
                )

    if table.geometry is not None and geometry_wkt:
        try:
            from .wkt import validate_geometry

            validate_geometry(geometry_wkt, table.geometry.geom_type)
        except InvalidGeometryError as exc:
            return _rejected(table.geometry.column, f"Invalid geometry: {exc}")

    return None


def _attempt_feature_save_sqlite_fallback(
    project_dir: str, layer_name: str, attributes: dict, geometry_wkt: str | None
) -> dict:
    gpkg_path, survey_type = _find_gpkg_and_survey_type(project_dir)
    schema = schemas.get_schema(survey_type)
    table = schema.get(layer_name)
    if table is None:
        return _rejected(None, f"Unknown layer: {layer_name!r}")

    rejection = _validate_against_constraints(table, attributes, geometry_wkt)
    if rejection is not None:
        return rejection

    conn = sqlite3.connect(gpkg_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    register_gpkg_functions(conn)
    try:
        record_id = new_uuid()
        columns = [table.uuid_pk]
        values: list = [record_id]
        for col in table.columns:
            if col.is_uuid_pk:
                continue
            if col.name in attributes:
                columns.append(col.name)
                values.append(attributes[col.name])

        geom_envelope = None
        if table.geometry is not None and geometry_wkt:
            blob, geom_envelope = wkt_to_gpkg_geometry(geometry_wkt, table.geometry.geom_type)
            columns.append(table.geometry.column)
            values.append(blob)

        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(f'"{c}"' for c in columns)
        try:
            cur = conn.execute(
                f'INSERT INTO "{layer_name}" ({column_list}) VALUES ({placeholders});', values
            )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            return _rejected(None, f"Database constraint violation: {exc}")

        if geom_envelope is not None:
            from .gpkg import _insert_rtree_row  # noqa: SLF001 - internal helper reuse

            _insert_rtree_row(conn, layer_name, table.geometry.column, cur.lastrowid, geom_envelope)

        conn.commit()
        return _accepted(record_id)
    finally:
        conn.close()


def _attempt_feature_save_pyqgis(
    project_dir: str, layer_name: str, attributes: dict, geometry_wkt: str | None
) -> dict | None:
    """Primary implementation path (FR-QPB-057's "hard constraints" via QgsFieldConstraints).

    Returns None if PyQGIS is not importable, signalling the caller to use the SQLite fallback.
    """
    try:
        from qgis.core import (
            QgsFieldConstraints,
            QgsGeometry,
            QgsProject,
            QgsVectorLayerUtils,
        )
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    root = Path(project_dir)
    qgs_candidates = list(root.glob("*.qgs"))
    if not qgs_candidates:
        return _rejected(None, "No .qgs project file found.")

    project = QgsProject()
    project.read(str(qgs_candidates[0]))
    layer = find_layer_by_table_name(project, layer_name)
    if layer is None:
        return _rejected(None, f"Unknown layer: {layer_name!r}")

    # `QgsVectorLayerUtils.createFeature` (rather than a bare `QgsFeature(layer.fields())`)
    # evaluates each field's configured default value expression — including the UUID primary
    # key's `uuid('WithoutBraces')` default (DR-QPB-005) — exactly as the real QGIS/QField
    # attribute form would for a newly created feature, so a caller-omitted UUID primary key is
    # correctly auto-generated rather than validated as a missing required value.
    attribute_map = {}
    for name, value in attributes.items():
        idx = layer.fields().indexOf(name)
        if idx >= 0:
            attribute_map[idx] = value
    geometry = QgsGeometry.fromWkt(geometry_wkt) if geometry_wkt else QgsGeometry()
    feature = QgsVectorLayerUtils.createFeature(layer, geometry, attribute_map)

    # `fid` is the OGR/GeoPackage provider's own autoincrement row-id primary key, invisible to
    # this project's own schema (:mod:`qfield_builder.schemas`, which uses its own UUID primary
    # key column instead per DR-QPB-002/003). It is intentionally left unset here so the provider
    # autogenerates it, so it must never be treated as a caller-facing "required" attribute.
    pk_indexes = set(layer.dataProvider().pkAttributeIndexes())
    for idx in range(layer.fields().count()):
        if idx in pk_indexes:
            continue
        ok, errors = QgsVectorLayerUtils.validateAttribute(
            layer, feature, idx, strength=QgsFieldConstraints.ConstraintStrengthHard
        )
        if not ok:
            field_name = layer.fields().at(idx).name()
            return _rejected(field_name, "; ".join(errors) if errors else "Constraint violated.")

    layer.startEditing()
    added = layer.addFeature(feature)
    if not added:
        layer.rollBack()
        return _rejected(None, "The feature could not be added.")
    layer.commitChanges()

    uuid_field = schemas.get_schema(_survey_type_for_project(project_dir))[layer_name].uuid_pk
    idx = layer.fields().indexOf(uuid_field)
    return _accepted(feature.attribute(idx))


def _survey_type_for_project(project_dir: str) -> str:
    _, survey_type = _find_gpkg_and_survey_type(project_dir)
    return survey_type


def attempt_feature_save(
    project_dir: str, layer_name: str, attributes: dict, geometry_wkt: str | None = None
) -> dict:
    """Apply the shared schema constraints without launching QGIS."""
    return _attempt_feature_save_sqlite_fallback(project_dir, layer_name, attributes, geometry_wkt)
