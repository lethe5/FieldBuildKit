"""Section 13.3 — Decision Log D-48's five-step KTSN reference-table row-filtering pipeline
(FR-QPB-118, further revised, complete five-step form): per-step, rule-level acceptance tests
for Steps 1-4, independent of the full generated-project bundling mechanism.

Covers:
- AC-QPB-084: Step 1 (Plantae-kingdom-subtree filter via the `p_ktsn` parent-pointer chain).
- AC-QPB-085: Step 2 (`rank_id >= 700` species-level-and-below filter).
- AC-QPB-087: Step 3 (seven-phylum vascular-plants-only allowlist against `r200_nm`).
- AC-QPB-086: Step 4 (duplicate-scientific-name canonical-KTSN resolution against the NIBR
  xlsx's `관속식물류` sheet).

**Why this is a separate file from `test_post_mvp_reference_bundling.py`:** that file exercises
the full five-step pipeline's real, generated-project *artifact* (`reference/ktsn_lookup.csv`,
via `acceptance_api.build_project()`), which only ever exposes the *final* (Step 5) output. Each
step's own row count and inclusion/exclusion rule (rank/phylum/duplicate-name properties of the
rows a given step lets through) is not observable once Step 5 has already reduced every surviving
row down to its 5 lookup columns. This file instead uses the new
`run_ktsn_reference_pipeline()` pure-Python reference-implementation harness function
(HARNESS_CONTRACT.md function 11), which can stop after any of Steps 1-5 and returns each
surviving row with all of its original source columns intact (for `through_step < 5`) — exactly
what AC-QPB-084/085/086/087's own wording requires ("every surviving row's `rank_id` parses as an
integer `>= 700`", "no surviving row has a `rank_id` value at or below ... `600` Genus", "every
surviving row's `r200_nm` value is one of those seven phyla", etc.).

None of this file's tests require a QGIS/PyQGIS runtime (mirroring `test_post_mvp_ktsn_matching.py`
and `test_post_mvp_plantnet_request_shape.py`'s existing precedent for pure-Python rule
validation elsewhere in this same Section 13 round) — `run_ktsn_reference_pipeline()` is a pure
row-filtering function over plain CSV/xlsx files, not a generated QGIS project.

**Two kinds of fixture are used per step, per AC-QPB-084/085/086/087's own "given the real..."
and "given a synthetic fixture..." clauses:**

- The real, full source CSV (`real_ktsn_csv_path`) run in isolation through Steps 1/1-2/1-3 proves
  the exact orchestrator-verified real counts Decision Log D-48 cites (32,251 / 26,763 / 21,025),
  and Step 4's real count (20,914 out of 21,025, 58 duplicated names/118 rows, 7 resolved, 51
  dropped/104 rows removed) against the real NIBR xlsx's `관속식물류` sheet. These real-fixture
  tests are the slow, authoritative half.
- Small, deliberately constructed synthetic fixtures under `fixtures/ktsn_pipeline_step*_synthetic*`
  isolate each step's own edge-case rules quickly and deterministically (a broken/terminating/
  cyclic `p_ktsn` chain for Step 1; a missing/blank/non-numeric `rank_id` for Step 2; a
  bryophyte/algae-under-Plantae/blank `r200_nm` for Step 3; a resolvable duplicate and three
  distinct unresolvable-duplicate sub-variants for Step 4). Every row in every synthetic fixture
  sets `p_ktsn` directly to the literal Plantae-root `ktsn` (`120000098391`) unless the row is
  itself testing Step 1's own chain-traversal behavior — this keeps each small, standalone fixture
  self-contained (Step 1's transitive closure is computed only over the rows present in the same
  file; a small fixture cannot embed a real, multi-level ancestor chain) without weakening the
  step *under test*, since a direct, one-hop child of the Plantae root is unambiguously still "a
  transitive descendant of `120000098391`" per FR-QPB-118's own Step 1 wording. See each test's own
  docstring for its fixture's exact row-by-row construction.

Real-data finding, flagged (not silently resolved) here and in the traceability file's
"Ambiguities" section: a small number of rows in the real, full source CSV carry a literal, stray
extra pair of double-quote characters around every field's value (an apparent upstream
data-serialization artifact), including 2 rows whose `r200_nm` value is the literal text
`"Magnoliophyta"` (quote characters included) rather than `Magnoliophyta`. FR-QPB-118's Step 3
text states only a literal, exact seven-value match, with no normalization rule for this
artifact — yet Decision Log D-48's own cited Step 3 ground truth (26,763 -> 21,025) is only
reproducible if these 2 rows are still counted as matching `Magnoliophyta`. The real-fixture
Step 3 test below asserts the spec's own cited count as ground truth; it does not itself assert
*how* an implementation must normalize this artifact (e.g. stripping stray quote characters),
since the specification's own prose does not say. The synthetic Step 3 fixture below deliberately
uses clean, unquoted phylum values, so it does not depend on this specific ambiguity.
"""
from __future__ import annotations

