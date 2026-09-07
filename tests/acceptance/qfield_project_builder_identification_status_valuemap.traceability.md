# Traceability Matrix — QField Project Builder, `identification_status` `ValueMap` Widget

> Specification: `specs/qfield-project-builder.md`, Section 9 (new `FR-QPB-122`), Section 18.2
> (new `AC-QPB-103`) — Decision Log D-63 (draft proposal) confirmed by Decision Log D-69, closing
> Open Question O-33.
>
> This is a **later, separate `test-designer` round against the same overall specification** as
> `qfield_project_builder.traceability.md` (the approved MVP baseline), recorded as its own file
> per this project's established convention (see `tests/acceptance/README.md`), so the
> already-approved MVP/post-MVP traceability records are not touched by this round's additions.
>
> Tests: `tests/acceptance/qfield_project_builder/test_qgis_project_config.py` (added to this
> existing MVP-suite file, not a new file — see rationale below).
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s "New
> (Decision Log D-64–D-69...)" section, function 16 (`inspect_editor_widget`), reused unchanged
> from the `test_ktsn_lookup_table.py` round.

## Why this round's one test pair lives in `test_qgis_project_config.py`, not a new file

Decision Log D-63's own text is explicit that this item "is unrelated in scope to Decision Log
D-62/Section 13.9's much larger lookup-table/autocomplete proposal" (the KTSN lookup-table feature,
covered by its own dedicated `test_ktsn_lookup_table.py`/traceability file) — it is a narrowly
scoped, single-field, single-mechanism change reusing the existing `ValueMap` editor-widget
mechanism this codebase already uses for the `organ` field. `test_qgis_project_config.py` already
covers exactly this class of criterion (per-field editor-widget configuration —
`RelationReference` for foreign keys, AC-QPB-013) for the approved MVP baseline; adding this
round's two new tests there, rather than to a new, single-purpose file, follows this project's own
file-organization judgment call for a small, single-criterion addition (mirrored by, e.g., how
Decision Log D-56–D-58's own Korean-field-alias round *did* warrant a dedicated new file, because
it touched every field of every layer of every survey type — a much larger surface than this one
field).

## Traceability table

| AC ID / FR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-103 | `identification_status` is configured with a `ValueMap` widget listing exactly the five existing enum values, displayed as the raw English strings (no Korean translation, Decision Log D-69); the stored value on save remains exactly the raw enum string | `test_qgis_project_config.py::test_ac103_identification_status_uses_a_value_map_widget_with_exactly_the_five_enum_values` (parametrized, 3 survey types — `inventory_observation`/`observation`), `::test_ac103_selecting_and_saving_a_value_writes_the_exact_raw_enum_string` (save-time persistence, `simple_inventory` only — see note below) | auto (proxy — PyQGIS-backed `inspect_editor_widget` for the widget-configuration half; `attempt_feature_save` + direct GeoPackage inspection for the save-time persistence half) |

## Notes on automation approach

1. **The save-time persistence test is exercised once, on `simple_inventory`'s
   `inventory_observation`, not per survey type.** The widget-configuration half
   (`test_ac103_identification_status_uses_a_value_map_widget_with_exactly_the_five_enum_values`)
   *is* parametrized across all three Types 1–3 survey types, since the widget itself is configured
   per layer/survey-type and could plausibly diverge. The save-time persistence mechanism itself —
   a `ValueMap` widget's own selection still writes the field's ordinary underlying value,
   unaffected by its own presentation — is not survey-type-specific (it is the same GeoPackage
   `CHECK`-constrained text column and the same field-constraint save path in every case), and
   testing it on `inventory_observation` (a self-contained layer with no foreign-key dependency)
   avoids the extra fixture complexity of seeding a parent `survey`/`site` row purely to exercise a
   survey-type-independent property. If a future round finds this assumption wrong (i.e. the
   persistence mechanism genuinely differs by survey type), that would be a defect this test would
   not, by itself, catch — flagged here as this test's own disclosed scope limitation.
2. **No Korean-language `ValueMap` value-label test exists, deliberately, per Decision Log D-69's
   own explicit confirmation.** The stakeholder's confirmed answer keeps the displayed option text
   as the existing raw English enum strings — `test_ac103_identification_status_uses_a_value_map_
   widget_with_exactly_the_five_enum_values` asserts this directly (`value_map.get(value) ==
   value` for every one of the five values), which is itself the negative confirmation that no
   Korean translation was silently introduced.

## Ambiguities / gaps found

None found. FR-QPB-122/AC-QPB-103's own text is fully concrete and unambiguous as written
(Decision Log D-69 explicitly closed the one previously-open sub-question, display-language, by
confirming the existing raw-English-string status quo) — no invented assumption was required.
