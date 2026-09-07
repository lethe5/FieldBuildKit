# Identification probability raster fallback traceability

Specification: [`specs/fieldbuild-kit-identification-probability-raster-fallback.md`](../../specs/fieldbuild-kit-identification-probability-raster-fallback.md)

Acceptance tests: [`qfield_project_builder/test_identification_probability_raster_fallback.py`](qfield_project_builder/test_identification_probability_raster_fallback.py)

The suite is deterministic on macOS. It uses the generated identification QML and the existing
authoritative-location expression builder as injectable/source-contract seams. It does not start
QField, create a QGIS application, inspect EXIF, read a real photo, access the network, or require
an installed raster-sampling capability. Runtime pixel values and device save/reopen remain
manual/device verification boundaries.

| Criterion | Automated coverage |
|---|---|
| AC-PRF-001 | `test_ac_prf_001_008_012_sampling_uses_the_candidate_raster_and_real_location_seam` and `test_ac_prf_001_type1_uses_inventory_observation_geometry_only` verify the species TIFF mapping, sampler arguments, candidate flow, and Type 1 geometry source. |
| AC-PRF-002 | `test_ac_prf_002_006_missing_raster_is_candidate_local_and_does_not_drop_candidates` verifies unavailable probability is retained on the candidate while the candidate model remains populated. |
| AC-PRF-003 | `test_ac_prf_003_011_sampling_capability_errors_are_bounded_and_non_blocking` verifies the sampler's candidate-local failure state, the WorkerScript message handler, and no unbounded sampler retry. |
| AC-PRF-004 | `test_ac_prf_004_007_010_location_failure_and_unavailable_probability_keep_writeback_flow` verifies null location handling and continued candidate/write-back flow without metadata fallback. |
| AC-PRF-005 | `test_ac_prf_005_invalid_raster_values_are_not_fabricated_as_zero` verifies NoData/null and valid-range handling without clamping or zero fabrication. |
| AC-PRF-006 | `test_ac_prf_002_006_missing_raster_is_candidate_local_and_does_not_drop_candidates` verifies per-candidate probability fields and preservation of the complete candidate model. |
| AC-PRF-007 | `test_ac_prf_004_007_010_location_failure_and_unavailable_probability_keep_writeback_flow` verifies Korean-name write-back, probability propagation, and candidate-flow cleanup. |
| AC-PRF-008 | `test_ac_prf_008_013_type2_uses_survey_and_type3_uses_live_or_persisted_plot_only` and the parametrized sampler-seam test verify Type 2 survey and Type 3 plot-only location contracts; the structural check rejects both persisted and live-survey fallback variables. |
| AC-PRF-009 | `test_ac_prf_009_type4_has_no_photo_identification_target` verifies the Type 4 community boundary. |
| AC-PRF-010 | `test_ac_prf_004_007_010_location_failure_and_unavailable_probability_keep_writeback_flow` and `test_ac_prf_010_015_paths_are_relative_and_do_not_embed_photo_or_secret_data` verify authoritative geometry only and no EXIF/device/photo metadata location use. |
| AC-PRF-011 | `test_ac_prf_003_011_sampling_capability_errors_are_bounded_and_non_blocking` verifies caught capability errors, localized non-blocking status, and the `qpbExpireProbabilitySamples` watchdog's 3-second timeout/timed-out contract. |
| AC-PRF-012 | `test_ac_prf_001_008_012_sampling_uses_the_candidate_raster_and_real_location_seam` verifies every candidate passes through species-specific probability formatting and retains the resulting value/state. |
| AC-PRF-013 | `test_ac_prf_008_013_type2_uses_survey_and_type3_uses_live_or_persisted_plot_only` is the automated generated-expression guard for live parent context and no Type 3 survey fallback. `test_ac_prf_013_type3_unsaved_plot_geometry_and_invalid_plot_on_qfield_device` is the explicit iOS QField acceptance script for the unsaved nested `site → plot → survey → observation` flow, distinct plot/survey controls, unavailable invalid-plot result, and non-blocking candidate/save behavior. |

## Coverage boundary

The test suite intentionally does not claim that a real QField build can open a bundled TIFF or
that a pixel value is correct. It does, however, require the approved asynchronous source
contract: `qpbSampleProbabilityRaster` creates a request, sends the candidate TIFF bytes and
authoritative coordinates to the project-relative WorkerScript, and returns a request ID; the
generated widget contains the WorkerScript `onMessage` handler and the candidate-local watchdog.
Implementer/reviewer stages must preserve this source contract and add implementation-level tests
for the actual sampling seam where available; real QField sampling, candidate selection,
persistence, and save/reopen remain device/manual checks from the approved specification.

The source contract cannot prove which live QField nested-form object supplies unsaved plot
geometry. That runtime binding, the sampled pixel value, and the unavailable result when a valid
survey geometry is present are intentionally covered only by AC-PRF-013's device script.