from pathlib import Path

from .conftest import (
    KTSN_PIPELINE_STEP1_SYNTHETIC_CSV_PATH,
    KTSN_PIPELINE_STEP2_SYNTHETIC_CSV_PATH,
    KTSN_PIPELINE_STEP3_SYNTHETIC_CSV_PATH,
    KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH,
    KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH,
)

PLANTAE_ROOT_KTSN = "120000098391"

ALLOWLISTED_VASCULAR_PHYLA = (
    "Magnoliophyta",
    "Pteridophyta",
    "Pinophyta",
    "Filicophyta",
    "Lycopodiophyta",
    "Psilophyta",
    "Sphenophyta",
)
EXCLUDED_BRYOPHYTE_PHYLA = ("Bryophyta", "Marchantiophyta", "Anthocerophyta")
EXCLUDED_ALGAE_UNDER_PLANTAE_PHYLA = ("Charophyta", "Chlorophyta", "Glaucophyta")


def _ktsns(rows: list[dict]) -> set:
    return {row["ktsn"] for row in rows}


# =====================================================================================
# AC-QPB-084 — Step 1 (Plantae-kingdom-subtree filter)
# =====================================================================================


def test_ac084_step1_synthetic_transitive_closure_edge_cases(run_ktsn_reference_pipeline):
    """AC-QPB-084 (synthetic fixture): `fixtures/ktsn_pipeline_step1_synthetic.csv` contains 6
    rows: a direct child of the Plantae root (survives), a two-hop grandchild of that same row
    (survives, proving the closure is transitive, not just one hop), a row whose `p_ktsn` chain
    terminates on an empty value without ever reaching the root (excluded), a row whose `p_ktsn`
    points at a `ktsn` absent from this file entirely -- a broken chain (excluded), and a two-row
    "other kingdom" lineage whose chain also terminates without reaching the Plantae root
    (excluded, exercising a lineage that never touches Plantae at all, not just a single broken
    row)."""
    result = run_ktsn_reference_pipeline(str(KTSN_PIPELINE_STEP1_SYNTHETIC_CSV_PATH), through_step=1)
    assert result["row_count"] == 2, (
        f"AC-QPB-084: expected exactly 2 survivors (direct child + grandchild); got "
        f"{result['row_count']} ({_ktsns(result['rows'])})"
    )
    assert _ktsns(result["rows"]) == {"200000000001", "200000000002"}, (
        "AC-QPB-084: the direct child and two-hop grandchild of the Plantae root must both "
        f"survive Step 1; got {_ktsns(result['rows'])}"
    )
    excluded_ktsns = {"200000000003", "200000000004", "200000000005", "200000000006"}
    assert not (excluded_ktsns & _ktsns(result["rows"])), (
        "AC-QPB-084: a chain that terminates without reaching the root, a chain broken by a "
        "nonexistent parent, and an other-kingdom lineage must all be excluded from Step 1's "
        f"surviving rows; found some of {excluded_ktsns} unexpectedly present"
    )


def test_ac084_step1_real_full_csv_produces_exactly_32251_survivors(
    run_ktsn_reference_pipeline, real_ktsn_csv_path
):
    """AC-QPB-084 (real fixture): given the real, full, unfiltered source CSV, Step 1 run in
    isolation must produce exactly 32,251 surviving rows (Decision Log D-48's orchestrator-verified
    count) -- not the source's full 212,397 data-row count."""
    result = run_ktsn_reference_pipeline(str(real_ktsn_csv_path), through_step=1)
    assert result["row_count"] == 32_251, (
        "AC-QPB-084: Step 1 run in isolation against the real, full source CSV must produce "
        f"exactly 32,251 surviving rows; got {result['row_count']}"
    )


