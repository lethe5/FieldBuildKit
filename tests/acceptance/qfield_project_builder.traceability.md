# Traceability Matrix — QField Project Builder

> Specification: `specs/qfield-project-builder.md` (approved MVP baseline, per the user's
> explicit approval: *"I explicitly approve specs/qfield-project-builder.md as the MVP
> product-specification baseline."*).
> Tests: `tests/acceptance/qfield_project_builder/`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`.
>
> **AC-QPB-009 narrowed by a later `test-designer` round (2026-08-28; Decision Log D-74/D-78)** —
> Type 2/3's `observation_photo` table is removed entirely; the row/note below are annotated in
> place (struck through, not deleted), and this round's own new coverage
> (AC-QPB-112/113/114) lives in
> `qfield_project_builder_observation_photo_removal.traceability.md`, not in this file.

Only MVP-scoped acceptance criteria (per Section 4.1/18.1–18.5, plus AC-QPB-051/052/053 — see
the "Section-4/Section-18 boundary flags" note below) are covered. Post-MVP criteria
(AC-QPB-040–050, Section 4.2/13/18.6) are explicitly out of scope for this stage and are not
mapped below, per the task instructions.

Legend for the **Automation** column:
- **auto** — runs and asserts automatically against the implementer-provided harness (may still
  require the `qgis` marker's runtime, which is skipped gracefully when unavailable).
- **auto (proxy)** — automates a faithful proxy for the criterion's underlying mechanism, not a
  literal end-to-end drive of a GUI/device (documented per-row).
- **manual/device (documented, skipped)** — a real test function exists, explicitly marked
  `manual`/`device` and skipped with a reason, because it requires a physical device, an
  installer on a target OS, or GUI interaction this harness cannot drive.
- **blocked on O-9 (documented, skipped)** — a real test function exists, skipped because the
  criterion itself references an undetermined version matrix (Open Question O-9); not a
  test-design gap, a specification-completeness gap.

| AC ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-001 | Project opens without repair warning | `test_geopackage_common.py::test_ac001_project_opens_without_repair_warning` | auto |
| AC-QPB-002 | Every domain UUID valid/unique/non-null | `test_geopackage_common.py::test_ac002_every_domain_uuid_is_valid_unique_and_non_null` | auto |
| AC-QPB-003 | No domain relation references `fid` | `test_geopackage_common.py::test_ac003_no_domain_relation_references_fid` | auto |
| AC-QPB-004 | `PRAGMA foreign_key_check` returns zero rows | `test_geopackage_common.py::test_ac004_foreign_key_check_returns_zero_rows` | auto |
| AC-QPB-005 | Geometry layers/CRS match schema by type | `test_geopackage_schema_by_type.py::test_ac005_geometry_layers_and_crs_match_schema_for_type` | auto |
| AC-QPB-006 | Spatial index exists per geometry column | `test_geopackage_common.py::test_ac006_spatial_index_exists_for_every_geometry_column` | auto |
| AC-QPB-007 | `cover` outside 0–100 rejected | `test_geopackage_schema_by_type.py::test_ac007_cover_outside_0_100_is_rejected` (+ boundary-acceptance complement `test_cover_within_0_100_is_accepted`) | auto |
| AC-QPB-008 | Type-1 photo fields optional (0/1/2/3) | `test_geopackage_schema_by_type.py::test_ac008_type1_photo_field_combinations_are_all_accepted` (+ `test_type1_layer_has_exactly_three_relation_free_photo_fields`) | auto |
| AC-QPB-009 (narrowed; Decision Log D-74, 2026-08-28 — see note below) | ~~Type-2/3 photo relations are zero-or-more;~~ a Type-2 `survey`/Type-3 `plot` with zero related photo records is accepted (never producing `broken_attachment_reference`/`invalid_attachment_path`); existing photo record needs a valid relative path, and a missing referenced file is reported via the `broken_attachment_reference` issue code (revised; Decision Log D-23); a malformed stored path (empty/whitespace/absolute/UNC/`file://`/traversal) is reported via the distinct `invalid_attachment_path` issue code, and never collides with `broken_attachment_reference` (DR-QPB-012). **The struck-through "or observation" scope above no longer applies (Decision Log D-74): `observation_photo` is removed entirely for Type 2/3, replaced by three inline photo-path columns on `observation` — see AC-QPB-112/AC-QPB-114 in `qfield_project_builder_observation_photo_removal.traceability.md`.** | `test_geopackage_schema_by_type.py::test_ac009_parent_with_zero_related_photos_is_accepted` (unaffected by D-74), ~~`::test_ac009_observation_with_zero_related_photos_is_accepted`~~ **(retired by the D-74 round — this test's own premise, a Type-2/3 `observation` with zero related `observation_photo` rows, is now moot; see AC-QPB-114 in the new round's own file for its replacement)**, `::test_ac009_photo_record_needs_valid_path_and_missing_file_is_a_broken_attachment`, `::test_ac009_valid_relative_attachment_path_is_accepted`, `::test_ac009_malformed_attachment_path_is_rejected_at_save_time` (parametrized: `empty`, `whitespace_only`, `posix_absolute`, `windows_drive_absolute`, `unc_path`, `file_uri`), `::test_ac009_malformed_attachment_path_is_detected_by_validate_project` (parametrized: the same six plus `traversal_escapes_project_root`), `::test_ac009_valid_relative_path_with_absent_file_is_broken_not_invalid_attachment_path` — all of the latter tests use `survey_photo`, unaffected by D-74 | auto |
| AC-QPB-010 | No missing-layer warning after path move | `test_qgis_project_config.py::test_ac010_ac014_project_reopens_without_missing_layer_warning_after_move` (+ `test_qgs_and_gpkg_paths_are_relative_to_each_other`) | auto |
| AC-QPB-011 | Child record created from parent form saved/associated | `test_qgis_project_config.py::test_ac011_child_record_created_via_relation_is_saved_and_associated` | auto (proxy — see note 1) |
| AC-QPB-012 | UUID auto-generated, not normally editable | `test_qgis_project_config.py::test_ac012_uuid_field_is_autogenerated_and_not_normally_editable` | auto |
| AC-QPB-013 | FK field shows human-readable name via Relation Reference | `test_qgis_project_config.py::test_ac013_foreign_key_field_uses_relation_reference_widget` | auto (proxy — see note 1) |
| AC-QPB-014 | Attachment paths remain relative/valid after round trip | `test_qgis_project_config.py::test_ac010_ac014_project_reopens_without_missing_layer_warning_after_move` | auto (proxy — see note 2) |
| AC-QPB-015 | Type-4 symbology switches red/green on `is_field_checked` | `test_geopackage_schema_by_type.py::test_ac015_community_symbology_rule_exists_in_qgs_project` | auto (proxy — see note 1) |
| AC-QPB-016 | Opens in each supported QGIS/QField version | `test_qgis_project_config.py::test_ac016_opens_in_every_explicitly_supported_qgis_and_qfield_version` | **blocked on O-9** (documented, skipped) |
| AC-QPB-017 | Valid VWorld key + online mode -> layer loads | Datasource-configuration half (a fake key CAN honestly verify): `test_basemap_online.py::test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully`. "Opens without a repair warning" half (requires a live, valid VWorld key; see note 5): `test_basemap_online.py::test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key` (`network`-marked, skipped by default; local QGIS/PyQGIS only, not iPhone-QField proof) | auto (datasource-configuration only) / network (opt-in — required for the "opens successfully" half; not verified by the default, automatic test run) |
| AC-QPB-018 | MBTiles coverage contains approved bbox at every zoom | `test_basemap_offline.py::test_ac018_ac019_mbtiles_coverage_and_metadata_match_request` | auto |
| AC-QPB-019 | MBTiles metadata bounds/format/min/max zoom correct | `test_basemap_offline.py::test_ac018_ac019_mbtiles_coverage_and_metadata_match_request` | auto |
| AC-QPB-020 | Final `.mbtiles` never exceeds 1 GiB | `test_basemap_offline.py::test_ac020_final_mbtiles_never_exceeds_1_gib` (+ `test_offline_build_aborts_and_cleans_up_when_actual_output_would_exceed_1_gib`) | auto |
| AC-QPB-021 | Estimate > 900 MiB blocks generation | `test_basemap_offline.py::test_ac021_estimate_over_900_mib_blocks_generation` (+ `test_estimate_within_threshold_does_not_block`) | auto |
| AC-QPB-022 | MBTiles renders correctly in each supported version | `test_basemap_offline.py::test_ac022_mbtiles_renders_correctly_in_every_supported_qgis_qfield_version` | **blocked on O-9** (documented, skipped) |
| AC-QPB-023 | Cancelled offline build leaves no partial deliverable | `test_basemap_offline.py::test_ac023_cancelled_build_leaves_no_partial_deliverable` | auto |
| AC-QPB-024 | Folder copied to new local path opens successfully | `test_transfer_and_validation.py::test_ac024_project_folder_copied_to_new_local_path_opens_successfully` | auto |
| AC-QPB-025 | Computer->phone->computer round trip preserves edits | `test_transfer_and_validation.py::test_ac025_computer_to_phone_to_computer_round_trip_preserves_edits` | **manual/device** (documented, skipped) |
| AC-QPB-026 | No QFieldSync packaging step invoked/required | `test_transfer_and_validation.py::test_ac026_transfer_workflow_never_requires_qfieldsync` (+ `test_readme_transfer_ko_covers_required_instructions`) | auto |
| AC-QPB-027 | MANIFEST.json detects missing attachment/db/basemap, reported via the `missing_manifest_file` issue code | `test_transfer_and_validation.py::test_ac027_manifest_detects_a_missing_required_file` (parametrized: attachment/database/basemap) | auto |
| AC-QPB-028 | Transfer paths function on target platform (4 combos) | `test_transfer_and_validation.py::test_ac028_transfer_path_functions_correctly_on_target_platform` (parametrized) | **manual/device** (documented, skipped) |
| AC-QPB-029 | Missing QGIS -> clear non-technical error, no crash | `test_runtime_detection.py::test_missing_runtime_produces_a_clear_actionable_error_not_a_crash` | auto |
| AC-QPB-030 | Existing output dir never silently overwritten (non-empty and empty cases) | `test_error_handling.py::test_ac030_existing_output_directory_is_never_silently_overwritten` (non-empty, sentinel-file case), `::test_ac030_existing_empty_output_directory_is_never_silently_overwritten` (empty pre-existing directory case; note 4) | auto |
| AC-QPB-031 | Failed build leaves no partial project at final path | `test_error_handling.py::test_ac031_a_failed_build_leaves_no_partial_project_at_the_final_path` | auto |
| AC-QPB-032 | Packaged Windows/macOS installers start app, complete wizard | `test_error_handling.py::test_ac032_packaged_application_starts_and_completes_wizard_on_target_os` (parametrized: Windows/macOS) | **manual** (documented, skipped) + partially blocked on O-9 (exact OS versions) |
| AC-QPB-051 | MOLIT/VWorld KOGL Type-1 attribution present (online+offline+manifest) | `test_basemap_online.py::test_ac051_molit_vworld_attribution_present_online`, `test_basemap_offline.py::test_ac051_molit_vworld_attribution_present_offline` | auto |
| AC-QPB-052 | Quota/auth/rate-limit error terminates gracefully, no partial `.mbtiles` | `test_basemap_offline.py::test_ac052_provider_error_terminates_gracefully_with_no_partial_mbtiles` (parametrized: quota/auth/rate-limit) | auto (fault-injected) |
| AC-QPB-053 | QGIS 3.44 LTR runtime check succeeds without pip-installed PyQGIS | `test_runtime_detection.py::test_detected_qgis_344_lts_passes_verification_without_pip_installed_pyqgis` | auto |
| AC-QPB-054 | Consent declined -> no key embedded, online layer omitted | `test_basemap_online.py::test_ac054_declined_consent_omits_key_and_online_layer` | auto |
| AC-QPB-055 | Consent accepted -> key only in `.qgs` online-layer URL | `test_basemap_online.py::test_ac055_accepted_consent_embeds_key_only_in_qgs_online_layer_url` | auto |
| AC-QPB-056 | Offline build references only local `.mbtiles`, no key anywhere | `test_basemap_offline.py::test_ac056_offline_project_references_only_local_mbtiles_no_key_anywhere` | auto |
| AC-QPB-057 | MANIFEST.json: boolean security-warning flag only, never the key | `test_basemap_online.py::test_ac057_manifest_contains_only_a_boolean_security_warning_flag` | auto |
| AC-QPB-058 | "Remember this key" -> OS credential store; else session-only. **Revised, Decision Log D-53** (Section 18.5): the local storage mechanism changed from the OS credential store (`keyring`) to an application-managed, password-derived, locally-encrypted `credentials.enc` file; the consent-gated opt-in behavior itself is unchanged. See note 3 — this existing test remains valid, unchanged, under that revision. | `test_basemap_online.py::test_ac058_remember_key_uses_os_credential_store_not_plaintext` (+ `test_key_not_remembered_by_default_across_sessions`) | auto (proxy — see note 3) |
| AC-QPB-059 | Unicode display name -> valid ASCII slug | `test_naming.py::test_slug_is_derived_and_ascii_safe_for_unicode_display_names` (+ `test_slug_never_exceeds_64_characters`) | auto |
| AC-QPB-060 | Blank/path-traversal/reserved names rejected | `test_naming.py::test_blank_and_path_traversal_names_are_rejected`, `::test_windows_reserved_filenames_are_rejected`, `::test_rejected_name_never_silently_becomes_a_reserved_or_traversal_slug` | auto |
| AC-QPB-061 | Distinct valid `project_id` per project, name-independent | `test_naming.py::test_each_generated_project_gets_a_distinct_valid_project_id` | auto |
| AC-QPB-068 | Online layer connects via QGIS's native WMTS provider at the capabilities endpoint; no `type=xyz`/manually-templated per-tile datasource; offline MBTiles pipeline unaffected | `test_basemap_online.py::test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully` (datasource-shape assertions; the offline-pipeline-unaffected half is covered separately by AC-QPB-018/056's own `test_basemap_offline.py` tests, which continue to exercise concrete per-tile GetTile URLs unchanged) | auto (offline-safe proxy — see note 5) |

