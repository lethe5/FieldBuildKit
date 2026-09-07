# D-95 canonical KTSN reference migration traceability

Status: D-95 implementation traceability. The implementation remains uncommitted; this document
records the acceptance mappings and the non-GUI/package-boundary verification for this round.

The real fixture is `storage/reference/tables/Rpt_2026-08-29_List.xlsx` (SHA-256
`2a7d81c7b032851ed1e260f08607296bc11519f6fa50a4909649269ab693c963`, 973,891 bytes). It has
sheet `Data Sheet`, row 1/2 headers, data rows 3–8044, 8,042 rows total, 4,673 `정명`, 3,369
`이명`, and no non-`관속식물류` row. The old CSV and 2025 workbook are intentionally treated as
legacy/mismatched inputs, never as fallback sources.

| Test ID | Requirement / acceptance criterion | Test location | Automation |
|---|---|---|---|
| D95-UNIT-001 | R-equivalent whitespace/parenthesis cleanup, first-genus exclusion, authority marker extraction, empty authority, raw-value non-replacement | `tests/unit/test_canonical_ktsn_contract.py::test_r_equivalent_cleaner_is_pure_and_does_not_replace_raw_name`; `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac139_r_equivalent_name_normalization_and_authority_extraction` | unit + pure acceptance |
| D95-UNIT-002 | Exact URL prefix only; KTSN remainder preserved as text including leading zero; invalid prefix/empty remainder rejected | `test_canonical_ktsn_contract.py::test_url_prefix_extraction_preserves_leading_zero_as_text`; acceptance `test_ac139_ktsn_is_only_the_string_remainder_of_exact_url_prefix`, `test_ac139_invalid_prefix_or_empty_ktsn_is_rejected` | unit + pure acceptance |
| AC-QPB-137 | Real canonical sheet/header layout, 8,042-row fixture counts, vascular-only scope, accepted/synonym grouping, No/KTSN/raw URL/name preservation | `test_d95_canonical_ktsn_reference.py::test_ac137_real_workbook_header_counts_samples_and_synonym_grouping` | pure acceptance; real read-only workbook |
| AC-QPB-138 | Fresh `.xlsx` candidate search; canonical recommendation without silent selection; filename/sheet/header/sample preview; legacy CSV excluded and old workbook not valid fallback; upload fallback with same preview/validation and confirmation | `test_ac138_candidate_search_recommends_canonical_without_silent_selection`; `test_ac138_upload_fallback_requires_same_preview_validation_and_confirmation` | pure acceptance |
| AC-QPB-139 | Exact R transformation and exact URL-derived KTSN rules | `test_ac139_r_equivalent_name_normalization_and_authority_extraction`; URL tests in same module | pure acceptance |
| AC-QPB-140 | `ktsn_taxonomy_reference` schema/data/rank pairs, blank hierarchy NULL semantics, accepted-only compatibility projection, Reference layer names/order/read-only/non-identifiable/indexes | `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_project_regression.py::test_ac140_new_type1_to3_projects_create_both_reference_layers_and_preserve_schema`; `test_ac140_rows_materialize_all_rank_fields_and_preserve_blank_hierarchy` | QGIS acceptance + pure acceptance |
| AC-QPB-141 | Provenance/hash/schema/pipeline identity; hash recomputation and post-confirmation hash mismatch; invalid/missing/non-vascular/status/No/orphan/URL/duplicate/schema/extension fail closed with actionable error and no partial promotion | `test_ac141_provenance_is_hash_schema_and_pipeline_identity_not_dataset_version`; `test_ac141_source_hash_is_recomputed_after_workbook_changes`; parametrized `test_ac141_invalid_or_missing_source_is_fail_closed_with_actionable_error`; `test_ac141_missing_canonical_source_fails_before_project_promotion_without_legacy_fallback`; generated manifest test `test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` | pure acceptance + QGIS acceptance |
| AC-QPB-142 | Canonical comparison key for accepted/synonym rows, synonym→accepted KTSN, raw authority-bearing accepted scientific name, ambiguity no-guess, field write-back compatibility | `test_ac142_synonym_matching_resolves_to_accepted_row_but_retains_raw_authority_name`; `test_ac142_comparison_key_collision_is_ambiguous_and_never_guesses`; QGIS `test_ac142_canonical_match_values_write_back_to_existing_observation_fields_without_relation_change` | pure acceptance + QGIS acceptance |
| FR-QPB-141 | Taxonomy aggregation by five ranks; synonym bucket unification; pre-lookup distinct-record counting; limitation behavior; Type 4 no-applicability; old-project missing-reference compatibility; no legacy implicit read | `test_ac143_taxonomy_report_unifies_synonym_and_accepted_observations_without_join_multiplication`; `test_ac144_old_project_report_path_is_compatible_without_legacy_fallback`; generated plugin source assertions in `test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` | pure acceptance + QGIS structural proxy |
| AC-QPB-143 | Independent report acceptance: existing ordinary report sections remain, accepted/synonym observations aggregate by Phylum/Class/Order/Family/Genus without lookup-join multiplication, and missing/Type-4 cases remain limited as specified | `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac143_taxonomy_report_unifies_synonym_and_accepted_observations_without_join_multiplication`; `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac143_type4_taxonomy_is_not_applicable` | pure acceptance |
| AC-QPB-144 | Independent privacy/backward-compatibility boundary: old projects without the canonical layer retain ordinary report behavior and declare `taxonomy_reference_unavailable`; generated output contains no raw canonical/legacy source, response, photo, key, or absolute source path and does not migrate old projects | `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac144_old_project_report_path_is_compatible_without_legacy_fallback`; `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac144_canonical_generated_plugin_fails_closed_without_source_fallback`; generated-project absence is additionally checked by `test_d95_canonical_ktsn_project_regression.py::test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` | pure acceptance + generated-project boundary proxy |
| AC-QPB-145 | Independent package/release boundary: release packaging places the canonical workbook at the same bundle-root `storage/reference/tables` path discovered by the wizard, excludes the legacy CSV/2025 workbook from release datas, and generated projects contain only materialized reference tables/provenance, never the source workbook | `tests/acceptance/qfield_project_builder/test_d95_canonical_ktsn_reference.py::test_ac145_release_datas_and_runtime_candidate_path_share_storage_boundary`; generated-project absence is additionally checked by `test_d95_canonical_ktsn_project_regression.py::test_ac137_ac140_generated_project_uses_canonical_source_and_never_copies_old_sources` | pure acceptance + QGIS/package structural proxy |
| FR-QPB-104/106/107 regression boundary | Existing Pl@ntNet request shape and matching remain covered by the pre-existing modules; the lookup-table comparison in `test_ktsn_lookup_table.py` now compares the generated table with D-95 canonical ingestion, while the two raw CSV derivation checks are marked `legacy_compatibility` | pre-existing modules plus D95 canonical lookup comparison | existing + pure acceptance |
| Backward compatibility | Existing saved project validation remains readable; report without taxonomy table preserves ordinary data and declares unavailable reference | `test_d95_canonical_ktsn_project_regression.py::test_ac141_legacy_project_without_taxonomy_reference_remains_readable`; `test_d95_canonical_ktsn_reference.py::test_ac144_old_project_report_path_is_compatible_without_legacy_fallback` | explicit legacy compatibility + pure acceptance |

