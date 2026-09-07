# Acceptance Tests

Executable acceptance tests live here, one set per feature, authored by the `test-designer` subagent from an approved specification under `specs/`.

Each feature's tests should be accompanied by a traceability file (e.g. `<feature>.traceability.md`) mapping every acceptance criterion ID (`AC-n`) in the corresponding spec to the test(s) that verify it.

## QField Project Builder

- Specification: [`specs/qfield-project-builder.md`](../../specs/qfield-project-builder.md) (approved MVP baseline).
- Tests: [`qfield_project_builder/`](qfield_project_builder/) (pytest).
- Traceability: [`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md).
- Test harness contract (what the `implementer` must expose for these tests to run):
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

No application code exists yet as of this writing. Every test that needs the
`qfield_builder.acceptance_api` module is written with `pytest.importorskip`, so the suite
currently **skips** (not fails) — this is the expected state before implementation exists.
Some criteria that require real QGIS/QField version pinning (Open Question O-9) or physical
iOS/Android devices are written as documented, explicitly skipped placeholders (`qgis`,
`device`, `manual`, `network` markers) rather than silently omitted; see the traceability file
for details on each.

### Post-MVP: identification subsystem (Section 13)

A later, separate `test-designer` round covers the "guaranteed-manual baseline" slice of
Section 13 (Pl@ntNet / KTSN / Occurrence Probability) authorized by Decision Log D-31–D-36:
`test_post_mvp_identification_plugin.py`, `test_post_mvp_reference_bundling.py`,
`test_post_mvp_plantnet_request_shape.py`, `test_post_mvp_ktsn_matching.py`, and
`test_post_mvp_manual_qfield_runtime.py`, all inside the same
[`qfield_project_builder/`](qfield_project_builder/) package (same specification, later round).

- Traceability:
  [`qfield_project_builder_post_mvp_identification.traceability.md`](qfield_project_builder_post_mvp_identification.traceability.md)
  (kept as its own file rather than merged into the MVP traceability file above, so the
  already-approved MVP traceability record is not touched by this later round).
- Test harness contract additions: the "Post-MVP: Section 13" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### D-96: wizard UI layout defect remediation

The approved UI defect specification
[`specs/fieldbuild-kit-wizard-ui-layout-defect.md`](../../specs/fieldbuild-kit-wizard-ui-layout-defect.md)
is covered by
[`qfield_project_builder_wizard_ui_layout.traceability.md`](qfield_project_builder_wizard_ui_layout.traceability.md).
The detailed headless Qt geometry,
scroll-boundary, control-policy, keyboard, API-secret, and canonical-Excel tests are in
[`tests/unit/test_wizard_ui_layout.py`](../unit/test_wizard_ui_layout.py), because they construct
the desktop application's real PySide6 widgets. The acceptance package adds real-wizard smoke
coverage in [`qfield_project_builder/test_wizard_ui_layout.py`](qfield_project_builder/test_wizard_ui_layout.py)
and an explicitly skipped `manual` Cocoa/DPI smoke placeholder for the display-only portion.
No test treats a static offscreen property as a substitute for a post-layout geometry check.

### D-88/D-89: recursive accepted-name resolution and filtered release packaging

The follow-up acceptance round adds recursive `correct_list` traversal (including deterministic
cycle/malformed-data bounds and NIBR disambiguation at intermediate hops) plus release-package
inspection for D-89's filtered reference bundle and retained probability TIFFs:
`test_post_mvp_ktsn_matching.py` and `test_post_mvp_filtered_packaging.py`.

- Traceability: [`qfield_project_builder_recursive_standardization_filtered_packaging.traceability.md`](qfield_project_builder_recursive_standardization_filtered_packaging.traceability.md).
- Harness addition: `match_ktsn_with_national_list(...)` in
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).
- Real reference-data fixtures used by these tests (`storage/reference/tables/
  tb_leco_nib_ktsn_dtl_gat.csv`, `storage/reference/rasters/bce_inverse_corrected_probability_maps/`)
  are gitignored, machine-local data — tests that depend on them skip gracefully (with a clear
  reason) when that data is absent, rather than failing.

### Post-MVP: Pl@ntNet API key consent-gated embedding (Decision Log D-45)

A later, separate `test-designer` round covers new Section 13.1a (FR-QPB-114–117), revised
Section 14.1 (NFR-QPB-071/072, NFR-QPB-019), and new Section 18.6 criteria AC-QPB-079–082 —
Decision Log D-45's extension of the VWorld online-layer consent-gated key-embedding exception
(Decision Log D-21) to the Pl@ntNet API key: `test_post_mvp_plantnet_key_embedding.py`, inside the
same [`qfield_project_builder/`](qfield_project_builder/) package (same specification, later
round).

- Traceability:
  [`qfield_project_builder_post_mvp_plantnet_key_embedding.traceability.md`](qfield_project_builder_post_mvp_plantnet_key_embedding.traceability.md)
  (kept as its own file, so neither of the two already-approved traceability records above is
  touched by this round's additions).
- Test harness contract additions: the "Post-MVP: Decision Log D-45" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Local credential-storage-mechanism change (Decision Log D-53/D-55) — no new executable test

A later `test-designer` round reviewed revised Section 14.1 (`NFR-QPB-012/018/072`, further
revised; new `NFR-QPB-073`) and new Section 18.5 criteria `AC-QPB-089`–`093`/`097` (Decision Log
D-53: replacing the OS credential store/`keyring` with an application-managed, locally-encrypted
`credentials.enc` file for the "Remember this key" opt-in; D-55: the retrieval-time password
re-prompt trigger point). It added **no new test file**, because these criteria concern the
desktop application's own internal storage/UI mechanism, not a generated-project artifact this
harness's black-box convention can reach, and the unit-level tests they require fall under the
`implementer` role's mandate, not `test-designer`'s file-scope boundary (`tests/acceptance/`
only). See
[`qfield_project_builder_credential_storage_mechanism.traceability.md`](qfield_project_builder_credential_storage_mechanism.traceability.md)
for the full analysis and exactly what coverage is still missing. The two pre-existing tests this
change touches (`AC-QPB-058`, `AC-QPB-082`) were confirmed to remain valid, unchanged.

### Korean field aliases (Decision Log D-56/D-57/D-58)

A later, separate `test-designer` round covers new `DR-QPB-071` (Section 7), new `FR-QPB-119`
(Section 9), new Section 8.5 (the full, per-survey-type Korean field-alias table), and new
`AC-QPB-098` (Section 18.2) — Decision Log D-56's proposal, now fully stakeholder-confirmed by
Decision Log D-57/D-58, that every attribute field on every layer of a generated project (except
a table's own UUID primary key) must carry a Korean-language display alias set via QGIS's
field-alias mechanism: `test_korean_field_aliases.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package (same specification, later round).

- Traceability:
  [`qfield_project_builder_korean_field_aliases.traceability.md`](qfield_project_builder_korean_field_aliases.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched
  by this round's additions).
- Test harness contract additions: the "Decision Log D-56/D-57/D-58" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md)
  (function 12, `inspect_field_aliases`).

### Standardized scientific-name display/persistence (Decision Log D-60/D-64)

A later, separate `test-designer` round covers `FR-QPB-106` (revised)/`FR-QPB-109` (further
revised) and new `AC-QPB-099` — Decision Log D-60's proposal (confirmed by D-64) that, after
identification, the displayed/persisted scientific name uses the standardized,
`taxon_full_nm`-derived name whenever some KTSN match exists, in preference order over Pl@ntNet's
own raw name: three new structural QML tests added to the existing
`test_post_mvp_identification_plugin.py`, plus two supplementary pure-Python `match_ktsn()`
reference-implementation tests added to the existing `test_post_mvp_ktsn_matching.py` (both inside
the same [`qfield_project_builder/`](qfield_project_builder/) package).

- Traceability: recorded as a 2026-08-26 addendum inside the existing
  [`qfield_project_builder_post_mvp_identification.traceability.md`](qfield_project_builder_post_mvp_identification.traceability.md)
  (this item directly extends FR-QPB-106/109/AC-QPB-04x-family criteria that file already owns —
  not a new file).
- Test harness contract additions: the `match_ktsn` addendum (function 9) in the "New (Decision
  Log D-64–D-69...)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Symbol styling configuration — wizard Step 6 (Decision Log D-61/D-65)

