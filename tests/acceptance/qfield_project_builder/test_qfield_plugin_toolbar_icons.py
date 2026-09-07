"""D-97 structural regressions for project-local QField toolbar assets.

These tests inspect the generated project folder and its ``<project_slug>.qml`` sidecar. They
cover the portable asset, control, callback, and plugin-owned exactly-once registration contracts
in FR-QPB-143 / AC-QPB-147; they do not claim to render a QField toolbar. The required iPhone
visual confirmation remains in ``test_d97_iphone_qfield_verification.py``.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis


_ACTION_CONTRACTS = (
    {
        "accessible_name": "HTML 보고서 내보내기",
        "asset": "icons/report-export.svg",
    },
    {
        "accessible_name": "사진으로 식물 동정",
        "asset": "icons/plant-identification.svg",
    },
)
_EXTERNAL_ICON_RESOURCE_RE = re.compile(r"(?:qrc\s*:|(?:https?|file)://)", re.IGNORECASE)


def _build_project(acceptance_api, tmp_path, *, identification_enabled: bool) -> tuple[dict, str]:
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = identification_enabled
    state = "identification-enabled" if identification_enabled else "identification-disabled"
    result = acceptance_api.build_project(config, str(tmp_path / state))
    assert result["success"], result.get("error_message")

    source = (Path(result["project_dir"]) / f"{result['project_slug']}.qml").read_text(
        encoding="utf-8"
    )
    return result, source


def _qml_object_blocks(source: str) -> list[str]:
    """Return all balanced QfToolButton blocks without requiring a QML runtime."""
    blocks: list[str] = []
    for match in re.finditer(r"QfToolButton\s*\{", source):
        body_start = match.end()
        depth = 1
        for index in range(body_start, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[match.start() : index + 1])
                    break
        else:
            raise AssertionError("QfToolButton block is not balanced QML")
    return blocks


def _qml_object_block(source: str, accessible_name: str) -> str:
    """Return the QfToolButton containing the required accessible action name."""
    accessible_name_pattern = re.compile(
        r"Accessible\.name\s*:\s*\"" + re.escape(accessible_name) + r"\""
    )
    for block in _qml_object_blocks(source):
        if accessible_name_pattern.search(block):
            return block
    raise AssertionError(f"expected a QfToolButton with Accessible.name {accessible_name!r}")


def _balanced_handler_body(block: str, property_name: str) -> str:
    match = re.search(rf"\b{re.escape(property_name)}\s*:\s*\{{", block)
    if not match:
        expression = re.search(rf"\b{re.escape(property_name)}\s*:\s*([^\n]+)", block)
        assert expression, f"toolbar control must attach an {property_name} callback"
        return expression.group(1)
    body_start = match.end()
    depth = 1
    for index in range(body_start, len(block)):
        if block[index] == "{":
            depth += 1
        elif block[index] == "}":
            depth -= 1
            if depth == 0:
                return block[body_start:index]
    raise AssertionError(f"{property_name} callback is not balanced QML")


def _assert_complete_self_contained_svg(project_dir: Path, asset: str) -> None:
    asset_path = project_dir / asset
    matches = list(project_dir.rglob(Path(asset).name))
    assert matches == [asset_path], (
        f"expected exactly one project-local {asset} asset, found {matches!r}"
    )

    content = asset_path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise AssertionError(f"{asset} must be a complete parseable SVG: {exc}") from exc
    assert root.tag.rsplit("}", 1)[-1] == "svg", f"{asset} must have an SVG root element"
    assert not _EXTERNAL_ICON_RESOURCE_RE.search(content), (
        f"{asset} must be self-contained and cannot load a qrc:, file:, or network resource"
    )
    assert "Theme" not in content, f"{asset} must not depend on a QField icon theme"


def _assert_project_relative_icon_source(block: str, asset: str, accessible_name: str) -> None:
    source_matches = re.findall(
        rf"\b(?:iconSource|icon\.source)\s*:\s*([^\n]*{re.escape(asset)}[^\n]*)",
        block,
    )
    assert len(source_matches) == 1, (
        f"{accessible_name}: exactly one icon source must resolve {asset!r} from the project"
    )
    source_expression = source_matches[0]
    relative_paths = re.findall(rf"[\"']((?:\./)?{re.escape(asset)})[\"']", source_expression)
    assert relative_paths, (
        f"{accessible_name}: icon source must use the project-relative {asset!r} path; "
        f"expression: {source_expression!r}"
    )
    assert not _EXTERNAL_ICON_RESOURCE_RE.search(source_expression), (
        f"{accessible_name}: icon source cannot use a qrc:, file:, or network URI"
    )
    assert "Theme" not in block, (
        f"{accessible_name}: the toolbar control must not fall back to a QField icon theme"
    )
    assert "qrc:" not in block.lower(), (
        f"{accessible_name}: the toolbar control must not use a qrc icon source"
    )


def _assert_control_contract(block: str, contract: dict[str, str]) -> None:
    accessible_name = contract["accessible_name"]
    visible_text = re.search(r"\btext\s*:\s*(?!\"\"|'')", block)
    assert not visible_text, (
        f"{accessible_name}: the toolbar control must have no visible button text; found "
        f"{visible_text.group(0)!r}"
    )
    for dimension in ("width", "height"):
        size = re.search(rf"{dimension}\s*:\s*(\d+)", block)
        assert size and int(size.group(1)) == 48, (
            f"{accessible_name}: {dimension} must be exactly 48px"
        )

    callback = _balanced_handler_body(block, "onClicked")
    assert re.search(r"[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*\s*\(", callback), (
        f"{accessible_name}: onClicked must retain an action callback, not an empty handler"
    )

    _assert_project_relative_icon_source(block, contract["asset"], accessible_name)


def _assert_plugin_owned_single_registration(
    source: str, control_blocks: list[str], expected_control_count: int
) -> None:
    """Check the sidecar's observable registration contract without dictating its QML strategy."""
    registrations = re.findall(r"iface\.addItemToPluginsToolbar\s*\(", source)
    assert len(registrations) == expected_control_count, (
        "the project-local plugin must contain exactly one toolbar registration per required "
        "QfToolButton: no duplicate registration and no missing registration"
    )

    # `findItemByObjectName` is useful for QField-owned internal items, but it cannot safely
    # determine whether this plugin's own QfToolButton has already been registered: QField may
    # resolve the local object before its first toolbar registration. Do not prescribe a positive
    # guard/state mechanism; only reject this self-suppressing lookup when an implementation elects
    # to give a local toolbar control an objectName.
    for block in control_blocks:
        for object_name in re.findall(r'objectName\s*:\s*"([^"]+)"', block):
            if not object_name:
                continue
            assert not re.search(
                rf"iface\.findItemByObjectName\s*\(\s*['\"]{re.escape(object_name)}['\"]\s*\)",
                source,
            ), (
                f"{object_name!r} is a project-local QfToolButton and must not use "
                "iface.findItemByObjectName as its registration state: that lookup can find the "
                "control before its first toolbar registration and suppress it. Use any "
                "plugin-owned exactly-once registration flow instead."
            )


