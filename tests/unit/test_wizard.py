"""GUI-level tests for qfield_builder.ui.wizard (offscreen, via tests/unit/conftest.py).

Covers the two defects this implementation round fixes:

1. Output-path workflow (FR-QPB-021/022/022a): the folder the user browses to in Step 1 is an
   *existing parent* directory -- the actual project folder the build must use is always
   `<parent>/<project_slug>/`, never the raw selected directory. See
   :func:`qfield_builder.ui.wizard.compute_final_output_dir` and its use in
   `ProjectBasicsPage`/`ReviewAndBuildPage`.
2. Site/plot upload wiring (FR-QPB-025/030/031): a selected upload path must actually flow into
   `config["sites_upload"]`, and the attribute-mapping/preview step must reflect what will
   actually be imported. The final test in this module exercises the *real* build pipeline
   end-to-end with a real zipped-Shapefile fixture and asserts the imported site data is
   genuinely present in the resulting GeoPackage.

Also covers a later, narrowly-scoped regression fix: `SurveyTypePage`'s "Continue"/"Next" button
must actually re-enable/re-evaluate live when the user clicks a *different* survey-type radio
button after the page has already been shown once -- see
`test_survey_type_page_next_button_updates_live_after_radio_click_post_show` below, which
exercises the real `QWizard` Next button's `isEnabled()` state (not just the field's raw value)
and would have failed against the pre-fix code (empirically verified against an isolated copy of
the pre-fix module during this round -- see the implementer's completion report).
"""
from __future__ import annotations

import sqlite3
import struct
import zipfile
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QScrollArea, QWizard

from qfield_builder import build as build_module
from qfield_builder import credential_store as credential_store_module
from qfield_builder import qgis_worker as qgis_worker_module
from qfield_builder import runtime as runtime_module
from qfield_builder.offline_estimate import (
    OFFLINE_PREGENERATION_THRESHOLD_BYTES,
    estimate_offline_basemap_size,
)
from qfield_builder.ui import wizard as wizard_module
from qfield_builder.ui.wizard import (
    ConnectivityBasemapPage,
    IdentificationTogglePage,
    ProjectBasicsPage,
    ProjectBuilderWizard,
    ReviewAndBuildPage,
    SiteInputPage,
    SurveyTypePage,
    SymbolStylingPage,
    compute_final_output_dir,
)
from qfield_builder.wkt import wkt_to_gpkg_geometry

# DR-QPB-072/FR-QPB-127 (Decision Log D-66/D-68): every Types 1-3 build now resolves/validates
# reference data unconditionally (FR-QPB-105, further revised; Decision Log D-70), not only when
# `identification_enabled`. These build-through-wizard regressions select the D-95 workbook
# explicitly; the small fixture directory contributes only a test raster sidecar.
_REFERENCE_DATA_VALID_SAMPLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "acceptance"
    / "qfield_project_builder"
    / "fixtures"
    / "reference_data_valid_sample"
)
_CANONICAL_REFERENCE_WORKBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "packaging"
    / "reference_source"
    / "tables"
    / "Rpt_2026-08-29_List.xlsx"
)


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------------------------
# Shared zipped-Shapefile fixture builder (adapted from tests/unit/test_shapefile_reader.py).
# ---------------------------------------------------------------------------------------------

SHAPE_TYPE_POLYGON = 5


def _shp_header(shape_type: int) -> bytes:
    header = bytearray(100)
    struct.pack_into(">I", header, 0, 9994)
    struct.pack_into("<I", header, 32, shape_type)
    return bytes(header)


def _polygon_record(points: list[tuple[float, float]]) -> bytes:
    ring = points + [points[0]]
    content = struct.pack("<I", SHAPE_TYPE_POLYGON)
    content += struct.pack("<dddd", 0, 0, 1, 1)
    content += struct.pack("<I", 1)
    content += struct.pack("<I", len(ring))
    content += struct.pack("<I", 0)
    for x, y in ring:
        content += struct.pack("<dd", x, y)
    return content