A later, separate `test-designer` round covers `FR-QPB-011` (further revised, new network clause
(d)), `FR-QPB-120`/`FR-QPB-121`/new `FR-QPB-123`, revised `NFR-QPB-080`, and new
`AC-QPB-100`–`102`/`104` — Decision Log D-61's proposal (confirmed and completed by D-65) for a
minimalist default point/polygon symbol plus an optional, offline-searchable Tabler SVG icon for
point markers: `test_symbol_styling.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package.

- Traceability:
  [`qfield_project_builder_symbol_styling.traceability.md`](qfield_project_builder_symbol_styling.traceability.md)
  (kept as its own file — a large enough feature to warrant one, per this project's own judgment
  call).
- Test harness contract additions: functions 13–15 (`fetch_tabler_icon_svg`,
  `search_bundled_tabler_icon_names`, `inspect_layer_renderer`) and the `symbol_styling`
  `build_project` config/return additions, in the "New (Decision Log D-64–D-69...)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### KTSN accepted-name lookup table / autofill (Decision Log D-62/D-66/D-67/D-68; D-70 follow-up)

A later, separate `test-designer` round covers new `DR-QPB-072` (Section 7), new
`FR-QPB-124`–`127` (Section 9), the revised Section 8.1/8.2/8.3
`selected_korean_name`/`selected_scientific_name`/`selected_ktsn` field-table entries, and new
`AC-QPB-105`–`108` — Decision Log D-62's investigation resolved by D-66 (architecture/scope), D-67
(synonym handling/derived fields), and D-68 (unconditional bundling scope): a real, indexed,
bundled lookup table backing a `ValueRelation` widget on `selected_korean_name`, with
`selected_scientific_name`/`selected_ktsn` becoming fully derived, read-only fields. A further,
separate follow-up `test-designer` round adds new `AC-QPB-109` — Decision Log D-70, closing Open
Question O-34 (raised by this same round's own "Flagged interaction..." finding below): `FR-QPB-105`
(Section 13.3)'s fail-early reference-data validation now has a second, independent trigger — a
Types 1-3 project being built at all, regardless of `identification_enabled` — made independently
testable by `AC-QPB-109`. All of the above:
`test_ktsn_lookup_table.py`, inside the same [`qfield_project_builder/`](qfield_project_builder/)
package.

- Traceability:
  [`qfield_project_builder_ktsn_lookup_table.traceability.md`](qfield_project_builder_ktsn_lookup_table.traceability.md)
  (kept as its own file — the largest of this batch of items, per this project's own judgment
  call). **Flagged a genuine interaction between `FR-QPB-127`'s unconditional-bundling scope and
  this suite's own pre-existing shared fixture defaults** — now confirmed, at the specification
  level, by Decision Log D-70 (Option (c): an accepted, already-established operational
  precondition) — but the *mechanical* shared-fixture-default housekeeping this implies remains
  explicitly deferred to a future round; see that file's own "Flagged interaction..." section and
  its "AC-QPB-109 addendum" section before any `implementer` work proceeds against `FR-QPB-127`/the
  new `FR-QPB-105` second trigger.
- Test harness contract additions: functions 16–17 (`inspect_editor_widget`,
  `derive_accepted_name_lookup_table`) and the `ktsn_lookup_table_name` `build_project` return
  addition, in the "New (Decision Log D-64–D-69...)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).
  `AC-QPB-109`'s own two new tests needed no harness-contract change.

### `identification_status` `ValueMap` widget (Decision Log D-63/D-69)

A later, separate `test-designer` round covers new `FR-QPB-122` and new `AC-QPB-103` — Decision
Log D-63's proposal (confirmed by D-69) that `identification_status` be constrained to a
fixed-list `ValueMap` selection (existing raw English enum strings, no Korean-language value-label
translation): two new tests added to the existing `test_qgis_project_config.py` (a narrowly scoped
single-field change, not large enough to warrant its own file — see that file's own rationale
note).

- Traceability:
  [`qfield_project_builder_identification_status_valuemap.traceability.md`](qfield_project_builder_identification_status_valuemap.traceability.md).
- Test harness contract additions: function 16 (`inspect_editor_widget`), reused unchanged from
  the KTSN-lookup-table round above, in the "New (Decision Log D-64–D-69...)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Manual QGIS install-path override (conformance-gap round; `FR-QPB-008`)

A later, separate `test-designer` round covers a real, zero-coverage conformance gap against the
already-approved MVP baseline: `FR-QPB-008` (Section 5.2, Decision Log D-10) has required, since
the original specification, that the application "attempt automatic detection of a supported QGIS
installation, and... allow the user to select the QGIS installation path manually when automatic
detection fails" — but no prior round ever implemented or tested the manual-override half of this
requirement (`qfield_builder/runtime.py`'s own missing-runtime error message already names a
`'QGIS 설치 위치 선택...'` option verbatim, but no such option, or any underlying function
accepting a manual path, existed anywhere in the codebase). This is a Category A conformance
defect, not a specification change: `test_qgis_manual_path_override.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package.