@pytest.mark.parametrize("identification_enabled", [False, True])
def test_ac147_project_local_toolbar_assets_controls_callbacks_and_registration(
    acceptance_api, tmp_path, identification_enabled
):
    """AC-QPB-147: portable SVG controls have the exact enabled/disabled structure."""
    result, source = _build_project(
        acceptance_api, tmp_path, identification_enabled=identification_enabled
    )
    project_dir = Path(result["project_dir"])
    expected_contracts = _ACTION_CONTRACTS if identification_enabled else _ACTION_CONTRACTS[:1]

    assert len(_qml_object_blocks(source)) == len(expected_contracts), (
        "the project plugin must define exactly one report-export QfToolButton when identification "
        "is disabled and exactly two controls when it is enabled"
    )
    control_blocks = _qml_object_blocks(source)
    _assert_plugin_owned_single_registration(source, control_blocks, len(expected_contracts))
    for contract in expected_contracts:
        _assert_complete_self_contained_svg(project_dir, contract["asset"])
        block = _qml_object_block(source, contract["accessible_name"])
        _assert_control_contract(block, contract)

    plant_asset = project_dir / _ACTION_CONTRACTS[1]["asset"]
    if not identification_enabled:
        assert not plant_asset.exists(), (
            "identification-disabled projects must not bundle plant-identification.svg"
        )
        assert not list(project_dir.rglob(plant_asset.name)), (
            "identification-disabled projects must not contain a duplicate plant-identification "
            "asset"
        )
        assert _ACTION_CONTRACTS[1]["accessible_name"] not in source, (
            "identification-disabled projects must not define the plant-identification toolbar "
            "control"
        )
