# FieldBuild Standalone QField HTML report refresh traceability

Specification: [`specs/fieldbuild-kit-qfield-html-report-refresh.md`](../../specs/fieldbuild-kit-qfield-html-report-refresh.md).

Acceptance tests: [`qfield_project_builder/test_fieldbuild_kit_qfield_html_report_refresh.py`](qfield_project_builder/test_fieldbuild_kit_qfield_html_report_refresh.py)

Harness contract: [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md), “FieldBuild Standalone QField HTML report refresh provider-runtime bridge”.

The automated fixture is mocked QGIS provider state: schema-named layers, QGIS-style features,
runtime geometry methods, layer CRS, direct GeoPackage metadata/rows, and QField capability
availability. It is not an abstract report input (`analytics_input`, flattened source rows, or
preselected anchors), and the result is parsed from the exact `qpbBuildHtmlReport()` output and
its embedded report scripts. A Python report implementation or fabricated report snapshot cannot
satisfy this contract.

| Acceptance criterion | Executable coverage |
|---|---|
| AC-FBKR-001 | `test_ac001_iphone_qfield_loaded_layer_geometry_gate_requires_privacy_safe_manual_evidence` remains explicitly `device` + `manual` + skipped. Only the specified iPhone/QField 4.2.4 evidence can pass it. |
| AC-FBKR-002 | `test_ac002_provider_geometry_outcomes_are_distinct_and_xy_only` drives direct GeoPackage rows and loaded QGIS feature geometry through the actual collector. It checks valid/empty/serializer/unknown-CRS/malformed outcomes, Korean reasons, EPSG:4326 identity, XY-only output, and row survival. |
| AC-FBKR-003 | `test_ac003_provider_fk_joins_preserve_type_anchors_and_rows` parameterizes Type 1–4 and direct/fallback collection. It checks schema PK/FK joins, Type 1 inventory anchors, Type 2 site + survey anchors, Type 3 plot with linked-survey-only fallback, Type 4 community-only anchors, and the true joined-table/CSV leaf rows. |
| AC-FBKR-004 | `test_ac004_normal_korean_status_and_closed_diagnostics_are_rendered_by_html_runtime` checks the actual rendered normal status and closed keyboard-operable Diagnostics after direct failure and provider fallback, including no false completeness or iOS sandbox path. |
| AC-FBKR-005 | `test_ac005_provider_joined_notes_are_korean_deduplicated_and_private_values_do_not_render` supplies conflicting source-layer notes and a sensitive path through feature attributes. It verifies Korean provenance, normal identifier suppression, and no rendered sensitive path. |
| AC-FBKR-006 | `test_ac006_chart_cards_are_derived_from_provider_attributes_not_analytics_input` derives the Type 1–4 chart matrix from actual provider attributes, including invalid cover/area and empty composition. It checks hidden non-applicable cards/section/TOC, Korean card text, textual equivalents, keyboard/focus/print behavior, and both viewport widths. |
| AC-FBKR-007 | `test_ac007_generated_html_retains_local_interactions_with_osm_fallback_without_vworld` executes the emitted report’s filter, keyboard sort, theme, Diagnostics, print, and CSV actions offline. It supplies a fake runtime VWorld key to verify that the standalone report neither serializes/injects it nor exposes a VWorld control, while retaining the OSM fallback and local behavior. |

## Fixture and physical-device boundary

`render_html_report_refresh_fixture()` must use the provider-runtime bridge defined in the harness
contract. The fixture never opens the user-owned evidence artifact, a Downloads folder, a QGIS or
browser profile, an iOS simulator, a physical device, or a network connection. AC-FBKR-001 is not
automated or relaxed by this bridge.

These revised acceptance artifacts await user review and approval before implementation begins.
