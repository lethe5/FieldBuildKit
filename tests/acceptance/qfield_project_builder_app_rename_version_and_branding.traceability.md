# Traceability Matrix — QField Project Builder, Application Rename to "FieldBuild Standalone" / Version Display / Credential-Storage-Directory Migration / Branding

> Specification: `specs/qfield-project-builder.md` — Decision Log **D-81** (the rename decision
> and the credential-storage-directory migration behavior it required), **D-82** (the
> version-display addition), and **D-86** (correcting D-81's specific proposed name from
> "QFieldKit" to "FieldBuild Standalone"); new `FR-QPB-131`/`FR-QPB-132` (Section 5.1); `NFR-QPB-018`
> (further revised)/`NFR-QPB-072` (further revised)/new `NFR-QPB-081` (Section 14.1); new
> `AC-QPB-119`–`AC-QPB-122` (Section 18.5). Also covers the separate, Category D branding decision
> recorded in `docs/ui-design-guidelines.md`'s "Branding: logo asset and its two confirmed uses"
> section (not a spec FR/AC — a direct follow-on to D-81/D-86, per that section's own closing note
> in the Decision Log).
>
> Tests: `tests/acceptance/qfield_project_builder/test_app_rename_and_branding.py`.
> Test harness contract: no `HARNESS_CONTRACT.md` change was made or needed — every criterion
> in this round concerns the desktop application's own code/UI/local-storage/packaging
> configuration, never a `build_project()`-generated project artifact, so none of it fits (or
> needed to extend) the existing `qfield_builder.acceptance_api` black-box surface. See "Scope-
> boundary finding" immediately below for what that means for this round's coverage.

## Scope-boundary finding (read this first)

This round's four new/revised requirements (`FR-QPB-131`, `FR-QPB-132`, `NFR-QPB-018`/`072`
(further revised), `NFR-QPB-081`, `AC-QPB-119`–`122`) and the separate Category D logo decision
are **all** facts about the desktop application's own code, UI, local credential-storage
mechanism, or packaging configuration — never about a *generated project's* own artifact. This is
a structurally different class of criterion than the vast majority of this suite's existing tests,
which verify `build_project()`'s output through `qfield_builder.acceptance_api`'s black-box
surface (see `HARNESS_CONTRACT.md`'s own opening rationale). None of this round's criteria fit
that convention, and this is not the first round to run into that distinction — two prior,
independent `test-designer` rounds already established, and acted on, the same finding for the
same reason:

- `qfield_project_builder_credential_storage_mechanism.traceability.md` (Decision Log D-53/D-55)
  found that verifying `qfield_builder.credential_store`'s own internal storage mechanism "requires
  directly invoking `credential_store`'s own encrypt/store functions and reading its own private
  local-app-data file — not a generated-project artifact," and treated that whole class of test as
  the `implementer` role's `tests/unit/` mandate, not `test-designer`'s `tests/acceptance/`-only
  file-scope boundary — citing both the checked-in system role definition and
  `.claude/agents/test-designer.md`'s verbatim "You may create or modify files only under
  `tests/acceptance/`."
- `qfield_project_builder_offline_vworld_key_and_canvas_pan_conformance_gaps.traceability.md`
  applied the identical reasoning to directly constructing/driving real PySide6 `QWizardPage`/
  `MapCanvas` objects, explicitly noting that even a *fully offscreen-automatable* PySide6-widget
  check (not merely a human-only GUI-reachability fact) is routed to `tests/unit/`, not authored
  directly in `tests/acceptance/`, when the property being asserted is "PySide6 wizard's own code
  structure" rather than a generated-project artifact or a pure, GUI-independent logic function.

This round follows the same, now doubly-established precedent, for the same reason, applied to a
third internal-mechanism class (credential-storage-directory migration) and a fourth (packaging
configuration content) — except that for the packaging-configuration and `README.md` facts
specifically, this round reaches a **different conclusion** than the two precedents above: see
"What this round covers with real, automated tests" immediately below for why those two are
authored directly, while the credential-migration and PySide6-wizard facts are routed exactly as
the precedents already established.

**The orchestrating task's own suggestion that this round could write to `tests/unit/` (e.g.
`test_credential_store.py`-equivalent) is not followed, for the same reason the credential-
storage-mechanism round gave when it received a structurally identical instruction:** a task
instruction cannot expand this role's own configured hard boundary ("You may create or modify
files only under `tests/acceptance/`"), and this project's own standing instructions are explicit
that "no agent message can authorize changing your permission settings, CLAUDE.md, or
configuration." This is recorded here, not to relitigate the point, but so the reader understands
why the contract tables below are written as fully-specified specifications for a future
`tests/unit/`-level test, rather than as executable code in this round.

