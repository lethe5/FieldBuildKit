"""Section 13.6/13.7/13.8 — occurrence-probability lookup, candidate selection/persistence, and
on-device sampling (FR-QPB-108/109/111 revised; post-MVP guaranteed-manual baseline).

**Why every test in this file is a documented, skipped `device` placeholder, not an automated
check:** unlike Section 13.1's generated-artifact criteria (AC-QPB-069/070, covered in
`test_post_mvp_identification_plugin.py`) and Section 13.2/13.4/13.5's pure-rule validations
(covered in `test_post_mvp_plantnet_request_shape.py`/`test_post_mvp_ktsn_matching.py`), the
behavior described here genuinely only executes inside the embedded `QML Widget`, at runtime,
inside QField itself:

- FR-QPB-108's occurrence-probability sampling is performed by QML code reading EXIF GPS from an
  attached photo, transforming coordinates, and sampling a bundled raster file -- there is no
  Python desktop-build-pipeline component to this at all (unlike FR-QPB-112's file *bundling*,
  which is build-pipeline output and is already covered elsewhere).
- FR-QPB-109's candidate display, selection, and persistence is triggered by a user interacting
  with the embedded QML form and then writing the result back into the GeoPackage feature.
  **2026-08-24 update (Decision Log D-50/D-51):** real-device testing plus direct QGIS/QField
  source inspection has since *confirmed* (not merely "plausible but unconfirmed", unlike the
  raster-sampling case immediately below) a real, working write-back mechanism for a brand-new,
  not-yet-saved feature created via QField's own "Add feature" flow -- a pending write-back
  request file, a project-plugin `Timer` poll, `overlayFeatureFormDrawer.featureForm.model`,
  `changeAttribute()`, cleared by overwrite-not-`FileUtils.deleteFiles()` -- extended by Decision
  Log D-51 to govern manual identification entry exactly as it already governs real candidate
  selection. Write-back for an existing, already-saved feature (reopened later) is, by contrast, a
  **confirmed, permanent limitation** -- not an open uncertainty -- because QField's own
  `FeatureListForm.qml` never exposes its internal, per-feature `AttributeFormModel` outside
  itself. Neither branch is testable by this Python-only harness: this project has no QField/QML
  runtime capable of actually creating a feature via QField's "Add feature" digitizing flow,
  driving its `Timer`-based project-plugin polling loop, or reopening a previously-saved feature
  inside a live QField session, so both branches of AC-QPB-046 remain manual/`device` QA below --
  now confirmed-mechanism/confirmed-limitation placeholders, not "plausible but unconfirmed"
  placeholders. A separate, narrower, purely *structural* check (does the generated QML source
  literally contain the confirmed mechanism's constituent API calls?) is additionally covered,
  automatically, in `test_post_mvp_identification_plugin.py`'s `test_fr109_*` tests -- that is a
  necessary-not-sufficient static-source check, never a substitute for the real-device
  confirmation below.
- FR-QPB-111 (revised)/AC-QPB-072's on-device sampling explicitly carries a recorded,
  not-yet-confirmed technical-feasibility caveat (Decision Log D-36): whether QField's plugin API
  actually exposes raster pixel sampling to a `QML Widget` context is unconfirmed by any working
  example found by research to date. This is exactly the class of criterion this project's own
  established convention (AC-QPB-025/028's device-dependent, honestly-skipped tests) already
  handles -- documented here as required manual QA, not silently claimed as automated or silently
  omitted from traceability.

This project has no QField/QML runtime or test harness of any kind. These tests exist to keep
every criterion individually traceable (per this project's traceability discipline) and to give a
human tester concrete, spec-derived steps -- not to pretend automated coverage exists.

**2026-08-25 addendum (Decision Log D-54; AC-QPB-096; FR-QPB-109, further revised):** new
`test_ac096_representative_image_renders_on_screen_with_attribution_and_image_load_failure_does_not_corrupt_the_card`
below records the one part of the new per-candidate representative-image/CC BY-SA-attribution
feature that requires actually seeing an image render on a real device -- explicitly recorded as a
manual-QA-only placeholder by the specification itself (AC-QPB-096's own text), mirroring this
file's established `device`-marked, skipped-placeholder convention. The complementary, purely
structural checks (does the generated QML contain an `Image` element, the "CC BY-SA" text, a
graceful-degradation guard, and an image-load-error handler?) are automated separately in
`test_post_mvp_identification_plugin.py`'s `test_ac095_*` tests.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.device


# --- FR-QPB-108 / AC-QPB-044 -------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "AC-QPB-044 (FR-QPB-108) requires the embedded QML Widget to read real EXIF GPS from a "
        "real attached photo on a physical device and confirm the WGS 84 (EPSG:4326) coordinate "
        "is transformed to the probability raster's own CRS before sampling -- this cannot be "
        "automated by this harness (no QField/QML runtime exists in this project). "
        "\n\nManual QA steps: (1) On a physical iOS or Android device running QField, open a "
        "generated project with the identification subsystem enabled. (2) Attach a photo with "
        "known, real EXIF GPS coordinates (in WGS 84) to a Type 1 inventory_observation, or a "
        "Type 2/3 observation, feature. (3) Trigger the embedded 'Identify attached photos' "
        "action. (4) Confirm the reported occurrence-probability sample corresponds to the "
        "correct raster pixel for that coordinate after reprojection to the raster's CRS (verify "
        "independently, e.g. by opening the same raster and coordinate in QGIS Desktop and "
        "comparing the sampled value)."
    )
)
def test_ac044_exif_gps_is_transformed_to_the_raster_crs_before_sampling():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- FR-QPB-108 / DR-QPB-070 / AC-QPB-045 / AC-QPB-049 / AC-QPB-050 ----------------------------


@pytest.mark.parametrize(
    "scenario",
    [
        "sampled_value_is_exactly_negative_9999_displays_no_probability_data_not_zero_or_a_probability",
        "coordinate_outside_raster_extent_displays_no_probability_data",
        "missing_raster_file_displays_no_probability_data",
        "no_photo_gps_displays_no_photo_gps_message_and_still_shows_top_three_candidates",
        "sampled_value_of_exactly_0.0_is_displayed_as_a_valid_probability_not_no_probability_data",
        "sampled_value_outside_0_to_1_and_not_negative_9999_is_a_validation_warning_never_clamped",
    ],
)
@pytest.mark.skip(
    reason=(
        "AC-QPB-045/049/050 (FR-QPB-108, DR-QPB-070) require exercising the embedded QML Widget's "
        "occurrence-probability display logic against real (or deliberately contrived) raster/"
        "EXIF conditions on a physical device -- not automatable by this harness. "
        "\n\nManual QA steps per scenario: "
        "(a) -9999 case: attach a photo whose GPS falls inside a bundled raster's NoData region "
        "(sampled value exactly -9999); confirm the UI shows 'No probability data', never a "
        "probability or a literal zero. "
        "(b) out-of-extent case: attach a photo whose GPS falls outside every bundled raster's "
        "extent; confirm 'No probability data' is shown. "
        "(c) missing-raster case: use a candidate Korean name with no matching "
        "bce_inverse_corrected_probability_{name}.tif file present; confirm 'No probability data'. "
        "(d) no-GPS case: attach a photo with no EXIF GPS; confirm the message is the no-GPS "
        "variant ('No photo GPS -- probability unavailable') and the top-three candidates are "
        "still shown. "
        "(e) 0.0 case: attach a photo whose GPS samples to exactly 0.0; confirm this is displayed "
        "as a valid probability (e.g. '0%'), never as 'No probability data'. "
        "(f) out-of-range case: this requires a deliberately corrupted/test raster containing a "
        "value outside 0.0-1.0 that is not exactly -9999; confirm the UI records a validation "
        "warning and never silently clamps the value into 0.0-1.0."
    )
)
def test_ac045_ac049_ac050_probability_display_rules(scenario):
    raise AssertionError("should never run while skipped -- see skip reason")


# --- FR-QPB-111 (revised) / AC-QPB-072 (on-device sampling; feasibility caveat, D-36) ----------


@pytest.mark.skip(
    reason=(
        "AC-QPB-072 requires confirming the embedded QML Widget can sample the bundled "
        "reference/rasters/bce_inverse_corrected_probability_maps/*.tif files directly on-device, "
        "while the field device is disconnected from the desktop -- not automatable by this "
        "harness, and explicitly recorded (Decision Log D-36) as a *plausible but not yet "
        "confirmed* QField plugin-API capability, not a settled fact. "
        "\n\nManual QA steps: (1) Build a project with identification enabled and transfer the "
        "complete generated folder (including reference/rasters/) to a physical device. "
        "(2) Disconnect the device from any network/desktop connection. (3) Attach a photo with "
        "real EXIF GPS and trigger 'Identify attached photos'. (4) Confirm a probability sample "
        "is produced using only the bundled on-device raster files (no round trip to a desktop), "
        "following the same NoData/-9999/range/out-of-extent rules as AC-QPB-045/049/050. "
        "(5) If QField's plugin API does not expose raster pixel sampling to a QML Widget context "
        "at all, this criterion cannot be satisfied on-device -- report that as a concrete "
        "implementer finding per Decision Log D-36, rather than silently falling back to a "
        "desktop-only sampling path without disclosure."
    )
)
def test_ac072_on_device_probability_sampling_while_disconnected_from_desktop():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- FR-QPB-109 (further revised; Decision Log D-50/D-51) / AC-QPB-046 (further revised; --------
# --- Decision Log D-50) -- candidate display, selection, and persistence -------------------------
#
# AC-QPB-046 is now two independently testable branches by feature save-state (Decision Log D-50,
# further revised by D-51). Both remain manual/`device` QA -- this project has no QField/QML
# runtime capable of actually driving QField's "Add feature" digitizing flow, its project-plugin
# `Timer` poll, or reopening a previously-saved feature inside a live QField session -- but they
# are no longer "plausible but unconfirmed" placeholders as the pre-D-50 version of this test was:
# branch (a) now names a real, real-device-confirmed mechanism the human tester is confirming
# actually works end-to-end (not merely hoping it might); branch (b) is confirming a *confirmed,
# permanent limitation*, not an open question -- a "PASS" for branch (b) below means the disclosed
# not-saved message appeared and the saved value was untouched, exactly as intended, not a defect.
# See test_post_mvp_identification_plugin.py's test_fr109_* tests for the complementary, automatic,
# purely structural check (does the generated QML source literally contain this mechanism's
# constituent API calls?) -- necessary, not sufficient, and never a substitute for the real-device
# confirmation these two tests require.


@pytest.mark.skip(
    reason=(
        "AC-QPB-046(a) (FR-QPB-109, further revised; Decision Log D-50/D-51): for a brand-new, "
        "not-yet-saved feature created via QField's own 'Add feature' digitizing flow, the "
        "confirmed, real write-back mechanism (a pending write-back request written via "
        "FileUtils.writeFileContent(); the <project_slug>.qml project plugin polling via a "
        "short-interval Timer; locating the live AttributeFormModel via "
        "overlayFeatureFormDrawer.featureForm.model; confirming the pending request's UUID "
        "matches the current feature; applying it via changeAttribute(name, value); clearing the "
        "request file afterward by overwriting it with empty content, never "
        "FileUtils.deleteFiles()) must actually persist the result into the real GeoPackage "
        "record, for both a real candidate selection AND a manual identification entry (Decision "
        "Log D-51 extends the mechanism to manual entry, not just candidate selection) -- not "
        "automatable by this harness (no QField/QML runtime exists in this project, and this "
        "project's hard QGIS-isolation rule bars constructing a QgsApplication or launching any "
        "interactive QGIS/QField session for this purpose). "
        "\n\nManual QA steps -- Sub-case (i), real candidate selection: "
        "(1) On a physical iOS or Android device running QField, open a project with "
        "identification enabled that was transferred to the device. "
        "(2) Using QField's own 'Add feature' action (not editing an existing, already-saved "
        "feature), create a brand-new inventory_observation (Type 1) or observation (Type 2/3) "
        "feature; do not save it yet. "
        "(3) Attach a photo and trigger the embedded 'Identify attached photos' action. "
        "(4) Select one of the three displayed Pl@ntNet candidates. Confirm the selected value "
        "(scientific/Korean name, KTSN when available) appears immediately in the still-open, "
        "unsaved form -- i.e. the write-back applied live, before any save action. "
        "(5) Perform the normal QField save action (the checkmark) to save the new feature. "
        "(6) Transfer the project back and reopen its GeoPackage (e.g. in QGIS Desktop). Confirm: "
        "only the intended observation row exists/changed; its fid is a normal new row; every "
        "UUID foreign-key relation (survey_id/observation_id/etc.) is correctly populated and "
        "intact; selected_korean_name/selected_scientific_name/selected_ktsn (when available)/"
        "identification_score/occurrence_probability (when available) were persisted; "
        "identification_status is exactly 'complete' (never 'manual'); identification_timestamp/"
        "identification_model_version (DR-QPB-052/053) are populated when the API response "
        "supplied them, NULL otherwise. "
        "\n\nManual QA steps -- Sub-case (ii), manual identification entry: "
        "(7) Repeat steps (1)-(3) for a second brand-new 'Add feature' session. Reject all three "
        "displayed candidates and type a scientific and/or Korean name manually, then confirm the "
        "manual entry. Confirm the typed value appears immediately in the still-open, unsaved "
        "form. "
        "(8) Save the feature (checkmark), transfer back, and reopen the GeoPackage. Confirm: "
        "selected_korean_name/selected_scientific_name were persisted as typed; "
        "identification_status is exactly 'manual' (never 'complete', per the unchanged Decision "
        "Log D-38/D-43 rule and AC-QPB-078); identification_score, occurrence_probability, and "
        "identification_model_version are all NULL -- never inherited or fabricated from a "
        "candidate. "
        "\n\nIf, on the real device actually used for this QA pass, either sub-case fails to "
        "persist (i.e. the disclosed not-saved message appears instead, or the saved GeoPackage "
        "value is unchanged), report this as a concrete conformance defect against FR-QPB-109 "
        "(further revised; Decision Log D-50/D-51) -- Decision Log D-50 recorded this mechanism as "
        "already confirmed working end-to-end on the specific device/QField version tested during "
        "specification work (QField 4.2.4), not as certain to work identically on every device/"
        "QField version; a regression or version-specific gap found here is a real, reportable "
        "finding, not something this placeholder pre-judges as impossible."
    )
)
def test_ac046a_brand_new_unsaved_feature_write_back_persists_for_candidate_selection_and_manual_entry():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.skip(
    reason=(
        "AC-QPB-046(b) (FR-QPB-109, further revised; Decision Log D-50): for an existing, "
        "already-saved feature reopened later (not created in the same 'Add feature' session), "
        "write-back is a confirmed, permanent limitation -- QField's own FeatureListForm.qml "
        "never exposes its internal, per-feature AttributeFormModel outside itself, so no "
        "mechanism reachable from a QField project plugin can write to that feature's live "
        "attribute-editing model, for either a candidate selection or a manual entry. This is the "
        "intended, final behavior for this case, not a gap awaiting a future fix -- confirming it "
        "is still manual/device QA (no QField/QML runtime exists in this project), but a 'PASS' "
        "here means the disclosed message appeared and the saved value was untouched, not that a "
        "defect was found. "
        "\n\nManual QA steps: "
        "(1) On a physical iOS or Android device running QField, open a project with "
        "identification enabled. Use a feature that was already saved in a previous session -- "
        "for example, reopen the very feature saved in "
        "test_ac046a_brand_new_unsaved_feature_write_back_persists_for_candidate_selection_and_manual_entry's "
        "own manual QA steps, after closing and reopening the project (or the app), so it is "
        "genuinely 'reopened later', not part of the same 'Add feature' session. Record its "
        "current selected_korean_name/selected_scientific_name/selected_ktsn/"
        "identification_score/occurrence_probability/identification_status/"
        "identification_timestamp/identification_model_version values before proceeding. "
        "(2) Trigger the embedded 'Identify attached photos' action on this existing feature "
        "(attaching a new photo first if none is attached yet). "
        "(3) Select one of the three displayed candidates. Confirm the application's disclosed "
        "'not saved' message appears (the informational message stating the selection was "
        "recorded on screen but not saved because attribute write-back is unavailable in this "
        "case; its exact wording is implementation-authored UI copy, not dictated verbatim by the "
        "specification, per the existing Decision Log D-27 convention). "
        "(4) Reopen the project's GeoPackage (e.g. in QGIS Desktop) and confirm every value "
        "recorded in step (1) is completely unchanged -- the attempted candidate selection had no "
        "effect on the saved record. "
        "(5) Repeat steps (2)-(4), this time rejecting all three candidates and confirming a "
        "manual entry instead of selecting a candidate. Confirm the same disclosed message "
        "appears and the same previously-saved values remain unchanged afterward. "
        "(6) Do not report either outcome in this test as a defect: per Decision Log D-50, this is "
        "the correct, intended, confirmed-permanent-limitation behavior for this case. If, "
        "instead, either attempt is ever found to silently succeed in changing the saved "
        "GeoPackage record without disclosure, or to crash/corrupt the record, THAT would be a "
        "genuine, reportable conformance defect."
    )
)
def test_ac046b_existing_already_saved_feature_write_back_is_a_confirmed_permanent_limitation():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.skip(
    reason=(
        "FR-QPB-109 additionally requires persisting an 'identification timestamp/API-model "
        "version when available' alongside the selected candidate. This project's approved "
        "schema (Section 7/8 of specs/qfield-project-builder.md) defines no column for either "
        "an identification timestamp or an API-model version anywhere in the Type 1/2/3 "
        "observation schemas (only selected_korean_name/selected_scientific_name/selected_ktsn/"
        "identification_score/occurrence_probability/identification_status exist). This is a "
        "genuine specification gap -- not a test-design ambiguity being silently resolved here -- "
        "flagged in the traceability file's ambiguity report rather than tested against an "
        "invented column. This placeholder exists so the gap remains individually traceable to "
        "FR-QPB-109/AC-QPB-046, rather than being silently dropped."
    )
)
def test_fr109_timestamp_and_model_version_persistence_not_testable_pending_schema_clarification():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- AC-QPB-040 (residual, display-rendering half only) ----------------------------------------


@pytest.mark.skip(
    reason=(
        "AC-QPB-040's request-count half (exactly 3 results requested via nb-results=3) and its "
        "response-ordering half (the real Pl@ntNet API already returns results in descending-"
        "score order, live-confirmed during test design) are both covered offline/live in "
        "test_post_mvp_plantnet_request_shape.py. The one remaining, genuinely untestable-here "
        "half is that the embedded QML Widget actually *renders* the three candidate cards "
        "on-screen in that same descending-score order without re-shuffling them -- a QML/UI "
        "rendering behavior with no Python-observable artifact. "
        "\n\nManual QA steps: trigger 'Identify attached photos' on a physical device for a photo "
        "that yields three distinguishable-confidence candidates; confirm the three displayed "
        "candidate cards appear in descending Pl@ntNet-score order on-screen."
    )
)
def test_ac040_displayed_candidate_card_order_matches_descending_score():
    raise AssertionError("should never run while skipped -- see skip reason")


# --- AC-QPB-096 (post-MVP; new, Decision Log D-54) -- representative-image rendering/attribution --
# --- and image-load-failure isolation, on a real device/QGIS Desktop -------------------------------
#
# AC-QPB-096 is, per the specification's own text, "verifiable only via real-device/real-QGIS-
# Desktop manual QA -- no QField/QML runtime exists in this project's automated harness -- and is
# not asserted as already confirmed by this entry." The complementary, purely structural checks
# (does the generated QML source contain an Image element, the CC BY-SA attribution text, a
# graceful-degradation guard, and an image-load-error handler?) are automated, separately, in
# `test_post_mvp_identification_plugin.py`'s `test_ac095_*` tests -- necessary, not sufficient, and
# never a substitute for the real-device confirmation this placeholder requires.


@pytest.mark.skip(
    reason=(
        "AC-QPB-096 (FR-QPB-109, further revised; Decision Log D-54) requires confirming, on a "
        "real device (or QGIS Desktop, subject to the existing QField-vs-QGIS-Desktop "
        "rendering-scope caveat, Decision Log D-46 -- the embedded 'Identify attached photos' QML "
        "Widget is expected to fail to load/render at all in QGIS Desktop specifically once "
        "FR-QPB-101's QField-native file-read mechanism is adopted, so this manual QA is "
        "realistically only exercisable on a real QField device) with network connectivity, that "
        "(a) a real Pl\\u0040ntNet-supplied representative image actually renders on screen for "
        "each candidate the response supplied one for, alongside its required CC BY-SA "
        "attribution text, and (b) an isolated, subsequent failure to load one candidate's image "
        "does not block or corrupt the rest of that candidate's displayed content -- not "
        "automatable by this harness (no QField/QML runtime exists in this project, and this "
        "project's hard QGIS-isolation rule bars constructing a QgsApplication or launching any "
        "interactive QGIS/QField session for this purpose). "
        "\n\nManual QA steps: "
        "(1) Build a project for any survey type with identification_enabled=True, embedding (or "
        "having the tester supply at runtime) a real Pl\\u0040ntNet API key. Transfer the "
        "generated project to a physical iOS or Android device running QField (or, subject to the "
        "Decision Log D-46 caveat above, open it in the exact supported QGIS Desktop version). "
        "(2) Confirm the device/desktop has active network connectivity. "
        "(3) Attach one or more photos of a plant reasonably likely to be well-represented in "
        "Pl\\u0040ntNet's own image database (e.g. a common, frequently-photographed species) to a "
        "Type 1 inventory_observation or Type 2/3 observation feature -- note that whether any "
        "specific candidate's response actually includes a related image cannot be guaranteed in "
        "advance by this placeholder; choose a species/photo combination reasonably likely to "
        "produce at least one candidate with an image, and record which candidate(s) did or did "
        "not receive one. "
        "(4) Trigger the embedded 'Identify attached photos' action and wait for the three "
        "candidate cards to render. "
        "(5) For each candidate whose Pl\\u0040ntNet response entry included a related image, "
        "confirm: the small-size representative image actually renders visibly on screen "
        "(not a broken-image icon, not a blank/placeholder box); and the required attribution "
        "text is visibly shown alongside or together with it, combining the contributor's name, "
        "the literal text 'Pl\\u0040ntNet', and the literal text 'CC BY-SA' (matching the "
        "documented format 'Photo(s): [Contributor Username] / Pl\\u0040ntNet, CC BY-SA'). "
        "(6) For each candidate whose response did NOT include a related image, confirm: no "
        "broken-image placeholder of any kind is shown for that candidate; no attribution text is "
        "shown for that candidate; and that candidate's other existing display content "
        "(scientific name, confidence, Korean name, KTSN, occurrence probability, warning text) "
        "is fully present and unaffected. "
        "(7) For at least one candidate whose image rendered successfully in step (5), force an "
        "isolated image-load failure for a *subsequent* identification run -- e.g. re-trigger "
        "'Identify attached photos' on a new photo of the same or a different plant, then disable "
        "network connectivity (airplane mode) immediately after the candidate cards appear but "
        "before their images finish loading, so the identify response itself already succeeded "
        "but the image fetch that follows it fails. Confirm that candidate's existing textual "
        "content (scientific name, confidence, Korean name, KTSN, occurrence probability, warning "
        "text) remains fully displayed and unaffected by the failed image load -- it must not be "
        "hidden, blanked, or otherwise corrupted. "
        "(8) If any part of steps (5)-(7) fails to hold, report this as a concrete conformance "
        "defect against FR-QPB-109 (further revised; Decision Log D-54)/AC-QPB-096, rather than "
        "assuming success -- this placeholder does not pre-judge the outcome either way."
    )
)
def test_ac096_representative_image_renders_on_screen_with_attribution_and_image_load_failure_does_not_corrupt_the_card():
    raise AssertionError("should never run while skipped -- see skip reason")
