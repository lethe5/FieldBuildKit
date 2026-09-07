"""`match_ktsn()` (HARNESS_CONTRACT.md function 9; FR-QPB-106/107, further revised D-40/D-42).

A pure-Python reference implementation of the direct KTSN name-match (FR-QPB-106) and
accepted-name resolution (FR-QPB-107, further revised) rules, validated against real slices of
the actual KTSN reference CSV by the acceptance suite
(`tests/acceptance/qfield_project_builder/test_post_mvp_ktsn_matching.py`).

This validates the *rules* against real data; the actual shipped mechanism runs as embedded QML
inside QField (see :mod:`qfield_builder.qml_plugin`'s `qpbMatchKtsn` JavaScript function, which
mirrors this implementation's logic line-for-line) -- this module is not itself the shipped
mechanism, per HARNESS_CONTRACT.md's "Post-MVP: Section 13" rationale.
"""

from __future__ import annotations

import csv
import json
import re

_EM_TAG_RE = re.compile(r"</?em>")
_WHITESPACE_RE = re.compile(r"\s+")

_ACCEPTED_STATUS_VALUE = "정명"


def _normalize(text: str | None) -> str:
    if text is None:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def _strip_em_tags(text: str | None) -> str:
    if text is None:
        return ""
    return _normalize(_EM_TAG_RE.sub("", text))


def _empty_result() -> dict:
    return {
        "direct_match_found": False,
        "direct_row_ktsn": None,
        "direct_korean_name": None,
        "direct_scientific_name": None,
        "direct_taxon_jm_nm": None,
        "accepted_resolution_attempted": False,
        "accepted_resolved": False,
        "accepted_ktsn": None,
        "accepted_korean_name": None,
        "accepted_scientific_name": None,
        "ambiguous": False,
        "ambiguous_reason": None,
        "unresolved_reason": None,
    }


def _load_rows(csv_path: str) -> list[dict]:
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _find_by_ktsn(rows: list[dict], ktsn_value: str) -> dict | None:
    for row in rows:
        if row.get("ktsn") == ktsn_value:
            return row
    return None


_MAX_ACCEPTED_NAME_TRANSITIONS = 64


def _correct_list_candidates(
    result: dict,
    row: dict,
    rows: list[dict],
    national_ktsn_set: set[str] | None,
    use_national_list: bool,
) -> list[dict] | None:
    """Return the one next-hop entry, or record a deterministic failure.

    ``correct_list`` is upstream data, so this deliberately treats every shape other than a
    JSON array of objects as malformed.  In particular, accepting a dict here would make a bad
    row look like a valid one-hop resolution and could leak a non-accepted record downstream.
    """
    raw_correct_list = row.get("correct_list") or ""
    try:
        parsed = json.loads(raw_correct_list) if str(raw_correct_list).strip() else []
    except (json.JSONDecodeError, TypeError):
        result["unresolved_reason"] = "correct_list_malformed"
        return None
    if not isinstance(parsed, list) or not parsed:
        result["unresolved_reason"] = (
            "correct_list_empty" if isinstance(parsed, list) else "correct_list_malformed"
        )
        return None

    if len(parsed) == 1:
        return parsed

    if not use_national_list:
        result["unresolved_reason"] = "correct_list_multi_entry_unresolved"
        return None

    national_set = national_ktsn_set or set()
    matches: list[dict] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            result["unresolved_reason"] = "correct_list_invalid_entry"
            return None
        candidate = _entry_ktsn(result, entry)
        if candidate is None:
            return None
        if candidate in national_set:
            matches.append(entry)
    if len(matches) == 1:
        return matches
    result["ambiguous"] = True
    result["ambiguous_reason"] = (
        "no candidate KTSN found in the NIBR accepted-taxon national list"
        if len(matches) == 0
        else "more than one candidate KTSN found in the NIBR accepted-taxon national list"
    )
    return None


