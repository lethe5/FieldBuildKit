"""Explicit legacy-compatibility tests for qfield_builder.reference_bundle's pre-D-95 helpers.

The normal D-95 canonical release boundary is covered by ``test_reference_source_boundaries.py``;
this module is retained only to protect the explicitly opted-in CSV/NIBR compatibility path.
It must not be read as the normal new-build or release fixture contract.

FR-QPB-105/112/113/118; Decision Log D-35/D-41/D-47/D-48.

Uses small, self-contained fixture directories built with `tmp_path` (never the real ~247 MB
`storage/reference/` scaffold, and never touching `tests/acceptance/**`'s own approved fixtures),
so these run fast and require no gitignored data.

Covers FR-QPB-118 (further revised; Decision Log D-48)'s five-step row-filtering/extraction
pipeline directly at the unit level (each `_step*` function in isolation, plus the public
`run_ktsn_reference_pipeline()` entry point and the `bundle_reference_data()`/
`_extract_ktsn_lookup_csv()` wiring), in addition to what the acceptance suite
(`tests/acceptance/qfield_project_builder/test_post_mvp_ktsn_reference_pipeline.py`/
`test_post_mvp_reference_bundling.py`) already exercises.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from qfield_builder import reference_bundle as rb
from qfield_builder.errors import ReferenceDataInvalidError, ReferenceDataMissingError

pytestmark = pytest.mark.legacy_compatibility

# A row shaped to survive all four of Steps 1-4 unfiltered: a direct child of the Plantae root
# (Step 1), a Species-level rank (Step 2), an allowlisted vascular-plant phylum (Step 3), and a
# `taxon_full_nm` that is not duplicated by any other row in the same fixture (Step 4 no-op).
_VALID_CSV_HEADER = (
    "ktsn,p_ktsn,rank_id,r200_nm,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list\n"
)
_VALID_CSV_ROW = (
    "120000000001,120000098391,700,Magnoliophyta,<em>Testus</em> <em>demo</em>,테스트종,정명,[]\n"
)
_VALID_CSV_ROW_2 = (
    "012000000002,120000098391,700,Magnoliophyta,<em>Alius</em> <em>demo</em>,다른테스트종,이명,\n"
)


def _write_minimal_nibr_xlsx(xlsx_path, extra_rows: list[tuple] | None = None) -> None:
    """Writes a minimal, well-formed NIBR-shaped xlsx with a `관속식물류` sheet whose header row
    matches the real workbook's shape (`KTSN` in column A, `학명` further along the row), and no
    data rows unless `extra_rows` supplies some. This is enough to satisfy FR-QPB-118 Step 4's
    hard requirement that the workbook/sheet/columns exist and be well-formed, for fixtures that
    otherwise have no duplicated `taxon_full_nm` (and therefore never actually need a lookup
    hit)."""
    openpyxl = pytest.importorskip("openpyxl")
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    sheet = workbook.create_sheet(rb.NIBR_VASCULAR_SHEET_NAME)
    header = ["KTSN"] + [None] * 25 + ["학명", "대표국명"]
    sheet.append(header)
    sheet.append([None] * len(header))  # row 2: metadata/blank, per the real workbook's shape
    for row in extra_rows or []:
        sheet.append(list(row))
    workbook.save(str(xlsx_path))


def _make_reference_dir(
    tmp_path,
    csv_text: str | None = _VALID_CSV_HEADER + _VALID_CSV_ROW,
    include_nibr_xlsx: bool = True,
    nibr_xlsx_rows: list[tuple] | None = None,
):
    base = tmp_path / "reference_scaffold"
    tables_dir = base / "tables"
    raster_dir = base / "rasters" / "bce_inverse_corrected_probability_maps"
    tables_dir.mkdir(parents=True)
    raster_dir.mkdir(parents=True)
    if csv_text is not None:
        (tables_dir / "tb_leco_nib_ktsn_dtl_gat.csv").write_text(csv_text, encoding="utf-8")
    (raster_dir / "bce_inverse_corrected_probability_테스트종.tif").write_bytes(b"fake-tif-bytes")
    if include_nibr_xlsx:
        xlsx_path = tables_dir / rb.NATIONAL_LIST_XLSX_RELATIVE_SUBPATH.name
        _write_minimal_nibr_xlsx(xlsx_path, extra_rows=nibr_xlsx_rows)
    return base


def test_validate_reference_data_succeeds_for_a_well_formed_scaffold(tmp_path):
    base = _make_reference_dir(tmp_path)
    csv_path, raster_dir = rb.validate_reference_data(str(base))
    assert csv_path.is_file()
    assert raster_dir.is_dir()


def test_validate_reference_data_raises_when_csv_missing(tmp_path):
    base = tmp_path / "reference_scaffold"
    (base / "tables").mkdir(parents=True)
    (base / "rasters" / "bce_inverse_corrected_probability_maps").mkdir(parents=True)
    with pytest.raises(ReferenceDataMissingError):
        rb.validate_reference_data(str(base))


def test_validate_reference_data_raises_when_raster_dir_missing(tmp_path):
    base = tmp_path / "reference_scaffold"
    tables_dir = base / "tables"
    tables_dir.mkdir(parents=True)
    (tables_dir / "tb_leco_nib_ktsn_dtl_gat.csv").write_text(
        _VALID_CSV_HEADER + _VALID_CSV_ROW, encoding="utf-8"
    )
    with pytest.raises(ReferenceDataMissingError):
        rb.validate_reference_data(str(base))


def test_validate_reference_data_raises_when_required_column_missing(tmp_path):
    base = _make_reference_dir(tmp_path, csv_text="ktsn,taxon_full_nm\n120000000001,Testus demo\n")
    with pytest.raises(ReferenceDataInvalidError):
        rb.validate_reference_data(str(base))


def test_validate_reference_data_raises_when_csv_is_empty(tmp_path):
    base = _make_reference_dir(tmp_path, csv_text="")
    with pytest.raises(ReferenceDataInvalidError):
        rb.validate_reference_data(str(base))


def test_bundle_reference_data_extracts_5_column_lookup_csv_and_copies_rasters_byte_identical(
    tmp_path,
):
    """FR-QPB-112 (revised)/FR-QPB-118 (Decision Log D-48): the bundled KTSN reference asset is
    now the extracted 5-column `reference/ktsn_lookup.csv`, containing only the rows surviving the
    complete five-step pipeline, while the raster-bundling half of FR-QPB-112 remains unaffected
    and unweakened."""
    base = _make_reference_dir(
        tmp_path, csv_text=_VALID_CSV_HEADER + _VALID_CSV_ROW + _VALID_CSV_ROW_2
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    rb.bundle_reference_data(str(base), str(project_dir))

    dest_lookup_csv = project_dir / rb.PROJECT_KTSN_LOOKUP_RELPATH
    assert dest_lookup_csv.is_file()
    assert dest_lookup_csv.parent.name == "reference"
    assert dest_lookup_csv.name == "ktsn_lookup.csv"

    lines = dest_lookup_csv.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list"
    assert len(lines) == 3, "one header row + one data row per source data row surviving Steps 1-4"
    assert lines[1] == "120000000001,<em>Testus</em> <em>demo</em>,테스트종,정명,[]"
    # A leading-zero ktsn value must survive verbatim (preserved as a string, not renormalized as
    # a number), and an empty source `correct_list` must round-trip verbatim, not be coerced to
    # e.g. "[]".
    assert lines[2] == "012000000002,<em>Alius</em> <em>demo</em>,다른테스트종,이명,"

    # The complete, unmodified raw CSV must never be bundled anywhere in the project.
    assert not (project_dir / "reference" / "tables").exists()
    assert not list(project_dir.rglob("tb_leco_nib_ktsn_dtl_gat.csv"))

    dest_raster_dir = project_dir / rb.PROJECT_RASTER_DIR_RELPATH
    tif_files = list(dest_raster_dir.glob("*.tif"))
    assert len(tif_files) == 1
    assert tif_files[0].read_bytes() == b"fake-tif-bytes"


def test_bundle_reference_data_lookup_csv_drops_unrelated_columns(tmp_path):
    """FR-QPB-118: only the 5 required columns are carried forward, even when the source has
    additional columns interleaved before/after them; `p_ktsn`/`rank_id`/`r200_nm` are used only
    for Steps 1-3's row filtering and are not themselves carried into the extracted lookup file."""
    csv_text = (
        "extra_before,ktsn,p_ktsn,rank_id,r200_nm,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,"
        "correct_list,extra_after\n"
        "zzz,120000000001,120000098391,700,Magnoliophyta,Testus demo,테스트종,정명,[],unused\n"
    )
    base = _make_reference_dir(tmp_path, csv_text=csv_text)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    rb.bundle_reference_data(str(base), str(project_dir))

    dest_lookup_csv = project_dir / rb.PROJECT_KTSN_LOOKUP_RELPATH
    lines = dest_lookup_csv.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list"
    assert lines[1] == "120000000001,Testus demo,테스트종,정명,[]"
    assert "extra_before" not in dest_lookup_csv.read_text(encoding="utf-8")
    assert "unused" not in dest_lookup_csv.read_text(encoding="utf-8")


