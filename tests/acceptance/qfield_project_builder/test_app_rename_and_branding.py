"""Application rename ("FieldBuild Standalone") and branding (Decision Log D-81/D-82/D-86;
`docs/ui-design-guidelines.md`'s "Branding: logo asset and its two confirmed uses").

Covers, with real, automated, offscreen-safe tests (plain text/AST inspection of static
repository files -- no Qt, no QGIS, no PyInstaller execution, no invocation of any
`qfield_builder` runtime module):

- FR-QPB-131 (Section 5.1): the application's own display name is "FieldBuild Standalone," superseding
  "QField Project Builder," as shown in `README.md` and the PyInstaller packaging configuration's
  own bundle name (`packaging/qfield_builder.spec`).
- The Category D logo decision's macOS-icon half (`docs/ui-design-guidelines.md`, "Branding: logo
  asset and its two confirmed uses"): the packaging spec's icon reference must no longer be the
  old `resources/app-icon-glass.icns` file, and must reference some `.icns` file under
  `resources/` instead (a `.icns` iconset being the documented macOS requirement for a `BUNDLE`
  icon, per that same guidelines section).

**What this file deliberately does NOT cover, and why (scope-boundary finding).** Several
criteria from this same round -- the wizard's own window title/in-UI product-name string
(FR-QPB-131), the version-string display (FR-QPB-132/AC-QPB-122), the credential-storage
directory migration (NFR-QPB-018/072 (further revised)/NFR-QPB-081/AC-QPB-119-AC-QPB-121), and
the wizard banner's own widget-existence fact (Category D logo item 1) -- all require either
directly constructing/driving a real PySide6 `QWizard`/`QWizardPage` object graph, or directly
invoking `qfield_builder.credential_store`'s own internal encrypt/store/retrieve functions
against a monkeypatched application-data directory. Both classes of check are, by this exact
project's own doubly-established precedent
(`../qfield_project_builder_credential_storage_mechanism.traceability.md`'s "Scope-boundary
finding"; `../qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.
traceability.md`'s "Genuinely out of this harness's reach" sections), the `implementer` role's
`tests/unit/` mandate,
not `test-designer`'s `tests/acceptance/`-only file-scope boundary -- both the checked-in system
role definition and `.claude/agents/test-designer.md` state, verbatim, "You may create or modify
files only under `tests/acceptance/`." See
`../qfield_project_builder_app_rename_version_and_branding.traceability.md` for the fully
specified, offscreen-automatable contract tables a `tests/unit/test_credential_store.py`-level and
a `tests/unit/test_wizard.py`-level test suite must satisfy for each of those criteria, and for
the `manual`-marked placeholders (below, in this file) covering the two genuinely
human/visual-only facts this round found (the regenerated macOS icon's actual visual content, and
the wizard banner's actual on-screen rendering quality).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "README.md"
PACKAGING_SPEC_PATH = REPO_ROOT / "packaging" / "qfield_builder.spec"

OLD_APP_NAME = "QField Project Builder"
NEW_APP_NAME = "FieldBuild Standalone"
OLD_ICON_FILENAME = "app-icon-glass.icns"


def _packaging_spec_ast() -> ast.Module:
    source = PACKAGING_SPEC_PATH.read_text(encoding="utf-8")
    # `packaging/qfield_builder.spec` is valid Python syntax that PyInstaller `exec()`s with
    # injected globals (`SPECPATH`, `Analysis`, `EXE`, `BUNDLE`, ...). `ast.parse` only parses the
    # syntax tree -- it never executes the file -- so this is a safe, static way to locate literal
    # assignment/call-argument values without needing PyInstaller installed or invoked, mirroring
    # `tests/unit/test_credential_store.py::test_module_source_contains_no_keyring_import`'s own
    # established `ast.parse(source)`-without-executing technique in this exact codebase.
    return ast.parse(source, filename=str(PACKAGING_SPEC_PATH))


def _top_level_assign_string_value(tree: ast.Module, name: str) -> str | None:
    """Returns the literal string value of a top-level `name = "..."` assignment, or `None` if no
    such assignment exists or its value is not a plain string literal."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if name in targets and isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                return node.value.value
    return None


