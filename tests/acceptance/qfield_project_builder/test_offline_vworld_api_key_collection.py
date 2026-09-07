"""Bug 1 (Category A conformance defect; test-designer conformance-gap round, 2026-08-27):
offline basemap generation never collects the VWorld API key in the wizard, and a missing/
unverifiable key currently surfaces as a raw Python dict-key repr, not an actionable error.

`E-QPB-003` ("Invalid or unverifiable VWorld API key must be surfaced as an actionable error
without blocking the rest of project setup unnecessarily") and `FR-QPB-078`/`NFR-QPB-058` (the
VWorld key "may be used only during tile retrieval" for offline MBTiles generation -- which
presupposes the key is actually collected in the first place) are already-approved MVP
requirements (`specs/qfield-project-builder.md`, Sections 11/15). This round independently
re-verified the reported root cause by direct code reading (not by trusting the bug report handed
to this round at face value):

- `qfield_builder/ui/wizard.py`'s `ConnectivityBasemapPage.__init__` places `self.api_key_edit`
  (the VWorld key input, line 662) only inside `self.online_group`
  (`online_layout.addRow("VWorld API 키:", self.api_key_edit)`, line 710), and
  `self.online_group`'s visibility is tied solely to `self.online_radio`
  (`self.online_radio.toggled.connect(self.online_group.setVisible)`, line 768) -- confirmed the
  key input is never shown for offline mode, and `ConnectivityBasemapPage.offline_config()`
  (line 981) returns only `{"bbox", "min_zoom", "max_zoom"}`, never `vworld_api_key`.
- `ReviewAndBuildPage._collect_config()` (line 1439) only adds `"vworld_api_key"` to
  `config["basemap"]` when `mode == "online"` (line 1450-1462); for `"offline"` (line 1471-1473)
  it calls `basemap_page.offline_config()`, which -- confirmed above -- never includes it.
- `qfield_builder/vworld_tiles.py::resolve_tile_fetcher()` (line 114-122) does a raw
  `basemap_config["vworld_api_key"]` dict index with no `.get()`/fallback whenever `tile_source`
  is not an injected `{"fake": ...}` test double -- confirmed this raises `KeyError` while
  evaluating `make_real_vworld_tile_fetcher`'s `api_key=...` *argument*, strictly before that
  function's returned closure (and therefore any network I/O) ever runs. This is what makes the
  negative test below fully offline/deterministic.
- `qfield_builder/build.py::build_project()` (line 505-507) *does* have an outermost
  `except Exception as exc: ... return _empty_result(error_code="unexpected_error",
  error_message=str(exc))`, so this `KeyError` is actually caught -- `build_project()` never
  raises an uncaught exception to its caller. But `str(KeyError("vworld_api_key"))` is the literal
  text `"'vworld_api_key'"`, a bare Python dict-key repr, not a clear, non-technical, actionable
  message -- and that text is exactly what reaches the wizard's own `result_label`
  (`f"생성 실패: {result.get('error_message') or result.get('error_code')}"`, wizard.py:1685),
  matching the stakeholder's own real screenshot ("생성 실패: 'vworld_api_key'") verbatim. **The
  defect is therefore a message-quality defect against E-QPB-003's "actionable error" wording, not
  an uncaught-exception-propagation defect** -- `build_project()` already never crashes on this
  input.

**Suggested-but-not-mandated implementation direction** (an observation for whichever
`implementer` round picks this up, not asserted by any test below): every other anticipated
`build_project()` failure mode already has its own dedicated `BuildError` subclass with a specific
`error_code` and a purpose-written message (`qfield_builder/errors.py`:
`OfflineSizeExceededError`, `ProviderAuthError`, `ProviderQuotaError`, ...). The most natural fix
mirrors that existing pattern -- a dedicated exception raised proactively (e.g. before
`resolve_tile_fetcher()` is ever called) when offline mode has no `vworld_api_key`, rather than
relying on the generic `except Exception` catch-all this round's negative test currently exercises
-- but the tests below deliberately assert only on message quality and non-crash behavior, not on
any specific `error_code` value or exception class, so as not to invent an implementation detail
this specification does not itself dictate.

**What this file does *not* cover, and why** (see
`../qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md` for
the full analysis): whether the VWorld key input control is actually visible/reachable when
offline mode is selected in a real running wizard (Bug 1(a)), and whether
`ReviewAndBuildPage._collect_config()` actually wires a typed-in key into `config["basemap"]`
once the wizard is fixed (Bug 1(b)). Both require directly constructing and driving real PySide6
`QWizardPage` objects (`ConnectivityBasemapPage`/`ReviewAndBuildPage`) -- exactly the class of
"PySide6 wizard's own code structure" testing `HARNESS_CONTRACT.md`'s own "what these tests
deliberately do not invent" section already excludes from this black-box,
`qfield_builder.acceptance_api`-mediated harness, and which this suite's own established
precedent (`../qfield_project_builder_credential_storage_mechanism.traceability.md`'s
"Scope-boundary finding") treats as the `implementer` role's `tests/unit/` mandate, not
`test-designer`'s `tests/acceptance/`-only file-scope boundary. The traceability file linked above
specifies the exact contract a `tests/unit/test_wizard.py`-level test must satisfy for both.
"""
from __future__ import annotations

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis

