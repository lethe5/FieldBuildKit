# Traceability — D-97 VWorld Satellite and project-local toolbar assets

**Status:** Approved by the user (2026-09-04).

Specification: `specs/qfield-project-builder.md` — FR-QPB-072 (further clarified), FR-QPB-143,
AC-QPB-146–148, Decision Log D-97. Shared design guidance:
`docs/ui-design-guidelines.md` — D-97 correction.

This slice adds generated-project structural coverage and records the two required iPhone-QField
manual gates. It does not create a QField iOS simulator, treat source inspection as visual proof,
or change callbacks, consent/key boundaries, or plugin discovery behavior.

| Criterion | Executable acceptance test | Coverage and boundary |
| --- | --- | --- |
| AC-QPB-068 / FR-QPB-072 (revised, D-29) — `Satellite` native-WMTS generated datasource | `qfield_project_builder/test_basemap_online.py::test_ac068_satellite_fallback_keeps_a_layer_specific_native_wmts_source` | Automatic generated-project-artifact check using the fake key, with no live negotiation. It preserves the layer-specific `Satellite` WMTS constants and rejects an XYZ/per-tile source. |
| AC-QPB-017 — real-key live provider validation, exercised with `Satellite` | `qfield_project_builder/test_basemap_online.py::test_ac017_online_satellite_opens_without_repair_warning_with_a_real_key` | Opt-in `network` check with `QPB_TEST_VWORLD_API_KEY`; validates the local QGIS/PyQGIS provider path. It is explicitly not iPhone-QField evidence and cannot satisfy AC-QPB-146. |
| AC-QPB-146 / FR-QPB-072 (further clarified, D-97) — iPhone QField renders `Satellite` with no source-repair warning | `qfield_project_builder/test_d97_iphone_qfield_verification.py::test_ac146_iphone_qfield_satellite_renders_without_source_repair_warning` | Manual `device` gate, skipped by design. Its steps require an unchanged generated project, a valid accepted VWorld key, usable network, and an iPhone running QField. The record identifies the build, layer, QField/iOS versions, and observations, never the key. |
| AC-QPB-147 / FR-QPB-143 — unconditional report-export asset/control and conditional plant-identification asset/control, each project-local, self-contained, accessible, 48px, icon-only, callback-attached, and registered exactly once | `qfield_project_builder/test_qfield_plugin_toolbar_icons.py::test_ac147_project_local_toolbar_assets_controls_callbacks_and_registration[False]`; `...[True]` | Automatic structural generated-project inspection. The disabled branch requires only `icons/report-export.svg` and one control; the enabled branch requires exactly that asset plus `icons/plant-identification.svg` and exactly two controls. It verifies complete parseable SVG assets, relative icon paths, Korean accessible names, empty visible text, 48px width/height, nonempty click callbacks, and exactly one project-plugin `iface.addItemToPluginsToolbar` registration per required control. It does not prescribe a particular registration guard or state mechanism. If a control declares an `objectName`, the sidecar may not ask `iface.findItemByObjectName` for that same project-local control as its registration state, because that lookup can suppress its first registration. It rejects theme, `qrc:`, file, and network icon-resource dependencies. |
| AC-QPB-148 / FR-QPB-143 (D-97) — two visible nonblank nonduplicated iPhone toolbar targets, callbacks, and accessible names | `qfield_project_builder/test_d97_iphone_qfield_verification.py::test_ac148_iphone_qfield_toolbar_icons_are_nonblank_nonduplicated_and_accessible` | Manual `device` gate, skipped by design. It requires an iPhone-QField toolbar and VoiceOver/equivalent inspection; it records build and QField/iOS versions plus pass/fail observations without keys. The structural AC-QPB-147 check is necessary regression coverage, not a substitute for this visual result. |

## Active coverage boundaries

- The legacy provider-specific icon identifiers are deliberately not asserted. D-97 instead
  requires project-local SVG assets and portable, relative sources.
- AC-QPB-147 verifies the project plugin's observable exactly-once registration count, not a
  particular QML guard implementation. `iface.findItemByObjectName` remains permissible for
  QField-internal items; it is not an acceptable registration-state probe for the same
  project-local toolbar control because it can suppress that control's first registration.
- Neither the real-key local QGIS/PyQGIS test nor the structural source/asset test claims iPhone
  QField rendering, nonblank pixels, runtime duplicate behavior, tap behavior, or VoiceOver
  output. AC-QPB-146 and AC-QPB-148 remain manual iPhone gates until recorded device evidence is
  supplied.
- The manual records may identify an application/project build, QField/iOS version, selected layer,
  network condition, and pass/fail observations; they must not include VWorld or Pl@ntNet keys.