def _find_call_by_name(tree: ast.Module, func_name: str) -> ast.Call | None:
    """Returns the first `Call` node in the tree whose callee is a bare `Name` equal to
    `func_name` (e.g. `BUNDLE(...)`), or `None` if no such call exists."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == func_name
        ):
            return node
    return None


def _keyword_value(call: ast.Call, keyword: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return None


def _stringify_expr_best_effort(expr: ast.expr) -> str:
    """Best-effort literal reconstruction of a (possibly `pathlib`-style) expression, e.g.
    `str(REPO_ROOT / "resources" / "app-icon-glass.icns")`, sufficient to find the literal
    path-segment string constants it is built from, *in their original left-to-right source
    order*, without evaluating the expression (which would require the real `REPO_ROOT`/
    PyInstaller-injected globals). Deliberately uses a manual, order-preserving recursive descent
    via `ast.iter_child_nodes` (pre-order, left-to-right) rather than `ast.walk` -- `ast.walk` is
    breadth-first and would silently reorder a left-associative `pathlib` `/`-chain's own string
    constants (e.g. `REPO_ROOT / "resources" / "app-icon-glass.icns"` parses as
    `BinOp(BinOp(REPO_ROOT, Div, "resources"), Div, "app-icon-glass.icns")`, whose two string
    constants sit at different tree depths), which would silently break any assertion relying on
    the resulting string's own suffix/prefix (e.g. `.endswith(".icns")`)."""
    parts: list[str] = []

    def _walk_in_order(node: ast.AST) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts.append(node.value)
        for child in ast.iter_child_nodes(node):
            _walk_in_order(child)

    _walk_in_order(expr)
    return "/".join(parts)


# ---------------------------------------------------------------------------------------------
# FR-QPB-131: README.md no longer names the application "QField Project Builder"; it is named
# "FieldBuild Standalone" instead.
# ---------------------------------------------------------------------------------------------


def test_readme_uses_fieldbuild_kit_and_not_the_old_product_name():
    text = README_PATH.read_text(encoding="utf-8")
    assert NEW_APP_NAME in text, (
        f"FR-QPB-131 (Decision Log D-81/D-86): README.md must name the application "
        f"'{NEW_APP_NAME}' somewhere in its text."
    )
    assert OLD_APP_NAME not in text, (
        f"FR-QPB-131 (Decision Log D-81/D-86): README.md must no longer contain the literal "
        f"superseded application name '{OLD_APP_NAME}' anywhere in its text."
    )


# ---------------------------------------------------------------------------------------------
# FR-QPB-131: the PyInstaller packaging configuration's own bundle name is "FieldBuild Standalone".
# ---------------------------------------------------------------------------------------------


def test_packaging_spec_app_name_is_fieldbuild_kit():
    tree = _packaging_spec_ast()
    app_name = _top_level_assign_string_value(tree, "APP_NAME")
    assert app_name is not None, (
        "packaging/qfield_builder.spec must define a top-level `APP_NAME = \"...\"` string "
        "literal assignment (as it does today, pre-rename, with the value "
        f"'{OLD_APP_NAME}')."
    )
    assert app_name == NEW_APP_NAME, (
        f"FR-QPB-131 (Decision Log D-81/D-86): packaging/qfield_builder.spec's own `APP_NAME` "
        f"must be '{NEW_APP_NAME}' (it determines the EXE/COLLECT/BUNDLE name and the "
        f"CFBundleName/CFBundleDisplayName info_plist values) -- got {app_name!r}."
    )


