"""Unit tests for qfield_builder.qgis_worker's post-MVP identification-widget helpers
(FR-QPB-101, revised; Decision Log D-31; DR-QPB-076/AC-QPB-113, Decision Log D-74).

`_identification_photo_paths_expression` is a pure function (no PyQGIS needed) that this file
tests directly. The real, PyQGIS-backed end-to-end behavior (the QgsAttributeEditorQmlElement
actually being embedded/round-tripped through a real `.qgs` project) is exercised by the
acceptance suite's `test_post_mvp_identification_plugin.py`/`test_observation_photo_removal.py`
(`qgis`-marked, requires a real bridgeable QGIS installation) -- this file covers the
survey-type-specific expression-building logic in isolation.
"""
from __future__ import annotations

from qfield_builder import qgis_worker, schemas


def test_type1_inventory_observation_expression_reads_the_three_inline_photo_fields():
    schema = schemas.get_schema("simple_inventory")
    table = schema["inventory_observation"]
    expr = qgis_worker._identification_photo_paths_expression(table)
    assert "leaf_photo_path" in expr
    assert "flower_photo_path" in expr
    assert "fruit_photo_path" in expr
    assert "array_remove_all" in expr


def test_type2_observation_expression_reads_the_three_inline_photo_fields():
    """DR-QPB-076 (Decision Log D-74): `observation_photo`/`relation_aggregate()` are removed --
    Type 2's `observation` now reads its own three inline photo-path columns directly."""
    schema = schemas.get_schema("temporary_plots")
    table = schema["observation"]
    expr = qgis_worker._identification_photo_paths_expression(table)
    assert "leaf_photo_path" in expr
    assert "flower_photo_path" in expr
    assert "fruit_photo_path" in expr
    assert "array_remove_all" in expr
    assert "relation_aggregate" not in expr
    assert "rel_observation_photo_observation" not in expr


def test_type3_observation_expression_is_identical_to_type2():
    schema_t2 = schemas.get_schema("temporary_plots")
    schema_t3 = schemas.get_schema("permanent_plots")
    expr_t2 = qgis_worker._identification_photo_paths_expression(schema_t2["observation"])
    expr_t3 = qgis_worker._identification_photo_paths_expression(schema_t3["observation"])
    assert expr_t2 == expr_t3


def test_type2_3_observation_expression_matches_type1_inventory_observation_exactly():
    """AC-QPB-113: Type 2/3's `observation` must use the identical inline-column-reading
    mechanism as Type 1's `inventory_observation` -- since all three tables declare the same
    three photo-path column names, the expressions are byte-for-byte identical, not merely
    structurally similar."""
    schema_t1 = schemas.get_schema("simple_inventory")
    schema_t2 = schemas.get_schema("temporary_plots")
    expr_t1 = qgis_worker._identification_photo_paths_expression(schema_t1["inventory_observation"])
    expr_t2 = qgis_worker._identification_photo_paths_expression(schema_t2["observation"])
    assert expr_t1 == expr_t2


def test_identification_target_layers_includes_community_for_display_only_candidates():
    assert "community" in qgis_worker.IDENTIFICATION_TARGET_LAYERS


def test_identification_target_layers_includes_inventory_observation_and_observation():
    assert "inventory_observation" in qgis_worker.IDENTIFICATION_TARGET_LAYERS
    assert "observation" in qgis_worker.IDENTIFICATION_TARGET_LAYERS
