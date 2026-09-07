# D-UI-HRA-001 HTML report visual-refinement traceability

Approved design source: [`docs/ui-design-guidelines.md`](../../docs/ui-design-guidelines.md),
Decision Log `D-UI-HRA-001`, design-review criteria `DAC-HRA-001` through `DAC-HRA-015`.

New acceptance tests:
[`qfield_project_builder/test_html_report_ui_refinement.py`](qfield_project_builder/test_html_report_ui_refinement.py)

The automatic checks build a generated project and inspect the report-producing
`<project_slug>.qml` sidecar as the repository's existing report tests do. They are static/
generated-HTML checks: they verify source-level constituents and dependency boundaries, not final
browser layout. The `manual` tests are intentionally skipped placeholders for browser, print,
reduced-motion, keyboard, contrast, and QField output-boundary evidence; a skip is not a passing
claim.

The approved design is presentation-only. Functional behavior remains governed by the report
specifications and is cross-referenced below rather than redefined here:

- [`specs/html-report-interactive-analytics.md`](../../specs/html-report-interactive-analytics.md)
  (FR-HRA-001..017 and AC-HRA-001..016)
- [`qfield_project_builder/test_html_report_interactive_analytics.py`](qfield_project_builder/test_html_report_interactive_analytics.py)
  (current-data, map, details, joins, filter/sort, CSV, Korean/escaping, offline, empty-state,
  and standalone-report checks)
- [`qfield_project_builder/test_html_report_export.py`](qfield_project_builder/test_html_report_export.py)
  (unconditional report registration, no external resources, and project-relative output paths)
- [`qfield_project_builder_html_report_dhra003.traceability.md`](qfield_project_builder_html_report_dhra003.traceability.md)
  (VWorld-key-first/OSM fallback and non-fatal offline behavior)

