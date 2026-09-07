"""Exclude unused Qt entry points without stripping dependencies of retained plugins."""

import ast
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("prefix,suffix", [("", ".dll"), ("lib", ".dylib"), ("lib", ".so")])
def test_qtgui_hook_preserves_needed_plugins(monkeypatch, tmp_path, prefix, suffix):
    names = ["qpdf", "qtvirtualkeyboardplugin", "qsvg", "qjpeg", "qcocoa", "qwindows", "qibus"]
    binaries = [(str(tmp_path / f"{prefix}{name}{suffix}"), "plugins") for name in names]
    imports, datas = ["PySide6.QtCore"], [("qtbase_ko.qm", "translations")]
    monkeypatch.setitem(sys.modules, "PyInstaller.utils.hooks.qt", SimpleNamespace(
        add_qt6_dependencies=lambda _path: (imports, binaries, datas)
    ))
    result = runpy.run_path(str(ROOT / "packaging/hooks/hook-PySide6.QtGui.py"))
    assert result["binaries"] == binaries[2:]
    assert result["hiddenimports"] == imports
    assert result["datas"] == datas


def test_spec_excludes_only_unused_qt_python_modules():
    tree = ast.parse((ROOT / "packaging/qfield_builder.spec").read_text(encoding="utf-8"))
    analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
    keywords = {item.arg: item.value for item in analysis.keywords}
    excluded = set(ast.literal_eval(keywords["excludes"]))
    assert {"PySide6.QtPdf", "PySide6.QtQuick", "PySide6.QtQml"} <= excluded
    assert not excluded.intersection({
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtNetwork",
        "PySide6.QtSvg", "PySide6.QtDBus",
    })
    hook_paths = eval(compile(ast.Expression(keywords["hookspath"]), "spec", "eval"), {
        "REPO_ROOT": ROOT,
    })
    assert str(ROOT / "packaging/hooks") in hook_paths
    # Future UI imports must not silently depend on a module excluded from distribution.
    excluded = {name for name in excluded if name.startswith("PySide6.")}
    for path in (ROOT / "qfield_builder").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in excluded, path
            elif isinstance(node, ast.Import):
                assert not excluded.intersection(alias.name for alias in node.names), path