## Notes on automation approach (not ambiguity — testability/feasibility notes)

1. **AC-QPB-011/013/015** — these describe interactive QGIS Desktop/QField GUI behavior (embedded
   relation widgets, Relation Reference display, rendered symbology). They are verified by
   inspecting the generated `.qgs` project's relation/widget/renderer configuration (via PyQGIS
   or direct XML), which is the mechanism that produces the described behavior, rather than by
   physically driving the GUI. A residual, purely visual/interactive check (e.g. actually clicking
   through QGIS Desktop or QField) is not automated by this harness and is expected to remain part
   of the manual QA supplement alongside AC-QPB-025/028.
2. **AC-QPB-014** — the full computer->phone->computer round trip requires a physical device
   (see AC-QPB-025). The relative-path-survives-a-move behavior it depends on is automated as a
   proxy (moving the folder to an arbitrary new local path and re-validating), consistent with
   how NFR-QPB-021/022 themselves frame the requirement.
3. **AC-QPB-058** — the OS credential store itself is outside this harness's black-box reach (it
   would require inspecting the running desktop application's OS keychain access, not the
   generated project artifact). The test verifies the artifact-level guarantee (the key is never
   persisted in plaintext anywhere in the delivered project either way), which is what these
   acceptance tests can directly observe; full credential-store behavior verification is a
   supplement for manual/integration QA of the desktop application itself, not the generated
   project.
   **Update (Decision Log D-53/D-55, 2026-08-25):** the desktop application's own local storage
   mechanism changed from the OS credential store (`keyring`) to an application-managed,
   password-derived, locally-encrypted `credentials.enc` file — this test's own reasoning above
   applies identically to that new mechanism (it never asserted *how* the key is retained
   locally, only that the generated project artifact never leaks it), so it remains valid,
   correct, and unchanged by this revision. The new internal-mechanism criteria this revision
   introduces (`AC-QPB-089`–`093`/`097`, `NFR-QPB-073`) are **not** addable to this file's own
   table, because verifying them requires unit-level tests against the desktop application's own
   internal modules (`qfield_builder.credential_store`, wizard-page dialog/prompt logic) — outside
   this black-box harness's convention and outside this role's own file-scope boundary. See the
   dedicated
   [`qfield_project_builder_credential_storage_mechanism.traceability.md`](qfield_project_builder_credential_storage_mechanism.traceability.md)
   for the full analysis, including exactly what test coverage is still missing and why it could
   not be added by this round.
