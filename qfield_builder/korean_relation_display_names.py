"""Korean relation-widget display-name mapping for generated QGIS/QField attribute forms.

Implements FR-QPB-128/Section 8.6 of the specification (Decision Log D-73 proposed the mapping,
in response to the stakeholder's verbatim report "Widget에 relation을 추가할 때
rel_observation_survey와 같은 이름으로 추가하지 말고 적절한 한국어 alias를 적용할 것"; Decision Log
D-77 confirmed six of the seven proposed names exactly as proposed and corrected the seventh,
`rel_observation_survey`, from the originally proposed "관찰" to the stakeholder's actual confirmed
term, "식물관찰").

Every relation embedded as a `QgsAttributeEditorRelation` widget in a parent record's own
attribute form (FR-QPB-056/FR-QPB-057) must receive a Korean display name via the relation's own
separate, human-facing "name" property (`QgsRelation.setName()`) -- never the relation's own
stable `id()` (`QgsRelation.setId()`), which remains completely unchanged (FR-QPB-056; depended on
by `relation_aggregate()` expressions elsewhere and by `_add_relations()`'s own returned
`relation_ids_by_parent` mapping).

The mapping below is keyed by relation ID and is a direct transcription of Section 8.6's now-fully
-confirmed table (mirrored verbatim in `tests/acceptance/qfield_project_builder/conftest.py`'s
`KOREAN_RELATION_DISPLAY_NAMES`) -- every display-name string here must match that source exactly.

`rel_observation_photo_observation` is deliberately absent from this mapping, not merely
unreferenced: Section 8.6 explicitly excludes it (proposing a Korean name for it would be moot),
since Decision Log D-74 -- a separate, related change -- removes the `observation_photo` table,
and therefore this relation, entirely for Type 2/3 (see `qfield_builder.schemas`). No relation ID
currently produced by `qfield_builder.schemas` is missing from this mapping (confirmed directly
against every `ForeignKeyDef(relation_id=...)` value in that module).
"""
from __future__ import annotations

# {relation_id: Korean display name} -- see module docstring for provenance (Section 8.6, Decision
# Log D-73/D-77).
RELATION_DISPLAY_NAMES: dict[str, str] = {
    "rel_survey_site": "조사",
    "rel_observation_survey": "식물관찰",  # Decision Log D-77 correction (originally "관찰")
    "rel_survey_photo_survey": "조사 사진",
    "rel_plot_site": "고정조사구",
    "rel_survey_plot": "조사",
    "rel_plot_photo_plot": "고정조사구 사진",
    "rel_community_survey": "군락",
}


def display_name_for(relation_id: str) -> str:
    """The confirmed Korean display name for `relation_id` (Section 8.6), or the raw
    `relation_id` itself if this mapping has no entry for it -- a defensive fallback only; every
    relation ID this application's own `qfield_builder.schemas` currently produces is covered
    above, so this fallback is not expected to be exercised in practice."""
    return RELATION_DISPLAY_NAMES.get(relation_id, relation_id)
