"""Korean field-alias mapping for generated QGIS/QField attribute forms.

Implements DR-QPB-071/FR-QPB-119/Section 8.5 of the specification (Decision Log D-56, confirmed
by D-57/D-58): every attribute field on every layer of a generated project must carry a
Korean-language display alias, set via QGIS's field-alias mechanism, *except* a table's own UUID
primary-key field (already `Hidden`/read-only per DR-QPB-005/FR-QPB-057 -- see
`qfield_builder.qgis_worker._configure_widget_for_column`, which is the sole caller of
:func:`alias_for` and is responsible for excluding the primary-key case before ever calling it).

The mapping below is keyed by table name, then by column name, and is a direct transcription of
Section 8.5's now-fully-confirmed table (mirrored verbatim in
`tests/acceptance/qfield_project_builder/conftest.py`'s `KOREAN_FIELD_ALIASES`) -- every alias
string here must match that source exactly. A table entry lists every non-UUID-primary-key column
that table can have across any survey type it appears in (e.g. `survey` appears, with different
column subsets, in Types 2/3/4; this module's `survey` entry is the union of all of them). Because
`qfield_builder.schemas` only ever asks for the alias of a column that actually exists on the
`TableDef` being built, a superset dict here is safe -- a lookup simply never happens for a column
absent from a given survey type's own table definition.

`fid` (the hidden GeoPackage physical key) and geometry columns are correctly absent from this
module entirely: neither is ever modeled as a `schemas.ColumnDef` in the first place (DR-QPB-002;
Section 8.5's own scoping note), so `_configure_widget_for_column` never calls into this module for
either of them.
"""
from __future__ import annotations

# Shared by both `observation` (Type 2/3) and, in part, `inventory_observation` (Type 1) -- see
# Section 8.5's own "identical to Type 1" cross-references.
_IDENTIFICATION_ALIASES = {
    "selected_korean_name": "국명",
    "selected_scientific_name": "학명",
    "selected_ktsn": "KTSN",
    "identification_score": "식별 신뢰도",
    "occurrence_probability": "출현 확률",
    "identification_timestamp": "식별 일시",
    "identification_model_version": "식별 모델 버전",
    "identification_status": "식별 상태",
    "notes": "비고",
}

# {table_name: {column_name: Korean alias}} -- see module docstring for the "union across survey
# types" note on why a single flat per-table dict, rather than a per-survey-type dict, is correct.
FIELD_ALIASES_BY_TABLE: dict[str, dict[str, str]] = {
    "inventory_observation": {
        "observed_at": "관찰일시",
        "surveyor": "조사자",
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        **_IDENTIFICATION_ALIASES,
    },
    "site": {
        "site_name": "사이트명",
    },
    "survey": {
        "site_id": "사이트",  # Type 2/4 foreign key to `site`
        "plot_id": "고정조사구",  # Type 3 foreign key to `plot` (Decision Log D-58)
        "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
        "survey_date": "조사일자",
        "surveyor": "조사자",
        "plot_size": "조사구 크기",  # Type 2 only
    },
    "observation": {
        "survey_id": "조사",
        "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
        "cover": "피도",
        # DR-QPB-077 (Decision Log D-74, 2026-08-28): reuses Type 1's `inventory_observation`
        # aliases verbatim -- these replace the now-removed `observation_photo` child table for
        # Type 2/3.
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        **_IDENTIFICATION_ALIASES,
    },
    "survey_photo": {
        "survey_id": "조사",
        "path": "사진",
        "captured_at": "촬영일시",
        "notes": "비고",
    },
    # `observation_photo` is deliberately absent (Decision Log D-74, 2026-08-28): the table itself
    # no longer exists for Type 2/3 -- see `observation`'s three new photo-path aliases above,
    # which replace it. Removed entirely, not merely struck through, since this is executable
    # code, mirroring `tests/acceptance/qfield_project_builder/conftest.py`'s identical treatment.
    "plot": {
        "site_id": "사이트",
        "qpb_plot_geometry_wkt": "조사구 위치 정보 (자동)",
        "plot_name": "고정조사구명",
        "plot_size": "조사구 크기",
    },
    "plot_photo": {
        "plot_id": "고정조사구",  # Decision Log D-58, same as survey.plot_id above
        "path": "사진",
        "captured_at": "촬영일시",
        "notes": "비고",
    },
    "community": {
        "survey_id": "조사",
        "community_name": "군락명",
        "dominant_species": "우점종",
        "subdominant_species": "차우점종",
        "is_field_checked": "현장 확인 여부",
        "leaf_photo_path": "잎 사진",
        "flower_photo_path": "꽃 사진",
        "fruit_photo_path": "열매 사진",
        "notes": "비고",
    },
}


def alias_for(table_name: str, column_name: str) -> str | None:
    """The confirmed Korean alias for `column_name` on `table_name`, or `None` if this module has
    no entry for it (the caller's responsibility to only ask for in-scope columns -- see module
    docstring)."""
    return FIELD_ALIASES_BY_TABLE.get(table_name, {}).get(column_name)