4. **AC-QPB-030 empty-pre-existing-directory case (stakeholder-directed addition, 2026-08-11).**
   A reviewer found that neither E-QPB-008 nor AC-QPB-030's wording carries an emptiness
   qualifier ("If the chosen output directory already exists, the application must not overwrite
   it silently"), but the only approved test exercised a non-empty pre-existing directory (via a
   sentinel file). `test_ac030_existing_empty_output_directory_is_never_silently_overwritten` adds
   the empty-directory case: the directory must still exist afterward and remain empty (not merely
   "no new project files" — literally empty), i.e. it must not be deleted, recreated, or populated.
   Per the stakeholder's explicit instruction, an explicit "replace-with-backup" operation was also
   checked for separately: as of this addition, `qfield_builder/build.py`'s only reference to
   "replace... with a backup" is the *text* of the `output_dir_exists` error message
   (`build.py:159`) — there is no corresponding parameter, config flag, or code path in
   `build_project()`, `acceptance_api.py`, or elsewhere in `qfield_builder/` that implements an
   actual replace/overwrite/force operation (confirmed by reading `build.py` end-to-end and
   grepping the package for `replace|overwrite|force`). **No explicit replace operation currently
   exists to test separately.** This is not a gap in test design; there is nothing yet to test.
   When such an operation is implemented, a dedicated test requiring explicit user authorization
   before any replace/backup occurs should be added at that time.