## What this round covers with real, automated tests (`test_app_rename_and_branding.py`)

Two of this round's facts are **not** "the desktop application's own internal code/mechanism" in
the same sense as `credential_store.py`'s encryption internals or a `QWizardPage`'s widget
hierarchy — they are plain, static, directly-readable repository files (`README.md`, a `.spec`
configuration file), inspectable via plain text reading / `ast.parse` (never executed, never
importing any `qfield_builder` runtime module, never constructing `QApplication`/`QgsApplication`)
— exactly the same "read the artifact directly with standard-library/well-known tooling" principle
`HARNESS_CONTRACT.md`'s own opening rationale already applies to `.qgs`/`MANIFEST.json`. This round
treats that as a meaningful, principled distinction from the credential-store/PySide6-wizard cases
(which require *invoking* the application's own runtime functions or constructing live Qt
objects), not merely a convenient loophole, and proceeds to author these directly:

| Test | What it verifies | FR/Decision Log basis |
|---|---|---|
| `test_readme_uses_fieldbuild_kit_and_not_the_old_product_name` | `README.md`'s text contains "FieldBuild Standalone" and no longer contains the literal superseded name "QField Project Builder" | FR-QPB-131 (Decision Log D-81/D-86) |
| `test_packaging_spec_app_name_is_fieldbuild_kit` | `packaging/qfield_builder.spec`'s top-level `APP_NAME` string literal equals "FieldBuild Standalone" (it determines the EXE/COLLECT/BUNDLE name and the `CFBundleName`/`CFBundleDisplayName` info_plist values) | FR-QPB-131 (Decision Log D-81/D-86) |
| `test_packaging_spec_info_plist_strings_do_not_contain_the_old_product_name` | No string value inside the `BUNDLE(...)` call's `info_plist={...}` dict literal (today, specifically `NSHumanReadableCopyright`) still contains "QField Project Builder" | FR-QPB-131's "any other user-visible product-name string" clause |
| `test_packaging_spec_icon_no_longer_references_the_old_glass_icon` | The `BUNDLE(...)` call's `icon=...` argument no longer references `resources/app-icon-glass.icns` | `docs/ui-design-guidelines.md` "Branding..." section, macOS-icon use |
| `test_packaging_spec_icon_references_an_icns_file_under_resources` | The `icon=...` argument still references some `.icns` file under `resources/` (the guideline's own "a full `.icns` iconset" requirement) — deliberately does **not** assert a specific new filename, since none is specified anywhere in the approved guidelines text (see "Ambiguities" below) | `docs/ui-design-guidelines.md` "Branding..." section |

All five were run against the current, pre-implementation codebase and produce the expected "red"
state: the first four fail (README/`.spec` still name the old application/reference the old icon);
the fifth passes today (the current `app-icon-glass.icns` reference already happens to satisfy the
weaker "some `.icns` file under `resources/`" structural check, which remains true regardless of
which specific `.icns` file is referenced — this is an intentional, permanently-valid regression
guard, not a criterion this round expects to currently fail).

Two additional `@pytest.mark.manual`/`@pytest.mark.skip` placeholders, mirroring the established
`AC-QPB-104`/`FR-QPB-008`/`test_map_canvas_pan_navigability.py` convention exactly, cover the two
genuinely human/visual-only facts neither this round's automated tests nor any headless mechanism
can confirm:

| Test | What it documents |
|---|---|
| `test_macos_packaged_app_icon_shows_only_the_icon_mark_not_the_old_glass_icon_or_the_wordmark` | The regenerated `.icns` file's actual visual content (only the map-layers-with-pin icon mark, correctly cropped, at every required resolution) — requires an actual macOS build via `packaging/build_macos_app.sh` and visual inspection in Finder/Dock/"Get Info" |
| `test_wizard_banner_renders_correctly_on_screen_not_distorted_or_cropped` | The wizard banner's actual on-screen rendering quality (correct aspect ratio, not cropped/cut off, legible) once a real human launches the wizard |

## What this round routes to `tests/unit/` (fully specified, not authored here)

### `tests/unit/test_credential_store.py` — credential-storage-directory migration

Covers `NFR-QPB-018` (further revised)/`NFR-QPB-072` (further revised)'s directory-name change and
new `NFR-QPB-081`'s one-time migration requirement, and `AC-QPB-119`–`AC-QPB-121` (the fresh-
install, populated-upgrade, and both-already-populated scenarios).