def _entry_ktsn(result: dict, entry: object) -> str | None:
    if not isinstance(entry, dict):
        result["unresolved_reason"] = "correct_list_invalid_entry"
        return None
    has_ktsn_key = "KTSN" in entry
    has_ktns_key = "KTNS" in entry
    if not has_ktsn_key and not has_ktns_key:
        result["unresolved_reason"] = "correct_list_missing_ktsn_key"
        return None
    if has_ktsn_key and has_ktns_key:
        left = entry["KTSN"]
        right = entry["KTNS"]
        scalar_types = (str, int, float)
        left_valid = (
            left is not None
            and not isinstance(left, bool)
            and isinstance(left, scalar_types)
            and str(left).strip()
            and str(left).strip().lower() not in {"null", "undefined"}
        )
        right_valid = (
            right is not None
            and not isinstance(right, bool)
            and isinstance(right, scalar_types)
            and str(right).strip()
            and str(right).strip().lower() not in {"null", "undefined"}
        )
        if not left_valid or not right_valid:
            result["unresolved_reason"] = "correct_list_invalid_ktsn"
            return None
        if str(left).strip() != str(right).strip():
            result["ambiguous"] = True
            result["ambiguous_reason"] = "KTSN and KTNS keys present with different values"
            return None
    value = entry["KTSN"] if has_ktsn_key else entry["KTNS"]
    # JSON null becomes the literal string "null" if converted before validation in JavaScript;
    # reject that and other non-scalar/non-identifier values before conversion so the Python
    # reference implementation and embedded QML matcher fail closed in the same way.
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (str, int, float))
        or not str(value).strip()
        or str(value).strip().lower() in {"null", "undefined"}
    ):
        result["unresolved_reason"] = "correct_list_invalid_ktsn"
        return None
    return str(value).strip()


def _resolve_accepted_name_recursively(
    result: dict,
    matched_row: dict,
    rows: list[dict],
    national_ktsn_set: set[str] | None = None,
    use_national_list: bool = False,
) -> None:
    """Follow ``correct_list`` until an exact ``정명`` row, never an intermediate row.

    The transition cap and visited-set check are intentionally applied before looking up the
    next row.  This makes self-references, cycles, and pathological source data fail closed while
    retaining the direct-match fields already placed in ``result``.
    """
    current = matched_row
    visited: set[str] = set()
    transitions = 0
    while True:
        if current.get("taxon_jm_nm") == _ACCEPTED_STATUS_VALUE:
            result["accepted_resolved"] = True
            result["accepted_ktsn"] = current.get("ktsn")
            result["accepted_korean_name"] = current.get("taxon_kor_nm") or None
            result["accepted_scientific_name"] = _strip_em_tags(current.get("taxon_full_nm"))
            return

        current_ktsn = str(current.get("ktsn") or "").strip()
        if current_ktsn and current_ktsn in visited:
            result["unresolved_reason"] = "correct_list_cycle"
            return
        if current_ktsn:
            visited.add(current_ktsn)
        if transitions >= _MAX_ACCEPTED_NAME_TRANSITIONS:
            result["unresolved_reason"] = "correct_list_max_depth_exceeded"
            return

        candidates = _correct_list_candidates(
            result, current, rows, national_ktsn_set, use_national_list
        )
        if candidates is None:
            return
        next_ktsn = _entry_ktsn(result, candidates[0])
        if next_ktsn is None:
            return
        if next_ktsn in visited:
            result["unresolved_reason"] = "correct_list_cycle"
            return
        next_row = _find_by_ktsn(rows, next_ktsn)
        if next_row is None:
            result["unresolved_reason"] = "accepted_ktsn_not_found_in_csv"
            return
        transitions += 1
        current = next_row


