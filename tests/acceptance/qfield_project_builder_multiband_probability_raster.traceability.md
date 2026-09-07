# Single multiband occurrence-probability raster — acceptance traceability

This file maps every `AC-MPR-*` criterion in
`specs/fieldbuild-kit-multiband-probability-raster.md`.  The artifact tests call only the
acceptance API seams documented in `qfield_project_builder/HARNESS_CONTRACT.md`; the runtime
tests inspect generated QML source and do not construct QGIS or launch QGIS/QField.

| Criterion | Executable coverage | Mode and boundary |
|---|---|---|
| AC-MPR-001 | `test_ac_mpr_001_species_inventory_uses_discovered_count_and_excludes_richness`; `test_ac_mpr_001_missing_empty_or_invalid_inventory_fails_closed` | auto; accepts the complete positive discovered inventory, excludes/reports richness, repeats successfully with a different positive discovered count, and verifies missing/empty/corrupt inventories leave no partial outputs |
| AC-MPR-002 | `test_ac_mpr_002_stack_band_count_matches_discovered_species_and_preserves_pixels` | auto through stack-inspection seam; dynamic band count, one-to-one source coverage, representative pixel/NoData equality, sentinel |
| AC-MPR-003 | `test_ac_mpr_003_index_is_nfc_normalized_unique_1_based_and_order_independent` | auto; JSON schema, NFC keys, unique 1-based bands, stable mapping under reversed enumeration, secret/photo/absolute-path exclusion |
| AC-MPR-004 | `test_ac_mpr_004_ac_mpr_005_project_has_one_relative_multiband_layer_and_no_species_tiffs` | auto through generated enabled Type 1, Type 2, and Type 3 projects; relative stack/index paths, manifest band count, no individual TIFFs, and no path/secret leaks asserted |
| AC-MPR-005 | `test_ac_mpr_004_ac_mpr_005_project_has_one_relative_multiband_layer_and_no_species_tiffs` | auto through project-inspection seam; exactly one valid raster layer and one tree node, shared datasource, no hidden/per-species layer |
| AC-MPR-006 | `test_ac_mpr_006_generation_returns_before_180_seconds_and_registers_once` | auto through the normal `build_project` acceptance seam; elapsed bound, no `worker_timeout`, registration count exactly one |
| AC-MPR-007 | `test_ac_mpr_007_runtime_looks_up_nfc_korean_name_and_samples_shared_stack_via_raster_value`; `test_ac_mpr_007_to_012_end_to_end_qfield_runtime_sampling_and_persistence` | structural auto plus explicitly skipped device QA; NFC Korean-name index lookup, shared stack, integer band, `raster_value` semantics, no filename/scientific/KTSN/filesystem fallback |
| AC-MPR-008 | `test_ac_mpr_008_ac_mpr_011_missing_mapping_and_sampler_failure_are_candidate_local`; skipped device QA | structural auto plus manual/device end-to-end confirmation; missing map/sampler failure retains candidates and write-back flow |
| AC-MPR-009 | `test_ac_mpr_009_zero_nodata_nonfinite_and_out_of_range_values_are_not_clamped`; skipped device QA | structural auto plus manual/device value cases; 0.0 valid, -9999/NoData/non-finite/out-of-range/out-of-extent unavailable, no clamping |
| AC-MPR-010 | `test_ac_mpr_010_authoritative_locations_are_type_specific_and_transform_to_epsg4326`; `test_ac_prf_013_type3_unsaved_plot_geometry_and_invalid_plot_on_qfield_device` | auto for authoritative expressions, live parent context, no Type 3 survey fallback, and EPSG:4326 transform; the shared iOS QField device gate confirms actual unsaved-plot sampling and unavailable invalid-plot behavior |
| AC-MPR-011 | `test_ac_mpr_008_ac_mpr_011_missing_mapping_and_sampler_failure_are_candidate_local`; skipped device QA | structural auto plus manual/device bounded identification/save confirmation for invalid location, mapping, read, and timeout failures |
| AC-MPR-012 | `test_ac_mpr_012_mixed_candidates_keep_individual_probability_and_persist_only_selected_value`; skipped device QA | structural auto plus manual/device mixed-candidate selection and relation-preservation confirmation |
| AC-MPR-013 | `test_ac_mpr_013_identification_disabled_does_not_add_probability_scope`; `test_ac_mpr_013_type4_has_no_probability_stack_layer_or_identification_target` | auto through normal build artifact inspection for disabled Types 1–3 and Type 4; no stack/index/layer/photo-identification target |
| AC-MPR-014 | `test_ac_mpr_014_copied_project_resolves_relative_stack_and_index_without_species_layers` | auto through copied-project inspection and injected candidate sampling seam; no original source directory or recreated species layers |

## Harness additions

The feature tests expect the acceptance API to expose these test seams; they are not product
requirements and may wrap any internal implementation:

- `validate_probability_raster_sources(source_dir: str) -> dict` returns `ok`, `error_code`,
  `message`, and `excluded_files`.
- `build_probability_stack(source_dir: str, project_dir: str) -> dict` returns `success`,
  `error_code`/`error_message`, and project-relative `stack_path`/`index_path` on success. It
  must promote outputs atomically.
- `inspect_probability_stack(stack_path: str, source_dir: str) -> dict` returns `valid`,
  `band_count`, `source_files_represented_once`, `pixel_crosscheck.values_match`,
  `pixel_crosscheck.nodata_match`, and `metadata.nodata`.
- `inspect_probability_project(project_dir: str) -> dict` returns `probability_layers`,
  `probability_layer_tree_nodes`, `reference_files`, `band_index_mapping`, and
  `absolute_path_leaks`; each layer includes `valid` and `datasource`.
- `sample_probability_candidate(project_dir: str, korean_name: str, location: dict) -> dict`
  returns `available` and, when available, a numeric `value`.

The existing `build_project(config, output_dir)` seam additionally accepts the test-only
`_test_probability_raster_source_dir` override so the acceptance suite can exercise inventories
with different positive discovered counts without changing the repository's authoritative source
directory. The normal production source remains the fixed
`storage/reference/rasters/bce_inverse_corrected_probability_maps/` location.

## Ambiguities and honest limits

- No fixed species count is part of the test oracle. Tests derive `discovered_species_count` from
  regular files matching the species filename pattern in the supplied source directory, then use
  that value for stack, index, manifest, and band-range assertions. A small hard-linked inventory
  is used only to prove that a different positive discovered count also succeeds without copying
  raster payloads; it does not pad the authoritative inventory to a predetermined count.
- The Python harness has no QField/QML runtime. Structural QML assertions are necessary but not
  sufficient for device behavior, so AC-MPR-007–012 also remain explicitly traceable to a skipped
  manual/device test with concrete runtime, transfer, selection, save, and reopen checks.
- The spec says the authoritative location is transformed to the stack CRS and separately calls
  out the existing EPSG:4326 transform boundary. The automatic assertion follows the existing
  project convention: authoritative project geometry is converted to WGS 84 before the runtime
  sampling expression; the device check must confirm the final `raster_value` call uses the stack
  CRS correctly if the source CRS is not EPSG:4326.