- Traceability:
  [`qfield_project_builder_qgis_manual_path_override.traceability.md`](qfield_project_builder_qgis_manual_path_override.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched by
  this round's additions).
- Test harness contract additions: the "New (test-designer conformance-gap round, 2026-08-27)"
  section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md) —
  extends the existing function 1 (`check_runtime`) with a new `manual_path` parameter, a
  clarified `force_missing` interaction, and a new `qgis_prefix_path` return key.

### Offline VWorld-key collection and drawing-canvas pan navigability (conformance-gap round; `E-QPB-003`/`FR-QPB-078`/`NFR-QPB-058`/`FR-QPB-025`)

A later, separate `test-designer` round covers two independent, real, already-diagnosed Category A
conformance gaps found via manual UI testing of the built desktop app — neither required a
specification change:

1. **Offline basemap generation never collects the VWorld API key.** `ConnectivityBasemapPage`
   only ever shows/collects `api_key_edit` for online mode; `offline_config()`/
   `ReviewAndBuildPage._collect_config()` never include `vworld_api_key` for offline mode; and
   `vworld_tiles.resolve_tile_fetcher()`'s raw `basemap_config["vworld_api_key"]` dict index then
   raises an unhandled `KeyError` whose bare repr (`"'vworld_api_key'"`) reaches the user as the
   entire error message (`생성 실패: 'vworld_api_key'`) — a message-quality defect against
   `E-QPB-003`'s "actionable error" requirement, confirmed by a real stakeholder screenshot.
