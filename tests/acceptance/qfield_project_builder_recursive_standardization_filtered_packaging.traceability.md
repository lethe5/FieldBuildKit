# D-88 recursive accepted-name resolution and D-89 filtered packaging

This traceability addendum covers the two still-draft decision-log slices added to
`specs/qfield-project-builder.md`. Tests are deliberately acceptance-level: pure-Python matching
tests validate the resolution rules, while release-package tests inspect the ordinary PyInstaller
directory directly. No QGIS profile or real user profile is touched.

| Criterion | Executable coverage | Mode |
|---|---|---|
| AC-QPB-128: multi-hop `이명`/`원기재명` chain reaches terminal `정명`; fields come from terminal row | `test_post_mvp_ktsn_matching.py::test_ac128_follows_multiple_correct_list_hops_to_the_terminal_jungmyeong_row` | auto |
| AC-QPB-128: NIBR disambiguation at an intermediate hop; zero/multiple matches ambiguous | `test_post_mvp_ktsn_matching.py::test_ac128_applies_nibr_disambiguation_at_an_intermediate_hop`, `::test_ac128_zero_or_multiple_nibr_matches_at_an_intermediate_hop_are_ambiguous` | auto |
| AC-QPB-129: cycle/self-reference, missing target, blank/malformed/non-array/empty list, invalid candidate, conflicting `KTSN`/`KTNS`, and >64 transitions terminate fail-closed | `test_post_mvp_ktsn_matching.py::test_ac129_recursive_resolution_fails_closed_for_bad_or_unbounded_chains` (10 parametrized cases) | auto |
| AC-QPB-130: release bundle contains filtered lookup artifacts, exact schema/count, no raw table sources, and internally consistent manifest | `test_post_mvp_filtered_packaging.py::test_ac130_packaging_spec_stages_filtered_data_instead_of_raw_reference_tree`, `::test_ac130_release_package_contains_only_filtered_tables_and_consistent_manifest` | auto; package test skips when no release artifact is supplied |
| AC-QPB-131: all probability TIFFs retained byte-for-byte; filtered-only generated project remains usable and emits no raw table | `test_post_mvp_filtered_packaging.py::test_ac131_release_package_retains_every_probability_raster_byte_for_byte` (canonical release artifact boundary), `::test_ac131_filtered_only_project_build_emits_no_raw_table_sources` (explicit `legacy_compatibility`) | auto; real package test skips when artifact/source is absent |
| AC-QPB-132: missing/invalid filtered artifact fails before partial project promotion | `test_post_mvp_filtered_packaging.py::test_ac132_missing_or_invalid_filtered_artifact_fails_without_partial_project` (missing lookup and invalid manifest; explicit `legacy_compatibility`) | auto |

## Harness additions

`HARNESS_CONTRACT.md` documents `match_ktsn_with_national_list(...)`, an additive seam that has
the existing `match_ktsn` return shape but applies NIBR accepted-KTSN disambiguation at each
recursive hop. The filtered-only project tests use the existing `build_project()` seam and its
`_test_reference_data_dir` test hook; release-package tests discover `dist/FieldBuild Standalone.app` or
the path supplied through `QPB_PACKAGED_APP_PATH`.

## Red/green authoring result

At authoring time, before D-88/D-89 implementation, the recursive selection run produced
**5 failed, 6 passed, 2 skipped, 18 deselected**: the two NIBR cases skipped because the new
harness function was not yet exposed, and the direct recursive/safety assertions failed against
the pre-D-88 one-hop implementation (including a non-array `correct_list` crash). Ruff passed for
the new test files after formatting. The package-content test is expected to fail against the
currently existing raw-reference PyInstaller spec/app until D-89 implementation lands; absent
release artifacts are explicitly skipped rather than silently treated as passing.

## Scope/ambiguity notes

- The exact serialization names of the accepted-only and NIBR artifacts are not mandated by D-89;
  package inspection therefore identifies them by semantic filename (`accepted`/`nibr`) and uses
  the shipped manifest for provenance/hash consistency.
- `AC-QPB-131`'s generated-project branch constructs a synthetic, validated 20,914-row filtered
  bundle with one raster. This isolates the no-raw-input contract; full production raster byte
  coverage is asserted separately against the real raster directory when available.
