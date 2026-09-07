# Probability-raster generation timeout traceability

Specification: [`specs/fieldbuild-kit-probability-raster-generation-timeout.md`](../../specs/fieldbuild-kit-probability-raster-generation-timeout.md)

Acceptance tests: [`qfield_project_builder/test_probability_raster_generation_timeout.py`](qfield_project_builder/test_probability_raster_generation_timeout.py)

The suite is deterministic on macOS.  It injects a fake runtime/QGIS project-writer boundary into
the existing `acceptance_api.build_project()` seam, uses checked-in reference fixtures, and reads
generated QML/source contracts.  It never constructs `QgsApplication`, starts QGIS, starts QField,
opens a browser, reads EXIF, or makes a network request.

| Criterion | Automated coverage |
|---|---|
| AC-PRG-001 | `test_ac_prg_001_small_reference_rasters_are_copied_byte_for_byte_and_sorted` and `test_ac_prg_001_full_reference_fixture_has_2532_files_and_is_fully_bundled` verify complete raster copying, Unicode-safe names, and byte identity. |
| AC-PRG-002 | `test_ac_prg_002_qgis_project_builder_has_no_probability_raster_registration_or_group` verifies the PyQGIS build path has no per-TIFF registration or probability layer-tree group. |
| AC-PRG-003 | `test_ac_prg_003_fake_bridge_generation_succeeds_without_worker_timeout` exercises the existing build seam with a fake QGIS boundary and rejects `worker_timeout`; `test_ac_prg_003_build_manifest_lists_every_raster_as_project_relative_reference` verifies the generated manifest list. |
| AC-PRG-004 | `test_ac_prg_003_build_manifest_lists_every_raster_as_project_relative_reference` and `test_ac_prg_012_identification_enabled_build_keeps_worker_and_raster_files_outside_qgis_tree` verify project-relative persistence after the fake generated-project flow. |
| AC-PRG-005 | `test_ac_prg_006_types_1_to_3_keep_authoritative_location_and_direct_worker_sampler` verifies the project-local WorkerScript/FileUtils path and Type 1/2/3 location expressions without a QGIS raster layer. |
| AC-PRG-006 | `test_ac_prg_006_types_1_to_3_keep_authoritative_location_and_direct_worker_sampler` checks Type 1 inventory, Type 2 survey, and Type 3 live/persisted plot-only expressions; it rejects Type 3 survey fallback variables. The shared `test_ac_prf_013_type3_unsaved_plot_geometry_and_invalid_plot_on_qfield_device` remains the iOS QField runtime proof for unsaved plot geometry. |
| AC-PRG-007 | `test_ac_prg_007_missing_or_invalid_candidate_is_unavailable_without_dropping_candidates` checks candidate-local unavailable states and continued candidate-job handling. |
| AC-PRG-008 | `test_ac_prg_005_worker_script_retains_tiff_lzw_msb_first_decoder_and_pixel_validation` checks the supported float32 TIFF/LZW MSB-first decoder, strip-reset, and value validation contract. |
| AC-PRG-009 | `test_ac_prg_009_sampling_is_async_watchdog_bounded_and_has_no_sync_qgis_expression_path` checks WorkerScript messaging, the three-second watchdog, and absence of synchronous `raster_value()` use. |
| AC-PRG-010 | `test_ac_prg_010_location_failure_uses_no_exif_gps_or_photo_metadata_fallback` checks authoritative-geometry-only location handling and fail-closed null behavior. |
| AC-PRG-011 | `test_ac_prg_011_type4_has_no_identification_target_or_probability_specific_schema_fields` verifies Type 4 remains outside photo identification/probability sampling. |
| AC-PRG-012 | `test_ac_prg_004_generated_manifest_has_no_absolute_secret_or_photo_paths` and `test_ac_prg_012_identification_enabled_build_keeps_worker_and_raster_files_outside_qgis_tree` verify no-secret/no-photo-path and existing generated asset boundaries. |

## Deliberate boundary

The full 2,532-file test uses a temporary reference scaffold whose raster directory is a read-only
symlink to the checked-in `storage/reference` fixture; the generated project receives regular
byte-for-byte copies.  The fake QGIS writer intentionally does not claim to validate a real `.qgs`
round-trip.  Real QGIS project reopen, QField WorkerScript execution, pixel values on device, and
the 180-second wall-clock measurement remain implementation/reviewer or manual runtime gates.

No production code, approved specification, or shared harness contract is changed by this round.
