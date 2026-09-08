"""Type 2/3's `observation_photo` removal and its three-inline-photo-path-field replacement
(Section 8.2/8.3, DR-QPB-074-077; Decision Log D-74, confirmed 2026-08-28; migration/backward-
compatibility scope explicitly closed by Decision Log D-78).

Covers:
- AC-QPB-112 (new; Decision Log D-74): given a generated Type 2 or Type 3 project, when its
  GeoPackage schema is inspected, then no `observation_photo` table exists anywhere in it, and the
  `observation` table instead has exactly three optional, nullable columns —
  `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` — each configured with the Attachment
  (`ExternalResource`) editor widget and the Korean-language alias already confirmed for Type 1's
  identical column names (Section 8.5, Decision Log D-56-D-58); and given the same project's Type
  3 `plot_photo` table (if applicable) or Type 2 `survey_photo` table, when inspected, then each
  remains fully present and unaffected by this criterion.
- AC-QPB-113 (post-MVP; new; Decision Log D-74): given a generated Type 2 or Type 3 project with
  the identification subsystem enabled, when the embedded "Identify attached photos" widget's own
  photo-path-reading expression (`_identification_photo_paths_expression`,
  `qfield_builder/qgis_worker.py`) is inspected for the `observation` layer, then it reads the same
  three inline photo-path columns directly -- identically to Type 1's `inventory_observation` --
  and contains no `relation_aggregate()` expression referencing
  `rel_observation_photo_observation` (a relation which, per AC-QPB-112, no longer exists for
  these survey types).
- AC-QPB-114 (new; Decision Log D-74; mirrors AC-QPB-008 for Type 2/3): given a Type 2 or Type 3
  `observation` record with zero, one, two, or three of `leaf_photo_path`/`flower_photo_path`/
  `fruit_photo_path` populated, when the record is saved, then it is accepted in every case -- no
  photo is required to complete an observation of either type.
- Type 3's `plot_photo` table (photos of the permanent `plot` itself, not of an individual
  `observation`) and Type 2's `survey_photo` table remain structurally distinct. Type 4's
  `community` table also uses the same three inline optional photo paths, but no photo child table.
- Per Decision Log D-78: this change applies only to newly generated projects going forward -- no
  migration/backward-compatibility path for an already-generated project using the old
  `observation_photo` schema is required or tested for anywhere in this file, by design (see the
  module-level note near the bottom of this file).

**What this file does not re-test.** The Korean-alias half of AC-QPB-112 (the three new fields
carry 잎 사진/꽃 사진/열매 사진, exactly matching Type 1's own confirmed aliases) is not repeated
here: it is already fully exercised by `test_korean_field_aliases.py`'s existing, data-driven
`test_ac098_in_scope_field_has_the_exact_confirmed_korean_alias`/
`test_every_layer_field_is_accounted_for_by_exactly_one_alias_expectation` tests, which this round
extended by updating `KOREAN_FIELD_ALIASES` in `conftest.py` (adding the three new fields to
`observation`'s entry, removing the now-obsolete `observation_photo` table entries for
`temporary_plots`/`permanent_plots`) rather than by duplicating a parallel alias assertion in this
new file. See `../qfield_project_builder_observation_photo_removal.traceability.md` for the full
mapping, including why this is a deliberate non-duplication decision, not a coverage gap.

0.2.8: attachment and embedded-QML structure is read directly from generated QGS XML.
This keeps structural checks independent of external PyQGIS; it does not replace device tests.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config, open_gpkg, user_tables

_PHOTO_PATH_FIELDS = ("leaf_photo_path", "flower_photo_path", "fruit_photo_path")

_PHOTO_PATHS_EXPRESSION_RE = re.compile(r'expression\.evaluate\("(.*?)"\)')


def _build_with_identification(acceptance_api, tmp_path, survey_type: str, label: str):
    config = make_base_config(survey_type, display_name="관찰 사진 이전 테스트 프로젝트")
    config["identification_enabled"] = True
    out_dir = tmp_path / f"proj_{label}"
    return acceptance_api.build_project(config, str(out_dir))


def _extract_photo_paths_expression(qml_code: str) -> str:
    match = _PHOTO_PATHS_EXPRESSION_RE.search(qml_code or "")
    assert match, (
        "expected the embedded identification widget's qpbCurrentPhotoPaths() to call "
        f"expression.evaluate(\"...\") with a literal expression string; got qml_code={qml_code!r}"
    )
    return match.group(1)


def _create_survey_for_observation(acceptance_api, project_dir, gpkg_path, survey_type, geom_wkt):
    """Builds the minimal valid parent chain an `observation` record needs (`survey`, plus, for
    Type 3, the intermediate `plot`), returning the created `survey_id`. Mirrors the parent-chain
    pattern already established in `test_geopackage_schema_by_type.py`
    (`test_cover_within_0_100_is_accepted`)."""
    conn = open_gpkg(gpkg_path)
    try:
        site_id = conn.execute("SELECT site_id FROM site LIMIT 1;").fetchone()[0]
    finally:
        conn.close()

    if survey_type == "temporary_plots":
        survey_outcome = acceptance_api.attempt_feature_save(
            project_dir,
            "survey",
            {"surveyor": "Field Researcher", "plot_size": "5m x 5m", "site_id": site_id},
            geometry_wkt=geom_wkt,
        )
    else:
        plot_outcome = acceptance_api.attempt_feature_save(
            project_dir,
            "plot",
            {"plot_name": "Plot AC-112/114", "plot_size": "10m x 10m", "site_id": site_id},
            geometry_wkt=geom_wkt,
        )
        assert plot_outcome["accepted"], plot_outcome
        survey_outcome = acceptance_api.attempt_feature_save(
            project_dir,
            "survey",
            {"surveyor": "Field Researcher", "plot_id": plot_outcome["generated_uuid"]},
        )
    assert survey_outcome["accepted"], survey_outcome
    return survey_outcome["generated_uuid"]


# --- AC-QPB-112 (schema shape: observation_photo removed, observation gains 3 photo columns) ----


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac112_observation_photo_table_no_longer_exists(built_project_by_type, survey_type):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    conn = open_gpkg(result["gpkg_path"])
    try:
        tables = user_tables(conn)
        assert "observation_photo" not in tables, (
            f"AC-QPB-112: observation_photo must no longer exist anywhere in a generated "
            f"{survey_type} project's GeoPackage (DR-QPB-076/Decision Log D-74); found "
            f"tables={tables}"
        )
    finally:
        conn.close()


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac112_observation_has_exactly_three_optional_nullable_photo_path_columns(
    built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    conn = open_gpkg(result["gpkg_path"])
    try:
        columns = {
            row[1]: row for row in conn.execute("PRAGMA table_info(observation);").fetchall()
        }
        for expected_col in _PHOTO_PATH_FIELDS:
            assert expected_col in columns, (
                f"AC-QPB-112: expected {expected_col} on {survey_type}.observation "
                f"(DR-QPB-074), got columns={sorted(columns)}"
            )
            _, _name, _coltype, notnull, _default, _pk = columns[expected_col]
            assert notnull == 0, f"{expected_col} must be nullable/optional (DR-QPB-074/075)"
        # `organ` (DR-QPB-032) existed only on the now-removed `observation_photo` table; it must
        # not have been reintroduced anywhere on `observation` itself by this replacement.
        assert "organ" not in columns, (
            "DR-QPB-074/DR-QPB-032 (superseded): observation must not carry an `organ` column -- "
            "the field name alone identifies the organ, mirroring Type 1's inventory_observation"
        )
    finally:
        conn.close()


@pytest.mark.parametrize(
    "survey_type,unaffected_photo_table,unaffected_relation_id,unaffected_fk_column",
    [
        ("temporary_plots", "survey_photo", "rel_survey_photo_survey", "survey_id"),
        ("permanent_plots", "plot_photo", "rel_plot_photo_plot", "plot_id"),
    ],
)
def test_ac112_sibling_photo_table_and_relation_are_completely_unaffected(
    built_project_by_type,
    survey_type,
    unaffected_photo_table,
    unaffected_relation_id,
    unaffected_fk_column,
):
    """(e): Type 2's `survey_photo` / Type 3's `plot_photo` -- structurally distinct tables from
    the removed `observation_photo` -- must remain fully present and unaffected."""
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    conn = open_gpkg(result["gpkg_path"])
    try:
        tables = user_tables(conn)
        assert unaffected_photo_table in tables, (
            f"{unaffected_photo_table} must remain present, unaffected by the Type 2/3 "
            f"observation_photo removal (Decision Log D-74): found tables={tables}"
        )
        fk_list = conn.execute(f"PRAGMA foreign_key_list({unaffected_photo_table});").fetchall()
        assert any(row[3] == unaffected_fk_column for row in fk_list), (
            f"{unaffected_photo_table} must still declare its own foreign key on "
            f"{unaffected_fk_column}: {fk_list}"
        )
    finally:
        conn.close()

    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8")
    assert unaffected_relation_id in qgs_text, (
        f"expected the unaffected relation {unaffected_relation_id!r} to still be present in the "
        f"generated .qgs project for {survey_type}"
    )


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac112_rel_observation_photo_observation_relation_no_longer_exists(
    built_project_by_type, survey_type
):
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")
    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8")
    assert "rel_observation_photo_observation" not in qgs_text, (
        "AC-QPB-112: the rel_observation_photo_observation relation must no longer exist "
        f"anywhere in the generated .qgs project for {survey_type} "
        "(DR-QPB-076/Decision Log D-74)"
    )


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
@pytest.mark.parametrize("field", _PHOTO_PATH_FIELDS)
def test_ac112_observation_photo_fields_use_the_same_attachment_widget_as_type1(
    project_layer_xml, built_project_by_type, survey_type, field
):
    """AC-QPB-112: the Attachment (`ExternalResource`) editor widget, matching
    `inventory_observation`'s own existing widget configuration exactly."""
    type1_result = built_project_by_type("simple_inventory")
    assert type1_result["success"], type1_result.get("error_message")
    type23_result = built_project_by_type(survey_type)
    assert type23_result["success"], type23_result.get("error_message")

    for result, table in ((type1_result, "inventory_observation"), (type23_result, "observation")):
        layer = project_layer_xml(result, table)
        widget = layer.find(f"./fieldConfiguration/field[@name='{field}']/editWidget")
        assert widget is not None and widget.get("type") == "ExternalResource"
        editable = layer.find(f"./editable/field[@name='{field}']")
        assert editable is None or editable.get("editable") == "1"
        default = layer.find(f"./defaults/default[@field='{field}']")
        assert default is None or not default.get("expression")