| Design criterion | Automated static/generated-HTML check | Browser/manual check | Functional preservation cross-reference |
|---|---|---|---|
| DAC-HRA-001 — presentation-only change | `test_dac001_design_refinement_preserves_existing_report_data_and_behavior_contract` checks retained current-record, geometry, join, analytics, escaping, CSV, metadata, and output-path constituents. | Covered by the data/component regression gate below; compare generated report rows, geometry payloads, and summary counts before/after refinement. | AC-HRA-001..012 in `test_html_report_interactive_analytics.py`; AC-QPB-123..125 in `test_html_report_export.py`. |
| DAC-HRA-002 — one self-contained HTML file, no inline style/new remote dependency | `test_dac002_report_has_one_embedded_style_block_no_inline_styles_or_new_html_dependencies` checks one `<style>` block, parses syntactically valid HTML opening-tag attributes for real `style` attributes (without treating JavaScript bodies as markup), rejects remote HTML resources, and requires embedded runtime. | Offline-copy portion is covered by the existing AC-HRA-015 manual gate; inspect the browser network log for no new script/style/font/image/service dependency. | AC-HRA-015 and AC-QPB-124. |
| DAC-HRA-003 — 375px responsive layout and contained table scroll | `test_dac003_css_defines_375px_responsive_shell_and_contained_table_scrolling` checks breakpoint, shell containment, and table-region overflow. | `test_dac003_dac004_dac015_browser_responsive_navigation_focus_and_contrast_gate` verifies exact 375px rendering and no page-level overflow. | AC-HRA-006 table behavior remains covered by the existing interactive-analytics tests. |
| DAC-HRA-004 — stable section anchors and sticky/flow TOC | `test_dac004_sections_have_stable_anchors_and_responsive_sticky_table_of_contents` checks TOC, anchor navigation, sticky positioning, heading offset, and narrow-flow rules. | Same responsive/navigation gate verifies unique targets, target visibility, focus visibility, and desktop/mobile non-obscuration. | Existing AC-HRA-001..016 report sections/data remain the content targets. |
| DAC-HRA-005 — persistent light/dark theme without state loss | `test_dac005_theme_toggle_persists_and_does_not_replace_report_state` checks localStorage get/set, theme state, accessible control state, and storage-failure fallback. | `test_dac005_dac006_dac007_browser_theme_print_and_reduced_motion_gate` toggles with active filter/sort/details/map/CSV state and reloads to verify persistence. | AC-HRA-006..012 existing behavior must remain visible through the theme transition. |
| DAC-HRA-006 — readable print stylesheet without control clutter | `test_dac006_print_css_keeps_report_content_and_hides_control_chrome` checks `@media print`, hiding rules, light print surfaces, and required report content. | Same theme/print/motion gate verifies print preview has readable metadata/cards/map/table/details/notices/Korean text and no clipping. | AC-HRA-002..015 existing report content is the printable payload. |
| DAC-HRA-007 — reduced-motion support | `test_dac007_reduced_motion_minimizes_nonessential_motion_without_removing_controls` checks `prefers-reduced-motion: reduce`, disabled/minimized motion, and retained controls. | Same gate emulates reduced motion and verifies map/table/detail controls work immediately. | AC-HRA-002, AC-HRA-006..008, and AC-HRA-011 existing interactions. |
| DAC-HRA-008 — coherent map card and local/offline behavior | `test_dac008_map_is_a_coherent_card_with_local_feature_and_offline_states` checks map framing, local geometry path, invalid/missing state, offline disclosure, and attribution. | `test_dac008_dac009_dac010_dac011_dac012_browser_data_and_component_regression_gate` verifies every usable feature, invalid records outside map, and local usability when backgrounds fail. | AC-HRA-002, AC-HRA-011, and D-HRA-003 traceability. |
| DAC-HRA-009 — coherent joined table and unchanged row/filter/sort semantics | `test_dac009_joined_table_preserves_rows_filters_sorts_and_integrity_markers` checks source/visible row separation, filter, sort, null ordering, orphan/integrity markers, and visible-row feedback. The feedback may use the approved Korean `표시 중인 행 수` wording (or English compatibility wording), but must be bound to `visibleRows.length / allRows.length` and refresh after filtering. | Data/component gate verifies one-to-many/orphan rows, every visible-field filter, every-column deterministic sort, and no source mutation. | AC-HRA-004..006. |
| DAC-HRA-010 — coherent toolbar and exact filtered/all UTF-8 CSV | `test_dac010_csv_action_preserves_explicit_scope_utf8_headers_and_escaping` checks visible action/scope, stable columns, UTF-8, RFC-style quote escaping, and joined CSV path. | Data/component gate verifies keyboard/mouse action, exact selected existing rows, stable headers, commas/quotes/newlines/Korean, and filtered/all choice. | AC-HRA-007 and AC-HRA-012. |
| DAC-HRA-011 — mapped-feature activation uses one minimal escaped Leaflet popup (D-HRA-005) | test_dac011_map_activation_uses_one_minimal_leaflet_popup_and_escaped_values checks Leaflet popup binding/presentation, retained keyboard path, four observation labels, site-name path, escaping, no permanent/custom panel surface, and exclusion of technical popup fields. The detailed generated-runtime checks are in test_html_report_interactive_analytics.py. | The D-HRA-005 browser gate clicks and keyboard-activates point/polygon features, verifies exactly one adjacent transient Leaflet popup, exact observation/site content, inert escaping, unchanged geometry, and no permanent label or duplicate right-side panel. | Revised AC-HRA-003 and FR-HRA-005 in specs/html-report-interactive-analytics.md; existing AC-HRA-004..007 data/join/table/CSV contracts remain unchanged. |
| DAC-HRA-012 — Korean content remains readable and encoded | `test_dac012_korean_content_is_utf8_and_not_lost_by_the_visual_layer` checks UTF-8 declaration, the agreed current Korean labels `조사지` and `국명` (and rejects deprecated `조사대상`/`한국명`), Korean content, escaping, and UTF-8 CSV representation. | Data/component gate verifies Korean metadata/labels/values/notes/empty/limitation states render without mojibake or clipping and survive CSV export. | AC-HRA-007, AC-HRA-012, AC-HRA-014. |
| DAC-HRA-013 — one-time initialization/no duplicates after reload/theme | `test_dac013_initialization_has_one_sequence_and_theme_changes_do_not_duplicate_views` checks the explicit initialization entry and exactly one map/table/cards sequence, with the approved `qpbSyncSummaryState()` accessibility synchronization between `renderMap()` and listener registration. | `test_dac013_dac014_browser_reload_and_project_folder_boundary_gate` reloads and theme-toggles repeatedly, verifying one map, one control set, one row projection, and one detail/summary view. | AC-HRA-001, AC-HRA-006, AC-HRA-008, AC-HRA-013. |
| DAC-HRA-014 — current project folder and exact HTML/CSV paths retained | `test_dac014_output_paths_remain_current_project_folder_only` checks `qgisProject.homePath`, both exact path functions, path display, and no changed destination contract. | Same reload/output gate verifies actual writes in the current project folder and absence of outside-project picker/upload/sync/alternate destination. | AC-HRA-013, AC-HRA-016, and AC-QPB-125. |
| DAC-HRA-015 — keyboard access, visible focus, contrast, non-color state | `test_dac015_keyboard_focus_labels_and_non_color_accessibility_hooks_are_present` checks focus selectors, outline/box-shadow, accessible names/state, labels, and keyboard controls. | Responsive/navigation gate performs keyboard-only traversal and contrast review in both themes; record browser/accessibility-tool results. | Existing AC-HRA-003, AC-HRA-006, AC-HRA-007, AC-HRA-008, AC-HRA-011, and AC-HRA-013 control behavior. |

## Execution

Run the automatic generated-sidecar checks:

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_html_report_ui_refinement.py -q
```

The module is marked `qgis`, matching the existing acceptance suite. Manual evidence gates can be
listed without running them:

```text
.venv/bin/python -m pytest tests/acceptance/qfield_project_builder/test_html_report_ui_refinement.py --collect-only -q
```

No application code, approved design specification, Git state, or harness contract is changed by
this acceptance-test round.
