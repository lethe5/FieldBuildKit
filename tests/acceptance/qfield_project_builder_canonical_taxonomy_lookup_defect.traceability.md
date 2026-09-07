# Canonical taxonomy lookup parser-defect traceability

Specification: specs/fieldbuild-kit-canonical-taxonomy-lookup-defect.md

Tests:

- tests/unit/test_canonical_taxonomy_lookup_defect.py
- tests/acceptance/qfield_project_builder/test_canonical_taxonomy_lookup_defect.py

This defect round does not modify the approved D-95 specification or source-selection contract.
After QCR's approved supersession, its expression coverage is limited to the retained
pre-QCR compatibility route rendered without a runtime-resource descriptor; it is not evidence
for a newly generated canonical project's QField runtime route. The unit tests execute generated
QML/JavaScript with Node only to capture that compatibility expression and exercise its
candidate/failure path. The acceptance tests then evaluate the captured expression in an isolated
QGIS process, using a real in-memory layer named 식물 분류 참조표; they skip when Node or a
working QGIS 3.44 bridge is unavailable. The delivered new-project local-resource route is owned
by the QCR acceptance and traceability artifacts.

| Criterion | Automated coverage |
|---|---|
| AC-CTLD-001 / FR-CTLD-001 | test_qgis_344_evaluates_captured_lookup_expression_without_parser_or_eval_error[valid] checks selected KTSN, Korean name, and scientific name from a valid canonical row; test_generated_widget_displays_a_valid_canonical_candidate checks the compatibility candidate model path. |
| AC-CTLD-002 / FR-CTLD-002 | test_qpb_lookup_captures_the_nested_expression_from_generated_qml captures the retained compatibility expression; the QGIS acceptance parametrization checks QgsExpression parser and evaluator status for both expressions. |
| AC-CTLD-003 / FR-CTLD-003 | The no-match parametrization verifies matched=false; the unit fail-closed contract test verifies no fabricated selection. |
| AC-CTLD-004 / FR-CTLD-004 | The ambiguous and malformed parametrizations verify no arbitrary accepted group/identity is selected; the generated failure-message test preserves the canonical failure surface. |
| AC-CTLD-005 / FR-CTLD-005 | test_canonical_branch_does_not_silently_use_legacy_csv_fallback verifies canonical and explicit legacy branches remain separate and canonical failure does not call the CSV matcher. |
| AC-CTLD-006 | test_widget_keeps_compatibility_candidate_and_failure_paths checks the generated compatibility widget contract and the existing canonical failure message. It intentionally makes no project-plugin lookup assertion: the plugin is not the new-project canonical lookup route. |

## Deliberate limits

The Python suite cannot launch QField or perform a physical-device photo upload. Candidate
rendering is exercised by executing the generated response handler with a deterministic Pl@ntNet
fixture; on-device QField loading remains a separate manual/device gate. The QGIS probe uses the
repository's existing isolated bridge and never constructs a QGIS application in the pytest
process. The QCR acceptance suite separately verifies the new-project local runtime resource,
the absence of canonical QGIS-expression operations, no canonical/legacy fallback, and its
physical-device release gate.