def test_ac084_step1_real_full_csv_excludes_a_known_non_plantae_row(
    run_ktsn_reference_pipeline, real_ktsn_csv_path
):
    """AC-QPB-084 (real fixture): no row corresponding to a source-CSV row outside the Plantae
    subtree is present among Step 1's survivors -- spot-checked here against a real, known
    non-Plantae (Arthropoda/insect) row already used elsewhere in this suite's own fixtures
    (`ktsn_real_slice.csv`'s `120000033551`, "Gandaritis agnes")."""
    result = run_ktsn_reference_pipeline(str(real_ktsn_csv_path), through_step=1)
    assert "120000033551" not in _ktsns(result["rows"]), (
        "AC-QPB-084: a known real, non-Plantae (Arthropoda) row must not survive Step 1's "
        "Plantae-kingdom-subtree filter"
    )


# =====================================================================================
# AC-QPB-085 — Step 2 (rank_id >= 700 filter)
# =====================================================================================


def test_ac085_step2_synthetic_rank_filter_edge_cases(run_ktsn_reference_pipeline):
    """AC-QPB-085 (synthetic fixture): `fixtures/ktsn_pipeline_step2_synthetic.csv` contains 6
    rows, all trivially surviving Step 1 (`p_ktsn` set directly to the Plantae root): a Species
    (`rank_id=700`, survives), a Subspecies (`rank_id=710`, survives), a Genus (`rank_id=600`,
    excluded), a Family (`rank_id=500`, excluded), a row with a blank `rank_id` (excluded), and a
    row with a non-numeric `rank_id` (`"abc"`, excluded)."""
    result = run_ktsn_reference_pipeline(str(KTSN_PIPELINE_STEP2_SYNTHETIC_CSV_PATH), through_step=2)
    assert result["row_count"] == 2, (
        f"AC-QPB-085: expected exactly 2 survivors (Species + Subspecies); got "
        f"{result['row_count']} ({_ktsns(result['rows'])})"
    )
    assert _ktsns(result["rows"]) == {"200000000101", "200000000102"}
    for row in result["rows"]:
        assert int(row["rank_id"]) >= 700, (
            f"AC-QPB-085: every surviving row's rank_id must parse as an integer >= 700; "
            f"got {row['rank_id']!r} for ktsn {row['ktsn']}"
        )
    excluded_ktsns = {
        "200000000103",  # Genus (600)
        "200000000104",  # Family (500)
        "200000000105",  # blank rank_id
        "200000000106",  # non-numeric rank_id
    }
    assert not (excluded_ktsns & _ktsns(result["rows"])), (
        "AC-QPB-085: genus/family-level rows and rows with a missing/non-numeric rank_id must "
        "never be guess-included"
    )


def test_ac085_step2_real_full_csv_produces_exactly_26763_survivors(
    run_ktsn_reference_pipeline, real_ktsn_csv_path
):
    """AC-QPB-085 (real fixture): of the 32,251 rows surviving Step 1 (AC-QPB-084), Step 2's
    `rank_id >= 700` filter must leave exactly 26,763 rows surviving (Decision Log D-48's
    orchestrator-verified count), and no surviving row may have a rank code at or below a
    genus/family/order-level rank (600/500/400)."""
    result = run_ktsn_reference_pipeline(str(real_ktsn_csv_path), through_step=2)
    assert result["row_count"] == 26_763, (
        "AC-QPB-085: Steps 1-2 run against the real, full source CSV must leave exactly 26,763 "
        f"surviving rows; got {result['row_count']}"
    )
    non_qualifying_ranks = {600, 500, 400}
    offenders = [
        row["ktsn"]
        for row in result["rows"]
        if int(row["rank_id"]) in non_qualifying_ranks
    ]
    assert not offenders, (
        f"AC-QPB-085: no row surviving Step 2 may have a genus/family/order-level rank_id; "
        f"found {offenders[:5]}"
    )


# =====================================================================================
# AC-QPB-087 — Step 3 (vascular-plants-only phylum allowlist)
# =====================================================================================


