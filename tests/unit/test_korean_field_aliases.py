"""Unit tests for `qfield_builder.korean_field_aliases` (DR-QPB-071/FR-QPB-119/Section 8.5;
Decision Log D-56/D-57/D-58).

Pure-Python tests of the alias-lookup table itself -- no PyQGIS needed. The real, PyQGIS-backed
end-to-end behavior (an actual `.qgs` layer's fields carrying these aliases after generation) is
exercised by `test_qgis_worker_field_aliases.py` (`qgis`-marked/skipped without a bridgeable QGIS
installation) and by the acceptance suite's `test_korean_field_aliases.py`.

The expected values below are transcribed directly from
`tests/acceptance/qfield_project_builder/conftest.py`'s `KOREAN_FIELD_ALIASES` map (the
acceptance-test suite's own authoritative source, confirmed to agree with Section 8.5 of the
specification) so that a mismatch here fails loudly rather than only surfacing much later, in the
slower, real-QGIS-backed acceptance run.
"""
from __future__ import annotations

from qfield_builder import korean_field_aliases, schemas


def test_uuid_primary_key_columns_have_no_alias_table_entry():
    """DR-QPB-071: a UUID primary-key column must never be looked up at all by
    `_configure_widget_for_column` (which returns before reaching the alias-setting step for
    `col.is_uuid_pk` columns) -- but as a defensive double-check, no primary-key column name is
    accidentally present in any table's alias dict either."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        for table_name, table_def in schema.items():
            table_aliases = korean_field_aliases.FIELD_ALIASES_BY_TABLE.get(table_name, {})
            assert table_def.uuid_pk not in table_aliases, (
                f"{table_name}.{table_def.uuid_pk} is this table's own UUID primary key and must "
                f"not appear as an alias-table entry (DR-QPB-071)"
            )


def test_every_non_uuid_pk_column_across_every_survey_type_has_an_alias():
    """FR-QPB-119: every remaining (non-UUID-primary-key) column on every table of every survey
    type must resolve to a non-empty Korean alias, and that alias must never equal the raw
    snake_case column name."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        for table_name, table_def in schema.items():
            for col in table_def.columns:
                if col.is_uuid_pk:
                    continue
                alias = korean_field_aliases.alias_for(table_name, col.name)
                assert alias, f"{table_name}.{col.name} has no Korean alias configured"
                assert alias != col.name, (
                    f"{table_name}.{col.name} alias must not be the raw column name"
                )


def test_alias_for_returns_none_for_an_unknown_table():
    assert korean_field_aliases.alias_for("no_such_table", "site_name") is None


def test_alias_for_returns_none_for_an_unknown_column_on_a_known_table():
    assert korean_field_aliases.alias_for("site", "no_such_column") is None


# --- Spot-check every alias against Section 8.5 / the acceptance test's own authoritative source
# (tests/acceptance/qfield_project_builder/conftest.py KOREAN_FIELD_ALIASES), table by table. ----

def test_inventory_observation_aliases_match_section_8_5():
    expected = {
        "observed_at": "관찰일시",
        "surveyor": "조사자",
        "selected_korean_name": "국명",
        "selected_scientific_name": "학명",
        "selected_ktsn": "KTSN",
        "identification_score": "식별 신뢰도",
        "occurrence_probability": "출현 확률",
        "identification_timestamp": "식별 일시",
        "identification_model_version": "식별 모델 버전",
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        "identification_status": "식별 상태",
        "notes": "비고",
    }
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("inventory_observation", column) == alias


def test_site_aliases_match_section_8_5():
    assert korean_field_aliases.alias_for("site", "site_name") == "사이트명"


def test_survey_aliases_match_section_8_5():
    expected = {
        "site_id": "사이트",
        "plot_id": "고정조사구",  # Decision Log D-58
        "survey_date": "조사일자",
        "surveyor": "조사자",
        "plot_size": "조사구 크기",
    }
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("survey", column) == alias


def test_observation_aliases_match_section_8_5():
    expected = {
        "survey_id": "조사",
        "selected_korean_name": "국명",
        "selected_scientific_name": "학명",
        "selected_ktsn": "KTSN",
        "cover": "피도",
        "identification_score": "식별 신뢰도",
        "occurrence_probability": "출현 확률",
        "identification_status": "식별 상태",
        "identification_timestamp": "식별 일시",
        "identification_model_version": "식별 모델 버전",
        # DR-QPB-077 (Decision Log D-74, 2026-08-28): reuses Type 1's `inventory_observation`
        # aliases verbatim, replacing the now-removed `observation_photo` child table.
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        "notes": "비고",
    }
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("observation", column) == alias


def test_survey_photo_aliases_match_section_8_5():
    expected = {"survey_id": "조사", "path": "사진", "captured_at": "촬영일시", "notes": "비고"}
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("survey_photo", column) == alias


def test_observation_photo_table_no_longer_has_any_aliases():
    """Decision Log D-74 (2026-08-28): `observation_photo` is removed entirely for Type 2/3 --
    its own alias-table entry is removed too (see `observation`'s three new photo-path aliases
    above, which replace it), so any lookup against it now resolves to `None`."""
    for column in ("observation_id", "path", "organ", "captured_at"):
        assert korean_field_aliases.alias_for("observation_photo", column) is None


def test_plot_aliases_match_section_8_5():
    expected = {"site_id": "사이트", "plot_name": "고정조사구명", "plot_size": "조사구 크기"}
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("plot", column) == alias


def test_plot_photo_aliases_match_section_8_5_and_decision_log_d58():
    expected = {
        "plot_id": "고정조사구",
        "path": "사진",
        "captured_at": "촬영일시",
        "notes": "비고",
    }
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("plot_photo", column) == alias


def test_community_aliases_match_section_8_5():
    expected = {
        "survey_id": "조사",
        "community_name": "군락명",
        "dominant_species": "우점종",
        "subdominant_species": "차우점종",
        "is_field_checked": "현장 확인 여부",
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        "notes": "비고",
    }
    for column, alias in expected.items():
        assert korean_field_aliases.alias_for("community", column) == alias
