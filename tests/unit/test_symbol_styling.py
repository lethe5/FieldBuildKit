"""Unit tests for qfield_builder.symbol_styling (FR-QPB-120/FR-QPB-121, FR-QPB-011(d),
NFR-QPB-080; Decision Log D-61/D-65), including the live preview-SVG fetch during search
(FR-QPB-011(d)(ii), NFR-QPB-080 clauses (5)-(8), AC-QPB-117; Decision Log D-76).

Covers the parts of this module the acceptance suite's `tests/acceptance/qfield_project_builder/
test_symbol_styling.py`/`test_tabler_icon_preview_fetch.py` do not reach directly:

- The bundled icon-name index itself (real, non-trivial, sorted, no duplicates).
- `search_bundled_tabler_icon_names`'s pure filtering logic (also exercised, black-box, by the
  acceptance suite via `qfield_builder.acceptance_api`, but covered here with implementation-level
  detail/edge cases).
- `is_valid_icon_name_shape`'s defensive validation.
- `resolve_svg_fetch`'s fake-vs-real dispatch (mirrors the acceptance suite's own
  `symbol_styling.tabler_svg_fetch.fake` config coverage, but at the function level).
- `fetch_tabler_icon_svg_real`'s actual HTTP behavior: a compliant, identifying `User-Agent`
  header and no automatic retry on failure (NFR-QPB-080(1)/(2)) -- the acceptance suite's own
  `test_ac102_...` test explicitly declines to cover this "internal HTTP-client construction"
  half of AC-QPB-102 (see that file's module docstring and HARNESS_CONTRACT.md's "what these
  tests deliberately do not invent" list), routing it to this implementer's own unit-test mandate
  instead -- this file is that coverage.
- `fetch_tabler_icon_preview_svgs`'s (HARNESS_CONTRACT.md function 20) fake-double dispatch, at
  implementation-level detail beyond what the acceptance suite already exercises.
- `dispatch_preview_fetches_real`'s real, production dispatch mechanism -- in particular the two
  routed `tests/unit/` contract rows the acceptance suite's own traceability file explicitly
  cannot reach from a black-box test: NFR-QPB-080(7) (real bounded concurrency of in-flight
  requests) and NFR-QPB-080(5) (the same compliant `User-Agent` header the existing
  selection-fetch request already carries, now also for this second fetch trigger). The
  debounce (NFR-QPB-080(6)) and real, on-widget graceful-degradation (NFR-QPB-080(8)/AC-QPB-117)
  rows are covered in `test_wizard.py` instead, against the real `SymbolStylingPage` widget those
  two rows are actually about.
"""
from __future__ import annotations

import threading
import time
import urllib.error

import pytest

from qfield_builder import symbol_styling

# --- Bundled icon-name index -------------------------------------------------------------------


def test_bundled_icon_names_is_real_non_trivial_sorted_and_deduplicated():
    names = symbol_styling._bundled_icon_names()
    assert len(names) > 1000
    assert list(names) == sorted(names)
    assert len(names) == len(set(names))


def test_bundled_icon_names_contains_icons_the_acceptance_suite_relies_on():
    names = set(symbol_styling._bundled_icon_names())
    assert {"map-pin", "leaf", "home"} <= names


# --- search_bundled_tabler_icon_names --------------------------------------------------------


def test_search_returns_empty_matches_for_blank_query():
    result = symbol_styling.search_bundled_tabler_icon_names("")
    assert result["matches"] == []
    assert result["total_bundled_names"] > 1000

    result_whitespace = symbol_styling.search_bundled_tabler_icon_names("   ")
    assert result_whitespace["matches"] == []


def test_search_is_case_insensitive_substring_match():
    result = symbol_styling.search_bundled_tabler_icon_names("LEAF")
    assert "leaf" in result["matches"]


def test_search_matches_a_substring_not_only_a_prefix():
    # "map-pin" contains "pin" but does not start with it.
    result = symbol_styling.search_bundled_tabler_icon_names("pin")
    assert "map-pin" in result["matches"]


def test_search_returns_no_matches_for_a_nonexistent_query():
    result = symbol_styling.search_bundled_tabler_icon_names("zzz_not_a_real_icon_zzz")
    assert result["matches"] == []


def test_search_never_performs_network_io(monkeypatch):
    def _fail(*_a, **_k):
        raise AssertionError("search_bundled_tabler_icon_names must never touch the network")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fail)
    result = symbol_styling.search_bundled_tabler_icon_names("home")
    assert result["matches"]


