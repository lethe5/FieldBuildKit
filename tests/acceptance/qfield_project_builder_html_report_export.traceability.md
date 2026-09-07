# Traceability Matrix — Unconditional HTML Report Project Plugin

> Approved specification: `specs/qfield-project-builder.md`, Decision Logs **D-83**, **D-85**,
> and **D-87**; `FR-QPB-038` (further revised), `FR-QPB-090` (further revised), `FR-QPB-100`
> (further revised), `FR-QPB-133`/`134`, and `AC-QPB-123`–`127`.
>
> Executable tests: `qfield_project_builder/test_html_report_export.py`, plus the narrowed
> identification-disabled regression in
> `qfield_project_builder/test_post_mvp_identification_plugin.py`.

## Approved behavior

D-87 closes former Open Question O-42 as **always present, no toggle**. Every generated project
contains a slug-named `<project_slug>.qml` sidecar alongside its `.qgs`, and that sidecar always
contains the Export HTML Report toolbar/report mechanism. No report-enable wizard/config field is
introduced.

The shared file's identification content is separate and conditional:

- `identification_enabled = false`: report sidecar/mechanism present; "Identify attached photos"
  reminder and identification write-back polling `Timer` absent.
- `identification_enabled = true`: report sidecar/mechanism present; reminder and polling `Timer`
  present.

This resolves D-85's former dual-trigger wording and the former FR-QPB-038 tension. The historical
claim that the whole sidecar should be absent when identification is disabled is superseded.

## Criterion-to-test mapping

| ID | Observable requirement | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-123; FR-QPB-090/100/133 (D-87) | Every survey type has the slug-named sidecar and distinct Export HTML Report toolbar registration with identification disabled or enabled, without a report config key | `test_html_report_export.py::test_ac123_report_sidecar_and_toolbar_button_are_unconditional_without_report_toggle` (4 survey types × 2 identification states) | auto; generated-sidecar inspection |
| AC-QPB-124; FR-QPB-133/134 | The report handler constructs HTML with no externally hosted script, stylesheet, font, or image | `test_html_report_export.py::test_ac124_generated_html_report_content_has_no_external_resource_references` | auto; structural QML inspection |
| AC-QPB-125; FR-QPB-133/134 | The `.html` output path is rooted at `qgisProject.homePath` (or the established equivalent) and is not a hardcoded absolute path | `test_html_report_export.py::test_ac125_output_path_is_project_relative_via_qgis_project_home_path` | auto; structural QML inspection |
| AC-QPB-126; FR-QPB-133/134 | A report generated on a real runtime reflects the current project/schema summary and all actual stored domain records | `test_html_report_export.py::test_ac126_generated_report_reflects_actual_current_project_data_on_a_real_device` | manual/`device`; skipped; O-41-gated |
| AC-QPB-127 branch 1; FR-QPB-038/090/100/133 | Identification disabled leaves sidecar/report present but removes reminder and polling `Timer` | `test_html_report_export.py::test_ac127_identification_disabled_keeps_report_but_omits_identification_components`; `test_post_mvp_identification_plugin.py::test_identification_disabled_keeps_shared_sidecar_without_identification_runtime` | auto; generated-sidecar inspection |
| AC-QPB-127 branch 2; FR-QPB-090/100/109/133 | Identification enabled leaves sidecar/report present and includes reminder and polling `Timer` | `test_html_report_export.py::test_ac127_identification_enabled_keeps_report_and_adds_identification_components` | auto; generated-sidecar inspection |

Every AC in this slice maps to a concrete executable test except AC-QPB-126, whose own approved
text explicitly requires manual/device QA and remains gated by O-41.

## Harness contract

No new `qfield_builder.acceptance_api` function or config field is required. All automated checks
build through the existing `build_project()` contract and inspect the generated sidecar directly,
matching AC-QPB-069's established pattern. In particular, the tests intentionally pass no report-
enable key: D-87 says none exists.

## Remaining ambiguity

Only **O-41** remains. It asks whether QField's QML context can enumerate complete GeoPackage
layers at the volume needed for the actual-record portion of the report. Therefore AC-QPB-126
remains a manual/`device` placeholder and must not be marked passing for a schema-only, stale, or
fabricated report. O-42 is closed and no longer blocks any automated test.

## Scope notes

- AC-QPB-124/125 inspect the identification-disabled branch. This also proves the report content
  and output-path mechanism do not depend on identification.
- The AC-QPB-127 `Timer` checks target the approved generated sidecar. The report is on-demand-only
  (FR-QPB-133); the identification polling `Timer` is therefore expected only in the enabled
  branch.
- The earlier `test_no_plugin_file_when_identification_disabled` premise was not retained. Its
  replacement narrows the negative assertion to identification-specific runtime content while
  positively asserting the unconditional shared sidecar/report mechanism, preserving FR-QPB-038
  traceability under D-87.
- Photos and identification-result data remain outside the HTML report's required content scope,
  exactly as D-83 states.
