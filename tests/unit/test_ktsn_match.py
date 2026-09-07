"""Unit tests for qfield_builder.ktsn_match (FR-QPB-106/107; Decision Log D-40/D-42).

Uses small, self-contained inline CSV fixtures (distinct from the acceptance suite's own real/
synthetic fixture files under tests/acceptance/**, which this implementer must never modify), so
these are fast and independent of that approved fixture data. Focuses in particular on
`match_ktsn_with_national_list`'s multi-entry `correct_list` cross-reference logic (Decision Log
D-40/D-42), which HARNESS_CONTRACT.md's `match_ktsn` acceptance contract explicitly leaves
untested (a "known, deliberately-uncovered specification gap" at the time the acceptance tests
were designed).
"""
from __future__ import annotations

import csv as csv_module

from qfield_builder import ktsn_match

_HEADER = ["ktsn", "taxon_full_nm", "taxon_kor_nm", "taxon_jm_nm", "correct_list"]


def _write_csv(tmp_path, rows: list[list[str]]):
    path = tmp_path / "ktsn.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv_module.writer(fh)
        writer.writerow(_HEADER)
        writer.writerows(rows)
    return str(path)


def test_direct_match_strips_em_tags_and_normalizes_whitespace(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [["1", "<em>Foo</em>  <em>bar</em>", "포바", "정명", "[]"]],
    )
    result = ktsn_match.match_ktsn("Foo bar", csv_path)
    assert result["direct_match_found"] is True
    assert result["direct_row_ktsn"] == "1"
    assert result["direct_korean_name"] == "포바"


def test_no_match_never_fabricates_a_korean_name(tmp_path):
    csv_path = _write_csv(tmp_path, [["1", "Foo bar", "포바", "정명", "[]"]])
    result = ktsn_match.match_ktsn("Nonexistent species", csv_path)
    assert result["direct_match_found"] is False
    assert result["direct_korean_name"] is None
    assert result["accepted_resolved"] is False


def test_already_accepted_row_does_not_consult_correct_list(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [["1", "Foo bar", "포바", "정명", "SHOULD_NOT_BE_PARSED"]],
    )
    result = ktsn_match.match_ktsn("Foo bar", csv_path)
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "1"
    assert result["accepted_korean_name"] == "포바"


