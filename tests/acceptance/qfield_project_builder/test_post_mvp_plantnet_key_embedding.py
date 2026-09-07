"""Pl@ntNet API key consent-gated key-embedding exception (Section 13.1a, Decision Log D-45).

Mirrors, for the Pl@ntNet API key, the VWorld online-layer consent-gated key-embedding pattern
already tested in `test_basemap_online.py` (AC-QPB-054/055/057/058, Decision Log D-21). See
FR-QPB-114-117 (Section 13.1a), NFR-QPB-071/072 (Section 14.1), and AC-QPB-079-082 (Section 18.6).

Covers:
- AC-QPB-079: consent declined -> no Pl@ntNet key embedded anywhere in the generated project
  (not the `.qgs` project variables, not the GeoPackage, not `MANIFEST.json`, not
  `VALIDATION_REPORT.json`, not the `<project_slug>.qml` plugin, not application logs) -- and the
  identification feature still falls back to manual QField key entry (FR-QPB-116), i.e. the
  feature itself remains present and usable; only its key *source* changes.
- AC-QPB-080: consent accepted -> the key is embedded ONLY as the `.qgs` project variable named
  exactly `qpb_plantnet_api_key` (FR-QPB-114); no other generated-project artifact contains it.
- AC-QPB-081: `MANIFEST.json` contains only a boolean security-warning flag for the Pl@ntNet
  embedding, never the key value itself, and this flag is independent of (can coexist with, or
  without) the pre-existing VWorld online-layer security-warning flag (NFR-QPB-017/071).
- AC-QPB-082: "Remember this key" (Pl@ntNet) -> retrieved from the OS credential store across
  sessions; otherwise session-only. This has the same harness black-box limitation already
  documented for AC-QPB-058 (see the traceability file's note 3, and the equivalent note this
  round adds): a headless `build_project()` call cannot observe a live desktop-application
  session's OS-keychain access, so this is verified as a proxy -- the generated project artifact
  never itself becomes a plaintext retention mechanism, either way.

Per Decision Log D-45 / FR-QPB-079 (revised) / NFR-QPB-019 (revised): this is now the second of
exactly two enumerated, independently scoped generated-project provider-credential exceptions
this specification permits (the other being FR-QPB-073's VWorld online-layer exception, tested in
`test_basemap_online.py`). Neither exception extends automatically to the other's credential, and
this closed, enumerated list must not be further extended without its own explicit stakeholder
decision (FR-QPB-079, revised).

See `HARNESS_CONTRACT.md`'s new "Post-MVP: Decision Log D-45" section for the `plantnet`
build-config dict this round adds, and for why `_read_project_variables()` below parses the `.qgs`
XML directly rather than inventing a new `acceptance_api` function.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

FAKE_PLANTNET_KEY = "ACCEPTANCE-TEST-FAKE-PLANTNET-KEY-0000"
FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-FAKE-KEY-0000"

PLANTNET_VARIABLE_NAME = "qpb_plantnet_api_key"


def _identification_config(
    consent_accepted: bool,
    remember_key: bool = False,
    survey_type: str = "simple_inventory",
    with_vworld_online: bool = False,
) -> dict:
    config = make_base_config(survey_type)
    config["identification_enabled"] = True
    config["plantnet"] = {
        "api_key": FAKE_PLANTNET_KEY,
        "consent_accepted": consent_accepted,
        "remember_key": remember_key,
    }
    if with_vworld_online:
        config["basemap"] = {
            "mode": "online",
            "vworld_api_key": FAKE_VWORLD_KEY,
            "layer": "Base",
            "consent_accepted": True,
            "remember_key": False,
        }
    return config


def _all_files(project_dir) -> list:
    return [p for p in Path(project_dir).rglob("*") if p.is_file()]


def _assert_key_absent_everywhere(project_dir, key: str) -> None:
    for path in _all_files(project_dir):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        assert key.encode() not in content, f"key must not appear anywhere, found in {path}"


def _assert_key_absent_outside_qgs(project_dir, key: str) -> None:
    for path in _all_files(project_dir):
        if path.suffix.lower() == ".qgs":
            continue
        try:
            content = path.read_bytes()
        except OSError:
            continue
        assert key.encode() not in content, (
            f"key must never appear outside the .qgs project variable; found in {path}"
        )


def _read_project_variables(qgs_path: str) -> dict:
    """Parses the standard QGIS `<properties><Variables><variableNames>/<variableValues>`
    parallel QStringList project-variable storage shape -- a documented fact about the `.qgs`
    container format itself (the same class of format-level fact `test_basemap_online.py` already
    relies on for `&` -> `&amp;` XML escaping), not an invented application behavior.
    """
    tree = ET.parse(qgs_path)
    root = tree.getroot()
    variables_elem = root.find(".//properties/Variables")
    if variables_elem is None:
        return {}
    names_elem = variables_elem.find("variableNames")
    values_elem = variables_elem.find("variableValues")
    if names_elem is None or values_elem is None:
        return {}
    names = [v.text for v in names_elem.findall("value")]
    values = [v.text for v in values_elem.findall("value")]
    return dict(zip(names, values))


def _manifest(project_dir) -> dict:
    manifest_path = f"{project_dir}/MANIFEST.json"
    return json.loads(open(manifest_path, "r", encoding="utf-8").read())


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else k)
    else:
        yield prefix, obj


def _security_warning_flags(manifest: dict) -> list:
    return [
        (key, value)
        for key, value in _flatten(manifest)
        if isinstance(value, bool)
        and ("security" in key.lower() or "credential" in key.lower() or "warning" in key.lower())
    ]


# --- AC-QPB-079 ------------------------------------------------------------------


def test_ac079_declined_consent_embeds_no_plantnet_key_anywhere(acceptance_api, tmp_path):
    config = _identification_config(consent_accepted=False)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    _assert_key_absent_everywhere(result["project_dir"], FAKE_PLANTNET_KEY)


def test_ac079_declined_consent_still_leaves_identification_feature_present(
    acceptance_api, inspect_identification_widget, tmp_path
):
    """FR-QPB-116: declining consent must not remove the identification feature itself -- only
    its key source falls back to manual QField entry."""
    config = _identification_config(consent_accepted=False)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    assert (project_dir / f"{slug}.qml").is_file(), (
        "FR-QPB-116: the <project_slug>.qml identification plugin must still be present when "
        "Pl@ntNet key-embedding consent is declined"
    )

    report = inspect_identification_widget(result["project_dir"], "inventory_observation")
    assert report["qml_widget_field_found"] is True, (
        f"FR-QPB-116: the embedded QML Widget identification action must still be present and "
        f"usable when consent is declined (manual-key-entry fallback): {report}"
    )


# --- AC-QPB-080 ------------------------------------------------------------------


def test_ac080_accepted_consent_embeds_key_only_as_the_project_variable(acceptance_api, tmp_path):
    config = _identification_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    variables = _read_project_variables(result["qgs_path"])
    assert variables.get(PLANTNET_VARIABLE_NAME) == FAKE_PLANTNET_KEY, (
        f"AC-QPB-080/FR-QPB-114: expected a `.qgs` project variable named exactly "
        f"{PLANTNET_VARIABLE_NAME!r} holding the key; found project variables: {variables}"
    )

    _assert_key_absent_outside_qgs(result["project_dir"], FAKE_PLANTNET_KEY)


# --- AC-QPB-081 ------------------------------------------------------------------


def test_ac081_manifest_contains_only_a_boolean_plantnet_security_warning_flag(
    acceptance_api, tmp_path
):
    config = _identification_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    manifest = _manifest(result["project_dir"])
    manifest_text = json.dumps(manifest)
    assert FAKE_PLANTNET_KEY not in manifest_text

    flags = _security_warning_flags(manifest)
    plantnet_true_flags = [k for k, v in flags if v is True and "plantnet" in k.lower()]
    assert plantnet_true_flags, (
        f"NFR-QPB-071: expected a boolean Pl@ntNet security-warning flag in MANIFEST.json; "
        f"manifest: {manifest}"
    )


def test_ac081_plantnet_flag_is_independent_of_the_existing_vworld_flag(acceptance_api, tmp_path):
    """NFR-QPB-071: a generated project may carry either flag, both, or neither, independently."""
    # Only Pl@ntNet embedded (no VWorld online layer): only the Pl@ntNet flag is true.
    config_only = _identification_config(consent_accepted=True, with_vworld_online=False)
    result_only = acceptance_api.build_project(config_only, str(tmp_path / "plantnet_only"))
    assert result_only["success"], result_only.get("error_message")

    flags_only = _security_warning_flags(_manifest(result_only["project_dir"]))
    true_flags_only = [k for k, v in flags_only if v is True]
    assert true_flags_only, f"expected at least one true security-warning flag: {flags_only}"
    assert all("plantnet" in k.lower() for k in true_flags_only), (
        f"NFR-QPB-071: with no VWorld key embedded, only the Pl@ntNet flag should be true: "
        f"{flags_only}"
    )

    # Both Pl@ntNet and VWorld embedded: both flags present and true, independently of each other.
    config_both = _identification_config(consent_accepted=True, with_vworld_online=True)
    result_both = acceptance_api.build_project(config_both, str(tmp_path / "both"))
    assert result_both["success"], result_both.get("error_message")

    flags_both = _security_warning_flags(_manifest(result_both["project_dir"]))
    true_flags_both = [k for k, v in flags_both if v is True]
    plantnet_true = [k for k in true_flags_both if "plantnet" in k.lower()]
    other_true = [k for k in true_flags_both if "plantnet" not in k.lower()]
    assert plantnet_true, f"expected a true Pl@ntNet security-warning flag: {flags_both}"
    assert other_true, (
        f"NFR-QPB-071: expected the pre-existing VWorld security-warning flag to remain true "
        f"independently alongside the Pl@ntNet flag when both are embedded: {flags_both}"
    )


# --- AC-QPB-082 ------------------------------------------------------------------


def test_ac082_remember_key_uses_os_credential_store_not_plaintext(acceptance_api, tmp_path):
    config = _identification_config(consent_accepted=True, remember_key=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    # NFR-QPB-072: "remember this key" must store the key in the OS credential store, not in a
    # plaintext application file. We can at least assert no plaintext application/project file
    # (outside the one permitted .qgs project-variable location) contains the key.
    _assert_key_absent_outside_qgs(result["project_dir"], FAKE_PLANTNET_KEY)


def test_plantnet_key_not_remembered_by_default_across_sessions(acceptance_api, tmp_path):
    """NFR-QPB-072: without 'remember this key', retention is session-only.

    This cannot be fully verified without a real desktop-application session boundary; verified
    here as the contrapositive of the remembered case: the generated project (an on-disk
    artifact, not a live session) never itself becomes the retention mechanism.
    """
    config = _identification_config(consent_accepted=True, remember_key=False)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    _assert_key_absent_outside_qgs(result["project_dir"], FAKE_PLANTNET_KEY)
