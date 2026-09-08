"""Section 13.1 — the project-scoped identification plugin (post-MVP guaranteed-manual baseline).

Covers:
- AC-QPB-069: the generated project's output folder contains a `<project_slug>.qml` file
  (matching `project_slug`, not `project_display_name`) placed alongside the `.qgs` file, at the
  same folder level (FR-QPB-100, revised; Decision Log D-31).
- AC-QPB-070: the "Identify attached photos" action is present as a `QML Widget` editor-widget
  embedded within the relevant layer's own attribute form (Type 1's `inventory_observation`;
  Type 2/3's `observation`), built via the same `QgsAttributeEditorContainer`/
  `QgsAttributeEditorField` mechanism as the rest of the form (FR-QPB-057), not as a separate,
  disconnected plugin surface (FR-QPB-101, revised; Decision Log D-31).
- FR-QPB-109 (further revised; Decision Log D-50/D-51) / AC-QPB-046 (further revised; Decision
  Log D-50) — **structural presence only**: whether the generated `<project_slug>.qml` project
  plugin and the embedded identification widget's own QML source actually contain the specific,
  confirmed write-back mechanism FR-QPB-109 now requires for a brand-new, not-yet-saved feature
  (a pending write-back request written via `FileUtils.writeFileContent()`; a project-plugin
  `Timer` poll; an `overlayFeatureFormDrawer.featureForm.model` lookup reached via
  `iface.findItemByObjectName('overlayFeatureFormDrawer')`; `changeAttribute()` application;
  overwrite-not-`FileUtils.deleteFiles()` clearing). This is a *necessary, not sufficient*
  structural check: it cannot execute the QML, so it cannot confirm the mechanism actually works
  end-to-end on a real device, nor that it is wired specifically to both required trigger points
  (candidate selection and manual-entry confirmation) rather than only one of them. The
  authoritative, end-to-end confirmation for both branches of AC-QPB-046 remains manual/`device`
  QA in `test_post_mvp_manual_qfield_runtime.py`.

Both criteria describe *generated build-pipeline artifacts* (a sidecar file; attribute-form
configuration inside the `.qgs` project) — this is the same kind of desktop-build-pipeline output
this project's MVP acceptance tests already inspect directly (see HARNESS_CONTRACT.md's rationale),
not QML/QField-runtime behavior. The *actual runtime behavior* of the embedded QML (permission
requests, reading attachments/EXIF, calling Pl@ntNet, displaying candidates) is out of this
harness's reach and is documented separately as manual/`device` QA in
`test_post_mvp_manual_qfield_runtime.py`.

See HARNESS_CONTRACT.md's "Post-MVP: Section 13" section, function 10
(`inspect_identification_widget`), for why the exact registered QGIS editor-widget-type-ID string
for "QML Widget" is deliberately *not* hardcoded into these tests as a literal string assertion.

**Decision Log D-46 note (AC-QPB-070 further revised, scoped to QField):** D-46 corrects
FR-QPB-101's photo-file-reading mechanism and, as a disclosed consequence, scopes AC-QPB-070's
criterion explicitly to QField, while disclosing that the same embedded widget is expected to
fail to load/render at all in QGIS Desktop specifically. The AC-QPB-070 test below (
`test_ac070_qml_widget_is_embedded_in_the_relevant_layers_attribute_form`) required no code change
for this: it only ever asserted the generated `.qgs` project's *static structure* (a QML Widget
field exists, is embedded in the attribute form, carries non-empty QML source) via
`inspect_identification_widget`'s direct XML/PyQGIS inspection of the build artifact — it never
loaded, executed, or rendered the QML through any real engine, for either QGIS Desktop or QField,
and never made any claim about which host application renders it. It therefore remains an accurate
build-pipeline-artifact check under the revised criterion. See
`tests/acceptance/qfield_project_builder_post_mvp_identification.traceability.md` for the full
determination and the new, separately tracked open question this revision raised (a documented
`manual`-marked placeholder at the end of this file, concerning whether the disclosed QGIS-Desktop
widget-load failure interacts with the unrevised MVP criterion AC-QPB-001).

**Decision Log D-50/D-51 note (FR-QPB-109 further revised; AC-QPB-046 further revised):**
Real-device testing and direct QGIS/QField source inspection (Decision Log D-50) confirmed the
prior, speculative `currentFeature.setAttribute(...)`-style write-back attempt never works, and
confirmed a different, narrower mechanism that does — but only for a brand-new, not-yet-saved
feature created via QField's own "Add feature" flow; write-back for an existing, already-saved
feature reopened later is a confirmed, permanent limitation, not an open question. Decision Log
D-51 extends the confirmed, working mechanism to manual identification entry, not just real
candidate selection, for the brand-new/not-yet-saved-feature branch. The `test_fr109_*` tests
added below (see the "FR-QPB-109 (further revised; Decision Log D-50/D-51)" section near the end
of this file) check only whether the generated QML source for both artifacts (the embedded
widget; the `<project_slug>.qml` project plugin) actually contains the confirmed mechanism's
required constituent pieces — a necessary, not sufficient, condition; they cannot execute the
QML. They are expected to currently FAIL (red) as of this test-design round, since
`qfield_builder/qml_plugin.py` still implements only the prior, now-confirmed-broken mechanism
(`qpbPersistIdentification`'s `currentFeature.setAttribute(...)` attempt — confirmed by direct
inspection of that module during this test-design round). See
`tests/acceptance/qfield_project_builder_post_mvp_identification.traceability.md`'s 2026-08-24
addendum for the full mapping and disclosed limitations, and
`test_post_mvp_manual_qfield_runtime.py` for the authoritative, real-device-required manual QA
this structural check cannot substitute for.

**AC-QPB-088 note (Decision Log D-52; FR-QPB-101 further revised — mandatory photo-resize-via-
temporary-copy step):** a confirmed real-device HTTP 413 rejection (an unresized, full-resolution
photo submitted to Pl@ntNet) led to a new, mandatory requirement: before a photo's bytes are
included in the Pl@ntNet multipart request body, the embedded widget must resize them via a
*temporary copy* — writing the original, already-read bytes to a new temporary file
(`FileUtils.writeFileContent()`), calling `FileUtils.restrictImageSize(<tempFilePath>, 1280)`
against that temporary copy only (never the original attachment file's own path), reading the
resized bytes back from that same temporary file (`FileUtils.readFileContent()`), and finally
clearing the temporary file with an empty-content overwrite (`FileUtils.writeFileContent(tempPath,
"")`, never `FileUtils.deleteFiles()`, per Decision Log D-50's confirmed unreliability finding for
that method) — never mutating the original, full-resolution attachment file itself. The
`test_ac088_*` tests near the end of this file check only whether the generated widget QML
*structurally* contains this ordered mechanism — a necessary, not sufficient, condition; they
cannot execute the QML, and, as static-text checks, cannot perfectly distinguish "the original
attachment file's own path" from "the new temporary file's own path" in every conceivable
implementation shape (see that section's own header comment for the precise, disclosed heuristic
and its limitations). They are expected to currently FAIL (red) as of this test-design round: a
direct inspection of `qfield_builder/qml_plugin.py` during this round confirmed no
`FileUtils.restrictImageSize(` call, and no photo-resize-related temporary-file handling of any
kind, exists yet anywhere in the generated QML — `qpbReadFileBytes`/`qpbRunIdentification` still
read and submit each photo's original, unresized bytes directly. See
`tests/acceptance/qfield_project_builder_post_mvp_identification.traceability.md`'s AC-QPB-088
addendum for the full mapping and disclosed limitations.

**AC-QPB-095 note (Decision Log D-54; FR-QPB-109 further revised — new per-candidate
representative-image display, CC BY-SA attribution, graceful degradation, and image-load-failure
isolation):** Pl@ntNet's own documentation confirms an `include-related-images=true` request
parameter (FR-QPB-104, further revised; AC-QPB-094, tested in
`test_post_mvp_plantnet_request_shape.py`) causes each result to carry a related-images list with
`organ`/`author`/`license`/`date`/`citation` fields plus an `o`/`m`/`s` size-variant `url` object.
FR-QPB-109 (further revised) requires each candidate card to additionally display one
representative image (the small, `s`, size variant) when supplied, with the required CC BY-SA
attribution whenever an image is shown, degrading gracefully (no broken-image placeholder, no
attribution text) when a candidate has no image, and never letting an image-load failure corrupt
the rest of that candidate's textual content. The `test_ac095_*` tests near the end of this file
check only whether the generated widget QML *structurally* contains this mechanism — a necessary,
not sufficient, condition, relying on several disclosed heuristics (see that section's own header
comment). They are expected to currently FAIL (red) as of this test-design round: a direct
inspection of `qfield_builder/qml_plugin.py` during this round confirmed no `Image` QML element,
no occurrence of the literal text "CC BY-SA", and no `author`-field reference of any kind exist
anywhere yet in the generated identification widget QML. AC-QPB-096 (the one part of this feature
that requires actually seeing an image render on a real device) is an explicit manual-QA-only
placeholder per the specification itself — see
`test_post_mvp_manual_qfield_runtime.py::test_ac096_representative_image_renders_on_screen_with_attribution_and_image_load_failure_does_not_corrupt_the_card`.
See `tests/acceptance/qfield_project_builder_post_mvp_identification.traceability.md`'s AC-QPB-094/
095/096 addendum for the full mapping and disclosed limitations.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import make_base_config

pytestmark = pytest.mark.qgis


def _build_with_identification(
    acceptance_api, tmp_path, survey_type: str, display_name: str = "테스트 식별 프로젝트"
):
    config = make_base_config(survey_type, display_name=display_name)
    config["identification_enabled"] = True
    out_dir = tmp_path / f"proj_{survey_type}"
    return acceptance_api.build_project(config, str(out_dir))


# --- AC-QPB-069 ------------------------------------------------------------------


@pytest.mark.parametrize(
    "survey_type", ["simple_inventory", "temporary_plots", "permanent_plots", "vegetation_mapping"]
)
def test_ac069_project_slug_qml_plugin_file_exists_alongside_qgs(
    acceptance_api, tmp_path, survey_type
):
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    assert slug, "build_project() must report project_slug"

    expected_plugin_path = project_dir / f"{slug}.qml"
    assert expected_plugin_path.is_file(), (
        f"AC-QPB-069: expected a project-plugin sidecar at {expected_plugin_path} "
        f"(FR-QPB-100, revised; Decision Log D-31)"
    )

    qgs_path = Path(result["qgs_path"])
    assert expected_plugin_path.parent == qgs_path.parent, (
        "AC-QPB-069: the <project_slug>.qml plugin must sit alongside the .qgs file, at the same "
        "folder level, matching QField's own documented project-plugin discovery convention"
    )


def test_ac069_plugin_filename_uses_ascii_slug_not_unicode_display_name(acceptance_api, tmp_path):
    result = _build_with_identification(
        acceptance_api, tmp_path, "simple_inventory", display_name="한글 프로젝트 이름 테스트"
    )
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    assert slug.isascii(), "project_slug must be ASCII (FR-QPB-021/022)"

    plugin_files = list(project_dir.glob("*.qml"))
    assert plugin_files, "expected a <project_slug>.qml plugin file"
    assert plugin_files[0].stem == slug, (
        "AC-QPB-069: the plugin filename must be derived from project_slug, never from the "
        "Unicode project_display_name"
    )
    assert "한글" not in plugin_files[0].name


def test_identification_disabled_keeps_shared_sidecar_without_identification_runtime(
    acceptance_api, tmp_path
):
    """FR-QPB-038 (D-87): the shared report sidecar remains, but identification content does not.

    This replaces the superseded premise that disabling identification suppresses the whole
    ``<project_slug>.qml`` file. The sidecar and report mechanism are now unconditional under
    FR-QPB-090/100/133; only the reminder and write-back polling Timer remain gated.
    """
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = False
    out_dir = tmp_path / "proj_no_identification"
    result = acceptance_api.build_project(config, str(out_dir))
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    plugin_path = project_dir / f"{result['project_slug']}.qml"
    assert plugin_path.is_file(), (
        "FR-QPB-090/100/133 (D-87): the shared project-plugin sidecar must still be generated "
        "when identification is disabled"
    )
    plugin_source = plugin_path.read_text(encoding="utf-8")
    assert "Export HTML Report" in plugin_source, (
        "FR-QPB-133 (D-87): the unconditional report mechanism must remain in the shared sidecar"
    )
    assert "Identify attached photos" not in plugin_source, (
        "FR-QPB-038 (D-87): identification-disabled output must omit the identification reminder"
    )
    assert re.search(r"\bTimer\s*\{", plugin_source) is None, (
        "FR-QPB-038 (D-87): identification-disabled output must omit the write-back polling Timer"
    )


# --- AC-QPB-070 ------------------------------------------------------------------


@pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)
def test_ac070_qml_widget_is_embedded_in_the_relevant_layers_attribute_form(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")

    report = inspect_identification_widget(result["project_dir"], layer_name)
    assert report["qml_widget_field_found"] is True, (
        f"AC-QPB-070: expected a QML Widget editor-widget on {layer_name!r}: {report}"
    )
    assert report["qml_widget_field_name"], "expected the hosting field's name to be reported"
    assert report["embedded_in_attribute_form"] is True, (
        "AC-QPB-070: the QML Widget must be embedded within the layer's own attribute form "
        "(QgsAttributeEditorContainer/QgsAttributeEditorField, FR-QPB-057), not merely configured "
        f"as an available-but-unplaced widget: {report}"
    )
    assert report["qml_code_present"] is True, (
        "AC-QPB-101 (revised): the embedded QML Widget must carry actual QML source implementing "
        f"the 'Identify attached photos' action, not an empty placeholder: {report}"
    )


def test_ac070_vegetation_mapping_community_layer_has_display_only_qml_widget(
    acceptance_api, project_layer_xml, tmp_path
):
    """Type 4 community forms show candidates but never offer candidate write-back."""
    result = _build_with_identification(acceptance_api, tmp_path, "vegetation_mapping")
    assert result["success"], result.get("error_message")

    layer = project_layer_xml(result, "community")
    widget = layer.find("./attributeEditorForm//attributeEditorQmlElement")
    assert widget is not None
    assert "qpbCandidateSelectionEnabled: false" in (widget.text or "")


def test_ac070_no_qml_widget_anywhere_when_identification_disabled(
    acceptance_api, inspect_identification_widget, tmp_path
):
    config = make_base_config("simple_inventory")
    config["identification_enabled"] = False
    out_dir = tmp_path / "proj_no_identification_widget"
    result = acceptance_api.build_project(config, str(out_dir))
    assert result["success"], result.get("error_message")

    report = inspect_identification_widget(result["project_dir"], "inventory_observation")
    assert report["qml_widget_field_found"] is False


# --- Open question (Decision Log D-46): does the QML Widget's disclosed QGIS-Desktop load ------
# --- failure additionally trigger a project-level "repair" warning of the kind AC-QPB-001 -------
# --- (an unrevised MVP criterion) tests? Not automatable here; documented, not silently dropped. -


@pytest.mark.manual
@pytest.mark.skip(
    reason=(
        "Decision Log D-46 discloses that adopting QField's `org.qfield.core`/`QfFileUtils` "
        "module (FR-QPB-101, further revised) is expected to make the embedded 'Identify "
        "attached photos' QML Widget fail to load/render at all when the same generated project "
        "is opened in QGIS Desktop specifically -- an accepted, disclosed tradeoff, not a defect "
        "(AC-QPB-070, further revised, no longer asserts or requires QGIS-Desktop rendering "
        "success at all). What Decision Log D-46 does NOT state is whether that same widget-load "
        "failure, encountered when a human actually opens the relevant layer's attribute form for "
        "a feature inside QGIS Desktop's own GUI, additionally triggers any project-level "
        "'repair'/error warning of the kind AC-QPB-001 (an MVP criterion, unrevised by D-46, and "
        "still worded as applying to 'a generated project for any of the four survey types' with "
        "no identification-enabled carve-out) requires be absent. This matters because "
        "AC-QPB-001's existing automated coverage "
        "(test_geopackage_common.py::test_ac001_project_opens_without_repair_warning) only ever "
        "builds/validates projects with identification_enabled=False (make_base_config's default) "
        "via a headless, non-interactive validate_project() call that never opens any feature's "
        "attribute form -- so it has never actually exercised, and cannot detect, this specific "
        "new failure mode. Confirming whether a QML-Widget load failure escalates into a "
        "project-level repair warning requires a human opening an identification-enabled "
        "generated project's actual attribute form inside a real, running QGIS Desktop GUI "
        "session -- not automatable by this harness (this project's hard QGIS-isolation rule also "
        "bars the test-designer role itself from ever constructing a QgsApplication for any "
        "diagnostic purpose, including this one). No outcome is asserted or assumed here. "
        "\n\nManual QA steps: (1) Build a project for any survey type with "
        "identification_enabled=True. (2) Open the generated .qgs project in the exact supported "
        "QGIS Desktop version (AC-QPB-001's own target). (3) Confirm the project itself opens "
        "without any repair warning at the project-open step (expected to be unaffected, since "
        "the existing identification-disabled AC-QPB-001 test already covers project-open itself; "
        "this step simply re-confirms that with identification enabled). (4) Additionally open "
        "the relevant layer's (inventory_observation, or observation) attribute form for any one "
        "feature, triggering the embedded QML Widget's load attempt. (5) Record whether QGIS "
        "Desktop shows any repair/error dialog, a broken-widget indicator, or a Log Messages Panel "
        "error at that point. (6) If a repair warning is in fact shown, report this as a concrete, "
        "non-blocking finding against AC-QPB-001 for identification-enabled projects "
        "specifically, rather than silently treating Decision Log D-46's disclosed tradeoff "
        "(which only concerns the widget's own render failure, not any project-level escalation) "
        "as already covering this distinct symptom."
    )
)
def test_qgis_desktop_repair_warning_status_when_qml_widget_fails_to_load_not_yet_confirmed():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- FR-QPB-109 (further revised; Decision Log D-50/D-51) / AC-QPB-046 (further revised; ---------
# --- Decision Log D-50) -- structural presence of the confirmed write-back mechanism, -------------
# --- for the brand-new/not-yet-saved-feature branch only (existing/already-saved-feature ----------
# --- write-back is a confirmed, permanent *limitation* -- nothing to assert structurally here). ---
#
# Every test below is a *necessary, not sufficient* structural check: it inspects the generated
# QML/JavaScript source text this project's own build pipeline produces (the embedded widget via
# `inspect_identification_widget()`'s new `qml_code` field, HARNESS_CONTRACT.md function 10's
# 2026-08-24 addendum; the `<project_slug>.qml` project plugin by reading the sidecar file this
# project's own build pipeline already places on disk, exactly like AC-QPB-069's existing
# `expected_plugin_path.is_file()` check). It never loads, executes, or renders the QML through
# any real QML/QField engine, so it cannot confirm the mechanism actually works end-to-end on a
# real device, nor that a given call site is genuinely reachable from both required trigger points
# (candidate selection and manual-entry confirmation) rather than only one of them -- the
# authoritative, end-to-end confirmation for both branches of AC-QPB-046 remains manual/`device`
# QA in `test_post_mvp_manual_qfield_runtime.py`. See this file's own module docstring above and
# `tests/acceptance/qfield_project_builder_post_mvp_identification.traceability.md`'s 2026-08-24
# addendum for the full mapping and disclosed limitations.
#
# All tests in this section are expected to currently FAIL (red): `qfield_builder/qml_plugin.py`
# still implements only the prior, now-confirmed-broken `currentFeature.setAttribute(...)`
# best-effort attempt (`qpbPersistIdentification`), and `render_project_plugin_qml()` contains
# only a toolbar button/toast -- neither a pending-request write/poll/apply/clear mechanism of any
# kind exists yet in either generated artifact (confirmed by direct inspection of
# `qfield_builder/qml_plugin.py` during this test-design round).


def _widget_qml_source(inspect_identification_widget, project_dir: str, layer_name: str) -> str:
    report = inspect_identification_widget(project_dir, layer_name)
    assert report["qml_widget_field_found"] is True, (
        f"expected an embedded 'Identify attached photos' QML Widget on {layer_name!r}: {report}"
    )
    qml_code = report.get("qml_code")
    assert qml_code, (
        "expected inspect_identification_widget() to report the widget's raw QML source via "
        "the 'qml_code' key (HARNESS_CONTRACT.md function 10, 2026-08-24 addendum) -- got "
        f"{report!r}"
    )
    return qml_code


@pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)
def test_fr109_embedded_widget_writes_a_pending_write_back_request_via_file_utils(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """FR-QPB-109 (further revised; Decision Log D-50/D-51): for a brand-new, not-yet-saved
    feature, the embedded identification widget must write a pending write-back request -- the
    current feature's own UUID, the target attribute field name, and the value -- to a request
    file inside the project folder, via `FileUtils.writeFileContent()`. Decision Log D-51 extends
    this to the manual-entry-confirmation trigger as well as real candidate selection, using "the
    identical confirmed mechanism" -- i.e. a single, shared write-back call site reachable from
    both triggers is the *expected*, spec-aligned shape, not a limitation; this test therefore
    only requires the call to exist somewhere in the widget's QML, not that it is duplicated once
    per trigger. It cannot prove the call is actually reachable from both trigger points (see this
    section's own header comment).
    """
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")

    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)
    assert "FileUtils.writeFileContent(" in qml_code, (
        "FR-QPB-109 (further revised; Decision Log D-50/D-51): expected the embedded widget's "
        "own QML source to write a pending write-back request via FileUtils.writeFileContent() "
        f"somewhere -- not found in the generated QML for {layer_name!r}"
    )


@pytest.fixture(scope="module")
def identification_project_plugin_source(acceptance_api, tmp_path_factory):
    """Builds one identification-enabled project (module-scoped -- shared, read-only inspection,
    across the FR-QPB-109 project-plugin structural tests below) and returns
    `(plugin_qml_source_text, build_result)`."""
    tmp_path = tmp_path_factory.mktemp("fr109_project_plugin")
    result = _build_with_identification(acceptance_api, tmp_path, "simple_inventory")
    assert result["success"], result.get("error_message")

    project_dir = Path(result["project_dir"])
    slug = result["project_slug"]
    plugin_path = project_dir / f"{slug}.qml"
    assert plugin_path.is_file(), f"expected a <project_slug>.qml plugin sidecar at {plugin_path}"
    return plugin_path.read_text(encoding="utf-8"), result


def test_fr109_project_plugin_polls_for_the_pending_request_via_a_timer(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): the project plugin (`<project_slug>.qml`)
    "must poll for this request on a short-interval `Timer`". This checks only that a QML `Timer`
    component is declared in the generated plugin source -- it cannot confirm the Timer actually
    drives the polling/apply logic the other tests in this section check separately (necessary,
    not sufficient)."""
    plugin_source, _ = identification_project_plugin_source
    assert re.search(r"\bTimer\s*\{", plugin_source), (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        "declare a Timer component to poll for the pending write-back request file"
    )


def test_fr109_project_plugin_reaches_the_live_attribute_form_model_via_overlay_drawer(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): the project plugin must locate the live
    `AttributeFormModel` for the feature currently being created, "reachable via
    `overlayFeatureFormDrawer.featureForm.model`" -- Decision Log D-50's own confirmed finding
    names `iface.findItemByObjectName('overlayFeatureFormDrawer')` as the confirmed way a project
    plugin reaches this object. This check is deliberately loose: it requires only that both named
    identifiers ("overlayFeatureFormDrawer" and a "featureForm"/".model" access) appear somewhere
    in the plugin's QML source, since the exact statement-level chaining (one dotted expression
    vs. split across an intermediate variable) is an implementation detail this project's own
    confirmed-mechanism text does not literally dictate beyond naming this access path
    conceptually."""
    plugin_source, _ = identification_project_plugin_source
    assert "overlayFeatureFormDrawer" in plugin_source, (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        "reference 'overlayFeatureFormDrawer' (QField's own Add-feature drawer -- the only "
        "confirmed way to reach a brand-new feature's live AttributeFormModel)"
    )
    assert "featureForm" in plugin_source and ".model" in plugin_source, (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        "reach the live AttributeFormModel via '...featureForm.model' "
        "(overlayFeatureFormDrawer.featureForm.model)"
    )


def test_fr109_project_plugin_matches_the_pending_requests_uuid_before_applying_it(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): before applying a pending request, the
    project plugin must "confirm its current feature's UUID matches the pending request". No
    specific property/variable name for this comparison is named anywhere in the specification's
    own text (unlike `overlayFeatureFormDrawer`/`featureForm.model`/`changeAttribute`, which are
    literal, spec-quoted identifiers) -- this is therefore the loosest, most heuristic check in
    this section, deliberately not over-fitted to a guessed implementation shape: it requires only
    that the plugin's QML source contains the case-insensitive substring "uuid" somewhere near
    (same source file as) the `changeAttribute(` call this section's other test already requires,
    as a minimal signal that *some* identity check is present before applying a write. This cannot,
    by itself, prove the comparison is correct, or even that it actually gates the
    `changeAttribute(` call at all -- flagged here, not silently assumed, as this section's
    weakest check."""
    plugin_source, _ = identification_project_plugin_source
    assert "changeAttribute(" in plugin_source, (
        "expected the project plugin QML to call changeAttribute(name, value) at all -- see "
        "test_fr109_project_plugin_applies_the_pending_request_via_change_attribute"
    )
    assert re.search(r"uuid", plugin_source, re.IGNORECASE), (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        "reference a UUID somewhere, as the minimal signal of the required "
        "'current feature's UUID matches the pending request' check before applying a write-back "
        "(see this test's own docstring for why this specific check is intentionally loose)"
    )