def _wrap_record(content: bytes) -> bytes:
    header = struct.pack(">II", 1, len(content) // 2)
    return header + content


def _build_shp(shape_type: int, content: bytes) -> bytes:
    return _shp_header(shape_type) + _wrap_record(content)


def _build_dbf(field_name: str, value: str) -> bytes:
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<I", header, 4, 1)
    field_desc_len = 32
    header_len = 32 + field_desc_len + 1
    record_len = 1 + 20
    struct.pack_into("<H", header, 8, header_len)
    struct.pack_into("<H", header, 10, record_len)

    field_desc = bytearray(32)
    name_bytes = field_name.encode("ascii")[:10]
    field_desc[0 : len(name_bytes)] = name_bytes
    field_desc[11] = ord("C")
    field_desc[16] = 20

    terminator = b"\x0d"
    record = b" " + value.ljust(20).encode("ascii")
    eof = b"\x1a"
    return bytes(header) + bytes(field_desc) + terminator + record + eof


def _make_site_zip(tmp_path, field_name: str = "NAME", value: str = "Uploaded Site") -> str:
    shp = _build_shp(
        SHAPE_TYPE_POLYGON,
        _polygon_record([(127.0, 37.0), (127.01, 37.0), (127.01, 37.01), (127.0, 37.01)]),
    )
    dbf = _build_dbf(field_name, value)
    zip_path = tmp_path / "sites.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("sites.shp", shp)
        zf.writestr("sites.dbf", dbf)
    return str(zip_path)


# ---------------------------------------------------------------------------------------------
# 1. Output-path derivation.
# ---------------------------------------------------------------------------------------------


def test_compute_final_output_dir_appends_slug_to_parent():
    result = compute_final_output_dir("/Users/example/Documents", "My Great Project")
    assert result == "/Users/example/Documents/my-great-project"


def test_compute_final_output_dir_none_when_parent_missing():
    assert compute_final_output_dir("", "My Great Project") is None


def test_compute_final_output_dir_none_when_name_invalid():
    assert compute_final_output_dir("/Users/example/Documents", "") is None
    assert compute_final_output_dir("/Users/example/Documents", "..") is None


def test_project_basics_page_preview_shows_full_parent_plus_slug_path(tmp_path):
    page = ProjectBasicsPage()
    page.display_name_edit.setText("My Great Project")
    page.output_dir_edit.setText(str(tmp_path))

    expected = str(tmp_path / "my-great-project")
    assert expected in page.slug_preview_label.text()


def test_project_basics_page_preview_updates_when_name_changes(tmp_path):
    page = ProjectBasicsPage()
    page.output_dir_edit.setText(str(tmp_path))
    page.display_name_edit.setText("First Name")
    assert str(tmp_path / "first-name") in page.slug_preview_label.text()

    page.display_name_edit.setText("Second Name")
    assert str(tmp_path / "second-name") in page.slug_preview_label.text()
    assert "first-name" not in page.slug_preview_label.text()


def test_project_basics_page_preview_updates_when_parent_changes(tmp_path):
    page = ProjectBasicsPage()
    page.display_name_edit.setText("My Project")

    parent_a = tmp_path / "a"
    parent_b = tmp_path / "b"
    page.output_dir_edit.setText(str(parent_a))
    assert str(parent_a / "my-project") in page.slug_preview_label.text()

    page.output_dir_edit.setText(str(parent_b))
    assert str(parent_b / "my-project") in page.slug_preview_label.text()
    assert str(parent_a / "my-project") not in page.slug_preview_label.text()


def test_project_basics_page_preview_before_parent_chosen_does_not_show_raw_parent_as_final():
    page = ProjectBasicsPage()
    page.display_name_edit.setText("My Project")
    # No parent folder chosen yet -- must not claim any final path exists.
    assert "my-project" in page.slug_preview_label.text()
    assert page.output_dir_edit.text() == ""


class _RecordingBuildWorkerThread:
    """Stand-in for BuildWorkerThread that records what it was constructed with and never
    actually starts a real subprocess-backed QThread."""

    instances: list[_RecordingBuildWorkerThread] = []

    def __init__(self, config, output_dir, parent=None):
        self.config = config
        self.output_dir = output_dir
        self.parent = parent
        self.finished_with_result = _FakeSignal()
        self.cancel_called = False
        _RecordingBuildWorkerThread.instances.append(self)

    def start(self) -> None:
        pass  # Intentionally never runs a real build in this test.

    def cancel(self) -> None:
        self.cancel_called = True


class _FakeSignal:
    def connect(self, _slot) -> None:
        pass


@pytest.fixture(autouse=True)
def _reset_recording_instances():
    _RecordingBuildWorkerThread.instances.clear()
    yield
    _RecordingBuildWorkerThread.instances.clear()


def _make_wizard_with_fields(tmp_path, monkeypatch, *, project_name="My Great Project"):
    monkeypatch.setattr(
        runtime_module, "check_runtime", lambda **_kw: {"available": True, "message": ""}
    )
    monkeypatch.setattr(wizard_module, "BuildWorkerThread", _RecordingBuildWorkerThread)

    wizard = ProjectBuilderWizard()
    wizard.setField("project_display_name", project_name)
    wizard.setField("output_dir", str(tmp_path))
    # survey_type/basemap_mode are backed by plain getter methods (no Qt property setter), so
    # QWizard can't write them via setField -- their pages' own defaults ("simple_inventory" /
    # "none") already match what these tests need, so nothing further to set here.
    return wizard


def _set_site_name_field_combo(wizard: ProjectBuilderWizard, field_name: str) -> None:
    """Set SiteInputPage's attribute-mapping combo directly.

    Its registered field is backed by QComboBox's `currentText` property, which (for a
    non-editable combo box, as here) can only be set to a value already present as an item --
    `QWizard.setField` alone can't populate that item list, so tests that need a specific
    mapping selected populate the combo box itself first.
    """
    site_input_page: SiteInputPage = wizard.page(2)
    site_input_page.site_name_field_combo.addItem(field_name)
    site_input_page.site_name_field_combo.setCurrentText(field_name)


def _select_survey_type(wizard: ProjectBuilderWizard, value: str) -> None:
    """Selects the given `survey_type` value on `SurveyTypePage` by clicking its matching radio
    button -- the only way to change this read-only-property-backed field (see
    `SurveyTypePage.surveyType`'s own comment). Tests that exercise `SiteInputPage`'s site-upload
    or drawn-site wiring must call this with a survey type for which sites are actually
    applicable (`temporary_plots`, `permanent_plots`, `vegetation_mapping`) -- `simple_inventory`
    (the default-checked radio) has no `site` entity at all (FR-QPB-025/Section 8.1) and is
    deliberately excluded from site collection by `ReviewAndBuildPage._collect_config()`.
    """
    survey_type_page: SurveyTypePage = wizard.page(1)
    for radio, (radio_value, _label) in zip(
        survey_type_page.radio_buttons, wizard_module.SURVEY_TYPES, strict=True
    ):
        if radio_value == value:
            radio.setChecked(True)
            return
    raise ValueError(f"Unknown survey_type value: {value!r}")


def test_start_build_passes_parent_plus_slug_never_raw_parent(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    review_page._start_build()

    assert len(_RecordingBuildWorkerThread.instances) == 1
    used_output_dir = _RecordingBuildWorkerThread.instances[0].output_dir
    expected = str(tmp_path / "my-great-project")
    assert used_output_dir == expected
    assert used_output_dir != str(tmp_path)  # never the raw selected parent directory


# ---------------------------------------------------------------------------------------------
# 2. Site/plot upload wiring: _collect_config.
# ---------------------------------------------------------------------------------------------


def test_collect_config_wires_zipped_shapefile_upload(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    # Site upload only applies to survey types 2/3/4 -- see `_select_survey_type`'s docstring.
    _select_survey_type(wizard, "temporary_plots")
    wizard.setField("sites_upload_path", "/some/where/sites.zip")
    _set_site_name_field_combo(wizard, "NAME")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["sites_upload"] == {
        "format": "zipped_shapefile",
        "path": "/some/where/sites.zip",
        "attribute_mapping": {"site_name": "NAME"},
        "encoding": "cp949",
    }


def test_collect_config_wires_source_crs_for_shapefile_without_prj(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    _select_survey_type(wizard, "temporary_plots")
    zip_path = _make_site_zip(tmp_path, field_name="NAME", value="Uploaded Site")
    wizard.setField("sites_upload_path", zip_path)
    _set_site_name_field_combo(wizard, "NAME")
    site_input_page: SiteInputPage = wizard.page(2)
    site_input_page.upload_crs_edit.setText("5186")

    config = ReviewAndBuildPage._collect_config(wizard.page(6))

    assert config["sites_upload"]["source_crs"] == "EPSG:5186"



def test_collect_config_wires_gpkg_upload(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    # Site upload only applies to survey types 2/3/4 -- see `_select_survey_type`'s docstring.
    _select_survey_type(wizard, "temporary_plots")
    wizard.setField("sites_upload_path", "/some/where/sites.gpkg")
    _set_site_name_field_combo(wizard, "site_name")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["sites_upload"]["format"] == "gpkg"
    assert config["sites_upload"]["path"] == "/some/where/sites.gpkg"


def test_collect_config_omits_sites_upload_when_no_path_chosen(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    # Site upload only applies to survey types 2/3/4 -- see `_select_survey_type`'s docstring.
    # This exercises "no path chosen" specifically, not the separate `simple_inventory` omission
    # covered by `test_collect_config_omits_site_data_for_simple_inventory_survey_type` below.
    _select_survey_type(wizard, "temporary_plots")
    # sites_upload_path left at its default (empty).

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert "sites_upload" not in config


# ---------------------------------------------------------------------------------------------
# SiteInputPage: attribute-mapping combo + preview (FR-QPB-030/031).
# ---------------------------------------------------------------------------------------------


def test_site_input_page_populates_attribute_fields_and_preview(tmp_path):
    zip_path = _make_site_zip(tmp_path, field_name="NAME", value="Preview Site")
    page = SiteInputPage()

    page.upload_path_edit.setText(zip_path)

    combo = page.site_name_field_combo
    assert combo.isEnabled()
    combo_items = [combo.itemText(i) for i in range(combo.count())]
    assert "NAME" in combo_items

    page.site_name_field_combo.setCurrentText("NAME")
    preview_items = [
        page.preview_list.item(i).text() for i in range(page.preview_list.count())
    ]
    assert len(preview_items) == 1
    assert "Preview Site" in preview_items[0]


def test_site_input_page_rejects_unrecognized_extension(tmp_path):
    bogus_path = tmp_path / "sites.txt"
    bogus_path.write_text("not a supported upload")
    page = SiteInputPage()

    page.upload_path_edit.setText(str(bogus_path))

    assert not page.site_name_field_combo.isEnabled()
    assert "인식할 수 없는 파일 형식" in page.upload_status_label.text()
    assert page.validatePage() is False


def test_site_input_page_empty_upload_path_is_valid():
    page = SiteInputPage()
    assert page.validatePage() is True


def test_site_input_page_requires_epsg_when_shapefile_has_no_prj(tmp_path):
    zip_path = _make_site_zip(tmp_path, field_name="NAME", value="No CRS Site")
    page = SiteInputPage()
    page.upload_path_edit.setText(zip_path)

    assert page._upload_prj_missing is True
    assert page.upload_crs_label.isHidden() is False
    assert page.validatePage() is False

    page.upload_crs_edit.setText("5186")
    assert page.validatePage() is True
    assert page.upload_crs_edit.text() == "EPSG:5186"


# ---------------------------------------------------------------------------------------------
# 3. End-to-end: build_project actually imports the uploaded site into the built GeoPackage.
# ---------------------------------------------------------------------------------------------


def _fake_check_runtime(force_missing: bool = False, manual_path: str | None = None):
    if force_missing:
        return {
            "available": False,
            "message": "No compatible QGIS installation found.",
            "qgis_prefix_path": None,
        }
    return {
        "available": True,
        "message": "Stubbed QGIS runtime for unit testing.",
        "qgis_prefix_path": None,
    }


def _fake_build_qgis_project(
    gpkg_path,
    qgs_path,
    survey_type,
    project_crs,
    basemap_config,
    mbtiles_relative_path=None,
    identification_enabled=False,
    plantnet_config=None,
    svg_relative_path=None,
    ktsn_lookup_table_name=None,
    ktsn_taxonomy_table_name=None,
    offline_source_identity=None,
    probability_raster_relative_path=None,
    canonical_runtime_lookup_resource=None,
):
    from pathlib import Path

    Path(qgs_path).parent.mkdir(parents=True, exist_ok=True)
    Path(qgs_path).write_text(
        f"<qgis projectname='stub'><layer>{gpkg_path}</layer></qgis>", encoding="utf-8"
    )
    plantnet_key_embedded = bool(plantnet_config and plantnet_config.get("consent_accepted"))
    return {"online_key_embedded": False, "plantnet_key_embedded": plantnet_key_embedded}


@pytest.fixture()
def _stub_qgis_for_build(monkeypatch):
    monkeypatch.setattr(runtime_module, "check_runtime", _fake_check_runtime)
    monkeypatch.setattr(build_module, "runtime", runtime_module)
    monkeypatch.setattr(qgis_worker_module, "build_qgis_project", _fake_build_qgis_project)
    monkeypatch.setattr(build_module.qgis_worker, "build_qgis_project", _fake_build_qgis_project)


def test_end_to_end_zipped_shapefile_site_upload_is_imported_into_built_gpkg(
    tmp_path, _stub_qgis_for_build
):
    zip_path = _make_site_zip(tmp_path, field_name="NAME", value="Uploaded Site")

    config = {
        "project_display_name": "Upload Test Project",
        "description": "",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": "temporary_plots",
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "_test_reference_data_dir": str(_REFERENCE_DATA_VALID_SAMPLE_DIR),
        "canonical_reference_path": str(_CANONICAL_REFERENCE_WORKBOOK_PATH),
        "sites_upload": {
            "format": "zipped_shapefile",
            "path": zip_path,
            "attribute_mapping": {"site_name": "NAME"},
            "source_crs": "EPSG:4326",
        },
    }

    out_dir = tmp_path / "out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    gpkg_path = result["gpkg_path"]
    conn = sqlite3.connect(gpkg_path)
    try:
        rows = conn.execute("SELECT site_name, site_geom FROM site;").fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    site_name, site_geom = rows[0]
    assert site_name == "Uploaded Site"
    assert site_geom is not None
    assert bytes(site_geom)[0:2] == b"GP"  # a real GeoPackage geometry blob was written


# ---------------------------------------------------------------------------------------------
# 4. End-to-end: build_project actually imports an uploaded *GeoPackage*-format site upload into
#    the built GeoPackage (genuine .gpkg fixture, not just a path string -- FR-QPB-025).
# ---------------------------------------------------------------------------------------------

_UPLOAD_SITE_WKT = (
    "MULTIPOLYGON(((127.00 37.00, 127.01 37.00, 127.01 37.01, 127.00 37.01, 127.00 37.00)))"
)


def _make_site_gpkg(tmp_path, field_name: str = "site_name", value: str = "Uploaded Site") -> str:
    """Build a minimal, externally-authored-style GeoPackage with one feature layer -- just
    enough of the `gpkg_contents`/`gpkg_geometry_columns` bookkeeping for
    :mod:`qfield_builder.gpkg_upload_reader` to discover and read it, deliberately not built
    through this application's own :func:`qfield_builder.gpkg.build_geopackage` schema builder,
    since an uploaded GeoPackage is not guaranteed to have been produced by it."""
    gpkg_path = tmp_path / "sites.gpkg"
    conn = sqlite3.connect(str(gpkg_path))
    try:
        conn.executescript(
            f"""
            CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT);
            CREATE TABLE gpkg_geometry_columns (
                table_name TEXT, column_name TEXT, geometry_type_name TEXT,
                srs_id INTEGER, z TINYINT, m TINYINT
            );
            CREATE TABLE "sites" (
                "fid" INTEGER PRIMARY KEY AUTOINCREMENT,
                "{field_name}" TEXT,
                "geom" BLOB
            );
            """
        )
        conn.execute(
            "INSERT INTO gpkg_contents (table_name, data_type) VALUES ('sites', 'features');"
        )
        conn.execute(
            "INSERT INTO gpkg_geometry_columns "
            "(table_name, column_name, geometry_type_name, srs_id, z, m) "
            "VALUES ('sites', 'geom', 'MULTIPOLYGON', 4326, 0, 0);"
        )
        blob, _ = wkt_to_gpkg_geometry(_UPLOAD_SITE_WKT, "MULTIPOLYGON", srs_id=4326)
        conn.execute(f'INSERT INTO "sites" ("{field_name}", "geom") VALUES (?, ?);', (value, blob))
        conn.commit()
    finally:
        conn.close()
    return str(gpkg_path)


def test_end_to_end_gpkg_site_upload_is_imported_into_built_gpkg(tmp_path, _stub_qgis_for_build):
    gpkg_upload_path = _make_site_gpkg(tmp_path, field_name="site_name", value="Uploaded Site")

    config = {
        "project_display_name": "GPKG Upload Test Project",
        "description": "",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": "temporary_plots",
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "_test_reference_data_dir": str(_REFERENCE_DATA_VALID_SAMPLE_DIR),
        "canonical_reference_path": str(_CANONICAL_REFERENCE_WORKBOOK_PATH),
        "sites_upload": {
            "format": "gpkg",
            "path": gpkg_upload_path,
            "attribute_mapping": {"site_name": "site_name"},
        },
    }

    out_dir = tmp_path / "gpkg_out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    built_gpkg_path = result["gpkg_path"]
    conn = sqlite3.connect(built_gpkg_path)
    try:
        rows = conn.execute("SELECT site_name, site_geom FROM site;").fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    site_name, site_geom = rows[0]
    assert site_name == "Uploaded Site"
    assert site_geom is not None
    assert bytes(site_geom)[0:2] == b"GP"  # a real GeoPackage geometry blob was written

    # Verify the imported geometry survived the upload round trip correctly (not merely "some
    # geometry was written") by decoding it back through this application's own reader.
    from qfield_builder.gpkg_functions import strip_gpkg_geometry_header
    from qfield_builder.wkt import wkb_to_wkt

    wkt, geom_type = wkb_to_wkt(strip_gpkg_geometry_header(bytes(site_geom)))
    assert geom_type == "MULTIPOLYGON"
    assert wkt == (
        "MULTIPOLYGON(((127.0 37.0, 127.01 37.0, 127.01 37.01, 127.0 37.01, 127.0 37.0)))"
    )


# ---------------------------------------------------------------------------------------------
# 5. SiteInputPage: drawing a site boundary on the map instead of uploading (FR-QPB-025).
# ---------------------------------------------------------------------------------------------


def test_site_input_page_defaults_to_upload_mode():
    page = SiteInputPage()
    page.show()  # isVisible() only reflects the real Qt visibility state once actually shown.
    assert page.input_mode_upload_radio.isChecked()
    assert page.upload_group.isVisible()
    assert not page.draw_group.isVisible()
    assert page.drawn_site_wkt() is None


def test_site_input_page_drawing_a_polygon_produces_valid_site_wkt():
    page = SiteInputPage()
    page.show()
    page.input_mode_draw_radio.setChecked(True)
    assert page.draw_group.isVisible()

    canvas = page.draw_map_canvas
    canvas.add_polygon_vertex_at(50, 50)
    canvas.add_polygon_vertex_at(200, 50)
    canvas.add_polygon_vertex_at(200, 150)
    page._finish_drawn_shape()

    wkt = page.drawn_site_wkt()
    assert wkt is not None
    assert wkt.startswith("MULTIPOLYGON(((")
    from qfield_builder.wkt import validate_geometry

    validate_geometry(wkt, "MULTIPOLYGON")  # must not raise


def test_site_input_page_drawn_site_wkt_is_none_when_upload_mode_selected():
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)
    canvas = page.draw_map_canvas
    canvas.add_polygon_vertex_at(50, 50)
    canvas.add_polygon_vertex_at(200, 50)
    canvas.add_polygon_vertex_at(200, 150)
    page._finish_drawn_shape()
    assert page.drawn_site_wkt() is not None

    # Switching back to upload mode must make the drawn shape inert (not silently used).
    page.input_mode_upload_radio.setChecked(True)
    assert page.drawn_site_wkt() is None


def test_site_input_page_drawn_site_name_defaults_and_can_be_overridden():
    page = SiteInputPage()
    assert page.drawn_site_name() == "그려진 사이트"
    page.draw_site_name_edit.setText("My Custom Site")
    assert page.drawn_site_name() == "My Custom Site"


def test_site_input_page_clear_drawn_shape_resets_state():
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)
    canvas = page.draw_map_canvas
    canvas.add_polygon_vertex_at(50, 50)
    canvas.add_polygon_vertex_at(200, 50)
    canvas.add_polygon_vertex_at(200, 150)
    page._finish_drawn_shape()
    assert page.drawn_site_wkt() is not None

    page._clear_drawn_shape()
    assert page.drawn_site_wkt() is None


def test_collect_config_uses_drawn_site_instead_of_upload(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    # Site input only applies to survey types 2/3/4 -- see `_select_survey_type`'s docstring.
    _select_survey_type(wizard, "temporary_plots")
    wizard.setField("sites_upload_path", "/some/where/sites.zip")
    _set_site_name_field_combo(wizard, "NAME")

    site_input_page: SiteInputPage = wizard.page(2)
    site_input_page.input_mode_draw_radio.setChecked(True)
    canvas = site_input_page.draw_map_canvas
    canvas.add_polygon_vertex_at(20, 20)
    canvas.add_polygon_vertex_at(220, 20)
    canvas.add_polygon_vertex_at(220, 180)
    site_input_page._finish_drawn_shape()
    site_input_page.draw_site_name_edit.setText("Drawn Site A")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert "sites_upload" not in config
    assert config["sites"] == [
        {"site_name": "Drawn Site A", "geom_wkt": site_input_page.drawn_site_wkt()}
    ]


# ---------------------------------------------------------------------------------------------
# 5a. Multiple, individually-named polygons in one drawing session (FR-QPB-129; Decision Log
#     D-75/D-79; AC-QPB-115/116). Routed contract:
#     tests/acceptance/qfield_project_builder_multi_polygon_site_drawing.traceability.md,
#     "tests/unit/test_wizard.py -- per-polygon naming and config["sites"] list construction"
#     table, rows 5-8.
# ---------------------------------------------------------------------------------------------


def _draw_and_finish_triangle(page: SiteInputPage, x0: float, y0: float) -> None:
    canvas = page.draw_map_canvas
    canvas.add_polygon_vertex_at(x0, y0)
    canvas.add_polygon_vertex_at(x0 + 40, y0)
    canvas.add_polygon_vertex_at(x0 + 40, y0 + 40)
    page._finish_drawn_shape()


def test_site_input_page_can_draw_and_individually_name_multiple_separate_polygons():
    """Contract row 5: `SiteInputPage` lets the user assign/confirm a distinct name for each
    individual finished polygon -- not one shared name applied to every polygon in the session."""
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)

    _draw_and_finish_triangle(page, 20, 20)
    page.draw_site_name_edit.setText("Site A")
    page._commit_and_start_new_polygon()

    _draw_and_finish_triangle(page, 200, 200)
    page.draw_site_name_edit.setText("Site B")

    sites = page.drawn_sites()
    assert len(sites) == 2
    assert sites[0]["site_name"] == "Site A"
    assert sites[1]["site_name"] == "Site B"
    assert sites[0]["geom_wkt"] != sites[1]["geom_wkt"]


def test_site_input_page_blank_name_falls_back_to_default_for_that_polygon_only():
    """Contract row 5: leaving one specific polygon's own name blank produces the existing
    non-blank fallback ("그려진 사이트") for that polygon only, without altering any other,
    already-named polygon in the same session."""
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)

    _draw_and_finish_triangle(page, 20, 20)
    page.draw_site_name_edit.setText("")  # left blank for this polygon
    page._commit_and_start_new_polygon()

    _draw_and_finish_triangle(page, 200, 200)
    page.draw_site_name_edit.setText("Site B")

    sites = page.drawn_sites()
    assert sites[0]["site_name"] == "그려진 사이트"
    assert sites[1]["site_name"] == "Site B"


def test_site_input_page_committing_a_second_polygon_never_alters_the_first():
    """Mirrors `MapCanvas`'s own "committing a later polygon never mutates an earlier one"
    guarantee, one layer up at the `SiteInputPage` level."""
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)

    _draw_and_finish_triangle(page, 20, 20)
    page.draw_site_name_edit.setText("Site A")
    page._commit_and_start_new_polygon()

    site_a_after_first_commit = dict(page.drawn_sites()[0])

    _draw_and_finish_triangle(page, 200, 200)
    page.draw_site_name_edit.setText("Site B")
    page._commit_and_start_new_polygon()

    _draw_and_finish_triangle(page, 20, 200)
    page.draw_site_name_edit.setText("Site C")

    sites = page.drawn_sites()
    assert len(sites) == 3
    assert sites[0] == site_a_after_first_commit
    assert [s["site_name"] for s in sites] == ["Site A", "Site B", "Site C"]


def test_site_input_page_commit_without_a_finished_shape_reports_status_and_changes_nothing():
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)

    page._commit_and_start_new_polygon()  # nothing finished yet -- must not raise or commit

    assert page.drawn_sites() == []


def test_collect_config_builds_multi_entry_sites_list_for_each_site_owning_survey_type(
    tmp_path, monkeypatch
):
    """Contract rows 6/8: `ReviewAndBuildPage._collect_config()` builds `config["sites"]` as a
    list with one `{"site_name", "geom_wkt"}` entry per named, finished polygon -- for Type 2,
    Type 3, and Type 4 alike (Decision Log D-79's own scope extension)."""
    for survey_type in ("temporary_plots", "permanent_plots", "vegetation_mapping"):
        wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
        _select_survey_type(wizard, survey_type)

        site_input_page: SiteInputPage = wizard.page(2)
        site_input_page.input_mode_draw_radio.setChecked(True)

        _draw_and_finish_triangle(site_input_page, 20, 20)
        site_input_page.draw_site_name_edit.setText("Site A")
        site_input_page._commit_and_start_new_polygon()

        _draw_and_finish_triangle(site_input_page, 200, 200)
        site_input_page.draw_site_name_edit.setText("Site B")
        site_input_page._commit_and_start_new_polygon()

        _draw_and_finish_triangle(site_input_page, 20, 200)
        site_input_page.draw_site_name_edit.setText("Site C")
        # deliberately left uncommitted -- ending the session by proceeding straight to the
        # review page must still pick this last, finished-but-not-yet-committed polygon up.

        review_page: ReviewAndBuildPage = wizard.page(6)
        config = review_page._collect_config()

        assert "sites_upload" not in config, survey_type
        assert config["sites"] == site_input_page.drawn_sites(), survey_type
        assert [s["site_name"] for s in config["sites"]] == [
            "Site A",
            "Site B",
            "Site C",
        ], survey_type
        geometries = [s["geom_wkt"] for s in config["sites"]]
        assert len(set(geometries)) == 3, (survey_type, geometries)


def test_site_input_page_validate_page_still_true_with_zero_finished_polygons():
    """Contract row 7 (regression guard): zero named polygons remains a valid outcome of one
    drawing session -- `validatePage()`'s existing "drawing is optional" behavior is unchanged."""
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)
    assert page.validatePage() is True
    assert page.drawn_sites() == []


def test_site_input_page_drawn_sites_single_polygon_path_unchanged():
    """Contract row 7 (regression guard): the pre-existing single-polygon path (finish, never
    commit) still produces a correctly single-element list, exactly as before this requirement."""
    page = SiteInputPage()
    page.input_mode_draw_radio.setChecked(True)
    _draw_and_finish_triangle(page, 20, 20)
    page.draw_site_name_edit.setText("Only Site")

    sites = page.drawn_sites()
    assert sites == [{"site_name": "Only Site", "geom_wkt": page.drawn_site_wkt()}]