**Illustrative-only naming note:** the exact name/signature of the new migration entry point
(e.g. a plausible `credential_store.migrate_legacy_credentials()`) is not mandated by this
contract — only the input/output behavior below is required, mirroring this project's own
established convention (e.g. Decision Log D-27/D-75) of leaving exact implementation-level naming
to the implementer where the specification itself does not dictate one.

**Interpretive note on NFR-QPB-081's own "credentials.enc file and its accompanying salt"
wording (recorded per this role's ambiguity-handling duty — not a blocking ambiguity):** the
current, already-implemented `qfield_builder/credential_store.py` stores the salt as one field
*inside* `credentials.enc`'s own single JSON structure (`_write_store`'s `"salt"` key,
base64-encoded) — there is no second, separate salt file anywhere in this module today
(`establish_password`'s `_write_store({"salt": ..., "iterations": ..., "verifier": ...})` is the
entire file's content). This contract therefore treats "copy the `credentials.enc` file and its
accompanying salt" as describing a single-file copy (the one file that already contains the salt
internally), not two separate files — the actual required behavior (copy the one `credentials.enc`
file, which structurally already carries the salt) is unambiguous and directly testable as
specified below, so this does not block coverage; it is recorded so a future reader is not
surprised that no separate "salt file" appears in the assertions below.

