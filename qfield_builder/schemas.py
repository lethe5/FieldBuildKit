"""Survey schema definitions by type (Section 8 of the specification).

This module is the single source of truth for table/column/foreign-key/geometry/relation
definitions per survey type, used by both the GeoPackage builder (:mod:`qfield_builder.gpkg`)
and the QGIS project generator (:mod:`qfield_builder.qgis_worker`), so the two never drift apart.

Only MVP survey types are modelled: ``simple_inventory`` (Type 1), ``temporary_plots`` (Type 2),
``permanent_plots`` (Type 3), and ``vegetation_mapping`` (Type 4). The post-MVP Pl@ntNet/KTSN/
probability workflow (Section 13) is out of scope; the nullable, inactive forward-compatible
columns it will eventually use (per Decision Log D-12) are still declared here for Types 1-3,
per DR-QPB-014/DR-QPB-015, but no post-MVP behavior reads or writes them.
"""
from __future__ import annotations

from dataclasses import dataclass

SURVEY_TYPES = (
    "simple_inventory",
    "temporary_plots",
    "permanent_plots",
    "vegetation_mapping",
)

# Forward-compatible, nullable, inactive-in-MVP Pl@ntNet columns shared by Types 1-3 (D-12).
_IDENTIFICATION_STATUS_VALUES = ("not_requested", "pending", "complete", "failed", "manual")


@dataclass(frozen=True)
class ColumnDef:
    name: str
    sql_type: str  # SQLite storage class: TEXT, INTEGER, REAL, DATETIME, DATE, BOOLEAN
    not_null: bool = False
    default_sql: str | None = None  # raw SQL default expression, e.g. "(datetime('now'))"
    unique: bool = False
    is_uuid_pk: bool = False
    check_sql: str | None = None  # raw SQL CHECK expression (without surrounding parens)
    is_attachment_path: bool = False
    comment: str = ""


@dataclass(frozen=True)
class ForeignKeyDef:
    column: str
    ref_table: str
    ref_column: str
    on_delete: str = "CASCADE"
    on_update: str = "CASCADE"
    relation_id: str = ""
    composition: bool = True


@dataclass(frozen=True)
class GeometryDef:
    column: str
    geom_type: str  # "POINT" | "MULTIPOLYGON"
    srs_id: int = 4326


@dataclass(frozen=True)
class TableDef:
    name: str
    columns: tuple[ColumnDef, ...]
    uuid_pk: str
    geometry: GeometryDef | None = None
    foreign_key: ForeignKeyDef | None = None
    display_expression: str = ""
    group: str = "Survey data"


def _uuid_col(name: str) -> ColumnDef:
    return ColumnDef(name=name, sql_type="TEXT", not_null=True, unique=True, is_uuid_pk=True)


def _fk_uuid_col(name: str) -> ColumnDef:
    return ColumnDef(name=name, sql_type="TEXT", not_null=True)


def _required_text(name: str) -> ColumnDef:
    return ColumnDef(
        name=name,
        sql_type="TEXT",
        not_null=True,
        check_sql=f"length(trim({name})) > 0",
    )


def _optional_text_nonempty_when_present(name: str) -> ColumnDef:
    return ColumnDef(
        name=name,
        sql_type="TEXT",
        not_null=False,
        check_sql=f"{name} IS NULL OR length(trim({name})) > 0",
    )


def _identification_status_col() -> ColumnDef:
    values = ", ".join(f"'{v}'" for v in _IDENTIFICATION_STATUS_VALUES)
    return ColumnDef(
        name="identification_status",
        sql_type="TEXT",
        not_null=True,
        default_sql="'not_requested'",
        check_sql=f"identification_status IN ({values})",
        comment="not_requested in MVP; post-MVP adds pending/complete/failed/manual",
    )


def _score_col(name: str) -> ColumnDef:
    return ColumnDef(
        name=name,
        sql_type="REAL",
        not_null=False,
        check_sql=f"{name} IS NULL OR ({name} >= 0.0 AND {name} <= 1.0)",
        comment="reserved; nullable/inactive until post-MVP identification subsystem ships",
    )


def _photo_path_col(name: str) -> ColumnDef:
    return ColumnDef(name=name, sql_type="TEXT", not_null=False, is_attachment_path=True)


