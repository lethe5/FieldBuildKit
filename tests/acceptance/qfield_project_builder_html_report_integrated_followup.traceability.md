# HTML report integrated follow-up traceability

Specification: [`specs/html-report-integrated-followup.md`](../../specs/html-report-integrated-followup.md)

Acceptance tests: [`qfield_project_builder/test_html_report_integrated_followup.py`](qfield_project_builder/test_html_report_integrated_followup.py)

The feature-local module uses the existing isolated `acceptance_api.build_project()` seam and
generated `<project_slug>.qml` sidecar. It does not edit `specs/**`, application source, QGIS
profiles, or GeoPackages, and it does not call remote tiles. The automatic checks are strict
generated-artifact contract assertions; a missing contract fails. A missing QGIS/PyQGIS runtime
is handled only by the existing harness-level skip and is not considered coverage.

| Acceptance criterion | Executable coverage |
|---|---|
| AC-IRF-001 (historical/superseded behavior retained) | `test_ac001_saved_vworld_key_is_runtime_selected_and_osm_is_keyless_default` preserves the original saved-key discovery, VWorld-first/OSM-default selection, attribution, no blank-key request, and key non-leakage regression. The superseding export-consent behavior is covered by AC-IRF-013/014 below. |
| AC-IRF-002 | `test_ac002_background_failure_is_nonfatal_and_preserves_all_local_capabilities` checks alternate-once guard, Korean/offline disclosure, and local map/table/cards/charts/filter/sort/detail/theme/CSV constituents. Live failure injection is the marked gate. |
| AC-IRF-003 | `test_ac003_current_gpkg_spatial_metadata_collects_every_table_and_attributes` runs for all four survey types and checks direct `gpkg_contents`/`gpkg_geometry_columns` inspection, geometry column, CRS, attributes/source identity, raw identity, non-spatial exclusion, and read-only current-data collection. |
| AC-IRF-004 | `test_ac004_type_specific_anchor_rules_and_fk_join_boundaries` runs Type 1–4 anchor cases and checks anchor/fallback rules, UUID/FK joins, one-to-many preservation, and observation non-promotion. |
| AC-IRF-005 | `test_ac005_geometry_validity_crs_serialization_and_truthful_global_empty_state` checks validity classification, EPSG:4326/WGS84 transformation, reason retention, and the conditional global empty-map message. |
| AC-IRF-006 | `test_ac006_one_to_many_anchor_is_single_feature_but_all_children_and_orphan_rows_survive` checks one anchor feature, deterministic child collection, three-row joined/CSV preservation, orphan marker, and no fabricated geometry. |
| AC-IRF-007 | `test_ac007_columns_are_collision_free_normalized_and_byte_stable_for_csv` checks collision detection, `source_table__source_field` normalization, suffix allocation, uniqueness, schema-order stability, and repeat-export header stability. |
| AC-IRF-008 | `test_ac008_visible_labels_are_concise_korean_and_identity_csv_contract_is_preserved` checks concise-label path, hidden raw technical names, exact `국명`/`학명`/`KTSN`, one header per column, and stable machine headers. |
| AC-IRF-009 | `test_ac009_overview_cards_are_explicit_korean_distinct_source_level_counts` runs all types and checks `조사지`/`조사구`/`조사`/`관찰`, no `조사대상`, distinct-ID/source basis, explicit absent-level semantics, and level counts. |
| AC-IRF-010 | `test_ac010_d3_charts_use_defined_source_aggregations_and_truthful_numeric_empty_states` checks local d3, Korean bar/pie chart titles, occurrence/cover/area aggregation paths, zero-valid numeric handling, invalid exclusions, and empty states. |
| AC-IRF-011 | `test_ac011_theme_toggle_is_accessible_and_state_preserving` checks accessible keyboard/pointer theme control, deterministic/persistent theme state, preservation hooks for filter/sort/expanded/map/detail/chart state, and unchanged CSV data/header path. Stateful transition is the marked browser/device gate. |
| AC-IRF-012 | `test_ac012_escaping_utf8_csv_and_secret_attachment_boundaries_are_explicit` checks inert HTML values, quoted UTF-8 CSV, Korean support, duplicate-name/collision diagnostics, and exclusion of credentials/attachment paths from normal surfaces/logs. Adversarial runtime values are exercised by the marked browser/device gate. |
| AC-IRF-013 | `test_ac013_export_consent_is_explicit_key_scoped_and_fail_closed` checks the pre-export popup, default `미포함`, exposure warning, affirmative include-only VWorld/key branch, OSM/no-key omission branch, payload/CSV secret boundary, and cancel/close fail-closed output behavior. The configured acceptance key is asserted absent from generated source. |
| AC-IRF-014 | `test_ac014_missing_key_is_keyless_osm_export_without_include_choice` checks no-key OSM export, no blank-key VWorld request, and absence/disablement of a usable include choice. |
| AC-IRF-015 | `test_ac015_direct_sqlite_reads_actual_spatial_rows_and_reports_only_authorized_fallback` runs for all four survey types and requires direct SQLite metadata plus actual spatial-row selection, geometry column, CRS, attributes, raw/current record identity, payload propagation, and fallback/omission completeness disclosure only at the direct-access failure boundary. |
| AC-IRF-016 | `test_ac016_official_d3_bundle_is_local_and_chart_initialization_validates_aggregates` requires an official local/inline d3 distribution, no remote d3 dependency, initialization validation for occurrence/cover/area, source-row aggregation linkage, and truthful unavailable/limited state. |
| AC-IRF-017 | `test_ac017_dimensional_wkb_discards_zm_and_supports_all_xy_geometry_types` checks dimensional WKB/equivalent handling for Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, and GeometryCollection, including explicit Z/M removal, valid X/Y-only EPSG:4326/WGS84 transformation, and dimensional markers. `test_ac017_invalid_xy_is_retained_with_limitation_and_never_fabricated_from_zm` checks malformed/invalid X/Y retention with a stable reason, rendered-geometry exclusion, and no Z/M-derived coordinate invention. `test_ac017_table_and_csv_contract_excludes_zm_coordinates_and_values` checks that integrated table/CSV serialization uses report columns/attributes and contains no Z/M coordinate columns or copied ordinates. |

