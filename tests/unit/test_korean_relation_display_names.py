"""Unit tests for `qfield_builder.korean_relation_display_names` (FR-QPB-128/Section 8.6;
Decision Log D-73/D-77).

Pure-Python tests of the relation-display-name lookup table itself -- no PyQGIS needed. The real,
PyQGIS-backed end-to-end behavior (an actual `.qgs` project's relations carrying these names after
generation) is exercised by `test_qgis_worker_relations.py` (`qgis`-marked/skipped without a
bridgeable QGIS installation) and by the acceptance suite's
`test_korean_relation_display_names.py`.

The expected values below are transcribed directly from
`tests/acceptance/qfield_project_builder/conftest.py`'s `KOREAN_RELATION_DISPLAY_NAMES` map (the
acceptance-test suite's own authoritative source, confirmed to agree with Section 8.6 of the
specification) so that a mismatch here fails loudly rather than only surfacing much later, in the
slower, real-QGIS-backed acceptance run.
"""
from __future__ import annotations

from qfield_builder import korean_relation_display_names, schemas


def test_every_relation_id_produced_by_schemas_has_a_display_name():
    """No relation ID currently produced by `qfield_builder.schemas` may be missing from the
    mapping -- every `ForeignKeyDef(relation_id=...)` value across every survey type must resolve
    to a configured Korean display name (FR-QPB-128)."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        for table_name, table_def in schema.items():
            fk = table_def.foreign_key
            if fk is None:
                continue
            display_name = korean_relation_display_names.display_name_for(fk.relation_id)
            assert display_name, (
                f"{survey_type}.{table_name}: no Korean display name configured for relation "
                f"{fk.relation_id!r}"
            )
            assert display_name != fk.relation_id, (
                f"{survey_type}.{table_name}: relation {fk.relation_id!r}'s display name must "
                f"not be the raw relation-ID string itself"
            )


def test_rel_observation_photo_observation_is_not_produced_by_schemas():
    """Decision Log D-74 removed the `observation_photo` table (and therefore
    `rel_observation_photo_observation`) entirely for Type 2/3; Section 8.6/Decision Log D-73
    deliberately excludes this relation from its Korean-display-name proposal because proposing a
    name for it would be moot. This is a defensive double-check that no schema currently produces
    it -- if one ever did, `display_name_for` would fall back to the raw ID rather than inventing
    an unconfirmed Korean name, per this module's own documented fallback behavior."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        for table_def in schema.values():
            fk = table_def.foreign_key
            if fk is None:
                continue
            assert fk.relation_id != "rel_observation_photo_observation"


def test_display_name_for_falls_back_to_the_raw_id_for_an_unknown_relation():
    """Defensive fallback: a relation ID Section 8.6 does not cover must never receive an
    invented Korean name -- `display_name_for` returns the raw ID unchanged in that case."""
    assert korean_relation_display_names.display_name_for("rel_not_in_section_8_6") == (
        "rel_not_in_section_8_6"
    )


# --- Spot-check every proposed relation name against Section 8.6's confirmed table, one by one,
# mirroring `test_korean_field_aliases.py`'s own per-value spot-check convention. -----------------

def test_rel_survey_site_is_josa():
    assert korean_relation_display_names.display_name_for("rel_survey_site") == "조사"


def test_rel_observation_survey_is_the_decision_log_d77_corrected_term():
    """Decision Log D-77 correction: the Decision Log D-73 draft proposal read "관찰"; the
    stakeholder's actual confirmed term is "식물관찰"."""
    assert korean_relation_display_names.display_name_for("rel_observation_survey") == "식물관찰"


def test_rel_survey_photo_survey_is_josa_sajin():
    assert korean_relation_display_names.display_name_for("rel_survey_photo_survey") == "조사 사진"


def test_rel_plot_site_is_gojeong_josagu():
    assert korean_relation_display_names.display_name_for("rel_plot_site") == "고정조사구"


def test_rel_survey_plot_is_josa():
    assert korean_relation_display_names.display_name_for("rel_survey_plot") == "조사"


def test_rel_plot_photo_plot_is_gojeong_josagu_sajin():
    assert (
        korean_relation_display_names.display_name_for("rel_plot_photo_plot")
        == "고정조사구 사진"
    )


def test_rel_community_survey_is_gullak():
    assert korean_relation_display_names.display_name_for("rel_community_survey") == "군락"