def _identification_timestamp_and_model_version_columns() -> tuple[ColumnDef, ...]:
    """DR-QPB-052 (Type 1)/DR-QPB-053 (Type 2/3) (Decision Log D-38): two new nullable, reserved,
    inactive-until-post-MVP columns following the exact same forward-compatible pattern as the
    existing Pl@ntNet columns -- an identification timestamp (DATETIME, ISO 8601 with timezone per
    DR-QPB-013) and the API/model version string (TEXT). Never added to Type 4 `community`
    (DR-QPB-054, a non-destructive extension of DR-QPB-050's existing exclusion)."""
    return (
        ColumnDef(
            name="identification_timestamp",
            sql_type="DATETIME",
            not_null=False,
            comment="reserved; nullable/inactive until post-MVP identification subsystem ships",
        ),
        ColumnDef(
            name="identification_model_version",
            sql_type="TEXT",
            not_null=False,
            comment="reserved; nullable/inactive until post-MVP identification subsystem ships",
        ),
    )


def _identification_forward_compat_columns() -> tuple[ColumnDef, ...]:
    """Types 1-3 forward-compatible, nullable, inactive Pl@ntNet columns (Decision Log D-12),
    now including the DR-QPB-053 identification-timestamp/model-version columns (D-38)."""
    return (
        ColumnDef(name="selected_korean_name", sql_type="TEXT", not_null=False),
        ColumnDef(name="selected_scientific_name", sql_type="TEXT", not_null=False),
        ColumnDef(name="selected_ktsn", sql_type="TEXT", not_null=False),
        _score_col("identification_score"),
        _score_col("occurrence_probability"),
        *_identification_timestamp_and_model_version_columns(),
    )


def _build_simple_inventory() -> dict[str, TableDef]:
    columns = (
        _uuid_col("inventory_id"),
        ColumnDef(
            name="observed_at",
            sql_type="DATETIME",
            not_null=True,
            default_sql="(datetime('now'))",
        ),
        _required_text("surveyor"),
        ColumnDef(name="selected_korean_name", sql_type="TEXT", not_null=False),
        ColumnDef(name="selected_scientific_name", sql_type="TEXT", not_null=False),
        ColumnDef(name="selected_ktsn", sql_type="TEXT", not_null=False),
        _score_col("identification_score"),
        _score_col("occurrence_probability"),
        *_identification_timestamp_and_model_version_columns(),
        _photo_path_col("leaf_photo_path"),
        _photo_path_col("flower_photo_path"),
        _photo_path_col("fruit_photo_path"),
        _identification_status_col(),
        ColumnDef(name="notes", sql_type="TEXT", not_null=False),
    )
    return {
        "inventory_observation": TableDef(
            name="inventory_observation",
            columns=columns,
            uuid_pk="inventory_id",
            geometry=GeometryDef(column="geom", geom_type="POINT"),
            display_expression=(
                "coalesce(selected_korean_name, selected_scientific_name, 'Inventory record')"
            ),
        )
    }


def _site_table() -> TableDef:
    return TableDef(
        name="site",
        columns=(
            _uuid_col("site_id"),
            _required_text("site_name"),
        ),
        uuid_pk="site_id",
        geometry=GeometryDef(column="site_geom", geom_type="MULTIPOLYGON"),
        display_expression="site_name",
    )