| Criterion | Summary | Exact assertions (`tests/unit/test_credential_store.py`-level, mirroring this file's own existing `_isolate_credential_store`/`monkeypatch.setattr(credential_store, "app_data_dir", ...)` convention) |
|---|---|---|
| `NFR-QPB-018` (further revised)/`NFR-QPB-072` (further revised) — directory renamed | `app_data_dir()` resolves to a `FieldBuild Standalone`-named directory (macOS: `~/Library/Application Support/FieldBuild Standalone/`; Windows: `%APPDATA%\FieldBuild Standalone\`), no longer `QField Project Builder`-named | Mirrors this file's own existing `test_app_data_dir_uses_the_macos_convention`/`test_app_data_dir_uses_the_windows_convention` (which currently assert the pre-rename `"QField Project Builder"` name) updated to assert `"FieldBuild Standalone"` instead, via the same `_REAL_APP_DATA_DIR()`/`monkeypatch.setattr(credential_store.sys, "platform", ...)` pattern already established in that exact file. |
| `AC-QPB-119` — fresh install, no old dir | Given no `QField Project Builder`-named directory exists anywhere, when the migration entry point runs, no migration is attempted, no error is raised, and no directory/`credentials.enc` is created until a key is actually remembered | Point `app_data_dir()` at a fresh, empty temp dir with no sibling old-name directory created at all; invoke the migration entry point; assert it no-ops cleanly (e.g. returns a falsy/"nothing to migrate" result) and that `credentials_file_path()` still does not exist afterward. |
| `AC-QPB-120` — old dir populated, new dir empty | Given an old-name temp dir containing a real `credentials.enc` (produced via real `establish_password`+`remember_key` calls against that dir), and a new-name temp dir with no `credentials.enc` yet, when the migration entry point runs, the new dir ends up with a byte-identical copy of the old dir's `credentials.enc`, the old dir's own file is left byte-for-byte unchanged, and the previously remembered key is retrievable from the new dir using the same original password | Exercise real `establish_password(password)`/`remember_key(key)` against `app_data_dir() -> old_dir`; snapshot `old_dir`'s file bytes; repoint `app_data_dir() -> new_dir`; invoke the migration entry point; assert (a) `(new_dir / "credentials.enc").read_bytes() == (old_dir / "credentials.enc").read_bytes()`, (b) the old file's bytes are unchanged from the snapshot, (c) a fresh `lock_session()` then `unlock_session(password)` against the new dir succeeds and `get_remembered_key()` returns the original key. |
| `AC-QPB-121` — both dirs already populated | Given both an old-name dir and a new-name dir each already containing their own distinct `credentials.enc` (different passwords/keys), when the migration entry point runs, the new dir's file is left byte-for-byte unchanged (never overwritten/merged), and the old dir's file is likewise left byte-for-byte unchanged | Establish two independent stores in two separate temp dirs with two different passwords/keys; snapshot both files' bytes; invoke the migration entry point with `app_data_dir()` pointed at the new dir; assert both files' bytes are byte-for-byte identical to their pre-migration snapshots (i.e. neither dir's file changed at all). |
| `NFR-QPB-081` — "copies; never deletes" (applies to the `AC-QPB-120` scenario specifically) | After a successful migration, the old directory and its file must still exist on disk, completely untouched | In the `AC-QPB-120`-style test above, additionally assert `old_dir.exists()` and `(old_dir / "credentials.enc").is_file()` remain `True` after migration. |

### `tests/unit/test_wizard.py` — version display, window-title rename, and wizard banner existence

| Criterion | Summary | Exact assertions (`tests/unit/test_wizard.py`-level, mirroring this file's own existing offscreen `QApplication`/wizard-construction conventions) |
|---|---|---|
| `FR-QPB-131` (application's own display name, wizard window title) | `ProjectBuilderWizard`'s window title contains "FieldBuild Standalone" and no longer contains the literal old name "QField Project Builder" | Construct a `ProjectBuilderWizard` under the existing offscreen `QApplication` fixture; assert `"FieldBuild Standalone" in wizard.windowTitle()` and `"QField Project Builder" not in wizard.windowTitle()`. |
| `AC-QPB-122`/`FR-QPB-132` (version display) | `qfield_builder.__version__` ("0.1.0") is visible somewhere in the wizard UI without inspecting a file/running a command | **Placement-tolerant**, per FR-QPB-132's own explicit "exact placement... left to implementer discretion" clause (mirroring Decision Log D-27's precedent, cited by FR-QPB-132 itself): assert `qfield_builder.__version__` is a substring of the wizard's own `windowTitle()` **or**, if the implementer instead surfaces it elsewhere (e.g. a footer label/About dialog reachable from the constructed wizard/its pages), that some enumerable, already-constructed widget's displayed text (e.g. iterating `wizard.findChildren(QLabel)` and any per-page equivalent) contains it. This contract does not mandate which; it requires only that the version string be demonstrably reachable from the real, constructed wizard object graph without a special test-only hook. |
| Category D logo item 1 (`docs/ui-design-guidelines.md`) — wizard banner exists | A widget referencing `resources/fieldbuild-kit-logo.png` (e.g. a `QLabel` holding a `QPixmap` loaded from that path) exists somewhere in the wizard's page hierarchy | Construct the wizard (or the specific page(s) the implementer places the banner on); assert some discoverable widget's pixmap/image source resolves to `resources/fieldbuild-kit-logo.png` — exact widget type/attribute name left to the implementer, mirroring the guideline's own "exact placement... left to implementer discretion" framing. |

## Full traceability table

| ID | Summary | Test(s) | Automation |
|---|---|---|---|
| FR-QPB-131 (`README.md`) | README no longer names the app "QField Project Builder"; names it "FieldBuild Standalone" | `test_app_rename_and_branding.py::test_readme_uses_fieldbuild_kit_and_not_the_old_product_name` | auto |
| FR-QPB-131 (packaging bundle name, `APP_NAME`) | `packaging/qfield_builder.spec`'s `APP_NAME` is "FieldBuild Standalone" | `test_app_rename_and_branding.py::test_packaging_spec_app_name_is_fieldbuild_kit` | auto |
| FR-QPB-131 ("any other user-visible product-name string," `info_plist`) | No `info_plist` string value in the `.spec`'s `BUNDLE(...)` call still names the old app | `test_app_rename_and_branding.py::test_packaging_spec_info_plist_strings_do_not_contain_the_old_product_name` | auto |
| FR-QPB-131 (wizard window title / any other in-UI product-name string) | Wizard's own window title uses the new name, not the old one | *(no test in this round — see routed contract table above)* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| FR-QPB-132 / AC-QPB-122 (version display) | `qfield_builder.__version__` visible somewhere in the wizard UI | *(no test in this round — see routed contract table above)* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| NFR-QPB-018 (further revised)/NFR-QPB-072 (further revised) (directory renamed) | `app_data_dir()` resolves to the `FieldBuild Standalone`-named directory on macOS/Windows | *(no test in this round — see routed contract table above)* | **routed to `tests/unit/test_credential_store.py`**, not yet written |
| NFR-QPB-081 / AC-QPB-119 | Fresh install, no old dir → no migration attempted, no error | *(routed, see table above)* | routed |
| NFR-QPB-081 / AC-QPB-120 | Old dir populated, new dir empty → migration copies, old dir untouched, key still retrievable | *(routed, see table above)* | routed |
| NFR-QPB-081 / AC-QPB-121 | Both dirs already populated → no migration, no overwrite either direction | *(routed, see table above)* | routed |
| Category D logo item 1 (wizard banner existence) | Some widget in the wizard references `resources/fieldbuild-kit-logo.png` | *(routed, see table above)* | **routed to `tests/unit/test_wizard.py`**, not yet written |
| Category D logo item 1 (wizard banner visual-rendering quality) | The banner actually renders correctly on screen (aspect ratio, no cropping, legible) | `test_app_rename_and_branding.py::test_wizard_banner_renders_correctly_on_screen_not_distorted_or_cropped` | **manual** (documented, skipped) |
| Category D logo item 2 (macOS icon reference replaced) | `.spec`'s `icon=` no longer references `resources/app-icon-glass.icns`; references some `.icns` file under `resources/` | `test_app_rename_and_branding.py::test_packaging_spec_icon_no_longer_references_the_old_glass_icon`, `::test_packaging_spec_icon_references_an_icns_file_under_resources` | auto |
| Category D logo item 2 (macOS icon actual visual crop correctness) | The regenerated icon visually shows only the map-layers-pin icon mark, not the full wordmark lockup, not the old glass icon | `test_app_rename_and_branding.py::test_macos_packaged_app_icon_shows_only_the_icon_mark_not_the_old_glass_icon_or_the_wordmark` | **manual** (documented, skipped) |

Every criterion this round was asked to cover (`FR-QPB-131`, `FR-QPB-132`, `NFR-QPB-018` (further
revised), `NFR-QPB-072` (further revised), `NFR-QPB-081`, `AC-QPB-119`–`AC-QPB-122`, and the two
Category D logo-decision items) appears above, mapped to either a real automated test, a `manual`-
marked placeholder, or a fully-specified routed contract — nothing is silently dropped.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

1. **This round's central finding is a role/file-scope-boundary matter, not a specification
   ambiguity** — mirroring the two precedent files cited above. `FR-QPB-131`, `FR-QPB-132`,
   `NFR-QPB-018`/`072` (further revised), `NFR-QPB-081`, and `AC-QPB-119`–`122` are all clearly,
   unambiguously worded and fully testable as written; none of them required inventing unstated
   behavior. The routing recorded above is procedural (which role's mandate covers authoring the
   test), not a defect in the requirement text itself.
2. **NFR-QPB-081's "credentials.enc file and its accompanying salt" wording** — addressed as an
   interpretive clarification, not a blocking ambiguity, in the routed contract table above (the
   current implementation stores the salt inside `credentials.enc`'s own JSON, not as a separate
   file).
3. **The regenerated macOS icon's exact filename is genuinely unspecified.** Neither
   `docs/ui-design-guidelines.md` nor any spec text names the new `.icns` file's filename (the
   guideline text explicitly states it "does not specify an exact crop rectangle or pixel
   dimensions," and says nothing about a filename either). This round's automated tests therefore
   assert only the two facts the guideline text *does* state (no longer the old filename; still
   some `.icns` file under `resources/`) rather than inventing a specific expected new filename to
   assert equality against. If the stakeholder/spec-writer wants a specific new filename fixed
   (e.g. `resources/fieldbuild-kit-icon.icns`) recorded as a firmer contract, that is a
   `spec-writer`/`docs/ui-design-guidelines.md` decision this round does not make unilaterally.
4. **`packaging/qfield_builder.spec`'s `bundle_identifier` (`kr.re.nie.qfield-project-builder`) is
   deliberately left untested/unasserted by this round.** Neither `FR-QPB-131` nor Decision Log
   D-81/D-86 mentions the bundle *identifier* (a distinct, normally-stable technical string from
   the bundle *name* FR-QPB-131 actually names) — asserting a specific new value for it here would
   be inventing a requirement the approved text does not state. This round leaves it untouched and
   unasserted, consistent with the ambiguity-handling duty not to guess past what the text actually
   requires.