def match_ktsn(scientific_name_without_author: str, csv_path: str) -> dict:
    """See HARNESS_CONTRACT.md function 9 for the exact, authoritative contract this implements."""
    result = _empty_result()

    rows = _load_rows(csv_path)
    target = _normalize(scientific_name_without_author)

    matched_row = None
    for row in rows:
        candidate = _strip_em_tags(row.get("taxon_full_nm"))
        if candidate == target:
            matched_row = row
            break

    if matched_row is None:
        return result

    result["direct_match_found"] = True
    result["direct_row_ktsn"] = matched_row.get("ktsn")
    result["direct_korean_name"] = matched_row.get("taxon_kor_nm") or None
    # FR-QPB-106 (revised; Decision Log D-60/D-64): mirrors direct_korean_name exactly -- the
    # directly-matched row's own taxon_full_nm, tag-stripped, populated whenever a direct match is
    # found, independent of whether accepted-name resolution below succeeds.
    result["direct_scientific_name"] = _strip_em_tags(matched_row.get("taxon_full_nm"))
    result["direct_taxon_jm_nm"] = matched_row.get("taxon_jm_nm") or None
    result["accepted_resolution_attempted"] = True

    if result["direct_taxon_jm_nm"] == _ACCEPTED_STATUS_VALUE:
        result["accepted_resolved"] = True
        result["accepted_ktsn"] = result["direct_row_ktsn"]
        result["accepted_korean_name"] = result["direct_korean_name"]
        result["accepted_scientific_name"] = _strip_em_tags(matched_row.get("taxon_full_nm"))
        return result

    _resolve_accepted_name_recursively(result, matched_row, rows)
    return result


def _resolve_chosen_entry(result: dict, chosen_entry: dict, rows: list[dict]) -> None:
    accepted_ktsn = _entry_ktsn(result, chosen_entry)
    if accepted_ktsn is None:
        return
    accepted_row = _find_by_ktsn(rows, accepted_ktsn)
    if accepted_row is None:
        result["unresolved_reason"] = "accepted_ktsn_not_found_in_csv"
        return

    _resolve_accepted_name_recursively(result, accepted_row, rows)


def match_ktsn_with_national_list(
    scientific_name_without_author: str, csv_path: str, national_ktsn_set: set[str] | None = None
) -> dict:
    """FR-QPB-107 (further revised; Decision Log D-40/D-42)-aware variant of :func:`match_ktsn`,
    additionally cross-referencing a multi-entry `correct_list` against the extracted NIBR
    accepted-taxon national list (FR-QPB-113). `national_ktsn_set` is the set of KTSN values
    present in that extracted list (see :func:`qfield_builder.reference_bundle.
    extract_and_bundle_national_ktsn_list`'s output file, one value per line).

    Kept as a separate function from :func:`match_ktsn` because HARNESS_CONTRACT.md's function-9
    contract predates Decision Log D-40/D-42 and documents the multi-entry `correct_list` case as
    an explicitly out-of-scope "known, deliberately-uncovered specification gap" for the acceptance
    tests that call `match_ktsn` directly -- this function does not change that contract, it adds
    the D-40/D-42 behavior as an additive capability for callers (e.g. the QML plugin's mirrored
    logic) that need it.
    """
    result = _empty_result()
    rows = _load_rows(csv_path)
    target = _normalize(scientific_name_without_author)

    matched_row = None
    for row in rows:
        if _strip_em_tags(row.get("taxon_full_nm")) == target:
            matched_row = row
            break
    if matched_row is None:
        return result

    result["direct_match_found"] = True
    result["direct_row_ktsn"] = matched_row.get("ktsn")
    result["direct_korean_name"] = matched_row.get("taxon_kor_nm") or None
    # FR-QPB-106 (revised; Decision Log D-60/D-64): mirrors direct_korean_name exactly -- see
    # match_ktsn's own identical comment above.
    result["direct_scientific_name"] = _strip_em_tags(matched_row.get("taxon_full_nm"))
    result["direct_taxon_jm_nm"] = matched_row.get("taxon_jm_nm") or None
    result["accepted_resolution_attempted"] = True

    if result["direct_taxon_jm_nm"] == _ACCEPTED_STATUS_VALUE:
        result["accepted_resolved"] = True
        result["accepted_ktsn"] = result["direct_row_ktsn"]
        result["accepted_korean_name"] = result["direct_korean_name"]
        result["accepted_scientific_name"] = _strip_em_tags(matched_row.get("taxon_full_nm"))
        return result

    _resolve_accepted_name_recursively(
        result,
        matched_row,
        rows,
        national_ktsn_set=national_ktsn_set,
        use_national_list=True,
    )
    return result