def test_bundle_reference_data_never_crops_multiple_raster_files(tmp_path):
    base = _make_reference_dir(tmp_path)
    raster_dir = base / "rasters" / "bce_inverse_corrected_probability_maps"
    (raster_dir / "bce_inverse_corrected_probability_다른종.tif").write_bytes(b"second-fake-tif")

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    rb.bundle_reference_data(str(base), str(project_dir))

    dest_raster_dir = project_dir / rb.PROJECT_RASTER_DIR_RELPATH
    assert len(list(dest_raster_dir.glob("*.tif"))) == 2


def test_bundle_reference_data_excludes_rows_that_fail_the_five_step_pipeline(tmp_path):
    """FR-QPB-118 (further revised; Decision Log D-48): a row that fails any of Steps 1-3 must not
    appear in the bundled lookup file, even though it satisfies FR-QPB-105's 5-required-column
    check on its own."""
    csv_text = (
        _VALID_CSV_HEADER
        + _VALID_CSV_ROW
        # Fails Step 1: p_ktsn does not resolve to the Plantae root.
        + "120000000099,,700,Magnoliophyta,<em>Nonplantae</em> <em>demo</em>,,정명,\n"
        # Fails Step 2: rank_id is genus-level, not species-level-and-below.
        + "120000000098,120000098391,600,Magnoliophyta,<em>Genuslevel</em> <em>demo</em>,,정명,\n"
        # Fails Step 3: r200_nm is a bryophyte phylum, not vascular-plant.
        + "120000000097,120000098391,700,Bryophyta,<em>Bryo</em> <em>demo</em>,,정명,\n"
    )
    base = _make_reference_dir(tmp_path, csv_text=csv_text)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    rb.bundle_reference_data(str(base), str(project_dir))

    dest_lookup_csv = project_dir / rb.PROJECT_KTSN_LOOKUP_RELPATH
    lines = dest_lookup_csv.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "only the one row surviving all of Steps 1-4 may remain"
    assert lines[1].startswith("120000000001,")