2. **The wizard's interactive drawing canvas cannot be panned.** `MapCanvas` already has fully
   working pan support (`MODE_PAN`/`pan_by_pixels()`), but both wizard usages hardcode
   `"polygon"`/`"bbox"` mode with no secondary input path back to pan — so a real area of interest
   not already near the canvas's hardcoded default center is unreachable, confirmed by a real
   stakeholder device report.

New tests: `test_offline_vworld_api_key_collection.py`, `test_map_canvas_pan_navigability.py`,
inside the same [`qfield_project_builder/`](qfield_project_builder/) package. Each file's own
automated coverage is limited to what is verifiable through the existing black-box
`build_project()` contract or (for Bug 2) a `manual`-marked placeholder — the PySide6-widget-
internal halves of both bugs (wizard field-collection wiring; the underlying `MapCanvas`
mouse-event/mode-gating mechanism) are, like the credential-storage-mechanism round above, outside
`test-designer`'s own `tests/acceptance/`-only file-scope boundary and are routed to the
`implementer` role's `tests/unit/` mandate instead, with the exact contract fully specified in the
traceability file below rather than silently left unaddressed.

- Traceability:
  [`qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md`](qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched by
  this round's additions).
- Test harness contract additions: none — Bug 1's automated coverage uses the existing
  `build_project()` contract (function 4) unchanged; neither bug's PySide6-widget-internal half is
  exposed through `qfield_builder.acceptance_api` (see the traceability file's "Genuinely out of
  this harness's reach" sections for the exact, fully specified contract routed to `tests/unit/`
  instead).

### Type 2/3 `observation_photo` removal (Decision Log D-74/D-78)

A later, separate `test-designer` round covers new `DR-QPB-074`–`077` (Section 8.2/8.3), the
narrowed `AC-QPB-009`, new `AC-QPB-112`/`AC-QPB-114` (Section 18.1), and new `AC-QPB-113` (Section
18.6, post-MVP) — Decision Log D-74's stakeholder-directed removal of Type 2/3's `observation_photo`
child table (and its relation, `rel_observation_photo_observation`), replaced by three inline
photo-path columns on `observation` mirroring Type 1's `inventory_observation` exactly, and
Decision Log D-78's confirmation that this applies only to newly generated projects going forward
(no migration/backward-compatibility handling required or tested): new file
`test_observation_photo_removal.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package. This round also revised
`conftest.py`'s shared `SURVEY_TYPE_SCHEMAS`/`KOREAN_FIELD_ALIASES` fixtures (removing
`observation_photo`'s entries for Type 2/3, adding the three new fields' aliases to `observation`)
and retired one now-superseded pre-existing test from `test_geopackage_schema_by_type.py`.

- Traceability:
  [`qfield_project_builder_observation_photo_removal.traceability.md`](qfield_project_builder_observation_photo_removal.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched by
  this round's additions). The MVP baseline file
  ([`qfield_project_builder.traceability.md`](qfield_project_builder.traceability.md)) and the
  Korean-field-aliases file
  ([`qfield_project_builder_korean_field_aliases.traceability.md`](qfield_project_builder_korean_field_aliases.traceability.md))
  each received a small, non-destructive (struck-through, not deleted) annotation recording the
  side effects this round has on rows/tests they already own.
- Test harness contract additions: none — this round reuses `attempt_feature_save`/
  `validate_project` (functions 5/6), `inspect_editor_widget` (function 16), and
  `inspect_identification_widget` (function 10) unchanged; see the "New (test-designer round,
  2026-08-28)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Korean relation-widget display names (Decision Log D-73/D-77)

A later, separate `test-designer` round covers new `FR-QPB-128` (Section 9) and new `AC-QPB-111`
(Section 18.2) — Decision Log D-73's proposal, now fully stakeholder-confirmed by Decision Log
D-77 (six of the seven proposed names exactly as proposed; the seventh, `rel_observation_survey`,
corrected from "관찰" to "식물관찰"), that every relation embedded as a `QgsAttributeEditorRelation`
widget in a parent record's own attribute form (FR-QPB-056/FR-QPB-057) must receive a Korean
display name via the relation's own separate `name()` property — never its stable `id()`, which
remains completely unchanged: `test_korean_relation_display_names.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package (same specification, later round).

- Traceability:
  [`qfield_project_builder_korean_relation_display_names.traceability.md`](qfield_project_builder_korean_relation_display_names.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above — including
  the textually distinct Korean *field*-alias round above — are touched by this round's
  additions).
- Test harness contract additions: the "Decision Log D-73/D-77" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md)
  (function 18, `inspect_relations`).

