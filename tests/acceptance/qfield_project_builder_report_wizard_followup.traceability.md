# FieldBuild Standalone report/wizard follow-up traceability

Specification: [`specs/fieldbuild-kit-report-wizard-followup.md`](../../specs/fieldbuild-kit-report-wizard-followup.md)

Acceptance tests: [`qfield_project_builder/test_report_wizard_followup.py`](qfield_project_builder/test_report_wizard_followup.py)

This round adds tests only. It does not change the application, specification, shared docs, or
the acceptance harness contract. It reuses `make_base_config`, the checked-in reference-data
fixtures, `build_project`, `inspect_identification_widget`, and `open_gpkg`. The supplied report
HTML is evidence only and is not copied into the repository or used as a normative fixture.

| Criterion | Automated coverage | Manual/device coverage and boundary |
|---|---|---|
| AC-RWF-001 | `test_ac001_no_usable_vworld_key_keeps_report_generation_and_fallback_guarded` (Type 1/2/3) checks successful build, no blank-key VWorld call shape, Korean no-key/fallback state, and retained local surfaces. | `test_ac001_ac002_ac003_report_runtime_fallback_and_local_functions_in_browser` verifies the actual no-key report opening, OSM attempt, and offline runtime state. |
| AC-RWF-002 | `test_ac002_key_first_vworld_failure_fallback_and_offline_status_are_nonfatal_and_singleton` checks VWorld-first selection, tile-error handling, OSM fallback, attribution, and no key in UI source. | Same browser/network skip verifies successful VWorld imagery and visible attribution. |
| AC-RWF-003 | `test_ac003_local_geometry_and_non_geometry_data_survive_background_failure` checks retained GeoPackage geometry plus report serialization, joined data, and geometry limitation paths. | Same browser/network skip covers valid/invalid geometry and local-only behavior after remote failures. |
| AC-RWF-004 | `test_ac004_identity_columns_have_exact_order_and_authoritative_row_mapping` (Type 1/2/3) checks exact consecutive labels, existing source fields, child-row expansion, and empty-value preservation. `test_ac005_identity_filters_sorting_csv_scope_and_escaping_preserve_existing_rows` checks filter/sort/CSV/escaping structure. | `test_ac004_ac005_ac006_identity_and_type4_report_behavior_in_browser` checks actual values and one-to-many UI behavior. |
| AC-RWF-005 | `test_ac005_identity_filters_sorting_csv_scope_and_escaping_preserve_existing_rows` checks null-safe values, typed sorting, original-row collection, RFC-style CSV quoting, and HTML escaping. | Same browser skip exercises null/duplicate/scientific-only/KTSN-only/all-empty/HTML-looking values and exact filtered/all-row export. |
| AC-RWF-006 | `test_ac006_type4_report_has_no_fabricated_plant_identity_or_identification_target` checks Type 4 report definition and `community` widget exclusion. | Same browser skip confirms no fabricated Type 1/2/3 values/control in the rendered Type 4 report. |
| AC-RWF-007 | `test_ac007_generated_report_and_related_surface_use_korean_fieldbuild_copy` extracts only report HTML text/visible attribute values and generated identification-QML text-bearing properties. It checks the required Korean meanings and rejects the specified authored English prose on those rendered artifact surfaces. JS/Python source, function names, comments, docstrings, and stable keys/codes are outside this scan. | `test_ac007_ac008_all_user_facing_copy_is_localized_in_supported_surfaces` is the visual review of every visible report, identification, and wizard state. |
| AC-RWF-008 | `test_ac008_proper_names_and_internal_keys_remain_distinct_secondary_metadata` checks allowed proper names, primary Korean labels, escaped secondary field-key path, and stable internal identity fields. | Same localization skip checks proper-name/internal-key distinction in the actual UI. |
| AC-RWF-009 | `test_ac009_all_type1_to_3_identify_buttons_start_immediately_without_app_gate` (Type 1/2/3) checks exact button label, direct request invocation, absence of app Dialog/OK gate, and single explicit trigger. | `test_ac009_ac010_ac011_immediate_identification_and_boundaries_on_device` checks real click-to-request timing and platform behavior. |
| AC-RWF-010 | `test_ac010_identification_workflow_writeback_and_location_boundaries_remain_intact` and `test_ac010_type4_is_excluded_and_photo_attachment_alone_is_not_a_trigger` check existing photo/request/candidate/write-back/UUID-layer guards, derived scientific/KTSN boundary, attachment-only non-trigger, and Type 4 exclusion. | Device skip covers candidate selection, save/reopen, parent/sibling isolation, and Type 4. |
| AC-RWF-011 | `test_ac011_privacy_location_and_authoritative_geometry_fail_closed_are_source_guarded` checks authoritative geometry resolution, fail-closed validation, and no EXIF/GPS/device/centroid location path. | Device skip verifies request/context/logs and original attachment bytes/path with EXIF and invalid-geometry scenarios. |
| AC-RWF-012 | `test_ac012_ac013_step4_canvas_floor_scroll_layout_and_drawing_semantics_are_declared` checks the 700x560 window contract, 320x240 canvas floor, scroll-area reachability mechanism, visibility wiring, and polygon/bbox semantics. | `test_ac012_ac013_step4_canvas_visual_layout_and_resize_stability` measures the actual 700x560 screen geometry and clipping/overlap. |
| AC-RWF-013 | `test_ac012_ac013_step4_canvas_floor_scroll_layout_and_drawing_semantics_are_declared` checks resizable scroll layout and visibility hooks without changing drawing modes/finish operations. | Same manual skip repeats resize cycles and optional-section visibility transitions. |
| AC-RWF-014 | `test_ac014_report_is_standalone_and_one_time_local_initialization_is_present` checks embedded runtime/resources, no external HTML resources, one initialization function, and guarded DOM readiness. | `test_ac014_copied_report_is_standalone_and_local_on_browser_device` verifies a copied report with network disabled and reload. |

## Test correction rationale

The AC-RWF-001 structural contract deliberately continues to require the internal
`qpbBuildAnalytics` function. The AC-RWF-007 automated localization check no longer scans whole
JS/Python/QML source, because that conflated implementation identifiers and authoring comments
with rendered copy (including the wizard docstring text `Identify attached photos`). In particular,
the helper no longer feeds the complete JS/QML source to `HTMLParser`; it parses only HTML-bearing
string literals and explicitly visible HTML attributes, so executable identifiers such as
`qpbBuildAnalytics` can never become report copy. The corrected check is surface-scoped: report
HTML text/visible attribute values and generated identification QML text-bearing properties.
Python wizard source is not a rendered artifact and is therefore not scanned by this automated
check; its visible states remain covered by the existing manual/device acceptance. The forbidden
English mapping and minimum Korean semantic mapping are unchanged; this correction only removes
false positives and does not remove runtime/manual acceptance coverage.

## Coverage boundary

The Python acceptance API exposes generated artifacts, not a browser DOM, QField's QML runtime, a
real platform permission flow, or live Qt widget rectangles. The skipped tests are therefore
explicit acceptance obligations, not silent omissions. The automated source checks are necessary
guards for the generated contract; they do not claim to replace those runtime/device checks.
