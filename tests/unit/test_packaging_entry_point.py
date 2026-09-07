"""Structural regression coverage for `packaging/entry_point.py`'s
`multiprocessing.freeze_support()` fix (Bug 1: a real, packaged `.app` spawning extra full-GUI
windows -- see this module's own docstring below for why this is the *only* kind of automated
coverage this specific bug admits).

This bug only actually manifests in a *frozen* PyInstaller executable's real `sys.frozen`-gated
`multiprocessing` respawn behavior (see `packaging/entry_point.py`'s own module docstring for the
full mechanism, confirmed by reading CPython's `multiprocessing.spawn`/`resource_tracker` source
directly). A plain `pytest`-from-source run is never frozen (`sys.frozen` is never set), so no
in-process/subprocess test run via `pytest` can actually exercise the real defect -- that is
exactly why the pre-fix code shipped without this being caught by the existing suite, and it is
also why this implementation round's actual verification of the fix was performed directly against
the real, rebuilt `.app` binary (process-tree monitoring; see the implementer's completion report
for this round for the exact commands and observed process list), not via any test in this file or
elsewhere in this repository.

What *can* be usefully guarded here, structurally, without a frozen build: that the fix itself --
calling `multiprocessing.freeze_support()` as the very first statement inside
`if __name__ == "__main__":`, before `main()` is ever called -- is not silently removed, reordered
after `main()`, or moved outside the `__main__` guard by some future refactor. This is checked via
`ast` (structural parsing), not string matching, so it is robust to incidental formatting changes.
"""
from __future__ import annotations

import ast
from pathlib import Path

_ENTRY_POINT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "packaging" / "entry_point.py"
)


def _find_main_guard(tree: ast.Module) -> ast.If:
    for node in tree.body:
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            return node
    raise AssertionError(
        "packaging/entry_point.py has no `if __name__ == '__main__':` block at all -- the "
        "multiprocessing.freeze_support() fix (and the script's own purpose) depends on one "
        "existing."
    )


def test_entry_point_imports_multiprocessing():
    """A regression guard for the most trivial way this fix could be silently undone: removing
    the `import multiprocessing` statement (leaving a `NameError` at the call site below, which
    would only ever be discovered by actually running the frozen `.app` -- exactly the class of
    silent regression this test exists to catch earlier, in plain source review/CI)."""
    tree = ast.parse(_ENTRY_POINT_PATH.read_text(encoding="utf-8"))
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
    assert "multiprocessing" in imported_names


def test_entry_point_calls_freeze_support_as_the_first_statement_in_main_guard():
    """The actual fix for Bug 1: `multiprocessing.freeze_support()` must be the first statement
    inside `if __name__ == "__main__":`, strictly before `main()` is ever invoked -- per Python's
    own documented guidance ("Programming guidelines" -> "Frozen executables" in the
    `multiprocessing` docs) and, empirically for this codebase, before PyInstaller's own
    multiprocessing runtime hook's enhanced `freeze_support()` (which also intercepts the
    resource-tracker helper's respawn, not just the worker's -- see `entry_point.py`'s own
    docstring) gets a chance to redirect this process into the real dispatched job instead of
    falling through into a second `main()`/`QApplication` launch.
    """
    tree = ast.parse(_ENTRY_POINT_PATH.read_text(encoding="utf-8"))
    main_guard = _find_main_guard(tree)
    assert main_guard.body, "the `if __name__ == '__main__':` block must not be empty"

    first_statement = main_guard.body[0]
    assert isinstance(first_statement, ast.Expr), (
        "the first statement inside `if __name__ == '__main__':` must be a bare call "
        f"expression (multiprocessing.freeze_support()), found: {ast.dump(first_statement)}"
    )
    call = first_statement.value
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    assert call.func.attr == "freeze_support"
    assert isinstance(call.func.value, ast.Name)
    assert call.func.value.id == "multiprocessing"

    # And, just as importantly, that this is genuinely *before* `main()` is called -- not just
    # present somewhere in the block.
    remaining_source = ast.dump(ast.Module(body=main_guard.body[1:], type_ignores=[]))
    assert "main" in remaining_source, (
        "sanity check: main() should still be called somewhere after freeze_support() in this "
        "block -- if this assertion itself fails, the test fixture/parsing assumption is wrong, "
        "not the production code"
    )


def test_entry_point_does_not_call_main_before_freeze_support():
    """Belt-and-suspenders check against a reordering regression (e.g. someone moves the
    `sys.exit(main())` line above `multiprocessing.freeze_support()` during a future edit)."""
    tree = ast.parse(_ENTRY_POINT_PATH.read_text(encoding="utf-8"))
    main_guard = _find_main_guard(tree)

    call_order = []
    for stmt in main_guard.body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("freeze_support",):
                    call_order.append("freeze_support")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "main":
                    call_order.append("main")

    assert "freeze_support" in call_order
    assert "main" in call_order
    assert call_order.index("freeze_support") < call_order.index("main"), (
        f"freeze_support() must be called before main(); observed call order: {call_order}"
    )