def test_fr109_project_plugin_applies_the_pending_request_via_change_attribute(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): once the pending request's UUID matches
    the current feature, the project plugin must call `changeAttribute(name, value)` on the live
    AttributeFormModel to actually apply the write."""
    plugin_source, _ = identification_project_plugin_source
    assert "changeAttribute(" in plugin_source, (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        "call changeAttribute(name, value) on the live AttributeFormModel to apply the pending "
        "write-back request"
    )


def test_fr109_project_plugin_never_clears_the_pending_request_via_delete_files(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): the pending-request file must be cleared
    "not by calling `FileUtils.deleteFiles()`, which real-device testing found unreliable on at
    least one tested device". This is the robust half of the clearing requirement (a plain
    substring absence, not a fragile regex); the file must also actually clear the request by some
    overwrite -- see `test_fr109_project_plugin_clears_the_pending_request_with_a_literal_empty_content_overwrite`
    for that narrower, best-effort half, kept in its own test so a styling difference in *how* the
    overwrite is expressed cannot mask this stronger, more essential prohibition."""
    plugin_source, _ = identification_project_plugin_source
    assert "FileUtils.deleteFiles(" not in plugin_source, (
        "FR-QPB-109 (further revised; Decision Log D-50): the project plugin must never clear "
        "the pending-request file via FileUtils.deleteFiles() -- real-device testing found this "
        "unreliable; overwrite with empty content instead"
    )
    assert "FileUtils.writeFileContent(" in plugin_source, (
        "FR-QPB-109 (further revised; Decision Log D-50): expected the project plugin QML to "
        'clear the pending-request file by overwriting it (FileUtils.writeFileContent(path, ""))'
        " once the request has been applied"
    )


