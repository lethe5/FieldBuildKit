import zipfile

import pytest

from qfield_builder.errors import BuildError
from qfield_builder.site_upload import (
    infer_format,
    normalize_epsg_code,
    shapefile_has_prj,
)


def test_infer_format_accepts_standalone_shapefile():
    assert infer_format("/tmp/sites.shp") == "shapefile"
    assert infer_format("/tmp/sites.SHP") == "shapefile"


def test_shapefile_prj_detection_handles_standalone_and_zip(tmp_path):
    shp_path = tmp_path / "sites.shp"
    shp_path.write_bytes(b"shp")
    assert not shapefile_has_prj("shapefile", str(shp_path))

    (tmp_path / "sites.PRJ").write_text('GEOGCS["WGS 84"]', encoding="utf-8")
    assert shapefile_has_prj("shapefile", str(shp_path))

    zip_path = tmp_path / "sites.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/sites.shp", b"shp")
        archive.writestr("nested/sites.prj", b"GEOGCS[\"WGS 84\"]")
    assert shapefile_has_prj("zipped_shapefile", str(zip_path))


def test_normalize_epsg_code_accepts_plain_and_prefixed_values():
    assert normalize_epsg_code("5186") == "EPSG:5186"
    assert normalize_epsg_code(" epsg:4326 ") == "EPSG:4326"


@pytest.mark.parametrize("value", [None, "", "EPSG:", "WGS84", "-1", "1000000"])
def test_normalize_epsg_code_rejects_invalid_values(value):
    with pytest.raises(BuildError, match="EPSG 코드"):
        normalize_epsg_code(value)