def test_bundle_reference_data_fails_early_when_nibr_xlsx_missing_for_step4(tmp_path):
    """FR-QPB-118 Step 4 (Decision Log D-48): the NIBR xlsx workbook is now a hard build-time
    requirement whenever the identification subsystem is enabled -- if it is absent, the build
    must fail early with a clear message rather than silently skipping Step 4 or bundling an
    unfiltered/partial lookup file."""
    base = _make_reference_dir(tmp_path, include_nibr_xlsx=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    with pytest.raises(ReferenceDataMissingError):
        rb.bundle_reference_data(str(base), str(project_dir))
    assert not (project_dir / rb.PROJECT_KTSN_LOOKUP_RELPATH).exists()
    assert not list(project_dir.rglob("*.tmp"))


def test_bundle_reference_data_fails_early_when_nibr_xlsx_missing_vascular_sheet(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    base = _make_reference_dir(tmp_path, include_nibr_xlsx=False)
    xlsx_path = base / rb.NATIONAL_LIST_XLSX_RELATIVE_SUBPATH
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    workbook.active.title = "무관한시트"
    workbook.save(str(xlsx_path))

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    with pytest.raises(ReferenceDataInvalidError):
        rb.bundle_reference_data(str(base), str(project_dir))
    assert not (project_dir / rb.PROJECT_KTSN_LOOKUP_RELPATH).exists()


def test_bundle_reference_data_fails_early_when_nibr_xlsx_missing_required_headers(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    base = _make_reference_dir(tmp_path, include_nibr_xlsx=False)
    xlsx_path = base / rb.NATIONAL_LIST_XLSX_RELATIVE_SUBPATH
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    sheet = workbook.create_sheet(rb.NIBR_VASCULAR_SHEET_NAME)
    sheet.append(["not_ktsn", "not_the_name_column"])  # neither KTSN nor 학명 present
    workbook.save(str(xlsx_path))

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    with pytest.raises(ReferenceDataInvalidError):
        rb.bundle_reference_data(str(base), str(project_dir))


def test_extract_national_ktsn_list_returns_false_when_xlsx_absent(tmp_path):
    base = _make_reference_dir(tmp_path, include_nibr_xlsx=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    written = rb.extract_and_bundle_national_ktsn_list(str(base), str(project_dir))
    assert written is False
    assert not (project_dir / rb.PROJECT_NATIONAL_LIST_RELPATH).exists()


def test_extract_national_ktsn_list_extracts_only_the_ktsn_column(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    base = _make_reference_dir(tmp_path, include_nibr_xlsx=False)
    xlsx_path = base / rb.NATIONAL_LIST_XLSX_RELATIVE_SUBPATH
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    sheet = workbook.create_sheet(rb.NATIONAL_LIST_XLSX_SHEET_NAME)
    sheet.append(["KTSN", "NO", "관리분류군"])
    sheet.append([None, None, None])
    sheet.append(["120000000006", 1, "녹조류"])
    sheet.append(["120000000007", 2, "녹조류"])
    workbook.save(str(xlsx_path))

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    written = rb.extract_and_bundle_national_ktsn_list(str(base), str(project_dir))
    assert written is True

    dest_path = project_dir / rb.PROJECT_NATIONAL_LIST_RELPATH
    lines = dest_path.read_text(encoding="utf-8").splitlines()
    assert lines == ["120000000006", "120000000007"]


def test_extract_national_ktsn_list_relative_destination_path_is_under_reference_folder():
    assert rb.PROJECT_NATIONAL_LIST_RELPATH.startswith("reference/")
    assert not rb.PROJECT_NATIONAL_LIST_RELPATH.startswith("/")


def test_correct_list_json_is_still_a_valid_marker_column(tmp_path):
    """Sanity check: the required-columns list itself matches FR-QPB-105's documented set."""
    assert set(rb.REQUIRED_KTSN_CSV_COLUMNS) == {
        "ktsn",
        "taxon_full_nm",
        "taxon_kor_nm",
        "taxon_jm_nm",
        "correct_list",
    }
    # `correct_list` values are expected to be JSON; a minimal sanity parse of the fixture value
    # used throughout this file confirms the fixture itself is well-formed.
    assert json.loads("[]") == []


def _write_filtered_bundle_fixture(tmp_path, *, correct_list="[]", accepted_ktsn="1", nibr="1"):
    root = tmp_path / "filtered_bundle"
    filtered = root / rb.FILTERED_REFERENCE_RELPATH
    filtered.mkdir(parents=True)
    (filtered / rb.FILTERED_KTSN_LOOKUP_NAME).write_text(
        "ktsn,taxon_full_nm,taxon_kor_nm,taxon_jm_nm,correct_list\n"
        f"1,Testus demo,테스트종,정명,{correct_list}\n",
        encoding="utf-8",
    )
    (filtered / rb.FILTERED_ACCEPTED_LOOKUP_NAME).write_text(
        f"ktsn,taxon_kor_nm,taxon_full_nm\n{accepted_ktsn},테스트종,Testus demo\n",
        encoding="utf-8",
    )
    (filtered / rb.FILTERED_NIBR_LIST_NAME).write_text(nibr + "\n", encoding="utf-8")
    (root / rb.RASTER_DIR_RELATIVE_SUBPATH).mkdir(parents=True)
    (root / rb.RASTER_DIR_RELATIVE_SUBPATH / "probability.tif").write_bytes(b"tif")

    def artifact(path: str, row_count: int):
        file_path = root / path
        return {
            "path": path,
            "row_count": row_count,
            "sha256": rb._sha256_file(file_path),
        }

    manifest = {
        "pipeline_revision": "FR-QPB-118-D48",
        "artifacts": {
            rb.FILTERED_KTSN_LOOKUP_NAME: artifact(
                f"filtered/{rb.FILTERED_KTSN_LOOKUP_NAME}", 1
            ),
            rb.FILTERED_ACCEPTED_LOOKUP_NAME: artifact(
                f"filtered/{rb.FILTERED_ACCEPTED_LOOKUP_NAME}", 1
            ),
            rb.FILTERED_NIBR_LIST_NAME: artifact(
                f"filtered/{rb.FILTERED_NIBR_LIST_NAME}", 1
            ),
        },
    }
    (root / rb.FILTERED_MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return root


def test_filtered_manifest_rejects_non_json_array_correct_list(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "FILTERED_EXPECTED_KTSN_ROWS", 1)
    root = _write_filtered_bundle_fixture(tmp_path, correct_list="not-json")
    with pytest.raises(ReferenceDataInvalidError, match="correct_list"):
        rb.validate_filtered_reference_data(root)


def test_filtered_manifest_rejects_accepted_row_not_marked_jeongmyeong(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "FILTERED_EXPECTED_KTSN_ROWS", 1)
    root = _write_filtered_bundle_fixture(tmp_path, accepted_ktsn="2")
    with pytest.raises(ReferenceDataInvalidError, match="정명"):
        rb.validate_filtered_reference_data(root)


def test_filtered_manifest_rejects_malformed_single_column_nibr_list(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "FILTERED_EXPECTED_KTSN_ROWS", 1)
    root = _write_filtered_bundle_fixture(tmp_path, nibr="1,2")
    with pytest.raises(ReferenceDataInvalidError, match="한 열"):
        rb.validate_filtered_reference_data(root)


def test_validate_reference_data_rejects_empty_raster_set(tmp_path):
    base = tmp_path / "reference_scaffold"
    (base / "tables").mkdir(parents=True)
    (base / rb.RASTER_DIR_RELATIVE_SUBPATH).mkdir(parents=True)
    (base / rb.KTSN_CSV_RELATIVE_SUBPATH).write_text(
        _VALID_CSV_HEADER + _VALID_CSV_ROW, encoding="utf-8"
    )
    with pytest.raises(ReferenceDataMissingError, match="TIFF"):
        rb.validate_reference_data(base)


def test_prepare_filtered_bundle_canonicalizes_empty_correct_list_and_records_provenance(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(rb, "FILTERED_EXPECTED_KTSN_ROWS", 1)
    source = Path(__file__).resolve().parents[2] / "packaging" / "reference_source"
    canonical_workbook = source / "tables" / "Rpt_2026-08-29_List.xlsx"
    raster_dir = tmp_path / "provisioned-rasters"
    raster_dir.mkdir()
    (raster_dir / "bce_inverse_corrected_probability_테스트종.tif").write_bytes(b"tif")
    destination = tmp_path / "stage"
    rb.prepare_filtered_reference_bundle(
        str(canonical_workbook),
        str(destination),
        raster_dir=str(raster_dir),
    )
    lookup = destination / rb.FILTERED_REFERENCE_RELPATH / rb.FILTERED_KTSN_LOOKUP_NAME
    assert lookup.is_file()
    manifest = json.loads((destination / rb.FILTERED_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["source_provenance"]["input_kind"] == "canonical_workbook"
    assert manifest["source_provenance"]["canonical_workbook"]["path"] == (
        rb.CANONICAL_WORKBOOK_RELATIVE_SUBPATH.as_posix()
    )
    assert manifest["raster_files"]["bce_inverse_corrected_probability_테스트종.tif"]["sha256"]


def test_release_manifest_requires_provenance_and_complete_raster_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "FILTERED_EXPECTED_KTSN_ROWS", 1)
    root = _write_filtered_bundle_fixture(tmp_path)
    manifest_path = root / rb.FILTERED_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pipeline_revision"] = rb.CANONICAL_FILTERED_PIPELINE_REVISION
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReferenceDataInvalidError, match="provenance"):
        rb._validate_filtered_manifest(root, require_release_contract=True)

    manifest["source_provenance"] = {
        "input_kind": "canonical_workbook",
        "canonical_workbook": {
            "path": rb.CANONICAL_WORKBOOK_RELATIVE_SUBPATH.as_posix(),
            "sha256": "0" * 64,
        },
    }
    manifest["artifacts"][rb.FILTERED_KTSN_LOOKUP_NAME]["path"] = (
        rb.FILTERED_REFERENCE_RELPATH / rb.FILTERED_KTSN_LOOKUP_NAME
    ).as_posix()
    manifest["artifacts"][rb.FILTERED_ACCEPTED_LOOKUP_NAME]["path"] = (
        rb.FILTERED_REFERENCE_RELPATH / rb.FILTERED_ACCEPTED_LOOKUP_NAME
    ).as_posix()
    manifest["artifacts"][rb.FILTERED_NIBR_LIST_NAME]["path"] = (
        rb.FILTERED_REFERENCE_RELPATH / rb.FILTERED_NIBR_LIST_NAME
    ).as_posix()
    with pytest.raises(ReferenceDataInvalidError, match="inventory"):
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        rb._validate_filtered_manifest(root, require_release_contract=True)


def test_raw_inputs_win_over_neighboring_filtered_bundle(tmp_path, monkeypatch):
    base = _make_reference_dir(tmp_path)
    filtered = base / rb.FILTERED_REFERENCE_RELPATH
    filtered.mkdir()
    # A structurally valid-looking filtered directory must not shadow the raw source tree.
    (filtered / rb.FILTERED_MANIFEST_NAME).write_text("{not-json", encoding="utf-8")
    csv_path, _raster_dir = rb.validate_reference_data(str(base))
    assert csv_path == base / rb.KTSN_CSV_RELATIVE_SUBPATH
    assert rb.is_filtered_reference_data(base) is False


# ================================================================================================
# FR-QPB-118 (further revised; Decision Log D-48) -- five-step pipeline unit tests
# ================================================================================================


def _row(**kwargs) -> dict:
    base_row = {
        "ktsn": "1",
        "p_ktsn": rb.PLANTAE_ROOT_KTSN,
        "rank_id": "700",
        "r200_nm": "Magnoliophyta",
        "taxon_full_nm": "<em>Testus</em> <em>demo</em>",
        "taxon_kor_nm": "",
        "taxon_jm_nm": "정명",
        "correct_list": "",
    }
    base_row.update(kwargs)
    return base_row


class TestStep1PlantaeSubtreeFilter:
    def test_direct_child_of_root_survives(self):
        rows = [_row(ktsn="1", p_ktsn=rb.PLANTAE_ROOT_KTSN)]
        assert rb._step1_plantae_subtree_filter(rows) == rows

    def test_transitive_grandchild_survives(self):
        rows = [
            _row(ktsn="1", p_ktsn=rb.PLANTAE_ROOT_KTSN),
            _row(ktsn="2", p_ktsn="1"),
        ]
        survivors = rb._step1_plantae_subtree_filter(rows)
        assert {r["ktsn"] for r in survivors} == {"1", "2"}

    def test_terminating_chain_excluded(self):
        rows = [_row(ktsn="1", p_ktsn="")]
        assert rb._step1_plantae_subtree_filter(rows) == []

    def test_broken_chain_excluded(self):
        rows = [_row(ktsn="1", p_ktsn="does-not-exist")]
        assert rb._step1_plantae_subtree_filter(rows) == []

    def test_cycle_excluded(self):
        rows = [
            _row(ktsn="1", p_ktsn="2"),
            _row(ktsn="2", p_ktsn="1"),
        ]
        assert rb._step1_plantae_subtree_filter(rows) == []

    def test_other_kingdom_lineage_excluded(self):
        rows = [
            _row(ktsn="1", p_ktsn="2"),
            _row(ktsn="2", p_ktsn=""),
        ]
        assert rb._step1_plantae_subtree_filter(rows) == []


class TestStep2RankFilter:
    @pytest.mark.parametrize("rank_id", ["700", "710", "999"])
    def test_species_level_and_below_survives(self, rank_id):
        rows = [_row(rank_id=rank_id)]
        assert len(rb._step2_rank_filter(rows)) == 1

    @pytest.mark.parametrize("rank_id", ["600", "500", "400", "100"])
    def test_genus_and_above_excluded(self, rank_id):
        rows = [_row(rank_id=rank_id)]
        assert rb._step2_rank_filter(rows) == []

    @pytest.mark.parametrize("rank_id", ["", None, "abc", "  "])
    def test_missing_blank_or_non_numeric_rank_excluded(self, rank_id):
        rows = [_row(rank_id=rank_id)]
        assert rb._step2_rank_filter(rows) == []

    def test_rank_id_with_surrounding_whitespace_is_parsed(self):
        rows = [_row(rank_id=" 700 ")]
        assert len(rb._step2_rank_filter(rows)) == 1


class TestStep3VascularPhylumAllowlistFilter:
    @pytest.mark.parametrize("phylum", rb.VASCULAR_PHYLUM_ALLOWLIST)
    def test_each_allowlisted_phylum_survives(self, phylum):
        rows = [_row(r200_nm=phylum)]
        survivors = rb._step3_vascular_phylum_allowlist_filter(rows)
        assert len(survivors) == 1
        assert survivors[0]["r200_nm"] == phylum

    @pytest.mark.parametrize(
        "phylum",
        [
            "Bryophyta",
            "Marchantiophyta",
            "Anthocerophyta",
            "Charophyta",
            "Chlorophyta",
            "Glaucophyta",
        ],
    )
    def test_bryophyte_and_algae_phyla_excluded(self, phylum):
        rows = [_row(r200_nm=phylum)]
        assert rb._step3_vascular_phylum_allowlist_filter(rows) == []

    @pytest.mark.parametrize("r200_nm", ["", None])
    def test_missing_or_blank_phylum_excluded(self, r200_nm):
        rows = [_row(r200_nm=r200_nm)]
        assert rb._step3_vascular_phylum_allowlist_filter(rows) == []

    def test_stray_quote_wrapped_value_is_normalized_and_survives(self):
        """See Decision Log D-48's real-data quote-artifact ambiguity note: a small number of real
        rows carry a literal, stray extra pair of double-quote characters wrapped around every
        field's value; this must still be counted as matching its intended phylum."""
        rows = [_row(r200_nm='"Magnoliophyta"')]
        survivors = rb._step3_vascular_phylum_allowlist_filter(rows)
        assert len(survivors) == 1
        assert survivors[0]["r200_nm"] == "Magnoliophyta"

    def test_stray_quote_wrapped_non_allowlisted_value_still_excluded(self):
        rows = [_row(r200_nm='"Bryophyta"')]
        assert rb._step3_vascular_phylum_allowlist_filter(rows) == []


class TestStep4DuplicateNameResolution:
    def test_singleton_name_survives_unaffected(self, tmp_path):
        rows = [_row(ktsn="1", taxon_full_nm="<em>Solo</em> <em>demo</em>")]
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)
        survivors = rb._step4_duplicate_name_resolution(rows, xlsx_path)
        assert [r["ktsn"] for r in survivors] == ["1"]

    def test_duplicate_resolved_via_single_matching_national_list_entry(self, tmp_path):
        rows = [
            _row(ktsn="1", taxon_full_nm="<em>Dup</em> <em>licatus</em>"),
            _row(ktsn="2", taxon_full_nm="<em>Dup</em> <em>licatus</em>"),
        ]
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(
            xlsx_path,
            extra_rows=[
                (["1"] + [None] * 25 + ["Dup licatus", None]),
            ],
        )
        survivors = rb._step4_duplicate_name_resolution(rows, xlsx_path)
        assert [r["ktsn"] for r in survivors] == ["1"]

    def test_duplicate_dropped_when_name_absent_from_national_list(self, tmp_path):
        rows = [
            _row(ktsn="1", taxon_full_nm="<em>Notfound</em> <em>us</em>"),
            _row(ktsn="2", taxon_full_nm="<em>Notfound</em> <em>us</em>"),
        ]
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)
        assert rb._step4_duplicate_name_resolution(rows, xlsx_path) == []

    def test_duplicate_dropped_when_multiple_distinct_ktsn_values_found(self, tmp_path):
        rows = [
            _row(ktsn="1", taxon_full_nm="<em>Multi</em> <em>match</em>"),
            _row(ktsn="2", taxon_full_nm="<em>Multi</em> <em>match</em>"),
        ]
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(
            xlsx_path,
            extra_rows=[
                (["1"] + [None] * 25 + ["Multi match", None]),
                (["99"] + [None] * 25 + ["Multi match", None]),
            ],
        )
        assert rb._step4_duplicate_name_resolution(rows, xlsx_path) == []

    def test_duplicate_dropped_when_found_ktsn_matches_neither_own_row(self, tmp_path):
        rows = [
            _row(ktsn="1", taxon_full_nm="<em>Mis</em> <em>match</em>"),
            _row(ktsn="2", taxon_full_nm="<em>Mis</em> <em>match</em>"),
        ]
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(
            xlsx_path,
            extra_rows=[
                (["99"] + [None] * 25 + ["Mis match", None]),
            ],
        )
        assert rb._step4_duplicate_name_resolution(rows, xlsx_path) == []

    def test_raises_when_xlsx_path_is_none(self):
        rows = [
            _row(ktsn="1", taxon_full_nm="<em>Dup</em>"),
            _row(ktsn="2", taxon_full_nm="<em>Dup</em>"),
        ]
        with pytest.raises(ReferenceDataMissingError):
            rb._step4_duplicate_name_resolution(rows, None)

    def test_raises_when_xlsx_missing(self, tmp_path):
        rows = [_row(ktsn="1")]
        with pytest.raises(ReferenceDataMissingError):
            rb._step4_duplicate_name_resolution(rows, tmp_path / "does_not_exist.xlsx")


class TestRunKtsnReferencePipeline:
    def _write_csv(self, tmp_path, text: str):
        csv_path = tmp_path / "raw.csv"
        csv_path.write_text(text, encoding="utf-8")
        return csv_path

    def test_through_step_1_returns_all_original_columns(self, tmp_path):
        csv_path = self._write_csv(tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW)
        result = rb.run_ktsn_reference_pipeline(str(csv_path), through_step=1)
        assert result["row_count"] == 1
        assert set(result["rows"][0].keys()) == {
            "ktsn", "p_ktsn", "rank_id", "r200_nm", "taxon_full_nm", "taxon_kor_nm",
            "taxon_jm_nm", "correct_list",
        }

    def test_through_step_5_projects_to_5_columns_only(self, tmp_path):
        csv_path = self._write_csv(tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)
        result = rb.run_ktsn_reference_pipeline(str(csv_path), str(xlsx_path), through_step=5)
        assert result["row_count"] == 1
        assert set(result["rows"][0].keys()) == set(rb.REQUIRED_KTSN_CSV_COLUMNS)

    def test_through_step_defaults_to_5(self, tmp_path):
        csv_path = self._write_csv(tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)
        result = rb.run_ktsn_reference_pipeline(str(csv_path), str(xlsx_path))
        assert set(result["rows"][0].keys()) == set(rb.REQUIRED_KTSN_CSV_COLUMNS)

    def test_row_failing_every_step_yields_empty_result(self, tmp_path):
        csv_text = _VALID_CSV_HEADER + (
            "120000000099,,700,Magnoliophyta,<em>Excluded</em>,,정명,\n"
        )
        csv_path = self._write_csv(tmp_path, csv_text)
        result = rb.run_ktsn_reference_pipeline(str(csv_path), through_step=3)
        assert result == {"rows": [], "row_count": 0}


# ================================================================================================
# DR-QPB-072/FR-QPB-126 (Decision Log D-66/D-67) -- derive_accepted_name_lookup_table()
# (HARNESS_CONTRACT.md function 17) unit tests
# ================================================================================================


class TestDeriveAcceptedNameLookupTable:
    """`_VALID_CSV_ROW` (taxon_jm_nm='정명') and `_VALID_CSV_ROW_2` (taxon_jm_nm='이명', a
    synonym) both already survive Steps 1-4 unfiltered (see the module-level fixtures above) --
    exactly the shape needed to isolate FR-QPB-126's own new Step 5 accepted-only filter."""

    def _write_csv(self, tmp_path, text: str):
        csv_path = tmp_path / "raw.csv"
        csv_path.write_text(text, encoding="utf-8")
        return csv_path

    def test_keeps_only_the_accepted_jeongmyeong_row(self, tmp_path):
        csv_path = self._write_csv(
            tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW + _VALID_CSV_ROW_2
        )
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))

        assert result["row_count"] == 1
        assert [row["ktsn"] for row in result["rows"]] == ["120000000001"]

    def test_excludes_a_row_with_blank_taxon_jm_nm(self, tmp_path):
        csv_text = _VALID_CSV_HEADER + (
            "120000000005,120000098391,700,Magnoliophyta,<em>Blank</em> <em>status</em>,,,[]\n"
        )
        csv_path = self._write_csv(tmp_path, csv_text)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        assert result == {"rows": [], "row_count": 0}

    def test_row_shape_is_exactly_three_columns_with_tags_stripped(self, tmp_path):
        csv_path = self._write_csv(tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        assert result["row_count"] == 1
        row = result["rows"][0]
        assert set(row.keys()) == {"ktsn", "taxon_kor_nm", "taxon_full_nm"}
        assert row["ktsn"] == "120000000001"
        assert row["taxon_kor_nm"] == "테스트종"
        assert row["taxon_full_nm"] == "Testus demo", "<em>/</em> tags must be stripped"

    def test_row_excluded_upstream_by_steps_1_to_4_never_reaches_step_5(self, tmp_path):
        """A row failing Step 1 (not a Plantae-subtree descendant) must not survive even though
        its own `taxon_jm_nm` is '정명' -- Steps 1-4 are reused unchanged ahead of the new
        Step 5."""
        csv_text = _VALID_CSV_HEADER + (
            "120000000099,,700,Magnoliophyta,<em>Nonplantae</em> <em>demo</em>,,정명,\n"
        )
        csv_path = self._write_csv(tmp_path, csv_text)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        assert result == {"rows": [], "row_count": 0}

    def test_ktsn_preserved_as_string_with_leading_zero(self, tmp_path):
        csv_path = self._write_csv(
            tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW + _VALID_CSV_ROW_2
        )
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        # _VALID_CSV_ROW_2 has a leading-zero ktsn but is a synonym (이명) -- swap its status to
        # confirm string preservation specifically through the Step 5 filter/projection path.
        accepted_leading_zero_row = _VALID_CSV_ROW_2.replace(",이명,", ",정명,")
        csv_path.write_text(
            _VALID_CSV_HEADER + _VALID_CSV_ROW + accepted_leading_zero_row, encoding="utf-8"
        )

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        ktsns = {row["ktsn"] for row in result["rows"]}
        assert "012000000002" in ktsns

    def test_taxon_kor_nm_may_be_an_empty_string(self, tmp_path):
        csv_text = _VALID_CSV_HEADER + (
            "120000000006,120000098391,700,Magnoliophyta,<em>Noname</em> <em>demo</em>,,정명,[]\n"
        )
        csv_path = self._write_csv(tmp_path, csv_text)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        result = rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        assert result["row_count"] == 1
        assert result["rows"][0]["taxon_kor_nm"] == ""

    def test_reuses_steps_1_to_4_via_run_ktsn_reference_pipeline(self, tmp_path, monkeypatch):
        """FR-QPB-126's own text: reuse the identical, shared Steps 1-4 computation, not a
        second, independent implementation."""
        csv_path = self._write_csv(tmp_path, _VALID_CSV_HEADER + _VALID_CSV_ROW)
        xlsx_path = tmp_path / "nibr.xlsx"
        _write_minimal_nibr_xlsx(xlsx_path)

        calls = []
        original = rb.run_ktsn_reference_pipeline

        def _spy(csv_path_arg, xlsx_path_arg=None, through_step=5):
            calls.append(through_step)
            return original(csv_path_arg, xlsx_path_arg, through_step=through_step)

        monkeypatch.setattr(rb, "run_ktsn_reference_pipeline", _spy)
        rb.derive_accepted_name_lookup_table(str(csv_path), str(xlsx_path))
        assert calls == [4]
