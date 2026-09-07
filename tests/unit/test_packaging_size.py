"""Keep runtime resources while omitting build-only assets and optional imaging support."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("separator", ["/", "\\"])
def test_data_filter_preserves_runtime_assets_and_supported_translations(separator):
    tree = ast.parse((ROOT / "packaging/qfield_builder.spec").read_text(encoding="utf-8"))
    filters = [
        node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Attribute) and target.attr == "datas"
                for target in node.targets)
    ]
    assert len(filters) == 1
    keep = [
        "resources/fieldbuild-kit-logo.png", "resources/config/vworld_layers.json",
        "resources/tabler/icon_names.txt", "resources/vendor/d3.v7.9.0.min.js",
        "storage/reference/probability_cache/occurrence_probability_multiband.tif",
        "storage/reference/tables/Rpt_2026-08-29_List.xlsx",
        "PySide6/Qt/translations/qtbase_ko.qm", "PySide6/Qt/translations/qtbase_en.qm",
        "PySide6/translations/qtbase_en_GB.qm", "PySide6/translations/qtbase_ko_KR.qm",
        "other/translations/messages_de.qm",
    ]
    drop = [
        "resources/app-icon-glass.icns", "resources/fieldbuild-kit-icon.icns",
        "resources/fieldbuild-kit-icon-mark.png", "PySide6/Qt/translations/qtbase_de.qm",
        "PySide6/translations/qtbase_fr.qm",
    ]
    entries = [(name.replace("/", separator), "/source", "DATA") for name in keep + drop]
    analysis = SimpleNamespace(datas=entries)
    exec(compile(ast.Module(body=filters, type_ignores=[]), "spec", "exec"), {"a": analysis})
    assert analysis.datas == entries[:len(keep)]


def test_pillow_is_excluded_only_from_the_app():
    tree = ast.parse((ROOT / "packaging/qfield_builder.spec").read_text(encoding="utf-8"))
    analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
    excluded = next(item.value for item in analysis.keywords if item.arg == "excludes")
    assert "PIL" in ast.literal_eval(excluded)
    assert '"Pillow>=10.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
