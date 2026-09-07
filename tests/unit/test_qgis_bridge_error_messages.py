"""Regression tests for NFR-QPB-070 (Decision Log D-28): a real QGIS-worker-subprocess failure
(timeout, launch failure, missing result, corrupted result) must surface a Korean, not English,
message all the way to the wizard's result label.

A prior implementation round translated `qfield_builder.qgis_worker`'s own fallback string
(`outcome.get("error") or "<Korean fallback>"`) but left the four messages actually constructed by
`qfield_builder.qgis_bridge.run_job` in English. Since `run_job` never returns a falsy `"error"` on
any of its failure branches, that Korean fallback was unreachable dead code and the raw English
`run_job` text reached the user verbatim. These tests exercise the whole chain --
`qgis_bridge.run_job` -> `qgis_worker.build_qgis_project` -> `build.build_project` ->
`wizard.ReviewAndBuildPage._on_build_finished` -- to confirm the fix actually changes what reaches
the user, not just what is technically closer to the source.

A second implementation round translated all four hardcoded sentences to Korean, but two of the
four branches (`OSError` on launch; `OSError`/`json.JSONDecodeError` on reading the result file)
still appended the raw underlying exception's own `str(exc)` after the Korean sentence via
f-string interpolation -- itself untranslated, OS/library-generated English text. That round's
`_contains_only_ascii_letters_words()` only matched a fixed list of the four *original* English
sentences, so it kept passing even though the leaked exception text (which differs word-for-word
from those four sentences) was still present. `_contains_only_ascii_letters_words()` below now
detects any unapproved run of ASCII letters instead, so it would have caught that leak too; the
raw exception text now goes into the (never user-displayed) `"traceback"` field instead of
`"error"`.
"""
from __future__ import annotations

import re
import subprocess

import pytest
from PySide6.QtWidgets import QApplication

from qfield_builder import build as build_module
from qfield_builder import qgis_bridge
from qfield_builder import qgis_worker as qgis_worker_module
from qfield_builder import runtime as runtime_module


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _contains_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


_ASCII_WORD_RE = re.compile(r"[A-Za-z]{2,}")

# Proper names that are legitimately allowed to appear verbatim in an otherwise-Korean
# user-facing message (they have no Korean equivalent and are not English prose).
_ALLOWED_ASCII_WORDS = {"QGIS", "PyQGIS"}


def _contains_only_ascii_letters_words(text: str) -> bool:
    """True if `text` contains any run of 2+ consecutive ASCII letters that is not an approved
    carve-out (a proper name such as "QGIS"/"PyQGIS", or a file extension immediately following a
    dot, e.g. ".gpkg"/".qgs").

    This is a *general* leak detector, not a fixed list of the four original hardcoded English
    sentences. A narrower, fixed-fragment version of this check previously kept passing even
    though a real exception's raw `str(exc)` (e.g. an `OSError`'s or `json.JSONDecodeError`'s own
    message) was still being interpolated into the Korean "error" string, because that leaked
    text differed word-for-word from the four original hardcoded English sentences it matched
    against. Matching on *any* unapproved run of ASCII letters instead of specific phrases means
    an arbitrary interpolated exception message is caught too, not just a regression back to one
    of the four known original strings.
    """
    for match in _ASCII_WORD_RE.finditer(text):
        word = match.group(0)
        if word in _ALLOWED_ASCII_WORDS:
            continue
        start = match.start()
        if start > 0 and text[start - 1] == ".":
            # A file extension carve-out (e.g. ".gpkg", ".qgs"), not English prose.
            continue
        return True
    return False


class _FakeBridgeTarget:
    kind = "python_interpreter"
    executable = "/does/not/matter/python"
    env: dict = {}
    install_path = "/does/not/matter"
    qgis_version = None


@pytest.fixture(autouse=True)
def _fake_bridge_target(monkeypatch):
    """Every test in this module simulates a subprocess-level failure, so `run_job` must believe
    a bridge target was found at all (otherwise it short-circuits to `None` before ever reaching
    the code under test)."""
    monkeypatch.setattr(qgis_bridge, "get_bridge_target", lambda **_kw: _FakeBridgeTarget())


# ---------------------------------------------------------------------------------------------
# 1. qgis_bridge.run_job's four failure branches: the "error" string itself must be Korean.
# ---------------------------------------------------------------------------------------------


def test_run_job_timeout_error_message_is_korean(monkeypatch):
    def _raise_timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["fake"], timeout=1)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    outcome = qgis_bridge.run_job("some.module", "some_func", {})

    assert outcome["ok"] is False
    assert _contains_hangul(outcome["error"])
    assert not _contains_only_ascii_letters_words(outcome["error"])


