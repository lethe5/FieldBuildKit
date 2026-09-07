"""Unit tests for qfield_builder.manifest and qfield_builder.transfer_readme."""
from __future__ import annotations

import json

from qfield_builder.manifest import build_manifest, find_missing_required_files, write_manifest
from qfield_builder.transfer_readme import build_readme_transfer_ko, write_readme_transfer_ko


def _sample_manifest():
    return build_manifest(
        project_dir="/does/not/matter",
        project_id="11111111-1111-4111-8111-111111111111",
        project_slug="my-project",
        survey_type="simple_inventory",
        qgs_relpath="my-project.qgs",
        gpkg_relpath="data/my-project.gpkg",
        attachment_relpaths=[],
        basemap_relpaths=["basemap/offline.mbtiles"],
        online_key_embedded=False,
    )


def test_manifest_never_contains_the_api_key_and_has_boolean_security_flag():
    manifest = build_manifest(
        project_dir="/x",
        project_id="id",
        project_slug="slug",
        survey_type="simple_inventory",
        qgs_relpath="slug.qgs",
        gpkg_relpath="data/slug.gpkg",
        attachment_relpaths=[],
        basemap_relpaths=[],
        online_key_embedded=True,
    )
    manifest_text = json.dumps(manifest)
    assert "FAKE-KEY" not in manifest_text
    assert manifest["security"]["online_layer_key_embedded_warning"] is True
    assert isinstance(manifest["security"]["online_layer_key_embedded_warning"], bool)


def test_manifest_includes_molit_vworld_attribution():
    manifest = _sample_manifest()
    manifest_text = json.dumps(manifest, ensure_ascii=False)
    assert "vworld" in manifest_text.lower()
    assert "국토교통부" in manifest_text or "molit" in manifest_text.lower()


def test_write_manifest_creates_valid_json_file(tmp_path):
    manifest = _sample_manifest()
    path = write_manifest(str(tmp_path), manifest)
    loaded = json.loads(open(path, encoding="utf-8").read())
    assert loaded["project_slug"] == "my-project"


def test_find_missing_required_files_detects_missing_basemap(tmp_path):
    manifest = _sample_manifest()
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "my-project.gpkg").write_bytes(b"fake")
    (tmp_path / "my-project.qgs").write_text("<qgis/>")
    # basemap/offline.mbtiles deliberately not created.
    issues = find_missing_required_files(str(tmp_path), manifest)
    codes = {i["code"] for i in issues}
    assert "missing_manifest_file" in codes
    assert any("offline.mbtiles" in i["message"] for i in issues)


def test_find_missing_required_files_clean_when_everything_present(tmp_path):
    manifest = _sample_manifest()
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "my-project.gpkg").write_bytes(b"fake")
    (tmp_path / "my-project.qgs").write_text("<qgis/>")
    (tmp_path / "basemap").mkdir()
    (tmp_path / "basemap" / "offline.mbtiles").write_bytes(b"fake")
    assert find_missing_required_files(str(tmp_path), manifest) == []


def test_readme_transfer_ko_covers_required_topics():
    text = build_readme_transfer_ko("테스트 프로젝트")
    lowered = text.lower()
    assert "qfieldsync" in lowered
    assert "qfield" in lowered
    assert "android" in lowered
    assert "ios" in lowered
    assert ".gpkg" in lowered or "geopackage" in lowered


def test_write_readme_transfer_ko_writes_file(tmp_path):
    path = write_readme_transfer_ko(str(tmp_path), "My Project")
    assert (tmp_path / "README_TRANSFER_KO.md").exists()
    assert "My Project" in open(path, encoding="utf-8").read()