def test_packaging_spec_info_plist_strings_do_not_contain_the_old_product_name():
    """FR-QPB-131's "any other user-visible product-name string" clause: today's spec hardcodes
    the literal old name a second time, independent of `APP_NAME`, as the `NSHumanReadableCopyright`
    info_plist value (`"NSHumanReadableCopyright": "QField Project Builder"`) -- this must also be
    updated, not merely `APP_NAME` itself."""
    tree = _packaging_spec_ast()
    bundle_call = _find_call_by_name(tree, "BUNDLE")
    assert bundle_call is not None, (
        "packaging/qfield_builder.spec must contain a `BUNDLE(...)` call configuring the macOS "
        ".app bundle (as it does today, guarded by `sys.platform == 'darwin'`)."
    )
    info_plist_expr = _keyword_value(bundle_call, "info_plist")
    assert info_plist_expr is not None and isinstance(info_plist_expr, ast.Dict), (
        "packaging/qfield_builder.spec's BUNDLE(...) call must pass an `info_plist={...}` dict "
        "literal (as it does today)."
    )
    offending = [
        v.value
        for v in info_plist_expr.values
        if isinstance(v, ast.Constant) and isinstance(v.value, str) and OLD_APP_NAME in v.value
    ]
    assert not offending, (
        f"FR-QPB-131 (Decision Log D-81/D-86): no `info_plist` string value in "
        f"packaging/qfield_builder.spec's BUNDLE(...) call may still contain the superseded "
        f"application name '{OLD_APP_NAME}' -- found: {offending!r}."
    )


# ---------------------------------------------------------------------------------------------
# Category D (docs/ui-design-guidelines.md, "Branding: logo asset and its two confirmed uses"):
# the macOS app icon is regenerated from the icon-mark sub-region of
# resources/fieldbuild-kit-logo.png, replacing resources/app-icon-glass.icns.
# ---------------------------------------------------------------------------------------------


def _packaging_spec_bundle_icon_path_text() -> str:
    tree = _packaging_spec_ast()
    bundle_call = _find_call_by_name(tree, "BUNDLE")
    assert bundle_call is not None, (
        "packaging/qfield_builder.spec must contain a `BUNDLE(...)` call configuring the macOS "
        ".app bundle icon (as it does today)."
    )
    icon_expr = _keyword_value(bundle_call, "icon")
    assert icon_expr is not None, (
        "packaging/qfield_builder.spec's BUNDLE(...) call must pass an `icon=...` argument "
        "(as it does today)."
    )
    return _stringify_expr_best_effort(icon_expr)


def test_packaging_spec_icon_no_longer_references_the_old_glass_icon():
    icon_path_text = _packaging_spec_bundle_icon_path_text()
    assert OLD_ICON_FILENAME not in icon_path_text, (
        "docs/ui-design-guidelines.md ('Branding: logo asset and its two confirmed uses'): the "
        f"packaged macOS app's icon must no longer be '{OLD_ICON_FILENAME}' -- it must be "
        "regenerated from the icon-mark sub-region of resources/fieldbuild-kit-logo.png instead "
        f"-- got an icon path built from: {icon_path_text!r}."
    )


def test_packaging_spec_icon_references_an_icns_file_under_resources():
    """This does not (and cannot, since no exact filename is specified anywhere in the approved
    guidelines text) assert a specific new filename -- see this round's traceability file's
    ambiguity note. It asserts only the two concrete, textually-grounded facts the guidelines
    section states: the icon lives under `resources/`, and (per that section's own "a full
    `.icns` iconset at the standard multiple resolutions" text) it is an `.icns` file."""
    icon_path_text = _packaging_spec_bundle_icon_path_text()
    assert "resources" in icon_path_text, (
        f"Expected the packaged macOS app's icon to be built from a path under 'resources/' -- "
        f"got: {icon_path_text!r}."
    )
    assert icon_path_text.endswith(".icns"), (
        f"docs/ui-design-guidelines.md requires 'a full `.icns` iconset' for the regenerated "
        f"macOS app icon -- got a path not ending in '.icns': {icon_path_text!r}."
    )