def _build_temporary_plots() -> dict[str, TableDef]:
    site = _site_table()
    survey = TableDef(
        name="survey",
        columns=(
            _uuid_col("survey_id"),
            _fk_uuid_col("site_id"),
            ColumnDef(
                name="survey_date",
                sql_type="DATE",
                not_null=False,
                default_sql="(date('now'))",
                comment="nullable to support FR-QPB-033 seed survey records",
            ),
            _optional_text_nonempty_when_present("surveyor"),
            ColumnDef(name="plot_size", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="survey_id",
        geometry=GeometryDef(column="plot_geom", geom_type="POINT"),
        foreign_key=ForeignKeyDef(
            column="site_id", ref_table="site", ref_column="site_id", relation_id="rel_survey_site"
        ),
        display_expression="concat(survey_date, ' ', surveyor)",
    )
    observation = TableDef(
        name="observation",
        columns=(
            _uuid_col("observation_id"),
            _fk_uuid_col("survey_id"),
            *_identification_forward_compat_columns(),
            ColumnDef(
                name="cover",
                sql_type="INTEGER",
                not_null=True,
                check_sql="cover >= 0 AND cover <= 100",
            ),
            # DR-QPB-074/075 (Decision Log D-74, 2026-08-28): three optional, nullable,
            # relation-free photo-path fields, replacing the now-removed `observation_photo`
            # child table -- mirrors Type 1's `inventory_observation` exactly (DR-QPB-020).
            _photo_path_col("leaf_photo_path"),
            _photo_path_col("flower_photo_path"),
            _photo_path_col("fruit_photo_path"),
            _identification_status_col(),
            ColumnDef(name="notes", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="observation_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="survey_id",
            ref_table="survey",
            ref_column="survey_id",
            relation_id="rel_observation_survey",
        ),
        display_expression=(
            "concat(coalesce(selected_korean_name, selected_scientific_name, '미입력'), "
            "'(', coalesce(to_string(cover), '미입력'), '%)')"
        ),
    )
    survey_photo = TableDef(
        name="survey_photo",
        columns=(
            _uuid_col("photo_id"),
            _fk_uuid_col("survey_id"),
            ColumnDef(name="path", sql_type="TEXT", not_null=True, is_attachment_path=True),
            ColumnDef(name="captured_at", sql_type="DATETIME", not_null=False),
            ColumnDef(name="notes", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="photo_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="survey_id",
            ref_table="survey",
            ref_column="survey_id",
            relation_id="rel_survey_photo_survey",
        ),
        display_expression="path",
    )
    # `observation_photo` (and its relation, `rel_observation_photo_observation`) is deliberately
    # absent here: DR-QPB-076 (Decision Log D-74, 2026-08-28) removes it entirely for Type 2 --
    # `observation`'s own three inline photo-path columns above replace it.
    return {
        "site": site,
        "survey": survey,
        "observation": observation,
        "survey_photo": survey_photo,
    }


def _build_permanent_plots() -> dict[str, TableDef]:
    site = _site_table()
    plot = TableDef(
        name="plot",
        columns=(
            _uuid_col("plot_id"),
            _fk_uuid_col("site_id"),
            # Carries the plot's own digitized geometry through a nested Plot → Survey →
            # Observation form.  It is operational state only and is excluded from reports.
            ColumnDef(name="qpb_plot_geometry_wkt", sql_type="TEXT", not_null=False),
            _required_text("plot_name"),
            ColumnDef(name="plot_size", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="plot_id",
        geometry=GeometryDef(column="plot_geom", geom_type="POINT"),
        foreign_key=ForeignKeyDef(
            column="site_id", ref_table="site", ref_column="site_id", relation_id="rel_plot_site"
        ),
        display_expression="plot_name",
    )
    survey = TableDef(
        name="survey",
        columns=(
            _uuid_col("survey_id"),
            _fk_uuid_col("plot_id"),
            # Copied from the immediate plot parent when this survey is opened as a related
            # record.  The observation form then reads this immediate survey-parent value.
            ColumnDef(name="qpb_plot_geometry_wkt", sql_type="TEXT", not_null=False),
            ColumnDef(
                name="survey_date", sql_type="DATE", not_null=True, default_sql="(date('now'))"
            ),
            _required_text("surveyor"),
        ),
        uuid_pk="survey_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="plot_id", ref_table="plot", ref_column="plot_id", relation_id="rel_survey_plot"
        ),
        display_expression="concat(survey_date, ' ', surveyor)",
    )
    observation = TableDef(
        name="observation",
        columns=(
            _uuid_col("observation_id"),
            _fk_uuid_col("survey_id"),
            # The final hop of the Type 3 Plot → Survey → Observation location snapshot. The
            # identification QML widget reads its own record, never a nested parent form.
            ColumnDef(name="qpb_plot_geometry_wkt", sql_type="TEXT", not_null=False),
            *_identification_forward_compat_columns(),
            ColumnDef(
                name="cover",
                sql_type="INTEGER",
                not_null=True,
                check_sql="cover >= 0 AND cover <= 100",
            ),
            # DR-QPB-074/075 (Decision Log D-74, 2026-08-28): three optional, nullable,
            # relation-free photo-path fields, replacing the now-removed `observation_photo`
            # child table -- mirrors Type 1's `inventory_observation` exactly (DR-QPB-020), and
            # is shared, by cross-reference, with Type 2's identical `observation` table above.
            _photo_path_col("leaf_photo_path"),
            _photo_path_col("flower_photo_path"),
            _photo_path_col("fruit_photo_path"),
            _identification_status_col(),
            ColumnDef(name="notes", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="observation_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="survey_id",
            ref_table="survey",
            ref_column="survey_id",
            relation_id="rel_observation_survey",
        ),
        display_expression=(
            "concat(coalesce(selected_korean_name, selected_scientific_name, '미입력'), "
            "'(', coalesce(to_string(cover), '미입력'), '%)')"
        ),
    )
    plot_photo = TableDef(
        name="plot_photo",
        columns=(
            _uuid_col("photo_id"),
            _fk_uuid_col("plot_id"),
            ColumnDef(name="path", sql_type="TEXT", not_null=True, is_attachment_path=True),
            ColumnDef(name="captured_at", sql_type="DATETIME", not_null=False),
            ColumnDef(name="notes", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="photo_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="plot_id",
            ref_table="plot",
            ref_column="plot_id",
            relation_id="rel_plot_photo_plot",
        ),
        display_expression="path",
    )
    # `observation_photo` (and its relation, `rel_observation_photo_observation`) is deliberately
    # absent here: DR-QPB-076 (Decision Log D-74, 2026-08-28) removes it entirely for Type 3 --
    # `observation`'s own three inline photo-path columns above replace it. `plot_photo`
    # immediately above is a structurally distinct table (photos of the permanent `plot` itself,
    # not of an individual `observation`) and is completely unaffected by this change.
    return {
        "site": site,
        "plot": plot,
        "survey": survey,
        "observation": observation,
        "plot_photo": plot_photo,
    }


def _build_vegetation_mapping() -> dict[str, TableDef]:
    site = _site_table()
    survey = TableDef(
        name="survey",
        columns=(
            _uuid_col("survey_id"),
            _fk_uuid_col("site_id"),
            ColumnDef(
                name="survey_date", sql_type="DATE", not_null=True, default_sql="(date('now'))"
            ),
            _required_text("surveyor"),
        ),
        uuid_pk="survey_id",
        geometry=None,
        foreign_key=ForeignKeyDef(
            column="site_id", ref_table="site", ref_column="site_id", relation_id="rel_survey_site"
        ),
        display_expression="concat(survey_date, ' ', surveyor)",
    )
    community = TableDef(
        name="community",
        columns=(
            _uuid_col("community_id"),
            _fk_uuid_col("survey_id"),
            _required_text("community_name"),
            ColumnDef(name="dominant_species", sql_type="TEXT", not_null=False),
            ColumnDef(name="subdominant_species", sql_type="TEXT", not_null=False),
            ColumnDef(
                name="is_field_checked", sql_type="BOOLEAN", not_null=True, default_sql="0"
            ),
            _photo_path_col("leaf_photo_path"),
            _photo_path_col("flower_photo_path"),
            _photo_path_col("fruit_photo_path"),
            ColumnDef(name="notes", sql_type="TEXT", not_null=False),
        ),
        uuid_pk="community_id",
        geometry=GeometryDef(column="community_geom", geom_type="MULTIPOLYGON"),
        foreign_key=ForeignKeyDef(
            column="survey_id",
            ref_table="survey",
            ref_column="survey_id",
            relation_id="rel_community_survey",
        ),
        display_expression="community_name",
    )
    return {"site": site, "survey": survey, "community": community}


_BUILDERS = {
    "simple_inventory": _build_simple_inventory,
    "temporary_plots": _build_temporary_plots,
    "permanent_plots": _build_permanent_plots,
    "vegetation_mapping": _build_vegetation_mapping,
}


def get_schema(survey_type: str) -> dict[str, TableDef]:
    """Return the ordered {table_name: TableDef} mapping for a survey type.

    Tables are returned in dependency order (parents before children) so callers can create
    tables and insert seed data without needing a second topological sort.
    """
    if survey_type not in _BUILDERS:
        raise ValueError(f"Unknown survey_type: {survey_type!r}")
    return _BUILDERS[survey_type]()


def photo_tables_for(survey_type: str) -> tuple[str, ...]:
    """Names of tables that are related, zero-or-more, optional photo tables (Section 8).

    `observation_photo` (Type 2/3) is deliberately absent (Decision Log D-74, 2026-08-28): it was
    removed entirely and replaced by three inline photo-path columns on `observation` itself
    (see :func:`photo_path_fields_for`), mirroring Type 1's `inventory_observation`, which has
    never had a related photo table of its own either.
    """
    return {
        "simple_inventory": (),
        "temporary_plots": ("survey_photo",),
        "permanent_plots": ("plot_photo",),
        "vegetation_mapping": (),
    }[survey_type]


def photo_path_fields_for(survey_type: str) -> dict[str, tuple[str, ...]]:
    """{table_name: (photo-path-column, ...)} for tables with attachment-path columns."""
    schema = get_schema(survey_type)
    result: dict[str, tuple[str, ...]] = {}
    for table_name, table_def in schema.items():
        photo_cols = tuple(c.name for c in table_def.columns if c.is_attachment_path)
        if photo_cols:
            result[table_name] = photo_cols
    return result