def test_single_entry_correct_list_resolves_to_accepted_row(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ["1", "Synonym name", "동의어", "이명", '[{"KTSN": "2"}]'],
            ["2", "Accepted name", "정명종", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "2"
    assert result["accepted_korean_name"] == "정명종"


def test_empty_correct_list_is_unresolved_but_retains_direct_match(tmp_path):
    csv_path = _write_csv(tmp_path, [["1", "Synonym name", "동의어", "이명", "[]"]])
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["accepted_resolution_attempted"] is True
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "correct_list_empty"
    assert result["direct_row_ktsn"] == "1"


def test_malformed_correct_list_json_does_not_crash(tmp_path):
    csv_path = _write_csv(tmp_path, [["1", "Synonym name", "동의어", "이명", "NOT VALID{{"]])
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["unresolved_reason"] == "correct_list_malformed"


def test_conflicting_ktsn_ktns_values_are_flagged_ambiguous(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [["1", "Synonym name", "동의어", "이명", '[{"KTSN": "2", "KTNS": "3"}]']],
    )
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["ambiguous"] is True
    assert result["accepted_resolved"] is False


def test_ktns_only_legacy_fallback_resolves(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ["1", "Synonym name", "동의어", "이명", '[{"KTNS": "2"}]'],
            ["2", "Accepted name", "정명종", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "2"


def test_accepted_ktsn_not_found_in_csv(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [["1", "Synonym name", "동의어", "이명", '[{"KTSN": "999"}]']],
    )
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "accepted_ktsn_not_found_in_csv"


# --- direct_scientific_name (FR-QPB-106, revised; Decision Log D-60/D-64) -----------------------
# Mirrors direct_korean_name exactly: the matched row's own taxon_full_nm, <em>-tag-stripped,
# populated whenever a direct match is found, independent of whether accepted-name resolution
# succeeds.


def test_direct_scientific_name_is_tag_stripped_on_an_already_accepted_direct_match(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [["1", "<em>Foo</em>  <em>bar</em>", "포바", "정명", "[]"]],
    )
    result = ktsn_match.match_ktsn("Foo bar", csv_path)
    assert result["direct_match_found"] is True
    assert result["direct_scientific_name"] == "Foo bar"
    # Mirrors accepted_scientific_name exactly for an already-accepted row.
    assert result["direct_scientific_name"] == result["accepted_scientific_name"]


def test_direct_scientific_name_is_populated_even_when_accepted_resolution_fails(tmp_path):
    """Unlike accepted_scientific_name (only set on successful resolution), direct_scientific_name
    must be populated from the direct match alone, regardless of whether the separate accepted-
    name resolution (correct_list) below it succeeds."""
    csv_path = _write_csv(tmp_path, [["1", "Synonym name", "동의어", "이명", "[]"]])
    result = ktsn_match.match_ktsn("Synonym name", csv_path)
    assert result["accepted_resolved"] is False
    assert result["direct_scientific_name"] == "Synonym name"
    assert result["accepted_scientific_name"] is None


def test_direct_scientific_name_is_none_when_no_direct_match(tmp_path):
    csv_path = _write_csv(tmp_path, [["1", "Foo bar", "포바", "정명", "[]"]])
    result = ktsn_match.match_ktsn("Nonexistent species", csv_path)
    assert result["direct_match_found"] is False
    assert result["direct_scientific_name"] is None


def test_match_ktsn_with_national_list_also_populates_direct_scientific_name(tmp_path):
    """Lockstep check: match_ktsn_with_national_list must expose direct_scientific_name exactly
    like match_ktsn above."""
    csv_path = _write_csv(
        tmp_path,
        [["1", "<em>Foo</em> <em>bar</em>", "포바", "이명", '[{"KTSN": "2"}]']],
    )
    result = ktsn_match.match_ktsn_with_national_list("Foo bar", csv_path, national_ktsn_set=set())
    assert result["direct_match_found"] is True
    assert result["direct_scientific_name"] == "Foo bar"


# --- match_ktsn_with_national_list (D-40/D-42 multi-entry cross-reference) ----------------------


def test_multi_entry_correct_list_resolves_when_exactly_one_candidate_is_in_national_list(
    tmp_path,
):
    csv_path = _write_csv(
        tmp_path,
        [
            [
                "1",
                "Synonym name",
                "동의어",
                "이명",
                '[{"KTSN": "2"}, {"KTSN": "3"}]',
            ],
            ["2", "Accepted candidate A", "후보A", "정명", "[]"],
            ["3", "Accepted candidate B", "후보B", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn_with_national_list(
        "Synonym name", csv_path, national_ktsn_set={"2"}
    )
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "2"
    assert result["ambiguous"] is False


def test_multi_entry_correct_list_is_ambiguous_when_zero_candidates_in_national_list(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ["1", "Synonym name", "동의어", "이명", '[{"KTSN": "2"}, {"KTSN": "3"}]'],
            ["2", "Accepted candidate A", "후보A", "정명", "[]"],
            ["3", "Accepted candidate B", "후보B", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn_with_national_list(
        "Synonym name", csv_path, national_ktsn_set=set()
    )
    assert result["ambiguous"] is True
    assert result["accepted_resolved"] is False


def test_multi_entry_correct_list_is_ambiguous_when_multiple_candidates_in_national_list(
    tmp_path,
):
    csv_path = _write_csv(
        tmp_path,
        [
            ["1", "Synonym name", "동의어", "이명", '[{"KTSN": "2"}, {"KTSN": "3"}]'],
            ["2", "Accepted candidate A", "후보A", "정명", "[]"],
            ["3", "Accepted candidate B", "후보B", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn_with_national_list(
        "Synonym name", csv_path, national_ktsn_set={"2", "3"}
    )
    assert result["ambiguous"] is True
    assert result["accepted_resolved"] is False


def test_single_entry_correct_list_unaffected_by_national_list_variant(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ["1", "Synonym name", "동의어", "이명", '[{"KTSN": "2"}]'],
            ["2", "Accepted name", "정명종", "정명", "[]"],
        ],
    )
    result = ktsn_match.match_ktsn_with_national_list("Synonym name", csv_path, set())
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "2"