# ---------------------------------------------------------------------------------------------
# manual-marked placeholders: genuinely human/visual-only facts no static text/AST inspection,
# and no headless PySide6/PyInstaller-free check, can confirm.
# ---------------------------------------------------------------------------------------------


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "docs/ui-design-guidelines.md ('Branding: logo asset and its two confirmed uses') "
        "requires the regenerated macOS app icon to be cropped from ONLY the icon-mark "
        "sub-region of resources/fieldbuild-kit-logo.png (the map-layers-with-pin graphic) -- "
        "never the full wide lockup image and never the wordmark text -- but 'does not specify "
        "an exact crop rectangle or pixel dimensions,' leaving the actual cropping/regeneration "
        "mechanism to the implementer. Confirming the resulting .icns file's actual visual "
        "content (does it genuinely show only the icon mark, correctly cropped, at each "
        "required resolution, with no wordmark text or stray whitespace/lockup padding visible) "
        "is a real, on-screen visual-correctness fact that requires actually building the macOS "
        ".app (packaging/build_macos_app.sh, per README.md's own 'Building the macOS .app' "
        "section) and looking at the resulting icon in Finder/Dock/'Get Info' -- not a "
        "generated-project artifact this harness's black-box build_project()/validate_project() "
        "convention can reach, not a pure logic function, and not even a static-file/AST check "
        "the way this file's own automated tests above are (those confirm only that *some* "
        ".icns file under resources/ is referenced, not that its pixel content is correct). "
        "Mirrors this suite's own established AC-QPB-104/FR-QPB-008 manual-placeholder "
        "convention for exactly this class of criterion."
        "\n\nManual QA steps: (1) Run packaging/build_macos_app.sh to produce a real, unsigned "
        "macOS .app bundle. (2) In Finder, select the built .app and press Cmd+I ('Get Info'), "
        "or view it in Finder icon view / the Dock after opening it. (3) Confirm the displayed "
        "icon is a square, layered-map-tiles-with-a-location-pin graphic (matching the icon-mark "
        "sub-region described in docs/ui-design-guidelines.md), NOT the prior glass-sphere icon "
        "(resources/app-icon-glass.icns) and NOT the full wide 'FieldBuild Standalone' wordmark lockup "
        "image. (4) Confirm the icon renders cleanly (no visible stray whitespace/padding from "
        "the original wide lockup image, no partial/cut-off wordmark text bleeding into the "
        "crop) at both a large ('Get Info' preview) and small (Dock) size."
    )
)
def test_macos_packaged_app_icon_shows_only_the_icon_mark_not_the_old_glass_icon_or_the_wordmark():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "docs/ui-design-guidelines.md ('Branding: logo asset and its two confirmed uses') "
        "requires resources/fieldbuild-kit-logo.png to be displayed as a banner somewhere in the "
        "desktop wizard's own UI, with exact placement left to implementer discretion. Whether "
        "some widget referencing that image file exists at all in the wizard's page hierarchy is "
        "a headlessly PySide6-offscreen-automatable fact (see "
        "../qfield_project_builder_app_rename_version_and_branding.traceability.md's routed "
        "contract table for tests/unit/test_wizard.py) -- but whether that image actually "
        "*renders correctly on screen* (not stretched/squashed out of its original aspect ratio, "
        "not cut off, recognizable as the FieldBuild Standalone logo lockup to a human looking at it) "
        "is a real, on-screen visual-rendering fact this harness cannot confirm through widget "
        "construction alone, mirroring the same distinction this suite's own Decision "
        "Log D-54/AC-QPB-096 precedent draws between 'a QML Image element exists in the source' "
        "(structural, automatable) and 'the image actually displays correctly once rendered' "
        "(manual-only)."
        "\n\nManual QA steps: (1) Launch the desktop wizard. (2) Confirm a banner image showing "
        "the FieldBuild Standalone logo (the layered-map-tiles-with-pin icon mark plus the "
        "'FieldBuild Standalone' wordmark, per resources/fieldbuild-kit-logo.png) is visibly displayed "
        "wherever the implementer placed it (every page, or only the first page). (3) Confirm "
        "the image is not visibly distorted (stretched/squashed out of its original ~3:1 "
        "aspect ratio), not cropped in a way that cuts off the wordmark or icon mark, and "
        "renders at a legible, reasonably-sized scale relative to the rest of the wizard page."
    )
)
def test_wizard_banner_renders_correctly_on_screen_not_distorted_or_cropped():
    raise AssertionError("should never run while skipped -- see skip reason")