### Korean layer display names (Decision Log D-80/D-84)

A later, separate `test-designer` round covers new `DR-QPB-078` (Section 7), new `FR-QPB-130`
(Section 9), new Section 8.7 (the confirmed, per-survey-type Korean layer-display-name table plus
the KTSN-lookup-layer bonus row), and new `AC-QPB-118` (Section 18.2) — Decision Log D-80's
proposal (identifying that every generated domain survey-data layer must receive a Korean display
name via `QgsMapLayer.setName()`, replacing the raw GeoPackage table name), now fully
stakeholder-confirmed by Decision Log D-84 (every proposed name confirmed as-is except `site`,
corrected from "사이트" to "조사지" in all three occurrences), which also extended this
requirement's own scope to the bundled KTSN accepted-name lookup table (DR-QPB-072):
`test_korean_layer_display_names.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package (same specification, later round).

- Traceability:
  [`qfield_project_builder_korean_layer_display_names.traceability.md`](qfield_project_builder_korean_layer_display_names.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above — including
  the textually distinct Korean *field*-alias and *relation-widget*-display-name rounds above —
  are touched by this round's additions).
- Test harness contract additions: the "Decision Log D-80/D-84" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md)
  (function 19, `inspect_layer_names`).
- **Flagged interaction (not an ambiguity in the requirement itself):** implementing this
  requirement will break three pre-existing harness functions' own by-layer-`.name()` lookup
  mechanism (`inspect_field_aliases`/`inspect_editor_widget`/`inspect_layer_renderer`) and every
  existing test across this suite that calls them by raw table name — see the traceability file's
  own "Flagged interaction with this suite's own pre-existing name-based layer lookups" section
  before any `implementer` work proceeds against `DR-QPB-078`/`FR-QPB-130`.

### Application rename to "FieldBuild Standalone" / version display / credential-storage-directory migration / branding (Decision Log D-81/D-82/D-86)

A later, separate `test-designer` round covers new `FR-QPB-131`/`FR-QPB-132` (Section 5.1),
`NFR-QPB-018`/`NFR-QPB-072` (further revised)/new `NFR-QPB-081` (Section 14.1), and new
`AC-QPB-119`–`122` (Section 18.5) — Decision Log D-81's application rename away from "QField
Project Builder" (its specific proposed name, "QFieldKit," corrected to **"FieldBuild Standalone"** by
Decision Log D-86) plus the credential-storage-directory migration this rename's own consequential
side effect required; Decision Log D-82's addition of a visible running-version string somewhere
in the wizard UI. Also covers the separate, Category D branding decision recorded in
`docs/ui-design-guidelines.md`'s "Branding: logo asset and its two confirmed uses" section (a
wizard banner, and a macOS app icon regenerated from `resources/fieldbuild-kit-logo.png`'s
icon-mark sub-region) — not a spec FR/AC, but a direct follow-on to D-81/D-86 recorded in that same
Decision Log entry's closing note. New file `test_app_rename_and_branding.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package.

