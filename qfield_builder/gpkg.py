"""Standards-compliant GeoPackage (.gpkg) builder (Section 7-8 of the specification).

Builds a GeoPackage 1.2/1.3-compliant SQLite database directly via :mod:`sqlite3` — no GDAL/OGR
dependency is required to *create* the file, which keeps schema generation fully testable in
environments without a QGIS/GDAL runtime (this sandbox included). The resulting file follows the
GeoPackage core spec (``gpkg_spatial_ref_sys``, ``gpkg_contents``, ``gpkg_geometry_columns``) and
the R*Tree Spatial Indexes extension (``gpkg_extensions`` + the standard trigger set), so a real
GDAL/QGIS installation can open, read, and continue maintaining the spatial index on this file
without modification.

Domain schema (tables/columns/constraints/foreign keys) comes from :mod:`qfield_builder.schemas`,
which is the single source of truth shared with the QGIS project generator.
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
import uuid
from pathlib import Path

from . import schemas
from .gpkg_functions import register_gpkg_functions
from .wkt import Envelope, polygon_wkb_to_multipolygon, wkb_to_gpkg_blob, wkt_to_gpkg_geometry

GPKG_APPLICATION_ID = 0x47504B47  # 'GPKG'
SCHEMA_VERSION = "1.0.0"

_WGS84_WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]'
)


def _connect(gpkg_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(gpkg_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    register_gpkg_functions(conn)
    return conn


def _write_gpkg_application_id(conn: sqlite3.Connection) -> None:
    # 'GP' + version digits '1' '1' in the two low bytes, per the GeoPackage spec's
    # application_id/user_version convention (informational; not required for the checks these
    # acceptance tests run, but keeps the file self-describing for other GeoPackage tooling).
    conn.execute(f"PRAGMA application_id = {GPKG_APPLICATION_ID};")
    conn.execute("PRAGMA user_version = 10200;")


def _create_core_gpkg_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL,
            organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY,
            data_type TEXT NOT NULL,
            identifier TEXT UNIQUE,
            description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
            srs_id INTEGER,
            CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL,
            m TINYINT NOT NULL,
            CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
            CONSTRAINT uk_gc_table_name UNIQUE (table_name),
            CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
            CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE gpkg_extensions (
            table_name TEXT,
            column_name TEXT,
            extension_name TEXT NOT NULL,
            definition TEXT NOT NULL,
            scope TEXT NOT NULL,
            CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name)
        );

        CREATE TABLE qpb_schema_metadata (
            project_id TEXT NOT NULL,
            survey_type TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO gpkg_spatial_ref_sys "
        "(srs_name, srs_id, organization, organization_coordsys_id, definition, description) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("Undefined cartesian SRS", 0, "NONE", 0, "undefined", "undefined Cartesian SRS"),
    )
    conn.execute(
        "INSERT INTO gpkg_spatial_ref_sys "
        "(srs_name, srs_id, organization, organization_coordsys_id, definition, description) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("Undefined geographic SRS", -1, "NONE", -1, "undefined", "undefined geographic SRS"),
    )
    conn.execute(
        "INSERT INTO gpkg_spatial_ref_sys "
        "(srs_name, srs_id, organization, organization_coordsys_id, definition, description) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("WGS 84", 4326, "EPSG", 4326, _WGS84_WKT, "WGS 84"),
    )


_SQLITE_TYPE_MAP = {
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "REAL": "REAL",
    "DATETIME": "TEXT",
    "DATE": "TEXT",
    "BOOLEAN": "BOOLEAN",
}


def _column_ddl(col: schemas.ColumnDef) -> str:
    parts = [f'"{col.name}"', _SQLITE_TYPE_MAP.get(col.sql_type, "TEXT")]
    if col.not_null:
        parts.append("NOT NULL")
    if col.unique:
        parts.append("UNIQUE")
    if col.default_sql is not None:
        parts.append(f"DEFAULT {col.default_sql}")
    if col.check_sql:
        parts.append(f"CHECK ({col.check_sql})")
    return " ".join(parts)


def _create_domain_table(conn: sqlite3.Connection, table: schemas.TableDef) -> None:
    column_ddls = [_column_ddl(c) for c in table.columns]
    ddl_parts = ['"fid" INTEGER PRIMARY KEY AUTOINCREMENT', *column_ddls]
    if table.geometry is not None:
        ddl_parts.append(f'"{table.geometry.column}" BLOB')
    fk_clause = ""
    if table.foreign_key is not None:
        fk = table.foreign_key
        fk_clause = (
            f', CONSTRAINT "fk_{table.name}_{fk.column}" FOREIGN KEY ("{fk.column}") '
            f'REFERENCES "{fk.ref_table}" ("{fk.ref_column}") '
            f"ON DELETE {fk.on_delete} ON UPDATE {fk.on_update} DEFERRABLE INITIALLY DEFERRED"
        )
    ddl = f'CREATE TABLE "{table.name}" ({", ".join(ddl_parts)}{fk_clause});'
    conn.execute(ddl)

    # Ordinary indexes on UUID FK columns and commonly-searched name fields (DR-QPB-009).
    if table.foreign_key is not None:
        conn.execute(
            f'CREATE INDEX "idx_{table.name}_{table.foreign_key.column}" '
            f'ON "{table.name}" ("{table.foreign_key.column}");'
        )
    for col in table.columns:
        if col.name.endswith("_name") or col.name == "surveyor":
            conn.execute(
                f'CREATE INDEX "idx_{table.name}_{col.name}" ON "{table.name}" ("{col.name}");'
            )


def _register_geometry_table(conn: sqlite3.Connection, table: schemas.TableDef) -> None:
    assert table.geometry is not None
    conn.execute(
        "INSERT INTO gpkg_contents (table_name, data_type, identifier, srs_id) "
        "VALUES (?, ?, ?, ?);",
        (table.name, "features", table.name, table.geometry.srs_id),
    )
    conn.execute(
        "INSERT INTO gpkg_geometry_columns "
        "(table_name, column_name, geometry_type_name, srs_id, z, m) VALUES (?, ?, ?, ?, 0, 0);",
        (table.name, table.geometry.column, table.geometry.geom_type, table.geometry.srs_id),
    )


def _register_attributes_table(conn: sqlite3.Connection, table: schemas.TableDef) -> None:
    conn.execute(
        "INSERT INTO gpkg_contents (table_name, data_type, identifier) VALUES (?, ?, ?);",
        (table.name, "attributes", table.name),
    )


def _create_rtree(conn: sqlite3.Connection, table: schemas.TableDef) -> None:
    assert table.geometry is not None
    t, c = table.name, table.geometry.column
    rtree_name = f"rtree_{t}_{c}"
    conn.execute(f'CREATE VIRTUAL TABLE "{rtree_name}" USING rtree(id, minx, maxx, miny, maxy);')
    conn.execute(
        "INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope) "
        "VALUES (?, ?, 'gpkg_rtree_index', "
        "'http://www.geopackage.org/spec/#extension_rtree', 'write-only');",
        (t, c),
    )
    # Standard GeoPackage RTree-maintenance triggers (per the GeoPackage spec Annex). These call
    # the ST_MinX/ST_MaxX/ST_MinY/ST_MaxY/ST_IsEmpty SQL functions that GDAL registers when it
    # opens this file — they are inert (never fired) for the seed-data inserts this builder
    # performs itself, since we populate the rtree rows directly (see _insert_rtree_row), but
    # they are exactly what a real QGIS/QField edit session relies on afterwards.
    conn.executescript(
        f"""
        CREATE TRIGGER "rtree_{t}_{c}_insert" AFTER INSERT ON "{t}"
          WHEN (new."{c}" NOT NULL AND NOT ST_IsEmpty(NEW."{c}"))
        BEGIN
          INSERT OR REPLACE INTO "{rtree_name}" VALUES (
            NEW."fid",
            ST_MinX(NEW."{c}"), ST_MaxX(NEW."{c}"),
            ST_MinY(NEW."{c}"), ST_MaxY(NEW."{c}")
          );
        END;

        CREATE TRIGGER "rtree_{t}_{c}_update1" AFTER UPDATE OF "{c}" ON "{t}"
          WHEN OLD."fid" = NEW."fid" AND
               (NEW."{c}" NOTNULL AND NOT ST_IsEmpty(NEW."{c}"))
        BEGIN
          INSERT OR REPLACE INTO "{rtree_name}" VALUES (
            NEW."fid",
            ST_MinX(NEW."{c}"), ST_MaxX(NEW."{c}"),
            ST_MinY(NEW."{c}"), ST_MaxY(NEW."{c}")
          );
        END;

        CREATE TRIGGER "rtree_{t}_{c}_update2" AFTER UPDATE OF "{c}" ON "{t}"
          WHEN OLD."fid" = NEW."fid" AND
               (NEW."{c}" ISNULL OR ST_IsEmpty(NEW."{c}"))
        BEGIN
          DELETE FROM "{rtree_name}" WHERE id = OLD."fid";
        END;

        CREATE TRIGGER "rtree_{t}_{c}_update3" AFTER UPDATE ON "{t}"
          WHEN OLD."fid" != NEW."fid" AND
               (NEW."{c}" NOTNULL AND NOT ST_IsEmpty(NEW."{c}"))
        BEGIN
          DELETE FROM "{rtree_name}" WHERE id = OLD."fid";
          INSERT OR REPLACE INTO "{rtree_name}" VALUES (
            NEW."fid",
            ST_MinX(NEW."{c}"), ST_MaxX(NEW."{c}"),
            ST_MinY(NEW."{c}"), ST_MaxY(NEW."{c}")
          );
        END;

        CREATE TRIGGER "rtree_{t}_{c}_update4" AFTER UPDATE ON "{t}"
          WHEN OLD."fid" != NEW."fid" AND
               (NEW."{c}" ISNULL OR ST_IsEmpty(NEW."{c}"))
        BEGIN
          DELETE FROM "{rtree_name}" WHERE id = OLD."fid";
        END;

        CREATE TRIGGER "rtree_{t}_{c}_delete" AFTER DELETE ON "{t}"
          WHEN old."{c}" NOT NULL
        BEGIN
          DELETE FROM "{rtree_name}" WHERE id = OLD."fid";
        END;
        """
    )


def _insert_rtree_row(
    conn: sqlite3.Connection, table_name: str, geom_col: str, fid: int, envelope: Envelope
) -> None:
    conn.execute(
        f'INSERT OR REPLACE INTO "rtree_{table_name}_{geom_col}" VALUES (?, ?, ?, ?, ?);',
        (fid, envelope.min_x, envelope.max_x, envelope.min_y, envelope.max_y),
    )


def new_uuid() -> str:
    return str(uuid.uuid4())


def build_geopackage(
    gpkg_path: str,
    survey_type: str,
    project_id: str,
    seed_sites: list[dict] | None = None,
    seed_plots: list[dict] | None = None,
    seed_temporary_plot_points: list[dict] | None = None,
    taxonomy_reference_available: bool = True,
) -> None:
    """Create a fresh GeoPackage for `survey_type` at `gpkg_path`, with any provided seed data.

    `seed_sites`: [{"site_name": str, "geom_wkt": str}] (or the internal binary
      `geom_wkb`/`geom_envelope` pair for large uploaded boundaries), written to the `site`
      table if present.
    `seed_plots`: [{"plot_name": str, "geom_wkt": str, "plot_size": str}], written to `plot`
      (Type 3 only).
    `seed_temporary_plot_points`: [{"site_name": str, "geom_wkt": str, "plot_size": str}],
      written as seed `survey` rows with empty survey_date/surveyor (FR-QPB-033, Type 2 only).
    """
    path = Path(gpkg_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = _connect(str(path))
    try:
        _write_gpkg_application_id(conn)
        _create_core_gpkg_tables(conn)

        schema = schemas.get_schema(survey_type, taxonomy_reference_available=taxonomy_reference_available)
        for table in schema.values():
            _create_domain_table(conn, table)
            if table.geometry is not None:
                _register_geometry_table(conn, table)
                _create_rtree(conn, table)
            else:
                _register_attributes_table(conn, table)

        conn.execute(
            "INSERT INTO qpb_schema_metadata "
            "(project_id, survey_type, schema_version, created_at) VALUES (?, ?, ?, ?);",
            (
                project_id,
                survey_type,
                SCHEMA_VERSION,
                _dt.datetime.now(_dt.timezone.utc).isoformat(),
            ),
        )

        site_id_by_name: dict[str, str] = {}
        if seed_sites and "site" in schema:
            for site in seed_sites:
                site_id = new_uuid()
                if site.get("geom_wkb") is not None:
                    source_wkb = polygon_wkb_to_multipolygon(site["geom_wkb"])
                    envelope = site.get("geom_envelope")
                    blob = wkb_to_gpkg_blob(source_wkb, 4326, envelope)
                    if envelope is None:
                        # This is only a fallback for nonstandard source headers.  Normal
                        # GeoPackages carry the XY envelope in their geometry header.
                        from .gpkg_functions import _wkb_envelope

                        envelope = _wkb_envelope(source_wkb)
                    if envelope is None:
                        raise ValueError("업로드 geometry의 envelope를 계산할 수 없습니다")
                else:
                    blob, envelope = wkt_to_gpkg_geometry(site["geom_wkt"], "MULTIPOLYGON")
                cur = conn.execute(
                    'INSERT INTO "site" (site_id, site_name, site_geom) VALUES (?, ?, ?);',
                    (site_id, site["site_name"], blob),
                )
                _insert_rtree_row(conn, "site", "site_geom", cur.lastrowid, envelope)
                site_id_by_name[site["site_name"]] = site_id

        if seed_plots and "plot" in schema:
            for plot in seed_plots:
                plot_id = new_uuid()
                blob, envelope = wkt_to_gpkg_geometry(plot["geom_wkt"], "POINT")
                site_id = next(iter(site_id_by_name.values()), None)
                cur = conn.execute(
                    'INSERT INTO "plot" (plot_id, site_id, plot_name, plot_size, plot_geom) '
                    "VALUES (?, ?, ?, ?, ?);",
                    (plot_id, site_id, plot["plot_name"], plot.get("plot_size"), blob),
                )
                _insert_rtree_row(conn, "plot", "plot_geom", cur.lastrowid, envelope)

        if seed_temporary_plot_points and "survey" in schema and "plot_geom" in {
            c.name for c in schema["survey"].columns
        } | {schema["survey"].geometry.column if schema["survey"].geometry else ""}:
            for point in seed_temporary_plot_points:
                survey_id = new_uuid()
                blob, envelope = wkt_to_gpkg_geometry(point["geom_wkt"], "POINT")
                site_id = site_id_by_name.get(point.get("site_name")) or next(
                    iter(site_id_by_name.values()), None
                )
                cur = conn.execute(
                    'INSERT INTO "survey" '
                    "(survey_id, site_id, survey_date, surveyor, plot_size, plot_geom) "
                    "VALUES (?, ?, NULL, NULL, ?, ?);",
                    (survey_id, site_id, point.get("plot_size"), blob),
                )
                _insert_rtree_row(conn, "survey", "plot_geom", cur.lastrowid, envelope)

        conn.commit()

        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        if violations:
            raise RuntimeError(f"GeoPackage foreign_key_check reported violations: {violations}")
    finally:
        conn.close()


def add_ktsn_lookup_table(gpkg_path: str, table_name: str, rows: list[dict]) -> None:
    """DR-QPB-072/FR-QPB-126/FR-QPB-127 (Decision Log D-66/D-67/D-68): adds the bundled KTSN
    accepted-name lookup table as an additional non-spatial table inside the same, already-built
    survey `.gpkg` file at `gpkg_path` -- **not** a second `.gpkg` file (DR-QPB-007). `rows` is
    the exact `"rows"` output of
    :func:`qfield_builder.reference_bundle.derive_accepted_name_lookup_table` (each a dict with
    `ktsn`/`taxon_kor_nm`/`taxon_full_nm` keys).

    Its own key column (`ktsn`) is the source data's own natural identifier, not a newly generated
    UUID -- DR-QPB-072's own explicit carve-out from DR-QPB-001's UUID-identifier rule, so this
    deliberately does not use `_uuid_col`/`_create_domain_table`'s domain-table conventions.

    Creates a real, build-time `CREATE INDEX` on the Korean-name (`taxon_kor_nm`) and
    scientific-name (`taxon_full_nm`) columns (closes O-32), mirroring DR-QPB-009's existing
    "ordinary indexes... on commonly searched name fields" convention -- not the in-memory
    JavaScript index technique the Pl@ntNet identification widget already uses for the same
    source data, which is unrelated to this table (DR-QPB-072).

    Must be called only after :func:`build_geopackage` has already created `gpkg_path` for this
    same project.
    """
    conn = _connect(gpkg_path)
    try:
        conn.execute(
            f'CREATE TABLE "{table_name}" ('
            '"fid" INTEGER PRIMARY KEY AUTOINCREMENT, '
            '"ktsn" TEXT NOT NULL, '
            '"taxon_kor_nm" TEXT, '
            '"taxon_full_nm" TEXT NOT NULL'
            ");"
        )
        conn.execute(
            f'CREATE INDEX "idx_{table_name}_taxon_kor_nm" ON "{table_name}" ("taxon_kor_nm");'
        )
        conn.execute(
            f'CREATE INDEX "idx_{table_name}_taxon_full_nm" ON "{table_name}" ("taxon_full_nm");'
        )
        conn.executemany(
            f'INSERT INTO "{table_name}" (ktsn, taxon_kor_nm, taxon_full_nm) VALUES (?, ?, ?);',
            [(row["ktsn"], row.get("taxon_kor_nm") or "", row["taxon_full_nm"]) for row in rows],
        )
        conn.execute(
            "INSERT INTO gpkg_contents (table_name, data_type, identifier) VALUES (?, ?, ?);",
            (table_name, "attributes", table_name),
        )
        conn.commit()
    finally:
        conn.close()


def add_ktsn_taxonomy_reference_table(gpkg_path: str, table_name: str, rows: list[dict]) -> None:
    """Materialize the D-95 canonical taxonomy table in the project's GeoPackage.

    It is intentionally a plain attributes table without ``fid``: the canonical KTSN is the
    source identity, and exposing a synthetic identifier would turn a read-only reference table
    into a domain entity in QField.  The physical declarations mirror DR-QPB-079 so SQLite/GPKG
    inspection can verify required fields and the integer source-row contract directly.
    """
    from .canonical_reference import LOGICAL_COLUMNS

    conn = _connect(gpkg_path)
    try:
        required_text = {
            "ktsn", "source_no", "taxon_status", "scientific_name",
            "scientific_name_normalized", "scientific_name_without_authority",
            "accepted_ktsn", "source_url",
        }
        integer_columns = {"source_row"}
        column_parts = []
        for column in LOGICAL_COLUMNS:
            sql_type = "INTEGER" if column in integer_columns else "TEXT"
            declaration = f'"{column}" {sql_type}'
            if column in required_text or column in integer_columns:
                declaration += " NOT NULL"
            column_parts.append(declaration)
        column_parts.extend(
            [
                'CHECK ("taxon_status" IN (\'정명\', \'이명\'))',
                'CHECK (length(trim("ktsn")) > 0)',
                'CHECK (length(trim("accepted_ktsn")) > 0)',
                'CHECK ("source_row" >= 1)',
            ]
        )
        columns = ", ".join(column_parts)
        conn.execute(f'CREATE TABLE "{table_name}" ({columns});')
        conn.execute(f'CREATE UNIQUE INDEX "idx_{table_name}_ktsn" ON "{table_name}" ("ktsn");')
        conn.execute(f'CREATE INDEX "idx_{table_name}_accepted_ktsn" ON "{table_name}" ("accepted_ktsn");')
        conn.execute(f'CREATE INDEX "idx_{table_name}_scientific_name_without_authority" ON "{table_name}" ("scientific_name_without_authority");')
        placeholders = ", ".join("?" for _ in LOGICAL_COLUMNS)
        column_list = ", ".join(f'"{column}"' for column in LOGICAL_COLUMNS)
        conn.executemany(
            f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders})',
            [[row.get(column) for column in LOGICAL_COLUMNS] for row in rows],
        )
        conn.execute(
            "INSERT INTO gpkg_contents (table_name, data_type, identifier) VALUES (?, ?, ?);",
            (table_name, "attributes", table_name),
        )
        conn.commit()
    finally:
        conn.close()