SMALL_BBOX = {"min_lon": 127.000, "min_lat": 37.000, "max_lon": 127.010, "max_lat": 37.010}

# The literal text of `str(KeyError("vworld_api_key"))` -- exactly the raw defect text confirmed
# in the stakeholder's own screenshot ("생성 실패: 'vworld_api_key'").
_RAW_KEYERROR_TEXT = "'vworld_api_key'"

_TECHNICAL_JARGON = [
    "keyerror",
    "traceback",
    "stack trace",
    "nonetype",
    "attributeerror",
    "exception",
]


def test_offline_missing_vworld_api_key_fails_with_actionable_message_not_raw_keyerror(
    acceptance_api, tmp_path
):
    """E-QPB-003/FR-QPB-078/NFR-QPB-058: an offline-mode build whose `config["basemap"]` has no
    `vworld_api_key` at all -- simulating today's actual wizard output (see module docstring) and
    guarding against a future regression reintroducing the same gap once the wizard is fixed --
    must fail with `success: False` and a clear, non-technical, actionable `error_message`, never
    the bare `KeyError` repr the stakeholder's own screenshot showed, and never an uncaught
    exception out of `build_project()` itself.

    `tile_source` is deliberately left unset (defaults to `"vworld"`, the real-downloader code
    path in `vworld_tiles.resolve_tile_fetcher()`) -- a `{"fake": {...}}` tile_source would never
    read `basemap_config["vworld_api_key"]` at all and would not reproduce this defect. This is
    still fully offline/deterministic and needs no live network access or a real API key: per the
    module docstring, the `KeyError` this test exercises happens while constructing the tile-fetch
    closure, strictly before any network I/O is attempted.
    """
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        # Deliberately no "vworld_api_key" key at all -- see module docstring.
        "layer": "Base",
        "bbox": SMALL_BBOX,
        "min_zoom": 10,
        "max_zoom": 11,
    }
    out_dir = tmp_path / "out"
    try:
        result = acceptance_api.build_project(config, str(out_dir))
    except Exception as exc:  # noqa: BLE001 - this is exactly the failure mode under test
        pytest.fail(
            "E-QPB-003: a missing/unverifiable VWorld API key must never raise an uncaught "
            f"exception out of build_project(), got: {exc!r}"
        )

    assert result["success"] is False
    assert result.get("error_code"), "expected a structured error_code for this failure"

    message = result.get("error_message") or ""
    assert message.strip(), "E-QPB-003: expected a non-blank, actionable error message"
    lowered = message.lower().strip()

    assert lowered != _RAW_KEYERROR_TEXT, (
        "error_message must not be the bare KeyError repr shown to the stakeholder "
        f"(생성 실패: {_RAW_KEYERROR_TEXT}), got: {message!r}"
    )
    assert not any(term in lowered for term in _TECHNICAL_JARGON), (
        f"E-QPB-003: error message must be non-technical/actionable, got: {message!r}"
    )
    assert not (out_dir.exists() and any(out_dir.iterdir())), (
        "E-QPB-009: no partially generated project may remain at the output path"
    )


def test_offline_with_vworld_api_key_present_does_not_hit_the_missing_key_failure_path(
    acceptance_api, tmp_path
):
    """Companion positive-path check: once `vworld_api_key` IS present in `config["basemap"]` for
    offline mode -- the shape a fixed wizard must actually produce -- generation must not fail
    with the missing-key symptom this round's negative test above guards against. This does not
    duplicate `test_basemap_offline.py`'s own detailed successful-generation coverage
    (`test_ac018_ac019_mbtiles_coverage_and_metadata_match_request` etc.); it exists only to pin
    the *specific* failure mode this round is about as a companion to the negative test above.
    """
    config = make_base_config("simple_inventory")
    config["basemap"] = {
        "mode": "offline",
        "vworld_api_key": "ACCEPTANCE-TEST-FAKE-KEY-BUG1-COMPANION",
        "layer": "Base",
        "bbox": SMALL_BBOX,
        "min_zoom": 10,
        "max_zoom": 11,
        "tile_source": {"fake": {"mode": "success", "tile_bytes": 4000}},
    }
    result = acceptance_api.build_project(config, str(tmp_path / "out"))
    assert result["success"], result.get("error_message")