def test_ac087_step3_synthetic_phylum_allowlist_edge_cases(run_ktsn_reference_pipeline):
    """AC-QPB-087 (synthetic fixture): `fixtures/ktsn_pipeline_step3_synthetic.csv` contains 14
    rows, all trivially surviving Steps 1-2 (`p_ktsn` set directly to the Plantae root,
    `rank_id=700`): one row for each of the 7 allowlisted vascular-plant phyla (all survive), one
    row for each of the 3 bryophyte phyla (`Bryophyta`/`Marchantiophyta`/`Anthocerophyta`, all
    excluded), one row for each of the 3 algae-related phyla this dataset classifies under Plantae
    (`Charophyta`/`Chlorophyta`/`Glaucophyta`, all excluded), and one row with a blank `r200_nm`
    (excluded)."""
    result = run_ktsn_reference_pipeline(str(KTSN_PIPELINE_STEP3_SYNTHETIC_CSV_PATH), through_step=3)
    assert result["row_count"] == 7, (
        f"AC-QPB-087: expected exactly 7 survivors (one per allowlisted phylum); got "
        f"{result['row_count']} ({[r['r200_nm'] for r in result['rows']]})"
    )
    survivor_phyla = {row["r200_nm"] for row in result["rows"]}
    assert survivor_phyla == set(ALLOWLISTED_VASCULAR_PHYLA), (
        f"AC-QPB-087: every surviving row's r200_nm must be one of the seven allowlisted "
        f"vascular-plant phyla, and every one of those seven phyla must be represented; got "
        f"{survivor_phyla}"
    )
    for row in result["rows"]:
        assert row["r200_nm"] not in EXCLUDED_BRYOPHYTE_PHYLA
        assert row["r200_nm"] not in EXCLUDED_ALGAE_UNDER_PLANTAE_PHYLA
        assert row["r200_nm"] != ""


def test_ac087_step3_real_full_csv_produces_exactly_21025_survivors(
    run_ktsn_reference_pipeline, real_ktsn_csv_path
):
    """AC-QPB-087 (real fixture): of the 26,763 rows surviving Steps 1-2 (AC-QPB-085), Step 3's
    seven-phylum vascular-plant allowlist must leave exactly 21,025 rows surviving (Decision Log
    D-48's orchestrator-verified count), and every surviving row's `r200_nm` must be one of the
    seven allowlisted phyla."""
    result = run_ktsn_reference_pipeline(str(real_ktsn_csv_path), through_step=3)
    assert result["row_count"] == 21_025, (
        "AC-QPB-087: Steps 1-3 run against the real, full source CSV must leave exactly 21,025 "
        f"surviving rows; got {result['row_count']}"
    )
    offenders = [
        row["ktsn"] for row in result["rows"] if row["r200_nm"] not in ALLOWLISTED_VASCULAR_PHYLA
    ]
    assert not offenders, (
        "AC-QPB-087: every row surviving Step 3 must have an r200_nm value in the seven-phylum "
        f"allowlist; found {len(offenders)} offender(s), e.g. {offenders[:5]}"
    )


# =====================================================================================
# AC-QPB-086 — Step 4 (duplicate-scientific-name canonical-KTSN resolution)
# =====================================================================================


def test_ac086_step4_synthetic_resolvable_duplicate_keeps_exactly_one_row(
    run_ktsn_reference_pipeline,
):
    """AC-QPB-086 (synthetic fixture, resolvable case): two rows share the normalized name
    "Testus resolvablus" (ktsn `300000000001`/`300000000002`); the synthetic `관속식물류`-shaped
    xlsx fixture maps that same normalized name (written with `<em>` tags, to also exercise
    cross-side normalization) to exactly one distinct KTSN, `300000000001`, which equals one of
    the two duplicate rows' own `ktsn` values. Exactly one row must survive, with that
    corroborated `ktsn`."""
    result = run_ktsn_reference_pipeline(
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH),
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH),
        through_step=4,
    )
    surviving_ktsns = _ktsns(result["rows"])
    assert "300000000001" in surviving_ktsns, (
        "AC-QPB-086: the corroborated row (ktsn matching the xlsx's single found KTSN value) "
        "must survive"
    )
    assert "300000000002" not in surviving_ktsns, (
        "AC-QPB-086: the other duplicate row for the same resolved name must be dropped"
    )
    resolvablus_survivors = [
        row for row in result["rows"] if row["ktsn"] in ("300000000001", "300000000002")
    ]
    assert len(resolvablus_survivors) == 1, (
        "AC-QPB-086: exactly one row must survive for a resolvable duplicated name, not zero and "
        f"not both; got {len(resolvablus_survivors)}"
    )