# --- is_valid_icon_name_shape ------------------------------------------------------------------


@pytest.mark.parametrize("name", ["map-pin", "leaf", "home", "a-b-2", "abacus-off"])
def test_is_valid_icon_name_shape_accepts_real_bundled_names(name):
    assert symbol_styling.is_valid_icon_name_shape(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        None,
        "../../etc/passwd",
        "/etc/passwd",
        "Map-Pin",
        "map_pin",
        "map pin",
        "map--pin",
        "-map-pin",
        "map-pin-",
        "map/pin",
    ],
)
def test_is_valid_icon_name_shape_rejects_malformed_or_hostile_input(name):
    assert not symbol_styling.is_valid_icon_name_shape(name)


# --- resolve_svg_fetch: fake-vs-real dispatch ------------------------------------------------


def test_resolve_svg_fetch_uses_the_fake_double_when_present(monkeypatch):
    def _fail_real_fetch(*_a, **_k):
        raise AssertionError("resolve_svg_fetch must not call the real fetch when a fake is given")

    monkeypatch.setattr(symbol_styling, "fetch_tabler_icon_svg_real", _fail_real_fetch)

    config = {"tabler_svg_fetch": {"fake": {"mode": "success", "svg_content": "<svg></svg>"}}}
    result = symbol_styling.resolve_svg_fetch(config, "map-pin")
    assert result == {"success": True, "svg_content": "<svg></svg>", "error": None}


@pytest.mark.parametrize("failure_mode", ["network_error", "http_error", "timeout"])
def test_resolve_svg_fetch_fake_double_reports_every_documented_failure_mode(failure_mode):
    config = {"tabler_svg_fetch": {"fake": {"mode": failure_mode, "svg_content": ""}}}
    result = symbol_styling.resolve_svg_fetch(config, "map-pin")
    assert result["success"] is False
    assert result["svg_content"] is None
    assert result["error"] == failure_mode


def test_resolve_svg_fetch_fake_double_rejects_an_unknown_mode():
    config = {"tabler_svg_fetch": {"fake": {"mode": "not_a_real_mode"}}}
    with pytest.raises(ValueError):
        symbol_styling.resolve_svg_fetch(config, "map-pin")


def test_resolve_svg_fetch_calls_the_real_fetch_when_no_fake_is_configured(monkeypatch):
    calls = []

    def _fake_real_fetch(icon_name, timeout=symbol_styling._DEFAULT_FETCH_TIMEOUT_SECONDS):
        calls.append(icon_name)
        return {"success": True, "svg_content": "<svg></svg>", "error": None}

    monkeypatch.setattr(symbol_styling, "fetch_tabler_icon_svg_real", _fake_real_fetch)

    result = symbol_styling.resolve_svg_fetch({}, "leaf")
    assert calls == ["leaf"]
    assert result["success"] is True


# --- fetch_tabler_icon_svg_real: NFR-QPB-080(1)/(2) (User-Agent, no automatic retry) ----------
#
# AC-QPB-102's own module docstring in the acceptance suite explicitly declines to cover this
# "internal HTTP-client construction" half -- routed here instead (see this file's own docstring).


class _FakeHTTPResponse:
    def __init__(self, status: int, body: bytes, content_type: str = "image/svg+xml"):
        self.status = status
        self._body = body
        self.headers = {"Content-Type": content_type}

    def getcode(self):
        return self.status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_fetch_tabler_icon_svg_real_sends_a_compliant_identifying_user_agent_header(monkeypatch):
    captured_requests = []

    def _fake_urlopen(request, timeout=None, context=None):
        captured_requests.append(request)
        return _FakeHTTPResponse(200, b"<svg></svg>")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.fetch_tabler_icon_svg_real("map-pin")

    assert result == {"success": True, "svg_content": "<svg></svg>", "error": None}
    assert len(captured_requests) == 1
    user_agent = captured_requests[0].get_header("User-agent")
    assert user_agent, "expected a User-Agent header to be sent"
    # NFR-QPB-080(1): "a compliant, identifying User-Agent header" -- not a generic/default HTTP
    # client string (Python's urllib default is literally "Python-urllib/<version>").
    assert "python-urllib" not in user_agent.lower()
    assert user_agent == symbol_styling.TABLER_USER_AGENT


