# Optional reference inputs: verification record

Date: 2026-09-08. App version: **0.1.11 → 0.2.0**. Decision: D-98 in
`specs/qfield-project-builder.md`.

## Implemented behavior and automated evidence

| Contract | Evidence |
| --- | --- |
| No private assets required | Normal builds never discover `storage` or `REFERENCE_DATA_DIR`; clean copied checkout without `storage`: 89 relevant tests passed. |
| Excel and TIFFs independently optional | Real builds for all four survey types × identification enabled/disabled × neither/Excel/TIFFs/both; generated folders moved and local sources checked. |
| Explicit input validation | Missing selected inputs fail atomically; workbook preview, confirmation, clear and Back/Next tested. |
| Downloadable fictional workbook | `resources/samples/taxonomy_sample.xlsx`: 5,810 bytes, 23 columns, two header rows, two accepted examples and one synonym; actual ingest and save-dialog download tested. Sample is never automatically selected. |
| No workbook identification | Actual generated JavaScript candidate selection, direct form writeback and pending project-plugin writeback executed with Node; API scientific names preserved without fabricated Korean names/KTSNs. |
| Portable TIFF selection | Synthetic georeferenced TIFF combined into project-local stack; value 0.25 preserved, original input unchanged, no source cache written. |
| Standalone packaging | PyInstaller build and packaged `--check-runtime` succeeded; no packaged `storage`, fictional sample present, three source versions and bundle version agree. |

Broader related regression run: **418 passed, 12 skipped, 1 failed**. The failure,
`test_candidate_write_back_preserves_three_identity_values_but_manual_path_is_compatible`,
also fails on untouched HEAD: it expects older generated QML source text. It is not counted
as a pass. The full repository suite also has existing failures outside this change; this
record does not claim the whole suite is green.

After the final Satellite zoom fix, the focused optional-input, GUI smoke, packaging and QML
suite passed: **195 passed, 4 skipped**. Reproduce with:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q \
  tests/unit/test_optional_reference_inputs.py tests/unit/test_smoke_gui.py \
  tests/unit/test_packaging_build.py tests/unit/test_packaging_probability.py \
  tests/unit/test_qml_plugin.py