def test_ac086_step4_synthetic_unresolvable_duplicates_drop_all_variants(
    run_ktsn_reference_pipeline,
):
    """AC-QPB-086 (synthetic fixture, three unresolvable sub-variants): for each of
    "Testus notfoundus" (name absent from the xlsx sheet entirely), "Testus multimatchus" (name
    found mapping to two distinct KTSN values in the xlsx sheet), and "Testus mismatchus" (name
    found with exactly one KTSN value, but it matches neither duplicate row's own `ktsn`), both
    duplicate rows must be dropped entirely -- no fallback heuristic (file order, `taxon_jm_nm`
    accepted/synonym status, or anything else) may rescue either one."""
    result = run_ktsn_reference_pipeline(
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH),
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH),
        through_step=4,
    )
    surviving_ktsns = _ktsns(result["rows"])
    unresolvable_ktsns = {
        "300000000011",
        "300000000012",  # notfoundus
        "300000000021",
        "300000000022",  # multimatchus
        "300000000031",
        "300000000032",  # mismatchus
    }
    offenders = unresolvable_ktsns & surviving_ktsns
    assert not offenders, (
        "AC-QPB-086: every row belonging to an unresolvable duplicated name (not found in the "
        "xlsx; found with more than one distinct KTSN; or found but matching neither duplicate "
        f"row's own ktsn) must be dropped entirely; unexpectedly found {offenders} surviving"
    )


def test_ac086_step4_synthetic_non_duplicated_name_is_unaffected(run_ktsn_reference_pipeline):
    """AC-QPB-086 (synthetic fixture, control case): a non-duplicated (singleton) name must
    survive Step 4 unaffected, regardless of xlsx content -- Step 4's dedup rule only ever
    applies to names appearing on more than one surviving row."""
    result = run_ktsn_reference_pipeline(
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH),
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH),
        through_step=4,
    )
    assert "300000000041" in _ktsns(result["rows"]), (
        "AC-QPB-086: a non-duplicated name must survive Step 4 unaffected"
    )


def test_ac086_step4_synthetic_fixture_combined_row_count(run_ktsn_reference_pipeline):
    """Sanity check tying the three tests above together: of this fixture's 9 rows (all
    trivially surviving Steps 1-3), exactly 2 survive Step 4 -- the one corroborated row from the
    resolvable group, plus the untouched singleton control row."""
    result = run_ktsn_reference_pipeline(
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_CSV_PATH),
        str(KTSN_PIPELINE_STEP4_SYNTHETIC_NIBR_XLSX_PATH),
        through_step=4,
    )
    assert result["row_count"] == 2, (
        f"expected exactly 2 rows surviving Step 4 (1 resolved + 1 singleton); got "
        f"{result['row_count']} ({_ktsns(result['rows'])})"
    )


def test_ac086_step4_real_full_csv_and_xlsx_produces_exactly_20914_survivors(
    run_ktsn_reference_pipeline, real_ktsn_csv_path, real_nibr_xlsx_path
):
    """AC-QPB-086 (real fixture): of the 21,025 rows surviving Steps 1-3 (AC-QPB-087), Step 4's
    duplicate-name resolution against the real NIBR xlsx's `관속식물류` sheet must leave exactly
    20,914 rows surviving (Decision Log D-48's orchestrator-verified combined count: 58 distinct
    duplicated normalized names/118 total rows going in, 7 resolved to exactly one row each, 51
    dropped entirely/104 rows removed)."""
    result = run_ktsn_reference_pipeline(
        str(real_ktsn_csv_path), str(real_nibr_xlsx_path), through_step=4
    )
    assert result["row_count"] == 20_914, (
        "AC-QPB-086: Steps 1-4 run against the real, full source CSV and the real NIBR xlsx's "
        f"관속식물류 sheet must leave exactly 20,914 surviving rows; got {result['row_count']}"
    )