5. **AC-QPB-068 (Decision Log D-29 correction, 2026-08-14).** The prior version of
   `test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully` asserted a
   `/Base/`-style path-segment layer name, which was the old, now-superseded per-tile XYZ
   GetTile URL shape (FR-QPB-072 original). This has been corrected to assert the new,
   spec-mandated QGIS-native-WMTS datasource shape instead: the `url=` parameter references the
   VWorld WMTS capabilities endpoint, the selected layer name appears as the `layers=` query
   parameter (not a path segment), and the datasource contains neither a `type=xyz` marker nor a
   raw `{z}/{y}/{x}`-style per-tile template. All three corrected assertions pass against the
   current implementation. See also the now-resolved testability finding in "Ambiguities / gaps
   found" below regarding this same test's separate, pre-existing `opens_without_repair_warning`
   assertion: per explicit stakeholder decision (2026-08-14), that assertion has been removed from
   this offline-safe proxy test (it can no longer be honestly verified with a fake key under the
   D-29 WMTS architecture) and the genuine "opens without a repair warning" check has moved
   exclusively to the network-gated `test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key`,
   which now also asserts `missing_layer_warning is False` in addition to
   `opens_without_repair_warning is True`. AC-QPB-017 is therefore **not** fully verified by the
   default, automatic-by-default test run — see its updated row above and the resolved finding
   below.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- ~~**AC-QPB-009 exact trigger mechanism.**~~ **Resolved** (Decision Log D-23, sixth clarification
  round). The prior draft of this criterion referenced an undefined "marked field-complete"
  concept and an "at least one related photo" mandatory rule; both are corrected in the approved
  specification. AC-QPB-009 now requires only that a record with zero related photos is accepted
  on save and by `validate_project()`, and that an existing photo record with a path referencing a
  file missing from the project folder is reported as a broken attachment. Tests now assert this
  directly (`test_ac009_parent_with_zero_related_photos_is_accepted`,
  ~~`test_ac009_observation_with_zero_related_photos_is_accepted`~~,
  `test_ac009_photo_record_needs_valid_path_and_missing_file_is_a_broken_attachment`); no
  ambiguity remains. **Further narrowed by a later `test-designer` round (Decision Log D-74,
  2026-08-28), not re-opening this original resolution:** `observation_photo` is removed entirely
  for Type 2/3, replaced by three inline photo-path columns on `observation` mirroring Type 1's
  `inventory_observation` — `test_ac009_observation_with_zero_related_photos_is_accepted`'s own
  premise (a Type-2/3 `observation` with zero related `observation_photo` rows) is therefore moot
  and that test was retired, not merely edited; its replacement coverage is new AC-QPB-112/
  AC-QPB-114, tested in `test_observation_photo_removal.py` — see
  `qfield_project_builder_observation_photo_removal.traceability.md` for the full record. The
  `survey`/`plot`-level zero-related-photos rule this note otherwise describes is entirely
  unaffected.
