"""Check the platform-specific DLL filter without running a full PyInstaller build."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_icu_filter_is_windows_only(platform):
    spec = Path(__file__).resolve().parents[2] / "packaging" / "qfield_builder.spec"
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    # Run the top-level binary filter, preserving its platform guard.
    filters = [
        node for node in tree.body
        if isinstance(node, ast.If)
        and any(
            isinstance(child, ast.Attribute)
            and isinstance(child.ctx, ast.Store)
            and child.attr == "binaries"
            for child in ast.walk(node)
        )
    ]
    assert len(filters) == 1
    binaries = [(name, "/source/" + name, "BINARY") for name in (
        "ICUUC.DLL", "icudt78.dll", "Qt6Core.dll", "icuin78.dll", "libicuuc.dylib"
    )]
    analysis = SimpleNamespace(binaries=binaries.copy())
    exec(compile(ast.Module(body=filters, type_ignores=[]), str(spec), "exec"), {
        "sys": SimpleNamespace(platform=platform), "a": analysis,
    })
    assert analysis.binaries == (binaries[2:] if platform == "win32" else binaries)
