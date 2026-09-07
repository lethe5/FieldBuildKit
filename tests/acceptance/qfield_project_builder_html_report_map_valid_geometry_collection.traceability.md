# HTML report spatial-anchor map collection traceability

Specification: [`specs/html-report-map-valid-geometry-collection.md`](../../specs/html-report-map-valid-geometry-collection.md)

Acceptance tests: [`qfield_project_builder/test_html_report_map_valid_geometry_collection.py`](qfield_project_builder/test_html_report_map_valid_geometry_collection.py)

The automated tests use only the existing `make_base_config`, `build_project`, generated QML
sidecars, and `qfield_builder.schemas`. They do not construct a QGIS application, access a real
QGIS profile, start a browser, or call a remote tile service. Browser/device rendering, actual
coordinate placement, and network-disabled execution remain runtime verification boundaries and
are not claimed by these source-contract tests.

| Criterion | Automated coverage |
|---|---|
| AC-MGC-001 | `test_ac001_ac002_type_specific_spatial_contexts_and_deterministic_layer_order` covers Type 1 single inventory, Type 2 site + survey-observation, Type 3 site + plot-survey-observation, Type 4 community-only contexts and no-valid-geometry state. |
| AC-MGC-002 | `test_ac001_ac002_type_specific_spatial_contexts_and_deterministic_layer_order` checks schema-defined tables, geometry declarations, and dedicated map collection; `test_ac006_type4_community_only_does_not_fabricate_observation_rows_or_identity` checks Type 4 exclusion. |
| AC-MGC-003 | `test_ac003_valid_geometry_only_is_rendered_and_unusable_records_remain_report_data` checks valid-only selection, retained serialized records, limitation reasons, and WGS84 path. |
| AC-MGC-004 | `test_ac004_ac008_ac009_ac010_ac011_type2_site_survey_observation_join_is_survey_anchored`, `test_ac004_ac010_ac011_type3_site_plot_survey_observation_join_and_fallback`, and `test_ac004_one_to_many_is_row_authoritative_and_map_aggregation_is_deterministic` check UUID/FK joins, one-to-many rows, orphan-safe anchor rules, and deterministic aggregation. |
| AC-MGC-005 | `test_ac005_crs_conversion_preserves_geometry_type_and_rejects_bad_coordinates` checks explicit EPSG:4326/WGS84 transformation, type-preserving JSON serialization, and invalid-geometry rejection. |
| AC-MGC-006 | `test_ac003_valid_geometry_only_is_rendered_and_unusable_records_remain_report_data` checks invalid/missing retention and limitation paths; `test_ac006_type4_community_only_does_not_fabricate_observation_rows_or_identity` checks non-spatial/Type 4 boundaries. |
| AC-MGC-007 | `test_ac001_ac002_type_specific_spatial_contexts_and_deterministic_layer_order` and `test_ac009_ac010_no_observation_geometry_promotion_and_no_valid_state_is_explicit` check explicit valid-feature counting and the truthful empty state. |
| AC-MGC-008 | `test_ac007_ac008_local_offline_report_keeps_identity_filter_sort_csv_and_privacy_boundaries` checks identity, filter/sort/CSV, escaping, local map/report functions, and offline surfaces; `test_ac008_map_details_keep_anchor_uuid_and_joined_site_context_without_fabrication` checks detail context. |
| AC-MGC-009 | `test_ac006_type4_community_only_does_not_fabricate_observation_rows_or_identity` verifies community data stays separate and no plant-observation rows/identity are fabricated. |
| AC-MGC-010 | `test_ac007_ac008_local_offline_report_keeps_identity_filter_sort_csv_and_privacy_boundaries` checks local report functions, OpenStreetMap/offline paths, escaping, and CSV contracts independent of remote background tiles. |
| AC-MGC-011 | `test_ac007_ac008_local_offline_report_keeps_identity_filter_sort_csv_and_privacy_boundaries` checks escaping, safe JSON, CSV encoding, local resources, and secret-boundary patterns; `test_ac008_map_details_keep_anchor_uuid_and_joined_site_context_without_fabrication` checks safe joined details and forbidden EXIF/GPS/centroid promotion. |

## Coverage boundary

The generated sidecar is the harness's injectable artifact boundary. Actual map painting, WGS84
placement in a browser, copied-report offline loading, QField save/reopen behavior, and device
geometry inspection require the manual/browser/device acceptance obligations already described by
the specification; no real QGIS/browser dependency is introduced into this deterministic suite.