- **`missing_manifest_file` / `broken_attachment_reference` code split (stakeholder correction,
  2026-08-10).** The prior pass had reused a single `missing_attachment_file` code across two
  different integrity layers: the manifest-declared-file-absent check (AC-QPB-027) and the
  GeoPackage-photo-record-path-absent check (AC-QPB-009). Per explicit stakeholder direction these
  are now two distinct codes — `missing_manifest_file` (AC-QPB-027) and `broken_attachment_reference`
  (AC-QPB-009) — documented separately in `HARNESS_CONTRACT.md`, and
  `test_ac027_manifest_detects_a_missing_required_file` /
  `test_ac009_photo_record_needs_valid_path_and_missing_file_is_a_broken_attachment` have been
  updated accordingly. A record with zero related photo rows continues to produce neither code
  (Decision Log D-23).
- ~~**`invalid_attachment_path` code — documented, not yet exercised by a dedicated test.**~~
  **Resolved** (stakeholder-required dedicated coverage pass, 2026-08-10). Per DR-QPB-012 and
  NFR-QPB-020–022, `invalid_attachment_path` now has dedicated coverage in
  `test_geopackage_schema_by_type.py`: a valid relative path is accepted
  (`test_ac009_valid_relative_attachment_path_is_accepted`); empty, whitespace-only, POSIX
  absolute, Windows drive-letter absolute, UNC, and `file://` paths are rejected at save time via
  `attempt_feature_save` (`test_ac009_malformed_attachment_path_is_rejected_at_save_time`); all
  seven malformed shapes (those six plus `..`-traversal escaping the project root) are reported by
  `validate_project()` when baked into the GeoPackage directly, simulating imported/externally
  edited/corrupted data (`test_ac009_malformed_attachment_path_is_detected_by_validate_project`);
  and a syntactically valid relative path whose target file is absent is confirmed to produce
  `broken_attachment_reference` and never `invalid_attachment_path`
  (`test_ac009_valid_relative_path_with_absent_file_is_broken_not_invalid_attachment_path`). Per
  `HARNESS_CONTRACT.md`'s new "Save-time vs. `validate_project`-only enforcement" note,
  `..`-traversal is deliberately *not* asserted as save-time-rejected (only `validate_project`-
  caught), because determining whether a `..`-relative path escapes the project root requires
  resolving it against the actual project folder location — context a single static QGIS
  field-constraint expression does not have, unlike the other six purely syntactic shapes. No
  ambiguity remains; this is a documented, deliberate enforcement-layer split, not a gap.