This round's central finding, mirroring the credential-storage-mechanism and offline-VWorld-
key/canvas-pan rounds above: every criterion here concerns the desktop application's own code, UI,
local-storage mechanism, or packaging configuration — never a generated-project artifact — so most
of it does not fit (and did not need to extend) `qfield_builder.acceptance_api`'s black-box
surface. Two exceptions (`README.md`'s and `packaging/qfield_builder.spec`'s own plain, statically
readable text/AST content, never requiring any `qfield_builder` runtime import or Qt/QGIS
construction) are covered directly with real, automated tests; two genuinely human/visual-only
facts (the regenerated macOS icon's actual visual crop, and the wizard banner's actual on-screen
rendering quality) are covered with `manual`-marked placeholders; everything else (the credential-
storage-directory migration itself, the wizard's own window title/version-string display, and the
wizard banner's own widget-existence fact) is routed to the `implementer` role's `tests/unit/`
mandate, with a fully specified, offscreen-automatable contract table rather than being silently
left unaddressed.

- Traceability:
  [`qfield_project_builder_app_rename_version_and_branding.traceability.md`](qfield_project_builder_app_rename_version_and_branding.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched by
  this round's additions).
- Test harness contract additions: none — every criterion in this round is either a plain
  static-file check needing no `qfield_builder.acceptance_api` surface at all, a `manual`-marked
  placeholder, or routed to `tests/unit/` (see the traceability file's own routed contract tables
  for the exact, fully specified assertions a future `tests/unit/test_credential_store.py`/
  `tests/unit/test_wizard.py` round must satisfy).

### Live Tabler icon preview-fetch during search (Decision Log D-76)

A later, separate `test-designer` round covers revised `FR-QPB-011(d)` (Section 5.4, new clause
`(d)(ii)`), revised `NFR-QPB-080` (Section 5.4, new clauses (5)-(8)), annotated `AC-QPB-101`
(Section 18.2, not altered in substance), and new `AC-QPB-117` (Section 18.2) — Decision Log D-76's
stakeholder-approved addition of a second, independently scoped, narrower network-fetch trigger to
the Step 6 Tabler icon search: fetching preview SVG content, live, for the currently visible/
matched results of an in-progress search, debounced as the user types, bounded so it is never an
unbounded background prefetch of the entire ~5,130-name bundled index and never for a result not
currently visible — additional to, and not a replacement for, the pre-existing, unaffected
fetch-on-selection mechanism (`FR-QPB-011(d)(i)`/`AC-QPB-101`): new file
`test_tabler_icon_preview_fetch.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package.

This round's central finding, mirroring the credential-storage-mechanism, offline-VWorld-key/
canvas-pan, and app-rename rounds above: the real debounce timing, real bounded HTTP concurrency,
and the new preview-fetch request's own `User-Agent` header are all internal PySide6-widget/
HTTP-client-construction mechanisms, not generated-project artifacts or pure GUI-independent logic
functions, and are routed to the `implementer` role's own `tests/unit/` mandate in full, with a
fully specified contract table. The one part of this feature that genuinely is a pure,
GUI-independent logic function — "given a set of currently visible/matched names, fetch each
one's preview, degrading gracefully per name on failure, never expanding beyond the given set" —
is exposed headlessly via a new harness function and is tested directly, mirroring the existing
`search_bundled_tabler_icon_names` precedent.

- Traceability:
  [`qfield_project_builder_tabler_icon_preview_fetch.traceability.md`](qfield_project_builder_tabler_icon_preview_fetch.traceability.md)
  (kept as its own file, separate from the Decision Log D-61/D-65 symbol-styling baseline round
  above, so that already-approved traceability record is not touched by this round's additions).
- Test harness contract additions: new function 20 (`fetch_tabler_icon_preview_svgs`), in the "New
  (Decision Log D-76)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Unconditional "Export HTML Report" project plugin (Decision Log D-83/D-85/D-87)

A later, separate `test-designer` round covers Section 13.10, `FR-QPB-038`/`090`/`100` (further
revised), `FR-QPB-133`/`134`, and `AC-QPB-123`–`127`. D-83 adds the on-demand standalone HTML
report; D-85 first broadened the shared sidecar trigger; D-87 closes former Open Question O-42 as
**always present, no toggle** and makes the final boundary explicit. Every generated project has
the slug-named `<project_slug>.qml` sidecar and Export HTML Report mechanism. The "Identify
attached photos" reminder and identification write-back polling `Timer` appear only when
`identification_enabled = true`. Coverage is in `test_html_report_export.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package.

`AC-QPB-123`/`124`/`125` and both D-87 branches of `AC-QPB-127` are executable structural checks
against generated sidecars. They pass no invented report-enable config key. `AC-QPB-126` remains
the specification-required manual/`device` placeholder, gated only on Open Question O-41. The
superseded `test_no_plugin_file_when_identification_disabled` premise is replaced in
`test_post_mvp_identification_plugin.py` by a narrowed FR-QPB-038 regression: the shared
sidecar/report remains present while identification-specific reminder/Timer content is absent.

- Traceability:
  [`qfield_project_builder_html_report_export.traceability.md`](qfield_project_builder_html_report_export.traceability.md)
  (kept as its own file, so none of the already-approved traceability records above are touched by
  this round's additions).
- Test harness contract additions: none — every criterion is covered either by reading the
  generated `<project_slug>.qml` sidecar file directly (already exposed via `build_project()`,
  function 4, mirroring `AC-QPB-099`'s "no new harness function" precedent), or by a documented,
  skipped manual/`device` placeholder for AC-QPB-126/O-41. See the "New (Decision Log
  D-83/D-85/D-87)" section of
  [`qfield_project_builder/HARNESS_CONTRACT.md`](qfield_project_builder/HARNESS_CONTRACT.md).

### Standalone HTML report visual refinement (Decision Log D-UI-HRA-001)

The approved Category-D visual refinement of the generated standalone HTML report is covered by
`test_html_report_ui_refinement.py`, inside the same
[`qfield_project_builder/`](qfield_project_builder/) package. It covers all 15 stable
`DAC-HRA-001`–`DAC-HRA-015` design-review criteria with generated-sidecar static/HTML checks and
explicitly skipped browser/manual gates for 375px responsive layout, theme persistence, print,
reduced motion, navigation, keyboard focus, contrast, and data/control regression behavior.

- Traceability:
  [`qfield_project_builder_html_report_ui_refinement.traceability.md`](qfield_project_builder_html_report_ui_refinement.traceability.md)
  (kept separate from the functional AC-HRA report mappings so the approved data/report contract
  remains independently traceable).
- Test harness contract additions: none — the tests reuse `build_project()` and the generated
  `<project_slug>.qml` sidecar already covered by the report-export acceptance round.

### Saved-feature identification edit write-back (Decision Log D-92)

The separately approved saved/reopened plant-observation edit feature is covered by
`test_saved_feature_identification_edit.py`. Its structural checks inspect the generated project
plugin and embedded widget for the distinct existing-feature `FeatureForm.model` lookup, UUID and
layer guards, Type 3 relation-model traversal, all three selected fields, and fail-closed
behavior; they reject a feature-list model as a write target. The actual QField form interaction,
normal save/reopen persistence, and target-runtime API reachability are explicit, skipped
`manual`/`device` placeholders because this harness has no QField/QML runtime.

- Traceability:
  [`qfield_project_builder_saved_feature_identification_edit.traceability.md`](qfield_project_builder_saved_feature_identification_edit.traceability.md).
- Test harness contract additions: none — the structural tests reuse `build_project()` and the
  existing `inspect_identification_widget(...)["qml_code"]` surface; runtime criteria retain
  explicit device/manual evidence gates.
