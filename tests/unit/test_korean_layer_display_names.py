"""Unit tests for `qfield_builder.korean_layer_display_names` (DR-QPB-078/FR-QPB-130/Section 8.7;
Decision Log D-80/D-84).

Pure-Python tests of the layer-display-name lookup table itself -- no PyQGIS needed. The real,
PyQGIS-backed end-to-end behavior (an actual `.qgs` project's layers carrying these names after
generation) is exercised by `test_qgis_worker_layer_display_names.py` (`qgis`-marked/skipped
without a bridgeable QGIS installation) and by the acceptance suite's
`test_korean_layer_display_names.py`.

The expected values below are transcribed directly from
`tests/acceptance/qfield_project_builder/conftest.py`'s `KOREAN_LAYER_DISPLAY_NAMES`/
`KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME` (the acceptance-test suite's own authoritative source,
confirmed to agree with Section 8.7 of the specification) so that a mismatch here fails loudly
rather than only surfacing much later, in the slower, real-QGIS-backed acceptance run.
"""
from __future__ import annotations

from qfield_builder import korean_layer_display_names, schemas


def test_every_table_name_produced_by_schemas_has_a_display_name():
    """No domain table name currently produced by `qfield_builder.schemas` may be missing from the
    mapping (DR-QPB-078/FR-QPB-130)."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        for table_name in schema:
            display_name = korean_layer_display_names.display_name_for(table_name)
            assert display_name, f"{survey_type}.{table_name}: no Korean display name configured"
            assert display_name != table_name, (
                f"{survey_type}.{table_name}: display name must not be the raw table name itself"
            )


def test_observation_photo_is_not_produced_by_schemas():
    """Decision Log D-74 removed the `observation_photo` table entirely for Type 2/3; Section 8.7
    correctly has no entry for it, since this application's own schema never produces it."""
    for survey_type in schemas.SURVEY_TYPES:
        schema = schemas.get_schema(survey_type)
        assert "observation_photo" not in schema


def test_display_name_for_falls_back_to_the_raw_table_name_for_an_unknown_table():
    """Defensive fallback: a table name Section 8.7 does not cover must never receive an invented
    Korean name -- `display_name_for` returns the raw table name unchanged in that case."""
    assert korean_layer_display_names.display_name_for("not_in_section_8_7") == "not_in_section_8_7"


# --- Spot-check every proposed layer name against Section 8.7's confirmed table, one by one,
# mirroring `test_korean_relation_display_names.py`'s own per-value spot-check convention. --------


def test_inventory_observation_is_sikmulgwanchal():
    assert korean_layer_display_names.display_name_for("inventory_observation") == "식물관찰"


def test_site_is_the_decision_log_d84_corrected_term():
    """Decision Log D-84 correction: the Decision Log D-80 draft proposal read "사이트"; the
    stakeholder's actual confirmed term is "조사지"."""
    assert korean_layer_display_names.display_name_for("site") == "조사지"


def test_survey_is_josa():
    assert korean_layer_display_names.display_name_for("survey") == "조사"


def test_observation_is_sikmulgwanchal():
    assert korean_layer_display_names.display_name_for("observation") == "식물관찰"


def test_survey_photo_is_josa_sajin():
    assert korean_layer_display_names.display_name_for("survey_photo") == "조사 사진"


def test_plot_is_gojeong_josagu():
    assert korean_layer_display_names.display_name_for("plot") == "고정조사구"


def test_plot_photo_is_gojeong_josagu_sajin():
    assert korean_layer_display_names.display_name_for("plot_photo") == "고정조사구 사진"


def test_community_is_gullak():
    assert korean_layer_display_names.display_name_for("community") == "군락"


def test_ktsn_lookup_layer_display_name_is_injeong_gungmyeong_johoepyo():
    assert korean_layer_display_names.KTSN_LOOKUP_LAYER_DISPLAY_NAME == "인정 국명 조회표"