## Coverage boundary and approval request

The suite intentionally does not claim browser layout, actual d3 rendering/hover/focus feedback,
QField save/reopen behavior, live tile fallback, or byte-level CSV parsing from a real generated
dataset. Those are explicit skipped `manual`/`device`/`network` acceptance obligations, not
weakened pass criteria. The structural tests are executable and fail when the generated artifact
does not expose the required contract.

## New-round coverage boundary and approval request

The new AC-IRF-013–017 checks are executable generated-sidecar contract tests and intentionally
fail when the implementation merely mentions metadata or loaded layers without direct actual-row
SQLite collection, when export writes before consent, or when charts are plausible but not backed
by a validated local d3 initialization, or when dimensional geometry preserves Z/M or fabricates
coordinates from invalid X/Y. Existing AC-IRF-001–012 tests were retained; AC-IRF-001 is
explicitly marked historical because the approved spec supersedes its export-time behavior with
AC-IRF-013/014. No existing test was deleted or weakened. The packaging D3-path defect is
deliberately outside this acceptance mapping and remains an implementation-level test concern.

The existing `manual`/`device`/`network` skips remain unchanged for live tiles, QField/browser
state transitions, and adversarial runtime values. QGIS direct execution and real profile access
are prohibited for this round; therefore the automatic suite uses the established isolated
`build_project()` seam and generated-sidecar inspection only. This does not claim live popup
interaction, a real browser d3 render, or device persistence.

This acceptance-test round is awaiting the user's explicit approval before implementation work
may begin, per `CLAUDE.md`.
