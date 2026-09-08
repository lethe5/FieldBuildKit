"""No private reference datasets belong in the app."""

import ast
from pathlib import Path


def test_spec_packages_no_reference_datasets():
    spec = Path(__file__).resolve().parents[2] / "packaging" / "qfield_builder.spec"
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    destinations = {
        node.elts[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Tuple) and len(node.elts) == 2
        and isinstance(node.elts[1], ast.Constant)
        and isinstance(node.elts[1].value, str)
    }
    assert not any(path.startswith("storage/") for path in destinations)