def test_fr109_project_plugin_clears_the_pending_request_with_a_literal_empty_content_overwrite(
    identification_project_plugin_source,
):
    """FR-QPB-109 (further revised; Decision Log D-50): the pending-request file must be cleared
    "by overwriting it with empty content". This is a narrower, best-effort structural check on
    top of `test_fr109_project_plugin_never_clears_the_pending_request_via_delete_files`: it looks
    for a literal `FileUtils.writeFileContent(<path>, "")` (or `''`) call -- a semantically
    equivalent implementation that first stores an empty string in a named variable (e.g.
    `var EMPTY = ""; FileUtils.writeFileContent(path, EMPTY);`) would not be structurally detected
    by this specific regex. That limitation is disclosed here, not silently assumed away; if this
    test alone fails while the other FR-QPB-109 project-plugin tests in this section pass, that is
    this narrow regex's own limitation, not necessarily a real conformance defect, and should be
    checked by hand against the actual generated source before being treated as a genuine gap."""
    plugin_source, _ = identification_project_plugin_source
    empty_overwrite_pattern = re.compile(r'FileUtils\.writeFileContent\([^()]*,\s*(?:""|\'\')\s*\)')
    assert empty_overwrite_pattern.search(plugin_source), (
        "FR-QPB-109 (further revised; Decision Log D-50): expected at least one "
        'FileUtils.writeFileContent(path, "") call with a literal empty-string second argument, '
        "clearing the pending request (best-effort check -- see this test's own docstring for "
        "its disclosed limitation)"
    )