def test_run_job_launch_failure_error_message_is_korean(monkeypatch):
    def _raise_oserror(*_args, **_kwargs):
        raise OSError("no such file or directory")

    monkeypatch.setattr(subprocess, "run", _raise_oserror)

    outcome = qgis_bridge.run_job("some.module", "some_func", {})

    assert outcome["ok"] is False
    assert _contains_hangul(outcome["error"])
    assert not _contains_only_ascii_letters_words(outcome["error"])


def test_run_job_missing_result_error_message_is_korean(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(qgis_bridge.os.path, "exists", lambda _path: False)

    outcome = qgis_bridge.run_job("some.module", "some_func", {})

    assert outcome["ok"] is False
    assert _contains_hangul(outcome["error"])
    assert not _contains_only_ascii_letters_words(outcome["error"])


def test_run_job_unreadable_result_error_message_is_korean(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    # Let the missing-result branch's `os.path.exists` check pass (claiming the result file is
    # there) even though no such file was actually written -- the subsequent real `open()` of that
    # nonexistent path then genuinely raises `OSError`, exercising the same except-branch a real
    # unreadable/corrupted result would.
    monkeypatch.setattr(qgis_bridge.os.path, "exists", lambda _path: True)

    outcome = qgis_bridge.run_job("some.module", "some_func", {})

    assert outcome["ok"] is False
    assert _contains_hangul(outcome["error"])
    assert not _contains_only_ascii_letters_words(outcome["error"])


# ---------------------------------------------------------------------------------------------
# 2. qgis_worker.build_qgis_project must propagate run_job's (now Korean) message verbatim, not
#    the unreachable Korean fallback -- proving the fallback is no longer masking anything and
#    the actual bridge failure text is what the caller receives.
# ---------------------------------------------------------------------------------------------


def test_build_qgis_project_propagates_run_jobs_actual_korean_message(monkeypatch):
    def _raise_import_error(**_kwargs):
        raise ImportError("no PyQGIS here")

    monkeypatch.setattr(
        qgis_worker_module, "_build_qgis_project_pyqgis", _raise_import_error
    )
    korean_message = "QGIS 작업 프로세스가 제한 시간 내에 응답하지 않았습니다."
    monkeypatch.setattr(
        qgis_bridge, "run_job", lambda *_a, **_k: {"ok": False, "error": korean_message}
    )

    with pytest.raises(RuntimeError) as excinfo:
        qgis_worker_module.build_qgis_project(
            gpkg_path="/nonexistent.gpkg",
            qgs_path="/nonexistent.qgs",
            survey_type="simple_inventory",
            project_crs="EPSG:5186",
            basemap_config=None,
            mbtiles_relative_path=None,
        )

    message = str(excinfo.value)
    assert message == korean_message
    assert _contains_hangul(message)
    assert not _contains_only_ascii_letters_words(message)


# ---------------------------------------------------------------------------------------------
# 3. build.build_project's generic exception handler must surface that same Korean text as
#    `error_message` (it only special-cases ImportError; everything else -- including this
#    RuntimeError -- falls through to the generic `except Exception` handler).
# ---------------------------------------------------------------------------------------------


def test_build_project_surfaces_korean_worker_failure_message(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runtime_module, "check_runtime", lambda **_kw: {"available": True, "message": ""}
    )
    monkeypatch.setattr(build_module, "runtime", runtime_module)

    def _raise_runtime_error(**_kwargs):
        raise RuntimeError("QGIS 작업 프로세스가 제한 시간 내에 응답하지 않았습니다.")

    monkeypatch.setattr(build_module.qgis_worker, "build_qgis_project", _raise_runtime_error)

    config = {
        "project_display_name": "Bridge Failure Test",
        "survey_type": "simple_inventory",
        "basemap": {"mode": "none"},
    }
    result = build_module.build_project(config, str(tmp_path / "out"))

    assert result["success"] is False
    assert _contains_hangul(result["error_message"])
    assert not _contains_only_ascii_letters_words(result["error_message"])


# ---------------------------------------------------------------------------------------------
# 4. wizard.ReviewAndBuildPage._on_build_finished: the actual user-facing result label.
# ---------------------------------------------------------------------------------------------


def test_wizard_result_label_shows_korean_message_on_worker_failure():
    from qfield_builder.ui.wizard import ReviewAndBuildPage

    page = ReviewAndBuildPage()

    page._on_build_finished(
        {
            "success": False,
            "error_code": "unexpected_error",
            "error_message": "QGIS 작업 프로세스가 제한 시간 내에 응답하지 않았습니다.",
        }
    )

    label_text = page.result_label.text()
    assert _contains_hangul(label_text)
    assert not _contains_only_ascii_letters_words(label_text)
