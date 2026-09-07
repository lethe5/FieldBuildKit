# QField canonical runtime-lookup correction traceability

Specification: `specs/fieldbuild-kit-qfield-canonical-runtime-lookup-correction.md`

Executable acceptance test: `tests/acceptance/qfield_project_builder/test_qfield_canonical_runtime_lookup_correction.py`

The automated tests build a tiny accepted/synonym canonical workbook into real Type 1–3 projects,
inspect the delivered project-local resource and provenance, and exercise the emitted QML/JavaScript
lookup route through a QField-compatible adapter. They do not claim that QGIS Desktop expression
evaluation proves iPhone QField behavior.

| Criterion | Test evidence |
|---|---|
| AC-QCR-001 / FR-QCR-001–002 | `test_ac_qcr_001_type1_to3_project_contains_minimal_relative_verified_runtime_resource` runs for all Type 1–3 projects. It checks relative in-project delivery, SHA-256/byte-size/provenance, deterministic two-row canonical projection, absence of source workbook/path/URL, and absence of non-minimal source fields. |
| AC-QCR-002 / FR-QCR-003 | `test_ac_qcr_002_ac_qcr_003_accepted_and_synonym_use_resource_without_expression_lookup` verifies accepted and synonym keys both emit the accepted Korean name, preserved raw accepted scientific name, and accepted KTSN into candidate and write-back input. |
| AC-QCR-003 / FR-QCR-004 | The same test directly asserts that the actual generated canonical lookup fragment contains the runtime-resource loader, its path/provenance bindings, and `FileUtils.readFileContent`; it rejects `layer_property`, `aggregate`, and `get_feature`, then runs the route with expression operations forbidden and verifies the declared local resource read. This is the new-project route that supersedes CTLD/QCLR's expression/layer-ID route. |
| AC-QCR-004 / FR-QCR-005–006 | `test_ac_qcr_004_failure_matrix_is_fail_closed_without_expression_or_legacy_fallback` covers missing/unreadable resource, unknown schema, truncated record, provenance mismatch, consistency failure, and blank accepted output with exact unavailable/invalid reasons; `test_ac_qcr_004_normal_no_match_and_ambiguity_do_not_guess_or_write_back` covers normal no-match and multi-accepted-group ambiguity. Every non-match/failure has no candidate/write-back input and no fallback trace. |
| AC-QCR-005 / FR-QCR-007 | `test_ac_qcr_005_ac_qcr_006_preserve_gpkg_and_legacy_but_do_not_create_resource_for_boundaries` keeps `ktsn_taxonomy_reference`/`식물 분류 참조표`, confirms HTML-report taxonomy reads the GPKG rather than the resource, and confirms explicit legacy compatibility remains on its CSV branch. |
| AC-QCR-006 / FR-QCR-001, 006, 008 | The same boundary test verifies no resource for all identification-disabled Type 1–3 builds and Type 4. `test_ac_qcr_006_resource_stage_failures_do_not_promote_partial_projects` injects materialization, schema-validation, and provenance-write failures and requires no promoted output. |
| AC-QCR-007 | `test_ac_qcr_007_iphone_qfield_release_device_gate` is deliberately `manual`/`device`/skipped. The release record must include only app/project build identifiers, QField+iPhone/OS version, comparison key, absence of `canonical_taxonomy_lookup_failed`, and the three selected values; it must not include an API key, photo/image bytes, or precise coordinates. This is required release evidence and cannot be replaced by automated Desktop or simulated-QField tests. |

## Known automated boundary

The old-project non-migration portion of AC-QCR-006 requires a frozen pre-QCR project and a real
QField open/export path. The current acceptance harness has no such device runtime; it remains a
manual release verification alongside AC-QCR-007. The automated suite still verifies the new-project
atomicity, Type 1–3-disabled, Type 4, canonical-GPKG, and legacy-CSV boundaries above.
