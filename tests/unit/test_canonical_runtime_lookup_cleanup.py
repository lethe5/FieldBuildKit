"""SQLite handles must be closed before returning or propagating a lookup error."""

import sqlite3
from contextlib import closing

import pytest

from qfield_builder import canonical_runtime_lookup


@pytest.mark.parametrize("outcome", ["success", "query_error", "invalid_data"])
def test_projection_closes_geopackage_before_returning(tmp_path, monkeypatch, outcome):
    gpkg = tmp_path / "project.gpkg"
    with closing(sqlite3.connect(gpkg)) as connection:
        if outcome != "query_error":
            connection.execute(
                "CREATE TABLE ktsn_taxonomy_reference ("
                "source_row INTEGER, ktsn TEXT, taxon_status TEXT, "
                "scientific_name_without_authority TEXT, accepted_ktsn TEXT, "
                "korean_name TEXT, scientific_name TEXT)"
            )
            connection.execute(
                "INSERT INTO ktsn_taxonomy_reference VALUES "
                "(1, '1', '정명', 'Plant one', '1', ?, 'Plant one')",
                ("" if outcome == "invalid_data" else "식물",),
            )
            connection.commit()

    # Retain the real handle so garbage collection cannot hide a missing close() on macOS.
    connection = sqlite3.connect(gpkg)
    monkeypatch.setattr(canonical_runtime_lookup.sqlite3, "connect", lambda _path: connection)
    try:
        if outcome == "success":
            rows = canonical_runtime_lookup._projection_rows(str(gpkg))
            assert len(rows) == 1 and rows[0]["korean_name"] == "식물"
        else:
            with pytest.raises(canonical_runtime_lookup.CanonicalRuntimeLookupBuildError):
                canonical_runtime_lookup._projection_rows(str(gpkg))
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
        gpkg.rename(tmp_path / "moved.gpkg")
    finally:
        connection.close()