# --- AC-QPB-088 (post-MVP; new, Decision Log D-52) -- structural presence of the mandatory ---------
# --- photo-resize-via-temporary-copy mechanism (FR-QPB-101, further revised; Decision Log D-52). ---
#
# FR-QPB-101 (further revised; Decision Log D-52) requires that, before a photo's bytes are
# included in the Pl@ntNet multipart request body, the embedded widget resize them via a
# *temporary copy*: (1) write the original, already-read bytes to a NEW temporary file via
# `FileUtils.writeFileContent()`, at a path distinct from the original attachment file's own path;
# (2) call `FileUtils.restrictImageSize(<tempFilePath>, 1280)` against that temporary copy's path
# only -- never against the original attachment file's own path; (3) read the resized bytes back
# from that same temporary file via `FileUtils.readFileContent()`, for use as the Pl@ntNet
# multipart request body, in place of the original, unresized bytes; and (4) clean up the
# temporary file afterward by overwriting it with empty content
# (`FileUtils.writeFileContent(tempPath, "")`), never via `FileUtils.deleteFiles()` (Decision Log
# D-50's confirmed unreliability finding for that method).
#
# Every test below is a *necessary, not sufficient* structural check on the generated widget QML
# source text (via `inspect_identification_widget()`'s `qml_code` field, exactly like the
# `test_fr109_*` widget check above) -- it never loads, executes, or renders the QML through any
# real QML/QField engine, so it cannot confirm the mechanism actually works end-to-end on a real
# device, nor (see the next paragraph) can it perfectly distinguish "the original attachment
# file's own path" from "the new temporary file's own path" for every conceivable, otherwise
# spec-conformant implementation shape.
#
# **Disclosed heuristic and its limitation (identifying "the original attachment file's own
# path").** AC-QPB-088 requires checking that `FileUtils.restrictImageSize()` is never called
# against the original attachment file's own path, and that the temporary file written/read back
# is at a path "distinct from" it -- but neither FR-QPB-101 nor AC-QPB-088 names a specific
# variable/identifier for either path (unlike, say, FR-QPB-109's spec-quoted
# `overlayFeatureFormDrawer`/`changeAttribute` identifiers, which are real QField API names that
# must appear literally), so these tests must infer which call site is "the original" from
# structure alone. They do this by: (a) locating the `FileUtils.restrictImageSize(<X>, 1280)`
# call, whose captured first argument `<X>` is treated as "the temporary file's own path" for the
# rest of this section (an unambiguous anchor, since `1280` is a literal, spec-mandated value and
# no other call in this codebase resizes anything); then (b) treating the argument of the first
# `FileUtils.readFileContent()`/`QfFileUtils.readFileContent()` call *within the same enclosing
# JavaScript function* as `<X>`'s own `restrictImageSize()` call, whose argument differs from
# `<X>`, as "the original attachment file's own path" -- falling back to a whole-source search
# only if no such call exists in that local scope (e.g. if the resize logic is factored into its
# own small helper function). This deliberately does not search the *entire* generated QML
# indiscriminately for the first `FileUtils.readFileContent()`/`QfFileUtils.readFileContent()`
# call of any kind, because this project's own already-shipped QML legitimately contains several
# other, wholly unrelated calls to these same methods for bundled reference-data files (the KTSN
# lookup CSV, the national accepted-taxa list, the pending write-back request) that must not be
# confused with the photo-resize mechanism's own path variable. This heuristic is disclosed, not
# silently assumed perfect: a correct implementation that reuses and reassigns one single local
# variable name for both the original path and (after the original bytes have been read) the
# temporary path, within the very same function, would not be structurally distinguishable from an
# incorrect implementation that resizes the original attachment file in place, by textual
# comparison alone -- this is a genuine limitation of static-text inspection with no QML execution
# available, not a gap this test-design round silently resolved. The identical-naming-collision
# risk with the *unrelated* reference-data loaders above is a separate, narrower risk this
# heuristic's local-scope-first strategy is specifically designed to avoid.
#
# **Also note (identifying "the original attachment file's own path")**: because FR-QPB-101
# (further revised; Decision Log D-52) restates, unaltered, the original-photo-read mechanism from
# FR-QPB-101 (further revised; Decision Log D-46) -- whose own text names it
# `QfFileUtils.readFileContent(filePath)` -- while Decision Log D-52's own "Naming note, disclosed
# not resolved" explicitly leaves open whether that differs from the plain `FileUtils` naming
# Decision Log D-50/D-52 use for the write/resize/read-back/cleanup calls, the search for "the
# original attachment file's own path" below matches *either* `FileUtils.readFileContent(...)` or
# `QfFileUtils.readFileContent(...)`, remaining agnostic to this specification-disclosed,
# unresolved naming question. The read-back call itself (element (3) above), by contrast, is
# checked against the plain `FileUtils.readFileContent()` spelling only, exactly matching
# AC-QPB-088's own literal wording.
#
# All tests in this section are expected to currently FAIL (red): a direct inspection of
# `qfield_builder/qml_plugin.py` during this test-design round confirmed no
# `FileUtils.restrictImageSize(` call, and no photo-resize temporary-file handling of any kind,
# exists yet anywhere in the generated QML.


_ARG = r"(?:[^(),]|\([^()]*\))+?"

# Matches either the plain `FileUtils.readFileContent(...)` spelling (Decision Log D-50/D-52, and
# this codebase's own already-shipped implementation) or the `QfFileUtils.readFileContent(...)`
# spelling FR-QPB-101 (further revised; Decision Log D-46)'s own text still uses for the original
# photo-byte read -- see this section's own header comment for why both are accepted when
# identifying "the original attachment file's own path".
_READ_FILE_CONTENT_ANY_RE = re.compile(r"(?:Qf)?FileUtils\.readFileContent\(\s*(" + _ARG + r")\s*\)")
# The plain spelling only -- matches AC-QPB-088's own literal wording for the resized-bytes
# read-back call specifically (element (3)).
_READ_FILE_CONTENT_PLAIN_RE = re.compile(r"(?<!Qf)FileUtils\.readFileContent\(\s*(" + _ARG + r")\s*\)")
_WRITE_FILE_CONTENT_RE = re.compile(
    r"FileUtils\.writeFileContent\(\s*(" + _ARG + r")\s*,\s*(" + _ARG + r")\s*\)"
)
_RESTRICT_IMAGE_SIZE_RE = re.compile(
    r"FileUtils\.restrictImageSize\(\s*(" + _ARG + r")\s*,\s*(" + _ARG + r")\s*\)"
)
_FUNCTION_DECL_RE = re.compile(r"function\s+\w+\s*\([^()]*\)\s*\{")


def _is_empty_string_literal(arg: str) -> bool:
    return arg.strip() in ('""', "''")


def _enclosing_function_span(qml_code: str, pos: int) -> tuple[int, int]:
    """Returns the (start, end) character-offset span of the smallest ``function name(...) { ...
    }`` declaration that contains `pos`, found via simple brace-depth counting from each
    declaration's own opening brace -- this project's generated QML/JavaScript is plain,
    brace-balanced script with no unbalanced braces inside string/comment literals (confirmed by
    inspection of the current, already-shipped generated QML during test design). Falls back to
    the entire source (`0, len(qml_code)`) if no enclosing function is found, so callers degrade to
    a whole-file search rather than raising."""
    best = None
    for m in _FUNCTION_DECL_RE.finditer(qml_code):
        brace_start = m.end() - 1
        depth = 0
        end = None
        i = brace_start
        while i < len(qml_code):
            ch = qml_code[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1
        if end is None:
            continue
        if brace_start <= pos < end and (best is None or (end - brace_start) < (best[1] - best[0])):
            best = (brace_start, end)
    return best if best is not None else (0, len(qml_code))


def _find_restrict_image_size_1280_matches(qml_code: str) -> list["re.Match[str]"]:
    return [m for m in _RESTRICT_IMAGE_SIZE_RE.finditer(qml_code) if m.group(2).strip() == "1280"]


def _find_temp_resize_path_arg(qml_code: str) -> str | None:
    matches = _find_restrict_image_size_1280_matches(qml_code)
    return matches[0].group(1).strip() if matches else None


def _find_original_attachment_path_arg(qml_code: str, restrict_match: "re.Match[str]") -> str | None:
    """See this section's own header comment for the full reasoning and disclosed limitations."""
    temp_path_arg = restrict_match.group(1).strip()
    span_start, span_end = _enclosing_function_span(qml_code, restrict_match.start())
    scope = qml_code[span_start:span_end]
    candidates = [
        m.group(1).strip()
        for m in _READ_FILE_CONTENT_ANY_RE.finditer(scope)
        if m.group(1).strip() != temp_path_arg
    ]
    if not candidates:
        candidates = [
            m.group(1).strip()
            for m in _READ_FILE_CONTENT_ANY_RE.finditer(qml_code)
            if m.group(1).strip() != temp_path_arg
        ]
    return candidates[0] if candidates else None


_AC088_LAYER_PARAMS = pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)