- **AC-QPB-016 / AC-QPB-022 exact version matrix.** Both criteria require testing against "each
  explicitly supported QGIS and QField version," but NFR-QPB-001/Open Question O-9 explicitly
  states this matrix is not yet pinned and "must not be invented... without verification."
  Per the ambiguity-handling procedure, no version list has been guessed; both are written as
  real, parametrizable test functions that are currently skipped with an explicit reason citing
  O-9, to be filled in once the release-gate compatibility matrix is resolved.
- **AC-QPB-025 / AC-QPB-028 / AC-QPB-032 hardware/installer dependence.** These are not
  specification ambiguities — the required behavior is fully and unambiguously described — but
  they inherently require physical iOS/Android devices, real platform installers, and (for
  AC-QPB-032) partially the same O-9 OS-version matrix. They are documented as explicit, skipped
  `device`/`manual` test cases (a standing manual-QA checklist) rather than omitted from
  traceability.
- **FR-QPB-094 cross-reference.** FR-QPB-094 states the validation report must confirm "the
  checks in Section 17 (Acceptance Criteria)," but in the approved specification, Section 17 is
  "Out of Scope" and Section 18 is "Acceptance Criteria" — this looks like an off-by-one
  cross-reference slip in the specification text itself. It does not block testability (the
  intent — Section 18's acceptance criteria — is unambiguous from context), but is worth the
  spec-writer's attention for a future revision.
- ~~**AC-QPB-017's `opens_without_repair_warning` check is no longer offline-safe under the D-29
  WMTS connection mechanism (newly surfaced, 2026-08-14; flagged, not silently fixed).**~~
  **Resolved (explicit stakeholder decision, 2026-08-14).** While correcting the stale
  `/Base/`-path-segment regex in
  `test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully` to match the new
  WMTS datasource shape (AC-QPB-068), running the full corrected test against the current
  implementation revealed that the test's separate, pre-existing, *untouched*
  `report["opens_without_repair_warning"] is True` assertion (verified via
  `acceptance_api.validate_project`) now genuinely fails with this test's placeholder fake key
  (`ACCEPTANCE-TEST-FAKE-KEY-0000`) — confirmed independently (not just by the test) by querying
  the real VWorld endpoint directly with the fake key, which returns a genuine OGC
  `ExceptionReport` ("등록되지 않은 인증키입니다." / not a registered key). Root cause: the old
  `type=xyz` raster layer never needed a live, authentic capabilities response at project-open
  time, which is what let the offline-safe test use a placeholder key; QGIS's native WMTS
  provider (D-29) instead performs a real GetCapabilities negotiation at open time, so a fake key
  now correctly and expectedly produces `opens_without_repair_warning: False`,
  `missing_layer_warning: True`. This is genuine, correct, spec-consistent behavior for a fake
  key, not a defect.

  The stakeholder's explicit decision: accept this consequence, and move the "opens without a
  repair warning" check to the already-existing `network`-marked, real-key variant of this test
  only. Accordingly:
  - `test_ac017_online_vworld_layer_is_configured_and_project_opens_successfully` (offline-safe
    proxy) no longer calls `validate_project()`/asserts `opens_without_repair_warning`; it now
    verifies only the datasource-shape/configuration half of AC-QPB-017 (AC-QPB-068), with an
    in-line comment explaining why the "opens successfully" half is out of scope here.
  - `test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key` (network-gated, skipped by
    default) has been strengthened to explicitly assert both `opens_without_repair_warning is
    True` and `missing_layer_warning is False` with a real key — it is now the sole test that
    genuinely verifies AC-QPB-017's "opens without a repair warning" claim.
  - The specification's own `AC-QPB-017` text (Section 18) was reviewed and left unchanged: it
    already reads "Given a valid VWorld API key," which already implied a live, valid-key,
    network-connected scenario for the "opens successfully" claim — this is a test-design/
    traceability-honesty correction reflecting what the approved wording always required, not a
    specification defect needing a new Decision Log entry.

  This is related to, but distinct from, the specification's own Open Question O-12 (exact WMTS
  TileMatrixSet/CRS/format values requiring a real key to confirm) — O-12 is about *constructing*
  a correct datasource; this finding was about *verifying* one offline with a necessarily-
  inauthentic key.

