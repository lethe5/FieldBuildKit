# Traceability — D-90/D-93 identification interaction, D-91 visibility, and D-94 reconciliation

Specification: `specs/qfield-project-builder.md`, Decision Logs D-90/D-91/D-93/D-94.

This round adds only acceptance tests and this mapping.  It does not add an application API:
the tests use the existing `build_project()` and `inspect_identification_widget()` acceptance
surface, inspect the generated embedded QML source, and parse the standard QGIS `.qgs` XML layer
tree directly.  The direct XML approach follows the existing `AC-QPB-110` tests and avoids
inventing a second PyQGIS inspection function for a documented artifact format.

## Coverage

| Criterion | Test | Automation |
|---|---|---|
| AC-QPB-133 | `test_d90_d91_identify_and_layer_visibility.py::test_ac133_type_1_to_3_identify_click_starts_without_application_popup` (Type 1 `inventory_observation`, Type 2/3 `observation`) | auto (`qgis`-marked; uses generated QML source) |
| AC-QPB-134 — manual-only Identify and no automatic attachment trigger | `test_ac134_type_1_to_3_identify_is_manual_only_and_attachment_does_not_auto_identify` (Type 1/2/3) | auto structural proxy; real QField click/photo behavior remains device QA |
| AC-QPB-134 — no Type 1/2/3 application-owned consent gate | Covered jointly by the AC-QPB-133 direct-click test and the AC-QPB-134 manual-only test (Type 1/2/3) | auto structural regression check |
| AC-QPB-134 — separate Pl@ntNet key consent boundary | `test_ac134_type_1_to_3_identify_behavior_does_not_replace_separate_key_embedding_consent` (Type 1/2/3 × `consent=False/True`) | auto artifact check |
| AC-QPB-135 (revised, D-94) | `test_ac135_initial_layers_are_visible_except_registered_probability_lookup_on_untouched_reopen` (4 survey types × `none`/`online`/`offline`) | auto (`qgis`-marked; generated `.qgs` XML plus harness reopen) |
| AC-QPB-136 (new, D-94) — selected-layer identity | `test_ac136_explicit_supported_offline_layer_is_recorded_in_mbtiles_and_project_source` (`Satellite`) | auto (`qgis`-marked; checks completed tiles, MBTiles metadata, generated-project source identity, and key exclusion) |
| AC-QPB-136 (new, D-94) — invalid selection fail-closed | `test_ac136_missing_blank_or_unsupported_offline_layer_fails_before_tile_retrieval_or_promotion` (`None`, blank, unsupported/stale identity) | auto (`qgis`-marked; fake quota provider is a negative control proving selection validation precedes retrieval; asserts no promoted output) |

## Test design notes and limits

- For Type 1/2/3, the generated `사진으로 동정하기` button's `onClicked` body must call
  `qpbRunIdentification()` directly and must contain no application-owned dialog opening. The
  generated widget must contain no `Dialog`/`qpbConsentDialog` that can gate this interaction.
- The no-automatic-attachment assertion counts runtime calls to `qpbRunIdentification()` outside
  its function declaration. Type 1/2/3 must have exactly one such call, from the explicit Identify
  button.  This is a deterministic structural proxy; actual QField photo attachment and button
  execution still require the existing manual/device QA convention.
- D-93 supersedes the old Type 1 consent-gate boundary: Type 1 joins Type 2/3 on the direct path.
  The separate desktop Pl@ntNet-key embedding consent is checked independently for every Type 1/2/3
  widget with accepted and declined configurations; direct field-button behavior remains unchanged,
  while only the accepted configuration embeds the fake key. Type 4 is deliberately excluded: its
  current `community` schema has no generated identification widget/button. Existing
  `test_post_mvp_identification_plugin.py::test_ac070_vegetation_mapping_community_layer_has_no_qml_widget`
  verifies that boundary without inventing Type 4 identification behavior.
- AC-QPB-135 checks every descendant `layer-tree-layer` under each required top-level group,
  including non-spatial reference-table nodes when present. It identifies the sole hidden
  exception by the map layer's datasource ending in
  `reference/rasters/occurrence_probability_multiband.tif`, rather than by group or raster type:
  Types 1–3 with identification enabled must contain exactly one such `Reference` node and it
  must be unchecked. D-94 does not prohibit Type 4 from registering the same lookup source, so
  any Type-4 node present is checked only for the required hidden state. Every other present
  Survey data, Basemap, and Reference node must be checked. It covers all four survey types and all three basemap modes; a
  mode that does not create a basemap layer is allowed to have an empty `Basemap` group. The
  generated `.qgs` is inspected before and after the existing `validate_project()` reopen call,
  and its bytes must remain unchanged.
- AC-QPB-136 uses an explicit supported `Satellite` offline selection and verifies the completed
  MBTiles has tiles, that its metadata and generated `.qgs` preserve that identity, and that the
  key is absent. Missing, blank, and unsupported/stale selections use a fake `quota_error` source
  as a negative control: the required `offline_layer_unavailable` error must win, demonstrating
  validation occurs before tile retrieval, and no project may be promoted. All other valid
  offline fixtures updated in this round now explicitly select `Base`; a missing key fixture also
  selects `Base` so it continues to isolate the key-validation contract rather than a selection
  failure.
- The fake online VWorld key is used only to make online project generation deterministic.  The
  visibility assertion does not claim that a fake-key WMTS layer can render tiles; provider
  validity is covered by the existing online/network acceptance tests.

## Harness boundary

`build_project()` already provides generated project paths, and
`inspect_identification_widget()` already returns the raw embedded QML source. The acceptance
harness contract's existing offline `build_project()` configuration documentation is revised only
to make the D-94 explicit-supported-layer requirement visible to implementers; no API addition is
needed. This round remains entirely under `tests/acceptance/`.
