"""Korean layer display-name mapping for generated QGIS/QField projects.

Implements DR-QPB-078/FR-QPB-130/Section 8.7 of the specification (Decision Log D-80 proposed the
mapping, responding to the stakeholder's direct question, quoted in full in Decision Log D-80:
"레이어가 표시되는 이름을 한국어로 변경할 수 있나? 예를 들어, 테이블 이름은
inventory_observation이더라도 QField에서 표시되는 이름은 식물관찰 이라던지"; Decision Log D-84
confirmed both of Section 8.7's tables in full -- every row exactly as proposed, except `site`,
corrected from "사이트" to "조사지").

Every generated domain survey-data layer -- i.e. every layer created from a `TableDef` in
`qfield_builder.schemas`, across all four survey types -- must receive a Korean-language display
name, set via `QgsMapLayer.setName()`, in place of the raw GeoPackage table name QGIS/QField
otherwise shows by default in the Layers panel/legend. Decision Log D-84 additionally extends this
same treatment to the bundled KTSN accepted-name lookup table (DR-QPB-072) -- see
`KTSN_LOOKUP_LAYER_DISPLAY_NAME` below, kept separate from `LAYER_DISPLAY_NAMES` because that table
is not a `TableDef`-backed domain survey-data layer at all.

The mapping below is keyed by table name and is a direct transcription of Section 8.7's now-fully
-confirmed table (mirrored verbatim in `tests/acceptance/qfield_project_builder/conftest.py`'s
`KOREAN_LAYER_DISPLAY_NAMES`/`KTSN_LOOKUP_LAYER_KOREAN_DISPLAY_NAME`) -- every display-name string
here must match that source exactly. A table's own confirmed Korean display name does not vary by
survey type (confirmed directly against Section 8.7: `site`/`survey`/`observation` each reuse the
identical Korean text across every survey type that declares them), so this mapping is keyed by
table name alone, not by `(survey_type, table_name)`.

This is a distinct, third UI surface from, and does not alter, `qfield_builder.korean_field_
aliases` (a field's own display alias, DR-QPB-071/FR-QPB-119/Section 8.5) or `qfield_builder.
korean_relation_display_names` (an embedded relation widget's own display name, FR-QPB-128/
Section 8.6) -- a layer's own name, a field's alias, and a relation widget's group label are three
separately configured QGIS/QField concepts.
"""
from __future__ import annotations

# {table_name: Korean display name} -- see module docstring for provenance (Section 8.7, Decision
# Log D-80/D-84). Every domain table name currently produced by `qfield_builder.schemas` across all
# four survey types is covered here (`observation_photo` is correctly absent: Decision Log D-74
# removed that table entirely for Types 2/3).
LAYER_DISPLAY_NAMES: dict[str, str] = {
    "inventory_observation": "식물관찰",
    "site": "조사지",  # Decision Log D-84 correction (originally proposed "사이트")
    "survey": "조사",
    "observation": "식물관찰",
    "survey_photo": "조사 사진",
    "plot": "고정조사구",
    "plot_photo": "고정조사구 사진",
    "community": "군락",
}

# The bundled KTSN accepted-name lookup table's own confirmed layer name (Section 8.7's separate
# "bonus row"; DR-QPB-072; Decision Log D-84's scope extension of DR-QPB-078/FR-QPB-130 to this one
# additional, non-domain layer, for every Types 1-3 generated project). Kept separate from
# `LAYER_DISPLAY_NAMES` above since this table is not a `TableDef`-backed domain survey-data layer.
KTSN_LOOKUP_LAYER_DISPLAY_NAME = "인정 국명 조회표"
KTSN_TAXONOMY_LAYER_DISPLAY_NAME = "식물 분류 참조표"


def display_name_for(table_name: str) -> str:
    """The confirmed Korean display name for `table_name` (Section 8.7), or the raw `table_name`
    itself if this mapping has no entry for it -- a defensive fallback only; every domain table
    name this application's own `qfield_builder.schemas` currently produces is covered above, so
    this fallback is not expected to be exercised in practice."""
    return LAYER_DISPLAY_NAMES.get(table_name, table_name)