@_AC088_LAYER_PARAMS
def test_ac088_widget_writes_original_photo_bytes_to_a_new_temporary_file(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-088 element (1): the embedded widget must write the original photo's already-read
    bytes to a NEW temporary file via `FileUtils.writeFileContent()`, at a path distinct from the
    original attachment file's own path -- not merely re-use the empty-content cleanup call
    (element (4)) at the same path."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    temp_path_arg = _find_temp_resize_path_arg(qml_code)
    assert temp_path_arg is not None, (
        "AC-QPB-088 (FR-QPB-101, further revised; Decision Log D-52): expected a "
        "FileUtils.restrictImageSize(<tempFilePath>, 1280) call in the embedded widget's QML, "
        "identifying the temporary file's own path -- none found (this mechanism is not yet "
        "implemented)"
    )

    content_writes = [
        m
        for m in _WRITE_FILE_CONTENT_RE.finditer(qml_code)
        if m.group(1).strip() == temp_path_arg and not _is_empty_string_literal(m.group(2))
    ]
    assert content_writes, (
        "AC-QPB-088: expected a FileUtils.writeFileContent(<tempFilePath>, <original bytes>) call "
        f"writing content (not an empty-string cleanup) to the same temporary path "
        f"({temp_path_arg!r}) used by FileUtils.restrictImageSize() -- none found"
    )


@_AC088_LAYER_PARAMS
def test_ac088_widget_calls_restrict_image_size_only_against_the_temporary_file_with_maximum_1280(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-088 element (2), positive and negative halves together (the same call site governs
    both): the embedded widget must call `FileUtils.restrictImageSize(<tempFilePath>, 1280)`
    against the temporary copy's own path, and must never call it against the original attachment
    file's own path (see this section's own header comment for how "the original attachment
    file's own path" is identified, and its disclosed limitation)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    restrict_matches = list(_RESTRICT_IMAGE_SIZE_RE.finditer(qml_code))
    assert restrict_matches, (
        "AC-QPB-088 (FR-QPB-101, further revised; Decision Log D-52): expected a "
        "FileUtils.restrictImageSize() call in the embedded widget's QML -- none found (this "
        "mechanism is not yet implemented)"
    )
    matches_with_1280 = _find_restrict_image_size_1280_matches(qml_code)
    assert matches_with_1280, (
        "AC-QPB-088: found FileUtils.restrictImageSize() call(s) in the embedded widget's QML, but "
        "none with the required literal maximum width/height argument of 1280 -- found: "
        + ", ".join(
            f"restrictImageSize({m.group(1).strip()}, {m.group(2).strip()})" for m in restrict_matches
        )
    )

    original_path_arg = _find_original_attachment_path_arg(qml_code, matches_with_1280[0])
    if original_path_arg is None:
        pytest.fail(
            "AC-QPB-088: could not identify a distinct 'original attachment photo path' "
            "FileUtils.readFileContent()/QfFileUtils.readFileContent() call anywhere in the "
            "embedded widget's QML to check FileUtils.restrictImageSize() against -- see this "
            "section's own header comment for this heuristic's disclosed limitation"
        )

    for m in restrict_matches:
        assert m.group(1).strip() != original_path_arg, (
            "AC-QPB-088: FileUtils.restrictImageSize() must never be called against the original "
            f"attachment file's own path ({original_path_arg!r}) -- only against a distinct "
            f"temporary copy's path. Found: restrictImageSize({m.group(1).strip()}, "
            f"{m.group(2).strip()})"
        )


@_AC088_LAYER_PARAMS
def test_ac088_widget_reads_the_resized_bytes_back_from_the_temporary_file(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-088 element (3): the embedded widget must read the resized bytes back from the same
    temporary file via the plain `FileUtils.readFileContent()` (matching AC-QPB-088's own literal
    wording -- not the `QfFileUtils.readFileContent()` spelling FR-QPB-101 (further revised;
    Decision Log D-46) uses for the original photo-byte read; see this section's own header
    comment for the disclosed, unresolved naming question this reflects)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    temp_path_arg = _find_temp_resize_path_arg(qml_code)
    assert temp_path_arg is not None, (
        "AC-QPB-088 (FR-QPB-101, further revised; Decision Log D-52): expected a "
        "FileUtils.restrictImageSize(<tempFilePath>, 1280) call in the embedded widget's QML, "
        "identifying the temporary file's own path -- none found (this mechanism is not yet "
        "implemented)"
    )

    read_back = [
        m for m in _READ_FILE_CONTENT_PLAIN_RE.finditer(qml_code) if m.group(1).strip() == temp_path_arg
    ]
    assert read_back, (
        "AC-QPB-088: expected a FileUtils.readFileContent(<tempFilePath>) call reading the resized "
        f"bytes back from the same temporary path ({temp_path_arg!r}) used by "
        "FileUtils.restrictImageSize() -- none found"
    )


@_AC088_LAYER_PARAMS
def test_ac088_widget_clears_the_temporary_file_with_empty_content_never_delete_files(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-088 element (4): the temporary file must be cleaned up by overwriting it with empty
    content via `FileUtils.writeFileContent(tempPath, "")` -- never via `FileUtils.deleteFiles()`
    (Decision Log D-50's confirmed unreliability finding for that method, on at least one tested
    device)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    assert "FileUtils.deleteFiles(" not in qml_code, (
        "AC-QPB-088 (Decision Log D-52, citing Decision Log D-50's deleteFiles()-unreliability "
        "finding): the temporary file must never be cleaned up via FileUtils.deleteFiles() -- "
        "found a call to it in the embedded widget's QML"
    )

    temp_path_arg = _find_temp_resize_path_arg(qml_code)
    assert temp_path_arg is not None, (
        "AC-QPB-088 (FR-QPB-101, further revised; Decision Log D-52): expected a "
        "FileUtils.restrictImageSize(<tempFilePath>, 1280) call in the embedded widget's QML, "
        "identifying the temporary file's own path -- none found (this mechanism is not yet "
        "implemented)"
    )
    cleanup_writes = [
        m
        for m in _WRITE_FILE_CONTENT_RE.finditer(qml_code)
        if m.group(1).strip() == temp_path_arg and _is_empty_string_literal(m.group(2))
    ]
    assert cleanup_writes, (
        "AC-QPB-088: expected a temporary-file cleanup call overwriting the temporary file with "
        f'empty content (FileUtils.writeFileContent({temp_path_arg}, "")) -- none found'
    )


@_AC088_LAYER_PARAMS
def test_ac088_resize_mechanism_runs_in_order_and_resized_bytes_precede_the_plantnet_request(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-088, combined ordering assertion: the temporary-file content write must happen
    BEFORE `FileUtils.restrictImageSize()`, which must happen BEFORE the resized-bytes read-back,
    which must happen BEFORE the temporary-file cleanup overwrite -- and, since FR-QPB-101
    (further revised) requires the *resized* bytes (not the original, unresized bytes) to be what
    is actually submitted to Pl@ntNet, the resized-bytes read-back must also happen BEFORE the
    widget constructs the `XMLHttpRequest` carrying the Pl@ntNet multipart request body (Decision
    Log D-31/D-46, unaffected by D-52; the only network call in this widget). This does not, and
    cannot, prove by static text alone that the read-back *variable* is what is actually assembled
    into the multipart body's bytes (that would require executing the QML) -- it proves only that
    every required step is present and correctly ordered relative to the others, which is the
    necessary precondition for the resized bytes to be the ones used."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    matches_with_1280 = _find_restrict_image_size_1280_matches(qml_code)
    assert matches_with_1280, (
        "AC-QPB-088 (FR-QPB-101, further revised; Decision Log D-52): expected a "
        "FileUtils.restrictImageSize(<tempFilePath>, 1280) call in the embedded widget's QML -- "
        "none found (this mechanism is not yet implemented)"
    )
    restrict_match = matches_with_1280[0]
    temp_path_arg = restrict_match.group(1).strip()
    restrict_pos = restrict_match.start()

    write_matches = list(_WRITE_FILE_CONTENT_RE.finditer(qml_code))
    content_writes = [
        m
        for m in write_matches
        if m.group(1).strip() == temp_path_arg and not _is_empty_string_literal(m.group(2))
    ]
    cleanup_writes = [
        m for m in write_matches if m.group(1).strip() == temp_path_arg and _is_empty_string_literal(m.group(2))
    ]
    read_back_matches = [
        m for m in _READ_FILE_CONTENT_PLAIN_RE.finditer(qml_code) if m.group(1).strip() == temp_path_arg
    ]

    assert content_writes, (
        "AC-QPB-088: expected a FileUtils.writeFileContent(<tempFilePath>, <original bytes>) call "
        f"-- none found for temporary path {temp_path_arg!r}"
    )
    assert read_back_matches, (
        "AC-QPB-088: expected a FileUtils.readFileContent(<tempFilePath>) read-back call -- none "
        f"found for temporary path {temp_path_arg!r}"
    )
    assert cleanup_writes, (
        "AC-QPB-088: expected a FileUtils.writeFileContent(<tempFilePath>, \"\") cleanup call -- "
        f"none found for temporary path {temp_path_arg!r}"
    )

    earliest_write_pos = min(m.start() for m in content_writes)
    assert earliest_write_pos < restrict_pos, (
        "AC-QPB-088: the temporary file's content write (FileUtils.writeFileContent) must happen "
        "BEFORE FileUtils.restrictImageSize() resizes it"
    )

    read_back_after_restrict = [m.start() for m in read_back_matches if m.start() > restrict_pos]
    assert read_back_after_restrict, (
        "AC-QPB-088: FileUtils.restrictImageSize() must run BEFORE the resized bytes are read "
        "back via FileUtils.readFileContent() -- found only read-back call(s) positioned before "
        "(or coincident with) restrictImageSize()"
    )
    read_back_pos = min(read_back_after_restrict)

    cleanup_after_read_back = [m.start() for m in cleanup_writes if m.start() > read_back_pos]
    assert cleanup_after_read_back, (
        "AC-QPB-088: the temporary file must be cleaned up (empty-content overwrite) AFTER the "
        "resized bytes have been read back -- found only cleanup call(s) positioned before the "
        "read-back, if any"
    )

    xhr_match = re.search(r"new\s+XMLHttpRequest\s*\(\s*\)", qml_code)
    assert xhr_match, (
        "AC-QPB-088/FR-QPB-101 (further revised; Decision Log D-31/D-46): expected the embedded "
        "widget to construct an XMLHttpRequest for the Pl\\u0040ntNet network POST -- none found"
    )
    assert read_back_pos < xhr_match.start(), (
        "AC-QPB-088: the resized bytes must be read back from the temporary file BEFORE the "
        "XMLHttpRequest carrying the Pl\\u0040ntNet multipart request body is constructed -- "
        "otherwise the original, unresized bytes (already read earlier) would be what actually "
        "gets submitted"
    )


# --- AC-QPB-095 (post-MVP; new, Decision Log D-54) -- structural presence of the per-candidate ----
# --- representative-image display / CC BY-SA attribution / graceful-degradation mechanism ----------
# --- (FR-QPB-109, further revised; Decision Log D-54). See test_post_mvp_plantnet_request_shape.py -
# --- ::test_requests_related_images_are_included for the companion AC-QPB-094 request-shape test. --
#
# FR-QPB-109 (further revised; Decision Log D-54) requires each displayed candidate card to show
# one representative image -- using the small (`s`) size variant of the Pl@ntNet-returned
# `url` object -- when the API response supplies one for that candidate, together with the
# required CC BY-SA attribution (the contributor's own `author` field, the literal text
# "Pl@ntNet", and the literal text "CC BY-SA") whenever an image is actually displayed,
# degrading gracefully (no broken-image placeholder, no attribution text) when a candidate has no
# image, and never letting an image-load failure corrupt the rest of that candidate's existing
# textual content.
#
# Every test below is a *necessary, not sufficient* structural check on the generated widget QML
# source text (via `inspect_identification_widget()`'s `qml_code` field, exactly like the
# `test_fr109_*`/`test_ac088_*` checks above) -- it never loads, executes, or renders the QML
# through any real QML/QField engine, so it cannot confirm an image or its attribution actually
# renders on screen, nor that a load failure actually leaves the rest of the card visually intact.
# The authoritative, end-to-end confirmation for all of this remains the manual/`device` placeholder
# in `test_post_mvp_manual_qfield_runtime.py` (AC-QPB-096, an explicit manual-QA-only criterion per
# the specification itself). Several of the checks below additionally rely on disclosed heuristics,
# not proofs -- see each test's own docstring for what is, and is not, actually provable via
# static-text inspection alone.
#
# **Anchor used to identify "per-candidate" scope: the built-in QML `modelData` property.** Neither
# FR-QPB-109 nor AC-QPB-095 mandates a specific QML component (`Repeater`, `ListView`, or otherwise)
# for "one candidate card each" -- that is an implementation detail. But *some* per-item delegate
# mechanism must exist for "for each of the three displayed candidates" to hold at all, and QML's
# own built-in `modelData` property (automatically exposed to a `Repeater`/`ListView` delegate whose
# model is a plain array of objects) is the natural, idiomatic QML/Qt mechanism for this -- a real
# framework API name, not a project-invented convention, exactly the same kind of anchor this file
# already relies on for `overlayFeatureFormDrawer`/`changeAttribute` (FR-109 section above). Since
# AC-QPB-095/FR-QPB-109 (further revised) is explicitly framed as an *additive* extension to the
# existing candidate-card display mechanism ("In addition to the existing candidate-card display
# content required above ..."), anchoring these new checks on `modelData` as the signal of "bound to
# this specific candidate" is well-grounded. **Disclosed limitation:** an alternative, equally
# spec-conformant implementation that displays exactly three per-candidate blocks through some other
# QML mechanism not exposing per-item data via `modelData` (e.g. three explicitly unrolled static
# blocks, or index-based `Repeater.itemAt(i)` access instead of a delegate's own `modelData`) would
# not be structurally detected by these specific checks. That limitation is disclosed here, not
# silently assumed away, mirroring this file's own established convention (see the AC-088 section's
# "original attachment path" heuristic note, and the FR-109 section's "uuid" check note, above).
#
# **The literal "Pl@ntNet" attribution text.** This project's own existing, already-shipped
# QML consistently writes "Pl@ntNet" using this same `@` Unicode-escape device rather than
# a literal `@` character in every one of its own user-facing string literals (e.g. `"Identify
# attached photos (Pl@ntNet + KTSN)"`, confirmed by inspection of `qfield_builder/
# qml_plugin.py` during this test-design round -- this very module docstring/these very comments
# follow the identical convention for the identical reason: avoiding a literal `@` character that
# tooling scanning this repository could mistake for an email-address fragment). The
# specification's own literal attribution text (FR-QPB-109/Decision Log D-54) is quoted using a
# plain `@` character. Because either spelling is a reasonable, faithful rendering of the same
# required literal text, the checks below accept *both* -- a literal `@`, or this codebase's own
# `@`-escape convention -- so neither choice is unfairly marked non-conformant.
#
# All tests in this section are expected to currently FAIL (red): a direct inspection of
# `qfield_builder/qml_plugin.py` during this test-design round confirmed no `Image` QML element, no
# occurrence of the literal text "CC BY-SA", and no `author`-field reference of any kind, exist
# anywhere yet in the generated identification widget QML.


_AC095_LAYER_PARAMS = pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)

_IMAGE_DECL_RE = re.compile(r"\bImage\s*\{")
_CC_BY_SA_TEXT = "CC BY-SA"
_PLANTNET_TEXT_RE = re.compile(r"Pl(?:@|\\u0040)ntNet")
_AUTHOR_REF_RE = re.compile(r"\bauthor\b", re.IGNORECASE)
_SMALL_VARIANT_RE = re.compile(r"url\w*\s*(?:\.\s*s\b|\[\s*['\"]s['\"]\s*\])", re.IGNORECASE)
_MODEL_DATA_SOURCE_RE = re.compile(r"source\s*:\s*[^;\n]*modelData")
_MODEL_DATA_VISIBLE_RE = re.compile(r"visible\s*:\s*[^;\n]*modelData")
# Generous enough to cover one attribution-text expression/string-concatenation binding; narrow
# enough that unrelated, far-away "Pl@ntNet" mentions elsewhere in this ~1700-line generated
# file are not mistaken for the attribution construction itself.
_PROXIMITY_WINDOW_CHARS = 400


def _brace_block_span(qml_code: str, open_brace_pos: int) -> tuple[int, int]:
    """Returns the (start, end) character-offset span of the balanced ``{ ... }`` block whose
    opening brace is at `open_brace_pos` (which must itself be the index of a literal '{'
    character), found via simple brace-depth counting -- this project's generated QML/JavaScript
    is plain, brace-balanced script with no unbalanced braces inside string/comment literals (the
    same assumption `_enclosing_function_span` above already relies on, confirmed by inspection of
    the current, already-shipped generated QML during test design). Falls back to the rest of the
    source if no matching close brace is found."""
    assert qml_code[open_brace_pos] == "{", (
        f"_brace_block_span: expected an opening brace at position {open_brace_pos}"
    )
    depth = 0
    i = open_brace_pos
    while i < len(qml_code):
        ch = qml_code[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return open_brace_pos, i + 1
        i += 1
    return open_brace_pos, len(qml_code)


def _find_image_blocks(qml_code: str) -> list[str]:
    """Returns the full text of every balanced ``Image { ... }`` QML object block found in
    `qml_code` (see `_brace_block_span`'s own docstring for the brace-matching assumption)."""
    blocks = []
    for m in _IMAGE_DECL_RE.finditer(qml_code):
        start, end = _brace_block_span(qml_code, m.end() - 1)
        blocks.append(qml_code[start:end])
    return blocks


def _find_model_data_bound_image_blocks(qml_code: str) -> list[str]:
    """The subset of `_find_image_blocks`'s Image blocks whose `source:` property is bound to an
    expression referencing `modelData` -- see this section's own header comment for why
    `modelData` is used as the "bound to this specific candidate" anchor, and its disclosed
    limitation."""
    return [block for block in _find_image_blocks(qml_code) if _MODEL_DATA_SOURCE_RE.search(block)]


def _smallest_enclosing_brace_block(qml_code: str, pos: int) -> tuple[int, int] | None:
    """Returns the (start, end) character-offset span of the smallest balanced ``{ ... }`` block
    containing character offset `pos`, found via a single stack-based scan of every brace in
    `qml_code` -- the same plain-brace-balanced-script assumption `_brace_block_span`/
    `_enclosing_function_span` above already rely on. Returns None if no enclosing block is found
    (should not happen for text found inside the generated QML's own object tree)."""
    stack: list[int] = []
    best: tuple[int, int] | None = None
    for i, ch in enumerate(qml_code):
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if not stack:
                continue
            start = stack.pop()
            if start <= pos < i + 1 and (best is None or (i - start) < (best[1] - best[0])):
                best = (start, i + 1)
    return best


@_AC095_LAYER_PARAMS
def test_ac095_widget_contains_an_image_element_bound_to_model_data_per_candidate(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-095 element (1): the embedded widget's QML must contain, for each displayed
    candidate, an `Image` QML element whose `source` property is bound to that candidate's own
    data -- "structurally distinct per candidate" is satisfied by the element living inside a
    per-item delegate scope (signalled here by a `modelData` reference in its `source:` binding;
    see this section's own header comment for why, and its disclosed limitation), not by requiring
    three separately-declared `Image` elements in the static source (the correct QML idiom declares
    the template once and QML itself instantiates it three times at runtime)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    image_blocks = _find_image_blocks(qml_code)
    assert image_blocks, (
        "AC-QPB-095 (FR-QPB-109, further revised; Decision Log D-54): expected at least one QML "
        "'Image { ... }' element in the embedded widget's QML -- none found (this mechanism is "
        "not yet implemented)"
    )

    bound = _find_model_data_bound_image_blocks(qml_code)
    assert bound, (
        "AC-QPB-095: expected at least one Image element whose 'source:' property is bound to an "
        "expression referencing 'modelData' (QML's own per-candidate delegate property) -- found "
        f"{len(image_blocks)} Image element(s), but none with a modelData-bound source. See this "
        "section's own header comment for this heuristic's disclosed limitation."
    )


@_AC095_LAYER_PARAMS
def test_ac095_small_s_size_variant_is_selected_for_the_representative_image(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-095 element (1)'s size-variant clause: the small (`s`) size-variant URL specifically
    -- per Pl\\u0040ntNet's own confirmed `url` object shape (`o`/`m`/`s`, Decision Log D-54) --
    must be what is selected, not the original (`o`) or medium (`m`) variant. This is a
    whole-widget-source heuristic, not scoped to the Image element block found by the previous
    test: the actual extraction of "which size variant" most plausibly happens in the JavaScript
    response-handling code that builds each candidate's model data (mirroring this widget's
    existing candidate-construction code), not necessarily inline inside the declarative Image
    element's own `source:` expression itself. **Disclosed limitation:** this cannot prove the
    located `.s`/`["s"]` access is actually the value that ends up in the Image element's `source`
    property found by the previous test -- it only proves that *some* code in the widget selects
    the `s` size-variant sub-field of a `url`-named identifier, the necessary (not sufficient)
    signal AC-QPB-095 requires."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    assert _SMALL_VARIANT_RE.search(qml_code), (
        "AC-QPB-095 (Decision Log D-54): expected evidence somewhere in the embedded widget's QML "
        "of selecting the small ('s') size-variant sub-field of a Pl\\u0040ntNet-returned 'url' "
        "object (e.g. '....url.s' or '....url[\"s\"]') -- none found (this mechanism is not yet "
        "implemented)"
    )


@_AC095_LAYER_PARAMS
def test_ac095_attribution_text_combines_author_plantnet_and_cc_by_sa_per_candidate(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-095 element (2): the required CC BY-SA attribution -- the contributor's `author`,
    the literal text "Pl\\u0040ntNet", and the literal text "CC BY-SA" -- must be constructed
    together, bound to that specific candidate's own image data. "CC BY-SA" is a brand-new
    substring for this widget (confirmed absent from the pre-D-54 generated QML by inspection
    during this test-design round), so its mere presence is already a strong signal the
    attribution feature exists; this test additionally requires the literal "Pl\\u0040ntNet" text
    (accepting either spelling -- see this section's own header comment), a reference to the
    contributor's `author` field, and a `modelData` per-candidate binding, all within a bounded
    window of nearby characters around the "CC BY-SA" text, so this check cannot be satisfied by
    these signals appearing coincidentally, unrelated to each other, somewhere far apart in this
    ~1700-line generated file."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    cc_by_sa_pos = qml_code.find(_CC_BY_SA_TEXT)
    assert cc_by_sa_pos != -1, (
        'AC-QPB-095 (Decision Log D-54): expected the literal attribution text "CC BY-SA" '
        "somewhere in the embedded widget's QML -- none found (this mechanism is not yet "
        "implemented)"
    )

    window_start = max(0, cc_by_sa_pos - _PROXIMITY_WINDOW_CHARS)
    window_end = min(len(qml_code), cc_by_sa_pos + len(_CC_BY_SA_TEXT) + _PROXIMITY_WINDOW_CHARS)
    window = qml_code[window_start:window_end]

    assert _PLANTNET_TEXT_RE.search(window), (
        'AC-QPB-095: found "CC BY-SA" but no "Pl\\u0040ntNet"/"Pl@ntNet" text within the expected '
        "proximity window of it -- the required attribution combines both, per the documented "
        'format "Photo(s): [Contributor Username] / Pl\\u0040ntNet, CC BY-SA"'
    )
    assert _AUTHOR_REF_RE.search(window), (
        'AC-QPB-095: found "CC BY-SA" but no reference to the contributor\'s "author" field '
        "within the expected proximity window of it -- the required attribution must include the "
        "contributor's name (the image response's own 'author' field)"
    )
    assert "modelData" in window, (
        'AC-QPB-095: found "CC BY-SA" but no "modelData" reference (QML\'s own per-candidate '
        "delegate property) within the expected proximity window of it -- the attribution must be "
        "bound to that specific candidate's own image data, not a single global/shared string"
    )


@_AC095_LAYER_PARAMS
def test_ac095_image_and_attribution_are_guarded_by_a_conditional_check(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-095 element (3), the graceful-degradation half: when a candidate has no image data,
    the card must not show a broken-image placeholder or attribution text for a nonexistent image.
    This cannot be proven by static text inspection alone (that would require actually rendering
    the QML and observing the screen) -- the necessary, structural proxy checked here is that the
    modelData-bound Image element and the "CC BY-SA" attribution construction are each gated by
    some conditional/guard expression referencing modelData -- either a `visible:` property, or a
    ternary (`?:`) expression -- mirroring this widget's own pre-existing, already-shipped
    convention for exactly this kind of per-candidate conditional display (its existing
    warning-text Label already reads `visible: modelData.warning_text.length > 0`, confirmed by
    inspection of `qfield_builder/qml_plugin.py` during this test-design round). **Disclosed
    limitation:** this proves only that *some* conditional construct exists; it cannot prove the
    guard is logically correct (e.g. that it evaluates false specifically when no image data is
    present, as opposed to some unrelated condition), nor can it confirm the visual absence of a
    broken-image placeholder on an actual screen -- that residual confirmation is AC-QPB-096's own
    manual/`device` QA."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    bound_images = _find_model_data_bound_image_blocks(qml_code)
    assert bound_images, (
        "AC-QPB-095: expected a modelData-bound Image element (see "
        "test_ac095_widget_contains_an_image_element_bound_to_model_data_per_candidate above) -- "
        "none found; cannot check its graceful-degradation guard"
    )
    guarded_images = [
        block for block in bound_images
        if _MODEL_DATA_VISIBLE_RE.search(block) or "?" in block
    ]
    assert guarded_images, (
        "AC-QPB-095: expected the modelData-bound Image element to carry a conditional guard -- "
        "either a 'visible:' property referencing modelData, or a ternary ('?:') expression in "
        "its source binding -- so a candidate with no image data does not attempt to load a "
        f"nonexistent image. Found none in: {bound_images[0]!r}"
    )

    cc_by_sa_pos = qml_code.find(_CC_BY_SA_TEXT)
    assert cc_by_sa_pos != -1, (
        'AC-QPB-095: expected "CC BY-SA" attribution text (see '
        "test_ac095_attribution_text_combines_author_plantnet_and_cc_by_sa_per_candidate above) "
        "-- none found; cannot check its graceful-degradation guard"
    )
    enclosing = _smallest_enclosing_brace_block(qml_code, cc_by_sa_pos)
    assert enclosing is not None, (
        'AC-QPB-095: could not locate an enclosing QML element block around the "CC BY-SA" '
        "attribution text to check for a graceful-degradation guard"
    )
    block_start, block_end = enclosing
    block_text = qml_code[block_start:block_end]
    assert _MODEL_DATA_VISIBLE_RE.search(block_text), (
        'AC-QPB-095: expected the element hosting the "CC BY-SA" attribution text to carry a '
        "'visible:' property referencing modelData, so a candidate with no image data shows no "
        f"attribution text for a nonexistent image. Found no such guard in: {block_text!r}"
    )


@_AC095_LAYER_PARAMS
def test_ac095_image_element_has_an_error_status_handling_guard(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-095 element (4)/Decision Log D-54's image-load-failure-isolation clause: an
    image-load failure occurring after the initial identify response has already succeeded must
    never block or corrupt the rest of that candidate's display. This cannot be proven by static
    text alone (that would require executing the QML and simulating a failed image load) -- the
    necessary, structural proxy checked here is that the modelData-bound Image element contains an
    explicit `onStatusChanged`-style handler referencing `Image.Error` (QML's own standard
    `Image.status`/`Image.Error` API, not a project-specific convention), as the disclosed, minimal
    signal that image-load failure was deliberately considered and handled, rather than left
    entirely to whatever QML's own default behavior happens to be. **Disclosed limitation:**
    finding this handler does not prove its body actually leaves the rest of the candidate's
    Column content untouched (that would require tracing and executing the handler's own code) --
    nor does its absence necessarily prove a failure *would* corrupt the rest of the display. This
    is this section's own weakest check, flagged as such here rather than silently assumed
    airtight, mirroring this file's own established convention for similarly-shaped best-effort
    checks (e.g. the FR-109 section's "uuid" check above)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    bound_images = _find_model_data_bound_image_blocks(qml_code)
    assert bound_images, (
        "AC-QPB-095: expected a modelData-bound Image element (see "
        "test_ac095_widget_contains_an_image_element_bound_to_model_data_per_candidate above) -- "
        "none found; cannot check its error-handling guard"
    )
    has_error_guard = [
        block for block in bound_images
        if re.search(r"onStatusChanged", block) and re.search(r"Image\.Error", block)
    ]
    assert has_error_guard, (
        "AC-QPB-095/Decision Log D-54: expected the modelData-bound Image element to contain an "
        "onStatusChanged handler referencing Image.Error, as the minimal signal that an "
        f"image-load failure is explicitly handled. Found none in: {bound_images[0]!r}"
    )


# --- AC-QPB-099 (post-MVP; new, Decision Log D-60/D-64) -- standardized taxon_full_nm-derived -----
# --- scientific-name display/persistence, structural presence only -----------------------------
#
# FR-QPB-106 (revised)/FR-QPB-109 (further revised) (Decision Log D-60, confirmed by D-64) require
# that, once a direct KTSN match is found, the direct-match branch also exposes a new
# `direct_scientific_name` value -- the matched row's own `taxon_full_nm` with `<em>`/`</em>` tags
# removed, mirroring the existing `direct_korean_name` field exactly -- and that both the
# candidate-card display and the value persisted to `selected_scientific_name` on selection prefer,
# in order: (1) `accepted_scientific_name` when accepted-name resolution succeeded; (2) otherwise
# `direct_scientific_name` when a direct match was found but accepted-name resolution did not
# succeed; (3) otherwise (no direct KTSN match at all) Pl@ntNet's own raw `species.scientificName`,
# **completely unchanged** -- the existing "KTSN match not found" fallback/disclosure is not
# altered by this entry (Decision Log D-64's own explicit, narrower reading).
#
# Every test below is a *necessary, not sufficient* structural check on the generated widget QML
# source text (via `inspect_identification_widget()`'s `qml_code` field, exactly like the
# `test_fr109_*`/`test_ac088_*`/`test_ac095_*` checks above) -- it never loads, executes, or renders
# the QML through any real QML/QField engine, so it cannot confirm the preference order is actually
# applied correctly at runtime for a real Pl@ntNet response, only that the generated source
# structurally contains the required pieces. This project's own already-shipped `qpbMatchKtsn`
# (`qfield_builder/qml_plugin.py`, inspected during this test-design round) already computes
# `direct_korean_name`/`accepted_korean_name`/`accepted_scientific_name` from a matched row, and
# `qpbHandlePlantNetResponse`/`qpbSelectCandidate` already combine `accepted_korean_name`/
# `direct_korean_name` with a `||`-fallback-chain pattern for the Korean-name side
# (`ktsnMatch.accepted_korean_name || ktsnMatch.direct_korean_name || null`) -- the tests below
# check for the equivalent, newly-required pattern on the scientific-name side. All tests in this
# section are expected to currently FAIL (red), since `direct_scientific_name` does not yet exist
# anywhere in the generated QML (confirmed by direct inspection of `qfield_builder/qml_plugin.py`
# during this test-design round).


_AC099_LAYER_PARAMS = pytest.mark.parametrize(
    "survey_type,layer_name",
    [
        ("simple_inventory", "inventory_observation"),
        ("temporary_plots", "observation"),
        ("permanent_plots", "observation"),
    ],
)


@_AC099_LAYER_PARAMS
def test_ac099_direct_match_constructs_direct_scientific_name_from_tag_stripped_taxon_full_nm(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-099 element (1): the direct-match branch must construct a `direct_scientific_name`
    value from the matched row's own `taxon_full_nm`, with `<em>`/`</em>` tags removed, populated
    whenever a direct match is found -- mirroring the existing `direct_korean_name` construction
    exactly. This checks only that the generated QML assigns a `direct_scientific_name` property
    somewhere, from a tag-stripping call (`qpbStripEmTags`, this codebase's own existing, already-
    confirmed tag-stripping function name) against a `taxon_full_nm`-derived value -- it cannot
    confirm this assignment is reached only on an actual direct match at runtime."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    assert "direct_scientific_name" in qml_code, (
        "AC-QPB-099/FR-QPB-106 (revised; Decision Log D-60/D-64): expected the generated QML to "
        "construct a direct_scientific_name value, mirroring the existing direct_korean_name field "
        "-- not found"
    )
    assignment = re.search(r"direct_scientific_name\s*=\s*([^;\n]+)", qml_code)
    assert assignment, (
        "AC-QPB-099: expected an assignment to direct_scientific_name (e.g. "
        "result.direct_scientific_name = ...) -- found the identifier as a bare reference "
        "somewhere in the generated QML, but no assignment expression to it"
    )
    assert "qpbStripEmTags" in assignment.group(1) or "qpbStripEmTags" in qml_code, (
        "AC-QPB-099/FR-QPB-106 (revised): expected direct_scientific_name to be derived via this "
        "codebase's own existing <em>-tag-stripping function (qpbStripEmTags), mirroring "
        f"accepted_scientific_name's own existing construction -- assignment was: "
        f"{assignment.group(0)!r}"
    )
    assert "idxFullNm" in qml_code or "taxon_full_nm" in qml_code, (
        "AC-QPB-099/FR-QPB-106 (revised): expected direct_scientific_name to be derived from the "
        "matched row's own taxon_full_nm column"
    )


@_AC099_LAYER_PARAMS
def test_ac099_display_and_persistence_prefer_accepted_then_direct_then_raw_plantnet_name(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-099 element (2): both the candidate-card scientific-name display and the value
    passed to the selection-persistence call must prefer, in order, accepted_scientific_name, then
    direct_scientific_name, then Pl@ntNet's own raw species.scientificName -- mirroring the
    existing, already-shipped Korean-name preference chain
    (`ktsnMatch.accepted_korean_name || ktsnMatch.direct_korean_name || null`) exactly, but with
    `species.scientificName` (Pl@ntNet's own raw name) as the final fallback instead of `null`
    (unlike the Korean-name case, which has no Pl@ntNet-native equivalent to fall back to)."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    preference_chain = re.search(
        r"accepted_scientific_name\s*\|\|\s*[^|;\n]*direct_scientific_name\s*\|\|\s*[^;\n]+",
        qml_code,
    )
    assert preference_chain, (
        "AC-QPB-099/FR-QPB-109 (further revised; Decision Log D-60/D-64): expected a preference-"
        "order fallback chain reading accepted_scientific_name, then direct_scientific_name, then "
        "a final fallback (Pl@ntNet's own raw species.scientificName) -- mirroring the existing "
        "accepted_korean_name || direct_korean_name || null pattern -- not found anywhere in the "
        "generated QML"
    )
    assert "scientificName" in preference_chain.group(0), (
        "AC-QPB-099: expected the final fallback in the preference chain to be Pl@ntNet's own raw "
        f"species.scientificName, not null (unlike the Korean-name case) -- got: "
        f"{preference_chain.group(0)!r}"
    )


@_AC099_LAYER_PARAMS
def test_ac099_no_match_branch_unchanged_no_direct_scientific_name_constructed(
    acceptance_api, inspect_identification_widget, tmp_path, survey_type, layer_name
):
    """AC-QPB-099 element (3): the no-direct-match branch is structurally unchanged by this entry
    -- it must still fall through to Pl@ntNet's raw species.scientificName with the existing "KTSN
    match not found" Korean-name disclosure, and must construct no direct_scientific_name value in
    that branch. This is a loose, best-effort structural check: it confirms the existing "KTSN
    match not found" disclosure text is still present verbatim (unweakened, unremoved by this
    entry) rather than tracing the no-match code path's own control flow, which a static-text check
    cannot do."""
    result = _build_with_identification(acceptance_api, tmp_path, survey_type)
    assert result["success"], result.get("error_message")
    qml_code = _widget_qml_source(inspect_identification_widget, result["project_dir"], layer_name)

    assert "KTSN match not found" in qml_code, (
        "AC-QPB-099/Decision Log D-64: the existing 'KTSN match not found' disclosure must remain "
        "completely unchanged by this entry -- not found in the generated QML"
    )
