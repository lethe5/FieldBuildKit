# Traceability — Type 2·3 site opacity and editable-layer order

Specification: [`specs/html-report-site-opacity-types-2-3.md`](../../specs/html-report-site-opacity-types-2-3.md)

Acceptance tests: [`qfield_project_builder/test_html_report_site_opacity_types_2_3.py`](qfield_project_builder/test_html_report_site_opacity_types_2_3.py)

The tests use the existing `built_project_by_type` and acceptance `build_project` seams.  QGIS
project XML is read-only inspection of persisted semantic values; generated QML inspection covers
the report-local map style and preserves the existing report execution path without requiring a
browser, network tiles, or a QField device.

| Acceptance criterion | Test coverage | Verification surface |
|---|---|---|
| AC-SOP-001 | `test_ac001_ac002_site_persists_070_opacity_in_type2_and_type3_project_and_report` (`temporary_plots`) | Type 2 generated QGIS project, QML report map style |
| AC-SOP-002 | `test_ac001_ac002_site_persists_070_opacity_in_type2_and_type3_project_and_report` (`permanent_plots`) | Type 3 generated QGIS project, QML report map style |
| AC-SOP-003 | `test_ac003_type1_and_type4_do_not_receive_type2_type3_site_opacity_change`; `test_ac003_site_opacity_does_not_change_type2_type3_anchor_layer_style` | Type 1/4 and Type 2/3 persisted layer opacity |
| AC-SOP-004 | `test_ac004_existing_join_table_and_csv_paths_remain_in_report` | Row-authoritative join builder, identity fields, HTML/CSV functions |
| AC-SOP-005 | `test_ac005_local_report_style_is_feature_local_and_keeps_offline_map_path` | Local `map_features` renderer, valid geometry gate, background-independent site style |
| AC-SOP-006 | `test_ac006_missing_site_geometry_keeps_report_empty_geometry_contract` | Empty-state, limitation, and data-preservation markers |
| AC-SOP-007 | `test_ac007_site_is_last_among_editable_geometry_layers_only` | Generated layer-tree order filtered by geometry and `readOnly`; reference/relation tables excluded |

The browser/QField-device portions of AC-SOP-001/002/005/006 remain manual verification gates;
these acceptance tests intentionally verify the deterministic generated-artifact contracts that
are available on this host.