## Section 4 / Section 18.6 boundary flag (MVP vs. post-MVP labeling)

Section 18.6 is headed "Post-MVP acceptance criteria (do not block MVP)," but three criteria
placed under that heading — **AC-QPB-051, AC-QPB-052, AC-QPB-053** — are each individually
labeled `(MVP; ...)` in their own text, and each traces to requirements/decision-log entries that
are unambiguously MVP elsewhere in the specification (NFR-QPB-058/FR-QPB-074 attribution,
FR-QPB-088 quota/rate-limit handling, FR-QPB-009/FR-QPB-007a runtime verification — none of which
are listed as post-MVP anywhere else in Sections 4, 10, or 11). This looks like a section-heading/
individual-label inconsistency in the specification rather than an intentional post-MVP
placement. **These tests treat AC-QPB-051/052/053 as in-scope MVP criteria** (their individual
labels, which are more specific, are treated as authoritative over the enclosing section
heading), and this discrepancy is flagged here for the spec-writer/user to confirm or correct.
No other AC's MVP/post-MVP placement appeared inconsistent with its section grouping.

## Post-MVP acceptance criteria (not covered, by design)

AC-QPB-040 through AC-QPB-050 (Pl@ntNet/KTSN/occurrence-probability, Section 18.6) are explicitly
post-MVP per Section 4.2/Section 18.6's heading and are **not** covered by this test suite, per
the task instructions. No test files reference them.

**Update (2026-08-15, later round — this note is additive; nothing above this line was changed by
that round):** a subsequent `test-designer` round, authorized by Decision Log D-31–D-36, covers the
"guaranteed-manual baseline" slice of Section 13 (FR-QPB-100/101/104/105/106/107/112 and
AC-QPB-040–046/049/050/069–072). See
[`qfield_project_builder_post_mvp_identification.traceability.md`](qfield_project_builder_post_mvp_identification.traceability.md)
for that round's own, separate traceability table — this file's own content above remains exactly
as originally approved.
