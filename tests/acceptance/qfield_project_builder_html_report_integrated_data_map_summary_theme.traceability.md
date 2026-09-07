# HTML report integrated data/map/summary/theme traceability

Specification: [`specs/html-report-integrated-data-map-summary-theme.md`](../../specs/html-report-integrated-data-map-summary-theme.md)

New acceptance tests: [`qfield_project_builder/test_html_report_integrated_data_map_summary_theme.py`](qfield_project_builder/test_html_report_integrated_data_map_summary_theme.py)

Harness contract: [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md), section “HTML report integrated data/map/summary/theme fixture renderer”.

The new tests use an in-memory, production-path adapter and therefore never construct QGIS, touch a
user profile, access the user-owned `/Users/tory/Downloads/test2.*` files, start a browser, or use
the network. They complement—without changing—the prior hardening coverage for normalized keys,
partial fallback, and malformed geometries.

| Criterion | Executable coverage |
|---|---|
| AC-IHRM-001 | `test_ac001_same_semantic_identity_columns_collapse_without_changing_five_source_records` supplies five source rows with equal Korean/scientific/KTSN semantic aliases. It verifies one canonical column per semantic group in visible/export definitions and preservation of every supplied value in all projections and CSV. |
| AC-IHRM-002 | `test_ac002_falsey_missing_and_present_null_values_keep_stable_canonical_provenance` covers present `0`, `False`, `""`, present `None`, and a genuinely absent source key. It verifies typed values, per-row presence, canonical provenance, input immutability, and repeat stability. |
| AC-IHRM-003 | `test_ac003_differing_semantic_values_are_source_specific_disclosed_and_repeatable` covers unequal values and present-null versus non-empty values. It verifies separate final keys, no overwrites, collision disclosure, and deterministic definitions/CSV. |
| AC-IHRM-004 | `test_ac004_one_column_definition_drives_collision_filter_sort_detail_and_csv` supplies two normalized-name collisions and verifies unique deterministic keys, exact source-key value placement in all projections and CSV, plus filter/sort by source-column identity. |
| AC-IHRM-005 | `test_ac005_ac006_five_epsg4326_points_stay_map_eligible_with_stable_joined_details` verifies the five-row `inventory_observation.geom` POINT/EPSG:4326 collection model and that missing coordinate-transform availability does not invalidate it. |
| AC-IHRM-006 | `test_ac005_ac006_five_epsg4326_points_stay_map_eligible_with_stable_joined_details` verifies five WGS84 point features, stable source IDs, joined detail attributes, and absence of the global empty-map notice. |
| AC-IHRM-007 | `test_ac007_one_malformed_geometry_keeps_row_off_map_with_a_stable_visible_limitation` keeps the malformed row in table/detail/payload/CSV and non-geometry count while later valid rows render; it requires the stable invalid reason in the user-visible limitation notice. The pre-existing `test_ac020_one_malformed_geometry_preserves_its_row_join_and_aggregates_only_off_map` provides additional independent regression coverage. |
| AC-IHRM-008 | `test_ac008_cards_have_exact_type_specific_labels_number_and_order` is parameterized across Types 1–4 and asserts the exact label sequences/counts, including the Type 4 no-species/no-observation boundary and `community.community_name` basis. |
| AC-IHRM-009 | `test_ac009_direct_layer_cards_ignore_join_fanout_and_disclose_invalid_inputs` is parameterized across Types 1–4 and checks direct-layer values/sources, date and KTSN limitations, zero-row behavior, absent-layer `해당 레벨 부재`, Type 4 distinct-community behavior, and fan-out resistance. `test_ac013_ktsn_only_values_count_in_direct_layer_card_but_not_species_charts_or_mijeong` further makes the Type 1–3 direct KTSN measure observably distinct from species/chart aggregation. |
| AC-IHRM-010 | `test_ac010_integrated_table_is_present_for_populated_and_empty_sources_with_one_row_authority` verifies populated and zero-row table DOM/data states, stable headers, empty projections, header-only CSV, and joined-row filter/sort authority. |
| AC-IHRM-011 | `test_ac011_partial_fallback_discloses_scope_and_keeps_successful_rows_usable_in_cards` verifies failed direct path, fallback source, successful table/row read, known omission, unknown scope/count, non-complete status, and continued fallback-row usability in map/table/detail/cards/filter/sort/CSV. The pre-existing `test_ac019_direct_gpkg_failure_discloses_partial_fallback_without_hiding_success` independently covers the same limitation model. |
| AC-IHRM-012 | `test_ac012_theme_click_keyboard_storage_and_no_storage_preserve_report_state` verifies click and keyboard dark/light transitions, document-theme/ARIA/CSS state, saved-preference reopening, no-storage in-document switching, and preserved report state. |
| AC-IHRM-013 | `test_ac013_total_species_uses_only_direct_type_source_and_excludes_invalid_ktsn` is parameterized for Types 1–3. It verifies the exact direct KTSN source/field, distinct count, null/empty/whitespace exclusions, and limitation count. `test_ac013_ktsn_only_values_count_in_direct_layer_card_but_not_species_charts_or_mijeong` supplies two KTSN-only values, a duplicate direct KTSN, and repeated joined projections for every Type 1–3 source layer; it verifies direct-layer distinct count and no fan-out, while the occurrence/chart aggregation excludes those values and does not place them in `미동정`. |

## Fixture-access boundary

No acceptance criterion is behaviorally ambiguous. However, the specification names concrete
user-owned fixtures at `/Users/tory/Downloads/test2.gpkg` and
`/Users/tory/Downloads/test2_joined.csv`, while the test-designer isolation rule forbids accessing
files outside this repository. Thus AC-IHRM-001's exact five attached CSV values and AC-IHRM-005/006's
exact attached GPKG records are covered with equivalent five-row synthetic fixtures, not a
byte-for-byte verification of those external files. To add that fixture-specific assertion later,
the user must place approved copies inside the repository and send the specification through the
test-design approval gate again.

Until the adapter is implemented, the new module is collected and reports `SKIPPED`, consistent
with the existing `render_html_report_fixture` acceptance convention; it never produces a false
pass. These tests and this mapping require the user's explicit approval before implementation
begins.
