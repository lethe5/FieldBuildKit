"""Only the merged probability cache belongs in the app, not the build-input TIFFs."""

import ast
from pathlib import Path


def test_spec_packages_probability_cache_without_source_rasters():
    spec = Path(__file__).resolve().parents[2] / "packaging" / "qfield_builder.spec"
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    destinations = {
        node.elts[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Tuple) and len(node.elts) == 2
        and isinstance(node.elts[1], ast.Constant)
        and isinstance(node.elts[1].value, str)
    }
    assert "storage/reference/probability_cache" in destinations
    assert not any(path.startswith("storage/reference/rasters") for path in destinations)
