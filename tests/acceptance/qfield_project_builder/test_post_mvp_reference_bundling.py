"""Explicit legacy-compatibility coverage for the pre-D-95 reference bundling helpers.

The normal new-build and release boundary is canonical D-95 workbook materialization, covered by
``test_d95_canonical_ktsn_reference.py``, ``test_d95_canonical_ktsn_project_regression.py``, and
the release-boundary tests.  This module remains only for callers that explicitly select the
pre-D-95 CSV/NIBR compatibility mode; its placeholder rasters are not a canonical release
fixture.

Covers:
- FR-QPB-105: project creation must fail early with a clear message when the identification
  subsystem is enabled but the KTSN reference CSV is missing or lacks required columns.
- AC-QPB-071 (further revised, Decision Log D-48, complete five-step-pipeline form) /
  FR-QPB-112 (revised, Decision Log D-47): whenever identification is enabled, the build pipeline
  must bundle (1) the build-time-extracted, 5-column `reference/ktsn_lookup.csv` lookup file,
  produced from only the rows surviving all five of FR-QPB-118 (further revised)'s ordered
  row-filtering/extraction steps — never the complete, unmodified raw KTSN CSV, which must not
  appear anywhere in the generated project — and (2) the complete, unmodified probability-raster
  set, exactly as before D-47/D-48 (this half of the requirement is unaffected and must continue
  to pass unweakened).
- AC-QPB-083 / FR-QPB-118 (further revised, Decision Log D-48, complete five-step form): the
  extraction pipeline itself — exact 5-column header/order on the rows surviving Steps 1-4, `ktsn`
  preserved as a string, `correct_list` preserved as valid JSON where present in the source — and
  its early, clear-failure behavior (no silent skip, no fallback to the raw CSV, no partial/
  truncated output) when the source CSV is missing or fails FR-QPB-105's required-column
  validation.

Decision Log D-48 (further extending D-47) inserts four ordered row-filtering steps ahead of the
already-existing column-extraction step (now Step 5): Step 1 (Plantae-kingdom-subtree filter via
the `p_ktsn` parent-pointer chain), Step 2 (`rank_id >= 700` species-level-and-below filter),
Step 3 (seven-phylum vascular-plants-only allowlist against `r200_nm`), and Step 4
(duplicate-scientific-name canonical-KTSN resolution against the NIBR xlsx's `관속식물류` sheet).
Orchestrator-verified real-fixture result: 212,397 raw rows -> 32,251 after Step 1 -> 26,763 after
Step 2 -> 21,025 after Step 3 -> 20,914 after Step 4 -> unchanged through Step 5's column-only
reduction — a final **20,914**-row `reference/ktsn_lookup.csv`, superseding this suite's pre-D-48
expectation that the lookup file would have the same row count as the raw source CSV.

**Two kinds of test are used, mirroring this suite's existing FR-QPB-104/106/107 vs.
FR-QPB-100/101/112 split (see HARNESS_CONTRACT.md's "Post-MVP: Section 13" preamble):**

- This file (`test_post_mvp_reference_bundling.py`) exercises the **bundling mechanism** —
  `build_project()`'s real, generated-project artifact (`reference/ktsn_lookup.csv`, the bundled
  raster set, and relative-path discipline) — via small, `_test_reference_data_dir`-overridden
  fixture directories under `fixtures/` (fast) and, once, directly against the real, full ~183 MB
  source CSV/~247 MB reference scaffold and the real NIBR xlsx workbook, with no override (slow,
  authoritative — the one test that proves the true, complete, real-world 212,397 -> 20,914
  transformation end-to-end). Because every row in this file's own small fixtures was
  deliberately constructed to survive Steps 1-4 unfiltered (a direct child of the Plantae root,
  species rank, an allowlisted phylum, no duplicated name) except where a fixture explicitly
  includes a row constructed to be excluded, this file's own tests validate that filtering is
  correctly *wired into* the bundling pipeline, not the correctness of each filtering *rule* in
  isolation — that per-step correctness is `test_post_mvp_ktsn_reference_pipeline.py`'s job (see
  its own module docstring for AC-QPB-084/085/086/087's Step 1-4 rule-level tests).
- `test_post_mvp_ktsn_reference_pipeline.py` exercises each of Steps 1-4's own row-inclusion/
  exclusion *rules* independently and precisely (including against the real, full source CSV/NIBR
  xlsx, per AC-QPB-084/085/086/087's own "given the real..." clauses), via the new
  `run_ktsn_reference_pipeline()` pure-Python reference-implementation harness function
  (HARNESS_CONTRACT.md function 11).

Ambiguity flagged, not silently resolved (see the traceability file's "Ambiguities" section for
the full note): AC-QPB-071 (further revised)/AC-QPB-083 both require "`correct_list` values
remaining valid JSON," but a full scan of the real, full source CSV performed during test design
found 144,917 of 212,397 rows (~68%) have an *empty string* `correct_list` value, which is not
itself valid JSON. The specification does not say whether an empty source value must round-trip
as an empty string (i.e., "whatever was in the source, verbatim, including non-JSON emptiness") or
must somehow become valid JSON (e.g. an empty array) during extraction. FR-QPB-118's own text —
"this extraction step narrows which columns are carried forward; it does not alter, reformat, or
revalidate the values within the columns it does carry forward beyond what FR-QPB-105 already
requires" — is the most literal instruction available, and is read here as "carry the source value
through unchanged, whatever it is"; these tests therefore assert JSON validity only for rows where
the source value is non-empty, and assert *exact* preservation (verbatim, including emptiness) for
all rows, rather than inventing a "coerce empty to `[]`" behavior the specification never states.

A second, related real-data finding, also flagged (not silently resolved) in the traceability
file's "Ambiguities" section: a small number of rows in the real, full source CSV carry a literal,
stray extra pair of double-quote characters around every field's value (an apparent upstream
data-serialization artifact), including 2 rows whose `r200_nm` value is the literal text
`"Magnoliophyta"` (quote characters included) rather than `Magnoliophyta`. FR-QPB-118's Step 3
text states only a literal, exact seven-value match, with no normalization rule for this
artifact — yet Decision Log D-48's own cited Step 3 ground truth (26,763 -> 21,025) is only
reproducible if these rows are still counted as matching. This file's own slow, authoritative,
real-CSV test asserts the spec's own cited final count as ground truth; it does not itself assert
*how* an implementation must normalize this artifact, since the specification's own prose does
not say.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from .conftest import (
    REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR,
    REFERENCE_DATA_VALID_SAMPLE_DIR,
    make_base_config,
)

pytestmark = [pytest.mark.qgis, pytest.mark.legacy_compatibility]

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
# A dedicated fixture for the AC-QPB-083 extraction-property tests: real 53-column header, three
# real data rows (one with an empty `correct_list`, one with a populated valid-JSON
# `correct_list`), plus one deliberately constructed synthetic row (NOT real reference data) whose
# `ktsn` value has a leading zero — added specifically to make the "preserved as a string, not
# renormalized as a number" property observable, since a full scan of the real ~212,397-row source
# file found zero rows with a leading-zero `ktsn` value. This mirrors this suite's existing
# precedent of mixing real header/rows with a clearly-labeled constructed edge-case row
# (`fixtures/ktsn_synthetic_edge_cases.csv`).
REFERENCE_DATA_KTSN_LOOKUP_SAMPLE_DIR = FIXTURES_DIR / "reference_data_ktsn_lookup_sample"


def _build_with_identification(acceptance_api, tmp_path, reference_data_dir=None, name="proj"):
    """`reference_data_dir=None` (this helper's own default) means "no override requested, use
    the real production dataset" -- this is deliberately relied on by exactly one caller in this
    file, `test_ac071_full_real_reference_dataset_extraction_and_raster_bundling` (see that
    test's own docstring). `make_base_config()` (Decision Log D-70) now supplies its own default
    `_test_reference_data_dir` (pointing at the small `REFERENCE_DATA_VALID_SAMPLE_DIR` fixture)
    for the sake of this suite's many unrelated Types 1-3 tests, so this helper must explicitly
    overwrite that default back to `None` whenever no override was requested here, rather than
    silently inheriting it. `_resolve_reference_data_dir()` (`qfield_builder/build.py`) treats a
    falsy `_test_reference_data_dir` value exactly like an absent key and falls through to the
    `REFERENCE_DATA_DIR` environment variable, then the real, version-controlled-scaffold default
    location -- so `None` here is the correct spelling of "use the real production default."
    """
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = True
    config["_test_reference_data_dir"] = (
        str(reference_data_dir) if reference_data_dir is not None else None
    )
    # This module intentionally exercises the retained pre-D-95 path. Normal new builds must not
    # infer this mode from a legacy fixture or a missing canonical workbook.
    config.pop("canonical_reference_path", None)
    config["reference_compatibility_mode"] = "legacy_reference_compatibility"
    out_dir = tmp_path / name
    return acceptance_api.build_project(config, str(out_dir))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _read_csv_rows(csv_path: Path) -> tuple[list[str], list[list[str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    return header, rows


def _assert_raw_csv_never_bundled(project_dir: Path, source_csv: Path) -> None:
    """AC-QPB-071 (revised)/AC-QPB-083: the complete, unmodified raw KTSN CSV must not appear
    anywhere in the generated project — not at its former `reference/tables/...` location, not
    under any other name or location."""
    assert not (project_dir / "reference" / "tables").exists(), (
        "FR-QPB-112 (revised, D-47): the former reference/tables/ location for the complete raw "
        "KTSN CSV must no longer be created at all"
    )
    matches_by_name = list(project_dir.rglob("tb_leco_nib_ktsn_dtl_gat.csv"))
    assert not matches_by_name, (
        "FR-QPB-112 (revised, D-47): the complete, unmodified raw CSV must not be bundled under "
        f"its original filename anywhere in the project; found: {matches_by_name}"
    )
    source_size = source_csv.stat().st_size
    source_hash = None
    for candidate in project_dir.rglob("*"):
        if not candidate.is_file():
            continue
        if candidate.stat().st_size != source_size:
            continue
        if source_hash is None:
            source_hash = _sha256(source_csv)
        assert _sha256(candidate) != source_hash, (
            "FR-QPB-112 (revised, D-47): the complete, unmodified raw CSV must not be bundled "
            f"anywhere in the project, even under a different name; found at {candidate}"
        )


# --- FR-QPB-105 (early failure) ---------------------------------------------------


RASTER_SUBDIR = Path("rasters") / "bce_inverse_corrected_probability_maps"
KTSN_CSV_SUBDIR = Path("tables") / "tb_leco_nib_ktsn_dtl_gat.csv"  # source-side subpath only

# Destination-side (Decision Log D-47): the new, single build-time-extracted lookup file replacing
# the former complete-raw-CSV bundling location.
KTSN_LOOKUP_RELPATH = Path("reference") / "ktsn_lookup.csv"

REQUIRED_LOOKUP_COLUMNS = (
    "ktsn",
    "taxon_full_nm",
    "taxon_kor_nm",
    "taxon_jm_nm",
    "correct_list",
)


def test_fr105_missing_reference_csv_fails_build_early_with_a_clear_message(
    acceptance_api, tmp_path
):
    empty_reference_dir = tmp_path / "empty_reference_scaffold"
    (empty_reference_dir / "tables").mkdir(parents=True)
    (empty_reference_dir / RASTER_SUBDIR).mkdir(parents=True)

    result = _build_with_identification(
        acceptance_api, tmp_path, reference_data_dir=empty_reference_dir, name="proj_missing_csv"
    )
    assert result["success"] is False, "FR-QPB-105: a missing reference CSV must fail the build"
    assert result.get("error_code"), "expected a non-null error_code, not a bare failure"
    assert result.get("error_message"), (
        "FR-QPB-105: the failure message must be clear, not a bare stack trace/exception"
    )


def test_fr105_reference_csv_missing_required_columns_fails_build_early(acceptance_api, tmp_path):
    result = _build_with_identification(
        acceptance_api,
        tmp_path,
        reference_data_dir=REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR,
        name="proj_bad_columns",
    )
    assert result["success"] is False, (
        "FR-QPB-105: a CSV lacking required columns (ktsn, taxon_full_nm, taxon_kor_nm, "
        "taxon_jm_nm, correct_list) must fail the build"
    )
    assert result.get("error_code")
    assert result.get("error_message")


# --- AC-QPB-083 (new, D-47): the same early-failure conditions must also leave no partial or ----
# --- silently-substituted `reference/ktsn_lookup.csv` output -------------------------------------


def test_ac083_missing_source_csv_fails_early_with_no_partial_project_or_lookup_file(
    acceptance_api, tmp_path
):
    empty_reference_dir = tmp_path / "empty_reference_scaffold_ac083"
    (empty_reference_dir / "tables").mkdir(parents=True)
    (empty_reference_dir / RASTER_SUBDIR).mkdir(parents=True)

    out_dir = tmp_path / "proj_ac083_missing_csv"
    result = _build_with_identification(
        acceptance_api,
        tmp_path,
        reference_data_dir=empty_reference_dir,
        name="proj_ac083_missing_csv",
    )
    assert result["success"] is False, (
        "AC-QPB-083/FR-QPB-118: extraction must not run, and the build must fail, when the "
        "source CSV is missing"
    )
    assert result.get("error_code")
    assert result.get("error_message")
    assert not out_dir.exists() or not any(out_dir.iterdir()), (
        "AC-QPB-083/E-QPB-009: no partially generated project — and in particular no partial or "
        "truncated reference/ktsn_lookup.csv — may exist at the final path after a failed build"
    )


def test_ac083_source_csv_missing_required_columns_fails_early_with_no_partial_lookup_file(
    acceptance_api, tmp_path
):
    out_dir = tmp_path / "proj_ac083_bad_columns"
    result = _build_with_identification(
        acceptance_api,
        tmp_path,
        reference_data_dir=REFERENCE_DATA_MISSING_COLUMNS_SAMPLE_DIR,
        name="proj_ac083_bad_columns",
    )
    assert result["success"] is False, (
        "AC-QPB-083/FR-QPB-118: extraction must not run, and the build must fail, when the "
        "source CSV fails FR-QPB-105's required-column validation"
    )
    assert result.get("error_code")
    assert result.get("error_message")
    assert not out_dir.exists() or not any(out_dir.iterdir()), (
        "AC-QPB-083/E-QPB-009: no partially generated project — and in particular no partial or "
        "truncated reference/ktsn_lookup.csv — may exist at the final path after a failed build"
    )


# --- AC-QPB-071 (further revised, D-47) / FR-QPB-112 (revised) -- fast, mechanism-level ----------


def _is_absolute_or_unc_or_outside_project(path_text: str, project_dir: Path) -> bool:
    if path_text.startswith("/") or path_text.startswith("\\\\"):
        return True
    if re.match(r"^[A-Za-z]:[\\/]", path_text):
        return True
    resolved = (project_dir / path_text).resolve()
    try:
        resolved.relative_to(project_dir.resolve())
    except ValueError:
        return True
    return False


def test_ac071_ktsn_lookup_csv_and_raster_set_are_bundled_with_relative_paths_and_no_raw_csv(
    acceptance_api, tmp_path
):
    """AC-QPB-071 (further revised, Decision Log D-48, complete five-step-pipeline form): (1) the
    extracted `reference/ktsn_lookup.csv` is bundled instead of the complete raw CSV, with the
    exact 5-column header, containing only the rows surviving Steps 1-4 of FR-QPB-118's
    five-step pipeline (**not** the same row count as the raw source CSV — this fixture
    deliberately includes one row, a real insect taxon, that Step 1's Plantae-subtree filter must
    exclude, alongside two rows deliberately constructed to survive every step, so this test can
    confirm the bundling mechanism genuinely narrows the row set rather than merely
    column-projecting every input row unfiltered); (2) the complete, unmodified probability-raster
    set is still bundled exactly as before D-47/D-48 (unaffected, unweakened); and (3) all
    reference-asset paths remain project-relative."""
    result = _build_with_identification(
        acceptance_api,
        tmp_path,
        reference_data_dir=REFERENCE_DATA_VALID_SAMPLE_DIR,
        name="proj_bundling_mechanism",
    )
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])

    # --- (1) KTSN lookup extraction (D-48: five-step-filtered, not a raw pass-through) ----------
    bundled_lookup = project_dir / KTSN_LOOKUP_RELPATH
    assert bundled_lookup.is_file(), (
        "FR-QPB-112 (revised, D-47): expected the build-time-extracted lookup file at "
        "reference/ktsn_lookup.csv"
    )

    source_csv = REFERENCE_DATA_VALID_SAMPLE_DIR / KTSN_CSV_SUBDIR
    source_header, source_rows = _read_csv_rows(source_csv)
    lookup_header, lookup_rows = _read_csv_rows(bundled_lookup)

    assert lookup_header == list(REQUIRED_LOOKUP_COLUMNS), (
        "AC-QPB-071/AC-QPB-083: reference/ktsn_lookup.csv's header must list exactly "
        f"{REQUIRED_LOOKUP_COLUMNS}, in that order; got {lookup_header}"
    )
    assert len(source_rows) == 3, (
        "sanity check: this fixture's own source CSV must have exactly 3 rows (2 deliberately "
        "constructed survivors, 1 deliberately constructed Step-1 exclusion)"
    )
    ktsn_idx = REQUIRED_LOOKUP_COLUMNS.index("ktsn")
    lookup_ktsns = {row[ktsn_idx] for row in lookup_rows}
    assert lookup_ktsns == {"120000526319", "120000528986"}, (
        "AC-QPB-071/FR-QPB-118 (D-48): reference/ktsn_lookup.csv must contain exactly the 2 rows "
        "this fixture constructed to survive every one of Steps 1-4, and must not contain the "
        f"row deliberately excluded by Step 1 (ktsn 120000033551); got {lookup_ktsns}"
    )
    assert len(lookup_rows) == 2 < len(source_rows), (
        "AC-QPB-071/FR-QPB-118 (D-48): the bundled lookup file must have fewer data rows than the "
        "raw source CSV whenever the source contains a row that fails Steps 1-4 -- proving the "
        "bundling mechanism actually applies the five-step filtering pipeline, not merely a "
        "column projection of every input row"
    )

    _assert_raw_csv_never_bundled(project_dir, source_csv)

    # --- (2) Probability-raster bundling (unaffected by D-47 — must still pass, unweakened) -----
    bundled_raster_dir = project_dir / "reference" / RASTER_SUBDIR
    assert bundled_raster_dir.is_dir()
    source_raster_dir = REFERENCE_DATA_VALID_SAMPLE_DIR / RASTER_SUBDIR
    source_files = sorted(p.name for p in source_raster_dir.glob("*.tif"))
    bundled_files = sorted(p.name for p in bundled_raster_dir.glob("*.tif"))
    assert bundled_files == source_files, (
        "FR-QPB-112 (unaffected raster clause): every .tif file present in the source scaffold "
        "must be bundled, with none added, removed, or renamed"
    )
    for name in source_files:
        assert _sha256(bundled_raster_dir / name) == _sha256(source_raster_dir / name), (
            f"FR-QPB-112 (unaffected raster clause): {name} must be bundled byte-identical, "
            "unmodified"
        )

    # --- (3) Relative-path discipline (FR-QPB-091, DR-QPB-012, applied per D-35/D-47) -----------
    qgs_text = Path(result["qgs_path"]).read_text(encoding="utf-8", errors="replace")
    manifest_text = (project_dir / "MANIFEST.json").read_text(encoding="utf-8")
    slug = result["project_slug"]
    plugin_path = project_dir / f"{slug}.qml"
    plugin_text = (
        plugin_path.read_text(encoding="utf-8", errors="replace") if plugin_path.is_file() else ""
    )

    haystacks = (
        (qgs_text, ".qgs"),
        (manifest_text, "MANIFEST.json"),
        (plugin_text, "<slug>.qml"),
    )
    for haystack, label in haystacks:
        for reference_path_str in re.findall(r"reference[\\/][^\"'<>\s]*", haystack):
            assert not _is_absolute_or_unc_or_outside_project(reference_path_str, project_dir), (
                f"FR-QPB-112: reference-asset path {reference_path_str!r} found in {label} must "
                "be relative to the project folder, never absolute and never escaping it"
            )


def test_reference_folder_absent_when_identification_disabled(acceptance_api, tmp_path):
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = False
    out_dir = tmp_path / "proj_no_reference"
    result = acceptance_api.build_project(config, str(out_dir))
    assert result["success"], result.get("error_message")
    assert not (Path(result["project_dir"]) / "reference").exists(), (
        "FR-QPB-090: the reference/ folder is post-MVP-only and must not be created when the "
        "identification subsystem is disabled"
    )


# --- AC-QPB-083 (new, D-47) -- extraction correctness: exact columns, order, row count, ----------
# --- string/JSON preservation --------------------------------------------------------------------


def test_ac083_extraction_preserves_ktsn_as_string_and_correct_list_as_valid_json(
    acceptance_api, tmp_path
):
    """AC-QPB-083/FR-QPB-118 (D-48, complete five-step form): exercises Step 5's extraction
    per-value properties against a fixture containing a mix of real rows (one with an empty
    `correct_list`, one with a populated, valid-JSON `correct_list`) and one deliberately
    constructed synthetic row with a leading-zero `ktsn` value (see this module's docstring and
    the fixture's own generation note). Every one of this fixture's 3 rows was deliberately
    constructed (`p_ktsn` set directly to the Plantae-root `ktsn`, `rank_id=700`/`730`,
    `r200_nm="Magnoliophyta"`, 3 mutually distinct `taxon_full_nm` values) to survive Steps 1-4
    unfiltered, so this test isolates Step 5's own column-projection/string-preservation/
    JSON-preservation mechanics from the separate row-filtering correctness covered by
    `test_post_mvp_ktsn_reference_pipeline.py`."""
    result = _build_with_identification(
        acceptance_api,
        tmp_path,
        reference_data_dir=REFERENCE_DATA_KTSN_LOOKUP_SAMPLE_DIR,
        name="proj_ac083_extraction",
    )
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])

    bundled_lookup = project_dir / KTSN_LOOKUP_RELPATH
    assert bundled_lookup.is_file()

    source_csv = REFERENCE_DATA_KTSN_LOOKUP_SAMPLE_DIR / KTSN_CSV_SUBDIR
    source_header, source_rows = _read_csv_rows(source_csv)
    lookup_header, lookup_rows = _read_csv_rows(bundled_lookup)

    assert lookup_header == list(REQUIRED_LOOKUP_COLUMNS), (
        f"AC-QPB-083: expected exactly {REQUIRED_LOOKUP_COLUMNS} as the header, in that order; "
        f"got {lookup_header}"
    )
    assert len(lookup_rows) == len(source_rows) == 3, (
        "AC-QPB-083: same number of data rows as the source (excluding the source's own header) "
        "-- every row in this fixture was deliberately constructed to survive Steps 1-4; "
        "sanity-checks this fixture's own row count too"
    )

    source_idx = {name: i for i, name in enumerate(source_header)}

    def _source_projection(row: list[str]) -> list[str]:
        return [row[source_idx[col]] for col in REQUIRED_LOOKUP_COLUMNS]

    expected_rows = [_source_projection(row) for row in source_rows]
    # Row order is not asserted to be significant beyond "one data row per source data row" — sort
    # both by ktsn (the natural key) so this test does not depend on an unstated row-ordering
    # guarantee the specification never makes.
    assert sorted(lookup_rows, key=lambda r: r[0]) == sorted(expected_rows, key=lambda r: r[0]), (
        "AC-QPB-083: every extracted row's 5 values must match the corresponding source row's "
        "values in the same 5 columns, verbatim"
    )

    ktsn_idx = REQUIRED_LOOKUP_COLUMNS.index("ktsn")
    correct_list_idx = REQUIRED_LOOKUP_COLUMNS.index("correct_list")

    leading_zero_rows = [r for r in lookup_rows if r[ktsn_idx].startswith("0")]
    assert leading_zero_rows, (
        "sanity check: this fixture's deliberately constructed synthetic row (leading-zero ktsn) "
        "must be present in the extracted output"
    )
    for row in leading_zero_rows:
        assert row[ktsn_idx] == "012345678901", (
            "AC-QPB-083/FR-QPB-118: ktsn values must be preserved as strings, not renormalized as "
            "numbers (a leading zero must survive extraction unchanged)"
        )

    # correct_list: valid JSON where the source itself has a non-empty value; verbatim (including
    # emptiness) otherwise — see this module's docstring "Ambiguity flagged" note.
    for source_row, lookup_row in zip(
        sorted(source_rows, key=lambda r: r[source_idx["ktsn"]]),
        sorted(lookup_rows, key=lambda r: r[ktsn_idx]),
        strict=True,
    ):
        source_cl = source_row[source_idx["correct_list"]]
        lookup_cl = lookup_row[correct_list_idx]
        assert lookup_cl == source_cl, (
            "AC-QPB-083/FR-QPB-118: correct_list values must be preserved exactly as they appear "
            "in the source file"
        )
        if source_cl:
            json.loads(lookup_cl)  # must not raise — AC-QPB-071/AC-QPB-083's "valid JSON" claim

    _assert_raw_csv_never_bundled(project_dir, source_csv)


# --- AC-QPB-071/083 (further revised, D-48) -- slow, authoritative: the real, full ~183 MB CSV ---
# --- + the real NIBR xlsx workbook, run through the complete five-step pipeline ------------------


def test_ac071_full_real_reference_dataset_extraction_and_raster_bundling(
    acceptance_api,
    tmp_path,
    real_ktsn_csv_path,
    real_probability_raster_dir,
    real_nibr_xlsx_path,
    run_ktsn_reference_pipeline,
):
    """The one test that genuinely proves AC-QPB-071/AC-QPB-083 (further revised, Decision Log
    D-48, complete five-step-pipeline form)'s claims against the real, full ~183 MB source CSV,
    the real NIBR xlsx workbook, and the ~64 MB raster set: no `_test_reference_data_dir` override
    here. This is the one test asserting the true, complete, real-world 212,397 -> 20,914
    transformation end-to-end. This may take a noticeable amount of time; that is expected, and
    exactly what Decision Log D-35/D-47/D-48 requires be checked on every enabled build, not a
    test artifact to optimize away.
    """
    result = _build_with_identification(acceptance_api, tmp_path, name="proj_real_reference_full")
    assert result["success"], result.get("error_message")
    project_dir = Path(result["project_dir"])

    bundled_lookup = project_dir / KTSN_LOOKUP_RELPATH
    assert bundled_lookup.is_file()

    lookup_header, lookup_rows = _read_csv_rows(bundled_lookup)
    assert lookup_header == list(REQUIRED_LOOKUP_COLUMNS)

    assert len(lookup_rows) == 20_914, (
        "AC-QPB-071/AC-QPB-083/FR-QPB-118 (Decision Log D-48): reference/ktsn_lookup.csv must "
        "contain exactly the 20,914 rows the orchestrator-verified real-data computation cites "
        "for the complete five-step pipeline (212,397 raw rows -> 32,251 after Step 1 -> 26,763 "
        "after Step 2 -> 21,025 after Step 3 -> 20,914 after Step 4 -> unchanged through Step 5) "
        f"-- got {len(lookup_rows)}"
    )

    # --- Cross-check: build_project()'s real generated artifact must match the independent,
    # --- per-step pipeline reference implementation (HARNESS_CONTRACT.md function 11) run
    # --- directly against the same real CSV/xlsx, not merely happen to agree on a row count.
    pipeline_result = run_ktsn_reference_pipeline(
        str(real_ktsn_csv_path), str(real_nibr_xlsx_path), through_step=5
    )
    assert pipeline_result["row_count"] == 20_914, (
        "sanity check: run_ktsn_reference_pipeline() itself must also compute 20,914 rows for "
        "Steps 1-5 against the same real CSV/xlsx"
    )
    ktsn_idx = REQUIRED_LOOKUP_COLUMNS.index("ktsn")
    bundled_by_ktsn = {row[ktsn_idx]: row for row in lookup_rows}
    pipeline_by_ktsn = {
        row["ktsn"]: [row[col] for col in REQUIRED_LOOKUP_COLUMNS]
        for row in pipeline_result["rows"]
    }
    assert set(bundled_by_ktsn) == set(pipeline_by_ktsn), (
        "AC-QPB-071/AC-QPB-083: the set of ktsn values in the bundled reference/ktsn_lookup.csv "
        "must exactly match the set produced by the independent five-step pipeline reference "
        "implementation, run directly against the same real source data"
    )
    mismatches = [
        (ktsn, bundled_by_ktsn[ktsn], pipeline_by_ktsn[ktsn])
        for ktsn in bundled_by_ktsn
        if bundled_by_ktsn[ktsn] != pipeline_by_ktsn[ktsn]
    ]
    assert not mismatches, (
        f"AC-QPB-071/AC-QPB-083: {len(mismatches)} row(s)' 5-column values differed between the "
        f"real build_project() artifact and the independent pipeline reference implementation "
        f"(showing up to 5): {mismatches[:5]}"
    )

    _assert_raw_csv_never_bundled(project_dir, real_ktsn_csv_path)

    bundled_raster_dir = project_dir / "reference" / RASTER_SUBDIR
    source_files = sorted(p.name for p in real_probability_raster_dir.glob("*.tif"))
    bundled_files = sorted(p.name for p in bundled_raster_dir.glob("*.tif"))
    assert len(source_files) > 0, "sanity check: the real raster scaffold must be non-empty"
    assert bundled_files == source_files, (
        "AC-QPB-071 (unaffected raster clause): every one of the real .tif files must be "
        "bundled, with none missing, added, or renamed (no partial/region-limited subset per "
        "Decision Log D-35)"
    )
    for name in source_files:
        assert _sha256(bundled_raster_dir / name) == _sha256(real_probability_raster_dir / name), (
            f"AC-QPB-071 (unaffected raster clause): {name} must be bundled byte-identical, "
            "unmodified"
        )
