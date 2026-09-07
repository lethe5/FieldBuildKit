# Interactive HTML report and analytics traceability

Specification: [`specs/html-report-interactive-analytics.md`](../../specs/html-report-interactive-analytics.md)

Automatic checks: [`qfield_project_builder/test_html_report_interactive_analytics.py`](qfield_project_builder/test_html_report_interactive_analytics.py)

This round adds coverage for every AC-HRA criterion, including the D-HRA-005 popup change.
The Python acceptance harness can build a
real project and inspect the generated project-plugin QML, but it cannot start QField's QML
engine, a browser, the target QField 4.2.4 runtime, or a physical device.  Automatic checks consequently
verify observable generated-artifact structure, current-record enumeration, escaping/resource
guards, and required interaction constituents.  The explicitly skipped `manual`/`device`/
`network` tests are required end-to-end evidence gates; they are not passing claims.

| Criterion | Coverage |
|---|---|
| AC-HRA-001 | `test_ac001_every_survey_type_has_on_demand_current_data_report_with_metadata` (four survey types) checks the unconditional action, retained metadata, current feature iteration, and absence of periodic report generation. |
| AC-HRA-002 | `test_ac002_report_source_has_leaflet_or_d3_map_geometry_and_invalid_geometry_notice` checks map library, geometry input/CRS transformation, and invalid-geometry disclosure; `test_ac002_map_renders_every_valid_point_and_polygon_on_device` is the required real-report geometry-fidelity gate. |
| AC-HRA-003 | test_ac003_report_runtime_uses_one_leaflet_popup_for_pointer_and_keyboard_activation checks one Leaflet bindPopup path, retained pointer/Enter/Space activation, Leaflet popup CSS, escaping path, no permanent labels, and absence of the duplicate custom panel; test_ac003_report_runtime_uses_minimal_observation_and_site_popup_allow_lists checks the four observation labels, site-name path, explicit non-generic field projection, and exclusion of UUID/KTSN/FK/parent/technical popup content. test_ac003_feature_activation_shows_one_minimal_escaped_leaflet_popup_in_browser is the required pointer/keyboard/browser gate for adjacency, exact visible content, inert escaping, geometry preservation, and transient/no-label behavior. |
| AC-HRA-004 | `test_ac004_ac005_join_source_declares_uuid_fk_hierarchies_and_absent_levels` checks FK/UUID joins, joined table, and orphan/integrity marker; `test_ac004_ac005_joined_rows_preserve_relationships_for_all_survey_types_on_device` covers one-to-many/orphan runtime semantics. |
| AC-HRA-005 | `test_ac004_ac005_join_source_declares_uuid_fk_hierarchies_and_absent_levels` is parametrized over all four survey types and checks schema-absent empty-level handling; the paired device gate verifies no fabricated rows. |
| AC-HRA-006 | `test_ac006_joined_table_source_has_filter_sort_null_date_numeric_and_stable_data_paths` checks client filter, visible count, typed/stable sort, null handling, and preservation of unfiltered rows; `test_ac006_filter_and_sort_joined_table_without_mutating_source_in_browser` is the data/runtime gate. |
| AC-HRA-007 | `test_ac007_ac012_report_source_has_utf8_csv_action_visible_choice_and_safe_escaping` checks CSV action, UTF-8, quoting, and filtered/all choice; `test_ac007_ac012_csv_matches_selected_rows_and_escapes_adversarial_values` verifies exact exported rows/values manually. |
| AC-HRA-008 | `test_ac008_report_source_has_collapsible_schema_level_summaries_with_semantic_korean_labels_and_counts` checks the collapsible renderer's semantic schema-level mapping—`site` = `조사지`, `survey` = `조사`, `plot` = `조사구`—and its per-level record count. It requires the renderer to emit a section only when that schema level exists and rejects the deprecated ambiguous `조사대상` label. `test_ac008_collapsing_summaries_does_not_remove_map_or_joined_rows` verifies state isolation manually. Type-specific schema-absent-level behavior remains covered by AC-HRA-005. |
| AC-HRA-009 | `test_ac009_ac010_report_source_has_species_precedence_counts_and_date_cards` keeps the Korean-only/scientific-only precedence, explicit all-fields-empty “미동정” fallback, observation-row counts, and separate Type 4 community concept checks; `test_ac009_ac010_report_source_excludes_ktsn_only_from_species_aggregation` accepts an explicit KTSN-only exclusion with species mutation isolated in its eligible `else` branch, forbids KTSN-only fall-through into a species or “미동정” bucket, and confirms the row remains in joined/report data; `test_ac013_ktsn_only_values_count_in_direct_layer_card_but_not_species_charts_or_mijeong` behaviorally verifies the same chart/“미동정” exclusion for Types 1–3 while the direct card includes those values. |
| AC-HRA-010 | `test_ac009_ac010_report_source_has_species_precedence_counts_and_date_cards` checks date-card and missing/invalid-date disclosure constituents; `test_ac009_ac010_report_source_excludes_ktsn_only_from_species_aggregation` structurally preserves D-HRA-002 species-key exclusion while requiring date aggregation to continue after the exclusion decision; `test_ac013_ktsn_only_values_count_in_direct_layer_card_but_not_species_charts_or_mijeong` verifies D-HRA-004’s separate direct-layer KTSN-card count, valid KTSN-only inclusion, duplicate/fan-out resistance, continued occurrence/chart and “미동정” exclusion, and the Type 4 boundary remains asserted by `test_ac008_cards_have_exact_type_specific_labels_number_and_order`. The paired manual gate verifies the complete browser-visible behavior. |
| AC-HRA-011 | `test_ac011_report_source_selects_vworld_key_first_and_osm_without_key` builds both consented-key and no-key projects, checking saved-key lookup, VWorld-first/OSM fallback constituents, explicit service-failure/offline handling, visible attribution/status, and absence of the literal key from the generated report sidecar; `test_ac011_vworld_key_first_osm_fallback_and_offline_report_are_nonfatal_on_device` is the required real QField/browser/network gate for VWorld-key-first, automatic OSM fallback, alternate-service failure, both-service offline resilience, attribution/status, and UI key non-exposure. |
| AC-HRA-012 | `test_ac007_ac012_report_source_has_utf8_csv_action_visible_choice_and_safe_escaping` checks HTML escaping and CSV escaping/quoting constituents; the paired manual test uses script-like, quote, comma, newline, and Korean adversarial values. |
| AC-HRA-013 | `test_ac013_project_folder_html_and_csv_paths_and_write_failures_are_reported` is an explicit QField 4.2.4 project-folder-write gate covering the fixed current-project destination, exact HTML/CSV path reporting, successful writes, unavailable/non-writable-folder errors, no false success, no silent alternate-destination fallback, and in-memory report availability. |
| AC-HRA-014 | `test_ac014_empty_project_report_source_has_zero_and_header_only_empty_states` checks empty-state, zero, and header-only CSV constituents; `test_ac014_empty_project_is_valid_in_browser_and_csv_parser` verifies the actual empty export manually across survey types. |
| AC-HRA-015 | `test_ac015_report_sidecar_embeds_local_runtime_without_external_resources` checks standalone HTML, embedded style/interaction code, and no external resource references; `test_ac015_copied_report_works_without_network_in_browser` is the offline-copy/network-log gate. |
| AC-HRA-016 | `test_ac016_qfield_424_capability_and_project_folder_boundary_are_reported_honestly` is the required QField 4.2.4 version/platform capability audit for full-layer enumeration, VWorld, and the absence of an external save-location picker/API; it requires an explicit project-folder-only output boundary and forbids false completeness or outside-folder-export claims. |

## Execution

Run automatic generated-artifact checks (requires the existing QGIS-marked acceptance setup):

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_html_report_interactive_analytics.py -q
```

The suite's normal default skips `network` tests; the live VWorld portion can be selected with
`--run-network`, a valid approved test key, and the target device/browser procedure documented in
the skip reason.  To see the complete manual/device checklist without running it, use:

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_html_report_interactive_analytics.py --collect-only -q
```

The new tests do not modify the application, project data, Git state, or HARNESS_CONTRACT.md.
They rely on the existing build_project() acceptance entry point and generated
<project_slug>.qml sidecar; no new acceptance API function is required for the structural
checks. The D-HRA-005 update changes only mapped-feature display assertions; existing data, join,
table, geometry, summary, and CSV coverage remains in place.
