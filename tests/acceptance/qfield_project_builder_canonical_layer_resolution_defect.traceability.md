# QField canonical taxonomy layer-resolution defect traceability

Specification: `specs/fieldbuild-kit-qfield-canonical-layer-resolution-defect.md`

This test-design round adds new regression coverage only. The approved D-95 and canonical lookup
defect test files are intentionally unchanged. All QGIS tests create temporary GeoPackages and
projects and run PyQGIS through the repository's isolated bridge; they never read or mutate the
user's live QGIS profile.

QCR supersedes QCLR's new-project expression/layer-ID route only (FR-QCLR-001–003/007 and
AC-QCLR-001–003/005/007–008). The expression/layer-ID evidence below therefore documents the
retained pre-QCR/old-project compatibility route; it is not evidence for the current delivered
new-project QField runtime route. That route, including its project-local resource and
expression-independence assertions, is owned by
`qfield_project_builder_qfield_canonical_runtime_lookup_correction.traceability.md`.

| Requirement / acceptance criterion | Test location | Evidence |
|---|---|---|
| FR/AC-QCLR-001 generated canonical layer-ID propagation | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_renderer_forwards_the_actual_layer_id_to_the_widget`; `tests/acceptance/qfield_project_builder/test_qfield_canonical_layer_resolution_defect.py::test_generated_project_propagates_actual_canonical_layer_id_to_embedded_widget` | The worker seam must pass the fake layer's exact `layer.id()` to the renderer. The QGIS acceptance test reopens the generated `.qgs`, obtains the canonical layer's real ID and the embedded QML, and asserts the same ID is present; table name and display name are not used as the identity token. |
| FR/AC-QCLR-002 ID-based `layer_property`/`aggregate`/`get_feature` and safe escaping | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_canonical_lookup_targets_the_embedded_id_for_every_expression_function`; `tests/acceptance/qfield_project_builder/test_qfield_canonical_layer_resolution_defect.py::test_qgis_344_parses_and_evaluates_all_captured_production_targets_by_layer_id` | Node captures the exact expressions emitted by the generated lookup function. The acceptance test checks every production layer target is the actual project ID, rejects the logical display name and physical table name, balances the expression, and evaluates it in isolated QGIS 3.44 without parser/evaluation errors. |
| FR/AC-QCLR-003 / AC-QCLR-008 valid canonical candidate and selected fields | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_valid_id_based_candidate_display_keeps_all_selected_identity_fields`; `tests/acceptance/qfield_project_builder/test_qfield_canonical_layer_resolution_defect.py::test_qgis_344_valid_row_returns_all_selected_identity_values` | The QField-shaped response handler displays a valid candidate. The isolated QGIS evaluation uses a real canonical layer and asserts `selected_ktsn`, `selected_korean_name`, and `selected_scientific_name` from the matched row. |
| FR/AC-QCLR-004 missing/invalid ID, wrong layer, missing context, no-match, ambiguous, malformed fail-closed | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_id_based_lookup_preserves_selected_fields_and_fail_closed_semantics`; `::test_invalid_id_and_missing_expression_context_are_unavailable`; `::test_no_match_ambiguous_and_lookup_failure_never_display_a_candidate` | Parameterized generated-JavaScript execution checks existing reason/matched semantics, refuses wrong-layer identity and missing context, and ensures failed canonical results do not create candidate cards or fabricated selected values. |
| FR/AC-QCLR-005 old generated project without embedded ID | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_old_generated_project_without_embedded_id_uses_only_documented_display_name_fallback` | A widget rendered without an embedded ID is exercised with the exact display-name compatibility target. The test rejects physical-table-name use and verifies a valid compatibility match remains usable. |
| FR/AC/AC-QCLR-006 legacy boundary | `tests/unit/test_qfield_canonical_layer_resolution_defect.py::test_canonical_branch_does_not_activate_legacy_csv_fallback` | The canonical branch calls only canonical lookup; the explicit legacy branch retains both CSV loading and matching. No canonical-resolution failure can activate the legacy branch. |
| AC-QCLR-007 saved/reloaded project round trip | `tests/acceptance/qfield_project_builder/test_qfield_canonical_layer_resolution_defect.py::test_saved_and_reloaded_project_keeps_the_same_id_in_widget_and_project` | The generated `.qgs` is written and reloaded in isolated QGIS; the canonical layer ID and embedded widget ID remain identical. |

## Execution commands

Pure generated-QML/unit coverage:

```bash
pytest -q tests/unit/test_qfield_canonical_layer_resolution_defect.py
```

QGIS 3.44 isolated-project coverage:

```bash
pytest -q tests/acceptance/qfield_project_builder/test_qfield_canonical_layer_resolution_defect.py -m qgis
```

The tests skip only when Node or a working QGIS 3.44 bridge is unavailable. They do not claim to
replace the separate physical-device QField gate described by AC-QCLR-008.
