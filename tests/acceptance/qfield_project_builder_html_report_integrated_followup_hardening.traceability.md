# HTML report integrated follow-up hardening traceability

Specification: [`specs/html-report-integrated-followup-hardening.md`](../../specs/html-report-integrated-followup-hardening.md)

Acceptance tests: [`qfield_project_builder/test_html_report_integrated_followup_hardening.py`](qfield_project_builder/test_html_report_integrated_followup_hardening.py)

Harness contract: [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md), section “HTML report integrated follow-up hardening fixture renderer”

This is an additive test round. It does not delete, weaken, or reinterpret any test mapped to the
approved baseline `specs/html-report-integrated-followup.md`. The synthetic fixtures execute the
same production report pipeline through a narrow acceptance adapter and do not open QGIS, a user
profile, a GeoPackage, a browser, or a network service.

| Acceptance criterion | Executable coverage |
|---|---|
| AC-IRF-018 | `test_ac018_collision_suffixes_move_every_value_without_overwrite_and_repeat_stably` supplies three source columns that normalize to one base key and rows containing zero, false, empty string, present null, genuine absence, and distinct sentinels. It verifies the exact deterministic base/`_2`/`_3` source-column mapping in column definitions; typed preservation under those same keys in integrated, detail, and payload rows; absence distinct from present null; unique, correctly aligned CSV cells; no stale suffix/overwrite; source-input immutability; and identical mappings/rows/CSV on repeat. |
| AC-IRF-019 | `test_ac019_direct_gpkg_failure_discloses_partial_fallback_without_hiding_success` forces the direct `project.gpkg` SQLite path to fail and supplies one loaded-layer fallback row, an identifiable omitted table, an identifiable omitted row, and an unverifiable inventory scope. It verifies the user-visible fallback/direct-path notice, complete known-omission listing, structured unknown count/completeness rather than zero/complete, an explicit non-complete inventory claim, and retention of the successful row in map, integrated table, detail, payload, summary, chart, filter, sort, and CSV results. |
| AC-IRF-020 | `test_ac020_one_malformed_geometry_preserves_its_row_join_and_aggregates_only_off_map` places one malformed row between two valid rows in one spatial table. It verifies successful table processing; all attributes and established joined values in table/detail/payload/CSV; unchanged three-row source count and occurrence aggregation; one stable invalid reason/count; no normalized or rendered geometry for only the malformed row; and rendering of both valid rows. `test_ac017_ac020_regression_zm_is_removed_before_xy_validity_and_never_substitutes_for_xy` additionally verifies the dimensional-input clause: a valid Point ZM renders only its X/Y pair, while valid Z/M cannot rescue malformed X/Y and that row still survives off-map. |

## Inherited Z/M regression

The dedicated `test_ac017_ac020_regression_zm_is_removed_before_xy_validity_and_never_substitutes_for_xy`
also traces to inherited **AC-IRF-017**, FR-IRF-026, and C-IRH-005. It supplements rather than
replaces the existing all-geometry-type structural AC-IRF-017 tests in
`test_html_report_integrated_followup.py`: Z/M ordinates are absent from normalized geometry,
integrated/detail/payload values, and CSV; valid X/Y still renders; malformed X/Y remains invalid;
and no Z/M ordinate becomes a substitute coordinate.

## Coverage boundary and approval gate

The new tests are executable headless data-contract tests. Until the new
`acceptance_api.render_html_report_fixture()` adapter is implemented, they follow this repository's
established per-function convention and report **SKIPPED**, not a false pass. Once present, the
adapter is required to invoke the production report pipeline and return snapshots parsed from its
actual output; a parallel test-only reimplementation is expressly non-conforming.

No criterion in the approved hardening specification is left uncovered or blocked by ambiguity.
These acceptance tests and this mapping await the user's explicit approval before implementation
work begins.

