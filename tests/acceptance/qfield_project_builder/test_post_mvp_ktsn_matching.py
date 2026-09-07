"""Section 13.4/13.5 — KTSN direct match + accepted-name resolution (FR-QPB-106/107; post-MVP
guaranteed-manual baseline; Decision Log D-34, closing the validation-authorization portion of
Open Question O-7).

The real, shipped mechanism runs as embedded QML inside QField (FR-QPB-101) -- genuinely
QML-runtime behavior this project has no harness for. What this file tests instead is a
**pure-Python reference implementation of the matching/resolution *rules themselves***
(`acceptance_api.match_ktsn`), validated against real slices of the actual, stakeholder-confirmed
KTSN reference CSV (Decision Log D-34) plus a small number of deliberately constructed rows
exercising edge cases confirmed *absent* from the real file (see below). **Passing these tests
validates the rules are correct against real data; it is not a substitute for confirming the
eventual QML implementation behaves identically** -- see HARNESS_CONTRACT.md's "Post-MVP: Section
13" section.

Fixture provenance:
- `fixtures/ktsn_real_slice.csv` -- 10 real rows copied verbatim (all original columns preserved)
  from `storage/reference/tables/tb_leco_nib_ktsn_dtl_gat.csv`, chosen during test design to
  represent: an already-accepted (`taxon_jm_nm == '정명'`) row with a plain Korean name; a
  synonym (`이명`) row whose single-entry `correct_list` resolves to that accepted row; and a
  synonym row whose `correct_list` is empty (`[]`) -- a real, naturally-occurring
  resolution-fails case. NOT synthetic data.
- `fixtures/ktsn_synthetic_edge_cases.csv` -- deliberately constructed rows (clearly-fake
  `9000000000xx`-style KTSN identifiers, fictional `Testus ...` scientific names) exercising
  malformed JSON, a missing-KTSN/KTNS-key entry, a genuine `KTSN` vs `KTNS` value conflict, a
  `KTNS`-only legacy-fallback case, a same-value-in-both-keys non-conflict case, and a resolved
  KTSN that doesn't exist in the CSV. A full scan of the real, full CSV (~212,397 rows) performed
  during test design found **zero** malformed `correct_list` JSON values and **zero** literal
  `"KTNS"` occurrences -- these cases are real, spec-required rules (AC-QPB-043) that do not
  currently occur naturally in the real dataset, so they are tested here with clearly-labeled
  constructed data rather than left untested.

**Known, deliberately-uncovered specification gap:** a full scan of the real CSV during test
design found ~402 rows (of ~212,397) whose `correct_list` is a JSON array with *more than one*
entry, each a distinct candidate accepted taxon with its own differing `KTSN` value.
FR-QPB-107's text describes reading a single scalar `KTSN` value with no rule for which array
entry is canonical when several exist. No test here asserts any particular behavior for a
multi-entry `correct_list` -- see the traceability file's ambiguity report.
"""
from __future__ import annotations

import csv
import json

import pytest

from .conftest import KTSN_REAL_SLICE_CSV_PATH, KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH

_MINIMAL_KTSN_FIELDS = (
    "ktsn",
    "taxon_full_nm",
    "taxon_kor_nm",
    "taxon_jm_nm",
    "correct_list",
)


