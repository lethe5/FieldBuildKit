"""Online VWorld basemap and the consent-gated key-embedding exception (Section 10, D-21).

Covers:
- AC-QPB-017: valid VWorld key + online mode -> the VWorld layer loads successfully.
- AC-QPB-068 (Decision Log D-29): the online VWorld layer connects via QGIS's native WMTS
  provider, pointed at the VWorld WMTS capabilities endpoint, and does not contain the
  superseded manually constructed per-tile XYZ URL template / `type=xyz` datasource shape.
- AC-QPB-054: consent declined -> no key embedded anywhere, online layer omitted.
- AC-QPB-055: consent accepted -> key only in the .qgs online-layer URL, nowhere else.
- AC-QPB-057: MANIFEST.json contains only a boolean security-warning flag, never the key.
- AC-QPB-058: "Remember this key" -> retrieved from OS credential store; otherwise session-only.
- AC-QPB-051 (online half): required MOLIT/VWorld KOGL Type-1 attribution present in the project
  and MANIFEST.json.

AC-QPB-017's "loads successfully" claim is split across two tests (stakeholder decision,
2026-08-14, following the AC-QPB-068/D-29 correction below), because the new QGIS-native WMTS
datasource (FR-QPB-072 revised/Decision Log D-29) makes QGIS perform a real GetCapabilities
negotiation against the live VWorld service at project-open time. A necessarily-fake acceptance
key genuinely cannot pass that negotiation: VWorld's real endpoint correctly returns an OGC
`ExceptionReport` for an unregistered key, so QGIS correctly marks the layer invalid (confirmed
independently against the live service, not merely asserted) -- this is expected, spec-consistent
behavior, not a defect.

- The offline-safe proxy test below,
  `test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully`, verifies only
  what a fake key can honestly verify without a live, valid VWorld connection: that the `.qgs`
  online layer is configured with a correctly shaped VWorld WMTS datasource -- QGIS's native WMTS
  provider, pointed at the VWorld WMTS capabilities endpoint, containing none of the superseded
  manually constructed per-tile XYZ shape (AC-QPB-068). It does not call `validate_project()` /
  assert `opens_without_repair_warning`, because that claim cannot be honestly verified with a
  fake key under this architecture.
- AC-QPB-017's actual "opens without a repair warning" claim is genuinely verified only by
  `test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key` below
  (`@pytest.mark.network`, skipped by default; requires `--run-network` and a real VWorld API key
  exported as `QPB_TEST_VWORLD_API_KEY`). This is local QGIS/PyQGIS evidence only; D-97's distinct
  AC-QPB-146 iPhone-QField Satellite result remains a documented manual/device gate.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

FAKE_VWORLD_KEY = "ACCEPTANCE-TEST-FAKE-KEY-0000"


def _online_config(
    consent_accepted: bool, remember_key: bool = False, layer: str = "Base"
) -> dict:
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "online",
        "vworld_api_key": FAKE_VWORLD_KEY,
        "layer": layer,
        "consent_accepted": consent_accepted,
        "remember_key": remember_key,
    }
    return config


def _native_wmts_source_for_layer(qgs_path, layer: str) -> tuple[str, dict[str, str]]:
    """Return the native-WMTS datasource and parsed parameters for one selected VWorld layer.

    This intentionally parses the generated project artifact rather than inspecting the builder's
    own configuration.  It therefore catches a layer-specific fallback being flattened into the
    generic connection pair while a different VWorld layer still happens to look correct.
    """
    root = ET.parse(qgs_path).getroot()
    for map_layer in root.findall(".//maplayer"):
        if (map_layer.findtext("provider") or "").strip() != "wms":
            continue
        source = map_layer.findtext("datasource") or ""
        params = dict(parse_qsl(source, keep_blank_values=True))
        if params.get("layers") == layer:
            return source, params
    raise AssertionError(f"expected a native WMTS datasource for selected VWorld layer {layer!r}")


def _read_text_files_under(project_dir) -> dict:
    from pathlib import Path

    texts = {}
    for path in Path(project_dir).rglob("*"):
        if path.is_file() and path.suffix.lower() in {".qgs", ".json", ".md", ".log", ".txt"}:
            try:
                texts[str(path)] = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
    return texts


# --- AC-QPB-054 ----------------------------------------------------------------

def test_ac054_declined_consent_omits_key_and_online_layer(acceptance_api, tmp_path):
    config = _online_config(consent_accepted=False)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    texts = _read_text_files_under(result["project_dir"])
    for path, text in texts.items():
        assert FAKE_VWORLD_KEY not in text, f"key must not appear anywhere, found in {path}"


# --- AC-QPB-055 / AC-QPB-056 ---------------------------------------------------

def test_ac055_accepted_consent_embeds_key_only_in_qgs_online_layer_url(acceptance_api, tmp_path):
    config = _online_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    assert FAKE_VWORLD_KEY in qgs_text, (
        "consent accepted: the .qgs online-layer URL is the one permitted place for the key "
        "(FR-QPB-073)"
    )

    from pathlib import Path

    other_paths = [
        p
        for p in Path(result["project_dir"]).rglob("*")
        if p.is_file() and p.suffix.lower() != ".qgs"
    ]
    for path in other_paths:
        try:
            content = path.read_bytes()
        except OSError:
            continue
        assert FAKE_VWORLD_KEY.encode() not in content, (
            f"key must never appear outside the .qgs online-layer URL; found in {path}"
        )


# --- AC-QPB-057 ----------------------------------------------------------------

def test_ac057_manifest_contains_only_a_boolean_security_warning_flag(acceptance_api, tmp_path):
    config = _online_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    manifest_path = f"{result['project_dir']}/MANIFEST.json"
    manifest = json.loads(open(manifest_path, "r", encoding="utf-8").read())
    manifest_text = json.dumps(manifest)
    assert FAKE_VWORLD_KEY not in manifest_text

    flag_found = False
    for key, value in _flatten(manifest):
        if "security" in key.lower() or "credential" in key.lower() or "warning" in key.lower():
            if isinstance(value, bool):
                flag_found = True
    assert flag_found, (
        f"expected a boolean security-warning flag somewhere in MANIFEST.json (NFR-QPB-017); "
        f"manifest: {manifest}"
    )


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else k)
    else:
        yield prefix, obj


# --- AC-QPB-058 ----------------------------------------------------------------

def test_ac058_remember_key_uses_os_credential_store_not_plaintext(acceptance_api, tmp_path):
    config = _online_config(consent_accepted=True, remember_key=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    # NFR-QPB-018: "remember this key" must store the key in the OS credential store, not in a
    # plaintext application file. We can at least assert no plaintext application config/log
    # file (outside the one permitted .qgs online-layer URL) contains the key.
    from pathlib import Path

    for path in Path(result["project_dir"]).rglob("*"):
        if path.is_file() and path.suffix.lower() != ".qgs":
            try:
                content = path.read_bytes()
            except OSError:
                continue
            assert FAKE_VWORLD_KEY.encode() not in content


def test_key_not_remembered_by_default_across_sessions(acceptance_api, tmp_path):
    """NFR-QPB-018: without 'remember this key', retention is session-only.

    This cannot be fully verified without a real desktop-application session boundary; verified
    here as the contrapositive of the remembered case: the generated project (an on-disk
    artifact, not a live session) never itself becomes the retention mechanism.
    """
    config = _online_config(consent_accepted=True, remember_key=False)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")
    from pathlib import Path

    for path in Path(result["project_dir"]).rglob("*"):
        if path.is_file() and path.suffix.lower() != ".qgs":
            try:
                content = path.read_bytes()
            except OSError:
                continue
            assert FAKE_VWORLD_KEY.encode() not in content


# --- AC-QPB-017 / AC-QPB-068 -----------------------------------------------------

def test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully(
    acceptance_api, tmp_path
):
    """Offline-safe proxy for AC-QPB-017/AC-QPB-068: verifies only that the `.qgs` online layer
    is *configured* with a correctly shaped VWorld WMTS datasource. Does NOT assert
    `opens_without_repair_warning` (see the module docstring): with this test's necessarily-fake
    key, QGIS's native WMTS provider genuinely negotiates GetCapabilities against the live VWorld
    service, and a fake key correctly fails that negotiation -- there is no honest way to assert
    "opens successfully" here. That claim is verified only by
    `test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key` below."""
    config = _online_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    assert "vworld" in qgs_text.lower(), "expected a VWorld-sourced online layer in the project"

    # AC-QPB-017/AC-QPB-068 (FR-QPB-072 revised; Decision Log D-29): the online layer connects
    # through QGIS's native WMTS provider, pointed at the VWorld WMTS capabilities endpoint --
    # the `url=` datasource parameter must reference that capabilities document, not a manually
    # constructed per-tile GetTile URL. Note the `.qgs` file XML-escapes literal `&` characters
    # in element text as `&amp;`, so the datasource string appears as
    # `...&amp;url=https://api.vworld.kr/req/wmts/1.0.0/<key>/WMTSCapabilities.xml`.
    assert re.search(
        r"url=https://api\.vworld\.kr/req/wmts/1\.0\.0/[^&<]*WMTSCapabilities\.xml", qgs_text
    ), (
        "expected the online layer's datasource `url=` parameter to reference the VWorld WMTS "
        "capabilities endpoint (FR-QPB-072 revised; AC-QPB-068)"
    )

    # The configured/selected layer name ("Base" for this test's fixture config) must appear as
    # the WMTS datasource's `layers=` query parameter -- QGIS negotiates the actual tile requests
    # itself from the capabilities document -- not as a `/Base/` per-tile URL path segment (the
    # old, now-superseded shape).
    assert re.search(r"layers=Base(?:&|$|&amp;)", qgs_text), (
        "expected the selected VWorld layer name as the WMTS datasource's `layers=` parameter "
        "(FR-QPB-072 revised; AC-QPB-068)"
    )

    # AC-QPB-068 negative assertion: the datasource must not contain the superseded, manually
    # constructed per-tile XYZ shape -- neither a `type=xyz` provider marker nor a raw
    # `{z}/{y}/{x}`-style per-tile URL template (nor a literal, already-substituted `/Base/`
    # per-tile path segment, which is what that old template would have produced for this
    # layer).
    assert "type=xyz" not in qgs_text, (
        "the online layer must not be added as a `type=xyz` datasource -- QGIS's native WMTS "
        "provider is required instead (FR-QPB-072 revised; AC-QPB-068)"
    )
    assert not re.search(r"\{z\}|\{x\}|\{y\}", qgs_text), (
        "the online layer's datasource must not contain a raw per-tile XYZ URL template "
        "(FR-QPB-072 revised; AC-QPB-068)"
    )
    assert "/Base/" not in qgs_text, (
        "the online layer's datasource must not reference the layer as a `/Base/` per-tile URL "
        "path segment -- the superseded manually constructed GetTile shape (FR-QPB-072 revised; "
        "AC-QPB-068)"
    )

    # AC-QPB-017's "opens without a repair warning" claim is deliberately NOT checked here.
    # Under the D-29 QGIS-native-WMTS connection mechanism, `validate_project()` would have QGIS
    # perform a real GetCapabilities negotiation against the live VWorld endpoint using this
    # test's fake key (`ACCEPTANCE-TEST-FAKE-KEY-0000`). VWorld's real endpoint correctly rejects
    # that fake key with an OGC `ExceptionReport`, so QGIS correctly marks the layer invalid --
    # i.e. `opens_without_repair_warning` would genuinely and correctly be `False` here, which is
    # expected behavior for an invalid key, not a defect, but also not something this offline-safe
    # proxy should assert on or depend on a live network round-trip to observe. The only place
    # that genuinely verifies "opens without a repair warning" for a *valid* key is the
    # network-gated `test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key`
    # below.


def test_ac068_satellite_fallback_keeps_a_layer_specific_native_wmts_source(
    acceptance_api, tmp_path
):
    """Regression for the Satellite fallback source, with no live user credential.

    The build deliberately uses the fixture's fake key and does not call ``validate_project()``.
    The assertion is solely about the generated native-WMTS datasource: it must remain a VWorld
    capabilities connection for ``Satellite`` while using VWorld's native Satellite constants,
    rather than flattening the fallback to the rejected generic ``EPSG:900913`` and
    ``image/png`` values.
    """
    result = acceptance_api.build_project(
        _online_config(consent_accepted=True, layer="Satellite"), str(tmp_path / "satellite")
    )
    assert result["success"], result.get("error_message")

    source, params = _native_wmts_source_for_layer(result["qgs_path"], "Satellite")
    assert params["tileMatrixSet"] == "GoogleMapsCompatible", source
    assert params["crs"] == "EPSG:3857", source
    assert params["layers"] == "Satellite", source
    assert params.get("styles", "").strip(), (
        "AC-QPB-068: the Satellite datasource must include a non-empty WMTS style parameter; "
        f"source: {source!r}"
    )
    assert params["format"] == "image/jpeg", (
        "AC-QPB-068: Satellite must retain its layer-specific JPEG format rather than using the "
        f"generic fallback format. Source: {source!r}"
    )
    assert params["url"] == (
        "https://api.vworld.kr/req/wmts/1.0.0/"
        f"{FAKE_VWORLD_KEY}/WMTSCapabilities.xml"
    ), source
    assert "type=xyz" not in source.lower(), source
    assert not re.search(r"\{z\}|\{x\}|\{y\}", source)
    assert "/Satellite/" not in source, (
        "AC-QPB-068: Satellite must be selected by the native WMTS `layers` parameter, never "
        "by a per-tile URL path. "
        f"Source: {source!r}"
    )
    assert "EPSG:900913" not in source, (
        "Satellite must explicitly reject the generic EPSG:900913 fallback. "
        f"Source: {source!r}"
    )
    assert "image/png" not in source.lower(), (
        "Satellite must explicitly reject the generic image/png fallback. "
        f"Source: {source!r}"
    )


@pytest.mark.network
def test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key(
    acceptance_api, tmp_path
):
    """Live QGIS/PyQGIS network check for AC-QPB-017's selected Satellite layer.

    Run with ``--run-network`` and a real VWorld key exported as ``QPB_TEST_VWORLD_API_KEY``.
    It verifies live WMTS negotiation and provider validity in the local QGIS validation path.
    It does *not* run QField or an iPhone, so it is not evidence for D-97's AC-QPB-146 iPhone
    rendering/no-repair-warning gate; that result remains the manual ``device`` test.
    """
    import os

    real_key = os.environ.get("QPB_TEST_VWORLD_API_KEY")
    if not real_key:
        pytest.skip("QPB_TEST_VWORLD_API_KEY not set")
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "online",
        "vworld_api_key": real_key,
        "layer": "Satellite",
        "consent_accepted": True,
        "remember_key": False,
    }
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    report = acceptance_api.validate_project(result["project_dir"])
    assert report["opens_without_repair_warning"] is True, report["issues"]
    assert report["missing_layer_warning"] is False, report["issues"]


# --- AC-QPB-051 (online half) --------------------------------------------------

def test_ac051_molit_vworld_attribution_present_online(acceptance_api, tmp_path):
    config = _online_config(consent_accepted=True)
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")

    qgs_text = open(result["qgs_path"], "r", encoding="utf-8").read()
    manifest = json.loads(open(f"{result['project_dir']}/MANIFEST.json", "r", encoding="utf-8").read())
    manifest_text = json.dumps(manifest)

    for text, label in [(qgs_text, "qgs"), (manifest_text, "manifest")]:
        assert "vworld" in text.lower(), f"expected VWorld attribution text in {label}"
        assert (
            "국토교통부" in text
            or "ministry of land" in text.lower()
            or "molit" in text.lower()
        ), f"expected MOLIT attribution reference in {label}"