.venv/bin/python packaging/build_app.py
```

New tests and packaging script pass Ruff; changed production modules pass Ruff's F checks;
`git diff --check` and dependency consistency checks pass. Historical full private-workbook
acceptance cases require explicit `QPB_PRIVATE_REFERENCE_WORKBOOK`; ordinary tests use fictional
data. The removed release-source workbook remains in the user's ignored local storage.

## Actual service calls

The user explicitly approved the temporary FieldBuild API Test app and unlocked the existing
encrypted store directly in its password dialog. Keys were used in memory for the test requests
and in a temporary QField project under a private temporary directory. No secrets are recorded
in this document, source control or reported logs; QField output was redacted before saving.

- VWorld capabilities: successful response with 41 advertised layer identifiers.
- VWorld Satellite: HTTP 200, decoded 256 × 256 JPEG at a Seoul tile, zoom 16.
- Pl@ntNet: HTTP 200, six candidates, top result `Hibiscus rosa-sinensis`, using the public
  example flower image. This verifies a real service response, not in-form photo capture.
- Native QField initially requested Satellite zoom 4. The service returned
  `InvalidParameterValue`, explicitly giving valid zooms 6–19. Both project generators now
  use Satellite `zmin=6`; the final QField run produced no tile errors in its 15-second log.

## Native QField evidence and remaining blocker

Installed executable: `/Applications/qfield.app/Contents/MacOS/qfield`.
QField short bundle version **4.2**, full bundle version **4.2.11**,
runtime QGIS **4.0.3-Norrköping**.

Generated no-reference and fictional-workbook projects were passed to the actual installed
QField executable. The final project with live API configuration was regenerated after the
zoom fix and launched again. QField logged `AppInterface loading file` for that project and
remained running for the 15-second observation interval. Test subprocesses were then stopped.
The log also warns that the template was saved by QGIS 3.44.13-Solothurn, older than its runtime.
Launch/load requests and absence of additional logged errors do not prove successful form edits.

Native automation can enumerate the QField window and title-bar controls, but interior map/form
actions return **`AXError.notImplemented`**. QML form controls are absent from the accessibility
tree. Consequently form entry, in-form Pl@ntNet selection, save/reopen persistence, and interactive
TIFF sampling remain **unverified in QField**. Static/Node/GUI smoke passes above are separate
evidence and do not replace those checks. Windows, iOS and Android were not tested.

Future project changes must repeat native QField verification per `AGENTS.md`. Completing these
remaining interactions requires an automation route that can operate this QField Qt Quick view;
the user was not assigned routine manual testing.

### Follow-up: accessibility investigation

After the user enabled QField in macOS Accessibility, a fresh automation session still saw
only the native window/title-bar/menu elements. Clicking the visible Created projects row
returned `AXError.notImplemented`, including after activating the window with keyboard input.
The user reports that manual form input works; this is not evidence of a broken survey form.

The installed executable contains `QCocoaAccessibility`, `QMacAccessibilityElement`,
`QAccessibleQuickControl`, `QAccessibleQuickItem`, and `QAccessibleQuickWindow` identifiers.
Thus a complete omission of Qt/macOS accessibility code from this build is not supported by
the evidence. Presence of these classes does not establish correct runtime activation or
exposure of the QML controls. Inspection of the matching official v4.2.11 source found an
Android accessibility-disable setting, but no corresponding macOS disable setting. QField's
custom QML also contains no explicit `Accessible` attached properties; inherited Qt controls
can still provide accessibility, so this alone does not explain the failure.

The precise failing macOS AX operation is not exposed by the automation tool's error. We cannot
yet distinguish a Qt accessibility bridge/runtime problem from the tool's handling of that
bridge. The error must not be reported as proof that QField does not support accessibility.
The official source includes a separate `WITH_SPIX` GUI test build (default off) and tests that
launch `qfield_spix`; that is an alternative test architecture, not a setting enabled in the
installed release app. No application binaries or system permissions were changed during this
investigation.

Sources: [matching QField entry point](https://github.com/opengisch/QField/blob/v4.2.11/src/app/main.cpp),
[test build option](https://github.com/opengisch/QField/blob/v4.2.11/CMakeLists.txt),
[GUI test launcher](https://github.com/opengisch/QField/blob/v4.2.11/test/spix/conftest.py),
[Apple error definition](https://developer.apple.com/documentation/applicationservices/axerror/notimplemented).

## 0.2.3 initial map extent fix — user confirmation received (2026-09-08)

The reported first-open QGIS view showed global imagery warped into EPSG:5186. The templates
contained neither a named `mapcanvas` nor a default/preset view extent. The QField 4.2.11 source
in `src/core/qgsquick/qgsquickmapsettings.cpp` confirms that a missing `theMapCanvas` falls back
to the project full extent, which can include a worldwide basemap.

Branch `fix/project-initial-map-extent` now writes both the named canvas and
`ProjectViewSettings` extents in the selected project CRS. Bounds use survey geometry first,
offline MBTiles coverage next, and Korea (124.5–132 E, 33–39 N) when neither is available.
Geometry/coverage receives 10% padding with a 0.001-degree minimum for point-only data.
The stored geometry and project CRS selection remain unchanged.

Verification completed:
- 139 related tests passed (initial extent, standalone builds/relocation, optional references,
  and build orchestration). Two offline empty-survey cases were rerun after adding explicit
  coverage assertions; both passed. Ruff and `git diff --check` passed.
- QGIS 3.44.13, through `scripts/qgis_isolated_probe.py` with a temporary isolated profile,
  loaded both generated projects, read their native map settings, and rendered without errors.
  Korea view width was about 701 km; the test survey view was about 1.07 × 1.33 km.
  QGIS's installed world-outline dataset was added only to the in-memory test renderer.
  Screenshots and the diagnostic script are under ignored `build/extent-verification/`.
- The 0.2.3 application bundle and packaged runtime check passed; all three source version
  declarations and the bundle version were synchronized from 0.2.2 to 0.2.3.

Agent-driven QField UI verification was blocked: three attempts to acquire the installed app's UI returned
`timeoutReached`. The longer direct launch logged `AppInterface loading file` for the generated
survey project and QGIS runtime 4.0.3, but this does not prove the visible map extent. Test-owned
processes were stopped; existing user app sessions were retained. No live API keys were needed.
After this limitation and the deferred commit/merge were reported, the user stated
"확인 완료" (verification complete). This user confirmation closes the remaining acceptance
step for this change and permits the agreed local commit/merge workflow. It is user-reported
verification, not a successful agent-driven QField UI test; no additional test scenarios or
runtime details were supplied. Previously generated user projects have not been modified.