# ---------------------------------------------------------------------------------------------
# 5b. Regression: no site boundary is asked for/collected for "Simple species inventory"
#     (Type 1, `simple_inventory`). FR-QPB-025 ("when applicable to the selected survey type")
#     and Section 8.1/DR-QPB-008 (Type 1 has no `site` entity at all) already required this; the
#     defect fixed here is that `SiteInputPage` previously showed its upload/draw UI
#     unconditionally regardless of the survey type selected on the prior page.
# ---------------------------------------------------------------------------------------------


def test_site_input_page_hides_upload_and_draw_ui_for_simple_inventory():
    """Once this page becomes current with `survey_type == "simple_inventory"`, its entire
    site-boundary input UI (mode radios, upload group, draw group) must not be presented -- only
    an explanatory "not applicable" message."""
    page = SiteInputPage()
    page.show()

    class _FakeWizard:
        @staticmethod
        def field(name):
            assert name == "survey_type"
            return "simple_inventory"

    page.wizard = lambda: _FakeWizard()
    page.initializePage()

    assert page.not_applicable_label.isVisible()
    assert not page.input_mode_upload_radio.isVisible()
    assert not page.input_mode_draw_radio.isVisible()
    assert not page.upload_group.isVisible()
    assert not page.draw_group.isVisible()


def test_site_input_page_shows_upload_and_draw_ui_for_applicable_survey_types():
    """Sanity check for the fix above: survey types 2/3/4 must still show the normal UI (no
    regression to the FR-QPB-025 behavior that already existed for those types)."""
    page = SiteInputPage()
    page.show()

    class _FakeWizard:
        @staticmethod
        def field(name):
            assert name == "survey_type"
            return "temporary_plots"

    page.wizard = lambda: _FakeWizard()
    page.initializePage()

    assert not page.not_applicable_label.isVisible()
    assert page.input_mode_upload_radio.isVisible()
    assert page.input_mode_draw_radio.isVisible()
    assert page.upload_group.isVisible()  # upload mode is the default-checked radio


def test_site_input_page_not_shown_when_navigating_wizard_for_simple_inventory(
    tmp_path, monkeypatch
):
    """End-to-end through the real `QWizard` page-transition machinery (not a direct
    `initializePage()` call): advancing from Step 2 (survey type, left at its default
    `simple_inventory` selection) to Step 3 must land on `SiteInputPage` with its site-boundary
    input UI already hidden -- the user is never asked to upload or draw a site boundary."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    wizard.show()
    wizard.next()  # ProjectBasicsPage -> SurveyTypePage
    assert wizard.field("survey_type") == "simple_inventory"
    wizard.next()  # SurveyTypePage -> SiteInputPage
    site_input_page = wizard.currentPage()
    assert isinstance(site_input_page, SiteInputPage)

    assert site_input_page.not_applicable_label.isVisible()
    assert not site_input_page.upload_group.isVisible()
    assert not site_input_page.draw_group.isVisible()
    assert site_input_page.drawn_site_wkt() is None


def test_collect_config_omits_site_data_for_simple_inventory_survey_type(tmp_path, monkeypatch):
    """Defense in depth at the point that actually decides what reaches the build pipeline:
    `_collect_config()` must never emit `sites`/`sites_upload` for `simple_inventory`, even if a
    site was uploaded/drawn on the page beforehand (e.g. the user picked a different survey type,
    provided a site, then went back and switched to `simple_inventory`)."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    wizard.setField("sites_upload_path", "/some/where/sites.zip")
    _set_site_name_field_combo(wizard, "NAME")

    site_input_page: SiteInputPage = wizard.page(2)
    site_input_page.input_mode_draw_radio.setChecked(True)
    canvas = site_input_page.draw_map_canvas
    canvas.add_polygon_vertex_at(20, 20)
    canvas.add_polygon_vertex_at(220, 20)
    canvas.add_polygon_vertex_at(220, 180)
    site_input_page._finish_drawn_shape()

    # survey_type is left at its default ("simple_inventory") -- see `SurveyTypePage.__init__`.
    assert wizard.field("survey_type") == "simple_inventory"

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert "sites" not in config
    assert "sites_upload" not in config


def test_build_project_succeeds_for_simple_inventory_with_no_site_data(
    tmp_path, _stub_qgis_for_build
):
    """The build pipeline itself (not just the wizard UI) must complete successfully for Type 1
    with no site data present at all -- Section 8.1's schema has no `site` entity/relation, so
    `build.py` must never require one."""
    config = {
        "project_display_name": "Simple Inventory Project",
        "description": "",
        "project_crs": "EPSG:5186",
        "storage_crs": "EPSG:4326",
        "survey_type": "simple_inventory",
        "basemap": {"mode": "none"},
        "identification_enabled": False,
        "_test_reference_data_dir": str(_REFERENCE_DATA_VALID_SAMPLE_DIR),
        "canonical_reference_path": str(_CANONICAL_REFERENCE_WORKBOOK_PATH),
    }

    out_dir = tmp_path / "simple_inventory_out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    conn = sqlite3.connect(result["gpkg_path"])
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "site" not in tables


# ---------------------------------------------------------------------------------------------
# 6. ConnectivityBasemapPage: offline basemap bbox/zoom UI wiring (FR-QPB-034-036/080-089).
# ---------------------------------------------------------------------------------------------

_SMALL_TEST_BBOX = {"min_lon": 127.00, "min_lat": 37.00, "max_lon": 127.01, "max_lat": 37.01}


def test_connectivity_page_defaults_to_upload_bbox_source():
    page = ConnectivityBasemapPage()
    page.show()  # isVisible() only reflects the real Qt visibility state once actually shown.
    page.offline_radio.setChecked(True)  # the offline group itself is only shown in this mode.
    assert page.offline_bbox_source_upload_radio.isChecked()
    assert page.offline_upload_path_edit.isVisible()
    assert not page.offline_map_canvas.isVisible()


def test_connectivity_page_draw_bbox_populates_offline_config():
    page = ConnectivityBasemapPage()
    page.show()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    assert page.offline_map_canvas.isVisible()

    canvas = page.offline_map_canvas
    canvas.start_bbox_at(50, 50)
    canvas.finish_bbox_at(200, 150)

    offline_cfg = page.offline_config()
    assert offline_cfg["bbox"] is not None
    assert offline_cfg["bbox"]["min_lon"] <= offline_cfg["bbox"]["max_lon"]
    assert offline_cfg["bbox"]["min_lat"] <= offline_cfg["bbox"]["max_lat"]
    assert offline_cfg["min_zoom"] == page.min_zoom_spin.value()
    assert offline_cfg["max_zoom"] == page.max_zoom_spin.value()


def test_connectivity_page_estimate_label_reflects_estimate_offline_basemap_size():
    page = ConnectivityBasemapPage()
    page.offline_bbox_source_draw_radio.setChecked(True)
    page._offline_bbox = dict(_SMALL_TEST_BBOX)
    page.min_zoom_spin.setValue(10)
    page.max_zoom_spin.setValue(12)
    page._update_offline_estimate()

    expected = estimate_offline_basemap_size(_SMALL_TEST_BBOX, 10, 12, 15000.0)
    label_text = page.offline_estimate_label.text()
    assert str(expected["tile_count"]) in label_text
    expected_mib = expected["estimated_bytes"] / (1024 * 1024)
    assert f"{expected_mib:.1f}" in label_text
    assert "1 GiB" in label_text
    assert "900 MiB" in label_text
    assert not page._offline_blocked


def test_connectivity_page_blocks_when_estimate_exceeds_pregeneration_threshold():
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    # A deliberately huge bbox/zoom combination, chosen to comfortably exceed the 900 MiB
    # pre-generation threshold (verified below against the real estimator, not assumed).
    huge_bbox = {"min_lon": 120.0, "min_lat": 30.0, "max_lon": 135.0, "max_lat": 45.0}
    page._offline_bbox = huge_bbox
    page.min_zoom_spin.setValue(0)
    page.max_zoom_spin.setValue(18)
    page._update_offline_estimate()

    estimate = estimate_offline_basemap_size(huge_bbox, 0, 18, 15000.0)
    assert estimate["exceeds_pregeneration_threshold"]
    assert estimate["estimated_bytes"] > OFFLINE_PREGENERATION_THRESHOLD_BYTES

    assert page._offline_blocked is True
    assert "BLOCKED" in page.offline_estimate_label.text()
    assert page.validatePage() is False


def test_connectivity_page_validate_page_true_for_online_and_none_modes_regardless_of_state():
    page = ConnectivityBasemapPage()
    # No offline bbox has ever been set -- must not block online/none modes.
    page.none_radio.setChecked(True)
    assert page.validatePage() is True
    page.online_radio.setChecked(True)
    assert page.validatePage() is True


def test_connectivity_page_validate_page_false_when_offline_selected_without_bbox():
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    assert page._offline_bbox is None
    assert page.validatePage() is False


def test_connectivity_page_validate_page_true_when_offline_bbox_set_and_within_limit():
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    page.layer_combo.activated.emit(page.layer_combo.currentIndex())
    page._offline_bbox = dict(_SMALL_TEST_BBOX)
    page.min_zoom_spin.setValue(10)
    page.max_zoom_spin.setValue(12)
    page._update_offline_estimate()
    assert page.validatePage() is True


def test_connectivity_page_requires_explicit_offline_layer_choice_when_multiple_exist():
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    page._offline_bbox = dict(_SMALL_TEST_BBOX)
    page._update_offline_estimate()

    # The shared combo visibly starts on the online selector's existing first item, but that
    # implicit value must not count as an offline download choice.
    assert page.layer_combo.currentText() == "Base"
    assert page.validatePage() is False

    # A programmatic change is not a deliberate user choice either.
    page.layer_combo.setCurrentText("White")
    assert page.validatePage() is False

    # QComboBox.activated is the user-activation seam used by the widget implementation.
    page.layer_combo.activated.emit(page.layer_combo.currentIndex())
    assert page.validatePage() is True
    assert page.offline_config()["layer"] == "White"


def test_connectivity_page_refresh_invalidates_disappeared_offline_layer_until_reselected():
    catalogs = iter([["Base", "White"], ["Satellite"]])

    def _fetch_layers(_api_key: str) -> list[str]:
        return next(catalogs)

    page = ConnectivityBasemapPage(fetch_layers_fn=_fetch_layers)
    page.api_key_edit.setText("MY-TEST-KEY")
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    page._offline_bbox = dict(_SMALL_TEST_BBOX)
    page._update_offline_estimate()

    page._refresh_vworld_layers()
    page.layer_combo.setCurrentText("Base")
    page.layer_combo.activated.emit(page.layer_combo.currentIndex())
    assert page.validatePage() is True

    page._refresh_vworld_layers()

    # Re-population must not let Qt silently replace the stale Base choice with Satellite.
    assert page.layer_combo.currentIndex() == -1
    assert page.offline_config()["layer"] == ""
    assert page.validatePage() is False

    page.layer_combo.setCurrentText("Satellite")
    assert page.validatePage() is False
    page.layer_combo.activated.emit(page.layer_combo.currentIndex())
    assert page.validatePage() is True
    assert page.offline_config()["layer"] == "Satellite"