def test_fetch_tabler_icon_svg_real_makes_exactly_one_attempt_on_failure_no_automatic_retry(
    monkeypatch,
):
    call_count = 0

    def _fake_urlopen(request, timeout=None, context=None):
        nonlocal call_count
        call_count += 1
        raise urllib.error.URLError("simulated network failure")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.fetch_tabler_icon_svg_real("map-pin")

    # NFR-QPB-080(2): "must not retry automatically in an unbounded loop on failure -- one
    # attempt per user selection."
    assert call_count == 1
    assert result["success"] is False
    assert result["error"] == "network_error"


def test_fetch_tabler_icon_svg_real_reports_a_non_200_http_status_as_http_error(monkeypatch):
    def _fake_urlopen(request, timeout=None, context=None):
        raise urllib.error.HTTPError(
            "https://example.invalid/x.svg", 404, "Not Found", None, None
        )

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.fetch_tabler_icon_svg_real("map-pin")
    assert result["success"] is False
    assert result["error"] == "http_error:404"


def test_fetch_tabler_icon_svg_real_rejects_a_malformed_icon_name_without_any_network_call(
    monkeypatch,
):
    def _fail(*_a, **_k):
        raise AssertionError("must not attempt a network call for an invalid icon name")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fail)

    result = symbol_styling.fetch_tabler_icon_svg_real("../../etc/passwd")
    assert result == {"success": False, "svg_content": None, "error": "invalid_icon_name"}


# --- fetch_tabler_icon_svg (HARNESS_CONTRACT.md function 13, test-only reference impl) --------


def test_fetch_tabler_icon_svg_returns_the_response_shape_for_a_successful_fetch(monkeypatch):
    def _fake_urlopen(request, timeout=None, context=None):
        return _FakeHTTPResponse(200, b"<svg>content</svg>", content_type="image/svg+xml")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.fetch_tabler_icon_svg("home")
    assert result["http_status"] == 200
    assert result["content_type"] == "image/svg+xml"
    assert result["svg_text"] == "<svg>content</svg>"


def test_fetch_tabler_icon_svg_reports_network_level_failure_as_status_zero(monkeypatch):
    def _fake_urlopen(request, timeout=None, context=None):
        raise urllib.error.URLError("simulated failure")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.fetch_tabler_icon_svg("home")
    assert result == {"http_status": 0, "content_type": None, "svg_text": None}


# --- fetch_tabler_icon_preview_svgs (HARNESS_CONTRACT.md function 20; Decision Log D-76) -------
#
# The full FR-QPB-011(d)(ii)/AC-QPB-117 contract is already exercised, black-box, by
# tests/acceptance/qfield_project_builder/test_tabler_icon_preview_fetch.py via
# qfield_builder.acceptance_api. These add implementation-level detail that suite does not cover.


def test_fetch_tabler_icon_preview_svgs_uses_per_name_override_over_the_shared_default():
    fake = {
        "fake": {
            "default": {"mode": "success", "svg_content": "<svg>default</svg>"},
            "overrides": {"leaf": {"mode": "success", "svg_content": "<svg>leaf</svg>"}},
        }
    }
    result = symbol_styling.fetch_tabler_icon_preview_svgs(["map-pin", "leaf"], fake)
    assert result["previews"]["map-pin"]["svg_content"] == "<svg>default</svg>"
    assert result["previews"]["leaf"]["svg_content"] == "<svg>leaf</svg>"


def test_fetch_tabler_icon_preview_svgs_preserves_the_given_names_and_their_order():
    fake = {"fake": {"default": {"mode": "success", "svg_content": "<svg></svg>"}}}
    names = ["home", "leaf", "map-pin"]
    result = symbol_styling.fetch_tabler_icon_preview_svgs(names, fake)
    assert result["requested_names"] == names


def test_fetch_tabler_icon_preview_svgs_empty_name_list_returns_no_previews():
    fake = {"fake": {"default": {"mode": "success", "svg_content": "<svg></svg>"}}}
    result = symbol_styling.fetch_tabler_icon_preview_svgs([], fake)
    assert result == {"requested_names": [], "previews": {}}


# --- dispatch_preview_fetches_real: routed tests/unit/ contract rows ---------------------------
#
# NFR-QPB-080(7) (real bounded concurrency) and NFR-QPB-080(5) (User-Agent parity) -- see
# ../acceptance/qfield_project_builder_tabler_icon_preview_fetch.traceability.md's routed
# `tests/unit/` contract table, rows 2 and 3.


def test_dispatch_preview_fetches_real_returns_empty_result_for_no_names():
    assert symbol_styling.dispatch_preview_fetches_real([]) == {
        "requested_names": [],
        "previews": {},
    }