# --- AC-QPB-114 (0/1/2/3 of the 3 photo fields populated is always accepted; mirrors AC-QPB-008) -


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
@pytest.mark.parametrize(
    "photo_fields",
    [
        {},
        {"leaf_photo_path": "attachments/leaf1.jpg"},
        {"leaf_photo_path": "attachments/leaf1.jpg", "flower_photo_path": "attachments/fl1.jpg"},
        {
            "leaf_photo_path": "attachments/leaf1.jpg",
            "flower_photo_path": "attachments/fl1.jpg",
            "fruit_photo_path": "attachments/fr1.jpg",
        },
    ],
    ids=["zero_photos", "one_photo", "two_photos", "three_photos"],
)
def test_ac114_type2_3_observation_photo_field_combinations_are_all_accepted(
    acceptance_api, isolated_project_by_type, survey_type, photo_fields
):
    """Uses `isolated_project_by_type` (not the shared `built_project_by_type` cache), mirroring
    `test_geopackage_schema_by_type.py::test_ac008_type1_photo_field_combinations_are_all_
    accepted`: this test deliberately saves photo paths never written to disk, which would
    otherwise leave a permanently broken attachment reference behind in the session-shared
    project for other tests to trip over.

    Deliberately reads the saved row back from the GeoPackage (not merely asserting
    `outcome["accepted"]`): `attempt_feature_save`'s own implementation silently drops any
    attribute key that does not match a real field on the layer (see
    `qfield_builder/feature_save.py`'s `attribute_map` construction) -- so, against the
    not-yet-updated schema (`observation` without the three new photo-path columns), this test
    would otherwise pass *vacuously* (the unknown `leaf_photo_path`/etc. keys silently ignored,
    the remaining valid attributes alone already sufficient for acceptance) rather than failing
    red for a genuinely not-yet-implemented feature, defeating the purpose of this acceptance
    test. Reading the value back forces the three columns to actually exist and actually store
    what was written.
    """
    result = isolated_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    survey_id = _create_survey_for_observation(
        acceptance_api,
        result["project_dir"],
        result["gpkg_path"],
        survey_type,
        geom_wkt="POINT(127.012 37.012)",
    )

    attributes = {
        "cover": 10,
        "selected_scientific_name": "Test taxon",
        "survey_id": survey_id,
        **photo_fields,
    }
    outcome = acceptance_api.attempt_feature_save(result["project_dir"], "observation", attributes)
    assert outcome["accepted"] is True, (
        f"AC-QPB-114: a {survey_type} observation with photo fields {sorted(photo_fields)} must "
        f"be accepted in every case (DR-QPB-075), got {outcome}"
    )
    observation_id = outcome["generated_uuid"]
    assert observation_id, "attempt_feature_save must report the generated UUID"

    conn = open_gpkg(result["gpkg_path"])
    try:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(observation);").fetchall()
        }
        missing = set(_PHOTO_PATH_FIELDS) - columns
        assert not missing, (
            f"AC-QPB-114/AC-QPB-112: observation is missing the photo-path column(s) {missing} "
            f"needed to actually persist {photo_fields!r} (DR-QPB-074) -- found columns={columns}"
        )
        row = conn.execute(
            "SELECT leaf_photo_path, flower_photo_path, fruit_photo_path FROM observation "
            "WHERE observation_id = ?;",
            (observation_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"expected to find the saved observation row {observation_id!r}"
    stored = dict(zip(_PHOTO_PATH_FIELDS, row, strict=True))
    for field in _PHOTO_PATH_FIELDS:
        assert stored[field] == photo_fields.get(field), (
            f"AC-QPB-114: {survey_type}.observation.{field} must actually persist the value "
            f"supplied at save time (or remain NULL when omitted): expected "
            f"{photo_fields.get(field)!r}, got {stored[field]!r}"
        )


# --- AC-QPB-113 (post-MVP): identification photo-paths expression matches Type 1's mechanism -----


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac113_observation_identification_expression_reads_inline_columns_not_relation_aggregate(
    acceptance_api, project_layer_xml, tmp_path, survey_type
):
    result = _build_with_identification(acceptance_api, tmp_path, survey_type, label=survey_type)
    assert result["success"], result.get("error_message")

    layer = project_layer_xml(result, "observation")
    widget = layer.find("./attributeEditorForm//attributeEditorQmlElement")
    assert widget is not None
    expr = _extract_photo_paths_expression(widget.text)

    assert "relation_aggregate" not in expr, (
        f"AC-QPB-113: {survey_type}.observation's photo-paths expression must no longer use "
        f"relation_aggregate() (DR-QPB-076): got expr={expr!r}"
    )
    assert "rel_observation_photo_observation" not in expr, (
        f"AC-QPB-113: {survey_type}.observation's photo-paths expression must not reference the "
        f"now-removed rel_observation_photo_observation relation: got expr={expr!r}"
    )
    for field in _PHOTO_PATH_FIELDS:
        assert field in expr, (
            f"AC-QPB-113: expected {survey_type}.observation's photo-paths expression to read "
            f"{field} directly (inline column, identically to Type 1): got expr={expr!r}"
        )


@pytest.mark.parametrize("survey_type", ["temporary_plots", "permanent_plots"])
def test_ac113_observation_expression_matches_type1_inline_mechanism_shape(
    acceptance_api, project_layer_xml, tmp_path, survey_type
):
    """Stronger companion to the test above: AC-QPB-113's own text says the expression must read
    the three inline columns "identically to Type 1's inventory_observation" -- not merely "not
    via relation_aggregate." This asserts the two expressions share the identical structural shape
    once the three field names are normalized away, i.e. the exact same mechanism/code path is
    used for both tables, mirroring DR-QPB-076's "no relation_aggregate() branch remaining for any
    table in IDENTIFICATION_TARGET_LAYERS" wording (a single, table-name-agnostic mechanism, not
    two different inline-reading implementations that happen to both avoid relation_aggregate)."""
    type1_result = _build_with_identification(
        acceptance_api, tmp_path, "simple_inventory", label=f"type1_{survey_type}"
    )
    assert type1_result["success"], type1_result.get("error_message")
    type23_result = _build_with_identification(
        acceptance_api, tmp_path, survey_type, label=f"type23_{survey_type}"
    )
    assert type23_result["success"], type23_result.get("error_message")

    type1_widget = project_layer_xml(type1_result, "inventory_observation").find("./attributeEditorForm//attributeEditorQmlElement")
    type23_widget = project_layer_xml(type23_result, "observation").find("./attributeEditorForm//attributeEditorQmlElement")
    assert type1_widget is not None and type23_widget is not None
    type1_expr = _extract_photo_paths_expression(type1_widget.text)
    type23_expr = _extract_photo_paths_expression(type23_widget.text)

    def _normalize(expr: str) -> str:
        normalized = expr
        for i, field in enumerate(_PHOTO_PATH_FIELDS):
            normalized = normalized.replace(field, f"__PHOTO_FIELD_{i}__")
        return normalized

    assert _normalize(type23_expr) == _normalize(type1_expr), (
        "AC-QPB-113: Type 2/3's observation photo-paths expression must use the identical "
        "inline-column-reading mechanism as Type 1's inventory_observation (DR-QPB-076), with "
        f"only the field names differing: inventory_observation expr={type1_expr!r}, "
        f"observation expr={type23_expr!r}"
    )


# --- Type 4 uses the same inline photo-path storage, but never candidate write-back ------------


def test_type4_community_has_inline_photo_paths_without_photo_child_table(built_project_by_type):
    """Type 4 identifies attached community photos, while retaining its no-child-photo-table schema."""
    result = built_project_by_type("vegetation_mapping")
    assert result["success"], result.get("error_message")
    conn = open_gpkg(result["gpkg_path"])
    try:
        tables = user_tables(conn)
        assert "observation_photo" not in tables
        assert not any(t.endswith("_photo") for t in tables), (
            f"Type 4 (vegetation_mapping) must have no photo table of any kind: {tables}"
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(community);").fetchall()
        }
        assert set(_PHOTO_PATH_FIELDS) <= columns, (
            f"Type 4's community table must carry its inline photo paths: {sorted(columns)}"
        )
    finally:
        conn.close()


# --- Deliberately not tested: migration/backward-compatibility (Decision Log D-78, closes O-37) --
#
# Decision Log D-78 is the stakeholder's explicit, direct answer that this change applies only to
# newly generated projects going forward: "no migration path, no backward-compatibility mechanism,
# and no handling of any already-generated Type 2/3 project still using the old observation_photo
# schema is required or in scope." Per this project's ambiguity-handling procedure (do not invent
# behavior the specification does not define), no test in this file (or anywhere else in this
# round) exercises, or asserts the presence or absence of, any migration/dual-schema-read/upgrade
# mechanism for an already-generated project. Every test above builds only newly generated
# projects via `build_project()`/`built_project_by_type`/`isolated_project_by_type`, never against
# a pre-existing, hand-constructed "old-schema" project fixture.