## Fixture/provenance notes

- The real workbook's first sample rows are asserted from the file itself: accepted row 3
  `Huperzia cryptomeriana (Maxim.)R. D. Dixit` → KTSN `120000059514`; accepted row 4
  `Huperzia jejuensis B.-Y Sun & J. Lim` → `120000059515`; synonym row 5
  `Huperzia integrifolia (Matsuda)Z. Satou` → `120000215993`, attached to accepted KTSN
  `120000059515`.
- Temporary upload/error fixtures use fictional `Testus ...` names and KTSNs, so no synthetic row
  is presented as real reference data. They reproduce the workbook's two-level header exactly.
- Provenance intentionally retains metadata such as `source_filename` and `header_rows`; the
  no-content assertion checks the provenance object for absent row-bearing keys (`rows`,
  `preview`, `preview_rows`, `sample_rows`) rather than searching serialized metadata for an
  incidental substring. Likewise, the manifest may legitimately contain the canonical filename
  in `source_provenance`; generated-project safety is tested by checking that the original
  workbook path/file is not copied into `project_dir`.
- The invalid-case parameterization covers missing/unreadable workbook, non-vascular row,
  unrecognized status, missing accepted No, synonym No not `-`, orphan synonym, invalid URL
  prefix, empty URL remainder, duplicate URL/KTSN identity, missing rank subcolumn, missing
  required column, and `.xls` extension.
- The unit seam tests follow the repository convention of skipping only when a named harness
  function is not yet implemented. The D-95 pure acceptance/resource tests and the related QGIS
  project regression were executed in this round; GUI, PySide6, wizard-interaction, live-network,
  and packaged-app launch tests were not run.

## Deliberate boundary/gap

The existing Pl@ntNet live request/response and QField runtime tests are not duplicated. The new
tests verify that a canonical comparison key accepts a Pl@ntNet-style
`scientificNameWithoutAuthor` value and that the existing feature-save fields/relations remain
compatible. Actual QField QML execution, wizard keystrokes, and live external API calls remain
covered by their established manual/network boundaries.

AC-QPB-143, AC-QPB-144, and AC-QPB-145 are intentionally separate mappings: report semantics,
privacy/old-project compatibility, and release/package-vs-generated-project boundaries are
verified independently. AC-QPB-145's pure check inspects the PyInstaller `datas` destination and
the runtime storage resolver; its generated-project half remains a separate QGIS-marked boundary
check. No GUI, PySide6, wizard interaction, or packaged-app launch is required by these checks.