def test_dispatch_preview_fetches_real_bounds_concurrency_below_firing_all_names_at_once():
    """NFR-QPB-080(7): 'concurrency for in-flight preview fetches must be bounded to a small,
    reasonable number at any one time -- never one unbounded, simultaneous request fired per
    every currently visible result at once.' Drives the real production dispatch mechanism with
    a realistic concurrency-observable double: a fake per-name fetch function that records the
    maximum number of simultaneously in-flight calls via a counter guarded by a lock."""
    names = [f"icon-{i}" for i in range(20)]
    lock = threading.Lock()
    state = {"current": 0, "max_seen": 0}

    def _slow_fetch_one(name: str) -> dict:
        with lock:
            state["current"] += 1
            state["max_seen"] = max(state["max_seen"], state["current"])
        time.sleep(0.05)
        with lock:
            state["current"] -= 1
        return {"success": True, "svg_content": "<svg></svg>", "error": None}

    result = symbol_styling.dispatch_preview_fetches_real(names, fetch_one=_slow_fetch_one)

    assert set(result["previews"].keys()) == set(names)
    assert all(p["success"] for p in result["previews"].values())
    assert 0 < state["max_seen"] <= symbol_styling.PREVIEW_FETCH_MAX_CONCURRENCY
    assert state["max_seen"] < len(names), (
        "must never fire one simultaneous request per every currently visible result at once -- "
        f"observed {state['max_seen']} concurrent in-flight calls out of {len(names)} names"
    )


def test_preview_dispatch_delivers_fast_icon_before_slow_request_finishes():
    from threading import Event

    first_delivered = Event()

    def fetch_one(name):
        if name == "leaf":
            assert first_delivered.wait(2), "fast preview was held until the entire batch finished"
        return {"success": True, "svg_content": "<svg/>", "error": None}

    result = symbol_styling.dispatch_preview_fetches_real(
        ["leaf", "map-pin"], fetch_one=fetch_one,
        on_result=lambda name, preview: first_delivered.set() if name == "map-pin" else None,
    )
    assert all(preview["success"] for preview in result["previews"].values())


def test_https_context_has_verified_trust_without_developer_ca_files(monkeypatch, tmp_path):
    import ssl

    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path / "missing-certs"))
    symbol_styling._https_context.cache_clear()
    try:
        context = symbol_styling._https_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        assert context.cert_store_stats()["x509_ca"] > 0
    finally:
        symbol_styling._https_context.cache_clear()


def test_dispatch_preview_fetches_real_one_name_raising_never_blocks_or_omits_its_siblings():
    """NFR-QPB-080(8)/AC-QPB-117, at the real dispatch mechanism's own level: one name's fetch
    raising unexpectedly must never crash the batch or drop any other name's own result."""

    def _fetch_one(name: str) -> dict:
        if name == "leaf":
            raise RuntimeError("simulated unexpected failure")
        return {"success": True, "svg_content": "<svg></svg>", "error": None}

    result = symbol_styling.dispatch_preview_fetches_real(
        ["map-pin", "leaf", "home"], fetch_one=_fetch_one
    )

    assert result["previews"]["map-pin"]["success"] is True
    assert result["previews"]["home"]["success"] is True
    leaf = result["previews"]["leaf"]
    assert leaf["success"] is False
    assert leaf["svg_content"] is None
    assert "unexpected_error" in leaf["error"]


def test_dispatch_preview_fetches_real_uses_the_same_compliant_user_agent_as_the_selection_fetch(
    monkeypatch,
):
    """NFR-QPB-080(5): 'every live search-preview-fetch request permitted by FR-QPB-011(d)(ii)
    must carry the same compliant, identifying User-Agent header clause (1) above already
    requires of the selection-fetch request.' `dispatch_preview_fetches_real`'s default
    `fetch_one` is `fetch_tabler_icon_svg_real` -- this confirms that parity holds when actually
    invoked through the real (not-fake) preview-fetch dispatch code path, not merely by
    construction."""
    captured_requests = []

    def _fake_urlopen(request, timeout=None, context=None):
        captured_requests.append(request)
        return _FakeHTTPResponse(200, b"<svg></svg>")

    monkeypatch.setattr(symbol_styling.urllib.request, "urlopen", _fake_urlopen)

    result = symbol_styling.dispatch_preview_fetches_real(["map-pin", "leaf"])

    assert len(captured_requests) == 2
    for request in captured_requests:
        user_agent = request.get_header("User-agent")
        assert user_agent == symbol_styling.TABLER_USER_AGENT
    assert all(p["success"] for p in result["previews"].values())
