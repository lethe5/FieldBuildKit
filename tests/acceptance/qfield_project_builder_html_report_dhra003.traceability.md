# D-HRA-003 traceability — VWorld-key-first report background with OpenStreetMap fallback

Specification: [`specs/html-report-interactive-analytics.md`](../specs/html-report-interactive-analytics.md)

Tests: [`qfield_project_builder/test_html_report_dhra003_vworld_osm_fallback.py`](qfield_project_builder/test_html_report_dhra003_vworld_osm_fallback.py)

| Requirement / criterion | Coverage |
|---|---|
| FR-HRA-004 (revised), E-HRA-008 (revised) | `test_dhra003_saved_key_is_runtime_input_with_vworld_first_and_osm_default` checks runtime saved-key lookup, selector-to-VWorld-helper argument linkage, VWorld helper tile-request use, and automatic no-key OpenStreetMap selection. It deliberately does not require a VWorld URL to appear after the selector's key variable because the helper is defined earlier. `test_dhra003_remote_failure_keeps_local_report_usable_and_discloses_state` checks tile-failure handling, alternate/offline disclosure, and retention of local report capabilities; the device placeholder covers actual service outcomes. |
| FR-HRA-015, C-HRA-004 | `test_dhra003_remote_failure_keeps_local_report_usable_and_discloses_state` requires local map/table/summary/CSV functions to remain represented independently of remote tile success; the device placeholder exercises them with both services unavailable. |
| FR-HRA-017, C-HRA-008; FR-RWF-006 (preserved secret boundary) | `test_dhra003_attribution_status_and_key_not_displayed` checks visible VWorld/OpenStreetMap attribution and background status constituents. `test_dhra003_export_key_embedding_requires_explicit_consent` checks that the saved key is not copied into plugin/UI source, non-consent exports clear it, omission is the dialog default, and only an accepted explicit include choice reaches HTML generation. The device placeholder verifies rendered UI does not display the key. Option 1 permits the credential in exported tile-request data only after that consent. |
| AC-HRA-011 (revised) | The four automatic tests cover structural key-first/OSM-default behavior, failure/offline resilience, attribution/status, and the consent-gated Option 1 export boundary. `test_dhra003_vworld_key_first_osm_fallback_and_offline_resilience_on_device` is the required real-QField/browser/network gate for actual VWorld imagery, automatic OSM fallback, alternate-service behavior, usable offline local report functions, and UI key non-display. |

## Harness boundary

The acceptance harness has no QField project-plugin runtime, browser, network-service control, or
device session. Fake-key builds and source inspection are therefore necessary structural checks,
not claims that tiles render. The skipped device test must record the exact QField version/platform,
browser/device, active background, fallback/offline status, attribution, local-function behavior,
and confirmation that the API key is not displayed in the report UI. Under Option 1, the exported
HTML may include the key in VWorld tile-request data.