def _write_minimal_ktsn_csv(path, rows):
    """Write a deliberately small KTSN fixture while preserving JSON/list edge cases."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_MINIMAL_KTSN_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in _MINIMAL_KTSN_FIELDS})

# --- FR-QPB-106 / AC-QPB-041 (direct match + <em>-tag normalization) ----------------------------


def test_ac041_em_tags_are_stripped_and_direct_match_found_for_a_real_accepted_row(match_ktsn):
    # Real row 120000033551: taxon_full_nm "<em>Gandaritis</em> <em>agnes</em>", taxon_kor_nm
    # "회색물결자나방", taxon_jm_nm "정명".
    result = match_ktsn("Gandaritis agnes", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["direct_row_ktsn"] == "120000033551"
    assert result["direct_korean_name"] == "회색물결자나방"


def test_direct_match_normalizes_extra_internal_whitespace_in_the_candidate_name(match_ktsn):
    result = match_ktsn("Gandaritis   agnes", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["direct_row_ktsn"] == "120000033551"


def test_direct_match_trims_leading_and_trailing_whitespace(match_ktsn):
    result = match_ktsn("  Gandaritis agnes  ", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True


def test_direct_match_not_found_for_an_unknown_scientific_name_and_never_fabricates(match_ktsn):
    result = match_ktsn(
        "Nonexistentus fabricatus", str(KTSN_REAL_SLICE_CSV_PATH)
    )
    assert result["direct_match_found"] is False
    assert result["direct_korean_name"] is None
    assert result["accepted_resolved"] is False


# --- FR-QPB-106 (revised; Decision Log D-60, confirmed by D-64) -- new direct_scientific_name ----
# --- return key, mirroring direct_korean_name exactly. Supplementary to AC-QPB-099 (which checks --
# --- the shipped QML mirror, qpbMatchKtsn, structurally, in test_post_mvp_identification_plugin.py)
# --- -- this extends the existing pure-Python reference implementation of the same rule. ----------


def test_direct_scientific_name_is_populated_from_tag_stripped_taxon_full_nm_on_a_direct_match(
    match_ktsn,
):
    # Real row 120000033551: taxon_full_nm "<em>Gandaritis</em> <em>agnes</em>" -> tag-stripped
    # "Gandaritis agnes" -- mirrors accepted_scientific_name's own existing tag-stripping rule
    # (FR-QPB-107), populated here regardless of whether accepted-name resolution itself succeeds.
    result = match_ktsn("Gandaritis agnes", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["direct_scientific_name"] == "Gandaritis agnes"


def test_direct_scientific_name_is_none_when_no_direct_match_is_found(match_ktsn):
    result = match_ktsn("Nonexistentus fabricatus", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is False
    assert result["direct_scientific_name"] is None


# --- FR-QPB-107 / AC-QPB-042 (accepted-name resolution, real synonym rows) ----------------------


def test_ac106_direct_match_already_accepted_needs_no_further_resolution(match_ktsn):
    # 120000033551 is already taxon_jm_nm == '정명'; correct_list must not even be consulted.
    result = match_ktsn("Gandaritis agnes", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_taxon_jm_nm"] == "정명"
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "120000033551"
    assert result["accepted_korean_name"] == "회색물결자나방"
    assert result["accepted_scientific_name"] == "Gandaritis agnes"  # <em> tags removed
    assert result["ambiguous"] is False


def test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_lestes(
    match_ktsn,
):
    # Real synonym row 120000522614 "Lestes japonica" (이명) -> correct_list resolves to
    # 120000037377 "Lestes japonicus" / "좀청실잠자리" (정명).
    result = match_ktsn("Lestes japonica", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["direct_taxon_jm_nm"] == "이명"
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "120000037377"
    assert result["accepted_korean_name"] == "좀청실잠자리"
    assert result["accepted_scientific_name"] == "Lestes japonicus"
    assert result["ambiguous"] is False


def test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_tinea(
    match_ktsn,
):
    # Real synonym row 120000521623 "Tinea dubia" (이명) -> resolves to 120000032120
    # "Scirpophaga praelata" / "흰빛그늘긴날개명나방" (정명).
    result = match_ktsn("Tinea dubia", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "120000032120"
    assert result["accepted_korean_name"] == "흰빛그늘긴날개명나방"
    assert result["accepted_scientific_name"] == "Scirpophaga praelata"


def test_ac042_accepted_name_resolution_follows_a_single_entry_correct_list_real_case_lygris(
    match_ktsn,
):
    # Real synonym row 120000113292 "Lygris agnes" (이명) -> resolves to 120000033551
    # "Gandaritis agnes" / "회색물결자나방" (정명).
    result = match_ktsn("Lygris agnes", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "120000033551"
    assert result["accepted_korean_name"] == "회색물결자나방"


# --- AC-QPB-043 (real, naturally-occurring resolution-fails case: empty correct_list) -----------


def test_ac043_empty_correct_list_is_a_real_naturally_occurring_resolution_failure(match_ktsn):
    # Real synonym rows 120000110910/09/08 all have taxon_jm_nm == '이명' and correct_list == '[]'.
    result = match_ktsn("Eulecanium armeniacum", str(KTSN_REAL_SLICE_CSV_PATH))
    assert result["direct_match_found"] is True, "the direct match itself must still succeed"
    assert result["direct_taxon_jm_nm"] == "이명"
    assert result["accepted_resolution_attempted"] is True
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "correct_list_empty"
    assert result["ambiguous"] is False
    # "retain the direct match" -- direct match fields must not be cleared just because
    # accepted-name resolution failed.
    assert result["direct_row_ktsn"] == "120000110910"


# --- AC-QPB-043 (constructed edge cases; real data confirmed clean of these) --------------------


def test_ac043_malformed_correct_list_json_is_handled_deterministically_not_a_crash(match_ktsn):
    result = match_ktsn(
        "Testus malformedus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH)
    )
    assert result["direct_match_found"] is True
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "correct_list_malformed"
    assert result["ambiguous"] is False


def test_ac043_missing_ktsn_and_ktns_keys_entirely_is_handled_deterministically(match_ktsn):
    result = match_ktsn("Testus nokeyus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "correct_list_missing_ktsn_key"
    assert result["ambiguous"] is False


def test_ac043_conflicting_ktsn_and_ktns_values_are_flagged_ambiguous_not_silently_resolved(
    match_ktsn,
):
    result = match_ktsn("Testus conflictus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["ambiguous"] is True
    assert result["ambiguous_reason"]
    assert result["accepted_resolved"] is False, (
        "a conflicting KTSN/KTNS pair must never be silently resolved to either value"
    )


def test_ktns_is_used_only_as_a_defensive_legacy_fallback_when_ktsn_key_is_absent(match_ktsn):
    # correct_list == [{"KTNS": "900000000001"}] -> resolves via the legacy KTNS-only fallback to
    # the synthetic accepted row 900000000001 ("테스트정명종").
    result = match_ktsn("Testus legacyus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH))
    assert result["direct_match_found"] is True
    assert result["ambiguous"] is False
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "900000000001"
    assert result["accepted_korean_name"] == "테스트정명종"


def test_ktsn_and_ktns_present_with_the_same_value_is_not_treated_as_a_conflict(match_ktsn):
    result = match_ktsn(
        "Testus samevalueus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH)
    )
    assert result["direct_match_found"] is True
    assert result["ambiguous"] is False
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "900000000001"


def test_accepted_ktsn_not_found_in_csv_is_handled_gracefully(match_ktsn):
    # correct_list points at a KTSN value ("900000000999") that does not exist anywhere in this
    # fixture's own `ktsn` column.
    result = match_ktsn(
        "Testus danglingus", str(KTSN_SYNTHETIC_EDGE_CASES_CSV_PATH)
    )
    assert result["direct_match_found"] is True
    assert result["accepted_resolved"] is False
    assert result["unresolved_reason"] == "accepted_ktsn_not_found_in_csv"
    assert result["ambiguous"] is False


# --- Real, full CSV sanity check (slow-ish; skipped if the gitignored real data is absent) ------


def test_real_full_csv_end_to_end_direct_match_and_accepted_name_resolution(
    match_ktsn, real_ktsn_csv_path
):
    """One end-to-end check against the actual, full, stakeholder-confirmed-authoritative
    (Decision Log D-34) production CSV (~212,397 rows) -- not the extracted slice -- confirming
    the loader/matcher genuinely works against the real file, not just a hand-picked excerpt."""
    result = match_ktsn("Lestes japonica", str(real_ktsn_csv_path))
    assert result["direct_match_found"] is True
    assert result["direct_row_ktsn"] == "120000522614"
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "120000037377"
    assert result["accepted_korean_name"] == "좀청실잠자리"
    assert result["accepted_scientific_name"] == "Lestes japonicus"


# --- D-88 / AC-QPB-128 (recursive accepted-name resolution) -------------------------------


def _recursive_fixture_rows():
    rows = [
        {
            "ktsn": "910000000001",
            "taxon_full_nm": "<em>Testus</em> <em>aliasus</em>",
            "taxon_kor_nm": "중간이명",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"KTSN": "910000000002"}]),
        },
        {
            "ktsn": "910000000002",
            "taxon_full_nm": "<em>Testus</em> <em>originalis</em>",
            "taxon_kor_nm": "중간원기재명",
            "taxon_jm_nm": "원기재명",
            "correct_list": json.dumps([{"KTSN": "910000000003"}]),
        },
        {
            "ktsn": "910000000003",
            "taxon_full_nm": "<em>Testus</em> <em>terminalis</em>",
            "taxon_kor_nm": "최종정명종",
            "taxon_jm_nm": "정명",
            "correct_list": "[]",
        },
        {
            "ktsn": "910000000010",
            "taxon_full_nm": "<em>Testus</em> <em>multi-hop</em>",
            "taxon_kor_nm": "다중후보이명",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps(
                [{"KTSN": "910000000011"}, {"KTSN": "910000000012"}]
            ),
        },
        {
            "ktsn": "910000000011",
            "taxon_full_nm": "<em>Testus</em> <em>selected-intermediate</em>",
            "taxon_kor_nm": "선택된중간명",
            "taxon_jm_nm": "원기재명",
            "correct_list": json.dumps([{"KTNS": "910000000013"}]),
        },
        {
            "ktsn": "910000000012",
            "taxon_full_nm": "<em>Testus</em> <em>unselected-intermediate</em>",
            "taxon_kor_nm": "선택되지않은중간명",
            "taxon_jm_nm": "정명",
            "correct_list": "[]",
        },
        {
            "ktsn": "910000000013",
            "taxon_full_nm": "<em>Testus</em> <em>nibr-terminalis</em>",
            "taxon_kor_nm": "NIBR최종정명종",
            "taxon_jm_nm": "정명",
            "correct_list": "[]",
        },
    ]
    return rows


def test_ac128_follows_multiple_correct_list_hops_to_the_terminal_jungmyeong_row(
    match_ktsn, tmp_path
):
    csv_path = tmp_path / "recursive.csv"
    _write_minimal_ktsn_csv(csv_path, _recursive_fixture_rows())

    result = match_ktsn("Testus aliasus", str(csv_path))

    assert result["direct_match_found"] is True
    assert result["direct_row_ktsn"] == "910000000001"
    assert result["direct_taxon_jm_nm"] == "이명"
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "910000000003"
    assert result["accepted_korean_name"] == "최종정명종"
    assert result["accepted_scientific_name"] == "Testus terminalis"
    assert result["accepted_ktsn"] != result["direct_row_ktsn"]


def test_ac128_applies_nibr_disambiguation_at_an_intermediate_hop(
    match_ktsn_with_national_list, tmp_path
):
    csv_path = tmp_path / "recursive_nibr.csv"
    _write_minimal_ktsn_csv(csv_path, _recursive_fixture_rows())

    result = match_ktsn_with_national_list(
        "Testus multi-hop", str(csv_path), {"910000000011", "910000000013"}
    )

    assert result["direct_match_found"] is True
    assert result["accepted_resolved"] is True
    assert result["accepted_ktsn"] == "910000000013"
    assert result["accepted_korean_name"] == "NIBR최종정명종"
    assert result["accepted_scientific_name"] == "Testus nibr-terminalis"


def test_ac128_zero_or_multiple_nibr_matches_at_an_intermediate_hop_are_ambiguous(
    match_ktsn_with_national_list, tmp_path
):
    csv_path = tmp_path / "recursive_nibr_ambiguous.csv"
    _write_minimal_ktsn_csv(csv_path, _recursive_fixture_rows())

    for national_set in (set(), {"910000000011", "910000000012"}):
        result = match_ktsn_with_national_list(
            "Testus multi-hop", str(csv_path), national_set
        )
        assert result["direct_match_found"] is True
        assert result["accepted_resolved"] is False
        assert result["accepted_ktsn"] is None
        assert result["ambiguous"] is True


# --- D-88 / AC-QPB-129 (bounded, fail-closed recursive resolution) --------------------------


def _safety_fixture_rows():
    rows = [
        {
            "ktsn": "920000000001",
            "taxon_full_nm": "<em>Testus</em> <em>cycle-a</em>",
            "taxon_kor_nm": "순환A",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"KTSN": "920000000002"}]),
        },
        {
            "ktsn": "920000000002",
            "taxon_full_nm": "<em>Testus</em> <em>cycle-b</em>",
            "taxon_kor_nm": "순환B",
            "taxon_jm_nm": "원기재명",
            "correct_list": json.dumps([{"KTSN": "920000000001"}]),
        },
        {
            "ktsn": "920000000003",
            "taxon_full_nm": "<em>Testus</em> <em>self-cycle</em>",
            "taxon_kor_nm": "자기순환",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"KTSN": "920000000003"}]),
        },
        {
            "ktsn": "920000000004",
            "taxon_full_nm": "<em>Testus</em> <em>missing-target</em>",
            "taxon_kor_nm": "누락대상",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"KTSN": "920000000099"}]),
        },
        {
            "ktsn": "920000000005",
            "taxon_full_nm": "<em>Testus</em> <em>blank-list</em>",
            "taxon_kor_nm": "빈목록",
            "taxon_jm_nm": "이명",
            "correct_list": "",
        },
        {
            "ktsn": "920000000006",
            "taxon_full_nm": "<em>Testus</em> <em>malformed-list</em>",
            "taxon_kor_nm": "잘못된목록",
            "taxon_jm_nm": "이명",
            "correct_list": "not-json",
        },
        {
            "ktsn": "920000000007",
            "taxon_full_nm": "<em>Testus</em> <em>object-list</em>",
            "taxon_kor_nm": "객체목록",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps({"KTSN": "920000000001"}),
        },
        {
            "ktsn": "920000000008",
            "taxon_full_nm": "<em>Testus</em> <em>empty-array</em>",
            "taxon_kor_nm": "빈배열",
            "taxon_jm_nm": "이명",
            "correct_list": "[]",
        },
        {
            "ktsn": "920000000009",
            "taxon_full_nm": "<em>Testus</em> <em>invalid-entry</em>",
            "taxon_kor_nm": "잘못된항목",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"RANK_NM": "Species"}]),
        },
        {
            "ktsn": "920000000010",
            "taxon_full_nm": "<em>Testus</em> <em>conflict-entry</em>",
            "taxon_kor_nm": "충돌항목",
            "taxon_jm_nm": "이명",
            "correct_list": json.dumps([{"KTSN": "920000000001", "KTNS": "920000000002"}]),
        },
    ]
    # Deliberately no terminal row: this chain is longer than the specified 64 transitions.
    for index in range(70):
        current = f"9200000001{index:03d}"
        next_ktsn = f"9200000001{index + 1:03d}"
        rows.append(
            {
                "ktsn": current,
                "taxon_full_nm": f"<em>Testus</em> <em>long-{index}</em>",
                "taxon_kor_nm": f"긴체인{index}",
                "taxon_jm_nm": "이명",
                "correct_list": json.dumps([{"KTSN": next_ktsn}]),
            }
        )
    return rows


@pytest.mark.parametrize(
    "name",
    [
        "Testus cycle-a",
        "Testus self-cycle",
        "Testus missing-target",
        "Testus blank-list",
        "Testus malformed-list",
        "Testus object-list",
        "Testus empty-array",
        "Testus invalid-entry",
        "Testus conflict-entry",
        "Testus long-0",
    ],
)
def test_ac129_recursive_resolution_fails_closed_for_bad_or_unbounded_chains(
    match_ktsn, tmp_path, name
):
    csv_path = tmp_path / "recursive_safety.csv"
    _write_minimal_ktsn_csv(csv_path, _safety_fixture_rows())

    result = match_ktsn(name, str(csv_path))

    assert result["direct_match_found"] is True
    assert result["accepted_resolved"] is False
    assert result["accepted_ktsn"] is None
    assert result["accepted_korean_name"] is None
    assert result["accepted_scientific_name"] is None
    assert result["ambiguous"] or result["unresolved_reason"], (
        "a failed recursive chain must expose the existing unresolved/ambiguous indication"
    )