def test_collect_config_wires_offline_bbox_min_max_zoom(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.offline_radio.setChecked(True)
    basemap_page.offline_bbox_source_draw_radio.setChecked(True)
    basemap_page._offline_bbox = dict(_SMALL_TEST_BBOX)
    basemap_page.min_zoom_spin.setValue(11)
    basemap_page.max_zoom_spin.setValue(13)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["mode"] == "offline"
    assert config["basemap"]["bbox"] == _SMALL_TEST_BBOX
    assert config["basemap"]["min_zoom"] == 11
    assert config["basemap"]["max_zoom"] == 13


# ---------------------------------------------------------------------------------------------
# 6b. Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058; see
#     tests/acceptance/qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.
#     traceability.md's contract rows 1(a)/1(b)): the VWorld API key input must be genuinely
#     reachable (visible/enabled) when offline mode is selected -- not only online mode -- and a
#     typed-in key must actually reach `config["basemap"]["vworld_api_key"]` for offline builds.
# ---------------------------------------------------------------------------------------------


def test_connectivity_page_api_key_input_is_reachable_when_offline_mode_selected():
    """Contract row 1(a): mirrors the established pattern at
    `test_connectivity_page_defaults_to_upload_bbox_source` (`page.show()` then `isVisible()`)."""
    page = ConnectivityBasemapPage()
    page.show()  # isVisible() only reflects the real Qt visibility state once actually shown.
    page.offline_radio.setChecked(True)
    assert page.api_key_edit.isVisible() is True
    assert page.api_key_edit.isEnabled() is True
    page.hide()


def test_connectivity_page_api_key_input_is_still_reachable_when_online_mode_selected():
    """Companion regression check (contract row 1(a)): the fix for offline mode must not regress
    the pre-existing, already-correct online-mode case."""
    page = ConnectivityBasemapPage()
    page.show()
    page.online_radio.setChecked(True)
    assert page.api_key_edit.isVisible() is True
    assert page.api_key_edit.isEnabled() is True
    page.hide()


def test_connectivity_page_api_key_input_is_hidden_when_no_basemap_mode_selected():
    """The VWorld key is only ever needed for online/offline mode -- hidden for "배경지도 없음"."""
    page = ConnectivityBasemapPage()
    page.show()
    page.none_radio.setChecked(True)
    assert page.api_key_edit.isVisible() is False
    page.hide()


def test_collect_config_wires_offline_vworld_api_key(tmp_path, monkeypatch):
    """Contract row 1(b): a typed-in offline-mode VWorld key must reach
    `config["basemap"]["vworld_api_key"]`, using `_on_bbox_drawn`'s own existing direct-call hook
    (the same deterministic-drawing convention `test_map_canvas.py` already establishes) to supply
    an offline bbox without depending on synthetic mouse-event delivery."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.offline_radio.setChecked(True)
    basemap_page.offline_bbox_source_draw_radio.setChecked(True)
    basemap_page.api_key_edit.setText("test-offline-key")
    basemap_page._on_bbox_drawn(dict(_SMALL_TEST_BBOX))

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["mode"] == "offline"
    assert config["basemap"]["vworld_api_key"] == "test-offline-key"


def test_collect_config_online_vworld_api_key_collection_is_unaffected_by_the_offline_fix(
    tmp_path, monkeypatch
):
    """Companion regression assertion (contract row 1(b)): the existing online-mode collection
    must remain unaffected by the offline-mode fix above."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("test-online-key")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["mode"] == "online"
    assert config["basemap"]["vworld_api_key"] == "test-online-key"


# ---------------------------------------------------------------------------------------------
# 6c. Reviewer-round fix (FR-QPB-076): the shared `api_key_group` widget's consent/disclosure
#     sub-widgets must be mode-aware -- `consent_disclosure_label`'s online-only "this key will be
#     embedded in the .qgs file" text must never be shown to an offline-mode user (it is simply
#     false for that case: FR-QPB-078/NFR-QPB-058), and the offline-mode "remember this key"
#     checkbox must actually have an effect rather than silently no-op'ing. A test that only
#     checked widget *visibility* (e.g. "some label is shown") without checking *which* label/its
#     *text content* would NOT catch the original defect, since a visible-but-wrong-text label
#     passes a visibility-only check -- see the assertions on `.text()` below.
# ---------------------------------------------------------------------------------------------


def test_connectivity_page_offline_mode_never_shows_the_online_only_embedding_disclosure():
    """The exact defect the reviewer found: `consent_disclosure_label`'s text is true only for
    online mode (the key really is embedded in the `.qgs` file there) and is factually false for
    offline mode (FR-QPB-078/NFR-QPB-058: the key is used only transiently and never retained in
    the delivered project). It must be hidden, not merely present-but-inactive, when offline mode
    is selected."""
    page = ConnectivityBasemapPage()
    page.show()
    page.offline_radio.setChecked(True)
    assert page.consent_disclosure_label.isVisible() is False
    assert page.consent_checkbox.isVisible() is False
    page.hide()


def test_connectivity_page_offline_mode_shows_accurate_transient_key_usage_text():
    """The offline-mode replacement (`offline_key_usage_label`) must be shown, and its text must
    accurately reflect FR-QPB-078/NFR-QPB-058 (transient use only, never retained in the delivered
    project) rather than either saying nothing or repeating the online-only embedding claim."""
    page = ConnectivityBasemapPage()
    page.show()
    page.offline_radio.setChecked(True)
    assert page.offline_key_usage_label.isVisible() is True
    text = page.offline_key_usage_label.text()
    # The specific false claim the reviewer found must never appear in the offline-mode text.
    assert "포함되며" not in text
    assert "추출할 수 있다" not in text
    # And the offline-mode text must make an accurate, positive claim of its own (not merely the
    # absence of the false one) -- mirroring FR-QPB-078's "must not remain in the generated
    # project" wording.
    assert "저장되지" in text or "포함되지" in text
    page.hide()


def test_connectivity_page_online_mode_shows_the_embedding_consent_widgets():
    """Companion regression check: the fix for offline mode must not regress the pre-existing,
    correct online-mode disclosure/consent flow."""
    page = ConnectivityBasemapPage()
    page.show()
    page.online_radio.setChecked(True)
    assert page.consent_disclosure_label.isVisible() is True
    assert page.consent_checkbox.isVisible() is True
    assert page.offline_key_usage_label.isVisible() is False
    page.hide()


def test_connectivity_page_remember_checkbox_is_reachable_in_offline_mode_too():
    """`remember_checkbox` (NFR-QPB-018) is generic to "the VWorld key," not scoped to the
    online-embedding case -- it must remain visible/reachable for offline mode, unlike the
    consent widgets above."""
    page = ConnectivityBasemapPage()
    page.show()
    page.offline_radio.setChecked(True)
    assert page.remember_checkbox.isVisible() is True
    page.hide()


def test_collect_config_wires_offline_remember_key(tmp_path, monkeypatch):
    """Compounding-issue fix: a checked `remember_checkbox` in offline mode must actually reach
    `config["basemap"]["remember_key"]`, exactly like the pre-existing online-mode wiring, instead
    of being silently dropped."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.offline_radio.setChecked(True)
    basemap_page.offline_bbox_source_draw_radio.setChecked(True)
    basemap_page.api_key_edit.setText("test-offline-key")
    basemap_page._on_bbox_drawn(dict(_SMALL_TEST_BBOX))
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["mode"] == "offline"
    assert config["basemap"]["remember_key"] is True


def test_collect_config_offline_remember_key_false_when_unchecked(tmp_path, monkeypatch):
    """Companion regression assertion: an unchecked `remember_checkbox` must still produce an
    explicit `False`, never a missing key that could be misread downstream."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.offline_radio.setChecked(True)
    basemap_page.offline_bbox_source_draw_radio.setChecked(True)
    basemap_page.api_key_edit.setText("test-offline-key")
    basemap_page._on_bbox_drawn(dict(_SMALL_TEST_BBOX))

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["remember_key"] is False


def test_review_page_persists_the_vworld_key_directly_once_unlocked_for_offline_mode(
    tmp_path, monkeypatch
):
    """Compounding-issue fix (reviewer round): "Remember this key" must not silently no-op in
    offline mode -- mirrors the existing online-mode persistence test
    (`test_review_page_persists_the_vworld_key_directly_once_unlocked`) but drives the offline
    path end to end through the real wizard/UI-process persistence mechanism
    (`ReviewAndBuildPage._maybe_unlock_for_remembering`/`_persist_remembered_keys`)."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.offline_radio.setChecked(True)
    basemap_page.offline_bbox_source_draw_radio.setChecked(True)
    basemap_page.api_key_edit.setText("OFFLINE-KEY-TO-REMEMBER")
    basemap_page._on_bbox_drawn(dict(_SMALL_TEST_BBOX))
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: "a-real-password"

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert credential_store_module.get_remembered_key() == "OFFLINE-KEY-TO-REMEMBER"
    assert review_page._remember_persist_failed is False


# ---------------------------------------------------------------------------------------------
# 7. End-to-end: build_project actually imports a *drawn* (not uploaded) site geometry into the
#    built GeoPackage (FR-QPB-025's drawing alternative).
# ---------------------------------------------------------------------------------------------


def test_end_to_end_drawn_site_geometry_is_imported_into_built_gpkg(
    tmp_path, monkeypatch, _stub_qgis_for_build
):
    monkeypatch.setattr(
        runtime_module, "check_runtime", lambda **_kw: {"available": True, "message": ""}
    )
    monkeypatch.setattr(wizard_module, "BuildWorkerThread", _RecordingBuildWorkerThread)

    wizard = ProjectBuilderWizard()
    wizard.setField("project_display_name", "Drawn Site Project")
    wizard.setField("output_dir", str(tmp_path))
    # Site input only applies to survey types 2/3/4 -- see `_select_survey_type`'s docstring. This
    # must happen before `_collect_config()` below reads `wizard.field("survey_type")`.
    _select_survey_type(wizard, "temporary_plots")

    site_input_page: SiteInputPage = wizard.page(2)
    site_input_page.input_mode_draw_radio.setChecked(True)
    canvas = site_input_page.draw_map_canvas
    canvas.add_polygon_vertex_at(40, 40)
    canvas.add_polygon_vertex_at(240, 40)
    canvas.add_polygon_vertex_at(240, 200)
    site_input_page._finish_drawn_shape()
    site_input_page.draw_site_name_edit.setText("Drawn E2E Site")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()
    assert config["survey_type"] == "temporary_plots"
    config["_test_reference_data_dir"] = str(_REFERENCE_DATA_VALID_SAMPLE_DIR)
    config["canonical_reference_path"] = str(_CANONICAL_REFERENCE_WORKBOOK_PATH)

    out_dir = tmp_path / "drawn_out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    gpkg_path = result["gpkg_path"]
    conn = sqlite3.connect(gpkg_path)
    try:
        rows = conn.execute("SELECT site_name, site_geom FROM site;").fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    site_name, site_geom = rows[0]
    assert site_name == "Drawn E2E Site"
    assert site_geom is not None
    assert bytes(site_geom)[0:2] == b"GP"  # a real GeoPackage geometry blob was written

    from qfield_builder.gpkg_functions import strip_gpkg_geometry_header
    from qfield_builder.wkt import wkb_to_wkt

    wkt, geom_type = wkb_to_wkt(strip_gpkg_geometry_header(bytes(site_geom)))
    assert geom_type == "MULTIPOLYGON"
    # The round-tripped geometry must match what the canvas actually drew (same coordinates as
    # `config["sites"][0]["geom_wkt"]`).
    assert wkt == site_input_page.drawn_site_wkt()


# ---------------------------------------------------------------------------------------------
# 8. SurveyTypePage: the real Next/Continue button must re-enable/re-evaluate live when the
#    checked radio button changes, *after* the page has already been shown once (FR-QPB-023/024).
#
# This is deliberately NOT just a check of `wizard.field("survey_type")`'s raw value after
# `radio.setChecked(True)` -- reading the field's value was never broken (the getter has always
# been correct). What was broken is that `QWizard`'s own mandatory-field completeness tracking
# never got told to re-run `isComplete()` and refresh the actual Next/Continue button after a
# live radio-button click post-page-show. So these tests exercise the real `QWizard` Next button
# (`wizard.button(QWizard.WizardButton.NextButton)`) and the page's own `completeChanged` signal,
# via a simulated real click (`QRadioButton.click()`), not a direct field/property write.
# ---------------------------------------------------------------------------------------------


def _advance_to_survey_type_page(
    tmp_path, monkeypatch
) -> tuple[ProjectBuilderWizard, SurveyTypePage]:
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    wizard.show()
    basics_page = wizard.currentPage()
    assert isinstance(basics_page, ProjectBasicsPage)
    wizard.next()
    survey_page = wizard.currentPage()
    assert isinstance(survey_page, SurveyTypePage)
    return wizard, survey_page


def test_survey_type_page_next_button_is_enabled_once_shown(tmp_path, monkeypatch):
    """A survey type is always pre-selected (the first radio defaults to checked), so the real
    Next button must already be enabled the moment the page is shown -- not frozen disabled at
    page-show time, which is what the pre-fix default `isComplete()` behavior actually produced
    (verified empirically against an isolated copy of the pre-fix module: `isComplete()` started
    `False` and the Next button's `isEnabled()` started `False` too, even though a valid survey
    type was already selected)."""
    wizard, _survey_page = _advance_to_survey_type_page(tmp_path, monkeypatch)
    next_button = wizard.button(QWizard.WizardButton.NextButton)
    assert next_button.isEnabled() is True


def test_survey_type_page_next_button_updates_live_after_radio_click_post_show(
    tmp_path, monkeypatch
):
    """The core regression this round fixes: after the page has already been shown once, a real
    click on a *different* survey-type radio button must (a) actually change the registered
    field's value, (b) trigger the page's own `completeChanged` signal (what `QWizard` uses to
    decide to re-check the Next button), and (c) leave the real Next button enabled afterward --
    not frozen at whatever state it happened to have when the page first loaded."""
    wizard, survey_page = _advance_to_survey_type_page(tmp_path, monkeypatch)
    next_button = wizard.button(QWizard.WizardButton.NextButton)
    assert next_button.isEnabled() is True  # sanity: matches the previous test

    complete_changed_calls = []
    survey_page.completeChanged.connect(lambda: complete_changed_calls.append(True))

    # A real simulated user click -- not `setField`/direct property assignment -- on a
    # *different* radio than the one already checked.
    assert wizard.field("survey_type") == "simple_inventory"
    survey_page.radio_buttons[2].click()  # "permanent_plots"

    assert wizard.field("survey_type") == "permanent_plots"
    assert len(complete_changed_calls) >= 1, (
        "clicking a different survey-type radio button did not emit completeChanged -- this is "
        "exactly the frozen-Continue-button regression this round fixes"
    )
    assert next_button.isEnabled() is True


def test_survey_type_page_next_button_stays_enabled_across_repeated_radio_clicks(
    tmp_path, monkeypatch
):
    """Guards against a fix that only happens to work for one specific transition (e.g. only the
    first click after page-show): clicking through every survey type in turn must leave the real
    Next button enabled the whole time, and each click must be reflected in the field value."""
    wizard, survey_page = _advance_to_survey_type_page(tmp_path, monkeypatch)
    next_button = wizard.button(QWizard.WizardButton.NextButton)

    expected_values = [value for value, _label in wizard_module.SURVEY_TYPES]
    for index, expected_value in enumerate(expected_values):
        survey_page.radio_buttons[index].click()
        assert wizard.field("survey_type") == expected_value
        assert next_button.isEnabled() is True


def test_survey_type_page_is_complete_reflects_current_radio_selection(tmp_path, monkeypatch):
    """`SurveyTypePage.isComplete()` itself (not just the button) must always report the actual
    current selection state, exactly one radio being checked at a time."""
    _wizard, survey_page = _advance_to_survey_type_page(tmp_path, monkeypatch)
    assert survey_page.isComplete() is True

    survey_page.radio_buttons[3].click()
    assert survey_page.isComplete() is True
    assert survey_page._get_survey_type() == "vegetation_mapping"


# ---------------------------------------------------------------------------------------------
# 9. ProjectBuilderWizard: bounded overall window size.
#
# Regression coverage for a real, stakeholder-reported defect in the packaged `.app`: after
# clicking through to a page with sparse content ("Step 5 - Photo identification"), the window
# stayed enormous (~3222px wide in the reported screenshot, almost entirely empty) because
# `QWizard` grows to accommodate whichever page has had the largest natural content size at any
# point in the wizard's lifetime, and never shrinks back down on its own for a later, sparser
# page. The fix has two independent parts, both covered below:
#   (a) `ProjectBuilderWizard.__init__` now sets an explicit, finite `setMaximumSize` (structural
#       bound -- `test_wizard_has_an_explicit_bounded_maximum_size`), rather than relying on
#       `QWidget`'s own effectively-unbounded default maximum size.
#   (b) Several long, single-line explanatory `QLabel`s across the wizard's pages (including the
#       exact "Step 5" label that was empirically the widest single page-state, at 1365 logical
#       px, before this fix) now word-wrap, so they no longer force excess width on their own
#       page.
# The tests below deliberately exercise the real, currently-widest page state
# (`ConnectivityBasemapPage`'s online-VWorld-layer mode, which includes a long VWorld-API-key
# consent checkbox with no word-wrap mechanism available) via `wizard.adjustSize()` and the
# wizard's *actual displayed size*, to confirm the bound holds in practice -- not merely that a
# `maximumSize` property happens to be set (that alone is `test_wizard_has_an_explicit_bounded_
# maximum_size`, just below).
# ---------------------------------------------------------------------------------------------

# Deliberately a small fraction of the reported ~3222px defect width, but generous enough to
# comfortably fit every page's genuinely-needed content (map canvas, forms, review text) -- see
# `qfield_builder.ui.wizard._WIZARD_MAX_SIZE`'s own comment for exactly how these were chosen.
_REASONABLE_MAX_WIDTH = 1200
_REASONABLE_MAX_HEIGHT = 900


def test_wizard_has_an_explicit_bounded_maximum_size():
    """The structural half of the fix: `QWidget`'s own default maximum size is effectively
    unbounded (`QWIDGETSIZE_MAX` == 16777215), so without an explicit, finite bound set here,
    nothing would prevent a future content change on any single page from reproducing the
    reported ~3222px-wide defect on every other page."""
    wizard = ProjectBuilderWizard()
    assert wizard.maximumWidth() <= _REASONABLE_MAX_WIDTH
    assert wizard.maximumHeight() <= _REASONABLE_MAX_HEIGHT
    # Sanity check that this is a real, deliberately-chosen bound, not an accident of some other
    # default: Qt's own unbounded sentinel must not appear here.
    assert wizard.maximumWidth() < 16_777_215
    assert wizard.maximumHeight() < 16_777_215


def test_wizard_show_process_events_and_close_avoid_qt_default_pixmap_lookup():
    """The real wizard lifecycle must not enter macOS Qt's invalid default-pixmap path.

    On affected Qt/macOS combinations, an unset QWizard pixmap causes ``show()``'s internal
    restart sequence to call ``NSBundle.bundleWithURL`` with a null URL and abort the process.
    This test deliberately exercises the same lifecycle rather than only inspecting the selected
    wizard style.  The explicit local pixmap contract also keeps every QWizard role non-null.
    """
    wizard = ProjectBuilderWizard()
    for role in (
        QWizard.WizardPixmap.WatermarkPixmap,
        QWizard.WizardPixmap.LogoPixmap,
        QWizard.WizardPixmap.BannerPixmap,
        QWizard.WizardPixmap.BackgroundPixmap,
    ):
        assert not wizard.pixmap(role).isNull()

    wizard.show()
    QApplication.processEvents()
    assert wizard.isVisible()
    wizard.close()
    QApplication.processEvents()
    assert not wizard.isVisible()


def _advance_to_connectivity_basemap_page_in_its_widest_state(
    tmp_path, monkeypatch
) -> ProjectBuilderWizard:
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    wizard.show()
    wizard.next()  # ProjectBasicsPage -> SurveyTypePage
    wizard.next()  # SurveyTypePage -> SiteInputPage
    wizard.next()  # SiteInputPage -> ConnectivityBasemapPage
    basemap_page = wizard.currentPage()
    assert isinstance(basemap_page, ConnectivityBasemapPage)
    # The online-VWorld-layer state is empirically the widest single page state in this wizard
    # (its long API-key-consent checkbox text has no word-wrap mechanism available, unlike the
    # plain QLabels fixed above) -- deliberately exercised here, not just a MapCanvas-bearing
    # state, so this test would catch a regression in *either* contributor.
    basemap_page.online_radio.setChecked(True)
    QApplication.processEvents()
    wizard.adjustSize()
    QApplication.processEvents()
    return wizard


def test_wizard_size_stays_bounded_on_the_widest_content_page(tmp_path, monkeypatch):
    wizard = _advance_to_connectivity_basemap_page_in_its_widest_state(tmp_path, monkeypatch)
    assert wizard.size().width() <= _REASONABLE_MAX_WIDTH
    assert wizard.size().height() <= _REASONABLE_MAX_HEIGHT


def test_wizard_does_not_stay_ballooned_on_a_later_sparse_page(tmp_path, monkeypatch):
    """The core regression: after the wizard has already shown its widest page, navigating onward
    to the sparsest page ("Step 5") must leave the window within the same reasonable bound -- not
    stuck at whatever size the widest page's content previously demanded."""
    wizard = _advance_to_connectivity_basemap_page_in_its_widest_state(tmp_path, monkeypatch)

    wizard.next()  # ConnectivityBasemapPage -> IdentificationTogglePage ("Step 5")
    sparse_page = wizard.currentPage()
    assert isinstance(sparse_page, IdentificationTogglePage)
    QApplication.processEvents()
    wizard.adjustSize()
    QApplication.processEvents()

    assert wizard.size().width() <= _REASONABLE_MAX_WIDTH
    assert wizard.size().height() <= _REASONABLE_MAX_HEIGHT


# ---------------------------------------------------------------------------------------------
# 10. FR-QPB-024a (Decision Log D-27): Korean survey-type explanations at Step 2.
# ---------------------------------------------------------------------------------------------


def test_survey_type_descriptions_exist_for_all_four_survey_types():
    values = {value for value, _label in wizard_module.SURVEY_TYPES}
    assert values == set(wizard_module.SURVEY_TYPE_DESCRIPTIONS_KO.keys())


def test_survey_type_descriptions_are_non_trivial_and_distinct():
    descriptions = wizard_module.SURVEY_TYPE_DESCRIPTIONS_KO
    # Each description must be substantive (not a one-word placeholder)...
    for value, description in descriptions.items():
        assert len(description) >= 40, f"{value}'s description looks like placeholder filler"
    # ...and every pair of descriptions must be genuinely distinct from one another (no
    # copy-pasted generic filler that could describe more than one type equally well).
    values = list(descriptions.keys())
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            assert descriptions[values[i]] != descriptions[values[j]]


def test_survey_type_descriptions_are_grounded_in_each_type_s_own_schema_vocabulary():
    """FR-QPB-024a requires each description to be "grounded in that type's actual schema"
    (Section 8), not interchangeable filler -- spot-check a schema-specific keyword unique to
    each type's own structure (Section 8.1-8.4)."""
    descriptions = wizard_module.SURVEY_TYPE_DESCRIPTIONS_KO
    # Type 1: a relation-free point-observation layer -- no site/plot hierarchy at all.
    assert "사이트" in descriptions["simple_inventory"]
    assert "관찰" in descriptions["simple_inventory"]
    # Type 2: site -> survey -> observation (temporary plot; no fixed `plot` entity).
    assert "임시" in descriptions["temporary_plots"]
    assert "피도" in descriptions["temporary_plots"] or "cover" in descriptions["temporary_plots"]
    # Type 3: site -> plot -> survey -> observation (fixed, repeatedly revisited plot).
    assert "고정" in descriptions["permanent_plots"]
    assert "반복" in descriptions["permanent_plots"]
    # Type 4: site -> survey -> community polygon mapping.
    assert "군락" in descriptions["vegetation_mapping"] or "폴리곤" in descriptions[
        "vegetation_mapping"
    ]


def test_survey_type_page_displays_each_description_next_to_its_radio_button():
    page = SurveyTypePage()
    layout = page.layout()
    widget_texts = [
        layout.itemAt(i).widget().text()
        for i in range(layout.count())
        if layout.itemAt(i).widget() is not None
    ]
    for value, description in wizard_module.SURVEY_TYPE_DESCRIPTIONS_KO.items():
        assert any(description in text for text in widget_texts), (
            f"expected {value}'s Korean description to be displayed on SurveyTypePage"
        )


# ---------------------------------------------------------------------------------------------
# 11. FR-QPB-071 (revised; Decision Log D-26): VWorld layer discovery wiring in the wizard UI.
# ---------------------------------------------------------------------------------------------


def test_connectivity_page_refresh_layers_requires_an_api_key_first():
    page = ConnectivityBasemapPage()
    page._refresh_vworld_layers()
    assert "API 키" in page.layer_status_label.text()


def test_connectivity_page_refresh_layers_populates_combo_from_injected_fetcher():
    calls = []

    def _fake_fetch(api_key: str) -> list[str]:
        calls.append(api_key)
        return ["Base", "White", "Midnight", "Hybrid", "Satellite", "NewLayer"]

    page = ConnectivityBasemapPage(fetch_layers_fn=_fake_fetch)
    page.api_key_edit.setText("MY-TEST-KEY")
    page._refresh_vworld_layers()

    assert calls == ["MY-TEST-KEY"]
    combo_items = [page.layer_combo.itemText(i) for i in range(page.layer_combo.count())]
    assert combo_items == ["Base", "White", "Midnight", "Hybrid", "Satellite", "NewLayer"]
    assert page.known_vworld_layers() == combo_items
    assert "6" in page.layer_status_label.text()  # "(6개)" -- six layers were discovered


def test_connectivity_page_refresh_layers_surfaces_a_clear_error_without_crashing():
    def _failing_fetch(api_key: str) -> list[str]:  # noqa: ARG001
        raise RuntimeError("이 VWorld 레이어 목록을 가져올 수 없었습니다 (테스트).")

    page = ConnectivityBasemapPage(fetch_layers_fn=_failing_fetch)
    page.api_key_edit.setText("MY-TEST-KEY")
    page._refresh_vworld_layers()  # must not raise

    assert "가져올 수 없었습니다" in page.layer_status_label.text()
    assert page.known_vworld_layers() is None


def test_collect_config_passes_through_known_vworld_layers_when_discovered(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page._fetch_layers_fn = lambda api_key: ["Base", "White", "ExtraLayer"]  # noqa: ARG005
    basemap_page.api_key_edit.setText("SOME-KEY")
    basemap_page._refresh_vworld_layers()

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["known_vworld_layers"] == ["Base", "White", "ExtraLayer"]


def test_collect_config_omits_known_vworld_layers_when_never_discovered(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    # No refresh ever performed -- only the static fallback list is available.

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert "known_vworld_layers" not in config["basemap"]


# ---------------------------------------------------------------------------------------------
# 12. NFR-QPB-070 (Decision Log D-28): spot-checks that key wizard UI strings are now in Korean.
#
# This deliberately does not assert every single string in the wizard (an exhaustive check would
# be brittle and duplicate the implementation) -- just a representative sample of page titles,
# a button label, and a validation/status message per page, so a regression that accidentally
# reintroduces English text on one of these pages would be caught.
# ---------------------------------------------------------------------------------------------


def _contains_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def test_wizard_page_titles_are_in_korean():
    wizard = ProjectBuilderWizard()
    for page_id in wizard.pageIds():
        title = wizard.page(page_id).title()
        assert _contains_hangul(title), f"expected a Korean page title, got: {title!r}"


def test_project_basics_page_labels_are_in_korean():
    page = ProjectBasicsPage()
    assert _contains_hangul(page.slug_preview_label.text())


def test_survey_type_page_radio_labels_are_in_korean():
    page = SurveyTypePage()
    for radio in page.radio_buttons:
        assert _contains_hangul(radio.text())


def test_site_input_page_buttons_and_status_are_in_korean():
    page = SiteInputPage()
    assert _contains_hangul(page.input_mode_upload_radio.text())
    assert _contains_hangul(page.input_mode_draw_radio.text())
    assert _contains_hangul(page.draw_status_label.text())


def test_connectivity_basemap_page_labels_are_in_korean():
    page = ConnectivityBasemapPage()
    assert _contains_hangul(page.online_radio.text())
    assert _contains_hangul(page.offline_radio.text())
    assert _contains_hangul(page.none_radio.text())
    assert _contains_hangul(page.consent_checkbox.text())
    assert _contains_hangul(page.offline_estimate_label.text())


def test_identification_toggle_page_checkbox_is_in_korean():
    page = IdentificationTogglePage()
    assert _contains_hangul(page.enable_checkbox.text())


def test_review_and_build_page_button_is_in_korean():
    page = ReviewAndBuildPage()
    assert _contains_hangul(page.build_button.text())


def test_review_page_exposes_and_propagates_user_build_cancellation(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    review_page._start_build()
    worker = _RecordingBuildWorkerThread.instances[0]
    assert review_page.cancel_build_button.isVisibleTo(review_page)
    assert review_page.cancel_build_button.isEnabled()

    review_page.cancel_build_button.click()

    assert worker.cancel_called is True
    assert review_page.cancel_build_button.isEnabled() is False
    assert "취소" in review_page.result_label.text()

    review_page._on_build_finished(
        {
            "success": False,
            "cancelled": True,
            "error_code": "cancelled",
            "error_message": "빌드가 취소되었습니다.",
        }
    )
    assert review_page.cancel_build_button.isVisibleTo(review_page) is False
    assert review_page.build_button.isEnabled() is True
    assert "부분 파일은 삭제되었습니다" in review_page.result_label.text()


def test_identification_intro_uses_current_survey_plot_geometry_for_probability():
    page = IdentificationTogglePage()
    intro_text = next(
        label.text()
        for label in page.findChildren(QLabel)
        if "Pl@ntNet" in label.text() and "현재 조사/조사구" in label.text()
    )

    assert "현재 조사/조사구 geometry" in intro_text
    assert "위치를 사용할 수 없으면 사진 식별은 계속" in intro_text
    assert "위치 기반 출현 확률 조회는 건너뜁니다" in intro_text
    assert "GPS" not in intro_text


# ---------------------------------------------------------------------------------------------
# 13. IdentificationTogglePage (Section 6.5/FR-QPB-037-039/E-QPB-001): the guaranteed-manual
#     identification baseline (Section 13) is now real, implemented, reviewer-PASSed code, so this
#     page must no longer present it as an unavailable future feature -- but it must also not
#     silently invent a build-time Pl@ntNet-key field that goes nowhere (see the class docstring
#     in `qfield_builder/ui/wizard.py` for the traced reason no such field exists).
# ---------------------------------------------------------------------------------------------


def test_identification_toggle_checkbox_is_enabled_and_can_be_checked():
    page = IdentificationTogglePage()
    assert page.enable_checkbox.isEnabled() is True
    assert page.enable_checkbox.isChecked() is False  # off by default (FR-QPB-038)

    page.enable_checkbox.setChecked(True)
    assert page.enable_checkbox.isChecked() is True


def test_identification_toggle_page_no_longer_claims_a_future_unavailable_feature():
    """The E-QPB-001 condition that required "coming in a future release" framing no longer
    holds -- the subsystem genuinely exists now (qml_plugin.py/reference_bundle.py/ktsn_match.py),
    so this page must not claim it is a future/unavailable feature."""
    page = IdentificationTogglePage()
    full_text = page.enable_checkbox.text() + " " + page.layout().itemAt(0).widget().text()
    assert "향후 릴리스" not in full_text
    assert "사용할 수 없습니다" not in full_text


def test_identification_toggle_page_intro_describes_the_real_feature_honestly():
    """Must accurately name the real, shipped mechanism (Pl@ntNet + KTSN + occurrence
    probability, delivered via a QField plugin/embedded widget), describe it as a guaranteed
    *manual* action (not automatic), and not overclaim the on-device raster-sampling/attribute
    write-back mechanisms as fully certain (Decision Log D-36's feasibility caveat)."""
    page = IdentificationTogglePage()
    intro_text = page.layout().itemAt(0).widget().text()
    assert "Pl@ntNet" in intro_text
    assert "KTSN" in intro_text
    assert "국가생물종목록" in intro_text or "정명" in intro_text
    assert "직접 눌러야" in intro_text or "수동" in intro_text  # guaranteed-manual, not automatic


def test_identification_toggle_page_has_masked_plantnet_api_key_field():
    """FR-QPB-117 (Decision Log D-45, superseding this page's prior no-key-field design): the
    page must collect the Pl@ntNet API key as a masked secret input, mirroring
    `ConnectivityBasemapPage.api_key_edit`'s `EchoMode.Password` treatment of the VWorld key."""
    page = IdentificationTogglePage()
    assert page.plantnet_api_key_edit in page.findChildren(QLineEdit)
    assert page.plantnet_api_key_edit.echoMode() == QLineEdit.EchoMode.Password


def test_identification_toggle_page_has_mandatory_plantnet_consent_checkbox():
    """FR-QPB-115 (Decision Log D-45): an explicit confirmation checkbox -- not merely an
    informational label -- gates Pl@ntNet key embedding, mirroring
    `ConnectivityBasemapPage.consent_checkbox`. Bug 1 fix: the full Pl@ntNet-specific disclosure
    text now lives in a separately word-wrapped `QLabel`
    (`plantnet_consent_disclosure_label`) -- the checkbox itself carries only a short
    confirmation label -- so the disclosure content is checked on the label, not the checkbox."""
    page = IdentificationTogglePage()
    assert isinstance(page.plantnet_consent_checkbox, QCheckBox)
    assert "Pl@ntNet" in page.plantnet_consent_disclosure_label.text()
    assert page.plantnet_consent_disclosure_label.wordWrap() is True
    assert not page.plantnet_consent_checkbox.isChecked()  # never pre-checked


def test_identification_toggle_page_discloses_the_real_plantnet_key_mechanism():
    """NFR-QPB-013/FR-QPB-116: if consent is declined, the Pl@ntNet key still ends up present on
    the phone via manual QField entry, so this must remain disclosed, including that folder/
    device recipients could extract it, and that a client-side key is never truly secret."""
    page = IdentificationTogglePage()
    layout = page.layout()
    all_label_text = " ".join(
        layout.itemAt(i).widget().text()
        for i in range(layout.count())
        if hasattr(layout.itemAt(i).widget(), "text")
    )
    assert "QField" in all_label_text
    assert "추출" in all_label_text  # "extract" -- recipients could extract the key
    assert "비밀" in all_label_text  # a client-side key must never be claimed secret


def test_collect_config_identification_enabled_true_when_checked(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    identification_page: IdentificationTogglePage = wizard.page(4)
    identification_page.enable_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["identification_enabled"] is True


def test_collect_config_identification_enabled_false_when_unchecked(tmp_path, monkeypatch):
    """Matches prior, still-correct MVP behavior for the disabled case: `identification_enabled`
    is `False` and no other identification-related config key is produced."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["identification_enabled"] is False
    identification_related_keys = {
        key for key in config if "plantnet" in key.lower() or "identification" in key.lower()
    }
    assert identification_related_keys == {"identification_enabled"}


# ---------------------------------------------------------------------------------------------
# 14. End-to-end: build_project actually generates the identification-subsystem artifacts
#     (<slug>.qml project plugin + reference/ folder) from a wizard-collected config shape, when
#     the checkbox is checked -- not just that `_collect_config()`'s dict looks right.
# ---------------------------------------------------------------------------------------------

_POST_MVP_REFERENCE_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "acceptance"
    / "qfield_project_builder"
    / "fixtures"
    / "reference_data_valid_sample"
)


def test_end_to_end_identification_enabled_generates_plugin_qml_and_reference_folder(
    tmp_path, monkeypatch, _stub_qgis_for_build
):
    assert _POST_MVP_REFERENCE_FIXTURE_DIR.is_dir(), (
        f"expected fixture directory to exist: {_POST_MVP_REFERENCE_FIXTURE_DIR}"
    )

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch, project_name="Identification Project")
    identification_page: IdentificationTogglePage = wizard.page(4)
    identification_page.enable_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()
    assert config["identification_enabled"] is True
    # FR-QPB-114-117 (Decision Log D-45): once identification is enabled, the collected config
    # must carry a `plantnet` dict -- but since neither the key field nor the consent checkbox
    # was touched here, consent must default to False, so nothing gets embedded downstream
    # (FR-QPB-116).
    assert config["plantnet"]["consent_accepted"] is False

    # The small fixture supplies the raster sidecar; D-95 source identity remains canonical.
    config["_test_reference_data_dir"] = str(_POST_MVP_REFERENCE_FIXTURE_DIR)
    config["canonical_reference_path"] = str(_CANONICAL_REFERENCE_WORKBOOK_PATH)

    out_dir = tmp_path / "identification_out"
    result = build_module.build_project(config, str(out_dir))

    assert result["success"] is True, result
    project_dir = Path(result["project_dir"])

    plugin_qml_path = project_dir / f"{result['project_slug']}.qml"
    assert plugin_qml_path.is_file(), "expected the <project_slug>.qml project plugin sidecar"
    plugin_qml_text = plugin_qml_path.read_text(encoding="utf-8")
    assert "qpbIdentificationPlugin" in plugin_qml_text  # genuine plugin source, not an empty stub

    # FR-QPB-112 (revised)/FR-QPB-118 (Decision Log D-47): the bundled KTSN reference asset is the
    # build-time-extracted 5-column lookup file, never the complete raw CSV -- which must not
    # appear anywhere in the generated project, not even at its former bundled location.
    reference_ktsn_lookup_csv = project_dir / "reference" / "ktsn_lookup.csv"
    assert reference_ktsn_lookup_csv.is_file(), (
        "expected the build-time-extracted KTSN lookup CSV (FR-QPB-112 revised/FR-QPB-118)"
    )
    assert not (project_dir / "reference" / "tables").exists(), (
        "the former reference/tables/ complete-raw-CSV bundling location must no longer be "
        "created at all"
    )

    reference_raster_dir = (
        project_dir / "reference" / "rasters" / "bce_inverse_corrected_probability_maps"
    )
    assert reference_raster_dir.is_dir()
    assert list(reference_raster_dir.glob("*.tif")), "expected bundled probability rasters"

    manifest_path = project_dir / "MANIFEST.json"
    assert manifest_path.is_file()
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_files = manifest.get("required_files", {})
    assert required_files.get("identification_plugin") == f"{result['project_slug']}.qml"
    assert any(
        relpath.endswith("ktsn_lookup.csv") for relpath in required_files.get("reference", [])
    )


# ---------------------------------------------------------------------------------------------
# 12. NFR-QPB-018 (revised)/NFR-QPB-073 (Decision Log D-53/D-55): a VWorld key previously
#     remembered via "Remember this key" (now stored in the encrypted local `credentials.enc`
#     file by `qfield_builder.credential_store.remember_key`) must actually be reloaded into a
#     fresh wizard -- "across sessions" requires the field to be pre-filled, not merely writable.
#     Per AC-QPB-097/the traceability finding on `QWizardPage.initializePage()` vs `__init__`
#     timing, this reload now happens in `initializePage()`, not at construction time -- these
#     tests call `initializePage()` explicitly (mirroring real wizard navigation) rather than
#     asserting on bare `__init__` state. `credential_store.get_remembered_key` is monkeypatched
#     directly in the simplest cases (never the real encrypted file/OS keychain) to keep this
#     hermetic; the locked-session/prompt-timing cases below exercise the real
#     `credential_store` encryption against `tests/unit/conftest.py`'s isolated app-data
#     directory instead, since they need genuine "is there a password to ask for" state.
# ---------------------------------------------------------------------------------------------


def test_connectivity_page_prefills_api_key_from_credential_store(monkeypatch):
    monkeypatch.setattr(
        wizard_module.credential_store, "get_remembered_key", lambda: "REMEMBERED-KEY-123"
    )

    page = ConnectivityBasemapPage()
    page.initializePage()

    assert page.api_key_edit.text() == "REMEMBERED-KEY-123"
    assert page.remember_checkbox.isChecked()
    # NFR-QPB-010: still masked in the UI, whether pre-filled or typed by the user.
    assert page.api_key_edit.echoMode() == QLineEdit.EchoMode.Password


def test_connectivity_page_does_not_prefill_before_initialize_page_is_called(monkeypatch):
    """The core AC-QPB-097 timing guarantee at the single-page level: merely constructing the
    page (as happens when the wizard itself is constructed, before it is ever shown) must not
    have already reloaded a remembered key -- only `initializePage()` (real page navigation)
    does."""
    monkeypatch.setattr(
        wizard_module.credential_store, "get_remembered_key", lambda: "REMEMBERED-KEY-123"
    )

    page = ConnectivityBasemapPage()

    assert page.api_key_edit.text() == ""
    assert not page.remember_checkbox.isChecked()


def test_connectivity_page_leaves_api_key_empty_when_nothing_remembered(monkeypatch):
    monkeypatch.setattr(wizard_module.credential_store, "get_remembered_key", lambda: None)

    page = ConnectivityBasemapPage()
    page.initializePage()

    assert page.api_key_edit.text() == ""
    assert not page.remember_checkbox.isChecked()


def test_connectivity_page_survives_a_credential_store_failure(monkeypatch):
    def _raise():
        raise RuntimeError("credential store unavailable (test)")

    monkeypatch.setattr(wizard_module.credential_store, "get_remembered_key", _raise)

    page = ConnectivityBasemapPage()
    page.initializePage()  # must not raise

    assert page.api_key_edit.text() == ""
    assert not page.remember_checkbox.isChecked()


def test_connectivity_page_remember_checkbox_disabled_when_no_password_established():
    """NFR-QPB-073 decline-path fallback: "Remember this key" must be unavailable/disabled for
    the session when no encrypted-storage password has ever been established."""
    page = ConnectivityBasemapPage()
    page.initializePage()

    assert not credential_store_module.is_password_established()
    assert not page.remember_checkbox.isEnabled()


def test_connectivity_page_remember_checkbox_enabled_once_password_established():
    credential_store_module.establish_password("a-real-password")  # noqa: S106

    page = ConnectivityBasemapPage()
    page.initializePage()

    assert page.remember_checkbox.isEnabled()


def test_connectivity_page_prompts_for_password_only_when_a_key_is_actually_remembered():
    """AC-QPB-097: no encrypted-storage password prompt is shown when nothing has been
    remembered -- there is nothing to auto-fill."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()  # Simulates a genuinely fresh application launch.
    prompt_calls = []

    def _spy_prompt(_parent=None):
        prompt_calls.append(True)
        return None

    page = ConnectivityBasemapPage(password_prompt_fn=_spy_prompt)
    page.initializePage()

    assert prompt_calls == []
    assert page.api_key_edit.text() == ""


def test_connectivity_page_prompts_for_password_when_a_remembered_key_would_be_auto_filled():
    """AC-QPB-097: the specific point of use -- a remembered key exists, and this session has not
    yet supplied the password -- does show exactly one prompt, and a correct password unlocks and
    prefills it."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_key("REMEMBERED-VIA-ENCRYPTION")
    credential_store_module.lock_session()
    prompt_calls = []

    def _spy_prompt(_parent=None):
        prompt_calls.append(True)
        return "a-real-password"

    page = ConnectivityBasemapPage(password_prompt_fn=_spy_prompt)
    page.initializePage()

    assert len(prompt_calls) == 1
    assert page.api_key_edit.text() == "REMEMBERED-VIA-ENCRYPTION"
    assert page.remember_checkbox.isChecked()


def test_connectivity_page_declining_the_unlock_prompt_leaves_the_field_empty(monkeypatch):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_key("REMEMBERED-VIA-ENCRYPTION")
    credential_store_module.lock_session()

    page = ConnectivityBasemapPage(password_prompt_fn=lambda _parent=None: None)
    page.initializePage()  # User cancelled the prompt.

    assert page.api_key_edit.text() == ""
    assert not credential_store_module.is_unlocked()


def test_connectivity_page_wrong_password_at_unlock_prompt_leaves_field_empty_with_a_message():
    """AC-QPB-093: a forgotten/incorrect password never silently guesses/bypasses -- the field
    stays empty (equivalent to requiring manual re-entry) and the user is told why."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_key("REMEMBERED-VIA-ENCRYPTION")
    credential_store_module.lock_session()

    page = ConnectivityBasemapPage(password_prompt_fn=lambda _parent=None: "totally-wrong")
    page.initializePage()

    assert page.api_key_edit.text() == ""
    assert not credential_store_module.is_unlocked()
    assert page.credential_status_label.text() != ""


def test_wizard_shows_no_password_prompt_before_the_connectivity_basemap_page_is_reached(
    tmp_path, monkeypatch
):
    """AC-QPB-097, at the full-wizard level: earlier steps (Step 1-3) must never trigger the
    encrypted-storage password prompt, even though a remembered VWorld key exists -- only the
    specific step that would auto-fill it (Step 4, `ConnectivityBasemapPage`) may."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_key("REMEMBERED-VIA-ENCRYPTION")
    credential_store_module.lock_session()

    prompt_calls = []

    def _spy_prompt(_parent=None):
        prompt_calls.append(True)
        return "a-real-password"

    monkeypatch.setattr(wizard_module, "prompt_for_unlock_password", _spy_prompt)
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    wizard.show()

    wizard.next()  # ProjectBasicsPage -> SurveyTypePage
    wizard.next()  # SurveyTypePage -> SiteInputPage
    assert prompt_calls == [], "no step before ConnectivityBasemapPage may prompt"

    wizard.next()  # SiteInputPage -> ConnectivityBasemapPage: the specific point of use.
    basemap_page = wizard.currentPage()
    assert isinstance(basemap_page, ConnectivityBasemapPage)
    assert len(prompt_calls) == 1
    assert basemap_page.api_key_edit.text() == "REMEMBERED-VIA-ENCRYPTION"


# ---------------------------------------------------------------------------------------------
# 12b. NFR-QPB-072 (revised)/NFR-QPB-073 mirror: identical point-of-use retrieval-timing rules
#      for the Pl@ntNet key on `IdentificationTogglePage`.
# ---------------------------------------------------------------------------------------------


def test_identification_page_prefills_plantnet_api_key_from_credential_store(monkeypatch):
    monkeypatch.setattr(
        wizard_module.credential_store,
        "get_remembered_plantnet_key",
        lambda: "REMEMBERED-PLANTNET-KEY",
    )

    page = IdentificationTogglePage()
    page.initializePage()

    assert page.plantnet_api_key_edit.text() == "REMEMBERED-PLANTNET-KEY"
    assert page.plantnet_remember_checkbox.isChecked()
    assert page.plantnet_api_key_edit.echoMode() == QLineEdit.EchoMode.Password


def test_identification_page_does_not_prefill_before_initialize_page_is_called(monkeypatch):
    monkeypatch.setattr(
        wizard_module.credential_store,
        "get_remembered_plantnet_key",
        lambda: "REMEMBERED-PLANTNET-KEY",
    )

    page = IdentificationTogglePage()

    assert page.plantnet_api_key_edit.text() == ""
    assert not page.plantnet_remember_checkbox.isChecked()


def test_identification_page_survives_a_credential_store_failure(monkeypatch):
    def _raise():
        raise RuntimeError("credential store unavailable (test)")

    monkeypatch.setattr(wizard_module.credential_store, "get_remembered_plantnet_key", _raise)

    page = IdentificationTogglePage()
    page.initializePage()  # must not raise

    assert page.plantnet_api_key_edit.text() == ""


def test_identification_page_remember_checkbox_disabled_when_no_password_established():
    page = IdentificationTogglePage()
    page.initializePage()

    assert not credential_store_module.is_password_established()
    assert not page.plantnet_remember_checkbox.isEnabled()


def test_identification_page_prompts_for_password_when_a_remembered_key_would_be_auto_filled():
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_plantnet_key("REMEMBERED-PLANTNET-VIA-ENCRYPTION")
    credential_store_module.lock_session()
    prompt_calls = []

    def _spy_prompt(_parent=None):
        prompt_calls.append(True)
        return "a-real-password"

    page = IdentificationTogglePage(password_prompt_fn=_spy_prompt)
    page.initializePage()

    assert len(prompt_calls) == 1
    assert page.plantnet_api_key_edit.text() == "REMEMBERED-PLANTNET-VIA-ENCRYPTION"
    assert page.plantnet_remember_checkbox.isChecked()


def test_identification_page_wrong_password_at_unlock_prompt_leaves_field_empty_with_a_message():
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.remember_plantnet_key("REMEMBERED-PLANTNET-VIA-ENCRYPTION")
    credential_store_module.lock_session()

    page = IdentificationTogglePage(password_prompt_fn=lambda _parent=None: "totally-wrong")
    page.initializePage()

    assert page.plantnet_api_key_edit.text() == ""
    assert not credential_store_module.is_unlocked()
    assert page.plantnet_credential_status_label.text() != ""


# ---------------------------------------------------------------------------------------------
# 12c. NFR-QPB-073: the "remember new key" store-time unlock prompt
#      (`ReviewAndBuildPage._maybe_unlock_for_remembering`) -- the point at which a *newly*
#      checked "Remember this key" request is actually about to be encrypted and persisted, for
#      a password established in an earlier session that this one has not yet unlocked.
# ---------------------------------------------------------------------------------------------


def test_review_page_unlocks_before_build_when_remember_is_checked_and_password_established(
    tmp_path, monkeypatch
):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("FRESH-KEY")
    basemap_page.remember_checkbox.setEnabled(True)  # Reflects a password now being established.
    basemap_page.remember_checkbox.setChecked(True)
    basemap_page.consent_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: "a-real-password"

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert credential_store_module.is_unlocked()


def test_review_page_never_blocks_the_build_when_the_unlock_prompt_is_declined(
    tmp_path, monkeypatch
):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("FRESH-KEY")
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)
    basemap_page.consent_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: None  # User declines.

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)  # Must not raise.

    assert not credential_store_module.is_unlocked()
    # The actual build-triggering path must still proceed regardless (never blocked).
    review_page.build_button.click()
    assert review_page._worker_thread is not None


def test_review_page_does_not_prompt_when_remember_is_not_checked(tmp_path, monkeypatch):
    prompt_calls = []
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: prompt_calls.append(True)

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert prompt_calls == []


# ---------------------------------------------------------------------------------------------
# 12d. Reviewer round (Decision Log D-53/D-55), Finding 1 fix: `_maybe_unlock_for_remembering`
#      must now actually persist a requested "Remember this key" into the encrypted store itself,
#      from the UI process -- not merely unlock the session and leave persistence to
#      `build_project()` (which the real desktop application can never reach across the real
#      subprocess boundary; see `tests/unit/test_smoke_gui.py`'s companion real-subprocess test
#      for the full end-to-end regression proof).
# ---------------------------------------------------------------------------------------------


def test_review_page_persists_the_vworld_key_directly_once_unlocked(tmp_path, monkeypatch):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("FRESH-KEY-TO-REMEMBER")
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)
    basemap_page.consent_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: "a-real-password"

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    # The critical Finding 1 assertion: the key must actually be in the encrypted store now,
    # from this (the UI) process -- not merely "unlocked" with nothing ever written.
    assert credential_store_module.get_remembered_key() == "FRESH-KEY-TO-REMEMBER"
    assert review_page._remember_persist_failed is False


def test_review_page_persists_the_plantnet_key_directly_once_unlocked(tmp_path, monkeypatch):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    identification_page: IdentificationTogglePage = wizard.page(4)
    identification_page.enable_checkbox.setChecked(True)
    identification_page.plantnet_api_key_edit.setText("FRESH-PLANTNET-KEY-TO-REMEMBER")
    identification_page.plantnet_consent_checkbox.setChecked(True)
    identification_page.plantnet_remember_checkbox.setEnabled(True)
    identification_page.plantnet_remember_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: "a-real-password"

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert credential_store_module.get_remembered_plantnet_key() == "FRESH-PLANTNET-KEY-TO-REMEMBER"
    assert review_page._remember_persist_failed is False


def test_review_page_persists_immediately_when_the_session_was_already_unlocked(
    tmp_path, monkeypatch
):
    """Covers the "already unlocked, no prompt needed" branch: `_maybe_unlock_for_remembering`
    must still persist in this case (Finding 1) -- it must not, as before this fix, return early
    and leave persistence to the (real-subprocess-unreachable) build pipeline."""
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    # Deliberately NOT calling lock_session(): the session is already unlocked, exactly as it
    # would be if a remembered key had already been loaded earlier in the same wizard session.

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("ALREADY-UNLOCKED-KEY")
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)
    basemap_page.consent_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    prompt_calls = []
    review_page._password_prompt_fn = lambda _parent=None: prompt_calls.append(True)

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert prompt_calls == []  # Never re-prompted: the session was already unlocked.
    assert credential_store_module.get_remembered_key() == "ALREADY-UNLOCKED-KEY"


def test_review_page_never_persists_when_the_unlock_prompt_is_declined(tmp_path, monkeypatch):
    credential_store_module.establish_password("a-real-password")  # noqa: S106
    credential_store_module.lock_session()

    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText("SHOULD-NOT-BE-REMEMBERED")
    basemap_page.remember_checkbox.setEnabled(True)
    basemap_page.remember_checkbox.setChecked(True)
    basemap_page.consent_checkbox.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._password_prompt_fn = lambda _parent=None: None  # User declines.

    config = review_page._collect_config()
    review_page._maybe_unlock_for_remembering(config)

    assert credential_store_module.get_remembered_key() is None
    assert review_page._remember_persist_failed is False  # Declining is not a "failure" to flag.


# ---------------------------------------------------------------------------------------------
# 12e. Minor Finding 2 (reviewer round, D-53/D-55): a failed "Remember this key" persistence
#      attempt (the store confirmed unlocked, yet the underlying write itself still failed) must
#      surface a best-effort, non-blocking, user-facing signal once the build finishes -- rather
#      than failing completely silently, as the pre-fix `except Exception: pass` did.
# ---------------------------------------------------------------------------------------------


def test_on_build_finished_surfaces_a_note_when_remembering_the_key_failed(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    review_page._remember_persist_failed = True
    review_page._on_build_finished({"success": True, "project_dir": str(tmp_path / "out")})

    assert "프로젝트가 생성되었습니다:" in review_page.result_label.text()
    assert "기억하지 못했습니다" in review_page.result_label.text()


def test_on_build_finished_does_not_surface_a_note_when_remembering_succeeded(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    review_page._remember_persist_failed = False
    review_page._on_build_finished({"success": True, "project_dir": str(tmp_path / "out")})

    assert "기억하지 못했습니다" not in review_page.result_label.text()


def test_start_build_resets_the_remember_persist_failed_flag_for_a_fresh_attempt(
    tmp_path, monkeypatch
):
    """A stale failure flag from a *previous* build attempt must never bleed into the next one."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._remember_persist_failed = True

    review_page.build_button.click()

    assert review_page._remember_persist_failed is False


# ---------------------------------------------------------------------------------------------
# 16. FR-QPB-008 (Decision Log D-10): manual QGIS-install-path override control, reachable once
#     automatic runtime detection has failed -- previously a Category A conformance defect (a
#     control the runtime's own error message named by name, but that did not exist anywhere).
# ---------------------------------------------------------------------------------------------


# `QWizardPage.isVisible()` only ever reflects real, on-screen visibility for the wizard's
# *currently displayed* page -- QWizard's internal page-stack keeps every other registered page
# explicitly hidden regardless of a direct `.show()` call on that page object, so asserting on
# `select_qgis_path_button.isVisible()` directly here (Step 7, not the wizard's default first
# page) would depend on actually navigating the whole wizard there first. `isVisibleTo(review_page)`
# instead reports the button's own explicit shown/hidden state (and its containment within
# `review_page`'s own layout) independent of whether `review_page` itself is the wizard's current
# page -- exactly the fact these tests care about.


def test_select_qgis_path_button_hidden_before_any_build_attempt(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    assert review_page.select_qgis_path_button.isVisibleTo(review_page) is False


def test_select_qgis_path_button_becomes_visible_when_runtime_check_fails(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    monkeypatch.setattr(
        runtime_module,
        "check_runtime",
        lambda **_kw: {
            "available": False,
            "message": "이 컴퓨터에서 호환되는 QGIS Desktop 설치를 찾을 수 없습니다.",
            "qgis_prefix_path": None,
        },
    )

    review_page._start_build()

    assert review_page.select_qgis_path_button.isVisibleTo(review_page) is True
    assert "QGIS Desktop" in review_page.result_label.text()
    # No build must actually have been dispatched -- the runtime check failed before that point.
    assert len(_RecordingBuildWorkerThread.instances) == 0


def test_select_qgis_path_button_hidden_again_once_runtime_check_succeeds(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page.select_qgis_path_button.setVisible(True)  # simulate a prior failed attempt

    review_page._start_build()  # _make_wizard_with_fields stubs check_runtime to succeed

    assert review_page.select_qgis_path_button.isVisibleTo(review_page) is False
    assert len(_RecordingBuildWorkerThread.instances) == 1


def test_select_qgis_install_location_cancelled_picker_leaves_state_unchanged(
    tmp_path, monkeypatch
):
    """An empty/cancelled `QFileDialog.getExistingDirectory` result must never be treated as a
    real manual-path selection (mirrors FR-QPB-008's own blank-means-no-override contract)."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    calls = []

    def _fake_check_runtime(**kw):
        calls.append(kw)
        return {"available": False, "message": "x", "qgis_prefix_path": None}

    monkeypatch.setattr(runtime_module, "check_runtime", _fake_check_runtime)
    monkeypatch.setattr(wizard_module.QFileDialog, "getExistingDirectory", lambda *a, **k: "")

    review_page._on_select_qgis_install_location()

    assert calls == []  # check_runtime must never be re-consulted for a cancelled picker
    assert review_page._manual_qgis_path is None


def test_select_qgis_install_location_success_hides_button_and_remembers_path(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page.select_qgis_path_button.setVisible(True)
    chosen_dir = str(tmp_path / "MyQGIS")

    calls = []

    def _fake_check_runtime_with_manual_path(force_missing=False, manual_path=None):
        calls.append(manual_path)
        if manual_path == chosen_dir:
            return {"available": True, "message": "ok", "qgis_prefix_path": chosen_dir}
        return {"available": False, "message": "no", "qgis_prefix_path": None}

    monkeypatch.setattr(runtime_module, "check_runtime", _fake_check_runtime_with_manual_path)
    monkeypatch.setattr(
        wizard_module.QFileDialog, "getExistingDirectory", lambda *a, **k: chosen_dir
    )

    review_page._on_select_qgis_install_location()

    assert calls == [chosen_dir]
    assert review_page._manual_qgis_path == chosen_dir
    assert review_page.select_qgis_path_button.isVisibleTo(review_page) is False
    assert "확인했습니다" in review_page.result_label.text()


def test_select_qgis_install_location_failure_shows_the_specific_message_and_keeps_button(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page.select_qgis_path_button.setVisible(True)
    rejected_message = "지정한 위치에서 QGIS Desktop 설치를 확인할 수 없습니다."

    monkeypatch.setattr(
        runtime_module,
        "check_runtime",
        lambda **_kw: {"available": False, "message": rejected_message, "qgis_prefix_path": None},
    )
    monkeypatch.setattr(
        wizard_module.QFileDialog,
        "getExistingDirectory",
        lambda *a, **k: str(tmp_path / "not_a_qgis_install"),
    )

    review_page._on_select_qgis_install_location()

    assert review_page._manual_qgis_path is None
    assert review_page.select_qgis_path_button.isVisibleTo(review_page) is True
    assert review_page.result_label.text() == rejected_message


def test_successful_manual_override_is_reused_on_the_next_build_attempt_without_reselecting(
    tmp_path, monkeypatch
):
    """Session-local state: once a manual path has been verified, a later `_start_build()` call
    (e.g. the user clicking "생성" again) must pass it along automatically -- FR-QPB-008 does not
    require the user to re-pick the same folder for every attempt within one running session."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._manual_qgis_path = str(tmp_path / "AlreadyVerifiedQGIS")

    received_manual_paths = []

    def _fake_check_runtime(force_missing=False, manual_path=None):
        received_manual_paths.append(manual_path)
        return {"available": True, "message": "ok", "qgis_prefix_path": manual_path}

    monkeypatch.setattr(runtime_module, "check_runtime", _fake_check_runtime)

    review_page._start_build()

    assert received_manual_paths == [str(tmp_path / "AlreadyVerifiedQGIS")]


def test_collect_config_includes_manual_qgis_path_once_verified(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page._manual_qgis_path = str(tmp_path / "AlreadyVerifiedQGIS")

    config = review_page._collect_config()

    assert config["_manual_qgis_path"] == str(tmp_path / "AlreadyVerifiedQGIS")


def test_collect_config_omits_manual_qgis_path_when_never_set(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)

    config = review_page._collect_config()

    assert "_manual_qgis_path" not in config


# ---------------------------------------------------------------------------------------------
# 15. Bug 1 fix (real-device regression): a consent checkbox's long disclosure text must never
#     visually overlap the widget rendered directly below it in the same group box. This is
#     verified via actual computed geometry after a real Qt layout pass -- not merely by reading
#     source text -- because this exact defect was previously "reviewer-PASSed" at the
#     code-reading level and was only caught by a real on-screen screenshot; a test that only
#     inspects widget text would not have caught the original bug and would not catch a
#     regression either.
# ---------------------------------------------------------------------------------------------


def _assert_no_vertical_overlap(above, below) -> None:
    above_rect = above.geometry()
    below_rect = below.geometry()
    assert above_rect.bottom() <= below_rect.top(), (
        f"{above!r} (bottom={above_rect.bottom()}) vertically overlaps "
        f"{below!r} (top={below_rect.top()})"
    )


def _show_and_lay_out(widget, width=380) -> None:
    widget.resize(width, max(1, widget.sizeHint().height()))
    widget.show()
    QApplication.processEvents()
    widget.adjustSize()
    QApplication.processEvents()


def test_connectivity_basemap_consent_checkbox_does_not_overlap_remember_checkbox():
    page = ConnectivityBasemapPage()
    page.online_radio.setChecked(True)  # online_group is only visible in this state.
    _show_and_lay_out(page)

    assert page.online_group.isVisible()
    _assert_no_vertical_overlap(page.consent_disclosure_label, page.consent_checkbox)
    _assert_no_vertical_overlap(page.consent_checkbox, page.remember_checkbox)
    page.hide()


def test_connectivity_basemap_offline_key_usage_label_does_not_overlap_remember_checkbox():
    """Reviewer-round fix companion: `offline_key_usage_label` replaces
    `consent_disclosure_label`/`consent_checkbox` for offline mode (never shown at the same time --
    see `test_connectivity_page_offline_mode_never_shows_the_online_only_embedding_disclosure`) --
    it must not overlap `remember_checkbox` either, mirroring the online-mode layout guard above."""
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    _show_and_lay_out(page)

    assert page.offline_key_usage_label.isVisible()
    assert not page.consent_disclosure_label.isVisible()
    assert not page.consent_checkbox.isVisible()
    _assert_no_vertical_overlap(page.offline_key_usage_label, page.remember_checkbox)
    page.hide()


def test_connectivity_basemap_consent_checkbox_text_is_short_and_disclosure_is_on_the_label():
    """The structural half of the fix: the checkbox itself must carry only a short, single-line
    confirmation label -- the full disclosure text moved to `consent_disclosure_label` -- while
    the checkbox's checked state remains the actual `consent_accepted` gate, unchanged."""
    page = ConnectivityBasemapPage()
    assert len(page.consent_checkbox.text()) < 40
    assert ".qgs" not in page.consent_checkbox.text()
    assert ".qgs" in page.consent_disclosure_label.text()
    assert page.consent_disclosure_label.wordWrap() is True


def test_identification_toggle_plantnet_consent_checkbox_does_not_overlap_remember_checkbox():
    page = IdentificationTogglePage()
    page.enable_checkbox.setChecked(True)  # plantnet_group is only visible in this state.
    _show_and_lay_out(page)

    assert page.plantnet_group.isVisible()
    _assert_no_vertical_overlap(
        page.plantnet_consent_disclosure_label, page.plantnet_consent_checkbox
    )
    _assert_no_vertical_overlap(page.plantnet_consent_checkbox, page.plantnet_remember_checkbox)
    page.hide()


def test_identification_toggle_plantnet_consent_checkbox_text_is_short():
    page = IdentificationTogglePage()
    assert len(page.plantnet_consent_checkbox.text()) < 40
    assert "Pl@ntNet" not in page.plantnet_consent_checkbox.text()
    assert page.plantnet_consent_disclosure_label.wordWrap() is True


# ---------------------------------------------------------------------------------------------
# 16. Bug 2 fix (real-device regression): an API key with embedded whitespace/control characters
#     (e.g. a stray trailing newline from a paste) must be stripped before it ever reaches
#     `_collect_config()`'s output -- this is what a real VWorld/Pl@ntNet key ends up embedded in
#     a generated `.qgs` project and used to build download URLs from
#     (`qfield_builder.build`/`qfield_builder.vworld`).
# ---------------------------------------------------------------------------------------------


def test_collect_config_strips_whitespace_from_the_vworld_api_key(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    basemap_page: ConnectivityBasemapPage = wizard.page(3)
    basemap_page.online_radio.setChecked(True)
    basemap_page.api_key_edit.setText(" MY-KEY\n\t")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["basemap"]["vworld_api_key"] == "MY-KEY"


def test_collect_config_strips_whitespace_from_the_plantnet_api_key(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    identification_page: IdentificationTogglePage = wizard.page(4)
    identification_page.enable_checkbox.setChecked(True)
    identification_page.plantnet_api_key_edit.setText(" MY-PLANTNET-KEY\n\t")

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()

    assert config["plantnet"]["api_key"] == "MY-PLANTNET-KEY"


# ---------------------------------------------------------------------------------------------
# 17. New Step 6 -- Symbol styling configuration (FR-QPB-120/121/123; Decision Log D-61/D-65):
#     SymbolStylingPage's own field/selection behavior, and ReviewAndBuildPage._collect_config()'s
#     `symbol_styling` wiring. The wizard's own on-screen step *sequencing* (AC-QPB-104's first
#     clause) is a `manual`-marked acceptance-test placeholder per the approved acceptance suite --
#     out of this file's own scope -- but page(5) being a real, correctly configured
#     `SymbolStylingPage` instance, reachable at that index, is exercised throughout this section
#     and by `test_smoke_gui.py`'s real end-to-end wizard walk.
# ---------------------------------------------------------------------------------------------


def test_symbol_styling_page_defaults_to_minimalist_mode():
    # `QWizardPage.field()` only resolves once a page is attached to a real `QWizard` (see
    # `_make_wizard_with_fields`-based tests below for that coverage) -- a standalone page here
    # checks the same underlying getter `field("symbol_styling_mode")` would read from directly,
    # mirroring this file's own existing precedent for standalone `ConnectivityBasemapPage`/
    # `SurveyTypePage` widget-state checks above.
    page = SymbolStylingPage()
    assert page._get_symbol_styling_mode() == "minimalist"
    assert page.minimalist_radio.isChecked()
    assert page.selected_tabler_icon_name() is None
    assert page.tabler_group.isVisible() is False


def test_symbol_styling_page_switching_to_tabler_radio_updates_the_mode_field():
    page = SymbolStylingPage()
    page.show()  # isVisible() only reflects the real Qt visibility state once actually shown.
    page.tabler_radio.setChecked(True)
    assert page._get_symbol_styling_mode() == "tabler_icon"
    assert page.tabler_group.isVisible() is True


def test_symbol_styling_page_search_populates_results_from_the_bundled_index():
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)
    page.search_edit.setText("map-pin")
    items = [page.results_list.item(i).text() for i in range(page.results_list.count())]
    assert "map-pin" in items


def test_symbol_styling_page_search_never_shows_results_for_an_empty_query():
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)
    page.search_edit.setText("leaf")
    assert page.results_list.count() > 0
    page.search_edit.setText("")
    assert page.results_list.count() == 0


def test_symbol_styling_page_clicking_a_result_selects_it():
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)
    page.search_edit.setText("map-pin")
    page.results_list.setCurrentRow(0)
    assert page.selected_tabler_icon_name() == "map-pin"
    assert "map-pin" in page.selected_icon_label.text()


def test_symbol_styling_page_selection_survives_refining_the_search_text():
    """A fresh search clears and repopulates `results_list` (firing `currentTextChanged("")`
    along the way) -- the previously made selection must not be silently lost merely because the
    user kept typing."""
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)
    page.search_edit.setText("map-pin")
    page.results_list.setCurrentRow(0)
    assert page.selected_tabler_icon_name() == "map-pin"

    page.search_edit.setText("map-pin-2")  # a different, still-nonempty search.
    assert page.selected_tabler_icon_name() == "map-pin"


def test_symbol_styling_page_switching_back_to_minimalist_clears_the_selection():
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)
    page.search_edit.setText("map-pin")
    page.results_list.setCurrentRow(0)
    assert page.selected_tabler_icon_name() == "map-pin"

    page.minimalist_radio.setChecked(True)
    assert page.selected_tabler_icon_name() is None
    assert page._get_symbol_styling_mode() == "minimalist"


def test_collect_config_omits_symbol_styling_when_left_at_the_minimalist_default(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()
    assert "symbol_styling" not in config


def test_type4_skips_point_symbol_step_and_omits_symbol_styling_from_its_build_config(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    _select_survey_type(wizard, "vegetation_mapping")

    identification_page: IdentificationTogglePage = wizard.page(4)
    review_page: ReviewAndBuildPage = wizard.page(6)

    assert identification_page.nextId() == 6
    review_page.initializePage()
    assert review_page.title() == "6단계 - 검토 및 생성"
    assert "기호 스타일:" not in review_page.summary_view.toPlainText()
    assert "symbol_styling" not in review_page._collect_config()


def test_collect_config_omits_symbol_styling_when_tabler_mode_chosen_but_no_icon_selected(
    tmp_path, monkeypatch
):
    """FR-QPB-121: choosing Tabler mode without ever picking an icon must not produce a
    build-blocking or malformed config -- `build.py`'s own defensive fallback (or, here, simply
    omitting the key) applies, exactly as if the minimalist default had been left in place."""
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    symbol_styling_page: SymbolStylingPage = wizard.page(5)
    symbol_styling_page.tabler_radio.setChecked(True)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()
    assert "symbol_styling" not in config


def test_collect_config_includes_symbol_styling_once_an_icon_is_actually_selected(
    tmp_path, monkeypatch
):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    symbol_styling_page: SymbolStylingPage = wizard.page(5)
    symbol_styling_page.tabler_radio.setChecked(True)
    symbol_styling_page.search_edit.setText("leaf")
    symbol_styling_page.results_list.setCurrentRow(0)

    review_page: ReviewAndBuildPage = wizard.page(6)
    config = review_page._collect_config()
    assert config["symbol_styling"] == {"mode": "tabler_icon", "tabler_icon_name": "leaf"}


def test_review_page_summary_reflects_the_minimalist_default(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page.initializePage()
    assert "기본 미니멀 스타일" in review_page.summary_view.toPlainText()


def test_review_page_summary_reflects_a_selected_tabler_icon(tmp_path, monkeypatch):
    wizard = _make_wizard_with_fields(tmp_path, monkeypatch)
    symbol_styling_page: SymbolStylingPage = wizard.page(5)
    symbol_styling_page.tabler_radio.setChecked(True)
    symbol_styling_page.search_edit.setText("leaf")
    symbol_styling_page.results_list.setCurrentRow(0)

    review_page: ReviewAndBuildPage = wizard.page(6)
    review_page.initializePage()
    assert "leaf" in review_page.summary_view.toPlainText()


# ---------------------------------------------------------------------------------------------
# 17a. Live Tabler icon preview-fetch during search (FR-QPB-011(d)(ii), NFR-QPB-080 clauses
#      (5)-(8), AC-QPB-117; Decision Log D-76). Routed `tests/unit/` contract rows (see
#      tests/acceptance/qfield_project_builder_tabler_icon_preview_fetch.traceability.md):
#      - NFR-QPB-080(6): debounced, not fired on every keystroke.
#      - NFR-QPB-080(8)/AC-QPB-117: real, on-widget graceful degradation when every preview fetch
#        fails/is unavailable -- search and selection remain fully functional, nothing crashes.
#      NFR-QPB-080(7) (bounded concurrency) and NFR-QPB-080(5) (User-Agent parity) are routed to
#      `test_symbol_styling.py` instead, against the real, non-Qt production dispatch mechanism
#      (`symbol_styling.dispatch_preview_fetches_real`) those two rows are actually about.
# ---------------------------------------------------------------------------------------------


def test_symbol_styling_page_debounces_the_preview_fetch_dispatch_across_a_keystroke_burst(
    monkeypatch,
):
    """NFR-QPB-080(6): 'a fetch must not be issued on every keystroke, only after the user's
    input has briefly settled.' A rapid burst of successive `search_edit` text changes (each one
    a direct, synchronous call -- no event-loop tick elapses between them) must dispatch the real
    preview-fetch mechanism at most once, only after the burst stops and the debounce interval
    elapses -- never once per individual text change."""
    monkeypatch.setattr(SymbolStylingPage, "_PREVIEW_FETCH_DEBOUNCE_MS", 30)
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)

    dispatch_calls: list[list[str]] = []

    def _counting_dispatch(names: list[str]) -> dict:
        dispatch_calls.append(list(names))
        return {
            "requested_names": names,
            "previews": {n: {"success": False, "svg_content": None, "error": "network_error"}
                         for n in names},
        }

    page._preview_fetch_dispatch = _counting_dispatch

    for text in ["m", "ma", "map", "map-", "map-p", "map-pi", "map-pin"]:
        page.search_edit.setText(text)  # synchronous -- no real time elapses between these.

    assert dispatch_calls == [], (
        "must not dispatch a preview fetch on every keystroke during the burst itself"
    )

    # Let the (shortened) debounce interval elapse, plus a margin for the background worker
    # thread this dispatches on to actually run and its result to be delivered.
    QTest.qWait(300)

    assert len(dispatch_calls) == 1, (
        f"expected exactly one dispatch once the burst settled, got {len(dispatch_calls)}: "
        f"{dispatch_calls}"
    )
    assert "map-pin" in dispatch_calls[0]


def test_symbol_styling_page_search_and_selection_remain_functional_when_every_preview_fails(
    monkeypatch,
):
    """NFR-QPB-080(8)/AC-QPB-117: given the real `SymbolStylingPage`, when every preview fetch
    fails/is unavailable, the results list must still populate from
    `search_bundled_tabler_icon_names` exactly as before, remain selectable
    (`results_list.setCurrentItem`/`currentTextChanged` still updates
    `selected_tabler_icon_name()`), and no exception may propagate out of the text-changed
    handler or the Qt event loop."""
    monkeypatch.setattr(SymbolStylingPage, "_PREVIEW_FETCH_DEBOUNCE_MS", 10)
    page = SymbolStylingPage()
    page.tabler_radio.setChecked(True)

    def _always_failing_dispatch(names: list[str]) -> dict:
        return {
            "requested_names": names,
            "previews": {n: {"success": False, "svg_content": None, "error": "network_error"}
                         for n in names},
        }

    page._preview_fetch_dispatch = _always_failing_dispatch

    page.search_edit.setText("map")
    items_before = [page.results_list.item(i).text() for i in range(page.results_list.count())]
    assert items_before, "expected at least one real bundled match for 'map'"

    # Let the debounce settle and the background worker (calling the always-failing double)
    # run to completion; its `result_ready` signal is queued and delivered on the next tick(s).
    QTest.qWait(300)
    if page._preview_worker is not None:
        assert page._preview_worker.wait(2000), "preview-fetch worker never finished"
        QTest.qWait(50)

    items_after = [page.results_list.item(i).text() for i in range(page.results_list.count())]
    assert items_after == items_before, (
        "a fully failed preview-fetch batch must never alter the search results themselves"
    )
    for i in range(page.results_list.count()):
        assert page.results_list.item(i).icon().isNull(), (
            "a failed preview fetch must leave that result without an image"
        )

    # Selection-by-name must remain fully functional throughout.
    page.results_list.setCurrentRow(0)
    assert page.selected_tabler_icon_name() == items_after[0]


# ---------------------------------------------------------------------------------------------
# 17. AC-UI-QPB-001/002/005/011 positive regression: Step 4's page-level content viewport keeps
#     the hard 320x240 canvas and the controls below it in separate scroll-content geometry. The
#     former pre-fix monkeypatch/reproduction test was stale: after D-96 the page-level QScrollArea
#     owns the outer layout boundary, so disabling only the old nested wrap no longer models the
#     product's pre-D-96 layout. This test asserts the shipped behavior and preserves the stronger
#     no-overlap/canvas-floor contract.
# ---------------------------------------------------------------------------------------------


def _show_and_lay_out_at_size(widget, width: int, height: int) -> None:
    """Like `_show_and_lay_out` above, but at an explicit window size (mirroring this wizard's own
    real `_WIZARD_INITIAL_SIZE`/`_WIZARD_MIN_SIZE`) rather than a size derived from `sizeHint()` --
    this is what actually reproduces the real-device defect, which only manifests once the page's
    natural content need exceeds the space actually available to it."""
    widget.resize(width, height)
    widget.show()
    QApplication.processEvents()
    QApplication.processEvents()


@pytest.mark.parametrize(
    "size", [wizard_module._WIZARD_INITIAL_SIZE, wizard_module._WIZARD_MIN_SIZE]
)
def test_offline_map_canvas_does_not_overlap_clear_button(size):
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    _show_and_lay_out_at_size(page, *size)

    assert page.offline_map_canvas.isVisible()
    assert page._offline_clear_button.isVisible()
    _assert_no_vertical_overlap(page.offline_map_canvas, page._offline_clear_button)
    page.hide()


@pytest.mark.parametrize(
    "size", [wizard_module._WIZARD_INITIAL_SIZE, wizard_module._WIZARD_MIN_SIZE]
)
def test_offline_map_canvas_does_not_overlap_estimate_label(size):
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    _show_and_lay_out_at_size(page, *size)

    assert page.offline_estimate_label.isVisible()
    _assert_no_vertical_overlap(page._offline_clear_button, page.offline_estimate_label)
    _assert_no_vertical_overlap(page.offline_map_canvas, page.offline_estimate_label)
    page.hide()


def test_offline_map_canvas_keeps_its_full_320x240_usable_minimum_size():
    """The fix must not shrink the canvas to an unusably tiny fixed size as a workaround -- it
    must remain at least as usable as its existing 320x240 minimum, even at the wizard's own
    smallest allowed window size."""
    page = ConnectivityBasemapPage()
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    _show_and_lay_out_at_size(page, *wizard_module._WIZARD_MIN_SIZE)

    canvas_size = page.offline_map_canvas.size()
    assert canvas_size.width() >= 320
    assert canvas_size.height() >= 240
    page.hide()


def test_td_ui_qpb_011_offline_map_canvas_scrolls_inside_page_without_covering_controls():
    """AC-UI-QPB-001/002/005/011 and E-UI-QPB-001: page-level scrolling is the supported
    response when Step 4 drawing content exceeds the available viewport."""
    wizard = ProjectBuilderWizard()
    wizard.resize(*wizard_module._WIZARD_MIN_SIZE)
    wizard.show()
    wizard.setCurrentId(3)
    QApplication.processEvents()

    page = wizard.currentPage()
    assert isinstance(page, ConnectivityBasemapPage)
    page.offline_radio.setChecked(True)
    page.offline_bbox_source_draw_radio.setChecked(True)
    QApplication.processEvents()

    page_layout = page.layout()
    assert page_layout is not None
    viewport = next(
        item.widget()
        for index in range(page_layout.count())
        if (item := page_layout.itemAt(index)) is not None
        and isinstance(item.widget(), QScrollArea)
    )
    assert viewport.widget() is not None
    assert viewport.widgetResizable() is True
    assert viewport.verticalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert viewport.verticalScrollBar().maximum() > 0, (
        "AC-UI-QPB-002/E-UI-QPB-001: the long offline drawing state must actually be scrollable"
    )
    assert page.offline_map_canvas.minimumSize().width() >= 320
    assert page.offline_map_canvas.minimumSize().height() >= 240
    _assert_no_vertical_overlap(page.offline_map_canvas, page._offline_clear_button)
    _assert_no_vertical_overlap(page._offline_clear_button, page.offline_estimate_label)
    wizard.close()


@pytest.mark.parametrize(
    "size", [wizard_module._WIZARD_INITIAL_SIZE, wizard_module._WIZARD_MIN_SIZE]
)
def test_draw_map_canvas_does_not_overlap_status_label(size):
    """`SiteInputPage.draw_map_canvas` shares the same `MapCanvas` widget class (and the same hard
    320x240 minimum-size floor) as `ConnectivityBasemapPage.offline_map_canvas` -- confirms the
    same preventive scroll-area fix holds here too."""
    page = SiteInputPage()
    page._applicable = True
    page.input_mode_draw_radio.setChecked(True)
    page._update_input_mode_visibility()
    _show_and_lay_out_at_size(page, *size)

    assert page.draw_map_canvas.isVisible()
    assert page.draw_status_label.isVisible()
    _assert_no_vertical_overlap(page.draw_map_canvas, page.draw_status_label)
    page.hide()


def test_draw_map_canvas_keeps_its_full_320x240_usable_minimum_size():
    page = SiteInputPage()
    page._applicable = True
    page.input_mode_draw_radio.setChecked(True)
    page._update_input_mode_visibility()
    _show_and_lay_out_at_size(page, *wizard_module._WIZARD_MIN_SIZE)

    canvas_size = page.draw_map_canvas.size()
    assert canvas_size.width() >= 320
    assert canvas_size.height() >= 240


# ---------------------------------------------------------------------------------------------
# Application rename (FR-QPB-131), version display (FR-QPB-132/AC-QPB-122), and the wizard-banner
# branding decision (Decision Log D-81/D-82/D-86; `docs/ui-design-guidelines.md`, "Branding: logo
# asset and its two confirmed uses") -- the `tests/unit/test_wizard.py`-level contract routed by
# `tests/acceptance/qfield_project_builder_app_rename_version_and_branding.traceability.md`.
# ---------------------------------------------------------------------------------------------


def test_wizard_window_title_uses_standalone_and_not_the_old_product_name():
    """FR-QPB-131 (Decision Log D-81/D-86): the wizard's own window title -- this application's
    own UI -- names the application "FieldBuild Standalone," never the superseded "QField Project
    Builder.\""""
    wizard = ProjectBuilderWizard()
    assert "FieldBuild Standalone" in wizard.windowTitle()
    assert "QField Project Builder" not in wizard.windowTitle()


def test_wizard_window_title_shows_the_currently_running_version():
    """AC-QPB-122/FR-QPB-132: `qfield_builder.__version__` is visible somewhere in the wizard UI
    without requiring the user to inspect a file or run a command -- this implementation's own
    chosen placement is the wizard's own window title (FR-QPB-132's own proposed default)."""
    from qfield_builder import __version__

    wizard = ProjectBuilderWizard()
    assert __version__ in wizard.windowTitle()


def test_wizard_page_hierarchy_shows_independent_app_banner():
    """The independent app must not display the inherited FieldBuild Kit wordmark."""
    wizard = ProjectBuilderWizard()
    banner_labels = [
        label
        for label in wizard.findChildren(QLabel)
        if label.objectName() == "fieldbuild_standalone_logo_banner"
    ]
    assert banner_labels
    assert all(label.text() == "FieldBuild Standalone" for label in banner_labels)
