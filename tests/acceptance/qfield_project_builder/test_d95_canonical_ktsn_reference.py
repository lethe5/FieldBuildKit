"""D-95 canonical KTSN workbook/source-selection acceptance tests.

These tests are intentionally written against the new acceptance seams documented in
``HARNESS_CONTRACT.md``.  They do not change the approved specification or application code.
The real workbook is used as a read-only fixture for the current header, counts, and sample rows;
temporary workbooks are used only for invalid-input and upload-fallback cases.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from qfield_builder import qml_plugin

from .conftest import REPO_ROOT, make_base_config

PRIVATE_WORKBOOK = os.environ.get("QPB_PRIVATE_REFERENCE_WORKBOOK")
CANONICAL_XLSX = Path(PRIVATE_WORKBOOK or "__private_workbook_not_supplied__.xlsx")
private_workbook = pytest.mark.skipif(
    not PRIVATE_WORKBOOK, reason="optional historical dataset: set QPB_PRIVATE_REFERENCE_WORKBOOK"
)

CANONICAL_SHA256 = "2a7d81c7b032851ed1e260f08607296bc11519f6fa50a4909649269ab693c963"
SOURCE_COLUMNS = (
    "No",
    "관리분류군",
    "정이명여부",
    "학명",
    "대표국명",
    "명명자",
    "명명년도",
    "Phylum",
    "Phylum 국명",
    "Class",
    "Class 국명",
    "Order",
    "Order 국명",
    "Family",
    "Family 국명",
    "Genus",
    "Genus 국명",
    "SubGenus",
    "SubGenus 국명",
    "Species",
    "Species 국명",
    "콘텐츠 여부",
    "URL",
)
LOGICAL_COLUMNS = (
    "ktsn",
    "source_no",
    "taxon_status",
    "korean_name",
    "scientific_name",
    "scientific_name_normalized",
    "scientific_name_without_authority",
    "authority",
    "naming_year",
    "phylum_scientific_name",
    "phylum_korean_name",
    "class_scientific_name",
    "class_korean_name",
    "order_scientific_name",
    "order_korean_name",
    "family_scientific_name",
    "family_korean_name",
    "genus_scientific_name",
    "genus_korean_name",
    "accepted_ktsn",
    "source_url",
    "content_available",
    "source_row",
)


def _require(acceptance_api, name: str):
    function = getattr(acceptance_api, name, None)
    if function is None:
        pytest.skip(
            f"qfield_builder.acceptance_api.{name}() is not implemented yet — see "
            "HARNESS_CONTRACT.md D-95 additions"
        )
    return function


@pytest.fixture()
def inspect_source_candidates(acceptance_api):
    return _require(acceptance_api, "inspect_ktsn_source_candidates")


@pytest.fixture()
def ingest_canonical_workbook(acceptance_api):
    return _require(acceptance_api, "ingest_canonical_workbook")


@pytest.fixture()
def normalize_canonical_name(acceptance_api):
    return _require(acceptance_api, "normalize_canonical_scientific_name")


@pytest.fixture()
def extract_canonical_ktsn(acceptance_api):
    return _require(acceptance_api, "extract_canonical_ktsn")


@pytest.fixture()
def match_canonical_name(acceptance_api):
    return _require(acceptance_api, "match_canonical_ktsn")


@pytest.fixture()
def aggregate_taxonomy_report(acceptance_api):
    return _require(acceptance_api, "aggregate_taxonomy_report")


def _write_workbook(path: Path, rows: list[list[object]], *, row1=None, row2=None) -> Path:
    """Create the exact two-row-header shape used by Rpt_2026-08-29_List.xlsx."""
    openpyxl = pytest.importorskip("openpyxl")
    row1 = row1 or [
        "No", "관리분류군", "정이명여부", "학명", "대표국명", "명명자", "명명년도",
        "Phylum", None, "Class", None, "Order", None, "Family", None, "Genus", None,
        "SubGenus", None, "Species", None, "콘텐츠 여부", "URL",
    ]
    row2 = row2 or [
        None, None, None, None, None, None, None, "Name", "국명", "Name", "국명",
        "Name", "국명", "Name", "국명", "Name", "국명", "Name", "국명", "Name",
        "국명", None, None,
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Data Sheet"
    sheet.append(row1)
    sheet.append(row2)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


def _valid_rows() -> list[list[object]]:
    return [
        [1, "관속식물류", "정명", "Testus demo (A.) B.", "테스트종", "B.", "1900",
         "Magnoliophyta", "속씨식물문", "Testopsida", "테스트강", "Testales", "테스트목",
         "Testaceae", "테스트과", "Testus", "테스트속", None, None, "demo", "테스트종", "O",
         "https://species.nibr.go.kr/species-detail/000000000001"],
        ["-", "관속식물류", "이명", "Testus oldus A.", "테스트종", "A.", "1899",
         "Magnoliophyta", "속씨식물문", "Testopsida", "테스트강", "Testales", "테스트목",
         "Testaceae", "테스트과", "Testus", "테스트속", None, None, "oldus", "테스트종", "X",
         "https://species.nibr.go.kr/species-detail/000000000002"],
    ]


@private_workbook
def test_ac137_real_workbook_header_counts_samples_and_synonym_grouping(ingest_canonical_workbook):
    result = ingest_canonical_workbook(str(CANONICAL_XLSX), source_kind="bundled_candidate")
    assert result["success"] is True, result
    assert result["sheet_name"] == "Data Sheet"
    assert result["header_rows"] == [1, 2]
    assert result["data_start_row"] == 3
    assert result["row_count"] == 8_042
    assert result["accepted_count"] == 4_673
    assert result["synonym_count"] == 3_369
    assert result["source_columns"] == list(SOURCE_COLUMNS)
    assert result["logical_columns"] == list(LOGICAL_COLUMNS)
    assert set(result["taxon_groups"]) == {"관속식물류"}

    first = result["rows"][0]
    assert first["source_row"] == 3
    assert first["ktsn"] == "120000059514"
    assert first["source_no"] == "1"
    assert first["taxon_status"] == "정명"
    assert first["korean_name"] == "왕다람쥐꼬리"
    assert first["scientific_name"] == "Huperzia cryptomeriana (Maxim.)R. D. Dixit"
    assert first["accepted_ktsn"] == first["ktsn"]
    assert first["source_url"] == "https://species.nibr.go.kr/species-detail/120000059514"

    synonym = result["rows"][2]
    assert synonym["source_row"] == 5
    assert synonym["source_no"] == "-"
    assert synonym["taxon_status"] == "이명"
    assert synonym["ktsn"] == "120000215993"
    assert synonym["accepted_ktsn"] == "120000059515"
    assert synonym["scientific_name"] == "Huperzia integrifolia (Matsuda)Z. Satou"
    assert result["rows"][1]["accepted_ktsn"] == result["rows"][1]["ktsn"]


def test_ac138_candidate_search_recommends_canonical_without_silent_selection(
    inspect_source_candidates, tmp_path,
):
    tables = tmp_path / "tables"
    canonical_path = _write_workbook(tables / "Rpt_2026-08-29_List.xlsx", _valid_rows())
    legacy_path = tables / "2025년 국가생물종목록_v1.0.xlsx"
    from openpyxl import Workbook
    Workbook().save(legacy_path)
    legacy_csv = tables / "tb_leco_nib_ktsn_dtl_gat.csv"
    legacy_csv.write_text("legacy")
    result = inspect_source_candidates(str(tables))
    assert result["recommended_filename"] == canonical_path.name
    candidates = {entry["filename"]: entry for entry in result["candidates"]}
    assert canonical_path.name in candidates
    assert legacy_path.name in candidates
    assert all(entry["extension"] == ".xlsx" for entry in result["candidates"])
    assert legacy_csv.name not in candidates

    canonical = candidates[canonical_path.name]
    assert canonical["source_kind"] == "bundled_candidate"
    assert Path(canonical["path"]).resolve() == canonical_path.resolve()
    assert canonical["sheet_name"] == "Data Sheet"
    assert canonical["header_rows"] == [1, 2]
    assert canonical["sample_rows"]
    assert {"status", "scientific_name", "korean_name", "ktsn"}.issubset(
        canonical["sample_rows"][0]
    )
    assert result["selected"] is None
    assert result["can_continue"] is False

    confirmed = inspect_source_candidates(
        str(tables), confirmed_path=str(canonical_path)
    )
    assert confirmed["selected"]["filename"] == canonical_path.name
    assert confirmed["selected"]["validation_status"] == "valid"
    assert confirmed["can_continue"] is True

    legacy_confirmed = inspect_source_candidates(
        str(tables), confirmed_path=str(legacy_path)
    )
    assert legacy_confirmed["can_continue"] is False
    assert legacy_confirmed["selected"] is None or legacy_confirmed["selected"][
        "validation_status"
    ] != "valid"


def test_ac138_missing_candidate_does_not_fallback_to_legacy_sources(inspect_source_candidates, tmp_path):
    tables = tmp_path / "tables"
    tables.mkdir()
    result = inspect_source_candidates(str(tables))
    assert result["candidates"] == []
    assert result["recommended_filename"] is None
    assert result["selected"] is None
    assert result["can_continue"] is False
    assert result.get("error_code")
    assert result.get("error_message")


def test_ac138_upload_fallback_requires_same_preview_validation_and_confirmation(
    inspect_source_candidates, ingest_canonical_workbook, tmp_path
):
    upload = _write_workbook(tmp_path / "user-selected.xlsx", _valid_rows())
    preview = inspect_source_candidates(str(tmp_path), upload_path=str(upload))
    assert preview["candidates"] == []
    assert preview["upload"]["filename"] == upload.name
    assert preview["upload"]["sample_rows"]
    assert preview["can_continue"] is False

    confirmed = inspect_source_candidates(
        str(tmp_path), upload_path=str(upload), confirmed_path=str(upload)
    )
    assert confirmed["selected"]["source_kind"] == "user_upload"
    assert confirmed["selected"]["validation_status"] == "valid"
    assert confirmed["can_continue"] is True

    ingested = ingest_canonical_workbook(str(upload), source_kind="user_upload")
    assert ingested["source_kind"] == "user_upload"
    assert ingested["row_count"] == 2
    assert ingested["rows"][1]["accepted_ktsn"] == "000000000001"


@pytest.mark.parametrize(
    "case",
    [
        "nonvascular",
        "missing_file",
        "unreadable_workbook",
        "bad_status",
        "accepted_no_missing",
        "synonym_no_not_dash",
        "orphan_synonym",
        "bad_url_prefix",
        "empty_url_ktsn",
        "duplicate_ktsn",
        "missing_subcolumn",
        "missing_required_column",
        "invalid_extension",
    ],
)
def test_ac141_invalid_or_missing_source_is_fail_closed_with_actionable_error(
    ingest_canonical_workbook, tmp_path, case
):
    rows = _valid_rows()
    row1 = None
    row2 = None
    suffix = ".xlsx"
    if case == "nonvascular":
        rows[0][1] = "선태식물류"
    elif case == "bad_status":
        rows[0][2] = "미상"
    elif case == "accepted_no_missing":
        rows[0][0] = ""
    elif case == "synonym_no_not_dash":
        rows[1][0] = "9"
    elif case == "orphan_synonym":
        rows[0][0], rows[0][2] = "-", "이명"
    elif case == "bad_url_prefix":
        rows[0][-1] = "https://example.invalid/species-detail/000000000001"
    elif case == "empty_url_ktsn":
        rows[0][-1] = "https://species.nibr.go.kr/species-detail/"
    elif case == "duplicate_ktsn":
        rows[1][-1] = rows[0][-1]
    elif case == "missing_subcolumn":
        row2 = [None, None, None, None, None, None, None, "Name", None, "Name", "국명",
                "Name", "국명", "Name", "국명", "Name", "국명", "Name", "국명", "Name",
                "국명", None, None]
    elif case == "missing_required_column":
        row1 = [
            "No", "관리분류군", "정이명여부", "학명", None, "명명자", "명명년도", "Phylum",
            None, "Class", None, "Order", None, "Family", None, "Genus", None, "SubGenus",
            None, "Species", None, "콘텐츠 여부", "URL",
        ]
    elif case == "invalid_extension":
        suffix = ".xls"

    path = tmp_path / f"bad-{case}{suffix}"
    if case == "unreadable_workbook":
        path.write_text("not an xlsx workbook", encoding="utf-8")
    elif case != "missing_file":
        _write_workbook(path, rows, row1=row1, row2=row2)
    result = ingest_canonical_workbook(str(path), source_kind="user_upload")
    assert result["success"] is False, (case, result)
    assert result.get("error_code")
    assert result.get("error_message")
    assert any("가" <= character <= "힣" for character in result["error_message"])
    assert result.get("partial_rows", []) == []
    assert result.get("promoted_project") is not True


def test_ac139_r_equivalent_name_normalization_and_authority_extraction(normalize_canonical_name):
    cases = {
        "  Huperzia   cryptomeriana  (  Maxim.  )R. D. Dixit  ": {
            "scientific_name_normalized": "Huperzia cryptomeriana (Maxim.) R. D. Dixit",
            "scientific_name_without_authority": "Huperzia cryptomeriana",
            "authority": "(Maxim.) R. D. Dixit",
        },
        "Huperzia jejuensis B.-Y Sun & J. Lim": {
            "scientific_name_normalized": "Huperzia jejuensis B.-Y Sun & J. Lim",
            "scientific_name_without_authority": "Huperzia jejuensis",
            "authority": "B.-Y Sun & J. Lim",
        },
        "Huperzia cryptomeriana": {
            "scientific_name_normalized": "Huperzia cryptomeriana",
            "scientific_name_without_authority": "Huperzia cryptomeriana",
            "authority": "",
        },
    }
    for raw, expected in cases.items():
        result = normalize_canonical_name(raw)
        assert result == expected, (raw, result)


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://species.nibr.go.kr/species-detail/120000059514",
            "120000059514",
        ),
        (
            "https://species.nibr.go.kr/species-detail/000000000001",
            "000000000001",
        ),
    ],
)
def test_ac139_ktsn_is_only_the_string_remainder_of_exact_url_prefix(
    extract_canonical_ktsn, url, expected
):
    assert extract_canonical_ktsn(url) == {"source_url": url, "ktsn": expected}


@pytest.mark.parametrize(
    "url",
    [
        "https://species.nibr.go.kr/species/120000059514",
        "http://species.nibr.go.kr/species-detail/120000059514",
        "https://example.invalid/species-detail/120000059514",
        "https://species.nibr.go.kr/species-detail/",
    ],
)
def test_ac139_invalid_prefix_or_empty_ktsn_is_rejected(extract_canonical_ktsn, url):
    with pytest.raises(Exception):
        extract_canonical_ktsn(url)


@private_workbook
def test_ac140_rows_materialize_all_rank_fields_and_preserve_blank_hierarchy(
    ingest_canonical_workbook,
):
    result = ingest_canonical_workbook(str(CANONICAL_XLSX), source_kind="bundled_candidate")
    row = result["rows"][0]
    for field in (
        "phylum_scientific_name", "phylum_korean_name", "class_scientific_name",
        "class_korean_name", "order_scientific_name", "order_korean_name",
        "family_scientific_name", "family_korean_name", "genus_scientific_name",
        "genus_korean_name",
    ):
        assert row[field] is not None and row[field] != ""
    sparse = next(item for item in result["rows"] if item["genus_scientific_name"] is None)
    assert sparse["genus_scientific_name"] is None
    assert sparse["genus_korean_name"] is None


@private_workbook
def test_ac141_provenance_is_hash_schema_and_pipeline_identity_not_dataset_version(
    ingest_canonical_workbook,
):
    result = ingest_canonical_workbook(str(CANONICAL_XLSX), source_kind="bundled_candidate")
    provenance = result["provenance"]
    assert provenance["source_filename"] == CANONICAL_XLSX.name
    assert provenance["source_kind"] == "bundled_candidate"
    assert provenance["sha256"] == CANONICAL_SHA256
    assert provenance["byte_size"] == CANONICAL_XLSX.stat().st_size
    assert provenance["sheet_name"] == "Data Sheet"
    assert provenance["header_rows"] == [1, 2]
    assert provenance["data_start_row"] == 3
    assert provenance["source_row_count"] == 8_042
    assert provenance["accepted_count"] == 4_673
    assert provenance["synonym_count"] == 3_369
    assert provenance["selection_timestamp"]
    assert provenance["validation_result"] == "valid"
    assert provenance["schema_revision"]
    assert provenance["pipeline_revision"]
    assert "dataset_version" not in provenance
    for row_payload_key in ("rows", "preview", "preview_rows", "sample_rows"):
        assert row_payload_key not in provenance


@private_workbook
def test_ac142_synonym_matching_resolves_to_accepted_row_but_retains_raw_authority_name(
    ingest_canonical_workbook, match_canonical_name
):
    ingested = ingest_canonical_workbook(str(CANONICAL_XLSX), source_kind="bundled_candidate")
    result = match_canonical_name("Huperzia integrifolia", ingested["rows"])
    assert result["matched"] is True
    assert result["matched_ktsn"] == "120000215993"
    assert result["taxon_status"] == "이명"
    assert result["accepted_ktsn"] == "120000059515"
    assert result["selected_korean_name"] == "긴다람쥐꼬리"
    assert result["selected_scientific_name"] == "Huperzia jejuensis B.-Y Sun & J. Lim"
    assert result["selected_scientific_name_without_authority"] == "Huperzia jejuensis"


def test_ac142_comparison_key_collision_is_ambiguous_and_never_guesses(match_canonical_name):
    rows = [
        {
            "ktsn": "1", "taxon_status": "정명", "accepted_ktsn": "1", "korean_name": "가",
            "scientific_name": "Foo bar A.", "scientific_name_without_authority": "Foo bar",
        },
        {
            "ktsn": "2", "taxon_status": "정명", "accepted_ktsn": "2", "korean_name": "나",
            "scientific_name": "Foo bar B.", "scientific_name_without_authority": "Foo bar",
        },
    ]
    result = match_canonical_name("Foo bar", rows)
    assert result["ambiguous"] is True
    assert result["accepted_ktsn"] is None
    assert result["selected_scientific_name"] is None


def test_ac143_taxonomy_report_unifies_synonym_and_accepted_observations_without_join_multiplication(
    aggregate_taxonomy_report,
):
    taxonomy_rows = [
        {
            "ktsn": "A", "accepted_ktsn": "A", "taxon_status": "정명",
            "phylum_scientific_name": "Magnoliophyta", "phylum_korean_name": "속씨식물문",
            "class_scientific_name": "Testopsida", "class_korean_name": "테스트강",
            "order_scientific_name": "Testales", "order_korean_name": "테스트목",
            "family_scientific_name": "Testaceae", "family_korean_name": "테스트과",
            "genus_scientific_name": "Testus", "genus_korean_name": "테스트속",
        },
        {
            "ktsn": "S", "accepted_ktsn": "A", "taxon_status": "이명",
            "phylum_scientific_name": "Magnoliophyta", "phylum_korean_name": "속씨식물문",
            "class_scientific_name": "Testopsida", "class_korean_name": "테스트강",
            "order_scientific_name": "Testales", "order_korean_name": "테스트목",
            "family_scientific_name": "Testaceae", "family_korean_name": "테스트과",
            "genus_scientific_name": "Testus", "genus_korean_name": "테스트속",
        },
    ]
    observations = [
        {"observation_id": "o1", "selected_ktsn": "A"},
        {"observation_id": "o2", "selected_ktsn": "S"},
        {"observation_id": "o3", "selected_ktsn": "missing"},
        {"observation_id": "o4", "selected_ktsn": ""},
    ]
    report = aggregate_taxonomy_report(observations, taxonomy_rows, survey_type="simple_inventory")
    bucket = report["aggregations"]["Phylum"][0]
    assert bucket["scientific_name"] == "Magnoliophyta"
    assert bucket["korean_name"] == "속씨식물문"
    assert bucket["observation_count"] == 2
    assert bucket["distinct_ktsn_count"] == 2
    assert len(report["aggregations"]["Phylum"]) == 1
    assert "missing" in report["limitations"]
    assert len(report["ordinary_observations"]) == 4


def test_ac143_type4_taxonomy_is_not_applicable(aggregate_taxonomy_report):
    type4 = aggregate_taxonomy_report([], [], survey_type="vegetation_mapping")
    assert type4["aggregations"] == {}
    assert type4["taxonomy_applicability"] == "not_applicable"


def test_ac144_old_project_report_path_is_compatible_without_legacy_fallback(
    aggregate_taxonomy_report,
):

    old = aggregate_taxonomy_report(
        [{"observation_id": "legacy-1", "selected_ktsn": "1"}],
        None,
        survey_type="simple_inventory",
    )
    assert old["ordinary_observations"] == [{"observation_id": "legacy-1", "selected_ktsn": "1"}]
    assert "taxonomy_reference_unavailable" in old["limitations"]


def test_ac144_canonical_generated_plugin_fails_closed_without_source_fallback():
    plugin_source = qml_plugin.render_project_plugin_qml(
        "canonical-output", identification_enabled=True, canonical_reference_enabled=True
    )
    assert "Rpt_2026-08-29_List.xlsx" not in plugin_source
    assert "qpbCanonicalReferenceRequired: true" in plugin_source
    widget_source = qml_plugin.render_identification_widget_qml(
        "''", canonical_reference_enabled=True
    )
    assert "qpbCanonicalReferenceRequired: true" in widget_source
    assert "canonical_taxonomy_layer_missing" in widget_source
    assert "식물 분류 참조표를 사용할 수 없어 자동 동정 후보를 표시할 수 없습니다" in widget_source
    handler = widget_source[widget_source.index("function qpbHandlePlantNetResponse") : widget_source.index(
        "function qpbPersistIdentification", widget_source.index("function qpbHandlePlantNetResponse")
    )]
    assert "qpbLookupCanonicalTaxonomy(sciName)" in handler
    assert "if (!ktsnMatch) { if (!csv)" not in handler


def test_ac145_packaging_and_wizard_do_not_discover_storage_sources():
    packaging_spec = (REPO_ROOT / "packaging/qfield_builder.spec").read_text(encoding="utf-8")
    wizard_source = (REPO_ROOT / "qfield_builder/ui/wizard.py").read_text(encoding="utf-8")
    assert "storage/reference" not in packaging_spec
    assert 'reference_path("tables")' not in wizard_source
    assert "taxonomy_sample.xlsx" in wizard_source
    assert "_browse_reference_source" in wizard_source


def test_ac138_wizard_upload_candidate_keeps_user_upload_provenance_explicit():
    wizard_source = (REPO_ROOT / "qfield_builder" / "ui" / "wizard.py").read_text(
        encoding="utf-8"
    )
    assert 'upload_candidate["source_kind"] = "user_upload"' in wizard_source
    assert 'config["canonical_source_kind"] = reference_source["source_kind"]' in wizard_source
    confirm_source = wizard_source.split("def _confirm_reference_source", 1)[1].split(
        "def _load_remembered_plantnet_key", 1
    )[0]
    assert "candidate = self._selected_reference_candidate" in confirm_source
    assert "source_kind = candidate.get(\"source_kind\")" in confirm_source
    assert "for candidate in self._reference_candidates.values()" not in confirm_source


def test_ac141_source_hash_is_recomputed_after_workbook_changes(ingest_canonical_workbook, tmp_path):
    path = _write_workbook(tmp_path / "candidate.xlsx", _valid_rows())
    first = ingest_canonical_workbook(str(path), source_kind="user_upload")
    confirmed_hash = first["provenance"]["sha256"]
    path.write_bytes(path.read_bytes() + b"\n")
    second = ingest_canonical_workbook(str(path), source_kind="user_upload")
    assert first["provenance"]["sha256"] != second["provenance"]["sha256"]
    assert first["provenance"]["sha256"] == hashlib.sha256(
        (tmp_path / "candidate.xlsx").read_bytes()[:-1]
    ).hexdigest()
    changed_after_confirmation = ingest_canonical_workbook(
        str(path), source_kind="user_upload", expected_sha256=confirmed_hash
    )
    assert changed_after_confirmation["success"] is False
    assert changed_after_confirmation.get("error_code")
    assert changed_after_confirmation.get("partial_rows", []) == []
